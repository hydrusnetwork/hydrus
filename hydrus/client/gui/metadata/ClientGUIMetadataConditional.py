from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientThreading
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientMetadataConditional
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearchAutocomplete
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchTagContext
from hydrus.client.search import ClientSearchPredicate

def ResultsFetch(
    win: QW.QWidget,
    job_status: ClientThreading.JobStatus,
    prefetch_callable,
    results_callable,
    parsed_autocomplete_text: ClientSearchAutocomplete.ParsedAutocompleteText,
    file_search_context: ClientSearchFileSearchContext.FileSearchContext,
    results_cache: ClientSearchAutocomplete.PredicateResultsCache,
    under_construction_or_predicate,
):
    
    results = []
    
    if parsed_autocomplete_text.IsEmpty():
        
        results = [
            ClientSearchPredicate.Predicate( predicate_type = predicate_type )
            for predicate_type
            in [
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_INBOX,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVE,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_PROPERTIES,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, # TODO: add ratio and num pixels and collapse and reorder this to 'system:dimensions'
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TAG_ADVANCED,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TIME,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_URLS,
            ]
        ]
        
        if under_construction_or_predicate is not None:
            
            ClientGUIACDropdown.PutAtTopOfMatches( results, under_construction_or_predicate )
            
        
    else:
        
        # TODO: This is mostly a botched copy of ReadFetch, so obviously this could get merged a little, somewhere, in a nice way
        
        if parsed_autocomplete_text.IsValidSystemPredicate():
            
            results = parsed_autocomplete_text.GetValidSystemPredicates()
            
            results = [ predicate for predicate in results if predicate.CanTestMediaResult() ]
            
        if under_construction_or_predicate is not None:
            
            ClientGUIACDropdown.PutAtTopOfMatches( results, under_construction_or_predicate )
            
        
        else:
            
            # user has typed a tag-like thing
            
            tag_context = file_search_context.GetTagContext()
            
            tag_service_key = tag_context.service_key
            
            if not parsed_autocomplete_text.IsAcceptableForTagSearches():
                
                matches = []
                
            else:
                
                strict_search_text = parsed_autocomplete_text.GetSearchText( False )
                autocomplete_search_text = parsed_autocomplete_text.GetSearchText( True )
                
                allow_auto_wildcard_conversion = True
                
                is_explicit_wildcard = parsed_autocomplete_text.IsExplicitWildcard( allow_auto_wildcard_conversion )
                
                if is_explicit_wildcard:
                    
                    cache_valid = False
                    
                else:
                    
                    cache_valid = results_cache.CanServeTagResults( parsed_autocomplete_text, False )
                    
                
                if cache_valid:
                    
                    matches = results_cache.FilterPredicates( tag_service_key, autocomplete_search_text )
                    
                else:
                    
                    exact_match_predicates = CG.client_controller.Read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, file_search_context, search_text = strict_search_text, exact_match = True, job_status = job_status )
                    
                    small_exact_match_search = ClientGUIACDropdown.ShouldDoExactSearch( parsed_autocomplete_text )
                    
                    if small_exact_match_search:
                        
                        results_cache = ClientSearchAutocomplete.PredicateResultsCacheTag( exact_match_predicates, strict_search_text, True )
                        
                        matches = results_cache.FilterPredicates( tag_service_key, strict_search_text )
                        
                    else:
                        
                        exact_match_matches = ClientSearchAutocomplete.FilterPredicatesBySearchText( tag_service_key, autocomplete_search_text, exact_match_predicates )
                        
                        exact_match_matches = ClientSearchPredicate.SortPredicates( exact_match_matches )
                        
                        allow_auto_wildcard_conversion = True
                        
                        ClientGUIACDropdown.InsertTagPredicates( exact_match_matches, tag_service_key, parsed_autocomplete_text, allow_auto_wildcard_conversion, insert_if_does_not_exist = False )
                        
                        include_unusual_predicate_types = True
                        
                        ClientGUIACDropdown.InsertOtherPredicatesForRead( exact_match_matches, parsed_autocomplete_text, include_unusual_predicate_types, under_construction_or_predicate )
                        
                        ClientGUIACDropdown.AppendLoadingPredicate( exact_match_matches, 'loading full results' )
                        
                        CG.client_controller.CallAfterQtSafe( win, prefetch_callable, job_status, exact_match_matches, parsed_autocomplete_text )
                        
                        #
                        
                        search_namespaces_into_full_tags = parsed_autocomplete_text.GetTagAutocompleteOptions().SearchNamespacesIntoFullTags()
                        
                        predicates = CG.client_controller.Read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, file_search_context, search_text = autocomplete_search_text, job_status = job_status, search_namespaces_into_full_tags = search_namespaces_into_full_tags )
                        
                        if job_status.IsCancelled():
                            
                            return
                            
                        
                        if is_explicit_wildcard:
                            
                            matches = ClientSearchAutocomplete.FilterPredicatesBySearchText( tag_service_key, autocomplete_search_text, predicates )
                            
                        else:
                            
                            results_cache = ClientSearchAutocomplete.PredicateResultsCacheTag( predicates, strict_search_text, False )
                            
                            matches = results_cache.FilterPredicates( tag_service_key, autocomplete_search_text )
                            
                        
                    
                
                if job_status.IsCancelled():
                    
                    return
                    
                
                matches = ClientSearchPredicate.SortPredicates( matches )
                
            
            allow_auto_wildcard_conversion = True
            
            matches = HydrusLists.FastIndexUniqueList( matches )
            
            ClientGUIACDropdown.InsertTagPredicates( matches, tag_service_key, parsed_autocomplete_text, allow_auto_wildcard_conversion, insert_if_does_not_exist = False )
            
            include_unusual_predicate_types = True
            
            ClientGUIACDropdown.InsertOtherPredicatesForRead( matches, parsed_autocomplete_text, include_unusual_predicate_types, under_construction_or_predicate )
            
            if job_status.IsCancelled():
                
                return
                
            
            results = matches
            
        
    
    ClientSearchPredicate.SetPredicatesInclusivity( results, parsed_autocomplete_text.inclusive )
    
    CG.client_controller.CallAfterQtSafe( win, results_callable, job_status, parsed_autocomplete_text, results_cache, results )
    

class AutoCompleteDropdownMetadataConditional( ClientGUIACDropdown.AutocompleteDropdownTagsFileSearchContextORCapable ):
    
    def __init__( self, parent: QW.QWidget, file_search_context: ClientSearchFileSearchContext.FileSearchContext ):
        
        # make a dupe here so we know that any direct changes we make to this guy will not affect other copies around
        file_search_context = file_search_context.Duplicate()
        
        location_context = file_search_context.GetLocationContext()
        tag_context = file_search_context.GetTagContext()
        
        page_key = HydrusData.GenerateKey()
        for_metadata_conditional = True
        
        super().__init__( parent, location_context, tag_context, file_search_context, page_key, for_metadata_conditional )
        
        self._location_context_button.setVisible( False )
        self._tag_context_button.setVisible( False )
        
        #
        
        self._paste_button = ClientGUICommon.IconButton( self._text_input_panel, CC.global_icons().paste, self._Paste )
        self._paste_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'You can paste a newline-separated list of system predicates.' ) )
        
        self._empty_search_button = ClientGUICommon.IconButton( self._text_input_panel, CC.global_icons().clear_highlight, self._ClearSearch )
        self._empty_search_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Clear the search back to an empty page.' ) )
        
        QP.AddToLayout( self._text_input_hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._text_input_hbox, self._empty_search_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        #
        
        self._include_current_tags = ClientGUICommon.OnOffButton( self._dropdown_window, on_label = 'include current tags', off_label = 'exclude current tags', start_on = tag_context.include_current_tags )
        self._include_current_tags.setToolTip( ClientGUIFunctions.WrapToolTip( 'select whether to include current tags in the search' ) )
        self._include_pending_tags = ClientGUICommon.OnOffButton( self._dropdown_window, on_label = 'include pending tags', off_label = 'exclude pending tags', start_on = tag_context.include_pending_tags )
        self._include_pending_tags.setToolTip( ClientGUIFunctions.WrapToolTip( 'select whether to include pending tags in the search' ) )
        
        self._include_current_tags.setVisible( False )
        self._include_pending_tags.setVisible( False )
        
        button_hbox_1 = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox_1, self._include_current_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox_1, self._include_pending_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        sync_button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( sync_button_hbox, self._or_basic, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( sync_button_hbox, self._or_cancel, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( sync_button_hbox, self._or_rewind, CC.FLAGS_CENTER_PERPENDICULAR )
        
        button_hbox_2 = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox_2, self._location_context_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox_2, self._tag_context_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, button_hbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, sync_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, button_hbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._dropdown_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.setLayout( vbox )
        
        self._predicates_listbox.listBoxChanged.connect( self._NotifyPredicatesBoxChanged )
        
        self._include_current_tags.valueChanged.connect( self._tag_context_button.SetIncludeCurrent )
        self._include_pending_tags.valueChanged.connect( self._tag_context_button.SetIncludePending )
        
    
    def _BroadcastCurrentInputFromEnterKey( self, shift_down ):
        
        current_broadcast_predicate = self._GetCurrentBroadcastTextPredicate()
        
        if current_broadcast_predicate is not None:
            
            self._BroadcastChoices( { current_broadcast_predicate }, shift_down )
            
        
    
    def _ClearSearch( self ):
        
        location_context = self._location_context_button.GetValue()
        
        tag_context = self._tag_context_button.GetValue()
        
        predicates = []
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, tag_context = tag_context, predicates = predicates )
        
        self.blockSignals( True )
        
        self.SetFileSearchContext( file_search_context )
        
        self.blockSignals( False )
        
        self.locationChanged.emit( self._location_context_button.GetValue() )
        
        self.tagContextChanged.emit( self._tag_context_button.GetValue() )
        
    
    def _GetCurrentBroadcastTextPredicate( self ) -> ClientSearchPredicate.Predicate | None:
        
        return None
        
    
    def _InitChildrenList( self ):
        
        return None
        
    
    def _InitSearchResultsList( self ):
        
        height_num_chars = 3
        
        tag_service_key = self._file_search_context.GetTagContext().service_key
        
        return ClientGUIACDropdown.ListBoxTagsPredicatesAC( self._dropdown_notebook, self.BroadcastChoices, self._float_mode, tag_service_key, tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, height_num_chars = height_num_chars )
        
    
    def _LocationContextJustChanged( self, location_context: ClientLocation.LocationContext ):
        
        super()._LocationContextJustChanged( location_context )
        
        self._file_search_context.SetLocationContext( location_context )
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        try:
            
            texts = HydrusText.DeserialiseNewlinedTexts( raw_text )
            
            predicates = []
            
            for text in texts:
                
                try:
                    
                    collapse_search_characters = True
                    
                    tag_service_key = self._file_search_context.GetTagContext().service_key
                    
                    tag_autocomplete_options = CG.client_controller.tag_display_manager.GetTagAutocompleteOptions( tag_service_key )
                    
                    pat = ClientSearchAutocomplete.ParsedAutocompleteText( text, tag_autocomplete_options, collapse_search_characters = collapse_search_characters )
                    
                    if pat.IsAcceptableForFileSearches():
                        
                        predicates.append( pat.GetImmediateFileSearchPredicate( allow_auto_wildcard_conversion = True ) )
                        
                    
                except Exception as e:
                    
                    continue
                    
                
            
            if len( predicates ) > 0:
                
                shift_down = False
                
                self._BroadcastChoices( predicates, shift_down )
                
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'Lines of tags', e )
            
        
    
    def _NotifyPredicatesBoxChanged( self ):
        
        predicates = self._predicates_listbox.GetPredicates()
        
        self._file_search_context.SetPredicates( predicates )
        
    
    def _SetTagContext( self, tag_context: ClientSearchTagContext.TagContext ):
        
        it_changed = super()._SetTagContext( tag_context )
        
        if it_changed:
            
            self._include_current_tags.SetOnOff( tag_context.include_current_tags )
            self._include_pending_tags.SetOnOff( tag_context.include_pending_tags )
            
        
        return it_changed
        
    
    def _ShouldBroadcastCurrentInputOnEnterKey( self ):
        
        return False
        
    
    def _StartSearchResultsFetchJob( self, job_status ):
        
        fsc = self.GetFileSearchContext()
        
        parsed_autocomplete_text = self._GetParsedAutocompleteText()
        
        if self._under_construction_or_predicate is None:
            
            under_construction_or_predicate = None
            
        else:
            
            under_construction_or_predicate = self._under_construction_or_predicate.Duplicate()
            
        
        CG.client_controller.CallToThread( ResultsFetch, self, job_status, self.SetPrefetchResults, self.SetFetchedResults, parsed_autocomplete_text, fsc, self._results_cache, under_construction_or_predicate )
        
    
    def GetPredicates( self ) -> set[ ClientSearchPredicate.Predicate ]:
        
        return self._file_search_context.GetPredicates()
        
    
    def SetFetchedResults( self, job_status: ClientThreading.JobStatus, parsed_autocomplete_text: ClientSearchAutocomplete.ParsedAutocompleteText, results_cache: ClientSearchAutocomplete.PredicateResultsCache, results: list ):
        
        if self._current_fetch_job_status is not None and self._current_fetch_job_status.GetKey() == job_status.GetKey():
            
            super().SetFetchedResults( job_status, parsed_autocomplete_text, results_cache, results )
            
        
    
    def SetFileSearchContext( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext ):
        
        self._ClearInput()
        
        super().SetFileSearchContext( file_search_context )
        
        self._predicates_listbox.SetFileSearchContext( self._file_search_context )
        
        self._SetLocationContext( self._file_search_context.GetLocationContext() )
        self._SetTagContext( self._file_search_context.GetTagContext() )
        
    
    def SetIncludeCurrent( self, value: bool ):
        
        self._include_current_tags.SetOnOff( value )
        
    
    def SetIncludePending( self, value: bool ):
        
        self._include_pending_tags.SetOnOff( value )
        
    

class EditMetadataConditionalPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, metadata_conditional: ClientMetadataConditional.MetadataConditional ):
        
        super().__init__( parent, 'metadata conditional' )
        
        self._ac_panel = AutoCompleteDropdownMetadataConditional( self, metadata_conditional.GetFileSearchContext() )
        
        self.Add( self._ac_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setFocusProxy( self._ac_panel )
        
    
    def GetValue( self ) -> ClientMetadataConditional.MetadataConditional:
        
        file_search_context = self._ac_panel.GetFileSearchContext()
        
        metadata_conditional = ClientMetadataConditional.MetadataConditional()
        
        metadata_conditional.SetFileSearchContext( file_search_context )
        
        return metadata_conditional
        
    
