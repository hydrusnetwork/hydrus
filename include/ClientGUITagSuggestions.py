from . import ClientConstants as CC
from . import ClientData
from . import ClientGUICommon
from . import ClientGUIDialogs
from . import ClientGUIListBoxes
from . import ClientGUIParsing
from . import ClientParsing
from . import ClientSearch
from . import ClientThreading
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusSerialisable
import wx

class ListBoxTagsSuggestionsFavourites( ClientGUIListBoxes.ListBoxTagsStrings ):
    
    def __init__( self, parent, activate_callable, sort_tags = True ):
        
        ClientGUIListBoxes.ListBoxTagsStrings.__init__( self, parent, sort_tags = sort_tags )
        
        self._activate_callable = activate_callable
        
        width = HG.client_controller.new_options.GetInteger( 'suggested_tags_width' )
        
        if width is not None:
            
            self.SetMinSize( ( width, -1 ) )
            
        
    
    def _Activate( self ):
        
        if len( self._selected_terms ) > 0:
            
            tags = set( self._selected_terms )
            
            self._activate_callable( tags )
            
        
    
    def ActivateAll( self ):
        
        self._activate_callable( self.GetTags(), only_add = True )
        
    
    def TakeFocusForUser( self ):
        
        if len( self._selected_terms ) == 0 and len( self._terms ) > 0:
            
            self._Hit( False, False, 0 )
            
        
        self.SetFocus()
        
    
class ListBoxTagsSuggestionsRelated( ClientGUIListBoxes.ListBoxTagsPredicates ):
    
    def __init__( self, parent, activate_callable ):
        
        ClientGUIListBoxes.ListBoxTags.__init__( self, parent )
        
        self._activate_callable = activate_callable
        
        width = HG.client_controller.new_options.GetInteger( 'suggested_tags_width' )
        
        self.SetMinSize( ( width, -1 ) )
        
    
    def _Activate( self ):
        
        if len( self._selected_terms ) > 0:
            
            tags = { predicate.GetValue() for predicate in self._selected_terms }
            
            self._activate_callable( tags )
            
        
    
    def _GetTextFromTerm( self, term ):
        
        predicate = term
        
        return predicate.ToString( with_count = False )
        
    
    def SetPredicates( self, predicates ):
        
        self._Clear()
        
        for predicate in predicates:
            
            self._AppendTerm( predicate )
            
        
        self._DataHasChanged()
        
    
    def TakeFocusForUser( self ):
        
        if len( self._selected_terms ) == 0 and len( self._terms ) > 0:
            
            self._Hit( False, False, 0 )
            
        
        self.SetFocus()
        
    
class RecentTagsPanel( wx.Panel ):
    
    def __init__( self, parent, service_key, activate_callable, canvas_key = None ):
        
        wx.Panel.__init__( self, parent )
        
        self._service_key = service_key
        self._canvas_key = canvas_key
        
        self._new_options = HG.client_controller.new_options
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        clear_button = wx.Button( self, label = 'clear' )
        clear_button.Bind( wx.EVT_BUTTON, self.EventClear )
        
        self._recent_tags = ListBoxTagsSuggestionsFavourites( self, activate_callable, sort_tags = False )
        
        vbox.Add( clear_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._recent_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self._RefreshRecentTags()
        
        if self._canvas_key is not None:
            
            HG.client_controller.sub( self, 'CanvasHasNewMedia', 'canvas_new_display_media' )
            
        
    
    def _RefreshRecentTags( self ):
        
        def do_it( service_key ):
            
            def wx_code():
                
                if not self:
                    
                    return
                    
                
                self._recent_tags.SetTags( recent_tags )
                
            
            recent_tags = HG.client_controller.Read( 'recent_tags', service_key )
            
            wx.CallAfter( wx_code )
            
        
        HG.client_controller.CallToThread( do_it, self._service_key )
        
    
    def CanvasHasNewMedia( self, canvas_key, new_media_singleton ):
        
        if canvas_key == self._canvas_key:
            
            self._RefreshRecentTags()
            
        
    
    def EventClear( self, event ):
        
        HG.client_controller.Write( 'push_recent_tags', self._service_key, None )
        
        self._RefreshRecentTags()
        
    
    def TakeFocusForUser( self ):
        
        self._recent_tags.TakeFocusForUser()
        
    
class RelatedTagsPanel( wx.Panel ):
    
    def __init__( self, parent, service_key, media, activate_callable, canvas_key = None ):
        
        wx.Panel.__init__( self, parent )
        
        self._service_key = service_key
        self._media = media
        self._canvas_key = canvas_key
        
        self._have_fetched = False
        
        self._new_options = HG.client_controller.new_options
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._button_2 = wx.Button( self, label = 'medium' )
        self._button_2.Bind( wx.EVT_BUTTON, self.EventSuggestedRelatedTags2 )
        self._button_2.SetMinSize( ( 30, -1 ) )
        
        self._button_3 = wx.Button( self, label = 'thorough' )
        self._button_3.Bind( wx.EVT_BUTTON, self.EventSuggestedRelatedTags3 )
        self._button_3.SetMinSize( ( 30, -1 ) )
        
        self._related_tags = ListBoxTagsSuggestionsRelated( self, activate_callable )
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.Add( self._button_2, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        button_hbox.Add( self._button_3, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        vbox.Add( button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._related_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        if self._canvas_key is not None:
            
            HG.client_controller.sub( self, 'CanvasHasNewMedia', 'canvas_new_display_media' )
            
        
        self._QuickSuggestedRelatedTags()
        
    
    def _FetchRelatedTags( self, max_time_to_take ):
        
        def do_it( service_key ):
            
            def wx_code():
                
                if not self:
                    
                    return
                    
                
                self._related_tags.SetPredicates( predicates )
                
                self._have_fetched = True
                
            
            predicates = HG.client_controller.Read( 'related_tags', service_key, hash, search_tags, max_results, max_time_to_take )
            
            predicates = ClientSearch.SortPredicates( predicates )
            
            wx.CallAfter( wx_code )
            
        
        ( m, ) = self._media
        
        hash = m.GetHash()
        
        ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientData.GetMediasTagCount( self._media, tag_service_key = self._service_key, collapse_siblings = False )
        
        tags_to_count = collections.Counter()
        
        tags_to_count.update( current_tags_to_count )
        tags_to_count.update( pending_tags_to_count )
        
        search_tags = set( tags_to_count.keys() )
        
        max_results = 100
        
        HG.client_controller.CallToThread( do_it, self._service_key )
        
    
    def _QuickSuggestedRelatedTags( self ):
        
        max_time_to_take = self._new_options.GetInteger( 'related_tags_search_1_duration_ms' ) / 1000.0
        
        self._FetchRelatedTags( max_time_to_take )
        
    
    def CanvasHasNewMedia( self, canvas_key, new_media_singleton ):
        
        if canvas_key == self._canvas_key:
            
            if new_media_singleton is not None:
                
                self._media = ( new_media_singleton.Duplicate(), )
                
                self._QuickSuggestedRelatedTags()
                
            
        
    
    def EventSuggestedRelatedTags2( self, event ):
        
        max_time_to_take = self._new_options.GetInteger( 'related_tags_search_2_duration_ms' ) / 1000.0
        
        self._FetchRelatedTags( max_time_to_take )
        
    
    def EventSuggestedRelatedTags3( self, event ):
        
        max_time_to_take = self._new_options.GetInteger( 'related_tags_search_3_duration_ms' ) / 1000.0
        
        self._FetchRelatedTags( max_time_to_take )
        
    
    def TakeFocusForUser( self ):
        
        self._related_tags.TakeFocusForUser()
        
    
class FileLookupScriptTagsPanel( wx.Panel ):
    
    def __init__( self, parent, service_key, media, activate_callable, canvas_key = None ):
        
        wx.Panel.__init__( self, parent )
        
        self._service_key = service_key
        self._media = media
        self._canvas_key = canvas_key
        
        self._script_choice = ClientGUICommon.BetterChoice( self )
        
        self._script_choice.Disable()
        
        self._have_fetched = False
        
        self._fetch_button = ClientGUICommon.BetterButton( self, 'fetch tags', self.FetchTags )
        
        self._fetch_button.Disable()
        
        self._script_management = ClientGUIParsing.ScriptManagementControl( self )
        
        self._tags = ListBoxTagsSuggestionsFavourites( self, activate_callable, sort_tags = True )
        
        self._add_all = ClientGUICommon.BetterButton( self, 'add all', self._tags.ActivateAll )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._script_choice, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._fetch_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._script_management, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._add_all, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._SetTags( [] )
        
        self.SetSizer( vbox )
        
        if self._canvas_key is not None:
            
            HG.client_controller.sub( self, 'CanvasHasNewMedia', 'canvas_new_display_media' )
            
        
        self._FetchScripts()
        
    
    def _FetchScripts( self ):
        
        def do_it():
            
            def wx_code():
                
                if not self:
                    
                    return
                    
                
                script_names_to_scripts = { script.GetName() : script for script in scripts }
                
                for ( name, script ) in list(script_names_to_scripts.items()):
                    
                    self._script_choice.Append( script.GetName(), script )
                    
                
                new_options = HG.client_controller.new_options
                
                favourite_file_lookup_script = new_options.GetNoneableString( 'favourite_file_lookup_script' )
                
                if favourite_file_lookup_script in script_names_to_scripts:
                    
                    self._script_choice.SelectClientData( script_names_to_scripts[ favourite_file_lookup_script ] )
                    
                else:
                    
                    self._script_choice.Select( 0 )
                    
                
                self._script_choice.Enable()
                self._fetch_button.Enable()
                
            
            scripts = HG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP )
            
            wx.CallAfter( wx_code )
            
        
        HG.client_controller.CallToThread( do_it )
        
    
    def _SetTags( self, tags ):
        
        self._tags.SetTags( tags )
        
        if len( tags ) == 0:
            
            self._add_all.Disable()
            
        else:
            
            self._add_all.Enable()
            
        
    
    def CanvasHasNewMedia( self, canvas_key, new_media_singleton ):
        
        if canvas_key == self._canvas_key:
            
            if new_media_singleton is not None:
                
                self._media = ( new_media_singleton.Duplicate(), )
                
                self._SetTags( [] )
                
            
        
    
    def FetchTags( self ):
        
        script = self._script_choice.GetChoice()
        
        if script.UsesUserInput():
            
            message = 'Enter the custom input for the file lookup script.'
            
            with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
                
                if dlg.ShowModal() != wx.ID_OK:
                    
                    return
                    
                
                file_identifier = dlg.GetValue()
                
            
        else:
            
            ( m, ) = self._media
            
            file_identifier = script.ConvertMediaToFileIdentifier( m )
            
        
        stop_time = HydrusData.GetNow() + 30
        
        job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
        
        self._script_management.SetJobKey( job_key )
        
        HG.client_controller.CallToThread( self.THREADFetchTags, script, job_key, file_identifier )
        
    
    def TakeFocusForUser( self ):
        
        if self._have_fetched:
            
            self._tags.TakeFocusForUser()
            
        else:
            
            self._fetch_button.SetFocus()
            
        
    
    def THREADFetchTags( self, script, job_key, file_identifier ):
        
        def wx_code( tags ):
            
            if not self:
                
                return
                
            
            self._SetTags( tags )
            
            self._have_fetched = True
            
        
        parse_results = script.DoQuery( job_key, file_identifier )
        
        tags = ClientParsing.GetTagsFromParseResults( parse_results )
        
        wx.CallAfter( wx_code, tags )
        
    
class SuggestedTagsPanel( wx.Panel ):
    
    def __init__( self, parent, service_key, media, activate_callable, canvas_key = None ):
        
        wx.Panel.__init__( self, parent )
        
        self._service_key = service_key
        self._media = media
        self._canvas_key = canvas_key
        
        self._new_options = HG.client_controller.new_options
        
        layout_mode = self._new_options.GetNoneableString( 'suggested_tags_layout' )
        
        self._notebook = None
        
        if layout_mode == 'notebook':
            
            self._notebook = ClientGUICommon.BetterNotebook( self )
            
            panel_parent = self._notebook
            
        else:
            
            panel_parent = self
            
        
        panels = []
        
        favourites = self._new_options.GetSuggestedTagsFavourites( service_key )
        
        self._favourite_tags = None
        
        if len( favourites ) > 0:
            
            self._favourite_tags = ListBoxTagsSuggestionsFavourites( panel_parent, activate_callable )
            
            self._favourite_tags.SetTags( favourites )
            
            panels.append( ( 'favourites', self._favourite_tags ) )
            
        
        self._related_tags = None
        
        if self._new_options.GetBoolean( 'show_related_tags' ) and len( media ) == 1:
            
            self._related_tags = RelatedTagsPanel( panel_parent, service_key, media, activate_callable, canvas_key = self._canvas_key )
            
            panels.append( ( 'related', self._related_tags ) )
            
        
        self._file_lookup_script_tags = None
        
        if self._new_options.GetBoolean( 'show_file_lookup_script_tags' ) and len( media ) == 1:
            
            self._file_lookup_script_tags = FileLookupScriptTagsPanel( panel_parent, service_key, media, activate_callable, canvas_key = self._canvas_key )
            
            panels.append( ( 'file lookup scripts', self._file_lookup_script_tags ) )
            
        
        self._recent_tags = None
        
        if self._new_options.GetNoneableInteger( 'num_recent_tags' ) is not None:
            
            self._recent_tags = RecentTagsPanel( panel_parent, service_key, activate_callable, canvas_key = self._canvas_key )
            
            panels.append( ( 'recent', self._recent_tags ) )
            
        
        if layout_mode == 'notebook':
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            for ( name, panel ) in panels:
                
                self._notebook.AddPage( panel, name )
                
            
            hbox.Add( self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.SetSizer( hbox )
            
        elif layout_mode == 'columns':
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            for ( name, panel ) in panels:
                
                hbox.Add( panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            self.SetSizer( hbox )
            
        
        if len( panels ) == 0:
            
            self.Hide()
            
        
    
    def TakeFocusForUser( self, command ):
        
        if command == 'show_and_focus_manage_tags_favourite_tags':
            
            panel = self._favourite_tags
            
        elif command == 'show_and_focus_manage_tags_related_tags':
            
            panel = self._related_tags
            
        elif command == 'show_and_focus_manage_tags_file_lookup_script_tags':
            
            panel = self._file_lookup_script_tags
            
        elif command == 'show_and_focus_manage_tags_recent_tags':
            
            panel = self._recent_tags
            
        
        if panel is not None:
            
            if self._notebook is not None:
                
                self._notebook.SelectPage( panel )
                
            
            panel.TakeFocusForUser()
            
        
    
