from hydrus.core import HydrusData

def ShouldUpdateDomainModifiedTime( existing_timestamp: int, timestamp: int ):
    
    # assume anything too early is a meme and a timestamp parsing conversion error
    if timestamp <= 86400 * 7:
        
        return False
        
    
    # only go backwards, in general
    if timestamp >= existing_timestamp:
        
        return False
        
    
    return True
