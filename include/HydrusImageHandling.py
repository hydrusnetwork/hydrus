import ClientConstants as CC
import cStringIO
import numpy.core.multiarray # important this comes before cv!
import cv
import cv2
import HydrusConstants as HC
import HydrusExceptions
import HydrusThreading
import lz4
import numpy
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
        
    
def EfficientlyResizeCVImage( cv_image, ( target_x, target_y ) ):
    
    ( im_y, im_x, depth ) = cv_image.shape
    
    if target_x >= im_x and target_y >= im_y: return cv_image
    
    result = cv_image
    
    # this seems to slow things down a lot, at least for cv!
    #if im_x > 2 * target_x and im_y > 2 * target_y: result = cv2.resize( cv_image, ( 2 * target_x, 2 * target_y ), interpolation = cv2.INTER_NEAREST )
    
    return cv2.resize( result, ( target_x, target_y ), interpolation = cv2.INTER_LINEAR )
    
def EfficientlyResizePILImage( pil_image, ( target_x, target_y ) ):
    
    ( im_x, im_y ) = pil_image.size
    
    if target_x >= im_x and target_y >= im_y: return pil_image
    
    #if pil_image.mode == 'RGB': # low quality resize screws up alpha channel!
    #    
    #    if im_x > 2 * target_x and im_y > 2 * target_y: pil_image.thumbnail( ( 2 * target_x, 2 * target_y ), PILImage.NEAREST )
    #    
    
    return pil_image.resize( ( target_x, target_y ), PILImage.ANTIALIAS )
    
def EfficientlyThumbnailCVImage( cv_image, ( target_x, target_y ) ):
    
    ( im_y, im_x, depth ) = cv_image.shape
    
    if target_x >= im_x and target_y >= im_y: return cv_image
    
    ( target_x, target_y ) = GetThumbnailResolution( ( im_x, im_y ), ( target_x, target_y ) )
    
    return cv2.resize( cv_image, ( target_x, target_y ), interpolation = cv2.INTER_AREA )
    
def EfficientlyThumbnailPILImage( pil_image, ( target_x, target_y ) ):
    
    ( im_x, im_y ) = pil_image.size
    
    #if pil_image.mode == 'RGB': # low quality resize screws up alpha channel!
    #    
    #    if im_x > 2 * target_x or im_y > 2 * target_y: pil_image.thumbnail( ( 2 * target_x, 2 * target_y ), PILImage.NEAREST )
    #    
    
    pil_image.thumbnail( ( target_x, target_y ), PILImage.ANTIALIAS )
    
def GenerateCVImage( path ):
    
    cv_image = cv2.imread( self._path, flags = -1 ) # flags = -1 loads alpha channel, if present
    
    ( x, y, depth ) = cv_image.shape
    
    if depth == 4: raise Exception( 'CV is bad at alpha!' )
    else: cv_image = cv2.cvtColor( cv_image, cv2.COLOR_BGR2RGB )
    
    return cv_image
    
def GenerateHydrusBitmap( path ):
    
    try:
        
        cv_image = GenerateCVImage( path )
        
        return GenerateHydrusBitmapFromCVImage( cv_image )
        
    except:
        
        pil_image = GeneratePILImage( path )
        
        return GenerateHydrusBitmapFromPILImage( pil_image )
        
    
def GenerateHydrusBitmapFromCVImage( cv_image ):
    
    ( y, x, depth ) = cv_image.shape
    
    if depth == 4: raise Exception( 'CV is bad at alpha!' )
    else: return HydrusBitmap( cv_image.data, wx.BitmapBufferFormat_RGB, ( x, y ) )
    
def GenerateHydrusBitmapFromPILImage( pil_image ):
    
    if pil_image.mode == 'RGBA' or ( pil_image.mode == 'P' and pil_image.info.has_key( 'transparency' ) ):
        
        if pil_image.mode == 'P': pil_image = pil_image.convert( 'RGBA' )
        
        return HydrusBitmap( pil_image.tostring(), wx.BitmapBufferFormat_RGBA, pil_image.size )
        
    else:
        
        if pil_image.mode != 'RGB': pil_image = pil_image.convert( 'RGB' )
        
        return HydrusBitmap( pil_image.tostring(), wx.BitmapBufferFormat_RGB, pil_image.size )
        
    
def GeneratePerceptualHash( path ):
    
    cv_image = cv2.imread( path, cv2.CV_LOAD_IMAGE_UNCHANGED )
    
    ( x, y, depth ) = cv_image.shape
    
    if depth == 4:
        
        # create a white greyscale canvas
        
        white = numpy.ones( ( x, y ) ) * 255
        
        # create weight and transform cv_image to greyscale
        
        cv_alpha = cv_image[ :, :, 3 ]
        
        cv_image_bgr = cv_image[ :, :, :3 ]
        
        cv_image_gray = cv2.cvtColor( cv_image_bgr, cv2.COLOR_BGR2GRAY )
        
        cv_image_result = numpy.empty( ( x, y ), numpy.float32 )
        
        # paste greyscale onto the white
        
        # can't think of a better way to do this!
        # cv2.addWeighted only takes a scalar for weight!
        for i in range( x ):
            
            for j in range( y ):
                
                opacity = float( cv_alpha[ i, j ] ) / 255.0
                
                grey_part = cv_image_gray[ i, j ] * opacity
                white_part = 255 * ( 1 - opacity )
                
                pixel = grey_part + white_part
                
                cv_image_result[ i, j ] = pixel
                
            
        
        cv_image_gray = cv_image_result
        
        # use 255 for white weight, alpha for image weight
        
    else:
        
        cv_image_gray = cv2.cvtColor( cv_image, cv2.COLOR_BGR2GRAY )
        
    
    cv_image_tiny = cv2.resize( cv_image_gray, ( 32, 32 ), interpolation = cv2.INTER_AREA )
    
    # convert to float and calc dct
    
    cv_image_tiny_float = numpy.float32( cv_image_tiny )
    
    dct = cv2.dct( cv_image_tiny_float )
    
    # take top left 8x8 of dct
    
    dct_88 = dct[:8,:8]
    
    # get mean of dct, excluding [0,0]
    
    mask = numpy.ones( ( 8, 8 ) )
    
    mask[0,0] = 0
    
    average = numpy.average( dct_88, weights = mask )
    
    # make a monochromatic, 64-bit hash of whether the entry is above or below the mean
    
    bytes = []
    
    for i in range( 8 ):
        
        byte = 0
        
        for j in range( 8 ):
            
            byte <<= 1 # shift byte one left
            
            value = dct_88[i,j]
            
            if value > average: byte |= 1
            
        
        bytes.append( byte )
        
    
    answer = str( bytearray( bytes ) )
    
    # we good
    
    return answer
    
def old_GeneratePerceptualHash( path ):
    
    # I think what I should be doing here is going cv2.imread( path, flags = cv2.CV_LOAD_IMAGE_GRAYSCALE )
    # then efficiently resize
    
    thumbnail = GeneratePILImage( path )
    
    # convert to 32 x 32 greyscale
    
    if thumbnail.mode == 'P':
        
        thumbnail = thumbnail.convert( 'RGBA' ) # problem with some P images converting to L without RGBA step in between
        
    
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

def GetGIFFrameDurations( path ):
    
    pil_image_for_duration = GeneratePILImage( path )
    
    frame_durations = []
    
    i = 0
    
    while True:
        
        try: pil_image_for_duration.seek( i )
        except: break
        
        if 'duration' not in pil_image_for_duration.info: duration = 40 # 25 fps default when duration is missing or too funky to extract. most stuff looks ok at this.
        else:
            
            duration = pil_image_for_duration.info[ 'duration' ]
            
            if duration == 0: duration = 40
            
        
        frame_durations.append( duration )
        
        i += 1
        
    
    return frame_durations
    
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
    
def GetImageProperties( path ):
    
    ( ( width, height ), num_frames ) = GetResolutionAndNumFrames( path )
    
    if num_frames > 1:
        
        durations = GetGIFFrameDurations( path )
        
        duration = sum( durations )
        
    else:
        
        duration = None
        num_frames = None
        
    
    return ( ( width, height ), duration, num_frames )
    
def GetResolutionAndNumFrames( path ):
    
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
    
def GetThumbnailResolution( ( im_x, im_y ), ( target_x, target_y ) ):
    
    im_x = float( im_x )
    im_y = float( im_y )
    
    target_x = float( target_x )
    target_y = float( target_y )
    
    x_ratio = im_x / target_x
    y_ratio = im_y / target_y
    
    ratio_to_use = max( x_ratio, y_ratio )
    
    target_x = int( im_x / ratio_to_use )
    target_y = int( im_y / ratio_to_use )
    
    return ( target_x, target_y )
    
''' # old pil code

def _GetCurrentFramePIL( pil_image, target_resolution, canvas ):
    
    current_frame = EfficientlyResizePILImage( pil_image, target_resolution )
    
    if pil_image.mode == 'P' and 'transparency' in pil_image.info:
        
        # I think gif problems are around here somewhere; the transparency info is not converted to RGBA properly, so it starts drawing colours when it should draw nothing
        
        current_frame = current_frame.convert( 'RGBA' )
        
        if canvas is None: canvas = current_frame
        else: canvas.paste( current_frame, None, current_frame ) # yeah, use the rgba image as its own mask, wut.
        
    else: canvas = current_frame
    
    return canvas
    

def _GetFramePIL( self, index ):
    
    pil_image = self._image_object
    
    pil_image.seek( index )
    
    canvas = self._GetCurrentFramePIL( pil_image, self._target_resolution, canvas )
    
    return GenerateHydrusBitmapFromPILImage( canvas )
    

def _GetFramesPIL( self ):
    
    pil_image = self._image_object
    
    canvas = None
    
    global_palette = pil_image.palette
    
    dirty = pil_image.palette.dirty
    mode = pil_image.palette.mode
    rawmode = pil_image.palette.rawmode
    
    # believe it or not, doing this actually fixed a couple of gifs!
    pil_image.seek( 1 )
    pil_image.seek( 0 )
    
    while True:
        
        canvas = self._GetCurrentFramePIL( pil_image, self._target_resolution, canvas )
        
        yield GenerateHydrusBitmapFromPILImage( canvas )
        
        try:
            
            pil_image.seek( pil_image.tell() + 1 )
            
            if pil_image.palette == global_palette: # for some reason, when we fall back to global palette (no local-frame palette), we reset bunch of important variables!
                
                pil_image.palette.dirty = dirty
                pil_image.palette.mode = mode
                pil_image.palette.rawmode = rawmode
                
            
        except: break
        
    
'''

# the cv code was initially written by @fluffy_cub
class HydrusBitmap():
    
    def __init__( self, data, format, size ):
        
        self._data = lz4.dumps( data )
        self._format = format
        self._size = size
        
    
    def CreateWxBmp( self ):
        
        ( width, height ) = self._size
        
        if self._format == wx.BitmapBufferFormat_RGB: return wx.BitmapFromBuffer( width, height, lz4.loads( self._data ) )
        else: return wx.BitmapFromBufferRGBA( width, height, lz4.loads( self._data ) )
        
    
    def GetEstimatedMemoryFootprint( self ): return len( self._data )
    
    def GetSize( self ): return self._size
    
class RasterContainer( object ):
    
    def __init__( self, media, target_resolution = None ):
        
        if target_resolution is None: target_resolution = media.GetResolution()
        
        self._media = media
        self._target_resolution = target_resolution
        
        hash = self._media.GetHash()
        mime = self._media.GetMime()
        
        self._path = CC.GetFilePath( hash, mime )
        
        ( original_width, original_height ) = self._media.GetResolution()
        
        ( my_width, my_height ) = target_resolution
        
        width_zoom = my_width / float( original_width )
        height_zoom = my_height / float( original_height )
        
        self._zoom = min( ( width_zoom, height_zoom ) )
        
        if self._zoom > 1.0: self._zoom = 1.0
        
    
class ImageContainer( RasterContainer ):
    
    def __init__( self, media, target_resolution = None ):
        
        RasterContainer.__init__( self, media, target_resolution )
        
        self._hydrus_bitmap = None
        
        HydrusThreading.CallToThread( self.THREADRender )
        
    
    def _GetHydrusBitmap( self ):
        
        try:
            
            cv_image = GenerateCVImage( self._path )
            
            resized_cv_image = EfficientlyResizeCVImage( cv_image, self._target_resolution )
            
            return GenerateHydrusBitmapFromCVImage( resized_cv_image )
            
        except:
            
            pil_image = GeneratePILImage( self._path )
            
            resized_pil_image = EfficientlyResizePILImage( pil_image, self._target_resolution )
            
            return GenerateHydrusBitmapFromPILImage( resized_pil_image )
            
        
    
    def THREADRender( self ):
        
        time.sleep( 0.00001 ) # thread yield
        
        wx.CallAfter( self.SetHydrusBitmap, self._GetHydrusBitmap() )
        
        HC.pubsub.pub( 'finished_rendering', self.GetKey() )
        
    
    def GetEstimatedMemoryFootprint( self ): return self._hydrus_bitmap.GetEstimatedMemoryFootprint()
    
    def GetHash( self ): return self._media.GetHash()
    
    def GetHydrusBitmap( self ): return self._hydrus_bitmap
    
    def GetKey( self ): return ( self._media.GetHash(), self._target_resolution )
    
    def GetNumFrames( self ): return self._media.GetNumFrames()
    
    def GetResolution( self ): return self._media.GetResolution()
    
    def GetSize( self ): return self._target_resolution
    
    def GetZoom( self ): return self._zoom
    
    def IsRendered( self ): return self._hydrus_bitmap is not None
    
    def IsScaled( self ): return self._zoom != 1.0
    
    def SetHydrusBitmap( self, hydrus_bitmap ): self._hydrus_bitmap = hydrus_bitmap
    