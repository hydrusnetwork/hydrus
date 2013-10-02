import httplib
import HydrusConstants as HC
import HydrusServer
import HydrusSessions
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

class Controller( wx.App ):
    
    def _AlreadyRunning( self, port ):
        
        connection = httplib.HTTPConnection( '127.0.0.1', port, timeout = 20 )
        
        try:
            
            connection.connect()
            connection.close()
            
            return True
            
        except: return False
        
    
    def _Read( self, action, *args, **kwargs ): return self._db.Read( action, HC.HIGH_PRIORITY, *args, **kwargs )
    
    def _Write( self, action, priority, *args, **kwargs ): return self._db.Write( action, priority, *args, **kwargs )
    
    def AddSession( self, service_identifier, account ): return self._session_manager.AddSession( service_identifier, account )
    
    def GetAccount( self, session_key, service_identifier ): return self._session_manager.GetAccount( session_key, service_identifier )
    
    def EventExit( self, event ): self._tbicon.Destroy()
    
    def EventPubSub( self, event ):
        
        pubsubs_queue = HC.pubsub.GetQueue()
        
        ( callable, args, kwargs ) = pubsubs_queue.get()
        
        try: callable( *args, **kwargs )
        except TypeError: pass
        except Exception as e: HC.ShowException( e )
        
        pubsubs_queue.task_done()
        
    
    def OnInit( self ):
        
        HC.app = self
        
        try:
            
            self._db = ServerDB.DB()
            
            self.Bind( wx.EVT_MENU, self.EventExit, id=wx.ID_EXIT )
            
            self.Bind( HC.EVT_PUBSUB, self.EventPubSub )
            
            self._tbicon = TaskBarIcon()
            
            self._session_manager = HydrusSessions.HydrusSessionManagerServer()
            
            HC.pubsub.sub( self, 'RestartService', 'restart_service' )
            
            self._services = {}
            
            services_info = self.Read( 'services' )
            
            for ( service_identifier, options ) in services_info: self.RestartService( service_identifier, options )
            
            return True
            
        except Exception as e:
            
            print( traceback.format_exc() )
            
            return False
            
        
    
    def Read( self, action, *args, **kwargs ):
        
        return self._Read( action, *args, **kwargs )
        
    
    def RestartService( self, service_identifier, options ):
        
        def TWISTEDRestartService():
            
            def StartService():
                
                try:
                    
                    port = options[ 'port' ]
                    
                    connection = httplib.HTTPConnection( '127.0.0.1', port, timeout = 10 )
                    
                    try:
                        
                        connection.connect()
                        connection.close()
                        
                        raise Exception( 'Something was already bound to port ' + HC.u( port ) )
                        
                    except:
                        
                        message = options[ 'message' ]
                        
                        service_type = service_identifier.GetType()
                        
                        if service_type == HC.SERVER_ADMIN: service_object = HydrusServer.HydrusServiceAdmin( service_identifier, message )
                        elif service_type == HC.FILE_REPOSITORY: service_object = HydrusServer.HydrusServiceRepositoryFile( service_identifier, message )
                        elif service_type == HC.TAG_REPOSITORY: service_object = HydrusServer.HydrusServiceRepositoryTag( service_identifier, message )
                        elif service_type == HC.MESSAGE_DEPOT: return
                        
                        self._services[ service_identifier ] = reactor.listenTCP( port, service_object )
                        
                        connection = httplib.HTTPConnection( '127.0.0.1', port, timeout = 10 )
                        
                        try:
                            
                            connection.connect()
                            connection.close()
                            
                        except:
                            
                            raise Exception( 'Tried to bind port ' + HC.u( port ) + ' but it failed.' )
                            
                        
                    
                except Exception as e:
                    
                    print( traceback.format_exc() )
                    
            
            if service_identifier not in self._services: StartService()
            else:
                
                deferred = self._services[ service_identifier ].stopListening()
                
                deferred.AddCallback( StartService )
                
            
        
        reactor.callFromThread( TWISTEDRestartService )
        
    
    def Write( self, action, *args, **kwargs ):
        
        return self._Write( action, HC.HIGH_PRIORITY, *args, **kwargs )
        
    
class TaskBarIcon( wx.TaskBarIcon ):
    
    def __init__( self ):
        
        wx.TaskBarIcon.__init__( self )
        
        icon = wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO )
        
        self.SetIcon( icon, 'hydrus server' )
        
        self._tbmenu = wx.Menu()
        
        self._tbmenu.Append( wx.ID_EXIT, 'exit' )
        
        self.Bind( wx.EVT_TASKBAR_RIGHT_DOWN, lambda event: self.PopupMenu( self._tbmenu ) )
        
    