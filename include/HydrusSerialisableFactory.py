import json
import HydrusData

# have upgrade code as funcs here, or include inside the factory. think about it

# stick type_ids in HC I think
# and objects and serialisable interface to hydrusdata

class SerialisableFactory( object ):
    
    def __init__( self ):
        
        self._type_id_to_version = {}
        
        self._type_id_to_type = {}
        
        self._type_to_type_id = {}
        
        # init these dicts
        
    
    def _CreateObject( self, type_id, name, info ):
        
        obj_type = self._type_id_to_type[ type_id ]
        
        obj = obj_type( name, info )
        
        return obj
        
    
    def _PrepareInfo( self, type_id, info ):
        
        sanitised_info = dict( info )
        
        # some types may need conversion, like tuples or whatever
        
        return sanitised_info
        
    
    def _LoadInfo( self, type_id, version, info_string ):
        
        info = json.loads( info_string )
        
        # some types may need conversion, like tuples or whatever
        # also do update step here
        
        return info
        
    
    def SerialiseForDB( self, obj ):
        
        type_id = self._type_to_type_id[ type( obj ) ]
        version = self._type_id_to_version[ type_id ]
        name = obj.GetName()
        info = obj.GetInfo()
        
        sanitised_info = self._PrepareInfo( type_id, info )
        
        info_string = json.dumps( sanitised_info )
        
        return ( type_id, version, name, info_string )
        
    
    def LoadFromDB( self, type_id, version, name, info_string ):
        
        sanitised_info = json.loads( info_string )
        
        info = self._LoadInfo( type_id, version, info_string )
        
        obj = self._CreateObject( type_id, name, info )
        
        return obj
        
    