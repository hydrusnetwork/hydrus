import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.duplicates import ClientGUIDuplicatesContentMergeOptions
from hydrus.client.gui.duplicates import ClientGUIPotentialDuplicatesSearchContext
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.metadata import ClientGUIMetadataConditional
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton

class EditDuplicatesAutoResolutionRulesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, duplicates_auto_resolution_rules: typing.Collection[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ] ):
        
        super().__init__( parent )
        
        menu_items = []
        
        call = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DUPLICATES_AUTO_RESOLUTION )
        
        menu_items.append( ( 'normal', 'open the duplicates auto-resolution help', 'Open the help page for duplicates auto-resolution in your web browser.', call ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        self._duplicates_auto_resolution_rules_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_EDIT_DUPLICATES_AUTO_RESOLUTION_RULES.ID, self._ConvertRuleToDisplayTuple, self._ConvertRuleToSortTuple )
        
        self._duplicates_auto_resolution_rules = ClientGUIListCtrl.BetterListCtrlTreeView( self._duplicates_auto_resolution_rules_panel, 12, model, use_simple_delete = True, activation_callback = self._Edit )
        
        self._duplicates_auto_resolution_rules_panel.SetListCtrl( self._duplicates_auto_resolution_rules )
        
        #self._duplicates_auto_resolution_rules_panel.AddButton( 'add', self._Add )
        self._duplicates_auto_resolution_rules_panel.AddButton( 'add suggested', self._AddSuggested )
        self._duplicates_auto_resolution_rules_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        self._duplicates_auto_resolution_rules_panel.AddDeleteButton()
        #self._duplicates_auto_resolution_rules_panel.AddImportExportButtons( ( ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, ), self._ImportRule )
        
        #
        
        self._duplicates_auto_resolution_rules.AddDatas( duplicates_auto_resolution_rules )
        
        self._duplicates_auto_resolution_rules.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        st = ClientGUICommon.BetterStaticText( self, 'Hey, this system does not work yet! This UI is just a placeholder!' )
        st.setWordWrap( True )
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._duplicates_auto_resolution_rules_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _Add( self ):
        
        name = 'new rule'
        
        duplicates_auto_resolution_rule = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( name )
        
        # TODO: set some good defaults
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit rule' ) as dlg:
            
            panel = EditDuplicatesAutoResolutionRulePanel( dlg, duplicates_auto_resolution_rule )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                duplicates_auto_resolution_rule = panel.GetValue()
                
                duplicates_auto_resolution_rule.SetNonDupeName( self._GetExistingNames() )
                
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
        paused = duplicates_auto_resolution_rule.IsPaused()
        
        pretty_paused = 'yes' if paused else ''
        
        return ( name, rule_summary, pair_selector_summary, action_summary, search_status, pretty_paused )
        
    
    _ConvertRuleToSortTuple = _ConvertRuleToDisplayTuple
    
    def _Edit( self ):
        
        duplicates_auto_resolution_rule: typing.Optional[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ] = self._duplicates_auto_resolution_rules.GetTopSelectedData()
        
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
                    
                    edited_duplicates_auto_resolution_rule.SetNonDupeName( existing_names )
                    
                
                self._duplicates_auto_resolution_rules.ReplaceData( duplicates_auto_resolution_rule, edited_duplicates_auto_resolution_rule, sort_and_scroll = True )
                
            
        
    
    def _GetExistingNames( self ):
        
        return { duplicates_auto_resolution_rule.GetName() for duplicates_auto_resolution_rule in self._duplicates_auto_resolution_rules.GetData() }
        
    
    def _ImportRule( self, duplicates_auto_resolution_rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        duplicates_auto_resolution_rule.SetNonDupeName( self._GetExistingNames() )
        
        self._duplicates_auto_resolution_rules.AddData( duplicates_auto_resolution_rule, select_sort_and_scroll = True )
        
    
    def GetValue( self ) -> typing.List[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ]:
        
        return self._duplicates_auto_resolution_rules.GetData()
        
    

class EditDuplicatesAutoResolutionRulePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, duplicates_auto_resolution_rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        super().__init__( parent )
        
        self._duplicates_auto_resolution_rule = duplicates_auto_resolution_rule
        
        self._rule_panel = ClientGUICommon.StaticBox( self, 'rule' )
        
        self._name = QW.QLineEdit( self._rule_panel )
        
        self._paused = QW.QCheckBox( self._rule_panel )
        
        self._main_notebook = ClientGUICommon.BetterNotebook( self )
        
        #
        
        self._search_panel = QW.QWidget( self._main_notebook )
        
        potential_duplicates_search_context = duplicates_auto_resolution_rule.GetPotentialDuplicatesSearchContext()
        
        self._potential_duplicates_search_context = ClientGUIPotentialDuplicatesSearchContext.EditPotentialDuplicatesSearchContextPanel( self._search_panel, potential_duplicates_search_context, put_searches_side_by_side = True )
        
        self._potential_duplicates_search_context.setEnabled( False )
        
        #
        
        self._selector_panel = QW.QWidget( self._main_notebook )
        
        pair_selector = duplicates_auto_resolution_rule.GetPairSelector()
        
        self._pair_selector = EditPairSelectorWidget( self._selector_panel, pair_selector )
        
        self._pair_selector.setEnabled( False )
        
        #
        
        self._actions_panel = QW.QWidget( self._main_notebook )
        
        action = duplicates_auto_resolution_rule.GetAction()
        ( delete_a, delete_b ) = duplicates_auto_resolution_rule.GetDeleteInfo()
        duplicates_content_merge_options = duplicates_auto_resolution_rule.GetDuplicateContentMergeOptions()
        
        self._edit_actions_panel = EditPairActionsWidget( self._actions_panel, action, delete_a, delete_b, duplicates_content_merge_options )
        
        self._edit_actions_panel.setEnabled( False )
        
        #
        
        self._preview_panel = QW.QWidget( self._main_notebook )
        
        #
        
        self._name.setText( self._duplicates_auto_resolution_rule.GetName() )
        self._paused.setChecked( self._duplicates_auto_resolution_rule.IsPaused() )
        
        #
        
        label = 'First we have to find some duplicate pairs to test. This can be system:everything if you like, but it is best to narrow it down if you can.'
        
        st = ClientGUICommon.BetterStaticText( self._search_panel, label = label )
        
        st.setWordWrap( True )
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._potential_duplicates_search_context, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._search_panel.setLayout( vbox )
        
        #
        
        
        vbox = QP.VBoxLayout()
        
        label = 'Now we have some pairs, we need to determine if we are confident enough to make an automatic decision. If we are setting one file to be a better duplicate of the other, we also need to arrange which is the A (usually the better) and the B (the worse).'
        label += '\n\n'
        label += 'The client will test the incoming pair both ways around against these rules, and if they fit either way, that "AB" is set and the action is applied. If the pair fails the rules both ways around, no changes will be made. If there are no rules, all pairs will be actioned--but you need at least one A- or B-defining rule for a "better/worse duplicates" action'
        
        st = ClientGUICommon.BetterStaticText( self._selector_panel, label )
        
        st.setWordWrap( True )
        st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._pair_selector, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._selector_panel.setLayout( vbox )
        
        #
        
        label = 'And now we have pairs to action, what should we do?'
        
        st = ClientGUICommon.BetterStaticText( self._actions_panel, label = label )
        
        st.setWordWrap( True )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._edit_actions_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self._actions_panel.setLayout( vbox )
        
        #
        
        label = 'In future, this panel will run some live database queries and preview examples of the pairs it finds and which pass the test.\n\nRun Search (pair count)\n\nRun Test on n pairs\n\nTest Results%\n\nShow a Failing Test | Show a Passing Test\n\nthumb A <-> thumb B, some way to launch a (read-only?) media viewer or something'
        
        st = ClientGUICommon.BetterStaticText( self._preview_panel, label = label )
        
        st.setWordWrap( True )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
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
        
        gridbox = ClientGUICommon.WrapInGrid( self._rule_panel, rows )
        
        self._rule_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._rule_panel.Add( self._main_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        st = ClientGUICommon.BetterStaticText( self, 'Hey, this system does not work yet! This UI is just a placeholder!' )
        st.setWordWrap( True )
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._rule_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        name = self._name.text()
        
        duplicates_auto_resolution_rule = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( name )
        
        duplicates_auto_resolution_rule.SetPaused( self._paused.isChecked() )
        
        duplicates_auto_resolution_rule.SetPotentialDuplicatesSearchContext( self._potential_duplicates_search_context.GetValue() )
        
        #
        
        pair_selector = self._pair_selector.GetValue()
        
        duplicates_auto_resolution_rule.SetPairSelector( pair_selector )
        
        #
        
        # action
        
        ( action, delete_a, delete_b, duplicate_content_merge_options ) = self._edit_actions_panel.GetValue()
        
        if action in ( HC.DUPLICATE_BETTER, HC.DUPLICATE_WORSE ) and not pair_selector.CanDetermineBetter():
            
            raise HydrusExceptions.VetoException( 'Hey, you have the action set to "better/worse duplicate" but the comparison step has no way to figure out A or B! You need to add at least one step that specifies either A or B so the rule knows which way around to apply the action. If there is no easy determination, perhaps "set as same quality" is more appropriate?' )
            
        
        duplicates_auto_resolution_rule.SetAction( action )
        duplicates_auto_resolution_rule.SetDeleteInfo( delete_a, delete_b )
        duplicates_auto_resolution_rule.SetDuplicateContentMergeOptions( duplicate_content_merge_options )
        
        #
        
        duplicates_auto_resolution_rule.SetId( self._duplicates_auto_resolution_rule.GetId() )
        
        # TODO: transfer any cached search data, including what we may have re-fetched in this panel's work, to the new rule
        
        return duplicates_auto_resolution_rule
        
    

class EditPairActionsWidget( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, action: int, delete_a: bool, delete_b: bool, duplicates_content_merge_options: typing.Optional[ ClientDuplicates.DuplicateContentMergeOptions ] ):
        
        super().__init__( parent, 'pair actions' )
        
        self._action = ClientGUICommon.BetterChoice( self )
        
        for duplicate_type in [
            HC.DUPLICATE_BETTER,
            HC.DUPLICATE_WORSE,
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
        
        action_to_set = action
        
        if action_to_set == HC.DUPLICATE_WORSE:
            
            action_to_set = HC.DUPLICATE_BETTER
            
        
        if duplicates_content_merge_options is None:
            
            duplicates_content_merge_options = CG.client_controller.new_options.GetDuplicateContentMergeOptions( action_to_set )
            
        else:
            
            self._custom_duplicate_content_merge_options.ExpandCollapse()
            
        
        self._custom_duplicate_content_merge_options.SetValue( action_to_set, duplicates_content_merge_options )
        
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
        
        action_to_set = self._action.GetValue()
        
        if action_to_set == HC.DUPLICATE_WORSE:
            
            action_to_set = HC.DUPLICATE_BETTER
            
        
        current_action = self._custom_duplicate_content_merge_options.GetDuplicateAction()
        
        if current_action != action_to_set:
            
            duplicates_content_merge_options = CG.client_controller.new_options.GetDuplicateContentMergeOptions( action_to_set )
            
            self._custom_duplicate_content_merge_options.SetValue( action_to_set, duplicates_content_merge_options )
            
        
    
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
    
    def __init__( self, parent, pair_comparator: ClientDuplicatesAutoResolution.PairComparatorOneFile ):
        
        super().__init__( parent )
        
        self._looking_at = ClientGUICommon.BetterChoice( self )
        
        self._looking_at.addItem( 'A will pass these', ClientDuplicatesAutoResolution.LOOKING_AT_A )
        self._looking_at.addItem( 'B will pass these', ClientDuplicatesAutoResolution.LOOKING_AT_B )
        self._looking_at.addItem( 'either will pass these', ClientDuplicatesAutoResolution.LOOKING_AT_EITHER )
        
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
        
    
    def GetValue( self ):
        
        looking_at = self._looking_at.GetValue()
        metadata_conditional = self._metadata_conditional.GetValue()
        
        pair_comparator = ClientDuplicatesAutoResolution.PairComparatorOneFile()
        
        pair_comparator.SetLookingAt( looking_at )
        pair_comparator.SetMetadataConditional( metadata_conditional )
        
        return pair_comparator
        
    

class EditPairSelectorWidget( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, pair_selector: ClientDuplicatesAutoResolution.PairSelector ):
        
        super().__init__( parent, 'pair comparison and selection' )
        
        self._original_pair_selector = pair_selector
        
        self._comparators = ClientGUIListBoxes.AddEditDeleteListBox( self, 8, self._PairComparatorToPretty, self._Add, self._Edit )
        
        self._comparators.AddDatas( self._original_pair_selector.GetComparators() )
        
        self.Add( self._comparators, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _Add( self ):
        
        # presumably we could ask for the type of comparator here
        
        pair_comparator = ClientDuplicatesAutoResolution.PairComparatorOneFile()
        
        return self._Edit( pair_comparator )
        
    
    def _Edit( self, comparator: ClientDuplicatesAutoResolution.PairComparator ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit comparator' ) as dlg:
            
            if isinstance( comparator, ClientDuplicatesAutoResolution.PairComparatorOneFile ):
                
                panel = EditPairComparatorOneFilePanel( dlg, comparator )
                
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_comparator = panel.GetValue()
                
                return edited_comparator
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
    
    def _PairComparatorToPretty( self, pair_comparator: ClientDuplicatesAutoResolution.PairComparator ):
        
        return pair_comparator.GetSummary()
        
    
    def GetValue( self ) -> ClientDuplicatesAutoResolution.PairSelector:
        
        pair_selector = ClientDuplicatesAutoResolution.PairSelector()
        
        comparators = self._comparators.GetData()
        
        pair_selector.SetComparators( comparators )
        
        return pair_selector
        
    

class ReviewDuplicatesAutoResolutionPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent )
        
        menu_items = []
        
        call = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DUPLICATES_AUTO_RESOLUTION )
        
        menu_items.append( ( 'normal', 'open the duplicates auto-resolution help', 'Open the help page for duplicates auto-resolution in your web browser.', call ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        # TODO: A cog icon with 'run in normal/idle time' stuff
        
        #
        
        self._duplicates_auto_resolution_rules_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_REVIEW_DUPLICATES_AUTO_RESOLUTION_RULES.ID, self._ConvertRuleToDisplayTuple, self._ConvertRuleToSortTuple )
        
        self._duplicates_auto_resolution_rules = ClientGUIListCtrl.BetterListCtrlTreeView( self._duplicates_auto_resolution_rules_panel, 12, model, use_simple_delete = True, activation_callback = self._Edit )
        
        self._duplicates_auto_resolution_rules_panel.SetListCtrl( self._duplicates_auto_resolution_rules )
        
        self._duplicates_auto_resolution_rules_panel.AddButton( 'run now', self._RunNow, enabled_check_func = self._CanRunNow )
        self._duplicates_auto_resolution_rules_panel.AddButton( 'edit rules', self._Edit )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        
        st = ClientGUICommon.BetterStaticText( self, 'Hey, this system does not work yet! This UI is just a placeholder!' )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._duplicates_auto_resolution_rules_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        #
        
        self._ResetListData()
        
        # TODO: hook into the manager's pubsub update signal, _ResetListData
        
    
    def _CanRunNow( self ):
        
        return False
        
    
    def _ConvertRuleToDisplayTuple( self, duplicates_auto_resolution_rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        name = duplicates_auto_resolution_rule.GetName()
        search_status = duplicates_auto_resolution_rule.GetSearchSummary()
        
        if duplicates_auto_resolution_rule.IsPaused():
            
            running_status = 'paused'
            
        else:
            
            running_status = CG.client_controller.duplicates_auto_resolution_manager.GetRunningStatus( duplicates_auto_resolution_rule.GetId() )
            
        
        return ( name, search_status, running_status )
        
    
    _ConvertRuleToSortTuple = _ConvertRuleToDisplayTuple
    
    def _Edit( self ):
        
        # TODO: Some sort of async delay as we wait for any current work to halt and the manager to save
        
        duplicates_auto_resolution_rules = self._duplicates_auto_resolution_rules.GetData()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit rules' ) as dlg:
            
            panel = EditDuplicatesAutoResolutionRulesPanel( dlg, duplicates_auto_resolution_rules )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_duplicates_auto_resolution_rules = panel.GetValue()
                
                CG.client_controller.duplicates_auto_resolution_manager.SetRules( edited_duplicates_auto_resolution_rules )
                
            
        
    
    def _ResetListData( self ):
        
        rules = CG.client_controller.duplicates_auto_resolution_manager.GetRules()
        
        self._duplicates_auto_resolution_rules.SetData( rules )
        
    
    def _RunNow( self ):
        
        pass
        
    
