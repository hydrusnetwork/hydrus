from hydrus.core import HydrusConstants as HC

from hydrus.client.executables import ClientExecutableActualCall
from hydrus.client.executables import ClientExecutableCallables
from hydrus.client.executables import ClientExecutablePipelines

def GetDefaultOpenExternally() -> list[ ClientExecutableCallables.ClientExecutableCallable ]:
    
    input_parameter_processing_rules = [
        ClientExecutableActualCall.LocalProcessCallInputParameterProcessingRule(
            ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATH,
            '%path%'
        )
    ]
    
    callables = []
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchFile()
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'Default OS File Launch',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( True, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
        executable_path = 'xdg-open',
        executable_parameter_templates = [ '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'xdg-open',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
        executable_path = 'gio',
        executable_parameter_templates = [ 'open', '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'gio open (Gnome)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
        executable_path = 'kioclient',
        executable_parameter_templates = [ 'exec', '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'kioclient exec (KDE)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
        executable_path = 'firefox',
        executable_parameter_templates = [ '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'firefox (file path)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX or HC.PLATFORM_WINDOWS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
        executable_path = 'google-chrome',
        executable_parameter_templates = [ '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'chrome (file path)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX, call ) )
    
    #
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
        executable_path = 'chrome',
        executable_parameter_templates = [ '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'chrome (file path) (Windows)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_WINDOWS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
        executable_path = 'open',
        executable_parameter_templates = [ '-a', 'Firefox', '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'firefox (file path) (macOS)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_MACOS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
        executable_path = 'open',
        executable_parameter_templates = [ '-a', 'Google Chrome', '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'chrome (file path) (macOS)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_MACOS, call ) )
    
    return callables
    

def GetDefaultOpenURL() -> list[ ClientExecutableCallables.ClientExecutableCallable ]:
    
    input_parameter_processing_rules = [
        ClientExecutableActualCall.LocalProcessCallInputParameterProcessingRule(
            ClientExecutablePipelines.PARAMETER_TYPE_URL,
            '%url%'
        )
    ]
    
    callables = []
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchURL()
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'Default OS URL Launch',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( True, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
        executable_path = 'firefox',
        executable_parameter_templates = [ '%url%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'firefox (URL)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX or HC.PLATFORM_WINDOWS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
        executable_path = 'google-chrome',
        executable_parameter_templates = [ '%url%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'chrome (URL)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX, call ) )
    
    #
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
        executable_path = 'chrome',
        executable_parameter_templates = [ '%url%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'chrome (URL) (Windows)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_WINDOWS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
        executable_path = 'open',
        executable_parameter_templates = [ '-a', 'Firefox', '%url%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'firefox (URL) (macOS)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_MACOS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.ExecutableLocalProcessCall(
        executable_path = 'open',
        executable_parameter_templates = [ '-a', 'Google Chrome', '%url%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallables.ClientExecutableCallable(
        'chrome (URL) (macOS)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_MACOS, call ) )
    
    return callables
    
