import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core.processes import HydrusSubprocess

from hydrus.client import ClientStrings

class ExecutableActualCall( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_NAME = 'Actual Call Superclass'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, can_test_availability: bool | None = None ):
        
        super().__init__()
        
        if can_test_availability is None:
            
            can_test_availability = True
            
        
        self._can_test_availability = can_test_availability
        
    
    def _DoCall( self, input_parameters: dict ) -> dict:
        
        raise NotImplementedError()
        
    
    def _GetSerialisableInfo( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        raise NotImplementedError()
        
    
    def _TestAvailability( self ):
        
        raise NotImplementedError()
        
    
    def GetCommandDescription( self ):
        
        raise NotImplementedError()
        
    
    def CanTestAvailability( self ):
        
        return self._can_test_availability
        
    
    def Call( self, input_parameters: dict ) -> dict:
        
        return self._DoCall( input_parameters )
        

    def TestAvailability( self ):
        
        return self._TestAvailability()
        
    

class LocalProcessCallTemplateInputParameterProcessingRule(HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALL_LOCAL_PROCESS_INPUT_TEMPLATE_PARAM_PROCESSING_RULE
    SERIALISABLE_NAME = 'Local Process Call - Input Parameter Processing Rule'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, input_parameter_name: str | None = None, replacement_string: str | None = None, string_processor: ClientStrings.StringProcessor | None = None ):
        
        super().__init__()
        
        if input_parameter_name is None:
            
            input_parameter_name = 'path'
            
        
        if replacement_string is None:
            
            replacement_string = '%path%'
            
        
        if string_processor is None:
            
            string_processor = ClientStrings.StringProcessor()
            
        
        self.input_parameter_name: str = input_parameter_name
        self.replacement_string: str = replacement_string
        self.string_processor: ClientStrings.StringProcessor = string_processor
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_string_processor = self.string_processor.GetSerialisableTuple()
        
        return ( self.input_parameter_name, self.replacement_string, serialisable_string_processor )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.input_parameter_name, self.replacement_string, serialisable_string_processor ) = serialisable_info
        
        self.string_processor = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_processor )
        
    
    def GetInsertionIndex( self, path_template: str ):
        
        try:
            
            return path_template.index( self.replacement_string )
            
        except IndexError:
            
            raise HydrusExceptions.ExecutableException( f'The path template "{path_template}" did not have the expected replacement string "{self.replacement_string}"!' )
            
        
    
    def GetStringToInsert( self, input_parameter_string_list: list[ str ] ) -> str:
        
        result = self.string_processor.ProcessStrings( input_parameter_string_list )
        
        if len( result ) == 0:
            
            raise HydrusExceptions.ExecutableException( f'The input parameter "{input_parameter_string_list}" did not string-process to anything!' )
            
        
        return result[0]
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALL_LOCAL_PROCESS_INPUT_TEMPLATE_PARAM_PROCESSING_RULE ] = LocalProcessCallTemplateInputParameterProcessingRule

class ExecutableLocalProcessCallTemplate( ExecutableActualCall ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALL_LOCAL_PROCESS_TEMPLATE
    SERIALISABLE_NAME = 'Local Process Call (Template)'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, availability_path = None, path_template = None, parameter_processing_rules = None ):
        
        super().__init__( can_test_availability = availability_path is not None )
        
        if path_template is None:
            
            path_template = ''
            
        
        if parameter_processing_rules is None:
            
            parameter_processing_rules = HydrusSerialisable.SerialisableList()
            
        
        self._availability_path: str | None = availability_path # 'ffmpeg --version' or something, maybe optional?
        self._path_template: str = path_template # the actual call
        self._parameter_processing_rules: HydrusSerialisable.SerialisableList = HydrusSerialisable.SerialisableList( parameter_processing_rules )
        self._timeout = 15
        self._this_is_a_potentially_long_lived_external_guy = False
        self._hide_terminal = False
        self._text = False
        
    
    def _DoCall( self, input_parameters: dict ) -> dict:
        
        insertion_tuples = []
        
        for parameter_processing_rule in self._parameter_processing_rules:
            
            parameter_processing_rule = typing.cast( LocalProcessCallTemplateInputParameterProcessingRule, parameter_processing_rule )
            
            insertion_index = parameter_processing_rule.GetInsertionIndex( self._path_template )
            
            try:
                
                input_parameter_value = input_parameters[ parameter_processing_rule.input_parameter_name ]
                
            except KeyError:
                
                raise HydrusExceptions.ExecutableException( f'The expected input parameter "{parameter_processing_rule.input_parameter_name}" was not in the call arguments!' )
                
            
            if isinstance( input_parameter_value, str ):
                
                input_parameter_string_list = [ input_parameter_value ]
                
            else:
                
                input_parameter_string_list = input_parameter_value
                
            
            insertion_string = parameter_processing_rule.GetStringToInsert( input_parameter_string_list )
            
            insertion_tuples.append( ( insertion_index, parameter_processing_rule.replacement_string, insertion_string ) )
            
        
        # ok we know what we want to insert, and where. now let's do it in reverse order so as not to trip up on something we later insert
        insertion_tuples.sort( reverse = True )
        
        final_call = self._path_template
        
        for ( _, replacement_string, insertion_string ) in insertion_tuples:
            
            final_call = final_call.replace( replacement_string, insertion_string, 1 )
            
        
        try:

            ( stdout, stderr ) = HydrusSubprocess.RunSubprocess(
                final_call,
                timeout = self._timeout,
                this_is_a_potentially_long_lived_external_guy = self._this_is_a_potentially_long_lived_external_guy,
                hide_terminal = self._hide_terminal,
                text = self._text
            )
            
        except Exception as e:
            
            raise HydrusExceptions.ExecutableException( f'Problem running external local process! Final call was "{final_call}", error was: {e}' ) from e
            
        
        # if this is a long-lived guy, no stdout/stderr processing
        # if text, we can do json or whatever parsing on it
        # if not text, we can eat a file bytes response
        # can also be no response. maybe we were passed a temp file, the caller cares but we don't
        # TODO: so yeah expand this guy to eat either text or bytes back and transmogrify that into a dict response that a higher guy will pick up
        # if bytes, we should stream to a tempdir tbh that the Response can clean up
        # TODO: consider validity parsing here when we _do_ get text back. standard veto content parser?
        
        return dict()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_parameter_processing_rules = self._parameter_processing_rules.GetSerialisableTuple()
        
        return (
            self._availability_path,
            self._path_template,
            serialisable_parameter_processing_rules,
            self._timeout,
            self._this_is_a_potentially_long_lived_external_guy,
            self._hide_terminal,
            self._text
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            self._availability_path,
            self._path_template,
            serialisable_parameter_processing_rules,
            self._timeout,
            self._this_is_a_potentially_long_lived_external_guy,
            self._hide_terminal,
            self._text
        ) = serialisable_info
        
        self._parameter_processing_rules = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_parameter_processing_rules )
        
    
    def _TestAvailability( self ):
        
        try:
            
            HydrusSubprocess.RunSubprocess(
                self._availability_path,
                this_is_a_potentially_long_lived_external_guy = False,
                hide_terminal = True,
                text = True
            )
            
            return True
            
        except Exception as e:
            
            HydrusData.Print( f'While testing local process call with "{self._availability_path}", ran into the following error:' f' {e}' )
            HydrusData.PrintException( e )
            
        
        return False
        
    
    def GetCommandDescription( self ):
        
        return 'CALL: ' + self._path_template
        
    
    def SetHideTerminal( self, value: bool ):
        
        self._hide_terminal = value
        
    
    def SetText( self, value: bool ):
        
        self._text = value
        
    
    def SetThisIsAPotentiallyLongLivedExternalGuy( self, value: bool ):
        
        self._this_is_a_potentially_long_lived_external_guy = value
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALL_LOCAL_PROCESS_TEMPLATE ] = ExecutableLocalProcessCallTemplate
