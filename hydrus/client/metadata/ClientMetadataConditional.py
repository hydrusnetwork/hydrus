from hydrus.core import HydrusSerialisable

from hydrus.client.media import ClientMediaResult
from hydrus.client.search import ClientSearchPredicate

class MetadataConditional( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_METADATA_CONDITIONAL
    SERIALISABLE_NAME = 'Metadata Conditional'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        # starting this guy out nice and simple, just a wrapper for a system pred
        # future versions of this object could hold multiple system preds or whatever
        
        self._predicate = ClientSearchPredicate.SYSTEM_PREDICATE_INBOX
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_predicate = self._predicate.GetSerialisableTuple()
        
        return serialisable_predicate
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_predicate = serialisable_info
        
        self._predicate = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_predicate )
        
    
    def GetPredicate( self ) -> ClientSearchPredicate.Predicate:
        
        return self._predicate
        
    
    def GetSummary( self ):
        
        return self._predicate.ToString()
        
    
    def SetPredicate( self, predicate: ClientSearchPredicate.Predicate ):
        
        self._predicate = predicate
        
    
    def Test( self, media_result: ClientMediaResult.MediaResult ) -> bool:
        
        if self._predicate.CanTestMediaResult():
            
            return self._predicate.TestMediaResult( media_result )
            
        
        raise NotImplementedError( f'The given predicate, "{self._predicate.ToString()}", cannot test a media result! You should not be able to this situation, so please contact hydev with details.' )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_METADATA_CONDITIONAL ] = MetadataConditional
