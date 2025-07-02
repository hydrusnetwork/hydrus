import random

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientGlobals as CG
from hydrus.client.files import ClientFilesMaintenance
from hydrus.client.gui import ClientGUIDragDrop
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIRatings
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.media import ClientGUIMediaSimpleActions
from hydrus.client.gui.media import ClientGUIMediaModalActions
from hydrus.client.gui.media import ClientGUIMediaMenus
from hydrus.client.gui.pages import ClientGUIPageManager
from hydrus.client.gui.pages import ClientGUIMediaResultsPanel
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelMenus
from hydrus.client.gui.widgets import ClientGUIPainterShapes
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaFileFilter
from hydrus.client.media import ClientMediaResultPrettyInfo
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientRatings

FRAME_DURATION_60FPS = 1.0 / 60

class ThumbnailWaitingToBeDrawn( object ):
    
    def __init__( self, hash, thumbnail, thumbnail_index, bitmap ):
        
        self.hash = hash
        self.thumbnail = thumbnail
        self.thumbnail_index = thumbnail_index
        self.bitmap = bitmap
        
        self._draw_complete = False
        
    
    def DrawComplete( self ) -> bool:
        
        return self._draw_complete
        
    
    def DrawDue( self ) -> bool:
        
        return True
        
    
    def DrawToPainter( self, x: int, y: int, painter: QG.QPainter ):
        
        painter.drawImage( x, y, self.bitmap )
        
        self._draw_complete = True
        
    

class ThumbnailWaitingToBeDrawnAnimated( ThumbnailWaitingToBeDrawn ):
    
    FADE_DURATION_S = 0.5
    
    def __init__( self, hash, thumbnail, thumbnail_index, bitmap ):
        
        super().__init__( hash, thumbnail, thumbnail_index, bitmap )
        
        self.num_frames_drawn = 0
        self.num_frames_to_draw = max( int( self.FADE_DURATION_S // FRAME_DURATION_60FPS ), 1 ) 
        
        opacity_factor = max( 0.05, 1 / ( self.num_frames_to_draw / 3 ) )
        
        self.alpha_bmp = QP.AdjustOpacity( self.bitmap, opacity_factor )
        
        self.animation_started_precise = HydrusTime.GetNowPrecise()
        
    
    def _GetNumFramesOutstanding( self ):
        
        now_precise = HydrusTime.GetNowPrecise()
        
        num_frames_to_now = int( ( now_precise - self.animation_started_precise ) // FRAME_DURATION_60FPS )
        
        return min( num_frames_to_now, self.num_frames_to_draw - self.num_frames_drawn )
        
    
    def DrawDue( self ) -> bool:
        
        return self._GetNumFramesOutstanding() > 0
        
    
    def DrawToPainter( self, x: int, y: int, painter: QG.QPainter ):
        
        num_frames_to_draw = self._GetNumFramesOutstanding()
        
        if self.num_frames_drawn + num_frames_to_draw >= self.num_frames_to_draw:
            
            painter.drawImage( x, y, self.bitmap )
            
            self.num_frames_drawn = self.num_frames_to_draw
            self._draw_complete = True
            
        else:
            
            for i in range( num_frames_to_draw ):
                
                painter.drawImage( x, y, self.alpha_bmp )
                
            
            self.num_frames_drawn += num_frames_to_draw
            
        
    

class MediaResultsPanelThumbnails( ClientGUIMediaResultsPanel.MediaResultsPanel ):
    
    def __init__( self, parent, page_key, page_manager: ClientGUIPageManager.PageManager, media_results ):
        
        self._clean_canvas_pages = {}
        self._dirty_canvas_pages = []
        self._num_rows_per_canvas_page = 1
        self._num_rows_per_actual_page = 1
        
        self._last_size = QC.QSize( 20, 20 )
        self._num_columns = 1
        
        self._drag_init_coordinates = None
        self._drag_click_timestamp_ms = 0
        self._drag_prefire_event_count = 0
        self._hashes_to_thumbnails_waiting_to_be_drawn: dict[ bytes, ThumbnailWaitingToBeDrawn ] = {}
        self._hashes_faded = set()
        
        super().__init__( parent, page_key, page_manager, media_results )
        
        self._my_current_drag_object = None
        
        self._last_device_pixel_ratio = self.devicePixelRatio()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        thumbnail_scroll_rate = float( CG.client_controller.new_options.GetString( 'thumbnail_scroll_rate' ) )
        
        self.verticalScrollBar().setSingleStep( int( round( thumbnail_span_height * thumbnail_scroll_rate ) ) )
        
        self._widget_event_filter = QP.WidgetEventFilter( self.widget() )
        self._widget_event_filter.EVT_LEFT_DCLICK( self.EventMouseFullScreen )
        self._widget_event_filter.EVT_MIDDLE_DOWN( self.EventMouseFullScreen )
        
        # notice this is on widget, not myself. fails to set up scrollbars if just moved up
        # there's a job in qt to-do to sort all this out and fix other scroll issues
        self._widget_event_filter.EVT_SIZE( self.EventResize )
        
        self.widget().setMinimumSize( 50, 50 )
        
        self._UpdateScrollBars()
        
        CG.client_controller.sub( self, 'MaintainPageCache', 'memory_maintenance_pulse' )
        CG.client_controller.sub( self, 'NotifyFilesNeedRedraw', 'notify_files_need_redraw' )
        CG.client_controller.sub( self, 'NewThumbnails', 'new_thumbnails' )
        CG.client_controller.sub( self, 'ThumbnailsReset', 'notify_complete_thumbnail_reset' )
        CG.client_controller.sub( self, 'RedrawAllThumbnails', 'refresh_all_tag_presentation_gui' )
        CG.client_controller.sub( self, 'WaterfallThumbnails', 'waterfall_thumbnails' )
        
    
    def _CalculateVisiblePageIndices( self ):
        
        y_start = self._GetYStart()
        
        earliest_y = y_start
        
        last_y = earliest_y + QP.ScrollAreaVisibleRect( self ).size().height()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        page_height = self._num_rows_per_canvas_page * thumbnail_span_height
        
        first_visible_page_index = earliest_y // page_height
        
        last_visible_page_index = last_y // page_height
        
        page_indices = list( range( first_visible_page_index, last_visible_page_index + 1 ) )
        
        return page_indices
        
    
    def _CheckDnDIsOK( self, drag_object ):
        
        # drag.cancel is not supported on macOS
        if HC.PLATFORM_MACOS:
            
            return
            
        
        # QW.QApplication.mouseButtons() doesn't work unless mouse is over!
        if not ClientGUIFunctions.MouseIsOverOneOfOurWindows():
            
            return
            
        
        if self._my_current_drag_object == drag_object and QW.QApplication.mouseButtons() != QC.Qt.MouseButton.LeftButton:
            
            # awkward situation where, it seems, the DnD is spawned while the 'release left-click' event is in the queue
            # the DnD spawns after the click release and sits there until the user clicks again
            # I think this is because I am spawning the DnD in the move event rather than the mouse press
            
            self._my_current_drag_object.cancel()
            
            self._my_current_drag_object = None
            
        
    
    def _CreateNewDirtyPage( self ):
        
        my_width = self.size().width()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        dpr = self.devicePixelRatio()
        
        canvas_width = int( my_width * dpr )
        canvas_height = int( self._num_rows_per_canvas_page * thumbnail_span_height * dpr )
        
        canvas_page = CG.client_controller.bitmap_manager.GetQtImage( canvas_width, canvas_height, 32 )
        
        canvas_page.setDevicePixelRatio( dpr )
        
        self._dirty_canvas_pages.append( canvas_page )
        
    
    def _DeleteAllDirtyPages( self ):
        
        self._dirty_canvas_pages = []
        
    
    def _DirtyAllPages( self ):
        
        clean_indices = list( self._clean_canvas_pages.keys() )
        
        for clean_index in clean_indices:
            
            self._DirtyPage( clean_index )
            
        
    
    def _DirtyPage( self, clean_index ):

        canvas_page = self._clean_canvas_pages[ clean_index ]
        
        del self._clean_canvas_pages[ clean_index ]
        
        thumbnails = [ thumbnail for ( thumbnail_index, thumbnail ) in self._GetThumbnailsFromPageIndex( clean_index ) ]
        
        if len( thumbnails ) > 0:
            
            CG.client_controller.thumbnails_cache.CancelWaterfall( self._page_key, thumbnails )
            
        
        self._dirty_canvas_pages.append( canvas_page )
        
    
    def _DrawCanvasPage( self, page_index, canvas_page ):
        
        painter = QG.QPainter( canvas_page )
        
        new_options = CG.client_controller.new_options
        
        bg_colour = self.GetColour( CC.COLOUR_THUMBGRID_BACKGROUND )
        
        if HG.thumbnail_debug_mode and page_index % 2 == 0:
            
            bg_colour = ClientGUIFunctions.GetLighterDarkerColour( bg_colour )
            
        
        comp_mode = painter.compositionMode()
        
        painter.setCompositionMode( QG.QPainter.CompositionMode.CompositionMode_Source )
        
        if new_options.GetNoneableString( 'media_background_bmp_path' ) is not None:
            
            painter.setBackground( QG.QBrush( QC.Qt.GlobalColor.transparent ) )
            
        else: 
            
            painter.setBackground( QG.QBrush( bg_colour ) )
            
        
        painter.eraseRect( painter.viewport() )
        
        painter.setCompositionMode( comp_mode )
        
        #
        
        page_thumbnails = self._GetThumbnailsFromPageIndex( page_index )
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        thumbnails_to_render_later = []
        
        thumbnail_cache = CG.client_controller.thumbnails_cache
        
        thumbnail_margin = CG.client_controller.new_options.GetInteger( 'thumbnail_margin' )
        
        for ( thumbnail_index, thumbnail ) in page_thumbnails:
            
            display_media = thumbnail.GetDisplayMedia()
            
            if display_media is None:
                
                continue
                
            
            hash = display_media.GetHash()
            
            if hash in self._hashes_faded and thumbnail_cache.HasThumbnailCached( thumbnail ):
                
                self._StopFading( hash )
                
                thumbnail_col = thumbnail_index % self._num_columns
                
                thumbnail_row = thumbnail_index // self._num_columns
                
                x = thumbnail_col * thumbnail_span_width + thumbnail_margin
                
                y = ( thumbnail_row - ( page_index * self._num_rows_per_canvas_page ) ) * thumbnail_span_height + thumbnail_margin
                
                painter.drawImage( x, y, thumbnail.GetQtImage( thumbnail, self, self.devicePixelRatio() ) )
                
            else:
                
                thumbnails_to_render_later.append( thumbnail )
                
            
        
        if len( thumbnails_to_render_later ) > 0:
            
            CG.client_controller.thumbnails_cache.Waterfall( self._page_key, thumbnails_to_render_later )
            
        
    
    def _FadeThumbnails( self, thumbnails ):
        
        if len( thumbnails ) == 0:
            
            return
            
        
        if not CG.client_controller.gui.IsCurrentPage( self._page_key ):
            
            self._DirtyAllPages()
            
            return
            
        
        now_precise = HydrusTime.GetNowPrecise()
        
        for thumbnail in thumbnails:
            
            display_media = thumbnail.GetDisplayMedia()
            
            if display_media is None:
                
                continue
                
            
            try:
                
                thumbnail_index = self._sorted_media.index( thumbnail )
                
            except HydrusExceptions.DataMissing:
                
                # probably means a collect happened during an ongoing waterfall or whatever
                
                continue
                
            
            if self._GetPageIndexFromThumbnailIndex( thumbnail_index ) not in self._clean_canvas_pages:
                
                continue
                
            
            hash = display_media.GetHash()
            
            self._hashes_faded.add( hash )
            
            self._StopFading( hash )
            
            bitmap = thumbnail.GetQtImage( thumbnail, self, self.devicePixelRatio() )
            
            fade_thumbnails = CG.client_controller.new_options.GetBoolean( 'fade_thumbnails' )
            
            if fade_thumbnails:
                
                thumbnail_draw_object = ThumbnailWaitingToBeDrawnAnimated( hash, thumbnail, thumbnail_index, bitmap )
                
            else:
                
                thumbnail_draw_object = ThumbnailWaitingToBeDrawn( hash, thumbnail, thumbnail_index, bitmap )
                
            
            self._hashes_to_thumbnails_waiting_to_be_drawn[ hash ] = thumbnail_draw_object
            
        
        CG.client_controller.gui.RegisterAnimationUpdateWindow( self )
        
    
    def _GenerateMediaCollection( self, media_results ):
        
        return ThumbnailMediaCollection( self._location_context, media_results )
        
    
    def _GenerateMediaSingleton( self, media_result ):
        
        return ThumbnailMediaSingleton( media_result )
        
    
    def _GetMediaCoordinates( self, media ):
        
        try: index = self._sorted_media.index( media )
        except: return ( -1, -1 )
        
        row = index // self._num_columns
        column = index % self._num_columns
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        thumbnail_margin = CG.client_controller.new_options.GetInteger( 'thumbnail_margin' )
        
        ( x, y ) = ( column * thumbnail_span_width + thumbnail_margin, row * thumbnail_span_height + thumbnail_margin )
        
        return ( x, y )
        
    
    def _GetPageIndexFromThumbnailIndex( self, thumbnail_index ):
        
        thumbnails_per_page = self._num_columns * self._num_rows_per_canvas_page
        
        page_index = thumbnail_index // thumbnails_per_page
        
        return page_index
        
    
    def _GetThumbnailSpanDimensions( self ):
        
        thumbnail_border = CG.client_controller.new_options.GetInteger( 'thumbnail_border' )
        thumbnail_margin = CG.client_controller.new_options.GetInteger( 'thumbnail_margin' )
        
        return ClientData.AddPaddingToDimensions( HC.options[ 'thumbnail_dimensions' ], ( thumbnail_border + thumbnail_margin ) * 2 )
        
    
    def _GetThumbnailUnderMouse( self, mouse_event ):
        
        pos = mouse_event.position().toPoint()
        
        x = pos.x()
        y = pos.y()
        
        ( t_span_x, t_span_y ) = self._GetThumbnailSpanDimensions()
        
        x_mod = x % t_span_x
        y_mod = y % t_span_y
        
        thumbnail_margin = CG.client_controller.new_options.GetInteger( 'thumbnail_margin' )
        
        if x_mod <= thumbnail_margin or y_mod <= thumbnail_margin or x_mod > t_span_x - thumbnail_margin or y_mod > t_span_y - thumbnail_margin:
            
            return None
            
        
        column_index = x // t_span_x
        row_index = y // t_span_y
        
        if column_index >= self._num_columns:
            
            return None
            
        
        thumbnail_index = self._num_columns * row_index + column_index
        
        if thumbnail_index < 0:
            
            return None
            
        
        if thumbnail_index >= len( self._sorted_media ):
            
            return None
            
        
        return self._sorted_media[ thumbnail_index ]
        
    
    def _GetThumbnailsFromPageIndex( self, page_index ):
        
        num_thumbnails_per_page = self._num_columns * self._num_rows_per_canvas_page
        
        start_index = num_thumbnails_per_page * page_index
        
        if start_index <= len( self._sorted_media ):
            
            end_index = min( len( self._sorted_media ), start_index + num_thumbnails_per_page )
            
            thumbnails = [ ( index, self._sorted_media[ index ] ) for index in range( start_index, end_index ) ]
            
        else:
            
            thumbnails = []
            
        
        return thumbnails
        
    
    def _MediaIsInCleanPage( self, thumbnail ):
        
        try:
            
            index = self._sorted_media.index( thumbnail )
            
        except HydrusExceptions.DataMissing:
            
            return False
            
        
        if self._GetPageIndexFromThumbnailIndex( index ) in self._clean_canvas_pages:
            
            return True
            
        else:
            
            return False
            
        
    
    def _MediaIsVisible( self, media ):
        
        if media is not None:
            
            ( x, y ) = self._GetMediaCoordinates( media )
            
            visible_rect = QP.ScrollAreaVisibleRect( self )
            
            visible_rect_y = visible_rect.y()
            
            visible_rect_height = visible_rect.height()
            
            ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
            
            bottom_edge_below_top_of_view = visible_rect_y < y + thumbnail_span_height
            top_edge_above_bottom_of_view = y < visible_rect_y + visible_rect_height
            
            is_visible = bottom_edge_below_top_of_view and top_edge_above_bottom_of_view
            
            return is_visible
            
        
        return True
        
    
    def _MoveThumbnailFocus( self, rows, columns, shift ):
        
        if self._last_hit_media is not None:
            
            media_to_use = self._last_hit_media
            
        elif self._next_best_media_if_focuses_removed is not None:
            
            media_to_use = self._next_best_media_if_focuses_removed
            
            if columns == -1: # treat it as if the focused area is between this and the next
                
                columns = 0
                
            
        elif len( self._sorted_media ) > 0:
            
            media_to_use = self._sorted_media[ 0 ]
            
        else:
            
            media_to_use = None
            
        
        if media_to_use is not None:
            
            try:
                
                current_position = self._sorted_media.index( media_to_use )
                
            except HydrusExceptions.DataMissing:
                
                self._SetFocusedMedia( None )
                
                return
                
            
            new_position = current_position + columns + ( self._num_columns * rows )
            
            if new_position < 0:
                
                new_position = 0
                
            elif new_position > len( self._sorted_media ) - 1:
                
                new_position = len( self._sorted_media ) - 1
                
            
            new_media = self._sorted_media[ new_position ]
            
            self._HitMedia( new_media, False, shift )
            
            self._ScrollToMedia( new_media )
            
        
    
    def _NotifyThumbnailsHaveMoved( self ):
        
        self._DirtyAllPages()
        
        self.widget().update()
        
    
    def _RecalculateVirtualSize( self, called_from_resize_event = False ):
        
        my_size = QP.ScrollAreaVisibleRect( self ).size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        if my_width > 0 and my_height > 0:
            
            ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
            
            num_media = len( self._sorted_media )
            
            num_rows = max( 1, num_media // self._num_columns )
            
            if num_media % self._num_columns > 0:
                
                num_rows += 1
                
            
            virtual_width = my_width
            
            virtual_height = num_rows * thumbnail_span_height
            
            yUnit = self.verticalScrollBar().singleStep()
            
            excess = virtual_height % yUnit
            
            if excess > 0: # we want virtual height to fit exactly into scroll units, even if that puts some padding below bottom row
                
                top_up = yUnit - excess
                
                virtual_height += top_up
                
            
            virtual_height = max( virtual_height, my_height )
            
            virtual_size = QC.QSize( virtual_width, virtual_height )
            
            if virtual_size != self.widget().size():
                
                self.widget().resize( QC.QSize( virtual_width, virtual_height ) )
                
                if not called_from_resize_event:
                    
                    self._UpdateScrollBars() # would lead to infinite recursion if called from a resize event
                    
                
            
        
    
    def _RedrawMedia( self, thumbnails ):
        
        visible_thumbnails = [ thumbnail for thumbnail in thumbnails if self._MediaIsInCleanPage( thumbnail ) ]
        
        thumbnails_cache = CG.client_controller.thumbnails_cache
        
        thumbnails_to_render_now = []
        thumbnails_to_render_later = []
        
        for thumbnail in visible_thumbnails:
            
            if thumbnails_cache.HasThumbnailCached( thumbnail ):
                
                thumbnails_to_render_now.append( thumbnail )
                
            else:
                
                thumbnails_to_render_later.append( thumbnail )
                
            
        
        if len( thumbnails_to_render_now ) > 0:
            
            self._FadeThumbnails( thumbnails_to_render_now )
            
        
        if len( thumbnails_to_render_later ) > 0:
            
            thumbnails_cache.Waterfall( self._page_key, thumbnails_to_render_later )
            
        
    
    def _ReinitialisePageCacheIfNeeded( self ):
        
        old_num_rows = self._num_rows_per_canvas_page
        old_num_columns = self._num_columns
        
        old_width = self._last_size.width()
        old_height = self._last_size.height()
        
        my_size = QP.ScrollAreaVisibleRect( self ).size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        num_rows = ( my_height // thumbnail_span_height )
        
        self._num_rows_per_actual_page = max( 1, num_rows )
        self._num_rows_per_canvas_page = max( 1, num_rows // 2 )
        
        self._num_columns = max( 1, my_width // thumbnail_span_width )
        
        dimensions_changed = old_width != my_width or old_height != my_height
        thumb_layout_changed = old_num_columns != self._num_columns or old_num_rows != self._num_rows_per_canvas_page
        
        if dimensions_changed or thumb_layout_changed:
            
            width_got_bigger = old_width < my_width
            
            if thumb_layout_changed or width_got_bigger:
                
                self._DirtyAllPages()
                
                self._DeleteAllDirtyPages()
                
            
            self.widget().update()
            
        
    
    def _RemoveMediaDirectly( self, singleton_media, collected_media ):
        
        if self._focused_media is not None:
            
            if self._focused_media in singleton_media or self._focused_media in collected_media:
                
                self._SetFocusedMedia( None )
                
            
        
        super()._RemoveMediaDirectly( singleton_media, collected_media )
        
        self._EndShiftSelect()
        
        self._RecalculateVirtualSize()
        
        self._DirtyAllPages()
        
        self._PublishSelectionChange()
        
        CG.client_controller.pub( 'refresh_page_name', self._page_key )
        
        CG.client_controller.pub( 'notify_new_pages_count' )
        
        self.widget().update()
        
    
    def _ScrollEnd( self, shift = False ):
        
        if len( self._sorted_media ) > 0:
            
            end_media = self._sorted_media[ -1 ]
            
            self._HitMedia( end_media, False, shift )
            
            self._ScrollToMedia( end_media )
            
        
    
    def _ScrollHome( self, shift = False ):
        
        if len( self._sorted_media ) > 0:
            
            home_media = self._sorted_media[ 0 ]
            
            self._HitMedia( home_media, False, shift )
            
            self._ScrollToMedia( home_media )
            
        
    
    def _ScrollToMedia( self, media ):
        
        if media is not None:
            
            ( x, y ) = self._GetMediaCoordinates( media )
            
            visible_rect = QP.ScrollAreaVisibleRect( self )
            
            visible_rect_y = visible_rect.y()
            
            visible_rect_height = visible_rect.height()
            
            ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
            
            new_options = CG.client_controller.new_options
            
            percent_visible = new_options.GetInteger( 'thumbnail_visibility_scroll_percent' ) / 100
            
            if y < visible_rect_y:
                
                self.ensureVisible( 0, y, 0, 0 )
                
            elif y > visible_rect_y + visible_rect_height - ( thumbnail_span_height * percent_visible ):
                
                self.ensureVisible( 0, y + thumbnail_span_height )
                
            
        
    
    def _StopFading( self, hash ):
        
        if hash in self._hashes_to_thumbnails_waiting_to_be_drawn:
            
            del self._hashes_to_thumbnails_waiting_to_be_drawn[ hash ]
            
        
    
    def _UpdateBackgroundColour( self ):
        
        super()._UpdateBackgroundColour()
        
        self._DirtyAllPages()
        
        self._DeleteAllDirtyPages()
        
        self.widget().update()
        
    
    def _UpdateScrollBars( self ):
        
        # The following call is officially a no-op since this property is already true, but it also triggers an update
        # of the scroll area's scrollbars which we need.
        # We need this since we are intercepting & doing work in resize events which causes
        # event propagation between the scroll area and the scrolled widget to not work properly (since we are suppressing resize events of the scrolled widget - otherwise we would get an infinite loop).
        # Probably the best would be to change how this work and not intercept any resize events.
        # Originally this was wx event handling which got ported to Qt more or less unchanged, hence the hackiness.
        
        self.setWidgetResizable( True )
        
    
    def AddMediaResults( self, page_key, media_results ):
        
        if page_key == self._page_key:
            
            thumbnails = super().AddMediaResults( page_key, media_results )
            
            if len( thumbnails ) > 0:
                
                self._RecalculateVirtualSize()
                
                CG.client_controller.thumbnails_cache.Waterfall( self._page_key, thumbnails )
                
                send_publish = False
                
                if len( self._selected_media ) == 0:
                    
                    max_number = CG.client_controller.new_options.GetNoneableInteger( 'number_of_unselected_medias_to_present_tags_for' )
                    
                    if max_number is None:
                        
                        send_publish = True
                        
                    elif len( self._sorted_media ) < max_number:
                        
                        send_publish = True
                        
                    
                
                if send_publish:
                    
                    self._PublishSelectionIncrement( thumbnails )
                    
                else:
                    
                    self.statusTextChanged.emit( self._GetPrettyStatusForStatusBar() )
                    
                
            
        
    
    def contextMenuEvent( self, event ):
        
        if event.reason() == QG.QContextMenuEvent.Reason.Keyboard:
            
            self.ShowMenu()
            
        
    
    def DoMouseMoveEvent( self, event ):
        
        if event.buttons() & QC.Qt.MouseButton.LeftButton:
            
            we_started_dragging_on_this_panel = self._drag_init_coordinates is not None
            
            if we_started_dragging_on_this_panel:
                
                old_drag_pos = self._drag_init_coordinates
                
                global_mouse_pos = QG.QCursor.pos()
                
                delta_pos = global_mouse_pos - old_drag_pos
                
                total_absolute_pixels_moved = delta_pos.manhattanLength()
                
                we_moved = total_absolute_pixels_moved > 0
                
                if we_moved:
                    
                    self._drag_prefire_event_count += 1
                    
                
                # prefire deal here is mpv lags on initial click, which can cause a drag (and hence an immediate pause) event by accident when mouserelease isn't processed quick
                # so now we'll say we can't start a drag unless we get a smooth ramp to our pixel delta threshold
                clean_drag_started = self._drag_prefire_event_count >= 10
                prob_not_an_accidental_click = HydrusTime.TimeHasPassedMS( self._drag_click_timestamp_ms + 100 )
                
                if clean_drag_started and prob_not_an_accidental_click:
                    
                    media = self._GetSelectedFlatMedia( discriminant = CC.DISCRIMINANT_LOCAL )
                    
                    if len( media ) > 0:
                        
                        alt_down = event.modifiers() & QC.Qt.KeyboardModifier.AltModifier
                        
                        self._my_current_drag_object = QG.QDrag( self )
                        
                        CG.client_controller.CallLaterQtSafe( self, 0.1, 'doing DnD check', self._CheckDnDIsOK, self._my_current_drag_object )
                        
                        result = ClientGUIDragDrop.DoFileExportDragDrop( self._my_current_drag_object, self._page_key, media, alt_down )
                        
                        self._my_current_drag_object = None
                        
                        if result not in ( QC.Qt.DropAction.IgnoreAction, ):
                            
                            self.focusMediaPaused.emit()
                            
                        
                        event.accept()
                        
                        return
                        
                    
                
            
        else:
            
            self._drag_init_coordinates = None
            self._drag_prefire_event_count = 0
            self._drag_click_timestamp_ms = 0
            
        
        event.ignore()
        
    
    def EventMouseFullScreen( self, event ):
        
        t = self._GetThumbnailUnderMouse( event )
        
        if t is not None:
            
            locations_manager = t.GetLocationsManager()
            
            if locations_manager.IsLocal():
                
                self._LaunchMediaViewer( t )
                
            else:
                
                can_download = not locations_manager.GetCurrent().isdisjoint( CG.client_controller.services_manager.GetRemoteFileServiceKeys() )
                
                if can_download:
                    
                    self._DownloadHashes( t.GetHashes() )
                    
                
            
        
    
    def EventResize( self, event ):
        
        self._ReinitialisePageCacheIfNeeded()
        
        self._RecalculateVirtualSize( called_from_resize_event = True )
        
        self._last_size = QP.ScrollAreaVisibleRect( self ).size()
        
    
    def GetTotalFileSize( self ):
        
        return sum( ( m.GetSize() for m in self._sorted_media ) )
        
    
    def MaintainPageCache( self ):
        
        if not CG.client_controller.gui.IsCurrentPage( self._page_key ):
            
            self._DirtyAllPages()
            
        
        self._DeleteAllDirtyPages()
        
    
    def mouseReleaseEvent( self, event ):
        
        if event.button() != QC.Qt.MouseButton.RightButton:
            
            QW.QScrollArea.mouseReleaseEvent( self, event )
            
            return
            
        
        self.ShowMenu()
        
    
    def MoveMedia( self, medias: list[ ClientMedia.Media ], insertion_index: int ):
        
        super().MoveMedia( medias, insertion_index )
        
        self._NotifyThumbnailsHaveMoved()
        
        self._ScrollToMedia( medias[0] )
        
    
    def NewThumbnails( self, hashes ):
        
        affected_thumbnails = self._GetMedia( hashes )
        
        if len( affected_thumbnails ) > 0:
            
            self._RedrawMedia( affected_thumbnails )
            
        
    
    def NotifyFilesNeedRedraw( self, hashes ):
        
        affected_media = self._GetMedia( hashes )
        
        self._RedrawMedia( affected_media )
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS:
                
                ( move_direction, selection_status ) = command.GetSimpleData()
                
                shift = selection_status == CAC.SELECTION_STATUS_SHIFT
                
                if move_direction in ( CAC.MOVE_HOME, CAC.MOVE_END ):
                    
                    if move_direction == CAC.MOVE_HOME:
                        
                        self._ScrollHome( shift )
                        
                    else: # MOVE_END
                        
                        self._ScrollEnd( shift )
                        
                    
                elif move_direction in ( CAC.MOVE_PAGE_UP, CAC.MOVE_PAGE_DOWN ):
                    
                    if move_direction == CAC.MOVE_PAGE_UP:
                        
                        direction = -1
                        
                    else: # MOVE_PAGE_DOWN
                        
                        direction = 1
                        
                    
                    self._MoveThumbnailFocus( self._num_rows_per_actual_page * direction, 0, shift )
                    
                else:
                    
                    if move_direction == CAC.MOVE_LEFT:
                        
                        rows = 0
                        columns = -1
                        
                    elif move_direction == CAC.MOVE_RIGHT:
                        
                        rows = 0
                        columns = 1
                        
                    elif move_direction == CAC.MOVE_UP:
                        
                        rows = -1
                        columns = 0
                        
                    elif move_direction == CAC.MOVE_DOWN:
                        
                        rows = 1
                        columns = 0
                        
                    else:
                        
                        raise NotImplementedError()
                        
                    
                    self._MoveThumbnailFocus( rows, columns, shift )
                    
                
            elif action == CAC.SIMPLE_SELECT_FILES:
                
                file_filter = command.GetSimpleData()
                
                self._Select( file_filter )
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        if not command_processed:
            
            return super().ProcessApplicationCommand( command )
            
        else:
            
            return command_processed
            
        
    
    def RedrawAllThumbnails( self ):
        
        self._DirtyAllPages()
        
        for m in self._collected_media:
            
            m.RecalcInternals()
            
        
        for thumbnail in self._sorted_media:
            
            thumbnail.ClearTagSummaryCaches()
            
        
        self.widget().update()
        
    
    def SetFocusedMedia( self, media ):
        
        super().SetFocusedMedia( media )
        
        if media is None:
            
            self._SetFocusedMedia( None )
            
        else:
            
            try:
                
                my_media = self._GetMedia( media.GetHashes() )[0]
                
                self._HitMedia( my_media, False, False )
                
                self._ScrollToMedia( self._focused_media )
                
            except:
                
                pass
                
            
        
    
    def showEvent( self, event ):
        
        self._UpdateScrollBars()
        
    
    def ShowMenu( self, do_not_show_just_return = False ):
        
        flat_selected_medias = ClientMedia.FlattenMedia( self._selected_media )
        
        all_locations_managers = [ media.GetLocationsManager() for media in ClientMedia.FlattenMedia( self._sorted_media ) ]
        selected_locations_managers = [ media.GetLocationsManager() for media in flat_selected_medias ]
        
        selection_has_local_file_domain = True in ( locations_manager.IsLocal() and not locations_manager.IsTrashed() for locations_manager in selected_locations_managers )
        selection_has_trash = True in ( locations_manager.IsTrashed() for locations_manager in selected_locations_managers )
        selection_has_inbox = True in ( media.HasInbox() for media in self._selected_media )
        selection_has_archive = True in ( media.HasArchive() and media.GetLocationsManager().IsLocal() for media in self._selected_media )
        selection_has_deletion_record = True in ( CC.COMBINED_LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() for locations_manager in selected_locations_managers )
        
        all_file_domains = HydrusLists.MassUnion( locations_manager.GetCurrent() for locations_manager in all_locations_managers )
        all_specific_file_domains = all_file_domains.difference( { CC.COMBINED_FILE_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_SERVICE_KEY } )
        
        some_downloading = True in ( locations_manager.IsDownloading() for locations_manager in selected_locations_managers )
        
        has_local = True in ( locations_manager.IsLocal() for locations_manager in all_locations_managers )
        has_remote = True in ( locations_manager.IsRemote() for locations_manager in all_locations_managers )
        
        num_files = self.GetNumFiles()
        num_selected = self._GetNumSelected()
        num_inbox = self.GetNumInbox()
        num_archive = self.GetNumArchive()
        
        any_selected = num_selected > 0
        multiple_selected = num_selected > 1
        
        menu = ClientGUIMenus.GenerateMenu( self.window() )
        
        # variables
        
        collections_selected = True in ( media.IsCollection() for media in self._selected_media )
        
        services_manager = CG.client_controller.services_manager
        
        services = services_manager.GetServices()
        
        file_repositories = [ service for service in services if service.GetServiceType() == HC.FILE_REPOSITORY ]
        
        ipfs_services = [ service for service in services if service.GetServiceType() == HC.IPFS ]
        
        local_ratings_services = [ service for service in services if service.GetServiceType() in HC.RATINGS_SERVICES ]
        
        i_can_post_ratings = len( local_ratings_services ) > 0
        
        local_media_file_service_keys = { service.GetServiceKey() for service in services if service.GetServiceType() == HC.LOCAL_FILE_DOMAIN }
        
        file_repository_service_keys = { repository.GetServiceKey() for repository in file_repositories }
        upload_permission_file_service_keys = { repository.GetServiceKey() for repository in file_repositories if repository.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_CREATE ) }
        petition_resolve_permission_file_service_keys = { repository.GetServiceKey() for repository in file_repositories if repository.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_MODERATE ) }
        petition_permission_file_service_keys = { repository.GetServiceKey() for repository in file_repositories if repository.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_PETITION ) } - petition_resolve_permission_file_service_keys
        user_manage_permission_file_service_keys = { repository.GetServiceKey() for repository in file_repositories if repository.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_MODERATE ) }
        ipfs_service_keys = { service.GetServiceKey() for service in ipfs_services }
        
        if multiple_selected:
            
            download_phrase = 'download all possible selected'
            rescind_download_phrase = 'cancel downloads for all possible selected'
            upload_phrase = 'upload all possible selected to'
            rescind_upload_phrase = 'rescind pending selected uploads to'
            petition_phrase = 'petition all possible selected for removal from'
            rescind_petition_phrase = 'rescind selected petitions for'
            remote_delete_phrase = 'delete all possible selected from'
            modify_account_phrase = 'modify the accounts that uploaded selected to'
            
            pin_phrase = 'pin all to'
            rescind_pin_phrase = 'rescind pin to'
            unpin_phrase = 'unpin all from'
            rescind_unpin_phrase = 'rescind unpin from'
            
            archive_phrase = 'archive selected'
            inbox_phrase = 're-inbox selected'
            local_delete_phrase = 'delete selected'
            delete_physically_phrase = 'delete selected physically now'
            undelete_phrase = 'undelete selected'
            clear_deletion_phrase = 'clear deletion record for selected'
            
        else:
            
            download_phrase = 'download'
            rescind_download_phrase = 'cancel download'
            upload_phrase = 'upload to'
            rescind_upload_phrase = 'rescind pending upload to'
            petition_phrase = 'petition for removal from'
            rescind_petition_phrase = 'rescind petition for'
            remote_delete_phrase = 'delete from'
            modify_account_phrase = 'modify the account that uploaded this to'
            
            pin_phrase = 'pin to'
            rescind_pin_phrase = 'rescind pin to'
            unpin_phrase = 'unpin from'
            rescind_unpin_phrase = 'rescind unpin from'
            
            archive_phrase = 'archive'
            inbox_phrase = 're-inbox'
            local_delete_phrase = 'delete'
            delete_physically_phrase = 'delete physically now'
            undelete_phrase = 'undelete'
            clear_deletion_phrase = 'clear deletion record'
            
        
        # info about the files
        
        remote_service_keys = CG.client_controller.services_manager.GetRemoteFileServiceKeys()
        
        groups_of_current_remote_service_keys = [ locations_manager.GetCurrent().intersection( remote_service_keys ) for locations_manager in selected_locations_managers ]
        groups_of_pending_remote_service_keys = [ locations_manager.GetPending().intersection( remote_service_keys ) for locations_manager in selected_locations_managers ]
        groups_of_petitioned_remote_service_keys = [ locations_manager.GetPetitioned().intersection( remote_service_keys ) for locations_manager in selected_locations_managers ]
        groups_of_deleted_remote_service_keys = [ locations_manager.GetDeleted().intersection( remote_service_keys ) for locations_manager in selected_locations_managers ]
        
        current_remote_service_keys = HydrusLists.MassUnion( groups_of_current_remote_service_keys )
        pending_remote_service_keys = HydrusLists.MassUnion( groups_of_pending_remote_service_keys )
        petitioned_remote_service_keys = HydrusLists.MassUnion( groups_of_petitioned_remote_service_keys )
        deleted_remote_service_keys = HydrusLists.MassUnion( groups_of_deleted_remote_service_keys )
        
        common_current_remote_service_keys = HydrusLists.IntelligentMassIntersect( groups_of_current_remote_service_keys )
        common_pending_remote_service_keys = HydrusLists.IntelligentMassIntersect( groups_of_pending_remote_service_keys )
        common_petitioned_remote_service_keys = HydrusLists.IntelligentMassIntersect( groups_of_petitioned_remote_service_keys )
        common_deleted_remote_service_keys = HydrusLists.IntelligentMassIntersect( groups_of_deleted_remote_service_keys )
        
        disparate_current_remote_service_keys = current_remote_service_keys - common_current_remote_service_keys
        disparate_pending_remote_service_keys = pending_remote_service_keys - common_pending_remote_service_keys
        disparate_petitioned_remote_service_keys = petitioned_remote_service_keys - common_petitioned_remote_service_keys
        disparate_deleted_remote_service_keys = deleted_remote_service_keys - common_deleted_remote_service_keys
        
        pending_file_service_keys = pending_remote_service_keys.intersection( file_repository_service_keys )
        petitioned_file_service_keys = petitioned_remote_service_keys.intersection( file_repository_service_keys )
        
        common_current_file_service_keys = common_current_remote_service_keys.intersection( file_repository_service_keys )
        common_pending_file_service_keys = common_pending_remote_service_keys.intersection( file_repository_service_keys )
        common_petitioned_file_service_keys = common_petitioned_remote_service_keys.intersection( file_repository_service_keys )
        common_deleted_file_service_keys = common_deleted_remote_service_keys.intersection( file_repository_service_keys )
        
        disparate_current_file_service_keys = disparate_current_remote_service_keys.intersection( file_repository_service_keys )
        disparate_pending_file_service_keys = disparate_pending_remote_service_keys.intersection( file_repository_service_keys )
        disparate_petitioned_file_service_keys = disparate_petitioned_remote_service_keys.intersection( file_repository_service_keys )
        disparate_deleted_file_service_keys = disparate_deleted_remote_service_keys.intersection( file_repository_service_keys )
        
        pending_ipfs_service_keys = pending_remote_service_keys.intersection( ipfs_service_keys )
        petitioned_ipfs_service_keys = petitioned_remote_service_keys.intersection( ipfs_service_keys )
        
        common_current_ipfs_service_keys = common_current_remote_service_keys.intersection( ipfs_service_keys )
        common_pending_ipfs_service_keys = common_pending_file_service_keys.intersection( ipfs_service_keys )
        common_petitioned_ipfs_service_keys = common_petitioned_remote_service_keys.intersection( ipfs_service_keys )
        
        disparate_current_ipfs_service_keys = disparate_current_remote_service_keys.intersection( ipfs_service_keys )
        disparate_pending_ipfs_service_keys = disparate_pending_remote_service_keys.intersection( ipfs_service_keys )
        disparate_petitioned_ipfs_service_keys = disparate_petitioned_remote_service_keys.intersection( ipfs_service_keys )
        
        # valid commands for the files
        
        current_file_service_keys = set()
        
        uploadable_file_service_keys = set()
        
        downloadable_file_service_keys = set()
        
        petitionable_file_service_keys = set()
        
        deletable_file_service_keys = set()
        
        modifyable_file_service_keys = set()
        
        pinnable_ipfs_service_keys = set()
        
        unpinnable_ipfs_service_keys = set()
        
        remote_file_service_keys = ipfs_service_keys.union( file_repository_service_keys )
        
        for locations_manager in selected_locations_managers:
            
            current = locations_manager.GetCurrent()
            deleted = locations_manager.GetDeleted()
            pending = locations_manager.GetPending()
            petitioned = locations_manager.GetPetitioned()
            
            # ALL
            
            current_file_service_keys.update( current )
            
            # FILE REPOS
            
            # we can upload (set pending) to a repo_id when we have permission, a file is local, not current, not pending, and either ( not deleted or we_can_overrule )
            
            if locations_manager.IsLocal():
                
                cannot_upload_to = current.union( pending ).union( deleted.difference( petition_resolve_permission_file_service_keys ) )
                
                can_upload_to = upload_permission_file_service_keys.difference( cannot_upload_to )
                
                uploadable_file_service_keys.update( can_upload_to )
                
            
            # we can download (set pending to local) when we have permission, a file is not local and not already downloading and current
            
            if not locations_manager.IsLocal() and not locations_manager.IsDownloading():
                
                downloadable_file_service_keys.update( remote_file_service_keys.intersection( current ) )
                
            
            # we can petition when we have permission and a file is current and it is not already petitioned
            
            petitionable_file_service_keys.update( ( petition_permission_file_service_keys & current ) - petitioned )
            
            # we can delete remote when we have permission and a file is current and it is not already petitioned
            
            deletable_file_service_keys.update( ( petition_resolve_permission_file_service_keys & current ) - petitioned )
            
            # we can modify users when we have permission and the file is current or deleted
            
            modifyable_file_service_keys.update( user_manage_permission_file_service_keys & ( current | deleted ) )
            
            # IPFS
            
            # we can pin if a file is local, not current, not pending
            
            if locations_manager.IsLocal():
                
                pinnable_ipfs_service_keys.update( ipfs_service_keys - current - pending )
                
            
            # we can unpin a file if it is current and not petitioned
            
            unpinnable_ipfs_service_keys.update( ( ipfs_service_keys & current ) - petitioned )
            
        
        # do the actual menu
        
        selection_info_menu = ClientGUIMenus.GenerateMenu( menu )
        
        selected_files_string = ClientMedia.GetMediasFiletypeSummaryString( self._selected_media )
        
        selection_info_menu_label = f'{selected_files_string}, {self._GetPrettyTotalSize( only_selected = True )}'
        
        if multiple_selected:
            
            pretty_total_duration = self._GetPrettyTotalDuration( only_selected = True )
            
            if pretty_total_duration != '':
                
                selection_info_menu_label += ', {}'.format( pretty_total_duration )
                
            
        else:
            
            if self._HasFocusSingleton():
                
                focus_singleton = self._GetFocusSingleton()
                
                pretty_info_lines = ClientMediaResultPrettyInfo.GetPrettyMediaResultInfoLines( focus_singleton.GetMediaResult() )
                
                ClientGUIMediaMenus.AddPrettyMediaResultInfoLines( selection_info_menu, pretty_info_lines )
                
            
        
        ClientGUIMenus.AppendSeparator( selection_info_menu )
        
        ClientGUIMediaMenus.AddFileViewingStatsMenu( selection_info_menu, self._selected_media )
        
        if len( disparate_current_file_service_keys ) > 0:
            
            ClientGUIMediaMenus.AddServiceKeyLabelsToMenu( selection_info_menu, disparate_current_file_service_keys, 'some uploaded to' )
            
        
        if multiple_selected and len( common_current_file_service_keys ) > 0:
            
            ClientGUIMediaMenus.AddServiceKeyLabelsToMenu( selection_info_menu, common_current_file_service_keys, 'selected uploaded to' )
            
        
        if len( disparate_pending_file_service_keys ) > 0:
            
            ClientGUIMediaMenus.AddServiceKeyLabelsToMenu( selection_info_menu, disparate_pending_file_service_keys, 'some pending to' )
            
        
        if len( common_pending_file_service_keys ) > 0:
            
            ClientGUIMediaMenus.AddServiceKeyLabelsToMenu( selection_info_menu, common_pending_file_service_keys, 'pending to' )
            
        
        if len( disparate_petitioned_file_service_keys ) > 0:
            
            ClientGUIMediaMenus.AddServiceKeyLabelsToMenu( selection_info_menu, disparate_petitioned_file_service_keys, 'some petitioned for removal from' )
            
        
        if len( common_petitioned_file_service_keys ) > 0:
            
            ClientGUIMediaMenus.AddServiceKeyLabelsToMenu( selection_info_menu, common_petitioned_file_service_keys, 'petitioned for removal from' )
            
        
        if len( disparate_deleted_file_service_keys ) > 0:
            
            ClientGUIMediaMenus.AddServiceKeyLabelsToMenu( selection_info_menu, disparate_deleted_file_service_keys, 'some deleted from' )
            
        
        if len( common_deleted_file_service_keys ) > 0:
            
            ClientGUIMediaMenus.AddServiceKeyLabelsToMenu( selection_info_menu, common_deleted_file_service_keys, 'deleted from' )
            
        
        if len( disparate_current_ipfs_service_keys ) > 0:
            
            ClientGUIMediaMenus.AddServiceKeyLabelsToMenu( selection_info_menu, disparate_current_ipfs_service_keys, 'some pinned to' )
            
        
        if multiple_selected and len( common_current_ipfs_service_keys ) > 0:
            
            ClientGUIMediaMenus.AddServiceKeyLabelsToMenu( selection_info_menu, common_current_ipfs_service_keys, 'selected pinned to' )
            
        
        if len( disparate_pending_ipfs_service_keys ) > 0:
            
            ClientGUIMediaMenus.AddServiceKeyLabelsToMenu( selection_info_menu, disparate_pending_ipfs_service_keys, 'some to be pinned to' )
            
        
        if len( common_pending_ipfs_service_keys ) > 0:
            
            ClientGUIMediaMenus.AddServiceKeyLabelsToMenu( selection_info_menu, common_pending_ipfs_service_keys, 'to be pinned to' )
            
        
        if len( disparate_petitioned_ipfs_service_keys ) > 0:
            
            ClientGUIMediaMenus.AddServiceKeyLabelsToMenu( selection_info_menu, disparate_petitioned_ipfs_service_keys, 'some to be unpinned from' )
            
        
        if len( common_petitioned_ipfs_service_keys ) > 0:
            
            ClientGUIMediaMenus.AddServiceKeyLabelsToMenu( selection_info_menu, common_petitioned_ipfs_service_keys, unpin_phrase )
            
        
        if any_selected:
            
            if len( selection_info_menu.actions() ) == 0:
                
                selection_info_menu.deleteLater()
                
                ClientGUIMenus.AppendMenuLabel( menu, selection_info_menu_label )
                
            else:
                
                ClientGUIMenus.AppendMenu( menu, selection_info_menu, selection_info_menu_label )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        ClientGUIMenus.AppendMenuItem( menu, 'refresh', 'Refresh the current search.', self.refreshQuery.emit )
        
        if len( self._sorted_media ) > 0:
            
            ClientGUIMenus.AppendSeparator( menu )
            
            filter_counts = {}
            
            filter_counts[ ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_ALL ) ] = num_files
            filter_counts[ ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_INBOX ) ] = num_inbox
            filter_counts[ ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_ARCHIVE ) ] = num_archive
            filter_counts[ ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_SELECTED ) ] = num_selected
            
            has_local_and_remote = has_local and has_remote
            
            ClientGUIMediaResultsPanelMenus.AddSelectMenu( self, menu, filter_counts, all_specific_file_domains, has_local_and_remote )
            ClientGUIMediaResultsPanelMenus.AddRemoveMenu( self, menu, filter_counts, all_specific_file_domains, has_local_and_remote )
            
            if len( self._selected_media ) > 0:
                
                ordered_selected_media = self._GetSelectedMediaOrdered()
                
                try:
                    
                    earliest_index = self._sorted_media.index( ordered_selected_media[ 0 ] )
                    
                    selection_is_contiguous = any_selected and self._sorted_media.index( ordered_selected_media[ -1 ] ) - earliest_index == num_selected - 1
                    
                    ClientGUIMediaResultsPanelMenus.AddRearrangeMenu( self, menu, self._selected_media, self._sorted_media, self._focused_media, selection_is_contiguous, earliest_index )
                    
                except HydrusExceptions.DataMissing:
                    
                    pass
                    
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if has_local:
                
                ClientGUIMenus.AppendMenuItem( menu, 'archive/delete filter', 'Launch a special media viewer that will quickly archive or delete the selected media. Check the help if you are unfamiliar with this mode!', self._ArchiveDeleteFilter )
                
            
        
        if selection_has_inbox:
            
            ClientGUIMenus.AppendMenuItem( menu, archive_phrase, 'Archive the selected files.', self._Archive )
            
        
        if selection_has_archive:
            
            ClientGUIMenus.AppendMenuItem( menu, inbox_phrase, 'Put the selected files back in the inbox.', self._Inbox )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        user_command_deletable_file_service_keys = local_media_file_service_keys.union( [ CC.LOCAL_UPDATE_SERVICE_KEY ] )
        
        local_file_service_keys_we_are_in = sorted( current_file_service_keys.intersection( user_command_deletable_file_service_keys ), key = CG.client_controller.services_manager.GetName )
        
        if len( local_file_service_keys_we_are_in ) > 0:
            
            delete_menu = ClientGUIMenus.GenerateMenu( menu )
            
            for file_service_key in local_file_service_keys_we_are_in:
                
                service_name = CG.client_controller.services_manager.GetName( file_service_key )
                
                ClientGUIMenus.AppendMenuItem( delete_menu, f'from {service_name}', f'Delete the selected files from {service_name}.', self._Delete, file_service_key )
                
            
            ClientGUIMenus.AppendMenu( menu, delete_menu, local_delete_phrase )
            
        
        if selection_has_trash:
            
            if selection_has_local_file_domain:
                
                ClientGUIMenus.AppendMenuItem( menu, 'delete trash physically now', 'Completely delete the selected trashed files, forcing an immediate physical delete from your hard drive.', self._Delete, CC.COMBINED_LOCAL_FILE_SERVICE_KEY, only_those_in_file_service_key = CC.TRASH_SERVICE_KEY )
                
            
            ClientGUIMenus.AppendMenuItem( menu, delete_physically_phrase, 'Completely delete the selected files, forcing an immediate physical delete from your hard drive.', self._Delete, CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
            ClientGUIMenus.AppendMenuItem( menu, undelete_phrase, 'Restore the selected files back to \'my files\'.', self._Undelete )
            
        
        if selection_has_deletion_record:
            
            ClientGUIMenus.AppendMenuItem( menu, clear_deletion_phrase, 'Clear the deletion record for these files, allowing them to reimport even if previously deleted files are set to be discarded.', self._ClearDeleteRecord )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if any_selected:
            
            manage_menu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( manage_menu, 'tags', 'Manage tags for the selected files.', self._ManageTags )
            
            if i_can_post_ratings:
                
                ClientGUIMenus.AppendMenuItem( manage_menu, 'ratings', 'Manage ratings for the selected files.', self._ManageRatings )
                
            
            num_notes = 0
            
            if self._HasFocusSingleton():
                
                focus_singleton = self._GetFocusSingleton()
                
                num_notes = focus_singleton.GetNotesManager().GetNumNotes()
                
            
            notes_str = 'notes'
            
            if num_notes > 0:
                
                notes_str = '{} ({})'.format( notes_str, HydrusNumbers.ToHumanInt( num_notes ) )
                
            
            ClientGUIMenus.AppendMenuItem( manage_menu, notes_str, 'Manage notes for the focused file.', self._ManageNotes )
            
            ClientGUIMenus.AppendMenuItem( manage_menu, 'times', 'Edit the timestamps for your files.', self._ManageTimestamps )
            ClientGUIMenus.AppendMenuItem( manage_menu, 'force filetype', 'Force your files to appear as a different filetype.', ClientGUIMediaModalActions.SetFilesForcedFiletypes, self, self._selected_media )
            
            if self._HasFocusSingleton():
                
                media_result = self._GetFocusSingleton().GetMediaResult()
                
                ClientGUIMediaMenus.AddDuplicatesMenu( self, self, manage_menu, self._location_context, media_result, num_selected, collections_selected )
                
            
            regen_menu = ClientGUIMenus.GenerateMenu( manage_menu )
            
            for job_type in ClientFilesMaintenance.ALL_REGEN_JOBS_IN_HUMAN_ORDER:
                
                ClientGUIMenus.AppendMenuItem( regen_menu, ClientFilesMaintenance.regen_file_enum_to_str_lookup[ job_type ], ClientFilesMaintenance.regen_file_enum_to_description_lookup[ job_type ], self._RegenerateFileData, job_type )
                
            
            ClientGUIMenus.AppendMenu( manage_menu, regen_menu, 'maintenance' )
            
            ClientGUIMediaMenus.AddManageFileViewingStatsMenu( self, manage_menu, flat_selected_medias )
            
            ClientGUIMenus.AppendMenu( menu, manage_menu, 'manage' )
            
            ( local_duplicable_to_file_service_keys, local_moveable_from_and_to_file_service_keys ) = ClientGUIMediaSimpleActions.GetLocalFileActionServiceKeys( flat_selected_medias )
            
            len_interesting_local_service_keys = 0
            
            len_interesting_local_service_keys += len( local_duplicable_to_file_service_keys )
            len_interesting_local_service_keys += len( local_moveable_from_and_to_file_service_keys )
            
            #
            
            len_interesting_remote_service_keys = 0
            
            len_interesting_remote_service_keys += len( downloadable_file_service_keys )
            len_interesting_remote_service_keys += len( uploadable_file_service_keys )
            len_interesting_remote_service_keys += len( pending_file_service_keys )
            len_interesting_remote_service_keys += len( petitionable_file_service_keys )
            len_interesting_remote_service_keys += len( petitioned_file_service_keys )
            len_interesting_remote_service_keys += len( deletable_file_service_keys )
            len_interesting_remote_service_keys += len( modifyable_file_service_keys )
            len_interesting_remote_service_keys += len( pinnable_ipfs_service_keys )
            len_interesting_remote_service_keys += len( pending_ipfs_service_keys )
            len_interesting_remote_service_keys += len( unpinnable_ipfs_service_keys )
            len_interesting_remote_service_keys += len( petitioned_ipfs_service_keys )
            
            if multiple_selected:
                
                len_interesting_remote_service_keys += len( ipfs_service_keys )
                
            
            if len_interesting_local_service_keys > 0 or len_interesting_remote_service_keys > 0:
                
                locations_menu = ClientGUIMenus.GenerateMenu( menu )
                
                ClientGUIMenus.AppendMenu( menu, locations_menu, 'locations' )
                
                if len_interesting_local_service_keys > 0:
                    
                    ClientGUIMediaMenus.AddLocalFilesMoveAddToMenu( self, locations_menu, local_duplicable_to_file_service_keys, local_moveable_from_and_to_file_service_keys, multiple_selected, self.ProcessApplicationCommand )
                    
                
                if len_interesting_remote_service_keys > 0:
                    
                    ClientGUIMenus.AppendSeparator( locations_menu )
                    
                    if len( downloadable_file_service_keys ) > 0:
                        
                        ClientGUIMenus.AppendMenuItem( locations_menu, download_phrase, 'Download all possible selected files.', self._DownloadSelected )
                        
                    
                    if some_downloading:
                        
                        ClientGUIMenus.AppendMenuItem( locations_menu, rescind_download_phrase, 'Stop downloading any of the selected files.', self._RescindDownloadSelected )
                        
                    
                    if len( uploadable_file_service_keys ) > 0:
                        
                        ClientGUIMediaMenus.AddServiceKeysToMenu( locations_menu, uploadable_file_service_keys, upload_phrase, 'Upload all selected files to the file repository.', self._UploadFiles )
                        
                    
                    if len( pending_file_service_keys ) > 0:
                        
                        ClientGUIMediaMenus.AddServiceKeysToMenu( locations_menu, pending_file_service_keys, rescind_upload_phrase, 'Rescind the pending upload to the file repository.', self._RescindUploadFiles )
                        
                    
                    if len( petitionable_file_service_keys ) > 0:
                        
                        ClientGUIMediaMenus.AddServiceKeysToMenu( locations_menu, petitionable_file_service_keys, petition_phrase, 'Petition these files for deletion from the file repository.', self._PetitionFiles )
                        
                    
                    if len( petitioned_file_service_keys ) > 0:
                        
                        ClientGUIMediaMenus.AddServiceKeysToMenu( locations_menu, petitioned_file_service_keys, rescind_petition_phrase, 'Rescind the petition to delete these files from the file repository.', self._RescindPetitionFiles )
                        
                    
                    if len( deletable_file_service_keys ) > 0:
                        
                        ClientGUIMediaMenus.AddServiceKeysToMenu( locations_menu, deletable_file_service_keys, remote_delete_phrase, 'Delete these files from the file repository.', self._Delete )
                        
                    
                    if len( modifyable_file_service_keys ) > 0:
                        
                        ClientGUIMediaMenus.AddServiceKeysToMenu( locations_menu, modifyable_file_service_keys, modify_account_phrase, 'Modify the account(s) that uploaded these files to the file repository.', self._ModifyUploaders )
                        
                    
                    if len( pinnable_ipfs_service_keys ) > 0:
                        
                        ClientGUIMediaMenus.AddServiceKeysToMenu( locations_menu, pinnable_ipfs_service_keys, pin_phrase, 'Pin these files to the ipfs service.', self._UploadFiles )
                        
                    
                    if len( pending_ipfs_service_keys ) > 0:
                        
                        ClientGUIMediaMenus.AddServiceKeysToMenu( locations_menu, pending_ipfs_service_keys, rescind_pin_phrase, 'Rescind the pending pin to the ipfs service.', self._RescindUploadFiles )
                        
                    
                    if len( unpinnable_ipfs_service_keys ) > 0:
                        
                        ClientGUIMediaMenus.AddServiceKeysToMenu( locations_menu, unpinnable_ipfs_service_keys, unpin_phrase, 'Unpin these files from the ipfs service.', self._PetitionFiles )
                        
                    
                    if len( petitioned_ipfs_service_keys ) > 0:
                        
                        ClientGUIMediaMenus.AddServiceKeysToMenu( locations_menu, petitioned_ipfs_service_keys, rescind_unpin_phrase, 'Rescind the pending unpin from the ipfs service.', self._RescindPetitionFiles )
                        
                    
                    if multiple_selected and len( ipfs_service_keys ) > 0:
                        
                        ClientGUIMediaMenus.AddServiceKeysToMenu( locations_menu, ipfs_service_keys, 'pin new directory to', 'Pin these files as a directory to the ipfs service.', self._UploadDirectory )
                        
                    
                
            
            #
            
            ClientGUIMediaMenus.AddKnownURLsViewCopyMenu( self, self, menu, self._focused_media, num_selected, selected_media = self._selected_media )
            
            ClientGUIMediaMenus.AddOpenMenu( self, self, menu, self._focused_media, self._selected_media )
            
            ClientGUIMediaMenus.AddShareMenu( self, self, menu, self._focused_media, self._selected_media )
            
        
        if not do_not_show_just_return:
            
            CGC.core().PopupMenu( self, menu )
            
        
        else:
            
            return menu
            
        
    
    def Sort( self, media_sort = None ):
        
        super().Sort( media_sort )
        
        self._NotifyThumbnailsHaveMoved()
        
    
    def ThumbnailsReset( self ):
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        thumbnail_scroll_rate = float( CG.client_controller.new_options.GetString( 'thumbnail_scroll_rate' ) )
        
        self.verticalScrollBar().setSingleStep( int( round( thumbnail_span_height * thumbnail_scroll_rate ) ) )
        
        self._hashes_to_thumbnails_waiting_to_be_drawn = {}
        self._hashes_faded = set()
        
        self._ReinitialisePageCacheIfNeeded()
        
        self._RecalculateVirtualSize()
        
        self.RedrawAllThumbnails()
        
    
    def TIMERAnimationUpdate( self ):
        
        loop_should_break_time = HydrusTime.GetNowPrecise() + ( FRAME_DURATION_60FPS / 2 )
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        thumbnail_margin = CG.client_controller.new_options.GetInteger( 'thumbnail_margin' )
        
        hashes = list( self._hashes_to_thumbnails_waiting_to_be_drawn.keys() )
        
        page_indices_to_painters = {}
        
        page_height = self._num_rows_per_canvas_page * thumbnail_span_height
        
        for hash in HydrusData.IterateListRandomlyAndFast( hashes ):
            
            thumbnail_draw_object = self._hashes_to_thumbnails_waiting_to_be_drawn[ hash ]
            
            delete_entry = False
            
            if thumbnail_draw_object.DrawDue():
                
                thumbnail_index = thumbnail_draw_object.thumbnail_index
                
                try:
                    
                    expected_thumbnail = self._sorted_media[ thumbnail_index ]
                    
                except:
                    
                    expected_thumbnail = None
                    
                
                page_index = self._GetPageIndexFromThumbnailIndex( thumbnail_index )
                
                if expected_thumbnail != thumbnail_draw_object.thumbnail:
                    
                    delete_entry = True
                    
                elif page_index not in self._clean_canvas_pages:
                    
                    delete_entry = True
                    
                else:
                    
                    thumbnail_col = thumbnail_index % self._num_columns
                    
                    thumbnail_row = thumbnail_index // self._num_columns
                    
                    x = thumbnail_col * thumbnail_span_width + thumbnail_margin
                    
                    y = ( thumbnail_row - ( page_index * self._num_rows_per_canvas_page ) ) * thumbnail_span_height + thumbnail_margin
                    
                    if page_index not in page_indices_to_painters:
                        
                        canvas_page = self._clean_canvas_pages[ page_index ]
                        
                        painter = QG.QPainter( canvas_page )
                        
                        page_indices_to_painters[ page_index ] = painter
                        
                    
                    painter = page_indices_to_painters[ page_index ]
                    
                    thumbnail_draw_object.DrawToPainter( x, y, painter )
                    
                    #
                    
                    page_virtual_y = page_height * page_index
                    
                    self.widget().update( QC.QRect( x, page_virtual_y + y, thumbnail_span_width - thumbnail_margin, thumbnail_span_height - thumbnail_margin ) )
                    
                
            
            if thumbnail_draw_object.DrawComplete() or delete_entry:
                
                del self._hashes_to_thumbnails_waiting_to_be_drawn[ hash ]
                
            
            if HydrusTime.TimeHasPassedPrecise( loop_should_break_time ):
                
                break
                
            
        
        if len( self._hashes_to_thumbnails_waiting_to_be_drawn ) == 0:
            
            CG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
            
        
        
    
    def WaterfallThumbnails( self, page_key, thumbnails ):
        
        if self._page_key == page_key:
            
            self._FadeThumbnails( thumbnails )
            
        
    
    class _InnerWidget( QW.QWidget ):
        
        def __init__( self, parent: "MediaResultsPanelThumbnails" ):
            
            super().__init__( parent )
            
            self.setMouseTracking( True )
            
            self._parent = parent
            
        
        def mouseMoveEvent( self, event ):
            
            self._parent.DoMouseMoveEvent( event )
            
        
        def mousePressEvent( self, event ):
            
            self._parent._drag_init_coordinates = QG.QCursor.pos()
            self._parent._drag_click_timestamp_ms = HydrusTime.GetNowMS()
            
            thumb = self._parent._GetThumbnailUnderMouse( event )
            
            right_on_whitespace = event.button() == QC.Qt.MouseButton.RightButton and thumb is None
            
            if not right_on_whitespace:
                
                self._parent._HitMedia( thumb, event.modifiers() & QC.Qt.KeyboardModifier.ControlModifier, event.modifiers() & QC.Qt.KeyboardModifier.ShiftModifier )
                
            
            # this specifically does not scroll to media, as for clicking (esp. double-clicking attempts), the scroll can be jarring
            
        
        def paintEvent( self, event ):
            
            if self._parent.devicePixelRatio() != self._parent._last_device_pixel_ratio:
                
                self._parent._last_device_pixel_ratio = self._parent.devicePixelRatio()
                
                self._parent._DirtyAllPages()
                self._parent._DeleteAllDirtyPages()
                
            
            painter = QG.QPainter( self )
            
            ( thumbnail_span_width, thumbnail_span_height ) = self._parent._GetThumbnailSpanDimensions()
            
            page_height = self._parent._num_rows_per_canvas_page * thumbnail_span_height
            
            page_indices_to_display = self._parent._CalculateVisiblePageIndices()
            
            earliest_page_index_to_display = min( page_indices_to_display )
            last_page_index_to_display = max( page_indices_to_display )
            
            page_indices_to_draw = list( page_indices_to_display )
            
            if earliest_page_index_to_display > 0:
                
                page_indices_to_draw.append( earliest_page_index_to_display - 1 )
                
            
            page_indices_to_draw.append( last_page_index_to_display + 1 )
            
            page_indices_to_draw.sort()
            
            potential_clean_indices_to_steal = [ page_index for page_index in self._parent._clean_canvas_pages.keys() if page_index not in page_indices_to_draw ]
            
            random.shuffle( potential_clean_indices_to_steal )
            
            y_start = self._parent._GetYStart()
            
            bg_colour = self._parent.GetColour( CC.COLOUR_THUMBGRID_BACKGROUND )
            
            painter.setBackground( QG.QBrush( bg_colour ) )
            
            painter.eraseRect( painter.viewport() )
            
            background_pixmap = CG.client_controller.bitmap_manager.GetMediaBackgroundPixmap()
            
            if background_pixmap is not None:
                
                my_size = QP.ScrollAreaVisibleRect( self._parent ).size()
                
                pixmap_size = background_pixmap.size()
                
                painter.drawPixmap( my_size.width() - pixmap_size.width(), my_size.height() - pixmap_size.height(), background_pixmap )
                
            
            for page_index in page_indices_to_draw:
                
                if page_index not in self._parent._clean_canvas_pages:
                    
                    if len( self._parent._dirty_canvas_pages ) == 0:
                        
                        if len( potential_clean_indices_to_steal ) > 0:
                            
                            index_to_steal = potential_clean_indices_to_steal.pop()
                            
                            self._parent._DirtyPage( index_to_steal )
                            
                        else:
                            
                            self._parent._CreateNewDirtyPage()
                            
                        
                    
                    canvas_page = self._parent._dirty_canvas_pages.pop()
                    
                    self._parent._DrawCanvasPage( page_index, canvas_page )
                    
                    self._parent._clean_canvas_pages[ page_index ] = canvas_page
                    
                
                if page_index in page_indices_to_display:
                    
                    canvas_page = self._parent._clean_canvas_pages[ page_index ]
                    
                    page_virtual_y = page_height * page_index
                    
                    painter.drawImage( 0, page_virtual_y, canvas_page )
                    
                
            
        
    

class Selectable( object ):
    
    def __init__( self, *args, **kwargs ):
        
        self._selected = False
        
        super().__init__( *args, **kwargs )
        
    
    def Deselect( self ): self._selected = False
    
    def IsSelected( self ): return self._selected
    
    def Select( self ): self._selected = True
    

def ShouldShowRatingInThumbnail( media: ClientMedia.Media, service_key: bytes ) -> bool:
    
    try:
        
        service = CG.client_controller.services_manager.GetService( service_key )
        
        show_in_thumbnail = service.GetShowInThumbnail()
        show_in_thumbnail_even_when_null = service.GetShowInThumbnailEvenWhenNull()
        
        if not show_in_thumbnail:
            
            return False
            
        
        if show_in_thumbnail_even_when_null:
            
            return True
            
        else:
            
            service_type = service.GetServiceType()
            
            if service_type == HC.LOCAL_RATING_LIKE:
                
                rating_state = ClientRatings.GetLikeStateFromMedia( ( media, ), service_key )
                
                return rating_state in ( ClientRatings.LIKE, ClientRatings.DISLIKE )
                
            elif service_type == HC.LOCAL_RATING_NUMERICAL:
                
                ( rating_state, rating ) = ClientRatings.GetNumericalStateFromMedia( ( media, ), service_key )
                
                return rating_state == ClientRatings.SET
                
            elif service_type == HC.LOCAL_RATING_INCDEC:
                
                ( rating_state, rating ) = ClientRatings.GetIncDecStateFromMedia( ( media, ), service_key )
                
                return rating_state == ClientRatings.SET and rating != 0
                
            else:
                
                raise NotImplementedError( 'Do not understand the rating service!' )
                
            
        
    except HydrusExceptions.DataMissing:
        
        return False
        
    

class Thumbnail( Selectable ):
    
    def __init__( self, *args, **kwargs ):
        
        super().__init__( *args, **kwargs )
        
        self._last_tags = None
        
        self._last_upper_summary = None
        self._last_lower_summary = None
        
    
    def ClearTagSummaryCaches( self ):
        
        self._last_tags = None
        
        self._last_upper_summary = None
        self._last_lower_summary = None
        
    
    def GetQtImage( self, media: ClientMedia.Media, media_panel: ClientGUIMediaResultsPanel.MediaResultsPanel, device_pixel_ratio ) -> QG.QImage:
        
        # we probably don't really want to say DPR as a param here, but instead ask for a qt_image in a certain resolution?
        # or just give the qt_image to be drawn to?
        # or just give a painter and a rect and draw to that or something
        # we don't really want to mess around with DPR here, we just want to draw thumbs
        # that said, this works after a medium-high headache getting it there, so let's not get ahead of ourselves
        
        if media.GetDisplayMedia() is None:
            
            thumbnail_hydrus_bmp = CG.client_controller.thumbnails_cache.GetHydrusPlaceholderThumbnail()
            
        else:
            
            thumbnail_hydrus_bmp = CG.client_controller.thumbnails_cache.GetThumbnail( media.GetDisplayMedia().GetMediaResult() )
            
        
        thumbnail_border = CG.client_controller.new_options.GetInteger( 'thumbnail_border' )
        
        ( width, height ) = ClientData.AddPaddingToDimensions( HC.options[ 'thumbnail_dimensions' ], thumbnail_border * 2 )
        
        qt_image_width = int( width * device_pixel_ratio )
        
        qt_image_height = int( height * device_pixel_ratio )
        
        qt_image = CG.client_controller.bitmap_manager.GetQtImage( qt_image_width, qt_image_height, 24 )
        
        qt_image.setDevicePixelRatio( device_pixel_ratio )
        
        # TODO: obviously this is the lynchpin of remaining ugly rewrites. we want to re-wangle this guy out of the Media system and broadly decouple this knot entirely
        # Step one I am doing is fixing the linting by passing the Media object as an explicit param rather than asking self.HasInbox() etc.., despite that Media secretly being self
        
        inbox = media.HasInbox()
        
        local = media.GetLocationsManager().IsLocal()
        
        #
        # BAD FONT QUALITY AT 100% UI Scale (semi fixed now, look at the bottom)
        #
        # Ok I have spent hours on this now trying to figure it out and can't, so I'll just write about it for when I come back
        # So, if you boot with two monitors at 100% UI scale, the text here on a QImage is ugly, but on QWidget it is fine
        # If you boot with one monitor at 125%, the text is beautiful on QImage both screens
        # My current assumption is booting Qt with unusual UI scales triggers some extra init and that spills over to QImage QPainter initialisation
        #
        # I checked painter hints, font stuff, fontinfo and fontmetrics, and the only difference was with fontmetrics, on all-100% vs one >100%:
        # minLeftBearing: -1, -7
        # minRightBearing: -1, -8
        # xHeight: 3, 6
        #
        # The fontmetric produced a text size one pixel less wide on the both-100% run, so it is calculating different
        # However these differences are global to the program so don't explain why painting on a QImage specifically has bad font rather than QWidget
        # The ugly font is anti-aliased, but it looks like not drawn with sub-pixel calculations, like ClearType isn't kicking in or something
        # If I blow the font size up to 72, there is still a difference in screenshots between the all-100% and some >100% boot.
        # So, maybe if the program boots with any weird UI scale going on, Qt kicks in a different renderer for all QImages, the same renderer for QWidgets, perhaps more expensively
        # Or this is just some weird bug
        # Or I am still missing some flag
        #
        # bit like this https://stackoverflow.com/questions/31043332/qt-antialiasing-of-vertical-text-rendered-using-qpainter
        #
        # EDIT: OK, I 'fixed' it with setStyleStrategy( preferantialias ), which has no change in 125%, but in all-100% it draws something different but overall better quality
        # Note you can't setStyleStrategy on the font when it is in the QPainter. either it gets set read only or there is some other voodoo going on
        # It does look very slightly weird, but it is a step up so I won't complain. it really seems like the isolated QPainter of only-100% world has some different initialisation. it just can't find the nice font renderer
        #
        # EDIT 2: I think it may only look weird when the thumb banner has opacity. Maybe I need to learn about CompositionModes
        #
        # EDIT 3: Appalently Qt 6.4.0 may fix the basic 100% UI scale QImage init bug!
        #
        # UPDATE 3a: Qt 6.4.x did not magically fix it. It draws much nicer, but still a different font weight/metrics compared to media viewer background, say.
        # The PreferAntialias flag on 6.4.x seems to draw very very close to our ideal, so let's be happy with it for now.
        
        painter = QG.QPainter( qt_image )
        
        painter.setRenderHint( QG.QPainter.RenderHint.TextAntialiasing, True ) # is true already in tests, is supposed to be 'the way' to fix the ugly text issue
        painter.setRenderHint( QG.QPainter.RenderHint.Antialiasing, True ) # seems to do nothing, it only affects primitives?
        painter.setRenderHint( QG.QPainter.RenderHint.SmoothPixmapTransform, True ) # makes the thumb QImage scale up and down prettily when we need it, either because it is too small or DPR gubbins
        
        new_options = CG.client_controller.new_options
        
        if not local:
            
            if self._selected:
                
                background_colour_type = CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED
                
            else:
                
                background_colour_type = CC.COLOUR_THUMB_BACKGROUND_REMOTE
                
            
        else:
            
            if self._selected:
                
                background_colour_type = CC.COLOUR_THUMB_BACKGROUND_SELECTED
                
            else:
                
                background_colour_type = CC.COLOUR_THUMB_BACKGROUND
                
            
        
        # the painter isn't getting QSS style from the qt_image, we need to set the font explitly to get font size changes from QSS etc..
        
        f = QG.QFont( CG.client_controller.gui.font() )
        
        # this line magically fixes the bad text, as above
        f.setStyleStrategy( QG.QFont.StyleStrategy.PreferAntialias )
        
        f.setBold( False )
        
        painter.setFont( f )
        
        qss_window_colour = media_panel.palette().color( QG.QPalette.ColorRole.Window )
        qss_text_colour = media_panel.palette().color( QG.QPalette.ColorRole.WindowText )
        
        media_panel_background_colour = media_panel.GetColour( background_colour_type )
        
        painter.fillRect( thumbnail_border, thumbnail_border, width - ( thumbnail_border * 2 ), height - ( thumbnail_border * 2 ), media_panel_background_colour )
        
        raw_thumbnail_qt_image = thumbnail_hydrus_bmp.GetQtImage()
        
        thumbnail_dpr_percent = new_options.GetInteger( 'thumbnail_dpr_percent' )
        
        if thumbnail_dpr_percent != 100:
            
            thumbnail_dpr = thumbnail_dpr_percent / 100
            
            raw_thumbnail_qt_image.setDevicePixelRatio( thumbnail_dpr )
            
            # qt_image.deviceIndepedentSize isn't supported in Qt5 lmao
            device_independent_thumb_size = raw_thumbnail_qt_image.size() / thumbnail_dpr
            
        else:
            
            device_independent_thumb_size = raw_thumbnail_qt_image.size()
            
        
        x_offset = ( width - device_independent_thumb_size.width() ) // 2
        
        y_offset = ( height - device_independent_thumb_size.height() ) // 2
        
        painter.drawImage( x_offset, y_offset, raw_thumbnail_qt_image )
        
        TEXT_BORDER = 1
        
        tags = media.GetTagsManager().GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_SINGLE_MEDIA )
        
        if len( tags ) > 0:
            
            upper_tag_summary_generator = new_options.GetTagSummaryGenerator( 'thumbnail_top' )
            lower_tag_summary_generator = new_options.GetTagSummaryGenerator( 'thumbnail_bottom_right' )
            
            if self._last_tags is not None and self._last_tags == tags:
                
                upper_summary = self._last_upper_summary
                lower_summary = self._last_lower_summary
                
            else:
                
                upper_summary = upper_tag_summary_generator.GenerateSummary( tags )
                
                lower_summary = lower_tag_summary_generator.GenerateSummary( tags )
                
                self._last_tags = set( tags )
                
                self._last_upper_summary = upper_summary
                self._last_lower_summary = lower_summary
                
            
            if len( upper_summary ) > 0 or len( lower_summary ) > 0:
                
                if len( upper_summary ) > 0:
                    
                    text_colour_with_alpha = upper_tag_summary_generator.GetTextColour()
                    
                    background_colour_with_alpha = upper_tag_summary_generator.GetBackgroundColour()
                    
                    ( text_size, upper_summary ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, upper_summary )
                    
                    box_x = thumbnail_border
                    box_y = thumbnail_border
                    box_width = width - ( thumbnail_border * 2 )
                    box_height = text_size.height() + 2
                    
                    painter.fillRect( box_x, box_y, box_width, box_height, background_colour_with_alpha )
                    
                    text_x = ( width - text_size.width() ) // 2
                    text_y = box_y + TEXT_BORDER
                    
                    painter.setPen( QG.QPen( text_colour_with_alpha ) )
                    
                    ClientGUIFunctions.DrawText( painter, text_x, text_y, upper_summary )
                    
                
                if len( lower_summary ) > 0:
                    
                    text_colour_with_alpha = lower_tag_summary_generator.GetTextColour()
                    
                    background_colour_with_alpha = lower_tag_summary_generator.GetBackgroundColour()
                    
                    ( text_size, lower_summary ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, lower_summary )
                    
                    text_width = text_size.width()
                    text_height = text_size.height()
                    
                    box_width = text_width + ( TEXT_BORDER * 2 )
                    box_height = text_height + ( TEXT_BORDER * 2 )
                    box_x = width - box_width - thumbnail_border
                    box_y = height - text_height - thumbnail_border
                    
                    painter.fillRect( box_x, box_y, box_width, box_height, background_colour_with_alpha )
                    
                    text_x = box_x + TEXT_BORDER
                    text_y = box_y + TEXT_BORDER
                    
                    painter.setPen( QG.QPen( text_colour_with_alpha ) )
                    
                    ClientGUIFunctions.DrawText( painter, text_x, text_y, lower_summary )
                    
                
            
        
        if thumbnail_border > 0:
            
            if not local:
                
                if self._selected:
                    
                    border_colour_type = CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED
                    
                else:
                    
                    border_colour_type = CC.COLOUR_THUMB_BORDER_REMOTE
                    
                
            else:
                
                if self._selected:
                    
                    border_colour_type = CC.COLOUR_THUMB_BORDER_SELECTED
                    
                else:
                    
                    border_colour_type = CC.COLOUR_THUMB_BORDER
                    
                
            
            # I had a hell of a time getting a transparent box to draw right with a pen border without crazy +1px in the params for reasons I did not understand
            # so I just decided four rects is neater and fine and actually prob faster in some cases
            
            #         _____            ______                              _____            ______      ________________
            # ___________(_)___  _________  /_______   _______ ______      __  /______      ___  /_________  /__  /__  /
            # ___  __ \_  /__  |/_/  _ \_  /__  ___/   __  __ `/  __ \     _  __/  __ \     __  __ \  _ \_  /__  /__  / 
            # __  /_/ /  / __>  < /  __/  / _(__  )    _  /_/ // /_/ /     / /_ / /_/ /     _  / / /  __/  / _  /  /_/  
            # _  .___//_/  /_/|_| \___//_/  /____/     _\__, / \____/      \__/ \____/      /_/ /_/\___//_/  /_/  (_)   
            # /_/                                      /____/                                                            
            
            bd_colour = media_panel.GetColour( border_colour_type )
            
            painter.setBrush( QG.QBrush( bd_colour ) )
            painter.setPen( QG.QPen( QC.Qt.PenStyle.NoPen ) )
            
            rectangles = []
            
            side_height = height - ( thumbnail_border * 2 )
            rectangles.append( QC.QRectF( 0, 0, width, thumbnail_border ) ) # top
            rectangles.append( QC.QRectF( 0, height - thumbnail_border, width, thumbnail_border ) ) # bottom
            rectangles.append( QC.QRectF( 0, thumbnail_border, thumbnail_border, side_height ) ) # left
            rectangles.append( QC.QRectF( width - thumbnail_border, thumbnail_border, thumbnail_border, side_height ) ) # right
            
            painter.drawRects( rectangles )
            
        
        
        locations_manager = media.GetLocationsManager()
        
        # ratings
        THUMBNAIL_RATING_ICON_SET_SIZE = round( new_options.GetFloat( 'draw_thumbnail_rating_icon_size_px' ) )
        THUMBNAIL_RATING_INCDEC_SET_WIDTH = round( new_options.GetFloat( 'thumbnail_rating_incdec_width_px' ) )
        STAR_DX = THUMBNAIL_RATING_ICON_SET_SIZE
        STAR_DY = THUMBNAIL_RATING_ICON_SET_SIZE
        
        ICON_PAD = ClientGUIPainterShapes.PAD_PX #4px constant pad between each shape
        
        ICON_MARGIN = 1
        
        draw_thumbnail_rating_background = new_options.GetBoolean( 'draw_thumbnail_rating_background' )
        
        current_top_right_y = thumbnail_border
        
        services_manager = CG.client_controller.services_manager
        
        
        like_services = services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ) )
        
        like_services_to_show = [ like_service for like_service in like_services if ShouldShowRatingInThumbnail( media, like_service.GetServiceKey() ) ]
        
        num_to_show = len( like_services_to_show )
        
        if num_to_show > 0:
            
            rect_width = ( STAR_DX * num_to_show ) + ( ICON_PAD * ( num_to_show - 1 ) ) + ( ICON_MARGIN * 2 )
            rect_height = STAR_DY + ICON_PAD + ( ICON_MARGIN * 2 )
            
            rect_x = width - thumbnail_border - rect_width
            rect_y = current_top_right_y
            
            if draw_thumbnail_rating_background:
                
                painter.fillRect( rect_x, rect_y, rect_width, rect_height, qss_window_colour )
                
            
            like_rating_current_x = rect_x + round( ICON_PAD / 2 )
            like_rating_current_y = rect_y + round( ICON_PAD / 2 )
            
            for like_service in like_services_to_show:
                
                service_key = like_service.GetServiceKey()
                
                rating_state = ClientRatings.GetLikeStateFromMedia( ( media, ), service_key )
                
                ClientGUIRatings.DrawLike( painter, like_rating_current_x, like_rating_current_y, service_key, rating_state, QC.QSize( STAR_DX, STAR_DY ) )
                
                like_rating_current_x += STAR_DX + ICON_PAD
                
            
            current_top_right_y += rect_height
            
        
        
        numerical_services = services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        draw_collapsed_numerical_ratings = new_options.GetBoolean( 'draw_thumbnail_numerical_ratings_collapsed_always' )
        
        numerical_services_to_show = [ numerical_service for numerical_service in numerical_services if ShouldShowRatingInThumbnail( media, numerical_service.GetServiceKey() ) ]
        
        for numerical_service in numerical_services_to_show:
            
            service_key = numerical_service.GetServiceKey()
            
            custom_pad = numerical_service.GetCustomPad()
            
            ( rating_state, rating ) = ClientRatings.GetNumericalStateFromMedia( ( media, ), service_key )
            
            numerical_width = ClientGUIRatings.GetNumericalWidth( service_key, STAR_DX, None, draw_collapsed_numerical_ratings, rating_state, rating )
            
            rect_width = numerical_width + ( ICON_MARGIN * 2 ) #icon padding is included in GetNumericalWidth
            rect_height = STAR_DY + ICON_PAD + ( ICON_MARGIN * 2 )
            
            rect_x = width - thumbnail_border - rect_width
            rect_y = current_top_right_y
            
            if draw_thumbnail_rating_background:
                
                painter.fillRect( rect_x, rect_y, rect_width, rect_height, qss_window_colour )
                
            
            numerical_rating_current_x = rect_x + round( ICON_PAD / 2 )
            numerical_rating_current_y = rect_y + round( ICON_PAD / 2 )
            
            ClientGUIRatings.DrawNumerical( painter, numerical_rating_current_x, numerical_rating_current_y, service_key, rating_state, rating, QC.QSize( STAR_DX, STAR_DY ), custom_pad, draw_collapsed_numerical_ratings )
            
            current_top_right_y += rect_height
            
        
        
        incdec_services = services_manager.GetServices( ( HC.LOCAL_RATING_INCDEC, ) )
        
        incdec_services_to_show = [ incdec_service for incdec_service in incdec_services if ShouldShowRatingInThumbnail( media, incdec_service.GetServiceKey() ) ]
        
        num_to_show = len( incdec_services_to_show )
        
        if num_to_show > 0:
            
            control_width = THUMBNAIL_RATING_INCDEC_SET_WIDTH
            control_height = round( THUMBNAIL_RATING_INCDEC_SET_WIDTH / 2 )
            
            rect_width = ( control_width * num_to_show ) + ( ICON_MARGIN * 2 ) + ( ICON_MARGIN * ( num_to_show - 1 ) )
            rect_height = control_height + ( ICON_MARGIN * 2 )
            
            rect_x = width - thumbnail_border - rect_width
            rect_y = current_top_right_y
            
            if draw_thumbnail_rating_background:
                
                painter.fillRect( rect_x, rect_y, rect_width, rect_height, qss_window_colour )
                
            
            incdec_rating_current_x = rect_x
            incdec_rating_current_y = rect_y + ICON_MARGIN
            
            for incdec_service in incdec_services_to_show:
                
                service_key = incdec_service.GetServiceKey()
                
                ( rating_state, rating ) = ClientRatings.GetIncDecStateFromMedia( ( media, ), service_key )
                
                incdec_rating_current_x += ICON_MARGIN
                
                ClientGUIRatings.DrawIncDec( painter, incdec_rating_current_x, incdec_rating_current_y, service_key, rating_state, rating, QC.QSize( control_width, control_height ), QC.QSize( ICON_PAD, ICON_MARGIN ) )
                
                incdec_rating_current_x += control_width
                
            
            current_top_right_y += rect_height
            
        
        # icons
        
        icons_to_draw = []
        
        if locations_manager.IsDownloading():
            
            icons_to_draw.append( CC.global_pixmaps().downloading )
            
        
        if media.HasNotes():
            
            icons_to_draw.append( CC.global_pixmaps().notes )
            
        
        if locations_manager.IsTrashed() or CC.COMBINED_LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted():
            
            icons_to_draw.append( CC.global_pixmaps().trash )
            
        
        if inbox:
            
            icons_to_draw.append( CC.global_pixmaps().inbox )
            
        
        if len( icons_to_draw ) > 0:
            
            icon_x = - ( thumbnail_border + ICON_MARGIN )
            
            for icon in icons_to_draw:
                
                icon_x -= icon.width()
                
                painter.drawPixmap( width + icon_x, current_top_right_y, icon )
                
                icon_x -= 2 * ICON_MARGIN
                
            
        
        if media.IsCollection():
            
            icon = CC.global_pixmaps().collection
            
            num_files_str = HydrusNumbers.ToHumanInt( media.GetNumFiles() )
            
            ( text_size, num_files_str ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, num_files_str )
            
            text_width = text_size.width()
            text_height = text_size.height()
            
            box_width = icon.width() + text_width + ( ICON_MARGIN * 3 )
            box_height = max( icon.height(), text_height ) + ( ICON_MARGIN * 2 )
            
            box_x = thumbnail_border
            box_y = height - thumbnail_border - box_height
            
            painter.fillRect( box_x, box_y, box_width, box_height, qss_window_colour )
            
            icon_x = box_x + ICON_MARGIN
            icon_y = ( box_y + box_height ) - ICON_MARGIN - icon.height()
            
            painter.drawPixmap( icon_x, icon_y, icon )
            
            painter.setPen( QG.QPen( qss_text_colour ) )
            
            text_x = icon_x + icon.width() + ICON_MARGIN
            text_y = box_y + ICON_MARGIN
            
            ClientGUIFunctions.DrawText( painter, text_x, text_y, num_files_str )
            
        
        # top left icons
        
        icons_to_draw = []
        
        if media.HasAudio():
            
            icons_to_draw.append( CC.global_pixmaps().sound )
            
        elif media.HasDuration():
            
            icons_to_draw.append( CC.global_pixmaps().play )
            
        
        services_manager = CG.client_controller.services_manager
        
        remote_file_service_keys = CG.client_controller.services_manager.GetRemoteFileServiceKeys()
        
        current = locations_manager.GetCurrent().intersection( remote_file_service_keys )
        pending = locations_manager.GetPending().intersection( remote_file_service_keys )
        petitioned = locations_manager.GetPetitioned().intersection( remote_file_service_keys )
        
        current_to_display = current.difference( petitioned )
        
        #
        
        service_types = [ services_manager.GetService( service_key ).GetServiceType() for service_key in current_to_display ]
        
        if HC.FILE_REPOSITORY in service_types:
            
            icons_to_draw.append( CC.global_pixmaps().file_repository )
            
        
        if HC.IPFS in service_types:
            
            icons_to_draw.append( CC.global_pixmaps().ipfs )
            
        
        #
        
        service_types = [ services_manager.GetService( service_key ).GetServiceType() for service_key in pending ]
        
        if HC.FILE_REPOSITORY in service_types:
            
            icons_to_draw.append( CC.global_pixmaps().file_repository_pending )
            
        
        if HC.IPFS in service_types:
            
            icons_to_draw.append( CC.global_pixmaps().ipfs_pending )
            
        
        #
        
        service_types = [ services_manager.GetService( service_key ).GetServiceType() for service_key in petitioned ]
        
        if HC.FILE_REPOSITORY in service_types:
            
            icons_to_draw.append( CC.global_pixmaps().file_repository_petitioned )
            
        
        if HC.IPFS in service_types:
            
            icons_to_draw.append( CC.global_pixmaps().ipfs_petitioned )
            
        
        top_left_x = thumbnail_border + ICON_MARGIN
        
        for icon_to_draw in icons_to_draw:
            
            painter.drawPixmap( top_left_x, thumbnail_border + ICON_MARGIN, icon_to_draw )
            
            top_left_x += icon_to_draw.width() + ( ICON_MARGIN * 2 )
            
        
        return qt_image
        
    

# TODO: This is another area of OOD inheritance garbage. just rewrite the whole damn thing, stop trying to do everything in one class, decouple and you'll lose the linter freakout over GetQtImage's references and related __init__ headaches
class ThumbnailMediaCollection( Thumbnail, ClientMedia.MediaCollection ):
    
    def __init__( self, location_context, media_results ):
        
        super().__init__( location_context, media_results )
        
    
class ThumbnailMediaSingleton( Thumbnail, ClientMedia.MediaSingleton ):
    
    def __init__( self, media_result ):
        
        super().__init__( media_result )
        
    
