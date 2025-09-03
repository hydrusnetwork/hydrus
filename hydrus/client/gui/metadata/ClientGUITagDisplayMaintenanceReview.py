import time
import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusNumbers

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBook
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon

class ReviewTagDisplayMaintenancePanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        if CG.client_controller.new_options.GetBoolean( 'use_listbook_for_tag_service_panels' ):
            
            self._tag_services = ClientGUIListBook.ListBook( self )
            
        else:
            
            self._tag_services = ClientGUICommon.BetterNotebook( self )
            
        
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._tag_services, 100 )
        
        self._tag_services.setMinimumWidth( min_width )
        
        #
        
        services = list( CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES ) )
        
        default_tag_service_key = CG.client_controller.new_options.GetKey( 'default_tag_service_tab' )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            name = service.GetName()
            
            page = self._Panel( self._tag_services, service_key )
            
            self._tag_services.addTab( page, name )
            
            if service_key == default_tag_service_key:
                
                CG.client_controller.CallAfter( self._tag_services, self._tag_services.setCurrentWidget, page )
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        message = 'Figuring out how tags should appear according to sibling and parent application rules takes time. When you set new rules, the changes in presentation and suggestion do not happen immediately--the client catches up to your settings in the background. This work takes a lot of math and can cause lag.\n\nIf there is a lot of work still to do, your tag suggestions and presentation during the interim may be unusual.'
        
        self._message = ClientGUICommon.BetterStaticText( self, label = message )
        self._message.setWordWrap( True )
        
        self._sync_status = ClientGUICommon.BetterStaticText( self )
        
        self._sync_status.setWordWrap( True )
        
        self._UpdateStatusText()
        
        QP.AddToLayout( vbox, self._message, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._sync_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tag_services, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        CG.client_controller.sub( self, '_UpdateStatusText', 'notify_new_menu_option' )
        
        self._tag_services.currentChanged.connect( self._ServicePageChanged )
        
    
    def _ServicePageChanged( self ):
        
        if CG.client_controller.new_options.GetBoolean( 'save_default_tag_service_tab_on_change' ):
            
            current_page = typing.cast( ReviewTagDisplayMaintenancePanel._Panel, self._tag_services.currentWidget() )
            
            CG.client_controller.new_options.SetKey( 'default_tag_service_tab', current_page.GetServiceKey() )
            
        
    
    def _UpdateStatusText( self ):
        
        if CG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_active' ):
            
            self._sync_status.setText( 'Siblings and parents are set to sync all the time. If there is work to do here, it should be cleared out in real time as you watch.' )
            
            self._sync_status.setObjectName( 'HydrusValid' )
            
        else:
            
            if CG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_idle' ):
                
                self._sync_status.setText( 'Siblings and parents are only set to sync during idle time. If there is work to do here, it should be cleared out when you are not using the client.' )
                
            else:
                
                self._sync_status.setText( 'Siblings and parents are not set to sync in the background at any time. If there is work to do here, you can force it now by clicking \'work now!\' button.' )
                
            
            self._sync_status.setObjectName( 'HydrusWarning' )
            
        
        self._sync_status.style().polish( self._sync_status )
        
    
    class _Panel( QW.QWidget ):
        
        def __init__( self, parent, service_key ):
            
            super().__init__( parent )
            
            self._service_key = service_key
            
            self._siblings_and_parents_st = ClientGUICommon.BetterStaticText( self )
            
            self._progress = ClientGUICommon.TextAndGauge( self )
            
            self._refresh_button = ClientGUICommon.IconButton( self, CC.global_icons().refresh, self._StartRefresh )
            
            self._go_faster_button = ClientGUICommon.BetterButton( self, 'work hard now!', self._SyncFaster )
            
            button_hbox = QP.HBoxLayout()
            
            QP.AddToLayout( button_hbox, self._refresh_button, CC.FLAGS_CENTER )
            QP.AddToLayout( button_hbox, self._go_faster_button, CC.FLAGS_CENTER )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._siblings_and_parents_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._progress, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, button_hbox, CC.FLAGS_ON_RIGHT )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
            self._refresh_values_updater = self._InitialiseRefreshValuesUpdater()
            
            CG.client_controller.sub( self, 'NotifyRefresh', 'notify_new_tag_display_sync_status' )
            CG.client_controller.sub( self, '_StartRefresh', 'notify_new_tag_display_application' )
            
            self._StartRefresh()
            
        
        def _InitialiseRefreshValuesUpdater( self ):
            
            service_key = self._service_key
            
            def loading_callable():
                
                self._progress.SetText( 'refreshing' + HC.UNICODE_ELLIPSIS )
                
                self._refresh_button.setEnabled( False )
                
                # keep button available to slow down
                running_fast_and_button_is_slow = CG.client_controller.tag_display_maintenance_manager.CurrentlyGoingFaster( self._service_key ) and 'slow' in self._go_faster_button.text()
                
                if not running_fast_and_button_is_slow:
                    
                    self._go_faster_button.setEnabled( False )
                    
                
            
            def work_callable( args ):
                
                status = CG.client_controller.Read( 'tag_display_maintenance_status', service_key )
                
                time.sleep( 0.1 ) # for user feedback more than anything
                
                return status
                
            
            def publish_callable( result ):
                
                status = result
                
                num_siblings_to_sync = status[ 'num_siblings_to_sync' ]
                num_parents_to_sync = status[ 'num_parents_to_sync' ]
                
                num_items_to_regen = num_siblings_to_sync + num_parents_to_sync
                
                sync_halted = False
                
                if num_items_to_regen == 0:
                    
                    message = 'All synced!'
                    
                elif num_parents_to_sync == 0:
                    
                    message = '{} siblings to sync.'.format( HydrusNumbers.ToHumanInt( num_siblings_to_sync ) )
                    
                elif num_siblings_to_sync == 0:
                    
                    message = '{} parents to sync.'.format( HydrusNumbers.ToHumanInt( num_parents_to_sync ) )
                    
                else:
                    
                    message = '{} siblings and {} parents to sync.'.format( HydrusNumbers.ToHumanInt( num_siblings_to_sync ), HydrusNumbers.ToHumanInt( num_parents_to_sync ) )
                    
                
                if len( status[ 'waiting_on_tag_repos' ] ) > 0:
                    
                    message += '\n' * 2
                    message += '\n'.join( status[ 'waiting_on_tag_repos' ] )
                    
                    sync_halted = True
                    
                
                self._siblings_and_parents_st.setText( message )
                
                #
                
                num_actual_rows = status[ 'num_actual_rows' ]
                num_ideal_rows = status[ 'num_ideal_rows' ]
                
                if num_items_to_regen == 0:
                    
                    if num_ideal_rows == 0:
                        
                        message = 'No siblings/parents applying to this service.'
                        
                    else:
                        
                        message = '{} rules, all synced!'.format( HydrusNumbers.ToHumanInt( num_ideal_rows ) )
                        
                    
                    value = 1
                    range = 1
                    
                    sync_work_to_do = False
                    
                else:
                    
                    value = None
                    range = None
                    
                    if num_ideal_rows == 0:
                        
                        message = 'Removing all siblings/parents, {} rules remaining.'.format( HydrusNumbers.ToHumanInt( num_actual_rows ) )
                        
                    else:
                        
                        message = '{} rules applied now, moving to {}.'.format( HydrusNumbers.ToHumanInt( num_actual_rows ), HydrusNumbers.ToHumanInt( num_ideal_rows ) )
                        
                        if num_actual_rows <= num_ideal_rows:
                            
                            value = num_actual_rows
                            range = num_ideal_rows
                            
                        
                    
                    sync_work_to_do = True
                    
                
                self._progress.SetValue( message, value, range )
                
                self._refresh_button.setEnabled( True )
                
                self._go_faster_button.setVisible( sync_work_to_do and not sync_halted )
                self._go_faster_button.setEnabled( sync_work_to_do and not sync_halted )
                
                if CG.client_controller.tag_display_maintenance_manager.CurrentlyGoingFaster( self._service_key ):
                    
                    self._go_faster_button.setText( 'slow down!' )
                    
                else:
                    
                    if not CG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_active' ):
                        
                        self._go_faster_button.setText( 'work now!' )
                        
                    else:
                        
                        self._go_faster_button.setText( 'work hard now!' )
                        
                    
                
            
            return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
            
        
        def _StartRefresh( self ):
            
            self._refresh_values_updater.update()
            
        
        def _SyncFaster( self ):
            
            CG.client_controller.tag_display_maintenance_manager.FlipSyncFaster( self._service_key )
            
            self._StartRefresh()
            
        
        def GetServiceKey( self ):
            
            return self._service_key
            
        
        def NotifyRefresh( self, service_key ):
            
            if service_key == self._service_key:
                
                self._StartRefresh()
                
            
        
    
