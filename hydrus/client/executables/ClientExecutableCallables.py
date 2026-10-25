from hydrus.core import HydrusData
from hydrus.core import HydrusSerialisable

from hydrus.client.executables import ClientExecutableActualCall
from hydrus.client.executables import ClientExecutablePipelines
from hydrus.client.executables import ClientExecutableResponses
from hydrus.client.parsing import ClientParsing

class ClientExecutableCallable( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALLABLE
    SERIALISABLE_NAME = 'Executable Manager Callable'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, name: str, pipeline_type: int | None = None, actual_call: ClientExecutableActualCall.ExecutableActualCall | None = None ):
        
        super().__init__( name )
        
        if pipeline_type is None:
            
            pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_FILE
            
        
        if actual_call is None:
            
            actual_call = ClientExecutableActualCall.ExecutableLocalProcessCall()
            
        
        self._callable_key = HydrusData.GenerateKey()
        self._pipeline_type = pipeline_type
        self._actual_call = actual_call
        self._page_parser = ClientParsing.PageParser( 'response parser' )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_callable_key = self._callable_key.hex()
        serialisable_actual_call = self._actual_call.GetSerialisableTuple()
        serialisable_page_parser = self._page_parser.GetSerialisableTuple()
        
        return (
            serialisable_callable_key,
            self._pipeline_type,
            serialisable_actual_call,
            serialisable_page_parser,
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info: object, restricted_serialisable_types: set[ int ] | None ):
        
        (
            serialisable_callable_key,
            self._pipeline_type,
            serialisable_actual_call,
            serialisable_page_parser,
        ) = serialisable_info
        
        self._callable_key = bytes.fromhex( serialisable_callable_key )
        self._actual_call = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_actual_call )
        self._page_parser = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_page_parser )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            (
                serialisable_callable_key,
                pipeline_type,
                serialisable_actual_call,
            ) = old_serialisable_info
            
            page_parser = ClientParsing.PageParser( 'response parser' )
            
            serialisable_page_parser = page_parser.GetSerialisableTuple()
            
            new_serialisable_info = (
                serialisable_callable_key,
                pipeline_type,
                serialisable_actual_call,
                serialisable_page_parser,
            )
            
            return ( 2, new_serialisable_info )
            
        
    
    def Call( self, input_params ) -> ClientExecutableResponses.ExecutableCallResponse:
        
        return self._actual_call.Call( input_params )
        
    
    def CheckLooksOkForImport( self ):
        
        self._actual_call.CheckLooksOkForImport()
        
    
    def GenerateNewCallableKey( self ):
        
        self._callable_key = HydrusData.GenerateKey()
        
    
    def GetCall( self ):
        
        return self._actual_call
        
    
    def GetCallableKey( self ):
        
        return self._callable_key
        
    
    def GetIdAndName( self ):
        
        return HydrusSerialisable.IdAndName( object_id = self._callable_key, name = self._name )
        
    
    def GetPageParser( self ):
        
        return self._page_parser
        
    
    def GetPipelineType( self ):
        
        return self._pipeline_type
        
    
    def SetCallableKey( self, value: bytes ):
        
        self._callable_key = value
        
    
    def SetPageParser( self, page_parser: ClientParsing.PageParser ):
        
        self._page_parser = page_parser
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALLABLE ] = ClientExecutableCallable
