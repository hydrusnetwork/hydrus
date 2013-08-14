import gc
import HydrusConstants as HC
import HydrusExceptions
import HydrusImageHandling
import HydrusSessions
import HydrusTags
import ClientConstants as CC
import ClientDB
import ClientGUI
import ClientGUIDialogs
import os
import sqlite3
import sys
import threading
import time
import traceback
import wx
import wx.richtext

ID_ANIMATED_EVENT_TIMER = wx.NewId()
ID_MAINTENANCE_EVENT_TIMER = wx.NewId()

class Controller( wx.App ):
    
    def _Read( self, action, *args, **kwargs ): return self._db.Read( action, HC.HIGH_PRIORITY, *args, **kwargs )
    
    def _Write( self, action, priority, synchronous, *args, **kwargs ): return self._db.Write( action, priority, synchronous, *args, **kwargs )
    
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
        
        if HC.GetNow() - self._last_idle_time > 60 * 60: # a long time, so we probably just woke up from a sleep
            
            self._last_idle_time = HC.GetNow()
            
        
        if HC.GetNow() - self._last_idle_time > 20 * 60: # 20 mins since last user-initiated db request
            
            self.MaintainDB()
            
        
    
    def EventPubSub( self, event ):
        
        pubsubs_queue = HC.pubsub.GetQueue()
        
        ( callable, args, kwargs ) = pubsubs_queue.get()
        
        try: callable( *args, **kwargs )
        except wx._core.PyDeadObjectError: pass
        except TypeError: pass
        finally: pubsubs_queue.task_done()
        
    
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
        
        sys.stdout.flush()
        sys.stderr.flush()
        
        gc.collect()
        
        now = HC.GetNow()
        
        shutdown_timestamps = self.Read( 'shutdown_timestamps' )
        
        if now - shutdown_timestamps[ CC.SHUTDOWN_TIMESTAMP_VACUUM ] > 86400 * 5: self.Write( 'vacuum' )
        # try no fatten, since we made the recent A/C changes
        #if now - shutdown_timestamps[ CC.SHUTDOWN_TIMESTAMP_FATTEN_AC_CACHE ] > 50000: self.Write( 'fatten_autocomplete_cache' )
        if now - shutdown_timestamps[ CC.SHUTDOWN_TIMESTAMP_DELETE_ORPHANS ] > 86400 * 3: self.Write( 'delete_orphans' )
        
    
    def OnInit( self ):
        
        HC.app = self
        
        try:
            
            self._splash = ClientGUI.FrameSplash()
            
            self.SetSplashText( 'log' )
            
            self._log = CC.Log()
            
            self.SetSplashText( 'db' )
            
            db_initialised = False
            
            while not db_initialised:
                
                try:
                    
                    self._db = ClientDB.DB()
                    
                    db_initialised = True
                    
                except HydrusExceptions.DBAccessException as e:
                    
                    print( HC.u( e ) )
                    
                    message = 'This instance of the client had a problem connecting to the database, which probably means an old instance is still closing.'
                    message += os.linesep + os.linesep
                    message += 'If the old instance does not close for a _very_ long time, you can usually safely force-close it from task manager.'
                    
                    with ClientGUIDialogs.DialogYesNo( None, message, yes_label = 'wait a bit, then try again', no_label = 'quit now' ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES: time.sleep( 3 )
                        else: return False
                        
                    
                
            
            self._session_manager = HydrusSessions.HydrusSessionManagerClient()
            self._web_session_manager = CC.WebSessionManagerClient()
            self._tag_parents_manager = HydrusTags.TagParentsManager()
            self._tag_siblings_manager = HydrusTags.TagSiblingsManager()
            self._undo_manager = CC.UndoManager()
            
            self.SetSplashText( 'caches' )
            
            self._fullscreen_image_cache = CC.RenderedImageCache( 'fullscreen' )
            self._preview_image_cache = CC.RenderedImageCache( 'preview' )
            
            self._thumbnail_cache = CC.ThumbnailCache()
            
            CC.GlobalBMPs.STATICInitialise()
            
            self.SetSplashText( 'gui' )
            
            self._gui = ClientGUI.FrameGUI()
            
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
            if HC.is_db_updated: wx.CallAfter( HC.pubsub.pub, 'message', HC.Message( HC.MESSAGE_TYPE_TEXT, 'The client has updated to version ' + HC.u( HC.SOFTWARE_VERSION ) + '!' ) )
            
            self._db._InitPostGUI()
            
            self._last_idle_time = 0.0
            
            self.Bind( wx.EVT_TIMER, self.EventMaintenanceTimer, id = ID_MAINTENANCE_EVENT_TIMER )
            
            self._maintenance_event_timer = wx.Timer( self, ID_MAINTENANCE_EVENT_TIMER )
            self._maintenance_event_timer.Start( 20 * 60000, wx.TIMER_CONTINUOUS )
            
        except sqlite3.OperationalError as e:
            
            message = 'Database error!' + os.linesep + os.linesep + traceback.format_exc()
            
            print message
            
            wx.MessageBox( message )
            
            return False
            
        except HydrusExceptions.PermissionException as e: pass
        except:
            
            wx.MessageBox( 'Woah, bad error:' + os.linesep + os.linesep + traceback.format_exc() )
            
            try: self._splash.Close()
            except: pass
            
            return False
            
        
        self._splash.Close()
        
        return True
        
    
    def PrepStringForDisplay( self, text ):
        
        if HC.options[ 'gui_capitalisation' ]: return text
        else: return text.lower()
        
    
    def Read( self, action, *args, **kwargs ):
        
        self._last_idle_time = HC.GetNow()
        
        return self._Read( action, *args, **kwargs )
        
    
    def ReadDaemon( self, action, *args, **kwargs ):
        
        result = self._Read( action, *args, **kwargs )
        
        time.sleep( 0.1 )
        
        return result
        
    
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
        
        self._last_idle_time = HC.GetNow()
        
        if False and action == 'content_updates': self._undo_manager.AddCommand( 'content_updates', *args, **kwargs )
        
        return self._Write( action, HC.HIGH_PRIORITY, False, *args, **kwargs )
        
    
    def WriteSynchronous( self, action, *args, **kwargs ):
        
        result = self._Write( action, HC.LOW_PRIORITY, True, *args, **kwargs )
        
        time.sleep( 0.1 )
        
        return result
        
    