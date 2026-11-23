from pathlib import Path

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientGlobals as CG
from hydrus.client.executables import ClientExecutableManager
from hydrus.client.executables import ClientExecutablePipelines
from hydrus.client.files import ClientFilesMaintenance
from hydrus.client.media import ClientMediaResult

def SendSingleFile( executable_manager: ClientExecutableManager.ExecutableManager, id_and_name: HydrusSerialisable.IdAndName, media_result: ClientMediaResult.MediaResult ):
    
    if not media_result.GetLocationsManager().IsLocal():
        
        raise HydrusExceptions.VetoException( 'This file is not local--it cannot be opened!' )
        
    
    hash = media_result.GetHash()
    
    try:
        
        call = executable_manager.GetCallable( id_and_name )
        
    except HydrusExceptions.DataMissing:
        
        raise HydrusExceptions.ExecutableException( f'When trying to open file "{hash.hex()}" externally, the executable we wanted to call ({id_and_name}) did not exist!' )
        
    
    if call.GetPipelineType() != ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_FILE:
        
        raise HydrusExceptions.ExecutableException( f'When trying to open file "{hash.hex()}" externally, the executable we wanted to call ({id_and_name}) was the wrong type ({ClientExecutablePipelines.executable_pipeline_types_to_strs[call.GetPipelineType()]})!' )
        
    
    required_input_parameters = call.GetCall().GetInputParametersUsed()
    
    file_path_or_none: str | None = None
    
    input_params: dict[ int, str | list[ str ] ] = dict()
    
    for required_input_parameter in required_input_parameters:
        
        if required_input_parameter in ( ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATH, ClientExecutablePipelines.PARAMETER_TYPE_FILE_LOCAL_PATH_URI ):
            
            if file_path_or_none is None:
                
                mime = media_result.GetMime()
                
                try:
                    
                    file_path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
                    
                except HydrusExceptions.FileMissingException as e:
                    
                    raise HydrusExceptions.CannotProvideExecutableCallParameters( f'This call needs a file path, but the file {hash.hex()} appears to be missing!' ) from e
                    
                
            else:
                
                file_path = file_path_or_none
                
            
            if required_input_parameter == ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATH:
                
                value = file_path
                
            elif required_input_parameter == ClientExecutablePipelines.PARAMETER_TYPE_FILE_LOCAL_PATH_URI:
                
                file_url = Path( file_path ).as_uri()
                
                value = file_url
                
            else:
                
                raise NotImplementedError( 'Unknown input parameter, something needs to get updated!' )
                
            
        elif required_input_parameter == ClientExecutablePipelines.PARAMETER_TYPE_FILE_HASH_SHA256:
            
            value = hash.hex()
            
        elif required_input_parameter in (
            ClientExecutablePipelines.PARAMETER_TYPE_FILE_HASH_MD5,
            ClientExecutablePipelines.PARAMETER_TYPE_FILE_HASH_SHA1,
            ClientExecutablePipelines.PARAMETER_TYPE_FILE_HASH_SHA512,
        ):
            
            desired_hash_type = {
                ClientExecutablePipelines.PARAMETER_TYPE_FILE_HASH_MD5 : 'md5',
                ClientExecutablePipelines.PARAMETER_TYPE_FILE_HASH_SHA1 : 'sha1',
                ClientExecutablePipelines.PARAMETER_TYPE_FILE_HASH_SHA512 : 'sha256',
            }.get( required_input_parameter )
            
            source_to_desired = CG.client_controller.Read( 'file_hashes', ( hash, ), 'sha256', desired_hash_type )
            
            if hash not in source_to_desired:
                
                if media_result.GetLocationsManager().IsLocal():
                    
                    CG.client_controller.Write( 'file_maintenance_add_jobs_hashes', { hash }, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_OTHER_HASHES )
                    
                    extra_note = 'Since the file is local, it is supposed to have this hash available. I have scheduled your database to regen this hash to fill in the gap. With luck, you can try this job again soon and it will work.'
                    
                else:
                    
                    extra_note = 'Unfortunately, because this file is not local, we cannot generate this hash. You would have to import this file to make this job work.'
                    
                
                message = f'This call needs a {desired_hash_type} hash, but the file {hash.hex()} does not seem to have that hash!'
                message += '\n\n'
                message += extra_note
                
                raise HydrusExceptions.CannotProvideExecutableCallParameters( message )
                
            
            value = source_to_desired[ hash ].hex()
            
        elif required_input_parameter == ClientExecutablePipelines.PARAMETER_TYPE_FILE_FILE_ID:
            
            value = str( media_result.GetHashId() )
            
        else:
            
            raise NotImplementedError( 'Unknown input parameter, something needs to get updated!' )
            
        
        input_params[ required_input_parameter ] = value
        
    
    call.Call( input_params )
    
    return True
    

def SendMultipleFiles( executable_manager: ClientExecutableManager.ExecutableManager, id_and_name: HydrusSerialisable.IdAndName, media_results: list[ ClientMediaResult.MediaResult ] ):
    
    files_desc = f'{HydrusNumbers.ToHumanInt( len( media_results ))} files'
    
    try:
        
        call = executable_manager.GetCallable( id_and_name )
        
    except HydrusExceptions.DataMissing:
        
        raise HydrusExceptions.ExecutableException( f'When trying to open {files_desc} externally, the executable we wanted to call ({id_and_name}) did not exist!' )
        
    
    if call.GetPipelineType() != ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_FILE:
        
        raise HydrusExceptions.ExecutableException( f'When trying to open {files_desc} externally, the executable we wanted to call ({id_and_name}) was the wrong type ({ClientExecutablePipelines.executable_pipeline_types_to_strs[call.GetPipelineType()]})!' )
        
    
    required_input_parameters = call.GetCall().GetInputParametersUsed()
    
    file_paths = []
    file_uris = []
    
    for media_result in media_results:
        
        hash = media_result.GetHash()
        mime = media_result.GetMime()
        
        if ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATHS in required_input_parameters or ClientExecutablePipelines.PARAMETER_TYPE_FILE_LOCAL_PATH_URIS in required_input_parameters:
            
            try:
                
                file_path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
                
            except HydrusExceptions.FileMissingException as e:
                
                raise HydrusExceptions.CannotProvideExecutableCallParameters( f'This call needs a file path, but the file {hash.hex()} appears to be missing!' ) from e
                
            
            file_uri = Path( file_path ).as_uri()
            
            file_paths.append( file_path )
            file_uris.append( file_uri )
            
        
    
    input_params: dict[ int, str | list[ str ] ] = dict()
    
    if ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATHS in required_input_parameters:
        
        input_params[ ClientExecutablePipelines.PARAMETER_TYPE_FILE_PATHS ] = file_paths
        
    
    if ClientExecutablePipelines.PARAMETER_TYPE_FILE_LOCAL_PATH_URIS in required_input_parameters:
        
        input_params[ ClientExecutablePipelines.PARAMETER_TYPE_FILE_LOCAL_PATH_URIS ] = file_uris
        
    
    call.Call( input_params )
    

def SendSingleURL( executable_manager: ClientExecutableManager.ExecutableManager, id_and_name: HydrusSerialisable.IdAndName, url: str ):
    
    try:
        
        call = executable_manager.GetCallable( id_and_name )
        
    except HydrusExceptions.DataMissing:
        
        raise HydrusExceptions.ExecutableException( f'When trying to open URL "{url}" externally, the executable we wanted to call ({id_and_name}) did not exist!' )
        
    
    if call.GetPipelineType() != ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_URL:
        
        raise HydrusExceptions.ExecutableException( f'When trying to open URL "{url}" externally, the executable we wanted to call ({id_and_name}) was the wrong type ({ClientExecutablePipelines.executable_pipeline_types_to_strs[call.GetPipelineType()]})!' )
        
    
    required_input_parameters = call.GetCall().GetInputParametersUsed()
    
    input_params: dict[ int, str | list[ str ] ] = dict()
    
    if ClientExecutablePipelines.PARAMETER_TYPE_URL in required_input_parameters:
        
        input_params[ ClientExecutablePipelines.PARAMETER_TYPE_URL ] = url
        
    
    call.Call( input_params )
    
