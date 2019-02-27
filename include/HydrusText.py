try:
    
    import chardet
    
    CHARDET_OK = True
    
except:
    
    CHARDET_OK = False
    
import json
import re

re_newlines = re.compile( '[\r\n]+' )
re_multiple_spaces = re.compile( '\\s+' )
re_leading_space_or_garbage = re.compile( '^(\\s|-|system:)+' )
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
        
    
def NonFailingUnicodeDecode( data, encoding ):
    
    try:
        
        text = str( data, encoding )
        
    except UnicodeDecodeError:
        
        unicode_replacement_character = u'\ufffd'
        
        text = str( data, encoding, errors = 'replace' )
        
        error_count = text.count( unicode_replacement_character )
        
        if CHARDET_OK:
            
            chardet_result = chardet.detect( data )
            
            if chardet_result[ 'confidence' ] > 0.85:
                
                chardet_encoding = chardet_result[ 'encoding' ]
                
                chardet_text = str( data, chardet_encoding, errors = 'replace' )
                
                chardet_error_count = chardet_text.count( unicode_replacement_character )
                
                if chardet_error_count < error_count:
                    
                    return ( chardet_text, chardet_encoding )
                    
                
            
        
    
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
    
