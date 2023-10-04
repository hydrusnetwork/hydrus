import os
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
            row_text += os.linesep
            row_text += value_string
            
            texts.append( row_text )
            
        
        if len( texts ) > 0:
            
            return os.linesep.join( texts )
            
        else:
            
            return None
            
        
    
    if hasattr( pil_image, 'info' ):
        
        try:
            
            return render_dict( pil_image.info, '' )
            
        except:
            
            pass
            
        
    
    return None
    

def GetEXIFDict( pil_image: PILImage.Image ) -> typing.Optional[ dict ]:
    
    if pil_image.format in ( 'JPEG', 'TIFF', 'PNG', 'WEBP', 'HEIF', 'AVIF', 'MPO' ):
        
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
        
        if quality >= 3400:
            
            label = 'very low'
            
        elif quality >= 2000:
            
            label = 'low'
            
        elif quality >= 1400:
            
            label = 'medium low'
            
        elif quality >= 1000:
            
            label = 'medium'
            
        elif quality >= 700:
            
            label = 'medium high'
            
        elif quality >= 400:
            
            label = 'high'
            
        elif quality >= 200:
            
            label = 'very high'
            
        else:
            
            label = 'extremely high'
            
        
        return ( label, quality )
        
    
    return ( 'unknown', None )
    

def GetJpegSubsampling( pil_image: PILImage.Image ) -> str:
    
    from PIL import JpegImagePlugin
    
    result = JpegImagePlugin.get_sampling( pil_image )
    
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
    
