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
import ClientGUIImport
import ClientGUIListBoxes
import ClientGUIListCtrl
import ClientGUIPredicates
import ClientGUITime
import ClientGUITopLevelWindows
import ClientImporting
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
import wx.adv
import yaml
import HydrusData
import ClientSearch
import HydrusGlobals as HG

# Option Enums

ID_NULL = wx.NewId()

ID_TIMER_UPDATE = wx.NewId()

def SelectServiceKey( service_types = HC.ALL_SERVICES, service_keys = None, unallowed = None ):
    
    if service_keys is None:
        
        services = HG.client_controller.services_manager.GetServices( service_types )
        
        service_keys = [ service.GetServiceKey() for service in services ]
        
    
    if unallowed is not None:
        
        service_keys.difference_update( unallowed )
        
    
    if len( service_keys ) == 0:
        
        return None
        
    elif len( service_keys ) == 1:
        
        ( service_key, ) = service_keys
        
        return service_key
        
    else:
        
        services = { HG.client_controller.services_manager.GetService( service_key ) for service_key in service_keys }
        
        list_of_tuples = [ ( service.GetName(), service.GetServiceKey() ) for service in services ]
        
        with DialogSelectFromList( HG.client_controller.GetGUI(), 'select service', list_of_tuples ) as dlg:
            
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
                
            
            ( pos_x, pos_y ) = parent_tlp.GetPosition()
            
            pos = ( pos_x + 50, pos_y + 50 )
            
        else:
            
            pos = wx.DefaultPosition
            
        
        if not HC.PLATFORM_LINUX and parent is not None:
            
            style |= wx.FRAME_FLOAT_ON_PARENT
            
        
        wx.Dialog.__init__( self, parent, title = title, style = style, pos = pos )
        
        self._new_options = HG.client_controller.new_options
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self.SetIcon( HG.client_controller.frame_icon )
        
        self.Bind( wx.EVT_BUTTON, self.EventDialogButton )
        
        if parent is not None and position == 'center':
            
            wx.CallAfter( self.Center )
            
        
        HG.client_controller.ResetIdleTimer()
        
    
    def EventDialogButton( self, event ):
        
        if self.IsModal():
            
            self.EndModal( event.GetId() )
            
        
    
    def SetInitialSize( self, ( width, height ) ):
        
        ( display_width, display_height ) = ClientGUITopLevelWindows.GetDisplaySize( self )
        
        width = min( display_width, width )
        height = min( display_height, height )
        
        wx.Dialog.SetInitialSize( self, ( width, height ) )
        
        min_width = min( 240, width )
        min_height = min( 240, height )
        
        self.SetMinSize( ( min_width, min_height ) )
        
    
class DialogButtonChoice( Dialog ):
    
    def __init__( self, parent, intro, choices, show_always_checkbox = False ):
        
        Dialog.__init__( self, parent, 'choose what to do', position = 'center' )
        
        self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
        
        self._buttons = []
        self._ids_to_data = {}
        
        i = 0
        
        for ( text, data, tooltip ) in choices:
            
            button = wx.Button( self, label = text, id = i )
            
            button.SetToolTip( tooltip )
            
            self._buttons.append( button )
            
            self._ids_to_data[ i ] = data
            
            i += 1
            
        
        self._always_do_checkbox = wx.CheckBox( self, label = 'do this for all' )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( ClientGUICommon.BetterStaticText( self, intro ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        for button in self._buttons:
            
            vbox.Add( button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        vbox.Add( self._always_do_checkbox, CC.FLAGS_LONE_BUTTON )
        
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
        
        vbox.Add( self._register, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( wx.StaticText( self, label = '-or-', style = wx.ALIGN_CENTER ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._setup, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( x, y ) )
        
        self._should_register = False
        
        wx.CallAfter( self._register.SetFocus )
        
    
    def EventRegister( self, event ):
        
        self._should_register = True
        
        self.EndModal( wx.ID_OK )
        
    
    def GetRegister( self ): return self._should_register
    
class DialogCommitInterstitialFiltering( Dialog ):
    
    def __init__( self, parent, label ):
        
        Dialog.__init__( self, parent, 'commit and continue?', position = 'center' )
        
        self._commit = wx.Button( self, id = wx.ID_YES, label = 'commit and continue' )
        self._commit.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._back = wx.Button( self, id = wx.ID_CANCEL, label = 'go back' )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( wx.StaticText( self, label = label, style = wx.ALIGN_CENTER ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._commit, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( wx.StaticText( self, label = '-or-', style = wx.ALIGN_CENTER ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._commit.SetFocus )
        
    
class DialogFinishFiltering( Dialog ):
    
    def __init__( self, parent, label ):
        
        Dialog.__init__( self, parent, 'are you sure?', position = 'center' )
        
        self._commit = wx.Button( self, id = wx.ID_YES, label = 'commit' )
        self._commit.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._forget = wx.Button( self, id = wx.ID_NO, label = 'forget' )
        self._forget.SetForegroundColour( ( 128, 0, 0 ) )
        
        self._back = wx.Button( self, id = wx.ID_CANCEL, label = 'back to filtering' )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._commit, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._forget, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( wx.StaticText( self, label = label, style = wx.ALIGN_CENTER ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( wx.StaticText( self, label = '-or-', style = wx.ALIGN_CENTER ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
        
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
        
        self._ok = wx.Button( self, label = 'OK' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        self._num.SetValue( 1 )
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
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
        
        ctrl_box.Add( ClientGUICommon.BetterStaticText( self, 'generate' ), CC.FLAGS_VCENTER )
        ctrl_box.Add( self._num, CC.FLAGS_VCENTER )
        ctrl_box.Add( self._account_types, CC.FLAGS_VCENTER )
        ctrl_box.Add( ClientGUICommon.BetterStaticText( self, 'accounts, to expire in' ), CC.FLAGS_VCENTER )
        ctrl_box.Add( self._lifetime, CC.FLAGS_VCENTER )
        
        b_box = wx.BoxSizer( wx.HORIZONTAL )
        b_box.Add( self._ok, CC.FLAGS_VCENTER )
        b_box.Add( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( ctrl_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( b_box, CC.FLAGS_BUTTON_SIZER )
        
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
            
        
        service = HG.client_controller.services_manager.GetService( self._service_key )
        
        try:
            
            request_args = { 'num' : num, 'account_type_key' : account_type_key }
            
            if expires is not None:
                
                request_args[ 'expires' ] = expires
                
            
            response = service.Request( HC.GET, 'registration_keys', request_args )
            
            registration_keys = response[ 'registration_keys' ]
            
            ClientGUIFrames.ShowKeys( 'registration', registration_keys )
            
        finally:
            
            self.EndModal( wx.ID_OK )
            
        
    
class DialogInputFileSystemPredicates( Dialog ):
    
    def __init__( self, parent, predicate_type ):
        
        Dialog.__init__( self, parent, 'enter predicate' )
        
        pred_classes = []
        
        if predicate_type == HC.PREDICATE_TYPE_SYSTEM_AGE:
            
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemAgeDelta )
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemAgeDate )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_DIMENSIONS:
            
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemHeight )
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemWidth )
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemRatio )
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemNumPixels )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_DURATION:
            
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemDuration )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE:
            
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemFileService )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_HASH:
            
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemHash )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_LIMIT:
            
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemLimit )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_MIME:
            
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemMime )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS:
            
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemNumTags )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS:
            
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemNumWords )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_RATING:
            
            services_manager = HG.client_controller.services_manager
            
            ratings_services = services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
            
            if len( ratings_services ) > 0:
                
                pred_classes.append( ClientGUIPredicates.PanelPredicateSystemRating )
                
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO:
            
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemSimilarTo )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIZE:
            
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemSize )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER:
            
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemTagAsNumber )
            
        elif predicate_type == HC.PREDICATE_TYPE_SYSTEM_DUPLICATE_RELATIONSHIPS:
            
            pred_classes.append( ClientGUIPredicates.PanelPredicateSystemDuplicateRelationships )
            
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        for pred_class in pred_classes:
            
            panel = self._Panel( self, pred_class )
            
            vbox.Add( panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
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
            
            self._ok = wx.Button( self, id = wx.ID_OK, label = 'OK' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( self._predicate_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            hbox.Add( self._ok, CC.FLAGS_VCENTER )
            
            self.SetSizer( hbox )
            
            self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
            
        
        def _DoOK( self ):
            
            predicates = self._predicate_panel.GetPredicates()
            
            self.GetParent().SubPanelOK( predicates )
            
        
        def EventCharHook( self, event ):
            
            ( modifier, key ) = ClientData.ConvertKeyEventToSimpleTuple( event )
            
            if key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
                
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
            
            time_left = HydrusData.GetTimeDeltaUntilTime( timeout )
            
            if time_left < 60 * 60 * 12: time_value = 60
            elif time_left < 60 * 60 * 24 * 7: time_value = 60 * 60 
            else: time_value = 60 * 60 * 24
            
            self._timeout_number.SetValue( time_left / time_value )
            
            self._timeout_multiplier.SelectClientData( time_value )
            
        
        self._hashes = hashes
        
        self._service = HG.client_controller.services_manager.GetService( CC.LOCAL_BOORU_SERVICE_KEY )
        
        internal_port = self._service.GetPort()
        
        if internal_port is None:
            
            self._copy_internal_share_link.Disable()
            self._copy_external_share_link.Disable()
            
        
        #
        
        rows = []
        
        rows.append( ( 'share name: ', self._name ) )
        rows.append( ( 'share text: ', self._text ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        timeout_box = wx.BoxSizer( wx.HORIZONTAL )
        timeout_box.Add( self._timeout_number, CC.FLAGS_EXPAND_BOTH_WAYS )
        timeout_box.Add( self._timeout_multiplier, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        link_box = wx.BoxSizer( wx.HORIZONTAL )
        link_box.Add( self._copy_internal_share_link, CC.FLAGS_VCENTER )
        link_box.Add( self._copy_external_share_link, CC.FLAGS_VCENTER )
        
        b_box = wx.BoxSizer( wx.HORIZONTAL )
        b_box.Add( self._ok, CC.FLAGS_VCENTER )
        b_box.Add( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        intro = 'Sharing ' + HydrusData.ConvertIntToPrettyString( len( self._hashes ) ) + ' files.'
        intro += os.linesep + 'Title and text are optional.'
        
        if new_share: intro += os.linesep + 'The link will not work until you ok this dialog.'
        
        vbox.Add( ClientGUICommon.BetterStaticText( self, intro ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( timeout_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( link_box, CC.FLAGS_BUTTON_SIZER )
        vbox.Add( b_box, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 350 )
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def EventCopyExternalShareURL( self, event ):
        
        self._service = HG.client_controller.services_manager.GetService( CC.LOCAL_BOORU_SERVICE_KEY )
        
        external_ip = HydrusNATPunch.GetExternalIP() # eventually check for optional host replacement here
        
        external_port = self._service.GetUPnPPort()
        
        if external_port is None:
            
            external_port = self._service.GetPort()
            
        
        url = 'http://' + external_ip + ':' + HydrusData.ToUnicode( external_port ) + '/gallery?share_key=' + self._share_key.encode( 'hex' )
        
        HG.client_controller.pub( 'clipboard', 'text', url )
        
    
    def EventCopyInternalShareURL( self, event ):
        
        self._service = HG.client_controller.services_manager.GetService( CC.LOCAL_BOORU_SERVICE_KEY )
        
        internal_ip = '127.0.0.1'
        
        internal_port = self._service.GetPort()
        
        url = 'http://' + internal_ip + ':' + str( internal_port ) + '/gallery?share_key=' + self._share_key.encode( 'hex' )
        
        HG.client_controller.pub( 'clipboard', 'text', url )
        
    
    def GetInfo( self ):
        
        name = self._name.GetValue()
        
        text = self._text.GetValue()
        
        timeout = self._timeout_number.GetValue()
        
        if timeout is not None: timeout = timeout * self._timeout_multiplier.GetChoice() + HydrusData.GetNow()
        
        return ( self._share_key, name, text, timeout, self._hashes )
        
    
class FrameInputLocalFiles( wx.Frame ):
    
    def __init__( self, parent, paths = None ):
        
        ( pos_x, pos_y ) = parent.GetPosition()
        
        pos = ( pos_x + 50, pos_y + 50 )
        
        style = wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT
        
        wx.Frame.__init__( self, parent, title = 'importing files', style = style, pos = pos )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self.SetIcon( HG.client_controller.frame_icon )
        
        if paths is None:
            
            paths = []
            
        
        self.SetDropTarget( ClientDragDrop.FileDropTarget( self, filenames_callable = self._AddPathsToList ) )
        
        listctrl_panel = ClientGUIListCtrl.SaneListCtrlPanel( self )
        
        self._paths_list = ClientGUIListCtrl.SaneListCtrl( listctrl_panel, 120, [ ( 'path', -1 ), ( 'guessed mime', 110 ), ( 'size', 60 ) ], delete_key_callback = self.RemovePaths )
        
        listctrl_panel.SetListCtrl( self._paths_list )
        
        listctrl_panel.AddButton( 'add files', self.AddPaths )
        listctrl_panel.AddButton( 'add folder', self.AddFolder )
        listctrl_panel.AddButton( 'remove files', self.RemovePaths, enabled_only_on_selection = True )
        
        self._progress = ClientGUICommon.TextAndGauge( self )
        
        self._progress_pause = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.pause, self.PauseProgress )
        self._progress_pause.Disable()
        
        self._progress_cancel = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.stop, self.StopProgress )
        self._progress_cancel.Disable()
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self, file_import_options )
        
        self._delete_after_success_st = ClientGUICommon.BetterStaticText( self, style = wx.ALIGN_RIGHT | wx.ST_NO_AUTORESIZE )
        self._delete_after_success_st.SetForegroundColour( ( 127, 0, 0 ) )
        
        self._delete_after_success = wx.CheckBox( self, label = 'delete original files after successful import' )
        self._delete_after_success.Bind( wx.EVT_CHECKBOX, self.EventDeleteAfterSuccessCheck )
        
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
        
        gauge_sizer.Add( self._progress, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        gauge_sizer.Add( self._progress_pause, CC.FLAGS_VCENTER )
        gauge_sizer.Add( self._progress_cancel, CC.FLAGS_VCENTER )
        
        delete_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        delete_hbox.Add( self._delete_after_success_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        delete_hbox.Add( self._delete_after_success, CC.FLAGS_VCENTER )
        
        buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        buttons.Add( self._add_button, CC.FLAGS_VCENTER )
        buttons.Add( self._tag_button, CC.FLAGS_VCENTER )
        buttons.Add( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( gauge_sizer, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( delete_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._file_import_options, CC.FLAGS_LONE_BUTTON )
        vbox.Add( buttons, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        if x < 780: x = 780
        if y < 480: y = 480
        
        self.SetInitialSize( ( x, y ) )
        
        self._lock = threading.Lock()
        
        self._current_paths = []
        self._current_paths_set = set()
        
        self._job_key = ClientThreading.JobKey()
        
        self._unparsed_paths_queue = Queue.Queue()
        self._currently_parsing = threading.Event()
        self._work_to_do = threading.Event()
        self._parsed_path_queue = Queue.Queue()
        self._pause_event = threading.Event()
        self._cancel_event = threading.Event()
        
        self._progress_updater = ClientGUICommon.ThreadToGUIUpdater( self._progress, self._progress.SetValue )
        
        if len( paths ) > 0:
            
            self._AddPathsToList( paths )
            
        
        self.Show()
        
        HG.client_controller.gui.RegisterUIUpdateWindow( self )
        
        HG.client_controller.CallToThreadLongRunning( self.THREADParseImportablePaths, self._unparsed_paths_queue, self._currently_parsing, self._work_to_do, self._parsed_path_queue, self._progress_updater, self._pause_event, self._cancel_event )
        
    
    def _AddPathsToList( self, paths ):
        
        if self._cancel_event.is_set():
            
            message = 'Please wait for the cancel to clear.'
            
            wx.MessageBox( message )
            
            return
            
        
        paths = [ HydrusData.ToUnicode( path ) for path in paths ]
        
        self._unparsed_paths_queue.put( paths )
        
    
    def _TidyUp( self ):
        
        self._pause_event.set()
        
    
    def AddFolder( self ):
        
        with wx.DirDialog( self, 'Select a folder to add.', style = wx.DD_DIR_MUST_EXIST ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = HydrusData.ToUnicode( dlg.GetPath() )
                
                self._AddPathsToList( ( path, ) )
                
            
        
    
    def AddPaths( self ):
        
        with wx.FileDialog( self, 'Select the files to add.', style = wx.FD_MULTIPLE ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                paths = [ HydrusData.ToUnicode( path ) for path in dlg.GetPaths() ]
                
                self._AddPathsToList( paths )
                
            
        
    
    def EventCancel( self, event ):
        
        self._TidyUp()
        
        self.Close()
        
    
    def EventDeleteAfterSuccessCheck( self, event ):
        
        if self._delete_after_success.GetValue():
            
            self._delete_after_success_st.SetLabelText( 'YOUR ORIGINAL FILES WILL BE DELETED' )
            
        else:
            
            self._delete_after_success_st.SetLabelText( '' )
            
        
    
    def EventOK( self, event ):
        
        self._TidyUp()
        
        if len( self._current_paths ) > 0:
            
            file_import_options = self._file_import_options.GetValue()
            
            paths_to_tags = {}
            
            delete_after_success = self._delete_after_success.GetValue()
            
            HG.client_controller.pub( 'new_hdd_import', self._current_paths, file_import_options, paths_to_tags, delete_after_success )
            
        
        self.Close()
        
    
    def EventTags( self, event ):
        
        if len( self._current_paths ) > 0:
            
            file_import_options = self._file_import_options.GetValue()
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'filename tagging', frame_key = 'local_import_filename_tagging' ) as dlg:
                
                panel = ClientGUIImport.EditLocalImportFilenameTaggingPanel( dlg, self._current_paths )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    paths_to_tags = panel.GetValue()
                    
                    delete_after_success = self._delete_after_success.GetValue()
                    
                    HG.client_controller.pub( 'new_hdd_import', self._current_paths, file_import_options, paths_to_tags, delete_after_success )
                    
                    self.Close()
                    
                
            
        
    
    def PauseProgress( self ):
        
        if self._pause_event.is_set():
            
            self._pause_event.clear()
            
        else:
            
            self._pause_event.set()
            
        
    
    def StopProgress( self ):
        
        self._cancel_event.set()
        
    
    def RemovePaths( self ):
        
        with DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._paths_list.RemoveAllSelected()
                
                self._current_paths = [ row[0] for row in self._paths_list.GetClientData() ]
                self._current_paths_set = set( self._current_paths )
                
            
        
    
    def THREADParseImportablePaths( self, unparsed_paths_queue, currently_parsing, work_to_do, parsed_path_queue, progress_updater, pause_event, cancel_event ):
        
        unparsed_paths = []
        
        num_files_done = 0
        num_good_files = 0
        
        num_empty_files = 0
        num_uninteresting_mime_files = 0
        num_occupied_files = 0
        
        while not HG.view_shutdown:
            
            if not self:
                
                return
                
            
            if len( unparsed_paths ) > 0:
                
                work_to_do.set()
                
            else:
                
                work_to_do.clear()
                
            
            currently_parsing.clear()
            
            # ready to start, let's update ui on status
            
            total_paths = num_files_done + len( unparsed_paths )
            
            if num_good_files == 0:
                
                if num_files_done == 0:
                    
                    message = 'waiting for paths to parse'
                    
                else:
                    
                    message = 'none of the ' + HydrusData.ConvertIntToPrettyString( total_paths ) + ' files parsed successfully'
                    
                
            else:
                
                message = HydrusData.ConvertValueRangeToPrettyString( num_good_files, total_paths ) + ' files parsed successfully'
                
            
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
            
            progress_updater.Update( message, num_files_done, total_paths )
            
            # status updated, lets see what work there is to do
            
            if cancel_event.is_set():
                
                while not unparsed_paths_queue.empty():
                    
                    try:
                        
                        unparsed_paths_queue.get( block = False )
                        
                    except Queue.Empty:
                        
                        pass
                        
                    
                
                unparsed_paths = []
                
                cancel_event.clear()
                pause_event.clear()
                
                continue
                
            
            if pause_event.is_set():
                
                time.sleep( 1 )
                
                continue
                
            
            # let's see if there is anything to parse
            
            # first we'll flesh out unparsed_paths with anything new to look at
            
            while not unparsed_paths_queue.empty():
                
                try:
                    
                    raw_paths = unparsed_paths_queue.get( block = False )
                    
                    paths = ClientFiles.GetAllPaths( raw_paths ) # convert any dirs to subpaths
                    
                    unparsed_paths.extend( paths )
                    
                except Queue.Empty:
                    
                    pass
                    
                
            
            # if unparsed_paths still has nothing, we'll nonetheless sleep on new paths
            
            if len( unparsed_paths ) == 0:
                
                try:
                    
                    raw_paths = unparsed_paths_queue.get( timeout = 5 )
                    
                    paths = ClientFiles.GetAllPaths( raw_paths ) # convert any dirs to subpaths
                    
                    unparsed_paths.extend( paths )
                    
                except Queue.Empty:
                    
                    pass
                    
                
                continue # either we added some or didn't--in any case, restart the cycle
                
            
            path = unparsed_paths.pop( 0 )
            
            currently_parsing.set()
            
            # we are now dealing with a file. let's clear out quick no-gos
            
            num_files_done += 1
            
            if path.endswith( os.path.sep + 'Thumbs.db' ) or path.endswith( os.path.sep + 'thumbs.db' ):
                
                num_uninteresting_mime_files += 1
                
                continue
                
            
            if not HydrusPaths.PathIsFree( path ):
                
                num_occupied_files += 1
                
                continue
                
            
            size = os.path.getsize( path )
            
            if size == 0:
                
                HydrusData.Print( 'Empty file: ' + path )
                
                num_empty_files += 1
                
                continue
                
            
            # looks good, let's burn some CPU
            
            mime = HydrusFileHandling.GetMime( path )
            
            if mime in HC.ALLOWED_MIMES:
                
                num_good_files += 1
                
                parsed_path_queue.put( ( path, mime, size ) )
                
            else:
                
                HydrusData.Print( 'Unparsable file: ' + path )
                
                num_uninteresting_mime_files += 1
                
            
        
    
    def TIMERUIUpdate( self ):
        
        while not self._parsed_path_queue.empty():
            
            ( path, mime, size ) = self._parsed_path_queue.get()
            
            pretty_mime = HC.mime_string_lookup[ mime ]
            pretty_size = HydrusData.ConvertIntToBytes( size )
            
            if path not in self._current_paths_set:
                
                self._current_paths_set.add( path )
                self._current_paths.append( path )
                
                self._paths_list.Append( ( path, pretty_mime, pretty_size ), ( path, mime, size ) )
                
            
        
        #
        
        paused = self._pause_event.is_set()
        no_work_in_queue = not self._work_to_do.is_set()
        working_on_a_file_now = self._currently_parsing.is_set()
        
        can_import = ( no_work_in_queue or paused ) and not working_on_a_file_now
        
        if no_work_in_queue:
            
            self._progress_pause.Disable()
            self._progress_cancel.Disable()
            
        else:
            
            self._progress_pause.Enable()
            self._progress_cancel.Enable()
            
        
        if can_import:
            
            self._add_button.Enable()
            self._tag_button.Enable()
            
        else:
            
            self._add_button.Disable()
            self._tag_button.Disable()
            
        
        if paused:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._progress_pause, CC.GlobalBMPs.play )
            
        else:
            
            ClientGUICommon.SetBitmapButtonBitmap( self._progress_pause, CC.GlobalBMPs.pause )
            
        
    
class DialogInputNamespaceRegex( Dialog ):
    
    def __init__( self, parent, namespace = '', regex = '' ):
        
        Dialog.__init__( self, parent, 'configure quick namespace' )
        
        self._namespace = wx.TextCtrl( self )
        
        self._regex = wx.TextCtrl( self )
        
        self._shortcuts = ClientGUICommon.RegexButton( self )
        
        self._regex_intro_link = wx.adv.HyperlinkCtrl( self, id = -1, label = 'a good regex introduction', url = 'http://www.aivosto.com/vbtips/regex.html' )
        self._regex_practise_link = wx.adv.HyperlinkCtrl( self, id = -1, label = 'regex practise', url = 'http://regexr.com/3cvmf' )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'OK' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
    
        self._namespace.SetValue( namespace )
        self._regex.SetValue( regex )
        
        #
        
        control_box = wx.BoxSizer( wx.HORIZONTAL )
        
        control_box.Add( self._namespace, CC.FLAGS_EXPAND_BOTH_WAYS )
        control_box.Add( ClientGUICommon.BetterStaticText( self, ':' ), CC.FLAGS_VCENTER )
        control_box.Add( self._regex, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        b_box = wx.BoxSizer( wx.HORIZONTAL )
        b_box.Add( self._ok, CC.FLAGS_VCENTER )
        b_box.Add( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        intro = r'Put the namespace (e.g. page) on the left.' + os.linesep + r'Put the regex (e.g. [1-9]+\d*(?=.{4}$)) on the right.' + os.linesep + r'All files will be tagged with "namespace:regex".'
        
        vbox.Add( ClientGUICommon.BetterStaticText( self, intro ), CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( control_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._shortcuts, CC.FLAGS_LONE_BUTTON )
        vbox.Add( self._regex_intro_link, CC.FLAGS_LONE_BUTTON )
        vbox.Add( self._regex_practise_link, CC.FLAGS_LONE_BUTTON )
        vbox.Add( b_box, CC.FLAGS_BUTTON_SIZER )
        
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
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'OK' )
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
        
        b_box.Add( self._ok, CC.FLAGS_VCENTER )
        b_box.Add( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( b_box, CC.FLAGS_BUTTON_SIZER )
        
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
        
    
class DialogInputTags( Dialog ):
    
    def __init__( self, parent, service_key, tags ):
        
        Dialog.__init__( self, parent, 'input tags' )
        
        self._service_key = service_key
        
        self._tags = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, service_key = service_key )
        
        expand_parents = True
        
        self._tag_box = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterTags, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, service_key, null_entry_callable = self.OK )
        
        self._ok = wx.Button( self, id= wx.ID_OK, label = 'OK' )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        self._tags.SetTags( tags )
        
        #
        
        b_box = wx.BoxSizer( wx.HORIZONTAL )
        
        b_box.Add( self._ok, CC.FLAGS_VCENTER )
        b_box.Add( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._tag_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( b_box, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 300 )
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._tag_box.SetFocus )
        

    def EnterTags( self, tags ):
        
        tag_parents_manager = HG.client_controller.GetManager( 'tag_parents' )
        
        parents = set()
        
        for tag in tags:
            
            some_parents = tag_parents_manager.GetParents( self._service_key, tag )
            
            parents.update( some_parents )
            
        
        if len( tags ) > 0:
            
            self._tags.EnterTags( tags )
            self._tags.AddTags( parents )
            
        
    
    def GetTags( self ):
        
        return self._tags.GetTags()
        
    
    def OK( self ):
        
        self.EndModal( wx.ID_OK )
        
    
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
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'OK' )
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
        b_box.Add( self._ok, CC.FLAGS_VCENTER )
        b_box.Add( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        vbox.Add( b_box, CC.FLAGS_BUTTON_SIZER )
        
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
        
        self._service = HG.client_controller.services_manager.GetService( service_key )
        self._subject_identifiers = list( subject_identifiers )
        
        #
        
        self._account_info_panel = ClientGUICommon.StaticBox( self, 'account info' )
        
        self._subject_text = wx.StaticText( self._account_info_panel )
        
        #
        
        self._account_types_panel = ClientGUICommon.StaticBox( self, 'account types' )
        
        self._account_types = wx.Choice( self._account_types_panel )
        
        self._account_types_ok = wx.Button( self._account_types_panel, label = 'OK' )
        self._account_types_ok.Bind( wx.EVT_BUTTON, self.EventChangeAccountType )
        
        #
        
        self._expiration_panel = ClientGUICommon.StaticBox( self, 'change expiration' )
        
        self._add_to_expires = wx.Choice( self._expiration_panel )
        
        self._add_to_expires_ok = wx.Button( self._expiration_panel, label = 'OK' )
        self._add_to_expires_ok.Bind( wx.EVT_BUTTON, self.EventAddToExpires )
        
        self._set_expires = wx.Choice( self._expiration_panel )
        
        self._set_expires_ok = wx.Button( self._expiration_panel, label = 'OK' )
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
        
        self._account_info_panel.Add( self._subject_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        account_types_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        account_types_hbox.Add( self._account_types, CC.FLAGS_VCENTER )
        account_types_hbox.Add( self._account_types_ok, CC.FLAGS_VCENTER )
        
        self._account_types_panel.Add( account_types_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        add_to_expires_box = wx.BoxSizer( wx.HORIZONTAL )
        
        add_to_expires_box.Add( wx.StaticText( self._expiration_panel, label = 'add to expires: ' ), CC.FLAGS_VCENTER )
        add_to_expires_box.Add( self._add_to_expires, CC.FLAGS_EXPAND_BOTH_WAYS )
        add_to_expires_box.Add( self._add_to_expires_ok, CC.FLAGS_VCENTER )
        
        set_expires_box = wx.BoxSizer( wx.HORIZONTAL )
        
        set_expires_box.Add( wx.StaticText( self._expiration_panel, label = 'set expires to: ' ), CC.FLAGS_VCENTER )
        set_expires_box.Add( self._set_expires, CC.FLAGS_EXPAND_BOTH_WAYS )
        set_expires_box.Add( self._set_expires_ok, CC.FLAGS_VCENTER )
        
        self._expiration_panel.Add( add_to_expires_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._expiration_panel.Add( set_expires_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._ban_panel.Add( self._ban, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._ban_panel.Add( self._superban, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        vbox.Add( self._account_info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._account_types_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._expiration_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._ban_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._exit, CC.FLAGS_BUTTON_SIZER )
        
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
            
        
    
class DialogSelectBooru( Dialog ):
    
    def __init__( self, parent ):
        
        Dialog.__init__( self, parent, 'select booru' )
        
        self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
        
        self._boorus = wx.ListBox( self )
        self._boorus.Bind( wx.EVT_LISTBOX_DCLICK, self.EventDoubleClick )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetDefault()
        
        #
        
        boorus = HG.client_controller.Read( 'remote_boorus' )
        
        booru_names = boorus.keys()
        
        booru_names.sort()
        
        for name in booru_names:
            
            self._boorus.Append( name )
            
        
        self._boorus.Select( 0 )
        
        self._boorus.SetFocus()
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._boorus, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._ok, CC.FLAGS_LONE_BUTTON )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 320 )
        y = max( y, 320 )
        
        self.SetInitialSize( ( x, y ) )
        
        if len( boorus ) == 1:
            
            wx.CallAfter( self.EndModal, wx.ID_OK )
            
        
    
    def EventDoubleClick( self, event ):
        
        self.EndModal( wx.ID_OK )
        
    
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
        
        button_hbox.Add( self._ok, CC.FLAGS_VCENTER )
        button_hbox.Add( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._tree, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
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
        
        all_imageboards = HG.client_controller.Read( 'imageboards' )
        
        root_item = self._tree.AddRoot( 'all sites' )
        
        for ( site, imageboards ) in all_imageboards.items():
            
            site_item = self._tree.AppendItem( root_item, site )
            
            for imageboard in imageboards:
                
                name = imageboard.GetName()
                
                self._tree.AppendItem( site_item, name, data = wx.TreeItemData( imageboard ) )
                
            
        
        self._tree.Expand( root_item )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._tree, CC.FLAGS_EXPAND_BOTH_WAYS )
        
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
    
class DialogCheckFromList( Dialog ):
    
    def __init__( self, parent, title, list_of_tuples ):
        
        Dialog.__init__( self, parent, title )
        
        self._check_list_box = ClientGUICommon.BetterCheckListBox( self, style = wx.LB_EXTENDED )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        
        for ( index, ( text, data, selected ) ) in enumerate( list_of_tuples ):
            
            self._check_list_box.Append( text, data )
            
            if selected:
                
                self._check_list_box.Check( index )
                
            
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._ok, CC.FLAGS_VCENTER )
        hbox.Add( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._check_list_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        if x < 320: x = 320
        
        self.SetInitialSize( ( x, y ) )
        
    
    def GetChecked( self ):
        
        return self._check_list_box.GetChecked()
        
    
class DialogSelectFromList( Dialog ):
    
    def __init__( self, parent, title, list_of_tuples ):
        
        Dialog.__init__( self, parent, title )
        
        self._list = wx.ListBox( self )
        self._list.Bind( wx.EVT_LISTBOX_DCLICK, self.EventSelect )
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
        self._ok.SetDefault()
        
        self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) ) # to handle esc key events properly
        
        #
        
        list_of_tuples.sort()
        
        for ( label, value ) in list_of_tuples:
            
            self._list.Append( label, value )
            
        
        self._list.Select( 0 )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._list, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._ok, CC.FLAGS_LONE_BUTTON )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 320 )
        y = max( y, 320 )
        
        self.SetInitialSize( ( x, y ) )
        
    
    def EventSelect( self, event ):
        
        self.EndModal( wx.ID_OK )
        
    
    def GetChoice( self ):
        
        selection = self._list.GetSelection()
        
        return self._list.GetClientData( selection )
        
    
class DialogSelectYoutubeURL( Dialog ):
    
    def __init__( self, parent, info ):
        
        Dialog.__init__( self, parent, 'choose youtube format' )
        
        self._info = info
        
        self._urls = ClientGUIListCtrl.SaneListCtrl( self, 360, [ ( 'format', 150 ), ( 'resolution', -1 ) ] )
        self._urls.Bind( wx.EVT_LIST_ITEM_ACTIVATED, self.EventOK )
        
        self._urls.SetMinSize( ( 360, 200 ) )
        
        self._ok = wx.Button( self, wx.ID_OK, label = 'ok' )
        self._ok.Bind( wx.EVT_BUTTON, self.EventOK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        keys = list( self._info.keys() )
        
        keys.sort()
        
        for ( extension, resolution ) in keys:
            
            self._urls.Append( ( extension, resolution ), ( extension, resolution ) )
            
        
        #self._urls.SortListItems( 0 )
        
        #
        
        buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        buttons.Add( self._ok, CC.FLAGS_VCENTER )
        buttons.Add( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._urls, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( buttons, CC.FLAGS_BUTTON_SIZER )
        
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
                
                HG.client_controller.CallToThread( ClientImporting.THREADDownloadURL, job_key, url, url_string )
                
                HG.client_controller.pub( 'message', job_key )
                
            
        
        self.EndModal( wx.ID_OK )
        
    
class DialogSetupExport( Dialog ):
    
    def __init__( self, parent, flat_media ):
        
        Dialog.__init__( self, parent, 'setup export' )
        
        new_options = HG.client_controller.new_options
        
        self._tags_box = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'files\' tags' )
        
        services_manager = HG.client_controller.services_manager
        
        self._neighbouring_txt_tag_service_keys = services_manager.FilterValidServiceKeys( new_options.GetKeyList( 'default_neighbouring_txt_tag_service_keys' ) )
        
        t = ClientGUIListBoxes.ListBoxTagsSelection( self._tags_box, include_counts = True, collapse_siblings = True )
        
        self._tags_box.SetTagsBox( t )
        
        self._tags_box.SetMinSize( ( 220, 300 ) )
        
        self._paths = ClientGUIListCtrl.SaneListCtrl( self, 120, [ ( 'number', 60 ), ( 'mime', 70 ), ( 'expected path', -1 ) ], delete_key_callback = self.DeletePaths )
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
        
        self._export_tag_txts = wx.CheckBox( self, label = 'export tags to .txt files?' )
        self._export_tag_txts.SetToolTip( text )
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
        
        phrase = new_options.GetString( 'export_phrase' )
        
        self._pattern.SetValue( phrase )
        
        if len( self._neighbouring_txt_tag_service_keys ) > 0:
            
            self._export_tag_txts.SetValue( True )
            
        
        #
        
        top_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        top_hbox.Add( self._tags_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        top_hbox.Add( self._paths, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._directory_picker, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._open_location, CC.FLAGS_VCENTER )
        
        self._export_path_box.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._pattern, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._update, CC.FLAGS_VCENTER )
        hbox.Add( self._examples, CC.FLAGS_VCENTER )
        
        self._filenames_box.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( top_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        vbox.Add( self._export_path_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._filenames_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._export_tag_txts, CC.FLAGS_LONE_BUTTON )
        vbox.Add( self._export, CC.FLAGS_LONE_BUTTON )
        vbox.Add( self._cancel, CC.FLAGS_LONE_BUTTON )
        
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
        
        filename = ClientExporting.GenerateExportFilename( directory, media, terms )
        
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
        
        new_options = HG.client_controller.new_options
        
        new_options.SetKeyList( 'default_neighbouring_txt_tag_service_keys', self._neighbouring_txt_tag_service_keys )
        
        new_options.SetString( 'export_phrase', pattern )
        
        terms = ClientExporting.ParseExportPhrase( pattern )
        
        client_files_manager = HG.client_controller.client_files_manager
        
        self._export.Disable()
        
        to_do = self._paths.GetClientData()
        
        num_to_do = len( to_do )
        
        def wx_update_label( text ):
            
            if not self or not self._export:
                
                return
                
            
            self._export.SetLabel( text )
            
        
        def wx_done():
            
            if not self or not self._export:
                
                return
                
            
            self._export.Enable()
            
        
        def do_it( neighbouring_txt_tag_service_keys ):
            
            for ( index, ( ( ordering_index, media ), mime, path ) ) in enumerate( to_do ):
                
                try:
                    
                    wx.CallAfter( wx_update_label, HydrusData.ConvertValueRangeToPrettyString( index + 1, num_to_do ) )
                    
                    hash = media.GetHash()
                    
                    if export_tag_txts:
                        
                        tags_manager = media.GetTagsManager()
                        
                        tags = set()
                        
                        siblings_manager = HG.controller.GetManager( 'tag_siblings' )
                        
                        tag_censorship_manager = HG.client_controller.GetManager( 'tag_censorship' )
                        
                        for service_key in neighbouring_txt_tag_service_keys:
                            
                            current_tags = tags_manager.GetCurrent( service_key )
                            
                            current_tags = siblings_manager.CollapseTags( service_key, current_tags )
                            
                            current_tags = tag_censorship_manager.FilterTags( service_key, current_tags )
                            
                            tags.update( current_tags )
                            
                        
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
                    
                
            
            wx.CallAfter( wx_update_label, 'done!' )
            
            time.sleep( 1 )
            
            wx.CallAfter( wx_update_label, 'export' )
            
            wx.CallAfter( wx_done )
            
        
        HG.client_controller.CallToThread( do_it, self._neighbouring_txt_tag_service_keys )
        
    
    def EventExportTagTxtsChanged( self, event ):
        
        services_manager = HG.client_controller.services_manager
        
        tag_services = services_manager.GetServices( HC.TAG_SERVICES )
        
        list_of_tuples = [ ( service.GetName(), service.GetServiceKey(), service.GetServiceKey() in self._neighbouring_txt_tag_service_keys ) for service in tag_services ]
        
        list_of_tuples.sort()
        
        with DialogCheckFromList( self, 'select tag services', list_of_tuples ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._neighbouring_txt_tag_service_keys = dlg.GetChecked()
                
                if len( self._neighbouring_txt_tag_service_keys ) == 0:
                    
                    self._export_tag_txts.SetValue( False )
                    
                else:
                    
                    self._export_tag_txts.SetValue( True )
                    
                
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
        
        new_options = HG.client_controller.new_options
        
        new_options.SetString( 'export_phrase', pattern )
        
        self._RecalcPaths()
        
    
    def EventSelectPath( self, event ):
        
        indices = self._paths.GetAllSelected()
        
        if len( indices ) == 0:
            
            all_media = [ media for ( ( ordering_index, media ), mime, old_path ) in self._paths.GetClientData() ]
            
        else:
            
            all_media = [ media for ( ( ordering_index, media ), mime, old_path ) in [ self._paths.GetClientData( index ) for index in indices ] ]
            
        
        self._tags_box.SetTagsByMedia( all_media )
        
    
class DialogTextEntry( Dialog ):
    
    def __init__( self, parent, message, default = '', allow_blank = False, suggestions = None, max_chars = None ):
        
        if suggestions is None:
            
            suggestions = []
            
        
        Dialog.__init__( self, parent, 'enter text', position = 'center' )
        
        self._chosen_suggestion = None
        self._allow_blank = allow_blank
        self._max_chars = max_chars
        
        button_choices =  []
        
        for text in suggestions:
            
            button_choices.append( ClientGUICommon.BetterButton( self, text, self.ButtonChoice, text ) )
            
        
        self._text = wx.TextCtrl( self, style = wx.TE_PROCESS_ENTER )
        self._text.Bind( wx.EVT_TEXT, self.EventText )
        self._text.Bind( wx.EVT_TEXT_ENTER, self.EventEnter )
        
        if self._max_chars is not None:
            
            self._text.SetMaxLength( self._max_chars )
            
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'ok' )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'cancel' )
        self._cancel.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        self._text.SetValue( default )
        
        self._CheckText()
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._ok, CC.FLAGS_SMALL_INDENT )
        hbox.Add( self._cancel, CC.FLAGS_SMALL_INDENT )
        
        st_message = ClientGUICommon.BetterStaticText( self, message )
        st_message.Wrap( 480 )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( st_message, CC.FLAGS_BIG_INDENT )
        
        for button in button_choices:
            
            vbox.Add( button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        vbox.Add( self._text, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 250 )
        
        self.SetInitialSize( ( x, y ) )
        
    
    def _CheckText( self ):
        
        if not self._allow_blank:
            
            if self._text.GetValue() == '':
                
                self._ok.Disable()
                
            else:
                
                self._ok.Enable()
                
            
        
    
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
        
        self._yes = wx.Button( self, id = wx.ID_YES )
        self._yes.SetForegroundColour( ( 0, 128, 0 ) )
        self._yes.SetLabelText( yes_label )
        
        self._no = wx.Button( self, id = wx.ID_NO )
        self._no.SetForegroundColour( ( 128, 0, 0 ) )
        self._no.SetLabelText( no_label )
        
        self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._yes, CC.FLAGS_SMALL_INDENT )
        hbox.Add( self._no, CC.FLAGS_SMALL_INDENT )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        text = ClientGUICommon.BetterStaticText( self, message )
        
        text.Wrap( 480 )
        
        vbox.Add( text, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 250 )
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._yes.SetFocus )
        
    
class DialogYesYesNo( Dialog ):
    
    def __init__( self, parent, message, title = 'Are you sure?', yes_tuples = None, no_label = 'no' ):
        
        if yes_tuples is None:
            
            yes_tuples = [ ( 'yes', 'yes' ) ]
            
        
        Dialog.__init__( self, parent, title, position = 'center' )
        
        self._value = None
        
        yes_buttons = []
        
        for ( label, data ) in yes_tuples:
            
            yes_button = ClientGUICommon.BetterButton( self, label, self._DoYes, data )
            yes_button.SetForegroundColour( ( 0, 128, 0 ) )
            
            yes_buttons.append( yes_button )
            
        
        self._no = wx.Button( self, id = wx.ID_NO )
        self._no.SetForegroundColour( ( 128, 0, 0 ) )
        self._no.SetLabelText( no_label )
        
        self._hidden_cancel = wx.Button( self, id = wx.ID_CANCEL, size = ( 0, 0 ) )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        for yes_button in yes_buttons:
            
            hbox.Add( yes_button, CC.FLAGS_SMALL_INDENT )
            
        
        hbox.Add( self._no, CC.FLAGS_SMALL_INDENT )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        text = ClientGUICommon.BetterStaticText( self, message )
        
        text.Wrap( 480 )
        
        vbox.Add( text, CC.FLAGS_BIG_INDENT )
        vbox.Add( hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 250 )
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( yes_buttons[0].SetFocus )
        
    
    def _DoYes( self, value ):
        
        self._value = value
        
        self.EndModal( wx.ID_YES )
        
    
    def GetValue( self ):
        
        return self._value
        
