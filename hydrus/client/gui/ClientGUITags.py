import collections
import itertools
import random
import re
import time
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusText
from hydrus.core.networking import HydrusNetwork

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITagSuggestions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListBook
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUIMigrateTags
from hydrus.client.gui.metadata import ClientGUITagActions
from hydrus.client.gui.networking import ClientGUIHydrusNetwork
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.search import ClientGUILocation
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIColourPicker
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.gui.widgets import ClientGUITextInput
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientTagsHandling

def EditNamespaceSort( win: QW.QWidget, sort_data ):
    
    ( namespaces, tag_display_type ) = sort_data
    
    # users might want to add a namespace with a hyphen in it, so in lieu of a nice list to edit we'll just escape for now mate
    correct_char = '-'
    escaped_char = '\\-'
    
    escaped_namespaces = [ namespace.replace( correct_char, escaped_char ) for namespace in namespaces ]
    
    edit_string = '-'.join( escaped_namespaces )
    
    message = 'Write the namespaces you would like to sort by here, separated by hyphens. Any namespace in any of your sort definitions will be added to the collect-by menu.'
    message += '\n' * 2
    message += 'If the namespace you want to add has a hyphen, like \'creator-id\', instead type it with a backslash escape, like \'creator\\-id-page\'.'
    
    with ClientGUIDialogs.DialogTextEntry( win, message, allow_blank = False, default = edit_string ) as dlg:
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            edited_string = dlg.GetValue()
            
            edited_escaped_namespaces = re.split( r'(?<!\\)-', edited_string )
            
            edited_namespaces = [ namespace.replace( escaped_char, correct_char ) for namespace in edited_escaped_namespaces ]
            
            edited_namespaces = [ HydrusTags.CleanTag( namespace ) for namespace in edited_namespaces if HydrusTags.TagOK( namespace ) ]
            
            if len( edited_namespaces ) > 0:
                
                if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                    
                    available_types = [
                        ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL,
                        ClientTags.TAG_DISPLAY_SELECTION_LIST,
                        ClientTags.TAG_DISPLAY_SINGLE_MEDIA
                    ]
                    
                    choice_tuples = [ ( ClientTags.tag_display_str_lookup[ tag_display_type ], tag_display_type, ClientTags.tag_display_str_lookup[ tag_display_type ] ) for tag_display_type in available_types ]
                    
                    message = 'If you filter your different tag views (e.g. hiding the PTR\'s title tags), sorting on those views may give a different order. If you are not sure on this, set \'display tags\'.'
                    
                    try:
                        
                        tag_display_type = ClientGUIDialogsQuick.SelectFromListButtons( win, 'select tag view to sort on', choice_tuples = choice_tuples, message = message )
                        
                    except HydrusExceptions.CancelledException:
                        
                        raise HydrusExceptions.VetoException()
                        
                    
                else:
                    
                    tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL
                    
                
                return ( tuple( edited_namespaces ), tag_display_type )
                
            
        
        raise HydrusExceptions.VetoException()
        
    
class EditTagAutocompleteOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, tag_autocomplete_options: ClientTagsHandling.TagAutocompleteOptions ):
        
        super().__init__( parent )
        
        self._original_tag_autocomplete_options = tag_autocomplete_options
        services_manager = CG.client_controller.services_manager
        
        all_real_tag_service_keys = services_manager.GetServiceKeys( HC.REAL_TAG_SERVICES )
        
        #
        
        self._write_autocomplete_tag_domain = ClientGUICommon.BetterChoice( self )
        self._write_autocomplete_tag_domain.setToolTip( ClientGUIFunctions.WrapToolTip( 'A manage tags autocomplete will start with this domain. Typically only useful with this service or "all known tags".' ) )
        
        self._write_autocomplete_tag_domain.addItem( services_manager.GetName( CC.COMBINED_TAG_SERVICE_KEY ), CC.COMBINED_TAG_SERVICE_KEY )
        
        for service_key in all_real_tag_service_keys:
            
            self._write_autocomplete_tag_domain.addItem( services_manager.GetName( service_key ), service_key )
            
        
        self._override_write_autocomplete_location_context = QW.QCheckBox( self )
        self._override_write_autocomplete_location_context.setToolTip( ClientGUIFunctions.WrapToolTip( 'If set, a manage tags dialog autocomplete will start with a different file domain than the one that launched the dialog.' ) )
        
        self._write_autocomplete_location_context = ClientGUILocation.LocationSearchContextButton( self, tag_autocomplete_options.GetWriteAutocompleteLocationContext() )
        self._write_autocomplete_location_context.setToolTip( ClientGUIFunctions.WrapToolTip( 'A manage tags autocomplete will start with this domain. Normally only useful for "all known files" or "my files".' ) )
        
        self._write_autocomplete_location_context.SetAllKnownFilesAllowed( True, False )
        
        self._search_namespaces_into_full_tags = QW.QCheckBox( self )
        self._search_namespaces_into_full_tags.setToolTip( ClientGUIFunctions.WrapToolTip( 'If on, a search for "ser" will return all "series:" results such as "series:metroid". On large tag services, these searches are extremely slow.' ) )
        
        self._unnamespaced_search_gives_any_namespace_wildcards = QW.QCheckBox( self )
        self._unnamespaced_search_gives_any_namespace_wildcards.setToolTip( ClientGUIFunctions.WrapToolTip( 'If on, an unnamespaced search like "sam" will return a special additional "any-namespace" wildcard for "sam (any namespace)", just as if you had typed "*:sam". If you regularly like to search for tags that may have multiple namespaces, this may save you time.\n\nIf you are not sure what this does, leave it unchecked.' ) )
        
        self._namespace_bare_fetch_all_allowed = QW.QCheckBox( self )
        self._namespace_bare_fetch_all_allowed.setToolTip( ClientGUIFunctions.WrapToolTip( 'If on, a search for "series:" will return all "series:" results. On large tag services, these searches are extremely slow.' ) )
        
        self._namespace_fetch_all_allowed = QW.QCheckBox( self )
        self._namespace_fetch_all_allowed.setToolTip( ClientGUIFunctions.WrapToolTip( 'If on, a search for "series:*" will return all "series:" results. On large tag services, these searches are extremely slow.' ) )
        
        self._fetch_all_allowed = QW.QCheckBox( self )
        self._fetch_all_allowed.setToolTip( ClientGUIFunctions.WrapToolTip( 'If on, a search for "*" will return all tags. On large tag services, these searches are extremely slow.' ) )
        
        self._fetch_results_automatically = QW.QCheckBox( self )
        self._fetch_results_automatically.setToolTip( ClientGUIFunctions.WrapToolTip( 'If on, results will load as you type. If off, you will have to hit a shortcut (default Ctrl+Space) to load results.' ) )
        
        self._exact_match_character_threshold = ClientGUICommon.NoneableSpinCtrl( self, 2, none_phrase = 'always autocomplete (only appropriate for small tag services)', min = 1, max = 256, unit = 'characters' )
        self._exact_match_character_threshold.setToolTip( ClientGUIFunctions.WrapToolTip( 'When the search text has <= this many characters, autocomplete will not occur and you will only get results that exactly match the input. Increasing this value makes autocomplete snappier but reduces the number of results.' ) )
        
        #
        
        self._write_autocomplete_tag_domain.SetValue( tag_autocomplete_options.GetWriteAutocompleteTagDomain() )
        self._override_write_autocomplete_location_context.setChecked( tag_autocomplete_options.OverridesWriteAutocompleteLocationContext() )
        self._search_namespaces_into_full_tags.setChecked( tag_autocomplete_options.SearchNamespacesIntoFullTags() )
        self._unnamespaced_search_gives_any_namespace_wildcards.setChecked( tag_autocomplete_options.UnnamespacedSearchGivesAnyNamespaceWildcards() )
        self._namespace_bare_fetch_all_allowed.setChecked( tag_autocomplete_options.NamespaceBareFetchAllAllowed() )
        self._namespace_fetch_all_allowed.setChecked( tag_autocomplete_options.NamespaceFetchAllAllowed() )
        self._fetch_all_allowed.setChecked( tag_autocomplete_options.FetchAllAllowed() )
        self._fetch_results_automatically.setChecked( tag_autocomplete_options.FetchResultsAutomatically() )
        self._exact_match_character_threshold.SetValue( tag_autocomplete_options.GetExactMatchCharacterThreshold() )
        
        #
        
        rows = []
        
        rows.append( ( 'Fetch results as you type: ', self._fetch_results_automatically ) )
        rows.append( ( 'Do-not-autocomplete character threshold: ', self._exact_match_character_threshold ) )
        
        if tag_autocomplete_options.GetServiceKey() == CC.COMBINED_TAG_SERVICE_KEY:
            
            self._write_autocomplete_tag_domain.setVisible( False )
            self._override_write_autocomplete_location_context.setVisible( False )
            self._write_autocomplete_location_context.setVisible( False )
            
        else:
            
            rows.append( ( 'Override default autocomplete file domain in _manage tags_: ', self._override_write_autocomplete_location_context ) )
            rows.append( ( 'Default autocomplete location in _manage tags_: ', self._write_autocomplete_location_context ) )
            rows.append( ( 'Default autocomplete tag domain in _manage tags_: ', self._write_autocomplete_tag_domain ) )
            
        
        rows.append( ( 'Search namespaces with normal input: ', self._search_namespaces_into_full_tags ) )
        rows.append( ( 'Unnamespaced input gives (any namespace) wildcard results: ', self._unnamespaced_search_gives_any_namespace_wildcards ) )
        rows.append( ( 'Allow "namespace:": ', self._namespace_bare_fetch_all_allowed ) )
        rows.append( ( 'Allow "namespace:*": ', self._namespace_fetch_all_allowed ) )
        rows.append( ( 'Allow "*": ', self._fetch_all_allowed ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        label = 'The settings that permit searching namespaces and expansive "*" queries can be very expensive on a large client and may cause problems!'
        
        st = ClientGUICommon.BetterStaticText( self, label = label )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        self._UpdateControls()
        
        self._override_write_autocomplete_location_context.stateChanged.connect( self._UpdateControls )
        self._search_namespaces_into_full_tags.stateChanged.connect( self._UpdateControlsFromSearchNamespacesIntoFullTags )
        self._unnamespaced_search_gives_any_namespace_wildcards.stateChanged.connect( self._UpdateControlsFromUnnamespacedSearchGivesAnyNamespaceWildcards )
        self._namespace_bare_fetch_all_allowed.stateChanged.connect( self._UpdateControls )
        
    
    def _UpdateControls( self ):
        
        self._write_autocomplete_location_context.setEnabled( self._override_write_autocomplete_location_context.isChecked() )
        
        for c in ( self._namespace_bare_fetch_all_allowed, self._namespace_fetch_all_allowed ):
            
            if not c.isEnabled():
                
                c.blockSignals( True )
                
                c.setChecked( True )
                
                c.blockSignals( False )
                
            
        
    
    def _UpdateControlsFromSearchNamespacesIntoFullTags( self ):
        
        if self._search_namespaces_into_full_tags.isChecked():
            
            self._namespace_bare_fetch_all_allowed.setEnabled( False )
            self._namespace_fetch_all_allowed.setEnabled( False )
            
            if self._unnamespaced_search_gives_any_namespace_wildcards.isChecked():
                
                self._unnamespaced_search_gives_any_namespace_wildcards.setChecked( False )
                
            
        else:
            
            self._namespace_bare_fetch_all_allowed.setEnabled( True )
            
            if self._namespace_bare_fetch_all_allowed.isChecked():
                
                self._namespace_fetch_all_allowed.setEnabled( False )
                
            else:
                
                self._namespace_fetch_all_allowed.setEnabled( True )
                
            
        
        self._UpdateControls()
        
    
    def _UpdateControlsFromUnnamespacedSearchGivesAnyNamespaceWildcards( self ):
        
        if self._unnamespaced_search_gives_any_namespace_wildcards.isChecked():
            
            if self._search_namespaces_into_full_tags.isChecked():
                
                self._search_namespaces_into_full_tags.setChecked( False )
                
            
        
        self._UpdateControls()
        
    
    def GetValue( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( self._original_tag_autocomplete_options.GetServiceKey() )
        
        write_autocomplete_tag_domain = self._write_autocomplete_tag_domain.GetValue()
        override_write_autocomplete_location_context = self._override_write_autocomplete_location_context.isChecked()
        write_autocomplete_location_context = self._write_autocomplete_location_context.GetValue()
        search_namespaces_into_full_tags = self._search_namespaces_into_full_tags.isChecked()
        namespace_bare_fetch_all_allowed = self._namespace_bare_fetch_all_allowed.isChecked()
        namespace_fetch_all_allowed = self._namespace_fetch_all_allowed.isChecked()
        fetch_all_allowed = self._fetch_all_allowed.isChecked()
        
        tag_autocomplete_options.SetTuple(
            write_autocomplete_tag_domain,
            override_write_autocomplete_location_context,
            write_autocomplete_location_context,
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        tag_autocomplete_options.SetFetchResultsAutomatically( self._fetch_results_automatically.isChecked() )
        tag_autocomplete_options.SetExactMatchCharacterThreshold( self._exact_match_character_threshold.GetValue() )
        tag_autocomplete_options.SetUnnamespacedSearchGivesAnyNamespaceWildcards( self._unnamespaced_search_gives_any_namespace_wildcards.isChecked() )
        
        return tag_autocomplete_options
        
    

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
                QP.CallAfter( self._tag_services.setCurrentWidget, page )
                
            
        
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
        
        def __init__( self, parent: QW.QWidget, master_service_key: bytes, sibling_applicable_service_keys: typing.Sequence[ bytes ], parent_applicable_service_keys: typing.Sequence[ bytes ] ):
            
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
            
        
    
class EditTagDisplayManagerPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, tag_display_manager: ClientTagsHandling.TagDisplayManager ):
        
        super().__init__( parent )
        
        self._original_tag_display_manager = tag_display_manager
        
        if CG.client_controller.new_options.GetBoolean( 'use_listbook_for_tag_service_panels' ):
            
            self._tag_services = ClientGUIListBook.ListBook( self )
            
        else:
            
            self._tag_services = ClientGUICommon.BetterNotebook( self )
            
        
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._tag_services, 100 )
        
        self._tag_services.setMinimumWidth( min_width )
        
        #
        
        services = list( CG.client_controller.services_manager.GetServices( ( HC.COMBINED_TAG, HC.LOCAL_TAG, HC.TAG_REPOSITORY ) ) )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            name = service.GetName()
            
            page = self._Panel( self._tag_services, self._original_tag_display_manager, service_key )
            
            self._tag_services.addTab( page, name )
            
            if service_key == CC.COMBINED_TAG_SERVICE_KEY:
                
                self._tag_services.setCurrentWidget( page )
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._tag_services, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        tag_display_manager = self._original_tag_display_manager.Duplicate()
        
        tag_display_manager.ClearTagDisplayOptions()
        
        for page in self._tag_services.GetPages():
            
            ( service_key, tag_display_types_to_tag_filters, tag_autocomplete_options ) = page.GetValue()
            
            for ( tag_display_type, tag_filter ) in tag_display_types_to_tag_filters.items():
                
                tag_display_manager.SetTagFilter( tag_display_type, service_key, tag_filter )
                
            
            tag_display_manager.SetTagAutocompleteOptions( tag_autocomplete_options )
            
        
        return tag_display_manager
        
    
    class _Panel( QW.QWidget ):
        
        def __init__( self, parent: QW.QWidget, tag_display_manager: ClientTagsHandling.TagDisplayManager, service_key: bytes ):
            
            super().__init__( parent )
            
            single_tag_filter = tag_display_manager.GetTagFilter( ClientTags.TAG_DISPLAY_SINGLE_MEDIA, service_key )
            selection_tag_filter = tag_display_manager.GetTagFilter( ClientTags.TAG_DISPLAY_SELECTION_LIST, service_key )
            
            tag_autocomplete_options = tag_display_manager.GetTagAutocompleteOptions( service_key )
            
            self._service_key = service_key
            
            #
            
            self._display_box = ClientGUICommon.StaticBox( self, 'display' )
            
            message = 'This filters which tags will show on \'single\' file views such as the media viewer and thumbnail banners.'
            
            self._single_tag_filter_button = TagFilterButton( self._display_box, message, single_tag_filter, label_prefix = 'tags shown: ' )
            
            message = 'This filters which tags will show on \'selection\' file views such as the \'selection tags\' list on regular search pages.'
            
            self._selection_tag_filter_button = TagFilterButton( self._display_box, message, selection_tag_filter, label_prefix = 'tags shown: ' )
            
            #
            
            self._tao_box = ClientGUICommon.StaticBox( self, 'autocomplete' )
            
            self._tag_autocomplete_options_panel = EditTagAutocompleteOptionsPanel( self._tao_box, tag_autocomplete_options )
            
            #
            
            rows = []
            
            rows.append( ( 'Tag filter for single file views: ', self._single_tag_filter_button ) )
            rows.append( ( 'Tag filter for multiple file views: ', self._selection_tag_filter_button ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._display_box, rows )
            
            self._display_box.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            self._tao_box.Add( self._tag_autocomplete_options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            
            vbox = QP.VBoxLayout()
            
            if self._service_key == CC.COMBINED_TAG_SERVICE_KEY:
                
                message = 'These options apply to all tag services, or to where the tag domain is "all known tags".'
                message += '\n' * 2
                message += 'This tag domain is the union of all other services, so it can be more computationally expensive. You most often see it on new search pages.'
                
            else:
                
                message = 'This is just one tag service. You most often search a specific tag service in the manage tags dialog.'
                
            
            st = ClientGUICommon.BetterStaticText( self, message )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            QP.AddToLayout( vbox, self._display_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._tao_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 0 )
            
            self.setLayout( vbox )
            
        
        def GetValue( self ):
            
            tag_display_types_to_tag_filters = {}
            
            tag_display_types_to_tag_filters[ ClientTags.TAG_DISPLAY_SINGLE_MEDIA ] = self._single_tag_filter_button.GetValue()
            tag_display_types_to_tag_filters[ ClientTags.TAG_DISPLAY_SELECTION_LIST ] = self._selection_tag_filter_button.GetValue()
            
            tag_autocomplete_options = self._tag_autocomplete_options_panel.GetValue()
            
            return ( self._service_key, tag_display_types_to_tag_filters, tag_autocomplete_options )
            
        
    
class EditTagFilterPanel( ClientGUIScrolledPanels.EditPanel ):
    
    TEST_RESULT_DEFAULT = 'Enter a tag here to test if it passes the current filter:'
    TEST_RESULT_BLACKLIST_DEFAULT = 'Enter a tag here to test if it passes the blacklist (siblings tested, unnamespaced rules match namespaced tags):'
    
    def __init__( self, parent, tag_filter, only_show_blacklist = False, namespaces = None, message = None, read_only = False ):
        
        super().__init__( parent )
        
        self._only_show_blacklist = only_show_blacklist
        self._namespaces = namespaces
        self._read_only = read_only
        
        self._wildcard_replacements = {}
        
        self._wildcard_replacements[ '*' ] = ''
        self._wildcard_replacements[ '*:' ] = ':'
        self._wildcard_replacements[ '*:*' ] = ':'
        
        #
        
        self._favourites_panel = ClientGUICommon.StaticBox( self, 'favourites' )
        
        self._import_favourite = ClientGUICommon.BetterButton( self._favourites_panel, 'import', self._ImportFavourite )
        self._export_favourite = ClientGUICommon.BetterButton( self._favourites_panel, 'export', self._ExportFavourite )
        self._load_favourite = ClientGUICommon.BetterButton( self._favourites_panel, 'load', self._LoadFavourite )
        self._save_favourite = ClientGUICommon.BetterButton( self._favourites_panel, 'save', self._SaveFavourite )
        self._delete_favourite = ClientGUICommon.BetterButton( self._favourites_panel, 'delete', self._DeleteFavourite )
        
        #
        
        self._filter_panel = ClientGUICommon.StaticBox( self, 'filter' )
        
        self._show_all_panels_button = ClientGUICommon.BetterButton( self._filter_panel, 'show other panels', self._ShowAllPanels )
        self._show_all_panels_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'This shows the whitelist and advanced panels, in case you want to craft a clever blacklist with \'except\' rules.' ) )
        
        show_the_button = self._only_show_blacklist and CG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
        self._show_all_panels_button.setVisible( show_the_button )
        
        #
        
        self._notebook = ClientGUICommon.BetterNotebook( self._filter_panel )
        
        #
        
        self._advanced_panel = self._InitAdvancedPanel()
        
        self._whitelist_panel = self._InitWhitelistPanel()
        self._blacklist_panel = self._InitBlacklistPanel()
        
        #
        
        if self._only_show_blacklist:
            
            self._whitelist_panel.setVisible( False )
            self._notebook.addTab( self._blacklist_panel, 'blacklist' )
            self._advanced_panel.setVisible( False )
            
        else:
            
            self._notebook.addTab( self._whitelist_panel, 'whitelist' )
            self._notebook.addTab( self._blacklist_panel, 'blacklist' )
            self._notebook.addTab( self._advanced_panel, 'advanced' )
            
        
        #
        
        self._redundant_st = ClientGUICommon.BetterStaticText( self._filter_panel, '', ellipsize_end = True )
        self._redundant_st.setVisible( False )
        
        self._current_filter_st = ClientGUICommon.BetterStaticText( self._filter_panel, 'current filter: ', ellipsize_end = True )
        
        #
        
        self._test_panel = ClientGUICommon.StaticBox( self, 'testing', can_expand = True, start_expanded = True )
        
        self._test_result_st = ClientGUICommon.BetterStaticText( self._test_panel, self.TEST_RESULT_DEFAULT )
        self._test_result_st.setAlignment( QC.Qt.AlignmentFlag.AlignVCenter | QC.Qt.AlignmentFlag.AlignRight )
        
        self._test_result_st.setWordWrap( True )
        
        self._test_input = QW.QPlainTextEdit( self._test_panel )
        
        #
        
        vbox = QP.VBoxLayout()
        
        if not self._read_only:
            
            help_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().help, self._ShowHelp )
            
            help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
            
            QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
            
        
        if message is not None:
            
            message_panel = ClientGUICommon.StaticBox( self, 'explanation', can_expand = True, start_expanded = True )
            
            st = ClientGUICommon.BetterStaticText( message_panel, message )
            
            st.setWordWrap( True )
            
            message_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            QP.AddToLayout( vbox, message_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        #
        
        hbox = QP.HBoxLayout()
        
        if self._read_only:
            
            self._import_favourite.hide()
            self._load_favourite.hide()
            
        
        QP.AddToLayout( hbox, self._import_favourite, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._export_favourite, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._load_favourite, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._save_favourite, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._delete_favourite, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._favourites_panel.Add( hbox, CC.FLAGS_ON_RIGHT )
        
        QP.AddToLayout( vbox, self._favourites_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._filter_panel.Add( self._show_all_panels_button, CC.FLAGS_ON_RIGHT )
        
        label = 'Click the "(un)namespaced" checkboxes to allow/disallow those tags.\nType "namespace:" to manually input a namespace that is not in the list.'
        st = ClientGUICommon.BetterStaticText( self, label = label )
        st.setWordWrap( True )
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        self._filter_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._filter_panel.Add( self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._filter_panel.Add( self._redundant_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filter_panel.Add( self._current_filter_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._filter_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        test_text_vbox = QP.VBoxLayout()
        
        if self._only_show_blacklist:
            
            message = 'This is a fixed blacklist. It will apply rules against all test tag siblings and apply unnamespaced rules to namespaced test tags.'
            
            st = ClientGUICommon.BetterStaticText( self._test_input, message )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( test_text_vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        QP.AddToLayout( test_text_vbox, self._test_result_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, test_text_vbox, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._test_input, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        
        self._test_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._test_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._advanced_blacklist.listBoxChanged.connect( self._UpdateStatus )
        self._advanced_whitelist.listBoxChanged.connect( self._UpdateStatus )
        self._simple_whitelist_global_checkboxes.clicked.connect( self.EventSimpleWhitelistGlobalCheck )
        self._simple_whitelist_namespace_checkboxes.clicked.connect( self.EventSimpleWhitelistNamespaceCheck )
        self._simple_blacklist_global_checkboxes.clicked.connect( self.EventSimpleBlacklistGlobalCheck )
        self._simple_blacklist_namespace_checkboxes.clicked.connect( self.EventSimpleBlacklistNamespaceCheck )
        
        self._test_input.textChanged.connect( self._UpdateTest )
        
        self.SetValue( tag_filter )
        
    
    def _AdvancedAddBlacklistMultiple( self, tag_slices, only_add = False, only_remove = False ):
        
        self._AdvancedEnterBlacklistMultiple( tag_slices, only_add = True )
        
    
    def _AdvancedAddWhitelistMultiple( self, tag_slices ):
        
        self._AdvancedEnterWhitelistMultiple( tag_slices, only_add = True )
        
    
    def _AdvancedBlacklistEverything( self ):
        
        self._advanced_blacklist.SetTagSlices( [] )
        
        self._advanced_whitelist.RemoveTagSlices( ( '', ':' ) )
        
        self._advanced_blacklist.AddTagSlices( ( '', ':' ) )
        
        self._UpdateStatus()
        
    
    def _AdvancedDeleteBlacklistButton( self ):
        
        selected_tag_slices = self._advanced_blacklist.GetSelectedTagSlices()
        
        if len( selected_tag_slices ) > 0:
            
            result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._advanced_blacklist.RemoveTagSlices( selected_tag_slices )
                
            
        
        self._UpdateStatus()
        
    
    def _AdvancedDeleteWhitelistButton( self ):
        
        selected_tag_slices = self._advanced_whitelist.GetSelectedTagSlices()
        
        if len( selected_tag_slices ) > 0:
            
            result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._advanced_whitelist.RemoveTagSlices( selected_tag_slices )
                
            
        
        self._UpdateStatus()
        
    
    def _AdvancedEnterBlacklistMultiple( self, tag_slices, only_add = False, only_remove = False ):
        
        tag_slices = [ self._CleanTagSliceInput( tag_slice ) for tag_slice in tag_slices ]
        
        tag_slices = HydrusData.DedupeList( tag_slices )
        
        current_blacklist = set( self._advanced_blacklist.GetTagSlices() )
        
        to_remove = set( tag_slices ).intersection( current_blacklist )
        
        to_add = [ tag_slice for tag_slice in tag_slices if tag_slice not in to_remove ]
        
        if len( to_remove ) > 0 and not only_add:
            
            self._advanced_blacklist.RemoveTagSlices( to_remove )
            
        
        if len( to_add ) > 0 and not only_remove:
            
            self._advanced_whitelist.RemoveTagSlices( to_add )
            
            already_blocked = [ tag_slice for tag_slice in to_add if self._CurrentlyBlocked( tag_slice ) ]
            
            if len( already_blocked ) > 0:
                
                if len( already_blocked ) == 1:
                    
                    message = f'{HydrusTags.ConvertTagSliceToPrettyString( already_blocked[0] )} is already blocked by a broader rule!'
                    
                else:
                    
                    separator = '\n' if len( already_blocked ) < 5 else ', '
                    
                    message = 'The tags\n\n' + separator.join( [ HydrusTags.ConvertTagSliceToPrettyString( tag_slice ) for tag_slice in already_blocked ] ) + '\n\nare already blocked by a broader rule!'
                    
                
                self._ShowRedundantError( message )
                
            
            self._advanced_blacklist.AddTagSlices( to_add )
            
        
        self._UpdateStatus()
        
    
    def _AdvancedEnterWhitelistMultiple( self, tag_slices, only_add = False, only_remove = False ):
        
        tag_slices = [ self._CleanTagSliceInput( tag_slice ) for tag_slice in tag_slices ]
        
        current_whitelist = set( self._advanced_whitelist.GetTagSlices() )
        
        to_remove = set( tag_slices ).intersection( current_whitelist )
        
        if len( to_remove ) > 0 and not only_add:
            
            self._advanced_whitelist.RemoveTagSlices( to_remove )
            
        
        to_add = [ tag_slice for tag_slice in tag_slices if tag_slice not in to_remove ]
        
        if len( to_add ) > 0 and not only_remove:
            
            self._advanced_blacklist.RemoveTagSlices( to_add )
            
            already_permitted = [ tag_slice for tag_slice in to_add if tag_slice not in ( '', ':' ) and not self._CurrentlyBlocked( tag_slice ) ]
            
            if len( already_permitted ) > 0:
                
                if len( already_permitted ) == 1:
                    
                    message = f'{HydrusTags.ConvertTagSliceToPrettyString( to_add[0] )} is already permitted by a broader rule!'
                    
                else:
                    
                    separator = '\n' if len( already_permitted ) < 5 else ', '
                    
                    message = 'The tags\n\n' + separator.join( [ HydrusTags.ConvertTagSliceToPrettyString( tag_slice ) for tag_slice in already_permitted ] ) + '\n\nare already permitted by a broader rule!'
                    
                
                self._ShowRedundantError( message )
                
            
            tag_slices_to_actually_add = [ tag_slice for tag_slice in tag_slices if tag_slice not in ( '', ':' ) ]
            
            # we don't say 'except for' for (un)namespaced
            self._advanced_whitelist.AddTagSlices( tag_slices_to_actually_add )
            
        
        self._UpdateStatus()
        
    
    def _CleanTagSliceInput( self, tag_slice ):
        
        tag_slice = tag_slice.lower().strip()
        
        while '**' in tag_slice:
            
            tag_slice = tag_slice.replace( '**', '*' )
            
        
        if tag_slice in self._wildcard_replacements:
            
            tag_slice = self._wildcard_replacements[ tag_slice ]
            
        
        if ':' in tag_slice:
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag_slice )
            
            if subtag == '*':
                
                tag_slice = '{}:'.format( namespace )
                
            
        
        return tag_slice
        
    
    def _CurrentlyBlocked( self, tag_slice ):
        
        if tag_slice in ( '', ':' ):
            
            test_slices = { tag_slice }
            
        elif HydrusTags.IsNamespaceTagSlice( tag_slice ):
            
            test_slices = { ':', tag_slice }
            
        elif ':' in tag_slice:
            
            ( ns, st ) = HydrusTags.SplitTag( tag_slice )
            
            test_slices = { ':', ns + ':', tag_slice }
            
        else:
            
            test_slices = { '', tag_slice }
            
        
        blacklist = set( self._advanced_blacklist.GetTagSlices() )
        
        return not blacklist.isdisjoint( test_slices )
        
    
    def _DeleteFavourite( self ):
        
        def do_it( name ):
            
            names_to_tag_filters = CG.client_controller.new_options.GetFavouriteTagFilters()
            
            if name in names_to_tag_filters:
                
                message = 'Delete "{}"?'.format( name )
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return
                    
                
                del names_to_tag_filters[ name ]
                
                CG.client_controller.new_options.SetFavouriteTagFilters( names_to_tag_filters )
                
            
        
        names_to_tag_filters = CG.client_controller.new_options.GetFavouriteTagFilters()
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        if len( names_to_tag_filters ) == 0:
            
            ClientGUIMenus.AppendMenuLabel( menu, 'no favourites set!' )
            
        else:
            
            for ( name, tag_filter ) in names_to_tag_filters.items():
                
                ClientGUIMenus.AppendMenuItem( menu, name, 'delete {}'.format( name ), do_it, name )
                
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _ExportFavourite( self ):
        
        names_to_tag_filters = CG.client_controller.new_options.GetFavouriteTagFilters()
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        ClientGUIMenus.AppendMenuItem( menu, 'this tag filter', 'export this tag filter', CG.client_controller.pub, 'clipboard', 'text', self.GetValue().DumpToString() )
        
        if len( names_to_tag_filters ) > 0:
            
            ClientGUIMenus.AppendSeparator( menu )
            
            for ( name, tag_filter ) in names_to_tag_filters.items():
                
                ClientGUIMenus.AppendMenuItem( menu, name, 'export {}'.format( name ), CG.client_controller.pub, 'clipboard', 'text', tag_filter.DumpToString() )
                
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _GetWhiteBlacklistsPossible( self ):
        
        blacklist_tag_slices = self._advanced_blacklist.GetTagSlices()
        whitelist_tag_slices = self._advanced_whitelist.GetTagSlices()
        
        blacklist_is_only_simples = set( blacklist_tag_slices ).issubset( { '', ':' } )
        
        nothing_is_whitelisted = len( whitelist_tag_slices ) == 0
        
        whitelist_possible = blacklist_is_only_simples
        blacklist_possible = nothing_is_whitelisted
        
        return ( whitelist_possible, blacklist_possible )
        
    
    def _ImportFavourite( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', str(e) )
            
            return
            
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON-serialised Tag Filter object', e )
            
            return
            
        
        if not isinstance( obj, HydrusTags.TagFilter ):
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Error', f'That object was not a Tag Filter! It seemed to be a "{type(obj)}".' )
            
            return
            
        
        tag_filter = obj
        
        tag_filter.CleanRules()
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter a name for the favourite.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                names_to_tag_filters = CG.client_controller.new_options.GetFavouriteTagFilters()
                
                name = dlg.GetValue()
                
                if name in names_to_tag_filters:
                    
                    message = '"{}" already exists! Overwrite?'.format( name )
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.DialogCode.Accepted:
                        
                        return
                        
                    
                
                names_to_tag_filters[ name ] = tag_filter
                
                CG.client_controller.new_options.SetFavouriteTagFilters( names_to_tag_filters )
                
                self.SetValue( tag_filter )
                
            
        
    
    def _InitAdvancedPanel( self ):
        
        advanced_panel = QW.QWidget( self._notebook )
        
        #
        
        self._advanced_blacklist_panel = ClientGUICommon.StaticBox( advanced_panel, 'exclude these' )
        
        self._advanced_blacklist = ClientGUIListBoxes.ListBoxTagsFilter( self._advanced_blacklist_panel, read_only = self._read_only )
        
        self._advanced_blacklist_input = ClientGUITextInput.TextAndPasteCtrl( self._advanced_blacklist_panel, self._AdvancedAddBlacklistMultiple, allow_empty_input = True )
        
        delete_blacklist_button = ClientGUICommon.BetterButton( self._advanced_blacklist_panel, 'delete', self._AdvancedDeleteBlacklistButton )
        blacklist_everything_button = ClientGUICommon.BetterButton( self._advanced_blacklist_panel, 'block everything', self._AdvancedBlacklistEverything )
        
        #
        
        self._advanced_whitelist_panel = ClientGUICommon.StaticBox( advanced_panel, 'except for these' )
        
        self._advanced_whitelist = ClientGUIListBoxes.ListBoxTagsFilter( self._advanced_whitelist_panel, read_only = self._read_only )
        
        self._advanced_whitelist_input = ClientGUITextInput.TextAndPasteCtrl( self._advanced_whitelist_panel, self._AdvancedAddWhitelistMultiple, allow_empty_input = True )
        
        delete_whitelist_button = ClientGUICommon.BetterButton( self._advanced_whitelist_panel, 'delete', self._AdvancedDeleteWhitelistButton )
        
        #
        
        if self._read_only:
            
            self._advanced_blacklist_input.hide()
            delete_blacklist_button.hide()
            blacklist_everything_button.hide()
            
            self._advanced_whitelist_input.hide()
            delete_whitelist_button.hide()
            
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._advanced_blacklist_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox, delete_blacklist_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, blacklist_everything_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._advanced_blacklist_panel.Add( self._advanced_blacklist, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._advanced_blacklist_panel.Add( button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._advanced_whitelist_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox, delete_whitelist_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._advanced_whitelist_panel.Add( self._advanced_whitelist, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._advanced_whitelist_panel.Add( button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._advanced_blacklist_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._advanced_whitelist_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        advanced_panel.setLayout( hbox )
        
        return advanced_panel
        
    
    def _InitBlacklistPanel( self ):
        
        blacklist_overpanel = QW.QWidget( self._notebook )
        
        #
        
        self._simple_blacklist_error_st = ClientGUICommon.BetterStaticText( blacklist_overpanel )
        self._simple_blacklist_error_st.setVisible( False )
        
        #
        
        self._simple_blacklist_panel = ClientGUICommon.StaticBox( blacklist_overpanel, 'exclude these' )
        
        self._simple_blacklist_global_checkboxes = ClientGUICommon.BetterCheckBoxList( self._simple_whitelist_panel )
        
        self._simple_blacklist_global_checkboxes.Append( 'unnamespaced tags', '' )
        self._simple_blacklist_global_checkboxes.Append( 'namespaced tags', ':' )
        
        self._simple_blacklist_global_checkboxes.SetHeightBasedOnContents()
        
        self._simple_blacklist_namespace_checkboxes = ClientGUICommon.BetterCheckBoxList( self._simple_whitelist_panel )
        
        for namespace in self._namespaces:
            
            if namespace == '':
                
                continue
                
            
            self._simple_blacklist_namespace_checkboxes.Append( namespace, namespace + ':' )
            
        
        self._simple_blacklist = ClientGUIListBoxes.ListBoxTagsFilter( self._simple_whitelist_panel, read_only = self._read_only )
        
        self._simple_blacklist_input = ClientGUITextInput.TextAndPasteCtrl( self._simple_whitelist_panel, self._SimpleAddBlacklistMultiple, allow_empty_input = True )
        
        delete_blacklist_button = ClientGUICommon.BetterButton( self._simple_whitelist_panel, 'remove', self._SimpleDeleteBlacklistButton )
        blacklist_everything_button = ClientGUICommon.BetterButton( self._simple_whitelist_panel, 'block everything', self._AdvancedBlacklistEverything )
        
        #
        
        if self._read_only:
            
            self._simple_blacklist_global_checkboxes.setEnabled( False )
            self._simple_blacklist_namespace_checkboxes.setEnabled( False )
            
            self._simple_blacklist_input.hide()
            
            delete_blacklist_button.hide()
            blacklist_everything_button.hide()
            
        
        left_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( left_vbox, self._simple_blacklist_global_checkboxes, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( left_vbox, self._simple_blacklist_namespace_checkboxes, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._simple_blacklist_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox, delete_blacklist_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, blacklist_everything_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        right_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( right_vbox, self._simple_blacklist, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( right_vbox, button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        main_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( main_hbox, left_vbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( main_hbox, right_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._simple_blacklist_panel.Add( main_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._simple_blacklist_error_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._simple_blacklist_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        blacklist_overpanel.setLayout( vbox )
        
        self._simple_blacklist.tagsRemoved.connect( self._SimpleBlacklistRemoved )
        
        return blacklist_overpanel
        
    
    def _InitWhitelistPanel( self ):
        
        whitelist_overpanel = QW.QWidget( self._notebook )
        
        #
        
        self._simple_whitelist_error_st = ClientGUICommon.BetterStaticText( whitelist_overpanel )
        self._simple_whitelist_error_st.setVisible( False )
        
        #
        
        self._simple_whitelist_panel = ClientGUICommon.StaticBox( whitelist_overpanel, 'allow these' )
        
        self._simple_whitelist_global_checkboxes = ClientGUICommon.BetterCheckBoxList( self._simple_whitelist_panel )
        
        self._simple_whitelist_global_checkboxes.Append( 'unnamespaced tags', '' )
        self._simple_whitelist_global_checkboxes.Append( 'namespaced tags', ':' )
        
        self._simple_whitelist_global_checkboxes.SetHeightBasedOnContents()
        
        self._simple_whitelist_namespace_checkboxes = ClientGUICommon.BetterCheckBoxList( self._simple_whitelist_panel )
        
        for namespace in self._namespaces:
            
            if namespace == '':
                
                continue
                
            
            self._simple_whitelist_namespace_checkboxes.Append( namespace, namespace + ':' )
            
        
        #
        
        self._simple_whitelist = ClientGUIListBoxes.ListBoxTagsFilter( self._simple_whitelist_panel, read_only = self._read_only )
        
        self._simple_whitelist_input = ClientGUITextInput.TextAndPasteCtrl( self._simple_whitelist_panel, self._SimpleAddWhitelistMultiple, allow_empty_input = True )
        
        delete_whitelist_button = ClientGUICommon.BetterButton( self._simple_whitelist_panel, 'remove', self._SimpleDeleteWhitelistButton )
        
        #
        
        if self._read_only:
            
            self._simple_whitelist_global_checkboxes.setEnabled( False )
            self._simple_whitelist_namespace_checkboxes.setEnabled( False )
            
            self._simple_whitelist_input.hide()
            delete_whitelist_button.hide()
            
        
        left_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( left_vbox, self._simple_whitelist_global_checkboxes, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( left_vbox, self._simple_whitelist_namespace_checkboxes, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._simple_whitelist_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox, delete_whitelist_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        right_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( right_vbox, self._simple_whitelist, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( right_vbox, button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        main_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( main_hbox, left_vbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( main_hbox, right_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._simple_whitelist_panel.Add( main_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._simple_whitelist_error_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._simple_whitelist_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        whitelist_overpanel.setLayout( vbox )
        
        self._simple_whitelist.tagsRemoved.connect( self._SimpleWhitelistRemoved )
        
        return whitelist_overpanel
        
    
    def _LoadFavourite( self ):
        
        names_to_tag_filters = CG.client_controller.new_options.GetFavouriteTagFilters()
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        if len( names_to_tag_filters ) == 0:
            
            ClientGUIMenus.AppendMenuLabel( menu, 'no favourites set!' )
            
        else:
            
            for ( name, tag_filter ) in names_to_tag_filters.items():
                
                ClientGUIMenus.AppendMenuItem( menu, name, 'load {}'.format( name ), self.SetValue, tag_filter )
                
            
        
        tag_repositories = CG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) )
        
        if len( tag_repositories ) > 0:
            
            ClientGUIMenus.AppendSeparator( menu )
            
            for service in sorted( tag_repositories, key = lambda s: s.GetName() ):
                
                tag_filter = service.GetTagFilter()
                
                ClientGUIMenus.AppendMenuItem( menu, f'tag filter for "{service.GetName()}"', 'load the serverside tag filter for this service', self.SetValue, tag_filter )
                
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _SaveFavourite( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter a name for the favourite.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                names_to_tag_filters = CG.client_controller.new_options.GetFavouriteTagFilters()
                
                name = dlg.GetValue()
                tag_filter = self.GetValue()
                
                if name in names_to_tag_filters:
                    
                    message = '"{}" already exists! Overwrite?'.format( name )
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.DialogCode.Accepted:
                        
                        return
                        
                    
                
                names_to_tag_filters[ name ] = tag_filter
                
                CG.client_controller.new_options.SetFavouriteTagFilters( names_to_tag_filters )
                
            
        
    
    def _ShowAllPanels( self ):
        
        self._whitelist_panel.setVisible( True )
        self._advanced_panel.setVisible( True )
        
        self._notebook.addTab( self._whitelist_panel, 'whitelist' )
        self._notebook.addTab( self._advanced_panel, 'advanced' )
        
        self._show_all_panels_button.setVisible( False )
        
    
    def _ShowHelp( self ):
        
        help = 'Here you can set rules to filter tags for one purpose or another. The default is typically to permit all tags. Check the current filter summary text at the bottom-left of the panel to ensure you have your logic correct.'
        help += '\n' * 2
        help += 'The whitelist/blacklist/advanced tabs are different ways of looking at the same filter, so you can choose which works best for you. Sometimes it is more useful to think about a filter as a whitelist (where only the listed contents are kept) or a blacklist (where everything _except_ the listed contents are kept), while the advanced tab lets you do a more complicated combination of the two.'
        help += '\n' * 2
        help += 'As well as selecting entire namespaces with the checkboxes, you can type or paste the individual tags directly--just hit enter to add each one. Double-click an existing entry in a list to remove it.'
        
        ClientGUIDialogsMessage.ShowInformation( self, help )
        
    
    def _ShowRedundantError( self, text ):
        
        self._redundant_st.setVisible( True )
        
        self._redundant_st.setText( text )
        
        CG.client_controller.CallLaterQtSafe( self._redundant_st, 2, 'clear redundant error', self._redundant_st.setVisible, False )
        
    
    def _SimpleAddBlacklistMultiple( self, tag_slices ):
        
        self._AdvancedAddBlacklistMultiple( tag_slices )
        
    
    def _SimpleAddWhitelistMultiple( self, tag_slices ):
        
        tag_slices = set( tag_slices )
        
        for simple in ( '', ':' ):
            
            if False and simple in tag_slices and simple in self._simple_whitelist.GetTagSlices():
                
                tag_slices.discard( simple )
                
                self._AdvancedEnterBlacklistMultiple( ( simple, ) )
                
            
        
        self._AdvancedAddWhitelistMultiple( tag_slices )
        
    
    def _SimpleBlacklistRemoved( self, tag_slices ):
        
        self._AdvancedEnterBlacklistMultiple( tag_slices )
        
    
    def _SimpleBlacklistReset( self ):
        
        pass
        
    
    def _SimpleDeleteBlacklistButton( self ):
        
        selected_tag_slices = self._simple_blacklist.GetSelectedTagSlices()
        
        if len( selected_tag_slices ) > 0:
            
            result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._simple_blacklist.RemoveTagSlices( selected_tag_slices )
                
                self._simple_blacklist.tagsRemoved.emit( selected_tag_slices )
                
            
        
        self._UpdateStatus()
        
    
    def _SimpleDeleteWhitelistButton( self ):
        
        selected_tag_slices = self._simple_whitelist.GetSelectedTagSlices()
        
        if len( selected_tag_slices ) > 0:
            
            result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._simple_whitelist.RemoveTagSlices( selected_tag_slices )
                
                self._simple_whitelist.tagsRemoved.emit( selected_tag_slices )
                
            
        
        self._UpdateStatus()
        
    
    def _SimpleWhitelistRemoved( self, tag_slices ):
        
        tag_slices = set( tag_slices )
        
        for simple in ( '', ':' ):
            
            if simple in tag_slices:
                
                tag_slices.discard( simple )
                
                self._AdvancedEnterBlacklistMultiple( ( simple, ) )
                
            
        
        self._AdvancedEnterWhitelistMultiple( tag_slices )
        
    
    def _SimpleWhitelistReset( self ):
        
        pass
        
    
    def _UpdateStatus( self ):
        
        ( whitelist_possible, blacklist_possible ) = self._GetWhiteBlacklistsPossible()
        
        whitelist_tag_slices = self._advanced_whitelist.GetTagSlices()
        
        self._whitelist_panel.setEnabled( whitelist_possible )
        
        self._simple_whitelist_error_st.setVisible( not whitelist_possible )
        
        if whitelist_possible:
            
            whitelist_tag_slices = set( whitelist_tag_slices )
            
            if not self._CurrentlyBlocked( '' ):
                
                whitelist_tag_slices.add( '' )
                
            
            if not self._CurrentlyBlocked( ':' ):
                
                whitelist_tag_slices.add( ':' )
                
                self._simple_whitelist_namespace_checkboxes.setEnabled( False )
                
            else:
                
                self._simple_whitelist_namespace_checkboxes.setEnabled( True )
                
            
            self._simple_whitelist.SetTagSlices( whitelist_tag_slices )
            
            for index in range( self._simple_whitelist_global_checkboxes.count() ):
                
                check = self._simple_whitelist_global_checkboxes.GetData( index ) in whitelist_tag_slices
                
                self._simple_whitelist_global_checkboxes.Check( index, check )
                
            
            for index in range( self._simple_whitelist_namespace_checkboxes.count() ):
                
                check = self._simple_whitelist_namespace_checkboxes.GetData( index ) in whitelist_tag_slices
                
                self._simple_whitelist_namespace_checkboxes.Check( index, check )
                
            
        else:
            
            self._simple_whitelist_error_st.setText( 'The filter is currently more complicated than a simple whitelist, so it cannot be shown here.' )
            
            self._simple_whitelist.SetTagSlices( '' )
            
            for index in range( self._simple_whitelist_global_checkboxes.count() ):
                
                self._simple_whitelist_global_checkboxes.Check( index, False )
                
            
            for index in range( self._simple_whitelist_namespace_checkboxes.count() ):
                
                self._simple_whitelist_namespace_checkboxes.Check( index, False )
                
            
        
        #
        
        blacklist_tag_slices = self._advanced_blacklist.GetTagSlices()
        
        self._blacklist_panel.setEnabled( blacklist_possible )
        
        self._simple_blacklist_error_st.setVisible( not blacklist_possible )
        
        if blacklist_possible:
            
            if self._CurrentlyBlocked( ':' ):
                
                self._simple_blacklist_namespace_checkboxes.setEnabled( False )
                
            else:
                
                self._simple_blacklist_namespace_checkboxes.setEnabled( True )
                
            
            self._simple_blacklist.SetTagSlices( blacklist_tag_slices )
            
            for index in range( self._simple_blacklist_global_checkboxes.count() ):
                
                check = self._simple_blacklist_global_checkboxes.GetData( index ) in blacklist_tag_slices
                
                self._simple_blacklist_global_checkboxes.Check( index, check )
                
            
            for index in range( self._simple_blacklist_namespace_checkboxes.count() ):
                
                check = self._simple_blacklist_namespace_checkboxes.GetData( index ) in blacklist_tag_slices
                
                self._simple_blacklist_namespace_checkboxes.Check( index, check )
                
            
        else:
            
            self._simple_blacklist_error_st.setText( 'The filter is currently more complicated than a simple blacklist, so it cannot be shown here.' )
            
            self._simple_blacklist.SetTagSlices( '' )
            
            for index in range( self._simple_blacklist_global_checkboxes.count() ):
                
                self._simple_blacklist_global_checkboxes.Check( index, False )
                
            
            for index in range( self._simple_blacklist_namespace_checkboxes.count() ):
                
                self._simple_blacklist_namespace_checkboxes.Check( index, False )
                
            
        
        #
        
        whitelist_tag_slices = self._advanced_whitelist.GetTagSlices()
        blacklist_tag_slices = self._advanced_blacklist.GetTagSlices()
        
        self._advanced_whitelist_input.setEnabled( len( blacklist_tag_slices ) > 0 )
        
        #
        
        tag_filter = self.GetValue()
        
        if self._only_show_blacklist:
            
            pretty_tag_filter = tag_filter.ToBlacklistString()
            
        else:
            
            pretty_tag_filter = 'current filter: {}'.format( tag_filter.ToPermittedString() )
            
        
        self._current_filter_st.setText( pretty_tag_filter )
        
        self._UpdateTest()
        
    
    def _UpdateTest( self ):
        
        test_input = self._test_input.toPlainText()
        
        if test_input == '':
            
            if self._only_show_blacklist:
                
                test_result_text = self.TEST_RESULT_BLACKLIST_DEFAULT
                
            else:
                
                test_result_text = self.TEST_RESULT_DEFAULT
                
            
            self._test_result_st.setObjectName( '' )
            
            self._test_result_st.setText( test_result_text )
            self._test_result_st.style().polish( self._test_result_st )
            
        else:
            
            test_tags = HydrusText.DeserialiseNewlinedTexts( test_input )
            
            test_tags = HydrusTags.CleanTags( test_tags )
            
            tag_filter = self.GetValue()
            
            self._test_result_st.setObjectName( '' )
            
            self._test_result_st.clear()
            self._test_result_st.style().polish( self._test_result_st )
            
            if self._only_show_blacklist:
                
                def work_callable():
                    
                    results = []
                    
                    tags_to_siblings = CG.client_controller.Read( 'tag_siblings_lookup', CC.COMBINED_TAG_SERVICE_KEY, test_tags )
                    
                    for test_tag_and_siblings in tags_to_siblings.values():
                        
                        results.append( False not in ( tag_filter.TagOK( t, apply_unnamespaced_rules_to_namespaced_tags = True ) for t in test_tag_and_siblings ) )
                        
                    
                    return results
                    
                
            else:
                
                def work_callable():
                    
                    results = [ tag_filter.TagOK( test_tag ) for test_tag in test_tags ]
                    
                    return results
                    
                
            
            def publish_callable( results ):
                
                all_good = False not in results
                all_bad = True not in results
                
                if len( results ) == 1:
                    
                    if all_good:
                        
                        test_result_text = 'tag passes!'
                        
                        self._test_result_st.setObjectName( 'HydrusValid' )
                        
                    else:
                        
                        test_result_text = 'tag blocked!'
                        
                        self._test_result_st.setObjectName( 'HydrusInvalid' )
                        
                    
                else:
                    
                    if all_good:
                        
                        test_result_text = 'all pass!'
                        
                        self._test_result_st.setObjectName( 'HydrusValid' )
                        
                    elif all_bad:
                        
                        test_result_text = 'all blocked!'
                        
                        self._test_result_st.setObjectName( 'HydrusInvalid' )
                        
                    else:
                        
                        c = collections.Counter()
                        
                        c.update( results )
                        
                        test_result_text = '{} pass, {} blocked!'.format( HydrusNumbers.ToHumanInt( c[ True ] ), HydrusNumbers.ToHumanInt( c[ False ] ) )
                        
                        self._test_result_st.setObjectName( 'HydrusInvalid' )
                        
                    
                
                self._test_result_st.setText( test_result_text )
                self._test_result_st.style().polish( self._test_result_st )
                
            
            async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
            
            async_job.start()
            
        
    
    def EventSimpleBlacklistNamespaceCheck( self, index ):

        index = index.row()
        
        if index != -1:
            
            tag_slice = self._simple_blacklist_namespace_checkboxes.GetData( index )
            
            self._AdvancedEnterBlacklistMultiple( ( tag_slice, ) )
            
        
    
    def EventSimpleBlacklistGlobalCheck( self, index ):
        
        index = index.row()
        
        if index != -1:
            
            tag_slice = self._simple_blacklist_global_checkboxes.GetData( index )
            
            self._AdvancedEnterBlacklistMultiple( ( tag_slice, ) )
            
        
    
    def EventSimpleWhitelistNamespaceCheck( self, index ):

        index = index.row()
        
        if index != -1:
            
            tag_slice = self._simple_whitelist_namespace_checkboxes.GetData( index )
            
            self._AdvancedEnterWhitelistMultiple( ( tag_slice, ) )
            
        
    
    def EventSimpleWhitelistGlobalCheck( self, index ):
        
        index = index.row()
        
        if index != -1:
            
            tag_slice = self._simple_whitelist_global_checkboxes.GetData( index )
            
            if tag_slice in ( '', ':' ) and tag_slice in self._simple_whitelist.GetTagSlices():
                
                self._AdvancedEnterBlacklistMultiple( ( tag_slice, ) )
                
            else:
                
                self._AdvancedEnterWhitelistMultiple( ( tag_slice, ) )
                
            
        
    
    def GetValue( self ):
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRules( self._advanced_blacklist.GetTagSlices(), HC.FILTER_BLACKLIST )
        tag_filter.SetRules( self._advanced_whitelist.GetTagSlices(), HC.FILTER_WHITELIST )
        
        return tag_filter
        
    
    def SetValue( self, tag_filter: HydrusTags.TagFilter ):
        
        blacklist_tag_slices = [ tag_slice for ( tag_slice, rule ) in tag_filter.GetTagSlicesToRules().items() if rule == HC.FILTER_BLACKLIST ]
        whitelist_tag_slices = [ tag_slice for ( tag_slice, rule ) in tag_filter.GetTagSlicesToRules().items() if rule == HC.FILTER_WHITELIST ]
        
        self._advanced_blacklist.SetTagSlices( blacklist_tag_slices )
        self._advanced_whitelist.SetTagSlices( whitelist_tag_slices )
        
        ( whitelist_possible, blacklist_possible ) = self._GetWhiteBlacklistsPossible()
        
        selection_tests = []
        
        if self._only_show_blacklist:
            
            selection_tests.append( ( blacklist_possible, self._blacklist_panel ) )
            
        else:
            
            selection_tests.append( ( whitelist_possible, self._whitelist_panel ) )
            selection_tests.append( ( blacklist_possible, self._blacklist_panel ) )
            selection_tests.append( ( True, self._advanced_panel ) )
            
        
        for ( test, page ) in selection_tests:
            
            if test:
                
                self._notebook.SelectPage( page )
                
                break
                
            
        
        self._UpdateStatus()
        
    

class IncrementalTaggingPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, medias: typing.List[ ClientMedia.MediaSingleton ] ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        self._medias = medias
        self._namespaces_to_medias_to_namespaced_subtags = collections.defaultdict( dict )
        
        self._service = CG.client_controller.services_manager.GetService( self._service_key )
        
        self._i_am_local_tag_service = self._service.GetServiceType() == HC.LOCAL_TAG
        
        label = 'Here you can add numerical tags incrementally to a selection of files, for instance adding page:1 -> page:20 to twenty files.'
        
        self._top_st = ClientGUICommon.BetterStaticText( self, label = label )
        self._top_st.setWordWrap( True )
        
        self._namespace = QW.QLineEdit( self )
        initial_namespace = CG.client_controller.new_options.GetString( 'last_incremental_tagging_namespace' )
        self._namespace.setText( initial_namespace )
        
        # let's make this dialog a reasonable landscape shape
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._namespace, 64 )
        self._namespace.setFixedWidth( width )
        
        self._prefix = QW.QLineEdit( self )
        initial_prefix = CG.client_controller.new_options.GetString( 'last_incremental_tagging_prefix' )
        self._prefix.setText( initial_prefix )
        
        self._suffix = QW.QLineEdit( self )
        initial_suffix = CG.client_controller.new_options.GetString( 'last_incremental_tagging_suffix' )
        self._suffix.setText( initial_suffix )
        
        self._tag_in_reverse = QW.QCheckBox( self )
        tt = 'Tag the last file first and work backwards, e.g. for start=1, step=1 on five files, set 5, 4, 3, 2, 1.'
        self._tag_in_reverse.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        initial_start = self._GetInitialStart()
        
        self._start = ClientGUICommon.BetterSpinBox( self, initial = initial_start, min = -10000000, max = 10000000 )
        tt = 'If you initialise this dialog and the first file already has that namespace, this widget will start with that version! A little overlap/prep may help here!'
        self._start.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._step = ClientGUICommon.BetterSpinBox( self, initial = 1, min = -10000, max = 10000 )
        tt = 'This sets how much the numerical tag should increment with each iteration. Negative values are fine and will decrement.'
        self._step.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        label = 'initialising\n\ninitialising'
        self._summary_st = ClientGUICommon.BetterStaticText( self, label = label )
        self._summary_st.setWordWrap( True )
        
        #
        
        rows = []
        
        rows.append( ( 'namespace: ', self._namespace ) )
        rows.append( ( 'start: ', self._start ) )
        rows.append( ( 'step: ', self._step ) )
        rows.append( ( 'prefix: ', self._prefix ) )
        rows.append( ( 'suffix: ', self._suffix ) )
        rows.append( ( 'tag in reverse: ', self._tag_in_reverse ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._top_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._summary_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._namespace.textChanged.connect( self._UpdateNamespace )
        self._prefix.textChanged.connect( self._UpdatePrefix )
        self._suffix.textChanged.connect( self._UpdateSuffix )
        self._start.valueChanged.connect( self._UpdateSummary )
        self._step.valueChanged.connect( self._UpdateSummary )
        self._tag_in_reverse.clicked.connect( self._UpdateSummary )
        
        self._UpdateSummary()
        
    
    def _GetInitialStart( self ):
        
        namespace = self._namespace.text()
        
        first_media = self._medias[0]
        
        medias_to_namespaced_subtags = self._GetMediasToNamespacedSubtags( namespace )
        
        namespaced_subtags = HydrusTags.SortNumericTags( medias_to_namespaced_subtags[ first_media ] )
        
        for subtag in namespaced_subtags:
            
            if subtag.isdecimal():
                
                return int( subtag )
                
            
        
        return 1
        
    
    def _GetMediaAndTagPairs( self ) -> typing.List[ typing.Tuple[ ClientMedia.MediaSingleton, str ] ]:
        
        tag_template = self._GetTagTemplate()
        start = self._start.value()
        step = self._step.value()
        prefix = self._prefix.text()
        suffix = self._suffix.text()
        
        result = []
        
        medias = list( self._medias )
        
        if self._tag_in_reverse.isChecked():
            
            medias.reverse()
            
        
        for ( i, media ) in enumerate( medias ):
            
            number = start + i * step
            
            subtag = f'{prefix}{number}{suffix}'
            
            tag = tag_template.format( subtag )
            
            result.append( ( media, tag ) )
            
        
        if self._tag_in_reverse.isChecked():
            
            result.reverse()
            
        
        return result
        
    
    def _GetMediasToNamespacedSubtags( self, namespace: str ):
        
        if namespace not in self._namespaces_to_medias_to_namespaced_subtags:
            
            medias_to_namespaced_subtags = dict()
            
            for media in self._medias:
                
                namespaced_subtags = set()
                
                current_and_pending_tags = media.GetTagsManager().GetCurrentAndPending( self._service_key, ClientTags.TAG_DISPLAY_STORAGE )
                
                for tag in current_and_pending_tags:
                    
                    ( n, subtag ) = HydrusTags.SplitTag( tag )
                    
                    if n == namespace:
                        
                        namespaced_subtags.add( subtag )
                        
                    
                
                medias_to_namespaced_subtags[ media ] = namespaced_subtags
                
            
            self._namespaces_to_medias_to_namespaced_subtags[ namespace ] = medias_to_namespaced_subtags
            
        
        return self._namespaces_to_medias_to_namespaced_subtags[ namespace ]
        
    
    def _GetTagTemplate( self ):
        
        namespace = self._namespace.text()
        
        if namespace == '':
            
            return '{}'
            
        else:
            
            return namespace + ':{}'
            
        
    
    def _UpdateNamespace( self ):
        
        namespace = self._namespace.text()
        
        CG.client_controller.new_options.SetString( 'last_incremental_tagging_namespace', namespace )
        
        self._UpdateSummary()
        
    
    def _UpdatePrefix( self ):
        
        prefix = self._prefix.text()
        
        CG.client_controller.new_options.SetString( 'last_incremental_tagging_prefix', prefix )
        
        self._UpdateSummary()
        
    
    def _UpdateSuffix( self ):
        
        suffix = self._suffix.text()
        
        CG.client_controller.new_options.SetString( 'last_incremental_tagging_suffix', suffix )
        
        self._UpdateSummary()
        
    
    def _UpdateSummary( self ):
        
        file_summary = f'{HydrusNumbers.ToHumanInt(len(self._medias))} files'
        
        medias_and_tags = self._GetMediaAndTagPairs()
        
        if len( medias_and_tags ) <= 4:
            
            tag_summary = ', '.join( ( tag for ( media, tag ) in medias_and_tags ) )
            
        else:
            
            if self._tag_in_reverse.isChecked():
                
                tag_summary = medias_and_tags[0][1] + f' {HC.UNICODE_ELLIPSIS} ' + ', '.join( ( tag for ( media, tag ) in medias_and_tags[-3:] ) )
                
            else:
                
                tag_summary = ', '.join( ( tag for ( media, tag ) in medias_and_tags[:3] ) ) + f' {HC.UNICODE_ELLIPSIS} ' + medias_and_tags[-1][1]
                
            
        
        #
        
        namespace = self._namespace.text()
        
        medias_to_namespaced_subtags = self._GetMediasToNamespacedSubtags( namespace )
        
        already_count = 0
        disagree_count = 0
        
        for ( media, tag ) in medias_and_tags:
            
            ( n, subtag ) = HydrusTags.SplitTag( tag )
            
            namespaced_subtags = medias_to_namespaced_subtags[ media ]
            
            if subtag in namespaced_subtags:
                
                already_count += 1
                
            elif len( namespaced_subtags ) > 0:
                
                disagree_count += 1
                
            
        
        if already_count == 0 and disagree_count == 0:
            
            conflict_summary = 'No conflicts, this all looks fresh!'
            
        elif disagree_count == 0:
            
            if already_count == len( self._medias ):
                
                conflict_summary = 'All the files already have these tags. This will make no changes.'
                
            else:
                
                conflict_summary = f'{HydrusNumbers.ToHumanInt( already_count )} files already have these tags.'
                
            
        elif already_count == 0:
            
            conflict_summary = f'{HydrusNumbers.ToHumanInt( disagree_count )} files already have different tags for this namespace. Are you sure you are lined up correct?'
            
        else:
            
            conflict_summary = f'{HydrusNumbers.ToHumanInt( already_count )} files already have these tags, and {HydrusNumbers.ToHumanInt( disagree_count )} files already have different tags for this namespace. Are you sure you are lined up correct?'
            
        
        label = f'For the {file_summary}, you are setting {tag_summary}.'
        label += '\n' * 2
        label += f'{conflict_summary}'
        
        self._summary_st.setText( label )
        
    
    def GetValue( self ) -> ClientContentUpdates.ContentUpdatePackage:
        
        if self._i_am_local_tag_service:
            
            content_action = HC.CONTENT_UPDATE_ADD
            
        else:
            
            content_action = HC.CONTENT_UPDATE_PEND
            
        
        medias_and_tags = self._GetMediaAndTagPairs()
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_action, ( tag, { media.GetHash() } ) ) for ( media, tag ) in medias_and_tags ]
        
        return ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( self._service_key, content_updates )
        
    

class ManageTagsPanel( CAC.ApplicationCommandProcessorMixin, ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, location_context: ClientLocation.LocationContext, tag_presentation_location: int, medias: typing.List[ ClientMedia.MediaSingleton ], immediate_commit = False, canvas_key = None ):
        
        super().__init__( parent )
        
        self._location_context = location_context
        self._tag_presentation_location = tag_presentation_location
        
        self._immediate_commit = immediate_commit
        self._canvas_key = canvas_key
        
        self._current_media = [ m.Duplicate() for m in medias ]
        
        self._hashes = set()
        
        for m in self._current_media:
            
            self._hashes.update( m.GetHashes() )
            
        
        if CG.client_controller.new_options.GetBoolean( 'use_listbook_for_tag_service_panels' ):
            
            self._tag_services = ClientGUIListBook.ListBook( self )
            
        else:
            
            self._tag_services = ClientGUICommon.BetterNotebook( self )
            
        
        #
        
        services = list( CG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) ) )
        
        services.extend( CG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) ) )
        
        if HG.gui_report_mode:
            
            HydrusData.ShowText( f'Opening manage tags on these services: {services}' )
            
        
        default_tag_service_key = CG.client_controller.new_options.GetKey( 'default_tag_service_tab' )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            name = service.GetName()
            
            if HG.gui_report_mode:
                
                HydrusData.ShowText( 'Opening manage tags panel on {}, {}, {}'.format( service, name, service_key.hex() ) )
                
            
            page = self._Panel( self._tag_services, self._location_context, service.GetServiceKey(), self._tag_presentation_location, self._current_media, self._immediate_commit, canvas_key = self._canvas_key )
            
            self._tag_services.addTab( page, name )
            
            page.movePageLeft.connect( self.MovePageLeft )
            page.movePageRight.connect( self.MovePageRight )
            page.showPrevious.connect( self.ShowPrevious )
            page.showNext.connect( self.ShowNext )
            
            page.okSignal.connect( self.okSignal )
            
            page.valueChanged.connect( self._UpdatePageTabNames )
            
            if service_key == default_tag_service_key:
                
                # Py 3.11/PyQt6 6.5.0/two tabs/total tab characters > ~12/select second tab during init = first tab disappears bug
                QP.CallAfter( self._tag_services.setCurrentWidget, page )
                
            
        
        if HG.gui_report_mode:
            
            HydrusData.ShowText( 'Opening manage tags panel, notebook tab count is {}'.format( self._tag_services.count() ) )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._tag_services, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        QP.CallAfter( self._tag_services.currentChanged.connect, self.EventServiceChanged )
        
        if self._canvas_key is not None:
            
            CG.client_controller.sub( self, 'CanvasHasNewMedia', 'canvas_new_display_media' )
            
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ 'global', 'media', 'main_gui' ] )
        
        self._UpdatePageTabNames()
        
        QP.CallAfter( self._SetSearchFocus )
        
    
    def _GetContentUpdatePackages( self ):
        
        content_update_packages = []
        
        for page in self._tag_services.GetPages():
            
            content_update_packages.extend( page.GetContentUpdatePackages() )
            
        
        return content_update_packages
        
    
    def _SetSearchFocus( self ):
        
        current_page = typing.cast( ManageTagsPanel._Panel, self._tag_services.currentWidget() )
        
        if current_page is not None:
            
            current_page.SetTagBoxFocus()
            
        
    
    def _UpdatePageTabNames( self ):
        
        for index in range( self._tag_services.count() ):
            
            page = typing.cast( ManageTagsPanel._Panel, self._tag_services.widget( index ) )
            
            service_key = page.GetServiceKey()
            
            service_name = CG.client_controller.services_manager.GetServiceName( service_key )
            
            num_tags = page.GetTagCount()
            
            if num_tags > 0:
                
                tab_name = f'{service_name} ({num_tags})'
                
            else:
                
                tab_name = service_name
                
            
            if page.HasChanges():
                
                tab_name += ' *'
                
            
            if self._tag_services.tabText( index ) != tab_name:
                
                self._tag_services.setTabText( index, tab_name )
                
            
        
    
    def CanvasHasNewMedia( self, canvas_key, new_media_singleton ):
        
        if canvas_key == self._canvas_key:
            
            if new_media_singleton is not None:
                
                self._current_media = ( new_media_singleton.Duplicate(), )
                
                for page in self._tag_services.GetPages():
                    
                    page.SetMedia( self._current_media )
                    
                
                self._UpdatePageTabNames()
                
            
        
    
    def CleanBeforeDestroy( self ):
        
        ClientGUIScrolledPanels.ManagePanel.CleanBeforeDestroy( self )
        
        for page in self._tag_services.GetPages():
            
            page.CleanBeforeDestroy()
            
        
    
    def CommitChanges( self ):
        
        content_update_packages = self._GetContentUpdatePackages()
        
        for content_update_package in content_update_packages:
            
            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
            
        
    
    def EventServiceChanged( self, index ):
        
        if not self or not QP.isValid( self ): # actually did get a runtime error here, on some Linux WM dialog shutdown
            
            return
            
        
        if self.sender() != self._tag_services:
            
            return
            
        
        current_page: typing.Optional[ ManageTagsPanel._Panel ] = self._tag_services.currentWidget()
        
        if current_page is not None:
            
            CG.client_controller.CallAfterQtSafe( current_page, 'setting page focus', current_page.SetTagBoxFocus )
            
        
        if CG.client_controller.new_options.GetBoolean( 'save_default_tag_service_tab_on_change' ):
            
            CG.client_controller.new_options.SetKey( 'default_tag_service_tab', current_page.GetServiceKey() )
            
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_MANAGE_FILE_TAGS:
                
                self._OKParent()
                
            elif action == CAC.SIMPLE_FOCUS_MEDIA_VIEWER:
                
                tlws = ClientGUIFunctions.GetTLWParents( self )
                
                from hydrus.client.gui.canvas import ClientGUICanvasFrame
                
                command_processed = False
                
                for tlw in tlws:
                    
                    if isinstance( tlw, ClientGUICanvasFrame.CanvasFrame ):
                        
                        tlw.TakeFocusForUser()
                        
                        command_processed = True
                        
                        break
                        
                    
                
            elif action == CAC.SIMPLE_SET_SEARCH_FOCUS:
                
                self._SetSearchFocus()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def MovePageRight( self ):
        
        self._tag_services.SelectRight()
        
        self._SetSearchFocus()
        
    
    def MovePageLeft( self ):
        
        self._tag_services.SelectLeft()
        
        self._SetSearchFocus()
        
    
    def ShowNext( self ):
        
        if self._canvas_key is not None:
            
            CG.client_controller.pub( 'canvas_show_next', self._canvas_key )
            
        
    
    def ShowPrevious( self ):
        
        if self._canvas_key is not None:
            
            CG.client_controller.pub( 'canvas_show_previous', self._canvas_key )
            
        
    
    def UserIsOKToCancel( self ):
        
        content_update_packages = self._GetContentUpdatePackages()
        
        if len( content_update_packages ) > 0:
            
            message = 'Are you sure you want to cancel? You have uncommitted changes that will be lost.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
    
    class _Panel( CAC.ApplicationCommandProcessorMixin, QW.QWidget ):
        
        okSignal = QC.Signal()
        movePageLeft = QC.Signal()
        movePageRight = QC.Signal()
        showPrevious = QC.Signal()
        showNext = QC.Signal()
        valueChanged = QC.Signal()
        
        def __init__( self, parent, location_context: ClientLocation.LocationContext, tag_service_key, tag_presentation_location: int, media: typing.List[ ClientMedia.MediaSingleton ], immediate_commit, canvas_key = None ):
            
            super().__init__( parent )
            
            self._location_context = location_context
            self._tag_service_key = tag_service_key
            self._tag_presentation_location = tag_presentation_location
            self._immediate_commit = immediate_commit
            self._canvas_key = canvas_key
            
            self._pending_content_update_packages = []
            
            self._service = CG.client_controller.services_manager.GetService( self._tag_service_key )
            
            self._i_am_local_tag_service = self._service.GetServiceType() == HC.LOCAL_TAG
            
            tags_panel = QW.QWidget( self )
            
            self._tags_box_sorter = ClientGUIListBoxes.StaticBoxSorterForListBoxTags( tags_panel, 'tags', self._tag_presentation_location, show_siblings_sort = True )
            
            self._tags_box = ClientGUIListBoxes.ListBoxTagsMediaTagsDialog( self._tags_box_sorter, self._tag_presentation_location, self.EnterTags, self.RemoveTags )
            
            self._tags_box_sorter.SetTagsBox( self._tags_box )
            
            #
            
            self._new_options = CG.client_controller.new_options
            
            if self._i_am_local_tag_service:
                
                text = 'remove all/selected tags'
                
            else:
                
                text = 'petition to remove all/selected tags'
                
            
            self._remove_tags = ClientGUICommon.BetterButton( self._tags_box_sorter, text, self._RemoveTagsButton )
            
            self._copy_button = ClientGUICommon.BetterBitmapButton( self._tags_box_sorter, CC.global_pixmaps().copy, self._Copy )
            self._copy_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Copy selected tags to the clipboard. If none are selected, copies all.' ) )
            
            self._paste_button = ClientGUICommon.BetterBitmapButton( self._tags_box_sorter, CC.global_pixmaps().paste, self._Paste )
            self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Paste newline-separated tags from the clipboard into here.' ) )
            
            self._show_deleted = False
            
            menu_items = []
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'allow_remove_on_manage_tags_input' )
            
            menu_items.append( ( 'check', 'allow remove/petition result on tag input for already existing tag', 'If checked, inputting a tag that already exists will try to remove it.', check_manager ) )
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'yes_no_on_remove_on_manage_tags' )
            
            menu_items.append( ( 'check', 'confirm remove/petition tags on explicit delete actions', 'If checked, clicking the remove/petition tags button (or hitting the deleted key on the list) will first confirm the action with a yes/no dialog.', check_manager ) )
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'ac_select_first_with_count' )
            
            menu_items.append( ( 'check', 'select the first tag result with actual count', 'If checked, when results come in, the typed entry, if it has no count, will be skipped.', check_manager ) )
            
            check_manager = ClientGUICommon.CheckboxManagerCalls( self._FlipShowDeleted, lambda: self._show_deleted )
            
            menu_items.append( ( 'check', 'show deleted', 'Show deleted tags, if any.', check_manager ) )
            
            menu_items.append( ( 'separator', 0, 0, 0 ) )
            
            menu_items.append( ( 'normal', 'migrate tags for these files', 'Migrate the tags for the files used to launch this manage tags panel.', self._MigrateTags ) )
            
            if not self._i_am_local_tag_service and self._service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_MODERATE ):
                
                menu_items.append( ( 'separator', 0, 0, 0 ) )
                
                menu_items.append( ( 'normal', 'modify users who added the selected tags', 'Modify the users who added the selected tags.', self._ModifyMappers ) )
                
            
            self._incremental_tagging_button = ClientGUICommon.BetterButton( self._tags_box_sorter, HC.UNICODE_PLUS_OR_MINUS, self._DoIncrementalTagging )
            self._incremental_tagging_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Incremental Tagging' ) )
            self._incremental_tagging_button.setVisible( len( media ) > 1 )
            
            width = ClientGUIFunctions.ConvertTextToPixelWidth( self._incremental_tagging_button, 5 )
            self._incremental_tagging_button.setFixedWidth( width )
            
            self._cog_button = ClientGUIMenuButton.MenuBitmapButton( self._tags_box_sorter, CC.global_pixmaps().cog, menu_items )
            
            #
            
            self._add_tag_box = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( tags_panel, self.AddTags, self._location_context, self._tag_service_key )
            
            self._add_tag_box.movePageLeft.connect( self.movePageLeft )
            self._add_tag_box.movePageRight.connect( self.movePageRight )
            self._add_tag_box.showPrevious.connect( self.showPrevious )
            self._add_tag_box.showNext.connect( self.showNext )
            self._add_tag_box.externalCopyKeyPressEvent.connect( self._tags_box.keyPressEvent )
            
            self._add_tag_box.nullEntered.connect( self.OK )
            
            self._tags_box.tagsChanged.connect( self._add_tag_box.SetContextTags )
            
            self._tags_box.SetTagServiceKey( self._tag_service_key )
            
            self._suggested_tags = ClientGUITagSuggestions.SuggestedTagsPanel( self, self._tag_service_key, self._tag_presentation_location, len( media ) == 1, self.AddTags )
            
            self.SetMedia( media )
            
            button_hbox = QP.HBoxLayout()
            
            QP.AddToLayout( button_hbox, self._remove_tags, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( button_hbox, self._copy_button, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( button_hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( button_hbox, self._incremental_tagging_button, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( button_hbox, self._cog_button, CC.FLAGS_CENTER )
            
            self._tags_box_sorter.Add( button_hbox, CC.FLAGS_ON_RIGHT )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._tags_box_sorter, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( vbox, self._add_tag_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            tags_panel.setLayout( vbox )
            
            #
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._suggested_tags, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( hbox, tags_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ 'global', 'main_gui' ] )
            
            self.setLayout( hbox )
            
            if self._immediate_commit:
                
                CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
                
            
            self._suggested_tags.mouseActivationOccurred.connect( self.SetTagBoxFocus )
            
            self._tags_box.tagsSelected.connect( self._suggested_tags.SetSelectedTags )
            
        
        def _EnterTags( self, tags, only_add = False, only_remove = False, forced_reason = None ):
            
            tags = HydrusTags.CleanTags( tags )
            
            if not self._i_am_local_tag_service and self._service.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_MODERATE ):
                
                forced_reason = 'Entered by a janitor.'
                
            
            tags_managers = [ m.GetTagsManager() for m in self._media ]
            
            # TODO: All this should be extracted to another object that does some prep work and then answers questions like 'can I add this tag?' or 'what are the human-text/content-action choices for this tag?'
            # then we'll be able to do quick-add in other locations and so on with less hassle!
            
            currents = [ tags_manager.GetCurrent( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ) for tags_manager in tags_managers ]
            pendings = [ tags_manager.GetPending( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ) for tags_manager in tags_managers ]
            petitioneds = [ tags_manager.GetPetitioned( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ) for tags_manager in tags_managers ]
            
            num_files = len( self._media )
            
            # let's figure out what these tags can mean for the media--add, remove, or what?
            
            choices = collections.defaultdict( list )
            
            for tag in tags:
                
                num_current = sum( ( 1 for current in currents if tag in current ) )
                
                if self._i_am_local_tag_service:
                    
                    if not only_remove:
                        
                        if num_current < num_files:
                            
                            num_non_current = num_files - num_current
                            
                            choices[ HC.CONTENT_UPDATE_ADD ].append( ( tag, num_non_current ) )
                            
                        
                    
                    if not only_add:
                        
                        if num_current > 0:
                            
                            choices[ HC.CONTENT_UPDATE_DELETE ].append( ( tag, num_current ) )
                            
                        
                    
                else:
                    
                    num_pending = sum( ( 1 for pending in pendings if tag in pending ) )
                    num_petitioned = sum( ( 1 for petitioned in petitioneds if tag in petitioned ) )
                    
                    if not only_remove:
                        
                        # it is possible to have content petitioned without being current
                        # we don't want to pend in this case!
                        
                        if num_current + num_pending + num_petitioned < num_files:
                            
                            num_pendable = num_files - ( num_current + num_pending + num_petitioned )
                            
                            choices[ HC.CONTENT_UPDATE_PEND ].append( ( tag, num_pendable ) )
                            
                        
                    
                    if not only_add:
                        
                        # although it is technically possible to petition content that doesn't exist yet...
                        # for human uses, we do not want to provide petition as an option unless it is already current
                        
                        if num_current > num_petitioned and not only_add:
                            
                            num_petitionable = num_current - num_petitioned
                            
                            choices[ HC.CONTENT_UPDATE_PETITION ].append( ( tag, num_petitionable ) )
                            
                        
                        if num_pending > 0 and not only_add:
                            
                            choices[ HC.CONTENT_UPDATE_RESCIND_PEND ].append( ( tag, num_pending ) )
                            
                        
                    
                    if not only_remove:
                        
                        if num_petitioned > 0:
                            
                            choices[ HC.CONTENT_UPDATE_RESCIND_PETITION ].append( ( tag, num_petitioned ) )
                            
                        
                    
                
            
            if len( choices ) == 0:
                
                return
                
            
            # now we have options, let's ask the user what they want to do
            
            if len( choices ) == 1:
                
                [ ( choice_action, tag_counts ) ] = list( choices.items() )
                
                tags = { tag for ( tag, count ) in tag_counts }
                
            else:
                
                bdc_choices = []
                
                preferred_order = [ HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_RESCIND_PEND, HC.CONTENT_UPDATE_PETITION, HC.CONTENT_UPDATE_RESCIND_PETITION ]
                
                choice_text_lookup = {}
                
                choice_text_lookup[ HC.CONTENT_UPDATE_ADD ] = 'add'
                choice_text_lookup[ HC.CONTENT_UPDATE_DELETE ] = 'delete'
                choice_text_lookup[ HC.CONTENT_UPDATE_PEND ] = 'pend (add)'
                choice_text_lookup[ HC.CONTENT_UPDATE_PETITION ] = 'petition to remove'
                choice_text_lookup[ HC.CONTENT_UPDATE_RESCIND_PEND ] = 'undo pend'
                choice_text_lookup[ HC.CONTENT_UPDATE_RESCIND_PETITION ] = 'undo petition to remove'
                
                choice_tooltip_lookup = {}
                
                choice_tooltip_lookup[ HC.CONTENT_UPDATE_ADD ] = 'this adds the tags to this local tag service'
                choice_tooltip_lookup[ HC.CONTENT_UPDATE_DELETE ] = 'this deletes the tags from this local tag service'
                choice_tooltip_lookup[ HC.CONTENT_UPDATE_PEND ] = 'this pends the tags to be added to this tag repository when you upload'
                choice_tooltip_lookup[ HC.CONTENT_UPDATE_PETITION ] = 'this petitions the tags for deletion from this tag repository when you upload'
                choice_tooltip_lookup[ HC.CONTENT_UPDATE_RESCIND_PEND ] = 'this rescinds the currently pending tags, so they will not be added'
                choice_tooltip_lookup[ HC.CONTENT_UPDATE_RESCIND_PETITION ] = 'this rescinds the current tag petitions, so they will not be deleted'
                
                for choice_action in preferred_order:
                    
                    if choice_action not in choices:
                        
                        continue
                        
                    
                    choice_text_prefix = choice_text_lookup[ choice_action ]
                    
                    tag_counts = choices[ choice_action ]
                    
                    choice_tags = { tag for ( tag, count ) in tag_counts }
                    
                    if len( choice_tags ) == 1:
                        
                        [ ( tag, count ) ] = tag_counts
                        
                        text = '{} "{}" for {} files'.format( choice_text_prefix, HydrusText.ElideText( tag, 64 ), HydrusNumbers.ToHumanInt( count ) )
                        
                    else:
                        
                        text = '{} {} tags'.format( choice_text_prefix, HydrusNumbers.ToHumanInt( len( choice_tags ) ) )
                        
                    
                    data = ( choice_action, choice_tags )
                    
                    t_c_lines = [ choice_tooltip_lookup[ choice_action ] ]
                    
                    if len( tag_counts ) > 25:
                        
                        t_c = tag_counts[:25]
                        
                    else:
                        
                        t_c = tag_counts
                        
                    
                    t_c_lines.extend( ( '{} - {} files'.format( tag, HydrusNumbers.ToHumanInt( count ) ) for ( tag, count ) in t_c ) )
                    
                    if len( tag_counts ) > 25:
                        
                        t_c_lines.append( 'and {} others'.format( HydrusNumbers.ToHumanInt( len( tag_counts ) - 25 ) ) )
                        
                    
                    tooltip = '\n'.join( t_c_lines )
                    
                    bdc_choices.append( ( text, data, tooltip ) )
                    
                
                try:
                    
                    if len( tags ) > 1:
                        
                        message = 'The file{} some of those tags, but not all, so there are different things you can do.'.format( 's have' if len( self._media ) > 1 else ' has' )
                        
                    else:
                        
                        message = 'Of the {} files being managed, some have that tag, but not all of them do, so there are different things you can do.'.format( HydrusNumbers.ToHumanInt( len( self._media ) ) )
                        
                    
                    ( choice_action, tags ) = ClientGUIDialogsQuick.SelectFromListButtons( self, 'What would you like to do?', bdc_choices, message = message )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            
            reason = None
            
            if choice_action == HC.CONTENT_UPDATE_PETITION:
                
                if forced_reason is None:
                    
                    # add the easy reason buttons here
                    
                    if len( tags ) == 1:
                        
                        ( tag, ) = tags
                        
                        tag_text = '"' + tag + '"'
                        
                    else:
                        
                        tag_text = 'the ' + HydrusNumbers.ToHumanInt( len( tags ) ) + ' tags'
                        
                    
                    message = 'Enter a reason for ' + tag_text + ' to be removed. A janitor will review your petition.'
                    
                    fixed_suggestions = [
                        'mangled parse/typo',
                        'not applicable/incorrect',
                        'clearing mass-pasted junk',
                        'splitting filename/title/etc... into individual tags'
                    ]
                    
                    suggestions = CG.client_controller.new_options.GetRecentPetitionReasons( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE )
                    
                    suggestions.extend( fixed_suggestions )
                    
                    with ClientGUIDialogs.DialogTextEntry( self, message, suggestions = suggestions ) as dlg:
                        
                        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                            
                            reason = dlg.GetValue()
                            
                            if reason not in fixed_suggestions:
                                
                                CG.client_controller.new_options.PushRecentPetitionReason( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, reason )
                                
                            
                        else:
                            
                            return
                            
                        
                    
                else:
                    
                    reason = forced_reason
                    
                
            
            # we have an action and tags, so let's effect the content updates
            
            content_updates_for_this_call = []
            
            recent_tags = set()
            
            medias_and_tags_managers = [ ( m, m.GetTagsManager() ) for m in self._media ]
            medias_and_sets_of_tags = [ ( m, tm.GetCurrent( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ), tm.GetPending( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ), tm.GetPetitioned( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ) ) for ( m, tm ) in medias_and_tags_managers ]
            
            # there is a big CPU hit here as every time you ProcessContentUpdatePackage, the tagsmanagers need to regen caches lmao
            # so if I refetch current tags etc... for every tag loop, we end up getting 16 million tagok calls etc...
            # however, as tags is a set, thus with unique members, let's say for now this is ok, don't need to regen just to consult current
            
            for tag in tags:
                
                if choice_action == HC.CONTENT_UPDATE_ADD:
                    
                    media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag not in mc ]
                    
                elif choice_action == HC.CONTENT_UPDATE_DELETE:
                    
                    media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag in mc ]
                    
                elif choice_action == HC.CONTENT_UPDATE_PEND:
                    
                    # check petitioned too, we don't want both at once!
                    media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag not in mc and tag not in mp and tag not in mpt ]
                    
                elif choice_action == HC.CONTENT_UPDATE_PETITION:
                    
                    # check current even though we don't have to (it makes it more human to say things need to be current here before being petitioned)
                    # check pending too, we don't want both at once!
                    media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag in mc and tag not in mpt and tag not in mp ]
                    
                elif choice_action == HC.CONTENT_UPDATE_RESCIND_PEND:
                    
                    media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag in mp ]
                    
                elif choice_action == HC.CONTENT_UPDATE_RESCIND_PETITION:
                    
                    media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag in mpt ]
                    
                else:
                    
                    raise Exception( 'Unknown tag action choice!' )
                    
                
                hashes = set( itertools.chain.from_iterable( ( m.GetHashes() for m in media_to_affect ) ) )
                
                if len( hashes ) > 0:
                    
                    content_updates = []
                    
                    if choice_action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_PEND ):
                        
                        recent_tags.add( tag )
                        
                    
                    content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, choice_action, ( tag, hashes ), reason = reason ) )
                    
                    if len( content_updates ) > 0:
                        
                        if not self._immediate_commit:
                            
                            for m in media_to_affect:
                                
                                mt = m.GetTagsManager()
                                
                                for content_update in content_updates:
                                    
                                    mt.ProcessContentUpdate( self._tag_service_key, content_update )
                                    
                                
                            
                        
                        content_updates_for_this_call.extend( content_updates )
                        
                    
                
            
            num_recent_tags = CG.client_controller.new_options.GetNoneableInteger( 'num_recent_tags' )
            
            if len( recent_tags ) > 0 and num_recent_tags is not None:
                
                recent_tags = list( recent_tags )
                
                if len( recent_tags ) > num_recent_tags:
                    
                    recent_tags = random.sample( recent_tags, num_recent_tags )
                    
                
                CG.client_controller.Write( 'push_recent_tags', self._tag_service_key, recent_tags )
                
            
            if len( content_updates_for_this_call ) > 0:
                
                content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( self._tag_service_key, content_updates_for_this_call )
                
                if self._immediate_commit:
                    
                    CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
                    
                else:
                    
                    self._pending_content_update_packages.append( content_update_package )
                    
                    self._suggested_tags.MediaUpdated()
                    
                
            
            self._tags_box.SetTagsByMedia( self._media )
            
            self.valueChanged.emit()
            
        
        def _Copy( self ):
            
            tags = list( self._tags_box.GetSelectedTags() )
            
            if len( tags ) == 0:
                
                ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientMedia.GetMediasTagCount( self._media, self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE )
                
                tags = set( current_tags_to_count.keys() ).union( pending_tags_to_count.keys() )
                
            
            if len( tags ) > 0:
                
                tags = HydrusTags.SortNumericTags( tags )
                
                text = '\n'.join( tags )
                
                CG.client_controller.pub( 'clipboard', 'text', text )
                
            
        
        def _DoIncrementalTagging( self ):
            
            title = 'Incremental Tagging'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                
                panel = IncrementalTaggingPanel( dlg, self._tag_service_key, self._media )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    content_update_package = panel.GetValue()
                    
                    if content_update_package.HasContent():
                        
                        if self._immediate_commit:
                            
                            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
                            
                        else:
                            
                            self._pending_content_update_packages.append( content_update_package )
                            
                            self.ProcessContentUpdatePackage( content_update_package )
                            
                        
                    
                
            
        
        def _FlipShowDeleted( self ):
            
            self._show_deleted = not self._show_deleted
            
            self._tags_box.SetShow( 'deleted', self._show_deleted )
            
        
        def _MigrateTags( self ):
            
            hashes = set()
            
            for m in self._media:
                
                hashes.update( m.GetHashes() )
                
            
            def do_it( tag_service_key, hashes ):
                
                tlw = CG.client_controller.GetMainTLW()
                
                frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( tlw, 'migrate tags' )
                
                panel = ClientGUIMigrateTags.MigrateTagsPanel( frame, self._tag_service_key, hashes )
                
                frame.SetPanel( panel )
                
            
            QP.CallAfter( do_it, self._tag_service_key, hashes )
            
            self.OK()
            
        
        def _ModifyMappers( self ):
            
            contents = []
            
            tags = self._tags_box.GetSelectedTags()
            
            if len( tags ) == 0:
                
                ClientGUIDialogsMessage.ShowWarning( self, 'Please select some tags first!' )
                
                return
                
            
            hashes_and_current_tags = [ ( m.GetHashes(), m.GetTagsManager().GetCurrent( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ) ) for m in self._media ]
            
            for tag in tags:
                
                hashes_iter = itertools.chain.from_iterable( ( hashes for ( hashes, current_tags ) in hashes_and_current_tags if tag in current_tags ) )
                
                contents.extend( [ HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPING, ( tag, hash ) ) for hash in hashes_iter ] )
                
            
            if len( contents ) > 0:
                
                subject_account_identifiers = [ HydrusNetwork.AccountIdentifier( content = content ) for content in contents ]
                
                frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self.window().parentWidget(), 'manage accounts' )
                
                panel = ClientGUIHydrusNetwork.ModifyAccountsPanel( frame, self._tag_service_key, subject_account_identifiers )
                
                frame.SetPanel( panel )
                
            
        
        def _Paste( self ):
            
            try:
                
                raw_text = CG.client_controller.GetClipboardText()
                
            except HydrusExceptions.DataMissing as e:
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting tags!', str(e) )
                
                return
                
            
            try:
                
                tags = HydrusText.DeserialiseNewlinedTexts( raw_text )
                
                tags = HydrusTags.CleanTags( tags )
                
                self.AddTags( tags, only_add = True )
                
            except Exception as e:
                
                ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'Lines of tags', e )
                
            
        
        def _RemoveTagsButton( self ):
            
            tags_managers = [ m.GetTagsManager() for m in self._media ]
            
            removable_tags = set()
            
            for tags_manager in tags_managers:
                
                removable_tags.update( tags_manager.GetCurrent( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ) )
                removable_tags.update( tags_manager.GetPending( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ) )
                
            
            selected_tags = list( self._tags_box.GetSelectedTags() )
            
            if len( selected_tags ) == 0:
                
                tags_to_remove = list( removable_tags )
                
            else:
                
                tags_to_remove = [ tag for tag in selected_tags if tag in removable_tags ]
                
            
            tags_to_remove = HydrusTags.SortNumericTags( tags_to_remove )
            
            self.RemoveTags( tags_to_remove )
            
        
        def AddTags( self, tags, only_add = False ):
            
            if not self._new_options.GetBoolean( 'allow_remove_on_manage_tags_input' ):
                
                only_add = True
                
            
            if len( tags ) > 0:
                
                self.EnterTags( tags, only_add = only_add )
                
            
        
        def CleanBeforeDestroy( self ):
            
            self._add_tag_box.CancelCurrentResultsFetchJob()
            
        
        def ClearMedia( self ):
            
            self.SetMedia( set() )
            
        
        def EnterTags( self, tags, only_add = False ):
            
            if len( tags ) > 0:
                
                self._EnterTags( tags, only_add = only_add )
                
            
        
        def GetContentUpdatePackages( self ):
            
            return self._pending_content_update_packages
            
        
        def GetTagCount( self ):
            
            return self._tags_box.GetNumTerms()
            
        
        def GetServiceKey( self ):
            
            return self._tag_service_key
            
        
        def HasChanges( self ):
            
            return len( self._pending_content_update_packages ) > 0
            
        
        def OK( self ):
            
            self.okSignal.emit()
            
        
        def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
            
            command_processed = True
            
            if command.IsSimpleCommand():
                
                action = command.GetSimpleAction()
                
                if action == CAC.SIMPLE_SET_SEARCH_FOCUS:
                    
                    self.SetTagBoxFocus()
                    
                elif action in ( CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_FAVOURITE_TAGS, CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_RELATED_TAGS, CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_FILE_LOOKUP_SCRIPT_TAGS, CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_RECENT_TAGS ):
                    
                    self._suggested_tags.TakeFocusForUser( action )
                    
                elif action == CAC.SIMPLE_REFRESH_RELATED_TAGS:
                    
                    self._suggested_tags.RefreshRelatedThorough()
                    
                else:
                    
                    command_processed = False
                    
                
            else:
                
                command_processed = False
                
            
            return command_processed
            
        
        def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
            
            for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
                
                for content_update in content_updates:
                    
                    for m in self._media:
                        
                        if HydrusLists.SetsIntersect( m.GetHashes(), content_update.GetHashes() ):
                            
                            m.GetMediaResult().ProcessContentUpdate( service_key, content_update )
                            
                        
                    
                
            
            self._tags_box.SetTagsByMedia( self._media )
            
            self.valueChanged.emit()
            
            self._suggested_tags.MediaUpdated()
            
        
        def RemoveTags( self, tags ):
            
            if len( tags ) > 0:
                
                if self._new_options.GetBoolean( 'yes_no_on_remove_on_manage_tags' ):
                    
                    if len( tags ) < 10:
                        
                        message = 'Are you sure you want to remove these tags:'
                        message += '\n' * 2
                        message += '\n'.join( ( HydrusText.ElideText( tag, 64 ) for tag in tags ) )
                        
                    else:
                        
                        message = 'Are you sure you want to remove these ' + HydrusNumbers.ToHumanInt( len( tags ) ) + ' tags?'
                        
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.DialogCode.Accepted:
                        
                        return
                        
                    
                
                self._EnterTags( tags, only_remove = True )
                
            
        
        def SetMedia( self, media ):
            
            if media is None:
                
                media = set()
                
            
            self._media = media
            
            self._tags_box.SetTagsByMedia( self._media )
            
            self.valueChanged.emit()
            
            self._suggested_tags.SetMedia( media )
            
        
        def SetTagBoxFocus( self ):
            
            self._add_tag_box.setFocus( QC.Qt.FocusReason.OtherFocusReason )
            
        

class ManageTagParents( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, tags = None ):
        
        super().__init__( parent )
        
        if CG.client_controller.new_options.GetBoolean( 'use_listbook_for_tag_service_panels' ):
            
            self._tag_services = ClientGUIListBook.ListBook( self )
            
        else:
            
            self._tag_services = ClientGUICommon.BetterNotebook( self )
            
        
        #
        
        default_tag_service_key = CG.client_controller.new_options.GetKey( 'default_tag_service_tab' )
        
        services = list( CG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) ) )
        
        services.extend( CG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) ) )
        
        for service in services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            page = self._Panel( self._tag_services, service_key, tags )
            
            self._tag_services.addTab( page, name )
            
            if service_key == default_tag_service_key:
                
                # Py 3.11/PyQt6 6.5.0/two tabs/total tab characters > ~12/select second tab during init = first tab disappears bug
                QP.CallAfter( self._tag_services.setCurrentWidget, page )
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._tag_services, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._tag_services.currentChanged.connect( self._SaveDefaultTagServiceKey )
        
    
    def _SaveDefaultTagServiceKey( self ):
        
        if CG.client_controller.new_options.GetBoolean( 'save_default_tag_service_tab_on_change' ):
            
            current_page = typing.cast( ManageTagParents._Panel, self._tag_services.currentWidget() )
            
            CG.client_controller.new_options.SetKey( 'default_tag_service_tab', current_page.GetServiceKey() )
            
        
    
    def _SetSearchFocus( self ):
        
        current_page = typing.cast( ManageTagParents._Panel, self._tag_services.currentWidget() )
        
        if current_page is not None:
            
            current_page.SetTagBoxFocus()
            
        
    
    def CommitChanges( self ):
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        for page in self._tag_services.GetPages():
            
            ( service_key, content_updates ) = page.GetContentUpdates()
            
            content_update_package.AddContentUpdates( service_key, content_updates )
            
        
        if content_update_package.HasContent():
            
            CG.client_controller.Write( 'content_updates', content_update_package )
            
        
    
    def UserIsOKToOK( self ):
        
        current_page = typing.cast( ManageTagParents._Panel, self._tag_services.currentWidget() )
        
        if current_page.HasUncommittedPair():
            
            message = 'Are you sure you want to OK? You have an uncommitted pair.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
    
    class _Panel( QW.QWidget ):
        
        def __init__( self, parent, service_key, tags = None ):
            
            super().__init__( parent )
            
            self._current_pertinent_tags = set()
            
            self._service_key = service_key
            
            self._service = CG.client_controller.services_manager.GetService( self._service_key )
            
            self._i_am_local_tag_service = self._service.GetServiceType() == HC.LOCAL_TAG
            
            self._parent_action_context = ClientGUITagActions.ParentActionContext( self._service_key )
            
            self._current_new = None
            
            self._show_all = QW.QCheckBox( self )
            self._show_pending_and_petitioned = QW.QCheckBox( self )
            self._pursue_whole_chain = QW.QCheckBox( self )
            
            tt = 'When you enter tags in the bottom boxes, the upper list is filtered to pertinent related relationships.'
            tt += '\n' * 2
            tt += 'With this off, it will show (grand)children and (grand)parents only. With it on, it walks up and down the full chain, including cousins. This can be overwhelming!'
            
            self._pursue_whole_chain.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
            # leave up here since other things have updates based on them
            self._children = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, self._service_key, tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, height_num_chars = 4 )
            self._parents = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, self._service_key, tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, height_num_chars = 4 )
            
            self._listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
            
            model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_TAG_PARENTS.ID, self._ConvertPairToDisplayTuple, self._ConvertPairToSortTuple )
            
            self._tag_parents = ClientGUIListCtrl.BetterListCtrlTreeView( self._listctrl_panel, 6, model, delete_key_callback = self._DeleteSelectedRows, activation_callback = self._DeleteSelectedRows )
            
            self._listctrl_panel.SetListCtrl( self._tag_parents )
            
            self._listctrl_panel.AddButton( 'add', self._AddButton, enabled_check_func = self._CanAddFromCurrentInput )
            self._listctrl_panel.AddButton( 'delete', self._DeleteSelectedRows, enabled_only_on_selection = True )
            
            self._tag_parents.Sort()
            
            menu_items = []
            
            menu_items.append( ( 'normal', 'from clipboard', 'Load siblings from text in your clipboard.', HydrusData.Call( self._ImportFromClipboard, False ) ) )
            menu_items.append( ( 'normal', 'from clipboard (only add pairs--no deletions)', 'Load siblings from text in your clipboard.', HydrusData.Call( self._ImportFromClipboard, True ) ) )
            menu_items.append( ( 'normal', 'from .txt file', 'Load siblings from a .txt file.', HydrusData.Call( self._ImportFromTXT, False ) ) )
            menu_items.append( ( 'normal', 'from .txt file (only add pairs--no deletions)', 'Load siblings from a .txt file.', HydrusData.Call( self._ImportFromTXT, True ) ) )
            
            self._listctrl_panel.AddMenuButton( 'import', menu_items )
            
            menu_items = []
            
            menu_items.append( ( 'normal', 'to clipboard', 'Save selected siblings to your clipboard.', self._ExportToClipboard ) )
            menu_items.append( ( 'normal', 'to .txt file', 'Save selected siblings to a .txt file.', self._ExportToTXT ) )
            
            self._listctrl_panel.AddMenuButton( 'export', menu_items, enabled_only_on_selection = True )
            
            ( gumpf, preview_height ) = ClientGUIFunctions.ConvertTextToPixels( self._children, ( 12, 6 ) )
            
            self._children.setMinimumHeight( preview_height )
            self._parents.setMinimumHeight( preview_height )
            
            default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
            
            self._children_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterChildren, default_location_context, service_key, show_paste_button = True )
            
            self._parents_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterParents, default_location_context, service_key, show_paste_button = True )
            
            self._children.tagsChanged.connect( self._children_input.SetContextTags )
            self._parents.tagsChanged.connect( self._parents_input.SetContextTags )
            
            self._children_input.externalCopyKeyPressEvent.connect( self._children.keyPressEvent )
            self._parents_input.externalCopyKeyPressEvent.connect( self._parents.keyPressEvent )
            
            #
            
            self._status_st = ClientGUICommon.BetterStaticText( self,'Files with any tag on the left will also be given the tags on the right.' )
            self._sync_status_st = ClientGUICommon.BetterStaticText( self, '' )
            self._sync_status_st.setWordWrap( True )
            self._count_st = ClientGUICommon.BetterStaticText( self, '' )
            
            self._wipe_workspace = ClientGUICommon.BetterButton( self, 'wipe workspace', self._WipeWorkspace )
            self._wipe_workspace.setEnabled( False )
            
            children_vbox = QP.VBoxLayout()
            
            QP.AddToLayout( children_vbox, ClientGUICommon.BetterStaticText( self, label = 'set children' ), CC.FLAGS_CENTER )
            QP.AddToLayout( children_vbox, self._children, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            parents_vbox = QP.VBoxLayout()
            
            QP.AddToLayout( parents_vbox, ClientGUICommon.BetterStaticText( self, label = 'set parents' ), CC.FLAGS_CENTER )
            QP.AddToLayout( parents_vbox, self._parents, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            tags_box = QP.HBoxLayout()
            
            QP.AddToLayout( tags_box, children_vbox, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( tags_box, parents_vbox, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            input_box = QP.HBoxLayout()
            
            QP.AddToLayout( input_box, self._children_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( input_box, self._parents_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            workspace_hbox = QP.HBoxLayout()
            
            QP.AddToLayout( workspace_hbox, self._wipe_workspace, CC.FLAGS_SIZER_CENTER )
            QP.AddToLayout( workspace_hbox, self._count_st, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._sync_status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._show_all, self, 'show all pairs' ), CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._show_pending_and_petitioned, self, 'show pending and petitioned groups' ), CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._pursue_whole_chain, self, 'show whole chains' ), CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, workspace_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( vbox, tags_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, input_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.setLayout( vbox )
            
            #
            
            self._listctrl_async_updater = self._InitialiseListCtrlAsyncUpdater()
            
            self._children.listBoxChanged.connect( self._listctrl_async_updater.update )
            self._parents.listBoxChanged.connect( self._listctrl_async_updater.update )
            self._show_all.clicked.connect( self._listctrl_async_updater.update )
            self._show_pending_and_petitioned.clicked.connect( self._listctrl_async_updater.update )
            self._pursue_whole_chain.clicked.connect( self._listctrl_async_updater.update )
            
            self._children_input.tagsPasted.connect( self.EnterChildrenOnlyAdd )
            self._parents_input.tagsPasted.connect( self.EnterParentsOnlyAdd )
            
            self._parent_action_context.RegisterQtUpdateCall( self, self._listctrl_async_updater.update )
            
            self._STARTInitialisation( tags, self._service_key )
            
        
        def _AddButton( self ):
            
            children = self._children.GetTags()
            parents = self._parents.GetTags()
            
            if len( children ) > 0 and len( parents ) > 0:
                
                pairs = list( itertools.product( children, parents ) )
                
                self._parent_action_context.EnterPairs( self, pairs )
                
                self._children.SetTags( [] )
                self._parents.SetTags( [] )
                
            
        
        def _CanAddFromCurrentInput( self ):
            
            if len( self._children.GetTags() ) == 0 or len( self._parents.GetTags() ) == 0:
                
                return False
                
            
            return True
            
        
        def _ConvertPairToDisplayTuple( self, pair ):
            
            ( old, new ) = pair
            
            ( in_pending, in_petitioned, reason ) = self._parent_action_context.GetPairListCtrlInfo( pair )
            
            note = reason
            
            if in_pending or in_petitioned:
                
                if in_pending:
                    
                    status = HC.CONTENT_STATUS_PENDING
                    
                else:
                    
                    status = HC.CONTENT_STATUS_PETITIONED
                    
                
            else:
                
                status = HC.CONTENT_STATUS_CURRENT
                
                note = ''
                
            
            pretty_status = HydrusData.status_to_prefix.get( status, '(?) ' )
            
            return ( pretty_status, old, new, note )
            
        
        def _ConvertPairToSortTuple( self, pair ):
            
            ( old, new ) = pair
            
            ( in_pending, in_petitioned, reason ) = self._parent_action_context.GetPairListCtrlInfo( pair )
            
            note = reason
            
            if in_pending or in_petitioned:
                
                if in_pending:
                    
                    status = HC.CONTENT_STATUS_PENDING
                    
                else:
                    
                    status = HC.CONTENT_STATUS_PETITIONED
                    
                
            else:
                
                status = HC.CONTENT_STATUS_CURRENT
                
                note = ''
                
            
            return ( status, old, new, note )
            
        
        def _DeleteSelectedRows( self ):
            
            pairs = self._tag_parents.GetData( only_selected = True )
            
            if len( pairs ) > 0:
                
                self._parent_action_context.EnterPairs( self, pairs )
                
            
        
        def _DeserialiseImportString( self, import_string ):
            
            tags = HydrusText.DeserialiseNewlinedTexts( import_string )
            
            if len( tags ) % 2 == 1:
                
                ClientGUIDialogsMessage.ShowInformation( self, 'Uneven number of tags in clipboard!' )
                
            
            pairs = []
            
            for i in range( len( tags ) // 2 ):
                
                try:
                    
                    pair = (
                        HydrusTags.CleanTag( tags[ 2 * i ] ),
                        HydrusTags.CleanTag( tags[ ( 2 * i ) + 1 ] )
                    )
                    
                except:
                    
                    continue
                    
                
                pairs.append( pair )
                
            
            pairs = HydrusData.DedupeList( pairs )
            
            return pairs
            
        
        def _ExportToClipboard( self ):
            
            export_string = self._GetExportString()
            
            CG.client_controller.pub( 'clipboard', 'text', export_string )
            
        
        def _ExportToTXT( self ):
            
            export_string = self._GetExportString()
            
            with QP.FileDialog( self, 'Set the export path.', default_filename = 'parents.txt', acceptMode = QW.QFileDialog.AcceptMode.AcceptSave, fileMode = QW.QFileDialog.FileMode.AnyFile ) as dlg:
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    path = dlg.GetPath()
                    
                    with open( path, 'w', encoding = 'utf-8' ) as f:
                        
                        f.write( export_string )
                        
                    
                
            
        
        def _GetExportString( self ):
            
            tags = []
            
            for ( a, b ) in self._tag_parents.GetData( only_selected = True ):
                
                tags.append( a )
                tags.append( b )
                
            
            export_string = '\n'.join( tags )
            
            return export_string
            
        
        def _ImportFromClipboard( self, only_add = False ):
            
            try:
                
                raw_text = CG.client_controller.GetClipboardText()
                
            except HydrusExceptions.DataMissing as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', str(e) )
                
                return
                
            
            try:
                
                pairs = self._DeserialiseImportString( raw_text )
                
                for ( a, b ) in pairs:
                    
                    self._current_pertinent_tags.add( a )
                    self._current_pertinent_tags.add( b )
                    
                
                self._parent_action_context.EnterPairs( self, pairs, only_add = only_add )
                
            except Exception as e:
                
                ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'Lines of child-parent line-pairs', e )
                
            
        
        def _ImportFromTXT( self, only_add = False ):
            
            with QP.FileDialog( self, 'Select the file to import.', acceptMode = QW.QFileDialog.AcceptMode.AcceptOpen ) as dlg:
                
                if dlg.exec() != QW.QDialog.DialogCode.Accepted:
                    
                    return
                    
                else:
                    
                    path = dlg.GetPath()
                    
                
            
            with open( path, 'r', encoding = 'utf-8' ) as f:
                
                import_string = f.read()
                
            
            pairs = self._DeserialiseImportString( import_string )
            
            for ( a, b ) in pairs:
                
                self._current_pertinent_tags.add( a )
                self._current_pertinent_tags.add( b )
                
            
            self._parent_action_context.EnterPairs( self, pairs, only_add = only_add )
            
        
        def _InitialiseListCtrlAsyncUpdater( self ) -> ClientGUIAsync.AsyncQtUpdater:
            
            def loading_callable():
                
                self._count_st.setText( 'loading' + HC.UNICODE_ELLIPSIS )
                
            
            def pre_work_callable():
                
                children = self._children.GetTags()
                parents = self._parents.GetTags()
                
                self._current_pertinent_tags.update( children )
                self._current_pertinent_tags.update( parents )
                
                show_all = self._show_all.isChecked()
                
                self._show_pending_and_petitioned.setEnabled( not show_all )
                self._pursue_whole_chain.setEnabled( not show_all )
                
                show_pending_and_petitioned = self._show_pending_and_petitioned.isEnabled() and self._show_pending_and_petitioned.isChecked()
                pursue_whole_chain = self._pursue_whole_chain.isEnabled() and self._pursue_whole_chain.isChecked()
                
                return ( set( self._current_pertinent_tags ), show_all, show_pending_and_petitioned, pursue_whole_chain, self._parent_action_context )
                
            
            def work_callable( args ):
                
                ( pertinent_tags, show_all, show_pending_and_petitioned, pursue_whole_chain, parent_action_context ) = args
                
                pertinent_pairs = parent_action_context.GetPertinentPairsForTags( pertinent_tags, show_all, show_pending_and_petitioned, pursue_whole_chain )
                
                return pertinent_pairs
                
            
            def publish_callable( result ):
                
                pairs = result
                
                num_active_pertinent_tags = len( self._children.GetTags() ) + len( self._parents.GetTags() )
                
                self._wipe_workspace.setEnabled( len( self._current_pertinent_tags ) > num_active_pertinent_tags )
                
                message = 'This dialog will remember the tags you enter and leave all the related pairs in view. Once you are done editing a group, hit this and it will clear the old pairs away.'
                
                if len( self._current_pertinent_tags ) > 0:
                    
                    message += f' Current workspace:{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( self._current_pertinent_tags, no_trailing_whitespace = True )}'
                    
                
                self._wipe_workspace.setToolTip( ClientGUIFunctions.WrapToolTip( message ) )
                
                self._count_st.setText( f'{HydrusNumbers.ToHumanInt(len(pairs))} pairs.' )
                
                self._tag_parents.SetData( pairs )
                
                self._listctrl_panel.UpdateButtons()
                
            
            return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
            
        
        def _WipeWorkspace( self ):
            
            self._current_pertinent_tags = set()
            
            self._listctrl_async_updater.update()
            
        
        def EnterChildren( self, tags ):
            
            if len( tags ) > 0:
                
                self._parents.RemoveTags( tags )
                
                self._children.EnterTags( tags )
                
            
            self._listctrl_async_updater.update()
            
        
        def EnterChildrenOnlyAdd( self, tags ):
            
            current_children = self._children.GetTags()
            
            tags = { tag for tag in tags if tag not in current_children }
            
            if len( tags ) > 0:
                
                self.EnterChildren( tags )
                
            
        
        def EnterParents( self, tags ):
            
            if len( tags ) > 0:
                
                self._children.RemoveTags( tags )
                
                self._parents.EnterTags( tags )
                
            
            self._listctrl_async_updater.update()
            
        
        def EnterParentsOnlyAdd( self, tags ):
            
            current_parents = self._parents.GetTags()
            
            tags = { tag for tag in tags if tag not in current_parents }
            
            if len( tags ) > 0:
                
                self.EnterParents( tags )
                
            
        
        def GetContentUpdates( self ):
            
            content_updates = self._parent_action_context.GetContentUpdates()
            
            return ( self._service_key, content_updates )
            
        
        def GetServiceKey( self ):
            
            return self._service_key
            
        
        def HasUncommittedPair( self ):
            
            return len( self._children.GetTags() ) > 0 and len( self._parents.GetTags() ) > 0
            
        
        def SetTagBoxFocus( self ):
            
            if len( self._children.GetTags() ) == 0:
                
                self._children_input.setFocus( QC.Qt.FocusReason.OtherFocusReason )
                
            else:
                
                self._parents_input.setFocus( QC.Qt.FocusReason.OtherFocusReason )
                
            
        
        def _STARTInitialisation( self, tags, service_key ):
            
            def work_callable():
                
                ( master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys ) = CG.client_controller.Read( 'tag_display_application' )
                
                service_keys_we_care_about = { s_k for ( s_k, s_ks ) in master_service_keys_to_parent_applicable_service_keys.items() if service_key in s_ks }
                
                service_keys_to_work_to_do = {}
                
                for s_k in service_keys_we_care_about:
                    
                    status = CG.client_controller.Read( 'tag_display_maintenance_status', s_k )
                    
                    work_to_do = status[ 'num_parents_to_sync' ] > 0
                    
                    service_keys_to_work_to_do[ s_k ] = work_to_do
                    
                
                return service_keys_to_work_to_do
                
            
            def publish_callable( result ):
                
                service_keys_to_work_to_do = result
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                looking_good = True
                
                if len( service_keys_to_work_to_do ) == 0:
                    
                    looking_good = False
                    
                    status_text = 'No services currently apply these parents. Changes here will have no effect unless parent application is changed later.'
                    
                else:
                    
                    synced_names = sorted( ( CG.client_controller.services_manager.GetName( s_k ) for ( s_k, work_to_do ) in service_keys_to_work_to_do.items() if not work_to_do ) )
                    unsynced_names = sorted( ( CG.client_controller.services_manager.GetName( s_k ) for ( s_k, work_to_do ) in service_keys_to_work_to_do.items() if work_to_do ) )
                    
                    synced_string = ', '.join( ( '"{}"'.format( name ) for name in synced_names ) )
                    unsynced_string = ', '.join( ( '"{}"'.format( name ) for name in unsynced_names ) )
                    
                    if len( unsynced_names ) == 0:
                        
                        service_part = '{} apply these parents and are fully synced.'.format( synced_string )
                        
                    else:
                        
                        looking_good = False
                        
                        if len( synced_names ) > 0:
                            
                            service_part = '{} apply these parents and are fully synced, but {} still have work to do.'.format( synced_string, unsynced_string )
                            
                        else:
                            
                            service_part = '{} apply these parents but still have sync work to do.'.format( unsynced_string )
                            
                        
                    
                    if CG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_active' ):
                        
                        maintenance_part = 'Parents are set to sync all the time in the background.'
                        
                        if looking_good:
                            
                            changes_part = 'Changes from this dialog should be reflected soon after closing the dialog.'
                            
                        else:
                            
                            changes_part = 'It may take some time for changes here to apply everywhere, though.'
                            
                        
                    else:
                        
                        looking_good = False
                        
                        if CG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_idle' ):
                            
                            maintenance_part = 'Parents are set to sync only when you are not using the client.'
                            changes_part = 'It may take some time for changes here to apply.'
                            
                        else:
                            
                            maintenance_part = 'Parents are not set to sync.'
                            changes_part = 'Changes here will not apply unless sync is manually forced to run.'
                            
                        
                    
                    s = ' | '
                    status_text = s.join( ( service_part, maintenance_part, changes_part ) )
                    
                
                if not self._i_am_local_tag_service:
                    
                    account = self._service.GetAccount()
                    
                    if account.IsUnknown():
                        
                        looking_good = False
                        
                        s = 'The account for this service is currently unsynced! It is uncertain if you have permission to upload parents! Please try to refresh the account in _review services_.'
                        
                        status_text = '{}\n\n{}'.format( s, status_text )
                        
                    elif not account.HasPermission( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.PERMISSION_ACTION_PETITION ):
                        
                        looking_good = False
                        
                        s = 'The account for this service does not seem to have permission to upload parents! You can edit them here for now, but the pending menu will not try to upload any changes you make.'
                        
                        status_text = '{}\n\n{}'.format( s, status_text )
                        
                    
                
                self._sync_status_st.setText( status_text )
                
                if looking_good:
                    
                    self._sync_status_st.setObjectName( 'HydrusValid' )
                    
                else:
                    
                    self._sync_status_st.setObjectName( 'HydrusWarning' )
                    
                
                self._sync_status_st.style().polish( self._sync_status_st )
                
                if tags is None:
                    
                    self._listctrl_async_updater.update()
                    
                else:
                    
                    self.EnterChildren( tags )
                    
                
                if self.isVisible():
                    
                    self.SetTagBoxFocus()
                    
                
            
            self._sync_status_st.setText( 'initialising sync data' + HC.UNICODE_ELLIPSIS )
            
            job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
            
            job.start()
            
        
    
class ManageTagSiblings( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, tags = None ):
        
        super().__init__( parent )
        
        if CG.client_controller.new_options.GetBoolean( 'use_listbook_for_tag_service_panels' ):
            
            self._tag_services = ClientGUIListBook.ListBook( self )
            
        else:
            
            self._tag_services = ClientGUICommon.BetterNotebook( self )
            
        
        #
        
        default_tag_service_key = CG.client_controller.new_options.GetKey( 'default_tag_service_tab' )
        
        services = list( CG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) ) )
        
        services.extend( CG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) ) )
        
        for service in services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            page = self._Panel( self._tag_services, service_key, tags )
            
            self._tag_services.addTab( page, name )
            
            if service_key == default_tag_service_key:
                
                # Py 3.11/PyQt6 6.5.0/two tabs/total tab characters > ~12/select second tab during init = first tab disappears bug
                QP.CallAfter( self._tag_services.setCurrentWidget, page )
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._tag_services, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._tag_services.currentChanged.connect( self._SaveDefaultTagServiceKey )
        
    
    def _SaveDefaultTagServiceKey( self ):
        
        if CG.client_controller.new_options.GetBoolean( 'save_default_tag_service_tab_on_change' ):
            
            current_page = typing.cast( ManageTagSiblings._Panel, self._tag_services.currentWidget() )
            
            if current_page is not None:
                
                CG.client_controller.new_options.SetKey( 'default_tag_service_tab', current_page.GetServiceKey() )
                
            
        
    
    def _SetSearchFocus( self ):
        
        current_page = typing.cast( ManageTagSiblings._Panel, self._tag_services.currentWidget() )
        
        if current_page is not None:
            
            current_page.SetTagBoxFocus()
            
        
    
    def CommitChanges( self ):
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        for page in self._tag_services.GetPages():
            
            ( service_key, content_updates ) = page.GetContentUpdates()
            
            content_update_package.AddContentUpdates( service_key, content_updates )
            
        
        if content_update_package.HasContent():
            
            CG.client_controller.Write( 'content_updates', content_update_package )
            
        
    
    def UserIsOKToOK( self ):
        
        current_page = typing.cast( ManageTagSiblings._Panel, self._tag_services.currentWidget() )
        
        if current_page.HasUncommittedPair():
            
            message = 'Are you sure you want to OK? You have an uncommitted pair.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
    
    def EventServiceChanged( self, event ):
        
        current_page = typing.cast( ManageTagSiblings._Panel, self._tag_services.currentWidget() )
        
        if current_page is not None:
            
            CG.client_controller.CallAfterQtSafe( current_page, 'setting page focus', current_page.SetTagBoxFocus )
            
        
    
    class _Panel( QW.QWidget ):
        
        def __init__( self, parent, service_key, tags = None ):
            
            super().__init__( parent )
            
            self._current_pertinent_tags = set()
            
            self._service_key = service_key
            
            self._service = CG.client_controller.services_manager.GetService( self._service_key )
            
            self._i_am_local_tag_service = self._service.GetServiceType() == HC.LOCAL_TAG
            
            self._sibling_action_context = ClientGUITagActions.SiblingActionContext( self._service_key )
            
            self._current_new = None
            
            self._show_all = QW.QCheckBox( self )
            self._show_pending_and_petitioned = QW.QCheckBox( self )
            
            # leave up here since other things have updates based on them
            self._old_siblings = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, self._service_key, tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, height_num_chars = 4 )
            self._new_sibling = ClientGUICommon.BetterStaticText( self )
            self._new_sibling.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
            
            self._listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
            
            model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_TAG_SIBLINGS.ID, self._ConvertPairToDisplayTuple, self._ConvertPairToSortTuple )
            
            self._tag_siblings = ClientGUIListCtrl.BetterListCtrlTreeView( self._listctrl_panel, 14, model, delete_key_callback = self._DeleteSelectedRows, activation_callback = self._DeleteSelectedRows )
            
            self._listctrl_panel.SetListCtrl( self._tag_siblings )
            
            self._listctrl_panel.AddButton( 'add', self._AddButton, enabled_check_func = self._CanAddFromCurrentInput )
            self._listctrl_panel.AddButton( 'delete', self._DeleteSelectedRows, enabled_only_on_selection = True )
            
            self._tag_siblings.Sort()
            
            menu_items = []
            
            menu_items.append( ( 'normal', 'from clipboard', 'Load siblings from text in your clipboard.', HydrusData.Call( self._ImportFromClipboard, False ) ) )
            menu_items.append( ( 'normal', 'from clipboard (only add pairs--no deletions)', 'Load siblings from text in your clipboard.', HydrusData.Call( self._ImportFromClipboard, True ) ) )
            menu_items.append( ( 'normal', 'from .txt file', 'Load siblings from a .txt file.', HydrusData.Call( self._ImportFromTXT, False ) ) )
            menu_items.append( ( 'normal', 'from .txt file (only add pairs--no deletions)', 'Load siblings from a .txt file.', HydrusData.Call( self._ImportFromTXT, True ) ) )
            
            self._listctrl_panel.AddMenuButton( 'import', menu_items )
            
            menu_items = []
            
            menu_items.append( ( 'normal', 'to clipboard', 'Save selected siblings to your clipboard.', self._ExportToClipboard ) )
            menu_items.append( ( 'normal', 'to .txt file', 'Save selected siblings to a .txt file.', self._ExportToTXT ) )
            
            self._listctrl_panel.AddMenuButton( 'export', menu_items, enabled_only_on_selection = True )
            
            ( gumpf, preview_height ) = ClientGUIFunctions.ConvertTextToPixels( self._old_siblings, ( 12, 4 ) )
            
            self._old_siblings.setMinimumHeight( preview_height )
            
            default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
            
            self._old_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterOlds, default_location_context, service_key, show_paste_button = True )
            self._new_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.SetNew, default_location_context, service_key, show_paste_button = True )
            
            self._old_siblings.tagsChanged.connect( self._old_input.SetContextTags )
            
            self._old_input.externalCopyKeyPressEvent.connect( self._old_siblings.keyPressEvent )
            
            #
            
            self._status_st = ClientGUICommon.BetterStaticText( self,'Tags on the left will appear as those on the right.' )
            self._sync_status_st = ClientGUICommon.BetterStaticText( self, '' )
            self._sync_status_st.setWordWrap( True )
            self._count_st = ClientGUICommon.BetterStaticText( self, '' )
            
            self._wipe_workspace = ClientGUICommon.BetterButton( self, 'wipe workspace', self._WipeWorkspace )
            self._wipe_workspace.setEnabled( False )
            
            old_sibling_box = QP.VBoxLayout()
            
            QP.AddToLayout( old_sibling_box, ClientGUICommon.BetterStaticText( self, label = 'set tags to be replaced' ), CC.FLAGS_CENTER )
            QP.AddToLayout( old_sibling_box, self._old_siblings, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            new_sibling_box = QP.VBoxLayout()
            
            QP.AddToLayout( new_sibling_box, ClientGUICommon.BetterStaticText( self, label = 'set new ideal tag' ), CC.FLAGS_CENTER )
            QP.AddToLayout( new_sibling_box, self._new_sibling, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            text_box = QP.HBoxLayout()
            
            QP.AddToLayout( text_box, old_sibling_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            QP.AddToLayout( text_box, new_sibling_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            input_box = QP.HBoxLayout()
            
            QP.AddToLayout( input_box, self._old_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( input_box, self._new_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            workspace_hbox = QP.HBoxLayout()
            
            QP.AddToLayout( workspace_hbox, self._wipe_workspace, CC.FLAGS_SIZER_CENTER )
            QP.AddToLayout( workspace_hbox, self._count_st, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._sync_status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._show_all, self, 'show all pairs' ), CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._show_pending_and_petitioned, self, 'show pending and petitioned groups' ), CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, workspace_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( vbox, text_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, input_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.setLayout( vbox )
            
            #
            
            self._listctrl_async_updater = self._InitialiseListCtrlAsyncUpdater()
            
            self._show_all.clicked.connect( self._listctrl_async_updater.update )
            self._show_pending_and_petitioned.clicked.connect( self._listctrl_async_updater.update )
            
            self._old_siblings.listBoxChanged.connect( self._listctrl_async_updater.update )
            
            self._sibling_action_context.RegisterQtUpdateCall( self, self._listctrl_async_updater.update )
            
            self._old_input.tagsPasted.connect( self.EnterOldsOnlyAdd )
            self._new_input.tagsPasted.connect( self.SetNew )
            
            self._STARTInitialisation( tags, self._service_key )
            
        
        def _AddButton( self ):
            
            if self._current_new is not None and len( self._old_siblings.GetTags() ) > 0:
                
                olds = self._old_siblings.GetTags()
                
                pairs = [ ( old, self._current_new ) for old in olds ]
                
                self._sibling_action_context.EnterPairs( self, pairs )
                
                self._old_siblings.SetTags( set() )
                self.SetNew( set() )
                
            
        
        def _CanAddFromCurrentInput( self ):
            
            if self._current_new is None or len( self._old_siblings.GetTags() ) == 0:
                
                return False
                
            
            return True
            
        
        def _ConvertPairToDisplayTuple( self, pair ):
            
            ( old, new ) = pair
            
            ( in_pending, in_petitioned, reason ) = self._sibling_action_context.GetPairListCtrlInfo( pair )
            
            note = reason
            
            if in_pending or in_petitioned:
                
                if in_pending:
                    
                    status = HC.CONTENT_STATUS_PENDING
                    
                else:
                    
                    status = HC.CONTENT_STATUS_PETITIONED
                    
                
            else:
                
                status = HC.CONTENT_STATUS_CURRENT
                
                note = ''
                
            
            pretty_status = HydrusData.status_to_prefix.get( status, '(?) ' )
            
            existing_olds = self._old_siblings.GetTags()
            
            if old in existing_olds:
                
                if status == HC.CONTENT_STATUS_PENDING:
                    
                    note = 'CONFLICT: Will be rescinded on add.'
                    
                elif status == HC.CONTENT_STATUS_CURRENT:
                    
                    note = 'CONFLICT: Will be petitioned/deleted on add.'
                    
                
            
            return ( pretty_status, old, new, note )
            
        
        def _ConvertPairToSortTuple( self, pair ):
            
            ( old, new ) = pair
            
            ( in_pending, in_petitioned, reason ) = self._sibling_action_context.GetPairListCtrlInfo( pair )
            
            note = reason
            
            if in_pending or in_petitioned:
                
                if in_pending:
                    
                    status = HC.CONTENT_STATUS_PENDING
                    
                else:
                    
                    status = HC.CONTENT_STATUS_PETITIONED
                    
                
            else:
                
                status = HC.CONTENT_STATUS_CURRENT
                
                note = ''
                
            
            existing_olds = self._old_siblings.GetTags()
            
            if old in existing_olds:
                
                if status == HC.CONTENT_STATUS_PENDING:
                    
                    note = 'CONFLICT: Will be rescinded on add.'
                    
                elif status == HC.CONTENT_STATUS_CURRENT:
                    
                    note = 'CONFLICT: Will be petitioned/deleted on add.'
                    
                
            
            return ( status, old, new, note )
            
        
        def _DeleteSelectedRows( self ):
            
            pairs = self._tag_siblings.GetData( only_selected = True )
            
            if len( pairs ) > 0:
                
                self._sibling_action_context.EnterPairs( self, pairs )
                
            
        
        def _DeserialiseImportString( self, import_string ):
            
            tags = HydrusText.DeserialiseNewlinedTexts( import_string )
            
            if len( tags ) % 2 == 1:
                
                ClientGUIDialogsMessage.ShowInformation( self, 'Uneven number of tags in clipboard!' )
                
            
            pairs = []
            
            for i in range( len( tags ) // 2 ):
                
                try:
                    
                    pair = (
                        HydrusTags.CleanTag( tags[ 2 * i ] ),
                        HydrusTags.CleanTag( tags[ ( 2 * i ) + 1 ] )
                    )
                    
                except:
                    
                    continue
                    
                
                pairs.append( pair )
                
            
            pairs = HydrusData.DedupeList( pairs )
            
            return pairs
            
        
        def _ExportToClipboard( self ):
            
            export_string = self._GetExportString()
            
            CG.client_controller.pub( 'clipboard', 'text', export_string )
            
        
        def _ExportToTXT( self ):
            
            export_string = self._GetExportString()
            
            with QP.FileDialog( self, 'Set the export path.', default_filename = 'siblings.txt', acceptMode = QW.QFileDialog.AcceptMode.AcceptSave, fileMode = QW.QFileDialog.FileMode.AnyFile ) as dlg:
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    path = dlg.GetPath()
                    
                    with open( path, 'w', encoding = 'utf-8' ) as f:
                        
                        f.write( export_string )
                        
                    
                
            
        
        def _GetExportString( self ):
            
            tags = []
            
            for ( a, b ) in self._tag_siblings.GetData( only_selected = True ):
                
                tags.append( a )
                tags.append( b )
                
            
            export_string = '\n'.join( tags )
            
            return export_string
            
        
        def _ImportFromClipboard( self, only_add = False ):
            
            try:
                
                raw_text = CG.client_controller.GetClipboardText()
                
            except HydrusExceptions.DataMissing as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', str(e) )
                
                return
                
            
            try:
                
                pairs = self._DeserialiseImportString( raw_text )
                
                for ( a, b ) in pairs:
                    
                    self._current_pertinent_tags.add( a )
                    self._current_pertinent_tags.add( b )
                    
                
                self._sibling_action_context.EnterPairs( self, pairs, only_add = only_add )
                
            except Exception as e:
                
                ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'Lines of lesser-ideal sibling line-pairs', e )
                
            
        
        def _ImportFromTXT( self, only_add = False ):
            
            with QP.FileDialog( self, 'Select the file to import.', acceptMode = QW.QFileDialog.AcceptMode.AcceptOpen ) as dlg:
                
                if dlg.exec() != QW.QDialog.DialogCode.Accepted:
                    
                    return
                    
                else:
                    
                    path = dlg.GetPath()
                    
                
            
            with open( path, 'r', encoding = 'utf-8' ) as f:
                
                import_string = f.read()
                
            
            pairs = self._DeserialiseImportString( import_string )
            
            for ( a, b ) in pairs:
                
                self._current_pertinent_tags.add( a )
                self._current_pertinent_tags.add( b )
                
            
            self._sibling_action_context.EnterPairs( self, pairs, only_add = only_add )
            
        
        def _InitialiseListCtrlAsyncUpdater( self ) -> ClientGUIAsync.AsyncQtUpdater:
            
            def loading_callable():
                
                self._count_st.setText( 'loading' + HC.UNICODE_ELLIPSIS )
                
            
            def pre_work_callable():
                
                olds = self._old_siblings.GetTags()
                
                self._current_pertinent_tags.update( olds )
                
                if self._current_new is not None:
                    
                    self._current_pertinent_tags.add( self._current_new )
                    
                
                show_all = self._show_all.isChecked()
                
                self._show_pending_and_petitioned.setEnabled( not show_all )
                
                show_pending_and_petitioned = self._show_pending_and_petitioned.isEnabled() and self._show_pending_and_petitioned.isChecked()
                
                return ( set( self._current_pertinent_tags ), show_all, show_pending_and_petitioned, self._sibling_action_context )
                
            
            def work_callable( args ):
                
                ( pertinent_tags, show_all, show_pending_and_petitioned, sibling_action_context ) = args
                
                pursue_whole_chain = True # parent hack
                
                pertinent_pairs = sibling_action_context.GetPertinentPairsForTags( pertinent_tags, show_all, show_pending_and_petitioned, pursue_whole_chain )
                
                return pertinent_pairs
                
            
            def publish_callable( result ):
                
                pairs = result
                
                num_active_pertinent_tags = len( self._old_siblings.GetTags() )
                
                if self._current_new is not None:
                    
                    num_active_pertinent_tags += 1
                    
                
                self._wipe_workspace.setEnabled( len( self._current_pertinent_tags ) > num_active_pertinent_tags )
                
                message = 'This dialog will remember the tags you enter and leave all the related pairs in view. Once you are done editing a group, hit this and it will clear the old pairs away.'
                
                if len( self._current_pertinent_tags ) > 0:
                    
                    message += f' Current workspace:{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( self._current_pertinent_tags, no_trailing_whitespace = True )}'
                    
                
                self._wipe_workspace.setToolTip( ClientGUIFunctions.WrapToolTip( message ) )
                
                self._count_st.setText( f'{HydrusNumbers.ToHumanInt(len(pairs))} pairs.' )
                
                self._tag_siblings.SetData( pairs )
                
                self._listctrl_panel.UpdateButtons()
                
            
            return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
            
        
        def _WipeWorkspace( self ):
            
            self._current_pertinent_tags = set()
            
            self._listctrl_async_updater.update()
            
        
        def EnterOlds( self, olds ):
            
            if self._current_new in olds:
                
                self.SetNew( set() )
                
            
            self._old_siblings.EnterTags( olds )
            
            self._listctrl_async_updater.update()
            
        
        def EnterOldsOnlyAdd( self, olds ):
            
            current_olds = self._old_siblings.GetTags()
            
            olds = { old for old in olds if old not in current_olds }
            
            if len( olds ) > 0:
                
                self.EnterOlds( olds )
                
            
        
        def GetContentUpdates( self ):
            
            content_updates = self._sibling_action_context.GetContentUpdates()
            
            return ( self._service_key, content_updates )
            
        
        def GetServiceKey( self ):
            
            return self._service_key
            
        
        def HasUncommittedPair( self ):
            
            return len( self._old_siblings.GetTags() ) > 0 and self._current_new is not None
            
        
        def SetNew( self, new_tags ):
            
            if len( new_tags ) == 0:
                
                self._new_sibling.clear()
                
                self._current_new = None
                
            else:
                
                new = list( new_tags )[0]
                
                self._old_siblings.RemoveTags( { new } )
                
                self._new_sibling.setText( new )
                
                self._current_new = new
                
            
            self._listctrl_async_updater.update()
            
        
        def SetTagBoxFocus( self ):
            
            if len( self._old_siblings.GetTags() ) == 0:
                
                self._old_input.setFocus( QC.Qt.FocusReason.OtherFocusReason )
                
            else:
                
                self._new_input.setFocus( QC.Qt.FocusReason.OtherFocusReason )
                
            
        
        def _STARTInitialisation( self, tags, service_key ):
            
            def work_callable():
                
                ( master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys ) = CG.client_controller.Read( 'tag_display_application' )
                
                service_keys_we_care_about = { s_k for ( s_k, s_ks ) in master_service_keys_to_sibling_applicable_service_keys.items() if service_key in s_ks }
                
                service_keys_to_work_to_do = {}
                
                for s_k in service_keys_we_care_about:
                    
                    status = CG.client_controller.Read( 'tag_display_maintenance_status', s_k )
                    
                    work_to_do = status[ 'num_siblings_to_sync' ] > 0
                    
                    service_keys_to_work_to_do[ s_k ] = work_to_do
                    
                
                return service_keys_to_work_to_do
                
            
            def publish_callable( result ):
                
                service_keys_to_work_to_do = result
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                looking_good = True
                
                if len( service_keys_to_work_to_do ) == 0:
                    
                    looking_good = False
                    
                    status_text = 'No services currently apply these siblings. Changes here will have no effect unless sibling application is changed later.'
                    
                else:
                    
                    synced_names = sorted( ( CG.client_controller.services_manager.GetName( s_k ) for ( s_k, work_to_do ) in service_keys_to_work_to_do.items() if not work_to_do ) )
                    unsynced_names = sorted( ( CG.client_controller.services_manager.GetName( s_k ) for ( s_k, work_to_do ) in service_keys_to_work_to_do.items() if work_to_do ) )
                    
                    synced_string = ', '.join( ( '"{}"'.format( name ) for name in synced_names ) )
                    unsynced_string = ', '.join( ( '"{}"'.format( name ) for name in unsynced_names ) )
                    
                    if len( unsynced_names ) == 0:
                        
                        service_part = '{} apply these siblings and are fully synced.'.format( synced_string )
                        
                    else:
                        
                        looking_good = False
                        
                        if len( synced_names ) > 0:
                            
                            service_part = '{} apply these siblings and are fully synced, but {} still have work to do.'.format( synced_string, unsynced_string )
                            
                        else:
                            
                            service_part = '{} apply these siblings but still have sync work to do.'.format( unsynced_string )
                            
                        
                    
                    if CG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_active' ):
                        
                        maintenance_part = 'Siblings are set to sync all the time in the background.'
                        
                        if looking_good:
                            
                            changes_part = 'Changes from this dialog should be reflected soon after closing the dialog.'
                            
                        else:
                            
                            changes_part = 'It may take some time for changes here to apply everywhere, though.'
                            
                        
                    else:
                        
                        looking_good = False
                        
                        if CG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_idle' ):
                            
                            maintenance_part = 'Siblings are set to sync only when you are not using the client.'
                            changes_part = 'It may take some time for changes here to apply.'
                            
                        else:
                            
                            maintenance_part = 'Siblings are not set to sync.'
                            changes_part = 'Changes here will not apply unless sync is manually forced to run.'
                            
                        
                    
                    s = ' | '
                    status_text = s.join( ( service_part, maintenance_part, changes_part ) )
                    
                
                if not self._i_am_local_tag_service:
                    
                    account = self._service.GetAccount()
                    
                    if account.IsUnknown():
                        
                        looking_good = False
                        
                        s = 'The account for this service is currently unsynced! It is uncertain if you have permission to upload siblings! Please try to refresh the account in _review services_.'
                        
                        status_text = '{}\n\n{}'.format( s, status_text )
                        
                    elif not account.HasPermission( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.PERMISSION_ACTION_PETITION ):
                        
                        looking_good = False
                        
                        s = 'The account for this service does not seem to have permission to upload siblings! You can edit them here for now, but the pending menu will not try to upload any changes you make.'
                        
                        status_text = '{}\n\n{}'.format( s, status_text )
                        
                    
                
                self._sync_status_st.setText( status_text )
                
                if looking_good:
                    
                    self._sync_status_st.setObjectName( 'HydrusValid' )
                    
                else:
                    
                    self._sync_status_st.setObjectName( 'HydrusWarning' )
                    
                
                self._sync_status_st.style().polish( self._sync_status_st )
                
                if tags is None:
                    
                    self._listctrl_async_updater.update()
                    
                else:
                    
                    self.EnterOlds( tags )
                    
                
                if self.isVisible():
                    
                    self.SetTagBoxFocus()
                    
                
            
            self._sync_status_st.setText( 'initialising sync data' + HC.UNICODE_ELLIPSIS )
            
            job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
            
            job.start()
            
        
    

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
                
                QP.CallAfter( self._tag_services.setCurrentWidget, page )
                
            
        
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
            
            self._refresh_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().refresh, self._StartRefresh )
            
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
                
            
        
    
class TagFilterButton( ClientGUICommon.BetterButton ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, message, tag_filter, only_show_blacklist = False, label_prefix = None ):
        
        super().__init__( parent, 'tag filter', self._EditTagFilter )
        
        self._message = message
        self._tag_filter = tag_filter
        self._only_show_blacklist = only_show_blacklist
        self._label_prefix = label_prefix
        
        self._UpdateLabel()
        
    
    def _EditTagFilter( self ):
        
        if self._only_show_blacklist:
            
            title = 'edit blacklist'
            
        else:
            
            title = 'edit tag filter'
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            namespaces = CG.client_controller.network_engine.domain_manager.GetParserNamespaces()
            
            panel = EditTagFilterPanel( dlg, self._tag_filter, only_show_blacklist = self._only_show_blacklist, namespaces = namespaces, message = self._message )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                self._tag_filter = panel.GetValue()
                
                self._UpdateLabel()
                
                self.valueChanged.emit()
                
            
        
    
    def _UpdateLabel( self ):
        
        if self._only_show_blacklist:
            
            tt = self._tag_filter.ToBlacklistString()
            
        else:
            
            tt = self._tag_filter.ToPermittedString()
            
        
        if self._label_prefix is not None:
            
            tt = self._label_prefix + tt
            
        
        button_text = HydrusText.ElideText( tt, 45 )
        
        self.setText( button_text )
        
        self.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
    
    def GetValue( self ):
        
        return self._tag_filter
        
    
    def SetValue( self, tag_filter ):
        
        self._tag_filter = tag_filter
        
        self._UpdateLabel()
        
    
class TagSummaryGenerator( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_SUMMARY_GENERATOR
    SERIALISABLE_NAME = 'Tag Summary Generator'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, background_colour = None, text_colour = None, namespace_info = None, separator = None, example_tags = None, show = True ):
        
        if background_colour is None:
            
            background_colour = QG.QColor( 223, 227, 230, 255 )
            
        
        if text_colour is None:
            
            text_colour = QG.QColor( 1, 17, 26, 255 )
            
        
        if namespace_info is None:
            
            namespace_info = []
            
            namespace_info.append( ( 'creator', '', ', ' ) )
            namespace_info.append( ( 'series', '', ', ' ) )
            namespace_info.append( ( 'title', '', ', ' ) )
            
        
        if separator is None:
            
            separator = ' - '
            
        
        if example_tags is None:
            
            example_tags = []
            
        
        self._background_colour = background_colour
        self._text_colour = text_colour
        self._namespace_info = namespace_info
        self._separator = separator
        self._example_tags = list( example_tags )
        self._show = show
        
        self._UpdateNamespaceLookup()
        
    
    def _GetSerialisableInfo( self ):
        
        bc = self._background_colour
        
        background_colour_rgba = [ bc.red(), bc.green(), bc.blue(), bc.alpha() ]
        
        tc = self._text_colour
        
        text_colour_rgba = [ tc.red(), tc.green(), tc.blue(), tc.alpha() ]
        
        return ( background_colour_rgba, text_colour_rgba, self._namespace_info, self._separator, self._example_tags, self._show )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( background_rgba, text_rgba, self._namespace_info, self._separator, self._example_tags, self._show ) = serialisable_info
        
        ( r, g, b, a ) = background_rgba
        
        self._background_colour = QG.QColor( r, g, b, a )
        
        ( r, g, b, a ) = text_rgba
        
        self._text_colour = QG.QColor( r, g, b, a )
        
        self._namespace_info = [ tuple( row ) for row in self._namespace_info ]
        
        self._UpdateNamespaceLookup()
        
    
    def _UpdateNamespaceLookup( self ):
        
        self._interesting_namespaces = { namespace for ( namespace, prefix, separator ) in self._namespace_info }
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( namespace_info, separator, example_tags ) = old_serialisable_info
            
            background_rgba = ( 223, 227, 230, 255 )
            text_rgba = ( 1, 17, 26, 255 )
            show = True
            
            new_serialisable_info = ( background_rgba, text_rgba, namespace_info, separator, example_tags, show )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GenerateExampleSummary( self ):
        
        if not self._show:
            
            return 'not showing'
            
        else:
            
            return self.GenerateSummary( self._example_tags )
            
        
    
    def GenerateSummary( self, tags, max_length = None ):
        
        if not self._show:
            
            return ''
            
        
        namespaces_to_subtags = collections.defaultdict( list )
        
        for tag in tags:
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag )
            
            if namespace in self._interesting_namespaces:
                
                subtag = ClientTags.RenderTag( subtag, render_for_user = True )
                
                namespaces_to_subtags[ namespace ].append( subtag )
                
            
        
        for ( namespace, unsorted_l ) in list( namespaces_to_subtags.items() ):
            
            sorted_l = HydrusTags.SortNumericTags( unsorted_l )
            
            sorted_l = HydrusTags.CollapseMultipleSortedNumericTagsToMinMax( sorted_l )
            
            namespaces_to_subtags[ namespace ] = sorted_l
            
        
        namespace_texts = []
        
        for ( namespace, prefix, separator ) in self._namespace_info:
            
            subtags = namespaces_to_subtags[ namespace ]
            
            if len( subtags ) > 0:
                
                namespace_text = prefix + separator.join( namespaces_to_subtags[ namespace ] )
                
                namespace_texts.append( namespace_text )
                
            
        
        summary = self._separator.join( namespace_texts )
        
        if max_length is not None:
            
            summary = summary[:max_length]
            
        
        return summary
        
    
    def GetBackgroundColour( self ):
        
        return self._background_colour
        
    
    def GetTextColour( self ):
        
        return self._text_colour
        
    
    def ToTuple( self ):
        
        return ( self._background_colour, self._text_colour, self._namespace_info, self._separator, self._example_tags, self._show )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_SUMMARY_GENERATOR ] = TagSummaryGenerator

class EditTagSummaryGeneratorPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, tag_summary_generator: TagSummaryGenerator ):
        
        super().__init__( parent )
        
        show_panel = ClientGUICommon.StaticBox( self, 'shows' )
        
        self._show = QW.QCheckBox( show_panel )
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._background_colour = ClientGUIColourPicker.AlphaColourControl( edit_panel )
        self._text_colour = ClientGUIColourPicker.AlphaColourControl( edit_panel )
        
        self._namespaces_listbox = ClientGUIListBoxes.QueueListBox( edit_panel, 8, self._ConvertNamespaceToListBoxString, self._AddNamespaceInfo, self._EditNamespaceInfo )
        
        self._separator = QW.QLineEdit( edit_panel )
        
        example_panel = ClientGUICommon.StaticBox( self, 'example' )
        
        self._example_tags = QW.QPlainTextEdit( example_panel )
        
        self._test_result = QW.QLineEdit( example_panel )
        self._test_result.setReadOnly( True )
        
        #
        
        ( background_colour, text_colour, namespace_info, separator, example_tags, show ) = tag_summary_generator.ToTuple()
        
        self._show.setChecked( show )
        
        self._background_colour.SetValue( background_colour )
        self._text_colour.SetValue( text_colour )
        self._namespaces_listbox.AddDatas( namespace_info )
        self._separator.setText( separator )
        self._example_tags.setPlainText( '\n'.join( example_tags ) )
        
        self._UpdateTest()
        
        #
        
        rows = []
        
        rows.append( ( 'currently shows (turn off to hide): ', self._show ) )
        
        gridbox = ClientGUICommon.WrapInGrid( show_panel, rows )
        
        show_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'background colour: ', self._background_colour ) )
        rows.append( ( 'text colour: ', self._text_colour ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, 'The colours only work for the thumbnails right now!' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( self._namespaces_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        edit_panel.Add( ClientGUICommon.WrapInText( self._separator, edit_panel, 'separator' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        example_panel.Add( ClientGUICommon.BetterStaticText( example_panel, 'Enter some newline-separated tags here to see what your current object would generate.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        example_panel.Add( self._example_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        example_panel.Add( self._test_result, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, show_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, example_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._show.clicked.connect( self._UpdateTest )
        self._separator.textChanged.connect( self._UpdateTest )
        self._example_tags.textChanged.connect( self._UpdateTest )
        self._namespaces_listbox.listBoxChanged.connect( self._UpdateTest )
        
    
    def _AddNamespaceInfo( self ):
        
        namespace = ''
        prefix = ''
        separator = ', '
        
        namespace_info = ( namespace, prefix, separator )
        
        return self._EditNamespaceInfo( namespace_info )
        
    
    def _ConvertNamespaceToListBoxString( self, namespace_info ):
        
        ( namespace, prefix, separator ) = namespace_info
        
        if namespace == '':
            
            pretty_namespace = 'unnamespaced'
            
        else:
            
            pretty_namespace = namespace
            
        
        pretty_prefix = prefix
        pretty_separator = separator
        
        return pretty_namespace + ' | prefix: "' + pretty_prefix + '" | separator: "' + pretty_separator + '"'
        
    
    def _EditNamespaceInfo( self, namespace_info ):
        
        ( namespace, prefix, separator ) = namespace_info
        
        message = 'Edit namespace.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message, namespace, allow_blank = True ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                namespace = dlg.GetValue()
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
        message = 'Edit prefix.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message, prefix, allow_blank = True ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                prefix = dlg.GetValue()
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
        message = 'Edit separator.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message, separator, allow_blank = True ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                separator = dlg.GetValue()
                
                namespace_info = ( namespace, prefix, separator )
                
                return namespace_info
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
    
    def _UpdateTest( self ):
        
        tag_summary_generator = self.GetValue()
        
        self._test_result.setText( tag_summary_generator.GenerateExampleSummary() )
        
    
    def GetValue( self ) -> TagSummaryGenerator:
        
        show = self._show.isChecked()
        
        background_colour = self._background_colour.GetValue()
        text_colour = self._text_colour.GetValue()
        namespace_info = self._namespaces_listbox.GetData()
        separator = self._separator.text()
        example_tags = HydrusTags.CleanTags( HydrusText.DeserialiseNewlinedTexts( self._example_tags.toPlainText() ) )
        
        return TagSummaryGenerator( background_colour, text_colour, namespace_info, separator, example_tags, show )
        
    
class TagSummaryGeneratorButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent: QW.QWidget, tag_summary_generator: TagSummaryGenerator ):
        
        label = tag_summary_generator.GenerateExampleSummary()
        
        super().__init__( parent, label, self._Edit )
        
        self._tag_summary_generator = tag_summary_generator
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit tag summary' ) as dlg:
            
            panel = EditTagSummaryGeneratorPanel( dlg, self._tag_summary_generator )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                self._tag_summary_generator = panel.GetValue()
                
                self.setText( self._tag_summary_generator.GenerateExampleSummary() )
                
            
        
    
    def GetValue( self ) -> TagSummaryGenerator:
        
        return self._tag_summary_generator
        
    
