import collections
import os

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
from hydrus.client import ClientSearch
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUICanvas
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIManagement
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIResults
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP

RESERVED_SESSION_NAMES = { '', 'just a blank page', 'last session', 'exit session' }

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
        
        repository_petition_permissions = [ ( content_type, HC.PERMISSION_ACTION_OVERRULE ) for content_type in HC.REPOSITORY_CONTENT_TYPES ]
        
        self._petition_service_keys = [ service.GetServiceKey() for service in self._services if service.GetServiceType() in HC.REPOSITORIES and True in ( service.HasPermission( content_type, action ) for ( content_type, action ) in repository_petition_permissions ) ]
        
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
        
        id = int( button.objectName() )
        
        self._command_dict[ id ] = entry
        
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
        
    
    def _HitButton( self, id ):
        
        if id in self._command_dict:
            
            ( entry_type, obj ) = self._command_dict[ id ]
            
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
                        
                    
                    tag_search_context = ClientSearch.TagSearchContext( service_key = tag_service_key )
                    
                    file_search_context = ClientSearch.FileSearchContext( file_service_key = file_service_key, tag_search_context = tag_search_context )
                    
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
        
        id = None
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key == QC.Qt.Key_Up: id = 8
        elif key == QC.Qt.Key_Left: id = 4
        elif key == QC.Qt.Key_Right: id = 6
        elif key == QC.Qt.Key_Down: id = 2
        elif key == QC.Qt.Key_1 and modifier == QC.Qt.KeypadModifier: id = 1
        elif key == QC.Qt.Key_2 and modifier == QC.Qt.KeypadModifier: id = 2
        elif key == QC.Qt.Key_3 and modifier == QC.Qt.KeypadModifier: id = 3
        elif key == QC.Qt.Key_4 and modifier == QC.Qt.KeypadModifier: id = 4
        elif key == QC.Qt.Key_5 and modifier == QC.Qt.KeypadModifier: id = 5
        elif key == QC.Qt.Key_6 and modifier == QC.Qt.KeypadModifier: id = 6
        elif key == QC.Qt.Key_7 and modifier == QC.Qt.KeypadModifier: id = 7
        elif key == QC.Qt.Key_8 and modifier == QC.Qt.KeypadModifier: id = 8
        elif key == QC.Qt.Key_9 and modifier == QC.Qt.KeypadModifier: id = 9
        elif key in ( QC.Qt.Key_Enter, QC.Qt.Key_Return ):
            
            # get the 'first', scanning from top-left
            
            for possible_id in ( 7, 8, 9, 4, 5, 6, 1, 2, 3 ):
                
                if possible_id in self._command_dict:
                    
                    id = possible_id
                    
                    break
                    
                
            
        elif key == QC.Qt.Key_Escape:
            
            self.done( QW.QDialog.Rejected )
            
            return
            
        else:
            
            event.ignore()
            
        
        if id is not None:
            
            self._HitButton( id )
            
        
    
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
        
        self._preview_canvas = ClientGUICanvas.CanvasPanel( self._preview_panel, self._page_key )
        
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
        
        self._ConnectMediaPanelSignals()
        
    
    def _ConnectMediaPanelSignals( self ):
        
        self._media_panel.refreshQuery.connect( self.RefreshQuery )
        self._media_panel.focusMediaChanged.connect( self._preview_canvas.SetMedia )
        self._media_panel.focusMediaCleared.connect( self._preview_canvas.ClearMedia )
        self._media_panel.statusTextChanged.connect( self._SetPrettyStatus )
        
        self._management_panel.ConnectMediaPanelSignals( self._media_panel )
        
    
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
                
                self._controller.CallLaterQtSafe( self, 0.5, clean_up_old_panel )
                
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
        
    
    def GetTotalWeight( self ):
        
        num_hashes = len( self.GetHashes() )
        num_seeds = self._management_controller.GetNumSeeds()
        
        # hashes are smaller, but seeds tend to need more cpu, so we'll just say 1:1 for now
        return num_hashes + num_seeds
        
    
    def IsMultipleWatcherPage( self ):
        
        return self._management_controller.GetType() == ClientGUIManagement.MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER
        
    
    def IsImporter( self ):
        
        return self._management_controller.IsImporter()
        
    
    def IsInitialised( self ):
        
        return self._initialised
        
    
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
            
        
    
    def ShowHideSplit( self ):
        
        if QP.SplitterVisibleCount( self ) > 1:
            
            QP.Unsplit( self, self._search_preview_split )
            
            self._media_panel.SetFocusedMedia( None )
            
        else:
            
            self.SetSplitterPositions()
            
        
    
    def SetMediaFocus( self ):
        
        self._media_panel.setFocus( QC.Qt.OtherFocusReason )
        
    
    def SetName( self, name ):
        
        return self._management_controller.SetPageName( name )
        
    
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
            
        
    
    def PausePlaySearch( self ):
        
        self._management_panel.PausePlaySearch()
        
    
    def _StartInitialMediaResultsLoad( self ):
        
        def qt_code_status( status ):
            
            self._SetPrettyStatus( status )
            
        
        controller = self._controller
        initial_hashes = HydrusData.DedupeList( self._initial_hashes )
        
        def work_callable():
            
            initial_media_results = []
            
            for group_of_initial_hashes in HydrusData.SplitListIntoChunks( initial_hashes, 256 ):
                
                more_media_results = controller.Read( 'media_results', group_of_initial_hashes )
                
                initial_media_results.extend( more_media_results )
                
                status = 'Loading initial files\u2026 ' + HydrusData.ConvertValueRangeToPrettyString( len( initial_media_results ), len( initial_hashes ) )
                
                controller.CallAfterQtSafe( self, qt_code_status, status )
                
                QP.CallAfter( qt_code_status, status )
                
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in initial_media_results }
            
            sorted_initial_media_results = [ hashes_to_media_results[ hash ] for hash in initial_hashes if hash in hashes_to_media_results ]
            
            return sorted_initial_media_results
            
        
        def publish_callable( media_results ):
            
            if self._management_controller.IsImporter():
                
                file_service_key = CC.LOCAL_FILE_SERVICE_KEY
                
            else:
                
                file_service_key = self._management_controller.GetKey( 'file_service' )
                
            
            media_panel = ClientGUIResults.MediaPanelThumbnails( self, self._page_key, file_service_key, media_results )
            
            self._SwapMediaPanel( media_panel )
            
            if len( self._pre_initialisation_media_results ) > 0:
                
                media_panel.AddMediaResults( self._page_key, self._pre_initialisation_media_results )
                
                self._pre_initialisation_media_results = []
                
            
            self._initialised = True
            self._initial_hashes = []
            
            QP.CallAfter( self._management_panel.Start ) # important this is callafter, so it happens after a heavy session load is done
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def Start( self ):
        
        if self._initial_hashes is not None and len( self._initial_hashes ) > 0:
            
            self._StartInitialMediaResultsLoad()
            
        else:
            
            self._initialised = True
            
            QP.CallAfter( self._management_panel.Start ) # important this is callafter, so it happens after a heavy session load is done
            
        
    
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
            self._controller.pub( 'notify_new_undo' )
            
        
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
        
        session = GUISession( 'dupe page session' )
        
        session.AddPageTuple( page )
        
        session = session.Duplicate() # this ensures we are using fresh new objects
        
        self.InsertSessionPageTuples( index + 1, session.GetPageTuples() )
        
    
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
        
    
    def _GetNotebookFromScreenPosition( self, screen_position ):
        
        current_page = self.currentWidget()
        
        if current_page is None or not isinstance( current_page, PagesNotebook ):
            
            return self
            
        else:
            
            tab_index = ClientGUIFunctions.NotebookScreenToHitTest( self, screen_position )
            
            if tab_index != -1:
                
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
        
        can_go_left = tab_index > 0
        can_go_right = tab_index < end_index
        
        click_over_page_of_pages = False
        
        menu = QW.QMenu()
        
        if click_over_tab:
            
            page = self.widget( tab_index )
            
            click_over_page_of_pages = isinstance( page, PagesNotebook )
            
            ClientGUIMenus.AppendMenuItem( menu, 'close page', 'Close this page.', self._ClosePage, tab_index )
            
            if num_pages > 1:
                
                ClientGUIMenus.AppendMenuItem( menu, 'close other pages', 'Close all pages but this one.', self._CloseOtherPages, tab_index )
                
                if can_go_left:
                    
                    ClientGUIMenus.AppendMenuItem( menu, 'close pages to the left', 'Close all pages to the left of this one.', self._CloseLeftPages, tab_index )
                    
                
                if can_go_right:
                    
                    ClientGUIMenus.AppendMenuItem( menu, 'close pages to the right', 'Close all pages to the right of this one.', self._CloseRightPages, tab_index )
                    
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'rename page', 'Rename this page.', self._RenamePage, tab_index )
            
        
        ClientGUIMenus.AppendMenuItem( menu, 'new page', 'Choose a new page.', self._ChooseNewPage )
        
        if click_over_tab:
            
            ClientGUIMenus.AppendMenuItem( menu, 'new page here', 'Choose a new page.', self._ChooseNewPage, tab_index )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'duplicate page', 'Duplicate this page.', self._DuplicatePage, tab_index )
            
            if more_than_one_tab:
                
                ClientGUIMenus.AppendSeparator( menu )
                
                can_home = tab_index > 1
                can_move_left = tab_index > 0
                can_move_right = tab_index < end_index
                can_end = tab_index < end_index - 1
                
                if can_home:
                    
                    ClientGUIMenus.AppendMenuItem( menu, 'move to left end', 'Move this page all the way to the left.', self._ShiftPage, tab_index, new_index=0 )
                    
                
                if can_move_left:
                    
                    ClientGUIMenus.AppendMenuItem( menu, 'move left', 'Move this page one to the left.', self._ShiftPage, tab_index, delta=-1 )
                    
                
                if can_move_right:
                    
                    ClientGUIMenus.AppendMenuItem( menu, 'move right', 'Move this page one to the right.', self._ShiftPage, tab_index, 1 )
                    
                
                if can_end:
                    
                    ClientGUIMenus.AppendMenuItem( menu, 'move to right end', 'Move this page all the way to the right.', self._ShiftPage, tab_index, new_index=end_index )
                    
                
                ClientGUIMenus.AppendSeparator( menu )
                
                submenu = QW.QMenu( menu )
                
                ClientGUIMenus.AppendMenuItem( submenu, 'by most files first', 'Sort these pages according to how many files they appear to have.', self._SortPagesByFileCount, 'desc' )
                ClientGUIMenus.AppendMenuItem( submenu, 'by fewest files first', 'Sort these pages according to how few files they appear to have.', self._SortPagesByFileCount, 'asc' )
                ClientGUIMenus.AppendMenuItem( submenu, 'by name a-z', 'Sort these pages according to how many files they appear to have.', self._SortPagesByName, 'asc' )
                ClientGUIMenus.AppendMenuItem( submenu, 'by name z-a', 'Sort these pages according to how many files they appear to have.', self._SortPagesByName, 'desc' )
                
                ClientGUIMenus.AppendMenu( menu, submenu, 'sort pages' )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'send this page down to a new page of pages', 'Make a new page of pages and put this page in it.', self._SendPageToNewNotebook, tab_index )
            
            if can_go_right:
                
                ClientGUIMenus.AppendMenuItem( menu, 'send pages to the right to a new page of pages', 'Make a new page of pages and put all the pages to the right into it.', self._SendRightPagesToNewNotebook, tab_index )
                
            
            if click_over_page_of_pages and page.count() > 0:
                
                ClientGUIMenus.AppendSeparator( menu )
                
                ClientGUIMenus.AppendMenuItem( menu, 'refresh all this page\'s pages', 'Command every page below this one to refresh.', page.RefreshAllPages )
                
            
        
        existing_session_names = self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
        
        if len( existing_session_names ) > 0 or click_over_page_of_pages:
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        if len( existing_session_names ) > 0:
            
            submenu = QW.QMenu( menu )
            
            for name in existing_session_names:
                
                ClientGUIMenus.AppendMenuItem( submenu, name, 'Load this session here.', self.AppendGUISession, name )
                
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'append session' )
            
        
        if click_over_page_of_pages:
            
            submenu = QW.QMenu( menu )
            
            for name in existing_session_names:
                
                if name in RESERVED_SESSION_NAMES:
                    
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
                
            
        
    
    def AppendGUISession( self, name, load_in_a_page_of_pages = True ):
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetVariable( 'popup_text_1', 'loading session "{}"\u2026'.format( name ) )
        
        HG.client_controller.pub( 'message', job_key )
        
        # get that message showing before we do the work of loading session
        HG.client_controller.app.processEvents()
        
        try:
            
            session = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION, name )
            
        except Exception as e:
            
            HydrusData.ShowText( 'While trying to load session ' + name + ', this error happened:' )
            HydrusData.ShowException( e )
            
            self.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY )
            
            return
            
        
        HG.client_controller.app.processEvents()
        
        if load_in_a_page_of_pages:
            
            destination = self.NewPagesNotebook( name = name, give_it_a_blank_page = False)
            
        else:
            
            destination = self
            
        
        page_tuples = session.GetPageTuples()
        
        HG.client_controller.app.processEvents()
        
        destination.AppendSessionPageTuples( page_tuples )
        
        job_key.Delete()
        
    
    def AppendGUISessionBackup( self, name, timestamp, load_in_a_page_of_pages = True ):
        
        try:
            
            session = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION, name, timestamp )
            
        except Exception as e:
            
            HydrusData.ShowText( 'While trying to load session ' + name + ' (ts ' + str( timestamp ) + ', this error happened:' )
            HydrusData.ShowException( e )
            
            self.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY )
            
            return
            
        
        if load_in_a_page_of_pages:
            
            destination = self.NewPagesNotebook( name = name, give_it_a_blank_page = False)
            
        else:
            
            destination = self
            
        
        page_tuples = session.GetPageTuples()
        
        destination.AppendSessionPageTuples( page_tuples )
        
    
    def AppendSessionPageTuples( self, page_tuples ):
        
        starting_index = self._GetDefaultPageInsertionIndex()
        
        forced_insertion_index = starting_index
        
        self.InsertSessionPageTuples( forced_insertion_index, page_tuples )
        
    
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
        
    
    def mouseReleaseEvent( self, event ):
        
        if event.button() != QC.Qt.RightButton:
            
            QP.TabWidgetWithDnD.mouseReleaseEvent( self, event )
            
            return
            
        
        mouse_position = QG.QCursor.pos()
        
        self._ShowMenu( mouse_position )
        
    
    def ShowMenuFromScreenPosition( self, position ):
        
        notebook = self._GetNotebookFromScreenPosition( position )
        
        notebook._ShowMenu( position )
        
    
    def EventNewPageFromScreenPosition( self, position ):
        
        notebook = self._GetNotebookFromScreenPosition( position )
        
        notebook._ChooseNewPage()
        
    
    def GetAPIInfoDict( self, simple ):
        
        return {}
        
    
    def GetCurrentGUISession( self, name ):
        
        session = GUISession( name )
        
        for page in self._GetPages():
            
            session.AddPageTuple( page )
            
        
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
        
    
    def GetSessionAPIInfoDict( self, is_selected = True ):
        
        current_page = self.currentWidget()
        
        my_pages_list = []
        
        for page in self._GetPages():
            
            page_info_dict = page.GetSessionAPIInfoDict( is_selected = is_selected )
            
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
            
        
    
    def GetTotalWeight( self ):
        
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
        
    
    def InsertSessionPageTuples( self, forced_insertion_index, page_tuples ):
        
        done_first_page = False
        
        for page_tuple in page_tuples:
            
            select_page = not done_first_page
            
            ( page_type, page_data ) = page_tuple
            
            if page_type == 'pages':
                
                ( name, subpage_tuples ) = page_data
                
                try:
                    
                    page = self.NewPagesNotebook( name, forced_insertion_index = forced_insertion_index, give_it_a_blank_page = False, select_page = select_page )
                    
                    page.AppendSessionPageTuples( subpage_tuples )
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                
            elif page_type == 'page':
                
                ( management_controller, initial_hashes ) = page_data
                
                try:
                    
                    self.NewPage( management_controller, initial_hashes = initial_hashes, forced_insertion_index = forced_insertion_index, select_page = select_page )
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                
            
            forced_insertion_index += 1
            
            done_first_page = True
            
        
    
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
            
            self._controller.CallLaterQtSafe(self, 1.0, self.AppendGUISession, name, load_in_a_page_of_pages = False)
            
        else:
            
            self.AppendGUISession( name, load_in_a_page_of_pages = False )
            
        
    
    def MediaDragAndDropDropped( self, source_page_key, hashes ):
        
        source_page = self.GetPageFromPageKey( source_page_key )
        
        if source_page is None:
            
            return
            
        
        screen_position = QG.QCursor.pos()
        
        dest_notebook = self._GetNotebookFromScreenPosition( screen_position )
        
        tab_index = ClientGUIFunctions.NotebookScreenToHitTest( dest_notebook, screen_position )
        
        do_add = True
        # do chase - if we need to chase to an existing dest page on which we dropped files
        # do return - if we need to return to source page if we created a new one
        
        if tab_index == -1 and dest_notebook.currentWidget() and dest_notebook.currentWidget().rect().contains( dest_notebook.currentWidget().mapFromGlobal( screen_position ) ):
            
            dest_page = dest_notebook.currentWidget()
            
        elif tab_index == -1:
            
            dest_page = dest_notebook.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY, initial_hashes = hashes )
            
            do_add = False
            
        else:
            
            dest_page = dest_notebook.widget( tab_index )
            
            if isinstance( dest_page, PagesNotebook ):
                
                result = dest_page.GetCurrentMediaPage()
                
                if result is None:
                    
                    dest_page = dest_page.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY, initial_hashes = hashes )
                    
                    do_add = False
                    
                else:
                    
                    dest_page = result
                    
                
            
        
        if dest_page is None:
            
            return # we somehow dropped onto a new notebook that has no pages
            
        
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
        MAX_TOTAL_PAGES = 500
        
        ( total_active_page_count, total_closed_page_count, total_active_weight, total_closed_weight ) = self._controller.gui.GetTotalPageCounts()
        
        if total_active_page_count + total_closed_page_count >= WARNING_TOTAL_PAGES:
            
            self._controller.gui.DeleteAllClosedPages()
            
        
        if not HG.no_page_limit_mode:
            
            if total_active_page_count >= MAX_TOTAL_PAGES:
                
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
        
        QP.CallAfter( page.Start )
        
        if select_page:
            
            page.SetSearchFocus()
            
            # this is here for now due to the pagechooser having a double-layer dialog on a booru choice, which messes up some focus inheritance
            
            self._controller.CallLaterQtSafe( self, 0.5, page.SetSearchFocus )
            
        
        return page
        
    
    def NewPageDuplicateFilter( self, on_deepest_notebook = False ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerDuplicateFilter()
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook )
        
    
    def NewPageImportGallery( self, on_deepest_notebook = False ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportGallery()
        
        return self.NewPage( management_controller, on_deepest_notebook = on_deepest_notebook )
        
    
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
        
    
    def NewPageQuery( self, file_service_key, initial_hashes = None, initial_predicates = None, page_name = None, on_deepest_notebook = False, do_sort = False, select_page = True ):
        
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
            
        
        if file_service_key == CC.COMBINED_FILE_SERVICE_KEY and tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
            
        
        tag_search_context = ClientSearch.TagSearchContext( service_key = tag_service_key )
        
        file_search_context = ClientSearch.FileSearchContext( file_service_key = file_service_key, tag_search_context = tag_search_context, predicates = initial_predicates )
        
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
            
            page.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY )
            
        
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
            
            page = self.NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY, initial_hashes = hashes, page_name = page_name, on_deepest_notebook = True, select_page = False )
            
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
        
    
class GUISession( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION
    SERIALISABLE_NAME = 'GUI Session'
    SERIALISABLE_VERSION = 4
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._page_tuples = []
        
    
    def _GetPageTuple( self, page ):
        
        if isinstance( page, PagesNotebook ):
            
            name = page.GetName()
            
            page_tuples = [ self._GetPageTuple( subpage ) for subpage in page.GetPages() ]
            
            return ( 'pages', ( name, page_tuples ) )
            
        else:
            
            management_controller = page.GetManagementController()
            
            hashes = list( page.GetHashes() )
            
            return ( 'page', ( management_controller, hashes ) )
            
        
    
    def _GetSerialisableInfo( self ):
        
        def handle_e( page_tuple, e ):
            
            HydrusData.ShowText( 'Attempting to save a page to the session failed! Its data tuple and error follows! Please close it or see if you can clear any potentially invalid data from it!' )
            
            HydrusData.ShowText( page_tuple )
            
            HydrusData.ShowException( e )
            
        
        def GetSerialisablePageTuple( page_tuple ):
            
            ( page_type, page_data ) = page_tuple
            
            if page_type == 'pages':
                
                ( name, page_tuples ) = page_data
                
                serialisable_page_tuples = []
                
                for pt in page_tuples:
                    
                    try:
                        
                        serialisable_page_tuples.append( GetSerialisablePageTuple( pt ) )
                        
                    except Exception as e:
                        
                        handle_e( page_tuple, e )
                        
                    
                
                serialisable_page_data = ( name, serialisable_page_tuples )
                
            elif page_type == 'page':
                
                ( management_controller, hashes ) = page_data
                
                serialisable_management_controller = management_controller.GetSerialisableTuple()
                
                serialisable_hashes = [ hash.hex() for hash in hashes ]
                
                serialisable_page_data = ( serialisable_management_controller, serialisable_hashes )
                
            
            serialisable_tuple = ( page_type, serialisable_page_data )
            
            return serialisable_tuple
            
        
        serialisable_info = []
        
        for page_tuple in self._page_tuples:
            
            try:
                
                serialisable_page_tuple = GetSerialisablePageTuple( page_tuple )
                
                serialisable_info.append( serialisable_page_tuple )
                
            except Exception as e:
                
                handle_e( page_tuple, e )
                
            
        
        return serialisable_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        def handle_e( serialisable_page_tuple, e ):
            
            HydrusData.ShowText( 'A page failed to load! Its serialised data and error follows!' )
            
            HydrusData.ShowText( serialisable_page_tuple )
            
            HydrusData.ShowException( e )
            
        
        def GetPageTuple( serialisable_page_tuple ):
            
            ( page_type, serialisable_page_data ) = serialisable_page_tuple
            
            if page_type == 'pages':
                
                ( name, serialisable_page_tuples ) = serialisable_page_data
                
                page_tuples = []
                
                for spt in serialisable_page_tuples:
                    
                    try:
                        
                        page_tuples.append( GetPageTuple( spt ) )
                        
                    except Exception as e:
                        
                        handle_e( spt, e )
                        
                    
                
                page_data = ( name, page_tuples )
                
            elif page_type == 'page':
                
                ( serialisable_management_controller, serialisable_hashes ) = serialisable_page_data
                
                management_controller = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_management_controller )
                
                hashes = [ bytes.fromhex( hash ) for hash in serialisable_hashes ]
                
                page_data = ( management_controller, hashes )
                
            
            page_tuple = ( page_type, page_data )
            
            return page_tuple
            
        
        for serialisable_page_tuple in serialisable_info:
            
            try:
                
                page_tuple = GetPageTuple( serialisable_page_tuple )
                
                self._page_tuples.append( page_tuple )
                
            except Exception as e:
                
                handle_e( serialisable_page_tuple, e )
                
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            new_serialisable_info = []
            
            for ( page_name, serialisable_management_controller, serialisable_hashes ) in old_serialisable_info:
                
                management_controller = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_management_controller )
                
                management_controller.SetPageName( page_name )
                
                serialisable_management_controller = management_controller.GetSerialisableTuple()
                
                new_serialisable_info.append( ( serialisable_management_controller, serialisable_hashes ) )
                
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            new_serialisable_info = []
            
            for ( serialisable_management_controller, serialisable_hashes ) in old_serialisable_info:
                
                new_serialisable_info.append( ( 'page', ( serialisable_management_controller, serialisable_hashes ) ) )
                
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            def clean_tuple( spt ):
                
                ( page_type, serialisable_page_data ) = spt
                
                if page_type == 'pages':
                    
                    ( name, pages_serialisable_page_tuples ) = serialisable_page_data
                    
                    if name.startswith( '[USER]' ) and len( name ) > 6:
                        
                        name = name[6:]
                        
                    
                    pages_serialisable_page_tuples = [ clean_tuple( pages_spt ) for pages_spt in pages_serialisable_page_tuples ]
                    
                    return ( 'pages', ( name, pages_serialisable_page_tuples ) )
                    
                else:
                    
                    return spt
                    
                
            
            new_serialisable_info = []
            
            serialisable_page_tuples = old_serialisable_info
            
            for serialisable_page_tuple in serialisable_page_tuples:
                
                serialisable_page_tuple = clean_tuple( serialisable_page_tuple )
                
                new_serialisable_info.append( serialisable_page_tuple )
                
            
            return ( 4, new_serialisable_info )
            
        
    
    def AddPageTuple( self, page ):
        
        page_tuple = self._GetPageTuple( page )
        
        self._page_tuples.append( page_tuple )
        
    
    def GetPageTuples( self ):
        
        return self._page_tuples
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION ] = GUISession
