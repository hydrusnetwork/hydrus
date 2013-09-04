import httplib
import HydrusConstants as HC
import HydrusSessions
import ServerDB
import os
import random
import threading
import time
import traceback
import wx
import yaml

class Controller( wx.App ):
    
    def _AlreadyRunning( self, port ):
        
        connection = httplib.HTTPConnection( 'localhost:' + HC.u( port ) )
        
        try:
            
            connection.connect()
            connection.close()
            
            return True
            
        except: return False
        
    
    def AddSession( self, session_key, service_identifier, account_identifier, expiry ): self._session_manager.AddSession( session_key, service_identifier, account_identifier, expiry )
    
    def ChangePort( self, port ):
        
        new_server = self._server_callable( port )
        
        server_daemon = threading.Thread( target=new_server.serve_forever )
        server_daemon.setDaemon( True )
        server_daemon.start()
        
        connection = httplib.HTTPConnection( 'localhost:' + HC.u( port ) )
        
        connection.connect()
        
        connection.request( 'GET', '/' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        if response.status != 200: raise Exception( yaml.safe_load( data ) )
        
        connection.close()
        
        self._server.shutdown()
        
        self._server = new_server
        
    
    def GetAccountIdentifier( self, session_key, service_identifier ): return self._session_manager.GetAccountIdentifier( session_key, service_identifier )
    
    def EventExit( self, event ): self._tbicon.Destroy()
    
    def EventPubSub( self, event ):
        
        pubsubs_queue = HC.pubsub.GetQueue()
        
        ( callable, args, kwargs ) = pubsubs_queue.get()
        
        try: callable( *args, **kwargs )
        except TypeError: pass
        except Exception as e: HC.ShowException( e )
        
        pubsubs_queue.task_done()
        
    
    def GetDB( self ): return self._db
    
    def OnInit( self ):
        
        HC.app = self
        
        try: self._db = ServerDB.DB()
        except Exception as e:
            
            HC.ShowException( e )
            
            return False
            
        
        self._session_manager = HydrusSessions.HydrusSessionManagerServer()
        
        self.Bind( wx.EVT_MENU, self.EventExit, id=wx.ID_EXIT )
        
        self.Bind( HC.EVT_PUBSUB, self.EventPubSub )
        
        self._tbicon = TaskBarIcon()
        
        return True
        
    
class TaskBarIcon( wx.TaskBarIcon ):
    
    def __init__( self ):
        
        wx.TaskBarIcon.__init__( self )
        
        icon = wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO )
        
        self.SetIcon( icon, 'hydrus server' )
        
        self._tbmenu = wx.Menu()
        
        self._tbmenu.Append( wx.ID_EXIT, 'exit' )
        
        self.Bind( wx.EVT_TASKBAR_RIGHT_DOWN, lambda event: self.PopupMenu( self._tbmenu ) )
        
    