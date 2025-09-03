import re

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIFrames
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIRegex

class Dialog( QP.Dialog ):
    
    def __init__( self, parent, title, style = QC.Qt.WindowType.Dialog, position = 'topleft' ):

        super().__init__( parent )
        
        self.setWindowFlags( style )
        
        self.setWindowTitle( title )
        
        if parent is not None and position == 'topleft':
            
            parent_tlw = self.parentWidget().window()                
            
            pos = parent_tlw.pos() + QC.QPoint( 50, 50 )
            
            self.move( pos )
            
        
        self.setWindowFlag( QC.Qt.WindowType.WindowContextHelpButtonHint, on = False )
        
        self._new_options = CG.client_controller.new_options
        
        self.setWindowIcon( CC.global_icons().hydrus_frame )
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
        if parent is not None and position == 'center':
            
            CG.client_controller.CallAfter( self, QP.CenterOnWindow, parent, self )
            
        
        CG.client_controller.ResetIdleTimer()
        
    
    def keyPressEvent( self, event ):
        
        shortcut = ClientGUIShortcuts.ConvertKeyEventToShortcut( event )
        
        escape_shortcut = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_ESCAPE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] )
        command_w_shortcut = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'W' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] )
        
        if shortcut == escape_shortcut or ( HC.PLATFORM_MACOS and shortcut == command_w_shortcut ):
            
            self.done( QW.QDialog.DialogCode.Rejected )
            
        else:
            
            QP.Dialog.keyPressEvent( self, event )
            
        
    
    def SetInitialSize( self, size: QC.QSize ):
        
        display_size = ClientGUIFunctions.GetDisplaySize( self )
        
        width = min( display_size.width(), size.width() )
        height = min( display_size.height(), size.height() )
        
        self.resize( QC.QSize( width, height ) )
        
        min_width = min( 240, width )
        min_height = min( 240, height )
        
        self.setMinimumSize( QC.QSize( min_width, min_height ) )
        
    
class DialogChooseNewServiceMethod( Dialog ):
    
    def __init__( self, parent ):
        
        super().__init__( parent, 'how to set up the account?', position = 'center' )
        
        register_message = 'I want to initialise a new account with the server. I have a registration token (a hexadecimal key starting with \'r\').'
        
        self._register = QW.QPushButton( register_message, self )
        self._register.clicked.connect( self.EventRegister )
        
        setup_message = 'The account is already initialised; I just want to add it to this client. I have a normal access key.'
        
        self._setup = QW.QPushButton( setup_message, self )
        self._setup.clicked.connect( self.accept )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._register, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        st = ClientGUICommon.BetterStaticText( self, '-or-' )
        
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._setup, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        size_hint = self.sizeHint()
        
        QP.SetInitialSize( self, size_hint )
        
        self._should_register = False
        
        ClientGUIFunctions.SetFocusLater( self._register )
        
    
    def EventRegister( self ):
        
        self._should_register = True
        
        self.done( QW.QDialog.DialogCode.Accepted )
        
    
    def GetRegister( self ):
        
        return self._should_register
        
    
class DialogGenerateNewAccounts( Dialog ):
    
    def __init__( self, parent, service_key ):
        
        super().__init__( parent, 'configure new accounts' )
        
        self._service_key = service_key
        
        self._num = ClientGUICommon.BetterSpinBox( self, min=1, max=10000, width = 80 )
        
        self._account_types = ClientGUICommon.BetterChoice( self )
        
        self._lifetime = ClientGUICommon.BetterChoice( self )
        
        self._ok = QW.QPushButton( 'OK', self )
        self._ok.clicked.connect( self.EventOK )
        self._ok.setObjectName( 'HydrusAccept' )
        
        self._cancel = QW.QPushButton( 'Cancel', self )
        self._cancel.clicked.connect( self.reject )
        self._cancel.setObjectName( 'HydrusCancel' )
        
        #
        
        self._num.setValue( 1 )
        
        service = CG.client_controller.services_manager.GetService( service_key )
        
        response = service.Request( HC.GET, 'account_types' )
        
        account_types = response[ 'account_types' ]
        
        for account_type in account_types:
            
            self._account_types.addItem( account_type.GetTitle(), account_type )
            
        
        self._account_types.setCurrentIndex( 0 )
        
        for ( s, value ) in HC.lifetimes:
            
            self._lifetime.addItem( s, value )
            
        
        self._lifetime.setCurrentIndex( 3 ) # one year
        
        #
        
        ctrl_box = QP.HBoxLayout()
        
        QP.AddToLayout( ctrl_box, ClientGUICommon.BetterStaticText(self,'generate'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( ctrl_box, self._num, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( ctrl_box, self._account_types, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( ctrl_box, ClientGUICommon.BetterStaticText(self,'accounts, to expire in'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( ctrl_box, self._lifetime, CC.FLAGS_CENTER_PERPENDICULAR )
        
        b_box = QP.HBoxLayout()
        QP.AddToLayout( b_box, self._ok, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( b_box, self._cancel, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, ctrl_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, b_box, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
        size_hint = self.sizeHint()
        
        QP.SetInitialSize( self, size_hint )
        
        ClientGUIFunctions.SetFocusLater( self._ok )
        
    
    def EventOK( self ):
        
        num = self._num.value()
        
        account_type = self._account_types.GetValue()
        
        account_type_key = account_type.GetAccountTypeKey()
        
        lifetime = self._lifetime.GetValue()
        
        if lifetime is None:
            
            expires = None
            
        else:
            
            expires = HydrusTime.GetNow() + lifetime
            
        
        service = CG.client_controller.services_manager.GetService( self._service_key )
        
        try:
            
            request_args = { 'num' : num, 'account_type_key' : account_type_key }
            
            if expires is not None:
                
                request_args[ 'expires' ] = expires
                
            
            response = service.Request( HC.GET, 'registration_keys', request_args )
            
            registration_keys = response[ 'registration_keys' ]
            
            ClientGUIFrames.ShowKeys( 'registration', registration_keys )
            
        finally:
            
            self.done( QW.QDialog.DialogCode.Accepted )
            
        
    

class DialogInputNamespaceRegex( Dialog ):
    
    def __init__( self, parent, namespace = '', regex = '' ):
        
        super().__init__( parent, 'configure quick namespace' )
        
        self._namespace = QW.QLineEdit( self )
        
        self._regex = ClientGUIRegex.RegexInput( self )
        
        self._ok = QW.QPushButton( 'OK', self )
        self._ok.clicked.connect( self.EventOK )
        self._ok.setObjectName( 'HydrusAccept' )
        
        self._cancel = QW.QPushButton( 'Cancel', self )
        self._cancel.clicked.connect( self.reject )
        self._cancel.setObjectName( 'HydrusCancel' )
        
        #
        
        self._namespace.setText( namespace )
        self._regex.SetValue( regex )
        
        #
        
        control_box = QP.HBoxLayout()
        
        QP.AddToLayout( control_box, self._namespace, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( control_box, ClientGUICommon.BetterStaticText(self,':'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( control_box, self._regex, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        b_box = QP.HBoxLayout()
        QP.AddToLayout( b_box, self._ok, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( b_box, self._cancel, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        intro = r'Put the namespace (e.g. page) on the left.' + '\n' + r'Put the regex (e.g. [1-9]+\d*(?=.{4}$)) on the right.' + '\n' + r'All files will be tagged with "namespace:regex".'
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self,intro), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, control_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, b_box, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
        size_hint = self.sizeHint()
        
        QP.SetInitialSize( self, size_hint )
        
        ClientGUIFunctions.SetFocusLater( self._ok )
        
    
    def EventOK( self ):
        
        ( namespace, regex ) = self.GetInfo()
        
        if namespace == '':
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Please enter something for the namespace.' )
            
            return
            
        
        try:
            
            re.compile( regex )
            
        except Exception as e:
            
            text = 'That regex would not compile!'
            text += '\n' * 2
            text += str( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Error', text )
            
            return
            
        
        self.done( QW.QDialog.DialogCode.Accepted )
        
    
    def GetInfo( self ):
        
        namespace = self._namespace.text()
        
        regex = self._regex.GetValue()
        
        return ( namespace, regex )
        
    

class DialogInputTags( Dialog ):
    
    def __init__( self, parent, service_key, tag_display_type, tags, message = '' ):
        
        super().__init__( parent, 'input tags' )
        
        self._service_key = service_key
        
        self._tags = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, service_key, tag_display_type = tag_display_type )
        
        default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
        
        self._tag_autocomplete = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterTags, default_location_context, service_key, show_paste_button = True )
        
        self._tags.tagsChanged.connect( self._tag_autocomplete.SetContextTags )
        self._tag_autocomplete.externalCopyKeyPressEvent.connect( self._tags.keyPressEvent )
        
        self._tag_autocomplete.nullEntered.connect( self.OK )
        
        self._ok = ClientGUICommon.BetterButton( self, 'OK', self.done, QW.QDialog.DialogCode.Accepted )
        self._ok.setObjectName( 'HydrusAccept' )
        
        self._cancel = QW.QPushButton( 'Cancel', self )
        self._cancel.clicked.connect( self.reject )
        self._cancel.setObjectName( 'HydrusCancel' )
        
        #
        
        self._tags.SetTags( tags )
        
        #
        
        b_box = QP.HBoxLayout()
        
        QP.AddToLayout( b_box, self._ok, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( b_box, self._cancel, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        if message != '':
            
            st = ClientGUICommon.BetterStaticText( self, message )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        QP.AddToLayout( vbox, self._tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._tag_autocomplete, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, b_box, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
        size_hint = self.sizeHint()
        
        size_hint.setWidth( max( size_hint.width(), 300 ) )
        
        self._tag_autocomplete.tagsPasted.connect( self.EnterTagsOnlyAdd )
        
        QP.SetInitialSize( self, size_hint )
        
        ClientGUIFunctions.SetFocusLater( self._tag_autocomplete )
        

    def EnterTags( self, tags ):
        
        if len( tags ) > 0:
            
            self._tags.EnterTags( tags )
            
        
    
    def EnterTagsOnlyAdd( self, tags ):
        
        current_tags = self._tags.GetTags()
        
        tags = { tag for tag in tags if tag not in current_tags }
        
        if len( tags ) > 0:
            
            self.EnterTags( tags )
            
        
    
    def GetTags( self ):
        
        return self._tags.GetTags()
        
    
    def OK( self ):
        
        self.done( QW.QDialog.DialogCode.Accepted )
        
    
class DialogInputUPnPMapping( Dialog ):
    
    def __init__( self, parent, external_port, protocol_type, internal_port, description, duration ):
        
        super().__init__( parent, 'configure upnp mapping' )
        
        self._external_port = ClientGUICommon.BetterSpinBox( self, min=0, max=65535 )
        
        self._protocol_type = ClientGUICommon.BetterChoice( self )
        self._protocol_type.addItem( 'TCP', 'TCP' )
        self._protocol_type.addItem( 'UDP', 'UDP' )
        
        self._internal_port = ClientGUICommon.BetterSpinBox( self, min=0, max=65535 )
        self._description = QW.QLineEdit( self )
        self._duration = ClientGUICommon.BetterSpinBox( self, min=0, max=86400 )
        
        self._ok = ClientGUICommon.BetterButton( self, 'OK', self.done, QW.QDialog.DialogCode.Accepted )
        self._ok.setObjectName( 'HydrusAccept' )
        
        self._cancel = QW.QPushButton( 'Cancel', self )
        self._cancel.clicked.connect( self.reject )
        self._cancel.setObjectName( 'HydrusCancel' )
        
        #
        
        self._external_port.setValue( external_port )
        
        if protocol_type == 'TCP': self._protocol_type.setCurrentIndex( 0 )
        elif protocol_type == 'UDP': self._protocol_type.setCurrentIndex( 1 )
        
        self._internal_port.setValue( internal_port )
        self._description.setText( description )
        self._duration.setValue( duration )
        
        #
        
        rows = []
        
        rows.append( ( 'external port: ', self._external_port ) )
        rows.append( ( 'protocol type: ', self._protocol_type ) )
        rows.append( ( 'internal port: ', self._internal_port ) )
        rows.append( ( 'description: ', self._description ) )
        rows.append( ( 'duration (0 = indefinite): ', self._duration ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        b_box = QP.HBoxLayout()
        QP.AddToLayout( b_box, self._ok, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( b_box, self._cancel, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, b_box, CC.FLAGS_ON_RIGHT )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        size_hint = self.sizeHint()
        
        QP.SetInitialSize( self, size_hint )
        
        ClientGUIFunctions.SetFocusLater( self._ok )
        
    
    def GetInfo( self ):
        
        external_port = self._external_port.value()
        protocol_type = self._protocol_type.GetValue()
        internal_port = self._internal_port.value()
        description = self._description.text()
        duration = self._duration.value()
        
        return ( external_port, protocol_type, internal_port, description, duration )
        
    
class DialogSelectFromURLTree( Dialog ):
    
    def __init__( self, parent, url_tree ):
        
        super().__init__( parent, 'select items' )
        
        self._tree = QP.TreeWidgetWithInheritedCheckState( self )
        
        self._ok = ClientGUICommon.BetterButton( self, 'OK', self.done, QW.QDialog.DialogCode.Accepted )
        self._ok.setObjectName( 'HydrusAccept' )
        
        self._cancel = QW.QPushButton( 'Cancel', self )
        self._cancel.clicked.connect( self.reject )
        self._cancel.setObjectName( 'HydrusCancel' )
        
        #
        
        ( text_gumpf, name, size, children ) = url_tree
        
        root_name = self._RenderItemName( name, size )
        
        root_item = QW.QTreeWidgetItem()
        root_item.setText( 0, root_name )
        root_item.setCheckState( 0, QC.Qt.CheckState.Checked )
        self._tree.addTopLevelItem( root_item )
        
        self._AddDirectory( root_item, children )
        
        root_item.setExpanded( True )
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._ok, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._cancel, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._tree, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
        size_hint = self.sizeHint()
        
        size_hint.setWidth( max( size_hint.width(), 640 ) )
        size_hint.setHeight( max( size_hint.height(), 640 ) )
        
        QP.SetInitialSize( self, size_hint )
        
    
    def _AddDirectory( self, root, children ):
        
        for ( child_type, name, size, data ) in children:
            
            item_name = self._RenderItemName( name, size )
            
            if child_type == 'file':
                
                item = QW.QTreeWidgetItem()
                item.setText( 0, item_name )
                item.setCheckState( 0, root.checkState( 0 ) )
                item.setData( 0, QC.Qt.ItemDataRole.UserRole, data )
                root.addChild( item )
                
            else:
                
                subroot = QW.QTreeWidgetItem()
                subroot.setText( 0, item_name )
                subroot.setCheckState( 0, root.checkState( 0 ) )
                root.addChild( subroot )
                
                self._AddDirectory( subroot, data )
                
            
        
    
    def _GetSelectedChildrenData( self, parent_item ):
        
        result = []
        
        for i in range( parent_item.childCount() ):
            
            child_item = parent_item.child( i )
            
            if child_item.checkState( 0 ) == QC.Qt.CheckState.Checked:
                
                data = child_item.data( 0, QC.Qt.ItemDataRole.UserRole )
                
                if data is not None:
                    
                    result.append( data )
                    
                
            
            result.extend( self._GetSelectedChildrenData( child_item ) )
            
        
        return result
        
    
    def _RenderItemName( self, name, size ):
        
        return name + ' - ' + HydrusData.ToHumanBytes( size )
        
    
    def GetURLs( self ):
        
        root_item = self._tree.topLevelItem( 0 )
        
        urls = self._GetSelectedChildrenData( root_item )
        
        return urls
        
    
