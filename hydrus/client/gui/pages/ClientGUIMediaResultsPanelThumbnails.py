import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

import hydrus.core.HydrusData
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientServices
from hydrus.client.files import ClientFilesMaintenance
from hydrus.client.gui import ClientGUIDragDrop
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIRatings
from hydrus.client.gui import ClientGUIThumbnailLayouts
from hydrus.client.gui.media import ClientGUIMediaSimpleActions
from hydrus.client.gui.media import ClientGUIMediaModalActions
from hydrus.client.gui.media import ClientGUIMediaMenus
from hydrus.client.gui.pages import ClientGUIPageManager
from hydrus.client.gui.pages import ClientGUIMediaResultsPanel
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelMenus
from hydrus.client.gui.widgets import ClientGUIPainterShapes
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaFileFilter
from hydrus.client.media import ClientMediaList
from hydrus.client.media import ClientMediaResultPrettyInfo
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientRatings

FRAME_DURATION_60FPS = 1.0 / 60

class MediaResultsPanelThumbnails( ClientGUIMediaResultsPanel.MediaResultsPanel ):
    
    def __init__( self, parent, page_key, page_manager: ClientGUIPageManager.PageManager, media_results ):
        
        self._drag_init_coordinates = None
        self._drag_click_timestamp_ms = 0
        self._drag_prefire_event_count = 0
        
        self._media_to_thumbnails = {} # associates medias with their Thumbnails (which are Qt GraphicsItems and live in the QGraphicsScene)
        self._possibly_visible_thumbnails = set() # this is a quick cache-like thing to keep a list of thumbnails that might be in the viewport, for animation/drawing purposes
        
        # this should come from the application settings, and then the page's own settings (so each page can have its separate layout),
        # but for now it's hardcoded
        # leaving a few options here commented out for demo purposes
        self._thumbnail_layout: ClientGUIThumbnailLayouts.ThumbnailLayout = ClientGUIThumbnailLayouts.MasonryLayout( ClientGUIThumbnailLayouts.MasonryLayout.VariableDimension.HEIGHT )
        #self._thumbnail_layout: ClientGUIThumbnailLayouts.ThumbnailLayout = ClientGUIThumbnailLayouts.MasonryLayout( ClientGUIThumbnailLayouts.MasonryLayout.VariableDimension.WIDTH )
        #self._thumbnail_layout: ClientGUIThumbnailLayouts.ThumbnailLayout = ClientGUIThumbnailLayouts.RegularGridLayout()
        
        self._last_animation_update_time = HydrusTime.GetNowPrecise()
        
        super().__init__( parent, page_key, page_manager, media_results )
        
        self.visibleRectChanged.connect( self._OnVisibleRectChanged )
        
        self._my_current_drag_object = None
        
        self._ArrangeThumbnails()
        
        self._ResetThumbnailScrollSingleStep()
        
        CG.client_controller.sub( self, 'MaintainPageCache', 'memory_maintenance_pulse' )
        CG.client_controller.sub( self, 'NotifyFilesNeedRedraw', 'notify_files_need_redraw' )
        CG.client_controller.sub( self, 'NewThumbnails', 'new_thumbnails' )
        CG.client_controller.sub( self, 'ThumbnailsReset', 'notify_complete_thumbnail_reset' )
        CG.client_controller.sub( self, 'RedrawAllThumbnails', 'refresh_all_tag_presentation_gui' )
        CG.client_controller.sub( self, 'WaterfallThumbnails', 'waterfall_thumbnails' )
        
        CG.client_controller.gui.RegisterAnimationUpdateWindow( self )
        
    
    def _ArrangeThumbnails( self ):
        
        new_scene_rect = self._thumbnail_layout.ArrangeThumbnails( self._media_to_thumbnails.values(), self._CollectLayoutParams() )
        
        self.setSceneRect( new_scene_rect )
        
        # do a forced update here, since even if the visible rect of the scene itself hasn't changed, new thumbs might have appeared / removed ones disappeared
        # without this newly appearing thumbs on e.g. a download page would not be visible until a scene rect update happens for some other reason
        self._VisibleRectUpdate( force = True )
        
    
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
        
    
    def _CollectLayoutParams( self ) -> ClientGUIThumbnailLayouts.LayoutParams:
        
        thumbnail_border = CG.client_controller.new_options.GetInteger( 'thumbnail_border' )
        thumb_width, thumb_height = ClientData.AddPaddingToDimensions( HC.options[ 'thumbnail_dimensions' ], thumbnail_border * 2 )
        thumb_content_width, thumb_content_height = HC.options[ 'thumbnail_dimensions' ]
        thumbnail_margin = CG.client_controller.new_options.GetInteger( 'thumbnail_margin' )
        
        # this is now mostly hardcoded for demo purposes, but should come from:
        # 1. settings / application-widge defaults
        # 2. each page could also have some config GUI to change these parameters,
        #    e.g. would be cool to have a quick zoom slider or something to change zoom, or a switch between horizontal/vertical scrolling etc. 
        return ClientGUIThumbnailLayouts.LayoutParams(
            viewport_width = self.viewport().width(),
            viewport_height = self.viewport().height(),
            thumb_width = thumb_width,
            thumb_height = thumb_height,
            thumb_content_width = thumb_content_width,
            thumb_content_height = thumb_content_height,
            thumb_margin_vertical = thumbnail_margin,
            thumb_margin_horizontal = thumbnail_margin,
            scene_margin_vertical = 0,
            scene_margin_horizontal = 0,
            scroll_direction = ClientGUIThumbnailLayouts.ScrollDirection.HORIZONTAL,
            content_alignment = QC.Qt.AlignmentFlag.AlignHCenter, # layouts will ignore alignments that don't make sense for them or with the selected scroll direction
            zoom = 1.0
        )
        
    
    def _FadeThumbnails( self, media ):
        
        fade_thumbnails = CG.client_controller.new_options.GetBoolean( 'fade_thumbnails' )
        
        for m in media:
            
            if fade_thumbnails:
                
                self._media_to_thumbnails[ m ].StartFadeIn()
                
            else:
                
                self._media_to_thumbnails[ m ].update()
                
            
        
    
    def _IsMediaInRect( self, rect, media ):
        
        return self._media_to_thumbnails[ media ].sceneBoundingRect().intersects( rect )
        
    
    def _IsMediaSelected( self, media: ClientMedia.Media ) -> bool:
        
        thumb = self._media_to_thumbnails.get( media )
        
        if thumb is not None:
            
            return thumb.isSelected()
            
        return False
        
    
    def _MaintainMediaAssociatedGraphics( self, media ):
        
        for m in media:
            
            if not m in self._sorted_media: # not in media list anymore -> was removed, so we need to remove the corresponding thumbnail
                
                thumb = self._media_to_thumbnails.get( m )
                
                if thumb is not None:
                    
                    self.scene().removeItem( thumb )
                    self._possibly_visible_thumbnails.discard( thumb )
                    del self._media_to_thumbnails[ m ]
                    
                
            elif not m in self._media_to_thumbnails: # new media, make thumbnail
                
                thumb = Thumbnail( m, self )
                self._media_to_thumbnails[ m ] = thumb
                self.scene().addItem( thumb )
                
            
        
    
    def _MediaToUseWhenMovingFocus( self ):
        
        media_to_use = None
        next_best = False
        
        if self._last_hit_media is not None:
            
            media_to_use = self._last_hit_media
            
        elif self._next_best_media_if_focuses_removed is not None:
            
            media_to_use = self._next_best_media_if_focuses_removed
            
            next_best = True
            
        elif len( self._sorted_media ) > 0:
            
            media_to_use = self._sorted_media[ 0 ]
            
        return media_to_use, next_best
        
    
    def _MoveThumbnailFocus( self, new_position, shift ):
            
            if new_position < 0:
                
                new_position = 0
                
            elif new_position > len( self._sorted_media ) - 1:
                
                new_position = len( self._sorted_media ) - 1
                
            new_media = self._sorted_media[ new_position ]
            
            self._HitMedia( new_media, False, shift )
            
            self._ScrollToMedia( new_media )
            
        
    
    def _NotifyThumbnailsHaveMoved( self ):
        
        self._ArrangeThumbnails()
        
    
    def _OnVisibleRectChanged( self, rect: QC.QRectF ) -> None:
        
        # Update the list of possibly visible items
        
        # Leave some additional safety margin for extreme situations like if we decide to paint outside the bounding rect of a thumbnail in its paint function (which kinda works),
        # or some other unforeseen circumstance
        SAFETY_MARGIN_PX = 64 # 512
        
        rect = rect.marginsAdded( QC.QMarginsF( SAFETY_MARGIN_PX, SAFETY_MARGIN_PX, SAFETY_MARGIN_PX, SAFETY_MARGIN_PX ) )
        
        new_possibly_visible_thumbnails = set( self.scene().items( rect, QC.Qt.ItemSelectionMode.IntersectsItemBoundingRect ) )
        
        no_longer_visible_thumbnails = self._possibly_visible_thumbnails.difference( new_possibly_visible_thumbnails )
        
        for thumb in no_longer_visible_thumbnails:
            
            thumb.possibly_visible = False
            
        
        thumbnails_cache = CG.client_controller.thumbnails_cache
        
        thumbnails_cache.CancelWaterfall( self._page_key, [ thumb._media for thumb in no_longer_visible_thumbnails ] )
        
        self._possibly_visible_thumbnails = new_possibly_visible_thumbnails
        
        waterfall_needed = []
        
        for thumb in self._possibly_visible_thumbnails:
            
            thumb.possibly_visible = True
            
            if not thumbnails_cache.HasThumbnailCached( thumb._media, thumb._GetContentSize() ):
                
                waterfall_needed.append( thumb._media )
                
            
        if waterfall_needed:
            
            thumbnails_cache.Waterfall( self._page_key, waterfall_needed )
            
        
    
    def _RedrawMedia( self, media ):
        
        visible_thumbs = []
        
        for m in media:
            
            thumb = self._media_to_thumbnails[ m ]
            
            if thumb.possibly_visible:
                
                visible_thumbs.append( thumb )
                
            else:
                
                thumb.Invalidate() # not currently visible, but when it will become visible we'll want it to be redrawn
                
        
        thumbnails_cache = CG.client_controller.thumbnails_cache
        
        thumbnails_to_render_now = []
        thumbnails_to_render_later = []
        
        for thumb in visible_thumbs:
            
            if thumbnails_cache.HasThumbnailCached( thumb._media, thumb._GetContentSize() ):
                
                thumbnails_to_render_now.append( thumb._media )
                
            else:
                
                thumbnails_to_render_later.append( thumb._media )
                
            
        
        if len( thumbnails_to_render_now ) > 0:
            
            self._FadeThumbnails( thumbnails_to_render_now )
            
        
        if len( thumbnails_to_render_later ) > 0:
            
            thumbnails_cache.Waterfall( self._page_key, thumbnails_to_render_later )
            
        
    
    def _RemoveMediaDirectly( self, singleton_media, collected_media ):
        
        if self._focused_media is not None:
            
            if self._focused_media in singleton_media or self._focused_media in collected_media:
                
                self._SetFocusedMedia( None )
                
            
        
        super()._RemoveMediaDirectly( singleton_media, collected_media )
        
        self._EndShiftSelect()
        
        self._ArrangeThumbnails()
        
        self._PublishSelectionChange()
        
        CG.client_controller.pub( 'refresh_page_name', self._page_key )
        
        CG.client_controller.pub( 'notify_new_pages_count' )
        
    
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
            
        
    
    def _SetMediaSelected( self, media: ClientMedia.Media, selected: bool ) -> None:
        
        thumb = self._media_to_thumbnails.get( media )
        
        if thumb is not None:
            
            thumb.setSelected( selected )
            
        
    
    def _ScrollToMedia( self, media ):
        
        thumb = self._media_to_thumbnails.get( media )
        
        if thumb is None: return
        
        thumb_pos = thumb.scenePos()
        
        percent_visible = CG.client_controller.new_options.GetInteger( 'thumbnail_visibility_scroll_percent' ) / 100
        
        visible_rect = self.mapToScene( self.viewport().rect() ).boundingRect()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_layout.ThumbnailSpanDimensions( thumb )
        
        ensure_x = thumb_pos.x()
        ensure_y = thumb_pos.y()
        
        if thumb_pos.y() < visible_rect.y():
            
            pass
            
        elif thumb_pos.y() > visible_rect.y() + visible_rect.height() - thumbnail_span_height * percent_visible:
            
            ensure_y = thumb_pos.y() + thumbnail_span_height
            
        if thumb_pos.x() < visible_rect.x():
            
            pass
            
        elif thumb_pos.x() > visible_rect.x() + visible_rect.width() - thumbnail_span_width * percent_visible:
            
            ensure_x = thumb_pos.x() + thumbnail_span_width
            
        self.ensureVisible( ensure_x, ensure_y, 0, 0 )
        
    
    def AddMediaResults( self, page_key, media_results ):
        
        if page_key == self._page_key:
            
            thumbnails = super().AddMediaResults( page_key, media_results )
            
            if len( thumbnails ) > 0:
                
                self._ArrangeThumbnails()
                
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
                    
                
            
        
    
    def CleanBeforeDestroy( self ):
        
        CG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
        
        # explicitly clear all references to thumbnail objects just in case, don't want any hanging around
        self._media_to_thumbnails.clear()
        CG.client_controller.thumbnails_cache.CancelWaterfall( self._page_key, [ thumb._media for thumb in self._possibly_visible_thumbnails ] )
        self._possibly_visible_thumbnails.clear()
        self.scene().clear()
        
        super().CleanBeforeDestroy()
        
    
    def ShowMediaFullScreen( self, media ):
        
        if media is not None:
            
            locations_manager = media.GetLocationsManager()
            
            if locations_manager.IsLocal():
                
                self._LaunchMediaViewer( media )
                
            else:
                
                can_download = not locations_manager.GetCurrent().isdisjoint( CG.client_controller.services_manager.GetRemoteFileServiceKeys() )
                
                if can_download:
                    
                    self._DownloadHashes( media.GetHashes() )
                    
                
            
        
    
    def MaintainPageCache( self ):
        
        if not CG.client_controller.gui.IsCurrentPage( self._page_key ):
            
            # TODO
            # I'm really not sure this is a good idea - fiddling with QGraphicsView's internal caching mechanism might hurt more than help...
            # On the other hand, it CAN consume quite a bit of memory, but when exactly to clean caches is probably important for performance.
            # Should decide based on real-world usage experience and a more through reading of the QGraphicsView docs, I leave it commented out for now.
            # There are also some cache-related APIs on QGraphicsView (e.g. setCacheMode) that might be worth taking a look at in the future. 
            # self.resetCachedContent()
            pass
            
        
    
    def mouseMoveEvent( self, event ):
        
        if event.buttons() & QC.Qt.MouseButton.LeftButton:
            
            we_started_dragging_on_this_panel = self._drag_init_coordinates is not None
            
            if we_started_dragging_on_this_panel:
                
                old_drag_pos = self._drag_init_coordinates
                
                global_mouse_pos = ClientGUIFunctions.GetMousePos()
                
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
        
    
    def mousePressEvent( self, event: QG.QMouseEvent ):
        
        # Mouse presses on graphics items will be handled by the items themselves so we are only interested in presses on the empty area here
        if event.button() != QC.Qt.MouseButton.RightButton and self.itemAt( event.pos() ) is None:
            
            self._HitMedia( None, event.modifiers() & QC.Qt.KeyboardModifier.ControlModifier, event.modifiers() & QC.Qt.KeyboardModifier.ShiftModifier )
            
            return
            
        
        QW.QGraphicsView.mousePressEvent( self, event )
        
    
    def MoveMedia( self, medias: list[ ClientMedia.Media ], insertion_index: int ):
        
        if len( medias ) == 0:
            
            return
            
        
        super().MoveMedia( medias, insertion_index )
        
        self._NotifyThumbnailsHaveMoved()
        
        self._ScrollToMedia( medias[0] )
        
    
    def NewThumbnails( self, hashes ):
        
        affected_thumbnails = self._GetMedia( hashes )
        
        if len( affected_thumbnails ) > 0:
            
            self._RedrawMedia( affected_thumbnails )
            
        
    
    def NotifyFilesNeedRedraw( self, hashes ):
        
        affected_media = self._GetMedia( hashes )
        
        for m in affected_media:
            
            self._media_to_thumbnails[ m ].Invalidate()
            
        
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
                        
                    focus_media, _ = self._MediaToUseWhenMovingFocus()
                    
                    if focus_media:
                        
                        scene_rect = self.mapToScene( self.viewport().rect() ).boundingRect()
                        media_index = self._sorted_media.index( focus_media )
                        percent_visible = CG.client_controller.new_options.GetInteger( 'thumbnail_visibility_scroll_percent' ) / 100
                        
                        new_index = self._thumbnail_layout.JumpPage( scene_rect, media_index, direction, percent_visible )
                        
                        self._MoveThumbnailFocus( new_index, shift )
                    
                else:
                    
                    focus_media, is_next_best = self._MediaToUseWhenMovingFocus()
                    
                    if focus_media:
                        
                        # TODO
                        # I expanded this check so rows & columns behave symmetrically (previously there was only an equivalent condition for columns i.e. the MOVE_LEFT case inside _MoveThumbnailFocus).
                        # Symmetric behavior will be important when we have non-uniform grids or grids scrolling horizontally,
                        # but honestly even after playing around with the original implementation, I still don't fully understand what this is supposed to achieve.
                        # If this logic weren't needed we could remove this ugly is_next_best return value when determining the focus media...
                        if is_next_best and ( move_direction == CAC.MOVE_LEFT or move_direction == CAC.MOVE_UP ): # treat it as if the focused area is between this and the next
                            
                            pass
                            
                        else:
                            
                            focus_media_index = self._sorted_media.index( focus_media )
                            
                            self._MoveThumbnailFocus( self._thumbnail_layout.MoveFromIndex( focus_media_index, move_direction ), shift )
                            
                        
                    
                
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
        
        for m in self._collected_media:
            
            m.RecalcInternals()
            
        
        for media in self._sorted_media:
            
            self._media_to_thumbnails[ media ].ClearCachesAndInvalidate()
            
        
        self.scene().update()
        
    
    def contextMenuEvent( self, event ) -> None:
        
        super().contextMenuEvent( event )
        
        # This is not nice and I tried a lot of things here to make both the context menu of the view work, while
        # the Thumbnails still receive & handle mouse events but ultimately only this hack worked out.
        # The problem is something like that the right click event makes the item you are clicking on become the "mouse grabber" item,
        # and somehow exec'ing the menu messes up the event loop or some internal state, so after you close the menu,
        # the item is still the mouse grabber item and the next mouse click (that could be on another item), goes to the mouse grabber item instead,
        # and a further mouse click is required to then select a new item.
        # This expliticly "ungrabs" the mouse, so when the context menu closes there is no mouse grabber, and so any items can receive the next click.
        # One thing I did not try and could be tried is instead of all this, handling the showing of the context menu in the item's context menu handler (that is currently not used).
        if self.scene().mouseGrabberItem():
            
            self.scene().mouseGrabberItem().ungrabMouse()
            
        if event.type() == QC.QEvent.Type.ContextMenu:
            
            self.ShowMenu()
            
        
    
    def resizeEvent( self, event: QG.QResizeEvent ) -> None:
        
        super().resizeEvent( event )
        
        self._ArrangeThumbnails()
        
    
    def SetFocusedMedia( self, media ):
        
        super().SetFocusedMedia( media )
        
        if media is None:
            
            self._SetFocusedMedia( None )
            
        else:
            
            try:
                
                my_media = self._GetMedia( media.GetHashes() )[0]
                
                self._HitMedia( my_media, False, False )
                
                self._ScrollToMedia( self._focused_media )
                
            except Exception as e:
                
                pass
                
            
        
    
    def GetMenu( self ) -> QW.QMenu:
        
        flat_selected_medias = ClientMediaList.FlattenMedia( self._selected_media )
        
        all_locations_managers = [ media.GetLocationsManager() for media in ClientMediaList.FlattenMedia( self._sorted_media ) ]
        selected_locations_managers = [ media.GetLocationsManager() for media in flat_selected_medias ]
        
        selection_has_local_file_domain = True in ( locations_manager.IsLocal() and not locations_manager.IsTrashed() for locations_manager in selected_locations_managers )
        selection_has_trash = True in ( locations_manager.IsTrashed() for locations_manager in selected_locations_managers )
        selection_has_inbox = True in ( media.HasInbox() for media in self._selected_media )
        selection_has_archive = True in ( media.HasArchive() and media.GetLocationsManager().IsLocal() for media in self._selected_media )
        selection_has_deletion_record = True in ( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in locations_manager.GetDeleted() for locations_manager in selected_locations_managers )
        
        all_file_domains = HydrusLists.MassUnion( locations_manager.GetCurrent() for locations_manager in all_locations_managers )
        all_specific_file_domains = all_file_domains.difference( { CC.COMBINED_FILE_SERVICE_KEY, CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY } )
        
        some_downloading = True in ( locations_manager.IsDownloading() for locations_manager in selected_locations_managers )
        
        has_local = True in ( locations_manager.IsLocal() for locations_manager in all_locations_managers )
        has_remote = True in ( locations_manager.IsRemote() for locations_manager in all_locations_managers )
        
        num_files = self.GetNumFiles()
        num_selected = self._GetNumSelected()
        num_inbox = self.GetNumInbox()
        num_archive = self.GetNumArchive()
        
        any_selected = num_selected > 0
        multiple_selected = num_selected > 1
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        # variables
        
        collections_selected = True in ( media.IsCollection() for media in self._selected_media )
        
        services_manager = CG.client_controller.services_manager
        
        services = services_manager.GetServices()
        
        file_repositories: list[ ClientServices.ServiceRepository ] = [ service for service in services if service.GetServiceType() == HC.FILE_REPOSITORY ]
        
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
            
            if len( local_file_service_keys_we_are_in ) == 1:
                
                file_service_key = local_file_service_keys_we_are_in[0]
                
                ClientGUIMenus.AppendMenuItem( menu, 'delete from {}'.format( CG.client_controller.services_manager.GetNameSafe( file_service_key ) ), 'Delete this file.', self._Delete, file_service_key = file_service_key )
                
            else:
                
                delete_menu = ClientGUIMenus.GenerateMenu( menu )
                
                for file_service_key in local_file_service_keys_we_are_in:
                    
                    ClientGUIMenus.AppendMenuItem( delete_menu, 'from {}'.format( CG.client_controller.services_manager.GetNameSafe( file_service_key ) ), 'Delete this file.', self._Delete, file_service_key = file_service_key )
                    
                
                ClientGUIMenus.AppendMenu( menu, delete_menu, local_delete_phrase )
                
            
        
        if selection_has_trash:
            
            if selection_has_local_file_domain:
                
                ClientGUIMenus.AppendMenuItem( menu, 'delete trash physically now', 'Completely delete the selected trashed files, forcing an immediate physical delete from your hard drive.', self._Delete, CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, only_those_in_file_service_key = CC.TRASH_SERVICE_KEY )
                
            
            ClientGUIMenus.AppendMenuItem( menu, delete_physically_phrase, 'Completely delete the selected files, forcing an immediate physical delete from your hard drive.', self._Delete, CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY )
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
            
            local_file_service_keys = ClientMedia.GetLocalFileServiceKeys( flat_selected_medias )
            
            ( local_duplicable_to_file_service_keys, local_moveable_from_and_to_file_service_keys, local_mergable_from_and_to_file_service_keys ) = ClientGUIMediaSimpleActions.GetLocalFileActionServiceKeys( flat_selected_medias )
            
            len_interesting_local_service_keys = 0
            
            len_interesting_local_service_keys += len( local_file_service_keys )
            len_interesting_local_service_keys += len( local_duplicable_to_file_service_keys )
            len_interesting_local_service_keys += len( local_moveable_from_and_to_file_service_keys )
            len_interesting_local_service_keys += len( local_mergable_from_and_to_file_service_keys )
            
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
                    
                    ClientGUIMediaMenus.AddLocalFilesMoveAddToMenu( self, locations_menu, local_file_service_keys, local_duplicable_to_file_service_keys, local_moveable_from_and_to_file_service_keys, local_mergable_from_and_to_file_service_keys, multiple_selected, self.ProcessApplicationCommand )
                    
                
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
            
        
        return menu
        
    
    def GetTotalFileSize( self ):
        
        return sum( ( m.GetSize() for m in self._sorted_media ) )
        
    
    def ShowMenu( self ):
        
        menu = self.GetMenu()
        
        CGC.core().PopupMenu( self, menu )
        
    
    def Sort( self, media_sort = None ):
        
        super().Sort( media_sort )
        
        self._NotifyThumbnailsHaveMoved()
        
    
    def _ResetThumbnailScrollSingleStep( self ):
        
        # No idea what to do if thumbnail height and/or width isn't constant.
        # For now, use the "generic"/"average" thumbnail size for this purpose.
        # This is probably fine...
        ( thumbnail_span_width, thumbnail_span_height ) = self._thumbnail_layout.ThumbnailSpanDimensions( None )
        
        thumbnail_scroll_rate = float( CG.client_controller.new_options.GetString( 'thumbnail_scroll_rate' ) )
        
        self.verticalScrollBar().setSingleStep( int( round( thumbnail_span_height * thumbnail_scroll_rate ) ) )
        
        self.horizontalScrollBar().setSingleStep( int( round( thumbnail_span_width * thumbnail_scroll_rate ) ) )
        
    
    def ThumbnailsReset( self ):
        
        for m in self._collected_media:
            
            m.RecalcInternals()
            
        
        for media in self._sorted_media:
            
            self._media_to_thumbnails[ media ].ClearCachesAndInvalidate()
            
        
        self._ResetThumbnailScrollSingleStep()
        
        self._ArrangeThumbnails()
        
        self.scene().update()
        
    
    def TIMERAnimationUpdate( self ):
        
        if HydrusTime.GetNowPrecise() - self._last_animation_update_time < FRAME_DURATION_60FPS: return
            
        for thumb in self._possibly_visible_thumbnails:
            
            if thumb.is_animating: thumb.AnimationUpdate()
            
        self._last_animation_update_time = HydrusTime.GetNowPrecise()
        
    
    def WaterfallThumbnails( self, page_key, thumbnails ):
        
        if self._page_key == page_key:
            
            self._FadeThumbnails( thumbnails )
            
        
    

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
        
    

# TODO: should be moved to a separate file but leaving this here for the time being to minimize code changes
class Thumbnail( QW.QGraphicsItem ):
    
    FADE_DURATION_S = 0.5
    
    def __init__( self, media: ClientMedia.Media, panel: MediaResultsPanelThumbnails ):
        
        super().__init__()
        
        self._media = media
        
        # These will be accessed by the layouting code
        # I leave them as properties instead of having a GetResolution() method
        # to reduce access overhead (the layouting code is VERY performance-sensitive for more complex layouts if the number of thumbnails is large)
        # TODO: what if the media has no/weird/invalid resolution values? This is not handled currently, as it is not appearent to me
        # what all the possibilites are or if this is even a problem.
        # Probably easy enough to handle by using default thumb size or something here if no proper resolution is available.
        # TODO: what if the media resolution changes? Is that possible? Invalidate() already re-sets this at least but this is untested.
        self.res_x, self.res_y = media.GetResolution()
        
        self._view = panel
        
        self.setAcceptHoverEvents( True )
        
        # right now we do not really utilize the QGraphicsView/Scene functionality related to these flags,
        # and just use the selected state for our own purposes, not the scene/view's own selecting/moving handling
        # but this is ok. these functionalities could get used in the future
        self.setFlag( QW.QGraphicsItem.GraphicsItemFlag.ItemIsMovable )
        self.setFlag( QW.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable )
        
        # # be SUPER careful to keep the thumb width/height as integers (when setting them in the layouting code or elsewhere),
        # otherwise caching etc. will be fucked cause the stored width/height won't be exactly the same as the final thumb pixmap's (integer) width/height
        # if width here somehow becomes 100.325 then everything will seem to work but the QPixmap will have width=100, so width != pixmap.width() and all checks
        # based on this (like in paint()) are fucked
        self.width: int = 0 # these will be set by the layouting code. perf sensitive access!!
        self.height: int = 0
        
        # these are not as perf. sensitive as the res_x,y stuff above simply because there should be less thumbnails updated at a time when these change
        # so some setter/getters COULD be used and be fine, I think
        # But for the time being I think leaving it a simple bool variable is fine too.
        self.possibly_visible = False
        self.is_animating = False
        
        self._is_hovered = False
        self._is_pressed = False
        
        self._last_tags = None
        
        self._last_upper_summary = None
        self._last_lower_summary = None
        
        self._fade_in_started_at = None
        
        # Yes, this is another level of caching but I find it helps with performance, although investigating how big is the performance (vs. memory) hit really would be worth it.
        # In addition to the image in the ThumbnailCache this already has the borders, tags, etc. drawn on it too and also it already in QPixmap format for fast painting!
        # So overall we have the ThumbnailCache + caching the pixmap here + whatever Qt caches in QGraphicsView
        # this is not quite as bad as it sounds, since in the old implementation with the manual "paging", the
        # thumbs were also stored in the ThumbnailCache and also painted onto those "page" bitmaps and this basically replaces that...
        # But if memory usage seems to be higher with the new impl. I would try not using this guy first.
        # I do think that the whole thumbnail caching system should be revised from the ground-up eventually so it is better suited to the QGraphicsView/Scene
        self._cached_pixmap = None
        
        self._cached_old_pixmap_for_fade = None
        
    
    def AnimationUpdate( self ):
        
        if not self.possibly_visible or not self.is_animating:
            
            return
        
        self.update()
        
    
    def boundingRect( self ) -> QC.QRectF:
        
        return QC.QRectF( 0, 0, self.width, self.height )
        
    
    def ClearCachesAndInvalidate( self ):
        
        self._last_tags = None
        
        self._last_upper_summary = None
        self._last_lower_summary = None
        
        self.Invalidate()
        
    
    def hoverEnterEvent( self, event: QW.QGraphicsSceneHoverEvent ) -> None:
        
        self._is_hovered = True
        
        super().hoverEnterEvent( event )
        
    
    def hoverLeaveEvent( self, event: QW.QGraphicsSceneHoverEvent ) -> None:
        
        self._is_hovered = False
        
        super().hoverLeaveEvent( event )
        
    
    def hoverMoveEvent( self, event: QW.QGraphicsSceneHoverEvent ) -> None:
        
        super().hoverMoveEvent( event )
        
    
    def Invalidate( self ) -> None:
        
        self.res_x, self.res_y = self._media.GetResolution() # TODO see the comment on these in __init__
        
        self._cached_pixmap = None
        self._cached_old_pixmap_for_fade = None
        
    
    def mouseDoubleClickEvent( self, event: QW.QGraphicsSceneMouseEvent ) -> None:
        
        self._view.ShowMediaFullScreen( self._media )
        
        super().mouseDoubleClickEvent( event )
        
    
    def mousePressEvent( self, event: QW.QGraphicsSceneMouseEvent ) -> None:
        
        self._is_pressed = True
        
        self._view._drag_init_coordinates = QG.QCursor.pos()
        self._view._drag_click_timestamp_ms = HydrusTime.GetNowMS()
        
        if event.buttons() == QC.Qt.MouseButton.MiddleButton:
            
            self._view.ShowMediaFullScreen( self._media )
            
        else:
            
            # this specifically does not scroll to media, as for clicking (esp. double-clicking attempts), the scroll can be jarring
            self._view._HitMedia( self._media, event.modifiers() & QC.Qt.KeyboardModifier.ControlModifier, event.modifiers() & QC.Qt.KeyboardModifier.ShiftModifier )
            
        
        super().mousePressEvent( event )
        
    
    def mouseReleaseEvent( self, event: QW.QGraphicsSceneMouseEvent ) -> None:
        
        self._is_pressed = False
        
        super().mouseReleaseEvent( event )
        
    
    def paint( self, painter: QG.QPainter, option: QW.QStyleOptionGraphicsItem, widget: QW.QWidget = None ) -> None:
        
        if not self._cached_pixmap or self.width != self._cached_pixmap.width() or self.height != self._cached_pixmap.height():
            
            if not CG.client_controller.thumbnails_cache.HasThumbnailCached( self._media, self._GetContentSize() ):
                
                painter.fillRect( self.boundingRect(), QC.Qt.GlobalColor.transparent )
                
                # TODO is this really OK? I guess this is the way to tell the cache to plz load the thumbnail but without blocking in the paint event
                CG.client_controller.thumbnails_cache.Waterfall( self._view._page_key, ( self._media, ) )
                
                # TODO what if fade is not enabled? I think we don't need to check here for that since then StartFadeIn would never be called and
                #_ cached_old_pixmap_for_fade would be None. Right??
                if self._cached_old_pixmap_for_fade: # fade-in in progress, draw the old image first if available
                    
                    # if the size of the thumb changed in the meantime then probably don't want to draw
                    if self.width == self._cached_old_pixmap_for_fade.width() and self.height == self._cached_old_pixmap_for_fade.height():
                        
                        painter.drawPixmap( 0, 0, self._cached_old_pixmap_for_fade )
                        
                    
                
                return
                
            cached_image = QG.QImage( self.width, self.height, QG.QImage.Format.Format_ARGB32_Premultiplied )
            
            cached_image.setDevicePixelRatio( painter.device().devicePixelRatio() )
            
            cached_image.fill( QC.Qt.GlobalColor.transparent )
            
            image_painter = QG.QPainter( cached_image )
            
            self._PaintThumbnailContent( image_painter, self._media, self._view )
            
            image_painter.end()
            
            self._cached_pixmap = QG.QPixmap.fromImage( cached_image )
            
        
        fade_opacity = self.GetFadeInOpacity()
        
        if fade_opacity < 1.0 and self._cached_old_pixmap_for_fade: # fade-in in progress, draw the old image first if available
            
            # if the size of the thumb changed in the meantime then probably don't want to draw
            if self.width == self._cached_old_pixmap_for_fade.width() and self.height == self._cached_old_pixmap_for_fade.height():
                
                painter.drawPixmap( 0, 0, self._cached_old_pixmap_for_fade )
                
            
        
        painter.setOpacity( fade_opacity )
        
        painter.drawPixmap( 0, 0, self._cached_pixmap )
        
    
    def StartFadeIn( self ):
        
        # Instead of managing the opacity ourselves here and in paint(),
        # we could just use QGraphicsItem::setOpacity and update that value in AnimationUpdate().
        # However, that would cause the opacity value to get stuck when the item leaves the visible area,
        # since we stop calling AnimationUpdate() then.
        # So when it re-enters the visible area, it would still have the previous opacity value
        # until the next AnimationUpdate().
        # Could work around by revising the 'possibly visible' thumbnail tracking logic a bit,
        # but other animations will most likely not have such nice corresponding properties anyway so
        # if we want more animations in the future we won't be able to avoid having to roll our own logic.
        # Nevermind actually I'm not sure about that, the scene/view stuff does have a whole system for animations afterall,
        # so maybe we should take a harder look at that for future animations before rolling our own.
        
        self._fade_in_started_at = HydrusTime.GetNowPrecise()
        
        self._cached_old_pixmap_for_fade = self._cached_pixmap
        self._cached_pixmap = None
        
        self.is_animating = True
        
        self.update()
        
    
    def GetFadeInOpacity( self ) -> float:
        
        if self._fade_in_started_at is None: return 1.0
            
        passed = HydrusTime.GetNowPrecise() - self._fade_in_started_at
        
        if passed >= self.FADE_DURATION_S:
            
            self._fade_in_started_at = None
            
            self._cached_old_pixmap_for_fade = None
            
            self.is_animating = False # now this is great that the only possible animation we have is the fading but if in the future we have multiple types we can't just set it to False here
            
            return 1.0
            
        else:
            
            return passed / self.FADE_DURATION_S # linear transition from 0 to 1 opacity, maybe some other easing curve would look better?
            
        
    def _GetContentSize( self ) -> tuple[int, int]:
        
        thumbnail_border = CG.client_controller.new_options.GetInteger( 'thumbnail_border' )
        
        # now if self.width/height haven't been set (by the layouting code) by this time we will be in for a lot of pain when this returns negative values,
        # but since that happens in the layouting code at the same place where we make this thumb visible,
        # before that the thumb should be hidden so none of the painting-related functions that need this should be called at all
        # maybe return None or something in that case here? at least that would be easier to catch if it somehow happens anyway
        return ( self.width - thumbnail_border * 2, self.height - thumbnail_border * 2 )
        
    
    def _PaintThumbnailContent( self, painter: QG.QPainter, media: ClientMedia.Media, media_panel: ClientGUIMediaResultsPanel.MediaResultsPanel ) -> None:
        
        thumbnail_border = CG.client_controller.new_options.GetInteger( 'thumbnail_border' )
        
        content_size = self._GetContentSize()
        
        if media.GetDisplayMedia() is None:
            
            thumbnail_hydrus_bmp = CG.client_controller.thumbnails_cache.GetHydrusSpecialThumbnail( content_size )
            
        else:
            
            thumbnail_hydrus_bmp = CG.client_controller.thumbnails_cache.GetThumbnail( media.GetDisplayMedia().GetMediaResult(), content_size )
            
        
        ( width, height ) = self.width, self.height
        
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
        
        painter.setRenderHint( QG.QPainter.RenderHint.TextAntialiasing, True ) # is true already in tests, is supposed to be 'the way' to fix the ugly text issue
        painter.setRenderHint( QG.QPainter.RenderHint.Antialiasing, True ) # seems to do nothing, it only affects primitives?
        painter.setRenderHint( QG.QPainter.RenderHint.SmoothPixmapTransform, True ) # makes the thumb QImage scale up and down prettily when we need it, either because it is too small or DPR gubbins
        
        new_options = CG.client_controller.new_options
        
        if not local:
            
            if self.isSelected():
                
                background_colour_type = CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED
                
            else:
                
                background_colour_type = CC.COLOUR_THUMB_BACKGROUND_REMOTE
                
            
        else:
            
            if self.isSelected():
                
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
        
        try:
            
            raw_thumbnail_qt_image = thumbnail_hydrus_bmp.GetQtImage()
            
        except Exception as e:
            
            display_media_result = media.GetDisplayMediaResult()
            
            if display_media_result is None:
                
                hash_hex = 'unknown file--probably an empty list somehow'
                
            else:
                
                hash_hex = display_media_result.GetHash().hex()
                
            
            HydrusData.ShowText( f'Failed to render thumbnail for file {hash_hex}!' )
            HydrusData.ShowException( e, do_wait = False )
            
            thumbnail_hydrus_bmp = CG.client_controller.thumbnails_cache.GetHydrusSpecialThumbnail( content_size )
            
            raw_thumbnail_qt_image = thumbnail_hydrus_bmp.GetQtImage()
            
        
        thumbnail_dpr_percent = new_options.GetInteger( 'thumbnail_dpr_percent' )
        
        if thumbnail_dpr_percent != 100:
            
            thumbnail_dpr = thumbnail_dpr_percent / 100
            
            raw_thumbnail_qt_image.setDevicePixelRatio( thumbnail_dpr )
            
            device_independent_thumb_size = raw_thumbnail_qt_image.deviceIndependentSize()
            
        else:
            
            device_independent_thumb_size = raw_thumbnail_qt_image.size()
            
        
        x_offset = int( ( width - device_independent_thumb_size.width() ) // 2 )
        
        y_offset = int( ( height - device_independent_thumb_size.height() ) // 2 )
        
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
                
                if self.isSelected():
                    
                    border_colour_type = CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED
                    
                else:
                    
                    border_colour_type = CC.COLOUR_THUMB_BORDER_REMOTE
                    
                
            else:
                
                if self.isSelected():
                    
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
        THUMBNAIL_RATING_INCDEC_SET_HEIGHT = round( new_options.GetFloat( 'thumbnail_rating_incdec_height_px' ) )
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
            
            numerical_service = typing.cast( ClientServices.ServiceLocalRatingNumerical, numerical_service )
            
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
            
            ClientGUIRatings.DrawNumerical( painter, numerical_rating_current_x, numerical_rating_current_y, service_key, rating_state, rating, size = QC.QSize( STAR_DX, STAR_DY ), pad_px = custom_pad, draw_collapsed = draw_collapsed_numerical_ratings, text_pen_colour = qss_text_colour )
            
            current_top_right_y += rect_height
            
        
        
        incdec_services = services_manager.GetServices( ( HC.LOCAL_RATING_INCDEC, ) )
        
        incdec_services_to_show = [ incdec_service for incdec_service in incdec_services if ShouldShowRatingInThumbnail( media, incdec_service.GetServiceKey() ) ]
        
        num_to_show = len( incdec_services_to_show )
        
        if num_to_show > 0:
            
            """
            The total rect_width will be added to dynamically, since we want to be able to have dramatically large numbers in some inc/dec services without needing to have unnecessary whitespace in others' boxes
            We need this rect_width for drawing the thumbnail_rating_background only, but it must be pre-calculated for proper painter drawing, so;
            to avoid extra fetches of Service data / Media rating state, we buffer the values used for this pre-calculation for use a moment later in the Draw call.
            """
            
            rect_width = ( ICON_MARGIN * 2 ) + ( ICON_MARGIN * ( num_to_show - 1 ) )
            rect_height = THUMBNAIL_RATING_INCDEC_SET_HEIGHT + ( ICON_MARGIN * 2 )
            
            prefetched_display_values = []
            
            for incdec_service in incdec_services_to_show:
                
                service_key = incdec_service.GetServiceKey()
                
                ( rating_state, rating ) = ClientRatings.GetIncDecStateFromMedia( ( media, ), service_key )
                
                service_size = ClientGUIRatings.GetIncDecSize( THUMBNAIL_RATING_INCDEC_SET_HEIGHT, rating )
                
                rect_width += service_size.width()
                
                prefetched_display_values.append( ( service_key, rating_state, rating, service_size ) )
                
            
            rect_x = width - thumbnail_border - rect_width
            rect_y = current_top_right_y
            
            if draw_thumbnail_rating_background:
                
                painter.fillRect( rect_x, rect_y, rect_width, rect_height, qss_window_colour )
                
            
            incdec_rating_current_x = rect_x + ICON_MARGIN
            incdec_rating_current_y = rect_y + ICON_MARGIN
            
            for incdec_service_details in prefetched_display_values:
                
                ( service_key, rating_state, rating, incdec_size ) = incdec_service_details
                
                ClientGUIRatings.DrawIncDec( painter, incdec_rating_current_x, incdec_rating_current_y, service_key, rating_state, rating, incdec_size, QC.QSize( ICON_PAD, ICON_MARGIN ) )
                
                incdec_rating_current_x += incdec_size.width() + ICON_MARGIN
                
            
            current_top_right_y += rect_height
            
        
        # icons
        
        icons_to_draw = []
        
        if locations_manager.IsDownloading():
            
            icons_to_draw.append( CC.global_pixmaps().downloading )
            
        
        if media.HasNotes():
            
            icons_to_draw.append( CC.global_pixmaps().notes )
            
        
        if locations_manager.IsTrashed() or CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in locations_manager.GetDeleted():
            
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
            
        elif media.HasDuration() or media.HasSimulatedDuration():
            
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
            
        
    
