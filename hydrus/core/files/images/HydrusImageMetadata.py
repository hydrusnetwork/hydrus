import base64
import json
from PIL import Image as PILImage

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions

def render_char_card( chara_text: str, indent_depth: int ) -> str:
    
    try:
        
        card_json = json.loads( base64.b64decode( chara_text ).decode( 'utf-8' ) )
        
    except Exception as e:
        
        return render_key_value( indent_depth, 'chara', chara_text )
        
    
    if isinstance( card_json, dict ):
        
        spec = { 'spec': 'chara_card_v2', 'spec_version': '2.0' }
        
        if any( ( item in card_json.items() for item in spec.items() ) ):
            
            key = 'Character Card'
            
            # this is so ugly to achieve the propagation to lower levels but whatever
            return render_key_value( indent_depth, key, card_json, keys_to_put_at_the_top = [ 'name', 'description', 'personality' ] )
            
        
    
    return render_key_value( indent_depth, 'Character Card?', card_json )
    

def render_dict( d: dict, indent_depth: int, keys_to_put_at_the_top = None, ignore_these_keys = None ) -> str | None:
    
    if keys_to_put_at_the_top is None:
        
        keys_to_put_at_the_top = []
        
    
    if ignore_these_keys is None:
        
        ignore_these_keys = set()
        
    
    def muh_sort( k ):
        
        if k in keys_to_put_at_the_top:
            
            return ( 0, keys_to_put_at_the_top.index( k ), k )
            
        else:
            
            return ( 1, 0, k )
            
        
    
    texts = []
    
    keys = sorted( d.keys(), key = muh_sort )
    
    if indent_depth == 0 and 'chara' in keys:
        
        keys.remove( 'chara' )
        
        texts.append( render_char_card( d[ 'chara' ], indent_depth ) )
        
    
    for key in keys:
        
        if key in ignore_these_keys:
            
            continue
            
        
        value = d[ key ]
        
        if isinstance( value, bytes ):
            
            continue
            
        
        row_text = render_key_value( indent_depth, key, value, keys_to_put_at_the_top = keys_to_put_at_the_top )
        
        texts.append( row_text )
        
    
    if len( texts ) > 0:
        
        return '\n'.join( texts )
        
    else:
        
        return None
        
    

def render_key_value( indent_depth, key, value, keys_to_put_at_the_top = None ) -> str:
    
    if keys_to_put_at_the_top is None:
        
        keys_to_put_at_the_top = []
        
    
    indent = '    '
    
    if isinstance( value, dict ):
        
        value_string = render_dict( value, indent_depth = indent_depth + 1, keys_to_put_at_the_top = keys_to_put_at_the_top )
        
        if value_string is None:
            
            value_string = '{}{}'.format( indent * ( indent_depth + 1 ), 'empty/unknown' )
            
        
    elif isinstance( value, bytes ):
        
        raw_value = f'{HydrusData.ToHumanBytes(len(value))} of data'
        
        value_string = ( indent * ( indent_depth + 1 ) ) + raw_value
        
    else:
        
        raw_value = f'{value}'
        raw_value_lines = raw_value.splitlines()
        indented_lines = [ ( indent * ( indent_depth + 1 ) ) + line for line in raw_value_lines ]
        
        value_string = '\n'.join( indented_lines )
        
    
    row_text = '{}{}:'.format( indent * indent_depth, key )
    row_text += '\n'
    row_text += value_string
    
    return row_text
    

# we parse and display this stuff in other places
PIL_INFO_KEYS_THAT_ARE_NOT_CONSIDERED_HUMAN_READABLE_STUFF = {
    'exif',
    'icc_profile',
    'progression',
    'progressive',
    'srgb',
    'gamma',
    'chromaticity',
    'dpi',
    'jfif',
    'jfif_unit',
    'jfif_density',
    'jfif_version',
    'compression',
    'resolution',
}

def GetEmbeddedFileText( pil_image: PILImage.Image ) -> str | None:
    
    # OK WE DISCOVERED AN IMAGE THAT DID NOT FLESH OUT ITS info DICT UNTIL IT WAS LOADED
    # I guess sometimes that stuff lives in the frame rather than header data
    # this guy is apparently idempotent so we'll call it here to ensure we are getting a more decent shot
    pil_image.load()
    
    if hasattr( pil_image, 'info' ):
        
        try:
            
            info_dict = pil_image.info.copy()
            
            return render_dict( info_dict, indent_depth = 0, ignore_these_keys = PIL_INFO_KEYS_THAT_ARE_NOT_CONSIDERED_HUMAN_READABLE_STUFF )
            
        except Exception as e:
            
            pass
            
        
    
    return None
    

def GetEXIFDict( pil_image: PILImage.Image ) -> dict | None:
    
    if pil_image.format in ( 'JPEG', 'JXL', 'TIFF', 'PNG', 'WEBP', 'HEIF', 'AVIF', 'MPO' ):
        
        try:
            
            exif_dict = pil_image.getexif()._get_merged_dict()
            
            if len( exif_dict ) > 0:
                
                return exif_dict
                
            
        except Exception as e:
            
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
            
            quality = quality ** ( 1 / subsampling_quality_lookup[ subsampling_value ] )
            
        except Exception as e:
            
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
    

# these first three line up with PIL, so don't change them
SUBSAMPLING_444 = 0
SUBSAMPLING_422 = 1
SUBSAMPLING_420 = 2
SUBSAMPLING_UNKNOWN = 3
SUBSAMPLING_GREYSCALE = 4

# broad relative quality of a particular subsampling against another
subsampling_quality_lookup = {
    SUBSAMPLING_444 : 1.00,
    SUBSAMPLING_422 : 0.93,
    SUBSAMPLING_420 : 0.83,
    SUBSAMPLING_UNKNOWN : 0.75,
    SUBSAMPLING_GREYSCALE : 0.967 # through the power of experimental magic, comparing RGB vs L greyscale conversions and relative quantization table strength, I have determined this is ok
}

subsampling_str_lookup = {
    SUBSAMPLING_444 : '4:4:4',
    SUBSAMPLING_422 : '4:2:2',
    SUBSAMPLING_420 : '4:2:0',
    SUBSAMPLING_UNKNOWN : 'unknown',
    SUBSAMPLING_GREYSCALE : 'greyscale (no subsampling)'
}

def GetJpegSubsamplingRaw( pil_image: PILImage.Image ) -> int:
    
    if pil_image.mode == 'L':
        
        return SUBSAMPLING_GREYSCALE
        
    
    from PIL import JpegImagePlugin
    
    result = JpegImagePlugin.get_sampling( pil_image )
    
    if result not in ( 0, 1, 2 ):
        
        return SUBSAMPLING_UNKNOWN
        
    
    return result
    

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
    
