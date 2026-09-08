from hydrus.core import HydrusExceptions
from hydrus.core import HydrusText

from hydrus.client.executables import ClientExecutableActualCall
from hydrus.client.executables import ClientExecutableCallables
from hydrus.client.executables import ClientExecutablePipelines

def ConvertOldCallToExecutableParams( call_template: str ):
    
    call_template = HydrusText.re_one_or_more_whitespace.sub( ' ', call_template )
    
    call_template = call_template.strip()
    
    call_template_components = call_template.split( ' ' )
    
    if len( call_template_components ) == 0:
        
        raise HydrusExceptions.VetoException( 'Empty call template, looks like!' )
        
    
    executable_path = call_template_components[0]
    raw_params = call_template_components[1:]
    
    executable_parameter_templates = []
    
    for raw_param in raw_params:
        
        if raw_param[0] == '"' and raw_param[-1] == '"':
            
            raw_param = raw_param[ 1 : -1 ]
            
        
        if raw_param == '':
            
            # not expecting this, but w/e
            continue
            
        
        executable_parameter_templates.append( raw_param )
        
    
    return ( executable_path, executable_parameter_templates )
    

def ConvertOldFileCallToExecutableActualCall( call_template: str ):
    
    # something like `my_image_viewer "%path%"`
    
    input_parameter_processing_rules = [
        ClientExecutableActualCall.LocalProcessCallInputParameterProcessingRule(
            ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATH,
            '%path%'
        )
    ]
    
    ( executable_path, executable_parameter_templates ) = ConvertOldCallToExecutableParams( call_template )
    
    process_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
        executable_path = executable_path,
        executable_parameter_templates = executable_parameter_templates,
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    executable_callable = ClientExecutableCallables.ClientExecutableCallable(
        name = call_template,
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = process_call
    )
    
    return executable_callable
    

def ConvertOldURLCallToExecutableActualCall( call_template: str ):
    
    # something like `firefox "%url%"`
    
    input_parameter_processing_rules = [
        ClientExecutableActualCall.LocalProcessCallInputParameterProcessingRule(
            ClientExecutablePipelines.PARAMETER_TYPE_URL,
            '%url%'
        )
    ]
    
    ( executable_path, executable_parameter_templates ) = ConvertOldCallToExecutableParams( call_template )
    
    process_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
        executable_path = executable_path,
        executable_parameter_templates = executable_parameter_templates,
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    executable_callable = ClientExecutableCallables.ClientExecutableCallable(
        name = call_template,
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
        actual_call = process_call
    )
    
    return executable_callable
    
