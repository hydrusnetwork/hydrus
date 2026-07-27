import base64
import json
import re
from PIL import Image as PILImage

from hydrus.core import HydrusData
from hydrus.core import HydrusLists
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
    

def render_dict( d: dict, indent_depth: int, keys_to_put_at_the_top = None ) -> str | None:
    
    if keys_to_put_at_the_top is None:
        
        keys_to_put_at_the_top = []
        
    
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
    

def GetEmbeddedFileText( pil_image: PILImage.Image ) -> str | None:
    
    # OK WE DISCOVERED AN IMAGE THAT DID NOT FLESH OUT ITS info DICT UNTIL IT WAS LOADED
    # I guess sometimes that stuff lives in the frame rather than header data
    # this guy is apparently idempotent so we'll call it here to ensure we are getting a more decent shot
    pil_image.load()
    
    if hasattr( pil_image, 'info' ):
        
        try:
            
            info_dict = WashPilImageInfoDictForHumanReadableMetadata( pil_image.info.copy() )
            
            return render_dict( info_dict, indent_depth = 0 )
            
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

subsampling_misc_object_to_enum_lookup  = {
    '420' : SUBSAMPLING_420,
    420 : SUBSAMPLING_420,
    '422' : SUBSAMPLING_422,
    422 : SUBSAMPLING_422,
    '444' : SUBSAMPLING_444,
    444 : SUBSAMPLING_444,
}

def GetChromaSubsamplingFromPilInfo( pil_image: PILImage.Image ):
    
    pil_info = pil_image.info.copy()
    
    if 'chroma' in pil_info:
        
        chroma_object = pil_info[ 'chroma' ]
        
        if chroma_object in subsampling_misc_object_to_enum_lookup:
            
            return subsampling_misc_object_to_enum_lookup[ chroma_object ]
            
        
    
    return SUBSAMPLING_UNKNOWN
    

def GetJpegSubsamplingRaw( pil_image: PILImage.Image ) -> int:
    
    if pil_image.mode == 'L':
        
        return SUBSAMPLING_GREYSCALE
        
    
    from PIL import JpegImagePlugin
    
    result = JpegImagePlugin.get_sampling( pil_image )
    
    if result not in ( 0, 1, 2 ):
        
        return SUBSAMPLING_UNKNOWN
        
    
    return result
    

def GetSoftwareFromCommentInfoField( value ) -> str | None:
    
    if isinstance( value, str ):
        
        patterns = [
            r'^(Created|Converted|Cropped|Compressed|Edited) with (?P<software>.+)',
            r'^... (created|converted|cropped|compressed|edited) with (?P<software>.+)',
        ]
        
        for pattern in patterns:
            
            result = re.search( pattern, value )
            
            if result is not None:
                
                software = result[ 'software' ]
                
                return software
                
            
        
    
    return None
    

def GetSoftwareFromPilInfo( pil_image: PILImage.Image ) -> str | None:
    
    info_dict = pil_image.info.copy()
    
    components = []
    
    for key in [ 'Software', 'software' ]:
        
        if key in info_dict:
            
            components.append( info_dict[ key ] )
            
        
    
    if 'Comment' in info_dict or 'comment' in info_dict:
        
        if 'Comment' in info_dict:
            
            value = info_dict[ 'Comment' ]
            
        else:
            
            value = info_dict[ 'comment' ]
            
        
        software = GetSoftwareFromCommentInfoField( value )
        
        if software is not None:
            
            components.append( software )
            
        
    
    for key in [ 'Creator', 'creator', 'Source', 'source' ]:
        
        if key in info_dict:
            
            components.append( info_dict[ key ] )
            
        
    
    if 'Creator' in info_dict:
        
        components.append( info_dict[ 'Creator' ] )
        
    
    if 'Source' in info_dict:
        
        components.append( info_dict[ 'Source' ] )
        
    
    if len( components ) == 0:
        
        return None
        
    else:
        
        components = HydrusLists.DedupeList( components )
        
        return ' / '.join( [ str( c ) for c in components ] )
        
    

def HasEXIF( pil_image: PILImage.Image ) -> bool:
    
    result = GetEXIFDict( pil_image )
    
    return result is not None
    

def HasHumanReadableEmbeddedMetadata( pil_image: PILImage.Image ) -> bool:
    
    # we do a quick search first. if it has interesting data before the forced load call, we don't have to do any load
    if hasattr( pil_image, 'info' ):
        
        try:
            
            info_dict = WashPilImageInfoDictForHumanReadableMetadata( pil_image.info.copy() )
            
            result = render_dict( info_dict, indent_depth = 0 )
            
            if result is not None:
                
                return True
                
            
        except Exception as e:
            
            pass
            
        
    
    # OK WE DISCOVERED AN IMAGE THAT DID NOT FLESH OUT ITS info DICT UNTIL IT WAS LOADED
    # I guess sometimes that stuff lives in the frame rather than header data
    # this guy is apparently idempotent so we'll call it here to ensure we are getting a more decent shot
    pil_image.load()
    
    if hasattr( pil_image, 'info' ):
        
        try:
            
            info_dict = WashPilImageInfoDictForHumanReadableMetadata( pil_image.info.copy() )
            
            result = render_dict( info_dict, indent_depth = 0 )
            
            return result is not None
            
        except Exception as e:
            
            pass
            
        
    
    return False
    

def HasICCProfile( pil_image: PILImage.Image ) -> bool:
    
    if 'icc_profile' in pil_image.info:
        
        icc_profile = pil_image.info[ 'icc_profile' ]
        
        if isinstance( icc_profile, bytes ) and len( icc_profile ) > 0:
            
            return True
            
        
    
    return False
    

# we parse and display this stuff in other places
# ultimately I guess I should really find the three comment fields we want and whitelist them, rather than trying to blacklist every whack decoder field
# but I think I do fall on the side of 'yeah let's expose and put human eyes what crazy stuff is going on' so we discover new things
PIL_INFO_KEYS_THAT_ARE_NOT_CONSIDERED_HUMAN_READABLE_STUFF = {
    'exif',
    'Raw profile type exif',
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
    'Software', # this is cool and we'll def want to search it special one day, but it is not quite human-readable gubbins imo
    'software', # yeah I have seen both cases
    'adobe', # this is almost always '100' and isn't helpful
    'adobe_transform', # this is almost always '1', which is (jpeg) YCbCr
    'transparency', # we handle this elsewhere
    'background',
    'duration',
    'bit_depth',
    'primary', # heif "yeah this is the main image"
    'chroma', # "420" et al on a heif
    'loop',
    'photoshop', # this is actually a cool dict but it is either 1005 which has DPI we already pulled or bytes objects
    'extension', # ( b'NETSCAPE2.0', 419/795 ), gif thing about bytenum where frame starts
    'bbox', # apng gubbins
    'blend', # apng gubbins
    'disposal', # apng gubbins
    'sizes', # .ico gubbins
    'interlace',
    'aspect',
    'xmp', # xmp stuff
    'XML:com.adobe.xmp', # xmp stuff
    'iptc', # ye olde XMP
    'Raw profile type iptc', # ye olde XMP
    'default_image', #png thing
    'Creator',
    'creator',
    'Source',
    'source',
    'mpoffset',
    'Creation Time', # TODO: Woop woop, pull this for a noice modified time with like 'file metadata' as the 'domain'
    'create-date',
    'modify-date',
    'date:create',
    'date:modify',
    'Thumb::MTime', # leaving this here as a reminder for another source of modified time
}

def WashPilImageInfoDictForHumanReadableMetadata( info_dict: dict ) -> dict:
    
    new_info_dict = dict()
    
    for ( key, value ) in list( info_dict.items() ):
        
        if key in PIL_INFO_KEYS_THAT_ARE_NOT_CONSIDERED_HUMAN_READABLE_STUFF:
            
            continue
            
        
        if value is None:
            
            continue
            
        
        if isinstance( value, ( list, dict ) ) and len( value ) == 0:
            
            continue
            
        
        # we fetch this elsewhere
        if key in ( 'comment', 'Comment' ) and GetSoftwareFromCommentInfoField( value ) is not None:
            
            continue
            
        
        # some gif gubbins along with 'loop'
        if key == 'timestamp' and value == 0:
            
            continue
            
        
        if key.startswith( 'Thumb::' ):
            
            '''
Thumb::Document::Pages:
    1
Thumb::Image::Width:
    24
Thumb::Image::height:
    18
Thumb::MTime:
    1359601259
Thumb::Mimetype:
    image/png
Thumb::Size:
    701BB
Thumb::URI:
    file:///tmp/minimagick29295-7.png
'''
            
            continue
            
        
        new_info_dict[ key ] = value
        
    
    return new_info_dict
    

