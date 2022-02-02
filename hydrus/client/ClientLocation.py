import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC

class LocationContext( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_location_context
    SERIALISABLE_NAME = 'Location Search Context'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, current_service_keys = None, deleted_service_keys = None ):
        
        # note this is pretty much a read-only class
        # sometimes we'll run FixMissingServices, but usually only on load and who cares if that fix is propagated around
        # hence no need to duplicate this for every handler, since it won't be changing
        
        if current_service_keys is None:
            
            current_service_keys = []
            
        
        if deleted_service_keys is None:
            
            deleted_service_keys = []
            
        
        self.current_service_keys = frozenset( current_service_keys )
        self.deleted_service_keys = frozenset( deleted_service_keys )
        
        if self.IsAllKnownFiles():
            
            self.current_service_keys = frozenset( [ CC.COMBINED_FILE_SERVICE_KEY ] )
            self.deleted_service_keys = frozenset()
            
        
    
    def __eq__( self, other ):
        
        if isinstance( other, LocationContext ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        # works because frozenset
        return ( self.current_service_keys, self.deleted_service_keys ).__hash__()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_current_service_keys = [ service_key.hex() for service_key in self.current_service_keys ]
        serialisable_deleted_service_keys = [ service_key.hex() for service_key in self.deleted_service_keys ]
        
        return ( serialisable_current_service_keys, serialisable_deleted_service_keys )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_current_service_keys, serialisable_deleted_service_keys ) = serialisable_info
        
        self.current_service_keys = frozenset( { bytes.fromhex( service_key ) for service_key in serialisable_current_service_keys } )
        self.deleted_service_keys = frozenset( { bytes.fromhex( service_key ) for service_key in serialisable_deleted_service_keys } )
        
    
    def ClearAllLocalFilesServices( self, filter_func: typing.Callable ):
        
        if CC.COMBINED_LOCAL_FILE_SERVICE_KEY in self.current_service_keys:
            
            self.current_service_keys = frozenset( ( service_key for service_key in self.current_service_keys if filter_func( service_key ) ) )
            
        
        if CC.COMBINED_LOCAL_FILE_SERVICE_KEY in self.deleted_service_keys:
            
            self.deleted_service_keys = frozenset( ( service_key for service_key in self.deleted_service_keys if filter_func( service_key ) ) )
            
        
    
    def FixMissingServices( self, filter_method: typing.Callable ):
        
        self.current_service_keys = frozenset( filter_method( self.current_service_keys ) )
        self.deleted_service_keys = frozenset( filter_method( self.deleted_service_keys ) )
        
    
    def GetCoveringCurrentFileServiceKeys( self ):
        
        file_location_is_cross_referenced = not ( self.IsAllKnownFiles() or self.IncludesDeleted() )
        
        file_service_keys = list( self.current_service_keys )
        
        if self.IncludesDeleted():
            
            file_service_keys.append( CC.COMBINED_DELETED_FILE_SERVICE_KEY )
            
        
        return ( file_service_keys, file_location_is_cross_referenced )
        
    
    def IncludesCurrent( self ):
        
        return len( self.current_service_keys ) > 0
        
    
    def IncludesDeleted( self ):
        
        return len( self.deleted_service_keys ) > 0
        
    
    def IsAllKnownFiles( self ):
        
        return CC.COMBINED_FILE_SERVICE_KEY in self.current_service_keys
        
    
    def IsAllLocalFiles( self ):
        
        return self.IsOneDomain() and CC.COMBINED_LOCAL_FILE_SERVICE_KEY in self.current_service_keys
        
    
    def IsOneDomain( self ):
        
        return len( self.current_service_keys ) + len( self.deleted_service_keys ) == 1
        
    
    def SearchesAnything( self ):
        
        return len( self.current_service_keys ) + len( self.deleted_service_keys ) > 0
        
    
    def ToString( self, name_method ):
        
        # this probably needs some params for 'short string' and stuff later on
        
        if not self.SearchesAnything():
            
            return 'nothing'
            
        
        if self.IncludesCurrent() and self.IncludesDeleted():
            
            if self.current_service_keys == self.deleted_service_keys:
                
                prefix = 'current and deleted files of '
                
            else:
                
                prefix = 'a mix of current and deleted files of '
                
            
        elif self.IncludesDeleted():
            
            prefix = 'deleted files of '
            
        else:
            
            prefix = ''
            
        
        if self.current_service_keys == self.deleted_service_keys:
            
            service_keys_to_consider = self.current_service_keys
            
        else:
            
            service_keys_to_consider = self.current_service_keys.union( self.deleted_service_keys )
            
        
        if len( service_keys_to_consider ) <= 2:
            
            service_strings = sorted( ( name_method( service_key ) for service_key in service_keys_to_consider ) )
            
            service_string = ', '.join( service_strings )
            
        else:
            
            service_string = '{} services'.format( HydrusData.ToHumanInt( len( service_keys_to_consider ) ) )
            
        
        return prefix + service_string
        
    
    @staticmethod
    def STATICCreateAllCurrent( current_service_keys ) -> "LocationContext":
        
        return LocationContext( current_service_keys, [] )
        
    
    @staticmethod
    def STATICCreateSimple( file_service_key ) -> "LocationContext":
        
        return LocationContext( [ file_service_key ], [] )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_location_context ] = LocationContext

def GetLocationContextForAllLocalMedia() -> LocationContext:
    
    local_file_domain_service_keys = set( HG.client_controller.services_manager.GetServiceKeys( [ HC.LOCAL_FILE_DOMAIN ] ) )
    local_file_domain_service_keys.discard( CC.LOCAL_UPDATE_SERVICE_KEY )
    
    return LocationContext.STATICCreateAllCurrent( local_file_domain_service_keys )
    
