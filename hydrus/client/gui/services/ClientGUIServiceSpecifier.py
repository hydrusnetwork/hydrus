from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientServices
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon

class EditServiceSpecifierPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, service_specifier: ClientServices.ServiceSpecifier, allowed_service_types: list[ int ] ):
        
        super().__init__( parent )
        
        self._specifier_type_choice = ClientGUICommon.BetterChoice( self )
        
        self._specifier_type_choice.addItem( 'service type', 'service_type' )
        self._specifier_type_choice.addItem( 'service', 'service_key' )
        
        self._service_types_radiobox = ClientGUICommon.BetterCheckBoxList( self )
        
        for service_type in allowed_service_types:
            
            self._service_types_radiobox.Append( HC.service_string_lookup_short[ service_type ], service_type )
            
        
        self._service_keys_radiobox = ClientGUICommon.BetterCheckBoxList( self )
        
        allowed_services = CG.client_controller.services_manager.GetServices( allowed_service_types )
        
        for service in allowed_services:
            
            name = service.GetName()
            
            if len( allowed_service_types ) > 1:
                
                name = HC.service_string_lookup_short[ service.GetServiceType() ] + ': ' + name
                
            
            self._service_keys_radiobox.Append( name, service.GetServiceKey() )
            
        
        #
        
        service_types = service_specifier.GetServiceTypes()
        service_keys = service_specifier.GetServiceKeys()
        
        if len( service_keys ) > 0:
            
            self._specifier_type_choice.SetValue( 'service_key' )
            
            self._service_keys_radiobox.SetValue( service_keys )
            
        else:
            
            self._specifier_type_choice.SetValue( 'service_type' )
            
            self._service_types_radiobox.SetValue( service_types )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._specifier_type_choice, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._service_types_radiobox, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._service_keys_radiobox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        self._specifier_type_choice.currentIndexChanged.connect( self._UpdateWidgets )
        
        self._UpdateWidgets()
        
    
    def _UpdateWidgets( self ):
        
        we_service_type = self._specifier_type_choice.GetValue() == 'service_type'
        
        self._service_types_radiobox.setVisible( we_service_type )
        self._service_keys_radiobox.setVisible( not we_service_type )
        
    
    def GetValue( self ):
        
        service_types = None
        service_keys = None
        
        if self._specifier_type_choice.GetValue() == 'service_type':
            
            service_types = self._service_types_radiobox.GetValue()
            
        else:
            
            service_keys = self._service_keys_radiobox.GetValue()
            
        
        return ClientServices.ServiceSpecifier( service_types = service_types, service_keys = service_keys )
        
    

class ServiceSpecifierButton( ClientGUICommon.BetterButton ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, service_specifier: ClientServices.ServiceSpecifier, allowed_service_types: list[ int ] ):
        
        super().__init__( parent, 'initialising', self._Edit )
        
        self._service_specifier = service_specifier
        self._allowed_service_types = allowed_service_types
        
        self.SetValue( service_specifier )
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit service specifier' ) as dlg:
            
            panel = EditServiceSpecifierPanel( dlg, self._service_specifier, self._allowed_service_types )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                value = panel.GetValue()
                
                self.SetValue( value )
                
                self.valueChanged.emit()
                
            
        
    
    def _RefreshLabel( self ):
        
        text = self._service_specifier.ToString()
        
        self.setText( text )
        
    
    def GetValue( self ):
        
        return self._service_specifier
        
    
    def SetValue( self, value ):
        
        self._service_specifier = value
        
        self._RefreshLabel()
        
    
