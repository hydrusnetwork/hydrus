from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.metadata import ClientGUITagsEditNamespaceSort
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelSortCollect
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags

class FileSortCollectPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        self._file_sort_panel = ClientGUICommon.StaticBox( self, 'file sort' )
        
        default_sort = self._new_options.GetDefaultSort()
        
        self._default_media_sort = ClientGUIMediaResultsPanelSortCollect.MediaSortControl( self._file_sort_panel, media_sort = default_sort )
        
        if self._default_media_sort.GetSort() != default_sort:
            
            media_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
            
            self._default_media_sort.SetSort( media_sort )
            
        
        fallback_sort = self._new_options.GetFallbackSort()
        
        self._fallback_media_sort = ClientGUIMediaResultsPanelSortCollect.MediaSortControl( self._file_sort_panel, media_sort = fallback_sort )
        
        if self._fallback_media_sort.GetSort() != fallback_sort:
            
            media_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_IMPORT_TIME ), CC.SORT_ASC )
            
            self._fallback_media_sort.SetSort( media_sort )
            
        
        self._save_page_sort_on_change = QW.QCheckBox( self._file_sort_panel )
        
        self._default_media_collect = ClientGUIMediaResultsPanelSortCollect.MediaCollectControl( self._file_sort_panel )
        
        #
        
        namespace_file_sorting_box = ClientGUICommon.StaticBox( self._file_sort_panel, 'namespace file sorting' )
        
        self._namespace_file_sort_by = ClientGUIListBoxes.QueueListBox( namespace_file_sorting_box, 8, self._ConvertNamespaceTupleToSortString, add_callable = self._AddNamespaceSort, edit_callable = self._EditNamespaceSort )
        
        #
        
        self._namespace_file_sort_by.AddDatas( [ media_sort.sort_type[1] for media_sort in CG.client_controller.new_options.GetDefaultNamespaceSorts() ] )
        
        self._save_page_sort_on_change.setChecked( self._new_options.GetBoolean( 'save_page_sort_on_change' ) )
        
        #
        
        sort_by_text = 'You can manage your namespace sorting schemes here.'
        sort_by_text += '\n'
        sort_by_text += 'The client will sort media by comparing their namespaces, moving from left to right until an inequality is found.'
        sort_by_text += '\n'
        sort_by_text += 'Any namespaces here will also appear in your collect-by dropdowns.'
        
        namespace_file_sorting_box.Add( ClientGUICommon.BetterStaticText( namespace_file_sorting_box, sort_by_text ), CC.FLAGS_EXPAND_PERPENDICULAR )
        namespace_file_sorting_box.Add( self._namespace_file_sort_by, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        seriation_box = ClientGUICommon.StaticBox( self._file_sort_panel, 'seriation' )
        
        seriation_text = 'Controls for the seriation sort types (visual, tags, or blended).'
        
        self._seriation_visual_weight = ClientGUICommon.BetterDoubleSpinBox( seriation_box, min = 0.0, max = 1.0 )
        self._seriation_visual_weight.setSingleStep( 0.05 )
        
        self._seriation_tag_weight = ClientGUICommon.BetterDoubleSpinBox( seriation_box, min = 0.0, max = 1.0 )
        self._seriation_tag_weight.setSingleStep( 0.05 )
        
        self._seriation_visual_bin_size = ClientGUICommon.BetterSpinBox( seriation_box, min = 1, max = 255 )
        self._seriation_max_visual_candidates = ClientGUICommon.BetterSpinBox( seriation_box, min = 10, max = 10000 )
        self._seriation_max_tag_candidates = ClientGUICommon.BetterSpinBox( seriation_box, min = 10, max = 10000 )
        self._seriation_max_tag_keys = ClientGUICommon.BetterSpinBox( seriation_box, min = 1, max = 50 )
        self._seriation_max_hybrid_candidates = ClientGUICommon.BetterSpinBox( seriation_box, min = 10, max = 10000 )
        
        self._seriation_visual_weight.setToolTip( ClientGUIFunctions.WrapToolTip( 'Weight for visual similarity (blurhash). If both weights are zero, defaults apply.' ) )
        self._seriation_tag_weight.setToolTip( ClientGUIFunctions.WrapToolTip( 'Weight for tag similarity (Jaccard distance). If both weights are zero, defaults apply.' ) )
        self._seriation_visual_bin_size.setToolTip( ClientGUIFunctions.WrapToolTip( 'Colour bin size used to shortlist candidates for visual seriation. Smaller is more precise but slower.' ) )
        self._seriation_max_visual_candidates.setToolTip( ClientGUIFunctions.WrapToolTip( 'Max candidates considered per item for visual seriation.' ) )
        self._seriation_max_tag_candidates.setToolTip( ClientGUIFunctions.WrapToolTip( 'Max candidates considered per item for tag seriation.' ) )
        self._seriation_max_tag_keys.setToolTip( ClientGUIFunctions.WrapToolTip( 'How many rarest tags to use when building tag candidates.' ) )
        self._seriation_max_hybrid_candidates.setToolTip( ClientGUIFunctions.WrapToolTip( 'Max candidates considered per item for visual+tag seriation.' ) )
        
        self._seriation_visual_weight.setValue( self._new_options.GetFloat( 'seriation_visual_weight' ) )
        self._seriation_tag_weight.setValue( self._new_options.GetFloat( 'seriation_tag_weight' ) )
        self._seriation_visual_bin_size.setValue( self._new_options.GetInteger( 'seriation_visual_bin_size' ) )
        self._seriation_max_visual_candidates.setValue( self._new_options.GetInteger( 'seriation_max_visual_candidates' ) )
        self._seriation_max_tag_candidates.setValue( self._new_options.GetInteger( 'seriation_max_tag_candidates' ) )
        self._seriation_max_tag_keys.setValue( self._new_options.GetInteger( 'seriation_max_tag_keys' ) )
        self._seriation_max_hybrid_candidates.setValue( self._new_options.GetInteger( 'seriation_max_hybrid_candidates' ) )
        
        seriation_rows = []
        
        seriation_rows.append( ( 'Visual weight (0-1): ', self._seriation_visual_weight ) )
        seriation_rows.append( ( 'Tag weight (0-1): ', self._seriation_tag_weight ) )
        seriation_rows.append( ( 'Visual bin size: ', self._seriation_visual_bin_size ) )
        seriation_rows.append( ( 'Max visual candidates: ', self._seriation_max_visual_candidates ) )
        seriation_rows.append( ( 'Max tag candidates: ', self._seriation_max_tag_candidates ) )
        seriation_rows.append( ( 'Max tag keys: ', self._seriation_max_tag_keys ) )
        seriation_rows.append( ( 'Max hybrid candidates: ', self._seriation_max_hybrid_candidates ) )
        
        seriation_box.Add( ClientGUICommon.BetterStaticText( seriation_box, seriation_text ), CC.FLAGS_EXPAND_PERPENDICULAR )
        seriation_box.Add( ClientGUICommon.WrapInGrid( seriation_box, seriation_rows ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Default file sort: ', self._default_media_sort ) )
        rows.append( ( 'Secondary file sort (when primary gives two equal values): ', self._fallback_media_sort ) )
        rows.append( ( 'Update default file sort every time a new sort is manually chosen: ', self._save_page_sort_on_change ) )
        rows.append( ( 'Default collect: ', self._default_media_collect ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self._file_sort_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._file_sort_panel.Add( namespace_file_sorting_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._file_sort_panel.Add( seriation_box, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._file_sort_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _AddNamespaceSort( self ):
        
        default = ( ( 'creator', 'series', 'page' ), ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
        
        return self._EditNamespaceSort( default )
        
    
    def _ConvertNamespaceTupleToSortString( self, sort_data ):
        
        ( namespaces, tag_display_type ) = sort_data
        
        return '-'.join( namespaces )
        
    
    def _EditNamespaceSort( self, sort_data ):
        
        return ClientGUITagsEditNamespaceSort.EditNamespaceSort( self, sort_data )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetDefaultSort( self._default_media_sort.GetSort() )
        self._new_options.SetFallbackSort( self._fallback_media_sort.GetSort() )
        self._new_options.SetBoolean( 'save_page_sort_on_change', self._save_page_sort_on_change.isChecked() )
        self._new_options.SetDefaultCollect( self._default_media_collect.GetValue() )
        self._new_options.SetFloat( 'seriation_visual_weight', self._seriation_visual_weight.value() )
        self._new_options.SetFloat( 'seriation_tag_weight', self._seriation_tag_weight.value() )
        self._new_options.SetInteger( 'seriation_visual_bin_size', self._seriation_visual_bin_size.value() )
        self._new_options.SetInteger( 'seriation_max_visual_candidates', self._seriation_max_visual_candidates.value() )
        self._new_options.SetInteger( 'seriation_max_tag_candidates', self._seriation_max_tag_candidates.value() )
        self._new_options.SetInteger( 'seriation_max_tag_keys', self._seriation_max_tag_keys.value() )
        self._new_options.SetInteger( 'seriation_max_hybrid_candidates', self._seriation_max_hybrid_candidates.value() )
        
        namespace_sorts = [ ClientMedia.MediaSort( sort_type = ( 'namespaces', sort_data ) ) for sort_data in self._namespace_file_sort_by.GetData() ]
        
        self._new_options.SetDefaultNamespaceSorts( namespace_sorts )
        
    
