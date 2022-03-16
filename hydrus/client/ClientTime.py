import typing

from hydrus.core import HydrusData

def ShouldUpdateDomainModifiedTime( existing_timestamp: int, new_timestamp: int ):
    
    # assume anything too early is a meme and a timestamp parsing conversion error
    if new_timestamp <= 86400 * 7:
        
        return False
        
    
    # only go backwards, in general
    if new_timestamp >= existing_timestamp:
        
        return False
        
    
    return True
    
def MergeModifiedTimes( existing_timestamp: typing.Optional[ int ], new_timestamp: typing.Optional[ int ] ) -> typing.Optional[ int ]:
    
    if existing_timestamp is None:
        
        return new_timestamp
        
    
    if new_timestamp is None:
        
        return existing_timestamp
        
    
    if ShouldUpdateDomainModifiedTime( existing_timestamp, new_timestamp ):
        
        return new_timestamp
        
    else:
        
        return existing_timestamp
        
    
