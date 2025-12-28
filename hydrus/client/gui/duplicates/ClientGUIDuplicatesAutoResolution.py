import collections.abc
import threading

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientThreading
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.duplicates import ClientDuplicatesAutoResolutionComparators
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext
from hydrus.client.files.images import ClientVisualData
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.duplicates import ClientGUIDuplicatesAutoResolutionRulePreview
from hydrus.client.gui.duplicates import ClientGUIDuplicatesAutoResolutionRuleReview
from hydrus.client.gui.duplicates import ClientGUIDuplicatesContentMergeOptions
from hydrus.client.gui.duplicates import ClientGUIPotentialDuplicatesSearchContext
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.metadata import ClientGUIMetadataConditional
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.gui.widgets import ClientGUINumberTest
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchPredicate

class EditDuplicatesAutoResolutionRulesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, duplicates_auto_resolution_rules: collections.abc.Collection[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ] ):
        
        super().__init__( parent )
        
        menu_template_items = []
        
        call = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DUPLICATES_AUTO_RESOLUTION )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the duplicates auto-resolution help', 'Open the help page for duplicates auto-resolution in your web browser.', call ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        self._duplicates_auto_resolution_rules_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_EDIT_DUPLICATES_AUTO_RESOLUTION_RULES.ID, self._ConvertRuleToDisplayTuple, self._ConvertRuleToSortTuple )
        
        self._duplicates_auto_resolution_rules = ClientGUIListCtrl.BetterListCtrlTreeView( self._duplicates_auto_resolution_rules_panel, 12, model, use_simple_delete = True, activation_callback = self._Edit )
        
        self._duplicates_auto_resolution_rules_panel.SetListCtrl( self._duplicates_auto_resolution_rules )
        
        self._duplicates_auto_resolution_rules_panel.AddButton( 'add suggested', self._AddSuggested )
        self._duplicates_auto_resolution_rules_panel.AddButton( 'add', self._Add )
        self._duplicates_auto_resolution_rules_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        self._duplicates_auto_resolution_rules_panel.AddDeleteButton()
        self._duplicates_auto_resolution_rules_panel.AddImportExportButtons( ( ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, ), self._ImportRule )
        
        #
        
        self._duplicates_auto_resolution_rules.AddDatas( duplicates_auto_resolution_rules )
        
        self._duplicates_auto_resolution_rules.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        st_warning = ClientGUICommon.BetterStaticText( self, 'THIS IS AN ADVANCED SYSTEM. READ THE HELP DOCUMENTATION. DO NOT CREATE A NEW RULE WITHOUT UNDERSTANDING AND PREVIEWING WHAT IT WILL DO' )
        st_warning.setWordWrap( True )
        st_warning.setObjectName( 'HydrusWarning' )
        st_warning.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        QP.AddToLayout( vbox, st_warning, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        label = 'Rules are worked on in smart alphabetical name order, so if you have overlapping test domains and want to force precedence, try naming them "1 - " and "2 - " etc..'
        
        st = ClientGUICommon.BetterStaticText( self, label )
        st.setWordWrap( True )
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._duplicates_auto_resolution_rules_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _Add( self ):
        
        name = 'new rule'
        
        duplicates_auto_resolution_rule = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( name )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
        predicates = [
            ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = ( HC.GENERAL_IMAGE, ) ),
            ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) ),
            ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) ),
        ]
        
        file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext(
            location_context = location_context,
            predicates = predicates
        )
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( file_search_context_1 )
        potential_duplicates_search_context.SetDupeSearchType( ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH )
        potential_duplicates_search_context.SetPixelDupesPreference( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED )
        potential_duplicates_search_context.SetMaxHammingDistance( 0 )
        
        duplicates_auto_resolution_rule.SetPotentialDuplicatesSearchContext( potential_duplicates_search_context )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit rule' ) as dlg:
            
            panel = EditDuplicatesAutoResolutionRulePanel( dlg, duplicates_auto_resolution_rule )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                duplicates_auto_resolution_rule = panel.GetValue()
                
                duplicates_auto_resolution_rule.SetNonDupeName( self._GetExistingNames(), do_casefold = True )
                
                self._duplicates_auto_resolution_rules.AddData( duplicates_auto_resolution_rule, select_sort_and_scroll = True )
                
            
        
    
    def _AddSuggested( self ):
        
        suggested_rules = ClientDuplicatesAutoResolution.GetDefaultRuleSuggestions()
        
        choice_tuples = [ ( rule.GetName(), rule ) for rule in suggested_rules ]
        
        try:
            
            duplicates_auto_resolution_rule = ClientGUIDialogsQuick.SelectFromList( self, 'Select which to add', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        self._ImportRule( duplicates_auto_resolution_rule )
        
    
    def _ConvertRuleToDisplayTuple( self, duplicates_auto_resolution_rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        name = duplicates_auto_resolution_rule.GetName()
        rule_summary = duplicates_auto_resolution_rule.GetRuleSummary()
        pair_selector_summary = duplicates_auto_resolution_rule.GetPairSelectorSummary()
        action_summary = duplicates_auto_resolution_rule.GetActionSummary()
        search_status = duplicates_auto_resolution_rule.GetSearchSummary()
        
        operation_mode = duplicates_auto_resolution_rule.GetOperationMode()
        
        pretty_operation_mode = ClientDuplicatesAutoResolution.duplicates_auto_resolution_rule_operation_mode_str_lookup[ operation_mode ]
        
        if duplicates_auto_resolution_rule.IsPaused():
            
            pretty_operation_mode += ' - paused'
            
        
        return ( name, rule_summary, pair_selector_summary, action_summary, search_status, pretty_operation_mode )
        
    
    def _ConvertRuleToSortTuple( self, duplicates_auto_resolution_rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        ( name, rule_summary, pair_selector_summary, action_summary, search_status, pretty_operation_mode ) = self._ConvertRuleToDisplayTuple( duplicates_auto_resolution_rule )
        
        sort_name = HydrusText.HumanTextSortKey( name )
        
        return ( sort_name, rule_summary, pair_selector_summary, action_summary, search_status, pretty_operation_mode )
        
    
    def _Edit( self ):
        
        duplicates_auto_resolution_rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule | None = self._duplicates_auto_resolution_rules.GetTopSelectedData()
        
        if duplicates_auto_resolution_rule is None:
            
            return
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit duplicates auto-resolution rule' ) as dlg:
            
            panel = EditDuplicatesAutoResolutionRulePanel( dlg, duplicates_auto_resolution_rule )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_duplicates_auto_resolution_rule = panel.GetValue()
                
                if edited_duplicates_auto_resolution_rule.GetName() != duplicates_auto_resolution_rule.GetName():
                    
                    existing_names = self._GetExistingNames()
                    
                    existing_names.discard( duplicates_auto_resolution_rule.GetName() )
                    
                    edited_duplicates_auto_resolution_rule.SetNonDupeName( existing_names, do_casefold = True )
                    
                
                self._duplicates_auto_resolution_rules.ReplaceData( duplicates_auto_resolution_rule, edited_duplicates_auto_resolution_rule, sort_and_scroll = True )
                
            
        
    
    def _GetExistingNames( self ):
        
        return { duplicates_auto_resolution_rule.GetName() for duplicates_auto_resolution_rule in self._duplicates_auto_resolution_rules.GetData() }
        
    
    def _ImportRule( self, duplicates_auto_resolution_rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        duplicates_auto_resolution_rule.SetNonDupeName( self._GetExistingNames(), do_casefold = True )
        
        # this is already sorted for the "add suggested" rules, but isn't for duplicate/clipboard/png import. we'll do it anyway to be safe and cover all situations
        duplicates_auto_resolution_rule.SetId( ClientDuplicatesAutoResolution.NEW_RULE_SESSION_ID )
        
        ClientDuplicatesAutoResolution.NEW_RULE_SESSION_ID -= 1
        
        self._duplicates_auto_resolution_rules.AddData( duplicates_auto_resolution_rule, select_sort_and_scroll = True )
        
    
    def GetValue( self ) -> list[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ]:
        
        return self._duplicates_auto_resolution_rules.GetData()
        
    

class EditDuplicatesAutoResolutionRulePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, duplicates_auto_resolution_rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        super().__init__( parent )
        
        self._duplicates_auto_resolution_rule = duplicates_auto_resolution_rule
        
        self._rule_panel = ClientGUICommon.StaticBox( self, 'rule' )
        
        self._name = QW.QLineEdit( self._rule_panel )
        
        self._paused = QW.QCheckBox( self )
        
        self._operation_mode = ClientGUICommon.BetterChoice( self._rule_panel )
        
        for operation_mode in [
            ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION,
            ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_FULLY_AUTOMATIC
        ]:
            
            self._operation_mode.addItem( ClientDuplicatesAutoResolution.duplicates_auto_resolution_rule_operation_mode_desc_lookup[ operation_mode ], operation_mode )
            
        
        self._max_pending_pairs = ClientGUICommon.NoneableSpinCtrl( self._rule_panel, 512, min = 1 )
        self._max_pending_pairs.setToolTip( ClientGUIFunctions.WrapToolTip( 'Testing needs CPU time. It is generally good to keep a semi-automatic pending queue short and snappy in case you need to change anything (thus resetting the queue) in future.' ) )
        
        self._main_notebook = ClientGUICommon.BetterNotebook( self )
        
        #
        
        self._search_panel = QW.QWidget( self._main_notebook )
        
        potential_duplicates_search_context = duplicates_auto_resolution_rule.GetPotentialDuplicatesSearchContext()
        
        self._potential_duplicates_search_context = ClientGUIPotentialDuplicatesSearchContext.EditPotentialDuplicatesSearchContextPanel( self._search_panel, potential_duplicates_search_context, put_searches_side_by_side = True )
        
        #
        
        self._selector_panel = QW.QWidget( self._main_notebook )
        
        pair_selector = duplicates_auto_resolution_rule.GetPairSelector()
        
        self._pair_selector = EditPairSelectorWidget( self._selector_panel, pair_selector )
        
        #
        
        self._actions_panel = QW.QWidget( self._main_notebook )
        
        action = duplicates_auto_resolution_rule.GetAction()
        ( delete_a, delete_b ) = duplicates_auto_resolution_rule.GetDeleteInfo()
        duplicates_content_merge_options = duplicates_auto_resolution_rule.GetDuplicateContentMergeOptions()
        
        self._edit_actions_panel = EditPairActionsWidget( self._actions_panel, action, delete_a, delete_b, duplicates_content_merge_options )
        
        #
        
        self._preview_panel = QW.QWidget( self._main_notebook )
        
        self._full_preview_panel = ClientGUIDuplicatesAutoResolutionRulePreview.PreviewPanel( self._preview_panel, self.GetValue )
        
        #
        
        self._name.setText( self._duplicates_auto_resolution_rule.GetName() )
        self._paused.setChecked( self._duplicates_auto_resolution_rule.IsPaused() )
        self._operation_mode.SetValue( self._duplicates_auto_resolution_rule.GetOperationMode() )
        self._max_pending_pairs.SetValue( self._duplicates_auto_resolution_rule.GetMaxPendingPairs() )
        
        #
        
        label = 'First we have to find some duplicate pairs to test. This can be system:everything if you like, but it is best to narrow it down if you can.'
        label += '\n\n'
        label += 'It is a good idea to keep a "system:filetype is image" in here to ensure you do not include some PSD files by accident etc..'
        
        st = ClientGUICommon.BetterStaticText( self._search_panel, label = label )
        
        st.setWordWrap( True )
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._potential_duplicates_search_context, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._search_panel.setLayout( vbox )
        
        #
        
        
        vbox = QP.VBoxLayout()
        
        label = 'Now, for each pair that matches our search, we need to determine if their differences (or similarities!) are clear enough that we can confidently make an automatic decision. The pairs are also unordered, so if we are setting one file to be a better duplicate of the other, we also need to define which is the A (usually the better) and the B (usually the worse).'
        label += '\n\n'
        label += 'The client will test the incoming pair both ways around ([1,2] and [2,1]) against these rules, and if they fit either way, that "AB" pair order is set and the action is applied. If the pair cannot fit into the rules either way, the test is considered failed and no changes are made. If there are no rules, all pairs will be actioned--but remember you need at least one clear A- or B-defining rule for a "better/worse duplicates" action.'
        
        st = ClientGUICommon.BetterStaticText( self._selector_panel, label )
        
        st.setWordWrap( True )
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._pair_selector, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._selector_panel.setLayout( vbox )
        
        #
        
        label = 'And now we have pairs to action, what should we do?'
        label += '\n\n'
        label += 'Note that in the auto-resolution filter, "always archive both" will be treated as "if one is archived, archive the other".'
        
        st = ClientGUICommon.BetterStaticText( self._actions_panel, label = label )
        
        st.setWordWrap( True )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._edit_actions_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self._actions_panel.setLayout( vbox )
        
        #
        
        label = 'Let\'s review our rule to make sure it makes sense.'
        
        st = ClientGUICommon.BetterStaticText( self._preview_panel, label = label )
        
        st.setWordWrap( True )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._full_preview_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._preview_panel.setLayout( vbox )
        
        #
        
        self._main_notebook.addTab( self._search_panel, 'search' )
        self._main_notebook.addTab( self._selector_panel, 'comparison' )
        self._main_notebook.addTab( self._actions_panel, 'action' )
        self._main_notebook.addTab( self._preview_panel, 'preview' )
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'paused: ', self._paused ) )
        rows.append( ( 'operation: ', self._operation_mode ) )
        rows.append( ( 'max pending pairs (semi-automatic only): ', self._max_pending_pairs ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._rule_panel, rows )
        
        self._rule_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._rule_panel.Add( self._main_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._rule_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._operation_mode.currentIndexChanged.connect( self._OperationModeChanged )
        
        self._main_notebook.currentChanged.connect( self._CurrentPageChanged )
        
        self._OperationModeChanged()
        
        self._CurrentPageChanged()
        
    
    def _CurrentPageChanged( self ):
        
        page = self._main_notebook.currentWidget()
        
        if page == self._search_panel:
            
            self._potential_duplicates_search_context.PageShown()
            
        else:
            
            self._potential_duplicates_search_context.PageHidden()
            
        
        if page == self._preview_panel:
            
            self._full_preview_panel.PageShown()
            
        else:
            
            self._full_preview_panel.PageIsHidden()
            
        
    
    def _OperationModeChanged( self ):
        
        operation_mode = self._operation_mode.GetValue()
        
        self._max_pending_pairs.setEnabled( operation_mode == ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION )
        
    
    def GetValue( self ):
        
        name = self._name.text()
        
        duplicates_auto_resolution_rule = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( name )
        
        duplicates_auto_resolution_rule.SetPaused( self._paused.isChecked() )
        
        duplicates_auto_resolution_rule.SetOperationMode( self._operation_mode.GetValue() )
        
        duplicates_auto_resolution_rule.SetPotentialDuplicatesSearchContext( self._potential_duplicates_search_context.GetValue() )
        
        duplicates_auto_resolution_rule.SetMaxPendingPairs( self._max_pending_pairs.GetValue() )
        
        #
        
        pair_selector = self._pair_selector.GetValue()
        
        duplicates_auto_resolution_rule.SetPairSelector( pair_selector )
        
        #
        
        # action
        
        ( action, delete_a, delete_b, duplicate_content_merge_options ) = self._edit_actions_panel.GetValue()
        
        if action == HC.DUPLICATE_BETTER and not pair_selector.CanDetermineBetter():
            
            raise HydrusExceptions.VetoException( 'Hey, you have the action set to "better/worse duplicate" but the comparison step has no way to figure out A or B! You need to add at least one step that specifies either A or B so the rule knows which way around to apply the action. If there is no easy determination, perhaps "set as same quality" is more appropriate?' )
            
        
        duplicates_auto_resolution_rule.SetAction( action )
        duplicates_auto_resolution_rule.SetDeleteInfo( delete_a, delete_b )
        duplicates_auto_resolution_rule.SetDuplicateContentMergeOptions( duplicate_content_merge_options )
        
        #
        
        duplicates_auto_resolution_rule.SetId( self._duplicates_auto_resolution_rule.GetId() )
        duplicates_auto_resolution_rule.SetCountsCache( self._duplicates_auto_resolution_rule.GetCountsCacheDuplicate() )
        
        return duplicates_auto_resolution_rule
        
    

class EditPairActionsWidget( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, action: int, delete_a: bool, delete_b: bool, duplicates_content_merge_options: ClientDuplicates.DuplicateContentMergeOptions | None ):
        
        super().__init__( parent, 'pair actions' )
        
        self._action = ClientGUICommon.BetterChoice( self )
        
        for duplicate_type in [
            HC.DUPLICATE_BETTER,
            HC.DUPLICATE_SAME_QUALITY,
            HC.DUPLICATE_ALTERNATE,
            HC.DUPLICATE_FALSE_POSITIVE
        ]:
            
            self._action.addItem( HC.duplicate_type_auto_resolution_action_description_lookup[ duplicate_type ], duplicate_type )
            
        
        self._delete_a = QW.QCheckBox( self )
        self._delete_b = QW.QCheckBox( self )
        
        self._use_default_duplicates_content_merge_options = QW.QCheckBox( self )
        
        self._custom_duplicate_content_merge_options = ClientGUIDuplicatesContentMergeOptions.EditDuplicateContentMergeOptionsWidget( self, HC.DUPLICATE_BETTER, ClientDuplicates.DuplicateContentMergeOptions(), can_expand = True, start_expanded = False )
        
        # TODO: a lovely panel that handles merge options lad
        
        # I really want this to be a live in-place widget, which means we'll have to dynamically update this guy with action as we switch things!!
        # also, we'll want to disable/enable with the checkbox
        # also, we'll want a favourites system, which the new staticbox could do
        
        #
        
        self._action.SetValue( action )
        self._delete_a.setChecked( delete_a )
        self._delete_b.setChecked( delete_b )
        self._use_default_duplicates_content_merge_options.setChecked( duplicates_content_merge_options is None )
        
        if duplicates_content_merge_options is None:
            
            duplicates_content_merge_options = CG.client_controller.new_options.GetDuplicateContentMergeOptions( action )
            
        else:
            
            self._custom_duplicate_content_merge_options.ExpandCollapse()
            
        
        self._custom_duplicate_content_merge_options.SetValue( action, duplicates_content_merge_options )
        
        #
        
        rows = []
        
        rows.append( ( 'action: ', self._action ) )
        rows.append( ( 'delete A: ', self._delete_a ) )
        rows.append( ( 'delete B: ', self._delete_b ) )
        rows.append( ( 'use default content merge options for action: ', self._use_default_duplicates_content_merge_options ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self.Add( self._custom_duplicate_content_merge_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._use_default_duplicates_content_merge_options.clicked.connect( self._UpdateMergeWidgetEnabled )
        self._action.currentIndexChanged.connect( self._UpdateActionControls )
        
        self._UpdateMergeWidgetEnabled()
        
    
    def _UpdateActionControls( self ):
        
        action = self._action.GetValue()
        
        current_action = self._custom_duplicate_content_merge_options.GetDuplicateAction()
        
        if current_action != action:
            
            duplicates_content_merge_options = CG.client_controller.new_options.GetDuplicateContentMergeOptions( action )
            
            self._custom_duplicate_content_merge_options.SetValue( action, duplicates_content_merge_options )
            
        
    
    def _UpdateMergeWidgetEnabled( self ):
        
        we_can_edit_it = not self._use_default_duplicates_content_merge_options.isChecked()
        
        self._custom_duplicate_content_merge_options.setEnabled( we_can_edit_it )
        
        if we_can_edit_it:
            
            self._UpdateActionControls()
            
            if not self._custom_duplicate_content_merge_options.IsExpanded():
                
                self._custom_duplicate_content_merge_options.ExpandCollapse()
                
            
        
    
    def GetValue( self ):
        
        action = self._action.GetValue()
        delete_a = self._delete_a.isChecked()
        delete_b = self._delete_b.isChecked()
        
        if self._use_default_duplicates_content_merge_options.isChecked():
            
            duplicate_content_merge_options = None
            
        else:
            
            duplicate_content_merge_options = self._custom_duplicate_content_merge_options.GetValue()
            
        
        return ( action, delete_a, delete_b, duplicate_content_merge_options )
        
    

class EditPairComparatorOneFilePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, pair_comparator: ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile ):
        
        super().__init__( parent )
        
        self._looking_at = ClientGUICommon.BetterChoice( self )
        
        self._looking_at.addItem( 'A will match these', ClientDuplicatesAutoResolutionComparators.LOOKING_AT_A )
        self._looking_at.addItem( 'B will match these', ClientDuplicatesAutoResolutionComparators.LOOKING_AT_B )
        self._looking_at.addItem( 'either will match these', ClientDuplicatesAutoResolutionComparators.LOOKING_AT_EITHER )
        
        self._metadata_conditional = ClientGUIMetadataConditional.EditMetadataConditionalPanel( self, pair_comparator.GetMetadataConditional() )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._metadata_conditional, 64 )
        
        self._metadata_conditional.setMinimumWidth( width )
        
        #
        
        self._looking_at.SetValue( pair_comparator.GetLookingAt() )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._looking_at, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._metadata_conditional, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        CG.client_controller.CallAfterQtSafe( self, ClientGUIFunctions.SetFocusLater, self._metadata_conditional )
        
    
    def GetValue( self ):
        
        looking_at = self._looking_at.GetValue()
        metadata_conditional = self._metadata_conditional.GetValue()
        
        pair_comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        pair_comparator.SetLookingAt( looking_at )
        pair_comparator.SetMetadataConditional( metadata_conditional )
        
        return pair_comparator
        
    

class EditComparatorList( ClientGUIListBoxes.AddEditDeleteListBox ):
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent, 8, self._PairComparatorToPretty, self._AddComparator, self._EditComparator )
        
        self.AddImportExportButtons( ( ClientDuplicatesAutoResolutionComparators.PairComparator, ) )
        
    
    def _AddComparator( self ):
        
        choice_tuples = [
            ( 'test A or B', ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile(), 'A comparator that tests one file at a time using system predicates.' ),
            ( 'test A against B using file info', ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo(), 'A comparator that performs a number test on the width, filesize, etc.. of A vs B.' ),
            ( 'test if A and B are visual duplicates', ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeVisualDuplicates( acceptable_confidence = ClientVisualData.VISUAL_DUPLICATES_RESULT_ALMOST_CERTAINLY ), 'A comparator that examines the differences in the images\' shape and colour to determine if they are visual duplicates.' )
        ]
        
        additional_comparators = [
            ( ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME ), 'A comparator that tests if the two files share the same filetype.' ),
            ( ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_DIFFERS ), 'A comparator that tests if the two files have different filetype.' ),
            ( ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_A_HAS_CLEARLY_BETTER_JPEG_QUALITY ), 'A comparator that tests if A has a non-trivially higher apparent jpeg quality than B. The difference corresponds to about one label-step of quality as you see in the duplicate filter. If either file is not a jpeg, it fails.' ),
            ( ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_HAS_EXIF_SAME ), 'A comparator that tests if the two files either both have or both do not have some amount of EXIF data.' ),
            ( ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_HAS_ICC_PROFILE_SAME ), 'A comparator that tests if the two files either both have or both do not have some amount of ICC Profile data.' ),
        ]
        
        choice_tuples.extend(
            ( ( comparator.GetSummary(), comparator, description ) for ( comparator, description ) in additional_comparators )
        )
        
        choice_tuples.append(
            ( 'OR Comparator', ClientDuplicatesAutoResolutionComparators.PairComparatorOR( [] ), 'A comparator that tests an OR of several sub-comparators.' )
        )
        
        choice_tuples.append(
            ( 'AND Comparator', ClientDuplicatesAutoResolutionComparators.PairComparatorAND( [] ), 'A comparator that tests an AND of several sub-comparators. Use when you need to mix several different comparators within an OR.' )
        )
        
        try:
            
            comparator = ClientGUIDialogsQuick.SelectFromListButtons( self, 'Which type of comparator?', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            raise
            
        
        return self._EditComparator( comparator )
        
    
    def _EditComparator( self, comparator: ClientDuplicatesAutoResolutionComparators.PairComparator ):
        
        if isinstance( comparator, ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile ):
            
            title = 'edit one-file comparator'
            
        elif isinstance( comparator, ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo ):
            
            title = 'edit relative comparator'
            
        elif isinstance( comparator, ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeVisualDuplicates ):
            
            title = 'edit visual duplicates comparator'
            
        elif isinstance( comparator, ClientDuplicatesAutoResolutionComparators.PairComparatorOR ):
            
            title = 'edit OR comparator'
            
        elif isinstance( comparator, ClientDuplicatesAutoResolutionComparators.PairComparatorAND ):
            
            title = 'edit AND comparator'
            
        elif isinstance( comparator, ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded ):
            
            return comparator
            
        else:
            
            raise NotImplementedError( 'Unknown comparator type!' )
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            if isinstance( comparator, ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile ):
                
                panel = EditPairComparatorOneFilePanel( dlg, comparator )
                
            elif isinstance( comparator, ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo ):
                
                panel = EditPairComparatorRelativeFileinfoPanel( dlg, comparator )
                
            elif isinstance( comparator, ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeVisualDuplicates ):
                
                panel = EditPairComparatorRelativeVisualDuplicatesPanel( dlg, comparator )
                
            elif isinstance( comparator, ClientDuplicatesAutoResolutionComparators.PairComparatorOR ):
                
                panel = EditPairComparatorOR( dlg, comparator )
                
            elif isinstance( comparator, ClientDuplicatesAutoResolutionComparators.PairComparatorAND ):
                
                panel = EditPairComparatorAND( dlg, comparator )
                
            else:
                
                raise NotImplementedError( 'Unknown comparator type!' )
                
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_comparator = panel.GetValue()
                
                return edited_comparator
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
    
    def _PairComparatorToPretty( self, pair_comparator: ClientDuplicatesAutoResolutionComparators.PairComparator ):
        
        return pair_comparator.GetSummary()
        
    

class EditPairComparatorAND( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, pair_comparator: ClientDuplicatesAutoResolutionComparators.PairComparatorAND ):
        
        super().__init__( parent )
        
        self._comparators = EditComparatorList( self )
        
        self._comparators.AddDatas( pair_comparator.GetComparators() )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._comparators, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        comparators = self._comparators.GetData()
        
        pair_comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorAND( comparators )
        
        return pair_comparator
        
    

class EditPairComparatorOR( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, pair_comparator: ClientDuplicatesAutoResolutionComparators.PairComparatorOR ):
        
        super().__init__( parent )
        
        self._comparators = EditComparatorList( self )
        
        self._comparators.AddDatas( pair_comparator.GetComparators() )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._comparators, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        comparators = self._comparators.GetData()
        
        pair_comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOR( comparators )
        
        return pair_comparator
        
    

class EditPairComparatorRelativeFileinfoPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, pair_comparator: ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo ):
        
        super().__init__( parent )
        
        # note in a label that for duration, the units is ms
        
        self._system_predicate = ClientGUICommon.BetterChoice( self )
        
        for predicate_type in ClientSearchPredicate.PREDICATE_TYPES_WE_CAN_EXTRACT_FROM_MEDIA_RESULTS:
            
            predicate = ClientSearchPredicate.Predicate( predicate_type = predicate_type )
            
            self._system_predicate.addItem( predicate.ToString(), predicate )
            
        
        self._warning_label = ClientGUICommon.BetterStaticText( self, label = 'initialising' )
        self._warning_label.setWordWrap( True )
        self._warning_label.setVisible( False )
        
        self._system_pred_types_to_warning_label_texts = {
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FRAMERATE : 'Framerate is an approximation (e.g. it might be calculated as 30.05fps for one file but 29.98fps for another), so be careful with < and > here. Best to try for some padding, like "A framerate > 1.1x B".'
        }
        
        self._time_panel = QW.QWidget( self )
        
        allowed_operators = [
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN_OR_EQUAL_TO,
            ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_NOT_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN_OR_EQUAL_TO,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE
        ]
        
        self._time_number_test = ClientGUITime.NumberTestWidgetTimestamp(
            self._time_panel,
            allowed_operators = allowed_operators,
            swap_in_string_for_value = 'B'
        )
        
        self._time_delta = ClientGUITime.TimeDeltaWidget( self, min = - 86400 * 10000, days = True, hours = True, minutes = True, seconds = True, milliseconds = True, negative_allowed = True )
        
        self._time_delta.SetValue( 0 )
        
        #
        
        self._duration_panel = QW.QWidget( self )
        
        allowed_operators = [
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN_OR_EQUAL_TO,
            ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_NOT_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN_OR_EQUAL_TO,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT
        ]
        
        self._duration_number_test = ClientGUITime.NumberTestWidgetDuration(
            self._duration_panel,
            allowed_operators = allowed_operators,
            swap_in_string_for_value = 'B'
        )
        
        self._duration_multiplier = QW.QDoubleSpinBox( self._duration_panel )
        self._duration_multiplier.setDecimals( 2 )
        self._duration_multiplier.setSingleStep( 0.01 )
        self._duration_multiplier.setMinimum( -10000 )
        self._duration_multiplier.setMaximum( 10000 )
        
        self._duration_multiplier.setMinimumWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._duration_multiplier, 11 ) )
        
        self._duration_multiplier.setValue( 1.00 )
        
        self._duration_delta = ClientGUITime.TimeDeltaWidget( self, min = - 86400 * 10000, minutes = True, seconds = True, milliseconds = True, negative_allowed = True )
        
        self._duration_delta.SetValue( 0 )
        
        #
        
        self._normal_panel = QW.QWidget( self )
        
        allowed_operators = [
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN_OR_EQUAL_TO,
            ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_NOT_EQUAL,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN_OR_EQUAL_TO,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT
        ]
        
        self._normal_number_test = ClientGUINumberTest.NumberTestWidget(
            self._normal_panel,
            allowed_operators = allowed_operators,
            swap_in_string_for_value = 'B'
        )
        
        self._normal_multiplier = QW.QDoubleSpinBox( self._normal_panel )
        self._normal_multiplier.setDecimals( 2 )
        self._normal_multiplier.setSingleStep( 0.01 )
        self._normal_multiplier.setMinimum( -10000 )
        self._normal_multiplier.setMaximum( 10000 )
        
        self._normal_multiplier.setMinimumWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._normal_multiplier, 11 ) )
        
        self._normal_multiplier.setValue( 1.00 )
        
        self._normal_delta = ClientGUICommon.BetterSpinBox( self._normal_panel, min = -100000000, max = 100000000 )
        
        self._normal_delta.setMinimumWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._normal_delta, 13 ) )
        
        self._normal_delta.setValue( 0 )
        
        #
        
        self._fuzzy_panel = QW.QWidget( self )
        
        allowed_operators = [
            ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE,
            ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT
        ]
        
        self._fuzzy_number_test = ClientGUINumberTest.NumberTestWidget(
            self._fuzzy_panel,
            allowed_operators = allowed_operators,
            swap_in_string_for_value = 'B'
        )
        
        self._fuzzy_multiplier = QW.QDoubleSpinBox( self._fuzzy_panel )
        self._fuzzy_multiplier.setDecimals( 2 )
        self._fuzzy_multiplier.setSingleStep( 0.01 )
        self._fuzzy_multiplier.setMinimum( -10000 )
        self._fuzzy_multiplier.setMaximum( 10000 )
        
        self._fuzzy_multiplier.setMinimumWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._fuzzy_multiplier, 11 ) )
        
        self._fuzzy_multiplier.setValue( 1.00 )
        
        self._fuzzy_delta = ClientGUICommon.BetterSpinBox( self._fuzzy_panel, min = -100000000, max = 100000000 )
        
        self._fuzzy_delta.setMinimumWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._fuzzy_delta, 13 ) )
        
        self._fuzzy_delta.setValue( 0 )
        
        #
        
        self._live_value_st = ClientGUICommon.BetterStaticText( self )
        
        #
        
        self._SetValue( pair_comparator )
        
        #
        
        rows = []
        
        rows.append( ( 'operator: ', self._time_number_test ) )
        rows.append( ( 'delta (optional)', self._time_delta ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._time_panel, rows )
        
        self._time_panel.setLayout( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'operator: ', self._duration_number_test ) )
        rows.append( ( 'multiplier (optional): ', self._duration_multiplier ) )
        rows.append( ( 'delta (optional)', self._duration_delta ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._duration_panel, rows )
        
        self._duration_panel.setLayout( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'operator: ', self._normal_number_test ) )
        rows.append( ( 'multiplier (optional): ', self._normal_multiplier ) )
        rows.append( ( 'delta (optional)', self._normal_delta ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._normal_panel, rows )
        
        self._normal_panel.setLayout( gridbox )
        
        #
        
        rows = []
        
        rows.append( ( 'operator: ', self._fuzzy_number_test ) )
        rows.append( ( 'multiplier (optional): ', self._fuzzy_multiplier ) )
        rows.append( ( 'delta (optional)', self._fuzzy_delta ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._fuzzy_panel, rows )
        
        self._fuzzy_panel.setLayout( gridbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._system_predicate, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._warning_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._time_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._duration_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._normal_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._fuzzy_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._live_value_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        self._system_predicate.currentIndexChanged.connect( self._UpdateWidgets )
        
        self._time_number_test.valueChanged.connect( self._UpdateLabel )
        self._time_delta.timeDeltaChanged.connect( self._UpdateLabel )
        
        self._duration_number_test.valueChanged.connect( self._UpdateLabel )
        self._duration_multiplier.valueChanged.connect( self._UpdateLabel )
        self._duration_delta.timeDeltaChanged.connect( self._UpdateLabel )
        
        self._fuzzy_number_test.valueChanged.connect( self._UpdateLabel )
        self._fuzzy_multiplier.valueChanged.connect( self._UpdateLabel )
        self._fuzzy_delta.valueChanged.connect( self._UpdateLabel )
        
        self._normal_number_test.valueChanged.connect( self._UpdateLabel )
        self._normal_multiplier.valueChanged.connect( self._UpdateLabel )
        self._normal_delta.valueChanged.connect( self._UpdateLabel )
        
        self._UpdateWidgets()
        
    
    def _SetValue( self, pair_comparator: ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo ):
        
        system_predicate = pair_comparator.GetSystemPredicate()
        
        self._system_predicate.SetValue( system_predicate )
        
        we_time_pred = system_predicate.GetType() in (
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME,
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME,
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME,
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME
        )
        
        we_duration_pred = system_predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION
        we_fuzzy_pred = system_predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FRAMERATE
        if we_time_pred:
            
            self._time_number_test.SetValue( pair_comparator.GetNumberTest() )
            
            self._time_delta.SetValue( HydrusTime.SecondiseMS( pair_comparator.GetDelta() ) )
            
        elif we_duration_pred:
            
            self._duration_number_test.SetValue( pair_comparator.GetNumberTest() )
            
            self._duration_multiplier.setValue( pair_comparator.GetMultiplier() )
            self._duration_delta.SetValue( HydrusTime.SecondiseMS( pair_comparator.GetDelta() ) )
            
        elif we_fuzzy_pred:
            
            self._fuzzy_number_test.SetValue( pair_comparator.GetNumberTest() )
            
            self._fuzzy_multiplier.setValue( pair_comparator.GetMultiplier() )
            self._fuzzy_delta.setValue( pair_comparator.GetDelta() )
            
        else:
            
            self._normal_number_test.SetValue( pair_comparator.GetNumberTest() )
            
            self._normal_multiplier.setValue( pair_comparator.GetMultiplier() )
            self._normal_delta.setValue( pair_comparator.GetDelta() )
            
        
    
    def _UpdateLabel( self ):
        
        try:
            
            value = self.GetValue()
            
            text = value.GetSummary()
            
        except:
            
            text = 'Could not calculate current value!'
            
        
        self._live_value_st.setText( text )
        
    
    def _UpdateWidgets( self ):
        
        system_predicate: ClientSearchPredicate.Predicate = self._system_predicate.GetValue()
        
        we_time_pred = system_predicate.GetType() in (
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME,
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME,
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME,
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME
        )
        
        we_duration_pred = system_predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION
        
        we_fuzzy_pred = system_predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FRAMERATE
        
        self._time_panel.setVisible( we_time_pred )
        
        self._duration_panel.setVisible( we_duration_pred )
        
        self._fuzzy_panel.setVisible( we_fuzzy_pred )
        
        self._normal_panel.setVisible( not ( we_time_pred or we_duration_pred or we_fuzzy_pred ) )
        
        warning_label = self._system_pred_types_to_warning_label_texts.get( system_predicate.GetType(), '' )
        
        self._warning_label.setText( warning_label )
        self._warning_label.setVisible( warning_label != '' )
        
        self._UpdateLabel()
        
    
    def GetValue( self ):
        
        system_predicate = self._system_predicate.GetValue()
        
        we_time_pred = system_predicate.GetType() in (
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME,
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME,
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME,
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME
        )
        
        we_duration_pred = system_predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION
        
        we_fuzzy_pred = system_predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FRAMERATE
        
        if we_time_pred:
            
            number_test = self._time_number_test.GetValue()
            
            multiplier = 1.00
            delta = HydrusTime.MillisecondiseS( self._time_delta.GetValue() )
            
        elif we_duration_pred:
            
            number_test = self._duration_number_test.GetValue()
            
            multiplier = self._duration_multiplier.value()
            delta = HydrusTime.MillisecondiseS( self._duration_delta.GetValue() )
            
        elif we_fuzzy_pred:
            
            number_test = self._fuzzy_number_test.GetValue()
            
            multiplier = self._fuzzy_multiplier.value()
            delta = self._fuzzy_delta.value()
            
        else:
            
            number_test = self._normal_number_test.GetValue()
            
            multiplier = self._normal_multiplier.value()
            delta = self._normal_delta.value()
            
        
        number_test.value = 1
        
        pair_comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        pair_comparator.SetSystemPredicate( system_predicate )
        pair_comparator.SetNumberTest( number_test )
        pair_comparator.SetMultiplier( multiplier )
        pair_comparator.SetDelta( delta )
        
        return pair_comparator
        
    

class EditPairComparatorRelativeVisualDuplicatesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, pair_comparator: ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeVisualDuplicates ):
        
        super().__init__( parent )
        
        self._acceptable_confidence = ClientGUICommon.BetterChoice( self )
        
        for confidence in [ ClientVisualData.VISUAL_DUPLICATES_RESULT_VERY_PROBABLY, ClientVisualData.VISUAL_DUPLICATES_RESULT_ALMOST_CERTAINLY, ClientVisualData.VISUAL_DUPLICATES_RESULT_NEAR_PERFECT ]:
            
            self._acceptable_confidence.addItem( ClientVisualData.result_str_lookup[ confidence ], confidence )
            
        
        #
        
        self._acceptable_confidence.SetValue( pair_comparator.GetAcceptableConfidence() )
        
        #
        
        label = 'This comparison uses a custom visual inspection algorithm that renders both images, computes statistical data on their edges and colours, and compares the two to determine if they are the same image with no changes a human eye would notice. Imagine it as a much more precise version of the original similar file search that populates this whole system. It filters out noise from compression artifacts or resizing differences but will spot almost all watermarks or artist corrections/alterations.'
        label += '\n\n'
        label += 'This system is not perfect, but when it is positive, it is usually trustworthy. I recommend you keep it at at least "almost-certainly" confidence confidence, and only on semi-automatic to start with. I have ironed out all the false positives we have discovered, but if you encounter any more, I would be interested in seeing them. False negatives are more common and less urgent--this system is designed for the auto-resolution system, and thus it errs on the side of "not visual duplicates". It will most often do this on very heavy re-encodes, where the jpeg artifacts are overwhelmingly fuzzy on the smaller file.'
        label += '\n\n'
        label += 'It only works on images and cannot handle files with transparency yet. It will also abstain from giving a positive result on anything too unusual, such as a very small resolution file, or one that seems to only be a white panel.'
        label += '\n\n'
        label += 'This system is heavy on the CPU! Expect about a second of processing time per pair. Try to cut down the prior search space if you can.'
        
        st = ClientGUICommon.BetterStaticText( self, label = label )
        
        st.setWordWrap( True )
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        
        rows = []
        
        rows.append( ( 'A and B are at least ', self._acceptable_confidence ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        acceptable_confidence = self._acceptable_confidence.GetValue()
        
        pair_comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeVisualDuplicates( acceptable_confidence = acceptable_confidence )
        
        return pair_comparator
        
    

class EditPairSelectorWidget( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, pair_selector: ClientDuplicatesAutoResolutionComparators.PairSelector ):
        
        super().__init__( parent, 'pair comparison and selection' )
        
        self._original_pair_selector = pair_selector
        
        self._comparators = EditComparatorList( self )
        
        self._comparators.AddDatas( self._original_pair_selector.GetComparators() )
        
        self.Add( self._comparators, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def GetValue( self ) -> ClientDuplicatesAutoResolutionComparators.PairSelector:
        
        pair_selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparators = self._comparators.GetData()
        
        pair_selector.SetComparators( comparators )
        
        return pair_selector
        
    

EDIT_RULES_DIALOG_LOCK = threading.Lock()

class ReviewDuplicatesAutoResolutionPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent )
        
        self._rules_are_stale = True
        self._properties_are_stale = True
        
        menu_template_items = []
        
        call = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DUPLICATES_AUTO_RESOLUTION )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the duplicates auto-resolution help', 'Open the help page for duplicates auto-resolution in your web browser.', call ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        self._refresh_button = ClientGUICommon.IconButton( self, CC.global_icons().refresh, self._SetRulesStale )
        self._cog_button = ClientGUIMenuButton.CogIconButton( self, self._GetCogMenuTemplateItems() )
        
        #
        
        self._duplicates_auto_resolution_rules_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_REVIEW_DUPLICATES_AUTO_RESOLUTION_RULES.ID, self._ConvertRuleToDisplayTuple, self._ConvertRuleToSortTuple )
        
        self._duplicates_auto_resolution_rules = ClientGUIListCtrl.BetterListCtrlTreeView( self._duplicates_auto_resolution_rules_panel, 6, model, use_simple_delete = True, activation_callback = self._ReviewActions )
        
        self._duplicates_auto_resolution_rules_panel.SetListCtrl( self._duplicates_auto_resolution_rules )
        
        self._duplicates_auto_resolution_rules_st = ClientGUICommon.BetterStaticText( self, label = f'initialising{HC.UNICODE_ELLIPSIS}' )
        self._have_loaded_rules_once = False
        
        self._duplicates_auto_resolution_rules_panel.AddButton( 'pause/play', self._PausePlayRules, enabled_only_on_selection = True )
        self._duplicates_auto_resolution_rules_panel.AddButton( 'review actions', self._ReviewActions, enabled_only_on_selection = True )
        self._duplicates_auto_resolution_rules_panel.AddButton( 'edit rules', self._Edit )
        #self._duplicates_auto_resolution_rules_panel.AddButton( 'work hard', self._FlipWorkingHard, enabled_check_func = self._CanWorkHard )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._refresh_button, CC.FLAGS_CENTER )
        QP.AddToLayout( button_hbox, self._cog_button, CC.FLAGS_CENTER )
        
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._duplicates_auto_resolution_rules_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._duplicates_auto_resolution_rules_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        #
        
        self._rules_list_updater = self._InitialiseUpdater()
        
        self._SetRulesStale()
        
        CG.client_controller.sub( self, 'NotifyRulePropertiesHaveChanged', 'duplicates_auto_resolution_rules_properties_have_changed' )
        CG.client_controller.sub( self, 'NotifyNewRules', 'notify_duplicates_auto_resolution_new_rules' )
        
    
    def _CanWorkHard( self ):
        
        rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
        working_hard_rules = CG.client_controller.duplicates_auto_resolution_manager.GetWorkingHard()
        
        return True in ( rule.CanWorkHard() or rule in working_hard_rules for rule in rules )
        
    
    def _CheckStaleStuff( self ):
        
        if self.isVisible():
            
            if self._properties_are_stale:
                
                self._duplicates_auto_resolution_rules.UpdateDatas()
                
                self._properties_are_stale = False
                
            
            if self._rules_are_stale:
                
                self._rules_list_updater.update()
                
                self._rules_are_stale = False
                
            
        
    
    def _ConvertRuleToDisplayTuple( self, duplicates_auto_resolution_rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        name = duplicates_auto_resolution_rule.GetName()
        
        search_status = duplicates_auto_resolution_rule.GetSearchSummary()
        
        running_status = CG.client_controller.duplicates_auto_resolution_manager.GetRunningStatus( duplicates_auto_resolution_rule )
        
        return ( name, search_status, running_status )
        
    
    def _ConvertRuleToSortTuple( self, duplicates_auto_resolution_rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        ( name, search_status, running_status ) = self._ConvertRuleToDisplayTuple( duplicates_auto_resolution_rule )
        
        sort_name = HydrusText.HumanTextSortKey( name )
        
        return ( sort_name, search_status, running_status )
        
    
    def _DeleteOrphanRules( self ):
        
        text = 'PAUSE ALL RULE WORK BEFORE STARTING THIS.'
        text += '\n\n'
        text += f'This will scan the database for rule definitions in the primary rule module and the backing object in the serialisable module. If a rule is in one location but not the other (probably due to hard drive damage), the rule will be deleted.'
        text += '\n\n'
        text += 'This command is useful if your client is shouting about missing rules, otherwise it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.Write( 'duplicates_auto_resolution_maintenance_fix_orphan_rules' )
            
        
    
    def _DeleteOrphanPotentialPairs( self ):
        
        text = f'This will scan the primary potential pairs table. If any are missing from the auto-resolution rule potential pair cache, they will be added. Orphans will be deleted.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.Write( 'duplicates_auto_resolution_maintenance_fix_orphan_potential_pairs' )
            
        
    
    def _Edit( self ):
        
        def do_it_qt( duplicates_auto_resolution_rules: list[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ] ):
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit rules' ) as dlg:
                
                panel = EditDuplicatesAutoResolutionRulesPanel( dlg, duplicates_auto_resolution_rules )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    edited_duplicates_auto_resolution_rules = panel.GetValue()
                    
                    CG.client_controller.duplicates_auto_resolution_manager.SetRules( edited_duplicates_auto_resolution_rules )
                    
                
            
        
        def do_it():
            
            with EDIT_RULES_DIALOG_LOCK:
                
                job_status = ClientThreading.JobStatus()
                
                job_status.SetStatusText( 'Waiting for current rules work to finish.' )
                
                CG.client_controller.pub( 'message', job_status )
                
                try:
                    
                    edit_work_lock = CG.client_controller.duplicates_auto_resolution_manager.GetEditWorkLock()
                    
                    while not edit_work_lock.acquire( timeout = 0.25 ):
                        
                        if HG.started_shutdown:
                            
                            return
                            
                        
                    
                finally:
                    
                    job_status.FinishAndDismiss()
                    
                
                # we have the lock
                
                try:
                    
                    CG.client_controller.pub( 'edit_duplicates_auto_resolution_rules_dialog_opening' )
                    
                    rules = CG.client_controller.duplicates_auto_resolution_manager.GetRules()
                    
                    CG.client_controller.CallBlockingToQtFireAndForgetNoResponse( self, do_it_qt, rules )
                    
                finally:
                    
                    edit_work_lock.release()
                    
                    CG.client_controller.duplicates_auto_resolution_manager.Wake()
                    
                
            
        
        CG.client_controller.CallToThread( do_it )
        
    
    def _FlipBoolean( self, name ):
        
        CG.client_controller.new_options.FlipBoolean( name )
        
        CG.client_controller.duplicates_auto_resolution_manager.Wake()
        
    
    def _FlipWorkingHard( self ):
        
        rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
        
        working_hard_rules = CG.client_controller.duplicates_auto_resolution_manager.GetWorkingHard()
        
        for rule in rules:
            
            if rule in working_hard_rules:
                
                CG.client_controller.duplicates_auto_resolution_manager.SetWorkingHard( rule, False )
                
            elif rule.CanWorkHard():
                
                CG.client_controller.duplicates_auto_resolution_manager.SetWorkingHard( rule, True )
                
            
        
    
    def _GetCogMenuTemplateItems( self ) -> list[ ClientGUIMenuButton.MenuTemplateItem ]:
        
        menu_template_items = []
        
        check_manager = ClientGUICommon.CheckboxManagerCalls(
            lambda: self._FlipBoolean( 'duplicates_auto_resolution_during_idle' ),
            lambda: CG.client_controller.new_options.GetBoolean( 'duplicates_auto_resolution_during_idle' )
        )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'work on these rules during idle time', 'Allow the client to work on auto-resolution rules when you are not using the program.', check_manager ) )
        
        check_manager = ClientGUICommon.CheckboxManagerCalls(
            lambda: self._FlipBoolean( 'duplicates_auto_resolution_during_active' ),
            lambda: CG.client_controller.new_options.GetBoolean( 'duplicates_auto_resolution_during_active' )
        )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'work on these rules during normal time', 'Allow the client to work on auto-resolution rules when you are using the program.', check_manager ) )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        
        def title_call_1():
            
            rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
            
            if len( rules ) == 0:
                
                return 'reset search on all rules'
                
            else:
                
                return f'reset search on {HydrusNumbers.ToHumanInt( len( rules ) )} selected rules'
                
            
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( title_call_1, 'Reset the search for the given rules.', self._ResetSearch ) )
        
        def title_call_2():
            
            rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
            
            if len( rules ) == 0:
                
                return 'reset test on all rules'
                
            else:
                
                return f'reset test on {HydrusNumbers.ToHumanInt( len( rules ) )} selected rules'
                
            
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( title_call_2, 'Reset the test for the given rules.', self._ResetTest ) )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        
        def title_call_3():
            
            rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
            
            if len( rules ) == 0:
                
                return 'reset all denied pairs on all rules'
                
            else:
                
                return f'reset all denied pairs on {HydrusNumbers.ToHumanInt( len( rules ) )} selected rules'
                
            
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( title_call_3, 'Reset all the denied pairs for the given rules.', self._ResetDenied ) )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'maintenance: delete orphan rules', 'Scan for rules that are partly missing (probably from hard drive damage) and delete them.', self._DeleteOrphanRules ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'maintenance: fix orphan potential pairs', 'Scan for potential pairs in your rule cache that are no longer pertinent and delete them.', self._DeleteOrphanPotentialPairs ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'maintenance: regen cached numbers', 'Clear cached pair counts and regenerate from source.', self._RegenNumbers ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'maintenance: resync rule file domains', 'Check that the rule has desynced from the correct pairs its search looks for.', self._ResyncRulesToLocationContexts ) )
        
        return menu_template_items
        
    
    def _InitialiseUpdater( self ):
        
        def loading_callable():
            
            if not self._have_loaded_rules_once:
                
                self._duplicates_auto_resolution_rules_panel.setEnabled( False )
                
            
            pass
            
        
        def work_callable( args ):
            
            rules = CG.client_controller.Read( 'duplicates_auto_resolution_rules_with_counts' )
            
            return rules
            
        
        def publish_callable( rules ):
            
            if not self._have_loaded_rules_once:
                
                self._duplicates_auto_resolution_rules_panel.setEnabled( True )
                self._duplicates_auto_resolution_rules_st.setVisible( False )
                
            
            self._duplicates_auto_resolution_rules.SetData( rules )
            
            ideal_rows = len( rules )
            ideal_rows = max( 4, ideal_rows )
            ideal_rows = min( ideal_rows, 24 )
            
            self._duplicates_auto_resolution_rules.ForceHeight( ideal_rows )
            
        
        return ClientGUIAsync.AsyncQtUpdater( 'review auto-resolution rules fetch', self, loading_callable, work_callable, publish_callable )
        
    
    def _PausePlayRules( self ):
        
        rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
        
        for rule in rules:
            
            CG.client_controller.duplicates_auto_resolution_manager.PausePlayRule( rule )
            
        
    
    def _RegenNumbers( self ):
        
        text = f'This will delete all the cached pair counts for your rules. If it seems there is a miscount somewhere (e.g. a pending pair to search that never clears), try hitting this.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.Write( 'duplicates_auto_resolution_maintenance_regen_numbers' )
            
        
    
    def _ResetDenied( self ):
        
        rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
        
        if len( rules ) == 0:
            
            rules = self._duplicates_auto_resolution_rules.GetData()
            
            if len( rules ) == 0:
                
                return
                
            
        
        text = f'This will command the database to repeal all user-denied decisions for these {HydrusNumbers.ToHumanInt(len(rules))} rules.\n\nDo this only if the rules have tens of thousands of denied pairs and you do not want to undo them manually in the "review actions" window.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.duplicates_auto_resolution_manager.ResetRuleDenied( rules )
            
        
    
    def _ResetSearch( self ):
        
        rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
        
        if len( rules ) == 0:
            
            rules = self._duplicates_auto_resolution_rules.GetData()
            
            if len( rules ) == 0:
                
                return
                
            
        
        text = f'This will command the database to re-search these {HydrusNumbers.ToHumanInt(len(rules))} rules. It will not undo any user-denied decisions. There is no point to running this unless you suspect a miscount or other sync bug.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.duplicates_auto_resolution_manager.ResetRuleSearchProgress( rules )
            
        
    
    def _ResetTest( self ):
        
        rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
        
        if len( rules ) == 0:
            
            rules = self._duplicates_auto_resolution_rules.GetData()
            
            if len( rules ) == 0:
                
                return
                
            
        
        text = f'This will command the database to re-test the pending/fails for these {HydrusNumbers.ToHumanInt(len(rules))} rules. It will not undo any user-denied decisions. There is no point to running this unless you suspect a miscount or other sync bug.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.duplicates_auto_resolution_manager.ResetRuleTestProgress( rules )
            
        
    
    def _ResyncRulesToLocationContexts( self ):
        
        text = f'This will check that every rule is tracking all the pairs in its search domain, and no others. There is no point to running this unless you see a pair that should not be in a pending queue or similar (e.g. if one of the files is trashed).'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.Write( 'duplicates_auto_resolution_maintenance_resync_rules_to_location_contexts' )
            
        
    
    def _ReviewActions( self ):
        
        rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
        
        for rule in rules:
            
            frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'review duplicate auto-resolution actions' )
            
            panel = ClientGUIDuplicatesAutoResolutionRuleReview.ReviewActionsPanel( frame, rule )
            
            frame.SetPanel( panel )
            
        
    
    def _SetPropertiesStale( self ):
        
        self._properties_are_stale = True
        
        self._CheckStaleStuff()
        
    
    def _SetRulesStale( self ):
        
        self._rules_are_stale = True
        
        self._CheckStaleStuff()
        
    
    def NotifyNewRules( self ):
        
        self._SetRulesStale()
        
    
    def NotifyRulePropertiesHaveChanged( self ):
        
        self._SetPropertiesStale()
        
    
    def PageHidden( self ):
        
        pass
        
    
    def PageShown( self ):
        
        self._CheckStaleStuff()
        
    
