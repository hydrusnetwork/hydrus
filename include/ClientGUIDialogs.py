from . import HydrusConstants as HC
from . import ClientConstants as CC
from . import ClientData
from . import ClientDefaults
from . import ClientDownloading
from . import ClientDragDrop
from . import ClientExporting
from . import ClientCaches
from . import ClientFiles
from . import ClientGUIACDropdown
from . import ClientGUIFrames
from . import ClientGUICommon
from . import ClientGUIDialogsQuick
from . import ClientGUIFunctions
from . import ClientGUIImport
from . import ClientGUIListBoxes
from . import ClientGUIListCtrl
from . import ClientGUIPredicates
from . import ClientGUIShortcuts
from . import ClientGUITime
from . import ClientGUITopLevelWindows
from . import ClientImporting
from . import ClientTags
from . import ClientThreading
import collections
import gc
from . import HydrusExceptions
from . import HydrusFileHandling
from . import HydrusNATPunch
from . import HydrusNetwork
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusTagArchive
from . import HydrusTags
from . import HydrusThreading
import itertools
import os
import random
import re
import queue
import shutil
import stat
import string
import threading
import time
import traceback
import wx
import wx.lib.agw.customtreectrl
import yaml
from . import HydrusData
from . import ClientSearch
from . import HydrusGlobals as HG

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
        
        choice_tuples = [ ( service.GetName(), service.GetServiceKey() ) for service in services ]
        
        try:
            
            service_key = ClientGUIDialogsQuick.SelectFromList( HG.client_controller.GetGUI(), 'select service', choice_tuples )
            
            return service_key
            
        except HydrusExceptions.CancelledException:
            
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
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
        if parent is not None and position == 'center':
            
            wx.CallAfter( self.Center )
            
        
        HG.client_controller.ResetIdleTimer()
        
    
    def EventCharHook( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key == wx.WXK_ESCAPE:
            
            self.EndModal( wx.ID_CANCEL )
            
        else:
            
            event.Skip()
            
        
    
    def SetInitialSize( self, size ):
        
        ( width, height ) = size
        
        ( display_width, display_height ) = ClientGUITopLevelWindows.GetDisplaySize( self )
        
        width = min( display_width, width )
        height = min( display_height, height )
        
        wx.Dialog.SetInitialSize( self, ( width, height ) )
        
        min_width = min( 240, width )
        min_height = min( 240, height )
        
        self.SetMinSize( ( min_width, min_height ) )
        
    
class DialogChooseNewServiceMethod( Dialog ):
    
    def __init__( self, parent ):
        
        Dialog.__init__( self, parent, 'how to set up the account?', position = 'center' )
        
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
        
    
    def GetRegister( self ):
        
        return self._should_register
        
    
class DialogCommitInterstitialFiltering( Dialog ):
    
    def __init__( self, parent, label ):
        
        Dialog.__init__( self, parent, 'commit and continue?', position = 'center' )
        
        self._commit = ClientGUICommon.BetterButton( self, 'commit and continue', self.EndModal, wx.ID_YES )
        self._commit.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._back = ClientGUICommon.BetterButton( self, 'go back', self.EndModal, wx.ID_NO )
        
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
        
        self._commit = ClientGUICommon.BetterButton( self, 'commit', self.EndModal, wx.ID_YES )
        self._commit.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._forget = ClientGUICommon.BetterButton( self, 'forget', self.EndModal, wx.ID_NO )
        self._forget.SetForegroundColour( ( 128, 0, 0 ) )
        
        self._back = ClientGUICommon.BetterButton( self, 'back to filtering', self.EndModal, wx.ID_CANCEL )
        
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
        
        self._ok = wx.Button( self, id = wx.ID_OK, label = 'OK' )
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
            
            self._timeout_number.SetValue( time_left // time_value )
            
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
        
        intro = 'Sharing ' + HydrusData.ToHumanInt( len( self._hashes ) ) + ' files.'
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
        
        internal_port = self._service.GetPort()
        
        if internal_port is None:
            
            wx.MessageBox( 'The local booru is not currently running!' )
            
        
        try:
            
            url = self._service.GetExternalShareURL( self._share_key )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            wx.MessageBox( 'Unfortunately, could not generate an external URL: {}'.format( e ) )
            
            return
            
        
        HG.client_controller.pub( 'clipboard', 'text', url )
        
    
    def EventCopyInternalShareURL( self, event ):
        
        self._service = HG.client_controller.services_manager.GetService( CC.LOCAL_BOORU_SERVICE_KEY )
        
        internal_ip = '127.0.0.1'
        
        internal_port = self._service.GetPort()
        
        url = 'http://' + internal_ip + ':' + str( internal_port ) + '/gallery?share_key=' + self._share_key.hex()
        
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
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( '#', 4 ), ( 'path', -1 ), ( 'guessed mime', 16 ), ( 'size', 10 ) ]
        
        self._paths_list = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, 'input_local_files', 12, 36, columns, self._ConvertListCtrlDataToTuple, delete_key_callback = self.RemovePaths )
        
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
        show_downloader_options = False
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self, file_import_options, show_downloader_options )
        
        menu_items = []
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'do_human_sort_on_hdd_file_import_paths' )
        
        menu_items.append( ( 'check', 'sort paths as they are added', 'If checked, paths will be sorted in a numerically human-friendly (e.g. "page 9.jpg" comes before "page 10.jpg") way.', check_manager ) )
        
        self._cog_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.cog, menu_items )
        
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
        
        import_options_buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        import_options_buttons.Add( self._file_import_options, CC.FLAGS_SIZER_VCENTER )
        import_options_buttons.Add( self._cog_button, CC.FLAGS_SIZER_VCENTER )
        
        buttons = wx.BoxSizer( wx.HORIZONTAL )
        
        buttons.Add( self._add_button, CC.FLAGS_VCENTER )
        buttons.Add( self._tag_button, CC.FLAGS_VCENTER )
        buttons.Add( self._cancel, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( gauge_sizer, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( delete_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( import_options_buttons, CC.FLAGS_LONE_BUTTON )
        vbox.Add( buttons, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        if x < 780: x = 780
        if y < 480: y = 480
        
        self.SetInitialSize( ( x, y ) )
        
        self._lock = threading.Lock()
        
        self._current_path_data = {}
        
        self._job_key = ClientThreading.JobKey()
        
        self._unparsed_paths_queue = queue.Queue()
        self._currently_parsing = threading.Event()
        self._work_to_do = threading.Event()
        self._parsed_path_queue = queue.Queue()
        self._pause_event = threading.Event()
        self._cancel_event = threading.Event()
        
        self._progress_updater = ClientGUICommon.ThreadToGUIUpdater( self._progress, self._progress.SetValue )
        
        if len( paths ) > 0:
            
            self._AddPathsToList( paths )
            
        
        self.Show()
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
        HG.client_controller.gui.RegisterUIUpdateWindow( self )
        
        HG.client_controller.CallToThreadLongRunning( self.THREADParseImportablePaths, self._unparsed_paths_queue, self._currently_parsing, self._work_to_do, self._parsed_path_queue, self._progress_updater, self._pause_event, self._cancel_event )
        
    
    def _AddPathsToList( self, paths ):
        
        if self._cancel_event.is_set():
            
            message = 'Please wait for the cancel to clear.'
            
            wx.MessageBox( message )
            
            return
            
        
        self._unparsed_paths_queue.put( paths )
        
    
    def _ConvertListCtrlDataToTuple( self, path ):
        
        ( index, mime, size ) = self._current_path_data[ path ]
        
        pretty_index = HydrusData.ToHumanInt( index )
        pretty_mime = HC.mime_string_lookup[ mime ]
        pretty_size = HydrusData.ToHumanBytes( size )
        
        display_tuple = ( pretty_index, path, pretty_mime, pretty_size )
        sort_tuple = ( index, path, pretty_mime, size )
        
        return ( display_tuple, sort_tuple )
        
    
    def _TidyUp( self ):
        
        self._pause_event.set()
        
    
    def AddFolder( self ):
        
        with wx.DirDialog( self, 'Select a folder to add.', style = wx.DD_DIR_MUST_EXIST ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                self._AddPathsToList( ( path, ) )
                
            
        
    
    def AddPaths( self ):
        
        with wx.FileDialog( self, 'Select the files to add.', style = wx.FD_MULTIPLE ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                paths = dlg.GetPaths()
                
                self._AddPathsToList( paths )
                
            
        
    
    def EventCancel( self, event ):
        
        self._TidyUp()
        
        self.Close()
        
    
    def EventCharHook( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key == wx.WXK_ESCAPE:
            
            self._TidyUp()
            
            self.Close()
            
        else:
            
            event.Skip()
            
        
    
    def EventDeleteAfterSuccessCheck( self, event ):
        
        if self._delete_after_success.GetValue():
            
            self._delete_after_success_st.SetLabelText( 'YOUR ORIGINAL FILES WILL BE DELETED' )
            
        else:
            
            self._delete_after_success_st.SetLabelText( '' )
            
        
    
    def EventOK( self, event ):
        
        self._TidyUp()
        
        paths = self._paths_list.GetData()
        
        if len( paths ) > 0:
            
            file_import_options = self._file_import_options.GetValue()
            
            paths_to_service_keys_to_tags = collections.defaultdict( ClientTags.ServiceKeysToTags )
            
            delete_after_success = self._delete_after_success.GetValue()
            
            HG.client_controller.pub( 'new_hdd_import', paths, file_import_options, paths_to_service_keys_to_tags, delete_after_success )
            
        
        self.Close()
        
    
    def EventTags( self, event ):
        
        paths = self._paths_list.GetData()
        
        if len( paths ) > 0:
            
            file_import_options = self._file_import_options.GetValue()
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'filename tagging', frame_key = 'local_import_filename_tagging' ) as dlg:
                
                panel = ClientGUIImport.EditLocalImportFilenameTaggingPanel( dlg, paths )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    paths_to_service_keys_to_tags = panel.GetValue()
                    
                    delete_after_success = self._delete_after_success.GetValue()
                    
                    HG.client_controller.pub( 'new_hdd_import', paths, file_import_options, paths_to_service_keys_to_tags, delete_after_success )
                    
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
                
                paths_to_delete = self._paths_list.GetData( only_selected = True )
                
                self._paths_list.DeleteSelected()
                
                for path in paths_to_delete:
                    
                    del self._current_path_data[ path ]
                    
                
                flat_path_data = [ ( index, path, mime, size ) for ( path, ( index, mime, size ) ) in self._current_path_data.items() ]
                
                flat_path_data.sort()
                
                new_index = 1
                
                for ( old_index, path, mime, size ) in flat_path_data:
                    
                    self._current_path_data[ path ] = ( new_index, mime, size )
                    
                    new_index += 1
                    
                
                self._paths_list.UpdateDatas()
                
            
        
    
    def THREADParseImportablePaths( self, unparsed_paths_queue, currently_parsing, work_to_do, parsed_path_queue, progress_updater, pause_event, cancel_event ):
        
        unparsed_paths = collections.deque()
        
        num_files_done = 0
        num_good_files = 0
        
        num_empty_files = 0
        num_unimportable_mime_files = 0
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
                    
                    message = 'none of the ' + HydrusData.ToHumanInt( total_paths ) + ' files parsed successfully'
                    
                
            else:
                
                message = HydrusData.ConvertValueRangeToPrettyString( num_good_files, total_paths ) + ' files parsed successfully'
                
            
            if num_empty_files > 0 or num_unimportable_mime_files > 0 or num_occupied_files > 0:
                
                if num_good_files == 0:
                    
                    message += ': '
                    
                else:
                    
                    message += ', but '
                    
                
                bad_comments = []
                
                if num_empty_files > 0:
                    
                    bad_comments.append( HydrusData.ToHumanInt( num_empty_files ) + ' were empty' )
                    
                
                if num_unimportable_mime_files > 0:
                    
                    bad_comments.append( HydrusData.ToHumanInt( num_unimportable_mime_files ) + ' had unsupported file types' )
                    
                
                if num_occupied_files > 0:
                    
                    bad_comments.append( HydrusData.ToHumanInt( num_occupied_files ) + ' were inaccessible (maybe in use by another process)' )
                    
                
                message += ' and '.join( bad_comments )
                
            
            message += '.'
            
            progress_updater.Update( message, num_files_done, total_paths )
            
            # status updated, lets see what work there is to do
            
            if cancel_event.is_set():
                
                while not unparsed_paths_queue.empty():
                    
                    try:
                        
                        unparsed_paths_queue.get( block = False )
                        
                    except queue.Empty:
                        
                        pass
                        
                    
                
                unparsed_paths = collections.deque()
                
                cancel_event.clear()
                pause_event.clear()
                
                continue
                
            
            if pause_event.is_set():
                
                time.sleep( 1 )
                
                continue
                
            
            # let's see if there is anything to parse
            
            # first we'll flesh out unparsed_paths with anything new to look at
            
            do_human_sort = HG.client_controller.new_options.GetBoolean( 'do_human_sort_on_hdd_file_import_paths' )
            
            while not unparsed_paths_queue.empty():
                
                try:
                    
                    raw_paths = unparsed_paths_queue.get( block = False )
                    
                    paths = ClientFiles.GetAllFilePaths( raw_paths, do_human_sort = do_human_sort ) # convert any dirs to subpaths
                    
                    unparsed_paths.extend( paths )
                    
                except queue.Empty:
                    
                    pass
                    
                
            
            # if unparsed_paths still has nothing, we'll nonetheless sleep on new paths
            
            if len( unparsed_paths ) == 0:
                
                try:
                    
                    raw_paths = unparsed_paths_queue.get( timeout = 5 )
                    
                    paths = ClientFiles.GetAllFilePaths( raw_paths, do_human_sort = do_human_sort ) # convert any dirs to subpaths
                    
                    unparsed_paths.extend( paths )
                    
                except queue.Empty:
                    
                    pass
                    
                
                continue # either we added some or didn't--in any case, restart the cycle
                
            
            path = unparsed_paths.popleft()
            
            currently_parsing.set()
            
            # we are now dealing with a file. let's clear out quick no-gos
            
            num_files_done += 1
            
            if path.endswith( os.path.sep + 'Thumbs.db' ) or path.endswith( os.path.sep + 'thumbs.db' ):
                
                num_unimportable_mime_files += 1
                
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
                
                num_unimportable_mime_files += 1
                
            
        
    
    def TIMERUIUpdate( self ):
        
        good_paths = list()
        
        while not self._parsed_path_queue.empty():
            
            ( path, mime, size ) = self._parsed_path_queue.get()
            
            if not self._paths_list.HasData( path ):
                
                good_paths.append( path )
                
                index = len( self._current_path_data ) + 1
                
                self._current_path_data[ path ] = ( index, mime, size )
                
            
        
        if len( good_paths ) > 0:
            
            self._paths_list.AddDatas( good_paths )
            
        
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
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._progress_pause, CC.GlobalBMPs.play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._progress_pause, CC.GlobalBMPs.pause )
            
        
    
class DialogInputNamespaceRegex( Dialog ):
    
    def __init__( self, parent, namespace = '', regex = '' ):
        
        Dialog.__init__( self, parent, 'configure quick namespace' )
        
        self._namespace = wx.TextCtrl( self )
        
        self._regex = wx.TextCtrl( self )
        
        self._shortcuts = ClientGUICommon.RegexButton( self )
        
        self._regex_intro_link = ClientGUICommon.BetterHyperLink( self, 'a good regex introduction', 'http://www.aivosto.com/vbtips/regex.html' )
        self._regex_practise_link = ClientGUICommon.BetterHyperLink( self, 'regex practise', 'http://regexr.com/3cvmf' )
        
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
            
            re.compile( regex )
            
        except Exception as e:
            
            text = 'That regex would not compile!'
            text += os.linesep * 2
            text += str( e )
            
            wx.MessageBox( text )
            
            return
            
        
        self.EndModal( wx.ID_OK )
        
    
    def GetInfo( self ):
        
        namespace = self._namespace.GetValue()
        
        regex = self._regex.GetValue()
        
        return ( namespace, regex )
        
    
class DialogInputTags( Dialog ):
    
    def __init__( self, parent, service_key, tags, message = '' ):
        
        Dialog.__init__( self, parent, 'input tags' )
        
        self._service_key = service_key
        
        self._tags = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, service_key = service_key )
        
        expand_parents = True
        
        self._tag_box = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterTags, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, service_key, null_entry_callable = self.OK, show_paste_button = True )
        
        self._ok = ClientGUICommon.BetterButton( self, 'OK', self.EndModal, wx.ID_OK )
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
        
        if message != '':
            
            vbox.Add( ClientGUICommon.BetterStaticText( self, message ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        vbox.Add( self._tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._tag_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( b_box, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        ( x, y ) = self.GetEffectiveMinSize()
        
        x = max( x, 300 )
        
        self.SetInitialSize( ( x, y ) )
        
        wx.CallAfter( self._tag_box.SetFocus )
        

    def EnterTags( self, tags ):
        
        tag_parents_manager = HG.client_controller.tag_parents_manager
        
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
        
        self._ok = ClientGUICommon.BetterButton( self, 'OK', self.EndModal, wx.ID_OK )
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
            
            subject_string = str( response[ 'account_info' ] )
            
        else:
            
            subject_string = 'modifying ' + HydrusData.ToHumanInt( len( self._subject_identifiers ) ) + ' accounts'
            
        
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
        # generate accounts, with the modification having occurred
        
        self._service.Request( HC.POST, 'account', { 'accounts' : self._accounts } )
        
        if len( self._subject_identifiers ) == 1:
            
            ( subject_identifier, ) = self._subject_identifiers
            
            response = self._service.Request( HC.GET, 'account_info', { 'subject_identifier' : subject_identifier } )
            
            account_info = response[ 'account_info' ]
            
            self._subject_text.SetLabelText( str( account_info ) )
            
        
        if len( self._subject_identifiers ) > 1: wx.MessageBox( 'Done!' )
        
    
    def EventAddToExpires( self, event ):
        
        raise NotImplementedError()
        #self._DoModification( HC.ADD_TO_EXPIRES, timespan = self._add_to_expires.GetClientData( self._add_to_expires.GetSelection() ) )
        
    
    def EventBan( self, event ):
        
        with DialogTextEntry( self, 'Enter reason for the ban.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                raise NotImplementedError()
                #self._DoModification( HC.BAN, reason = dlg.GetValue() )
                
            
        
    
    def EventChangeAccountType( self, event ):
        
        raise NotImplementedError()
        #self._DoModification( HC.CHANGE_ACCOUNT_TYPE, account_type_key = self._account_types.GetChoice() )
        
    
    def EventSetExpires( self, event ):
        
        expires = self._set_expires.GetClientData( self._set_expires.GetSelection() )
        
        if expires is not None:
            
            expires += HydrusData.GetNow()
            
        
        raise NotImplementedError()
        #self._DoModification( HC.SET_EXPIRES, expires = expires )
        
    
    def EventSuperban( self, event ):
        
        with DialogTextEntry( self, 'Enter reason for the superban.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                raise NotImplementedError()
                #self._DoModification( HC.SUPERBAN, reason = dlg.GetValue() )
                
            
        
    
class DialogSelectFromURLTree( Dialog ):
    
    def __init__( self, parent, url_tree ):
        
        Dialog.__init__( self, parent, 'select items' )
        
        agwStyle = wx.lib.agw.customtreectrl.TR_DEFAULT_STYLE | wx.lib.agw.customtreectrl.TR_AUTO_CHECK_CHILD
        
        self._tree = wx.lib.agw.customtreectrl.CustomTreeCtrl( self, agwStyle = agwStyle )
        
        self._ok = ClientGUICommon.BetterButton( self, 'OK', self.EndModal, wx.ID_OK )
        self._ok.SetForegroundColour( ( 0, 128, 0 ) )
        
        self._cancel = wx.Button( self, id = wx.ID_CANCEL, label = 'Cancel' )
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
        
        return name + ' - ' + HydrusData.ToHumanBytes( size )
        
    
    def GetURLs( self ):
        
        root_item = self._tree.GetRootItem()
        
        urls = self._GetSelectedChildrenData( root_item )
        
        return urls
        
    
class DialogSelectImageboard( Dialog ):
    
    def __init__( self, parent ):
        
        Dialog.__init__( self, parent, 'select imageboard' )
        
        self._tree = wx.TreeCtrl( self )
        self._tree.Bind( wx.EVT_TREE_ITEM_ACTIVATED, self.EventActivate )
        
        #
        
        all_imageboards = HG.client_controller.Read( 'imageboards' )
        
        root_item = self._tree.AddRoot( 'all sites' )
        
        for ( site, imageboards ) in list(all_imageboards.items()):
            
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
            
        
        self._ok = ClientGUICommon.BetterButton( self, 'ok', self.EndModal, wx.ID_OK )
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
        st_message.SetWrapWidth( 480 )
        
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
        
        self._yes = ClientGUICommon.BetterButton( self, yes_label, self.EndModal, wx.ID_YES )
        self._yes.SetForegroundColour( ( 0, 128, 0 ) )
        self._yes.SetLabelText( yes_label )
        
        self._no = ClientGUICommon.BetterButton( self, no_label, self.EndModal, wx.ID_NO )
        self._no.SetForegroundColour( ( 128, 0, 0 ) )
        self._no.SetLabelText( no_label )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._yes, CC.FLAGS_SMALL_INDENT )
        hbox.Add( self._no, CC.FLAGS_SMALL_INDENT )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        text = ClientGUICommon.BetterStaticText( self, message )
        
        text.SetWrapWidth( 480 )
        
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
            
        
        self._no = ClientGUICommon.BetterButton( self, no_label, self.EndModal, wx.ID_NO )
        self._no.SetForegroundColour( ( 128, 0, 0 ) )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        for yes_button in yes_buttons:
            
            hbox.Add( yes_button, CC.FLAGS_SMALL_INDENT )
            
        
        hbox.Add( self._no, CC.FLAGS_SMALL_INDENT )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        text = ClientGUICommon.BetterStaticText( self, message )
        
        text.SetWrapWidth( 480 )
        
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
        
