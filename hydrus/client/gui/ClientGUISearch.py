import os
import re
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientSearch
from hydrus.client.gui import ClientGUICommon
from hydrus.client.gui import ClientGUIControls
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIOptionsPanels
from hydrus.client.gui import ClientGUIRatings
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITime
from hydrus.client.gui import QtPorting as QP
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientRatings

FLESH_OUT_SYSTEM_PRED_TYPES = {
    ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS,
    ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT,
    ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE,
    ClientSearch.PREDICATE_TYPE_SYSTEM_DIMENSIONS,
    ClientSearch.PREDICATE_TYPE_SYSTEM_AGE,
    ClientSearch.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME,
    ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS,
    ClientSearch.PREDICATE_TYPE_SYSTEM_HASH,
    ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION,
    ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO,
    ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS,
    ClientSearch.PREDICATE_TYPE_SYSTEM_MIME,
    ClientSearch.PREDICATE_TYPE_SYSTEM_RATING,
    ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO,
    ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE,
    ClientSearch.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER,
    ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS,
    ClientSearch.PREDICATE_TYPE_SYSTEM_NOTES,
    ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS
}

def FleshOutPredicates( widget: QW.QWidget, predicates: typing.Iterable[ ClientSearch.Predicate ] ) -> typing.List[ ClientSearch.Predicate ]:
    
    window = widget.window()
    
    good_predicates = []
    
    for predicate in predicates:
        
        predicate = predicate.GetCountlessCopy()
        
        ( predicate_type, value, inclusive ) = predicate.GetInfo()
        
        if value is None and predicate_type in FLESH_OUT_SYSTEM_PRED_TYPES:
            
            from hydrus.client.gui import ClientGUITopLevelWindowsPanels
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( window, 'input predicate', hide_buttons = True ) as dlg:
                
                panel = InputFileSystemPredicate( dlg, predicate_type )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    good_predicates.extend( panel.GetValue() )
                    
                
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_UNTAGGED:
            
            good_predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '=', 0 ) ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_LABEL:
            
            continue
            
        else:
            
            good_predicates.append( predicate )
            
        
    
    return good_predicates
    
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
        
        self._collect_unmatched = ClientGUICommon.BetterChoice( self )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._collect_unmatched, 19 )
        
        self._collect_unmatched.setMinimumWidth( width )
        
        self._collect_unmatched.addItem( 'collect unmatched', True )
        self._collect_unmatched.addItem( 'leave unmatched', False )
        
        #
        
        self._collect_unmatched.SetValue( self._media_collect.collect_unmatched )
        
        #
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._collect_comboctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._collect_unmatched, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        #
        
        self._UpdateLabel()
        
        self._collect_unmatched.currentIndexChanged.connect( self.CollectValuesChanged )
        self._collect_comboctrl.itemChanged.connect( self.CollectValuesChanged )
        
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
        self._sort_order_choice = ClientGUICommon.BetterChoice( self )
        
        type_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._sort_type_button, 14 )
        
        self._sort_type_button.setMinimumWidth( type_width )
        
        asc_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._sort_order_choice, 14 )
        
        self._sort_order_choice.setMinimumWidth( asc_width )
        
        self._sort_order_choice.addItem( '', CC.SORT_ASC )
        
        self._UpdateSortTypeLabel()
        self._UpdateAscLabels()
        
        #
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._sort_type_button, CC.FLAGS_EXPAND_BOTH_WAYS )
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
                
            
        
        self._sort_order_choice.currentIndexChanged.connect( self.EventSortAscChoice )
        
    
    def _BroadcastSort( self ):
        
        media_sort = self._GetCurrentSort()
        
        if self._management_controller is not None:
            
            self._management_controller.SetVariable( 'media_sort', media_sort )
            
        
        self.sortChanged.emit( media_sort )
        
    
    def _GetCurrentSort( self ) -> ClientMedia.MediaSort:
        
        sort_order = self._sort_order_choice.GetValue()
        
        media_sort = ClientMedia.MediaSort( self._sort_type, sort_order )
        
        return media_sort
        
    
    def _PopulateSortMenuOrList( self, menu = None ):
        
        sort_types = []
        
        menu_items_and_sort_types = []
        
        submetatypes_to_menus = {}
        
        for system_sort_type in CC.SYSTEM_SORT_TYPES:
            
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
                
            
        
        namespace_sort_types = HC.options[ 'sort_by' ]
        
        if len( namespace_sort_types ) > 0:
            
            if menu is not None:
                
                submenu = QW.QMenu( menu )
                
                ClientGUIMenus.AppendMenu( menu, submenu, 'namespaces' )
                
            
            for ( namespaces_text, namespaces_list ) in namespace_sort_types:
                
                sort_type = ( namespaces_text, tuple( namespaces_list ) )
                
                sort_types.append( sort_type )
                
                if menu is not None:
                    
                    example_sort = ClientMedia.MediaSort( sort_type, CC.SORT_ASC )
                    
                    label = example_sort.GetSortTypeString()
                    
                    menu_item = ClientGUIMenus.AppendMenuItem( submenu, label, 'Select this sort type.', self._SetSortType, sort_type )
                    
                    menu_items_and_sort_types.append( ( menu_item, sort_type ) )
                    
                
            
        
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
        
        self._sort_order_choice.clear()
        
        if media_sort.CanAsc():
            
            ( asc_str, desc_str, default_sort_order ) = media_sort.GetSortOrderStrings()
            
            self._sort_order_choice.addItem( asc_str, CC.SORT_ASC )
            self._sort_order_choice.addItem( desc_str, CC.SORT_DESC )
            
            if set_default_asc:
                
                sort_order_to_set = default_sort_order
                
            else:
                
                sort_order_to_set = media_sort.sort_order
                
            
            self._sort_order_choice.SetValue( sort_order_to_set )
            
            self._sort_order_choice.setEnabled( True )
            
        else:
            
            self._sort_order_choice.addItem( '', CC.SORT_ASC )
            self._sort_order_choice.addItem( '', CC.SORT_DESC )
            
            self._sort_order_choice.SetValue( CC.SORT_ASC )
            
            self._sort_order_choice.setEnabled( False )
            
        
    
    def _UpdateSortTypeLabel( self ):
        
        example_sort = ClientMedia.MediaSort( self._sort_type, CC.SORT_ASC )
        
        self._sort_type_button.setText( example_sort.GetSortTypeString() )
        
    
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
        
    
    def EventSortAscChoice( self, index ):
        
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
        self._sort_order_choice.SetValue( media_sort.sort_order )
        
        self._UpdateSortTypeLabel()
        self._UpdateAscLabels()
        
    
class InputFileSystemPredicate( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, predicate_type ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._predicates = []
        
        label = None
        editable_pred_panel_classes = []
        static_pred_buttons = []
        
        if predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_AGE:
            
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 0, 0, 1, 0 ) ) ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 0, 0, 7, 0 ) ) ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 0, 1, 0, 0 ) ) ), ) ) )
            
            editable_pred_panel_classes.append( PanelPredicateSystemAgeDelta )
            editable_pred_panel_classes.append( PanelPredicateSystemAgeDate )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME:
            
            editable_pred_panel_classes.append( PanelPredicateSystemModifiedDelta )
            editable_pred_panel_classes.append( PanelPredicateSystemModifiedDate )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_DIMENSIONS:
            
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 16, 9 ) ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 9, 16 ) ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 4, 3 ) ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 1, 1 ) ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( '=', 1920 ) ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '=', 1080 ) ) ), forced_label = '1080p' ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( '=', 1280 ) ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '=', 720 ) ) ), forced_label = '720p' ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( '=', 3840 ) ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '=', 2160 ) ) ), forced_label = '4k' ) )
            
            editable_pred_panel_classes.append( PanelPredicateSystemHeight )
            editable_pred_panel_classes.append( PanelPredicateSystemWidth )
            editable_pred_panel_classes.append( PanelPredicateSystemRatio )
            editable_pred_panel_classes.append( PanelPredicateSystemNumPixels )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION:
            
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( '>', 0 ) ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( '=', 0 ) ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FRAMERATE, ( '=', 30 ) ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FRAMERATE, ( '=', 60 ) ), ) ) )
            
            editable_pred_panel_classes.append( PanelPredicateSystemDuration )
            editable_pred_panel_classes.append( PanelPredicateSystemFramerate )
            editable_pred_panel_classes.append( PanelPredicateSystemNumFrames )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE:
            
            editable_pred_panel_classes.append( PanelPredicateSystemFileService )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
            
            editable_pred_panel_classes.append( PanelPredicateSystemKnownURLsExactURL )
            editable_pred_panel_classes.append( PanelPredicateSystemKnownURLsDomain )
            editable_pred_panel_classes.append( PanelPredicateSystemKnownURLsRegex )
            editable_pred_panel_classes.append( PanelPredicateSystemKnownURLsURLClass )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO:
            
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, True ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, False ), ) ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_HASH:
            
            editable_pred_panel_classes.append( PanelPredicateSystemHash )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT:
            
            label = 'system:limit clips a large search result down to the given number of files. It is very useful for processing in smaller batches.'
            label += os.linesep * 2
            label += 'For all the simpler sorts (filesize, duration, etc...), it will select the n largest/smallest in the result set appropriate for that sort. For complicated sorts like tags, it will sample randomly.'
            
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, 64 ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, 256 ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, 1024 ), ) ) )
            
            editable_pred_panel_classes.append( PanelPredicateSystemLimit )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_MIME:
            
            editable_pred_panel_classes.append( PanelPredicateSystemMime )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS:
            
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '>', 0 ) ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '=', 0 ) ), ) ) )
            
            editable_pred_panel_classes.append( PanelPredicateSystemNumTags )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_NOTES:
            
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_NOTES, ( '>', 0 ) ), ) ) )
            static_pred_buttons.append( StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_NOTES, ( '=', 0 ) ), ) ) )
            
            editable_pred_panel_classes.append( PanelPredicateSystemNumNotes )
            editable_pred_panel_classes.append( PanelPredicateSystemHasNoteName )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS:
            
            editable_pred_panel_classes.append( PanelPredicateSystemNumWords )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_RATING:
            
            services_manager = HG.client_controller.services_manager
            
            ratings_services = services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
            
            if len( ratings_services ) > 0:
                
                editable_pred_panel_classes.append( PanelPredicateSystemRating )
                
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO:
            
            editable_pred_panel_classes.append( PanelPredicateSystemSimilarTo )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE:
            
            editable_pred_panel_classes.append( PanelPredicateSystemSize )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER:
            
            editable_pred_panel_classes.append( PanelPredicateSystemTagAsNumber )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS:
            
            editable_pred_panel_classes.append( PanelPredicateSystemDuplicateRelationships )
            editable_pred_panel_classes.append( PanelPredicateSystemDuplicateKing )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS:
            
            editable_pred_panel_classes.append( PanelPredicateSystemFileViewingStatsViews )
            editable_pred_panel_classes.append( PanelPredicateSystemFileViewingStatsViewtime )
            
        
        vbox = QP.VBoxLayout()
        
        if label is not None:
            
            st = ClientGUICommon.BetterStaticText( self, label = label )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        for button in static_pred_buttons:
            
            QP.AddToLayout( vbox, button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        for pred_class in editable_pred_panel_classes:
            
            panel = self._EditablePredPanel( self, pred_class )
            
            QP.AddToLayout( vbox, panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        if len( static_pred_buttons ) > 0 and len( editable_pred_panel_classes ) == 0:
            
            HG.client_controller.CallAfterQtSafe( static_pred_buttons[0], static_pred_buttons[0].setFocus, QC.Qt.OtherFocusReason )
            
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        return self._predicates
        
    
    def SubPanelOK( self, predicates ):
        
        self._predicates = predicates
        
        self.parentWidget().DoOK()
        
    
    class _EditablePredPanel( QW.QWidget ):
        
        def __init__( self, parent, predicate_class ):
            
            QW.QWidget.__init__( self, parent )
            
            self._predicate_panel = predicate_class( self )
            self._parent = parent
            
            self._ok = QW.QPushButton( 'ok', self )
            self._ok.clicked.connect( self._DoOK )
            self._ok.setObjectName( 'HydrusAccept' )
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._predicate_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            QP.AddToLayout( hbox, self._ok, CC.FLAGS_CENTER_PERPENDICULAR )
            
            self.setLayout( hbox )
            
            HG.client_controller.CallAfterQtSafe( self._ok, self._ok.setFocus, QC.Qt.OtherFocusReason )
            
        
        def _DoOK( self ):
            
            try:
                
                self._predicate_panel.CheckCanOK()
                
            except Exception as e:
                
                message = 'Cannot OK: {}'.format( e )
                
                QW.QMessageBox.warning( self, 'Warning', message )
                
                return
                
            
            predicates = self._predicate_panel.GetPredicates()
            
            self._parent.SubPanelOK( predicates )
            
        
        def keyPressEvent( self, event ):
            
            ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
            
            if key in ( QC.Qt.Key_Enter, QC.Qt.Key_Return ):
                
                self._DoOK()
                
            else:
                
                event.ignore()
                
            
        
    
class StaticSystemPredicateButton( QW.QPushButton ):
    
    def __init__( self, parent, predicates, forced_label = None ):
        
        QW.QPushButton.__init__( self, parent )
        
        self._parent = parent
        self._predicates = predicates
        self._forced_label = forced_label
        
        if forced_label is None:
            
            label = ', '.join( ( predicate.ToString() for predicate in self._predicates ) )
            
        else:
            
            label = forced_label
            
        
        self.setText( label )
        
        self.clicked.connect( self.DoOK )
        
    
    def DoOK( self ):
        
        self._parent.SubPanelOK( self._predicates )
        
    
class PanelPredicateSystem( QW.QWidget ):
    
    def CheckCanOK( self ):
        
        pass
        
    
    def GetPredicates( self ):
        
        raise NotImplementedError()
        

class PanelPredicateSystemAgeDate( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._date = QW.QCalendarWidget( self )
        
        qt_dt = QC.QDate.currentDate()
        
        qt_dt.addDays( -7 )
        
        self._date.setSelectedDate( qt_dt )
        
        self._sign.SetStringSelection( '>' )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:time imported'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._date, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        qt_dt = self._date.selectedDate()
        
        year = qt_dt.year()
        month = qt_dt.month()
        day = qt_dt.day()
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( self._sign.GetStringSelection(), 'date', ( year, month, day ) ) ), )
        
        return predicates
        
    
class PanelPredicateSystemAgeDelta( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','>'] )
        
        self._years = QP.MakeQSpinBox( self, max=30, width = 60 )
        self._months = QP.MakeQSpinBox( self, max=60, width = 60 )
        self._days = QP.MakeQSpinBox( self, max=90, width = 60 )
        self._hours = QP.MakeQSpinBox( self, max=24, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        try:
            
            ( sign, age_type, ( years, months, days, hours ) ) = system_predicates[ 'age' ]
            
        except:
            
            # wew lad. replace this all with proper system pred saving on new_options in future
            sign = '<'
            
            years = 0
            months = 0
            days = 7
            hours = 0
            
        
        self._sign.SetStringSelection( sign )
        
        self._years.setValue( years )
        self._months.setValue( months )
        self._days.setValue( days )
        self._hours.setValue( hours )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:time imported'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._years, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'years'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._months, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'months'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._days, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'days'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hours, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'hours'), CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( self._sign.GetStringSelection(), 'delta', (self._years.value(), self._months.value(), self._days.value(), self._hours.value() ) ) ), )
        
        return predicates
        
    
class PanelPredicateSystemModifiedDate( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._date = QW.QCalendarWidget( self )
        
        qt_dt = QC.QDate.currentDate()
        
        qt_dt.addDays( -7 )
        
        self._date.setSelectedDate( qt_dt )
        
        self._sign.SetStringSelection( '>' )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:modified date'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._date, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        qt_dt = self._date.selectedDate()
        
        year = qt_dt.year()
        month = qt_dt.month()
        day = qt_dt.day()
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, ( self._sign.GetStringSelection(), 'date', ( year, month, day ) ) ), )
        
        return predicates
        
    
class PanelPredicateSystemModifiedDelta( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','>'] )
        
        self._years = QP.MakeQSpinBox( self, max=30 )
        self._months = QP.MakeQSpinBox( self, max=60 )
        self._days = QP.MakeQSpinBox( self, max=90 )
        self._hours = QP.MakeQSpinBox( self, max=24 )
        
        # wew lad. replace this all with proper system pred saving on new_options in future
        sign = '<'
        
        years = 0
        months = 0
        days = 7
        hours = 0
        
        self._sign.SetStringSelection( sign )
        
        self._years.setValue( years )
        self._months.setValue( months )
        self._days.setValue( days )
        self._hours.setValue( hours )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:modified date'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._years, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'years'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._months, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'months'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._days, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'days'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hours, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'hours'), CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, ( self._sign.GetStringSelection(), 'delta', ( self._years.value(), self._months.value(), self._days.value(), self._hours.value() ) ) ), )
        
        return predicates
        
    
class PanelPredicateSystemDuplicateKing( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        choices = [ 'is the best quality file of its group', 'is not the best quality file of its group' ]
        
        self._king = QP.RadioBox( self, choices = choices, vertical = True )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._king, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        king_str = self._king.GetStringSelection()
        
        king = 'is the' in king_str
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING, king ), )
        
        return predicates
        
    
class PanelPredicateSystemDuplicateRelationships( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        choices = [ '<', '\u2248', '=', '>' ]
        
        self._sign = QP.RadioBox( self, choices = choices )
        
        self._num = QP.MakeQSpinBox( self, min=0, max=65535 )
        
        choices = [ ( HC.duplicate_type_string_lookup[ status ], status ) for status in ( HC.DUPLICATE_MEMBER, HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_POTENTIAL ) ]
        
        self._dupe_type = ClientGUICommon.BetterRadioBox( self, choices = choices, vertical = True )
        
        #
        
        self._sign.SetStringSelection( '>' )
        self._num.setValue( 0 )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:num file relationships'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._dupe_type, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT, ( self._sign.GetStringSelection(), self._num.value(), self._dupe_type.GetValue() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemDuration( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        choices = [ '<', '\u2248', '=', '>' ]
        
        self._sign = QP.RadioBox( self, choices = choices )
        
        self._duration_s = QP.MakeQSpinBox( self, max=3599, width = 60 )
        self._duration_ms = QP.MakeQSpinBox( self, max=999, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, ms ) = system_predicates[ 'duration' ]
        
        s = ms // 1000
        
        ms = ms % 1000
        
        self._sign.SetStringSelection( sign )
        
        self._duration_s.setValue( s )
        self._duration_ms.setValue( ms )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:duration'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._duration_s, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'s'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._duration_ms, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'ms'), CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( self._sign.GetStringSelection(), self._duration_s.value() * 1000 + self._duration_ms.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemFileService( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = ClientGUICommon.BetterRadioBox( self, choices = [ ( 'is', True ), ( 'is not', False ) ], vertical = True )
        
        self._current_pending = ClientGUICommon.BetterRadioBox( self, choices = [ ( 'currently in', HC.CONTENT_STATUS_CURRENT ), ( 'pending to', HC.CONTENT_STATUS_PENDING ) ], vertical = True )
        
        services = HG.client_controller.services_manager.GetServices( HC.FILE_SERVICES )
        
        choices = [ ( service.GetName(), service.GetServiceKey() ) for service in services ]
        
        self._file_service_key = ClientGUICommon.BetterRadioBox( self, choices = choices, vertical = True )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:file service:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._current_pending, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._file_service_key, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( self._sign.GetValue(), self._current_pending.GetValue(), self._file_service_key.GetValue() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemFileViewingStatsViews( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._viewing_locations = QP.CheckListBox( self )
        
        self._viewing_locations.Append( 'media views', 'media' )
        self._viewing_locations.Append( 'preview views', 'preview' )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._value = QP.MakeQSpinBox( self, min=0, max=1000000 )
        
        #
        
        self._viewing_locations.Check( 0 )
        
        self._sign.Select( 3 )
        
        self._value.setValue( 10 )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._viewing_locations, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._value, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        viewing_locations = self._viewing_locations.GetChecked()
        
        if len( viewing_locations ) == 0:
            
            viewing_locations = [ 'media' ]
            
        
        sign = self._sign.GetStringSelection()
        
        value = self._value.value()
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'views', tuple( viewing_locations ), sign, value ) ), )
        
        return predicates
        
    
class PanelPredicateSystemFileViewingStatsViewtime( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._viewing_locations = QP.CheckListBox( self )
        
        self._viewing_locations.Append( 'media viewtime', 'media' )
        self._viewing_locations.Append( 'preview viewtime', 'preview' )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._time_delta = ClientGUITime.TimeDeltaCtrl( self, min = 0, days = True, hours = True, minutes = True, seconds = True )
        
        #
        
        self._viewing_locations.Check( 0 )
        
        self._sign.Select( 3 )
        
        self._time_delta.SetValue( 600 )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._viewing_locations, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._time_delta, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        viewing_locations = self._viewing_locations.GetChecked()
        
        if len( viewing_locations ) == 0:
            
            viewing_locations = [ 'media' ]
            
        
        sign = self._sign.GetStringSelection()
        
        time_delta = self._time_delta.GetValue()
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'viewtime', tuple( viewing_locations ), sign, time_delta ) ), )
        
        return predicates
        
    
class PanelPredicateSystemFramerate( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        choices = [ '<', '=', '>' ]
        
        self._sign = QP.RadioBox( self, choices = choices )
        
        self._framerate = QP.MakeQSpinBox( self, min = 1, max = 3600, width = 60 )
        
        self._sign.SetStringSelection( '=' )
        self._framerate.setValue( 60 )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, 'system:framerate' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._framerate, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, 'fps' ), CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText( 'All framerate searches are +/- 5%. Exactly searching for 29.97 is not currently possible.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.setLayout( vbox )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FRAMERATE, ( self._sign.GetStringSelection(), self._framerate.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemHash( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._hashes = QW.QPlainTextEdit( self )
        
        ( init_width, init_height ) = ClientGUIFunctions.ConvertTextToPixels( self._hashes, ( 66, 10 ) )
        
        self._hashes.setMinimumSize( QC.QSize( init_width, init_height ) )
        
        choices = [ 'sha256', 'md5', 'sha1', 'sha512' ]
        
        self._hash_type = QP.RadioBox( self, choices = choices, vertical = True )
        
        self._hashes.setPlaceholderText( 'enter hash (paste newline-separated for multiple hashes)' )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:hash='), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hashes, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hash_type, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        # replace this with a better 'cleanhashes( hash_type )' thing that checks length properly
        # and have that then show in the plaintext above a red background or whatever when invalid hashes, with some text
        
        hex_hashes_raw = self._hashes.toPlainText()
        
        hex_hashes = HydrusText.DeserialiseNewlinedTexts( hex_hashes_raw )
        
        hex_hashes = [ HydrusText.HexFilter( hex_hash ) for hex_hash in hex_hashes ]
        
        hex_hashes = [ hex_hash for hex_hash in hex_hashes if len( hex_hash ) % 2 == 0 ]
        
        hex_hashes = HydrusData.DedupeList( hex_hashes )
        
        hashes = tuple( [ bytes.fromhex( hex_hash ) for hex_hash in hex_hashes ] )
        
        hash_type = self._hash_type.GetStringSelection()
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HASH, ( hashes, hash_type ) ), )
        
        return predicates
        
    
class PanelPredicateSystemHasNoteName( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has note with name ', True )
        self._operator.addItem( 'does not have note with name', False )
        
        self._name = QW.QLineEdit( self )
        self._name.setFixedWidth( 250 )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:note name'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._name, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        name = self._name.text()
        
        if name == '':
            
            name = 'notes'
            
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_NOTE_NAME, ( self._operator.GetValue(), name ) ), )
        
        return predicates
        
    
class PanelPredicateSystemHeight( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._height = QP.MakeQSpinBox( self, max=200000, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, height ) = system_predicates[ 'height' ]
        
        self._sign.SetStringSelection( sign )
        
        self._height.setValue( height )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:height'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._height, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( self._sign.GetStringSelection(), self._height.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemKnownURLsExactURL( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has', True )
        self._operator.addItem( 'does not have', False )
        
        self._exact_url = QW.QLineEdit( self )
        self._exact_url.setFixedWidth( 250 )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:known url'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'exact url:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._exact_url, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        operator = self._operator.GetValue()
        
        if operator:
            
            operator_description = 'has url: '
            
        else:
            
            operator_description = 'does not have url: '
            
        
        rule_type = 'exact_match'
        
        exact_url = self._exact_url.text()
        
        rule = exact_url
        
        description = operator_description + exact_url
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) ), )
        
        return predicates
        
    
class PanelPredicateSystemKnownURLsDomain( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has', True )
        self._operator.addItem( 'does not have', False )
        
        self._domain = QW.QLineEdit( self )
        self._domain.setFixedWidth( 250 )
        
        self._domain.setPlaceholderText( 'example.com' )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:known url'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'a url with domain:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._domain, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        operator = self._operator.GetValue()
        
        if operator:
            
            operator_description = 'has a url with domain: '
            
        else:
            
            operator_description = 'does not have a url with domain: '
            
        
        rule_type = 'domain'
        
        domain = self._domain.text()
        
        rule = domain
        
        description = operator_description + domain
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) ), )
        
        return predicates
        
    
class PanelPredicateSystemKnownURLsRegex( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has', True )
        self._operator.addItem( 'does not have', False )
        
        self._regex = QW.QLineEdit( self )
        self._regex.setFixedWidth( 250 )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:known url'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'a url that matches this regex:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._regex, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def CheckCanOK( self ):
        
        regex = self._regex.text()
        
        try:
            
            re.compile( regex )
            
        except Exception as e:
            
            raise Exception( 'Cannot compile that regex: {}'.format( e ) )
            
        
    
    def GetPredicates( self ):
        
        operator = self._operator.GetValue()
        
        if operator:
            
            operator_description = 'has a url matching regex: '
            
        else:
            
            operator_description = 'does not have a url matching regex: '
            
        
        rule_type = 'regex'
        
        regex = self._regex.text()
        
        rule = regex
        
        description = operator_description + regex
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) ), )
        
        return predicates
        
    
class PanelPredicateSystemKnownURLsURLClass( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._operator = ClientGUICommon.BetterChoice( self )
        
        self._operator.addItem( 'has', True )
        self._operator.addItem( 'does not have', False )
        
        self._url_classes = ClientGUICommon.BetterChoice( self )
        
        for url_class in HG.client_controller.network_engine.domain_manager.GetURLClasses():
            
            if url_class.ShouldAssociateWithFiles():
                
                self._url_classes.addItem( url_class.GetName(), url_class )
                
            
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:known url'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._operator, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'url matching this class:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._url_classes, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        operator = self._operator.GetValue()
        
        if operator:
            
            operator_description = 'has '
            
        else:
            
            operator_description = 'does not have '
            
        
        rule_type = 'url_class'
        
        url_class = self._url_classes.GetValue()
        
        rule = url_class
        
        description = operator_description + url_class.GetName() + ' url'
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( operator, rule_type, rule, description ) ), )
        
        return predicates
        
    
class PanelPredicateSystemLimit( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._limit = QP.MakeQSpinBox( self, max=1000000, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        limit = system_predicates[ 'limit' ]
        
        self._limit.setValue( limit )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:limit='), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._limit, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, self._limit.value() ), )
        
        return predicates
        
    
class PanelPredicateSystemMime( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._mimes = ClientGUIOptionsPanels.OptionsPanelMimes( self, HC.SEARCHABLE_MIMES )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        mimes = system_predicates[ 'mime' ]
        
        if isinstance( mimes, int ):
            
            mimes = ( mimes, )
            
        
        self._mimes.SetValue( mimes )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, 'system:filetype' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._mimes, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        mimes = self._mimes.GetValue()
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, mimes ), )
        
        return predicates
        
    
class PanelPredicateSystemNumPixels( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=[ '<', '\u2248', '=', '>' ] )
        
        self._num_pixels = QP.MakeQSpinBox( self, max=1048576, width = 60 )
        
        self._unit = QP.RadioBox( self, choices=['pixels','kilopixels','megapixels'] )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, num_pixels, unit ) = system_predicates[ 'num_pixels' ]
        
        self._sign.SetStringSelection( sign )
        
        self._num_pixels.setValue( num_pixels )
        
        self._unit.SetStringSelection( HydrusData.ConvertIntToPixels( unit ) )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:num_pixels'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num_pixels, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._unit, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_PIXELS, ( self._sign.GetStringSelection(), self._num_pixels.value(), HydrusData.ConvertPixelsToInt( self._unit.GetStringSelection() ) ) ), )
        
        return predicates
        
    
class PanelPredicateSystemNumFrames( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        choices = [ '<', '\u2248', '=', '>' ]
        
        self._sign = QP.RadioBox( self, choices = choices )
        
        self._num_frames = QP.MakeQSpinBox( self, min = 0, max = 1000000, width = 80 )
        
        self._sign.SetStringSelection( '>' )
        self._num_frames.setValue( 600 )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, 'system:number of frames' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num_frames, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_FRAMES, ( self._sign.GetStringSelection(), self._num_frames.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemNumTags( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._namespace = ClientGUICommon.NoneableTextCtrl( self, none_phrase = 'all tags' )
        self._namespace.setToolTip( 'Enable but leave blank for unnamespaced tags.' )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._num_tags = QP.MakeQSpinBox( self, max=2000, width = 60 )
        
        ( namespace, sign, num_tags ) = ( None, '>', 4 )
        
        self._namespace.SetValue( namespace )
        
        self._sign.SetStringSelection( sign )
        
        self._num_tags.setValue( num_tags )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:number of tags: namespace:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._namespace, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num_tags, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        ( namespace, operator, value ) = ( self._namespace.GetValue(), self._sign.GetStringSelection(), self._num_tags.value() )
        
        predicate = None
        
        if namespace is not None:
            
            number_test = ClientSearch.NumberTest.STATICCreateFromCharacters( operator, value )
            
            if number_test.IsZero():
                
                predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, namespace, inclusive = False )
                
            elif number_test.IsAnythingButZero():
                
                predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, namespace )
                
            
        
        if predicate is None:
            
            predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( namespace, operator, value ) )
            
        
        predicates = ( predicate, )
        
        return predicates
        
    
class PanelPredicateSystemNumNotes( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices = [ '<', '=', '>' ] )
        
        self._num_notes = QP.MakeQSpinBox( self, max = 256, width = 60 )
        
        self._sign.SetStringSelection( '=' )
        
        self._num_notes.setValue( 1 )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:number of notes'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num_notes, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_NOTES, ( self._sign.GetStringSelection(), self._num_notes.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemNumWords( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._num_words = QP.MakeQSpinBox( self, max=1000000, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, num_words ) = system_predicates[ 'num_words' ]
        
        self._sign.SetStringSelection( sign )
        
        self._num_words.setValue( num_words )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:number of words'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num_words, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( self._sign.GetStringSelection(), self._num_words.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemRating( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        #
        
        local_like_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ) )
        
        self._like_checkboxes_to_info = {}
        
        self._like_rating_ctrls = []
        
        gridbox = QP.GridLayout( cols = 5 )
        
        gridbox.setColumnStretch( 0, 1 )
        
        for service in local_like_services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            rated_checkbox = QW.QCheckBox( 'rated', self )
            not_rated_checkbox = QW.QCheckBox( 'not rated', self )
            rating_ctrl = ClientGUIRatings.RatingLikeDialog( self, service_key )
            
            self._like_checkboxes_to_info[ rated_checkbox ] = ( service_key, ClientRatings.SET )
            self._like_checkboxes_to_info[ not_rated_checkbox ] = ( service_key, ClientRatings.NULL )
            self._like_rating_ctrls.append( rating_ctrl )
            
            QP.AddToLayout( gridbox, ClientGUICommon.BetterStaticText(self,name), CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( gridbox, rated_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( gridbox, not_rated_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
            ClientGUICommon.AddGridboxStretchSpacer( gridbox )
            QP.AddToLayout( gridbox, rating_ctrl, CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        #
        
        local_numerical_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        self._numerical_checkboxes_to_info = {}
        
        self._numerical_rating_ctrls_to_info = {}
        
        for service in local_numerical_services:
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            rated_checkbox = QW.QCheckBox( 'rated', self )
            not_rated_checkbox = QW.QCheckBox( 'not rated', self )
            choice = QP.RadioBox( self, choices=['>','<','=','\u2248'] )
            rating_ctrl = ClientGUIRatings.RatingNumericalDialog( self, service_key )
            
            choice.Select( 2 )
            
            self._numerical_checkboxes_to_info[ rated_checkbox ] = ( service_key, ClientRatings.SET )
            self._numerical_checkboxes_to_info[ not_rated_checkbox ] = ( service_key, ClientRatings.NULL )
            self._numerical_rating_ctrls_to_info[ rating_ctrl ] = choice
            
            QP.AddToLayout( gridbox, ClientGUICommon.BetterStaticText(self,name), CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( gridbox, rated_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( gridbox, not_rated_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( gridbox, choice, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( gridbox, rating_ctrl, CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def GetPredicates( self ):
        
        infos = []
        
        #
        
        for ( checkbox, ( service_key, rating_state ) ) in list(self._like_checkboxes_to_info.items()):
            
            if checkbox.isChecked():
                
                if rating_state == ClientRatings.SET:
                    
                    value = 'rated'
                    
                elif rating_state == ClientRatings.NULL:
                    
                    value = 'not rated'
                    
                
                infos.append( ( '=', value, service_key ) )
                
            
        
        for ctrl in self._like_rating_ctrls:
            
            rating_state = ctrl.GetRatingState()
            
            if rating_state in ( ClientRatings.LIKE, ClientRatings.DISLIKE ):
                
                if rating_state == ClientRatings.LIKE:
                    
                    value = 1
                    
                elif rating_state == ClientRatings.DISLIKE:
                    
                    value = 0
                    
                
                service_key = ctrl.GetServiceKey()
                
                infos.append( ( '=', value, service_key ) )
                
            
        
        #
        
        for ( checkbox, ( service_key, rating_state ) ) in list(self._numerical_checkboxes_to_info.items()):
            
            if checkbox.isChecked():
                
                if rating_state == ClientRatings.SET:
                    
                    value = 'rated'
                    
                elif rating_state == ClientRatings.NULL:
                    
                    value = 'not rated'
                    
                
                infos.append( ( '=', value, service_key ) )
                
            
        
        for ( ctrl, choice ) in list(self._numerical_rating_ctrls_to_info.items()):
            
            rating_state = ctrl.GetRatingState()
            
            if rating_state == ClientRatings.SET:
                
                operator = choice.GetStringSelection()
                
                value = ctrl.GetRating()
                
                service_key = ctrl.GetServiceKey()
                
                infos.append( ( operator, value, service_key ) )
                
            
        
        #
        
        predicates = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, info ) for info in infos ]
        
        return predicates
        
    
class PanelPredicateSystemRatio( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['=','wider than','taller than','\u2248'] )
        
        self._width = QP.MakeQSpinBox( self, max=50000, width = 60 )
        
        self._height = QP.MakeQSpinBox( self, max=50000, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, width, height ) = system_predicates[ 'ratio' ]
        
        self._sign.SetStringSelection( sign )
        
        self._width.setValue( width )
        
        self._height.setValue( height )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:ratio'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._width, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,':'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._height, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( self._sign.GetStringSelection(), self._width.value(), self._height.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemSimilarTo( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._hashes = QW.QPlainTextEdit( self )
        
        ( init_width, init_height ) = ClientGUIFunctions.ConvertTextToPixels( self._hashes, ( 66, 10 ) )
        
        self._hashes.setMinimumSize( QC.QSize( init_width, init_height ) )
        
        self._max_hamming = QP.MakeQSpinBox( self, max=256, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        self._hashes.setPlaceholderText( 'enter hash (paste newline-separated for multiple hashes)' )
        
        hamming_distance = system_predicates[ 'hamming_distance' ]
        
        self._max_hamming.setValue( hamming_distance )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:similar_to'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._hashes, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, QW.QLabel( '\u2248', self ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._max_hamming, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        hex_hashes_raw = self._hashes.toPlainText()
        
        hex_hashes = HydrusText.DeserialiseNewlinedTexts( hex_hashes_raw )
        
        hex_hashes = [ HydrusText.HexFilter( hex_hash ) for hex_hash in hex_hashes ]
        
        hex_hashes = HydrusData.DedupeList( hex_hashes )
        
        hashes = tuple( [ bytes.fromhex( hex_hash ) for hex_hash in hex_hashes ] )
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, ( hashes, self._max_hamming.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemSize( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._bytes = ClientGUIControls.BytesControl( self )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, size, unit ) = system_predicates[ 'size' ]
        
        self._sign.SetStringSelection( sign )
        
        self._bytes.SetSeparatedValue( size, unit )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:filesize'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._bytes, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        ( size, unit ) = self._bytes.GetSeparatedValue()
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( self._sign.GetStringSelection(), size, unit ) ), )
        
        return predicates
        
    
class PanelPredicateSystemTagAsNumber( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._namespace = QW.QLineEdit( self )
        
        choices = [ '<', '\u2248', '>' ]
        
        self._sign = QP.RadioBox( self, choices = choices )
        
        self._num = QP.MakeQSpinBox( self, min=-99999999, max=99999999 )
        
        #
        
        self._namespace.setText( 'page' )
        self._sign.SetStringSelection( '>' )
        self._num.setValue( 0 )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:tag as number'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._namespace, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._num, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER, ( self._namespace.text(), self._sign.GetStringSelection(), self._num.value() ) ), )
        
        return predicates
        
    
class PanelPredicateSystemWidth( PanelPredicateSystem ):
    
    def __init__( self, parent ):
        
        PanelPredicateSystem.__init__( self, parent )
        
        self._sign = QP.RadioBox( self, choices=['<','\u2248','=','>'] )
        
        self._width = QP.MakeQSpinBox( self, max=200000, width = 60 )
        
        system_predicates = HC.options[ 'file_system_predicates' ]
        
        ( sign, width ) = system_predicates[ 'width' ]
        
        self._sign.SetStringSelection( sign )
        
        self._width.setValue( width )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,'system:width'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sign, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._width, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetPredicates( self ):
        
        predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( self._sign.GetStringSelection(), self._width.value() ) ), )
        
        return predicates
        
    
