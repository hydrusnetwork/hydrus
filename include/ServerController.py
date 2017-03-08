import httplib
import HydrusConstants as HC
import HydrusController
import HydrusData
import HydrusExceptions
import HydrusGlobals
import HydrusNetworking
import HydrusSessions
import HydrusThreading
import os
import ServerDaemons
import ServerDB
import ServerServer
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
            
            answer = raw_input()
            
            if len( answer ) > 0:
                
                answer = answer[0]
                
                if answer == 's':
                    
                    return 'stop'
                    
                elif answer == 'r':
                    
                    return 'restart'
                    
                
            
            raise HydrusExceptions.PermissionException( 'Exiting!' )
            
        else:
            
            return action
            
        
    elif action == 'stop':
        
        if already_running:
            
            return action
            
        else:
            
            raise HydrusExceptions.PermissionException( 'The server is not running, so it cannot be stopped!' )
            
        
    elif action == 'restart':
        
        if already_running:
            
            return action
            
        else:
            
            return 'start'
            
        
    
def ShutdownSiblingInstance( db_dir ):
    
    port_found = False
    
    ports = HydrusData.GetSiblingProcessPorts( db_dir, 'server' )
    
    if ports is None:
        
        raise HydrusExceptions.PermissionException( 'Could not figure out the existing server\'s ports, so could not shut it down!' )
        
    
    for port in ports:
        
        try:
            
            connection = HydrusNetworking.GetLocalConnection( port, https = True )
            
            connection.request( 'GET', '/' )
            
            response = connection.getresponse()
            
            response.read()
            
            server_name = response.getheader( 'Server' )
            
        except:
            
            text = 'Could not contact existing server\'s port ' + str( port ) + '!'
            text += os.linesep
            text += traceback.format_exc()
            
            raise HydrusExceptions.PermissionException( text )
            
        
        if 'server administration' in server_name:
            
            port_found = True
            
            HydrusData.Print( u'Sending shut down instruction\u2026' )
            
            connection.request( 'POST', '/shutdown' )
            
            response = connection.getresponse()
            
            result = response.read()
            
            if response.status != 200:
                
                text = 'When told to shut down, the existing server gave an error!'
                text += os.linesep
                text += result
                
                raise HydrusExceptions.PermissionException( text )
                
            
            time_waited = 0
            
            while HydrusData.IsAlreadyRunning( db_dir, 'server' ):
                
                time.sleep( 1 )
                
                time_waited += 1
                
                if time_waited > 20:
                    
                    raise HydrusExceptions.PermissionException( 'Attempted to shut the existing server down, but it took too long!' )
                    
                
            
            break
            
        
    
    if not port_found:
        
        raise HydrusExceptions.PermissionException( 'The existing server did not have an administration service!' )
        
    
    HydrusData.Print( 'The existing server is shut down!' )
    
class Controller( HydrusController.HydrusController ):
    
    def __init__( self, db_dir, no_daemons, no_wal ):
        
        HydrusController.HydrusController.__init__( self, db_dir, no_daemons, no_wal )
        
        self._name = 'server'
        
        HydrusGlobals.server_controller = self
        
    
    def _InitDB( self ):
        
        return ServerDB.DB( self, self._db_dir, 'server', no_wal = self._no_wal )
        
    
    def StartService( self, service ):
        
        def TWISTEDDoIt():
            
            service_key = service.GetServiceKey()
            service_type = service.GetServiceType()
            
            def Start( *args, **kwargs ):
                
                try:
                    
                    port = service.GetPort()
                    
                    try:
                        
                        connection = HydrusNetworking.GetLocalConnection( port )
                        connection.close()
                        
                        raise Exception( 'Something was already bound to port ' + str( port ) )
                        
                    except:
                        
                        if service_type == HC.SERVER_ADMIN:
                            
                            http_factory = ServerServer.HydrusServiceAdmin( service )
                            
                        elif service_type == HC.FILE_REPOSITORY:
                            
                            http_factory = ServerServer.HydrusServiceRepositoryFile( service )
                            
                        elif service_type == HC.TAG_REPOSITORY:
                            
                            http_factory = ServerServer.HydrusServiceRepositoryTag( service )
                            
                        else:
                            
                            return
                            
                        
                        ( ssl_cert_path, ssl_key_path ) = self._db.GetSSLPaths()
                        
                        context_factory = twisted.internet.ssl.DefaultOpenSSLContextFactory( ssl_key_path, ssl_cert_path )
                        
                        self._service_keys_to_connected_ports[ service_key ] = reactor.listenSSL( port, http_factory, context_factory )
                        
                        try:
                            
                            connection = HydrusNetworking.GetLocalConnection( port )
                            connection.close()
                            
                        except:
                            
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
        
    
    def Exit( self ):
        
        HydrusData.Print( u'Shutting down daemons and services\u2026' )
        
        self.ShutdownView()
        
        HydrusData.Print( u'Shutting down db\u2026' )
        
        self.ShutdownModel()
        
        HydrusData.CleanRunningFile( self._db_dir, 'server' )
        
    
    def GetFilesDir( self ):
        
        return self._db.GetFilesDir()
        
    
    def GetServerSessionManager( self ):
        
        return self._server_session_manager
        
    
    def InitModel( self ):
        
        HydrusController.HydrusController.InitModel( self )
        
        self._server_session_manager = HydrusSessions.HydrusSessionManagerServer()
        
        self._service_keys_to_connected_ports = {}
        
    
    def InitView( self ):
        
        HydrusController.HydrusController.InitView( self )
        
        if not self._no_daemons:
            
            self._daemons.append( HydrusThreading.DAEMONWorker( self, 'DeleteOrphans', ServerDaemons.DAEMONDeleteOrphans, period = 86400 ) )
            self._daemons.append( HydrusThreading.DAEMONWorker( self, 'GenerateUpdates', ServerDaemons.DAEMONGenerateUpdates, period = 600, init_wait = 10 ) )
            self._daemons.append( HydrusThreading.DAEMONWorker( self, 'SaveDirtyObjects', ServerDaemons.DAEMONSaveDirtyObjects, period = 30 ) )
            self._daemons.append( HydrusThreading.DAEMONWorker( self, 'UPnP', ServerDaemons.DAEMONUPnP, ( 'notify_new_options', ), period = 43200 ) )
            
        
        #
        
        self._services = self.Read( 'services' )
        
        [ self._admin_service ] = [ service for service in self._services if service.GetServiceType() == HC.SERVER_ADMIN ]
        
        port = self._admin_service.GetPort()
        
        already_bound = False
        
        try:
            
            connection = HydrusNetworking.GetLocalConnection( port )
            connection.close()
            
            already_bound = True
            
        except:
            
            pass
            
        
        if already_bound:
            
            HydrusData.Print( 'Something is already bound to port ' + str( port ) + ', so your administration service cannot be started. Please quit the server and retry once the port is clear.' )
            
        else:
            
            for service in self._services:
                
                self.StartService( service )
                
            
        
    
    def JustWokeFromSleep( self ): return False
    
    def MaintainDB( self, stop_time = None ):
        
        stop_time = HydrusData.GetNow() + 10
        
        self.WriteSynchronous( 'analyze', stop_time )
        
    
    def NotifyPubSubs( self ):
        
        self.CallToThread( self.ProcessPubSub )
        
    
    def RequestMade( self, num_bytes ):
        
        self._admin_service.ServerRequestMade( num_bytes )
        
    
    def Run( self ):
        
        HydrusData.RecordRunningStart( self._db_dir, 'server' )
        
        HydrusData.Print( u'Initialising db\u2026' )
        
        self.InitModel()
        
        HydrusData.Print( u'Initialising daemons and services\u2026' )
        
        self.InitView()
        
        HydrusData.Print( 'Server is running. Press Ctrl+C to quit.' )
        
        interrupt_received = False
        
        while not self._model_shutdown:
            
            try:
                
                time.sleep( 1 )
                
            except KeyboardInterrupt:
                
                if not interrupt_received:
                    
                    interrupt_received = True
                    
                    HydrusData.Print( u'Received a keyboard interrupt\u2026' )
                    
                    def do_it():
                        
                        self.Exit()
                        
                    
                    self.CallToThread( do_it )
                    
                
            
        
        HydrusData.Print( u'Shutting down controller\u2026' )
        
    
    def SaveDirtyObjects( self ):
        
        with HydrusGlobals.dirty_object_lock:
            
            dirty_services = [ service for service in self._services if service.IsDirty() ]
            
            if len( dirty_services ) > 0:
                
                self.WriteSynchronous( 'dirty_services', dirty_services )
                
            
            dirty_accounts = self._server_session_manager.GetDirtyAccounts()
            
            if len( dirty_accounts ) > 0:
                
                self.WriteSynchronous( 'dirty_accounts', dirty_accounts )
                
            
        
    
    def ServerBandwidthOk( self ):
        
        return self._admin_service.ServerBandwidthOk()
        
    
    def SetServices( self, services ):
        
        self._services = services
        
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
        
        HydrusData.Print( u'Received a server shut down request\u2026' )
        
        def do_it():
            
            time.sleep( 1 )
            
            self.Exit()
            
        
        self.CallToThread( do_it )
        
    
    def SyncRepositories( self ):
        
        repositories = [ service for service in self._services if service.GetServiceType() in HC.REPOSITORIES ]
        
        for service in repositories:
            
            service.Sync()
            
        
    
    def UpdateAccounts( self, service_key, accounts ):
        
        self._server_session_manager.UpdateAccounts( service_key, accounts )
        
