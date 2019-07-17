from . import ClientCaches
from . import ClientConstants as CC
from . import ClientData
from . import ClientGUICommon
from . import ClientGUIFunctions
from . import ClientGUIListBoxes
from . import ClientGUIMenus
from . import ClientGUIShortcuts
from . import ClientSearch
from . import ClientThreading
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusTags
from . import HydrusText
import itertools
import wx
import wx.lib.scrolledpanel

ID_TIMER_DROPDOWN_HIDE = wx.NewId()
ID_TIMER_AC_LAG = wx.NewId()

( SelectUpEvent, EVT_SELECT_UP ) = wx.lib.newevent.NewCommandEvent()
( SelectDownEvent, EVT_SELECT_DOWN ) = wx.lib.newevent.NewCommandEvent()

( ShowPreviousEvent, EVT_SHOW_PREVIOUS ) = wx.lib.newevent.NewCommandEvent()
( ShowNextEvent, EVT_SHOW_NEXT ) = wx.lib.newevent.NewCommandEvent()

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
    
    ( raw_entry, inclusive, search_text, explicit_wildcard, cache_text, entry_predicate ) = parsed_search_text
    
    if search_text in ( '', ':', '*' ):
        
        pass
        
    else:
        
        if include_unusual_predicate_types:
            
            if explicit_wildcard:
                
                predicates.insert( 0, ClientSearch.Predicate( HC.PREDICATE_TYPE_WILDCARD, search_text, inclusive ) )
                
            else:
                
                ( namespace, half_complete_subtag ) = HydrusTags.SplitTag( search_text )
                
                if namespace != '' and half_complete_subtag in ( '', '*' ):
                    
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
    
    if search_text in ( '', ':', '*' ):
        
        pass
        
    else:
        
        PutAtTopOfMatches( predicates, entry_predicate )
        
        if sibling_predicate is not None:
            
            PutAtTopOfMatches( predicates, sibling_predicate )
            
        
        if expand_parents:
            
            predicates = HG.client_controller.tag_parents_manager.ExpandPredicates( tag_service_key, predicates )
            
        
    
    return predicates
    
def ReadFetch( win, job_key, results_callable, parsed_search_text, wx_media_callable, file_search_context, synchronised, include_unusual_predicate_types, initial_matches_fetched, search_text_for_current_cache, cached_results, under_construction_or_predicate ):
    
    next_search_is_probably_fast = False
    
    include_current = file_search_context.IncludeCurrentTags()
    include_pending = file_search_context.IncludePendingTags()
    
    file_service_key = file_search_context.GetFileServiceKey()
    tag_service_key = file_search_context.GetTagServiceKey()
    
    ( raw_entry, inclusive, search_text, explicit_wildcard, cache_text, entry_predicate ) = parsed_search_text
    
    if search_text in ( '', ':', '*' ):
        
        # if the user inputs '-' or similar, let's go to an empty list
        if raw_entry == '':
            
            input_just_changed = search_text_for_current_cache is not None
            
            db_not_going_to_hang_if_we_hit_it = not HG.client_controller.DBCurrentlyDoingJob()
            
            if input_just_changed or db_not_going_to_hang_if_we_hit_it or not initial_matches_fetched:
                
                if file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
                    
                    search_service_key = tag_service_key
                    
                else:
                    
                    search_service_key = file_service_key
                    
                
                search_text_for_current_cache = None
                
                cached_results = HG.client_controller.Read( 'file_system_predicates', search_service_key )
                
            
            matches = cached_results
            
        else:
            
            matches = []
            
        
    else:
        
        ( namespace, half_complete_subtag ) = HydrusTags.SplitTag( search_text )
        
        siblings_manager = HG.client_controller.tag_siblings_manager
        
        if False and half_complete_subtag == '':
            
            search_text_for_current_cache = None
            
            matches = [] # a query like 'namespace:'
            
        else:
            
            fetch_from_db = True
            
            if synchronised and wx_media_callable is not None:
                
                try:
                    
                    media = HG.client_controller.CallBlockingToWX( win, wx_media_callable )
                    
                except HydrusExceptions.WXDeadWindowException:
                    
                    return
                    
                
                can_fetch_from_media = media is not None and len( media ) > 0
                
                if can_fetch_from_media:
                    
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
                    
                
            else:
                
                # it is possible that media will change between calls to this, so don't cache it
                # it's also quick as hell, so who cares
                
                tags_managers = []
                
                for m in media:
                    
                    if m.IsCollection():
                        
                        tags_managers.extend( m.GetSingletonsTagsManagers() )
                        
                    else:
                        
                        tags_managers.append( m.GetTagsManager() )
                        
                    
                
                tags_to_do = set()
                
                current_tags_to_count = collections.Counter()
                pending_tags_to_count = collections.Counter()
                
                if include_current:
                    
                    lists_of_current_tags = [ list( tags_manager.GetCurrent( tag_service_key ) ) for tags_manager in tags_managers ]
                    
                    current_tags_flat_iterable = itertools.chain.from_iterable( lists_of_current_tags )
                    
                    current_tags_flat = ClientSearch.FilterTagsBySearchText( tag_service_key, search_text, current_tags_flat_iterable )
                    
                    current_tags_to_count.update( current_tags_flat )
                    
                    tags_to_do.update( list(current_tags_to_count.keys()) )
                    
                
                if include_pending:
                    
                    lists_of_pending_tags = [ list( tags_manager.GetPending( tag_service_key ) ) for tags_manager in tags_managers ]
                    
                    pending_tags_flat_iterable = itertools.chain.from_iterable( lists_of_pending_tags )
                    
                    pending_tags_flat = ClientSearch.FilterTagsBySearchText( tag_service_key, search_text, pending_tags_flat_iterable )
                    
                    pending_tags_to_count.update( pending_tags_flat )
                    
                    tags_to_do.update( list(pending_tags_to_count.keys()) )
                    
                
                predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag, inclusive, current_tags_to_count[ tag ], pending_tags_to_count[ tag ] ) for tag in tags_to_do ]
                
                if tag_service_key != CC.COMBINED_TAG_SERVICE_KEY:
                    
                    predicates = siblings_manager.CollapsePredicates( tag_service_key, predicates )
                    
                
                if namespace == '':
                    
                    predicates = ClientData.MergePredicates( predicates, add_namespaceless = True )
                    
                
                next_search_is_probably_fast = True
                
            
            matches = ClientSearch.FilterPredicatesBySearchText( tag_service_key, search_text, predicates )
            
            matches = ClientSearch.SortPredicates( matches )
            
        
        for match in matches:
            
            if match.GetInclusive() != inclusive:
                
                match.SetInclusive( inclusive )
                
            
        
    
    matches = InsertStaticPredicatesForRead( matches, parsed_search_text, include_unusual_predicate_types, under_construction_or_predicate )
    
    if job_key.IsCancelled():
        
        return
        
    
    HG.client_controller.CallLaterWXSafe( win, 0.0, results_callable, job_key, search_text, search_text_for_current_cache, cached_results, matches, next_search_is_probably_fast )
    
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
    
    HG.client_controller.CallLaterWXSafe( win, 0.0, results_callable, job_key, search_text, search_text_for_current_cache, cached_results, matches, next_search_is_probably_fast )
    
# much of this is based on the excellent TexCtrlAutoComplete class by Edward Flick, Michele Petrazzo and Will Sadkin, just with plenty of simplification and integration into hydrus
class AutoCompleteDropdown( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._intercept_key_events = True
        
        tlp = self.GetTopLevelParent()
        
        # There's a big bug in wx where FRAME_FLOAT_ON_PARENT Frames don't get passed their mouse events if their parent is a Dialog jej
        # I think it is something to do with the initialisation order; if the frame is init'ed before the ShowModal call, but whatever.
        
        # This turned out to be ugly when I added the manage tags frame, so I've set it to if the tlp has a parent, which basically means "not the main gui"
        
        not_main_gui = tlp.GetParent() is not None
        
        if not_main_gui or HC.options[ 'always_embed_autocompletes' ] or not HC.PLATFORM_WINDOWS:
            
            self._float_mode = False
            
        else:
            
            self._float_mode = True
            
        
        self._text_ctrl = wx.TextCtrl( self, style = wx.TE_PROCESS_ENTER )
        
        self._UpdateBackgroundColour()
        
        self._last_attempted_dropdown_width = 0
        self._last_attempted_dropdown_position = ( None, None )
        
        self._last_move_event_started = 0.0
        self._last_move_event_occurred = 0.0
        
        if self._float_mode:
            
            self._text_ctrl.Bind( wx.EVT_SET_FOCUS, self.EventSetFocus )
            self._text_ctrl.Bind( wx.EVT_KILL_FOCUS, self.EventKillFocus )
            
        
        self._text_ctrl.Bind( wx.EVT_TEXT, self.EventText )
        self._text_ctrl.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
        self._text_ctrl.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._text_input_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        self._text_input_hbox.Add( self._text_ctrl, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        
        vbox.Add( self._text_input_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #self._dropdown_window = wx.PopupWindow( self, flags = wx.BORDER_RAISED )
        #self._dropdown_window = wx.PopupTransientWindow( self, style = wx.BORDER_RAISED )
        #self._dropdown_window = wx.Window( self, style = wx.BORDER_RAISED )
        
        #self._dropdown_window = wx.Panel( self )
        
        if self._float_mode:
            
            self._dropdown_window = wx.Frame( self, style = wx.FRAME_TOOL_WINDOW | wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT | wx.BORDER_RAISED )
            
            self._dropdown_window.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
            
            self._dropdown_window.SetPosition( ClientGUIFunctions.ClientToScreen( self._text_ctrl, ( 0, 0 ) ) )
            
            self._dropdown_window.Bind( wx.EVT_CLOSE, self.EventCloseDropdown )
            
            self._dropdown_hidden = True
            
            self._list_height_num_chars = 19
            
        else:
            
            self._dropdown_window = wx.Panel( self )
            
            self._list_height_num_chars = 8
            
        
        self._dropdown_notebook = wx.Notebook( self._dropdown_window )
        
        #
        
        self._search_results_list = self._InitSearchResultsList()
        
        self._dropdown_notebook.AddPage( self._search_results_list, 'results', True )
        
        #
        
        if not self._float_mode:
            
            vbox.Add( self._dropdown_window, CC.FLAGS_EXPAND_BOTH_WAYS )
            
        
        self.SetSizer( vbox )
        
        self._last_fetched_search_text = ''
        self._next_search_is_probably_fast = False
        
        self._search_text_for_current_cache = None
        self._cached_results = []
        
        self._current_fetch_job_key = None
        
        self._initial_matches_fetched = False
        
        self._move_hide_job = None
        self._refresh_list_job = None
        
        if self._float_mode:
            
            self.Bind( wx.EVT_MOVE, self.EventMove )
            self.Bind( wx.EVT_SIZE, self.EventMove )
            
            HG.client_controller.sub( self, '_ParentMovedOrResized', 'main_gui_move_event' )
            
            parent = self
            
            while True:
                
                try:
                    
                    parent = parent.GetParent()
                    
                    if isinstance( parent, wx.ScrolledWindow ):
                        
                        parent.Bind( wx.EVT_SCROLLWIN, self.EventMove )
                        
                    
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
            
        
    
    def _CancelScheduledListRefresh( self ):
        
        if self._refresh_list_job is not None:
            
            self._refresh_list_job.Cancel()
            
        
    
    def _ClearInput( self ):
        
        self._CancelCurrentResultsFetchJob()
        
        self._text_ctrl.SetValue( '' )
        
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
            
            self.GetTopLevelParent().SetFocus()
            
            return True
            
        else:
            
            return False
            
        
    
    def _HideDropdown( self ):
        
        if not self._dropdown_hidden:
            
            self._dropdown_window.Hide()
            
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
                        
                        self._move_hide_job = HG.client_controller.CallRepeatingWXSafe( self._dropdown_window, 0.0, 0.25, self._DropdownHideShow )
                        
                    
                    self._move_hide_job.Delay( 0.25 )
                    
                
            else:
                
                self._DropdownHideShow()
                
            
        
    
    def _ScheduleListRefresh( self, delay ):
        
        if self._refresh_list_job is not None and delay == 0.0:
            
            self._refresh_list_job.Wake()
            
        else:
            
            self._CancelScheduledListRefresh()
            
            self._refresh_list_job = HG.client_controller.CallLaterWXSafe( self, delay, self._UpdateSearchResultsList )
            
        
    
    def _SetListDirty( self ):
        
        self._search_text_for_current_cache = None
        
        self._ScheduleListRefresh( 0.0 )
        
    
    def _SetResultsToList( self, results ):
        
        raise NotImplementedError()
        
    
    def _ShouldShow( self ):
        
        tlp_active = self.GetTopLevelParent().IsActive() or self._dropdown_window.IsActive()
        
        if HC.PLATFORM_LINUX:
            
            tlp = self.GetTopLevelParent()
            
            if isinstance( tlp, wx.Dialog ):
                
                visible = True
                
            else:
                
                # notebook on linux doesn't 'hide' things apparently, so isshownonscreen, which recursively tests parents' hide status, doesn't work!
                
                gui = HG.client_controller.GetGUI()
                
                current_page = gui.GetCurrentPage()
                
                visible = ClientGUIFunctions.IsWXAncestor( self, current_page )
                
            
        else:
            
            visible = self._text_ctrl.IsShownOnScreen()
            
        
        focus_remains_on_self_or_children = ClientGUIFunctions.WindowOrAnyTLPChildHasFocus( self )
        
        return tlp_active and visible and focus_remains_on_self_or_children
        
    
    def _ShouldTakeResponsibilityForEnter( self ):
        
        raise NotImplementedError()
        
    
    def _ShowDropdown( self ):
        
        ( text_width, text_height ) = self._text_ctrl.GetSize()
        
        if self._text_ctrl.IsShown():
            
            desired_dropdown_position = ClientGUIFunctions.ClientToScreen( self._text_ctrl, ( -2, text_height - 2 ) )
            
            if self._last_attempted_dropdown_position != desired_dropdown_position:
                
                self._dropdown_window.SetPosition( desired_dropdown_position )
                
                self._last_attempted_dropdown_position = desired_dropdown_position
                
            
        
        #
        
        show_and_fit_needed = False
        
        if self._dropdown_hidden:
            
            self._dropdown_window.Show()
            
            self._dropdown_hidden = False
            
        
        if text_width != self._last_attempted_dropdown_width:
            
            show_and_fit_needed = True
            
            self._dropdown_window.Fit()
            
            self._dropdown_window.SetSize( ( text_width, -1 ) )
            
            self._dropdown_window.Layout()
            
            self._last_attempted_dropdown_width = text_width
            
        
    
    def _StartResultsFetchJob( self, job_key ):
        
        raise NotImplementedError()
        
    
    def _TakeResponsibilityForEnter( self, shift_down ):
        
        raise NotImplementedError()
        
    
    def _UpdateBackgroundColour( self ):
        
        colour = HG.client_controller.new_options.GetColour( CC.COLOUR_AUTOCOMPLETE_BACKGROUND )
        
        if not self._intercept_key_events:
            
            colour = ClientData.GetLighterDarkerColour( colour )
            
        
        self._text_ctrl.SetBackgroundColour( colour )
        
        self._text_ctrl.Refresh()
        
    
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
        
    
    def EventCharHook( self, event ):
        
        HG.client_controller.ResetIdleTimer()
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key in ( wx.WXK_INSERT, wx.WXK_NUMPAD_INSERT ):
            
            self._intercept_key_events = not self._intercept_key_events
            
            self._UpdateBackgroundColour()
            
        elif key == wx.WXK_SPACE and event.RawControlDown(): # this is control, not command on os x, for which command+space does some os stuff
            
            self._ScheduleListRefresh( 0.0 )
            
        elif self._intercept_key_events:
            
            send_input_to_current_list = False
            
            current_results_list = self._dropdown_notebook.GetCurrentPage()
            
            current_list_is_empty = len( current_results_list ) == 0
            
            input_is_empty = self._text_ctrl.GetValue() == ''
            
            if key in ( ord( 'A' ), ord( 'a' ) ) and modifier == wx.ACCEL_CTRL:
                
                event.Skip()
                
            elif key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ) and self._ShouldTakeResponsibilityForEnter():
                
                shift_down = modifier == wx.ACCEL_SHIFT
                
                self._TakeResponsibilityForEnter( shift_down )
                
            elif input_is_empty: # maybe we should be sending a 'move' event to a different place
                
                if key in ( wx.WXK_UP, wx.WXK_NUMPAD_UP, wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN ) and current_list_is_empty:
                    
                    if key in ( wx.WXK_UP, wx.WXK_NUMPAD_UP ):
                        
                        new_event = SelectUpEvent( -1 )
                        
                    elif key in ( wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN ):
                        
                        new_event = SelectDownEvent( -1 )
                        
                    
                    wx.QueueEvent( self.GetEventHandler(), new_event )
                    
                elif key in ( wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN, wx.WXK_PAGEUP, wx.WXK_NUMPAD_PAGEUP ) and current_list_is_empty:
                    
                    if key in ( wx.WXK_PAGEUP, wx.WXK_NUMPAD_PAGEUP ):
                        
                        new_event = ShowPreviousEvent( -1 )
                        
                    elif key in ( wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN ):
                        
                        new_event = ShowNextEvent( -1 )
                        
                    
                    wx.QueueEvent( self.GetEventHandler(), new_event )
                    
                elif key in ( wx.WXK_LEFT, wx.WXK_NUMPAD_LEFT, wx.WXK_RIGHT, wx.WXK_NUMPAD_RIGHT ):
                    
                    if key in ( wx.WXK_LEFT, wx.WXK_NUMPAD_LEFT ):
                        
                        direction = -1
                        
                    elif key in ( wx.WXK_RIGHT, wx.WXK_NUMPAD_RIGHT ):
                        
                        direction = 1
                        
                    
                    self.MoveNotebookPageFocus( direction = direction )
                    
                elif key == wx.WXK_ESCAPE:
                    
                    escape_caught = self._HandleEscape()
                    
                    if not escape_caught:
                        
                        send_input_to_current_list = True
                        
                    
                else:
                    
                    send_input_to_current_list = True
                    
                
            else:
                
                send_input_to_current_list = True
                
            
            if send_input_to_current_list:
                
                # Don't say QueueEvent here--it duplicates the event processing at higher levels, leading to 2 x F9, for instance
                current_results_list.EventCharHook( event ) # ultimately, this typically skips the event, letting the text ctrl take it
                
            
        else:
            
            event.Skip()
            
        
    
    def EventCloseDropdown( self, event ):
        
        HG.client_controller.GetGUI().Close()
        
    
    def EventKillFocus( self, event ):
        
        if self._float_mode:
            
            self._DropdownHideShow()
            
        
        event.Skip()
        
    
    def EventMouseWheel( self, event ):
        
        current_results_list = self._dropdown_notebook.GetCurrentPage()
        
        if self._text_ctrl.GetValue() == '' and len( current_results_list ) == 0:
            
            if event.GetWheelRotation() > 0:
                
                new_event = SelectUpEvent( -1 )
                
            else:
                
                new_event = SelectDownEvent( -1 )
                
            
            wx.QueueEvent( self.GetEventHandler(), new_event )
            
        else:
            
            if event.CmdDown():
                
                if event.GetWheelRotation() > 0:
                    
                    current_results_list.MoveSelectionUp()
                    
                else:
                    
                    current_results_list.MoveSelectionDown()
                    
                
            else:
                
                # for some reason, the scrolledwindow list doesn't process scroll events properly when in a popupwindow
                # so let's just tell it to scroll manually
                
                ( start_x, start_y ) = current_results_list.GetViewStart()
                
                if event.GetWheelRotation() > 0:
                    
                    current_results_list.Scroll( -1, start_y - 3 )
                    
                else:
                    
                    current_results_list.Scroll( -1, start_y + 3 )
                    
                
                if event.GetWheelRotation() > 0:
                    
                    command_type = wx.wxEVT_SCROLLWIN_LINEUP
                    
                else:
                    
                    command_type = wx.wxEVT_SCROLLWIN_LINEDOWN
                    
                
                wx.QueueEvent( current_results_list.GetEventHandler(), wx.ScrollWinEvent( command_type ) )
                
            
        
    
    def EventMove( self, event ):
        
        self._ParentMovedOrResized()
        
        event.Skip()
        
    
    def EventSetFocus( self, event ):
        
        if self._float_mode:
            
            self._DropdownHideShow()
            
        
        event.Skip()
        
    
    def EventText( self, event ):
        
        num_chars = len( self._text_ctrl.GetValue() )
        
        if num_chars == 0:
            
            self._ScheduleListRefresh( 0.0 )
            
        else:
            
            if HG.client_controller.new_options.GetBoolean( 'autocomplete_results_fetch_automatically' ):
                
                self._ScheduleListRefresh( 0.0 )
                
            
            if self._dropdown_notebook.GetCurrentPage() != self._search_results_list:
                
                self.MoveNotebookPageFocus( index = 0 )
                
            
        
    
    def ForceSizeCalcNow( self ):
        
        if self._float_mode:
            
            self._DropdownHideShow()
            
        
    
    def MoveNotebookPageFocus( self, index = None, direction = None ):
        
        new_index = None
        
        if index is not None:
            
            new_index = index
            
        elif direction is not None:
            
            current_index = self._dropdown_notebook.GetSelection()
            
            if current_index is not None and current_index != wx.NOT_FOUND:
                
                number_of_pages = self._dropdown_notebook.GetPageCount()
                
                new_index = ( current_index + direction ) % number_of_pages # does wraparound
                
            
        
        if new_index is not None:
            
            self._dropdown_notebook.ChangeSelection( new_index )
            
            self._text_ctrl.SetFocus()
            
        
    
    def SetFetchedResults( self, job_key, search_text, search_text_for_cache, cached_results, results ):
        
        if self._current_fetch_job_key is not None and self._current_fetch_job_key.GetKey() == job_key.GetKey():
            
            self._CancelCurrentResultsFetchJob()
            
            self._last_fetched_search_text = search_text
            
            self._search_text_for_current_cache = search_text_for_cache
            self._cached_results = cached_results
            
            self._current_fetch_job_key = None
            
            self._initial_matches_fetched = True
            
            self._SetResultsToList( results )
            
        
    
    def SetFocus( self ):
        
        if HC.PLATFORM_OSX:
            
            wx.CallAfter( self._text_ctrl.SetFocus )
            
        else:
            
            self._text_ctrl.SetFocus()
            
        
    
class AutoCompleteDropdownTags( AutoCompleteDropdown ):
    
    def __init__( self, parent, file_service_key, tag_service_key ):
        
        self._file_service_key = file_service_key
        self._tag_service_key = tag_service_key
        
        AutoCompleteDropdown.__init__( self, parent )
        
        self._allow_all_known_files = True
        
        file_service = HG.client_controller.services_manager.GetService( self._file_service_key )
        
        tag_service = HG.client_controller.services_manager.GetService( self._tag_service_key )
        
        self._file_repo_button = ClientGUICommon.BetterButton( self._dropdown_window, file_service.GetName(), self.FileButtonHit )
        self._file_repo_button.SetMinSize( ( 20, -1 ) )
        
        self._tag_repo_button = ClientGUICommon.BetterButton( self._dropdown_window, tag_service.GetName(), self.TagButtonHit )
        self._tag_repo_button.SetMinSize( ( 20, -1 ) )
        
        self._favourites_list = self._InitFavouritesList()
        
        self.RefreshFavouriteTags()
        
        self._dropdown_notebook.AddPage( self._favourites_list, 'favourites', False )
        
        #
        
        HG.client_controller.sub( self, 'RefreshFavouriteTags', 'notify_new_favourite_tags' )
        
    
    def _ChangeFileService( self, file_service_key ):
        
        if file_service_key == CC.COMBINED_FILE_SERVICE_KEY and self._tag_service_key == CC.COMBINED_TAG_SERVICE_KEY:
            
            self._ChangeTagService( CC.LOCAL_TAG_SERVICE_KEY )
            
        
        self._file_service_key = file_service_key
        
        file_service = HG.client_controller.services_manager.GetService( self._file_service_key )
        
        name = file_service.GetName()
        
        self._file_repo_button.SetLabelText( name )
        
        self._SetListDirty()
        
    
    def _ChangeTagService( self, tag_service_key ):
        
        if tag_service_key == CC.COMBINED_TAG_SERVICE_KEY and self._file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
            
            self._ChangeFileService( CC.LOCAL_FILE_SERVICE_KEY )
            
        
        self._tag_service_key = tag_service_key
        
        self._search_results_list.SetTagService( self._tag_service_key )
        
        tag_service = tag_service = HG.client_controller.services_manager.GetService( self._tag_service_key )
        
        name = tag_service.GetName()
        
        self._tag_repo_button.SetLabelText( name )
        
        self._search_text_for_current_cache = None
        
        self._SetListDirty()
        
    
    def _InitFavouritesList( self ):
        
        raise NotImplementedError()
        
    
    def _SetResultsToList( self, results ):
        
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
            
        
        menu = wx.Menu()
        
        for service in services:
            
            ClientGUIMenus.AppendMenuItem( self, menu, service.GetName(), 'Change the current file domain to ' + service.GetName() + '.', self._ChangeFileService, service.GetServiceKey() )
            
        
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
        
        services.append( services_manager.GetService( CC.LOCAL_TAG_SERVICE_KEY ) )
        services.extend( services_manager.GetServices( ( HC.TAG_REPOSITORY, ) ) )
        services.append( services_manager.GetService( CC.COMBINED_TAG_SERVICE_KEY ) )
        
        menu = wx.Menu()
        
        for service in services:
            
            ClientGUIMenus.AppendMenuItem( self, menu, service.GetName(), 'Change the current tag domain to ' + service.GetName() + '.', self._ChangeTagService, service.GetServiceKey() )
            
        
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
        self._include_current_tags.SetToolTip( 'select whether to include current tags in the search' )
        self._include_pending_tags = ClientGUICommon.OnOffButton( self._dropdown_window, self._page_key, 'notify_include_pending', on_label = 'include pending tags', off_label = 'exclude pending tags', start_on = file_search_context.IncludePendingTags() )
        self._include_pending_tags.SetToolTip( 'select whether to include pending tags in the search' )
        
        self._synchronised = ClientGUICommon.OnOffButton( self._dropdown_window, self._page_key, 'notify_search_immediately', on_label = 'searching immediately', off_label = 'waiting -- tag counts may be inaccurate', start_on = synchronised )
        self._synchronised.SetToolTip( 'select whether to renew the search as soon as a new predicate is entered' )
        
        self._or_cancel = ClientGUICommon.BetterBitmapButton( self._dropdown_window, CC.GlobalBMPs.delete, self._CancelORConstruction )
        self._or_cancel.SetToolTip( 'Cancel OR Predicate construction.' )
        self._or_cancel.Hide()
        
        self._or_rewind = ClientGUICommon.BetterBitmapButton( self._dropdown_window, CC.GlobalBMPs.previous, self._RewindORConstruction )
        self._or_rewind.SetToolTip( 'Rewind OR Predicate construction.' )
        self._or_rewind.Hide()
        
        self._include_unusual_predicate_types = include_unusual_predicate_types
        
        button_hbox_1 = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox_1.Add( self._include_current_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        button_hbox_1.Add( self._include_pending_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        sync_button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        sync_button_hbox.Add( self._synchronised, CC.FLAGS_EXPAND_BOTH_WAYS )
        sync_button_hbox.Add( self._or_cancel, CC.FLAGS_VCENTER )
        sync_button_hbox.Add( self._or_rewind, CC.FLAGS_VCENTER )
        
        button_hbox_2 = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox_2.Add( self._file_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        button_hbox_2.Add( self._tag_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( button_hbox_1, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( sync_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( button_hbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._dropdown_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.SetSizer( vbox )
        
        HG.client_controller.sub( self, 'SetSynchronisedWait', 'synchronised_wait_switch' )
        
        HG.client_controller.sub( self, 'IncludeCurrent', 'notify_include_current' )
        HG.client_controller.sub( self, 'IncludePending', 'notify_include_pending' )
        
    
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
        
        ( raw_entry, inclusive, search_text, explicit_wildcard, cache_text, entry_predicate ) = self._ParseSearchText()
        
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
        
        if self._under_construction_or_predicate is not None and self._text_ctrl.GetValue() == '':
            
            self._CancelORConstruction()
            
            return True
            
        else:
            
            return AutoCompleteDropdown._HandleEscape( self )
            
        
    
    def _InitFavouritesList( self ):
        
        favs_list = ClientGUIListBoxes.ListBoxTagsACRead( self._dropdown_notebook, self.BroadcastChoices, self._tag_service_key, height_num_chars = self._list_height_num_chars )
        
        return favs_list
        
    
    def _InitSearchResultsList( self ):
        
        return ClientGUIListBoxes.ListBoxTagsACRead( self._dropdown_notebook, self.BroadcastChoices, self._tag_service_key, height_num_chars = self._list_height_num_chars )
        
    
    def _ParseSearchText( self ):
        
        raw_entry = self._text_ctrl.GetValue()
        
        if raw_entry.startswith( '-' ):
            
            inclusive = False
            
            entry_text = raw_entry[1:]
            
        else:
            
            inclusive = True
            
            entry_text = raw_entry
            
        
        tag = HydrusTags.CleanTag( entry_text )
        
        explicit_wildcard = '*' in entry_text
        
        search_text = ClientSearch.ConvertEntryTextToSearchText( entry_text )
        
        if explicit_wildcard:
            
            cache_text = None
            
            entry_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_WILDCARD, search_text, inclusive )
            
        else:
            
            cache_text = search_text[:-1] # take off the trailing '*' for the cache text
            
            siblings_manager = HG.client_controller.tag_siblings_manager
            
            sibling = siblings_manager.GetSibling( self._tag_service_key, tag )
            
            if sibling is None:
                
                entry_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag, inclusive )
                
            else:
                
                entry_predicate = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, sibling, inclusive )
                
            
        
        return ( raw_entry, inclusive, search_text, explicit_wildcard, cache_text, entry_predicate )
        
    
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
        
        HG.client_controller.CallLaterWXSafe( self, 0.2, self.SetStubPredicates, job_key, stub_predicates )
        
        HG.client_controller.CallToThread( ReadFetch, self, job_key, self.SetFetchedResults, parsed_search_text, self._media_callable, self._file_search_context, self._synchronised.IsOn(), self._include_unusual_predicate_types, self._initial_matches_fetched, self._search_text_for_current_cache, self._cached_results, self._under_construction_or_predicate )
        
    
    def _ShouldTakeResponsibilityForEnter( self ):
        
        ( raw_entry, inclusive, search_text, explicit_wildcard, cache_text, entry_predicate ) = self._ParseSearchText()
        
        sitting_on_empty = raw_entry == ''
        
        # when the user has quickly typed something in and the results are not yet in
        
        p1 = not sitting_on_empty and self._last_fetched_search_text != search_text
        
        return p1
        
    
    def _TakeResponsibilityForEnter( self, shift_down ):
        
        self._BroadcastCurrentText( shift_down )
        
    
    def _UpdateORButtons( self ):
        
        layout_needed = False
        
        if self._under_construction_or_predicate is None:
            
            if self._or_cancel.IsShown():
                
                self._or_cancel.Hide()
                
                layout_needed = True
                
            
            if self._or_rewind.IsShown():
                
                self._or_rewind.Hide()
                
                layout_needed = True
                
            
        else:
            
            or_preds = self._under_construction_or_predicate.GetValue()
            
            if len( or_preds ) > 1:
                
                if not self._or_rewind.IsShown():
                    
                    self._or_rewind.Show()
                    
                    layout_needed = True
                    
                
            else:
                
                if self._or_rewind.IsShown():
                    
                    self._or_rewind.Hide()
                    
                    layout_needed = True
                    
                
            
            if not self._or_cancel.IsShown():
                
                self._or_cancel.Show()
                
                layout_needed = True
                
            
        
        if layout_needed:
            
            self._dropdown_window.Layout()
            
        
    
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
            
            num_chars = len( self._text_ctrl.GetValue() )
            
            if num_chars == 0:
                
                # refresh system preds after five mins
                
                self._ScheduleListRefresh( 300 )
                
            
        
    
    def SetSynchronisedWait( self, page_key ):
        
        if page_key == self._page_key:
            
            self._synchronised.EventButton( None )
            
        
    
class AutoCompleteDropdownTagsWrite( AutoCompleteDropdownTags ):
    
    def __init__( self, parent, chosen_tag_callable, expand_parents, file_service_key, tag_service_key, null_entry_callable = None, tag_service_key_changed_callable = None, show_paste_button = False ):
        
        self._chosen_tag_callable = chosen_tag_callable
        self._expand_parents = expand_parents
        self._null_entry_callable = null_entry_callable
        self._tag_service_key_changed_callable = tag_service_key_changed_callable
        
        if tag_service_key != CC.COMBINED_TAG_SERVICE_KEY and HC.options[ 'show_all_tags_in_autocomplete' ]:
            
            file_service_key = CC.COMBINED_FILE_SERVICE_KEY
            
        
        if tag_service_key == CC.LOCAL_TAG_SERVICE_KEY:
            
            file_service_key = CC.LOCAL_FILE_SERVICE_KEY
            
        
        AutoCompleteDropdownTags.__init__( self, parent, file_service_key, tag_service_key )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.paste, self._Paste )
        self._paste_button.SetToolTip( 'Paste from the clipboard and quick-enter as if you had typed. This can take multiple newline-separated tags.' )
        
        if not show_paste_button:
            
            self._paste_button.Hide()
            
        
        self._text_input_hbox.Add( self._paste_button, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._file_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._tag_repo_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.Add( self._dropdown_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._dropdown_window.SetSizer( vbox )
        
    
    def _BroadcastChoices( self, predicates, shift_down ):
        
        tags = { predicate.GetValue() for predicate in predicates }
        
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
        
        return ClientGUIListBoxes.ListBoxTagsACWrite( self._dropdown_notebook, self.BroadcastChoices, self._tag_service_key, height_num_chars = self._list_height_num_chars )
        
    
    def _ParseSearchText( self ):
        
        raw_entry = self._text_ctrl.GetValue()
        
        tag = HydrusTags.CleanTag( raw_entry )
        
        search_text = ClientSearch.ConvertEntryTextToSearchText( raw_entry )
        
        if ClientSearch.IsComplexWildcard( search_text ):
            
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
            
            wx.MessageBox( str( e ) )
            
            return
            
        
        try:
            
            tags = [ text for text in HydrusText.DeserialiseNewlinedTexts( raw_text ) ]
            
            tags = HydrusTags.CleanTags( tags )
            
            entry_predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag ) for tag in tags ]
            
            if len( entry_predicates ) > 0:
                
                shift_down = False
                
                self._BroadcastChoices( entry_predicates, shift_down )
                
            
        except:
            
            wx.MessageBox( 'I could not understand what was in the clipboard' )
            
            raise
            
        
    
    
    def _ShouldTakeResponsibilityForEnter( self ):
        
        ( raw_entry, search_text, cache_text, entry_predicate, sibling_predicate ) = self._ParseSearchText()
        
        sitting_on_empty = raw_entry == ''
        
        # when the user has quickly typed something in and the results are not yet in
        
        p1 = not sitting_on_empty and self._last_fetched_search_text != search_text
        
        # when the text ctrl is empty, we are looking at search results, and we want to push a None to the parent dialog
        
        p2 = sitting_on_empty and self._dropdown_notebook.GetCurrentPage() == self._search_results_list
        
        return p1 or p2
        
    
    def _StartResultsFetchJob( self, job_key ):
        
        parsed_search_text = self._ParseSearchText()
        
        stub_predicates = []
        
        stub_predicates = InsertStaticPredicatesForWrite( stub_predicates, parsed_search_text, self._tag_service_key, self._expand_parents )
        
        AppendLoadingPredicate( stub_predicates )
        
        HG.client_controller.CallLaterWXSafe( self, 0.2, self.SetStubPredicates, job_key, stub_predicates )
        
        HG.client_controller.CallToThread( WriteFetch, self, job_key, self.SetFetchedResults, parsed_search_text, self._file_service_key, self._tag_service_key, self._expand_parents, self._search_text_for_current_cache, self._cached_results )
        
    
    def _TakeResponsibilityForEnter( self, shift_down ):
        
        if self._text_ctrl.GetValue() == '' and self._dropdown_notebook.GetCurrentPage() == self._search_results_list:
            
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
        
    
    def SetFetchedResults( self, job_key, search_text, search_text_for_cache, cached_results, results, next_search_is_probably_fast ):
        
        if self._current_fetch_job_key is not None and self._current_fetch_job_key.GetKey() == job_key.GetKey():
            
            AutoCompleteDropdownTags.SetFetchedResults( self, job_key, search_text, search_text_for_cache, cached_results, results )
            
            self._next_search_is_probably_fast = next_search_is_probably_fast
            
        
    
