try:
    
    import chardet
    
    CHARDET_OK = True
    
except:
    
    CHARDET_OK = False
    
import json
import os
import re

from hydrus.core import HydrusExceptions

re_newlines = re.compile( '[\r\n]+' )
re_multiple_spaces = re.compile( r'\s+' )
# want to keep the 'leading space' part here, despite tag.strip() elsewhere, in case of some crazy '- test' tag
re_leading_space_or_garbage = re.compile( r'^(\s|-|system:)+' )
re_leading_single_colon = re.compile( '^:(?!:)' )
re_leading_byte_order_mark = re.compile( '^\ufeff' ) # unicode .txt files prepend with this, wew

HYDRUS_NOTE_NEWLINE = '\n'

def CleanNoteText( t: str ):
    
    # trim leading and trailing whitespace
    
    t = t.strip()
    
    # wash all newlines to be os.linesep
    
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
            
            text = '{}\u2026{}'.format( text[ : max_length - ( 1 + CENTER_END_CHARS ) ], text[ - CENTER_END_CHARS : ] )
            
        else:
            
            text = '{}\u2026'.format( text[ : max_length - 1 ] )
            
        
    
    return text
    
def LooksLikeHTML( file_data ):
    # this will false-positive if it is json that contains html, ha ha
    
    if isinstance( file_data, bytes ):
        
        search_elements = ( b'<html', b'<HTML', b'<title', b'<TITLE' )
        
    else:
        
        search_elements = ( '<html', '<HTML', '<title', '<TITLE' )
        
    
    for s_e in search_elements:
        
        if s_e in file_data:
            
            return True
            
        
    
    return False
    
def LooksLikeJSON( file_data ):
    
    try:
        
        if isinstance( file_data, bytes ):
            
            file_data = str( file_data, 'utf-8' )
            
        
        json.loads( file_data )
        
        return True
        
    except:
        
        return False
        
    

UNICODE_REPLACEMENT_CHARACTER = u'\ufffd'
NULL_CHARACTER = '\x00'

def ChardetDecode( data ):
    
    chardet_result = chardet.detect( data )
    
    chardet_confidence = chardet_result[ 'confidence' ]
    
    chardet_encoding = chardet_result[ 'encoding' ]
    
    chardet_text = str( data, chardet_encoding, errors = 'replace' )
    
    chardet_error_count = chardet_text.count( UNICODE_REPLACEMENT_CHARACTER )
    
    return ( chardet_text, chardet_encoding, chardet_confidence, chardet_error_count )

def DefaultDecode( data ):
    
    default_encoding = 'windows-1252'
    
    default_text = str( data, default_encoding, errors = 'replace' )
    
    default_error_count = default_text.count( UNICODE_REPLACEMENT_CHARACTER )
    
    return ( default_text, default_encoding, default_error_count )
    
def NonFailingUnicodeDecode( data, encoding ):
    
    text = None
    
    try:
        
        if encoding in ( 'ISO-8859-1', 'Windows-1252', None ):
            
            # ok, the site delivered one of these non-utf-8 'default' encodings. this is probably actually requests filling this in as default
            # we don't want to trust these because they are very permissive sets and'll usually decode garbage without errors
            # we want chardet to have a proper look
            
            raise LookupError()
            
        
        text = str( data, encoding )
        
    except ( UnicodeDecodeError, LookupError ) as e:
        
        try:
            
            if isinstance( e, UnicodeDecodeError ):
                
                text = str( data, encoding, errors = 'replace' )
                
                confidence = 0.7
                error_count = text.count( UNICODE_REPLACEMENT_CHARACTER )
                
            else:
                
                confidence = None
                error_count = None
                
            
            if CHARDET_OK:
                
                ( chardet_text, chardet_encoding, chardet_confidence, chardet_error_count ) = ChardetDecode( data )
                
                if chardet_error_count == 0:
                    
                    chardet_is_better = True
                    
                else:
                    
                    chardet_confidence_is_better = confidence is None or chardet_confidence > confidence
                    chardet_errors_is_better = error_count is None or chardet_error_count < error_count
                    
                    chardet_is_better = chardet_confidence_is_better and chardet_errors_is_better
                    
                
                if chardet_is_better:
                    
                    text = chardet_text
                    encoding = chardet_encoding
                    
                
            else:
                
                if text is None:
                    
                    try:
                        
                        ( default_text, default_encoding, default_error_count ) = DefaultDecode( data )
                        
                        text = default_text
                        encoding = default_encoding
                        
                    except:
                        
                        text = 'Could not decode the page--problem with given encoding "{}" and no chardet library available.'.format( encoding )
                        encoding = 'utf-8'
                        
                    
                
            
            if text is None:
                
                raise Exception()
                
            
        except Exception as e:
            
            text = 'Unfortunately, could not decode the page with given encoding "{}".'.format( encoding )
            encoding = 'utf-8'
            
        
    
    if NULL_CHARACTER in text:
        
        # I guess this is valid in unicode for some reason
        # funnily enough, it is not replaced by 'replace'
        # nor does it raise an error in normal str creation
        
        text = text.replace( NULL_CHARACTER, '' )
        
    
    return ( text, encoding )
    
def RemoveNewlines( text ):
    
    text = re.sub( r'[\r\n]', '', text )
    
    return text
    
def SortStringsIgnoringCase( list_of_strings ):
    
    list_of_strings.sort( key = lambda s: s.lower() )
    
def StripIOInputLine( t ):
    
    t = re_leading_byte_order_mark.sub( '', t )
    
    t = t.strip()
    
    return t
    
