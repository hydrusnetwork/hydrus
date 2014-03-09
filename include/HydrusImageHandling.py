import cStringIO
import numpy.core.multiarray # important this comes before cv!
import cv
import cv2
import HydrusConstants as HC
import HydrusExceptions
import os
from PIL import Image as PILImage
import shutil
import struct
import threading
import time
import traceback
import wx

#LINEAR_SCALE_PALETTE = [ 0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8, 9, 9, 9, 10, 10, 10, 11, 11, 11, 12, 12, 12, 13, 13, 13, 14, 14, 14, 15, 15, 15, 16, 16, 16, 17, 17, 17, 18, 18, 18, 19, 19, 19, 20, 20, 20, 21, 21, 21, 22, 22, 22, 23, 23, 23, 24, 24, 24, 25, 25, 25, 26, 26, 26, 27, 27, 27, 28, 28, 28, 29, 29, 29, 30, 30, 30, 31, 31, 31, 32, 32, 32, 33, 33, 33, 34, 34, 34, 35, 35, 35, 36, 36, 36, 37, 37, 37, 38, 38, 38, 39, 39, 39, 40, 40, 40, 41, 41, 41, 42, 42, 42, 43, 43, 43, 44, 44, 44, 45, 45, 45, 46, 46, 46, 47, 47, 47, 48, 48, 48, 49, 49, 49, 50, 50, 50, 51, 51, 51, 52, 52, 52, 53, 53, 53, 54, 54, 54, 55, 55, 55, 56, 56, 56, 57, 57, 57, 58, 58, 58, 59, 59, 59, 60, 60, 60, 61, 61, 61, 62, 62, 62, 63, 63, 63, 64, 64, 64, 65, 65, 65, 66, 66, 66, 67, 67, 67, 68, 68, 68, 69, 69, 69, 70, 70, 70, 71, 71, 71, 72, 72, 72, 73, 73, 73, 74, 74, 74, 75, 75, 75, 76, 76, 76, 77, 77, 77, 78, 78, 78, 79, 79, 79, 80, 80, 80, 81, 81, 81, 82, 82, 82, 83, 83, 83, 84, 84, 84, 85, 85, 85, 86, 86, 86, 87, 87, 87, 88, 88, 88, 89, 89, 89, 90, 90, 90, 91, 91, 91, 92, 92, 92, 93, 93, 93, 94, 94, 94, 95, 95, 95, 96, 96, 96, 97, 97, 97, 98, 98, 98, 99, 99, 99, 100, 100, 100, 101, 101, 101, 102, 102, 102, 103, 103, 103, 104, 104, 104, 105, 105, 105, 106, 106, 106, 107, 107, 107, 108, 108, 108, 109, 109, 109, 110, 110, 110, 111, 111, 111, 112, 112, 112, 113, 113, 113, 114, 114, 114, 115, 115, 115, 116, 116, 116, 117, 117, 117, 118, 118, 118, 119, 119, 119, 120, 120, 120, 121, 121, 121, 122, 122, 122, 123, 123, 123, 124, 124, 124, 125, 125, 125, 126, 126, 126, 127, 127, 127, 128, 128, 128, 129, 129, 129, 130, 130, 130, 131, 131, 131, 132, 132, 132, 133, 133, 133, 134, 134, 134, 135, 135, 135, 136, 136, 136, 137, 137, 137, 138, 138, 138, 139, 139, 139, 140, 140, 140, 141, 141, 141, 142, 142, 142, 143, 143, 143, 144, 144, 144, 145, 145, 145, 146, 146, 146, 147, 147, 147, 148, 148, 148, 149, 149, 149, 150, 150, 150, 151, 151, 151, 152, 152, 152, 153, 153, 153, 154, 154, 154, 155, 155, 155, 156, 156, 156, 157, 157, 157, 158, 158, 158, 159, 159, 159, 160, 160, 160, 161, 161, 161, 162, 162, 162, 163, 163, 163, 164, 164, 164, 165, 165, 165, 166, 166, 166, 167, 167, 167, 168, 168, 168, 169, 169, 169, 170, 170, 170, 171, 171, 171, 172, 172, 172, 173, 173, 173, 174, 174, 174, 175, 175, 175, 176, 176, 176, 177, 177, 177, 178, 178, 178, 179, 179, 179, 180, 180, 180, 181, 181, 181, 182, 182, 182, 183, 183, 183, 184, 184, 184, 185, 185, 185, 186, 186, 186, 187, 187, 187, 188, 188, 188, 189, 189, 189, 190, 190, 190, 191, 191, 191, 192, 192, 192, 193, 193, 193, 194, 194, 194, 195, 195, 195, 196, 196, 196, 197, 197, 197, 198, 198, 198, 199, 199, 199, 200, 200, 200, 201, 201, 201, 202, 202, 202, 203, 203, 203, 204, 204, 204, 205, 205, 205, 206, 206, 206, 207, 207, 207, 208, 208, 208, 209, 209, 209, 210, 210, 210, 211, 211, 211, 212, 212, 212, 213, 213, 213, 214, 214, 214, 215, 215, 215, 216, 216, 216, 217, 217, 217, 218, 218, 218, 219, 219, 219, 220, 220, 220, 221, 221, 221, 222, 222, 222, 223, 223, 223, 224, 224, 224, 225, 225, 225, 226, 226, 226, 227, 227, 227, 228, 228, 228, 229, 229, 229, 230, 230, 230, 231, 231, 231, 232, 232, 232, 233, 233, 233, 234, 234, 234, 235, 235, 235, 236, 236, 236, 237, 237, 237, 238, 238, 238, 239, 239, 239, 240, 240, 240, 241, 241, 241, 242, 242, 242, 243, 243, 243, 244, 244, 244, 245, 245, 245, 246, 246, 246, 247, 247, 247, 248, 248, 248, 249, 249, 249, 250, 250, 250, 251, 251, 251, 252, 252, 252, 253, 253, 253, 254, 254, 254, 255, 255, 255 ]

def ConvertToPngIfBmp( path ):
    
    with open( path, 'rb' ) as f: header = f.read( 2 )
    
    if header == 'BM':
        
        temp_path = HC.GetTempPath()
        
        shutil.move( path, temp_path )
        
        pil_image = GeneratePILImage( temp_path )
        
        pil_image = pil_image.convert( 'P' )
        
        pil_image.save( path, 'PNG' )
        
        os.remove( temp_path )
        
    
def EfficientlyResizeImage( pil_image, ( x, y ) ):
    
    ( im_x, im_y ) = pil_image.size
    
    if x >= im_x and y >= im_y: return pil_image
    
    if pil_image.mode == 'RGB': # low quality resize screws up alpha channel!
        
        if im_x > 2 * x and im_y > 2 * y: pil_image.thumbnail( ( 2 * x, 2 * y ), PILImage.NEAREST )
        
    
    return pil_image.resize( ( x, y ), PILImage.ANTIALIAS )
    
def EfficientlyThumbnailImage( pil_image, ( x, y ) ):
    
    ( im_x, im_y ) = pil_image.size
    
    if pil_image.mode == 'RGB': # low quality resize screws up alpha channel!
        
        if im_x > 2 * x or im_y > 2 * y: pil_image.thumbnail( ( 2 * x, 2 * y ), PILImage.NEAREST )
        
    
    pil_image.thumbnail( ( x, y ), PILImage.ANTIALIAS )
    
def GenerateAnimatedFrame( pil_image, target_resolution, canvas ):
    
    if 'duration' not in pil_image.info: duration = 40 # 25 fps default when duration is missing or too funky to extract. most stuff looks ok at this.
    else:
        
        duration = pil_image.info[ 'duration' ]
        
        if duration == 0: duration = 40
        
    
    current_frame = EfficientlyResizeImage( pil_image, target_resolution )
    
    if canvas is None: canvas = current_frame
    else: canvas.paste( current_frame )
    
    return ( canvas, duration )
    
def GenerateHydrusBitmap( path ):
    
    pil_image = GeneratePILImage( path )
    
    return GenerateHydrusBitmapFromPILImage( pil_image )
    
def GenerateHydrusBitmapFromPILImage( pil_image ):
    
    if pil_image.mode == 'RGBA' or ( pil_image.mode == 'P' and pil_image.info.has_key( 'transparency' ) ):
        
        if pil_image.mode == 'P': pil_image = pil_image.convert( 'RGBA' )
        
        return HydrusBitmap( pil_image.tostring(), wx.BitmapBufferFormat_RGBA, pil_image.size )
        
    else:
        
        if pil_image.mode != 'RGB': pil_image = pil_image.convert( 'RGB' )
        
        return HydrusBitmap( pil_image.tostring(), wx.BitmapBufferFormat_RGB, pil_image.size )
        
    
def GeneratePerceptualHash( path ):
    
    thumbnail = GeneratePILImage( path )
    
    # convert to 32 x 32 greyscale
    
    if thumbnail.mode == 'RGBA':
        
        # this is some code i picked up somewhere
        # another great example of PIL failing; it turns all alpha to pure black on a RGBA->RGB
        
        thumbnail.load()
        
        canvas = PILImage.new( 'RGB', thumbnail.size, ( 255, 255, 255 ) )
        
        canvas.paste( thumbnail, mask = thumbnail.split()[3] )
        
        thumbnail = canvas
        
    
    thumbnail = thumbnail.convert( 'L' )
    
    thumbnail = thumbnail.resize( ( 32, 32 ), PILImage.ANTIALIAS )
    
    # convert to mat
    
    cv_thumbnail_8 = cv.CreateMatHeader( 32, 32, cv.CV_8UC1 )
    
    cv.SetData( cv_thumbnail_8, thumbnail.tostring() )
    
    cv_thumbnail_32 = cv.CreateMat( 32, 32, cv.CV_32FC1 )
    
    cv.Convert( cv_thumbnail_8, cv_thumbnail_32 )
    
    # compute dct
    
    dct = cv.CreateMat( 32, 32, cv.CV_32FC1 )
    
    cv.DCT( cv_thumbnail_32, dct, cv.CV_DXT_FORWARD )
    
    # take top left 8x8 of dct
    
    dct = cv.GetSubRect( dct, ( 0, 0, 8, 8 ) )
    
    # get mean of dct, excluding [0,0]
    
    mask = cv.CreateMat( 8, 8, cv.CV_8U )
    
    cv.Set( mask, 1 )
    
    mask[0,0] = 0
    
    channel_averages = cv.Avg( dct, mask )
    
    average = channel_averages[0]
    
    # make a monochromatic, 64-bit hash of whether the entry is above or below the mean
    
    bytes = []
    
    for i in range( 8 ):
        
        byte = 0
        
        for j in range( 8 ):
            
            byte <<= 1 # shift byte one left
            
            value = dct[i,j]
            
            if value > average: byte |= 1
            
        
        bytes.append( byte )
        
    
    answer = str( bytearray( bytes ) )
    
    # we good
    
    return answer
    
def GeneratePILImage( path ): return PILImage.open( path )

def GenerateResolutionAndNumFrames( path ):
    
    pil_image = GeneratePILImage( path )
    
    ( x, y ) = pil_image.size
    
    try:
        
        pil_image.seek( 1 )
        pil_image.seek( 0 )
        
        num_frames = 1
        
        while True:
            
            try:
                
                pil_image.seek( pil_image.tell() + 1 )
                num_frames += 1
                
            except: break
            
        
    except: num_frames = 1
    
    return ( ( x, y ), num_frames )
    
def GenerateThumbnail( path, dimensions = HC.UNSCALED_THUMBNAIL_DIMENSIONS ):
    
    pil_image = GeneratePILImage( path )
    
    EfficientlyThumbnailImage( pil_image, dimensions )
    
    f = cStringIO.StringIO()
    
    if pil_image.mode == 'P' and pil_image.info.has_key( 'transparency' ):
        
        pil_image.save( f, 'PNG', transparency = pil_image.info[ 'transparency' ] )
        
    elif pil_image.mode == 'RGBA': pil_image.save( f, 'PNG' )
    else:
        
        pil_image = pil_image.convert( 'RGB' )
        
        pil_image.save( f, 'JPEG', quality=92 )
        
    
    f.seek( 0 )
    
    thumbnail = f.read()
    
    f.close()
    
    return thumbnail
    
def GetHammingDistance( phash1, phash2 ):
    
    distance = 0
    
    phash1 = bytearray( phash1 )
    phash2 = bytearray( phash2 )
    
    for i in range( len( phash1 ) ):
        
        xor = phash1[i] ^ phash2[i]
        
        while xor > 0:
            
            distance += 1
            xor &= xor - 1
            
        
    
    return distance
    
def RenderImage( path, hash, target_resolution = None, synchronous = True ):
    
    try:
        
        ( original_resolution, num_frames ) = GenerateResolutionAndNumFrames( path )
        
        if target_resolution is None: target_resolution = original_resolution
        
        image_container = RenderedImageContainer( hash, original_resolution, target_resolution, num_frames )
        
        if image_container.IsAnimated(): renderer = AnimatedFrameRenderer( image_container, path, target_resolution )
        else: renderer = StaticFrameRenderer( image_container, path, target_resolution )
        
        if synchronous: renderer.Render()
        else: threading.Thread( target = renderer.THREADRender ).start()
        
        return image_container
        
    except Exception as e:
        
        raise Exception( 'Attempted to render the image, but received an error. It was likely either formatted slightly incorrectly or PIL could not handle it; look up PIL in the hydrus help for more info. Here is the exact error:' + os.linesep + os.linesep + HC.u( e ) )
        
    
class FrameRenderer():
    
    def __init__( self, image_container, path, target_resolution ):
        
        self._image_container = image_container
        self._path = path
        self._target_resolution = target_resolution
        
    
class AnimatedFrameRenderer( FrameRenderer ):
    
    def _GetFramesPIL( self ):
        
        pil_image = GeneratePILImage( self._path )
        
        canvas = None
        
        while True:
            
            try:
                if 'transparency' in pil_image.info:
                    # it is possible that the first frame of an image is RGB and every other frame RGBA
                    if not canvas is None and canvas.mode == "RGB":
                        canvas = canvas.convert( "RGBA" )
            
                    pil_canvas = pil_image.convert( "RGBA" )

                else:
                    pil_canvas = pil_image.convert( "RGB" )
                
                pil_canvas.info = pil_image.info
                
            except:
                # skip corrupt images in a gif ( e.g. images, which cannot be converted to neither RGBA nor RGB )
                if not canvas is None: pil_canvas = canvas
                else: pil_canvas = PILImage.new( "RGBA", pil_image.size )
                
                pil_canvas.info['duration'] = 1
            
            ( canvas, duration ) = GenerateAnimatedFrame( pil_canvas, self._target_resolution, canvas )
            yield ( GenerateHydrusBitmapFromPILImage( canvas ), duration )

            try:
                
                pil_image.seek( pil_image.tell() + 1 )
                
            except: break
            
        
    
    def GetFrames( self ):
    
        for ( frame, duration ) in self._GetFramesPIL(): yield ( frame, duration )
        
        #try:
            
            #for ( frame, duration ) in self._GetFramesCV(): yield ( frame, duration )
            
        #except HydrusExceptions.CantRenderWithCVException:
            
        #    for ( frame, duration ) in self._GetFramesPIL(): yield ( frame, duration )
            
    
    def Render( self ):
        
        for ( frame, duration ) in self.GetFrames(): self._image_container.AddFrame( frame, duration )
        
    
    def THREADRender( self ):
        
        time.sleep( 0.00001 ) # thread yield
        
        for ( frame, duration ) in self.GetFrames(): wx.CallAfter( self._image_container.AddFrame, frame, duration )
        
        HC.pubsub.pub( 'finished_rendering', self._image_container.GetKey() )
        
    
class StaticFrameRenderer( FrameRenderer ):
    
    def GetFrame( self ):
        
        pil_image = GeneratePILImage( self._path )
        
        return GenerateHydrusBitmapFromPILImage( EfficientlyResizeImage( pil_image, self._target_resolution ) )
        
    
    def Render( self ): self._image_container.AddFrame( self.GetFrame() )
    
    def THREADRender( self ):
        
        time.sleep( 0.00001 ) # thread yield
        
        wx.CallAfter( self._image_container.AddFrame, self.GetFrame() )
        
        HC.pubsub.pub( 'finished_rendering', self._image_container.GetKey() )
        
    
class HydrusBitmap():
    
    def __init__( self, data, format, size ):
        
        self._data = data
        self._format = format
        self._size = size
        
    
    def CreateWxBmp( self ):
        
        ( width, height ) = self._size
        
        if self._format == wx.BitmapBufferFormat_RGB: return wx.BitmapFromBuffer( width, height, self._data )
        else: return wx.BitmapFromBufferRGBA( width, height, self._data )
        
    
    def GetEstimatedMemoryFootprint( self ): return len( self._data )
    
    def GetSize( self ): return self._size
    
class RenderedImageContainer():
    
    def __init__( self, hash, original_resolution, my_resolution, num_frames ):
        
        self._hash = hash
        self._original_resolution = original_resolution
        self._my_resolution = my_resolution
        self._num_frames = num_frames
        
        ( original_width, original_height ) = original_resolution
        
        ( my_width, my_height ) = my_resolution
        
        width_zoom = my_width / float( original_width )
        height_zoom = my_height / float( original_height )
        
        self._zoom = min( ( width_zoom, height_zoom ) )
        
        if self._zoom > 1.0: self._zoom = 1.0
        
        self._frames = []
        self._durations = []
        
        self._finished_rendering = False
        
    
    def AddFrame( self, frame, duration = None ):
        
        self._frames.append( frame )
        
        if duration is not None: self._durations.append( duration )
        
    
    def GetDuration( self, index ): return self._durations[ index ]
    
    def GetEstimatedMemoryFootprint( self ): return sum( [ frame.GetEstimatedMemoryFootprint() for frame in self._frames ] )
    
    def GetFrame( self, index = None ):
        
        if index is None: return self._frames[ 0 ]
        else: return self._frames[ index ]
        
    
    def GetHash( self ): return self._hash
    
    def GetKey( self ): return ( self._hash, self._my_resolution )
    
    def GetNumFrames( self ): return self._num_frames
    
    def GetNumFramesRendered( self ): return len( self._frames )
    
    def GetResolution( self ): return self._original_resolution
    
    def GetSize( self ): return self._my_resolution
    
    def GetTotalDuration( self ): return sum( self._durations )
    
    def GetZoom( self ): return self._zoom
    
    def HasFrame( self, index = None ):
        
        if index is None: index = 0
        
        return len( self._frames ) > index
        
    
    def IsAnimated( self ): return self._num_frames > 1
    
    def IsFinishedRendering( self ): return len( self._frames ) == self._num_frames
    
    def IsScaled( self ): return self._zoom != 1.0
    