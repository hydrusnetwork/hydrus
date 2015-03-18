import collections
import dircache
import hashlib
import httplib
import HydrusConstants as HC
import HydrusExceptions
import HydrusFileHandling
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
import wx

def DAEMONCheckDataUsage(): HC.app.WriteDaemon( 'check_data_usage' )

def DAEMONCheckMonthlyData(): HC.app.WriteDaemon( 'check_monthly_data' )

def DAEMONClearBans(): HC.app.WriteDaemon( 'clear_bans' )

def DAEMONDeleteOrphans(): HC.app.WriteDaemon( 'delete_orphans' )

def DAEMONFlushRequestsMade( all_requests ): HC.app.WriteDaemon( 'flush_requests_made', all_requests )

def DAEMONGenerateUpdates():
    
    dirty_updates = HC.app.ReadDaemon( 'dirty_updates' )
    
    for ( service_key, tuples ) in dirty_updates.items():
        
        for ( begin, end ) in tuples: HC.app.WriteDaemon( 'clean_update', service_key, begin, end )
        
    
    update_ends = HC.app.ReadDaemon( 'update_ends' )
    
    for ( service_key, biggest_end ) in update_ends.items():
        
        now = HC.GetNow()
        
        next_begin = biggest_end + 1
        next_end = biggest_end + HC.UPDATE_DURATION
        
        while next_end < now:
            
            HC.app.WriteDaemon( 'create_update', service_key, next_begin, next_end )
            
            biggest_end = next_end
            
            now = HC.GetNow()
            
            next_begin = biggest_end + 1
            next_end = biggest_end + HC.UPDATE_DURATION
            
        
    
def DAEMONUPnP():
    
    try:
        
        local_ip = HydrusNATPunch.GetLocalIP()
        
        current_mappings = HydrusNATPunch.GetUPnPMappings()
        
        our_mappings = { ( internal_client, internal_port ) : external_port for ( description, internal_client, internal_port, external_ip_address, external_port, protocol, enabled ) in current_mappings }
        
    except: return # This IGD probably doesn't support UPnP, so don't spam the user with errors they can't fix!
    
    services_info = HC.app.ReadDaemon( 'services_info' )
    
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
            
        
    