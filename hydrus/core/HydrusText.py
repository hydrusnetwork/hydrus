try:
    
    import chardet
    
    CHARDET_OK = True
    
except:
    
    CHARDET_OK = False
    
import json
import os
import re

re_newlines = re.compile( '[\r\n]+' )
re_multiple_spaces = re.compile( r'\s+' )
# want to keep the 'leading space' part here, despite tag.strip() elsewhere, in case of some crazy '- test' tag
re_leading_space_or_garbage = re.compile( r'^(\s|-|system:)+' )
re_leading_single_colon = re.compile( '^:(?!:)' )
re_leading_byte_order_mark = re.compile( '^\ufeff' ) # unicode .txt files prepend with this, wew

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
        
        search_elements = ( b'<html', b'<HTML' )
        
    else:
        
        search_elements = ( '<html', '<HTML' )
        
    
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

def NonFailingUnicodeDecode( data, encoding ):
    
    try:
        
        text = str( data, encoding )
        
    except UnicodeDecodeError:
        
        text = str( data, encoding, errors = 'replace' )
        
        error_count = text.count( UNICODE_REPLACEMENT_CHARACTER )
        
        if CHARDET_OK:
            
            chardet_result = chardet.detect( data )
            
            if chardet_result[ 'confidence' ] > 0.85:
                
                chardet_encoding = chardet_result[ 'encoding' ]
                
                chardet_text = str( data, chardet_encoding, errors = 'replace' )
                
                chardet_error_count = chardet_text.count( UNICODE_REPLACEMENT_CHARACTER )
                
                if chardet_error_count < error_count:
                    
                    if NULL_CHARACTER in chardet_text:
                        
                        chardet_text = chardet_text.replace( NULL_CHARACTER, '' )
                        
                    
                    return ( chardet_text, chardet_encoding )
                    
                
            
        
    
    if NULL_CHARACTER in text:
        
        # I guess this is valid in unicode for some reason
        # funnily enough, it is not replaced by 'replace'
        # nor does it raise an error in normal str creation
        
        text = text.replace( NULL_CHARACTER, '' )
        
    
    return ( text, encoding )
    
def RemoveNewlines( text ):
    
    text = re.sub( r'\r|\n', '', text )
    
    return text
    
def SortStringsIgnoringCase( list_of_strings ):
    
    list_of_strings.sort( key = lambda s: s.lower() )
    
def StripIOInputLine( t ):
    
    t = re_leading_byte_order_mark.sub( '', t )
    
    t = t.strip()
    
    return t
    
