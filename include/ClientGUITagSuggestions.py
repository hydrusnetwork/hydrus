import ClientConstants as CC
import ClientData
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIListBoxes
import ClientGUIParsing
import ClientParsing
import ClientSearch
import ClientThreading
import collections
import HydrusConstants as HC
import HydrusData
import HydrusGlobals
import HydrusSerialisable
import wx

class ListBoxTagsSuggestionsFavourites( ClientGUIListBoxes.ListBoxTagsStrings ):
    
    def __init__( self, parent, activate_callable, sort_tags = True ):
        
        ClientGUIListBoxes.ListBoxTagsStrings.__init__( self, parent, sort_tags = sort_tags )
        
        self._activate_callable = activate_callable
        
        width = HydrusGlobals.client_controller.GetNewOptions().GetInteger( 'suggested_tags_width' )
        
        if width is not None:
            
            self.SetMinSize( ( width, -1 ) )
            
        
    
    def _Activate( self ):
        
        if len( self._selected_terms ) > 0:
            
            tags = set( self._selected_terms )
            
            self._activate_callable( tags )
            
        
    
    def ActivateAll( self ):
        
        self._activate_callable( self.GetTags(), only_add = True )
        
    '''
    # Maybe reinclude this if per-column autoresizing is desired and not completely buggy
    def SetTags( self, tags ):
        
        ClientGUIListBoxes.ListBoxTagsStrings.SetTags( self, tags )
        
        width = HydrusGlobals.client_controller.GetNewOptions().GetInteger( 'suggested_tags_width' )
        
        if width is None:
            
            if len( self._ordered_strings ) > 0:
                
                dc = wx.MemoryDC( self._client_bmp )
                
                dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
                
                width = max( ( dc.GetTextExtent( s )[0] for s in self._ordered_strings ) )
                
                self.SetMinClientSize( ( width + 2 * self.TEXT_X_PADDING, -1 ) )
                
            
        else:
            
            self.SetMinSize( ( width, -1 ) )
            
        
        wx.PostEvent( self.GetParent(), CC.SizeChangedEvent( -1 ) )
        
    '''
class ListBoxTagsSuggestionsRelated( ClientGUIListBoxes.ListBoxTagsPredicates ):
    
    def __init__( self, parent, activate_callable ):
        
        ClientGUIListBoxes.ListBoxTags.__init__( self, parent )
        
        self._activate_callable = activate_callable
        
        width = HydrusGlobals.client_controller.GetNewOptions().GetInteger( 'suggested_tags_width' )
        
        self.SetMinSize( ( width, -1 ) )
        
    
    def _Activate( self ):
        
        if len( self._selected_terms ) > 0:
            
            tags = { predicate.GetValue() for predicate in self._selected_terms }
            
            self._activate_callable( tags )
            
        
    
    def _GetTextFromTerm( self, term ):
        
        predicate = term
        
        return predicate.GetUnicode( with_count = False )
        
    
    def SetPredicates( self, predicates ):
        
        self._Clear()
        
        for predicate in predicates:
            
            self._AppendTerm( predicate )
            
        
        self._DataHasChanged()
        
    
class RecentTagsPanel( wx.Panel ):
    
    def __init__( self, parent, service_key, activate_callable, canvas_key = None ):
        
        wx.Panel.__init__( self, parent )
        
        self._service_key = service_key
        self._canvas_key = canvas_key
        
        self._new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        clear_button = wx.Button( self, label = 'clear' )
        clear_button.Bind( wx.EVT_BUTTON, self.EventClear )
        
        self._recent_tags = ListBoxTagsSuggestionsFavourites( self, activate_callable, sort_tags = False )
        
        vbox.AddF( clear_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._recent_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self._RefreshRecentTags()
        
        if self._canvas_key is not None:
            
            HydrusGlobals.client_controller.sub( self, 'CanvasHasNewMedia', 'canvas_new_display_media' )
            
        
    
    def _RefreshRecentTags( self ):
        
        recent_tags = HydrusGlobals.client_controller.Read( 'recent_tags', self._service_key )
        
        self._recent_tags.SetTags( recent_tags )
        
    
    def CanvasHasNewMedia( self, canvas_key, new_media_singleton ):
        
        if canvas_key == self._canvas_key:
            
            self._RefreshRecentTags()
            
        
    
    def EventClear( self, event ):
        
        HydrusGlobals.client_controller.WriteSynchronous( 'push_recent_tags', self._service_key, None )
        
        self._RefreshRecentTags()
        
    
class RelatedTagsPanel( wx.Panel ):
    
    def __init__( self, parent, service_key, media, activate_callable, canvas_key = None ):
        
        wx.Panel.__init__( self, parent )
        
        self._service_key = service_key
        self._media = media
        self._canvas_key = canvas_key
        
        self._new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        button_2 = wx.Button( self, label = 'medium' )
        button_2.Bind( wx.EVT_BUTTON, self.EventSuggestedRelatedTags2 )
        button_2.SetMinSize( ( 30, -1 ) )
        
        button_3 = wx.Button( self, label = 'thorough' )
        button_3.Bind( wx.EVT_BUTTON, self.EventSuggestedRelatedTags3 )
        button_3.SetMinSize( ( 30, -1 ) )
        
        self._related_tags = ListBoxTagsSuggestionsRelated( self, activate_callable )
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.AddF( button_2, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        button_hbox.AddF( button_3, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        vbox.AddF( button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._related_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        if self._canvas_key is not None:
            
            HydrusGlobals.client_controller.sub( self, 'CanvasHasNewMedia', 'canvas_new_display_media' )
            
        
        self._QuickSuggestedRelatedTags()
        
    
    def _FetchRelatedTags( self, max_time_to_take ):
        
        ( m, ) = self._media
        
        hash = m.GetHash()
        
        ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientData.GetMediasTagCount( self._media, tag_service_key = self._service_key, collapse_siblings = False )
        
        tags_to_count = collections.Counter()
        
        tags_to_count.update( current_tags_to_count )
        tags_to_count.update( pending_tags_to_count )
        
        search_tags = set( tags_to_count.keys() )
        
        max_results = 100
        
        predicates = HydrusGlobals.client_controller.Read( 'related_tags', self._service_key, hash, search_tags, max_results, max_time_to_take )
        
        predicates = ClientSearch.SortPredicates( predicates )
        
        self._related_tags.SetPredicates( predicates )
        
    
    def _QuickSuggestedRelatedTags( self ):
        
        max_time_to_take = self._new_options.GetInteger( 'related_tags_search_1_duration_ms' ) / 1000.0
        
        self._FetchRelatedTags( max_time_to_take )
        
    
    def CanvasHasNewMedia( self, canvas_key, new_media_singleton ):
        
        if canvas_key == self._canvas_key:
            
            self._media = ( new_media_singleton.Duplicate(), )
            
            self._QuickSuggestedRelatedTags()
            
        
    
    def EventSuggestedRelatedTags2( self, event ):
        
        max_time_to_take = self._new_options.GetInteger( 'related_tags_search_2_duration_ms' ) / 1000.0
        
        self._FetchRelatedTags( max_time_to_take )
        
    
    def EventSuggestedRelatedTags3( self, event ):
        
        max_time_to_take = self._new_options.GetInteger( 'related_tags_search_3_duration_ms' ) / 1000.0
        
        self._FetchRelatedTags( max_time_to_take )
        
    
class FileLookupScriptTagsPanel( wx.Panel ):
    
    def __init__( self, parent, service_key, media, activate_callable, canvas_key = None ):
        
        wx.Panel.__init__( self, parent )
        
        self._service_key = service_key
        self._media = media
        self._canvas_key = canvas_key
        
        scripts = HydrusGlobals.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP )
        
        script_names_to_scripts = { script.GetName() : script for script in scripts }
        
        self._script_choice = ClientGUICommon.BetterChoice( self )
        
        for ( name, script ) in script_names_to_scripts.items():
            
            self._script_choice.Append( script.GetName(), script )
            
        
        new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        favourite_file_lookup_script = new_options.GetNoneableString( 'favourite_file_lookup_script' )
        
        if favourite_file_lookup_script in script_names_to_scripts:
            
            self._script_choice.SelectClientData( script_names_to_scripts[ favourite_file_lookup_script ] )
            
        else:
            
            self._script_choice.Select( 0 )
            
        
        fetch_button = ClientGUICommon.BetterButton( self, 'fetch tags', self.FetchTags )
        
        self._script_management = ClientGUIParsing.ScriptManagementControl( self )
        
        self._tags = ListBoxTagsSuggestionsFavourites( self, activate_callable, sort_tags = True )
        
        self._add_all = ClientGUICommon.BetterButton( self, 'add all', self._tags.ActivateAll )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._script_choice, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( fetch_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._script_management, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._add_all, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._SetTags( [] )
        
        self.SetSizer( vbox )
        
        if self._canvas_key is not None:
            
            HydrusGlobals.client_controller.sub( self, 'CanvasHasNewMedia', 'canvas_new_display_media' )
            
        
    
    def _SetTags( self, tags ):
        
        self._tags.SetTags( tags )
        
        if len( tags ) == 0:
            
            self._add_all.Disable()
            
        else:
            
            self._add_all.Enable()
            
        
    
    def CanvasHasNewMedia( self, canvas_key, new_media_singleton ):
        
        if canvas_key == self._canvas_key:
            
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
        
        desired_content = 'all'
        
        HydrusGlobals.client_controller.CallToThread( self.THREADFetchTags, script, job_key, file_identifier, desired_content )
        
    
    def THREADFetchTags( self, script, job_key, file_identifier, desired_content ):
        
        content_results = script.DoQuery( job_key, file_identifier, desired_content )
        
        tags = ClientParsing.GetTagsFromContentResults( content_results )
        
        wx.CallAfter( self._SetTags, tags )
        
    
class SuggestedTagsPanel( wx.Panel ):
    
    def __init__( self, parent, service_key, media, activate_callable, canvas_key = None ):
        
        wx.Panel.__init__( self, parent )
        
        self._service_key = service_key
        self._media = media
        self._canvas_key = canvas_key
        
        self._new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        layout_mode = self._new_options.GetNoneableString( 'suggested_tags_layout' )
        
        if layout_mode == 'notebook':
            
            notebook = wx.Notebook( self )
            
            panel_parent = notebook
            
        else:
            
            panel_parent = self
            
        
        panels = []
        
        favourites = self._new_options.GetSuggestedTagsFavourites( service_key )
        
        if len( favourites ) > 0:
            
            favourite_tags = ListBoxTagsSuggestionsFavourites( panel_parent, activate_callable )
            
            favourite_tags.SetTags( favourites )
            
            panels.append( ( 'favourites', favourite_tags ) )
            
        
        if self._new_options.GetBoolean( 'show_related_tags' ) and len( media ) == 1:
            
            related_tags = RelatedTagsPanel( panel_parent, service_key, media, activate_callable, canvas_key = self._canvas_key )
            
            panels.append( ( 'related', related_tags ) )
            
        
        if self._new_options.GetBoolean( 'show_file_lookup_script_tags' ) and len( media ) == 1:
            
            file_lookup_script_tags = FileLookupScriptTagsPanel( panel_parent, service_key, media, activate_callable, canvas_key = self._canvas_key )
            
            panels.append( ( 'file lookup scripts', file_lookup_script_tags ) )
            
        
        if self._new_options.GetNoneableInteger( 'num_recent_tags' ) is not None:
            
            recent_tags = RecentTagsPanel( panel_parent, service_key, activate_callable, canvas_key = self._canvas_key )
            
            panels.append( ( 'recent', recent_tags ) )
            
        
        if layout_mode == 'notebook':
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            for ( name, panel ) in panels:
                
                notebook.AddPage( panel, name )
                
            
            hbox.AddF( notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.SetSizer( hbox )
            
        elif layout_mode == 'columns':
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            for ( name, panel ) in panels:
                
                hbox.AddF( panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            self.SetSizer( hbox )
            
        
        if len( panels ) == 0:
            
            self.Hide()
            
        
    
