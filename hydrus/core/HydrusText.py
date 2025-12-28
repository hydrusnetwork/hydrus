import collections.abc

try:
    
    import chardet
    
    CHARDET_OK = True
    
except:
    
    CHARDET_OK = False
    

import json
import re

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusNumbers

re_one_or_more_whitespace = re.compile( r'\s+' ) # this does \t and friends too
# want to keep the 'leading space' part here, despite tag.strip() elsewhere, in case of some crazy '- test' tag
re_leading_garbage = re.compile( r'^(-|system:)+' )
re_leading_single_colon = re.compile( '^:(?!:)' )
re_leading_single_colon_and_no_more_colons = re.compile( '^:(?=[^:]+$)' )
re_leading_single_colon_and_later_colon = re.compile( '^:(?=[^:]+:[^:]+$)' )
re_leading_double_colon = re.compile( '^::(?!:)' )
re_leading_colons = re.compile( '^:+' )
re_leading_byte_order_mark = re.compile( '^' + HC.UNICODE_BYTE_ORDER_MARK ) # unicode .txt files prepend with this, wew

# Control Character definitions
# easy answer is they are all fairly horrible, but ZWNJ and ZWJ (zero-width joiner stuff) are useful for hangul and arabic rendering etc...

# ZWNJ and ZWJ: [\u200C\u200D]

# c0 and c1 (newline, tab, "ring bell", "start of selection"): [\u0000-\u001F\u007F-\u009F]
# cf (right-to-left, "bidi", BOM), but allowing ZWNJ and ZWJ: [\u200B\u200E\u200F\u202A-\u202E\u2066-\u2069\ufeff]
# co (private use): [\uE000-\uF8FF\U000F0000-\U000FFFFD\U00100000-\U0010FFFD]
# cs (surrogates): [\uD800-\uDFFF]
# there's also "unassigned", but to chase that up we have to test each char against unicodedata library. we'll never solve that perfectly, so let's just go breddy gud for now

re_undesired_control_characters = re.compile( r'[\u0000-\u001F\u007F-\u009F\u200B\u200E\u200F\u202A-\u202E\u2066-\u2069\ufeff\uE000-\uF8FF\U000F0000-\U000FFFFD\U00100000-\U0010FFFD\uD800-\uDFFF]' )
re_oops_all_zero_width_joiners = re.compile( r'^[\u200C\u200D]+$' )
re_zero_width_joiners = re.compile( r'[\u200C\u200D]' )

re_has_surrogate_garbage = re.compile( r'[\ud800-\udfff]' )

re_this_is_all_latin_and_zero_width = re.compile( r'^[\u0020-\u007E\u00A0-\u024F\u200C\u200D]+$' ) # ascii block, normal symbols, and regular euro accented characters

# korean uses these pretty much: [\u1100-\u11FF\uAC00-\uD7AF]

re_looks_like_hangul = re.compile( r'[\u1100-\u11FF\uAC00-\uD7AF]' )
HANGUL_FILLER_CHARACTER = '\u3164'

# there's some more CJK, mongolian, and braille in the style of the hangul filler character if we want to keep at this

HYDRUS_NOTE_NEWLINE = '\n'

def CleanseImportText( text: str ):
    
    # the website has placed utf-16 characters here due to a failure to encode some emoji properly
    # we try to fix it
    if re_has_surrogate_garbage.search( text ) is not None:
        
        try:
            
            return text.encode( 'utf-16', 'surrogatepass' ).decode( 'utf-16' )
            
        except:
            
            import HydrusData
            
            HydrusData.Print( f'Could not cleanse surrogates from this: {text}' )
            
        
    
    return text
    

def CleanseImportTexts( texts: collections.abc.Collection[ str ] ):
    
    return [ CleanseImportText( text ) for text in texts ]
    

def CleanNoteText( t: str ):
    
    # trim leading and trailing whitespace
    
    t = t.strip()
    
    # wash all newlines
    
    lines = t.splitlines()
    
    # now trim each line
    
    lines = [ line.strip() for line in lines ]
    
    t = HYDRUS_NOTE_NEWLINE.join( lines )
    
    # now replace big gaps with reasonable ones
    
    double_newline = HYDRUS_NOTE_NEWLINE * 2
    triple_newline = HYDRUS_NOTE_NEWLINE * 3
    
    while triple_newline in t:
        
        t = t.replace( triple_newline, double_newline )
        
    
    return t
    

def ConvertManyStringsToNiceInsertableHumanSummary( texts: collections.abc.Collection[ str ], do_sort: bool = True, no_trailing_whitespace = False ) -> str:
    """
    The purpose of this guy is to convert your list of 20 subscription names or whatever to something you can present to the user without making a giganto tall dialog.
    """
    texts = list( texts )
    
    if do_sort:
        
        HumanTextSort( texts )
        
    
    if len( texts ) == 1:
        
        if no_trailing_whitespace:
            
            return f' "{texts[0]}"'
            
        else:
            
            return f' "{texts[0]}" '
            
        
    else:
        
        if len( texts ) <= 4:
            
            t = '\n'.join( texts )
            
        else:
            
            LINE_NO_LONGER_THAN = 64
            NUM_LINES_LIMIT = 24
            
            lines = []
            line_under_construction = ''
            
            texts_to_do = list( texts )
            
            while len( texts_to_do ) > 0:
                
                text = texts_to_do.pop( 0 )
                
                if line_under_construction == '':
                    
                    line_under_construction = text
                    
                else:
                    
                    potential_next_line = f'{line_under_construction}, {text}'
                    
                    if len( potential_next_line ) > LINE_NO_LONGER_THAN:
                        
                        lines.append( line_under_construction )
                        
                        if len( lines ) >= NUM_LINES_LIMIT:
                            
                            line_under_construction = ''
                            texts_to_do.insert( 0, text )
                            
                            lines.append( f'and {HydrusNumbers.ToHumanInt( len( texts_to_do ) )} others' )
                            
                            break
                            
                        else:
                            
                            line_under_construction = text
                            
                        
                    else:
                        
                        line_under_construction = potential_next_line
                        
                    
                
            
            if len( line_under_construction ) > 0:
                
                lines.append( line_under_construction )
                
            
            t = '\n'.join( lines )
            
        
        if no_trailing_whitespace:
            
            return f'\n\n{t}'
            
        else:
            
            return f'\n\n{t}\n\n'
            
        
    

def ConvertManyStringsToNiceInsertableHumanSummarySingleLine( texts: collections.abc.Collection[ str ], collective_description_noun: str, do_sort: bool = True ) -> str:
    """
    The purpose of this guy is to convert your list of 20 subscription names or whatever to something you can present to the user without making a giganto tall dialog.
    Suitable for a menu!
    """
    if len( texts ) == 0:
        
        return f'0(?) {collective_description_noun}'
        
    
    texts = list( texts )
    
    if do_sort:
        
        HumanTextSort( texts )
        
    
    LINE_NO_LONGER_THAN = 48
    
    if len( texts ) == 1:
        
        text = texts[0]
        
        if len( text ) + 2 > LINE_NO_LONGER_THAN:
            
            return f'1 {collective_description_noun}'
            
        else:
            
            return f'"{text}"'
            
        
    else:
        
        full_result = ', '.join( ( f'"{text}"' for text in texts ) )
        
        if len( full_result ) <= LINE_NO_LONGER_THAN:
            
            return full_result
            
        else:
            
            first_text = texts[0]
            num_texts = len( texts )
            
            leading_example_result = f'"{first_text}" & {HydrusNumbers.ToHumanInt( num_texts - 1 )} other {collective_description_noun}'
            
            if len( leading_example_result ) <= LINE_NO_LONGER_THAN:
                
                return leading_example_result
                
            else:
                
                return f'{HydrusNumbers.ToHumanInt( num_texts )} {collective_description_noun}'
                
            
        
    

def HexFilter( text ):
    
    text = text.lower()
    
    text = re.sub( '[^0123456789abcdef]', '', text )
    
    return text
    
def DeserialiseNewlinedTexts( text ):
    
    texts = text.splitlines()
    
    texts = [ StripIOInputLine( line ) for line in texts ]
    
    texts = [ line for line in texts if line != '' ]
    
    return texts
    
def ElideText( text, max_length, elide_center = False ):
    
    if len( text ) > max_length:
        
        if elide_center:
            
            CENTER_END_CHARS = max( 2, max_length // 8 )
            
            text = '{}{}{}'.format( text[ : max_length - ( 1 + CENTER_END_CHARS ) ], HC.UNICODE_ELLIPSIS, text[ - CENTER_END_CHARS : ] )
            
        else:
            
            text = '{}{}'.format( text[ : max_length - 1 ], HC.UNICODE_ELLIPSIS )
            
        
    
    return text
    

def GetFirstLine( text: str | None ) -> str:
    
    if text is None:
        
        return 'unknown'
        
    
    if len( text ) > 0:
        
        return text.splitlines()[0]
        
    else:
        
        return ''
        
    

def GetFirstLineSummary( text: str | None ) -> str:
    
    if text is None:
        
        return 'unknown'
        
    
    if len( text ) > 0:
        
        lines = text.splitlines()
        
        if len( lines ) > 1:
            
            return lines[0] + HC.UNICODE_ELLIPSIS + f' (+{HydrusNumbers.ToHumanInt(len( lines) - 1)} lines)'
            
        else:
            
            return text
            
        
    else:
        
        return ''
        
    

def GenerateHumanTextSortKey():
    """
    Solves the 19, 20, 200, 21, 22 issue when sorting 'Page 21.jpg' type strings.
    Breaks the string into groups of text and int (i.e. ( ( "Page ", 0 ), ( '', 21 ), ( ".jpg", 0 ) ) ).
    We declare that a number is earlier than text.
    """
    
    convert = lambda t: ( '', int( t ) ) if t.isdecimal() else ( t, 0 )
    
    split_alphanum = lambda t: tuple( ( convert( sub_t ) for sub_t in re.split( '([0-9]+)', t.casefold() ) ) )
    
    return split_alphanum
    

HumanTextSortKey = GenerateHumanTextSortKey()

def HumanTextSort( texts ):
    
    texts.sort( key = HumanTextSortKey ) 
    

def LooksLikeHTML( file_data: str | bytes ):
    # this will false-positive if it is json that contains html, ha ha
    
    if isinstance( file_data, bytes ):
        
        search_elements = ( b'<html', b'<HTML', b'<!DOCTYPE html', b'<!DOCTYPE HTML' )
        
    else:
        
        search_elements = ( '<html', '<HTML', '<!DOCTYPE html', '<!DOCTYPE HTML' )
        
    
    for s_e in search_elements:
        
        if s_e in file_data:
            
            return True
            
        
    
    return False

def LooksLikeSVG( file_data ):
    
    if isinstance( file_data, bytes ):
        
        search_elements = ( b'<svg', b'<SVG', b'<!DOCTYPE svg', b'<!DOCTYPE SVG' )
        
    else:
        
        search_elements = ( '<svg', '<SVG', '<!DOCTYPE svg', '<!DOCTYPE SVG' )
        
    
    for s_e in search_elements:
        
        if s_e in file_data:
            
            return True
            
        
    
    return False
    

def LooksLikeJSON( file_data: str | bytes ) -> bool:
    
    try:
        
        if isinstance( file_data, bytes ):
            
            file_data = str( file_data, 'utf-8' )
            
        
        json.loads( file_data )
        
        return True
        
    except:
        
        return False
        
    

NULL_CHARACTER = '\x00'

def ChardetDecode( data ):
    
    chardet_result = chardet.detect( data )
    
    chardet_confidence = chardet_result[ 'confidence' ]
    
    chardet_encoding = chardet_result[ 'encoding' ]
    
    chardet_text = str( data, chardet_encoding, errors = 'replace' )
    
    chardet_error_count = chardet_text.count( HC.UNICODE_REPLACEMENT_CHARACTER )
    
    return ( chardet_text, chardet_encoding, chardet_confidence, chardet_error_count )

def DefaultDecode( data ):
    
    default_encoding = 'windows-1252'
    
    default_text = str( data, default_encoding, errors = 'replace' )
    
    default_error_count = default_text.count( HC.UNICODE_REPLACEMENT_CHARACTER )
    
    return ( default_text, default_encoding, default_error_count )
    

# ISO is the official default I understand, absent an explicit declaration in http header or html document
# win-1252 is often assigned as an unofficial default after a scan suggests more complicated characters than the ISO
# I believe I have seen requests give both as default, but I am only super confident in the former
DEFAULT_WEB_ENCODINGS = ( 'ISO-8859-1', 'Windows-1252' )

def NonFailingUnicodeDecode( data, encoding, trust_the_encoding = False ):
    
    if trust_the_encoding:
        
        try:
            
            text = str( data, encoding, errors = 'replace' )
            
            return ( text, encoding )
            
        except:
            
            # ok, the encoding type wasn't recognised locally or something, so revert to trying our best
            encoding = None
            trust_the_encoding = False
            
        
    
    text = None
    confidence = None
    error_count = None
    
    try:
        
        ruh_roh_a = CHARDET_OK and encoding in DEFAULT_WEB_ENCODINGS
        ruh_roh_b = encoding is None
        
        if ruh_roh_a or ruh_roh_b:
            
            # ok, the site delivered one of these 'default' encodings. this is probably actually requests filling this in as default
            # we don't want to trust these because they are very permissive sets and'll usually decode garbage without errors
            # we want chardet to have a proper look and then compare them
            
            raise LookupError()
            
        
        text = str( data, encoding )
        
    except ( UnicodeDecodeError, LookupError ) as e:
        
        try:
            
            if encoding is not None:
                
                text = str( data, encoding, errors = 'replace' )
                
                confidence = 0.7
                error_count = text.count( HC.UNICODE_REPLACEMENT_CHARACTER )
                
            
            if CHARDET_OK:
                
                ( chardet_text, chardet_encoding, chardet_confidence, chardet_error_count ) = ChardetDecode( data )
                
                if chardet_error_count == 0:
                    
                    chardet_is_better = True
                    
                else:
                    
                    chardet_confidence_is_better = confidence is None or chardet_confidence > confidence
                    chardet_errors_is_as_good_or_better = error_count is None or chardet_error_count <= error_count
                    
                    chardet_is_better = chardet_confidence_is_better and chardet_errors_is_as_good_or_better
                    
                
                if chardet_is_better:
                    
                    text = chardet_text
                    encoding = chardet_encoding
                    
                
            
            if text is None:
                
                try:
                    
                    ( default_text, default_encoding, default_error_count ) = DefaultDecode( data )
                    
                    text = default_text
                    encoding = default_encoding
                    
                except:
                    
                    text = f'Could not decode the page--problem with given encoding "{encoding}" and no chardet library available.'
                    encoding = 'utf-8'
                    
                
            
            if text is None:
                
                raise Exception()
                
            
        except Exception as e:
            
            text = f'Unfortunately, could not decode the page with given encoding "{encoding}".'
            encoding = 'utf-8'
            
        
    
    if NULL_CHARACTER in text:
        
        # I guess this is valid in unicode for some reason
        # funnily enough, it is not replaced by 'replace'
        # nor does it raise an error in normal str creation
        
        text = text.replace( NULL_CHARACTER, '' )
        
    
    return ( text, encoding )
    

def RemoveNewlines( text: str ) -> str:
    
    good_lines = [ l.strip() for l in text.splitlines() ]
    
    good_lines = [ l for l in good_lines if l != '' ]
    
    # I really want to make this ' '.join(), but I'm sure that would break some old parsers
    text = ''.join( good_lines )
    
    return text
    

def StripIOInputLine( t ):
    
    t = re_leading_byte_order_mark.sub( '', t )
    
    t = t.strip()
    
    return t
    
