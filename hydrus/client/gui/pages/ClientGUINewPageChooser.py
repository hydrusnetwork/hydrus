from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.pages import ClientGUIManagementController
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchTagContext

class DialogPageChooser( ClientGUIDialogs.Dialog ):
    
    def __init__( self, parent, controller: "CG.ClientController.Controller" ):
        
        super().__init__( parent, 'new page', position = 'center' )
        
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
        size_policy.setVerticalPolicy( QW.QSizePolicy.Policy.Expanding )
        size_policy.setHorizontalPolicy( QW.QSizePolicy.Policy.Expanding )
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
        self._button_7.setFocusPolicy( QC.Qt.FocusPolicy.NoFocus )
        self._button_8.setFocusPolicy( QC.Qt.FocusPolicy.NoFocus )
        self._button_9.setFocusPolicy( QC.Qt.FocusPolicy.NoFocus )
        self._button_4.setFocusPolicy( QC.Qt.FocusPolicy.NoFocus )
        self._button_5.setFocusPolicy( QC.Qt.FocusPolicy.NoFocus )
        self._button_6.setFocusPolicy( QC.Qt.FocusPolicy.NoFocus )
        self._button_1.setFocusPolicy( QC.Qt.FocusPolicy.NoFocus )
        self._button_2.setFocusPolicy( QC.Qt.FocusPolicy.NoFocus )
        self._button_3.setFocusPolicy( QC.Qt.FocusPolicy.NoFocus )
        
        gridbox = QP.GridLayout( cols = 3 )
        
        # do not add a flag here! we need the above size policy
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
        
        self._petition_service_keys = [ service.GetServiceKey() for service in CG.client_controller.services_manager.GetServices( HC.REPOSITORIES ) if True in ( service.HasPermission( content_type, HC.PERMISSION_ACTION_MODERATE ) for content_type in HC.SERVICE_TYPES_TO_CONTENT_TYPES[ service.GetServiceType() ] ) ]
        
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
            
            name = CG.client_controller.services_manager.GetService( obj ).GetName()
            
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
                    
                    tag_context = ClientSearchTagContext.TagContext( service_key = tag_service_key )
                    
                    file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, tag_context = tag_context )
                    
                    self._result = ( 'page', ClientGUIManagementController.CreateManagementControllerQuery( page_name, file_search_context, search_enabled ) )
                    
                elif entry_type == 'page_duplicate_filter':
                    
                    self._result = ( 'page', ClientGUIManagementController.CreateManagementControllerDuplicateFilter() )
                    
                elif entry_type == 'pages_notebook':
                    
                    self._result = ( 'pages', None )
                    
                elif entry_type == 'page_import_gallery':
                    
                    self._result = ( 'page', ClientGUIManagementController.CreateManagementControllerImportGallery() )
                    
                elif entry_type == 'page_import_simple_downloader':
                    
                    self._result = ( 'page', ClientGUIManagementController.CreateManagementControllerImportSimpleDownloader() )
                    
                elif entry_type == 'page_import_watcher':
                    
                    self._result = ( 'page', ClientGUIManagementController.CreateManagementControllerImportMultipleWatcher() )
                    
                elif entry_type == 'page_import_urls':
                    
                    self._result = ( 'page', ClientGUIManagementController.CreateManagementControllerImportURLs() )
                    
                elif entry_type == 'page_petitions':
                    
                    petition_service_key = obj
                    
                    self._result = ( 'page', ClientGUIManagementController.CreateManagementControllerPetitions( petition_service_key ) )
                    
                
                self._action_picked = True
                
                self.done( QW.QDialog.DialogCode.Accepted )
                
            
        
    
    def _InitButtons( self, menu_keyword ):
        
        self._command_dict = {}
        
        entries = []
        
        if menu_keyword == 'home':
            
            entries.append( ( 'menu', 'file search' ) )
            entries.append( ( 'menu', 'download' ) )
            
            if len( self._petition_service_keys ) > 0:
                
                entries.append( ( 'menu', 'petitions' ) )
                
            
            entries.append( ( 'menu', 'special' ) )
            
        elif menu_keyword == 'file search':
            
            for service_key in self._controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) ):
                
                entries.append( ( 'page_query', service_key ) )
                
            
            if len( entries ) > 1 and self._controller.new_options.GetBoolean( 'show_all_my_files_on_page_chooser' ):
                
                entries.append( ( 'page_query', CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY ) )
                
            
            entries.append( ( 'page_query', CC.TRASH_SERVICE_KEY ) )
            
            if self._controller.new_options.GetBoolean( 'show_local_files_on_page_chooser' ):
                
                entries.append( ( 'page_query', CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
                
            
            for service_key in self._controller.services_manager.GetServiceKeys( ( HC.FILE_REPOSITORY, ) ):
                
                entries.append( ( 'page_query', service_key ) )
                
            
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
        
        if event.type() == QC.QEvent.Type.WindowDeactivate and not self._action_picked:
            
            self.done( QW.QDialog.DialogCode.Rejected )
            
            return True
            
        else:
            
            return ClientGUIDialogs.Dialog.event( self, event )
            
        
    
    def keyPressEvent( self, event ):
        
        button_id = None
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key == QC.Qt.Key.Key_Up: button_id = 8
        elif key == QC.Qt.Key.Key_Left: button_id = 4
        elif key == QC.Qt.Key.Key_Right: button_id = 6
        elif key == QC.Qt.Key.Key_Down: button_id = 2
        elif key == QC.Qt.Key.Key_1 and modifier == QC.Qt.KeyboardModifier.KeypadModifier: button_id = 1
        elif key == QC.Qt.Key.Key_2 and modifier == QC.Qt.KeyboardModifier.KeypadModifier: button_id = 2
        elif key == QC.Qt.Key.Key_3 and modifier == QC.Qt.KeyboardModifier.KeypadModifier: button_id = 3
        elif key == QC.Qt.Key.Key_4 and modifier == QC.Qt.KeyboardModifier.KeypadModifier: button_id = 4
        elif key == QC.Qt.Key.Key_5 and modifier == QC.Qt.KeyboardModifier.KeypadModifier: button_id = 5
        elif key == QC.Qt.Key.Key_6 and modifier == QC.Qt.KeyboardModifier.KeypadModifier: button_id = 6
        elif key == QC.Qt.Key.Key_7 and modifier == QC.Qt.KeyboardModifier.KeypadModifier: button_id = 7
        elif key == QC.Qt.Key.Key_8 and modifier == QC.Qt.KeyboardModifier.KeypadModifier: button_id = 8
        elif key == QC.Qt.Key.Key_9 and modifier == QC.Qt.KeyboardModifier.KeypadModifier: button_id = 9
        elif key in ( QC.Qt.Key.Key_Enter, QC.Qt.Key.Key_Return ):
            
            # get the 'first', scanning from top-left
            
            for possible_id in ( 7, 8, 9, 4, 5, 6, 1, 2, 3 ):
                
                if possible_id in self._command_dict:
                    
                    button_id = possible_id
                    
                    break
                    
                
            
        elif key == QC.Qt.Key.Key_Escape:
            
            self.done( QW.QDialog.DialogCode.Rejected )
            
            return
            
        else:
            
            event.ignore()
            
        
        if button_id is not None:
            
            self._HitButton( button_id )
            
        
    
    def GetValue( self ):
        
        return self._result
        
    
