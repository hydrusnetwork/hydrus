import collections
import collections.abc
import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon

class EditTagDisplayApplication( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys ):
        
        master_service_keys_to_sibling_applicable_service_keys = collections.defaultdict( list, master_service_keys_to_sibling_applicable_service_keys )
        master_service_keys_to_parent_applicable_service_keys = collections.defaultdict( list, master_service_keys_to_parent_applicable_service_keys )
        
        super().__init__( parent )
        
        self._tag_services = ClientGUICommon.BetterNotebook( self )
        
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._tag_services, 100 )
        
        self._tag_services.setMinimumWidth( min_width )
        
        #
        
        services = list( CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES ) )
        
        default_tag_service_key = CG.client_controller.new_options.GetKey( 'default_tag_service_tab' )
        
        for service in services:
            
            master_service_key = service.GetServiceKey()
            name = service.GetName()
            
            sibling_applicable_service_keys = master_service_keys_to_sibling_applicable_service_keys[ master_service_key ]
            parent_applicable_service_keys = master_service_keys_to_parent_applicable_service_keys[ master_service_key ]
            
            page = self._Panel( self._tag_services, master_service_key, sibling_applicable_service_keys, parent_applicable_service_keys )
            
            self._tag_services.addTab( page, name )
            
            if master_service_key == default_tag_service_key:
                
                # Py 3.11/PyQt6 6.5.0/two tabs/total tab characters > ~12/select second tab during init = first tab disappears bug
                CG.client_controller.CallAfter( self._tag_services, self._tag_services.setCurrentWidget, page )
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        warning = 'THIS IS COMPLICATED, THINK CAREFULLY'
        
        self._warning = ClientGUICommon.BetterStaticText( self, label = warning )
        self._warning.setObjectName( 'HydrusWarning' )
        
        message = 'While a tag service normally only applies its own siblings and parents to itself, it does not have to. You can have other services\' rules apply (e.g. putting the PTR\'s siblings on your "my tags"), or no siblings/parents at all.'
        message += '\n' * 2
        message += 'If you apply multiple services and there are conflicts (e.g. disagreements on where siblings go, or loops), the services at the top of the list have precedence. If you want to overwrite some PTR rules, then make what you want on a local service and then put it above the PTR here. Also, siblings apply first, then parents.'
        message += '\n' * 2
        message += 'If you make big changes here, it will take a long time for the client to recalculate everything. Sibling and parent chains will be broken apart and rearranged live, and for a brief period, some sibling or parent suggestions or presentation may be unusual. Check the sync progress panel under _tags->sibling/parent sync_ to see how it is going. If your client gets too laggy doing the recalc, turn it off during "normal time".'
        
        self._message = ClientGUICommon.BetterStaticText( self, label = message )
        self._message.setWordWrap( True )
        
        self._sync_status = ClientGUICommon.BetterStaticText( self )
        
        self._sync_status.setWordWrap( True )
        
        if CG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_active' ):
            
            self._sync_status.setText( 'Siblings and parents are set to sync all the time. Changes will start applying as soon as you ok this dialog.' )
            
            self._sync_status.setObjectName( 'HydrusValid' )
            
        else:
            
            if CG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_idle' ):
                
                self._sync_status.setText( 'Siblings and parents are only set to sync during idle time. Changes here will only start to apply when you are not using the client.' )
                
            else:
                
                self._sync_status.setText( 'Siblings and parents are not set to sync in the background at any time. If there is sync work to do, you will have to force it to run using the \'review\' window under _tags->siblings and parents sync_.' )
                
            
            self._sync_status.setObjectName( 'HydrusWarning' )
            
        
        self._sync_status.style().polish( self._sync_status )
        
        QP.AddToLayout( vbox, self._warning, CC.FLAGS_CENTER )
        QP.AddToLayout( vbox, self._message, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._sync_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tag_services, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._tag_services.currentChanged.connect( self._ServicePageChanged )
        
    
    def _ServicePageChanged( self ):
        
        if CG.client_controller.new_options.GetBoolean( 'save_default_tag_service_tab_on_change' ):
            
            current_page = typing.cast( EditTagDisplayApplication._Panel, self._tag_services.currentWidget() )
            
            CG.client_controller.new_options.SetKey( 'default_tag_service_tab', current_page.GetServiceKey() )
            
        
    
    def GetValue( self ):
        
        master_service_keys_to_sibling_applicable_service_keys = collections.defaultdict( list )
        master_service_keys_to_parent_applicable_service_keys = collections.defaultdict( list )
        
        for page in self._tag_services.GetPages():
            
            ( master_service_key, sibling_applicable_service_keys, parent_applicable_service_keys ) = page.GetValue()
            
            master_service_keys_to_sibling_applicable_service_keys[ master_service_key ] = sibling_applicable_service_keys
            master_service_keys_to_parent_applicable_service_keys[ master_service_key ] = parent_applicable_service_keys
            
        
        return ( master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys )
        
    
    class _Panel( QW.QWidget ):
        
        def __init__( self, parent: QW.QWidget, master_service_key: bytes, sibling_applicable_service_keys: collections.abc.Sequence[ bytes ], parent_applicable_service_keys: collections.abc.Sequence[ bytes ] ):
            
            super().__init__( parent )
            
            self._master_service_key = master_service_key
            
            #
            
            self._sibling_box = ClientGUICommon.StaticBox( self, 'sibling application' )
            
            #
            
            self._sibling_service_keys_listbox = ClientGUIListBoxes.QueueListBox( self._sibling_box, 4, CG.client_controller.services_manager.GetName, add_callable = self._AddSibling )
            
            #
            
            self._sibling_service_keys_listbox.AddDatas( sibling_applicable_service_keys )
            
            #
            
            self._parent_box = ClientGUICommon.StaticBox( self, 'parent application' )
            
            #
            
            self._parent_service_keys_listbox = ClientGUIListBoxes.QueueListBox( self._sibling_box, 4, CG.client_controller.services_manager.GetName, add_callable = self._AddParent )
            
            #
            
            self._parent_service_keys_listbox.AddDatas( parent_applicable_service_keys )
            
            #
            
            self._sibling_box.Add( self._sibling_service_keys_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self._parent_box.Add( self._parent_service_keys_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._sibling_box, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( vbox, self._parent_box, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def _AddParent( self ):
            
            current_service_keys = self._parent_service_keys_listbox.GetData()
            
            return self._AddService( current_service_keys )
            
        
        def _AddService( self, current_service_keys ):
            
            allowed_services = CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
            
            allowed_services = [ service for service in allowed_services if service.GetServiceKey() not in current_service_keys ]
            
            if len( allowed_services ) == 0:
                
                ClientGUIDialogsMessage.ShowInformation( self, 'You have all the current tag services applied to this service.' )
                
                raise HydrusExceptions.VetoException()
                
            
            choice_tuples = [ ( service.GetName(), service.GetServiceKey(), service.GetName() ) for service in allowed_services ]
            
            try:
                
                service_key = ClientGUIDialogsQuick.SelectFromListButtons( self, 'Which service?', choice_tuples )
                
                return service_key
                
            except HydrusExceptions.CancelledException:
                
                raise HydrusExceptions.VetoException()
                
            
        
        def _AddSibling( self ):
            
            current_service_keys = self._sibling_service_keys_listbox.GetData()
            
            return self._AddService( current_service_keys )
            
        
        def GetServiceKey( self ):
            
            return self._master_service_key
            
        
        def GetValue( self ):
            
            return ( self._master_service_key, self._sibling_service_keys_listbox.GetData(), self._parent_service_keys_listbox.GetData() )
            
        
    
