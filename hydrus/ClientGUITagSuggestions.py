from . import ClientConstants as CC
from . import ClientData
from . import ClientGUICommon
from . import ClientGUIDialogs
from . import ClientGUIListBoxes
from . import ClientGUIParsing
from . import ClientMedia
from . import ClientParsing
from . import ClientSearch
from . import ClientTags
from . import ClientThreading
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusSerialisable
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
from . import QtPorting as QP
from . import QtPorting as QP

class ListBoxTagsSuggestionsFavourites( ClientGUIListBoxes.ListBoxTagsStrings ):
    
    def __init__( self, parent, activate_callable, sort_tags = True ):
        
        ClientGUIListBoxes.ListBoxTagsStrings.__init__( self, parent, sort_tags = sort_tags )
        
        self._activate_callable = activate_callable
        
        width = HG.client_controller.new_options.GetInteger( 'suggested_tags_width' )
        
        if width is not None:
            
            self.setMinimumWidth( width )
            
        
    
    def _Activate( self ):
        
        if len( self._selected_terms ) > 0:
            
            tags = set( self._selected_terms )
            
            self._activate_callable( tags, only_add = True )
            
            self._RemoveSelectedTerms()
            
            self._DataHasChanged()
            
        
    
    def ActivateAll( self ):
        
        self._activate_callable( self.GetTags(), only_add = True )
        
    
    def TakeFocusForUser( self ):
        
        if len( self._selected_terms ) == 0 and len( self._terms ) > 0:
            
            self._Hit( False, False, 0 )
            
        
        self.setFocus( QC.Qt.OtherFocusReason )
        
    
class ListBoxTagsSuggestionsRelated( ClientGUIListBoxes.ListBoxTagsPredicates ):
    
    def __init__( self, parent, activate_callable ):
        
        ClientGUIListBoxes.ListBoxTagsPredicates.__init__( self, parent )
        
        self._activate_callable = activate_callable
        
        width = HG.client_controller.new_options.GetInteger( 'suggested_tags_width' )
        
        self.setMinimumWidth( width )
        
    
    def _Activate( self ):
        
        if len( self._selected_terms ) > 0:
            
            tags = { predicate.GetValue() for predicate in self._selected_terms }
            
            self._activate_callable( tags )
            
            self._RemoveSelectedTerms()
            
            self._DataHasChanged()
            
        
    
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
            
        
        self.setFocus( QC.Qt.OtherFocusReason )
        
    
class RecentTagsPanel( QW.QWidget ):
    
    def __init__( self, parent, service_key, activate_callable, canvas_key = None ):
        
        QW.QWidget.__init__( self, parent )
        
        self._service_key = service_key
        self._canvas_key = canvas_key
        
        self._new_options = HG.client_controller.new_options
        
        vbox = QP.VBoxLayout()
        
        clear_button = QW.QPushButton( 'clear', self )
        clear_button.clicked.connect( self.EventClear )
        
        self._recent_tags = ListBoxTagsSuggestionsFavourites( self, activate_callable, sort_tags = False )
        
        QP.AddToLayout( vbox, clear_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._recent_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self._RefreshRecentTags()
        
    
    def _RefreshRecentTags( self ):
        
        def do_it( service_key ):
            
            def qt_code():
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                self._recent_tags.SetTags( recent_tags )
                
            
            recent_tags = HG.client_controller.Read( 'recent_tags', service_key )
            
            QP.CallAfter( qt_code )
            
        
        HG.client_controller.CallToThread( do_it, self._service_key )
        
    
    def EventClear( self ):
        
        from . import ClientGUIDialogsQuick
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Clear recent tags?' )
        
        if result == QW.QDialog.Accepted:
            
            HG.client_controller.Write( 'push_recent_tags', self._service_key, None )
            
            self._RefreshRecentTags()
            
        
    
    def RefreshRecentTags( self ):
        
        self._RefreshRecentTags()
        
    
    def TakeFocusForUser( self ):
        
        self._recent_tags.TakeFocusForUser()
        
    
class RelatedTagsPanel( QW.QWidget ):
    
    def __init__( self, parent, service_key, media, activate_callable, canvas_key = None ):
        
        QW.QWidget.__init__( self, parent )
        
        self._service_key = service_key
        self._media = media
        self._canvas_key = canvas_key
        
        self._have_fetched = False
        
        self._new_options = HG.client_controller.new_options
        
        vbox = QP.VBoxLayout()
        
        self._button_2 = QW.QPushButton( 'medium', self )
        self._button_2.clicked.connect( self.EventSuggestedRelatedTags2 )
        self._button_2.setMinimumWidth( 30 )
        
        self._button_3 = QW.QPushButton( 'thorough', self )
        self._button_3.clicked.connect( self.EventSuggestedRelatedTags3 )
        self._button_3.setMinimumWidth( 30 )
        
        self._related_tags = ListBoxTagsSuggestionsRelated( self, activate_callable )
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._button_2, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( button_hbox, self._button_3, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._related_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _FetchRelatedTags( self, max_time_to_take ):
        
        def do_it( service_key ):
            
            def qt_code():
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                self._related_tags.SetPredicates( predicates )
                
                self._have_fetched = True
                
            
            predicates = HG.client_controller.Read( 'related_tags', service_key, hash, search_tags, max_results, max_time_to_take )
            
            predicates = ClientSearch.SortPredicates( predicates )
            
            QP.CallAfter( qt_code )
            
        
        self._related_tags.SetPredicates( [] )
        
        ( m, ) = self._media
        
        hash = m.GetHash()
        
        ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientMedia.GetMediasTagCount( self._media, self._service_key, ClientTags.TAG_DISPLAY_STORAGE )
        
        tags_to_count = collections.Counter()
        
        tags_to_count.update( current_tags_to_count )
        tags_to_count.update( pending_tags_to_count )
        
        search_tags = set( tags_to_count.keys() )
        
        max_results = 100
        
        HG.client_controller.CallToThread( do_it, self._service_key )
        
    
    def _QuickSuggestedRelatedTags( self ):
        
        max_time_to_take = self._new_options.GetInteger( 'related_tags_search_1_duration_ms' ) / 1000.0
        
        self._FetchRelatedTags( max_time_to_take )
        
    
    def EventSuggestedRelatedTags2( self ):
        
        max_time_to_take = self._new_options.GetInteger( 'related_tags_search_2_duration_ms' ) / 1000.0
        
        self._FetchRelatedTags( max_time_to_take )
        
    
    def EventSuggestedRelatedTags3( self ):
        
        max_time_to_take = self._new_options.GetInteger( 'related_tags_search_3_duration_ms' ) / 1000.0
        
        self._FetchRelatedTags( max_time_to_take )
        
    
    def SetMedia( self, media ):
        
        self._media = media
        
        self._QuickSuggestedRelatedTags()
        
    
    def TakeFocusForUser( self ):
        
        self._related_tags.TakeFocusForUser()
        
    
class FileLookupScriptTagsPanel( QW.QWidget ):
    
    def __init__( self, parent, service_key, media, activate_callable, canvas_key = None ):
        
        QW.QWidget.__init__( self, parent )
        
        self._service_key = service_key
        self._media = media
        self._canvas_key = canvas_key
        
        self._script_choice = ClientGUICommon.BetterChoice( self )
        
        self._script_choice.setEnabled( False )
        
        self._have_fetched = False
        
        self._fetch_button = ClientGUICommon.BetterButton( self, 'fetch tags', self.FetchTags )
        
        self._fetch_button.setEnabled( False )
        
        self._script_management = ClientGUIParsing.ScriptManagementControl( self )
        
        self._tags = ListBoxTagsSuggestionsFavourites( self, activate_callable, sort_tags = True )
        
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
        
    
    def _FetchScripts( self ):
        
        def do_it():
            
            def qt_code():
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                script_names_to_scripts = { script.GetName() : script for script in scripts }
                
                for ( name, script ) in list(script_names_to_scripts.items()):
                    
                    self._script_choice.addItem( script.GetName(), script )
                    
                
                new_options = HG.client_controller.new_options
                
                favourite_file_lookup_script = new_options.GetNoneableString( 'favourite_file_lookup_script' )
                
                if favourite_file_lookup_script in script_names_to_scripts:
                    
                    self._script_choice.SetValue( script_names_to_scripts[ favourite_file_lookup_script ] )
                    
                else:
                    
                    self._script_choice.setCurrentIndex( 0 )
                    
                
                self._script_choice.setEnabled( True )
                self._fetch_button.setEnabled( True )
                
            
            scripts = HG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP )
            
            QP.CallAfter( qt_code )
            
        
        HG.client_controller.CallToThread( do_it )
        
    
    def _SetTags( self, tags ):
        
        self._tags.SetTags( tags )
        
        if len( tags ) == 0:
            
            self._add_all.setEnabled( False )
            
        else:
            
            self._add_all.setEnabled( True )
            
        
    
    def FetchTags( self ):
        
        script = self._script_choice.GetValue()
        
        if script.UsesUserInput():
            
            message = 'Enter the custom input for the file lookup script.'
            
            with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
                
                if dlg.exec() != QW.QDialog.Accepted:
                    
                    return
                    
                
                file_identifier = dlg.GetValue()
                
            
        else:
            
            ( m, ) = self._media
            
            file_identifier = script.ConvertMediaToFileIdentifier( m )
            
        
        stop_time = HydrusData.GetNow() + 30
        
        job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
        
        self._script_management.SetJobKey( job_key )
        
        self._SetTags( set() )
        
        HG.client_controller.CallToThread( self.THREADFetchTags, script, job_key, file_identifier )
        
    
    def SetMedia( self, media ):
        
        self._media = media
        
    
    def TakeFocusForUser( self ):
        
        if self._have_fetched:
            
            self._tags.TakeFocusForUser()
            
        else:
            
            self._fetch_button.setFocus( QC.Qt.OtherFocusReason )
            
        
    
    def THREADFetchTags( self, script, job_key, file_identifier ):
        
        def qt_code( tags ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._SetTags( tags )
            
            self._have_fetched = True
            
        
        parse_results = script.DoQuery( job_key, file_identifier )
        
        tags = ClientParsing.GetTagsFromParseResults( parse_results )
        
        QP.CallAfter( qt_code, tags )
        
    
class SuggestedTagsPanel( QW.QWidget ):
    
    def __init__( self, parent, service_key, media, activate_callable, canvas_key = None ):
        
        QW.QWidget.__init__( self, parent )
        
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
            
        
        hbox = QP.HBoxLayout()
        
        if layout_mode == 'notebook':
            
            for ( name, panel ) in panels:
                
                self._notebook.addTab( panel, name )
                
            
            QP.AddToLayout( hbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
            
        elif layout_mode == 'columns':
            
            for ( name, panel ) in panels:
                
                QP.AddToLayout( hbox, panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
        
        self.setLayout( hbox )
        
        if len( panels ) == 0:
            
            self.hide()
            
        
    
    def SetMedia( self, media ):
        
        self._media = media
        
        if self._recent_tags is not None:
            
            self._recent_tags.RefreshRecentTags()
            
        
        if self._file_lookup_script_tags is not None:
            
            self._file_lookup_script_tags.SetMedia( media )
            
        
        if self._related_tags is not None:
            
            self._related_tags.SetMedia( media )
            
        
    
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
            
        
    
