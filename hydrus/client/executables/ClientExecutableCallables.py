from hydrus.core import HydrusData
from hydrus.core import HydrusSerialisable

from hydrus.client.executables import ClientExecutableActualCall
from hydrus.client.executables import ClientExecutablePipelines

class ClientExecutableCallable( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALLABLE
    SERIALISABLE_NAME = 'Executable Manager Callable'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name: str, pipeline_type: int | None = None, actual_call: ClientExecutableActualCall.ExecutableActualCall | None = None ):
        
        super().__init__( name )
        
        if pipeline_type is None:
            
            pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE
            
        
        if actual_call is None:
            
            actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate()
            
        
        self._callable_key = HydrusData.GenerateKey()
        self._pipeline_type = pipeline_type
        self._actual_call = actual_call
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_callable_key = self._callable_key.hex()
        serialisable_actual_call = self._actual_call.GetSerialisableTuple()
        
        return (
            serialisable_callable_key,
            self._pipeline_type,
            serialisable_actual_call,
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            serialisable_callable_key,
            self._pipeline_type,
            serialisable_actual_call,
        ) = serialisable_info
        
        self._callable_key = bytes.fromhex( serialisable_callable_key )
        self._actual_call = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_actual_call )
        
    
    def Call( self, input_params ):
        
        return self._actual_call.Call( input_params )
        
    
    def GenerateNewCallableKey( self ):
        
        self._callable_key = HydrusData.GenerateKey()
        
    
    def GetCall( self ):
        
        return self._actual_call
        
    
    def GetCallableKey( self ):
        
        return self._callable_key
        
    
    def GetIdAndName( self ):
        
        return HydrusSerialisable.IdAndName( object_id = self._callable_key, name = self._name )
        
    
    def GetPipelineType( self ):
        
        return self._pipeline_type
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALLABLE ] = ClientExecutableCallable
