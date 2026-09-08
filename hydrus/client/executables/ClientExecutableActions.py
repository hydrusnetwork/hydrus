from pathlib import Path

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientGlobals as CG
from hydrus.client.executables import ClientExecutableManager
from hydrus.client.executables import ClientExecutablePipelines
from hydrus.client.media import ClientMediaResult

def OpenExternallySingleFile( executable_manager: ClientExecutableManager.ExecutableManager, id_and_name: HydrusSerialisable.IdAndName, media_result: ClientMediaResult.MediaResult ):
    
    if not media_result.GetLocationsManager().IsLocal():
        
        raise HydrusExceptions.VetoException( 'This file is not local--it cannot be opened!' )
        
    
    hash = media_result.GetHash()
    
    try:
        
        call = executable_manager.GetCallable( id_and_name )
        
    except HydrusExceptions.DataMissing:
        
        raise HydrusExceptions.ExecutableException( f'When trying to open file "{hash.hex()}" externally, the executable we wanted to call ({id_and_name}) did not exist!' )
        
    
    if call.GetPipelineType() != ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE:
        
        raise HydrusExceptions.ExecutableException( f'When trying to open file "{hash.hex()}" externally, the executable we wanted to call ({id_and_name}) was the wrong type ({ClientExecutablePipelines.executable_pipeline_types_to_strs[call.GetPipelineType()]})!' )
        
    
    mime = media_result.GetMime()
    
    file_path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
    
    file_uri = Path( file_path ).as_uri()
    
    input_params = {
        ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATH : file_path,
        ClientExecutablePipelines.PARAMETER_TYPE_FILE_LOCAL_PATH_URI : file_uri,
        ClientExecutablePipelines.PARAMETER_TYPE_FILE_HASH : hash.hex(),
        ClientExecutablePipelines.PARAMETER_TYPE_FILE_HASH_ID : media_result.GetHashId(),
    }
    
    call.Call( input_params )
    
    return True
    

def OpenExternallyMultipleFiles( executable_manager: ClientExecutableManager.ExecutableManager, id_and_name: HydrusSerialisable.IdAndName, media_results: list[ ClientMediaResult.MediaResult ] ):
    
    files_desc = f'{HydrusNumbers.ToHumanInt( len( media_results ))} files'
    
    try:
        
        call = executable_manager.GetCallable( id_and_name )
        
    except HydrusExceptions.DataMissing:
        
        raise HydrusExceptions.ExecutableException( f'When trying to open {files_desc} externally, the executable we wanted to call ({id_and_name}) did not exist!' )
        
    
    if call.GetPipelineType() != ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE:
        
        raise HydrusExceptions.ExecutableException( f'When trying to open {files_desc} externally, the executable we wanted to call ({id_and_name}) was the wrong type ({ClientExecutablePipelines.executable_pipeline_types_to_strs[call.GetPipelineType()]})!' )
        
    
    file_paths = []
    file_uris = []
    
    for media_result in media_results:
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        file_path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
        
        file_uri = Path( file_path ).as_uri()
        
        file_paths.append( file_path )
        file_uris.append( file_uri )
        
    
    input_params = {
        ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATHS : file_paths,
        ClientExecutablePipelines.PARAMETER_TYPE_FILE_LOCAL_PATH_URIS : file_uris,
    }
    
    call.Call( input_params )
    

def OpenExternallyURL( executable_manager: ClientExecutableManager.ExecutableManager, id_and_name: HydrusSerialisable.IdAndName, url: str ):
    
    try:
        
        call = executable_manager.GetCallable( id_and_name )
        
    except HydrusExceptions.DataMissing:
        
        raise HydrusExceptions.ExecutableException( f'When trying to open URL "{url}" externally, the executable we wanted to call ({id_and_name}) did not exist!' )
        
    
    if call.GetPipelineType() != ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL:
        
        raise HydrusExceptions.ExecutableException( f'When trying to open URL "{url}" externally, the executable we wanted to call ({id_and_name}) was the wrong type ({ClientExecutablePipelines.executable_pipeline_types_to_strs[call.GetPipelineType()]})!' )
        
    
    input_params = {
        ClientExecutablePipelines.PARAMETER_TYPE_URL : url,
    }
    
    call.Call( input_params )
    
