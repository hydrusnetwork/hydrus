import os
import threading
import time

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusCompression
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusImageHandling
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusVideoHandling

from hydrus.client import ClientFiles
from hydrus.client import ClientImageHandling
from hydrus.client import ClientVideoHandling

def FrameIndexOutOfRange( index, range_start, range_end ):
    
    before_start = index < range_start
    after_end = range_end < index
    
    if range_start < range_end:
        
        if before_start or after_end:
            
            return True
            
        
    else:
        
        if after_end and before_start:
            
            return True
            
        
    
    return False
    
def GenerateHydrusBitmap( path, mime, compressed = True ):
    
    numpy_image = ClientImageHandling.GenerateNumPyImage( path, mime )
    
    return GenerateHydrusBitmapFromNumPyImage( numpy_image, compressed = compressed )
    
def GenerateHydrusBitmapFromNumPyImage( numpy_image, compressed = True ):
    
    ( y, x, depth ) = numpy_image.shape
    
    return HydrusBitmap( numpy_image.data, ( x, y ), depth, compressed = compressed )
    
def GenerateHydrusBitmapFromPILImage( pil_image, compressed = True ):
    
    if pil_image.mode == 'RGBA':
        
        depth = 4
        
    elif pil_image.mode == 'RGB':
        
        depth = 3
        
    
    return HydrusBitmap( pil_image.tobytes(), pil_image.size, depth, compressed = compressed )
    
class ImageRenderer( object ):
    
    def __init__( self, media, this_is_for_metadata_alone = False ):
        
        self._numpy_image = None
        
        self._hash = media.GetHash()
        self._mime = media.GetMime()
        
        self._num_frames = media.GetNumFrames()
        self._resolution = media.GetResolution()
        
        self._icc_profile_bytes = None
        self._qt_colourspace = None
        
        self._path = None
        
        self._this_is_for_metadata_alone = this_is_for_metadata_alone
        
        HG.client_controller.CallToThread( self._Initialise )
        
    
    def _GetNumPyImage( self, clip_rect: QC.QRect, target_resolution: QC.QSize ):
        
        clip_size = clip_rect.size()
        clip_width = clip_size.width()
        clip_height = clip_size.height()
        
        ( my_width, my_height ) = self._resolution
        
        my_full_rect = QC.QRect( 0, 0, my_width, my_height )
        
        ZERO_MARGIN = QC.QMargins( 0, 0, 0, 0 )
        
        clip_padding = ZERO_MARGIN
        target_padding = ZERO_MARGIN
        
        if clip_rect == my_full_rect:
            
            # full image
            
            source = self._numpy_image
            
        else:
            
            if target_resolution.width() > clip_width:
                
                # this is a tile that is being scaled up!
                # to reduce tiling artifacts (disagreement at otherwise good borders), we want to oversample the clip for our tile so lanczos and friends can get good neighbour data and then crop it
                # therefore, we'll figure out some padding for the clip, and then calculate what that means in the target end, and do a crop at the end
                
                # we want to pad. that means getting a larger resolution and keeping a record of the padding
                # can't pad if we are at 0 for x or y, or up against width/height max, but no problem in that case obviously
                
                # there is the float-int precision calculation problem again. we can't pick a padding of 3 in the clip if we are zooming by 150%--what do we clip off in the target: 4 or 5 pixels? whatever, we get warping
                # first let's figure a decent zoom estimate:
                
                zoom_estimate = target_resolution.width() / clip_width if target_resolution.width() > target_resolution.height() else target_resolution.height() / clip_height
                
                # now, if zoom is 150% (as a fraction, 3/2), we want a padding at the target of something that divides by 3 cleanly, or, since we are choosing at the clip in this case and will be multiplying, something that divides cleanly to 67%
                
                zoom_estimate_for_clip_padding_multiplier = 1 / zoom_estimate
                
                # and we want a nice padding size limit, big enough to make clean numbers but not so big that we are rendering the 8 tiles in a square around the one we want
                no_bigger_than = max( 4, ( clip_width + clip_height ) // 4 )
                
                nice_number = HydrusData.GetNicelyDivisibleNumberForZoom( zoom_estimate_for_clip_padding_multiplier, no_bigger_than )
                
                if nice_number != -1:
                    
                    # lanczos, I think, uses 4x4 neighbour grid to render. we'll say padding of 4 pixels to be safe for now, although 2 or 3 is probably correct???
                    # however it works, numbers these small are not a big deal
                    
                    while nice_number < 4:
                        
                        nice_number *= 2
                        
                    
                    PADDING_AMOUNT = nice_number
                    
                    # LIMITATION: There is still a problem here for the bottom and rightmost edges. These tiles are not squares, so the shorter/thinner dimension my be an unpleasant number and be warped _anyway_, regardless of nice padding
                    # perhaps there is a way to boost left or top padding so we are rendering a full square tile but still cropping our target at the end, but with a little less warping
                    # I played around with this idea but did not have much success
                    
                    LEFT_PADDING_AMOUNT = PADDING_AMOUNT
                    TOP_PADDING_AMOUNT = PADDING_AMOUNT
                    
                    left_padding = min( LEFT_PADDING_AMOUNT, clip_rect.x() )
                    top_padding = min( TOP_PADDING_AMOUNT, clip_rect.y() )
                    right_padding = min( PADDING_AMOUNT, ( my_width - 1 ) - clip_rect.bottomRight().x() )
                    bottom_padding = min( PADDING_AMOUNT, ( my_height - 1 ) - clip_rect.bottomRight().y() )
                    
                    clip_padding = QC.QMargins( left_padding, top_padding, right_padding, bottom_padding )
                    
                    target_padding = clip_padding * zoom_estimate
                    
                
            
            clip_rect_with_padding = clip_rect + clip_padding
            
            ( x, y, clip_width, clip_height ) = ( clip_rect_with_padding.x(), clip_rect_with_padding.y(), clip_rect_with_padding.width(), clip_rect_with_padding.height() )
            
            source = self._numpy_image[ y : y + clip_height, x : x + clip_width ]
            
        
        if target_resolution == clip_size:
            
            # 100% zoom
            
            result = source
            
        else:
            
            if clip_padding == ZERO_MARGIN:
                
                result = ClientImageHandling.ResizeNumPyImageForMediaViewer( self._mime, source, ( target_resolution.width(), target_resolution.height() ) )
                
            else:
                
                target_width_with_padding = target_resolution.width() + target_padding.left() + target_padding.right()
                target_height_with_padding = target_resolution.height() + target_padding.top() + target_padding.bottom()
                
                result = ClientImageHandling.ResizeNumPyImageForMediaViewer( self._mime, source, ( target_width_with_padding, target_height_with_padding ) )
                
                y = target_padding.top()
                x = target_padding.left()
                
                result = result[ y : y + target_resolution.height(), x : x + target_resolution.width() ]
                
            
        
        if not result.data.c_contiguous:
            
            result = result.copy()
            
        
        return result
        
    
    def _Initialise( self ):
        
        # do this here so we are off the main thread and can wait
        client_files_manager = HG.client_controller.client_files_manager
        
        self._path = client_files_manager.GetFilePath( self._hash, self._mime )
        
        self._numpy_image = ClientImageHandling.GenerateNumPyImage( self._path, self._mime )
        
        if not self._this_is_for_metadata_alone:
            
            my_resolution_size = QC.QSize( self._resolution[0], self._resolution[1] )
            my_numpy_size = QC.QSize( self._numpy_image.shape[1], self._numpy_image.shape[0] )
            
            if my_resolution_size != my_numpy_size:
                
                HG.client_controller.Write( 'file_maintenance_add_jobs_hashes', { self._hash }, ClientFiles.REGENERATE_FILE_DATA_JOB_FILE_METADATA )
                
                m = 'There was a problem rendering the image with hash {}! Hydrus thinks its resolution is {}, but it was actually {}. Maybe hydrus missed rotation data when the file first imported?'.format(
                    self._hash.hex(),
                    my_resolution_size,
                    my_numpy_size
                )
                
                m += os.linesep * 2
                m += 'You may see some black squares in the image. A metadata regeneration has been scheduled, so with luck the image will fix itself soon.'
                
                HydrusData.ShowText( m )
                
            
        
    
    def GetEstimatedMemoryFootprint( self ):
        
        if self._numpy_image is None:
            
            ( width, height ) = self._resolution
            
            return width * height * 3
            
        else:
            
            return self._numpy_image.nbytes
            
        
    
    def GetHash( self ): return self._hash
    
    def GetNumFrames( self ): return self._num_frames
    
    def GetResolution( self ): return self._resolution
    
    def GetQtImage( self, clip_rect = None, target_resolution = None ):
        
        if clip_rect is None:
            
            ( width, height ) = self._resolution
            
            clip_rect = QC.QRect( QC.QPoint( 0, 0 ), QC.QSize( width, height ) )
            
        
        if target_resolution is None:
            
            target_resolution = clip_rect.size()
            
        
        numpy_image = self._GetNumPyImage( clip_rect, target_resolution )
        
        ( height, width, depth ) = numpy_image.shape
        
        data = numpy_image.data
        
        qt_image = HG.client_controller.bitmap_manager.GetQtImageFromBuffer( width, height, depth * 8, data )
        
        # ok this stuff was originally for image ICC, as loaded using PIL's image.info dict
        # ultimately I figured out how to do the conversion with PIL itself, which was more universal
        # however if we end up pulling display ICC or taking user-set ICC, we may want this qt code somewhere
        
        if self._icc_profile_bytes is not None:
            
            try:
                
                if self._qt_colourspace is None:
                    
                    self._qt_colourspace = QG.QColorSpace.fromIccProfile( self._icc_profile_bytes )
                    
                
                # originally this was converting image ICC to sRGB, but I think in the 'display' sense, we'd be setting sRGB and then converting to the user-set ICC
                # 'hey, Qt, this QImage is in sRGB (I already normalised it), now convert it to xxx, thanks!'
                
                qt_image.setColorSpace( self._qt_colourspace )
                qt_image.convertToColorSpace( QG.QColorSpace.SRgb )
                
            except:
                
                HydrusData.Print( 'Failed to load the ICC Profile for {} into a Qt Colourspace!'.format( self._path ) )
                
                self._icc_profile_bytes = None
                
            
        
        return qt_image
        
    
    def GetQtPixmap( self, clip_rect = None, target_resolution = None ):
        
        # colourspace conversions seem to be exclusively QImage territory
        if self._icc_profile_bytes is not None:
            
            qt_image = self.GetQtImage( clip_rect = clip_rect, target_resolution = target_resolution )
            
            return QG.QPixmap.fromImage( qt_image )
            
        
        ( my_width, my_height ) = self._resolution
        
        if clip_rect is None:
            
            clip_rect = QC.QRect( QC.QPoint( 0, 0 ), QC.QSize( my_width, my_height ) )
            
        
        if target_resolution is None:
            
            target_resolution = clip_rect.size()
            
        
        my_full_rect = QC.QRect( 0, 0, my_width, my_height )
        
        if my_full_rect.contains( clip_rect ):
            
            try:
                
                numpy_image = self._GetNumPyImage( clip_rect, target_resolution )
                
                ( height, width, depth ) = numpy_image.shape
                
                data = numpy_image.data
                
                return HG.client_controller.bitmap_manager.GetQtPixmapFromBuffer( width, height, depth * 8, data )
                
            except Exception as e:
                
                HydrusData.PrintException( e, do_wait = False )
                
            
        
        HydrusData.Print( 'Failed to produce a tile! Info is: {}, {}, {}, {}'.format( self._hash.hex(), ( my_width, my_height ), clip_rect, target_resolution ) )
        
        pixmap = QG.QPixmap( target_resolution )
        
        pixmap.fill( QC.Qt.black )
        
        return pixmap
        
    
    def IsReady( self ):
        
        return self._numpy_image is not None
        
    
class ImageTile( object ):
    
    def __init__( self, hash: bytes, clip_rect: QC.QRect, qt_pixmap: QG.QPixmap ):
        
        self.hash = hash
        self.clip_rect = clip_rect
        self.qt_pixmap = qt_pixmap
        
        self._num_bytes = self.qt_pixmap.width() * self.qt_pixmap.height() * 3
        
    
    def GetEstimatedMemoryFootprint( self ):
        
        return self._num_bytes
        
    
class RasterContainer( object ):
    
    def __init__( self, media, target_resolution = None ):
        
        if target_resolution is None: target_resolution = media.GetResolution()
        
        ( width, height ) = target_resolution
        
        if width == 0 or height == 0:
            
            target_resolution = ( 100, 100 )
            
        
        self._media = media
        
        ( media_width, media_height ) = self._media.GetResolution()
        ( target_width, target_height ) = target_resolution
        
        if target_width > media_width or target_height > media_height:
            
            target_resolution = self._media.GetResolution()
            
        
        self._target_resolution = target_resolution
        
        ( target_width, target_height ) = target_resolution
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        
        client_files_manager = HG.client_controller.client_files_manager
        
        self._path = client_files_manager.GetFilePath( hash, mime )
        
        width_zoom = target_width / media_width
        height_zoom = target_height / media_height
        
        self._zoom = min( ( width_zoom, height_zoom ) )
        
        if self._zoom > 1.0:
            
            self._zoom = 1.0
            
        
    
class RasterContainerVideo( RasterContainer ):
    
    def __init__( self, media, target_resolution = None, init_position = 0 ):
        
        RasterContainer.__init__( self, media, target_resolution )
        
        self._init_position = init_position
        
        self._initialised = False
        
        self._renderer = None
        
        self._frames = {}
        
        self._buffer_start_index = -1
        self._buffer_end_index = -1
        
        self._times_to_play_gif = 0
        
        self._stop = False
        
        self._render_event = threading.Event()
        
        ( x, y ) = self._target_resolution
        
        new_options = HG.client_controller.new_options
        
        video_buffer_size_mb = new_options.GetInteger( 'video_buffer_size_mb' )
        
        duration = self._media.GetDuration()
        num_frames_in_video = self._media.GetNumFrames()
        
        if duration is None or duration == 0:
            
            message = 'The file with hash ' + media.GetHash().hex() + ', had an invalid duration.'
            message += os.linesep * 2
            message += 'You may wish to try regenerating its metadata through the advanced mode right-click menu.'
            
            HydrusData.ShowText( message )
            
            duration = 1.0
            
        
        if num_frames_in_video is None or num_frames_in_video == 0:
            
            message = 'The file with hash ' + media.GetHash().hex() + ', had an invalid number of frames.'
            message += os.linesep * 2
            message += 'You may wish to try regenerating its metadata through the advanced mode right-click menu.'
            
            HydrusData.ShowText( message )
            
            num_frames_in_video = 1
            
        
        self._average_frame_duration = duration / num_frames_in_video
        
        frame_buffer_length = ( video_buffer_size_mb * 1024 * 1024 ) // ( x * y * 3 )
        
        # if we can't buffer the whole vid, then don't have a clunky massive buffer
        
        max_streaming_buffer_size = max( 48, int( num_frames_in_video / ( duration / 3.0 ) ) ) # 48 or 3 seconds
        
        if max_streaming_buffer_size < frame_buffer_length and frame_buffer_length < num_frames_in_video:
            
            frame_buffer_length = max_streaming_buffer_size
            
        
        self._num_frames_backwards = frame_buffer_length * 2 // 3
        self._num_frames_forwards = frame_buffer_length // 3
        
        self._lock = threading.Lock()
        
        self._last_index_rendered = -1
        self._next_render_index = -1
        self._rendered_first_frame = False
        self._ideal_next_frame = 0
        
        HG.client_controller.CallToThread( self.THREADRender )
        
    
    def _HasFrame( self, index ):
        
        return index in self._frames
        
    
    def _IndexInRange( self, index, range_start, range_end ):
        
        return not FrameIndexOutOfRange( index, range_start, range_end )
        
    
    def _MaintainBuffer( self ):
        
        deletees = [ index for index in list(self._frames.keys()) if FrameIndexOutOfRange( index, self._buffer_start_index, self._buffer_end_index ) ]
        
        for i in deletees:
            
            del self._frames[ i ]
            
        
    
    def THREADRender( self ):
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        duration = self._media.GetDuration()
        num_frames_in_video = self._media.GetNumFrames()
        
        client_files_manager = HG.client_controller.client_files_manager
        
        time.sleep( 0.00001 )
        
        if self._media.GetMime() == HC.IMAGE_GIF:
            
            ( self._durations, self._times_to_play_gif ) = HydrusImageHandling.GetGIFFrameDurations( self._path )
            
            self._renderer = ClientVideoHandling.GIFRenderer( self._path, num_frames_in_video, self._target_resolution )
            
        else:
            
            self._renderer = HydrusVideoHandling.VideoRendererFFMPEG( self._path, mime, duration, num_frames_in_video, self._target_resolution )
            
        
        # give ui a chance to draw a blank frame rather than hard-charge right into CPUland
        time.sleep( 0.00001 )
        
        self.GetReadyForFrame( self._init_position )
        
        with self._lock:
            
            self._initialised = True
            
        
        while True:
            
            if self._stop or HG.view_shutdown:
                
                self._renderer.Stop()
                
                self._renderer = None
                
                with self._lock:
                    
                    self._frames = {}
                    
                
                return
                
            
            #
            
            with self._lock:
                
                # lets see if we should move the renderer to a new position
                
                next_render_is_out_of_buffer = FrameIndexOutOfRange( self._next_render_index, self._buffer_start_index, self._buffer_end_index )
                buffer_not_fully_rendered = self._last_index_rendered != self._buffer_end_index
                
                currently_rendering_out_of_buffer = next_render_is_out_of_buffer and buffer_not_fully_rendered
                
                will_render_ideal_frame_soon = self._IndexInRange( self._next_render_index, self._buffer_start_index, self._ideal_next_frame )
                
                need_ideal_next_frame = not self._HasFrame( self._ideal_next_frame )
                
                will_not_get_to_ideal_frame = need_ideal_next_frame and not will_render_ideal_frame_soon
                
                if currently_rendering_out_of_buffer or will_not_get_to_ideal_frame:
                    
                    # we cannot get to the ideal next frame, so we need to rewind/reposition
                    
                    self._renderer.set_position( self._buffer_start_index )
                    
                    self._last_index_rendered = -1
                    
                    self._next_render_index = self._buffer_start_index
                    
                
                #
                
                need_to_render = self._last_index_rendered != self._buffer_end_index
                
            
            if need_to_render:
                
                with self._lock:
                    
                    self._rendered_first_frame = True
                    
                    frame_index = self._next_render_index # keep this before the get call, as it increments in a clock arithmetic way afterwards
                    
                    renderer = self._renderer
                    
                
                try:
                    
                    numpy_image = renderer.read_frame()
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                finally:
                    
                    with self._lock:
                        
                        self._last_index_rendered = frame_index
                        
                        self._next_render_index = ( self._next_render_index + 1 ) % num_frames_in_video
                        
                    
                
                with self._lock:
                    
                    if self._next_render_index == 0 and self._buffer_end_index != num_frames_in_video - 1:
                        
                        # we need to rewind renderer
                        
                        self._renderer.set_position( 0 )
                        
                        self._last_index_rendered = -1
                        
                    
                    should_save_frame = not self._HasFrame( frame_index )
                    
                
                if should_save_frame:
                    
                    frame = GenerateHydrusBitmapFromNumPyImage( numpy_image, compressed = False )
                    
                    with self._lock:
                        
                        self._frames[ frame_index ] = frame
                        
                        self._MaintainBuffer()
                        
                    
                
                with self._lock:
                    
                    work_still_to_do = self._last_index_rendered != self._buffer_end_index
                    
                
                if work_still_to_do:
                    
                    time.sleep( 0.0001 )
                    
                else:
                    
                    half_a_frame = ( self._average_frame_duration / 1000.0 ) * 0.5
                    
                    sleep_duration = min( 0.1, half_a_frame ) # for 10s-long 3-frame gifs, wew
                    
                    time.sleep( sleep_duration ) # just so we don't spam cpu
                    
                
            else:
                
                self._render_event.wait( 1 )
                
                self._render_event.clear()
                
            
        
    
    def GetBufferIndices( self ):
        
        if self._last_index_rendered == -1:
            
            return None
            
        else:
            
            return ( self._buffer_start_index, self._last_index_rendered, self._buffer_end_index )
            
        
    
    def GetDuration( self, index ):
        
        if self._media.GetMime() == HC.IMAGE_GIF:
            
            return self._durations[ index ]
            
        else:
            
            return self._average_frame_duration
            
        
    
    def GetFrame( self, index ):
        
        with self._lock:
            
            frame = self._frames[ index ]
            
        
        num_frames_in_video = self.GetNumFrames()
        
        if index == num_frames_in_video - 1:
            
            next_index = 0
            
        else:
            
            next_index = index + 1
            
        
        self.GetReadyForFrame( next_index )
        
        return frame
        
    
    def GetHash( self ):
        
        return self._media.GetHash()
        
    
    def GetKey( self ):
        
        return ( self._media.GetHash(), self._target_resolution )
        
    
    def GetNumFrames( self ):
        
        return self._media.GetNumFrames()
        
    
    def GetReadyForFrame( self, next_index_to_expect ):
        
        num_frames_in_video = self.GetNumFrames()
        
        frame_request_is_impossible = FrameIndexOutOfRange( next_index_to_expect, 0, num_frames_in_video - 1 )
        
        if frame_request_is_impossible:
            
            return
            
        
        with self._lock:
            
            self._ideal_next_frame = next_index_to_expect
            
            video_is_bigger_than_buffer = num_frames_in_video > self._num_frames_backwards + 1 + self._num_frames_forwards
            
            if video_is_bigger_than_buffer:
                
                current_ideal_is_out_of_buffer = self._buffer_start_index == -1 or FrameIndexOutOfRange( self._ideal_next_frame, self._buffer_start_index, self._buffer_end_index )
                
                ideal_buffer_start_index = max( 0, self._ideal_next_frame - self._num_frames_backwards )
                
                ideal_buffer_end_index = ( self._ideal_next_frame + self._num_frames_forwards ) % num_frames_in_video
                
                if current_ideal_is_out_of_buffer:
                    
                    # the current buffer won't get to where we want, so remake it
                    
                    self._buffer_start_index = ideal_buffer_start_index
                    self._buffer_end_index = ideal_buffer_end_index
                    
                else:
                    
                    # we can get to our desired position, but should we move the start and beginning on a bit?
                    
                    # we do not ever want to shunt left (rewind)
                    # we do not want to shunt right if we don't have the earliest frames yet--be patient
                    
                    # i.e. it is between the current start and the ideal
                    next_ideal_start_would_shunt_right = self._IndexInRange( ideal_buffer_start_index, self._buffer_start_index, self._ideal_next_frame )
                    have_next_ideal_start = self._HasFrame( ideal_buffer_start_index )
                    
                    if next_ideal_start_would_shunt_right and have_next_ideal_start:
                        
                        self._buffer_start_index = ideal_buffer_start_index
                        
                    
                    next_ideal_end_would_shunt_right = self._IndexInRange( ideal_buffer_end_index, self._buffer_end_index, self._buffer_start_index )
                    
                    if next_ideal_end_would_shunt_right:
                    
                        self._buffer_end_index = ideal_buffer_end_index
                        
                
            else:
                
                self._buffer_start_index = 0
                
                self._buffer_end_index = num_frames_in_video - 1
                
            
        
        self._render_event.set()
        
    
    def GetResolution( self ):
        
        return self._media.GetResolution()
        
    
    def GetSize( self ):
        
        return self._target_resolution
        
    
    def GetTimesToPlayGIF( self ):
        
        return self._times_to_play_gif
        
    
    def GetFrameIndex( self, timestamp_ms ):
        
        if self._media.GetMime() == HC.IMAGE_GIF:
            
            so_far = 0
            
            for ( frame_index, duration_ms ) in enumerate( self._durations ):
                
                so_far += duration_ms
                
                if so_far > timestamp_ms:
                    
                    result = frame_index
                    
                    if FrameIndexOutOfRange( result, 0, self.GetNumFrames() - 1 ):
                        
                        return 0
                        
                    else:
                        
                        return result
                        
                    
                
            
            return 0
            
        else:
            
            return timestamp_ms // self._average_frame_duration
            
        
    
    def GetTimestampMS( self, frame_index ):
        
        if self._media.GetMime() == HC.IMAGE_GIF:
            
            return sum( self._durations[ : frame_index ] )
            
        else:
            
            return self._average_frame_duration * frame_index
            
        
    
    def GetTotalDuration( self ):
        
        if self._media.GetMime() == HC.IMAGE_GIF:
            
            return sum( self._durations )
            
        else:
            
            return self._average_frame_duration * self.GetNumFrames()
            
        
    
    def HasFrame( self, index ):
        
        with self._lock:
            
            return self._HasFrame( index )
            
        
    
    def CanHaveVariableFramerate( self ):
        
        with self._lock:
            
            return self._media.GetMime() == HC.IMAGE_GIF
            
        
    
    def IsInitialised( self ):
        
        with self._lock:
            
            return self._initialised
            
        
    
    def IsScaled( self ):
        
        return self._zoom != 1.0
        
    
    def Stop( self ):
        
        self._stop = True
        
    
class HydrusBitmap( object ):
    
    def __init__( self, data, size, depth, compressed = True ):
        
        self._compressed = compressed
        
        if isinstance( data, memoryview ) and not data.c_contiguous:
            
            data = data.copy()
            
        
        if self._compressed:
            
            self._data = HydrusCompression.CompressFastBytesToBytes( data )
            
        else:
            
            self._data = data
            
        
        self._size = size
        self._depth = depth
        
    
    def _GetData( self ):
        
        if self._compressed:
            
            return HydrusCompression.DecompressFastBytesToBytes( self._data )
            
        else:
            
            return self._data
            
        
    
    def _GetQtImageFormat( self ):
        
        if self._depth == 3:
            
            return QG.QImage.Format_RGB888
            
        elif self._depth == 4:
            
            return QG.QImage.Format_RGBA8888
            
        
    
    def GetDepth( self ):
        
        return self._depth
        
    
    def GetQtImage( self ):
        
        ( width, height ) = self._size
        
        return HG.client_controller.bitmap_manager.GetQtImageFromBuffer( width, height, self._depth * 8, self._GetData() )
        
    
    def GetQtPixmap( self ):
        
        ( width, height ) = self._size
        
        return HG.client_controller.bitmap_manager.GetQtPixmapFromBuffer( width, height, self._depth * 8, self._GetData() )
        
    
    def GetEstimatedMemoryFootprint( self ):
        
        return len( self._data )
        
    
    def GetSize( self ):
        
        return self._size
        
    
