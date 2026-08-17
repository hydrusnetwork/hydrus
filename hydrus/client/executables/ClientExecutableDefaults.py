from hydrus.core import HydrusConstants as HC

from hydrus.client.executables import ClientExecutableActualCall
from hydrus.client.executables import ClientExecutableCallables
from hydrus.client.executables import ClientExecutablePipelines

def GetDefaultOpenExternally() -> list[ ClientExecutableCallables.ClientExecutableCallable ]:
    
    input_parameter_processing_rules = [
        ClientExecutableActualCall.LocalProcessCallTemplateInputParameterProcessingRule(
            ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATH,
            '%path%'
        )
    ]
    
    callables = []
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchFile()
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'Default OS Launch File Command',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( True, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'xdg-open "%path%"',
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    actual_call.SetAvailabilityWhichName( 'xdg-open' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'xdg-open',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'gio open "%path%"',
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    actual_call.SetAvailabilityWhichName( 'gio' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'gio open (Gnome)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'kioclient exec "%path%"',
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    actual_call.SetAvailabilityWhichName( 'kioclient' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'kioclient exec (KDE)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'firefox "%path%"',
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    actual_call.SetAvailabilityWhichName( 'firefox' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'firefox (file path)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX or HC.PLATFORM_WINDOWS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'google-chrome "%path%"',
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    actual_call.SetAvailabilityWhichName( 'google-chrome' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'chrome (file path)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX, call ) )
    
    #
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'chrome "%path%"',
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    actual_call.SetAvailabilityWhichName( 'chrome' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'chrome (file path) (Windows)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_WINDOWS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'open -a "Firefox" "%path%"',
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    actual_call.SetAvailabilityCall( 'open -Ra "Firefox"' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'firefox (file path) (macOS)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_MACOS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'open -a "Google Chrome" "%path%"',
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    actual_call.SetAvailabilityCall( 'open -Ra "Google Chrome"' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'chrome (file path) (macOS)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_MACOS, call ) )
    
    return callables
    

def GetDefaultOpenURL() -> list[ ClientExecutableCallables.ClientExecutableCallable ]:
    
    input_parameter_processing_rules = [
        ClientExecutableActualCall.LocalProcessCallTemplateInputParameterProcessingRule(
            ClientExecutablePipelines.PARAMETER_TYPE_URL,
            '%url%'
        )
    ]
    
    callables = []
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchURL()
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'Default OS Launch URL Command',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( True, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'firefox "%url%"',
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    actual_call.SetAvailabilityWhichName( 'firefox' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'firefox (URL)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX or HC.PLATFORM_WINDOWS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'google-chrome "%url%"',
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    actual_call.SetAvailabilityWhichName( 'google-chrome' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'chrome (URL)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX, call ) )
    
    #
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'chrome "%url%"',
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    actual_call.SetAvailabilityWhichName( 'chrome' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'chrome (URL) (Windows)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_WINDOWS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'open -a "Firefox" "%url%"',
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    actual_call.SetAvailabilityCall( 'open -Ra "Firefox"' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'firefox (URL) (macOS)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_MACOS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCallTemplate(
        'open -a "Google Chrome" "%url%"',
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    actual_call.SetAvailabilityCall( 'open -Ra "Google Chrome"' )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'chrome (URL) (macOS)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_MACOS, call ) )
    
    return callables
    
