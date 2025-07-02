from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBook
from hydrus.client.gui.metadata import ClientGUITagFilter
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.search import ClientGUILocation
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientTagsHandling

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
            
            self._single_tag_filter_button = ClientGUITagFilter.TagFilterButton( self._display_box, message, single_tag_filter, label_prefix = 'tags shown: ' )
            
            message = 'This filters which tags will show on \'selection\' file views such as the \'selection tags\' list on regular search pages.'
            
            self._selection_tag_filter_button = ClientGUITagFilter.TagFilterButton( self._display_box, message, selection_tag_filter, label_prefix = 'tags shown: ' )
            
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
            
        
    
