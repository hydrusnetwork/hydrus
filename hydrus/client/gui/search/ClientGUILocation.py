from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon

def GetPossibleFileDomainServicesInOrder( all_known_files_allowed: bool, only_local_file_domains_allowed: bool ):
    
    services_manager = HG.client_controller.services_manager
    
    if only_local_file_domains_allowed:
        
        service_types_in_order = [ HC.LOCAL_FILE_DOMAIN ]
        
    else:
        
        service_types_in_order = [ HC.LOCAL_FILE_DOMAIN, HC.LOCAL_FILE_TRASH_DOMAIN ]
        
        advanced_mode = HG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
        if advanced_mode:
            
            service_types_in_order.append( HC.COMBINED_LOCAL_FILE )
            
        
        service_types_in_order.append( HC.FILE_REPOSITORY )
        service_types_in_order.append( HC.IPFS )
        
        if all_known_files_allowed:
            
            service_types_in_order.append( HC.COMBINED_FILE )
            
        
    
    services = services_manager.GetServices( service_types_in_order )
    
    if only_local_file_domains_allowed or not advanced_mode:
        
        services = [ service for service in services if service.GetServiceKey() != CC.LOCAL_UPDATE_SERVICE_KEY ]
        
    
    return services
    

class EditMultipleLocationContextPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, location_context: ClientLocation.LocationContext, all_known_files_allowed: bool, only_local_file_domains_allowed: bool ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_location_context = location_context
        self._all_known_files_allowed = all_known_files_allowed
        self._only_local_file_domains_allowed = only_local_file_domains_allowed
        
        self._location_list = ClientGUICommon.BetterCheckBoxList( self )
        
        services = GetPossibleFileDomainServicesInOrder( all_known_files_allowed, only_local_file_domains_allowed )
        
        for service in services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            starts_checked = service_key in self._original_location_context.current_service_keys
            
            self._location_list.Append( name, ( HC.CONTENT_STATUS_CURRENT, service_key ), starts_checked = starts_checked )
            
        
        advanced_mode = HG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
        if advanced_mode and not only_local_file_domains_allowed:
            
            for service in services:
                
                name = service.GetName()
                service_key = service.GetServiceKey()
                
                if service_key in ( CC.COMBINED_FILE_SERVICE_KEY, CC.TRASH_SERVICE_KEY ):
                    
                    continue
                    
                
                starts_checked = service_key in self._original_location_context.deleted_service_keys
                
                self._location_list.Append( 'deleted from {}'.format( name ), ( HC.CONTENT_STATUS_DELETED, service_key ), starts_checked = starts_checked )
                
            
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._location_list, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._location_list.checkBoxListChanged.connect( self._ClearSurplusServices )
        
    
    def _ClearSurplusServices( self ):
        
        # if user clicks all known files, then all other services will be wiped
        # all local files should do other file services too
        
        location_context = self._GetValue()
        
        location_context.ClearSurplusLocalFilesServices( HG.client_controller.services_manager.GetServiceType )
        
        if set( location_context.GetStatusesAndServiceKeysList() ) != set( self._location_list.GetValue() ):
            
            self._SetValue( location_context )
            
        
    
    def _GetValue( self ):
        
        statuses_and_service_keys = self._location_list.GetValue()
        
        current_service_keys = { service_key for ( status, service_key ) in statuses_and_service_keys if status == HC.CONTENT_STATUS_CURRENT }
        deleted_service_keys = { service_key for ( status, service_key ) in statuses_and_service_keys if status == HC.CONTENT_STATUS_DELETED }
        
        location_context = ClientLocation.LocationContext( current_service_keys = current_service_keys, deleted_service_keys = deleted_service_keys )
        
        return location_context
        
    
    def _SetValue( self, location_context: ClientLocation.LocationContext ):
        
        self._location_list.blockSignals( True )
        
        statuses_and_service_keys = location_context.GetStatusesAndServiceKeysList()
        
        self._location_list.SetValue( statuses_and_service_keys )
        
        self._location_list.blockSignals( False )
        
    
    def GetValue( self ) -> ClientLocation.LocationContext:
        
        location_context = self._GetValue()
        
        return location_context
        
    
    def SetValue( self, location_context: ClientLocation.LocationContext ):
        
        self._SetValue( location_context )
        
        self._location_list.checkBoxListChanged.emit()
        
    
class LocationSearchContextButton( ClientGUICommon.BetterButton ):
    
    locationChanged = QC.Signal( ClientLocation.LocationContext )
    
    def __init__( self, parent: QW.QWidget, location_context: ClientLocation.LocationContext ):
        
        self._location_context = location_context
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'initialising', self._EditLocation )
        
        self._all_known_files_allowed = True
        self._all_known_files_allowed_only_in_advanced_mode = False
        self._only_importable_domains_allowed = False
        
        self.SetValue( location_context )
        
    
    def _EditLocation( self ):
        
        services = GetPossibleFileDomainServicesInOrder( self._IsAllKnownFilesServiceTypeAllowed(), self._only_importable_domains_allowed )
        
        menu = QW.QMenu()
        
        for service in services:
            
            location_context = ClientLocation.LocationContext.STATICCreateSimple( service.GetServiceKey() )
            
            ClientGUIMenus.AppendMenuItem( menu, service.GetName(), 'Change the current file domain to {}.'.format( service.GetName() ), self.SetValue, location_context )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'multiple locations', 'Change the current file domain to something with multiple locations.', self._EditMultipleLocationContext )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _EditMultipleLocationContext( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit multiple location' ) as dlg:
            
            panel = EditMultipleLocationContextPanel( dlg, self._location_context, self._IsAllKnownFilesServiceTypeAllowed(), self._only_importable_domains_allowed )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                location_context = panel.GetValue()
                
                self.SetValue( location_context )
                
            
        
    
    def _IsAllKnownFilesServiceTypeAllowed( self ) -> bool:
        
        if self._all_known_files_allowed:
            
            if self._all_known_files_allowed_only_in_advanced_mode and not HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                
                return False
                
            else:
                
                return True
                
            
        else:
            
            return False
            
        
    
    def GetValue( self ) -> ClientLocation.LocationContext:
        
        return self._location_context
        
    
    def SetOnlyImportableDomainsAllowed( self, only_importable_domains_allowed: bool ):
        
        self._only_importable_domains_allowed = only_importable_domains_allowed
        
    
    def SetAllKnownFilesAllowed( self, all_known_files_allowed: bool, all_known_files_allowed_only_in_advanced_mode: bool ):
        
        self._all_known_files_allowed = all_known_files_allowed
        self._all_known_files_allowed_only_in_advanced_mode = all_known_files_allowed_only_in_advanced_mode
        
    
    def SetValue( self, location_context: ClientLocation.LocationContext ):
        
        location_context = location_context.Duplicate()
        
        location_context.FixMissingServices( HG.client_controller.services_manager.FilterValidServiceKeys )
        
        self._location_context = location_context
        
        self.setText( self._location_context.ToString( HG.client_controller.services_manager.GetName ) )
        
        self.locationChanged.emit( self._location_context )
        
