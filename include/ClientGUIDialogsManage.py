import Crypto.PublicKey.RSA
import ClientCaches
import ClientConstants as CC
import ClientData
import ClientDefaults
import ClientDragDrop
import ClientFiles
import ClientGUICollapsible
import ClientGUICommon
import ClientGUIDialogs
import ClientDownloading
import ClientGUIOptionsPanels
import ClientGUIPredicates
import ClientImporting
import ClientMedia
import ClientRatings
import collections
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals
import HydrusNATPunch
import HydrusPaths
import HydrusSerialisable
import HydrusTags
import itertools
import multipart
import os
import random
import re
import string
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

def GenerateMultipartFormDataCTAndBodyFromDict( fields ):
    
    m = multipart.Multipart()
    
    for ( name, value ) in fields.items(): m.field( name, HydrusData.ToByteString( value ) )
    
    return m.get()
    
class DialogManage4chanPass( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage 4chan pass' )
        
        ( token, pin, self._timeout ) = HydrusGlobals.client_controller.Read( '4chan_pass' )
        
        self._token = wx.TextCtrl( self )
        self._pin = wx.TextCtrl( self )
        
        self._status = wx.StaticText( self )
        
        self._SetStatus()
        
        self._reauthenticate = wx.Button( self, label = 'reauthenticate' )
        self._reauthenticate.Bind( wx.EVT_BUTTON, self.EventReauthenticate )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        self._token.SetValue( token )
        self._pin.SetValue( pin )
        
        gridbox = wx.FlexGridSizer( 0, 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        gridbox.AddF( wx.StaticText( self, label = 'token' ), CC.FLAGS_MIXED )
        gridbox.AddF( self._token, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.AddF( wx.StaticText( self, label = 'pin' ), CC.FLAGS_MIXED )
        gridbox.AddF( self._pin, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        b_box = wx.BoxSizer( wx.HORIZONTAL )
        b_box.AddF( self._ok, CC.FLAGS_MIXED )
        b_box.AddF( self._cancel, CC.FLAGS_MIXED )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._status, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._reauthenticate, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 240 )
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _SetStatus( self ):
        
        if self._timeout == 0: label = 'not authenticated'
        elif HydrusData.TimeHasPassed( self._timeout ): label = 'timed out'
        else: label = 'authenticated - ' + HydrusData.ConvertTimestampToPrettyExpires( self._timeout )
        
        self._status.SetLabel( label )
        
    
    def EventOK( self, event ):
        
        token = self._token.GetValue()
        pin = self._pin.GetValue()
        
        HydrusGlobals.client_controller.Write( '4chan_pass', ( token, pin, self._timeout ) )
        
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
            
            ( ct, body ) = GenerateMultipartFormDataCTAndBodyFromDict( form_fields )
            
            request_headers = {}
            request_headers[ 'Content-Type' ] = ct
            
            response = HydrusGlobals.client_controller.DoHTTP( HC.POST, 'https://sys.4chan.org/auth', request_headers = request_headers, body = body )
            
            self._timeout = HydrusData.GetNow() + 365 * 24 * 3600
            
        
        HydrusGlobals.client_controller.Write( '4chan_pass', ( token, pin, self._timeout ) )
        
        self._SetStatus()
        
    
class DialogManageAccountTypes( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, service_key ):
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage account types' )
        
        self._service_key = service_key
        
        self._edit_log = []
    
        self._account_types_panel = ClientGUICommon.StaticBox( self, 'account types' )
        
        self._ctrl_account_types = ClientGUICommon.SaneListCtrl( self._account_types_panel, 350, [ ( 'title', 120 ), ( 'permissions', -1 ), ( 'max monthly bytes', 120 ), ( 'max monthly requests', 120 ) ], delete_key_callback = self.Delete )
        
        self._add = wx.Button( self._account_types_panel, label = 'add' )
        self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
        
        self._edit = wx.Button( self._account_types_panel, label = 'edit' )
        self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
        
        self._delete = wx.Button( self._account_types_panel, label = 'delete' )
        self._delete.Bind( wx.EVT_BUTTON, self.EventDelete )
        
        self._apply = wx.Button( self, id = wx.ID_OK, label = 'apply' )
        self._apply.Bind( wx.EVT_BUTTON, self.EventOK )
        self._apply.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
        
        response = service.Request( HC.GET, 'account_types' )
        
        account_types = response[ 'account_types' ]
        
        self._titles_to_account_types = {}
        
        for account_type in account_types:
            
            title = account_type.GetTitle()
            
            self._titles_to_account_types[ title ] = account_type
            
            permissions = account_type.GetPermissions()
            
            permissions_string = ', '.join( [ HC.permissions_string_lookup[ permission ] for permission in permissions ] )
            
            max_num_bytes = account_type.GetMaxBytes()
            max_num_requests = account_type.GetMaxRequests()
            
            max_num_bytes_string = account_type.GetMaxBytesString()
            max_num_requests_string = account_type.GetMaxRequestsString()
            
            self._ctrl_account_types.Append( ( title, permissions_string, max_num_bytes_string, max_num_requests_string ), ( title, len( permissions ), max_num_bytes, max_num_requests ) )
            
        
        h_b_box = wx.BoxSizer( wx.HORIZONTAL )
        
        h_b_box.AddF( self._add, CC.FLAGS_MIXED )
        h_b_box.AddF( self._edit, CC.FLAGS_MIXED )
        h_b_box.AddF( self._delete, CC.FLAGS_MIXED )
        
        self._account_types_panel.AddF( self._ctrl_account_types, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._account_types_panel.AddF( h_b_box, CC.FLAGS_BUTTON_SIZER )
        
        b_box = wx.BoxSizer( wx.HORIZONTAL )
        b_box.AddF( self._apply, CC.FLAGS_MIXED )
        b_box.AddF( self._cancel, CC.FLAGS_MIXED )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        vbox.AddF( self._account_types_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( 980, y ) )
        
        wx.CallAfter( self._apply.SetFocus )
        
    
    def Delete( self ):
        
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
        
    
    def EventAdd( self, event ):
        
        with ClientGUIDialogs.DialogInputNewAccountType( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                account_type = dlg.GetAccountType()
                
                title = account_type.GetTitle()
                
                permissions = account_type.GetPermissions()
                
                permissions_string = ', '.join( [ HC.permissions_string_lookup[ permission ] for permission in permissions ] )
                
                max_num_bytes = account_type.GetMaxBytes()
                max_num_requests = account_type.GetMaxRequests()
                
                max_num_bytes_string = account_type.GetMaxBytesString()
                max_num_requests_string = account_type.GetMaxRequestsString()
                
                if title in self._titles_to_account_types: raise Exception( 'You already have an account type called ' + title + '; delete or edit that one first' )
                
                self._titles_to_account_types[ title ] = account_type
                
                self._edit_log.append( ( HC.ADD, account_type ) )
                
                self._ctrl_account_types.Append( ( title, permissions_string, max_num_bytes_string, max_num_requests_string ), ( title, len( permissions ), max_num_bytes, max_num_requests ) )
                
            
        
    
    def EventDelete( self, event ): self.Delete()
    
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
                    
                    max_num_bytes = account_type.GetMaxBytes()
                    max_num_requests = account_type.GetMaxRequests()
                    
                    max_num_bytes_string = account_type.GetMaxBytesString()
                    max_num_requests_string = account_type.GetMaxRequestsString()
                    
                    if old_title != title:
                        
                        if title in self._titles_to_account_types: raise Exception( 'You already have an account type called ' + title + '; delete or edit that one first' )
                        
                        del self._titles_to_account_types[ old_title ]
                        
                    
                    self._titles_to_account_types[ title ] = account_type
                    
                    self._edit_log.append( ( HC.EDIT, ( old_title, account_type ) ) )
                    
                    self._ctrl_account_types.UpdateRow( index, ( title, permissions_string, max_num_bytes_string, max_num_requests_string ), ( title, len( permissions ), max_num_bytes, max_num_requests ) )
                    
                
            
        
    
    def EventOK( self, event ):
        
        service = HydrusGlobals.client_controller.GetServicesManager().GetService( self._service_key )
        
        service.Request( HC.POST, 'account_types', { 'edit_log' : self._edit_log } )
        
        self.EndModal( wx.ID_OK )
        
    
class DialogManageBoorus( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._names_to_delete = []
            
            self._boorus = ClientGUICommon.ListBook( self )
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            self._add.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._remove = wx.Button( self, label = 'remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._export = wx.Button( self, label = 'export' )
            self._export.Bind( wx.EVT_BUTTON, self.EventExport )
            
            self._ok = wx.Button( self, id = wx.ID_OK,  label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            boorus = HydrusGlobals.client_controller.Read( 'remote_boorus' )
            
            for ( name, booru ) in boorus.items():
                
                self._boorus.AddPageArgs( name, self._Panel, ( self._boorus, booru ), {} )
                
            
        
        def ArrangeControls():
            
            add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
            add_remove_hbox.AddF( self._add, CC.FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, CC.FLAGS_MIXED )
            add_remove_hbox.AddF( self._export, CC.FLAGS_MIXED )
            
            ok_hbox = wx.BoxSizer( wx.HORIZONTAL )
            ok_hbox.AddF( self._ok, CC.FLAGS_MIXED )
            ok_hbox.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._boorus, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( add_remove_hbox, CC.FLAGS_SMALL_INDENT )
            vbox.AddF( ok_hbox, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage boorus' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self.SetDropTarget( ClientDragDrop.FileDropTarget( self.Import ) )
    
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( 980, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventAdd( self, event ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter new booru\'s name.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    name = dlg.GetValue()
                    
                    if self._boorus.NameExists( name ): raise HydrusExceptions.NameException( 'That name is already in use!' )
                    
                    if name == '': raise HydrusExceptions.NameException( 'Please enter a nickname for the service.' )
                    
                    booru = ClientData.Booru( name, 'search_url', '+', 1, 'thumbnail', '', 'original image', {} )
                    
                    page = self._Panel( self._boorus, booru, is_new = True )
                    
                    self._boorus.AddPage( name, page, select = True )
                    
                except HydrusExceptions.NameException as e:
                    
                    wx.MessageBox( str( e ) )
                    
                    self.EventAdd( event )
                    
                
            
        
    
    def EventExport( self, event ):
        
        booru_panel = self._boorus.GetCurrentPage()
        
        if booru_panel is not None:
            
            name = self._boorus.GetCurrentName()
            
            booru = booru_panel.GetBooru()
            
            with wx.FileDialog( self, 'select where to export booru', defaultFile = 'booru.yaml', style = wx.FD_SAVE ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    path = HydrusData.ToUnicode( dlg.GetPath() )
                    
                    with open( path, 'wb' ) as f: f.write( yaml.safe_dump( booru ) )
                    
                
            
        
    
    def EventOK( self, event ):
        
        try:
            
            for name in self._names_to_delete:
                
                HydrusGlobals.client_controller.Write( 'delete_remote_booru', name )
                
            
            for ( name, page ) in self._boorus.GetNamesToActivePages().items():
                
                if page.HasChanges():
                    
                    booru = page.GetBooru()
                    
                    HydrusGlobals.client_controller.Write( 'remote_booru', name, booru )
                    
                
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventRemove( self, event ):
        
        booru_panel = self._boorus.GetCurrentPage()
        
        if booru_panel is not None:
            
            name = self._boorus.GetCurrentName()
            
            self._names_to_delete.append( name )
            
            self._boorus.DeleteCurrentPage()
            
        
    
    def Import( self, paths ):
        
        for path in paths:
            
            try:
                
                with open( path, 'rb' ) as f: file = f.read()
                
                thing = yaml.safe_load( file )
                
                if type( thing ) == ClientData.Booru:
                    
                    booru = thing
                    
                    name = booru.GetName()
                    
                    if not self._boorus.NameExists( name ):
                        
                        new_booru = ClientData.Booru( name, 'search_url', '+', 1, 'thumbnail', '', 'original image', {} )
                        
                        page = self._Panel( self._boorus, new_booru, is_new = True )
                        
                        self._boorus.AddPage( name, page, select = True )
                        
                    
                    self._boorus.Select( name )
                    
                    page = self._boorus.GetNamesToActivePages()[ name ]
                    
                    page.Update( booru )
                    
                
            except:
                
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, booru, is_new = False ):
            
            wx.Panel.__init__( self, parent )
            
            self._booru = booru
            self._is_new = is_new
            
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
                
                self._tag_classnames_to_namespaces = wx.ListBox( self._tag_panel )
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
                
                gridbox.AddF( wx.StaticText( self._search_panel, label = 'search url' ), CC.FLAGS_MIXED )
                gridbox.AddF( self._search_url, CC.FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._search_panel, label = 'search tag separator' ), CC.FLAGS_MIXED )
                gridbox.AddF( self._search_separator, CC.FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._search_panel, label = 'advance by page num' ), CC.FLAGS_MIXED )
                gridbox.AddF( self._advance_by_page_num, CC.FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._search_panel, label = 'thumbnail classname' ), CC.FLAGS_MIXED )
                gridbox.AddF( self._thumb_classname, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                self._search_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                self._search_panel.AddF( self._example_html_search, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                #
                
                gridbox = wx.FlexGridSizer( 0, 2 )
                
                gridbox.AddGrowableCol( 1, 1 )
                
                gridbox.AddF( wx.StaticText( self._image_panel, label = 'text' ), CC.FLAGS_MIXED )
                gridbox.AddF( self._image_info, CC.FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._image_panel, label = 'id of <img>' ), CC.FLAGS_MIXED )
                gridbox.AddF( self._image_id, CC.FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._image_panel, label = 'text of <a>' ), CC.FLAGS_MIXED )
                gridbox.AddF( self._image_data, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                self._image_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                self._image_panel.AddF( self._example_html_image, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                #
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( self._tag_classname, CC.FLAGS_MIXED )
                hbox.AddF( self._namespace, CC.FLAGS_MIXED )
                hbox.AddF( self._add, CC.FLAGS_MIXED )
                
                self._tag_panel.AddF( self._tag_classnames_to_namespaces, CC.FLAGS_EXPAND_BOTH_WAYS )
                self._tag_panel.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                self._tag_panel.AddF( self._example_html_tags, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                #
                
                self._booru_panel.AddF( self._search_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._booru_panel.AddF( self._image_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._booru_panel.AddF( self._tag_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._booru_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                
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
            
            return ClientData.Booru( booru_name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
            
        
        def HasChanges( self ):
            
            if self._is_new: return True
            
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
            
        
    '''
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
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._edit_log = []
            
            ( identities, contacts, deletable_names ) = HydrusGlobals.client_controller.Read( 'identities_and_contacts' )
            
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
            add_remove_hbox.AddF( self._add_manually, CC.FLAGS_MIXED )
            add_remove_hbox.AddF( self._add_contact_address, CC.FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, CC.FLAGS_MIXED )
            add_remove_hbox.AddF( self._export, CC.FLAGS_MIXED )
            
            ok_hbox = wx.BoxSizer( wx.HORIZONTAL )
            ok_hbox.AddF( self._ok, CC.FLAGS_MIXED )
            ok_hbox.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._contacts, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( add_remove_hbox, CC.FLAGS_SMALL_INDENT )
            vbox.AddF( ok_hbox, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage contacts' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( 980, y ) )
        
        self.SetDropTarget( ClientDragDrop.FileDropTarget( self.Import ) )
        
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
            
            wx.MessageBox( HydrusData.ToUnicode( e ) )
            
            return
            
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter contact\'s address in the form contact_key@hostname:port.' ) as dlg:
            
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
            
            wx.MessageBox( HydrusData.ToUnicode( e ) )
            
            return
            
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter new contact\'s name.' ) as dlg:
            
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
                
            
        
    
    def EventContactChanged( self, event ):
        
        contact_panel = self._contacts.GetCurrentPage()
        
        if contact_panel is not None:
            
            old_name = contact_panel.GetOriginalName()
            
            if old_name in self._deletable_names: self._remove.Enable()
            else: self._remove.Disable()
            
        
    
    def EventContactChanging( self, event ):
        
        try: self._CheckCurrentContactIsValid()
        except Exception as e:
            
            wx.MessageBox( HydrusData.ToUnicode( e ) )
            
            event.Veto()
            
        
    
    def EventExport( self, event ):
        
        contact_panel = self._contacts.GetCurrentPage()
        
        if contact_panel is not None:
            
            name = self._contacts.GetCurrentName()
            
            contact = contact_panel.GetContact()
            
            try:
                
                with wx.FileDialog( self, 'select where to export contact', defaultFile = name + '.yaml', style = wx.FD_SAVE ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        path = HydrusData.ToUnicode( dlg.GetPath() )
                        
                        with open( path, 'wb' ) as f: f.write( yaml.safe_dump( contact ) )
                        
                    
                
            except:
                
                with wx.FileDialog( self, 'select where to export contact', defaultFile = 'contact.yaml', style = wx.FD_SAVE ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        path = HydrusData.ToUnicode( dlg.GetPath() )
                        
                        with open( path, 'wb' ) as f: f.write( yaml.safe_dump( contact ) )
                        
                    
                
            
        
    
    def EventOK( self, event ):
        
        try: self._CheckCurrentContactIsValid()
        except Exception as e:
            
            wx.MessageBox( HydrusData.ToUnicode( e ) )
            
            return
            
        
        for ( name, page ) in self._contacts.GetNamesToActivePages().items():
            
            if page.HasChanges(): self._edit_log.append( ( HC.EDIT, ( page.GetOriginalName(), page.GetContact() ) ) )
            
        
        try:
            
            if len( self._edit_log ) > 0: HydrusGlobals.client_controller.Write( 'update_contacts', self._edit_log )
            
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
            
            wx.MessageBox( HydrusData.ToUnicode( e ) )
            
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
                        
                        with ClientGUIDialogs.DialogYesNo( self, message, title = 'Please choose what to do.', yes_label = 'overwrite', no_label = 'make new' ) as dlg:
                            
                            if True:
                                
                                name_to_page_dict = self._contacts.GetNamesToActivePages()
                                
                                if name in name_to_page_dict: page = name_to_page_dict[ name ]
                                else: page = name_to_page_dict[ ' identities - ' + name ]
                                
                                page.Update( contact )
                                
                            else:
                                
                                while self._contacts.NameExists( name ) or self._contacts.NameExists( ' identities - ' + name ) or name == 'Anonymous': name = name + str( random.randint( 0, 9 ) )
                                
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
                
                contact_address = host + ':' + str( port )
                
                if contact_key is not None: contact_address = contact_key.encode( 'hex' ) + '@' + contact_address
                
                self._contact_address.SetValue( contact_address )
                
                if public_key is not None: self._public_key.SetValue( public_key )
                
            
            def ArrangeControls():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                gridbox = wx.FlexGridSizer( 0, 2 )
                
                gridbox.AddGrowableCol( 1, 1 )
                
                gridbox.AddF( wx.StaticText( self._contact_panel, label = 'name' ), CC.FLAGS_MIXED )
                gridbox.AddF( self._name, CC.FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._contact_panel, label = 'contact address' ), CC.FLAGS_MIXED )
                gridbox.AddF( self._contact_address, CC.FLAGS_EXPAND_BOTH_WAYS )
                gridbox.AddF( wx.StaticText( self._contact_panel, label = 'public key' ), CC.FLAGS_MIXED )
                gridbox.AddF( self._public_key, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                self._contact_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._contact_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                
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
            
            contact_address = host + ':' + str( port )
            
            if contact_key is not None: contact_address = contact_key.encode( 'hex' ) + '@' + contact_address
            
            self._contact_address.SetValue( contact_address )
            
            if public_key is None: public_key = ''
            
            self._public_key.SetValue( public_key )
            
        
    '''
class DialogManageExportFolders( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage export folders' )
        
        self._export_folders = ClientGUICommon.SaneListCtrl( self, 120, [ ( 'path', -1 ), ( 'type', 120 ), ( 'query', 120 ), ( 'period', 120 ), ( 'phrase', 120 ) ], delete_key_callback = self.Delete, use_display_tuple_for_sort = True )
        
        export_folders = HydrusGlobals.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
        
        self._original_paths = []
        
        for export_folder in export_folders:
            
            path = export_folder.GetName()
            
            self._original_paths.append( path )
            
            ( pretty_path, pretty_export_type, pretty_file_search_context, pretty_period, pretty_phrase ) = self._GetPrettyVariables( export_folder )
            
            self._export_folders.Append( ( pretty_path, pretty_export_type, pretty_file_search_context, pretty_period, pretty_phrase ), export_folder )
            
        
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
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        file_buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        file_buttons.AddF( self._add_button, CC.FLAGS_MIXED )
        file_buttons.AddF( self._edit_button, CC.FLAGS_MIXED )
        file_buttons.AddF( self._delete_button, CC.FLAGS_MIXED )
        
        buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        buttons.AddF( self._ok, CC.FLAGS_MIXED )
        buttons.AddF( self._cancel, CC.FLAGS_MIXED )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        intro = 'Here you can set the client to regularly export a certain query to a particular location.'
        
        vbox.AddF( wx.StaticText( self, label = intro ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._export_folders, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( file_buttons, CC.FLAGS_BUTTON_SIZER )
        vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        if x < 780: x = 780
        if y < 480: y = 480
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _AddFolder( self, path ):
        
        export_folders = self._export_folders.GetClientData()
        
        for export_folder in export_folders:
            
            existing_path = export_folder.GetName()
            
            test_path = os.path.join( path, '' )
            test_existing_path = os.path.join( existing_path, '' )
            
            if test_path == test_existing_path:
                
                text = 'That directory already exists as an export folder--at current, there can only be one export folder per destination.'
                
                wx.MessageBox( text )
                
                return
                
            
            if test_path.startswith( test_existing_path ):
                
                text = 'You have entered a subdirectory of an existing path--at current, this is not permitted.'
                
                wx.MessageBox( text )
                
                return
                
            
            if test_existing_path.startswith( test_path ):
                
                text = 'You have entered a parent directory of an existing path--at current, this is not permitted.'
                
                wx.MessageBox( text )
                
                return
                
            
        
        export_type = HC.EXPORT_FOLDER_TYPE_REGULAR
        file_search_context = ClientData.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY )
        period = 15 * 60
        phrase = '{hash}'
        
        export_folder = ClientFiles.ExportFolder( path, export_type = export_type, file_search_context = file_search_context, period = period, phrase = phrase )
        
        with DialogManageExportFoldersEdit( self, export_folder ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                export_folder = dlg.GetInfo()
                
                ( pretty_path, pretty_export_type, pretty_file_search_context, pretty_period, pretty_phrase ) = self._GetPrettyVariables( export_folder )
                
                self._export_folders.Append( ( pretty_path, pretty_export_type, pretty_file_search_context, pretty_period, pretty_phrase ), export_folder )
                
            
        
    
    def _GetPrettyVariables( self, export_folder ):
        
        ( path, export_type, file_search_context, period, phrase ) = export_folder.ToTuple()
        
        if export_type == HC.EXPORT_FOLDER_TYPE_REGULAR:
            
            pretty_export_type = 'regular'
            
        elif export_type == HC.EXPORT_FOLDER_TYPE_SYNCHRONISE:
            
            pretty_export_type = 'synchronise'
            
        
        pretty_file_search_context = ', '.join( predicate.GetUnicode( with_count = False ) for predicate in file_search_context.GetPredicates() )
        
        pretty_period = str( period / 60 ) + ' minutes'
        
        pretty_phrase = phrase
        
        return ( path, pretty_export_type, pretty_file_search_context, pretty_period, pretty_phrase )
        
    
    def Delete( self ): self._export_folders.RemoveAllSelected()
    
    def EventAdd( self, event ):
        
        with wx.DirDialog( self, 'Select a folder to add.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = HydrusData.ToUnicode( dlg.GetPath() )
                
                self._AddFolder( path )
                
            
        
    
    def EventDelete( self, event ): self.Delete()
    
    def EventEdit( self, event ):
        
        indices = self._export_folders.GetAllSelected()
        
        for index in indices:
            
            export_folder = self._export_folders.GetClientData( index )
            
            with DialogManageExportFoldersEdit( self, export_folder ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    export_folder = dlg.GetInfo()
                    
                    ( pretty_path, pretty_export_type, pretty_file_search_context, pretty_period, pretty_phrase ) = self._GetPrettyVariables( export_folder )
                    
                    self._export_folders.UpdateRow( index, ( pretty_path, pretty_export_type, pretty_file_search_context, pretty_period, pretty_phrase ), export_folder )
                    
                
            
        
    
    def EventOK( self, event ):
        
        client_data = self._export_folders.GetClientData()
        
        export_folders = []
        
        paths_set = set()
        
        for export_folder in client_data:
            
            HydrusGlobals.client_controller.Write( 'serialisable', export_folder )
            
            path = export_folder.GetName()
            
            paths_set.add( path )
            
        
        deletees = set( self._original_paths ) - paths_set
        
        for deletee in deletees:
            
            HydrusGlobals.client_controller.Write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER, deletee )
            
        
        HydrusGlobals.client_controller.pub( 'notify_new_export_folders' )
        
        self.EndModal( wx.ID_OK )
        
    
class DialogManageExportFoldersEdit( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, export_folder ):
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'edit export folder' )
        
        self._export_folder = export_folder
        
        ( path, export_type, file_search_context, period, phrase ) = self._export_folder.ToTuple()
        
        self._path_box = ClientGUICommon.StaticBox( self, 'export path' )
        
        self._path = wx.DirPickerCtrl( self._path_box, style = wx.DIRP_USE_TEXTCTRL )
        
        self._path.SetPath( path )
        
        #
        
        self._type_box = ClientGUICommon.StaticBox( self, 'type of export folder' )
        
        self._type = ClientGUICommon.BetterChoice( self._type_box )
        self._type.Append( 'regular', HC.EXPORT_FOLDER_TYPE_REGULAR )
        self._type.Append( 'synchronise', HC.EXPORT_FOLDER_TYPE_SYNCHRONISE )
        
        self._type.SelectClientData( export_type )
        
        #
        
        self._query_box = ClientGUICommon.StaticBox( self, 'query to export' )
        
        self._page_key = HydrusData.GenerateKey()
        
        predicates = file_search_context.GetPredicates()
        
        self._predicates_box = ClientGUICommon.ListBoxTagsPredicates( self._query_box, self._page_key, predicates )
        
        file_service_key = file_search_context.GetFileServiceKey()
        tag_service_key = file_search_context.GetTagServiceKey()
        include_current = file_search_context.IncludeCurrentTags()
        include_pending = file_search_context.IncludePendingTags()
        
        self._searchbox = ClientGUICommon.AutoCompleteDropdownTagsRead( self._query_box, self._page_key, file_service_key = file_service_key, tag_service_key = tag_service_key, include_current = include_current, include_pending = include_pending )
        
        #
        
        self._period_box = ClientGUICommon.StaticBox( self, 'export period (minutes)' )
        
        self._period = wx.SpinCtrl( self._period_box )
        
        self._period.SetRange( 3, 60 * 24 * 30 )
        
        self._period.SetValue( period / 60 )
        
        #
        
        self._phrase_box = ClientGUICommon.StaticBox( self, 'filenames' )
        
        self._pattern = wx.TextCtrl( self._phrase_box )
        
        self._pattern.SetValue( phrase )
        
        self._examples = ClientGUICommon.ExportPatternButton( self._phrase_box )
        
        #
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        self._path_box.AddF( self._path, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        text = '''regular - try to export the files to the directory, overwriting if the filesize if different

synchronise - try to export the files to the directory, overwriting if the filesize if different, and delete anything else in the directory

If you select synchronise, be careful!'''
        
        st = wx.StaticText( self._type_box, label = text )
        st.Wrap( 440 )
        
        self._type_box.AddF( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._type_box.AddF( self._type, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._query_box.AddF( self._predicates_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._query_box.AddF( self._searchbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._period_box.AddF( self._period, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        phrase_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        phrase_hbox.AddF( self._pattern, CC.FLAGS_EXPAND_BOTH_WAYS )
        phrase_hbox.AddF( self._examples, CC.FLAGS_MIXED )
        
        self._phrase_box.AddF( phrase_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        buttons.AddF( self._ok, CC.FLAGS_MIXED )
        buttons.AddF( self._cancel, CC.FLAGS_MIXED )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._path_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._type_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._query_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._period_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._phrase_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( 480, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
        
    
    def EventOK( self, event ):
        
        phrase = self._pattern.GetValue()
        
        try: ClientFiles.ParseExportPhrase( phrase )
        except:
            
            wx.MessageBox( 'Could not parse that export phrase!' )
            
            return
            
        
        self.EndModal( wx.ID_OK )
        
    
    def GetInfo( self ):
        
        path = HydrusData.ToUnicode( self._path.GetPath() )
        
        export_type = self._type.GetChoice()
        
        file_search_context = self._searchbox.GetFileSearchContext()
        
        predicates = self._predicates_box.GetPredicates()
        
        file_search_context.SetPredicates( predicates )
        
        period = self._period.GetValue() * 60
        
        phrase = self._pattern.GetValue()
        
        self._export_folder.SetTuple( path, export_type, file_search_context, period, phrase )
        
        return self._export_folder
        
    
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
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._names_to_delete = []
            
            sites = HydrusGlobals.client_controller.Read( 'imageboards' )
            
            for ( name, imageboards ) in sites.items():
                
                self._sites.AddPageArgs( name, self._Panel, ( self._sites, imageboards ), {} )
                
            
        
        def ArrangeControls():
            
            add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
            add_remove_hbox.AddF( self._add, CC.FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, CC.FLAGS_MIXED )
            add_remove_hbox.AddF( self._export, CC.FLAGS_MIXED )
            
            ok_hbox = wx.BoxSizer( wx.HORIZONTAL )
            ok_hbox.AddF( self._ok, CC.FLAGS_MIXED )
            ok_hbox.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._sites, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( add_remove_hbox, CC.FLAGS_SMALL_INDENT )
            vbox.AddF( ok_hbox, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage imageboards' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( 980, y ) )
        
        self.SetDropTarget( ClientDragDrop.FileDropTarget( self.Import ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventAdd( self, event ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter new site\'s name.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    name = dlg.GetValue()
                    
                    if self._sites.NameExists( name ): raise HydrusExceptions.NameException( 'That name is already in use!' )
                    
                    if name == '': raise HydrusExceptions.NameException( 'Please enter a nickname for the service.' )
                    
                    page = self._Panel( self._sites, [], is_new = True )
                    
                    self._sites.AddPage( name, page, select = True )
                    
                except HydrusExceptions.NameException as e:
                    
                    wx.MessageBox( str( e ) )
                    
                    self.EventAdd( event )
                    
                
            
        
    
    def EventExport( self, event ):
        
        site_panel = self._sites.GetCurrentPage()
        
        if site_panel is not None:
            
            name = self._sites.GetCurrentName()
            
            imageboards = site_panel.GetImageboards()
            
            dict = { name : imageboards }
            
            with wx.FileDialog( self, 'select where to export site', defaultFile = 'site.yaml', style = wx.FD_SAVE ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    path = HydrusData.ToUnicode( dlg.GetPath() )
                    
                    with open( path, 'wb' ) as f: f.write( yaml.safe_dump( dict ) )
                    
                
            
        
    
    def EventOK( self, event ):
        
        try:
            
            for name in self._names_to_delete:
                
                HydrusGlobals.client_controller.Write( 'delete_imageboard', name )
                
            
            for ( name, page ) in self._sites.GetNamesToActivePages().items():
                
                if page.HasChanges():
                    
                    imageboards = page.GetImageboards()
                    
                    HydrusGlobals.client_controller.Write( 'imageboard', name, imageboards )
                    
                
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventRemove( self, event ):
        
        site_panel = self._sites.GetCurrentPage()
        
        if site_panel is not None:
            
            name = self._sites.GetCurrentName()
            
            self._names_to_delete.append( name )
            
            self._sites.DeleteCurrentPage()
            
        
    
    def Import( self, paths ):
        
        for path in paths:
            
            try:
                
                with open( path, 'rb' ) as f: file = f.read()
                
                thing = yaml.safe_load( file )
                
                if type( thing ) == dict:
                    
                    ( name, imageboards ) = thing.items()[0]
                    
                    if not self._sites.NameExists( name ):
                        
                        page = self._Panel( self._sites, [], is_new = True )
                        
                        self._sites.AddPage( name, page, select = True )
                        
                    
                    page = self._sites.GetNamesToActivePages()[ name ]
                    
                    for imageboard in imageboards:
                        
                        if type( imageboard ) == ClientData.Imageboard: page.UpdateImageboard( imageboard )
                        
                    
                elif type( thing ) == ClientData.Imageboard:
                    
                    imageboard = thing
                    
                    page = self._sites.GetCurrentPage()
                    
                    page.UpdateImageboard( imageboard )
                    
                
            except:
                
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, imageboards, is_new = False ):
            
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
                
                for imageboard in imageboards:
                    
                    name = imageboard.GetName()
                    
                    self._imageboards.AddPageArgs( name, self._Panel, ( self._imageboards, imageboard ), {} )
                    
                
            
            def ArrangeControls():
                
                add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
                add_remove_hbox.AddF( self._add, CC.FLAGS_MIXED )
                add_remove_hbox.AddF( self._remove, CC.FLAGS_MIXED )
                add_remove_hbox.AddF( self._export, CC.FLAGS_MIXED )
                
                self._site_panel.AddF( self._imageboards, CC.FLAGS_EXPAND_BOTH_WAYS )
                self._site_panel.AddF( add_remove_hbox, CC.FLAGS_SMALL_INDENT )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._site_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                self.SetSizer( vbox )
                
            
            wx.Panel.__init__( self, parent )
            
            self._original_imageboards = imageboards
            self._has_changes = False
            self._is_new = is_new
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( 980, y ) )
            
        
        def EventAdd( self, event ):
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Enter new imageboard\'s name.' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    try:
                        
                        name = dlg.GetValue()
                        
                        if self._imageboards.NameExists( name ): raise HydrusExceptions.NameException()
                        
                        if name == '': raise Exception( 'Please enter a nickname for the service.' )
                        
                        imageboard = ClientData.Imageboard( name, '', 60, [], {} )
                        
                        page = self._Panel( self._imageboards, imageboard, is_new = True )
                        
                        self._imageboards.AddPage( name, page, select = True )
                        
                        self._has_changes = True
                        
                    except Exception as e:
                        
                        wx.MessageBox( HydrusData.ToUnicode( e ) )
                        
                        self.EventAdd( event )
                        
                    
                
            
        
        def EventExport( self, event ):
            
            imageboard_panel = self._imageboards.GetCurrentPage()
            
            if imageboard_panel is not None:
                
                imageboard = imageboard_panel.GetImageboard()
                
                with wx.FileDialog( self, 'select where to export imageboard', defaultFile = 'imageboard.yaml', style = wx.FD_SAVE ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        path = HydrusData.ToUnicode( dlg.GetPath() )
                        
                        with open( path, 'wb' ) as f: f.write( yaml.safe_dump( imageboard ) )
                        
                    
                
            
        
        def EventRemove( self, event ):
            
            imageboard_panel = self._imageboards.GetCurrentPage()
            
            if imageboard_panel is not None:
                
                name = self._imageboards.GetCurrentName()
                
                self._imageboards.DeleteCurrentPage()
                
                self._has_changes = True
                
            
        
        def GetImageboards( self ):
            
            current_names = self._imageboards.GetNames()
            
            names_to_imageboards = { imageboard.GetName() : imageboard for imageboard in self._original_imageboards if imageboard.GetName() in current_names }
            
            for page in self._imageboards.GetNamesToActivePages().values():
                
                imageboard = page.GetImageboard()
                
                names_to_imageboards[ imageboard.GetName() ] = imageboard
                
            
            return names_to_imageboards.values()
            
        
        def HasChanges( self ):
            
            if self._is_new: return True
            
            return self._has_changes or True in ( page.HasChanges() for page in self._imageboards.GetNamesToActivePages().values() )
            
        
        def UpdateImageboard( self, imageboard ):
            
            name = imageboard.GetName()
            
            if not self._imageboards.NameExists( name ):
                
                new_imageboard = ClientData.Imageboard( name, '', 60, [], {} )
                
                page = self._Panel( self._imageboards, new_imageboard, is_new = True )
                
                self._imageboards.AddPage( name, page, select = True )
                
            
            page = self._imageboards.GetNamesToActivePages()[ name ]
            
            page.Update( imageboard )
            
        
        class _Panel( wx.Panel ):
            
            def __init__( self, parent, imageboard, is_new = False ):
                
                wx.Panel.__init__( self, parent )
                
                self._imageboard = imageboard
                self._is_new = is_new
                
                ( post_url, flood_time, form_fields, restrictions ) = self._imageboard.GetBoardInfo()
                
                def InitialiseControls():
                    
                    self._imageboard_panel = ClientGUICommon.StaticBox( self, 'imageboard' )
                    
                    #
                    
                    self._basic_info_panel = ClientGUICommon.StaticBox( self._imageboard_panel, 'basic info' )
                    
                    self._post_url = wx.TextCtrl( self._basic_info_panel )
                    
                    self._flood_time = wx.SpinCtrl( self._basic_info_panel, min = 5, max = 1200 )
                    
                    #
                    
                    self._form_fields_panel = ClientGUICommon.StaticBox( self._imageboard_panel, 'form fields' )
                    
                    self._form_fields = ClientGUICommon.SaneListCtrl( self._form_fields_panel, 350, [ ( 'name', 120 ), ( 'type', 120 ), ( 'default', -1 ), ( 'editable', 120 ) ], delete_key_callback = self.Delete )
                    
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
                    
                    for ( name, field_type, default, editable ) in form_fields:
                        
                        self._form_fields.Append( ( name, CC.field_string_lookup[ field_type ], HydrusData.ToUnicode( default ), HydrusData.ToUnicode( editable ) ), ( name, field_type, default, editable ) )
                        
                    
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
                    
                    gridbox.AddF( wx.StaticText( self._basic_info_panel, label = 'POST URL' ), CC.FLAGS_MIXED )
                    gridbox.AddF( self._post_url, CC.FLAGS_EXPAND_BOTH_WAYS )
                    gridbox.AddF( wx.StaticText( self._basic_info_panel, label = 'flood time' ), CC.FLAGS_MIXED )
                    gridbox.AddF( self._flood_time, CC.FLAGS_EXPAND_BOTH_WAYS )
                    
                    self._basic_info_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                    
                    #
                    
                    h_b_box = wx.BoxSizer( wx.HORIZONTAL )
                    h_b_box.AddF( self._add, CC.FLAGS_MIXED )
                    h_b_box.AddF( self._edit, CC.FLAGS_MIXED )
                    h_b_box.AddF( self._delete, CC.FLAGS_MIXED )
                    
                    self._form_fields_panel.AddF( self._form_fields, CC.FLAGS_EXPAND_BOTH_WAYS )
                    self._form_fields_panel.AddF( h_b_box, CC.FLAGS_BUTTON_SIZER )
                    
                    #
                    
                    mime_buttons_box = wx.BoxSizer( wx.HORIZONTAL )
                    mime_buttons_box.AddF( self._mime_choice, CC.FLAGS_MIXED )
                    mime_buttons_box.AddF( self._add_mime, CC.FLAGS_MIXED )
                    mime_buttons_box.AddF( self._remove_mime, CC.FLAGS_MIXED )
                    
                    self._allowed_mimes_panel.AddF( self._mimes, CC.FLAGS_EXPAND_BOTH_WAYS )
                    self._allowed_mimes_panel.AddF( mime_buttons_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                    
                    self._restrictions_panel.AddF( self._min_resolution, CC.FLAGS_EXPAND_PERPENDICULAR )
                    self._restrictions_panel.AddF( self._max_resolution, CC.FLAGS_EXPAND_PERPENDICULAR )
                    self._restrictions_panel.AddF( self._max_file_size, CC.FLAGS_EXPAND_PERPENDICULAR )
                    self._restrictions_panel.AddF( self._allowed_mimes_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                    
                    #
                    
                    self._imageboard_panel.AddF( self._basic_info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                    self._imageboard_panel.AddF( self._form_fields_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                    self._imageboard_panel.AddF( self._restrictions_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                    
                    vbox = wx.BoxSizer( wx.VERTICAL )
                    
                    vbox.AddF( self._imageboard_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                    
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
                
            
            def Delete( self ): self._form_fields.RemoveAllSelected()
            
            def EventAdd( self, event ):
                
                with ClientGUIDialogs.DialogInputNewFormField( self ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        ( name, field_type, default, editable ) = dlg.GetFormField()
                        
                        if name in [ form_field[0] for form_field in self._form_fields.GetClientData() ]:
                            
                            wx.MessageBox( 'There is already a field named ' + name )
                            
                            self.EventAdd( event )
                            
                            return
                            
                        
                        self._form_fields.Append( ( name, CC.field_string_lookup[ field_type ], HydrusData.ToUnicode( default ), HydrusData.ToUnicode( editable ) ), ( name, field_type, default, editable ) )
                        
                    
                
            
            def EventAddMime( self, event ):
                
                selection = self._mime_choice.GetSelection()
                
                if selection != wx.NOT_FOUND:
                    
                    mime = self._mime_choice.GetClientData( selection )
                    
                    existing_mimes = [ self._mimes.GetClientData( i ) for i in range( self._mimes.GetCount() ) ]
                    
                    if mime not in existing_mimes: self._mimes.Append( HC.mime_string_lookup[ mime ], mime )
                    
                
            
            def EventDelete( self, event ): self.Delete()
            
            def EventRemoveMime( self, event ):
                
                selection = self._mimes.GetSelection()
                
                if selection != wx.NOT_FOUND: self._mimes.Delete( selection )
                
            
            def EventEdit( self, event ):
                
                indices = self._form_fields.GetAllSelected()
                
                for index in indices:
                    
                    ( name, field_type, default, editable ) = self._form_fields.GetClientData( index )
                    
                    form_field = ( name, field_type, default, editable )
                    
                    with ClientGUIDialogs.DialogInputNewFormField( self, form_field ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            old_name = name
                            
                            ( name, field_type, default, editable ) = dlg.GetFormField()
                            
                            if old_name != name:
                                
                                if name in [ form_field[0] for form_field in self._form_fields.GetClientData() ]: raise Exception( 'You already have a form field called ' + name + '; delete or edit that one first' )
                                
                            
                            self._form_fields.UpdateRow( index, ( name, CC.field_string_lookup[ field_type ], HydrusData.ToUnicode( default ), HydrusData.ToUnicode( editable ) ), ( name, field_type, default, editable ) )
                            
                        
                    
                
            
            def GetImageboard( self ):
                
                ( name, post_url, flood_time, form_fields, restrictions ) = self._GetInfo()
                
                return ClientData.Imageboard( name, post_url, flood_time, form_fields, restrictions )
                
            
            def HasChanges( self ):
                
                if self._is_new: return True
                
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
                
                for ( name, field_type, default, editable ) in form_fields:
                    
                    self._form_fields.Append( ( name, CC.field_string_lookup[ field_type ], HydrusData.ToUnicode( default ), HydrusData.ToUnicode( editable ) ), ( name, field_type, default, editable ) )
                    
                
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
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage import folders' )
        
        self._import_folders = ClientGUICommon.SaneListCtrl( self, 120, [ ( 'name', 120 ), ( 'path', -1 ), ( 'check period', 120 ) ], delete_key_callback = self.Delete )
        
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
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        self._names_to_import_folders = {}
        
        import_folders = HydrusGlobals.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
        
        for import_folder in import_folders:
            
            ( name, path, check_period ) = import_folder.ToListBoxTuple()
            
            pretty_check_period = self._GetPrettyVariables( check_period )
            
            self._import_folders.Append( ( name, path, pretty_check_period ), ( name, path, check_period ) )
            
            self._names_to_import_folders[ name ] = import_folder
            
        
        #
        
        file_buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        file_buttons.AddF( self._add_button, CC.FLAGS_MIXED )
        file_buttons.AddF( self._edit_button, CC.FLAGS_MIXED )
        file_buttons.AddF( self._delete_button, CC.FLAGS_MIXED )
        
        buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        buttons.AddF( self._ok, CC.FLAGS_MIXED )
        buttons.AddF( self._cancel, CC.FLAGS_MIXED )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        intro = 'Here you can set the client to regularly check certain folders for new files to import.'
        
        vbox.AddF( wx.StaticText( self, label = intro ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._import_folders, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( file_buttons, CC.FLAGS_BUTTON_SIZER )
        vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        #
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        if x < 780: x = 780
        if y < 480: y = 480
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _AddImportFolder( self, name ):
        
        if name not in self._names_to_import_folders:
            
            import_folder = ClientImporting.ImportFolder( name )
            
            with DialogManageImportFoldersEdit( self, import_folder ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    import_folder = dlg.GetInfo()
                    
                    ( name, path, check_period ) = import_folder.ToListBoxTuple()
                    
                    pretty_check_period = self._GetPrettyVariables( check_period )
                    
                    self._import_folders.Append( ( name, path, pretty_check_period ), ( name, path, check_period ) )
                    
                    self._names_to_import_folders[ name ] = import_folder
                    
                
            
        
    
    def _GetPrettyVariables( self, check_period ):
        
        pretty_check_period = str( check_period / 60 ) + ' minutes'
        
        return pretty_check_period
        
    
    def Delete( self ):
        
        self._import_folders.RemoveAllSelected()
        
    
    def EventAdd( self, event ):
        
        client_data = self._import_folders.GetClientData()
        
        existing_names = set()
        
        for ( name, path, check_period ) in client_data:
            
            existing_names.add( name )
            
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter a name for the import folder.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    name = dlg.GetValue()
                    
                    if name in existing_names: raise HydrusExceptions.NameException( 'That name is already in use!' )
                    
                    if name == '': raise HydrusExceptions.NameException( 'Please enter a nickname for the import folder.' )
                    
                    self._AddImportFolder( name )
                    
                except HydrusExceptions.NameException as e:
                    
                    wx.MessageBox( str( e ) )
                    
                    self.EventAdd( event )
                    
                
            
        
    
    def EventDelete( self, event ):
        
        self.Delete()
        
    
    def EventEdit( self, event ):
        
        indices = self._import_folders.GetAllSelected()
        
        for index in indices:
            
            ( name, path, check_period ) = self._import_folders.GetClientData( index )
            
            import_folder = self._names_to_import_folders[ name ]
            
            with DialogManageImportFoldersEdit( self, import_folder ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    import_folder = dlg.GetInfo()
                    
                    ( name, path, check_period ) = import_folder.ToListBoxTuple()
                    
                    pretty_check_period = self._GetPrettyVariables( check_period )
                    
                    self._import_folders.UpdateRow( index, ( name, path, pretty_check_period ), ( name, path, check_period ) )
                    
                    self._names_to_import_folders[ name ] = import_folder
                    
                
            
        
    
    def EventOK( self, event ):
        
        client_data = self._import_folders.GetClientData()
        
        names_to_save = set()
        
        for ( name, path, check_period ) in client_data:
            
            names_to_save.add( name )
            
        
        names_to_delete = { name for name in self._names_to_import_folders if name not in names_to_save }
        
        for name in names_to_delete:
            
            HydrusGlobals.client_controller.Write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER, name )
            
        
        for name in names_to_save:
            
            import_folder = self._names_to_import_folders[ name ]
            
            HydrusGlobals.client_controller.Write( 'serialisable', import_folder )
            
        
        HydrusGlobals.client_controller.pub( 'notify_new_import_folders' )
        
        self.EndModal( wx.ID_OK )
        
    
class DialogManageImportFoldersEdit( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, import_folder ):
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'edit import folder' )
        
        self._import_folder = import_folder
        
        ( name, path, mimes, import_file_options, import_tag_options, actions, action_locations, period, open_popup, paused ) = self._import_folder.ToTuple()
        
        self._folder_box = ClientGUICommon.StaticBox( self, 'folder options' )
        
        self._name = wx.TextCtrl( self._folder_box )
        
        self._path = wx.DirPickerCtrl( self._folder_box, style = wx.DIRP_USE_TEXTCTRL )
        
        self._open_popup = wx.CheckBox( self._folder_box )
        
        self._period = wx.SpinCtrl( self._folder_box, min = 3, max = 60 * 24 * 30 )
        
        self._paused = wx.CheckBox( self._folder_box )
        
        self._seed_cache_button = wx.BitmapButton( self._folder_box, bitmap = CC.GlobalBMPs.seed_cache )
        self._seed_cache_button.Bind( wx.EVT_BUTTON, self.EventSeedCache )
        self._seed_cache_button.SetToolTipString( 'open detailed file import status' )
        
        #
        
        self._file_box = ClientGUICommon.StaticBox( self, 'file options' )
        
        self._mimes = ClientGUIOptionsPanels.OptionsPanelMimes( self._file_box, HC.ALLOWED_MIMES )
        
        def create_choice():
            
            choice = ClientGUICommon.BetterChoice( self._file_box )
            
            for if_id in ( CC.IMPORT_FOLDER_DELETE, CC.IMPORT_FOLDER_IGNORE, CC.IMPORT_FOLDER_MOVE ):
                
                choice.Append( CC.import_folder_string_lookup[ if_id ], if_id )
                
            
            choice.Bind( wx.EVT_CHOICE, self.EventCheckLocations )
            
            return choice
            
        
        self._action_successful = create_choice()
        self._location_successful = wx.DirPickerCtrl( self._file_box, style = wx.DIRP_USE_TEXTCTRL )
        
        self._action_redundant = create_choice()
        self._location_redundant = wx.DirPickerCtrl( self._file_box, style = wx.DIRP_USE_TEXTCTRL )
        
        self._action_deleted = create_choice()
        self._location_deleted = wx.DirPickerCtrl( self._file_box, style = wx.DIRP_USE_TEXTCTRL )
        
        self._action_failed = create_choice()
        self._location_failed = wx.DirPickerCtrl( self._file_box, style = wx.DIRP_USE_TEXTCTRL )
        
        self._import_file_options = ClientGUIOptionsPanels.OptionsPanelImportFiles( self._file_box )
        self._import_tag_options = ClientGUIOptionsPanels.OptionsPanelTags( self._file_box )
        self._import_tag_options.SetNamespaces( [] )
        
        #
        
        self._ok = wx.Button( self, label = 'ok' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        self._name.SetValue( name )
        self._path.SetPath( path )
        self._open_popup.SetValue( open_popup )
        
        self._period.SetValue( period / 60 )
        self._paused.SetValue( paused )
        
        self._mimes.SetInfo( mimes )
        
        self._action_successful.SelectClientData( actions[ CC.STATUS_SUCCESSFUL ] )
        if CC.STATUS_SUCCESSFUL in action_locations:
            
            self._location_successful.SetPath( action_locations[ CC.STATUS_SUCCESSFUL ] )
            
        
        self._action_redundant.SelectClientData( actions[ CC.STATUS_REDUNDANT ] )
        if CC.STATUS_REDUNDANT in action_locations:
            
            self._location_redundant.SetPath( action_locations[ CC.STATUS_REDUNDANT ] )
            
        
        self._action_deleted.SelectClientData( actions[ CC.STATUS_DELETED ] )
        if CC.STATUS_DELETED in action_locations:
            
            self._location_deleted.SetPath( action_locations[ CC.STATUS_DELETED ] )
            
        
        self._action_failed.SelectClientData( actions[ CC.STATUS_FAILED ] )
        if CC.STATUS_FAILED in action_locations:
            
            self._location_failed.SetPath( action_locations[ CC.STATUS_FAILED ] )
            
        
        self._import_file_options.SetOptions( import_file_options )
        self._import_tag_options.SetOptions( import_tag_options )
        
        #
        
        gridbox = wx.FlexGridSizer( 0, 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        gridbox.AddF( wx.StaticText( self._folder_box, label = 'name: '), CC.FLAGS_MIXED )
        gridbox.AddF( self._name, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self._folder_box, label = 'folder path: '), CC.FLAGS_MIXED )
        gridbox.AddF( self._path, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self._folder_box, label = 'check period (mins): '), CC.FLAGS_MIXED )
        gridbox.AddF( self._period, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self._folder_box, label = 'currently paused: '), CC.FLAGS_MIXED )
        gridbox.AddF( self._paused, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self._folder_box, label = 'open a popup if new files imported: '), CC.FLAGS_MIXED )
        gridbox.AddF( self._open_popup, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self._folder_box, label = 'review currently cached import paths: '), CC.FLAGS_MIXED )
        gridbox.AddF( self._seed_cache_button, CC.FLAGS_MIXED )
        
        self._folder_box.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        gridbox = wx.FlexGridSizer( 0, 3 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        gridbox.AddF( wx.StaticText( self._file_box, label = 'mimes to import: '), CC.FLAGS_MIXED )
        gridbox.AddF( self._mimes, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.AddF( ( 20, 20 ), CC.FLAGS_NONE )
        
        gridbox.AddF( wx.StaticText( self._file_box, label = 'when a file imports successfully: '), CC.FLAGS_MIXED )
        gridbox.AddF( self._action_successful, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.AddF( self._location_successful, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self._file_box, label = 'when a file is already in the db: '), CC.FLAGS_MIXED )
        gridbox.AddF( self._action_redundant, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.AddF( self._location_redundant, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self._file_box, label = 'when a file has already been deleted from the db: '), CC.FLAGS_MIXED )
        gridbox.AddF( self._action_deleted, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.AddF( self._location_deleted, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        gridbox.AddF( wx.StaticText( self._file_box, label = 'when a file fails to import: '), CC.FLAGS_MIXED )
        gridbox.AddF( self._action_failed, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.AddF( self._location_failed, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._file_box.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._file_box.AddF( self._import_file_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._file_box.AddF( self._import_tag_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        buttons.AddF( self._ok, CC.FLAGS_MIXED )
        buttons.AddF( self._cancel, CC.FLAGS_MIXED )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._folder_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._file_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( 720, x )
        
        self.SetInitialSize( ( x, y ) )
        
        self._CheckLocations()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _CheckLocations( self ):
        
        if self._action_successful.GetChoice() == CC.IMPORT_FOLDER_MOVE:
            
            self._location_successful.Enable()
            
        else:
            
            self._location_successful.Disable()
            
        
        if self._action_redundant.GetChoice() == CC.IMPORT_FOLDER_MOVE:
            
            self._location_redundant.Enable()
            
        else:
            
            self._location_redundant.Disable()
            
        
        if self._action_deleted.GetChoice() == CC.IMPORT_FOLDER_MOVE:
            
            self._location_deleted.Enable()
            
        else:
            
            self._location_deleted.Disable()
            
        
        if self._action_failed.GetChoice() == CC.IMPORT_FOLDER_MOVE:
            
            self._location_failed.Enable()
            
        else:
            
            self._location_failed.Disable()
            
        
    
    def EventCheckLocations( self, event ):
        
        self._CheckLocations()
        
    
    def EventOK( self, event ):
        
        if self._path.GetPath() in ( '', None ):
            
            wx.MessageBox( 'You must enter a folder path to import from!' )
            
            return
            
        
        if self._action_successful.GetChoice() == CC.IMPORT_FOLDER_MOVE and self._location_successful.GetPath() in ( '', None ):
            
            wx.MessageBox( 'You must enter a path for your successful file move location!' )
            
            return
            
        
        if self._action_redundant.GetChoice() == CC.IMPORT_FOLDER_MOVE and self._location_redundant.GetPath() in ( '', None ):
            
            wx.MessageBox( 'You must enter a path for your redundant file move location!' )
            
            return
            
        
        if self._action_deleted.GetChoice() == CC.IMPORT_FOLDER_MOVE and self._location_deleted.GetPath() in ( '', None ):
            
            wx.MessageBox( 'You must enter a path for your deleted file move location!' )
            
            return
            
        
        if self._action_failed.GetChoice() == CC.IMPORT_FOLDER_MOVE and self._location_failed.GetPath() in ( '', None ):
            
            wx.MessageBox( 'You must enter a path for your failed file move location!' )
            
            return
            
        
        self.EndModal( wx.ID_OK )
        
    
    def EventSeedCache( self, event ):
        
        seed_cache = self._import_folder.GetSeedCache()
        
        HydrusGlobals.client_controller.pub( 'show_seed_cache', seed_cache )
        
    
    def GetInfo( self ):
        
        name = self._name.GetValue()
        path = HydrusData.ToUnicode( self._path.GetPath() )
        mimes = self._mimes.GetInfo()
        import_file_options = self._import_file_options.GetOptions()
        import_tag_options = self._import_tag_options.GetOptions()
        
        actions = {}
        action_locations = {}
        
        actions[ CC.STATUS_SUCCESSFUL ] = self._action_successful.GetChoice()
        if actions[ CC.STATUS_SUCCESSFUL ] == CC.IMPORT_FOLDER_MOVE:
            
            action_locations[ CC.STATUS_SUCCESSFUL ] = HydrusData.ToUnicode( self._location_successful.GetPath() )
            
        
        actions[ CC.STATUS_REDUNDANT ] = self._action_redundant.GetChoice()
        if actions[ CC.STATUS_REDUNDANT ] == CC.IMPORT_FOLDER_MOVE:
            
            action_locations[ CC.STATUS_REDUNDANT ] = HydrusData.ToUnicode( self._location_redundant.GetPath() )
            
        
        actions[ CC.STATUS_DELETED ] = self._action_deleted.GetChoice()
        if actions[ CC.STATUS_DELETED] == CC.IMPORT_FOLDER_MOVE:
            
            action_locations[ CC.STATUS_DELETED ] = HydrusData.ToUnicode( self._location_deleted.GetPath() )
            
        
        actions[ CC.STATUS_FAILED ] = self._action_failed.GetChoice()
        if actions[ CC.STATUS_FAILED ] == CC.IMPORT_FOLDER_MOVE:
            
            action_locations[ CC.STATUS_FAILED ] = HydrusData.ToUnicode( self._location_failed.GetPath() )
            
        
        period = self._period.GetValue() * 60
        open_popup = self._open_popup.GetValue()
        
        paused = self._paused.GetValue()
        
        self._import_folder.SetTuple( name, path, mimes, import_file_options, import_tag_options, actions, action_locations, period, open_popup, paused )
        
        return self._import_folder
        
    
class DialogManageOptions( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage options' )
        
        self._new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        self._listbook = ClientGUICommon.ListBook( self )
        
        self._listbook.AddPage( 'connection', self._ConnectionPanel( self._listbook ) )
        self._listbook.AddPage( 'files and trash', self._FilesAndTrashPanel( self._listbook ) )
        self._listbook.AddPage( 'speed and memory', self._SpeedAndMemoryPanel( self._listbook ) )
        self._listbook.AddPage( 'maintenance and processing', self._MaintenanceAndProcessingPanel( self._listbook ) )
        self._listbook.AddPage( 'media', self._MediaPanel( self._listbook ) )
        self._listbook.AddPage( 'gui', self._GUIPanel( self._listbook ) )
        #self._listbook.AddPage( 'sound', self._SoundPanel( self._listbook ) )
        self._listbook.AddPage( 'default file system predicates', self._DefaultFileSystemPredicatesPanel( self._listbook ) )
        self._listbook.AddPage( 'default tag import options', self._DefaultTagImportOptionsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'colours', self._ColoursPanel( self._listbook ) )
        self._listbook.AddPage( 'local server', self._ServerPanel( self._listbook ) )
        self._listbook.AddPage( 'sort/collect', self._SortCollectPanel( self._listbook ) )
        self._listbook.AddPage( 'shortcuts', self._ShortcutsPanel( self._listbook ) )
        self._listbook.AddPage( 'downloading', self._DownloadingPanel( self._listbook ) )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'Save' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        buttons.AddF( self._ok, CC.FLAGS_SMALL_INDENT )
        buttons.AddF( self._cancel, CC.FLAGS_SMALL_INDENT )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._listbook, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( 800, x )
        y = max( 800, y )
        
        self.SetInitialSize( ( x, y ) )
        
        #
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    class _ColoursPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._gui_colours = {}
            
            for ( name, rgb ) in HC.options[ 'gui_colours' ].items():
                
                ctrl = wx.ColourPickerCtrl( self )
                
                ctrl.SetMaxSize( ( 20, -1 ) )
                
                self._gui_colours[ name ] = ctrl
                
            
            self._namespace_colours = ClientGUICommon.ListBoxTagsColourOptions( self, HC.options[ 'namespace_colours' ] )
            
            self._edit_namespace_colour = wx.Button( self, label = 'edit selected' )
            self._edit_namespace_colour.Bind( wx.EVT_BUTTON, self.EventEditNamespaceColour )
            
            self._new_namespace_colour = wx.TextCtrl( self, style = wx.TE_PROCESS_ENTER )
            self._new_namespace_colour.Bind( wx.EVT_KEY_DOWN, self.EventKeyDownNamespace )
            
            #
            
            for ( name, rgb ) in HC.options[ 'gui_colours' ].items(): self._gui_colours[ name ].SetColour( wx.Colour( *rgb ) )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddF( wx.StaticText( self, label = 'thumbnail background (local: normal/selected, remote: normal/selected): ' ), CC.FLAGS_MIXED )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._gui_colours[ 'thumb_background' ], CC.FLAGS_MIXED )
            hbox.AddF( self._gui_colours[ 'thumb_background_selected' ], CC.FLAGS_MIXED )
            hbox.AddF( self._gui_colours[ 'thumb_background_remote' ], CC.FLAGS_MIXED )
            hbox.AddF( self._gui_colours[ 'thumb_background_remote_selected' ], CC.FLAGS_MIXED )
            
            gridbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            gridbox.AddF( wx.StaticText( self, label = 'thumbnail border (local: normal/selected, remote: normal/selected): ' ), CC.FLAGS_MIXED )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._gui_colours[ 'thumb_border' ], CC.FLAGS_MIXED )
            hbox.AddF( self._gui_colours[ 'thumb_border_selected' ], CC.FLAGS_MIXED )
            hbox.AddF( self._gui_colours[ 'thumb_border_remote' ], CC.FLAGS_MIXED )
            hbox.AddF( self._gui_colours[ 'thumb_border_remote_selected' ], CC.FLAGS_MIXED )
            
            gridbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            gridbox.AddF( wx.StaticText( self, label = 'thumbnail grid background: '), CC.FLAGS_MIXED )
            gridbox.AddF( self._gui_colours[ 'thumbgrid_background' ], CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'autocomplete background: '), CC.FLAGS_MIXED )
            gridbox.AddF( self._gui_colours[ 'autocomplete_background' ], CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'media viewer background: '), CC.FLAGS_MIXED )
            gridbox.AddF( self._gui_colours[ 'media_background' ], CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'media viewer text: '), CC.FLAGS_MIXED )
            gridbox.AddF( self._gui_colours[ 'media_text' ], CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'tags box background: '), CC.FLAGS_MIXED )
            gridbox.AddF( self._gui_colours[ 'tags_box' ], CC.FLAGS_MIXED )
            
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._namespace_colours, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._new_namespace_colour, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._edit_namespace_colour, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def EventEditNamespaceColour( self, event ):
            
            results = self._namespace_colours.GetSelectedNamespaceColours()
            
            for ( namespace, colour ) in results:
                
                colour_data = wx.ColourData()
                
                colour_data.SetColour( colour )
                colour_data.SetChooseFull( True )
                
                with wx.ColourDialog( self, data = colour_data ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        colour_data = dlg.GetColourData()
                        
                        colour = colour_data.GetColour()
                        
                        self._namespace_colours.SetNamespaceColour( namespace, colour )
                        
                    
                
            
        
        def EventKeyDownNamespace( self, event ):
            
            if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
                
                namespace = self._new_namespace_colour.GetValue()
                
                if namespace != '':
                    
                    self._namespace_colours.SetNamespaceColour( namespace, wx.Colour( random.randint( 0, 255 ), random.randint( 0, 255 ), random.randint( 0, 255 ) ) )
                    
                    self._new_namespace_colour.SetValue( '' )
                    
                
            else: event.Skip()
            
        
        def UpdateOptions( self ):
            
            for ( name, ctrl ) in self._gui_colours.items():
                
                colour = ctrl.GetColour()
                
                rgb = ( colour.Red(), colour.Green(), colour.Blue() )
                
                HC.options[ 'gui_colours' ][ name ] = rgb
                
            
            HC.options[ 'namespace_colours' ] = self._namespace_colours.GetNamespaceColours()
            
        
    
    class _ConnectionPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._external_host = wx.TextCtrl( self )
            self._external_host.SetToolTipString( 'If you have trouble parsing your external ip using UPnP, you can force it to be this.' )
            
            proxy_panel = ClientGUICommon.StaticBox( self, 'proxy settings' )
            
            self._proxy_type = ClientGUICommon.BetterChoice( proxy_panel )
            
            self._proxy_address = wx.TextCtrl( proxy_panel )
            self._proxy_port = wx.SpinCtrl( proxy_panel, min = 0, max = 65535 )
            
            self._proxy_username = wx.TextCtrl( proxy_panel )
            self._proxy_password = wx.TextCtrl( proxy_panel )
            
            #
            
            if HC.options[ 'external_host' ] is not None:
                
                self._external_host.SetValue( HC.options[ 'external_host' ] )
                
            
            self._proxy_type.Append( 'http', 'http' )
            self._proxy_type.Append( 'socks4', 'socks4' )
            self._proxy_type.Append( 'socks5', 'socks5' )
            
            if HC.options[ 'proxy' ] is not None:
                
                ( proxytype, host, port, username, password ) = HC.options[ 'proxy' ]
                
                self._proxy_type.SelectClientData( proxytype )
                
                self._proxy_address.SetValue( host )
                self._proxy_port.SetValue( port )
                
                if username is not None:
                    
                    self._proxy_username.SetValue( username )
                    
                
                if password is not None:
                    
                    self._proxy_password.SetValue( password )
                    
                
            else:
                
                self._proxy_type.Select( 0 )
                
            
            #
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( proxy_panel, label = 'Proxy type: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._proxy_type, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( proxy_panel, label = 'Address: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._proxy_address, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( proxy_panel, label = 'Port: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._proxy_port, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( proxy_panel, label = 'Username (optional): ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._proxy_username, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( proxy_panel, label = 'Password (optional): ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._proxy_password, CC.FLAGS_MIXED )
            
            text = 'You have to restart the client for proxy settings to take effect.'
            text += os.linesep
            text += 'This is in a buggy prototype stage right now, pending a rewrite of the networking engine.'
            text += os.linesep
            text += 'Please send me your feedback.'
            
            proxy_panel.AddF( wx.StaticText( proxy_panel, label = text ), CC.FLAGS_EXPAND_PERPENDICULAR )
            proxy_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label = 'External IP/host override: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._external_host, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( proxy_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            if self._proxy_address.GetValue() == '':
                
                HC.options[ 'proxy' ] = None
                
            else:
                
                proxytype = self._proxy_type.GetChoice()
                address = self._proxy_address.GetValue()
                port = self._proxy_port.GetValue()
                username = self._proxy_username.GetValue()
                password = self._proxy_password.GetValue()
                
                if username == '': username = None
                if password == '': password = None
                
                HC.options[ 'proxy' ] = ( proxytype, address, port, username, password )
                
            
            external_host = self._external_host.GetValue()
            
            if external_host == '':
                
                external_host = None
                
            
            HC.options[ 'external_host' ] = external_host
            
        
    
    class _DownloadingPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            general = ClientGUICommon.StaticBox( self, 'general' )
            
            self._website_download_polite_wait = wx.SpinCtrl( general, min = 1, max = 30 )
            
            #
            
            gallery_downloader = ClientGUICommon.StaticBox( self, 'gallery downloader' )
            
            self._gallery_file_limit = ClientGUICommon.NoneableSpinCtrl( gallery_downloader, 'default file limit', none_phrase = 'no limit', min = 1, max = 1000000 )
            
            #
            
            thread_checker = ClientGUICommon.StaticBox( self, 'thread checker' )
            
            self._thread_times_to_check = wx.SpinCtrl( thread_checker, min = 0, max = 100 )
            self._thread_times_to_check.SetToolTipString( 'how many times the thread checker will check' )
            
            self._thread_check_period = wx.SpinCtrl( thread_checker, min = 30, max = 86400 )
            self._thread_check_period.SetToolTipString( 'how long the checker will wait between checks' )
            
            #
            
            self._website_download_polite_wait.SetValue( HC.options[ 'website_download_polite_wait' ] )
            
            self._gallery_file_limit.SetValue( HC.options[ 'gallery_file_limit' ] )
            
            ( times_to_check, check_period ) = HC.options[ 'thread_checker_timings' ]
            
            self._thread_times_to_check.SetValue( times_to_check )
            
            self._thread_check_period.SetValue( check_period )
            
            #
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( general, label = 'seconds to politely wait between gallery/thread url requests: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._website_download_polite_wait, CC.FLAGS_MIXED )
            
            general.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            gallery_downloader.AddF( self._gallery_file_limit, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( thread_checker, label = 'default number of times to check: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._thread_times_to_check, CC.FLAGS_MIXED )
            gridbox.AddF( wx.StaticText( thread_checker, label = 'default wait in seconds between checks: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._thread_check_period, CC.FLAGS_MIXED )
            
            thread_checker.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( general, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( gallery_downloader, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( thread_checker, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'website_download_polite_wait' ] = self._website_download_polite_wait.GetValue()
            HC.options[ 'gallery_file_limit' ] = self._gallery_file_limit.GetValue()
            HC.options[ 'thread_checker_timings' ] = ( self._thread_times_to_check.GetValue(), self._thread_check_period.GetValue() )
            
        
    
    class _MaintenanceAndProcessingPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._idle_panel = ClientGUICommon.StaticBox( self, 'when to run big jobs' )
            self._maintenance_panel = ClientGUICommon.StaticBox( self, 'maintenance period' )
            self._processing_panel = ClientGUICommon.StaticBox( self, 'processing' )
            
            self._idle_period = wx.SpinCtrl( self._idle_panel, min = 0, max = 1000 )
            self._idle_mouse_period = wx.SpinCtrl( self._idle_panel, min = 0, max = 1000 )
            self._idle_cpu_max = wx.SpinCtrl( self._idle_panel, min = 0, max = 100 )
            
            self._idle_shutdown = ClientGUICommon.BetterChoice( self._idle_panel )
            
            for idle_id in ( CC.IDLE_NOT_ON_SHUTDOWN, CC.IDLE_ON_SHUTDOWN, CC.IDLE_ON_SHUTDOWN_ASK_FIRST ):
                
                self._idle_shutdown.Append( CC.idle_string_lookup[ idle_id ], idle_id )
                
            
            self._idle_shutdown_max_minutes = wx.SpinCtrl( self._idle_panel, min = 1, max = 1440 )
            
            self._maintenance_vacuum_period = wx.SpinCtrl( self._maintenance_panel, min = 0, max = 365 )
            
            self._processing_phase = wx.SpinCtrl( self._processing_panel, min = 0, max = 100000 )
            self._processing_phase.SetToolTipString( 'how long this client will delay processing updates after they are due. useful if you have multiple clients and do not want them to process at the same time' )
            
            #
            
            self._idle_period.SetValue( HC.options[ 'idle_period' ] / 60 )
            self._idle_mouse_period.SetValue( HC.options[ 'idle_mouse_period' ] / 60 )
            self._idle_cpu_max.SetValue( HC.options[ 'idle_cpu_max' ] )
            self._idle_shutdown.SelectClientData( HC.options[ 'idle_shutdown' ] )
            self._idle_shutdown_max_minutes.SetValue( HC.options[ 'idle_shutdown_max_minutes' ] )
            
            self._maintenance_vacuum_period.SetValue( HC.options[ 'maintenance_vacuum_period' ] / 86400 )
            
            self._processing_phase.SetValue( HC.options[ 'processing_phase' ] )
            
            #
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self._idle_panel, label = 'Minutes of general client inactivity until client can be considered idle: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._idle_period, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._idle_panel, label = 'Minutes of unmoving mouse until client can be considered idle: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._idle_mouse_period, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._idle_panel, label = 'Do not start a job if any CPU core has more than this percent usage: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._idle_cpu_max, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._idle_panel, label = 'Run jobs on shutdown?: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._idle_shutdown, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self._idle_panel, label = 'Max number of minutes to run shutdown jobs: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._idle_shutdown_max_minutes, CC.FLAGS_MIXED )
            
            text = 'CPU-heavy jobs like maintenance routines and repository synchronisation processing will only start by themselves when you are not using the client.'
            text += os.linesep * 2
            text += 'If you set both client inactivy and unmoving mouse to 0, the client will never consider itself idle and you should set up shutdown processing.'
            
            st = wx.StaticText( self._idle_panel, label = text )
            
            st.Wrap( 400 )
            
            self._idle_panel.AddF( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._idle_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self._maintenance_panel, label = 'Number of days to wait between vacuums (0 for never): ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._maintenance_vacuum_period, CC.FLAGS_MIXED )
            
            self._maintenance_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self._processing_panel, label = 'Delay update processing by (s): ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._processing_phase, CC.FLAGS_MIXED )
            
            self._processing_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._idle_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._maintenance_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._processing_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'idle_period' ] = 60 * self._idle_period.GetValue()
            HC.options[ 'idle_mouse_period' ] = 60 * self._idle_mouse_period.GetValue()
            HC.options[ 'idle_cpu_max' ] = self._idle_cpu_max.GetValue()
            HC.options[ 'idle_shutdown' ] = self._idle_shutdown.GetChoice()
            HC.options[ 'idle_shutdown_max_minutes' ] = self._idle_shutdown_max_minutes.GetValue()
            
            HC.options[ 'maintenance_vacuum_period' ] = 86400 * self._maintenance_vacuum_period.GetValue()
            
            HC.options[ 'processing_phase' ] = self._processing_phase.GetValue()
            
        
    
    class _DefaultFileSystemPredicatesPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._file_system_predicate_age = ClientGUIPredicates.PanelPredicateSystemAge( self )
            self._file_system_predicate_duration = ClientGUIPredicates.PanelPredicateSystemDuration( self )
            self._file_system_predicate_height = ClientGUIPredicates.PanelPredicateSystemHeight( self )
            self._file_system_predicate_limit = ClientGUIPredicates.PanelPredicateSystemLimit( self )
            self._file_system_predicate_mime = ClientGUIPredicates.PanelPredicateSystemMime( self )
            self._file_system_predicate_num_pixels = ClientGUIPredicates.PanelPredicateSystemNumPixels( self )
            self._file_system_predicate_num_tags = ClientGUIPredicates.PanelPredicateSystemNumTags( self )
            self._file_system_predicate_num_words = ClientGUIPredicates.PanelPredicateSystemNumWords( self )
            self._file_system_predicate_ratio = ClientGUIPredicates.PanelPredicateSystemRatio( self )
            self._file_system_predicate_similar_to = ClientGUIPredicates.PanelPredicateSystemSimilarTo( self )
            self._file_system_predicate_size = ClientGUIPredicates.PanelPredicateSystemSize( self )
            self._file_system_predicate_width = ClientGUIPredicates.PanelPredicateSystemWidth( self )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._file_system_predicate_age, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_duration, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_height, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_limit, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_mime, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_num_pixels, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_num_tags, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_num_words, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_ratio, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_similar_to, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_size, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_width, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            system_predicates = HC.options[ 'file_system_predicates' ]
            
            system_predicates[ 'age' ] = self._file_system_predicate_age.GetInfo()
            system_predicates[ 'duration' ] = self._file_system_predicate_duration.GetInfo()
            system_predicates[ 'hamming_distance' ] = self._file_system_predicate_similar_to.GetInfo()[1]
            system_predicates[ 'height' ] = self._file_system_predicate_height.GetInfo()
            system_predicates[ 'limit' ] = self._file_system_predicate_limit.GetInfo()
            system_predicates[ 'mime' ] = self._file_system_predicate_mime.GetInfo()
            system_predicates[ 'num_pixels' ] = self._file_system_predicate_num_pixels.GetInfo()
            system_predicates[ 'num_tags' ] = self._file_system_predicate_num_tags.GetInfo()
            system_predicates[ 'num_words' ] = self._file_system_predicate_num_words.GetInfo()
            system_predicates[ 'ratio' ] = self._file_system_predicate_ratio.GetInfo()
            system_predicates[ 'size' ] = self._file_system_predicate_size.GetInfo()
            system_predicates[ 'width' ] = self._file_system_predicate_width.GetInfo()
            
            HC.options[ 'file_system_predicates' ] = system_predicates
            
        
    
    class _DefaultTagImportOptionsPanel( wx.Panel ):
        
        def __init__( self, parent, new_options ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = new_options
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._import_tag_options = wx.ListBox( self )
            self._import_tag_options.Bind( wx.EVT_LEFT_DCLICK, self.EventDelete )
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            
            self._edit = wx.Button( self, label = 'edit' )
            self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
            
            self._delete = wx.Button( self, label = 'delete' )
            self._delete.Bind( wx.EVT_BUTTON, self.EventDelete )
            
            #
            
            for ( gallery_identifier, import_tag_options ) in self._new_options.GetDefaultImportTagOptions().items():
                
                name = gallery_identifier.ToString()
                
                self._import_tag_options.Append( name, ( gallery_identifier, import_tag_options ) )
                
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._import_tag_options, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._add, CC.FLAGS_BUTTON_SIZER )
            hbox.AddF( self._edit, CC.FLAGS_BUTTON_SIZER )
            hbox.AddF( self._delete, CC.FLAGS_BUTTON_SIZER )
            
            vbox.AddF( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def EventAdd( self, event ):
            
            gallery_identifiers = []
            
            for site_type in [ HC.SITE_TYPE_DEFAULT, HC.SITE_TYPE_DEVIANT_ART, HC.SITE_TYPE_GIPHY, HC.SITE_TYPE_HENTAI_FOUNDRY, HC.SITE_TYPE_NEWGROUNDS, HC.SITE_TYPE_PIXIV, HC.SITE_TYPE_TUMBLR ]:
                
                gallery_identifiers.append( ClientDownloading.GalleryIdentifier( site_type ) )
                
            
            gallery_identifiers.append( ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_BOORU ) )
            
            boorus = HydrusGlobals.client_controller.Read( 'remote_boorus' )
            
            for booru_name in boorus.keys():
                
                gallery_identifiers.append( ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_BOORU, additional_info = booru_name ) )
                
            
            ordered_names = [ gallery_identifier.ToString() for gallery_identifier in gallery_identifiers ]
            
            names_to_gallery_identifiers = { gallery_identifier.ToString() : gallery_identifier for gallery_identifier in gallery_identifiers }
            
            with ClientGUIDialogs.DialogSelectFromListOfStrings( self, 'select tag domain', ordered_names ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    name = dlg.GetString()
                    
                    for i in range( self._import_tag_options.GetCount() ):
                        
                        if name == self._import_tag_options.GetString( i ):
                            
                            wx.MessageBox( 'You already have default tag import options set up for that domain!' )
                            
                            return
                            
                        
                    
                    gallery_identifier = names_to_gallery_identifiers[ name ]
                    
                    with ClientGUIDialogs.DialogInputImportTagOptions( self, name, gallery_identifier ) as ito_dlg:
                        
                        if ito_dlg.ShowModal() == wx.ID_OK:
                            
                            import_tag_options = ito_dlg.GetImportTagOptions()
                            
                            self._import_tag_options.Append( name, ( gallery_identifier, import_tag_options ) )
                            
                        
                    
                
            
        
        def EventDelete( self, event ):
            
            selection = self._import_tag_options.GetSelection()
            
            if selection != wx.NOT_FOUND: self._import_tag_options.Delete( selection )
            
        
        def EventEdit( self, event ):
            
            selection = self._import_tag_options.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                name = self._import_tag_options.GetString( selection )
                
                ( gallery_identifier, import_tag_options ) = self._import_tag_options.GetClientData( selection )
                
                with ClientGUIDialogs.DialogInputImportTagOptions( self, name, gallery_identifier, import_tag_options ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        import_tag_options = dlg.GetImportTagOptions()
                        
                        self._import_tag_options.SetClientData( selection, ( gallery_identifier, import_tag_options ) )
                        
                    
                
            
        
        def UpdateOptions( self ):
            
            self._new_options.ClearDefaultImportTagOptions()
            
            for ( gallery_identifier, import_tag_options ) in [ self._import_tag_options.GetClientData( i ) for i in range( self._import_tag_options.GetCount() ) ]:
                
                self._new_options.SetDefaultImportTagOptions( gallery_identifier, import_tag_options )
                
            
        
    
    class _FilesAndTrashPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._export_location = wx.DirPickerCtrl( self, style = wx.DIRP_USE_TEXTCTRL )
            
            self._delete_to_recycle_bin = wx.CheckBox( self, label = '' )
            self._exclude_deleted_files = wx.CheckBox( self, label = '' )
            
            self._remove_filtered_files = wx.CheckBox( self, label = '' )
            self._remove_trashed_files = wx.CheckBox( self, label = '' )
            
            self._trash_max_age = ClientGUICommon.NoneableSpinCtrl( self, '', none_phrase = 'no age limit', min = 0, max = 8640 )
            self._trash_max_size = ClientGUICommon.NoneableSpinCtrl( self, '', none_phrase = 'no size limit', min = 0, max = 20480 )
            
            #
            
            if HC.options[ 'export_path' ] is not None:
                
                abs_path = HydrusData.ConvertPortablePathToAbsPath( HC.options[ 'export_path' ] )
                
                if abs_path is not None: self._export_location.SetPath( abs_path )
                
            
            self._delete_to_recycle_bin.SetValue( HC.options[ 'delete_to_recycle_bin' ] )
            self._exclude_deleted_files.SetValue( HC.options[ 'exclude_deleted_files' ] )
            self._remove_filtered_files.SetValue( HC.options[ 'remove_filtered_files' ] )
            self._remove_trashed_files.SetValue( HC.options[ 'remove_trashed_files' ] )
            self._trash_max_age.SetValue( HC.options[ 'trash_max_age' ] )
            self._trash_max_size.SetValue( HC.options[ 'trash_max_size' ] )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label = 'Default export directory: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._export_location, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            gridbox.AddF( wx.StaticText( self, label = 'When deleting files or folders, send them to the OS\'s recycle bin: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._delete_to_recycle_bin, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'By default, do not reimport files that have been previously deleted: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._exclude_deleted_files, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Remove files from view when they are filtered: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._remove_filtered_files, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Remove files from view when they are sent to the trash: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._remove_trashed_files, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Number of hours a file can be in the trash before being deleted: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._trash_max_age, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Maximum size of trash (MB): ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._trash_max_size, CC.FLAGS_MIXED )
            
            text = 'If you set the default export directory blank, the client will use \'hydrus_export\' under the current user\'s home directory.'
            
            vbox.AddF( wx.StaticText( self, label = text ), CC.FLAGS_CENTER )
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'export_path' ] = HydrusPaths.ConvertAbsPathToPortablePath( HydrusData.ToUnicode( self._export_location.GetPath() ) )
            
            HC.options[ 'delete_to_recycle_bin' ] = self._delete_to_recycle_bin.GetValue()
            HC.options[ 'exclude_deleted_files' ] = self._exclude_deleted_files.GetValue()
            HC.options[ 'remove_filtered_files' ] = self._remove_filtered_files.GetValue()
            HC.options[ 'remove_trashed_files' ] = self._remove_trashed_files.GetValue()
            HC.options[ 'trash_max_age' ] = self._trash_max_age.GetValue()
            HC.options[ 'trash_max_size' ] = self._trash_max_size.GetValue()
            
        
    
    class _GUIPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._default_gui_session = wx.Choice( self )
            
            self._confirm_client_exit = wx.CheckBox( self )
            self._confirm_trash = wx.CheckBox( self )
            self._confirm_archive = wx.CheckBox( self )
            
            self._always_embed_autocompletes = wx.CheckBox( self )
            
            self._gui_capitalisation = wx.CheckBox( self )
            
            self._gui_show_all_tags_in_autocomplete = wx.CheckBox( self )
            
            self._default_tag_sort = wx.Choice( self )
            
            self._default_tag_sort.Append( 'lexicographic (a-z)', CC.SORT_BY_LEXICOGRAPHIC_ASC )
            self._default_tag_sort.Append( 'lexicographic (z-a)', CC.SORT_BY_LEXICOGRAPHIC_DESC )
            self._default_tag_sort.Append( 'incidence (desc)', CC.SORT_BY_INCIDENCE_DESC )
            self._default_tag_sort.Append( 'incidence (asc)', CC.SORT_BY_INCIDENCE_ASC )
            
            self._default_tag_repository = ClientGUICommon.BetterChoice( self )
            
            self._tag_dialog_size = wx.CheckBox( self )
            self._tag_dialog_position = wx.CheckBox( self )
            self._rating_dialog_position = wx.CheckBox( self )
            self._hide_preview = wx.CheckBox( self )
            
            #
            
            gui_session_names = HydrusGlobals.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
            
            if 'last session' not in gui_session_names: gui_session_names.insert( 0, 'last session' )
            
            self._default_gui_session.Append( 'just a blank page', None )
            
            for name in gui_session_names: self._default_gui_session.Append( name, name )
            
            try: self._default_gui_session.SetStringSelection( HC.options[ 'default_gui_session' ] )
            except: self._default_gui_session.SetSelection( 0 )
            
            self._confirm_client_exit.SetValue( HC.options[ 'confirm_client_exit' ] )
            
            self._confirm_trash.SetValue( HC.options[ 'confirm_trash' ] )
            
            self._confirm_archive.SetValue( HC.options[ 'confirm_archive' ] )
            
            self._always_embed_autocompletes.SetValue( HC.options[ 'always_embed_autocompletes' ] )
            
            self._gui_capitalisation.SetValue( HC.options[ 'gui_capitalisation' ] )
            
            self._gui_show_all_tags_in_autocomplete.SetValue( HC.options[ 'show_all_tags_in_autocomplete' ] )
            
            if HC.options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_ASC: self._default_tag_sort.Select( 0 )
            elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_DESC: self._default_tag_sort.Select( 1 )
            elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_DESC: self._default_tag_sort.Select( 2 )
            elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_ASC: self._default_tag_sort.Select( 3 )
            
            services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ) )
            
            for service in services: self._default_tag_repository.Append( service.GetName(), service.GetServiceKey() )
            
            default_tag_repository_key = HC.options[ 'default_tag_repository' ]
            
            self._default_tag_repository.SelectClientData( default_tag_repository_key )
            
            ( remember, size ) = HC.options[ 'tag_dialog_size' ]
            
            self._tag_dialog_size.SetValue( remember )
            
            ( remember, position ) = HC.options[ 'tag_dialog_position' ]
            
            self._tag_dialog_position.SetValue( remember )
            
            ( remember, position ) = HC.options[ 'rating_dialog_position' ]
            
            self._rating_dialog_position.SetValue( remember )
            
            self._hide_preview.SetValue( HC.options[ 'hide_preview' ] )
            
            #
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label = 'Default session on startup:' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._default_gui_session, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Confirm client exit:' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._confirm_client_exit, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Confirm sending files to trash:' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._confirm_trash, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Confirm sending more than one file to archive or inbox:' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._confirm_archive, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Always embed autocomplete dropdown results window:' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._always_embed_autocompletes, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Default tag service in manage tag dialogs:' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._default_tag_repository, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Default tag sort:' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._default_tag_sort, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Capitalise gui: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._gui_capitalisation, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'By default, search non-local tags in write-autocomplete: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._gui_show_all_tags_in_autocomplete, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Remember manage tags dialog size: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._tag_dialog_size, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Remember manage tags dialog position: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._tag_dialog_position, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Remember manage ratings dialog position: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._rating_dialog_position, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Hide the preview window: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._hide_preview, CC.FLAGS_MIXED )
            
            self.SetSizer( gridbox )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'default_gui_session' ] = self._default_gui_session.GetStringSelection()
            HC.options[ 'confirm_client_exit' ] = self._confirm_client_exit.GetValue()
            HC.options[ 'confirm_trash' ] = self._confirm_trash.GetValue()
            HC.options[ 'confirm_archive' ] = self._confirm_archive.GetValue()
            HC.options[ 'always_embed_autocompletes' ] = self._always_embed_autocompletes.GetValue()
            HC.options[ 'gui_capitalisation' ] = self._gui_capitalisation.GetValue()
            HC.options[ 'show_all_tags_in_autocomplete' ] = self._gui_show_all_tags_in_autocomplete.GetValue()
            HC.options[ 'default_tag_repository' ] = self._default_tag_repository.GetChoice()
            HC.options[ 'default_tag_sort' ] = self._default_tag_sort.GetClientData( self._default_tag_sort.GetSelection() )
            
            ( remember, size ) = HC.options[ 'tag_dialog_size' ]
            
            remember = self._tag_dialog_size.GetValue()
            
            if remember:
                
                HC.options[ 'tag_dialog_size' ] = ( remember, size )
                
            else:
                
                HC.options[ 'tag_dialog_size' ] = ( remember, None )
                
            
            ( remember, position ) = HC.options[ 'tag_dialog_position' ]
            
            remember = self._tag_dialog_position.GetValue()
            
            if remember:
                
                HC.options[ 'tag_dialog_position' ] = ( remember, position )
                
            else:
                
                HC.options[ 'tag_dialog_position' ] = ( remember, None )
                
            
            ( remember, position ) = HC.options[ 'rating_dialog_position' ]
            
            remember = self._rating_dialog_position.GetValue()
            
            if remember:
                
                HC.options[ 'rating_dialog_position' ] = ( remember, position )
                
            else:
                
                HC.options[ 'rating_dialog_position' ] = ( remember, None )
                
            
            HC.options[ 'hide_preview' ] = self._hide_preview.GetValue()
            
        
    
    class _MediaPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._fit_to_canvas = wx.CheckBox( self, label = '' )
            self._animation_start_position = wx.SpinCtrl( self, min = 0, max = 100 )
            
            self._mime_media_viewer_panel = ClientGUICommon.StaticBox( self, 'media viewer mime handling' )
            
            self._mime_media_viewer_actions = {}
            
            mimes_in_correct_order = ( HC.IMAGE_JPEG, HC.IMAGE_PNG, HC.IMAGE_GIF, HC.APPLICATION_FLASH, HC.APPLICATION_PDF, HC.VIDEO_FLV, HC.VIDEO_MP4, HC.VIDEO_MKV, HC.VIDEO_WEBM, HC.VIDEO_WMV, HC.AUDIO_MP3, HC.AUDIO_OGG, HC.AUDIO_FLAC, HC.AUDIO_WMA )
            
            for mime in mimes_in_correct_order:
                
                dropdown = ClientGUICommon.BetterChoice( self._mime_media_viewer_panel )
                
                for action in CC.media_viewer_capabilities[ mime ]:
                    
                    dropdown.Append( CC.media_viewer_action_string_lookup[ action ], action )
                    
                
                current_action = HC.options[ 'mime_media_viewer_actions' ][ mime ]
                
                dropdown.SelectClientData( current_action )
                
                self._mime_media_viewer_actions[ mime ] = dropdown
                
            
            #
            
            self._fit_to_canvas.SetValue( HC.options[ 'fit_to_canvas' ] )
            self._animation_start_position.SetValue( int( HC.options[ 'animation_start_position' ] * 100.0 ) )
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            for mime in mimes_in_correct_order:
                
                gridbox.AddF( wx.StaticText( self._mime_media_viewer_panel, label = HC.mime_string_lookup[ mime ] ), CC.FLAGS_MIXED )
                gridbox.AddF( self._mime_media_viewer_actions[ mime ], CC.FLAGS_MIXED )
                
            
            self._mime_media_viewer_panel.AddF( gridbox, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label = 'Zoom smaller media to fit media canvas: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._fit_to_canvas, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Start animations this % in: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._animation_start_position, CC.FLAGS_MIXED )
            
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._mime_media_viewer_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'fit_to_canvas' ] = self._fit_to_canvas.GetValue()
            HC.options[ 'animation_start_position' ] = float( self._animation_start_position.GetValue() ) / 100.0
            
            mime_media_viewer_actions = {}
            
            for ( mime, dropdown ) in self._mime_media_viewer_actions.items():
                
                mime_media_viewer_actions[ mime ] = dropdown.GetChoice()
                
            
            HC.options[ 'mime_media_viewer_actions' ] = mime_media_viewer_actions
            
        
    
    class _ServerPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._local_port = wx.SpinCtrl( self, min = 0, max = 65535 )
            
            #
            
            self._local_port.SetValue( HC.options[ 'local_port' ] )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self, label = 'local server port: ' ), CC.FLAGS_MIXED )
            hbox.AddF( self._local_port, CC.FLAGS_MIXED )
            
            vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            new_local_port = self._local_port.GetValue()
            
            if new_local_port != HC.options[ 'local_port' ]: HydrusGlobals.client_controller.pub( 'restart_server' )
            
            HC.options[ 'local_port' ] = new_local_port
            
        
    
    class _ShortcutsPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._shortcuts = ClientGUICommon.SaneListCtrl( self, 480, [ ( 'modifier', 120 ), ( 'key', 120 ), ( 'action', -1 ) ], delete_key_callback = self.DeleteShortcuts )
            
            self._shortcuts_add = wx.Button( self, label = 'add' )
            self._shortcuts_add.Bind( wx.EVT_BUTTON, self.EventAdd )
            
            self._shortcuts_edit = wx.Button( self, label = 'edit' )
            self._shortcuts_edit.Bind( wx.EVT_BUTTON, self.EventEdit )
            
            self._shortcuts_delete = wx.Button( self, label = 'delete' )
            self._shortcuts_delete.Bind( wx.EVT_BUTTON, self.EventDelete )
            
            #
            
            for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items():
                
                for ( key, action ) in key_dict.items():
                    
                    ( pretty_modifier, pretty_key ) = ClientData.ConvertShortcutToPrettyShortcut( modifier, key )
                    
                    pretty_action = action
                    
                    self._shortcuts.Append( ( pretty_modifier, pretty_key, pretty_action ), ( modifier, key, action ) )
                    
                
            
            self._SortListCtrl()
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( wx.StaticText( self, label = 'These shortcuts are global to the main gui! You probably want to stick to function keys or ctrl + something!' ), CC.FLAGS_MIXED )
            vbox.AddF( self._shortcuts, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._shortcuts_add, CC.FLAGS_BUTTON_SIZER )
            hbox.AddF( self._shortcuts_edit, CC.FLAGS_BUTTON_SIZER )
            hbox.AddF( self._shortcuts_delete, CC.FLAGS_BUTTON_SIZER )
            
            vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def _SortListCtrl( self ): self._shortcuts.SortListItems( 2 )
        
        def DeleteShortcuts( self ):
            
            self._shortcuts.RemoveAllSelected()
            
        
        def EventAdd( self, event ):
            
            with ClientGUIDialogs.DialogInputShortcut( self ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( modifier, key, action ) = dlg.GetInfo()
                    
                    ( pretty_modifier, pretty_key ) = ClientData.ConvertShortcutToPrettyShortcut( modifier, key )
                    
                    pretty_action = action
                    
                    self._shortcuts.Append( ( pretty_modifier, pretty_key, pretty_action ), ( modifier, key, action ) )
                    
                    self._SortListCtrl()
                    
                
            
        
        def EventDelete( self, event ):
            
            self.DeleteShortcuts()
            
        
        def EventEdit( self, event ):
            
            indices = self._shortcuts.GetAllSelected()
            
            for index in indices:
                
                ( modifier, key, action ) = self._shortcuts.GetClientData( index )
                
                with ClientGUIDialogs.DialogInputShortcut( self, modifier, key, action ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        ( modifier, key, action ) = dlg.GetInfo()
                        
                        ( pretty_modifier, pretty_key ) = ClientData.ConvertShortcutToPrettyShortcut( modifier, key )
                        
                        pretty_action = action
                        
                        self._shortcuts.UpdateRow( index, ( pretty_modifier, pretty_key, pretty_action ), ( modifier, key, action ) )
                        
                        self._SortListCtrl()
                        
                    
                
            
        
        def UpdateOptions( self ):
            
            shortcuts = {}
            
            shortcuts[ wx.ACCEL_NORMAL ] = {}
            shortcuts[ wx.ACCEL_CTRL ] = {}
            shortcuts[ wx.ACCEL_ALT ] = {}
            shortcuts[ wx.ACCEL_SHIFT ] = {}
            
            for ( modifier, key, action ) in self._shortcuts.GetClientData(): shortcuts[ modifier ][ key ] = action
            
            HC.options[ 'shortcuts' ] = shortcuts
            
        
    
    class _SortCollectPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._default_sort = ClientGUICommon.ChoiceSort( self, sort_by = HC.options[ 'sort_by' ] )
            
            self._default_collect = ClientGUICommon.CheckboxCollect( self )
            
            self._sort_by = wx.ListBox( self )
            self._sort_by.Bind( wx.EVT_LEFT_DCLICK, self.EventRemoveSortBy )
            
            self._new_sort_by = wx.TextCtrl( self, style = wx.TE_PROCESS_ENTER )
            self._new_sort_by.Bind( wx.EVT_KEY_DOWN, self.EventKeyDownSortBy )
            
            #
            
            for ( sort_by_type, sort_by ) in HC.options[ 'sort_by' ]: self._sort_by.Append( '-'.join( sort_by ), sort_by )
            
            #
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label = 'default sort: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._default_sort, CC.FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( wx.StaticText( self, label = 'default collect: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._default_collect, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            sort_by_text = 'You can manage new namespace sorting schemes here.'
            sort_by_text += os.linesep
            sort_by_text += 'The client will sort media by comparing their namespaces, moving from left to right until an inequality is found.'
            sort_by_text += os.linesep
            sort_by_text += 'Any changes will be shown in the sort-by dropdowns of any new pages you open.'
            
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( wx.StaticText( self, label = sort_by_text ), CC.FLAGS_MIXED )
            vbox.AddF( self._sort_by, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._new_sort_by, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
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
            
        
        def EventRemoveSortBy( self, event ):
            
            selection = self._sort_by.GetSelection()
            
            if selection != wx.NOT_FOUND: self._sort_by.Delete( selection )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'default_sort' ] = self._default_sort.GetSelection() 
            HC.options[ 'default_collect' ] = self._default_collect.GetChoice()
            
            sort_by_choices = []
            
            for sort_by in [ self._sort_by.GetClientData( i ) for i in range( self._sort_by.GetCount() ) ]: sort_by_choices.append( ( 'namespaces', sort_by ) )
            
            HC.options[ 'sort_by' ] = sort_by_choices
            
        
    
    class _SoundPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._play_dumper_noises = wx.CheckBox( self, label = 'play success/fail noises when dumping' )
            
            #
            
            self._play_dumper_noises.SetValue( HC.options[ 'play_dumper_noises' ] )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._play_dumper_noises, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'play_dumper_noises' ] = self._play_dumper_noises.GetValue()
            
        
    
    class _SpeedAndMemoryPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._thumbnail_width = wx.SpinCtrl( self, min = 20, max = 200 )
            self._thumbnail_width.Bind( wx.EVT_SPINCTRL, self.EventThumbnailsUpdate )
            
            self._thumbnail_height = wx.SpinCtrl( self, min = 20, max = 200 )
            self._thumbnail_height.Bind( wx.EVT_SPINCTRL, self.EventThumbnailsUpdate )
            
            self._thumbnail_cache_size = wx.SpinCtrl( self, min = 5, max = 3000 )
            self._thumbnail_cache_size.Bind( wx.EVT_SPINCTRL, self.EventThumbnailsUpdate )
            
            self._estimated_number_thumbnails = wx.StaticText( self, label = '' )
            
            self._preview_cache_size = wx.SpinCtrl( self, min = 5, max = 3000 )
            self._preview_cache_size.Bind( wx.EVT_SPINCTRL, self.EventPreviewsUpdate )
            
            self._estimated_number_previews = wx.StaticText( self, label = '' )
            
            self._fullscreen_cache_size = wx.SpinCtrl( self, min = 25, max = 3000 )
            self._fullscreen_cache_size.Bind( wx.EVT_SPINCTRL, self.EventFullscreensUpdate )
            
            self._estimated_number_fullscreens = wx.StaticText( self, label = '' )
            
            self._num_autocomplete_chars = wx.SpinCtrl( self, min = 1, max = 100 )
            self._num_autocomplete_chars.SetToolTipString( 'how many characters you enter before the gui fetches autocomplete results from the db' + os.linesep + 'increase this if you find autocomplete results are slow' )
            
            self._autocomplete_long_wait = wx.SpinCtrl( self, min = 0, max = 10000 )
            self._autocomplete_long_wait.SetToolTipString( 'how long the gui will wait, after you enter a character, before it queries the db with what you have entered so far' )
            
            self._autocomplete_short_wait_chars = wx.SpinCtrl( self, min = 1, max = 100 )
            self._autocomplete_short_wait_chars.SetToolTipString( 'how many characters you enter before the gui starts waiting the short time before querying the db' )
            
            self._autocomplete_short_wait = wx.SpinCtrl( self, min = 0, max = 10000 )
            self._autocomplete_short_wait.SetToolTipString( 'how long the gui will wait, after you enter a lot of characters, before it queries the db with what you have entered so far' )
            
            #
            
            ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
            
            self._thumbnail_width.SetValue( thumbnail_width )
            
            self._thumbnail_height.SetValue( thumbnail_height )
            
            self._thumbnail_cache_size.SetValue( int( HC.options[ 'thumbnail_cache_size' ] / 1048576 ) )
            
            self._preview_cache_size.SetValue( int( HC.options[ 'preview_cache_size' ] / 1048576 ) )
            
            self._fullscreen_cache_size.SetValue( int( HC.options[ 'fullscreen_cache_size' ] / 1048576 ) )
            
            self._num_autocomplete_chars.SetValue( HC.options[ 'num_autocomplete_chars' ] )
            
            ( char_limit, long_wait, short_wait ) = HC.options[ 'ac_timings' ]
            
            self._autocomplete_long_wait.SetValue( long_wait )
            
            self._autocomplete_short_wait_chars.SetValue( char_limit )
            
            self._autocomplete_short_wait.SetValue( short_wait )
            
            #
            
            thumbnails_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            thumbnails_sizer.AddF( self._thumbnail_cache_size, CC.FLAGS_MIXED )
            thumbnails_sizer.AddF( self._estimated_number_thumbnails, CC.FLAGS_MIXED )
            
            previews_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            previews_sizer.AddF( self._preview_cache_size, CC.FLAGS_MIXED )
            previews_sizer.AddF( self._estimated_number_previews, CC.FLAGS_MIXED )
            
            fullscreens_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            fullscreens_sizer.AddF( self._fullscreen_cache_size, CC.FLAGS_MIXED )
            fullscreens_sizer.AddF( self._estimated_number_fullscreens, CC.FLAGS_MIXED )
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label = 'Thumbnail width: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._thumbnail_width, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Thumbnail height: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._thumbnail_height, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'MB memory reserved for thumbnail cache: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( thumbnails_sizer, CC.FLAGS_NONE )
            
            gridbox.AddF( wx.StaticText( self, label = 'MB memory reserved for preview cache: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( previews_sizer, CC.FLAGS_NONE )
            
            gridbox.AddF( wx.StaticText( self, label = 'MB memory reserved for media viewer cache: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( fullscreens_sizer, CC.FLAGS_NONE )
            
            gridbox.AddF( wx.StaticText( self, label = 'Autocomplete character threshold: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._num_autocomplete_chars, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Autocomplete long wait (ms): ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._autocomplete_long_wait, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Autocomplete short wait threshold: ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._autocomplete_short_wait_chars, CC.FLAGS_MIXED )
            
            gridbox.AddF( wx.StaticText( self, label = 'Autocomplete short wait (ms): ' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._autocomplete_short_wait, CC.FLAGS_MIXED )
            
            self.SetSizer( gridbox )
            
            #
            
            self.EventFullscreensUpdate( None )
            self.EventPreviewsUpdate( None )
            self.EventThumbnailsUpdate( None )
            
            wx.CallAfter( self.Layout ) # draws the static texts correctly
            
        
        def EventFullscreensUpdate( self, event ):
            
            ( width, height ) = wx.GetDisplaySize()
            
            estimated_bytes_per_fullscreen = 3 * width * height
            
            self._estimated_number_fullscreens.SetLabel( '(about ' + HydrusData.ConvertIntToPrettyString( ( self._fullscreen_cache_size.GetValue() * 1048576 ) / estimated_bytes_per_fullscreen ) + '-' + HydrusData.ConvertIntToPrettyString( ( self._fullscreen_cache_size.GetValue() * 1048576 ) / ( estimated_bytes_per_fullscreen / 4 ) ) + ' images)' )
            
        
        def EventPreviewsUpdate( self, event ):
            
            estimated_bytes_per_preview = 3 * 400 * 400
            
            self._estimated_number_previews.SetLabel( '(about ' + HydrusData.ConvertIntToPrettyString( ( self._preview_cache_size.GetValue() * 1048576 ) / estimated_bytes_per_preview ) + ' previews)' )
            
        
        def EventThumbnailsUpdate( self, event ):
            
            estimated_bytes_per_thumb = 3 * self._thumbnail_height.GetValue() * self._thumbnail_width.GetValue()
            
            self._estimated_number_thumbnails.SetLabel( '(about ' + HydrusData.ConvertIntToPrettyString( ( self._thumbnail_cache_size.GetValue() * 1048576 ) / estimated_bytes_per_thumb ) + ' thumbnails)' )
            
        
        def UpdateOptions( self ):
            
            new_thumbnail_dimensions = [ self._thumbnail_width.GetValue(), self._thumbnail_height.GetValue() ]
            
            if new_thumbnail_dimensions != HC.options[ 'thumbnail_dimensions' ]:
                
                text = 'You have changed the thumbnail dimensions, which will mean deleting all the old resized thumbnails right now, during which time the database will be locked. If you have tens or hundreds of thousands of files, this could take a long time.'
                text += os.linesep * 2
                text += 'Are you sure you want to change your thumbnail dimensions?'
                
                with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES: HC.options[ 'thumbnail_dimensions' ] = new_thumbnail_dimensions
                    
                
            
            HC.options[ 'thumbnail_cache_size' ] = self._thumbnail_cache_size.GetValue() * 1048576
            HC.options[ 'preview_cache_size' ] = self._preview_cache_size.GetValue() * 1048576
            HC.options[ 'fullscreen_cache_size' ] = self._fullscreen_cache_size.GetValue() * 1048576
            
            HC.options[ 'num_autocomplete_chars' ] = self._num_autocomplete_chars.GetValue()
            
            long_wait = self._autocomplete_long_wait.GetValue()
            
            char_limit = self._autocomplete_short_wait_chars.GetValue()
            
            short_wait = self._autocomplete_short_wait.GetValue()
            
            HC.options[ 'ac_timings' ] = ( char_limit, long_wait, short_wait )
            
        
    
    def EventOK( self, event ):
        
        for ( name, page ) in self._listbook.GetNamesToActivePages().items():
            
            page.UpdateOptions()
            
        
        try:
            
            HydrusGlobals.client_controller.WriteSynchronous( 'save_options', HC.options )
            
            HydrusGlobals.client_controller.WriteSynchronous( 'serialisable', self._new_options )
            
        except: wx.MessageBox( traceback.format_exc() )
        
        self.EndModal( wx.ID_OK )
        
    
class DialogManagePixivAccount( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._id = wx.TextCtrl( self )
            self._password = wx.TextCtrl( self )
            
            self._status = wx.StaticText( self )
            
            self._test = wx.Button( self, label = 'test' )
            self._test.Bind( wx.EVT_BUTTON, self.EventTest )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            ( id, password ) = HydrusGlobals.client_controller.Read( 'pixiv_account' )
            
            self._id.SetValue( id )
            self._password.SetValue( password )
            
        
        def ArrangeControls():
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label = 'id/email' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._id, CC.FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( wx.StaticText( self, label = 'password' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._password, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, CC.FLAGS_MIXED )
            b_box.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            text = 'In order to search and download from Pixiv, the client needs to log in to it.'
            text += os.linesep
            text += 'Until you put something in here, you will not see the option to download from Pixiv.'
            text += os.linesep
            text += 'You can use a throwaway account if you want--this only needs to log in.'
            
            vbox.AddF( wx.StaticText( self, label = text ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( self._status, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._test, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            x = max( x, 240 )
            
            self.SetInitialSize( ( x, y ) )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage pixiv account' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventOK( self, event ):
        
        id = self._id.GetValue()
        password = self._password.GetValue()
        
        HydrusGlobals.client_controller.Write( 'pixiv_account', ( id, password ) )
        
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
        
        ( response_gumpf, cookies ) = HydrusGlobals.client_controller.DoHTTP( HC.POST, 'http://www.pixiv.net/login.php', request_headers = headers, body = body, return_cookies = True )
        
        # _ only given to logged in php sessions
        if 'PHPSESSID' in cookies and '_' in cookies[ 'PHPSESSID' ]: self._status.SetLabel( 'OK!' )
        else: self._status.SetLabel( 'Did not work!' )
        
        wx.CallLater( 2000, self._status.SetLabel, '' )
        
    
class DialogManageRatings( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, media ):
        
        self._hashes = set()
        
        for m in media: self._hashes.update( m.GetHashes() )
        
        ( remember, position ) = HC.options[ 'rating_dialog_position' ]
        
        if remember and position is not None:
            
            my_position = 'custom'
            
            wx.CallAfter( self.SetPosition, position )
            
        else:
            
            my_position = 'topleft'
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage ratings for ' + HydrusData.ConvertIntToPrettyString( len( self._hashes ) ) + ' files', position = my_position )
        
        #
        
        like_services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.LOCAL_RATING_LIKE, ) )
        numerical_services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        self._panels = []
        
        if len( like_services ) > 0:
            
            self._panels.append( self._LikePanel( self, like_services, media ) )
            
        
        if len( numerical_services ) > 0:
            
            self._panels.append( self._NumericalPanel( self, numerical_services, media ) )
            
        
        self._apply = wx.Button( self, id = wx.ID_OK, label = 'apply' )
        self._apply.Bind( wx.EVT_BUTTON, self.EventOK )
        self._apply.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        buttonbox = wx.BoxSizer( wx.HORIZONTAL )
        
        buttonbox.AddF( self._apply, CC.FLAGS_MIXED )
        buttonbox.AddF( self._cancel, CC.FLAGS_MIXED )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        for panel in self._panels: vbox.AddF( panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( buttonbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( x, y ) )
        
        #
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.RefreshAcceleratorTable()
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'manage_ratings': self.EventOK( event )
            elif command == 'ok': self.EventOK( event )
            else: event.Skip()
            
        
    
    def EventOK( self, event ):
        
        try:
            
            service_keys_to_content_updates = {}
            
            for panel in self._panels:
                
                sub_service_keys_to_content_updates = panel.GetContentUpdates()
                
                service_keys_to_content_updates.update( sub_service_keys_to_content_updates )
                
            
            if len( service_keys_to_content_updates ) > 0:
                
                HydrusGlobals.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                
            
            ( remember, position ) = HC.options[ 'rating_dialog_position' ]
            
            current_position = self.GetPositionTuple()
            
            if remember and position != current_position:
                
                HC.options[ 'rating_dialog_position' ] = ( remember, current_position )
                
                HydrusGlobals.client_controller.Write( 'save_options', HC.options )
                
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def RefreshAcceleratorTable( self ):
        
        interested_actions = [ 'manage_ratings' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    class _LikePanel( wx.Panel ):
        
        def __init__( self, parent, services, media ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._services = services
            
            self._media = media
            
            self._service_keys_to_controls = {}
            self._service_keys_to_original_ratings_states = {}
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 0, 1 )
            
            for service in self._services:
                
                name = service.GetName()
                
                service_key = service.GetServiceKey()
                
                rating_state = ClientRatings.GetLikeStateFromMedia( self._media, service_key )
                
                control = ClientGUICommon.RatingLikeDialog( self, service_key )
                
                control.SetRatingState( rating_state )
                
                self._service_keys_to_controls[ service_key ] = control
                self._service_keys_to_original_ratings_states[ service_key ] = rating_state
                
                gridbox.AddF( wx.StaticText( self, label = name ), CC.FLAGS_MIXED )
                gridbox.AddF( control, CC.FLAGS_MIXED )
                
            
            self.SetSizer( gridbox )
            
        
        def GetContentUpdates( self ):
            
            service_keys_to_content_updates = {}
            
            hashes = { hash for hash in itertools.chain.from_iterable( ( media.GetHashes() for media in self._media ) ) }
            
            for ( service_key, control ) in self._service_keys_to_controls.items():
                
                original_rating_state = self._service_keys_to_original_ratings_states[ service_key ]
                
                rating_state = control.GetRatingState()
                
                if rating_state != original_rating_state:
                    
                    if rating_state == ClientRatings.LIKE: rating = 1
                    elif rating_state == ClientRatings.DISLIKE: rating = 0
                    else: rating = None
                    
                    content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, hashes ) )
                    
                    service_keys_to_content_updates[ service_key ] = ( content_update, )
                    
                
            
            return service_keys_to_content_updates
            
        
    
    class _NumericalPanel( wx.Panel ):
        
        def __init__( self, parent, services, media ):
            
            wx.Panel.__init__( self, parent )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._services = services
            
            self._media = media
            
            self._service_keys_to_controls = {}
            self._service_keys_to_original_ratings_states = {}
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 0, 1 )
            
            for service in self._services:
                
                name = service.GetName()
                
                service_key = service.GetServiceKey()
                
                ( rating_state, rating ) = ClientRatings.GetNumericalStateFromMedia( self._media, service_key )
                
                control = ClientGUICommon.RatingNumericalDialog( self, service_key )
                
                if rating_state != ClientRatings.SET:
                    
                    control.SetRatingState( rating_state )
                    
                else:
                    
                    control.SetRating( rating )
                    
                
                self._service_keys_to_controls[ service_key ] = control
                self._service_keys_to_original_ratings_states[ service_key ] = ( rating_state, rating )
                
                gridbox.AddF( wx.StaticText( self, label = name ), CC.FLAGS_MIXED )
                gridbox.AddF( control, CC.FLAGS_MIXED )
                
            
            self.SetSizer( gridbox )
            
        
        def GetContentUpdates( self ):
            
            service_keys_to_content_updates = {}
            
            hashes = { hash for hash in itertools.chain.from_iterable( ( media.GetHashes() for media in self._media ) ) }
            
            for ( service_key, control ) in self._service_keys_to_controls.items():
                
                ( original_rating_state, original_rating ) = self._service_keys_to_original_ratings_states[ service_key ]
                
                rating_state = control.GetRatingState()
                
                if rating_state != original_rating_state:
                    
                    if rating_state == ClientRatings.NULL:
                        
                        rating = None
                        
                    else:
                        
                        rating = control.GetRating()
                        
                    
                    content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, hashes ) )
                    
                    service_keys_to_content_updates[ service_key ] = ( content_update, )
                    
                
            
            return service_keys_to_content_updates
            
        #
    
class DialogManageRegexFavourites( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage regex favourites' )
        
        self._regexes = ClientGUICommon.SaneListCtrl( self, 200, [ ( 'regex phrase', 120 ), ( 'description', -1 ) ], delete_key_callback = self.Delete )
        
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
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        for ( regex_phrase, description ) in HC.options[ 'regex_favourites' ]:
            
            self._regexes.Append( ( regex_phrase, description ), ( regex_phrase, description ) )
            
        
        #
        
        regex_buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        regex_buttons.AddF( self._add_button, CC.FLAGS_MIXED )
        regex_buttons.AddF( self._edit_button, CC.FLAGS_MIXED )
        regex_buttons.AddF( self._delete_button, CC.FLAGS_MIXED )
        
        buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        buttons.AddF( self._ok, CC.FLAGS_MIXED )
        buttons.AddF( self._cancel, CC.FLAGS_MIXED )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._regexes, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( regex_buttons, CC.FLAGS_BUTTON_SIZER )
        vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        #
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        if x < 360: x = 360
        if y < 360: y = 360
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def Delete( self ):
        
        self._regexes.RemoveAllSelected()
        
    
    def EventAdd( self, event ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter regex.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                regex_phrase = dlg.GetValue()
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Enter description.' ) as dlg_2:
                    
                    if dlg_2.ShowModal() == wx.ID_OK:
                        
                        description = dlg_2.GetValue()
                        
                        self._regexes.Append( ( regex_phrase, description ), ( regex_phrase, description ) )
                        
                    
                
            
        
    
    def EventDelete( self, event ):
        
        self.Delete()
        
    
    def EventEdit( self, event ):
        
        indices = self._regexes.GetAllSelected()
        
        for index in indices:
            
            ( regex_phrase, description ) = self._regexes.GetClientData( index )
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Update regex.', default = regex_phrase ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    regex_phrase = dlg.GetValue()
                    
                    with ClientGUIDialogs.DialogTextEntry( self, 'Update description.', default = description ) as dlg_2:
                        
                        if dlg_2.ShowModal() == wx.ID_OK:
                            
                            description = dlg_2.GetValue()
                            
                            self._regexes.UpdateRow( index, ( regex_phrase, description ), ( regex_phrase, description ) )
                            
                        
                    
                
            
        
    
    def EventOK( self, event ):
        
        try:
            
            HC.options[ 'regex_favourites' ] = self._regexes.GetClientData()
            
            HydrusGlobals.client_controller.Write( 'save_options', HC.options )
            
        finally:
            
            self.EndModal( wx.ID_OK )
            
        
    
class DialogManageServer( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, service_key ):
        
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
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            for service_type in [ HC.TAG_REPOSITORY, HC.FILE_REPOSITORY, HC.MESSAGE_DEPOT ]: self._service_types.Append( HC.service_string_lookup[ service_type ], service_type )
            
            self._service_types.SetSelection( 0 )
            
            response = self._service.Request( HC.GET, 'services_info' )
            
            self._services_info = response[ 'services_info' ]
            
            for ( service_key, service_type, options ) in self._services_info:
                
                name = HC.service_string_lookup[ service_type ] + '@' + str( options[ 'port' ] )
                
                page = self._Panel( self._services_listbook, service_key, service_type, options )
                
                self._services_listbook.AddPage( name, page )
                
            
        
        def ArrangeControls():
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, CC.FLAGS_MIXED )
            b_box.AddF( self._cancel, CC.FLAGS_MIXED )
            
            add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
            add_remove_hbox.AddF( self._service_types, CC.FLAGS_MIXED )
            add_remove_hbox.AddF( self._add, CC.FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._services_listbook, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( add_remove_hbox, CC.FLAGS_SMALL_INDENT )
            vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if y < 400: y = 400 # listbook's setsize ( -1, 400 ) is buggy
            
            self.SetInitialSize( ( 680, y ) )
            
        
        self._service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage ' + self._service.GetName() + ' services' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self.EventServiceChanged( None )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _CheckCurrentServiceIsValid( self ):
        
        service_panel = self._services_listbook.GetCurrentPage()
        
        if service_panel is not None:
            
            ( service_key, service_type, options ) = service_panel.GetInfo()
            
            for ( existing_service_key, existing_service_type, existing_options ) in [ page.GetInfo() for page in self._services_listbook.GetNamesToActivePages().values() if page != service_panel ]:
                
                if options[ 'port' ] == existing_options[ 'port' ]: raise Exception( 'That port is already in use!' )
                
            
            name = self._services_listbook.GetCurrentName()
            
            new_name = HC.service_string_lookup[ service_type ] + '@' + str( options[ 'port' ] )
            
            if name != new_name: self._services_listbook.RenamePage( name, new_name )
            
        
    
    def EventAdd( self, event ):
        
        self._CheckCurrentServiceIsValid()
        
        service_key = HydrusData.GenerateKey()
        
        service_type = self._service_types.GetClientData( self._service_types.GetSelection() )
        
        port = HC.DEFAULT_SERVICE_PORT
        
        existing_ports = set()
        
        for ( existing_service_key, existing_service_type, existing_options ) in [ page.GetInfo() for page in self._services_listbook.GetNamesToActivePages().values() ]: existing_ports.add( existing_options[ 'port' ] )
        
        while port in existing_ports: port += 1
        
        options = dict( HC.DEFAULT_OPTIONS[ service_type ] )
        
        options[ 'port' ] = port
        
        self._edit_log.append( ( HC.ADD, ( service_key, service_type, options ) ) )
        
        page = self._Panel( self._services_listbook, service_key, service_type, options )
        
        name = HC.service_string_lookup[ service_type ] + '@' + str( port )
        
        self._services_listbook.AddPage( name, page, select = True )
        
    
    def EventOK( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            wx.MessageBox( HydrusData.ToUnicode( e ) )
            
            return
            
        
        for ( name, page ) in self._services_listbook.GetNamesToActivePages().items():
            
            if page.HasChanges():
                
                ( service_key, service_type, options ) = page.GetInfo()
                
                self._edit_log.append( ( HC.EDIT, ( service_key, service_type, options ) ) )
                
            
        
        try:
            
            if len( self._edit_log ) > 0:
                
                response = self._service.Request( HC.POST, 'services', { 'edit_log' : self._edit_log } )
                
                service_keys_to_access_keys = dict( response[ 'service_keys_to_access_keys' ] )
                
                admin_service_key = self._service.GetServiceKey()
                
                HydrusGlobals.client_controller.Write( 'update_server_services', admin_service_key, self._services_info, self._edit_log, service_keys_to_access_keys )
                
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventRemove( self, event ):
        
        service_panel = self._services_listbook.GetCurrentPage()
        
        if service_panel is not None:
            
            ( service_key, service_type, options ) = service_panel.GetInfo()
            
            self._edit_log.append( ( HC.DELETE, service_key ) )
            
            self._services_listbook.DeleteCurrentPage()
            
        
    
    def EventServiceChanged( self, event ):
        
        page = self._services_listbook.GetCurrentPage()
        
        ( service_key, service_type, options ) = page.GetInfo()
        
        if service_type == HC.SERVER_ADMIN: self._remove.Disable()
        else: self._remove.Enable()
        
    
    def EventServiceChanging( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            wx.MessageBox( HydrusData.ToUnicode( e ) )
            
            event.Veto()
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_key, service_type, options ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_key = service_key
            self._service_type = service_type
            self._options = options
            
            def InitialiseControls():
                
                self._options_panel = ClientGUICommon.StaticBox( self, 'options' )
                
                if 'port' in self._options: self._port = wx.SpinCtrl( self._options_panel, min = 1, max = 65535 )
                if 'max_monthly_data' in self._options: self._max_monthly_data = ClientGUICommon.NoneableSpinCtrl( self._options_panel, 'max monthly data (MB)', multiplier = 1048576 )
                if 'max_storage' in self._options: self._max_storage = ClientGUICommon.NoneableSpinCtrl( self._options_panel, 'max storage (MB)', multiplier = 1048576 )
                if 'log_uploader_ips' in self._options: self._log_uploader_ips = wx.CheckBox( self._options_panel )
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
                    
                    gridbox.AddF( wx.StaticText( self._options_panel, label = 'port' ), CC.FLAGS_MIXED )
                    gridbox.AddF( self._port, CC.FLAGS_EXPAND_BOTH_WAYS )
                    
                
                if 'max_monthly_data' in self._options:
                    
                    gridbox.AddF( wx.StaticText( self._options_panel, label = 'max monthly data' ), CC.FLAGS_MIXED )
                    gridbox.AddF( self._max_monthly_data, CC.FLAGS_EXPAND_BOTH_WAYS )
                    
                
                if 'max_storage' in self._options:
                    
                    gridbox.AddF( wx.StaticText( self._options_panel, label = 'max storage' ), CC.FLAGS_MIXED )
                    gridbox.AddF( self._max_storage, CC.FLAGS_EXPAND_BOTH_WAYS )
                    
                
                if 'log_uploader_ips' in self._options:
                    
                    gridbox.AddF( wx.StaticText( self._options_panel, label = 'log uploader IPs' ), CC.FLAGS_MIXED )
                    gridbox.AddF( self._log_uploader_ips, CC.FLAGS_EXPAND_BOTH_WAYS )
                    
                
                if 'message' in self._options:
                    
                    gridbox.AddF( wx.StaticText( self._options_panel, label = 'message' ), CC.FLAGS_MIXED )
                    gridbox.AddF( self._message, CC.FLAGS_EXPAND_BOTH_WAYS )
                    
                
                if 'upnp' in self._options:
                    
                    gridbox.AddF( wx.StaticText( self._options_panel, label = 'UPnP' ), CC.FLAGS_MIXED )
                    gridbox.AddF( self._upnp, CC.FLAGS_EXPAND_BOTH_WAYS )
                    
                
                self._options_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
                
                vbox.AddF( self._options_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                
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
            
            return ( self._service_key, self._service_type, options )
            
        
        def HasChanges( self ):
            
            ( service_key, service_type, options ) = self.GetInfo()
            
            if options != self._options: return True
            
            return False
            
        
    
class DialogManageServices( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._edit_log = []
            
            self._notebook = wx.Notebook( self )
            self._notebook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
            self._notebook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
            self._notebook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventPageChanging, source = self._notebook )
            
            self._local_listbook = ClientGUICommon.ListBook( self._notebook )
            self._local_listbook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventPageChanging, source = self._local_listbook )
            
            self._remote_listbook = ClientGUICommon.ListBook( self._notebook )
            self._remote_listbook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventPageChanging, source = self._remote_listbook )
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            self._add.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._remove = wx.Button( self, label = 'remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._export = wx.Button( self, label = 'export' )
            self._export.Bind( wx.EVT_BUTTON, self.EventExport )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            manageable_service_types = HC.RESTRICTED_SERVICES + [ HC.LOCAL_TAG, HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL, HC.LOCAL_BOORU ]
            
            for service_type in manageable_service_types:
                
                if service_type == HC.LOCAL_RATING_LIKE: name = 'like/dislike ratings'
                elif service_type == HC.LOCAL_RATING_NUMERICAL: name = 'numerical ratings'
                elif service_type == HC.LOCAL_BOORU: name = 'booru'
                elif service_type == HC.LOCAL_TAG: name = 'local tags'
                elif service_type == HC.TAG_REPOSITORY: name = 'tag repositories'
                elif service_type == HC.FILE_REPOSITORY: name = 'file repositories'
                #elif service_type == HC.MESSAGE_DEPOT: name = 'message repositories'
                elif service_type == HC.SERVER_ADMIN: name = 'administrative services'
                #elif service_type == HC.RATING_LIKE_REPOSITORY: name = 'like/dislike rating repositories'
                #elif service_type == HC.RATING_NUMERICAL_REPOSITORY: name = 'numerical rating repositories'
                else: continue
                
                if service_type in HC.LOCAL_SERVICES: parent_listbook = self._local_listbook
                else: parent_listbook = self._remote_listbook
                
                listbook = ClientGUICommon.ListBook( parent_listbook )
                listbook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGING, self.EventServiceChanging )
                
                self._service_types_to_listbooks[ service_type ] = listbook
                self._listbooks_to_service_types[ listbook ] = service_type
                
                parent_listbook.AddPage( name, listbook )
                
                services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( service_type, ) )
                
                for service in services:
                    
                    service_key = service.GetServiceKey()
                    name = service.GetName()
                    info = service.GetInfo()
                    
                    listbook.AddPageArgs( name, self._Panel, ( listbook, service_key, service_type, name, info ), {} )
                    
                
            
            wx.CallAfter( self._local_listbook.Layout )
            wx.CallAfter( self._remote_listbook.Layout )
            
        
        def ArrangeControls():
            
            add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            add_remove_hbox.AddF( self._add, CC.FLAGS_MIXED )
            add_remove_hbox.AddF( self._remove, CC.FLAGS_MIXED )
            add_remove_hbox.AddF( self._export, CC.FLAGS_MIXED )
            
            ok_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            ok_hbox.AddF( self._ok, CC.FLAGS_MIXED )
            ok_hbox.AddF( self._cancel, CC.FLAGS_MIXED )
            
            self._notebook.AddPage( self._local_listbook, 'local' )
            self._notebook.AddPage( self._remote_listbook, 'remote' )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( add_remove_hbox, CC.FLAGS_SMALL_INDENT )
            vbox.AddF( ok_hbox, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage services' )
        
        self._service_types_to_listbooks = {}
        self._listbooks_to_service_types = {}
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( 880, y + 220 ) )
        
        self.SetDropTarget( ClientDragDrop.FileDropTarget( self.Import ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _CheckCurrentServiceIsValid( self ):
        
        local_or_remote_listbook = self._notebook.GetCurrentPage()
        
        if local_or_remote_listbook is not None:
            
            services_listbook = local_or_remote_listbook.GetCurrentPage()
            
            if services_listbook is not None:
                
                service_panel = services_listbook.GetCurrentPage()
                
                if service_panel is not None:
                    
                    ( service_key, service_type, name, info ) = service_panel.GetInfo()
                    
                    old_name = services_listbook.GetCurrentName()
                    
                    if old_name is not None and name != old_name:
                        
                        if services_listbook.NameExists( name ): raise HydrusExceptions.NameException( 'That name is already in use!' )
                        
                        services_listbook.RenamePage( old_name, name )
                        
                    
                
            
        
    
    def EventAdd( self, event ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter new service\'s name.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    name = dlg.GetValue()
                    
                    local_or_remote_listbook = self._notebook.GetCurrentPage()
                    
                    if local_or_remote_listbook is not None:
                        
                        services_listbook = local_or_remote_listbook.GetCurrentPage()
                        
                        if services_listbook.NameExists( name ): raise HydrusExceptions.NameException( 'That name is already in use!' )
                        
                        if name == '': raise HydrusExceptions.NameException( 'Please enter a nickname for the service.' )
                        
                        service_key = HydrusData.GenerateKey()
                        service_type = self._listbooks_to_service_types[ services_listbook ]
                        
                        info = {}
                        
                        if service_type in HC.REMOTE_SERVICES:
                            
                            if service_type == HC.SERVER_ADMIN:
                                
                                ( host, port ) = ( 'hostname', 45870 )
                                
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
                                    
                                
                            else:
                                
                                ( host, port ) = ( 'hostname', 45871 )
                                
                            
                            info[ 'host' ] = host
                            info[ 'port' ] = port
                            
                        
                        if service_type in HC.REPOSITORIES:
                            
                            info[ 'paused' ] = False
                            
                        
                        if service_type == HC.TAG_REPOSITORY:
                            
                            info[ 'tag_archive_sync' ] = {}
                            
                        
                        if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                            
                            if service_type == HC.LOCAL_RATING_NUMERICAL:
                                
                                info[ 'num_stars' ] = 5
                                
                                info[ 'colours' ] = ClientRatings.default_numerical_colours
                                
                                info[ 'allow_zero' ] = True
                                
                            else:
                                
                                info[ 'colours' ] = ClientRatings.default_like_colours
                                
                            
                            info[ 'shape' ] = ClientRatings.CIRCLE
                            
                        
                        self._edit_log.append( HydrusData.EditLogActionAdd( ( service_key, service_type, name, info ) ) )
                        
                        page = self._Panel( services_listbook, service_key, service_type, name, info )
                        
                        services_listbook.AddPage( name, page, select = True )
                        
                    
                except HydrusExceptions.NameException as e:
                    
                    wx.MessageBox( str( e ) )
                    
                    self.EventAdd( event )
                    
                
            
        
    
    def EventExport( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except HydrusExceptions.NameException as e:
            
            wx.MessageBox( str( e ) )
            
            return
            
        
        local_or_remote_listbook = self._notebook.GetCurrentPage()
        
        if local_or_remote_listbook is not None:
            
            services_listbook = local_or_remote_listbook.GetCurrentPage()
            
            if services_listbook is not None:
                
                service_panel = services_listbook.GetCurrentPage()
                
                ( service_key, service_type, name, info ) = service_panel.GetInfo()
                
                try:
                    
                    with wx.FileDialog( self, 'select where to export service', defaultFile = name + '.yaml', style = wx.FD_SAVE ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            path = HydrusData.ToUnicode( dlg.GetPath() )
                            
                            with open( path, 'wb' ) as f: f.write( yaml.safe_dump( ( service_key, service_type, name, info ) ) )
                            
                        
                    
                except:
                    
                    with wx.FileDialog( self, 'select where to export service', defaultFile = 'service.yaml', style = wx.FD_SAVE ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            path = HydrusData.ToUnicode( dlg.GetPath() )
                            
                            with open( path, 'wb' ) as f: f.write( yaml.safe_dump( ( service_key, service_type, name, info ) ) )
                            
                        
                    
                
            
        
    
    def EventOK( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except HydrusExceptions.NameException as e:
            
            wx.MessageBox( str( e ) )
            
            return
            
        
        all_listbooks = self._service_types_to_listbooks.values()
        
        for listbook in all_listbooks:
            
            all_pages = listbook.GetNamesToActivePages().values()
            
            for page in all_pages:
                
                page.DoOnOKStuff()
                
            
        
        for listbook in all_listbooks:
            
            all_pages = listbook.GetNamesToActivePages().values()
            
            for page in all_pages:
                
                if page.HasChanges():
                    
                    ( service_key, service_type, name, info ) = page.GetInfo()
                    
                    self._edit_log.append( HydrusData.EditLogActionEdit( service_key, ( service_key, service_type, name, info ) ) )
                    
                
            
        
        try:
            
            if len( self._edit_log ) > 0: HydrusGlobals.client_controller.Write( 'update_services', self._edit_log )
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventPageChanging( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except HydrusExceptions.NameException as e:
            
            wx.MessageBox( str( e ) )
            
            event.Veto()
            
        
    
    def EventRemove( self, event ):
        
        local_or_remote_listbook = self._notebook.GetCurrentPage()
        
        if local_or_remote_listbook is not None:
            
            services_listbook = local_or_remote_listbook.GetCurrentPage()
            
            service_panel = services_listbook.GetCurrentPage()
            
            if service_panel is not None:
                
                ( service_key, service_type, name, info ) = service_panel.GetInfo()
                
                self._edit_log.append( HydrusData.EditLogActionDelete( service_key ) )
                
                services_listbook.DeleteCurrentPage()
                
            
        
    
    def EventServiceChanged( self, event ):
        
        local_or_remote_listbook = self._notebook.GetCurrentPage()
        
        if local_or_remote_listbook is not None:
            
            services_listbook = local_or_remote_listbook.GetCurrentPage()
            
            service_type = self._listbooks_to_service_types[ services_listbook ]
            
            if service_type in HC.NONEDITABLE_SERVICES:
                
                self._add.Disable()
                self._remove.Disable()
                self._export.Disable()
                
            else:
                
                self._add.Enable()
                self._remove.Enable()
                self._export.Enable()
                
            
        
        event.Skip()
        
    
    def EventServiceChanging( self, event ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            event.Veto()
            
        
    
    def Import( self, paths ):
        
        try: self._CheckCurrentServiceIsValid()
        except Exception as e:
            
            wx.MessageBox( HydrusData.ToUnicode( e ) )
            
            return
            
        
        for path in paths:
            
            with open( path, 'rb' ) as f: file = f.read()
            
            ( service_key, service_type, name, info ) = yaml.safe_load( file )
            
            services_listbook = self._service_types_to_listbooks[ service_type ]
            
            if services_listbook.NameExists( name ):
                
                message = 'A service already exists with that name. Overwrite it?'
                
                with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        page = services_listbook.GetNamesToActivePages()[ name ]
                        
                        page.Update( service_key, service_type, name, info )
                        
                    
                
            else:
                
                self._edit_log.append( HydrusData.EditLogActionAdd( ( service_key, service_type, name, info ) ) )
                
                page = self._Panel( services_listbook, service_key, service_type, name, info )
                
                services_listbook.AddPage( name, page, select = True )
                
            
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_key, service_type, name, info ):
            
            wx.Panel.__init__( self, parent )
            
            self._original_info = ( service_key, service_type, name, info )
            
            self._reset_downloading = False
            self._reset_processing = False
            
            def InitialiseControls():
                
                if service_type not in HC.NONEDITABLE_SERVICES:
                    
                    if service_type in HC.REMOTE_SERVICES: title = 'name and credentials'
                    else: title = 'name'
                    
                    self._credentials_panel = ClientGUICommon.StaticBox( self, title )
                    
                    self._service_name = wx.TextCtrl( self._credentials_panel )
                    
                    if service_type in HC.REMOTE_SERVICES:
                        
                        host = info[ 'host' ]
                        port = info[ 'port' ]
                        
                        if 'access_key' in info: access_key = info[ 'access_key' ]
                        else: access_key = None
                        
                        credentials = ClientData.Credentials( host, port, access_key )
                        
                        self._service_credentials = wx.TextCtrl( self._credentials_panel, value = credentials.GetConnectionString() )
                        
                        self._check_service = wx.Button( self._credentials_panel, label = 'test credentials' )
                        self._check_service.Bind( wx.EVT_BUTTON, self.EventCheckService )
                        
                    
                
                if service_type in HC.REPOSITORIES:
                    
                    self._repositories_panel = ClientGUICommon.StaticBox( self, 'repository synchronisation' )
                    
                    self._pause_synchronisation = wx.CheckBox( self._repositories_panel, label = 'pause synchronisation' )
                    
                    self._reset_processing_button = wx.Button( self._repositories_panel, label = 'reset processing cache on dialog ok' )
                    self._reset_processing_button.Bind( wx.EVT_BUTTON, self.EventServiceResetProcessing )
                    
                    self._reset_downloading_button = wx.Button( self._repositories_panel, label = 'reset processing and download cache on dialog ok' )
                    self._reset_downloading_button.Bind( wx.EVT_BUTTON, self.EventServiceResetDownload )
                    
                
                if service_type in HC.RATINGS_SERVICES:
                    
                    self._local_rating_panel = ClientGUICommon.StaticBox( self, 'local rating configuration' )
                    
                    if service_type == HC.LOCAL_RATING_NUMERICAL:
                        
                        num_stars = info[ 'num_stars' ]
                        
                        self._num_stars = wx.SpinCtrl( self._local_rating_panel, min = 1, max = 20 )
                        self._num_stars.SetValue( num_stars )
                        
                        allow_zero = info[ 'allow_zero' ]
                        
                        self._allow_zero = wx.CheckBox( self._local_rating_panel )
                        self._allow_zero.SetValue( allow_zero )
                        
                    
                    self._shape = ClientGUICommon.BetterChoice( self._local_rating_panel )
                    
                    self._shape.Append( 'circle', ClientRatings.CIRCLE )
                    self._shape.Append( 'square', ClientRatings.SQUARE )
                    self._shape.Append( 'star', ClientRatings.STAR )
                    
                    self._colour_ctrls = {}
                    
                    for colour_type in [ ClientRatings.LIKE, ClientRatings.DISLIKE, ClientRatings.NULL, ClientRatings.MIXED ]:
                        
                        border_ctrl = wx.ColourPickerCtrl( self._local_rating_panel )
                        fill_ctrl = wx.ColourPickerCtrl( self._local_rating_panel )
                        
                        border_ctrl.SetMaxSize( ( 20, -1 ) )
                        fill_ctrl.SetMaxSize( ( 20, -1 ) )
                        
                        self._colour_ctrls[ colour_type ] = ( border_ctrl, fill_ctrl )
                        
                    
                
                if service_type in HC.TAG_SERVICES:
                    
                    self._archive_info = HydrusGlobals.client_controller.Read( 'tag_archive_info' )
                    
                    self._archive_panel = ClientGUICommon.StaticBox( self, 'archive synchronisation' )
                    
                    self._archive_sync = wx.ListBox( self._archive_panel, size = ( -1, 100 ) )
                    
                    self._archive_sync_add = wx.Button( self._archive_panel, label = 'add' )
                    self._archive_sync_add.Bind( wx.EVT_BUTTON, self.EventArchiveAdd )
                    
                    self._archive_sync_edit = wx.Button( self._archive_panel, label = 'edit' )
                    self._archive_sync_edit.Bind( wx.EVT_BUTTON, self.EventArchiveEdit )
                    
                    self._archive_sync_remove = wx.Button( self._archive_panel, label = 'remove' )
                    self._archive_sync_remove.Bind( wx.EVT_BUTTON, self.EventArchiveRemove )
                    
                
                if service_type == HC.LOCAL_BOORU:
                    
                    self._booru_options_panel = ClientGUICommon.StaticBox( self, 'options' )
                    
                    self._port = wx.SpinCtrl( self._booru_options_panel, min = 0, max = 65535 )
                    
                    self._upnp = ClientGUICommon.NoneableSpinCtrl( self._booru_options_panel, 'upnp port', none_phrase = 'do not forward port', max = 65535 )
                    
                    self._max_monthly_data = ClientGUICommon.NoneableSpinCtrl( self._booru_options_panel, 'max monthly MB', multiplier = 1024 * 1024 )
                    
                
            
            def PopulateControls():
                
                if service_type not in HC.NONEDITABLE_SERVICES:
                    
                    self._service_name.SetValue( name )
                    
                
                if service_type in HC.REPOSITORIES:
                    
                    self._pause_synchronisation.SetValue( info[ 'paused' ] )
                    
                
                if service_type in HC.TAG_SERVICES:
                    
                    for ( archive_name, namespaces ) in info[ 'tag_archive_sync' ].items():
                        
                        name_to_display = self._GetArchiveNameToDisplay( archive_name, namespaces )
                        
                        self._archive_sync.Append( name_to_display, ( archive_name, namespaces ) )
                        
                    
                    self._UpdateArchiveButtons()
                    
                
                if service_type in HC.RATINGS_SERVICES:
                    
                    self._shape.SelectClientData( info[ 'shape' ] )
                    
                    colours = info[ 'colours' ]
                    
                    for colour_type in colours:
                        
                        ( border_rgb, fill_rgb ) = colours[ colour_type ]
                        
                        ( border_ctrl, fill_ctrl ) = self._colour_ctrls[ colour_type ]
                        
                        border_ctrl.SetColour( wx.Colour( *border_rgb ) )
                        fill_ctrl.SetColour( wx.Colour( *fill_rgb ) )
                        
                    
                
                if service_type == HC.LOCAL_BOORU:
                    
                    self._port.SetValue( info[ 'port' ] )
                    self._upnp.SetValue( info[ 'upnp' ] )
                    self._max_monthly_data.SetValue( info[ 'max_monthly_data' ] )
                    
                
            
            def ArrangeControls():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                if service_type not in HC.NONEDITABLE_SERVICES:
                    
                    gridbox = wx.FlexGridSizer( 0, 2 )
                    
                    gridbox.AddGrowableCol( 1, 1 )
                    
                    gridbox.AddF( wx.StaticText( self._credentials_panel, label = 'name' ), CC.FLAGS_MIXED )
                    gridbox.AddF( self._service_name, CC.FLAGS_EXPAND_BOTH_WAYS )
                    
                    if service_type in HC.REMOTE_SERVICES:
                        
                        gridbox.AddF( wx.StaticText( self._credentials_panel, label = 'credentials' ), CC.FLAGS_MIXED )
                        gridbox.AddF( self._service_credentials, CC.FLAGS_EXPAND_BOTH_WAYS )
                        
                        gridbox.AddF( ( 20, 20 ), CC.FLAGS_MIXED )
                        gridbox.AddF( self._check_service, CC.FLAGS_LONE_BUTTON )
                        
                    
                    self._credentials_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
                    
                    vbox.AddF( self._credentials_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                    
                
                if service_type in HC.REPOSITORIES:
                    
                    self._repositories_panel.AddF( self._pause_synchronisation, CC.FLAGS_MIXED )
                    self._repositories_panel.AddF( self._reset_processing_button, CC.FLAGS_LONE_BUTTON )
                    self._repositories_panel.AddF( self._reset_downloading_button, CC.FLAGS_LONE_BUTTON )
                    
                    vbox.AddF( self._repositories_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                    
                
                if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                    
                    gridbox = wx.FlexGridSizer( 0, 2 )
                    
                    gridbox.AddGrowableCol( 1, 1 )
                    
                    if service_type == HC.LOCAL_RATING_NUMERICAL:
                        
                        gridbox.AddF( wx.StaticText( self._local_rating_panel, label = 'number of \'stars\'' ), CC.FLAGS_MIXED )
                        gridbox.AddF( self._num_stars, CC.FLAGS_EXPAND_BOTH_WAYS )
                        
                        gridbox.AddF( wx.StaticText( self._local_rating_panel, label = 'allow a zero rating' ), CC.FLAGS_MIXED )
                        gridbox.AddF( self._allow_zero, CC.FLAGS_EXPAND_BOTH_WAYS )
                        
                    
                    gridbox.AddF( wx.StaticText( self._local_rating_panel, label = 'shape' ), CC.FLAGS_MIXED )
                    gridbox.AddF( self._shape, CC.FLAGS_EXPAND_BOTH_WAYS )
                    
                    for colour_type in [ ClientRatings.LIKE, ClientRatings.DISLIKE, ClientRatings.NULL, ClientRatings.MIXED ]:
                        
                        ( border_ctrl, fill_ctrl ) = self._colour_ctrls[ colour_type ]
                        
                        hbox = wx.BoxSizer( wx.HORIZONTAL )
                        
                        hbox.AddF( border_ctrl, CC.FLAGS_MIXED )
                        hbox.AddF( fill_ctrl, CC.FLAGS_MIXED )
                        
                        if colour_type == ClientRatings.LIKE: colour_text = 'liked'
                        elif colour_type == ClientRatings.DISLIKE: colour_text = 'disliked'
                        elif colour_type == ClientRatings.NULL: colour_text = 'not rated'
                        elif colour_type == ClientRatings.MIXED: colour_text = 'a mixture of ratings'
                        
                        gridbox.AddF( wx.StaticText( self._local_rating_panel, label = 'border/fill for ' + colour_text ), CC.FLAGS_MIXED )
                        gridbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
                        
                    
                    self._local_rating_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
                    
                    vbox.AddF( self._local_rating_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                    
                
                if service_type in HC.TAG_SERVICES:
                    
                    hbox = wx.BoxSizer( wx.HORIZONTAL )
                    
                    hbox.AddF( self._archive_sync_add, CC.FLAGS_MIXED )
                    hbox.AddF( self._archive_sync_edit, CC.FLAGS_MIXED )
                    hbox.AddF( self._archive_sync_remove, CC.FLAGS_MIXED )
                    
                    self._archive_panel.AddF( self._archive_sync, CC.FLAGS_EXPAND_BOTH_WAYS )
                    self._archive_panel.AddF( hbox, CC.FLAGS_BUTTON_SIZER )
                    
                    vbox.AddF( self._archive_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                    
                
                if service_type == HC.LOCAL_BOORU:
                    
                    hbox = wx.BoxSizer( wx.HORIZONTAL )
                    
                    hbox.AddF( wx.StaticText( self._booru_options_panel, label = 'port' ), CC.FLAGS_MIXED )
                    hbox.AddF( self._port, CC.FLAGS_EXPAND_BOTH_WAYS )
                    
                    self._booru_options_panel.AddF( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
                    self._booru_options_panel.AddF( self._upnp, CC.FLAGS_EXPAND_BOTH_WAYS )
                    self._booru_options_panel.AddF( self._max_monthly_data, CC.FLAGS_EXPAND_BOTH_WAYS )
                    
                    vbox.AddF( self._booru_options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                    
                
                self.SetSizer( vbox )
                
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
            
        
        def _GetArchiveNameToDisplay( self, archive_name, namespaces ):
            
            if len( namespaces ) == 0: name_to_display = archive_name
            else: name_to_display = archive_name + ' (' + ', '.join( HydrusData.ConvertUglyNamespacesToPrettyStrings( namespaces ) ) + ')'
            
            return name_to_display
            
        
        def _GetPotentialArchives( self ):
            
            existing_syncs = set()
            
            for i in range( self._archive_sync.GetCount() ):
                
                ( archive_name, namespaces ) = self._archive_sync.GetClientData( i )
                
                existing_syncs.add( archive_name )
                
            
            potential_archives = { archive_name for archive_name in self._archive_info.keys() if archive_name not in existing_syncs }
            
            return potential_archives
            
        
        def _UpdateArchiveButtons( self ):
            
            potential_archives = self._GetPotentialArchives()
            
            if len( potential_archives ) == 0: self._archive_sync_add.Disable()
            else: self._archive_sync_add.Enable()
            
        
        def DoOnOKStuff( self ):
            
            ( service_key, service_type, name, info ) = self._original_info
            
            if self._reset_downloading:
                
                HydrusGlobals.client_controller.Write( 'reset_service', service_key, delete_updates = True )
                
            elif self._reset_processing:
                
                HydrusGlobals.client_controller.Write( 'reset_service', service_key )
                
            
        
        def EventArchiveAdd( self, event ):
            
            if self._archive_sync.GetCount() == 0:
                
                wx.MessageBox( 'Be careful with this tool! Synching a lot of files to a large archive can take a very long time to initialise.' )
                
            
            potential_archives = self._GetPotentialArchives()
            
            if len( potential_archives ) == 1:
                
                ( archive_name, ) = potential_archives
                
                wx.MessageBox( 'There is only one tag archive, ' + archive_name + ', to select, so I am selecting it for you.' )
                
            else:
                
                with ClientGUIDialogs.DialogSelectFromListOfStrings( self, 'Select the tag archive to add', potential_archives ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK: archive_name = dlg.GetString()
                    else: return
                    
                
            
            potential_namespaces = self._archive_info[ archive_name ]
            
            with ClientGUIDialogs.DialogCheckFromListOfStrings( self, 'Select namespaces', HydrusData.ConvertUglyNamespacesToPrettyStrings( potential_namespaces ) ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    namespaces = HydrusData.ConvertPrettyStringsToUglyNamespaces( dlg.GetChecked() )
                    
                else: return
                
            
            name_to_display = self._GetArchiveNameToDisplay( archive_name, namespaces )
            
            self._archive_sync.Append( name_to_display, ( archive_name, namespaces ) )
            
            self._UpdateArchiveButtons()
            
        
        def EventArchiveEdit( self, event ):
            
            selection = self._archive_sync.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                ( archive_name, existing_namespaces ) = self._archive_sync.GetClientData( selection )
                
                if archive_name not in self._archive_info.keys():
                    
                    wx.MessageBox( 'This archive does not seem to exist any longer!' )
                    
                    return
                    
                
                archive_namespaces = self._archive_info[ archive_name ]
                
                with ClientGUIDialogs.DialogCheckFromListOfStrings( self, 'Select namespaces', HydrusData.ConvertUglyNamespacesToPrettyStrings( archive_namespaces ), HydrusData.ConvertUglyNamespacesToPrettyStrings( existing_namespaces ) ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        namespaces = HydrusData.ConvertPrettyStringsToUglyNamespaces( dlg.GetChecked() )
                        
                    else: return
                    
                
                name_to_display = self._GetArchiveNameToDisplay( archive_name, namespaces )
                
                self._archive_sync.SetString( selection, name_to_display )
                self._archive_sync.SetClientData( selection, ( archive_name, namespaces ) )
                
            
        
        def EventArchiveRemove( self, event ):
            
            selection = self._archive_sync.GetSelection()
            
            if selection != wx.NOT_FOUND: self._archive_sync.Delete( selection )
            
            self._UpdateArchiveButtons()
            
        
        def EventCheckService( self, event ):
            
            ( service_key, service_type, name, info ) = self.GetInfo()
            
            service = ClientData.Service( service_key, service_type, name, info )
            
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
            
            ( service_key, service_type, name, info ) = self._original_info
            
            info = dict( info )
            
            if service_type not in HC.NONEDITABLE_SERVICES:
                
                name = self._service_name.GetValue()
                
                if name == '': raise Exception( 'Please enter a name' )
                
            
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
                
            
            if service_type in HC.REPOSITORIES:
                
                info[ 'paused' ] = self._pause_synchronisation.GetValue()
                
            
            if service_type in HC.RATINGS_SERVICES:
                
                if service_type == HC.LOCAL_RATING_NUMERICAL:
                    
                    info[ 'num_stars' ] = self._num_stars.GetValue()
                    info[ 'allow_zero' ] = self._allow_zero.GetValue()
                    
                
                info[ 'shape' ] = self._shape.GetChoice()
                
                colours = {}
                
                for colour_type in self._colour_ctrls:
                    
                    ( border_ctrl, fill_ctrl ) = self._colour_ctrls[ colour_type ]
                    
                    border_colour = border_ctrl.GetColour()
                    
                    border_rgb = ( border_colour.Red(), border_colour.Green(), border_colour.Blue() )
                    
                    fill_colour = fill_ctrl.GetColour()
                    
                    fill_rgb = ( fill_colour.Red(), fill_colour.Green(), fill_colour.Blue() )
                    
                    colours[ colour_type ] = ( border_rgb, fill_rgb )
                    
                
                info[ 'colours' ] = colours
                
            
            if service_type in HC.TAG_SERVICES:
                
                tag_archives = {}
                
                for i in range( self._archive_sync.GetCount() ):
                    
                    ( archive_name, namespaces ) = self._archive_sync.GetClientData( i )
                    
                    tag_archives[ archive_name ] = namespaces
                    
                
                info[ 'tag_archive_sync' ] = tag_archives
                
            
            if service_type == HC.LOCAL_BOORU:
                
                info[ 'port' ] = self._port.GetValue()
                info[ 'upnp' ] = self._upnp.GetValue()
                info[ 'max_monthly_data' ] = self._max_monthly_data.GetValue()
                
                # listctrl stuff here
                
            
            return ( service_key, service_type, name, info )
            
        
        def EventServiceResetDownload( self, event ):
            
            ( service_key, service_type, name, info ) = self._original_info
            
            message = 'This will completely reset ' + name + ', deleting all downloaded and processed information from the database. It may take several minutes to finish the operation, during which time the gui will likely freeze.' + os.linesep * 2 + 'Once the service is reset, the client will have to redownload and reprocess everything, which could take a very long time.' + os.linesep * 2 + 'If you do not understand what this button does, you definitely want to click no!'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._reset_downloading_button.SetLabel( 'everything will be reset on dialog ok!' )
                    
                    self._reset_downloading = True
                    
                
            
        
        def EventServiceResetProcessing( self, event ):
            
            ( service_key, service_type, name, info ) = self._original_info
            
            message = 'This will remove all the processed information for ' + name + ' from the database. It may take several minutes to finish the operation, during which time the gui will likely freeze.' + os.linesep * 2 + 'Once the service is reset, the client will have to reprocess all the downloaded updates, which could take a very long time.' + os.linesep * 2 + 'If you do not understand what this button does, you probably want to click no!'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._reset_processing_button.SetLabel( 'processing will be reset on dialog ok!' )
                    
                    self._reset_processing = True
                    
                
            
        
        def HasChanges( self ): return self._original_info != self.GetInfo()
        
        def Update( self, service_key, service_type, name, info ):
            
            self._service_name.SetValue( name )
            
            if service_type in HC.REMOTE_SERVICES:
                
                host = info[ 'host' ]
                port = info[ 'port' ]
                
                if service_type in HC.RESTRICTED_SERVICES: access_key = info[ 'access_key' ]
                else: access_key = None
                
                credentials = ClientData.Credentials( host, port, access_key )
                
                self._service_credentials.SetValue( credentials.GetConnectionString() )
                
            
            if service_type == HC.LOCAL_RATING_NUMERICAL:
                
                num_stars = info[ 'num_stars' ]
                
                self._num_stars.SetValue( num_stars )
                
            
        
    
class DialogManageSubscriptions( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage subscriptions' )
        
        self._original_subscription_names = HydrusGlobals.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION )
        
        self._names_to_delete = set()
        
        #
        
        self._listbook = ClientGUICommon.ListBook( self )
        
        self._add = wx.Button( self, label = 'add' )
        self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
        self._add.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._remove = wx.Button( self, label = 'remove' )
        self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
        self._remove.SetForegroundColour( ( 128, 0, 0 ) )
        
        self._export = wx.Button( self, label = 'export' )
        self._export.Bind( wx.EVT_BUTTON, self.EventExport )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        for name in self._original_subscription_names:
            
            self._listbook.AddPageArgs( name, self._Panel, ( self._listbook, name ), {} )
            
        
        #
        
        add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
        add_remove_hbox.AddF( self._add, CC.FLAGS_MIXED )
        add_remove_hbox.AddF( self._remove, CC.FLAGS_MIXED )
        add_remove_hbox.AddF( self._export, CC.FLAGS_MIXED )
        
        ok_hbox = wx.BoxSizer( wx.HORIZONTAL )
        ok_hbox.AddF( self._ok, CC.FLAGS_MIXED )
        ok_hbox.AddF( self._cancel, CC.FLAGS_MIXED )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        vbox.AddF( self._listbook, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( add_remove_hbox, CC.FLAGS_SMALL_INDENT )
        vbox.AddF( ok_hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        #
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( 680, max( 720, y ) ) )
        
        self.SetDropTarget( ClientDragDrop.FileDropTarget( self.Import ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventAdd( self, event ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter a name for the subscription.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    name = dlg.GetValue()
                    
                    if self._listbook.NameExists( name ): raise HydrusExceptions.NameException( 'That name is already in use!' )
                    
                    if name == '': raise HydrusExceptions.NameException( 'Please enter a nickname for the subscription.' )
                    
                    page = self._Panel( self._listbook, name, is_new_subscription = True )
                    
                    self._listbook.AddPage( name, page, select = True )
                    
                except HydrusExceptions.NameException as e:
                    
                    wx.MessageBox( str( e ) )
                    
                    self.EventAdd( event )
                    
                
            
        
    
    def EventExport( self, event ):
        
        panel = self._listbook.GetCurrentPage()
        
        if panel is not None:
            
            subscription = panel.GetSubscription()
            
            name = subscription.GetName()
            
            dump = subscription.DumpToString()
            
            try:
                
                with wx.FileDialog( self, 'select where to export subscription', defaultFile = name + '.json', style = wx.FD_SAVE ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        path = HydrusData.ToUnicode( dlg.GetPath() )
                        
                        with open( path, 'wb' ) as f: f.write( dump )
                        
                    
                
            except:
                
                with wx.FileDialog( self, 'select where to export subscription', defaultFile = 'subscription.json', style = wx.FD_SAVE ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        path = HydrusData.ToUnicode( dlg.GetPath() )
                        
                        with open( path, 'wb' ) as f: f.write( dump )
                        
                    
                
            
        
    
    def EventOK( self, event ):
        
        all_pages = self._listbook.GetNamesToActivePages().values()
        
        try:
            
            for name in self._names_to_delete:
                
                HydrusGlobals.client_controller.Write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION, name )
                
            
            for page in all_pages:
                
                subscription = page.GetSubscription()
                
                HydrusGlobals.client_controller.Write( 'serialisable', subscription )
                
            
            HydrusGlobals.client_controller.pub( 'notify_new_subscriptions' )
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventRemove( self, event ):
        
        name = self._listbook.GetCurrentName()
        
        self._names_to_delete.add( name )
        
        self._listbook.DeleteCurrentPage()
        
    
    def Import( self, paths ):
        
        for path in paths:
            
            try:
                
                with open( path, 'rb' ) as f: data = f.read()
                
                subscription = HydrusSerialisable.CreateFromString( data )
                
                name = subscription.GetName()
                
                if self._listbook.NameExists( name ):
                    
                    message = 'A service already exists with that name. Overwrite it?'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            self._listbook.Select( name )
                            
                            page = self._listbook.GetNamesToActivePages()[ name ]
                            
                            page.Update( subscription )
                            
                        
                    
                else:
                    
                    page = self._Panel( self._listbook, name, is_new_subscription = True )
                    
                    page.Update( subscription )
                    
                    self._listbook.AddPage( name, page, select = True )
                    
                
            except:
                
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    class _Panel( wx.ScrolledWindow ):
        
        def __init__( self, parent, name, is_new_subscription = False ):
            
            wx.ScrolledWindow.__init__( self, parent )
            
            self._is_new_subscription = is_new_subscription
            
            if self._is_new_subscription:
                
                self._original_subscription = ClientImporting.Subscription( name )
                
            else:
                
                self._original_subscription = HydrusGlobals.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION, name )
                
            
            #
            
            self._query_panel = ClientGUICommon.StaticBox( self, 'site and query' )
            
            self._site_type = ClientGUICommon.BetterChoice( self._query_panel )
            
            site_types = []
            site_types.append( HC.SITE_TYPE_BOORU )
            site_types.append( HC.SITE_TYPE_DEVIANT_ART )
            site_types.append( HC.SITE_TYPE_GIPHY )
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
            
            self._period_days = wx.SpinCtrl( self._query_panel, min = 1, max = 1000 )
            
            self._info_panel = ClientGUICommon.StaticBox( self, 'info' )
            
            self._get_tags_if_redundant = wx.CheckBox( self._info_panel, label = 'get tags even if file already in db' )
            
            self._initial_file_limit = ClientGUICommon.NoneableSpinCtrl( self._info_panel, 'initial file limit', none_phrase = 'no limit', min = 1, max = 1000000 )
            self._initial_file_limit.SetToolTipString( 'If set, the first sync will add no more than this many files. Otherwise, it will get everything the gallery has.' )
            
            self._periodic_file_limit = ClientGUICommon.NoneableSpinCtrl( self._info_panel, 'periodic file limit', none_phrase = 'no limit', min = 1, max = 1000000 )
            self._periodic_file_limit.SetToolTipString( 'If set, normal syncs will add no more than this many files. Otherwise, they will get everything up until they find a file they have seen before.' )
            
            self._paused = wx.CheckBox( self._info_panel, label = 'paused' )
            
            self._seed_cache_button = wx.BitmapButton( self._info_panel, bitmap = CC.GlobalBMPs.seed_cache )
            self._seed_cache_button.Bind( wx.EVT_BUTTON, self.EventSeedCache )
            self._seed_cache_button.SetToolTipString( 'open detailed url cache status' )
            
            self._reset_cache_button = wx.Button( self._info_panel, label = '     reset url cache on dialog ok     ' )
            self._reset_cache_button.Bind( wx.EVT_BUTTON, self.EventResetCache )
            
            self._import_tag_options = ClientGUICollapsible.CollapsibleOptionsTags( self )
            
            self._import_file_options = ClientGUICollapsible.CollapsibleOptionsImportFiles( self )
            
            #
            
            self._SetControls()
            
            #
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            #
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._query_panel, label = 'Check subscription every ' ), CC.FLAGS_MIXED )
            hbox.AddF( self._period_days, CC.FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._query_panel, label = 'days' ), CC.FLAGS_MIXED )
            
            self._query_panel.AddF( self._site_type, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._query_panel.AddF( self._query, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._query_panel.AddF( self._booru_selector, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._query_panel.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            self._info_panel.AddF( self._get_tags_if_redundant, CC.FLAGS_LONE_BUTTON )
            self._info_panel.AddF( self._initial_file_limit, CC.FLAGS_LONE_BUTTON )
            self._info_panel.AddF( self._periodic_file_limit, CC.FLAGS_LONE_BUTTON )
            self._info_panel.AddF( self._paused, CC.FLAGS_LONE_BUTTON )
            
            last_checked_text = self._original_subscription.GetLastCheckedText()
            
            self._info_panel.AddF( wx.StaticText( self._info_panel, label = last_checked_text ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            seed_cache = self._original_subscription.GetSeedCache()
            
            seed_cache_text = str( seed_cache.GetSeedCount() ) + ' urls in cache'
            
            self._info_panel.AddF( wx.StaticText( self._info_panel, label = seed_cache_text ), CC.FLAGS_EXPAND_PERPENDICULAR )
            self._info_panel.AddF( self._seed_cache_button, CC.FLAGS_LONE_BUTTON )
            self._info_panel.AddF( self._reset_cache_button, CC.FLAGS_LONE_BUTTON )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._query_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._import_tag_options, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._import_file_options, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            self._reset_cache = False
            
            self.SetScrollRate( 0, 20 )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        def _ConfigureImportTagOptions( self ):
            
            gallery_identifier = self._GetGalleryIdentifier()
            
            ( namespaces, search_value ) = ClientDefaults.GetDefaultNamespacesAndSearchValue( gallery_identifier )
            
            new_options = HydrusGlobals.client_controller.GetNewOptions()
            
            import_tag_options = new_options.GetDefaultImportTagOptions( gallery_identifier )
            
            if not self._is_new_subscription:
                
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
            
        
        def _PresentForSiteType( self ):
            
            site_type = self._site_type.GetChoice()
            
            if site_type == HC.SITE_TYPE_BOORU:
                
                if self._booru_selector.GetCount() == 0:
                    
                    boorus = HydrusGlobals.client_controller.Read( 'remote_boorus' )
                    
                    for ( name, booru ) in boorus.items(): self._booru_selector.Append( name, booru )
                    
                    self._booru_selector.Select( 0 )
                    
                
                self._booru_selector.Show()
                
            else: self._booru_selector.Hide()
            
            wx.CallAfter( self._ConfigureImportTagOptions )
            
            self.Layout()
            
        
        def _SetControls( self ):
            
            ( gallery_identifier, gallery_stream_identifiers, query, period, get_tags_if_redundant, initial_file_limit, periodic_file_limit, paused, import_file_options, import_tag_options ) = self._original_subscription.ToTuple()
            
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
            
            self._period_days.SetValue( period / 86400 )
            
            self._get_tags_if_redundant.SetValue( get_tags_if_redundant )
            self._initial_file_limit.SetValue( initial_file_limit )
            self._periodic_file_limit.SetValue( periodic_file_limit )
            
            self._paused.SetValue( paused )
            
            self._reset_cache = False
            
            self._reset_cache_button.SetLabel( '     reset cache on dialog ok     ' )
            self._reset_cache_button.Enable()
            
            self._import_file_options.SetOptions( import_file_options )
            
            self._import_tag_options.SetOptions( import_tag_options )
            
        
        def EventBooruSelected( self, event ):
            
            self._ConfigureImportTagOptions()
            
        
        def EventResetCache( self, event ):
            
            message = '''Resetting this subscription's cache will delete ''' + HydrusData.ConvertIntToPrettyString( self._original_subscription.GetSeedCache().GetSeedCount() ) + ''' remembered urls, meaning when the subscription next runs, it will try to download those all over again. This may be expensive in time and data. Only do it if you are willing to wait. Do you want to do it?'''
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._reset_cache = True
                    
                    self._reset_cache_button.SetLabel( 'cache will be reset on dialog ok' )
                    self._reset_cache_button.Disable()
                    
                
            
        
        def EventSeedCache( self, event ):
            
            seed_cache = self._original_subscription.GetSeedCache()
            
            HydrusGlobals.client_controller.pub( 'show_seed_cache', seed_cache )
            
        
        def EventSiteChanged( self, event ): self._PresentForSiteType()
        
        def GetSubscription( self ):
            
            gallery_identifier = self._GetGalleryIdentifier()
            
            # in future, this can be harvested from some checkboxes or whatever for stream selection
            gallery_stream_identifiers = ClientDownloading.GetGalleryStreamIdentifiers( gallery_identifier )
            
            query = self._query.GetValue()
            
            period = self._period_days.GetValue() * 86400
            
            get_tags_if_redundant = self._get_tags_if_redundant.GetValue()
            initial_file_limit = self._initial_file_limit.GetValue()
            periodic_file_limit = self._periodic_file_limit.GetValue()
            
            paused = self._paused.GetValue()
            
            import_file_options = self._import_file_options.GetOptions()
            
            import_tag_options = self._import_tag_options.GetOptions()
            
            self._original_subscription.SetTuple( gallery_identifier, gallery_stream_identifiers, query, period, get_tags_if_redundant, initial_file_limit, periodic_file_limit, paused, import_file_options, import_tag_options )
            
            if self._reset_cache:
                
                self._original_subscription.Reset()
                
            
            return self._original_subscription
            
        
        def Update( self, subscription ):
            
            self._original_subscription = subscription
            
            self._SetControls()
            
        
    
class DialogManageTagCensorship( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._tag_services = ClientGUICommon.ListBook( self )
            self._tag_services.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.COMBINED_TAG, HC.TAG_REPOSITORY, HC.LOCAL_TAG ) )
            
            default_tag_repository_key = HC.options[ 'default_tag_repository' ]
            
            for service in services:
                
                service_key = service.GetServiceKey()
                name = service.GetName()
                
                if service_key == default_tag_repository_key: default_name = name
                
                page = self._Panel( self._tag_services, service_key )
                
                self._tag_services.AddPage( name, page )
                
            
            self._tag_services.Select( default_name )
            
        
        def ArrangeControls():
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._ok, CC.FLAGS_SMALL_INDENT )
            buttons.AddF( self._cancel, CC.FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            intro = "Here you can set which tags or classes of tags you do not want to see. Input something like 'series:' to censor an entire namespace, or ':' for all namespaced tags, and '' for all unnamespaced tags. You may have to refresh your current queries to see any changes."
            
            st = wx.StaticText( self, label = intro )
            
            st.Wrap( 350 )
            
            vbox.AddF( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._tag_services, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            self.SetInitialSize( ( -1, 480 ) )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'tag censorship' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        interested_actions = [ 'set_search_focus' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_services.GetCurrentPage()
        
        page.SetTagBoxFocus()
        
    
    def EventOK( self, event ):
        
        try:
            
            info = [ page.GetInfo() for page in self._tag_services.GetNamesToActivePages().values() if page.HasInfo() ]
            
            HydrusGlobals.client_controller.Write( 'tag_censorship', info )
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_services.GetCurrentPage()
        
        wx.CallAfter( page.SetTagBoxFocus )
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_key ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_key = service_key
            
            choice_pairs = [ ( 'blacklist', True ), ( 'whitelist', False ) ]
            
            self._blacklist = ClientGUICommon.RadioBox( self, 'type', choice_pairs )
            
            self._tags = ClientGUICommon.ListBoxTagsCensorship( self )
            
            self._tag_input = wx.TextCtrl( self, style = wx.TE_PROCESS_ENTER )
            self._tag_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDownTag )
            
            #
            
            ( blacklist, tags ) = HydrusGlobals.client_controller.Read( 'tag_censorship', service_key )
            
            if blacklist: self._blacklist.SetSelection( 0 )
            else: self._blacklist.SetSelection( 1 )
            
            self._tags.AddTags( tags )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._blacklist, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._tags, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._tag_input, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def EventKeyDownTag( self, event ):
            
            if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
                
                tag = self._tag_input.GetValue()
                
                self._tags.EnterTags( { tag } )
                
                self._tag_input.SetValue( '' )
                
            else: event.Skip()
            
        
        def GetInfo( self ):
            
            blacklist = self._blacklist.GetSelectedClientData()
            
            tags = self._tags.GetClientData()
            
            return ( self._service_key, blacklist, tags )
            
        
        def HasInfo( self ):
            
            ( service_key, blacklist, tags ) = self.GetInfo()
            
            return len( tags ) > 0
            
        
        def SetTagBoxFocus( self ): self._tag_input.SetFocus()
        
    
class DialogManageTagParents( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, tag = None ):
        
        def InitialiseControls():
            
            self._tag_repositories = ClientGUICommon.ListBook( self )
            self._tag_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.TAG_REPOSITORY, ) )
            
            for service in services:
                
                account = service.GetInfo( 'account' )
                
                if account.HasPermission( HC.POST_DATA ) or account.IsUnknownAccount():
                    
                    name = service.GetName()
                    service_key = service.GetServiceKey()
                    
                    self._tag_repositories.AddPageArgs( name, self._Panel, ( self._tag_repositories, service_key, tag ), {} )
                    
                
            
            page = self._Panel( self._tag_repositories, CC.LOCAL_TAG_SERVICE_KEY, tag )
            
            name = CC.LOCAL_TAG_SERVICE_KEY
            
            self._tag_repositories.AddPage( name, page )
            
            default_tag_repository_key = HC.options[ 'default_tag_repository' ]
            
            service = HydrusGlobals.client_controller.GetServicesManager().GetService( default_tag_repository_key )
            
            self._tag_repositories.Select( service.GetName() )
            
        
        def ArrangeControls():
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._ok, CC.FLAGS_SMALL_INDENT )
            buttons.AddF( self._cancel, CC.FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tag_repositories, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            self.SetInitialSize( ( 550, 780 ) )
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'tag parents' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        interested_actions = [ 'set_search_focus' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        page.SetTagBoxFocus()
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'set_search_focus': self._SetSearchFocus()
            else: event.Skip()
            
        
    
    def EventOK( self, event ):
        
        service_keys_to_content_updates = {}
        
        try:
            
            for page in self._tag_repositories.GetNamesToActivePages().values():
                
                ( service_key, content_updates ) = page.GetContentUpdates()
                
                service_keys_to_content_updates[ service_key ] = content_updates
                
            
            HydrusGlobals.client_controller.Write( 'content_updates', service_keys_to_content_updates )
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        wx.CallAfter( page.SetTagBoxFocus )
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_key, tags = None ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_key = service_key
            
            if service_key != CC.LOCAL_TAG_SERVICE_KEY:
                
                service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
                
                self._account = service.GetInfo( 'account' )
                
            
            self._original_statuses_to_pairs = HydrusGlobals.client_controller.Read( 'tag_parents', service_key )
            
            self._current_statuses_to_pairs = collections.defaultdict( set )
            
            self._current_statuses_to_pairs.update( { key : set( value ) for ( key, value ) in self._original_statuses_to_pairs.items() } )
            
            self._pairs_to_reasons = {}
            
            self._tag_parents = ClientGUICommon.SaneListCtrl( self, 250, [ ( '', 30 ), ( 'child', 160 ), ( 'parent', -1 ) ] )
            self._tag_parents.Bind( wx.EVT_LIST_ITEM_ACTIVATED, self.EventActivated )
            self._tag_parents.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventItemSelected )
            self._tag_parents.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventItemSelected )
            
            self._children = ClientGUICommon.ListBoxTagsStrings( self )
            self._parents = ClientGUICommon.ListBoxTagsStrings( self )
            
            expand_parents = True
            
            self._child_input = ClientGUICommon.AutoCompleteDropdownTagsWrite( self, self.EnterChildren, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, service_key )
            self._parent_input = ClientGUICommon.AutoCompleteDropdownTagsWrite( self, self.EnterParents, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, service_key )
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAddButton )
            self._add.Disable()
            
            #
            
            petitioned_pairs = set( self._original_statuses_to_pairs[ HC.PETITIONED ] )
            
            for ( status, pairs ) in self._original_statuses_to_pairs.items():
                
                if status != HC.DELETED:
                    
                    sign = HydrusData.ConvertStatusToPrefix( status )
                    
                    for ( child, parent ) in pairs:
                        
                        if status == HC.CURRENT and ( child, parent ) in petitioned_pairs:
                            
                            continue
                            
                        
                        self._tag_parents.Append( ( sign, child, parent ), ( status, child, parent ) )
                        
                    
                
            
            self._tag_parents.SortListItems( 2 )
            
            if tags is not None:
                
                self.EnterChildren( tags )
                
            
            #
            
            intro = 'Files with a tag on the left will also be given the tag on the right.'
            
            tags_box = wx.BoxSizer( wx.HORIZONTAL )
            
            tags_box.AddF( self._children, CC.FLAGS_EXPAND_BOTH_WAYS )
            tags_box.AddF( self._parents, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            input_box = wx.BoxSizer( wx.HORIZONTAL )
            
            input_box.AddF( self._child_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            input_box.AddF( self._parent_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( wx.StaticText( self, label = intro ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._tag_parents, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._add, CC.FLAGS_LONE_BUTTON )
            vbox.AddF( tags_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( input_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def _AddPairs( self, children, parent ):
            
            new_pairs = []
            current_pairs = []
            petitioned_pairs = []
            pending_pairs = []
            
            for child in children:
                
                pair = ( child, parent )
                
                if pair in self._current_statuses_to_pairs[ HC.PENDING ]:
                    
                    pending_pairs.append( pair )
                    
                elif pair in self._current_statuses_to_pairs[ HC.PETITIONED ]:
                    
                    petitioned_pairs.append( pair )
                    
                elif pair in self._original_statuses_to_pairs[ HC.CURRENT ]:
                    
                    current_pairs.append( pair )
                    
                elif self._CanAdd( pair ):
                    
                    new_pairs.append( pair )
                    
                
            
            affected_pairs = []
            
            if len( new_pairs ) > 0:
            
                do_it = True
                
                if self._service_key != CC.LOCAL_TAG_SERVICE_KEY:
                    
                    if self._account.HasPermission( HC.RESOLVE_PETITIONS ): reason = 'admin'
                    else:
                        
                        pair_strings = os.linesep.join( ( child + '->' + parent for ( child, parent ) in new_pairs ) )
                        
                        message = 'Enter a reason for:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'To be added. A janitor will review your petition.'
                        
                        with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
                            
                            if dlg.ShowModal() == wx.ID_OK:
                                
                                reason = dlg.GetValue()
                                
                            else: do_it = False
                            
                        
                    
                    if do_it:
                        
                        for pair in new_pairs: self._pairs_to_reasons[ pair ] = reason
                        
                    
                
                if do_it:
                    
                    self._current_statuses_to_pairs[ HC.PENDING ].update( new_pairs )
                    
                    affected_pairs.extend( new_pairs )
                    
                
            else:
                
                if len( current_pairs ) > 0:
                    
                    do_it = True
                    
                    if self._service_key != CC.LOCAL_TAG_SERVICE_KEY:
                        
                        pair_strings = os.linesep.join( ( child + '->' + parent for ( child, parent ) in current_pairs ) )
                        
                        if len( current_pairs ) > 1: message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Already exist.'
                        else: message = 'The pair ' + pair_strings + ' already exists.'
                        
                        with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose what to do.', yes_label = 'petition it', no_label = 'do nothing' ) as dlg:
                            
                            if dlg.ShowModal() == wx.ID_YES:
                                
                                if self._account.HasPermission( HC.RESOLVE_PETITIONS ): reason = 'admin'
                                else:
                                    
                                    message = 'Enter a reason for this pair to be removed. A janitor will review your petition.'
                                    
                                    with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
                                        
                                        if dlg.ShowModal() == wx.ID_OK:
                                            
                                            reason = dlg.GetValue()
                                            
                                        else: do_it = False
                                        
                                    
                                
                                if do_it:
                                    
                                    for pair in current_pairs: self._pairs_to_reasons[ pair ] = reason
                                    
                                
                            
                        
                    
                    if do_it:
                        
                        self._current_statuses_to_pairs[ HC.PETITIONED ].update( current_pairs )
                        
                        affected_pairs.extend( current_pairs )
                        
                    
                
                if len( pending_pairs ) > 0:
                    
                    pair_strings = os.linesep.join( ( child + '->' + parent for ( child, parent ) in pending_pairs ) )
                    
                    if len( pending_pairs ) > 1: message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Are pending.'
                    else: message = 'The pair ' + pair_strings + ' is pending.'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose what to do.', yes_label = 'rescind the pend', no_label = 'do nothing' ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            self._current_statuses_to_pairs[ HC.PENDING ].difference_update( pending_pairs )
                            
                            affected_pairs.extend( pending_pairs )
                            
                        
                    
                
                if len( petitioned_pairs ) > 0:
                    
                    pair_strings = ', '.join( ( child + '->' + parent for ( child, parent ) in petitioned_pairs ) )
                    
                    if len( petitioned_pairs ) > 1: message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Are petitioned.'
                    else: message = 'The pair ' + pair_strings + ' is petitioned.'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose what to do.', yes_label = 'rescind the petition', no_label = 'do nothing' ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            self._current_statuses_to_pairs[ HC.PETITIONED ].difference_update( petitioned_pairs )
                            
                            affected_pairs.extend( petitioned_pairs )
                            
                        
                    
                
            
            if len( affected_pairs ) > 0:
                
                for pair in affected_pairs:
                    
                    self._RefreshPair( pair )
                    
                
                self._tag_parents.SortListItems()
                
            
        
        def _CanAdd( self, potential_pair ):
            
            ( potential_child, potential_parent ) = potential_pair
            
            if potential_child == potential_parent: return False
            
            current_pairs = self._current_statuses_to_pairs[ HC.CURRENT ].union( self._current_statuses_to_pairs[ HC.PENDING ] )
            
            current_children = { child for ( child, parent ) in current_pairs }
            
            # test for loops
            
            if potential_parent in current_children:
                
                simple_children_to_parents = ClientCaches.BuildSimpleChildrenToParents( current_pairs )
                
                if ClientCaches.LoopInSimpleChildrenToParents( simple_children_to_parents, potential_child, potential_parent ):
                    
                    wx.MessageBox( 'Adding ' + potential_child + '->' + potential_parent + ' would create a loop!' )
                    
                    return False
                    
                
            
            return True
            
        
        def _RefreshPair( self, pair ):
            
            ( child, parent ) = pair
            
            for status in ( HC.CURRENT, HC.DELETED, HC.PENDING, HC.PETITIONED ):
                
                if self._tag_parents.HasClientData( ( status, child, parent ) ):
                    
                    index = self._tag_parents.GetIndexFromClientData( ( status, child, parent ) )
                    
                    self._tag_parents.DeleteItem( index )
                    
                    break
                    
                
            
            new_status = None
            
            if pair in self._current_statuses_to_pairs[ HC.PENDING ]:
                
                new_status = HC.PENDING
                
            elif pair in self._current_statuses_to_pairs[ HC.PETITIONED ]:
                
                new_status = HC.PETITIONED
                
            elif pair in self._original_statuses_to_pairs[ HC.CURRENT ]:
                
                new_status = HC.CURRENT
                
            
            if new_status is not None:
                
                sign = HydrusData.ConvertStatusToPrefix( new_status )
                
                self._tag_parents.Append( ( sign, child, parent ), ( new_status, child, parent ) )
                
            
        
        def _SetButtonStatus( self ):
            
            if len( self._children.GetTags() ) == 0 or len( self._parents.GetTags() ) == 0: self._add.Disable()
            else: self._add.Enable()
            
        
        def EnterChildren( self, tags, parents = None ):
            
            if len( tags ) > 0:
                
                self._parents.RemoveTags( tags )
                
                self._children.AddTags( tags )
                
                self._SetButtonStatus()
                
            
        
        def EnterParents( self, tags, parents = None ):
            
            if len( tags ) > 0:
                
                self._children.RemoveTags( tags )
                
                self._parents.AddTags( tags )
                
                self._SetButtonStatus()
                
            
        
        def EventActivated( self, event ):
            
            parents_to_children = collections.defaultdict( set )
            
            all_selected = self._tag_parents.GetAllSelected()
            
            for selection in all_selected:
                
                ( status, child, parent ) = self._tag_parents.GetClientData( selection )
                
                parents_to_children[ parent ].add( child )
                
            
            if len( parents_to_children ) > 0:
                
                for ( parent, children ) in parents_to_children.items():
                    
                    self._AddPairs( children, parent )
                    
                
            
        
        def EventAddButton( self, event ):
            
            children = self._children.GetTags()
            parents = self._parents.GetTags()
            
            for parent in parents: self._AddPairs( children, parent )
            
            self._children.SetTags( [] )
            self._parents.SetTags( [] )
            
            self._SetButtonStatus()
            
        
        def EventItemSelected( self, event ):
            
            self._SetButtonStatus()
            
        
        def GetContentUpdates( self ):
            
            # we make it manually here because of the mass pending tags done (but not undone on a rescind) on a pending pair!
            # we don't want to send a pend and then rescind it, cause that will spam a thousand bad tags and not undo it
            
            content_updates = []
            
            if self._service_key == CC.LOCAL_TAG_SERVICE_KEY:
                
                for pair in self._current_statuses_to_pairs[ HC.PENDING ]: content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_ADD, pair ) )
                for pair in self._current_statuses_to_pairs[ HC.PETITIONED ]: content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_DELETE, pair ) )
                
            else:
                
                current_pending = self._current_statuses_to_pairs[ HC.PENDING ]
                original_pending = self._original_statuses_to_pairs[ HC.PENDING ]
                
                current_petitioned = self._current_statuses_to_pairs[ HC.PETITIONED ]
                original_petitioned = self._original_statuses_to_pairs[ HC.PETITIONED ]
                
                new_pends = current_pending.difference( original_pending )
                rescinded_pends = original_pending.difference( current_pending )
                
                new_petitions = current_petitioned.difference( original_petitioned )
                rescinded_petitions = original_petitioned.difference( current_petitioned )
                
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PEND, ( pair, self._pairs_to_reasons[ pair ] ) ) for pair in new_pends ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_RESCIND_PEND, pair ) for pair in rescinded_pends ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PETITION, ( pair, self._pairs_to_reasons[ pair ] ) ) for pair in new_petitions ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_RESCIND_PETITION, pair ) for pair in rescinded_petitions ) )
                
            
            return ( self._service_key, content_updates )
            
        
        def SetTagBoxFocus( self ):
            
            if len( self._children.GetTags() ) == 0: self._child_input.SetFocus()
            else: self._parent_input.SetFocus()
            
        
    
class DialogManageTagSiblings( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, tag = None ):
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'tag siblings' )
        
        self._tag_repositories = ClientGUICommon.ListBook( self )
        self._tag_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        page = self._Panel( self._tag_repositories, CC.LOCAL_TAG_SERVICE_KEY, tag )
        
        name = CC.LOCAL_TAG_SERVICE_KEY
        
        self._tag_repositories.AddPage( name, page )
        
        services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.TAG_REPOSITORY, ) )
        
        for service in services:
            
            account = service.GetInfo( 'account' )
            
            if account.HasPermission( HC.POST_DATA ) or account.IsUnknownAccount():
                
                name = service.GetName()
                service_key = service.GetServiceKey()
                
                self._tag_repositories.AddPageArgs( name, self._Panel, ( self._tag_repositories, service_key, tag ), {} )
                
            
        
        default_tag_repository_key = HC.options[ 'default_tag_repository' ]
        
        service = HydrusGlobals.client_controller.GetServicesManager().GetService( default_tag_repository_key )
        
        self._tag_repositories.Select( service.GetName() )
        
        #
        
        buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        buttons.AddF( self._ok, CC.FLAGS_SMALL_INDENT )
        buttons.AddF( self._cancel, CC.FLAGS_SMALL_INDENT )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._tag_repositories, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        self.SetInitialSize( ( 550, 780 ) )
        
        #
        
        interested_actions = [ 'set_search_focus' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        page.SetTagBoxFocus()
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'set_search_focus': self._SetSearchFocus()
            else: event.Skip()
            
        
    
    def EventOK( self, event ):
        
        service_keys_to_content_updates = {}
        
        try:
            
            for page in self._tag_repositories.GetNamesToActivePages().values():
                
                ( service_key, content_updates ) = page.GetContentUpdates()
                
                service_keys_to_content_updates[ service_key ] = content_updates
                
            
            HydrusGlobals.client_controller.Write( 'content_updates', service_keys_to_content_updates )
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        wx.CallAfter( page.SetTagBoxFocus )
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_key, tags = None ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_key = service_key
            
            if self._service_key != CC.LOCAL_TAG_SERVICE_KEY:
                
                service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
                
                self._account = service.GetInfo( 'account' )
                
            
            self._original_statuses_to_pairs = HydrusGlobals.client_controller.Read( 'tag_siblings', service_key )
            
            self._current_statuses_to_pairs = collections.defaultdict( set )
            
            self._current_statuses_to_pairs.update( { key : set( value ) for ( key, value ) in self._original_statuses_to_pairs.items() } )
            
            self._pairs_to_reasons = {}
            
            self._current_new = None
            
            self._tag_siblings = ClientGUICommon.SaneListCtrl( self, 250, [ ( '', 30 ), ( 'old', 160 ), ( 'new', -1 ) ] )
            self._tag_siblings.Bind( wx.EVT_LIST_ITEM_ACTIVATED, self.EventActivated )
            self._tag_siblings.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventItemSelected )
            self._tag_siblings.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventItemSelected )
            
            removed_callable = lambda tags: 1
            
            self._old_siblings = ClientGUICommon.ListBoxTagsStrings( self )
            self._new_sibling = wx.StaticText( self )
            
            expand_parents = False
            
            self._old_input = ClientGUICommon.AutoCompleteDropdownTagsWrite( self, self.EnterOlds, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, service_key )
            self._new_input = ClientGUICommon.AutoCompleteDropdownTagsWrite( self, self.SetNew, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, service_key )
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAddButton )
            self._add.Disable()
            
            #
            
            petitioned_pairs = set( self._original_statuses_to_pairs[ HC.PETITIONED ] )
            
            for ( status, pairs ) in self._original_statuses_to_pairs.items():
                
                if status != HC.DELETED:
                    
                    sign = HydrusData.ConvertStatusToPrefix( status )
                    
                    for ( old, new ) in pairs:
                        
                        if status == HC.CURRENT and ( old, new ) in petitioned_pairs:
                            
                            continue
                            
                        
                        self._tag_siblings.Append( ( sign, old, new ), ( status, old, new ) )
                        
                    
                
            
            self._tag_siblings.SortListItems( 2 )
            
            if tags is not None:
                
                self.EnterOlds( tags )
                
            
            #
            
            intro = 'Tags on the left will be replaced by those on the right.'
            
            new_sibling_box = wx.BoxSizer( wx.VERTICAL )
            
            new_sibling_box.AddF( ( 10, 10 ), CC.FLAGS_EXPAND_BOTH_WAYS )
            new_sibling_box.AddF( self._new_sibling, CC.FLAGS_EXPAND_PERPENDICULAR )
            new_sibling_box.AddF( ( 10, 10 ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            text_box = wx.BoxSizer( wx.HORIZONTAL )
            
            text_box.AddF( self._old_siblings, CC.FLAGS_EXPAND_BOTH_WAYS )
            text_box.AddF( new_sibling_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            input_box = wx.BoxSizer( wx.HORIZONTAL )
            
            input_box.AddF( self._old_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            input_box.AddF( self._new_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( wx.StaticText( self, label = intro ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._tag_siblings, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._add, CC.FLAGS_LONE_BUTTON )
            vbox.AddF( text_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( input_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            
        
        def _AddPairs( self, olds, new ):
            
            new_pairs = []
            current_pairs = []
            petitioned_pairs = []
            pending_pairs = []
            
            for old in olds:
                
                pair = ( old, new )
                
                if pair in self._current_statuses_to_pairs[ HC.PENDING ]:
                    
                    pending_pairs.append( pair )
                    
                elif pair in self._current_statuses_to_pairs[ HC.PETITIONED ]:
                    
                    petitioned_pairs.append( pair )
                    
                elif pair in self._original_statuses_to_pairs[ HC.CURRENT ]:
                    
                    current_pairs.append( pair )
                    
                elif self._CanAdd( pair ):
                    
                    new_pairs.append( pair )
                    
                
            
            affected_pairs = []
            
            if len( new_pairs ) > 0:
                
                do_it = True
                
                if self._service_key != CC.LOCAL_TAG_SERVICE_KEY:
                    
                    if self._account.HasPermission( HC.RESOLVE_PETITIONS ): reason = 'admin'
                    else:
                        
                        pair_strings = os.linesep.join( ( old + '->' + new for ( old, new ) in new_pairs ) )
                        
                        message = 'Enter a reason for:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'To be added. A janitor will review your petition.'
                        
                        with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
                            
                            if dlg.ShowModal() == wx.ID_OK:
                                
                                reason = dlg.GetValue()
                                
                            else: do_it = False
                            
                        
                    
                    if do_it:
                        
                        for pair in new_pairs: self._pairs_to_reasons[ pair ] = reason
                        
                    
                
                if do_it:
                    
                    self._current_statuses_to_pairs[ HC.PENDING ].update( new_pairs )
                    
                    affected_pairs.extend( new_pairs )
                    
                
            else:
                
                if len( current_pairs ) > 0:
                    
                    do_it = True
                    
                    if self._service_key != CC.LOCAL_TAG_SERVICE_KEY:
                        
                        pair_strings = os.linesep.join( ( old + '->' + new for ( old, new ) in current_pairs ) )
                        
                        if len( current_pairs ) > 1: message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Already exist.'
                        else: message = 'The pair ' + pair_strings + ' already exists.'
                        
                        with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose what to do.', yes_label = 'petition it', no_label = 'do nothing' ) as dlg:
                            
                            if dlg.ShowModal() == wx.ID_YES:
                                
                                if self._account.HasPermission( HC.RESOLVE_PETITIONS ): reason = 'admin'
                                else:
                                    
                                    message = 'Enter a reason for this pair to be removed. A janitor will review your petition.'
                                    
                                    with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
                                        
                                        if dlg.ShowModal() == wx.ID_OK: reason = dlg.GetValue()
                                        else: do_it = False
                                        
                                    
                                
                                if do_it:
                                    
                                    for pair in current_pairs: self._pairs_to_reasons[ pair ] = reason
                                    
                                
                            
                        
                    
                    if do_it:
                        
                        self._current_statuses_to_pairs[ HC.PETITIONED ].update( current_pairs )
                        
                        affected_pairs.extend( current_pairs )
                        
                    
                    
                
                if len( pending_pairs ) > 0:
                    
                    pair_strings = os.linesep.join( ( old + '->' + new for ( old, new ) in pending_pairs ) )
                    
                    if len( pending_pairs ) > 1: message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Are pending.'
                    else: message = 'The pair ' + pair_strings + ' is pending.'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose what to do.', yes_label = 'rescind the pend', no_label = 'do nothing' ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            self._current_statuses_to_pairs[ HC.PENDING ].difference_update( pending_pairs )
                            
                            affected_pairs.extend( pending_pairs )
                            
                        
                    
                
                if len( petitioned_pairs ) > 0:
                    
                    pair_strings = ', '.join( ( old + '->' + new for ( old, new ) in petitioned_pairs ) )
                    
                    if len( petitioned_pairs ) > 1: message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Are petitioned.'
                    else: message = 'The pair ' + pair_strings + ' is petitioned.'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose what to do.', yes_label = 'rescind the petition', no_label = 'do nothing' ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            self._current_statuses_to_pairs[ HC.PETITIONED ].difference_update( petitioned_pairs )
                            
                            affected_pairs.extend( petitioned_pairs )
                            
                        
                    
                
            
            if len( affected_pairs ) > 0:
                
                for pair in affected_pairs:
                    
                    self._RefreshPair( pair )
                    
                
                self._tag_siblings.SortListItems()
                
            
        
        def _CanAdd( self, potential_pair ):
            
            ( potential_old, potential_new ) = potential_pair
            
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
                        
                        wx.MessageBox( 'Adding ' + potential_old + '->' + potential_new + ' would create a loop!' )
                        
                        return False
                        
                    
                
            
            return True
            
        
        def _RefreshPair( self, pair ):
            
            ( old, new ) = pair
            
            for status in ( HC.CURRENT, HC.DELETED, HC.PENDING, HC.PETITIONED ):
                
                if self._tag_siblings.HasClientData( ( status, old, new ) ):
                    
                    index = self._tag_siblings.GetIndexFromClientData( ( status, old, new ) )
                    
                    self._tag_siblings.DeleteItem( index )
                    
                    break
                    
                
            
            new_status = None
            
            if pair in self._current_statuses_to_pairs[ HC.PENDING ]:
                
                new_status = HC.PENDING
                
            elif pair in self._current_statuses_to_pairs[ HC.PETITIONED ]:
                
                new_status = HC.PETITIONED
                
            elif pair in self._original_statuses_to_pairs[ HC.CURRENT ]:
                
                new_status = HC.CURRENT
                
            
            if new_status is not None:
                
                sign = HydrusData.ConvertStatusToPrefix( new_status )
                
                self._tag_siblings.Append( ( sign, old, new ), ( new_status, old, new ) )
                
            
        
        def _SetButtonStatus( self ):
            
            if self._current_new is None or len( self._old_siblings.GetTags() ) == 0: self._add.Disable()
            else: self._add.Enable()
            
        
        def EnterOlds( self, olds ):
            
            potential_olds = olds
            
            olds = set()
            
            for potential_old in potential_olds:
                
                do_it = True
                
                current_pairs = self._current_statuses_to_pairs[ HC.CURRENT ].union( self._current_statuses_to_pairs[ HC.PENDING ] )
                
                current_olds = { current_old for ( current_old, current_new ) in current_pairs }
                
                while potential_old in current_olds:
                    
                    olds_to_news = dict( current_pairs )
                    
                    conflicting_new = olds_to_news[ potential_old ]
                    
                    message = 'There already is a relationship set for ' + potential_old + '! It goes to ' + conflicting_new + '.'
                    message += os.linesep * 2
                    message += 'You cannot have two siblings for the same original term.'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose what to do.', yes_label = 'I want to overwrite the existing record', no_label = 'do nothing' ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES:
                            
                            self._AddPairs( [ potential_old ], conflicting_new )
                            
                        else:
                            
                            do_it = False
                            
                            break
                            
                        
                    
                    current_pairs = self._current_statuses_to_pairs[ HC.CURRENT ].union( self._current_statuses_to_pairs[ HC.PENDING ] )
                    
                    current_olds = { current_old for ( current_old, current_new ) in current_pairs }
                    
                
                if do_it:
                    
                    olds.add( potential_old )
                    
                
            
            if self._current_new in olds:
                
                self.SetNew( set() )
                
            
            self._old_siblings.EnterTags( olds )
            
            self._SetButtonStatus()
            
        
        def EventActivated( self, event ):
            
            news_to_olds = collections.defaultdict( set )
            
            all_selected = self._tag_siblings.GetAllSelected()
            
            for selection in all_selected:
                
                ( status, old, new ) = self._tag_siblings.GetClientData( selection )
                
                news_to_olds[ new ].add( old )
                
            
            if len( news_to_olds ) > 0:
                
                for ( new, olds ) in news_to_olds.items():
                    
                    self._AddPairs( olds, new )
                    
                
            
        
        def EventAddButton( self, event ):
            
            if self._current_new is not None and len( self._old_siblings.GetTags() ) > 0:
                
                olds = self._old_siblings.GetTags()
                
                self._AddPairs( olds, self._current_new )
                
                self._old_siblings.SetTags( set() )
                self.SetNew( set() )
                
                self._SetButtonStatus()
                
            
        
        def EventItemSelected( self, event ):
            
            self._SetButtonStatus()
            
        
        def GetContentUpdates( self ):
            
            # we make it manually here because of the mass pending tags done (but not undone on a rescind) on a pending pair!
            # we don't want to send a pend and then rescind it, cause that will spam a thousand bad tags and not undo it
            
            # actually, we don't do this for siblings, but we do for parents, and let's have them be the same
            
            content_updates = []
            
            if self._service_key == CC.LOCAL_TAG_SERVICE_KEY:
                
                for pair in self._current_statuses_to_pairs[ HC.PENDING ]: content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, pair ) )
                for pair in self._current_statuses_to_pairs[ HC.PETITIONED ]: content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DELETE, pair ) )
                
            else:
                
                current_pending = self._current_statuses_to_pairs[ HC.PENDING ]
                original_pending = self._original_statuses_to_pairs[ HC.PENDING ]
                
                current_petitioned = self._current_statuses_to_pairs[ HC.PETITIONED ]
                original_petitioned = self._original_statuses_to_pairs[ HC.PETITIONED ]
                
                new_pends = current_pending.difference( original_pending )
                rescinded_pends = original_pending.difference( current_pending )
                
                new_petitions = current_petitioned.difference( original_petitioned )
                rescinded_petitions = original_petitioned.difference( current_petitioned )
                
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PEND, ( pair, self._pairs_to_reasons[ pair ] ) ) for pair in new_pends ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_RESCIND_PEND, pair ) for pair in rescinded_pends ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PETITION, ( pair, self._pairs_to_reasons[ pair ] ) ) for pair in new_petitions ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_RESCIND_PETITION, pair ) for pair in rescinded_petitions ) )
                
            
            return ( self._service_key, content_updates )
            
        
        def SetNew( self, new_tags ):
            
            if len( new_tags ) == 0:
                
                self._new_sibling.SetLabel( '' )
                
                self._current_new = None
                
            else:
                
                new = list( new_tags )[0]
                
                self._old_siblings.RemoveTags( { new } )
                
                self._new_sibling.SetLabel( new )
                
                self._current_new = new
                
            
            self._SetButtonStatus()
            
        
        def SetTagBoxFocus( self ):
            
            if len( self._old_siblings.GetTags() ) == 0: self._old_input.SetFocus()
            else: self._new_input.SetFocus()
            
        
    
class DialogManageTags( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, file_service_key, media, canvas_key = None ):
        
        def InitialiseControls():
            
            if canvas_key is not None:
                
                self._next = wx.Button( self, label = '->' )
                self._next.Bind( wx.EVT_BUTTON, self.EventNext )
                
                self._delete = wx.Button( self, label = 'delete' )
                self._delete.Bind( wx.EVT_BUTTON, self.EventDelete )
                
                self._previous = wx.Button( self, label = '<-' )
                self._previous.Bind( wx.EVT_BUTTON, self.EventPrevious )
                
            
            self._tag_repositories = ClientGUICommon.ListBook( self )
            self._tag_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
            
            self._apply = wx.Button( self, id = wx.ID_OK, label = 'apply' )
            self._apply.Bind( wx.EVT_BUTTON, self.EventOK )
            self._apply.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.TAG_REPOSITORY, HC.LOCAL_TAG ) )
            
            name_to_select = None
            
            for service in services:
                
                service_key = service.GetServiceKey()
                service_type = service.GetServiceType()
                name = service.GetName()
                
                page = self._Panel( self._tag_repositories, self._file_service_key, service.GetServiceKey(), media )
                
                self._tag_repositories.AddPage( name, page )
                
                if service_key == HC.options[ 'default_tag_repository' ]: name_to_select = name
                
            
            if name_to_select is not None: self._tag_repositories.Select( name_to_select )
            
        
        def ArrangeControls():
            
            buttonbox = wx.BoxSizer( wx.HORIZONTAL )
            
            buttonbox.AddF( self._apply, CC.FLAGS_MIXED )
            buttonbox.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            if canvas_key is not None:
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( self._previous, CC.FLAGS_MIXED )
                hbox.AddF( ( 20, 20 ), CC.FLAGS_EXPAND_BOTH_WAYS )
                hbox.AddF( self._delete, CC.FLAGS_MIXED )
                hbox.AddF( ( 20, 20 ), CC.FLAGS_EXPAND_BOTH_WAYS )
                hbox.AddF( self._next, CC.FLAGS_MIXED )
                
                vbox.AddF( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            vbox.AddF( self._tag_repositories, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttonbox, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( remember, size ) = HC.options[ 'tag_dialog_size' ]
            
            if remember and size is not None:
                
                self.SetInitialSize( size )
                
            else:
                
                ( x, y ) = self.GetEffectiveMinSize()
                
                ( parent_window_width, parent_window_height ) = parent.GetTopLevelParent().GetSize()
                
                self.SetInitialSize( ( x + 200, max( 500, parent_window_height - 200 ) ) )
                
            
        
        self._file_service_key = file_service_key
        
        self._hashes = set()
        
        self._canvas_key = canvas_key
        
        self._current_media = media
        
        for m in media: self._hashes.update( m.GetHashes() )
        
        ( remember, position ) = HC.options[ 'tag_dialog_position' ]
        
        if remember and position is not None:
            
            my_position = 'custom'
            
            wx.CallAfter( self.SetPosition, position )
            
        else:
            
            my_position = 'topleft'
            
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'manage tags for ' + HydrusData.ConvertIntToPrettyString( len( self._hashes ) ) + ' files', position = my_position )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.RefreshAcceleratorTable()
        
        if self._canvas_key is not None: HydrusGlobals.client_controller.sub( self, 'CanvasHasNewMedia', 'canvas_new_display_media' )
        
    
    def _ClearPanels( self ):
        
        for page in self._tag_repositories.GetNamesToActivePages().values(): page.SetMedia( set() )
        
    
    def _CommitCurrentChanges( self ):
        
        service_keys_to_content_updates = {}
        
        for page in self._tag_repositories.GetNamesToActivePages().values():
            
            ( service_key, content_updates ) = page.GetContentUpdates()
            
            if len( content_updates ) > 0: service_keys_to_content_updates[ service_key ] = content_updates
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        page.SetTagBoxFocus()
        
    
    def CanvasHasNewMedia( self, canvas_key, new_media ):
        
        if canvas_key == self._canvas_key:
            
            self._current_media = new_media
            
            for page in self._tag_repositories.GetNamesToActivePages().values(): page.SetMedia( ( new_media, ) )
            
        
    
    def EventDelete( self, event ):
        
        do_it = False
        
        locations_manager = self._current_media.GetLocationsManager()
        
        if CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent():
            
            if not HC.options[ 'confirm_trash' ]:
                
                do_it = True
                
            
            text = 'Send this file to the trash?'
            
            service_key = CC.LOCAL_FILE_SERVICE_KEY
            
        elif CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent():
            
            text = 'Permanently delete this file?'
            
            service_key = CC.TRASH_SERVICE_KEY
            
        else:
            
            return
            
        
        if not do_it:
            
            with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    do_it = True
                    
                
            
        
        if do_it:
            
            self._CommitCurrentChanges()
            
            HydrusGlobals.client_controller.Write( 'content_updates', { service_key : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( self._current_media.GetHash(), ) ) ] } )
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'canvas_show_next': self.EventNext( event )
            elif command == 'canvas_show_previous': self.EventPrevious( event )
            elif command == 'manage_tags': self.EventOK( event )
            elif command == 'set_search_focus': self._SetSearchFocus()
            elif command == 'ok': self.EventOK( event )
            else: event.Skip()
            
        
    
    def EventNext( self, event ):
        
        if self._canvas_key is not None:
            
            self._CommitCurrentChanges()
            
            self._ClearPanels()
            
            HydrusGlobals.client_controller.pub( 'canvas_show_next', self._canvas_key )
            
        
    
    def EventOK( self, event ):
        
        try:
            
            self._CommitCurrentChanges()
            
            ( remember, size ) = HC.options[ 'tag_dialog_size' ]
            
            current_size = self.GetSizeTuple()
            
            if remember and size != current_size:
                
                HC.options[ 'tag_dialog_size' ] = ( remember, current_size )
                
                HydrusGlobals.client_controller.Write( 'save_options', HC.options )
                
            
            ( remember, position ) = HC.options[ 'tag_dialog_position' ]
            
            current_position = self.GetPositionTuple()
            
            if remember and position != current_position:
                
                HC.options[ 'tag_dialog_position' ] = ( remember, current_position )
                
                HydrusGlobals.client_controller.Write( 'save_options', HC.options )
                
            
        finally: self.EndModal( wx.ID_OK )
        
    
    def EventPrevious( self, event ):
        
        if self._canvas_key is not None:
            
            self._CommitCurrentChanges()
            
            self._ClearPanels()
            
            HydrusGlobals.client_controller.pub( 'canvas_show_previous', self._canvas_key )
            
        
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        wx.CallAfter( page.SetTagBoxFocus )
        
    
    def RefreshAcceleratorTable( self ):
        
        interested_actions = [ 'manage_tags', 'set_search_focus' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, file_service_key, tag_service_key, media ):
            
            wx.Panel.__init__( self, parent )
            
            self._file_service_key = file_service_key
            self._tag_service_key = tag_service_key
            
            self._i_am_local_tag_service = self._tag_service_key == CC.LOCAL_TAG_SERVICE_KEY
            
            if not self._i_am_local_tag_service:
                
                service = HydrusGlobals.client_controller.GetServicesManager().GetService( tag_service_key )
                
                try: self._account = service.GetInfo( 'account' )
                except: self._account = HydrusData.GetUnknownAccount()
                
            
            self._tags_box_sorter = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'tags' )
            
            self._tags_box = ClientGUICommon.ListBoxTagsSelectionTagsDialog( self._tags_box_sorter, self.AddTags )
            
            self._tags_box_sorter.SetTagsBox( self._tags_box )
            
            self._show_deleted_checkbox = wx.CheckBox( self._tags_box_sorter, label = 'show deleted' )
            self._show_deleted_checkbox.Bind( wx.EVT_CHECKBOX, self.EventShowDeleted )
            
            self._tags_box_sorter.AddF( self._show_deleted_checkbox, CC.FLAGS_LONE_BUTTON )
            
            expand_parents = True
            
            self._add_tag_box = ClientGUICommon.AutoCompleteDropdownTagsWrite( self, self.AddTags, expand_parents, self._file_service_key, self._tag_service_key, null_entry_callable = self.Ok )
            
            self._modify_mappers = wx.Button( self, label = 'Modify mappers' )
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
            
            self._tags_box.ChangeTagRepository( self._tag_service_key )
            
            self.SetMedia( media )
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            if self._i_am_local_tag_service: self._modify_mappers.Hide()
            else:
                
                if not self._account.HasPermission( HC.MANAGE_USERS ): self._modify_mappers.Hide()
                
            
            copy_paste_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            copy_paste_hbox.AddF( self._copy_tags, CC.FLAGS_MIXED )
            copy_paste_hbox.AddF( self._paste_tags, CC.FLAGS_MIXED )
            copy_paste_hbox.AddF( self._remove_tags, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tags_box_sorter, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._add_tag_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( copy_paste_hbox, CC.FLAGS_BUTTON_SIZER )
            vbox.AddF( self._modify_mappers, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
        
        def _AddTag( self, tag, only_add = False, only_remove = False, reason = None ):
            
            tag_managers = [ m.GetTagsManager() for m in self._media ]
            
            num_files = len( self._media )
            
            num_current = len( [ 1 for tag_manager in tag_managers if tag in tag_manager.GetCurrent( self._tag_service_key ) ] )
            
            choices = []
            
            sibling_tag = HydrusGlobals.client_controller.GetManager( 'tag_siblings' ).GetSibling( tag )
            
            if sibling_tag is not None:
                
                num_sibling_current = len( [ 1 for tag_manager in tag_managers if sibling_tag in tag_manager.GetCurrent( self._tag_service_key ) ] )
                
            
            if self._i_am_local_tag_service:
                
                if not only_remove:
                    
                    if num_current < num_files:
                        
                        choices.append( ( 'add ' + tag + ' to ' + HydrusData.ConvertIntToPrettyString( num_files - num_current ) + ' files', ( HC.CONTENT_UPDATE_ADD, tag ) ) )
                        
                    
                    if sibling_tag is not None and num_sibling_current < num_files:
                        
                        choices.append( ( 'add ' + sibling_tag + ' to ' + HydrusData.ConvertIntToPrettyString( num_files - num_current ) + ' files', ( HC.CONTENT_UPDATE_ADD, sibling_tag ) ) )
                        
                    
                
                if not only_add:
                    
                    if num_current > 0:
                        
                        choices.append( ( 'delete ' + tag + ' from ' + HydrusData.ConvertIntToPrettyString( num_current ) + ' files', ( HC.CONTENT_UPDATE_DELETE, tag ) ) )
                        
                    
                
            else:
                
                num_pending = len( [ 1 for tag_manager in tag_managers if tag in tag_manager.GetPending( self._tag_service_key ) ] )
                num_petitioned = len( [ 1 for tag_manager in tag_managers if tag in tag_manager.GetPetitioned( self._tag_service_key ) ] )
                
                if not only_remove:
                    
                    if num_current + num_pending < num_files: choices.append( ( 'pend ' + tag + ' to ' + HydrusData.ConvertIntToPrettyString( num_files - ( num_current + num_pending ) ) + ' files', ( HC.CONTENT_UPDATE_PEND, tag ) ) )
                    
                    if sibling_tag is not None:
                        
                        num_sibling_pending = len( [ 1 for tag_manager in tag_managers if sibling_tag in tag_manager.GetPending( self._tag_service_key ) ] )
                        
                        if num_sibling_current + num_sibling_pending < num_files:
                            
                            choices.append( ( 'pend ' + sibling_tag + ' to ' + HydrusData.ConvertIntToPrettyString( num_files - num_current ) + ' files', ( HC.CONTENT_UPDATE_PEND, sibling_tag ) ) )
                            
                        
                    
                
                if not only_add:
                    
                    if num_current > num_petitioned and not only_add: choices.append( ( 'petition ' + tag + ' from ' + HydrusData.ConvertIntToPrettyString( num_current - num_petitioned ) + ' files', ( HC.CONTENT_UPDATE_PETITION, tag ) ) )
                    if num_pending > 0 and not only_add: choices.append( ( 'rescind pending ' + tag + ' from ' + HydrusData.ConvertIntToPrettyString( num_pending ) + ' files', ( HC.CONTENT_UPDATE_RESCIND_PEND, tag ) ) )
                    
                
                if not only_remove:
                    
                    if num_petitioned > 0: choices.append( ( 'rescind petitioned ' + tag + ' from ' + HydrusData.ConvertIntToPrettyString( num_petitioned ) + ' files', ( HC.CONTENT_UPDATE_RESCIND_PETITION, tag ) ) )
                    
                
            
            if len( choices ) == 0: return
            elif len( choices ) > 1:
                
                intro = 'What would you like to do?'
                
                with ClientGUIDialogs.DialogButtonChoice( self, intro, choices ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK: choice = dlg.GetData()
                    else: return
                    
                
            else: [ ( text, choice ) ] = choices
            
            ( choice_action, choice_tag ) = choice
            
            if choice_action == HC.CONTENT_UPDATE_ADD: media_to_affect = ( m for m in self._media if choice_tag not in m.GetTagsManager().GetCurrent( self._tag_service_key ) )
            elif choice_action == HC.CONTENT_UPDATE_DELETE: media_to_affect = ( m for m in self._media if choice_tag in m.GetTagsManager().GetCurrent( self._tag_service_key ) )
            elif choice_action == HC.CONTENT_UPDATE_PEND: media_to_affect = ( m for m in self._media if choice_tag not in m.GetTagsManager().GetCurrent( self._tag_service_key ) and choice_tag not in m.GetTagsManager().GetPending( self._tag_service_key ) )
            elif choice_action == HC.CONTENT_UPDATE_PETITION: media_to_affect = ( m for m in self._media if choice_tag in m.GetTagsManager().GetCurrent( self._tag_service_key ) and choice_tag not in m.GetTagsManager().GetPetitioned( self._tag_service_key ) )
            elif choice_action == HC.CONTENT_UPDATE_RESCIND_PEND: media_to_affect = ( m for m in self._media if choice_tag in m.GetTagsManager().GetPending( self._tag_service_key ) )
            elif choice_action == HC.CONTENT_UPDATE_RESCIND_PETITION: media_to_affect = ( m for m in self._media if choice_tag in m.GetTagsManager().GetPetitioned( self._tag_service_key ) )
            
            hashes = set( itertools.chain.from_iterable( ( m.GetHashes() for m in media_to_affect ) ) )
            
            if choice_action == HC.CONTENT_UPDATE_PETITION:
                
                if reason is None:
                    
                    if self._account.HasPermission( HC.RESOLVE_PETITIONS ): reason = 'admin'
                    else:
                        
                        message = 'Enter a reason for this tag to be removed. A janitor will review your petition.'
                        
                        with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
                            
                            if dlg.ShowModal() == wx.ID_OK: reason = dlg.GetValue()
                            else: return
                            
                        
                    
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, choice_action, ( choice_tag, hashes, reason ) )
                
            else: content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, choice_action, ( choice_tag, hashes ) )
            
            for m in self._media: m.GetMediaResult().ProcessContentUpdate( self._tag_service_key, content_update )
            
            self._content_updates.append( content_update )
            
            self._tags_box.SetTagsByMedia( self._media, force_reload = True )
            
        
        def AddTags( self, tags, parents = None ):
            
            if parents is None:
                
                parents = []
                
            
            if len( tags ) > 0:
                
                for tag in tags:
                    
                    self._AddTag( tag )
                    
                
                for parent in parents:
                    
                    self._AddTag( parent, only_add = True )
                    
                
            
        
        def EventCopyTags( self, event ):
        
            ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientData.GetMediasTagCount( self._media, tag_service_key = self._tag_service_key, collapse_siblings = False )
            
            tags = set( current_tags_to_count.keys() ).union( pending_tags_to_count.keys() )
            
            text = os.linesep.join( tags )
            
            HydrusGlobals.client_controller.pub( 'clipboard', 'text', text )
            
        
        def EventModify( self, event ):
            
            contents = []
            
            tags = self._tags_box.GetSelectedTags()
            
            for tag in tags:
                
                contents.extend( [ HydrusData.Content( HC.CONTENT_TYPE_MAPPING, ( tag, hash ) ) for hash in self._hashes ] )
                
            
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
                    
                    for tag in tags:
                        
                        self._AddTag( tag, only_add = True )
                        
                    
                except: wx.MessageBox( 'I could not understand what was in the clipboard' )
                
            else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
        def EventRemoveTags( self, event ):
            
            tag_managers = [ m.GetTagsManager() for m in self._media ]
            
            removable_tags = set()
            
            for tag_manager in tag_managers:

                removable_tags.update( tag_manager.GetCurrent( self._tag_service_key ) )
                removable_tags.update( tag_manager.GetPending( self._tag_service_key ) )
                
            
            reason = None
            
            if not self._i_am_local_tag_service:
                
                if self._account.HasPermission( HC.RESOLVE_PETITIONS ):
                    
                    reason = 'admin'
                    
                else:
                    
                    message = 'Enter a reason for all these tags to be removed. A janitor will review your petition.'
                    
                    with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            reason = dlg.GetValue()
                            
                        else:
                            
                            return
                            
                        
                    
                
            
            for tag in removable_tags:
                
                self._AddTag( tag, only_remove = True, reason = reason )
                
            
            
        
        def EventShowDeleted( self, event ):
            
            self._tags_box.SetShow( 'deleted', self._show_deleted_checkbox.GetValue() )
            
        
        def GetContentUpdates( self ): return ( self._tag_service_key, self._content_updates )
        
        def GetServiceKey( self ): return self._tag_service_key
        
        def HasChanges( self ): return len( self._content_updates ) > 0
        
        def Ok( self ):
            
            wx.PostEvent( self, wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'ok' ) ) )
            
        
        def SetMedia( self, media ):
            
            self._content_updates = []
            
            if media is None: media = []
            
            self._hashes = { hash for hash in itertools.chain.from_iterable( ( m.GetHashes() for m in media ) ) }
            
            if len( self._hashes ) > 0: media_results = HydrusGlobals.client_controller.Read( 'media_results', self._file_service_key, self._hashes )
            else: media_results = []
            
            # this should now be a nice clean copy of the original media
            self._media = [ ClientMedia.MediaSingleton( media_result ) for media_result in media_results ]
            
            self._tags_box.SetTagsByMedia( self._media )
            
        
        def SetTagBoxFocus( self ):
            
            self._add_tag_box.SetFocus()
            
        
    
class DialogManageUPnP( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
            
            self._mappings_list_ctrl = ClientGUICommon.SaneListCtrl( self, 480, [ ( 'description', -1 ), ( 'internal ip', 100 ), ( 'internal port', 80 ), ( 'external ip', 100 ), ( 'external port', 80 ), ( 'protocol', 80 ), ( 'lease', 80 ) ], delete_key_callback = self.RemoveMappings )
            
            self._add_custom = wx.Button( self, label = 'add custom mapping' )
            self._add_custom.Bind( wx.EVT_BUTTON, self.EventAddCustomMapping )
            
            self._edit = wx.Button( self, label = 'edit mapping' )
            self._edit.Bind( wx.EVT_BUTTON, self.EventEditMapping )
            
            self._remove = wx.Button( self, label = 'remove mapping' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemoveMapping )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
        
        def PopulateControls():
            
            self._RefreshMappings()
            
        
        def ArrangeControls():
            
            edit_buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            edit_buttons.AddF( self._add_custom, CC.FLAGS_MIXED )
            edit_buttons.AddF( self._edit, CC.FLAGS_MIXED )
            edit_buttons.AddF( self._remove, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._mappings_list_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( edit_buttons, CC.FLAGS_BUTTON_SIZER )
            vbox.AddF( self._ok, CC.FLAGS_LONE_BUTTON )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            x = max( x, 760 )
            
            self.SetInitialSize( ( x, y ) )
            
        
        title = 'manage local upnp'
        
        ClientGUIDialogs.Dialog.__init__( self, parent, title )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _RefreshMappings( self ):
    
        self._mappings_list_ctrl.DeleteAllItems()
        
        self._mappings = HydrusNATPunch.GetUPnPMappings()
        
        for mapping in self._mappings: self._mappings_list_ctrl.Append( mapping, mapping )
        
        self._mappings_list_ctrl.SortListItems( 1 )
        
    
    def EventAddCustomMapping( self, event ):
        
        do_refresh = False
        
        external_port = HC.DEFAULT_SERVICE_PORT
        protocol = 'TCP'
        internal_port = HC.DEFAULT_SERVICE_PORT
        description = 'hydrus service'
        duration = 0
        
        with ClientGUIDialogs.DialogInputUPnPMapping( self, external_port, protocol, internal_port, description, duration ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                ( external_port, protocol, internal_port, description, duration ) = dlg.GetInfo()
                
                for ( existing_description, existing_internal_ip, existing_internal_port, existing_external_ip, existing_external_port, existing_protocol, existing_lease ) in self._mappings:
                    
                    if external_port == existing_external_port and protocol == existing_protocol:
                        
                        wx.MessageBox( 'That external port already exists!' )
                        
                        return
                        
                    
                
                internal_client = HydrusNATPunch.GetLocalIP()
                
                HydrusNATPunch.AddUPnPMapping( internal_client, internal_port, external_port, protocol, description, duration = duration )
                
                do_refresh = True
                
            
        
        if do_refresh: self._RefreshMappings()
        
    
    def EventEditMapping( self, event ):
        
        do_refresh = False
        
        for index in self._mappings_list_ctrl.GetAllSelected():
            
            ( description, internal_ip, internal_port, external_ip, external_port, protocol, duration ) = self._mappings_list_ctrl.GetClientData( index )
            
            with ClientGUIDialogs.DialogInputUPnPMapping( self, external_port, protocol, internal_port, description, duration ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( external_port, protocol, internal_port, description, duration ) = dlg.GetInfo()
                    
                    HydrusNATPunch.RemoveUPnPMapping( external_port, protocol )
                    
                    internal_client = HydrusNATPunch.GetLocalIP()
                    
                    HydrusNATPunch.AddUPnPMapping( internal_client, internal_port, external_port, protocol, description, duration = duration )
                    
                    do_refresh = True
                    
                
            
        
        if do_refresh: self._RefreshMappings()
        
    
    def EventOK( self, event ):
        
        self.EndModal( wx.ID_OK )
        
    
    def EventRemoveMapping( self, event ): self.RemoveMappings()
    
    def RemoveMappings( self ):
        
        do_refresh = False
        
        for index in self._mappings_list_ctrl.GetAllSelected():
            
            ( description, internal_ip, internal_port, external_ip, external_port, protocol, duration ) = self._mappings_list_ctrl.GetClientData( index )
            
            HydrusNATPunch.RemoveUPnPMapping( external_port, protocol )
            
            do_refresh = True
            
        
        if do_refresh: self._RefreshMappings()
        