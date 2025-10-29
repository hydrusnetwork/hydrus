from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
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
        
        rows = []
        
        rows.append( ( 'Default file sort: ', self._default_media_sort ) )
        rows.append( ( 'Secondary file sort (when primary gives two equal values): ', self._fallback_media_sort ) )
        rows.append( ( 'Update default file sort every time a new sort is manually chosen: ', self._save_page_sort_on_change ) )
        rows.append( ( 'Default collect: ', self._default_media_collect ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self._file_sort_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._file_sort_panel.Add( namespace_file_sorting_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
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
        
        namespace_sorts = [ ClientMedia.MediaSort( sort_type = ( 'namespaces', sort_data ) ) for sort_data in self._namespace_file_sort_by.GetData() ]
        
        self._new_options.SetDefaultNamespaceSorts( namespace_sorts )
        
    
