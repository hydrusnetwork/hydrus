from PIL import Image as PILImage
from PIL import ImageOps as PILImageOps

from hydrus.core.files.images import HydrusImageHandling

THUMBNAIL_SCALE_DOWN_ONLY = 0
THUMBNAIL_SCALE_TO_FIT = 1
THUMBNAIL_SCALE_TO_FILL = 2

thumbnail_scale_str_lookup = {
    THUMBNAIL_SCALE_DOWN_ONLY : 'scale down only',
    THUMBNAIL_SCALE_TO_FIT : 'scale to fit',
    THUMBNAIL_SCALE_TO_FILL : 'scale to fill'
}

def GenerateDefaultThumbnailNumPyFromPath( path: str, target_resolution: tuple[ int, int ] ):
    
    thumb_image = HydrusImageHandling.GeneratePILImage( path )
    
    try:
        
        pil_image = PILImageOps.pad( thumb_image, target_resolution, PILImage.Resampling.LANCZOS )
        
        try:
            
            result = HydrusImageHandling.GenerateNumPyImageFromPILImage( pil_image, strip_useless_alpha = False )
            
        finally:
            
            pil_image.close()
            
        
    finally:
        
        thumb_image.close()
        
    
    return result
    

def GenerateThumbnailBytesFromNumPy( numpy_image ) -> bytes:
    
    if len( numpy_image.shape ) == 2:
        
        depth = 3
        
    else:
        
        ( im_height, im_width, depth ) = numpy_image.shape
        
    
    if depth == 4:
        
        ext = '.png'
        
        params = HydrusImageHandling.CV_PNG_THUMBNAIL_ENCODE_PARAMS
        
    else:
        
        ext = '.jpg'
        
        params = HydrusImageHandling.CV_JPEG_THUMBNAIL_ENCODE_PARAMS
        
    
    return HydrusImageHandling.GenerateFileBytesNumPy( numpy_image, ext, params )
    

def GetThumbnailResolution( image_resolution: tuple[ int, int ], bounding_dimensions: tuple[ int, int ], thumbnail_scale_type: int, thumbnail_dpr_percent: int ) -> tuple[ int, int ]:
    
    ( im_width, im_height ) = image_resolution
    ( bounding_width, bounding_height ) = bounding_dimensions
    
    if thumbnail_dpr_percent != 100:
        
        thumbnail_dpr = thumbnail_dpr_percent / 100
        
        bounding_height = int( bounding_height * thumbnail_dpr )
        bounding_width = int( bounding_width * thumbnail_dpr )
        
    
    # this is appropriate for the crazy (0x0) svg or whatever we have, since we will _try_ to render it properly later on
    # but if it fails to render, we'll still get a fairly nice filetype.png or hydrus.png fallback
    # we don't want to pass around 0x0 and have a handler everywhere
    if im_width is None or im_width == 0 or im_height is None or im_height == 0:
        
        im_width = bounding_width
        im_height = bounding_width
        
    
    # TODO SVG thumbs should always scale up to the bounding dimensions
    
    if thumbnail_scale_type == THUMBNAIL_SCALE_DOWN_ONLY:
        
        if bounding_width >= im_width and bounding_height >= im_height:
            
            return ( im_width, im_height )
            
        
    
    image_ratio = im_width / im_height
    
    width_ratio = im_width / bounding_width
    height_ratio = im_height / bounding_height
    
    image_is_wider_than_bounding_box = width_ratio > height_ratio
    image_is_taller_than_bounding_box = height_ratio > width_ratio
    
    thumbnail_width = bounding_width
    thumbnail_height = bounding_height
    
    if thumbnail_scale_type in ( THUMBNAIL_SCALE_DOWN_ONLY, THUMBNAIL_SCALE_TO_FIT ):
        
        if image_is_taller_than_bounding_box: # i.e. the height will be at bounding height
            
            thumbnail_width = im_width / height_ratio
            
        elif image_is_wider_than_bounding_box: # i.e. the width will be at bounding width
            
            thumbnail_height = im_height / width_ratio
            
        
    elif thumbnail_scale_type == THUMBNAIL_SCALE_TO_FILL:
        
        # we do min 5.0 here to stop really tall and thin images getting zoomed in from width 1px to 150 and getting a thumbnail with a height of 75,000 pixels
        # in this case the line image is already crazy distorted, so we don't mind squishing it
        
        if image_is_taller_than_bounding_box: # i.e. the width will be at bounding width, the height will spill over
            
            thumbnail_height = bounding_width * min( 5.0, 1 / image_ratio )
            
        elif image_is_wider_than_bounding_box: # i.e. the height will be at bounding height, the width will spill over
            
            thumbnail_width = bounding_height * min( 5.0, image_ratio )
            
        
        # old stuff that actually clipped the size of the thing
        '''
        clip_x = 0
        clip_y = 0
        clip_width = im_width
        clip_height = im_height
        
        if width_ratio > height_ratio:
            
            clip_width = max( int( im_width * height_ratio / width_ratio ), 1 )
            clip_x = ( im_width - clip_width ) // 2
            
        elif height_ratio > width_ratio:
            
            clip_height = max( int( im_height * width_ratio / height_ratio ), 1 )
            clip_y = ( im_height - clip_height ) // 2
            
        
        clip_rect = ( clip_x, clip_y, clip_width, clip_height )
        '''
        
    
    thumbnail_width = int( thumbnail_width )
    thumbnail_height = int( thumbnail_height )
    
    thumbnail_width = max( thumbnail_width, 1 )
    thumbnail_height = max( thumbnail_height, 1 )
    
    return ( thumbnail_width, thumbnail_height )
    
