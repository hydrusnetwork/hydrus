import typing

from PIL import Image as PILImage

from hydrus.core import HydrusExceptions

def GetEmbeddedFileText( pil_image: PILImage.Image ) -> typing.Optional[ str ]:
    
    def render_dict( d, prefix ):
        
        texts = []
        
        keys = sorted( d.keys() )
        
        for key in keys:
            
            if key in ( 'exif', 'icc_profile' ):
                
                continue
                
            
            value = d[ key ]
            
            if isinstance( value, bytes ):
                
                continue
                
            
            if isinstance( value, dict ):
                
                value_string = render_dict( value, prefix = '    ' + prefix )
                
                if value_string is None:
                    
                    continue
                    
                
            else:
                
                value_string = '    {}{}'.format( prefix, value )
                
            
            row_text = '{}{}:'.format( prefix, key )
            row_text += '\n'
            row_text += value_string
            
            texts.append( row_text )
            
        
        if len( texts ) > 0:
            
            return '\n'.join( texts )
            
        else:
            
            return None
            
        
    
    if hasattr( pil_image, 'info' ):
        
        try:
            
            return render_dict( pil_image.info, '' )
            
        except:
            
            pass
            
        
    
    return None
    

def GetEXIFDict( pil_image: PILImage.Image ) -> typing.Optional[ dict ]:
    
    if pil_image.format in ( 'JPEG', 'JXL', 'TIFF', 'PNG', 'WEBP', 'HEIF', 'AVIF', 'MPO' ):
        
        try:
            
            exif_dict = pil_image.getexif()._get_merged_dict()
            
            if len( exif_dict ) > 0:
                
                return exif_dict
                
            
        except:
            
            pass
            
        
    
    return None
    

def GetICCProfileBytes( pil_image: PILImage.Image ) -> bytes:
    
    if HasICCProfile( pil_image ):
        
        return pil_image.info[ 'icc_profile' ]
        
    
    raise HydrusExceptions.DataMissing( 'This image has no ICC profile!' )
    

# bigger number is worse quality
# this is very rough and misses some finesse
def GetJPEGQuantizationQualityEstimate( pil_image: PILImage.Image ):
    
    if hasattr( pil_image, 'quantization' ):
        
        table_arrays = list( pil_image.quantization.values() )
        
        if len( table_arrays ) == 0:
            
            return ( 'unknown', None )
            
        
        quality = sum( ( sum( table_array ) for table_array in table_arrays ) )
        
        quality /= len( table_arrays )
        
        # ok we are going to do some exponential magic here
        # 422 is roughly 0.92 in the arithmetic 'visual quality' scale of 444
        # 420 is 0.85
        # 'other' is going to be 0.75
        # we want to splay that number to our inverse exponential quality metric
        # typically we'd do multiply and simple to-the-power-of, but since a higher score here is lower quality, we divide/invert instead
        # basically:
        #
        # score_arithmetic = ln( x )
        # score_arithmetic /= 0.92
        # x_modified = e^score_arithmetic
        #
        # which is equivalent to:
        #
        # x ^ (1/0.92)
        
        try:
            
            subsampling_value = GetJpegSubsamplingRaw( pil_image )
            
            if subsampling_value == 0: # 444
                
                pass
                
            elif subsampling_value == 1: # 422
                
                quality = quality ** ( 1 / 0.92 )
                
            elif subsampling_value == 2: # 420
                
                quality = quality ** ( 1 / 0.85 )
                
            else: # who knows, but probably crazy
                
                quality = quality ** ( 1 / 0.75 )
                
            
        except:
            
            pass
            
        
        # this used to be ad-hoc but it was fairly exponential, now I made it 0.7 ratio for every step
        
        if quality >= 2800:
            
            label = 'very low'
            
        elif quality >= 2000:
            
            label = 'low'
            
        elif quality >= 1400:
            
            label = 'medium low'
            
        elif quality >= 1000:
            
            label = 'medium'
            
        elif quality >= 700:
            
            label = 'medium high'
            
        elif quality >= 480:
            
            label = 'high'
            
        elif quality >= 330:
            
            label = 'very high'
            
        else:
            
            label = 'extremely high'
            
        
        return ( label, quality )
        
    
    return ( 'unknown', None )
    

subsampling_value_lookup = {
    '4:4:4' : 1.00,
    '4:2:2' : 0.93,
    '4:2:0' : 0.83,
    'unknown' : 0.75
}

def GetJpegSubsamplingRaw( pil_image: PILImage.Image ) -> int:
    
    from PIL import JpegImagePlugin
    
    result = JpegImagePlugin.get_sampling( pil_image )
    
    return result
    

def GetJpegSubsampling( pil_image: PILImage.Image ) -> str:
    
    result = GetJpegSubsamplingRaw( pil_image )
    
    subsampling_str_lookup = {
        0 : '4:4:4',
        1 : '4:2:2',
        2 : '4:2:0'
    }
    
    return subsampling_str_lookup.get( result, 'unknown' )
    

def HasEXIF( pil_image: PILImage.Image ) -> bool:
    
    result = GetEXIFDict( pil_image )
    
    return result is not None
    

def HasHumanReadableEmbeddedMetadata( pil_image: PILImage.Image ) -> bool:
    
    result = GetEmbeddedFileText( pil_image )
    
    return result is not None
    

def HasICCProfile( pil_image: PILImage.Image ) -> bool:
    
    if 'icc_profile' in pil_image.info:
        
        icc_profile = pil_image.info[ 'icc_profile' ]
        
        if isinstance( icc_profile, bytes ) and len( icc_profile ) > 0:
            
            return True
            
        
    
    return False
    
