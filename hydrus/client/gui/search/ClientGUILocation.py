from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon

class EditMultipleLocationContextPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, location_context: ClientLocation.LocationContext, all_known_files_allowed: bool, only_local_file_domains_allowed: bool ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_location_context = location_context
        self._all_known_files_allowed = all_known_files_allowed
        self._only_local_file_domains_allowed = only_local_file_domains_allowed
        
        self._location_list = ClientGUICommon.BetterCheckBoxList( self )
        
        services = ClientLocation.GetPossibleFileDomainServicesInOrder( all_known_files_allowed, only_local_file_domains_allowed )
        
        for service in services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            starts_checked = service_key in self._original_location_context.current_service_keys
            
            self._location_list.Append( name, ( HC.CONTENT_STATUS_CURRENT, service_key ), starts_checked = starts_checked )
            
        
        advanced_mode = CG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
        if advanced_mode and not only_local_file_domains_allowed:
            
            for service in services:
                
                name = service.GetName()
                service_key = service.GetServiceKey()
                
                if service.GetServiceType() in HC.FILE_SERVICES_WITH_NO_DELETE_RECORD:
                    
                    continue
                    
                
                starts_checked = service_key in self._original_location_context.deleted_service_keys
                
                self._location_list.Append( 'deleted from {}'.format( name ), ( HC.CONTENT_STATUS_DELETED, service_key ), starts_checked = starts_checked )
                
            
        
        height_rows = min( 24, self._location_list.count() )
        
        ( gumpf, min_height ) = ClientGUIFunctions.ConvertTextToPixels( self._location_list, ( 24, height_rows + 2 ) )
        
        self._location_list.setMinimumHeight( min_height )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._location_list, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._location_list.checkBoxListChanged.connect( self._ClearSurplusServices )
        
    
    def _ClearSurplusServices( self ):
        
        # if user clicks all known files, then all other services will be wiped
        # all local files should do other file services too
        # and all my files does local file domains
        
        location_context = self._GetValue()
        
        location_context.ClearSurplusLocalFilesServices( CG.client_controller.services_manager.GetServiceType )
        
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
    
    def __init__( self, parent: QW.QWidget, location_context: ClientLocation.LocationContext, is_paired_with_tag_domain = False ):
        
        self._location_context = ClientLocation.LocationContext()
        self._is_paired_with_tag_domain = is_paired_with_tag_domain
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'initialising', self._EditLocation )
        
        self._all_known_files_allowed = True
        self._all_known_files_allowed_only_in_advanced_mode = False
        self._only_importable_domains_allowed = False
        
        self.SetValue( location_context, force_label = True )
        
    
    def _EditLocation( self ):
        
        services = ClientLocation.GetPossibleFileDomainServicesInOrder( self._IsAllKnownFilesServiceTypeAllowed(), self._only_importable_domains_allowed )
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        last_seen_service_type = None
        
        we_have_checked_something = False
        
        for service in services:
            
            if last_seen_service_type is not None and last_seen_service_type != service.GetServiceType():
                
                ClientGUIMenus.AppendSeparator( menu )
                
            
            location_context = ClientLocation.LocationContext.STATICCreateSimple( service.GetServiceKey() )
            
            if service.GetServiceType() == HC.COMBINED_FILE and self._is_paired_with_tag_domain:
                
                name = 'all known files with tags'
                
            else:
                
                name = service.GetName()
                
            
            desc = 'Change the current file domain to {}.'.format( service.GetName() )
            
            if service.GetServiceKey() == CC.COMBINED_DELETED_FILE_SERVICE_KEY:
                
                desc += ' Note this includes files deleted from any domain at all, including those removed from one local file service but still in another local file service.'
                
            
            check_it = location_context == self._location_context
            
            ClientGUIMenus.AppendMenuCheckItem( menu, name, desc, check_it, self.SetValue, location_context )
            
            if check_it:
                
                we_have_checked_something = True
                
            
            last_seen_service_type = service.GetServiceType()
            
            if service.GetServiceType() == HC.LOCAL_FILE_TRASH_DOMAIN:
                
                ClientGUIMenus.AppendSeparator( menu )
                
                location_context = ClientLocation.LocationContext( current_service_keys = ( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY, ), deleted_service_keys = ( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY, ) )
                
                check_it = location_context == self._location_context
                
                ClientGUIMenus.AppendMenuCheckItem( menu, 'all files ever imported or deleted', 'Change the current file domain to all current and deleted files your client has seen.', check_it, self.SetValue, location_context )
                
                if check_it:
                    
                    we_have_checked_something = True
                    
                
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        check_it = not we_have_checked_something
        
        ClientGUIMenus.AppendMenuCheckItem( menu, 'multiple/deleted locations', 'Change the current file domain to something with multiple locations.', check_it, self._EditMultipleLocationContext )
        
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
            
            if self._all_known_files_allowed_only_in_advanced_mode and not CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                
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
        
    
    def SetValue( self, location_context: ClientLocation.LocationContext, force_label = False ):
        
        location_context = location_context.Duplicate()
        
        location_context.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        
        if not force_label:
            
            if location_context == self._location_context:
                
                return
                
            
        
        self._location_context = location_context
        
        if self._location_context.IsAllKnownFiles():
            
            text = 'all known files with tags'
            
        else:
            
            text = self._location_context.ToString( CG.client_controller.services_manager.GetName )
            
        
        self.setText( text )
        
        self.locationChanged.emit( self._location_context )
        
    
