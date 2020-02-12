from . import ClientCaches
from . import ClientConstants as CC
from . import ClientData
from . import ClientGUICommon
from . import ClientGUIFunctions
from . import ClientGUIListBoxes
from . import ClientGUIMenus
from . import ClientGUIShortcuts
from . import ClientSearch
from . import ClientTags
from . import ClientThreading
from . import ClientGUIScrolledPanels
from . import ClientGUITopLevelWindows
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusTags
from . import HydrusText
import itertools
from . import LogicExpressionQueryParser
import os
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
from . import QtPorting as QP

def AppendLoadingPredicate( predicates ):
    
    predicates.append( ClientSearch.Predicate( predicate_type = HC.PREDICATE_TYPE_LABEL, value = 'loading results\u2026' ) )
    
def CacheCanBeUsedForInput( search_text_for_cache, new_search_text ):
    
    if search_text_for_cache is None:
        
        return False
        
    
    if new_search_text is None:
        
        return False
        
    
    namespace_cache = ':' in search_text_for_cache
    namespace_search = ':' in new_search_text
    
    if ( namespace_cache and namespace_search ) or ( not namespace_cache and not namespace_search ):
        
        if new_search_text.startswith( search_text_for_cache ):
            
            return True
            
        
    
    return False
    
def InsertStaticPredicatesForRead( predicates, parsed_search_text, include_unusual_predicate_types, under_construction_or_predicate ):
    
    ( raw_entry, inclusive, wildcard_text, search_text, explicit_wildcard, cache_text, entry_predicate ) = parsed_search_text
    
    if search_text in ( '', ':', '*' ):
        
        pass
        
    else:
        
        if include_unusual_predicate_types:
            
            if explicit_wildcard:
                
                if wildcard_text != search_text:
                    
                    predicates.insert( 0, ClientSearch.Predicate( HC.PREDICATE_TYPE_WILDCARD, search_text, inclusive ) )
                    
                
                predicates.insert( 0, ClientSearch.Predicate( HC.PREDICATE_TYPE_WILDCARD, wildcard_text, inclusive ) )
                
            else:
                
                ( namespace, subtag ) = HydrusTags.SplitTag( search_text )
                
                if namespace != '' and subtag in ( '', '*' ):
                    
                    predicates.insert( 0, ClientSearch.Predicate( HC.PREDICATE_TYPE_NAMESPACE, namespace, inclusive ) )
                    
                
            
        
        try:
            
            index = predicates.index( entry_predicate )
            
            predicate = predicates[ index ]
            
            del predicates[ index ]
            
            predicates.insert( 0, predicate )
            
        except:
            
            pass
            
        
    
    if under_construction_or_predicate is not None:
        
        predicates.insert( 0, under_construction_or_predicate )
        
    
    return predicates
    
def InsertStaticPredicatesForWrite( predicates, parsed_search_text, tag_service_key, expand_parents ):
    
    ( raw_entry, search_text, cache_text, entry_predicate, sibling_predicate ) = parsed_search_text
    
    ( namespace, subtag ) = HydrusTags.SplitTag( search_text )
    
    if search_text in ( '', ':', '*' ) or subtag == '':
        
        pass
        
    else:
        
        PutAtTopOfMatches( predicates, entry_predicate )
        
        if sibling_predicate is not None:
            
            PutAtTopOfMatches( predicates, sibling_predicate )
            
        
        if expand_parents:
            
            predicates = HG.client_controller.tag_parents_manager.ExpandPredicates( tag_service_key, predicates )
            
        
    
    return predicates
    
def ReadFetch( win, job_key, results_callable, parsed_search_text, qt_media_callable, file_search_context, synchronised, include_unusual_predicate_types, initial_matches_fetched, search_text_for_current_cache, cached_results, under_construction_or_predicate ):
    
    next_search_is_probably_fast = False
    
    include_current = file_search_context.IncludeCurrentTags()
    include_pending = file_search_context.IncludePendingTags()
    
    file_service_key = file_search_context.GetFileServiceKey()
    tag_service_key = file_search_context.GetTagServiceKey()
    
    ( raw_entry, inclusive, wildcard_text, search_text, explicit_wildcard, cache_text, entry_predicate ) = parsed_search_text
    
    if search_text in ( '', ':', '*' ):
        
        # if the user inputs '-' or similar, let's go to an empty list
        if raw_entry == '':
            
            input_just_changed = search_text_for_current_cache is not None
            
            definitely_do_it = input_just_changed or not initial_matches_fetched
            
            db_not_going_to_hang_if_we_hit_it = not HG.client_controller.DBCurrentlyDoingJob()
            
            if definitely_do_it or db_not_going_to_hang_if_we_hit_it:
                
                if file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
                    
                    search_service_key = tag_service_key
                    
                else:
                    
                    search_service_key = file_service_key
                    
                
                search_text_for_current_cache = None
                
                cached_results = HG.client_controller.Read( 'file_system_predicates', search_service_key )
                
                matches = cached_results
                
            elif ( search_text_for_current_cache is None or search_text_for_current_cache == '' ) and cached_results is not None: # if repeating query but busy, use same
                
                matches = cached_results
                
            else:
                
                matches = []
                
            
        else:
            
            matches = []
            
        
    else:
        
        ( namespace, half_complete_subtag ) = HydrusTags.SplitTag( search_text )
        
        if half_complete_subtag == '':
            
            search_text_for_current_cache = None
            
            matches = [] # a query like 'namespace:'
            
        else:
            
            fetch_from_db = True
            
            if synchronised and qt_media_callable is not None:
                
                try:
                    
                    media = HG.client_controller.CallBlockingToQt( win, qt_media_callable )
                    
                except HydrusExceptions.QtDeadWindowException:
                    
                    return
                    
                
                if job_key.IsCancelled():
                    
                    return
                    
                
                media_available_and_good = media is not None and len( media ) > 0
                
                if media_available_and_good:
                    
                    fetch_from_db = False
                    
                
            
            if fetch_from_db:
                
                # if user searches 'blah', then we include 'blah (23)' for 'series:blah (10)', 'blah (13)'
                # if they search for 'series:blah', then we don't!
                add_namespaceless = ':' not in namespace
                
                small_exact_match_search = ShouldDoExactSearch( cache_text )
                
                if small_exact_match_search:
                    
                    predicates = HG.client_controller.Read( 'autocomplete_predicates', file_service_key = file_service_key, tag_service_key = tag_service_key, search_text = cache_text, exact_match = True, inclusive = inclusive, include_current = include_current, include_pending = include_pending, add_namespaceless = add_namespaceless, job_key = job_key, collapse_siblings = True )
                    
                else:
                    
                    cache_valid = CacheCanBeUsedForInput( search_text_for_current_cache, cache_text )
                    
                    if not cache_valid:
                        
                        new_search_text_for_current_cache = cache_text
                        
                        cached_results = HG.client_controller.Read( 'autocomplete_predicates', file_service_key = file_service_key, tag_service_key = tag_service_key, search_text = search_text, inclusive = inclusive, include_current = include_current, include_pending = include_pending, add_namespaceless = add_namespaceless, job_key = job_key, collapse_siblings = True )
                        
                    
                    predicates = cached_results
                    
                    next_search_is_probably_fast = True
                    
                
                if job_key.IsCancelled():
                    
                    return
                    
                
                matches = ClientSearch.FilterPredicatesBySearchText( tag_service_key, search_text, predicates )
                
            else:
                
                # it is possible that media will change between calls to this, so don't cache it
                # it's also quick as hell, so who cares
                
                tags_managers = []
                
                for m in media:
                    
                    if m.IsCollection():
                        
                        tags_managers.extend( m.GetSingletonsTagsManagers() )
                        
                    else:
                        
                        tags_managers.append( m.GetTagsManager() )
                        
                    
                
                if job_key.IsCancelled():
                    
                    return
                    
                
                current_tags_to_count = collections.Counter()
                pending_tags_to_count = collections.Counter()
                
                for group_of_tags_managers in HydrusData.SplitListIntoChunks( tags_managers, 1000 ):
                    
                    if include_current:
                        
                        current_tags_to_count.update( itertools.chain.from_iterable( tags_manager.GetCurrent( tag_service_key, ClientTags.TAG_DISPLAY_SIBLINGS_AND_PARENTS ) for tags_manager in group_of_tags_managers ) )
                        
                    
                    if include_pending:
                        
                        pending_tags_to_count.update( itertools.chain.from_iterable( [ tags_manager.GetPending( tag_service_key, ClientTags.TAG_DISPLAY_SIBLINGS_AND_PARENTS ) for tags_manager in group_of_tags_managers ] ) )
                        
                    
                    if job_key.IsCancelled():
                        
                        return
                        
                    
                
                tags_to_do = set()
                
                tags_to_do.update( current_tags_to_count.keys() )
                tags_to_do.update( pending_tags_to_count.keys() )
                
                tags_to_do = ClientSearch.FilterTagsBySearchText( tag_service_key, search_text, tags_to_do )
                
                if job_key.IsCancelled():
                    
                    return
                    
                
                predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag, inclusive, current_tags_to_count[ tag ], pending_tags_to_count[ tag ] ) for tag in tags_to_do ]
                
                if job_key.IsCancelled():
                    
                    return
                    
                
                if namespace == '':
                    
                    predicates = ClientData.MergePredicates( predicates, add_namespaceless = True )
                    
                
                next_search_is_probably_fast = True
                
                matches = predicates
                
            
            matches = ClientSearch.SortPredicates( matches )
            
        
        for match in matches:
            
            if match.GetInclusive() != inclusive:
                
                match.SetInclusive( inclusive )
                
            
        
    
    matches = InsertStaticPredicatesForRead( matches, parsed_search_text, include_unusual_predicate_types, under_construction_or_predicate )
    
    if job_key.IsCancelled():
        
        return
        
    
    HG.client_controller.CallLaterQtSafe(win, 0.0, results_callable, job_key, search_text, search_text_for_current_cache, cached_results, matches, next_search_is_probably_fast)
    
def PutAtTopOfMatches( matches, predicate ):
    
    try:
        
        index = matches.index( predicate )
        
        predicate = matches[ index ]
        
        matches.remove( predicate )
        
    except ValueError:
        
        pass
        
    
    matches.insert( 0, predicate )
    
def ShouldDoExactSearch( cache_text ):
    
    if cache_text is None:
        
        return False
        
    
    autocomplete_exact_match_threshold = HG.client_controller.new_options.GetNoneableInteger( 'autocomplete_exact_match_threshold' )
    
    if autocomplete_exact_match_threshold is None:
        
        return False
        
    
    if ':' in cache_text:
        
        ( namespace, test_text ) = HydrusTags.SplitTag( cache_text )
        
    else:
        
        test_text = cache_text
        
    
    return len( test_text ) <= autocomplete_exact_match_threshold
    
def WriteFetch( win, job_key, results_callable, parsed_search_text, file_service_key, tag_service_key, expand_parents, search_text_for_current_cache, cached_results ):
    
    next_search_is_probably_fast = False
    
    ( raw_entry, search_text, cache_text, entry_predicate, sibling_predicate ) = parsed_search_text
    
    if search_text in ( '', ':', '*' ):
        
        search_text_for_current_cache = None
        
        matches = []
        
    else:
        
        ( namespace, subtag ) = HydrusTags.SplitTag( search_text )
        
        if subtag == '':
            
            search_text_for_current_cache = None
            
            matches = [] # a query like 'namespace:'
            
        else:
            
            must_do_a_search = False
            
            small_exact_match_search = ShouldDoExactSearch( cache_text )
            
            if small_exact_match_search:
                
                predicates = HG.client_controller.Read( 'autocomplete_predicates', file_service_key = file_service_key, tag_service_key = tag_service_key, search_text = cache_text, exact_match = True, add_namespaceless = False, job_key = job_key, collapse_siblings = False )
                
            else:
                
                cache_valid = CacheCanBeUsedForInput( search_text_for_current_cache, cache_text )
                
                if must_do_a_search or not cache_valid:
                    
                    search_text_for_current_cache = cache_text
                    
                    cached_results = HG.client_controller.Read( 'autocomplete_predicates', file_service_key = file_service_key, tag_service_key = tag_service_key, search_text = search_text, add_namespaceless = False, job_key = job_key, collapse_siblings = False )
                    
                
                predicates = cached_results
                
                next_search_is_probably_fast = True
                
            
            matches = ClientSearch.FilterPredicatesBySearchText( tag_service_key, search_text, predicates )
            
            matches = ClientSearch.SortPredicates( matches )
            
        
    
    matches = InsertStaticPredicatesForWrite( matches, parsed_search_text, tag_service_key, expand_parents )
    
    HG.client_controller.CallLaterQtSafe(win, 0.0, results_callable, job_key, search_text, search_text_for_current_cache, cached_results, matches, next_search_is_probably_fast)
    
class WindowActivationACDropdownEventFilter( QC.QObject ):
    
    def __init__( self, parent ):
        
        QC.QObject.__init__( self, parent )
        
    
    def eventFilter( self, watched, event ):
        
        if event.type() in ( QC.QEvent.WindowActivate, QC.QEvent.WindowDeactivate ):
            
            self.parent().DoDropdownHideShow()
            
        
        return False
        
    
# much of this is based on the excellent TexCtrlAutoComplete class by Edward Flick, Michele Petrazzo and Will Sadkin, just with plenty of simplification and integration into hydrus
class AutoCompleteDropdown( QW.QWidget ):
    
    selectUp = QC.Signal()
    selectDown = QC.Signal()
    showNext = QC.Signal()
    showPrevious = QC.Signal()
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        self._intercept_key_events = True
        
        if self.window() == HG.client_controller.gui:
            
            use_float_mode = HG.client_controller.new_options.GetBoolean( 'autocomplete_float_main_gui' )
            
        else:
            
            use_float_mode = HG.client_controller.new_options.GetBoolean( 'autocomplete_float_frames' )
            
        
        self._float_mode = use_float_mode
        
        self._text_ctrl = QW.QLineEdit( self )
        
        self._UpdateBackgroundColour()
        
        self._last_attempted_dropdown_width = 0
        self._last_attempted_dropdown_position = ( None, None )
        
        self._last_move_event_started = 0.0
        self._last_move_event_occurred = 0.0
        
        self._text_ctrl_widget_event_filter = QP.WidgetEventFilter( self._text_ctrl )
        
        if self._float_mode:
            
            self._text_ctrl_widget_event_filter.EVT_SET_FOCUS( self.EventSetFocus )
            self._text_ctrl_widget_event_filter.EVT_KILL_FOCUS( self.EventKillFocus )
            
        
        self._text_ctrl.textChanged.connect( self.EventText )
        
        self._text_ctrl_widget_event_filter.EVT_KEY_DOWN( self.keyPressFilter )
        
        self._text_ctrl_widget_event_filter.EVT_MOUSEWHEEL( self.EventMouseWheel )
        
        vbox = QP.VBoxLayout( margin = 0 )
        
        self._text_input_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( self._text_input_hbox, self._text_ctrl, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        
        QP.AddToLayout( vbox, self._text_input_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if self._float_mode:
            
            self._dropdown_window = QW.QFrame( self )
            
            self._dropdown_window.setWindowFlags( QC.Qt.Tool | QC.Qt.FramelessWindowHint )
            
            self._dropdown_window.setAttribute( QC.Qt.WA_ShowWithoutActivating )
            
            self._dropdown_window.setFrameStyle( QW.QFrame.Panel | QW.QFrame.Raised )
            self._dropdown_window.setLineWidth( 2 )
            
            self._dropdown_window.move( ClientGUIFunctions.ClientToScreen( self._text_ctrl, ( 0, 0 ) ) )
            
            self._dropdown_window_widget_event_filter = QP.WidgetEventFilter( self._dropdown_window )
            self._dropdown_window_widget_event_filter.EVT_CLOSE( self.EventCloseDropdown )
            
            self._dropdown_hidden = True
            
            self._window_activation_ac_dropdown_event_filter = WindowActivationACDropdownEventFilter( self )
            
            self._dropdown_window.installEventFilter( self._window_activation_ac_dropdown_event_filter )
            
        else:
            
            self._dropdown_window = QW.QFrame( self )
            
            self._dropdown_window.setFrameShape( QW.QFrame.NoFrame )
            #self._dropdown_window.setFrameStyle( QW.QFrame.Box | QW.QFrame.Raised )
            
        
        self._dropdown_notebook = QW.QTabWidget( self._dropdown_window )
        
        #
        
        self._list_height_num_chars = 8
        
        self._search_results_list = self._InitSearchResultsList()
        
        self._dropdown_notebook.setCurrentIndex( self._dropdown_notebook.addTab( self._search_results_list, 'results' ) )
        
        #
        
        if not self._float_mode:
            
            QP.AddToLayout( vbox, self._dropdown_window, CC.FLAGS_EXPAND_BOTH_WAYS )
            
        
        self.setLayout( vbox )
        
        self._current_list_raw_entry = ''
        self._next_search_is_probably_fast = False
        
        self._search_text_for_current_cache = None
        self._cached_results = []
        
        self._current_fetch_job_key = None
        
        self._initial_matches_fetched = False
        
        self._move_hide_job = None
        self._refresh_list_job = None
        
        if self._float_mode:
            
            self._widget_event_filter = QP.WidgetEventFilter( self )
            self._widget_event_filter.EVT_MOVE( self.EventMove )
            self._widget_event_filter.EVT_SIZE( self.EventMove )
            
            HG.client_controller.sub( self, '_ParentMovedOrResized', 'top_level_window_move_event' )
            
            parent = self
            
            self._scroll_event_filters = []
            
            while True:
                
                try:
                    
                    parent = parent.parentWidget()
                    
                    if isinstance( parent, QW.QScrollArea ):
                        
                        scroll_event_filter = QP.WidgetEventFilter( parent )
                        
                        self._scroll_event_filters.append( scroll_event_filter )
                        
                        scroll_event_filter.EVT_SCROLLWIN( self.EventMove )
                        
                    
                except:
                    
                    break
                    
                
            
        
        HG.client_controller.sub( self, '_UpdateBackgroundColour', 'notify_new_colourset' )
        HG.client_controller.sub( self, 'DoDropdownHideShow', 'notify_page_change' )
        
        self._ScheduleListRefresh( 0.0 )
        
    
    def _BroadcastChoices( self, predicates, shift_down ):
        
        raise NotImplementedError()
        
    
    def _BroadcastCurrentText( self, shift_down ):
        
        raise NotImplementedError()
        
    
    def _CancelCurrentResultsFetchJob( self ):
        
        if self._current_fetch_job_key is not None:
            
            self._current_fetch_job_key.Cancel()
            
            self._current_fetch_job_key = None
            
        
    
    def _CancelScheduledListRefresh( self ):
        
        if self._refresh_list_job is not None:
            
            self._refresh_list_job.Cancel()
            
        
    
    def _ClearInput( self ):
        
        self._CancelCurrentResultsFetchJob()
        
        self._text_ctrl.setText( '' )
        
        self._SetResultsToList( [] )
        
        self._ScheduleListRefresh( 0.0 )
        
    
    def _DropdownHideShow( self ):
        
        if not self._float_mode:
            
            return
            
        
        try:
            
            if self._ShouldShow():
                
                self._ShowDropdown()
                
                if self._move_hide_job is not None:
                    
                    self._move_hide_job.Cancel()
                    
                    self._move_hide_job = None
                    
                
            else:
                
                self._HideDropdown()
                
            
        except:
            
            if self._move_hide_job is not None:
                
                self._move_hide_job.Cancel()
                
                self._move_hide_job = None
                
            
            raise
            
        
    
    def _HandleEscape( self ):
        
        if self._float_mode:
            
            self.parentWidget().setFocus( QC.Qt.OtherFocusReason )
            
            return True
            
        else:
            
            return False
            
        
    
    def _HideDropdown( self ):
        
        if not self._dropdown_hidden:
            
            self._dropdown_window.hide()
            
            self._dropdown_hidden = True
            
        
    
    def _InitSearchResultsList( self ):
        
        raise NotImplementedError()
        
    
    def _ParentMovedOrResized( self ):
        
        if self._float_mode:
            
            if HydrusData.TimeHasPassedFloat( self._last_move_event_occurred + 1.0 ):
                
                self._last_move_event_started = HydrusData.GetNowFloat()
                
            
            self._last_move_event_occurred = HydrusData.GetNowFloat()
            
            # we'll do smoother move updates for a little bit to stop flickeryness, but after that we'll just hide
            
            NICE_ANIMATION_GRACE_PERIOD = 0.25
            
            time_to_delay_these_calls = HydrusData.TimeHasPassedFloat( self._last_move_event_started + NICE_ANIMATION_GRACE_PERIOD )
            
            if time_to_delay_these_calls:
                
                self._HideDropdown()
                
                if self._ShouldShow():
                    
                    if self._move_hide_job is None:
                        
                        self._move_hide_job = HG.client_controller.CallRepeatingQtSafe( self._dropdown_window, 0.0, 0.25, self._DropdownHideShow )
                        
                    
                    self._move_hide_job.Delay( 0.25 )
                    
                
            else:
                
                self._DropdownHideShow()
                
            
        
    
    def _ScheduleListRefresh( self, delay ):
        
        if self._refresh_list_job is not None and delay == 0.0:
            
            self._refresh_list_job.Wake()
            
        else:
            
            self._CancelScheduledListRefresh()
            
            self._refresh_list_job = HG.client_controller.CallLaterQtSafe(self, delay, self._UpdateSearchResultsList)
            
        
    
    def _SetListDirty( self ):
        
        self._search_text_for_current_cache = None
        
        self._ScheduleListRefresh( 0.0 )
        
    
    def _SetResultsToList( self, results ):
        
        raise NotImplementedError()
        
    
    def _ShouldShow( self ):
        
        i_am_active_and_focused = self.window().isActiveWindow() and self._text_ctrl.hasFocus()
        
        dropdown_is_active = self._dropdown_window.isActiveWindow()
        
        focus_or_active_good = i_am_active_and_focused or dropdown_is_active
        
        visible = self.isVisible()
        
        return focus_or_active_good and visible
        
    
    def _ShouldTakeResponsibilityForEnter( self ):
        
        raise NotImplementedError()
        
    
    def _ShowDropdown( self ):
        
        ( text_width, text_height ) = self._text_ctrl.size().toTuple()
        
        if self._text_ctrl.isVisible():
            
            desired_dropdown_position = ClientGUIFunctions.ClientToScreen( self._text_ctrl, ( 0, text_height ) )
            
            if self._last_attempted_dropdown_position != desired_dropdown_position:
                
                self._dropdown_window.move( desired_dropdown_position )
                
                self._last_attempted_dropdown_position = desired_dropdown_position
                
            
        
        #
        
        if self._dropdown_hidden:
            
            self._dropdown_window.show()
            
            self._dropdown_hidden = False
            
        
        if text_width != self._last_attempted_dropdown_width:
            
            self._dropdown_window.setFixedWidth( text_width )
            
            self._last_attempted_dropdown_width = text_width
            
        
    
    def _StartResultsFetchJob( self, job_key ):
        
        raise NotImplementedError()
        
    
    def _TakeResponsibilityForEnter( self, shift_down ):
        
        raise NotImplementedError()
        
    
    def _UpdateBackgroundColour( self ):
        
        colour = HG.client_controller.new_options.GetColour( CC.COLOUR_AUTOCOMPLETE_BACKGROUND )
        
        if not self._intercept_key_events:
            
            colour = ClientData.GetLighterDarkerColour( colour )
            
        
        QP.SetBackgroundColour( self._text_ctrl, colour )
        
        self._text_ctrl.update()
        
    
    def _UpdateSearchResultsList( self ):
        
        self._refresh_list_job = None
        
        self._CancelCurrentResultsFetchJob()
        
        self._current_fetch_job_key = ClientThreading.JobKey( cancellable = True )
        
        self._StartResultsFetchJob( self._current_fetch_job_key )
        
    
    def BroadcastChoices( self, predicates, shift_down = False ):
        
        self._BroadcastChoices( predicates, shift_down )
        
    
    def CancelCurrentResultsFetchJob( self ):
        
        self._CancelCurrentResultsFetchJob()
        
    
    def DoDropdownHideShow( self ):
        
        self._DropdownHideShow()
        
    
    def keyPressFilter( self, event ):
        
        HG.client_controller.ResetIdleTimer()
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        raw_control_modifier = QC.Qt.ControlModifier
        
        if HC.PLATFORM_MACOS:
            
            raw_control_modifier = QC.Qt.MetaModifier # This way raw_control_modifier always means the Control key, even on Mac. See Qt docs.
            
        
        if key in ( QC.Qt.Key_Insert, ):
            
            self._intercept_key_events = not self._intercept_key_events
            
            self._UpdateBackgroundColour()
            
        elif key == QC.Qt.Key_Space and event.modifiers() & raw_control_modifier:
            
            self._ScheduleListRefresh( 0.0 )
            
        elif self._intercept_key_events:
            
            send_input_to_current_list = False
            
            current_results_list = self._dropdown_notebook.currentWidget()
            
            current_list_is_empty = len( current_results_list ) == 0
            
            input_is_empty = self._text_ctrl.text() == ''
            
            if key in ( ord( 'A' ), ord( 'a' ) ) and modifier == QC.Qt.ControlModifier:
                
                return True # was: event.ignore()
                
            elif key in ( QC.Qt.Key_Return, QC.Qt.Key_Enter ) and self._ShouldTakeResponsibilityForEnter():
                
                shift_down = modifier == QC.Qt.ShiftModifier
                
                self._TakeResponsibilityForEnter( shift_down )
                
            elif input_is_empty: # maybe we should be sending a 'move' event to a different place
                
                if key in ( QC.Qt.Key_Up, QC.Qt.Key_Down ) and current_list_is_empty:
                    
                    if key in ( QC.Qt.Key_Up, ):
                        
                        self.selectUp.emit()
                        
                    elif key in ( QC.Qt.Key_Down, ):
                        
                        self.selectDown.emit()
                        
                    
                elif key in ( QC.Qt.Key_PageDown, QC.Qt.Key_PageUp ) and current_list_is_empty:
                    
                    if key in ( QC.Qt.Key_PageUp, ):
                        
                        self.showPrevious.emit()
                        
                    elif key in ( QC.Qt.Key_PageDown, ):
                        
                        self.showNext.emit()
                        
                    
                elif key in ( QC.Qt.Key_Right, QC.Qt.Key_Left ):
                    
                    if key in ( QC.Qt.Key_Left, ):
                        
                        direction = -1
                        
                    elif key in ( QC.Qt.Key_Right, ):
                        
                        direction = 1
                        
                    
                    self.MoveNotebookPageFocus( direction = direction )
                    
                elif key == QC.Qt.Key_Escape:
                    
                    escape_caught = self._HandleEscape()
                    
                    if not escape_caught:
                        
                        send_input_to_current_list = True
                        
                    
                else:
                    
                    send_input_to_current_list = True
                    
                
            else:
                
                send_input_to_current_list = True
                
            
            if send_input_to_current_list:
                
                current_results_list.keyPressEvent( event ) # ultimately, this typically ignores the event, letting the text ctrl take it
                
                return not event.isAccepted()
                
            
        else:
            
            return True # was: event.ignore()
            
        
    
    def EventCloseDropdown( self, event ):
        
        HG.client_controller.gui.close()
        
        return True
        
    
    def EventKillFocus( self, event ):
        
        if self._float_mode:
            
            self._DropdownHideShow()
            
        
        return True # was: event.ignore()
        
    
    def EventMouseWheel( self, event ):
        
        current_results_list = self._dropdown_notebook.currentWidget()
        
        if self._text_ctrl.text() == '' and len( current_results_list ) == 0:
            
            if event.angleDelta().y() > 0:
                
                self.selectUp.emit()
                
            else:
                
                self.selectDown.emit()
                
            
            event.accept()
            
        else:
            
            if event.modifiers() & QC.Qt.ControlModifier:
                
                if event.angleDelta().y() > 0:
                    
                    current_results_list.MoveSelectionUp()
                    
                else:
                    
                    current_results_list.MoveSelectionDown()
                    
                
                event.accept()
                
            else:
                
                event.ignore()
                
            
        
        return True
        
    
    def EventMove( self, event ):
        
        self._ParentMovedOrResized()
        
        return True # was: event.ignore()
        
    
    def EventSetFocus( self, event ):
        
        if self._float_mode:
            
            self._DropdownHideShow()
            
        
        return True # was: event.ignore()
        
    
    def EventText( self, new_text ):
        
        num_chars = len( self._text_ctrl.text() )
        
        if num_chars == 0:
            
            self._ScheduleListRefresh( 0.0 )
            
        else:
            
            if HG.client_controller.new_options.GetBoolean( 'autocomplete_results_fetch_automatically' ):
                
                self._ScheduleListRefresh( 0.0 )
                
            
            if self._dropdown_notebook.currentWidget() != self._search_results_list:
                
                self.MoveNotebookPageFocus( index = 0 )
                
            
        
    
    def ForceSizeCalcNow( self ):
        
        if self._float_mode:
            
            self._DropdownHideShow()
            
        
    
    def MoveNotebookPageFocus( self, index = None, direction = None ):
        
        new_index = None
        
        if index is not None:
            
            new_index = index
            
        elif direction is not None:
            
            current_index = self._dropdown_notebook.currentIndex()
            
            if current_index is not None and current_index != -1:
                
                number_of_pages = self._dropdown_notebook.count()
                
                new_index = ( current_index + direction ) % number_of_pages # does wraparound
                
            
        
        if new_index is not None:
            
            self._dropdown_notebook.setCurrentIndex( new_index )
            
            self._text_ctrl.setFocus( QC.Qt.OtherFocusReason )
            
        
    
    def SetFetchedResults( self, job_key, search_text, search_text_for_cache, cached_results, results ):
        
        if self._current_fetch_job_key is not None and self._current_fetch_job_key.GetKey() == job_key.GetKey():
            
            self._CancelCurrentResultsFetchJob()
            
            self._search_text_for_current_cache = search_text_for_cache
            self._cached_results = cached_results
            
            self._initial_matches_fetched = True
            
            self._SetResultsToList( results )
            
        
    
    def setFocus( self, focus_reason = QC.Qt.OtherFocusReason ):
        
        if HC.PLATFORM_MACOS:
            
            QP.CallAfter( self._text_ctrl.setFocus, focus_reason )
            
        else:
            
            self._text_ctrl.setFocus( focus_reason )
            
        
    
class AutoCompleteDropdownTags( AutoCompleteDropdown ):
    
    def __init__( self, parent, file_service_key, tag_service_key ):
        
        self._file_service_key = file_service_key
        self._tag_service_key = tag_service_key
        
        AutoCompleteDropdown.__init__( self, parent )
        
        self._allow_all_known_files = True
        
        file_service = HG.client_controller.services_manager.GetService( self._file_service_key )
        
        tag_service = HG.client_controller.services_manager.GetService( self._tag_service_key )
        
        self._file_repo_button = ClientGUICommon.BetterButton( self._dropdown_window, file_service.GetName(), self.FileButtonHit )
        self._file_repo_button.setMinimumWidth( 20 )
        
        self._tag_repo_button = ClientGUICommon.BetterButton( self._dropdown_window, tag_service.GetName(), self.TagButtonHit )
        self._tag_repo_button.setMinimumWidth( 20 )
        
        self._favourites_list = self._InitFavouritesList()
        
        self.RefreshFavouriteTags()
        
        self._dropdown_notebook.addTab( self._favourites_list, 'favourites' )
        
        #
        
        HG.client_controller.sub( self, 'RefreshFavouriteTags', 'notify_new_favourite_tags' )
        
    
    def _ChangeFileService( self, file_service_key ):
        
        if file_service_key == CC.COMBINED_FILE_SERVICE_KEY and self._tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            local_tag_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) )
            
            self._ChangeTagService( local_tag_services[0].GetServiceKey() )
            
        
        self._file_service_key = file_service_key
        
        file_service = HG.client_controller.services_manager.GetService( self._file_service_key )
        
        name = file_service.GetName()
        
        self._file_repo_button.setText( name )
        
        self._SetListDirty()
        
    
    def _ChangeTagService( self, tag_service_key ):
        
        if tag_service_key == CC.COMBINED_TAG_SERVICE_KEY and self._file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
            
            self._ChangeFileService( CC.LOCAL_FILE_SERVICE_KEY )
            
        
        self._tag_service_key = tag_service_key
        
        self._search_results_list.SetTagService( self._tag_service_key )
        
        tag_service = tag_service = HG.client_controller.services_manager.GetService( self._tag_service_key )
        
        name = tag_service.GetName()
        
        self._tag_repo_button.setText( name )
        
        self._search_text_for_current_cache = None
        
        self._SetListDirty()
        
    
    def _InitFavouritesList( self ):
        
        raise NotImplementedError()
        
    
    def _SetResultsToList( self, results ):
        
        self._current_list_raw_entry = self._text_ctrl.text()
        
        self._search_results_list.SetPredicates( results )
        
    
    def FileButtonHit( self ):
        
        services_manager = HG.client_controller.services_manager
        
        services = []
        
        services.append( services_manager.GetService( CC.LOCAL_FILE_SERVICE_KEY ) )
        services.append( services_manager.GetService( CC.TRASH_SERVICE_KEY ) )
        
        if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            services.append( services_manager.GetService( CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
            
        
        services.extend( services_manager.GetServices( ( HC.FILE_REPOSITORY, ) ) )
        
        advanced_mode = HG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
        if advanced_mode and self._allow_all_known_files:
            
            services.append( services_manager.GetService( CC.COMBINED_FILE_SERVICE_KEY ) )
            
        
        menu = QW.QMenu()
        
        for service in services:
            
            ClientGUIMenus.AppendMenuItem( menu, service.GetName(), 'Change the current file domain to ' + service.GetName() + '.', self._ChangeFileService, service.GetServiceKey() )
            
        
        HG.client_controller.PopupMenu( self._file_repo_button, menu )
        
    
    def RefreshFavouriteTags( self ):
        
        favourite_tags = list( HG.client_controller.new_options.GetStringList( 'favourite_tags' ) )
        
        favourite_tags.sort()
        
        predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag ) for tag in favourite_tags ]
        
        self._favourites_list.SetPredicates( predicates )
        
    
    def SetFileService( self, file_service_key ):
        
        self._ChangeFileService( file_service_key )
        
    
    def SetStubPredicates( self, job_key, stub_predicates ):
        
        if self._current_fetch_job_key is not None and self._current_fetch_job_key.GetKey() == job_key.GetKey():
            
            self._SetResultsToList( stub_predicates )
            
        
    
    def SetTagService( self, tag_service_key ):
        
        self._ChangeTagService( tag_service_key )
        
    
    def TagButtonHit( self ):
        
        services_manager = HG.client_controller.services_manager
        
        services = []
        
        services.extend( services_manager.GetServices( ( HC.LOCAL_TAG, ) ) )
        services.extend( services_manager.GetServices( ( HC.TAG_REPOSITORY, ) ) )
        services.append( services_manager.GetService( CC.COMBINED_TAG_SERVICE_KEY ) )
        
        menu = QW.QMenu()
        
        for service in services:
            
            ClientGUIMenus.AppendMenuItem( menu, service.GetName(), 'Change the current tag domain to ' + service.GetName() + '.', self._ChangeTagService, service.GetServiceKey() )
            
        
        HG.client_controller.PopupMenu( self._tag_repo_button, menu )
        
    
class AutoCompleteDropdownTagsRead( AutoCompleteDropdownTags ):
    
    def __init__( self, parent, page_key, file_search_context, media_callable = None, synchronised = True, include_unusual_predicate_types = True, allow_all_known_files = True ):
        
        file_service_key = file_search_context.GetFileServiceKey()
        tag_service_key = file_search_context.GetTagServiceKey()
        
        AutoCompleteDropdownTags.__init__( self, parent, file_service_key, tag_service_key )
        
        self._allow_all_known_files = allow_all_known_files
        
        self._media_callable = media_callable
        self._page_key = page_key
        
        self._under_construction_or_predicate = None
        
        self._file_search_context = file_search_context
        
        self._include_current_tags = ClientGUICommon.OnOffButton( self._dropdown_window, self._page_key, 'notify_include_current', on_label = 'include current tags', off_label = 'exclude current tags', start_on = file_search_context.IncludeCurrentTags() )
        self._include_current_tags.setToolTip( 'select whether to include current tags in the search' )
        self._include_pending_tags = ClientGUICommon.OnOffButton( self._dropdown_window, self._page_key, 'notify_include_pending', on_label = 'include pending tags', off_label = 'exclude pending tags', start_on = file_search_context.IncludePendingTags() )
        self._include_pending_tags.setToolTip( 'select whether to include pending tags in the search' )
        
        self._synchronised = ClientGUICommon.OnOffButton( self._dropdown_window, self._page_key, 'notify_search_immediately', on_label = 'searching immediately', off_label = 'waiting -- tag counts may be inaccurate', start_on = synchronised )
        self._synchronised.setToolTip( 'select whether to renew the search as soon as a new predicate is entered' )
        
        self._or_advanced = ClientGUICommon.BetterButton( self._dropdown_window, 'OR', self._AdvancedORInput )
        self._or_advanced.setToolTip( 'Advanced OR Search input.' )
        
        if not HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            self._or_advanced.hide()
            
        
        self._or_cancel = ClientGUICommon.BetterBitmapButton( self._dropdown_window, CC.GlobalPixmaps.delete, self._CancelORConstruction )
        self._or_cancel.setToolTip( 'Cancel OR Predicate construction.' )
        self._or_cancel.hide()
        
        self._or_rewind = ClientGUICommon.BetterBitmapButton( self._dropdown_window, CC.GlobalPixmaps.previous, self._RewindORConstruction )
        self._or_rewind.setToolTip( 'Rewind OR Predicate construction.' )
        self._or_rewind.hide()
        
        self._include_unusual_predicate_types = include_unusual_predicate_types
        
        button_hbox_1 = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox_1, self._include_current_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox_1, self._include_pending_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        sync_button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( sync_button_hbox, self._synchronised, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( sync_button_hbox, self._or_advanced, CC.FLAGS_VCENTER )
        QP.AddToLayout( sync_button_hbox, self._or_cancel, CC.FLAGS_VCENTER )
        QP.AddToLayout( sync_button_hbox, self._or_rewind, CC.FLAGS_VCENTER )
        
        button_hbox_2 = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox_2, self._file_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox_2, self._tag_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, button_hbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, sync_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, button_hbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._dropdown_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.setLayout( vbox )
        
        HG.client_controller.sub( self, 'SetSynchronisedWait', 'synchronised_wait_switch' )
        
        HG.client_controller.sub( self, 'IncludeCurrent', 'notify_include_current' )
        HG.client_controller.sub( self, 'IncludePending', 'notify_include_pending' )
        
    
    def _AdvancedORInput( self ):
        
        title = 'enter advanced OR predicates'
        
        with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
            
            panel = EditAdvancedORPredicates( dlg )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                predicates = panel.GetValue()
                shift_down = False
                
                if len( predicates ) > 0:
                    
                    self._BroadcastChoices( predicates, shift_down )
                    
                
            
        
    
    def _BroadcastChoices( self, predicates, shift_down ):
        
        or_pred_in_broadcast = self._under_construction_or_predicate is not None and self._under_construction_or_predicate in predicates
        
        if shift_down:
            
            if self._under_construction_or_predicate is None:
                
                self._under_construction_or_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_OR_CONTAINER, predicates )
                
            else:
                
                if or_pred_in_broadcast:
                    
                    predicates.remove( self._under_construction_or_predicate )
                    
                
                or_preds = list( self._under_construction_or_predicate.GetValue() )
                
                or_preds.extend( [ predicate for predicate in predicates if predicate not in or_preds ] )
                
                self._under_construction_or_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_OR_CONTAINER, or_preds )
                
            
        else:
            
            if self._under_construction_or_predicate is not None and not or_pred_in_broadcast:
                
                or_preds = list( self._under_construction_or_predicate.GetValue() )
                
                or_preds.extend( [ predicate for predicate in predicates if predicate not in or_preds ] )
                
                predicates = { ClientSearch.Predicate( HC.PREDICATE_TYPE_OR_CONTAINER, or_preds ) }
                
            
            if or_pred_in_broadcast:
                
                or_preds = list( self._under_construction_or_predicate.GetValue() )
                
                if len( or_preds ) == 1:
                    
                    predicates.remove( self._under_construction_or_predicate )
                    
                    predicates.extend( or_preds )
                    
                
            
            self._under_construction_or_predicate = None
            
            HG.client_controller.pub( 'enter_predicates', self._page_key, predicates )
            
        
        self._UpdateORButtons()
        
        self._ClearInput()
        
    
    def _BroadcastCurrentText( self, shift_down ):
        
        ( raw_entry, inclusive, wildcard_text, search_text, explicit_wildcard, cache_text, entry_predicate ) = self._ParseSearchText()
        
        ( namespace, subtag ) = HydrusTags.SplitTag( search_text )
        
        if namespace != '' and subtag in ( '', '*' ):
            
            entry_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_NAMESPACE, namespace, inclusive )
            
        else:
            
            try:
                
                HydrusTags.CheckTagNotEmpty( search_text )
                
            except HydrusExceptions.SizeException:
                
                return
                
            
        
        self._BroadcastChoices( { entry_predicate }, shift_down )
        
    
    def _CancelORConstruction( self ):
        
        self._under_construction_or_predicate = None
        
        self._UpdateORButtons()
        
        self._ClearInput()
        
    
    def _ChangeFileService( self, file_service_key ):
        
        AutoCompleteDropdownTags._ChangeFileService( self, file_service_key )
        
        self._file_search_context.SetFileServiceKey( file_service_key )
        
        HG.client_controller.pub( 'change_file_service', self._page_key, file_service_key )
        
        HG.client_controller.pub( 'refresh_query', self._page_key )
        
    
    def _ChangeTagService( self, tag_service_key ):
        
        AutoCompleteDropdownTags._ChangeTagService( self, tag_service_key )
        
        self._file_search_context.SetTagServiceKey( tag_service_key )
        
        HG.client_controller.pub( 'change_tag_service', self._page_key, tag_service_key )
        
        HG.client_controller.pub( 'refresh_query', self._page_key )
        
    
    def _HandleEscape( self ):
        
        if self._under_construction_or_predicate is not None and self._text_ctrl.text() == '':
            
            self._CancelORConstruction()
            
            return True
            
        else:
            
            return AutoCompleteDropdown._HandleEscape( self )
            
        
    
    def _InitFavouritesList( self ):
        
        favs_list = ClientGUIListBoxes.ListBoxTagsACRead( self._dropdown_notebook, self.BroadcastChoices, self._tag_service_key, height_num_chars = self._list_height_num_chars )
        
        return favs_list
        
    
    def _InitSearchResultsList( self ):
        
        if self._float_mode:
            
            self._list_height_num_chars = 19
            
        else:
            
            self._list_height_num_chars = 8
            
        
        return ClientGUIListBoxes.ListBoxTagsACRead( self._dropdown_notebook, self.BroadcastChoices, self._tag_service_key, height_num_chars = self._list_height_num_chars )
        
    
    def _ParseSearchText( self ):
        
        raw_entry = self._text_ctrl.text()
        
        if raw_entry.startswith( '-' ):
            
            inclusive = False
            
            entry_text = raw_entry[1:]
            
        else:
            
            inclusive = True
            
            entry_text = raw_entry
            
        
        explicit_wildcard = '*' in entry_text
        
        ( wildcard_text, search_text ) = ClientSearch.ConvertEntryTextToSearchText( entry_text )
        
        if explicit_wildcard:
            
            cache_text = None
            
            entry_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_WILDCARD, search_text, inclusive )
            
        else:
            
            tag = HydrusTags.CleanTag( entry_text )
            
            cache_text = search_text[:-1] # take off the trailing '*' for the cache text
            
            siblings_manager = HG.client_controller.tag_siblings_manager
            
            sibling = siblings_manager.GetSibling( self._tag_service_key, tag )
            
            if sibling is None:
                
                entry_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag, inclusive )
                
            else:
                
                entry_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, sibling, inclusive )
                
            
        
        return ( raw_entry, inclusive, wildcard_text, search_text, explicit_wildcard, cache_text, entry_predicate )
        
    
    def _RewindORConstruction( self ):
        
        if self._under_construction_or_predicate is not None:
            
            or_preds = self._under_construction_or_predicate.GetValue()
            
            if len( or_preds ) <= 1:
                
                self._CancelORConstruction()
                
                return
                
            
            or_preds = or_preds[:-1]
            
            self._under_construction_or_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_OR_CONTAINER, or_preds )
            
        
        self._UpdateORButtons()
        
        self._ClearInput()
        
    
    def _StartResultsFetchJob( self, job_key ):
        
        parsed_search_text = self._ParseSearchText()
        
        stub_predicates = []
        
        stub_predicates = InsertStaticPredicatesForRead( stub_predicates, parsed_search_text, self._include_unusual_predicate_types, self._under_construction_or_predicate )
        
        AppendLoadingPredicate( stub_predicates )
        
        HG.client_controller.CallLaterQtSafe(self, 0.2, self.SetStubPredicates, job_key, stub_predicates)
        
        HG.client_controller.CallToThread( ReadFetch, self, job_key, self.SetFetchedResults, parsed_search_text, self._media_callable, self._file_search_context, self._synchronised.IsOn(), self._include_unusual_predicate_types, self._initial_matches_fetched, self._search_text_for_current_cache, self._cached_results, self._under_construction_or_predicate )
        
    
    def _ShouldTakeResponsibilityForEnter( self ):
        
        ( raw_entry, inclusive, wildcard_text, search_text, explicit_wildcard, cache_text, entry_predicate ) = self._ParseSearchText()
        
        looking_at_search_results = self._dropdown_notebook.currentWidget() == self._search_results_list
        
        something_to_broadcast = cache_text != ''
        
        # the list has results, but they are out of sync with what we have currently entered
        # when the user has quickly typed something in and the results are not yet in
        results_desynced_with_text = raw_entry != self._current_list_raw_entry
        
        p1 = looking_at_search_results and something_to_broadcast and results_desynced_with_text
        
        return p1
        
    
    def _TakeResponsibilityForEnter( self, shift_down ):
        
        self._BroadcastCurrentText( shift_down )
        
    
    def _UpdateORButtons( self ):
        
        if self._under_construction_or_predicate is None:
            
            if self._or_cancel.isVisible():
                
                self._or_cancel.hide()
                
            
            if self._or_rewind.isVisible():
                
                self._or_rewind.hide()
                
            
        else:
            
            or_preds = self._under_construction_or_predicate.GetValue()
            
            if len( or_preds ) > 1:
                
                if not self._or_rewind.isVisible():
                    
                    self._or_rewind.show()
                    
                
            else:
                
                if self._or_rewind.isVisible():
                    
                    self._or_rewind.hide()
                    
                
            
            if not self._or_cancel.isVisible():
                
                self._or_cancel.show()
            
        
    
    def GetFileSearchContext( self ):
        
        return self._file_search_context
        
    
    def IncludeCurrent( self, page_key, value ):
        
        if page_key == self._page_key:
            
            self._file_search_context.SetIncludeCurrentTags( value )
            
            self._SetListDirty()
            
            HG.client_controller.pub( 'refresh_query', self._page_key )
            
        
    
    def IncludePending( self, page_key, value ):
        
        if page_key == self._page_key:
            
            self._file_search_context.SetIncludePendingTags( value )
            
            self._SetListDirty()
            
            HG.client_controller.pub( 'refresh_query', self._page_key )
            
        
    
    def IsSynchronised( self ):
        
        return self._synchronised.IsOn()
        
    
    def SetFetchedResults( self, job_key, search_text, search_text_for_cache, cached_results, results, next_search_is_probably_fast ):
        
        if self._current_fetch_job_key is not None and self._current_fetch_job_key.GetKey() == job_key.GetKey():
            
            AutoCompleteDropdownTags.SetFetchedResults( self, job_key, search_text, search_text_for_cache, cached_results, results )
            
            self._next_search_is_probably_fast = next_search_is_probably_fast
            
            num_chars = len( self._text_ctrl.text() )
            
            if num_chars == 0:
                
                # refresh system preds after five mins
                
                self._ScheduleListRefresh( 300 )
                
            
        
    
    def SetSynchronisedWait( self, page_key ):
        
        if page_key == self._page_key:
            
            self._synchronised.EventButton()
            
        
    
class AutoCompleteDropdownTagsWrite( AutoCompleteDropdownTags ):
    
    def __init__( self, parent, chosen_tag_callable, expand_parents, file_service_key, tag_service_key, null_entry_callable = None, tag_service_key_changed_callable = None, show_paste_button = False ):
        
        self._chosen_tag_callable = chosen_tag_callable
        self._expand_parents = expand_parents
        self._null_entry_callable = null_entry_callable
        self._tag_service_key_changed_callable = tag_service_key_changed_callable
        
        service = HG.client_controller.services_manager.GetService( tag_service_key )
        
        if service.GetServiceType() == HC.LOCAL_TAG:
            
            file_service_key = CC.LOCAL_FILE_SERVICE_KEY
            
        elif tag_service_key != CC.COMBINED_TAG_SERVICE_KEY and HC.options[ 'show_all_tags_in_autocomplete' ]:
            
            file_service_key = CC.COMBINED_FILE_SERVICE_KEY
            
        
        AutoCompleteDropdownTags.__init__( self, parent, file_service_key, tag_service_key )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalPixmaps.paste, self._Paste )
        self._paste_button.setToolTip( 'Paste from the clipboard and quick-enter as if you had typed. This can take multiple newline-separated tags.' )
        
        if not show_paste_button:
            
            self._paste_button.hide()
            
        
        QP.AddToLayout( self._text_input_hbox, self._paste_button, CC.FLAGS_VCENTER )
        
        vbox = QP.VBoxLayout()
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._file_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._tag_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._dropdown_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.setLayout( vbox )
        
    
    def _BroadcastChoices( self, predicates, shift_down ):
        
        tags = {predicate.GetValue() for predicate in predicates}
        
        if len( tags ) > 0:
            
            self._chosen_tag_callable( tags )
            
        
        self._ClearInput()
        
    
    def _BroadcastCurrentText( self, shift_down ):
        
        ( raw_entry, search_text, cache_text, entry_predicate, sibling_predicate ) = self._ParseSearchText()
        
        try:
            
            HydrusTags.CheckTagNotEmpty( search_text )
            
        except HydrusExceptions.SizeException:
            
            return
            
        
        self._BroadcastChoices( { entry_predicate }, shift_down )
        
    
    def _ChangeTagService( self, tag_service_key ):
        
        AutoCompleteDropdownTags._ChangeTagService( self, tag_service_key )
        
        if self._tag_service_key_changed_callable is not None:
            
            self._tag_service_key_changed_callable( tag_service_key )
            
        
    
    def _InitFavouritesList( self ):
        
        favs_list = ClientGUIListBoxes.ListBoxTagsACWrite( self._dropdown_notebook, self.BroadcastChoices, self._tag_service_key, height_num_chars = self._list_height_num_chars )
        
        return favs_list
        
    
    def _InitSearchResultsList( self ):
        
        self._list_height_num_chars = 8
        
        return ClientGUIListBoxes.ListBoxTagsACWrite( self._dropdown_notebook, self.BroadcastChoices, self._tag_service_key, height_num_chars = self._list_height_num_chars )
        
    
    def _ParseSearchText( self ):
        
        raw_entry = self._text_ctrl.text()
        
        tag = HydrusTags.CleanTag( raw_entry )
        
        explicit_wildcard = '*' in raw_entry
        
        ( wildcard_text, search_text ) = ClientSearch.ConvertEntryTextToSearchText( raw_entry )
        
        if explicit_wildcard:
            
            cache_text = None
            
        else:
            
            cache_text = search_text[:-1] # take off the trailing '*' for the cache text
            
        
        entry_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag )
        
        siblings_manager = HG.client_controller.tag_siblings_manager
        
        sibling = siblings_manager.GetSibling( self._tag_service_key, tag )
        
        if sibling is not None:
            
            sibling_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, sibling )
            
        else:
            
            sibling_predicate = None
            
        
        return ( raw_entry, search_text, cache_text, entry_predicate, sibling_predicate )
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        try:
            
            tags = [ text for text in HydrusText.DeserialiseNewlinedTexts( raw_text ) ]
            
            tags = HydrusTags.CleanTags( tags )
            
            entry_predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag ) for tag in tags ]
            
            if len( entry_predicates ) > 0:
                
                shift_down = False
                
                self._BroadcastChoices( entry_predicates, shift_down )
                
            
        except:
            
            QW.QMessageBox.critical( self, 'Error', 'I could not understand what was in the clipboard' )
            
            raise
            
        
    
    
    def _ShouldTakeResponsibilityForEnter( self ):
        
        ( raw_entry, search_text, cache_text, entry_predicate, sibling_predicate ) = self._ParseSearchText()
        
        looking_at_search_results = self._dropdown_notebook.currentWidget() == self._search_results_list
        
        sitting_on_empty = raw_entry == ''
        
        something_to_broadcast = not sitting_on_empty
        
        # the list has results, but they are out of sync with what we have currently entered
        # when the user has quickly typed something in and the results are not yet in
        results_desynced_with_text = raw_entry != self._current_list_raw_entry
        
        p1 = something_to_broadcast and results_desynced_with_text
        
        # when the text ctrl is empty and we want to push a None to the parent dialog
        p2 = sitting_on_empty
        
        return looking_at_search_results and ( p1 or p2 )
        
    
    def _StartResultsFetchJob( self, job_key ):
        
        parsed_search_text = self._ParseSearchText()
        
        stub_predicates = []
        
        stub_predicates = InsertStaticPredicatesForWrite( stub_predicates, parsed_search_text, self._tag_service_key, self._expand_parents )
        
        AppendLoadingPredicate( stub_predicates )
        
        HG.client_controller.CallLaterQtSafe(self, 0.2, self.SetStubPredicates, job_key, stub_predicates)
        
        HG.client_controller.CallToThread( WriteFetch, self, job_key, self.SetFetchedResults, parsed_search_text, self._file_service_key, self._tag_service_key, self._expand_parents, self._search_text_for_current_cache, self._cached_results )
        
    
    def _TakeResponsibilityForEnter( self, shift_down ):
        
        if self._text_ctrl.text() == '' and self._dropdown_notebook.currentWidget() == self._search_results_list:
            
            if self._null_entry_callable is not None:
                
                self._null_entry_callable()
                
            
        else:
            
            self._BroadcastCurrentText( shift_down )
            
        
    
    def RefreshFavouriteTags( self ):
        
        favourite_tags = list( HG.client_controller.new_options.GetStringList( 'favourite_tags' ) )
        
        favourite_tags.sort()
        
        predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag ) for tag in favourite_tags ]
        
        parents_manager = HG.client_controller.tag_parents_manager
        
        predicates = parents_manager.ExpandPredicates( CC.COMBINED_TAG_SERVICE_KEY, predicates )
        
        self._favourites_list.SetPredicates( predicates )
        
    
    def SetExpandParents( self, expand_parents ):
        
        self._expand_parents = expand_parents
        
    
    def SetFetchedResults( self, job_key, search_text, search_text_for_cache, cached_results, results, next_search_is_probably_fast ):
        
        if self._current_fetch_job_key is not None and self._current_fetch_job_key.GetKey() == job_key.GetKey():
            
            AutoCompleteDropdownTags.SetFetchedResults( self, job_key, search_text, search_text_for_cache, cached_results, results )
            
            self._next_search_is_probably_fast = next_search_is_probably_fast
            
        
    
class EditAdvancedORPredicates( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, initial_string = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._input_text = QW.QLineEdit( self )
        
        self._result_preview = QW.QPlainTextEdit()
        self._result_preview.setReadOnly( True )
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._result_preview, ( 64, 6 ) )
        
        self._result_preview.setMinimumWidth( width )
        self._result_preview.setMinimumHeight( height )
        
        self._current_predicates = []
        
        #
        
        if initial_string is not None:
            
            self._input_text.setText( initial_string )
            
        
        #
        
        rows = []
        
        rows.append( ( 'Input: ', self._input_text ) )
        rows.append( ( 'Result preview: ', self._result_preview ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        summary = 'Enter a complicated tag search here as text, such as \'( blue eyes and blonde hair ) or ( green eyes and red hair )\', and this should turn it into hydrus-compatible search predicates.'
        summary += os.linesep * 2
        summary += 'Accepted operators: not (!, -), and (&&), or (||), implies (=>), xor, xnor (iff, <=>), nand, nor.'
        summary += os.linesep * 2
        summary += 'Parentheses work the usual way. \ can be used to escape characters (e.g. to search for tags including parentheses)'
        
        st = ClientGUICommon.BetterStaticText( self, summary )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._UpdateText()
        
        self._input_text.textChanged.connect( self.EventUpdateText )
        
    
    def _UpdateText( self ):
        
        text = self._input_text.text()
        
        self._current_predicates = []
        
        colour = ( 0, 0, 0 )
        
        output = ''
        
        if len( text ) > 0:
            
            try:
                
                # this makes a list of sets, each set representing a list of AND preds
                result = LogicExpressionQueryParser.parse_logic_expression_query( text )
                
                for s in result:
                    
                    row_preds = []
                    
                    for tag_string in s:
                        
                        if tag_string.startswith( '-' ):
                            
                            inclusive = False
                            
                            tag_string = tag_string[1:]
                            
                        else:
                            
                            inclusive = True
                            
                        
                        if '*' in tag_string:
                            
                            ( namespace, subtag ) = HydrusTags.SplitTag( tag_string )
                            
                            if '*' not in namespace and subtag == '*':
                                
                                row_pred = ClientSearch.Predicate( HC.PREDICATE_TYPE_NAMESPACE, namespace, inclusive )
                                
                            else:
                                
                                row_pred = ClientSearch.Predicate( HC.PREDICATE_TYPE_WILDCARD, tag_string, inclusive )
                                
                            
                        else:
                            
                            row_pred = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag_string, inclusive )
                            
                        
                        row_preds.append( row_pred )
                        
                    
                    if len( row_preds ) == 1:
                        
                        self._current_predicates.append( row_preds[0] )
                        
                    else:
                        
                        self._current_predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_OR_CONTAINER, row_preds ) )
                        
                    
                
                output = os.linesep.join( ( pred.ToString() for pred in self._current_predicates ) )
                colour = ( 0, 128, 0 )
                
            except ValueError:
                
                output = 'Could not parse!'
                colour = ( 128, 0, 0 )
                
            
        
        self._result_preview.setPlainText( output )
        QP.SetForegroundColour( self._result_preview, colour )
        
    
    def EventUpdateText( self, text ):
        
        self._UpdateText()
        
    
    def GetValue( self ):
        
        self._UpdateText()
        
        if len( self._current_predicates ) == 0:
            
            raise HydrusExceptions.VetoException( 'Please enter a string that parses into a set of search rules.' )
            
        
        return self._current_predicates
        
    
