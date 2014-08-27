import collections
import gc
import hashlib
import httplib
import HydrusConstants as HC
import HydrusExceptions
import HydrusNetworking
import HydrusSessions
import HydrusServer
import HydrusTags
import HydrusThreading
import ClientConstants as CC
import ClientDB
import ClientGUI
import ClientGUIDialogs
import os
import random
import shutil
import sqlite3
import stat
import subprocess
import sys
import threading
import time
import traceback
import wx
import wx.richtext
from twisted.internet import reactor
from twisted.internet import defer

ID_ANIMATED_EVENT_TIMER = wx.NewId()
ID_MAINTENANCE_EVENT_TIMER = wx.NewId()

MAINTENANCE_PERIOD = 5 * 60

class Controller( wx.App ):
    
    def _Read( self, action, *args, **kwargs ): return self._db.Read( action, HC.HIGH_PRIORITY, *args, **kwargs )
    
    def _Write( self, action, priority, synchronous, *args, **kwargs ): return self._db.Write( action, priority, synchronous, *args, **kwargs )
    
    def BackupDatabase( self ):
        
        with wx.DirDialog( self._gui, 'Select backup location.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                message = '''Are you sure "''' + path + '''" is the correct directory?
Everything already in that directory will be deleted before the backup starts.
The database will be locked while the backup occurs, which may lock up your gui as well.'''
                
                with ClientGUIDialogs.DialogYesNo( self._gui, message ) as dlg_yn:
                    
                    if dlg_yn.ShowModal() == wx.ID_YES:
                        
                        self.Write( 'backup', path )
                        
                    
                
            
        
    
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
            
        
    
    def CurrentlyIdle( self ): return HC.GetNow() - self._timestamps[ 'last_user_action' ] > 30 * 60 # 30 mins since last canvas media swap
    
    def EventPubSub( self, event ):
        
        HC.currently_doing_pubsub = True
        
        try: HC.pubsub.WXProcessQueueItem()
        finally: HC.currently_doing_pubsub = False
        
    
    def GetDB( self ): return self._db
    
    def GetFullscreenImageCache( self ): return self._fullscreen_image_cache
    
    def GetGUI( self ): return self._gui
    
    def GetLog( self ): return self._log
    
    def GetManager( self, type ): return self._managers[ type ]
    
    def GetPreviewImageCache( self ): return self._preview_image_cache
    
    def GetThumbnailCache( self ): return self._thumbnail_cache
    
    def InitCheckPassword( self ):
        
        while True:
            
            with wx.PasswordEntryDialog( None, 'Enter your password', 'Enter password' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    if hashlib.sha256( dlg.GetValue() ).digest() == HC.options[ 'password' ]: break
                    
                else: raise HydrusExceptions.PermissionException()
                
            
        
    
    def InitDB( self ):
        
        self._log = CC.Log()
        
        try:
            
            def make_temp_files_deletable( function_called, path, traceback_gumpf ):
                
                os.chmod( path, stat.S_IWRITE )
                
                function_called( path ) # try again
                
            
            if os.path.exists( HC.TEMP_DIR ): shutil.rmtree( HC.TEMP_DIR, onerror = make_temp_files_deletable )
            
        except: pass
        
        try:
            
            if not os.path.exists( HC.TEMP_DIR ): os.mkdir( HC.TEMP_DIR )
            
        except: pass
        
        db_initialised = False
        
        while not db_initialised:
            
            try:
                
                self._db = ClientDB.DB()
                
                db_initialised = True
                
            except HydrusExceptions.DBAccessException as e:
                
                try: print( HC.u( e ) )
                except: print( repr( HC.u( e ) ) )
                
                message = 'This instance of the client had a problem connecting to the database, which probably means an old instance is still closing.'
                message += os.linesep + os.linesep
                message += 'If the old instance does not close for a _very_ long time, you can usually safely force-close it from task manager.'
                
                with ClientGUIDialogs.DialogYesNo( None, message, yes_label = 'wait a bit, then try again', no_label = 'forget it' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES: time.sleep( 3 )
                    else: raise HydrusExceptions.PermissionException()
                    
                
            
        
        threading.Thread( target = self._db.MainLoop, name = 'Database Main Loop' ).start()
        
    
    def InitGUI( self ):
        
        self._managers = {}
        
        self._managers[ 'services' ] = CC.ServicesManager()
        
        self._managers[ 'hydrus_sessions' ] = HydrusSessions.HydrusSessionManagerClient()
        self._managers[ 'local_booru' ] = CC.LocalBooruCache()
        self._managers[ 'tag_censorship' ] = HydrusTags.TagCensorshipManager()
        self._managers[ 'tag_siblings' ] = HydrusTags.TagSiblingsManager()
        self._managers[ 'tag_parents' ] = HydrusTags.TagParentsManager()
        self._managers[ 'undo' ] = CC.UndoManager()
        self._managers[ 'web_sessions' ] = HydrusSessions.WebSessionManagerClient()
        
        self._fullscreen_image_cache = CC.RenderedImageCache( 'fullscreen' )
        self._preview_image_cache = CC.RenderedImageCache( 'preview' )
        
        self._thumbnail_cache = CC.ThumbnailCache()
        
        CC.GlobalBMPs.STATICInitialise()
        
        self._gui = ClientGUI.FrameGUI()
        
        HC.pubsub.sub( self, 'Clipboard', 'clipboard' )
        HC.pubsub.sub( self, 'RestartServer', 'restart_server' )
        HC.pubsub.sub( self, 'RestartBooru', 'restart_booru' )
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventMaintenance, id = ID_MAINTENANCE_EVENT_TIMER )
        
        self._maintenance_event_timer = wx.Timer( self, ID_MAINTENANCE_EVENT_TIMER )
        self._maintenance_event_timer.Start( MAINTENANCE_PERIOD * 1000, wx.TIMER_CONTINUOUS )
        
        # this is because of some bug in wx C++ that doesn't add these by default
        wx.richtext.RichTextBuffer.AddHandler( wx.richtext.RichTextHTMLHandler() )
        wx.richtext.RichTextBuffer.AddHandler( wx.richtext.RichTextXMLHandler() )
        
        if HC.is_first_start: wx.CallAfter( self._gui.DoFirstStart )
        if HC.is_db_updated: wx.CallLater( 1, HC.ShowText, 'The client has updated to version ' + HC.u( HC.SOFTWARE_VERSION ) + '!' )
        
        self.RestartServer()
        self.RestartBooru()
        self._db.StartDaemons()
        
    
    def MaintainDB( self ):
        
        sys.stdout.flush()
        sys.stderr.flush()
        
        gc.collect()
        
        now = HC.GetNow()
        
        shutdown_timestamps = self.Read( 'shutdown_timestamps' )
        
        if now - shutdown_timestamps[ CC.SHUTDOWN_TIMESTAMP_VACUUM ] > 86400 * 5: self.Write( 'vacuum' )
        if now - shutdown_timestamps[ CC.SHUTDOWN_TIMESTAMP_DELETE_ORPHANS ] > 86400 * 3: self.Write( 'delete_orphans' )
        
        if now - self._timestamps[ 'last_service_info_cache_fatten' ] > 60 * 20:
            
            HC.pubsub.pub( 'set_splash_text', 'fattening service info' )
            
            services = self.GetManager( 'services' ).GetServices()
            
            for service in services: self.Read( 'service_info', service.GetKey() )
            
            self._timestamps[ 'service_info_cache_fatten' ] = HC.GetNow()
            
        
        HC.pubsub.pub( 'clear_closed_pages' )
        
    
    def OnInit( self ):
        
        HC.app = self
        HC.http = HydrusNetworking.HTTPConnectionManager()
        
        self._timestamps = collections.defaultdict( lambda: 0 )
        
        self._timestamps[ 'boot' ] = HC.GetNow()
        
        self._local_service = None
        self._booru_service = None
        
        self.Bind( HC.EVT_PUBSUB, self.EventPubSub )
        
        try:
            
            splash = ClientGUI.FrameSplash( 'boot' )
            
            return True
            
        except:
            
            print( 'There was an error trying to start the splash screen!' )
            
            print( traceback.format_exc() )
            
            try: wx.CallAfter( splash.Destroy )
            except: pass
            
            return False
            
        
    
    def PrepStringForDisplay( self, text ):
        
        if HC.options[ 'gui_capitalisation' ]: return text
        else: return text.lower()
        
    
    def Read( self, action, *args, **kwargs ): return self._Read( action, *args, **kwargs )
    
    def ReadDaemon( self, action, *args, **kwargs ):
        
        result = self._Read( action, *args, **kwargs )
        
        time.sleep( 0.1 )
        
        return result
        
    
    def ResetIdleTimer( self ): self._timestamps[ 'last_user_action' ] = HC.GetNow()
    
    def RestartBooru( self ):
        
        service = self.GetManager( 'services' ).GetService( HC.LOCAL_BOORU_SERVICE_KEY )
        
        info = service.GetInfo()
        
        port = info[ 'port' ]
        
        def TWISTEDRestartServer():
            
            def StartServer( *args, **kwargs ):
                
                try:
                    
                    connection = httplib.HTTPConnection( '127.0.0.1', port, timeout = 10 )
                    
                    try:
                        
                        connection.connect()
                        connection.close()
                        
                        text = 'The client\'s booru server could not start because something was already bound to port ' + HC.u( port ) + '.'
                        text += os.linesep * 2
                        text += 'This usually means another hydrus client is already running and occupying that port. It could be a previous instantiation of this client that has yet to shut itself down.'
                        text += os.linesep * 2
                        text += 'You can change the port this client tries to host its local server on in services->manage services.'
                        
                        wx.CallLater( 1, HC.ShowText, text )
                        
                    except:
                        
                        self._booru_service = reactor.listenTCP( port, HydrusServer.HydrusServiceBooru( HC.LOCAL_BOORU_SERVICE_KEY, HC.LOCAL_BOORU, 'This is the local booru.' ) )
                        
                        connection = httplib.HTTPConnection( '127.0.0.1', port, timeout = 10 )
                        
                        try:
                            
                            connection.connect()
                            connection.close()
                            
                        except:
                            
                            text = 'Tried to bind port ' + HC.u( port ) + ' for the local booru, but it failed.'
                            
                            wx.CallLater( 1, HC.ShowText, text )
                            
                        
                    
                except Exception as e:
                    
                    wx.CallAfter( HC.ShowException, e )
                    
                
            
            if self._booru_service is None: StartServer()
            else:
                
                deferred = defer.maybeDeferred( self._booru_service.stopListening )
                
                deferred.addCallback( StartServer )
                
            
        
        reactor.callFromThread( TWISTEDRestartServer )
        
    
    def RestartServer( self ):
        
        port = HC.options[ 'local_port' ]
        
        def TWISTEDRestartServer():
            
            def StartServer( *args, **kwargs ):
                
                try:
                    
                    connection = httplib.HTTPConnection( '127.0.0.1', port, timeout = 10 )
                    
                    try:
                        
                        connection.connect()
                        connection.close()
                        
                        text = 'The client\'s local server could not start because something was already bound to port ' + HC.u( port ) + '.'
                        text += os.linesep * 2
                        text += 'This usually means another hydrus client is already running and occupying that port. It could be a previous instantiation of this client that has yet to shut itself down.'
                        text += os.linesep * 2
                        text += 'You can change the port this client tries to host its local server on in file->options.'
                        
                        wx.CallLater( 1, HC.ShowText, text )
                        
                    except:
                        
                        self._local_service = reactor.listenTCP( port, HydrusServer.HydrusServiceLocal( HC.LOCAL_FILE_SERVICE_KEY, HC.LOCAL_FILE, 'This is the local file service.' ) )
                        
                        connection = httplib.HTTPConnection( '127.0.0.1', port, timeout = 10 )
                        
                        try:
                            
                            connection.connect()
                            connection.close()
                            
                        except:
                            
                            text = 'Tried to bind port ' + HC.u( port ) + ' for the local server, but it failed.'
                            
                            wx.CallLater( 1, HC.ShowText, text )
                            
                        
                    
                except Exception as e:
                    
                    wx.CallAfter( HC.ShowException, e )
                    
                
            
            if self._local_service is None: StartServer()
            else:
                
                deferred = defer.maybeDeferred( self._local_service.stopListening )
                
                deferred.addCallback( StartServer )
                
            
        
        reactor.callFromThread( TWISTEDRestartServer )
        
    
    def RestoreDatabase( self ):
        
        with wx.DirDialog( self._gui, 'Select backup location.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                message = '''Are you sure you want to restore a backup from "''' + path + '''"?
Everything in your current database will be deleted!
The gui will shut down, and then it will take a while to complete the restore.
Once it is done, the client will restart.'''
                
                with ClientGUIDialogs.DialogYesNo( self._gui, message ) as dlg_yn:
                    
                    if dlg_yn.ShowModal() == wx.ID_YES:
                        
                        self._gui.Hide()
                        
                        self._gui.Close()
                        
                        self._db.Shutdown()
                        
                        while not self._db.LoopIsFinished(): time.sleep( 0.1 )
                        
                        self._db.RestoreBackup( path )
                        
                        call_stuff = [ sys.executable ]
                        
                        call_stuff.extend( sys.argv )
                        
                        subprocess.call( call_stuff, shell = True )
                        
                    
                
            
        
    
    def StartFileQuery( self, query_key, search_context ): HydrusThreading.CallToThread( self.THREADDoFileQuery, query_key, search_context )
    
    def THREADDoFileQuery( self, query_key, search_context ):
        
        try:
            
            query_hash_ids = self.Read( 'file_query_ids', search_context )
            
            query_hash_ids = list( query_hash_ids )
            
            random.shuffle( query_hash_ids )
            
            limit = search_context.GetSystemPredicates().GetLimit()
            
            if limit is not None: query_hash_ids = query_hash_ids[ : limit ]
            
            service_key = search_context.GetFileServiceKey()
            
            include_current_tags = search_context.IncludeCurrentTags()
            
            media_results = []
            
            include_pending_tags = search_context.IncludePendingTags()
            
            i = 0
            
            base = 256
            
            while i < len( query_hash_ids ):
                
                if query_key.IsCancelled(): return
                
                if i == 0: ( last_i, i ) = ( 0, base )
                else: ( last_i, i ) = ( i, i + base )
                
                sub_query_hash_ids = query_hash_ids[ last_i : i ]
                
                more_media_results = self.Read( 'media_results_from_ids', service_key, sub_query_hash_ids )
                
                media_results.extend( more_media_results )
                
                HC.pubsub.pub( 'set_num_query_results', len( media_results ), len( query_hash_ids ) )
                
                self.WaitUntilGoodTimeToUseGUIThread()
                
            
            HC.pubsub.pub( 'file_query_done', query_key, media_results )
            
        except Exception as e: HC.ShowException( e )
        
    
    def TIMEREventMaintenance( self, event ):
        
        last_time_this_ran = self._timestamps[ 'last_check_idle_time' ]
        
        self._timestamps[ 'last_check_idle_time' ] = HC.GetNow()
        
        # this tests if we probably just woke up from a sleep
        if HC.GetNow() - last_time_this_ran > MAINTENANCE_PERIOD + ( 5 * 60 ): return
        
        if self.CurrentlyIdle(): self.MaintainDB()
        
    
    def WaitUntilGoodTimeToUseGUIThread( self ):
        
        while True:
            
            if HC.shutdown: raise Exception( 'Client shutting down!' )
            elif HC.pubsub.NoJobsQueued() and not HC.currently_doing_pubsub: return
            else: time.sleep( 0.0001 )
            
        
    
    def Write( self, action, *args, **kwargs ):
        
        if action == 'content_updates': self._managers[ 'undo' ].AddCommand( 'content_updates', *args, **kwargs )
        
        return self._Write( action, HC.HIGH_PRIORITY, False, *args, **kwargs )
        
    
    def WriteSynchronous( self, action, *args, **kwargs ):
        
        result = self._Write( action, HC.LOW_PRIORITY, True, *args, **kwargs )
        
        time.sleep( 0.1 )
        
        return result
        
    