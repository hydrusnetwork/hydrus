import collections
import hashlib
import os
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client import ClientSearch
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvas
from hydrus.client.gui.pages import ClientGUIManagement
from hydrus.client.gui.pages import ClientGUIResults
from hydrus.client.gui.pages import ClientGUISession
from hydrus.client.gui.pages import ClientGUISessionLegacy # to get serialisable data types loaded

def ConvertNumHashesToWeight( num_hashes: int ) -> int:
    
    return num_hashes
    
def ConvertNumHashesAndSeedsToWeight( num_hashes: int, num_seeds: int ) -> int:
    
    return ConvertNumHashesToWeight( num_hashes ) + ConvertNumSeedsToWeight( num_seeds )
    
def ConvertNumSeedsToWeight( num_seeds: int ) -> int:
    
    return num_seeds * 20
    
class DialogPageChooser( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, controller ):
        
        ClientGUIDialogs.Dialog.__init__( self, parent, 'new page', position = 'center' )
        
        self._controller = controller
        
        self._action_picked = False
        
        self._result = None
        
        # spawn and add to layout in this order, so focus precipitates from the graphical top
        
        self._button_7 = QW.QPushButton( '', self )
        self._button_8 = QW.QPushButton( '', self )
        self._button_9 = QW.QPushButton( '', self )
        self._button_4 = QW.QPushButton( '', self )
        self._button_5 = QW.QPushButton( '', self )
        self._button_6 = QW.QPushButton( '', self )
        self._button_1 = QW.QPushButton( '', self )
        self._button_2 = QW.QPushButton( '', self )
        self._button_3 = QW.QPushButton( '', self )
        
        size_policy = self._button_1.sizePolicy()
        size_policy.setVerticalPolicy( QW.QSizePolicy.Expanding )
        size_policy.setRetainSizeWhenHidden( True )
        
        self._button_7.setSizePolicy( size_policy )
        self._button_8.setSizePolicy( size_policy )
        self._button_9.setSizePolicy( size_policy )
        self._button_4.setSizePolicy( size_policy )
        self._button_5.setSizePolicy( size_policy )
        self._button_6.setSizePolicy( size_policy )
        self._button_1.setSizePolicy( size_policy )
        self._button_2.setSizePolicy( size_policy )
        self._button_3.setSizePolicy( size_policy )
        
        self._button_7.setObjectName('7')
        self._button_8.setObjectName('8')
        self._button_9.setObjectName('9')
        self._button_4.setObjectName('4')
        self._button_5.setObjectName('5')
        self._button_6.setObjectName('6')
        self._button_1.setObjectName('1')
        self._button_2.setObjectName('2')
        self._button_3.setObjectName('3')
        
        # this ensures these buttons won't get focus and receive key events, letting dialog handle arrow/number shortcuts
        self._button_7.setFocusPolicy( QC.Qt.NoFocus )
        self._button_8.setFocusPolicy( QC.Qt.NoFocus )
        self._button_9.setFocusPolicy( QC.Qt.NoFocus )
        self._button_4.setFocusPolicy( QC.Qt.NoFocus )
        self._button_5.setFocusPolicy( QC.Qt.NoFocus )
        self._button_6.setFocusPolicy( QC.Qt.NoFocus )
        self._button_1.setFocusPolicy( QC.Qt.NoFocus )
        self._button_2.setFocusPolicy( QC.Qt.NoFocus )
        self._button_3.setFocusPolicy( QC.Qt.NoFocus )
        
        gridbox = QP.GridLayout( cols = 3 )
        
        QP.AddToLayout( gridbox, self._button_7 )
        QP.AddToLayout( gridbox, self._button_8 )
        QP.AddToLayout( gridbox, self._button_9 )
        QP.AddToLayout( gridbox, self._button_4 )
        QP.AddToLayout( gridbox, self._button_5 )
        QP.AddToLayout( gridbox, self._button_6 )
        QP.AddToLayout( gridbox, self._button_1 )
        QP.AddToLayout( gridbox, self._button_2 )
        QP.AddToLayout( gridbox, self._button_3 )
        
        self.setLayout( gridbox )
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self, ( 64, 14 ) )
        
        self.setMinimumWidth( width )
        self.setMinimumHeight( height )
        
        self._services = HG.client_controller.services_manager.GetServices()
        
        self._petition_service_keys = [ service.GetServiceKey() for service in self._services if service.GetServiceType() in HC.REPOSITORIES and True in ( service.HasPermission( content_type, HC.PERMISSION_ACTION_MODERATE ) for content_type in HC.SERVICE_TYPES_TO_CONTENT_TYPES[ service.GetServiceType() ] ) ]
        
        self._InitButtons( 'home' )
        
        self._button_7.clicked.connect( lambda: self._HitButton( 7 ) )
        self._button_8.clicked.connect( lambda: self._HitButton( 8 ) )
        self._button_9.clicked.connect( lambda: self._HitButton( 9 ) )
        self._button_4.clicked.connect( lambda: self._HitButton( 4 ) )
        self._button_5.clicked.connect( lambda: self._HitButton( 5 ) )
        self._button_6.clicked.connect( lambda: self._HitButton( 6 ) )
        self._button_1.clicked.connect( lambda: self._HitButton( 1 ) )
        self._button_2.clicked.connect( lambda: self._HitButton( 2 ) )
        self._button_3.clicked.connect( lambda: self._HitButton( 3 ) )
        
    
    def _AddEntry( self, button, entry ):
        
        button_id = int( button.objectName() )
        
        self._command_dict[ button_id ] = entry
        
        ( entry_type, obj ) = entry
        
        if entry_type == 'menu':
            
            button.setText( obj )
            
        elif entry_type == 'page_duplicate_filter':
            
            button.setText( 'duplicates processing' )
            
        elif entry_type == 'pages_notebook':
            
            button.setText( 'page of pages' )
            
        elif entry_type in ( 'page_query', 'page_petitions' ):
            
            name = HG.client_controller.services_manager.GetService( obj ).GetName()
            
            button.setText( name )
            
        elif entry_type == 'page_import_gallery':
            
            button.setText( 'gallery' )
            
        elif entry_type == 'page_import_simple_downloader':
            
            button.setText( 'simple downloader' )
            
        elif entry_type == 'page_import_watcher':
            
            button.setText( 'watcher' )
            
        elif entry_type == 'page_import_urls':
            
            button.setText( 'urls' )
            
        
        button.show()
        
    
    def _HitButton( self, button_id ):
        
        if button_id in self._command_dict:
            
            ( entry_type, obj ) = self._command_dict[ button_id ]
            
            if entry_type == 'menu':
                
                self._InitButtons( obj )
                
            else:
                
                if entry_type == 'page_query': 
                    
                    file_service_key = obj
                    
                    page_name = 'files'
                    
                    search_enabled = True
                    
                    new_options = self._controller.new_options
                    
                    tag_service_key = new_options.GetKey( 'default_tag_service_search_page' )
                    
                    if not self._controller.services_manager.ServiceExists( tag_service_key ):
                        
                        tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
                        
                    
                    location_context = ClientLocation.LocationContext.STATICCreateSimple( file_service_key )
                    
                    tag_search_context = ClientSearch.TagSearchContext( service_key = tag_service_key )
                    
                    file_search_context = ClientSearch.FileSearchContext( location_context = location_context, tag_search_context = tag_search_context )
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerQuery( page_name, file_search_context, search_enabled ) )
                    
                elif entry_type == 'page_duplicate_filter':
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerDuplicateFilter() )
                    
                elif entry_type == 'pages_notebook':
                    
                    self._result = ( 'pages', None )
                    
                elif entry_type == 'page_import_gallery':
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerImportGallery() )
                    
                elif entry_type == 'page_import_simple_downloader':
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerImportSimpleDownloader() )
                    
                elif entry_type == 'page_import_watcher':
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerImportMultipleWatcher() )
                    
                elif entry_type == 'page_import_urls':
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerImportURLs() )
                    
                elif entry_type == 'page_petitions':
                    
                    petition_service_key = obj
                    
                    self._result = ( 'page', ClientGUIManagement.CreateManagementControllerPetitions( petition_service_key ) )
                    
                
                self._action_picked = True
                
                self.done( QW.QDialog.Accepted )
                
            
        
    
    def _InitButtons( self, menu_keyword ):
        
        self._command_dict = {}
        
        entries = []
        
        if menu_keyword == 'home':
            
            entries.append( ( 'menu', 'files' ) )
            entries.append( ( 'menu', 'download' ) )
            
            if len( self._petition_service_keys ) > 0:
                
                entries.append( ( 'menu', 'petitions' ) )
                
            
            entries.append( ( 'menu', 'special' ) )
            
        elif menu_keyword == 'files':
            
            entries.append( ( 'page_query', CC.LOCAL_FILE_SERVICE_KEY ) )
            entries.append( ( 'page_query', CC.TRASH_SERVICE_KEY ) )
            
            if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                
                entries.append( ( 'page_query', CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
                
            
            for service in self._services:
                
                if service.GetServiceType() == HC.FILE_REPOSITORY:
                    
                    entries.append( ( 'page_query', service.GetServiceKey() ) )
                    
                
            
        elif menu_keyword == 'download':
            
            entries.append( ( 'page_import_urls', None ) )
            entries.append( ( 'page_import_watcher', None ) )
            entries.append( ( 'page_import_gallery', None ) )
            entries.append( ( 'page_import_simple_downloader', None ) )
            
        elif menu_keyword == 'petitions':
            
            entries = [ ( 'page_petitions', service_key ) for service_key in self._petition_service_keys ]
            
        elif menu_keyword == 'special':
            
            entries.append( ( 'pages_notebook', None ) )
            entries.append( ( 'page_duplicate_filter', None ) )
            
        
        if len( entries ) <= 4:
            
            self._button_1.setVisible( False )
            self._button_3.setVisible( False )
            self._button_5.setVisible( False )
            self._button_7.setVisible( False )
            self._button_9.setVisible( False )
            
            potential_buttons = [ self._button_8, self._button_4, self._button_6, self._button_2 ]
            
        elif len( entries ) <= 9:
            
            potential_buttons = [ self._button_7, self._button_8, self._button_9, self._button_4, self._button_5, self._button_6, self._button_1, self._button_2, self._button_3 ]
            
        else:
            
            # sort out a multi-page solution? maybe only if this becomes a big thing; the person can always select from the menus, yeah?
            
            potential_buttons = [ self._button_7, self._button_8, self._button_9, self._button_4, self._button_5, self._button_6, self._button_1, self._button_2, self._button_3 ]
            entries = entries[:9]
            
        
        for entry in entries:
            
            self._AddEntry( potential_buttons.pop( 0 ), entry )
            
        
        unused_buttons = potential_buttons
        
        for button in unused_buttons:
            
            button.setVisible( False )
            
        
    
    def event( self, event ):
        
        if event.type() == QC.QEvent.WindowDeactivate and not self._action_picked:
            
            self.done( QW.QDialog.Rejected )
            
            return True
            
        else:
            
            return ClientGUIDialogs.Dialog.event( self, event )
            
        
    
    def keyPressEvent( self, event ):
        
        button_id = None
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key == QC.Qt.Key_Up: button_id = 8
        elif key == QC.Qt.Key_Left: button_id = 4
        elif key == QC.Qt.Key_Right: button_id = 6
        elif key == QC.Qt.Key_Down: button_id = 2
        elif key == QC.Qt.Key_1 and modifier == QC.Qt.KeypadModifier: button_id = 1
        elif key == QC.Qt.Key_2 and modifier == QC.Qt.KeypadModifier: button_id = 2
        elif key == QC.Qt.Key_3 and modifier == QC.Qt.KeypadModifier: button_id = 3
        elif key == QC.Qt.Key_4 and modifier == QC.Qt.KeypadModifier: button_id = 4
        elif key == QC.Qt.Key_5 and modifier == QC.Qt.KeypadModifier: button_id = 5
        elif key == QC.Qt.Key_6 and modifier == QC.Qt.KeypadModifier: button_id = 6
        elif key == QC.Qt.Key_7 and modifier == QC.Qt.KeypadModifier: button_id = 7
        elif key == QC.Qt.Key_8 and modifier == QC.Qt.KeypadModifier: button_id = 8
        elif key == QC.Qt.Key_9 and modifier == QC.Qt.KeypadModifier: button_id = 9
        elif key in ( QC.Qt.Key_Enter, QC.Qt.Key_Return ):
            
            # get the 'first', scanning from top-left
            
            for possible_id in ( 7, 8, 9, 4, 5, 6, 1, 2, 3 ):
                
                if possible_id in self._command_dict:
                    
                    button_id = possible_id
                    
                    break
                    
                
            
        elif key == QC.Qt.Key_Escape:
            
            self.done( QW.QDialog.Rejected )
            
            return
            
        else:
            
            event.ignore()
            
        
        if button_id is not None:
            
            self._HitButton( button_id )
            
        
    
    def GetValue( self ):
        
        return self._result
        
    
class Page( QW.QSplitter ):
    
    def __init__( self, parent, controller, management_controller, initial_hashes ):
        
        QW.QSplitter.__init__( self, parent )
        
        self._parent_notebook = parent
        
        self._controller = controller
        
        self._page_key = self._controller.AcquirePageKey()
        
        self._management_controller = management_controller
        
        self._initial_hashes = initial_hashes
        
        self._management_controller.SetKey( 'page', self._page_key )
        
        self._initialised = len( initial_hashes ) == 0
        self._pre_initialisation_media_results = []
        
        self._pretty_status = ''
        
        self._search_preview_split = QW.QSplitter( self )
        
        self._done_split_setups = False
        
        self._management_panel = ClientGUIManagement.CreateManagementPanel( self._search_preview_split, self, self._controller, self._management_controller )
        
        self._preview_panel = QW.QFrame( self._search_preview_split )
        self._preview_panel.setFrameStyle( QW.QFrame.Panel | QW.QFrame.Sunken )
        self._preview_panel.setLineWidth( 2 )
        
        self._preview_canvas = ClientGUICanvas.CanvasPanel( self._preview_panel, self._page_key, self._management_controller.GetVariable( 'location_context' ) )
        
        self._management_panel.locationChanged.connect( self._preview_canvas.SetLocationContext )
        
        self._media_panel = self._management_panel.GetDefaultEmptyMediaPanel()
        
        vbox = QP.VBoxLayout( margin = 0 )
        
        QP.AddToLayout( vbox, self._preview_canvas, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._preview_panel.setLayout( vbox )
        
        self.widget( 0 ).setMinimumWidth( 120 )
        self.widget( 1 ).setMinimumWidth( 120 )
        self.setStretchFactor( 0, 0 )
        self.setStretchFactor( 1, 1 )
        
        self._handle_event_filter = QP.WidgetEventFilter( self.handle( 1 ) )
        self._handle_event_filter.EVT_LEFT_DCLICK( self.EventUnsplit )
        
        self._search_preview_split.widget( 0 ).setMinimumHeight( 180 )
        self._search_preview_split.widget( 1 ).setMinimumHeight( 180 )
        self._search_preview_split.setStretchFactor( 0, 1 )
        self._search_preview_split.setStretchFactor( 1, 0 )
        
        self._search_preview_split._handle_event_filter = QP.WidgetEventFilter( self._search_preview_split.handle( 1 ) )
        self._search_preview_split._handle_event_filter.EVT_LEFT_DCLICK( self.EventPreviewUnsplit )
        
        self._controller.sub( self, 'SetSplitterPositions', 'set_splitter_positions' )
        
        self._current_session_page_container = None
        self._current_session_page_container_hashes_hash = self._GetCurrentSessionPageHashesHash()
        self._current_session_page_container_timestamp = 0
        
        self._ConnectMediaPanelSignals()
        
    
    def _ConnectMediaPanelSignals( self ):
        
        self._media_panel.refreshQuery.connect( self.RefreshQuery )
        self._media_panel.focusMediaChanged.connect( self._preview_canvas.SetMedia )
        self._media_panel.focusMediaCleared.connect( self._preview_canvas.ClearMedia )
        self._media_panel.statusTextChanged.connect( self._SetPrettyStatus )
        
        self._management_panel.ConnectMediaPanelSignals( self._media_panel )
        
    
    def _GetCurrentSessionPageHashesHash( self ):
        
        hashlist = self.GetHashes()
        
        hashlist_hashable = tuple( hashlist )
        
        return hash( hashlist_hashable )
        
    
    def _SetCurrentPageContainer( self, page_container: ClientGUISession.GUISessionContainerPageSingle ):
        
        self._current_session_page_container = page_container
        self._current_session_page_container_hashes_hash = self._GetCurrentSessionPageHashesHash()
        self._current_session_page_container_timestamp = HydrusData.GetNow()
        
    
    def _SetPrettyStatus( self, status: str ):
        
        self._pretty_status = status
        
        self._controller.gui.SetStatusBarDirty()
        
    
    def _SwapMediaPanel( self, new_panel ):
        
        # if a new media page comes in while its menu is open, we can enter program instability.
        # so let's just put it off.
        
        previous_sizes = self.sizes()
        
        self._preview_canvas.ClearMedia()
        
        self._media_panel.ClearPageKey()
        
        media_collect = self._management_panel.GetMediaCollect()
        
        if media_collect.DoesACollect():
            
            new_panel.Collect( self._page_key, media_collect )
            
            media_sort = self._management_panel.GetMediaSort()
            
            new_panel.Sort( media_sort )
            
        
        self._media_panel.setParent( None )
        
        old_panel = self._media_panel
        
        self.addWidget( new_panel )
        
        self.setSizes( previous_sizes )
        
        self.setStretchFactor( 1, 1 )
        
        self._media_panel = new_panel
        
        self._ConnectMediaPanelSignals()
        
        self._controller.pub( 'refresh_page_name', self._page_key )
        
        def clean_up_old_panel():
            
            if CGC.core().MenuIsOpen():
                
                self._controller.CallLaterQtSafe( self, 0.5, 'menu closed panel swap loop', clean_up_old_panel )
                
                return
                
            
            old_panel.deleteLater()
            
        
        clean_up_old_panel()
        
    
    def AddMediaResults( self, media_results ):
        
        if self._initialised:
            
            self._media_panel.AddMediaResults( self._page_key, media_results )
            
        else:
            
            self._pre_initialisation_media_results.extend( media_results )
            
        
    
    def CheckAbleToClose( self ):
        
        self._management_panel.CheckAbleToClose()
        
    
    def CleanBeforeClose( self ):
        
        self._management_panel.CleanBeforeClose()
        
        self._media_panel.SetFocusedMedia( None )
        
    
    def CleanBeforeDestroy( self ):
        
        self._management_panel.CleanBeforeDestroy()
        
        self._preview_canvas.CleanBeforeDestroy()
        
        self._controller.ReleasePageKey( self._page_key )
        
    
    def EventPreviewUnsplit( self, event ):
        
        QP.Unsplit( self._search_preview_split, self._preview_panel )
        
        self._media_panel.SetFocusedMedia( None )
        
    
    def EventUnsplit( self, event ):
        
        QP.Unsplit( self, self._search_preview_split )
        
        self._media_panel.SetFocusedMedia( None )
        
    
    def GetAPIInfoDict( self, simple ):
        
        d = {}
        
        d[ 'name' ] = self._management_controller.GetPageName()
        d[ 'page_key' ] = self._page_key.hex()
        d[ 'page_type' ] = self._management_controller.GetType()
        
        management_info = self._management_controller.GetAPIInfoDict( simple )
        
        d[ 'management' ] = management_info
        
        media_info = self._media_panel.GetAPIInfoDict( simple )
        
        d[ 'media' ] = media_info
        
        return d
        
    
    def GetHashes( self ):
        
        if self._initialised:
            
            return self._media_panel.GetHashes( ordered = True )
            
        else:
            
            hashes = list( self._initial_hashes )
            hashes.extend( ( media_result.GetHash() for media_result in self._pre_initialisation_media_results ) )
            
            hashes = HydrusData.DedupeList( hashes )
            
            return hashes
            
        
    
    def GetManagementController( self ):
        
        return self._management_controller
        
    
    def GetManagementPanel( self ):
        
        return self._management_panel
        
    
    # used by autocomplete
    def GetMedia( self ):
        
        return self._media_panel.GetSortedMedia()
        
    
    def GetMediaPanel( self ):
        
        return self._media_panel
        
    
    def GetName( self ):
        
        return self._management_controller.GetPageName()
        
    
    def GetNumFileSummary( self ):
        
        if self._initialised:
            
            num_files = self._media_panel.GetNumFiles()
            
        else:
            
            num_files = len( self._initial_hashes )
            
        
        ( num_value, num_range ) = self._management_controller.GetValueRange()
        
        if num_value == num_range:
            
            ( num_value, num_range ) = ( 0, 0 )
            
        
        return ( num_files, ( num_value, num_range ) )
        
    
    def GetPageKey( self ):
        
        return self._page_key
        
    
    def GetPageKeys( self ):
        
        return { self._page_key }
        
    
    def GetParentNotebook( self ):
        
        return self._parent_notebook
        
    
    def GetSerialisablePage( self, only_changed_page_data, about_to_save ):
        
        if only_changed_page_data and not self.IsCurrentSessionPageDirty():
            
            hashes_to_page_data = {}
            
            skipped_unchanged_page_hashes = { self._current_session_page_container.GetPageDataHash() }
            
            return ( self._current_session_page_container, hashes_to_page_data, skipped_unchanged_page_hashes )
            
        
        name = self.GetName()
        
        page_data = ClientGUISession.GUISessionPageData( self._management_controller, self.GetHashes() )
        
        # this is the only place this is generated. this will be its key/name/id from now on
        # we won't regen the hash for identifier since it could change due to object updates etc...
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( name, page_data_hash )
        
        hashes_to_page_data = { page_data_hash : page_data }
        
        if about_to_save:
            
            self._SetCurrentPageContainer( page_container )
            
        
        skipped_unchanged_page_hashes = set()
        
        return ( page_container, hashes_to_page_data, skipped_unchanged_page_hashes )
        
    
    def GetSessionAPIInfoDict( self, is_selected = False ):
        
        root = {}
        
        root[ 'name' ] = self.GetName()
        root[ 'page_key' ] = self._page_key.hex()
        root[ 'page_type' ] = self._management_controller.GetType()
        root[ 'focused' ] = is_selected
        
        return root
        
    
    def GetPrettyStatus( self ):
        
        return self._pretty_status
        
    
    def GetSashPositions( self ):
        
        hpos = HC.options[ 'hpos' ]
        
        sizes = self.sizes()
        
        if len( sizes ) > 1:
            
            if sizes[0] != 0:
                
                hpos = sizes[0]
                
            
        
        vpos = HC.options[ 'vpos' ]
        
        sizes = self._search_preview_split.sizes()
        
        if len( sizes ) > 1:
            
            if sizes[1] != 0:
                
                vpos = - sizes[1]
                
            
        
        return ( hpos, vpos )
        
    
    def GetTotalNumHashesAndSeeds( self ):
        
        num_hashes = len( self.GetHashes() )
        num_seeds = self._management_controller.GetNumSeeds()
        
        return ( num_hashes, num_seeds )
        
    
    def GetTotalWeight( self ) -> int:
        
        ( num_hashes, num_seeds ) = self.GetTotalNumHashesAndSeeds()
        
        return ConvertNumHashesAndSeedsToWeight( num_hashes, num_seeds )
        
    
    def IsCurrentSessionPageDirty( self ):
        
        if self._current_session_page_container is None:
            
            return True
            
        else:
            
            if self._GetCurrentSessionPageHashesHash() != self._current_session_page_container_hashes_hash:
                
                return True
                
            
            return self._management_controller.HasSerialisableChangesSince( self._current_session_page_container_timestamp )
            
        
    
    def IsGalleryDownloaderPage( self ):
        
        return self._management_controller.GetType() == ClientGUIManagement.MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY
        
    
    def IsImporter( self ):
        
        return self._management_controller.IsImporter()
        
    
    def IsInitialised( self ):
        
        return self._initialised
        
    
    def IsMultipleWatcherPage( self ):
        
        return self._management_controller.GetType() == ClientGUIManagement.MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER
        
    
    def IsURLImportPage( self ):
        
        return self._management_controller.GetType() == ClientGUIManagement.MANAGEMENT_TYPE_IMPORT_URLS
        
    
    def PageHidden( self ):
        
        self._management_panel.PageHidden()
        self._media_panel.PageHidden()
        self._preview_canvas.PageHidden()
        
    
    def PageShown( self ):
        
        if self.isVisible() and not self._done_split_setups:
            
            self.SetSplitterPositions()
            
            self._done_split_setups = True
            
        
        self._management_panel.PageShown()
        self._media_panel.PageShown()
        self._preview_canvas.PageShown()
        
    
    def RefreshQuery( self ):
        
        if self._initialised:
            
            self._management_panel.RefreshQuery()
            
        
    
    def SetMediaFocus( self ):
        
        self._media_panel.setFocus( QC.Qt.OtherFocusReason )
        
    
    def SetName( self, name ):
        
        return self._management_controller.SetPageName( name )
        
    
    def SetPageContainerClean( self, page_container: ClientGUISession.GUISessionContainerPageSingle ):
        
        self._SetCurrentPageContainer( page_container )
        
    
    def SetPrettyStatus( self, page_key, status ):
        
        if page_key == self._page_key:
            
            if self._initialised:
                
                self._SetPrettyStatus( status )
                
            
        
    
    def SetSearchFocus( self ):
        
        self._management_panel.SetSearchFocus()
        
    
    def SetSplitterPositions( self, hpos = None, vpos = None ):
        
        if hpos is None:
            
            hpos = HC.options[ 'hpos' ]
            
        
        if vpos is None:
            
            vpos = HC.options[ 'vpos' ]
            
        
        QP.SplitHorizontally( self._search_preview_split, self._management_panel, self._preview_panel, vpos )
        
        QP.SplitVertically( self, self._search_preview_split, self._media_panel, hpos )
        
        if HC.options[ 'hide_preview' ]:
            
            QP.CallAfter( QP.Unsplit, self._search_preview_split, self._preview_panel )
            
        
    
    def ShowHideSplit( self ):
        
        if QP.SplitterVisibleCount( self ) > 1:
            
            QP.Unsplit( self, self._search_preview_split )
            
            self._media_panel.SetFocusedMedia( None )
            
        else:
            
            self.SetSplitterPositions()
            
        
    
    def _StartInitialMediaResultsLoad( self ):
        
        def qt_code_status( status ):
            
            if not self._initialised:
                
                self._SetPrettyStatus( status )
                
            
        
        controller = self._controller
        initial_hashes = HydrusData.DedupeList( self._initial_hashes )
        
        def work_callable():
            
            initial_media_results = []
            
            for group_of_initial_hashes in HydrusData.SplitListIntoChunks( initial_hashes, 256 ):
                
                more_media_results = controller.Read( 'media_results', group_of_initial_hashes )
                
                initial_media_results.extend( more_media_results )
                
                status = 'Loading initial files\u2026 ' + HydrusData.ConvertValueRangeToPrettyString( len( initial_media_results ), len( initial_hashes ) )
                
                controller.CallAfterQtSafe( self, 'setting status bar loading string', qt_code_status, status )
                
                QP.CallAfter( qt_code_status, status )
                
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in initial_media_results }
            
            sorted_initial_media_results = [ hashes_to_media_results[ hash ] for hash in initial_hashes if hash in hashes_to_media_results ]
            
            return sorted_initial_media_results
            
        
        def publish_callable( media_results ):
            
            self._SetPrettyStatus( '' )
            
            location_context = self._management_controller.GetVariable( 'location_context' )
            
            media_panel = ClientGUIResults.MediaPanelThumbnails( self, self._page_key, location_context, media_results )
            
            self._SwapMediaPanel( media_panel )
            
            if len( self._pre_initialisation_media_results ) > 0:
                
                media_panel.AddMediaResults( self._page_key, self._pre_initialisation_media_results )
                
                self._pre_initialisation_media_results = []
                
            
            # do this 'after' so on a long session setup, it all boots once session loaded
            HG.client_controller.CallAfterQtSafe( self, 'starting page controller', self._management_panel.Start )
            
            self._initialised = True
            self._initial_hashes = []
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def Start( self ):
        
        if self._initial_hashes is not None and len( self._initial_hashes ) > 0:
            
            self._StartInitialMediaResultsLoad()
            
        else:
            
            # do this 'after' so on a long session setup, it all boots once session loaded
            HG.client_controller.CallAfterQtSafe( self, 'starting page controller', self._management_panel.Start )
            
            self._initialised = True
            
        
    
    def SwapMediaPanel( self, new_panel ):
        
        self._SwapMediaPanel( new_panel )
        
    
    def TestAbleToClose( self ):
        
        try:
            
            self._management_panel.CheckAbleToClose()
            
        except HydrusExceptions.VetoException as e:
            
            reason = str( e )
            
            message = '{} Are you sure you want to close it?'.format( str( e ) )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result == QW.QDialog.Rejected:
                
                raise HydrusExceptions.VetoException()
                
            
        
    
    def REPEATINGPageUpdate( self ):
        
        self._management_panel.REPEATINGPageUpdate()
        
    
directions_for_notebook_tabs = {}

directions_for_notebook_tabs[ CC.DIRECTION_UP ] = QW.QTabWidget.North
directions_for_notebook_tabs[ CC.DIRECTION_LEFT ] = QW.QTabWidget.West
directions_for_notebook_tabs[ CC.DIRECTION_RIGHT ] = QW.QTabWidget.East
directions_for_notebook_tabs[ CC.DIRECTION_DOWN ] = QW.QTabWidget.South

class PagesNotebook( QP.TabWidgetWithDnD ):
    
    freshSessionLoaded = QC.Signal( ClientGUISession.GUISessionContainer )
    
    def __init__( self, parent, controller, name ):
        
        QP.TabWidgetWithDnD.__init__( self, parent )
        
        self._parent_notebook = parent
        
        direction = controller.new_options.GetInteger( 'notebook_tab_alignment' )
        
        self.setTabPosition( directions_for_notebook_tabs[ direction ] )
        
        self._controller = controller
        
        self._page_key = self._controller.AcquirePageKey()
        
        self._name = name
        
        self._next_new_page_index = None
        
        self._potential_drag_page = None
        
        self._closed_pages = []
        
        self._controller.sub( self, 'RefreshPageName', 'refresh_page_name' )
        self._controller.sub( self, 'NotifyPageUnclosed', 'notify_page_unclosed' )
        self._controller.sub( self, '_UpdateOptions', 'notify_new_options' )
        
        self.currentChanged.connect( self.pageJustChanged )
        self.pageDragAndDropped.connect( self._RefreshPageNamesAfterDnD )
        
        self.tabBar().tabDoubleLeftClicked.connect( self._RenamePage )
        self.tabBar().tabMiddleClicked.connect( self._ClosePage )
        
        self.tabBar().tabSpaceDoubleLeftClicked.connect( self.ChooseNewPage )
        self.tabBar().tabSpaceDoubleMiddleClicked.connect( self.ChooseNewPage )
        
        self._previous_page_index = -1
        
        self._UpdateOptions()
        
        self.tabBar().installEventFilter( self )
        self.installEventFilter( self )
        
    
    def _RefreshPageNamesAfterDnD( self, page_widget, source_widget ):
        
        if hasattr( page_widget, 'GetPageKey' ):
            
            self._controller.pub( 'refresh_page_name', page_widget.GetPageKey() )
            
        
        source_notebook = source_widget.parentWidget()
        
        if hasattr( source_notebook, 'GetPageKey' ):
            
            self._controller.pub( 'refresh_page_name', source_notebook.GetPageKey() )
            
        
    
    def _UpdateOptions( self ):
        
        if HG.client_controller.new_options.GetBoolean( 'elide_page_tab_names' ):
            
            self.tabBar().setElideMode( QC.Qt.ElideMiddle )
            
        else:
            
            self.tabBar().setElideMode( QC.Qt.ElideNone )
            
        
        direction = HG.client_controller.new_options.GetInteger( 'notebook_tab_alignment' )
        
        self.setTabPosition( directions_for_notebook_tabs[ direction ] )
        
    
    def _UpdatePreviousPageIndex( self ):
        
        self._previous_page_index = self.currentIndex()
        
    
    def _ChooseNewPage( self, insertion_index = None ):
        
        self._next_new_page_index = insertion_index
        
        with DialogPageChooser( self, self._controller ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                ( page_type, page_data ) = dlg.GetValue()
                
                if page_type == 'pages':
                    
                    self.NewPagesNotebook()
                    
                elif page_type == 'page':
                    
                    management_controller = page_data
                    
                    self.NewPage( management_controller )
                    
                
            
        
    
    def _CloseAllPages( self, polite = True, delete_pages = False ):
        
        closees = [ index for index in range( self.count() ) ]
        
        self._ClosePages( closees, polite, delete_pages = delete_pages )
        
    
    def _CloseLeftPages( self, from_index ):
        
        message = 'Close all pages to the left?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            closees = [ index for index in range( self.count() ) if index < from_index ]
            
            self._ClosePages( closees )
            
        
    
    def _CloseOtherPages( self, except_index ):
        
        message = 'Close all other pages?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            closees = [ index for index in range( self.count() ) if index != except_index ]
            
            self._ClosePages( closees )
            
        
    
    def _ClosePage( self, index, polite = True, delete_page = False ):
        
        self._controller.ResetIdleTimer()
        self._controller.ResetPageChangeTimer()
        
        if index == -1 or index > self.count() - 1:
            
            return False
            
        
        page = self.widget( index )
        
        if polite:
            
            try:
                
                page.TestAbleToClose()
                
            except HydrusExceptions.VetoException:
                
                return False
                
            
        
        page.CleanBeforeClose()
        
        page_key = page.GetPageKey()
        
        self._closed_pages.append( ( index, page_key ) )
        
        self.removeTab( index )
        
        self._UpdatePreviousPageIndex()
        
        self._controller.pub( 'refresh_page_name', self._page_key )
        
        if delete_page:
            
            self._controller.pub( 'notify_deleted_page', page )
            
        else:
            
            self._controller.pub( 'notify_closed_page', page )
            
        
        return True
        
    
    def _ClosePages( self, indices, polite = True, delete_pages = False ):
        
        indices = list( indices )
        
        indices.sort( reverse = True ) # so we are closing from the end first
        
        for index in indices:
            
            successful = self._ClosePage( index, polite, delete_page = delete_pages )
            
            if not successful:
                
                break
                
            
        
    
    def _CloseRightPages( self, from_index ):
        
        message = 'Close all pages to the right?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            closees = [ index for index in range( self.count() ) if index > from_index ]
            
            self._ClosePages( closees )
            
        
    
    def _DuplicatePage( self, index ):
        
        if index == -1 or index > self.count() - 1:
            
            return False
            
        
        page = self.widget( index )
        
        only_changed_page_data = False
        about_to_save = False
        
        ( container, hashes_to_page_data, skipped_unchanged_page_hashes ) = page.GetSerialisablePage( only_changed_page_data, about_to_save )
        
        top_notebook_container = ClientGUISession.GUISessionContainerPageNotebook( 'dupe top notebook', page_containers = [ container ] )
        
        session = ClientGUISession.GUISessionContainer( 'dupe session', top_notebook_container = top_notebook_container, hashes_to_page_data = hashes_to_page_data )
        
        self.InsertSession( index + 1, session, session_is_clean = False )
        
    
    def _GetDefaultPageInsertionIndex( self ):
        
        new_options = self._controller.new_options
        
        new_page_goes = new_options.GetInteger( 'default_new_page_goes' )
        
        current_index = self.currentIndex()
        
        if current_index == -1:
            
            new_page_goes = CC.NEW_PAGE_GOES_FAR_LEFT
            
        
        if new_page_goes == CC.NEW_PAGE_GOES_FAR_LEFT:
            
            insertion_index = 0
            
        elif new_page_goes == CC.NEW_PAGE_GOES_LEFT_OF_CURRENT:
            
            insertion_index = current_index
            
        elif new_page_goes == CC.NEW_PAGE_GOES_RIGHT_OF_CURRENT:
            
            insertion_index = current_index + 1
            
        elif new_page_goes == CC.NEW_PAGE_GOES_FAR_RIGHT:
            
            insertion_index = self.count()
            
        
        return insertion_index
        
    
    def _GetMediaPages( self, only_my_level ):
        
        results = []
        
        for page in self._GetPages():
            
            if isinstance( page, PagesNotebook ):
                
                if not only_my_level:
                    
                    results.extend( page.GetMediaPages() )
                    
                
            else:
                
                results.append( page )
                
            
        
        return results
        
    
    def _GetIndex( self, page_key ):
        
        for ( page, index ) in ( ( self.widget( index ), index ) for index in range( self.count() ) ):
            
            if page.GetPageKey() == page_key:
                
                return index
                
            
        
        raise HydrusExceptions.DataMissing()
        
    
    def _GetNotebookFromScreenPosition( self, screen_position ) -> "PagesNotebook":
        
        current_page = self.currentWidget()
        
        if current_page is None or not isinstance( current_page, PagesNotebook ):
            
            return self
            
        else:
            
            tab_index = ClientGUIFunctions.NotebookScreenToHitTest( self, screen_position )
            
            if tab_index == -1:
                
                return self
                
            
            on_child_notebook_somewhere = screen_position.y() > current_page.pos().y()
            
            if on_child_notebook_somewhere:
                
                return current_page._GetNotebookFromScreenPosition( screen_position )
                
            
        
        return self
        
    
    def _GetPages( self ):
        
        return [ self.widget( i ) for i in range( self.count() ) ]
        
    
    def _GetPageFromName( self, page_name, only_media_pages = False ):
        
        for page in self._GetPages():
            
            if page.GetName() == page_name:
                
                do_not_do_it = only_media_pages and isinstance( page, PagesNotebook )
                
                if not do_not_do_it:
                    
                    return page
                    
                
            
            if isinstance( page, PagesNotebook ):
                
                result = page._GetPageFromName( page_name, only_media_pages = only_media_pages )
                
                if result is not None:
                    
                    return result
                    
                
            
        
        return None
        
    
    def _MovePage( self, page, dest_notebook, insertion_tab_index, follow_dropped_page = False ):
        
        source_notebook = page.GetParentNotebook()
        
        for ( index, p ) in enumerate( source_notebook._GetPages() ):
            
            if p == page:
                
                source_notebook.removeTab( index )
                
                source_notebook._UpdatePreviousPageIndex()
                
                break
                
            
        
        if source_notebook != dest_notebook:
            
            page.setParent( dest_notebook )
            
            self._controller.pub( 'refresh_page_name', source_notebook.GetPageKey() )
            
        
        insertion_tab_index = min( insertion_tab_index, dest_notebook.count() )
        
        dest_notebook.insertTab( insertion_tab_index, page, page.GetName() )
        
        if follow_dropped_page: dest_notebook.setCurrentIndex( insertion_tab_index )
        
        if follow_dropped_page:
            
            self.ShowPage( page )
            
        
        self._controller.pub( 'refresh_page_name', page.GetPageKey() )
        
    
    def _MovePages( self, pages, dest_notebook ):
        
        insertion_tab_index = dest_notebook.GetNumPages( only_my_level = True )
        
        for page in pages:
            
            if page.GetParentNotebook() != dest_notebook:
                
                self._MovePage( page, dest_notebook, insertion_tab_index )
                
                insertion_tab_index += 1
                
            
        
    
    def _RefreshPageName( self, index ):
        
        if index == -1 or index > self.count() - 1:
            
            return
            
        
        new_options = self._controller.new_options
        
        max_page_name_chars = new_options.GetInteger( 'max_page_name_chars' )
        
        page_file_count_display = new_options.GetInteger( 'page_file_count_display' )
        
        import_page_progress_display = new_options.GetBoolean( 'import_page_progress_display' )
        
        page = self.widget( index )
        
        if isinstance( page, Page ) and not page.IsInitialised():
            
            page_name = 'initialising'
            
        else:
            
            page_name = page.GetName()
            
            page_name = page_name.replace( os.linesep, '' )
            
        
        page_name = HydrusText.ElideText( page_name, max_page_name_chars )
        
        num_string = ''
        
        ( num_files, ( num_value, num_range ) ) = page.GetNumFileSummary()
        
        if page_file_count_display == CC.PAGE_FILE_COUNT_DISPLAY_ALL or ( page_file_count_display == CC.PAGE_FILE_COUNT_DISPLAY_ONLY_IMPORTERS and page.IsImporter() ):
            
            num_string += HydrusData.ToHumanInt( num_files )
            
        
        if import_page_progress_display:
            
            if num_range > 0 and num_value != num_range:
                
                if len( num_string ) > 0:
                    
                    num_string += ', '
                    
                
                num_string += HydrusData.ConvertValueRangeToPrettyString( num_value, num_range )
                
            
        
        if len( num_string ) > 0:
            
            page_name += ' (' + num_string + ')'
            
        
        safe_page_name = ClientGUIFunctions.EscapeMnemonics( page_name )
        
        tab_bar = self.tabBar()
        
        existing_page_name = tab_bar.tabText( index )
        
        if existing_page_name not in ( safe_page_name, page_name ):
            
            tab_bar.setTabText( index, safe_page_name )
            
        
    
    def _RenamePage( self, index ):
        
        if index == -1 or index > self.count() - 1:
            
            return
            
        
        page = self.widget( index )
        
        current_name = page.GetName()
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the new name.', default = current_name, allow_blank = False ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                new_name = dlg.GetValue()
                
                page.SetName( new_name )
                
                self._controller.pub( 'refresh_page_name', page.GetPageKey() )
                
            
        
    
    def _SendPageToNewNotebook( self, index ):
        
        if 0 <= index and index <= self.count() - 1:
            
            page = self.widget( index )
            
            dest_notebook = self.NewPagesNotebook( forced_insertion_index = index, give_it_a_blank_page = False )
            
            self._MovePage( page, dest_notebook, 0 )
            
        
    
    def _SendRightPagesToNewNotebook( self, from_index ):
        
        message = 'Send all pages to the right to a new page of pages?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            pages_index = self.count()
            
            dest_notebook = self.NewPagesNotebook( forced_insertion_index = pages_index, give_it_a_blank_page = False )
            
            movees = list( range( from_index + 1, pages_index ) )
            
            movees.reverse()
            
            for index in movees:
                
                page = self.widget( index )
                
                self._MovePage( page, dest_notebook, 0 )
                
            
        
    
    def _ShiftPage( self, page_index, delta = None, new_index = None ):
        
        new_page_index = page_index
        
        if delta is not None:
            
            new_page_index = page_index + delta
            
        
        if new_index is not None:
            
            new_page_index = new_index
            
        
        if new_page_index == page_index:
            
            return
            
        
        if 0 <= new_page_index and new_page_index <= self.count() - 1:
            
            page_is_selected = self.currentIndex() == page_index
            
            page = self.widget( page_index )
            name = self.tabText( page_index )
            
            self.removeTab( page_index )
            
            self._UpdatePreviousPageIndex()
            
            self.insertTab( new_page_index, page, name )
            if page_is_selected: self.setCurrentIndex( new_page_index )
            
        
    
    def _ShowMenu( self, screen_position ):
        
        tab_index = ClientGUIFunctions.NotebookScreenToHitTest( self, screen_position )
        
        num_pages = self.count()
        
        end_index = num_pages - 1
        
        more_than_one_tab = num_pages > 1
        
        click_over_tab = tab_index != -1
        
        can_go_home = tab_index > 1
        can_go_left = tab_index > 0
        can_go_right = tab_index < end_index
        can_go_end = tab_index < end_index - 1
        
        click_over_page_of_pages = False
        
        menu = QW.QMenu()
        
        if click_over_tab:
            
            page = self.widget( tab_index )
            
            click_over_page_of_pages = isinstance( page, PagesNotebook )
            
            if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                
                label = 'page weight: {}'.format( HydrusData.ToHumanInt( page.GetTotalWeight() ) )
                
                ClientGUIMenus.AppendMenuLabel( menu, label, label )
                
                ClientGUIMenus.AppendSeparator( menu )
                
            
            ClientGUIMenus.AppendMenuItem( menu, 'close page', 'Close this page.', self._ClosePage, tab_index )
            
            if more_than_one_tab:
                
                if not can_go_left or not can_go_right:
                    
                    if num_pages == 2:
                        
                        label = 'close other page'
                        description = 'Close the other page.'
                        
                    else:
                        
                        label = 'close other pages'
                        description = 'Close all pages but this one.'
                        
                    
                    ClientGUIMenus.AppendMenuItem( menu, label, description, self._CloseOtherPages, tab_index )
                    
                else:
                    
                    close_menu = QW.QMenu( menu )
                    
                    ClientGUIMenus.AppendMenuItem( close_menu, 'other pages', 'Close all pages but this one.', self._CloseOtherPages, tab_index )
                    
                    if can_go_left:
                        
                        ClientGUIMenus.AppendMenuItem( close_menu, 'pages to the left', 'Close all pages to the left of this one.', self._CloseLeftPages, tab_index )
                        
                    
                    if can_go_right:
                        
                        ClientGUIMenus.AppendMenuItem( close_menu, 'pages to the right', 'Close all pages to the right of this one.', self._CloseRightPages, tab_index )
                        
                    
                    ClientGUIMenus.AppendMenu( menu, close_menu, 'close' )
                    
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        #
        
        if click_over_page_of_pages:
            
            notebook_to_get_selectable_media_pages_from = self.widget( tab_index )
            
        else:
            
            notebook_to_get_selectable_media_pages_from = self
            
        
        selectable_media_pages = notebook_to_get_selectable_media_pages_from.GetMediaPages()
        
        if len( selectable_media_pages ) > 0:
            
            select_menu = QW.QMenu( menu )
            
            for selectable_media_page in selectable_media_pages:
                
                label = '{} - {}'.format( selectable_media_page.GetName(), selectable_media_page.GetPrettyStatus() )
                
                ClientGUIMenus.AppendMenuItem( select_menu, label, 'select this page', self.ShowPage, selectable_media_page )
                
            
            ClientGUIMenus.AppendMenu( menu, select_menu, 'pages' )
            
        
        #
        
        if more_than_one_tab:
            
            selection_index = self.currentIndex()
            
            can_select_home = selection_index > 1
            can_select_left = selection_index > 0
            can_select_right = selection_index < end_index
            can_select_end = selection_index < end_index - 1
            
            navigate_menu = QW.QMenu( menu )
            
            if can_select_home:
                
                ClientGUIMenus.AppendMenuItem( navigate_menu, 'first page', 'Select the page at the start of these.', self.MoveSelectionEnd, -1 )
                
            
            if can_select_left:
                
                ClientGUIMenus.AppendMenuItem( navigate_menu, 'page to the left', 'Select the page to the left of this one.', self.MoveSelection, -1 )
                
            
            if can_select_right:
                
                ClientGUIMenus.AppendMenuItem( navigate_menu, 'page to the right', 'Select the page to the right of this one.', self.MoveSelection, 1 )
                
            
            if can_select_end:
                
                ClientGUIMenus.AppendMenuItem( navigate_menu, 'last page', 'Select the page at the end of these.', self.MoveSelectionEnd, 1 )
                
            
            ClientGUIMenus.AppendMenu( menu, navigate_menu, 'select' )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'new page', 'Choose a new page.', self._ChooseNewPage )
        
        if click_over_tab:
            
            ClientGUIMenus.AppendMenuItem( menu, 'new page here', 'Choose a new page.', self._ChooseNewPage, tab_index )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if more_than_one_tab:
                
                move_menu = QW.QMenu( menu )
                
                if can_go_home:
                    
                    ClientGUIMenus.AppendMenuItem( move_menu, 'to left end', 'Move this page all the way to the left.', self._ShiftPage, tab_index, new_index=0 )
                    
                
                if can_go_left:
                    
                    ClientGUIMenus.AppendMenuItem( move_menu, 'left', 'Move this page one to the left.', self._ShiftPage, tab_index, delta=-1 )
                    
                
                if can_go_right:
                    
                    ClientGUIMenus.AppendMenuItem( move_menu, 'right', 'Move this page one to the right.', self._ShiftPage, tab_index, 1 )
                    
                
                if can_go_end:
                    
                    ClientGUIMenus.AppendMenuItem( move_menu, 'to right end', 'Move this page all the way to the right.', self._ShiftPage, tab_index, new_index=end_index )
                    
                
                ClientGUIMenus.AppendMenu( menu, move_menu, 'move page' )
                
            
            ClientGUIMenus.AppendMenuItem( menu, 'rename page', 'Rename this page.', self._RenamePage, tab_index )
            
            ClientGUIMenus.AppendMenuItem( menu, 'duplicate page', 'Duplicate this page.', self._DuplicatePage, tab_index )
            
            if more_than_one_tab:
                
                ClientGUIMenus.AppendSeparator( menu )
                
                submenu = QW.QMenu( menu )
                
                ClientGUIMenus.AppendMenuItem( submenu, 'by most files first', 'Sort these pages according to how many files they appear to have.', self._SortPagesByFileCount, 'desc' )
                ClientGUIMenus.AppendMenuItem( submenu, 'by fewest files first', 'Sort these pages according to how few files they appear to have.', self._SortPagesByFileCount, 'asc' )
                ClientGUIMenus.AppendMenuItem( submenu, 'by name a-z', 'Sort these pages according to their names.', self._SortPagesByName, 'asc' )
                ClientGUIMenus.AppendMenuItem( submenu, 'by name z-a', 'Sort these pages according to their names.', self._SortPagesByName, 'desc' )
                
                ClientGUIMenus.AppendMenu( menu, submenu, 'sort pages' )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'send this page down to a new page of pages', 'Make a new page of pages and put this page in it.', self._SendPageToNewNotebook, tab_index )
            
            if can_go_right:
                
                ClientGUIMenus.AppendMenuItem( menu, 'send pages to the right to a new page of pages', 'Make a new page of pages and put all the pages to the right into it.', self._SendRightPagesToNewNotebook, tab_index )
                
            
            if click_over_page_of_pages and page.count() > 0:
                
                ClientGUIMenus.AppendSeparator( menu )
                
                ClientGUIMenus.AppendMenuItem( menu, 'refresh all this page\'s pages', 'Command every page below this one to refresh.', page.RefreshAllPages )
                
            
        
        existing_session_names = self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER )
        
        if len( existing_session_names ) > 0 or click_over_page_of_pages:
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        if len( existing_session_names ) > 0:
            
            submenu = QW.QMenu( menu )
            
            for name in existing_session_names:
                
                ClientGUIMenus.AppendMenuItem( submenu, name, 'Load this session here.', self.AppendGUISessionFreshest, name )
                
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'append session' )
            
        
        if click_over_page_of_pages:
            
            submenu = QW.QMenu( menu )
            
            for name in existing_session_names:
                
                if name in ClientGUISession.RESERVED_SESSION_NAMES:
                    
                    continue
                    
                
                ClientGUIMenus.AppendMenuItem( submenu, name, 'Save this page of pages to the session.', self._controller.gui.ProposeSaveGUISession, notebook = page, name = name )
                
            
            ClientGUIMenus.AppendMenuItem( submenu, 'create a new session', 'Save this page of pages to the session.', self._controller.gui.ProposeSaveGUISession, notebook = page, suggested_name = page.GetName() )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'save this page of pages to a session' )
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _SortPagesByFileCount( self, order ):
        
        def key( page ):
            
            ( total_num_files, ( total_num_value, total_num_range ) ) = page.GetNumFileSummary()
            
            return ( total_num_files, total_num_range, total_num_value )
            
        
        ordered_pages = sorted( self.GetPages(), key = key, reverse = order == 'desc' )
        
        self._SortPagesSetPages( ordered_pages )
        
    
    def _SortPagesByName( self, order ):
        
        def file_count_secondary( page ):
            
            ( total_num_files, ( total_num_value, total_num_range ) ) = page.GetNumFileSummary()
            
            return ( total_num_files, total_num_range, total_num_value )
            
        
        ordered_pages = sorted( self.GetPages(), key = file_count_secondary, reverse = True )
        
        ordered_pages = sorted( ordered_pages, key = lambda page: page.GetName(), reverse = order == 'desc' )
        
        self._SortPagesSetPages( ordered_pages )
        
    
    def _SortPagesSetPages( self, ordered_pages ):
        
        selected_page = self.currentWidget()
        
        pages_to_names = {}
        
        for i in range( self.count() ):
            
            page = self.widget( 0 )
            
            name = self.tabText( 0 )
            
            pages_to_names[ page ] = name
            
            self.removeTab( 0 )
            
            self._UpdatePreviousPageIndex()
            
        
        for page in ordered_pages:
            
            name = pages_to_names[ page ]
            
            self.addTab( page, name )
            
            if page == selected_page:
                
                self.setCurrentIndex( self.count() - 1 )
                
            
        
    
    def AppendGUISession( self, session: ClientGUISession.GUISessionContainer ):
        
        starting_index = self._GetDefaultPageInsertionIndex()
        
        forced_insertion_index = starting_index
        
        self.InsertSession( forced_insertion_index, session )
        
    
    def AppendGUISessionBackup( self, name, timestamp, load_in_a_page_of_pages = True ):
        
        try:
            
            session = session = self._controller.Read( 'gui_session', name, timestamp )
            
        except Exception as e:
            
            HydrusData.ShowText( 'While trying to load session "{}" (ts {}), this error happened:'.format( name, timestamp ) )
            HydrusData.ShowException( e )
            
            return
            
        
        if load_in_a_page_of_pages:
            
            destination = self.NewPagesNotebook( name = name, give_it_a_blank_page = False )
            
        else:
            
            destination = self
            
        
        destination.AppendGUISession( session )
        
    
    def AppendGUISessionFreshest( self, name, load_in_a_page_of_pages = True ):
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetVariable( 'popup_text_1', 'loading session "{}"\u2026'.format( name ) )
        
        HG.client_controller.pub( 'message', job_key )
        
        # get that message showing before we do the work of loading session
        HG.client_controller.app.processEvents()
        
        try:
            
            session = self._controller.Read( 'gui_session', name )
            
        except Exception as e:
            
            HydrusData.ShowText( 'While trying to load session "{}", this error happened:'.format( name ) )
            HydrusData.ShowException( e )
            
            return
            
        
        HG.client_controller.app.processEvents()
        
        if load_in_a_page_of_pages:
            
            destination = self.NewPagesNotebook( name = name, give_it_a_blank_page = False )
            
        else:
            
            destination = self
            
        
        HG.client_controller.app.processEvents()
        
        destination.AppendGUISession( session )
        
        self.freshSessionLoaded.emit( session )
        
        job_key.Delete()
        
    
    def ChooseNewPage( self ):
        
        self._ChooseNewPage()
        
    
    def ChooseNewPageForDeepestNotebook( self ):
        
        current_page = self.currentWidget()
        
        if isinstance( current_page, PagesNotebook ):
            
            current_page.ChooseNewPageForDeepestNotebook()
            
        else:
            
            self._ChooseNewPage()
            
        
    
    def CleanBeforeClose( self ):
        
        for page in self._GetPages():
            
            page.CleanBeforeClose()
            
        
    
    def CleanBeforeDestroy( self ):
        
        for page in self._GetPages():
            
            page.CleanBeforeDestroy()
            
        
        self._controller.ReleasePageKey( self._page_key )
        
    
    def CloseCurrentPage( self, polite = True ):
        
        selection = self.currentIndex()
        
        if selection != -1:
            
            page = self.widget( selection )
            
            if isinstance( page, PagesNotebook ):
                
                if page.GetNumPages() > 0:
                    
                    page.CloseCurrentPage( polite )
                    
                else:
                    
                    self._ClosePage( selection, polite = polite )
                    
                
            else:
                
                self._ClosePage( selection, polite = polite )
                
            
        
    
    def eventFilter( self, watched, event ):
        
        if event.type() in ( QC.QEvent.MouseButtonDblClick, QC.QEvent.MouseButtonRelease ):
            
            screen_position = QG.QCursor.pos()
            
            if watched == self.tabBar():
                
                tab_pos = self.tabBar().mapFromGlobal( screen_position )
                
                over_a_tab = tab_pos != -1
                over_tab_greyspace = tab_pos == -1
                
            else:
                
                over_a_tab = False
                
                widget_under_mouse = QW.QApplication.instance().widgetAt( screen_position )
                
                if widget_under_mouse is None:
                    
                    over_tab_greyspace = None
                    
                else:
                    
                    if self.count() == 0 and isinstance( widget_under_mouse, QW.QStackedWidget ):
                        
                        over_tab_greyspace = True
                        
                    else:
                        
                        over_tab_greyspace = widget_under_mouse == self
                        
                    
                
            
            if event.type() == QC.QEvent.MouseButtonDblClick:
                
                if event.button() == QC.Qt.LeftButton and over_tab_greyspace and not over_a_tab:
                    
                    self.EventNewPageFromScreenPosition( screen_position )
                    
                    return True
                    
                
            elif event.type() == QC.QEvent.MouseButtonRelease:
                
                if event.button() == QC.Qt.RightButton and ( over_a_tab or over_tab_greyspace ):
                    
                    self.ShowMenuFromScreenPosition( screen_position )
                    
                    return True
                    
                elif event.button() == QC.Qt.MiddleButton and over_tab_greyspace and not over_a_tab:
                    
                    self.EventNewPageFromScreenPosition( screen_position )
                    
                    return True
                    
                
            
        
        return False
        
    
    def ShowMenuFromScreenPosition( self, position ):
        
        notebook = self._GetNotebookFromScreenPosition( position )
        
        notebook._ShowMenu( position )
        
    
    def EventNewPageFromScreenPosition( self, position ):
        
        notebook = self._GetNotebookFromScreenPosition( position )
        
        notebook._ChooseNewPage()
        
    
    def GetAPIInfoDict( self, simple ):
        
        return {}
        
    
    def GetCurrentGUISession( self, name: str, only_changed_page_data: bool, about_to_save: bool ):
        
        ( page_container, hashes_to_page_data, skipped_unchanged_page_hashes ) = self.GetSerialisablePage( only_changed_page_data, about_to_save )
        
        session = ClientGUISession.GUISessionContainer( name, top_notebook_container = page_container, hashes_to_page_data = hashes_to_page_data, skipped_unchanged_page_hashes = skipped_unchanged_page_hashes )
        
        return session
        
    
    def GetCurrentMediaPage( self ):
        
        page = self.currentWidget()
        
        if isinstance( page, PagesNotebook ):
            
            return page.GetCurrentMediaPage()
            
        else:
            
            return page # this can be None
            
        
    
    def GetMediaPages( self, only_my_level = False ):
        
        return self._GetMediaPages( only_my_level )
        
    
    def GetName( self ):
        
        return self._name
        
    
    def GetNumFileSummary( self ):
        
        total_num_files = 0
        total_num_value = 0
        total_num_range = 0
        
        for page in self._GetPages():
            
            ( num_files, ( num_value, num_range ) ) = page.GetNumFileSummary()
            
            total_num_files += num_files
            total_num_value += num_value
            total_num_range += num_range
            
        
        return ( total_num_files, ( total_num_value, total_num_range ) )
        
    
    def GetNumPages( self, only_my_level = False ):
        
        if only_my_level:
            
            return self.count()
            
        else:
            
            total = 0
            
            for page in self._GetPages():
                
                if isinstance( page, PagesNotebook ):
                    
                    total += page.GetNumPages( False )
                    
                else:
                    
                    total += 1
                    
                
            
            return total
            
        
    
    def GetOrMakeGalleryDownloaderPage( self, desired_page_name = None, desired_page_key = None, select_page = True ):
        
        potential_gallery_downloader_pages = [ page for page in self._GetMediaPages( False ) if page.IsGalleryDownloaderPage() ]
        
        if desired_page_key is not None and desired_page_key in ( page.GetPageKey() for page in potential_gallery_downloader_pages ):
            
            potential_gallery_downloader_pages = [ page for page in potential_gallery_downloader_pages if page.GetPageKey() == desired_page_key ]
            
        elif desired_page_name is not None:
            
            potential_gallery_downloader_pages = [ page for page in potential_gallery_downloader_pages if page.GetName() == desired_page_name ]
            
        
        if len( potential_gallery_downloader_pages ) > 0:
            
            # ok, we can use an existing one. should we use the current?
            
            current_media_page = self.GetCurrentMediaPage()
            
            if current_media_page is not None and current_media_page in potential_gallery_downloader_pages:
                
                return current_media_page
                
            else:
                
                return potential_gallery_downloader_pages[0]
                
            
        else:
            
            return self.NewPageImportGallery( page_name = desired_page_name, on_deepest_notebook = True, select_page = select_page )
            
        
    
    def GetOrMakeMultipleWatcherPage( self, desired_page_name = None, desired_page_key = None, select_page = True ):
        
        potential_watcher_pages = [ page for page in self._GetMediaPages( False ) if page.IsMultipleWatcherPage() ]
        
        if desired_page_key is not None and desired_page_key in ( page.GetPageKey() for page in potential_watcher_pages ):
            
            potential_watcher_pages = [ page for page in potential_watcher_pages if page.GetPageKey() == desired_page_key ]
            
        elif desired_page_name is not None:
            
            potential_watcher_pages = [ page for page in potential_watcher_pages if page.GetName() == desired_page_name ]
            
        
        if len( potential_watcher_pages ) > 0:
            
            # ok, we can use an existing one. should we use the current?
            
            current_media_page = self.GetCurrentMediaPage()
            
            if current_media_page is not None and current_media_page in potential_watcher_pages:
                
                return current_media_page
                
            else:
                
                return potential_watcher_pages[0]
                
            
        else:
            
            return self.NewPageImportMultipleWatcher( page_name = desired_page_name, on_deepest_notebook = True, select_page = select_page )
            
        
    
    def GetOrMakeURLImportPage( self, desired_page_name = None, desired_page_key = None, select_page =  True ):
        
        potential_url_import_pages = [ page for page in self._GetMediaPages( False ) if page.IsURLImportPage() ]
        
        if desired_page_key is not None and desired_page_key in ( page.GetPageKey() for page in potential_url_import_pages ):
            
            potential_url_import_pages = [ page for page in potential_url_import_pages if page.GetPageKey() == desired_page_key ]
            
        elif desired_page_name is not None:
            
            potential_url_import_pages = [ page for page in potential_url_import_pages if page.GetName() == desired_page_name ]
            
        
        if len( potential_url_import_pages ) > 0:
            
            # ok, we can use an existing one. should we use the current?
            
            current_media_page = self.GetCurrentMediaPage()
            
            if current_media_page is not None and current_media_page in potential_url_import_pages:
                
                return current_media_page
                
            else:
                
                return potential_url_import_pages[0]
                
            
        else:
            
            return self.NewPageImportURLs( page_name = desired_page_name, on_deepest_notebook = True, select_page = select_page )
            
        
    
    def GetPageFromPageKey( self, page_key ):
        
        if self._page_key == page_key:
            
            return self
            
        
        for page in self._GetPages():
            
            if page.GetPageKey() == page_key:
                
                return page
                
            
            if isinstance( page, PagesNotebook ):
                
                if page.HasPageKey( page_key ):
                    
                    return page.GetPageFromPageKey( page_key )
                    
                
            
        
        return None
        
    
    def GetPageKey( self ):
        
        return self._page_key
        
    
    def GetPageKeys( self ):
        
        page_keys = { self._page_key }
        
        for page in self._GetPages():
            
            page_keys.update( page.GetPageKeys() )
            
        
        return page_keys
        
    
    def GetParentNotebook( self ):
        
        return self._parent_notebook
        
    
    def GetSerialisablePage( self, only_changed_page_data, about_to_save ):
        
        page_containers = []
        
        hashes_to_page_data = {}
        
        skipped_unchanged_page_hashes = set()
        
        for page in self._GetPages():
            
            ( sub_page_container, some_hashes_to_page_data, some_skipped_unchanged_page_hashes ) = page.GetSerialisablePage( only_changed_page_data, about_to_save )
            
            page_containers.append( sub_page_container )
            
            hashes_to_page_data.update( some_hashes_to_page_data )
            skipped_unchanged_page_hashes.update( some_skipped_unchanged_page_hashes )
            
        
        page_container = ClientGUISession.GUISessionContainerPageNotebook( self._name, page_containers = page_containers )
        
        return ( page_container, hashes_to_page_data, skipped_unchanged_page_hashes )
        
    
    def GetSessionAPIInfoDict( self, is_selected = True ):
        
        current_page = self.currentWidget()
        
        my_pages_list = []
        
        for page in self._GetPages():
            
            page_is_selected = is_selected and page == current_page
            
            page_info_dict = page.GetSessionAPIInfoDict( is_selected = page_is_selected )
            
            my_pages_list.append( page_info_dict )
            
        
        root = {}
        
        root[ 'name' ] = self.GetName()
        root[ 'page_key' ] = self._page_key.hex()
        root[ 'page_type' ] = ClientGUIManagement.MANAGEMENT_TYPE_PAGE_OF_PAGES
        root[ 'selected' ] = is_selected
        root[ 'pages' ] = my_pages_list
        
        return root
        
    
    def GetPages( self ):
        
        return self._GetPages()
        
    
    def GetPrettyStatus( self ):
        
        ( num_files, ( num_value, num_range ) ) = self.GetNumFileSummary()
        
        num_string = HydrusData.ToHumanInt( num_files )
        
        if num_range > 0 and num_value != num_range:
            
            num_string += ', ' + HydrusData.ConvertValueRangeToPrettyString( num_value, num_range )
            
        
        return HydrusData.ToHumanInt( self.count() ) + ' pages, ' + num_string + ' files'
        
    
    def GetTestAbleToCloseStatement( self ):
        
        count = collections.Counter()
        
        for page in self._GetMediaPages( False ):
            
            try:
                
                page.CheckAbleToClose()
                
            except HydrusExceptions.VetoException as e:
                
                reason = str( e )
                
                count[ reason ] += 1
                
            
        
        if len( count ) > 0:
            
            message = ''
            
            for ( reason, c ) in list(count.items()):
                
                if c == 1:
                    
                    message = '1 page says: ' + reason
                    
                else:
                    
                    message = HydrusData.ToHumanInt( c ) + ' pages say:' + reason
                    
                
                message += os.linesep
                
            
            return message
            
        else:
            
            return None
            
        
    
    def GetTotalNumHashesAndSeeds( self ) -> int:
        
        total_num_hashes = 0
        total_num_seeds = 0
        
        for page in self._GetPages():
            
            ( num_hashes, num_seeds ) = page.GetTotalNumHashesAndSeeds()
            
            total_num_hashes += num_hashes
            total_num_seeds += num_seeds
            
        
        return ( total_num_hashes, total_num_seeds )
        
    
    def GetTotalWeight( self ) -> int:
        
        total_weight = sum( ( page.GetTotalWeight() for page in self._GetPages() ) )
        
        return total_weight
        
    
    def HasMediaPageName( self, page_name, only_my_level = False ):
        
        media_pages = self._GetMediaPages( only_my_level )
        
        for page in media_pages:
            
            if page.GetName() == page_name:
                
                return True
                
            
        
        return False
        
    
    def HasPage( self, page ):
        
        return self.HasPageKey( page.GetPageKey() )
        
    
    def HasPageKey( self, page_key ):
        
        for page in self._GetPages():
            
            if page.GetPageKey() == page_key:
                
                return True
                
            elif isinstance( page, PagesNotebook ) and page.HasPageKey( page_key ):
                
                return True
                
            
        
        return False
        
    
    def HasMultipleWatcherPage( self ):
        
        for page in self._GetPages():
            
            if isinstance( page, PagesNotebook ):
                
                if page.HasMultipleWatcherPage():
                    
                    return True
                    
                
            else:
                
                if page.IsMultipleWatcherPage():
                    
                    return True
                    
                
            
        
        return False
        
    
    def HasURLImportPage( self ):
        
        for page in self._GetPages():
            
            if isinstance( page, PagesNotebook ):
                
                if page.HasURLImportPage():
                    
                    return True
                    
                
            else:
                
                if page.IsURLImportPage():
                    
                    return True
                    
                
            
        
        return False
        
    
    def InsertSession( self, forced_insertion_index: int, session: ClientGUISession.GUISessionContainer, session_is_clean = True ):
        
        # get the top notebook, then for every page in there...
        
        top_notebook_container = session.GetTopNotebook()
        
        page_containers = top_notebook_container.GetPageContainers()
        select_first_page = True
        
        self.InsertSessionNotebookPages( forced_insertion_index, session, page_containers, select_first_page, session_is_clean = session_is_clean )
        
    
    def InsertSessionNotebook( self, forced_insertion_index: int, session: ClientGUISession.GUISessionContainer, notebook_page_container: ClientGUISession.GUISessionContainerPageNotebook, select_first_page: bool, session_is_clean = True ):
        
        name = notebook_page_container.GetName()
        
        page = self.NewPagesNotebook( name, forced_insertion_index = forced_insertion_index, give_it_a_blank_page = False, select_page = select_first_page )
        
        page_containers = notebook_page_container.GetPageContainers()
        
        page.InsertSessionNotebookPages( 0, session, page_containers, select_first_page, session_is_clean = session_is_clean )
        
    
    def InsertSessionNotebookPages( self, forced_insertion_index: int, session: ClientGUISession.GUISessionContainer, page_containers: typing.Collection[ ClientGUISession.GUISessionContainerPage ], select_first_page: bool, session_is_clean = True ):
        
        done_first_page = False
        
        for page_container in page_containers:
            
            select_page = select_first_page and not done_first_page
            
            try:
                
                if isinstance( page_container, ClientGUISession.GUISessionContainerPageNotebook ):
                    
                    self.InsertSessionNotebook( forced_insertion_index, session, page_container, select_page, session_is_clean = session_is_clean )
                    
                else:
                    
                    result = self.InsertSessionPage( forced_insertion_index, session, page_container, select_page, session_is_clean = session_is_clean )
                    
                    if result is None:
                        
                        continue
                        
                    
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            forced_insertion_index += 1
            
            done_first_page = True
            
        
    
    def InsertSessionPage( self, forced_insertion_index: int, session: ClientGUISession.GUISessionContainer, page_container: ClientGUISession.GUISessionContainerPageSingle, select_page: bool, session_is_clean = True ):
        
        try:
            
            page_data_hash = page_container.GetPageDataHash()
            
            page_data = session.GetPageData( page_data_hash )
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.ShowText( 'The page with name "{}" and hash "{}" failed to load because its data was missing!'.format( page_container.GetName(), page_data_hash.hex() ) )
            
            return None
            
        
        management_controller = page_data.GetManagementController()
        initial_hashes = page_data.GetHashes()
        
        page = self.NewPage( management_controller, initial_hashes = initial_hashes, forced_insertion_index = forced_insertion_index, select_page = select_page )
        
        if session_is_clean and page is not None:
            
            page.SetPageContainerClean( page_container )
            
        
        return page
        
    
    def IsMultipleWatcherPage( self ):
        
        return False
        
    
    def IsImporter( self ):
        
        return False
        
    
    def IsURLImportPage( self ):
        
        return False
        
    
    def LoadGUISession( self, name ):
        
        if self.count() > 0:
            
            message = 'Close the current pages and load session "{}"?'.format( name )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Clear and load session?' )
            
            if result != QW.QDialog.Accepted:
                
                return
                
            
            try:
                
                self.TestAbleToClose()
                
            except HydrusExceptions.VetoException:
                
                return
                
            
            self._CloseAllPages( polite = False, delete_pages = True )
            
            self._controller.CallLaterQtSafe( self, 1.0, 'append session', self.AppendGUISessionFreshest, name, load_in_a_page_of_pages = False )
            
        else:
            
            self.AppendGUISessionFreshest( name, load_in_a_page_of_pages = False )
            
        
    
    def MediaDragAndDropDropped( self, source_page_key, hashes ):
        
        source_page = self.GetPageFromPageKey( source_page_key )
        
        if source_page is None:
            
            return
            
        
        source_management_controller = source_page.GetManagementController()
        
        location_context = source_management_controller.GetVariable( 'location_context' )
        
        screen_position = QG.QCursor.pos()
        
        dest_notebook = self._GetNotebookFromScreenPosition( screen_position )
        
        tab_index = ClientGUIFunctions.NotebookScreenToHitTest( dest_notebook, screen_position )
        
        do_add = True
        # do chase - if we need to chase to an existing dest page on which we dropped files
        # do return - if we need to return to source page if we created a new one
        
        current_widget = dest_notebook.currentWidget()
        
        if tab_index == -1 and current_widget is not None and not isinstance( current_widget, PagesNotebook ) and current_widget.rect().contains( current_widget.mapFromGlobal( screen_position ) ):
            
            dest_page = current_widget
            
        elif tab_index == -1:
            
            dest_page = dest_notebook.NewPageQuery( location_context, initial_hashes = hashes )
            
            do_add = False
            
        else:
            
            dest_page = dest_notebook.widget( tab_index )
            
            if isinstance( dest_page, PagesNotebook ):
                
                result = dest_page.GetCurrentMediaPage()
                
                if result is None:
                    
                    dest_page = dest_page.NewPageQuery( location_context, initial_hashes = hashes )
                    
                    do_add = False
                    
                else:
                    
                    dest_page = result
                    
                
            
        
        if dest_page is None:
            
            return # we somehow dropped onto a new notebook that has no pages
            
        
        if isinstance( dest_page, PagesNotebook ):
            
            return # dropped on the edge of some notebook somehow
            
        
        if dest_page.GetPageKey() == source_page_key:
            
            return # we dropped onto the same page we picked up on
            
        
        if do_add:
            
            media_results = self._controller.Read( 'media_results', hashes, sorted = True )
            
            dest_page.AddMediaResults( media_results )
            
        else:
            
            self.ShowPage( source_page )
            
        
        # queryKBM here for instant check, not waiting for event processing to catch up u wot mate
        ctrl_down = QW.QApplication.queryKeyboardModifiers() & QC.Qt.ControlModifier
        
        if not ctrl_down:
            
            source_page.GetMediaPanel().RemoveMedia( source_page.GetPageKey(), hashes )
            
        
    
    def MoveSelection( self, delta, just_do_test = False ):
        
        current_index = self.currentIndex()
        current_page = self.currentWidget()
        
        if current_page is None or current_index is None:
            
            return False
            
        elif isinstance( current_page, PagesNotebook ):
            
            if current_page.MoveSelection( delta, just_do_test = True ):
                
                return current_page.MoveSelection( delta, just_do_test = just_do_test )
                
            
        
        new_index = self.currentIndex() + delta
        
        if 0 <= new_index <= self.count() - 1:
            
            if not just_do_test:
                
                self.setCurrentIndex( new_index )
                
            
            return True
            
        
        return False
        
    
    def MoveSelectionEnd( self, delta, just_do_test = False ):
        
        if self.count() <= 1: # 1 is a no-op
            
            return False
            
        
        current_index = self.currentIndex()
        current_page = self.currentWidget()
        
        if isinstance( current_page, PagesNotebook ):
            
            if current_page.MoveSelectionEnd( delta, just_do_test = True ):
                
                return current_page.MoveSelectionEnd( delta, just_do_test = just_do_test )
                
            
        
        if delta < 0:
            
            new_index = 0
            
        else:
            
            new_index = self.count() - 1
            
        
        if not just_do_test:
            
            self.setCurrentIndex( new_index )
            
        
        return True
        
    
    def NewPage( self, management_controller, initial_hashes = None, forced_insertion_index = None, on_deepest_notebook = False, select_page = True ):
        
        current_page = self.currentWidget()
        
        if on_deepest_notebook and isinstance( current_page, PagesNotebook ):
            
            return current_page.NewPage( management_controller, initial_hashes = initial_hashes, forced_insertion_index = forced_insertion_index, on_deepest_notebook = on_deepest_notebook )
            
        
        WARNING_TOTAL_PAGES = self._controller.new_options.GetInteger( 'total_pages_warning' )
        MAX_TOTAL_PAGES = max( 500, WARNING_TOTAL_PAGES * 2 )
        
        (
            total_active_page_count,
            total_active_num_hashes,
            total_active_num_seeds,
            total_closed_page_count,
            total_closed_num_hashes,
            total_closed_num_seeds
        ) = self._controller.gui.GetTotalPageCounts()
        
        if total_active_page_count + total_closed_page_count >= WARNING_TOTAL_PAGES:
            
            self._controller.gui.DeleteAllClosedPages()
            
        
        if not HG.no_page_limit_mode:
            
            if total_active_page_count >= MAX_TOTAL_PAGES and not ClientGUIFunctions.DialogIsOpen():
                
                message = 'The client should not have more than ' + str( MAX_TOTAL_PAGES ) + ' pages open, as it leads to program instability! Are you sure you want to open more pages?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Too many pages!', yes_label = 'yes, and do not tell me again', no_label = 'no' )
                
                if result == QW.QDialog.Accepted:
                    
                    HG.no_page_limit_mode = True
                    
                    self._controller.pub( 'notify_new_options' )
                    
                else:
                    
                    return None
                    
                
            
            if total_active_page_count == WARNING_TOTAL_PAGES:
                
                HydrusData.ShowText( 'You have ' + str( total_active_page_count ) + ' pages open! You can only open a few more before program stability is affected! Please close some now!' )
                
            
        
        self._controller.ResetIdleTimer()
        self._controller.ResetPageChangeTimer()
        
        if initial_hashes is None:
            
            initial_hashes = []
            
        
        page = Page( self, self._controller, management_controller, initial_hashes )
        
        if forced_insertion_index is None:
            
            if self._next_new_page_index is None:
                
                insertion_index = self._GetDefaultPageInsertionIndex()
                
            else:
                
                insertion_index = self._next_new_page_index
                
                self._next_new_page_index = None
                
            
        else:
            
            insertion_index = forced_insertion_index
            
        
        page_name = page.GetName()
        
        # in some unusual circumstances, this gets out of whack
        insertion_index = min( insertion_index, self.count() )
        
        self.insertTab( insertion_index, page, page_name )
        
        if select_page:
            
            self.setCurrentIndex( insertion_index )
            
        
        self._controller.pub( 'refresh_page_name', page.GetPageKey() )
        self._controller.pub( 'notify_new_pages' )
        
        page.Start()
        
        if select_page:
            
            page.SetSearchFocus()
            
            # this is here for now due to the pagechooser having a double-layer dialog on a booru choice, which messes up some focus inheritance
            
            self._controller.CallLaterQtSafe( self, 0.5, 'set page focus', page.SetSearchFocus )
            
        
        return page
        
    
    def NewPageDuplicateFilter( self, on_deepest_notebook = False ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerDuplicateFilter()
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPageImportGallery( self, page_name = None, on_deepest_notebook = False, select_page = True ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportGallery( page_name = page_name )
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook, select_page = select_page )
        
    
    def NewPageImportSimpleDownloader( self, on_deepest_notebook = False ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportSimpleDownloader()
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPageImportMultipleWatcher( self, page_name = None, url = None, on_deepest_notebook = False, select_page = True ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportMultipleWatcher( page_name = page_name, url = url )
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook, select_page = select_page )
        
    
    def NewPageImportURLs( self, page_name = None, on_deepest_notebook = False, select_page = True ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportURLs( page_name = page_name )
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook, select_page = select_page )
        
    
    def NewPagePetitions( self, service_key, on_deepest_notebook = False ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerPetitions( service_key )
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPageQuery( self, location_context: ClientLocation.LocationContext, initial_hashes = None, initial_predicates = None, page_name = None, on_deepest_notebook = False, do_sort = False, select_page = True ):
        
        if initial_hashes is None:
            
            initial_hashes = []
            
        
        if initial_predicates is None:
            
            initial_predicates = []
            
        
        if page_name is None:
            
            page_name = 'files'
            
        
        search_enabled = len( initial_hashes ) == 0
        
        new_options = self._controller.new_options
        
        tag_service_key = new_options.GetKey( 'default_tag_service_search_page' )
        
        if not self._controller.services_manager.ServiceExists( tag_service_key ):
            
            tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        if location_context.IsAllKnownFiles() and tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            location_context = location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
            
        
        tag_search_context = ClientSearch.TagSearchContext( service_key = tag_service_key )
        
        file_search_context = ClientSearch.FileSearchContext( location_context = location_context, tag_search_context = tag_search_context, predicates = initial_predicates )
        
        management_controller = ClientGUIManagement.CreateManagementControllerQuery( page_name, file_search_context, search_enabled )
        
        page = self.NewPage( management_controller, initial_hashes = initial_hashes, on_deepest_notebook = on_deepest_notebook, select_page = select_page )
        
        if do_sort:
            
            HG.client_controller.pub( 'do_page_sort', page.GetPageKey() )
            
        
        return page
        
    
    def NewPagesNotebook( self, name = 'pages', forced_insertion_index = None, on_deepest_notebook = False, give_it_a_blank_page = True, select_page = True ):
        
        current_page = self.currentWidget()
        
        if on_deepest_notebook and isinstance( current_page, PagesNotebook ):
            
            return current_page.NewPagesNotebook( name = name, forced_insertion_index = forced_insertion_index, on_deepest_notebook = on_deepest_notebook, give_it_a_blank_page = give_it_a_blank_page )
            
        
        self._controller.ResetIdleTimer()
        self._controller.ResetPageChangeTimer()
        
        page = PagesNotebook( self, self._controller, name )
        
        if forced_insertion_index is None:
            
            if self._next_new_page_index is None:
                
                insertion_index = self._GetDefaultPageInsertionIndex()
                
            else:
                
                insertion_index = self._next_new_page_index
                
                self._next_new_page_index = None
                
            
        else:
            
            insertion_index = forced_insertion_index
            
        
        page_name = page.GetName()
        
        self.insertTab( insertion_index, page, page_name )
        
        if select_page:
            
            self.setCurrentIndex( insertion_index )
            
        
        self._controller.pub( 'refresh_page_name', page.GetPageKey() )
        
        if give_it_a_blank_page:
            
            default_location_context = HG.client_controller.services_manager.GetDefaultLocationContext()
            
            page.NewPageQuery( default_location_context )
            
        
        return page
        
    
    def NotifyPageUnclosed( self, page ):
        
        page_key = page.GetPageKey()
        
        for ( index, closed_page_key ) in self._closed_pages:
            
            if page_key == closed_page_key:
                
                page.show()
                
                insert_index = min( index, self.count() )
                
                name = page.GetName()
                
                self.insertTab( insert_index, page, name )
                self.setCurrentIndex( insert_index )
                
                self._controller.pub( 'refresh_page_name', page.GetPageKey() )
                
                self._closed_pages.remove( ( index, closed_page_key ) )
                
                break
                
            
        
    
    def PageHidden( self ):
        
        result = self.currentWidget()
        
        if result is not None:
            
            result.PageHidden()
            
        
    
    def pageJustChanged( self, index ):
        
        old_selection = self._previous_page_index
        selection = index
        
        if old_selection != -1 and old_selection < self.count():
            
            self.widget( old_selection ).PageHidden()
            
        
        if selection != -1:
            
            new_page = self.widget( selection )
            
            new_page.PageShown()
            
        
        self._controller.gui.RefreshStatusBar()
        
        self._previous_page_index = index
        
        self._controller.pub( 'notify_page_change' )
        
    
    def PageShown( self ):
        
        result = self.currentWidget()
        
        if result is not None:
            
            result.PageShown()
            
        
    
    def PresentImportedFilesToPage( self, hashes, page_name ):
        
        hashes = list( hashes )
        
        page = self._GetPageFromName( page_name, only_media_pages = True )
        
        if page is None:
            
            location_context = ClientLocation.GetLocationContextForAllLocalMedia()
            
            page = self.NewPageQuery( location_context, initial_hashes = hashes, page_name = page_name, on_deepest_notebook = True, select_page = False )
            
        else:
            
            def work_callable():
                
                media_results = self._controller.Read( 'media_results', hashes, sorted = True )
                
                return media_results
                
            
            def publish_callable( media_results ):
                
                page.AddMediaResults( media_results )
                
            
            job = ClientGUIAsync.AsyncQtJob( page, work_callable, publish_callable )
            
            job.start()
            
        
        return page
        
    
    def RefreshAllPages( self ):
        
        for page in self._GetPages():
            
            if isinstance( page, PagesNotebook ):
                
                page.RefreshAllPages()
                
            else:
                
                page.RefreshQuery()
                
            
        
    
    def RefreshPageName( self, page_key = None ):
        
        if page_key is None:
            
            for index in range( self.count() ):
                
                self._RefreshPageName( index )
                
            
        else:
            
            for ( index, page ) in enumerate( self._GetPages() ):
                
                do_it = False
                
                if page.GetPageKey() == page_key:
                    
                    do_it = True
                    
                elif isinstance( page, PagesNotebook ) and page.HasPageKey( page_key ):
                    
                    do_it = True
                    
                
                if do_it:
                    
                    self._RefreshPageName( index )
                    
                    break
                    
                
            
        
    
    def SetName( self, name ):
        
        self._name = name
        
    
    def ShowPage( self, showee ):
        
        for ( i, page ) in enumerate( self._GetPages() ):
            
            if isinstance( page, QW.QTabWidget ) and page.HasPage( showee ):
                
                self.setCurrentIndex( i )
                
                page.ShowPage( showee )
                
                break
                
            elif page == showee:
                
                self.setCurrentIndex( i )
                
                break
                
            
        
    
    def TestAbleToClose( self ):
        
        statement = self.GetTestAbleToCloseStatement()
        
        if statement is not None:
            
            message = 'Are you sure you want to close this page of pages?'
            message += os.linesep * 2
            message += statement
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result == QW.QDialog.Rejected:
                
                raise HydrusExceptions.VetoException()
                
            
        
    
    def REPEATINGPageUpdate( self ):
        
        pass
        
    