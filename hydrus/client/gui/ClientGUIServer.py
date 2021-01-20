import os
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNetwork
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDefaults
from hydrus.client import ClientParsing
from hydrus.client import ClientPaths
from hydrus.client.gui import ClientGUICommon
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.networking import ClientNetworkingDomain

def LaunchEditAccountsFromAccountIdentifiers( win: QW.QWidget, service_key: bytes, account_identifiers: typing.Collection[ HydrusNetwork.AccountIdentifier ] ):
    
    # async lad that can cancel and all that
    # fetch the accounts, deal with errors, then launch the nulli dialog
    
    pass
    
class ModifyAccountsPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, accounts: typing.Collection[ HydrusNetwork.Account ]  ):
        
        # convert this to accounts, not subject identifiers
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._service = HG.client_controller.services_manager.GetService( service_key )
        self._subject_accounts = accounts
        
        #
        
        self._account_info_panel = ClientGUICommon.StaticBox( self, 'account info' )
        
        self._subject_text = QW.QLabel( self._account_info_panel )
        
        #
        
        self._account_types_panel = ClientGUICommon.StaticBox( self, 'account types' )
        
        self._account_types = QW.QComboBox( self._account_types_panel )
        
        self._account_types_ok = QW.QPushButton( 'OK', self._account_types_panel )
        self._account_types_ok.clicked.connect( self.EventChangeAccountType )
        
        #
        
        self._expiration_panel = ClientGUICommon.StaticBox( self, 'change expiration' )
        
        self._add_to_expires = QW.QComboBox( self._expiration_panel )
        
        self._add_to_expires_ok = QW.QPushButton( 'OK', self._expiration_panel )
        self._add_to_expires_ok.clicked.connect( self.EventAddToExpires )
        
        self._set_expires = QW.QComboBox( self._expiration_panel )
        
        self._set_expires_ok = QW.QPushButton( 'OK', self._expiration_panel )
        self._set_expires_ok.clicked.connect( self.EventSetExpires )
        
        #
        
        self._ban_panel = ClientGUICommon.StaticBox( self, 'bans' )
        
        self._ban = QW.QPushButton( 'ban user', self._ban_panel )
        self._ban.clicked.connect( self.EventBan )        
        QP.SetBackgroundColour( self._ban, (255,0,0) )
        QP.SetForegroundColour( self._ban, (255,255,0) )
        
        self._superban = QW.QPushButton( 'ban user and delete every contribution they have ever made', self._ban_panel )
        self._superban.clicked.connect( self.EventSuperban )        
        QP.SetBackgroundColour( self._superban, (255,0,0) )
        QP.SetForegroundColour( self._superban, (255,255,0) )
        
        self._exit = QW.QPushButton( 'Exit', self )
        self._exit.clicked.connect( self.reject )
        
        #
        
        if len( self._subject_accounts ) == 1:
            
            ( subject_account, ) = self._subject_accounts
            
            #response = self._service.Request( HC.GET, 'account_info', { 'subject_identifier' : subject_identifier } )
            
            #subject_string = str( response[ 'account_info' ] )
            subject_string = 'account info string here'
            
        else:
            
            subject_string = 'modifying ' + HydrusData.ToHumanInt( len( self._subject_accounts ) ) + ' accounts'
            
        
        self._subject_text.setText( subject_string )
        
        #
        
        response = self._service.Request( HC.GET, 'account_types' )
        
        account_types = response[ 'account_types' ]
        
        for account_type in account_types: self._account_types.addItem( account_type.ConvertToString(), account_type )
        
        self._account_types.setCurrentIndex( 0 )
        
        #
        
        for ( label, value ) in HC.lifetimes:
            
            if value is not None:
                
                self._add_to_expires.addItem( label, value ) # don't want 'add no limit'
                
            
        
        self._add_to_expires.setCurrentIndex( 1 ) # three months
        
        for ( label, value ) in HC.lifetimes:
            
            self._set_expires.addItem( label, value )
            
        
        self._set_expires.setCurrentIndex( 1 ) # three months
        
        #
        
        self._account_info_panel.Add( self._subject_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        account_types_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( account_types_hbox, self._account_types, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( account_types_hbox, self._account_types_ok, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._account_types_panel.Add( account_types_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        add_to_expires_box = QP.HBoxLayout()
        
        QP.AddToLayout( add_to_expires_box, QW.QLabel( 'add to expires: ', self._expiration_panel ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( add_to_expires_box, self._add_to_expires, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( add_to_expires_box, self._add_to_expires_ok, CC.FLAGS_CENTER_PERPENDICULAR )
        
        set_expires_box = QP.HBoxLayout()
        
        QP.AddToLayout( set_expires_box, QW.QLabel( 'set expires to: ', self._expiration_panel ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( set_expires_box, self._set_expires, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( set_expires_box, self._set_expires_ok, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._expiration_panel.Add( add_to_expires_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._expiration_panel.Add( set_expires_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._ban_panel.Add( self._ban, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._ban_panel.Add( self._superban, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        QP.AddToLayout( vbox, self._account_info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._account_types_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._expiration_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._ban_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._exit, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( vbox )
        
        size_hint = self.sizeHint()
        
        QP.SetInitialSize( self, size_hint )
        
        HG.client_controller.CallAfterQtSafe( self._exit, self._exit.setFocus, QC.Qt.OtherFocusReason)
        
    
    def _DoModification( self ):
        
        # also make this async. disable the panel UI and show a status text. cancel button too
        
        # change this to saveaccounts or whatever. the previous func changes the accounts, and then we push that change
        # generate accounts, with the modification having occurred
        
        self._service.Request( HC.POST, 'account', { 'accounts' : self._accounts } )
        
        pass # update self._subject_text string here
        
        if len( self._subject_accounts ) > 1:
            
            QW.QMessageBox.information( self, 'Information', 'Done!' )
            
        
    
    def EventAddToExpires( self ):
        
        raise NotImplementedError()
        #self._DoModification( HC.ADD_TO_EXPIRES, timespan = self._add_to_expires.GetClientData( self._add_to_expires.GetSelection() ) )
        
    
    def EventBan( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter reason for the ban.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                raise NotImplementedError()
                #self._DoModification( HC.BAN, reason = dlg.GetValue() )
                
            
        
    
    def EventChangeAccountType( self ):
        
        raise NotImplementedError()
        #self._DoModification( HC.CHANGE_ACCOUNT_TYPE, account_type_key = self._account_types.GetValue() )
        
    
    def EventSetExpires( self ):
        
        expires = QP.GetClientData( self._set_expires, self._set_expires.currentIndex() )
        
        if expires is not None:
            
            expires += HydrusData.GetNow()
            
        
        raise NotImplementedError()
        #self._DoModification( HC.SET_EXPIRES, expires = expires )
        
    
    def EventSuperban( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter reason for the superban.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                raise NotImplementedError()
                #self._DoModification( HC.SUPERBAN, reason = dlg.GetValue() )
                
            
        
    
