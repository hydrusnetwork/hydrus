import cv2

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG

cv_interpolation_enum_lookup = {}

cv_interpolation_enum_lookup[ CC.ZOOM_NEAREST ] = cv2.INTER_NEAREST
cv_interpolation_enum_lookup[ CC.ZOOM_LINEAR ] = cv2.INTER_LINEAR
cv_interpolation_enum_lookup[ CC.ZOOM_AREA ] = cv2.INTER_AREA
cv_interpolation_enum_lookup[ CC.ZOOM_CUBIC ] = cv2.INTER_CUBIC
cv_interpolation_enum_lookup[ CC.ZOOM_LANCZOS4 ] = cv2.INTER_LANCZOS4

def ResizeNumPyImageForMediaViewer( mime, numpy_image, target_resolution ):
    
    ( target_width, target_height ) = target_resolution
    new_options = CG.client_controller.new_options
    
    ( scale_up_quality, scale_down_quality ) = new_options.GetMediaZoomQuality( mime )
    
    ( image_height, image_width, depth ) = numpy_image.shape
    
    if ( target_width, target_height ) == ( image_height, image_width ):
        
        return numpy_image
        
    else:
        
        if target_width > image_width or target_height > image_height:
            
            interpolation = cv_interpolation_enum_lookup[ scale_up_quality ]
            
        else:
            
            interpolation = cv_interpolation_enum_lookup[ scale_down_quality ]
            
        
        return cv2.resize( numpy_image, ( target_width, target_height ), interpolation = interpolation )
        
    
