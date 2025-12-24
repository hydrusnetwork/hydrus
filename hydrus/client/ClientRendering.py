import numpy
import threading
import time

from qtpy import QtCore as QC
from qtpy import QtGui as QG

from hydrus.core import HydrusCompression
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusAnimationHandling
from hydrus.core.files import HydrusVideoHandling
from hydrus.core.files.images import HydrusImageHandling

from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientVideoHandling
from hydrus.client.caches import ClientCachesBase
from hydrus.client.files import ClientFilesMaintenance
from hydrus.client.files.images import ClientImageHandling
from hydrus.client.media import ClientMedia
from hydrus.client import ClientUgoiraHandling

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
    
    numpy_image = HydrusImageHandling.GenerateNumPyImage( path, mime )
    
    return GenerateHydrusBitmapFromNumPyImage( numpy_image, compressed = compressed )
    

def GenerateHydrusBitmapFromNumPyImage( numpy_image, compressed = True ):
    
    ( y, x, depth ) = numpy_image.shape
    
    return HydrusBitmap( numpy_image.data, ( x, y ), depth, compressed = compressed )
    
def GenerateHydrusBitmapFromPILImage( pil_image, compressed = True ):
    
    depth = 3
    
    if pil_image.mode == 'RGBA':
        
        depth = 4
        
    elif pil_image.mode == 'RGB':
        
        depth = 3
        
    
    try:
        
        return HydrusBitmap( pil_image.tobytes(), pil_image.size, depth, compressed = compressed )
        
    except IOError:
        
        raise HydrusExceptions.DamagedOrUnusualFileException( 'Looks like a truncated file that PIL could not handle!' )
        
    

class ImageRenderer( ClientCachesBase.CacheableObject ):
    
    def __init__( self, media, this_is_for_metadata_alone = False ):
        
        super().__init__()
        
        self._numpy_image = None
        self._render_failed = False
        self._is_ready = False
        
        self._hash = media.GetHash()
        self._mime = media.GetMime()
        
        self._num_frames = media.GetNumFrames()
        self._resolution = media.GetResolution()
        
        if None in self._resolution:
            
            self._resolution = ( 100, 100 )
            
        
        self._icc_profile_bytes = None
        self._qt_colourspace = None
        
        self._path = None
        
        self._this_is_for_metadata_alone = this_is_for_metadata_alone
        
        CG.client_controller.CallToThread( self._Initialise )
        

    def GetNumPyImage(self):

        return self._numpy_image
        
    
    def _GetNumPyImage( self, clip_rect: QC.QRect, target_resolution: QC.QSize ):
        
        if self._numpy_image is None:
            
            return numpy.zeros( ( target_resolution.height(), target_resolution.width() ), dtype = 'uint8' )
            
        
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
        client_files_manager = CG.client_controller.client_files_manager
        
        try:
            
            self._path = client_files_manager.GetFilePath( self._hash, self._mime )
            
            self._numpy_image = HydrusImageHandling.GenerateNumPyImage( self._path, self._mime )
            
        except HydrusExceptions.NoRenderFileException as e:
            
            self._numpy_image = self._InitialiseErrorImage( e, mention_log = False )
            
            self._render_failed = True
            
        except Exception as e:
            
            self._numpy_image = self._InitialiseErrorImage( e )
            
            self._render_failed = True
            
            HydrusData.Print( 'Problem rendering image at "{}"! Error follows:'.format( self._path ) )
            
            HydrusData.PrintException( e, do_wait = False )
            
        
        self._is_ready = True
        
        CG.client_controller.pub( 'notify_image_finished_rendering' )
        
        if not self._this_is_for_metadata_alone:
            
            # TODO: Move this error code to a nice button or something
            # old recovery code, before the ErrorImage
            # I think move to show a nice 'check integrity' button when a file errors, so the user can kick it off, and we avoid the popup spam
            '''
            m += '\n' * 2
            m += 'Jobs to check its integrity and metadata have been scheduled. If it is damaged, it may be redownloaded or removed from the client completely. If it is not damaged, it may be fixed automatically or further action may be required.'
            
            HydrusData.ShowText( m )
            
            CG.client_controller.Write( 'file_maintenance_add_jobs_hashes', { self._hash }, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_INTEGRITY_DATA_TRY_URL_ELSE_REMOVE_RECORD )
            CG.client_controller.Write( 'file_maintenance_add_jobs_hashes', { self._hash }, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_METADATA )
            '''
            
            if not self._render_failed:
                
                my_expected_size = ( self._resolution[0], self._resolution[1] )
                my_numpy_size = ( self._numpy_image.shape[1], self._numpy_image.shape[0] )
                
                expectation_rotated = ( self._resolution[1], self._resolution[0] )
                
                hash_hex = self._hash.hex()
                
                if my_expected_size != my_numpy_size:
                    
                    if my_numpy_size == expectation_rotated:
                        
                        m = f'There was a problem rendering the image with hash {hash_hex}! Hydrus thought its resolution would be {my_expected_size}, but it looks like we rendered it to the rotated value of {my_numpy_size}. This happens sometimes with weirder rotation metadata where support changes over time.'
                        
                    else:
                        
                        m = f'There was a problem rendering the image with hash {hash_hex}! Hydrus thought its resolution would be {my_expected_size}, but it actually rendered to {my_numpy_size}. This is an odd situation.'
                        
                    
                    m += '\n' * 2
                    m += 'You may see some black squares in the image. A metadata regeneration has been scheduled, so with luck it will fix itself soon. If the file is still broken, hydev would like to see it!'
                    
                    HydrusData.ShowText( m )
                    
                    CG.client_controller.Write( 'file_maintenance_add_jobs_hashes', { self._hash }, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_METADATA )
                    
                
            
        
    
    def _InitialiseErrorImage( self, e: Exception, mention_log = True ):
        
        ( width, height ) = self._resolution
        
        qt_image = QG.QImage( width, height, QG.QImage.Format.Format_RGB888 )
        
        painter = QG.QPainter( qt_image )
        
        painter.setBackground( QG.QBrush( QC.Qt.GlobalColor.white ) )
        
        painter.eraseRect( painter.viewport() )
        
        pen = QG.QPen( QG.QColor( 20, 20, 20 ) )
        
        pen.setWidth( 5 )
        
        painter.setPen( pen )
        painter.setBrush( QC.Qt.BrushStyle.NoBrush )
        
        painter.drawRect( 0, 0, width - 1, height - 1 )
        
        from hydrus.client.gui import ClientGUIFunctions
        
        font = painter.font()
        
        font.setPixelSize( height // 20 )
        
        painter.setFont( font )
        
        text = 'Image failed to render:'
        text += '\n'
        text += str( e )
        
        if mention_log:
            
            text += '\n'
            text += 'Full info written to the log.'
            
        
        painter.drawText( QC.QRectF( 0, 0, width, height ), QC.Qt.AlignmentFlag.AlignCenter, text )
        
        del painter
        
        return ClientGUIFunctions.ConvertQtImageToNumPy( qt_image )
        
    
    def GetEstimatedMemoryFootprint( self ):
        
        if self._numpy_image is None:
            
            ( width, height ) = self._resolution
            
            return width * height * 3
            
        else:
            
            return self._numpy_image.nbytes
            
        
    
    def GetHash( self ): return self._hash
    
    def GetNumFrames( self ): return self._num_frames
    
    def GetResolution( self ): return self._resolution
    
    def GetQtImage( self, clip_rect: QC.QRect | None = None, target_resolution: QC.QSize | None = None ):
        
        if clip_rect is None:
            
            ( width, height ) = self._resolution
            
            clip_rect = QC.QRect( QC.QPoint( 0, 0 ), QC.QSize( width, height ) )
            
        
        if target_resolution is None:
            
            target_resolution = clip_rect.size()
            
        
        numpy_image = self._GetNumPyImage( clip_rect, target_resolution )
        
        ( height, width, depth ) = numpy_image.shape
        
        data = numpy_image.data
        
        qt_image = CG.client_controller.bitmap_manager.GetQtImageFromBuffer( width, height, depth * 8, data )
        
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
                qt_image.convertToColorSpace( QG.QColorSpace.NamedColorSpace.SRgb )
                
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
                
                return CG.client_controller.bitmap_manager.GetQtPixmapFromBuffer( width, height, depth * 8, data )
                
            except Exception as e:
                
                HydrusData.PrintException( e, do_wait = False )
                
            
        
        HydrusData.Print( 'Failed to produce a tile! Info is: {}, {}, {}, {}'.format( self._hash.hex(), ( my_width, my_height ), clip_rect, target_resolution ) )
        
        pixmap = QG.QPixmap( target_resolution )
        
        pixmap.fill( QC.Qt.GlobalColor.black )
        
        return pixmap
        
    
    def IsFinishedLoading( self ):
        
        return self._is_ready
        
    
    def IsReady( self ):
        
        return self._is_ready
        
    
    def RenderFailed( self ):
        
        return self._render_failed
        
    

class ImageTile( ClientCachesBase.CacheableObject ):
    
    def __init__( self, hash: bytes, clip_rect: QC.QRect, qt_pixmap: QG.QPixmap ):
        
        super().__init__()
        
        self.hash = hash
        self.clip_rect = clip_rect
        self.qt_pixmap = qt_pixmap
        
        self._num_bytes = self.qt_pixmap.width() * self.qt_pixmap.height() * 3
        
    
    def GetEstimatedMemoryFootprint( self ):
        
        return self._num_bytes
        
    
    def IsFinishedLoading( self ):
        
        return True
        
    

class RasterContainer( object ):
    
    def __init__( self, media: ClientMedia.MediaSingleton, target_resolution = None ):
        
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
        
        client_files_manager = CG.client_controller.client_files_manager
        
        self._path = client_files_manager.GetFilePath( hash, mime )
        
        width_zoom = target_width / media_width
        height_zoom = target_height / media_height
        
        self._zoom = min( ( width_zoom, height_zoom ) )
        
        if self._zoom > 1.0:
            
            self._zoom = 1.0
            
        
    
class RasterContainerVideo( RasterContainer ):
    
    def __init__( self, media: ClientMedia.MediaSingleton, target_resolution = None, init_position = 0, frame_durations_ms = None ):
        
        super().__init__( media, target_resolution )
        
        self._init_position = init_position
        
        self._initialised = False
        
        self._renderer = None
        
        self._frames = {}
        self._frame_durations_ms = []
        
        self._buffer_start_index = -1
        self._buffer_end_index = -1
        
        self._times_to_play_animation = 0
        
        self._stop = False
        
        self._render_event = threading.Event()
        
        ( x, y ) = self._target_resolution
        
        new_options = CG.client_controller.new_options
        
        video_buffer_size = new_options.GetInteger( 'video_buffer_size' )
        
        duration_ms = self._media.GetDurationMS()
        num_frames_in_video = self._media.GetNumFrames()
        
        if frame_durations_ms is not None:
            
            self._frame_durations_ms = frame_durations_ms
            
            if duration_ms is None:
                
                duration_ms = sum( frame_durations_ms )
                
            
        
        if duration_ms is None or duration_ms == 0:
            
            message = 'The file with hash ' + media.GetHash().hex() + ', had an invalid duration.'
            message += '\n' * 2
            message += 'You may wish to try regenerating its metadata through the advanced mode right-click menu.'
            
            HydrusData.ShowText( message )
            
            duration_ms = 1000
            
        
        if num_frames_in_video is None or num_frames_in_video == 0:
            
            message = 'The file with hash ' + media.GetHash().hex() + ', had an invalid number of frames.'
            message += '\n' * 2
            message += 'You may wish to try regenerating its metadata through the advanced mode right-click menu.'
            
            HydrusData.ShowText( message )
            
            num_frames_in_video = 1
            
        
        self._average_frame_duration_ms = duration_ms / num_frames_in_video
        
        frame_buffer_length = video_buffer_size // ( x * y * 3 )
        
        # if we can't buffer the whole vid, then don't have a clunky massive buffer that's like 80% of the vid
        
        max_streaming_buffer_size = max( 48, int( 3000 / self._average_frame_duration_ms ) ) # 48 or 3 seconds
        
        if max_streaming_buffer_size < frame_buffer_length < num_frames_in_video:
            
            frame_buffer_length = max_streaming_buffer_size
            
        
        self._num_frames_backwards = frame_buffer_length * 2 // 3
        self._num_frames_forwards = frame_buffer_length // 3
        
        self._lock = threading.Lock()
        
        self._last_index_rendered = -1
        self._next_render_index = -1
        self._rendered_first_frame = False
        self._ideal_next_frame = 0
        
        CG.client_controller.CallToThread( self.THREADRender )
        
    
    def __del__( self ):
        
        self.Stop()
        
    
    def _HasFrame( self, index ):
        
        return index in self._frames
        
    
    def _IndexInRange( self, index, range_start, range_end ):
        
        return not FrameIndexOutOfRange( index, range_start, range_end )
        
    
    def _MaintainBuffer( self ):
        
        deletees = [ index for index in list(self._frames.keys()) if FrameIndexOutOfRange( index, self._buffer_start_index, self._buffer_end_index ) ]
        
        for i in deletees:
            
            del self._frames[ i ]
            
        
    
    def CanHaveVariableFramerate( self ):
        
        return self._media.GetMime() in ( HC.ANIMATION_GIF, HC.ANIMATION_UGOIRA, HC.ANIMATION_WEBP )
        
    
    def GetBufferIndices( self ):
        
        if self._last_index_rendered == -1:
            
            return None
            
        else:
            
            return ( self._buffer_start_index, self._last_index_rendered, self._buffer_end_index )
            
        
    
    def GetDurationMS( self, index ):
        
        if self.CanHaveVariableFramerate():
            
            if 0 <= index <= len( self._frame_durations_ms ) - 1:
                
                return self._frame_durations_ms[ index ]
                
            
        
        return self._average_frame_duration_ms
        
    
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
        
    
    def GetTimesToPlayAnimation( self ):
        
        return self._times_to_play_animation
        
    
    def GetFrameIndex( self, timestamp_ms ):
        
        if self.CanHaveVariableFramerate():
            
            so_far = 0
            
            for ( frame_index, duration_ms ) in enumerate( self._frame_durations_ms ):
                
                so_far += duration_ms
                
                if so_far > timestamp_ms:
                    
                    result = frame_index
                    
                    if FrameIndexOutOfRange( result, 0, self.GetNumFrames() - 1 ):
                        
                        return 0
                        
                    else:
                        
                        return result
                        
                    
                
            
            return 0
            
        else:
            
            return timestamp_ms // self._average_frame_duration_ms
            
        
    
    def GetTimestampMS( self, frame_index ):
        
        if self.CanHaveVariableFramerate():
            
            return sum( self._frame_durations_ms[ : frame_index ] )
            
        else:
            
            return self._average_frame_duration_ms * frame_index
            
        
    
    def GetTotalDuration( self ):
        
        if self.CanHaveVariableFramerate():
            
            return sum( self._frame_durations_ms )
            
        else:
            
            return self._average_frame_duration_ms * self.GetNumFrames()
            
        
    
    def HasFrame( self, index ):
        
        with self._lock:
            
            return self._HasFrame( index )
            
        
    
    def IsInitialised( self ):
        
        with self._lock:
            
            return self._initialised
            
        
    
    def IsScaled( self ):
        
        return self._zoom != 1.0
        
    
    def Stop( self ):
        
        self._stop = True
        
    
    def THREADRender( self ):
        
        mime = self._media.GetMime()
        duration_ms = self._media.GetDurationMS()
        num_frames_in_video = self._media.GetNumFrames()
        
        time.sleep( 0.00001 )
        
        if self._media.GetMime() == HC.ANIMATION_APNG:
            
            self._frame_durations_ms = [] # we only support constant framerate for apng, I think the spec support variable though if PIL ever supports that
            self._times_to_play_animation = HydrusAnimationHandling.GetTimesToPlayAPNG( self._path )
            
        elif self._media.GetMime() == HC.ANIMATION_WEBP:
            
            try:
                
                ( self._frame_durations_ms, self._times_to_play_animation ) = HydrusAnimationHandling.GetWebPFrameDurationsMS( self._path )
                
            except:
                
                self._frame_durations_ms = []
                self._times_to_play_animation = 0
                
            
        elif self._media.GetMime() == HC.ANIMATION_UGOIRA:
            
            self._times_to_play_animation = 0
            
        else:
            
            try:
                
                ( self._frame_durations_ms, self._times_to_play_animation ) = HydrusAnimationHandling.GetFrameDurationsMSPILAnimation( self._path )
                
            except:
                
                self._frame_durations_ms = []
                self._times_to_play_animation = 0
                
            
        
        # OK so just a note, you can switch GIF to the FFMPEG renderer these days and it works fine mate, transparency included
        if self._media.GetMime() in ( HC.ANIMATION_GIF, HC.ANIMATION_WEBP ):
            
            self._renderer = ClientVideoHandling.AnimationRendererPIL( self._path, num_frames_in_video, self._target_resolution )
            
        elif self._media.GetMime() == HC.ANIMATION_UGOIRA:
            
            self._renderer = ClientUgoiraHandling.UgoiraRenderer( self._path, num_frames_in_video, self._target_resolution )
            
        else:
            
            self._renderer = HydrusVideoHandling.VideoRendererFFMPEG( self._path, mime, duration_ms, num_frames_in_video, self._target_resolution )
            
        
        # give ui a chance to draw a blank frame rather than hard-charge right into CPUland
        time.sleep( 0.00001 )
        
        self.GetReadyForFrame( self._init_position )
        
        with self._lock:
            
            self._initialised = True
            
        
        while True:
            
            if self._stop or HG.started_shutdown:
                
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
                    
                    half_a_frame = ( HydrusTime.SecondiseMSFloat( self._average_frame_duration_ms ) ) * 0.5
                    
                    sleep_duration = min( 0.1, half_a_frame ) # for 10s-long 3-frame gifs, wew
                    
                    time.sleep( sleep_duration ) # just so we don't spam cpu
                    
                
            else:
                
                self._render_event.wait( 1 )
                
                self._render_event.clear()
                
            
        
    

class HydrusBitmap( ClientCachesBase.CacheableObject ):
    
    def __init__( self, data, size, depth, compressed = True ):
        
        super().__init__()
        
        self._compressed = compressed
        
        if isinstance( data, memoryview ) and not data.c_contiguous:
            
            data = data.tobytes() # this _should_ work and is an emergency relief
            
        
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
            
            return QG.QImage.Format.Format_RGB888
            
        elif self._depth == 4:
            
            return QG.QImage.Format.Format_RGBA8888
            
        
    
    def GetDepth( self ):
        
        return self._depth
        
    
    def GetQtImage( self ) -> QG.QImage:
        
        ( width, height ) = self._size
        
        return CG.client_controller.bitmap_manager.GetQtImageFromBuffer( width, height, self._depth * 8, self._GetData() )
        
    
    def GetQtPixmap( self ) -> QG.QPixmap:
        
        ( width, height ) = self._size
        
        return CG.client_controller.bitmap_manager.GetQtPixmapFromBuffer( width, height, self._depth * 8, self._GetData() )
        
    
    def GetEstimatedMemoryFootprint( self ):
        
        return len( self._data )
        
    
    def GetSize( self ):
        
        return self._size
        
    
    def IsFinishedLoading( self ):
        
        return True
        
    
