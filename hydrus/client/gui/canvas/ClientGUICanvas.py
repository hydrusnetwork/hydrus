import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusImageHandling
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTags

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientDuplicates
from hydrus.client import ClientLocation
from hydrus.client import ClientPaths
from hydrus.client import ClientSearch
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsManage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMedia
from hydrus.client.gui import ClientGUIMediaActions
from hydrus.client.gui import ClientGUIMediaControls
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIRatings
from hydrus.client.gui import ClientGUIScrolledPanelsEdit
from hydrus.client.gui import ClientGUIScrolledPanelsManagement
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITags
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvasHoverFrames
from hydrus.client.gui.canvas import ClientGUICanvasMedia
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientRatings
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientTagSorting
from hydrus.client.gui.widgets import ClientGUICommon

ZOOM_CENTERPOINT_MEDIA_CENTER = 0
ZOOM_CENTERPOINT_VIEWER_CENTER = 1
ZOOM_CENTERPOINT_MOUSE = 2
ZOOM_CENTERPOINT_MEDIA_TOP_LEFT = 3

ZOOM_CENTERPOINT_TYPES = ( ZOOM_CENTERPOINT_VIEWER_CENTER, ZOOM_CENTERPOINT_MOUSE, ZOOM_CENTERPOINT_MEDIA_CENTER, ZOOM_CENTERPOINT_MEDIA_TOP_LEFT )

zoom_centerpoints_str_lookup = {}

zoom_centerpoints_str_lookup[ ZOOM_CENTERPOINT_MEDIA_CENTER ] = 'media center'
zoom_centerpoints_str_lookup[ ZOOM_CENTERPOINT_VIEWER_CENTER ] = 'viewer center'
zoom_centerpoints_str_lookup[ ZOOM_CENTERPOINT_MOUSE ] = 'mouse (or viewer center if mouse outside)'
zoom_centerpoints_str_lookup[ ZOOM_CENTERPOINT_MEDIA_TOP_LEFT ] = 'media top-left'

OPEN_EXTERNALLY_BUTTON_SIZE = ( 200, 45 )

def AddAudioVolumeMenu( menu, canvas_type ):
    
    mute_volume_type = None
    volume_volume_type = ClientGUIMediaControls.AUDIO_GLOBAL
    
    if canvas_type == CC.CANVAS_MEDIA_VIEWER:
        
        mute_volume_type = ClientGUIMediaControls.AUDIO_MEDIA_VIEWER
        
        if HG.client_controller.new_options.GetBoolean( 'media_viewer_uses_its_own_audio_volume' ):
            
            volume_volume_type = ClientGUIMediaControls.AUDIO_MEDIA_VIEWER
            
        
    elif canvas_type == CC.CANVAS_PREVIEW:
        
        mute_volume_type = ClientGUIMediaControls.AUDIO_PREVIEW
        
        if HG.client_controller.new_options.GetBoolean( 'preview_uses_its_own_audio_volume' ):
            
            volume_volume_type = ClientGUIMediaControls.AUDIO_PREVIEW
            
        
    
    volume_menu = QW.QMenu( menu )
    
    ( global_mute_option_name, global_volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ ClientGUIMediaControls.AUDIO_GLOBAL ]
    
    if HG.client_controller.new_options.GetBoolean( global_mute_option_name ):
        
        label = 'unmute global'
        
    else:
        
        label = 'mute global'
        
    
    ClientGUIMenus.AppendMenuItem( volume_menu, label, 'Mute/unmute audio.', ClientGUIMediaControls.FlipMute, ClientGUIMediaControls.AUDIO_GLOBAL )
    
    #
    
    if mute_volume_type is not None:
        
        ClientGUIMenus.AppendSeparator( volume_menu )
        
        ( mute_option_name, volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ mute_volume_type ]
        
        if HG.client_controller.new_options.GetBoolean( mute_option_name ):
            
            label = 'unmute {}'.format( ClientGUIMediaControls.volume_types_str_lookup[ mute_volume_type ] )
            
        else:
            
            label = 'mute {}'.format( ClientGUIMediaControls.volume_types_str_lookup[ mute_volume_type ] )
            
        
        ClientGUIMenus.AppendMenuItem( volume_menu, label, 'Mute/unmute audio.', ClientGUIMediaControls.FlipMute, mute_volume_type )
        
    
    #
    
    ClientGUIMenus.AppendSeparator( volume_menu )
    
    ( mute_option_name, volume_option_name ) = ClientGUIMediaControls.volume_types_to_option_names[ volume_volume_type ]
    
    # 0-100 inclusive
    volumes = list( range( 0, 110, 10 ) )
    
    current_volume = HG.client_controller.new_options.GetInteger( volume_option_name )
    
    if current_volume not in volumes:
        
        volumes.append( current_volume )
        
        volumes.sort()
        
    
    for volume in volumes:
        
        label = 'volume: {}'.format( volume )
        
        if volume == current_volume:
            
            ClientGUIMenus.AppendMenuCheckItem( volume_menu, label, 'Set the volume.', True, ClientGUIMediaControls.ChangeVolume, volume_volume_type, volume )
            
        else:
            
            ClientGUIMenus.AppendMenuItem( volume_menu, label, 'Set the volume.', ClientGUIMediaControls.ChangeVolume, volume_volume_type, volume )
            
        
    
    ClientGUIMenus.AppendMenu( menu, volume_menu, 'volume' )
    
def CalculateCanvasMediaSize( media, canvas_size: QC.QSize, show_action ):
    
    canvas_width = canvas_size.width()
    canvas_height = canvas_size.height()
    
    if ClientGUICanvasMedia.ShouldHaveAnimationBar( media, show_action ):
        
        animated_scanbar_height = HG.client_controller.new_options.GetInteger( 'animated_scanbar_height' )
        animated_scanbar_height = 0
        canvas_height -= animated_scanbar_height
        
    
    canvas_width = max( canvas_width, 80 )
    canvas_height = max( canvas_height, 60 )
    
    return ( canvas_width, canvas_height )
    
def CalculateCanvasZooms( canvas, media, show_action ):
    
    if media is None:
        
        return ( 1.0, 1.0 )
        
    
    if show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
        
        return ( 1.0, 1.0 )
        
    
    ( media_width, media_height ) = CalculateMediaSize( media, 1.0 )
    
    if media_width == 0 or media_height == 0:
        
        return ( 1.0, 1.0 )
        
    
    new_options = HG.client_controller.new_options
    
    ( canvas_width, canvas_height ) = CalculateCanvasMediaSize( media, canvas.size(), show_action )
    
    width_zoom = canvas_width / media_width
    
    height_zoom = canvas_height / media_height
    
    canvas_zoom = min( ( width_zoom, height_zoom ) )
    
    #
    
    mime = media.GetMime()
    
    ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) = new_options.GetMediaZoomOptions( mime )
    
    if exact_zooms_only:
        
        max_regular_zoom = 1.0
        
        if canvas_zoom > 1.0:
            
            while max_regular_zoom * 2 < canvas_zoom:
                
                max_regular_zoom *= 2
                
            
        elif canvas_zoom < 1.0:
            
            while max_regular_zoom > canvas_zoom:
                
                max_regular_zoom /= 2
                
            
        
    else:
        
        regular_zooms = new_options.GetMediaZooms()
        
        valid_regular_zooms = [ zoom for zoom in regular_zooms if zoom < canvas_zoom ]
        
        if len( valid_regular_zooms ) > 0:
            
            max_regular_zoom = max( valid_regular_zooms )
            
        else:
            
            max_regular_zoom = canvas_zoom
            
        
    
    if media.GetMime() in HC.AUDIO:
        
        scale_up_action = CC.MEDIA_VIEWER_SCALE_100
        scale_down_action = CC.MEDIA_VIEWER_SCALE_TO_CANVAS
        
    elif canvas.PREVIEW_WINDOW:
        
        scale_up_action = preview_scale_up
        scale_down_action = preview_scale_down
        
    else:
        
        scale_up_action = media_scale_up
        scale_down_action = media_scale_down
        
    
    can_be_scaled_down = media_width > canvas_width or media_height > canvas_height
    can_be_scaled_up = media_width < canvas_width and media_height < canvas_height
    
    #
    
    if can_be_scaled_up:
        
        scale_action = scale_up_action
        
    elif can_be_scaled_down:
        
        scale_action = scale_down_action
        
    else:
        
        scale_action = CC.MEDIA_VIEWER_SCALE_100
        
    
    if scale_action == CC.MEDIA_VIEWER_SCALE_100:
        
        default_zoom = 1.0
        
    elif scale_action == CC.MEDIA_VIEWER_SCALE_MAX_REGULAR:
        
        default_zoom = max_regular_zoom
        
    else:
        
        default_zoom = canvas_zoom
        
    
    return ( default_zoom, canvas_zoom )
    
def CalculateMediaContainerSize( media, zoom, show_action ):
    
    if show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
        
        raise Exception( 'This media should not be shown in the media viewer!' )
        
    elif show_action == CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON:
        
        ( width, height ) = OPEN_EXTERNALLY_BUTTON_SIZE
        
        if media.GetMime() in HC.MIMES_WITH_THUMBNAILS:
            
            bounding_dimensions = HG.client_controller.options[ 'thumbnail_dimensions' ]
            thumbnail_scale_type = HG.client_controller.new_options.GetInteger( 'thumbnail_scale_type' )
            
            ( clip_rect, ( thumb_width, thumb_height ) ) = HydrusImageHandling.GetThumbnailResolutionAndClipRegion( media.GetResolution(), bounding_dimensions, thumbnail_scale_type )
            
            height = height + thumb_height
            
        
        return QC.QSize( width, height )
        
    else:
        
        ( media_width, media_height ) = CalculateMediaSize( media, zoom )
        
        if ClientGUICanvasMedia.ShouldHaveAnimationBar( media, show_action ):
            
            animated_scanbar_height = HG.client_controller.new_options.GetInteger( 'animated_scanbar_height' )
            animated_scanbar_height = 0
            media_height += animated_scanbar_height
            
        
        return QC.QSize( media_width, media_height )
        
    
def CalculateMediaSize( media, zoom ):
    
    if media.GetMime() in HC.AUDIO:
        
        ( original_width, original_height ) = ( 360, 240 )
        
    else:
        
        ( original_width, original_height ) = media.GetResolution()
        
    
    media_width = int( round( zoom * original_width ) )
    media_height = int( round( zoom * original_height ) )
    
    media_width = max( 1, media_width )
    media_height = max( 1, media_height )
    
    return ( media_width, media_height )
    
class Canvas( QW.QWidget ):
    
    PREVIEW_WINDOW = False
    CANVAS_TYPE = CC.CANVAS_MEDIA_VIEWER
    
    def __init__( self, parent, location_context: ClientLocation.LocationContext ):
        
        QW.QWidget.__init__( self, parent )
        
        self.setSizePolicy( QW.QSizePolicy.Expanding, QW.QSizePolicy.Expanding )
        
        self._location_context = location_context
        
        self._current_media_start_time = HydrusData.GetNow()
        
        self._new_options = HG.client_controller.new_options
        
        self._canvas_key = HydrusData.GenerateKey()
        
        self._maintain_pan_and_zoom = False
        
        self._service_keys_to_services = {}
        
        self._current_media = None
        
        catch_mouse = True
        
        # once we have catch_mouse full shortcut support for canvases, swap out this out for an option to swallow activating clicks
        ignore_activating_mouse_click = catch_mouse and not self.PREVIEW_WINDOW
        
        self._my_shortcuts_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'media', 'media_viewer' ], catch_mouse = catch_mouse, ignore_activating_mouse_click = ignore_activating_mouse_click )
        
        self._click_drag_reporting_filter = MediaContainerDragClickReportingFilter( self )
        
        self.installEventFilter( self._click_drag_reporting_filter )
        
        self._media_container = ClientGUICanvasMedia.MediaContainer( self, self.CANVAS_TYPE, self._click_drag_reporting_filter )
        
        self._current_zoom = 1.0
        self._canvas_zoom = 1.0
        
        self._last_drag_pos = None
        self._current_drag_is_touch = False
        self._last_motion_pos = QC.QPoint( 0, 0 )
        self._media_window_pos = QC.QPoint( 0, 0 )
        
        self._UpdateBackgroundColour()
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
        self._media_container.readyForNeighbourPrefetch.connect( self._PrefetchNeighbours )
        
        HG.client_controller.sub( self, 'ZoomIn', 'canvas_zoom_in' )
        HG.client_controller.sub( self, 'ZoomOut', 'canvas_zoom_out' )
        HG.client_controller.sub( self, 'ZoomSwitch', 'canvas_zoom_switch' )
        HG.client_controller.sub( self, 'OpenExternally', 'canvas_open_externally' )
        HG.client_controller.sub( self, 'ManageNotes', 'canvas_manage_notes' )
        HG.client_controller.sub( self, 'ManageTags', 'canvas_manage_tags' )
        HG.client_controller.sub( self, 'ProcessApplicationCommand', 'canvas_application_command' )
        HG.client_controller.sub( self, '_UpdateBackgroundColour', 'notify_new_colourset' )
        HG.client_controller.sub( self, 'update', 'notify_new_colourset' )
        
    
    def _Archive( self ):
        
        if self._current_media is not None:
            
            HG.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, ( self._current_media.GetHash(), ) ) ] } )
            
        
    
    def _CanDisplayMedia( self, media ):
        
        if media is None:
            
            return True
            
        
        media = media.GetDisplayMedia()
        
        if media is None:
            
            return True
            
        
        locations_manager = media.GetLocationsManager()
        
        if not locations_manager.IsLocal():
            
            return False
            
        
        ( media_show_action, media_start_paused, media_start_with_embed ) = self._GetShowAction( media )
        
        if media_show_action in ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW ):
            
            return False
            
        
        return True
        
    
    def _CopyBMPToClipboard( self ):
        
        copied = False
        
        if self._current_media is not None:
            
            if self._current_media.GetMime() in HC.IMAGES:
                
                HG.client_controller.pub( 'clipboard', 'bmp', self._current_media )
                
                copied = True
                
            
        
        return copied
        
    
    def _CopyHashToClipboard( self, hash_type ):
        
        if self._current_media is None:
            
            return
            
        
        ClientGUIMedia.CopyHashesToClipboard( self, hash_type, [ self._current_media ] )
        
    
    def _CopyFileToClipboard( self ):
        
        if self._current_media is not None:
            
            client_files_manager = HG.client_controller.client_files_manager
            
            paths = [ client_files_manager.GetFilePath( self._current_media.GetHash(), self._current_media.GetMime() ) ]
            
            HG.client_controller.pub( 'clipboard', 'paths', paths )
            
        
    
    def _CopyPathToClipboard( self ):
        
        if self._current_media is not None:
            
            client_files_manager = HG.client_controller.client_files_manager
            
            path = client_files_manager.GetFilePath( self._current_media.GetHash(), self._current_media.GetMime() )
            
            HG.client_controller.pub( 'clipboard', 'text', path )
            
        
    
    def _Delete( self, media = None, default_reason = None, file_service_key = None ):
        
        if media is None:
            
            if self._current_media is None:
                
                return False
                
            
            media = [ self._current_media ]
            
        
        if default_reason is None:
            
            default_reason = 'Deleted from Preview or Media Viewer.'
            
        
        try:
            
            ( involves_physical_delete, jobs ) = ClientGUIDialogsQuick.GetDeleteFilesJobs( self, media, default_reason, suggested_file_service_key = file_service_key )
            
        except HydrusExceptions.CancelledException:
            
            return False
            
        
        def do_it( jobs ):
            
            for service_keys_to_content_updates in jobs:
                
                HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                
            
        
        HG.client_controller.CallToThread( do_it, jobs )
        
        return True
        
    
    def _DoEdgePan( self, pan_type ):
        
        if self._current_media is None:
            
            return
            
        
        my_size = self.size()
        media_size = self._media_container.size()
        
        delta_x = 0
        delta_y = 0
        
        if pan_type == CAC.SIMPLE_PAN_TOP_EDGE:
            
            delta_y = - self._media_window_pos.y()
            
        elif pan_type == CAC.SIMPLE_PAN_LEFT_EDGE:
            
            delta_x = - self._media_window_pos.x()
            
        elif pan_type == CAC.SIMPLE_PAN_BOTTOM_EDGE:
            
            delta_y = my_size.height() - ( self._media_window_pos.y() + media_size.height() )
            
        elif pan_type == CAC.SIMPLE_PAN_RIGHT_EDGE:
            
            delta_x = my_size.width() - ( self._media_window_pos.x() + media_size.width() )
            
        elif pan_type == CAC.SIMPLE_PAN_VERTICAL_CENTER:
            
            delta_y = ( my_size.height() / 2 ) - ( self._media_window_pos.y() + ( media_size.height() / 2 ) )
            
        elif pan_type == CAC.SIMPLE_PAN_HORIZONTAL_CENTER:
            
            delta_x = ( my_size.width() / 2 ) - ( self._media_window_pos.x() + ( media_size.width() / 2 ) )
            
        
        delta = QC.QPoint( delta_x, delta_y )
        
        self._media_window_pos += delta
        
        self._DrawCurrentMedia()
        
    
    def _DoManualPan( self, delta_x_step, delta_y_step ):
        
        if self._current_media is None:
            
            return
            
        
        my_size = self.size()
        media_size = self._media_container.size()
        
        x_pan_distance = min( my_size.width(), media_size.width() ) // 12
        y_pan_distance = min( my_size.height(), media_size.height() ) // 12
        
        delta_x = delta_x_step * x_pan_distance
        delta_y = delta_y_step * y_pan_distance
        
        delta = QC.QPoint( delta_x, delta_y )
        
        self._media_window_pos += delta
        
        self._DrawCurrentMedia()
        
    
    def _DrawBackgroundBitmap( self, painter ):
        
        background_colour = self._GetBackgroundColour()
        
        painter.setBackground( QG.QBrush( background_colour ) )
        
        painter.eraseRect( painter.viewport() )
        
        self._DrawBackgroundDetails( painter )
        
    
    def _DrawBackgroundDetails( self, painter ):
        
        pass
        
    
    def _DrawCurrentMedia( self ):
        
        if self._current_media is None:
            
            return
            
        
        size = self.size()
        
        if size.width() > 0 and size.height() > 0:
            
            self._SizeAndPositionMediaContainer()
            
        
    
    def _GetBackgroundColour( self ):
        
        return self._new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND )
        
    
    def _GetShowAction( self, media ):
        
        start_paused = False
        start_with_embed = False
        
        bad_result = ( CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW, start_paused, start_with_embed )
        
        if media is None:
            
            return bad_result
            
        
        mime = media.GetMime()
        
        if mime not in HC.ALLOWED_MIMES: # stopgap to catch a collection or application_unknown due to unusual import order/media moving
            
            return bad_result
            
        
        if self.PREVIEW_WINDOW:
            
            return self._new_options.GetPreviewShowAction( mime )
            
        else:
            
            return self._new_options.GetMediaShowAction( mime )
            
        
    
    def _GetIndexString( self ):
        
        return ''
        
    
    def _GetMediaContainerSize( self ):
        
        ( media_show_action, media_start_paused, media_start_with_embed ) = self._GetShowAction( self._current_media )
        
        new_size = CalculateMediaContainerSize( self._current_media, self._current_zoom, media_show_action )
        
        return new_size
        
    
    def _Inbox( self ):
        
        if self._current_media is None:
            
            return
            
        
        HG.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, ( self._current_media.GetHash(), ) ) ] } )
        
    
    def _IsZoomable( self ):
        
        if self._current_media is None:
            
            return False
            
        
        ( media_show_action, media_start_paused, media_start_with_embed ) = self._GetShowAction( self._current_media )
        
        return media_show_action not in ( CC.MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW )
        
    
    def _MaintainZoom( self, previous_media ):
        
        if previous_media is None:
            
            self._ReinitZoom()
            
        else:
            
            if self._current_media is None:
                
                return
                
            
            # set up canvas zoom
            
            previous_current_zoom = self._current_zoom
            
            ( media_show_action, media_start_paused, media_start_with_embed ) = self._GetShowAction( previous_media )
            
            ( previous_default_zoom, previous_canvas_zoom ) = CalculateCanvasZooms( self, previous_media, media_show_action )
            
            ( media_show_action, media_start_paused, media_start_with_embed ) = self._GetShowAction( self._current_media )
            
            ( gumpf_current_zoom, self._canvas_zoom ) = CalculateCanvasZooms( self, self._current_media, media_show_action )
            
            # previously, we always matched width, but this causes a problem in dupe viewer when B has a little watermark on the bottom, spilling below bottom of screen
            # I think in future we will have more options regarding all this, and this method will change significantly
            # however for now we really just want a hardcoded ok solution for all situations, so let's just hook on default canvas zoom situation
            
            ( previous_width, previous_height ) = CalculateMediaSize( previous_media, self._current_zoom )
            
            ( current_media_100_width, current_media_100_height ) = self._current_media.GetResolution()
            
            width_locked_zoom = previous_width / current_media_100_width
            height_locked_zoom = previous_height / current_media_100_height
            
            width_locked_size = CalculateMediaContainerSize( self._current_media, width_locked_zoom, media_show_action )
            height_locked_size = CalculateMediaContainerSize( self._current_media, height_locked_zoom, media_show_action )
            
            # if we have both landscape, we'll go height, otherwise default width
            if previous_width > previous_height and current_media_100_width > current_media_100_height:
                
                lock_height = True
                
            else:
                
                lock_height = False
                
            
            if previous_current_zoom == previous_default_zoom and previous_current_zoom <= previous_canvas_zoom * 1.02:
                
                # we were looking at the default zoom, near or at canvas edge(s), probably hadn't zoomed before switching comparison
                # we want to make sure our comparison does not spill over the canvas edge
                
                width_a_concern = self._media_container.width() >= self.width() * 0.95
                height_a_concern = self._media_container.height() >= self.height() * 0.95
                
                # locking by width will spill over bottom of screen
                if height_a_concern and width_locked_size.height() > self._media_container.height():
                    
                    lock_height = True
                    
                
                # locking by height will spill over right of screen
                if width_a_concern and height_locked_size.width() > self._media_container.width():
                    
                    lock_height = False
                    
                
            
            if lock_height:
                
                self._current_zoom = height_locked_zoom
                
            else:
                
                self._current_zoom = width_locked_zoom
                
            
            HG.client_controller.pub( 'canvas_new_zoom', self._canvas_key, self._current_zoom )
            
            # and fix drag delta, or rewangle this so drag delta is offset to start with anyway m8, yeah
            
        
    
    def _ManageNotes( self ):
        
        if self._current_media is None:
            
            return
            
        
        ClientGUIMediaActions.EditFileNotes( self, self._current_media )
        
    
    def _ManageRatings( self ):
        
        if self._current_media is None:
            
            return
            
        
        if len( HG.client_controller.services_manager.GetServices( HC.RATINGS_SERVICES ) ) > 0:
            
            with ClientGUIDialogsManage.DialogManageRatings( self, ( self._current_media, ) ) as dlg:
                
                dlg.exec()
                
            
        
    
    def _ManageTags( self ):
        
        if self._current_media is None:
            
            return
            
        
        for child in self.children():
            
            if isinstance( child, ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel ):
                
                panel = child.GetPanel()
                
                if isinstance( panel, ClientGUITags.ManageTagsPanel ):
                    
                    child.activateWindow()
                    
                    command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SET_SEARCH_FOCUS )
                    
                    panel.ProcessApplicationCommand( command )
                    
                    return
                    
                
            
        
        # take any focus away from hover window, which will mess up window order when it hides due to the new frame
        self.setFocus( QC.Qt.OtherFocusReason )
        
        title = 'manage tags'
        frame_key = 'manage_tags_frame'
        
        manage_tags = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUITags.ManageTagsPanel( manage_tags, self._location_context, ( self._current_media, ), immediate_commit = True, canvas_key = self._canvas_key )
        
        manage_tags.SetPanel( panel )
        
    
    def _ManageURLs( self ):
        
        if self._current_media is None:
            
            return
            
        
        title = 'manage known urls'
        
        with ClientGUITopLevelWindowsPanels.DialogManage( self, title ) as dlg:
            
            panel = ClientGUIScrolledPanelsManagement.ManageURLsPanel( dlg, ( self._current_media, ) )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    def _MediaFocusWentToExternalProgram( self ):
        
        if self._current_media is None:
            
            return
            
        
        mime = self._current_media.GetMime()
        
        if self._current_media.HasDuration():
            
            self._media_container.Pause()
            
        
    
    def _OpenExternally( self ):
        
        if self._current_media is None:
            
            return
            
        
        hash = self._current_media.GetHash()
        mime = self._current_media.GetMime()
        
        client_files_manager = HG.client_controller.client_files_manager
        
        path = client_files_manager.GetFilePath( hash, mime )
        
        launch_path = self._new_options.GetMimeLaunch( mime )
        
        HydrusPaths.LaunchFile( path, launch_path )
        
        self._MediaFocusWentToExternalProgram()
        
    
    def _OpenFileInWebBrowser( self ):
        
        if self._current_media is not None:
            
            hash = self._current_media.GetHash()
            mime = self._current_media.GetMime()
            
            client_files_manager = HG.client_controller.client_files_manager
            
            path = client_files_manager.GetFilePath( hash, mime )
            
            ClientPaths.LaunchPathInWebBrowser( path )
            
            self._MediaFocusWentToExternalProgram()
            
        
    
    def _OpenFileLocation( self ):
        
        if self._current_media is not None:
            
            hash = self._current_media.GetHash()
            mime = self._current_media.GetMime()
            
            client_files_manager = HG.client_controller.client_files_manager
            
            path = client_files_manager.GetFilePath( hash, mime )
            
            HydrusPaths.OpenFileLocation( path )
            
            self._MediaFocusWentToExternalProgram()
            
        
    
    def _OpenKnownURL( self ):
        
        if self._current_media is not None:
            
            ClientGUIMedia.DoOpenKnownURLFromShortcut( self, self._current_media )
            
        
    
    def _PauseCurrentMedia( self ):
        
        if self._current_media is None:
            
            return
            
        
        self._media_container.Pause()
        
    
    def _PausePlayCurrentMedia( self ):
        
        if self._current_media is None:
            
            return
            
        
        self._media_container.PausePlay()
        
    
    def _PrefetchNeighbours( self ):
        
        pass
        
    
    def _ReinitZoom( self ):
        
        if self._current_media is None:
            
            return
            
        
        ( media_show_action, media_start_paused, media_start_with_embed ) = self._GetShowAction( self._current_media )
        
        ( self._current_zoom, self._canvas_zoom ) = CalculateCanvasZooms( self, self._current_media, media_show_action )
        
        HG.client_controller.pub( 'canvas_new_zoom', self._canvas_key, self._current_zoom )
        
    
    def _RescueOffScreenMediaWindow( self ):
        
        size = self._GetMediaContainerSize()
        
        my_rect = self.rect()
        media_rect = QC.QRect( self._media_window_pos, size )
        
        if not my_rect.intersects( media_rect ):
            
            # up/down
            
            height_buffer = min( media_rect.height(), self.height() // 5 )
            
            if media_rect.bottom() < my_rect.top():
                
                media_rect.moveBottom( my_rect.top() + height_buffer )
                
            elif media_rect.top() > my_rect.bottom():
                
                media_rect.moveTop( my_rect.bottom() - height_buffer )
                
            
            # left/right
            
            width_buffer = min( media_rect.width(), self.width() // 5 )
            
            if media_rect.right() < my_rect.left():
                
                media_rect.moveRight( my_rect.left() + width_buffer )
                
            elif media_rect.left() > my_rect.right():
                
                media_rect.moveLeft( my_rect.right() - width_buffer )
                
            
            self._media_window_pos = media_rect.topLeft()
            
        
    
    def _ResetMediaWindowCenterPosition( self ):
        
        if self._current_media is None:
            
            return
            
        
        my_size = self.size()
        
        ( media_show_action, media_start_paused, media_start_with_embed ) = self._GetShowAction( self._current_media )
        
        media_size = CalculateMediaContainerSize( self._current_media, self._current_zoom, media_show_action )
        
        x = ( my_size.width() - media_size.width() ) // 2
        y = ( my_size.height() - media_size.height() ) // 2
        
        self._media_window_pos = QC.QPoint( x, y )
        
        self._last_drag_pos = None
        
    
    def _SaveCurrentMediaViewTime( self ):
        
        now = HydrusData.GetNow()
        
        view_timestamp = self._current_media_start_time
        
        viewtime_delta = now - self._current_media_start_time
        
        self._current_media_start_time = now
        
        if self._current_media is None:
            
            return
            
        
        hash = self._current_media.GetHash()
        
        HG.client_controller.file_viewing_stats_manager.FinishViewing( hash, self.CANVAS_TYPE, view_timestamp, viewtime_delta )
        
    
    def _SeekDeltaCurrentMedia( self, direction, duration_ms ):
        
        if self._current_media is None:
            
            return
            
        
        self._media_container.SeekDelta( direction, duration_ms )
        
    
    def _ShowMediaInNewPage( self ):
        
        if self._current_media is None:
            
            return
            
        
        hash = self._current_media.GetHash()
        
        hashes = { hash }
        
        HG.client_controller.pub( 'new_page_query', self._location_context, initial_hashes = hashes )
        
    
    def _SizeAndPositionMediaContainer( self ):
        
        if self._current_media is None:
            
            return
            
        
        new_size = self._GetMediaContainerSize()
        
        if new_size != self._media_container.size():
            
            self._media_container.setFixedSize( new_size )
            
        
        if self._media_window_pos == self._media_container.pos():
            
            if HC.PLATFORM_MACOS:
                
                self._media_container.update()
                
            
        else:
            
            self._media_container.move( self._media_window_pos )
            
        
    
    def _TryToChangeZoom( self, new_zoom, zoom_center_type_override = None ):
        
        if self._current_media is None:
            
            return
            
        
        media_window_size = self._media_container.size()
        
        media_window_width = media_window_size.width()
        media_window_height = media_window_size.height()
        
        new_media_window_size = CalculateMediaContainerSize( self._current_media, new_zoom, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV )
        
        new_media_window_width = new_media_window_size.width()
        new_media_window_height = new_media_window_size.height()
        
        if new_media_window_width > 32000 or new_media_window_height > 32000:
            
            return
            
        
        my_size = self.size()
        
        old_size_bigger = my_size.width() < media_window_width or my_size.height() < media_window_height
        new_size_fits = my_size.width() >= new_media_window_width and my_size.height() >= new_media_window_height
        
        #
        
        if media_window_width > 0 and media_window_height > 0:
            
            if zoom_center_type_override is None:
                
                zoom_center_type = HG.client_controller.new_options.GetInteger( 'media_viewer_zoom_center' )
                
            else:
                
                zoom_center_type = zoom_center_type_override
                
            
            # viewer center is the default
            zoom_centerpoint = QC.QPoint( my_size.width() // 2, my_size.height() // 2 )
            
            if zoom_center_type == ZOOM_CENTERPOINT_MEDIA_CENTER:
                
                zoom_centerpoint = self._media_window_pos + QC.QPoint( media_window_width // 2, media_window_height // 2 )
                
            elif zoom_center_type == ZOOM_CENTERPOINT_MEDIA_TOP_LEFT:
                
                zoom_centerpoint = self._media_window_pos
                
            elif zoom_center_type == ZOOM_CENTERPOINT_MOUSE:
                
                mouse_pos = self.mapFromGlobal( QG.QCursor.pos() )
                
                if self.rect().contains( mouse_pos ):
                    
                    zoom_centerpoint = mouse_pos
                    
                
        
            # probably a simpler way to calc this, but hey
            widths_centerpoint_is_from_pos = ( zoom_centerpoint.x() - self._media_window_pos.x() ) / media_window_width
            heights_centerpoint_is_from_pos = ( zoom_centerpoint.y() - self._media_window_pos.y() ) / media_window_height
            
            zoom_width_delta = media_window_width - new_media_window_width
            zoom_height_delta = media_window_height - new_media_window_height
            
            centerpoint_adjusted_delta = QC.QPoint( int( zoom_width_delta * widths_centerpoint_is_from_pos ), int( zoom_height_delta * heights_centerpoint_is_from_pos ) )
            
            self._media_window_pos += centerpoint_adjusted_delta
            
        
        #
        
        self._current_zoom = new_zoom
        
        self._RescueOffScreenMediaWindow()
        
        HG.client_controller.pub( 'canvas_new_zoom', self._canvas_key, self._current_zoom )
        '''
        # rescue hack no longer needed as media center zoom is non-default
        if old_size_bigger and new_size_fits:
            
            self._ResetMediaWindowCenterPosition()
            
        '''
        # due to the foolish 'giganto window' system for large zooms, some auto-update stuff doesn't work right if the convas rect is contained by the media rect, so do a refresh here
        self._DrawCurrentMedia()
        
        self.update()
        
    
    def _Undelete( self ):
        
        if self._current_media is None:
            
            return
            
        
        locations_manager = self._current_media.GetLocationsManager()
        
        local_file_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_FILE_DOMAIN, ) )
        
        deleted_local_services = [ local_file_service for local_file_service in local_file_services if local_file_service.GetServiceKey() in locations_manager.GetDeleted() ]
        
        if len( deleted_local_services ) > 0:
            
            choice_tuples = []
            
            for service in deleted_local_services:
                
                choice_tuples.append( ( service.GetName(), service, service.GetName() ) )
                
            
            try:
                
                undelete_service = ClientGUIDialogsQuick.SelectFromListButtons( self, 'Undelete for?', choice_tuples, message = 'Which service to undelete back to?' )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            do_it = False
            
            if len( choice_tuples ) > 1 or not HC.options[ 'confirm_trash' ]:
                
                do_it = True
                
            else:
                
                result = ClientGUIDialogsQuick.GetYesNo( self, 'Undelete this file back to {}?'.format( undelete_service.GetName() ) )
                
                if result == QW.QDialog.Accepted:
                    
                    do_it = True
                    
                
            
            if do_it:
                
                HG.client_controller.Write( 'content_updates', { undelete_service.GetServiceKey() : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, ( self._current_media.GetHash(), ) ) ] } )
                
            
        
    
    def _UpdateBackgroundColour( self ):
        
        colour = self._GetBackgroundColour()
        
        QP.SetBackgroundColour( self, colour )
        
        self.update()
        
    
    def _ZoomIn( self, zoom_center_type_override = None ):
        
        if self._current_media is not None and self._IsZoomable():
            
            ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) = self._new_options.GetMediaZoomOptions( self._current_media.GetMime() )
            
            if exact_zooms_only:
                
                exact_zoom = 1.0
                
                if exact_zoom <= self._current_zoom:
                    
                    while exact_zoom <= self._current_zoom:
                        
                        exact_zoom *= 2
                        
                    
                else:
                    
                    while exact_zoom / 2 > self._current_zoom:
                        
                        exact_zoom /= 2
                        
                    
                
                possible_zooms = [ exact_zoom ]
                
            else:
                
                possible_zooms = self._new_options.GetMediaZooms()
                
            
            possible_zooms.append( self._canvas_zoom )
            
            bigger_zooms = [ zoom for zoom in possible_zooms if zoom > self._current_zoom ]
            
            if len( bigger_zooms ) > 0:
                
                new_zoom = min( bigger_zooms )
                
                self._TryToChangeZoom( new_zoom, zoom_center_type_override = zoom_center_type_override )
                
            
        
    
    def _ZoomOut( self, zoom_center_type_override = None ):
        
        if self._current_media is not None and self._IsZoomable():
            
            ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) = self._new_options.GetMediaZoomOptions( self._current_media.GetMime() )
            
            if exact_zooms_only:
                
                exact_zoom = 1.0
                
                if exact_zoom < self._current_zoom:
                    
                    while exact_zoom * 2 < self._current_zoom:
                        
                        exact_zoom *= 2
                        
                    
                else:
                    
                    while exact_zoom >= self._current_zoom:
                        
                        exact_zoom /= 2
                        
                    
                
                possible_zooms = [ exact_zoom ]
                
            else:
                
                possible_zooms = self._new_options.GetMediaZooms()
                
            
            possible_zooms.append( self._canvas_zoom )
            
            smaller_zooms = [ zoom for zoom in possible_zooms if zoom < self._current_zoom ]
            
            if len( smaller_zooms ) > 0:
                
                new_zoom = max( smaller_zooms )
                
                self._TryToChangeZoom( new_zoom, zoom_center_type_override = zoom_center_type_override )
                
            
        
    
    def _ZoomSwitch( self, zoom_center_type_override = None ):
        
        if self._current_media is not None and self._IsZoomable():
            
            if self._canvas_zoom == 1.0 and self._current_zoom == 1.0:
                
                return
                
            
            if self._current_zoom == 1.0:
                
                new_zoom = self._canvas_zoom
                
            else:
                
                new_zoom = 1.0
                
            
            self._TryToChangeZoom( new_zoom, zoom_center_type_override = zoom_center_type_override )
            
            if new_zoom <= self._canvas_zoom:
                
                self._ResetMediaWindowCenterPosition()
                
            
        
    
    def event( self, event ):
        
        if event.type() == QC.QEvent.LayoutRequest:
            
            return True
            
        else:
            
            return QW.QWidget.event( self, event )
            
        
    
    def CleanBeforeDestroy( self ):
        
        self.ClearMedia()
        
    
    def ClearMedia( self ):
        
        self.SetMedia( None )
        
    
    def BeginDrag( self ):
        
        point = self.mapFromGlobal( QG.QCursor.pos() )
        
        self._last_drag_pos = point
        self._current_drag_is_touch = False
        
    
    def resizeEvent( self, event ):
        
        my_size = self.size()
        
        if self._current_media is not None:
            
            media_container_size = self._media_container.size()
            
            if my_size != media_container_size:
                
                self._ReinitZoom()
                
                self._ResetMediaWindowCenterPosition()
                
            
        
        self.update()
        
    
    def EndDrag( self ):
        
        self._last_drag_pos = None
        
    
    def FlipActiveCustomShortcutName( self, name ):
        
        self._my_shortcuts_handler.FlipShortcuts( name )
        
    
    def GetActiveCustomShortcutNames( self ):
        
        return self._my_shortcuts_handler.GetCustomShortcutNames()
        
    
    def ManageNotes( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ManageNotes()
            
        
    
    def ManageTags( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ManageTags()
            
        
    
    def MouseIsNearAnimationBar( self ):
        
        if self._current_media is None:
            
            return False
            
        else:
            
            return self._media_container.MouseIsNearAnimationBar()
            
        
    
    def MouseIsOverMedia( self ):
        
        if self._current_media is None:
            
            return False
            
        else:
            
            media_mouse_pos = self._media_container.mapFromGlobal( QG.QCursor.pos() )
            
            media_rect = self._media_container.rect()
            
            return media_rect.contains( media_mouse_pos )
            
        
    
    def OpenExternally( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._OpenExternally()
            
        
    
    def paintEvent( self, event ):
        
        painter = QG.QPainter( self )
        
        self._DrawBackgroundBitmap( painter )
        
        if self._current_media is not None:
            
            self._DrawCurrentMedia()
            
        
    
    def PauseMedia( self ):
        
        self._PauseCurrentMedia()
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand, canvas_key = None ):
        
        if canvas_key is not None and canvas_key != self._canvas_key:
            
            return False
            
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_MANAGE_FILE_RATINGS:
                
                self._ManageRatings()
                
            elif action == CAC.SIMPLE_MANAGE_FILE_TAGS:
                
                self._ManageTags()
                
            elif action == CAC.SIMPLE_MANAGE_FILE_URLS:
                
                self._ManageURLs()
                
            elif action == CAC.SIMPLE_MANAGE_FILE_NOTES:
                
                self._ManageNotes()
                
            elif action == CAC.SIMPLE_OPEN_KNOWN_URL:
                
                self._OpenKnownURL()
                
            elif action == CAC.SIMPLE_ARCHIVE_FILE:
                
                self._Archive()
                
            elif action == CAC.SIMPLE_COPY_BMP:
                
                self._CopyBMPToClipboard()
                
            elif action == CAC.SIMPLE_COPY_BMP_OR_FILE_IF_NOT_BMPABLE:
                
                copied = self._CopyBMPToClipboard()
                
                if not copied:
                    
                    self._CopyFileToClipboard()
                    
                
            elif action == CAC.SIMPLE_COPY_FILE:
                
                self._CopyFileToClipboard()
                
            elif action == CAC.SIMPLE_COPY_PATH:
                
                self._CopyPathToClipboard()
                
            elif action == CAC.SIMPLE_COPY_SHA256_HASH:
                
                self._CopyHashToClipboard( 'sha256' )
                
            elif action == CAC.SIMPLE_COPY_MD5_HASH:
                
                self._CopyHashToClipboard( 'md5' )
                
            elif action == CAC.SIMPLE_COPY_SHA1_HASH:
                
                self._CopyHashToClipboard( 'sha1' )
                
            elif action == CAC.SIMPLE_COPY_SHA512_HASH:
                
                self._CopyHashToClipboard( 'sha512' )
                
            elif action == CAC.SIMPLE_DELETE_FILE:
                
                self._Delete()
                
            elif action == CAC.SIMPLE_UNDELETE_FILE:
                
                self._Undelete()
                
            elif action == CAC.SIMPLE_INBOX_FILE:
                
                self._Inbox()
                
            elif action == CAC.SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM:
                
                self._OpenExternally()
                
            elif action == CAC.SIMPLE_PAN_UP:
                
                self._DoManualPan( 0, -1 )
                
            elif action == CAC.SIMPLE_PAN_DOWN:
                
                self._DoManualPan( 0, 1 )
                
            elif action == CAC.SIMPLE_PAN_LEFT:
                
                self._DoManualPan( -1, 0 )
                
            elif action == CAC.SIMPLE_PAN_RIGHT:
                
                self._DoManualPan( 1, 0 )
                
            elif action in ( CAC.SIMPLE_PAN_TOP_EDGE, CAC.SIMPLE_PAN_BOTTOM_EDGE, CAC.SIMPLE_PAN_LEFT_EDGE, CAC.SIMPLE_PAN_RIGHT_EDGE, CAC.SIMPLE_PAN_VERTICAL_CENTER, CAC.SIMPLE_PAN_HORIZONTAL_CENTER ):
                
                self._DoEdgePan( action )
                
            elif action == CAC.SIMPLE_PAUSE_MEDIA:
                
                self._PauseCurrentMedia()
                
            elif action == CAC.SIMPLE_PAUSE_PLAY_MEDIA:
                
                self._PausePlayCurrentMedia()
                
            elif action == CAC.SIMPLE_MEDIA_SEEK_DELTA:
                
                ( direction, ms ) = command.GetSimpleData()
                
                self._SeekDeltaCurrentMedia( direction, ms )
                
            elif action == CAC.SIMPLE_MOVE_ANIMATION_TO_PREVIOUS_FRAME:
                
                self._media_container.GotoPreviousOrNextFrame( -1 )
                
            elif action == CAC.SIMPLE_MOVE_ANIMATION_TO_NEXT_FRAME:
                
                self._media_container.GotoPreviousOrNextFrame( 1 )
                
            elif action == CAC.SIMPLE_ZOOM_IN:
                
                self._ZoomIn()
                
            elif action == CAC.SIMPLE_ZOOM_IN_VIEWER_CENTER:
                
                self._ZoomIn( zoom_center_type_override = ZOOM_CENTERPOINT_VIEWER_CENTER )
                
            elif action == CAC.SIMPLE_ZOOM_OUT:
                
                self._ZoomOut()
                
            elif action == CAC.SIMPLE_ZOOM_OUT_VIEWER_CENTER:
                
                self._ZoomOut( zoom_center_type_override = ZOOM_CENTERPOINT_VIEWER_CENTER )
                
            elif action == CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM:
                
                self._ZoomSwitch()
                
            elif action == CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM_VIEWER_CENTER:
                
                self._ZoomSwitch( zoom_center_type_override = ZOOM_CENTERPOINT_VIEWER_CENTER )
                
            else:
                
                command_processed = False
                
            
        elif command.IsContentCommand():
            
            if self._current_media is None:
                
                return
                
            
            command_processed = ClientGUIMediaActions.ApplyContentApplicationCommandToMedia( self, command, ( self._current_media, ) )
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def ResetMediaWindowCenterPosition( self ):
        
        self._ResetMediaWindowCenterPosition()
        
    
    def SetLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        self._location_context = location_context
        
    
    def SetMedia( self, media: typing.Optional[ ClientMedia.MediaSingleton ] ):
        
        if media is not None and not self.isVisible():
            
            return
            
        
        if media is not None:
            
            media = media.GetDisplayMedia()
            
            if not self._CanDisplayMedia( media ):
                
                media = None
                
            
        
        if media != self._current_media:
            
            HG.client_controller.ResetIdleTimer()
            
            self._SaveCurrentMediaViewTime()
            
            previous_media = self._current_media
            
            self._current_media = media
            
            if self._current_media is None:
                
                self._media_container.ClearMedia()
                
            else:
                
                if previous_media is not None and self._maintain_pan_and_zoom:
                    
                    self._MaintainZoom( previous_media )
                    
                else:
                    
                    self._ReinitZoom()
                    
                
                if not self._maintain_pan_and_zoom:
                    
                    self._ResetMediaWindowCenterPosition()
                    
                
                initial_size = self._GetMediaContainerSize()
                
                if self._current_media.GetLocationsManager().IsLocal() and initial_size.width() > 0 and initial_size.height() > 0:
                    
                    ( media_show_action, media_start_paused, media_start_with_embed ) = self._GetShowAction( self._current_media )
                    
                    self._media_container.SetMedia( self._current_media, initial_size, self._media_window_pos, media_show_action, media_start_paused, media_start_with_embed )
                    
                else:
                    
                    self._current_media = None
                    
                
            
            HG.client_controller.pub( 'canvas_new_display_media', self._canvas_key, self._current_media )
            
            HG.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self.update()
            
        
    
    def minimumSizeHint( self ):
        
        return QC.QSize( 120, 120 )
        
    
    def ZoomIn( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ZoomIn()
            
        
    
    def ZoomOut( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ZoomOut()
            
        
    
    def ZoomSwitch( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ZoomSwitch()
            
        
    
class MediaContainerDragClickReportingFilter( QC.QObject ):
    
    def __init__( self, parent: Canvas ):
        
        QC.QObject.__init__( self, parent )
        
        self._canvas = parent
        
    
    def eventFilter( self, watched, event ):
        
        if event.type() == QC.QEvent.MouseButtonPress and event.button() == QC.Qt.LeftButton:
            
            self._canvas.BeginDrag()
            
        elif event.type() == QC.QEvent.MouseButtonRelease and event.button() == QC.Qt.LeftButton:
            
            self._canvas.EndDrag()
            
        
        return False
        
    
class CanvasPanel( Canvas ):
    
    PREVIEW_WINDOW = True
    CANVAS_TYPE = CC.CANVAS_PREVIEW
    
    def __init__( self, parent, page_key, location_context: ClientLocation.LocationContext ):
        
        Canvas.__init__( self, parent, location_context )
        
        self._page_key = page_key
        
        self._hidden_page_current_media = None
        
        self._media_container.launchMediaViewer.connect( self.LaunchMediaViewer )
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        
    
    def mouseReleaseEvent( self, event ):
        
        if event.button() != QC.Qt.RightButton:
            
            Canvas.mouseReleaseEvent( self, event )
            
            return
            
        
        # contextmenu doesn't quite work here yet due to focus issues
        
        self.ShowMenu()
        
    
    def ClearMedia( self ):
        
        self._hidden_page_current_media = None
        
        Canvas.ClearMedia( self )
        
    
    def PageHidden( self ):
        
        hidden_page_current_media = self._current_media
        
        self.ClearMedia()
        
        self._hidden_page_current_media = hidden_page_current_media
        
    
    def PageShown( self ):
        
        self.SetMedia( self._hidden_page_current_media )
        
        self._hidden_page_current_media = None
        
    
    def ShowMenu( self ):
        
        menu = QW.QMenu()
        
        if self._current_media is not None:
            
            new_options = HG.client_controller.new_options
            
            advanced_mode = new_options.GetBoolean( 'advanced_mode' )
            
            services = HG.client_controller.services_manager.GetServices()
            
            locations_manager = self._current_media.GetLocationsManager()
            
            local_ratings_services = [ service for service in services if service.GetServiceType() in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
            
            i_can_post_ratings = len( local_ratings_services ) > 0
            
            #
            
            info_lines = self._current_media.GetPrettyInfoLines()
            
            top_line = info_lines.pop(0)
            
            info_menu = QW.QMenu( menu )
            
            for line in info_lines:
                
                ClientGUIMenus.AppendMenuLabel( info_menu, line, line )
                
            
            ClientGUIMedia.AddFileViewingStatsMenu( info_menu, ( self._current_media, ) )
            
            ClientGUIMenus.AppendMenu( menu, info_menu, top_line )
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        AddAudioVolumeMenu( menu, self.CANVAS_TYPE )
        
        if self._current_media is not None:
            
            #
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if self._current_media.HasInbox():
                
                ClientGUIMenus.AppendMenuItem( menu, 'archive', 'Archive this file.', self._Archive )
                
            
            if self._current_media.HasArchive():
                
                ClientGUIMenus.AppendMenuItem( menu, 'inbox', 'Send this files back to the inbox.', self._Inbox )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            local_file_service_keys = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
            
            # brush this up to handle different service keys
            # undelete do an optional service key too
            
            local_file_service_keys_we_are_in = sorted( locations_manager.GetCurrent().intersection( local_file_service_keys ), key = HG.client_controller.services_manager.GetName )
            
            for file_service_key in local_file_service_keys_we_are_in:
                
                ClientGUIMenus.AppendMenuItem( menu, 'delete from {}'.format( HG.client_controller.services_manager.GetName( file_service_key ) ), 'Delete this file.', self._Delete, file_service_key = file_service_key )
                
            
            if locations_manager.IsTrashed():
                
                ClientGUIMenus.AppendMenuItem( menu, 'delete completely', 'Physically delete this file from disk.', self._Delete, file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
                ClientGUIMenus.AppendMenuItem( menu, 'undelete', 'Take this file out of the trash.', self._Undelete )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            manage_menu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( manage_menu, 'tags', 'Manage this file\'s tags.', self._ManageTags )
            
            if i_can_post_ratings:
                
                ClientGUIMenus.AppendMenuItem( manage_menu, 'ratings', 'Manage this file\'s ratings.', self._ManageRatings )
                
            
            ClientGUIMenus.AppendMenuItem( manage_menu, 'urls', 'Manage this file\'s known URLs.', self._ManageURLs )
            
            num_notes = self._current_media.GetNotesManager().GetNumNotes()
            
            notes_str = 'notes'
            
            if num_notes > 0:
                
                notes_str = '{} ({})'.format( notes_str, HydrusData.ToHumanInt( num_notes ) )
                
            
            ClientGUIMenus.AppendMenuItem( manage_menu, notes_str, 'Manage this file\'s notes.', self._ManageNotes )
            
            ClientGUIMedia.AddManageFileViewingStatsMenu( self, manage_menu, [ self._current_media ] )
            
            ClientGUIMenus.AppendMenu( menu, manage_menu, 'manage' )
            
            ClientGUIMedia.AddKnownURLsViewCopyMenu( self, menu, self._current_media )
            
            open_menu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( open_menu, 'in external program', 'Open this file in your OS\'s default program.', self._OpenExternally )
            ClientGUIMenus.AppendMenuItem( open_menu, 'in a new page', 'Show your current media in a simple new page.', self._ShowMediaInNewPage )
            ClientGUIMenus.AppendMenuItem( open_menu, 'in web browser', 'Show this file in your OS\'s web browser.', self._OpenFileInWebBrowser )
            
            show_open_in_explorer = advanced_mode and ( HC.PLATFORM_WINDOWS or HC.PLATFORM_MACOS )
            
            if show_open_in_explorer:
                
                ClientGUIMenus.AppendMenuItem( open_menu, 'in file browser', 'Show this file in your OS\'s file browser.', self._OpenFileLocation )
                
            
            ClientGUIMenus.AppendMenu( menu, open_menu, 'open' )
            
            share_menu = QW.QMenu( menu )
            
            copy_menu = QW.QMenu( share_menu )

            ClientGUIMenus.AppendMenuItem( copy_menu, 'file', 'Copy this file to your clipboard.', self._CopyFileToClipboard )
            
            copy_hash_menu = QW.QMenu( copy_menu )

            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'sha256 (hydrus default)', 'Copy this file\'s SHA256 hash.', self._CopyHashToClipboard, 'sha256' )
            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'md5', 'Copy this file\'s MD5 hash.', self._CopyHashToClipboard, 'md5' )
            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'sha1', 'Copy this file\'s SHA1 hash.', self._CopyHashToClipboard, 'sha1' )
            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'sha512', 'Copy this file\'s SHA512 hash.', self._CopyHashToClipboard, 'sha512' )
            
            ClientGUIMenus.AppendMenu( copy_menu, copy_hash_menu, 'hash' )
            
            if advanced_mode:
                
                hash_id_str = str( self._current_media.GetHashId() )
                
                ClientGUIMenus.AppendMenuItem( copy_menu, 'file_id ({})'.format( hash_id_str ), 'Copy this file\'s internal file/hash_id.', HG.client_controller.pub, 'clipboard', 'text', hash_id_str )
                
            
            if self._current_media.GetMime() in HC.IMAGES:
                
                ClientGUIMenus.AppendMenuItem( copy_menu, 'image (bitmap)', 'Copy this file to your clipboard as a bmp.', self._CopyBMPToClipboard )
                

            ClientGUIMenus.AppendMenuItem( copy_menu, 'path', 'Copy this file\'s path to your clipboard.', self._CopyPathToClipboard )
            
            ClientGUIMenus.AppendMenu( share_menu, copy_menu, 'copy' )
            
            ClientGUIMenus.AppendMenu( menu, share_menu, 'share' )
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def LaunchMediaViewer( self ):
        
        HG.client_controller.pub( 'launch_media_viewer', self._page_key )
        
    
    def MediaFocusWentToExternalProgram( self, page_key ):
        
        if page_key == self._page_key:
            
            self._MediaFocusWentToExternalProgram()
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is not None:
            
            my_hash = self._current_media.GetHash()
            
            do_redraw = False
            
            for ( service_key, content_updates ) in service_keys_to_content_updates.items():
                
                if True in ( my_hash in content_update.GetHashes() for content_update in content_updates ):
                    
                    do_redraw = True
                    
                    break
                    
                
            
            if do_redraw:
                
                self.update()
                
            
        
    
    def SetMedia( self, media ):
        
        if HC.options[ 'hide_preview' ]:
            
            return
            
        
        Canvas.SetMedia( self, media )
        
    
class CanvasWithDetails( Canvas ):
    
    def __init__( self, parent, location_context ):
        
        Canvas.__init__( self, parent, location_context )
        
        HG.client_controller.sub( self, 'RedrawDetails', 'refresh_all_tag_presentation_gui' )
        
    
    def _DrawAdditionalTopMiddleInfo( self, painter, current_y ):
        
        pass
        
    
    def _DrawBackgroundDetails( self, painter ):
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        if self._current_media is None:
            
            text = self._GetNoMediaText()
            
            ( text_size, text ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, text )
            
            x = ( my_width - text_size.width() ) // 2
            y = ( my_height - text_size.height() ) // 2
            
            ClientGUIFunctions.DrawText( painter, x, y, text )
            
        else:
            
            # tags on the top left
            
            painter.setFont( QW.QApplication.font() )
            
            tags_manager = self._current_media.GetTagsManager()
            
            current = tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_SINGLE_MEDIA )
            pending = tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_SINGLE_MEDIA )
            petitioned = tags_manager.GetPetitioned( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_SINGLE_MEDIA )
            
            tags_i_want_to_display = set()
            
            tags_i_want_to_display.update( current )
            tags_i_want_to_display.update( pending )
            tags_i_want_to_display.update( petitioned )
            
            tags_i_want_to_display = list( tags_i_want_to_display )
            
            tag_sort = HG.client_controller.new_options.GetDefaultTagSort()
            
            ClientTagSorting.SortTags( tag_sort, tags_i_want_to_display )
            
            current_y = 3
            
            namespace_colours = HC.options[ 'namespace_colours' ]
            
            for tag in tags_i_want_to_display:
                
                display_string = ClientTags.RenderTag( tag, True )
                
                if tag in pending:
                    
                    display_string += ' (+)'
                    
                
                if tag in petitioned:
                    
                    display_string += ' (-)'
                    
                
                ( namespace, subtag ) = HydrusTags.SplitTag( tag )
                
                if namespace in namespace_colours:
                    
                    ( r, g, b ) = namespace_colours[ namespace ]
                    
                else:
                    
                    ( r, g, b ) = namespace_colours[ None ]
                    
                
                painter.setPen( QG.QPen( QG.QColor( r, g, b ) ) )
                
                ( text_size, display_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, display_string )
                
                ClientGUIFunctions.DrawText( painter, 5, current_y, display_string )
                
                current_y += text_size.height()
                
            
            # top right
            
            current_y = 2
            
            # ratings
            
            services_manager = HG.client_controller.services_manager
            
            like_services = services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ) )
            
            like_services.reverse()
            
            like_rating_current_x = my_width - 16 - 2 # -2 to line up exactly with the floating panel
            
            for like_service in like_services:
                
                service_key = like_service.GetServiceKey()
                
                rating_state = ClientRatings.GetLikeStateFromMedia( ( self._current_media, ), service_key )
                
                ClientGUIRatings.DrawLike( painter, like_rating_current_x, current_y, service_key, rating_state )
                
                like_rating_current_x -= 16
                
            
            if len( like_services ) > 0:
                
                current_y += 18
                
            
            numerical_services = services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
            
            for numerical_service in numerical_services:
                
                service_key = numerical_service.GetServiceKey()
                
                ( rating_state, rating ) = ClientRatings.GetNumericalStateFromMedia( ( self._current_media, ), service_key )
                
                numerical_width = ClientGUIRatings.GetNumericalWidth( service_key )
                
                ClientGUIRatings.DrawNumerical( painter, my_width - numerical_width - 2, current_y, service_key, rating_state, rating ) # -2 to line up exactly with the floating panel
                
                current_y += 18
                
            
            # icons
            
            icons_to_show = []
            
            if self._current_media.HasNotes():
                
                icons_to_show.append( CC.global_pixmaps().notes )
                
            
            if self._current_media.GetLocationsManager().IsTrashed():
                
                icons_to_show.append( CC.global_pixmaps().trash )
                
            
            if self._current_media.HasInbox():
                
                icons_to_show.append( CC.global_pixmaps().inbox )
                
            
            if len( icons_to_show ) > 0:
                
                icon_x = 0
                
                for icon in icons_to_show:
                    
                    painter.drawPixmap( my_width + icon_x - 18, current_y, icon )
                    
                    icon_x -= 18
                    
                
                current_y += 18
                
            
            painter.setPen( QG.QPen( self._new_options.GetColour( CC.COLOUR_MEDIA_TEXT ) ) )
            
            # repo strings
            
            remote_strings = self._current_media.GetLocationsManager().GetRemoteLocationStrings()
            
            for remote_string in remote_strings:
                
                ( text_size, remote_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, remote_string )
                
                ClientGUIFunctions.DrawText( painter, my_width - text_size.width() - 3, current_y, remote_string )
                
                current_y += text_size.height()
                
            
            # urls
            
            urls = self._current_media.GetLocationsManager().GetURLs()
            
            url_tuples = HG.client_controller.network_engine.domain_manager.ConvertURLsToMediaViewerTuples( urls )
            
            for ( display_string, url ) in url_tuples:
                
                ( text_size, display_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, display_string )
                
                ClientGUIFunctions.DrawText( painter, my_width - text_size.width() - 3, current_y, display_string )
                
                current_y += text_size.height() + 2
                
            
            # top-middle
            
            current_y = 3
            
            title_string = self._current_media.GetTitleString()
            
            if len( title_string ) > 0:
                
                ( text_size, title_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, title_string )
                
                ClientGUIFunctions.DrawText( painter, ( my_width - text_size.width() ) // 2, current_y, title_string )
                
                current_y += text_size.height() + 3
                
            
            info_string = self._GetInfoString()
            
            ( text_size, info_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, info_string )
            
            ClientGUIFunctions.DrawText( painter, ( my_width - text_size.width() ) // 2, current_y, info_string )
            
            current_y += text_size.height() + 3
            
            self._DrawAdditionalTopMiddleInfo( painter, current_y )
            
            # bottom-right index
            
            bottom_right_string = ClientData.ConvertZoomToPercentage( self._current_zoom )
            
            index_string = self._GetIndexString()
            
            if len( index_string ) > 0:
                
                bottom_right_string = '{} - {}'.format( bottom_right_string, index_string )
                
            
            ( text_size, bottom_right_string ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, bottom_right_string )
            
            ClientGUIFunctions.DrawText( painter, my_width - text_size.width() - 3, my_height - text_size.height() - 3, bottom_right_string )
            
        
    
    def _GetInfoString( self ):
        
        lines = self._current_media.GetPrettyInfoLines()
        
        lines.insert( 1, ClientData.ConvertZoomToPercentage( self._current_zoom ) )
        
        info_string = ' | '.join( lines )
        
        return info_string
        
    
    def _GetNoMediaText( self ):
        
        return 'No media to display'
        
    
    def RedrawDetails( self ):
        
        self.update()
        
    
    def TryToDoPreClose( self ):
        
        can_close = True
        
        return can_close
        
    
class CanvasWithHovers( CanvasWithDetails ):
    
    def __init__( self, parent, location_context ):
        
        CanvasWithDetails.__init__( self, parent, location_context )
        
        top_hover = self._GenerateHoverTopFrame()
        
        self._my_shortcuts_handler.AddWindowToFilter( top_hover )
        
        hover = ClientGUICanvasHoverFrames.CanvasHoverFrameTags( self, self, top_hover, self._canvas_key )
        
        self._my_shortcuts_handler.AddWindowToFilter( hover )
        
        hover = ClientGUICanvasHoverFrames.CanvasHoverFrameTopRight( self, self, top_hover, self._canvas_key )
        
        self._my_shortcuts_handler.AddWindowToFilter( hover )
        
        for name in self._new_options.GetStringList( 'default_media_viewer_custom_shortcuts' ):
            
            self._my_shortcuts_handler.AddShortcuts( name )
            
        
        #
        
        self._timer_cursor_hide_job = None
        self._last_cursor_autohide_touch_time = HydrusData.GetNowFloat()
        
        # need this as we need un-button-pressed move events for cursor hide
        self.setMouseTracking( True )
        
        self._RestartCursorHideWait()
        
        HG.client_controller.sub( self, 'CloseFromHover', 'canvas_close' )
        HG.client_controller.sub( self, 'FullscreenSwitch', 'canvas_fullscreen_switch' )
        
    
    def _GenerateHoverTopFrame( self ):
        
        raise NotImplementedError()
        
    
    def _HideCursorCheck( self ):
        
        hide_time_ms = HG.client_controller.new_options.GetNoneableInteger( 'media_viewer_cursor_autohide_time_ms' )
        
        if hide_time_ms is None:
            
            return
            
        
        hide_time = hide_time_ms / 1000
        
        can_hide = HydrusData.TimeHasPassedFloat( self._last_cursor_autohide_touch_time + hide_time )
        
        can_check_again = ClientGUIFunctions.MouseIsOverWidget( self )
        
        if not CC.CAN_HIDE_MOUSE:
            
            can_hide = False
            
        
        if CGC.core().MenuIsOpen():
            
            can_hide = False
            
        
        if ClientGUIFunctions.DialogIsOpen():
            
            can_hide = False
            
            can_check_again = False
            
        
        if can_hide:
            
            self.setCursor( QG.QCursor( QC.Qt.BlankCursor ) )
            
        elif can_check_again:
            
            self._RestartCursorHideCheckJob()
            
        
    
    def _RestartCursorHideWait( self ):
        
        self._last_cursor_autohide_touch_time = HydrusData.GetNowFloat()
        
        self._RestartCursorHideCheckJob()
        
    
    def _RestartCursorHideCheckJob( self ):
        
        if self._timer_cursor_hide_job is not None:
            
            timer_is_running_or_finished = self._timer_cursor_hide_job.CurrentlyWorking() or self._timer_cursor_hide_job.IsWorkComplete()
            
            if not timer_is_running_or_finished:
                
                return
                
            
        
        self._timer_cursor_hide_job = HG.client_controller.CallLaterQtSafe( self, 0.1, 'hide cursor check', self._HideCursorCheck )
        
    
    def _TryToCloseWindow( self ):
        
        self.window().close()
        
    
    def CloseFromHover( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._TryToCloseWindow()
            
        
    
    def FullscreenSwitch( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self.parentWidget().FullscreenSwitch()
            
        
    
    def mouseMoveEvent( self, event ):
        
        current_focus_tlw = QW.QApplication.activeWindow()
        
        my_tlw = self.window()
        
        if isinstance( current_focus_tlw, ClientGUICanvasHoverFrames.CanvasHoverFrame ) and ClientGUIFunctions.IsQtAncestor( current_focus_tlw, my_tlw, through_tlws = True ):
            
            my_tlw.activateWindow()
            
        
        #
        
        CC.CAN_HIDE_MOUSE = True
        
        # due to the mouse setPos below, the event pos can get funky I think due to out of order coordinate setting events, so we'll poll current value directly
        event_pos = self.mapFromGlobal( QG.QCursor.pos() )
        
        mouse_currently_shown = self.cursor() == QG.QCursor( QC.Qt.ArrowCursor )
        show_mouse = mouse_currently_shown
        
        is_dragging = event.buttons() & QC.Qt.LeftButton and self._last_drag_pos is not None
        has_moved = event_pos != self._last_motion_pos
        
        if is_dragging:
            
            delta = event_pos - self._last_drag_pos
            
            approx_distance = delta.manhattanLength()
            
            if approx_distance > 0:
                
                touchscreen_canvas_drags_unanchor = HG.client_controller.new_options.GetBoolean( 'touchscreen_canvas_drags_unanchor' )
                
                if not self._current_drag_is_touch and approx_distance > 50:
                    
                    # if user is able to generate such a large distance, they are almost certainly touching
                    
                    self._current_drag_is_touch = True
                    
                
                # touch events obviously don't mix with warping well. the touch just warps it back and again and we get a massive delta!
                
                touch_anchor_override = touchscreen_canvas_drags_unanchor and self._current_drag_is_touch
                anchor_and_hide_canvas_drags = HG.client_controller.new_options.GetBoolean( 'anchor_and_hide_canvas_drags' )
                
                if anchor_and_hide_canvas_drags and not touch_anchor_override:
                    
                    show_mouse = False
                    
                    global_mouse_pos = self.mapToGlobal( self._last_drag_pos )
                    
                    QG.QCursor.setPos( global_mouse_pos )
                    
                    ClientGUIShortcuts.CUMULATIVE_MOUSEWARP_MANHATTAN_LENGTH += approx_distance
                    
                else:
                    
                    show_mouse = True
                    
                    self._last_drag_pos = QC.QPoint( event_pos )
                    
                
                self._media_window_pos += delta
                
                self._DrawCurrentMedia()
                
            
        else:
            
            if has_moved:
                
                self._last_motion_pos = QC.QPoint( event_pos )
                
                show_mouse = True
                
            
        
        if show_mouse:
            
            if not mouse_currently_shown:
                
                self.setCursor( QG.QCursor( QC.Qt.ArrowCursor ) )
                
            
            self._RestartCursorHideWait()
            
        else:
            
            if mouse_currently_shown:
                
                self.setCursor( QG.QCursor( QC.Qt.BlankCursor ) )
                
            
        
        CanvasWithDetails.mouseMoveEvent( self, event )
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand, canvas_key = None ):
        
        if canvas_key is not None and canvas_key != self._canvas_key:
            
            return False
            
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_CLOSE_MEDIA_VIEWER:
                
                self._TryToCloseWindow()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = CanvasWithDetails.ProcessApplicationCommand( self, command )
            
        
        return command_processed
        
    
class CanvasFilterDuplicates( CanvasWithHovers ):
    
    CANVAS_TYPE = CC.CANVAS_MEDIA_VIEWER_DUPLICATES
    
    def __init__( self, parent, file_search_context: ClientSearch.FileSearchContext, both_files_match, pixel_dupes_preference, max_hamming_distance ):
        
        location_context = file_search_context.GetLocationContext()
        
        CanvasWithHovers.__init__( self, parent, location_context )
        
        hover = ClientGUICanvasHoverFrames.CanvasHoverFrameRightDuplicates( self, self, self._canvas_key )
        
        self._my_shortcuts_handler.AddWindowToFilter( hover )
        
        self._file_search_context = file_search_context
        self._both_files_match = both_files_match
        self._pixel_dupes_preference = pixel_dupes_preference
        self._max_hamming_distance = max_hamming_distance
        
        self._maintain_pan_and_zoom = True
        
        self._currently_fetching_pairs = False
        
        self._unprocessed_pairs = []
        self._current_pair = None
        self._processed_pairs = []
        self._hashes_due_to_be_deleted_in_this_batch = set()
        
        # ok we started excluding pairs if they had been deleted, now I am extending it to any files that have been processed.
        # main thing is if you have AB, AC, that's neat and a bunch of people want it, but current processing system doesn't do B->A->C merge if it happens in a single batch
        # I need to store dupe merge options rather than content updates apply them in db transaction or do the retroactive sync or similar to get this done properly
        # so regrettably I turn it off for now
        
        self._hashes_processed_in_this_batch = set()
        
        self._media_list = ClientMedia.ListeningMediaList( location_context, [] )
        
        self._my_shortcuts_handler.AddShortcuts( 'media_viewer_browser' )
        self._my_shortcuts_handler.AddShortcuts( 'duplicate_filter' )
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HG.client_controller.sub( self, 'Delete', 'canvas_delete' )
        HG.client_controller.sub( self, 'Undelete', 'canvas_undelete' )
        HG.client_controller.sub( self, 'SwitchMedia', 'canvas_show_next' )
        HG.client_controller.sub( self, 'SwitchMedia', 'canvas_show_previous' )
        
        QP.CallAfter( self._ShowNewPair )
        
    
    def _CommitProcessed( self, blocking = True ):
        
        pair_info = []
        
        for ( hash_pair, duplicate_type, first_media, second_media, service_keys_to_content_updates, was_auto_skipped ) in self._processed_pairs:
            
            if duplicate_type is None or was_auto_skipped:
                
                continue # it was a 'skip' decision
                
            
            first_hash = first_media.GetHash()
            second_hash = second_media.GetHash()
            
            pair_info.append( ( duplicate_type, first_hash, second_hash, service_keys_to_content_updates ) )
            
        
        if len( pair_info ) > 0:
            
            if blocking:
                
                HG.client_controller.WriteSynchronous( 'duplicate_pair_status', pair_info )
                
            else:
                
                HG.client_controller.Write( 'duplicate_pair_status', pair_info )
                
            
        
        self._processed_pairs = []
        self._hashes_due_to_be_deleted_in_this_batch = set()
        self._hashes_processed_in_this_batch = set()
        
    
    def _CurrentMediaIsBetter( self, delete_second = True ):
        
        self._ProcessPair( HC.DUPLICATE_BETTER, delete_second = delete_second )
        
    
    def _Delete( self, media = None, reason = None, file_service_key = None ):
        
        if self._current_media is None:
            
            return
            
        
        text = 'Delete just this file, or both?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'delete just this one', 'current' ) )
        yes_tuples.append( ( 'delete both', 'both' ) )
        
        with ClientGUIDialogs.DialogYesYesNo( self, text, yes_tuples = yes_tuples, no_label = 'forget it' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                value = dlg.GetValue()
                
                if value == 'current':
                    
                    media = [ self._current_media ]
                    
                    default_reason = 'Deleted manually in Duplicate Filter.'
                    
                elif value == 'both':
                    
                    media = [ self._current_media, self._media_list.GetNext( self._current_media ) ]
                    
                    default_reason = 'Deleted manually in Duplicate Filter, along with its potential duplicate.'
                    
                else:
                    
                    return False
                    
                
            else:
                
                return False
                
            
        
        deleted = CanvasWithHovers._Delete( self, media = media, default_reason = default_reason, file_service_key = file_service_key )
        
        if deleted:
            
            self._SkipPair()
            
        
        return True
        
    
    def _DoCustomAction( self ):
        
        if self._current_media is None:
            
            return
            
        
        duplicate_types = [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY, HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE ]
        
        choice_tuples = [ ( HC.duplicate_type_string_lookup[ duplicate_type ], duplicate_type ) for duplicate_type in duplicate_types ]
        
        try:
            
            duplicate_type = ClientGUIDialogsQuick.SelectFromList( self, 'select duplicate type', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        new_options = HG.client_controller.new_options
        
        if duplicate_type in [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ] or ( new_options.GetBoolean( 'advanced_mode' ) and duplicate_type == HC.DUPLICATE_ALTERNATE ):
            
            duplicate_action_options = new_options.GetDuplicateActionOptions( duplicate_type )
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit duplicate merge options' ) as dlg_2:
                
                panel = ClientGUIScrolledPanelsEdit.EditDuplicateActionOptionsPanel( dlg_2, duplicate_type, duplicate_action_options, for_custom_action = True )
                
                dlg_2.SetPanel( panel )
                
                if dlg_2.exec() == QW.QDialog.Accepted:
                    
                    duplicate_action_options = panel.GetValue()
                    
                else:
                    
                    return
                    
                
            
        else:
            
            duplicate_action_options = None
            
        
        text = 'Delete any of the files?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'delete neither', 'delete_neither' ) )
        yes_tuples.append( ( 'delete this one', 'delete_first' ) )
        yes_tuples.append( ( 'delete the other', 'delete_second' ) )
        yes_tuples.append( ( 'delete both', 'delete_both' ) )
        
        delete_first = False
        delete_second = False
        delete_both = False
        
        with ClientGUIDialogs.DialogYesYesNo( self, text, yes_tuples = yes_tuples, no_label = 'forget it' ) as dlg:
            
            result = dlg.exec()
            
            if result == QW.QDialog.Accepted:
                
                value = dlg.GetValue()
                
                if value == 'delete_first':
                    
                    delete_first = True
                    
                elif value == 'delete_second':
                    
                    delete_second = True
                    
                elif value == 'delete_both':
                    
                    delete_both = True
                    
                
            else:
                
                return
                
            
        
        self._ProcessPair( duplicate_type, delete_first = delete_first, delete_second = delete_second, delete_both = delete_both, duplicate_action_options = duplicate_action_options )
        
    
    def _DrawBackgroundDetails( self, painter ):
        
        if self._currently_fetching_pairs:
            
            text = 'Loading pairs\u2026'
            
            ( text_size, text ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, text )
            
            my_size = self.size()
            
            x = ( my_size.width() - text_size.width() ) // 2
            y = ( my_size.height() - text_size.height() ) // 2
            
            ClientGUIFunctions.DrawText( painter, x, y, text )
            
        else:
            
            CanvasWithHovers._DrawBackgroundDetails( self, painter )
            
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUICanvasHoverFrames.CanvasHoverFrameTopDuplicatesFilter( self, self, self._canvas_key )
        
    
    def _GetBackgroundColour( self ):
        
        normal_colour = self._new_options.GetColour( CC.COLOUR_MEDIA_BACKGROUND )
        
        if self._current_media is None or len( self._media_list ) == 0:
            
            return normal_colour
            
        else:
            
            if self._current_media == self._media_list.GetFirst():
                
                return normal_colour
                
            else:
                
                new_options = HG.client_controller.new_options
                
                duplicate_intensity = new_options.GetNoneableInteger( 'duplicate_background_switch_intensity' )
                
                return ClientGUIFunctions.GetLighterDarkerColour( normal_colour, duplicate_intensity )
                
            
        
    
    def _GetIndexString( self ):
        
        if self._current_media is None or len( self._media_list ) == 0:
            
            return '-'
            
        else:
            
            progress = len( self._processed_pairs ) + 1 # +1 here actually counts for the one currently displayed
            total = progress + len( self._unprocessed_pairs )
            
            index_string = HydrusData.ConvertValueRangeToPrettyString( progress, total )
            
            if self._current_media == self._media_list.GetFirst():
                
                return 'A - ' + index_string
                
            else:
                
                return 'B - ' + index_string
                
            
        
    
    def _GetNoMediaText( self ):
        
        return 'Looking for pairs to compare--please wait.'
        
    
    def _GetNumCommittableDecisions( self ):
        
        return len( [ 1 for ( hash_pair, duplicate_type, first_media, second_media, service_keys_to_content_updates, was_auto_skipped ) in self._processed_pairs if duplicate_type is not None and not was_auto_skipped ] )
        
    
    def _GoBack( self ):
        
        if len( self._processed_pairs ) > 0 and self._GetNumCommittableDecisions() > 0:
            
            self._unprocessed_pairs.append( self._current_pair )
            
            ( hash_pair, duplicate_type, first_media, second_media, service_keys_to_content_updates, was_auto_skipped ) = self._processed_pairs.pop()
            
            self._unprocessed_pairs.append( hash_pair )
            
            while was_auto_skipped:
                
                if len( self._processed_pairs ) == 0:
                    
                    QW.QMessageBox.critical( self, 'Error', 'Due to an unexpected series of events (likely a series of file deletes), the duplicate filter has no valid pair to back up to. It will now close.' )
                    
                    self.window().deleteLater()
                    
                    return
                    
                
                ( hash_pair, duplicate_type, first_media, second_media, service_keys_to_content_updates, was_auto_skipped ) = self._processed_pairs.pop()
                
                self._unprocessed_pairs.append( hash_pair )
                
            
            self._hashes_due_to_be_deleted_in_this_batch.difference_update( hash_pair )
            self._hashes_processed_in_this_batch.difference_update( hash_pair )
            
            self._ShowNewPair()
            
        
    
    def _MediaAreAlternates( self ):
        
        self._ProcessPair( HC.DUPLICATE_ALTERNATE )
        
    
    def _MediaAreFalsePositive( self ):
        
        self._ProcessPair( HC.DUPLICATE_FALSE_POSITIVE )
        
    
    def _MediaAreTheSame( self ):
        
        self._ProcessPair( HC.DUPLICATE_SAME_QUALITY )
        
    
    def _ProcessPair( self, duplicate_type, delete_first = False, delete_second = False, delete_both = False, duplicate_action_options = None ):
        
        if self._current_media is None:
            
            return
            
        
        if duplicate_action_options is None:
            
            if duplicate_type in [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ] or ( HG.client_controller.new_options.GetBoolean( 'advanced_mode' ) and duplicate_type == HC.DUPLICATE_ALTERNATE ):
                
                new_options = HG.client_controller.new_options
                
                duplicate_action_options = new_options.GetDuplicateActionOptions( duplicate_type )
                
            else:
                
                duplicate_action_options = ClientDuplicates.DuplicateActionOptions()
                
            
        
        first_media = self._current_media
        second_media = self._media_list.GetNext( first_media )
        
        was_auto_skipped = False
        
        self._hashes_processed_in_this_batch.update( first_media.GetHashes() )
        self._hashes_processed_in_this_batch.update( second_media.GetHashes() )
        
        if delete_first or delete_second or delete_both:
            
            if delete_first or delete_both:
                
                self._hashes_due_to_be_deleted_in_this_batch.update( first_media.GetHashes() )
                
            
            if delete_second or delete_both:
                
                self._hashes_due_to_be_deleted_in_this_batch.update( second_media.GetHashes() )
                
            
            if duplicate_type in ( HC.DUPLICATE_BETTER, HC.DUPLICATE_WORSE ):
                
                file_deletion_reason = 'better/worse'
                
                if delete_second:
                    
                    file_deletion_reason += ', worse file deleted'
                    
                
            else:
                
                file_deletion_reason = HC.duplicate_type_string_lookup[ duplicate_type ]
                
            
            if delete_both:
                
                file_deletion_reason += ', both files deleted'
                
            
            file_deletion_reason = 'Deleted in Duplicate Filter ({}).'.format( file_deletion_reason )
            
        else:
            
            file_deletion_reason = None
            
        
        service_keys_to_content_updates = duplicate_action_options.ProcessPairIntoContentUpdates( first_media, second_media, delete_first = delete_first, delete_second = delete_second, delete_both = delete_both, file_deletion_reason = file_deletion_reason )
        
        self._processed_pairs.append( ( self._current_pair, duplicate_type, first_media, second_media, service_keys_to_content_updates, was_auto_skipped ) )
        
        self._ShowNewPair()
        
    
    def _ShowNewPair( self ):
        
        if self._currently_fetching_pairs:
            
            return
            
        
        # hackery dackery doo to quick solve something that is calling this a bunch of times while the 'and continue?' dialog is open, making like 16 of them
        # a full rewrite is needed on this awful workflow
        
        tlws = QW.QApplication.topLevelWidgets()
        
        for tlw in tlws:
            
            if isinstance( tlw, ClientGUITopLevelWindowsPanels.DialogCustomButtonQuestion ) and tlw.isModal():
                
                return
                
            
        
        #
        
        num_committable = self._GetNumCommittableDecisions()
        
        if len( self._unprocessed_pairs ) == 0 and num_committable > 0:
            
            label = 'commit ' + HydrusData.ToHumanInt( num_committable ) + ' decisions and continue?'
            
            result = ClientGUIDialogsQuick.GetInterstitialFilteringAnswer( self, label )
            
            if result == QW.QDialog.Accepted:
                
                self._CommitProcessed( blocking = True )
                
            else:
                
                ( hash_pair, duplicate_type, first_media, second_media, service_keys_to_content_updates, was_auto_skipped ) = self._processed_pairs.pop()
                
                self._unprocessed_pairs.append( hash_pair )
                
                while was_auto_skipped:
                    
                    if len( self._processed_pairs ) == 0:
                        
                        HG.client_controller.pub( 'new_similar_files_potentials_search_numbers' )
                        
                        QW.QMessageBox.critical( self, 'Error', 'Due to an unexpected series of events (likely a series of file deletes), the duplicate filter has no valid pair to back up to. It will now close.' )
                        
                        self.window().deleteLater()
                        
                        return
                        
                    
                    ( hash_pair, duplicate_type, first_media, second_media, service_keys_to_content_updates, was_auto_skipped ) = self._processed_pairs.pop()
                    
                    self._unprocessed_pairs.append( hash_pair )
                    
                
                self._hashes_due_to_be_deleted_in_this_batch.difference_update( hash_pair )
                self._hashes_processed_in_this_batch.difference_update( hash_pair )
                
            
        
        if len( self._unprocessed_pairs ) == 0:
            
            self._hashes_due_to_be_deleted_in_this_batch = set()
            self._hashes_processed_in_this_batch = set()
            self._processed_pairs = [] # just in case someone 'skip'ed everything in the last batch, so this never got cleared above
            
            self.ClearMedia()
            
            self._media_list = ClientMedia.ListeningMediaList( self._location_context, [] )
            
            self._currently_fetching_pairs = True
            
            HG.client_controller.CallToThread( self.THREADFetchPairs, self._file_search_context, self._both_files_match, self._pixel_dupes_preference, self._max_hamming_distance )
            
            self.update()
            
        else:
            
            def pair_is_good( pair ):
                
                ( first_hash, second_hash ) = pair
                
                if first_hash in self._hashes_processed_in_this_batch or second_hash in self._hashes_processed_in_this_batch:
                    
                    return False
                    
                
                if first_hash in self._hashes_due_to_be_deleted_in_this_batch or second_hash in self._hashes_due_to_be_deleted_in_this_batch:
                    
                    return False
                    
                
                ( first_media_result, second_media_result ) = HG.client_controller.Read( 'media_results', pair )
                
                first_media = ClientMedia.MediaSingleton( first_media_result )
                second_media = ClientMedia.MediaSingleton( second_media_result )
                
                if not self._CanDisplayMedia( first_media ) or not self._CanDisplayMedia( second_media ):
                    
                    return False
                    
                
                return True
                
            
            potential_pair = self._unprocessed_pairs.pop()
            
            while not pair_is_good( potential_pair ):
                
                was_auto_skipped = True
                
                self._processed_pairs.append( ( potential_pair, None, None, None, {}, was_auto_skipped ) )
                
                if len( self._unprocessed_pairs ) == 0:
                    
                    if len( self._processed_pairs ) == 0:
                        
                        HG.client_controller.pub( 'new_similar_files_potentials_search_numbers' )
                        
                        QW.QMessageBox.critical( self, 'Error', 'It seems an entire batch of pairs were unable to be displayed. The duplicate filter will now close.' )
                        
                        self.window().deleteLater()
                        
                        return
                        
                    else:
                        
                        self._ShowNewPair() # there are no useful decisions left in the queue, so let's reset
                        
                        return
                        
                    
                
                potential_pair = self._unprocessed_pairs.pop()
                
            
            self._current_pair = potential_pair
            
            ( first_media_result, second_media_result ) = HG.client_controller.Read( 'media_results', self._current_pair )
            
            if not ( first_media_result.GetLocationsManager().IsLocal() and second_media_result.GetLocationsManager().IsLocal() ):
                
                QW.QMessageBox.warning( self, 'Warning', 'At least one of the potential files in this pair was not in this client. Likely it was very recently deleted through a different process. Your decisions until now will be saved, and then the duplicate filter will close.' )
                
                self._CommitProcessed( blocking = True )
                
                HG.client_controller.pub( 'new_similar_files_potentials_search_numbers' )
                
                self._TryToCloseWindow()
                
                return
                
            
            first_media = ClientMedia.MediaSingleton( first_media_result )
            second_media = ClientMedia.MediaSingleton( second_media_result )
            
            score = ClientMedia.GetDuplicateComparisonScore( first_media, second_media )
            
            if score > 0:
                
                media_results_with_better_first = ( first_media_result, second_media_result )
                
            else:
                
                media_results_with_better_first = ( second_media_result, first_media_result )
                
            
            self._media_list = ClientMedia.ListeningMediaList( self._location_context, media_results_with_better_first )
            
            # reset zoom gubbins
            self.SetMedia( None )
            
            self.SetMedia( self._media_list.GetFirst() )

            self._media_container.hide()
            
            self._ReinitZoom()
            
            self._ResetMediaWindowCenterPosition()
            
            self._SizeAndPositionMediaContainer()
            
            self._media_container.show()
            
        
    
    def _SkipPair( self ):
        
        if self._current_media is None:
            
            return
            
        
        was_auto_skipped = False
        
        self._processed_pairs.append( ( self._current_pair, None, None, None, {}, was_auto_skipped ) )
        
        self._ShowNewPair()
        
    
    def _SwitchMedia( self ):
        
        if self._current_media is not None:
            
            try:
                
                other_media = self._media_list.GetNext( self._current_media )
                
                self.SetMedia( other_media )
                
            except HydrusExceptions.DataMissing:
                
                return
                
            
        
    
    def Archive( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Archive()
            
        
    
    def CleanBeforeDestroy( self ):
        
        HG.client_controller.pub( 'new_similar_files_potentials_search_numbers' )
        
        ClientMedia.hashes_to_jpeg_quality = {} # clear the cache
        ClientMedia.hashes_to_pixel_hashes = {} # clear the cache
        
        CanvasWithHovers.CleanBeforeDestroy( self )
        
    
    def Delete( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Delete()
            
        
    
    def Inbox( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Inbox()
            
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand, canvas_key = None ):
        
        if canvas_key is not None and canvas_key != self._canvas_key:
            
            return False
            
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_AND_DELETE_OTHER:
                
                self._CurrentMediaIsBetter( delete_second = True )
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_BUT_KEEP_BOTH:
                
                self._CurrentMediaIsBetter( delete_second = False )
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_EXACTLY_THE_SAME:
                
                self._MediaAreTheSame()
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_ALTERNATES:
                
                self._MediaAreAlternates()
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_FALSE_POSITIVE:
                
                self._MediaAreFalsePositive()
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_CUSTOM_ACTION:
                
                self._DoCustomAction()
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_SKIP:
                
                self._SkipPair()
                
            elif action == CAC.SIMPLE_DUPLICATE_FILTER_BACK:
                
                self._GoBack()
                
            elif action in ( CAC.SIMPLE_VIEW_FIRST, CAC.SIMPLE_VIEW_LAST, CAC.SIMPLE_VIEW_PREVIOUS, CAC.SIMPLE_VIEW_NEXT ):
                
                self._SwitchMedia()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = CanvasWithHovers.ProcessApplicationCommand( self, command )
            
        
        return command_processed
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        def catch_up():
            
            # ugly, but it will do for now
            
            if len( self._media_list ) < 2:
                
                self._ShowNewPair()
                
            else:
                
                self.update()
                
            
        
        HG.client_controller.CallLaterQtSafe( self, 0.1, 'duplicates filter post-processing wait', catch_up )
        
    
    def SetMedia( self, media ):
        
        CanvasWithHovers.SetMedia( self, media )
        
        if media is not None:
            
            shown_media = self._current_media
            comparison_media = self._media_list.GetNext( shown_media )
            
            if shown_media != comparison_media:
                
                HG.client_controller.pub( 'canvas_new_duplicate_pair', self._canvas_key, shown_media, comparison_media )
                
            
        
    
    def SwitchMedia( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._SwitchMedia()
            
        
    
    def TryToDoPreClose( self ):
        
        num_committable = self._GetNumCommittableDecisions()
        
        if num_committable > 0:
            
            label = 'commit ' + HydrusData.ToHumanInt( num_committable ) + ' decisions?'
            
            ( result, cancelled ) = ClientGUIDialogsQuick.GetFinishFilteringAnswer( self, label )
            
            if cancelled:
                
                close_was_triggered_by_everything_being_processed = len( self._unprocessed_pairs ) == 0
                
                if close_was_triggered_by_everything_being_processed:
                    
                    self._GoBack()
                    
                
                return False
                
            elif result == QW.QDialog.Accepted:
                
                self._CommitProcessed( blocking = False )
                
            
        
        return CanvasWithHovers.TryToDoPreClose( self )
        
    
    def Undelete( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Undelete()
            
        
    
    def THREADFetchPairs( self, file_search_context, both_files_match, pixel_dupes_preference, max_hamming_distance ):
        
        def qt_close():
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            QW.QMessageBox.information( self, 'Information', 'All pairs have been filtered!' )
            
            self._TryToCloseWindow()
            
        
        def qt_continue( unprocessed_pairs ):
            
            if not self or not QP.isValid( self):
                
                return
                
            
            self._unprocessed_pairs = unprocessed_pairs
            
            self._currently_fetching_pairs = False
            
            self._ShowNewPair()
            
        
        result = HG.client_controller.Read( 'duplicate_pairs_for_filtering', file_search_context, both_files_match, pixel_dupes_preference, max_hamming_distance )
        
        if len( result ) == 0:
            
            QP.CallAfter( qt_close )
            
        else:
            
            QP.CallAfter( qt_continue, result )
            
        
    
class CanvasMediaList( ClientMedia.ListeningMediaList, CanvasWithHovers ):
    
    exitFocusMedia = QC.Signal( ClientMedia.Media )
    
    def __init__( self, parent, page_key, location_context: ClientLocation.LocationContext, media_results ):
        
        CanvasWithHovers.__init__( self, parent, location_context )
        ClientMedia.ListeningMediaList.__init__( self, location_context, media_results )
        
        self._page_key = page_key
        
        self._just_started = True
        
    
    def TryToDoPreClose( self ):
        
        if self._current_media is not None:
            
            self.exitFocusMedia.emit( self._current_media )
            
        
        return CanvasWithHovers.TryToDoPreClose( self )
        
    
    def _GenerateHoverTopFrame( self ):
        
        raise NotImplementedError()
        
    
    def _GetIndexString( self ):
        
        if self._current_media is None:
            
            index_string = '-/' + HydrusData.ToHumanInt( len( self._sorted_media ) )
            
        else:
            
            index_string = HydrusData.ConvertValueRangeToPrettyString( self._sorted_media.index( self._current_media ) + 1, len( self._sorted_media ) )
            
        
        return index_string
        
    
    def _PrefetchNeighbours( self ):
        
        media_looked_at = set()
        
        to_render = []
        
        previous = self._current_media
        next = self._current_media
        
        delay_base = HG.client_controller.new_options.GetInteger( 'media_viewer_prefetch_delay_base_ms' ) / 1000
        
        num_to_go_back = HG.client_controller.new_options.GetInteger( 'media_viewer_prefetch_num_previous' )
        num_to_go_forward = HG.client_controller.new_options.GetInteger( 'media_viewer_prefetch_num_next' )
        
        # if media_looked_at nukes the list, we want shorter delays, so do next first
        
        for i in range( num_to_go_forward ):
            
            next = self._GetNext( next )
            
            if next in media_looked_at:
                
                break
                
            else:
                
                media_looked_at.add( next )
                
            
            delay = delay_base * ( i + 1 )
            
            to_render.append( ( next, delay ) )
            
        
        for i in range( num_to_go_back ):
            
            previous = self._GetPrevious( previous )
            
            if previous in media_looked_at:
                
                break
                
            else:
                
                media_looked_at.add( previous )
                
            
            delay = delay_base * 2 * ( i + 1 )
            
            to_render.append( ( previous, delay ) )
            
        
        image_cache = HG.client_controller.GetCache( 'images' )
        
        for ( media, delay ) in to_render:
            
            hash = media.GetHash()
            mime = media.GetMime()
            
            if media.IsStaticImage():
                
                if not image_cache.HasImageRenderer( hash ):
                    
                    # we do qt safe to make sure the job is cancelled if we are destroyed
                    
                    HG.client_controller.CallLaterQtSafe( self, delay, 'image pre-fetch', image_cache.PrefetchImageRenderer, media )
                    
                
            
        
    
    def _Remove( self ):
        
        next_media = self._GetNext( self._current_media )
        
        if next_media == self._current_media:
            
            next_media = None
            
        
        hashes = { self._current_media.GetHash() }
        
        HG.client_controller.pub( 'remove_media', self._page_key, hashes )
        
        singleton_media = { self._current_media }
        
        ClientMedia.ListeningMediaList._RemoveMediaDirectly( self, singleton_media, {} )
        
        if self.HasNoMedia():
            
            self._TryToCloseWindow()
            
        elif self.HasMedia( self._current_media ):
            
            HG.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self.update()
            
        else:
            
            self.SetMedia( next_media )
            
        
    
    def _ShowFirst( self ):
        
        self.SetMedia( self._GetFirst() )
        
    
    def _ShowLast( self ):
        
        self.SetMedia( self._GetLast() )
        
    
    def _ShowNext( self ):
        
        self.SetMedia( self._GetNext( self._current_media ) )
        
    
    def _ShowPrevious( self ):
        
        self.SetMedia( self._GetPrevious( self._current_media ) )
        
    
    def _StartSlideshow( self, interval ):
        
        pass
        
    
    def AddMediaResults( self, page_key, media_results ):
        
        if page_key == self._page_key:
            
            ClientMedia.ListeningMediaList.AddMediaResults( self, media_results )
            
            HG.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self.update()
            
        
    
    def EventFullscreenSwitch( self, event ):
        
        self.parentWidget().FullscreenSwitch()
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is None:
            
            # probably a file view stats update as we close down--ignore it
            
            return
            
        
        if self.HasMedia( self._current_media ):
            
            next_media = self._GetNext( self._current_media )
            
            if next_media == self._current_media:
                
                next_media = None
                
            
        else:
            
            next_media = None
            
        
        ClientMedia.ListeningMediaList.ProcessContentUpdates( self, service_keys_to_content_updates )
        
        if self.HasNoMedia():
            
            self._TryToCloseWindow()
            
        elif self.HasMedia( self._current_media ):
            
            HG.client_controller.pub( 'canvas_new_index_string', self._canvas_key, self._GetIndexString() )
            
            self.update()
            
        elif self.HasMedia( next_media ):
            
            self.SetMedia( next_media )
            
        else:
            
            self.SetMedia( self._GetFirst() )
            
        
    
def CommitArchiveDelete( page_key, kept_hashes, deleted_hashes ):
    
    if HC.options[ 'remove_filtered_files' ]:
        
        all_hashes = set()
        
        all_hashes.update( deleted_hashes )
        all_hashes.update( kept_hashes )
        
        HG.client_controller.pub( 'remove_media', page_key, all_hashes )
        
    
    if not isinstance( deleted_hashes, list ):
        
        deleted_hashes = list( deleted_hashes )
        
    
    if not isinstance( kept_hashes, list ):
        
        kept_hashes = list( kept_hashes )
        
    
    # we do a second set of removes to deal with late processing and a quick F5ing user
    
    for block_of_deleted_hashes in HydrusData.SplitListIntoChunks( deleted_hashes, 64 ):
        
        service_keys_to_content_updates = {}
        
        reason = 'Deleted in Archive/Delete filter.'
        
        service_keys_to_content_updates[ CC.LOCAL_FILE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, block_of_deleted_hashes, reason = reason ) ]
        
        HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
        
        if HC.options[ 'remove_filtered_files' ]:
            
            HG.client_controller.pub( 'remove_media', page_key, block_of_deleted_hashes )
            
        
        HG.client_controller.WaitUntilViewFree()
        
    
    for block_of_kept_hashes in HydrusData.SplitListIntoChunks( kept_hashes, 64 ):
        
        service_keys_to_content_updates = {}
        
        service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, block_of_kept_hashes ) ]
        
        HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
        
        if HC.options[ 'remove_filtered_files' ]:
            
            HG.client_controller.pub( 'remove_media', page_key, block_of_kept_hashes )
            
        
        HG.client_controller.WaitUntilViewFree()
        
    
class CanvasMediaListFilterArchiveDelete( CanvasMediaList ):
    
    def __init__( self, parent, page_key, location_context: ClientLocation.LocationContext, media_results ):
        
        CanvasMediaList.__init__( self, parent, page_key, location_context, media_results )
        
        self._my_shortcuts_handler.AddShortcuts( 'archive_delete_filter' )
        
        self._kept = set()
        self._deleted = set()
        
        HG.client_controller.sub( self, 'Delete', 'canvas_delete' )
        HG.client_controller.sub( self, 'Undelete', 'canvas_undelete' )
        
        first_media = self._GetFirst()
        
        if first_media is not None:
            
            QP.CallAfter( self.SetMedia, first_media ) # don't set this until we have a size > (20, 20)!
            
        
    
    def _Back( self ):
        
        if self._current_media == self._GetFirst():
            
            return
            
        else:
            
            self._ShowPrevious()
            
            self._kept.discard( self._current_media )
            self._deleted.discard( self._current_media )
            
        
    
    def TryToDoPreClose( self ):
        
        kept_hashes = [ media.GetHash() for media in self._kept ]
        
        delete_lock_for_archived_files = HG.client_controller.new_options.GetBoolean( 'delete_lock_for_archived_files' )
        
        if delete_lock_for_archived_files:
            
            deleted_hashes = [ media.GetHash() for media in self._deleted if not media.HasArchive() ]
            
        else:
            
            deleted_hashes = [ media.GetHash() for media in self._deleted ]
            
        
        if len( kept_hashes ) > 0 or len( deleted_hashes ) > 0:
            
            label = 'keep ' + HydrusData.ToHumanInt( len( self._kept ) ) + ' and delete ' + HydrusData.ToHumanInt( len( self._deleted ) ) + ' files?'
            
            ( result, cancelled ) = ClientGUIDialogsQuick.GetFinishFilteringAnswer( self, label )
            
            if cancelled:
                
                if self._current_media in self._kept:
                    
                    self._kept.remove( self._current_media )
                    
                
                if self._current_media in self._deleted:
                    
                    self._deleted.remove( self._current_media )
                    
                
                return False
                
            elif result == QW.QDialog.Accepted:
                
                self._kept = set()
                self._deleted = set()
                
                self._current_media = self._GetFirst() # so the pubsub on close is better
                
                HG.client_controller.CallToThread( CommitArchiveDelete, self._page_key, kept_hashes, deleted_hashes )
                
            
        
        return CanvasMediaList.TryToDoPreClose( self )
        
    
    def _Delete( self, media = None, reason = None, file_service_key = None ):
        
        if self._current_media is None:
            
            return False
            
        
        self._deleted.add( self._current_media )
        
        if self._current_media == self._GetLast():
            
            self._TryToCloseWindow()
            
        else:
            
            self._ShowNext()
            
        
        return True
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUICanvasHoverFrames.CanvasHoverFrameTopArchiveDeleteFilter( self, self, self._canvas_key )
        
    
    def _Keep( self ):
        
        self._kept.add( self._current_media )
        
        if self._current_media == self._GetLast():
            
            self._TryToCloseWindow()
            
        else:
            
            self._ShowNext()
            
        
    
    def _Skip( self ):
        
        if self._current_media == self._GetLast():
            
            self._TryToCloseWindow()
            
        else:
            
            self._ShowNext()
            
        
    
    def Keep( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Keep()
            
        
    
    def Back( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Back()
            
        
    
    def Delete( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Delete()
            
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand, canvas_key = None ):
        
        if canvas_key is not None and canvas_key != self._canvas_key:
            
            return False
            
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action in ( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_KEEP, CAC.SIMPLE_ARCHIVE_FILE ):
                
                self._Keep()
                
            elif action in ( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_DELETE, CAC.SIMPLE_DELETE_FILE ):
                
                self._Delete()
                
            elif action == CAC.SIMPLE_ARCHIVE_DELETE_FILTER_SKIP:
                
                self._Skip()
                
            elif action == CAC.SIMPLE_ARCHIVE_DELETE_FILTER_BACK:
                
                self._Back()
                
            elif action == CAC.SIMPLE_LAUNCH_THE_ARCHIVE_DELETE_FILTER:
                
                self._TryToCloseWindow()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = CanvasMediaList.ProcessApplicationCommand( self, command )
            
        
        return command_processed
        
    
    def Skip( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Skip()
            
        
    
    def Undelete( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Undelete()
            
        
    
class CanvasMediaListNavigable( CanvasMediaList ):
    
    def __init__( self, parent, page_key, location_context: ClientLocation.LocationContext, media_results ):
        
        CanvasMediaList.__init__( self, parent, page_key, location_context, media_results )
        
        self._my_shortcuts_handler.AddShortcuts( 'media_viewer_browser' )
        
        HG.client_controller.sub( self, 'Delete', 'canvas_delete' )
        HG.client_controller.sub( self, 'ShowNext', 'canvas_show_next' )
        HG.client_controller.sub( self, 'ShowPrevious', 'canvas_show_previous' )
        HG.client_controller.sub( self, 'Undelete', 'canvas_undelete' )
        
    
    def _GenerateHoverTopFrame( self ):
        
        return ClientGUICanvasHoverFrames.CanvasHoverFrameTopNavigableList( self, self, self._canvas_key )
        
    
    def Archive( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Archive()
            
        
    
    def Delete( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Delete()
            
        
    
    def Inbox( self, canvas_key ):
        
        if self._canvas_key == canvas_key:
            
            self._Inbox()
            
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand, canvas_key = None ):
        
        if canvas_key is not None and canvas_key != self._canvas_key:
            
            return False
            
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_REMOVE_FILE_FROM_VIEW:
                
                self._Remove()
                
            elif action == CAC.SIMPLE_VIEW_FIRST:
                
                self._ShowFirst()
                
            elif action == CAC.SIMPLE_VIEW_LAST:
                
                self._ShowLast()
                
            elif action == CAC.SIMPLE_VIEW_PREVIOUS:
                
                self._ShowPrevious()
                
            elif action == CAC.SIMPLE_VIEW_NEXT:
                
                self._ShowNext()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = CanvasMediaList.ProcessApplicationCommand( self, command )
            
        
        return command_processed
        
    
    def ShowFirst( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ShowFirst()
            
        
    
    def ShowLast( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ShowLast()
            
        
    
    def ShowNext( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ShowNext()
            
        
    
    def ShowPrevious( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._ShowPrevious()
            
        
    
    def Undelete( self, canvas_key ):
        
        if canvas_key == self._canvas_key:
            
            self._Undelete()
            
        
    
class CanvasMediaListBrowser( CanvasMediaListNavigable ):
    
    def __init__( self, parent, page_key, location_context: ClientLocation.LocationContext, media_results, first_hash ):
        
        CanvasMediaListNavigable.__init__( self, parent, page_key, location_context, media_results )
        
        self._timer_slideshow_job = None
        self._timer_slideshow_interval = 0
        
        if first_hash is None:
            
            first_media = self._GetFirst()
            
        else:
            
            try:
                
                first_media = self._GetMedia( { first_hash } )[0]
                
            except:
                
                first_media = self._GetFirst()
                
            
        
        if first_media is not None:
            
            QP.CallAfter( self.SetMedia, first_media ) # don't set this until we have a size > (20, 20)!
            
        
        HG.client_controller.sub( self, 'AddMediaResults', 'add_media_results' )
        
    
    def _PausePlaySlideshow( self ):
        
        if self._RunningSlideshow():
            
            self._StopSlideshow()
            
        elif self._timer_slideshow_interval > 0:
            
            self._StartSlideshow( self._timer_slideshow_interval )
            
        
    
    def _RunningSlideshow( self ):
        
        return self._timer_slideshow_job is not None
        
    
    def _StartSlideshow( self, interval = None ):
        
        self._StopSlideshow()
        
        if interval is None:
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Enter the interval, in seconds.', default = '15', min_char_width = 12 ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    try:
                        
                        interval = float( dlg.GetValue() )
                        
                    except:
                        
                        return
                        
                    
                else:
                    
                    return
                    
                
            
        
        if interval > 0:
            
            self._timer_slideshow_interval = interval
            
            self._timer_slideshow_job = HG.client_controller.CallLaterQtSafe( self, self._timer_slideshow_interval, 'slideshow', self.DoSlideshow )
            
        
    
    def _StopSlideshow( self ):
        
        if self._RunningSlideshow():
            
            self._timer_slideshow_job.Cancel()
            
            self._timer_slideshow_job = None
            
            self._media_container.StopForSlideshow( False )
            
        
    
    def DoSlideshow( self ):
        
        try:
            
            # we are due for a slideshow change, so tell movie to stop for it once it has played once through
            # if short movie, it has prob played through a lot and will shift immediately
            # if longer movie, it has prob not played through but will now stop when it has and wait for us to change it then
            self._media_container.StopForSlideshow( True )
            
            if self._current_media is not None and self._RunningSlideshow():
                
                if self._media_container.ReadyToSlideshow() and not CGC.core().MenuIsOpen():
                    
                    self._media_container.StopForSlideshow( False )
                    
                    self._ShowNext()
                    
                    self._timer_slideshow_job = HG.client_controller.CallLaterQtSafe( self, self._timer_slideshow_interval, 'slideshow', self.DoSlideshow )
                    
                else:
                    
                    self._timer_slideshow_job = HG.client_controller.CallLaterQtSafe( self, 0.1, 'slideshow', self.DoSlideshow )
                    
                
            
        except:
            
            self._timer_slideshow_job = None
            
            raise
            
        
    
    def contextMenuEvent( self, event ):
        
        if event.reason() == QG.QContextMenuEvent.Keyboard:
            
            self.ShowMenu()
            
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand, canvas_key = None ):
        
        if canvas_key is not None and canvas_key != self._canvas_key:
            
            return False
            
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_PAUSE_PLAY_SLIDESHOW:
                
                self._PausePlaySlideshow()
                
            elif action == CAC.SIMPLE_SHOW_MENU:
                
                self.ShowMenu()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            command_processed = CanvasMediaListNavigable.ProcessApplicationCommand( self, command )
            
        
        return command_processed
        
    
    def ShowMenu( self ):
        
        if self._current_media is not None:
            
            new_options = HG.client_controller.new_options
            
            advanced_mode = new_options.GetBoolean( 'advanced_mode' )
            
            services = HG.client_controller.services_manager.GetServices()
            
            local_ratings_services = [ service for service in services if service.GetServiceType() in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
            
            i_can_post_ratings = len( local_ratings_services ) > 0
            
            self._last_drag_pos = None # to stop successive right-click drag warp bug
            
            locations_manager = self._current_media.GetLocationsManager()
            
            menu = QW.QMenu()
            
            #
            
            info_lines = self._current_media.GetPrettyInfoLines()
            
            top_line = info_lines.pop(0)
            
            info_menu = QW.QMenu( menu )
            
            for line in info_lines:
                
                ClientGUIMenus.AppendMenuLabel( info_menu, line, line )
                
            
            ClientGUIMedia.AddFileViewingStatsMenu( info_menu, ( self._current_media, ) )
            
            ClientGUIMenus.AppendMenu( menu, info_menu, top_line )
            
            #
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if self._IsZoomable():
                
                zoom_menu = QW.QMenu( menu )
                
                ClientGUIMenus.AppendMenuItem( zoom_menu, 'zoom in', 'Zoom the media in.', self._ZoomIn )
                ClientGUIMenus.AppendMenuItem( zoom_menu, 'zoom out', 'Zoom the media out.', self._ZoomOut )
                
                if self._current_zoom != 1.0:
                    
                    ClientGUIMenus.AppendMenuItem( zoom_menu, 'zoom to 100%', 'Set the zoom to 100%.', self._ZoomSwitch )
                    
                elif self._current_zoom != self._canvas_zoom:
                    
                    ClientGUIMenus.AppendMenuItem( zoom_menu, 'zoom fit', 'Set the zoom so the media fits the canvas.', self._ZoomSwitch )
                    
                
                ClientGUIMenus.AppendMenu( menu, zoom_menu, 'current zoom: {}'.format( ClientData.ConvertZoomToPercentage( self._current_zoom ) ) )
                
            
            AddAudioVolumeMenu( menu, self.CANVAS_TYPE )
            
            if self.parentWidget().isFullScreen():
                
                ClientGUIMenus.AppendMenuItem( menu, 'exit fullscreen', 'Make this media viewer a regular window with borders.', self.parentWidget().FullscreenSwitch )
                
            else:
                
                ClientGUIMenus.AppendMenuItem( menu, 'go fullscreen', 'Make this media viewer a fullscreen window without borders.', self.parentWidget().FullscreenSwitch )
                
            
            slideshow = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( slideshow, '1 second', 'Start a slideshow with a one second interval.', self._StartSlideshow, 1.0 )
            ClientGUIMenus.AppendMenuItem( slideshow, '5 second', 'Start a slideshow with a five second interval.', self._StartSlideshow, 5.0 )
            ClientGUIMenus.AppendMenuItem( slideshow, '10 second', 'Start a slideshow with a ten second interval.', self._StartSlideshow, 10.0 )
            ClientGUIMenus.AppendMenuItem( slideshow, '30 second', 'Start a slideshow with a thirty second interval.', self._StartSlideshow, 30.0 )
            ClientGUIMenus.AppendMenuItem( slideshow, '60 second', 'Start a slideshow with a one minute interval.', self._StartSlideshow, 60.0 )
            ClientGUIMenus.AppendMenuItem( slideshow, 'very fast', 'Start a very fast slideshow.', self._StartSlideshow, 0.08 )
            ClientGUIMenus.AppendMenuItem( slideshow, 'custom interval', 'Start a slideshow with a custom interval.', self._StartSlideshow )
            
            ClientGUIMenus.AppendMenu( menu, slideshow, 'start slideshow' )
            
            if self._RunningSlideshow():
                
                ClientGUIMenus.AppendMenuItem( menu, 'stop slideshow', 'Stop the current slideshow.', self._PausePlaySlideshow )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( menu, 'remove from view', 'Remove this file from the list you are viewing.', self._Remove )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if self._current_media.HasInbox():

                ClientGUIMenus.AppendMenuItem( menu, 'archive', 'Archive this file, taking it out of the inbox.', self._Archive )
                
            elif self._current_media.HasArchive():
                
                ClientGUIMenus.AppendMenuItem( menu, 'return to inbox', 'Put this file back in the inbox.', self._Inbox )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            #
            
            local_file_service_keys = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
            
            # brush this up to handle different service keys
            # undelete do an optional service key too
            
            local_file_service_keys_we_are_in = sorted( locations_manager.GetCurrent().intersection( local_file_service_keys ), key = HG.client_controller.services_manager.GetName )
            
            for file_service_key in local_file_service_keys_we_are_in:
                
                ClientGUIMenus.AppendMenuItem( menu, 'delete from {}'.format( HG.client_controller.services_manager.GetName( file_service_key ) ), 'Delete this file.', self._Delete, file_service_key = file_service_key )
                
            
            #
            
            if locations_manager.IsTrashed():
                
                ClientGUIMenus.AppendMenuItem( menu, 'delete physically now', 'Delete this file immediately. This cannot be undone.', self._Delete, file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
                ClientGUIMenus.AppendMenuItem( menu, 'undelete', 'Take this file out of the trash, returning it to its original file service.', self._Undelete )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            manage_menu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( manage_menu, 'tags', 'Manage this file\'s tags.', self._ManageTags )
            
            if i_can_post_ratings:
                
                ClientGUIMenus.AppendMenuItem( manage_menu, 'ratings', 'Manage this file\'s ratings.', self._ManageRatings )
                
            
            ClientGUIMenus.AppendMenuItem( manage_menu, 'urls', 'Manage this file\'s known urls.', self._ManageURLs )
            
            num_notes = self._current_media.GetNotesManager().GetNumNotes()
            
            notes_str = 'notes'
            
            if num_notes > 0:
                
                notes_str = '{} ({})'.format( notes_str, HydrusData.ToHumanInt( num_notes ) )
                
            
            ClientGUIMenus.AppendMenuItem( manage_menu, notes_str, 'Manage this file\'s notes.', self._ManageNotes )
            
            ClientGUIMedia.AddManageFileViewingStatsMenu( self, manage_menu, [ self._current_media ] )
            
            ClientGUIMenus.AppendMenu( menu, manage_menu, 'manage' )
            
            ClientGUIMedia.AddKnownURLsViewCopyMenu( self, menu, self._current_media )
            
            open_menu = QW.QMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( open_menu, 'in external program', 'Open this file in the default external program.', self._OpenExternally )
            ClientGUIMenus.AppendMenuItem( open_menu, 'in a new page', 'Show your current media in a simple new page.', self._ShowMediaInNewPage )
            ClientGUIMenus.AppendMenuItem( open_menu, 'in web browser', 'Show this file in your OS\'s web browser.', self._OpenFileInWebBrowser )
            
            show_open_in_explorer = advanced_mode and ( HC.PLATFORM_WINDOWS or HC.PLATFORM_MACOS )
            
            if show_open_in_explorer:
                
                ClientGUIMenus.AppendMenuItem( open_menu, 'in file browser', 'Show this file in your OS\'s file browser.', self._OpenFileLocation )
                
            
            ClientGUIMenus.AppendMenu( menu, open_menu, 'open' )
            
            share_menu = QW.QMenu( menu )
            
            copy_menu = QW.QMenu( share_menu )

            ClientGUIMenus.AppendMenuItem( copy_menu, 'file', 'Copy this file to your clipboard.', self._CopyFileToClipboard )
            
            copy_hash_menu = QW.QMenu( copy_menu )

            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'sha256 (hydrus default)', 'Copy this file\'s SHA256 hash to your clipboard.', self._CopyHashToClipboard, 'sha256' )
            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'md5', 'Copy this file\'s MD5 hash to your clipboard.', self._CopyHashToClipboard, 'md5' )
            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'sha1', 'Copy this file\'s SHA1 hash to your clipboard.', self._CopyHashToClipboard, 'sha1' )
            ClientGUIMenus.AppendMenuItem( copy_hash_menu, 'sha512', 'Copy this file\'s SHA512 hash to your clipboard.', self._CopyHashToClipboard, 'sha512' )
            
            ClientGUIMenus.AppendMenu( copy_menu, copy_hash_menu, 'hash' )
            
            if advanced_mode:
                
                hash_id_str = str( self._current_media.GetHashId() )
                
                ClientGUIMenus.AppendMenuItem( copy_menu, 'file_id ({})'.format( hash_id_str ), 'Copy this file\'s internal file/hash_id.', HG.client_controller.pub, 'clipboard', 'text', hash_id_str )
                
            
            if self._current_media.GetMime() in HC.IMAGES:
                
                ClientGUIMenus.AppendMenuItem( copy_menu, 'image (bitmap)', 'Copy this file to your clipboard as a BMP image.', self._CopyBMPToClipboard )
                

            ClientGUIMenus.AppendMenuItem( copy_menu, 'path', 'Copy this file\'s path to your clipboard.', self._CopyPathToClipboard )
            
            ClientGUIMenus.AppendMenu( share_menu, copy_menu, 'copy' )
            
            ClientGUIMenus.AppendMenu( menu, share_menu, 'share' )
            
            CGC.core().PopupMenu( self, menu )
            
        
    
