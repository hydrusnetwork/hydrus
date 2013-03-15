import cStringIO
import HydrusConstants as HC
import PyPDF2
import re
import time
import traceback
import wx

def GetNumWordsFromString( s ):
    
    s = re.sub( '[\s]+', ' ', s, flags = re.UNICODE ) # turns multiple spaces into single spaces
    
    num_words = len( s.split( ' ' ) )
    
    return num_words
    
def GetPDFNumWords( file ):
    
    try:
        
        pdf_object = PyPDF2.PdfFileReader( cStringIO.StringIO( file ), strict = False )
        
        # get.extractText() gives kooky and unreliable results
        # num_words = sum( [ GetNumWordsFromString( page.extractText() ) for page in pdf_object.pages ] )
        
        # so let's just estimate
        
        return pdf_object.numPages * 350
        
    except: num_words = 0
    
    return num_words
    