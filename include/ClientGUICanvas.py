import HydrusConstants as HC
import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
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
import wx.lib.flashwin

ID_TIMER_ANIMATED = wx.NewId()
ID_TIMER_SLIDESHOW = wx.NewId()
ID_TIMER_CURSOR_HIDE = wx.NewId()

ANIMATED_SCANBAR_HEIGHT = 20
ANIMATED_SCANBAR_CARET_WIDTH = 10

# Zooms

ZOOMINS = [ 0.01, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0 ]
ZOOMOUTS = [ 20.0, 10.0, 5.0, 3.0, 2.0, 1.5, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.5, 0.3, 0.2, 0.15, 0.1, 0.05, 0.01 ]

# Sizer Flags

FLAGS_NONE = wx.SizerFlags( 0 )

FLAGS_SMALL_INDENT = wx.SizerFlags( 0 ).Border( wx.ALL, 2 )

FLAGS_EXPAND_PERPENDICULAR = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_BOTH_WAYS = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Expand()

FLAGS_EXPAND_SIZER_PERPENDICULAR = wx.SizerFlags( 0 ).Expand()
FLAGS_EXPAND_SIZER_BOTH_WAYS = wx.SizerFlags( 2 ).Expand()

FLAGS_BUTTON_SIZERS = wx.SizerFlags( 0 ).Align( wx.ALIGN_RIGHT )
FLAGS_LONE_BUTTON = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_RIGHT )

FLAGS_MIXED = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

class Canvas():
    
    def __init__( self, file_service_identifier, image_cache ):
        
        self._file_service_identifier = file_service_identifier
        self._image_cache = image_cache
        
        self._service_identifiers_to_services = {}
        
        self._focus_holder = wx.Window( self )
        self._focus_holder.Hide()
        self._focus_holder.SetEventHandler( self )
        
        self._options = wx.GetApp().Read( 'options' )
        
        self._current_media = None
        self._current_display_media = None
        self._media_window = None
        self._current_zoom = 1.0
        
        self._last_drag_coordinates = None
        self._total_drag_delta = ( 0, 0 )
        
        self.SetBackgroundColour( wx.WHITE )
        
        self._canvas_bmp = wx.EmptyBitmap( 0, 0, 24 )
        
        self.Bind( wx.EVT_SIZE, self.EventResize )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        
    
    def _ChangeFrame( self, direction ):
        
        if self._current_media.GetMime() == HC.IMAGE_GIF and self._current_media.HasDuration(): self._media_window.ChangeFrame( direction )
        
    
    def _DrawBackgroundBitmap( self ):
        
        ( client_width, client_height ) = self.GetClientSize()
        
        cdc = wx.ClientDC( self )
        
        dc = wx.BufferedDC( cdc, self._canvas_bmp )
        
        dc.SetBackground( wx.Brush( wx.WHITE ) )
        
        dc.Clear()
        
        if self._current_media is not None:
            
            # tags on the top left
            
            dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
            
            tags_cdpp = self._current_media.GetTags()
            
            ( current, deleted, pending, petitioned ) = tags_cdpp.GetUnionCDPP()
            
            tags_i_want_to_display = list( current.union( pending ).union( petitioned ) )
            
            tags_i_want_to_display.sort()
            
            current_y = 3
            
            namespace_colours = self._options[ 'namespace_colours' ]
            
            for tag in tags_i_want_to_display:
                
                if tag in current: display_string = tag
                elif tag in pending: display_string = '(+) ' + tag
                elif tag in petitioned: display_string = '(-) ' + tag
                
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
                    
                    service = wx.GetApp().Read( 'service', service_identifier )
                    
                    self._service_identifiers_to_services[ service_identifier ] = service
                    
                
                if service_type == HC.LOCAL_RATING_LIKE:
                    
                    ( like, dislike ) = service.GetExtraInfo()
                    
                    if rating == 1: s = like
                    elif rating == 0: s = dislike
                    
                elif service_type == HC.LOCAL_RATING_NUMERICAL:
                    
                    ( lower, upper ) = service.GetExtraInfo()
                    
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
            
            if self._current_media is not None: self._SizeAndPositionMediaWindow()
            
        
    
    def _GetCollectionsString( self ): return ''
    
    def _GetInfoString( self ):
        
        info_string = self._current_media.GetPrettyInfo()
        
        return info_string
        
    
    def _GetIndexString( self ): return ''
    
    def _GetMediaWindowSizeAndPosition( self ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        if self._current_display_media.GetMime() == HC.APPLICATION_PDF: ( original_width, original_height ) = ( 200, 45 ) # for button
        else: ( original_width, original_height ) = self._current_display_media.GetResolution()
        
        media_width = int( round( original_width * self._current_zoom ) )
        media_height = int( round( original_height * self._current_zoom ) )
        
        if self._current_display_media.GetMime() == HC.IMAGE_GIF and self._current_display_media.HasDuration(): media_height += ANIMATED_SCANBAR_HEIGHT
        
        ( drag_x, drag_y ) = self._total_drag_delta
        
        x_offset = ( my_width - media_width ) / 2 + drag_x
        y_offset = ( my_height - media_height ) / 2 + drag_y
        
        new_size = ( media_width, media_height )
        new_position = ( x_offset, y_offset )
        
        return ( new_size, new_position )
        
    
    def _ManageRatings( self ):
        
        if self._current_media is not None:
            
            try:
                with ClientGUIDialogs.DialogManageRatings( self, ( self._current_media, ) ) as dlg: dlg.ShowModal()
            except: wx.MessageBox( 'Had a problem displaying the manage ratings dialog from fullscreen.' )
            
        
    
    def _ManageTags( self ):
        
        if self._current_media is not None:
            
            try:
                with ClientGUIDialogs.DialogManageTags( self, self._file_service_identifier, ( self._current_media, ) ) as dlg: dlg.ShowModal()
            except: wx.MessageBox( 'Had a problem displaying the manage tags dialog from fullscreen.' )
            
        
    
    def _PrefetchImages( self ): pass
    
    def _RecalcZoom( self ):
        
        if self._current_display_media is None: self._current_zoom = 1.0
        else:
            
            ( my_width, my_height ) = self.GetClientSize()
            
            ( media_width, media_height ) = self._current_display_media.GetResolution()
            
            if media_width > my_width or media_height > my_height:
                
                width_zoom = my_width / float( media_width )
                
                height_zoom = my_height / float( media_height )
                
                self._current_zoom = min( ( width_zoom, height_zoom ) )
                
            else: self._current_zoom = 1.0
            
        
    
    def _ShouldSkipInputDueToFlash( self ):
        
        if self._current_display_media.GetMime() in ( HC.APPLICATION_FLASH, HC.VIDEO_FLV ):
            
            ( x, y ) = self._media_window.GetPosition()
            ( width, height ) = self._media_window.GetSize()
            
            ( mouse_x, mouse_y ) = self.ScreenToClient( wx.GetMousePosition() )
            
            if mouse_x > x and mouse_x < x + width and mouse_y > y and mouse_y < y + height: return True
            
        
        return False
        
    
    def _SizeAndPositionMediaWindow( self ):
        
        ( new_size, new_position ) = self._GetMediaWindowSizeAndPosition()
        
        if new_size != self._media_window.GetSize(): self._media_window.SetSize( new_size )
        if new_position != self._media_window.GetPosition(): self._media_window.SetPosition( new_position )
        
    
    def EventPaint( self, event ): wx.BufferedPaintDC( self, self._canvas_bmp, wx.BUFFER_VIRTUAL_AREA )
    
    def EventResize( self, event ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        self._canvas_bmp = wx.EmptyBitmap( my_width, my_height, 24 )
        
        if self._media_window is not None:
            
            ( media_width, media_height ) = self._media_window.GetClientSize()
            
            if my_width != media_width or my_height != media_height:
                
                with wx.FrozenWindow( self ):
                    
                    self._RecalcZoom()
                    
                    self._DrawBackgroundBitmap()
                    
                    self._DrawCurrentMedia()
                    
                
            
        else: self._DrawBackgroundBitmap()
        
    
    def KeepCursorAlive( self ): pass
    
    def SetMedia( self, media ):
        
        initial_image = self._current_media == None
        
        if media != self._current_media:
            
            with wx.FrozenWindow( self ):
                
                self._current_media = media
                self._current_display_media = None
                self._total_drag_delta = ( 0, 0 )
                self._last_drag_coordinates = None
                
                if self._media_window is not None:
                    
                    self._media_window.Destroy()
                    self._media_window = None
                    
                
                if self._current_media is not None:
                    
                    self._current_display_media = self._current_media.GetDisplayMedia()
                    
                    if self._current_display_media.GetFileServiceIdentifiersCDPP().HasLocal():
                        
                        self._RecalcZoom()
                        
                        if self._current_display_media.GetMime() in HC.IMAGES:
                            
                            ( initial_size, initial_position ) = self._GetMediaWindowSizeAndPosition()
                            
                            self._media_window = Image( self, self._current_display_media, self._image_cache, initial_size, initial_position )
                            
                        elif self._current_display_media.GetMime() == HC.APPLICATION_FLASH:
                            
                            self._media_window = wx.lib.flashwin.FlashWindow( self )
                            
                            file_hash = self._current_display_media.GetHash()
                            
                            self._media_window.movie = HC.CLIENT_FILES_DIR + os.path.sep + file_hash.encode( 'hex' ) + '.swf'
                            
                        elif self._current_display_media.GetMime() == HC.VIDEO_FLV:
                            
                            self._media_window = wx.lib.flashwin.FlashWindow( self )
                            
                            file_hash = self._current_display_media.GetHash()
                            
                            flash_vars = []
                            flash_vars.append( ( 'flv', HC.CLIENT_FILES_DIR + os.path.sep + file_hash.encode( 'hex' ) + '.flv' ) )
                            flash_vars.append( ( 'margin', '0' ) )
                            flash_vars.append( ( 'autoload', '1' ) )
                            flash_vars.append( ( 'autoplay', '1' ) )
                            flash_vars.append( ( 'showvolume', '1' ) )
                            flash_vars.append( ( 'showtime', '1' ) )
                            flash_vars.append( ( 'loop', '1' ) )
                            
                            f = urllib.urlencode( flash_vars )
                            
                            self._media_window.flashvars = f
                            self._media_window.movie = HC.STATIC_DIR + os.path.sep + 'player_flv_maxi_1.6.0.swf'
                            
                        elif self._current_display_media.GetMime() == HC.APPLICATION_PDF:
                            
                            self._media_window = PDFButton( self, self._current_display_media.GetHash() )
                            
                        
                        if not initial_image: self._PrefetchImages()
                        
                    else: self._current_media = None
                    
                
                self._DrawBackgroundBitmap()
                
                self._DrawCurrentMedia()
                
            
        
class CanvasPanel( Canvas, wx.Window ):
    
    def __init__( self, parent, page_key, file_service_identifier ):
        
        wx.Window.__init__( self, parent, style = wx.SIMPLE_BORDER )
        Canvas.__init__( self, file_service_identifier, wx.GetApp().GetPreviewImageCache() )
        
        self._page_key = page_key
        
        HC.pubsub.sub( self, 'FocusChanged', 'focus_changed' )
        HC.pubsub.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        
        wx.CallAfter( self.Refresh )
        
    
    def FocusChanged( self, page_key, media ):
        
        if page_key == self._page_key: self.SetMedia( media )
        
    
    def ProcessContentUpdates( self, updates ):
        
        if self._current_display_media is not None:
            
            my_hash = self._current_display_media.GetHash()
            
            if True in ( my_hash in update.GetHashes() for update in updates ):
                
                self._DrawBackgroundBitmap()
                
                self._DrawCurrentMedia()
                
            
        
    
class CanvasFullscreenMediaList( ClientGUIMixins.ListeningMediaList, Canvas, ClientGUICommon.Frame ):
    
    def __init__( self, my_parent, page_key, file_service_identifier, predicates, media_results ):
        
        ClientGUICommon.Frame.__init__( self, my_parent, title = 'hydrus client fullscreen image viewer' )
        Canvas.__init__( self, file_service_identifier, wx.GetApp().GetFullscreenImageCache() )
        ClientGUIMixins.ListeningMediaList.__init__( self, file_service_identifier, predicates, media_results )
        
        self._page_key = page_key
        
        self._menu_open = False
        
        self._just_started = True
        
        self.SetIcon( wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO ) )
        
        self.SetCursor( wx.StockCursor( wx.CURSOR_BLANK ) )
        
        if self._options[ 'fullscreen_borderless' ]:
            
            self.ShowFullScreen( True, wx.FULLSCREEN_ALL )
            
        else:
            
            self.Maximize()
            
            self.Show( True )
            
        
        wx.GetApp().SetTopWindow( self )
        
        self._timer_cursor_hide = wx.Timer( self, id = ID_TIMER_CURSOR_HIDE )
        
        self.Bind( wx.EVT_TIMER, self.EventTimerCursorHide, id = ID_TIMER_CURSOR_HIDE )
        
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
        
        if self.IsFullScreen():
            
            self.ShowFullScreen( False )
            
            self.Maximize()
            
        else:
            
            self.ShowFullScreen( True, wx.FULLSCREEN_ALL )
            
        
    
    def _GetCollectionsString( self ):
        
        collections_string = ''
        
        ( creators, series, titles, volumes, chapters, pages ) = self._current_media.GetTags().GetCSTVCP()
        
        if len( creators ) > 0:
            
            collections_string_append = ', '.join( creators )
            
            if len( collections_string ) > 0: collections_string += ' - ' + collections_string_append
            else: collections_string = collections_string_append
            
        
        if len( series ) > 0:
            
            collections_string_append = ', '.join( series )
            
            if len( collections_string ) > 0: collections_string += ' - ' + collections_string_append
            else: collections_string = collections_string_append
            
        
        if len( titles ) > 0:
            
            collections_string_append = ', '.join( titles )
            
            if len( collections_string ) > 0: collections_string += ' - ' + collections_string_append
            else: collections_string = collections_string_append
            
        
        if len( volumes ) > 0:
            
            if len( volumes ) == 1:
                
                ( volume, ) = volumes
                
                collections_string_append = 'volume ' + str( volume )
                
            else: collections_string_append = 'volumes ' + str( min( volumes ) ) + '-' + str( max( volumes ) )
            
            if len( collections_string ) > 0: collections_string += ' - ' + collections_string_append
            else: collections_string = collections_string_append
            
        
        if len( chapters ) > 0:
            
            if len( chapters ) == 1:
                
                ( chapter, ) = chapters
                
                collections_string_append = 'chapter ' + str( chapter )
                
            else: collections_string_append = 'chapters ' + str( min( chapters ) ) + '-' + str( max( chapters ) )
            
            if len( collections_string ) > 0: collections_string += ' - ' + collections_string_append
            else: collections_string = collections_string_append
            
        
        if len( pages ) > 0:
            
            if len( pages ) == 1:
                
                ( page, ) = pages
                
                collections_string_append = 'page ' + str( page )
                
            else: collections_string_append = 'pages ' + str( min( pages ) ) + '-' + str( max( pages ) )
            
            if len( collections_string ) > 0: collections_string += ' - ' + collections_string_append
            else: collections_string = collections_string_append
            
        
        return collections_string
        
    
    def _GetInfoString( self ):
        
        info_string = self._current_media.GetPrettyInfo() + ' ' + HC.ConvertZoomToPercentage( self._current_zoom )
        
        return info_string
        
    
    def _GetIndexString( self ):
        
        index_string = HC.ConvertIntToPrettyString( self._sorted_media_to_indices[ self._current_media ] + 1 ) + os.path.sep + HC.ConvertIntToPrettyString( len( self._sorted_media ) )
        
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
            
            if media.GetMime() in ( HC.IMAGE_JPEG, HC.IMAGE_PNG ):
                
                ( media_width, media_height ) = media.GetResolution()
                
                if media_width > my_width or media_height > my_height:
                    
                    width_zoom = my_width / float( media_width )
                    
                    height_zoom = my_height / float( media_height )
                    
                    zoom = min( ( width_zoom, height_zoom ) )
                    
                else: zoom = 1.0
                
                resolution_to_request = ( int( round( zoom * media_width ) ), int( round( zoom * media_height ) ) )
                
                if not self._image_cache.HasImage( hash, resolution_to_request ): wx.CallLater( delay, self._image_cache.GetImage, hash, resolution_to_request )
                
            
        
    
    def _ShowFirst( self ): self.SetMedia( self._GetFirst() )
    
    def _ShowLast( self ): self.SetMedia( self._GetLast() )
    
    def _ShowNext( self ): self.SetMedia( self._GetNext( self._current_media ) )
    
    def _ShowPrevious( self ): self.SetMedia( self._GetPrevious( self._current_media ) )
    
    def _StartSlideshow( self, interval ): pass
    
    def _ZoomIn( self ):
        
        if self._current_media is not None:
            
            if self._current_media.GetMime() == HC.APPLICATION_PDF: return
            
            for zoom in ZOOMINS:
                
                if self._current_zoom < zoom:
                    
                    if self._current_media.GetMime() in ( HC.APPLICATION_FLASH, HC.VIDEO_FLV ):
                        
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
        
        if self._current_media.GetMime() == HC.APPLICATION_PDF: return
        
        if self._current_media.GetMime() not in ( HC.APPLICATION_FLASH, HC.VIDEO_FLV ) or self._current_zoom > 1.0 or ( media_width < my_width and media_height < my_height ):
            
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
                
            
        
    
    def Archive( self, hashes ):
        
        next_media = self._GetNext( self._current_media )
        
        if next_media == self._current_media: next_media = None
        
        ClientGUIMixins.ListeningMediaList.Archive( self, hashes )
        
        if self.HasNoMedia(): self.EventClose( None )
        elif self.HasMedia( self._current_media ): self._DrawCurrentMedia()
        else: self.SetMedia( next_media )
        
    
    def EventClose( self, event ):
        
        HC.pubsub.pub( 'set_focus', self._page_key, self._current_media )
        
        self.Destroy()
        
    
    def EventDrag( self, event ):
        
        self._focus_holder.SetFocus()
        
        if event.Dragging() and self._last_drag_coordinates is not None:
            
            ( old_x, old_y ) = self._last_drag_coordinates
            
            ( x, y ) = event.GetPosition()
            
            ( delta_x, delta_y ) = ( x - old_x, y - old_y )
            
            try: self.WarpPointer( old_x, old_y )
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
                
                self.WarpPointer( better_x, better_y )
                
                x = better_x
                y = better_y
                
            except: pass
            
        
        self._last_drag_coordinates = ( x, y )
        
        event.Skip()
        
    
    def EventDragEnd( self, event ):
        
        self._last_drag_coordinates = None
        
        event.Skip()
        
    
    def EventTimerCursorHide( self, event ):
        
        if self._menu_open: self._timer_cursor_hide.Start( 800, wx.TIMER_ONE_SHOT )
        else: self.SetCursor( wx.StockCursor( wx.CURSOR_BLANK ) )
        
    
    def KeepCursorAlive( self ): self._timer_cursor_hide.Start( 800, wx.TIMER_ONE_SHOT )
    
    def ProcessContentUpdates( self, updates ):
        
        next_media = self._GetNext( self._current_media )
        
        if next_media == self._current_media: next_media = None
        
        ClientGUIMixins.ListeningMediaList.ProcessContentUpdates( self, updates )
        
        if self.HasNoMedia(): self.EventClose( None )
        elif self.HasMedia( self._current_media ):
            
            self._DrawBackgroundBitmap()
            
            self._DrawCurrentMedia()
            
        else: self.SetMedia( next_media )
        
    
class CanvasFullscreenMediaListBrowser( CanvasFullscreenMediaList ):
    
    def __init__( self, my_parent, page_key, file_service_identifier, predicates, media_results, first_hash ):
        
        CanvasFullscreenMediaList.__init__( self, my_parent, page_key, file_service_identifier, predicates, media_results )
        
        self._timer_slideshow = wx.Timer( self, id = ID_TIMER_SLIDESHOW )
        
        self.Bind( wx.EVT_TIMER, self.EventTimerSlideshow, id = ID_TIMER_SLIDESHOW )
        
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventClose )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventClose )
        self.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
        self.Bind( wx.EVT_RIGHT_UP, self.EventShowMenu )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        if first_hash is None: self.SetMedia( self._GetFirst() )
        else: self.SetMedia( self._GetMedia( { first_hash } )[0] )
        
    
    def _Archive( self ): wx.GetApp().Write( 'content_updates', [ HC.ContentUpdate( HC.CONTENT_UPDATE_ARCHIVE, HC.LOCAL_FILE_SERVICE_IDENTIFIER, ( self._current_media.GetHash(), ) ) ] )
    
    def _CopyLocalUrlToClipboard( self ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject( 'http://127.0.0.1:45865/file?hash=' + self._current_media.GetHash().encode( 'hex' ) )
            
            wx.TheClipboard.SetData( data )
            
            wx.TheClipboard.Close()
            
        else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
        
    
    def _CopyPathToClipboard( self ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject( HC.CLIENT_FILES_DIR + os.path.sep + self._current_media.GetHash().encode( 'hex' ) + HC.mime_ext_lookup[ self._current_media.GetMime() ] )
            
            wx.TheClipboard.SetData( data )
            
            wx.TheClipboard.Close()
            
        else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
        
    
    def _Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Delete this file from the database?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES: wx.GetApp().Write( 'content_updates', [ HC.ContentUpdate( HC.CONTENT_UPDATE_DELETE, HC.LOCAL_FILE_SERVICE_IDENTIFIER, ( self._current_media.GetHash(), ) ) ] )
            
        
        self.SetFocus() # annoying bug because of the modal dialog
        
    
    def _Inbox( self ): wx.GetApp().Write( 'content_updates', [ HC.ContentUpdate( HC.CONTENT_UPDATE_INBOX, HC.LOCAL_FILE_SERVICE_IDENTIFIER, ( self._current_media.GetHash(), ) ) ] )
    
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
        
    
    def EventKeyDown( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            if event.KeyCode in ( wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE ): self._Delete()
            elif event.KeyCode in ( wx.WXK_SPACE, wx.WXK_NUMPAD_SPACE ): self._PausePlaySlideshow()
            elif event.KeyCode in ( ord( '+' ), wx.WXK_ADD, wx.WXK_NUMPAD_ADD ): self._ZoomIn()
            elif event.KeyCode in ( ord( '-' ), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT ): self._ZoomOut()
            elif event.KeyCode == ord( 'Z' ): self._ZoomSwitch()
            elif event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ): self.EventClose( event )
            else:
                
                ( modifier, key ) = HC.GetShortcutFromEvent( event )
                
                key_dict = self._options[ 'shortcuts' ][ modifier ]
                
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
                
                try:
                    
                    ( command, data ) = action
                    
                    if command == 'archive': self._Archive()
                    elif command == 'copy_local_url': self._CopyLocalUrlToClipboard()
                    elif command == 'copy_path': self._CopyPathToClipboard()
                    elif command == 'delete': self._Delete()
                    elif command == 'fullscreen_switch': self._FullscreenSwitch()
                    elif command == 'first': self._ShowFirst()
                    elif command == 'last': self._ShowLast()
                    elif command == 'previous': self._ShowPrevious()
                    elif command == 'next': self._ShowNext()
                    elif command == 'frame_back': self._ChangeFrame( -1 )
                    elif command == 'frame_next': self._ChangeFrame( 1 )
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
                    
                except Exception as e:
                    
                    wx.MessageBox( unicode( e ) )
                    
                
            
        
    
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
        
        services = wx.GetApp().Read( 'services' )
        
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
        
        if self._current_media.GetMime() not in ( HC.APPLICATION_FLASH, HC.VIDEO_FLV, HC.APPLICATION_PDF ):
            
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
        
        menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_path' ) , 'copy path' )
        menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_local_url' ) , 'copy local url' )
        
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
        
        menu.Destroy()
        
        event.Skip()
        
    
    def EventTimerSlideshow( self, event ): self._ShowNext()
    
class CanvasFullscreenMediaListCustomFilter( CanvasFullscreenMediaList ):
    
    def __init__( self, my_parent, page_key, file_service_identifier, predicates, media_results, actions ):
        
        CanvasFullscreenMediaList.__init__( self, my_parent, page_key, file_service_identifier, predicates, media_results )
        
        self._actions = actions
        
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventClose )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventClose )
        self.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
        self.Bind( wx.EVT_RIGHT_UP, self.EventShowMenu )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self.SetMedia( self._GetFirst() )
        
    
    def _Archive( self ): wx.GetApp().Write( 'content_updates', [ HC.ContentUpdate( HC.CONTENT_UPDATE_ARCHIVE, HC.LOCAL_FILE_SERVICE_IDENTIFIER, ( self._current_media.GetHash(), ) ) ] )
    
    def _CopyLocalUrlToClipboard( self ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject( 'http://127.0.0.1:45865/file?hash=' + self._current_media.GetHash().encode( 'hex' ) )
            
            wx.TheClipboard.SetData( data )
            
            wx.TheClipboard.Close()
            
        else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
        
    
    def _CopyPathToClipboard( self ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject( HC.CLIENT_FILES_DIR + os.path.sep + self._current_media.GetHash().encode( 'hex' ) + HC.mime_ext_lookup[ self._current_media.GetMime() ] )
            
            wx.TheClipboard.SetData( data )
            
            wx.TheClipboard.Close()
            
        else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
        
    
    def _Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Delete this file from the database?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES: wx.GetApp().Write( 'content_updates', [ HC.ContentUpdate( HC.CONTENT_UPDATE_DELETE, HC.LOCAL_FILE_SERVICE_IDENTIFIER, ( self._current_media.GetHash(), ) ) ] )
            
        
        self.SetFocus() # annoying bug because of the modal dialog
        
    
    def _Inbox( self ): wx.GetApp().Write( 'content_updates', [ HC.ContentUpdate( HC.CONTENT_UPDATE_INBOX, HC.LOCAL_FILE_SERVICE_IDENTIFIER, ( self._current_media.GetHash(), ) ) ] )
    
    def EventKeyDown( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            ( modifier, key ) = HC.GetShortcutFromEvent( event )
            
            key_dict = self._actions[ modifier ]
            
            if key in key_dict:
                
                ( service_identifier, action ) = key_dict[ key ]
                
                if service_identifier is None:
                    
                    if action == 'archive': self._Archive()
                    elif action == 'delete': self._Delete()
                    elif action == 'frame_back': self._ChangeFrame( -1 )
                    elif action == 'frame_next': self._ChangeFrame( 1 )
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
                        
                        tags = self._current_media.GetTags()
                        
                        ( current, deleted, pending, petitioned ) = tags.GetCDPP( service_identifier )
                        
                        if service_type == HC.LOCAL_TAG:
                            
                            if action in current: edit_log = [ ( HC.CONTENT_UPDATE_DELETE, action ) ]
                            else: edit_log = [ ( HC.CONTENT_UPDATE_ADD, action ) ]
                            
                        else:
                            
                            if action in current:
                                
                                if action in petitioned: edit_log = [ ( HC.CONTENT_UPDATE_RESCIND_PETITION, action ) ]
                                else:
                                    
                                    message = 'Enter a reason for this tag to be removed. A janitor will review your petition.'
                                    
                                    with wx.TextEntryDialog( self, message ) as dlg:
                                        
                                        if dlg.ShowModal() == wx.ID_OK: edit_log = [ ( HC.CONTENT_UPDATE_PETITION, ( action, dlg.GetValue() ) ) ]
                                        else: return
                                        
                                    
                                
                            else:
                                
                                if action in pending: edit_log = [ ( HC.CONTENT_UPDATE_RESCIND_PENDING, action ) ]
                                else: edit_log = [ ( HC.CONTENT_UPDATE_PENDING, action ) ]
                                
                            
                        
                        content_update = HC.ContentUpdate( HC.CONTENT_UPDATE_EDIT_LOG, service_identifier, ( self._current_media.GetHash(), ), info = edit_log )
                        
                    elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                        
                        content_update = HC.ContentUpdate( HC.CONTENT_UPDATE_RATING, service_identifier, ( self._current_media.GetHash(), ), info = action )
                        
                    
                    wx.GetApp().Write( 'content_updates', ( content_update, ) )
                    
                
            else:
                
                if event.KeyCode in ( ord( '+' ), wx.WXK_ADD, wx.WXK_NUMPAD_ADD ): self._ZoomIn()
                elif event.KeyCode in ( ord( '-' ), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT ): self._ZoomOut()
                elif event.KeyCode == ord( 'Z' ): self._ZoomSwitch()
                elif event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ): self.EventClose( event )
                else: event.Skip()
                
            
        
    
    def EventMenu( self, event ):
        
        # is None bit means this is prob from a keydown->menu event
        if event.GetEventObject() is None and self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
            
            if action is not None:
                
                try:
                    
                    ( command, data ) = action
                    
                    if command == 'archive': self._Archive()
                    elif command == 'copy_local_url': self._CopyLocalUrlToClipboard()
                    elif command == 'copy_path': self._CopyPathToClipboard()
                    elif command == 'delete': self._Delete()
                    elif command == 'fullscreen_switch': self._FullscreenSwitch()
                    elif command == 'first': self._ShowFirst()
                    elif command == 'last': self._ShowLast()
                    elif command == 'previous': self._ShowPrevious()
                    elif command == 'next': self._ShowNext()
                    elif command == 'frame_back': self._ChangeFrame( -1 )
                    elif command == 'frame_next': self._ChangeFrame( 1 )
                    elif command == 'inbox': self._Inbox()
                    elif command == 'manage_ratings': self._ManageRatings()
                    elif command == 'manage_tags': self._ManageTags()
                    elif command == 'slideshow': self._StartSlideshow( data )
                    elif command == 'slideshow_pause_play': self._PausePlaySlideshow()
                    elif command == 'zoom_in': self._ZoomIn()
                    elif command == 'zoom_out': self._ZoomOut()
                    elif command == 'zoom_switch': self._ZoomSwitch()
                    else: event.Skip()
                    
                except Exception as e:
                    
                    wx.MessageBox( unicode( e ) )
                    
                
            
        
    
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
        
        if self._current_media.GetMime() not in ( HC.APPLICATION_FLASH, HC.VIDEO_FLV, HC.APPLICATION_PDF ):
            
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
        
        menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_path' ) , 'copy path' )
        menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'copy_local_url' ) , 'copy local url' )
        
        menu.AppendSeparator()
        
        self._menu_open = True
        
        self.PopupMenu( menu )
        
        self._menu_open = False
        
        menu.Destroy()
        
        event.Skip()
        
    
class CanvasFullscreenMediaListFilter( CanvasFullscreenMediaList ):
    
    def __init__( self, my_parent, page_key, file_service_identifier, predicates, media_results ):
        
        CanvasFullscreenMediaList.__init__( self, my_parent, page_key, file_service_identifier, predicates, media_results )
        
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
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self.SetMedia( self._GetFirst() )
        
    
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
                            
                            try:
                                
                                self._deleted_hashes = [ media.GetHash() for media in self._deleted ]
                                self._kept_hashes = [ media.GetHash() for media in self._kept ]
                                
                                content_updates = []
                                
                                content_updates.append( HC.ContentUpdate( HC.CONTENT_UPDATE_DELETE, HC.LOCAL_FILE_SERVICE_IDENTIFIER, self._deleted_hashes ) )
                                content_updates.append( HC.ContentUpdate( HC.CONTENT_UPDATE_ARCHIVE, HC.LOCAL_FILE_SERVICE_IDENTIFIER, self._kept_hashes ) )
                                
                                wx.GetApp().Write( 'content_updates', content_updates )
                                
                                self._kept = set()
                                self._deleted = set()
                                
                            except: wx.MessageBox( traceback.format_exc() )
                            
                        
                        CanvasFullscreenMediaList.EventClose( self, event )
                        
                    
                
            else: CanvasFullscreenMediaList.EventClose( self, event )
            
        
    
    def EventDelete( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            self._deleted.add( self._current_media )
            
            if self._current_media == self._GetLast(): self.EventClose( event )
            else: self._ShowNext()
            
        
    
    def EventKeyDown( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            if event.KeyCode == wx.WXK_SPACE: self._Keep()
            elif event.KeyCode in ( ord( '+' ), wx.WXK_ADD, wx.WXK_NUMPAD_ADD ): self._ZoomIn()
            elif event.KeyCode in ( ord( '-' ), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT ): self._ZoomOut()
            elif event.KeyCode == ord( 'Z' ): self._ZoomSwitch()
            elif event.KeyCode == wx.WXK_BACK: self.EventBack( event )
            elif event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ): self.EventClose( event )
            elif event.KeyCode in ( wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE ): self.EventDelete( event )
            elif not event.ShiftDown() and event.KeyCode in ( wx.WXK_UP, wx.WXK_NUMPAD_UP ): self.EventSkip( event )
            else:
                
                ( modifier, key ) = HC.GetShortcutFromEvent( event )
                
                key_dict = self._options[ 'shortcuts' ][ modifier ]
                
                if key in key_dict:
                    
                    action = key_dict[ key ]
                    
                    self.ProcessEvent( wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) )
                    
                else: event.Skip()
                
            
        
    
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
                
                try:
                    
                    ( command, data ) = action
                    
                    if command == 'archive': self._Keep()
                    elif command == 'back': self.EventBack( event )
                    elif command == 'close': self.EventClose( event )
                    elif command == 'delete': self.EventDelete( event )
                    elif command == 'fullscreen_switch': self._FullscreenSwitch()
                    elif command == 'filter': self.EventClose( event )
                    elif command == 'frame_back': self._ChangeFrame( -1 )
                    elif command == 'frame_next': self._ChangeFrame( 1 )
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
                    
                except Exception as e:
                    
                    wx.MessageBox( unicode( e ) )
                    
                
            
        
    
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
            
        
    
class RatingsFilterFrameLike( CanvasFullscreenMediaListFilter ):
    
    def __init__( self, my_parent, page_key, service_identifier, media_results ):
        
        CanvasFullscreenMediaListFilter.__init__( self, my_parent, page_key, HC.LOCAL_FILE_SERVICE_IDENTIFIER, [], media_results )
        
        self._rating_service_identifier = service_identifier
        self._service = wx.GetApp().Read( 'service', service_identifier )
        
    
    def EventClose( self, event ):
        
        if self._ShouldSkipInputDueToFlash(): event.Skip()
        else:
            
            if len( self._kept ) > 0 or len( self._deleted ) > 0:
                
                ( like, dislike ) = self._service.GetExtraInfo()
                
                with ClientGUIDialogs.DialogFinishFiltering( self, len( self._kept ), len( self._deleted ), keep = like, delete = dislike ) as dlg:
                    
                    modal = dlg.ShowModal()
                    
                    if modal == wx.ID_CANCEL:
                        
                        if self._current_media in self._kept: self._kept.remove( self._current_media )
                        if self._current_media in self._deleted: self._deleted.remove( self._current_media )
                        
                    else:
                        
                        if modal == wx.ID_YES:
                            
                            try:
                                
                                self._deleted_hashes = [ media.GetHash() for media in self._deleted ]
                                self._kept_hashes = [ media.GetHash() for media in self._kept ]
                                
                                content_updates = []
                                
                                content_updates.extend( [ HC.ContentUpdate( HC.CONTENT_UPDATE_RATING, self._rating_service_identifier, ( hash, ), info = 0.0 ) for hash in self._deleted_hashes ] )
                                content_updates.extend( [ HC.ContentUpdate( HC.CONTENT_UPDATE_RATING, self._rating_service_identifier, ( hash, ), info = 1.0 ) for hash in self._kept_hashes ] )
                                
                                wx.GetApp().Write( 'content_updates', content_updates )
                                
                                self._kept = set()
                                self._deleted = set()
                                
                            except: wx.MessageBox( traceback.format_exc() )
                            
                        
                        CanvasFullscreenMediaList.EventClose( self, event )
                        
                    
                
            else: CanvasFullscreenMediaList.EventClose( self, event )
            
        
    
class RatingsFilterFrameNumerical( ClientGUICommon.Frame ):
    
    RATINGS_FILTER_INEQUALITY_FULL = 0
    RATINGS_FILTER_INEQUALITY_HALF = 1
    RATINGS_FILTER_INEQUALITY_QUARTER = 2
    
    RATINGS_FILTER_EQUALITY_FULL = 0
    RATINGS_FILTER_EQUALITY_HALF = 1
    RATINGS_FILTER_EQUALITY_QUARTER = 2
    
    def __init__( self, parent, page_key, service_identifier, media_results ):
        
        ClientGUICommon.Frame.__init__( self, parent, title = 'hydrus client ratings frame' )
        
        self._page_key = page_key
        self._service_identifier = service_identifier
        self._media_still_to_rate = { ClientGUIMixins.MediaSingleton( media_result ) for media_result in media_results }
        
        self._file_query_result = CC.FileQueryResult( HC.LOCAL_FILE_SERVICE_IDENTIFIER, [], media_results )
        
        if service_identifier.GetType() == HC.LOCAL_RATING_LIKE: self._score_gap = 1.0
        else:
            
            self._service = wx.GetApp().Read( 'service', service_identifier )
            
            ( self._lower, self._upper ) = self._service.GetExtraInfo()
            
            self._score_gap = 1.0 / ( self._upper - self._lower )
            
        
        hashes_to_min_max = wx.GetApp().Read( 'ratings_filter', service_identifier, [ media_result.GetHash() for media_result in media_results ] )
        
        self._media_to_initial_scores_dict = { media : hashes_to_min_max[ media.GetHash() ] for media in self._media_still_to_rate }
        
        self._decision_log = []
        
        self._ReinitialiseCurrentScores()
        
        self._inequal_accuracy = self.RATINGS_FILTER_INEQUALITY_FULL
        self._equal_accuracy = self.RATINGS_FILTER_EQUALITY_FULL
        
        # panel
        
        if service_identifier.GetType() == HC.LOCAL_RATING_NUMERICAL:
            
            top_panel = wx.Panel( self )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            if 'ratings_filter_accuracy' not in self._options:
                
                self._options[ 'ratings_filter_accuracy' ] = 1
                
                wx.GetApp().Write( 'save_options' )
                
            
            value = self._options[ 'ratings_filter_accuracy' ]
            
            self._accuracy_slider = wx.Slider( top_panel, value = value, minValue = 0, maxValue = 4 )
            self._accuracy_slider.Bind( wx.EVT_SLIDER, self.EventSlider )
            
            self.EventSlider( None )
            
            hbox.AddF( wx.StaticText( top_panel, label = 'quick' ), FLAGS_MIXED )
            hbox.AddF( self._accuracy_slider, FLAGS_EXPAND_BOTH_WAYS )
            hbox.AddF( wx.StaticText( top_panel, label = 'accurate' ), FLAGS_MIXED )
            
            top_panel.SetSizer( hbox )
            
        
        # end panel
        
        self._statusbar = self.CreateStatusBar()
        self._statusbar.SetFieldsCount( 3 )
        self._statusbar.SetStatusWidths( [ -1, 500, -1 ] )
        
        self._splitter = wx.SplitterWindow( self )
        self._splitter.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        if service_identifier.GetType() == HC.LOCAL_RATING_NUMERICAL: vbox.AddF( top_panel, FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._splitter, FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self._splitter.SetMinimumPaneSize( 120 )
        self._splitter.SetSashGravity( 0.5 ) # stay in the middle
        
        if True: # if borderless fullscreen
            
            self.ShowFullScreen( True, wx.FULLSCREEN_ALL ^ wx.FULLSCREEN_NOSTATUSBAR )
            
        else:
            
            self.Maximize()
            
            self.Show( True )
            
        
        wx.GetApp().SetTopWindow( self )
        
        self._left_window = self._Panel( self._splitter )
        self._right_window = self._Panel( self._splitter )
        
        ( my_width, my_height ) = self.GetClientSize()
        
        self._splitter.SplitVertically( self._left_window, self._right_window, my_width / 2 )
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        self.Bind( wx.EVT_LEFT_DOWN, self.EventMouseDown )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventMouseDown )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.Bind( wx.EVT_CLOSE, self.EventClose )
        
        self._ShowNewMedia()
        
        HC.pubsub.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HC.pubsub.sub( self, 'ProcessServiceUpdate', 'service_update_gui' )
        
        HC.pubsub.pub( 'set_focus', self._page_key, None )
        
    
    def _FullscreenSwitch( self ):
        
        if self.IsFullScreen():
            
            self.ShowFullScreen( False )
            
            self.Maximize()
            
        else:
            
            self.ShowFullScreen( True, wx.FULLSCREEN_ALL )
            
        
    
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
                
            
            center_string = str( len( self._media_to_initial_scores_dict ) ) + ' files being rated. after ' + str( len( self._decision_log ) ) + ' decisions, ' + str( len( certain_ratings ) ) + ' are certain'
            
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
                
            
            center_string = str( len( self._media_to_initial_scores_dict ) ) + ' files being rated. after ' + str( len( self._decision_log ) ) + ' decisions, ' + str( len( certain_ratings ) ) + ' are certain and ' + str( len( uncertain_ratings ) ) + ' are uncertain'
            
        
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
        
        ( self._current_media_to_rate, ) = random.sample( self._media_still_to_rate, 1 )
        
        ( min, max ) = self._media_to_current_scores_dict[ self._current_media_to_rate ]
        
        media_result_to_rate_against = wx.GetApp().Read( 'ratings_media_result', self._service_identifier, min, max )
        
        if media_result_to_rate_against is not None:
            
            hash = media_result_to_rate_against.GetHash()
            
            if hash in self._file_query_result.GetHashes(): media_result_to_rate_against = self._file_query_result.GetMediaResult( hash )
            else: self._file_query_result.AddMediaResult( media_result_to_rate_against )
            
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
            
            if random.randint( 0, 1 ) == 0:
                
                self._unrated_is_on_the_left = True
                
                self._left_window.SetMedia( self._current_media_to_rate )
                self._right_window.SetMedia( self._current_media_to_rate_against )
                
            else:
                
                self._unrated_is_on_the_left = False
                
                self._left_window.SetMedia( self._current_media_to_rate_against )
                self._right_window.SetMedia( self._current_media_to_rate )
                
            
            self._RefreshStatusBar()
            
        
    
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
        
    
    def EventClose( self, event ):
        
        if len( self._decision_log ) > 0:
            
            def normalise_rating( rating ): return round( rating / self._score_gap ) * self._score_gap
            
            certain_ratings = [ ( media.GetHash(), normalise_rating( ( min + max ) / 2 ) ) for ( media, ( min, max ) ) in self._media_to_current_scores_dict.items() if max - min < self._score_gap ]
            uncertain_ratings = [ ( media.GetHash(), min, max ) for ( media, ( min, max ) ) in self._media_to_current_scores_dict.items() if max - min >= self._score_gap and self._media_to_current_scores_dict[ media ] != self._media_to_initial_scores_dict[ media ] ]
            
            with ClientGUIDialogs.DialogFinishRatingFiltering( self, len( certain_ratings ), len( uncertain_ratings ) ) as dlg:
                
                modal = dlg.ShowModal()
                
                if modal == wx.ID_CANCEL:
                    
                    self._ShowNewMedia()
                    
                    return
                    
                elif modal == wx.ID_YES:
                    
                    try:
                        
                        content_updates = []
                        
                        content_updates.extend( [ HC.ContentUpdate( HC.CONTENT_UPDATE_RATING, self._service_identifier, ( hash, ), info = rating ) for ( hash, rating ) in certain_ratings ] )
                        content_updates.extend( [ HC.ContentUpdate( HC.CONTENT_UPDATE_RATINGS_FILTER, self._service_identifier, ( hash, ), info = ( min, max ) ) for ( hash, min, max ) in uncertain_ratings ] )
                        
                        wx.GetApp().Write( 'content_updates', content_updates )
                        
                    except: wx.MessageBox( traceback.format_exc() )
                    
                
            
        
        HC.pubsub.pub( 'set_focus', self._page_key, self._current_media_to_rate )
        
        self.Destroy()
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in ( wx.WXK_SPACE, wx.WXK_UP, wx.WXK_NUMPAD_UP ): self._ShowNewMedia()
        elif event.KeyCode in ( wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN ): self._ProcessAction( 'equal' )
        elif event.KeyCode in ( wx.WXK_LEFT, wx.WXK_NUMPAD_LEFT ): self._ProcessAction( 'left' )
        elif event.KeyCode in ( wx.WXK_RIGHT, wx.WXK_NUMPAD_RIGHT ): self._ProcessAction( 'right' )
        elif event.KeyCode == wx.WXK_BACK: self._GoBack()
        elif event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ): self.EventClose( event )
        else: event.Skip()
        
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            try:
                
                ( command, data ) = action
                
                if command == 'fullscreen_switch': self._FullscreenSwitch()
                else: event.Skip()
                
            except Exception as e:
                
                wx.MessageBox( unicode( e ) )
                
            
        
    
    def EventMouseDown( self, event ):
        
        if event.ButtonDown( wx.MOUSE_BTN_LEFT ): self._ProcessAction( 'left' )
        elif event.ButtonDown( wx.MOUSE_BTN_RIGHT ): self._ProcessAction( 'right' )
        elif event.ButtonDown( wx.MOUSE_BTN_MIDDLE ): self._ProcessAction( 'equal' )
        
    
    def EventSlider( self, event ):
        
        value = self._accuracy_slider.GetValue()
        
        if value == 0: self._equal_accuracy = self.RATINGS_FILTER_EQUALITY_FULL
        elif value <= 2: self._equal_accuracy = self.RATINGS_FILTER_EQUALITY_HALF
        else: self._equal_accuracy = self.RATINGS_FILTER_EQUALITY_QUARTER
        
        if value <= 1: self._inequal_accuracy = self.RATINGS_FILTER_INEQUALITY_FULL
        elif value <= 3: self._inequal_accuracy = self.RATINGS_FILTER_INEQUALITY_HALF
        else: self._inequal_accuracy = self.RATINGS_FILTER_INEQUALITY_QUARTER
        
        self._options[ 'ratings_filter_accuracy' ] = value
        
        wx.GetApp().Write( 'save_options' )
        
    
    def ProcessContentUpdates( self, content_updates ):
        
        redraw = False
        
        my_hashes = self._file_query_result.GetHashes()
        
        for content_update in content_updates:
            
            content_update_hashes = content_update.GetHashes()
            
            if len( my_hashes.intersection( content_update_hashes ) ) > 0:
                
                redraw = True
                
                break
                
            
        
        if redraw:
            
            self._left_window.RefreshBackground()
            self._right_window.RefreshBackground()
            
        
    
    def ProcessServiceUpdate( self, update ):
        
        self._left_window.RefreshBackground()
        self._right_window.RefreshBackground()
        
    
    class _Panel( Canvas, wx.Window ):
        
        def __init__( self, parent ):
            
            wx.Window.__init__( self, parent, style = wx.SIMPLE_BORDER | wx.WANTS_CHARS )
            Canvas.__init__( self, HC.LOCAL_FILE_SERVICE_IDENTIFIER, wx.GetApp().GetFullscreenImageCache() )
            
            wx.CallAfter( self.Refresh )
            
            self.Bind( wx.EVT_MOTION, self.EventDrag )
            self.Bind( wx.EVT_LEFT_DOWN, self.EventDragBegin )
            self.Bind( wx.EVT_RIGHT_DOWN, self.GetParent().GetParent().EventMouseDown )
            self.Bind( wx.EVT_MIDDLE_DOWN, self.GetParent().GetParent().EventMouseDown )
            self.Bind( wx.EVT_LEFT_UP, self.EventDragEnd )
            self.Bind( wx.EVT_MOUSEWHEEL, self.EventMouseWheel )
            self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
            
            self._timer_cursor_hide = wx.Timer( self, id = ID_TIMER_CURSOR_HIDE )
            
            self.Bind( wx.EVT_TIMER, self.EventTimerCursorHide, id = ID_TIMER_CURSOR_HIDE )
            
            self.Bind( wx.EVT_MENU, self.EventMenu )
            
        
        def _ZoomIn( self ):
            
            if self._current_media is not None:
                
                if self._current_media.GetMime() == HC.APPLICATION_PDF: return
                
                for zoom in ZOOMINS:
                    
                    if self._current_zoom < zoom:
                        
                        if self._current_media.GetMime() in ( HC.APPLICATION_FLASH, HC.VIDEO_FLV ):
                            
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
            
            if self._current_media.GetMime() == HC.APPLICATION_PDF: return
            
            if self._current_media.GetMime() not in ( HC.APPLICATION_FLASH, HC.VIDEO_FLV ) or self._current_zoom > 1.0 or ( media_width < my_width and media_height < my_height ):
                
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
            
            if wx.Window.FindFocus() != self: self.SetFocus()
            
            if event.Dragging() and self._last_drag_coordinates is not None:
                
                ( old_x, old_y ) = self._last_drag_coordinates
                
                ( x, y ) = event.GetPosition()
                
                ( delta_x, delta_y ) = ( x - old_x, y - old_y )
                
                try: self.WarpPointer( old_x, old_y )
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
                        
                        self.WarpPointer( better_x, better_y )
                        
                        x = better_x
                        y = better_y
                        
                    except: pass
                    
                
                self._last_drag_coordinates = ( x, y )
                
            else: self.GetParent().GetParent().ProcessEvent( event )
            
        
        def EventDragEnd( self, event ):
            
            self._last_drag_coordinates = None
            
            event.Skip()
            
        
        def EventKeyDown( self, event ):
            
            if self._ShouldSkipInputDueToFlash(): event.Skip()
            else:
                
                keys_i_want_to_bump_up_regardless = [ wx.WXK_SPACE, wx.WXK_UP, wx.WXK_NUMPAD_UP, wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN, wx.WXK_LEFT, wx.WXK_NUMPAD_LEFT, wx.WXK_RIGHT, wx.WXK_NUMPAD_RIGHT, wx.WXK_BACK, wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE ]
                
                ( modifier, key ) = HC.GetShortcutFromEvent( event )
                
                key_dict = self._options[ 'shortcuts' ][ modifier ]
                
                if event.KeyCode not in keys_i_want_to_bump_up_regardless and key in key_dict:
                    
                    action = key_dict[ key ]
                    
                    self.ProcessEvent( wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) )
                    
                else:
                    
                    if event.KeyCode in ( ord( '+' ), wx.WXK_ADD, wx.WXK_NUMPAD_ADD ): self._ZoomIn()
                    elif event.KeyCode in ( ord( '-' ), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT ): self._ZoomOut()
                    elif event.KeyCode == ord( 'Z' ): self._ZoomSwitch()
                    else: self.GetParent().ProcessEvent( event )
                    
            
        
        def EventMenu( self, event ):
            
            if self._ShouldSkipInputDueToFlash(): event.Skip()
            else:
                
                action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
                
                if action is not None:
                    
                    try:
                        
                        ( command, data ) = action
                        
                        if command == 'frame_back': self._ChangeFrame( -1 )
                        elif command == 'frame_next': self._ChangeFrame( 1 )
                        elif command == 'manage_ratings': self._ManageRatings()
                        elif command == 'manage_tags': self._ManageTags()
                        elif command == 'zoom_in': self._ZoomIn()
                        elif command == 'zoom_out': self._ZoomOut()
                        else: event.Skip()
                        
                    except Exception as e:
                        
                        wx.MessageBox( unicode( e ) )
                        
                    
                
            
        
        def EventMouseWheel( self, event ):
            
            if self._ShouldSkipInputDueToFlash(): event.Skip()
            else:
                
                if event.CmdDown():
                    
                    if event.GetWheelRotation() > 0: self._ZoomIn()
                    else: self._ZoomOut()
                    
                
            
        
        def EventTimerCursorHide( self, event ): self.SetCursor( wx.StockCursor( wx.CURSOR_BLANK ) )
        
        def RefreshBackground( self ): self._DrawBackgroundBitmap()
        
    
class Image( wx.Window ):
    
    def __init__( self, parent, media, image_cache, initial_size, initial_position ):
        
        wx.Window.__init__( self, parent, size = initial_size, pos = initial_position )
        
        self.SetDoubleBuffered( True )
        
        self._media = media
        self._image_container = None
        self._image_cache = image_cache
        
        self._current_frame_index = 0
        
        ( width, height ) = initial_size
        
        self._canvas_bmp = wx.EmptyBitmap( 0, 0, 24 )
        
        self._timer_animated = wx.Timer( self, id = ID_TIMER_ANIMATED )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_TIMER, self.EventTimerAnimated, id = ID_TIMER_ANIMATED )
        self.Bind( wx.EVT_MOUSE_EVENTS, self.PropagateMouseEvent )
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self.EventResize( None )
        
    
    def _Draw( self ):
        
        dc = wx.BufferedDC( wx.ClientDC( self ), self._canvas_bmp )
        
        if self._image_container.HasFrame( self._current_frame_index ):
            
            current_frame = self._image_container.GetFrame( self._current_frame_index )
            
            ( my_width, my_height ) = self._canvas_bmp.GetSize()
            
            if self._media.GetMime() == HC.IMAGE_GIF and self._media.HasDuration():
                image_width = my_width
                image_height = my_height - ANIMATED_SCANBAR_HEIGHT
            else:
                image_width = my_width
                image_height = my_height
            
            ( frame_width, frame_height ) = current_frame.GetSize()
            
            x_scale = image_width / float( frame_width )
            y_scale = image_height / float( frame_height )
            
            dc.SetUserScale( x_scale, y_scale )
            
            hydrus_bmp = current_frame.CreateWxBmp()
            
            dc.DrawBitmap( hydrus_bmp, 0, 0 )
            
            hydrus_bmp.Destroy()
            
            dc.SetUserScale( 1.0, 1.0 )
            
            if self._image_container.IsAnimated(): self._timer_animated.Start( self._image_container.GetDuration( self._current_frame_index ), wx.TIMER_ONE_SHOT )
            
        else:
            
            dc.SetBackground( wx.Brush( wx.WHITE ) )
            
            dc.Clear()
            
            self._timer_animated.Start( 50, wx.TIMER_ONE_SHOT )
            
        
        if self._media.GetMime() == HC.IMAGE_GIF and self._media.HasDuration():
            
            ( my_width, my_height ) = self.GetClientSize()
            
            zero_y = my_height - ANIMATED_SCANBAR_HEIGHT
            
            num_frames = self._media.GetNumFrames()
            
            dc.SetPen( wx.TRANSPARENT_PEN )
            
            dc.SetBrush( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) ) )
            
            dc.DrawRectangle( 0, zero_y, my_width, ANIMATED_SCANBAR_HEIGHT )
            
            dc.SetBrush( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_SCROLLBAR ) ) )
            
            dc.DrawRectangle( int( float( my_width - ANIMATED_SCANBAR_CARET_WIDTH ) * float( self._current_frame_index ) / float( num_frames - 1 ) ), zero_y, ANIMATED_SCANBAR_CARET_WIDTH, ANIMATED_SCANBAR_HEIGHT )
            
        
    
    def ChangeFrame( self, direction ):
        
        num_frames = self._media.GetNumFrames()
        
        if direction == 1:
            
            if self._current_frame_index == num_frames - 1: self._current_frame_index = 0
            else: self._current_frame_index += 1
            
        else:
            
            if self._current_frame_index == 0: self._current_frame_index = num_frames - 1
            else: self._current_frame_index -= 1
            
        
        self._Draw()
        
        self._timer_animated.Stop()
        
    
    def PropagateMouseEvent( self, event ):
        
        if self._media.GetMime() == HC.IMAGE_GIF and self._media.HasDuration():
            
            ( my_width, my_height ) = self.GetClientSize()
            
            ( x, y ) = event.GetPosition()
            
            if y > my_height - ANIMATED_SCANBAR_HEIGHT:
                
                if event.Dragging() or event.ButtonDown():
                    
                    num_frames = self._media.GetNumFrames()
                    
                    compensated_x_position = x - ( ANIMATED_SCANBAR_CARET_WIDTH / 2 )
                    
                    proportion = float( compensated_x_position ) / float( my_width - ANIMATED_SCANBAR_CARET_WIDTH )
                    
                    if proportion < 0: proportion = 0
                    if proportion > 1: proportion = 1
                    
                    self._current_frame_index = int( proportion * ( num_frames - 1 ) + 0.5 )
                    
                    self._Draw()
                    
                    if event.Dragging(): self._timer_animated.Stop()
                    
                    self.GetParent().KeepCursorAlive()
                    
                    return
                    
                
            
        
        screen_position = self.ClientToScreen( event.GetPosition() )
        ( x, y ) = self.GetParent().ScreenToClient( screen_position )
        
        event.SetX( x )
        event.SetY( y )
        
        event.ResumePropagation( 1 )
        event.Skip()
        
    
    def EventKeyDown( self, event ):
        
        self.GetParent().ProcessEvent( event )
        
    
    def EventPaint( self, event ): wx.BufferedPaintDC( self, self._canvas_bmp )
    
    def EventResize( self, event ):
        
        ( my_width, my_height ) = self.GetClientSize()
        
        ( current_bmp_width, current_bmp_height ) = self._canvas_bmp.GetSize()
        
        if my_width != current_bmp_width or my_height != current_bmp_height:
            
            if my_width > 0 and my_height > 0:
                
                if self._image_container is None:
                    
                    if self._media.GetMime() == HC.IMAGE_GIF and self._media.HasDuration():
                        image_width = my_width
                        image_height = my_height - ANIMATED_SCANBAR_HEIGHT
                    else:
                        image_width = my_width
                        image_height = my_height
                    
                    self._image_container = self._image_cache.GetImage( self._media.GetHash(), ( image_width, image_height ) )
                    
                else:
                    
                    ( image_width, image_height ) = self._image_container.GetSize()
                    
                    we_just_zoomed_in = my_width > image_width
                    
                    if we_just_zoomed_in and self._image_container.IsScaled():
                        
                        full_resolution = self._image_container.GetResolution()
                        
                        self._image_container = self._image_cache.GetImage( self._media.GetHash(), full_resolution )
                        
                    
                
                self._canvas_bmp = wx.EmptyBitmap( my_width, my_height, 24 )
                
                self._Draw()
                
            
        
    
    def EventTimerAnimated( self, event ):
        
        if self.IsShown():
            
            if self._image_container.HasFrame( self._current_frame_index + 1 ): self._current_frame_index += 1
            elif self._image_container.IsFinishedRendering(): self._current_frame_index = 0
            
            self._Draw()
            
        
    
class PDFButton( wx.Button ):
    
    def __init__( self, parent, hash ):
        
        wx.Button.__init__( self, parent, label = 'launch pdf' )
        
        self._hash = hash
        
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        
    
    def EventButton( self, event ):
        
        path = HC.CLIENT_FILES_DIR + os.path.sep + self._hash.encode( 'hex' ) + '.pdf'
        
        # os.system( 'start ' + path )
        subprocess.call( 'start "" "' + path + '"', shell = True )
        
    
class Text( wx.Window ):
    
    def __init__( self, parent, place, background_colour = wx.WHITE ):
        
        wx.Window.__init__( self, parent )
        
        self._place = place
        self._background_colour = background_colour
        
        self._current_text = ''
        self._canvas_bmp = wx.EmptyBitmap( 0, 0, 24 )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        
        self._can_show = False
        
        self.Hide()
        
    
    def EventPaint( self, event ): wx.BufferedPaintDC( self, self._canvas_bmp )
    
    def SetText( self, text ):
        
        ( my_width, my_height ) = self._canvas_bmp.GetSize()
        
        if text != self._current_text:
            
            self._current_text = text
            
            dc = wx.BufferedDC( wx.ClientDC( self ), self._canvas_bmp )
            
            dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
            
            ( x, y ) = dc.GetTextExtent( self._current_text )
            
            x += 2
            y += 2
            
            if x != my_width or y != my_height:
                
                del dc
                
                self._canvas_bmp = wx.EmptyBitmap( x, y, 24 )
                
                dc = wx.BufferedDC( wx.ClientDC( self ), self._canvas_bmp )
                
                dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
                
                ( my_width, my_height ) = ( x, y )
                
            
            dc.SetBackground( wx.Brush( self._background_colour ) )
            
            dc.Clear()
            
            dc.DrawText( self._current_text, 1, 1 )
            
        
        parent = self.GetParent()
        
        ( parent_width, parent_height ) = parent.GetClientSize()
        
        if self._place == 'top':
            
            pos_x = ( parent_width / 2 ) - ( my_width / 2 )
            pos_y = 0
            
        elif self._place == 'bottom_left':
            
            pos_x = 0
            pos_y = parent_height - my_height 
            
        elif self._place == 'bottom_right':
            
            pos_x = parent_width - my_width
            pos_y = parent_height - my_height
            
        
        self.SetSize( ( my_width, my_height ) )
        self.SetPosition( ( pos_x, pos_y ) )
        
        self._can_show = self._current_text != ''
        
    
    def ShowIfPossible( self ):
        
        if self._can_show: self.Show()
        else: self.Hide()
        
    