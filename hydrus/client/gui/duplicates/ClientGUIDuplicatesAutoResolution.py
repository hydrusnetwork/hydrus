import collections.abc
import threading
import time
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNumbers

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.duplicates import ClientDuplicatesAutoResolutionComparators
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
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
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.gui.widgets import ClientGUINumberTest

class EditDuplicatesAutoResolutionRulesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, duplicates_auto_resolution_rules: collections.abc.Collection[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ] ):
        
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
        
        self._duplicates_auto_resolution_rules_panel.AddButton( 'add suggested', self._AddSuggested )
        self._duplicates_auto_resolution_rules_panel.AddButton( 'add', self._Add )
        self._duplicates_auto_resolution_rules_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        self._duplicates_auto_resolution_rules_panel.AddDeleteButton()
        #self._duplicates_auto_resolution_rules_panel.AddImportExportButtons( ( ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, ), self._ImportRule )
        
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
        
        st = ClientGUICommon.BetterStaticText( self, 'Hey, this system is still launching, and not everything planned is available yet. Start with the suggested pixel duplicate jpg/png rule, and if it all makes sense to you, play with the other suggested rules and then perhaps making your own. Try to stick to pixel duplicates for now, and do semi-automatic before switching to automatic. Be careful. Let me know how it goes!' )
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
        
        operation_mode = duplicates_auto_resolution_rule.GetOperationMode()
        
        pretty_operation_mode = ClientDuplicatesAutoResolution.duplicates_auto_resolution_rule_operation_mode_str_lookup[ operation_mode ]
        
        return ( name, rule_summary, pair_selector_summary, action_summary, search_status, pretty_operation_mode )
        
    
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
        
    
    def GetValue( self ) -> list[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ]:
        
        return self._duplicates_auto_resolution_rules.GetData()
        
    

class EditDuplicatesAutoResolutionRulePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, duplicates_auto_resolution_rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        super().__init__( parent )
        
        self._duplicates_auto_resolution_rule = duplicates_auto_resolution_rule
        
        self._rule_panel = ClientGUICommon.StaticBox( self, 'rule' )
        
        self._name = QW.QLineEdit( self._rule_panel )
        
        self._operation_mode = ClientGUICommon.BetterChoice( self._rule_panel )
        
        for operation_mode in [
            ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_PAUSED,
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
        
        label = 'Now, for each pair that matches our search, we need to determine if their differences (or similarities!) are clear enough that we confidently can make an automatic decision. If we are setting one file to be a better duplicate of the other, we also need to arrange which is the A (usually the better) and the B (usually the worse).'
        label += '\n\n'
        label += 'The client will test the incoming pair both ways around against these rules, and if they fit either way, that "AB" pair order is set and the action is applied. If the pair fails the rules both ways around, no changes will be made. If there are no rules, all pairs will be actioned--but you need at least one A- or B-defining rule for a "better/worse duplicates" action'
        
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
        rows.append( ( 'operation: ', self._operation_mode ) )
        rows.append( ( 'max pending pairs (semi-automatic only): ', self._max_pending_pairs ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._rule_panel, rows )
        
        self._rule_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._rule_panel.Add( self._main_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        st = ClientGUICommon.BetterStaticText( self, 'Hey, this system is still launching, and not everything planned is available yet! You can now set basic relative pair comparison rules--try it out!' )
        st.setWordWrap( True )
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._rule_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._operation_mode.currentIndexChanged.connect( self._OperationModeChanged )
        
        self._main_notebook.currentChanged.connect( self._CurrentPageChanged )
        
        self._OperationModeChanged()
        
    
    def _CurrentPageChanged( self ):
        
        page = self._main_notebook.currentWidget()
        
        if page == self._preview_panel:
            
            self._full_preview_panel.PageShown()
            
        else:
            
            self._full_preview_panel.PageIsHidden()
            
        
    
    def _OperationModeChanged( self ):
        
        self._max_pending_pairs.setEnabled( self._operation_mode.GetValue() == ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION )
        
    
    def GetValue( self ):
        
        name = self._name.text()
        
        duplicates_auto_resolution_rule = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( name )
        
        duplicates_auto_resolution_rule.SetOperationMode( self._operation_mode.GetValue() )
        
        duplicates_auto_resolution_rule.SetPotentialDuplicatesSearchContext( self._potential_duplicates_search_context.GetValue() )
        
        duplicates_auto_resolution_rule.SetMaxPendingPairs( self._max_pending_pairs.GetValue() )
        
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
        duplicates_auto_resolution_rule.SetCountsCache( self._duplicates_auto_resolution_rule.GetCountsCacheDuplicate() )
        
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
        
    
    def GetValue( self ):
        
        looking_at = self._looking_at.GetValue()
        metadata_conditional = self._metadata_conditional.GetValue()
        
        pair_comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        pair_comparator.SetLookingAt( looking_at )
        pair_comparator.SetMetadataConditional( metadata_conditional )
        
        return pair_comparator
        
    

class EditPairComparatorRelativeFileinfoPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, pair_comparator: ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo ):
        
        super().__init__( parent )
        
        # note in a label that for duration, the units is ms
        
        self._system_predicate = ClientGUICommon.BetterChoice( self )
        
        for predicate_type in ClientSearchPredicate.PREDICATE_TYPES_WE_CAN_EXTRACT_FROM_MEDIA_RESULTS:
            
            predicate = ClientSearchPredicate.Predicate( predicate_type = predicate_type )
            
            self._system_predicate.addItem( predicate.ToString(), predicate )
            
        
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
        
        self._number_test = ClientGUINumberTest.NumberTestWidget(
            self,
            allowed_operators = allowed_operators,
            swap_in_string_for_value = 'B'
        )
        
        self._multiplier = QW.QDoubleSpinBox( self )
        self._multiplier.setDecimals( 2 )
        self._multiplier.setSingleStep( 0.01 )
        self._multiplier.setMinimum( -10000 )
        self._multiplier.setMaximum( 10000 )
        
        self._multiplier.setMinimumWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._multiplier, 11 ) )
        
        self._delta = ClientGUICommon.BetterSpinBox( self, min = -100000000, max = 100000000 )
        
        self._delta.setMinimumWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._delta, 13 ) )
        
        tt = 'If you dabble with this, the unit is usually obvious, but for duration, the unit is milliseconds!'
        
        self._delta.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._live_value_st = ClientGUICommon.BetterStaticText( self )
        
        #
        
        self._system_predicate.SetValue( pair_comparator.GetSystemPredicate() )
        self._number_test.SetValue( pair_comparator.GetNumberTest() )
        self._multiplier.setValue( pair_comparator.GetMultiplier() )
        self._delta.setValue( pair_comparator.GetDelta() )
        
        #
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'value to test: ', self._system_predicate ) )
        rows.append( ( 'operator: ', self._number_test ) )
        rows.append( ( 'multiplier (optional): ', self._multiplier ) )
        rows.append( ( 'delta (optional): ', self._delta ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._live_value_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        self._system_predicate.currentIndexChanged.connect( self._UpdateLabel )
        self._number_test.valueChanged.connect( self._UpdateLabel )
        self._multiplier.valueChanged.connect( self._UpdateLabel )
        self._delta.valueChanged.connect( self._UpdateLabel )
        
        self._UpdateLabel()
        
    
    def _UpdateLabel( self ):
        
        try:
            
            value = self.GetValue()
            
            text = value.GetSummary()
            
        except:
            
            text = 'Could not calculate current value!'
            
        
        self._live_value_st.setText( text )
        
    
    def GetValue( self ):
        
        system_predicate = self._system_predicate.GetValue()
        
        number_test = self._number_test.GetValue()
        number_test.value = 1
        
        multiplier = self._multiplier.value()
        delta = self._delta.value()
        
        pair_comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        pair_comparator.SetSystemPredicate( system_predicate )
        pair_comparator.SetNumberTest( number_test )
        pair_comparator.SetMultiplier( multiplier )
        pair_comparator.SetDelta( delta )
        
        return pair_comparator
        
    

class EditPairSelectorWidget( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, pair_selector: ClientDuplicatesAutoResolutionComparators.PairSelector ):
        
        super().__init__( parent, 'pair comparison and selection' )
        
        self._original_pair_selector = pair_selector
        
        self._comparators = ClientGUIListBoxes.AddEditDeleteListBox( self, 8, self._PairComparatorToPretty, self._Add, self._Edit )
        
        self._comparators.AddDatas( self._original_pair_selector.GetComparators() )
        
        self.Add( self._comparators, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _Add( self ):
        
        choice_tuples = [
            ( 'test A or B', ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile(), 'A comparator that tests one file at a time using system predicates.' ),
            ( 'test A against B using file info', ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo(), 'A comparator that performs a number test on the width, filesize, etc.. of A vs B.' )
        ]
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME )
        
        choice_tuples.append(
            ( comparator.GetSummary(), comparator, comparator.GetSummary() )
        )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_DIFFERS )
        
        choice_tuples.append(
            ( comparator.GetSummary(), comparator, comparator.GetSummary() )
        )
        
        try:
            
            comparator = ClientGUIDialogsQuick.SelectFromListButtons( self, 'Which type of comparator?', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            raise
            
        
        return self._Edit( comparator )
        
    
    def _Edit( self, comparator: ClientDuplicatesAutoResolutionComparators.PairComparator ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit comparator' ) as dlg:
            
            if isinstance( comparator, ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile ):
                
                panel = EditPairComparatorOneFilePanel( dlg, comparator )
                
            elif isinstance( comparator, ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo ):
                
                panel = EditPairComparatorRelativeFileinfoPanel( dlg, comparator )
                
            elif isinstance( comparator, ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded ):
                
                return comparator
                
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_comparator = panel.GetValue()
                
                return edited_comparator
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
    
    def _PairComparatorToPretty( self, pair_comparator: ClientDuplicatesAutoResolutionComparators.PairComparator ):
        
        return pair_comparator.GetSummary()
        
    
    def GetValue( self ) -> ClientDuplicatesAutoResolutionComparators.PairSelector:
        
        pair_selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparators = self._comparators.GetData()
        
        pair_selector.SetComparators( comparators )
        
        return pair_selector
        
    

EDIT_RULES_DIALOG_LOCK = threading.Lock()

class ReviewDuplicatesAutoResolutionPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent )
        
        menu_items = []
        
        call = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DUPLICATES_AUTO_RESOLUTION )
        
        menu_items.append( ( 'normal', 'open the duplicates auto-resolution help', 'Open the help page for duplicates auto-resolution in your web browser.', call ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        self._refresh_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().refresh, self._UpdateList )
        self._cog_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().cog, self._ShowCogMenu )
        
        #
        
        self._duplicates_auto_resolution_rules_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_REVIEW_DUPLICATES_AUTO_RESOLUTION_RULES.ID, self._ConvertRuleToDisplayTuple, self._ConvertRuleToSortTuple )
        
        self._duplicates_auto_resolution_rules = ClientGUIListCtrl.BetterListCtrlTreeView( self._duplicates_auto_resolution_rules_panel, 12, model, use_simple_delete = True, activation_callback = self._ReviewActions )
        
        self._duplicates_auto_resolution_rules_panel.SetListCtrl( self._duplicates_auto_resolution_rules )
        
        self._duplicates_auto_resolution_rules_panel.AddButton( 'review actions', self._ReviewActions, enabled_only_on_selection = True )
        self._duplicates_auto_resolution_rules_panel.AddButton( 'edit rules', self._Edit )
        self._duplicates_auto_resolution_rules_panel.AddButton( 'work hard', self._FlipWorkingHard, enabled_check_func = self._CanWorkHard )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        
        st = ClientGUICommon.BetterStaticText( self, 'Hey, this system is still launching, and not everything planned is available yet! Start with the suggested pixel duplicate jpg/png rule, and if it all makes sense to you, play with the other suggested rules and then perhaps making your own. Try to stick to pixel duplicates for now, and do semi-automatic before switching to automatic. Be careful. Let me know how it goes!' )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._refresh_button, CC.FLAGS_CENTER )
        QP.AddToLayout( button_hbox, self._cog_button, CC.FLAGS_CENTER )
        
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._duplicates_auto_resolution_rules_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        #
        
        self._rules_list_updater = self._InitialiseUpdater()
        
        self._rules_list_updater.update()
        
        CG.client_controller.sub( self, 'NotifyWorkComplete', 'notify_duplicates_auto_resolution_work_complete' )
        
    
    def _CanWorkHard( self ):
        
        rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
        working_hard_rules = CG.client_controller.duplicates_auto_resolution_manager.GetWorkingHard()
        
        return True in ( rule.CanWorkHard() or rule in working_hard_rules for rule in rules )
        
    
    def _ConvertRuleToDisplayTuple( self, duplicates_auto_resolution_rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        name = duplicates_auto_resolution_rule.GetName()
        
        search_status = duplicates_auto_resolution_rule.GetSearchSummary()
        
        running_status = CG.client_controller.duplicates_auto_resolution_manager.GetRunningStatus( duplicates_auto_resolution_rule )
        
        return ( name, search_status, running_status )
        
    
    _ConvertRuleToSortTuple = _ConvertRuleToDisplayTuple
    
    def _DeleteOrphanRules( self ):
        
        text = f'This will scan the database for rule definitions in the primary rule module and the backing object in the serialisable module. If a rule is in one location but not the other (probably due to hard drive damage), the rule will be deleted.'
        text += '\n\n'
        text += 'This command is useful if your client is shouting about missing rules, otherwise it is pointless.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.Write( 'duplicate_auto_resolution_maintenance_fix_orphan_rules' )
            
            self._rules_list_updater.update()
            
        
    
    def _DeleteOrphanPotentialPairs( self ):
        
        text = f'This will scan the primary potential pairs table. If any are missing from the auto-resolution rule potential pair cache, they will be added. Orphans will be deleted.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.Write( 'duplicate_auto_resolution_maintenance_fix_orphan_potential_pairs' )
            
            self._rules_list_updater.update()
            
        
    
    def _Edit( self ):
        
        def do_it_qt( duplicates_auto_resolution_rules: list[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ] ):
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit rules' ) as dlg:
                
                panel = EditDuplicatesAutoResolutionRulesPanel( dlg, duplicates_auto_resolution_rules )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    edited_duplicates_auto_resolution_rules = panel.GetValue()
                    
                    CG.client_controller.duplicates_auto_resolution_manager.SetRules( edited_duplicates_auto_resolution_rules )
                    
                    self._rules_list_updater.update()
                    
                
            
        
        def do_it():
            
            with EDIT_RULES_DIALOG_LOCK:
                
                job_status = ClientThreading.JobStatus()
                
                job_status.SetStatusText( 'Waiting for current rules work to finish.' )
                
                CG.client_controller.pub( 'message', job_status )
                
                try:
                    
                    work_edit_lock = CG.client_controller.duplicates_auto_resolution_manager.GetEditWorkLock()
                    
                    while not work_edit_lock.acquire( False ):
                        
                        time.sleep( 0.1 )
                        
                        if HG.started_shutdown:
                            
                            return
                            
                        
                    
                finally:
                    
                    job_status.FinishAndDismiss()
                    
                
                # we have the lock
                
                try:
                    
                    CG.client_controller.pub( 'edit_duplicates_auto_resolution_rules_dialog_opening' )
                    
                    rules = CG.client_controller.duplicates_auto_resolution_manager.GetRules()
                    
                    CG.client_controller.CallBlockingToQt( self, do_it_qt, rules )
                    
                finally:
                    
                    work_edit_lock.release()
                    
                
            
        
        CG.client_controller.CallToThread( do_it )
        
    
    def _FlipBoolean( self, name ):
        
        CG.client_controller.new_options.FlipBoolean( name )
        
        CG.client_controller.duplicates_auto_resolution_manager.Wake()
        
        self._rules_list_updater.update()
        
    
    def _FlipWorkingHard( self ):
        
        rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
        
        working_hard_rules = CG.client_controller.duplicates_auto_resolution_manager.GetWorkingHard()
        
        for rule in rules:
            
            if rule in working_hard_rules:
                
                CG.client_controller.duplicates_auto_resolution_manager.SetWorkingHard( rule, False )
                
            elif rule.CanWorkHard():
                
                CG.client_controller.duplicates_auto_resolution_manager.SetWorkingHard( rule, True )
                
            
        
        self._rules_list_updater.update()
        
    
    def _InitialiseUpdater( self ):
        
        def loading_callable():
            
            pass
            
        
        def work_callable( args ):
            
            rules = CG.client_controller.Read( 'duplicate_auto_resolution_rules_with_counts' )
            
            return rules
            
        
        def publish_callable( rules ):
            
            self._duplicates_auto_resolution_rules.SetData( rules )
            
        
        updater = ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
        return updater
        
    
    def _RegenNumbers( self ):
        
        text = f'This will delete all the cached pair counts for your rules. If it seems there is a miscount somewhere (e.g. a pending pair to search that never clears), try hitting this.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.Write( 'duplicate_auto_resolution_maintenance_regen_numbers' )
            
            self._rules_list_updater.update()
            
        
    
    def _ResetDeclined( self ):
        
        rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
        
        if len( rules ) == 0:
            
            rules = self._duplicates_auto_resolution_rules.GetData()
            
            if len( rules ) == 0:
                
                return
                
            
        
        text = f'This will command the database to repeal all user-declined decisions for these {HydrusNumbers.ToHumanInt(len(rules))} rules. Do this if you want to re-do them or have decided to set this rule to fully automatic and are happy it can now handle them appropriately.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.duplicates_auto_resolution_manager.ResetRuleDeclined( rules )
            
            self._rules_list_updater.update()
            
        
    
    def _ResetSearch( self ):
        
        rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
        
        if len( rules ) == 0:
            
            rules = self._duplicates_auto_resolution_rules.GetData()
            
            if len( rules ) == 0:
                
                return
                
            
        
        text = f'This will command the database to re-search these {HydrusNumbers.ToHumanInt(len(rules))} rules. It will not undo any user-declined decisions. There is no point to running this unless you suspect a miscount or other sync bug.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.duplicates_auto_resolution_manager.ResetRuleSearchProgress( rules )
            
            self._rules_list_updater.update()
            
        
    
    def _ResetTest( self ):
        
        rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
        
        if len( rules ) == 0:
            
            rules = self._duplicates_auto_resolution_rules.GetData()
            
            if len( rules ) == 0:
                
                return
                
            
        
        text = f'This will command the database to re-test the pending/fails for these {HydrusNumbers.ToHumanInt(len(rules))} rules. It will not undo any user-declined decisions. There is no point to running this unless you suspect a miscount or other sync bug.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.duplicates_auto_resolution_manager.ResetRuleTestProgress( rules )
            
            self._rules_list_updater.update()
            
        
    
    def _ReviewActions( self ):
        
        rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
        
        for rule in rules:
            
            frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'review duplicate auto-resolution actions' )
            
            panel = ClientGUIDuplicatesAutoResolutionRuleReview.ReviewActionsPanel( frame, rule )
            
            frame.SetPanel( panel )
            
        
    
    def _ShowCogMenu( self ):
        
        rules = self._duplicates_auto_resolution_rules.GetData( only_selected = True )
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        ClientGUIMenus.AppendMenuCheckItem( menu, 'work on these rules during idle time', 'Allow the client to work on auto-resolution rules when you are not using the program.', CG.client_controller.new_options.GetBoolean( 'maintain_similar_files_duplicate_pairs_during_idle' ), self._FlipBoolean, 'maintain_similar_files_duplicate_pairs_during_idle' )
        ClientGUIMenus.AppendMenuCheckItem( menu, 'work on these rules during normal time', 'Allow the client to work on auto-resolution rules when you are using the program.', CG.client_controller.new_options.GetBoolean( 'duplicates_auto_resolution_during_active' ), self._FlipBoolean, 'duplicates_auto_resolution_during_active' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if len( rules ) == 0:
            
            ClientGUIMenus.AppendMenuItem( menu, f'reset search on all rules', 'Reset the search for all your rules.', self._ResetSearch )
            ClientGUIMenus.AppendMenuItem( menu, f'reset test on all rules', 'Reset the test for all your rules.', self._ResetTest )
            ClientGUIMenus.AppendMenuItem( menu, f'reset user declined on all rules', 'Reset the test for all your rules.', self._ResetDeclined )
            
        else:
            
            ClientGUIMenus.AppendMenuItem( menu, f'reset search on {HydrusNumbers.ToHumanInt( len( rules ) )} selected rules', 'Reset the search for the given rules.', self._ResetSearch )
            ClientGUIMenus.AppendMenuItem( menu, f'reset test on {HydrusNumbers.ToHumanInt( len( rules ) )} selected rules', 'Reset the search for the given rules.', self._ResetTest )
            ClientGUIMenus.AppendMenuItem( menu, f'reset user declined search on {HydrusNumbers.ToHumanInt( len( rules ) )} selected rules', 'Reset the search for the given rules.', self._ResetDeclined )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'maintenance: delete orphan rules', 'Scan for rules that are partly missing (probably from hard drive damage) and delete them.', self._DeleteOrphanRules )
        ClientGUIMenus.AppendMenuItem( menu, 'maintenance: fix orphan potential pairs', 'Scan for potential pairs in your rule cache that are no longer pertinent and delete them.', self._DeleteOrphanPotentialPairs )
        ClientGUIMenus.AppendMenuItem( menu, 'maintenance: regen cached numbers', 'Clear cached pair counts and regenerate from source.', self._RegenNumbers )
        
        CGC.core().PopupMenu( self._cog_button, menu )
        
    
    def _UpdateList( self ):
        
        self._rules_list_updater.update()
        
    
    def NotifyWorkComplete( self ):
        
        self._rules_list_updater.update()
        
    
