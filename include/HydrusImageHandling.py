import cStringIO
import HydrusConstants as HC
import HydrusExceptions
import HydrusThreading
import os
from PIL import _imaging
from PIL import Image as PILImage
import shutil
import struct
import threading
import time
import traceback
import HydrusData
import HydrusGlobals as HG
import HydrusPaths

def ConvertToPngIfBmp( path ):
    
    with open( path, 'rb' ) as f: header = f.read( 2 )
    
    if header == 'BM':
        
        ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
        
        try:
            
            with open( path, 'rb' ) as f_source:
                
                with open( temp_path, 'wb' ) as f_dest:
                    
                    HydrusPaths.CopyFileLikeToFileLike( f_source, f_dest )
                    
                
            
            pil_image = GeneratePILImage( temp_path )
            
            pil_image.save( path, 'PNG' )
            
        finally:
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
        
    
def Dequantize( pil_image ):
    
    if pil_image.mode not in ( 'RGBA', 'RGB' ):
        
        if pil_image.mode == 'LA' or ( pil_image.mode == 'P' and pil_image.info.has_key( 'transparency' ) ):
            
            pil_image = pil_image.convert( 'RGBA' )
            
        else:
            
            pil_image = pil_image.convert( 'RGB' )
            
        
    
    return pil_image
    
def EfficientlyResizePILImage( pil_image, ( target_x, target_y ) ):
    
    ( im_x, im_y ) = pil_image.size
    
    if target_x >= im_x and target_y >= im_y: return pil_image
    
    #if pil_image.mode == 'RGB': # low quality resize screws up alpha channel!
    #    
    #    if im_x > 2 * target_x and im_y > 2 * target_y: pil_image.thumbnail( ( 2 * target_x, 2 * target_y ), PILImage.NEAREST )
    #    
    
    return pil_image.resize( ( target_x, target_y ), PILImage.ANTIALIAS )
    
def EfficientlyThumbnailPILImage( pil_image, ( target_x, target_y ) ):
    
    ( im_x, im_y ) = pil_image.size
    
    #if pil_image.mode == 'RGB': # low quality resize screws up alpha channel!
    #    
    #    if im_x > 2 * target_x or im_y > 2 * target_y: pil_image.thumbnail( ( 2 * target_x, 2 * target_y ), PILImage.NEAREST )
    #    
    
    if im_x > target_x or im_y > target_y:
        
        pil_image.thumbnail( ( target_x, target_y ), PILImage.ANTIALIAS )
        
    
def GeneratePILImage( path ):
    
    fp = open( path, 'rb' )
    
    try:
        
        pil_image = PILImage.open( fp )
        
    except:
        
        # pil doesn't clean up its open file on exception, jej
        
        fp.close()
        
        raise
        
    
    if pil_image is None:
        
        raise Exception( 'The file at ' + path + ' could not be rendered!' )
        
    
    return pil_image
    
def GeneratePILImageFromNumpyImage( numpy_image ):
    
    ( h, w, depth ) = numpy_image.shape
    
    if depth == 3:
        
        format = 'RGB'
        
    elif depth == 4:
        
        format = 'RGBA'
        
    
    pil_image = PILImage.frombytes( format, ( w, h ), numpy_image.data )
    
    return pil_image
    
def GetGIFFrameDurations( path ):
    
    pil_image = GeneratePILImage( path )
    
    frame_durations = []
    
    i = 0
    
    while True:
        
        try: pil_image.seek( i )
        except: break
        
        if 'duration' not in pil_image.info:
            
            duration = 83 # Set a 12 fps default when duration is missing or too funky to extract. most stuff looks ok at this.
            
        else:
            
            duration = pil_image.info[ 'duration' ]
            
            # In the gif frame header, 10 is stored as 1ms. This 1 is commonly as utterly wrong as 0.
            if duration in ( 0, 10 ):
                
                duration = 80
                
            
        
        frame_durations.append( duration )
        
        i += 1
        
    
    return frame_durations
    
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
    
    if target_x >= im_x and target_y >= im_y:
        
        return ( im_x, im_y )
        
    
    im_x = float( im_x )
    im_y = float( im_y )
    
    target_x = float( target_x )
    target_y = float( target_y )
    
    x_ratio = im_x / target_x
    y_ratio = im_y / target_y
    
    if x_ratio > y_ratio:
        
        target_y = im_y / x_ratio
        
    elif y_ratio > x_ratio:
        
        target_x = im_x / y_ratio
        
    
    target_x = int( target_x )
    target_y = int( target_y )
    
    return ( target_x, target_y )
    
