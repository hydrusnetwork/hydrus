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
import ClientGUICanvas
import ClientGUICollapsible
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIListBoxes
import ClientGUIMedia
import ClientGUIMenus
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
MANAGEMENT_TYPE_DUPLICATE_FILTER = 8

management_panel_types_to_classes = {}

def CreateManagementController( management_type, file_service_key = None ):
    
    if file_service_key is None:
        
        file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
        
    
    management_controller = ManagementController()
    
    # sort
    # collect
    # nah, these are only valid for types with regular file lists
    
    management_controller.SetType( management_type )
    management_controller.SetKey( 'file_service', file_service_key )
    
    return management_controller
    
def CreateManagementControllerDuplicateFilter():
    
    management_controller = CreateManagementController( MANAGEMENT_TYPE_DUPLICATE_FILTER )
    
    management_controller.SetKey( 'duplicate_filter_file_domain', CC.LOCAL_FILE_SERVICE_KEY )
    
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
    
    if petition_service_type in HC.LOCAL_FILE_SERVICES or petition_service_type == HC.FILE_REPOSITORY: file_service_key = petition_service_key
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
        
    
    def _InitialiseDefaults( self ):
        
        if self._management_type == MANAGEMENT_TYPE_DUPLICATE_FILTER:
            
            self._keys[ 'duplicate_filter_file_domain' ] = CC.LOCAL_FILE_SERVICE_KEY
            
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._management_type, serialisable_keys, serialisable_simples, serialisables ) = serialisable_info
        
        self._InitialiseDefaults()
        
        self._keys.update( { name : key.decode( 'hex' ) for ( name, key ) in serialisable_keys.items() } )
        
        if 'file_service' in self._keys:
            
            if not HydrusGlobals.client_controller.GetServicesManager().ServiceExists( self._keys[ 'file_service' ] ):
                
                self._keys[ 'file_service' ] = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
                
            
        
        self._simples.update( dict( serialisable_simples ) )
        
        self._serialisables.update( { name : HydrusSerialisable.CreateFromSerialisableTuple( value ) for ( name, value ) in serialisables.items() } )
        
    
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
        
        self._InitialiseDefaults()
        
    
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
        
        t = ClientGUIListBoxes.ListBoxTagsSelectionManagementPanel( tags_box, self._page_key )
        
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
    
class ManagementPanelDuplicateFilter( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._job = None
        self._job_key = None
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'refresh', 'This panel does not update itself when files are added or deleted elsewhere in the client. Hitting this will refresh the numbers from the database.', self._RefreshAndUpdateStatus ) )
        menu_items.append( ( 'normal', 'reset potential duplicates', 'This will delete all the potential duplicate pairs found so far and reset their files\' search status.', self._ResetUnknown ) )
        menu_items.append( ( 'separator', 0, 0, 0 ) )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'maintain_similar_files_duplicate_pairs_during_idle' )
        
        menu_items.append( ( 'check', 'search for duplicate pairs at the current distance during normal db maintenance', 'Tell the client to find duplicate pairs in its normal db maintenance cycles, whether you have that set to idle or shutdown time.', check_manager ) )
        
        self._cog_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.cog, menu_items )
        
        self._preparing_panel = ClientGUICommon.StaticBox( self, 'preparation' )
        
        # refresh button that just calls update
        
        self._num_phashes_to_regen = wx.StaticText( self._preparing_panel )
        self._num_branches_to_regen = wx.StaticText( self._preparing_panel )
        
        self._phashes_button = ClientGUICommon.BetterBitmapButton( self._preparing_panel, CC.GlobalBMPs.play, self._RegeneratePhashes )
        self._branches_button = ClientGUICommon.BetterBitmapButton( self._preparing_panel, CC.GlobalBMPs.play, self._RebalanceTree )
        
        #
        
        self._searching_panel = ClientGUICommon.StaticBox( self, 'discovery' )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'exact match', 'Search for exact matches.', HydrusData.Call( self._SetSearchDistance, HC.HAMMING_EXACT_MATCH ) ) )
        menu_items.append( ( 'normal', 'very similar', 'Search for very similar files.', HydrusData.Call( self._SetSearchDistance, HC.HAMMING_VERY_SIMILAR ) ) )
        menu_items.append( ( 'normal', 'similar', 'Search for similar files.', HydrusData.Call( self._SetSearchDistance, HC.HAMMING_SIMILAR ) ) )
        menu_items.append( ( 'normal', 'speculative', 'Search for files that are probably similar.', HydrusData.Call( self._SetSearchDistance, HC.HAMMING_SPECULATIVE ) ) )
        
        self._search_distance_button = ClientGUICommon.MenuButton( self._searching_panel, 'similarity', menu_items )
        
        self._search_distance_spinctrl = wx.SpinCtrl( self._searching_panel, min = 0, max = 64, size = ( 50, -1 ) )
        self._search_distance_spinctrl.Bind( wx.EVT_SPINCTRL, self.EventSearchDistanceChanged )
        
        self._num_searched = ClientGUICommon.TextAndGauge( self._searching_panel )
        
        self._search_button = ClientGUICommon.BetterBitmapButton( self._searching_panel, CC.GlobalBMPs.play, self._SearchForDuplicates )
        
        #
        
        self._filtering_panel = ClientGUICommon.StaticBox( self, 'filtering' )
        
        self._file_domain_button = ClientGUICommon.BetterButton( self._filtering_panel, 'file domain', self._FileDomainButtonHit )
        self._num_unknown_duplicates = wx.StaticText( self._filtering_panel )
        self._num_same_file_duplicates = wx.StaticText( self._filtering_panel )
        self._num_alternate_duplicates = wx.StaticText( self._filtering_panel )
        self._show_some_dupes = ClientGUICommon.BetterButton( self._filtering_panel, 'show some pairs (prototype!)', self._ShowSomeDupes )
        self._launch_filter = ClientGUICommon.BetterButton( self._filtering_panel, 'launch filter (prototype!)', self._LaunchFilter )
        
        #
        
        new_options = self._controller.GetNewOptions()
        
        self._search_distance_spinctrl.SetValue( new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' ) )
        
        duplicate_filter_file_domain = management_controller.GetKey( 'duplicate_filter_file_domain' )
        
        self._SetFileDomain( duplicate_filter_file_domain ) # this spawns a refreshandupdatestatus
        
        #
        
        gridbox_1 = wx.FlexGridSizer( 0, 3 )
        
        gridbox_1.AddGrowableCol( 0, 1 )
        
        gridbox_1.AddF( self._num_phashes_to_regen, CC.FLAGS_VCENTER )
        gridbox_1.AddF( ( 10, 10 ), CC.FLAGS_EXPAND_PERPENDICULAR )
        gridbox_1.AddF( self._phashes_button, CC.FLAGS_VCENTER )
        gridbox_1.AddF( self._num_branches_to_regen, CC.FLAGS_VCENTER )
        gridbox_1.AddF( ( 10, 10 ), CC.FLAGS_EXPAND_PERPENDICULAR )
        gridbox_1.AddF( self._branches_button, CC.FLAGS_VCENTER )
        
        self._preparing_panel.AddF( gridbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        distance_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        distance_hbox.AddF( wx.StaticText( self._searching_panel, label = 'search distance: ' ), CC.FLAGS_VCENTER )
        distance_hbox.AddF( self._search_distance_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        distance_hbox.AddF( self._search_distance_spinctrl, CC.FLAGS_VCENTER )
        
        gridbox_2 = wx.FlexGridSizer( 0, 2 )
        
        gridbox_2.AddGrowableCol( 0, 1 )
        
        gridbox_2.AddF( self._num_searched, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        gridbox_2.AddF( self._search_button, CC.FLAGS_VCENTER )
        
        self._searching_panel.AddF( distance_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._searching_panel.AddF( gridbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        self._filtering_panel.AddF( self._file_domain_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.AddF( self._num_unknown_duplicates, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.AddF( self._num_same_file_duplicates, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.AddF( self._num_alternate_duplicates, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.AddF( self._show_some_dupes, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.AddF( self._launch_filter, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._cog_button, CC.FLAGS_LONE_BUTTON )
        vbox.AddF( self._preparing_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._searching_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._filtering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventUpdateDBJob, id = ID_TIMER_UPDATE )
        self._update_db_job_timer = wx.Timer( self, id = ID_TIMER_UPDATE )
        
    
    def _FileDomainButtonHit( self ):
        
        services_manager = HydrusGlobals.client_controller.GetServicesManager()
        
        services = []
        
        services.append( services_manager.GetService( CC.LOCAL_FILE_SERVICE_KEY ) )
        services.append( services_manager.GetService( CC.TRASH_SERVICE_KEY ) )
        services.append( services_manager.GetService( CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
        
        menu = wx.Menu()
        
        for service in services:
            
            call = HydrusData.Call( self._SetFileDomain, service.GetServiceKey() )
            
            ClientGUIMenus.AppendMenuItem( self, menu, service.GetName(), 'Set the filtering file domain.', call )
            
        
        HydrusGlobals.client_controller.PopupMenu( self._file_domain_button, menu )
        
    
    def _LaunchFilter( self ):
        
        duplicate_filter_file_domain = self._management_controller.GetKey( 'duplicate_filter_file_domain' )
        
        canvas_frame = ClientGUICanvas.CanvasFrame( self.GetTopLevelParent() )
        
        canvas_window = ClientGUICanvas.CanvasFilterDuplicates( canvas_frame, duplicate_filter_file_domain )
        
        canvas_frame.SetCanvas( canvas_window )
        
    
    def _RebalanceTree( self ):
        
        self._job = 'branches'
        
        self._StartStopDBJob()
        
    
    def _RegeneratePhashes( self ):
        
        self._job = 'phashes'
        
        self._StartStopDBJob()
        
    
    def _ResetUnknown( self ):
        
        text = 'This will delete all the potential duplicate pairs and reset their files\' search status.'
        text += os.linesep * 2
        text += 'This can be useful if you have accidentally searched too broadly and are now swamped with too many false positives.'
        
        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.Write( 'delete_unknown_duplicate_pairs' )
                
                self._RefreshAndUpdateStatus()
            
        
    
    def _SearchForDuplicates( self ):
        
        self._job = 'search'
        
        self._StartStopDBJob()
        
    
    def _SetFileDomain( self, service_key ):
        
        self._management_controller.SetKey( 'duplicate_filter_file_domain', service_key )
        
        services_manager = HydrusGlobals.client_controller.GetServicesManager()
        
        service = services_manager.GetService( service_key )
        
        self._file_domain_button.SetLabelText( service.GetName() )
        
        self._RefreshAndUpdateStatus()
        
    
    def _SetSearchDistance( self, value ):
        
        self._search_distance_spinctrl.SetValue( value )
        
        self._UpdateStatus()
        
    
    def _ShowSomeDupes( self ):
        
        duplicate_filter_file_domain = self._management_controller.GetKey( 'duplicate_filter_file_domain' )
        
        hashes = self._controller.Read( 'some_dupes', duplicate_filter_file_domain )
        
        media_results = self._controller.Read( 'media_results', hashes )
        
        panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, CC.COMBINED_LOCAL_FILE_SERVICE_KEY, media_results )
        
        self._controller.pub( 'swap_media_panel', self._page_key, panel )
        
    
    def _StartStopDBJob( self ):
        
        if self._job_key is None:
            
            self._cog_button.Disable()
            self._phashes_button.Disable()
            self._branches_button.Disable()
            self._search_button.Disable()
            self._search_distance_button.Disable()
            self._search_distance_spinctrl.Disable()
            self._show_some_dupes.Disable()
            
            self._job_key = ClientThreading.JobKey( cancellable = True )
            
            if self._job == 'phashes':
                
                self._phashes_button.Enable()
                self._phashes_button.SetBitmap( CC.GlobalBMPs.stop )
                
                self._controller.Write( 'maintain_similar_files_phashes', job_key = self._job_key )
                
            elif self._job == 'branches':
                
                self._branches_button.Enable()
                self._branches_button.SetBitmap( CC.GlobalBMPs.stop )
                
                self._controller.Write( 'maintain_similar_files_tree', job_key = self._job_key )
                
            elif self._job == 'search':
                
                self._search_button.Enable()
                self._search_button.SetBitmap( CC.GlobalBMPs.stop )
                
                search_distance = self._search_distance_spinctrl.GetValue()
                
                self._controller.Write( 'maintain_similar_files_duplicate_pairs', search_distance, job_key = self._job_key )
                
            
            self._update_db_job_timer.Start( 250, wx.TIMER_CONTINUOUS )
            
        else:
            
            self._job_key.Cancel()
            
        
    
    def _RefreshAndUpdateStatus( self ):
        
        duplicate_filter_file_domain = self._management_controller.GetKey( 'duplicate_filter_file_domain' )
        
        self._similar_files_maintenance_status = self._controller.Read( 'similar_files_maintenance_status', duplicate_filter_file_domain )
        
        self._UpdateStatus()
        
    
    def _UpdateJob( self ):
        
        if self._job_key.TimeRunning() > 30:
            
            self._job_key.Cancel()
            
            self._job_key = None
            
            self._StartStopDBJob()
            
            return
            
        
        if self._job_key.IsDone():
            
            self._job_key = None
            
            self._update_db_job_timer.Stop()
            
            self._RefreshAndUpdateStatus()
            
            return
            
        
        if self._job == 'phashes':
            
            text = self._job_key.GetIfHasVariable( 'popup_text_1' )
            
            if text is not None:
                
                self._num_phashes_to_regen.SetLabelText( text )
                
            
        elif self._job == 'branches':
            
            text = self._job_key.GetIfHasVariable( 'popup_text_1' )
            
            if text is not None:
                
                self._num_branches_to_regen.SetLabelText( text )
                
            
        elif self._job == 'search':
            
            text = self._job_key.GetIfHasVariable( 'popup_text_1' )
            gauge = self._job_key.GetIfHasVariable( 'popup_gauge_1' )
            
            if text is not None and gauge is not None:
                
                ( value, range ) = gauge
                
                self._num_searched.SetValue( text, value, range )
                
            
        
    
    def _UpdateStatus( self ):
        
        ( num_phashes_to_regen, num_branches_to_regen, searched_distances_to_count, duplicate_types_to_count ) = self._similar_files_maintenance_status
        
        self._cog_button.Enable()
        
        self._phashes_button.SetBitmap( CC.GlobalBMPs.play )
        self._branches_button.SetBitmap( CC.GlobalBMPs.play )
        self._search_button.SetBitmap( CC.GlobalBMPs.play )
        
        total_num_files = sum( searched_distances_to_count.values() )
        
        if num_phashes_to_regen == 0:
            
            self._num_phashes_to_regen.SetLabelText( 'All ' + HydrusData.ConvertIntToPrettyString( total_num_files ) + ' eligible files up to date!' )
            
            self._phashes_button.Disable()
            
        else:
            
            num_done = total_num_files - num_phashes_to_regen
            
            self._num_phashes_to_regen.SetLabelText( HydrusData.ConvertValueRangeToPrettyString( num_done, total_num_files ) + ' eligible files up to date.' )
            
            self._phashes_button.Enable()
            
        
        if num_branches_to_regen == 0:
            
            self._num_branches_to_regen.SetLabelText( 'Search tree is fast!' )
            
            self._branches_button.Disable()
            
        else:
            
            self._num_branches_to_regen.SetLabelText( HydrusData.ConvertIntToPrettyString( num_branches_to_regen ) + ' search branches to rebalance.' )
            
            self._branches_button.Enable()
            
        
        self._search_distance_button.Enable()
        self._search_distance_spinctrl.Enable()
        
        search_distance = self._search_distance_spinctrl.GetValue()
        
        new_options = self._controller.GetNewOptions()
        
        new_options.SetInteger( 'similar_files_duplicate_pairs_search_distance', search_distance )
        
        if search_distance in HC.hamming_string_lookup:
            
            button_label = HC.hamming_string_lookup[ search_distance ]
            
        else:
            
            button_label = 'custom'
            
        
        self._search_distance_button.SetLabelText( button_label )
        
        num_searched = sum( ( count for ( value, count ) in searched_distances_to_count.items() if value is not None and value >= search_distance ) )
        
        if num_searched == total_num_files:
            
            self._num_searched.SetValue( 'All potential duplicates found at this distance.', total_num_files, total_num_files )
            
            self._search_button.Disable()
            
        else:
            
            if num_searched == 0:
                
                self._num_searched.SetValue( 'Have not yet searched at this distance.', 0, total_num_files )
                
            else:
                
                self._num_searched.SetValue( 'Searched ' + HydrusData.ConvertValueRangeToPrettyString( num_searched, total_num_files ) + ' files at this distance.', num_searched, total_num_files )
                
            
            self._search_button.Enable()
            
        
        num_unknown = duplicate_types_to_count[ HC.DUPLICATE_UNKNOWN ]
        
        self._num_unknown_duplicates.SetLabelText( HydrusData.ConvertIntToPrettyString( num_unknown ) + ' potential duplicates found.' )
        self._num_same_file_duplicates.SetLabelText( HydrusData.ConvertIntToPrettyString( duplicate_types_to_count[ HC.DUPLICATE_SAME_FILE ] ) + ' same file pairs filtered.' )
        self._num_alternate_duplicates.SetLabelText( HydrusData.ConvertIntToPrettyString( duplicate_types_to_count[ HC.DUPLICATE_ALTERNATE ] ) + ' alternate file pairs filtered.' )
        
        if num_unknown > 0:
            
            self._show_some_dupes.Enable()
            
        else:
            
            self._show_some_dupes.Disable()
            
        
    
    def EventSearchDistanceChanged( self, event ):
        
        self._UpdateStatus()
        
    
    def TIMEREventUpdateDBJob( self, event ):
        
        self._UpdateJob()
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_DUPLICATE_FILTER ] = ManagementPanelDuplicateFilter

class ManagementPanelGalleryImport( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._gallery_import = self._management_controller.GetVariable( 'gallery_import' )
        
        self._gallery_downloader_panel = ClientGUICommon.StaticBox( self, 'gallery downloader' )
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self._gallery_downloader_panel, 'imports' )
        
        self._overall_status = wx.StaticText( self._import_queue_panel )
        self._current_action = wx.StaticText( self._import_queue_panel )
        self._file_gauge = ClientGUICommon.Gauge( self._import_queue_panel )
        self._overall_gauge = ClientGUICommon.Gauge( self._import_queue_panel )
        
        self._waiting_politely_indicator = ClientGUICommon.GetWaitingPolitelyControl( self._import_queue_panel, self._page_key )
        
        self._seed_cache_button = ClientGUICommon.BetterBitmapButton( self._import_queue_panel, CC.GlobalBMPs.seed_cache, self._SeedCache )
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
        
        menu_items = []
        
        invert_call = self._gallery_import.InvertGetTagsIfURLKnownAndFileRedundant
        value_call = self._gallery_import.GetTagsIfURLKnownAndFileRedundant
        
        check_manager = ClientGUICommon.CheckboxManagerCalls( invert_call, value_call )
        
        menu_items.append( ( 'check', 'get tags even if url is known and file is already in db (this downloader)', 'If this is selected, the client will fetch the tags from a file\'s page even if it has the file and already previously downloaded it from that location.', check_manager ) )
        
        menu_items.append( ( 'separator', 0, 0, 0 ) )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'get_tags_if_url_known_and_file_redundant' )
        
        menu_items.append( ( 'check', 'get tags even if url is known and file is already in db (default)', 'Set the default for this value.', check_manager ) )
        
        self._cog_button = ClientGUICommon.MenuBitmapButton( self._gallery_downloader_panel, CC.GlobalBMPs.cog, menu_items )
        
        self._file_limit = ClientGUICommon.NoneableSpinCtrl( self._gallery_downloader_panel, 'stop after this many files', min = 1, none_phrase = 'no limit' )
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
        self._gallery_downloader_panel.AddF( self._cog_button, CC.FLAGS_LONE_BUTTON )
        self._gallery_downloader_panel.AddF( self._file_limit, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.AddF( self._import_file_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.AddF( self._import_tag_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        
        vbox.AddF( self._gallery_downloader_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self._controller.sub( self, 'UpdateStatus', 'update_status' )
        
        gallery_identifier = self._gallery_import.GetGalleryIdentifier()
        
        ( namespaces, search_value ) = ClientDefaults.GetDefaultNamespacesAndSearchValue( gallery_identifier )
        
        self._import_tag_options.SetNamespaces( namespaces )
        self._query_input.SetValue( search_value )
        
        def file_download_hook( gauge_range, gauge_value ):
            
            try:
                
                self._file_gauge.SetRange( gauge_range )
                self._file_gauge.SetValue( gauge_value )
                
            except wx.PyDeadObjectError:
                
                pass
                
            
        
        self._gallery_import.SetDownloadHook( file_download_hook )
        
        ( import_file_options, import_tag_options, file_limit ) = self._gallery_import.GetOptions()
        
        self._import_file_options.SetOptions( import_file_options )
        self._import_tag_options.SetOptions( import_tag_options )
        
        self._file_limit.SetValue( file_limit )
        
        self._Update()
        
        self._gallery_import.Start( self._page_key )
        
    
    def _SeedCache( self ):
        
        seed_cache = self._gallery_import.GetSeedCache()
        
        title = 'file import status'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIScrolledPanelsEdit.EditSeedCachePanel( frame, self._controller, seed_cache )
        
        frame.SetPanel( panel )
        
    
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
        
        self._seed_cache_button = ClientGUICommon.BetterBitmapButton( self._import_queue_panel, CC.GlobalBMPs.seed_cache, self._SeedCache )
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
        
    
    def _SeedCache( self ):
        
        seed_cache = self._hdd_import.GetSeedCache()
        
        title = 'file import status'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIScrolledPanelsEdit.EditSeedCachePanel( frame, self._controller, seed_cache )
        
        frame.SetPanel( panel )
        
    
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
        
        self._seed_cache_button = ClientGUICommon.BetterBitmapButton( self._import_queue_panel, CC.GlobalBMPs.seed_cache, self._SeedCache )
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
        
        vbox.AddF( self._page_of_images_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self._controller.sub( self, 'UpdateStatus', 'update_status' )
        
        self._page_of_images_import = self._management_controller.GetVariable( 'page_of_images_import' )
        
        def file_download_hook( gauge_range, gauge_value ):
            
            try:
                
                self._file_gauge.SetRange( gauge_range )
                self._file_gauge.SetValue( gauge_value )
                
            except wx.PyDeadObjectError:
                
                pass
                
            
        
        self._page_of_images_import.SetDownloadHook( file_download_hook )
        
        ( import_file_options, download_image_links, download_unlinked_images ) = self._page_of_images_import.GetOptions()
        
        self._import_file_options.SetOptions( import_file_options )
        
        self._download_image_links.SetValue( download_image_links )
        self._download_unlinked_images.SetValue( download_unlinked_images )
        
        self._Update()
        
        self._page_of_images_import.Start( self._page_key )
        
    
    def _SeedCache( self ):
        
        seed_cache = self._page_of_images_import.GetSeedCache()
        
        title = 'file import status'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIScrolledPanelsEdit.EditSeedCachePanel( frame, self._controller, seed_cache )
        
        frame.SetPanel( panel )
        
    
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
        self._can_ban = self._service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE )
        
        service_type = self._service.GetServiceType()
        
        self._num_petition_info = None
        self._current_petition = None
        
        #
        
        self._petitions_info_panel = ClientGUICommon.StaticBox( self, 'petitions info' )
        
        self._refresh_num_petitions_button = ClientGUICommon.BetterButton( self._petitions_info_panel, 'refresh counts', self._FetchNumPetitions )
        
        self._petition_types_to_controls = {}
        
        content_type_hboxes = []
        
        petition_types = []
        
        if service_type == HC.FILE_REPOSITORY:
            
            petition_types.append( ( HC.CONTENT_TYPE_FILES, HC.CONTENT_STATUS_PETITIONED ) )
            
        elif service_type == HC.TAG_REPOSITORY:
            
            petition_types.append( ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_STATUS_PETITIONED ) )
            petition_types.append( ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PENDING ) )
            petition_types.append( ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PETITIONED ) )
            petition_types.append( ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PENDING ) )
            petition_types.append( ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PETITIONED ) )
            
        
        for ( content_type, status ) in petition_types:
            
            func = HydrusData.Call( self._FetchPetition, content_type, status )
            
            st = wx.StaticText( self._petitions_info_panel )
            button = ClientGUICommon.BetterButton( self._petitions_info_panel, 'fetch ' + HC.content_status_string_lookup[ status ] + ' ' + HC.content_type_string_lookup[ content_type ] + ' petition', func )
            
            button.Disable()
            
            self._petition_types_to_controls[ ( content_type, status ) ] = ( st, button )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( st, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
            hbox.AddF( button, CC.FLAGS_VCENTER )
            
            content_type_hboxes.append( hbox )
            
        
        #
        
        self._petition_panel = ClientGUICommon.StaticBox( self, 'petition' )
        
        self._action_text = wx.StaticText( self._petition_panel, label = '' )
        
        self._reason_text = ClientGUICommon.SaneMultilineTextCtrl( self._petition_panel, style = wx.TE_READONLY )
        self._reason_text.SetMinSize( ( -1, 80 ) )
        
        check_all = ClientGUICommon.BetterButton( self._petition_panel, 'check all', self._CheckAll )
        check_none = ClientGUICommon.BetterButton( self._petition_panel, 'check none', self._CheckNone )
        
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
        
        self._petitions_info_panel.AddF( self._refresh_num_petitions_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        for hbox in content_type_hboxes:
            
            self._petitions_info_panel.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        check_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        check_hbox.AddF( check_all, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        check_hbox.AddF( check_none, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        
        self._petition_panel.AddF( wx.StaticText( self._petition_panel, label = 'Double-click a petition to see its files, if it has them.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.AddF( self._action_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.AddF( self._reason_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.AddF( check_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._petition_panel.AddF( self._contents, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._petition_panel.AddF( self._process, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.AddF( self._modify_petitioner, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._MakeSort( vbox )
        self._MakeCollect( vbox )
        
        vbox.AddF( self._petitions_info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._petition_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        wx.CallAfter( self._FetchNumPetitions )
        
        self._controller.sub( self, 'RefreshQuery', 'refresh_query' )
        
    
    def _BreakApprovedContentsIntoChunks( self, approved_contents ):
        
        chunks_of_approved_contents = []
        chunk_of_approved_contents = []
        weight = 0
        
        for content in approved_contents:
            
            chunk_of_approved_contents.append( content )
            
            weight += content.GetVirtualWeight()
            
            if weight > 200:
                
                chunks_of_approved_contents.append( chunk_of_approved_contents )
                
                weight = 0
                
            
        
        if len( chunk_of_approved_contents ) > 0:
            
            chunks_of_approved_contents.append( chunk_of_approved_contents )
            
        
        return chunks_of_approved_contents
        

    def _CheckAll( self ):
        
        for i in range( self._contents.GetCount() ):
            
            self._contents.Check( i )
            
        
    
    def _CheckNone( self ):
        
        for i in range( self._contents.GetCount() ):
            
            self._contents.Check( i, False )
            
        
    
    def _DrawCurrentPetition( self ):
        
        if self._current_petition is None:
            
            self._action_text.SetLabelText( '' )
            self._reason_text.SetValue( '' )
            self._reason_text.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )
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
            
            self._reason_text.SetBackgroundColour( action_colour )
            
            contents = self._current_petition.GetContents()
            
            self._contents.Clear()
            
            for content in contents:
                
                self._contents.Append( content.ToString(), content )
                
            
            self._contents.SetChecked( range( self._contents.GetCount() ) )
            
            self._process.Enable()
            
            if self._can_ban:
                
                self._modify_petitioner.Enable()
                
            
        
        self._ShowHashes( [] )
        
    
    def _DrawNumPetitions( self ):
        
        new_petition_fetched = False
        
        for ( content_type, status, count ) in self._num_petition_info:
            
            petition_type = ( content_type, status )
            
            if petition_type in self._petition_types_to_controls:
                
                ( st, button ) = self._petition_types_to_controls[ petition_type ]
                
                st.SetLabelText( HydrusData.ConvertIntToPrettyString( count ) + ' petitions' )
                
                if count > 0:
                    
                    button.Enable()
                    
                    if self._current_petition is None and not new_petition_fetched:
                        
                        self._FetchPetition( content_type, status )
                        
                        new_petition_fetched = True
                        
                    
                else:
                    
                    button.Disable()
                    
                
            
        
    
    def _FetchNumPetitions( self ):
        
        def do_it():
            
            try:
                
                response = self._service.Request( HC.GET, 'num_petitions' )
                
                self._num_petition_info = response[ 'num_petitions' ]
                
                wx.CallAfter( self._DrawNumPetitions )
                
            finally:
                
                self._refresh_num_petitions_button.SetLabelText( 'refresh counts' )
                
            
        
        self._refresh_num_petitions_button.SetLabelText( u'Fetching\u2026' )
        
        self._controller.CallToThread( do_it )
        
    
    def _FetchPetition( self, content_type, status ):
        
        ( st, button ) = self._petition_types_to_controls[ ( content_type, status ) ]
        
        def do_it():
            
            try:
                
                response = self._service.Request( HC.GET, 'petition', { 'content_type' : content_type, 'status' : status } )
                
                self._current_petition = response[ 'petition' ]
                
                wx.CallAfter( self._DrawCurrentPetition )
                
            finally:
                
                wx.CallAfter( button.Enable )
                wx.CallAfter( button.SetLabelText, 'fetch ' + HC.content_status_string_lookup[ status ] + ' ' + HC.content_type_string_lookup[ content_type ] + ' petition' )
                
            
        
        if self._current_petition is not None:
            
            self._current_petition = None
            
            self._DrawCurrentPetition()
            
        
        button.Disable()
        button.SetLabelText( u'Fetching\u2026' )
        
        self._controller.CallToThread( do_it )
        
    
    def _ShowHashes( self, hashes ):
        
        file_service_key = self._management_controller.GetKey( 'file_service' )
        
        with wx.BusyCursor(): media_results = self._controller.Read( 'media_results', hashes )
        
        panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, file_service_key, media_results )
        
        panel.Collect( self._page_key, self._collect_by.GetChoice() )
        
        panel.Sort( self._page_key, self._sort_by.GetChoice() )
        
        self._controller.pub( 'swap_media_panel', self._page_key, panel )
        
    
    def EventContentDoubleClick( self, event ):
        
        selection = self._contents.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            content = self._contents.GetClientData( selection )
            
            if content.HasHashes():
                
                self._ShowHashes( content.GetHashes() )
                
            
        
    
    def EventProcess( self, event ):
        
        def do_it( approved_contents, denied_contents, petition ):
            
            try:
                
                num_done = 0
                num_to_do = len( approved_contents )
                
                if len( denied_contents ) > 0:
                    
                    num_to_do += 1
                    
                
                if num_to_do > 1:
                    
                    job_key = ClientThreading.JobKey( cancellable = True )
                    
                    job_key.SetVariable( 'popup_title', 'comitting petitions' )
                    
                    HydrusGlobals.client_controller.pub( 'message', job_key )
                    
                else:
                    
                    job_key = None
                    
                
                chunks_of_approved_contents = self._BreakApprovedContentsIntoChunks( approved_contents )
                
                for chunk_of_approved_contents in chunks_of_approved_contents:
                    
                    if job_key is not None:
                        
                        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                        
                        if should_quit:
                            
                            return
                            
                        
                        job_key.SetVariable( 'popup_gauge_1', ( num_done, num_to_do ) )
                        
                    
                    ( update, content_updates ) = petition.GetApproval( chunk_of_approved_contents )
                    
                    self._service.Request( HC.POST, 'update', { 'client_to_server_update' : update } )
                    
                    self._controller.Write( 'content_updates', { self._petition_service_key : content_updates } )
                    
                    num_done += len( chunk_of_approved_contents )
                    
                
                if len( denied_contents ) > 0:
                    
                    if job_key is not None:
                        
                        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                        
                        if should_quit:
                            
                            return
                            
                        
                    
                    update = petition.GetDenial( denied_contents )
                    
                    self._service.Request( HC.POST, 'update', { 'client_to_server_update' : update } )
                    
                
            finally:
                
                if job_key is not None:
                    
                    job_key.Delete()
                    
                
                wx.CallAfter( self._FetchNumPetitions )
                
            
        
        approved_contents = []
        denied_contents = []
        
        for index in range( self._contents.GetCount() ):
            
            content = self._contents.GetClientData( index )
            
            if self._contents.IsChecked( index ):
                
                approved_contents.append( content )
                
            else:
                
                denied_contents.append( content )
                
            
        
        HydrusGlobals.client_controller.CallToThread( do_it, approved_contents, denied_contents, self._current_petition )
        
        self._current_petition = None
        
        self._DrawCurrentPetition()
        
    
    def EventModifyPetitioner( self, event ):
        
        wx.MessageBox( 'modify users does not work yet!' )
        
        with ClientGUIDialogs.DialogModifyAccounts( self, self._petition_service_key, ( self._current_petition.GetPetitionerAccount(), ) ) as dlg:
            
            dlg.ShowModal()
            
        
    
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
            
            self._current_predicates_box = ClientGUIListBoxes.ListBoxTagsActiveSearchPredicates( self._search_panel, self._page_key, initial_predicates )
            
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
            
            t = ClientGUIListBoxes.ListBoxTagsSelectionManagementPanel( tags_box, self._page_key, predicates_callable = self._current_predicates_box.GetPredicates )
            
            file_search_context = self._management_controller.GetVariable( 'file_search_context' )
            
            tag_service_key = file_search_context.GetTagServiceKey()
            
            t.ChangeTagService( tag_service_key )
            
        else:
            
            t = ClientGUIListBoxes.ListBoxTagsSelectionManagementPanel( tags_box, self._page_key )
            
        
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
        
        self._thread_times_to_check = wx.SpinCtrl( self._options_panel, size = ( 80, -1 ), min = 0, max = 65536 )
        self._thread_times_to_check.SetValue( times_to_check )
        self._thread_times_to_check.Bind( wx.EVT_SPINCTRL, self.EventTimesToCheck )
        
        self._thread_check_period = ClientGUICommon.TimeDeltaButton( self._options_panel, min = 30, hours = True, minutes = True, seconds = True )
        self._thread_check_period.SetValue( check_period )
        self._thread_check_period.Bind( ClientGUICommon.EVT_TIME_DELTA, self.EventCheckPeriod )
        
        self._thread_check_now_button = wx.Button( self._options_panel, label = 'check now' )
        self._thread_check_now_button.Bind( wx.EVT_BUTTON, self.EventCheckNow )
        
        self._waiting_politely_indicator = ClientGUICommon.GetWaitingPolitelyControl( self._options_panel, self._page_key )
        
        self._seed_cache_button = ClientGUICommon.BetterBitmapButton( self._options_panel, CC.GlobalBMPs.seed_cache, self._SeedCache )
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
            
            try:
                
                self._file_gauge.SetRange( gauge_range )
                self._file_gauge.SetValue( gauge_value )
                
            except wx.PyDeadObjectError:
                
                pass
                
            
        
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
        
    
    def _SeedCache( self ):
        
        seed_cache = self._thread_watcher_import.GetSeedCache()
        
        title = 'file import status'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIScrolledPanelsEdit.EditSeedCachePanel( frame, self._controller, seed_cache )
        
        frame.SetPanel( panel )
        
    
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
            
        else:
            
            event.Skip()
            
        
    
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
        
        self._seed_cache_button = ClientGUICommon.BetterBitmapButton( self._url_panel, CC.GlobalBMPs.seed_cache, self._SeedCache )
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
        
        vbox.AddF( self._url_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self._controller.sub( self, 'UpdateStatus', 'update_status' )
        
        self._urls_import = self._management_controller.GetVariable( 'urls_import' )
        
        def file_download_hook( gauge_range, gauge_value ):
            
            try:
                
                self._file_gauge.SetRange( gauge_range )
                self._file_gauge.SetValue( gauge_value )
                
            except wx.PyDeadObjectError:
                
                pass
                
            
        
        self._urls_import.SetDownloadHook( file_download_hook )
        
        import_file_options = self._urls_import.GetOptions()
        
        self._import_file_options.SetOptions( import_file_options )
        
        self._Update()
        
        self._urls_import.Start( self._page_key )
        
    
    def _SeedCache( self ):
        
        seed_cache = self._urls_import.GetSeedCache()
        
        title = 'file import status'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIScrolledPanelsEdit.EditSeedCachePanel( frame, self._controller, seed_cache )
        
        frame.SetPanel( panel )
        
    
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
        
    
    def SetSearchFocus( self, page_key ):
        
        if page_key == self._page_key: self._url_input.SetFocus()
        
    
    def UpdateStatus( self, page_key ):
        
        if page_key == self._page_key:
            
            self._Update()
            
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_URLS ] = ManagementPanelURLsImport
