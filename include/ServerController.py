import httplib
import HydrusConstants as HC
import HydrusServer
import HydrusSessions
import HydrusThreading
import ServerConstants as SC
import ServerDB
import os
import random
import threading
import time
import traceback
import wx
import yaml
from twisted.internet import reactor
from twisted.internet import defer

class Controller( wx.App ):
    
    def _AlreadyRunning( self, port ):
        
        connection = httplib.HTTPConnection( '127.0.0.1', port, timeout = 20 )
        
        try:
            
            connection.connect()
            connection.close()
            
            return True
            
        except: return False
        
    
    def _Read( self, action, priority, *args, **kwargs ): return self._db.Read( action, priority, *args, **kwargs )
    
    def _Write( self, action, priority, *args, **kwargs ): return self._db.Write( action, priority, *args, **kwargs )
    
    def ActionService( self, service_key, action ):
        
        if action != 'stop': ( service_type, options ) = self.Read( 'service_info', service_key )
        
        def TWISTEDDoIt():
            
            def StartService( *args, **kwargs ):
                
                try:
                    
                    if 'port' not in options: return
                    
                    port = options[ 'port' ]
                    
                    connection = httplib.HTTPConnection( '127.0.0.1', port, timeout = 10 )
                    
                    try:
                        
                        connection.connect()
                        connection.close()
                        
                        raise Exception( 'Something was already bound to port ' + HC.u( port ) )
                        
                    except:
                        
                        message = options[ 'message' ]
                        
                        if service_type == HC.SERVER_ADMIN: service_object = HydrusServer.HydrusServiceAdmin( service_key, service_type, message )
                        elif service_type == HC.FILE_REPOSITORY: service_object = HydrusServer.HydrusServiceRepositoryFile( service_key, service_type, message )
                        elif service_type == HC.TAG_REPOSITORY: service_object = HydrusServer.HydrusServiceRepositoryTag( service_key, service_type, message )
                        elif service_type == HC.MESSAGE_DEPOT: return
                        
                        self._services[ service_key ] = reactor.listenTCP( port, service_object )
                        
                        connection = httplib.HTTPConnection( '127.0.0.1', port, timeout = 10 )
                        
                        try:
                            
                            connection.connect()
                            connection.close()
                            
                        except:
                            
                            raise Exception( 'Tried to bind port ' + HC.u( port ) + ' but it failed.' )
                            
                        
                    
                except Exception as e:
                    
                    print( traceback.format_exc() )
                    
                
            
            if action == 'start': StartService()
            else:
                
                deferred = defer.maybeDeferred( self._services[ service_key ].stopListening )
                
                if action == 'restart': deferred.addCallback( StartService )
                elif action == 'stop': del self._services[ service_key ]
                
            
            
        
        reactor.callFromThread( TWISTEDDoIt )
        
    
    def EventExit( self, event ): wx.CallAfter( self._tbicon.Destroy )
    
    def EventPubSub( self, event ): HC.pubsub.WXProcessQueueItem()
    
    def GetManager( self, manager_type ): return self._managers[ manager_type ]
    
    def JustWokeFromSleep( self ): return False
    
    def OnInit( self ):
        
        HC.app = self
        
        try:
            
            self.Bind( HC.EVT_PUBSUB, self.EventPubSub )
            
            self._db = ServerDB.DB()
            
            self.Bind( wx.EVT_MENU, self.EventExit, id=wx.ID_EXIT )
            
            self._managers = {}
            
            self._managers[ 'restricted_services_sessions' ] = HydrusSessions.HydrusSessionManagerServer()
            self._managers[ 'messaging_sessions' ] = HydrusSessions.HydrusMessagingSessionManagerServer()
            
            HC.pubsub.sub( self, 'ActionService', 'action_service' )
            
            self._services = {}
            
            #
            
            ( service_type, options ) = self.Read( 'service_info', HC.SERVER_ADMIN_KEY )
            
            port = options[ 'port' ]
            
            connection = httplib.HTTPConnection( '127.0.0.1', port, timeout = 10 )
            
            try:
                
                connection.connect()
                connection.close()
                
                message = 'Something was already bound to port ' + HC.u( port )
                
                wx.MessageBox( message )
                
                return False
                
            except: pass
            
            #
            
            service_keys = self.Read( 'service_keys' )
            
            for service_key in service_keys: self.ActionService( service_key, 'start' )
            
            self.StartDaemons()
            
            self._tbicon = TaskBarIcon()
            
            return True
            
        except Exception as e:
            
            print( traceback.format_exc() )
            
            return False
            
        
    
    def Read( self, action, *args, **kwargs ):
        
        return self._Read( action, HC.HIGH_PRIORITY, *args, **kwargs )
        
    
    def ReadDaemon( self, action, *args, **kwargs ):
        
        return self._Read( action, HC.LOW_PRIORITY, *args, **kwargs )
        
    
    def StartDaemons( self ):
        
        HydrusThreading.DAEMONQueue( 'FlushRequestsMade', ServerDB.DAEMONFlushRequestsMade, 'request_made', period = 60 )
        
        HydrusThreading.DAEMONWorker( 'CheckMonthlyData', ServerDB.DAEMONCheckMonthlyData, period = 3600 )
        HydrusThreading.DAEMONWorker( 'ClearBans', ServerDB.DAEMONClearBans, period = 3600 )
        HydrusThreading.DAEMONWorker( 'DeleteOrphans', ServerDB.DAEMONDeleteOrphans, period = 86400 )
        HydrusThreading.DAEMONWorker( 'GenerateUpdates', ServerDB.DAEMONGenerateUpdates, period = 1200 )
        HydrusThreading.DAEMONWorker( 'CheckDataUsage', ServerDB.DAEMONCheckDataUsage, period = 86400 )
        HydrusThreading.DAEMONWorker( 'UPnP', ServerDB.DAEMONUPnP, ( 'notify_new_options', ), period = 43200 )
        
    
    def Write( self, action, *args, **kwargs ):
        
        return self._Write( action, HC.HIGH_PRIORITY, *args, **kwargs )
        
    
    def WriteDaemon( self, action, *args, **kwargs ):
        
        return self._Write( action, HC.LOW_PRIORITY, *args, **kwargs )
        
    
class TaskBarIcon( wx.TaskBarIcon ):
    
    def __init__( self ):
        
        wx.TaskBarIcon.__init__( self )
        
        icon = wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO )
        
        self.SetIcon( icon, 'hydrus server' )
        
        self._tbmenu = wx.Menu()
        
        self._tbmenu.Append( wx.ID_EXIT, 'exit' )
        
        self.Bind( wx.EVT_TASKBAR_RIGHT_DOWN, lambda event: self.PopupMenu( self._tbmenu ) )
        
    