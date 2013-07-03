import gc
import HydrusConstants as HC
import HydrusImageHandling
import HydrusSessions
import ClientConstants as CC
import ClientDB
import ClientGUI
import ClientGUIDialogs
import os
import sqlite3
import threading
import time
import traceback
import wx
import wx.richtext

ID_ANIMATED_EVENT_TIMER = wx.NewId()
ID_MAINTENANCE_EVENT_TIMER = wx.NewId()

class Controller( wx.App ):
    
    def _Read( self, action, *args, **kwargs ):
        
        if action == 'options': return self._options
        elif action == 'file': return self._db.ReadFile( *args, **kwargs )
        elif action == 'thumbnail': return self._db.ReadThumbnail( *args, **kwargs )
        else: return self._db.Read( action, HC.HIGH_PRIORITY, *args, **kwargs )
        
    
    def _Write( self, action, priority, *args, **kwargs ): self._db.Write( action, priority, *args, **kwargs )
    
    def ClearCaches( self ):
        
        self._thumbnail_cache.Clear()
        self._fullscreen_image_cache.Clear()
        self._preview_image_cache.Clear()
        
    
    def Clipboard( self, type, data ):
        
        # need this cause can't do it in a non-gui thread
        
        if type == 'paths':
            
            paths = data
            
            if wx.TheClipboard.Open():
                
                data = wx.DataObjectComposite()
                
                file_data = wx.FileDataObject()
                
                for path in paths: file_data.AddFile( path )
                
                text_data = wx.TextDataObject( os.linesep.join( paths ) )
                
                data.Add( file_data, True )
                data.Add( text_data, False )
                
                wx.TheClipboard.SetData( data )
                
                wx.TheClipboard.Close()
                
            else: wx.MessageBox( 'Could not get permission to access the clipboard!' )
            
        elif type == 'text':
            
            text = data
            
            if wx.TheClipboard.Open():
                
                data = wx.TextDataObject( text )
                
                wx.TheClipboard.SetData( data )
                
                wx.TheClipboard.Close()
                
            else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
    
    def DeleteSessionKey( self, service_identifier ): self._session_manager.DeleteSessionKey( service_identifier )
    
    def EventAnimatedTimer( self, event ):
        
        del gc.garbage[:]
        
        HC.pubsub.pub( 'animated_tick' )
        
    
    def EventMaintenanceTimer( self, event ):
        
        if int( time.time() ) - self._last_idle_time > 60 * 60: # a long time, so we probably just woke up from a sleep
            
            self._last_idle_time = int( time.time() )
            
        
        if int( time.time() ) - self._last_idle_time > 20 * 60: # 20 mins since last user-initiated db request
            
            self.MaintainDB()
            
        
    
    def EventPubSub( self, event ):
        
        pubsubs_queue = HC.pubsub.GetQueue()
        
        ( callable, args, kwargs ) = pubsubs_queue.get()
        
        try: callable( *args, **kwargs )
        except wx._core.PyDeadObjectError: pass
        except TypeError: pass
        except Exception as e:
            
            print( type( e ) )
            print( traceback.format_exc() )
            
        
        pubsubs_queue.task_done()
        
    
    def Exception( self, exception ): wx.MessageBox( unicode( exception ) )
    
    def GetFullscreenImageCache( self ): return self._fullscreen_image_cache
    
    def GetGUI( self ): return self._gui
    
    def GetLog( self ): return self._log
    
    def GetPreviewImageCache( self ): return self._preview_image_cache
    
    def GetSessionKey( self, service_identifier ): return self._session_manager.GetSessionKey( service_identifier )
    
    def GetTagParentsManager( self ): return self._tag_parents_manager
    
    def GetTagSiblingsManager( self ): return self._tag_siblings_manager
    
    def GetThumbnailCache( self ): return self._thumbnail_cache
    
    def GetWebCookies( self, name ): return self._web_session_manager.GetCookies( name )
    
    def MaintainDB( self ):
        
        now = int( time.time() )
        
        shutdown_timestamps = self.Read( 'shutdown_timestamps' )
        
        if now - shutdown_timestamps[ CC.SHUTDOWN_TIMESTAMP_VACUUM ] > 86400 * 5: self.Write( 'vacuum' )
        # try no fatten, since we made the recent A/C changes
        #if now - shutdown_timestamps[ CC.SHUTDOWN_TIMESTAMP_FATTEN_AC_CACHE ] > 50000: self.Write( 'fatten_autocomplete_cache' )
        if now - shutdown_timestamps[ CC.SHUTDOWN_TIMESTAMP_DELETE_ORPHANS ] > 86400 * 3: self.Write( 'delete_orphans' )
        
    
    def Message( self, message ): wx.MessageBox( message )
    
    def OnInit( self ):
        
        try:
            
            self._options = {} # this is for the db locked dialog
            
            self._splash = ClientGUI.FrameSplash()
            
            self.SetSplashText( 'log' )
            
            self._log = CC.Log()
            
            self.SetSplashText( 'db' )
            
            db_initialised = False
            
            while not db_initialised:
                
                try:
                    
                    self._db = ClientDB.DB()
                    
                    db_initialised = True
                    
                except HC.DBAccessException as e:
                    
                    print( unicode( e ) )
                    
                    message = 'This instance of the client had a problem connecting to the database, which probably means an old instance is still closing.'
                    message += os.linesep + os.linesep
                    message += 'If the old instance does not close for a _very_ long time, you can usually safely force-close it from task manager.'
                    
                    with ClientGUIDialogs.DialogYesNo( None, message, yes_label = 'wait a bit, then try again', no_label = 'quit now' ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES: time.sleep( 3 )
                        else: return False
                        
                    
                
            
            self._options = self._db.Read( 'options', HC.HIGH_PRIORITY )
            
            self._session_manager = HydrusSessions.HydrusSessionManagerClient()
            self._web_session_manager = CC.WebSessionManagerClient()
            self._tag_parents_manager = CC.TagParentsManager()
            self._tag_siblings_manager = CC.TagSiblingsManager()
            
            self.SetSplashText( 'caches' )
            
            self._fullscreen_image_cache = CC.RenderedImageCache( self._db, self._options, 'fullscreen' )
            self._preview_image_cache = CC.RenderedImageCache( self._db, self._options, 'preview' )
            
            self._thumbnail_cache = CC.ThumbnailCache( self._db, self._options )
            
            CC.GlobalBMPs.STATICInitialise()
            
            self.SetSplashText( 'gui' )
            
            self._gui = ClientGUI.FrameGUI()
            
            HC.pubsub.sub( self, 'Exception', 'exception' )
            HC.pubsub.sub( self, 'Message', 'message' )
            HC.pubsub.sub( self, 'Clipboard', 'clipboard' )
            
            self.Bind( HC.EVT_PUBSUB, self.EventPubSub )
            
            # this is because of some bug in wx C++ that doesn't add these by default
            wx.richtext.RichTextBuffer.AddHandler( wx.richtext.RichTextHTMLHandler() )
            wx.richtext.RichTextBuffer.AddHandler( wx.richtext.RichTextXMLHandler() )
            
            self.Bind( wx.EVT_TIMER, self.EventAnimatedTimer, id = ID_ANIMATED_EVENT_TIMER )
            
            self._animated_event_timer = wx.Timer( self, ID_ANIMATED_EVENT_TIMER )
            self._animated_event_timer.Start( 1000, wx.TIMER_CONTINUOUS )
            
            self.SetSplashText( 'starting daemons' )
            
            if HC.is_first_start: self._gui.DoFirstStart()
            
            self._db._InitPostGUI()
            
            self._last_idle_time = 0.0
            
            self.Bind( wx.EVT_TIMER, self.EventMaintenanceTimer, id = ID_MAINTENANCE_EVENT_TIMER )
            
            self._maintenance_event_timer = wx.Timer( self, ID_MAINTENANCE_EVENT_TIMER )
            self._maintenance_event_timer.Start( 20 * 60000, wx.TIMER_CONTINUOUS )
            
        except sqlite3.OperationalError as e:
            print( traceback.format_exc() )
            message = 'Database error!'
            message += os.linesep + os.linesep
            message += unicode( e )
            
            print message
            
            wx.MessageBox( message )
            
            return False
            
        except HC.PermissionException as e: pass
        except:
            
            wx.MessageBox( 'Woah, bad error:' + os.linesep + os.linesep + traceback.format_exc() )
            
            try: self._splash.Close()
            except: pass
            
            return False
            
        
        self._splash.Close()
        
        return True
        
    
    def PrepStringForDisplay( self, text ):
        
        if self._options[ 'gui_capitalisation' ]: return text
        else: return text.lower()
        
    
    def ProcessServerRequest( self, *args, **kwargs ): return self._db.ProcessRequest( *args, **kwargs )
    
    def Read( self, action, *args, **kwargs ):
        
        self._last_idle_time = int( time.time() )
        
        return self._Read( action, *args, **kwargs )
        
    
    def ReadDaemon( self, action, *args, **kwargs ): return self._Read( action, *args, **kwargs )
    
    def SetSplashText( self, text ):
        
        self._splash.SetText( text )
        self.Yield() # this processes the event queue immediately, so the paint event can occur
        
    
    def WaitUntilGoodTimeToUseGUIThread( self ):
        
        pubsubs_queue = HC.pubsub.GetQueue()
        
        while True:
            
            if HC.shutdown: raise Exception( 'Client shutting down!' )
            elif pubsubs_queue.qsize() == 0: return
            else: time.sleep( 0.0001 )
            
        
    
    def Write( self, action, *args, **kwargs ):
        
        self._last_idle_time = int( time.time() )
        
        self._Write( action, HC.HIGH_PRIORITY, *args, **kwargs )
        
    
    def WriteDaemon( self, action, *args, **kwargs ): self._Write( action, HC.LOW_PRIORITY, *args, **kwargs )
    
    def WriteLowPriority( self, action, *args, **kwargs ): self._Write( action, HC.LOW_PRIORITY, *args, **kwargs )
    