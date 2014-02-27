import HydrusConstants as HC
import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIDialogsManage
import ClientGUIMixins
import collections
import os
import Queue
import random
import shutil
import subprocess
import threading
import time
import traceback
import urllib
import wx
import wx.media

if HC.PLATFORM_WINDOWS: import wx.lib.flashwin

ID_TIMER_ANIMATED = wx.NewId()
ID_TIMER_ANIMATION_BAR_UPDATE = wx.NewId()
ID_TIMER_SLIDESHOW = wx.NewId()
ID_TIMER_CURSOR_HIDE = wx.NewId()

ANIMATED_SCANBAR_HEIGHT = 20
ANIMATED_SCANBAR_CARET_WIDTH = 10

# Zooms

ZOOMINS = [ 0.01, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0 ]
ZOOMOUTS = [ 20.0, 10.0, 5.0, 3.0, 2.0, 1.5, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.5, 0.3, 0.2, 0.15, 0.1, 0.05, 0.01 ]

NON_ZOOMABLE_MIMES = list( HC.AUDIO) + [ HC.APPLICATION_PDF ]

NON_LARGABLY_ZOOMABLE_MIMES = list( HC.VIDEO ) + [ HC.APPLICATION_FLASH ]

# Sizer Flags

FLAGS_NONE = wx.SizerFlags( 0 )

FLAGS_SMALL_INDENT = wx.SizerFlags( 0 ).Border( wx.ALL, 2 )

FLAGS_EXPAND_PERPENDICULAR = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_BOTH_WAYS = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_DEPTH_ONLY = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_EXPAND_SIZER_PERPENDICULAR = wx.SizerFlags( 0 ).Expand()
FLAGS_EXPAND_SIZER_BOTH_WAYS = wx.SizerFlags( 2 ).Expand()
FLAGS_EXPAND_SIZER_DEPTH_ONLY = wx.SizerFlags( 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_BUTTON_SIZERS = wx.SizerFlags( 0 ).Align( wx.ALIGN_RIGHT )
FLAGS_LONE_BUTTON = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_RIGHT )

FLAGS_MIXED = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

def ShouldHaveAnimationBar( media ):
    
    is_animated_gif = media.GetMime() == HC.IMAGE_GIF and media.HasDuration()
    
    is_animated_flash = media.GetMime() == HC.APPLICATION_FLASH and media.HasDuration()
    
    return is_animated_gif or is_animated_flash
    
def GetExtraDimensions( media ):
    
    extra_width = 0
    extra_height = 0
    
    if ShouldHaveAnimationBar( media ): extra_height += ANIMATED_SCANBAR_HEIGHT
    
    return ( extra_width, extra_height )

class AnimationBar( wx.Window ):
    
    def __init__( self, parent, media, media_window ):
        
        ( parent_width, parent_height ) = parent.GetClientSize()
        
        wx.Window.__init__( self, parent, size = ( parent_width, ANIMATED_SCANBAR_HEIGHT ), pos = ( 0, parent_height - ANIMATED_SCANBAR_HEIGHT ) )
        
        self._canvas_bmp = wx.EmptyBitmap( parent_width, ANIMATED_SCANBAR_HEIGHT, 24 )
        
        self.SetCursor( wx.StockCursor( wx.CURSOR_ARROW ) )
        
        self._media = media
        self._media_window = media_window
        self._num_frames = self._media.GetNumFrames()
        self._num_frames_rendered = 0
        self._current_frame_index = 0
        
        self._currently_in_a_drag = False
        
        self.Bind( wx.EVT_MOUSE_EVENTS, self.EventMouse )
        self.Bind( wx.EVT_TIMER, self.TIMEREventUpdate, id = ID_TIMER_ANIMATION_BAR_UPDATE )
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        
        self._timer_update = wx.Timer( self, id = ID_TIMER_ANIMATION_BAR_UPDATE )
        self._timer_update.Start( 100, wx.TIMER_CONTINUOUS )
        
        self._Draw()
        
    
    def _Draw( self ):
        
        ( my_width, my_height ) = self._canvas_bmp.GetSize()
        
        dc = wx.BufferedDC( wx.ClientDC( self ), self._canvas_bmp )
        
        dc.SetPen( wx.TRANSPARENT_PEN )
        
        if self._media.GetMime() in HC.IMAGES:
            
            image_container = self._media_window.GetImageContainer()
            
            self._num_frames_rendered = image_container.GetNumFramesRendered()
            
            num_frames = image_container.GetNumFrames()
            
            my_rendered_width = int( my_width * ( float( self._num_frames_rendered ) / num_frames ) )
            
            dc.SetBrush( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) ) )
            
            dc.DrawRectangle( 0, 0, my_rendered_width, ANIMATED_SCANBAR_HEIGHT )
            
            dc.SetBrush( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_SCROLLBAR ) ) )
            
            dc.DrawRectangle( my_rendered_width, 0, my_width - my_rendered_width, ANIMATED_SCANBAR_HEIGHT )
            
        else:
            
            dc.SetBrush( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) ) )
            
            dc.DrawRectangle( 0, 0, my_width, ANIMATED_SCANBAR_HEIGHT )
            
        
        dc.SetBrush( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_SCROLLBAR ) ) )
        
        dc.DrawRectangle( int( float( my_width - ANIMATED_SCANBAR_CARET_WIDTH ) * float( self._current_frame_index ) / float( self._num_frames - 1 ) ), 0, ANIMATED_SCANBAR_CARET_WIDTH, ANIMATED_SCANBAR_HEIGHT )
        
    
    def EventMouse( self, event ):
        
        CC.CAN_HIDE_MOUSE = False
        
        ( my_width, my_height ) = self.GetClientSize()
        
        if event.Dragging(): self._currently_in_a_drag = True
        
        if event.ButtonIsDown( wx.MOUSE_BTN_ANY ):
            
            ( x, y ) = event.GetPosition()
            
            compensated_x_position = x - ( ANIMATED_SCANBAR_CARET_WIDTH / 2 )
            
            proportion = float( compensated_x_position ) / float( my_width - ANIMATED_SCANBAR_CARET_WIDTH )
            
            if proportion < 0: proportion = 0
            if proportion > 1: proportion = 1
            
            self._current_frame_index = int( proportion * ( self._num_frames - 1 ) + 0.5 )
            
            self._Draw()
            
            self._media_window.GotoFrame( self._current_frame_index )
            
        elif event.ButtonUp():
            
            if not self._currently_in_a_drag: self._media_window.Play()
            
            self._currently_in_a_drag = False
            
        
    
    def EventPaint( self, event ): wx.BufferedPaintDC( self, self._canvas_bmp )
    
    def EventResize( self, event ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        ( current_bmp_width, current_bmp_height ) = self._canvas_bmp.GetSize()
        
        if my_width != current_bmp_width or my_height != current_bmp_height:
            
            if my_width > 0 and my_height > 0:
                
                wx.CallAfter( self._canvas_bmp.Destroy )
                
                self._canvas_bmp = wx.EmptyBitmap( my_width, my_height, 24 )
                
                self._Draw()
                
            
        
    
    def GotoFrame( self, frame_index ):
        
        self._current_frame_index = frame_index
        
        self._Draw()
        
    
    def TIMEREventUpdate( self, event ):
        
        if self.IsShown():
            
            if self._media.GetMime() in HC.IMAGES:
                
                image_container = self._media_window.GetImageContainer()
                
                if self._num_frames_rendered != image_container.GetNumFramesRendered():
                    
                    self._Draw()
                    
                
            elif self._media.GetMime() == HC.APPLICATION_FLASH:
                
                frame_index = self._media_window.CurrentFrame()
                
                if frame_index != self._current_frame_index:
                    
                    self._current_frame_index = frame_index
                    
                    self._Draw()
                    
                
            
        
    
class Canvas():
    
    def __init__( self, file_service_identifier, image_cache ):
        
        self._file_service_identifier = file_service_identifier
        self._image_cache = image_cache
        
        self._service_identifiers_to_services = {}
        
        self._focus_holder = wx.Window( self )
        self._focus_holder.Hide()
        self._focus_holder.SetEventHandler( self )
        
        self._current_media = None
        self._current_display_media = None
        self._media_container = None
        self._current_zoom = 1.0
        
        self._last_drag_coordinates = None
        self._total_drag_delta = ( 0, 0 )
        
        self.SetBackgroundColour( wx.WHITE )
        
        self._canvas_bmp = wx.EmptyBitmap( 0, 0, 24 )
        
        self.Bind( wx.EVT_SIZE, self.EventResize )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        
    
    def _DrawBackgroundBitmap( self ):
        
        ( client_width, client_height ) = self.GetClientSize()
        
        cdc = wx.ClientDC( self )
        
        dc = wx.BufferedDC( cdc, self._canvas_bmp )
        
        dc.SetBackground( wx.Brush( wx.WHITE ) )
        
        dc.Clear()
        
        if self._current_media is not None:
            
            # tags on the top left
            
            dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
            
            tags_manager = self._current_media.GetDisplayMedia().GetTagsManager()
            
            siblings_manager = HC.app.GetManager( 'tag_siblings' )
            
            current = siblings_manager.CollapseTags( tags_manager.GetCurrent() )
            pending = siblings_manager.CollapseTags( tags_manager.GetPending() )
            
            tags_i_want_to_display = list( current.union( pending ) )
            
            tags_i_want_to_display.sort()
            
            current_y = 3
            
            namespace_colours = HC.options[ 'namespace_colours' ]
            
            for tag in tags_i_want_to_display:
                
                if tag in current: display_string = tag
                elif tag in pending: display_string = '(+) ' + tag
                
                if ':' in tag:
                    
                    ( namespace, sub_tag ) = tag.split( ':', 1 )
                    
                    if namespace in namespace_colours: ( r, g, b ) = namespace_colours[ namespace ]
                    else: ( r, g, b ) = namespace_colours[ None ]
                    
                else: ( r, g, b ) = namespace_colours[ '' ]
                
                dc.SetTextForeground( wx.Colour( r, g, b ) )
                
                ( x, y ) = dc.GetTextExtent( display_string )
                
                dc.DrawText( display_string, 5, current_y )
                
                current_y += y
                
            
            dc.SetTextForeground( wx.BLACK )
            
            # icons
            
            icons_to_show = []
            
            if self._current_media.HasInbox(): icons_to_show.append( CC.GlobalBMPs.inbox_bmp )
            
            file_service_identifiers = self._current_media.GetFileServiceIdentifiersCDPP()
            
            if self._file_service_identifier.GetType() == HC.LOCAL_FILE:
                
                if len( file_service_identifiers.GetPendingRemote() ) > 0: icons_to_show.append( CC.GlobalBMPs.file_repository_pending_bmp )
                elif len( file_service_identifiers.GetCurrentRemote() ) > 0: icons_to_show.append( CC.GlobalBMPs.file_repository_bmp )
                
            elif self._file_service_identifier in file_service_identifiers.GetCurrentRemote():
                
                if self._file_service_identifier in file_service_identifiers.GetPetitionedRemote(): icons_to_show.append( CC.GlobalBMPs.file_repository_petitioned_bmp )
                
            
            current_x = client_width - 18
            
            for icon_bmp in icons_to_show:
                
                dc.DrawBitmap( icon_bmp, current_x, 2 )
                
                current_x -= 20
                
            
            # top right
            
            top_right_strings = []
            
            collections_string = self._GetCollectionsString()
            
            if len( collections_string ) > 0: top_right_strings.append( collections_string )
            
            ( local_ratings, remote_ratings ) = self._current_display_media.GetRatings()
            
            service_identifiers_to_ratings = local_ratings.GetServiceIdentifiersToRatings()
            
            for ( service_identifier, rating ) in service_identifiers_to_ratings.items():
                
                if rating is None: continue
                
                service_type = service_identifier.GetType()
                
                if service_identifier in self._service_identifiers_to_services: service = self._service_identifiers_to_services[ service_identifier ]
                else:
                    
                    service = HC.app.Read( 'service', service_identifier )
                    
                    self._service_identifiers_to_services[ service_identifier ] = service
                    
                
                if service_type == HC.LOCAL_RATING_LIKE:
                    
                    ( like, dislike ) = service.GetLikeDislike()
                    
                    if rating == 1: s = like
                    elif rating == 0: s = dislike
                    
                elif service_type == HC.LOCAL_RATING_NUMERICAL:
                    
                    ( lower, upper ) = service.GetLowerUpper()
                    
                    s = HC.ConvertNumericalRatingToPrettyString( lower, upper, rating )
                    
                
                top_right_strings.append( s )
                
            
            if len( top_right_strings ) > 0:
                
                current_y = 3
                
                if len( icons_to_show ) > 0: current_y += 16
                
                for s in top_right_strings:
                    
                    ( x, y ) = dc.GetTextExtent( s )
                    
                    dc.DrawText( s, client_width - x - 3, current_y )
                    
                    current_y += y
                    
                
            
            info_string = self._GetInfoString()
            
            ( x, y ) = dc.GetTextExtent( info_string )
            
            dc.DrawText( info_string, ( client_width - x ) / 2, client_height - y - 3 )
            
            index_string = self._GetIndexString()
            
            if len( index_string ) > 0:
                
                ( x, y ) = dc.GetTextExtent( index_string )
                
                dc.DrawText( index_string, client_width - x - 3, client_height - y - 3 )
                
            
        
    
    def _DrawCurrentMedia( self ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        if my_width > 0 and my_height > 0:
            
            if self._current_media is not None: self._SizeAndPositionMediaContainer()
            
        
    
    def _GetCollectionsString( self ): return ''
    
    def _GetInfoString( self ):
        
        info_string = self._current_media.GetPrettyInfo() + ' | ' + self._current_media.GetPrettyAge()
        
        return info_string
        
    
    def _GetIndexString( self ): return ''
    
    def _GetMediaContainerSizeAndPosition( self ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        if self._current_display_media.GetMime() == HC.APPLICATION_PDF: ( original_width, original_height ) = ( min( my_width, 200 ), min( my_height, 45 ) )
        elif self._current_display_media.GetMime() in HC.AUDIO: ( original_width, original_height ) = ( min( my_width, 360 ) , min( my_height, 240 ) )
        else: ( original_width, original_height ) = self._current_display_media.GetResolution()
        
        media_width = int( round( original_width * self._current_zoom ) )
        media_height = int( round( original_height * self._current_zoom ) )
        
        ( extra_width, extra_height ) = GetExtraDimensions( self._current_display_media )
        
        media_width += extra_width
        media_height += extra_height
        
        ( drag_x, drag_y ) = self._total_drag_delta
        
        x_offset = ( my_width - media_width ) / 2 + drag_x
        y_offset = ( my_height - media_height ) / 2 + drag_y
        
        new_size = ( media_width, media_height )
        new_position = ( x_offset, y_offset )
        
        return ( new_size, new_position )
        
    
    def _ManageRatings( self ):
        
        if self._current_media is not None:
            
            try:
                with ClientGUIDialogsManage.DialogManageRatings( self, ( self._current_media, ) ) as dlg: dlg.ShowModal()
            except: wx.MessageBox( 'Had a problem displaying the manage ratings dialog from fullscreen.' )
            
        
    
    def _ManageTags( self ):
        
        if self._current_media is not None:
            
            try:
                with ClientGUIDialogsManage.DialogManageTags( self, self._file_service_identifier, ( self._current_media, ) ) as dlg: dlg.ShowModal()
            except: wx.MessageBox( 'Had a problem displaying the manage tags dialog from fullscreen.' )
            
        
    
    def _PrefetchImages( self ): pass
    
    def _RecalcZoom( self ):
        
        if self._current_display_media is None: self._current_zoom = 1.0
        else:
            
            ( my_width, my_height ) = self.GetClientSize()
            
            ( media_width, media_height ) = self._current_display_media.GetResolution()
            
            if ShouldHaveAnimationBar( self._current_display_media ):
                
                media_height += ANIMATED_SCANBAR_HEIGHT
                
            
            if self._current_display_media.GetMime() in NON_LARGABLY_ZOOMABLE_MIMES: my_width -= 1
            
            if media_width > my_width or media_height > my_height:
                
                width_zoom = my_width / float( media_width )
                
                height_zoom = my_height / float( media_height )
                
                self._current_zoom = min( ( width_zoom, height_zoom ) )
                
            else: self._current_zoom = 1.0
            
        
    
    def _ShouldSkipInputDueToFlash( self ):
        
        if self._current_display_media.GetMime() in NON_LARGABLY_ZOOMABLE_MIMES:
            
            ( x, y ) = self._media_container.GetPosition()
            ( width, height ) = self._media_container.GetSize()
            
            ( mouse_x, mouse_y ) = self.ScreenToClient( wx.GetMousePosition() )
            
            if mouse_x > x and mouse_x < x + width and mouse_y > y and mouse_y < y + height: return True
            
        
        return False
        
    
    def _SizeAndPositionMediaContainer( self ):
        
        ( new_size, new_position ) = self._GetMediaContainerSizeAndPosition()
        
        if new_size != self._media_container.GetSize(): self._media_container.SetSize( new_size )
        if new_position != self._media_container.GetPosition(): self._media_container.SetPosition( new_position )
        
    
    def EventPaint( self, event ): wx.BufferedPaintDC( self, self._canvas_bmp, wx.BUFFER_VIRTUAL_AREA )
    
    def EventResize( self, event ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        wx.CallAfter( self._canvas_bmp.Destroy )
        
        self._canvas_bmp = wx.EmptyBitmap( my_width, my_height, 24 )
        
        if self._media_container is not None:
            
            ( media_width, media_height ) = self._media_container.GetClientSize()
            
            if my_width != media_width or my_height != media_height:
                
                with wx.FrozenWindow( self ):
                    
                    self._RecalcZoom()
                    
                    self._DrawBackgroundBitmap()
                    
                    self._DrawCurrentMedia()
                    
                
            
        else: self._DrawBackgroundBitmap()
        
        event.Skip()
        
    
    def KeepCursorAlive( self ): pass
    
    def SetMedia( self, media ):
        
        initial_image = self._current_media == None
        
        if media != self._current_media:
            
            with wx.FrozenWindow( self ):
                
                self._current_media = media
                self._current_display_media = None
                self._total_drag_delta = ( 0, 0 )
                self._last_drag_coordinates = None
                
                if self._media_container is not None:
                    
                    self._media_container.Hide()
                    
                    wx.CallAfter( self._media_container.Destroy )
                    
                    self._media_container = None
                    
                
                if self._current_media is not None:
                    
                    self._current_display_media = self._current_media.GetDisplayMedia()
                    
                    if self._current_display_media.GetFileServiceIdentifiersCDPP().HasLocal():
                        
                        self._RecalcZoom()
                        
                        ( initial_size, initial_position ) = self._GetMediaContainerSizeAndPosition()
                        
                        self._media_container = MediaContainer( self, self._image_cache, self._current_display_media, initial_size, initial_position )
                        
                        if not initial_image: self._PrefetchImages()
                        
                    else: self._current_media = None
                    
                
                self._DrawBackgroundBitmap()
                
                self._DrawCurrentMedia()
                
            
        
class CanvasPanel( Canvas, wx.Window ):
    
    def __init__( self, parent, page_key, file_service_identifier ):
        
        wx.Window.__init__( self, parent, style = wx.SIMPLE_BORDER )
        Canvas.__init__( self, file_service_identifier, HC.app.GetPreviewImageCache() )
        
        self._page_key = page_key
        
        HC.pubsub.sub( self, 'FocusChanged', 'focus_changed' )
        HC.pubsub.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        
        wx.CallAfter( self.Refresh )
        
    
    def FocusChanged( self, page_key, media ):
        
        if page_key == self._page_key: self.SetMedia( media )
        
    
    def ProcessContentUpdates( self, service_identifiers_to_content_updates ):
        
        if self._current_display_media is not None:
            
            my_hash = self._current_display_media.GetHash()
            
            do_redraw = False
            
            for ( service_identifier, content_updates ) in service_identifiers_to_content_updates.items():
                
                if True in ( my_hash in content_update.GetHashes() for content_update in content_updates ):
                    
                    do_redraw = True
                    
                    break
                    
                
            
            if do_redraw:
                
                self._DrawBackgroundBitmap()
                
                self._DrawCurrentMedia()
                
            
        
    
class CanvasFullscreenMediaList( ClientGUIMixins.ListeningMediaList, Canvas, ClientGUICommon.FrameThatResizes ):
    
    def __init__( self, my_parent, page_key, file_service_identifier, media_results ):
        
        ClientGUICommon.FrameThatResizes.__init__( self, my_parent, resize_option_prefix = 'fs_', title = 'hydrus client fullscreen media viewer' )
        Canvas.__init__( self, file_service_identifier, HC.app.GetFullscreenImageCache() )
        ClientGUIMixins.ListeningMediaList.__init__( self, file_service_identifier, media_results )
        
        self._page_key = page_key
        
        self._menu_open = False
        
        self._just_started = True
        
        self.Show( True )
        
        if self.IsMaximized() and HC.options[ 'fullscreen_borderless' ]:
            
            self.ShowFullScreen( True, wx.FULLSCREEN_ALL )
            
        
        HC.app.SetTopWindow( self )
        
        self._timer_cursor_hide = wx.Timer( self, id = ID_TIMER_CURSOR_HIDE )
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventCursorHide, id = ID_TIMER_CURSOR_HIDE )
        
        self.Bind( wx.EVT_CLOSE, self.EventClose )
        
        self.Bind( wx.EVT_MOTION, self.EventDrag )
        self.Bind( wx.EVT_LEFT_DOWN, self.EventDragBegin )
        self.Bind( wx.EVT_LEFT_UP, self.EventDragEnd )
        
        HC.pubsub.pub( 'set_focus', self._page_key, None )
        
    
    def _DoManualPan( self, delta_x, delta_y ):
        
        ( old_delta_x, old_delta_y ) = self._total_drag_delta
        
        self._total_drag_delta = ( old_delta_x + delta_x, old_delta_y + delta_y )
        
        self._DrawCurrentMedia()
        
    
    def _FullscreenSwitch( self ):
        
        if self.IsFullScreen(): self.ShowFullScreen( False )
        else: self.ShowFullScreen( True, wx.FULLSCREEN_ALL )
        
    
    def _GetCollectionsString( self ):
        
        collections_string = ''
        
        siblings_manager = HC.app.GetManager( 'tag_siblings' )
        
        namespaces = self._current_media.GetDisplayMedia().GetTagsManager().GetCombinedNamespaces( ( 'creator', 'series', 'title', 'volume', 'chapter', 'page' ) )
        
        creators = namespaces[ 'creator' ]
        series = namespaces[ 'series' ]
        titles = namespaces[ 'title' ]
        volumes = namespaces[ 'volume' ]
        chapters = namespaces[ 'chapter' ]
        pages = namespaces[ 'page' ]
        
        if len( creators ) > 0:
            
            creators = siblings_manager.CollapseNamespacedTags( 'creator', creators )
            
            collections_string_append = ', '.join( creators )
            
            if len( collections_string ) > 0: collections_string += ' - ' + collections_string_append
            else: collections_string = collections_string_append
            
        
        if len( series ) > 0:
            
            series = siblings_manager.CollapseNamespacedTags( 'series', series )
            
            collections_string_append = ', '.join( series )
            
            if len( collections_string ) > 0: collections_string += ' - ' + collections_string_append
            else: collections_string = collections_string_append
            
        
        if len( titles ) > 0:
            
            titles = siblings_manager.CollapseNamespacedTags( 'title', titles )
            
            collections_string_append = ', '.join( titles )
            
            if len( collections_string ) > 0: collections_string += ' - ' + collections_string_append
            else: collections_string = collections_string_append
            
        
        if len( volumes ) > 0:
            
            if len( volumes ) == 1:
                
                ( volume, ) = volumes
                
                collections_string_append = 'volume ' + HC.u( volume )
                
            else: collections_string_append = 'volumes ' + HC.u( min( volumes ) ) + '-' + HC.u( max( volumes ) )
            
            if len( collections_string ) > 0: collections_string += ' - ' + collections_string_append
            else: collections_string = collections_string_append
            
        
        if len( chapters ) > 0:
            
            if len( chapters ) == 1:
                
                ( chapter, ) = chapters
                
                collections_string_append = 'chapter ' + HC.u( chapter )
                
            else: collections_string_append = 'chapters ' + HC.u( min( chapters ) ) + '-' + HC.u( max( chapters ) )
            
            if len( collections_string ) > 0: collections_string += ' - ' + collections_string_append
            else: collections_string = collections_string_append
            
        
        if len( pages ) > 0:
            
            if len( pages ) == 1:
                
                ( page, ) = pages
                
                collections_string_append = 'page ' + HC.u( page )
                
            else: collections_string_append = 'pages ' + HC.u( min( pages ) ) + '-' + HC.u( max( pages ) )
            
            if len( collections_string ) > 0: collections_string += ' - ' + collections_string_append
            else: collections_string = collections_string_append
            
        
        return collections_string
        
    
    def _GetInfoString( self ):
        
        info_string = self._current_media.GetPrettyInfo() + ' | ' + HC.ConvertZoomToPercentage( self._current_zoom ) + ' | ' + self._current_media.GetPrettyAge()
        
        return info_string
        
    
    def _GetIndexString( self ):
        
        index_string = HC.ConvertIntToPrettyString( self._sorted_media.index( self._current_media ) + 1 ) + os.path.sep + HC.ConvertIntToPrettyString( len( self._sorted_media ) )
        
        return index_string
        
    
    def _PrefetchImages( self ):
        
        to_render = []
        
        previous = self._current_media
        next = self._current_media
        
        if self._just_started:
            
            extra_delay_base = 800
            
            self._just_started = False
            
        else: extra_delay_base = 200
        
        for i in range( 10 ):
            
            previous = self._GetPrevious( previous )
            next = self._GetNext( next )
            
            to_render.append( ( previous, 100 + ( extra_delay_base * 2 * i * i ) ) )
            to_render.append( ( next, 100 + ( extra_delay_base * i * i ) ) )
            
        
        ( my_width, my_height ) = self.GetClientSize()
        
        for ( media, delay ) in to_render:
            
            hash = media.GetHash()
            
            mime = media.GetMime()
            
            if media.GetMime() in ( HC.IMAGE_JPEG, HC.IMAGE_PNG ):
                
                ( media_width, media_height ) = media.GetResolution()
                
                if media_width > my_width or media_height > my_height:
                    
                    width_zoom = my_width / float( media_width )
                    
                    height_zoom = my_height / float( media_height )
                    
                    zoom = min( ( width_zoom, height_zoom ) )
                    
                else: zoom = 1.0
                
                resolution_to_request = ( int( round( zoom * media_width ) ), int( round( zoom * media_height ) ) )
                
                if not self._image_cache.HasImage( hash, resolution_to_request ): wx.CallLater( delay, self._image_cache.GetImage, hash, mime, resolution_to_request )
                
            
        
    
    def _ShowFirst( self ): self.SetMedia( self._GetFirst() )
    
    def _ShowLast( self ): self.SetMedia( self._GetLast() )
    
    def _ShowNext( self ): self.SetMedia( self._GetNext( self._current_media ) )
    
    def _ShowPrevious( self ): self.SetMedia( self._GetPrevious( self._current_media ) )
    
    def _StartSlideshow( self, interval ): pass
    
    def _ZoomIn( self ):
        
        if self._current_media is not None:
            
            if self._current_media.GetMime() in NON_ZOOMABLE_MIMES: return
            
            for zoom in ZOOMINS:
                
                if self._current_zoom < zoom:
                    
                    if self._current_media.GetMime() in NON_LARGABLY_ZOOMABLE_MIMES:
                        
                        # because of the event passing under mouse, we want to preserve whitespace around flash
                        
                        ( original_width, original_height ) = self._current_display_media.GetResolution()
                        
                        ( my_width, my_height ) = self.GetClientSize()
                        
                        new_media_width = int( round( original_width * zoom ) )
                        new_media_height = int( round( original_height * zoom ) )
                        
                        ( extra_width, extra_height ) = GetExtraDimensions( self._current_display_media )
                        
                        new_media_width += extra_width
                        new_media_height += extra_height
                        
                        if new_media_width >= my_width or new_media_height >= my_height: return
                        
                    
                    with wx.FrozenWindow( self ):
                        
                        ( drag_x, drag_y ) = self._total_drag_delta
                        
                        zoom_ratio = zoom / self._current_zoom
                        
                        self._total_drag_delta = ( int( drag_x * zoom_ratio ), int( drag_y * zoom_ratio ) )
                        
                        self._current_zoom = zoom
                        
                        self._DrawBackgroundBitmap()
                        
                        self._DrawCurrentMedia()
                        
                    
                    break
                    
                
            
        
    
    def _ZoomOut( self ):
        
        if self._current_media is not None:
            
            if self._current_media.GetMime() in NON_ZOOMABLE_MIMES: return
            
            for zoom in ZOOMOUTS:
                
                if self._current_zoom > zoom:
                    
                    with wx.FrozenWindow( self ):
                        
                        ( drag_x, drag_y ) = self._total_drag_delta
                        
                        zoom_ratio = zoom / self._current_zoom
                        
                        self._total_drag_delta = ( int( drag_x * zoom_ratio ), int( drag_y * zoom_ratio ) )
                        
                        self._current_zoom = zoom
                        
                        self._DrawBackgroundBitmap()
                        
                        self._DrawCurrentMedia()
                        
                    
                    break
                    
                
            
        
    
    def _ZoomSwitch( self ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        ( media_width, media_height ) = self._current_display_media.GetResolution()
        
        if self._current_media.GetMime() in NON_ZOOMABLE_MIMES: return
        
        if self._current_media.GetMime() not in NON_LARGABLY_ZOOMABLE_MIMES or self._current_zoom > 1.0 or ( media_width < my_width and media_height < my_height ):
            
            new_zoom = self._current_zoom
            
            if self._current_zoom == 1.0:
                
                if media_width > my_width or media_height > my_height:
                    
                    width_zoom = my_width / float( media_width )
                    
                    height_zoom = my_height / float( media_height )
                    
                    new_zoom = min( ( width_zoom, height_zoom ) )
                    
                
            else: new_zoom = 1.0
            
            if new_zoom != self._current_zoom:
                
                ( drag_x, drag_y ) = self._total_drag_delta
                
                zoom_ratio = new_zoom / self._current_zoom
                
                self._total_drag_delta = ( int( drag_x * zoom_ratio ), int( drag_y * zoom_ratio ) )
                
                self._current_zoom = new_zoom
                
                self._DrawBackgroundBitmap()
                
                self._DrawCurrentMedia()
                
            
        
    
    def AddMediaResults( self, page_key, media_results ):
        
        if page_key == self._page_key:
            
            ClientGUIMixins.ListeningMediaList.AddMediaResults( self, media_results )
            
            self._DrawBackgroundBitmap()
            
            self._DrawCurrentMedia()
            
        
    
    def Archive( self, hashes ):
        
        next_media = self._GetNext( self._current_media )
        
        if next_media == self._current_media: next_media = None
        
        ClientGUIMixins.ListeningMediaList.Archive( self, hashes )
        
        if self.HasNoMedia(): self.EventClose( None )
        elif self.HasMedia( self._current_media ): self._DrawCurrentMedia()
        else: self.SetMedia( next_media )
        
    
    def EventClose( self, event ):
        
        HC.pubsub.pub( 'set_focus', self._page_key, self._current_media )
        
        if HC.PLATFORM_OSX and self.IsFullScreen(): self.ShowFullScreen( False )
        
        wx.CallAfter( self.Destroy )
        
    
    def EventDrag( self, event ):
        
        CC.CAN_HIDE_MOUSE = True
        
        self._focus_holder.SetFocus()
        
        if event.Dragging() and self._last_drag_coordinates is not None:
            
            ( old_x, old_y ) = self._last_drag_coordinates
            
            ( x, y ) = event.GetPosition()
            
            ( delta_x, delta_y ) = ( x - old_x, y - old_y )
            
            try:
                
                if HC.PLATFORM_OSX: raise Exception() # can't warppointer in os x
                
                self.WarpPointer( old_x, old_y )
                
            except: self._last_drag_coordinates = ( x, y )
            
            ( old_delta_x, old_delta_y ) = self._total_drag_delta
            
            self._total_drag_delta = ( old_delta_x + delta_x, old_delta_y + delta_y )
            
            self._DrawCurrentMedia()
            
        
        self.SetCursor( wx.StockCursor( wx.CURSOR_ARROW ) )
        
        self._timer_cursor_hide.Start( 800, wx.TIMER_ONE_SHOT )
        
    
    def EventDragBegin( self, event ):
        
        ( x, y ) = event.GetPosition()
        
        ( client_x, client_y ) = self.GetClientSize()
        
        if x < 20 or x > client_x - 20 or y < 20 or y > client_y -20:
            
            try:
                
                better_x = x
                better_y = y
                
                if x < 20: better_x = 20
                if y < 20: better_y = 20
                
                if x > client_x - 20: better_x = client_x - 20
                if y > client_y - 20: better_y = client_y - 20
                
                if HC.PLATFORM_OSX: raise Exception() # can't warppointer in os x
                
                self.WarpPointer( better_x, better_y )
                
                x = better_x
                y = better_y
                
            except: pass
            
        
        self._last_drag_coordinates = ( x, y )
        
        event.Skip()
        
    
    def EventDragEnd( self, event ):
        
        self._last_drag_coordinates = None
        
        event.Skip()
        
    
    def EventFullscreenSwitch( self, event ): self._FullscreenSwitch()
    
    def KeepCursorAlive( self ): self._timer_cursor_hide.Start( 800, wx.TIMER_ONE_SHOT )
    
    def ProcessContentUpdates( self, service_identifiers_to_content_updates ):
        
        next_media = self._GetNext( self._current_media )
        
        if next_media == self._current_media: next_media = None
        
        ClientGUIMixins.ListeningMediaList.ProcessContentUpdates( self, service_identifiers_to_content_updates )
        
        if self.HasNoMedia(): self.EventClose( None )
        elif self.HasMedia( self._current_media ):
            
            self._DrawBackgroundBitmap()
            
            self._DrawCurrentMedia()
            
        else: self.SetMedia( next_media )
        
    
    def TIMEREventCursorHide( self, event ):
        
        if not CC.CAN_HIDE_MOUSE: return
        
        if self._menu_open: self._timer_cursor_hide.Start( 800, wx.TIMER_ONE_SHOT )
        else: self.SetCursor( wx.StockCursor( wx.CURSOR_BLANK ) )
        
    
class CanvasFullscreenMediaListBrowser( CanvasFullscreenMediaList ):
    
    def __init__( self, my_parent, page_key, file_service_identifier, media_results, first_hash ):
        
        CanvasFullscreenMediaList.__init__( self, my_parent, page_key, file_service_identifier, media_results )
        
        self._timer_slideshow = wx.Timer( self, id = ID_TIMER_SLIDESHOW )
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventSlideshow, id = ID_TIMER_SLIDESHOW )
        
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventClose )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventClose )
        self.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
        if first_hash is None: self.SetMedia( self._GetFirst() )
        else: self.SetMedia( self._GetMedia( { first_hash } )[0] )
        
        HC.pubsub.sub( self, 'AddMediaResults', 'add_media_results' )
        
    
    def _Archive( self ): HC.app.Write( 'content_updates', { HC.LOCAL_FILE_SERVICE_IDENTIFIER : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, ( self._current_media.GetHash(), ) ) ] } )
    
    def _CopyLocalUrlToClipboard( self ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject( 'http://127.0.0.1:' + str( HC.options[ 'local_port' ] ) + '/file?hash=' + self._current_media.GetHash().encode( 'hex' ) )
            
            wx.TheClipboard.SetData( data )
            
            wx.TheClipboard.Close()
            
        else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
        
    
    def _CopyPathToClipboard( self ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject( CC.GetFilePath( self._current_media.GetHash(), self._current_media.GetMime() ) )
            
            wx.TheClipboard.SetData( data )
            
            wx.TheClipboard.Close()
            
        else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
        
    
    def _Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Delete this file from the database?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES: HC.app.Write( 'content_updates', { HC.LOCAL_FILE_SERVICE_IDENTIFIER : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( self._current_media.GetHash(), ) ) ] } )
            
        
        self.SetFocus() # annoying bug because of the modal dialog
        
    
    def _Inbox( self ): HC.app.Write( 'content_updates', { HC.LOCAL_FILE_SERVICE_IDENTIFIER : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, ( self._current_media.GetHash(), ) ) ] } )
    
    def _PausePlaySlideshow( self ):
        
        if self._timer_slideshow.IsRunning(): self._timer_slideshow.Stop()
        elif self._timer_slideshow.GetInterval() > 0: self._timer_slideshow.Start()
        
    
    def _StartSlideshow( self, interval = None ):
        
        self._timer_slideshow.Stop()
        
        if interval is None:
            
            with wx.TextEntryDialog( self, 'Enter the interval, in seconds', defaultValue='15' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    try: interval = int( float( dlg.GetValue() ) * 1000 )
                    except: return
                    
                
            
        
        if interval > 0: self._timer_slideshow.Start( interval, wx.TIMER_CONTINUOUS )
        
    
    def EventCharHook( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            ( modifier, key ) = HC.GetShortcutFromEvent( event )
            
            if modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE ): self._Delete()
            elif modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_SPACE, wx.WXK_NUMPAD_SPACE ): self._PausePlaySlideshow()
            elif modifier == wx.ACCEL_NORMAL and key in ( ord( '+' ), wx.WXK_ADD, wx.WXK_NUMPAD_ADD ): self._ZoomIn()
            elif modifier == wx.ACCEL_NORMAL and key in ( ord( '-' ), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT ): self._ZoomOut()
            elif modifier == wx.ACCEL_NORMAL and key == ord( 'Z' ): self._ZoomSwitch()
            elif modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ): self.EventClose( event )
            elif modifier == wx.ACCEL_CTRL and key == ord( 'C' ):
                with wx.BusyCursor(): HC.app.Write( 'copy_files', ( self._current_media.GetHash(), ) )
            else:
                
                key_dict = HC.options[ 'shortcuts' ][ modifier ]
                
                if key in key_dict:
                    
                    action = key_dict[ key ]
                    
                    self.ProcessEvent( wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) )
                    
                else: event.Skip()
                
            
        
    
    def EventMenu( self, event ):
        
        # is None bit means this is prob from a keydown->menu event
        if event.GetEventObject() is None and self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
            
            if action is not None:
                
                ( command, data ) = action
                
                if command == 'archive': self._Archive()
                elif command == 'copy_files':
                    with wx.BusyCursor(): HC.app.Write( 'copy_files', ( self._current_media.GetHash(), ) )
                elif command == 'copy_local_url': self._CopyLocalUrlToClipboard()
                elif command == 'copy_path': self._CopyPathToClipboard()
                elif command == 'delete': self._Delete()
                elif command == 'fullscreen_switch': self._FullscreenSwitch()
                elif command == 'first': self._ShowFirst()
                elif command == 'last': self._ShowLast()
                elif command == 'previous': self._ShowPrevious()
                elif command == 'next': self._ShowNext()
                elif command == 'frame_back': self._media_container.GotoPreviousOrNextFrame( -1 )
                elif command == 'frame_next': self._media_container.GotoPreviousOrNextFrame( 1 )
                elif command == 'inbox': self._Inbox()
                elif command == 'manage_ratings': self._ManageRatings()
                elif command == 'manage_tags': self._ManageTags()
                elif command in ( 'pan_up', 'pan_down', 'pan_left', 'pan_right' ):
                    
                    distance = 20
                    
                    if command == 'pan_up': self._DoManualPan( 0, -distance )
                    elif command == 'pan_down': self._DoManualPan( 0, distance )
                    elif command == 'pan_left': self._DoManualPan( -distance, 0 )
                    elif command == 'pan_right': self._DoManualPan( distance, 0 )
                    
                elif command == 'slideshow': self._StartSlideshow( data )
                elif command == 'slideshow_pause_play': self._PausePlaySlideshow()
                elif command == 'zoom_in': self._ZoomIn()
                elif command == 'zoom_out': self._ZoomOut()
                elif command == 'zoom_switch': self._ZoomSwitch()
                else: event.Skip()
                
            
        
    
    def EventMouseWheel( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            if event.CmdDown():
                
                if event.GetWheelRotation() > 0: self._ZoomIn()
                else: self._ZoomOut()
                
            else:
                
                if event.GetWheelRotation() > 0: self._ShowPrevious()
                else: self._ShowNext()
                
            
        
    
    def EventShowMenu( self, event ):
        
        services = HC.app.Read( 'services' )
        
        local_ratings_services = [ service for service in services if service.GetServiceIdentifier().GetType() in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
        
        i_can_post_ratings = len( local_ratings_services ) > 0
        
        self._last_drag_coordinates = None # to stop successive right-click drag warp bug
        
        menu = wx.Menu()
        
        menu.Append( CC.ID_NULL, self._current_media.GetPrettyInfo() )
        menu.Append( CC.ID_NULL, self._current_media.GetPrettyAge() )
        
        menu.AppendSeparator()
        
        menu.Append( CC.ID_NULL, 'current zoom: ' + HC.ConvertZoomToPercentage( self._current_zoom ) )
        
        menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'zoom_in' ), 'zoom in' )
        menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'zoom_out' ), 'zoom out' )
        
        #
        
        if self._current_media.GetMime() not in NON_LARGABLY_ZOOMABLE_MIMES + NON_ZOOMABLE_MIMES:
            
            ( my_width, my_height ) = self.GetClientSize()
            
            ( media_width, media_height ) = self._current_display_media.GetResolution()
            
            if self._current_zoom == 1.0:
                
                if media_width > my_width or media_height > my_height: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'zoom_switch' ), 'zoom fit' )
                
            else: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'zoom_switch' ), 'zoom full' )
            
        
        #
        
        menu.AppendSeparator()
        
        menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_tags' ), 'manage tags' )
        
        if i_can_post_ratings: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_ratings' ), 'manage ratings' )
        
        menu.AppendSeparator()
        
        if self._current_media.HasInbox(): menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'archive' ), '&archive' )
        if self._current_media.HasArchive(): menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'inbox' ), 'return to &inbox' )
        menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'delete', HC.LOCAL_FILE_SERVICE_IDENTIFIER ), '&delete' )
        
        menu.AppendSeparator()
        
        copy_menu = wx.Menu()
        
        copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_files' ) , 'file' )
        copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_path' ) , 'path' )
        copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_local_url' ) , 'local url' )
        
        menu.AppendMenu( CC.ID_NULL, 'copy', copy_menu )
        
        menu.AppendSeparator()
        
        slideshow = wx.Menu()
        
        slideshow.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'slideshow', 1000 ), '1 second' )
        slideshow.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'slideshow', 5000 ), '5 seconds' )
        slideshow.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'slideshow', 10000 ), '10 seconds' )
        slideshow.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'slideshow', 30000 ), '30 seconds' )
        slideshow.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'slideshow', 60000 ), '60 seconds' )
        slideshow.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'slideshow', 80 ), 'william gibson' )
        slideshow.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'slideshow' ), 'custom interval' )
        
        menu.AppendMenu( CC.ID_NULL, 'Start Slideshow', slideshow )
        if self._timer_slideshow.IsRunning(): menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'slideshow_pause_play' ), 'stop slideshow' )
        
        self._menu_open = True
        
        self.PopupMenu( menu )
        
        self._menu_open = False
        
        wx.CallAfter( menu.Destroy )
        
        event.Skip()
        
    
    def TIMEREventSlideshow( self, event ): self._ShowNext()
    
class CanvasFullscreenMediaListCustomFilter( CanvasFullscreenMediaList ):
    
    def __init__( self, my_parent, page_key, file_service_identifier, media_results, actions ):
        
        CanvasFullscreenMediaList.__init__( self, my_parent, page_key, file_service_identifier, media_results )
        
        self._actions = actions
        
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventClose )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventClose )
        self.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
        self.SetMedia( self._GetFirst() )
        
        FullscreenPopoutFilterCustom( self )
        
        HC.pubsub.sub( self, 'AddMediaResults', 'add_media_results' )
        
    
    def _Archive( self ): HC.app.Write( 'content_updates', { HC.LOCAL_FILE_SERVICE_IDENTIFIER : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, ( self._current_media.GetHash(), ) ) ] } )
    
    def _CopyLocalUrlToClipboard( self ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject( 'http://127.0.0.1:' + str( HC.options[ 'local_port' ] ) + '/file?hash=' + self._current_media.GetHash().encode( 'hex' ) )
            
            wx.TheClipboard.SetData( data )
            
            wx.TheClipboard.Close()
            
        else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
        
    
    def _CopyPathToClipboard( self ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject( CC.GetFilePath( self._current_media.GetHash(), self._current_media.GetMime() ) )
            
            wx.TheClipboard.SetData( data )
            
            wx.TheClipboard.Close()
            
        else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
        
    
    def _Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Delete this file from the database?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES: HC.app.Write( 'content_updates', { HC.LOCAL_FILE_SERVICE_IDENTIFIER : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( self._current_media.GetHash(), ) ) ] } )
            
        
        self.SetFocus() # annoying bug because of the modal dialog
        
    
    def _Inbox( self ): HC.app.Write( 'content_updates', { HC.LOCAL_FILE_SERVICE_IDENTIFIER : [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, ( self._current_media.GetHash(), ) ) ] } )
    
    def EventActions( self, event ):
        
        with ClientGUIDialogs.DialogSetupCustomFilterActions( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK: self._actions = dlg.GetActions()
            
        
    
    def EventCharHook( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            ( modifier, key ) = HC.GetShortcutFromEvent( event )
            
            key_dict = self._actions[ modifier ]
            
            hashes = set( ( self._current_media.GetHash(), ) )
            
            if key in key_dict:
                
                ( service_identifier, action ) = key_dict[ key ]
                
                if service_identifier is None:
                    
                    if action == 'archive': self._Archive()
                    elif action == 'delete': self._Delete()
                    elif action == 'frame_back': self._media_container.GotoPreviousOrNextFrame( -1 )
                    elif action == 'frame_next': self._media_container.GotoPreviousOrNextFrame( 1 )
                    elif action == 'inbox': self._Inbox()
                    elif action == 'manage_ratings': self._ManageRatings()
                    elif action == 'manage_tags': self._ManageTags()
                    elif action in ( 'pan_up', 'pan_down', 'pan_left', 'pan_right' ):
                        
                        distance = 20
                        
                        if action == 'pan_up': self._DoManualPan( 0, -distance )
                        elif action == 'pan_down': self._DoManualPan( 0, distance )
                        elif action == 'pan_left': self._DoManualPan( -distance, 0 )
                        elif action == 'pan_right': self._DoManualPan( distance, 0 )
                        
                    elif action == 'first': self._ShowFirst()
                    elif action == 'last': self._ShowLast()
                    elif action == 'previous': self._ShowPrevious()
                    elif action == 'next': self._ShowNext()
                    
                else:
                    
                    service_type = service_identifier.GetType()
                    
                    if service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ):
                        
                        tag = action
                        
                        tags_manager = self._current_media.GetDisplayMedia().GetTagsManager()
                        
                        current = tags_manager.GetCurrent()
                        pending = tags_manager.GetPending()
                        petitioned = tags_manager.GetPetitioned()
                        
                        if service_type == HC.LOCAL_TAG:
                            
                            tags = [ tag ]
                            
                            if tag in current: content_update_action = HC.CONTENT_UPDATE_DELETE
                            else:
                                
                                content_update_action = HC.CONTENT_UPDATE_ADD
                                
                                tag_parents_manager = HC.app.GetManager( 'tag_parents' )
                                
                                parents = tag_parents_manager.GetParents( service_identifier, tag )
                                
                                tags.extend( parents )
                                
                            
                            rows = [ ( tag, hashes ) for tag in tags ]
                            
                        else:
                            
                            if tag in current:
                                
                                if tag in petitioned: edit_log = [ ( HC.CONTENT_UPDATE_RESCIND_PETITION, tag ) ]
                                else:
                                    
                                    message = 'Enter a reason for this tag to be removed. A janitor will review your petition.'
                                    
                                    with wx.TextEntryDialog( self, message ) as dlg:
                                        
                                        if dlg.ShowModal() == wx.ID_OK:
                                            
                                            content_update_action = HC.CONTENT_UPDATE_PETITION
                                            
                                            rows = [ ( dlg.GetValue(), tag, hashes ) ]
                                            
                                        else: return
                                        
                                    
                                
                            else:
                                
                                tags = [ tag ]
                                
                                if tag in pending: content_update_action = HC.CONTENT_UPDATE_RESCIND_PENDING
                                else:
                                    
                                    content_update_action = HC.CONTENT_UPDATE_PENDING
                                    
                                    tag_parents_manager = HC.app.GetManager( 'tag_parents' )
                                    
                                    parents = tag_parents_manager.GetParents( service_identifier, tag )
                                    
                                    tags.extend( parents )
                                    
                                
                                rows = [ ( tag, hashes ) for tag in tags ]
                                
                            
                        
                        content_updates = [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, content_update_action, row ) for row in rows ]
                        
                    elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                        
                        # maybe this needs to be more complicated, if action is, say, remove the rating?
                        # ratings needs a good look at anyway
                        
                        rating = action
                        
                        row = ( rating, hashes )
                        
                        content_updates = [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, row ) ]
                        
                    
                    HC.app.Write( 'content_updates', { service_identifier : content_updates } )
                    
                
            else:
                
                if modifier == wx.ACCEL_NORMAL and key in ( ord( '+' ), wx.WXK_ADD, wx.WXK_NUMPAD_ADD ): self._ZoomIn()
                elif modifier == wx.ACCEL_NORMAL and key in ( ord( '-' ), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT ): self._ZoomOut()
                elif modifier == wx.ACCEL_NORMAL and key == ord( 'Z' ): self._ZoomSwitch()
                elif modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ): self.EventClose( event )
                elif modifier == wx.ACCEL_CTRL and key == ord( 'C' ):
                    with wx.BusyCursor(): HC.app.Write( 'copy_files', ( self._current_media.GetHash(), ) )
                else:
                    
                    key_dict = HC.options[ 'shortcuts' ][ modifier ]
                    
                    if key in key_dict:
                        
                        action = key_dict[ key ]
                        
                        self.ProcessEvent( wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) )
                        
                    else: event.Skip()
                    
                
            
        
    
    def EventMenu( self, event ):
        
        # is None bit means this is prob from a keydown->menu event
        if event.GetEventObject() is None and self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
            
            if action is not None:
                
                ( command, data ) = action
                
                if command == 'archive': self._Archive()
                elif command == 'copy_files':
                    with wx.BusyCursor(): HC.app.Write( 'copy_files', ( self._current_media.GetHash(), ) )
                elif command == 'copy_local_url': self._CopyLocalUrlToClipboard()
                elif command == 'copy_path': self._CopyPathToClipboard()
                elif command == 'delete': self._Delete()
                elif command == 'fullscreen_switch': self._FullscreenSwitch()
                elif command == 'first': self._ShowFirst()
                elif command == 'last': self._ShowLast()
                elif command == 'previous': self._ShowPrevious()
                elif command == 'next': self._ShowNext()
                elif command == 'frame_back': self._media_container.GotoPreviousOrNextFrame( -1 )
                elif command == 'frame_next': self._media_container.GotoPreviousOrNextFrame( 1 )
                elif command == 'inbox': self._Inbox()
                elif command == 'manage_ratings': self._ManageRatings()
                elif command == 'manage_tags': self._ManageTags()
                elif command == 'slideshow': self._StartSlideshow( data )
                elif command == 'slideshow_pause_play': self._PausePlaySlideshow()
                elif command == 'zoom_in': self._ZoomIn()
                elif command == 'zoom_out': self._ZoomOut()
                elif command == 'zoom_switch': self._ZoomSwitch()
                else: event.Skip()
                
            
        
    
    def EventMouseWheel( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            if event.CmdDown():
                
                if event.GetWheelRotation() > 0: self._ZoomIn()
                else: self._ZoomOut()
                
            else:
                
                if event.GetWheelRotation() > 0: self._ShowPrevious()
                else: self._ShowNext()
                
            
        
    
    def EventShowMenu( self, event ):
        
        self._last_drag_coordinates = None # to stop successive right-click drag warp bug
        
        menu = wx.Menu()
        
        menu.Append( CC.ID_NULL, self._current_media.GetPrettyInfo() )
        menu.Append( CC.ID_NULL, self._current_media.GetPrettyAge() )
        
        menu.AppendSeparator()
        
        menu.Append( CC.ID_NULL, 'current zoom: ' + HC.ConvertZoomToPercentage( self._current_zoom ) )
        
        menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'zoom_in' ), 'zoom in' )
        menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'zoom_out' ), 'zoom out' )
        
        #
        
        if self._current_media.GetMime() not in NON_LARGABLY_ZOOMABLE_MIMES + NON_ZOOMABLE_MIMES:
            
            ( my_width, my_height ) = self.GetClientSize()
            
            ( media_width, media_height ) = self._current_display_media.GetResolution()
            
            if self._current_zoom == 1.0:
                
                if media_width > my_width or media_height > my_height: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'zoom_switch' ), 'zoom fit' )
                
            else: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'zoom_switch' ), 'zoom full' )
            
        
        #
        
        menu.AppendSeparator()
        
        if self._current_media.HasInbox(): menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'archive' ), '&archive' )
        if self._current_media.HasArchive(): menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'inbox' ), 'return to &inbox' )
        menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'delete', HC.LOCAL_FILE_SERVICE_IDENTIFIER ), '&delete' )
        
        menu.AppendSeparator()
        
        copy_menu = wx.Menu()
        
        copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_files' ) , 'file' )
        copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_path' ) , 'path' )
        copy_menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_local_url' ) , 'local url' )
        
        menu.AppendMenu( CC.ID_NULL, 'copy', copy_menu )
        
        menu.AppendSeparator()
        
        self._menu_open = True
        
        self.PopupMenu( menu )
        
        self._menu_open = False
        
        wx.CallAfter( menu.Destroy )
        
        event.Skip()
        
    
class CanvasFullscreenMediaListFilter( CanvasFullscreenMediaList ):
    
    def __init__( self, my_parent, page_key, file_service_identifier, media_results ):
        
        CanvasFullscreenMediaList.__init__( self, my_parent, page_key, file_service_identifier, media_results )
        
        self._kept = set()
        self._deleted = set()
        
        self.Bind( wx.EVT_LEFT_DOWN, self.EventMouseKeep )
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventMouseKeep )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventBack )
        self.Bind( wx.EVT_MIDDLE_DCLICK, self.EventBack )
        self.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventDelete )
        self.Bind( wx.EVT_RIGHT_DCLICK, self.EventDelete )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
        self.SetMedia( self._GetFirst() )
        
    
    def _Delete( self ):
        
        self._deleted.add( self._current_media )
        
        if self._current_media == self._GetLast(): self.EventClose( None )
        else: self._ShowNext()
        
    
    def _Keep( self ):
        
        self._kept.add( self._current_media )
        
        if self._current_media == self._GetLast(): self.EventClose( None )
        else: self._ShowNext()
        
    
    def EventBack( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            if self._current_media == self._GetFirst(): return
            else:
                
                self._ShowPrevious()
                
                self._kept.discard( self._current_media )
                self._deleted.discard( self._current_media )
                
            
        
    
    def EventButtonBack( self, event ): self.EventBack( event )
    def EventButtonDelete( self, event ): self._Delete()
    def EventButtonDone( self, event ): self.EventClose( event )
    def EventButtonKeep( self, event ): self._Keep()
    def EventButtonSkip( self, event ):
        
        if self._current_media == self._GetLast(): self.EventClose( event )
        else: self._ShowNext()
        
    
    def EventClose( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            if len( self._kept ) > 0 or len( self._deleted ) > 0:
                
                with ClientGUIDialogs.DialogFinishFiltering( self, len( self._kept ), len( self._deleted ) ) as dlg:
                    
                    modal = dlg.ShowModal()
                    
                    if modal == wx.ID_CANCEL:
                        
                        if self._current_media in self._kept: self._kept.remove( self._current_media )
                        if self._current_media in self._deleted: self._deleted.remove( self._current_media )
                        
                    else:
                        
                        if modal == wx.ID_YES:
                            
                            self._deleted_hashes = [ media.GetHash() for media in self._deleted ]
                            self._kept_hashes = [ media.GetHash() for media in self._kept ]
                            
                            content_updates = []
                            
                            content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, self._deleted_hashes ) )
                            content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, self._kept_hashes ) )
                            
                            HC.app.Write( 'content_updates', { HC.LOCAL_FILE_SERVICE_IDENTIFIER : content_updates } )
                            
                            self._kept = set()
                            self._deleted = set()
                            
                            self._current_media = self._GetFirst() # so the pubsub on close is better
                            
                        
                        CanvasFullscreenMediaList.EventClose( self, event )
                        
                    
                
            else: CanvasFullscreenMediaList.EventClose( self, event )
            
        
    
    def EventCharHook( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
        
            ( modifier, key ) = HC.GetShortcutFromEvent( event )
            
            if modifier == wx.ACCEL_NORMAL and key == wx.WXK_SPACE: self._Keep()
            elif modifier == wx.ACCEL_NORMAL and key in ( ord( '+' ), wx.WXK_ADD, wx.WXK_NUMPAD_ADD ): self._ZoomIn()
            elif modifier == wx.ACCEL_NORMAL and key in ( ord( '-' ), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT ): self._ZoomOut()
            elif modifier == wx.ACCEL_NORMAL and key == ord( 'Z' ): self._ZoomSwitch()
            elif modifier == wx.ACCEL_NORMAL and key == wx.WXK_BACK: self.EventBack( event )
            elif modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ): self.EventClose( event )
            elif modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE ): self.EventDelete( event )
            elif modifier == wx.ACCEL_CTRL and key == ord( 'C' ):
                with wx.BusyCursor(): HC.app.Write( 'copy_files', ( self._current_media.GetHash(), ) )
            elif not event.ShiftDown() and key in ( wx.WXK_UP, wx.WXK_NUMPAD_UP ): self.EventSkip( event )
            else:
                
                key_dict = HC.options[ 'shortcuts' ][ modifier ]
                
                if key in key_dict:
                    
                    action = key_dict[ key ]
                    
                    self.ProcessEvent( wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) )
                    
                else: event.Skip()
                
            
        
    
    def EventDelete( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else: self._Delete()
        
    
    def EventMouseKeep( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            if event.ShiftDown(): self.EventDragBegin( event )
            else: self._Keep()
            
        
    
    def EventMenu( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
            
            if action is not None:
                
                ( command, data ) = action
                
                if command == 'archive': self._Keep()
                elif command == 'back': self.EventBack( event )
                elif command == 'close': self.EventClose( event )
                elif command == 'delete': self.EventDelete( event )
                elif command == 'fullscreen_switch': self._FullscreenSwitch()
                elif command == 'filter': self.EventClose( event )
                elif command == 'frame_back': self._media_container.GotoPreviousOrNextFrame( -1 )
                elif command == 'frame_next': self._media_container.GotoPreviousOrNextFrame( 1 )
                elif command == 'manage_ratings': self._ManageRatings()
                elif command == 'manage_tags': self._ManageTags()
                elif command in ( 'pan_up', 'pan_down', 'pan_left', 'pan_right' ):
                    
                    distance = 20
                    
                    if command == 'pan_up': self._DoManualPan( 0, -distance )
                    elif command == 'pan_down': self._DoManualPan( 0, distance )
                    elif command == 'pan_left': self._DoManualPan( -distance, 0 )
                    elif command == 'pan_right': self._DoManualPan( distance, 0 )
                    
                elif command == 'zoom_in': self._ZoomIn()
                elif command == 'zoom_out': self._ZoomOut()
                else: event.Skip()
                
            
        
    
    def EventMouseWheel( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            if event.CmdDown():
                
                if event.GetWheelRotation() > 0: self._ZoomIn()
                else: self._ZoomOut()
                
            
        
    
    def EventSkip( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            if self._current_media == self._GetLast(): self.EventClose( event )
            else: self._ShowNext()
            
        
    
class CanvasFullscreenMediaListFilterInbox( CanvasFullscreenMediaListFilter ):
    
    def __init__( self, my_parent, page_key, file_service_identifier, media_results ):
        
        CanvasFullscreenMediaListFilter.__init__( self, my_parent, page_key, file_service_identifier, media_results )
        
        FullscreenPopoutFilterInbox( self )
        
    
class FullscreenPopout( wx.Frame ):
    
    def __init__( self, parent ):
        
        wx.Frame.__init__( self, parent, style = wx.FRAME_TOOL_WINDOW | wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT | wx.BORDER_SIMPLE )
        
        self._last_drag_coordinates = None
        self._total_drag_delta = ( 0, 0 )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
        
        self.SetCursor( wx.StockCursor( wx.CURSOR_ARROW ) )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        self._popout_window = self._InitialisePopoutWindow( hbox )
        
        self._popout_window.Hide()
        
        self._button_window = self._InitialiseButtonWindow( hbox )
        
        hbox.AddF( self._popout_window, FLAGS_EXPAND_PERPENDICULAR )
        hbox.AddF( self._button_window, FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( hbox )
        
        self._SizeAndPosition()
        
        tlp = self.GetParent().GetTopLevelParent()
        
        tlp.Bind( wx.EVT_SIZE, self.EventResize )
        tlp.Bind( wx.EVT_MOVE, self.EventMove )
        
        self.Show()
        
    
    def _InitialiseButtonWindow( self, sizer ):
        
        button_window = wx.Window( self )
        
        self._move_button = wx.Button( button_window, label = u'\u2022', size = ( 20, 20 ) )
        self._move_button.SetCursor( wx.StockCursor( wx.CURSOR_SIZING ) )
        self._move_button.Bind( wx.EVT_MOTION, self.EventDrag )
        self._move_button.Bind( wx.EVT_LEFT_DOWN, self.EventDragBegin )
        self._move_button.Bind( wx.EVT_LEFT_UP, self.EventDragEnd )
        
        self._arrow_button = wx.Button( button_window, label = '>', size = ( 20, 80 ) )
        self._arrow_button.Bind( wx.EVT_BUTTON, self.EventArrowClicked )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._move_button, FLAGS_MIXED )
        vbox.AddF( self._arrow_button, FLAGS_EXPAND_BOTH_WAYS )
        
        button_window.SetSizer( vbox )
        
        return button_window
        
    
    def _SizeAndPosition( self ):
        
        self.Fit()
        
        parent = self.GetParent()
        
        ( parent_width, parent_height ) = parent.GetClientSize()
        
        ( my_width, my_height ) = self.GetClientSize()
        
        my_y = ( parent_height - my_height ) / 2
        
        ( offset_x, offset_y ) = self._total_drag_delta
        
        self.SetPosition( parent.ClientToScreenXY( 0 + offset_x, my_y + offset_y ) )
        
    
    def EventArrowClicked( self, event ):
        
        if self._popout_window.IsShown():
            
            self._popout_window.Hide()
            self._arrow_button.SetLabel( '>' )
            
        else:
            
            self._popout_window.Show()
            self._arrow_button.SetLabel( '<' )
            
        
        self._SizeAndPosition()
        
        self.Layout()
        
    
    def EventMove( self, event ):
        
        self._SizeAndPosition()
        
        event.Skip()
        
    
    def EventDrag( self, event ):
        
        CC.CAN_HIDE_MOUSE = True
        
        if event.Dragging() and self._last_drag_coordinates is not None:
            
            ( old_x, old_y ) = self._last_drag_coordinates
            
            ( x, y ) = event.GetPosition()
            
            ( delta_x, delta_y ) = ( x - old_x, y - old_y )
            
            ( old_delta_x, old_delta_y ) = self._total_drag_delta
            
            self._total_drag_delta = ( old_delta_x + delta_x, old_delta_y + delta_y )
            
            self._SizeAndPosition()
            
        
    
    def EventDragBegin( self, event ):
        
        self._last_drag_coordinates = event.GetPosition()
        
        event.Skip()
        
    
    def EventDragEnd( self, event ):
        
        self._last_drag_coordinates = None
        
        event.Skip()
        
    
    def EventResize( self, event ):
        
        self._SizeAndPosition()
        
        event.Skip()
        
    
class FullscreenPopoutFilterCustom( FullscreenPopout ):
    
    def _InitialisePopoutWindow( self, sizer ):
        
        window = wx.Window( self )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        parent = self.GetParent()
        
        actions = wx.Button( window, label = 'actions' )
        actions.Bind( wx.EVT_BUTTON, parent.EventActions )
        
        fullscreen_switch = wx.Button( window, label = 'switch fullscreen' )
        fullscreen_switch.Bind( wx.EVT_BUTTON, parent.EventFullscreenSwitch )
        
        done = wx.Button( window, label = 'done' )
        done.Bind( wx.EVT_BUTTON, parent.EventClose )
        
        vbox.AddF( actions, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( fullscreen_switch, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( done, FLAGS_EXPAND_PERPENDICULAR )
        
        window.SetSizer( vbox )
        
        return window
        
    
class FullscreenPopoutFilterInbox( FullscreenPopout ):
    
    def _InitialisePopoutWindow( self, sizer ):
        
        window = wx.Window( self )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        parent = self.GetParent()
        
        keep = wx.Button( window, label = 'archive' )
        keep.Bind( wx.EVT_BUTTON, parent.EventButtonKeep )
        
        delete = wx.Button( window, label = 'delete' )
        delete.Bind( wx.EVT_BUTTON, parent.EventButtonDelete )
        
        skip = wx.Button( window, label = 'skip' )
        skip.Bind( wx.EVT_BUTTON, parent.EventButtonSkip )
        
        back = wx.Button( window, label = 'back' )
        back.Bind( wx.EVT_BUTTON, parent.EventButtonBack )
        
        fullscreen_switch = wx.Button( window, label = 'switch fullscreen' )
        fullscreen_switch.Bind( wx.EVT_BUTTON, parent.EventFullscreenSwitch )
        
        done = wx.Button( window, label = 'done' )
        done.Bind( wx.EVT_BUTTON, parent.EventButtonDone )
        
        vbox.AddF( keep, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( delete, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( skip, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( back, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( fullscreen_switch, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( done, FLAGS_EXPAND_PERPENDICULAR )
        
        window.SetSizer( vbox )
        
        return window
        
    
class FullscreenPopoutFilterLike( FullscreenPopout ):
    
    def _InitialisePopoutWindow( self, sizer ):
        
        window = wx.Window( self )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        parent = self.GetParent()
        
        like = wx.Button( window, label = 'like' )
        like.Bind( wx.EVT_BUTTON, parent.EventButtonKeep )
        
        dislike = wx.Button( window, label = 'dislike' )
        dislike.Bind( wx.EVT_BUTTON, parent.EventButtonDelete )
        
        skip = wx.Button( window, label = 'skip' )
        skip.Bind( wx.EVT_BUTTON, parent.EventButtonSkip )
        
        back = wx.Button( window, label = 'back' )
        back.Bind( wx.EVT_BUTTON, parent.EventButtonBack )
        
        fullscreen_switch = wx.Button( window, label = 'switch fullscreen' )
        fullscreen_switch.Bind( wx.EVT_BUTTON, parent.EventFullscreenSwitch )
        
        done = wx.Button( window, label = 'done' )
        done.Bind( wx.EVT_BUTTON, parent.EventButtonDone )
        
        vbox.AddF( like, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( dislike, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( skip, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( back, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( fullscreen_switch, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( done, FLAGS_EXPAND_PERPENDICULAR )
        
        window.SetSizer( vbox )
        
        return window
        
    
class FullscreenPopoutFilterNumerical( FullscreenPopout ):
    
    def __init__( self, parent, callable_parent ):
        
        self._callable_parent = callable_parent
        
        FullscreenPopout.__init__( self, parent )
        
    
    def _InitialisePopoutWindow( self, sizer ):
        
        window = wx.Window( self )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        parent = self.GetParent()
        
        #
        
        accuracy_slider_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        if 'ratings_filter_accuracy' not in HC.options:
            
            HC.options[ 'ratings_filter_accuracy' ] = 1
            
            HC.app.Write( 'save_options' )
            
        
        value = HC.options[ 'ratings_filter_accuracy' ]
        
        self._accuracy_slider = wx.Slider( window, size = ( 50, -1 ), value = value, minValue = 0, maxValue = 4 )
        self._accuracy_slider.Bind( wx.EVT_SLIDER, self.EventAccuracySlider )
        
        accuracy_slider_hbox.AddF( wx.StaticText( window, label = 'quick' ), FLAGS_MIXED )
        accuracy_slider_hbox.AddF( self._accuracy_slider, FLAGS_EXPAND_BOTH_WAYS )
        accuracy_slider_hbox.AddF( wx.StaticText( window, label = 'accurate' ), FLAGS_MIXED )
        
        self.EventAccuracySlider( None )
        
        #
        
        if 'ratings_filter_compare_same' not in HC.options:
            
            HC.options[ 'ratings_filter_compare_same' ] = False
            
            HC.app.Write( 'save_options' )
            
        
        compare_same = HC.options[ 'ratings_filter_compare_same' ]
        
        self._compare_same = wx.CheckBox( window, label = 'compare same image until rating is done' )
        self._compare_same.SetValue( compare_same )
        self._compare_same.Bind( wx.EVT_CHECKBOX, self.EventCompareSame )
        
        self.EventCompareSame( None )
        
        #
        
        self._left_right_slider_sizer = wx.BoxSizer( wx.HORIZONTAL )
        
        if 'ratings_filter_left_right' not in HC.options:
            
            HC.options[ 'ratings_filter_left_right' ] = 'left'
            
            HC.app.Write( 'save_options' )
            
        
        left_right = HC.options[ 'ratings_filter_left_right' ]
        
        if left_right == 'left': left_right_value = 0
        elif left_right == 'random': left_right_value = 1
        else: left_right_value = 2
        
        self._left_right_slider = wx.Slider( window, size = ( 30, -1 ), value = left_right_value, minValue = 0, maxValue = 2 )
        self._left_right_slider.Bind( wx.EVT_SLIDER, self.EventLeftRight )
        
        self._left_right_slider_sizer.AddF( wx.StaticText( window, label = 'left' ), FLAGS_MIXED )
        self._left_right_slider_sizer.AddF( self._left_right_slider, FLAGS_EXPAND_BOTH_WAYS )
        self._left_right_slider_sizer.AddF( wx.StaticText( window, label = 'right' ), FLAGS_MIXED )
        
        self.EventLeftRight( None )
        
        #
        
        left = wx.Button( window, label = 'left is better' )
        left.Bind( wx.EVT_BUTTON, self._callable_parent.EventButtonLeft )
        
        right = wx.Button( window, label = 'right is better' )
        right.Bind( wx.EVT_BUTTON, self._callable_parent.EventButtonRight )
        
        equal = wx.Button( window, label = 'they are about the same' )
        equal.Bind( wx.EVT_BUTTON, self._callable_parent.EventButtonEqual )
        
        skip = wx.Button( window, label = 'skip' )
        skip.Bind( wx.EVT_BUTTON, self._callable_parent.EventButtonSkip )
        
        back = wx.Button( window, label = 'back' )
        back.Bind( wx.EVT_BUTTON, self._callable_parent.EventButtonBack )
        
        dont_filter = wx.Button( window, label = 'don\'t filter this file' )
        dont_filter.Bind( wx.EVT_BUTTON, self._callable_parent.EventButtonDontFilter )
        
        fullscreen_switch = wx.Button( window, label = 'switch fullscreen' )
        fullscreen_switch.Bind( wx.EVT_BUTTON, self._callable_parent.EventFullscreenSwitch )
        
        done = wx.Button( window, label = 'done' )
        done.Bind( wx.EVT_BUTTON, self._callable_parent.EventButtonDone )
        
        vbox.AddF( accuracy_slider_hbox, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._compare_same, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._left_right_slider_sizer, FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.AddF( wx.StaticLine( window, style = wx.LI_HORIZONTAL ), FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.AddF( left, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( right, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( equal, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( skip, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( back, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( dont_filter, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( fullscreen_switch, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( done, FLAGS_EXPAND_PERPENDICULAR )
        
        window.SetSizer( vbox )
        
        return window
        
    
    def EventAccuracySlider( self, event ):
        
        value = self._accuracy_slider.GetValue()
        
        self._callable_parent.SetAccuracy( value )
        
    
    def EventCompareSame( self, event ):
        
        compare_same = self._compare_same.GetValue()
        
        self._callable_parent.SetCompareSame( compare_same )
        
    
    def EventLeftRight( self, event ):
        
        value = self._left_right_slider.GetValue()
        
        if value == 0: left_right = 'left'
        elif value == 1: left_right = 'random'
        else: left_right = 'right'
        
        self._callable_parent.SetLeftRight( left_right )
        
    
class RatingsFilterFrameLike( CanvasFullscreenMediaListFilter ):
    
    def __init__( self, my_parent, page_key, service_identifier, media_results ):
        
        CanvasFullscreenMediaListFilter.__init__( self, my_parent, page_key, HC.LOCAL_FILE_SERVICE_IDENTIFIER, [], media_results )
        
        self._rating_service_identifier = service_identifier
        self._service = HC.app.Read( 'service', service_identifier )
        
        FullscreenPopoutFilterLike( self )
        
    
    def EventClose( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            if len( self._kept ) > 0 or len( self._deleted ) > 0:
                
                ( like, dislike ) = self._service.GetLikeDislike()
                
                with ClientGUIDialogs.DialogFinishFiltering( self, len( self._kept ), len( self._deleted ), keep = like, delete = dislike ) as dlg:
                    
                    modal = dlg.ShowModal()
                    
                    if modal == wx.ID_CANCEL:
                        
                        if self._current_media in self._kept: self._kept.remove( self._current_media )
                        if self._current_media in self._deleted: self._deleted.remove( self._current_media )
                        
                    else:
                        
                        if modal == wx.ID_YES:
                            
                            self._deleted_hashes = [ media.GetHash() for media in self._deleted ]
                            self._kept_hashes = [ media.GetHash() for media in self._kept ]
                            
                            content_updates = []
                            
                            content_updates.extend( [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0.0, set( ( hash, ) ) ) ) for hash in self._deleted_hashes ] )
                            content_updates.extend( [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 1.0, set( ( hash, ) ) ) ) for hash in self._kept_hashes ] )
                            
                            HC.app.Write( 'content_updates', { self._rating_service_identifier : content_updates } )
                            
                            self._kept = set()
                            self._deleted = set()
                            
                        
                        CanvasFullscreenMediaList.EventClose( self, event )
                        
                    
                
            else: CanvasFullscreenMediaList.EventClose( self, event )
            
        
    
class RatingsFilterFrameNumerical( ClientGUICommon.FrameThatResizes ):
    
    RATINGS_FILTER_INEQUALITY_FULL = 0
    RATINGS_FILTER_INEQUALITY_HALF = 1
    RATINGS_FILTER_INEQUALITY_QUARTER = 2
    
    RATINGS_FILTER_EQUALITY_FULL = 0
    RATINGS_FILTER_EQUALITY_HALF = 1
    RATINGS_FILTER_EQUALITY_QUARTER = 2
    
    def __init__( self, parent, page_key, service_identifier, media_results ):
        
        ClientGUICommon.FrameThatResizes.__init__( self, parent, resize_option_prefix = 'fs_', title = 'hydrus client ratings frame' )
        
        self._page_key = page_key
        self._service_identifier = service_identifier
        self._media_still_to_rate = { ClientGUIMixins.MediaSingleton( media_result ) for media_result in media_results }
        self._current_media_to_rate = None
        
        self._file_query_result = CC.FileQueryResult( media_results )
        
        if service_identifier.GetType() == HC.LOCAL_RATING_LIKE: self._score_gap = 1.0
        else:
            
            self._service = HC.app.Read( 'service', service_identifier )
            
            ( self._lower, self._upper ) = self._service.GetLowerUpper()
            
            self._score_gap = 1.0 / ( self._upper - self._lower )
            
        
        hashes_to_min_max = HC.app.Read( 'ratings_filter', service_identifier, [ media_result.GetHash() for media_result in media_results ] )
        
        self._media_to_initial_scores_dict = { media : hashes_to_min_max[ media.GetHash() ] for media in self._media_still_to_rate }
        
        self._decision_log = []
        
        self._ReinitialiseCurrentScores()
        
        self._inequal_accuracy = self.RATINGS_FILTER_INEQUALITY_FULL
        self._equal_accuracy = self.RATINGS_FILTER_EQUALITY_FULL
        
        self._statusbar = self.CreateStatusBar()
        self._statusbar.SetFieldsCount( 3 )
        self._statusbar.SetStatusWidths( [ -1, 500, -1 ] )
        
        self._splitter = wx.SplitterWindow( self )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._splitter, FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self._splitter.SetMinimumPaneSize( 120 )
        self._splitter.SetSashGravity( 0.5 ) # stay in the middle
        
        self.Show( True )
        
        if self.IsMaximized() and HC.options[ 'fullscreen_borderless' ]:
            
            self.ShowFullScreen( True, wx.FULLSCREEN_ALL )
            
        
        HC.app.SetTopWindow( self )
        
        self._left_window = self._Panel( self._splitter )
        FullscreenPopoutFilterNumerical( self._left_window, self )
        
        self._right_window = self._Panel( self._splitter )
        
        ( my_width, my_height ) = self.GetClientSize()
        
        self._splitter.SplitVertically( self._left_window, self._right_window, my_width / 2 )
        
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        self.Bind( wx.EVT_LEFT_DOWN, self.EventMouseDown )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventMouseDown )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.Bind( wx.EVT_CLOSE, self.EventClose )
        
        self._ShowNewMedia()
        
        HC.pubsub.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HC.pubsub.sub( self, 'ProcessServiceUpdates', 'service_updates_gui' )
        
        HC.pubsub.pub( 'set_focus', self._page_key, None )
        
    
    def _FullscreenSwitch( self ):
        
        if self.IsFullScreen(): self.ShowFullScreen( False )
        else: self.ShowFullScreen( True, wx.FULLSCREEN_ALL )
        
    
    def _GoBack( self ):
        
        if len( self._decision_log ) > 0:
            
            ( action, entry ) = self._decision_log[-1]
            
            if action == 'external': ( min, max, self._current_media_to_rate, self._current_media_to_rate_against, self._unrated_is_on_the_left ) = entry
            elif action == 'internal': ( min, max, self._current_media_to_rate, other_min, other_max, self._current_media_to_rate_against, self._unrated_is_on_the_left ) = entry
            
            if self._unrated_is_on_the_left:
                
                self._left_window.SetMedia( self._current_media_to_rate )
                self._right_window.SetMedia( self._current_media_to_rate_against )
                
            else:
                
                self._left_window.SetMedia( self._current_media_to_rate_against )
                self._right_window.SetMedia( self._current_media_to_rate )
                
            
            self._decision_log = self._decision_log[:-1]
            
            self._ReinitialiseCurrentScores()
            
        
        self._RefreshStatusBar()
        
    
    def _RefreshStatusBar( self ):
        
        certain_ratings = [ ( media, ( min, max ) ) for ( media, ( min, max ) ) in self._media_to_current_scores_dict.items() if max - min < self._score_gap ]
        uncertain_ratings = [ ( media, ( min, max ) ) for ( media, ( min, max ) ) in self._media_to_current_scores_dict.items() if max - min >= self._score_gap and self._media_to_current_scores_dict[ media ] != self._media_to_initial_scores_dict[ media ] ]
        
        service_type = self._service_identifier.GetType()
        
        if service_type == HC.LOCAL_RATING_LIKE:
            
            current_string = 'uncertain'
            
            if self._current_media_to_rate_against in self._media_still_to_rate: against_string = 'uncertain'
            else:
                
                against_string = 'already rated'
                
                if self._current_media_to_rate_against in self._media_to_current_scores_dict:
                    
                    ( other_min, other_max ) = self._media_to_current_scores_dict[ self._current_media_to_rate_against ]
                    
                    rating = other_min
                    
                else:
                    
                    ( local_ratings, remote_ratings ) = self._current_media_to_rate_against.GetRatings()
                    
                    rating = local_ratings.GetRating( self._service_identifier )
                    
                
                if rating == 0.0: against_string += ' - dislike'
                else: against_string += ' - like'
                
            
            center_string = HC.u( len( self._media_to_initial_scores_dict ) ) + ' files being rated. after ' + HC.u( len( self._decision_log ) ) + ' decisions, ' + HC.u( len( certain_ratings ) ) + ' are certain'
            
        elif service_type == HC.LOCAL_RATING_NUMERICAL:
            
            ( min, max ) = self._media_to_current_scores_dict[ self._current_media_to_rate ]
            
            current_string = 'between ' + HC.ConvertNumericalRatingToPrettyString( self._lower, self._upper, min, out_of = False ) + ' and ' + HC.ConvertNumericalRatingToPrettyString( self._lower, self._upper, max, out_of = False )
            
            if self._current_media_to_rate_against in self._media_still_to_rate:
                
                ( other_min, other_max ) = self._media_to_current_scores_dict[ self._current_media_to_rate_against ]
                
                against_string = 'between ' + HC.ConvertNumericalRatingToPrettyString( self._lower, self._upper, other_min, out_of = False ) + ' and ' + HC.ConvertNumericalRatingToPrettyString( self._lower, self._upper, other_max, out_of = False )
                
            else:
                
                against_string = 'already rated'
                
                if self._current_media_to_rate_against in self._media_to_current_scores_dict:
                    
                    ( other_min, other_max ) = self._media_to_current_scores_dict[ self._current_media_to_rate_against ]
                    
                    rating = ( other_min + other_max ) / 2.0
                    
                else:
                    
                    ( local_ratings, remote_ratings ) = self._current_media_to_rate_against.GetRatings()
                    
                    rating = local_ratings.GetRating( self._service_identifier )
                    
                
                against_string += ' - ' + HC.ConvertNumericalRatingToPrettyString( self._lower, self._upper, rating )
                
            
            center_string = HC.u( len( self._media_to_initial_scores_dict ) ) + ' files being rated. after ' + HC.u( len( self._decision_log ) ) + ' decisions, ' + HC.u( len( certain_ratings ) ) + ' are certain and ' + HC.u( len( uncertain_ratings ) ) + ' are uncertain'
            
        
        if self._unrated_is_on_the_left:
            
            left_string = current_string
            right_string = against_string
            
        else:
            
            left_string = against_string
            right_string = current_string
            
        
        self._statusbar.SetStatusText( left_string, number = 0 )
        self._statusbar.SetStatusText( center_string, number = 1 )
        self._statusbar.SetStatusText( right_string, number = 2 )
        
    
    def _ReinitialiseCurrentScores( self ):
        
        self._media_to_current_scores_dict = dict( self._media_to_initial_scores_dict )
        
        self._already_rated_pairs = collections.defaultdict( set )
        
        for ( action, entry ) in self._decision_log:
            
            if action == 'external': ( min, max, media_rated, media_rated_against, unrated_was_on_the_left ) = entry
            elif action == 'internal':
                
                ( min, max, media_rated, other_min, other_max, media_rated_against, unrated_was_on_the_left ) = entry
                
                self._media_to_current_scores_dict[ media_rated_against ] = ( other_min, other_max )
                
            
            self._media_to_current_scores_dict[ media_rated ] = ( min, max )
            
            self._already_rated_pairs[ media_rated ].add( media_rated_against )
            self._already_rated_pairs[ media_rated_against ].add( media_rated )
            
        
        self._media_still_to_rate = { media for ( media, ( min, max ) ) in self._media_to_current_scores_dict.items() if max - min >= self._score_gap }
        
    
    def _ShowNewMedia( self ):
        
        if not ( self._compare_same and self._current_media_to_rate in self._media_still_to_rate ):
            
            ( self._current_media_to_rate, ) = random.sample( self._media_still_to_rate, 1 )
            
        
        ( min, max ) = self._media_to_current_scores_dict[ self._current_media_to_rate ]
        
        media_result_to_rate_against = HC.app.Read( 'ratings_media_result', self._service_identifier, min, max )
        
        if media_result_to_rate_against is not None:
            
            hash = media_result_to_rate_against.GetHash()
            
            if hash in self._file_query_result.GetHashes(): media_result_to_rate_against = self._file_query_result.GetMediaResult( hash )
            else: self._file_query_result.AddMediaResults( ( media_result_to_rate_against, ) )
            
            media_to_rate_against = ClientGUIMixins.MediaSingleton( media_result_to_rate_against )
            
        else: media_to_rate_against = None
        
        if media_to_rate_against in self._already_rated_pairs[ self._current_media_to_rate ]: media_to_rate_against = None
        
        if media_to_rate_against is None:
            
            internal_media = list( self._media_to_current_scores_dict.keys() )
            
            random.shuffle( internal_media )
            
            valid_internal_media = [ media for media in internal_media if media != self._current_media_to_rate and media not in self._already_rated_pairs[ self._current_media_to_rate ] and self._current_media_to_rate not in self._already_rated_pairs[ media ] ]
            
            best_media_first = Queue.PriorityQueue()
            
            for media in valid_internal_media:
                
                ( other_min, other_max ) = self._media_to_current_scores_dict[ media ]
                
                if not ( other_max < min or other_min > max ): # i.e. there is overlap in the two pairs of min,max
                    
                    # it is best when we have
                    #
                    #  #########
                    #    ####
                    #
                    # and better when the gaps are large (increasing the uncertainty)
                    
                    # when we must choose
                    #
                    #  #####
                    #    ######
                    #
                    # saying the second is better gives no change, so we want to minimise the gaps, to increase the likelyhood of a 50-50-ish situation (increasing the uncertainty)
                    # better we move by self._score_gap half the time than 0 most of the time.
                    
                    # the square root stuff prioritises middle-of-the-road results. two fives is more useful than ten and zero
                    # total gap value is in the range 0.0 - 1.0
                    # we times by -1 to prioritise and simultaneously reverse the overlapping-on-both-ends results for the priority queue
                    
                    min_gap = abs( other_min - min )
                    max_gap = abs( other_max - max )
                    
                    total_gap_value = ( min_gap ** 0.5 + max_gap ** 0.5 ) ** 2
                    
                    if ( other_min < min and other_max > max ) or ( other_min > min and other_max < max ): total_gap_value *= -1
                    
                    best_media_first.put( ( total_gap_value, media ) )
                    
                
            
            if best_media_first.qsize() > 0: ( value, media_to_rate_against ) = best_media_first.get()
            
        
        if media_to_rate_against is None:
            
            message = 'The client has run out of comparisons to show you, and still cannot deduce what ratings everything should have. Commit what decisions you have made, and then please either rate some more files manually, or ratings filter a larger group.'
            
            wx.MessageBox( message )
            
            self.EventClose( None )
            
        else:
            
            self._current_media_to_rate_against = media_to_rate_against
            
            if self._left_right == 'left': position = 0
            elif self._left_right == 'random': position = random.randint( 0, 1 )
            else: position = 1
            
            if position == 0:
                
                self._unrated_is_on_the_left = True
                
                self._left_window.SetMedia( self._current_media_to_rate )
                self._right_window.SetMedia( self._current_media_to_rate_against )
                
            else:
                
                self._unrated_is_on_the_left = False
                
                self._left_window.SetMedia( self._current_media_to_rate_against )
                self._right_window.SetMedia( self._current_media_to_rate )
                
            
            self._RefreshStatusBar()
            
        
    
    def _Skip( self ):
        
        if len( self._media_still_to_rate ) == 0: self.EventClose()
        else: self._ShowNewMedia()
        
    
    def _ProcessAction( self, action ):
        
        ( min, max ) = self._media_to_current_scores_dict[ self._current_media_to_rate ]
        
        if self._current_media_to_rate_against in self._media_to_current_scores_dict:
            
            ( other_min, other_max ) = self._media_to_current_scores_dict[ self._current_media_to_rate_against ]
            
            rate_other = self._current_media_to_rate_against in self._media_still_to_rate
            
            if action in ( 'left', 'right' ):
                
                if self._inequal_accuracy == self.RATINGS_FILTER_INEQUALITY_FULL: adjustment = self._score_gap
                if self._inequal_accuracy == self.RATINGS_FILTER_INEQUALITY_HALF: adjustment = 0
                elif self._inequal_accuracy == self.RATINGS_FILTER_INEQUALITY_QUARTER: adjustment = -self._score_gap
                
                if ( self._unrated_is_on_the_left and action == 'left' ) or ( not self._unrated_is_on_the_left and action == 'right' ):
                    
                    # unrated is better
                    
                    if min <= other_min:
                        
                        if min < other_min + adjustment: min = other_min + adjustment
                        else: min = other_min + self._score_gap / 2
                        
                    
                    if other_max >= max:
                        
                        if other_max > max - adjustment: other_max = max - adjustment
                        else: other_max = max - self._score_gap / 2
                        
                    
                    if min >= max: min = max
                    if other_max <= other_min: other_max = other_min
                    
                else:
                    
                    # unrated is worse
                    
                    if other_min <= min:
                        
                        if other_min < min + adjustment: other_min = min + adjustment
                        else: other_min = min + self._score_gap / 2
                        
                    
                    if max >= other_max:
                        
                        if max > other_max - adjustment: max = other_max - adjustment
                        else: max = other_max - self._score_gap / 2
                        
                    
                    if other_min >= other_max: other_min = other_max
                    if max <= min: max = min
                    
                
            elif action == 'equal':
                
                if self._equal_accuracy == self.RATINGS_FILTER_EQUALITY_FULL:
                    
                    if min < other_min: min = other_min
                    else: other_min = min
                    
                    if max > other_max: max = other_max
                    else: other_max = max
                    
                elif self._equal_accuracy == self.RATINGS_FILTER_EQUALITY_HALF:
                    
                    if min < other_min: min = ( min + other_min ) / 2
                    else: other_min = ( min + other_min ) / 2
                    
                    if max > other_max: max = ( max + other_max ) / 2
                    else: other_max = ( max + other_max ) / 2
                    
                elif self._equal_accuracy == self.RATINGS_FILTER_EQUALITY_QUARTER:
                    
                    if min < other_min: min = ( ( 3 * min ) + other_min ) / 4
                    else: other_min = ( min + ( 3 * other_min ) ) / 4
                    
                    if max > other_max: max = ( ( 3 * max ) + other_max ) / 4
                    else: other_max = ( max + ( 3 * other_max ) ) / 4
                    
                
            
            if min < 0.0: min = 0.0
            if max > 1.0: max = 1.0
            
            if other_min < 0.0: other_min = 0.0
            if other_max > 1.0: other_max = 1.0
            
            if max - min < self._score_gap: self._media_still_to_rate.discard( self._current_media_to_rate )
            
            if rate_other:
                
                if other_max - other_min < self._score_gap: self._media_still_to_rate.discard( self._current_media_to_rate_against )
                
                self._media_to_current_scores_dict[ self._current_media_to_rate_against ] = ( other_min, other_max )
                
            
            decision = ( 'internal', ( min, max, self._current_media_to_rate, other_min, other_max, self._current_media_to_rate_against, self._unrated_is_on_the_left ) )
            
        else:
            
            ( local_ratings, remote_ratings ) = self._current_media_to_rate_against.GetRatings()
            
            rating = local_ratings.GetRating( self._service_identifier )
            
            if action in ( 'left', 'right' ):
                
                if self._inequal_accuracy == self.RATINGS_FILTER_INEQUALITY_FULL: adjustment = self._score_gap
                if self._inequal_accuracy == self.RATINGS_FILTER_INEQUALITY_HALF: adjustment = 0
                elif self._inequal_accuracy == self.RATINGS_FILTER_INEQUALITY_QUARTER: adjustment = -self._score_gap
                
                if ( self._unrated_is_on_the_left and action == 'left' ) or ( not self._unrated_is_on_the_left and action == 'right' ):
                    
                    # unrated is better, so set new min
                    
                    if min <= rating:
                        
                        if min < rating + adjustment: min = rating + adjustment
                        else: min = rating + self._score_gap / 2
                        
                    
                    if min > max: min = max
                    
                else:
                    
                    # unrated is worse, so set new max
                    
                    if max >= rating:
                        
                        if max > rating - adjustment: max = rating - adjustment
                        else: max = rating - self._score_gap / 2
                        
                    
                    if max < min: max = min
                    
                
            elif action == 'equal':
                
                if self._equal_accuracy == self.RATINGS_FILTER_EQUALITY_FULL:
                    
                    min = rating
                    max = rating
                    
                elif self._equal_accuracy == self.RATINGS_FILTER_EQUALITY_HALF:
                    
                    min = ( min + rating ) / 2
                    max = ( max + rating ) / 2
                    
                elif self._equal_accuracy == self.RATINGS_FILTER_EQUALITY_QUARTER:
                    
                    min = ( ( 3 * min ) + rating ) / 4
                    max = ( ( 3 * max ) + rating ) / 4
                    
                
            
            if min < 0.0: min = 0.0
            if max > 1.0: max = 1.0
            
            decision = ( 'external', ( min, max, self._current_media_to_rate, self._current_media_to_rate_against, self._unrated_is_on_the_left ) )
            
        
        self._decision_log.append( decision )
        
        self._already_rated_pairs[ self._current_media_to_rate ].add( self._current_media_to_rate_against )
        self._already_rated_pairs[ self._current_media_to_rate_against ].add( self._current_media_to_rate )
        
        if max - min < self._score_gap: self._media_still_to_rate.discard( self._current_media_to_rate )
        
        self._media_to_current_scores_dict[ self._current_media_to_rate ] = ( min, max )
        
        if len( self._media_still_to_rate ) == 0: self.EventClose( None )
        else: self._ShowNewMedia()
        
    
    def EventButtonBack( self, event ): self._GoBack()
    def EventButtonDone( self, event ): self.EventClose( event )
    def EventButtonDontFilter( self, event ):
        
        self._media_still_to_rate.discard( self._current_media_to_rate )
        
        if len( self._media_still_to_rate ) == 0: self.EventClose( None )
        else: self._ShowNewMedia()
        
    def EventButtonEqual( self, event ): self._ProcessAction( 'equal' )
    def EventButtonLeft( self, event ): self._ProcessAction( 'right' )
    def EventButtonRight( self, event ): self._ProcessAction( 'left' )
    def EventButtonSkip( self, event ): self._Skip()
    
    def EventClose( self, event ):
        
        if len( self._decision_log ) > 0:
            
            def normalise_rating( rating ): return round( rating / self._score_gap ) * self._score_gap
            
            certain_ratings = [ ( normalise_rating( ( min + max ) / 2 ), media.GetHash() ) for ( media, ( min, max ) ) in self._media_to_current_scores_dict.items() if max - min < self._score_gap ]
            uncertain_ratings = [ ( min, max, media.GetHash() ) for ( media, ( min, max ) ) in self._media_to_current_scores_dict.items() if max - min >= self._score_gap and self._media_to_current_scores_dict[ media ] != self._media_to_initial_scores_dict[ media ] ]
            
            with ClientGUIDialogs.DialogFinishRatingFiltering( self, len( certain_ratings ), len( uncertain_ratings ) ) as dlg:
                
                modal = dlg.ShowModal()
                
                if modal == wx.ID_CANCEL:
                    
                    self._ShowNewMedia()
                    
                    return
                    
                elif modal == wx.ID_YES:
                    
                    content_updates = []
                    
                    content_updates.extend( [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, set( ( hash, ) ) ) ) for ( rating, hash ) in certain_ratings ] )
                    content_updates.extend( [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_RATINGS, HC.CONTENT_UPDATE_RATINGS_FILTER, ( min, max, set( ( hash, ) ) ) ) for ( min, max, hash ) in uncertain_ratings ] )
                    
                    HC.app.Write( 'content_updates', { self._service_identifier : content_updates } )
                    
                
            
        
        HC.pubsub.pub( 'set_focus', self._page_key, self._current_media_to_rate )
        
        if HC.PLATFORM_OSX and self.IsFullScreen(): self.ShowFullScreen( False )
        
        wx.CallAfter( self.Destroy )
        
    
    def EventFullscreenSwitch( self, event ): self._FullscreenSwitch()
    
    def EventCharHook( self, event ):
        
        ( modifier, key ) = HC.GetShortcutFromEvent( event )
        
        if modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_SPACE, wx.WXK_UP, wx.WXK_NUMPAD_UP ): self._Skip()
        elif modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN ): self._ProcessAction( 'equal' )
        elif modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_LEFT, wx.WXK_NUMPAD_LEFT ): self._ProcessAction( 'left' )
        elif modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_RIGHT, wx.WXK_NUMPAD_RIGHT ): self._ProcessAction( 'right' )
        elif modifier == wx.ACCEL_NORMAL and key == wx.WXK_BACK: self._GoBack()
        elif modifier == wx.ACCEL_NORMAL and key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ): self.EventClose( event )
        elif modifier == wx.ACCEL_CTRL and key == ord( 'C' ):
            with wx.BusyCursor(): HC.app.Write( 'copy_files', ( self._current_media.GetHash(), ) )
        else:
            
            key_dict = HC.options[ 'shortcuts' ][ modifier ]
            
            if key in key_dict:
                
                action = key_dict[ key ]
                
                self.ProcessEvent( wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) )
                
            else: event.Skip()
            
        
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'fullscreen_switch': self._FullscreenSwitch()
            else: event.Skip()
            
        
    
    def EventMouseDown( self, event ):
        
        if event.ButtonDown( wx.MOUSE_BTN_LEFT ): self._ProcessAction( 'left' )
        elif event.ButtonDown( wx.MOUSE_BTN_RIGHT ): self._ProcessAction( 'right' )
        elif event.ButtonDown( wx.MOUSE_BTN_MIDDLE ): self._ProcessAction( 'equal' )
        
    
    def ProcessContentUpdates( self, service_identifiers_to_content_updates ):
        
        redraw = False
        
        my_hashes = self._file_query_result.GetHashes()
        
        for ( service_identifier, content_updates ) in service_identifiers_to_content_updates.items():
            
            for content_update in content_updates:
                
                content_update_hashes = content_update.GetHashes()
                
                if len( my_hashes.intersection( content_update_hashes ) ) > 0:
                    
                    redraw = True
                    
                    break
                    
                
            
        
        if redraw:
            
            self._left_window.RefreshBackground()
            self._right_window.RefreshBackground()
            
        
    
    def ProcessServiceUpdates( self, service_identifiers_to_service_updates ):
        
        self._left_window.RefreshBackground()
        self._right_window.RefreshBackground()
        
    
    def SetAccuracy( self, accuracy ):
        
        if accuracy == 0: self._equal_accuracy = self.RATINGS_FILTER_EQUALITY_FULL
        elif accuracy <= 2: self._equal_accuracy = self.RATINGS_FILTER_EQUALITY_HALF
        else: self._equal_accuracy = self.RATINGS_FILTER_EQUALITY_QUARTER
        
        if accuracy <= 1: self._inequal_accuracy = self.RATINGS_FILTER_INEQUALITY_FULL
        elif accuracy <= 3: self._inequal_accuracy = self.RATINGS_FILTER_INEQUALITY_HALF
        else: self._inequal_accuracy = self.RATINGS_FILTER_INEQUALITY_QUARTER
        
        HC.options[ 'ratings_filter_accuracy' ] = accuracy
        
        HC.app.Write( 'save_options' )
        
    
    def SetCompareSame( self, compare_same ):
        
        HC.options[ 'ratings_filter_compare_same' ] = compare_same
        
        HC.app.Write( 'save_options' )
        
        self._compare_same = compare_same
        
    
    def SetLeftRight( self, left_right ):
        
        HC.options[ 'ratings_filter_left_right' ] = left_right
        
        HC.app.Write( 'save_options' )
        
        self._left_right = left_right
        
    
    class _Panel( Canvas, wx.Window ):
        
        def __init__( self, parent ):
            
            wx.Window.__init__( self, parent, style = wx.SIMPLE_BORDER | wx.WANTS_CHARS )
            Canvas.__init__( self, HC.LOCAL_FILE_SERVICE_IDENTIFIER, HC.app.GetFullscreenImageCache() )
            
            wx.CallAfter( self.Refresh )
            
            self.Bind( wx.EVT_MOTION, self.EventDrag )
            self.Bind( wx.EVT_LEFT_DOWN, self.EventDragBegin )
            self.Bind( wx.EVT_RIGHT_DOWN, self.GetParent().GetParent().EventMouseDown )
            self.Bind( wx.EVT_MIDDLE_DOWN, self.GetParent().GetParent().EventMouseDown )
            self.Bind( wx.EVT_LEFT_UP, self.EventDragEnd )
            self.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
            self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
            
            self._timer_cursor_hide = wx.Timer( self, id = ID_TIMER_CURSOR_HIDE )
            
            self.Bind( wx.EVT_TIMER, self.TIMEREventCursorHide, id = ID_TIMER_CURSOR_HIDE )
            
            self.Bind( wx.EVT_MENU, self.EventMenu )
            
        
        def _ZoomIn( self ):
            
            if self._current_media is not None:
                
                if self._current_media.GetMime() in NON_ZOOMABLE_MIMES: return
                
                for zoom in ZOOMINS:
                    
                    if self._current_zoom < zoom:
                        
                        if self._current_media.GetMime() in NON_LARGABLY_ZOOMABLE_MIMES:
                            
                            # because of the event passing under mouse, we want to preserve whitespace around flash
                            
                            ( original_width, original_height ) = self._current_display_media.GetResolution()
                            
                            ( my_width, my_height ) = self.GetClientSize()
                            
                            new_media_width = int( round( original_width * zoom ) )
                            new_media_height = int( round( original_height * zoom ) )
                            
                            if new_media_width >= my_width or new_media_height >= my_height: return
                            
                        
                        with wx.FrozenWindow( self ):
                            
                            ( drag_x, drag_y ) = self._total_drag_delta
                            
                            zoom_ratio = zoom / self._current_zoom
                            
                            self._total_drag_delta = ( int( drag_x * zoom_ratio ), int( drag_y * zoom_ratio ) )
                            
                            self._current_zoom = zoom
                            
                            self._DrawBackgroundBitmap()
                            
                            self._DrawCurrentMedia()
                            
                        
                        break
                        
                    
                
            
        
        def _ZoomOut( self ):
            
            if self._current_media is not None:
                
                if self._current_media.GetMime() in NON_ZOOMABLE_MIMES: return
                
                for zoom in ZOOMOUTS:
                    
                    if self._current_zoom > zoom:
                        
                        with wx.FrozenWindow( self ):
                            
                            ( drag_x, drag_y ) = self._total_drag_delta
                            
                            zoom_ratio = zoom / self._current_zoom
                            
                            self._total_drag_delta = ( int( drag_x * zoom_ratio ), int( drag_y * zoom_ratio ) )
                            
                            self._current_zoom = zoom
                            
                            self._DrawBackgroundBitmap()
                            
                            self._DrawCurrentMedia()
                            
                        
                        break
                        
                    
                
            
        
        def _ZoomSwitch( self ):
            
            ( my_width, my_height ) = self.GetClientSize()
            
            ( media_width, media_height ) = self._current_display_media.GetResolution()
            
            if self._current_media.GetMime() in NON_ZOOMABLE_MIMES: return
            
            if self._current_media.GetMime() not in NON_LARGABLY_ZOOMABLE_MIMES or self._current_zoom > 1.0 or ( media_width < my_width and media_height < my_height ):
                
                new_zoom = self._current_zoom
                
                if self._current_zoom == 1.0:
                    
                    if media_width > my_width or media_height > my_height:
                        
                        width_zoom = my_width / float( media_width )
                        
                        height_zoom = my_height / float( media_height )
                        
                        new_zoom = min( ( width_zoom, height_zoom ) )
                        
                    
                else: new_zoom = 1.0
                
                if new_zoom != self._current_zoom:
                    
                    ( drag_x, drag_y ) = self._total_drag_delta
                    
                    zoom_ratio = new_zoom / self._current_zoom
                    
                    self._total_drag_delta = ( int( drag_x * zoom_ratio ), int( drag_y * zoom_ratio ) )
                    
                    self._current_zoom = new_zoom
                    
                    self._DrawBackgroundBitmap()
                    
                    self._DrawCurrentMedia()
                    
                
            
        
        def EventDrag( self, event ):
            
            CC.CAN_HIDE_MOUSE = True
            
            if wx.Window.FindFocus() != self: self.SetFocus()
            
            if event.Dragging() and self._last_drag_coordinates is not None:
                
                ( old_x, old_y ) = self._last_drag_coordinates
                
                ( x, y ) = event.GetPosition()
                
                ( delta_x, delta_y ) = ( x - old_x, y - old_y )
                
                try:
                    
                    if HC.PLATFORM_OSX: raise Exception() # can't warppointer in os x
                    
                    self.WarpPointer( old_x, old_y )
                    
                except: self._last_drag_coordinates = ( x, y )
                
                ( old_delta_x, old_delta_y ) = self._total_drag_delta
                
                self._total_drag_delta = ( old_delta_x + delta_x, old_delta_y + delta_y )
                
                self._DrawCurrentMedia()
                
            
            self.SetCursor( wx.StockCursor( wx.CURSOR_ARROW ) )
            
            self._timer_cursor_hide.Start( 800, wx.TIMER_ONE_SHOT )
            
        
        def EventDragBegin( self, event ):
            
            if event.ShiftDown():
                
                ( x, y ) = event.GetPosition()
                
                ( client_x, client_y ) = self.GetClientSize()
                
                if x < 20 or x > client_x - 20 or y < 20 or y > client_y -20:
                    
                    try:
                        
                        better_x = x
                        better_y = y
                        
                        if x < 20: better_x = 20
                        if y < 20: better_y = 20
                        
                        if x > client_x - 20: better_x = client_x - 20
                        if y > client_y - 20: better_y = client_y - 20
                        
                        if HC.PLATFORM_OSX: raise Exception() # can't warppointer in os x
                        
                        self.WarpPointer( better_x, better_y )
                        
                        x = better_x
                        y = better_y
                        
                    except: pass
                    
                
                self._last_drag_coordinates = ( x, y )
                
            else: self.GetParent().GetParent().ProcessEvent( event )
            
        
        def EventDragEnd( self, event ):
            
            self._last_drag_coordinates = None
            
            event.Skip()
            
        
        def EventCharHook( self, event ):
            
            if self._ShouldSkipInputDueToFlash(): event.Skip()
            else:
                
                keys_i_want_to_bump_up_regardless = [ wx.WXK_SPACE, wx.WXK_UP, wx.WXK_NUMPAD_UP, wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN, wx.WXK_LEFT, wx.WXK_NUMPAD_LEFT, wx.WXK_RIGHT, wx.WXK_NUMPAD_RIGHT, wx.WXK_BACK, wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ]
                
                ( modifier, key ) = HC.GetShortcutFromEvent( event )
                
                key_dict = HC.options[ 'shortcuts' ][ modifier ]
                
                if key not in keys_i_want_to_bump_up_regardless and key in key_dict:
                    
                    action = key_dict[ key ]
                    
                    self.ProcessEvent( wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) )
                    
                else:
                    
                    if modifier == wx.ACCEL_NORMAL and key in ( ord( '+' ), wx.WXK_ADD, wx.WXK_NUMPAD_ADD ): self._ZoomIn()
                    elif modifier == wx.ACCEL_NORMAL and key in ( ord( '-' ), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT ): self._ZoomOut()
                    elif modifier == wx.ACCEL_NORMAL and key == ord( 'Z' ): self._ZoomSwitch()
                    elif modifier == wx.ACCEL_CTRL and key == ord( 'C' ):
                        with wx.BusyCursor(): HC.app.Write( 'copy_files', ( self._current_media.GetHash(), ) )
                    else: self.GetParent().ProcessEvent( event )
                    
            
        
        def EventMenu( self, event ):
            
            if self._ShouldSkipInputDueToFlash(): event.Skip()
            else:
                
                action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
                
                if action is not None:
                    
                    ( command, data ) = action
                    
                    if command == 'frame_back': self._media_container.GotoPreviousOrNextFrame( -1 )
                    elif command == 'frame_next': self._media_container.GotoPreviousOrNextFrame( 1 )
                    elif command == 'manage_ratings': self._ManageRatings()
                    elif command == 'manage_tags': self._ManageTags()
                    elif command == 'zoom_in': self._ZoomIn()
                    elif command == 'zoom_out': self._ZoomOut()
                    else: event.Skip()
                    
                
            
        
        def EventMouseWheel( self, event ):
            
            if self._ShouldSkipInputDueToFlash(): event.Skip()
            else:
                
                if event.CmdDown():
                    
                    if event.GetWheelRotation() > 0: self._ZoomIn()
                    else: self._ZoomOut()
                    
                
            
        
        def RefreshBackground( self ): self._DrawBackgroundBitmap()
        
        def TIMEREventCursorHide( self, event ):
            
            if not CC.CAN_HIDE_MOUSE: return
            
            self.SetCursor( wx.StockCursor( wx.CURSOR_BLANK ) )
            
        
    
class MediaContainer( wx.Window ):
    
    def __init__( self, parent, image_cache, media, initial_size, initial_position ):
        
        wx.Window.__init__( self, parent, size = initial_size, pos = initial_position )
        
        self._image_cache = image_cache
        self._media = media
        self._media_window = None
        self._embed_button = None
        
        self._MakeMediaWindow()
        
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_MOUSE_EVENTS, self.EventPropagateMouse )
        
        self.EventResize( None )
        
    
    def _MakeMediaWindow( self, do_embed_button = True ):
        
        ( media_initial_size, media_initial_position ) = ( self.GetClientSize(), ( 0, 0 ) )
        
        if do_embed_button and self._media.GetMime() in ( HC.VIDEO_FLV, HC.APPLICATION_FLASH ):
            
            self._embed_button = EmbedButton( self, media_initial_size )
            self._embed_button.Bind( wx.EVT_LEFT_DOWN, self.EventEmbedButton )
            
            return
            
        elif self._embed_button is not None: self._embed_button.Hide()
        
        if ShouldHaveAnimationBar( self._media ):
            
            ( x, y ) = media_initial_size
            
            media_initial_size = ( x, y - ANIMATED_SCANBAR_HEIGHT )
            
        
        if self._media.GetMime() in HC.IMAGES: self._media_window = Image( self, self._media, self._image_cache, media_initial_size, media_initial_position )
        elif self._media.GetMime() == HC.APPLICATION_FLASH:
            
            self._media_window = wx.lib.flashwin.FlashWindow( self, size = media_initial_size, pos = media_initial_position )
            
            self._media_window.movie = CC.GetFilePath( self._media.GetHash(), HC.APPLICATION_FLASH )
            
        elif self._media.GetMime() == HC.VIDEO_FLV:
            
            self._media_window = wx.lib.flashwin.FlashWindow( self, size = media_initial_size, pos = media_initial_position )
            
            flash_vars = []
            flash_vars.append( ( 'flv', CC.GetFilePath( self._media.GetHash(), HC.VIDEO_FLV ) ) )
            flash_vars.append( ( 'margin', '0' ) )
            flash_vars.append( ( 'autoload', '1' ) )
            flash_vars.append( ( 'autoplay', '1' ) )
            flash_vars.append( ( 'showvolume', '1' ) )
            flash_vars.append( ( 'showtime', '1' ) )
            flash_vars.append( ( 'loop', '1' ) )
            
            f = urllib.urlencode( flash_vars )
            
            self._media_window.flashvars = f
            self._media_window.movie = HC.STATIC_DIR + os.path.sep + 'player_flv_maxi_1.6.0.swf'
            
        elif self._media.GetMime() == HC.APPLICATION_PDF: self._media_window = PDFButton( self, self._media.GetHash(), media_initial_size )
        elif self._media.GetMime() in HC.AUDIO: self._media_window = EmbedWindowAudio( self, self._media.GetHash(), self._media.GetMime(), media_initial_size )
        elif self._media.GetMime() in ( HC.VIDEO_MP4, HC.VIDEO_WMV ): self._media_window = EmbedWindowVideo( self, self._media.GetHash(), self._media.GetMime(), media_initial_size )
        
        if ShouldHaveAnimationBar( self._media ):
            
            self._animation_bar = AnimationBar( self, self._media, self._media_window )
            
            if self._media.GetMime() == HC.IMAGE_GIF: self._media_window.SetAnimationBar( self._animation_bar )
            
        
    
    def EventEmbedButton( self, event ):
        
        self._MakeMediaWindow( do_embed_button = False )
        
    
    def EventPropagateMouse( self, event ):
        
        if self._media.GetMime() in HC.IMAGES:
            
            screen_position = self.ClientToScreen( event.GetPosition() )
            ( x, y ) = self.GetParent().ScreenToClient( screen_position )
            
            event.SetX( x )
            event.SetY( y )
            
            event.ResumePropagation( 1 )
            event.Skip()
            
        
    
    def EventResize( self, event ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        if self._media_window is None:
            
            self._embed_button.SetSize( ( my_width, my_height ) )
            
        else:
            
            ( media_width, media_height ) = ( my_width, my_height )
            
            if ShouldHaveAnimationBar( self._media ):
                
                media_height -= ANIMATED_SCANBAR_HEIGHT
                
                self._animation_bar.SetSize( ( my_width, ANIMATED_SCANBAR_HEIGHT ) )
                self._animation_bar.SetPosition( ( 0, my_height - ANIMATED_SCANBAR_HEIGHT ) )
                
            
            self._media_window.SetSize( ( media_width, media_height ) )
            self._media_window.SetPosition( ( 0, 0 ) )
            
        
    
    def GotoPreviousOrNextFrame( self, direction ):
        
        if self._media_window is not None:
            
            if ShouldHaveAnimationBar( self._media ):
                
                current_frame_index = self._media_window.CurrentFrame()
                
                num_frames = self._media.GetNumFrames()
                
                if direction == 1:
                    
                    if current_frame_index == num_frames - 1: current_frame_index = 0
                    else: current_frame_index += 1
                    
                else:
                    
                    if current_frame_index == 0: current_frame_index = num_frames - 1
                    else: current_frame_index -= 1
                    
                
                self._media_window.GotoFrame( current_frame_index )
                self._animation_bar.GotoFrame( current_frame_index )
                
            
        
    
class EmbedButton( wx.Window ):
    
    def __init__( self, parent, size ):
        
        wx.Window.__init__( self, parent, size = size )
        
        self._Redraw()
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        
    
    def _Redraw( self ):
        
        ( x, y ) = self.GetClientSize()
        
        self._canvas_bmp = wx.EmptyBitmap( x, y, 24 )
        
        dc = wx.BufferedDC( wx.ClientDC( self ), self._canvas_bmp )
        
        dc.SetBackground( wx.WHITE_BRUSH )
        
        dc.Clear() # gcdc doesn't support clear
        
        dc = wx.GCDC( dc )
        
        center_x = x / 2
        center_y = y / 2
        radius = min( center_x, center_y ) - 5
        
        dc.SetPen( wx.TRANSPARENT_PEN )
        
        dc.SetBrush( wx.Brush( wx.Colour( 215, 215, 215 ) ) )
        
        dc.DrawCircle( center_x, center_y, radius )
        
        dc.SetBrush( wx.WHITE_BRUSH )
        
        m = ( 2 ** 0.5 ) / 2 # 45 degree angle
        
        half_radius = radius / 2
        
        angle_half_radius = m * half_radius
        
        points = []
        
        points.append( ( center_x - angle_half_radius, center_y - angle_half_radius ) )
        points.append( ( center_x + half_radius, center_y ) )
        points.append( ( center_x - angle_half_radius, center_y + angle_half_radius ) )
        
        dc.DrawPolygon( points )
        
    
    def EventPaint( self, event ): wx.BufferedPaintDC( self, self._canvas_bmp )
    
    def EventResize( self, event ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        ( current_bmp_width, current_bmp_height ) = self._canvas_bmp.GetSize()
        
        if my_width != current_bmp_width or my_height != current_bmp_height:
            
            if my_width > 0 and my_height > 0: self._Redraw()
            
        
    
class EmbedWindowAudio( wx.Window ):
    
    def __init__( self, parent, hash, mime, size ):
        
        wx.Window.__init__( self, parent, size = size )
        
        self.SetCursor( wx.StockCursor( wx.CURSOR_ARROW ) )
        
        self._hash = hash
        self._mime = mime
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        ( width, height ) = size
        
        media_height = height - 45
        
        self._media_ctrl = wx.media.MediaCtrl( self, size = ( width, media_height ) )
        self._media_ctrl.Hide()
        
        self._embed_button = EmbedButton( self, size = ( width, media_height ) )
        self._embed_button.Bind( wx.EVT_LEFT_DOWN, self.EventEmbedButton )
        
        launch_button = wx.Button( self, label = 'launch ' + HC.mime_string_lookup[ mime ] + ' externally', size = ( width, 45 ), pos = ( 0, media_height ) )
        launch_button.Bind( wx.EVT_BUTTON, self.EventLaunchButton )
        
    
    def EventEmbedButton( self, event ):
        
        self._embed_button.Hide()
        
        self._media_ctrl.ShowPlayerControls( wx.media.MEDIACTRLPLAYERCONTROLS_DEFAULT )
        
        path = CC.GetFilePath( self._hash, self._mime )
        
        self._media_ctrl.Load( path )
        
        self._media_ctrl.Show()
        
    
    def EventLaunchButton( self, event ):
        
        path = CC.GetFilePath( self._hash, self._mime )
        
        subprocess.call( 'start "" "' + path + '"', shell = True )
        
    
class EmbedWindowVideo( wx.Window ):
    
    def __init__( self, parent, hash, mime, size ):
        
        wx.Window.__init__( self, parent, size = size )
        
        self.SetCursor( wx.StockCursor( wx.CURSOR_ARROW ) )
        
        self._hash = hash
        self._mime = mime
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        ( width, height ) = size
        
        media_height = height - 45
        
        self._media_ctrl = wx.media.MediaCtrl( self, size = ( width, media_height ) )
        self._media_ctrl.Hide()
        
        self._embed_button = EmbedButton( self, size = ( width, media_height ) )
        self._embed_button.Bind( wx.EVT_LEFT_DOWN, self.EventEmbedButton )
        
        launch_button = wx.Button( self, label = 'launch ' + HC.mime_string_lookup[ mime ] + ' externally', size = ( width, 45 ), pos = ( 0, media_height ) )
        launch_button.Bind( wx.EVT_BUTTON, self.EventLaunchButton )
        
    
    def EventEmbedButton( self, event ):
        
        self._embed_button.Hide()
        
        self._media_ctrl.ShowPlayerControls( wx.media.MEDIACTRLPLAYERCONTROLS_DEFAULT )
        
        path = CC.GetFilePath( self._hash, self._mime )
        
        self._media_ctrl.Load( path )
        
        self._media_ctrl.Show()
        
    
    def EventLaunchButton( self, event ):
        
        path = CC.GetFilePath( self._hash, self._mime )
        
        # os.system( 'start ' + path )
        subprocess.call( 'start "" "' + path + '"', shell = True )
        
    
class Image( wx.Window ):
    
    def __init__( self, parent, media, image_cache, initial_size, initial_position ):
        
        wx.Window.__init__( self, parent, size = initial_size, pos = initial_position )
        
        self.SetDoubleBuffered( True )
        
        self._media = media
        self._image_container = None
        self._image_cache = image_cache
        
        self._animation_bar = None
        
        self._last_clock = time.clock()
        self._current_frame_index = 0
        
        self._canvas_bmp = wx.EmptyBitmap( 0, 0, 24 )
        
        self._timer_animated = wx.Timer( self, id = ID_TIMER_ANIMATED )
        
        self._yet_to_draw_initial_frame = True
        
        self._paused = False
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_TIMER, self.TIMEREventAnimated, id = ID_TIMER_ANIMATED )
        self.Bind( wx.EVT_MOUSE_EVENTS, self.EventPropagateMouse )
        
        self.EventResize( None )
        
        self._timer_animated.Start( 16, wx.TIMER_CONTINUOUS )
        
    
    def _Draw( self ):
        
        dc = wx.BufferedDC( wx.ClientDC( self ), self._canvas_bmp )
        
        if self._image_container.HasFrame( self._current_frame_index ):
            
            if not self._image_container.IsAnimated():
                
                dc.SetBackground( wx.Brush( wx.WHITE ) )
                
                dc.Clear()
                
            
            current_frame = self._image_container.GetFrame( self._current_frame_index )
            
            ( my_width, my_height ) = self._canvas_bmp.GetSize()
            
            ( frame_width, frame_height ) = current_frame.GetSize()
            
            x_scale = my_width / float( frame_width )
            y_scale = my_height / float( frame_height )
            
            dc.SetUserScale( x_scale, y_scale )
            
            hydrus_bmp = current_frame.CreateWxBmp()
            
            dc.DrawBitmap( hydrus_bmp, 0, 0 )
            
            wx.CallAfter( hydrus_bmp.Destroy )
            
            dc.SetUserScale( 1.0, 1.0 )
            
            if self._image_container.IsAnimated():
                
                if self._animation_bar is not None: self._animation_bar.GotoFrame( self._current_frame_index )
                
            else: self._timer_animated.Stop()
            
        else:
            
            dc.SetBackground( wx.Brush( wx.WHITE ) )
            
            dc.Clear()
            
        
    
    def CurrentFrame( self ): return self._current_frame_index
    
    def EventPaint( self, event ): wx.BufferedPaintDC( self, self._canvas_bmp )
    
    def EventPropagateMouse( self, event ):
        
        screen_position = self.ClientToScreen( event.GetPosition() )
        ( x, y ) = self.GetParent().ScreenToClient( screen_position )
        
        event.SetX( x )
        event.SetY( y )
        
        event.ResumePropagation( 1 )
        event.Skip()
        
    
    def EventResize( self, event ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        ( current_bmp_width, current_bmp_height ) = self._canvas_bmp.GetSize()
        
        if my_width != current_bmp_width or my_height != current_bmp_height:
            
            if my_width > 0 and my_height > 0:
                
                if self._image_container is None: self._image_container = self._image_cache.GetImage( self._media.GetHash(), self._media.GetMime(), ( my_width, my_height ) )
                else:
                    
                    ( image_width, image_height ) = self._image_container.GetSize()
                    
                    we_just_zoomed_in = my_width > image_width
                    
                    if we_just_zoomed_in and self._image_container.IsScaled():
                        
                        full_resolution = self._image_container.GetResolution()
                        
                        self._image_container = self._image_cache.GetImage( self._media.GetHash(), self._media.GetMime(), full_resolution )
                        
                        self._yet_to_draw_initial_frame = True
                        
                        self._timer_animated.Start()
                        
                    
                
                wx.CallAfter( self._canvas_bmp.Destroy )
                
                self._canvas_bmp = wx.EmptyBitmap( my_width, my_height, 24 )
                
                self._Draw()
                
            
        
    
    def GetImageContainer( self ): return self._image_container
    
    def GotoFrame( self, frame_index ):
        
        self._current_frame_index = frame_index
        
        self._Draw()
        
        self._timer_animated.Stop()
        
    
    def Play( self ): self._timer_animated.Start()
    
    def SetAnimationBar( self, animation_bar ): self._animation_bar = animation_bar
    
    def TIMEREventAnimated( self, event ):
        
        if self.IsShown():
            
            now = time.clock()
            
            ms_since_last_clock = int( 1000.0 * ( now - self._last_clock ) )
            
            if self._yet_to_draw_initial_frame or ms_since_last_clock > self._image_container.GetDuration( self._current_frame_index ):
                
                if self._yet_to_draw_initial_frame: next_frame = 0
                else:
                    
                    num_frames = self._media.GetNumFrames()
                    
                    if num_frames is None: next_frame = 0
                    else: next_frame = ( self._current_frame_index + 1 ) % num_frames
                    
                
                if self._image_container.HasFrame( next_frame ):
                    
                    self._current_frame_index = next_frame
                    
                    self._last_clock = now
                    
                    self._Draw()
                    
                    self._yet_to_draw_initial_frame = False
                    
                
            
        
    
class PDFButton( wx.Button ):
    
    def __init__( self, parent, hash, size ):
        
        wx.Button.__init__( self, parent, label = 'launch pdf', size = size )
        
        self.SetCursor( wx.StockCursor( wx.CURSOR_ARROW ) )
        
        self._hash = hash
        
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        
    
    def EventButton( self, event ):
        
        path = CC.GetFilePath( self._hash, HC.APPLICATION_PDF )
        
        # os.system( 'start ' + path )
        subprocess.call( 'start "" "' + path + '"', shell = True )
        
    