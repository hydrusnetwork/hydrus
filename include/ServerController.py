import httplib
import HydrusConstants as HC
import HydrusController
import HydrusData
import HydrusGlobals
import HydrusNetworking
import HydrusServer
import HydrusSessions
import HydrusThreading
import ServerDaemons
import ServerDB
import os
import traceback
import wx
from twisted.internet import reactor
from twisted.internet import defer

ID_MAINTENANCE_EVENT_TIMER = wx.NewId()

MAINTENANCE_PERIOD = 5 * 60

class Controller( HydrusController.HydrusController ):
    
    db_class = ServerDB.DB
    
    def _AlreadyRunning( self, port ):
        
        try:
            
            connection = HydrusNetworking.GetLocalConnection( port )
            connection.close()
            
            return True
            
        except: return False
        
    
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
        
    
    def EventExit( self, event ):
        
        wx.CallAfter( self._tbicon.Destroy )
        
        self.ShutdownDB()
        
    
    def GetManager( self, manager_type ): return self._managers[ manager_type ]
    
    def JustWokeFromSleep( self ): return False
    
    def MaintainDB( self ):
        
        pass
        
    
    def OnInit( self ):
        
        try:
            
            HydrusController.HydrusController.OnInit( self )
            
            if HydrusData.IsAlreadyRunning():
                
                raise Exception( 'It looks like this server is already running!' )
                
            
            self.InitDB()
            
            self.Bind( wx.EVT_MENU, self.EventExit, id=wx.ID_EXIT )
            
            self._managers[ 'restricted_services_sessions' ] = HydrusSessions.HydrusSessionManagerServer()
            self._managers[ 'messaging_sessions' ] = HydrusSessions.HydrusMessagingSessionManagerServer()
            
            HydrusGlobals.pubsub.sub( self, 'ActionService', 'action_service' )
            
            self._services = {}
            
            #
            
            ( service_type, options ) = self.Read( 'service_info', HC.SERVER_ADMIN_KEY )
            
            port = options[ 'port' ]
            
            try:
                
                connection = HydrusNetworking.GetLocalConnection( port )
                connection.close()
                
                message = 'Something was already bound to port ' + HydrusData.ToString( port )
                
                wx.MessageBox( message )
                
                return False
                
            except: pass
            
            #
            
            service_keys = self.Read( 'service_keys' )
            
            for service_key in service_keys: self.ActionService( service_key, 'start' )
            
            self.StartDaemons()
            
            if HC.PLATFORM_WINDOWS: self._tbicon = TaskBarIcon()
            else:
                
                stay_open_frame = wx.Frame( None, title = 'Hydrus Server' )
                
                stay_open_frame.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                stay_open_frame.SetIcon( wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO ) )
                
                wx.StaticText( stay_open_frame, label = 'The hydrus server is now running.' + os.linesep * 2 + 'Close this window to stop it.' )
                
                ( x, y ) = stay_open_frame.GetEffectiveMinSize()
                
                stay_open_frame.SetInitialSize( ( x, y ) )
                
                stay_open_frame.Show()
                
            
            return True
            
        except Exception as e:
            
            print( traceback.format_exc() )
            
            return False
            
        
    
    def StartDaemons( self ):
        
        HydrusThreading.DAEMONQueue( 'FlushRequestsMade', ServerDaemons.DAEMONFlushRequestsMade, 'request_made', period = 60 )
        
        HydrusThreading.DAEMONWorker( 'CheckMonthlyData', ServerDaemons.DAEMONCheckMonthlyData, period = 3600 )
        HydrusThreading.DAEMONWorker( 'ClearBans', ServerDaemons.DAEMONClearBans, period = 3600 )
        HydrusThreading.DAEMONWorker( 'DeleteOrphans', ServerDaemons.DAEMONDeleteOrphans, period = 86400 )
        HydrusThreading.DAEMONWorker( 'GenerateUpdates', ServerDaemons.DAEMONGenerateUpdates, period = 1200 )
        HydrusThreading.DAEMONWorker( 'CheckDataUsage', ServerDaemons.DAEMONCheckDataUsage, period = 86400 )
        HydrusThreading.DAEMONWorker( 'UPnP', ServerDaemons.DAEMONUPnP, ( 'notify_new_options', ), period = 43200 )
        
    
class TaskBarIcon( wx.TaskBarIcon ):
    
    def __init__( self ):
        
        wx.TaskBarIcon.__init__( self )
        
        icon = wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO )
        
        self.SetIcon( icon, 'hydrus server' )
        
        self._tbmenu = wx.Menu()
        
        self._tbmenu.Append( wx.ID_EXIT, 'exit' )
        
        self.Bind( wx.EVT_TASKBAR_RIGHT_DOWN, lambda event: self.PopupMenu( self._tbmenu ) )
        
    