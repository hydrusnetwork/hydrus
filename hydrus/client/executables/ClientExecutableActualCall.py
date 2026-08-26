import os
import shutil
import webbrowser

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText
from hydrus.core.processes import HydrusSubprocess

from hydrus.client import ClientStrings
from hydrus.client.executables import ClientExecutablePipelines

class ExecutableActualCall( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_NAME = 'Actual Call Superclass'
    SERIALISABLE_VERSION = 1
    
    def _DoCall( self, input_parameters: dict, for_user_test = False ) -> dict:
        
        raise NotImplementedError()
        
    
    def _GetSerialisableInfo( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        raise NotImplementedError()
        
    
    def _TestAvailability( self ):
        
        raise NotImplementedError()
        
    
    def GetCommandDescription( self ) -> str:
        
        raise NotImplementedError()
        
    
    def GetCommandPreviewWithInputParams( self, input_params: dict[ int, str ] ):
        
        raise NotImplementedError()
        
    
    def GetInputParametersUsed( self ):
        
        raise NotImplementedError()
        
    
    def CanTestAvailability( self ):
        
        raise NotImplementedError()
        
    
    def Call( self, input_parameters: dict ) -> dict:
        
        return self._DoCall( input_parameters )
        
    
    def CallTest( self, input_parameters: dict ) -> dict:
        
        return self._DoCall( input_parameters, for_user_test = True )
        
    
    def TestAvailability( self ):
        
        return self._TestAvailability()
        
    

class LocalProcessCallInputParameterProcessingRule(HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALL_LOCAL_PROCESS_INPUT_TEMPLATE_PARAM_PROCESSING_RULE
    SERIALISABLE_NAME = 'Local Process Call - Input Parameter Processing Rule'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, parameter_type: int | None = None, replacement_string: str | None = None, string_processor: ClientStrings.StringProcessor | None = None ):
        
        super().__init__()
        
        if parameter_type is None:
            
            parameter_type = ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATH
            
        
        if replacement_string is None:
            
            replacement_string = ClientExecutablePipelines.parameter_types_to_default_token_names[ parameter_type ]
            
        
        if string_processor is None:
            
            string_processor = ClientStrings.StringProcessor()
            
        
        self.parameter_type: int = parameter_type
        self.replacement_string: str = replacement_string
        self.string_processor: ClientStrings.StringProcessor = string_processor
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_string_processor = self.string_processor.GetSerialisableTuple()
        
        return ( self.parameter_type, self.replacement_string, serialisable_string_processor )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.parameter_type, self.replacement_string, serialisable_string_processor ) = serialisable_info
        
        self.string_processor = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_string_processor )
        
    
    def GetInsertionIndex( self, executable_parameter_template: str ):
        
        try:
            
            return executable_parameter_template.index( self.replacement_string )
            
        except Exception as e:
            
            raise HydrusExceptions.ExecutableException( f'The executable parameter template "{executable_parameter_template}" did not have the expected replacement string "{self.replacement_string}"!' )
            
        
    
    def HasInsertionToken( self, executable_parameter_template: str ):
        
        return self.replacement_string in executable_parameter_template
        
    
    def GetStringToInsert( self, input_parameter_string_list: list[ str ] ) -> str:
        
        result = self.string_processor.ProcessStrings( input_parameter_string_list )
        
        if len( result ) == 0:
            
            raise HydrusExceptions.ExecutableException( f'The input parameter "{input_parameter_string_list}" did not string-process to anything!' )
            
        
        return result[0]
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALL_LOCAL_PROCESS_INPUT_TEMPLATE_PARAM_PROCESSING_RULE ] = LocalProcessCallInputParameterProcessingRule

# TODO: Make a LocalProcessCall that has a list of params, with slightly more complicated UI
# Instead of the shell parsing, we can do better for difficult situations

class ExecutableLocalProcessCall( ExecutableActualCall ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALL_LOCAL_PROCESS_CALL
    SERIALISABLE_NAME = 'Local Process Call'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, executable_path: str | None = None, executable_parameter_templates: list[ str ] | None = None, input_parameter_processing_rules = None ):
        
        super().__init__()
        
        if executable_path is None:
            
            executable_path = ''
            
        
        if executable_parameter_templates is None:
            
            executable_parameter_templates = []
            
        
        if input_parameter_processing_rules is None:
            
            input_parameter_processing_rules = HydrusSerialisable.SerialisableList()
            
        
        self._executable_path: str = executable_path
        self._executable_parameter_templates: list[ str ] = executable_parameter_templates
        self._input_parameter_processing_rules: HydrusSerialisable.SerialisableList[ LocalProcessCallInputParameterProcessingRule ] = HydrusSerialisable.SerialisableList( input_parameter_processing_rules )
        self._timeout: int = 15
        self._this_is_a_potentially_long_lived_external_guy = False
        self._hide_terminal = True
        self._text = True
        
    
    def _DoCall( self, input_parameters: dict, for_user_test = False ) -> dict:
        
        cmd = self._GetFinalCmd( input_parameters )
        
        if for_user_test and self._this_is_a_potentially_long_lived_external_guy:
            
            ( timeout, this_is_a_potentially_long_lived_external_guy ) = ( 15, False )
            
        else:
            
            ( timeout, this_is_a_potentially_long_lived_external_guy ) = ( self._timeout, self._this_is_a_potentially_long_lived_external_guy )
            
        
        try:
            
            ( stdout, stderr, returncode ) = HydrusSubprocess.RunSubprocess(
                cmd,
                timeout = timeout,
                this_is_a_potentially_long_lived_external_guy = this_is_a_potentially_long_lived_external_guy,
                hide_terminal = self._hide_terminal,
                text = self._text,
            )
            
        except Exception as e:
            
            raise HydrusExceptions.ExecutableException( f'Problem running external local process! Final call list was "{cmd}", error was: {e}' ) from e
            
        
        # if 1 is ok (e.g. on like imagemagick diff apparently), we'll have to filter this
        if returncode != 0:
            
            HydrusSubprocess.ReportBadReturnCode( cmd, returncode, stdout, stderr )
            
        
        # if this is a long-lived guy, no stdout/stderr processing
        # if text, we can do json or whatever parsing on it
        # if not text, we can eat a file bytes response
        # can also be no response. maybe we were passed a temp file, the caller cares but we don't
        # TODO: so yeah expand this guy to eat either text or bytes back and transmogrify that into a dict response that a higher guy will pick up
        # if bytes, we should stream to a tempdir tbh that the Response can clean up
        # TODO: consider validity parsing here when we _do_ get text back. standard veto content parser?
        
        return dict()
        
    
    def _GetFinalCmd( self, input_parameters: dict[ int, str | list[ str ] ] ) -> list[ str ]:
        
        cmd = [ self._executable_path ]
        
        input_parameters_used = set()
        
        for executable_parameter_template in self._executable_parameter_templates:
            
            insertion_tuples = []
            
            for parameter_processing_rule in self._input_parameter_processing_rules:
                
                if not parameter_processing_rule.HasInsertionToken( executable_parameter_template ):
                    
                    continue
                    
                
                insertion_index = parameter_processing_rule.GetInsertionIndex( executable_parameter_template )
                
                try:
                    
                    input_parameter_value = input_parameters[ parameter_processing_rule.parameter_type ]
                    
                except KeyError:
                    
                    raise HydrusExceptions.ExecutableException( f'The expected input parameter "{ClientExecutablePipelines.parameter_types_to_strs[ parameter_processing_rule.parameter_type ]}" was not in the call arguments!' )
                    
                
                input_parameters_used.add( parameter_processing_rule )
                
                if isinstance( input_parameter_value, str ):
                    
                    input_parameter_string_list = [ input_parameter_value ]
                    
                else:
                    
                    input_parameter_string_list = input_parameter_value
                    
                
                insertion_string = parameter_processing_rule.GetStringToInsert( input_parameter_string_list )
                
                insertion_tuples.append( ( insertion_index, parameter_processing_rule.replacement_string, insertion_string ) )
                
            
            # ok we know what we want to insert, and where. now let's do it in reverse order so as not to trip up on something we later insert
            insertion_tuples.sort( reverse = True )
            
            final_parameter = executable_parameter_template
            
            for ( _, replacement_string, insertion_string ) in insertion_tuples:
                
                final_parameter = final_parameter.replace( replacement_string, insertion_string, 1 )
                
            
            cmd.append( final_parameter )
            
        
        unused_parameters = set( self._input_parameter_processing_rules ).difference( input_parameters_used )
        
        if len( unused_parameters ) > 0:
            
            bad_strings = [ f'"{ClientExecutablePipelines.parameter_types_to_strs[ parameter_processing_rule.parameter_type]}"' for parameter_processing_rule in unused_parameters ]
            
            summary = HydrusText.ConvertManyStringsToNiceInsertableHumanSummarySingleLine( bad_strings, 'parameters' )
            
            raise HydrusExceptions.ExecutableException( f'Was set to ask for certain input parameters, but then could not find the associated replacement tokens in the parameter list. Missing parameters were: {summary}' )
            
        
        return cmd
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_input_parameter_processing_rules = self._input_parameter_processing_rules.GetSerialisableTuple()
        
        return (
            self._executable_path,
            self._executable_parameter_templates,
            serialisable_input_parameter_processing_rules,
            self._timeout,
            self._this_is_a_potentially_long_lived_external_guy,
            self._hide_terminal,
            self._text,
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            self._executable_path,
            self._executable_parameter_templates,
            serialisable_input_parameter_processing_rules,
            self._timeout,
            self._this_is_a_potentially_long_lived_external_guy,
            self._hide_terminal,
            self._text,
        ) = serialisable_info
        
        self._input_parameter_processing_rules = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_input_parameter_processing_rules )
        
    
    def _TestAvailability( self ):
        
        return shutil.which( self._executable_path ) is not None
        
    
    def CanTestAvailability( self ):
        
        return True
        
    
    def GetCommandDescription( self ) -> str:
        
        if self._executable_path == '':
            
            return 'no call set!'
            
        
        return 'CALL: ' + self._executable_path + ' ' + ' '.join( self._executable_parameter_templates )
        
    
    def GetCommandPreviewWithInputParams( self, input_params: dict[ int, str ] ) -> str:
        
        try:
            
            cmd = self._GetFinalCmd( input_params )
            
            return ' '.join( cmd )
            
        except Exception as e:
            
            return f'Error! {e}'
            
        
    
    def GetHideTerminal( self ):
        
        return self._hide_terminal
        
    
    def GetInputParametersUsed( self ):
        
        return [ input_parameter_processing_rule.parameter_type for input_parameter_processing_rule in self._input_parameter_processing_rules ]
        
    
    def GetInputParameterProcessingRules( self ):
        
        return self._input_parameter_processing_rules
        
    
    def GetExecutablePath( self ):
        
        return self._executable_path
        
    
    def GetExecutableParameterTemplates( self ):
        
        return self._executable_parameter_templates
        
    
    def GetText( self ):
        
        return self._text
        
    
    def GetTimeout( self ):
        
        return self._timeout
        
    
    def GetThisIsAPotentiallyLongLivedExternalGuy( self ):
        
        return self._this_is_a_potentially_long_lived_external_guy
        
    
    def SetHideTerminal( self, value: bool ):
        
        self._hide_terminal = value
        
    
    def SetText( self, value: bool ):
        
        self._text = value
        
    
    def SetTimeout( self, value: int ):
        
        self._timeout = value
        
    
    def SetThisIsAPotentiallyLongLivedExternalGuy( self, value: bool ):
        
        self._this_is_a_potentially_long_lived_external_guy = value
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALL_LOCAL_PROCESS_CALL ] = ExecutableLocalProcessCall

class ExecutableLocalProcessDefaultLaunchFile( ExecutableActualCall ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALL_LOCAL_PROCESS_DEFAULT_LAUNCH_FILE
    SERIALISABLE_NAME = 'Local Process (Default Launch File Command)'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
    
    def _DoCall( self, input_parameters: dict, for_user_test = False ) -> dict:
        
        try:
            
            path = input_parameters[ ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATH ]
            
        except KeyError:
            
            raise HydrusExceptions.ExecutableException( f'The expected input parameter "{ClientExecutablePipelines.parameter_types_to_strs[ ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATH ]}" was not in the call arguments!' )
            
        
        if HC.PLATFORM_WINDOWS:
            
            os.startfile( path )
            
        else:
            
            if HC.PLATFORM_MACOS:
                
                cmd = [ 'open', path ]
                
            elif HC.PLATFORM_LINUX:
                
                cmd = [ 'xdg-open', path ]
                
            elif HC.PLATFORM_HAIKU:
                
                cmd = [ 'open', path ]
                
            else:
                
                raise NotImplementedError( 'Unknown platform!' )
                
            
            HydrusData.CheckProgramIsNotShuttingDown()
            
            HydrusSubprocess.RunSubprocess( cmd, this_is_a_potentially_long_lived_external_guy = not for_user_test )
            
        
        return dict()
        
    
    def _GetSerialisableInfo( self ):
        
        return tuple()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        pass
        
    
    def _TestAvailability( self ):
        
        return True
        
    
    def CanTestAvailability( self ):
        
        return False
        
    
    def GetCommandDescription( self ) -> str:
        
        return '-hardcoded- Call OS default file launcher'
        
    
    def GetCommandPreviewWithInputParams( self, input_params: dict[ int, str ] ) -> str:
        
        try:
            
            return f'Ask OS to open "{input_params[ ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATH ]}"'
            
        except Exception as e:
            
            return f'Error! {e}'
            
        
    
    def GetInputParametersUsed( self ):
        
        return [ ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATH ]
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALL_LOCAL_PROCESS_DEFAULT_LAUNCH_FILE ] = ExecutableLocalProcessDefaultLaunchFile

class ExecutableLocalProcessDefaultLaunchURL( ExecutableActualCall ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALL_LOCAL_PROCESS_DEFAULT_LAUNCH_URL
    SERIALISABLE_NAME = 'Local Process (Default Launch URL Command)'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
    
    def _DoCall( self, input_parameters: dict, for_user_test = False ) -> dict:
        
        try:
            
            url = input_parameters[ ClientExecutablePipelines.PARAMETER_TYPE_URL ]
            
        except KeyError:
            
            raise HydrusExceptions.ExecutableException( f'The expected input parameter "{ClientExecutablePipelines.parameter_types_to_strs[ ClientExecutablePipelines.PARAMETER_TYPE_URL ]}" was not in the call arguments!' )
            
        
        webbrowser.open( url )
        
        return dict()
        
    
    def _GetSerialisableInfo( self ):
        
        return tuple()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        pass
        
    
    def _TestAvailability( self ):
        
        return True
        
    
    def CanTestAvailability( self ):
        
        return False
        
    
    def GetCommandDescription( self ) -> str:
        
        return '-hardcoded- Call OS default URL launcher'
        
    
    def GetCommandPreviewWithInputParams( self, input_params: dict[ int, str ] ) -> str:
        
        try:
            
            return f'Ask OS to open "{input_params[ ClientExecutablePipelines.PARAMETER_TYPE_URL ]}"'
            
        except Exception as e:
            
            return f'Error! {e}'
            
        
    
    def GetInputParametersUsed( self ):
        
        return [ ClientExecutablePipelines.PARAMETER_TYPE_URL ]
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALL_LOCAL_PROCESS_DEFAULT_LAUNCH_URL ] = ExecutableLocalProcessDefaultLaunchURL
