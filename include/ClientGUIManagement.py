import HydrusConstants as HC
import HydrusAudioHandling
import ClientDownloading
import HydrusExceptions
import HydrusPaths
import HydrusSerialisable
import HydrusThreading
import ClientConstants as CC
import ClientData
import ClientDefaults
import ClientCaches
import ClientFiles
import ClientGUIACDropdown
import ClientGUICollapsible
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIMedia
import ClientGUIScrolledPanelsEdit
import ClientGUITopLevelWindows
import ClientImporting
import ClientMedia
import ClientRendering
import ClientThreading
import json
import multipart
import os
import threading
import time
import traceback
import urllib
import urlparse
import wx
import wx.lib.scrolledpanel
import HydrusData
import ClientSearch
import HydrusGlobals

CAPTCHA_FETCH_EVENT_TYPE = wx.NewEventType()
CAPTCHA_FETCH_EVENT = wx.PyEventBinder( CAPTCHA_FETCH_EVENT_TYPE )

ID_TIMER_CAPTCHA = wx.NewId()
ID_TIMER_DUMP = wx.NewId()
ID_TIMER_UPDATE = wx.NewId()

MANAGEMENT_TYPE_DUMPER = 0
MANAGEMENT_TYPE_IMPORT_GALLERY = 1
MANAGEMENT_TYPE_IMPORT_PAGE_OF_IMAGES = 2
MANAGEMENT_TYPE_IMPORT_HDD = 3
MANAGEMENT_TYPE_IMPORT_THREAD_WATCHER = 4
MANAGEMENT_TYPE_PETITIONS = 5
MANAGEMENT_TYPE_QUERY = 6
MANAGEMENT_TYPE_IMPORT_URLS = 7

management_panel_types_to_classes = {}

def CreateManagementController( management_type, file_service_key = None ):
    
    if file_service_key is None:
        
        file_service_key = CC.LOCAL_FILE_SERVICE_KEY
        
    
    management_controller = ManagementController()
    
    # sort
    # collect
    
    management_controller.SetType( management_type )
    management_controller.SetKey( 'file_service', file_service_key )
    
    return management_controller
    
def CreateManagementControllerImportGallery( gallery_identifier ):
    
    management_controller = CreateManagementController( MANAGEMENT_TYPE_IMPORT_GALLERY )
    
    gallery_import = ClientImporting.GalleryImport( gallery_identifier = gallery_identifier )
    
    management_controller.SetVariable( 'gallery_import', gallery_import )
    
    return management_controller
    
def CreateManagementControllerImportPageOfImages():
    
    management_controller = CreateManagementController( MANAGEMENT_TYPE_IMPORT_PAGE_OF_IMAGES )
    
    page_of_images_import = ClientImporting.PageOfImagesImport()
    
    management_controller.SetVariable( 'page_of_images_import', page_of_images_import )
    
    return management_controller
    
def CreateManagementControllerImportHDD( paths, import_file_options, paths_to_tags, delete_after_success ):
    
    management_controller = CreateManagementController( MANAGEMENT_TYPE_IMPORT_HDD )
    
    hdd_import = ClientImporting.HDDImport( paths = paths, import_file_options = import_file_options, paths_to_tags = paths_to_tags, delete_after_success = delete_after_success )
    
    management_controller.SetVariable( 'hdd_import', hdd_import )
    
    return management_controller
    
def CreateManagementControllerImportThreadWatcher():
    
    management_controller = CreateManagementController( MANAGEMENT_TYPE_IMPORT_THREAD_WATCHER )
    
    thread_watcher_import = ClientImporting.ThreadWatcherImport()
    
    management_controller.SetVariable( 'thread_watcher_import', thread_watcher_import )
    
    return management_controller
    
def CreateManagementControllerImportURLs():
    
    management_controller = CreateManagementController( MANAGEMENT_TYPE_IMPORT_URLS )
    
    urls_import = ClientImporting.URLsImport()
    
    management_controller.SetVariable( 'urls_import', urls_import )
    
    return management_controller
    
def CreateManagementControllerPetitions( petition_service_key ):
    
    petition_service = HydrusGlobals.client_controller.GetServicesManager().GetService( petition_service_key )
    
    petition_service_type = petition_service.GetServiceType()
    
    if petition_service_type in ( HC.LOCAL_FILE, HC.FILE_REPOSITORY ): file_service_key = petition_service_key
    else: file_service_key = CC.COMBINED_FILE_SERVICE_KEY
    
    management_controller = CreateManagementController( MANAGEMENT_TYPE_PETITIONS, file_service_key = file_service_key )
    
    management_controller.SetKey( 'petition_service', petition_service_key )
    
    return management_controller
    
def CreateManagementControllerQuery( file_service_key, file_search_context, search_enabled ):
    
    management_controller = CreateManagementController( MANAGEMENT_TYPE_QUERY, file_service_key = file_service_key )
    
    management_controller.SetVariable( 'file_search_context', file_search_context )
    management_controller.SetVariable( 'search_enabled', search_enabled )
    management_controller.SetVariable( 'synchronised', True )
    
    return management_controller
    
def CreateManagementPanel( parent, page, controller, management_controller ):
    
    management_type = management_controller.GetType()
    
    management_class = management_panel_types_to_classes[ management_type ]
    
    management_panel = management_class( parent, page, controller, management_controller )
    
    return management_panel
    
def GenerateDumpMultipartFormDataCTAndBody( fields ):
    
    m = multipart.Multipart()
    
    for ( name, field_type, value ) in fields:
        
        if field_type in ( CC.FIELD_TEXT, CC.FIELD_COMMENT, CC.FIELD_PASSWORD, CC.FIELD_VERIFICATION_RECAPTCHA, CC.FIELD_THREAD_ID ): m.field( name, HydrusData.ToByteString( value ) )
        elif field_type == CC.FIELD_CHECKBOX:
            
            if value:
                
                # spoiler/on -> name : spoiler, value : on
                # we don't say true/false for checkboxes
                
                ( name, value ) = name.split( '/', 1 )
                
                m.field( name, value )
                
            
        elif field_type == CC.FIELD_FILE:
            
            ( hash, mime, file ) = value
            
            m.file( name, hash.encode( 'hex' ) + HC.mime_ext_lookup[ mime ], file, { 'Content-Type' : HC.mime_string_lookup[ mime ] } )
            
        
    
    return m.get()
    
'''class CaptchaControl( wx.Panel ):
    
    def __init__( self, parent, captcha_type, default ):
        
        wx.Panel.__init__( self, parent )
        
        self._captcha_key = default
        
        self._captcha_challenge = None
        self._captcha_runs_out = 0
        self._bitmap = wx.EmptyBitmap( 20, 20, 24 )
        
        self._timer = wx.Timer( self, ID_TIMER_CAPTCHA )
        self.Bind( wx.EVT_TIMER, self.TIMEREvent, id = ID_TIMER_CAPTCHA )
        
        self._captcha_box_panel = ClientGUICommon.StaticBox( self, 'recaptcha' )
        
        self._captcha_panel = ClientGUICommon.BufferedWindow( self._captcha_box_panel, size = ( 300, 57 ) )
        
        self._refresh_button = wx.Button( self._captcha_box_panel, label = '' )
        self._refresh_button.Bind( wx.EVT_BUTTON, self.EventRefreshCaptcha )
        self._refresh_button.Disable()
        
        self._captcha_time_left = wx.StaticText( self._captcha_box_panel )
        
        self._captcha_entry = wx.TextCtrl( self._captcha_box_panel, style = wx.TE_PROCESS_ENTER )
        self._captcha_entry.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._ready_button = wx.Button( self._captcha_box_panel, label = '' )
        self._ready_button.Bind( wx.EVT_BUTTON, self.EventReady )
        
        sub_vbox = wx.BoxSizer( wx.VERTICAL )
        
        sub_vbox.AddF( self._refresh_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        sub_vbox.AddF( self._captcha_time_left, CC.FLAGS_SMALL_INDENT )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._captcha_panel, CC.FLAGS_NONE )
        hbox.AddF( sub_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        hbox2 = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox2.AddF( self._captcha_entry, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox2.AddF( self._ready_button, CC.FLAGS_VCENTER )
        
        self._captcha_box_panel.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._captcha_box_panel.AddF( hbox2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._captcha_box_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.Disable()
        
    
    def _DrawEntry( self, entry = None ):
        
        if entry is None:
            
            self._captcha_entry.SetValue( '' )
            self._captcha_entry.Disable()
            
        else: self._captcha_entry.SetValue( entry )
        
    
    def _DrawMain( self, dc ):
        
        if self._captcha_challenge is None:
            
            dc.Clear()
            
            self._refresh_button.SetLabelText( '' )
            self._refresh_button.Disable()
            
            self._captcha_time_left.SetLabelText( '' )
            
        elif self._captcha_challenge == '':
            
            dc.Clear()
            
            event = wx.NotifyEvent( CAPTCHA_FETCH_EVENT_TYPE )
            
            self.ProcessEvent( event )
            
            if event.IsAllowed():
                
                self._refresh_button.SetLabelText( 'get captcha' )
                self._refresh_button.Enable()
                
            else:
                
                self._refresh_button.SetLabelText( 'not yet' )
                self._refresh_button.Disable()
                
            
            self._captcha_time_left.SetLabelText( '' )
            
        else:
            
            wx_bmp = self._bitmap.GetWxBitmap()
            
            dc.DrawBitmap( wx_bmp, 0, 0 )
            
            wx_bmp.Destroy()
            
            self._refresh_button.SetLabelText( 'get new captcha' )
            self._refresh_button.Enable()
            
            self._captcha_time_left.SetLabelText( HydrusData.ConvertTimestampToPrettyExpires( self._captcha_runs_out ) )
            
        
        del dc
        
    
    def _DrawReady( self, ready = None ):
        
        if ready is None:
            
            self._ready_button.SetLabelText( '' )
            self._ready_button.Disable()
            
        else:
            
            if ready:
                
                self._captcha_entry.Disable()
                self._ready_button.SetLabelText( 'edit' )
                
            else:
                
                self._captcha_entry.Enable()
                self._ready_button.SetLabelText( 'ready' )
                
            
            self._ready_button.Enable()
            
        
    
    def Disable( self ):
        
        self._captcha_challenge = None
        self._captcha_runs_out = 0
        self._bitmap = wx.EmptyBitmap( 20, 20, 24 )
        
        self._DrawMain()
        self._DrawEntry()
        self._DrawReady()
        
        self._timer.Stop()
        
    
    def Enable( self ):
        
        self._captcha_challenge = ''
        self._captcha_runs_out = 0
        self._bitmap = wx.EmptyBitmap( 20, 20, 24 )
        
        self._DrawMain()
        self._DrawEntry()
        self._DrawReady()
        
        self._timer.Start( 1000, wx.TIMER_CONTINUOUS )
        
    
    def EnableWithValues( self, challenge, bitmap, captcha_runs_out, entry, ready ):
        
        if HydrusData.TimeHasPassed( captcha_runs_out ): self.Enable()
        else:
            
            self._captcha_challenge = challenge
            self._captcha_runs_out = captcha_runs_out
            self._bitmap = bitmap
            
            self._DrawMain()
            self._DrawEntry( entry )
            self._DrawReady( ready )
            
            self._timer.Start( 1000, wx.TIMER_CONTINUOUS )
            
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ): self.EventReady( None )
        else: event.Skip()
        
    
    def EventReady( self, event ): self._DrawReady( not self._ready_button.GetLabelText() == 'edit' )
    
    def EventRefreshCaptcha( self, event ):
        
        javascript_string = self._controller.DoHTTP( HC.GET, 'http://www.google.com/recaptcha/api/challenge?k=' + self._captcha_key )
        
        ( trash, rest ) = javascript_string.split( 'challenge : \'', 1 )
        
        ( self._captcha_challenge, trash ) = rest.split( '\'', 1 )
        
        jpeg = self._controller.DoHTTP( HC.GET, 'http://www.google.com/recaptcha/api/image?c=' + self._captcha_challenge )
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            with open( temp_path, 'wb' ) as f: f.write( jpeg )
            
            self._bitmap = ClientRendering.GenerateHydrusBitmap( temp_path )
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
        self._captcha_runs_out = HydrusData.GetNow() + 5 * 60 - 15
        
        self._DrawMain()
        self._DrawEntry( '' )
        self._DrawReady( False )
        
        self._timer.Start( 1000, wx.TIMER_CONTINUOUS )
        
    
    # change this to hold (current challenge, bmp, timestamp it runs out, value, whethere ready to post)
    def GetValues( self ): return ( self._captcha_challenge, self._bitmap, self._captcha_runs_out, self._captcha_entry.GetValue(), self._ready_button.GetLabelText() == 'edit' )
    
    def TIMEREvent( self, event ):
        
        try:
            
            if HydrusData.TimeHasPassed( self._captcha_runs_out ):
                
                self.Enable()
                
            else:
                
                self._DrawMain()
                
            
        except wx.PyDeadObjectError:
            
            self._timer.Stop()
            
        except:
            
            self._timer.Stop()
            
            raise
            
        
    '''

'''class Comment( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._initial_comment = ''
        
        self._comment_panel = ClientGUICommon.StaticBox( self, 'comment' )
        
        self._comment = ClientGUICommon.SaneMultilineTextCtrl( self._comment_panel, style = wx.TE_READONLY )
        
        self._comment_append = ClientGUICommon.SaneMultilineTextCtrl( self._comment_panel, style = wx.TE_PROCESS_ENTER )
        self._comment_append.Bind( wx.EVT_KEY_UP, self.EventKeyDown )
        
        self._comment_panel.AddF( self._comment, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._comment_panel.AddF( self._comment_append, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._comment_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _SetComment( self ):
        
        append = self._comment_append.GetValue()
        
        if self._initial_comment != '' and append != '': comment = self._initial_comment + os.linesep * 2 + append
        else: comment = self._initial_comment + append
        
        self._comment.SetValue( comment )
        
    
    def Disable( self ):
        
        self._initial_comment = ''
        
        self._comment_append.SetValue( '' )
        self._comment_append.Disable()
        
        self._SetComment()
        
    
    def EnableWithValues( self, initial, append ):
        
        self._initial_comment = initial
        
        self._comment_append.SetValue( append )
        self._comment_append.Enable()
        
        self._SetComment()
        
    
    def GetValues( self ): return ( self._initial_comment, self._comment_append.GetValue() )
    
    def EventKeyDown( self, event ):
        
        self._SetComment()
        
        event.Skip()
        
    '''
class ManagementController( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_MANAGEMENT_CONTROLLER
    SERIALISABLE_VERSION = 2
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._management_type = None
        
        self._keys = {}
        self._simples = {}
        self._serialisables = {}
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_keys = { name : value.encode( 'hex' ) for ( name, value ) in self._keys.items() }
        
        serialisable_simples = dict( self._simples )
        
        serialisable_serialisables = { name : value.GetSerialisableTuple() for ( name, value ) in self._serialisables.items() }
        
        return ( self._management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._management_type, serialisable_keys, serialisable_simples, serialisables ) = serialisable_info
        
        self._keys = { name : key.decode( 'hex' ) for ( name, key ) in serialisable_keys.items() }
        
        self._simples = dict( serialisable_simples )
        
        self._serialisables = { name : HydrusSerialisable.CreateFromSerialisableTuple( value ) for ( name, value ) in serialisables.items() }
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if management_type == MANAGEMENT_TYPE_IMPORT_HDD:
                
                advanced_import_options = serialisable_simples[ 'advanced_import_options' ]
                paths_info = serialisable_simples[ 'paths_info' ]
                paths_to_tags = serialisable_simples[ 'paths_to_tags' ]
                delete_after_success = serialisable_simples[ 'delete_after_success' ]
                
                paths = [ path_info for ( path_type, path_info ) in paths_info if path_type != 'zip' ]
                
                automatic_archive = advanced_import_options[ 'automatic_archive' ]
                exclude_deleted = advanced_import_options[ 'exclude_deleted' ]
                min_size = advanced_import_options[ 'min_size' ]
                min_resolution = advanced_import_options[ 'min_resolution' ]
                
                import_file_options = ClientData.ImportFileOptions( automatic_archive = automatic_archive, exclude_deleted = exclude_deleted, min_size = min_size, min_resolution = min_resolution )
                
                paths_to_tags = { path : { service_key.decode( 'hex' ) : tags for ( service_key, tags ) in service_keys_to_tags } for ( path, service_keys_to_tags ) in paths_to_tags.items() }
                
                hdd_import = ClientImporting.HDDImport( paths = paths, import_file_options = import_file_options, paths_to_tags = paths_to_tags, delete_after_success = delete_after_success )
                
                serialisable_serialisables[ 'hdd_import' ] = hdd_import.GetSerialisableTuple()
                
                del serialisable_serialisables[ 'advanced_import_options' ]
                del serialisable_serialisables[ 'paths_info' ]
                del serialisable_serialisables[ 'paths_to_tags' ]
                del serialisable_serialisables[ 'delete_after_success' ]
                
            
            new_serialisable_info = ( management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetKey( self, name ):
        
        return self._keys[ name ]
        
    
    def GetType( self ):
        
        return self._management_type
        
    
    def GetVariable( self, name ):
        
        if name in self._simples:
            
            return self._simples[ name ]
            
        else:
            
            return self._serialisables[ name ]
            
        
    
    def SetKey( self, name, key ):
        
        self._keys[ name ] = key
        
    
    def SetType( self, management_type ):
        
        self._management_type = management_type
        
    
    def SetVariable( self, name, value ):
        
        if isinstance( value, HydrusSerialisable.SerialisableBase ):
            
            self._serialisables[ name ] = value
            
        else:
            
            self._simples[ name ] = value
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_MANAGEMENT_CONTROLLER ] = ManagementController

class ManagementPanel( wx.lib.scrolledpanel.ScrolledPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        wx.lib.scrolledpanel.ScrolledPanel.__init__( self, parent, style = wx.BORDER_NONE | wx.VSCROLL )
        
        self.SetupScrolling()
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._controller = controller
        self._management_controller = management_controller
        
        self._page = page
        self._page_key = self._management_controller.GetKey( 'page' )
        
        self._controller.sub( self, 'SetSearchFocus', 'set_search_focus' )
        
    
    def _MakeCollect( self, sizer ):
        
        self._collect_by = ClientGUICommon.CheckboxCollect( self, self._page_key )
        
        sizer.AddF( self._collect_by, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def _MakeCurrentSelectionTagsBox( self, sizer ):
        
        tags_box = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'selection tags' )
        
        t = ClientGUICommon.ListBoxTagsSelectionManagementPanel( tags_box, self._page_key )
        
        tags_box.SetTagsBox( t )
        
        sizer.AddF( tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _MakeSort( self, sizer ):
        
        self._sort_by = ClientGUICommon.ChoiceSort( self, self._page_key )
        
        try:
            
            self._sort_by.SetSelection( HC.options[ 'default_sort' ] )
            
        except:
            
            self._sort_by.SetSelection( 0 )
            
        
        sizer.AddF( self._sort_by, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def CleanBeforeDestroy( self ): pass
    
    def SetSearchFocus( self, page_key ): pass
    
    def TestAbleToClose( self ): pass
    '''
class ManagementPanelDumper( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        result = self._controller.Read( 'serialisable_simple', '4chan_pass' )
        
        if result is None:
            
            result = ( '', '', 0 )
            
        
        ( self._4chan_token, pin, timeout ) = result
        
        self._have_4chan_pass = timeout > HydrusData.GetNow()
        
        self._timer = wx.Timer( self, ID_TIMER_DUMP )
        self.Bind( wx.EVT_TIMER, self.TIMEREvent, id = ID_TIMER_DUMP )
        
        ( self._post_url, self._flood_time, self._form_fields, self._restrictions ) = self._imageboard.GetBoardInfo()
        
        # progress
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self, 'import queue' )
        
        self._progress_info = wx.StaticText( self._import_queue_panel )
        
        self._progress_gauge = ClientGUICommon.Gauge( self._import_queue_panel )
        self._progress_gauge.SetRange( len( media_results ) )
        
        self._start_button = wx.Button( self._import_queue_panel, label = 'start' )
        self._start_button.Bind( wx.EVT_BUTTON, self.EventStartButton )
        
        self._import_queue_panel.AddF( self._progress_info, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( self._progress_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( self._start_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        # thread options
        
        self._thread_panel = ClientGUICommon.StaticBox( self, 'thread options' )
        
        self._thread_fields = {}
        
        gridbox = wx.FlexGridSizer( 0, 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        for ( name, field_type, default, editable ) in self._form_fields:
            
            if field_type in ( CC.FIELD_TEXT, CC.FIELD_THREAD_ID ): field = wx.TextCtrl( self._thread_panel, value = default )
            elif field_type == CC.FIELD_PASSWORD: field = wx.TextCtrl( self._thread_panel, value = default, style = wx.TE_PASSWORD )
            else: continue
            
            self._thread_fields[ name ] = ( field_type, field )
            
            if editable:
                
                gridbox.AddF( wx.StaticText( self._thread_panel, label = name + ':' ), CC.FLAGS_VCENTER )
                gridbox.AddF( field, CC.FLAGS_EXPAND_BOTH_WAYS )
                
            else: field.Hide()
            
        
        self._thread_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        # post options
        
        self._post_panel = ClientGUICommon.StaticBox( self, 'post options' )
        
        self._post_fields = {}
        
        postbox = wx.BoxSizer( wx.VERTICAL )
        
        self._post_info = wx.StaticText( self._post_panel, label = 'no file selected', style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
        
        for ( name, field_type, default, editable ) in self._form_fields:
            
            if field_type == CC.FIELD_VERIFICATION_RECAPTCHA:
                
                if self._have_4chan_pass: continue
                
                field = CaptchaControl( self._post_panel, field_type, default )
                field.Bind( CAPTCHA_FETCH_EVENT, self.EventCaptchaRefresh )
                
            elif field_type == CC.FIELD_COMMENT: field = Comment( self._post_panel )
            else: continue
            
            self._post_fields[ name ] = ( field_type, field, default )
            
            postbox.AddF( field, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        gridbox = wx.FlexGridSizer( 0, 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        for ( name, field_type, default, editable ) in self._form_fields:
            
            if field_type == CC.FIELD_CHECKBOX:
                
                field = wx.CheckBox( self._post_panel )
                
                field.SetValue( default == 'True' )
                
            else: continue
            
            self._post_fields[ name ] = ( field_type, field, default )
            
            gridbox.AddF( wx.StaticText( self._post_panel, label = name + ':' ), CC.FLAGS_VCENTER )
            gridbox.AddF( field, CC.FLAGS_EXPAND_BOTH_WAYS )
            
        
        for ( name, field_type, default, editable ) in self._form_fields:
            
            if field_type == CC.FIELD_FILE: self._file_post_name = name
            
        
        self._post_panel.AddF( self._post_info, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._post_panel.AddF( postbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._post_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        # misc
        
        self._import_tag_options = ClientGUICollapsible.CollapsibleOptionsTags( self, namespaces = [ 'creator', 'series', 'title', 'volume', 'chapter', 'page', 'character', 'person', 'all others' ] )
        
        # arrange stuff
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        
        vbox.AddF( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._thread_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._post_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._import_tag_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        self._controller.sub( self, 'FocusChanged', 'focus_changed' )
        self._controller.sub( self, 'SortedMediaPulse', 'sorted_media_pulse' )
        
        self._sorted_media_hashes = [ media_result.GetHash() for media_result in media_results ]
        
        self._hashes_to_media = { media_result.GetHash() : ClientMedia.MediaSingleton( media_result ) for media_result in media_results }
        
        self._hashes_to_dump_info = {}
        
        for ( hash, media ) in self._hashes_to_media.items():
            
            dump_status_enum = CC.DUMPER_NOT_DUMPED
            
            dump_status_string = 'not yet dumped'
            
            post_field_info = []
            
            for ( name, ( field_type, field, default ) ) in self._post_fields.items():
                
                if field_type == CC.FIELD_COMMENT:
                    
                    post_field_info.append( ( name, field_type, ( self._GetInitialComment( media ), '' ) ) )
                    
                elif field_type == CC.FIELD_CHECKBOX: post_field_info.append( ( name, field_type, default == 'True' ) )
                elif field_type == CC.FIELD_VERIFICATION_RECAPTCHA: post_field_info.append( ( name, field_type, None ) )
                
            
            self._hashes_to_dump_info[ hash ] = ( dump_status_enum, dump_status_string, post_field_info )
            
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self._timer.Start( 1000, wx.TIMER_CONTINUOUS )
        
    
    def _THREADDoDump( self, hash, post_field_info, headers, body ):
        
        try:
            
            response = self._controller.DoHTTP( HC.POST, self._post_url, request_headers = headers, body = body )
            
            ( status, phrase ) = ClientDownloading.Parse4chanPostScreen( response )
            
        except Exception as e:
            
            ( status, phrase ) = ( 'big error', HydrusData.ToUnicode( e ) )
            
        
        wx.CallAfter( self.CALLBACKDoneDump, hash, post_field_info, status, phrase )
        
    
    def _FreezeCurrentMediaPostInfo( self ):
        
        ( dump_status_enum, dump_status_string, post_field_info ) = self._hashes_to_dump_info[ self._current_hash ]
        
        post_field_info = []
        
        for ( name, ( field_type, field, default ) ) in self._post_fields.items():
            
            if field_type == CC.FIELD_COMMENT: post_field_info.append( ( name, field_type, field.GetValues() ) )
            elif field_type == CC.FIELD_CHECKBOX: post_field_info.append( ( name, field_type, field.GetValue() ) )
            elif field_type == CC.FIELD_VERIFICATION_RECAPTCHA: post_field_info.append( ( name, field_type, field.GetValues() ) )
            
        
        self._hashes_to_dump_info[ self._current_hash ] = ( dump_status_enum, dump_status_string, post_field_info )
        
    
    def _GetInitialComment( self, media ):
        
        hash = media.GetHash()
        
        try: index = self._sorted_media_hashes.index( hash )
        except: return 'media removed'
        
        num_files = len( self._sorted_media_hashes )
        
        if index == 0:
            
            total_size = sum( [ m.GetSize() for m in self._hashes_to_media.values() ] )
            
            initial = 'Hydrus Network Client is starting a dump of ' + str( num_files ) + ' files, totalling ' + HydrusData.ConvertIntToBytes( total_size ) + ':' + os.linesep * 2
            
        else: initial = ''
        
        initial += HydrusData.ConvertValueRangeToPrettyString( index + 1, num_files )
        
        advanced_tag_options = self._import_tag_options.GetInfo()
        
        for ( service_key, namespaces ) in advanced_tag_options.items():
            
            tags_manager = media.GetTagsManager()
            
            try: service = self._controller.GetServicesManager().GetService( service_key )
            except HydrusExceptions.FileMissingException: continue
            
            service_key = service.GetServiceKey()
            
            current = tags_manager.GetCurrent( service_key )
            pending = tags_manager.GetPending( service_key )
            
            tags = current.union( pending )
            
            tags_to_include = []
            
            for namespace in namespaces:
                
                if namespace == 'all others': tags_to_include.extend( [ tag for tag in tags if not True in ( tag.startswith( n ) for n in namespaces if n != 'all others' ) ] )
                else: tags_to_include.extend( [ tag for tag in tags if tag.startswith( namespace + ':' ) ] )
                
            
            initial += os.linesep * 2 + ', '.join( tags_to_include )
            
        
        return initial
        
    
    def _ShowCurrentMedia( self ):
        
        if self._current_hash is None:
            
            self._post_info.SetLabelText( 'no file selected' )
            
            for ( name, ( field_type, field, default ) ) in self._post_fields.items():
                
                if field_type == CC.FIELD_CHECKBOX: field.SetValue( False )
                
                field.Disable()
                
            
        else:
            
            num_files = len( self._sorted_media_hashes )
            
            ( dump_status_enum, dump_status_string, post_field_info ) = self._hashes_to_dump_info[ self._current_hash ]
            
            index = self._sorted_media_hashes.index( self._current_hash )
            
            self._post_info.SetLabelText( HydrusData.ConvertValueRangeToPrettyString( index + 1, num_files ) + ': ' + dump_status_string )
            
            for ( name, field_type, value ) in post_field_info:
                
                ( field_type, field, default ) = self._post_fields[ name ]
                
                if field_type == CC.FIELD_COMMENT:
                    
                    ( initial, append ) = value
                    
                    field.EnableWithValues( initial, append )
                    
                elif field_type == CC.FIELD_CHECKBOX:
                    
                    field.SetValue( value )
                    field.Enable()
                    
                elif field_type == CC.FIELD_VERIFICATION_RECAPTCHA:
                    
                    if value is None: field.Enable()
                    else:
                        
                        ( challenge, bitmap, captcha_runs_out, entry, ready ) = value
                        
                        field.EnableWithValues( challenge, bitmap, captcha_runs_out, entry, ready )
                        
                    
                
            
            if dump_status_enum in ( CC.DUMPER_DUMPED_OK, CC.DUMPER_UNRECOVERABLE_ERROR ):
                
                for ( name, ( field_type, field, default ) ) in self._post_fields.items():
                    
                    if field_type == CC.FIELD_CHECKBOX: field.SetValue( False )
                    
                    field.Disable()
                    
                
            
        
    
    def _UpdatePendingInitialComments( self ):
        
        hashes_to_dump = self._sorted_media_hashes[ self._next_dump_index : ]
        
        for hash in hashes_to_dump:
            
            if hash == self._current_hash: self._FreezeCurrentMediaPostInfo()
            
            ( dump_status_enum, dump_status_string, post_field_info ) = self._hashes_to_dump_info[ hash ]
            
            new_post_field_info = []
            
            for ( name, field_type, value ) in post_field_info:
                
                if field_type == CC.FIELD_COMMENT:
                    
                    ( initial, append ) = value
                    
                    media = self._hashes_to_media[ hash ]
                    
                    initial = self._GetInitialComment( media )
                    
                    new_post_field_info.append( ( name, field_type, ( initial, append ) ) )
                    
                else: new_post_field_info.append( ( name, field_type, value ) )
                
            
            self._hashes_to_dump_info[ hash ] = ( dump_status_enum, dump_status_string, new_post_field_info )
            
            if hash == self._current_hash: self._ShowCurrentMedia()
            
        
    
    def CALLBACKDoneDump( self, hash, post_field_info, status, phrase ):
        
        self._actually_dumping = False
        
        if HC.options[ 'play_dumper_noises' ]:
            
            if status == 'success': HydrusAudioHandling.PlayNoise( 'success' )
            else: HydrusAudioHandling.PlayNoise( 'error' )
            
        
        if status == 'success':
            
            dump_status_enum = CC.DUMPER_DUMPED_OK
            dump_status_string = 'dumped ok'
            
            if hash == self._current_hash: self._controller.pub( 'set_focus', self._page_key, None )
            
            self._next_dump_time = HydrusData.GetNow() + self._flood_time
            
            self._num_dumped += 1
            
            self._progress_gauge.SetValue( self._num_dumped )
            
            self._next_dump_index += 1
            
        elif status == 'captcha':
            
            dump_status_enum = CC.DUMPER_RECOVERABLE_ERROR
            dump_status_string = 'captcha was incorrect'
            
            self._next_dump_time = HydrusData.GetNow() + 10
            
            new_post_field_info = []
            
            for ( name, field_type, value ) in post_field_info:
                
                if field_type == CC.FIELD_VERIFICATION_RECAPTCHA: new_post_field_info.append( ( name, field_type, None ) )
                else: new_post_field_info.append( ( name, field_type, value ) )
                
                if hash == self._current_hash:
                    
                    ( field_type, field, default ) = self._post_fields[ name ]
                    
                    field.Enable()
                    
                
            
            post_field_info = new_post_field_info
            
        elif status == 'too quick':
            
            dump_status_enum = CC.DUMPER_RECOVERABLE_ERROR
            dump_status_string = ''
            
            self._progress_info.SetLabelText( 'Flood limit hit, retrying.' )
            
            self._next_dump_time = HydrusData.GetNow() + self._flood_time
            
        elif status == 'big error':
            
            dump_status_enum = CC.DUMPER_UNRECOVERABLE_ERROR
            dump_status_string = ''
            
            HydrusData.ShowText( phrase )
            
            self._progress_info.SetLabelText( 'error: ' + phrase )
            
            self._start_button.Disable()
            
            self._timer.Stop()
            
        elif 'Thread specified does not exist' in phrase:
            
            dump_status_enum = CC.DUMPER_UNRECOVERABLE_ERROR
            dump_status_string = ''
            
            self._progress_info.SetLabelText( 'thread specified does not exist!' )
            
            self._start_button.Disable()
            
            self._timer.Stop()
            
        else:
            
            dump_status_enum = CC.DUMPER_UNRECOVERABLE_ERROR
            dump_status_string = phrase
            
            if hash == self._current_hash: self._controller.pub( 'set_focus', self._page_key, None )
            
            self._next_dump_time = HydrusData.GetNow() + self._flood_time
            
            self._next_dump_index += 1
            
        
        self._hashes_to_dump_info[ hash ] = ( dump_status_enum, dump_status_string, post_field_info )
        
        self._controller.pub( 'file_dumped', self._page_key, hash, dump_status_enum )
        
        if self._next_dump_index == len( self._sorted_media_hashes ):
            
            self._progress_info.SetLabelText( 'done - ' + str( self._num_dumped ) + ' dumped' )
            
            self._start_button.Disable()
            
            self._timer.Stop()
            
            self._dumping = False
            
        
    
    def EventCaptchaRefresh( self, event ):
        
        try:
            
            index = self._sorted_media_hashes.index( self._current_hash )
            
            if ( ( index + 1 ) - self._next_dump_index ) * ( self._flood_time + 10 ) > 5 * 60: event.Veto()
            
        except: event.Veto()
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'import_tag_options_changed': self._UpdatePendingInitialComments()
            else: event.Skip()
            
        
    
    def EventStartButton( self, event ):
        
        if self._start_button.GetLabelText() in ( 'start', 'continue' ):
            
            for ( name, ( field_type, field ) ) in self._thread_fields.items():
                
                if field_type == CC.FIELD_THREAD_ID:
                    
                    try: int( field.GetValue() )
                    except:
                        
                        # let's assume they put the url in
                        
                        value = field.GetValue()
                        
                        thread_id = value.split( '/' )[ -1 ]
                        
                        try: int( thread_id )
                        except:
                            
                            self._progress_info.SetLabelText( 'set thread_id field first' )
                            
                            return
                            
                        
                        field.SetValue( thread_id )
                        
                    
                
            
            for ( field_type, field ) in self._thread_fields.values(): field.Disable()
            
            self._dumping = True
            self._start_button.SetLabelText( 'pause' )
            
            if self._next_dump_time == 0: self._next_dump_time = HydrusData.GetNow() + 5
            
            # disable thread fields here
            
        else:
            
            for ( field_type, field ) in self._thread_fields.values(): field.Enable()
            
            self._dumping = False
            
            if self._num_dumped == 0: self._start_button.SetLabelText( 'start' )
            else: self._start_button.SetLabelText( 'continue' )
            
        
    
    def FocusChanged( self, page_key, media ):
        
        if page_key == self._page_key:
            
            if media is None: hash = None
            else: hash = media.GetHash()
            
            if hash != self._current_hash:
                
                old_hash = self._current_hash
                
                if old_hash is not None: self._FreezeCurrentMediaPostInfo()
                
                self._current_hash = hash
                
                self._ShowCurrentMedia()
                
            
        
    
    def SortedMediaPulse( self, page_key, sorted_media ):
        
        if page_key == self._page_key:
            
            self._sorted_media_hashes = [ media.GetHash() for media in sorted_media ]
            
            self._hashes_to_media = { hash : self._hashes_to_media[ hash ] for hash in self._sorted_media_hashes }
            
            new_hashes_to_dump_info = {}
            
            for ( hash, ( dump_status_enum, dump_status_string, post_field_info ) ) in self._hashes_to_dump_info.items():
                
                if hash not in self._sorted_media_hashes: continue
                
                new_post_field_info = []
                
                for ( name, field_type, value ) in post_field_info:
                    
                    if field_type == CC.FIELD_COMMENT:
                        
                        ( initial, append ) = value
                        
                        media = self._hashes_to_media[ hash ]
                        
                        initial = self._GetInitialComment( media )
                        
                        value = ( initial, append )
                        
                    
                    new_post_field_info.append( ( name, field_type, value ) )
                    
                
                new_hashes_to_dump_info[ hash ] = ( dump_status_enum, dump_status_string, new_post_field_info )
                
            
            self._hashes_to_dump_info = new_hashes_to_dump_info
            
            self._ShowCurrentMedia()
            
            if self._current_hash is None and len( self._sorted_media_hashes ) > 0:
                
                hash_to_select = self._sorted_media_hashes[0]
                
                media_to_select = self._hashes_to_media[ hash_to_select ]
                
                self._controller.pub( 'set_focus', self._page_key, media_to_select )
                
            
        
    
    def TestAbleToClose( self ):
        
        if self._dumping:
            
            with ClientGUIDialogs.DialogYesNo( self, 'This page is still dumping. Are you sure you want to close it?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_NO:
                    
                    raise HydrusExceptions.PermissionException()
                    
                
            
        
    
    def TIMEREvent( self, event ):
        
        if self._actually_dumping: return
        
        if self._dumping:
            
            time_left = self._next_dump_time - HydrusData.GetNow()
            
            if time_left < 1:
                
                try:
                    
                    hash = self._sorted_media_hashes[ self._next_dump_index ]
                    
                    wait = False
                    
                    if hash == self._current_hash: self._FreezeCurrentMediaPostInfo()
                    
                    ( dump_status_enum, dump_status_string, post_field_info ) = self._hashes_to_dump_info[ hash ]
                    
                    for ( name, field_type, value ) in post_field_info:
                        
                        if field_type == CC.FIELD_VERIFICATION_RECAPTCHA:
                            
                            if value is None:
                                
                                wait = True
                                
                                break
                                
                            else:
                                
                                ( challenge, bitmap, captcha_runs_out, entry, ready ) = value
                                
                                if HydrusData.TimeHasPassed( captcha_runs_out ) or not ready:
                                    
                                    wait = True
                                    
                                    break
                                    
                                
                            
                        
                    
                    if wait: self._progress_info.SetLabelText( 'waiting for captcha' )
                    else:
                        
                        self._progress_info.SetLabelText( 'dumping' ) # 100% cpu time here - may or may not be desirable
                        
                        post_fields = []
                        
                        for ( name, ( field_type, field ) ) in self._thread_fields.items():
                            
                            post_fields.append( ( name, field_type, field.GetValue() ) )
                            
                        
                        for ( name, field_type, value ) in post_field_info:
                            
                            if field_type == CC.FIELD_VERIFICATION_RECAPTCHA:
                                
                                ( challenge, bitmap, captcha_runs_out, entry, ready ) = value
                                
                                post_fields.append( ( 'recaptcha_challenge_field', field_type, challenge ) )
                                post_fields.append( ( 'recaptcha_response_field', field_type, entry ) )
                                
                            elif field_type == CC.FIELD_COMMENT:
                                
                                ( initial, append ) = value
                                
                                comment = initial
                                
                                if len( append ) > 0: comment += os.linesep * 2 + append
                                
                                post_fields.append( ( name, field_type, comment ) )
                                
                            else: post_fields.append( ( name, field_type, value ) )
                            
                        
                        media = self._hashes_to_media[ hash ]
                        
                        mime = media.GetMime()
                        
                        client_files_manager = self._controller.GetClientFilesManager()
                        
                        path = client_files_manager.GetFilePath( hash, mime )
                        
                        with open( path, 'rb' ) as f: file = f.read()
                        
                        post_fields.append( ( self._file_post_name, CC.FIELD_FILE, ( hash, mime, file ) ) )
                        
                        ( ct, body ) = GenerateDumpMultipartFormDataCTAndBody( post_fields )
                        
                        headers = {}
                        headers[ 'Content-Type' ] = ct
                        if self._have_4chan_pass: headers[ 'Cookie' ] = 'pass_enabled=1; pass_id=' + self._4chan_token
                        
                        self._actually_dumping = True
                        
                        self._controller.CallToThread( self._THREADDoDump, hash, post_field_info, headers, body )
                        
                    
                except Exception as e:
                    
                    ( status, phrase ) = ( 'big error', HydrusData.ToUnicode( e ) )
                    
                    wx.CallAfter( self.CALLBACKDoneDump, hash, post_field_info, status, phrase )
                    
                
            else: self._progress_info.SetLabelText( 'dumping next file in ' + str( time_left ) + ' seconds' )
            
        else:
            
            if self._num_dumped == 0: self._progress_info.SetLabelText( 'will dump to ' + self._imageboard.GetName() )
            else: self._progress_info.SetLabelText( 'paused after ' + str( self._num_dumped ) + ' files dumped' )
            
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_DUMPER ] = ManagementPanelDumper
'''
class ManagementPanelGalleryImport( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._gallery_downloader_panel = ClientGUICommon.StaticBox( self, 'gallery downloader' )
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self._gallery_downloader_panel, 'imports' )
        
        self._overall_status = wx.StaticText( self._import_queue_panel )
        self._current_action = wx.StaticText( self._import_queue_panel )
        self._file_gauge = ClientGUICommon.Gauge( self._import_queue_panel )
        self._overall_gauge = ClientGUICommon.Gauge( self._import_queue_panel )
        
        self._waiting_politely_indicator = ClientGUICommon.GetWaitingPolitelyControl( self._import_queue_panel, self._page_key )
        
        self._seed_cache_button = wx.BitmapButton( self._import_queue_panel, bitmap = CC.GlobalBMPs.seed_cache )
        self._seed_cache_button.Bind( wx.EVT_BUTTON, self.EventSeedCache )
        self._seed_cache_button.SetToolTipString( 'open detailed file import status' )
        
        self._files_pause_button = wx.BitmapButton( self._import_queue_panel, bitmap = CC.GlobalBMPs.pause )
        self._files_pause_button.Bind( wx.EVT_BUTTON, self.EventFilesPause )
        
        self._gallery_panel = ClientGUICommon.StaticBox( self._gallery_downloader_panel, 'gallery parser' )
        
        self._gallery_status = wx.StaticText( self._gallery_panel )
        
        self._gallery_pause_button = wx.BitmapButton( self._gallery_panel, bitmap = CC.GlobalBMPs.pause )
        self._gallery_pause_button.Bind( wx.EVT_BUTTON, self.EventGalleryPause )
        
        self._gallery_cancel_button = wx.BitmapButton( self._gallery_panel, bitmap = CC.GlobalBMPs.stop )
        self._gallery_cancel_button.Bind( wx.EVT_BUTTON, self.EventGalleryCancel )
        
        self._pending_queries_panel = ClientGUICommon.StaticBox( self._gallery_downloader_panel, 'pending queries' )
        
        self._pending_queries_listbox = wx.ListBox( self._pending_queries_panel, size = ( -1, 100 ) )
        
        self._advance_button = wx.Button( self._pending_queries_panel, label = u'\u2191' )
        self._advance_button.Bind( wx.EVT_BUTTON, self.EventAdvance )
        
        self._delete_button = wx.Button( self._pending_queries_panel, label = 'X' )
        self._delete_button.Bind( wx.EVT_BUTTON, self.EventDelete )
        
        self._delay_button = wx.Button( self._pending_queries_panel, label = u'\u2193' )
        self._delay_button.Bind( wx.EVT_BUTTON, self.EventDelay )
        
        self._query_input = wx.TextCtrl( self._pending_queries_panel, style = wx.TE_PROCESS_ENTER )
        self._query_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._query_paste = wx.Button( self._pending_queries_panel, label = 'paste queries' )
        self._query_paste.Bind( wx.EVT_BUTTON, self.EventPaste )
        
        self._get_tags_if_redundant = wx.CheckBox( self._gallery_downloader_panel, label = 'get tags even if file is already in db' )
        self._get_tags_if_redundant.Bind( wx.EVT_CHECKBOX, self.EventGetTagsIfRedundant )
        self._get_tags_if_redundant.SetToolTipString( 'only fetch tags from the gallery if the file is new' )
        
        self._file_limit = ClientGUICommon.NoneableSpinCtrl( self._gallery_downloader_panel, 'file limit', min = 1 )
        self._file_limit.Bind( wx.EVT_SPINCTRL, self.EventFileLimit )
        self._file_limit.SetToolTipString( 'per query, stop searching the gallery once this many files has been reached' )
        
        self._import_file_options = ClientGUICollapsible.CollapsibleOptionsImportFiles( self._gallery_downloader_panel )
        self._import_tag_options = ClientGUICollapsible.CollapsibleOptionsTags( self._gallery_downloader_panel )
        
        #
        
        button_sizer = wx.BoxSizer( wx.HORIZONTAL )
        
        button_sizer.AddF( self._gallery_pause_button, CC.FLAGS_VCENTER )
        button_sizer.AddF( self._gallery_cancel_button, CC.FLAGS_VCENTER )
        
        self._gallery_panel.AddF( self._gallery_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_panel.AddF( button_sizer, CC.FLAGS_LONE_BUTTON )
        
        #
        
        queue_buttons_vbox = wx.BoxSizer( wx.VERTICAL )
        
        queue_buttons_vbox.AddF( self._advance_button, CC.FLAGS_VCENTER )
        queue_buttons_vbox.AddF( self._delete_button, CC.FLAGS_VCENTER )
        queue_buttons_vbox.AddF( self._delay_button, CC.FLAGS_VCENTER )
        
        queue_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        queue_hbox.AddF( self._pending_queries_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        queue_hbox.AddF( queue_buttons_vbox, CC.FLAGS_VCENTER )
        
        input_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        input_hbox.AddF( self._query_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        input_hbox.AddF( self._query_paste, CC.FLAGS_VCENTER )
        
        self._pending_queries_panel.AddF( queue_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._pending_queries_panel.AddF( input_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        button_sizer = wx.BoxSizer( wx.HORIZONTAL )
        
        button_sizer.AddF( self._waiting_politely_indicator, CC.FLAGS_VCENTER )
        button_sizer.AddF( self._seed_cache_button, CC.FLAGS_VCENTER )
        button_sizer.AddF( self._files_pause_button, CC.FLAGS_VCENTER )
        
        self._import_queue_panel.AddF( self._overall_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( self._current_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( self._file_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( self._overall_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( button_sizer, CC.FLAGS_BUTTON_SIZER )
        
        self._gallery_downloader_panel.AddF( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.AddF( self._gallery_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.AddF( self._pending_queries_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.AddF( self._get_tags_if_redundant, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.AddF( self._file_limit, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.AddF( self._import_file_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.AddF( self._import_tag_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        
        vbox.AddF( self._gallery_downloader_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self._controller.sub( self, 'UpdateStatus', 'update_status' )
        
        self._gallery_import = self._management_controller.GetVariable( 'gallery_import' )
        
        gallery_identifier = self._gallery_import.GetGalleryIdentifier()
        
        ( namespaces, search_value ) = ClientDefaults.GetDefaultNamespacesAndSearchValue( gallery_identifier )
        
        self._import_tag_options.SetNamespaces( namespaces )
        self._query_input.SetValue( search_value )
        
        def file_download_hook( gauge_range, gauge_value ):
            
            self._file_gauge.SetRange( gauge_range )
            self._file_gauge.SetValue( gauge_value )
            
        
        self._gallery_import.SetDownloadHook( file_download_hook )
        
        ( import_file_options, import_tag_options, get_tags_if_redundant, file_limit ) = self._gallery_import.GetOptions()
        
        self._import_file_options.SetOptions( import_file_options )
        self._import_tag_options.SetOptions( import_tag_options )
        
        self._get_tags_if_redundant.SetValue( get_tags_if_redundant )
        self._file_limit.SetValue( file_limit )
        
        self._Update()
        
        self._gallery_import.Start( self._page_key )
        
    
    def _Update( self ):
        
        ( pending_queries, gallery_status, ( overall_status, ( overall_value, overall_range ) ), files_paused, gallery_paused, cancellable ) = self._gallery_import.GetStatus()
        
        if self._pending_queries_listbox.GetStrings() != pending_queries:
            
            selected_string = self._pending_queries_listbox.GetStringSelection()
            
            self._pending_queries_listbox.SetItems( pending_queries )
            
            selection_index = self._pending_queries_listbox.FindString( selected_string )
            
            if selection_index != wx.NOT_FOUND:
                
                self._pending_queries_listbox.Select( selection_index )
                
            
        
        if self._overall_status.GetLabelText() != overall_status:
            
            self._overall_status.SetLabelText( overall_status )
            
        
        self._overall_gauge.SetRange( overall_range )
        self._overall_gauge.SetValue( overall_value )
        
        if overall_value < overall_range:
            
            if files_paused:
                
                current_action = 'paused at ' + HydrusData.ConvertValueRangeToPrettyString( overall_value + 1, overall_range )
                
            else:
                
                current_action = 'processing ' + HydrusData.ConvertValueRangeToPrettyString( overall_value + 1, overall_range )
                
            
        else:
            
            current_action = ''
            
        
        if files_paused:
            
            if self._files_pause_button.GetBitmap() != CC.GlobalBMPs.play:
                
                self._files_pause_button.SetBitmap( CC.GlobalBMPs.play )
                
            
        else:
            
            if self._files_pause_button.GetBitmap() != CC.GlobalBMPs.pause:
                
                self._files_pause_button.SetBitmap( CC.GlobalBMPs.pause )
                
            
        
        if gallery_paused:
            
            if self._gallery_pause_button.GetBitmap() != CC.GlobalBMPs.play:
                
                self._gallery_pause_button.SetBitmap( CC.GlobalBMPs.play )
                
            
        else:
            
            if self._gallery_pause_button.GetBitmap() != CC.GlobalBMPs.pause:
                
                self._gallery_pause_button.SetBitmap( CC.GlobalBMPs.pause )
                
            
        
        if cancellable:
            
            self._gallery_cancel_button.Enable()
            
        else:
            
            self._gallery_cancel_button.Disable()
            
        
        if self._gallery_status.GetLabelText() != gallery_status:
            
            self._gallery_status.SetLabelText( gallery_status )
            
        
        if self._current_action.GetLabelText() != current_action:
            
            self._current_action.SetLabelText( current_action )
            
        
    
    def EventAdvance( self, event ):
        
        selection = self._pending_queries_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            query = self._pending_queries_listbox.GetString( selection )
            
            self._gallery_import.AdvanceQuery( query )
            
            self._Update()
            
        
    
    def EventDelay( self, event ):
        
        selection = self._pending_queries_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            query = self._pending_queries_listbox.GetString( selection )
            
            self._gallery_import.DelayQuery( query )
            
            self._Update()
            
        
    
    def EventDelete( self, event ):
        
        selection = self._pending_queries_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            query = self._pending_queries_listbox.GetString( selection )
            
            self._gallery_import.DeleteQuery( query )
            
            self._Update()
            
        
    
    def EventFileLimit( self, event ):
        
        self._gallery_import.SetFileLimit( self._file_limit.GetValue() )
        
        event.Skip()
        
    
    def EventFilesPause( self, event ):
        
        self._gallery_import.PausePlayFiles()
        
        self._Update()
        
    
    def EventGalleryCancel( self, event ):
        
        self._gallery_import.FinishCurrentQuery()
        
        self._Update()
        
    
    def EventGalleryPause( self, event ):
        
        self._gallery_import.PausePlayGallery()
        
        self._Update()
        
    
    def EventGetTagsIfRedundant( self, event ):
        
        self._gallery_import.SetGetTagsIfRedundant( self._get_tags_if_redundant.GetValue() )
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            query = self._query_input.GetValue()
            
            if query != '':
                
                self._gallery_import.PendQuery( query )
                
            
            self._query_input.SetValue( '' )
            
            self._Update()
            
        else:
            
            event.Skip()
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'import_file_options_changed':
                
                import_file_options = self._import_file_options.GetOptions()
                
                self._gallery_import.SetImportFileOptions( import_file_options )
                
            if command == 'import_tag_options_changed':
                
                import_tag_options = self._import_tag_options.GetOptions()
                
                self._gallery_import.SetImportTagOptions( import_tag_options )
                
            else: event.Skip()
            
        
    
    def EventPaste( self, event ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject()
            
            wx.TheClipboard.GetData( data )
            
            wx.TheClipboard.Close()
            
            raw_text = data.GetText()
            
            try:
                
                for query in HydrusData.SplitByLinesep( raw_text ):
                    
                    if query != '':
                        
                        self._gallery_import.PendQuery( query )
                        
                    
                
                self._Update()
                
            except:
                
                wx.MessageBox( 'I could not understand what was in the clipboard' )
                
            
        else:
            
            wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
    
    def EventSeedCache( self, event ):
        
        seed_cache = self._gallery_import.GetSeedCache()
        
        title = 'file import status'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIScrolledPanelsEdit.EditSeedCachePanel( frame, self._controller, seed_cache )
        
        frame.SetPanel( panel )
        
    
    def SetSearchFocus( self, page_key ):
        
        if page_key == self._page_key: self._query_input.SetFocus()
        
    
    def UpdateStatus( self, page_key ):
        
        if page_key == self._page_key:
            
            self._Update()
            
        

management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_GALLERY ] = ManagementPanelGalleryImport

class ManagementPanelHDDImport( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self, 'import summary' )
        
        self._overall_status = wx.StaticText( self._import_queue_panel )
        self._current_action = wx.StaticText( self._import_queue_panel )
        self._overall_gauge = ClientGUICommon.Gauge( self._import_queue_panel )
        
        self._seed_cache_button = wx.BitmapButton( self._import_queue_panel, bitmap = CC.GlobalBMPs.seed_cache )
        self._seed_cache_button.Bind( wx.EVT_BUTTON, self.EventSeedCache )
        self._seed_cache_button.SetToolTipString( 'open detailed file import status' )
        
        self._pause_button = wx.BitmapButton( self._import_queue_panel, bitmap = CC.GlobalBMPs.pause )
        self._pause_button.Bind( wx.EVT_BUTTON, self.EventPause )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        
        button_sizer = wx.BoxSizer( wx.HORIZONTAL )
        
        button_sizer.AddF( self._seed_cache_button, CC.FLAGS_VCENTER )
        button_sizer.AddF( self._pause_button, CC.FLAGS_VCENTER )
        
        self._import_queue_panel.AddF( self._overall_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( self._current_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( self._overall_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( button_sizer, CC.FLAGS_BUTTON_SIZER )
        
        vbox.AddF( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        self._controller.sub( self, 'UpdateStatus', 'update_status' )
        
        self._hdd_import = self._management_controller.GetVariable( 'hdd_import' )
        
        self._Update()
        
        self._hdd_import.Start( self._page_key )
        
    
    def _Update( self ):
        
        ( ( overall_status, ( overall_value, overall_range ) ), paused ) = self._hdd_import.GetStatus()
        
        if self._overall_status.GetLabelText() != overall_status:
            
            self._overall_status.SetLabelText( overall_status )
            
        
        self._overall_gauge.SetRange( overall_range )
        self._overall_gauge.SetValue( overall_value )
        
        if paused:
            
            current_action = 'paused at ' + HydrusData.ConvertValueRangeToPrettyString( overall_value + 1, overall_range )
            
            if self._pause_button.GetBitmap() != CC.GlobalBMPs.play:
                
                self._pause_button.SetBitmap( CC.GlobalBMPs.play )
                
            
        else:
            
            current_action = 'processing ' + HydrusData.ConvertValueRangeToPrettyString( overall_value + 1, overall_range )
            
            if self._pause_button.GetBitmap() != CC.GlobalBMPs.pause:
                
                self._pause_button.SetBitmap( CC.GlobalBMPs.pause )
                
            
        
        if overall_value < overall_range:
            
            if not self._pause_button.IsShown():
                
                self._pause_button.Show()
                self._current_action.Show()
                self._overall_gauge.Show()
                
                self.Layout()
                
            
        else:
            
            if self._pause_button.IsShown():
                
                self._pause_button.Hide()
                self._current_action.Hide()
                self._overall_gauge.Hide()
                
                self.Layout()
                
            
        
        if self._current_action.GetLabelText() != current_action:
            
            self._current_action.SetLabelText( current_action )
            
        
    
    def EventPause( self, event ):
        
        self._hdd_import.PausePlay()
        
        self._Update()
        
    
    def EventSeedCache( self, event ):
        
        seed_cache = self._hdd_import.GetSeedCache()
        
        title = 'file import status'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIScrolledPanelsEdit.EditSeedCachePanel( frame, self._controller, seed_cache )
        
        frame.SetPanel( panel )
        
    
    def TestAbleToClose( self ):
        
        ( ( overall_status, ( overall_value, overall_range ) ), paused ) = self._hdd_import.GetStatus()
        
        if overall_value < overall_range and not paused:
            
            with ClientGUIDialogs.DialogYesNo( self, 'This page is still importing. Are you sure you want to close it?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_NO:
                    
                    raise HydrusExceptions.PermissionException()
                    
                
            
        
    
    def UpdateStatus( self, page_key ):
        
        if page_key == self._page_key:
            
            self._Update()
            
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_HDD ] = ManagementPanelHDDImport

class ManagementPanelPageOfImagesImport( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._page_of_images_panel = ClientGUICommon.StaticBox( self, 'page of images downloader' )
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self._page_of_images_panel, 'imports' )
        
        self._parser_status = wx.StaticText( self._import_queue_panel )
        self._overall_status = wx.StaticText( self._import_queue_panel )
        self._current_action = wx.StaticText( self._import_queue_panel )
        self._file_gauge = ClientGUICommon.Gauge( self._import_queue_panel )
        self._overall_gauge = ClientGUICommon.Gauge( self._import_queue_panel )
        
        self._pause_button = wx.BitmapButton( self._import_queue_panel, bitmap = CC.GlobalBMPs.pause )
        self._pause_button.Bind( wx.EVT_BUTTON, self.EventPause )
        
        self._waiting_politely_indicator = ClientGUICommon.GetWaitingPolitelyControl( self._import_queue_panel, self._page_key )
        
        self._seed_cache_button = wx.BitmapButton( self._import_queue_panel, bitmap = CC.GlobalBMPs.seed_cache )
        self._seed_cache_button.Bind( wx.EVT_BUTTON, self.EventSeedCache )
        self._seed_cache_button.SetToolTipString( 'open detailed file import status' )
        
        button_sizer = wx.BoxSizer( wx.HORIZONTAL )
        
        button_sizer.AddF( self._waiting_politely_indicator, CC.FLAGS_VCENTER )
        button_sizer.AddF( self._seed_cache_button, CC.FLAGS_VCENTER )
        button_sizer.AddF( self._pause_button, CC.FLAGS_VCENTER )
        
        self._pending_page_urls_panel = ClientGUICommon.StaticBox( self._page_of_images_panel, 'pending page urls' )
        
        self._pending_page_urls_listbox = wx.ListBox( self._pending_page_urls_panel, size = ( -1, 100 ) )
        
        self._advance_button = wx.Button( self._pending_page_urls_panel, label = u'\u2191' )
        self._advance_button.Bind( wx.EVT_BUTTON, self.EventAdvance )
        
        self._delete_button = wx.Button( self._pending_page_urls_panel, label = 'X' )
        self._delete_button.Bind( wx.EVT_BUTTON, self.EventDelete )
        
        self._delay_button = wx.Button( self._pending_page_urls_panel, label = u'\u2193' )
        self._delay_button.Bind( wx.EVT_BUTTON, self.EventDelay )
        
        self._page_url_input = wx.TextCtrl( self._pending_page_urls_panel, style = wx.TE_PROCESS_ENTER )
        self._page_url_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._page_url_paste = wx.Button( self._pending_page_urls_panel, label = 'paste urls' )
        self._page_url_paste.Bind( wx.EVT_BUTTON, self.EventPaste )
        
        self._download_image_links = wx.CheckBox( self._page_of_images_panel, label = 'download image links' )
        self._download_image_links.Bind( wx.EVT_CHECKBOX, self.EventDownloadImageLinks )
        self._download_image_links.SetToolTipString( 'i.e. download the href url of an <a> tag if there is an <img> tag nested beneath it' )
        
        self._download_unlinked_images = wx.CheckBox( self._page_of_images_panel, label = 'download unlinked images' )
        self._download_unlinked_images.Bind( wx.EVT_CHECKBOX, self.EventDownloadUnlinkedImages )
        self._download_unlinked_images.SetToolTipString( 'i.e. download the src url of an <img> tag if there is no parent <a> tag' )
        
        self._import_file_options = ClientGUICollapsible.CollapsibleOptionsImportFiles( self._page_of_images_panel )
        
        #
        
        queue_buttons_vbox = wx.BoxSizer( wx.VERTICAL )
        
        queue_buttons_vbox.AddF( self._advance_button, CC.FLAGS_VCENTER )
        queue_buttons_vbox.AddF( self._delete_button, CC.FLAGS_VCENTER )
        queue_buttons_vbox.AddF( self._delay_button, CC.FLAGS_VCENTER )
        
        queue_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        queue_hbox.AddF( self._pending_page_urls_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        queue_hbox.AddF( queue_buttons_vbox, CC.FLAGS_VCENTER )
        
        input_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        input_hbox.AddF( self._page_url_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        input_hbox.AddF( self._page_url_paste, CC.FLAGS_VCENTER )
        
        self._pending_page_urls_panel.AddF( queue_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._pending_page_urls_panel.AddF( input_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        self._import_queue_panel.AddF( self._parser_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( self._overall_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( self._current_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( self._file_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( self._overall_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.AddF( button_sizer, CC.FLAGS_BUTTON_SIZER )
        
        self._page_of_images_panel.AddF( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._page_of_images_panel.AddF( self._pending_page_urls_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._page_of_images_panel.AddF( self._download_image_links, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._page_of_images_panel.AddF( self._download_unlinked_images, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._page_of_images_panel.AddF( self._import_file_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        
        vbox.AddF( self._page_of_images_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self._controller.sub( self, 'UpdateStatus', 'update_status' )
        
        self._page_of_images_import = self._management_controller.GetVariable( 'page_of_images_import' )
        
        def file_download_hook( gauge_range, gauge_value ):
            
            self._file_gauge.SetRange( gauge_range )
            self._file_gauge.SetValue( gauge_value )
            
        
        self._page_of_images_import.SetDownloadHook( file_download_hook )
        
        ( import_file_options, download_image_links, download_unlinked_images ) = self._page_of_images_import.GetOptions()
        
        self._import_file_options.SetOptions( import_file_options )
        
        self._download_image_links.SetValue( download_image_links )
        self._download_unlinked_images.SetValue( download_unlinked_images )
        
        self._Update()
        
        self._page_of_images_import.Start( self._page_key )
        
    
    def _Update( self ):
        
        ( pending_page_urls, parser_status, ( overall_status, ( overall_value, overall_range ) ), paused ) = self._page_of_images_import.GetStatus()
        
        if self._pending_page_urls_listbox.GetStrings() != pending_page_urls:
            
            selected_string = self._pending_page_urls_listbox.GetStringSelection()
            
            self._pending_page_urls_listbox.SetItems( pending_page_urls )
            
            selection_index = self._pending_page_urls_listbox.FindString( selected_string )
            
            if selection_index != wx.NOT_FOUND:
                
                self._pending_page_urls_listbox.Select( selection_index )
                
            
        
        if self._overall_status.GetLabelText() != overall_status:
            
            self._overall_status.SetLabelText( overall_status )
            
        
        self._overall_gauge.SetRange( overall_range )
        self._overall_gauge.SetValue( overall_value )
        
        if overall_value < overall_range:
            
            if paused:
                
                current_action = 'paused at ' + HydrusData.ConvertValueRangeToPrettyString( overall_value + 1, overall_range )
                
            else:
                
                current_action = 'processing ' + HydrusData.ConvertValueRangeToPrettyString( overall_value + 1, overall_range )
                
            
        else:
            
            current_action = ''
            
        
        if self._parser_status.GetLabelText() != parser_status:
            
            self._parser_status.SetLabelText( parser_status )
            
        
        if self._current_action.GetLabelText() != current_action:
            
            self._current_action.SetLabelText( current_action )
            
        
        if paused:
            
            if self._pause_button.GetBitmap() != CC.GlobalBMPs.play:
                
                self._pause_button.SetBitmap( CC.GlobalBMPs.play )
                
            
        else:
            
            if self._pause_button.GetBitmap() != CC.GlobalBMPs.pause:
                
                self._pause_button.SetBitmap( CC.GlobalBMPs.pause )
                
            
        
    
    def EventAdvance( self, event ):
        
        selection = self._pending_page_urls_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            page_url = self._pending_page_urls_listbox.GetString( selection )
            
            self._page_of_images_import.AdvancePageURL( page_url )
            
            self._Update()
            
        
    
    def EventDelay( self, event ):
        
        selection = self._pending_page_urls_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            page_url = self._pending_page_urls_listbox.GetString( selection )
            
            self._page_of_images_import.DelayPageURL( page_url )
            
            self._Update()
            
        
    
    def EventDelete( self, event ):
        
        selection = self._pending_page_urls_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            page_url = self._pending_page_urls_listbox.GetString( selection )
            
            self._page_of_images_import.DeletePageURL( page_url )
            
            self._Update()
            
        
    
    def EventDownloadImageLinks( self, event ):
        
        self._page_of_images_import.SetDownloadImageLinks( self._download_image_links.GetValue() )
        
    
    def EventDownloadUnlinkedImages( self, event ):
        
        self._page_of_images_import.SetDownloadUnlinkedImages( self._download_unlinked_images.GetValue() )
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            page_url = self._page_url_input.GetValue()
            
            if page_url != '':
                
                self._page_of_images_import.PendPageURL( page_url )
                
                self._page_url_input.SetValue( '' )
                
                self._Update()
                
            
        else:
            
            event.Skip()
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'import_file_options_changed':
                
                import_file_options = self._import_file_options.GetOptions()
                
                self._page_of_images_import.SetImportFileOptions( import_file_options )
                
            else: event.Skip()
            
        
    
    def EventPaste( self, event ):
    
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject()
            
            wx.TheClipboard.GetData( data )
            
            wx.TheClipboard.Close()
            
            raw_text = data.GetText()
            
            try:
                
                for page_url in HydrusData.SplitByLinesep( raw_text ):
                    
                    if page_url != '':
                        
                        self._page_of_images_import.PendPageURL( page_url )
                        
                    
                
                self._Update()
                
            except:
                
                wx.MessageBox( 'I could not understand what was in the clipboard' )
                
            
        else:
            
            wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
    
    def EventPause( self, event ):
        
        self._page_of_images_import.PausePlay()
        
        self._Update()
        
    
    def EventSeedCache( self, event ):
        
        seed_cache = self._page_of_images_import.GetSeedCache()
        
        title = 'file import status'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIScrolledPanelsEdit.EditSeedCachePanel( frame, self._controller, seed_cache )
        
        frame.SetPanel( panel )
        
    
    def SetSearchFocus( self, page_key ):
        
        if page_key == self._page_key: self._page_url_input.SetFocus()
        
    
    def UpdateStatus( self, page_key ):
        
        if page_key == self._page_key:
            
            self._Update()
            
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_PAGE_OF_IMAGES ] = ManagementPanelPageOfImagesImport

class ManagementPanelPetitions( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        self._petition_service_key = management_controller.GetKey( 'petition_service' )
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._service = self._controller.GetServicesManager().GetService( self._petition_service_key )
        self._can_ban = self._service.GetInfo( 'account' ).HasPermission( HC.MANAGE_USERS )
        
        self._num_petitions = None
        self._current_petition = None
        
        #
        
        self._petitions_info_panel = ClientGUICommon.StaticBox( self, 'petitions info' )
        
        self._num_petitions_text = wx.StaticText( self._petitions_info_panel )
        
        refresh_num_petitions = wx.Button( self._petitions_info_panel, label = 'refresh' )
        refresh_num_petitions.Bind( wx.EVT_BUTTON, self.EventRefreshNumPetitions )
        
        self._get_petition = wx.Button( self._petitions_info_panel, label = 'get petition' )
        self._get_petition.Bind( wx.EVT_BUTTON, self.EventGetPetition )
        self._get_petition.Disable()
        
        #
        
        self._petition_panel = ClientGUICommon.StaticBox( self, 'petition' )
        
        self._action_text = wx.StaticText( self._petition_panel, label = '' )
        
        self._reason_text = ClientGUICommon.SaneMultilineTextCtrl( self._petition_panel, style = wx.TE_READONLY )
        self._reason_text.SetMinSize( ( -1, 80 ) )
        
        self._contents = wx.CheckListBox( self._petition_panel, size = ( -1, 300 ) )
        self._contents.Bind( wx.EVT_LISTBOX_DCLICK, self.EventContentDoubleClick )
        
        self._process = wx.Button( self._petition_panel, label = 'process' )
        self._process.Bind( wx.EVT_BUTTON, self.EventProcess )
        self._process.SetForegroundColour( ( 0, 128, 0 ) )
        self._process.Disable()
        
        self._modify_petitioner = wx.Button( self._petition_panel, label = 'modify petitioner' )
        self._modify_petitioner.Bind( wx.EVT_BUTTON, self.EventModifyPetitioner )
        self._modify_petitioner.Disable()
        if not self._can_ban: self._modify_petitioner.Hide()
        
        #
        
        num_petitions_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        num_petitions_hbox.AddF( self._num_petitions_text, CC.FLAGS_EXPAND_BOTH_WAYS )
        num_petitions_hbox.AddF( refresh_num_petitions, CC.FLAGS_VCENTER )
        
        self._petitions_info_panel.AddF( num_petitions_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._petitions_info_panel.AddF( self._get_petition, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._petition_panel.AddF( wx.StaticText( self._petition_panel, label = 'Double click a petition to see its files, if it has them.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.AddF( self._action_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.AddF( self._reason_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.AddF( self._contents, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._petition_panel.AddF( self._process, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.AddF( self._modify_petitioner, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        self._MakeCollect( vbox )
        
        vbox.AddF( self._petitions_info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._petition_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        wx.CallAfter( self.EventRefreshNumPetitions, None )
        
        self._controller.sub( self, 'RefreshQuery', 'refresh_query' )
        
    
    def _DrawCurrentPetition( self ):
        
        hashes = []
        
        if self._current_petition is None:
            
            self._action_text.SetLabelText( '' )
            self._reason_text.SetValue( '' )
            self._contents.Clear()
            self._process.Disable()
            
            if self._can_ban:
                
                self._modify_petitioner.Disable()
                
            
        else:
            
            ( action_text, action_colour ) = self._current_petition.GetActionTextAndColour()
            
            self._action_text.SetLabelText( action_text )
            self._action_text.SetForegroundColour( action_colour )
            
            reason = self._current_petition.GetReason()
            
            self._reason_text.SetValue( reason )
            
            contents = self._current_petition.GetContents()
            
            self._contents.Clear()
            
            for content in contents:
                
                self._contents.Append( content.ToString(), content )
                
            
            self._contents.SetChecked( range( self._contents.GetCount() ) )
            
            self._process.Enable()
            
            if self._can_ban:
                
                self._modify_petitioner.Enable()
                
            
        
        self._ShowHashes( [] )
        
    
    def _ShowHashes( self, hashes ):
        
        file_service_key = self._management_controller.GetKey( 'file_service' )
    
        with wx.BusyCursor(): media_results = self._controller.Read( 'media_results', hashes )
        
        panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, file_service_key, media_results )
        
        panel.Collect( self._page_key, self._collect_by.GetChoice() )
        
        panel.Sort( self._page_key, self._sort_by.GetChoice() )
        
        self._controller.pub( 'swap_media_panel', self._page_key, panel )
        
    
    def _DrawNumPetitions( self ):
        
        self._num_petitions_text.SetLabelText( HydrusData.ConvertIntToPrettyString( self._num_petitions ) + ' petitions' )
        
        if self._num_petitions > 0: self._get_petition.Enable()
        else: self._get_petition.Disable()
        
    
    def EventContentDoubleClick( self, event ):
        
        selection = self._contents.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            content = self._contents.GetClientData( selection )
            
            if content.HasHashes():
                
                self._ShowHashes( content.GetHashes() )
                
            
        
    
    def EventProcess( self, event ):
        
        approved_contents = []
        denied_contents = []
        
        for index in range( self._contents.GetCount() ):
            
            content = self._contents.GetClientData( index )
            
            if self._contents.IsChecked( index ):
                
                approved_contents.append( content )
                
            else:
                
                denied_contents.append( content )
                
            
        
        if len( approved_contents ) > 0:
            
            for chunk_of_approved_contents in HydrusData.SplitListIntoChunks( approved_contents, 10 ):
                
                update = self._current_petition.GetApproval( chunk_of_approved_contents )
                
                self._service.Request( HC.POST, 'content_update_package', { 'update' : update } )
                
                self._controller.Write( 'content_updates', { self._petition_service_key : update.GetContentUpdates( for_client = True ) } )
                
            
        
        if len( denied_contents ) > 0:
            
            for chunk_of_denied_contents in HydrusData.SplitListIntoChunks( denied_contents, 10 ):
                
                update = self._current_petition.GetDenial( chunk_of_denied_contents )
                
                self._service.Request( HC.POST, 'content_update_package', { 'update' : update } )
                
                self._controller.Write( 'content_updates', { self._petition_service_key : update.GetContentUpdates( for_client = True ) } )
                
            
        
        self._current_petition = None
        
        self._DrawCurrentPetition()
        
        self.EventRefreshNumPetitions( event )
        
    
    def EventGetPetition( self, event ):
        
        def do_it():
            
            self._current_petition = self._service.Request( HC.GET, 'petition' )
            
            wx.CallAfter( self._DrawCurrentPetition )
            
        
        self._current_petition = None
        
        self._DrawCurrentPetition()
        
        self._controller.CallToThread( do_it )
        
    
    def EventModifyPetitioner( self, event ):
        
        with ClientGUIDialogs.DialogModifyAccounts( self, self._petition_service_key, ( self._current_petition.GetPetitionerIdentifier(), ) ) as dlg: dlg.ShowModal()
        
    
    def EventRefreshNumPetitions( self, event ):
        
        def do_it():
            
            try:
                
                response = self._service.Request( HC.GET, 'num_petitions' )
                
                self._num_petitions = response[ 'num_petitions' ]
                
                wx.CallAfter( self._DrawNumPetitions )
                
                if self._num_petitions > 0 and self._current_petition is None:
                    
                    wx.CallAfter( self.EventGetPetition, None )
                    
                
            except Exception as e:
                
                wx.CallAfter( self._num_petitions_text.SetLabel, 'Error' )
                
                raise
                
            
        
        self._num_petitions_text.SetLabelText( u'Fetching\u2026' )
        
        self._controller.CallToThread( do_it )
        
    
    def RefreshQuery( self, page_key ):
        
        if page_key == self._page_key: self._DrawCurrentPetition()
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_PETITIONS ] = ManagementPanelPetitions

class ManagementPanelQuery( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        file_search_context = self._management_controller.GetVariable( 'file_search_context' )
        
        self._search_enabled = self._management_controller.GetVariable( 'search_enabled' )
        
        self._query_key = ClientThreading.JobKey( cancellable = True )
        
        initial_predicates = file_search_context.GetPredicates()
        
        if self._search_enabled:
            
            self._search_panel = ClientGUICommon.StaticBox( self, 'search' )
            
            self._current_predicates_box = ClientGUICommon.ListBoxTagsPredicates( self._search_panel, self._page_key, initial_predicates )
            
            synchronised = self._management_controller.GetVariable( 'synchronised' )
            
            self._searchbox = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._search_panel, self._page_key, file_search_context, media_callable = self._page.GetMedia, synchronised = synchronised )
            self._search_panel.AddF( self._current_predicates_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._search_panel.AddF( self._searchbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        self._MakeCollect( vbox )
        
        if self._search_enabled: vbox.AddF( self._search_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        if len( initial_predicates ) > 0 and not file_search_context.IsComplete():
            
            wx.CallAfter( self._DoQuery )
            
        
        self._controller.sub( self, 'AddMediaResultsFromQuery', 'add_media_results_from_query' )
        self._controller.sub( self, 'SearchImmediately', 'notify_search_immediately' )
        self._controller.sub( self, 'ShowQuery', 'file_query_done' )
        self._controller.sub( self, 'RefreshQuery', 'refresh_query' )
        self._controller.sub( self, 'ChangeFileServicePubsub', 'change_file_service' )
        
    
    def _DoQuery( self ):
        
        self._controller.ResetIdleTimer()
        
        self._query_key.Cancel()
        
        self._query_key = ClientThreading.JobKey()
        
        if self._management_controller.GetVariable( 'search_enabled' ) and self._management_controller.GetVariable( 'synchronised' ):
            
            try:
                
                file_search_context = self._searchbox.GetFileSearchContext()
                
                current_predicates = self._current_predicates_box.GetPredicates()
                
                file_search_context.SetPredicates( current_predicates )
                
                self._management_controller.SetVariable( 'file_search_context', file_search_context )
                
                file_service_key = file_search_context.GetFileServiceKey()
                
                if len( current_predicates ) > 0:
                    
                    self._controller.StartFileQuery( self._query_key, file_search_context )
                    
                    panel = ClientGUIMedia.MediaPanelLoading( self._page, self._page_key, file_service_key )
                    
                else:
                    
                    panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, file_service_key, [] )
                    
                
                self._controller.pub( 'swap_media_panel', self._page_key, panel )
                
            except: wx.MessageBox( traceback.format_exc() )
            
        
    
    def _MakeCurrentSelectionTagsBox( self, sizer ):
        
        tags_box = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'selection tags' )
        
        if self._search_enabled:
            
            t = ClientGUICommon.ListBoxTagsSelectionManagementPanel( tags_box, self._page_key, predicates_callable = self._current_predicates_box.GetPredicates )
            
            file_search_context = self._management_controller.GetVariable( 'file_search_context' )
            
            tag_service_key = file_search_context.GetTagServiceKey()
            
            t.ChangeTagService( tag_service_key )
            
        else:
            
            t = ClientGUICommon.ListBoxTagsSelectionManagementPanel( tags_box, self._page_key )
            
        
        tags_box.SetTagsBox( t )
        
        sizer.AddF( tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def AddMediaResultsFromQuery( self, query_key, media_results ):
        
        if query_key == self._query_key: self._controller.pub( 'add_media_results', self._page_key, media_results, append = False )
        
    
    def ChangeFileServicePubsub( self, page_key, service_key ):
        
        if page_key == self._page_key:
            
            self._management_controller.SetKey( 'file_service', service_key )
            
        
    
    def CleanBeforeDestroy( self ):
        
        ManagementPanel.CleanBeforeDestroy( self )
        
        self._query_key.Cancel()
        
    
    def GetPredicates( self ):
        
        if self._search_enabled:
            
            return self._current_predicates_box.GetPredicates()
            
        else:
            
            return []
            
        
    
    def RefreshQuery( self, page_key ):
        
        if page_key == self._page_key:
            
            self._DoQuery()
            
        
    
    def SearchImmediately( self, page_key, value ):
        
        if page_key == self._page_key:
            
            self._management_controller.SetVariable( 'synchronised', value )
            
            self._DoQuery()
            
        
    
    def SetSearchFocus( self, page_key ):
        
        if page_key == self._page_key:
            
            try: self._searchbox.SetFocus() # there's a chance this doesn't exist!
            except: self._controller.pub( 'set_media_focus' )
            
        
    
    def ShowQuery( self, query_key, media_results ):
        
        if query_key == self._query_key:
            
            current_predicates = self._current_predicates_box.GetPredicates()
            
            file_service_key = self._management_controller.GetKey( 'file_service' )
            
            panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, file_service_key, media_results )
            
            panel.Collect( self._page_key, self._collect_by.GetChoice() )
            
            panel.Sort( self._page_key, self._sort_by.GetChoice() )
            
            self._controller.pub( 'swap_media_panel', self._page_key, panel )
            
        

management_panel_types_to_classes[ MANAGEMENT_TYPE_QUERY ] = ManagementPanelQuery

class ManagementPanelThreadWatcherImport( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._thread_watcher_panel = ClientGUICommon.StaticBox( self, 'thread watcher' )
        
        self._thread_input = wx.TextCtrl( self._thread_watcher_panel, style = wx.TE_PROCESS_ENTER )
        self._thread_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._options_panel = wx.Panel( self._thread_watcher_panel )
        
        self._watcher_status = wx.StaticText( self._options_panel )
        self._overall_status = wx.StaticText( self._options_panel )
        self._current_action = wx.StaticText( self._options_panel )
        self._file_gauge = ClientGUICommon.Gauge( self._options_panel )
        self._overall_gauge = ClientGUICommon.Gauge( self._options_panel )
        
        ( times_to_check, check_period ) = HC.options[ 'thread_checker_timings' ]
        
        self._thread_times_to_check = wx.SpinCtrl( self._options_panel, size = ( 60, -1 ), min = 0, max = 100 )
        self._thread_times_to_check.SetValue( times_to_check )
        self._thread_times_to_check.Bind( wx.EVT_SPINCTRL, self.EventTimesToCheck )
        
        self._thread_check_period = ClientGUICommon.TimeDeltaButton( self._options_panel, min = 30, hours = True, minutes = True, seconds = True )
        self._thread_check_period.SetValue( check_period )
        self._thread_check_period.Bind( ClientGUICommon.EVT_TIME_DELTA, self.EventCheckPeriod )
        
        self._thread_check_now_button = wx.Button( self._options_panel, label = 'check now' )
        self._thread_check_now_button.Bind( wx.EVT_BUTTON, self.EventCheckNow )
        
        self._waiting_politely_indicator = ClientGUICommon.GetWaitingPolitelyControl( self._options_panel, self._page_key )
        
        self._seed_cache_button = wx.BitmapButton( self._options_panel, bitmap = CC.GlobalBMPs.seed_cache )
        self._seed_cache_button.Bind( wx.EVT_BUTTON, self.EventSeedCache )
        self._seed_cache_button.SetToolTipString( 'open detailed file import status' )
        
        self._pause_button = wx.BitmapButton( self._options_panel, bitmap = CC.GlobalBMPs.pause )
        self._pause_button.Bind( wx.EVT_BUTTON, self.EventPause )
        
        self._import_file_options = ClientGUICollapsible.CollapsibleOptionsImportFiles( self._thread_watcher_panel )
        self._import_tag_options = ClientGUICollapsible.CollapsibleOptionsTags( self._thread_watcher_panel, namespaces = [ 'filename' ] )
        
        #
        
        hbox_1 = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox_1.AddF( wx.StaticText( self._options_panel, label = 'check ' ), CC.FLAGS_VCENTER )
        hbox_1.AddF( self._thread_times_to_check, CC.FLAGS_VCENTER )
        hbox_1.AddF( wx.StaticText( self._options_panel, label = ' more times' ), CC.FLAGS_VCENTER )
        
        hbox_2 = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox_2.AddF( wx.StaticText( self._options_panel, label = 'check every ' ), CC.FLAGS_VCENTER )
        hbox_2.AddF( self._thread_check_period, CC.FLAGS_VCENTER )
        
        button_sizer = wx.BoxSizer( wx.HORIZONTAL )
        
        button_sizer.AddF( self._thread_check_now_button, CC.FLAGS_VCENTER )
        button_sizer.AddF( self._waiting_politely_indicator, CC.FLAGS_VCENTER )
        button_sizer.AddF( self._seed_cache_button, CC.FLAGS_VCENTER )
        button_sizer.AddF( self._pause_button, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._watcher_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._overall_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._current_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._file_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._overall_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( hbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( hbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( button_sizer, CC.FLAGS_BUTTON_SIZER )
        
        self._options_panel.SetSizer( vbox )
        
        self._thread_watcher_panel.AddF( self._thread_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._thread_watcher_panel.AddF( self._options_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._thread_watcher_panel.AddF( self._import_file_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._thread_watcher_panel.AddF( self._import_tag_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        
        vbox.AddF( self._thread_watcher_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self._controller.sub( self, 'UpdateStatus', 'update_status' )
        self._controller.sub( self, 'DecrementTimesToCheck', 'decrement_times_to_check' )
        
        self._thread_watcher_import = self._management_controller.GetVariable( 'thread_watcher_import' )
        
        def file_download_hook( gauge_range, gauge_value ):
            
            self._file_gauge.SetRange( gauge_range )
            self._file_gauge.SetValue( gauge_value )
            
        
        self._thread_watcher_import.SetDownloadHook( file_download_hook )
        
        if self._thread_watcher_import.HasThread():
            
            ( thread_url, import_file_options, import_tag_options, times_to_check, check_period ) = self._thread_watcher_import.GetOptions()
            
            self._thread_input.SetValue( thread_url )
            self._thread_input.SetEditable( False )
            
            self._import_file_options.SetOptions( import_file_options )
            self._import_tag_options.SetOptions( import_tag_options )
            
            self._thread_times_to_check.SetValue( times_to_check )
            self._thread_check_period.SetValue( check_period )
            
            self._thread_watcher_import.Start( self._page_key )
            
        
        self._Update()
        
    
    def _Update( self ):
        
        if self._thread_watcher_import.HasThread():
            
            if not self._options_panel.IsShown():
                
                self._options_panel.Show()
                
                self.Layout()
                
            
        else:
            
            if self._options_panel.IsShown():
                
                self._options_panel.Hide()
                
                self.Layout()
                
            
        
        ( watcher_status, ( overall_status, ( overall_value, overall_range ) ), check_now, paused ) = self._thread_watcher_import.GetStatus()
        
        if self._overall_status.GetLabelText() != overall_status:
            
            self._overall_status.SetLabelText( overall_status )
            
        
        self._overall_gauge.SetRange( overall_range )
        self._overall_gauge.SetValue( overall_value )
        
        if overall_value < overall_range:
            
            if paused:
                
                current_action = 'paused at ' + HydrusData.ConvertValueRangeToPrettyString( overall_value + 1, overall_range )
                
            else:
                
                current_action = 'processing ' + HydrusData.ConvertValueRangeToPrettyString( overall_value + 1, overall_range )
                
            
        else:
            
            current_action = ''
            
        
        if paused:
            
            if self._thread_times_to_check.GetValue() > 0 or check_now:
                
                watcher_status = 'checking paused'
                
            
            if self._pause_button.GetBitmap() != CC.GlobalBMPs.play:
                
                self._pause_button.SetBitmap( CC.GlobalBMPs.play )
                
            
        else:
            
            if self._pause_button.GetBitmap() != CC.GlobalBMPs.pause:
                
                self._pause_button.SetBitmap( CC.GlobalBMPs.pause )
                
            
        
        if check_now:
            
            self._thread_check_now_button.Disable()
            
        else:
            
            self._thread_check_now_button.Enable()
            
        
        if self._watcher_status.GetLabelText() != watcher_status:
            
            self._watcher_status.SetLabelText( watcher_status )
            
        
        if self._current_action.GetLabelText() != current_action:
            
            self._current_action.SetLabelText( current_action )
            
        
    
    def DecrementTimesToCheck( self, page_key ):
        
        if page_key == self._page_key:
            
            current_value = self._thread_times_to_check.GetValue()
            
            new_value = max( 0, current_value - 1 )
            
            self._thread_times_to_check.SetValue( new_value )
            
        
    
    def EventCheckNow( self, event ):
        
        self._thread_watcher_import.CheckNow()
        
        self._Update()
        
    
    def EventCheckPeriod( self, event ):
        
        check_period = self._thread_check_period.GetValue()
        
        self._thread_watcher_import.SetCheckPeriod( check_period )
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            thread_url = self._thread_input.GetValue()
            
            if thread_url == '': return
            
            try:
                
                ( thread_url, host, board, thread_id ) = ClientDownloading.ParseImageboardThreadURL( thread_url )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                return
                
            
            self._thread_input.SetEditable( False )
            
            self._thread_watcher_import.SetThreadURL( thread_url )
            
            self._thread_watcher_import.Start( self._page_key )
            
        else: event.Skip()
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'import_file_options_changed':
                
                import_file_options = self._import_file_options.GetOptions()
                
                self._thread_watcher_import.SetImportFileOptions( import_file_options )
                
            elif command == 'import_tag_options_changed':
                
                import_tag_options = self._import_tag_options.GetOptions()
                
                self._thread_watcher_import.SetImportTagOptions( import_tag_options )
                
            else: event.Skip()
            
        
    
    def EventPause( self, event ):
        
        self._thread_watcher_import.PausePlay()
        
        self._Update()
        
    
    def EventSeedCache( self, event ):
        
        seed_cache = self._thread_watcher_import.GetSeedCache()
        
        title = 'file import status'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIScrolledPanelsEdit.EditSeedCachePanel( frame, self._controller, seed_cache )
        
        frame.SetPanel( panel )
        
    
    def EventTimesToCheck( self, event ):
        
        times_to_check = self._thread_times_to_check.GetValue()
        
        self._thread_watcher_import.SetTimesToCheck( times_to_check )
        
    
    def SetSearchFocus( self, page_key ):
        
        if page_key == self._page_key and self._thread_input.IsEditable():
            
            self._thread_input.SetFocus()
            
        
    
    def TestAbleToClose( self ):
        
        if self._thread_watcher_import.HasThread():
            
            ( watcher_status, ( overall_status, ( overall_value, overall_range ) ), check_now, paused ) = self._thread_watcher_import.GetStatus()
            
            if overall_value < overall_range and not paused:
                
                with ClientGUIDialogs.DialogYesNo( self, 'This page is still importing. Are you sure you want to close it?' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_NO:
                        
                        raise HydrusExceptions.PermissionException()
                        
                    
                
            
        
    
    def UpdateStatus( self, page_key ):
        
        if page_key == self._page_key:
            
            self._Update()
            
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_THREAD_WATCHER ] = ManagementPanelThreadWatcherImport

class ManagementPanelURLsImport( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._url_panel = ClientGUICommon.StaticBox( self, 'raw url downloader' )
        
        self._overall_status = wx.StaticText( self._url_panel )
        self._current_action = wx.StaticText( self._url_panel )
        self._file_gauge = ClientGUICommon.Gauge( self._url_panel )
        self._overall_gauge = ClientGUICommon.Gauge( self._url_panel )
        
        self._pause_button = wx.BitmapButton( self._url_panel, bitmap = CC.GlobalBMPs.pause )
        self._pause_button.Bind( wx.EVT_BUTTON, self.EventPause )
        
        self._waiting_politely_indicator = ClientGUICommon.GetWaitingPolitelyControl( self._url_panel, self._page_key )
        
        self._seed_cache_button = wx.BitmapButton( self._url_panel, bitmap = CC.GlobalBMPs.seed_cache )
        self._seed_cache_button.Bind( wx.EVT_BUTTON, self.EventSeedCache )
        self._seed_cache_button.SetToolTipString( 'open detailed file import status' )
        
        self._url_input = wx.TextCtrl( self._url_panel, style = wx.TE_PROCESS_ENTER )
        self._url_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._url_paste = wx.Button( self._url_panel, label = 'paste urls' )
        self._url_paste.Bind( wx.EVT_BUTTON, self.EventPaste )
        
        self._import_file_options = ClientGUICollapsible.CollapsibleOptionsImportFiles( self._url_panel )
        
        #
        
        button_sizer = wx.BoxSizer( wx.HORIZONTAL )
        
        button_sizer.AddF( self._waiting_politely_indicator, CC.FLAGS_VCENTER )
        button_sizer.AddF( self._seed_cache_button, CC.FLAGS_VCENTER )
        button_sizer.AddF( self._pause_button, CC.FLAGS_VCENTER )
        
        input_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        input_hbox.AddF( self._url_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        input_hbox.AddF( self._url_paste, CC.FLAGS_VCENTER )
        
        self._url_panel.AddF( self._overall_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.AddF( self._current_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.AddF( self._file_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.AddF( self._overall_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.AddF( button_sizer, CC.FLAGS_BUTTON_SIZER )
        self._url_panel.AddF( input_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._url_panel.AddF( self._import_file_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        
        vbox.AddF( self._url_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self._controller.sub( self, 'UpdateStatus', 'update_status' )
        
        self._urls_import = self._management_controller.GetVariable( 'urls_import' )
        
        def file_download_hook( gauge_range, gauge_value ):
            
            self._file_gauge.SetRange( gauge_range )
            self._file_gauge.SetValue( gauge_value )
            
        
        self._urls_import.SetDownloadHook( file_download_hook )
        
        import_file_options = self._urls_import.GetOptions()
        
        self._import_file_options.SetOptions( import_file_options )
        
        self._Update()
        
        self._urls_import.Start( self._page_key )
        
    
    def _Update( self ):
        
        ( ( overall_status, ( overall_value, overall_range ) ), paused ) = self._urls_import.GetStatus()
        
        if self._overall_status.GetLabelText() != overall_status:
            
            self._overall_status.SetLabelText( overall_status )
            
        
        self._overall_gauge.SetRange( overall_range )
        self._overall_gauge.SetValue( overall_value )
        
        if overall_value < overall_range:
            
            if paused:
                
                current_action = 'paused at ' + HydrusData.ConvertValueRangeToPrettyString( overall_value + 1, overall_range )
                
            else:
                
                current_action = 'processing ' + HydrusData.ConvertValueRangeToPrettyString( overall_value + 1, overall_range )
                
            
        else:
            
            current_action = ''
            
        
        if self._current_action.GetLabelText() != current_action:
            
            self._current_action.SetLabelText( current_action )
            
        
        if paused:
            
            if self._pause_button.GetBitmap() != CC.GlobalBMPs.play:
                
                self._pause_button.SetBitmap( CC.GlobalBMPs.play )
                
            
        else:
            
            if self._pause_button.GetBitmap() != CC.GlobalBMPs.pause:
                
                self._pause_button.SetBitmap( CC.GlobalBMPs.pause )
                
            
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            url = self._url_input.GetValue()
            
            if url != '':
                
                self._urls_import.PendURLs( ( url, ) )
                
                self._url_input.SetValue( '' )
                
                self._Update()
                
            
        else:
            
            event.Skip()
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'import_file_options_changed':
                
                import_file_options = self._import_file_options.GetOptions()
                
                self._urls_import.SetImportFileOptions( import_file_options )
                
            else:
                
                event.Skip()
                
            
        
    
    def EventPaste( self, event ):
    
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject()
            
            wx.TheClipboard.GetData( data )
            
            wx.TheClipboard.Close()
            
            raw_text = data.GetText()
            
            try:
                
                urls = HydrusData.SplitByLinesep( raw_text )
                
                if len( urls ) > 0:
                    
                    self._urls_import.PendURLs( urls )
                    
                
                self._Update()
                
            except:
                
                wx.MessageBox( 'I could not understand what was in the clipboard' )
                
            
        else:
            
            wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
    
    def EventPause( self, event ):
        
        self._urls_import.PausePlay()
        
        self._Update()
        
    
    def EventSeedCache( self, event ):
        
        seed_cache = self._urls_import.GetSeedCache()
        
        title = 'file import status'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIScrolledPanelsEdit.EditSeedCachePanel( frame, self._controller, seed_cache )
        
        frame.SetPanel( panel )
        
    
    def SetSearchFocus( self, page_key ):
        
        if page_key == self._page_key: self._url_input.SetFocus()
        
    
    def UpdateStatus( self, page_key ):
        
        if page_key == self._page_key:
            
            self._Update()
            
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_URLS ] = ManagementPanelURLsImport
