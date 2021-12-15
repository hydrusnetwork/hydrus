import collections
import itertools
import os
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
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusText
from hydrus.core.networking import HydrusNetwork

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientManagers
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIScrolledPanelsReview
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITagSuggestions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.networking import ClientGUIHydrusNetwork
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIControls
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.media import ClientMedia
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
    message += os.linesep * 2
    message += 'If the namespace you want to add has a hyphen, like \'creator-id\', instead type it with a backslash escape, like \'creator\\-id-page\'.'
    
    with ClientGUIDialogs.DialogTextEntry( win, message, allow_blank = False, default = edit_string ) as dlg:
        
        if dlg.exec() == QW.QDialog.Accepted:
            
            edited_string = dlg.GetValue()
            
            edited_escaped_namespaces = re.split( r'(?<!\\)\-', edited_string )
            
            edited_namespaces = [ namespace.replace( escaped_char, correct_char ) for namespace in edited_escaped_namespaces ]
            
            edited_namespaces = [ HydrusTags.CleanTag( namespace ) for namespace in edited_namespaces if HydrusTags.TagOK( namespace ) ]
            
            if len( edited_namespaces ) > 0:
                
                if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                    
                    available_types = [
                        ClientTags.TAG_DISPLAY_ACTUAL,
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
                    
                    tag_display_type = ClientTags.TAG_DISPLAY_ACTUAL
                    
                
                return ( tuple( edited_namespaces ), tag_display_type )
                
            
        
        raise HydrusExceptions.VetoException()
        
    
class EditTagAutocompleteOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, tag_autocomplete_options: ClientTagsHandling.TagAutocompleteOptions ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_tag_autocomplete_options = tag_autocomplete_options
        services_manager = HG.client_controller.services_manager
        
        all_real_tag_service_keys = services_manager.GetServiceKeys( HC.REAL_TAG_SERVICES )
        all_real_file_service_keys = services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, HC.FILE_REPOSITORY ) )
        
        #
        
        self._write_autocomplete_tag_domain = ClientGUICommon.BetterChoice( self )
        self._write_autocomplete_tag_domain.setToolTip( 'A manage tags autocomplete will start with this domain. Typically only useful with this service or "all known tags".' )
        
        self._write_autocomplete_tag_domain.addItem( services_manager.GetName( CC.COMBINED_TAG_SERVICE_KEY ), CC.COMBINED_TAG_SERVICE_KEY )
        
        for service_key in all_real_tag_service_keys:
            
            self._write_autocomplete_tag_domain.addItem( services_manager.GetName( service_key ), service_key )
            
        
        self._override_write_autocomplete_file_domain = QW.QCheckBox( self )
        self._override_write_autocomplete_file_domain.setToolTip( 'If set, a manage tags dialog autocomplete will start with a different file domain than the one that launched the dialog.' )
        
        self._write_autocomplete_file_domain = ClientGUICommon.BetterChoice( self )
        self._write_autocomplete_file_domain.setToolTip( 'A manage tags autocomplete will start with this domain. Normally only useful for "all known files" or "my files".' )
        
        self._write_autocomplete_file_domain.addItem( services_manager.GetName( CC.COMBINED_FILE_SERVICE_KEY ), CC.COMBINED_FILE_SERVICE_KEY )
        
        for service_key in all_real_file_service_keys:
            
            self._write_autocomplete_file_domain.addItem( services_manager.GetName( service_key ), service_key )
            
        
        self._search_namespaces_into_full_tags = QW.QCheckBox( self )
        self._search_namespaces_into_full_tags.setToolTip( 'If on, a search for "ser" will return all "series:" results such as "series:metrod". On large tag services, these searches are extremely slow.' )
        
        self._namespace_bare_fetch_all_allowed = QW.QCheckBox( self )
        self._namespace_bare_fetch_all_allowed.setToolTip( 'If on, a search for "series:" will return all "series:" results. On large tag services, these searches are extremely slow.' )
        
        self._namespace_fetch_all_allowed = QW.QCheckBox( self )
        self._namespace_fetch_all_allowed.setToolTip( 'If on, a search for "series:*" will return all "series:" results. On large tag services, these searches are extremely slow.' )
        
        self._fetch_all_allowed = QW.QCheckBox( self )
        self._fetch_all_allowed.setToolTip( 'If on, a search for "*" will return all tags. On large tag services, these searches are extremely slow.' )
        
        self._fetch_results_automatically = QW.QCheckBox( self )
        self._fetch_results_automatically.setToolTip( 'If on, results will load as you type. If off, you will have to hit a shortcut (default Ctrl+Space) to load results.' )
        
        self._exact_match_character_threshold = ClientGUICommon.NoneableSpinCtrl( self, none_phrase = 'always autocomplete (only appropriate for small tag services)', min = 1, max = 256, unit = 'characters' )
        self._exact_match_character_threshold.setToolTip( 'When the search text has <= this many characters, autocomplete will not occur and you will only get results that exactly match the input. Increasing this value makes autocomplete snappier but reduces the number of results.' )
        
        #
        
        self._write_autocomplete_tag_domain.SetValue( tag_autocomplete_options.GetWriteAutocompleteTagDomain() )
        self._override_write_autocomplete_file_domain.setChecked( tag_autocomplete_options.OverridesWriteAutocompleteFileDomain() )
        self._write_autocomplete_file_domain.SetValue( tag_autocomplete_options.GetWriteAutocompleteFileDomain() )
        self._search_namespaces_into_full_tags.setChecked( tag_autocomplete_options.SearchNamespacesIntoFullTags() )
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
            self._override_write_autocomplete_file_domain.setVisible( False )
            self._write_autocomplete_file_domain.setVisible( False )
            
        else:
            
            rows.append( ( 'Override default autocomplete file domain in _manage tags_: ', self._override_write_autocomplete_file_domain ) )
            rows.append( ( 'Default autocomplete file domain in _manage tags_: ', self._write_autocomplete_file_domain ) )
            rows.append( ( 'Default autocomplete tag domain in _manage tags_: ', self._write_autocomplete_tag_domain ) )
            
        
        rows.append( ( 'Search namespaces with normal input: ', self._search_namespaces_into_full_tags ) )
        rows.append( ( 'Allow "namespace:": ', self._namespace_bare_fetch_all_allowed ) )
        rows.append( ( 'Allow "namespace:*": ', self._namespace_fetch_all_allowed ) )
        rows.append( ( 'Allow "*": ', self._fetch_all_allowed ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        label = 'The settings that permit searching namespaces and expansive "*" queries can be very expensive on a large client and may cause problems!'
        
        st = ClientGUICommon.BetterStaticText( self, label = label )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 1 )
        
        self.widget().setLayout( vbox )
        
        self._UpdateControls()
        
        self._override_write_autocomplete_file_domain.stateChanged.connect( self._UpdateControls )
        self._search_namespaces_into_full_tags.stateChanged.connect( self._UpdateControls )
        self._namespace_bare_fetch_all_allowed.stateChanged.connect( self._UpdateControls )
        
    
    def _UpdateControls( self ):
        
        self._write_autocomplete_file_domain.setEnabled( self._override_write_autocomplete_file_domain.isChecked() )
        
        if self._search_namespaces_into_full_tags.isChecked():
            
            self._namespace_bare_fetch_all_allowed.setEnabled( False )
            self._namespace_fetch_all_allowed.setEnabled( False )
            
        else:
            
            self._namespace_bare_fetch_all_allowed.setEnabled( True )
            
            if self._namespace_bare_fetch_all_allowed.isChecked():
                
                self._namespace_fetch_all_allowed.setEnabled( False )
                
            else:
                
                self._namespace_fetch_all_allowed.setEnabled( True )
                
            
        
        for c in ( self._namespace_bare_fetch_all_allowed, self._namespace_fetch_all_allowed ):
            
            if not c.isEnabled():
                
                c.blockSignals( True )
                
                c.setChecked( True )
                
                c.blockSignals( False )
                
            
        
    
    def GetValue( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( self._original_tag_autocomplete_options.GetServiceKey() )
        
        write_autocomplete_tag_domain = self._write_autocomplete_tag_domain.GetValue()
        override_write_autocomplete_file_domain = self._override_write_autocomplete_file_domain.isChecked()
        write_autocomplete_file_domain = self._write_autocomplete_file_domain.GetValue()
        search_namespaces_into_full_tags = self._search_namespaces_into_full_tags.isChecked()
        namespace_bare_fetch_all_allowed = self._namespace_bare_fetch_all_allowed.isChecked()
        namespace_fetch_all_allowed = self._namespace_fetch_all_allowed.isChecked()
        fetch_all_allowed = self._fetch_all_allowed.isChecked()
        
        tag_autocomplete_options.SetTuple(
            write_autocomplete_tag_domain,
            override_write_autocomplete_file_domain,
            write_autocomplete_file_domain,
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        tag_autocomplete_options.SetFetchResultsAutomatically( self._fetch_results_automatically.isChecked() )
        tag_autocomplete_options.SetExactMatchCharacterThreshold( self._exact_match_character_threshold.GetValue() )
        
        return tag_autocomplete_options
        
    
class EditTagDisplayApplication( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys ):
        
        master_service_keys_to_sibling_applicable_service_keys = collections.defaultdict( list, master_service_keys_to_sibling_applicable_service_keys )
        master_service_keys_to_parent_applicable_service_keys = collections.defaultdict( list, master_service_keys_to_parent_applicable_service_keys )
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._tag_services_notebook = ClientGUICommon.BetterNotebook( self )
        
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._tag_services_notebook, 100 )
        
        self._tag_services_notebook.setMinimumWidth( min_width )
        
        #
        
        services = list( HG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES ) )
        
        select_service_key = services[0].GetServiceKey()
        
        for service in services:
            
            master_service_key = service.GetServiceKey()
            name = service.GetName()
            
            sibling_applicable_service_keys = master_service_keys_to_sibling_applicable_service_keys[ master_service_key ]
            parent_applicable_service_keys = master_service_keys_to_parent_applicable_service_keys[ master_service_key ]
            
            page = self._Panel( self._tag_services_notebook, master_service_key, sibling_applicable_service_keys, parent_applicable_service_keys )
            
            select = master_service_key == select_service_key
            
            self._tag_services_notebook.addTab( page, name )
            
            if select:
                
                self._tag_services_notebook.setCurrentWidget( page )
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        message = 'While a tag service normally applies its own siblings and parents to itself, it does not have to. If you want a different service\'s siblings (e.g. putting the PTR\'s siblings on your "my tags"), or multiple services\', then set it here. You can also apply no siblings or parents at all.'
        message += os.linesep * 2
        message += 'If there are conflicts, the services at the top of the list have precedence. Parents are collapsed by sibling rules before they are applied.'
        
        self._message = ClientGUICommon.BetterStaticText( self, label = message )
        self._message.setWordWrap( True )
        
        self._sync_status = ClientGUICommon.BetterStaticText( self )
        
        self._sync_status.setWordWrap( True )
        
        if HG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_active' ):
            
            self._sync_status.setText( 'Siblings and parents are set to sync all the time. Changes will start applying as soon as you ok this dialog.' )
            
            self._sync_status.setObjectName( 'HydrusValid' )
            
        else:
            
            if HG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_idle' ):
                
                self._sync_status.setText( 'Siblings and parents are only set to sync during idle time. Changes here will only start to apply when you are not using the client.' )
                
            else:
                
                self._sync_status.setText( 'Siblings and parents are not set to sync in the background at any time. If there is sync work to do, you will have to force it to run using the \'review\' window under _tags->siblings and parents sync_.' )
                
            
            self._sync_status.setObjectName( 'HydrusWarning' )
            
        
        self._sync_status.style().polish( self._sync_status )
        
        QP.AddToLayout( vbox, self._message, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._sync_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tag_services_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        master_service_keys_to_sibling_applicable_service_keys = collections.defaultdict( list )
        master_service_keys_to_parent_applicable_service_keys = collections.defaultdict( list )
        
        for page in self._tag_services_notebook.GetPages():
            
            ( master_service_key, sibling_applicable_service_keys, parent_applicable_service_keys ) = page.GetValue()
            
            master_service_keys_to_sibling_applicable_service_keys[ master_service_key ] = sibling_applicable_service_keys
            master_service_keys_to_parent_applicable_service_keys[ master_service_key ] = parent_applicable_service_keys
            
        
        return ( master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys )
        
    
    class _Panel( QW.QWidget ):
        
        def __init__( self, parent: QW.QWidget, master_service_key: bytes, sibling_applicable_service_keys: typing.Sequence[ bytes ], parent_applicable_service_keys: typing.Sequence[ bytes ] ):
            
            QW.QWidget.__init__( self, parent )
            
            self._master_service_key = master_service_key
            
            #
            
            self._sibling_box = ClientGUICommon.StaticBox( self, 'sibling application' )
            
            #
            
            self._sibling_service_keys_listbox = ClientGUIListBoxes.QueueListBox( self._sibling_box, 4, HG.client_controller.services_manager.GetName, add_callable = self._AddSibling )
            
            #
            
            self._sibling_service_keys_listbox.AddDatas( sibling_applicable_service_keys )
            
            #
            
            self._parent_box = ClientGUICommon.StaticBox( self, 'parent application' )
            
            #
            
            self._parent_service_keys_listbox = ClientGUIListBoxes.QueueListBox( self._sibling_box, 4, HG.client_controller.services_manager.GetName, add_callable = self._AddParent )
            
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
            
            allowed_services = HG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
            
            allowed_services = [ service for service in allowed_services if service.GetServiceKey() not in current_service_keys ]
            
            if len( allowed_services ) == 0:
                
                QW.QMessageBox.information( self, 'Information', 'You have all the current tag services applied to this service.' )
                
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
            
        
        def GetValue( self ):
            
            return ( self._master_service_key, self._sibling_service_keys_listbox.GetData(), self._parent_service_keys_listbox.GetData() )
            
        
    
class EditTagDisplayManagerPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, tag_display_manager: ClientTagsHandling.TagDisplayManager ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_tag_display_manager = tag_display_manager
        
        self._tag_services = ClientGUICommon.BetterNotebook( self )
        
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._tag_services, 100 )
        
        self._tag_services.setMinimumWidth( min_width )
        
        #
        
        services = list( HG.client_controller.services_manager.GetServices( ( HC.COMBINED_TAG, HC.LOCAL_TAG, HC.TAG_REPOSITORY ) ) )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            name = service.GetName()
            
            page = self._Panel( self._tag_services, self._original_tag_display_manager, service_key )
            
            select = service_key == CC.COMBINED_TAG_SERVICE_KEY
            
            self._tag_services.addTab( page, name )
            if select: self._tag_services.setCurrentWidget( page )
            
        
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
            
            QW.QWidget.__init__( self, parent )
            
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
            
            self._display_box.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            self._tao_box.Add( self._tag_autocomplete_options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            
            vbox = QP.VBoxLayout()
            
            if self._service_key == CC.COMBINED_TAG_SERVICE_KEY:
                
                message = 'These options apply to all tag services, or to where the tag domain is "all known tags".'
                message += os.linesep * 2
                message += 'This tag domain is the union of all other services, so it can be more computationally expensive. You most often see it on new search pages.'
                
            else:
                
                message = 'This is just one tag service. You most often search a specific tag service in the manage tags dialog.'
                
            
            st = ClientGUICommon.BetterStaticText( self, message )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            QP.AddToLayout( vbox, self._display_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._tao_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 1 )
            
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
    
    def __init__( self, parent, tag_filter, only_show_blacklist = False, namespaces = None, message = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._only_show_blacklist = only_show_blacklist
        self._namespaces = namespaces
        
        self._wildcard_replacements = {}
        
        self._wildcard_replacements[ '*' ] = ''
        self._wildcard_replacements[ '*:' ] = ':'
        self._wildcard_replacements[ '*:*' ] = ':'
        
        #
        
        help_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().help, self._ShowHelp )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        self._import_favourite = ClientGUICommon.BetterButton( self, 'import', self._ImportFavourite )
        self._export_favourite = ClientGUICommon.BetterButton( self, 'export', self._ExportFavourite )
        self._load_favourite = ClientGUICommon.BetterButton( self, 'load', self._LoadFavourite )
        self._save_favourite = ClientGUICommon.BetterButton( self, 'save', self._SaveFavourite )
        self._delete_favourite = ClientGUICommon.BetterButton( self, 'delete', self._DeleteFavourite )
        
        #
        
        self._show_all_panels_button = ClientGUICommon.BetterButton( self, 'show other panels', self._ShowAllPanels )
        self._show_all_panels_button.setToolTip( 'This shows the whitelist and advanced panels, in case you want to craft a clever blacklist with \'except\' rules.' )
        
        show_the_button = self._only_show_blacklist and HG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
        self._show_all_panels_button.setVisible( show_the_button )
        
        #
        
        self._notebook = ClientGUICommon.BetterNotebook( self )
        
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
        
        self._redundant_st = ClientGUICommon.BetterStaticText( self, '', ellipsize_end = True )
        
        self._current_filter_st = ClientGUICommon.BetterStaticText( self, 'currently keeping: ', ellipsize_end = True )
        
        self._test_result_st = ClientGUICommon.BetterStaticText( self, self.TEST_RESULT_DEFAULT )
        self._test_result_st.setAlignment( QC.Qt.AlignVCenter | QC.Qt.AlignRight )
        
        self._test_result_st.setWordWrap( True )
        
        self._test_input = QW.QPlainTextEdit( self )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        
        if message is not None:
            
            st = ClientGUICommon.BetterStaticText( self, message )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._import_favourite, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._export_favourite, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._load_favourite, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._save_favourite, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._delete_favourite, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._show_all_panels_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._redundant_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._current_filter_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        test_text_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( test_text_vbox, self._test_result_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, test_text_vbox, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._test_input, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
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
        
    
    def _AdvancedAddBlacklist( self, tag_slice ):
        
        tag_slice = self._CleanTagSliceInput( tag_slice )
        
        if tag_slice in self._advanced_blacklist.GetTagSlices():
            
            self._advanced_blacklist.RemoveTagSlices( ( tag_slice, ) )
            
        else:
            
            self._advanced_whitelist.RemoveTagSlices( ( tag_slice, ) )
            
            if self._CurrentlyBlocked( tag_slice ):
                
                self._ShowRedundantError( HydrusTags.ConvertTagSliceToString( tag_slice ) + ' is already blocked by a broader rule!' )
                
            
            self._advanced_blacklist.AddTagSlices( ( tag_slice, ) )
            
        
        self._UpdateStatus()
        
    
    def _AdvancedAddBlacklistButton( self ):
        
        tag_slice = self._advanced_blacklist_input.GetValue()
        
        self._AdvancedAddBlacklist( tag_slice )
        
    
    def _AdvancedAddBlacklistMultiple( self, tag_slices ):
        
        for tag_slice in tag_slices:
            
            self._AdvancedAddBlacklist( tag_slice )
            
        
    
    def _AdvancedAddWhitelist( self, tag_slice ):
        
        tag_slice = self._CleanTagSliceInput( tag_slice )
        
        if tag_slice in self._advanced_whitelist.GetTagSlices():
            
            self._advanced_whitelist.RemoveTagSlices( ( tag_slice, ) )
            
        else:
            
            self._advanced_blacklist.RemoveTagSlices( ( tag_slice, ) )
            
            # if it is still blocked after that, it needs whitelisting explicitly
            
            if not self._CurrentlyBlocked( tag_slice ) and tag_slice not in ( '', ':' ):
                
                self._ShowRedundantError( HydrusTags.ConvertTagSliceToString( tag_slice ) + ' is already permitted by a broader rule!' )
                
            
            self._advanced_whitelist.AddTagSlices( ( tag_slice, ) )
            
        
        self._UpdateStatus()
        
    
    def _AdvancedAddWhitelistButton( self ):
        
        tag_slice = self._advanced_whitelist_input.GetValue()
        
        self._AdvancedAddWhitelist( tag_slice )
        
    
    def _AdvancedAddWhitelistMultiple( self, tag_slices ):
        
        for tag_slice in tag_slices:
            
            self._AdvancedAddWhitelist( tag_slice )
            
        
    
    def _AdvancedBlacklistEverything( self ):
        
        self._advanced_blacklist.SetTagSlices( [] )
        
        self._advanced_whitelist.RemoveTagSlices( ( '', ':' ) )
        
        self._advanced_blacklist.AddTagSlices( ( '', ':' ) )
        
        self._UpdateStatus()
        
    
    def _AdvancedDeleteBlacklist( self ):
        
        selected_tag_slices = self._advanced_blacklist.GetSelectedTagSlices()
        
        if len( selected_tag_slices ) > 0:
            
            result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
            
            if result == QW.QDialog.Accepted:
                
                self._advanced_blacklist.RemoveTagSlices( selected_tag_slices )
                
            
        
        self._UpdateStatus()
        
    
    def _AdvancedDeleteWhitelist( self ):
        
        selected_tag_slices = self._advanced_whitelist.GetSelectedTagSlices()
        
        if len( selected_tag_slices ) > 0:
            
            result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
            
            if result == QW.QDialog.Accepted:
                
                self._advanced_whitelist.RemoveTagSlices( selected_tag_slices )
                
            
        
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
            
        elif tag_slice.count( ':' ) == 1 and tag_slice.endswith( ':' ):
            
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
            
            names_to_tag_filters = HG.client_controller.new_options.GetFavouriteTagFilters()
            
            if name in names_to_tag_filters:
                
                message = 'Delete "{}"?'.format( name )
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.Accepted:
                    
                    return
                    
                
                del names_to_tag_filters[ name ]
                
                HG.client_controller.new_options.SetFavouriteTagFilters( names_to_tag_filters )
                
            
        
        names_to_tag_filters = HG.client_controller.new_options.GetFavouriteTagFilters()
        
        menu = QW.QMenu()
        
        if len( names_to_tag_filters ) == 0:
            
            ClientGUIMenus.AppendMenuLabel( menu, 'no favourites set!' )
            
        else:
            
            for ( name, tag_filter ) in names_to_tag_filters.items():
                
                ClientGUIMenus.AppendMenuItem( menu, name, 'delete {}'.format( name ), do_it, name )
                
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _ExportFavourite( self ):
        
        names_to_tag_filters = HG.client_controller.new_options.GetFavouriteTagFilters()
        
        menu = QW.QMenu()
        
        ClientGUIMenus.AppendMenuItem( menu, 'this tag filter', 'export this tag filter', HG.client_controller.pub, 'clipboard', 'text', self.GetValue().DumpToString() )
        
        if len( names_to_tag_filters ) > 0:
            
            ClientGUIMenus.AppendSeparator( menu )
            
            for ( name, tag_filter ) in names_to_tag_filters.items():
                
                ClientGUIMenus.AppendMenuItem( menu, name, 'export {}'.format( name ), HG.client_controller.pub, 'clipboard', 'text', tag_filter.DumpToString() )
                
            
        
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
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
        except Exception as e:
            
            QW.QMessageBox.critical( self, 'Error', 'I could not understand what was in the clipboard' )
            
            return
            
        
        if not isinstance( obj, HydrusTags.TagFilter ):
            
            QW.QMessageBox.critical( self, 'Error', 'That object was not a Tag Filter! It seemed to be a "{}".'.format(type(obj)) )
            
            return
            
        
        tag_filter = obj
        
        tag_filter.CleanRules()
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter a name for the favourite.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                names_to_tag_filters = HG.client_controller.new_options.GetFavouriteTagFilters()
                
                name = dlg.GetValue()
                
                if name in names_to_tag_filters:
                    
                    message = '"{}" already exists! Overwrite?'.format( name )
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.Accepted:
                        
                        return
                        
                    
                
                names_to_tag_filters[ name ] = tag_filter
                
                HG.client_controller.new_options.SetFavouriteTagFilters( names_to_tag_filters )
                
                self.SetValue( tag_filter )
                
            
        
    
    def _InitAdvancedPanel( self ):
        
        advanced_panel = QW.QWidget( self._notebook )
        
        #
        
        blacklist_panel = ClientGUICommon.StaticBox( advanced_panel, 'exclude these' )
        
        self._advanced_blacklist = ClientGUIListBoxes.ListBoxTagsFilter( blacklist_panel )
        
        self._advanced_blacklist_input = ClientGUIControls.TextAndPasteCtrl( blacklist_panel, self._AdvancedAddBlacklistMultiple, allow_empty_input = True )
        
        add_blacklist_button = ClientGUICommon.BetterButton( blacklist_panel, 'add', self._AdvancedAddBlacklistButton )
        delete_blacklist_button = ClientGUICommon.BetterButton( blacklist_panel, 'delete', self._AdvancedDeleteBlacklist )
        blacklist_everything_button = ClientGUICommon.BetterButton( blacklist_panel, 'block everything', self._AdvancedBlacklistEverything )
        
        #
        
        whitelist_panel = ClientGUICommon.StaticBox( advanced_panel, 'except for these' )
        
        self._advanced_whitelist = ClientGUIListBoxes.ListBoxTagsFilter( whitelist_panel )
        
        self._advanced_whitelist_input = ClientGUIControls.TextAndPasteCtrl( whitelist_panel, self._AdvancedAddWhitelistMultiple, allow_empty_input = True )
        
        self._advanced_add_whitelist_button = ClientGUICommon.BetterButton( whitelist_panel, 'add', self._AdvancedAddWhitelistButton )
        delete_whitelist_button = ClientGUICommon.BetterButton( whitelist_panel, 'delete', self._AdvancedDeleteWhitelist )
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._advanced_blacklist_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox, add_blacklist_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, delete_blacklist_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, blacklist_everything_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        blacklist_panel.Add( self._advanced_blacklist, CC.FLAGS_EXPAND_BOTH_WAYS )
        blacklist_panel.Add( button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._advanced_whitelist_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox, self._advanced_add_whitelist_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, delete_whitelist_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        whitelist_panel.Add( self._advanced_whitelist, CC.FLAGS_EXPAND_BOTH_WAYS )
        whitelist_panel.Add( button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, blacklist_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, whitelist_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        advanced_panel.setLayout( hbox )
        
        return advanced_panel
        
    
    def _InitBlacklistPanel( self ):
        
        blacklist_panel = QW.QWidget( self._notebook )
        
        #
        
        self._simple_blacklist_error_st = ClientGUICommon.BetterStaticText( blacklist_panel )
        
        self._simple_blacklist_global_checkboxes = QP.CheckListBox( blacklist_panel )
        
        self._simple_blacklist_global_checkboxes.Append( 'unnamespaced tags', '' )
        self._simple_blacklist_global_checkboxes.Append( 'namespaced tags', ':' )
        
        self._simple_blacklist_namespace_checkboxes = QP.CheckListBox( blacklist_panel )
        
        for namespace in self._namespaces:
            
            if namespace == '':
                
                continue
                
            
            self._simple_blacklist_namespace_checkboxes.Append( namespace, namespace + ':' )
            
        
        self._simple_blacklist = ClientGUIListBoxes.ListBoxTagsFilter( blacklist_panel )
        
        self._simple_blacklist_input = ClientGUIControls.TextAndPasteCtrl( blacklist_panel, self._SimpleAddBlacklistMultiple, allow_empty_input = True )
        
        #
        
        left_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( left_vbox, self._simple_blacklist_global_checkboxes, CC.FLAGS_EXPAND_PERPENDICULAR )
        left_vbox.addStretch( 1 )
        QP.AddToLayout( left_vbox, self._simple_blacklist_namespace_checkboxes, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        right_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( right_vbox, self._simple_blacklist, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( right_vbox, self._simple_blacklist_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        main_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( main_hbox, left_vbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( main_hbox, right_vbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._simple_blacklist_error_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, main_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        blacklist_panel.setLayout( vbox )
        
        self._simple_blacklist.tagsRemoved.connect( self._SimpleBlacklistRemoved )
        
        return blacklist_panel
        
    
    def _InitWhitelistPanel( self ):
        
        whitelist_panel = QW.QWidget( self._notebook )
        
        #
        
        self._simple_whitelist_error_st = ClientGUICommon.BetterStaticText( whitelist_panel )
        
        self._simple_whitelist_global_checkboxes = QP.CheckListBox( whitelist_panel )
        
        self._simple_whitelist_global_checkboxes.Append( 'unnamespaced tags', '' )
        self._simple_whitelist_global_checkboxes.Append( 'namespaced tags', ':' )
        
        self._simple_whitelist_namespace_checkboxes = QP.CheckListBox( whitelist_panel )
        
        for namespace in self._namespaces:
            
            if namespace == '':
                
                continue
                
            
            self._simple_whitelist_namespace_checkboxes.Append( namespace, namespace + ':' )
            
        
        self._simple_whitelist = ClientGUIListBoxes.ListBoxTagsFilter( whitelist_panel )
        
        self._simple_whitelist_input = ClientGUIControls.TextAndPasteCtrl( whitelist_panel, self._SimpleAddWhitelistMultiple, allow_empty_input = True )
        
        #
        
        left_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( left_vbox, self._simple_whitelist_global_checkboxes, CC.FLAGS_EXPAND_PERPENDICULAR )
        left_vbox.addStretch( 1 )
        QP.AddToLayout( left_vbox, self._simple_whitelist_namespace_checkboxes, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        right_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( right_vbox, self._simple_whitelist, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( right_vbox, self._simple_whitelist_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        main_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( main_hbox, left_vbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( main_hbox, right_vbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._simple_whitelist_error_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, main_hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        whitelist_panel.setLayout( vbox )
        
        self._simple_whitelist.tagsRemoved.connect( self._SimpleWhitelistRemoved )
        
        return whitelist_panel
        
    
    def _LoadFavourite( self ):
        
        names_to_tag_filters = HG.client_controller.new_options.GetFavouriteTagFilters()
        
        menu = QW.QMenu()
        
        if len( names_to_tag_filters ) == 0:
            
            ClientGUIMenus.AppendMenuLabel( menu, 'no favourites set!' )
            
        else:
            
            for ( name, tag_filter ) in names_to_tag_filters.items():
                
                ClientGUIMenus.AppendMenuItem( menu, name, 'load {}'.format( name ), self.SetValue, tag_filter )
                
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _SaveFavourite( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter a name for the favourite.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                names_to_tag_filters = HG.client_controller.new_options.GetFavouriteTagFilters()
                
                name = dlg.GetValue()
                tag_filter = self.GetValue()
                
                if name in names_to_tag_filters:
                    
                    message = '"{}" already exists! Overwrite?'.format( name )
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.Accepted:
                        
                        return
                        
                    
                
                names_to_tag_filters[ name ] = tag_filter
                
                HG.client_controller.new_options.SetFavouriteTagFilters( names_to_tag_filters )
                
            
        
    
    def _ShowAllPanels( self ):
        
        self._whitelist_panel.setVisible( True )
        self._advanced_panel.setVisible( True )
        
        self._notebook.addTab( self._whitelist_panel, 'whitelist' )
        self._notebook.addTab( self._advanced_panel, 'advanced' )
        
        self._show_all_panels_button.setVisible( False )
        
    
    def _ShowHelp( self ):
        
        help = 'Here you can set rules to filter tags for one purpose or another. The default is typically to permit all tags. Check the current filter summary text at the bottom-left of the panel to ensure you have your logic correct.'
        help += os.linesep * 2
        help += 'The different tabs are multiple ways of looking at the filter--sometimes it is more useful to think about a filter as a whitelist (where only the listed contents are kept) or a blacklist (where everything _except_ the listed contents are kept), and there is also an advanced tab that lets you do a more complicated combination of the two.'
        help += os.linesep * 2
        help += 'As well as selecting broader categories of tags with the checkboxes, you can type or paste the individual tags directly--just hit enter to add each one--and double-click an existing entry in a list to remove it.'
        help += os.linesep * 2
        help += 'If you wish to manually type a special tag, use these shorthands:'
        help += os.linesep * 2
        help += '"namespace:" - all instances of that namespace'
        help += os.linesep
        help += '":" - all namespaced tags'
        help += os.linesep
        help += '"" (i.e. an empty string) - all unnamespaced tags'
        
        QW.QMessageBox.information( self, 'Information', help )
        
    
    def _ShowRedundantError( self, text ):
        
        self._redundant_st.setText( text )
        
        HG.client_controller.CallLaterQtSafe( self._redundant_st, 2, 'clear redundant error', self._redundant_st.setText, '' )
        
    
    def _SimpleAddBlacklistMultiple( self, tag_slices ):
        
        for tag_slice in tag_slices:
            
            self._AdvancedAddBlacklist( tag_slice )
            
        
    
    def _SimpleAddWhitelistMultiple( self, tag_slices ):
        
        for tag_slice in tag_slices:
            
            if tag_slice in ( '', ':' ) and tag_slice in self._simple_whitelist.GetTagSlices():
                
                self._AdvancedAddBlacklist( tag_slice )
                
            else:
                
                self._AdvancedAddWhitelist( tag_slice )
                
            
        
    
    def _SimpleBlacklistRemoved( self, tag_slices ):
        
        for tag_slice in tag_slices:
            
            self._AdvancedAddBlacklist( tag_slice )
            
        
    
    def _SimpleBlacklistReset( self ):
        
        pass
        
    
    def _SimpleWhitelistRemoved( self, tag_slices ):
        
        tag_slices = set( tag_slices )
        
        for simple in ( '', ':' ):
            
            if simple in tag_slices:
                
                tag_slices.discard( simple )
                
                self._AdvancedAddBlacklist( simple )
                
            
        
        for tag_slice in tag_slices:
            
            self._AdvancedAddWhitelist( tag_slice )
            
        
    
    def _SimpleWhitelistReset( self ):
        
        pass
        
    
    def _UpdateStatus( self ):
        
        ( whitelist_possible, blacklist_possible ) = self._GetWhiteBlacklistsPossible()
        
        whitelist_tag_slices = self._advanced_whitelist.GetTagSlices()
        blacklist_tag_slices = self._advanced_blacklist.GetTagSlices()
        
        if whitelist_possible:
            
            self._simple_whitelist_error_st.clear()
            
            self._simple_whitelist.setEnabled( True )
            self._simple_whitelist_global_checkboxes.setEnabled( True )
            self._simple_whitelist_input.setEnabled( True )
            
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
                
                check = QP.GetClientData( self._simple_whitelist_global_checkboxes, index ) in whitelist_tag_slices
                
                self._simple_whitelist_global_checkboxes.Check( index, check )
                
            
            for index in range( self._simple_whitelist_namespace_checkboxes.count() ):
                
                check = QP.GetClientData( self._simple_whitelist_namespace_checkboxes, index ) in whitelist_tag_slices
                
                self._simple_whitelist_namespace_checkboxes.Check( index, check )
                
            
        else:
            
            self._simple_whitelist_error_st.setText( 'The filter is currently more complicated than a simple whitelist, so cannot be shown here.' )
            
            self._simple_whitelist.setEnabled( False )
            self._simple_whitelist_global_checkboxes.setEnabled( False )
            self._simple_whitelist_namespace_checkboxes.setEnabled( False )
            self._simple_whitelist_input.setEnabled( False )
            
            self._simple_whitelist.SetTagSlices( '' )
            
            for index in range( self._simple_whitelist_global_checkboxes.count() ):
                
                self._simple_whitelist_global_checkboxes.Check( index, False )
                
            
            for index in range( self._simple_whitelist_namespace_checkboxes.count() ):
                
                self._simple_whitelist_namespace_checkboxes.Check( index, False )
                
            
        
        #
        
        whitelist_tag_slices = self._advanced_whitelist.GetTagSlices()
        blacklist_tag_slices = self._advanced_blacklist.GetTagSlices()
        
        if blacklist_possible:
            
            self._simple_blacklist_error_st.clear()
            
            self._simple_blacklist.setEnabled( True )
            self._simple_blacklist_global_checkboxes.setEnabled( True )
            self._simple_blacklist_input.setEnabled( True )
            
            if self._CurrentlyBlocked( ':' ):
                
                self._simple_blacklist_namespace_checkboxes.setEnabled( False )
                
            else:
                
                self._simple_blacklist_namespace_checkboxes.setEnabled( True )
                
            
            self._simple_blacklist.SetTagSlices( blacklist_tag_slices )
            
            for index in range( self._simple_blacklist_global_checkboxes.count() ):
                
                check = QP.GetClientData( self._simple_blacklist_global_checkboxes, index ) in blacklist_tag_slices
                
                self._simple_blacklist_global_checkboxes.Check( index, check )
                
            
            for index in range( self._simple_blacklist_namespace_checkboxes.count() ):
                
                check = QP.GetClientData( self._simple_blacklist_namespace_checkboxes, index ) in blacklist_tag_slices
                
                self._simple_blacklist_namespace_checkboxes.Check( index, check )
                
            
        else:
            
            self._simple_blacklist_error_st.setText( 'The filter is currently more complicated than a simple blacklist, so cannot be shown here.' )
            
            self._simple_blacklist.setEnabled( False )
            self._simple_blacklist_global_checkboxes.setEnabled( False )
            self._simple_blacklist_namespace_checkboxes.setEnabled( False )
            self._simple_blacklist_input.setEnabled( False )
            
            self._simple_blacklist.SetTagSlices( '' )
            
            for index in range( self._simple_blacklist_global_checkboxes.count() ):
                
                self._simple_blacklist_global_checkboxes.Check( index, False )
                
            
            for index in range( self._simple_blacklist_namespace_checkboxes.count() ):
                
                self._simple_blacklist_namespace_checkboxes.Check( index, False )
                
            
        
        #
        
        whitelist_tag_slices = self._advanced_whitelist.GetTagSlices()
        blacklist_tag_slices = self._advanced_blacklist.GetTagSlices()
        
        if len( blacklist_tag_slices ) == 0:
            
            self._advanced_whitelist_input.setEnabled( False )
            self._advanced_add_whitelist_button.setEnabled( False )
            
        else:
            
            self._advanced_whitelist_input.setEnabled( True )
            self._advanced_add_whitelist_button.setEnabled( True )
            
        
        #
        
        tag_filter = self.GetValue()
        
        if self._only_show_blacklist:
            
            pretty_tag_filter = tag_filter.ToBlacklistString()
            
        else:
            
            pretty_tag_filter = 'currently keeping: {}'.format( tag_filter.ToPermittedString() )
            
        
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
                    
                    tags_to_siblings = HG.client_controller.Read( 'tag_siblings_lookup', CC.COMBINED_TAG_SERVICE_KEY, test_tags )
                    
                    for ( test_tag, siblings ) in tags_to_siblings.items():
                        
                        results.append( False not in ( tag_filter.TagOK( sibling_tag, apply_unnamespaced_rules_to_namespaced_tags = True ) for sibling_tag in siblings ) )
                        
                    
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
                        
                        test_result_text = '{} pass, {} blocked!'.format( HydrusData.ToHumanInt( c[ True ] ), HydrusData.ToHumanInt( c[ False ] ) )
                        
                        self._test_result_st.setObjectName( 'HydrusInvalid' )
                        
                    
                
                self._test_result_st.setText( test_result_text )
                self._test_result_st.style().polish( self._test_result_st )
                
            
            async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
            
            async_job.start()
            
        
    
    def EventSimpleBlacklistNamespaceCheck( self, index ):

        index = index.row()
        
        if index != -1:
            
            tag_slice = QP.GetClientData( self._simple_blacklist_namespace_checkboxes, index )
            
            self._AdvancedAddBlacklist( tag_slice )
            
        
    
    def EventSimpleBlacklistGlobalCheck( self, index ):
        
        index = index.row()
        
        if index != -1:
            
            tag_slice = QP.GetClientData( self._simple_blacklist_global_checkboxes, index )
            
            self._AdvancedAddBlacklist( tag_slice )
            
        
    
    def EventSimpleWhitelistNamespaceCheck( self, index ):

        index = index.row()
        
        if index != -1:
            
            tag_slice = QP.GetClientData( self._simple_whitelist_namespace_checkboxes, index )
            
            self._AdvancedAddWhitelist( tag_slice )
            
        
    
    def EventSimpleWhitelistGlobalCheck( self, index ):

        index = index.row()
        
        if index != -1:
            
            tag_slice = QP.GetClientData( self._simple_whitelist_global_checkboxes, index )
            
            if tag_slice in ( '', ':' ) and tag_slice in self._simple_whitelist.GetTagSlices():
                
                self._AdvancedAddBlacklist( tag_slice )
                
            else:
                
                self._AdvancedAddWhitelist( tag_slice )
                
            
        
    
    def GetValue( self ):
        
        tag_filter = HydrusTags.TagFilter()
        
        for tag_slice in self._advanced_blacklist.GetTagSlices():
            
            tag_filter.SetRule( tag_slice, HC.FILTER_BLACKLIST )
            
        
        for tag_slice in self._advanced_whitelist.GetTagSlices():
            
            tag_filter.SetRule( tag_slice, HC.FILTER_WHITELIST )
            
        
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
        
    
class ManageTagsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, file_service_key, media, immediate_commit = False, canvas_key = None ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._file_service_key = file_service_key
        
        self._immediate_commit = immediate_commit
        self._canvas_key = canvas_key
        
        media = ClientMedia.FlattenMedia( media )
        
        self._current_media = [ m.Duplicate() for m in media ]
        
        self._hashes = set()
        
        for m in self._current_media:
            
            self._hashes.update( m.GetHashes() )
            
        
        self._tag_services = ClientGUICommon.BetterNotebook( self )
        
        #
        
        services = HG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
        
        default_tag_service_key = HG.client_controller.new_options.GetKey( 'default_tag_service_tab' )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            name = service.GetName()
            
            page = self._Panel( self._tag_services, self._file_service_key, service.GetServiceKey(), self._current_media, self._immediate_commit, canvas_key = self._canvas_key )
            page._add_tag_box.selectUp.connect( self.EventSelectUp )
            page._add_tag_box.selectDown.connect( self.EventSelectDown )
            page._add_tag_box.showPrevious.connect( self.EventShowPrevious )
            page._add_tag_box.showNext.connect( self.EventShowNext )
            page.okSignal.connect( self.okSignal )
            
            select = service_key == default_tag_service_key
            
            self._tag_services.addTab( page, name )
            if select: self._tag_services.setCurrentIndex( self._tag_services.count() - 1 )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._tag_services, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        if self._canvas_key is not None:
            
            HG.client_controller.sub( self, 'CanvasHasNewMedia', 'canvas_new_display_media' )
            
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'global', 'media', 'main_gui' ] )
        
        self._tag_services.currentChanged.connect( self.EventServiceChanged )
        
        self._SetSearchFocus()
        
    
    def _GetGroupsOfServiceKeysToContentUpdates( self ):
        
        groups_of_service_keys_to_content_updates = []
        
        for page in self._tag_services.GetPages():
            
            ( service_key, groups_of_content_updates ) = page.GetGroupsOfContentUpdates()
            
            for content_updates in groups_of_content_updates:
                
                if len( content_updates ) > 0:
                    
                    service_keys_to_content_updates = { service_key : content_updates }
                    
                    groups_of_service_keys_to_content_updates.append( service_keys_to_content_updates )
                    
                
            
        
        return groups_of_service_keys_to_content_updates
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_services.currentWidget()
        
        if page is not None:
            
            page.SetTagBoxFocus()
            
        
    
    def CanvasHasNewMedia( self, canvas_key, new_media_singleton ):
        
        if canvas_key == self._canvas_key:
            
            if new_media_singleton is not None:
                
                self._current_media = ( new_media_singleton.Duplicate(), )
                
                for page in self._tag_services.GetPages():
                    
                    page.SetMedia( self._current_media )
                    
                
            
        
    
    def CleanBeforeDestroy( self ):
        
        ClientGUIScrolledPanels.ManagePanel.CleanBeforeDestroy( self )
        
        for page in self._tag_services.GetPages():
            
            page.CleanBeforeDestroy()
            
        
    
    def CommitChanges( self ):
        
        groups_of_service_keys_to_content_updates = self._GetGroupsOfServiceKeysToContentUpdates()
        
        for service_keys_to_content_updates in groups_of_service_keys_to_content_updates:
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
    
    def EventSelectDown( self ):
        
        self._tag_services.SelectRight()
        
        self._SetSearchFocus()
        
    
    def EventSelectUp( self ):
        
        self._tag_services.SelectLeft()
        
        self._SetSearchFocus()
        
    
    def EventShowNext( self ):
        
        if self._canvas_key is not None:
            
            HG.client_controller.pub( 'canvas_show_next', self._canvas_key )
            
        
    
    def EventShowPrevious( self ):
        
        if self._canvas_key is not None:
            
            HG.client_controller.pub( 'canvas_show_previous', self._canvas_key )
            
        
    
    def EventServiceChanged( self, index ):
        
        if not self or not QP.isValid( self ): # actually did get a runtime error here, on some Linux WM dialog shutdown
            
            return
            
        
        if self.sender() != self._tag_services:
            
            return
            
        
        page = self._tag_services.currentWidget()
        
        if page is not None:
            
            HG.client_controller.CallAfterQtSafe( page, 'setting page focus', page.SetTagBoxFocus )
            
        
        if HG.client_controller.new_options.GetBoolean( 'save_default_tag_service_tab_on_change' ):
            
            current_page = self._tag_services.currentWidget()
            
            HG.client_controller.new_options.SetKey( 'default_tag_service_tab', current_page.GetServiceKey() )
            
        
    
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
        
    
    def UserIsOKToCancel( self ):
        
        groups_of_service_keys_to_content_updates = self._GetGroupsOfServiceKeysToContentUpdates()
        
        if len( groups_of_service_keys_to_content_updates ) > 0:
            
            message = 'Are you sure you want to cancel? You have uncommitted changes that will be lost.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.Accepted:
                
                return False
                
            
        
        return True
        
    
    class _Panel( QW.QWidget ):
        
        okSignal = QC.Signal()
        
        def __init__( self, parent, file_service_key, tag_service_key, media, immediate_commit, canvas_key = None ):
            
            QW.QWidget.__init__( self, parent )
            
            self._file_service_key = file_service_key
            self._tag_service_key = tag_service_key
            self._immediate_commit = immediate_commit
            self._canvas_key = canvas_key
            
            self._groups_of_content_updates = []
            
            self._service = HG.client_controller.services_manager.GetService( self._tag_service_key )
            
            self._i_am_local_tag_service = self._service.GetServiceType() == HC.LOCAL_TAG
            
            self._tags_box_sorter = ClientGUIListBoxes.StaticBoxSorterForListBoxTags( self, 'tags', show_siblings_sort = True )
            
            self._tags_box = ClientGUIListBoxes.ListBoxTagsMediaTagsDialog( self._tags_box_sorter, self.EnterTags, self.RemoveTags )
            
            self._tags_box_sorter.SetTagsBox( self._tags_box )
            
            #
            
            self._new_options = HG.client_controller.new_options
            
            if self._i_am_local_tag_service:
                
                text = 'remove all/selected tags'
                
            else:
                
                text = 'petition to remove all/selected tags'
                
            
            self._remove_tags = ClientGUICommon.BetterButton( self._tags_box_sorter, text, self._RemoveTagsButton )
            
            self._copy_button = ClientGUICommon.BetterBitmapButton( self._tags_box_sorter, CC.global_pixmaps().copy, self._Copy )
            self._copy_button.setToolTip( 'Copy selected tags to the clipboard. If none are selected, copies all.' )
            
            self._paste_button = ClientGUICommon.BetterBitmapButton( self._tags_box_sorter, CC.global_pixmaps().paste, self._Paste )
            self._paste_button.setToolTip( 'Paste newline-separated tags from the clipboard into here.' )
            
            self._show_deleted = False
            
            menu_items = []
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'allow_remove_on_manage_tags_input' )
            
            menu_items.append( ( 'check', 'allow remove/petition result on tag input for already existing tag', 'If checked, inputting a tag that already exists will try to remove it.', check_manager ) )
            
            check_manager = ClientGUICommon.CheckboxManagerOptions( 'yes_no_on_remove_on_manage_tags' )
            
            menu_items.append( ( 'check', 'confirm remove/petition tags on explicit delete actions', 'If checked, clicking the remove/petition tags button (or hitting the deleted key on the list) will first confirm the action with a yes/no dialog.', check_manager ) )
            
            check_manager = ClientGUICommon.CheckboxManagerCalls( self._FlipShowDeleted, lambda: self._show_deleted )
            
            menu_items.append( ( 'check', 'show deleted', 'Show deleted tags, if any.', check_manager ) )
            
            menu_items.append( ( 'separator', 0, 0, 0 ) )
            
            menu_items.append( ( 'normal', 'migrate tags for these files', 'Migrate the tags for the files used to launch this manage tags panel.', self._MigrateTags ) )
            
            if not self._i_am_local_tag_service and self._service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_MODERATE ):
                
                menu_items.append( ( 'separator', 0, 0, 0 ) )
                
                menu_items.append( ( 'normal', 'modify users who added the selected tags', 'Modify the users who added the selected tags.', self._ModifyMappers ) )
                
            
            self._cog_button = ClientGUIMenuButton.MenuBitmapButton( self._tags_box_sorter, CC.global_pixmaps().cog, menu_items )
            
            #
            
            self._add_tag_box = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.AddTags, self._file_service_key, self._tag_service_key, null_entry_callable = self.OK )
            
            self._tags_box.SetTagServiceKey( self._tag_service_key )
            
            self._suggested_tags = ClientGUITagSuggestions.SuggestedTagsPanel( self, self._tag_service_key, media, self.AddTags )
            
            self.SetMedia( media )
            
            button_hbox = QP.HBoxLayout()
            
            QP.AddToLayout( button_hbox, self._remove_tags, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( button_hbox, self._copy_button, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( button_hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( button_hbox, self._cog_button, CC.FLAGS_CENTER )
            
            self._tags_box_sorter.Add( button_hbox, CC.FLAGS_ON_RIGHT )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._tags_box_sorter, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( vbox, self._add_tag_box )
            
            #
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._suggested_tags, CC.FLAGS_EXPAND_BOTH_WAYS_POLITE )
            QP.AddToLayout( hbox, vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'global', 'main_gui' ] )
            
            self.setLayout( hbox )
            
            if self._immediate_commit:
                
                HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
                
            
            self._suggested_tags.mouseActivationOccurred.connect( self.SetTagBoxFocus )
            
        
        def _EnterTags( self, tags, only_add = False, only_remove = False, forced_reason = None ):
            
            tags = HydrusTags.CleanTags( tags )
            
            if not self._i_am_local_tag_service and self._service.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_MODERATE ):
                
                forced_reason = 'admin'
                
            
            tags_managers = [ m.GetTagsManager() for m in self._media ]
            
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
                        
                        if num_current + num_pending < num_files:
                            
                            num_pendable = num_files - ( num_current + num_pending )
                            
                            choices[ HC.CONTENT_UPDATE_PEND ].append( ( tag, num_pendable ) )
                            
                        
                    
                    if not only_add:
                        
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
                        
                        text = '{} "{}" for {} files'.format( choice_text_prefix, HydrusText.ElideText( tag, 64 ), HydrusData.ToHumanInt( count ) )
                        
                    else:
                        
                        text = '{} {} tags'.format( choice_text_prefix, HydrusData.ToHumanInt( len( choice_tags ) ) )
                        
                    
                    data = ( choice_action, choice_tags )
                    
                    t_c_lines = [ choice_tooltip_lookup[ choice_action ] ]
                    
                    if len( tag_counts ) > 25:
                        
                        t_c = tag_counts[:25]
                        
                    else:
                        
                        t_c = tag_counts
                        
                    
                    t_c_lines.extend( ( '{} - {} files'.format( tag, HydrusData.ToHumanInt( count ) ) for ( tag, count ) in t_c ) )
                    
                    if len( tag_counts ) > 25:
                        
                        t_c_lines.append( 'and {} others'.format( HydrusData.ToHumanInt( len( tag_counts ) - 25 ) ) )
                        
                    
                    tooltip = os.linesep.join( t_c_lines )
                    
                    bdc_choices.append( ( text, data, tooltip ) )
                    
                
                try:
                    
                    if len( tags ) > 1:
                        
                        message = 'The file{} some of those tags, but not all, so there are different things you can do.'.format( 's have' if len( self._media ) > 1 else ' has' )
                        
                    else:
                        
                        message = 'Of the {} files being managed, some have that tag, but not all of them do, so there are different things you can do.'.format( HydrusData.ToHumanInt( len( self._media ) ) )
                        
                    
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
                        
                        tag_text = 'the ' + HydrusData.ToHumanInt( len( tags ) ) + ' tags'
                        
                    
                    message = 'Enter a reason for ' + tag_text + ' to be removed. A janitor will review your petition.'
                    
                    suggestions = []
                    
                    suggestions.append( 'mangled parse/typo' )
                    suggestions.append( 'not applicable' )
                    suggestions.append( 'splitting filename/title/etc... into individual tags' )
                    
                    with ClientGUIDialogs.DialogTextEntry( self, message, suggestions = suggestions ) as dlg:
                        
                        if dlg.exec() == QW.QDialog.Accepted:
                            
                            reason = dlg.GetValue()
                            
                        else:
                            
                            return
                            
                        
                    
                else:
                    
                    reason = forced_reason
                    
                
            
            # we have an action and tags, so let's effect the content updates
            
            content_updates_group = []
            
            recent_tags = set()
            
            medias_and_tags_managers = [ ( m, m.GetTagsManager() ) for m in self._media ]
            medias_and_sets_of_tags = [ ( m, tm.GetCurrent( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ), tm.GetPending( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ), tm.GetPetitioned( self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE ) ) for ( m, tm ) in medias_and_tags_managers ]
            
            # there is a big CPU hit here as every time you processcontentupdates, the tagsmanagers need to regen caches lmao
            # so if I refetch current tags etc... for every tag loop, we end up getting 16 million tagok calls etc...
            # however, as tags is a set, thus with unique members, let's say for now this is ok, don't need to regen just to consult current
            
            for tag in tags:
                
                if choice_action == HC.CONTENT_UPDATE_ADD: media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag not in mc ]
                elif choice_action == HC.CONTENT_UPDATE_DELETE: media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag in mc ]
                elif choice_action == HC.CONTENT_UPDATE_PEND: media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag not in mc and tag not in mp ]
                elif choice_action == HC.CONTENT_UPDATE_PETITION: media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag in mc and tag not in mpt ]
                elif choice_action == HC.CONTENT_UPDATE_RESCIND_PEND: media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag in mp ]
                elif choice_action == HC.CONTENT_UPDATE_RESCIND_PETITION: media_to_affect = [ m for ( m, mc, mp, mpt ) in medias_and_sets_of_tags if tag in mpt ]
                
                hashes = set( itertools.chain.from_iterable( ( m.GetHashes() for m in media_to_affect ) ) )
                
                if len( hashes ) > 0:
                    
                    content_updates = []
                    
                    if choice_action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_PEND ):
                        
                        recent_tags.add( tag )
                        
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, choice_action, ( tag, hashes ), reason = reason ) )
                    
                    if len( content_updates ) > 0:
                        
                        if not self._immediate_commit:
                            
                            for m in media_to_affect:
                                
                                mt = m.GetTagsManager()
                                
                                for content_update in content_updates:
                                    
                                    mt.ProcessContentUpdate( self._tag_service_key, content_update )
                                    
                                
                            
                        
                        content_updates_group.extend( content_updates )
                        
                    
                
            
            num_recent_tags = HG.client_controller.new_options.GetNoneableInteger( 'num_recent_tags' )
            
            if len( recent_tags ) > 0 and num_recent_tags is not None:
                
                if len( recent_tags ) > num_recent_tags:
                    
                    recent_tags = random.sample( recent_tags, num_recent_tags )
                    
                
                HG.client_controller.Write( 'push_recent_tags', self._tag_service_key, recent_tags )
                
            
            if len( content_updates_group ) > 0:
                
                if self._immediate_commit:
                    
                    service_keys_to_content_updates = { self._tag_service_key : content_updates_group }
                    
                    HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                    
                else:
                    
                    self._groups_of_content_updates.append( content_updates_group )
                    
                    self._suggested_tags.MediaUpdated()
                    
                
            
            self._tags_box.SetTagsByMedia( self._media )
            
        
        def _MigrateTags( self ):
            
            hashes = set()
            
            for m in self._media:
                
                hashes.update( m.GetHashes() )
                
            
            def do_it( tag_service_key, hashes ):
                
                tlw = HG.client_controller.GetMainTLW()
                
                frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( tlw, 'migrate tags' )
                
                panel = ClientGUIScrolledPanelsReview.MigrateTagsPanel( frame, self._tag_service_key, hashes )
                
                frame.SetPanel( panel )
                
            
            QP.CallAfter( do_it, self._tag_service_key, hashes )
            
            self.OK()
            
        
        def _Copy( self ):
            
            tags = list( self._tags_box.GetSelectedTags() )
            
            if len( tags ) == 0:
                
                ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientMedia.GetMediasTagCount( self._media, self._tag_service_key, ClientTags.TAG_DISPLAY_STORAGE )
                
                tags = set( current_tags_to_count.keys() ).union( pending_tags_to_count.keys() )
                
            
            if len( tags ) > 0:
                
                tags = HydrusTags.SortNumericTags( tags )
                
                text = os.linesep.join( tags )
                
                HG.client_controller.pub( 'clipboard', 'text', text )
                
            
        
        def _FlipShowDeleted( self ):
            
            self._show_deleted = not self._show_deleted
            
            self._tags_box.SetShow( 'deleted', self._show_deleted )
            
        
        def _ModifyMappers( self ):
            
            contents = []
            
            tags = self._tags_box.GetSelectedTags()
            
            if len( tags ) == 0:
                
                QW.QMessageBox.information( self, 'No tags selected!', 'Please select some tags first!' )
                
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
                
                text = HG.client_controller.GetClipboardText()
                
            except HydrusExceptions.DataMissing as e:
                
                QW.QMessageBox.warning( self, 'Warning', str(e) )
                
                return
                
            
            try:
                
                tags = HydrusText.DeserialiseNewlinedTexts( text )
                
                tags = HydrusTags.CleanTags( tags )
                
                self.AddTags( tags, only_add = True )
                
            except Exception as e:
                
                QW.QMessageBox.warning( self, 'Warning', 'I could not understand what was in the clipboard' )
                
            
        
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
                
            
        
        def GetGroupsOfContentUpdates( self ):
            
            return ( self._tag_service_key, self._groups_of_content_updates )
            
        
        def GetServiceKey( self ):
            
            return self._tag_service_key
            
        
        def HasChanges( self ):
            
            return len( self._groups_of_content_updates ) > 0
            
        
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
            
        
        def ProcessContentUpdates( self, service_keys_to_content_updates ):
            
            for ( service_key, content_updates ) in service_keys_to_content_updates.items():
                
                for content_update in content_updates:
                    
                    for m in self._media:
                        
                        if HydrusData.SetsIntersect( m.GetHashes(), content_update.GetHashes() ):
                            
                            m.GetMediaResult().ProcessContentUpdate( service_key, content_update )
                            
                        
                    
                
            
            self._tags_box.SetTagsByMedia( self._media )
            
            self._suggested_tags.MediaUpdated()
            
        
        def RemoveTags( self, tags ):
            
            if len( tags ) > 0:
                
                if self._new_options.GetBoolean( 'yes_no_on_remove_on_manage_tags' ):
                    
                    if len( tags ) < 10:
                        
                        message = 'Are you sure you want to remove these tags:'
                        message += os.linesep * 2
                        message += os.linesep.join( ( HydrusText.ElideText( tag, 64 ) for tag in tags ) )
                        
                    else:
                        
                        message = 'Are you sure you want to remove these ' + HydrusData.ToHumanInt( len( tags ) ) + ' tags?'
                        
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.Accepted:
                        
                        return
                        
                    
                
                self._EnterTags( tags, only_remove = True )
                
            
        
        def SetMedia( self, media ):
            
            if media is None:
                
                media = set()
                
            
            self._media = media
            
            self._tags_box.SetTagsByMedia( self._media )
            
            self._suggested_tags.SetMedia( media )
            
        
        def SetTagBoxFocus( self ):
            
            self._add_tag_box.setFocus( QC.Qt.OtherFocusReason )
            
        

class ManageTagParents( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, tags = None ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._tag_services = ClientGUICommon.BetterNotebook( self )
        
        #
        
        default_tag_service_key = HG.client_controller.new_options.GetKey( 'default_tag_service_tab' )
        
        services = list( HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) ) )
        
        services.extend( HG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) ) )
        
        for service in services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            page = self._Panel( self._tag_services, service_key, tags )
            
            select = service_key == default_tag_service_key
            
            self._tag_services.addTab( page, name )
            if select: self._tag_services.setCurrentWidget( page )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._tag_services, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._tag_services.currentChanged.connect( self._SaveDefaultTagServiceKey )
        
    
    def _SaveDefaultTagServiceKey( self ):
        
        if HG.client_controller.new_options.GetBoolean( 'save_default_tag_service_tab_on_change' ):
            
            current_page = self._tag_services.currentWidget()
            
            HG.client_controller.new_options.SetKey( 'default_tag_service_tab', current_page.GetServiceKey() )
            
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_services.currentWidget()
        
        if page is not None:
            
            page.SetTagBoxFocus()
            
        
    
    def CommitChanges( self ):
        
        service_keys_to_content_updates = {}
        
        for page in self._tag_services.GetPages():
            
            ( service_key, content_updates ) = page.GetContentUpdates()
            
            if len( content_updates ) > 0:
                
                service_keys_to_content_updates[ service_key ] = content_updates
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
            
        
    
    def UserIsOKToOK( self ):
        
        if self._tag_services.currentWidget().HasUncommittedPair():
            
            message = 'Are you sure you want to OK? You have an uncommitted pair.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.Accepted:
                
                return False
                
            
        
        return True
        
    
    class _Panel( QW.QWidget ):
        
        def __init__( self, parent, service_key, tags = None ):
            
            QW.QWidget.__init__( self, parent )
            
            self._service_key = service_key
            
            self._service = HG.client_controller.services_manager.GetService( self._service_key )
            
            self._i_am_local_tag_service = self._service.GetServiceType() == HC.LOCAL_TAG
            
            self._pairs_to_reasons = {}
            
            self._original_statuses_to_pairs = collections.defaultdict( set )
            self._current_statuses_to_pairs = collections.defaultdict( set )
            
            self._show_all = QW.QCheckBox( self )
            
            self._listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
            
            self._tag_parents = ClientGUIListCtrl.BetterListCtrl( self._listctrl_panel, CGLC.COLUMN_LIST_TAG_PARENTS.ID, 8, self._ConvertPairToListCtrlTuples, delete_key_callback = self._ListCtrlActivated, activation_callback = self._ListCtrlActivated )
            
            self._listctrl_panel.SetListCtrl( self._tag_parents )
            
            self._tag_parents.Sort()
            
            menu_items = []
            
            menu_items.append( ( 'normal', 'from clipboard', 'Load parents from text in your clipboard.', HydrusData.Call( self._ImportFromClipboard, False ) ) )
            menu_items.append( ( 'normal', 'from clipboard (only add pairs--no deletions)', 'Load parents from text in your clipboard.', HydrusData.Call( self._ImportFromClipboard, True ) ) )
            menu_items.append( ( 'normal', 'from .txt file', 'Load parents from a .txt file.', HydrusData.Call( self._ImportFromTXT, False ) ) )
            menu_items.append( ( 'normal', 'from .txt file (only add pairs--no deletions)', 'Load parents from a .txt file.', HydrusData.Call( self._ImportFromTXT, True ) ) )
            
            self._listctrl_panel.AddMenuButton( 'import', menu_items )
            
            menu_items = []
            
            menu_items.append( ( 'normal', 'to clipboard', 'Save selected parents to your clipboard.', self._ExportToClipboard ) )
            menu_items.append( ( 'normal', 'to .txt file', 'Save selected parents to a .txt file.', self._ExportToTXT ) )
            
            self._listctrl_panel.AddMenuButton( 'export', menu_items, enabled_only_on_selection = True )
            
            self._listctrl_panel.setEnabled( False )
            
            self._children = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, self._service_key, ClientTags.TAG_DISPLAY_ACTUAL )
            self._parents = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, self._service_key, ClientTags.TAG_DISPLAY_ACTUAL )
            
            ( gumpf, preview_height ) = ClientGUIFunctions.ConvertTextToPixels( self._children, ( 12, 6 ) )
            
            self._children.setMinimumHeight( preview_height )
            self._parents.setMinimumHeight( preview_height )
            
            self._child_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterChildren, CC.LOCAL_FILE_SERVICE_KEY, service_key, show_paste_button = True )
            self._child_input.setEnabled( False )
            
            self._parent_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterParents, CC.LOCAL_FILE_SERVICE_KEY, service_key, show_paste_button = True )
            self._parent_input.setEnabled( False )
            
            self._add = QW.QPushButton( 'add', self )
            self._add.clicked.connect( self.EventAddButton )
            self._add.setEnabled( False )
            
            #
            
            self._status_st = ClientGUICommon.BetterStaticText( self, 'initialising\u2026' + os.linesep + '.' )
            self._sync_status_st = ClientGUICommon.BetterStaticText( self, '' )
            self._sync_status_st.setWordWrap( True )
            self._count_st = ClientGUICommon.BetterStaticText( self, '' )
            
            #
            
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
            
            QP.AddToLayout( input_box, self._child_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( input_box, self._parent_input, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._sync_status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._count_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText(self._show_all,self,'show all pairs'), CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( vbox, self._add, CC.FLAGS_ON_RIGHT )
            QP.AddToLayout( vbox, tags_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            QP.AddToLayout( vbox, input_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.setLayout( vbox )
            
            #
            
            self._tag_parents.itemSelectionChanged.connect( self._SetButtonStatus )
            
            self._children.listBoxChanged.connect( self._UpdateListCtrlData )
            self._parents.listBoxChanged.connect( self._UpdateListCtrlData )
            self._show_all.clicked.connect( self._UpdateListCtrlData )
            
            HG.client_controller.CallToThread( self.THREADInitialise, tags, self._service_key )
            
        
        def _AddPairs( self, pairs, add_only = False ):
            
            pairs = list( pairs )
            
            pairs.sort( key = lambda c_p: HydrusTags.ConvertTagToSortable( c_p[1] ) )
            
            new_pairs = []
            current_pairs = []
            petitioned_pairs = []
            pending_pairs = []
            
            for pair in pairs:
                
                if pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]:
                    
                    if not add_only:
                        
                        pending_pairs.append( pair )
                        
                    
                elif pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]:
                    
                    petitioned_pairs.append( pair )
                    
                elif pair in self._original_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ]:
                    
                    if not add_only:
                        
                        current_pairs.append( pair )
                        
                    
                elif self._CanAdd( pair ):
                    
                    new_pairs.append( pair )
                    
                
            
            affected_pairs = []
            
            if len( new_pairs ) > 0:
            
                do_it = True
                
                if not self._i_am_local_tag_service:
                    
                    if self._service.HasPermission( HC.CONTENT_TYPE_TAG_PARENTS, HC.PERMISSION_ACTION_MODERATE ):
                        
                        reason = 'admin'
                        
                    else:
                        
                        if len( new_pairs ) > 10:
                            
                            pair_strings = 'The many pairs you entered.'
                            
                        else:
                            
                            pair_strings = os.linesep.join( ( child + '->' + parent for ( child, parent ) in new_pairs ) )
                            
                        
                        message = 'Enter a reason for:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'To be added. A janitor will review your request.'
                        
                        suggestions = []
                        
                        suggestions.append( 'obvious by definition (a sword is a weapon)' )
                        suggestions.append( 'character/series/studio/etc... belonging (character x belongs to series y)' )
                        
                        with ClientGUIDialogs.DialogTextEntry( self, message, suggestions = suggestions ) as dlg:
                            
                            if dlg.exec() == QW.QDialog.Accepted:
                                
                                reason = dlg.GetValue()
                                
                            else:
                                
                                do_it = False
                                
                            
                        
                    
                    if do_it:
                        
                        for pair in new_pairs: self._pairs_to_reasons[ pair ] = reason
                        
                    
                
                if do_it:
                    
                    self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ].update( new_pairs )
                    
                    affected_pairs.extend( new_pairs )
                    
                
            else:
                
                if len( current_pairs ) > 0:
                    
                    do_it = True
                    
                    if not self._i_am_local_tag_service:
                        
                        if len( current_pairs ) > 10:
                            
                            pair_strings = 'The many pairs you entered.'
                            
                        else:
                            
                            pair_strings = os.linesep.join( ( child + '->' + parent for ( child, parent ) in current_pairs ) )
                            
                        
                        if len( current_pairs ) > 1:
                            
                            message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Already exist.'
                            
                        else:
                            
                            message = 'The pair ' + pair_strings + ' already exists.'
                            
                        
                        result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Choose what to do.', yes_label = 'petition to remove', no_label = 'do nothing' )
                        
                        if result == QW.QDialog.Accepted:
                            
                            if self._service.HasPermission( HC.CONTENT_TYPE_TAG_PARENTS, HC.PERMISSION_ACTION_MODERATE ):
                                
                                reason = 'admin'
                                
                            else:
                                
                                message = 'Enter a reason for:'
                                message += os.linesep * 2
                                message += pair_strings
                                message += os.linesep * 2
                                message += 'to be removed. A janitor will review your petition.'
                                
                                suggestions = []
                                
                                suggestions.append( 'obvious typo/mistake' )
                                
                                with ClientGUIDialogs.DialogTextEntry( self, message, suggestions = suggestions ) as dlg:
                                    
                                    if dlg.exec() == QW.QDialog.Accepted:
                                        
                                        reason = dlg.GetValue()
                                        
                                    else:
                                        
                                        do_it = False
                                        
                                    
                                
                            
                            if do_it:
                                
                                for pair in current_pairs: self._pairs_to_reasons[ pair ] = reason
                                
                            
                            
                        else:
                            
                            do_it = False
                            
                        
                    
                    if do_it:
                        
                        self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ].update( current_pairs )
                        
                        affected_pairs.extend( current_pairs )
                        
                    
                
                if len( pending_pairs ) > 0:
                
                    if len( pending_pairs ) > 10:
                        
                        pair_strings = 'The many pairs you entered.'
                        
                    else:
                        
                        pair_strings = os.linesep.join( ( child + '->' + parent for ( child, parent ) in pending_pairs ) )
                        
                    
                    if len( pending_pairs ) > 1:
                        
                        message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Are pending.'
                        
                    else:
                        
                        message = 'The pair ' + pair_strings + ' is pending.'
                        
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Choose what to do.', yes_label = 'rescind the pend', no_label = 'do nothing' )
                    
                    if result == QW.QDialog.Accepted:
                        
                        self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ].difference_update( pending_pairs )
                        
                        affected_pairs.extend( pending_pairs )
                        
                    
                
                if len( petitioned_pairs ) > 0:
                
                    if len( petitioned_pairs ) > 10:
                        
                        pair_strings = 'The many pairs you entered.'
                        
                    else:
                        
                        pair_strings = os.linesep.join( ( child + '->' + parent for ( child, parent ) in petitioned_pairs ) )
                        
                    
                    if len( petitioned_pairs ) > 1:
                        
                        message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Are petitioned.'
                        
                    else:
                        
                        message = 'The pair ' + pair_strings + ' is petitioned.'
                        
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Choose what to do.', yes_label = 'rescind the petition', no_label = 'do nothing' )
                    
                    if result == QW.QDialog.Accepted:
                        
                        self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ].difference_update( petitioned_pairs )
                        
                        affected_pairs.extend( petitioned_pairs )
                        
                    
                
            
            if len( affected_pairs ) > 0:
                
                def in_current( pair ):
                    
                    for status in ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING, HC.CONTENT_STATUS_PETITIONED ):
                        
                        if pair in self._current_statuses_to_pairs[ status ]:
                            
                            return True
                            
                        
                        return False
                        
                    
                
                affected_pairs = [ ( self._tag_parents.HasData( pair ), in_current( pair ), pair ) for pair in affected_pairs ]
                
                to_add = [ pair for ( exists, current, pair ) in affected_pairs if not exists ]
                to_update = [ pair for ( exists, current, pair ) in affected_pairs if exists and current ]
                to_delete = [ pair for ( exists, current, pair ) in affected_pairs if exists and not current ]
                
                self._tag_parents.AddDatas( to_add )
                self._tag_parents.UpdateDatas( to_update )
                self._tag_parents.DeleteDatas( to_delete )
                
                self._tag_parents.Sort()
                
            
        
        def _CanAdd( self, potential_pair ):
            
            ( potential_child, potential_parent ) = potential_pair
            
            if potential_child == potential_parent: return False
            
            current_pairs = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] ).difference( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ] )
            
            current_children = { child for ( child, parent ) in current_pairs }
            
            # test for loops
            
            if potential_parent in current_children:
                
                simple_children_to_parents = ClientManagers.BuildSimpleChildrenToParents( current_pairs )
                
                if ClientManagers.LoopInSimpleChildrenToParents( simple_children_to_parents, potential_child, potential_parent ):
                    
                    QW.QMessageBox.critical( self, 'Error', 'Adding '+potential_child+'->'+potential_parent+' would create a loop!' )
                    
                    return False
                    
                
            
            return True
            
        
        def _ConvertPairToListCtrlTuples( self, pair ):
            
            ( child, parent ) = pair
            
            if pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]:
                
                status = HC.CONTENT_STATUS_PENDING
                
            elif pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]:
                
                status = HC.CONTENT_STATUS_PETITIONED
                
            elif pair in self._original_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ]:
                
                status = HC.CONTENT_STATUS_CURRENT
                
            
            sign = HydrusData.ConvertStatusToPrefix( status )
            
            pretty_status = sign
            
            display_tuple = ( pretty_status, child, parent )
            sort_tuple = ( status, child, parent )
            
            return ( display_tuple, sort_tuple )
            
        
        def _DeserialiseImportString( self, import_string ):
            
            tags = HydrusText.DeserialiseNewlinedTexts( import_string )
            
            if len( tags ) % 2 == 1:
                
                QW.QMessageBox.information( self, 'Information', 'Uneven number of tags in clipboard!' )
                
            
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
                
            
            return pairs
            
        
        def _ExportToClipboard( self ):
            
            export_string = self._GetExportString()
            
            HG.client_controller.pub( 'clipboard', 'text', export_string )
            
        
        def _ExportToTXT( self ):
            
            export_string = self._GetExportString()
            
            with QP.FileDialog( self, 'Set the export path.', default_filename = 'parents.txt', acceptMode = QW.QFileDialog.AcceptSave, fileMode = QW.QFileDialog.AnyFile ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    path = dlg.GetPath()
                    
                    with open( path, 'w', encoding = 'utf-8' ) as f:
                        
                        f.write( export_string )
                        
                    
                
            
        
        def _GetExportString( self ):
            
            tags = []
            
            for ( a, b ) in self._tag_parents.GetData( only_selected = True ):
                
                tags.append( a )
                tags.append( b )
                
            
            export_string = os.linesep.join( tags )
            
            return export_string
            
        
        def _ImportFromClipboard( self, add_only = False ):
            
            try:
                
                import_string = HG.client_controller.GetClipboardText()
                
            except HydrusExceptions.DataMissing as e:
                
                QW.QMessageBox.critical( self, 'Error', str(e) )
                
                return
                
            
            pairs = self._DeserialiseImportString( import_string )
            
            self._AddPairs( pairs, add_only = add_only )
            
            self._UpdateListCtrlData()
            
        
        def _ImportFromTXT( self, add_only = False ):
            
            with QP.FileDialog( self, 'Select the file to import.', acceptMode = QW.QFileDialog.AcceptOpen ) as dlg:
                
                if dlg.exec() != QW.QDialog.Accepted:
                    
                    return
                    
                else:
                    
                    path = dlg.GetPath()
                    
                
            
            with open( path, 'r', encoding = 'utf-8' ) as f:
                
                import_string = f.read()
                
            
            pairs = self._DeserialiseImportString( import_string )
            
            self._AddPairs( pairs, add_only = add_only )
            
            self._UpdateListCtrlData()
            
        
        def _ListCtrlActivated( self ):
            
            parents_to_children = collections.defaultdict( set )
            
            pairs = self._tag_parents.GetData( only_selected = True )
            
            if len( pairs ) > 0:
                
                self._AddPairs( pairs )
                
            
        
        def _SetButtonStatus( self ):
            
            if len( self._children.GetTags() ) == 0 or len( self._parents.GetTags() ) == 0:
                
                self._add.setEnabled( False )
                
            else:
                
                self._add.setEnabled( True )
                
            
        
        def _UpdateListCtrlData( self ):
            
            children = self._children.GetTags()
            parents = self._parents.GetTags()
            
            pertinent_tags = children.union( parents )
            
            self._tag_parents.DeleteDatas( self._tag_parents.GetData() )
            
            all_pairs = set()
            
            show_all = self._show_all.isChecked()
            
            for ( status, pairs ) in self._current_statuses_to_pairs.items():
                
                if status == HC.CONTENT_STATUS_DELETED:
                    
                    continue
                    
                
                if len( pertinent_tags ) == 0:
                    
                    if status == HC.CONTENT_STATUS_CURRENT and not show_all:
                        
                        continue
                        
                    
                    # show all pending/petitioned
                    
                    all_pairs.update( pairs )
                    
                else:
                    
                    # show all appropriate
                    
                    for pair in pairs:
                        
                        ( a, b ) = pair
                        
                        if a in pertinent_tags or b in pertinent_tags or show_all:
                            
                            all_pairs.add( pair )
                            
                        
                    
                
            
            self._tag_parents.AddDatas( all_pairs )
            
            self._tag_parents.Sort()
            
        
        def EnterChildren( self, tags ):
            
            if len( tags ) > 0:
                
                self._parents.RemoveTags( tags )
                
                self._children.EnterTags( tags )
                
                self._UpdateListCtrlData()
                
                self._SetButtonStatus()
                
            
        
        def EnterParents( self, tags ):
            
            if len( tags ) > 0:
                
                self._children.RemoveTags( tags )
                
                self._parents.EnterTags( tags )
                
                self._UpdateListCtrlData()
                
                self._SetButtonStatus()
                
            
        
        def EventAddButton( self ):
            
            children = self._children.GetTags()
            parents = self._parents.GetTags()
            
            pairs = list( itertools.product( children, parents ) )
            
            self._AddPairs( pairs )
            
            self._children.SetTags( [] )
            self._parents.SetTags( [] )
            
            self._UpdateListCtrlData()
            
            self._SetButtonStatus()
            
        
        def GetContentUpdates( self ):
            
            # we make it manually here because of the mass pending tags done (but not undone on a rescind) on a pending pair!
            # we don't want to send a pend and then rescind it, cause that will spam a thousand bad tags and not undo it
            
            content_updates = []
            
            if self._i_am_local_tag_service:
                
                for pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_DELETE, pair ) )
                    
                
                for pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_ADD, pair ) )
                    
                
            else:
                
                current_pending = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]
                original_pending = self._original_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]
                
                current_petitioned = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]
                original_petitioned = self._original_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]
                
                new_pends = current_pending.difference( original_pending )
                rescinded_pends = original_pending.difference( current_pending )
                
                new_petitions = current_petitioned.difference( original_petitioned )
                rescinded_petitions = original_petitioned.difference( current_petitioned )
                
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_RESCIND_PETITION, pair ) for pair in rescinded_petitions ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_RESCIND_PEND, pair ) for pair in rescinded_pends ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PETITION, pair, reason = self._pairs_to_reasons[ pair ] ) for pair in new_petitions ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PEND, pair, reason = self._pairs_to_reasons[ pair ] ) for pair in new_pends ) )
                
            
            return ( self._service_key, content_updates )
            
        
        def GetServiceKey( self ):
            
            return self._service_key
            
        
        def HasUncommittedPair( self ):
            
            return len( self._children.GetTags() ) > 0 and len( self._parents.GetTags() ) > 0
            
        
        def SetTagBoxFocus( self ):
            
            if len( self._children.GetTags() ) == 0: self._child_input.setFocus( QC.Qt.OtherFocusReason )
            else: self._parent_input.setFocus( QC.Qt.OtherFocusReason )
            
        
        def THREADInitialise( self, tags, service_key ):
            
            def qt_code( original_statuses_to_pairs, current_statuses_to_pairs, service_keys_to_work_to_do ):
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                self._original_statuses_to_pairs = original_statuses_to_pairs
                self._current_statuses_to_pairs = current_statuses_to_pairs
                
                simple_status_text = 'Files with a tag on the left will also be given the tag on the right.'
                simple_status_text += os.linesep
                simple_status_text += 'As an experiment, this panel will only display the \'current\' pairs for those tags entered below.'
                
                self._status_st.setText( simple_status_text )
                
                looking_good = True
                
                if len( service_keys_to_work_to_do ) == 0:
                    
                    looking_good = False
                    
                    status_text = 'No services currently apply these parents. Changes here will have no effect unless parent application is changed later.'
                    
                else:
                    
                    synced_names = sorted( ( HG.client_controller.services_manager.GetName( s_k ) for ( s_k, work_to_do ) in service_keys_to_work_to_do.items() if not work_to_do ) )
                    unsynced_names = sorted( ( HG.client_controller.services_manager.GetName( s_k ) for ( s_k, work_to_do ) in service_keys_to_work_to_do.items() if work_to_do ) )
                    
                    synced_string = ', '.join( ( '"{}"'.format( name ) for name in synced_names ) )
                    unsynced_string = ', '.join( ( '"{}"'.format( name ) for name in unsynced_names ) )
                    
                    if len( unsynced_names ) == 0:
                        
                        service_part = '{} apply these parents and are fully synced.'.format( synced_string )
                        
                    else:
                        
                        looking_good = False
                        
                        if len( synced_names ) > 0:
                            
                            service_part = '{} apply these parents and are fully synced, but {} still have work to do.'.format( synced_string, unsynced_string )
                            
                        else:
                            
                            service_part = '{} apply these parents and still have sync work to do.'.format( unsynced_string )
                            
                        
                    
                    if HG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_active' ):
                        
                        maintenance_part = 'Parents are set to sync all the time in the background.'
                        
                        if looking_good:
                            
                            changes_part = 'Changes from this dialog should be reflected soon after closing the dialog.'
                            
                        else:
                            
                            changes_part = 'It may take some time for changes here to apply everywhere, though.'
                            
                        
                    else:
                        
                        looking_good = False
                        
                        if HG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_idle' ):
                            
                            maintenance_part = 'Parents are set to sync only when you are not using the client.'
                            changes_part = 'It may take some time for changes here to apply.'
                            
                        else:
                            
                            maintenance_part = 'Parents are not set to sync.'
                            changes_part = 'Changes here will not apply unless sync is manually forced to run.'
                            
                        
                    
                    s = os.linesep * 2
                    status_text = s.join( ( service_part, maintenance_part, changes_part ) )
                    
                
                if not self._i_am_local_tag_service:
                    
                    account = self._service.GetAccount()
                    
                    if account.IsUnknown():
                        
                        looking_good = False
                        
                        s = 'The account for this service is currently unsynced! It is uncertain if you have permission to upload parents! Please try to refresh the account in _review services_.'
                        
                        status_text = '{}{}{}'.format( s, os.linesep * 2, status_text )
                        
                    elif not account.HasPermission( HC.CONTENT_TYPE_TAG_PARENTS, HC.PERMISSION_ACTION_PETITION ):
                        
                        looking_good = False
                        
                        s = 'The account for this service does not seem to have permission to upload parents! You can edit them here for now, but the pending menu will not try to upload any changes you make.'
                        
                        status_text = '{}{}{}'.format( s, os.linesep * 2, status_text )
                        
                    
                
                self._sync_status_st.setText( status_text )
                
                if looking_good:
                    
                    self._sync_status_st.setObjectName( 'HydrusValid' )
                    
                else:
                    
                    self._sync_status_st.setObjectName( 'HydrusWarning' )
                    
                
                self._sync_status_st.style().polish( self._sync_status_st )
                
                self._count_st.setText( 'Starting with '+HydrusData.ToHumanInt(len(original_statuses_to_pairs[HC.CONTENT_STATUS_CURRENT]))+' pairs.' )
                
                self._listctrl_panel.setEnabled( True )
                self._child_input.setEnabled( True )
                self._parent_input.setEnabled( True )
                
                if tags is None:
                    
                    self._UpdateListCtrlData()
                    
                else:
                    
                    self.EnterChildren( tags )
                    
                
            
            original_statuses_to_pairs = HG.client_controller.Read( 'tag_parents', service_key )
            
            ( master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys ) = HG.client_controller.Read( 'tag_display_application' )
            
            service_keys_we_care_about = { s_k for ( s_k, s_ks ) in master_service_keys_to_parent_applicable_service_keys.items() if service_key in s_ks }
            
            service_keys_to_work_to_do = {}
            
            for s_k in service_keys_we_care_about:
                
                status = HG.client_controller.Read( 'tag_display_maintenance_status', s_k )
                
                work_to_do = status[ 'num_parents_to_sync' ] > 0
                
                service_keys_to_work_to_do[ s_k ] = work_to_do
                
            
            current_statuses_to_pairs = collections.defaultdict( set )
            
            current_statuses_to_pairs.update( { key : set( value ) for ( key, value ) in list(original_statuses_to_pairs.items()) } )
            
            QP.CallAfter( qt_code, original_statuses_to_pairs, current_statuses_to_pairs, service_keys_to_work_to_do )
            
        
    
class ManageTagSiblings( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, tags = None ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._tag_services = ClientGUICommon.BetterNotebook( self )
        
        #
        
        default_tag_service_key = HG.client_controller.new_options.GetKey( 'default_tag_service_tab' )
        
        services = list( HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) ) )
        
        services.extend( HG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) ) )
        
        for service in services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            page = self._Panel( self._tag_services, service_key, tags )
            
            select = service_key == default_tag_service_key
            
            self._tag_services.addTab( page, name )
            if select: self._tag_services.setCurrentIndex( self._tag_services.indexOf( page ) )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._tag_services, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._tag_services.currentChanged.connect( self._SaveDefaultTagServiceKey )
        
    
    def _SaveDefaultTagServiceKey( self ):
        
        if HG.client_controller.new_options.GetBoolean( 'save_default_tag_service_tab_on_change' ):
            
            current_page = self._tag_services.currentWidget()
            
            HG.client_controller.new_options.SetKey( 'default_tag_service_tab', current_page.GetServiceKey() )
            
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_services.currentWidget()
        
        if page is not None:
            
            page.SetTagBoxFocus()
            
        
    
    def CommitChanges( self ):
        
        service_keys_to_content_updates = {}
        
        for page in self._tag_services.GetPages():
            
            ( service_key, content_updates ) = page.GetContentUpdates()
            
            if len( content_updates ) > 0:
                
                service_keys_to_content_updates[ service_key ] = content_updates
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
            
        
    
    def UserIsOKToOK( self ):
        
        if self._tag_services.currentWidget().HasUncommittedPair():
            
            message = 'Are you sure you want to OK? You have an uncommitted pair.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.Accepted:
                
                return False
                
            
        
        return True
        
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_services.currentWidget()
        
        if page is not None:
            
            HG.client_controller.CallAfterQtSafe( page, 'setting page focus', page.SetTagBoxFocus )
            
        
    
    class _Panel( QW.QWidget ):
        
        def __init__( self, parent, service_key, tags = None ):
            
            QW.QWidget.__init__( self, parent )
            
            self._service_key = service_key
            
            self._service = HG.client_controller.services_manager.GetService( self._service_key )
            
            self._i_am_local_tag_service = self._service.GetServiceType() == HC.LOCAL_TAG
            
            self._original_statuses_to_pairs = collections.defaultdict( set )
            self._current_statuses_to_pairs = collections.defaultdict( set )
            
            self._pairs_to_reasons = {}
            
            self._current_new = None
            
            self._show_all = QW.QCheckBox( self )
            
            self._listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
            
            self._tag_siblings = ClientGUIListCtrl.BetterListCtrl( self._listctrl_panel, CGLC.COLUMN_LIST_TAG_SIBLINGS.ID, 8, self._ConvertPairToListCtrlTuples, delete_key_callback = self._ListCtrlActivated, activation_callback = self._ListCtrlActivated )
            
            self._listctrl_panel.SetListCtrl( self._tag_siblings )
            
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
            
            self._listctrl_panel.setEnabled( False )
            
            self._old_siblings = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, self._service_key, ClientTags.TAG_DISPLAY_ACTUAL )
            self._new_sibling = ClientGUICommon.BetterStaticText( self )
            
            ( gumpf, preview_height ) = ClientGUIFunctions.ConvertTextToPixels( self._old_siblings, ( 12, 6 ) )
            
            self._old_siblings.setMinimumHeight( preview_height )
            
            self._old_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterOlds, CC.LOCAL_FILE_SERVICE_KEY, service_key, show_paste_button = True )
            self._old_input.setEnabled( False )
            
            self._new_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.SetNew, CC.LOCAL_FILE_SERVICE_KEY, service_key )
            self._new_input.setEnabled( False )
            
            self._add = QW.QPushButton( 'add', self )
            self._add.clicked.connect( self.EventAddButton )
            self._add.setEnabled( False )
            
            #
            
            self._status_st = ClientGUICommon.BetterStaticText( self, 'initialising\u2026' )
            self._sync_status_st = ClientGUICommon.BetterStaticText( self, '' )
            self._sync_status_st.setWordWrap( True )
            self._count_st = ClientGUICommon.BetterStaticText( self, '' )
            
            old_sibling_box = QP.VBoxLayout()
            
            QP.AddToLayout( old_sibling_box, ClientGUICommon.BetterStaticText( self, label = 'set tags to be replaced' ), CC.FLAGS_CENTER )
            QP.AddToLayout( old_sibling_box, self._old_siblings, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            new_sibling_box = QP.VBoxLayout()
            
            QP.AddToLayout( new_sibling_box, ClientGUICommon.BetterStaticText( self, label = 'set new ideal tag' ), CC.FLAGS_CENTER )
            new_sibling_box.addStretch( 1 )
            QP.AddToLayout( new_sibling_box, self._new_sibling, CC.FLAGS_EXPAND_PERPENDICULAR )
            new_sibling_box.addStretch( 1 )
            
            text_box = QP.HBoxLayout()
            
            QP.AddToLayout( text_box, old_sibling_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            QP.AddToLayout( text_box, new_sibling_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            input_box = QP.HBoxLayout()
            
            QP.AddToLayout( input_box, self._old_input )
            QP.AddToLayout( input_box, self._new_input )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._sync_status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._count_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText(self._show_all,self,'show all pairs'), CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( vbox, self._add, CC.FLAGS_ON_RIGHT )
            QP.AddToLayout( vbox, text_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            QP.AddToLayout( vbox, input_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.setLayout( vbox )
            
            #
            
            self._tag_siblings.itemSelectionChanged.connect( self._SetButtonStatus )
            
            self._show_all.clicked.connect( self._UpdateListCtrlData )
            self._old_siblings.listBoxChanged.connect( self._UpdateListCtrlData )
            
            HG.client_controller.CallToThread( self.THREADInitialise, tags, self._service_key )
            
        
        def _AddPairs( self, pairs, add_only = False, remove_only = False, default_reason = None ):
            
            pairs = list( pairs )
            
            pairs.sort( key = lambda c_p1: HydrusTags.ConvertTagToSortable( c_p1[1] ) )
            
            new_pairs = []
            current_pairs = []
            petitioned_pairs = []
            pending_pairs = []
            
            for pair in pairs:
                
                if pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]:
                    
                    if not add_only:
                        
                        pending_pairs.append( pair )
                        
                    
                elif pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]:
                    
                    if not remove_only:
                        
                        petitioned_pairs.append( pair )
                        
                    
                elif pair in self._original_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ]:
                    
                    if not add_only:
                        
                        current_pairs.append( pair )
                        
                    
                elif not remove_only and self._CanAdd( pair ):
                    
                    new_pairs.append( pair )
                    
                
            
            if len( new_pairs ) > 0:
                
                do_it = True
                
                if not self._i_am_local_tag_service:
                    
                    if default_reason is not None:
                        
                        reason = default_reason
                        
                    elif self._service.HasPermission( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.PERMISSION_ACTION_MODERATE ):
                        
                        reason = 'admin'
                        
                    else:
                        
                        if len( new_pairs ) > 10:
                            
                            pair_strings = 'The many pairs you entered.'
                            
                        else:
                            
                            pair_strings = os.linesep.join( ( old + '->' + new for ( old, new ) in new_pairs ) )
                            
                        
                        suggestions = []
                        
                        suggestions.append( 'merging underscores/typos/phrasing/unnamespaced to a single uncontroversial good tag' )
                        suggestions.append( 'rewording/namespacing based on preference' )
                        
                        message = 'Enter a reason for:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'To be added. A janitor will review your petition.'
                        
                        with ClientGUIDialogs.DialogTextEntry( self, message, suggestions = suggestions ) as dlg:
                            
                            if dlg.exec() == QW.QDialog.Accepted:
                                
                                reason = dlg.GetValue()
                                
                            else:
                                
                                do_it = False
                                
                            
                        
                    
                    if do_it:
                        
                        for pair in new_pairs: self._pairs_to_reasons[ pair ] = reason
                        
                    
                
                if do_it:
                    
                    self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ].update( new_pairs )
                    
                
            else:
                
                if len( current_pairs ) > 0:
                    
                    do_it = True
                    
                    if not self._i_am_local_tag_service:
                        
                        if default_reason is not None:
                            
                            reason = default_reason
                            
                        elif self._service.HasPermission( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.PERMISSION_ACTION_MODERATE ):
                            
                            reason = 'admin'
                            
                        else:
                            
                            if len( current_pairs ) > 10:
                                
                                pair_strings = 'The many pairs you entered.'
                                
                            else:
                                
                                pair_strings = os.linesep.join( ( old + '->' + new for ( old, new ) in current_pairs ) )
                                
                            
                            message = 'Enter a reason for:'
                            message += os.linesep * 2
                            message += pair_strings
                            message += os.linesep * 2
                            message += 'to be removed. You will see the delete as soon as you upload, but a janitor will review your petition to decide if all users should receive it as well.'
                            
                            suggestions = []
                            
                            suggestions.append( 'obvious typo/mistake' )
                            suggestions.append( 'disambiguation' )
                            suggestions.append( 'correcting to repository standard' )
                            
                            with ClientGUIDialogs.DialogTextEntry( self, message, suggestions = suggestions ) as dlg:
                                
                                if dlg.exec() == QW.QDialog.Accepted:
                                    
                                    reason = dlg.GetValue()
                                    
                                else:
                                    
                                    do_it = False
                                    
                                
                            
                        
                        if do_it:
                            
                            for pair in current_pairs:
                                
                                self._pairs_to_reasons[ pair ] = reason
                                
                            
                        
                    
                    if do_it:
                        
                        self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ].update( current_pairs )
                        
                    
                
                if len( pending_pairs ) > 0:
                    
                    if len( pending_pairs ) > 10:
                        
                        pair_strings = 'The many pairs you entered.'
                        
                    else:
                        
                        pair_strings = os.linesep.join( ( old + '->' + new for ( old, new ) in pending_pairs ) )
                        
                    
                    if len( pending_pairs ) > 1:
                        
                        message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Are pending.'
                        
                    else:
                        
                        message = 'The pair ' + pair_strings + ' is pending.'
                        
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Choose what to do.', yes_label = 'rescind the pend', no_label = 'do nothing' )
                    
                    if result == QW.QDialog.Accepted:
                        
                        self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ].difference_update( pending_pairs )
                        
                    
                
                if len( petitioned_pairs ) > 0:
                
                    if len( petitioned_pairs ) > 10:
                        
                        pair_strings = 'The many pairs you entered.'
                        
                    else:
                        
                        pair_strings = ', '.join( ( old + '->' + new for ( old, new ) in petitioned_pairs ) )
                        
                    
                    if len( petitioned_pairs ) > 1:
                        
                        message = 'The pairs:' + os.linesep * 2 + pair_strings + os.linesep * 2 + 'Are petitioned.'
                        
                    else:
                        
                        message = 'The pair ' + pair_strings + ' is petitioned.'
                        
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Choose what to do.', yes_label = 'rescind the petition', no_label = 'do nothing' )
                    
                    if result == QW.QDialog.Accepted:
                        
                        self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ].difference_update( petitioned_pairs )
                        
                    
                
            
        
        def _AutoPetitionConflicts( self, pairs ):
            
            current_pairs = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] ).difference( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ] )
            
            current_olds_to_news = dict( current_pairs )
            
            current_olds = { current_old for ( current_old, current_new ) in current_pairs }
            
            pairs_to_auto_petition = set()
            
            for ( old, new ) in pairs:
                
                if old in current_olds:
                    
                    conflicting_new = current_olds_to_news[ old ]
                    
                    if conflicting_new != new:
                        
                        conflicting_pair = ( old, conflicting_new )
                        
                        pairs_to_auto_petition.add( conflicting_pair )
                        
                    
                
            
            if len( pairs_to_auto_petition ) > 0:
                
                pairs_to_auto_petition = list( pairs_to_auto_petition )
                
                self._AddPairs( pairs_to_auto_petition, remove_only = True, default_reason = 'AUTO-PETITION TO REASSIGN TO: ' + new )
                
            
        
        def _CanAdd( self, potential_pair ):
            
            ( potential_old, potential_new ) = potential_pair
            
            current_pairs = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] ).difference( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ] )
            
            current_olds = { old for ( old, new ) in current_pairs }
            
            # test for ambiguity
            
            if potential_old in current_olds:
                
                QW.QMessageBox.critical( self, 'Error', 'There already is a relationship set for the tag '+potential_old+'.' )
                
                return False
                
            
            # test for loops
            
            if potential_new in current_olds:
                
                seen_tags = set()
                
                d = dict( current_pairs )
                
                next_new = potential_new
                
                while next_new in d:
                    
                    next_new = d[ next_new ]
                    
                    if next_new == potential_old:
                        
                        QW.QMessageBox.critical( self, 'Error', 'Adding '+potential_old+'->'+potential_new+' would create a loop!' )
                        
                        return False
                        
                    
                    if next_new in seen_tags:
                        
                        message = 'The pair you mean to add seems to connect to a sibling loop already in your database! Please undo this loop first. The tags involved in the loop are:'
                        message += os.linesep * 2
                        message += ', '.join( seen_tags )
                        
                        QW.QMessageBox.critical( self, 'Error', message )
                        
                        return False
                        
                    
                    seen_tags.add( next_new )
                    
                
            
            return True
            
        
        def _ConvertPairToListCtrlTuples( self, pair ):
            
            ( old, new ) = pair
            
            if pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]:
                
                status = HC.CONTENT_STATUS_PENDING
                
            elif pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]:
                
                status = HC.CONTENT_STATUS_PETITIONED
                
            elif pair in self._original_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ]:
                
                status = HC.CONTENT_STATUS_CURRENT
                
            
            sign = HydrusData.ConvertStatusToPrefix( status )
            
            pretty_status = sign
            
            existing_olds = self._old_siblings.GetTags()
            
            note = ''
            
            if old in existing_olds:
                
                if status == HC.CONTENT_STATUS_PENDING:
                    
                    note = 'CONFLICT: Will be rescinded on add.'
                    
                elif status == HC.CONTENT_STATUS_CURRENT:
                    
                    note = 'CONFLICT: Will be petitioned/deleted on add.'
                    
                
            
            display_tuple = ( pretty_status, old, new, note )
            sort_tuple = ( status, old, new, note )
            
            return ( display_tuple, sort_tuple )
            
        
        def _DeserialiseImportString( self, import_string ):
            
            tags = HydrusText.DeserialiseNewlinedTexts( import_string )
            
            if len( tags ) % 2 == 1:
                
                QW.QMessageBox.information( self, 'Information', 'Uneven number of tags in clipboard!' )
                
            
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
                
            
            return pairs
            
        
        def _ExportToClipboard( self ):
            
            export_string = self._GetExportString()
            
            HG.client_controller.pub( 'clipboard', 'text', export_string )
            
        
        def _ExportToTXT( self ):
            
            export_string = self._GetExportString()
            
            with QP.FileDialog( self, 'Set the export path.', default_filename = 'siblings.txt', acceptMode = QW.QFileDialog.AcceptSave, fileMode = QW.QFileDialog.AnyFile ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    path = dlg.GetPath()
                    
                    with open( path, 'w', encoding = 'utf-8' ) as f:
                        
                        f.write( export_string )
                        
                    
                
            
        
        def _GetExportString( self ):
            
            tags = []
            
            for ( a, b ) in self._tag_siblings.GetData( only_selected = True ):
                
                tags.append( a )
                tags.append( b )
                
            
            export_string = os.linesep.join( tags )
            
            return export_string
            
        
        def _ImportFromClipboard( self, add_only = False ):
            
            try:
                
                import_string = HG.client_controller.GetClipboardText()
                
            except HydrusExceptions.DataMissing as e:
                
                QW.QMessageBox.critical( self, 'Error', str(e) )
                
                return
                
            
            pairs = self._DeserialiseImportString( import_string )
            
            self._AutoPetitionConflicts( pairs )
            
            self._AddPairs( pairs, add_only = add_only )
            
            self._UpdateListCtrlData()
            
        
        def _ImportFromTXT( self, add_only = False ):
            
            with QP.FileDialog( self, 'Select the file to import.', acceptMode = QW.QFileDialog.AcceptOpen ) as dlg:
                
                if dlg.exec() != QW.QDialog.Accepted:
                    
                    return
                    
                else:
                    
                    path = dlg.GetPath()
                    
                
            
            with open( path, 'r', encoding = 'utf-8' ) as f:
                
                import_string = f.read()
                
            
            pairs = self._DeserialiseImportString( import_string )
            
            self._AutoPetitionConflicts( pairs )
            
            self._AddPairs( pairs, add_only = add_only )
            
            self._UpdateListCtrlData()
            
        
        def _ListCtrlActivated( self ):
            
            pairs = self._tag_siblings.GetData( only_selected = True )
            
            if len( pairs ) > 0:
                
                self._AddPairs( pairs )
                
            
            self._UpdateListCtrlData()
            
        
        def _SetButtonStatus( self ):
            
            if self._current_new is None or len( self._old_siblings.GetTags() ) == 0:
                
                self._add.setEnabled( False )
                
            else:
                
                self._add.setEnabled( True )
                
            
        
        def _UpdateListCtrlData( self ):
            
            olds = self._old_siblings.GetTags()
            
            pertinent_tags = set( olds )
            
            if self._current_new is not None:
                
                pertinent_tags.add( self._current_new )
                
            
            self._tag_siblings.DeleteDatas( self._tag_siblings.GetData() )
            
            all_pairs = set()
            
            show_all = self._show_all.isChecked()
            
            for ( status, pairs ) in self._current_statuses_to_pairs.items():
                
                if status == HC.CONTENT_STATUS_DELETED:
                    
                    continue
                    
                
                if len( pertinent_tags ) == 0:
                    
                    if status == HC.CONTENT_STATUS_CURRENT and not show_all:
                        
                        continue
                        
                    
                    # show all pending/petitioned
                    
                    all_pairs.update( pairs )
                    
                else:
                    
                    # show all appropriate
                    
                    for pair in pairs:
                        
                        ( a, b ) = pair
                        
                        if a in pertinent_tags or b in pertinent_tags or show_all:
                            
                            all_pairs.add( pair )
                            
                        
                    
                
            
            self._tag_siblings.AddDatas( all_pairs )
            
            self._tag_siblings.Sort()
            
        
        def EnterOlds( self, olds ):
            
            if self._current_new in olds:
                
                self.SetNew( set() )
                
            
            self._old_siblings.EnterTags( olds )
            
            self._UpdateListCtrlData()
            
            self._SetButtonStatus()
            
        
        def EventAddButton( self ):
            
            if self._current_new is not None and len( self._old_siblings.GetTags() ) > 0:
                
                olds = self._old_siblings.GetTags()
                
                pairs = [ ( old, self._current_new ) for old in olds ]
                
                self._AutoPetitionConflicts( pairs )
                
                self._AddPairs( pairs )
                
                self._old_siblings.SetTags( set() )
                self.SetNew( set() )
                
                self._UpdateListCtrlData()
                
                self._SetButtonStatus()
                
            
        
        def GetContentUpdates( self ):
            
            # we make it manually here because of the mass pending tags done (but not undone on a rescind) on a pending pair!
            # we don't want to send a pend and then rescind it, cause that will spam a thousand bad tags and not undo it
            
            # actually, we don't do this for siblings, but we do for parents, and let's have them be the same
            
            content_updates = []
            
            if self._i_am_local_tag_service:
                
                for pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DELETE, pair ) )
                    
                
                for pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, pair ) )
                    
                
            else:
                
                current_pending = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]
                original_pending = self._original_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]
                
                current_petitioned = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]
                original_petitioned = self._original_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]
                
                new_pends = current_pending.difference( original_pending )
                rescinded_pends = original_pending.difference( current_pending )
                
                new_petitions = current_petitioned.difference( original_petitioned )
                rescinded_petitions = original_petitioned.difference( current_petitioned )
                
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_RESCIND_PETITION, pair ) for pair in rescinded_petitions ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_RESCIND_PEND, pair ) for pair in rescinded_pends ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PETITION, pair, reason = self._pairs_to_reasons[ pair ] ) for pair in new_petitions ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PEND, pair, reason = self._pairs_to_reasons[ pair ] ) for pair in new_pends ) )
                
            
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
                
            
            self._UpdateListCtrlData()
            
            self._SetButtonStatus()
            
        
        def SetTagBoxFocus( self ):
            
            if len( self._old_siblings.GetTags() ) == 0:
                
                self._old_input.setFocus( QC.Qt.OtherFocusReason )
                
            else:
                
                self._new_input.setFocus( QC.Qt.OtherFocusReason )
                
            
        
        def THREADInitialise( self, tags, service_key ):
            
            def qt_code( original_statuses_to_pairs, current_statuses_to_pairs, service_keys_to_work_to_do ):
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                self._original_statuses_to_pairs = original_statuses_to_pairs
                self._current_statuses_to_pairs = current_statuses_to_pairs
                
                self._status_st.setText( 'Tags on the left will be appear as those on the right.' )
                
                looking_good = True
                
                if len( service_keys_to_work_to_do ) == 0:
                    
                    looking_good = False
                    
                    status_text = 'No services currently apply these siblings. Changes here will have no effect unless sibling application is changed later.'
                    
                else:
                    
                    synced_names = sorted( ( HG.client_controller.services_manager.GetName( s_k ) for ( s_k, work_to_do ) in service_keys_to_work_to_do.items() if not work_to_do ) )
                    unsynced_names = sorted( ( HG.client_controller.services_manager.GetName( s_k ) for ( s_k, work_to_do ) in service_keys_to_work_to_do.items() if work_to_do ) )
                    
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
                            
                        
                    
                    if HG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_active' ):
                        
                        maintenance_part = 'Siblings are set to sync all the time in the background.'
                        
                        if looking_good:
                            
                            changes_part = 'Changes from this dialog should be reflected soon after closing the dialog.'
                            
                        else:
                            
                            changes_part = 'It may take some time for changes here to apply everywhere, though.'
                            
                        
                    else:
                        
                        looking_good = False
                        
                        if HG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_idle' ):
                            
                            maintenance_part = 'Siblings are set to sync only when you are not using the client.'
                            changes_part = 'It may take some time for changes here to apply.'
                            
                        else:
                            
                            maintenance_part = 'Siblings are not set to sync.'
                            changes_part = 'Changes here will not apply unless sync is manually forced to run.'
                            
                        
                    
                    s = os.linesep * 2
                    status_text = s.join( ( service_part, maintenance_part, changes_part ) )
                    
                
                if not self._i_am_local_tag_service:
                    
                    account = self._service.GetAccount()
                    
                    if account.IsUnknown():
                        
                        looking_good = False
                        
                        s = 'The account for this service is currently unsynced! It is uncertain if you have permission to upload parents! Please try to refresh the account in _review services_.'
                        
                        status_text = '{}{}{}'.format( s, os.linesep * 2, status_text )
                        
                    elif not account.HasPermission( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.PERMISSION_ACTION_PETITION ):
                        
                        looking_good = False
                        
                        s = 'The account for this service does not seem to have permission to upload parents! You can edit them here for now, but the pending menu will not try to upload any changes you make.'
                        
                        status_text = '{}{}{}'.format( s, os.linesep * 2, status_text )
                        
                    
                
                self._sync_status_st.setText( status_text )
                
                if looking_good:
                    
                    self._sync_status_st.setObjectName( 'HydrusValid' )
                    
                else:
                    
                    self._sync_status_st.setObjectName( 'HydrusWarning' )
                    
                
                self._sync_status_st.style().polish( self._sync_status_st )
                
                self._count_st.setText( 'Starting with '+HydrusData.ToHumanInt(len(original_statuses_to_pairs[HC.CONTENT_STATUS_CURRENT]))+' pairs.' )
                
                self._listctrl_panel.setEnabled( True )
                
                self._old_input.setEnabled( True )
                self._new_input.setEnabled( True )
                
                if tags is None:
                    
                    self._UpdateListCtrlData()
                    
                else:
                    
                    self.EnterOlds( tags )
                    
                
            
            original_statuses_to_pairs = HG.client_controller.Read( 'tag_siblings', service_key )
            
            ( master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys ) = HG.client_controller.Read( 'tag_display_application' )
            
            service_keys_we_care_about = { s_k for ( s_k, s_ks ) in master_service_keys_to_sibling_applicable_service_keys.items() if service_key in s_ks }
            
            service_keys_to_work_to_do = {}
            
            for s_k in service_keys_we_care_about:
                
                status = HG.client_controller.Read( 'tag_display_maintenance_status', s_k )
                
                work_to_do = status[ 'num_siblings_to_sync' ] > 0
                
                service_keys_to_work_to_do[ s_k ] = work_to_do
                
            
            current_statuses_to_pairs = collections.defaultdict( set )
            
            current_statuses_to_pairs.update( { key : set( value ) for ( key, value ) in original_statuses_to_pairs.items() } )
            
            QP.CallAfter( qt_code, original_statuses_to_pairs, current_statuses_to_pairs, service_keys_to_work_to_do )
            
        
    
class ReviewTagDisplayMaintenancePanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._tag_services_notebook = ClientGUICommon.BetterNotebook( self )
        
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._tag_services_notebook, 100 )
        
        self._tag_services_notebook.setMinimumWidth( min_width )
        
        #
        
        services = list( HG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES ) )
        
        select_service_key = services[0].GetServiceKey()
        
        for service in services:
            
            service_key = service.GetServiceKey()
            name = service.GetName()
            
            page = self._Panel( self._tag_services_notebook, service_key )
            
            self._tag_services_notebook.addTab( page, name )
            
            if service_key == select_service_key:
                
                self._tag_services_notebook.setCurrentWidget( page )
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        message = 'Figuring out how tags should appear according to sibling and parent application rules takes time. When you set new rules, the changes do not happen immediately--the client catches up in the background. You can review current progress and force faster sync here.'
        
        self._message = ClientGUICommon.BetterStaticText( self, label = message )
        self._message.setWordWrap( True )
        
        self._sync_status = ClientGUICommon.BetterStaticText( self )
        
        self._sync_status.setWordWrap( True )
        
        self._UpdateStatusText()
        
        QP.AddToLayout( vbox, self._message, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._sync_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tag_services_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        HG.client_controller.sub( self, '_UpdateStatusText', 'notify_new_menu_option' )
        
    
    def _UpdateStatusText( self ):
        
        if HG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_active' ):
            
            self._sync_status.setText( 'Siblings and parents are set to sync all the time. If there is work to do here, it should be cleared out in real time as you watch.' )
            
            self._sync_status.setObjectName( 'HydrusValid' )
            
        else:
            
            if HG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_idle' ):
                
                self._sync_status.setText( 'Siblings and parents are only set to sync during idle time. If there is work to do here, it should be cleared out when you are not using the client.' )
                
            else:
                
                self._sync_status.setText( 'Siblings and parents are not set to sync in the background at any time. If there is work to do here, you can force it now by clicking \'work now!\' button.' )
                
            
            self._sync_status.setObjectName( 'HydrusWarning' )
            
        
        self._sync_status.style().polish( self._sync_status )
        
    
    class _Panel( QW.QWidget ):
        
        def __init__( self, parent, service_key ):
            
            QW.QWidget.__init__( self, parent )
            
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
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
            self._refresh_values_updater = self._InitialiseRefreshValuesUpdater()
            
            HG.client_controller.sub( self, 'NotifyRefresh', 'notify_new_tag_display_sync_status' )
            HG.client_controller.sub( self, '_StartRefresh', 'notify_new_tag_display_application' )
            
            self._StartRefresh()
            
        
        def _InitialiseRefreshValuesUpdater( self ):
            
            service_key = self._service_key
            
            def loading_callable():
                
                self._progress.SetText( 'refreshing\u2026' )
                
                self._refresh_button.setEnabled( False )
                
                # keep button available to slow down
                running_fast_and_button_is_slow = HG.client_controller.tag_display_maintenance_manager.CurrentlyGoingFaster( self._service_key ) and 'slow' in self._go_faster_button.text()
                
                if not running_fast_and_button_is_slow:
                    
                    self._go_faster_button.setEnabled( False )
                    
                
            
            def work_callable():
                
                status = HG.client_controller.Read( 'tag_display_maintenance_status', service_key )
                
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
                    
                    message = '{} siblings to sync.'.format( HydrusData.ToHumanInt( num_siblings_to_sync ) )
                    
                elif num_siblings_to_sync == 0:
                    
                    message = '{} parents to sync.'.format( HydrusData.ToHumanInt( num_parents_to_sync ) )
                    
                else:
                    
                    message = '{} siblings and {} parents to sync.'.format( HydrusData.ToHumanInt( num_siblings_to_sync ), HydrusData.ToHumanInt( num_parents_to_sync ) )
                    
                
                if len( status[ 'waiting_on_tag_repos' ] ) > 0:
                    
                    message += os.linesep * 2
                    message += os.linesep.join( status[ 'waiting_on_tag_repos' ] )
                    
                    sync_halted = True
                    
                
                self._siblings_and_parents_st.setText( message )
                
                #
                
                num_actual_rows = status[ 'num_actual_rows' ]
                num_ideal_rows = status[ 'num_ideal_rows' ]
                
                if num_items_to_regen == 0:
                    
                    if num_ideal_rows == 0:
                        
                        message = 'No siblings/parents applying to this service.'
                        
                    else:
                        
                        message = '{} rules, all synced!'.format( HydrusData.ToHumanInt( num_ideal_rows ) )
                        
                    
                    value = 1
                    range = 1
                    
                    sync_work_to_do = False
                    
                else:
                    
                    value = None
                    range = None
                    
                    if num_ideal_rows == 0:
                        
                        message = 'Removing all siblings/parents, {} rules remaining.'.format( HydrusData.ToHumanInt( num_actual_rows ) )
                        
                    else:
                        
                        message = '{} rules applied now, moving to {}.'.format( HydrusData.ToHumanInt( num_actual_rows ), HydrusData.ToHumanInt( num_ideal_rows ) )
                        
                        if num_actual_rows <= num_ideal_rows:
                            
                            value = num_actual_rows
                            range = num_ideal_rows
                            
                        
                    
                    sync_work_to_do = True
                    
                
                self._progress.SetValue( message, value, range )
                
                self._refresh_button.setEnabled( True )
                
                self._go_faster_button.setVisible( sync_work_to_do and not sync_halted )
                self._go_faster_button.setEnabled( sync_work_to_do and not sync_halted )
                
                if HG.client_controller.tag_display_maintenance_manager.CurrentlyGoingFaster( self._service_key ):
                    
                    self._go_faster_button.setText( 'slow down!' )
                    
                else:
                    
                    if not HG.client_controller.new_options.GetBoolean( 'tag_display_maintenance_during_active' ):
                        
                        self._go_faster_button.setText( 'work now!' )
                        
                    else:
                        
                        self._go_faster_button.setText( 'work hard now!' )
                        
                    
                
            
            return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
            
        
        def _StartRefresh( self ):
            
            self._refresh_values_updater.update()
            
        
        def _SyncFaster( self ):
            
            HG.client_controller.tag_display_maintenance_manager.FlipSyncFaster( self._service_key )
            
            self._StartRefresh()
            
        
        def NotifyRefresh( self, service_key ):
            
            if service_key == self._service_key:
                
                self._StartRefresh()
                
            
        
    
class TagFilterButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, message, tag_filter, only_show_blacklist = False, label_prefix = None ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'tag filter', self._EditTagFilter )
        
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
            
            namespaces = HG.client_controller.network_engine.domain_manager.GetParserNamespaces()
            
            panel = EditTagFilterPanel( dlg, self._tag_filter, only_show_blacklist = self._only_show_blacklist, namespaces = namespaces, message = self._message )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._tag_filter = panel.GetValue()
                
                self._UpdateLabel()
                
            
        
    
    def _UpdateLabel( self ):
        
        if self._only_show_blacklist:
            
            tt = self._tag_filter.ToBlacklistString()
            
        else:
            
            tt = self._tag_filter.ToPermittedString()
            
        
        if self._label_prefix is not None:
            
            tt = self._label_prefix + tt
            
        
        button_text = HydrusText.ElideText( tt, 45 )
        
        self.setText( button_text )
        
        self.setToolTip( tt )
        
    
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
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        show_panel = ClientGUICommon.StaticBox( self, 'shows' )
        
        self._show = QW.QCheckBox( show_panel )
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._background_colour = ClientGUICommon.AlphaColourControl( edit_panel )
        self._text_colour = ClientGUICommon.AlphaColourControl( edit_panel )
        
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
        self._example_tags.setPlainText( os.linesep.join( example_tags ) )
        
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
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                namespace = dlg.GetValue()
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
        message = 'Edit prefix.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message, prefix, allow_blank = True ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                prefix = dlg.GetValue()
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
        message = 'Edit separator.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message, separator, allow_blank = True ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
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
        
        ClientGUICommon.BetterButton.__init__( self, parent, label, self._Edit )
        
        self._tag_summary_generator = tag_summary_generator
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit tag summary' ) as dlg:
            
            panel = EditTagSummaryGeneratorPanel( dlg, self._tag_summary_generator )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._tag_summary_generator = panel.GetValue()
                
                self.setText( self._tag_summary_generator.GenerateExampleSummary() )
                
            
        
    
    def GetValue( self ) -> TagSummaryGenerator:
        
        return self._tag_summary_generator
        
    
