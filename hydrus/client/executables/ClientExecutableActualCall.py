from hydrus.core import HydrusSerialisable

class ExecutableActualCall( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_NAME = 'Actual Call Superclass'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, can_test_availability: bool | None = None ):
        
        super().__init__()
        
        if can_test_availability is None:
            
            can_test_availability = True
            
        
        self._can_test_availability = can_test_availability
        # TODO: output parsing
        # TODO: maybe some validity/error checking on output
        
    
    def _DoCall( self, input_params: dict ) -> dict:
        
        raise NotImplementedError()
        
    
    def _GetSerialisableInfo( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        raise NotImplementedError()
        
    
    def _TestAvailability( self ):
        
        raise NotImplementedError()
        
    
    def CanTestAvailability( self ):
        
        return self._can_test_availability
        
    
    def TestAvailability( self ):
        
        return self._TestAvailability()
        
    
    def Call( self, input_params: dict ) -> dict:
        
        return self._DoCall( input_params )
        
    

class ExecutableLocalProcessCall( ExecutableActualCall ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALL_LOCAL_PROCESS
    SERIALISABLE_NAME = 'Local Process Call'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, availability_path = None, path = None ):
        
        super().__init__( can_test_availability = availability_path is not None )
        
        if availability_path is None:
            
            availability_path = ''
            
        
        if path is None:
            
            path = ''
            
        
        self._availability_path = availability_path # 'ffmpeg --version' or something, maybe optional?
        self._path: str = path # the actual call
        # I think I like the idea of maybe just a whole 'command' with %1 replacement guys in it
        # then we have a mapping of input_param -> replacement guy, with a strong converter if user needs it
        # TODO: rules on how to eat input params and wangle them to a launch command
        # TODO: do we get data or a file back? what do we do with that, do we parse it?
        # TODO: maybe some validity/error checking on output
        
    
    def _DoCall( self, input_params: dict ) -> dict:
        
        # TODO: eat the input params, wangle them to launch params and a full launch command according to rules
        # subprocess that guy
        # handle the response
        
        raise NotImplementedError()
        
    
    def _GetSerialisableInfo( self ):
        
        pass # TODO: do this
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        pass # TODO: do this
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALL_LOCAL_PROCESS ] = ExecutableLocalProcessCall
