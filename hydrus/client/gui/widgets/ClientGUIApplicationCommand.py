from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.media import ClientMediaFileFilter

class LocalFilesSubPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent )
        
        self._add_or_move_action = ClientGUICommon.BetterChoice( self )
        
        self._add_or_move_action.addItem( 'add to', HC.CONTENT_UPDATE_ADD )
        self._add_or_move_action.addItem( 'move to (even if already in destination)', HC.CONTENT_UPDATE_MOVE_MERGE )
        self._add_or_move_action.addItem( 'move to (if not already in destination)', HC.CONTENT_UPDATE_MOVE )
        
        self._add_or_move_action.SetValue( HC.CONTENT_UPDATE_ADD )
        tt = 'A "move (if not already in destination)" is a strict move: it will not "move" files that are already in the destination; a "move (even if already in destination)" is a softer "merge": it will ensure everything ends up in the destination and then clears all items from the source.'
        self._add_or_move_action.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._service_keys = ClientGUICommon.BetterChoice( self )
        
        #
        
        services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_FILE_DOMAIN, ) )
        
        for service in services:
            
            service_name = service.GetName()
            service_key = service.GetServiceKey()
            
            self._service_keys.addItem( service_name, service_key )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        ratings_numerical_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( vbox, self._add_or_move_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._service_keys, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
    
    def GetValue( self ):
        
        service_key = self._service_keys.GetValue()
        
        if service_key is None:
            
            raise HydrusExceptions.VetoException( 'Please select a service!' )
            
        
        action = self._add_or_move_action.GetValue()
        
        value = None
        
        return CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_FILES, action, value ) )
        
    
    def SetValue( self, action: int, service_key: bytes ):
        
        self._add_or_move_action.SetValue( action )
        
        self._service_keys.SetValue( service_key )
        
    
class RatingLikeSubPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent )
        
        self._flip_or_set_action = ClientGUICommon.BetterChoice( self )
        
        self._flip_or_set_action.addItem( 'set', HC.CONTENT_UPDATE_SET )
        self._flip_or_set_action.addItem( 'flip on and off', HC.CONTENT_UPDATE_FLIP )
        
        self._flip_or_set_action.SetValue( HC.CONTENT_UPDATE_SET )
        
        self._service_keys = ClientGUICommon.BetterChoice( self )
        self._ratings_like_like = QW.QRadioButton( 'like', self )
        self._ratings_like_dislike = QW.QRadioButton( 'dislike', self )
        self._ratings_like_remove = QW.QRadioButton( 'remove rating', self )
        
        #
        
        services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ) )
        
        if len( services ) == 0:
            
            self._service_keys.addItem( 'you have no like/dislike rating services', None )
            
        else:
            
            for service in services:
                
                service_name = service.GetName()
                service_key = service.GetServiceKey()
                
                self._service_keys.addItem( service_name, service_key )
                
            
        
        self._ratings_like_like.setChecked( True )
        
        #
        
        vbox = QP.VBoxLayout()
        
        ratings_like_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( ratings_like_hbox, self._service_keys, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( ratings_like_hbox, self._ratings_like_like, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( ratings_like_hbox, self._ratings_like_dislike, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( ratings_like_hbox, self._ratings_like_remove, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._flip_or_set_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, ratings_like_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        self._ratings_like_remove.toggled.connect( self._UpdateFlipAllowed )
        
    
    def _UpdateFlipAllowed( self ):
        
        if self._ratings_like_remove.isChecked():
            
            self._flip_or_set_action.SetValue( HC.CONTENT_UPDATE_SET )
            self._flip_or_set_action.setEnabled( False )
            
        else:
            
            self._flip_or_set_action.setEnabled( True )
            
        
    
    def GetValue( self ):
        
        service_key = self._service_keys.GetValue()
        
        if service_key is None:
            
            raise HydrusExceptions.VetoException( 'Please select a rating service!' )
            
        
        action = self._flip_or_set_action.GetValue()
        
        if self._ratings_like_like.isChecked():
            
            value = 1.0
            
        elif self._ratings_like_dislike.isChecked():
            
            value = 0.0
            
        else:
            
            value = None
            
        
        return CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_RATINGS, action, value ) )
        
    
    def SetValue( self, action: int, service_key: bytes, rating: float | None ):
        
        self._flip_or_set_action.SetValue( action )
        
        self._service_keys.SetValue( service_key )
        
        self._ratings_like_remove.setChecked( rating is None )
        self._ratings_like_like.setChecked( rating == 1.0 )
        self._ratings_like_dislike.setChecked( rating == 0.0 )
        
    
class RatingNumericalSubPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent )
        
        self._current_ratings_numerical_service = None
        
        self._flip_or_set_action = ClientGUICommon.BetterChoice( self )
        
        self._flip_or_set_action.addItem( 'set', HC.CONTENT_UPDATE_SET )
        self._flip_or_set_action.addItem( 'flip on and off', HC.CONTENT_UPDATE_FLIP )
        
        self._flip_or_set_action.SetValue( HC.CONTENT_UPDATE_SET )
        
        self._service_keys = ClientGUICommon.BetterChoice( self )
        self._service_keys.currentIndexChanged.connect( self._UpdateSliderRange )
        self._ratings_numerical_slider = QP.LabelledSlider( self )
        self._ratings_numerical_remove = QW.QCheckBox( 'remove rating', self )
        
        #
        
        services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        if len( services ) == 0:
            
            self._service_keys.addItem( 'you have no numerical rating services', None )
            
        else:
            
            for service in services:
                
                service_name = service.GetName()
                service_key = service.GetServiceKey()
                
                self._service_keys.addItem( service_name, service_key )
                
            
        
        self._UpdateSliderRange()
        
        #
        
        vbox = QP.VBoxLayout()
        
        ratings_numerical_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( ratings_numerical_hbox, self._service_keys, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( ratings_numerical_hbox, self._ratings_numerical_slider, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( ratings_numerical_hbox, self._ratings_numerical_remove, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._flip_or_set_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, ratings_numerical_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        self._ratings_numerical_remove.toggled.connect( self._UpdateFlipAllowed )
        
    
    def _UpdateFlipAllowed( self ):
        
        remove_on = self._ratings_numerical_remove.isChecked()
        
        if remove_on:
            
            self._flip_or_set_action.SetValue( HC.CONTENT_UPDATE_SET )
            
        
        self._flip_or_set_action.setEnabled( not remove_on )
        self._ratings_numerical_slider.setEnabled( not remove_on )
        
    
    def _UpdateSliderRange( self ):
        
        service_key = self._service_keys.GetValue()
        
        if service_key is not None:
            
            service = CG.client_controller.services_manager.GetService( service_key )
            
            self._current_ratings_numerical_service = service
            
            num_stars = service.GetNumStars()
            
            allow_zero = service.AllowZero()
            
            if allow_zero:
                
                minimum = 0
                
            else:
                
                minimum = 1
                
            
            self._ratings_numerical_slider.SetRange( minimum, num_stars )
            
        
    
    def GetValue( self ):
        
        service_key = self._service_keys.GetValue()
        
        if service_key is None:
            
            raise HydrusExceptions.VetoException( 'Please select a rating service!' )
            
        
        action = self._flip_or_set_action.GetValue()
        
        if self._ratings_numerical_remove.isChecked():
            
            rating = None
            
        else:
            
            value = self._ratings_numerical_slider.GetValue()
            
            rating = self._current_ratings_numerical_service.ConvertStarsToRating( value )
            
        
        return CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_RATINGS, action, rating ) )
        
    
    def SetValue( self, action: int, service_key: bytes, rating: float | None ):
        
        self._flip_or_set_action.SetValue( action )
        
        self._service_keys.SetValue( service_key )
        
        self._UpdateSliderRange()
        
        if rating is None:
            
            self._ratings_numerical_remove.setChecked( True )
            
        else:
            
            slider_value = self._current_ratings_numerical_service.ConvertRatingToStars( rating )
            
            self._ratings_numerical_slider.SetValue( slider_value )
            
        
    

class RatingIncDecSubPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent )
        
        self._service_keys = ClientGUICommon.BetterChoice( self )
        
        self._ratings_incdec = ClientGUICommon.BetterChoice( self )
        
        self._ratings_incdec.addItem( HC.content_update_string_lookup[ HC.CONTENT_UPDATE_INCREMENT ], HC.CONTENT_UPDATE_INCREMENT )
        self._ratings_incdec.addItem( HC.content_update_string_lookup[ HC.CONTENT_UPDATE_DECREMENT ], HC.CONTENT_UPDATE_DECREMENT )
        
        #
        
        services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, HC.LOCAL_RATING_INCDEC ) )
        
        if len( services ) == 0:
            
            self._service_keys.addItem( 'you have no numerical or inc/dec rating services', None )
            
        else:
            
            for service in services:
                
                service_name = service.GetName()
                service_key = service.GetServiceKey()
                
                self._service_keys.addItem( service_name, service_key )
                
            
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._service_keys, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._ratings_incdec, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
    
    def GetValue( self ):
        
        service_key = self._service_keys.GetValue()
        
        if service_key is None:
            
            raise HydrusExceptions.VetoException( 'Please select a rating service!' )
            
        
        action = self._ratings_incdec.GetValue()
        
        distance = 1
        
        return CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_RATINGS, action, distance ) )
        
    
    def SetValue( self, action: int, service_key: bytes, distance: int ):
        
        self._service_keys.SetValue( service_key )
        
        self._ratings_incdec.SetValue( action )
        
    

file_command_target_actions = {
    CAC.SIMPLE_COPY_FILES,
    CAC.SIMPLE_COPY_FILE_PATHS,
    CAC.SIMPLE_COPY_FILE_ID,
    CAC.SIMPLE_COPY_FILE_HASHES,
    CAC.SIMPLE_COPY_FILE_SERVICE_FILENAMES
}

zoom_command_actions = {
    CAC.SIMPLE_ZOOM_TO_PERCENTAGE,
    CAC.SIMPLE_ZOOM_TO_PERCENTAGE_CENTER,
    CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED,
    CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED_VIEWER_CENTER
}

class SimpleSubPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget, shortcuts_name: str ):
        
        super().__init__( parent )
        
        if shortcuts_name in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES:
            
            simple_types = ClientGUIShortcuts.simple_shortcut_name_to_action_lookup[ shortcuts_name ]
            
        else:
            
            simple_types = ClientGUIShortcuts.simple_shortcut_name_to_action_lookup[ 'custom' ]
            
        
        choices = sorted( [ ( CAC.simple_enum_to_str_lookup[ simple_type ], simple_type ) for simple_type in simple_types ] )
        
        self._simple_actions = ClientGUICommon.BetterChoice( self )
        
        for ( display_string, data ) in choices:
            
            self._simple_actions.addItem( display_string, data )
            
        
        #
        
        self._duplicates_type_panel = QW.QWidget( self )
        
        choice_tuples = [ ( HC.duplicate_type_string_lookup[ t ], t ) for t in ( HC.DUPLICATE_MEMBER, HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_POTENTIAL ) ]
        
        self._duplicate_type = ClientGUICommon.BetterRadioBox( self._duplicates_type_panel, choice_tuples )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._duplicate_type, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._duplicates_type_panel.setLayout( vbox )
        
        #
        
        self._thumbnail_rearrange_panel = QW.QWidget( self )
        
        self._thumbnail_rearrange_type = ClientGUICommon.BetterChoice( self )
        
        for rearrange_type in [
            CAC.MOVE_HOME,
            CAC.MOVE_END,
            CAC.MOVE_LEFT,
            CAC.MOVE_RIGHT,
            CAC.MOVE_TO_FOCUS
        ]:
            
            self._thumbnail_rearrange_type.addItem( CAC.move_enum_to_str_lookup[ rearrange_type ], rearrange_type )
            
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._thumbnail_rearrange_type, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._thumbnail_rearrange_panel.setLayout( vbox )
        
        #
        
        self._seek_panel = QW.QWidget( self )
        
        choice_tuples = [
            ( 'back', -1 ),
            ( 'forwards', 1 )
        ]
        
        self._seek_direction = ClientGUICommon.BetterRadioBox( self._seek_panel, choice_tuples )
        
        self._seek_duration_s = ClientGUICommon.BetterSpinBox( self._seek_panel, max=3599, width = 60 )
        self._seek_duration_ms = ClientGUICommon.BetterSpinBox( self._seek_panel, max=999, width = 60 )
        
        self._seek_duration_s.setValue( 5 )
        self._seek_duration_ms.setValue( 0 )
        
        self._seek_duration_s.value() * 1000 + self._seek_duration_ms.value()
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._seek_direction, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( hbox, self._seek_duration_s, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self._seek_panel, label = 's' ), CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._seek_duration_ms, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self._seek_panel, label = 'ms' ), CC.FLAGS_CENTER )
        
        self._seek_panel.setLayout( hbox )
        
        #
        
        self._thumbnail_move_panel = QW.QWidget( self )
        
        choice_tuples = [ ( CAC.selection_status_enum_to_str_lookup[ s ], s ) for s in [ CAC.SELECTION_STATUS_NORMAL, CAC.SELECTION_STATUS_SHIFT ] ]
        
        self._selection_status = ClientGUICommon.BetterRadioBox( self._thumbnail_move_panel, choice_tuples )
        
        self._selection_status.SetValue( CAC.SELECTION_STATUS_NORMAL )
        
        self._move_direction = ClientGUICommon.BetterChoice( self._thumbnail_move_panel )
        
        for m in [ CAC.MOVE_LEFT, CAC.MOVE_RIGHT, CAC.MOVE_UP, CAC.MOVE_DOWN, CAC.MOVE_HOME, CAC.MOVE_END, CAC.MOVE_PAGE_UP, CAC.MOVE_PAGE_DOWN ]:
            
            self._move_direction.addItem( CAC.move_enum_to_str_lookup[ m ], m )
            
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._selection_status, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._move_direction, CC.FLAGS_CENTER )
        
        self._thumbnail_move_panel.setLayout( hbox )
        
        #
        
        self._file_filter_panel = QW.QWidget( self )
        
        self._file_filter = ClientGUICommon.BetterChoice( self._file_filter_panel )
        
        for file_filter in [
            ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_ALL ),
            ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_NONE ),
            ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_INBOX ),
            ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_ARCHIVE ),
            ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_NOT_SELECTED ),
            ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_LOCAL ),
            ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_FILE_SERVICE, filter_data = CC.TRASH_SERVICE_KEY )
        ]:
            
            self._file_filter.addItem( file_filter.ToString(), file_filter )
            
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._file_filter, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._file_filter_panel.setLayout( hbox )
        
        #
        
        self._hamming_distance_panel = QW.QWidget( self )
        
        self._hamming_distance = ClientGUICommon.BetterSpinBox( self._hamming_distance_panel, min = 0, max = 64 )
        
        rows = []
        
        rows.append( ( 'Search distance:', self._hamming_distance ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._hamming_distance_panel, rows )
        
        self._hamming_distance_panel.setLayout( gridbox )
        
        #
        
        self._file_command_target_panel = QW.QWidget( self )
        
        choice_tuples = [ ( CAC.file_command_target_enum_to_str_lookup[ file_command_target ], file_command_target ) for file_command_target in ( CAC.FILE_COMMAND_TARGET_SELECTED_FILES, CAC.FILE_COMMAND_TARGET_FOCUSED_FILE ) ]
        
        self._file_command_target = ClientGUICommon.BetterRadioBox( self._file_command_target_panel, choice_tuples )
        
        self._file_command_target.SetValue( CAC.FILE_COMMAND_TARGET_SELECTED_FILES )
        
        self._file_command_target.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is only important in the thumbnail view, where the "focused file" means the one currently in the preview view, usually the one you last clicked on. In the media viewer, actions are always applied to the current file.' ) )
        
        rows = []
        
        rows.append( ( 'Files to apply to:', self._file_command_target ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._file_command_target_panel, rows )
        
        self._file_command_target_panel.setLayout( gridbox )
        
        #
        
        self._bitmap_type_panel = QW.QWidget( self )
        
        self._bitmap_type = ClientGUICommon.BetterChoice( self._bitmap_type_panel )
        
        for bitmap_type in (
            CAC.BITMAP_TYPE_FULL,
            CAC.BITMAP_TYPE_SOURCE_LOOKUPS,
            CAC.BITMAP_TYPE_THUMBNAIL,
            CAC.BITMAP_TYPE_FULL_OR_FILE
        ):
            
            self._bitmap_type.addItem( CAC.bitmap_type_enum_to_str_lookup[ bitmap_type ], bitmap_type )
            
        
        self._bitmap_type.SetValue( CAC.BITMAP_TYPE_FULL )
        
        rows = []
        
        rows.append( ( 'Bitmap to copy:', self._bitmap_type ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._bitmap_type_panel, rows )
        
        self._bitmap_type_panel.setLayout( gridbox )
        
        #
        
        self._hash_type_panel = QW.QWidget( self )
        
        self._hash_type = ClientGUICommon.BetterChoice( self._hash_type_panel )
        
        for hash_type in (
            'sha256',
            'md5',
            'sha1',
            'sha512',
            'blurhash',
            'pixel_hash'
        ):
            
            self._hash_type.addItem( hash_type, hash_type )
            
        
        self._hash_type.SetValue( 'sha256' )
        
        rows = []
        
        rows.append( ( 'Hash type to copy:', self._hash_type ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._hash_type_panel, rows )
        
        self._hash_type_panel.setLayout( gridbox )
        
        #
        
        self._ipfs_service_panel = QW.QWidget( self )
        
        self._ipfs_service_key = ClientGUICommon.BetterChoice( self._ipfs_service_panel )
        
        for service in CG.client_controller.services_manager.GetServices( ( HC.IPFS, ) ):
            
            name = service.GetName()
            service_key = service.GetServiceKey()
            
            self._ipfs_service_key.addItem( name, service_key )
            
        
        rows = []
        
        rows.append( ( 'Service to copy:', self._ipfs_service_key ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._ipfs_service_panel, rows )
        
        self._ipfs_service_panel.setLayout( gridbox )
        
        #
        
        self._zoom_panel = QW.QWidget( self )
        
        self._zoom_value = ClientGUICommon.BetterSpinBox( self._zoom_panel, initial = 100, min = 1, max = 1600 )
        
        rows = []
        
        rows.append( ( 'Zoom %:', self._zoom_value ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._zoom_panel, rows )
        
        self._zoom_panel.setLayout( gridbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._simple_actions, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._duplicates_type_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._seek_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._thumbnail_move_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._file_filter_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._hamming_distance_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._thumbnail_rearrange_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._file_command_target_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._bitmap_type_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._hash_type_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._ipfs_service_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._zoom_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._simple_actions.currentIndexChanged.connect( self._UpdateControls )
        
        self._UpdateControls()
        
    
    def _UpdateControls( self ):
        
        action = self._simple_actions.GetValue()
        
        self._thumbnail_rearrange_panel.setVisible( action == CAC.SIMPLE_REARRANGE_THUMBNAILS )
        self._duplicates_type_panel.setVisible( action == CAC.SIMPLE_SHOW_DUPLICATES )
        self._seek_panel.setVisible( action == CAC.SIMPLE_MEDIA_SEEK_DELTA )
        self._thumbnail_move_panel.setVisible( action == CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS )
        self._file_filter_panel.setVisible( action == CAC.SIMPLE_SELECT_FILES )
        self._hamming_distance_panel.setVisible( action == CAC.SIMPLE_OPEN_SIMILAR_LOOKING_FILES )
        self._hash_type_panel.setVisible( action == CAC.SIMPLE_COPY_FILE_HASHES )
        self._ipfs_service_panel.setVisible( action == CAC.SIMPLE_COPY_FILE_SERVICE_FILENAMES )
        self._bitmap_type_panel.setVisible( action == CAC.SIMPLE_COPY_FILE_BITMAP )
        
        self._zoom_panel.setVisible( action in zoom_command_actions )
        self._file_command_target_panel.setVisible( action in file_command_target_actions )
        
    
    def GetValue( self ):
        
        action = self._simple_actions.GetValue()
        
        if action == '':
            
            raise HydrusExceptions.VetoException( 'Please select an action!' )
            
        else:
            
            if action == CAC.SIMPLE_SHOW_DUPLICATES:
                
                duplicate_type = self._duplicate_type.GetValue()
                
                simple_data = duplicate_type
                
            elif action == CAC.SIMPLE_MEDIA_SEEK_DELTA:
                
                direction = self._seek_direction.GetValue()
                
                s = self._seek_duration_s.value()
                ms = self._seek_duration_ms.value() + ( 1000 * s )
                
                simple_data = ( direction, ms )
                
            elif action == CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS:
                
                move_direction = self._move_direction.GetValue()
                selection_status = self._selection_status.GetValue()
                
                simple_data = ( move_direction, selection_status )
                
            elif action == CAC.SIMPLE_SELECT_FILES:
                
                file_filter = self._file_filter.GetValue()
                
                simple_data = file_filter
                
            elif action == CAC.SIMPLE_OPEN_SIMILAR_LOOKING_FILES:
                
                hamming_distance = self._hamming_distance.value()
                
                simple_data = hamming_distance
                
            elif action == CAC.SIMPLE_REARRANGE_THUMBNAILS:
                
                rearrange_type = self._thumbnail_rearrange_type.GetValue()
                
                simple_data = ( CAC.REARRANGE_THUMBNAILS_TYPE_COMMAND, rearrange_type )
                
            elif action in ( CAC.SIMPLE_COPY_FILES, CAC.SIMPLE_COPY_FILE_PATHS, CAC.SIMPLE_COPY_FILE_ID ):
                
                file_command_target = self._file_command_target.GetValue()
                
                simple_data = file_command_target
                
            elif action == CAC.SIMPLE_COPY_FILE_BITMAP:
                
                bitmap_type = self._bitmap_type.GetValue()
                
                simple_data = bitmap_type
                
            elif action == CAC.SIMPLE_COPY_FILE_HASHES:
                
                file_command_target = self._file_command_target.GetValue()
                hash_type = self._hash_type.GetValue()
                
                simple_data = ( file_command_target, hash_type )
                
            elif action == CAC.SIMPLE_COPY_FILE_SERVICE_FILENAMES:
                
                file_command_target = self._file_command_target.GetValue()
                ipfs_service_key = self._ipfs_service_key.GetValue()
                
                hacky_ipfs_dict = HydrusSerialisable.SerialisableDictionary()
                
                hacky_ipfs_dict[ 'file_command_target' ] = file_command_target
                hacky_ipfs_dict[ 'ipfs_service_key' ] = ipfs_service_key
                
                simple_data = hacky_ipfs_dict
                
            elif action in zoom_command_actions:
                
                zoom_value_integer = self._zoom_value.value()
                
                zoom_value_decimal = zoom_value_integer / 100
                
                simple_data = zoom_value_decimal
                
            else:
                
                simple_data = None
                
            
            return CAC.ApplicationCommand.STATICCreateSimpleCommand( action, simple_data = simple_data )
            
        
    
    def SetValue( self, command: CAC.ApplicationCommand ):
        
        action = command.GetSimpleAction()
        
        self._simple_actions.SetValue( action )
        
        if action == CAC.SIMPLE_SHOW_DUPLICATES:
            
            duplicate_type = command.GetSimpleData()
            
            self._duplicate_type.SetValue( duplicate_type )
            
        elif action == CAC.SIMPLE_MEDIA_SEEK_DELTA:
            
            ( direction, ms ) = command.GetSimpleData()
            
            self._seek_direction.SetValue( direction )
            
            s = ms // 1000
            
            ms = ms % 1000
            
            self._seek_duration_s.setValue( s )
            self._seek_duration_ms.setValue( ms )
            
        elif action == CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS:
            
            ( move_direction, selection_status ) = command.GetSimpleData()
            
            self._move_direction.SetValue( move_direction )
            self._selection_status.SetValue( selection_status )
            
        elif action == CAC.SIMPLE_SELECT_FILES:
            
            file_filter = command.GetSimpleData()
            
            self._file_filter.SetValue( file_filter )
            
        elif action == CAC.SIMPLE_OPEN_SIMILAR_LOOKING_FILES:
            
            hamming_distance = command.GetSimpleData()
            
            self._hamming_distance.setValue( hamming_distance )
            
        elif action == CAC.SIMPLE_REARRANGE_THUMBNAILS:
            
            ( rearrange_type, rearrange_data ) = command.GetSimpleData()
            
            self._thumbnail_rearrange_type.SetValue( rearrange_data )
            
        elif action in ( CAC.SIMPLE_COPY_FILES, CAC.SIMPLE_COPY_FILE_PATHS, CAC.SIMPLE_COPY_FILE_ID ):
            
            file_command_target = command.GetSimpleData()
            
            self._file_command_target.SetValue( file_command_target )
            
        elif action == CAC.SIMPLE_COPY_FILE_BITMAP:
            
            bitmap_type = command.GetSimpleData()
            
            self._bitmap_type.SetValue( bitmap_type )
            
        elif action == CAC.SIMPLE_COPY_FILE_HASHES:
            
            ( file_command_target, hash_type ) = command.GetSimpleData()
            
            self._file_command_target.SetValue( file_command_target )
            self._hash_type.SetValue( hash_type )
            
        elif action == CAC.SIMPLE_COPY_FILE_SERVICE_FILENAMES:
            
            hacky_ipfs_dict = command.GetSimpleData()
            
            self._file_command_target.SetValue( hacky_ipfs_dict[ 'file_command_target' ] )
            self._ipfs_service_key.SetValue( hacky_ipfs_dict[ 'ipfs_service_key' ] )
            
        elif action in zoom_command_actions:
            
            zoom_value_decimal = command.GetSimpleData()
            
            if zoom_value_decimal is None:
                
                zoom_value_decimal = 1.0
                
            
            zoom_value_integer = int( zoom_value_decimal * 100 )
            
            self._zoom_value.setValue( zoom_value_integer )
            
        
        self._UpdateControls()
        
    

class TagSubPanel( QW.QWidget ):
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent )
        
        self._flip_or_set_action = ClientGUICommon.BetterChoice( self )
        
        self._flip_or_set_action.addItem( 'set', HC.CONTENT_UPDATE_SET )
        self._flip_or_set_action.addItem( 'flip on and off', HC.CONTENT_UPDATE_FLIP )
        
        self._flip_or_set_action.SetValue( HC.CONTENT_UPDATE_SET )
        
        self._service_keys = ClientGUICommon.BetterChoice( self )
        
        self._tag_value = QW.QLineEdit( self )
        self._tag_value.setReadOnly( True )
        
        default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
        
        self._tag_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.SetTags, default_location_context, CC.COMBINED_TAG_SERVICE_KEY )
        
        #
        
        services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ) )
        
        for service in services:
            
            service_name = service.GetName()
            service_key = service.GetServiceKey()
            
            self._service_keys.addItem( service_name, service_key )
            
        
        self._tag_input.SetTagServiceKey( self._service_keys.GetValue() )
        
        #
        
        vbox = QP.VBoxLayout()
        
        tag_sub_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( tag_sub_vbox, self._tag_value, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( tag_sub_vbox, self._tag_input, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        tag_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( tag_hbox, self._service_keys, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( tag_hbox, tag_sub_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        QP.AddToLayout( vbox, self._flip_or_set_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, tag_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        #
        
        self._service_keys.currentIndexChanged.connect( self._NewServiceKey )
        
    
    def _NewServiceKey( self ):
        
        self._tag_input.SetTagServiceKey( self._service_keys.GetValue() )
        
    
    def GetValue( self ):
        
        service_key = self._service_keys.GetValue()
        
        if service_key is None:
            
            raise HydrusExceptions.VetoException( 'Please select a tag service!' )
            
        
        action = self._flip_or_set_action.GetValue()
        
        tag = self._tag_value.text()
        
        if tag == '':
            
            raise HydrusExceptions.VetoException( 'Please enter a tag!' )
            
        
        return CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_MAPPINGS, action, tag ) )
        
    
    def SetTags( self, tags ):
        
        if len( tags ) > 0:
            
            tag = list( tags )[0]
            
            self._tag_value.setText( tag )
            
        
    
    def SetValue( self, action: int, service_key: bytes, tag: str ):
        
        self._flip_or_set_action.SetValue( action )
        
        self._service_keys.SetValue( service_key )
        
        self._tag_value.setText( tag )
        
    

class ApplicationCommandWidget( ClientGUIScrolledPanels.EditPanel ):
    
    PANEL_SIMPLE = 0
    PANEL_TAG = 1
    PANEL_RATING_LIKE = 2
    PANEL_RATING_NUMERICAL = 3
    PANEL_RATING_INCDEC = 4
    PANEL_LOCAL_FILES = 5
    
    def __init__( self, parent: QW.QWidget, command: CAC.ApplicationCommand, shortcuts_name: str ):
        
        super().__init__( parent )
        
        #
        
        is_custom_or_media = shortcuts_name not in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES or shortcuts_name == 'media'
        
        self._panel_choice = ClientGUICommon.BetterChoice( self )
        
        self._panel_choice.addItem( 'simple command', self.PANEL_SIMPLE )
        
        if is_custom_or_media:
            
            self._panel_choice.addItem( 'tag command', self.PANEL_TAG )
            self._panel_choice.addItem( 'local file command', self.PANEL_LOCAL_FILES )
            self._panel_choice.addItem( 'like/dislike rating command', self.PANEL_RATING_LIKE )
            self._panel_choice.addItem( 'numerical rating command', self.PANEL_RATING_NUMERICAL )
            self._panel_choice.addItem( 'rating increment/decrement command', self.PANEL_RATING_INCDEC )
            
        else:
            
            self._panel_choice.hide()
            
        
        self._simple_sub_panel = SimpleSubPanel( self, shortcuts_name )
        
        self._tag_sub_panel = TagSubPanel( self )
        
        self._rating_like_sub_panel = RatingLikeSubPanel( self )
        
        self._rating_numerical_sub_panel = RatingNumericalSubPanel( self )
        
        self._rating_inc_dec_sub_panel = RatingIncDecSubPanel( self )
        
        self._local_files_sub_panel = LocalFilesSubPanel( self )
        
        #
        
        if command.IsSimpleCommand():
            
            self._simple_sub_panel.SetValue( command )
            
            self._panel_choice.SetValue( self.PANEL_SIMPLE )
            
        elif command.IsContentCommand():
            
            service_key = command.GetContentServiceKey()
            
            if CG.client_controller.services_manager.ServiceExists( service_key ):
                
                service = CG.client_controller.services_manager.GetService( service_key )
                
                action = command.GetContentAction()
                value = command.GetContentValue()
                
            else:
                
                ClientGUIDialogsMessage.ShowWarning( self, 'The service that this command relies upon no longer exists! This command will reset to a default form.' )
                
                local_tag_services = list( CG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) ) )
                
                service = local_tag_services[0]
                
                service_key = service.GetServiceKey()
                action = HC.CONTENT_UPDATE_SET
                value = 'tag'
                
            
            service_type = service.GetServiceType()
            
            if service_type in HC.REAL_TAG_SERVICES:
                
                tag = value
                
                self._tag_sub_panel.SetValue( action, service_key, tag )
                
                self._panel_choice.SetValue( self.PANEL_TAG )
                
            elif service_type == HC.LOCAL_FILE_DOMAIN:
                
                self._local_files_sub_panel.SetValue( action, service_key )
                
                self._panel_choice.SetValue( self.PANEL_LOCAL_FILES )
                
            elif service_type == HC.LOCAL_RATING_LIKE:
                
                rating = value
                
                self._rating_like_sub_panel.SetValue( action, service_key, rating )
                
                self._panel_choice.SetValue( self.PANEL_RATING_LIKE )
                
            elif service_type in ( HC.LOCAL_RATING_NUMERICAL, HC.LOCAL_RATING_INCDEC ):
                
                if action in ( HC.CONTENT_UPDATE_SET, HC.CONTENT_UPDATE_FLIP ):
                    
                    rating = value
                    
                    self._rating_numerical_sub_panel.SetValue( action, service_key, rating )
                    
                    self._panel_choice.SetValue( self.PANEL_RATING_NUMERICAL )
                    
                elif action in ( HC.CONTENT_UPDATE_INCREMENT, HC.CONTENT_UPDATE_DECREMENT ):
                    
                    distance = 1
                    
                    self._rating_inc_dec_sub_panel.SetValue( action, service_key, distance )
                    
                    self._panel_choice.SetValue( self.PANEL_RATING_INCDEC )
                    
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._panel_choice, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._simple_sub_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tag_sub_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._local_files_sub_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._rating_like_sub_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._rating_numerical_sub_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._rating_inc_dec_sub_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        self._UpdateVisibleControls()
        
        #
        
        self._panel_choice.currentIndexChanged.connect( self._UpdateVisibleControls )
        
    
    def _UpdateVisibleControls( self ):
        
        panel_type = self._panel_choice.GetValue()
        
        self._simple_sub_panel.setVisible( panel_type == self.PANEL_SIMPLE )
        self._tag_sub_panel.setVisible( panel_type == self.PANEL_TAG )
        self._local_files_sub_panel.setVisible( panel_type == self.PANEL_LOCAL_FILES )
        self._rating_like_sub_panel.setVisible( panel_type == self.PANEL_RATING_LIKE )
        self._rating_numerical_sub_panel.setVisible( panel_type == self.PANEL_RATING_NUMERICAL )
        self._rating_inc_dec_sub_panel.setVisible( panel_type == self.PANEL_RATING_INCDEC )
        
    
    def GetValue( self ):
        
        panel_type = self._panel_choice.GetValue()
        
        if panel_type == self.PANEL_SIMPLE:
            
            return self._simple_sub_panel.GetValue()
            
        elif panel_type == self.PANEL_TAG:
            
            return self._tag_sub_panel.GetValue()
            
        elif panel_type == self.PANEL_LOCAL_FILES:
            
            return self._local_files_sub_panel.GetValue()
            
        elif panel_type == self.PANEL_RATING_LIKE:
            
            return self._rating_like_sub_panel.GetValue()
            
        elif panel_type == self.PANEL_RATING_NUMERICAL:
            
            return self._rating_numerical_sub_panel.GetValue()
            
        elif panel_type == self.PANEL_RATING_INCDEC:
            
            return self._rating_inc_dec_sub_panel.GetValue()
            
        
    
