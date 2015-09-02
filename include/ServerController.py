import httplib
import HydrusConstants as HC
import HydrusController
import HydrusData
import HydrusExceptions
import HydrusGlobals
import HydrusNetworking
import HydrusServer
import HydrusSessions
import HydrusThreading
import os
import ServerDaemons
import ServerDB
import sys
import time
import traceback
from twisted.internet import reactor
from twisted.internet import defer

def GetStartingAction():
    
    action = None
    
    args = sys.argv[1:]
    
    if len( args ) > 0:
        
        command = args[0]
        
        while command.startswith( '-' ):
            
            command = command[ 1: ]
            
        
        if command == 'help':
            
            action = 'help'
            
        else:
            
            already_running = HydrusData.IsAlreadyRunning( 'server' )
            
            if command == 'start':
                
                if already_running:
                    
                    raise HydrusExceptions.PermissionException( 'The server is already running!' )
                    
                else:
                    
                    action = None
                    
                
            elif command == 'stop':
                
                if already_running:
                    
                    action = 'stop'
                    
                else:
                    
                    raise HydrusExceptions.PermissionException( 'The server is not running, so it cannot be stopped!' )
                    
                
            elif command == 'restart':
                
                if already_running:
                    
                    action = 'restart'
                    
                else:
                    
                    action = 'start'
                    
                
            
        
    else:
        
        already_running = HydrusData.IsAlreadyRunning( 'server' )
        
        if not already_running:
            
            action = 'start'
            
        else:
            
            print( 'The server is already running. Would you like to [s]top it, or [r]estart it?' )
            
            answer = raw_input()
            
            if len( answer ) > 0:
                
                answer = answer[0]
                
                if answer == 's':
                    
                    action = 'stop'
                    
                elif answer == 'r':
                    
                    action = 'restart'
                    
                
            
        
    
    return action
    
class Controller( HydrusController.HydrusController ):
    
    def _InitDB( self ):
        
        return ServerDB.DB( self )
        
    
    def ActionService( self, service_key, action ):
        
        if action != 'stop': ( service_type, options ) = self.Read( 'service_info', service_key )
        
        def TWISTEDDoIt():
            
            def StartService( *args, **kwargs ):
                
                try:
                    
                    if 'port' not in options: return
                    
                    port = options[ 'port' ]
                    
                    try:
                        
                        connection = HydrusNetworking.GetLocalConnection( port )
                        connection.close()
                        
                        raise Exception( 'Something was already bound to port ' + HydrusData.ToString( port ) )
                        
                    except:
                        
                        message = options[ 'message' ]
                        
                        if service_type == HC.SERVER_ADMIN: service_object = HydrusServer.HydrusServiceAdmin( service_key, service_type, message )
                        elif service_type == HC.FILE_REPOSITORY: service_object = HydrusServer.HydrusServiceRepositoryFile( service_key, service_type, message )
                        elif service_type == HC.TAG_REPOSITORY: service_object = HydrusServer.HydrusServiceRepositoryTag( service_key, service_type, message )
                        elif service_type == HC.MESSAGE_DEPOT: return
                        
                        self._services[ service_key ] = reactor.listenTCP( port, service_object )
                        
                        try:
                            
                            connection = HydrusNetworking.GetLocalConnection( port )
                            connection.close()
                            
                        except:
                            
                            raise Exception( 'Tried to bind port ' + HydrusData.ToString( port ) + ' but it failed.' )
                            
                        
                    
                except Exception as e:
                    
                    print( traceback.format_exc() )
                    
                
            
            if action == 'start': StartService()
            else:
                
                deferred = defer.maybeDeferred( self._services[ service_key ].stopListening )
                
                if action == 'restart': deferred.addCallback( StartService )
                elif action == 'stop': del self._services[ service_key ]
                
            
        
        reactor.callFromThread( TWISTEDDoIt )
        
    
    def CheckIfAdminPortInUse( self ):
        
        ( service_type, options ) = self.Read( 'service_info', HC.SERVER_ADMIN_KEY )
        
        port = options[ 'port' ]
        
        already_bound = False
        
        try:
            
            connection = HydrusNetworking.GetLocalConnection( port )
            connection.close()
            
            already_bound = True
            
        except: pass
        
        if already_bound:
            
            raise HydrusExceptions.PermissionException( 'Something was already bound to port ' + HydrusData.ToString( port ) )
            
        
    
    def Exit( self ):
        
        self.ShutdownView()
        
        self.ShutdownModel()
        
    
    def InitModel( self ):
        
        HydrusController.HydrusController.InitModel( self )
        
        self._managers[ 'restricted_services_sessions' ] = HydrusSessions.HydrusSessionManagerServer()
        self._managers[ 'messaging_sessions' ] = HydrusSessions.HydrusMessagingSessionManagerServer()
        
        self._services = {}
        
        self.sub( self, 'ActionService', 'action_service' )
        
    
    def InitView( self ):
        
        HydrusController.HydrusController.InitView( self )
        
        self._daemons.append( HydrusThreading.DAEMONQueue( self, 'FlushRequestsMade', ServerDaemons.DAEMONFlushRequestsMade, 'request_made', period = 60 ) )
        
        self._daemons.append( HydrusThreading.DAEMONWorker( self, 'CheckMonthlyData', ServerDaemons.DAEMONCheckMonthlyData, period = 3600 ) )
        self._daemons.append( HydrusThreading.DAEMONWorker( self, 'ClearBans', ServerDaemons.DAEMONClearBans, period = 3600 ) )
        self._daemons.append( HydrusThreading.DAEMONWorker( self, 'DeleteOrphans', ServerDaemons.DAEMONDeleteOrphans, period = 86400 ) )
        self._daemons.append( HydrusThreading.DAEMONWorker( self, 'GenerateUpdates', ServerDaemons.DAEMONGenerateUpdates, period = 1200 ) )
        self._daemons.append( HydrusThreading.DAEMONWorker( self, 'CheckDataUsage', ServerDaemons.DAEMONCheckDataUsage, period = 86400 ) )
        self._daemons.append( HydrusThreading.DAEMONWorker( self, 'UPnP', ServerDaemons.DAEMONUPnP, ( 'notify_new_options', ), period = 43200 ) )
        
        self.CheckIfAdminPortInUse()
        
        service_keys = self.Read( 'service_keys' )
        
        for service_key in service_keys: self.ActionService( service_key, 'start' )
        
    
    def JustWokeFromSleep( self ): return False
    
    def NotifyPubSubs( self ):
        
        self.CallToThread( self.ProcessPubSub )
        
    
    def Run( self, action ):
        
        if action in ( 'stop', 'restart' ):
            
            raise HydrusExceptions.PermissionException( 'This isn\'t working yet! You will have to Ctrl+C to quit an existing server for now!' )
            
            self.ShutdownSiblingInstance()
            
        
        if action in ( 'start', 'restart' ):
            
            HydrusData.RecordRunningStart( 'server' )
            
            self.InitModel()
            
            self.InitView()
            
            while not HydrusGlobals.model_shutdown:
                
                try:
                    
                    time.sleep( 1 )
                    
                except KeyboardInterrupt:
                    
                    self.Exit()
                    
                
            
        
    