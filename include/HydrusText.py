import re

re_newlines = re.compile( '[\r\n]+', re.UNICODE )
re_multiple_spaces = re.compile( '\\s+', re.UNICODE )
re_trailing_space = re.compile( '\\s+$', re.UNICODE )
re_leading_space = re.compile( '^\\s+', re.UNICODE )
re_leading_space_or_garbage = re.compile( '^(\\s|-|system:)+', re.UNICODE )
re_leading_single_colon = re.compile( '^:(?!:)', re.UNICODE )
re_leading_byte_order_mark = re.compile( u'^\ufeff', re.UNICODE ) # unicode .txt files prepend with this, wew

def DeserialiseNewlinedTexts( text ):
    
    text = text.replace( '\r', '' )
    
    texts = text.split( '\n' )
    
    texts = [ StripTrailingAndLeadingSpaces( line ) for line in texts ]
    
    texts = [ line for line in texts if line != '' ]
    
    return texts
    
def SortStringsIgnoringCase( list_of_strings ):
    
    list_of_strings.sort( key = lambda s: s.lower() )
    
def StripTrailingAndLeadingSpaces( t ):
    
    t = re_leading_byte_order_mark.sub( '', t )
    
    t = re_trailing_space.sub( '', t )
    
    t = re_leading_space.sub( '', t )
    
    return t
    
