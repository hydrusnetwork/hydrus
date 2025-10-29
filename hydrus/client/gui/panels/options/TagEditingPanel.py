from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class TagEditingPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        #
        
        self._tag_services_panel = ClientGUICommon.StaticBox( self, 'tag dialogs' )
        
        self._use_listbook_for_tag_service_panels = QW.QCheckBox( self._tag_services_panel )
        
        self._expand_parents_on_storage_taglists = QW.QCheckBox( self._tag_services_panel )
        self._show_parent_decorators_on_storage_taglists = QW.QCheckBox( self._tag_services_panel )
        self._show_sibling_decorators_on_storage_taglists = QW.QCheckBox( self._tag_services_panel )
        
        self._num_recent_petition_reasons = ClientGUICommon.BetterSpinBox( self._tag_services_panel, initial = 5, min = 0, max = 100 )
        tt = 'In manage tags, tag siblings, and tag parents, you may be asked to provide a reason with a petition you make to a hydrus repository. There are some fixed reasons, but the dialog can also remember what you recently typed. This controls how many recent reasons it will remember.'
        self._num_recent_petition_reasons.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._save_default_tag_service_tab_on_change = QW.QCheckBox( self._tag_services_panel )
        
        self._default_tag_service_tab = ClientGUICommon.BetterChoice( self._tag_services_panel )
        
        #
        
        self._write_autocomplete_panel = ClientGUICommon.StaticBox( self, 'tag edit autocomplete' )
        
        self._ac_select_first_with_count = QW.QCheckBox( self._write_autocomplete_panel )
        
        self._skip_yesno_on_write_autocomplete_multiline_paste = QW.QCheckBox( self._write_autocomplete_panel )
        
        self._ac_write_list_height_num_chars = ClientGUICommon.BetterSpinBox( self._write_autocomplete_panel, min = 1, max = 128 )
        
        self._expand_parents_on_storage_autocomplete_taglists = QW.QCheckBox( self._write_autocomplete_panel )
        self._show_parent_decorators_on_storage_autocomplete_taglists = QW.QCheckBox( self._write_autocomplete_panel )
        self._show_sibling_decorators_on_storage_autocomplete_taglists = QW.QCheckBox( self._write_autocomplete_panel )
        
        #
        
        services = CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
        
        for service in services:
            
            self._default_tag_service_tab.addItem( service.GetName(), service.GetServiceKey() )
            
        
        self._default_tag_service_tab.SetValue( self._new_options.GetKey( 'default_tag_service_tab' ) )
        
        self._num_recent_petition_reasons.setValue( self._new_options.GetInteger( 'num_recent_petition_reasons' ) )
        
        self._use_listbook_for_tag_service_panels.setChecked( self._new_options.GetBoolean( 'use_listbook_for_tag_service_panels' ) )
        self._use_listbook_for_tag_service_panels.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you have many tag services, you might prefer to use a vertical list to navigate your various tag dialogs.' ) )
        
        self._save_default_tag_service_tab_on_change.setChecked( self._new_options.GetBoolean( 'save_default_tag_service_tab_on_change' ) )
        
        self._ac_select_first_with_count.setChecked( self._new_options.GetBoolean( 'ac_select_first_with_count' ) )
        
        self._ac_write_list_height_num_chars.setValue( self._new_options.GetInteger( 'ac_write_list_height_num_chars' ) )
        
        self._expand_parents_on_storage_taglists.setChecked( self._new_options.GetBoolean( 'expand_parents_on_storage_taglists' ) )
        self._expand_parents_on_storage_taglists.setToolTip( ClientGUIFunctions.WrapToolTip( 'This affects taglists in places like the manage tags dialog, where you edit tags as they actually are, and implied parents hang below tags.' ) )
        
        self._skip_yesno_on_write_autocomplete_multiline_paste.setChecked( self._new_options.GetBoolean( 'skip_yesno_on_write_autocomplete_multiline_paste' ) )
        self._skip_yesno_on_write_autocomplete_multiline_paste.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you paste multiline content into the text box of an edit autocomplete that has a paste button, it will ask you if you want to add what you pasted as separate tags. Check this to skip that yes/no test and just do it every time.' ) )
        
        self._expand_parents_on_storage_autocomplete_taglists.setChecked( self._new_options.GetBoolean( 'expand_parents_on_storage_autocomplete_taglists' ) )
        self._expand_parents_on_storage_autocomplete_taglists.setToolTip( ClientGUIFunctions.WrapToolTip( 'This affects the autocomplete results taglist.' ) )
        
        self._show_parent_decorators_on_storage_taglists.setChecked( self._new_options.GetBoolean( 'show_parent_decorators_on_storage_taglists' ) )
        self._show_parent_decorators_on_storage_taglists.setToolTip( ClientGUIFunctions.WrapToolTip( 'This affects taglists in places like the manage tags dialog, where you edit tags as they actually are, and implied parents either hang below tags or summarise in a suffix.' ) )
        
        self._show_parent_decorators_on_storage_autocomplete_taglists.setChecked( self._new_options.GetBoolean( 'show_parent_decorators_on_storage_autocomplete_taglists' ) )
        self._show_parent_decorators_on_storage_autocomplete_taglists.setToolTip( ClientGUIFunctions.WrapToolTip( 'This affects the autocomplete results taglist.' ) )
        
        self._show_sibling_decorators_on_storage_taglists.setChecked( self._new_options.GetBoolean( 'show_sibling_decorators_on_storage_taglists' ) )
        self._show_sibling_decorators_on_storage_taglists.setToolTip( ClientGUIFunctions.WrapToolTip( 'This affects taglists in places like the manage tags dialog, where you edit tags as they actually are, and siblings summarise in a suffix.' ) )
        
        self._show_sibling_decorators_on_storage_autocomplete_taglists.setChecked( self._new_options.GetBoolean( 'show_sibling_decorators_on_storage_autocomplete_taglists' ) )
        self._show_sibling_decorators_on_storage_autocomplete_taglists.setToolTip( ClientGUIFunctions.WrapToolTip( 'This affects the autocomplete results taglist.' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'Use listbook instead of tabbed notebook for tag service panels: ', self._use_listbook_for_tag_service_panels ) )
        rows.append( ( 'Remember last used default tag service in manage tag dialogs: ', self._save_default_tag_service_tab_on_change ) )
        rows.append( ( 'Default tag service in tag dialogs: ', self._default_tag_service_tab ) )
        rows.append( ( 'Number of recent petition reasons to remember in dialogs: ', self._num_recent_petition_reasons ) )
        rows.append( ( 'Show parent info by default on edit/write taglists: ', self._show_parent_decorators_on_storage_taglists ) )
        rows.append( ( 'Show parents expanded by default on edit/write taglists: ', self._expand_parents_on_storage_taglists ) )
        rows.append( ( 'Show sibling info by default on edit/write taglists: ', self._show_sibling_decorators_on_storage_taglists ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._tag_services_panel, rows )
        
        self._tag_services_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        #
        
        message = 'This tag autocomplete appears in the manage tags dialog and other places where you edit a list of tags.'
        
        st = ClientGUICommon.BetterStaticText( self._write_autocomplete_panel, label = message )
        
        self._write_autocomplete_panel.Add( st, CC.FLAGS_CENTER )
        
        rows = []
        
        rows.append( ( 'By default, select the first tag result with actual count in write-autocomplete: ', self._ac_select_first_with_count ) )
        rows.append( ( 'When pasting multiline content into a write-autocomplete, skip the yes/no check: ', self._skip_yesno_on_write_autocomplete_multiline_paste ) )
        rows.append( ( 'Show parent info by default on edit/write autocomplete taglists: ', self._show_parent_decorators_on_storage_autocomplete_taglists ) )
        rows.append( ( 'Show parents expanded by default on edit/write autocomplete taglists: ', self._expand_parents_on_storage_autocomplete_taglists ) )
        rows.append( ( 'Show sibling info by default on edit/write autocomplete taglists: ', self._show_sibling_decorators_on_storage_autocomplete_taglists ) )
        rows.append( ( 'Autocomplete list height: ', self._ac_write_list_height_num_chars ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._write_autocomplete_panel, rows )
        
        self._write_autocomplete_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._tag_services_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._write_autocomplete_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._UpdateDefaultTagServiceControl()
        
        self._save_default_tag_service_tab_on_change.clicked.connect( self._UpdateDefaultTagServiceControl )
        
    
    def _UpdateDefaultTagServiceControl( self ):
        
        enabled = not self._save_default_tag_service_tab_on_change.isChecked()
        
        self._default_tag_service_tab.setEnabled( enabled )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetBoolean( 'use_listbook_for_tag_service_panels', self._use_listbook_for_tag_service_panels.isChecked() )
        
        self._new_options.SetInteger( 'num_recent_petition_reasons', self._num_recent_petition_reasons.value() )
        
        self._new_options.SetBoolean( 'ac_select_first_with_count', self._ac_select_first_with_count.isChecked() )
        
        self._new_options.SetInteger( 'ac_write_list_height_num_chars', self._ac_write_list_height_num_chars.value() )
        
        self._new_options.SetBoolean( 'skip_yesno_on_write_autocomplete_multiline_paste', self._skip_yesno_on_write_autocomplete_multiline_paste.isChecked() )
        
        self._new_options.SetBoolean( 'show_parent_decorators_on_storage_taglists', self._show_parent_decorators_on_storage_taglists.isChecked() )
        self._new_options.SetBoolean( 'show_parent_decorators_on_storage_autocomplete_taglists', self._show_parent_decorators_on_storage_autocomplete_taglists.isChecked() )
        self._new_options.SetBoolean( 'expand_parents_on_storage_taglists', self._expand_parents_on_storage_taglists.isChecked() )
        self._new_options.SetBoolean( 'expand_parents_on_storage_autocomplete_taglists', self._expand_parents_on_storage_autocomplete_taglists.isChecked() )
        self._new_options.SetBoolean( 'show_sibling_decorators_on_storage_taglists', self._show_sibling_decorators_on_storage_taglists.isChecked() )
        self._new_options.SetBoolean( 'show_sibling_decorators_on_storage_autocomplete_taglists', self._show_sibling_decorators_on_storage_autocomplete_taglists.isChecked() )
        
        self._new_options.SetBoolean( 'save_default_tag_service_tab_on_change', self._save_default_tag_service_tab_on_change.isChecked() )
        self._new_options.SetKey( 'default_tag_service_tab', self._default_tag_service_tab.GetValue() )
        
    
