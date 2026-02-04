from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.search import ClientGUILocation
from hydrus.client.gui.widgets import ClientGUICommon

class FileSearchPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        #
        
        self._read_autocomplete_panel = ClientGUICommon.StaticBox( self, 'file search autocomplete' )
        
        location_context = self._new_options.GetDefaultLocalLocationContext()
        
        self._active_search_predicates_height_num_chars = ClientGUICommon.BetterSpinBox( self._read_autocomplete_panel, min = 1, max = 128 )
        tt = 'This is the list _above_ the tag autocomplete input on normal file search pages, where the currently active search predicates are listed. If you use regularly many predicates, boost this!'
        self._active_search_predicates_height_num_chars.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._default_local_location_context = ClientGUILocation.LocationSearchContextButton( self._read_autocomplete_panel, location_context )
        self._default_local_location_context.setToolTip( ClientGUIFunctions.WrapToolTip( 'This initialised into a bunch of dialogs across the program as a fallback. You can probably leave it alone forever, but if you delete or move away from \'my files\' as your main place to do work, please update it here.' ) )
        
        self._default_local_location_context.SetOnlyImportableDomainsAllowed( True )
        
        self._default_tag_service_search_page = ClientGUICommon.BetterChoice( self._read_autocomplete_panel )
        
        self._default_search_synchronised = QW.QCheckBox( self._read_autocomplete_panel )
        tt = 'This refers to the button on the autocomplete dropdown that enables new searches to start. If this is on, then new search pages will search as soon as you enter the first search predicate. If off, no search will happen until you switch it back on.'
        self._default_search_synchronised.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._autocomplete_float_main_gui = QW.QCheckBox( self._read_autocomplete_panel )
        tt = 'The autocomplete dropdown can either \'float\' on top of the main window, or if that does not work well for you, it can embed into the parent page panel.'
        self._autocomplete_float_main_gui.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._ac_read_list_height_num_chars = ClientGUICommon.BetterSpinBox( self._read_autocomplete_panel, min = 1, max = 128 )
        tt = 'This is the dropdown list _below_ the tag autocomplete input that shows the search results on what you type.'
        self._ac_read_list_height_num_chars.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._show_system_everything = QW.QCheckBox( self._read_autocomplete_panel )
        tt = 'After users get some experience with the program and a larger collection, they tend to have less use for system:everything.'
        self._show_system_everything.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        misc_panel = ClientGUICommon.StaticBox( self, 'file search' )
        
        self._forced_search_limit = ClientGUICommon.NoneableSpinCtrl( misc_panel, 10000, min = 1, max = 100000000 )
        self._forced_search_limit.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is overruled if you set an explicit system:limit larger than it.' ) )
        
        self._refresh_search_page_on_system_limited_sort_changed = QW.QCheckBox( misc_panel )
        tt = 'This is a fairly advanced option. It only fires if the sort is simple enough for the database to do the limited sort. Some people like it, some do not. If you turn it on and _do_ want to sort a limited set by a different sort, hit "searching immediately" to pause search updates.'
        self._refresh_search_page_on_system_limited_sort_changed.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._default_tag_service_search_page.addItem( 'all known tags', CC.COMBINED_TAG_SERVICE_KEY )
        
        services = CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
        
        for service in services:
            
            self._default_tag_service_search_page.addItem( service.GetName(), service.GetServiceKey() )
            
        
        self._default_tag_service_search_page.SetValue( self._new_options.GetKey( 'default_tag_service_search_page' ) )
        
        self._default_search_synchronised.setChecked( self._new_options.GetBoolean( 'default_search_synchronised' ) )
        
        self._autocomplete_float_main_gui.setChecked( self._new_options.GetBoolean( 'autocomplete_float_main_gui' ) )
        
        self._active_search_predicates_height_num_chars.setValue( self._new_options.GetInteger( 'active_search_predicates_height_num_chars' ) )
        self._ac_read_list_height_num_chars.setValue( self._new_options.GetInteger( 'ac_read_list_height_num_chars' ) )
        
        self._show_system_everything.setChecked( self._new_options.GetBoolean( 'show_system_everything' ) )
        
        self._forced_search_limit.SetValue( self._new_options.GetNoneableInteger( 'forced_search_limit' ) )
        
        self._refresh_search_page_on_system_limited_sort_changed.setChecked( self._new_options.GetBoolean( 'refresh_search_page_on_system_limited_sort_changed' ) )
        
        #
        
        message = 'This tag autocomplete appears in file search pages and other places where you use tags and system predicates to search for files.'
        
        st = ClientGUICommon.BetterStaticText( self._read_autocomplete_panel, label = message )
        
        self._read_autocomplete_panel.Add( st, CC.FLAGS_CENTER )
        
        rows = []
        
        rows.append( ( 'Active Search Predicates list height:', self._active_search_predicates_height_num_chars ) )
        rows.append( ( 'Default/Fallback local file search location:', self._default_local_location_context ) )
        rows.append( ( 'Default tag service in search pages:', self._default_tag_service_search_page ) )
        rows.append( ( 'Autocomplete dropdown floats over file search pages:', self._autocomplete_float_main_gui ) )
        rows.append( ( 'Autocomplete list height:', self._ac_read_list_height_num_chars ) )
        rows.append( ( 'Start new search pages in \'searching immediately\':', self._default_search_synchronised ) )
        rows.append( ( 'Show system:everything:', self._show_system_everything ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._read_autocomplete_panel, rows )
        
        self._read_autocomplete_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        #
        
        rows = []
        
        rows.append( ( 'Implicit system:limit for all searches: ', self._forced_search_limit ) )
        rows.append( ( 'If explicit system:limit, then refresh search when file sort changes: ', self._refresh_search_page_on_system_limited_sort_changed ) )
        
        gridbox = ClientGUICommon.WrapInGrid( misc_panel, rows )
        
        misc_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._read_autocomplete_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, misc_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetInteger( 'active_search_predicates_height_num_chars', self._active_search_predicates_height_num_chars.value() )
        
        self._new_options.SetKey( 'default_tag_service_search_page', self._default_tag_service_search_page.GetValue() )
        
        self._new_options.SetDefaultLocalLocationContext( self._default_local_location_context.GetValue() )
        
        self._new_options.SetBoolean( 'default_search_synchronised', self._default_search_synchronised.isChecked() )
        
        self._new_options.SetBoolean( 'autocomplete_float_main_gui', self._autocomplete_float_main_gui.isChecked() )
        
        self._new_options.SetInteger( 'ac_read_list_height_num_chars', self._ac_read_list_height_num_chars.value() )
        
        self._new_options.SetBoolean( 'show_system_everything', self._show_system_everything.isChecked() )
        
        self._new_options.SetNoneableInteger( 'forced_search_limit', self._forced_search_limit.GetValue() )
        
        self._new_options.SetBoolean( 'refresh_search_page_on_system_limited_sort_changed', self._refresh_search_page_on_system_limited_sort_changed.isChecked() )
        
    
