import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUITags
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags

class MediaCollectControl( QW.QWidget ):
    
    def __init__( self, parent, management_controller = None, silent = False ):
        
        QW.QWidget.__init__( self, parent )
        
        # this is trash, rewrite it to deal with the media_collect object, not the management controller
        
        self._management_controller = management_controller
        
        if self._management_controller is not None and self._management_controller.HasVariable( 'media_collect' ):
            
            self._media_collect = self._management_controller.GetVariable( 'media_collect' )
            
        else:
            
            self._media_collect = HG.client_controller.new_options.GetDefaultCollect()
            
        
        self._silent = silent
        
        self._collect_comboctrl = QP.CollectComboCtrl( self, self._media_collect )
        
        choice_tuples = [
            ( 'collect unmatched', True ),
            ( 'leave unmatched', False )
        ]
        
        self._collect_unmatched = ClientGUIMenuButton.MenuChoiceButton( self, choice_tuples )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._collect_unmatched, 19 )
        
        self._collect_unmatched.setMinimumWidth( width )
        
        #
        
        self._collect_unmatched.SetValue( self._media_collect.collect_unmatched )
        
        #
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._collect_comboctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._collect_unmatched, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        #
        
        self._UpdateLabel()
        
        self._collect_unmatched.valueChanged.connect( self.CollectValuesChanged )
        self._collect_comboctrl.itemChanged.connect( self.CollectValuesChanged )
        
        self._collect_comboctrl.installEventFilter( self )
        
        HG.client_controller.sub( self, 'SetCollectFromPage', 'set_page_collect' )
        
    
    def _BroadcastCollect( self ):
        
        if not self._silent and self._management_controller is not None:
            
            self._management_controller.SetVariable( 'media_collect', self._media_collect )
            
            page_key = self._management_controller.GetKey( 'page' )
            
            HG.client_controller.pub( 'collect_media', page_key, self._media_collect )
            HG.client_controller.pub( 'a_collect_happened', page_key )
            
        
    
    def _UpdateLabel( self ):
        
        ( namespaces, rating_service_keys, description ) = self._collect_comboctrl.GetValues()
        
        self._collect_comboctrl.SetValue( description )
        
    
    def GetValue( self ):
        
        return self._media_collect
        
    
    def CollectValuesChanged( self ):
        
        ( namespaces, rating_service_keys, description ) = self._collect_comboctrl.GetValues()
        
        self._UpdateLabel()
        
        collect_unmatched = self._collect_unmatched.GetValue()
        
        self._media_collect = ClientMedia.MediaCollect( namespaces = namespaces, rating_service_keys = rating_service_keys, collect_unmatched = collect_unmatched )
        
        self._BroadcastCollect()
        
    
    def eventFilter( self, watched, event ):
        
        if watched == self._collect_comboctrl:
            
            if event.type() == QC.QEvent.MouseButtonPress and event.button() == QC.Qt.MiddleButton:
                
                self.SetCollect( ClientMedia.MediaCollect( collect_unmatched = self._media_collect.collect_unmatched ) )
                
                return True
                
            
        
        return False
        
    
    def SetCollect( self, media_collect ):
        
        self._media_collect = media_collect
        
        self._collect_comboctrl.blockSignals( True )
        self._collect_unmatched.blockSignals( True )
        
        self._collect_comboctrl.SetCollectByValue( self._media_collect )
        self._collect_unmatched.SetValue( self._media_collect.collect_unmatched )
        
        self._UpdateLabel()
        
        self._collect_comboctrl.blockSignals( False )
        self._collect_unmatched.blockSignals( False )
        
        self._BroadcastCollect()
        
    
    def SetCollectFromPage( self, page_key, media_collect ):
        
        if page_key == self._management_controller.GetKey( 'page' ):
            
            self.SetCollect( media_collect )
            
            self._BroadcastCollect()
            
        
    
class MediaSortControl( QW.QWidget ):
    
    sortChanged = QC.Signal( ClientMedia.MediaSort )
    
    def __init__( self, parent, management_controller = None ):
        
        QW.QWidget.__init__( self, parent )
        
        self._management_controller = management_controller
        
        self._sort_type = ( 'system', CC.SORT_FILES_BY_FILESIZE )
        
        self._sort_type_button = ClientGUICommon.BetterButton( self, 'sort', self._SortTypeButtonClick )
        self._sort_tag_display_type_button = ClientGUIMenuButton.MenuChoiceButton( self, [] )
        self._sort_order_choice = ClientGUIMenuButton.MenuChoiceButton( self, [] )
        
        type_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._sort_type_button, 14 )
        
        self._sort_type_button.setMinimumWidth( type_width )
        
        tdt_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._sort_tag_display_type_button, 8 )
        
        self._sort_tag_display_type_button.setMinimumWidth( tdt_width )
        
        asc_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._sort_order_choice, 14 )
        
        self._sort_order_choice.setMinimumWidth( asc_width )
        
        self._UpdateSortTypeLabel()
        self._UpdateAscLabels()
        
        #
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._sort_type_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._sort_tag_display_type_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sort_order_choice, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        HG.client_controller.sub( self, 'ACollectHappened', 'a_collect_happened' )
        HG.client_controller.sub( self, 'BroadcastSort', 'do_page_sort' )
        
        if self._management_controller is not None and self._management_controller.HasVariable( 'media_sort' ):
            
            media_sort = self._management_controller.GetVariable( 'media_sort' )
            
            try:
                
                self.SetSort( media_sort )
                
            except:
                
                default_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
                
                self.SetSort( default_sort )
                
            
        
        self._sort_tag_display_type_button.valueChanged.connect( self.EventTagDisplayTypeChoice )
        self._sort_order_choice.valueChanged.connect( self.EventSortAscChoice )
        
    
    def _BroadcastSort( self ):
        
        media_sort = self._GetCurrentSort()
        
        if self._management_controller is not None:
            
            self._management_controller.SetVariable( 'media_sort', media_sort )
            
        
        self.sortChanged.emit( media_sort )
        
    
    def _GetCurrentSort( self ) -> ClientMedia.MediaSort:
        
        sort_order = self._sort_order_choice.GetValue()
        
        if sort_order is None:
            
            sort_order = CC.SORT_ASC
            
        
        media_sort = ClientMedia.MediaSort( self._sort_type, sort_order )
        
        return media_sort
        
    
    def _PopulateSortMenuOrList( self, menu = None ):
        
        sort_types = []
        
        menu_items_and_sort_types = []
        
        submetatypes_to_menus = {}
        
        for system_sort_type in CC.SYSTEM_SORT_TYPES_SORT_CONTROL_SORTED:
            
            sort_type = ( 'system', system_sort_type )
            
            sort_types.append( sort_type )
            
            if menu is not None:
                
                submetatype = CC.system_sort_type_submetatype_string_lookup[ system_sort_type ]
                
                if submetatype is None:
                    
                    menu_to_add_to = menu
                    
                else:
                    
                    if submetatype not in submetatypes_to_menus:
                        
                        submenu = QW.QMenu( menu )
                        
                        submetatypes_to_menus[ submetatype ] = submenu
                        
                        ClientGUIMenus.AppendMenu( menu, submenu, submetatype )
                        
                    
                    menu_to_add_to = submetatypes_to_menus[ submetatype ]
                    
                
                label = CC.sort_type_basic_string_lookup[ system_sort_type ]
                
                menu_item = ClientGUIMenus.AppendMenuItem( menu_to_add_to, label, 'Select this sort type.', self._SetSortType, sort_type )
                
                menu_items_and_sort_types.append( ( menu_item, sort_type ) )
                
            
        
        default_namespace_sorts = HG.client_controller.new_options.GetDefaultNamespaceSorts()
        
        if menu is not None:
            
            submenu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'namespaces' )
            
        
        for namespace_sort in default_namespace_sorts:
            
            sort_type = namespace_sort.sort_type
            
            sort_types.append( sort_type )
            
            if menu is not None:
                
                example_sort = ClientMedia.MediaSort( sort_type, CC.SORT_ASC )
                
                label = example_sort.GetSortTypeString()
                
                menu_item = ClientGUIMenus.AppendMenuItem( submenu, label, 'Select this sort type.', self._SetSortType, sort_type )
                
                menu_items_and_sort_types.append( ( menu_item, sort_type ) )
                
            
        
        if menu is not None:
            
            ClientGUIMenus.AppendMenuItem( submenu, 'custom', 'Set a custom namespace sort', self._SetCustomNamespaceSort )
            
        
        rating_service_keys = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
        
        if len( rating_service_keys ) > 0:
            
            if menu is not None:
                
                submenu = QW.QMenu( menu )
                
                ClientGUIMenus.AppendMenu( menu, submenu, 'ratings' )
                
            
            for service_key in rating_service_keys:
                
                sort_type = ( 'rating', service_key )
                
                sort_types.append( sort_type )
                
                if menu is not None:
                    
                    example_sort = ClientMedia.MediaSort( sort_type, CC.SORT_ASC )
                    
                    label = example_sort.GetSortTypeString()
                    
                    menu_item = ClientGUIMenus.AppendMenuItem( submenu, label, 'Select this sort type.', self._SetSortType, sort_type )
                    
                    menu_items_and_sort_types.append( ( menu_item, sort_type ) )
                    
                
            
        
        if menu is not None:
            
            for ( menu_item, sort_choice ) in menu_items_and_sort_types:
                
                if sort_choice == self._sort_type:
                    
                    menu_item.setCheckable( True )
                    menu_item.setChecked( True )
                    
                
            
        
        return sort_types
        
    
    def _SetCustomNamespaceSort( self ):
        
        if self._sort_type[0] == 'namespaces':
            
            sort_data = self._sort_type[1]
            
        else:
            
            sort_data = ( [ 'series' ], ClientTags.TAG_DISPLAY_ACTUAL )
            
        
        try:
            
            sort_data = ClientGUITags.EditNamespaceSort( self, sort_data )
            
            sort_type = ( 'namespaces', sort_data )
            
            self._SetSortType( sort_type )
            
        except HydrusExceptions.VetoException:
            
            return
            
        
    
    def EventTagDisplayTypeChoice( self ):
        
        tag_display_type = self._sort_tag_display_type_button.GetValue()
        
        ( sort_metatype, sort_data ) = self._sort_type
        
        if sort_metatype == 'namespaces':
            
            ( namespaces, current_tag_display_type ) = sort_data
            
            sort_data = ( namespaces, tag_display_type )
            
            self._sort_type = ( sort_metatype, sort_data )
            
            self._UserChoseASort()
            
            self._BroadcastSort()
            
        
    
    def _SortTypeButtonClick( self ):
        
        menu = QW.QMenu()
        
        self._PopulateSortMenuOrList( menu = menu )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _SetSortType( self, sort_type ):
        
        self._sort_type = sort_type
        
        self._UpdateSortTypeLabel()
        self._UpdateAscLabels( set_default_asc = True )
        
        self._UserChoseASort()
        
        self._BroadcastSort()
        
    
    def _UpdateAscLabels( self, set_default_asc = False ):
        
        media_sort = self._GetCurrentSort()
        
        self._sort_order_choice.blockSignals( True )
        
        if media_sort.CanAsc():
            
            ( asc_str, desc_str, default_sort_order ) = media_sort.GetSortOrderStrings()
            
            choice_tuples = [
                ( asc_str, CC.SORT_ASC ),
                ( desc_str, CC.SORT_DESC )
            ]
            
            self._sort_order_choice.SetChoiceTuples( choice_tuples )
            
            if set_default_asc:
                
                sort_order_to_set = default_sort_order
                
            else:
                
                sort_order_to_set = media_sort.sort_order
                
            
            self._sort_order_choice.SetValue( sort_order_to_set )
            
        else:
            
            self._sort_order_choice.SetChoiceTuples( [] )
            
        
        self._sort_order_choice.blockSignals( False )
        
    
    def _UpdateSortTypeLabel( self ):
        
        example_sort = ClientMedia.MediaSort( self._sort_type, CC.SORT_ASC )
        
        self._sort_type_button.setText( example_sort.GetSortTypeString() )
        
        ( sort_metatype, sort_data ) = self._sort_type
        
        show_tdt = sort_metatype == 'namespaces' and HG.client_controller.new_options.GetBoolean( 'advanced_mode' )
        
        if show_tdt:
            
            if sort_metatype == 'namespaces':
                
                ( namespaces, current_tag_display_type ) = sort_data
                
                tag_display_types = [
                    ClientTags.TAG_DISPLAY_ACTUAL,
                    ClientTags.TAG_DISPLAY_SELECTION_LIST,
                    ClientTags.TAG_DISPLAY_SINGLE_MEDIA
                ]
                
                choice_tuples = [ ( ClientTags.tag_display_str_lookup[ tag_display_type ], tag_display_type ) for tag_display_type in tag_display_types ]
                
                self._sort_tag_display_type_button.blockSignals( True )
                
                self._sort_tag_display_type_button.SetChoiceTuples( choice_tuples )
                
                self._sort_tag_display_type_button.SetValue( current_tag_display_type )
                
                self._sort_tag_display_type_button.blockSignals( False )
                
            
        
        self._sort_tag_display_type_button.setVisible( show_tdt )
        
    
    def _UserChoseASort( self ):
        
        if HG.client_controller.new_options.GetBoolean( 'save_page_sort_on_change' ):
            
            media_sort = self._GetCurrentSort()
            
            HG.client_controller.new_options.SetDefaultSort( media_sort )
            
        
    
    def ACollectHappened( self, page_key ):
        
        if self._management_controller is not None:
            
            my_page_key = self._management_controller.GetKey( 'page' )
            
            if page_key == my_page_key:
                
                self._BroadcastSort()
                
            
        
    
    def BroadcastSort( self, page_key = None ):
        
        if page_key is not None and page_key != self._management_controller.GetKey( 'page' ):
            
            return
            
        
        self._BroadcastSort()
        
    
    def EventSortAscChoice( self ):
        
        self._UserChoseASort()
        
        self._BroadcastSort()
        
    
    def GetSort( self ) -> ClientMedia.MediaSort:
        
        return self._GetCurrentSort()
        
    
    def wheelEvent( self, event ):
        
        if event.angleDelta().y() > 0:
            
            index_delta = -1
            
        else:
            
            index_delta = 1
            
        
        sort_types = self._PopulateSortMenuOrList()
        
        if self._sort_type in sort_types:
            
            index = sort_types.index( self._sort_type )
            
            new_index = ( index + index_delta ) % len( sort_types )
            
            new_sort_type = sort_types[ new_index ]
            
            self._SetSortType( new_sort_type )
            
        
        event.accept()
        
    
    def SetSort( self, media_sort: ClientMedia.MediaSort ):
        
        self._sort_type = media_sort.sort_type
        
        self._UpdateSortTypeLabel()
        self._UpdateAscLabels()
        
        # put this after 'asclabels', since we may transition from one-state to two-state
        self._sort_order_choice.SetValue( media_sort.sort_order )
        
    
