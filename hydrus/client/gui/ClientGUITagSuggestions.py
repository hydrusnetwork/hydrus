import collections.abc

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusTime

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListBoxesData
from hydrus.client.gui.parsing import ClientGUIParsingLegacy
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientTagSorting
from hydrus.client.parsing import ClientParsingLegacy
from hydrus.client.search import ClientSearchPredicate

def FilterSuggestedPredicatesForMedia( predicates: collections.abc.Sequence[ ClientSearchPredicate.Predicate ], medias: collections.abc.Collection[ ClientMedia.Media ], service_key: bytes ) -> list[ ClientSearchPredicate.Predicate ]:
    
    tags = [ predicate.GetValue() for predicate in predicates ]
    
    filtered_tags = FilterSuggestedTagsForMedia( tags, medias, service_key )
    
    predicates = [ predicate for predicate in predicates if predicate.GetValue() in filtered_tags ]
    
    return predicates
    

def FilterSuggestedTagsForMedia( tags: collections.abc.Sequence[ str ], medias: collections.abc.Collection[ ClientMedia.Media ], service_key: bytes ) -> list[ str ]:
    
    num_media = len( medias )
    
    useful_tags_set = set( tags )
    
    ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientMedia.GetMediasTagCount( medias, service_key, ClientTags.TAG_DISPLAY_STORAGE )
    
    current_tags_to_count.update( pending_tags_to_count )
    
    # TODO: figure out a nicer way to filter out siblings and parents here
    # maybe have to wait for when tags always know their siblings
    # then we could also filter out worse/better siblings of the same count
    
    # this is a sync way for now:
    # db_tags_to_ideals_and_parents = CG.client_controller.Read( 'tag_display_decorators', service_key, tags_to_lookup )
    
    for ( tag, count ) in current_tags_to_count.items():
        
        if count == num_media:
            
            useful_tags_set.discard( tag )
            
        
    
    tags_filtered = [ tag for tag in tags if tag in useful_tags_set ]
    
    return tags_filtered
    
class ListBoxTagsSuggestionsFavourites( ClientGUIListBoxes.ListBoxTagsStrings ):
    
    def __init__( self, parent, service_key, activate_callable, sort_tags = True ):
        
        super().__init__( parent, service_key = service_key, sort_tags = sort_tags, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE )
        
        self._activate_callable = activate_callable
        
        width = CG.client_controller.new_options.GetInteger( 'suggested_tags_width' )
        
        if width is not None:
            
            self.setMinimumWidth( width )
            
        
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        if len( self._selected_terms ) > 0:
            
            tags = set( self._GetTagsFromTerms( self._selected_terms ) )
            
            self._activate_callable( tags, only_add = True )
            
            self._RemoveSelectedTerms()
            
            self._DataHasChanged()
            
            return True
            
        
        return False
        
    
    def _Sort( self ):
        
        self._RegenTermsToIndices()
        
    
    def ActivateAll( self ):
        
        self._activate_callable( self.GetTags(), only_add = True )
        
    
    def TakeFocusForUser( self ):
        
        self.SelectTopItem()
        
        self.setFocus( QC.Qt.FocusReason.OtherFocusReason )
        
    
class ListBoxTagsSuggestionsRelated( ClientGUIListBoxes.ListBoxTagsPredicates ):
    
    def __init__( self, parent, service_key, activate_callable ):
        
        super().__init__( parent, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE )
        
        self._activate_callable = activate_callable
        
        width = CG.client_controller.new_options.GetInteger( 'suggested_tags_width' )
        
        self.setMinimumWidth( width )
        
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        if len( self._selected_terms ) > 0:
            
            tags = set( self._GetTagsFromTerms( self._selected_terms ) )
            
            self._activate_callable( tags, only_add = True )
            
            self._RemoveSelectedTerms()
            
            self._DataHasChanged()
            
            return True
            
        
        return False
        
    
    def _GenerateTermFromPredicate( self, predicate: ClientSearchPredicate.Predicate ) -> ClientGUIListBoxesData.ListBoxItemPredicate:
        
        predicate = predicate.GetCountlessCopy()
        
        return ClientGUIListBoxesData.ListBoxItemPredicate( predicate )
        
    
    def _Sort( self ):
        
        self._RegenTermsToIndices()
        
    
    def TakeFocusForUser( self ):
        
        self.SelectTopItem()
        
        self.setFocus( QC.Qt.FocusReason.OtherFocusReason )
        
    
class FavouritesTagsPanel( QW.QWidget ):
    
    mouseActivationOccurred = QC.Signal()
    
    def __init__( self, parent, service_key, tag_presentation_location: int, activate_callable ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        self._tag_presentation_location = tag_presentation_location
        self._media = []
        
        vbox = QP.VBoxLayout()
        
        self._favourite_tags = ListBoxTagsSuggestionsFavourites( self, self._service_key, activate_callable, sort_tags = False )
        
        QP.AddToLayout( vbox, self._favourite_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self._UpdateTagDisplay()
        
        self._favourite_tags.mouseActivationOccurred.connect( self.mouseActivationOccurred )
        
    
    def _UpdateTagDisplay( self ):
        
        favourites = list( CG.client_controller.new_options.GetSuggestedTagsFavourites( self._service_key ) )
        
        ClientTagSorting.SortTags( CG.client_controller.new_options.GetDefaultTagSort( self._tag_presentation_location ), favourites )
        
        tags = FilterSuggestedTagsForMedia( favourites, self._media, self._service_key )
        
        self._favourite_tags.SetTags( tags )
        
    
    def MediaUpdated( self ):
        
        self._UpdateTagDisplay()
        
    
    def SetMedia( self, media ):
        
        self._media = media
        
        self._UpdateTagDisplay()
        
    
    def TakeFocusForUser( self ):
        
        self._favourite_tags.TakeFocusForUser()
        
    
class RecentTagsPanel( QW.QWidget ):
    
    mouseActivationOccurred = QC.Signal()
    
    def __init__( self, parent, service_key, activate_callable ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        self._media = []
        
        self._last_fetched_tags = []
        
        self._new_options = CG.client_controller.new_options
        
        vbox = QP.VBoxLayout()
        
        clear_button = QW.QPushButton( 'clear', self )
        clear_button.clicked.connect( self.EventClear )
        
        self._recent_tags = ListBoxTagsSuggestionsFavourites( self, self._service_key, activate_callable, sort_tags = False )
        
        QP.AddToLayout( vbox, clear_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._recent_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self._RefreshRecentTags()
        
        self._recent_tags.mouseActivationOccurred.connect( self.mouseActivationOccurred )
        
    
    def _RefreshRecentTags( self ):
        
        def do_it( service_key ):
            
            def qt_code( recent_tags ):
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                self._last_fetched_tags = recent_tags
                
                self._UpdateTagDisplay()
                
                if len( self._recent_tags.GetTags() ) > 0:
                    
                    self._recent_tags.SelectTopItem()
                    
                
            
            recent_tags = CG.client_controller.Read( 'recent_tags', service_key )
            
            CG.client_controller.CallAfter( self, qt_code, recent_tags )
            
        
        CG.client_controller.CallToThread( do_it, self._service_key )
        
    
    def _UpdateTagDisplay( self ):
        
        tags = FilterSuggestedTagsForMedia( self._last_fetched_tags, self._media, self._service_key )
        
        self._recent_tags.SetTags( tags )
        
    
    def EventClear( self ):
        
        from hydrus.client.gui import ClientGUIDialogsQuick
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Clear recent tags?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.Write( 'push_recent_tags', self._service_key, None )
            
            self._last_fetched_tags = []
            
            self._UpdateTagDisplay()
            
        
    
    def RefreshRecentTags( self ):
        
        self._RefreshRecentTags()
        
    
    def MediaUpdated( self ):
        
        self._UpdateTagDisplay()
        
    
    def SetMedia( self, media ):
        
        self._media = media
        
        self._UpdateTagDisplay()
        
        self._RefreshRecentTags()
        
    
    def TakeFocusForUser( self ):
        
        self._recent_tags.TakeFocusForUser()
        
    
class RelatedTagsPanel( QW.QWidget ):
    
    mouseActivationOccurred = QC.Signal()
    
    def __init__( self, parent, service_key, activate_callable ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        self._media = []
        
        self._last_fetched_predicates = []
        
        self._have_done_search_with_this_media = False
        
        self._selected_tags = set()
        
        self._new_options = CG.client_controller.new_options
        
        vbox = QP.VBoxLayout()
        
        self._status_label = ClientGUICommon.BetterStaticText( self, label = 'ready' )
        
        self._just_do_local_files = ClientGUICommon.OnOffButton( self, on_label = 'just for my files', off_label = 'for all known files', start_on = True )
        self._just_do_local_files.setToolTip( ClientGUIFunctions.WrapToolTip( 'Select how big the search is. Searching across all known files on a repository produces high quality results but takes a long time.' ) )
        
        tt = 'If you select some tags, this will search using only those as reference!'
        
        self._button_1 = QW.QPushButton( 'quick', self )
        self._button_1.clicked.connect( self.RefreshQuick )
        self._button_1.setMinimumWidth( 30 )
        self._button_1.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._button_2 = QW.QPushButton( 'medium', self )
        self._button_2.clicked.connect( self.RefreshMedium )
        self._button_2.setMinimumWidth( 30 )
        self._button_2.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._button_3 = QW.QPushButton( 'thorough', self )
        self._button_3.clicked.connect( self.RefreshThorough )
        self._button_3.setMinimumWidth( 30 )
        self._button_3.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        if CG.client_controller.services_manager.GetServiceType( self._service_key ) == HC.LOCAL_TAG:
            
            self._just_do_local_files.setVisible( False )
            
        
        self._related_tags = ListBoxTagsSuggestionsRelated( self, service_key, activate_callable )
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._button_1, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( button_hbox, self._button_2, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( button_hbox, self._button_3, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        QP.AddToLayout( vbox, self._status_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._just_do_local_files, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._related_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self._related_tags.mouseActivationOccurred.connect( self.mouseActivationOccurred )
        
    
    def _FetchRelatedTagsNew( self, max_time_to_take ):
        
        def do_it( file_service_key, tag_service_key, search_tags, other_tags_to_exclude ):
            
            def qt_code( predicates, num_done, num_to_do, num_skipped, total_time_took ):
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                if num_skipped == 0:
                    
                    tags_s = 'tags'
                    
                else:
                    
                    tags_s = 'tags ({} skipped)'.format( HydrusNumbers.ToHumanInt( num_skipped ) )
                    
                
                if num_done == num_to_do:
                    
                    num_done_s = 'Searched {} {} in '.format( HydrusNumbers.ToHumanInt( num_done ), tags_s )
                    
                else:
                    
                    num_done_s = '{} {} searched fully in '.format( HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do ), tags_s )
                    
                
                label = '{}{}.'.format( num_done_s, HydrusTime.TimeDeltaToPrettyTimeDelta( total_time_took ) )
                
                self._status_label.setText( label )
                
                self._last_fetched_predicates = predicates
                
                self._UpdateTagDisplay()
                
                self._have_done_search_with_this_media = True
                
            
            start_time = HydrusTime.GetNowPrecise()
            
            concurrence_threshold = CG.client_controller.new_options.GetInteger( 'related_tags_concurrence_threshold_percent' ) / 100
            search_tag_slices_weight_dict = { ':' : 1.0, '' : 1.0 }
            result_tag_slices_weight_dict = { ':' : 1.0, '' : 1.0 }
            
            ( related_tags_search_tag_slices_weight_percent, related_tags_result_tag_slices_weight_percent ) = CG.client_controller.new_options.GetRelatedTagsTagSliceWeights()
            
            for ( tag_slice, weight_percent ) in related_tags_search_tag_slices_weight_percent:
                
                if HydrusTags.IsNamespaceTagSlice( tag_slice ):
                    
                    tag_slice = tag_slice[ : -1 ]
                    
                
                search_tag_slices_weight_dict[ tag_slice ] = weight_percent / 100
                
            
            for ( tag_slice, weight_percent ) in related_tags_result_tag_slices_weight_percent:
                
                if HydrusTags.IsNamespaceTagSlice( tag_slice ):
                    
                    tag_slice = tag_slice[ : -1 ]
                    
                
                result_tag_slices_weight_dict[ tag_slice ] = weight_percent / 100
                
            
            ( num_done, num_to_do, num_skipped, predicates ) = CG.client_controller.Read(
                'related_tags',
                file_service_key,
                tag_service_key,
                search_tags,
                max_time_to_take = max_time_to_take,
                concurrence_threshold = concurrence_threshold,
                search_tag_slices_weight_dict = search_tag_slices_weight_dict,
                result_tag_slices_weight_dict = result_tag_slices_weight_dict,
                other_tags_to_exclude = other_tags_to_exclude
            )
            
            total_time_took = HydrusTime.GetNowPrecise() - start_time
            
            predicates = ClientSearchPredicate.SortPredicates( predicates )
            
            CG.client_controller.CallAfter( self, qt_code, predicates, num_done, num_to_do, num_skipped, total_time_took )
            
        
        self._related_tags.SetPredicates( [] )
        
        if len( self._selected_tags ) == 0:
            
            search_tags = ClientMedia.GetMediasTags( self._media, self._service_key, ClientTags.TAG_DISPLAY_STORAGE, ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING ) )
            other_tags_to_exclude = None
            
        else:
            
            search_tags = self._selected_tags
            other_tags_to_exclude = set( ClientMedia.GetMediasTags( self._media, self._service_key, ClientTags.TAG_DISPLAY_STORAGE, ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING ) ) ).difference( self._selected_tags )
            
        
        if len( search_tags ) == 0:
            
            self._status_label.setVisible( False )
            
            return
            
        
        self._status_label.setVisible( True )
        
        self._status_label.setText( 'searching' + HC.UNICODE_ELLIPSIS )
        
        if self._just_do_local_files.IsOn():
            
            file_service_key = CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY
            
        else:
            
            file_service_key = CC.COMBINED_FILE_SERVICE_KEY
            
        
        tag_service_key = self._service_key
        
        CG.client_controller.CallToThread( do_it, file_service_key, tag_service_key, search_tags, other_tags_to_exclude )
        
    
    def _UpdateTagDisplay( self ):
        
        predicates = FilterSuggestedPredicatesForMedia( self._last_fetched_predicates, self._media, self._service_key )
        
        self._related_tags.SetPredicates( predicates )
        
    
    def RefreshQuick( self ):
        
        max_time_to_take = HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'related_tags_search_1_duration_ms' ) )
        
        self._FetchRelatedTagsNew( max_time_to_take )
        
    
    def RefreshMedium( self ):
        
        max_time_to_take = HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'related_tags_search_2_duration_ms' ) )
        
        self._FetchRelatedTagsNew( max_time_to_take )
        
    
    def RefreshThorough( self ):
        
        max_time_to_take = HydrusTime.SecondiseMSFloat( self._new_options.GetInteger( 'related_tags_search_3_duration_ms' ) )
        
        self._FetchRelatedTagsNew( max_time_to_take )
        
    
    def MediaUpdated( self ):
        
        self._UpdateTagDisplay()
        
    
    def NotifyUserLooking( self ):
        
        if not self._have_done_search_with_this_media:
            
            self.RefreshQuick()
            
        
    
    def SetMedia( self, media ):
        
        self._media = media
        
        self._status_label.setText( 'ready' )
        
        self._related_tags.SetPredicates( [] )
        
        self._have_done_search_with_this_media = False
        
    
    def SetSelectedTags( self, tags ):
        
        self._selected_tags = tags
        
    
    def TakeFocusForUser( self ):
        
        self._related_tags.TakeFocusForUser()
        
    
class FileLookupScriptTagsPanel( QW.QWidget ):
    
    mouseActivationOccurred = QC.Signal()
    
    def __init__( self, parent, service_key, activate_callable ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        self._media = []
        self._last_fetched_tags = []
        
        self._script_choice = ClientGUICommon.BetterChoice( self )
        
        self._script_choice.setEnabled( False )
        
        self._have_fetched = False
        
        self._fetch_button = ClientGUICommon.BetterButton( self, 'fetch tags', self.FetchTags )
        
        self._fetch_button.setEnabled( False )
        
        self._script_management = ClientGUIParsingLegacy.ScriptManagementControl( self )
        
        self._tags = ListBoxTagsSuggestionsFavourites( self, self._service_key, activate_callable, sort_tags = True )
        
        self._add_all = ClientGUICommon.BetterButton( self, 'add all', self._tags.ActivateAll )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._script_choice, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._fetch_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._script_management, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._add_all, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._SetTags( [] )
        
        self.setLayout( vbox )
        
        self._FetchScripts()
        
        self._tags.mouseActivationOccurred.connect( self.mouseActivationOccurred )
        
    
    def _FetchScripts( self ):
        
        def do_it():
            
            def qt_code():
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                script_names_to_scripts = { script.GetName() : script for script in scripts }
                
                for ( name, script ) in list(script_names_to_scripts.items()):
                    
                    self._script_choice.addItem( script.GetName(), script )
                    
                
                new_options = CG.client_controller.new_options
                
                favourite_file_lookup_script = new_options.GetNoneableString( 'favourite_file_lookup_script' )
                
                if favourite_file_lookup_script in script_names_to_scripts:
                    
                    self._script_choice.SetValue( script_names_to_scripts[ favourite_file_lookup_script ] )
                    
                else:
                    
                    self._script_choice.setCurrentIndex( 0 )
                    
                
                self._script_choice.setEnabled( True )
                self._fetch_button.setEnabled( True )
                
            
            scripts = CG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP )
            
            CG.client_controller.CallAfter( self, qt_code )
            
        
        CG.client_controller.CallToThread( do_it )
        
    
    def _SetTags( self, tags ):
        
        self._last_fetched_tags = tags
        
        self._UpdateTagDisplay()
        
    
    def _UpdateTagDisplay( self ):
        
        tags = FilterSuggestedTagsForMedia( self._last_fetched_tags, self._media, self._service_key )
        
        self._tags.SetTags( tags )
        
        if len( tags ) == 0:
            
            self._add_all.setEnabled( False )
            
        else:
            
            self._add_all.setEnabled( True )
            
        
    
    def FetchTags( self ):
        
        script = self._script_choice.GetValue()
        
        if script.UsesUserInput():
            
            message = 'Enter the custom input for the file lookup script.'
            
            try:
                
                file_identifier = ClientGUIDialogsQuick.EnterText( self, message )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
        else:
            
            ( m, ) = self._media
            
            file_identifier = script.ConvertMediaToFileIdentifier( m )
            
        
        stop_time = HydrusTime.GetNow() + 30
        
        job_status = ClientThreading.JobStatus( cancellable = True, stop_time = stop_time )
        
        self._script_management.SetJobStatus( job_status )
        
        self._SetTags( [] )
        
        CG.client_controller.CallToThread( self.THREADFetchTags, script, job_status, file_identifier )
        
    
    def MediaUpdated( self ):
        
        self._UpdateTagDisplay()
        
    
    def SetMedia( self, media ):
        
        self._media = media
        
        self._UpdateTagDisplay()
        
    
    def TakeFocusForUser( self ):
        
        if self._have_fetched:
            
            self._tags.TakeFocusForUser()
            
        else:
            
            self._fetch_button.setFocus( QC.Qt.FocusReason.OtherFocusReason )
            
        
    
    def THREADFetchTags( self, script: ClientParsingLegacy.ParseRootFileLookup, job_status, file_identifier ):
        
        def qt_code( tags ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._SetTags( tags )
            
            self._have_fetched = True
            
        
        parsed_post = script.DoQuery( job_status, file_identifier )
        
        tags = list( parsed_post.GetTags() )
        
        tag_sort = ClientTagSorting.TagSort( ClientTagSorting.SORT_BY_HUMAN_TAG, sort_order = CC.SORT_ASC )
        
        ClientTagSorting.SortTags( tag_sort, tags )
        
        CG.client_controller.CallAfter( self, qt_code, tags )
        
    
class SuggestedTagsPanel( QW.QWidget ):
    
    mouseActivationOccurred = QC.Signal()
    
    def __init__( self, parent, service_key, tag_presentation_location, handling_one_media, activate_callable ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        self._tag_presentation_location = tag_presentation_location
        self._media = []
        
        self._new_options = CG.client_controller.new_options
        
        layout_mode = self._new_options.GetNoneableString( 'suggested_tags_layout' )
        
        self._notebook = None
        
        if layout_mode == 'notebook':
            
            self._notebook = ClientGUICommon.BetterNotebook( self )
            
            panel_parent = self._notebook
            
        else:
            
            panel_parent = self
            
        
        panels = []
        
        self._favourite_tags = None
        
        favourites = CG.client_controller.new_options.GetSuggestedTagsFavourites( self._service_key )
        
        if len( favourites ) > 0:
            
            self._favourite_tags = FavouritesTagsPanel( panel_parent, service_key, self._tag_presentation_location, activate_callable )
            
            self._favourite_tags.mouseActivationOccurred.connect( self.mouseActivationOccurred )
            
            panels.append( ( 'most used', self._favourite_tags ) )
            
        
        self._related_tags = None
        
        if self._new_options.GetBoolean( 'show_related_tags' ):
            
            self._related_tags = RelatedTagsPanel( panel_parent, service_key, activate_callable )
            
            self._related_tags.mouseActivationOccurred.connect( self.mouseActivationOccurred )
            
            panels.append( ( 'related', self._related_tags ) )
            
        
        self._file_lookup_script_tags = None
        
        if self._new_options.GetBoolean( 'show_file_lookup_script_tags' ) and handling_one_media:
            
            self._file_lookup_script_tags = FileLookupScriptTagsPanel( panel_parent, service_key, activate_callable )
            
            self._file_lookup_script_tags.mouseActivationOccurred.connect( self.mouseActivationOccurred )
            
            panels.append( ( 'file lookup scripts', self._file_lookup_script_tags ) )
            
        
        self._recent_tags = None
        
        if self._new_options.GetNoneableInteger( 'num_recent_tags' ) is not None:
            
            self._recent_tags = RecentTagsPanel( panel_parent, service_key, activate_callable )
            
            self._recent_tags.mouseActivationOccurred.connect( self.mouseActivationOccurred )
            
            panels.append( ( 'recent', self._recent_tags ) )
            
        
        hbox = QP.HBoxLayout()
        
        if layout_mode == 'notebook':
            
            for ( name, panel ) in panels:
                
                self._notebook.addTab( panel, name )
                
            
            QP.AddToLayout( hbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            name_to_page_dict = {
                'favourites' : self._favourite_tags,
                'most used' : self._favourite_tags,
                'related' : self._related_tags,
                'file_lookup_scripts' : self._file_lookup_script_tags,
                'recent' : self._recent_tags
            }
            
            default_suggested_tags_notebook_page = self._new_options.GetString( 'default_suggested_tags_notebook_page' )
            
            choice = name_to_page_dict.get( default_suggested_tags_notebook_page, None )
            
            if choice is not None:
                
                self._notebook.setCurrentWidget( choice )
                
            
            self._notebook.currentChanged.connect( self._PageChanged )
            
        elif layout_mode == 'columns':
            
            for ( name, panel ) in panels:
                
                box_panel = ClientGUICommon.StaticBox( self, name )
                
                box_panel.Add( panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                QP.AddToLayout( hbox, box_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
        
        self.setLayout( hbox )
        
        if len( panels ) == 0:
            
            self.hide()
            
        else:
            
            self._PageChanged()
            
        
    
    def _PageChanged( self ):
        
        if self._related_tags is not None:
            
            if self._notebook is None:
                
                self._related_tags.NotifyUserLooking()
                
                return
                
            
            current_page = self._notebook.currentWidget()
            
            if current_page == self._related_tags:
                
                self._related_tags.NotifyUserLooking()
                
            
        
    
    def MediaUpdated( self ):
        
        if self._favourite_tags is not None:
            
            self._favourite_tags.MediaUpdated()
            
        
        if self._recent_tags is not None:
            
            self._recent_tags.MediaUpdated()
            
        
        if self._file_lookup_script_tags is not None:
            
            self._file_lookup_script_tags.MediaUpdated()
            
        
        if self._related_tags is not None:
            
            self._related_tags.MediaUpdated()
            
        
    
    def RefreshRelatedThorough( self ):
        
        if self._related_tags is not None:
            
            self._related_tags.RefreshThorough()
            
        
    
    def SetMedia( self, media ):
        
        self._media = media
        
        if self._favourite_tags is not None:
            
            self._favourite_tags.SetMedia( media )
            
        
        if self._recent_tags is not None:
            
            self._recent_tags.SetMedia( media )
            
        
        if self._file_lookup_script_tags is not None:
            
            self._file_lookup_script_tags.SetMedia( media )
            
        
        if self._related_tags is not None:
            
            self._related_tags.SetMedia( media )
            
        
        self._PageChanged()
        
    
    def SetSelectedTags( self, tags ):
        
        if self._related_tags is not None:
            
            self._related_tags.SetSelectedTags( tags )
            
        
    
    def TakeFocusForUser( self, command ):
        
        if command == CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_FAVOURITE_TAGS:
            
            panel = self._favourite_tags
            
        elif command == CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_RELATED_TAGS:
            
            panel = self._related_tags
            
        elif command == CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_FILE_LOOKUP_SCRIPT_TAGS:
            
            panel = self._file_lookup_script_tags
            
        elif command == CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_RECENT_TAGS:
            
            panel = self._recent_tags
            
        
        if panel is not None:
            
            if self._notebook is not None:
                
                self._notebook.SelectPage( panel )
                
            
            panel.TakeFocusForUser()
            
        
    
