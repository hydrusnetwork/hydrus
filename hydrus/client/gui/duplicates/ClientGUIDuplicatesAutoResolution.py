import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions

from hydrus.client import ClientConstants as CC
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
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
        
        self._duplicates_auto_resolution_rules = ClientGUIListCtrl.BetterListCtrlTreeView( self._duplicates_auto_resolution_rules_panel, CGLC.COLUMN_LIST_EXPORT_FOLDERS.ID, 12, model, use_simple_delete = True, activation_callback = self._Edit )
        
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
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                duplicates_auto_resolution_rule = panel.GetValue()
                
                duplicates_auto_resolution_rule.SetNonDupeName( self._GetExistingNames() )
                
                self._duplicates_auto_resolution_rules.AddDatas( ( duplicates_auto_resolution_rule, ), select_sort_and_scroll = True )
                
            
        
    
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
        comparator_summary = duplicates_auto_resolution_rule.GetComparatorSummary()
        action_summary = duplicates_auto_resolution_rule.GetActionSummary()
        search_status = duplicates_auto_resolution_rule.GetSearchSummary()
        paused = duplicates_auto_resolution_rule.IsPaused()
        
        pretty_paused = 'yes' if paused else ''
        
        return ( name, rule_summary, comparator_summary, action_summary, search_status, pretty_paused )
        
    
    _ConvertRuleToSortTuple = _ConvertRuleToDisplayTuple
    
    def _Edit( self ):
        
        duplicates_auto_resolution_rule: typing.Optional[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ] = self._duplicates_auto_resolution_rules.GetTopSelectedData()
        
        if duplicates_auto_resolution_rule is None:
            
            return
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit export folder' ) as dlg:
            
            panel = EditDuplicatesAutoResolutionRulePanel( dlg, duplicates_auto_resolution_rule )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
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
        
        self._duplicates_auto_resolution_rules.AddDatas( ( duplicates_auto_resolution_rule, ), select_sort_and_scroll = True )
        
    
    def GetValue( self ) -> typing.List[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ]:
        
        return self._duplicates_auto_resolution_rules.GetData()
        
    

class EditDuplicatesAutoResolutionRulePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, duplicates_auto_resolution_rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        super().__init__( parent )
        
        self._duplicates_auto_resolution_rule = duplicates_auto_resolution_rule
        
        self._rule_panel = ClientGUICommon.StaticBox( self, 'rule' )
        
        self._name = QW.QLineEdit( self._rule_panel )
        
        # paused
        # search gubbins
        # comparator gubbins
        # some way to test-run searches and see pair counts, and, eventually, a way to preview some pairs and the auto-choices we'd see
        
        #
        
        self._name.setText( self._duplicates_auto_resolution_rule.GetName() )
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._rule_panel, rows )
        
        self._rule_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        st = ClientGUICommon.BetterStaticText( self, 'Hey, this system does not work yet! This UI is just a placeholder!' )
        st.setWordWrap( True )
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._rule_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 1 )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        name = self._name.text()
        
        duplicates_auto_resolution_rule = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( name )
        
        # paused and search gubbins, everything else
        
        # TODO: transfer any cached search data, including what we may have re-fetched in this panel's work, to the new folder
        
        return duplicates_auto_resolution_rule
        
    

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
        
        self._duplicates_auto_resolution_rules = ClientGUIListCtrl.BetterListCtrlTreeView( self._duplicates_auto_resolution_rules_panel, CGLC.COLUMN_LIST_EXPORT_FOLDERS.ID, 12, model, use_simple_delete = True, activation_callback = self._Edit )
        
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
        vbox.addStretch( 1 )
        
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
            
            running_status = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionManager.instance().GetRunningStatus( duplicates_auto_resolution_rule.GetId() )
            
        
        return ( name, search_status, running_status )
        
    
    _ConvertRuleToSortTuple = _ConvertRuleToDisplayTuple
    
    def _Edit( self ):
        
        # TODO: Some sort of async delay as we wait for any current work to halt and the manager to save
        
        duplicates_auto_resolution_rules = self._duplicates_auto_resolution_rules.GetData()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit rules' ) as dlg:
            
            panel = EditDuplicatesAutoResolutionRulesPanel( dlg, duplicates_auto_resolution_rules )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                edited_duplicates_auto_resolution_rules = panel.GetValue()
                
                ClientDuplicatesAutoResolution.DuplicatesAutoResolutionManager.instance().SetRules( edited_duplicates_auto_resolution_rules )
                
            
        
    
    def _ResetListData( self ):
        
        rules = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionManager.instance().GetRules()
        
        self._duplicates_auto_resolution_rules.SetData( rules )
        
    
    def _RunNow( self ):
        
        pass
        
    
