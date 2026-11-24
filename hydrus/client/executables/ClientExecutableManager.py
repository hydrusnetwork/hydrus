# TODO: defaults setup
# TODO: create on update/init, save to db
# TODO: recovery when missing/damaged
# TODO: UI and plugged into options dialog
# TODO: maybe some state management for our callables. is it ready, tested, invalid, what?
# TODO: recovery process, with UI handholding, for realigning ids and keys when some objects object wants to remap or resync or whatever
    # can write that tech in HydrusSerialisable tbh!
# TODO: availability testing in UI and state updates as a result

import threading

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable

from hydrus.client.executables import ClientExecutableActualCall
from hydrus.client.executables import ClientExecutableCallableSockets
from hydrus.client.executables import ClientExecutablePipelines

class ExecutableManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_MANAGER
    SERIALISABLE_NAME = 'Executable Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._callable_sockets: HydrusSerialisable.SerialisableList[ ClientExecutableCallableSockets.CallableSocket ] = HydrusSerialisable.SerialisableList()
        
        self._callable_ids_and_names_to_callable_sockets: dict[ HydrusSerialisable.IdAndName, ClientExecutableCallableSockets.CallableSocket ] = {}
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_callable_sockets = self._callable_sockets.GetSerialisableTuple()
        
        return serialisable_callable_sockets
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info: object, deserialisation_context: HydrusSerialisable.DeserialisationContext ):
        
        serialisable_callable_sockets = serialisable_info
        
        self._callable_sockets = HydrusSerialisable.CreateFromSerialisableTuple(
            serialisable_callable_sockets,
            deserialisation_context.DuplicateForNewWhitelist(
                {
                    HydrusSerialisable.SERIALISABLE_TYPE_LIST,
                    HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_CALLABLE_SOCKET
                }
            )
        )
        
        self._RegenCache()
        
    
    def _RegenCache( self ):
        
        self._callable_ids_and_names_to_callable_sockets = { c.GetIdAndName() : c for c in self._callable_sockets }
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def GetCallableSocket( self, id_and_name: HydrusSerialisable.IdAndName ) -> ClientExecutableCallableSockets.CallableSocket:
        
        with self._lock:
            
            if id_and_name in self._callable_ids_and_names_to_callable_sockets:
                
                return self._callable_ids_and_names_to_callable_sockets[ id_and_name ]
                
            
            raise HydrusExceptions.DataMissing( f'Did not have callable {id_and_name} in the executable manager!' )
            
        
    
    def GetCallableSockets( self ) -> list[ ClientExecutableCallableSockets.CallableSocket ]:
        
        with self._lock:
            
            return list( self._callable_sockets )
            
        
    
    def GetIdsAndNamesOfType( self, pipeline_type: int ):
        
        with self._lock:
            
            calls = sorted( [ call for call in self._callable_sockets if call.GetPipelineType() == pipeline_type ], key = lambda c: c.GetName() )
            
            ids_and_names = [ call.GetIdAndName() for call in calls ]
            
            return ids_and_names
            
        
    
    def GetOSCallableSocket( self, pipeline_type: int ):
        
        with self._lock:
            
            if pipeline_type == ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_FILE:
                
                results = [ call for call in self._callable_sockets if isinstance( call.GetCall(), ClientExecutableActualCall.LocalProcessDefaultLaunchFile ) ]
                
            elif pipeline_type == ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_URL:
                
                results = [ call for call in self._callable_sockets if isinstance( call.GetCall(), ClientExecutableActualCall.LocalProcessDefaultLaunchURL ) ]
                
            else:
                
                raise NotImplementedError( 'Unknown pipeline type!' )
                
            
            if len( results ) == 0:
                
                if pipeline_type == ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_FILE:
                    
                    actual_call = ClientExecutableActualCall.LocalProcessDefaultLaunchFile()
                    
                    call = ClientExecutableCallableSockets.CallableSocket(
                        'Default OS File Launch',
                        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_URL,
                        actual_call = actual_call
                    )
                    
                elif pipeline_type == ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_URL:
                    
                    actual_call = ClientExecutableActualCall.LocalProcessDefaultLaunchURL()
                    
                    call = ClientExecutableCallableSockets.CallableSocket(
                        'Default OS URL Launch',
                        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_URL,
                        actual_call = actual_call
                    )
                    
                else:
                    
                    raise NotImplementedError( 'Unknown pipeline type!' )
                    
                
                HydrusSerialisable.SetNonDupeName( call, { c.GetName() for c in self._callable_sockets } )
                
                self._callable_sockets.append( call )
                
                self._RegenCache()
                
                self._SetDirty()
                
            else:
                
                call = results[ 0 ]
                
            
            return call
            
        
    
    def GetOSLaunchFileCallableSocket( self ):
        
        return self.GetOSCallableSocket( ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_FILE )
        
    
    def GetOSLaunchURLCallableSocket( self ):
        
        return self.GetOSCallableSocket( ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_SEND_SINGLE_URL )
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def SetCallableSockets( self, callable_sockets: list[ ClientExecutableCallableSockets.CallableSocket ] ):
        
        with self._lock:
            
            self._callable_sockets = HydrusSerialisable.SerialisableList( callable_sockets )
            
            self._RegenCache()
            
            self._SetDirty()
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def WashIdsAndNames( self, pipeline_type: int, ids_and_names: list[ HydrusSerialisable.IdAndName ] ):
        
        # the caller has old ids_and_names and may need to update the names
        # this also clears out missing guys
        
        lookup = { call.GetIdAndName() : call for call in self._callable_sockets if call.GetPipelineType() == pipeline_type }
        
        actual_ids_and_names = []
        
        for id_and_name_old in ids_and_names:
            
            if id_and_name_old in lookup:
                
                actual_id_and_name = lookup[ id_and_name_old ].GetIdAndName()
                
                if actual_id_and_name not in actual_ids_and_names:
                    
                    actual_ids_and_names.append( actual_id_and_name )
                    
                
            else:
                
                # ruh roh, we do not have an entry. just by chance, is there something with the same name but a different id?
                # I was originally committed to a 'clever' wash where if there exists an entry with different id but same name, I'd remap. is this a wise idea? no
                
                pass
                
            
        
        return actual_ids_and_names
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_MANAGER ] = ExecutableManager
