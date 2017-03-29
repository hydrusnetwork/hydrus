import HydrusConstants as HC
import ClientConstants as CC
import ClientData
import ClientDefaults
import ClientDownloading
import ClientDragDrop
import ClientExporting
import ClientCaches
import ClientFiles
import ClientGUIACDropdown
import ClientGUIFrames
import ClientGUICommon
import ClientGUICollapsible
import ClientGUIListBoxes
import ClientGUIPredicates
import ClientGUITopLevelWindows
import ClientThreading
import collections
import gc
import HydrusExceptions
import HydrusFileHandling
import HydrusNATPunch
import HydrusNetwork
import HydrusPaths
import HydrusSerialisable
import HydrusTagArchive
import HydrusTags
import HydrusThreading
import itertools
import os
import random
import re
import Queue
import shutil
import stat
import string
import threading
import time
import traceback
import urllib
import wx
import wx.lib.agw.customtreectrl
import yaml
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

def ExportToHTA( parent, service_key, hashes ):
    
    with wx.FileDialog( parent, style = wx.FD_SAVE, defaultFile = 'archive.db' ) as dlg:
        
        if dlg.ShowModal() == wx.ID_OK:
            
            path = HydrusData.ToUnicode( dlg.GetPath() )
            
        else:
            
            return
            
        
    
    message = 'Would you like to use hydrus\'s normal hash type, or an alternative?'
    message += os.linesep * 2
    message += 'Hydrus uses SHA256 to identify files, but other services use different standards. MD5, SHA1 and SHA512 are available, but only for local files, which may limit your export.'
    message += os.linesep * 2
    message += 'If you do not know what this stuff means, click \'normal\'.'
    
    with DialogYesNo( parent, message, title = 'Choose which hash type.', yes_label = 'normal', no_label = 'alternative' ) as dlg:
        
        result = dlg.ShowModal()
        
        if result in ( wx.ID_YES, wx.ID_NO ):
            
            if result == wx.ID_YES:
                
                hash_type = HydrusTagArchive.HASH_TYPE_SHA256
                
            else:
                
                list_of_tuples = []
                
                list_of_tuples.append( ( 'md5', HydrusTagArchive.HASH_TYPE_MD5 ) )
                list_of_tuples.append( ( 'sha1', HydrusTagArchive.HASH_TYPE_SHA1 ) )
                list_of_tuples.append( ( 'sha512', HydrusTagArchive.HASH_TYPE_SHA512 ) )
                
                with DialogSelectFromList( parent, 'Select the hash type', list_of_tuples ) as hash_dlg:
                    
                    if hash_dlg.ShowModal() == wx.ID_OK:
                        
                        hash_type = hash_dlg.GetChoice()
                        
                    else:
                        
                        return
                        
                    
                
            
        
    
    if hash_type is not None:
        
        HydrusGlobals.client_controller.Write( 'export_mappings', path, service_key, hash_type, hashes )
        
    
def ImportFromHTA( parent, hta_path, tag_service_key, hashes ):
    
    hta = HydrusTagArchive.HydrusTagArchive( hta_path )
    
    potential_namespaces = hta.GetNamespaces()
    
    hash_type = hta.GetHashType() # this tests if the hta can produce a hashtype
    
    del hta
    
    service = HydrusGlobals.client_controller.GetServicesManager().GetService( tag_service_key )
    
    service_type = service.GetServiceType()
    
    can_delete = True
    
    if service_type == HC.TAG_REPOSITORY:
        
        if service.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_OVERRULE ):
            
            can_delete = False
            
        
    
    if can_delete:
        
        text = 'Would you like to add or delete the archive\'s tags?'
        
        with DialogYesNo( parent, text, title = 'Add or delete?', yes_label = 'add', no_label = 'delete' ) as dlg_add:
            
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
    
    with DialogCheckFromListOfStrings( parent, text, HydrusData.ConvertUglyNamespacesToPrettyStrings( potential_namespaces ) ) as dlg_namespaces:
        
        if dlg_namespaces.ShowModal() == wx.ID_OK:
            
            namespaces = HydrusData.ConvertPrettyStringsToUglyNamespaces( dlg_namespaces.GetChecked() )
            
            if hash_type == HydrusTagArchive.HASH_TYPE_SHA256:
                
                text = 'This tag archive can be fully merged into your database, but this may be more than you want.'
                text += os.linesep * 2
                text += 'Would you like to import the tags only for files you actually have, or do you want absolutely everything?'
                
                with DialogYesNo( parent, text, title = 'How much do you want?', yes_label = 'just for my local files', no_label = 'everything' ) as dlg_add:
                    
                    result = dlg_add.ShowModal()
                    
                    if result == wx.ID_YES:
                        
                        file_service_key = CC.LOCAL_FILE_SERVICE_KEY
                        
                    elif result == wx.ID_NO:
                        
                        file_service_key = CC.COMBINED_FILE_SERVICE_KEY
                        
                    else:
                        
                        return
                        
                    
                
            else:
                
                file_service_key = CC.LOCAL_FILE_SERVICE_KEY
                
            
            text = 'Are you absolutely sure you want to '
            
            if adding: text += 'add'
            else: text += 'delete'
            
            text += ' the namespaces:'
            text += os.linesep * 2
            text += os.linesep.join( HydrusData.ConvertUglyNamespacesToPrettyStrings( namespaces ) )
            text += os.linesep * 2
            
            file_service = HydrusGlobals.client_controller.GetServicesManager().GetService( file_service_key )
            
            text += 'For '
            
            if hashes is None:
                
                text += 'all'
                
            else:
                
                text += HydrusData.ConvertIntToPrettyString( len( hashes ) )
                
            
            text += ' files in \'' + file_service.GetName() + '\''
            
            if adding: text += ' to '
            else: text += ' from '
            
            text += '\'' + service.GetName() + '\'?'
            
            with DialogYesNo( parent, text ) as dlg_final:
                
                if dlg_final.ShowModal() == wx.ID_YES:
                    
                    HydrusGlobals.client_controller.pub( 'sync_to_tag_archive', hta_path, tag_service_key, file_service_key, adding, namespaces, hashes )
                    
                
            
        
    
def SelectServiceKey( service_types = HC.ALL_SERVICES, service_keys = None, unallowed = None ):
    
    if service_keys is None:
        
        services = HydrusGlobals.client_controller.GetServicesManager().GetServices( service_types )
        
        service_keys = [ service.GetServiceKey() for service in services ]
        
    
    if unallowed is not None:
        
        service_keys.difference_update( unallowed )
        
    
    if len( service_keys ) == 0:
        
        return None
        
    elif len( service_keys ) == 1:
        
        ( service_key, ) = service_keys
        
        return service_key
        
    else:
        
        services = { HydrusGlobals.client_controller.GetServicesManager().GetService( service_key ) for service_key in service_keys }
        
        list_of_tuples = [ ( service.GetName(), service.GetServiceKey() ) for service in services ]
        
        with DialogSelectFromList( HydrusGlobals.client_controller.GetGUI(), 'select service', list_of_tuples ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                service_key = dlg.GetChoice()
                
                return service_key
                
            else:
                
                return None
                
            
        
    
class Dialog( wx.Dialog ):
    
    def __init__( self, parent, title, style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER, position = 'topleft' ):
        
        if parent is not None and position == 'topleft':
            
            if isinstance( parent, wx.TopLevelWindow ):
                
                parent_tlp = parent
                
            else:
                
                parent_tlp = parent.GetTopLevelParent()
                
            
            ( pos_x, pos_y ) = parent_tlp.GetPositionTuple()
            
            pos = ( pos_x + 50, pos_y + 50 )
            
        else:
            
            pos = wx.DefaultPosition
            
        
        if not HC.PLATFORM_LINUX and parent is not None:
            
            style |= wx.FRAME_FLOAT_ON_PARENT
            
        
        wx.Dialog.__init__( self, parent, title = title, style = style, pos = pos )
        
        self._new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self.SetIcon( wx.Icon( os.path.join( HC.STATIC_DIR, 'hydrus.ico' ), wx.BITMAP_TYPE_ICO ) )
        
        self.Bind( wx.EVT_BUTTON, self.EventDialogButton )
        
        if parent is not None and position == 'center':
            
            wx.CallAfter( self.Center )
            
        
        HydrusGlobals.client_controller.ResetIdleTimer()
        
    
    def EventDialogButton( self, event ): self.EndModal( event.GetId() )
    
    def SetInitialSize( self, ( width, height ) ):
        
        ( display_width, display_height ) = ClientGUITopLevelWindows.GetDisplaySize( self )
        
        width = min( display_width, width )
        height = min( display_height, height )
        
        wx.Dialog.SetInitialSize( self, ( width, height ) )
        
        min_width = min( 240, width )
        min_height = min( 240, height )
        
        self.SetMinSize( ( min_width, min_height ) )
        
    
class DialogAdvancedContentUpdate( Dialog ):
    
    COPY = 0
    DELETE = 1
    DELETE_DELETED = 2
    
    ALL_MAPPINGS = 0
    SPECIFIC_MAPPINGS = 1
    SPECIFIC_NAMESPACE = 2
    NAMESPACED = 3
    UNNAMESPACED = 4
    
    def __init__( self, parent, service_key, hashes = None ):
        
        Dialog.__init__( self, parent, 'Advanced Content Update' )
        
        self._service_key = service_key
        self._hashes = hashes
        
        service = HydrusGlobals.client_controller.GetServicesManager().GetService( self._service_key )
        
        self._service_name = service.GetName()
        
        self._command_panel = ClientGUICommon.StaticBox( self, 'database commands' )
        
        self._action_dropdown = ClientGUICommon.BetterChoice( self._command_panel )
        self._action_dropdown.Bind( wx.EVT_CHOICE, self.EventChoice )
        self._tag_type_dropdown = ClientGUICommon.BetterChoice( self._command_panel )
        self._action_text = wx.StaticText( self._command_panel, label = 'initialising' )
        self._service_key_dropdown = ClientGUICommon.BetterChoice( self._command_panel )
        
        self._go = ClientGUICommon.BetterButton( self._command_panel, 'Go!', self.Go )
        
        #
        
        self._hta_panel = ClientGUICommon.StaticBox( self, 'hydrus tag archives' )
        
        self._import_from_hta = ClientGUICommon.BetterButton( self._hta_panel, 'one-time mass import or delete using a hydrus tag archive', self.ImportFromHTA )
        self._export_to_hta = ClientGUICommon.BetterButton( self._hta_panel, 'export to hydrus tag archive', self.ExportToHTA )
        
        #
        
        self._done = wx.Button( self, id = wx.ID_OK, label = 'done' )
        
        #
        
        services = [ service for service in HydrusGlobals.client_controller.GetServicesManager().GetServices( HC.TAG_SERVICES ) if service.GetServiceKey() != self._service_key ]
        
        if len( services ) > 0:
            
            self._action_dropdown.Append( 'copy', self.COPY )
            
        
        if self._service_key == CC.LOCAL_TAG_SERVICE_KEY:
            
            self._action_dropdown.Append( 'delete', self.DELETE )
            self._action_dropdown.Append( 'clear deleted record', self.DELETE_DELETED )
            
        
        self._action_dropdown.Select( 0 )
        
        #
        
        self._tag_type_dropdown.Append( 'all mappings', self.ALL_MAPPINGS )
        self._tag_type_dropdown.Append( 'all namespaced mappings', self.NAMESPACED )
        self._tag_type_dropdown.Append( 'all unnamespaced mappings', self.UNNAMESPACED )
        self._tag_type_dropdown.Append( 'specific tag\'s mappings', self.SPECIFIC_MAPPINGS )
        self._tag_type_dropdown.Append( 'specific namespace\'s mappings', self.SPECIFIC_NAMESPACE )
        
        self._tag_type_dropdown.Select( 0 )
        
        #
        
        for service in services:
            
            self._service_key_dropdown.Append( service.GetName(), service.GetServiceKey() )
            
        
        self._service_key_dropdown.Select( 0 )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._action_dropdown, CC.FLAGS_VCENTER )
        hbox.AddF( self._tag_type_dropdown, CC.FLAGS_VCENTER )
        hbox.AddF( self._action_text, CC.FLAGS_VCENTER )
        hbox.AddF( self._service_key_dropdown, CC.FLAGS_VCENTER )
        hbox.AddF( self._go, CC.FLAGS_VCENTER )
        
        self._command_panel.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        self._hta_panel.AddF( self._import_from_hta, CC.FLAGS_LONE_BUTTON )
        self._hta_panel.AddF( self._export_to_hta, CC.FLAGS_LONE_BUTTON )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        message = 'Regarding '
        
        if self._hashes is None:
            
            message += 'all'
            
        else:
            
            message += HydrusData.ConvertIntToPrettyString( len( self._hashes ) )
            
        
        message += ' files on ' + self._service_name
        
        title_st = wx.StaticText( self, label = message)
        
        title_st.Wrap( 540 )
        
        message = 'These advanced operations are powerful, so think before you click. They can lock up your client for a _long_ time, and are not undoable. You may need to refresh your existing searches to see their effect.' 
        
        st = wx.StaticText( self, label = message )
        
        st.Wrap( 540 )
        
        vbox.AddF( title_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._command_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._hta_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._done, CC.FLAGS_LONE_BUTTON )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        if x < 540: x = 540
        
        self.SetInitialSize( ( x, y ) )
        
        self.EventChoice( None )
        
    
    def EventChoice( self, event ):
        
        data = self._action_dropdown.GetChoice()
        
        if data in ( self.DELETE, self.DELETE_DELETED ):
            
            self._action_text.SetLabelText( 'from ' + self._service_name )
            
            self._service_key_dropdown.Hide()
            
        else:
            
            self._action_text.SetLabelText( 'from ' + self._service_name + ' to')
            
            self._service_key_dropdown.Show()
            
        
        self.Layout()
        
    
    def ExportToHTA( self ):
        
        ExportToHTA( self, self._service_key, self._hashes )
        
    
    def Go( self ):
        
        # at some point, rewrite this to cope with multiple tags. setsometag is ready to go on that front
        # this should prob be with a listbox so people can enter their new multiple tags in several separate goes, rather than overwriting every time
        
        action = self._action_dropdown.GetChoice()
        
        tag_type = self._tag_type_dropdown.GetChoice()
        
        if tag_type == self.ALL_MAPPINGS:
            
            tag = None
            
        elif tag_type == self.SPECIFIC_MAPPINGS:
            
            with DialogTextEntry( self, 'Enter tag' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    entry = dlg.GetValue()
                    
                    tag = ( 'tag', entry )
                    
                else:
                    
                    return
                    
                
            
        elif tag_type == self.SPECIFIC_NAMESPACE:
            
            with DialogTextEntry( self, 'Enter namespace' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    entry = dlg.GetValue()
                    
                    if entry.endswith( ':' ): entry = entry[:-1]
                    
                    tag = ( 'namespace', entry )
                    
                else:
                    
                    return
                    
                
            
        elif tag_type == self.NAMESPACED:
            
            tag = ( 'namespaced', None )
            
        elif tag_type == self.UNNAMESPACED:
            
            tag = ( 'unnamespaced', None )
            
        
        with DialogYesNo( self, 'Are you sure?' ) as dlg:
            
            if dlg.ShowModal() != wx.ID_YES: return
            
        
        if action == self.COPY:
            
            service_key_target = self._service_key_dropdown.GetChoice()
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADVANCED, ( 'copy', ( tag, self._hashes, service_key_target ) ) )
            
        elif action == self.DELETE:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADVANCED, ( 'delete', ( tag, self._hashes ) ) )
            
        elif action == self.DELETE_DELETED:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADVANCED, ( 'delete_deleted', ( tag, self._hashes ) ) )
            
        
        service_keys_to_content_updates = { self._service_key : [ content_update ] }
        
        HydrusGlobals.client_controller.Write( 'content_updates', service_keys_to_content_updates )
        
    
    def ImportFromHTA( self ):
        
        text = 'Select the Hydrus Tag Archive\'s location.'
        
        with wx.FileDialog( self, message = text, style = wx.FD_OPEN ) as dlg_file:
            
            if dlg_file.ShowModal() == wx.ID_OK:
                
                path = HydrusData.ToUnicode( dlg_file.GetPath() )
                
                ImportFromHTA( self, path, self._service_key, self._hashes )
                
            
        
    
class DialogButtonChoice( Dialog ):
    
    def __init__( self, parent, intro, choices, show_always_checkbox = False ):
        
        Dialog.__init__( self, parent, 'choose what to do', position = 'center' )
        
        self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
        
        self._buttons = []
        self._ids_to_data = {}
        
        i = 0
        
        for ( text, data, tooltip ) in choices:
            
            button = wx.Button( self, label = text, id = i )
            
            button.SetToolTipString( tooltip )
            
            self._buttons.append( button )
            
            self._ids_to_data[ i ] = data
            
            i += 1
            
        
        self._always_do_checkbox = wx.CheckBox( self, label = 'do this for all' )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( wx.StaticText( self, label = intro ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        for button in self._buttons:
            
            vbox.AddF( button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        vbox.AddF( self._always_do_checkbox, CC.FLAGS_LONE_BUTTON )
        
        if not show_always_checkbox:
            
            self._always_do_checkbox.Hide()
            
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( x, y ) )
        
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        
        if len( self._buttons ) > 0:
            
            wx.CallAfter( self._buttons[0].SetFocus )
            
        
    
    def EventButton( self, event ):
        
        id = event.GetId()
        
        if id == wx.ID_CANCEL: self.EndModal( wx.ID_CANCEL )
        else:
            
            self._data = self._ids_to_data[ id ]
            
            self.EndModal( wx.ID_OK )
            
        
    
    def GetData( self ):
        
        return ( self._always_do_checkbox.GetValue(), self._data )
        
    
class DialogChooseNewServiceMethod( Dialog ):
    
    def __init__( self, parent ):
        
        Dialog.__init__( self, parent, 'how to set up the account?', position = 'center' )
        
        self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
        
        register_message = 'I want to initialise a new account with the server. I have a registration key (a key starting with \'r\').'
        
        self._register = wx.Button( self, label = register_message )
        self._register.Bind( wx.EVT_BUTTON, self.EventRegister )
        
        setup_message = 'The account is already initialised; I just want to add it to this client. I have a normal access key.'
        
        self._setup = wx.Button( self, id = wx.ID_OK, label = setup_message )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._register, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( wx.StaticText( self, label = '-or-', style = wx.ALIGN_CENTER ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._setup, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( x, y ) )
        
        self._should_register = False
        
        wx.CallAfter( self._register.SetFocus )
        
    
    def EventRegister( self, event ):
        
        self._should_register = True
        
        self.EndModal( wx.ID_OK )
        
    
    def GetRegister( self ): return self._should_register
    
class DialogFinishFiltering( Dialog ):
    
    def __init__( self, parent, num_kept, num_deleted, keep = 'keep', delete = 'delete' ):
        
        Dialog.__init__( self, parent, 'are you sure?', position = 'center' )
        
        self._commit = wx.Button( self, id = wx.ID_YES, label = 'commit' )
        self._commit.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._forget = wx.Button( self, id = wx.ID_NO, label = 'forget' )
        self._forget.SetForegroundColour( ( 128, 0, 0 ) )
        
        self._back = wx.Button( self, id = wx.ID_CANCEL, label = 'back to filtering' )
        
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
        
        wx.CallAfter( self._commit.SetFocus )
        
    
class DialogGenerateNewAccounts( Dialog ):
    
    def __init__( self, parent, service_key ):
        
        Dialog.__init__( self, parent, 'configure new accounts' )
        
        self._service_key = service_key
        
        self._num = wx.SpinCtrl( self, min = 1, max = 10000, size = ( 80, -1 ) )
        
        self._account_types = ClientGUICommon.BetterChoice( self )
        
        self._lifetime = ClientGUICommon.BetterChoice( self )
        
        self._ok = wx.Button( self, label = 'Ok' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        self._num.SetValue( 1 )
        
        service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
        
        response = service.Request( HC.GET, 'account_types' )
        
        account_types = response[ 'account_types' ]
        
        for account_type in account_types:
            
            self._account_types.Append( account_type.GetTitle(), account_type )
            
        
        self._account_types.Select( 0 )
        
        for ( s, value ) in HC.lifetimes:
            
            self._lifetime.Append( s, value )
            
        
        self._lifetime.SetSelection( 3 ) # one year
        
        #
        
        ctrl_box = wx.BoxSizer( wx.HORIZONTAL )
        
        ctrl_box.AddF( wx.StaticText( self, label = 'generate' ), CC.FLAGS_VCENTER )
        ctrl_box.AddF( self._num, CC.FLAGS_VCENTER )
        ctrl_box.AddF( self._account_types, CC.FLAGS_VCENTER )
        ctrl_box.AddF( wx.StaticText( self, label = 'accounts, to expire in' ), CC.FLAGS_VCENTER )
        ctrl_box.AddF( self._lifetime, CC.FLAGS_VCENTER )
        
        b_box = wx.BoxSizer( wx.HORIZONTAL )
        b_box.AddF( self._ok, CC.FLAGS_VCENTER )
        b_box.AddF( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( ctrl_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventOK( self, event ):
        
        num = self._num.GetValue()
        
        account_type = self._account_types.GetChoice()
        
        account_type_key = account_type.GetAccountTypeKey()
        
        lifetime = self._lifetime.GetChoice()
        
        if lifetime is None:
            
            expires = None
            
        else:
            
            expires = HydrusData.GetNow() + lifetime
            
        
        service = HydrusGlobals.client_controller.GetServicesManager().GetService( self._service_key )
        
        try:
            
            request_args = { 'num' : num, 'account_type_key' : account_type_key }
            
            if expires is not None:
                
                request_args[ 'expires' ] = expires
                
            
            response = service.Request( HC.GET, 'registration_keys', request_args )
            
            registration_keys = response[ 'registration_keys' ]
            
            ClientGUIFrames.ShowKeys( 'registration', registration_keys )
            
        finally:
            
            self.EndModal( wx.ID_OK )
            
        
    
class DialogInputImportTagOptions( Dialog ):
    
    def __init__( self, parent, pretty_name, gallery_identifier, import_tag_options = None ):
        
        Dialog.__init__( self, parent, 'configure default import tag options for ' + pretty_name )
        
        #
        
        ( namespaces, search_value ) = ClientDefaults.GetDefaultNamespacesAndSearchValue( gallery_identifier )
        
        self._import_tag_options = ClientGUICollapsible.CollapsibleOptionsTags( self, namespaces = namespaces )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        if import_tag_options is None:
            
            new_options = HydrusGlobals.client_controller.GetNewOptions()
            
            import_tag_options = new_options.GetDefaultImportTagOptions( gallery_identifier )
            
        
        self._import_tag_options.SetOptions( import_tag_options )
        
        #
        
        b_box = wx.BoxSizer( wx.HORIZONTAL )
        b_box.AddF( self._ok, CC.FLAGS_VCENTER )
        b_box.AddF( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._import_tag_options, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( 300, x )
        y = max( 300, y )
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._import_tag_options.ExpandCollapse )
        
    
    def GetImportTagOptions( self ):
        
        import_tag_options = self._import_tag_options.GetOptions()
        
        return import_tag_options
        
    
class DialogInputCustomFilterAction( Dialog ):
    
    def __init__( self, parent, modifier = wx.ACCEL_NORMAL, key = wx.WXK_F7, service_key = None, action = 'archive' ):
        
        Dialog.__init__( self, parent, 'input custom filter action' )
        
        self._service_key = service_key
        self._action = action
        
        self._current_ratings_like_service = None
        self._current_ratings_numerical_service = None
        
        self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
        
        self._shortcut_panel = ClientGUICommon.StaticBox( self, 'shortcut' )
        
        self._shortcut = ClientGUICommon.Shortcut( self._shortcut_panel, modifier, key )
        
        self._none_panel = ClientGUICommon.StaticBox( self, 'non-service actions' )
        
        self._none_actions = wx.Choice( self._none_panel, choices = [ 'manage_tags', 'manage_ratings', 'archive', 'inbox', 'delete', 'fullscreen_switch', 'frame_back', 'frame_next', 'next', 'first', 'last', 'open_externally', 'pan_up', 'pan_down', 'pan_left', 'pan_right', 'previous', 'remove', 'zoom_in', 'zoom_out', 'zoom_switch' ] )
        
        self._ok_none = wx.Button( self._none_panel, label = 'ok' )
        self._ok_none.Bind( wx.EVT_BUTTON, self.EventOKNone )
        self._ok_none.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._tag_panel = ClientGUICommon.StaticBox( self, 'tag service actions' )
        
        self._tag_service_keys = wx.Choice( self._tag_panel )
        self._tag_value = wx.TextCtrl( self._tag_panel, style = wx.TE_READONLY )
        
        expand_parents = False
        
        self._tag_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self._tag_panel, self.SetTags, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, CC.COMBINED_TAG_SERVICE_KEY )
        
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
        
        services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.LOCAL_TAG, HC.TAG_REPOSITORY, HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
        
        for service in services:
            
            service_type = service.GetServiceType()
            
            if service_type in HC.TAG_SERVICES: choice = self._tag_service_keys
            elif service_type == HC.LOCAL_RATING_LIKE: choice = self._ratings_like_service_keys
            elif service_type == HC.LOCAL_RATING_NUMERICAL: choice = self._ratings_numerical_service_keys
            
            choice.Append( service.GetName(), service.GetServiceKey() )
            
        
        self._SetActions()
        
        if self._service_key is None:
            
            self._none_actions.SetStringSelection( self._action )
            
        else:
            
            self._service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
            
            service_name = self._service.GetName()
            service_type = self._service.GetServiceType()
            
            if service_type in HC.TAG_SERVICES:
                
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
                
                if self._action is None:
                    
                    self._ratings_numerical_remove.SetValue( True )
                    
                else:
                    
                    num_stars = self._current_ratings_numerical_service.GetNumStars()
                    
                    slider_value = int( round( self._action * num_stars ) )
                    
                    self._ratings_numerical_slider.SetValue( slider_value )
                    
                
            
        
        #
        
        self._shortcut_panel.AddF( self._shortcut, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        none_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        none_hbox.AddF( self._none_actions, CC.FLAGS_EXPAND_DEPTH_ONLY )
        none_hbox.AddF( self._ok_none, CC.FLAGS_VCENTER )
        
        self._none_panel.AddF( none_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        tag_sub_vbox = wx.BoxSizer( wx.VERTICAL )
        
        tag_sub_vbox.AddF( self._tag_value, CC.FLAGS_EXPAND_PERPENDICULAR )
        tag_sub_vbox.AddF( self._tag_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        tag_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        tag_hbox.AddF( self._tag_service_keys, CC.FLAGS_EXPAND_DEPTH_ONLY )
        tag_hbox.AddF( tag_sub_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        tag_hbox.AddF( self._ok_tag, CC.FLAGS_VCENTER )
        
        self._tag_panel.AddF( tag_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        ratings_like_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        ratings_like_hbox.AddF( self._ratings_like_service_keys, CC.FLAGS_EXPAND_DEPTH_ONLY )
        ratings_like_hbox.AddF( self._ratings_like_like, CC.FLAGS_VCENTER )
        ratings_like_hbox.AddF( self._ratings_like_dislike, CC.FLAGS_VCENTER )
        ratings_like_hbox.AddF( self._ratings_like_remove, CC.FLAGS_VCENTER )
        ratings_like_hbox.AddF( self._ok_ratings_like, CC.FLAGS_VCENTER )
        
        self._ratings_like_panel.AddF( ratings_like_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        ratings_numerical_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        ratings_numerical_hbox.AddF( self._ratings_numerical_service_keys, CC.FLAGS_EXPAND_DEPTH_ONLY )
        ratings_numerical_hbox.AddF( self._ratings_numerical_slider, CC.FLAGS_VCENTER )
        ratings_numerical_hbox.AddF( self._ratings_numerical_remove, CC.FLAGS_VCENTER )
        ratings_numerical_hbox.AddF( self._ok_ratings_numerical, CC.FLAGS_VCENTER )
        
        self._ratings_numerical_panel.AddF( ratings_numerical_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._none_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._tag_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._ratings_like_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._ratings_numerical_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._shortcut_panel, CC.FLAGS_VCENTER )
        hbox.AddF( wx.StaticText( self, label = u'\u2192' ), CC.FLAGS_VCENTER )
        hbox.AddF( vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( hbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( 680, y ) )
        
        wx.CallAfter( self._ok_none.SetFocus )
        
    
    def _SetActions( self ):
        
        if self._ratings_like_service_keys.GetCount() > 0:
            
            selection = self._ratings_like_service_keys.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                service_key = self._ratings_like_service_keys.GetClientData( selection )
                
                service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
                
                self._current_ratings_like_service = service
                
            
        
        if self._ratings_numerical_service_keys.GetCount() > 0:
            
            selection = self._ratings_numerical_service_keys.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                service_key = self._ratings_numerical_service_keys.GetClientData( selection )
                
                service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
                
                self._current_ratings_numerical_service = service
                
                num_stars = service.GetNumStars()
                
                allow_zero = service.AllowZero()
                
                if allow_zero:
                    
                    min = 0
                    
                else:
                    
                    min = 1
                    
                
                self._ratings_numerical_slider.SetRange( min, num_stars )
                
            
        
    
    def EventOKNone( self, event ):
        
        self._service_key = None
        self._action = self._none_actions.GetStringSelection()
        self._pretty_action = self._action
        
        self.EndModal( wx.ID_OK )
        
    
    def EventOKRatingsLike( self, event ):
        
        selection = self._ratings_like_service_keys.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            self._service_key = self._ratings_like_service_keys.GetClientData( selection )
            
            if self._ratings_like_like.GetValue():
                
                self._action = 1.0
                self._pretty_action = 'like'
                
            elif self._ratings_like_dislike.GetValue():
                
                self._action = 0.0
                self._pretty_action = 'dislike'
                
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
                
                value = self._ratings_numerical_slider.GetValue()
                
                self._pretty_action = HydrusData.ToUnicode( value )
                
                num_stars = self._current_ratings_numerical_service.GetNumStars()
                allow_zero = self._current_ratings_numerical_service.AllowZero()
                
                if allow_zero:
                    
                    self._action = float( value ) / num_stars
                    
                else:
                    
                    self._action = float( value - 1 ) / ( num_stars - 1 )
                    
                
            
            self.EndModal( wx.ID_OK )
            
        else: self.EndModal( wx.ID_CANCEL )
        
    
    def EventOKTag( self, event ):
        
        # this could support multiple tags now
        
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
        else: pretty_service_key = HydrusGlobals.client_controller.GetServicesManager().GetService( self._service_key ).GetName()
        
        ( pretty_modifier, pretty_key ) = ClientData.ConvertShortcutToPrettyShortcut( modifier, key )
        
        return ( ( pretty_modifier, pretty_key, pretty_service_key, self._pretty_action ), ( modifier, key, self._service_key, self._action ) )
        
    
    def SetTags( self, tags ):
        
        if len( tags ) > 0:
            
            tag = list( tags )[0]
            
            self._tag_value.SetValue( tag )
            
        
    
class DialogInputFileSystemPredicates( Dialog ):
    
    def __init__( self, parent, predicate_type ):
        
        Dialog.__init__( self, parent, 'enter predicate' )
        
        pred_classes = []
        
        if predicate_type == HC.PREDICATE_TYPE_SYSTEM_AGE: pred_classes.append( ClientGUIPredicates.PanelPredicateSystemAge )
        if predicate_type == HC.PREDICATE_TYPE_SYSTEM_DIMENSIONS:
            
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemHeight )
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemWidth )
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemRatio )
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemNumPixels )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_DURATION: pred_classes.append( ClientGUIPredicates.PanelPredicateSystemDuration )
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE: pred_classes.append( ClientGUIPredicates.PanelPredicateSystemFileService )
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_HASH: pred_classes.append( ClientGUIPredicates.PanelPredicateSystemHash )
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_LIMIT: pred_classes.append( ClientGUIPredicates.PanelPredicateSystemLimit )
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_MIME: pred_classes.append( ClientGUIPredicates.PanelPredicateSystemMime )
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS: pred_classes.append( ClientGUIPredicates.PanelPredicateSystemNumTags )
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS: pred_classes.append( ClientGUIPredicates.PanelPredicateSystemNumWords )
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_RATING:
            
            services_manager = HydrusGlobals.client_controller.GetServicesManager()
            
            ratings_services = services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
            
            if len( ratings_services ) > 0:
                
                pred_classes.append( ClientGUIPredicates.PanelPredicateSystemRating )
                
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO: pred_classes.append( ClientGUIPredicates.PanelPredicateSystemSimilarTo )
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIZE: pred_classes.append( ClientGUIPredicates.PanelPredicateSystemSize )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        for pred_class in pred_classes:
            
            panel = self._Panel( self, pred_class )
            
            vbox.AddF( panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self.SetSizer( vbox )
        
        self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
    
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( x, y ) )
        
    
    def SubPanelOK( self, predicates ):
        
        self._predicates = predicates
        
        self.EndModal( wx.ID_OK )
        
    
    def GetPredicates( self ): return self._predicates
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, predicate_class ):
            
            wx.Panel.__init__( self, parent )
            
            self._predicate_panel = predicate_class( self )
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._predicate_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            hbox.AddF( self._ok, CC.FLAGS_VCENTER )
            
            self.SetSizer( hbox )
            
            self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
            
        
        def _DoOK( self ):
            
            predicates = self._predicate_panel.GetPredicates()
            
            self.GetParent().SubPanelOK( predicates )
            
        
        def EventCharHook( self, event ):
            
            if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
                
                self._DoOK()
                
            else:
                
                event.Skip()
                
            
        
        def EventOK( self, event ):
            
            self._DoOK()
            
        
    
class DialogInputLocalBooruShare( Dialog ):
    
    def __init__( self, parent, share_key, name, text, timeout, hashes, new_share = False ):
        
        Dialog.__init__( self, parent, 'configure local booru share' )
        
        self._name = wx.TextCtrl( self )
        
        self._text = ClientGUICommon.SaneMultilineTextCtrl( self )
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
        
        #
        
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
        
        #
        
        rows = []
        
        rows.append( ( 'share name: ', self._name ) )
        rows.append( ( 'share text: ', self._text ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        timeout_box = wx.BoxSizer( wx.HORIZONTAL )
        timeout_box.AddF( self._timeout_number, CC.FLAGS_EXPAND_BOTH_WAYS )
        timeout_box.AddF( self._timeout_multiplier, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        link_box = wx.BoxSizer( wx.HORIZONTAL )
        link_box.AddF( self._copy_internal_share_link, CC.FLAGS_VCENTER )
        link_box.AddF( self._copy_external_share_link, CC.FLAGS_VCENTER )
        
        b_box = wx.BoxSizer( wx.HORIZONTAL )
        b_box.AddF( self._ok, CC.FLAGS_VCENTER )
        b_box.AddF( self._cancel, CC.FLAGS_VCENTER )
        
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
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventCopyExternalShareURL( self, event ):
        
        self._service = HydrusGlobals.client_controller.GetServicesManager().GetService( CC.LOCAL_BOORU_SERVICE_KEY )
        
        external_ip = HydrusNATPunch.GetExternalIP() # eventually check for optional host replacement here
        
        external_port = self._service.GetUPnPPort()
        
        if external_port is None:
            
            external_port = self._service.GetPort()
            
        
        url = 'http://' + external_ip + ':' + HydrusData.ToUnicode( external_port ) + '/gallery?share_key=' + self._share_key.encode( 'hex' )
        
        HydrusGlobals.client_controller.pub( 'clipboard', 'text', url )
        
    
    def EventCopyInternalShareURL( self, event ):
        
        self._service = HydrusGlobals.client_controller.GetServicesManager().GetService( CC.LOCAL_BOORU_SERVICE_KEY )
        
        internal_ip = '127.0.0.1'
        
        internal_port = self._service.GetPort()
        
        url = 'http://' + internal_ip + ':' + str( internal_port ) + '/gallery?share_key=' + self._share_key.encode( 'hex' )
        
        HydrusGlobals.client_controller.pub( 'clipboard', 'text', url )
        
    
    def GetInfo( self ):
        
        name = self._name.GetValue()
        
        text = self._text.GetValue()
        
        timeout = self._timeout_number.GetValue()
        
        if timeout is not None: timeout = timeout * self._timeout_multiplier.GetChoice() + HydrusData.GetNow()
        
        return ( self._share_key, name, text, timeout, self._hashes )
        
    
class DialogInputLocalFiles( Dialog ):
    
    def __init__( self, parent, paths = None ):
        
        if paths is None: paths = []
        
        Dialog.__init__( self, parent, 'importing files' )
        
        self.SetDropTarget( ClientDragDrop.FileDropTarget( self._AddPathsToList ) )
        
        self._paths_list = ClientGUICommon.SaneListCtrl( self, 120, [ ( 'path', -1 ), ( 'guessed mime', 110 ), ( 'size', 60 ) ], delete_key_callback = self.RemovePaths )
        
        self._progress = ClientGUICommon.TextAndGauge( self )
        
        self._progress_pause = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.pause, self.PauseProgress )
        self._progress_pause.Disable()
        
        self._progress_cancel = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.stop, self.StopProgress )
        self._progress_cancel.Disable()
        
        self._add_files_button = ClientGUICommon.BetterButton( self, 'add files', self.AddPaths )
        
        self._add_folder_button = ClientGUICommon.BetterButton( self, 'add folder', self.AddFolder )
        
        self._remove_files_button = ClientGUICommon.BetterButton( self, 'remove files', self.RemovePaths )
        
        self._import_file_options = ClientGUICollapsible.CollapsibleOptionsImportFiles( self )
        
        self._delete_after_success = wx.CheckBox( self, label = 'delete original files after successful import' )
        
        self._add_button = wx.Button( self, label = 'import now' )
        self._add_button.Bind( wx.EVT_BUTTON, self.EventOK )
        self._add_button.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._tag_button = wx.Button( self, label = 'add tags based on filename' )
        self._tag_button.Bind( wx.EVT_BUTTON, self.EventTags )
        self._tag_button.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.Bind( wx.EVT_BUTTON, self.EventCancel )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        gauge_sizer = wx.BoxSizer( wx.HORIZONTAL )
        
        gauge_sizer.AddF( self._progress, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        gauge_sizer.AddF( self._progress_pause, CC.FLAGS_VCENTER )
        gauge_sizer.AddF( self._progress_cancel, CC.FLAGS_VCENTER )
        
        file_buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        file_buttons.AddF( self._add_files_button, CC.FLAGS_VCENTER )
        file_buttons.AddF( self._add_folder_button, CC.FLAGS_VCENTER )
        file_buttons.AddF( self._remove_files_button, CC.FLAGS_VCENTER )
        
        buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        buttons.AddF( self._add_button, CC.FLAGS_VCENTER )
        buttons.AddF( self._tag_button, CC.FLAGS_VCENTER )
        buttons.AddF( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._paths_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( gauge_sizer, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( file_buttons, CC.FLAGS_BUTTON_SIZER )
        vbox.AddF( self._import_file_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._delete_after_success, CC.FLAGS_LONE_BUTTON )
        vbox.AddF( ( 0, 5 ), CC.FLAGS_NONE )
        vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        if x < 780: x = 780
        if y < 480: y = 480
        
        self.SetInitialSize( ( x, y ) )
        
        self._lock = threading.Lock()
        
        self._processing_queue = []
        self._currently_parsing = False
        
        self._current_paths = []
        self._current_paths_set = set()
        
        self._job_key = ClientThreading.JobKey()
        
        self._parsed_path_queue = Queue.Queue()
        
        self._add_path_updater = ClientGUICommon.ThreadToGUIUpdater( self._paths_list, self.AddParsedPaths )
        self._progress_updater = ClientGUICommon.ThreadToGUIUpdater( self._progress, self._progress.SetValue )
        self._done_parsing_updater = ClientGUICommon.ThreadToGUIUpdater( self._progress_cancel, self.DoneParsing )
        
        if len( paths ) > 0:
            
            self._AddPathsToList( paths )
            
        
        wx.CallAfter( self._add_button.SetFocus )
        
    
    def _AddPathsToList( self, paths ):
        
        paths = [ HydrusData.ToUnicode( path ) for path in paths ]
        
        self._processing_queue.append( paths )
        
        self._ProcessQueue()
        
    
    def _ProcessQueue( self ):
        
        if not self._currently_parsing:
            
            if len( self._processing_queue ) == 0:
                
                self._progress_pause.Disable()
                self._progress_cancel.Disable()
                
                self._add_button.Enable()
                self._tag_button.Enable()
                
            else:
                
                self._currently_parsing = True
                
                paths = self._processing_queue.pop( 0 )
                
                self._progress_pause.Enable()
                self._progress_cancel.Enable()
                
                self._add_button.Disable()
                self._tag_button.Disable()
                
                self._job_key = ClientThreading.JobKey()
                
                HydrusGlobals.client_controller.CallToThread( self.THREADParseImportablePaths, paths, self._job_key )
                
            
        
    
    def _TidyUp( self ):
        
        self._job_key.Cancel()
        
    
    def AddFolder( self ):
        
        with wx.DirDialog( self, 'Select a folder to add.', style = wx.DD_DIR_MUST_EXIST ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = HydrusData.ToUnicode( dlg.GetPath() )
                
                self._AddPathsToList( ( path, ) )
                
            
        
    
    def AddParsedPaths( self ):
        
        while not self._parsed_path_queue.empty():
            
            ( path, mime, size ) = self._parsed_path_queue.get()
            
            pretty_mime = HC.mime_string_lookup[ mime ]
            pretty_size = HydrusData.ConvertIntToBytes( size )
            
            if path not in self._current_paths_set:
                
                self._current_paths_set.add( path )
                self._current_paths.append( path )
                
                self._paths_list.Append( ( path, pretty_mime, pretty_size ), ( path, mime, size ) )
                
            
        
    
    def AddPaths( self ):
        
        with wx.FileDialog( self, 'Select the files to add.', style = wx.FD_MULTIPLE ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                paths = [ HydrusData.ToUnicode( path ) for path in dlg.GetPaths() ]
                
                self._AddPathsToList( paths )
                
            
        
    
    def DoneParsing( self ):
        
        self._currently_parsing = False
        
        self._ProcessQueue()
        
    
    def EventCancel( self, event ):
        
        self._TidyUp()
        
        self.EndModal( wx.ID_CANCEL )
        
    
    def EventOK( self, event ):
        
        self._TidyUp()
        
        if len( self._current_paths ) > 0:
            
            import_file_options = self._import_file_options.GetOptions()
            
            paths_to_tags = {}
            
            delete_after_success = self._delete_after_success.GetValue()
            
            HydrusGlobals.client_controller.pub( 'new_hdd_import', self._current_paths, import_file_options, paths_to_tags, delete_after_success )
            
        
        self.EndModal( wx.ID_OK )
        
    
    def EventTags( self, event ):
        
        if len( self._current_paths ) > 0:
            
            import_file_options = self._import_file_options.GetOptions()
            
            with DialogPathsToTags( self, self._current_paths ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    paths_to_tags = dlg.GetInfo()
                    
                    delete_after_success = self._delete_after_success.GetValue()
                    
                    HydrusGlobals.client_controller.pub( 'new_hdd_import', self._current_paths, import_file_options, paths_to_tags, delete_after_success )
                    
                    self.EndModal( wx.ID_OK )
                    
                
            
        
    
    def PauseProgress( self ):
        
        self._job_key.PausePlay()
        
        if self._job_key.IsPaused():
            
            self._add_button.Enable()
            self._tag_button.Enable()
            
            self._progress_pause.SetBitmap( CC.GlobalBMPs.play )
            
        else:
            
            self._add_button.Disable()
            self._tag_button.Disable()
            
            self._progress_pause.SetBitmap( CC.GlobalBMPs.pause )
            
        
    
    def RemovePaths( self ):
        
        with DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._paths_list.RemoveAllSelected()
                
                self._current_paths = [ row[0] for row in self._paths_list.GetClientData() ]
                self._current_paths_set = set( self._current_paths )
                
            
        
    
    def StopProgress( self ):
        
        self._job_key.Cancel()
        
        self._progress_pause.Disable()
        self._progress_cancel.Disable()
        
        self._add_button.Enable()
        self._tag_button.Enable()
        
    
    def THREADParseImportablePaths( self, raw_paths, job_key ):
        
        self._progress_updater.Update( 'Finding all files', None, None )
        
        file_paths = ClientFiles.GetAllPaths( raw_paths )
        
        free_paths = HydrusPaths.FilterFreePaths( file_paths )
        
        num_file_paths = len( file_paths )
        num_good_files = 0
        num_empty_files = 0
        num_uninteresting_mime_files = 0
        num_occupied_files = num_file_paths - len( free_paths )
        
        for ( i, path ) in enumerate( free_paths ):
            
            if path.endswith( os.path.sep + 'Thumbs.db' ) or path.endswith( os.path.sep + 'thumbs.db' ):
                
                continue
                
            
            if i % 500 == 0: gc.collect()
            
            message = 'Parsed ' + HydrusData.ConvertValueRangeToPrettyString( i, num_file_paths )
            
            self._progress_updater.Update( message, i, num_file_paths )
            
            ( i_paused, should_quit ) = job_key.WaitIfNeeded()
            
            if should_quit:
                
                break
                
            
            size = os.path.getsize( path )
            
            if size == 0:
                
                HydrusData.Print( 'Empty file: ' + path )
                
                num_empty_files += 1
                
                continue
                
            
            mime = HydrusFileHandling.GetMime( path )
            
            if mime in HC.ALLOWED_MIMES:
                
                num_good_files += 1
                
                self._parsed_path_queue.put( ( path, mime, size ) )
                
                self._add_path_updater.Update()
                
            else:
                
                HydrusData.Print( 'Unparsable file: ' + path )
                
                num_uninteresting_mime_files += 1
                
                continue
                
            
        
        if num_good_files == 0:
            
            message = 'none of the files parsed successfully'
            
        elif num_good_files == 1:
            
            message = '1 file was parsed successfully'
            
        else:
            
            message = HydrusData.ConvertIntToPrettyString( num_good_files ) + ' files were parsed successfully'
            
        
        if num_empty_files > 0 or num_uninteresting_mime_files > 0 or num_occupied_files > 0:
            
            if num_good_files == 0:
                
                message += ': '
                
            else:
                
                message += ', but '
                
            
            bad_comments = []
            
            if num_empty_files > 0:
                
                bad_comments.append( HydrusData.ConvertIntToPrettyString( num_empty_files ) + ' were empty' )
                
            
            if num_uninteresting_mime_files > 0:
                
                bad_comments.append( HydrusData.ConvertIntToPrettyString( num_uninteresting_mime_files ) + ' had unsupported mimes' )
                
            
            if num_occupied_files > 0:
                
                bad_comments.append( HydrusData.ConvertIntToPrettyString( num_occupied_files ) + ' were probably already in use by another process' )
                
            
            message += ' and '.join( bad_comments )
            
        
        message += '.'
        
        HydrusData.Print( message )
        
        self._progress_updater.Update( message, num_file_paths, num_file_paths )
        
        self._done_parsing_updater.Update()
        
    
class DialogInputNamespaceRegex( Dialog ):
    
    def __init__( self, parent, namespace = '', regex = '' ):
        
        Dialog.__init__( self, parent, 'configure quick namespace' )
        
        self._namespace = wx.TextCtrl( self )
        
        self._regex = wx.TextCtrl( self )
        
        self._shortcuts = ClientGUICommon.RegexButton( self )
        
        self._regex_intro_link = wx.HyperlinkCtrl( self, id = -1, label = 'a good regex introduction', url = 'http://www.aivosto.com/vbtips/regex.html' )
        self._regex_practise_link = wx.HyperlinkCtrl( self, id = -1, label = 'regex practise', url = 'http://regexr.com/3cvmf' )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
    
        self._namespace.SetValue( namespace )
        self._regex.SetValue( regex )
        
        #
        
        control_box = wx.BoxSizer( wx.HORIZONTAL )
        
        control_box.AddF( self._namespace, CC.FLAGS_EXPAND_BOTH_WAYS )
        control_box.AddF( wx.StaticText( self, label = ':' ), CC.FLAGS_VCENTER )
        control_box.AddF( self._regex, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        b_box = wx.BoxSizer( wx.HORIZONTAL )
        b_box.AddF( self._ok, CC.FLAGS_VCENTER )
        b_box.AddF( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        intro = r'Put the namespace (e.g. page) on the left.' + os.linesep + r'Put the regex (e.g. [1-9]+\d*(?=.{4}$)) on the right.' + os.linesep + r'All files will be tagged with "namespace:regex".'
        
        vbox.AddF( wx.StaticText( self, label = intro ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( control_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._shortcuts, CC.FLAGS_LONE_BUTTON )
        vbox.AddF( self._regex_intro_link, CC.FLAGS_LONE_BUTTON )
        vbox.AddF( self._regex_practise_link, CC.FLAGS_LONE_BUTTON )
        vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventOK( self, event ):
        
        ( namespace, regex ) = self.GetInfo()
        
        if namespace == '':
            
            wx.MessageBox( 'Please enter something for the namespace.' )
            
            return
            
        
        try:
            
            re.compile( regex, flags = re.UNICODE )
            
        except Exception as e:
            
            text = 'That regex would not compile!'
            text += os.linesep * 2
            text += HydrusData.ToUnicode( e )
            
            wx.MessageBox( text )
            
            return
            
        
        self.EndModal( wx.ID_OK )
        
    
    def GetInfo( self ):
        
        namespace = self._namespace.GetValue()
        
        regex = self._regex.GetValue()
        
        return ( namespace, regex )
        
    
class DialogInputNewFormField( Dialog ):
    
    def __init__( self, parent, form_field = None ):
        
        Dialog.__init__( self, parent, 'configure form field' )
        
        if form_field is None: ( name, field_type, default, editable ) = ( '', CC.FIELD_TEXT, '', True )
        else: ( name, field_type, default, editable ) = form_field
        
        self._name = wx.TextCtrl( self )
        
        self._type = wx.Choice( self )
        
        self._default = wx.TextCtrl( self )
        
        self._editable = wx.CheckBox( self )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )   
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        self._name.SetValue( name )
        
        for temp_type in CC.FIELDS: self._type.Append( CC.field_string_lookup[ temp_type ], temp_type )
        self._type.Select( field_type )
        
        self._default.SetValue( default )
        
        self._editable.SetValue( editable )
        
        #
        
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'type: ', self._type ) )
        rows.append( ( 'default: ', self._default ) )
        rows.append( ( 'editable: ', self._editable ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        b_box = wx.BoxSizer( wx.HORIZONTAL )
        
        b_box.AddF( self._ok, CC.FLAGS_VCENTER )
        b_box.AddF( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def GetFormField( self ):
        
        name = self._name.GetValue()
        
        field_type = self._type.GetClientData( self._type.GetSelection() )
        
        default = self._default.GetValue()
        
        editable = self._editable.GetValue()
        
        return ( name, field_type, default, editable )
        
    
class DialogInputShortcut( Dialog ):
    
    def __init__( self, parent, modifier = wx.ACCEL_NORMAL, key = wx.WXK_F7, action = 'new_page' ):
        
        Dialog.__init__( self, parent, 'configure shortcut' )
        
        self._action = action
        
        self._shortcut = ClientGUICommon.Shortcut( self, modifier, key )
        
        self._actions = wx.Choice( self, choices = [ 'archive', 'inbox', 'close_page', 'filter', 'fullscreen_switch', 'frame_back', 'frame_next', 'manage_ratings', 'manage_tags', 'new_page', 'unclose_page', 'refresh', 'set_media_focus', 'set_search_focus', 'show_hide_splitters', 'synchronised_wait_switch', 'next', 'first', 'last', 'undo', 'redo', 'open_externally', 'pan_up', 'pan_down', 'pan_left', 'pan_right', 'previous', 'remove', 'zoom_in', 'zoom_out', 'zoom_switch' ] )
        
        self._ok = wx.Button( self, id= wx.ID_OK, label = 'Ok' )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        self._actions.SetSelection( self._actions.FindString( action ) )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._shortcut, CC.FLAGS_VCENTER )
        hbox.AddF( self._actions, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        b_box = wx.BoxSizer( wx.HORIZONTAL )
        b_box.AddF( self._ok, CC.FLAGS_VCENTER )
        b_box.AddF( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def GetInfo( self ):
        
        ( modifier, key ) = self._shortcut.GetValue()
        
        return ( modifier, key, self._actions.GetStringSelection() )
        
    
class DialogInputTags( Dialog ):
    
    def __init__( self, parent, service_key, tags ):
        
        Dialog.__init__( self, parent, 'input tags' )
        
        self._service_key = service_key
        
        self._tags = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, service_key = service_key )
        
        expand_parents = True
        
        self._tag_box = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterTags, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, service_key, null_entry_callable = self.Ok )
        
        self._ok = wx.Button( self, id= wx.ID_OK, label = 'Ok' )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        self._tags.SetTags( tags )
        
        #
        
        b_box = wx.BoxSizer( wx.HORIZONTAL )
        
        b_box.AddF( self._ok, CC.FLAGS_VCENTER )
        b_box.AddF( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._tag_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 300 )
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._tag_box.SetFocus )
        

    def EnterTags( self, tags ):
        
        tag_parents_manager = HydrusGlobals.client_controller.GetManager( 'tag_parents' )
        
        parents = set()
        
        for tag in tags:
            
            some_parents = tag_parents_manager.GetParents( self._service_key, tag )
            
            parents.update( some_parents )
            
        
        if len( tags ) > 0:
            
            self._tags.EnterTags( tags )
            self._tags.AddTags( parents )
            
        
    
    def GetTags( self ):
        
        return self._tags.GetTags()
        
    
    def Ok( self ):
        
        self.EndModal( wx.ID_OK )
        
    
class DialogInputTimeDelta( Dialog ):
    
    def __init__( self, parent, initial_value, min = 1, days = False, hours = False, minutes = False, seconds = False, monthly_allowed = False ):
        
        Dialog.__init__( self, parent, 'input time delta' )
        
        self._time_delta = ClientGUICommon.TimeDeltaCtrl( self, min = min, days = days, hours = hours, minutes = minutes, seconds = seconds, monthly_allowed = monthly_allowed )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'Ok' )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        self._time_delta.SetValue( initial_value )
        
        #
        
        b_box = wx.BoxSizer( wx.HORIZONTAL )
        b_box.AddF( self._ok, CC.FLAGS_VCENTER )
        b_box.AddF( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._time_delta, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def GetValue( self ):
        
        return self._time_delta.GetValue()
        
    
class DialogInputUPnPMapping( Dialog ):
    
    def __init__( self, parent, external_port, protocol_type, internal_port, description, duration ):
        
        Dialog.__init__( self, parent, 'configure upnp mapping' )
        
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
        
        #
        
        self._external_port.SetValue( external_port )
        
        if protocol_type == 'TCP': self._protocol_type.Select( 0 )
        elif protocol_type == 'UDP': self._protocol_type.Select( 1 )
        
        self._internal_port.SetValue( internal_port )
        self._description.SetValue( description )
        self._duration.SetValue( duration )
        
        #
        
        rows = []
        
        rows.append( ( 'external port: ', self._external_port ) )
        rows.append( ( 'protocol type: ', self._protocol_type ) )
        rows.append( ( 'internal port: ', self._internal_port ) )
        rows.append( ( 'description: ', self._description ) )
        rows.append( ( 'duration (0 = indefinite): ', self._duration ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        b_box = wx.BoxSizer( wx.HORIZONTAL )
        b_box.AddF( self._ok, CC.FLAGS_VCENTER )
        b_box.AddF( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        vbox.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( x, y ) )
        
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
        
        Dialog.__init__( self, parent, 'modify account' )
        
        self._service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
        self._subject_identifiers = list( subject_identifiers )
        
        #
        
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
        
        #
        
        if len( self._subject_identifiers ) == 1:
            
            ( subject_identifier, ) = self._subject_identifiers
            
            response = self._service.Request( HC.GET, 'account_info', { 'subject_identifier' : subject_identifier } )
            
            subject_string = HydrusData.ToUnicode( response[ 'account_info' ] )
            
        else: subject_string = 'modifying ' + HydrusData.ConvertIntToPrettyString( len( self._subject_identifiers ) ) + ' accounts'
        
        self._subject_text.SetLabelText( subject_string )
        
        #
        
        response = self._service.Request( HC.GET, 'account_types' )
        
        account_types = response[ 'account_types' ]
        
        for account_type in account_types: self._account_types.Append( account_type.ConvertToString(), account_type )
        
        self._account_types.SetSelection( 0 )
        
        #
        
        for ( string, value ) in HC.lifetimes:
            
            if value is not None:
                
                self._add_to_expires.Append( string, value ) # don't want 'add no limit'
                
            
        
        self._add_to_expires.SetSelection( 1 ) # three months
        
        for ( string, value ) in HC.lifetimes: self._set_expires.Append( string, value )
        self._set_expires.SetSelection( 1 ) # three months
        
        #
        
        self._account_info_panel.AddF( self._subject_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        account_types_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        account_types_hbox.AddF( self._account_types, CC.FLAGS_VCENTER )
        account_types_hbox.AddF( self._account_types_ok, CC.FLAGS_VCENTER )
        
        self._account_types_panel.AddF( account_types_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        add_to_expires_box = wx.BoxSizer( wx.HORIZONTAL )
        
        add_to_expires_box.AddF( wx.StaticText( self._expiration_panel, label = 'add to expires: ' ), CC.FLAGS_VCENTER )
        add_to_expires_box.AddF( self._add_to_expires, CC.FLAGS_EXPAND_BOTH_WAYS )
        add_to_expires_box.AddF( self._add_to_expires_ok, CC.FLAGS_VCENTER )
        
        set_expires_box = wx.BoxSizer( wx.HORIZONTAL )
        
        set_expires_box.AddF( wx.StaticText( self._expiration_panel, label = 'set expires to: ' ), CC.FLAGS_VCENTER )
        set_expires_box.AddF( self._set_expires, CC.FLAGS_EXPAND_BOTH_WAYS )
        set_expires_box.AddF( self._set_expires_ok, CC.FLAGS_VCENTER )
        
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
        
        wx.CallAfter( self._exit.SetFocus )
        
    
    def _DoModification( self ):
        
        # change this to saveaccounts or whatever. the previous func changes the accounts, and then we push that change
        # generate accounts, with the modification having occured
        
        self._service.Request( HC.POST, 'account', { 'accounts' : self._accounts } )
        
        if len( self._subject_identifiers ) == 1:
            
            ( subject_identifier, ) = self._subject_identifiers
            
            response = self._service.Request( HC.GET, 'account_info', { 'subject_identifier' : subject_identifier } )
            
            account_info = response[ 'account_info' ]
            
            self._subject_text.SetLabelText( HydrusData.ToUnicode( account_info ) )
            
        
        if len( self._subject_identifiers ) > 1: wx.MessageBox( 'Done!' )
        
    
    def EventAddToExpires( self, event ):
        
        self._DoModification( HC.ADD_TO_EXPIRES, timespan = self._add_to_expires.GetClientData( self._add_to_expires.GetSelection() ) )
        
    
    def EventBan( self, event ):
        
        with DialogTextEntry( self, 'Enter reason for the ban.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK: self._DoModification( HC.BAN, reason = dlg.GetValue() )
            
        
    
    def EventChangeAccountType( self, event ):
        
        self._DoModification( HC.CHANGE_ACCOUNT_TYPE, account_type_key = self._account_types.GetChoice() )
        
    
    def EventSetExpires( self, event ):
        
        expires = self._set_expires.GetClientData( self._set_expires.GetSelection() )
        
        if expires is not None: expires += HydrusData.GetNow()
        
        self._DoModification( HC.SET_EXPIRES, expires = expires )
        
    
    def EventSuperban( self, event ):
        
        with DialogTextEntry( self, 'Enter reason for the superban.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK: self._DoModification( HC.SUPERBAN, reason = dlg.GetValue() )
            
        
    
class DialogPageChooser( Dialog ):
    
    def __init__( self, parent ):
        
        Dialog.__init__( self, parent, 'new page', position = 'center' )
        
        # spawn in this order, so focus precipitates from the graphical top
        
        self._button_7 = wx.Button( self, label = '', id = 7 )
        self._button_8 = wx.Button( self, label = '', id = 8 )
        self._button_9 = wx.Button( self, label = '', id = 9 )
        self._button_4 = wx.Button( self, label = '', id = 4 )
        self._button_5 = wx.Button( self, label = '', id = 5 )
        self._button_6 = wx.Button( self, label = '', id = 6 )
        self._button_1 = wx.Button( self, label = '', id = 1 )
        self._button_2 = wx.Button( self, label = '', id = 2 )
        self._button_3 = wx.Button( self, label = '', id = 3 )
        
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
        
        self._services = HydrusGlobals.client_controller.GetServicesManager().GetServices()
        
        repository_petition_permissions = [ ( content_type, HC.PERMISSION_ACTION_OVERRULE ) for content_type in HC.REPOSITORY_CONTENT_TYPES ]
        
        self._petition_service_keys = [ service.GetServiceKey() for service in self._services if service.GetServiceType() in HC.REPOSITORIES and True in ( service.HasPermission( content_type, action ) for ( content_type, action ) in repository_petition_permissions ) ]
        
        self._InitButtons( 'home' )
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        
        #
        
        self.Show( True )
        
    
    def _AddEntry( self, button, entry ):
        
        id = button.GetId()
        
        self._command_dict[ id ] = entry
        
        ( entry_type, obj ) = entry
        
        if entry_type == 'menu': button.SetLabelText( obj )
        elif entry_type in ( 'page_query', 'page_petitions' ):
            
            name = HydrusGlobals.client_controller.GetServicesManager().GetService( obj ).GetName()
            
            button.SetLabelText( name )
            
        elif entry_type == 'page_import_booru':
            
            button.SetLabelText( 'booru' )
            
        elif entry_type == 'page_import_gallery':
            
            site_type = obj
            
            text = HC.site_type_string_lookup[ site_type ]
            
            button.SetLabelText( text )
            
        elif entry_type == 'page_import_page_of_images': button.SetLabelText( 'page of images' )
        elif entry_type == 'page_import_thread_watcher': button.SetLabelText( 'thread watcher' )
        elif entry_type == 'page_import_urls': button.SetLabelText( 'raw urls' )
        
        button.Show()
        
    
    def _HitButton( self, id ):
        
        if id in self._command_dict:
            
            ( entry_type, obj ) = self._command_dict[ id ]
            
            if entry_type == 'menu':
                
                self._InitButtons( obj )
                
            else:
                
                if entry_type == 'page_query': 
                    
                    HydrusGlobals.client_controller.pub( 'new_page_query', obj )
                    
                elif entry_type == 'page_import_booru':
                    
                    HydrusGlobals.client_controller.pub( 'new_import_booru' )
                    
                elif entry_type == 'page_import_gallery':
                    
                    site_type = obj
                    
                    HydrusGlobals.client_controller.pub( 'new_import_gallery', site_type )
                    
                elif entry_type == 'page_import_page_of_images':
                    
                    HydrusGlobals.client_controller.pub( 'new_page_import_page_of_images' )
                    
                elif entry_type == 'page_import_thread_watcher':
                    
                    HydrusGlobals.client_controller.pub( 'new_page_import_thread_watcher' )
                    
                elif entry_type == 'page_import_urls':
                    
                    HydrusGlobals.client_controller.pub( 'new_page_import_urls' )
                    
                elif entry_type == 'page_petitions':
                    
                    HydrusGlobals.client_controller.pub( 'new_page_petitions', obj )
                    
                
                self.EndModal( wx.ID_OK )
                
            
        
    
    def _InitButtons( self, menu_keyword ):
        
        self._command_dict = {}
        
        entries = []
        
        if menu_keyword == 'home':
            
            entries.append( ( 'menu', 'files' ) )
            entries.append( ( 'menu', 'download' ) )
            
            if len( self._petition_service_keys ) > 0:
                
                entries.append( ( 'menu', 'petitions' ) )
                
            
        elif menu_keyword == 'files':
            
            file_repos = [ ( 'page_query', service_key ) for service_key in [ service.GetServiceKey() for service in self._services if service.GetServiceType() == HC.FILE_REPOSITORY ] ]
            
            entries.append( ( 'page_query', CC.LOCAL_FILE_SERVICE_KEY ) )
            entries.append( ( 'page_query', CC.TRASH_SERVICE_KEY ) )
            entries.append( ( 'page_query', CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
            
            for service in self._services:
                
                if service.GetServiceType() == HC.FILE_REPOSITORY:
                    
                    entries.append( ( 'page_query', service.GetServiceKey() ) )
                    
                
            
        elif menu_keyword == 'download':
            
            entries.append( ( 'page_import_urls', None ) )
            entries.append( ( 'page_import_thread_watcher', None ) )
            entries.append( ( 'menu', 'gallery' ) )
            entries.append( ( 'page_import_page_of_images', None ) )
            
        elif menu_keyword == 'gallery':
            
            entries.append( ( 'page_import_booru', None ) )
            entries.append( ( 'page_import_gallery', HC.SITE_TYPE_DEVIANT_ART ) )
            entries.append( ( 'menu', 'hentai foundry' ) )
            entries.append( ( 'page_import_gallery', HC.SITE_TYPE_NEWGROUNDS ) )
            
            result = HydrusGlobals.client_controller.Read( 'serialisable_simple', 'pixiv_account' )
            
            if result is not None:
                
                entries.append( ( 'menu', 'pixiv' ) )
                
            
            entries.append( ( 'page_import_gallery', HC.SITE_TYPE_TUMBLR ) )
            
        elif menu_keyword == 'hentai foundry':
            
            entries.append( ( 'page_import_gallery', HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST ) )
            entries.append( ( 'page_import_gallery', HC.SITE_TYPE_HENTAI_FOUNDRY_TAGS ) )
            
        elif menu_keyword == 'pixiv':
            
            entries.append( ( 'page_import_gallery', HC.SITE_TYPE_PIXIV_ARTIST_ID ) )
            entries.append( ( 'page_import_gallery', HC.SITE_TYPE_PIXIV_TAG ) )
            
        elif menu_keyword == 'petitions':
            
            entries = [ ( 'page_petitions', service_key ) for service_key in self._petition_service_keys ]
            
        
        if len( entries ) <= 4:
            
            self._button_1.Hide()
            self._button_3.Hide()
            self._button_5.Hide()
            self._button_7.Hide()
            self._button_9.Hide()
            
            potential_buttons = [ self._button_8, self._button_4, self._button_6, self._button_2 ]
            
        elif len( entries ) <= 9:
            
            potential_buttons = [ self._button_7, self._button_8, self._button_9, self._button_4, self._button_5, self._button_6, self._button_1, self._button_2, self._button_3 ]
            
        else:
            
            # sort out a multi-page solution? maybe only if this becomes a big thing; the person can always select from the menus, yeah?
            
            potential_buttons = [ self._button_7, self._button_8, self._button_9, self._button_4, self._button_5, self._button_6, self._button_1, self._button_2, self._button_3 ]
            entries = entries[:9]
            
        
        for entry in entries: self._AddEntry( potential_buttons.pop( 0 ), entry )
        
        unused_buttons = potential_buttons
        
        for button in unused_buttons: button.Hide()
        
    
    def EventButton( self, event ):
        
        id = event.GetId()
        
        if id == wx.ID_CANCEL:
            
            self.EndModal( wx.ID_CANCEL )
            
        else:
            
            self._HitButton( id )
            
        
    
    def EventCharHook( self, event ):
        
        id = None
        
        kc = event.KeyCode
        
        if kc == wx.WXK_UP: id = 8
        elif kc == wx.WXK_LEFT: id = 4
        elif kc == wx.WXK_RIGHT: id = 6
        elif kc == wx.WXK_DOWN: id = 2
        elif kc == wx.WXK_NUMPAD1: id = 1
        elif kc == wx.WXK_NUMPAD2: id = 2
        elif kc == wx.WXK_NUMPAD3: id = 3
        elif kc == wx.WXK_NUMPAD4: id = 4
        elif kc == wx.WXK_NUMPAD5: id = 5
        elif kc == wx.WXK_NUMPAD6: id = 6
        elif kc == wx.WXK_NUMPAD7: id = 7
        elif kc == wx.WXK_NUMPAD8: id = 8
        elif kc == wx.WXK_NUMPAD9: id = 9
        elif kc == wx.WXK_ESCAPE:
            
            self.EndModal( wx.ID_CANCEL )
            
            return
            
        else:
            
            event.Skip()
            
        
        if id is not None:
            
            self._HitButton( id )
            
        
    
class DialogPathsToTags( Dialog ):
    
    def __init__( self, parent, paths ):
        
        Dialog.__init__( self, parent, 'path tagging' )
        
        self._paths = paths
        
        self._tag_repositories = ClientGUICommon.ListBook( self )
        
        self._add_button = wx.Button( self, id = wx.ID_OK, label = 'Import Files' )
        self._add_button.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Back to File Selection' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.TAG_REPOSITORY, ) )
        
        for service in services:
            
            if service.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_CREATE ):
                
                service_key = service.GetServiceKey()
                
                name = service.GetName()
                
                self._tag_repositories.AddPageArgs( name, service_key, self._Panel, ( self._tag_repositories, service_key, paths ), {} )
                
            
        
        page = self._Panel( self._tag_repositories, CC.LOCAL_TAG_SERVICE_KEY, paths )
        
        name = CC.LOCAL_TAG_SERVICE_KEY
        
        self._tag_repositories.AddPage( name, name, page )
        
        default_tag_repository_key = HC.options[ 'default_tag_repository' ]
        
        self._tag_repositories.Select( default_tag_repository_key )
        
        #
        
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
        
    
    def GetInfo( self ):
        
        paths_to_tags = collections.defaultdict( dict )
        
        for page in self._tag_repositories.GetActivePages():
            
            ( service_key, page_of_paths_to_tags ) = page.GetInfo()
            
            for ( path, tags ) in page_of_paths_to_tags.items(): paths_to_tags[ path ][ service_key ] = tags
            
        
        return paths_to_tags
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, service_key, paths ):
            
            wx.Panel.__init__( self, parent )
            
            self._service_key = service_key
            self._paths = paths
            
            self._paths_list = ClientGUICommon.SaneListCtrl( self, 250, [ ( '#', 50 ), ( 'path', 400 ), ( 'tags', -1 ) ] )
            
            self._paths_list.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventItemSelected )
            self._paths_list.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventItemSelected )
            
            #
            
            self._notebook = wx.Notebook( self )
            
            self._simple_panel = self._SimplePanel( self._notebook, self._service_key, self.RefreshFileList )
            self._advanced_panel = self._AdvancedPanel( self._notebook, self._service_key, self.RefreshFileList )
            
            self._notebook.AddPage( self._simple_panel, 'simple', select = True )
            self._notebook.AddPage( self._advanced_panel, 'advanced' )
            
            #
            
            for ( index, path ) in enumerate( self._paths ):
                
                pretty_num = HydrusData.ConvertIntToPrettyString( index + 1 )
                
                tags = self._GetTags( index, path )
                
                tags_string = ', '.join( tags )
                
                self._paths_list.Append( ( pretty_num, path, tags_string ), ( index, path, tags ) )
                
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._paths_list, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.SetSizer( vbox )
            
        
        
        def _GetTags( self, index, path ):
            
            tags = []
            
            tags.extend( self._simple_panel.GetTags( index, path ) )
            tags.extend( self._advanced_panel.GetTags( index, path ) )
            
            tags = HydrusTags.CleanTags( tags )
            
            siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
            parents_manager = HydrusGlobals.client_controller.GetManager( 'tag_parents' )
            
            tags = siblings_manager.CollapseTags( self._service_key, tags )
            tags = parents_manager.ExpandTags( self._service_key, tags )
            
            tags = list( tags )
            
            tags.sort()
            
            return tags
            
        
        def EventItemSelected( self, event ):
            
            paths = [ path for ( index, path, tags ) in self._paths_list.GetSelectedClientData() ]
            
            self._simple_panel.SetSelectedPaths( paths )
            
        
        def GetInfo( self ):
            
            paths_to_tags = { path : tags for ( index, path, tags ) in self._paths_list.GetClientData() }
            
            return ( self._service_key, paths_to_tags )
            
        
        def RefreshFileList( self ):
            
            for ( list_index, ( index, path, old_tags ) ) in enumerate( self._paths_list.GetClientData() ):
                
                # when doing regexes, make sure not to include '' results, same for system: and - started tags.
                
                tags = self._GetTags( index, path )
                
                if tags != old_tags:
                    
                    pretty_num = HydrusData.ConvertIntToPrettyString( index + 1 )
                    
                    tags_string = ', '.join( tags )
                    
                    self._paths_list.UpdateRow( list_index, ( pretty_num, path, tags_string ), ( index, path, tags ) )
                    
                
            
        
        def SetTagBoxFocus( self ):
            
            self._simple_panel._tag_box.SetFocus()
            
        
        class _AdvancedPanel( wx.Panel ):
            
            def __init__( self, parent, service_key, refresh_callable ):
                
                wx.Panel.__init__( self, parent )
                
                self._service_key = service_key
                self._refresh_callable = refresh_callable
                
                #
                
                self._quick_namespaces_panel = ClientGUICommon.StaticBox( self, 'quick namespaces' )
                
                self._quick_namespaces_list = ClientGUICommon.SaneListCtrl( self._quick_namespaces_panel, 200, [ ( 'namespace', 80 ), ( 'regex', -1 ) ], delete_key_callback = self.DeleteQuickNamespaces, activation_callback = self.EditQuickNamespaces )
                
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
                
                self._regex_intro_link = wx.HyperlinkCtrl( self._regexes_panel, id = -1, label = 'a good regex introduction', url = 'http://www.aivosto.com/vbtips/regex.html' )
                self._regex_practise_link = wx.HyperlinkCtrl( self._regexes_panel, id = -1, label = 'regex practise', url = 'http://regexr.com/3cvmf' )
                
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
                self._regexes_panel.AddF( self._regex_intro_link, CC.FLAGS_LONE_BUTTON )
                self._regexes_panel.AddF( self._regex_practise_link, CC.FLAGS_LONE_BUTTON )
                
                #
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self._num_panel, label = '# base/step: ' ), CC.FLAGS_VCENTER )
                hbox.AddF( self._num_base, CC.FLAGS_VCENTER )
                hbox.AddF( self._num_step, CC.FLAGS_VCENTER )
                
                self._num_panel.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( wx.StaticText( self._num_panel, label = '# namespace: ' ), CC.FLAGS_VCENTER )
                hbox.AddF( self._num_namespace, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                self._num_panel.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                second_vbox = wx.BoxSizer( wx.VERTICAL )
                
                second_vbox.AddF( self._regexes_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                second_vbox.AddF( self._num_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                #
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( self._quick_namespaces_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                hbox.AddF( second_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
                
                self.SetSizer( hbox )
                
            
            def DeleteQuickNamespaces( self ):
                
                with DialogYesNo( self, 'Remove all selected?' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        self._quick_namespaces_list.RemoveAllSelected()
                        
                        self._refresh_callable()
                        
                    
                
            
            def EditQuickNamespaces( self ):
                
                for index in self._quick_namespaces_list.GetAllSelected():
                    
                    ( namespace, regex ) = self._quick_namespaces_list.GetClientData( index = index )
                    
                    with DialogInputNamespaceRegex( self, namespace = namespace, regex = regex ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            ( namespace, regex ) = dlg.GetInfo()
                            
                            self._quick_namespaces_list.UpdateRow( index, ( namespace, regex ), ( namespace, regex ) )
                            
                        
                    
                
                self._refresh_callable()
                
            
            def EventAddRegex( self, event ):
                
                regex = self._regex_box.GetValue()
                
                if regex != '':
                    
                    try:
                        
                        re.compile( regex, flags = re.UNICODE )
                        
                    except Exception as e:
                        
                        text = 'That regex would not compile!'
                        text += os.linesep * 2
                        text += HydrusData.ToUnicode( e )
                        
                        wx.MessageBox( text )
                        
                        return
                        
                    
                    self._regexes.Append( regex )
                    
                    self._regex_box.Clear()
                    
                    self._refresh_callable()
                    
                
            
            def EventAddQuickNamespace( self, event ):
                
                with DialogInputNamespaceRegex( self ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        ( namespace, regex ) = dlg.GetInfo()
                        
                        self._quick_namespaces_list.Append( ( namespace, regex ), ( namespace, regex ) )
                        
                        self._refresh_callable()
                        
                    
                
            
            def EventDeleteQuickNamespace( self, event ):
                
                self.DeleteQuickNamespaces()
                
            
            def EventEditQuickNamespace( self, event ):
                
                self.EditQuickNamespaces()
                
            
            def EventNumNamespaceChanged( self, event ):
                
                self._refresh_callable()
                
            
            def EventRecalcNum( self, event ):
                
                self._refresh_callable()
                
            
            def EventRemoveRegex( self, event ):
                
                selection = self._regexes.GetSelection()
                
                if selection != wx.NOT_FOUND:
                    
                    if len( self._regex_box.GetValue() ) == 0: self._regex_box.SetValue( self._regexes.GetString( selection ) )
                    
                    self._regexes.Delete( selection )
                    
                    self._refresh_callable()
                    
                
            
            def GetTags( self, index, path ):
                
                tags = []
                
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
                    
                
                num_namespace = self._num_namespace.GetValue()
                
                if num_namespace != '':
                    
                    num_base = self._num_base.GetValue()
                    num_step = self._num_step.GetValue()
                    
                    tag_num = num_base + index * num_step
                    
                    tags.append( num_namespace + ':' + str( tag_num ) )
                    
                
                return tags
                
            
        
        class _SimplePanel( wx.Panel ):
            
            def __init__( self, parent, service_key, refresh_callable ):
                
                wx.Panel.__init__( self, parent )
                
                self._service_key = service_key
                self._refresh_callable = refresh_callable
                
                #
                
                self._tags_panel = ClientGUICommon.StaticBox( self, 'tags for all' )
                
                self._tags = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self._tags_panel, self._service_key, self.TagsRemoved )
                
                expand_parents = True
                
                self._tag_box = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self._tags_panel, self.EnterTags, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, service_key )
                
                #
                
                self._single_tags_panel = ClientGUICommon.StaticBox( self, 'tags just for selected files' )
                
                self._paths_to_single_tags = collections.defaultdict( set )
                
                self._single_tags = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self._single_tags_panel, self._service_key, self.SingleTagsRemoved )
                
                expand_parents = True
                
                self._single_tag_box = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self._single_tags_panel, self.EnterTagsSingle, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, service_key )
                
                self.SetSelectedPaths( [] )
                
                #
                
                self._checkboxes_panel = ClientGUICommon.StaticBox( self, 'misc' )
                
                self._load_from_txt_files_checkbox = wx.CheckBox( self._checkboxes_panel, label = 'try to load tags from neighbouring .txt files' )
                self._load_from_txt_files_checkbox.SetToolTipString( 'This looks for a [path].txt file, and will try to load line-separated tags from it. Look at thumbnail->share->export->files\'s txt file checkbox for an example.' )
                self._load_from_txt_files_checkbox.Bind( wx.EVT_CHECKBOX, self.EventRefresh )
                
                self._filename_namespace = wx.TextCtrl( self._checkboxes_panel )
                self._filename_namespace.Bind( wx.EVT_TEXT, self.EventRefresh )
                
                self._filename_checkbox = wx.CheckBox( self._checkboxes_panel, label = 'add filename? [namespace]' )
                self._filename_checkbox.Bind( wx.EVT_CHECKBOX, self.EventRefresh )
                
                self._dir_namespace_1 = wx.TextCtrl( self._checkboxes_panel )
                self._dir_namespace_1.Bind( wx.EVT_TEXT, self.EventRefresh )
                
                self._dir_checkbox_1 = wx.CheckBox( self._checkboxes_panel, label = 'add first directory? [namespace]' )
                self._dir_checkbox_1.Bind( wx.EVT_CHECKBOX, self.EventRefresh )
                
                self._dir_namespace_2 = wx.TextCtrl( self._checkboxes_panel )
                self._dir_namespace_2.Bind( wx.EVT_TEXT, self.EventRefresh )
                
                self._dir_checkbox_2 = wx.CheckBox( self._checkboxes_panel, label = 'add second directory? [namespace]' )
                self._dir_checkbox_2.Bind( wx.EVT_CHECKBOX, self.EventRefresh )
                
                self._dir_namespace_3 = wx.TextCtrl( self._checkboxes_panel )
                self._dir_namespace_3.Bind( wx.EVT_TEXT, self.EventRefresh )
                
                self._dir_checkbox_3 = wx.CheckBox( self._checkboxes_panel, label = 'add third directory? [namespace]' )
                self._dir_checkbox_3.Bind( wx.EVT_CHECKBOX, self.EventRefresh )
                
                #
                
                self._tags_panel.AddF( self._tags, CC.FLAGS_EXPAND_BOTH_WAYS )
                self._tags_panel.AddF( self._tag_box, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                self._single_tags_panel.AddF( self._single_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
                self._single_tags_panel.AddF( self._single_tag_box, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                filename_hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                filename_hbox.AddF( self._filename_checkbox, CC.FLAGS_EXPAND_BOTH_WAYS )
                filename_hbox.AddF( self._filename_namespace, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                dir_hbox_1 = wx.BoxSizer( wx.HORIZONTAL )
                
                dir_hbox_1.AddF( self._dir_checkbox_1, CC.FLAGS_EXPAND_BOTH_WAYS )
                dir_hbox_1.AddF( self._dir_namespace_1, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                dir_hbox_2 = wx.BoxSizer( wx.HORIZONTAL )
                
                dir_hbox_2.AddF( self._dir_checkbox_2, CC.FLAGS_EXPAND_BOTH_WAYS )
                dir_hbox_2.AddF( self._dir_namespace_2, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                dir_hbox_3 = wx.BoxSizer( wx.HORIZONTAL )
                
                dir_hbox_3.AddF( self._dir_checkbox_3, CC.FLAGS_EXPAND_BOTH_WAYS )
                dir_hbox_3.AddF( self._dir_namespace_3, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                self._checkboxes_panel.AddF( self._load_from_txt_files_checkbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._checkboxes_panel.AddF( filename_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                self._checkboxes_panel.AddF( dir_hbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                self._checkboxes_panel.AddF( dir_hbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                self._checkboxes_panel.AddF( dir_hbox_3, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( self._tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                hbox.AddF( self._single_tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                hbox.AddF( self._checkboxes_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                self.SetSizer( hbox )
                
            
            def EnterTags( self, tags ):
                
                tag_parents_manager = HydrusGlobals.client_controller.GetManager( 'tag_parents' )
                
                parents = set()
                
                for tag in tags:
                    
                    some_parents = tag_parents_manager.GetParents( self._service_key, tag )
                    
                    parents.update( some_parents )
                    
                
                if len( tags ) > 0:
                    
                    self._tags.AddTags( tags )
                    self._tags.AddTags( parents )
                    
                    self._refresh_callable()
                    
                
            
            def EnterTagsSingle( self, tags ):
                
                tag_parents_manager = HydrusGlobals.client_controller.GetManager( 'tag_parents' )
                
                parents = set()
                
                for tag in tags:
                    
                    some_parents = tag_parents_manager.GetParents( self._service_key, tag )
                    
                    parents.update( some_parents )
                    
                
                if len( tags ) > 0:
                    
                    self._single_tags.AddTags( tags )
                    self._single_tags.AddTags( parents )
                    
                    for path in self._selected_paths:
                        
                        current_tags = self._paths_to_single_tags[ path ]
                        
                        current_tags.update( tags )
                        current_tags.update( parents )
                        
                    
                    self._refresh_callable()
                    
                
            
            def EventRefresh( self, event ):
                
                self._refresh_callable()
                
            
            def GetTags( self, index, path ):
                
                tags = []
                
                tags.extend( self._tags.GetTags() )
                
                if path in self._paths_to_single_tags:
                    
                    tags.extend( list( self._paths_to_single_tags[ path ] ) )
                    
                
                if self._load_from_txt_files_checkbox.IsChecked():
                    
                    txt_path = path + '.txt'
                    
                    if os.path.exists( txt_path ):
                        
                        with open( txt_path, 'rb' ) as f:
                            
                            txt_tags_string = f.read()
                            
                        
                        try:
                            
                            txt_tags = [ HydrusData.ToUnicode( tag ) for tag in HydrusData.SplitByLinesep( txt_tags_string ) ]
                            
                            tags.extend( txt_tags )
                            
                        except:
                            
                            HydrusData.Print( 'Could not parse the tags from ' + txt_path + '!' )
                            
                        
                    
                
                ( base, filename ) = os.path.split( path )
                
                ( filename, any_ext_gumpf ) = os.path.splitext( filename )
                
                if self._filename_checkbox.IsChecked():
                    
                    namespace = self._filename_namespace.GetValue()
                    
                    if namespace != '':
                        
                        tag = namespace + ':' + filename
                        
                    else:
                        
                        tag = filename
                        
                    
                    tags.append( tag )
                    
                
                ( drive, dirs ) = os.path.splitdrive( base )
                
                while dirs.startswith( os.path.sep ):
                    
                    dirs = dirs[1:]
                    
                
                dirs = dirs.split( os.path.sep )
                
                if len( dirs ) > 0 and self._dir_checkbox_1.IsChecked():
                    
                    namespace = self._dir_namespace_1.GetValue()
                    
                    if namespace != '':
                        
                        tag = namespace + ':' + dirs[0]
                        
                    else:
                        
                        tag = dirs[0]
                        
                    
                    tags.append( tag )
                    
                
                if len( dirs ) > 1 and self._dir_checkbox_2.IsChecked():
                    
                    namespace = self._dir_namespace_2.GetValue()
                    
                    if namespace != '':
                        
                        tag = namespace + ':' + dirs[1]
                        
                    else:
                        
                        tag = dirs[1]
                        
                    
                    tags.append( tag )
                    
                
                if len( dirs ) > 2 and self._dir_checkbox_3.IsChecked():
                    
                    namespace = self._dir_namespace_3.GetValue()
                    
                    if namespace != '':
                        
                        tag = namespace + ':' + dirs[2]
                        
                    else:
                        
                        tag = dirs[2]
                        
                    
                    tags.append( tag )
                    
                
                return tags
                
            
            def SingleTagsRemoved( self, tags ):
                
                for path in self._selected_paths:
                    
                    current_tags = self._paths_to_single_tags[ path ]
                    
                    current_tags.difference_update( tags )
                    
                
                self._refresh_callable()
                
            
            def SetSelectedPaths( self, paths ):
                
                self._selected_paths = paths
                
                single_tags = set()
                
                if len( paths ) > 0:
                    
                    for path in self._selected_paths:
                        
                        if path in self._paths_to_single_tags:
                            
                            single_tags.update( self._paths_to_single_tags[ path ] )
                            
                        
                    
                    self._single_tag_box.Enable()
                    
                else:
                    
                    self._single_tag_box.Disable()
                    
                
                self._single_tags.SetTags( single_tags )
                
            
            def TagsRemoved( self, tag ):
                
                self._refresh_callable()
                
            
        
    
class DialogSelectBooru( Dialog ):
    
    def __init__( self, parent ):
        
        Dialog.__init__( self, parent, 'select booru' )
        
        self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
        
        self._boorus = wx.ListBox( self )
        self._boorus.Bind( wx.EVT_LISTBOX_DCLICK, self.EventDoubleClick )
        
        self._ok = wx.Button( self, id = wx.ID_OK, size = ( 0, 0 ) )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetDefault()
        
        #
        
        boorus = HydrusGlobals.client_controller.Read( 'remote_boorus' )
        
        booru_names = boorus.keys()
        
        booru_names.sort()
        
        for name in booru_names:
            
            self._boorus.Append( name )
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._boorus, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 320 )
        y = max( y, 320 )
        
        self.SetInitialSize( ( x, y ) )
        
        if len( boorus ) == 1:
            
            self._boorus.Select( 0 )
            
            wx.CallAfter( self.EventOK, None )
            
        else:
            
            wx.CallAfter( self._ok.SetFocus )
            
        
    
    def EventDoubleClick( self, event ): self.EndModal( wx.ID_OK )
    
    def EventOK( self, event ):
    
        selection = self._boorus.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            self.EndModal( wx.ID_OK )
            
        
    
    def GetGalleryIdentifier( self ):
        
        name = self._boorus.GetString( self._boorus.GetSelection() )
        
        gallery_identifier = ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_BOORU, additional_info = name )
        
        return gallery_identifier
        
    
class DialogSelectFromURLTree( Dialog ):
    
    def __init__( self, parent, url_tree ):
        
        Dialog.__init__( self, parent, 'select items' )
        
        agwStyle = wx.lib.agw.customtreectrl.TR_DEFAULT_STYLE | wx.lib.agw.customtreectrl.TR_AUTO_CHECK_CHILD
        
        self._tree = wx.lib.agw.customtreectrl.CustomTreeCtrl( self, agwStyle = agwStyle )
        
        self._ok = wx.Button( self, id = wx.ID_OK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        ( text_gumpf, name, size, children ) = url_tree
        
        root_name = self._RenderItemName( name, size )
        
        root_item = self._tree.AddRoot( root_name, ct_type = 1 )
        
        self._AddDirectory( root_item, children )
        
        self._tree.CheckItem( root_item )
        
        self._tree.Expand( root_item )
        
        #
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.AddF( self._ok, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._tree, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 640 )
        y = max( y, 640 )
        
        self.SetInitialSize( ( x, y ) )
        
    
    def _AddDirectory( self, root, children ):
        
        for ( child_type, name, size, data ) in children:
            
            item_name = self._RenderItemName( name, size )
            
            if child_type == 'file':
                
                self._tree.AppendItem( root, item_name, ct_type = 1, data = data )
                
            else:
                
                subroot = self._tree.AppendItem( root, item_name, ct_type = 1 )
                
                self._AddDirectory( subroot, data )
                
            
        
    
    def _GetSelectedChildrenData( self, parent_item ):
        
        result = []
        
        cookie = 0
        
        ( child_item, cookie ) = self._tree.GetNextChild( parent_item, cookie )
        
        while child_item is not None:
            
            data = self._tree.GetItemPyData( child_item )
            
            if data is None:
                
                result.extend( self._GetSelectedChildrenData( child_item ) )
                
            else:
                
                if self._tree.IsItemChecked( child_item ):
                    
                    result.append( data )
                    
                
            
            ( child_item, cookie ) = self._tree.GetNextChild( parent_item, cookie )
            
        
        return result
        
    
    def _RenderItemName( self, name, size ):
        
        return name + ' - ' + HydrusData.ConvertIntToBytes( size )
        
    
    def GetURLs( self ):
        
        root_item = self._tree.GetRootItem()
        
        urls = self._GetSelectedChildrenData( root_item )
        
        return urls
        
    
    
class DialogSelectImageboard( Dialog ):
    
    def __init__( self, parent ):
        
        Dialog.__init__( self, parent, 'select imageboard' )
        
        self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
        
        self._tree = wx.TreeCtrl( self )
        self._tree.Bind( wx.EVT_TREE_ITEM_ACTIVATED, self.EventActivate )
        
        #
        
        all_imageboards = HydrusGlobals.client_controller.Read( 'imageboards' )
        
        root_item = self._tree.AddRoot( 'all sites' )
        
        for ( site, imageboards ) in all_imageboards.items():
            
            site_item = self._tree.AppendItem( root_item, site )
            
            for imageboard in imageboards:
                
                name = imageboard.GetName()
                
                self._tree.AppendItem( site_item, name, data = wx.TreeItemData( imageboard ) )
                
            
        
        self._tree.Expand( root_item )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._tree, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        if x < 320: x = 320
        if y < 640: y = 640
        
        self.SetInitialSize( ( x, y ) )
        
    
    def EventActivate( self, event ):
        
        item = self._tree.GetSelection()
        
        data_object = self._tree.GetItemData( item )
        
        if data_object is None: self._tree.Toggle( item )
        else: self.EndModal( wx.ID_OK )
        
    
    def GetImageboard( self ): return self._tree.GetItemData( self._tree.GetSelection() ).GetData()
    
class DialogCheckFromListOfStrings( Dialog ):
    
    def __init__( self, parent, title, list_of_strings, checked_strings = None ):
        
        Dialog.__init__( self, parent, title )
        
        if checked_strings is None: checked_strings = []
        
        self._strings = wx.CheckListBox( self )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        
        for s in list_of_strings: self._strings.Append( s )
        
        for s in checked_strings:
            
            i = self._strings.FindString( s )
            
            if i != wx.NOT_FOUND: self._strings.Check( i, True )
            
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._ok, CC.FLAGS_VCENTER )
        hbox.AddF( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._strings, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        if x < 320: x = 320
        
        self.SetInitialSize( ( x, y ) )
        
    
    def GetChecked( self ): return self._strings.GetCheckedStrings()
    
class DialogSelectFromList( Dialog ):
    
    def __init__( self, parent, title, list_of_tuples ):
        
        Dialog.__init__( self, parent, title )
        
        self._list = wx.ListBox( self )
        self._list.Bind( wx.EVT_KEY_DOWN, self.EventListKeyDown )
        self._list.Bind( wx.EVT_LISTBOX_DCLICK, self.EventSelect )
        
        list_of_tuples.sort()
        
        for ( label, value ) in list_of_tuples:
            
            self._list.Append( label, value )
            
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 320 )
        y = max( y, 320 )
        
        self.SetInitialSize( ( x, y ) )
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
    
    def EventCharHook( self, event ):
        
        if event.KeyCode == wx.WXK_ESCAPE:
            
            self.EndModal( wx.ID_CANCEL )
            
        else:
            
            event.Skip()
            
        
    
    def EventListKeyDown( self, event ):
        
        if event.KeyCode in ( wx.WXK_SPACE, wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            selection = self._list.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                self.EndModal( wx.ID_OK )
                
            
        else:
            
            event.Skip()
            
        
    
    def EventSelect( self, event ):
        
        self.EndModal( wx.ID_OK )
        
    
    def GetChoice( self ):
        
        selection = self._list.GetSelection()
        
        return self._list.GetClientData( selection )
        
    
class DialogSelectYoutubeURL( Dialog ):
    
    def __init__( self, parent, info ):
        
        Dialog.__init__( self, parent, 'choose youtube format' )
        
        self._info = info
        
        self._urls = ClientGUICommon.SaneListCtrl( self, 360, [ ( 'format', 150 ), ( 'resolution', -1 ) ] )
        self._urls.Bind( wx.EVT_LIST_ITEM_ACTIVATED, self.EventOK )
        
        self._urls.SetMinSize( ( 360, 200 ) )
        
        self._ok = wx.Button( self, wx.ID_OK, label = 'ok' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        for ( extension, resolution ) in self._info: self._urls.Append( ( extension, resolution ), ( extension, resolution ) )
        
        self._urls.SortListItems( 0 )
        
        #
        
        buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        buttons.AddF( self._ok, CC.FLAGS_VCENTER )
        buttons.AddF( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._urls, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventOK( self, event ):
        
        indices = self._urls.GetAllSelected()
        
        if len( indices ) > 0:
            
            for index in indices:
                
                ( extension, resolution ) = self._urls.GetClientData( index )
                
                ( url, title ) = self._info[ ( extension, resolution ) ]
                
                url_string = title + ' ' + resolution + ' ' + extension
                
                job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
                
                HydrusGlobals.client_controller.CallToThread( ClientDownloading.THREADDownloadURL, job_key, url, url_string )
                
                HydrusGlobals.client_controller.pub( 'message', job_key )
                
            
        
        self.EndModal( wx.ID_OK )
        
    
class DialogSetupExport( Dialog ):
    
    def __init__( self, parent, flat_media ):
        
        Dialog.__init__( self, parent, 'setup export' )
        
        self._tags_box = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'files\' tags' )
        
        self._tag_txt_tag_services = []
        
        t = ClientGUIListBoxes.ListBoxTagsSelection( self._tags_box, include_counts = True, collapse_siblings = True )
        
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
        
        self._filenames_box = ClientGUICommon.StaticBox( self, 'filenames' )
        
        self._pattern = wx.TextCtrl( self._filenames_box )
        
        self._update = wx.Button( self._filenames_box, label = 'update' )
        self._update.Bind( wx.EVT_BUTTON, self.EventRecalcPaths )
        
        self._examples = ClientGUICommon.ExportPatternButton( self._filenames_box )
        
        text = 'This will export all the files\' tags, newline separated, into .txts beside the files themselves.'
        
        self._export_tag_txts = wx.CheckBox( self, label = 'export tags in .txt files?' )
        self._export_tag_txts.SetToolTipString( text )
        self._export_tag_txts.Bind( wx.EVT_CHECKBOX, self.EventExportTagTxtsChanged )
        
        self._export = wx.Button( self, label = 'export' )
        self._export.Bind( wx.EVT_BUTTON, self.EventExport )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'close' )
        
        #
        
        for ( i, media ) in enumerate( flat_media ):
            
            mime = media.GetMime()
            
            display_tuple = ( str( i + 1 ), HC.mime_string_lookup[ mime ], '' )
            sort_tuple = ( ( i, media ), mime, '' )
            
            self._paths.Append( display_tuple, sort_tuple )
            
        
        export_path = ClientExporting.GetExportPath()
        
        self._directory_picker.SetPath( export_path )
        
        new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        phrase = new_options.GetString( 'export_phrase' )
        
        self._pattern.SetValue( phrase )
        
        #
        
        top_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        top_hbox.AddF( self._tags_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        top_hbox.AddF( self._paths, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._directory_picker, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.AddF( self._open_location, CC.FLAGS_VCENTER )
        
        self._export_path_box.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._pattern, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.AddF( self._update, CC.FLAGS_VCENTER )
        hbox.AddF( self._examples, CC.FLAGS_VCENTER )
        
        self._filenames_box.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( top_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        vbox.AddF( self._export_path_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._filenames_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._export_tag_txts, CC.FLAGS_LONE_BUTTON )
        vbox.AddF( self._export, CC.FLAGS_LONE_BUTTON )
        vbox.AddF( self._cancel, CC.FLAGS_LONE_BUTTON )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        if x < 780: x = 780
        if y < 480: y = 480
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self.EventSelectPath, None )
        wx.CallAfter( self.EventRecalcPaths, None )
        
        wx.CallAfter( self._export.SetFocus )
        
    
    def _GetPath( self, media, terms ):
        
        directory = HydrusData.ToUnicode( self._directory_picker.GetPath() )
        
        filename = ClientExporting.GenerateExportFilename( media, terms )
        
        return os.path.join( directory, filename )
        
    
    def _RecalcPaths( self ):
        
        pattern = self._pattern.GetValue()
        
        terms = ClientExporting.ParseExportPhrase( pattern )
        
        all_paths = set()
        
        for ( index, ( ( ordering_index, media ), mime, old_path ) ) in enumerate( self._paths.GetClientData() ):
            
            path = self._GetPath( media, terms )
            
            if path in all_paths:
                
                i = 1
                
                while self._GetPath( media, terms + [ ( 'string', str( i ) ) ] ) in all_paths: i += 1
                
                path = self._GetPath( media, terms + [ ( 'string', str( i ) ) ] )
                
            
            all_paths.add( path )
            
            if path != old_path:
                
                mime = media.GetMime()
                
                self._paths.UpdateRow( index, ( str( ordering_index + 1 ), HC.mime_string_lookup[ mime ], path ), ( ( ordering_index, media ), mime, path ) )
                
            
        
    
    def DeletePaths( self ):
        
        with DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._paths.RemoveAllSelected()
                
                self._RecalcPaths()
                
            
        
    
    def EventExport( self, event ):
        
        self._RecalcPaths()
        
        export_tag_txts = self._export_tag_txts.GetValue()
        
        directory = self._directory_picker.GetPath()
        
        HydrusPaths.MakeSureDirectoryExists( directory )
        
        pattern = self._pattern.GetValue()
        
        new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        new_options.SetString( 'export_phrase', pattern )
        
        terms = ClientExporting.ParseExportPhrase( pattern )
        
        client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
        
        self._export.Disable()
        
        to_do = self._paths.GetClientData()
        
        num_to_do = len( to_do )
        
        def do_it():
            
            for ( index, ( ( ordering_index, media ), mime, path ) ) in enumerate( to_do ):
                
                try:
                    
                    wx.CallAfter( self._export.SetLabel, HydrusData.ConvertValueRangeToPrettyString( index + 1, num_to_do ) )
                    
                    hash = media.GetHash()
                    
                    if export_tag_txts:
                        
                        tags_manager = media.GetTagsManager()
                        
                        tags = set()
                        
                        for service_key in self._tag_txt_tag_services:
                            
                            tags.update( tags_manager.GetCurrent( service_key ) )
                            
                        
                        tags = list( tags )
                        
                        tags.sort()
                        
                        txt_path = path + '.txt'
                        
                        with open( txt_path, 'wb' ) as f:
                            
                            f.write( HydrusData.ToByteString( os.linesep.join( tags ) ) )
                            
                        
                    
                    source_path = client_files_manager.GetFilePath( hash, mime )
                    
                    HydrusPaths.MirrorFile( source_path, path )
                    
                    try: os.chmod( path, stat.S_IWRITE | stat.S_IREAD )
                    except: pass
                    
                except:
                    
                    wx.CallAfter( wx.MessageBox, 'Encountered a problem while attempting to export file with index ' + str( ordering_index + 1 ) + ':' + os.linesep * 2 + traceback.format_exc() )
                    
                    break
                    
                
            
            wx.CallAfter( self._export.SetLabel, 'done!' )
            
            time.sleep( 1 )
            
            wx.CallAfter( self._export.SetLabel, 'export' )
            
            wx.CallAfter( self._export.Enable )
            
        
        HydrusGlobals.client_controller.CallToThread( do_it )
        
    
    def EventExportTagTxtsChanged( self, event ):
        
        if self._export_tag_txts.GetValue() == True:
            
            services_manager = HydrusGlobals.client_controller.GetServicesManager()
            
            tag_services = services_manager.GetServices( HC.TAG_SERVICES )
            
            names_to_service_keys = { service.GetName() : service.GetServiceKey() for service in tag_services }
            
            service_keys_to_names = { service_key : name for ( name, service_key ) in names_to_service_keys.items() }
            
            tag_service_names = names_to_service_keys.keys()
            
            tag_service_names.sort()
            
            with DialogCheckFromListOfStrings( self, 'select tag services', tag_service_names, self._tag_txt_tag_services ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    selected_names = dlg.GetChecked()
                    
                    self._tag_txt_tag_services = [ names_to_service_keys[ name ] for name in selected_names ]
                    
                else:
                    
                    self._export_tag_txts.SetValue( False )
                    
                
            
        
    
    def EventOpenLocation( self, event ):
        
        directory = self._directory_picker.GetPath()
        
        if directory is not None and directory != '':
            
            try:
                
                HydrusPaths.LaunchDirectory( directory )
                
            except:
                
                wx.MessageBox( 'Could not open that location!' )
                
            
        
    
    def EventRecalcPaths( self, event ):
        
        pattern = self._pattern.GetValue()
        
        new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        new_options.SetString( 'export_phrase', pattern )
        
        self._RecalcPaths()
        
    
    def EventSelectPath( self, event ):
        
        indices = self._paths.GetAllSelected()
        
        if len( indices ) == 0:
            
            all_media = [ media for ( ( ordering_index, media ), mime, old_path ) in self._paths.GetClientData() ]
            
        else:
            
            all_media = [ media for ( ( ordering_index, media ), mime, old_path ) in [ self._paths.GetClientData( index ) for index in indices ] ]
            
        
        self._tags_box.SetTagsByMedia( all_media )
        
    
class DialogShortcuts( Dialog ):
    
    def __init__( self, parent ):
        
        Dialog.__init__( self, parent, 'setup shortcuts' )
        
        self._edit_log = []
        
        self._shortcuts = ClientGUICommon.ListBook( self )
        self._shortcuts.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventSelect )
        
        self._add = wx.Button( self, label = 'add' )
        self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
        
        self._delete = wx.Button( self, label = 'delete' )
        self._delete.Bind( wx.EVT_BUTTON, self.EventDelete )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        default_shortcuts = self._GetDefaultShortcuts()
        
        page = self._Panel( self._shortcuts, default_shortcuts )
        
        self._shortcuts.AddPage( 'default', 'default', page )
        
        all_shortcuts = HydrusGlobals.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUTS )
        
        names_to_shortcuts = { shortcuts.GetName() : shortcuts for shortcuts in all_shortcuts }
        
        for ( name, shortcuts ) in names_to_shortcuts.items():
            
            self._shortcuts.AddPageArgs( name, name, self._Panel, ( self._shortcuts, shortcuts ), {} )
            
        
        #
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.AddF( self._add, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._delete, CC.FLAGS_VCENTER )
        
        buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        buttons.AddF( self._ok, CC.FLAGS_VCENTER )
        buttons.AddF( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._shortcuts, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( button_hbox, CC.FLAGS_VCENTER )
        vbox.AddF( buttons, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        if x < 780: x = 780
        if y < 480: y = 480
        
        self.SetInitialSize( ( x, y ) )
        
        
        wx.CallAfter( self.EventSelect, None )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _GetDefaultShortcuts( self ):
        
        default_shortcuts = ClientData.Shortcuts( 'default' )
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items():
            
            for ( key, action ) in key_dict.items():
                
                if action in ( 'manage_tags', 'manage_ratings', 'archive', 'inbox', 'fullscreen_switch', 'frame_back', 'frame_next', 'next', 'first', 'last', 'open_externally', 'pan_up', 'pan_down', 'pan_left', 'pan_right', 'previous', 'remove', 'zoom_in', 'zoom_out', 'zoom_switch' ):
                    
                    service_key = None
                    
                    default_shortcuts.SetKeyboardAction( modifier, key, ( service_key, action ) )
                    
                
            
        
        default_shortcuts.SetKeyboardAction( wx.ACCEL_NORMAL, wx.WXK_DELETE, ( None, 'delete' ) )
        
        return default_shortcuts
        
    
    def _CurrentPageIsUntouchable( self ):
        
        name = self._shortcuts.GetCurrentKey()
        
        if name is None: # 'default'
            
            return True
            
        else:
            
            return False
            
        
    
    def EventDelete( self, event ):
        
        page = self._shortcuts.GetCurrentPage()
        
        if page is not None:
            
            if not self._CurrentPageIsUntouchable():
                
                name = self._shortcuts.GetCurrentKey()
                
                self._edit_log.append( HydrusData.EditLogActionDelete( name ) )
                
                self._shortcuts.DeleteCurrentPage()
                
            
        
    
    def EventOK( self, event ):
        
        for entry in self._edit_log:
            
            if entry.GetAction() == HC.DELETE:
                
                name = entry.GetIdentifier()
                
                HydrusGlobals.client_controller.Write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUTS, name )
                
            
        
        default_page = self._shortcuts.GetPage( 'default' )
        
        for page in self._shortcuts.GetActivePages():
            
            if page is not default_page:
                
                shortcuts = page.GetShortcuts()
                
                HydrusGlobals.client_controller.Write( 'serialisable', shortcuts )
                
            
        
        self.EndModal( wx.ID_OK )
        
    
    def EventAdd( self, event ):
        
        with DialogTextEntry( self, 'Enter name for these shortcuts.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                name = dlg.GetValue()
                
                if name == '': return
                
                while self._shortcuts.KeyExists( name ):
                    
                    name += str( random.randint( 0, 9 ) )
                    
                
                shortcuts = ClientData.Shortcuts( name )
                
                page = self._shortcuts.GetCurrentPage()
                
                if page is not None:
                    
                    existing_shortcuts = page.GetShortcuts()
                    
                    for ( ( modifier, key ), action ) in existing_shortcuts.IterateKeyboardShortcuts():
                        
                        shortcuts.SetKeyboardAction( modifier, key, action )
                        
                    
                    for ( ( modifier, mouse_button ), action ) in existing_shortcuts.IterateMouseShortcuts():
                        
                        shortcuts.SetKeyboardAction( modifier, mouse_button, action )
                        
                    
                
                page = self._Panel( self._shortcuts, shortcuts )
                
                self._shortcuts.AddPage( name, name, page, select = True )
                
            
        
    
    def EventSelect( self, event ):
        
        if self._CurrentPageIsUntouchable():
            
            self._delete.Disable()
            
        else:
            
            self._delete.Enable()
            
        
    
    def GetShortcuts( self ):
        
        page = self._shortcuts.GetCurrentPage()
        
        shortcuts = page.GetShortcuts()
        
        return shortcuts
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, shortcuts ):
            
            wx.Panel.__init__( self, parent )
            
            self._original_shortcuts = shortcuts
            
            self._shortcuts = ClientGUICommon.SaneListCtrl( self, 120, [ ( 'modifier', 150 ), ( 'key', 150 ), ( 'service', 150 ), ( 'action', -1 ) ], delete_key_callback = self.RemoveShortcuts, activation_callback = self.EditShortcuts )
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            self._add.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._edit = wx.Button( self, label = 'edit' )
            self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
            
            self._remove = wx.Button( self, label = 'remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            self._remove.SetForegroundColour( ( 128, 0, 0 ) )
            
            #
            
            for ( ( modifier, key ), action ) in self._original_shortcuts.IterateKeyboardShortcuts():
                
                ( pretty_modifier, pretty_key ) = ClientData.ConvertShortcutToPrettyShortcut( modifier, key )
                
                ( service_key, data ) = action
                
                if service_key is None:
                    
                    pretty_service_key = ''
                    
                else:
                    
                    try:
                        
                        service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
                        
                        pretty_service_key = service.GetName()
                        
                    except HydrusExceptions.DataMissing:
                        
                        pretty_service_key = 'service not found'
                        
                    
                
                pretty_data = data
                
                self._shortcuts.Append( ( pretty_modifier, pretty_key, pretty_service_key, pretty_data ), ( modifier, key, service_key, data ) )
                
            
            self._SortListCtrl()
            
            #
            
            action_buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            action_buttons.AddF( self._add, CC.FLAGS_VCENTER )
            action_buttons.AddF( self._edit, CC.FLAGS_VCENTER )
            action_buttons.AddF( self._remove, CC.FLAGS_VCENTER )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._shortcuts, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( action_buttons, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
        
        def _SortListCtrl( self ):
            
            self._shortcuts.SortListItems( 3 )
            
        
        def EditShortcuts( self ):
            
            for index in self._shortcuts.GetAllSelected():
                
                ( modifier, key, service_key, action ) = self._shortcuts.GetClientData( index )
                
                with DialogInputCustomFilterAction( self, modifier = modifier, key = key, service_key = service_key, action = action ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        ( pretty_tuple, sort_tuple ) = dlg.GetInfo()
                        
                        self._shortcuts.UpdateRow( index, pretty_tuple, sort_tuple )
                        
                        self._SortListCtrl()
                        
                    
                
            
        
        def EventAdd( self, event ):
            
            with DialogInputCustomFilterAction( self ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( pretty_tuple, sort_tuple ) = dlg.GetInfo()
                    
                    self._shortcuts.Append( pretty_tuple, sort_tuple )
                    
                    self._SortListCtrl()
                    
                
            
        
        def EventEdit( self, event ):
            
            self.EditShortcuts()
            
        
        def EventRemove( self, event ):
            
            self.RemoveShortcuts()
            
        
        def GetShortcuts( self ):
            
            name = self._original_shortcuts.GetName()
            
            shortcuts = ClientData.Shortcuts( name )
            
            rows = self._shortcuts.GetClientData()
            
            for ( modifier, key, service_key, data ) in rows:
                
                action = ( service_key, data )
                
                shortcuts.SetKeyboardAction( modifier, key, action )
                
            
            return shortcuts
            
        
        def RemoveShortcuts( self ):
            
            with DialogYesNo( self, 'Remove all selected?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._shortcuts.RemoveAllSelected()
                    
                
            
        
    
class DialogTextEntry( Dialog ):
    
    def __init__( self, parent, message, default = '', allow_blank = False, suggestions = None ):
        
        if suggestions is None:
            
            suggestions = []
            
        
        Dialog.__init__( self, parent, 'enter text', position = 'center' )
        
        self._chosen_suggestion = None
        self._allow_blank = allow_blank
        
        button_choices =  []
        
        for text in suggestions:
            
            button_choices.append( ClientGUICommon.BetterButton( self, text, self.ButtonChoice, text ) )
            
        
        self._text = wx.TextCtrl( self, style = wx.TE_PROCESS_ENTER )
        self._text.Bind( wx.EVT_TEXT, self.EventText )
        self._text.Bind( wx.EVT_TEXT_ENTER, self.EventEnter )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        self._text.SetValue( default )
        
        self._CheckText()
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._ok, CC.FLAGS_SMALL_INDENT )
        hbox.AddF( self._cancel, CC.FLAGS_SMALL_INDENT )
        
        st_message = wx.StaticText( self, label = message )
        
        st_message.Wrap( 480 )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( st_message, CC.FLAGS_BIG_INDENT )
        
        for button in button_choices:
            
            vbox.AddF( button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        vbox.AddF( self._text, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 250 )
        
        self.SetInitialSize( ( x, y ) )
        
    
    def _CheckText( self ):
        
        if not self._allow_blank:
            
            if self._text.GetValue() == '': self._ok.Disable()
            else: self._ok.Enable()
            
        
    
    def ButtonChoice( self, text ):
        
        self._chosen_suggestion =  text
        
        self.EndModal( wx.ID_OK )
        
    
    def EventText( self, event ):
        
        wx.CallAfter( self._CheckText )
        
        event.Skip()
        
    
    def EventEnter( self, event ):
        
        if self._text.GetValue() != '':
            
            self.EndModal( wx.ID_OK )
            
        
    
    def GetValue( self ):
        
        if self._chosen_suggestion is None:
            
            return self._text.GetValue()
            
        else:
            
            return self._chosen_suggestion
            
        
    
class DialogYesNo( Dialog ):
    
    def __init__( self, parent, message, title = 'Are you sure?', yes_label = 'yes', no_label = 'no' ):
        
        Dialog.__init__( self, parent, title, position = 'center' )
        
        self._yes = wx.Button( self, id = wx.ID_YES, label = yes_label )
        self._yes.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._no = wx.Button( self, id = wx.ID_NO, label = no_label )
        self._no.SetForegroundColour( ( 128, 0, 0 ) )
        
        self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
        
        #
        
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
        
        x = max( x, 250 )
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._yes.SetFocus )
        
    
