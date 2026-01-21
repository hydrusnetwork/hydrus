import traceback

TLDEXTRACT_OK = True
TLDEXTRACT_MODULE_NOT_FOUND = False
TLDEXTRACT_IMPORT_ERROR = 'tldextract seems fine!'

try:
    
    import tldextract
    
except Exception as e:
    
    TLDEXTRACT_OK = False
    TLDEXTRACT_MODULE_NOT_FOUND = isinstance( e, ModuleNotFoundError )
    TLDEXTRACT_IMPORT_ERROR = traceback.format_exc()
    

def ConvertDomainIntoSecondLevelDomain( domain: str ):
    
    if not TLDEXTRACT_OK:
        
        raise Exception( 'Sorry, this client needs tldextract in its venv! You should not see this message!' )
        
    
    # this guy offers '_under_registry_suffix', which is like blogspot.com, not the 'strict' TLD we are looking for atm
    return tldextract.extract( domain ).top_domain_under_public_suffix
    

def ConvertDomainIntoTopLevelDomain( domain: str ):
    
    if not TLDEXTRACT_OK:
        
        raise Exception( 'Sorry, this client needs tldextract in its venv! You should not see this message!' )
        
    
    return tldextract.extract( domain ).suffix
    
