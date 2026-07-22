import os.path
import threading
import traceback

from pathlib import Path

from hydrus.core import HydrusStaticDir

TLDEXTRACT_OK = True
TLDEXTRACT_MODULE_NOT_FOUND = False
TLDEXTRACT_IMPORT_ERROR = 'tldextract seems fine!'

# came from https://publicsuffix.org/list/public_suffix_list.dat
SUFFIX_LIST_PATH = HydrusStaticDir.GetStaticPath( 'public_suffix_list.dat' )

try:
    
    import tldextract
    
    if not os.path.exists( SUFFIX_LIST_PATH ):
        
        raise Exception( 'I tried to initialise tldextract, but there was no "public_suffix_list.dat" file in the static dir!' )
        
    
except Exception as e:
    
    TLDEXTRACT_OK = False
    TLDEXTRACT_MODULE_NOT_FOUND = isinstance( e, ModuleNotFoundError )
    TLDEXTRACT_IMPORT_ERROR = traceback.format_exc()
    

class TLDExtractor( object ):
    
    my_instance = None
    
    def __init__( self ):
        
        # if you just spawn this guy, he goes and uses requests to pull from publicsuffix.org and/or their github repo and stashes it in ~/.cache/blah
        # if you say 'hey do not check any URLs', it'll just gen a new json structure from its own internal snapshot it ships with
        # I also add a copy in static dir and give it that URI as first thing to check since I'm pretty sure the frozen releases do not have it
        # you can say 'do not cache' by setting the cache_dir to None. this is a big 300KB structure, but it doesn't seem to be a problem in testing and we now re-use it
        
        suffix_list_urls = [ Path( SUFFIX_LIST_PATH ).resolve().as_uri() ]
        
        self._extractor = tldextract.TLDExtract( suffix_list_urls = suffix_list_urls, cache_dir = None )
        self._lock = threading.Lock()
        
    
    @staticmethod
    def instance() -> 'TLDExtractor':
        
        if not TLDEXTRACT_OK:
            
            raise Exception( 'Sorry, this client needs tldextract in its venv! You should not see this message!' )
            
        
        if TLDExtractor.my_instance is None:
            
            TLDExtractor.my_instance = TLDExtractor()
            
        
        return TLDExtractor.my_instance
        
    
    def extract( self, domain: str ):
        
        with self._lock:
            
            return self._extractor( domain )
            
        
    

def ConvertDomainIntoSecondLevelDomain( domain: str ):
    
    # this guy offers '_under_registry_suffix' too, which is like blogspot.com, not the 'strict' TLD we are looking for atm
    return TLDExtractor.instance().extract( domain ).top_domain_under_public_suffix
    

def ConvertDomainIntoTopLevelDomain( domain: str ):
    
    return TLDExtractor.instance().extract( domain ).suffix
    
