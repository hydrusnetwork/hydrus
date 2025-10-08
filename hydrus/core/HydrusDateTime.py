import datetime
import sys

def nowutc():
    
    if sys.version_info < ( 3, 11 ):
        
        # noinspection PyDeprecation
        return datetime.datetime.utcnow()
        
    else:
        
        return datetime.datetime.now( datetime.UTC )
        
    

def fromtimestamputc( timestamp ):
    
    if sys.version_info < ( 3, 11 ):
        
        # noinspection PyDeprecation
        return datetime.datetime.utcfromtimestamp( timestamp )
        
    else:
        
        return datetime.datetime.fromtimestamp( timestamp, datetime.UTC )
        
    
