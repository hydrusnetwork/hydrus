from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientTags

class TagSuggestionsPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        suggested_tags_panel = ClientGUICommon.StaticBox( self, 'suggested tags' )
        
        self._suggested_tags_width = ClientGUICommon.BetterSpinBox( suggested_tags_panel, min=20, max=65535 )
        
        self._suggested_tags_layout = ClientGUICommon.BetterChoice( suggested_tags_panel )
        
        self._suggested_tags_layout.addItem( 'notebook', 'notebook' )
        self._suggested_tags_layout.addItem( 'side-by-side', 'columns' )
        
        self._default_suggested_tags_notebook_page = ClientGUICommon.BetterChoice( suggested_tags_panel )
        
        for item in [ 'favourites', 'related', 'file_lookup_scripts', 'recent' ]:
            
            label = 'most used' if item == 'favourites' else item
            
            self._default_suggested_tags_notebook_page.addItem( label, item )
            
        
        suggest_tags_panel_notebook = QW.QTabWidget( suggested_tags_panel )
        
        #
        
        suggested_tags_favourites_panel = QW.QWidget( suggest_tags_panel_notebook )
        
        suggested_tags_favourites_panel.setMinimumWidth( 400 )
        
        self._suggested_favourites_services = ClientGUICommon.BetterChoice( suggested_tags_favourites_panel )
        
        tag_services = CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
        
        for tag_service in tag_services:
            
            self._suggested_favourites_services.addItem( tag_service.GetName(), tag_service.GetServiceKey() )
            
        
        self._suggested_favourites = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( suggested_tags_favourites_panel, CC.COMBINED_TAG_SERVICE_KEY, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE )
        
        self._current_suggested_favourites_service = None
        
        self._suggested_favourites_dict = {}
        
        default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
        
        self._suggested_favourites_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( suggested_tags_favourites_panel, self._suggested_favourites.AddTags, default_location_context, CC.COMBINED_TAG_SERVICE_KEY, show_paste_button = True )
        
        self._suggested_favourites.tagsChanged.connect( self._suggested_favourites_input.SetContextTags )
        
        self._suggested_favourites_input.externalCopyKeyPressEvent.connect( self._suggested_favourites.keyPressEvent )
        
        #
        
        suggested_tags_related_panel = QW.QWidget( suggest_tags_panel_notebook )
        
        self._show_related_tags = QW.QCheckBox( suggested_tags_related_panel )
        
        self._related_tags_search_1_duration_ms = ClientGUICommon.BetterSpinBox( suggested_tags_related_panel, min=50, max=60000 )
        self._related_tags_search_2_duration_ms = ClientGUICommon.BetterSpinBox( suggested_tags_related_panel, min=50, max=60000 )
        self._related_tags_search_3_duration_ms = ClientGUICommon.BetterSpinBox( suggested_tags_related_panel, min=50, max=60000 )
        
        self._related_tags_concurrence_threshold_percent = ClientGUICommon.BetterSpinBox( suggested_tags_related_panel, min = 1, max = 100 )
        tt = 'The related tags system looks for tags that tend to be used on the same files. Here you can set how strict it is. How many percent of tag A\'s files must tag B on for tag B to be a good suggestion? Higher numbers will mean fewer but more relevant suggestions.'
        self._related_tags_concurrence_threshold_percent.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        search_tag_slices_weight_box = ClientGUICommon.StaticBox( suggested_tags_related_panel, 'adjust scores by search tags' )
        
        search_tag_slices_weight_panel = ClientGUIListCtrl.BetterListCtrlPanel( search_tag_slices_weight_box )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_TAG_SLICE_WEIGHT.ID, self._ConvertTagSliceAndWeightToDisplayTuple, self._ConvertTagSliceAndWeightToSortTuple )
        
        self._search_tag_slices_weights = ClientGUIListCtrl.BetterListCtrlTreeView( search_tag_slices_weight_panel, 8, model, activation_callback = self._EditSearchTagSliceWeight, use_simple_delete = True, can_delete_callback = self._CanDeleteSearchTagSliceWeight )
        tt = 'ADVANCED! These weights adjust the ranking scores of suggested tags by the tag type that searched for them. Set to 0 to not search with that type of tag.'
        self._search_tag_slices_weights.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        search_tag_slices_weight_panel.SetListCtrl( self._search_tag_slices_weights )
        
        search_tag_slices_weight_panel.AddButton( 'add', self._AddSearchTagSliceWeight )
        search_tag_slices_weight_panel.AddButton( 'edit', self._EditSearchTagSliceWeight, enabled_only_on_single_selection = True )
        search_tag_slices_weight_panel.AddDeleteButton( enabled_check_func = self._CanDeleteSearchTagSliceWeight )
        
        #
        
        result_tag_slices_weight_box = ClientGUICommon.StaticBox( suggested_tags_related_panel, 'adjust scores by suggested tags' )
        
        result_tag_slices_weight_panel = ClientGUIListCtrl.BetterListCtrlPanel( result_tag_slices_weight_box )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_TAG_SLICE_WEIGHT.ID, self._ConvertTagSliceAndWeightToDisplayTuple, self._ConvertTagSliceAndWeightToSortTuple )
        
        self._result_tag_slices_weights = ClientGUIListCtrl.BetterListCtrlTreeView( result_tag_slices_weight_panel, 8, model, activation_callback = self._EditResultTagSliceWeight, use_simple_delete = True, can_delete_callback = self._CanDeleteResultTagSliceWeight )
        tt = 'ADVANCED! These weights adjust the ranking scores of suggested tags by their tag type. Set to 0 to not suggest that type of tag at all.'
        self._result_tag_slices_weights.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        result_tag_slices_weight_panel.SetListCtrl( self._result_tag_slices_weights )
        
        result_tag_slices_weight_panel.AddButton( 'add', self._AddResultTagSliceWeight )
        result_tag_slices_weight_panel.AddButton( 'edit', self._EditResultTagSliceWeight, enabled_only_on_single_selection = True )
        result_tag_slices_weight_panel.AddDeleteButton( enabled_check_func = self._CanDeleteResultTagSliceWeight )
        
        #
        
        suggested_tags_file_lookup_script_panel = QW.QWidget( suggest_tags_panel_notebook )
        
        self._show_file_lookup_script_tags = QW.QCheckBox( suggested_tags_file_lookup_script_panel )
        
        self._favourite_file_lookup_script = ClientGUICommon.BetterChoice( suggested_tags_file_lookup_script_panel )
        
        script_names = sorted( CG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP ) )
        
        for name in script_names:
            
            self._favourite_file_lookup_script.addItem( name, name )
            
        
        #
        
        suggested_tags_recent_panel = QW.QWidget( suggest_tags_panel_notebook )
        
        self._num_recent_tags = ClientGUICommon.NoneableSpinCtrl( suggested_tags_recent_panel, 20, message = 'number of recent tags to show', min = 1, none_phrase = 'do not show' )
        
        #
        
        self._suggested_tags_width.setValue( self._new_options.GetInteger( 'suggested_tags_width' ) )
        
        self._suggested_tags_layout.SetValue( self._new_options.GetNoneableString( 'suggested_tags_layout' ) )
        
        self._default_suggested_tags_notebook_page.SetValue( self._new_options.GetString( 'default_suggested_tags_notebook_page' ) )
        
        #
        
        self._show_related_tags.setChecked( self._new_options.GetBoolean( 'show_related_tags' ) )
        
        self._related_tags_search_1_duration_ms.setValue( self._new_options.GetInteger( 'related_tags_search_1_duration_ms' ) )
        self._related_tags_search_2_duration_ms.setValue( self._new_options.GetInteger( 'related_tags_search_2_duration_ms' ) )
        self._related_tags_search_3_duration_ms.setValue( self._new_options.GetInteger( 'related_tags_search_3_duration_ms' ) )
        
        self._related_tags_concurrence_threshold_percent.setValue( self._new_options.GetInteger( 'related_tags_concurrence_threshold_percent' ) )

        ( related_tags_search_tag_slices_weight_percent, related_tags_result_tag_slices_weight_percent ) = self._new_options.GetRelatedTagsTagSliceWeights()
        
        self._search_tag_slices_weights.SetData( related_tags_search_tag_slices_weight_percent )
        self._result_tag_slices_weights.SetData( related_tags_result_tag_slices_weight_percent )
        
        self._show_file_lookup_script_tags.setChecked( self._new_options.GetBoolean( 'show_file_lookup_script_tags' ) )
        
        self._favourite_file_lookup_script.SetValue( self._new_options.GetNoneableString( 'favourite_file_lookup_script' ) )
        
        self._num_recent_tags.SetValue( self._new_options.GetNoneableInteger( 'num_recent_tags' ) )
        
        #
        
        panel_vbox = QP.VBoxLayout()
        
        st = ClientGUICommon.BetterStaticText( suggested_tags_favourites_panel, 'Add your most used tags for each particular service here, and then you can just double-click to add, rather than typing every time.' )
        st.setWordWrap( True )
        
        QP.AddToLayout( panel_vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Tag service: ', self._suggested_favourites_services ) )
        
        gridbox = ClientGUICommon.WrapInGrid( suggested_tags_favourites_panel, rows )
        
        QP.AddToLayout( panel_vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( panel_vbox, self._suggested_favourites, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( panel_vbox, self._suggested_favourites_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        suggested_tags_favourites_panel.setLayout( panel_vbox )
        
        #
        
        panel_vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'Show related tags: ', self._show_related_tags ) )
        rows.append( ( 'Initial/Quick search duration (ms): ', self._related_tags_search_1_duration_ms ) )
        rows.append( ( 'Medium search duration (ms): ', self._related_tags_search_2_duration_ms ) )
        rows.append( ( 'Thorough search duration (ms): ', self._related_tags_search_3_duration_ms ) )
        rows.append( ( 'Tag concurrence threshold %: ', self._related_tags_concurrence_threshold_percent ) )
        
        gridbox = ClientGUICommon.WrapInGrid( suggested_tags_related_panel, rows )
        
        search_tag_slices_weight_box.Add( search_tag_slices_weight_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        result_tag_slices_weight_box.Add( result_tag_slices_weight_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        desc = 'This will search the database for tags statistically related to what your files already have. It only searches within the specific service atm. The score weights are advanced, so only change them if you know what is going on!'
        st = ClientGUICommon.BetterStaticText( suggested_tags_related_panel, desc )
        st.setWordWrap( True )
        
        QP.AddToLayout( panel_vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( panel_vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( panel_vbox, search_tag_slices_weight_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( panel_vbox, result_tag_slices_weight_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        suggested_tags_related_panel.setLayout( panel_vbox )
        
        #
        
        panel_vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'Show file lookup scripts on single-file manage tags windows: ', self._show_file_lookup_script_tags ) )
        rows.append( ( 'Favourite file lookup script: ', self._favourite_file_lookup_script ) )
        
        gridbox = ClientGUICommon.WrapInGrid( suggested_tags_file_lookup_script_panel, rows )
        
        desc = 'This is an increasingly defunct system, do not expect miracles!'
        st = ClientGUICommon.BetterStaticText( suggested_tags_related_panel, desc )
        st.setWordWrap( True )
        
        QP.AddToLayout( panel_vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( panel_vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        panel_vbox.addStretch( 0 )
        
        suggested_tags_file_lookup_script_panel.setLayout( panel_vbox )
        
        #
        
        panel_vbox = QP.VBoxLayout()
        
        desc = 'This simply saves the last n tags you have added for each service.'
        st = ClientGUICommon.BetterStaticText( suggested_tags_related_panel, desc )
        st.setWordWrap( True )
        
        QP.AddToLayout( panel_vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( panel_vbox, self._num_recent_tags, CC.FLAGS_EXPAND_PERPENDICULAR )
        panel_vbox.addStretch( 0 )
        
        suggested_tags_recent_panel.setLayout( panel_vbox )
        
        #
        
        suggest_tags_panel_notebook.addTab( suggested_tags_favourites_panel, 'most used' )
        suggest_tags_panel_notebook.addTab( suggested_tags_related_panel, 'related' )
        suggest_tags_panel_notebook.addTab( suggested_tags_file_lookup_script_panel, 'file lookup scripts' )
        suggest_tags_panel_notebook.addTab( suggested_tags_recent_panel, 'recent' )
        
        #
        
        rows = []
        
        rows.append( ( 'Width of suggested tags columns: ', self._suggested_tags_width ) )
        rows.append( ( 'Column layout: ', self._suggested_tags_layout ) )
        rows.append( ( 'Default notebook page: ', self._default_suggested_tags_notebook_page ) )
        
        gridbox = ClientGUICommon.WrapInGrid( suggested_tags_panel, rows )
        
        desc = 'The manage tags dialog can provide several kinds of tag suggestions.'
        
        suggested_tags_panel.Add( ClientGUICommon.BetterStaticText( suggested_tags_panel, desc ), CC.FLAGS_EXPAND_PERPENDICULAR )
        suggested_tags_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        suggested_tags_panel.Add( suggest_tags_panel_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, suggested_tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        #
        
        self._suggested_favourites_services.currentIndexChanged.connect( self.EventSuggestedFavouritesService )
        self._suggested_tags_layout.currentIndexChanged.connect( self._NotifyLayoutChanged )
        
        self._NotifyLayoutChanged()
        self.EventSuggestedFavouritesService( None )
        
    
    def _AddResultTagSliceWeight( self ):
        
        self._AddTagSliceWeight( self._result_tag_slices_weights )
        
    
    def _AddSearchTagSliceWeight( self ):
        
        self._AddTagSliceWeight( self._search_tag_slices_weights )
        
    
    def _AddTagSliceWeight( self, list_ctrl ):
        
        message = 'enter namespace'
        
        try:
            
            tag_slice = ClientGUIDialogsQuick.EnterText( self, message )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if tag_slice in ( '', ':' ):
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, you cannot re-add unnamespaced or namespaced!' )
            
            return
            
        
        if not tag_slice.endswith( ':' ):
            
            tag_slice = tag_slice + ':'
            
        
        existing_tag_slices = { existing_tag_slice for ( existing_tag_slice, existing_weight ) in list_ctrl.GetData() }
        
        if tag_slice in existing_tag_slices:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, that namespace already exists!' )
            
            return
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'set weight' ) as dlg_2:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg_2 )
            
            control = ClientGUICommon.BetterSpinBox( panel, initial = 100, min = 0, max = 10000 )
            
            panel.SetControl( control, perpendicular = True )
            
            dlg_2.SetPanel( panel )
            
            if dlg_2.exec() == QW.QDialog.DialogCode.Accepted:
                
                weight = control.value()
                
                new_data = ( tag_slice, weight )
                
                list_ctrl.AddData( new_data, select_sort_and_scroll = True )
                
            
        
    
    def _CanDeleteResultTagSliceWeight( self ) -> bool:
        
        return self._CanDeleteTagSliceWeight( self._result_tag_slices_weights )
        
    
    def _CanDeleteSearchTagSliceWeight( self ) -> bool:
        
        return self._CanDeleteTagSliceWeight( self._search_tag_slices_weights )
        
    
    def _CanDeleteTagSliceWeight( self, list_ctrl ) -> bool:
        
        selected_tag_slices_and_weights = list_ctrl.GetData( only_selected = True )
        
        for ( tag_slice, weight ) in selected_tag_slices_and_weights:
            
            if tag_slice in ( '', ':' ):
                
                return False
                
            
        
        return True
        
    
    def _ConvertTagSliceAndWeightToDisplayTuple( self, tag_slice_and_weight ):
        
        ( tag_slice, weight ) = tag_slice_and_weight
        
        pretty_tag_slice = HydrusTags.ConvertTagSliceToPrettyString( tag_slice )
        
        pretty_weight = HydrusNumbers.ToHumanInt( weight ) + '%'
        
        display_tuple = ( pretty_tag_slice, pretty_weight )
        
        return display_tuple
        
    
    def _ConvertTagSliceAndWeightToSortTuple( self, tag_slice_and_weight ):
        
        ( tag_slice, weight ) = tag_slice_and_weight
        
        pretty_tag_slice = HydrusTags.ConvertTagSliceToPrettyString( tag_slice )
        sort_tag_slice = pretty_tag_slice
        
        sort_tuple = ( sort_tag_slice, weight )
        
        return sort_tuple
        
    
    def _EditResultTagSliceWeight( self ):
        
        self._EditTagSliceWeight( self._result_tag_slices_weights )
        
    
    def _EditSearchTagSliceWeight( self ):
        
        self._EditTagSliceWeight( self._search_tag_slices_weights )
        
    
    def _EditTagSliceWeight( self, list_ctrl ):
        
        original_data = list_ctrl.GetTopSelectedData()
        
        if original_data is None:
            
            return
            
        
        ( tag_slice, weight ) = original_data
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit weight' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = ClientGUICommon.BetterSpinBox( panel, initial = weight, min = 0, max = 10000 )
            
            panel.SetControl( control, perpendicular = True )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_weight = control.value()
                
                edited_data = ( tag_slice, edited_weight )
                
                list_ctrl.ReplaceData( original_data, edited_data, sort_and_scroll = True )
                
            
        
    
    def _NotifyLayoutChanged( self ):
        
        enable_default_page = self._suggested_tags_layout.GetValue() == 'notebook'
        
        self._default_suggested_tags_notebook_page.setEnabled( enable_default_page )
        
    
    def _SaveCurrentSuggestedFavourites( self ):
        
        if self._current_suggested_favourites_service is not None:
            
            self._suggested_favourites_dict[ self._current_suggested_favourites_service ] = self._suggested_favourites.GetTags()
            
        
    
    def EventSuggestedFavouritesService( self, index ):
        
        self._SaveCurrentSuggestedFavourites()
        
        self._current_suggested_favourites_service = self._suggested_favourites_services.GetValue()
        
        if self._current_suggested_favourites_service in self._suggested_favourites_dict:
            
            favourites = self._suggested_favourites_dict[ self._current_suggested_favourites_service ]
            
        else:
            
            favourites = self._new_options.GetSuggestedTagsFavourites( self._current_suggested_favourites_service )
            
        
        self._suggested_favourites.SetTagServiceKey( self._current_suggested_favourites_service )
        
        self._suggested_favourites.SetTags( favourites )
        
        self._suggested_favourites_input.SetTagServiceKey( self._current_suggested_favourites_service )
        self._suggested_favourites_input.SetDisplayTagServiceKey( self._current_suggested_favourites_service )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetInteger( 'suggested_tags_width', self._suggested_tags_width.value() )
        self._new_options.SetNoneableString( 'suggested_tags_layout', self._suggested_tags_layout.GetValue() )
        
        self._new_options.SetString( 'default_suggested_tags_notebook_page', self._default_suggested_tags_notebook_page.GetValue() )
        
        self._SaveCurrentSuggestedFavourites()
        
        for ( service_key, favourites ) in list(self._suggested_favourites_dict.items()):
            
            self._new_options.SetSuggestedTagsFavourites( service_key, favourites )
            
        
        self._new_options.SetBoolean( 'show_related_tags', self._show_related_tags.isChecked() )
        
        self._new_options.SetInteger( 'related_tags_search_1_duration_ms', self._related_tags_search_1_duration_ms.value() )
        self._new_options.SetInteger( 'related_tags_search_2_duration_ms', self._related_tags_search_2_duration_ms.value() )
        self._new_options.SetInteger( 'related_tags_search_3_duration_ms', self._related_tags_search_3_duration_ms.value() )
        
        self._new_options.SetInteger( 'related_tags_concurrence_threshold_percent', self._related_tags_concurrence_threshold_percent.value() )
        
        related_tags_search_tag_slices_weight_percent = self._search_tag_slices_weights.GetData()
        related_tags_result_tag_slices_weight_percent = self._result_tag_slices_weights.GetData()
        
        self._new_options.SetRelatedTagsTagSliceWeights( related_tags_search_tag_slices_weight_percent, related_tags_result_tag_slices_weight_percent )
        
        self._new_options.SetBoolean( 'show_file_lookup_script_tags', self._show_file_lookup_script_tags.isChecked() )
        self._new_options.SetNoneableString( 'favourite_file_lookup_script', self._favourite_file_lookup_script.GetValue() )
        
        self._new_options.SetNoneableInteger( 'num_recent_tags', self._num_recent_tags.GetValue() )
        
    
