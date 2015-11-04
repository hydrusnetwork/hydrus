import collections
import hashlib
import httplib
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals
import HydrusNATPunch
import HydrusServer
import itertools
import os
import Queue
import random
import ServerFiles
import shutil
import sqlite3
import sys
import threading
import time
import traceback
import yaml

def DAEMONCheckDataUsage( controller ):
    
    controller.WriteSynchronous( 'check_data_usage' )
    
def DAEMONCheckMonthlyData( controller ):
    
    controller.WriteSynchronous( 'check_monthly_data' )
    
def DAEMONClearBans( controller ):
    
    controller.WriteSynchronous( 'clear_bans' )
    
def DAEMONDeleteOrphans( controller ):
    
    controller.WriteSynchronous( 'delete_orphans' )
    
def DAEMONFlushRequestsMade( controller, all_requests ):
    
    controller.WriteSynchronous( 'flush_requests_made', all_requests )
    
def DAEMONGenerateUpdates( controller ):
    
    if not HydrusGlobals.server_busy:
        
        update_ends = controller.Read( 'update_ends' )
        
        for ( service_key, biggest_end ) in update_ends.items():
            
            if HydrusGlobals.view_shutdown:
                
                return
                
            
            now = HydrusData.GetNow()
            
            next_begin = biggest_end + 1
            next_end = biggest_end + HC.UPDATE_DURATION
            
            HydrusGlobals.server_busy = True
            
            while next_end < now:
                
                controller.WriteSynchronous( 'create_update', service_key, next_begin, next_end )
                
                biggest_end = next_end
                
                now = HydrusData.GetNow()
                
                next_begin = biggest_end + 1
                next_end = biggest_end + HC.UPDATE_DURATION
                
            
            HydrusGlobals.server_busy = False
            
            time.sleep( 1 )
            
        
        time_to_stop = HydrusData.GetNow() + 30
        
        service_keys = controller.Read( 'service_keys', HC.REPOSITORIES )
        
        for service_key in service_keys:
            
            num_petitions = controller.Read( 'num_petitions', service_key )
            
            if num_petitions == 0:
                
                dirty_updates = controller.Read( 'dirty_updates', service_key )
                
                for ( begin, end ) in dirty_updates:
                    
                    if HydrusGlobals.view_shutdown or HydrusData.TimeHasPassed( time_to_stop ):
                        
                        return
                        
                    
                    HydrusGlobals.server_busy = True
                    
                    controller.WriteSynchronous( 'clean_update', service_key, begin, end )
                    
                    HydrusGlobals.server_busy = False
                    
                    time.sleep( 1 )
                    
                
            
        
    
def DAEMONUPnP( controller ):
    
    try:
        
        local_ip = HydrusNATPunch.GetLocalIP()
        
        current_mappings = HydrusNATPunch.GetUPnPMappings()
        
        our_mappings = { ( internal_client, internal_port ) : external_port for ( description, internal_client, internal_port, external_ip_address, external_port, protocol, enabled ) in current_mappings }
        
    except: return # This IGD probably doesn't support UPnP, so don't spam the user with errors they can't fix!
    
    services_info = controller.Read( 'services_info' )
    
    for ( service_key, service_type, options ) in services_info:
        
        internal_port = options[ 'port' ]
        upnp = options[ 'upnp' ]
        
        if ( local_ip, internal_port ) in our_mappings:
            
            current_external_port = our_mappings[ ( local_ip, internal_port ) ]
            
            if current_external_port != upnp: HydrusNATPunch.RemoveUPnPMapping( current_external_port, 'TCP' )
            
        
    
    for ( service_key, service_type, options ) in services_info:
        
        internal_port = options[ 'port' ]
        upnp = options[ 'upnp' ]
        
        if upnp is not None and ( local_ip, internal_port ) not in our_mappings:
            
            external_port = upnp
            
            protocol = 'TCP'
            
            description = HC.service_string_lookup[ service_type ] + ' at ' + local_ip + ':' + str( internal_port )
            
            duration = 3600
            
            HydrusNATPunch.AddUPnPMapping( local_ip, internal_port, external_port, protocol, description, duration = duration )
            
        
    