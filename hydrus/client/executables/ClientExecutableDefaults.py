from hydrus.core import HydrusConstants as HC

from hydrus.client.executables import ClientExecutableActualCall
from hydrus.client.executables import ClientExecutableCallableSockets
from hydrus.client.executables import ClientExecutablePipelines

def GetDefaultOpenExternally() -> list[ ClientExecutableCallableSockets.CallableSocket ]:
    
    input_parameter_processing_rules = [
        ClientExecutableActualCall.LocalProcessCallInputParameterProcessingRule(
            ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATH,
            '%path%'
        )
    ]
    
    callables = []
    
    #
    
    actual_call = ClientExecutableActualCall.LocalProcessDefaultLaunchFile()
    
    call = ClientExecutableCallableSockets.CallableSocket(
        'Default OS File Launch',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( True, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.LocalProcessCall(
        executable_path = 'xdg-open',
        executable_parameter_templates = [ '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallableSockets.CallableSocket(
        'xdg-open',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.LocalProcessCall(
        executable_path = 'gio',
        executable_parameter_templates = [ 'open', '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallableSockets.CallableSocket(
        'gio open (Gnome)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.LocalProcessCall(
        executable_path = 'kioclient',
        executable_parameter_templates = [ 'exec', '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallableSockets.CallableSocket(
        'kioclient exec (KDE)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.LocalProcessCall(
        executable_path = 'firefox',
        executable_parameter_templates = [ '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallableSockets.CallableSocket(
        'firefox (file path)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX or HC.PLATFORM_WINDOWS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.LocalProcessCall(
        executable_path = 'google-chrome',
        executable_parameter_templates = [ '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallableSockets.CallableSocket(
        'chrome (file path)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX, call ) )
    
    #
    
    #
    
    actual_call = ClientExecutableActualCall.LocalProcessCall(
        executable_path = 'chrome',
        executable_parameter_templates = [ '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallableSockets.CallableSocket(
        'chrome (file path) (Windows)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_WINDOWS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.LocalProcessCall(
        executable_path = 'open',
        executable_parameter_templates = [ '-a', 'Firefox', '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallableSockets.CallableSocket(
        'firefox (file path) (macOS)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_MACOS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.LocalProcessCall(
        executable_path = 'open',
        executable_parameter_templates = [ '-a', 'Google Chrome', '%path%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallableSockets.CallableSocket(
        'chrome (file path) (macOS)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_FILE,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_MACOS, call ) )
    
    return callables
    

def GetDefaultOpenURL() -> list[ ClientExecutableCallableSockets.CallableSocket ]:
    
    input_parameter_processing_rules = [
        ClientExecutableActualCall.LocalProcessCallInputParameterProcessingRule(
            ClientExecutablePipelines.PARAMETER_TYPE_URL,
            '%url%'
        )
    ]
    
    callables = []
    
    #
    
    actual_call = ClientExecutableActualCall.LocalProcessDefaultLaunchURL()
    
    call = ClientExecutableCallableSockets.CallableSocket(
        'Default OS URL Launch',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( True, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.LocalProcessCall(
        executable_path = 'firefox',
        executable_parameter_templates = [ '%url%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallableSockets.CallableSocket(
        'firefox (URL)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX or HC.PLATFORM_WINDOWS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.LocalProcessCall(
        executable_path = 'google-chrome',
        executable_parameter_templates = [ '%url%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallableSockets.CallableSocket(
        'chrome (URL)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_LINUX, call ) )
    
    #
    
    #
    
    actual_call = ClientExecutableActualCall.LocalProcessCall(
        executable_path = 'chrome',
        executable_parameter_templates = [ '%url%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallableSockets.CallableSocket(
        'chrome (URL) (Windows)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_WINDOWS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.LocalProcessCall(
        executable_path = 'open',
        executable_parameter_templates = [ '-a', 'Firefox', '%url%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallableSockets.CallableSocket(
        'firefox (URL) (macOS)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_MACOS, call ) )
    
    #
    
    actual_call = ClientExecutableActualCall.LocalProcessCall(
        executable_path = 'open',
        executable_parameter_templates = [ '-a', 'Google Chrome', '%url%' ],
        input_parameter_processing_rules = input_parameter_processing_rules
    )
    
    actual_call.SetThisIsAPotentiallyLongLivedExternalGuy( True )
    
    call = ClientExecutableCallableSockets.CallableSocket(
        'chrome (URL) (macOS)',
        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_URL,
        actual_call = actual_call
    )
    
    callables.append( ( HC.PLATFORM_MACOS, call ) )
    
    return callables
    

def GetAllDefaultCallableSockets( filter_by_platform: bool ):
    
    external_platforms_and_callable_sockets = list( GetDefaultOpenExternally() )
    external_platforms_and_callable_sockets.extend( GetDefaultOpenURL() )
    
    if filter_by_platform:
        
        external_callable_sockets = [ call for ( my_platform, call ) in external_platforms_and_callable_sockets if my_platform ]
        
    else:
        
        external_callable_sockets = [ call for ( my_platform, call ) in external_platforms_and_callable_sockets ]
        
    
    return external_callable_sockets
    
