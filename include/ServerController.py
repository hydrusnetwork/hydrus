from . import HydrusConstants as HC
from . import HydrusController
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNetworking
from . import HydrusSessions
from . import HydrusThreading
import os
from . import ServerDB
from . import ServerServer
import requests
import sys
import time
import traceback
import twisted.internet.ssl
from twisted.internet import reactor
from twisted.internet import defer

def ProcessStartingAction( db_dir, action ):
    
    already_running = HydrusData.IsAlreadyRunning( db_dir, 'server' )
    
    if action == 'start':
        
        if already_running:
            
            HydrusData.Print( 'The server is already running. Would you like to [s]top it, [r]estart it, or e[x]it?' )
            
            answer = input()
            
            if len( answer ) > 0:
                
                answer = answer[0]
                
                if answer == 's':
                    
                    return 'stop'
                    
                elif answer == 'r':
                    
                    return 'restart'
                    
                
            
            HG.shutting_down_due_to_already_running = True
            
            raise HydrusExceptions.ShutdownException( 'Exiting!' )
            
        else:
            
            return action
            
        
    elif action == 'stop':
        
        if already_running:
            
            return action
            
        else:
            
            raise HydrusExceptions.ShutdownException( 'The server is not running, so it cannot be stopped!' )
            
        
    elif action == 'restart':
        
        if already_running:
            
            return action
            
        else:
            
            return 'start'
            
        
    
def ShutdownSiblingInstance( db_dir ):
    
    port_found = False
    
    ports = HydrusData.GetSiblingProcessPorts( db_dir, 'server' )
    
    if ports is None:
        
        raise HydrusExceptions.ShutdownException( 'Could not figure out the existing server\'s ports, so could not shut it down!' )
        
    
    session = requests.Session()
    
    session.verify = False
    
    for port in ports:
        
        try:
            
            r = session.get( 'https://127.0.0.1:' + str( port ) + '/' )
            
            server_name = r.headers[ 'Server' ]
            
        except:
            
            text = 'Could not contact existing server\'s port ' + str( port ) + '!'
            text += os.linesep
            text += traceback.format_exc()
            
            raise HydrusExceptions.ShutdownException( text )
            
        
        if 'server administration' in server_name:
            
            port_found = True
            
            HydrusData.Print( 'Sending shut down instruction\u2026' )
            
            r = session.post( 'https://127.0.0.1:' + str( port ) + '/shutdown' )
            
            if not r.ok:
                
                text = 'When told to shut down, the existing server gave an error!'
                text += os.linesep
                text += r.text
                
                raise HydrusExceptions.ShutdownException( text )
                
            
            time_waited = 0
            
            while HydrusData.IsAlreadyRunning( db_dir, 'server' ):
                
                time.sleep( 1 )
                
                time_waited += 1
                
                if time_waited > 20:
                    
                    raise HydrusExceptions.ShutdownException( 'Attempted to shut the existing server down, but it took too long!' )
                    
                
            
            break
            
        
    
    if not port_found:
        
        raise HydrusExceptions.ShutdownException( 'The existing server did not have an administration service!' )
        
    
    HydrusData.Print( 'The existing server is shut down!' )
    
class Controller( HydrusController.HydrusController ):
    
    def __init__( self, db_dir ):
        
        HydrusController.HydrusController.__init__( self, db_dir )
        
        self._name = 'server'
        
        self._shutdown = False
        
        HG.server_controller = self
        
    
    def _GetUPnPServices( self ):
        
        return self._services
        
    
    def _InitDB( self ):
        
        return ServerDB.DB( self, self.db_dir, 'server' )
        
    
    def StartService( self, service ):
        
        def TWISTEDDoIt():
            
            service_key = service.GetServiceKey()
            service_type = service.GetServiceType()
            
            def Start( *args, **kwargs ):
                
                try:
                    
                    time.sleep( 1 )
                    
                    port = service.GetPort()
                    
                    if HydrusNetworking.LocalPortInUse( port ):
                        
                        raise Exception( 'Something was already bound to port ' + str( port ) )
                        
                    
                    if service_type == HC.SERVER_ADMIN:
                        
                        http_factory = ServerServer.HydrusServiceAdmin( service )
                        
                    elif service_type == HC.FILE_REPOSITORY:
                        
                        http_factory = ServerServer.HydrusServiceRepositoryFile( service )
                        
                    elif service_type == HC.TAG_REPOSITORY:
                        
                        http_factory = ServerServer.HydrusServiceRepositoryTag( service )
                        
                    else:
                        
                        return
                        
                    
                    ( ssl_cert_path, ssl_key_path ) = self.db.GetSSLPaths()
                    
                    sslmethod = twisted.internet.ssl.SSL.TLSv1_2_METHOD
                    
                    context_factory = twisted.internet.ssl.DefaultOpenSSLContextFactory( ssl_key_path, ssl_cert_path, sslmethod )
                    
                    self._service_keys_to_connected_ports[ service_key ] = reactor.listenSSL( port, http_factory, context_factory )
                    
                    if not HydrusNetworking.LocalPortInUse( port ):
                        
                        raise Exception( 'Tried to bind port ' + str( port ) + ' but it failed.' )
                        
                    
                except Exception as e:
                    
                    HydrusData.Print( traceback.format_exc() )
                    
                
            
            if service_key in self._service_keys_to_connected_ports:
                
                deferred = defer.maybeDeferred( self._service_keys_to_connected_ports[ service_key ].stopListening )
                
                deferred.addCallback( Start )
                
            else:
                
                Start()
                
            
            
        
        reactor.callFromThread( TWISTEDDoIt )
        
    
    def StopService( self, service_key ):
        
        def TWISTEDDoIt():
            
            deferred = defer.maybeDeferred( self._service_keys_to_connected_ports[ service_key ].stopListening )
            
            del self._service_keys_to_connected_ports[ service_key ]
            
        
        reactor.callFromThread( TWISTEDDoIt )
        
    
    def DeleteOrphans( self ):
        
        self.WriteSynchronous( 'delete_orphans' )
        
    
    def Exit( self ):
        
        HydrusData.Print( 'Shutting down daemons and services\u2026' )
        
        self.ShutdownView()
        
        HydrusData.Print( 'Shutting down db\u2026' )
        
        self.ShutdownModel()
        
        if not HG.shutting_down_due_to_already_running:
            
            HydrusData.CleanRunningFile( self.db_dir, 'server' )
            
        
    
    def GetFilesDir( self ):
        
        return self.db.GetFilesDir()
        
    
    def GetServices( self ):
        
        return list( self._services )
        
    
    def InitModel( self ):
        
        HydrusController.HydrusController.InitModel( self )
        
        self._services = self.Read( 'services' )
        
        [ self._admin_service ] = [ service for service in self._services if service.GetServiceType() == HC.SERVER_ADMIN ]
        
        self.server_session_manager = HydrusSessions.HydrusSessionManagerServer()
        
        self._service_keys_to_connected_ports = {}
        
    
    def InitView( self ):
        
        HydrusController.HydrusController.InitView( self )
        
        port = self._admin_service.GetPort()
        
        if HydrusNetworking.LocalPortInUse( port ):
            
            HydrusData.Print( 'Something is already bound to port ' + str( port ) + ', so your administration service cannot be started. Please quit the server and retry once the port is clear.' )
            
        else:
            
            for service in self._services:
                
                self.StartService( service )
                
            
        
        #
        
        job = self.CallRepeating( 5.0, 600.0, self.SyncRepositories )
        
        self._daemon_jobs[ 'sync_repositories' ] = job
        
        job = self.CallRepeating( 0.0, 30.0, self.SaveDirtyObjects )
        
        self._daemon_jobs[ 'save_dirty_objects' ] = job
        
        job = self.CallRepeating( 0.0, 86400.0, self.DeleteOrphans )
        
        self._daemon_jobs[ 'delete_orphans' ] = job
        
    
    def JustWokeFromSleep( self ):
        
        return False
        
    
    def MaintainDB( self, maintenance_mode = HC.MAINTENANCE_FORCED, stop_time = None ):
        
        stop_time = HydrusData.GetNow() + 10
        
        self.WriteSynchronous( 'analyze', maintenance_mode = maintenance_mode, stop_time = stop_time )
        
    
    def ReportDataUsed( self, num_bytes ):
        
        self._admin_service.ServerReportDataUsed( num_bytes )
        
    
    def ReportRequestUsed( self ):
        
        self._admin_service.ServerReportRequestUsed()
        
    
    def Run( self ):
        
        HydrusData.RecordRunningStart( self.db_dir, 'server' )
        
        HydrusData.Print( 'Initialising db\u2026' )
        
        self.InitModel()
        
        HydrusData.Print( 'Initialising daemons and services\u2026' )
        
        self.InitView()
        
        HydrusData.Print( 'Server is running. Press Ctrl+C to quit.' )
        
        try:
            
            while not self._model_shutdown and not self._shutdown:
            
                time.sleep( 1 )
                
            
        except KeyboardInterrupt:
            
            HydrusData.Print( 'Received a keyboard interrupt\u2026' )
            
        
        HydrusData.Print( 'Shutting down controller\u2026' )
        
        self.Exit()
        
    
    def SaveDirtyObjects( self ):
        
        with HG.dirty_object_lock:
            
            dirty_services = [ service for service in self._services if service.IsDirty() ]
            
            if len( dirty_services ) > 0:
                
                self.WriteSynchronous( 'dirty_services', dirty_services )
                
            
            dirty_accounts = self.server_session_manager.GetDirtyAccounts()
            
            if len( dirty_accounts ) > 0:
                
                self.WriteSynchronous( 'dirty_accounts', dirty_accounts )
                
            
        
    
    def ServerBandwidthOK( self ):
        
        return self._admin_service.ServerBandwidthOK()
        
    
    def SetServices( self, services ):
        
        # doesn't need the dirty_object_lock because the caller takes it
        
        self._services = services
        
        self.CallToThread( self.services_upnp_manager.SetServices, self._services )
        
        [ self._admin_service ] = [ service for service in self._services if service.GetServiceType() == HC.SERVER_ADMIN ]
        
        current_service_keys = set( self._service_keys_to_connected_ports.keys() )
        future_service_keys = set( [ service.GetServiceKey() for service in self._services ] )
        
        stop_service_keys = current_service_keys.difference( future_service_keys )
        
        for service_key in stop_service_keys:
            
            self.StopService( service_key )
            
        
        for service in self._services:
            
            self.StartService( service )
            
        
    
    def ShutdownView( self ):
        
        for service in self._services:
            
            service_key = service.GetServiceKey()
            
            if service_key in self._service_keys_to_connected_ports:
                
                self.StopService( service_key )
                
            
        
        HydrusController.HydrusController.ShutdownView( self )
        
    
    def ShutdownFromServer( self ):
        
        HydrusData.Print( 'Received a server shut down request\u2026' )
        
        self._shutdown = True
        
    
    def SyncRepositories( self ):
        
        if HG.server_busy:
            
            return
            
        
        repositories = [ service for service in self._services if service.GetServiceType() in HC.REPOSITORIES ]
        
        for service in repositories:
            
            service.Sync()
            
        
    
