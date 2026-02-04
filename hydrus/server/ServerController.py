import os
import requests
import time
import traceback

from twisted.internet import threads, reactor, defer

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusController
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSessions
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetwork
from hydrus.core.networking import HydrusNetworking
from hydrus.core.processes import HydrusProcess
from hydrus.core.processes import HydrusThreading

from hydrus.server import ServerDB
from hydrus.server import ServerFiles
from hydrus.server import ServerGlobals as SG
from hydrus.server.networking import ServerServer

def ProcessStartingAction( db_dir, action ):
    
    already_running = HydrusProcess.IsAlreadyRunning( db_dir, 'server' )
    
    if action == 'start':
        
        if already_running:
            
            HydrusData.Print( 'The server is already running. Would you like to [s]top it, [r]estart it here, or e[x]it?' )
            
            answer = input()
            
            if len( answer ) > 0:
                
                answer = answer[0]
                
                if answer == 's':
                    
                    return 'stop'
                    
                elif answer == 'r':
                    
                    return 'restart'
                    
                
            
            return 'exit'
            
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
            
            HydrusData.Print( 'Did not find an already running instance of the server--changing boot command from \'restart\' to \'start\'.' )
            
            return 'start'
            
        
    

def ShutdownSiblingInstance( db_dir ):
    
    port_found = False
    
    try:
        
        ports = HydrusProcess.GetSiblingProcessPorts( db_dir, 'server' )
        
    except HydrusExceptions.CancelledException as e:
        
        HydrusData.Print( e )
        
        ports = None
        
    
    if ports is None:
        
        raise HydrusExceptions.ShutdownException( 'Could not figure out the existing server\'s ports, so could not shut it down!' )
        
    
    session = requests.Session()
    
    session.verify = False
    
    for port in ports:
        
        try:
            
            r = session.get( 'https://127.0.0.1:' + str( port ) + '/' )
            
            server_name = r.headers[ 'Server' ]
            
        except Exception as e:
            
            text = 'Could not contact existing server\'s port ' + str( port ) + '!'
            text += '\n'
            text += traceback.format_exc()
            
            raise HydrusExceptions.ShutdownException( text )
            
        
        if 'server administration' in server_name:
            
            port_found = True
            
            HydrusData.Print( 'Sending shut down instruction' + HC.UNICODE_ELLIPSIS )
            
            r = session.post( 'https://127.0.0.1:' + str( port ) + '/shutdown' )
            
            if not r.ok:
                
                text = 'When told to shut down, the existing server gave an error!'
                text += '\n'
                text += r.text
                
                raise HydrusExceptions.ShutdownException( text )
                
            
            time_waited = 0
            
            while HydrusProcess.IsAlreadyRunning( db_dir, 'server' ):
                
                time.sleep( 1 )
                
                time_waited += 1
                
                if time_waited > 20:
                    
                    raise HydrusExceptions.ShutdownException( 'Attempted to shut the existing server down, but it took too long!' )
                    
                
            
            break
            
        
    
    if not port_found:
        
        raise HydrusExceptions.ShutdownException( 'The existing server did not have an administration service!' )
        
    
    HydrusData.Print( 'The existing server is shut down!' )
    

class Controller( HydrusController.HydrusController ):
    
    def __init__( self, db_dir, logger ):
        
        super().__init__( db_dir, logger )
        
        self._name = 'server'
        
        self._shutdown = False
        
        SG.server_controller = self
        
        self.CallToThreadLongRunning( self.DAEMONPubSub )
        
    
    def _GetUPnPServices( self ):
        
        return self._services
        
    
    def _InitDB( self ):
        
        self.db = ServerDB.DB( self, self.db_dir, 'server' )
        
    
    def DAEMONPubSub( self ):
        
        while not HG.model_shutdown:
            
            if self._pubsub.WorkToDo():
                
                try:
                    
                    self._pubsub.Process()
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e, do_wait = True )
                    
                
            else:
                
                self._pubsub.WaitOnPub()
                
            
        
    
    def DoDeferredPhysicalDeletes( self ):
        
        num_files_deleted = 0
        num_thumbnails_deleted = 0
        
        pauser = HydrusThreading.BigJobPauser()
        
        ( file_hash, thumbnail_hash ) = self.Read( 'deferred_physical_delete' )
        
        while ( file_hash is not None or thumbnail_hash is not None ) and not HG.started_shutdown:
            
            if file_hash is not None:
                
                path = ServerFiles.GetExpectedFilePath( file_hash )
                
                if os.path.exists( path ):
                    
                    HydrusPaths.RecyclePath( path )
                    
                    num_files_deleted += 1
                    
                
            
            if thumbnail_hash is not None:
                
                path = ServerFiles.GetExpectedThumbnailPath( thumbnail_hash )
                
                if os.path.exists( path ):
                    
                    HydrusPaths.RecyclePath( path )
                    
                    num_thumbnails_deleted += 1
                    
                
            
            self.WriteSynchronous( 'clear_deferred_physical_delete', file_hash = file_hash, thumbnail_hash = thumbnail_hash )
            
            ( file_hash, thumbnail_hash ) = self.Read( 'deferred_physical_delete' )
            
            pauser.Pause()
            
        
        if num_files_deleted > 0 or num_thumbnails_deleted > 0:
            
            HydrusData.Print( 'Physically deleted {} files and {} thumbnails from file storage.'.format( HydrusNumbers.ToHumanInt( num_files_deleted ), HydrusNumbers.ToHumanInt( num_files_deleted ) ) )
            
        
    
    def Exit( self ):
        
        HG.started_shutdown = True
        
        self.SaveDirtyObjects()
        
        HydrusData.Print( 'Shutting down daemons' + HC.UNICODE_ELLIPSIS )
        
        self.ShutdownView()
        
        HydrusData.Print( 'Shutting down db' + HC.UNICODE_ELLIPSIS )
        
        self.ShutdownModel()
        
        self.CleanRunningFile()
        
    
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
            
            self.RestartServices()
            
        
        #
        
        job = self.CallRepeating( 5.0, HydrusNetwork.UPDATE_CHECKING_PERIOD, self.SyncRepositories )
        job.WakeOnPubSub( 'notify_new_repo_sync' )
        
        self._daemon_jobs[ 'sync_repositories' ] = job
        
        job = self.CallRepeating( 0.0, 30.0, self.SaveDirtyObjects )
        
        self._daemon_jobs[ 'save_dirty_objects' ] = job
        
        job = self.CallRepeating( 30.0, 86400.0, self.DoDeferredPhysicalDeletes )
        job.WakeOnPubSub( 'notify_new_physical_file_deletes' )
        
        self._daemon_jobs[ 'deferred_physical_deletes' ] = job
        
        job = self.CallRepeating( 120.0, 3600.0 * 4, self.NullifyHistory )
        job.WakeOnPubSub( 'notify_new_nullification' )
        
        self._daemon_jobs[ 'nullify_history' ] = job
        
    
    def JustWokeFromSleep( self ):
        
        return False
        
    
    def MaintainDB( self, maintenance_mode = HC.MAINTENANCE_FORCED, stop_time = None ):
        
        stop_time = HydrusTime.GetNow() + 10
        
        self.WriteSynchronous( 'analyze', maintenance_mode = maintenance_mode, stop_time = stop_time )
        
    
    def NullifyHistory( self ):
        
        repositories = [ service for service in self._services if service.GetServiceType() in HC.REPOSITORIES ]
        
        for service in repositories:
            
            service.NullifyHistory()
            
        
    
    def ReportDataUsed( self, num_bytes ):
        
        self._admin_service.ServerReportDataUsed( num_bytes )
        
    
    def ReportRequestUsed( self ):
        
        self._admin_service.ServerReportRequestUsed()
        
    
    def RestartServices( self ):
        
        self.SetRunningTwistedServices( self._services )
        
    
    def Run( self ):
        
        self.RecordRunningStart()
        
        HydrusData.Print( 'Initialising db' + HC.UNICODE_ELLIPSIS )
        
        self.InitModel()
        
        HydrusData.Print( 'Initialising workers' + HC.UNICODE_ELLIPSIS )
        
        self.InitView()
        
        HydrusData.Print( 'Server is running. Press Ctrl+C to quit.' )
        
        try:
            
            while not HG.model_shutdown and not self._shutdown:
                
                time.sleep( 1 )
                
            
        except KeyboardInterrupt:
            
            HydrusData.Print( 'Received a keyboard interrupt' + HC.UNICODE_ELLIPSIS )
            
        
        HydrusData.Print( 'Shutting down controller' + HC.UNICODE_ELLIPSIS )
        
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
        
    
    def SetRunningTwistedServices( self, services ):
        
        def TWISTEDDoIt():
            
            def StartServices( *args, **kwargs ):
                
                HydrusData.Print( 'Starting services' + HC.UNICODE_ELLIPSIS )
                
                for service in services:
                    
                    service_key = service.GetServiceKey()
                    service_type = service.GetServiceType()
                    
                    name = service.GetName()
                    
                    try:
                        
                        port = service.GetPort()
                        
                        if service_type == HC.SERVER_ADMIN:
                            
                            http_factory = ServerServer.HydrusServiceAdmin( service )
                            
                        elif service_type == HC.FILE_REPOSITORY:
                            
                            http_factory = ServerServer.HydrusServiceRepositoryFile( service )
                            
                        elif service_type == HC.TAG_REPOSITORY:
                            
                            http_factory = ServerServer.HydrusServiceRepositoryTag( service )
                            
                        else:
                            
                            return
                            
                        
                        from hydrus.core.networking import HydrusServerContextFactory
                        
                        ( ssl_cert_path, ssl_key_path ) = self.db.GetSSLPaths()
                        
                        context_factory = HydrusServerContextFactory.GenerateSSLContextFactory( ssl_cert_path, ssl_key_path )
                        
                        ipv6_port = None
                        
                        try:
                            
                            ipv6_port = reactor.listenSSL( port, http_factory, context_factory, interface = '::' )
                            
                        except Exception as e:
                            
                            HydrusData.Print( 'Could not bind to IPv6:' )
                            
                            HydrusData.Print( str( e ) )
                            
                        
                        ipv4_port = None
                        
                        try:
                            
                            ipv4_port = reactor.listenSSL( port, http_factory, context_factory )
                            
                        except Exception as e:
                            
                            if ipv6_port is None:
                                
                                raise
                                
                            
                        
                        self._service_keys_to_connected_ports[ service_key ] = ( ipv4_port, ipv6_port )
                        
                        if HydrusNetworking.LocalPortInUse( port ):
                            
                            HydrusData.Print( 'Running "{}" on port {}.'.format( name, port ) )
                            
                        else:
                            
                            raise Exception( 'Tried to bind port {} for "{}" but it failed.'.format( port, name ) )
                            
                        
                    except Exception as e:
                        
                        HydrusData.Print( traceback.format_exc() )
                        
                    
                
                HydrusData.Print( 'Services started' )
                
            
            if len( self._service_keys_to_connected_ports ) > 0:
                
                HydrusData.Print( 'Stopping services' + HC.UNICODE_ELLIPSIS )
                
                deferreds = []
                
                for ( ipv4_port, ipv6_port ) in self._service_keys_to_connected_ports.values():
                    
                    if ipv4_port is not None:
                        
                        deferred = defer.maybeDeferred( ipv4_port.stopListening )
                        
                        deferreds.append( deferred )
                        
                    
                    if ipv6_port is not None:
                        
                        deferred = defer.maybeDeferred( ipv6_port.stopListening )
                        
                        deferreds.append( deferred )
                        
                    
                
                self._service_keys_to_connected_ports = {}
                
                deferred = defer.DeferredList( deferreds )
                
                if len( services ) > 0:
                    
                    deferred.addCallback( StartServices )
                    
                
            elif len( services ) > 0:
                
                StartServices()
                
            
        
        threads.blockingCallFromThread( reactor, TWISTEDDoIt )
        
    
    def SetServices( self, services ):
        
        # doesn't need the dirty_object_lock because the caller takes it
        
        # first test available ports
        
        my_ports = { s.GetPort() for s in self._services }
        
        for service in services:
            
            port = service.GetPort()
            
            if port not in my_ports and HydrusNetworking.LocalPortInUse( port ):
                
                raise HydrusExceptions.ServerException( 'Something was already bound to port ' + str( port ) )
                
            
        
        #
        
        self._services = services
        
        self.CallToThread( self.services_upnp_manager.SetServices, self._services )
        
        [ self._admin_service ] = [ service for service in self._services if service.GetServiceType() == HC.SERVER_ADMIN ]
        
        self.RestartServices()
        
    
    def ShutdownView( self ):
        
        try:
            
            self.SetRunningTwistedServices( [] )
            
        except Exception as e:
            
            pass # sometimes this throws a wobbler, screw it
            
        
        HydrusController.HydrusController.ShutdownView( self )
        
    
    def ShutdownFromServer( self ):
        
        HydrusData.Print( 'Received a server shut down request' + HC.UNICODE_ELLIPSIS )
        
        self._shutdown = True
        
    
    def SyncRepositories( self ):
        
        repositories = [ service for service in self._services if service.GetServiceType() in HC.REPOSITORIES ]
        
        for service in repositories:
            
            service.Sync()
            
        
    
