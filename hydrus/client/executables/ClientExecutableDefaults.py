from hydrus.client.executables import ClientExecutableActualCall
from hydrus.client.executables import ClientExecutableCallables
from hydrus.client.executables import ClientExecutablePipelines

def GetDefaultOpenExternally() -> list[ ClientExecutableCallables.ClientExecutableCallable ]:
    
    # the hardcoded Windows open guy?
    
    parameter_processing_rules = [
        ClientExecutableActualCall.LocalProcessCallTemplateInputParameterProcessingRule(
            ClientExecutablePipelines.PARAM_TYPE_FILE_PATH,
            '%path%'
        )
    ]
    
    callables = []
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'xdg-open "%path%"',
        parameter_processing_rules = parameter_processing_rules
    )
    
    actual_call.SetAvailabilityWhichName( 'xdg-open' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'xdg-open',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( call )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'gio open "%path%"',
        parameter_processing_rules = parameter_processing_rules
    )
    
    actual_call.SetAvailabilityWhichName( 'gio' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'gio open (Gnome)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( call )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'kioclient exec "%path%"',
        parameter_processing_rules = parameter_processing_rules
    )
    
    actual_call.SetAvailabilityWhichName( 'kioclient' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'kioclient exec (KDE)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( call )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'firefox "%path%"',
        parameter_processing_rules = parameter_processing_rules
    )
    
    actual_call.SetAvailabilityWhichName( 'firefox' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'firefox (file path)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( call )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'google-chrome "%path%"',
        parameter_processing_rules = parameter_processing_rules
    )
    
    actual_call.SetAvailabilityWhichName( 'google-chrome' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'chrome (file path)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( call )
    
    #
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'chrome "%path%"',
        parameter_processing_rules = parameter_processing_rules
    )
    
    actual_call.SetAvailabilityWhichName( 'chrome' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'chrome (file path) (Windows)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( call )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'open -a "Firefox" "%path%"',
        parameter_processing_rules = parameter_processing_rules
    )
    
    actual_call.SetAvailabilityCall( 'open -Ra "Firefox"' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'firefox (file path) (macOS)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( call )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'open -a "Google Chrome" "%path%"',
        parameter_processing_rules = parameter_processing_rules
    )
    
    actual_call.SetAvailabilityCall( 'open -Ra "Google Chrome"' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'chrome (file path) (macOS)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( call )
    
    return callables
    
