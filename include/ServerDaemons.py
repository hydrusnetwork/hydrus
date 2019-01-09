from . import HydrusConstants as HC
from . import HydrusGlobals as HG
from . import HydrusNATPunch

def DAEMONSaveDirtyObjects( controller ):
    
    controller.SaveDirtyObjects()
    
def DAEMONDeleteOrphans( controller ):
    
    controller.WriteSynchronous( 'delete_orphans' )
    
def DAEMONGenerateUpdates( controller ):
    
    if not HG.server_busy:
        
        HG.server_controller.SyncRepositories()
        
    
def DAEMONUPnP( controller ):
    
    try:
        
        local_ip = HydrusNATPunch.GetLocalIP()
        
        current_mappings = HydrusNATPunch.GetUPnPMappings()
        
        our_mappings = { ( internal_client, internal_port ) : external_port for ( description, internal_client, internal_port, external_ip_address, external_port, protocol, enabled ) in current_mappings }
        
    except:
        
        return # This IGD probably doesn't support UPnP, so don't spam the user with errors they can't fix!
        
    
    services = HG.server_controller.GetServices()
    
    for service in services:
        
        internal_port = service.GetPort()
        upnp_port = service.GetUPnPPort()
        
        if ( local_ip, internal_port ) in our_mappings:
            
            current_external_port = our_mappings[ ( local_ip, internal_port ) ]
            
            if upnp_port is None or upnp_port != current_external_port:
                
                HydrusNATPunch.RemoveUPnPMapping( current_external_port, 'TCP' )
                
            
        
    
    for service in services:
        
        internal_port = service.GetPort()
        upnp_port = service.GetUPnPPort()
        
        if upnp_port is not None and ( local_ip, internal_port ) not in our_mappings:
            
            external_port = upnp_port
            
            protocol = 'TCP'
            
            service_type = service.GetServiceType()
            
            description = HC.service_string_lookup[ service_type ] + ' at ' + local_ip + ':' + str( internal_port )
            
            duration = 3600
            
            HydrusNATPunch.AddUPnPMapping( local_ip, internal_port, external_port, protocol, description, duration = duration )
            
        
    
