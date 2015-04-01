import Crypto.PublicKey.RSA
import HydrusConstants as HC
import ClientDownloading
import HydrusEncryption
import HydrusExceptions
import HydrusFileHandling
import HydrusNATPunch
import HydrusTagArchive
import HydrusTags
import HydrusThreading
import ClientConstants as CC
import ClientData
import ClientCaches
import ClientFiles
import ClientGUICommon
import ClientGUICollapsible
import collections
import gc
import itertools
import os
import random
import re
import shutil
import stat
import string
import subprocess
import threading
import time
import traceback
import urllib
import wx
import yaml
import zipfile
import HydrusData
import ClientSearch
import HydrusGlobals

# Option Enums

ID_NULL = wx.NewId()

ID_TIMER_UPDATE = wx.NewId()

# Hue is generally 200, Sat and Lum changes based on need

COLOUR_SELECTED = wx.Colour( 217, 242, 255 )
COLOUR_SELECTED_DARK = wx.Colour( 1, 17, 26 )
COLOUR_UNSELECTED = wx.Colour( 223, 227, 230 )

def SelectServiceKey( permission = None, service_types = HC.ALL_SERVICES, service_keys = None, unallowed = None ):
    
    if service_keys is None:
        
        services = wx.GetApp().GetManager( 'services' ).GetServices( service_types )
        
        if permission is not None: services = [ service for service in services if service.GetInfo( 'account' ).HasPermission( permission ) ]
        
        service_keys = [ service.GetServiceKey() for service in services ]
        
    
    if unallowed is not None: service_keys.difference_update( unallowed )
    
    if len( service_keys ) == 0: return None
    elif len( service_keys ) == 1:
        
        ( service_key, ) = service_keys
        
        return service_key
        
    else:
        
        services = { wx.GetApp().GetManager( 'services' ).GetService( service_key ) for service_key in service_keys }
        
        names_to_service_keys = { service.GetName() : service.GetServiceKey() for service in services }
        
        with DialogSelectFromListOfStrings( wx.GetApp().GetGUI(), 'select service', names_to_service_keys.keys() ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK: return names_to_service_keys[ dlg.GetString() ]
            else: return None
            
        
    
class Dialog( wx.Dialog ):
    
    def __init__( self, parent, title, style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER, position = 'topleft' ):
        
        if parent is not None and position == 'topleft':
            
            if issubclass( type( parent ), wx.TopLevelWindow ): parent_tlp = parent
            else: parent_tlp = parent.GetTopLevelParent()
            
            ( pos_x, pos_y ) = parent_tlp.GetPositionTuple()
            
            pos = ( pos_x + 50, pos_y + 100 )
            
        else: pos = ( -1, -1 )
        
        wx.Dialog.__init__( self, parent, title = title, style = style, pos = pos )
        
        #self.SetDoubleBuffered( True )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        
        self.SetIcon( wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO ) )
        
        self.Bind( wx.EVT_BUTTON, self.EventDialogButton )
        
        if position == 'center': wx.CallAfter( self.Center )
        
        wx.GetApp().ResetIdleTimer()
        
    
    def EventDialogButton( self, event ): self.EndModal( event.GetId() )
    
    def SetInitialSize( self, ( width, height ) ):
        
        wx.Dialog.SetInitialSize( self, ( width, height ) )
        
        min_width = min( 240, width )
        min_height = min( 180, height )
        
        self.SetMinSize( ( min_width, min_height ) )
        
    
class DialogAdvancedContentUpdate( Dialog ):
    
    COPY = 0
    DELETE = 1
    DELETE_DELETED = 2
    
    ALL_MAPPINGS = 0
    SPECIFIC_MAPPINGS = 1
    SPECIFIC_NAMESPACE = 2
    
    def __init__( self, parent, service_key, hashes = None ):
        
        def InitialiseControls():
            
            self._internal_actions = ClientGUICommon.StaticBox( self, 'internal' )
            
            self._action_dropdown = ClientGUICommon.BetterChoice( self._internal_actions )
            self._action_dropdown.Bind( wx.EVT_CHOICE, self.EventChoice )
            self._tag_type_dropdown = ClientGUICommon.BetterChoice( self._internal_actions )
            self._service_key_dropdown = ClientGUICommon.BetterChoice( self._internal_actions )
            
            self._go = wx.Button( self._internal_actions, label = 'Go!' )
            self._go.Bind( wx.EVT_BUTTON, self.EventGo )
            
            self._tag_input = ClientGUICommon.AutoCompleteDropdownTagsWrite( self._internal_actions, self.SetSomeTag, CC.COMBINED_FILE_SERVICE_KEY, self._service_key )
            self._specific_tag = wx.StaticText( self._internal_actions, label = '', size = ( 100, -1 ) )
            
            self._import_from_hta = wx.Button( self._internal_actions, label = 'one-time mass import or delete using a hydrus tag archive' )
            self._import_from_hta.Bind( wx.EVT_BUTTON, self.EventImportFromHTA )
            
            #
            
            self._external_actions = ClientGUICommon.StaticBox( self, 'external' )
            
            self._export_to_hta = wx.Button( self._external_actions, label = 'export to hydrus tag archive' )
            self._export_to_hta.Bind( wx.EVT_BUTTON, self.EventExportToHTA )
            
            #
            
            self._done = wx.Button( self, label = 'done' )
            
        
        def PopulateControls():
            
            self._action_dropdown.Append( 'copy', self.COPY )
            if self._service_key == CC.LOCAL_TAG_SERVICE_KEY:
                
                self._action_dropdown.Append( 'delete', self.DELETE )
                self._action_dropdown.Append( 'clear deleted record', self.DELETE_DELETED )
                
            
            self._action_dropdown.Select( 0 )
            
            #
            
            self._tag_type_dropdown.Append( 'all mappings', self.ALL_MAPPINGS )
            self._tag_type_dropdown.Append( 'specific tag\'s mappings', self.SPECIFIC_MAPPINGS )
            self._tag_type_dropdown.Append( 'specific namespace\'s mappings', self.SPECIFIC_NAMESPACE )
            
            self._tag_type_dropdown.Select( 0 )
            
            #
            
            services = [ service for service in wx.GetApp().GetManager( 'services' ).GetServices( ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ) ) if service.GetServiceKey() != self._service_key ]
            
            for service in services:
                
                self._service_key_dropdown.Append( service.GetName(), service.GetServiceKey() )
                
            
            self._service_key_dropdown.Select( 0 )
            
        
        def ArrangeControls():
            
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._action_dropdown, CC.FLAGS_MIXED )
            hbox.AddF( self._tag_type_dropdown, CC.FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self._internal_actions, label = 'to' ), CC.FLAGS_MIXED )
            hbox.AddF( self._service_key_dropdown, CC.FLAGS_MIXED )
            hbox.AddF( self._go, CC.FLAGS_MIXED )
            
            self._internal_actions.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self._internal_actions, label = 'set specific tag or namespace: ' ), CC.FLAGS_MIXED )
            hbox.AddF( self._tag_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            hbox.AddF( self._specific_tag, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self._internal_actions.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._import_from_hta, CC.FLAGS_LONE_BUTTON )
            
            self._internal_actions.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            self._external_actions.AddF( self._export_to_hta, CC.FLAGS_LONE_BUTTON )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            message = 'These advanced operations are powerful, so think before you click. They can lock up your client for a _long_ time, and are not undoable. You may need to refresh your existing searches to see their effect.' 
            
            st = wx.StaticText( self, label = message )
            
            st.Wrap( 360 )
            
            vbox.AddF( st, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._internal_actions, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._external_actions, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._done, CC.FLAGS_LONE_BUTTON )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 360: x = 360
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'Advanced Content Update' )
        
        self._service_key = service_key
        self._tag = ''
        self._hashes = hashes
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
    
    def EventChoice( self, event ):
        
        data = self._action_dropdown.GetChoice()
        
        if data in ( self.DELETE, self.DELETE_DELETED ): self._service_key_dropdown.Disable()
        else: self._service_key_dropdown.Enable()
        
    
    def EventExportToHTA( self, event ):
        
        with wx.FileDialog( self, style = wx.FD_SAVE, defaultFile = 'archive.db' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK: path = dlg.GetPath()
            else: return
            
        
        message = 'Would you like to use hydrus\'s normal hash type, or an alternative?'
        message += os.linesep * 2
        message += 'Hydrus uses SHA256 to identify files, but other services use different standards. MD5, SHA1 and SHA512 are available, but only for local files, which may limit your export.'
        message += os.linesep * 2
        message += 'If you do not know what this stuff means, click \'normal\'.'
        
        with DialogYesNo( self, message, title = 'Choose which hash type.', yes_label = 'normal', no_label = 'alternative' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result in ( wx.ID_YES, wx.ID_NO ):
                
                if result == wx.ID_YES: hash_type = HydrusTagArchive.HASH_TYPE_SHA256
                else:
                    
                    with DialogSelectFromListOfStrings( self, 'Select the hash type', [ 'md5', 'sha1', 'sha512' ] ) as hash_dlg:
                        
                        if hash_dlg.ShowModal() == wx.ID_OK:
                            
                            s = hash_dlg.GetString()
                            
                            if s == 'md5': hash_type = HydrusTagArchive.HASH_TYPE_MD5
                            elif s == 'sha1': hash_type = HydrusTagArchive.HASH_TYPE_SHA1
                            elif s == 'sha512': hash_type = HydrusTagArchive.HASH_TYPE_SHA512
                            
                        else: return
                        
                    
                
                wx.GetApp().Write( 'export_mappings', path, self._service_key, hash_type, self._hashes )
                
            
        
    
    def EventGo( self, event ):
        
        with DialogYesNo( self, 'Are you sure?' ) as dlg:
            
            if dlg.ShowModal() != wx.ID_YES: return
            
        
        action = self._action_dropdown.GetChoice()
        
        tag_type = self._tag_type_dropdown.GetChoice()
        
        if tag_type == self.ALL_MAPPINGS: tag = None
        elif tag_type == self.SPECIFIC_MAPPINGS: tag = ( 'tag', self._tag )
        elif tag_type == self.SPECIFIC_NAMESPACE:
            
            tag = self._tag
            
            if tag.endswith( ':' ): tag = tag[:-1]
            
            tag = ( 'namespace', tag )
            
        
        if tag == '': return
        
        service_key_target = self._service_key_dropdown.GetChoice()
        
        if action == self.COPY:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADVANCED, ( 'copy', ( tag, self._hashes, service_key_target ) ) )
            
        elif action == self.DELETE:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADVANCED, ( 'delete', ( tag, self._hashes ) ) )
            
        elif action == self.DELETE_DELETED:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADVANCED, ( 'delete_deleted', ( tag, self._hashes ) ) )
            
        
        service_keys_to_content_updates = { self._service_key : [ content_update ] }
        
        wx.GetApp().Write( 'content_updates', service_keys_to_content_updates )
        
    
    def EventImportFromHTA( self, event ):
        
        text = 'Select the Hydrus Tag Archive\'s location.'
        
        with wx.FileDialog( self, message = text, style = wx.FD_OPEN ) as dlg_file:
            
            if dlg_file.ShowModal() == wx.ID_OK:
                
                path = dlg_file.GetPath()
                
                hta = HydrusTagArchive.HydrusTagArchive( path )
                
                potential_namespaces = hta.GetNamespaces()
                
                hta.GetHashType() # this tests if the hta can produce a hashtype
                
                del hta
                
                service = wx.GetApp().GetManager( 'services' ).GetService( self._service_key )
                
                service_type = service.GetServiceType()
                
                can_delete = True
                
                if service_type == HC.TAG_REPOSITORY:
                    
                    account = service.GetInfo( 'account' )
                    
                    if not account.HasPermission( HC.RESOLVE_PETITIONS ): can_delete = False
                    
                
                if can_delete:
                    
                    text = 'Would you like to add or delete the archive\'s tags?'
                    
                    with DialogYesNo( self, text, title = 'Add or delete?', yes_label = 'add', no_label = 'delete' ) as dlg_add:
                        
                        result = dlg_add.ShowModal()
                        
                        if result == wx.ID_YES: adding = True
                        elif result == wx.ID_NO: adding = False
                        else: return
                        
                    
                else:
                    
                    text = 'You cannot quickly delete tags from this service, so I will assume you want to add tags.'
                    
                    wx.MessageBox( text )
                    
                    adding = True
                    
                
                text = 'Choose which namespaces to '
                
                if adding: text += 'add.'
                else: text += 'delete.'
                
                with DialogCheckFromListOfStrings( self, text, HydrusData.ConvertUglyNamespacesToPrettyStrings( potential_namespaces ) ) as dlg_namespaces:
                    
                    if dlg_namespaces.ShowModal() == wx.ID_OK:
                        
                        namespaces = HydrusData.ConvertPrettyStringsToUglyNamespaces( dlg_namespaces.GetChecked() )
                        
                        text = 'Are you absolutely sure you want to '
                        
                        if adding: text += 'add'
                        else: text += 'delete'
                        
                        text += ' the namespaces:'
                        text += os.linesep * 2
                        text += os.linesep.join( HydrusData.ConvertUglyNamespacesToPrettyStrings( namespaces ) )
                        text += os.linesep * 2
                        
                        if adding: text += 'To '
                        else: text += 'From '
                        
                        text += service.GetName() + ' ?'
                        
                        with DialogYesNo( self, text ) as dlg_final:
                            
                            if dlg_final.ShowModal() == wx.ID_YES:
                                
                                content_update = HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADVANCED, ( 'hta', ( path, adding, namespaces ) ) )
                                
                                service_keys_to_content_updates = { self._service_key : [ content_update ] }
                                
                                wx.GetApp().Write( 'content_updates', service_keys_to_content_updates )
                                
                            
                        
                    
                
            
        
    
    def SetSomeTag( self, tag, parents = None ):
        
        if parents is None: parents = []
        
        self._tag = tag
        
        self._specific_tag.SetLabel( tag )
        
    
class DialogButtonChoice( Dialog ):
    
    def __init__( self, parent, intro, choices ):
        
        def InitialiseControls():
            
            self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
            
            self._buttons = []
            self._ids_to_data = {}
            
            i = 0
            
            for ( text, data ) in choices:
                
                self._buttons.append( wx.Button( self, label = text, id = i ) )
                
                self._ids_to_data[ i ] = data
                
                i += 1
                
            
        
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( wx.StaticText( self, label = intro ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            for button in self._buttons: vbox.AddF( button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'choose what to do', position = 'center' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        
        wx.CallAfter( self._buttons[0].SetFocus )
        
    
    def EventButton( self, event ):
        
        id = event.GetId()
        
        if id == wx.ID_CANCEL: self.EndModal( wx.ID_CANCEL )
        else:
            
            self._data = self._ids_to_data[ id ]
            
            self.EndModal( wx.ID_OK )
            
        
    
    def GetData( self ): return self._data
    
class DialogChooseNewServiceMethod( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
            
            register_message = 'I want to initialise a new account with the server. I have a registration key (a key starting with \'r\').'
            
            self._register = wx.Button( self, label = register_message )
            self._register.Bind( wx.EVT_BUTTON, self.EventRegister )
            
            setup_message = 'The account is already initialised; I just want to add it to this client. I have a normal access key.'
            
            self._setup = wx.Button( self, id = wx.ID_OK, label = setup_message )
            
        
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._register, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( wx.StaticText( self, label = '-or-', style = wx.ALIGN_CENTER ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._setup, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'how to set up the account?', position = 'center' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self._should_register = False
        
        wx.CallAfter( self._register.SetFocus )
        
    
    def EventRegister( self, event ):
        
        self._should_register = True
        
        self.EndModal( wx.ID_OK )
        
    
    def GetRegister( self ): return self._should_register
    
class DialogFinishFiltering( Dialog ):
    
    def __init__( self, parent, num_kept, num_deleted, keep = 'keep', delete = 'delete' ):
        
        def InitialiseControls():
            
            self._commit = wx.Button( self, id = wx.ID_YES, label = 'commit' )
            self._commit.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._forget = wx.Button( self, id = wx.ID_NO, label = 'forget' )
            self._forget.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._back = wx.Button( self, id = wx.ID_CANCEL, label = 'back to filtering' )
            
        
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._commit, CC.FLAGS_EXPAND_BOTH_WAYS )
            hbox.AddF( self._forget, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            label = keep + ' ' + HydrusData.ConvertIntToPrettyString( num_kept ) + ' and ' + delete + ' ' + HydrusData.ConvertIntToPrettyString( num_deleted ) + ' files?'
            
            vbox.AddF( wx.StaticText( self, label = label, style = wx.ALIGN_CENTER ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( wx.StaticText( self, label = '-or-', style = wx.ALIGN_CENTER ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'are you sure?', position = 'center' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._commit.SetFocus )
        
    
class DialogFinishRatingFiltering( Dialog ):
    
    def __init__( self, parent, num_certain_ratings, num_uncertain_ratings ):
        
        def InitialiseControls():
            
            self._commit = wx.Button( self, id = wx.ID_YES, label = 'commit' )
            self._commit.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._forget = wx.Button( self, id = wx.ID_NO, label = 'forget' )
            self._forget.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._back = wx.Button( self, id = wx.ID_CANCEL, label = 'back to filtering' )
            
        
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._commit, CC.FLAGS_EXPAND_BOTH_WAYS )
            hbox.AddF( self._forget, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            info_strings = []
            
            if num_certain_ratings > 0: info_strings.append( HydrusData.ConvertIntToPrettyString( num_certain_ratings ) + ' ratings' )
            if num_uncertain_ratings > 0: info_strings.append( HydrusData.ConvertIntToPrettyString( num_uncertain_ratings ) + ' uncertain changes' )
            
            label = 'Apply ' + ' and '.join( info_strings ) + '?'
            
            vbox.AddF( wx.StaticText( self, label = label, style = wx.ALIGN_CENTER ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( wx.StaticText( self, label = '-or-', style = wx.ALIGN_CENTER ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'are you sure?', position = 'center' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._commit.SetFocus )
        
    
class DialogFirstStart( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok!' )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
        
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
            message1 = 'Hi, this looks like the first time you have started the hydrus client. Don\'t forget to check out the'
            link = wx.HyperlinkCtrl( self, id = -1, label = 'help', url = 'file://' + HC.BASE_DIR + '/help/index.html' )
            message2 = 'if you haven\'t already.'
            message3 = 'When you close this dialog, the client will start its local http server. You will probably get a firewall warning.'
            message4 = 'You can block it if you like, or you can allow it. It doesn\'t phone home, or expose your files to your network; it just provides another way to locally export your files.'
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self, label = message1 ), CC.FLAGS_MIXED )
            hbox.AddF( link, CC.FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self, label = message2 ), CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            vbox.AddF( wx.StaticText( self, label = message3 ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( wx.StaticText( self, label = message4 ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._ok, CC.FLAGS_LONE_BUTTON )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'First start', position = 'center' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
class DialogGenerateNewAccounts( Dialog ):
    
    def __init__( self, parent, service_key ):
        
        def InitialiseControls():
            
            self._num = wx.SpinCtrl( self, min = 1, max = 10000, size = ( 80, -1 ) )
            
            self._account_types = wx.Choice( self, size = ( 400, -1 ) )
            
            self._lifetime = wx.Choice( self )
            
            self._ok = wx.Button( self, label = 'Ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._num.SetValue( 1 )
            
            service = wx.GetApp().GetManager( 'services' ).GetService( service_key )
            
            response = service.Request( HC.GET, 'account_types' )
            
            account_types = response[ 'account_types' ]
            
            for account_type in account_types: self._account_types.Append( account_type.ConvertToString(), account_type )
            self._account_types.SetSelection( 0 ) # admin
            
            for ( str, value ) in HC.lifetimes: self._lifetime.Append( str, value )
            self._lifetime.SetSelection( 3 ) # one year
            
        
        def ArrangeControls():
            
            ctrl_box = wx.BoxSizer( wx.HORIZONTAL )
            
            ctrl_box.AddF( wx.StaticText( self, label = 'generate' ), CC.FLAGS_MIXED )
            ctrl_box.AddF( self._num, CC.FLAGS_MIXED )
            ctrl_box.AddF( self._account_types, CC.FLAGS_MIXED )
            ctrl_box.AddF( wx.StaticText( self, label = 'accounts, to expire in' ), CC.FLAGS_MIXED )
            ctrl_box.AddF( self._lifetime, CC.FLAGS_MIXED )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, CC.FLAGS_MIXED )
            b_box.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( ctrl_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'configure new accounts' )
        
        self._service_key = service_key
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventOK( self, event ):
        
        num = self._num.GetValue()
        
        account_type = self._account_types.GetClientData( self._account_types.GetSelection() )
        
        title = account_type.GetTitle()
        
        lifetime = self._lifetime.GetClientData( self._lifetime.GetSelection() )
        
        service = wx.GetApp().GetManager( 'services' ).GetService( self._service_key )
        
        try:
            
            request_args = { 'num' : num, 'title' : title }
            
            if lifetime is not None: request_args[ 'lifetime' ] = lifetime
            
            response = service.Request( HC.GET, 'registration_keys', request_args )
            
            registration_keys = response[ 'registration_keys' ]
            
            ClientGUICommon.ShowKeys( 'registration', registration_keys )
            
        finally: self.EndModal( wx.ID_OK )
        
    
class DialogInputAdvancedTagOptions( Dialog ):
    
    def __init__( self, parent, pretty_name, name, ato ):
        
        def InitialiseControls():
            
            if name in ( 'default', HC.SITE_TYPE_BOORU ): namespaces = [ 'all namespaces' ]
            elif name == HC.SITE_TYPE_DEVIANT_ART: namespaces = [ 'creator', 'title', '' ]
            elif name == HC.SITE_TYPE_GIPHY: namespaces = [ '' ]
            elif name == HC.SITE_TYPE_HENTAI_FOUNDRY: namespaces = [ 'creator', 'title', '' ]
            elif name == HC.SITE_TYPE_NEWGROUNDS: namespaces = [ 'creator', 'title', '' ]
            elif name == HC.SITE_TYPE_PIXIV: namespaces = [ 'creator', 'title', '' ]
            elif name == HC.SITE_TYPE_TUMBLR: namespaces = [ '' ]
            else:
                
                ( booru_id, booru_name ) = name
                
                booru = wx.GetApp().Read( 'remote_booru', booru_name )
                
                namespaces = booru.GetNamespaces()
                
            
            self._name = name
            
            self._advanced_tag_options = ClientGUICollapsible.CollapsibleOptionsTags( self, namespaces = namespaces )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            if name in ( 'default', HC.SITE_TYPE_BOORU ):
                
                namespaces = [ 'all namespaces' ]
                
                new_ato = {}
                
                for ( service_key, boolean ) in self._initial_ato.items():
                    
                    if boolean: new_ato[ service_key ] = [ 'all namespaces' ]
                    
                
                self._initial_ato = new_ato
                
            
            self._advanced_tag_options.SetInfo( self._initial_ato )
            
        
        def ArrangeControls():
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, CC.FLAGS_MIXED )
            b_box.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._advanced_tag_options, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            x = max( 200, x )
            y = max( 300, y )
            
            self.SetInitialSize( ( x, y ) )
            
        
        self._name = name
        self._initial_ato = ato
        
        Dialog.__init__( self, parent, 'configure default advanced tag options for ' + pretty_name )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._advanced_tag_options.ExpandCollapse )
        
    
    def GetATO( self ):
        
        ato = self._advanced_tag_options.GetInfo()
        
        if self._name in ( 'default', HC.SITE_TYPE_BOORU ):
            
            new_ato = {}
            
            for ( service_key, namespaces ) in ato.items():
                
                if namespaces == [ 'all namespaces' ]: new_ato[ service_key ] = True
                
            
            ato = new_ato
            
        
        return ato
        
    
class DialogInputCustomFilterAction( Dialog ):
    
    def __init__( self, parent, modifier = wx.ACCEL_NORMAL, key = wx.WXK_F7, service_key = None, action = 'archive' ):
        
        def InitialiseControls():
            
            self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
            
            self._shortcut_panel = ClientGUICommon.StaticBox( self, 'shortcut' )
            
            self._shortcut = ClientGUICommon.Shortcut( self._shortcut_panel, modifier, key )
            
            self._none_panel = ClientGUICommon.StaticBox( self, 'non-service actions' )
            
            self._none_actions = wx.Choice( self._none_panel, choices = [ 'manage_tags', 'manage_ratings', 'archive', 'inbox', 'delete', 'fullscreen_switch', 'frame_back', 'frame_next', 'previous', 'next', 'first', 'last', 'open_externally' ] )
            
            self._ok_none = wx.Button( self._none_panel, label = 'ok' )
            self._ok_none.Bind( wx.EVT_BUTTON, self.EventOKNone )
            self._ok_none.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._tag_panel = ClientGUICommon.StaticBox( self, 'tag service actions' )
            
            self._tag_service_keys = wx.Choice( self._tag_panel )
            self._tag_value = wx.TextCtrl( self._tag_panel, style = wx.TE_READONLY )
            self._tag_input = ClientGUICommon.AutoCompleteDropdownTagsWrite( self._tag_panel, self.SetTag, CC.LOCAL_FILE_SERVICE_KEY, CC.COMBINED_TAG_SERVICE_KEY )
            
            self._ok_tag = wx.Button( self._tag_panel, label = 'ok' )
            self._ok_tag.Bind( wx.EVT_BUTTON, self.EventOKTag )
            self._ok_tag.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._ratings_like_panel = ClientGUICommon.StaticBox( self, 'like/dislike ratings service actions' )
            
            self._ratings_like_service_keys = wx.Choice( self._ratings_like_panel )
            self._ratings_like_service_keys.Bind( wx.EVT_CHOICE, self.EventRecalcActions )
            self._ratings_like_like = wx.RadioButton( self._ratings_like_panel, style = wx.RB_GROUP, label = 'like' )
            self._ratings_like_dislike = wx.RadioButton( self._ratings_like_panel, label = 'dislike' )
            self._ratings_like_remove = wx.RadioButton( self._ratings_like_panel, label = 'remove rating' )
            
            self._ok_ratings_like = wx.Button( self._ratings_like_panel, label = 'ok' )
            self._ok_ratings_like.Bind( wx.EVT_BUTTON, self.EventOKRatingsLike )
            self._ok_ratings_like.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._ratings_numerical_panel = ClientGUICommon.StaticBox( self, 'numerical ratings service actions' )
            
            self._ratings_numerical_service_keys = wx.Choice( self._ratings_numerical_panel )
            self._ratings_numerical_service_keys.Bind( wx.EVT_CHOICE, self.EventRecalcActions )
            self._ratings_numerical_slider = wx.Slider( self._ratings_numerical_panel, style = wx.SL_AUTOTICKS | wx.SL_LABELS )
            self._ratings_numerical_remove = wx.CheckBox( self._ratings_numerical_panel, label = 'remove rating' )
            
            self._ok_ratings_numerical = wx.Button( self._ratings_numerical_panel, label = 'ok' )
            self._ok_ratings_numerical.Bind( wx.EVT_BUTTON, self.EventOKRatingsNumerical )
            self._ok_ratings_numerical.SetForegroundColour( ( 0, 128, 0 ) )
            
            services = wx.GetApp().GetManager( 'services' ).GetServices( ( HC.LOCAL_TAG, HC.TAG_REPOSITORY, HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
            
            for service in services:
                
                service_type = service.GetServiceType()
                
                if service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ): choice = self._tag_service_keys
                elif service_type == HC.LOCAL_RATING_LIKE: choice = self._ratings_like_service_keys
                elif service_type == HC.LOCAL_RATING_NUMERICAL: choice = self._ratings_numerical_service_keys
                
                choice.Append( service.GetName(), service.GetServiceKey() )
                
            
            self._SetActions()
            
            if self._service_key is None:
                
                self._none_actions.SetStringSelection( self._action )
                
            else:
                
                self._service = wx.GetApp().GetManager( 'services' ).GetService( service_key )
                
                service_name = self._service.GetName()
                service_type = self._service.GetServiceType()
                
                if service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ):
                    
                    self._tag_service_keys.SetStringSelection( service_name )
                    
                    self._tag_value.SetValue( self._action )
                    
                elif service_type == HC.LOCAL_RATING_LIKE:
                    
                    self._ratings_like_service_keys.SetStringSelection( service_name )
                    
                    self._SetActions()
                    
                    if self._action is None: self._ratings_like_remove.SetValue( True )
                    elif self._action == True: self._ratings_like_like.SetValue( True )
                    elif self._action == False: self._ratings_like_dislike.SetValue( True )
                    
                elif service_type == HC.LOCAL_RATING_NUMERICAL:
                    
                    self._ratings_numerical_service_keys.SetStringSelection( service_name )
                    
                    self._SetActions()
                    
                    if self._action is None: self._ratings_numerical_remove.SetValue( True )
                    else:
                        
                        ( lower, upper ) = self._current_ratings_numerical_service.GetLowerUpper()
                        
                        slider_value = int( self._action * ( upper - lower ) ) + lower
                        
                        self._ratings_numerical_slider.SetValue( slider_value )
                        
                    
                
            
        
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
            self._shortcut_panel.AddF( self._shortcut, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            none_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            none_hbox.AddF( self._none_actions, CC.FLAGS_EXPAND_DEPTH_ONLY )
            none_hbox.AddF( self._ok_none, CC.FLAGS_MIXED )
            
            self._none_panel.AddF( none_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            tag_sub_vbox = wx.BoxSizer( wx.VERTICAL )
            
            tag_sub_vbox.AddF( self._tag_value, CC.FLAGS_EXPAND_BOTH_WAYS )
            tag_sub_vbox.AddF( self._tag_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            tag_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            tag_hbox.AddF( self._tag_service_keys, CC.FLAGS_EXPAND_DEPTH_ONLY )
            tag_hbox.AddF( tag_sub_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            tag_hbox.AddF( self._ok_tag, CC.FLAGS_MIXED )
            
            self._tag_panel.AddF( tag_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            ratings_like_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            ratings_like_hbox.AddF( self._ratings_like_service_keys, CC.FLAGS_EXPAND_DEPTH_ONLY )
            ratings_like_hbox.AddF( self._ratings_like_like, CC.FLAGS_MIXED )
            ratings_like_hbox.AddF( self._ratings_like_dislike, CC.FLAGS_MIXED )
            ratings_like_hbox.AddF( self._ratings_like_remove, CC.FLAGS_MIXED )
            ratings_like_hbox.AddF( self._ok_ratings_like, CC.FLAGS_MIXED )
            
            self._ratings_like_panel.AddF( ratings_like_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            ratings_numerical_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            ratings_numerical_hbox.AddF( self._ratings_numerical_service_keys, CC.FLAGS_EXPAND_DEPTH_ONLY )
            ratings_numerical_hbox.AddF( self._ratings_numerical_slider, CC.FLAGS_MIXED )
            ratings_numerical_hbox.AddF( self._ratings_numerical_remove, CC.FLAGS_MIXED )
            ratings_numerical_hbox.AddF( self._ok_ratings_numerical, CC.FLAGS_MIXED )
            
            self._ratings_numerical_panel.AddF( ratings_numerical_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._none_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._tag_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._ratings_like_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._ratings_numerical_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._shortcut_panel, CC.FLAGS_MIXED )
            hbox.AddF( wx.StaticText( self, label = u'\u2192' ), CC.FLAGS_MIXED )
            hbox.AddF( vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            self.SetSizer( hbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( 680, y ) )
            
        
        Dialog.__init__( self, parent, 'input custom filter action' )
        
        self._service_key = service_key
        self._action = action
        
        self._current_ratings_like_service = None
        self._current_ratings_numerical_service = None
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok_none.SetFocus )
        
    
    def _SetActions( self ):
        
        if self._ratings_like_service_keys.GetCount() > 0:
            
            selection = self._ratings_like_service_keys.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                service_key = self._ratings_like_service_keys.GetClientData( selection )
                
                service = wx.GetApp().GetManager( 'services' ).GetService( service_key )
                
                self._current_ratings_like_service = service
                
                ( like, dislike ) = service.GetLikeDislike()
                
                self._ratings_like_like.SetLabel( like )
                self._ratings_like_dislike.SetLabel( dislike )
                
            else:
                
                self._ratings_like_like.SetLabel( 'like' )
                self._ratings_like_dislike.SetLabel( 'dislike' )
                
            
        
        if self._ratings_numerical_service_keys.GetCount() > 0:
            
            selection = self._ratings_numerical_service_keys.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                service_key = self._ratings_numerical_service_keys.GetClientData( selection )
                
                service = wx.GetApp().GetManager( 'services' ).GetService( service_key )
                
                self._current_ratings_numerical_service = service
                
                ( lower, upper ) = service.GetLowerUpper()
                
                self._ratings_numerical_slider.SetRange( lower, upper )
                
            else: self._ratings_numerical_slider.SetRange( 0, 5 )
            
        
    
    def EventOKNone( self, event ):
        
        self._service_key = None
        self._action = self._none_actions.GetStringSelection()
        self._pretty_action = self._action
        
        self.EndModal( wx.ID_OK )
        
    
    def EventOKRatingsLike( self, event ):
        
        selection = self._ratings_like_service_keys.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            self._service_key = self._ratings_like_service_keys.GetClientData( selection )
            
            ( like, dislike ) = self._current_ratings_like_service.GetLikeDislike()
            
            if self._ratings_like_like.GetValue():
                
                self._action = 1.0
                self._pretty_action = like
                
            elif self._ratings_like_dislike.GetValue():
                
                self._action = 0.0
                self._pretty_action = dislike
                
            else:
                
                self._action = None
                self._pretty_action = 'remove'
                
            
            self.EndModal( wx.ID_OK )
            
        else: self.EndModal( wx.ID_CANCEL )
        
    
    def EventOKRatingsNumerical( self, event ):
        
        selection = self._ratings_numerical_service_keys.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            self._service_key = self._ratings_numerical_service_keys.GetClientData( selection )
            
            if self._ratings_numerical_remove.GetValue():
                
                self._action = None
                self._pretty_action = 'remove'
                
            else:
                
                self._pretty_action = HydrusData.ToString( self._ratings_numerical_slider.GetValue() )
                
                ( lower, upper ) = self._current_ratings_numerical_service.GetLowerUpper()
                
                self._action = ( float( self._pretty_action ) - float( lower ) ) / ( upper - lower )
                
            
            self.EndModal( wx.ID_OK )
            
        else: self.EndModal( wx.ID_CANCEL )
        
    
    def EventOKTag( self, event ):
        
        selection = self._tag_service_keys.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            self._service_key = self._tag_service_keys.GetClientData( selection )
            
            self._action = self._tag_value.GetValue()
            self._pretty_action = self._action
            
            self.EndModal( wx.ID_OK )
            
        else: self.EndModal( wx.ID_CANCEL )
        
    
    def EventRecalcActions( self, event ):
        
        self._SetActions()
        
        event.Skip()
        
    
    def GetInfo( self ):
        
        ( modifier, key ) = self._shortcut.GetValue()
        
        if self._service_key is None: pretty_service_key = ''
        else: pretty_service_key = wx.GetApp().GetManager( 'services' ).GetService( self._service_key ).GetName()
        
        # ignore this pretty_action
        ( pretty_modifier, pretty_key, pretty_action ) = HydrusData.ConvertShortcutToPrettyShortcut( modifier, key, self._action )
        
        return ( ( pretty_modifier, pretty_key, pretty_service_key, self._pretty_action ), ( modifier, key, self._service_key, self._action ) )
        
    
    def SetTag( self, tag, parents = None ):
        
        if parents is None: parents = []
        
        self._tag_value.SetValue( tag )
        
    
class DialogInputFileSystemPredicate( Dialog ):
    
    def __init__( self, parent, predicate_type ):
        
        def Age():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '>' ] )
                
                self._years = wx.SpinCtrl( self, max = 30 )
                self._months = wx.SpinCtrl( self, max = 60 )
                self._days = wx.SpinCtrl( self, max = 90 )
                self._hours = wx.SpinCtrl( self, max = 24 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, years, months, days ) = system_predicates[ 'age' ]
                
                self._sign.SetSelection( sign )
                
                self._years.SetValue( years )
                self._months.SetValue( months )
                self._days.SetValue( days )
                self._hours.SetValue( 0 )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:age' ), CC.FLAGS_MIXED )
                hbox.AddF( self._sign, CC.FLAGS_MIXED )
                hbox.AddF( self._years, CC.FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label = 'years' ), CC.FLAGS_MIXED )
                hbox.AddF( self._months, CC.FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label = 'months' ), CC.FLAGS_MIXED )
                hbox.AddF( self._days, CC.FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label = 'days' ), CC.FLAGS_MIXED )
                hbox.AddF( self._hours, CC.FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label = 'hours' ), CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter age predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._days.SetFocus )
            
        
        def Duration():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
                
                self._duration_s = wx.SpinCtrl( self, max = 3599 )
                self._duration_ms = wx.SpinCtrl( self, max = 999 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, s, ms ) = system_predicates[ 'duration' ]
                
                self._sign.SetSelection( sign )
                
                self._duration_s.SetValue( s )
                self._duration_ms.SetValue( ms )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:duration' ), CC.FLAGS_MIXED )
                hbox.AddF( self._sign, CC.FLAGS_MIXED )
                hbox.AddF( self._duration_s, CC.FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label = 's' ), CC.FLAGS_MIXED )
                hbox.AddF( self._duration_ms, CC.FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label = 'ms' ), CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter duration predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._duration_s.SetFocus )
            
        
        def FileService():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self )
                self._sign.Append( 'is', True )
                self._sign.Append( 'is not', False )
                
                self._current_pending = wx.Choice( self )
                self._current_pending.Append( 'currently in', HC.CURRENT )
                self._current_pending.Append( 'pending to', HC.PENDING )
                
                self._file_service_key = wx.Choice( self )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._sign.SetSelection( 0 )
                self._current_pending.SetSelection( 0 )
                
                services = wx.GetApp().GetManager( 'services' ).GetServices( ( HC.FILE_REPOSITORY, HC.LOCAL_FILE ) )
                
                for service in services: self._file_service_key.Append( service.GetName(), service.GetServiceKey() )
                self._file_service_key.SetSelection( 0 )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:file service:' ), CC.FLAGS_MIXED )
                hbox.AddF( self._sign, CC.FLAGS_MIXED )
                hbox.AddF( self._current_pending, CC.FLAGS_MIXED )
                hbox.AddF( self._file_service_key, CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter file service predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._sign.SetFocus )
            
        
        def Hash():
            
            def InitialiseControls():
                
                self._hash = wx.TextCtrl( self )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                pass
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:hash=' ), CC.FLAGS_MIXED )
                hbox.AddF( self._hash, CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter hash predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._hash.SetFocus )
            
        
        def Height():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
                
                self._height = wx.SpinCtrl( self, max = 200000 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, height ) = system_predicates[ 'height' ]
                
                self._sign.SetSelection( sign )
                
                self._height.SetValue( height )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:height' ), CC.FLAGS_MIXED )
                hbox.AddF( self._sign, CC.FLAGS_MIXED )
                hbox.AddF( self._height, CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter height predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._height.SetFocus )
            
        
        def Limit():
            
            def InitialiseControls():
                
                self._limit = wx.SpinCtrl( self, max = 1000000 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                limit = system_predicates[ 'limit' ]
                
                self._limit.SetValue( limit )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:limit=' ), CC.FLAGS_MIXED )
                hbox.AddF( self._limit, CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter limit predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._limit.SetFocus )
            
        
        def Mime():
            
            def InitialiseControls():
                
                self._mime_media = wx.Choice( self, choices = [ 'image', 'application', 'audio', 'video' ] )
                self._mime_media.Bind( wx.EVT_CHOICE, self.EventMime )
                
                self._mime_type = wx.Choice( self, choices = [], size = ( 120, -1 ) )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( media, media_type ) = system_predicates[ 'mime' ]
                
                self._mime_media.SetSelection( media )
                
                self.EventMime( None )
                
                self._mime_type.SetSelection( media_type )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:mime' ), CC.FLAGS_MIXED )
                hbox.AddF( self._mime_media, CC.FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label = '/' ), CC.FLAGS_MIXED )
                hbox.AddF( self._mime_type, CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter mime predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._mime_media.SetFocus )
            
        
        def NumTags():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
                
                self._num_tags = wx.SpinCtrl( self, max = 2000 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, num_tags ) = system_predicates[ 'num_tags' ]
                
                self._sign.SetSelection( sign )
                
                self._num_tags.SetValue( num_tags )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:num_tags' ), CC.FLAGS_MIXED )
                hbox.AddF( self._sign, CC.FLAGS_MIXED )
                hbox.AddF( self._num_tags, CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter number of tags predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._num_tags.SetFocus )
            
        
        def NumWords():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '=', '>' ] )
                
                self._num_words = wx.SpinCtrl( self, max = 1000000 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, num_words ) = system_predicates[ 'num_words' ]
                
                self._sign.SetSelection( sign )
                
                self._num_words.SetValue( num_words )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:num_words' ), CC.FLAGS_MIXED )
                hbox.AddF( self._sign, CC.FLAGS_MIXED )
                hbox.AddF( self._num_words, CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter number of words predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._num_words.SetFocus )
            
        
        def Rating():
            
            def InitialiseControls():
                
                self._service_numerical = wx.Choice( self )
                self._service_numerical.Bind( wx.EVT_CHOICE, self.EventRatingsService )
                
                self._sign_numerical = wx.Choice( self, choices=[ '>', '<', '=', u'\u2248', '=rated', '=not rated', '=uncertain' ] )
                
                self._value_numerical = wx.SpinCtrl( self, min = 0, max = 50000 ) # set bounds based on current service
                
                self._first_ok = wx.Button( self, label = 'Ok', id = HC.LOCAL_RATING_NUMERICAL )
                self._first_ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._first_ok.SetForegroundColour( ( 0, 128, 0 ) )
                
                self._service_like = wx.Choice( self )
                self._service_like.Bind( wx.EVT_CHOICE, self.EventRatingsService )
                
                self._value_like = wx.Choice( self, choices=[ 'like', 'dislike', 'rated', 'not rated' ] ) # set words based on current service
                
                self._second_ok = wx.Button( self, label = 'Ok', id = HC.LOCAL_RATING_LIKE )
                self._second_ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._second_ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._local_numericals = wx.GetApp().GetManager( 'services' ).GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
                self._local_likes = wx.GetApp().GetManager( 'services' ).GetServices( ( HC.LOCAL_RATING_LIKE, ) )
                
                for service in self._local_numericals: self._service_numerical.Append( service.GetName(), service.GetServiceKey() )
                
                ( sign, value ) = system_predicates[ 'local_rating_numerical' ]
                
                self._sign_numerical.SetSelection( sign )
                
                self._value_numerical.SetValue( value )
                
                for service in self._local_likes: self._service_like.Append( service.GetName(), service.GetServiceKey() )
                
                value = system_predicates[ 'local_rating_like' ]
                
                self._value_like.SetSelection( value )
                
                if len( self._local_numericals ) > 0: self._service_numerical.SetSelection( 0 )
                if len( self._local_likes ) > 0: self._service_like.SetSelection( 0 )
                
                self.EventRatingsService( None )
                
            
            def ArrangeControls():
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:rating:' ), CC.FLAGS_MIXED )
                hbox.AddF( self._service_numerical, CC.FLAGS_MIXED )
                hbox.AddF( self._sign_numerical, CC.FLAGS_MIXED )
                hbox.AddF( self._value_numerical, CC.FLAGS_MIXED )
                hbox.AddF( self._first_ok, CC.FLAGS_MIXED )
                
                vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:rating:' ), CC.FLAGS_MIXED )
                hbox.AddF( self._service_like, CC.FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label = '=' ), CC.FLAGS_MIXED )
                hbox.AddF( self._value_like, CC.FLAGS_MIXED )
                hbox.AddF( self._second_ok, CC.FLAGS_MIXED )
                
                vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                self.SetSizer( vbox )
                
            
            Dialog.__init__( self, parent, 'enter rating predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._value_numerical.SetFocus )
            
        
        def Ratio():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices = [ '=', u'\u2248' ] )
                
                self._width = wx.SpinCtrl( self, max = 50000 )
                
                self._height = wx.SpinCtrl( self, max = 50000 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, width, height ) = system_predicates[ 'ratio' ]
                
                self._sign.SetSelection( sign )
                
                self._width.SetValue( width )
                
                self._height.SetValue( height )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:ratio' ), CC.FLAGS_MIXED )
                hbox.AddF( self._sign, CC.FLAGS_MIXED )
                hbox.AddF( self._width, CC.FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label = ':' ), CC.FLAGS_MIXED )
                hbox.AddF( self._height, CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter ratio predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._sign.SetFocus )
            
        
        def Size():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices = [ '<', u'\u2248', '=', '>' ] )
                
                self._size = wx.SpinCtrl( self, max = 1048576 )
                
                self._unit = wx.Choice( self, choices = [ 'B', 'KB', 'MB', 'GB' ] )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, size, unit ) = system_predicates[ 'size' ]
                
                self._sign.SetSelection( sign )
                
                self._size.SetValue( size )
                
                self._unit.SetSelection( unit )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:size' ), CC.FLAGS_MIXED )
                hbox.AddF( self._sign, CC.FLAGS_MIXED )
                hbox.AddF( self._size, CC.FLAGS_MIXED )
                hbox.AddF( self._unit, CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter size predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._size.SetFocus )
            
        
        def Width():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices = [ '<', u'\u2248', '=', '>' ] )
                
                self._width = wx.SpinCtrl( self, max = 200000 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                ( sign, width ) = system_predicates[ 'width' ]
                
                self._sign.SetSelection( sign )
                
                self._width.SetValue( width )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:width' ), CC.FLAGS_MIXED )
                hbox.AddF( self._sign, CC.FLAGS_MIXED )
                hbox.AddF( self._width, CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter width predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._width.SetFocus )
            
        
        def SimilarTo():
            
            def InitialiseControls():
                
                self._hash = wx.TextCtrl( self )
                
                self._max_hamming = wx.SpinCtrl( self, max = 256 )
                
                self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
                self._ok.SetDefault()
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._hash.SetValue( 'enter hash' )
                
                hamming_distance = system_predicates[ 'hamming_distance' ]
                
                self._max_hamming.SetValue( hamming_distance )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:similar_to' ), CC.FLAGS_MIXED )
                hbox.AddF( self._hash, CC.FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label=u'\u2248' ), CC.FLAGS_MIXED )
                hbox.AddF( self._max_hamming, CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter similar to predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._hash.SetFocus )
            
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        self._type = predicate_type
        
        if self._type == HC.SYSTEM_PREDICATE_TYPE_AGE: Age()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_DURATION: Duration()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_HASH: Hash()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_HEIGHT: Height()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_LIMIT: Limit()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_MIME: Mime()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS: NumTags()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_RATING: Rating()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_RATIO: Ratio()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_SIZE: Size()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_WIDTH: Width()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO: SimilarTo()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS: NumWords()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE: FileService()
        
        self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
        
    
    def EventMime( self, event ):
        
        media = self._mime_media.GetStringSelection()
        
        self._mime_type.Clear()
        
        if media == 'image':
            
            self._mime_type.Append( 'any', HC.IMAGES )
            self._mime_type.Append( 'gif', HC.IMAGE_GIF )
            self._mime_type.Append( 'jpeg', HC.IMAGE_JPEG )
            self._mime_type.Append( 'png', HC.IMAGE_PNG )
            
        elif media == 'application':
            
            self._mime_type.Append( 'any', HC.APPLICATIONS )
            self._mime_type.Append( 'pdf', HC.APPLICATION_PDF )
            self._mime_type.Append( 'x-shockwave-flash', HC.APPLICATION_FLASH )
            
        elif media == 'audio':
            
            self._mime_type.Append( 'any', HC.AUDIO )
            self._mime_type.Append( 'flac', HC.AUDIO_FLAC )
            self._mime_type.Append( 'mp3', HC.AUDIO_MP3 )
            self._mime_type.Append( 'ogg', HC.AUDIO_OGG )
            self._mime_type.Append( 'x-ms-wma', HC.AUDIO_WMA )
            
        elif media == 'video':
            
            self._mime_type.Append( 'any', HC.VIDEO )
            self._mime_type.Append( 'mp4', HC.VIDEO_MP4 )
            self._mime_type.Append( 'webm', HC.VIDEO_WEBM )
            self._mime_type.Append( 'x-matroska', HC.VIDEO_MKV )
            self._mime_type.Append( 'x-ms-wmv', HC.VIDEO_WMV )
            self._mime_type.Append( 'x-flv', HC.VIDEO_FLV )
            
        
        self._mime_type.SetSelection( 0 )
        
    
    def EventOK( self, event ):
        
        if self._type == HC.SYSTEM_PREDICATE_TYPE_AGE: info = ( self._sign.GetStringSelection(), self._years.GetValue(), self._months.GetValue(), self._days.GetValue(), self._hours.GetValue() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_DURATION: info = ( self._sign.GetStringSelection(), self._duration_s.GetValue() * 1000 + self._duration_ms.GetValue() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_HASH:
            
            hex_filter = lambda c: c in string.hexdigits
            
            hash = filter( hex_filter, self._hash.GetValue().lower() )
            
            if len( hash ) == 0: hash == '00'
            elif len( hash ) % 2 == 1: hash += '0' # since we are later decoding to byte
            
            info = hash.decode( 'hex' )
            
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_HEIGHT: info = ( self._sign.GetStringSelection(), self._height.GetValue() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_LIMIT: info = self._limit.GetValue()
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_MIME: info = self._mime_type.GetClientData( self._mime_type.GetSelection() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS: info = ( self._sign.GetStringSelection(), self._num_tags.GetValue() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS: info = ( self._sign.GetStringSelection(), self._num_words.GetValue() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_RATING:
            
            id = event.GetId()
            
            if id == HC.LOCAL_RATING_LIKE:
                
                service_key = self._service_like.GetClientData( self._service_like.GetSelection() )
                
                operator = '='
                
                selection = self._value_like.GetSelection()
                
                if selection == 0: value = '1'
                elif selection == 1: value = '0'
                elif selection == 2: value = 'rated'
                elif selection == 3: value = 'not rated'
                
                info = ( service_key, operator, value )
                
            elif id == HC.LOCAL_RATING_NUMERICAL:
                
                service_key = self._service_numerical.GetClientData( self._service_numerical.GetSelection() )
                
                operator = self._sign_numerical.GetStringSelection()
                
                if operator in ( '=rated', '=not rated', '=uncertain' ):
                    
                    value = operator[1:]
                    
                    operator = '='
                    
                else:
                    
                    service = wx.GetApp().GetManager( 'services' ).GetService( service_key )
                    
                    ( lower, upper ) = service.GetLowerUpper()
                    
                    value_raw = self._value_numerical.GetValue()
                    
                    value = float( value_raw - lower ) / float( upper - lower )
                    
                
                info = ( service_key, operator, value )
                
            
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_RATIO: info = ( self._sign.GetStringSelection(), self._width.GetValue(), self._height.GetValue() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_SIZE: info = ( self._sign.GetStringSelection(), self._size.GetValue(), HydrusData.ConvertUnitToInteger( self._unit.GetStringSelection() ) )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_WIDTH: info = ( self._sign.GetStringSelection(), self._width.GetValue() )
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO:
            
            hex_filter = lambda c: c in string.hexdigits
            
            hash = filter( hex_filter, self._hash.GetValue().lower() )
            
            if len( hash ) == 0: hash == '00'
            elif len( hash ) % 2 == 1: hash += '0' # since we are later decoding to byte
            
            info = ( hash.decode( 'hex' ), self._max_hamming.GetValue() )
            
        elif self._type == HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE: info = ( self._sign.GetClientData( self._sign.GetSelection() ), self._current_pending.GetClientData( self._current_pending.GetSelection() ), self._file_service_key.GetClientData( self._file_service_key.GetSelection() ) )
        
        self._predicate = HydrusData.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( self._type, info ) )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventRatingsService( self, event ):
        
        try:
            
            service = self._service_numerical.GetClientData( self._service_numerical.GetSelection() )
            
            ( lower, upper ) = service.GetLowerUpper()
            
            self._value_numerical.SetRange( lower, upper )
            
            service = self._service_like.GetClientData( self._service_like.GetSelection() )
            
        except: pass
        
        try:
            
            ( like, dislike ) = service.GetLikeDislike()
            
            selection = self._value_like.GetSelection()
            
            self._value_like.SetString( 0, like )
            self._value_like.SetString( 1, dislike )
            
            self._value_like.SetSelection( selection )
            
        except: pass
        
    
    def GetPredicate( self ): return self._predicate
    
class DialogInputLocalBooruShare( Dialog ):
    
    def __init__( self, parent, share_key, name, text, timeout, hashes, new_share = False ):
        
        def InitialiseControls():
            
            self._name = wx.TextCtrl( self )
            
            self._text = wx.TextCtrl( self, style = wx.TE_MULTILINE )
            self._text.SetMinSize( ( -1, 100 ) )
            
            message = 'expires in' 
            
            self._timeout_number = ClientGUICommon.NoneableSpinCtrl( self, message, none_phrase = 'no expiration', max = 1000000, multiplier = 1 )
            
            self._timeout_multiplier = ClientGUICommon.BetterChoice( self )
            self._timeout_multiplier.Append( 'minutes', 60 )
            self._timeout_multiplier.Append( 'hours', 60 * 60 )
            self._timeout_multiplier.Append( 'days', 60 * 60 * 24 )
            
            self._copy_internal_share_link = wx.Button( self, label = 'copy internal share link' )
            self._copy_internal_share_link.Bind( wx.EVT_BUTTON, self.EventCopyInternalShareURL )
            
            self._copy_external_share_link = wx.Button( self, label = 'copy external share link' )
            self._copy_external_share_link.Bind( wx.EVT_BUTTON, self.EventCopyExternalShareURL )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._share_key = share_key
            self._name.SetValue( name )
            self._text.SetValue( text )
            
            if timeout is None:
                
                self._timeout_number.SetValue( None )
                
                self._timeout_multiplier.SelectClientData( 60 )
                
            else:
                
                time_left = max( 0, timeout - HydrusData.GetNow() )
                
                if time_left < 60 * 60 * 12: time_value = 60
                elif time_left < 60 * 60 * 24 * 7: time_value = 60 * 60 
                else: time_value = 60 * 60 * 24
                
                self._timeout_number.SetValue( time_left / time_value )
                
                self._timeout_multiplier.SelectClientData( time_value )
                
            
            self._hashes = hashes
            
        
        def ArrangeControls():
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label = 'share name' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._name, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            gridbox.AddF( wx.StaticText( self, label = 'share text' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._text, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            timeout_box = wx.BoxSizer( wx.HORIZONTAL )
            timeout_box.AddF( self._timeout_number, CC.FLAGS_EXPAND_BOTH_WAYS )
            timeout_box.AddF( self._timeout_multiplier, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            link_box = wx.BoxSizer( wx.HORIZONTAL )
            link_box.AddF( self._copy_internal_share_link, CC.FLAGS_MIXED )
            link_box.AddF( self._copy_external_share_link, CC.FLAGS_MIXED )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, CC.FLAGS_MIXED )
            b_box.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            intro = 'Sharing ' + HydrusData.ConvertIntToPrettyString( len( self._hashes ) ) + ' files.'
            intro += os.linesep + 'Title and text are optional.'
            
            if new_share: intro += os.linesep + 'The link will not work until you ok this dialog.'
            
            vbox.AddF( wx.StaticText( self, label = intro ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( timeout_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( link_box, CC.FLAGS_BUTTON_SIZER )
            vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            x = max( x, 350 )
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'configure local booru share' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventCopyExternalShareURL( self, event ):
        
        self._service = wx.GetApp().GetManager( 'services' ).GetService( CC.LOCAL_BOORU_SERVICE_KEY )
        
        info = self._service.GetInfo()
        
        external_ip = HydrusNATPunch.GetExternalIP() # eventually check for optional host replacement here
        
        external_port = info[ 'upnp' ]
        
        if external_port is None: external_port = info[ 'port' ]
        
        url = 'http://' + external_ip + ':' + str( external_port ) + '/gallery?share_key=' + self._share_key.encode( 'hex' )
        
        HydrusGlobals.pubsub.pub( 'clipboard', 'text', url )
        
    
    def EventCopyInternalShareURL( self, event ):
        
        self._service = wx.GetApp().GetManager( 'services' ).GetService( CC.LOCAL_BOORU_SERVICE_KEY )
        
        info = self._service.GetInfo()
        
        internal_ip = '127.0.0.1'
        
        internal_port = info[ 'port' ]
        
        url = 'http://' + internal_ip + ':' + str( internal_port ) + '/gallery?share_key=' + self._share_key.encode( 'hex' )
        
        HydrusGlobals.pubsub.pub( 'clipboard', 'text', url )
        
    
    def GetInfo( self ):
        
        name = self._name.GetValue()
        
        text = self._text.GetValue()
        
        timeout = self._timeout_number.GetValue()
        
        if timeout is not None: timeout = timeout * self._timeout_multiplier.GetChoice() + HydrusData.GetNow()
        
        return ( self._share_key, name, text, timeout, self._hashes )
        
    
class DialogInputLocalFiles( Dialog ):
    
    def __init__( self, parent, paths = None ):
        
        if paths is None: paths = []
        
        def InitialiseControls():
            
            self._paths_list = ClientGUICommon.SaneListCtrl( self, 120, [ ( 'path', -1 ), ( 'guessed mime', 110 ), ( 'size', 60 ) ], delete_key_callback = self.RemovePaths )
            
            self._gauge = ClientGUICommon.Gauge( self )
            
            self._gauge_text = wx.StaticText( self, label = '' )
            
            self._gauge_pause = wx.Button( self, label = 'pause' )
            self._gauge_pause.Bind( wx.EVT_BUTTON, self.EventGaugePause )
            self._gauge_pause.Disable()
            
            self._gauge_cancel = wx.Button( self, label = 'cancel' )
            self._gauge_cancel.Bind( wx.EVT_BUTTON, self.EventGaugeCancel )
            self._gauge_cancel.Disable()
            
            self._add_files_button = wx.Button( self, label = 'Add Files' )
            self._add_files_button.Bind( wx.EVT_BUTTON, self.EventAddPaths )
            
            self._add_folder_button = wx.Button( self, label = 'Add Folder' )
            self._add_folder_button.Bind( wx.EVT_BUTTON, self.EventAddFolder )
            
            self._remove_files_button = wx.Button( self, label = 'Remove Files' )
            self._remove_files_button.Bind( wx.EVT_BUTTON, self.EventRemovePaths )
            
            self._advanced_import_options = ClientGUICollapsible.CollapsibleOptionsImport( self )
            
            self._delete_after_success = wx.CheckBox( self, label = 'delete files after successful import' )
            
            self._add_button = wx.Button( self, label = 'Import now' )
            self._add_button.Bind( wx.EVT_BUTTON, self.EventOK )
            self._add_button.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._tag_button = wx.Button( self, label = 'Add tags before importing' )
            self._tag_button.Bind( wx.EVT_BUTTON, self.EventTags )
            self._tag_button.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
            self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
    
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
            gauge_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            gauge_sizer.AddF( self._gauge_text, CC.FLAGS_EXPAND_BOTH_WAYS )
            gauge_sizer.AddF( self._gauge, CC.FLAGS_EXPAND_BOTH_WAYS )
            gauge_sizer.AddF( self._gauge_pause, CC.FLAGS_MIXED )
            gauge_sizer.AddF( self._gauge_cancel, CC.FLAGS_MIXED )
            
            file_buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            file_buttons.AddF( self._add_files_button, CC.FLAGS_MIXED )
            file_buttons.AddF( self._add_folder_button, CC.FLAGS_MIXED )
            file_buttons.AddF( self._remove_files_button, CC.FLAGS_MIXED )
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._add_button, CC.FLAGS_MIXED )
            buttons.AddF( self._tag_button, CC.FLAGS_MIXED )
            buttons.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._paths_list, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( gauge_sizer, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( file_buttons, CC.FLAGS_BUTTON_SIZER )
            vbox.AddF( self._advanced_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._delete_after_success, CC.FLAGS_LONE_BUTTON )
            vbox.AddF( ( 0, 5 ), CC.FLAGS_NONE )
            vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 780: x = 780
            if y < 480: y = 480
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'importing files' )
        
        self.SetDropTarget( ClientGUICommon.FileDropTarget( self._AddPathsToList ) )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self._processing_queue = []
        self._currently_parsing = False
        
        self._current_paths = set()
        
        self._job_key = HydrusData.JobKey()
        
        if len( paths ) > 0: self._AddPathsToList( paths )
        
        wx.CallAfter( self._add_button.SetFocus )
        
    
    def _AddPathsToList( self, paths ):
        
        self._processing_queue.append( paths )
        
        self._ProcessQueue()
        
    
    def _GetPathsInfo( self ): return [ row[0] for row in self._paths_list.GetClientData() ]
    
    def _ProcessQueue( self ):
        
        if not self._currently_parsing:
            
            if len( self._processing_queue ) == 0:
                
                self._gauge_pause.Disable()
                self._gauge_cancel.Disable()
                
                self._add_button.Enable()
                self._tag_button.Enable()
                
            else:
                
                paths = self._processing_queue.pop( 0 )
                
                self._currently_parsing = True
                
                self._job_key = HydrusData.JobKey()
                
                HydrusThreading.CallToThread( self.THREADParseImportablePaths, paths, self._job_key )
                
                self.SetGaugeInfo( None, None, '' )
                
                self._gauge_pause.Enable()
                self._gauge_cancel.Enable()
                
                self._add_button.Disable()
                self._tag_button.Disable()
                
            
        
    
    def _TidyUp( self ): self._job_key.Cancel()
    
    def AddParsedPath( self, path_type, mime, size, path_info ):
        
        pretty_size = HydrusData.ConvertIntToBytes( size )
        
        if path_type == 'path': pretty_path = path_info
        elif path_type == 'zip':
            
            ( zip_path, name ) = path_info
            
            pretty_path = zip_path + os.path.sep + name
            
        
        if ( path_type, path_info ) not in self._current_paths:
            
            self._current_paths.add( ( path_type, path_info ) )
            
            self._paths_list.Append( ( pretty_path, HC.mime_string_lookup[ mime ], pretty_size ), ( ( path_type, path_info ), mime, size ) )
            
        
    
    def DoneParsing( self ):
        
        self._currently_parsing = False
        
        self._ProcessQueue()
        
    
    def EventAddPaths( self, event ):
        
        with wx.FileDialog( self, 'Select the files to add.', style = wx.FD_MULTIPLE ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                paths = dlg.GetPaths()
                
                self._AddPathsToList( paths )
                
            
        
    
    def EventAddFolder( self, event ):
        
        with wx.DirDialog( self, 'Select a folder to add.', style = wx.DD_DIR_MUST_EXIST ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                self._AddPathsToList( ( path, ) )
                
            
        
    
    def EventCancel( self, event ):
        
        self._TidyUp()
        
        self.EndModal( wx.ID_CANCEL )
        
    
    def EventGaugeCancel( self, event ):
        
        self._job_key.Cancel()
        
        self._gauge_pause.Disable()
        self._gauge_cancel.Disable()
        
        self._add_button.Enable()
        self._tag_button.Enable()
        
    
    def EventGaugePause( self, event ):
        
        if self._job_key.IsPaused():
            
            self._job_key.Resume()
            
            self._add_button.Disable()
            self._tag_button.Disable()
            
            self._gauge_pause.SetLabel( 'pause' )
            
        else:
            
            self._job_key.Pause()
            
            self._add_button.Enable()
            self._tag_button.Enable()
            
            self._gauge_pause.SetLabel( 'resume' )
            
        
    
    def EventOK( self, event ):
        
        self._TidyUp()
        
        paths_info = self._GetPathsInfo()
        
        if len( paths_info ) > 0:
            
            advanced_import_options = self._advanced_import_options.GetInfo()
            
            delete_after_success = self._delete_after_success.GetValue()
            
            HydrusGlobals.pubsub.pub( 'new_hdd_import', paths_info, advanced_import_options = advanced_import_options, delete_after_success = delete_after_success )
            
            self.EndModal( wx.ID_OK )
            
        
    
    def EventRemovePaths( self, event ): self.RemovePaths()
    
    def EventTags( self, event ):
        
        try:
            
            paths_info = self._GetPathsInfo()
            
            if len( paths_info ) > 0:
                
                advanced_import_options = self._advanced_import_options.GetInfo()
                
                paths_to_send_to_dialog = []
                
                for ( path_type, path_info ) in paths_info:
                    
                    if path_type == 'path': pretty_path = path_info
                    elif path_type == 'zip':
                        
                        ( zip_path, name ) = path_info
                        
                        pretty_path = zip_path + os.path.sep + name
                        
                    
                    paths_to_send_to_dialog.append( pretty_path )
                    
                
                with DialogPathsToTags( self, paths_to_send_to_dialog ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        delete_after_success = self._delete_after_success.GetValue()
                        
                        paths_to_tags = dlg.GetInfo()
                        
                        HydrusGlobals.pubsub.pub( 'new_hdd_import', paths_info, advanced_import_options = advanced_import_options, paths_to_tags = paths_to_tags, delete_after_success = delete_after_success )
                        
                        self.EndModal( wx.ID_OK )
                        
                    
                
            
        except: wx.MessageBox( traceback.format_exc() )
        
    
    def RemovePaths( self ):
        
        self._paths_list.RemoveAllSelected()
        
        self._current_paths = set( self._GetPathsInfo() )
        
    
    def SetGaugeInfo( self, range, value, text ):
        
        if range is None: self._gauge.Pulse()
        else:
            
            self._gauge.SetRange( range )
            self._gauge.SetValue( value )
            
        
        self._gauge_text.SetLabel( text )
        
    
    def THREADParseImportablePaths( self, raw_paths, job_key ):
        
        wx.CallAfter( self.SetGaugeInfo, None, None, u'Parsing files and folders.' )
        
        file_paths = ClientFiles.GetAllPaths( raw_paths )
        
        num_file_paths = len( file_paths )
        num_good_files = 0
        num_odd_files = 0
        
        for ( i, path ) in enumerate( file_paths ):
            
            if path.endswith( os.path.sep + 'Thumbs.db' ) or path.endswith( os.path.sep + 'thumbs.db' ): continue
            
            if i % 500 == 0: gc.collect()
            
            wx.CallAfter( self.SetGaugeInfo, num_file_paths, i, u'Done ' + HydrusData.ToString( i ) + '/' + HydrusData.ToString( num_file_paths ) )
            
            job_key.WaitOnPause()
            
            if job_key.IsCancelled(): break
            
            info = os.lstat( path )
            
            size = info[6]
            
            if size == 0:
                
                num_odd_files += 1
                
                HydrusData.ShowException( HydrusExceptions.SizeException( path + ' could not be imported because it is empty!' ) )
                
                continue
                
            
            mime = HydrusFileHandling.GetMime( path )
            
            if mime in HC.ALLOWED_MIMES:
                
                num_good_files += 1
                
                wx.CallAfter( self.AddParsedPath, 'path', mime, size, path )
                
            elif mime in HC.ARCHIVES:
                
                wx.CallAfter( self.SetGaugeInfo, num_file_paths, i, u'Found an archive; parsing\u2026' )
                
                if mime == HC.APPLICATION_HYDRUS_ENCRYPTED_ZIP:
                    
                    aes_key = None
                    iv = None
                    
                    if '.encrypted' in path:
                        
                        try:
                            
                            potential_key_path = path.replace( '.encrypted', '.key' )
                            
                            if os.path.exists( potential_key_path ):
                                
                                with open( potential_key_path, 'rb' ) as f: key_text = f.read()
                                
                                ( aes_key, iv ) = HydrusEncryption.AESTextToKey( key_text )
                                
                            
                        except: HydrusData.ShowText( 'Tried to read a key, but did not understand it.' )
                        
                    
                    job_key = HydrusData.JobKey()
                    
                    def WXTHREADGetAESKey( key ):
                        
                        while key is None:
                            
                            with DialogTextEntry( wx.GetApp().GetTopWindow(), 'Please enter the key for ' + path + '.' ) as dlg:
                                
                                result = dlg.ShowModal()
                                
                                if result == wx.ID_OK:
                                    
                                    try:
                                        
                                        key_text = dlg.GetValue()
                                        
                                        ( key, iv ) = HydrusEncryption.AESTextToKey( key_text )
                                        
                                        job_key.SetVariable( 'result', ( key, iv ) )
                                        
                                    except: wx.MessageBox( 'Did not understand that key!' )
                                    
                                elif result == wx.ID_CANCEL: job_key.SetVariable( 'result', ( None, None ) )
                                
                            
                        
                    
                    if aes_key is None:
                        
                        wx.CallAfter( WXTHREADGetAESKey, aes_key )
                        
                        while not job_key.HasVariable( 'result' ):
                            
                            if job_key.IsCancelled(): return
                            
                            time.sleep( 0.1 )
                            
                        
                        ( aes_key, iv ) = job_key.GetVariable( 'result' )
                        
                    
                    if aes_key is not None:
                        
                        path_to = HydrusEncryption.DecryptAESFile( aes_key, iv, path )
                        
                        path = path_to
                        mime = HC.APPLICATION_ZIP
                        
                    
                
                if mime == HC.APPLICATION_ZIP:
                    
                    try:
                        
                        with zipfile.ZipFile( path, 'r' ) as z:
                            
                            if z.testzip() is not None: raise Exception()
                            
                            for name in z.namelist():
                                
                                # zip is deflate, which means have to read the whole file to read any of the file, so:
                                # the file pointer returned by open doesn't support seek, lol!
                                # so, might as well open the whole damn file
                                
                                
                                ( os_file_handle, temp_path ) = HydrusFileHandling.GetTempPath()
                                
                                try:
                                    
                                    with open( temp_path, 'wb' ) as f: f.write( z.read( name ) )
                                    
                                    name_mime = HydrusFileHandling.GetMime( temp_path )
                                    
                                finally:
                                    
                                    HydrusFileHandling.CleanUpTempPath( os_file_handle, temp_path )
                                    
                                
                                if name_mime in HC.ALLOWED_MIMES:
                                    
                                    size = z.getinfo( name ).file_size
                                    
                                    if size > 0:
                                        
                                        num_good_files += 1
                                        
                                        wx.CallAfter( self.AddParsedPath, 'zip', name_mime, size, ( path, name ) )
                                        
                                    
                                
                            
                        
                    except Exception as e:
                        
                        num_odd_files += 1
                        
                        HydrusData.ShowException( e )
                        
                        continue
                        
                    
                
            else:
                
                num_odd_files += 1
                
                e = HydrusExceptions.MimeException( path + ' could not be imported because its mime is not supported.' )
                
                HydrusData.ShowException( e )
                
                continue
                
            
        
        if num_good_files > 0:
            
            if num_good_files == 1: message = '1 file was parsed successfully'
            else: message = HydrusData.ToString( num_good_files ) + ' files were parsed successfully'
            
            if num_odd_files > 0: message += ', but ' + HydrusData.ToString( num_odd_files ) + ' failed.'
            else: message += '.'
            
        else:
            
            message = HydrusData.ToString( num_odd_files ) + ' files could not be parsed.'
            
        
        wx.CallAfter( self.SetGaugeInfo, num_file_paths, num_file_paths, message )
        
        time.sleep( 1.5 )
        
        wx.CallAfter( self.DoneParsing )
        
    
class DialogInputMessageSystemPredicate( Dialog ):
    
    def __init__( self, parent, predicate_type ):
        
        def Age():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices=[ '<', u'\u2248', '>' ] )
                
                self._years = wx.SpinCtrl( self, max = 30 )
                self._months = wx.SpinCtrl( self, max = 60 )
                self._days = wx.SpinCtrl( self, max = 90 )
                
                self._ok = wx.Button( self, label = 'Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._sign.SetSelection( 0 )
                
                self._years.SetValue( 0 )
                self._months.SetValue( 0 )
                self._days.SetValue( 7 )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:age' ), CC.FLAGS_MIXED )
                hbox.AddF( self._sign, CC.FLAGS_MIXED )
                hbox.AddF( self._years, CC.FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label = 'years' ), CC.FLAGS_MIXED )
                hbox.AddF( self._months, CC.FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label = 'months' ), CC.FLAGS_MIXED )
                hbox.AddF( self._days, CC.FLAGS_MIXED )
                hbox.AddF( wx.StaticText( self, label = 'days' ), CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter age predicate' )
            
            InitialiseControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def From():
            
            def InitialiseControls():
                
                contact_names = wx.GetApp().Read( 'contact_names' )
                
                self._contact = wx.Choice( self, choices=contact_names )
                
                self._ok = wx.Button( self, label = 'Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._contact.SetSelection( 0 )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:from' ), CC.FLAGS_MIXED )
                hbox.AddF( self._contact, CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter from predicate' )
            
            InitialiseControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def StartedBy():
            
            def InitialiseControls():
                
                contact_names = wx.GetApp().Read( 'contact_names' )
                
                self._contact = wx.Choice( self, choices = contact_names )
                
                self._ok = wx.Button( self, label = 'Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._contact.SetSelection( 0 )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:started_by' ), CC.FLAGS_MIXED )
                hbox.AddF( self._contact, CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter started by predicate' )
            
            InitialiseControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def To():
            
            def InitialiseControls():
                
                contact_names = [ name for name in wx.GetApp().Read( 'contact_names' ) if name != 'Anonymous' ]
                
                self._contact = wx.Choice( self, choices = contact_names )
                
                self._ok = wx.Button( self, label = 'Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._contact.SetSelection( 0 )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:to' ), CC.FLAGS_MIXED )
                hbox.AddF( self._contact, CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter to predicate' )
            
            InitialiseControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        def NumAttachments():
            
            def InitialiseControls():
                
                self._sign = wx.Choice( self, choices=[ '<', '=', '>' ] )
                
                self._num_attachments = wx.SpinCtrl( self, max = 2000 )
                
                self._ok = wx.Button( self, label = 'Ok' )
                self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
                self._ok.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            def PopulateControls():
                
                self._sign.SetSelection( 0 )
                
                self._num_attachments.SetValue( 4 )
                
            
            def ArrangeControls():
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self, label = 'system:numattachments' ), CC.FLAGS_MIXED )
                hbox.AddF( self._sign, CC.FLAGS_MIXED )
                hbox.AddF( self._num_attachments, CC.FLAGS_MIXED )
                hbox.AddF( self._ok, CC.FLAGS_MIXED )
                
                self.SetSizer( hbox )
                
            
            Dialog.__init__( self, parent, 'enter number of attachments predicate' )
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
        
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
            wx.CallAfter( self._ok.SetFocus )
            
        
        self._type = predicate_type
        
        if self._type == 'system:age': Age()
        elif self._type == 'system:started_by': StartedBy()
        elif self._type == 'system:from': From()
        elif self._type == 'system:to': To()
        elif self._type == 'system:numattachments': NumAttachments()
        
        self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
        
    
    def EventOK( self, event ): self.EndModal( wx.ID_OK )
    
    def GetString( self ):
        
        if self._type == 'system:age': return 'system:age' + self._sign.GetStringSelection() + HydrusData.ToString( self._years.GetValue() ) + 'y' + HydrusData.ToString( self._months.GetValue() ) + 'm' + HydrusData.ToString( self._days.GetValue() ) + 'd'
        elif self._type == 'system:started_by': return 'system:started_by=' + self._contact.GetStringSelection()
        elif self._type == 'system:from': return 'system:from=' + self._contact.GetStringSelection()
        elif self._type == 'system:to': return 'system:to=' + self._contact.GetStringSelection()
        elif self._type == 'system:numattachments': return 'system:numattachments' + self._sign.GetStringSelection() + HydrusData.ToString( self._num_attachments.GetValue() )
        
    
class DialogInputNamespaceRegex( Dialog ):
    
    def __init__( self, parent, namespace = '', regex = '' ):
        
        def InitialiseControls():
            
            self._namespace = wx.TextCtrl( self )
            
            self._regex = wx.TextCtrl( self )
            
            self._shortcuts = ClientGUICommon.RegexButton( self )
            
            self._regex_link = wx.HyperlinkCtrl( self, id = -1, label = 'a good regex introduction', url = 'http://www.aivosto.com/vbtips/regex.html' )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._namespace.SetValue( namespace )
            self._regex.SetValue( regex )
            
        
        def ArrangeControls():
            
            control_box = wx.BoxSizer( wx.HORIZONTAL )
            
            control_box.AddF( self._namespace, CC.FLAGS_EXPAND_BOTH_WAYS )
            control_box.AddF( wx.StaticText( self, label = ':' ), CC.FLAGS_MIXED )
            control_box.AddF( self._regex, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, CC.FLAGS_MIXED )
            b_box.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            intro = 'Put the namespace (e.g. page) on the left.' + os.linesep + 'Put the regex (e.g. [1-9]+\d*(?=.{4}$)) on the right.' + os.linesep + 'All files will be tagged with "namespace:regex".'
            
            vbox.AddF( wx.StaticText( self, label = intro ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( control_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( self._shortcuts, CC.FLAGS_LONE_BUTTON )
            vbox.AddF( self._regex_link, CC.FLAGS_LONE_BUTTON )
            vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'configure quick namespace' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def GetInfo( self ):
        
        namespace = self._namespace.GetValue()
        
        regex = self._regex.GetValue()
        
        return ( namespace, regex )
        
    
class DialogInputNewAccountType( Dialog ):
    
    def __init__( self, parent, account_type = None ):
        
        def InitialiseControls():
            
            self._title = wx.TextCtrl( self )
            
            self._permissions_panel = ClientGUICommon.StaticBox( self, 'permissions' )
            
            self._permissions = wx.ListBox( self._permissions_panel )
            
            self._permission_choice = wx.Choice( self._permissions_panel )
            
            self._add_permission = wx.Button( self._permissions_panel, label = 'add' )
            self._add_permission.Bind( wx.EVT_BUTTON, self.EventAddPermission )
            
            self._remove_permission = wx.Button( self._permissions_panel, label = 'remove' )
            self._remove_permission.Bind( wx.EVT_BUTTON, self.EventRemovePermission )
            
            self._max_num_mb = ClientGUICommon.NoneableSpinCtrl( self, 'max monthly data (MB)', multiplier = 1048576 )
            self._max_num_mb.SetValue( max_num_bytes )
            
            self._max_num_requests = ClientGUICommon.NoneableSpinCtrl( self, 'max monthly requests' )
            self._max_num_requests.SetValue( max_num_requests )
            
            self._apply = wx.Button( self, id = wx.ID_OK, label = 'apply' )
            self._apply.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._title.SetValue( title )
            
            for permission in permissions: self._permissions.Append( HC.permissions_string_lookup[ permission ], permission )
            
            for permission in HC.CREATABLE_PERMISSIONS: self._permission_choice.Append( HC.permissions_string_lookup[ permission ], permission )
            self._permission_choice.SetSelection( 0 )
            
        
        def ArrangeControls():
            
            t_box = wx.BoxSizer( wx.HORIZONTAL )
            
            t_box.AddF( wx.StaticText( self, label = 'title: ' ), CC.FLAGS_SMALL_INDENT )
            t_box.AddF( self._title, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            perm_buttons_box = wx.BoxSizer( wx.HORIZONTAL )
            
            perm_buttons_box.AddF( self._permission_choice, CC.FLAGS_MIXED )
            perm_buttons_box.AddF( self._add_permission, CC.FLAGS_MIXED )
            perm_buttons_box.AddF( self._remove_permission, CC.FLAGS_MIXED )
            
            self._permissions_panel.AddF( self._permissions, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._permissions_panel.AddF( perm_buttons_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            
            b_box.AddF( self._apply, CC.FLAGS_MIXED )
            b_box.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( t_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( self._permissions_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._max_num_mb, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._max_num_requests, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( 800, y ) )
            
        
        if account_type is None:
            
            title = ''
            permissions = [ HC.GET_DATA ]
            max_num_bytes = 104857600
            max_num_requests = 1000
            
        else:
            
            title = account_type.GetTitle()
            permissions = account_type.GetPermissions()
            max_num_bytes = account_type.GetMaxBytes()
            max_num_requests = account_type.GetMaxRequests()
            
        
        Dialog.__init__( self, parent, 'edit account type' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._apply.SetFocus )
        
    
    def EventAddPermission( self, event ):
        
        selection = self._permission_choice.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            permission = self._permission_choice.GetClientData( selection )
            
            existing_permissions = [ self._permissions.GetClientData( i ) for i in range( self._permissions.GetCount() ) ]
            
            if permission not in existing_permissions: self._permissions.Append( HC.permissions_string_lookup[ permission ], permission )
            
        
    
    def EventRemovePermission( self, event ):
        
        selection = self._permissions.GetSelection()
        
        if selection != wx.NOT_FOUND: self._permissions.Delete( selection )
        
    
    def GetAccountType( self ):
        
        title = self._title.GetValue()
        
        permissions = [ self._permissions.GetClientData( i ) for i in range( self._permissions.GetCount() ) ]
        
        max_num_bytes = self._max_num_mb.GetValue()
        
        max_num_requests = self._max_num_requests.GetValue()
        
        return HydrusData.AccountType( title, permissions, ( max_num_bytes, max_num_requests ) )
        
    
class DialogInputNewFormField( Dialog ):
    
    def __init__( self, parent, form_field = None ):
        
        def InitialiseControls():
            
            self._name = wx.TextCtrl( self )
            
            self._type = wx.Choice( self )
            
            self._default = wx.TextCtrl( self )
            
            self._editable = wx.CheckBox( self )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )   
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            self._name.SetValue( name )
            
            for temp_type in CC.FIELDS: self._type.Append( CC.field_string_lookup[ temp_type ], temp_type )
            self._type.Select( field_type )
            
            self._default.SetValue( default )
            
            self._editable.SetValue( editable )
            
        
        def ArrangeControls():
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label = 'name' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._name, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            gridbox.AddF( wx.StaticText( self, label = 'type' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._type, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            gridbox.AddF( wx.StaticText( self, label = 'default' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._default, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            gridbox.AddF( wx.StaticText( self, label = 'editable' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._editable, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            
            b_box.AddF( self._ok, CC.FLAGS_MIXED )
            b_box.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'configure form field' )
        
        if form_field is None: ( name, field_type, default, editable ) = ( '', CC.FIELD_TEXT, '', True )
        else: ( name, field_type, default, editable ) = form_field
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def GetFormField( self ):
        
        name = self._name.GetValue()
        
        field_type = self._type.GetClientData( self._type.GetSelection() )
        
        default = self._default.GetValue()
        
        editable = self._editable.GetValue()
        
        return ( name, field_type, default, editable )
        
    
class DialogInputShortcut( Dialog ):
    
    def __init__( self, parent, modifier = wx.ACCEL_NORMAL, key = wx.WXK_F7, action = 'new_page' ):
        
        self._action = action
        
        def InitialiseControls():
            
            self._shortcut = ClientGUICommon.Shortcut( self, modifier, key )
            
            self._actions = wx.Choice( self, choices = [ 'archive', 'inbox', 'close_page', 'filter', 'fullscreen_switch', 'ratings_filter', 'frame_back', 'frame_next', 'manage_ratings', 'manage_tags', 'new_page', 'refresh', 'set_search_focus', 'show_hide_splitters', 'synchronised_wait_switch', 'previous', 'next', 'first', 'last', 'undo', 'redo', 'open_externally' ] )
            
            self._ok = wx.Button( self, id= wx.ID_OK, label = 'Ok' )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
    
        def PopulateControls():
            
            self._actions.SetSelection( self._actions.FindString( action ) )
            
        
        def ArrangeControls():
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._shortcut, CC.FLAGS_MIXED )
            hbox.AddF( self._actions, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, CC.FLAGS_MIXED )
            b_box.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'configure shortcut' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def GetInfo( self ):
        
        ( modifier, key ) = self._shortcut.GetValue()
        
        return ( modifier, key, self._actions.GetStringSelection() )
        
    
class DialogInputUPnPMapping( Dialog ):
    
    def __init__( self, parent, external_port, protocol_type, internal_port, description, duration ):
        
        def InitialiseControls():
            
            self._external_port = wx.SpinCtrl( self, min = 0, max = 65535 )
            
            self._protocol_type = ClientGUICommon.BetterChoice( self )
            self._protocol_type.Append( 'TCP', 'TCP' )
            self._protocol_type.Append( 'UDP', 'UDP' )
            
            self._internal_port = wx.SpinCtrl( self, min = 0, max = 65535 )
            self._description = wx.TextCtrl( self )
            self._duration = wx.SpinCtrl( self, min = 0, max = 86400 )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
    
        def PopulateControls():
            
            self._external_port.SetValue( external_port )
            
            if protocol_type == 'TCP': self._protocol_type.Select( 0 )
            elif protocol_type == 'UDP': self._protocol_type.Select( 1 )
            
            self._internal_port.SetValue( internal_port )
            self._description.SetValue( description )
            self._duration.SetValue( duration )
            
        
        def ArrangeControls():
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label = 'external port' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._external_port, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            gridbox.AddF( wx.StaticText( self, label = 'protocol type' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._protocol_type, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            gridbox.AddF( wx.StaticText( self, label = 'internal port' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._internal_port, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            gridbox.AddF( wx.StaticText( self, label = 'description' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._description, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            gridbox.AddF( wx.StaticText( self, label = 'duration (0 = indefinite)' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._duration, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            b_box = wx.BoxSizer( wx.HORIZONTAL )
            b_box.AddF( self._ok, CC.FLAGS_MIXED )
            b_box.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'configure upnp mapping' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def GetInfo( self ):
        
        external_port = self._external_port.GetValue()
        protocol_type = self._protocol_type.GetChoice()
        internal_port = self._internal_port.GetValue()
        description = self._description.GetValue()
        duration = self._duration.GetValue()
        
        return ( external_port, protocol_type, internal_port, description, duration )
        
    
class DialogModifyAccounts( Dialog ):
    
    def __init__( self, parent, service_key, subject_identifiers ):
        
        def InitialiseControls():
            
            self._account_info_panel = ClientGUICommon.StaticBox( self, 'account info' )
            
            self._subject_text = wx.StaticText( self._account_info_panel )
            
            #
            
            self._account_types_panel = ClientGUICommon.StaticBox( self, 'account types' )
            
            self._account_types = wx.Choice( self._account_types_panel )
            
            self._account_types_ok = wx.Button( self._account_types_panel, label = 'Ok' )
            self._account_types_ok.Bind( wx.EVT_BUTTON, self.EventChangeAccountType )
            
            #
            
            self._expiration_panel = ClientGUICommon.StaticBox( self, 'change expiration' )
            
            self._add_to_expires = wx.Choice( self._expiration_panel )
            
            self._add_to_expires_ok = wx.Button( self._expiration_panel, label = 'Ok' )
            self._add_to_expires_ok.Bind( wx.EVT_BUTTON, self.EventAddToExpires )
            
            self._set_expires = wx.Choice( self._expiration_panel )
            
            self._set_expires_ok = wx.Button( self._expiration_panel, label = 'Ok' )
            self._set_expires_ok.Bind( wx.EVT_BUTTON, self.EventSetExpires )
            
            #
            
            self._ban_panel = ClientGUICommon.StaticBox( self, 'bans' )
            
            self._ban = wx.Button( self._ban_panel, label = 'ban user' )
            self._ban.Bind( wx.EVT_BUTTON, self.EventBan )        
            self._ban.SetBackgroundColour( ( 255, 0, 0 ) )
            self._ban.SetForegroundColour( ( 255, 255, 0 ) )
            
            self._superban = wx.Button( self._ban_panel, label = 'ban user and delete every contribution they have ever made' )
            self._superban.Bind( wx.EVT_BUTTON, self.EventSuperban )        
            self._superban.SetBackgroundColour( ( 255, 0, 0 ) )
            self._superban.SetForegroundColour( ( 255, 255, 0 ) )
            
            self._exit = wx.Button( self, id = wx.ID_CANCEL, label = 'Exit' )
            
    
        def PopulateControls():
            
            if len( self._subject_identifiers ) == 1:
                
                ( subject_identifier, ) = self._subject_identifiers
                
                response = self._service.Request( HC.GET, 'account_info', { 'subject_identifier' : subject_identifier } )
                
                subject_string = HydrusData.ToString( response[ 'account_info' ] )
                
            else: subject_string = 'modifying ' + HydrusData.ConvertIntToPrettyString( len( self._subject_identifiers ) ) + ' accounts'
            
            self._subject_text.SetLabel( subject_string )
            
            #
            
            response = self._service.Request( HC.GET, 'account_types' )
            
            account_types = response[ 'account_types' ]
            
            for account_type in account_types: self._account_types.Append( account_type.ConvertToString(), account_type )
            
            self._account_types.SetSelection( 0 )
            
            #
            
            for ( string, value ) in HC.lifetimes:
                
                if value is not None: self._add_to_expires.Append( string, value ) # don't want 'add no limit'
                
            
            self._add_to_expires.SetSelection( 1 ) # three months
            
            for ( string, value ) in HC.lifetimes: self._set_expires.Append( string, value )
            self._set_expires.SetSelection( 1 ) # three months
            
            #
            
            if not self._service.GetInfo( 'account' ).HasPermission( HC.GENERAL_ADMIN ):
                
                self._account_types_ok.Disable()
                self._add_to_expires_ok.Disable()
                self._set_expires_ok.Disable()
                
            
        
        def ArrangeControls():
            
            self._account_info_panel.AddF( self._subject_text, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            account_types_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            account_types_hbox.AddF( self._account_types, CC.FLAGS_MIXED )
            account_types_hbox.AddF( self._account_types_ok, CC.FLAGS_MIXED )
            
            self._account_types_panel.AddF( account_types_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            add_to_expires_box = wx.BoxSizer( wx.HORIZONTAL )
            
            add_to_expires_box.AddF( wx.StaticText( self._expiration_panel, label = 'add to expires: ' ), CC.FLAGS_MIXED )
            add_to_expires_box.AddF( self._add_to_expires, CC.FLAGS_EXPAND_BOTH_WAYS )
            add_to_expires_box.AddF( self._add_to_expires_ok, CC.FLAGS_MIXED )
            
            set_expires_box = wx.BoxSizer( wx.HORIZONTAL )
            
            set_expires_box.AddF( wx.StaticText( self._expiration_panel, label = 'set expires to: ' ), CC.FLAGS_MIXED )
            set_expires_box.AddF( self._set_expires, CC.FLAGS_EXPAND_BOTH_WAYS )
            set_expires_box.AddF( self._set_expires_ok, CC.FLAGS_MIXED )
            
            self._expiration_panel.AddF( add_to_expires_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._expiration_panel.AddF( set_expires_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._ban_panel.AddF( self._ban, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._ban_panel.AddF( self._superban, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._account_info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._account_types_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._expiration_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._ban_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._exit, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'modify account' )
        
        self._service = wx.GetApp().GetManager( 'services' ).GetService( service_key )
        self._subject_identifiers = list( subject_identifiers )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._exit.SetFocus )
        
    
    def _DoModification( self, action, **kwargs ):
        
        request_args = kwargs
        
        request_args[ 'subject_identifiers' ] = self._subject_identifiers
        request_args[ 'action' ] = action
        
        self._service.Request( HC.POST, 'account', request_args )
        
        if len( self._subject_identifiers ) == 1:
            
            ( subject_identifier, ) = self._subject_identifiers
            
            response = self._service.Request( HC.GET, 'account_info', { 'subject_identifier' : subject_identifier } )
            
            account_info = response[ 'account_info' ]
            
            self._subject_text.SetLabel( HydrusData.ToString( account_info ) )
            
        
        if len( self._subject_identifiers ) > 1: wx.MessageBox( 'Done!' )
        
    
    def EventAddToExpires( self, event ): self._DoModification( HC.ADD_TO_EXPIRES, timespan = self._add_to_expires.GetClientData( self._add_to_expires.GetSelection() ) )
    
    def EventBan( self, event ):
        
        with DialogTextEntry( self, 'Enter reason for the ban.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK: self._DoModification( HC.BAN, reason = dlg.GetValue() )
            
        
    
    def EventChangeAccountType( self, event ): self._DoModification( HC.CHANGE_ACCOUNT_TYPE, title = self._account_types.GetClientData( self._account_types.GetSelection() ).GetTitle() )
    
    def EventSetExpires( self, event ):
        
        expires = self._set_expires.GetClientData( self._set_expires.GetSelection() )
        
        if expires is not None: expires += HydrusData.GetNow()
        
        self._DoModification( HC.SET_EXPIRES, expires = expires )
        
    
    def EventSuperban( self, event ):
        
        with DialogTextEntry( self, 'Enter reason for the superban.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK: self._DoModification( HC.SUPERBAN, reason = dlg.GetValue() )
            
        
    
class DialogNews( Dialog ):
    
    def __init__( self, parent, service_key ):
        
        def InitialiseControls():
            
            self._news = wx.TextCtrl( self, style = wx.TE_READONLY | wx.TE_MULTILINE )
            
            self._previous = wx.Button( self, label = '<' )
            self._previous.Bind( wx.EVT_BUTTON, self.EventPrevious )
            
            self._news_position = wx.TextCtrl( self )
            
            self._next = wx.Button( self, label = '>' )
            self._next.Bind( wx.EVT_BUTTON, self.EventNext )
            
            self._done = wx.Button( self, id = wx.ID_CANCEL, label = 'Done' )
            
    
        def PopulateControls():
            
            self._newslist = wx.GetApp().Read( 'news', service_key )
            
            self._current_news_position = len( self._newslist )
            
            self._ShowNews()
            
        
        def ArrangeControls():
            
            buttonbox = wx.BoxSizer( wx.HORIZONTAL )
            
            buttonbox.AddF( self._previous, CC.FLAGS_MIXED )
            buttonbox.AddF( self._news_position, CC.FLAGS_MIXED )
            buttonbox.AddF( self._next, CC.FLAGS_MIXED )
            
            donebox = wx.BoxSizer( wx.HORIZONTAL )
            
            donebox.AddF( self._done, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._news, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttonbox, CC.FLAGS_BUTTON_SIZER )
            vbox.AddF( donebox, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x + 200, 580 ) )
            
        
        Dialog.__init__( self, parent, 'news' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._done.SetFocus )
        
    
    def _ShowNews( self ):
        
        if self._current_news_position == 0:
            
            self._news.SetValue( '' )
            
            self._news_position.SetValue( 'No News' )
            
        else:
            
            ( news, timestamp ) = self._newslist[ self._current_news_position - 1 ]
            
            self._news.SetValue( time.ctime( timestamp ) + ' (' + HydrusData.ConvertTimestampToPrettyAgo( timestamp ) + '):' + os.linesep * 2 + news )
            
            self._news_position.SetValue( HydrusData.ConvertIntToPrettyString( self._current_news_position ) + ' / ' + HydrusData.ConvertIntToPrettyString( len( self._newslist ) ) )
            
        
    
    def EventNext( self, event ):
        
        if self._current_news_position < len( self._newslist ): self._current_news_position += 1
        
        self._ShowNews()
        
    
    def EventPrevious( self, event ):
        
        if self._current_news_position > 1: self._current_news_position -= 1
        
        self._ShowNews()
        
    
class DialogPageChooser( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
            
            self._button_hidden = wx.Button( self )
            self._button_hidden.Hide()
            
            self._button_1 = wx.Button( self, label = '', id = 1 )
            self._button_2 = wx.Button( self, label = '', id = 2 )
            self._button_3 = wx.Button( self, label = '', id = 3 )
            self._button_4 = wx.Button( self, label = '', id = 4 )
            self._button_5 = wx.Button( self, label = '', id = 5 )
            self._button_6 = wx.Button( self, label = '', id = 6 )
            self._button_7 = wx.Button( self, label = '', id = 7 )
            self._button_8 = wx.Button( self, label = '', id = 8 )
            self._button_9 = wx.Button( self, label = '', id = 9 )
            
        
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            gridbox = wx.GridSizer( 0, 3 )
            
            gridbox.AddF( self._button_7, CC.FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_8, CC.FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_9, CC.FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_4, CC.FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_5, CC.FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_6, CC.FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_1, CC.FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_2, CC.FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_3, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.SetSizer( gridbox )
            
            self.SetInitialSize( ( 420, 210 ) )
            
        
        Dialog.__init__( self, parent, 'new page', position = 'center' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self._services = wx.GetApp().GetManager( 'services' ).GetServices()
        
        self._petition_service_keys = [ service.GetServiceKey() for service in self._services if service.GetServiceType() in HC.REPOSITORIES and service.GetInfo( 'account' ).HasPermission( HC.RESOLVE_PETITIONS ) ]
        
        self._InitButtons( 'home' )
        
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self._button_hidden.SetFocus()
        
        #
        
        entries = []
        
        entries.append( ( wx.ACCEL_NORMAL, wx.WXK_UP, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'button', 8 ) ) )
        entries.append( ( wx.ACCEL_NORMAL, wx.WXK_LEFT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'button', 4 ) ) )
        entries.append( ( wx.ACCEL_NORMAL, wx.WXK_RIGHT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'button', 6 ) ) )
        entries.append( ( wx.ACCEL_NORMAL, wx.WXK_DOWN, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'button', 2 ) ) )
        
        entries.append( ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD1, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'button', 1 ) ) )
        entries.append( ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD2, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'button', 2 ) ) )
        entries.append( ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD3, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'button', 3 ) ) )
        entries.append( ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD4, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'button', 4 ) ) )
        entries.append( ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD5, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'button', 5 ) ) )
        entries.append( ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD6, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'button', 6 ) ) )
        entries.append( ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD7, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'button', 7 ) ) )
        entries.append( ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD8, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'button', 8 ) ) )
        entries.append( ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD9, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'button', 9 ) ) )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
        #
        
        self.Show( True )
        
    
    def _AddEntry( self, button, entry ):
        
        id = button.GetId()
        
        self._command_dict[ id ] = entry
        
        ( entry_type, obj ) = entry
        
        if entry_type == 'menu': button.SetLabel( obj )
        elif entry_type in ( 'page_query', 'page_petitions' ):
            
            name = wx.GetApp().GetManager( 'services' ).GetService( obj ).GetName()
            
            button.SetLabel( name )
            
        elif entry_type == 'page_import_booru': button.SetLabel( 'booru' )
        elif entry_type == 'page_import_gallery':
            
            ( name, gallery_type ) = obj
            
            if gallery_type is None: button.SetLabel( name )
            else: button.SetLabel( name + ' by ' + gallery_type )
            
        elif entry_type == 'page_import_thread_watcher': button.SetLabel( 'thread watcher' )
        elif entry_type == 'page_import_url': button.SetLabel( 'url' )
        
        button.Show()
        
    
    def _InitButtons( self, menu_keyword ):
        
        self._command_dict = {}
        
        if menu_keyword == 'home':
            
            entries = [ ( 'menu', 'files' ), ( 'menu', 'download' ) ]
            
            if len( self._petition_service_keys ) > 0: entries.append( ( 'menu', 'petitions' ) )
            
        elif menu_keyword == 'files':
            
            file_repos = [ ( 'page_query', service_key ) for service_key in [ service.GetServiceKey() for service in self._services if service.GetServiceType() == HC.FILE_REPOSITORY ] ]
            
            entries = [ ( 'page_query', CC.LOCAL_FILE_SERVICE_KEY ) ] + file_repos
            
        elif menu_keyword == 'download': entries = [ ( 'page_import_url', None ), ( 'page_import_thread_watcher', None ), ( 'menu', 'gallery' ) ]
        elif menu_keyword == 'gallery':
            
            entries = [ ( 'page_import_booru', None ), ( 'page_import_gallery', ( 'giphy', None ) ), ( 'page_import_gallery', ( 'deviant art', 'artist' ) ), ( 'menu', 'hentai foundry' ), ( 'page_import_gallery', ( 'newgrounds', None ) ) ]
            
            ( id, password ) = wx.GetApp().Read( 'pixiv_account' )
            
            if id != '' and password != '': entries.append( ( 'menu', 'pixiv' ) )
            
            entries.extend( [ ( 'page_import_gallery', ( 'tumblr', None ) ) ] )
            
        elif menu_keyword == 'hentai foundry': entries = [ ( 'page_import_gallery', ( 'hentai foundry', 'artist' ) ), ( 'page_import_gallery', ( 'hentai foundry', 'tags' ) ) ]
        elif menu_keyword == 'pixiv': entries = [ ( 'page_import_gallery', ( 'pixiv', 'artist_id' ) ), ( 'page_import_gallery', ( 'pixiv', 'tag' ) ) ]
        elif menu_keyword == 'petitions': entries = [ ( 'page_petitions', service_key ) for service_key in self._petition_service_keys ]
        
        if len( entries ) <= 4:
            
            self._button_1.Hide()
            self._button_3.Hide()
            self._button_5.Hide()
            self._button_7.Hide()
            self._button_9.Hide()
            
            potential_buttons = [ self._button_8, self._button_4, self._button_6, self._button_2 ]
            
        elif len( entries ) <= 9: potential_buttons = [ self._button_7, self._button_8, self._button_9, self._button_4, self._button_5, self._button_6, self._button_1, self._button_2, self._button_3 ]
        else:
            
            pass # sort out a multi-page solution? maybe only if this becomes a big thing; the person can always select from the menus, yeah?
            
            potential_buttons = [ self._button_7, self._button_8, self._button_9, self._button_4, self._button_5, self._button_6, self._button_1, self._button_2, self._button_3 ]
            entries = entries[:9]
            
        
        for entry in entries: self._AddEntry( potential_buttons.pop( 0 ), entry )
        
        unused_buttons = potential_buttons
        
        for button in unused_buttons: button.Hide()
        
    
    def EventButton( self, event ):
        
        id = event.GetId()
        
        if id == wx.ID_CANCEL: self.EndModal( wx.ID_CANCEL )
        elif id in self._command_dict:
            
            ( entry_type, obj ) = self._command_dict[ id ]
            
            if entry_type == 'menu': self._InitButtons( obj )
            else:
                
                if entry_type == 'page_query': HydrusGlobals.pubsub.pub( 'new_page_query', obj )
                elif entry_type == 'page_import_booru':
                    
                    with DialogSelectBooru( self ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            booru = dlg.GetBooru()
                            
                            HydrusGlobals.pubsub.pub( 'new_page_import_gallery', 'booru', booru )
                            
                        
                    
                elif entry_type == 'page_import_gallery':
                    
                    ( gallery_name, gallery_type ) = obj
                    
                    HydrusGlobals.pubsub.pub( 'new_page_import_gallery', gallery_name, gallery_type )
                    
                elif entry_type == 'page_import_thread_watcher': HydrusGlobals.pubsub.pub( 'new_page_import_thread_watcher' )
                elif entry_type == 'page_import_url': HydrusGlobals.pubsub.pub( 'new_page_import_url' )
                elif entry_type == 'page_petitions': HydrusGlobals.pubsub.pub( 'new_page_petitions', obj )
                
                self.EndModal( wx.ID_OK )
                
            
        
        self._button_hidden.SetFocus()
        
    
    def EventCharHook( self, event ):
        
        if event.KeyCode == wx.WXK_ESCAPE: self.EndModal( wx.ID_OK )
        else: event.Skip()
        
    
    def EventMenu( self, event ):
        
        event_id = event.GetId()
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event_id )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'button':
                
                new_event = wx.CommandEvent( wx.wxEVT_COMMAND_BUTTON_CLICKED, winid = data )
                
                self.ProcessEvent( new_event )
                
            
        
    
class DialogPathsToTags( Dialog ):
    
    def __init__( self, parent, paths ):
        
        def InitialiseControls():
            
            self._tag_repositories = ClientGUICommon.ListBook( self )
            self._tag_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
            
            self._add_button = wx.Button( self, id = wx.ID_OK, label = 'Import Files' )
            self._add_button.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Back to File Selection' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            services = wx.GetApp().GetManager( 'services' ).GetServices( ( HC.TAG_REPOSITORY, ) )
            
            for service in services:
                
                account = service.GetInfo( 'account' )
                
                if account.HasPermission( HC.POST_DATA ) or account.IsUnknownAccount():
                    
                    service_key = service.GetServiceKey()
                    
                    page_info = ( self._Panel, ( self._tag_repositories, service_key, paths ), {} )
                    
                    name = service.GetName()
                    
                    self._tag_repositories.AddPage( page_info, name )
                    
                
            
            page = self._Panel( self._tag_repositories, CC.LOCAL_TAG_SERVICE_KEY, paths )
            
            name = CC.LOCAL_TAG_SERVICE_KEY
            
            self._tag_repositories.AddPage( page, name )
            
            default_tag_repository_key = HC.options[ 'default_tag_repository' ]
            
            default_tag_repository = wx.GetApp().GetManager( 'services' ).GetService( default_tag_repository_key )
            
            self._tag_repositories.Select( default_tag_repository.GetName() )
            
        
        def ArrangeControls():
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._add_button, CC.FLAGS_SMALL_INDENT )
            buttons.AddF( self._cancel, CC.FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tag_repositories, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( width, height ) = self.GetMinSize()
            
            width = max( width, 930 )
            height = max( height, 680 )
            
            self.SetInitialSize( ( width, height ) )
            
        
        Dialog.__init__( self, parent, 'path tagging' )
        
        self._paths = paths
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        interested_actions = [ 'set_search_focus' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        wx.CallAfter( self._add_button.SetFocus )
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        page.SetTagBoxFocus()
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'set_search_focus': self._SetSearchFocus()
            else: event.Skip()
            
        
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        wx.CallAfter( page.SetTagBoxFocus )
        
    
    def GetInfo( self ):
        
        paths_to_tags = collections.defaultdict( dict )
        
        for page in self._tag_repositories.GetNameToPageDict().values():
            
            ( service_key, page_of_paths_to_tags ) = page.GetInfo()
            
            for ( path, tags ) in page_of_paths_to_tags.items(): paths_to_tags[ path ][ service_key ] = tags
            
        
        return paths_to_tags
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_key, paths ):
            
            def InitialiseControls():
                
                self._paths_list = ClientGUICommon.SaneListCtrl( self, 250, [ ( '#', 50 ), ( 'path', 400 ), ( 'tags', -1 ) ] )
                
                self._paths_list.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventItemSelected )
                self._paths_list.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventItemSelected )
                
                #
                
                self._quick_namespaces_panel = ClientGUICommon.StaticBox( self, 'quick namespaces' )
                
                self._quick_namespaces_list = ClientGUICommon.SaneListCtrl( self._quick_namespaces_panel, 200, [ ( 'namespace', 80 ), ( 'regex', -1 ) ], delete_key_callback = self.DeleteQuickNamespaces )
                
                self._add_quick_namespace_button = wx.Button( self._quick_namespaces_panel, label = 'add' )
                self._add_quick_namespace_button.Bind( wx.EVT_BUTTON, self.EventAddQuickNamespace )
                self._add_quick_namespace_button.SetMinSize( ( 20, -1 ) )
                
                self._edit_quick_namespace_button = wx.Button( self._quick_namespaces_panel, label = 'edit' )
                self._edit_quick_namespace_button.Bind( wx.EVT_BUTTON, self.EventEditQuickNamespace )
                self._edit_quick_namespace_button.SetMinSize( ( 20, -1 ) )
                
                self._delete_quick_namespace_button = wx.Button( self._quick_namespaces_panel, label = 'delete' )
                self._delete_quick_namespace_button.Bind( wx.EVT_BUTTON, self.EventDeleteQuickNamespace )
                self._delete_quick_namespace_button.SetMinSize( ( 20, -1 ) )
                
                #
                
                self._regexes_panel = ClientGUICommon.StaticBox( self, 'regexes' )
                
                self._regexes = wx.ListBox( self._regexes_panel )
                self._regexes.Bind( wx.EVT_LISTBOX_DCLICK, self.EventRemoveRegex )
                
                self._regex_box = wx.TextCtrl( self._regexes_panel, style=wx.TE_PROCESS_ENTER )
                self._regex_box.Bind( wx.EVT_TEXT_ENTER, self.EventAddRegex )
                
                self._regex_shortcuts = ClientGUICommon.RegexButton( self._regexes_panel )
                
                self._regex_link = wx.HyperlinkCtrl( self._regexes_panel, id = -1, label = 'a good regex introduction', url = 'http://www.aivosto.com/vbtips/regex.html' )
                
                #
                
                self._num_panel = ClientGUICommon.StaticBox( self, '#' )
                
                self._num_base = wx.SpinCtrl( self._num_panel, min = -10000000, max = 10000000, size = ( 60, -1 ) )
                self._num_base.SetValue( 1 )
                self._num_base.Bind( wx.EVT_SPINCTRL, self.EventRecalcNum )
                
                self._num_step = wx.SpinCtrl( self._num_panel, min = -1000000, max = 1000000, size = ( 60, -1 ) )
                self._num_step.SetValue( 1 )
                self._num_step.Bind( wx.EVT_SPINCTRL, self.EventRecalcNum )
                
                self._num_namespace = wx.TextCtrl( self._num_panel, size = ( 100, -1 ) )
                self._num_namespace.Bind( wx.EVT_TEXT, self.EventNumNamespaceChanged )
                
                #
                
                self._tags_panel = ClientGUICommon.StaticBox( self, 'tags for all' )
                
                self._tags = ClientGUICommon.ListBoxTagsStrings( self._tags_panel, self.TagRemoved )
                
                self._tag_box = ClientGUICommon.AutoCompleteDropdownTagsWrite( self._tags_panel, self.AddTag, CC.LOCAL_FILE_SERVICE_KEY, service_key )
                
                #
                
                self._single_tags_panel = ClientGUICommon.StaticBox( self, 'tags just for this file' )
                
                self._paths_to_single_tags = collections.defaultdict( list )
                
                self._single_tags = ClientGUICommon.ListBoxTagsStrings( self._single_tags_panel, self.SingleTagRemoved )
                
                self._single_tag_box = ClientGUICommon.AutoCompleteDropdownTagsWrite( self._single_tags_panel, self.AddTagSingle, CC.LOCAL_FILE_SERVICE_KEY, service_key )
                
            
            def PopulateControls():
                
                num_base = self._num_base.GetValue()
                num_step = self._num_step.GetValue()
                
                for ( num, path ) in enumerate( self._paths ):
                    
                    processed_num = num_base + num * num_step
                    
                    pretty_num = HydrusData.ConvertIntToPrettyString( processed_num )
                    
                    tags = self._GetTags( num, path )
                    
                    tags_string = ', '.join( tags )
                    
                    self._paths_list.Append( ( pretty_num, path, tags_string ), ( ( num, processed_num ), path, tags ) )
                    
                
                self._single_tag_box.Disable()
                
            
            def ArrangeControls():
                
                button_box = wx.BoxSizer( wx.HORIZONTAL )
                
                button_box.AddF( self._add_quick_namespace_button, CC.FLAGS_EXPAND_BOTH_WAYS )
                button_box.AddF( self._edit_quick_namespace_button, CC.FLAGS_EXPAND_BOTH_WAYS )
                button_box.AddF( self._delete_quick_namespace_button, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                self._quick_namespaces_panel.AddF( self._quick_namespaces_list, CC.FLAGS_EXPAND_BOTH_WAYS )
                self._quick_namespaces_panel.AddF( button_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                #
                
                self._regexes_panel.AddF( self._regexes, CC.FLAGS_EXPAND_BOTH_WAYS )
                self._regexes_panel.AddF( self._regex_box, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._regexes_panel.AddF( self._regex_shortcuts, CC.FLAGS_LONE_BUTTON )
                self._regexes_panel.AddF( self._regex_link, CC.FLAGS_LONE_BUTTON )
                
                #
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self._num_panel, label = '# base/step: ' ), CC.FLAGS_MIXED )
                hbox.AddF( self._num_base, CC.FLAGS_MIXED )
                hbox.AddF( self._num_step, CC.FLAGS_MIXED )
                
                self._num_panel.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self._num_panel, label = '# namespace: ' ), CC.FLAGS_MIXED )
                hbox.AddF( self._num_namespace, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                self._num_panel.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                second_vbox = wx.BoxSizer( wx.VERTICAL )
                
                second_vbox.AddF( self._regexes_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                second_vbox.AddF( self._num_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                #
                
                self._tags_panel.AddF( self._tags, CC.FLAGS_EXPAND_BOTH_WAYS )
                self._tags_panel.AddF( self._tag_box, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                self._single_tags_panel.AddF( self._single_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
                self._single_tags_panel.AddF( self._single_tag_box, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( self._quick_namespaces_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                hbox.AddF( second_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
                hbox.AddF( self._tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                hbox.AddF( self._single_tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.AddF( self._paths_list, CC.FLAGS_EXPAND_BOTH_WAYS )
                vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
                
                self.SetSizer( vbox )
                
            
            wx.Panel.__init__( self, parent )
            
            self._service_key = service_key
            self._paths = paths
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
            
        
        
        def _GetTags( self, num, path ):
            
            tags = []
            
            tags.extend( self._tags.GetTags() )
            
            for regex in self._regexes.GetStrings():
                
                try:
                    
                    result = re.findall( regex, path )
                    
                    for match in result: tags.append( match )
                    
                except: pass
                
            
            for ( namespace, regex ) in self._quick_namespaces_list.GetClientData():
                
                try:
                    
                    result = re.findall( regex, path )
                    
                    for match in result: tags.append( namespace + ':' + match )
                    
                except: pass
                
            
            if path in self._paths_to_single_tags: tags.extend( self._paths_to_single_tags[ path ] )
            
            num_namespace = self._num_namespace.GetValue()
            
            if num_namespace != '':
                
                tags.append( num_namespace + ':' + HydrusData.ToString( num ) )
                
            
            tags = HydrusTags.CleanTags( tags )
            
            tags = list( tags )
            
            tags.sort()
            
            return tags
            
        
        def _RefreshFileList( self ):
            
            for ( index, ( ( original_num, processed_num ), path, old_tags ) ) in enumerate( self._paths_list.GetClientData() ):
                
                # when doing regexes, make sure not to include '' results, same for system: and - started tags.
                
                tags = self._GetTags( processed_num, path )
                
                if tags != old_tags:
                    
                    pretty_num = HydrusData.ConvertIntToPrettyString( processed_num )
                    
                    tags_string = ', '.join( tags )
                    
                    self._paths_list.UpdateRow( index, ( pretty_num, path, tags_string ), ( ( original_num, processed_num ), path, tags ) )
                    
                
            
        
        def AddTag( self, tag, parents = None ):
            
            if parents is None: parents = []
            
            if tag is not None:
                
                self._tags.AddTag( tag, parents )
                
                self._RefreshFileList()
                
            
        
        def AddTagSingle( self, tag, parents = None ):
            
            if parents is None: parents = []
            
            if tag is not None:
                
                self._single_tags.AddTag( tag, parents )
                
                indices = self._paths_list.GetAllSelected()
                
                for index in indices:
                    
                    ( ( original_num, processed_num ), path, old_tags ) = self._paths_list.GetClientData( index )
                    
                    if tag in self._paths_to_single_tags[ path ]: self._paths_to_single_tags[ path ].remove( tag )
                    else:
                        
                        self._paths_to_single_tags[ path ].append( tag )
                        
                        for parent in parents:
                            
                            if parent not in self._paths_to_single_tags[ path ]: self._paths_to_single_tags[ path ].append( parent )
                            
                        
                    
                
                self._RefreshFileList()
                
            
        
        def DeleteQuickNamespaces( self ):
            
            self._quick_namespaces_list.RemoveAllSelected()
            
            self._RefreshFileList()
            
        
        def EventAddRegex( self, event ):
            
            regex = self._regex_box.GetValue()
            
            if regex != '':
                
                self._regexes.Append( regex )
                
                self._regex_box.Clear()
                
                self._RefreshFileList()
                
            
        
        def EventAddQuickNamespace( self, event ):
            
            with DialogInputNamespaceRegex( self ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( namespace, regex ) = dlg.GetInfo()
                    
                    self._quick_namespaces_list.Append( ( namespace, regex ), ( namespace, regex ) )
                    
                    self._RefreshFileList()
                    
                
            
        
        def EventDeleteQuickNamespace( self, event ): self.DeleteQuickNamespaces()
        
        def EventEditQuickNamespace( self, event ):
            
            for index in self._quick_namespaces_list.GetAllSelected():
                
                ( namespace, regex ) = self._quick_namespaces_list.GetClientData( index = index )
                
                with DialogInputNamespaceRegex( self, namespace = namespace, regex = regex ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        ( namespace, regex ) = dlg.GetInfo()
                        
                        self._quick_namespaces_list.UpdateRow( index, ( namespace, regex ), ( namespace, regex ) )
                        
                    
                
            
            self._RefreshFileList()
            
        
        def EventItemSelected( self, event ):
            
            single_tags = set()
            
            indices = self._paths_list.GetAllSelected()
            
            if len( indices ) > 0:
                
                for index in indices:
                    
                    path = self._paths_list.GetClientData( index )[1]
                    
                    if path in self._paths_to_single_tags: single_tags.update( self._paths_to_single_tags[ path ] )
                    
                
                self._single_tag_box.Enable()
                
            else: self._single_tag_box.Disable()
            
            self._single_tags.SetTags( single_tags )
            
        
        def EventNumNamespaceChanged( self, event ): self._RefreshFileList()
        
        def EventRecalcNum( self, event ):
            
            num_base = self._num_base.GetValue()
            num_step = self._num_step.GetValue()
            
            for ( index, ( ( original_num, processed_num ), path, tags ) ) in enumerate( self._paths_list.GetClientData() ):
                
                processed_num = num_base + original_num * num_step
                
                pretty_num = HydrusData.ConvertIntToPrettyString( processed_num )
                
                tags_string = ', '.join( tags )
                
                self._paths_list.UpdateRow( index, ( pretty_num, path, tags_string ), ( ( original_num, processed_num ), path, tags ) )
                
            
        
        def EventRemoveRegex( self, event ):
            
            selection = self._regexes.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                if len( self._regex_box.GetValue() ) == 0: self._regex_box.SetValue( self._regexes.GetString( selection ) )
                
                self._regexes.Delete( selection )
                
                self._RefreshFileList()
                
            
        
        def GetInfo( self ):
            
            paths_to_tags = { path : tags for ( ( original_num, processed_num ), path, tags ) in self._paths_list.GetClientData() }
            
            return ( self._service_key, paths_to_tags )
            
        
        def SetTagBoxFocus( self ): self._tag_box.SetFocus()
        
        def SingleTagRemoved( self, tag ):
            
            indices = self._paths_list.GetAllSelected()
            
            for index in indices:
                
                ( ( original_num, processed_num ), path, old_tags ) = self._paths_list.GetClientData( index )
                
                if tag in self._paths_to_single_tags[ path ]: self._paths_to_single_tags[ path ].remove( tag )
                
            
            self._RefreshFileList()
            
        
        def TagRemoved( self, tag ): self._RefreshFileList()
        
    
class DialogRegisterService( Dialog ):
    
    def __init__( self, parent, service_type ):
        
        def InitialiseControls():
            
            self._address = wx.TextCtrl( self )
            self._registration_key = wx.TextCtrl( self )
            
            self._register_button = wx.Button( self, label = 'register' )
            self._register_button.Bind( wx.EVT_BUTTON, self.EventRegister )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            
        
        def PopulateControls():
            
            self._address.SetValue( 'hostname:port' )
            self._registration_key.SetValue( 'r0000000000000000000000000000000000000000000000000000000000000000' )
            
        
        def ArrangeControls():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( wx.StaticText( self, label = 'Please fill out the forms with the appropriate information for your service.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            gridbox = wx.FlexGridSizer( 0, 2 )
            
            gridbox.AddGrowableCol( 1, 1 )
            
            gridbox.AddF( wx.StaticText( self, label = 'address' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._address, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            gridbox.AddF( wx.StaticText( self, label = 'registration key' ), CC.FLAGS_MIXED )
            gridbox.AddF( self._registration_key, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            buttonbox = wx.BoxSizer( wx.HORIZONTAL )
            
            buttonbox.AddF( self._register_button, CC.FLAGS_MIXED )
            buttonbox.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox.AddF( buttonbox, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'register account', position = 'center' )
        
        self._service_type = service_type
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self._register = False
        
        wx.CallAfter( self._register_button.SetFocus )
        
    
    def EventRegister( self, event ):
        
        address = self._address.GetValue()
        
        try:
            
            ( host, port ) = address.split( ':' )
            
            port = int( port )
            
        except:
            
            wx.MessageBox( 'Could not parse that address!' )
            
            return
            
        
        registration_key_encoded = self._registration_key.GetValue()
        
        if registration_key_encoded[0] == 'r': registration_key_encoded = registration_key_encoded[1:]
        
        try: registration_key = registration_key_encoded.decode( 'hex' )
        except:
            
            wx.MessageBox( 'Could not parse that registration key!' )
            
            return
            
        
        service_key = os.urandom( 32 )
        name = 'temp registering service'
        
        info = { 'host' : host, 'port' : port }
        
        service = ClientData.Service( service_key, self._service_type, name, info )
        
        response = service.Request( HC.GET, 'access_key', request_headers = { 'Hydrus-Key' : registration_key_encoded } )
        
        access_key = response[ 'access_key' ]
        
        self._credentials = ClientData.Credentials( host, port, access_key )
        
        self.EndModal( wx.ID_OK )
        
    
    def GetCredentials( self ): return self._credentials
    
class DialogSelectBooru( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
            
            self._boorus = wx.ListBox( self, style = wx.LB_SORT )
            self._boorus.Bind( wx.EVT_LISTBOX_DCLICK, self.EventDoubleClick )
            
            self._ok = wx.Button( self, id = wx.ID_OK, size = ( 0, 0 ) )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetDefault()
            
    
        def PopulateControls():
            
            boorus = wx.GetApp().Read( 'remote_boorus' )
            
            for ( name, booru ) in boorus.items(): self._boorus.Append( name, booru )
            
        
        def ArrangeControls():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._boorus, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 320: x = 320
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'select booru' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventDoubleClick( self, event ): self.EndModal( wx.ID_OK )
    
    def EventOK( self, event ):
    
        selection = self._boorus.GetSelection()
        
        if selection != wx.NOT_FOUND: self.EndModal( wx.ID_OK )
        
    
    def GetBooru( self ): return self._boorus.GetClientData( self._boorus.GetSelection() )
    
class DialogSelectImageboard( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
            
            self._tree = wx.TreeCtrl( self )
            self._tree.Bind( wx.EVT_TREE_ITEM_ACTIVATED, self.EventActivate )
            
        
        def PopulateControls():
            
            all_imageboards = wx.GetApp().Read( 'imageboards' )
            
            root_item = self._tree.AddRoot( 'all sites' )
            
            for ( site, imageboards ) in all_imageboards.items():
                
                site_item = self._tree.AppendItem( root_item, site )
                
                for imageboard in imageboards:
                    
                    name = imageboard.GetName()
                    
                    self._tree.AppendItem( site_item, name, data = wx.TreeItemData( imageboard ) )
                    
                
            
            self._tree.Expand( root_item )
            
        
        def ArrangeControls():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tree, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 320: x = 320
            if y < 640: y = 640
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'select imageboard' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
    
    def EventActivate( self, event ):
        
        item = self._tree.GetSelection()
        
        data_object = self._tree.GetItemData( item )
        
        if data_object is None: self._tree.Toggle( item )
        else: self.EndModal( wx.ID_OK )
        
    
    def GetImageboard( self ): return self._tree.GetItemData( self._tree.GetSelection() ).GetData()
    
class DialogCheckFromListOfStrings( Dialog ):
    
    def __init__( self, parent, title, list_of_strings, checked_strings = None ):
        
        if checked_strings is None: checked_strings = []
        
        def InitialiseControls():
            
            self._strings = wx.CheckListBox( self )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            
    
        def PopulateControls():
            
            for s in list_of_strings: self._strings.Append( s )
            
            for s in checked_strings:
                
                i = self._strings.FindString( s )
                
                if i != wx.NOT_FOUND: self._strings.Check( i, True )
                
            
        
        def ArrangeControls():
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._ok, CC.FLAGS_MIXED )
            hbox.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._strings, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( hbox, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 320: x = 320
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, title )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
    
    def GetChecked( self ): return self._strings.GetCheckedStrings()
    
class DialogSelectFromListOfStrings( Dialog ):
    
    def __init__( self, parent, title, list_of_strings ):
        
        def InitialiseControls():
            
            self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
            
            self._strings = wx.ListBox( self )
            self._strings.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
            self._strings.Bind( wx.EVT_LISTBOX_DCLICK, self.EventSelect )
            
            self._ok = wx.Button( self, id = wx.ID_OK, size = ( 0, 0 ) )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetDefault()
            
    
        def PopulateControls():
            
            for s in list_of_strings: self._strings.Append( s )
            
        
        def ArrangeControls():
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._strings, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 320: x = 320
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, title )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode == wx.WXK_SPACE:
            
            selection = self._strings.GetSelection()
            
            if selection != wx.NOT_FOUND: self.EndModal( wx.ID_OK )
            
        else: event.Skip()
        
    
    def EventOK( self, event ):
        
        selection = self._strings.GetSelection()
        
        if selection != wx.NOT_FOUND: self.EndModal( wx.ID_OK )
        
    
    def EventSelect( self, event ): self.EndModal( wx.ID_OK )
    
    def GetString( self ): return self._strings.GetStringSelection()
    
class DialogSelectYoutubeURL( Dialog ):
    
    def __init__( self, parent, info ):
        
        def InitialiseControls():
            
            self._urls = ClientGUICommon.SaneListCtrl( self, 360, [ ( 'format', 150 ), ( 'resolution', 150 ) ] )
            self._urls.Bind( wx.EVT_LIST_ITEM_ACTIVATED, self.EventOK )
            
            self._urls.SetMinSize( ( 360, 200 ) )
            
            self._ok = wx.Button( self, wx.ID_OK, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            for ( extension, resolution ) in self._info: self._urls.Append( ( extension, resolution ), ( extension, resolution ) )
            
            self._urls.SortListItems( 0 )
            
        
        def ArrangeControls():
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._ok, CC.FLAGS_MIXED )
            buttons.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._urls, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'choose youtube format' )
        
        self._info = info
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventOK( self, event ):
        
        indices = self._urls.GetAllSelected()
        
        if len( indices ) > 0:
            
            for index in indices:
                
                ( extension, resolution ) = self._urls.GetClientData( index )
                
                ( url, title ) = self._info[ ( extension, resolution ) ]
                
                url_string = title + ' ' + resolution + ' ' + extension
                
                job_key = HydrusData.JobKey( pausable = True, cancellable = True )
                
                HydrusThreading.CallToThread( ClientDownloading.THREADDownloadURL, job_key, url, url_string )
                
                HydrusGlobals.pubsub.pub( 'message', job_key )
                
            
        
        self.EndModal( wx.ID_OK )
        
    
class DialogSetupCustomFilterActions( Dialog ):
    
    def __init__( self, parent ):
        
        def InitialiseControls():
            
            self._actions = ClientGUICommon.SaneListCtrl( self, 120, [ ( 'modifier', 150 ), ( 'key', 150 ), ( 'service', -1 ), ( 'action', 250 ) ], delete_key_callback = self.RemoveActions )
            
            self._favourites = wx.ListBox( self )
            self._favourites.Bind( wx.EVT_LISTBOX, self.EventSelectFavourite )
            
            self._save_favourite = wx.Button( self, label = 'save' )
            self._save_favourite.Bind( wx.EVT_BUTTON, self.EventSaveFavourite )
            
            self._save_new_favourite = wx.Button( self, label = 'save as' )
            self._save_new_favourite.Bind( wx.EVT_BUTTON, self.EventSaveNewFavourite )
            
            self._delete_favourite = wx.Button( self, label = 'delete' )
            self._delete_favourite.Bind( wx.EVT_BUTTON, self.EventDeleteFavourite )
            
            self._current_actions_selection = wx.NOT_FOUND
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            self._add.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._edit = wx.Button( self, label = 'edit' )
            self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
            
            self._remove = wx.Button( self, label = 'remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
        
        def PopulateControls():
            
            default_actions = self._GetDefaultActions()
            
            self._favourites.Append( 'default', default_actions )
            
            favourites = wx.GetApp().Read( 'favourite_custom_filter_actions' )
            
            self._initial_favourite_names = favourites.keys()
            
            if 'previous' in favourites: self._favourites.Append( 'previous', favourites[ 'previous' ] )
            else: self._favourites.Append( 'previous', default_actions )
            
            for ( name, actions ) in favourites.items():
                
                if name != 'previous': self._favourites.Append( name, actions )
                
            
            self._favourites.Select( 1 ) # previous
            
        
        def ArrangeControls():
            
            action_buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            action_buttons.AddF( self._add, CC.FLAGS_MIXED )
            action_buttons.AddF( self._edit, CC.FLAGS_MIXED )
            action_buttons.AddF( self._remove, CC.FLAGS_MIXED )
            
            buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            buttons.AddF( self._ok, CC.FLAGS_MIXED )
            buttons.AddF( self._cancel, CC.FLAGS_MIXED )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._actions, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( action_buttons, CC.FLAGS_BUTTON_SIZER )
            vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
            
            button_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            button_hbox.AddF( self._save_favourite, CC.FLAGS_MIXED )
            button_hbox.AddF( self._save_new_favourite, CC.FLAGS_MIXED )
            button_hbox.AddF( self._delete_favourite, CC.FLAGS_MIXED )
            
            f_vbox = wx.BoxSizer( wx.VERTICAL )
            
            f_vbox.AddF( self._favourites, CC.FLAGS_EXPAND_BOTH_WAYS )
            f_vbox.AddF( button_hbox, CC.FLAGS_BUTTON_SIZER )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( f_vbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            hbox.AddF( vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            self.SetSizer( hbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 780: x = 780
            if y < 480: y = 480
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'setup custom filter' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self.EventSelectFavourite, None )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _GetDefaultActions( self ):
        
        default_actions = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items():
            
            for ( key, action ) in key_dict.items():
                
                if action in ( 'manage_tags', 'manage_ratings', 'archive', 'inbox', 'fullscreen_switch', 'frame_back', 'frame_next', 'previous', 'next', 'first', 'last', 'pan_up', 'pan_down', 'pan_left', 'pan_right', 'open_externally' ):
                    
                    service_key = None
                    
                    default_actions.append( ( modifier, key, service_key, action ) )
                    
                
            
        
        ( modifier, key, service_key, action ) = ( wx.ACCEL_NORMAL, wx.WXK_DELETE, None, 'delete' )
        
        default_actions.append( ( modifier, key, service_key, action ) )
        
        return default_actions
        
    
    def _IsUntouchableFavouriteSelection( self, selection ):
        
        name = self._favourites.GetString( selection )
        
        if name in ( 'previous', 'default' ): return True
        else: return False
        
    
    def _SortListCtrl( self ): self._actions.SortListItems( 3 )
    
    def EventAdd( self, event ):
        
        with DialogInputCustomFilterAction( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                ( pretty_tuple, data_tuple ) = dlg.GetInfo()
                
                self._actions.Append( pretty_tuple, data_tuple )
                
                self._SortListCtrl()
                
            
        
    
    def EventDeleteFavourite( self, event ):
        
        selection = self._favourites.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if not self._IsUntouchableFavouriteSelection( selection ):
                
                self._favourites.Delete( selection )
                
            
        
    
    def EventEdit( self, event ):
        
        for index in self._actions.GetAllSelected():
            
            ( modifier, key, service_key, action ) = self._actions.GetClientData( index )
            
            with DialogInputCustomFilterAction( self, modifier = modifier, key = key, service_key = service_key, action = action ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( pretty_tuple, data_tuple ) = dlg.GetInfo()
                    
                    self._actions.UpdateRow( index, pretty_tuple, data_tuple )
                    
                    self._SortListCtrl()
                    
                
            
        
    
    def EventOK( self, event ):
        
        favourites = {}
        
        for i in range( self._favourites.GetCount() ):
            
            name = self._favourites.GetString( i )
            
            if name == 'default': continue
            
            actions = self._favourites.GetClientData( i )
            
            favourites[ name ] = actions
            
        
        favourites[ 'previous' ] = self._actions.GetClientData() # overwrite
        
        deletees = set( self._initial_favourite_names ) - set( favourites.keys() )
        
        for deletee in deletees: wx.GetApp().Write( 'delete_favourite_custom_filter_actions', deletee )
        
        for ( name, actions ) in favourites.items(): wx.GetApp().Write( 'favourite_custom_filter_actions', name, actions )
        
        self.EndModal( wx.ID_OK )
        
    
    def EventRemove( self, event ): self.RemoveActions()
    
    def EventSaveFavourite( self, event ):
        
        selection = self._favourites.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if not self._IsUntouchableFavouriteSelection( selection ):
                
                actions = self._actions.GetClientData()
                
                self._favourites.SetClientData( selection, actions )
                
            
        
    
    def EventSaveNewFavourite( self, event ):
        
        existing_names = { self._favourites.GetString( i ) for i in range( self._favourites.GetCount() ) }
        
        with DialogTextEntry( self, 'Enter name for these favourite actions.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                name = dlg.GetValue()
                
                if name == '': return
                
                while name in existing_names: name += HydrusData.ToString( random.randint( 0, 9 ) )
                
                actions = self._actions.GetClientData()
                
                self._favourites.Append( name, actions )
                
            
        
    
    def EventSelectFavourite( self, event ):
        
        selection = self._favourites.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            if selection != self._current_actions_selection:
                
                self._actions.DeleteAllItems()
                
                name = self._favourites.GetString( selection )
                
                if name in ( 'default', 'previous' ):
                    
                    self._save_favourite.Disable()
                    self._delete_favourite.Disable()
                    
                else:
                    
                    self._save_favourite.Enable()
                    self._delete_favourite.Enable()
                    
                
                actions = self._favourites.GetClientData( selection )
                
                for ( modifier, key, service_key, action ) in actions:
                    
                    ( pretty_modifier, pretty_key, pretty_action ) = HydrusData.ConvertShortcutToPrettyShortcut( modifier, key, action )
                    
                    if service_key is None: pretty_service_key = ''
                    else:
                        
                        if type( service_key ) == ClientData.ClientServiceIdentifier: service_key = service_key.GetServiceKey()
                        
                        service = wx.GetApp().GetManager( 'services' ).GetService( service_key )
                        
                        pretty_service_key = service.GetName()
                        
                    
                    self._actions.Append( ( pretty_modifier, pretty_key, pretty_service_key, pretty_action ), ( modifier, key, service_key, action ) )
                    
                
                self._SortListCtrl()
                
            
        
    
    def GetActions( self ):
        
        raw_data = self._actions.GetClientData()
        
        actions = collections.defaultdict( dict )
        
        for ( modifier, key, service_key, action ) in raw_data: actions[ modifier ][ key ] = ( service_key, action )
        
        return actions
        
    
    def RemoveActions( self ): self._actions.RemoveAllSelected()
    
class DialogSetupExport( Dialog ):
    
    def __init__( self, parent, flat_media ):
        
        def InitialiseControls():
            
            self._tags_box = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'files\' tags' )
            
            t = ClientGUICommon.ListBoxTagsSelection( self._tags_box, collapse_siblings = True )
            
            self._tags_box.SetTagsBox( t )
            
            self._tags_box.SetMinSize( ( 220, 300 ) )
            
            self._paths = ClientGUICommon.SaneListCtrl( self, 120, [ ( 'number', 60 ), ( 'mime', 70 ), ( 'expected path', -1 ) ], delete_key_callback = self.DeletePaths )
            self._paths.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventSelectPath )
            self._paths.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventSelectPath )
            
            self._export_path_box = ClientGUICommon.StaticBox( self, 'export path' )
            
            self._directory_picker = wx.DirPickerCtrl( self._export_path_box )
            self._directory_picker.Bind( wx.EVT_DIRPICKER_CHANGED, self.EventRecalcPaths )
            
            self._open_location = wx.Button( self._export_path_box, label = 'open this location' )
            self._open_location.Bind( wx.EVT_BUTTON, self.EventOpenLocation )
            
            self._zip_box = ClientGUICommon.StaticBox( self, 'zip' )
            
            self._export_to_zip = wx.CheckBox( self._zip_box, label = 'export to zip' )
            self._export_to_zip.Bind( wx.EVT_CHECKBOX, self.EventExportToZipCheckbox )
            
            self._zip_name = wx.TextCtrl( self._zip_box )
            self._zip_name.Disable()
            
            self._export_encrypted = wx.CheckBox( self._zip_box, label = 'encrypt zip' )
            self._export_encrypted.Disable()
            
            self._filenames_box = ClientGUICommon.StaticBox( self, 'filenames' )
            
            self._pattern = wx.TextCtrl( self._filenames_box )
            
            self._update = wx.Button( self._filenames_box, label = 'update' )
            self._update.Bind( wx.EVT_BUTTON, self.EventRecalcPaths )
            
            self._examples = ClientGUICommon.ExportPatternButton( self._filenames_box )
            
            self._export = wx.Button( self, label = 'export' )
            self._export.Bind( wx.EVT_BUTTON, self.EventExport )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'close' )
            
    
        def PopulateControls():
            
            for ( i, media ) in enumerate( flat_media ):
                
                mime = media.GetMime()
                
                pretty_tuple = ( HydrusData.ToString( i + 1 ), HC.mime_string_lookup[ mime ], '' )
                data_tuple = ( ( i, media ), mime, '' )
                
                self._paths.Append( pretty_tuple, data_tuple )
                
            
            if HC.options[ 'export_path' ] is not None:
                
                abs_path = HydrusData.ConvertPortablePathToAbsPath( HC.options[ 'export_path' ] )
                
                if abs_path is not None: self._directory_picker.SetPath( abs_path )
                
            
            self._zip_name.SetValue( 'archive name.zip' )
            
            self._pattern.SetValue( '{hash}' )
            
        
        def ArrangeControls():
            
            top_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            top_hbox.AddF( self._tags_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            top_hbox.AddF( self._paths, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._directory_picker, CC.FLAGS_EXPAND_BOTH_WAYS )
            hbox.AddF( self._open_location, CC.FLAGS_MIXED )
            
            self._export_path_box.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._pattern, CC.FLAGS_EXPAND_BOTH_WAYS )
            hbox.AddF( self._update, CC.FLAGS_MIXED )
            hbox.AddF( self._examples, CC.FLAGS_MIXED )
            
            self._filenames_box.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._export_to_zip, CC.FLAGS_MIXED )
            hbox.AddF( self._zip_name, CC.FLAGS_EXPAND_BOTH_WAYS )
            hbox.AddF( self._export_encrypted, CC.FLAGS_MIXED )
            
            self._zip_box.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( top_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            vbox.AddF( self._export_path_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._filenames_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._zip_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._export, CC.FLAGS_LONE_BUTTON )
            vbox.AddF( self._cancel, CC.FLAGS_LONE_BUTTON )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            if x < 780: x = 780
            if y < 480: y = 480
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'setup export' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        wx.CallAfter( self.EventSelectPath, None )
        wx.CallAfter( self.EventRecalcPaths, None )
        
        wx.CallAfter( self._export.SetFocus )
        
    
    def _GetPath( self, media, terms ):
        
        directory = self._directory_picker.GetPath()
        
        filename = ClientData.GenerateExportFilename( media, terms )
        
        if self._export_to_zip.GetValue() == True: zip_path = self._zip_name.GetValue() + os.path.sep
        else: zip_path = ''
        
        mime = media.GetMime()
        
        ext = HC.mime_ext_lookup[ mime ]
        
        return directory + os.path.sep + zip_path + filename + ext
        
    
    def _RecalcPaths( self ):
        
        pattern = self._pattern.GetValue()
        
        terms = ClientData.ParseExportPhrase( pattern )
        
        all_paths = set()
        
        for ( index, ( ( ordering_index, media ), mime, old_path ) ) in enumerate( self._paths.GetClientData() ):
            
            path = self._GetPath( media, terms )
            
            if path in all_paths:
                
                i = 1
                
                while self._GetPath( media, terms + [ ( 'string', HydrusData.ToString( i ) ) ] ) in all_paths: i += 1
                
                path = self._GetPath( media, terms + [ ( 'string', HydrusData.ToString( i ) ) ] )
                
            
            all_paths.add( path )
            
            if path != old_path:
                
                mime = media.GetMime()
                
                self._paths.UpdateRow( index, ( HydrusData.ToString( ordering_index + 1 ), HC.mime_string_lookup[ mime ], path ), ( ( ordering_index, media ), mime, path ) )
                
            
        
    
    def DeletePaths( self ):
        
        self._paths.RemoveAllSelected()
        
        self._RecalcPaths()
        
    
    def EventExport( self, event ):
        
        self._RecalcPaths()
        
        if self._export_to_zip.GetValue() == True:
            
            directory = self._directory_picker.GetPath()
            
            zip_path = directory + os.path.sep + self._zip_name.GetValue()
            
            with zipfile.ZipFile( zip_path, mode = 'w', compression = zipfile.ZIP_DEFLATED ) as z:
                
                for ( ( ordering_index, media ), mime, path ) in self._paths.GetClientData():
                    
                    try:
                        
                        hash = media.GetHash()
                        
                        source_path = ClientFiles.GetFilePath( hash, mime )
                        
                        ( gumpf, filename ) = os.path.split( path )
                        
                        z.write( source_path, filename )
                        
                    except:
                        
                        wx.MessageBox( 'Encountered a problem while attempting to export file with index ' + HydrusData.ToString( ordering_index + 1 ) + '.' + os.linesep * 2 + traceback.format_exc() )
                        
                        break
                        
                    
                
            
            if self._export_encrypted.GetValue() == True: HydrusEncryption.EncryptAESFile( zip_path, preface = 'hydrus encrypted zip' )
            
        else:
            
            for ( ( ordering_index, media ), mime, path ) in self._paths.GetClientData():
                
                try:
                    
                    hash = media.GetHash()
                    
                    source_path = ClientFiles.GetFilePath( hash, mime )
                    
                    if os.path.exists( path ): os.chmod( path, stat.S_IWRITE )
                    
                    shutil.copy( source_path, path )
                    
                except:
                    
                    wx.MessageBox( 'Encountered a problem while attempting to export file with index ' + HydrusData.ToString( ordering_index + 1 ) + ':' + os.linesep * 2 + traceback.format_exc() )
                    
                    break
                    
                
            
        
    
    def EventExportToZipCheckbox( self, event ):
        
        if self._export_to_zip.GetValue() == True:
            
            self._zip_name.Enable()
            self._export_encrypted.Enable()
            
        else:
            
            self._zip_name.Disable()
            self._export_encrypted.Disable()
            
        
    
    def EventOpenLocation( self, event ):
        
        directory = self._directory_picker.GetPath()
        
        if directory is not None and directory != '':
            
            try:
                
                HydrusFileHandling.LaunchDirectory( directory )
                
            except: wx.MessageBox( 'Could not open that location!' )
        
    
    def EventRecalcPaths( self, event ): self._RecalcPaths()
    
    def EventSelectPath( self, event ):
        
        indices = self._paths.GetAllSelected()
        
        if len( indices ) == 0:
            
            all_media = [ media for ( ( ordering_index, media ), mime, old_path ) in self._paths.GetClientData() ]
            
        else:
            
            all_media = [ media for ( ( ordering_index, media ), mime, old_path ) in [ self._paths.GetClientData( index ) for index in indices ] ]
            
        
        self._tags_box.SetTagsByMedia( all_media )
        
    
class DialogTextEntry( Dialog ):
    
    def __init__( self, parent, message, default = '', allow_blank = False ):
        
        def InitialiseControls():
            
            self._text = wx.TextCtrl( self, style = wx.TE_PROCESS_ENTER )
            self._text.Bind( wx.EVT_CHAR, self.EventChar )
            self._text.Bind( wx.EVT_TEXT_ENTER, self.EventEnter )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
            self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
            
    
        def PopulateControls():
            
            self._text.SetValue( default )
            
            self._CheckText()
            
        
        def ArrangeControls():
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._ok, CC.FLAGS_SMALL_INDENT )
            hbox.AddF( self._cancel, CC.FLAGS_SMALL_INDENT )
            
            st_message = wx.StaticText( self, label = message )
            
            st_message.Wrap( 480 )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( st_message, CC.FLAGS_BIG_INDENT )
            vbox.AddF( self._text, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( hbox, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            x = max( x, 250 )
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, 'enter text', position = 'center' )
        
        self._allow_blank = allow_blank
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
    
    def _CheckText( self ):
        
        if not self._allow_blank:
            
            if self._text.GetValue() == '': self._ok.Disable()
            else: self._ok.Enable()
            
        
    
    def EventChar( self, event ):
        
        wx.CallAfter( self._CheckText )
        
        event.Skip()
        
    
    def EventEnter( self, event ):
        
        if self._text.GetValue() != '': self.EndModal( wx.ID_OK )
        
    
    def GetValue( self ): return self._text.GetValue()
    
class DialogYesNo( Dialog ):
    
    def __init__( self, parent, message, title = 'Are you sure?', yes_label = 'yes', no_label = 'no' ):
        
        def InitialiseControls():
            
            self._yes = wx.Button( self, id = wx.ID_YES, label = yes_label )
            self._yes.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._no = wx.Button( self, id = wx.ID_NO, label = no_label )
            self._no.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
            
    
        def PopulateControls():
            
            pass
            
        
        def ArrangeControls():
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._yes, CC.FLAGS_SMALL_INDENT )
            hbox.AddF( self._no, CC.FLAGS_SMALL_INDENT )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            text = wx.StaticText( self, label = message )
            
            text.Wrap( 480 )
            
            vbox.AddF( text, CC.FLAGS_BIG_INDENT )
            vbox.AddF( hbox, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            ( x, y ) = self.GetEffectiveMinSize()
            
            self.SetInitialSize( ( x, y ) )
            
        
        Dialog.__init__( self, parent, title, position = 'center' )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
        wx.CallAfter( self._yes.SetFocus )
        
    
    def EventCharHook( self, event ):
        
        if event.KeyCode == wx.WXK_ESCAPE: self.EndModal( wx.ID_NO )
        else: event.Skip()
        
    