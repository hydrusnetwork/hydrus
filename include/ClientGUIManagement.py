from . import HydrusConstants as HC
from . import HydrusExceptions
from . import HydrusSerialisable
from . import ClientConstants as CC
from . import ClientDefaults
from . import ClientGUIACDropdown
from . import ClientGUICanvas
from . import ClientGUICommon
from . import ClientGUIControls
from . import ClientGUIDialogs
from . import ClientGUIFunctions
from . import ClientGUIImport
from . import ClientGUIListBoxes
from . import ClientGUIListCtrl
from . import ClientGUIMedia
from . import ClientGUIMenus
from . import ClientGUIParsing
from . import ClientGUIScrolledPanels
from . import ClientGUIFileSeedCache
from . import ClientGUIGallerySeedLog
from . import ClientGUIScrolledPanelsEdit
from . import ClientGUITopLevelWindows
from . import ClientImportGallery
from . import ClientImportLocal
from . import ClientImportOptions
from . import ClientImportSimpleURLs
from . import ClientImportWatchers
from . import ClientMedia
from . import ClientParsing
from . import ClientPaths
from . import ClientSearch
from . import ClientTags
from . import ClientThreading
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusThreading
import os
import time
import traceback
import wx
import wx.lib.scrolledpanel

CAPTCHA_FETCH_EVENT_TYPE = wx.NewEventType()
CAPTCHA_FETCH_EVENT = wx.PyEventBinder( CAPTCHA_FETCH_EVENT_TYPE )

ID_TIMER_CAPTCHA = wx.NewId()
ID_TIMER_DUMP = wx.NewId()

MANAGEMENT_TYPE_DUMPER = 0
MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY = 1
MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER = 2
MANAGEMENT_TYPE_IMPORT_HDD = 3
MANAGEMENT_TYPE_IMPORT_WATCHER = 4 # defunct
MANAGEMENT_TYPE_PETITIONS = 5
MANAGEMENT_TYPE_QUERY = 6
MANAGEMENT_TYPE_IMPORT_URLS = 7
MANAGEMENT_TYPE_DUPLICATE_FILTER = 8
MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER = 9
MANAGEMENT_TYPE_PAGE_OF_PAGES = 10

management_panel_types_to_classes = {}

def CreateManagementController( page_name, management_type, file_service_key = None ):
    
    if file_service_key is None:
        
        file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
        
    
    new_options = HG.client_controller.new_options
    
    management_controller = ManagementController( page_name )
    
    management_controller.SetType( management_type )
    management_controller.SetKey( 'file_service', file_service_key )
    management_controller.SetVariable( 'media_sort', new_options.GetDefaultSort() )
    
    collect_by = HC.options[ 'default_collect' ]
    
    if collect_by is None:
        
        collect_by = []
        
    
    management_controller.SetVariable( 'media_collect', collect_by )
    
    return management_controller
    
def CreateManagementControllerDuplicateFilter():
    
    management_controller = CreateManagementController( 'duplicates', MANAGEMENT_TYPE_DUPLICATE_FILTER )
    
    file_search_context = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_EVERYTHING ) ] )
    
    management_controller.SetVariable( 'file_search_context', file_search_context )
    management_controller.SetVariable( 'both_files_match', False )
    
    return management_controller
    
def CreateManagementControllerImportGallery():
    
    page_name = 'gallery'
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY )
    
    gug_key_and_name = HG.client_controller.network_engine.domain_manager.GetDefaultGUGKeyAndName()
    
    multiple_gallery_import = ClientImportGallery.MultipleGalleryImport( gug_key_and_name = gug_key_and_name )
    
    management_controller.SetVariable( 'multiple_gallery_import', multiple_gallery_import )
    
    return management_controller
    
def CreateManagementControllerImportSimpleDownloader():
    
    management_controller = CreateManagementController( 'simple downloader', MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER )
    
    simple_downloader_import = ClientImportSimpleURLs.SimpleDownloaderImport()
    
    formula_name = HG.client_controller.new_options.GetString( 'favourite_simple_downloader_formula' )
    
    simple_downloader_import.SetFormulaName( formula_name )
    
    management_controller.SetVariable( 'simple_downloader_import', simple_downloader_import )
    
    return management_controller
    
def CreateManagementControllerImportHDD( paths, file_import_options, paths_to_service_keys_to_tags, delete_after_success ):
    
    management_controller = CreateManagementController( 'import', MANAGEMENT_TYPE_IMPORT_HDD )
    
    hdd_import = ClientImportLocal.HDDImport( paths = paths, file_import_options = file_import_options, paths_to_service_keys_to_tags = paths_to_service_keys_to_tags, delete_after_success = delete_after_success )
    
    management_controller.SetVariable( 'hdd_import', hdd_import )
    
    return management_controller
    
def CreateManagementControllerImportMultipleWatcher( page_name = None, url = None ):
    
    if page_name is None:
        
        page_name = 'watcher'
        
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER )
    
    multiple_watcher_import = ClientImportWatchers.MultipleWatcherImport( url = url )
    
    management_controller.SetVariable( 'multiple_watcher_import', multiple_watcher_import )
    
    return management_controller
    
def CreateManagementControllerImportURLs( page_name = None ):
    
    if page_name is None:
        
        page_name = 'url import'
        
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_IMPORT_URLS )
    
    urls_import = ClientImportSimpleURLs.URLsImport()
    
    management_controller.SetVariable( 'urls_import', urls_import )
    
    return management_controller
    
def CreateManagementControllerPetitions( petition_service_key ):
    
    petition_service = HG.client_controller.services_manager.GetService( petition_service_key )
    
    page_name = petition_service.GetName() + ' petitions'
    
    petition_service_type = petition_service.GetServiceType()
    
    if petition_service_type in HC.LOCAL_FILE_SERVICES or petition_service_type == HC.FILE_REPOSITORY:
        
        file_service_key = petition_service_key
        
    else:
        
        file_service_key = CC.COMBINED_FILE_SERVICE_KEY
        
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_PETITIONS, file_service_key = file_service_key )
    
    management_controller.SetKey( 'petition_service', petition_service_key )
    
    return management_controller
    
def CreateManagementControllerQuery( page_name, file_service_key, file_search_context, search_enabled ):
    
    management_controller = CreateManagementController( page_name, MANAGEMENT_TYPE_QUERY, file_service_key = file_service_key )
    
    management_controller.SetVariable( 'file_search_context', file_search_context )
    management_controller.SetVariable( 'search_enabled', search_enabled )
    management_controller.SetVariable( 'synchronised', True )
    
    return management_controller
    
def CreateManagementPanel( parent, page, controller, management_controller ):
    
    management_type = management_controller.GetType()
    
    management_class = management_panel_types_to_classes[ management_type ]
    
    management_panel = management_class( parent, page, controller, management_controller )
    
    return management_panel
    
'''class CaptchaControl( wx.Panel ):
    
    def __init__( self, parent, captcha_type, default ):
        
        wx.Panel.__init__( self, parent )
        
        self._captcha_key = default
        
        self._captcha_challenge = None
        self._captcha_runs_out = 0
        self._bitmap = HG.client_controller.bitmap_manager.GetBitmap( 20, 20, 24 )
        
        self._timer = wx.Timer( self, ID_TIMER_CAPTCHA )
        self.Bind( wx.EVT_TIMER, self.TIMEREvent, id = ID_TIMER_CAPTCHA )
        
        self._captcha_box_panel = ClientGUICommon.StaticBox( self, 'recaptcha' )
        
        self._captcha_panel = ClientGUICommon.BufferedWindow( self._captcha_box_panel, size = ( 300, 57 ) )
        
        self._refresh_button = wx.Button( self._captcha_box_panel, label = '' )
        self._refresh_button.Bind( wx.EVT_BUTTON, self.EventRefreshCaptcha )
        self._refresh_button.Disable()
        
        self._captcha_time_left = ClientGUICommon.BetterStaticText( self._captcha_box_panel )
        
        self._captcha_entry = wx.TextCtrl( self._captcha_box_panel, style = wx.TE_PROCESS_ENTER )
        self._captcha_entry.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._ready_button = wx.Button( self._captcha_box_panel, label = '' )
        self._ready_button.Bind( wx.EVT_BUTTON, self.EventReady )
        
        sub_vbox = wx.BoxSizer( wx.VERTICAL )
        
        sub_vbox.Add( self._refresh_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        sub_vbox.Add( self._captcha_time_left, CC.FLAGS_SMALL_INDENT )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._captcha_panel, CC.FLAGS_NONE )
        hbox.Add( sub_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        hbox2 = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox2.Add( self._captcha_entry, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox2.Add( self._ready_button, CC.FLAGS_VCENTER )
        
        self._captcha_box_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._captcha_box_panel.Add( hbox2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._captcha_box_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
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
            
            wx.QueueEvent( self.GetEventHandler(), event )
            
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
            
            HG.client_controller.bitmap_manager.ReleaseBitmap( wx_bmp )
            
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
        self._bitmap = HG.client_controller.bitmap_manager.GetBitmap( 20, 20, 24 )
        
        self._DrawMain()
        self._DrawEntry()
        self._DrawReady()
        
        self._timer.Stop()
        
    
    def Enable( self ):
        
        self._captcha_challenge = ''
        self._captcha_runs_out = 0
        self._bitmap = HG.client_controller.bitmap_manager.GetBitmap( 20, 20, 24 )
        
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
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ): self.EventReady( None )
        else: event.Skip()
        
    
    def EventReady( self, event ): self._DrawReady( not self._ready_button.GetLabelText() == 'edit' )
    
    def EventRefreshCaptcha( self, event ):
        
        javascript_string = self._controller.DoHTTP( HC.GET, 'https://www.google.com/recaptcha/api/challenge?k=' + self._captcha_key )
        
        ( trash, rest ) = javascript_string.split( 'challenge : \'', 1 )
        
        ( self._captcha_challenge, trash ) = rest.split( '\'', 1 )
        
        jpeg = self._controller.DoHTTP( HC.GET, 'https://www.google.com/recaptcha/api/image?c=' + self._captcha_challenge )
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            with open( temp_path, 'wb' ) as f: f.write( jpeg )
            
            self._bitmap = ClientRendering.GenerateHydrusBitmap( temp_path, HC.IMAGE_JPEG )
            
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
        
        self._comment_panel.Add( self._comment, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._comment_panel.Add( self._comment_append, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._comment_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
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
    SERIALISABLE_NAME = 'Client Page Management Controller'
    SERIALISABLE_VERSION = 9
    
    def __init__( self, page_name = 'page' ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._page_name = page_name
        
        self._management_type = None
        
        self._keys = {}
        self._simples = {}
        self._serialisables = {}
        
    
    def __repr__( self ):
        
        return 'Management Controller: {} - {}'.format( self._management_type, self._page_name )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_keys = { name : value.hex() for ( name, value ) in list(self._keys.items()) }
        
        serialisable_simples = dict( self._simples )
        
        serialisable_serialisables = { name : value.GetSerialisableTuple() for ( name, value ) in list(self._serialisables.items()) }
        
        return ( self._page_name, self._management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
        
    
    def _InitialiseDefaults( self ):
        
        self._serialisables[ 'media_sort' ] = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._page_name, self._management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = serialisable_info
        
        self._InitialiseDefaults()
        
        self._keys.update( { name : bytes.fromhex( key ) for ( name, key ) in list(serialisable_keys.items()) } )
        
        if 'file_service' in self._keys:
            
            if not HG.client_controller.services_manager.ServiceExists( self._keys[ 'file_service' ] ):
                
                self._keys[ 'file_service' ] = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
                
            
        
        self._simples.update( dict( serialisable_simples ) )
        
        self._serialisables.update( { name : HydrusSerialisable.CreateFromSerialisableTuple( value ) for ( name, value ) in list(serialisable_serialisables.items()) } )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if management_type == MANAGEMENT_TYPE_IMPORT_HDD:
                
                advanced_import_options = serialisable_simples[ 'advanced_import_options' ]
                paths_info = serialisable_simples[ 'paths_info' ]
                paths_to_tags = serialisable_simples[ 'paths_to_tags' ]
                delete_after_success = serialisable_simples[ 'delete_after_success' ]
                
                paths = [ path_info for ( path_type, path_info ) in paths_info if path_type != 'zip' ]
                
                exclude_deleted = advanced_import_options[ 'exclude_deleted' ]
                do_not_check_known_urls_before_importing = False
                do_not_check_hashes_before_importing = False   
                allow_decompression_bombs = False
                min_size = advanced_import_options[ 'min_size' ]
                max_size = None
                max_gif_size = None
                min_resolution = advanced_import_options[ 'min_resolution' ]
                max_resolution = None
                
                automatic_archive = advanced_import_options[ 'automatic_archive' ]
                associate_source_urls = True
                
                file_import_options = ClientImportOptions.FileImportOptions()
                
                file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
                file_import_options.SetPostImportOptions( automatic_archive, associate_source_urls )
                
                paths_to_tags = { path : { bytes.fromhex( service_key ) : tags for ( service_key, tags ) in service_keys_to_tags } for ( path, service_keys_to_tags ) in list(paths_to_tags.items()) }
                
                hdd_import = ClientImportLocal.HDDImport( paths = paths, file_import_options = file_import_options, paths_to_service_keys_to_tags = paths_to_tags, delete_after_success = delete_after_success )
                
                serialisable_serialisables[ 'hdd_import' ] = hdd_import.GetSerialisableTuple()
                
                del serialisable_serialisables[ 'advanced_import_options' ]
                del serialisable_serialisables[ 'paths_info' ]
                del serialisable_serialisables[ 'paths_to_tags' ]
                del serialisable_serialisables[ 'delete_after_success' ]
                
            
            new_serialisable_info = ( management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            page_name = 'page'
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'page_of_images_import' in serialisable_serialisables:
                
                serialisable_serialisables[ 'simple_downloader_import' ] = serialisable_serialisables[ 'page_of_images_import' ]
                
                del serialisable_serialisables[ 'page_of_images_import' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'thread_watcher_import' in serialisable_serialisables:
                
                serialisable_serialisables[ 'watcher_import' ] = serialisable_serialisables[ 'thread_watcher_import' ]
                
                del serialisable_serialisables[ 'thread_watcher_import' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'gallery_import' in serialisable_serialisables:
                
                serialisable_serialisables[ 'multiple_gallery_import' ] = serialisable_serialisables[ 'gallery_import' ]
                
                del serialisable_serialisables[ 'gallery_import' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if 'watcher_import' in serialisable_serialisables:
                
                watcher = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_serialisables[ 'watcher_import' ] )
                
                management_type = MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER
                
                multiple_watcher_import = ClientImportWatchers.MultipleWatcherImport()
                
                multiple_watcher_import.AddWatcher( watcher )
                
                serialisable_multiple_watcher_import = multiple_watcher_import.GetSerialisableTuple()
                
                serialisable_serialisables[ 'multiple_watcher_import' ] = serialisable_multiple_watcher_import
                
                del serialisable_serialisables[ 'watcher_import' ]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if page_name.startswith( '[USER]' ) and len( page_name ) > 6:
                
                page_name = page_name[6:]
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 8, new_serialisable_info )
            
        
        if version == 8:
            
            ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables ) = old_serialisable_info
            
            if management_type == MANAGEMENT_TYPE_DUPLICATE_FILTER:
                
                if 'duplicate_filter_file_domain' in serialisable_keys:
                    
                    del serialisable_keys[ 'duplicate_filter_file_domain' ]
                    
                
                file_search_context = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_EVERYTHING ) ] )
                
                serialisable_serialisables[ 'file_search_context' ] = file_search_context.GetSerialisableTuple()
                
                serialisable_simples[ 'both_files_match' ] = False
                
            
            new_serialisable_info = ( page_name, management_type, serialisable_keys, serialisable_simples, serialisable_serialisables )
            
            return ( 9, new_serialisable_info )
            
        
    
    def GetKey( self, name ):
        
        return self._keys[ name ]
        
    
    def GetPageName( self ):
        
        return self._page_name
        
    
    def GetType( self ):
        
        return self._management_type
        
    
    def GetValueRange( self ):
        
        try:
            
            if self._management_type == MANAGEMENT_TYPE_IMPORT_HDD:
                
                hdd_import = self._serialisables[ 'hdd_import' ]
                
                return hdd_import.GetValueRange()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER:
                
                simple_downloader_import = self._serialisables[ 'simple_downloader_import' ]
                
                return simple_downloader_import.GetValueRange()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY:
                
                multiple_gallery_import = self._serialisables[ 'multiple_gallery_import' ]
                
                return multiple_gallery_import.GetValueRange()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER:
                
                multiple_watcher_import = self._serialisables[ 'multiple_watcher_import' ]
                
                return multiple_watcher_import.GetValueRange()
                
            elif self._management_type == MANAGEMENT_TYPE_IMPORT_URLS:
                
                urls_import = self._serialisables[ 'urls_import' ]
                
                return urls_import.GetValueRange()
                
            
        except KeyError:
            
            return ( 0 , 0 )
            
        
        return ( 0, 0 )
        
    
    def GetVariable( self, name ):
        
        if name in self._simples:
            
            return self._simples[ name ]
            
        else:
            
            return self._serialisables[ name ]
            
        
    
    def HasVariable( self, name ):
        
        return name in self._simples or name in self._serialisables
        
    
    def IsImporter( self ):
        
        return self._management_type in ( MANAGEMENT_TYPE_IMPORT_HDD, MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER, MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY, MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER, MANAGEMENT_TYPE_IMPORT_URLS )
        
    
    def SetKey( self, name, key ):
        
        self._keys[ name ] = key
        
    
    def SetPageName( self, name ):
        
        self._page_name = name
        
    
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
        
        self.SetupScrolling( scrollIntoView = False )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._controller = controller
        self._management_controller = management_controller
        
        self._page = page
        self._page_key = self._management_controller.GetKey( 'page' )
        
        self._sort_by = ClientGUICommon.ChoiceSort( self, management_controller = self._management_controller )
        
        self._collect_by = ClientGUICommon.CheckboxCollect( self, management_controller = self._management_controller )
        
    
    def GetCollectBy( self ):
        
        if self._collect_by.IsShown():
            
            return self._collect_by.GetChoice()
            
        else:
            
            return []
            
        
    
    def GetSortBy( self ):
        
        return self._sort_by.GetSort()
        
    
    def _MakeCurrentSelectionTagsBox( self, sizer ):
        
        tags_box = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'selection tags' )
        
        t = ClientGUIListBoxes.ListBoxTagsSelectionManagementPanel( tags_box, self._page_key )
        
        tags_box.SetTagsBox( t )
        
        sizer.Add( tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def CheckAbleToClose( self ):
        
        pass
        
    
    def CleanBeforeClose( self ):
        
        pass
        
    
    def CleanBeforeDestroy( self ):
        
        pass
        
    
    def PageHidden( self ):
        
        pass
        
    
    def PageShown( self ):
        
        if self._controller.new_options.GetBoolean( 'set_search_focus_on_page_change' ):
            
            self.SetSearchFocus()
            
        
    
    def SetSearchFocus( self ):
        
        pass
        
    
    def Start( self ):
        
        pass
        
    
    def REPEATINGPageUpdate( self ):
        
        pass
        
    
def WaitOnDupeFilterJob( job_key ):
    
    while not job_key.IsDone():
        
        if HydrusThreading.IsThreadShuttingDown():
            
            return
            
        
        time.sleep( 0.25 )
        
    
    time.sleep( 0.5 )
    
    HG.client_controller.pub( 'refresh_dupe_page_numbers' )
    
class ManagementPanelDuplicateFilter( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._job = None
        self._job_key = None
        self._in_break = False
        
        self._similar_files_maintenance_status = None
        
        new_options = self._controller.new_options
        
        self._currently_refreshing_maintenance_numbers = False
        self._currently_refreshing_dupe_count_numbers = False
        
        #
        
        self._main_notebook = ClientGUICommon.BetterNotebook( self )
        
        self._main_left_panel = wx.Panel( self._main_notebook )
        self._main_right_panel = wx.Panel( self._main_notebook )
        
        #
        
        self._refresh_maintenance_status = ClientGUICommon.BetterStaticText( self._main_left_panel )
        self._refresh_maintenance_button = ClientGUICommon.BetterBitmapButton( self._main_left_panel, CC.GlobalBMPs.refresh, self._RefreshMaintenanceStatus )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'reset potential duplicates', 'This will delete all the potential duplicate pairs found so far and reset their files\' search status.', self._ResetUnknown ) )
        menu_items.append( ( 'separator', 0, 0, 0 ) )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'maintain_similar_files_duplicate_pairs_during_idle' )
        
        menu_items.append( ( 'check', 'search for duplicate pairs at the current distance during normal db maintenance', 'Tell the client to find duplicate pairs in its normal db maintenance cycles, whether you have that set to idle or shutdown time.', check_manager ) )
        
        self._cog_button = ClientGUICommon.MenuBitmapButton( self._main_left_panel, CC.GlobalBMPs.cog, menu_items )
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'duplicates.html' ) )
        
        menu_items.append( ( 'normal', 'open the html duplicates help', 'Open the help page for duplicates processing in your web browser.', page_func ) )
        
        self._help_button = ClientGUICommon.MenuBitmapButton( self._main_left_panel, CC.GlobalBMPs.help, menu_items )
        
        #
        
        self._preparing_panel = ClientGUICommon.StaticBox( self._main_left_panel, 'maintenance' )
        
        self._eligible_files = ClientGUICommon.BetterStaticText( self._preparing_panel )
        self._num_branches_to_regen = ClientGUICommon.BetterStaticText( self._preparing_panel )
        
        self._branches_button = ClientGUICommon.BetterBitmapButton( self._preparing_panel, CC.GlobalBMPs.play, self._RebalanceTree )
        
        #
        
        self._searching_panel = ClientGUICommon.StaticBox( self._main_left_panel, 'finding potential duplicates' )
        
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
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'edit duplicate metadata merge options for \'this is better\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_BETTER ) ) )
        menu_items.append( ( 'normal', 'edit duplicate metadata merge options for \'same quality\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_SAME_QUALITY ) ) )
        
        if new_options.GetBoolean( 'advanced_mode' ):
            
            menu_items.append( ( 'normal', 'edit duplicate metadata merge options for \'alternates\' (advanced!)', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_ALTERNATE ) ) )
            
        
        self._edit_merge_options = ClientGUICommon.MenuButton( self._main_right_panel, 'edit default duplicate metadata merge options', menu_items )
        
        #
        
        self._filtering_panel = ClientGUICommon.StaticBox( self._main_right_panel, 'duplicate filter' )
        
        file_search_context = management_controller.GetVariable( 'file_search_context' )
        
        predicates = file_search_context.GetPredicates()
        
        self._active_predicates_box = ClientGUIListBoxes.ListBoxTagsActiveSearchPredicates( self._filtering_panel, self._page_key, predicates )
        
        self._ac_read = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._filtering_panel, self._page_key, file_search_context, allow_all_known_files = False )
        
        self._both_files_match = wx.CheckBox( self._filtering_panel )
        
        self._num_potential_duplicates = ClientGUICommon.BetterStaticText( self._filtering_panel )
        self._refresh_dupe_counts_button = ClientGUICommon.BetterBitmapButton( self._filtering_panel, CC.GlobalBMPs.refresh, self._RefreshDuplicateCounts )
        
        self._launch_filter = ClientGUICommon.BetterButton( self._filtering_panel, 'launch the filter', self._LaunchFilter )
        
        #
        
        random_filtering_panel = ClientGUICommon.StaticBox( self._main_right_panel, 'quick and dirty processing' )
        
        self._show_some_dupes = ClientGUICommon.BetterButton( random_filtering_panel, 'show some random potential pairs', self._ShowRandomPotentialDupes )
        
        self._set_random_as_same_quality_button = ClientGUICommon.BetterButton( random_filtering_panel, 'set current media as duplicates of the same quality', self._SetCurrentMediaAs, HC.DUPLICATE_SAME_QUALITY )
        self._set_random_as_alternates_button = ClientGUICommon.BetterButton( random_filtering_panel, 'set current media as all related alternates', self._SetCurrentMediaAs, HC.DUPLICATE_ALTERNATE )
        self._set_random_as_false_positives_button = ClientGUICommon.BetterButton( random_filtering_panel, 'set current media as not related/false positive', self._SetCurrentMediaAs, HC.DUPLICATE_FALSE_POSITIVE )
        
        #
        
        self._main_notebook.AddPage( self._main_left_panel, 'preparation', select = False )
        self._main_notebook.AddPage( self._main_right_panel, 'filtering', select = True )
        
        #
        
        self._search_distance_spinctrl.SetValue( new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' ) )
        
        self._both_files_match.SetValue( management_controller.GetVariable( 'both_files_match' ) )
        
        self._both_files_match.Bind( wx.EVT_CHECKBOX, self.EventBothFilesHitChanged )
        
        self._UpdateBothFilesMatchButton()
        
        #
        
        self._sort_by.Hide()
        self._collect_by.Hide()
        
        gridbox_1 = wx.FlexGridSizer( 3 )
        
        gridbox_1.AddGrowableCol( 0, 1 )
        
        gridbox_1.Add( self._eligible_files, CC.FLAGS_VCENTER )
        gridbox_1.Add( ( 10, 10 ), CC.FLAGS_EXPAND_PERPENDICULAR )
        gridbox_1.Add( ( 10, 10 ), CC.FLAGS_EXPAND_PERPENDICULAR )
        gridbox_1.Add( self._num_branches_to_regen, CC.FLAGS_VCENTER )
        gridbox_1.Add( ( 10, 10 ), CC.FLAGS_EXPAND_PERPENDICULAR )
        gridbox_1.Add( self._branches_button, CC.FLAGS_VCENTER )
        
        self._preparing_panel.Add( gridbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        distance_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        distance_hbox.Add( ClientGUICommon.BetterStaticText( self._searching_panel, label = 'search distance: ' ), CC.FLAGS_VCENTER )
        distance_hbox.Add( self._search_distance_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        distance_hbox.Add( self._search_distance_spinctrl, CC.FLAGS_VCENTER )
        
        gridbox_2 = wx.FlexGridSizer( 2 )
        
        gridbox_2.AddGrowableCol( 0, 1 )
        
        gridbox_2.Add( self._num_searched, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        gridbox_2.Add( self._search_button, CC.FLAGS_VCENTER )
        
        self._searching_panel.Add( distance_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._searching_panel.Add( gridbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._refresh_maintenance_status, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        hbox.Add( self._refresh_maintenance_button, CC.FLAGS_VCENTER )
        hbox.Add( self._cog_button, CC.FLAGS_VCENTER )
        hbox.Add( self._help_button, CC.FLAGS_VCENTER )
        
        vbox = ClientGUICommon.BetterBoxSizer( wx.VERTICAL )
        
        vbox.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._preparing_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._searching_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._main_left_panel.SetSizer( vbox )
        
        #
        
        text_and_button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        text_and_button_hbox.Add( self._num_potential_duplicates, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        text_and_button_hbox.Add( self._refresh_dupe_counts_button, CC.FLAGS_VCENTER )
        
        rows = []
        
        rows.append( ( 'both files of pair match in search: ', self._both_files_match ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._filtering_panel, rows )
        
        self._filtering_panel.Add( self._active_predicates_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( self._ac_read, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._filtering_panel.Add( text_and_button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( self._launch_filter, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        random_filtering_panel.Add( self._show_some_dupes, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_same_quality_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_alternates_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_false_positives_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = ClientGUICommon.BetterBoxSizer( wx.VERTICAL )
        
        vbox.Add( self._edit_merge_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._filtering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( random_filtering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._main_right_panel.SetSizer( vbox )
        
        #
        
        vbox = ClientGUICommon.BetterBoxSizer( wx.VERTICAL )
        
        vbox.Add( self._main_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self._controller.sub( self, 'RefreshAllNumbers', 'refresh_dupe_page_numbers' )
        self._controller.sub( self, 'RefreshQuery', 'refresh_query' )
        self._controller.sub( self, 'SearchImmediately', 'notify_search_immediately' )
        
        HG.client_controller.pub( 'refresh_dupe_page_numbers' )
        
    
    def _EditMergeOptions( self, duplicate_type ):
        
        new_options = HG.client_controller.new_options
        
        duplicate_action_options = new_options.GetDuplicateActionOptions( duplicate_type )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit duplicate merge options' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditDuplicateActionOptionsPanel( dlg, duplicate_type, duplicate_action_options )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                duplicate_action_options = panel.GetValue()
                
                new_options.SetDuplicateActionOptions( duplicate_type, duplicate_action_options )
                
            
        
    
    def _GetFileSearchContextAndBothFilesMatch( self ):
        
        file_search_context = self._ac_read.GetFileSearchContext()
        
        predicates = self._active_predicates_box.GetPredicates()
        
        file_search_context.SetPredicates( predicates )
        
        both_files_match = self._both_files_match.GetValue()
        
        return ( file_search_context, both_files_match )
        
    
    def _LaunchFilter( self ):
        
        ( file_search_context, both_files_match ) = self._GetFileSearchContextAndBothFilesMatch()
        
        canvas_frame = ClientGUICanvas.CanvasFrame( self.GetTopLevelParent() )
        
        canvas_window = ClientGUICanvas.CanvasFilterDuplicates( canvas_frame, file_search_context, both_files_match )
        
        canvas_frame.SetCanvas( canvas_window )
        
    
    def _RebalanceTree( self ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        job_key.SetVariable( 'popup_title', 'initialising' )
        
        self._controller.Write( 'maintain_similar_files_tree', job_key = job_key )
        
        self._controller.pub( 'modal_message', job_key )
        
        self._controller.CallLater( 1.0, WaitOnDupeFilterJob, job_key )
        
    
    def _RefreshDuplicateCounts( self ):
        
        def wx_code( potential_duplicates_count ):
            
            if not self:
                
                return
                
            
            self._currently_refreshing_dupe_count_numbers = False
            
            self._refresh_dupe_counts_button.Enable()
            
            self._UpdatePotentialDuplicatesCount( potential_duplicates_count )
            
        
        def thread_do_it( file_search_context, both_files_match ):
            
            potential_duplicates_count = HG.client_controller.Read( 'potential_duplicates_count', file_search_context, both_files_match )
            
            wx.CallAfter( wx_code, potential_duplicates_count )
            
        
        if not self._currently_refreshing_dupe_count_numbers:
            
            self._currently_refreshing_dupe_count_numbers = True
            
            self._refresh_dupe_counts_button.Disable()
            
            self._num_potential_duplicates.SetLabelText( 'updating\u2026' )
            
            ( file_search_context, both_files_match ) = self._GetFileSearchContextAndBothFilesMatch()
            
            HG.client_controller.CallToThread( thread_do_it, file_search_context, both_files_match )
            
        
    
    def _RefreshMaintenanceStatus( self ):
        
        def wx_code( similar_files_maintenance_status ):
            
            if not self:
                
                return
                
            
            self._currently_refreshing_maintenance_numbers = False
            
            self._refresh_maintenance_status.SetLabelText( '' )
            
            self._refresh_maintenance_button.Enable()
            
            self._similar_files_maintenance_status = similar_files_maintenance_status
            
            self._UpdateMaintenanceStatus()
            
        
        def thread_do_it():
            
            similar_files_maintenance_status = HG.client_controller.Read( 'similar_files_maintenance_status' )
            
            wx.CallAfter( wx_code, similar_files_maintenance_status )
            
        
        if not self._currently_refreshing_maintenance_numbers:
            
            self._currently_refreshing_maintenance_numbers = True
            
            self._refresh_maintenance_status.SetLabelText( 'updating\u2026' )
            
            self._refresh_maintenance_button.Disable()
            
            HG.client_controller.CallToThread( thread_do_it )
            
        
    
    def _ResetUnknown( self ):
        
        text = 'This will delete all the potential duplicate pairs and reset their files\' search status.'
        text += os.linesep * 2
        text += 'This can be useful if you have accidentally searched too broadly and are now swamped with too many false positives.'
        
        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.Write( 'delete_potential_duplicate_pairs' )
                
                self._RefreshMaintenanceStatus()
                
            
        
    
    def _SearchDomainUpdated( self ):
        
        ( file_search_context, both_files_match ) = self._GetFileSearchContextAndBothFilesMatch()
        
        self._management_controller.SetVariable( 'file_search_context', file_search_context )
        self._management_controller.SetVariable( 'both_files_match', both_files_match )
        
        self._UpdateBothFilesMatchButton()
        
        if self._ac_read.IsSynchronised():
            
            self._RefreshDuplicateCounts()
            
        
    
    def _SearchForDuplicates( self ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        job_key.SetVariable( 'popup_title', 'initialising' )
        
        search_distance = self._search_distance_spinctrl.GetValue()
        
        self._controller.Write( 'maintain_similar_files_search_for_potential_duplicates', search_distance, job_key = job_key )
        
        self._controller.pub( 'modal_message', job_key )
        
        self._controller.CallLater( 1.0, WaitOnDupeFilterJob, job_key )
        
    
    def _SetCurrentMediaAs( self, duplicate_type ):
        
        media_panel = self._page.GetMediaPanel()
        
        change_made = media_panel.SetDuplicateStatusForAll( duplicate_type )
        
        if change_made:
            
            self._RefreshDuplicateCounts()
            
            self._ShowRandomPotentialDupes()
            
        
    
    def _SetSearchDistance( self, value ):
        
        self._search_distance_spinctrl.SetValue( value )
        
        self._UpdateMaintenanceStatus()
        
    
    def _ShowRandomPotentialDupes( self ):
        
        ( file_search_context, both_files_match ) = self._GetFileSearchContextAndBothFilesMatch()
        
        file_service_key = file_search_context.GetFileServiceKey()
        
        hashes = self._controller.Read( 'random_potential_duplicate_hashes', file_search_context, both_files_match )
        
        if len( hashes ) == 0:
            
            wx.MessageBox( 'No files were found. Try refreshing the count, and if this keeps happening, please let hydrus_dev know.' )
            
            return
            
        
        media_results = self._controller.Read( 'media_results', hashes, sorted = True )
        
        if len( media_results ) == 0:
            
            wx.MessageBox( 'Files were found, but no media results could be loaded for them. Try refreshing the count, and if this keeps happening, please let hydrus_dev know.' )
            
            return
            
        
        panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, file_service_key, media_results )
        
        self._page.SwapMediaPanel( panel )
        
    
    def _UpdateMaintenanceStatus( self ):
        
        work_can_be_done = False
        
        if self._similar_files_maintenance_status is None:
            
            return
            
        
        ( num_branches_to_regen, searched_distances_to_count ) = self._similar_files_maintenance_status
        
        self._cog_button.Enable()
        
        total_num_files = sum( searched_distances_to_count.values() )
        
        self._eligible_files.SetLabelText( '{} eligible files in the system.'.format( HydrusData.ToHumanInt( total_num_files ) ) )
        
        if num_branches_to_regen == 0:
            
            self._num_branches_to_regen.SetLabelText( 'Search tree is fast!' )
            
            self._branches_button.Disable()
            
        else:
            
            self._num_branches_to_regen.SetLabelText( HydrusData.ToHumanInt( num_branches_to_regen ) + ' search branches to rebalance.' )
            
            self._branches_button.Enable()
            
            work_can_be_done = True
            
        
        self._search_distance_button.Enable()
        self._search_distance_spinctrl.Enable()
        
        search_distance = self._search_distance_spinctrl.GetValue()
        
        new_options = self._controller.new_options
        
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
            
            work_can_be_done = True
            
        
        if work_can_be_done:
            
            page_name = 'preparation (needs work)'
            
        else:
            
            page_name = 'preparation'
            
        
        self._main_notebook.SetPageText( 0, page_name )
        
    
    def _UpdateBothFilesMatchButton( self ):
        
        ( file_search_context, both_files_match ) = self._GetFileSearchContextAndBothFilesMatch()
        
        if file_search_context.IsJustSystemEverything() or file_search_context.HasNoPredicates():
            
            self._both_files_match.Disable()
            
        else:
            
            self._both_files_match.Enable()
            
        
    
    def _UpdatePotentialDuplicatesCount( self, potential_duplicates_count ):
        
        self._num_potential_duplicates.SetLabelText( HydrusData.ToHumanInt( potential_duplicates_count ) + ' potential pairs.' )
        
        if potential_duplicates_count > 0:
            
            self._show_some_dupes.Enable()
            self._launch_filter.Enable()
            
        else:
            
            self._show_some_dupes.Disable()
            self._launch_filter.Disable()
            
        
    
    def EventBothFilesHitChanged( self, event ):
        
        self._SearchDomainUpdated()
        
    
    def EventSearchDistanceChanged( self, event ):
        
        self._UpdateMaintenanceStatus()
        
    
    def RefreshAllNumbers( self ):
        
        self._RefreshMaintenanceStatus()
        
        self._RefreshDuplicateCounts()
        
    
    def RefreshQuery( self, page_key ):
        
        if page_key == self._page_key:
            
            self._SearchDomainUpdated()
            
        
    
    def SearchImmediately( self, page_key, value ):
        
        if page_key == self._page_key:
            
            self._SearchDomainUpdated()
            
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_DUPLICATE_FILTER ] = ManagementPanelDuplicateFilter

class ManagementPanelImporter( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._controller.sub( self, 'RefreshSort', 'refresh_query' )
        
    
    def _UpdateImportStatus( self ):
        
        raise NotImplementedError()
        
    
    def PageHidden( self ):
        
        ManagementPanel.PageHidden( self )
        
    
    def PageShown( self ):
        
        ManagementPanel.PageShown( self )
        
        self._UpdateImportStatus()
        
    
    def RefreshSort( self, page_key ):
        
        if page_key == self._page_key:
            
            self._sort_by.BroadcastSort()
            
        
    
    def REPEATINGPageUpdate( self ):
        
        self._UpdateImportStatus()
        
    
class ManagementPanelImporterHDD( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self, 'import summary' )
        
        self._current_action = ClientGUICommon.BetterStaticText( self._import_queue_panel )
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( self._import_queue_panel, self._controller, self._page_key )
        
        self._pause_button = ClientGUICommon.BetterBitmapButton( self._import_queue_panel, CC.GlobalBMPs.pause, self.Pause )
        
        self._hdd_import = self._management_controller.GetVariable( 'hdd_import' )
        
        file_import_options = self._hdd_import.GetFileImportOptions()
        show_downloader_options = False
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self._import_queue_panel, file_import_options, show_downloader_options, self._hdd_import.SetFileImportOptions )
        
        #
        
        vbox = ClientGUICommon.BetterBoxSizer( wx.VERTICAL )
        
        vbox.Add( self._sort_by, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._collect_by.Hide()
        
        self._import_queue_panel.Add( self._current_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._pause_button, CC.FLAGS_LONE_BUTTON )
        self._import_queue_panel.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.Add( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        file_seed_cache = self._hdd_import.GetFileSeedCache()
        
        self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
        
        self._UpdateImportStatus()
        
    
    def _UpdateImportStatus( self ):
        
        ( current_action, paused ) = self._hdd_import.GetStatus()
        
        if paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_button, CC.GlobalBMPs.play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_button, CC.GlobalBMPs.pause )
            
        
        if paused:
            
            if current_action == '':
                
                current_action = 'paused'
                
            else:
                
                current_action = 'pausing - ' + current_action
                
            
        
        self._current_action.SetLabelText( current_action )
        
    
    def CheckAbleToClose( self ):
        
        if self._hdd_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
    
    def Pause( self ):
        
        self._hdd_import.PausePlay()
        
        self._UpdateImportStatus()
        
    
    def Start( self ):
        
        self._hdd_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_HDD ] = ManagementPanelImporterHDD

class ManagementPanelImporterMultipleGallery( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._last_time_imports_changed = 0
        self._next_update_time = 0
        
        self._multiple_gallery_import = self._management_controller.GetVariable( 'multiple_gallery_import' )
        
        self._highlighted_gallery_import = self._multiple_gallery_import.GetHighlightedGalleryImport()
        
        #
        
        self._gallery_downloader_panel = ClientGUICommon.StaticBox( self, 'gallery downloader' )
        
        #
        
        
        self._gallery_importers_status_st_top = ClientGUICommon.BetterStaticText( self._gallery_downloader_panel )
        self._gallery_importers_status_st_bottom = ClientGUICommon.BetterStaticText( self._gallery_downloader_panel )
        
        self._gallery_importers_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._gallery_downloader_panel )
        
        columns = [ ( 'query', -1 ), ( 'source', 11 ), ( 'f', 3 ), ( 's', 3 ), ( 'status', 8 ), ( 'items', 9 ), ( 'added', 8 ) ]
        
        self._gallery_importers_listctrl = ClientGUIListCtrl.BetterListCtrl( self._gallery_importers_listctrl_panel, 'gallery_importers', 4, 8, columns, self._ConvertDataToListCtrlTuples, delete_key_callback = self._RemoveGalleryImports, activation_callback = self._HighlightSelectedGalleryImport )
        
        self._gallery_importers_listctrl_panel.SetListCtrl( self._gallery_importers_listctrl )
        
        self._gallery_importers_listctrl_panel.AddButton( 'clear highlight', self._ClearExistingHighlightAndPanel, enabled_check_func = self._CanClearHighlight )
        self._gallery_importers_listctrl_panel.AddButton( 'highlight', self._HighlightSelectedGalleryImport, enabled_check_func = self._CanHighlight )
        
        self._gallery_importers_listctrl_panel.NewButtonRow()
        
        self._gallery_importers_listctrl_panel.AddButton( 'pause/play files', self._PausePlayFiles, enabled_only_on_selection = True )
        self._gallery_importers_listctrl_panel.AddButton( 'pause/play search', self._PausePlayGallery, enabled_only_on_selection = True )
        
        self._gallery_importers_listctrl_panel.NewButtonRow()
        
        self._gallery_importers_listctrl_panel.AddButton( 'retry failed', self._RetryFailed, enabled_check_func = self._CanRetryFailed )
        self._gallery_importers_listctrl_panel.AddButton( 'remove', self._RemoveGalleryImports, enabled_only_on_selection = True )
        
        self._gallery_importers_listctrl_panel.NewButtonRow()
        
        self._gallery_importers_listctrl_panel.AddButton( 'set options to queries', self._SetOptionsToGalleryImports, enabled_only_on_selection = True )
        
        self._gallery_importers_listctrl.Sort( 0 )
        
        #
        
        self._query_input = ClientGUIControls.TextAndPasteCtrl( self._gallery_downloader_panel, self._PendQueries )
        
        self._cog_button = ClientGUICommon.BetterBitmapButton( self._gallery_downloader_panel, CC.GlobalBMPs.cog, self._ShowCogMenu )
        
        self._gug_key_and_name = ClientGUIImport.GUGKeyAndNameSelector( self._gallery_downloader_panel, self._multiple_gallery_import.GetGUGKeyAndName(), update_callable = self._SetGUGKeyAndName )
        
        self._file_limit = ClientGUICommon.NoneableSpinCtrl( self._gallery_downloader_panel, 'stop after this many files', min = 1, none_phrase = 'no limit' )
        self._file_limit.Bind( wx.EVT_SPINCTRL, self.EventFileLimit )
        self._file_limit.SetToolTip( 'per query, stop searching the gallery once this many files has been reached' )
        
        file_import_options = self._multiple_gallery_import.GetFileImportOptions()
        tag_import_options = self._multiple_gallery_import.GetTagImportOptions()
        file_limit = self._multiple_gallery_import.GetFileLimit()
        
        show_downloader_options = True
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self._gallery_downloader_panel, file_import_options, show_downloader_options, self._multiple_gallery_import.SetFileImportOptions )
        self._tag_import_options = ClientGUIImport.TagImportOptionsButton( self._gallery_downloader_panel, tag_import_options, show_downloader_options, update_callable = self._multiple_gallery_import.SetTagImportOptions, allow_default_selection = True )
        
        #
        
        input_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        input_hbox.Add( self._query_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        input_hbox.Add( self._cog_button, CC.FLAGS_VCENTER )
        
        self._gallery_downloader_panel.Add( self._gallery_importers_status_st_top, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._gallery_importers_status_st_bottom, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._gallery_importers_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._gallery_downloader_panel.Add( input_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._gug_key_and_name, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._file_limit, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._tag_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._highlighted_gallery_import_panel = ClientGUIImport.GalleryImportPanel( self, self._page_key, name = 'highlighted query' )
        
        self._highlighted_gallery_import_panel.SetGalleryImport( self._highlighted_gallery_import )
        
        #
        
        vbox = ClientGUICommon.BetterBoxSizer( wx.VERTICAL )
        
        vbox.Add( self._sort_by, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._collect_by.Hide()
        
        vbox.Add( self._gallery_downloader_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._highlighted_gallery_import_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        initial_search_text = self._multiple_gallery_import.GetInitialSearchText()
        
        self._query_input.SetValue( initial_search_text )
        
        self._file_limit.SetValue( file_limit )
        
        self._UpdateImportStatus()
        
        self._gallery_importers_listctrl.AddMenuCallable( self._GetListCtrlMenu )
        
    
    def _CanClearHighlight( self ):
        
        return self._highlighted_gallery_import is not None
        
    
    def _CanHighlight( self ):
        
        selected = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( selected ) != 1:
            
            return False
            
        
        gallery_import = selected[0]
        
        return gallery_import != self._highlighted_gallery_import
        
    
    def _CanRetryFailed( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            if gallery_import.CanRetryFailed():
                
                return True
                
            
        
        return False
        
    
    def _ClearExistingHighlight( self ):
        
        if self._highlighted_gallery_import is not None:
            
            self._highlighted_gallery_import.PublishToPage( False )
            
            self._highlighted_gallery_import = None
            
            self._multiple_gallery_import.SetHighlightedGalleryImport( self._highlighted_gallery_import )
            
            self._gallery_importers_listctrl_panel.UpdateButtons()
            
            self._highlighted_gallery_import_panel.SetGalleryImport( None )
            
        
    
    def _ClearExistingHighlightAndPanel( self ):
        
        if self._highlighted_gallery_import is None:
            
            return
            
        
        self._ClearExistingHighlight()
        
        media_results = []
        
        panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, CC.LOCAL_FILE_SERVICE_KEY, media_results )
        
        self._page.SwapMediaPanel( panel )
        
        self._gallery_importers_listctrl.UpdateDatas()
        
    
    def _ConvertDataToListCtrlTuples( self, gallery_import ):
        
        query_text = gallery_import.GetQueryText()
        
        pretty_query_text = query_text
        
        if gallery_import == self._highlighted_gallery_import:
            
            pretty_query_text = '* ' + pretty_query_text
            
        
        source = gallery_import.GetSourceName()
        
        pretty_source = source
        
        files_paused = gallery_import.FilesPaused()
        
        if files_paused:
            
            pretty_files_paused = HG.client_controller.new_options.GetString( 'pause_character' )
            
        else:
            
            pretty_files_paused = ''
            
        
        gallery_finished = gallery_import.GalleryFinished()
        gallery_paused = gallery_import.GalleryPaused()
        
        if gallery_finished:
            
            pretty_gallery_paused = HG.client_controller.new_options.GetString( 'stop_character' )
            
        elif gallery_paused:
            
            pretty_gallery_paused = HG.client_controller.new_options.GetString( 'pause_character' )
            
        else:
            
            pretty_gallery_paused = ''
            
        
        status = gallery_import.GetCurrentAction()
        
        if status == '':
            
            status = gallery_import.GetGalleryStatus()
            
        
        pretty_status = status
        
        ( file_seed_cache_status, file_seed_cache_simple_status, ( num_done, num_total ) ) = gallery_import.GetFileSeedCache().GetStatus()
        
        if num_total > 0:
            
            sort_float = num_done / num_total
            
        else:
            
            sort_float = 0.0
            
        
        progress = ( sort_float, num_total, num_done )
        
        pretty_progress = file_seed_cache_simple_status
        
        added = gallery_import.GetCreationTime()
        
        pretty_added = HydrusData.TimestampToPrettyTimeDelta( added, show_seconds = False )
        
        display_tuple = ( pretty_query_text, pretty_source, pretty_files_paused, pretty_gallery_paused, pretty_status, pretty_progress, pretty_added )
        sort_tuple = ( query_text, pretty_source, files_paused, gallery_paused, status, progress, added )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopySelectedQueries( self ):
        
        gallery_importers = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_importers ) > 0:
            
            text = os.linesep.join( ( gallery_importer.GetQueryText() for gallery_importer in gallery_importers ) )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _GetListCtrlMenu( self ):
        
        selected_watchers = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( selected_watchers ) == 0:
            
            raise HydrusExceptions.DataMissing()
            
        
        menu = wx.Menu()
        
        ClientGUIMenus.AppendMenuItem( self, menu, 'copy queries', 'Copy all the selected downloaders\' queries to clipboard.', self._CopySelectedQueries )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( self, menu, 'show all importers\' presented files', 'Gather the presented files for the selected importers and show them in a new page.', self._ShowSelectedImportersFiles, show = 'presented' )
        ClientGUIMenus.AppendMenuItem( self, menu, 'show all importers\' new files', 'Gather the presented files for the selected importers and show them in a new page.', self._ShowSelectedImportersFiles, show = 'new' )
        ClientGUIMenus.AppendMenuItem( self, menu, 'show all importers\' files', 'Gather the presented files for the selected importers and show them in a new page.', self._ShowSelectedImportersFiles, show = 'all' )
        
        if self._CanRetryFailed():
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'retry failed', 'Retry all the failed downloads.', self._RetryFailed )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( self, menu, 'pause/play files', 'Pause/play all the selected downloaders\' file queues.', self._PausePlayFiles )
        ClientGUIMenus.AppendMenuItem( self, menu, 'pause/play search', 'Pause/play all the selected downloaders\' gallery searches.', self._PausePlayGallery )
        
        return menu
        
    
    def _HighlightGalleryImport( self, new_highlight ):
        
        if new_highlight == self._highlighted_gallery_import:
            
            self._ClearExistingHighlightAndPanel()
            
        else:
            
            self._ClearExistingHighlight()
            
            self._highlighted_gallery_import = new_highlight
            
            self._multiple_gallery_import.SetHighlightedGalleryImport( self._highlighted_gallery_import )
            
            hashes = self._highlighted_gallery_import.GetPresentedHashes()
            
            hashes = HG.client_controller.Read( 'filter_hashes', hashes, CC.LOCAL_FILE_SERVICE_KEY )
            
            media_results = HG.client_controller.Read( 'media_results', hashes )
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
            
            sorted_media_results = [ hashes_to_media_results[ hash ] for hash in hashes ]
            
            panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, CC.LOCAL_FILE_SERVICE_KEY, sorted_media_results )
            
            self._page.SwapMediaPanel( panel )
            
            self._gallery_importers_listctrl_panel.UpdateButtons()
            
            self._gallery_importers_listctrl.UpdateDatas()
            
            self._highlighted_gallery_import_panel.SetGalleryImport( self._highlighted_gallery_import )
            
        
    
    def _HighlightSelectedGalleryImport( self ):
        
        selected = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            new_highlight = selected[0]
            
            self._HighlightGalleryImport( new_highlight )
            
        
    
    def _PausePlayFiles( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            gallery_import.PausePlayFiles()
            
        
        self._gallery_importers_listctrl.UpdateDatas()
        
    
    def _PausePlayGallery( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            gallery_import.PausePlayGallery()
            
        
        self._gallery_importers_listctrl.UpdateDatas()
        
    
    def _PendQueries( self, queries ):
        
        results = self._multiple_gallery_import.PendQueries( queries )
        
        if len( results ) > 0 and self._highlighted_gallery_import is None and HG.client_controller.new_options.GetBoolean( 'highlight_new_query' ):
            
            first_result = results[ 0 ]
            
            self._HighlightGalleryImport( first_result )
            
        
        self._UpdateImportStatusNow()
        
    
    def _RemoveGalleryImports( self ):
        
        removees = list( self._gallery_importers_listctrl.GetData( only_selected = True ) )
        
        if len( removees ) == 0:
            
            return
            
        
        num_working = 0
        
        for gallery_import in removees:
            
            if gallery_import.CurrentlyWorking():
                
                num_working += 1
                
            
        
        message = 'Remove the ' + HydrusData.ToHumanInt( len( removees ) ) + ' selected queries?'
        
        if num_working > 0:
            
            message += os.linesep * 2
            message += HydrusData.ToHumanInt( num_working ) + ' are still working.'
            
        
        if self._highlighted_gallery_import is not None and self._highlighted_gallery_import in removees:
            
            message += os.linesep * 2
            message += 'The currently highlighted query will be removed, and the media panel cleared.'
            
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                highlight_was_included = False
                
                for gallery_import in removees:
                    
                    if self._highlighted_gallery_import is not None and gallery_import == self._highlighted_gallery_import:
                        
                        highlight_was_included = True
                        
                    
                    self._multiple_gallery_import.RemoveGalleryImport( gallery_import.GetGalleryImportKey() )
                    
                
                if highlight_was_included:
                    
                    self._ClearExistingHighlightAndPanel()
                    
                
            
        
        self._UpdateImportStatusNow()
        
    
    def _RetryFailed( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            gallery_import.RetryFailed()
            
        
    
    def _SetGUGKeyAndName( self, gug_key_and_name ):
        
        current_initial_search_text = self._multiple_gallery_import.GetInitialSearchText()
        
        current_input_value = self._query_input.GetValue()
        
        should_initialise_new_text = current_input_value in ( current_initial_search_text, '' )
        
        self._multiple_gallery_import.SetGUGKeyAndName( gug_key_and_name )
        
        if should_initialise_new_text:
            
            new_initial_search_text = self._multiple_gallery_import.GetInitialSearchText()
            
            self._query_input.SetValue( new_initial_search_text )
            
        
    
    def _SetOptionsToGalleryImports( self ):
        
        gallery_imports = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_imports ) == 0:
            
            return
            
        
        message = 'Set the current file limit, file import, and tag import options to all the selected queries? (by default, these options are only applied to new queries)'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                file_limit = self._file_limit.GetValue()
                file_import_options = self._file_import_options.GetValue()
                tag_import_options = self._tag_import_options.GetValue()
                
                for gallery_import in gallery_imports:
                    
                    gallery_import.SetFileLimit( file_limit )
                    gallery_import.SetFileImportOptions( file_import_options )
                    gallery_import.SetTagImportOptions( tag_import_options )
                    
                
            
        
    
    def _ShowCogMenu( self ):
        
        menu = wx.Menu()
        
        ( start_file_queues_paused, start_gallery_queues_paused, merge_simultaneous_pends_to_one_importer ) = self._multiple_gallery_import.GetQueueStartSettings()
        
        ClientGUIMenus.AppendMenuCheckItem( self, menu, 'start new importers\' files paused', 'Start any new importers in a file import-paused state.', start_file_queues_paused, self._multiple_gallery_import.SetQueueStartSettings, not start_file_queues_paused, start_gallery_queues_paused, merge_simultaneous_pends_to_one_importer )
        ClientGUIMenus.AppendMenuCheckItem( self, menu, 'start new importers\' search paused', 'Start any new importers in a gallery search-paused state.', start_gallery_queues_paused, self._multiple_gallery_import.SetQueueStartSettings, start_file_queues_paused, not start_gallery_queues_paused, merge_simultaneous_pends_to_one_importer )
        ClientGUIMenus.AppendSeparator( menu )
        ClientGUIMenus.AppendMenuCheckItem( self, menu, 'bundle multiple pasted queries into one importer (advanced)', 'If you are pasting many small queries at once (such as md5 lookups), check this to smooth out the workflow.', merge_simultaneous_pends_to_one_importer, self._multiple_gallery_import.SetQueueStartSettings, start_file_queues_paused, start_gallery_queues_paused, not merge_simultaneous_pends_to_one_importer )
        
        HG.client_controller.PopupMenu( self._cog_button, menu )
        
    
    def _ShowSelectedImportersFiles( self, show = 'presented' ):
        
        gallery_imports = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_imports ) == 0:
            
            return
            
        
        hashes = list()
        seen_hashes = set()
        
        for gallery_import in gallery_imports:
            
            if show == 'presented':
                
                gallery_hashes = gallery_import.GetPresentedHashes()
                
            elif show == 'new':
                
                gallery_hashes = gallery_import.GetNewHashes()
                
            elif show == 'all':
                
                gallery_hashes = gallery_import.GetHashes()
                
            
            new_hashes = [ hash for hash in gallery_hashes if hash not in seen_hashes ]
            
            hashes.extend( new_hashes )
            seen_hashes.update( new_hashes )
            
        
        hashes = HG.client_controller.Read( 'filter_hashes', hashes, CC.LOCAL_FILE_SERVICE_KEY )
        
        if len( hashes ) > 0:
            
            self._ClearExistingHighlightAndPanel()
            
            media_results = self._controller.Read( 'media_results', hashes, sorted = True )
            
            panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, CC.LOCAL_FILE_SERVICE_KEY, media_results )
            
            self._page.SwapMediaPanel( panel )
            
        else:
            
            wx.MessageBox( 'No presented hashes for that selection!' )
            
        
    
    def _UpdateImportStatus( self ):
        
        if HydrusData.TimeHasPassed( self._next_update_time ):
            
            num_items = len( self._gallery_importers_listctrl.GetData() )
            
            update_period = max( 1, int( ( num_items / 10 ) ** 0.33 ) )
            
            self._next_update_time = HydrusData.GetNow() + update_period
            
            #
            
            last_time_imports_changed = self._multiple_gallery_import.GetLastTimeImportsChanged()
            
            num_gallery_imports = self._multiple_gallery_import.GetNumGalleryImports()
            
            #
            
            if num_gallery_imports == 0:
                
                text_top = 'waiting for new queries'
                text_bottom = ''
                
            else:
                
                ( status, simple_status, ( value, range ) ) = self._multiple_gallery_import.GetTotalStatus()
                
                text_top = HydrusData.ToHumanInt( num_gallery_imports ) + ' queries - ' + HydrusData.ConvertValueRangeToPrettyString( value, range )
                text_bottom = status
                
            
            self._gallery_importers_status_st_top.SetLabelText( text_top )
            self._gallery_importers_status_st_bottom.SetLabelText( text_bottom )
            
            #
            
            if self._last_time_imports_changed != last_time_imports_changed:
                
                self._last_time_imports_changed = last_time_imports_changed
                
                gallery_imports = self._multiple_gallery_import.GetGalleryImports()
                
                self._gallery_importers_listctrl.SetData( gallery_imports )
                
                ideal_rows = len( gallery_imports )
                ideal_rows = max( 4, ideal_rows )
                ideal_rows = min( ideal_rows, 24 )
                
                self._gallery_importers_listctrl.GrowShrinkColumnsHeight( ideal_rows )
                
                self.FitInside()
                
                self.Layout()
                
            else:
                
                sort_data_has_changed = self._gallery_importers_listctrl.UpdateDatas()
                
                if sort_data_has_changed:
                    
                    self._gallery_importers_listctrl.Sort()
                    
                
            
        
    
    def _UpdateImportStatusNow( self ):
        
        self._next_update_time = 0
        
        self._UpdateImportStatus()
        
    
    def CheckAbleToClose( self ):
        
        num_working = 0
        
        for gallery_import in self._multiple_gallery_import.GetGalleryImports():
            
            if gallery_import.CurrentlyWorking():
                
                num_working += 1
                
            
        
        if num_working > 0:
            
            raise HydrusExceptions.VetoException( HydrusData.ToHumanInt( num_working ) + ' queries are still importing.' )
            
        
    
    def EventFileLimit( self, event ):
        
        self._multiple_gallery_import.SetFileLimit( self._file_limit.GetValue() )
        
        event.Skip()
        
    
    def SetSearchFocus( self ):
        
        wx.CallAfter( self._query_input.SetFocus )
        
    
    def Start( self ):
        
        self._multiple_gallery_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY ] = ManagementPanelImporterMultipleGallery

class ManagementPanelImporterMultipleWatcher( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._last_time_watchers_changed = 0
        self._next_update_time = 0
        
        self._multiple_watcher_import = self._management_controller.GetVariable( 'multiple_watcher_import' )
        
        self._highlighted_watcher = self._multiple_watcher_import.GetHighlightedWatcher()
        
        ( checker_options, file_import_options, tag_import_options ) = self._multiple_watcher_import.GetOptions()
        
        #
        
        self._watchers_panel = ClientGUICommon.StaticBox( self, 'watchers' )
        
        self._watchers_status_st_top = ClientGUICommon.BetterStaticText( self._watchers_panel )
        self._watchers_status_st_bottom = ClientGUICommon.BetterStaticText( self._watchers_panel )
        
        self._watchers_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._watchers_panel )
        
        columns = [ ( 'subject', -1 ), ( 'f', 3 ), ( 'c', 3 ), ( 'status', 8 ), ( 'items', 9 ), ( 'added', 8 ) ]
        
        self._watchers_listctrl = ClientGUIListCtrl.BetterListCtrl( self._watchers_listctrl_panel, 'watchers', 4, 8, columns, self._ConvertDataToListCtrlTuples, delete_key_callback = self._RemoveWatchers, activation_callback = self._HighlightSelectedWatcher )
        
        self._watchers_listctrl_panel.SetListCtrl( self._watchers_listctrl )
        
        self._watchers_listctrl_panel.AddButton( 'clear highlight', self._ClearExistingHighlightAndPanel, enabled_check_func = self._CanClearHighlight )
        self._watchers_listctrl_panel.AddButton( 'highlight', self._HighlightSelectedWatcher, enabled_check_func = self._CanHighlight )
        
        self._watchers_listctrl_panel.NewButtonRow()
        
        self._watchers_listctrl_panel.AddButton( 'pause/play files', self._PausePlayFiles, enabled_only_on_selection = True )
        self._watchers_listctrl_panel.AddButton( 'pause/play checking', self._PausePlayChecking, enabled_only_on_selection = True )
        self._watchers_listctrl_panel.AddButton( 'check now', self._CheckNow, enabled_only_on_selection = True )
        
        self._watchers_listctrl_panel.NewButtonRow()
        
        self._watchers_listctrl_panel.AddButton( 'retry failed', self._RetryFailed, enabled_check_func = self._CanRetryFailed )
        self._watchers_listctrl_panel.AddButton( 'remove', self._RemoveWatchers, enabled_only_on_selection = True )
        
        self._watchers_listctrl_panel.NewButtonRow()
        
        self._watchers_listctrl_panel.AddButton( 'set options to watchers', self._SetOptionsToWatchers, enabled_only_on_selection = True )
        
        self._watchers_listctrl.Sort( 3 )
        
        self._watcher_url_input = ClientGUIControls.TextAndPasteCtrl( self._watchers_panel, self._AddURLs )
        
        show_downloader_options = True
        
        self._checker_options = ClientGUIImport.CheckerOptionsButton( self._watchers_panel, checker_options, self._OptionsUpdated )
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self._watchers_panel, file_import_options, show_downloader_options, self._OptionsUpdated )
        self._tag_import_options = ClientGUIImport.TagImportOptionsButton( self._watchers_panel, tag_import_options, show_downloader_options, update_callable = self._OptionsUpdated, allow_default_selection = True )
        
        # suck up watchers from elsewhere in the program (presents a checklistboxdialog)
        
        #
        
        self._highlighted_watcher_panel = ClientGUIImport.WatcherReviewPanel( self, self._page_key, name = 'highlighted watcher' )
        
        self._highlighted_watcher_panel.SetWatcher( self._highlighted_watcher )
        
        #
        
        self._watchers_panel.Add( self._watchers_status_st_top, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._watchers_status_st_bottom, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._watchers_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._watchers_panel.Add( self._watcher_url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._checker_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._tag_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = ClientGUICommon.BetterBoxSizer( wx.VERTICAL )
        
        vbox.Add( self._sort_by, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._collect_by.Hide()
        
        vbox.Add( self._watchers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._highlighted_watcher_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        self._watchers_listctrl.AddMenuCallable( self._GetListCtrlMenu )
        
        self._UpdateImportStatus()
        
        HG.client_controller.sub( self, '_ClearExistingHighlightAndPanel', 'clear_multiwatcher_highlights' )
        
    
    def _AddURLs( self, urls, service_keys_to_tags = None ):
        
        if service_keys_to_tags is None:
            
            service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        first_result = None
        
        for url in urls:
            
            result = self._multiple_watcher_import.AddURL( url, service_keys_to_tags )
            
            if result is not None and first_result is None:
                
                first_result = result
                
            
        
        if first_result is not None and self._highlighted_watcher is None and HG.client_controller.new_options.GetBoolean( 'highlight_new_watcher' ):
            
            self._HighlightWatcher( first_result )
            
        
        self._UpdateImportStatusNow()
        
    
    def _CanClearHighlight( self ):
        
        return self._highlighted_watcher is not None
        
    
    def _CanHighlight( self ):
        
        selected = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( selected ) != 1:
            
            return False
            
        
        watcher = selected[0]
        
        return watcher != self._highlighted_watcher
        
    
    def _CanRetryFailed( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            if watcher.CanRetryFailed():
                
                return True
                
            
        
        return False
        
    
    def _CheckNow( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.CheckNow()
            
        
    
    def _ClearExistingHighlight( self ):
        
        if self._highlighted_watcher is not None:
            
            self._highlighted_watcher.PublishToPage( False )
            
            self._highlighted_watcher = None
            
            self._multiple_watcher_import.SetHighlightedWatcher( self._highlighted_watcher )
            
            self._watchers_listctrl_panel.UpdateButtons()
            
            self._highlighted_watcher_panel.SetWatcher( None )
            
        
    
    def _ClearExistingHighlightAndPanel( self ):
        
        if self._highlighted_watcher is None:
            
            return
            
        
        self._ClearExistingHighlight()
        
        media_results = []
        
        panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, CC.LOCAL_FILE_SERVICE_KEY, media_results )
        
        self._page.SwapMediaPanel( panel )
        
        self._watchers_listctrl.UpdateDatas()
        
    
    def _ConvertDataToListCtrlTuples( self, watcher ):
        
        subject = watcher.GetSubject()
        
        pretty_subject = subject
        
        if watcher == self._highlighted_watcher:
            
            pretty_subject = '* ' + pretty_subject
            
        
        files_paused = watcher.FilesPaused()
        
        if files_paused:
            
            pretty_files_paused = HG.client_controller.new_options.GetString( 'pause_character' )
            
        else:
            
            pretty_files_paused = ''
            
        
        checking_dead = watcher.IsDead()
        checking_paused = watcher.CheckingPaused()
        
        if checking_dead:
            
            pretty_checking_paused = HG.client_controller.new_options.GetString( 'stop_character' )
            
        elif checking_paused:
            
            pretty_checking_paused = HG.client_controller.new_options.GetString( 'pause_character' )
            
        else:
            
            pretty_checking_paused = ''
            
        
        ( status, simple_status, ( num_done, num_total ) ) = watcher.GetFileSeedCache().GetStatus()
        
        if num_total > 0:
            
            sort_float = num_done / num_total
            
        else:
            
            sort_float = 0.0
            
        
        progress = ( sort_float, num_total, num_done )
        
        pretty_progress = simple_status
        
        added = watcher.GetCreationTime()
        
        pretty_added = HydrusData.TimestampToPrettyTimeDelta( added, show_seconds = False )
        
        watcher_status = self._multiple_watcher_import.GetWatcherSimpleStatus( watcher )
        
        pretty_watcher_status = watcher_status
        
        if watcher_status == '':
            
            watcher_status = 'zzz' # to sort _after_ DEAD and other interesting statuses on ascending sort
            
        
        display_tuple = ( pretty_subject, pretty_files_paused, pretty_checking_paused, pretty_watcher_status, pretty_progress, pretty_added )
        sort_tuple = ( subject, files_paused, checking_paused, watcher_status, progress, added )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopySelectedURLs( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) > 0:
            
            text = os.linesep.join( ( watcher.GetURL() for watcher in watchers ) )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _GetListCtrlMenu( self ):
        
        selected_watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( selected_watchers ) == 0:
            
            raise HydrusExceptions.DataMissing()
            
        
        menu = wx.Menu()
        
        ClientGUIMenus.AppendMenuItem( self, menu, 'copy urls', 'Copy all the selected watchers\' urls to clipboard.', self._CopySelectedURLs )
        ClientGUIMenus.AppendMenuItem( self, menu, 'open urls', 'Open all the selected watchers\' urls in your browser.', self._OpenSelectedURLs )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( self, menu, 'show all watchers\' presented files', 'Gather the presented files for the selected watchers and show them in a new page.', self._ShowSelectedImportersFiles, show = 'presented' )
        ClientGUIMenus.AppendMenuItem( self, menu, 'show all watchers\' new files', 'Gather the presented files for the selected watchers and show them in a new page.', self._ShowSelectedImportersFiles, show = 'new' )
        ClientGUIMenus.AppendMenuItem( self, menu, 'show all watchers\' files', 'Gather the presented files for the selected watchers and show them in a new page.', self._ShowSelectedImportersFiles, show = 'all' )
        
        if self._CanRetryFailed():
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'retry failed', 'Retry all the failed downloads.', self._RetryFailed )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( self, menu, 'pause/play files', 'Pause/play all the selected watchers\' file queues.', self._PausePlayFiles )
        ClientGUIMenus.AppendMenuItem( self, menu, 'pause/play checking', 'Pause/play all the selected watchers\' checking routines.', self._PausePlayChecking )
        
        return menu
        
    
    def _HighlightWatcher( self, new_highlight ):
        
        if new_highlight == self._highlighted_watcher:
            
            self._ClearExistingHighlightAndPanel()
            
        else:
            
            self._ClearExistingHighlight()
            
            self._highlighted_watcher = new_highlight
            
            hashes = self._highlighted_watcher.GetPresentedHashes()
            
            hashes = HG.client_controller.Read( 'filter_hashes', hashes, CC.LOCAL_FILE_SERVICE_KEY )
            
            media_results = HG.client_controller.Read( 'media_results', hashes )
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in media_results }
            
            sorted_media_results = [ hashes_to_media_results[ hash ] for hash in hashes ]
            
            panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, CC.LOCAL_FILE_SERVICE_KEY, sorted_media_results )
            
            self._page.SwapMediaPanel( panel )
            
            self._multiple_watcher_import.SetHighlightedWatcher( self._highlighted_watcher )
            
            self._watchers_listctrl_panel.UpdateButtons()
            
            self._watchers_listctrl.UpdateDatas()
            
            self._highlighted_watcher_panel.SetWatcher( self._highlighted_watcher )
            
        
    
    def _HighlightSelectedWatcher( self ):
        
        selected = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            new_highlight = selected[0]
            
            self._HighlightWatcher( new_highlight )
            
        
    
    def _OpenSelectedURLs( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) > 0:
            
            if len( watchers ) > 10:
                
                message = 'You have many watchers selected--are you sure you want to open them all?'
                
                with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                    
                    if dlg.ShowModal() != wx.ID_YES:
                        
                        return
                        
                    
                
            
            for watcher in watchers:
                
                ClientPaths.LaunchURLInWebBrowser( watcher.GetURL() )
                
            
        
    
    def _OptionsUpdated( self, *args, **kwargs ):
        
        self._multiple_watcher_import.SetOptions( self._checker_options.GetValue(), self._file_import_options.GetValue(), self._tag_import_options.GetValue() )
        
    
    def _PausePlayChecking( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.PausePlayChecking()
            
        
        self._watchers_listctrl.UpdateDatas()
        
    
    def _PausePlayFiles( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.PausePlayFiles()
            
        
        self._watchers_listctrl.UpdateDatas()
        
    
    def _RemoveWatchers( self ):
        
        removees = list( self._watchers_listctrl.GetData( only_selected = True ) )
        
        if len( removees ) == 0:
            
            return
            
        
        num_working = 0
        num_alive = 0
        
        for watcher in removees:
            
            if watcher.CurrentlyWorking():
                
                num_working += 1
                
            
            if watcher.CurrentlyAlive():
                
                num_alive += 1
                
            
        
        message = 'Remove the ' + HydrusData.ToHumanInt( len( removees ) ) + ' selected watchers?'
        
        if num_working > 0:
            
            message += os.linesep * 2
            message += HydrusData.ToHumanInt( num_working ) + ' are still working.'
            
        
        if num_alive > 0:
            
            message += os.linesep * 2
            message += HydrusData.ToHumanInt( num_alive ) + ' are not yet DEAD.'
            
        
        if self._highlighted_watcher is not None and self._highlighted_watcher in removees:
            
            message += os.linesep * 2
            message += 'The currently highlighted watcher will be removed, and the media panel cleared.'
            
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                highlight_was_included = False
                
                for watcher in removees:
                    
                    if self._highlighted_watcher is not None and watcher == self._highlighted_watcher:
                        
                        highlight_was_included = True
                        
                    
                    self._multiple_watcher_import.RemoveWatcher( watcher.GetWatcherKey() )
                    
                
                if highlight_was_included:
                    
                    self._ClearExistingHighlightAndPanel()
                    
                
            
        
        self._UpdateImportStatusNow()
        
    
    def _RetryFailed( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.RetryFailed()
            
        
    
    def _SetOptionsToWatchers( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) == 0:
            
            return
            
        
        message = 'Set the current checker, file import, and tag import options to all the selected watchers? (by default, these options are only applied to new watchers)'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                checker_options = self._checker_options.GetValue()
                file_import_options = self._file_import_options.GetValue()
                tag_import_options = self._tag_import_options.GetValue()
                
                for watcher in watchers:
                    
                    watcher.SetCheckerOptions( checker_options )
                    watcher.SetFileImportOptions( file_import_options )
                    watcher.SetTagImportOptions( tag_import_options )
                    
                
            
        
    
    def _ShowSelectedImportersFiles( self, show = 'presented' ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) == 0:
            
            return
            
        
        hashes = list()
        seen_hashes = set()
        
        for watcher in watchers:
            
            if show == 'presented':
                
                watcher_hashes = watcher.GetPresentedHashes()
                
            elif show == 'new':
                
                watcher_hashes = watcher.GetNewHashes()
                
            elif show == 'all':
                
                watcher_hashes = watcher.GetHashes()
                
            
            new_hashes = [ hash for hash in watcher_hashes if hash not in seen_hashes ]
            
            hashes.extend( new_hashes )
            seen_hashes.update( new_hashes )
            
        
        hashes = HG.client_controller.Read( 'filter_hashes', hashes, CC.LOCAL_FILE_SERVICE_KEY )
        
        if len( hashes ) > 0:
            
            self._ClearExistingHighlightAndPanel()
            
            media_results = self._controller.Read( 'media_results', hashes, sorted = True )
            
            panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, CC.LOCAL_FILE_SERVICE_KEY, media_results )
            
            self._page.SwapMediaPanel( panel )
            
        else:
            
            wx.MessageBox( 'No presented hashes for that selection!' )
            
        
    
    def _UpdateImportStatus( self ):
        
        if HydrusData.TimeHasPassed( self._next_update_time ):
            
            num_items = len( self._watchers_listctrl.GetData() )
            
            update_period = max( 1, int( ( num_items / 10 ) ** 0.33 ) )
            
            self._next_update_time = HydrusData.GetNow() + update_period
            
            #
            
            last_time_watchers_changed = self._multiple_watcher_import.GetLastTimeWatchersChanged()
            num_watchers = self._multiple_watcher_import.GetNumWatchers()
            
            #
            
            if num_watchers == 0:
                
                text_top = 'waiting for new watchers'
                text_bottom = ''
                
            else:
                
                num_dead = self._multiple_watcher_import.GetNumDead()
                
                if num_dead == 0:
                    
                    num_dead_text = ''
                    
                else:
                    
                    num_dead_text = HydrusData.ToHumanInt( num_dead ) + ' DEAD - '
                    
                
                ( status, simple_status, ( value, range ) ) = self._multiple_watcher_import.GetTotalStatus()
                
                text_top = HydrusData.ToHumanInt( num_watchers ) + ' watchers - ' + num_dead_text + HydrusData.ConvertValueRangeToPrettyString( value, range )
                text_bottom = status
                
            
            self._watchers_status_st_top.SetLabelText( text_top )
            self._watchers_status_st_bottom.SetLabelText( text_bottom )
            
            #
            
            if self._last_time_watchers_changed != last_time_watchers_changed:
                
                self._last_time_watchers_changed = last_time_watchers_changed
                
                watchers = self._multiple_watcher_import.GetWatchers()
                
                self._watchers_listctrl.SetData( watchers )
                
                ideal_rows = len( watchers )
                ideal_rows = max( 4, ideal_rows )
                ideal_rows = min( ideal_rows, 24 )
                
                self._watchers_listctrl.GrowShrinkColumnsHeight( ideal_rows )
                
                self.FitInside()
                
                self.Layout()
                
            else:
                
                sort_data_has_changed = self._watchers_listctrl.UpdateDatas()
                
                if sort_data_has_changed:
                    
                    self._watchers_listctrl.Sort()
                    
                
            
        
    
    def _UpdateImportStatusNow( self ):
        
        self._next_update_time = 0
        
        self._UpdateImportStatus()
        
    
    def CheckAbleToClose( self ):
        
        num_working = 0
        
        for watcher in self._multiple_watcher_import.GetWatchers():
            
            if watcher.CurrentlyWorking():
                
                num_working += 1
                
            
        
        if num_working > 0:
            
            raise HydrusExceptions.VetoException( HydrusData.ToHumanInt( num_working ) + ' watchers are still importing.' )
            
        
    
    def PendURL( self, url, service_keys_to_tags = None ):
        
        if service_keys_to_tags is None:
            
            service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        self._AddURLs( ( url, ), service_keys_to_tags )
        
    
    def SetSearchFocus( self ):
        
        wx.CallAfter( self._watcher_url_input.SetFocus )
        
    
    def Start( self ):
        
        self._multiple_watcher_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER ] = ManagementPanelImporterMultipleWatcher

class ManagementPanelImporterSimpleDownloader( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._simple_downloader_import = self._management_controller.GetVariable( 'simple_downloader_import' )
        
        #
        
        self._simple_downloader_panel = ClientGUICommon.StaticBox( self, 'simple downloader' )
        
        #
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self._simple_downloader_panel, 'imports' )
        
        self._pause_files_button = ClientGUICommon.BetterBitmapButton( self._import_queue_panel, CC.GlobalBMPs.pause, self.PauseFiles )
        
        self._current_action = ClientGUICommon.BetterStaticText( self._import_queue_panel, style = wx.ST_ELLIPSIZE_END )
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( self._import_queue_panel, self._controller, self._page_key )
        self._file_download_control = ClientGUIControls.NetworkJobControl( self._import_queue_panel )
        
        #
        
        #
        
        self._simple_parsing_jobs_panel = ClientGUICommon.StaticBox( self._simple_downloader_panel, 'simple parsing urls' )
        
        self._pause_queue_button = ClientGUICommon.BetterBitmapButton( self._simple_parsing_jobs_panel, CC.GlobalBMPs.pause, self.PauseQueue )
        
        self._parser_status = ClientGUICommon.BetterStaticText( self._simple_parsing_jobs_panel, style = wx.ST_ELLIPSIZE_END )
        
        self._gallery_seed_log_control = ClientGUIGallerySeedLog.GallerySeedLogStatusControl( self._simple_parsing_jobs_panel, self._controller, True, False, self._page_key )
        
        self._page_download_control = ClientGUIControls.NetworkJobControl( self._simple_parsing_jobs_panel )
        
        self._pending_jobs_listbox = wx.ListBox( self._simple_parsing_jobs_panel, size = ( -1, 100 ) )
        
        self._advance_button = wx.Button( self._simple_parsing_jobs_panel, label = '\u2191' )
        self._advance_button.Bind( wx.EVT_BUTTON, self.EventAdvance )
        
        self._delete_button = wx.Button( self._simple_parsing_jobs_panel, label = 'X' )
        self._delete_button.Bind( wx.EVT_BUTTON, self.EventDelete )
        
        self._delay_button = wx.Button( self._simple_parsing_jobs_panel, label = '\u2193' )
        self._delay_button.Bind( wx.EVT_BUTTON, self.EventDelay )
        
        self._page_url_input = ClientGUIControls.TextAndPasteCtrl( self._simple_parsing_jobs_panel, self._PendPageURLs )
        
        self._formulae = ClientGUICommon.BetterChoice( self._simple_parsing_jobs_panel )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'edit formulae', 'Edit these parsing formulae.', self._EditFormulae ) )
        
        self._formula_cog = ClientGUICommon.MenuBitmapButton( self._simple_parsing_jobs_panel, CC.GlobalBMPs.cog, menu_items )
        
        self._RefreshFormulae()
        
        file_import_options = self._simple_downloader_import.GetFileImportOptions()
        
        show_downloader_options = True
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self._simple_downloader_panel, file_import_options, show_downloader_options, self._simple_downloader_import.SetFileImportOptions )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._current_action, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        hbox.Add( self._pause_files_button, CC.FLAGS_VCENTER )
        
        self._import_queue_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        queue_buttons_vbox = wx.BoxSizer( wx.VERTICAL )
        
        queue_buttons_vbox.Add( self._advance_button, CC.FLAGS_VCENTER )
        queue_buttons_vbox.Add( self._delete_button, CC.FLAGS_VCENTER )
        queue_buttons_vbox.Add( self._delay_button, CC.FLAGS_VCENTER )
        
        queue_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        queue_hbox.Add( self._pending_jobs_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        queue_hbox.Add( queue_buttons_vbox, CC.FLAGS_VCENTER )
        
        formulae_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        formulae_hbox.Add( self._formulae, CC.FLAGS_EXPAND_BOTH_WAYS )
        formulae_hbox.Add( self._formula_cog, CC.FLAGS_VCENTER )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._parser_status, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        hbox.Add( self._pause_queue_button, CC.FLAGS_VCENTER )
        
        self._simple_parsing_jobs_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( self._gallery_seed_log_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( self._page_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( queue_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._simple_parsing_jobs_panel.Add( self._page_url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( formulae_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._simple_downloader_panel.Add( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_downloader_panel.Add( self._simple_parsing_jobs_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_downloader_panel.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = ClientGUICommon.BetterBoxSizer( wx.VERTICAL )
        
        vbox.Add( self._sort_by, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._collect_by.Hide()
        
        vbox.Add( self._simple_downloader_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        self._formulae.Bind( wx.EVT_CHOICE, self.EventFormulaChanged )
        
        file_seed_cache = self._simple_downloader_import.GetFileSeedCache()
        
        self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
        
        gallery_seed_log = self._simple_downloader_import.GetGallerySeedLog()
        
        self._gallery_seed_log_control.SetGallerySeedLog( gallery_seed_log )
        
        self._UpdateImportStatus()
        
    
    def _EditFormulae( self ):
        
        def data_to_pretty_callable( data ):
            
            simple_downloader_formula = data
            
            return simple_downloader_formula.GetName()
            
        
        def edit_callable( data ):
            
            simple_downloader_formula = data
            
            name = simple_downloader_formula.GetName()
            
            with ClientGUIDialogs.DialogTextEntry( dlg, 'edit name', default = name ) as dlg_2:
                
                if dlg_2.ShowModal() == wx.ID_OK:
                    
                    name = dlg_2.GetValue()
                    
                else:
                    
                    raise HydrusExceptions.VetoException()
                    
                
            
            with ClientGUITopLevelWindows.DialogEdit( dlg, 'edit formula' ) as dlg_3:
                
                panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg_3 )
                
                formula = simple_downloader_formula.GetFormula()
                
                control = ClientGUIParsing.EditFormulaPanel( panel, formula, lambda: ( {}, '' ) )
                
                panel.SetControl( control )
                
                dlg_3.SetPanel( panel )
                
                if dlg_3.ShowModal() == wx.ID_OK:
                    
                    formula = control.GetValue()
                    
                    simple_downloader_formula = ClientParsing.SimpleDownloaderParsingFormula( name = name, formula = formula )
                    
                    return simple_downloader_formula
                    
                else:
                    
                    raise HydrusExceptions.VetoException()
                    
                
            
        
        def add_callable():
            
            data = ClientParsing.SimpleDownloaderParsingFormula()
            
            return edit_callable( data )
            
        
        formulae = list( self._controller.new_options.GetSimpleDownloaderFormulae() )
        
        formulae.sort( key = lambda o: o.GetName() )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit simple downloader formulae' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            height_num_chars = 20
            
            control = ClientGUIListBoxes.AddEditDeleteListBoxUniqueNamedObjects( panel, height_num_chars, data_to_pretty_callable, add_callable, edit_callable )
            
            control.AddSeparator()
            control.AddImportExportButtons( ( ClientParsing.SimpleDownloaderParsingFormula, ) )
            control.AddSeparator()
            control.AddDefaultsButton( ClientDefaults.GetDefaultSimpleDownloaderFormulae )
            
            control.AddDatas( formulae )
            
            panel.SetControl( control )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                formulae = control.GetData()
                
                self._controller.new_options.SetSimpleDownloaderFormulae( formulae )
                
            
        
        self._RefreshFormulae()
        
    
    def _PendPageURLs( self, urls ):
        
        urls = [ url for url in urls if url.startswith( 'http' ) ]
        
        simple_downloader_formula = self._formulae.GetChoice()
        
        for url in urls:
            
            job = ( url, simple_downloader_formula )
            
            self._simple_downloader_import.PendJob( job )
            
        
        self._UpdateImportStatus()
        
    
    def _RefreshFormulae( self ):
        
        self._formulae.Clear()
        
        to_select = None
        
        select_name = self._simple_downloader_import.GetFormulaName()
        
        simple_downloader_formulae = list( self._controller.new_options.GetSimpleDownloaderFormulae() )
        
        simple_downloader_formulae.sort( key = lambda o: o.GetName() )
        
        for ( i, simple_downloader_formula ) in enumerate( simple_downloader_formulae ):
            
            name = simple_downloader_formula.GetName()
            
            self._formulae.Append( name, simple_downloader_formula )
            
            if name == select_name:
                
                to_select = i
                
            
        
        if to_select is not None:
            
            self._formulae.Select( to_select )
            
        
    
    def _UpdateImportStatus( self ):
        
        ( pending_jobs, parser_status, current_action, queue_paused, files_paused ) = self._simple_downloader_import.GetStatus()
        
        current_pending_jobs = [ self._pending_jobs_listbox.GetClientData( i ) for i in range( self._pending_jobs_listbox.GetCount() ) ]
        
        if current_pending_jobs != pending_jobs:
            
            selected_string = self._pending_jobs_listbox.GetStringSelection()
            
            self._pending_jobs_listbox.Clear()
            
            for job in pending_jobs:
                
                ( url, simple_downloader_formula ) = job
                
                pretty_job = simple_downloader_formula.GetName() + ': ' + url
                
                self._pending_jobs_listbox.Append( pretty_job, job )
                
            
            selection_index = self._pending_jobs_listbox.FindString( selected_string )
            
            if selection_index != wx.NOT_FOUND:
                
                self._pending_jobs_listbox.Select( selection_index )
                
            
        
        if queue_paused:
            
            parser_status = 'paused'
            
        
        self._parser_status.SetLabelText( parser_status )
        
        if current_action == '' and files_paused:
            
            current_action = 'paused'
            
        
        self._current_action.SetLabelText( current_action )
        
        if queue_paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_queue_button, CC.GlobalBMPs.play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_queue_button, CC.GlobalBMPs.pause )
            
        
        if files_paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_files_button, CC.GlobalBMPs.play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_files_button, CC.GlobalBMPs.pause )
            
        
        ( file_network_job, page_network_job ) = self._simple_downloader_import.GetNetworkJobs()
        
        self._file_download_control.SetNetworkJob( file_network_job )
        
        self._page_download_control.SetNetworkJob( page_network_job )
        
    
    def CheckAbleToClose( self ):
        
        if self._simple_downloader_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
    
    def EventAdvance( self, event ):
        
        selection = self._pending_jobs_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            job = self._pending_jobs_listbox.GetClientData( selection )
            
            self._simple_downloader_import.AdvanceJob( job )
            
            self._UpdateImportStatus()
            
        
    
    def EventDelay( self, event ):
        
        selection = self._pending_jobs_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            job = self._pending_jobs_listbox.GetClientData( selection )
            
            self._simple_downloader_import.DelayJob( job )
            
            self._UpdateImportStatus()
            
        
    
    def EventDelete( self, event ):
        
        selection = self._pending_jobs_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            job = self._pending_jobs_listbox.GetClientData( selection )
            
            self._simple_downloader_import.DeleteJob( job )
            
            self._UpdateImportStatus()
            
        
    
    def EventFormulaChanged( self, event ):
        
        formula = self._formulae.GetChoice()
        
        formula_name = formula.GetName()
        
        self._simple_downloader_import.SetFormulaName( formula_name )
        self._controller.new_options.SetString( 'favourite_simple_downloader_formula', formula_name )
        
        event.Skip()
        
    
    def PauseQueue( self ):
        
        self._simple_downloader_import.PausePlayQueue()
        
        self._UpdateImportStatus()
        
    
    def PauseFiles( self ):
        
        self._simple_downloader_import.PausePlayFiles()
        
        self._UpdateImportStatus()
        
    
    def SetSearchFocus( self ):
        
        wx.CallAfter( self._page_url_input.SetFocus )
        
    
    def Start( self ):
        
        self._simple_downloader_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER ] = ManagementPanelImporterSimpleDownloader

class ManagementPanelImporterURLs( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        #
        
        self._url_panel = ClientGUICommon.StaticBox( self, 'url downloader' )
        
        self._pause_button = ClientGUICommon.BetterBitmapButton( self._url_panel, CC.GlobalBMPs.pause, self.Pause )
        
        self._file_download_control = ClientGUIControls.NetworkJobControl( self._url_panel )
        
        self._urls_import = self._management_controller.GetVariable( 'urls_import' )
        
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( self._url_panel, self._controller, page_key = self._page_key )
        
        self._gallery_download_control = ClientGUIControls.NetworkJobControl( self._url_panel )
        
        self._gallery_seed_log_control = ClientGUIGallerySeedLog.GallerySeedLogStatusControl( self._url_panel, self._controller, False, False, page_key = self._page_key )
        
        self._url_input = ClientGUIControls.TextAndPasteCtrl( self._url_panel, self._PendURLs )
        
        ( file_import_options, tag_import_options ) = self._urls_import.GetOptions()
        
        show_downloader_options = True
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self._url_panel, file_import_options, show_downloader_options, self._urls_import.SetFileImportOptions )
        self._tag_import_options = ClientGUIImport.TagImportOptionsButton( self._url_panel, tag_import_options, show_downloader_options, update_callable = self._urls_import.SetTagImportOptions, allow_default_selection = True )
        
        #
        
        self._url_panel.Add( self._pause_button, CC.FLAGS_LONE_BUTTON )
        self._url_panel.Add( self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._file_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._gallery_seed_log_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._gallery_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._tag_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = ClientGUICommon.BetterBoxSizer( wx.VERTICAL )
        
        vbox.Add( self._sort_by, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._collect_by.Hide()
        
        vbox.Add( self._url_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        #
        
        file_seed_cache = self._urls_import.GetFileSeedCache()
        
        self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
        
        gallery_seed_log = self._urls_import.GetGallerySeedLog()
        
        self._gallery_seed_log_control.SetGallerySeedLog( gallery_seed_log )
        
        self._UpdateImportStatus()
        
    
    def _PendURLs( self, urls, service_keys_to_tags = None ):
        
        if service_keys_to_tags is None:
            
            service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        urls = [ url for url in urls if url.startswith( 'http' ) ]
        
        self._urls_import.PendURLs( urls, service_keys_to_tags )
        
        self._UpdateImportStatus()
        
    
    def _UpdateImportStatus( self ):
        
        paused = self._urls_import.IsPaused()
        
        if paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_button, CC.GlobalBMPs.play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_button, CC.GlobalBMPs.pause )
            
        
        ( file_network_job, gallery_network_job ) = self._urls_import.GetNetworkJobs()
        
        self._file_download_control.SetNetworkJob( file_network_job )
        
        self._gallery_download_control.SetNetworkJob( gallery_network_job )
        
    
    def CheckAbleToClose( self ):
        
        if self._urls_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
    
    def Pause( self ):
        
        self._urls_import.PausePlay()
        
        self._UpdateImportStatus()
        
    
    def PendURL( self, url, service_keys_to_tags = None ):
        
        if service_keys_to_tags is None:
            
            service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        self._PendURLs( ( url, ), service_keys_to_tags )
        
    
    def SetSearchFocus( self ):
        
        wx.CallAfter( self._url_input.SetFocus )
        
    
    def Start( self ):
        
        self._urls_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_IMPORT_URLS ] = ManagementPanelImporterURLs

class ManagementPanelPetitions( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        self._petition_service_key = management_controller.GetKey( 'petition_service' )
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._service = self._controller.services_manager.GetService( self._petition_service_key )
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
            
            st = ClientGUICommon.BetterStaticText( self._petitions_info_panel )
            button = ClientGUICommon.BetterButton( self._petitions_info_panel, 'fetch ' + HC.content_status_string_lookup[ status ] + ' ' + HC.content_type_string_lookup[ content_type ] + ' petition', func )
            
            button.Disable()
            
            self._petition_types_to_controls[ ( content_type, status ) ] = ( st, button )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( st, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
            hbox.Add( button, CC.FLAGS_VCENTER )
            
            content_type_hboxes.append( hbox )
            
        
        #
        
        self._petition_panel = ClientGUICommon.StaticBox( self, 'petition' )
        
        self._action_text = ClientGUICommon.BetterStaticText( self._petition_panel, label = '' )
        
        self._reason_text = ClientGUICommon.SaneMultilineTextCtrl( self._petition_panel, style = wx.TE_READONLY )
        self._reason_text.SetMinSize( ( -1, 80 ) )
        
        check_all = ClientGUICommon.BetterButton( self._petition_panel, 'check all', self._CheckAll )
        flip_selected = ClientGUICommon.BetterButton( self._petition_panel, 'flip selected', self._FlipSelected )
        check_none = ClientGUICommon.BetterButton( self._petition_panel, 'check none', self._CheckNone )
        
        self._contents = wx.CheckListBox( self._petition_panel, style = wx.LB_EXTENDED )
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
        
        self._petitions_info_panel.Add( self._refresh_num_petitions_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        for hbox in content_type_hboxes:
            
            self._petitions_info_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        check_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        check_hbox.Add( check_all, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        check_hbox.Add( flip_selected, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        check_hbox.Add( check_none, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        
        self._petition_panel.Add( ClientGUICommon.BetterStaticText( self._petition_panel, label = 'Double-click a petition to see its files, if it has them.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._action_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._reason_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( check_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._petition_panel.Add( self._contents, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._petition_panel.Add( self._process, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._modify_petitioner, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = ClientGUICommon.BetterBoxSizer( wx.VERTICAL )
        
        vbox.Add( self._sort_by, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._collect_by, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.Add( self._petitions_info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._petition_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        self._controller.sub( self, 'RefreshQuery', 'refresh_query' )
        
    
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
            
            def key( c ):
                
                if c.GetContentType() in ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ):
                    
                    ( part_two, part_one ) = c.GetContentData()
                    
                elif c.GetContentType() == HC.CONTENT_TYPE_MAPPINGS:
                    
                    ( tag, hashes ) = c.GetContentData()
                    
                    part_one = tag
                    part_two = None
                    
                else:
                    
                    part_one = None
                    part_two = None
                    
                
                return ( -c.GetVirtualWeight(), part_one, part_two )
                
            
            contents.sort( key = key )
            
            self._contents.Clear()
            
            for content in contents:
                
                content_string = self._contents.EscapeMnemonics( content.ToString() )
                
                self._contents.Append( content_string, content )
                
            
            self._contents.SetCheckedItems( list( range( self._contents.GetCount() ) ) )
            
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
                
                st.SetLabelText( HydrusData.ToHumanInt( count ) + ' petitions' )
                
                if count > 0:
                    
                    button.Enable()
                    
                    if self._current_petition is None and not new_petition_fetched:
                        
                        self._FetchPetition( content_type, status )
                        
                        new_petition_fetched = True
                        
                    
                else:
                    
                    button.Disable()
                    
                
            
        
    
    def _FetchNumPetitions( self ):
        
        def do_it( service ):
            
            def wx_draw( n_p_i ):
                
                if not self:
                    
                    return
                    
                
                self._num_petition_info = n_p_i
                
                self._DrawNumPetitions()
                
            
            def wx_reset():
                
                if not self:
                    
                    return
                    
                
                self._refresh_num_petitions_button.SetLabelText( 'refresh counts' )
                
            
            try:
                
                response = service.Request( HC.GET, 'num_petitions' )
                
                num_petition_info = response[ 'num_petitions' ]
                
                wx.CallAfter( wx_draw, num_petition_info )
                
            finally:
                
                wx.CallAfter( wx_reset )
                
            
        
        self._refresh_num_petitions_button.SetLabelText( 'Fetching\u2026' )
        
        self._controller.CallToThread( do_it, self._service )
        
    
    def _FetchPetition( self, content_type, status ):
        
        ( st, button ) = self._petition_types_to_controls[ ( content_type, status ) ]
        
        def wx_setpet( petition ):
            
            if not self:
                
                return
                
            
            self._current_petition = petition
            
            self._DrawCurrentPetition()
            
        
        def wx_done():
            
            if not self:
                
                return
                
            
            button.Enable()
            button.SetLabelText( 'fetch ' + HC.content_status_string_lookup[ status ] + ' ' + HC.content_type_string_lookup[ content_type ] + ' petition' )
            
        
        def do_it( service ):
            
            try:
                
                response = service.Request( HC.GET, 'petition', { 'content_type' : content_type, 'status' : status } )
                
                wx.CallAfter( wx_setpet, response[ 'petition' ] )
                
            finally:
                
                wx.CallAfter( wx_done )
                
            
        
        if self._current_petition is not None:
            
            self._current_petition = None
            
            self._DrawCurrentPetition()
            
        
        button.Disable()
        button.SetLabelText( 'Fetching\u2026' )
        
        self._controller.CallToThread( do_it, self._service )
        
    
    def _FlipSelected( self ):
        
        for i in self._contents.GetSelections():
            
            flipped_state = not self._contents.IsChecked( i )
            
            self._contents.Check( i, flipped_state )
            
        
    
    def _ShowHashes( self, hashes ):
        
        file_service_key = self._management_controller.GetKey( 'file_service' )
        
        with wx.BusyCursor():
            
            media_results = self._controller.Read( 'media_results', hashes )
            
        
        panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, file_service_key, media_results )
        
        panel.Collect( self._page_key, self._collect_by.GetChoice() )
        
        panel.Sort( self._page_key, self._sort_by.GetSort() )
        
        self._page.SwapMediaPanel( panel )
        
    
    def EventContentDoubleClick( self, event ):
        
        selections = self._contents.GetSelections()
        
        if len( selections ) > 0:
            
            selection = selections[0]
            
            content = self._contents.GetClientData( selection )
            
            if content.HasHashes():
                
                self._ShowHashes( content.GetHashes() )
                
            
        
    
    def EventProcess( self, event ):
        
        def break_approved_contents_into_chunks( approved_contents ):
            
            chunks_of_approved_contents = []
            chunk_of_approved_contents = []
            
            weight = 0
            
            for content in approved_contents:
                
                for content_chunk in content.IterateUploadableChunks(): # break 20K-strong mappings petitions into smaller bits to POST back
                    
                    chunk_of_approved_contents.append( content_chunk )
                    
                    weight += content.GetVirtualWeight()
                    
                    if weight > 50:
                        
                        chunks_of_approved_contents.append( chunk_of_approved_contents )
                        
                        chunk_of_approved_contents = []
                        
                        weight = 0
                        
                    
                
            
            if len( chunk_of_approved_contents ) > 0:
                
                chunks_of_approved_contents.append( chunk_of_approved_contents )
                
            
            return chunks_of_approved_contents
            
        
        def do_it( controller, service, petition_service_key, approved_contents, denied_contents, petition ):
            
            try:
                
                num_done = 0
                num_to_do = len( approved_contents )
                
                if len( denied_contents ) > 0:
                    
                    num_to_do += 1
                    
                
                if num_to_do > 1:
                    
                    job_key = ClientThreading.JobKey( cancellable = True )
                    
                    job_key.SetVariable( 'popup_title', 'committing petitions' )
                    
                    HG.client_controller.pub( 'message', job_key )
                    
                else:
                    
                    job_key = None
                    
                
                chunks_of_approved_contents = break_approved_contents_into_chunks( approved_contents )
                
                num_approved_to_do = len( chunks_of_approved_contents )
                
                for chunk_of_approved_contents in chunks_of_approved_contents:
                    
                    if job_key is not None:
                        
                        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                        
                        if should_quit:
                            
                            return
                            
                        
                        job_key.SetVariable( 'popup_gauge_1', ( num_done, num_approved_to_do ) )
                        
                    
                    ( update, content_updates ) = petition.GetApproval( chunk_of_approved_contents )
                    
                    service.Request( HC.POST, 'update', { 'client_to_server_update' : update } )
                    
                    controller.WriteSynchronous( 'content_updates', { petition_service_key : content_updates } )
                    
                    num_done += 1
                    
                
                if len( denied_contents ) > 0:
                    
                    if job_key is not None:
                        
                        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                        
                        if should_quit:
                            
                            return
                            
                        
                    
                    update = petition.GetDenial( denied_contents )
                    
                    service.Request( HC.POST, 'update', { 'client_to_server_update' : update } )
                    
                
            finally:
                
                if job_key is not None:
                    
                    job_key.Delete()
                    
                
                def wx_fetch():
                    
                    if not self:
                        
                        return
                        
                    
                    self._FetchNumPetitions()
                    
                
                wx.CallAfter( wx_fetch )
                
            
        
        approved_contents = []
        denied_contents = []
        
        for index in range( self._contents.GetCount() ):
            
            content = self._contents.GetClientData( index )
            
            if self._contents.IsChecked( index ):
                
                approved_contents.append( content )
                
            else:
                
                denied_contents.append( content )
                
            
        
        HG.client_controller.CallToThread( do_it, self._controller, self._service, self._petition_service_key, approved_contents, denied_contents, self._current_petition )
        
        self._current_petition = None
        
        self._DrawCurrentPetition()
        
    
    def EventModifyPetitioner( self, event ):
        
        wx.MessageBox( 'modify users does not work yet!' )
        
        with ClientGUIDialogs.DialogModifyAccounts( self, self._petition_service_key, ( self._current_petition.GetPetitionerAccount(), ) ) as dlg:
            
            dlg.ShowModal()
            
        
    
    def RefreshQuery( self, page_key ):
        
        if page_key == self._page_key: self._DrawCurrentPetition()
        
    
    def Start( self ):
        
        wx.CallAfter( self._FetchNumPetitions )
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_PETITIONS ] = ManagementPanelPetitions

class ManagementPanelQuery( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        file_search_context = self._management_controller.GetVariable( 'file_search_context' )
        
        self._search_enabled = self._management_controller.GetVariable( 'search_enabled' )
        
        self._query_job_key = ClientThreading.JobKey( cancellable = True )
        
        self._query_job_key.Finish()
        
        initial_predicates = file_search_context.GetPredicates()
        
        if self._search_enabled:
            
            self._search_panel = ClientGUICommon.StaticBox( self, 'search' )
            
            self._current_predicates_box = ClientGUIListBoxes.ListBoxTagsActiveSearchPredicates( self._search_panel, self._page_key, initial_predicates )
            
            synchronised = self._management_controller.GetVariable( 'synchronised' )
            
            self._searchbox = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._search_panel, self._page_key, file_search_context, media_callable = self._page.GetMedia, synchronised = synchronised )
            
            self._cancel_search_button = ClientGUICommon.BetterBitmapButton( self._search_panel, CC.GlobalBMPs.stop, self._CancelSearch )
            
            self._cancel_search_button.Hide()
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( self._searchbox, CC.FLAGS_EXPAND_BOTH_WAYS )
            hbox.Add( self._cancel_search_button, CC.FLAGS_VCENTER )
            
            self._search_panel.Add( self._current_predicates_box, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._search_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        vbox = ClientGUICommon.BetterBoxSizer( wx.VERTICAL )
        
        vbox.Add( self._sort_by, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._collect_by, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        if self._search_enabled:
            
            vbox.Add( self._search_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.SetSizer( vbox )
        
        self._controller.sub( self, 'AddMediaResultsFromQuery', 'add_media_results_from_query' )
        self._controller.sub( self, 'SearchImmediately', 'notify_search_immediately' )
        self._controller.sub( self, 'RefreshQuery', 'refresh_query' )
        self._controller.sub( self, 'ChangeFileServicePubsub', 'change_file_service' )
        
    
    def _CancelSearch( self ):
        
        self._query_job_key.Cancel()
        
        self._UpdateCancelButton()
        
    
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
        
        sizer.Add( tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _RefreshQuery( self ):
        
        self._controller.ResetIdleTimer()
        
        self._query_job_key.Cancel()
        
        if self._management_controller.GetVariable( 'search_enabled' ):
            
            if self._management_controller.GetVariable( 'synchronised' ):
                
                file_search_context = self._searchbox.GetFileSearchContext()
                
                current_predicates = self._current_predicates_box.GetPredicates()
                
                file_search_context.SetPredicates( current_predicates )
                
                self._management_controller.SetVariable( 'file_search_context', file_search_context )
                
                file_service_key = file_search_context.GetFileServiceKey()
                
                if len( current_predicates ) > 0:
                    
                    self._query_job_key = ClientThreading.JobKey()
                    
                    self._controller.CallToThread( self.THREADDoQuery, self._controller, self._page_key, self._query_job_key, file_search_context )
                    
                    panel = ClientGUIMedia.MediaPanelLoading( self._page, self._page_key, file_service_key )
                    
                else:
                    
                    panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, file_service_key, [] )
                    
                
                self._page.SwapMediaPanel( panel )
                
            
        else:
            
            self._sort_by.BroadcastSort()
            
        
    
    def _UpdateCancelButton( self ):
        
        if self._search_enabled:
            
            do_layout = False
            
            if self._query_job_key.IsDone():
                
                if self._cancel_search_button.IsShown():
                    
                    self._cancel_search_button.Hide()
                    
                    do_layout = True
                    
                
            else:
                
                # don't show it immediately to save on flickeriness on short queries
                
                WAIT_PERIOD = 3.0
                
                can_show = HydrusData.TimeHasPassedFloat( self._query_job_key.GetCreationTime() + WAIT_PERIOD )
                
                if can_show and not self._cancel_search_button.IsShown():
                    
                    self._cancel_search_button.Show()
                    
                    do_layout = True
                    
                
            
            if do_layout:
                
                self.Layout()
                
                self._searchbox.ForceSizeCalcNow()
                
            
        
    
    def AddMediaResultsFromQuery( self, query_job_key, media_results ):
        
        if query_job_key == self._query_job_key:
            
            self._controller.pub( 'add_media_results', self._page_key, media_results, append = False )
            
        
    
    def ChangeFileServicePubsub( self, page_key, service_key ):
        
        if page_key == self._page_key:
            
            self._management_controller.SetKey( 'file_service', service_key )
            
        
    
    def CleanBeforeClose( self ):
        
        ManagementPanel.CleanBeforeClose( self )
        
        if self._search_enabled:
            
            self._searchbox.CancelCurrentResultsFetchJob()
            
        
        self._query_job_key.Cancel()
        
    
    def CleanBeforeDestroy( self ):
        
        ManagementPanel.CleanBeforeDestroy( self )
        
        if self._search_enabled:
            
            self._searchbox.CancelCurrentResultsFetchJob()
            
        
        self._query_job_key.Cancel()
        
    
    def GetPredicates( self ):
        
        if self._search_enabled:
            
            return self._current_predicates_box.GetPredicates()
            
        else:
            
            return []
            
        
    
    def RefreshQuery( self, page_key ):
        
        if page_key == self._page_key:
            
            self._RefreshQuery()
            
        
    
    def SearchImmediately( self, page_key, value ):
        
        if page_key == self._page_key:
            
            self._management_controller.SetVariable( 'synchronised', value )
            
            self._RefreshQuery()
            
        
    
    def SetSearchFocus( self ):
        
        if self._search_enabled:
            
            wx.CallAfter( self._searchbox.SetFocus )
            
        
    
    def ShowFinishedQuery( self, query_job_key, media_results ):
        
        if query_job_key == self._query_job_key:
            
            file_service_key = self._management_controller.GetKey( 'file_service' )
            
            panel = ClientGUIMedia.MediaPanelThumbnails( self._page, self._page_key, file_service_key, media_results )
            
            panel.Collect( self._page_key, self._collect_by.GetChoice() )
            
            panel.Sort( self._page_key, self._sort_by.GetSort() )
            
            self._page.SwapMediaPanel( panel )
            
        
    
    def Start( self ):
        
        file_search_context = self._management_controller.GetVariable( 'file_search_context' )
        
        initial_predicates = file_search_context.GetPredicates()
        
        if len( initial_predicates ) > 0 and not file_search_context.IsComplete():
            
            wx.CallAfter( self._RefreshQuery )
            
        
    
    def THREADDoQuery( self, controller, page_key, query_job_key, search_context ):
        
        def wx_code():
            
            query_job_key.Finish()
            
            if not self:
                
                return
                
            
            self.ShowFinishedQuery( query_job_key, media_results )
            
        
        QUERY_CHUNK_SIZE = 256
        
        HG.client_controller.file_viewing_stats_manager.Flush()
        
        query_hash_ids = controller.Read( 'file_query_ids', search_context, job_key = query_job_key )
        
        if query_job_key.IsCancelled():
            
            return
            
        
        media_results = []
        
        for sub_query_hash_ids in HydrusData.SplitListIntoChunks( query_hash_ids, QUERY_CHUNK_SIZE ):
            
            if query_job_key.IsCancelled():
                
                return
                
            
            more_media_results = controller.Read( 'media_results_from_ids', sub_query_hash_ids )
            
            media_results.extend( more_media_results )
            
            controller.pub( 'set_num_query_results', page_key, len( media_results ), len( query_hash_ids ) )
            
            controller.WaitUntilViewFree()
            
        
        search_context.SetComplete()
        
        wx.CallAfter( wx_code )
        
    
    def REPEATINGPageUpdate( self ):
        
        self._UpdateCancelButton()
        
    
management_panel_types_to_classes[ MANAGEMENT_TYPE_QUERY ] = ManagementPanelQuery
