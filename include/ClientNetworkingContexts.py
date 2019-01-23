from . import ClientConstants as CC
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusSerialisable
import os

class NetworkContext( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_CONTEXT
    SERIALISABLE_NAME = 'Network Context'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, context_type = None, context_data = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.context_type = context_type
        self.context_data = context_data
        
    
    def __eq__( self, other ):
        
        return self.__hash__() == other.__hash__()
        
    
    def __hash__( self ):
        
        return ( self.context_type, self.context_data ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def __repr__( self ):
        
        return self.ToString()
        
    
    def _GetSerialisableInfo( self ):
        
        if self.context_data is None:
            
            serialisable_context_data = self.context_data
            
        else:
            
            if self.context_type in ( CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_SUBSCRIPTION ):
                
                serialisable_context_data = self.context_data
                
            else:
                
                serialisable_context_data = self.context_data.hex()
                
            
        
        return ( self.context_type, serialisable_context_data )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.context_type, serialisable_context_data ) = serialisable_info
        
        if serialisable_context_data is None:
            
            self.context_data = serialisable_context_data
            
        else:
            
            if self.context_type in ( CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_SUBSCRIPTION ):
                
                self.context_data = serialisable_context_data
                
            else:
                
                self.context_data = bytes.fromhex( serialisable_context_data )
                
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( context_type, serialisable_context_data ) = old_serialisable_info
            
            if serialisable_context_data is not None:
                
                # unicode subscription names were erroring on the hex call
                if context_type in ( CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_SUBSCRIPTION ):
                    
                    context_data = bytes.fromhex( serialisable_context_data )
                    
                    serialisable_context_data = context_data
                    
                
            
            new_serialisable_info = ( context_type, serialisable_context_data )
            
            return ( 2, new_serialisable_info )
            
        
    
    def IsDefault( self ):
        
        return self.context_data is None and self.context_type != CC.NETWORK_CONTEXT_GLOBAL
        
    
    def IsEphemeral( self ):
        
        return self.context_type in ( CC.NETWORK_CONTEXT_DOWNLOADER_PAGE, CC.NETWORK_CONTEXT_WATCHER_PAGE )
        
    
    def IsHydrus( self ):
        
        return self.context_type == CC.NETWORK_CONTEXT_HYDRUS
        
    
    def GetSummary( self ):
        
        summary = self.ToString()
        summary += os.linesep * 2
        summary += CC.network_context_type_description_lookup[ self.context_type ]
        
        return summary
        
    
    def ToHumanString( self ):
        
        if self.IsEphemeral():
            
            return CC.network_context_type_string_lookup[ self.context_type ] + ' instance'
            
        else:
            
            return self.ToString()
            
        
    
    def ToString( self ):
        
        if self.context_data is None:
            
            if self.context_type == CC.NETWORK_CONTEXT_GLOBAL:
                
                return 'global'
                
            else:
                
                return CC.network_context_type_string_lookup[ self.context_type ] + ' default'
                
            
        else:
            
            if self.context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                service_key = self.context_data
                
                services_manager = HG.client_controller.services_manager
                
                if services_manager.ServiceExists( service_key ):
                    
                    name = services_manager.GetName( service_key )
                    
                else:
                    
                    name = 'unknown service--probably deleted or an unusual test'
                    
                
            else:
                
                name = str( self.context_data )
                
            
            return CC.network_context_type_string_lookup[ self.context_type ] + ': ' + name
            
        
    
    @staticmethod
    def STATICGenerateForDomain( domain ):
        
        return NetworkContext( context_type = CC.NETWORK_CONTEXT_DOMAIN, context_data = domain )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_CONTEXT ] = NetworkContext

GLOBAL_NETWORK_CONTEXT = NetworkContext( CC.NETWORK_CONTEXT_GLOBAL )
