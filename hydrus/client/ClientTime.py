import typing

def ShouldUpdateDomainModifiedTime( existing_timestamp: int, new_timestamp: typing.Optional[ int ] ) -> bool:
    
    if not TimestampIsSensible( new_timestamp ):
        
        return False
        
    
    if not TimestampIsSensible( existing_timestamp ):
        
        return True
        
    
    # only go backwards, in general
    if new_timestamp >= existing_timestamp:
        
        return False
        
    
    return True
    
def MergeModifiedTimes( existing_timestamp: typing.Optional[ int ], new_timestamp: typing.Optional[ int ] ) -> typing.Optional[ int ]:
    
    if not TimestampIsSensible( existing_timestamp ):
        
        existing_timestamp = None
        
    
    if not TimestampIsSensible( new_timestamp ):
        
        new_timestamp = None
        
    
    if ShouldUpdateDomainModifiedTime( existing_timestamp, new_timestamp ):
        
        return new_timestamp
        
    else:
        
        return existing_timestamp
        
    

def TimestampIsSensible( timestamp: typing.Optional[ int ] ) -> bool:
    
    if timestamp is None:
        
        return False
        
    
    # assume anything too early is a meme and a timestamp parsing conversion error
    if timestamp <= 86400 * 7:
        
        return False
        
    
    return True
    
