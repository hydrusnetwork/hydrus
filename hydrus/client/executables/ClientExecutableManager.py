# TODO: defaults setup
# TODO: create on update/init, save to db
# TODO: recovery when missing/damaged
# TODO: UI and plugged into options dialog
# TODO: maybe some state management for our callables. is it ready, tested, invalid, what?
# TODO: recovery process, with UI handholding, for realigning ids and keys when some objects object wants to remap or resync or whatever
    # can write that tech in HydrusSerialisable tbh!
# TODO: availability testing in UI and state updates as a result

from pathlib import Path
import threading

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientGlobals as CG
from hydrus.client.executables import ClientExecutableCallables
from hydrus.client.executables import ClientExecutablePipelines
from hydrus.client.media import ClientMediaResult

class ExecutableManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_MANAGER
    SERIALISABLE_NAME = 'Executable Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._lock = threading.Lock()
        
        self._callables = HydrusSerialisable.SerialisableList()
        
        self._callable_ids_and_names_to_callables: dict[ HydrusSerialisable.IdAndName, ClientExecutableCallables.ClientExecutableCallable ] = {}
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_callables = self._callables.GetSerialisableTuple()
        
        return serialisable_callables
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_callables = serialisable_info
        
        self._callables = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_callables )
        
        self._RegenCache()
        
    
    def _RegenCache( self ):
        
        self._callable_ids_and_names_to_callables = { c.GetIdAndName() : c for c in self._callables }
        
    
    def GetCallable( self, id_and_name: HydrusSerialisable.IdAndName ) -> ClientExecutableCallables.ClientExecutableCallable:
        
        with self._lock:
            
            if id_and_name in self._callable_ids_and_names_to_callables:
                
                return self._callable_ids_and_names_to_callables[ id_and_name ]
                
            
            raise HydrusExceptions.DataMissing( f'Did not have callable {id_and_name} in the executable manager!' )
            
        
    
    def GetCallables( self ) -> list[ ClientExecutableCallables.ClientExecutableCallable ]:
        
        with self._lock:
            
            return list( self._callables )
            
        
    
    def SetCallables( self, callables: list[ ClientExecutableCallables.ClientExecutableCallable ] ):
        
        with self._lock:
            
            self._callables = HydrusSerialisable.SerialisableList( callables )
            
            self._RegenCache()
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_MANAGER ] = ExecutableManager

def OpenExternallySingleFile( executable_manager: ExecutableManager, id_and_name: HydrusSerialisable.IdAndName, media_result: ClientMediaResult.MediaResult ):
    
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
        ClientExecutablePipelines.PARAM_TYPE_FILE_PATH : file_path,
        ClientExecutablePipelines.PARAM_TYPE_FILE_LOCAL_PATH_URI : file_uri,
    }
    
    call.Call( input_params )
    

def OpenExternallyURL( executable_manager: ExecutableManager, id_and_name: HydrusSerialisable.IdAndName, url: str ):
    
    try:
        
        call = executable_manager.GetCallable( id_and_name )
        
    except HydrusExceptions.DataMissing:
        
        raise HydrusExceptions.ExecutableException( f'When trying to open URL "{url}" externally, the executable we wanted to call ({id_and_name}) did not exist!' )
        
    
    if call.GetPipelineType() != ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL:
        
        raise HydrusExceptions.ExecutableException( f'When trying to open URL "{url}" externally, the executable we wanted to call ({id_and_name}) was the wrong type ({ClientExecutablePipelines.executable_pipeline_types_to_strs[call.GetPipelineType()]})!' )
        
    
    input_params = {
        ClientExecutablePipelines.PARAM_TYPE_URL : url,
    }
    
    call.Call( input_params )
    
