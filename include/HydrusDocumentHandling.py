from . import HydrusConstants as HC
#import PyPDF2
import re
import time
import traceback

def GetNumWordsFromString( s ):
    
    s = re.sub( '[\s]+', ' ', s ) # turns multiple spaces into single spaces
    
    num_words = len( s.split( ' ' ) )
    
    return num_words
    
def GetPDFNumWords( path ):
    
    # I discovered a pdf that pulled this into an infinite loop due to malformed header.
    # This gives bunk data anyway, so let's just cut it out until we have a better solution here all around
    
    return None
    
    try:
        
        pass
        '''
        with open( path, 'rb' ) as f:
            
            pdf_object = PyPDF2.PdfFileReader( f, strict = False )
            
            # get.extractText() gives kooky and unreliable results
            # num_words = sum( [ GetNumWordsFromString( page.extractText() ) for page in pdf_object.pages ] )
            
            # so let's just estimate
            
            return pdf_object.numPages * 350
            
        '''
    except:
        
        num_words = 0
        
    
    return num_words
    
