import typing

from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIExceptionHandling
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.metadata import ClientGUITagsEditNamespaceSort
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearchTagContext

# wew lad
# https://stackoverflow.com/questions/46456238/checkbox-not-visible-inside-combobox
class CheckBoxDelegate( QW.QStyledItemDelegate ):
    
    def __init__( self, parent = None ):
        
        super().__init__( parent )
        

    def createEditor( self, parent, op, idx ):
        
        self.editor = QW.QCheckBox( parent )
        
    

class CollectComboCtrl( QW.QComboBox ):
    
    itemChanged = QC.Signal()
    
    def __init__( self, parent, media_collect ):
        
        # TODO: Rewrite this garbage! A custom paintEvent, r u serious???
        
        super().__init__( parent )
        
        self.view().pressed.connect( self._HandleItemPressed )
        
        # this was previously 'if Fusion style only', but as it works for normal styles too, it is more helpful to have it always on
        self.setItemDelegate( CheckBoxDelegate() )
        
        self.setModel( QG.QStandardItemModel( self ) )
        
        self._ReinitialiseChoices()
        
        # Trick to display custom text
        
        self._cached_text = ''
        
        if media_collect.DoesACollect():
            
            CG.client_controller.CallAfterQtSafe( self, self.SetCollectByValue, media_collect )
            
        
    
    def _HandleItemPressed( self, index ):
        
        item = self.model().itemFromIndex( index )
        
        if item.checkState() == QC.Qt.CheckState.Checked:
            
            item.setCheckState( QC.Qt.CheckState.Unchecked )
            
        else:
            
            item.setCheckState( QC.Qt.CheckState.Checked )
            
        
        self.SetValue( self._cached_text )
        
        self.itemChanged.emit()
        
    
    def _ReinitialiseChoices( self ):
        
        text_and_data_tuples = set()
        
        for media_sort in CG.client_controller.new_options.GetDefaultNamespaceSorts():
            
            namespaces = media_sort.GetNamespaces()
            
            try:
                
                text_and_data_tuples.update( namespaces )
                
            except Exception as e:
                
                HydrusData.DebugPrint( 'Bad namespaces: {}'.format( namespaces ) )
                
                HydrusData.ShowText( 'Hey, your namespace-based sorts are likely damaged. Details have been written to the log, please let hydev know!' )
                
            
        
        text_and_data_tuples = sorted( ( ( namespace, ( 'namespace', namespace ) ) for namespace in text_and_data_tuples ) )
        
        star_ratings_services = CG.client_controller.services_manager.GetServices( HC.STAR_RATINGS_SERVICES )
        
        for star_ratings_service in star_ratings_services:
            
            text_and_data_tuples.append( ( star_ratings_service.GetName(), ( 'rating', star_ratings_service.GetServiceKey() ) ) )
            
        
        current_text_and_data_tuples = []
        
        for i in range( self.count() ):
            
            item = self.model().item( i, 0 )
            
            t = item.text()
            d = self.itemData( i, QC.Qt.ItemDataRole.UserRole )
            
            current_text_and_data_tuples.append( ( t, d ) )
            
        
        made_changes = False
        
        if current_text_and_data_tuples != text_and_data_tuples:
            
            if self.count() > 0:
                
                # PRO TIP 4 U: if you say self.clear() here, the program has a ~15% chance to crash instantly if you have previously done a clear/add cycle!
                # this affects PyQt and PySide, 5 and 6, running from source, so must be something in Qt core. some argument between the model and widget
                self.model().clear()
                
            
            for ( text, data ) in text_and_data_tuples:
                
                self.addItem( text, userData = data )
                
                item = self.model().item( self.count() - 1, 0 )
                
                item.setCheckState( QC.Qt.CheckState.Unchecked )
                
            
            made_changes = True
            
        
        return made_changes
        
    
    def GetCheckedIndices( self ):
        
        indices = []
        
        for idx in range( self.count() ):

            item = self.model().item( idx )
            
            if item.checkState() == QC.Qt.CheckState.Checked:
                
                indices.append( idx )
                
            
        
        return indices
        

    def GetCheckedStrings( self ):
        
        strings = [ ]
        
        for idx in range( self.count() ):
            
            item = self.model().item( idx )
            
            if item.checkState() == QC.Qt.CheckState.Checked:
                
                strings.append( item.text() )
                
            
        
        return strings
        
    
    def GetValues( self ):
        
        namespaces = []
        rating_service_keys = []
        
        for index in self.GetCheckedIndices():
            
            ( collect_type, collect_data ) = self.itemData( index, QC.Qt.ItemDataRole.UserRole )
            
            if collect_type == 'namespace':
                
                namespaces.append( collect_data )
                
            elif collect_type == 'rating':
                
                rating_service_keys.append( collect_data )
                
            
        
        collect_strings = self.GetCheckedStrings()
        
        if len( collect_strings ) > 0:
            
            description = 'collect by ' + '-'.join( collect_strings )
            
        else:
            
            description = 'no collections'
            
        
        return ( namespaces, rating_service_keys, description )
        
    
    def hidePopup(self):
        
        if not self.view().underMouse():
            
            QW.QComboBox.hidePopup( self )
            
            
        
    
    def model( self ) -> QG.QStandardItemModel:
        
        return typing.cast( QG.QStandardItemModel, super().model() )
        
    
    def paintEvent( self, event ):
        
        try:
            
            painter = QW.QStylePainter( self )
            painter.setPen( self.palette().color( QG.QPalette.ColorRole.Text ) )
            
            opt = QW.QStyleOptionComboBox()
            self.initStyleOption( opt )
            
            opt.currentText = self._cached_text
            
            painter.drawComplexControl( QW.QStyle.CC_ComboBox, opt )
            
            painter.drawControl( QW.QStyle.CE_ComboBoxLabel, opt )
            
        except Exception as e:
            
            ClientGUIExceptionHandling.HandlePaintEventException( self, e )
            
        
    
    def ReinitialiseChoices( self ):
        
        return self._ReinitialiseChoices()
        
    
    def SetValue( self, text ):
        
        self._cached_text = text
        
        self.setCurrentText( text )
        
        
    
    def SetCollectByValue( self, media_collect ):

        try:
            
            indices_to_check = []

            for index in range( self.count() ):

                ( collect_type, collect_data ) = self.itemData( index, QC.Qt.ItemDataRole.UserRole )

                p1 = collect_type == 'namespace' and collect_data in media_collect.namespaces
                p2 = collect_type == 'rating' and collect_data in media_collect.rating_service_keys

                if p1 or p2:
                    
                    indices_to_check.append( index )
                    
                

            self.SetCheckedIndices( indices_to_check )
            
            self.itemChanged.emit()
            
        except Exception as e:
            
            HydrusData.ShowText( 'Failed to set a collect-by value!' )

            HydrusData.ShowException( e )
            
        

    def SetCheckedIndices( self, indices_to_check ):
        
        for idx in range( self.count() ):

            item = self.model().item( idx )
            
            if idx in indices_to_check:
                
                item.setCheckState( QC.Qt.CheckState.Checked )
                
            else:
                
                item.setCheckState( QC.Qt.CheckState.Unchecked )
                
            
        
    

class MediaCollectControl( QW.QWidget ):
    
    collectChanged = QC.Signal( ClientMedia.MediaCollect )
    
    def __init__( self, parent, media_collect: ClientMedia.MediaCollect | None = None ):
        
        super().__init__( parent )
        
        # this is trash, rewrite it to deal with the media_collect object, not the management controller
        
        if media_collect is None:
            
            media_collect = CG.client_controller.new_options.GetDefaultCollect()
            
        
        self._media_collect = media_collect
        self._tag_context = self._media_collect.tag_context
        
        self._collect_comboctrl = CollectComboCtrl( self, self._media_collect )
        
        self._cog_icon_button = ClientGUIMenuButton.CogIconButton( self, [] )
        
        self._collect_unmatched = self._media_collect.collect_unmatched
        
        #
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._collect_comboctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._cog_icon_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        #
        
        self._UpdateLabel()
        self._UpdateCogIconButton()
        
        self._collect_comboctrl.itemChanged.connect( self.CollectValuesChanged )
        
        self._collect_comboctrl.installEventFilter( self )
        
    
    def _BroadcastCollect( self ):
        
        self.collectChanged.emit( self._media_collect )
        
    
    def _UpdateCogIconButton( self ):
        
        menu_template_items = []
        
        #
        
        services_manager = CG.client_controller.services_manager
        
        service_types_in_order = [ HC.LOCAL_TAG, HC.TAG_REPOSITORY, HC.COMBINED_TAG ]
        
        services = services_manager.GetServices( service_types_in_order )
        
        submenu_template_items = []
        
        last_seen_service_type = None
        
        # need this isolated for lambda scope stuff
        def get_check_manager_lambda_1( tc ):
            
            return lambda: tc == self._tag_context
            
        
        for service in services:
            
            if last_seen_service_type is not None and last_seen_service_type != service.GetServiceType():
                
                submenu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
                
            
            new_tag_context = self._tag_context.Duplicate()
            
            new_tag_context.service_key = service.GetServiceKey()
            
            check_manager = ClientGUICommon.CheckboxManagerCalls(
                HydrusData.Call( self.SetTagContext, new_tag_context ),
                get_check_manager_lambda_1( new_tag_context )
            )
            
            submenu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( service.GetName(), 'Filter the namespaces by this tag domain.', check_manager ) )
            
            last_seen_service_type = service.GetServiceType()
            
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSubmenu( 'tag service', submenu_template_items ) )
        
        #
        
        # need this isolated for lambda scope stuff
        def get_check_manager_lambda_2( tdt ):
            
            return lambda: tdt == self._collect_unmatched
            
        
        submenu_template_items = []
        
        for ( label, desc, value ) in [
            ( 'collect into one group', 'Collect files that have none of these namespaces into one group.', True ),
            ( 'leave separate', 'Let files that have none of these namespaces stay separated.', False )
        ]:
            
            check_manager = ClientGUICommon.CheckboxManagerCalls(
                HydrusData.Call( self.SetCollectUnmatched, value ),
                get_check_manager_lambda_2( value )
            )
            
            submenu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( label, desc, check_manager ) )
            
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSubmenu( 'unmatched files', submenu_template_items ) )
        
        #
        
        self._cog_icon_button.SetMenuItems( menu_template_items )
        
    
    def _UpdateLabel( self ):
        
        ( namespaces, rating_service_keys, description ) = self._collect_comboctrl.GetValues()
        
        self._collect_comboctrl.SetValue( description )
        
    
    def CollectValuesChanged( self ):
        
        ( namespaces, rating_service_keys, description ) = self._collect_comboctrl.GetValues()
        
        self._media_collect = ClientMedia.MediaCollect( namespaces = namespaces, rating_service_keys = rating_service_keys, collect_unmatched = self._collect_unmatched, tag_context = self._tag_context )
        
        self._UpdateLabel()
        self._UpdateCogIconButton()
        
        self._BroadcastCollect()
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if watched == self._collect_comboctrl:
                
                if event.type() == QC.QEvent.Type.MouseButtonPress:
                    
                    event = typing.cast( QG.QMouseEvent, event )
                    
                    if event.button() == QC.Qt.MouseButton.MiddleButton:
                        
                        self.SetCollect( ClientMedia.MediaCollect( collect_unmatched = self._media_collect.collect_unmatched ) )
                        
                        return True
                        
                    
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
    def GetValue( self ):
        
        return self._media_collect
        
    
    def NotifyNewOptions( self ):
        
        media_collect = self._media_collect.Duplicate()
        
        made_changes = self._collect_comboctrl.ReinitialiseChoices()
        
        if made_changes:
            
            self.SetCollect( media_collect, do_broadcast = False )
            
        
    
    def SetCollect( self, media_collect: ClientMedia.MediaCollect, do_broadcast = True ):
        
        self._media_collect = media_collect
        
        self._collect_comboctrl.blockSignals( True )
        
        self._collect_comboctrl.SetCollectByValue( self._media_collect )
        self._collect_unmatched = self._media_collect.collect_unmatched
        self._tag_context = self._media_collect.tag_context
        
        self._UpdateLabel()
        self._UpdateCogIconButton()
        
        self._collect_comboctrl.blockSignals( False )
        
        if do_broadcast:
            
            self._BroadcastCollect()
            
        
    
    def SetCollectUnmatched( self, value: bool ):
        
        self._collect_unmatched = value
        
        self.CollectValuesChanged()
        
    
    def SetTagContext( self, tag_context: ClientSearchTagContext.TagContext ):
        
        self._tag_context = tag_context
        
        self.CollectValuesChanged()
        
    

class MediaSortControl( QW.QWidget ):
    
    sortChanged = QC.Signal( ClientMedia.MediaSort )
    
    def __init__( self, parent, media_sort = None ):
        
        super().__init__( parent )
        
        if media_sort is None:
            
            media_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
            
        
        self._tag_context = media_sort.tag_context
        
        self._sort_type = ( 'system', CC.SORT_FILES_BY_FILESIZE )
        
        self._sort_type_button = ClientGUICommon.BetterButton( self, 'sort', self._SortTypeButtonClick )
        self._sort_order_choice = ClientGUIMenuButton.MenuChoiceButton( self, [] )
        
        self._tag_gubbins_cog_icon_button = ClientGUIMenuButton.CogIconButton( self, [] )
        
        type_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._sort_type_button, 14 )
        
        self._sort_type_button.setMinimumWidth( type_width )
        
        asc_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._sort_order_choice, 14 )
        
        self._sort_order_choice.setMinimumWidth( asc_width )
        
        self._UpdateSortTypeLabel()
        self._UpdateAscDescLabelsAndDefault()
        
        #
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._sort_type_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._sort_order_choice, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._tag_gubbins_cog_icon_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        try:
            
            self.SetSort( media_sort )
            
        except Exception as e:
            
            default_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
            
            self.SetSort( default_sort )
            
        
        self._sort_order_choice.valueChanged.connect( self.EventSortAscChoice )
        
    
    def _BroadcastSort( self ):
        
        media_sort = self._GetCurrentSort()
        
        self.sortChanged.emit( media_sort )
        
    
    def _GetCurrentSort( self ) -> ClientMedia.MediaSort:
        
        sort_order = self._sort_order_choice.GetValue()
        
        if sort_order is None:
            
            sort_order = CC.SORT_ASC
            
        
        media_sort = ClientMedia.MediaSort( sort_type = self._sort_type, sort_order = sort_order, tag_context = self._tag_context )
        
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
                        
                        submenu = ClientGUIMenus.GenerateMenu( menu )
                        
                        submetatypes_to_menus[ submetatype ] = submenu
                        
                        ClientGUIMenus.AppendMenu( menu, submenu, submetatype )
                        
                    
                    menu_to_add_to = submetatypes_to_menus[ submetatype ]
                    
                
                label = CC.sort_type_basic_string_lookup[ system_sort_type ]
                
                menu_item = ClientGUIMenus.AppendMenuItem( menu_to_add_to, label, 'Select this sort type.', self._SetSortTypeFromUser, sort_type )
                
                menu_items_and_sort_types.append( ( menu_item, sort_type ) )
                
            
        
        default_namespace_sorts = CG.client_controller.new_options.GetDefaultNamespaceSorts()
        
        if menu is not None:
            
            submenu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'namespaces' )
            
        
        for namespace_sort in default_namespace_sorts:
            
            sort_type = namespace_sort.sort_type
            
            sort_types.append( sort_type )
            
            if menu is not None:
                
                example_sort = ClientMedia.MediaSort( sort_type, CC.SORT_ASC )
                
                label = example_sort.GetSortTypeString()
                
                menu_item = ClientGUIMenus.AppendMenuItem( submenu, label, 'Select this sort type.', self._SetSortTypeFromUser, sort_type )
                
                menu_items_and_sort_types.append( ( menu_item, sort_type ) )
                
            
        
        if menu is not None:
            
            ClientGUIMenus.AppendMenuItem( submenu, 'custom', 'Set a custom namespace sort', self._SetCustomNamespaceSortFromUser )
            
        
        rating_service_keys = CG.client_controller.services_manager.GetServiceKeys( HC.RATINGS_SERVICES )
        
        if len( rating_service_keys ) > 0:
            
            if menu is not None:
                
                submenu = ClientGUIMenus.GenerateMenu( menu )
                
                ClientGUIMenus.AppendMenu( menu, submenu, 'ratings' )
                
            
            for service_key in rating_service_keys:
                
                sort_type = ( 'rating', service_key )
                
                sort_types.append( sort_type )
                
                if menu is not None:
                    
                    example_sort = ClientMedia.MediaSort( sort_type, CC.SORT_ASC )
                    
                    label = example_sort.GetSortTypeString()
                    
                    menu_item = ClientGUIMenus.AppendMenuItem( submenu, label, 'Select this sort type.', self._SetSortTypeFromUser, sort_type )
                    
                    menu_items_and_sort_types.append( ( menu_item, sort_type ) )
                    
                
            
        
        if menu is not None:
            
            for ( menu_item, sort_choice ) in menu_items_and_sort_types:
                
                if sort_choice == self._sort_type:
                    
                    menu_item.setCheckable( True )
                    menu_item.setChecked( True )
                    
                
            
        
        return sort_types
        
    
    def _SetCustomNamespaceSortFromUser( self ):
        
        if self._sort_type[0] == 'namespaces':
            
            sort_data = self._sort_type[1]
            
        else:
            
            sort_data = ( [ 'series' ], ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
            
        
        try:
            
            sort_data = ClientGUITagsEditNamespaceSort.EditNamespaceSort( self, sort_data )
            
            sort_type = ( 'namespaces', sort_data )
            
            self._SetSortTypeFromUser( sort_type )
            
        except HydrusExceptions.VetoException:
            
            return
            
        
    
    def _SortTypeButtonClick( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        self._PopulateSortMenuOrList( menu = menu )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _SetSortType( self, sort_type ):
        
        self._sort_type = sort_type
        
        self._UpdateSortTypeLabel()
        self._UpdateCogIconButton()
        self._UpdateAscDescLabelsAndDefault()
        
    
    def _SetSortTypeFromUser( self, sort_type ):
        
        self._SetSortType( sort_type )
        
        self._UserChoseASort()
        
        self._BroadcastSort()
        
    
    def _UpdateAscDescLabelsAndDefault( self ):
        
        media_sort = self._GetCurrentSort()
        
        self._sort_order_choice.blockSignals( True )
        
        if media_sort.CanAsc():
            
            ( asc_str, desc_str, default_sort_order ) = media_sort.GetSortOrderStrings()
            
            choice_tuples = [
                ( asc_str, CC.SORT_ASC ),
                ( desc_str, CC.SORT_DESC )
            ]
            
            # if there are no changes to asc/desc texts, then we'll keep the previous value
            
            if choice_tuples != self._sort_order_choice.GetChoiceTuples():
                
                self._sort_order_choice.SetChoiceTuples( choice_tuples )
                
                self._sort_order_choice.SetValue( default_sort_order )
                
            
            self._sort_order_choice.setVisible( True )
            
        else:
            
            self._sort_order_choice.setVisible( False )
            #self._sort_order_choice.SetChoiceTuples( [] )
            
        
        self._sort_order_choice.blockSignals( False )
        
    
    def _UpdateCogIconButton( self ):
        
        ( sort_metatype, sort_data ) = self._sort_type
        
        menu_template_items = []
        
        we_are_namespaces = sort_metatype == 'namespaces'
        we_are_num_tags = sort_metatype == 'system' and sort_data == CC.SORT_FILES_BY_NUM_TAGS
        
        if we_are_namespaces or we_are_num_tags:
            
            self._tag_gubbins_cog_icon_button.setVisible( True )
            
            #
            
            services_manager = CG.client_controller.services_manager
            
            service_types_in_order = [ HC.LOCAL_TAG, HC.TAG_REPOSITORY, HC.COMBINED_TAG ]
            
            services = services_manager.GetServices( service_types_in_order )
            
            submenu_template_items = []
            
            last_seen_service_type = None
            
            # need this isolated for lambda scope stuff
            def get_check_manager_lambda_1( tc ):
                
                return lambda: tc == self._tag_context
                
            
            for service in services:
                
                if last_seen_service_type is not None and last_seen_service_type != service.GetServiceType():
                    
                    submenu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
                    
                
                new_tag_context = self._tag_context.Duplicate()
                
                new_tag_context.service_key = service.GetServiceKey()
                
                check_manager = ClientGUICommon.CheckboxManagerCalls(
                    HydrusData.Call( self.SetTagContext, new_tag_context ),
                    get_check_manager_lambda_1( new_tag_context )
                )
                
                submenu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( service.GetName(), 'Filter the namespaces by this tag domain.', check_manager ) )
                
                last_seen_service_type = service.GetServiceType()
                
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSubmenu( 'tag service', submenu_template_items ) )
            
            #
            
            if we_are_namespaces:
                
                ( namespaces, current_tag_display_type ) = sort_data
                
                tag_display_types = [
                    ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL,
                    ClientTags.TAG_DISPLAY_SELECTION_LIST,
                    ClientTags.TAG_DISPLAY_SINGLE_MEDIA
                ]
                
                # need this isolated for lambda scope stuff
                def get_check_manager_lambda_2( tdt ):
                    
                    return lambda: tdt == current_tag_display_type
                    
                
                submenu_template_items = []
                
                for tag_display_type in tag_display_types:
                    
                    check_manager = ClientGUICommon.CheckboxManagerCalls(
                        HydrusData.Call( self.SetTagDisplayType, tag_display_type ),
                        get_check_manager_lambda_2( tag_display_type )
                    )
                    
                    submenu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( ClientTags.tag_display_str_lookup[ tag_display_type ], 'Filter the namespaces by this tag display type.', check_manager ) )
                    
                
                menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSubmenu( 'ADVANCED: tag display type', submenu_template_items ) )
                
            
        else:
            
            self._tag_gubbins_cog_icon_button.setVisible( False )
            
        
        self._tag_gubbins_cog_icon_button.SetMenuItems( menu_template_items )
        
    
    def _UpdateSortTypeLabel( self ):
        
        example_sort = ClientMedia.MediaSort( self._sort_type, CC.SORT_ASC )
        
        self._sort_type_button.setText( example_sort.GetSortTypeString() )
        
        self._UpdateCogIconButton()
        
    
    def _UpdateToolTip( self ):
        
        media_sort = self._GetCurrentSort()
        
        # note we can't support this in 'all known files', but we don't make a song and dance about it here because it is advanced anyway
        if media_sort.CanSortAtDBLevel( ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ) ):
            
            tt = 'This sort type is simple enough that if your search has a "system:limit is n", the database will be able to select the nth tallest/smallest/whatever according to your sort.'
            
        else:
            
            tt = 'This sort type is too complicated to perform before media results are loaded, so if your search has a "system:limit is n", your n "limited" results will be sampled randomly.'
            
        
        wrapped_tt = ClientGUIFunctions.WrapToolTip( tt )
        
        self.setToolTip( wrapped_tt )
        self._sort_type_button.setToolTip( wrapped_tt )
        self._sort_order_choice.setToolTip( wrapped_tt )
        
    
    def _UserChoseASort( self ):
        
        if CG.client_controller.new_options.GetBoolean( 'save_page_sort_on_change' ):
            
            media_sort = self._GetCurrentSort()
            
            CG.client_controller.new_options.SetDefaultSort( media_sort )
            
        
        self._UpdateToolTip()
        
    
    def BroadcastSort( self ):
        
        self._BroadcastSort()
        
    
    def EventSortAscChoice( self ):
        
        self._UserChoseASort()
        
        self._BroadcastSort()
        
    
    def GetSort( self ) -> ClientMedia.MediaSort:
        
        return self._GetCurrentSort()
        
    
    def SetSort( self, media_sort: ClientMedia.MediaSort, do_sort = False ):
        
        self._SetSortType( media_sort.sort_type )
        
        # put this after 'asclabels', since we may transition from one-state to two-state
        self._sort_order_choice.SetValue( media_sort.sort_order )
        
        self._tag_context = media_sort.tag_context
        
        self._UpdateToolTip()
        
        if do_sort:
            
            self._BroadcastSort()
            
        
    
    def SetTagContext( self, tag_context: ClientSearchTagContext.TagContext ):
        
        self._tag_context = tag_context
        
        self._UserChoseASort()
        
        self._BroadcastSort()
        
    
    def SetTagDisplayType( self, tag_display_type: int ):
        
        ( sort_metatype, sort_data ) = self._sort_type
        
        if sort_metatype == 'namespaces':
            
            ( namespaces, current_tag_display_type ) = sort_data
            
            sort_data = ( namespaces, tag_display_type )
            
            self._SetSortType( ( sort_metatype, sort_data ) )
            
            self._UserChoseASort()
            
            self._BroadcastSort()
            
        
    
    def wheelEvent( self, event ):
        
        if CG.client_controller.new_options.GetBoolean( 'menu_choice_buttons_can_mouse_scroll' ):
            
            if self._sort_type_button.rect().contains( self._sort_type_button.mapFromGlobal( QG.QCursor.pos() ) ):
                
                if event.angleDelta().y() > 0:
                    
                    index_delta = -1
                    
                else:
                    
                    index_delta = 1
                    
                
                sort_types = self._PopulateSortMenuOrList()
                
                if self._sort_type in sort_types:
                    
                    index = sort_types.index( self._sort_type )
                    
                    new_index = ( index + index_delta ) % len( sort_types )
                    
                    new_sort_type = sort_types[ new_index ]
                    
                    self._SetSortTypeFromUser( new_sort_type )
                    
                
            
            event.accept()
            
        else:
            
            event.ignore()
            
        
    
