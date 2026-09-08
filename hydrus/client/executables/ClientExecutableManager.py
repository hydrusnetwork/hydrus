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
from hydrus.client.executables import ClientExecutableCallables
from hydrus.client.executables import ClientExecutablePipelines

class ExecutableManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_EXECUTABLE_MANAGER
    SERIALISABLE_NAME = 'Executable Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._callables: HydrusSerialisable.SerialisableList[ ClientExecutableCallables.ClientExecutableCallable ] = HydrusSerialisable.SerialisableList()
        
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
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def GetCallable( self, id_and_name: HydrusSerialisable.IdAndName ) -> ClientExecutableCallables.ClientExecutableCallable:
        
        with self._lock:
            
            if id_and_name in self._callable_ids_and_names_to_callables:
                
                return self._callable_ids_and_names_to_callables[ id_and_name ]
                
            
            raise HydrusExceptions.DataMissing( f'Did not have callable {id_and_name} in the executable manager!' )
            
        
    
    def GetCallables( self ) -> list[ ClientExecutableCallables.ClientExecutableCallable ]:
        
        with self._lock:
            
            return list( self._callables )
            
        
    
    def GetIdsAndNamesOfType( self, pipeline_type: int ):
        
        with self._lock:
            
            calls = sorted( [ call for call in self._callables if call.GetPipelineType() == pipeline_type ], key = lambda c: c.GetName() )
            
            ids_and_names = [ call.GetIdAndName() for call in calls ]
            
            return ids_and_names
            
        
    
    def GetOSCallable( self, pipeline_type: int ):
        
        with self._lock:
            
            if pipeline_type == ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE:
                
                results = [ call for call in self._callables if isinstance( call.GetCall(), ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchFile ) ]
                
            elif pipeline_type == ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL:
                
                results = [ call for call in self._callables if isinstance( call.GetCall(), ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchURL ) ]
                
            else:
                
                raise NotImplementedError( 'Unknown pipeline type!' )
                
            
            if len( results ) == 0:
                
                if pipeline_type == ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE:
                    
                    actual_call = ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchFile()
                    
                    call = ClientExecutableCallables.ClientExecutableCallable(
                        'Default OS File Launch',
                        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
                        actual_call = actual_call
                    )
                    
                elif pipeline_type == ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL:
                    
                    actual_call = ClientExecutableActualCall.ExecutableLocalProcessDefaultLaunchURL()
                    
                    call = ClientExecutableCallables.ClientExecutableCallable(
                        'Default OS URL Launch',
                        pipeline_type = ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL,
                        actual_call = actual_call
                    )
                    
                else:
                    
                    raise NotImplementedError( 'Unknown pipeline type!' )
                    
                
                HydrusSerialisable.SetNonDupeName( call, { c.GetName() for c in self._callables } )
                
                self._callables.append( call )
                
                self._RegenCache()
                
                self._SetDirty()
                
            else:
                
                call = results[ 0 ]
                
            
            return call
            
        
    
    def GetOSLaunchFileCallable( self ):
        
        return self.GetOSCallable( ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_FILE )
        
    
    def GetOSLaunchURLCallable( self ):
        
        return self.GetOSCallable( ClientExecutablePipelines.EXECUTABLE_PIPELINE_TYPE_OPEN_EXTERNALLY_SINGLE_URL )
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def SetCallables( self, callables: list[ ClientExecutableCallables.ClientExecutableCallable ] ):
        
        with self._lock:
            
            self._callables = HydrusSerialisable.SerialisableList( callables )
            
            self._RegenCache()
            
            self._SetDirty()
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def WashIdsAndNames( self, pipeline_type: int, ids_and_names: list[ HydrusSerialisable.IdAndName ] ):
        
        # the caller has old ids_and_names and may need to update the names
        # this also clears out missing guys
        
        lookup = { call.GetIdAndName() : call for call in self._callables if call.GetPipelineType() == pipeline_type }
        
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
