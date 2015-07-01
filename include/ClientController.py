import ClientCaches
import ClientData
import ClientDaemons
import hashlib
import httplib
import HydrusConstants as HC
import HydrusController
import HydrusData
import HydrusExceptions
import HydrusGlobals
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
import sqlite3
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

class Controller( HydrusController.HydrusController ):
    
    db_class = ClientDB.DB
    
    def BackupDatabase( self ):
        
        with wx.DirDialog( self._gui, 'Select backup location.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                text = 'Are you sure "' + path + '" is the correct directory?'
                text += os.linesep * 2
                text += 'Everything already in that directory will be deleted before the backup starts.'
                text += os.linesep * 2
                text += 'The database will be locked while the backup occurs, which may lock up your gui as well.'
                
                with ClientGUIDialogs.DialogYesNo( self._gui, text ) as dlg_yn:
                    
                    if dlg_yn.ShowModal() == wx.ID_YES:
                        
                        self.Write( 'backup', path )
                        
                    
                
            
        
    
    def Clipboard( self, data_type, data ):
        
        # need this cause can't do it in a non-gui thread
        
        if data_type == 'paths':
            
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
            
        elif data_type == 'text':
            
            text = data
            
            if wx.TheClipboard.Open():
                
                data = wx.TextDataObject( text )
                
                wx.TheClipboard.SetData( data )
                
                wx.TheClipboard.Close()
                
            else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        elif data_type == 'bmp':
            
            media = data
            
            image_container = wx.GetApp().Cache( 'fullscreen' ).GetImage( media )
            
            def THREADWait():
                
                # have to do this in thread, because the image rendered needs the wx event queue to render
                
                start_time = time.time()
                
                while not image_container.IsRendered():
                    
                    if HydrusData.TimeHasPassed( start_time + 15 ): raise Exception( 'The image did not render in fifteen seconds, so the attempt to copy it to the clipboard was abandoned.' )
                    
                    time.sleep( 0.1 )
                    
                
                wx.CallAfter( CopyToClipboard )
                
            
            def CopyToClipboard():
                
                if wx.TheClipboard.Open():
                    
                    hydrus_bmp = image_container.GetHydrusBitmap()
                    
                    wx_bmp = hydrus_bmp.GetWxBitmap()
                    
                    data = wx.BitmapDataObject( wx_bmp )
                    
                    wx.TheClipboard.SetData( data )
                    
                    wx.TheClipboard.Close()
                    
                else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
                
            
            HydrusThreading.CallToThread( THREADWait )
            
        
    
    def CurrentlyIdle( self ):
        
        if self._options[ 'idle_period' ] == 0: return False
        
        return HydrusData.GetNow() - self._timestamps[ 'last_user_action' ] > self._options[ 'idle_period' ]
        
    
    def DoHTTP( self, *args, **kwargs ): return self._http.Request( *args, **kwargs )
    
    def ForceIdle( self ):
        
        self._timestamps[ 'last_user_action' ] = 0
        
        HydrusGlobals.pubsub.pub( 'refresh_status' )
        
    
    def GetGUI( self ): return self._gui
    
    def GetManager( self, manager_type ): return self._managers[ manager_type ]
    
    def GetOptions( self ):
        
        return self._options
        
    
    def GetServicesManager( self ):
        
        return self._services_manager
        
    
    def InitCheckPassword( self ):
        
        while True:
            
            with wx.PasswordEntryDialog( None, 'Enter your password', 'Enter password' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    if hashlib.sha256( dlg.GetValue() ).digest() == self._options[ 'password' ]: break
                    
                else: raise HydrusExceptions.PermissionException()
                
            
        
    
    def InitDB( self ):
        
        db_initialised = False
        
        while not db_initialised:
            
            try:
                
                HydrusController.HydrusController.InitDB( self )
                
                db_initialised = True
                
            except HydrusExceptions.DBAccessException as e:
                
                try: print( HydrusData.ToString( e ) )
                except: print( repr( HydrusData.ToString( e ) ) )
                
                def wx_code():
                    
                    message = 'This instance of the client had a problem connecting to the database, which probably means an old instance is still closing.'
                    message += os.linesep * 2
                    message += 'If the old instance does not close for a _very_ long time, you can usually safely force-close it from task manager.'
                    
                    with ClientGUIDialogs.DialogYesNo( None, message, 'There was a problem connecting to the database.', yes_label = 'wait a bit, then try again', no_label = 'forget it' ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_YES: time.sleep( 3 )
                        else: raise HydrusExceptions.PermissionException()
                        
                    
                
                HydrusThreading.CallBlockingToWx( wx_code )
                
            
        
    
    def InitGUI( self ):
        
        self._managers = {}
        
        self._services_manager = ClientData.ServicesManager()
        
        self._managers[ 'hydrus_sessions' ] = HydrusSessions.HydrusSessionManagerClient()
        self._managers[ 'local_booru' ] = ClientCaches.LocalBooruCache()
        self._managers[ 'tag_censorship' ] = HydrusTags.TagCensorshipManager()
        self._managers[ 'tag_siblings' ] = HydrusTags.TagSiblingsManager()
        self._managers[ 'tag_parents' ] = HydrusTags.TagParentsManager()
        self._managers[ 'undo' ] = ClientData.UndoManager()
        self._managers[ 'web_sessions' ] = HydrusSessions.WebSessionManagerClient()
        
        self._caches[ 'fullscreen' ] = ClientCaches.RenderedImageCache( 'fullscreen' )
        self._caches[ 'preview' ] = ClientCaches.RenderedImageCache( 'preview' )
        self._caches[ 'thumbnail' ] = ClientCaches.ThumbnailCache()
        
        if HC.options[ 'proxy' ] is not None:
            
            ( proxytype, host, port, username, password ) = HC.options[ 'proxy' ]
            
            HydrusNetworking.SetProxy( proxytype, host, port, username, password )
            
        
        CC.GlobalBMPs.STATICInitialise()
        
        self._gui = ClientGUI.FrameGUI()
        
        HydrusGlobals.pubsub.sub( self, 'Clipboard', 'clipboard' )
        HydrusGlobals.pubsub.sub( self, 'RestartServer', 'restart_server' )
        HydrusGlobals.pubsub.sub( self, 'RestartBooru', 'restart_booru' )
        
        # this is because of some bug in wx C++ that doesn't add these by default
        wx.richtext.RichTextBuffer.AddHandler( wx.richtext.RichTextHTMLHandler() )
        wx.richtext.RichTextBuffer.AddHandler( wx.richtext.RichTextXMLHandler() )
        
        if HydrusGlobals.is_first_start: wx.CallAfter( self._gui.DoFirstStart )
        if HydrusGlobals.is_db_updated: wx.CallLater( 1, HydrusData.ShowText, 'The client has updated to version ' + HydrusData.ToString( HC.SOFTWARE_VERSION ) + '!' )
        
        self.RestartServer()
        self.RestartBooru()
        self.StartDaemons()
        
        self.ResetIdleTimer()
        
    
    def MaintainDB( self ):
        
        now = HydrusData.GetNow()
        
        shutdown_timestamps = self.Read( 'shutdown_timestamps' )
        
        if self._options[ 'maintenance_vacuum_period' ] != 0:
            
            if now - shutdown_timestamps[ CC.SHUTDOWN_TIMESTAMP_VACUUM ] > self._options[ 'maintenance_vacuum_period' ]: self.Write( 'vacuum' )
            
        
        if self._options[ 'maintenance_delete_orphans_period' ] != 0:
            
            if now - shutdown_timestamps[ CC.SHUTDOWN_TIMESTAMP_DELETE_ORPHANS ] > self._options[ 'maintenance_delete_orphans_period' ]: self.Write( 'delete_orphans' )
            
        
        if self._timestamps[ 'last_service_info_cache_fatten' ] != 0 and now - self._timestamps[ 'last_service_info_cache_fatten' ] > 60 * 20:
            
            HydrusGlobals.pubsub.pub( 'splash_set_text', 'fattening service info' )
            
            services = self.GetServicesManager().GetServices()
            
            for service in services:
                
                try: self.Read( 'service_info', service.GetServiceKey() )
                except: pass # sometimes this breaks when a service has just been removed and the client is closing, so ignore the error
                
            
            self._timestamps[ 'last_service_info_cache_fatten' ] = HydrusData.GetNow()
            
        
        HydrusGlobals.pubsub.pub( 'clear_closed_pages' )
        
    
    def OnInit( self ):
        
        HydrusController.HydrusController.OnInit( self )
        
        self._local_service = None
        self._booru_service = None
        
        self._http = HydrusNetworking.HTTPConnectionManager()
        
        try:
            
            splash = ClientGUI.FrameSplash()
            
        except:
            
            print( 'There was an error trying to start the splash screen!' )
            
            print( traceback.format_exc() )
            
            try: wx.CallAfter( splash.Destroy )
            except: pass
            
            return False
            
        
        boot_thread = threading.Thread( target = self.THREADBootEverything, name = 'Application Boot Thread' )
        
        wx.CallAfter( boot_thread.start )
        
        return True
        
    
    def PrepStringForDisplay( self, text ):
        
        if self._options[ 'gui_capitalisation' ]: return text
        else: return text.lower()
        
    
    def ResetIdleTimer( self ): self._timestamps[ 'last_user_action' ] = HydrusData.GetNow()
    
    def RestartBooru( self ):
        
        service = self.GetServicesManager().GetService( CC.LOCAL_BOORU_SERVICE_KEY )
        
        info = service.GetInfo()
        
        port = info[ 'port' ]
        
        def TWISTEDRestartServer():
            
            def StartServer( *args, **kwargs ):
                
                try:
                    
                    try:
                        
                        connection = HydrusNetworking.GetLocalConnection( port )
                        connection.close()
                        
                        text = 'The client\'s booru server could not start because something was already bound to port ' + HydrusData.ToString( port ) + '.'
                        text += os.linesep * 2
                        text += 'This usually means another hydrus client is already running and occupying that port. It could be a previous instantiation of this client that has yet to shut itself down.'
                        text += os.linesep * 2
                        text += 'You can change the port this client tries to host its local server on in services->manage services.'
                        
                        wx.CallLater( 1, HydrusData.ShowText, text )
                        
                    except:
                        
                        self._booru_service = reactor.listenTCP( port, HydrusServer.HydrusServiceBooru( CC.LOCAL_BOORU_SERVICE_KEY, HC.LOCAL_BOORU, 'This is the local booru.' ) )
                        
                        try:
                            
                            connection = HydrusNetworking.GetLocalConnection( port )
                            connection.close()
                            
                        except Exception as e:
                            
                            text = 'Tried to bind port ' + HydrusData.ToString( port ) + ' for the local booru, but it failed:'
                            text += os.linesep * 2
                            text += HydrusData.ToString( e )
                            
                            wx.CallLater( 1, HydrusData.ShowText, text )
                            
                        
                    
                except Exception as e:
                    
                    wx.CallAfter( HydrusData.ShowException, e )
                    
                
            
            if self._booru_service is None: StartServer()
            else:
                
                deferred = defer.maybeDeferred( self._booru_service.stopListening )
                
                deferred.addCallback( StartServer )
                
            
        
        reactor.callFromThread( TWISTEDRestartServer )
        
    
    def RestartServer( self ):
        
        port = self._options[ 'local_port' ]
        
        def TWISTEDRestartServer():
            
            def StartServer( *args, **kwargs ):
                
                try:
                    
                    try:
                        
                        connection = HydrusNetworking.GetLocalConnection( port )
                        connection.close()
                        
                        text = 'The client\'s local server could not start because something was already bound to port ' + HydrusData.ToString( port ) + '.'
                        text += os.linesep * 2
                        text += 'This usually means another hydrus client is already running and occupying that port. It could be a previous instantiation of this client that has yet to shut itself down.'
                        text += os.linesep * 2
                        text += 'You can change the port this client tries to host its local server on in file->options.'
                        
                        wx.CallLater( 1, HydrusData.ShowText, text )
                        
                    except:
                        
                        self._local_service = reactor.listenTCP( port, HydrusServer.HydrusServiceLocal( CC.LOCAL_FILE_SERVICE_KEY, HC.LOCAL_FILE, 'This is the local file service.' ) )
                        
                        try:
                            
                            connection = HydrusNetworking.GetLocalConnection( port )
                            connection.close()
                            
                        except Exception as e:
                            
                            text = 'Tried to bind port ' + HydrusData.ToString( port ) + ' for the local server, but it failed:'
                            text += os.linesep * 2
                            text += HydrusData.ToString( e )
                            
                            wx.CallLater( 1, HydrusData.ShowText, text )
                            
                        
                    
                except Exception as e:
                    
                    wx.CallAfter( HydrusData.ShowException, e )
                    
                
            
            if self._local_service is None: StartServer()
            else:
                
                deferred = defer.maybeDeferred( self._local_service.stopListening )
                
                deferred.addCallback( StartServer )
                
            
        
        reactor.callFromThread( TWISTEDRestartServer )
        
    
    def RestoreDatabase( self ):
        
        with wx.DirDialog( self._gui, 'Select backup location.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                text = 'Are you sure you want to restore a backup from "' + path + '"?'
                text += os.linesep * 2
                text += 'Everything in your current database will be deleted!'
                text += os.linesep * 2
                text += 'The gui will shut down, and then it will take a while to complete the restore. Once it is done, the client will restart.'
                
                with ClientGUIDialogs.DialogYesNo( self._gui, text ) as dlg_yn:
                    
                    if dlg_yn.ShowModal() == wx.ID_YES:
                        
                        def THREADRestart():
                            
                            wx.CallAfter( self._gui.Exit )
                            
                            while not self._db.LoopIsFinished(): time.sleep( 0.1 )
                            
                            self._db.RestoreBackup( path )
                            
                            cmd = [ sys.executable ]
                            
                            cmd.extend( sys.argv )
                            
                            subprocess.Popen( cmd )
                            
                        
                        restart_thread = threading.Thread( target = THREADRestart, name = 'Application Restart Thread' )
                        
                        wx.CallAfter( restart_thread.start )
                        
                        
                    
                
            
        
    
    def StartFileQuery( self, query_key, search_context ): HydrusThreading.CallToThread( self.THREADDoFileQuery, query_key, search_context )
    
    def StartDaemons( self ):
        
        HydrusThreading.DAEMONWorker( 'CheckImportFolders', ClientDaemons.DAEMONCheckImportFolders, ( 'notify_restart_import_folders_daemon', 'notify_new_import_folders' ), period = 180 )
        HydrusThreading.DAEMONWorker( 'CheckExportFolders', ClientDaemons.DAEMONCheckExportFolders, ( 'notify_restart_export_folders_daemon', 'notify_new_export_folders' ), period = 180 )
        HydrusThreading.DAEMONWorker( 'DownloadFiles', ClientDaemons.DAEMONDownloadFiles, ( 'notify_new_downloads', 'notify_new_permissions' ) )
        HydrusThreading.DAEMONWorker( 'ResizeThumbnails', ClientDaemons.DAEMONResizeThumbnails, period = 3600 * 24, init_wait = 600 )
        HydrusThreading.DAEMONWorker( 'SynchroniseAccounts', ClientDaemons.DAEMONSynchroniseAccounts, ( 'permissions_are_stale', ) )
        HydrusThreading.DAEMONWorker( 'SynchroniseRepositories', ClientDaemons.DAEMONSynchroniseRepositories, ( 'notify_restart_repo_sync_daemon', 'notify_new_permissions' ) )
        HydrusThreading.DAEMONWorker( 'SynchroniseSubscriptions', ClientDaemons.DAEMONSynchroniseSubscriptions, ( 'notify_restart_subs_sync_daemon', 'notify_new_subscriptions' ), period = 360, init_wait = 120 )
        HydrusThreading.DAEMONWorker( 'UPnP', ClientDaemons.DAEMONUPnP, ( 'notify_new_upnp_mappings', ), init_wait = 120, pre_callable_wait = 6 )
        
        HydrusThreading.DAEMONQueue( 'FlushRepositoryUpdates', ClientDaemons.DAEMONFlushServiceUpdates, 'service_updates_delayed', period = 5 )
        
    
    def THREADDoFileQuery( self, query_key, search_context ):
        
        query_hash_ids = self.Read( 'file_query_ids', search_context )
        
        query_hash_ids = list( query_hash_ids )
        
        random.shuffle( query_hash_ids )
        
        limit = search_context.GetSystemPredicates().GetLimit()
        
        if limit is not None: query_hash_ids = query_hash_ids[ : limit ]
        
        service_key = search_context.GetFileServiceKey()
        
        media_results = []
        
        for sub_query_hash_ids in HydrusData.SplitListIntoChunks( query_hash_ids, 256 ):
            
            if query_key.IsCancelled(): return
            
            more_media_results = self.Read( 'media_results_from_ids', service_key, sub_query_hash_ids )
            
            media_results.extend( more_media_results )
            
            HydrusGlobals.pubsub.pub( 'set_num_query_results', len( media_results ), len( query_hash_ids ) )
            
            self.WaitUntilWXThreadIdle()
            
        
        search_context.SetComplete()
        
        HydrusGlobals.pubsub.pub( 'file_query_done', query_key, media_results )
        
    
    def THREADBootEverything( self ):
        
        try:
            
            HydrusGlobals.pubsub.pub( 'splash_set_text', 'booting db' )
            
            self.InitDB() # can't run on wx thread because we need event queue free to update splash text
            
            self._options = wx.GetApp().Read( 'options' )
            
            HC.options = self._options
            
            if self._options[ 'password' ] is not None:
                
                HydrusGlobals.pubsub.pub( 'splash_set_text', 'waiting for password' )
                
                HydrusThreading.CallBlockingToWx( self.InitCheckPassword )
                
            
            HydrusGlobals.pubsub.pub( 'splash_set_text', 'booting gui' )
            
            HydrusThreading.CallBlockingToWx( self.InitGUI )
            
        except HydrusExceptions.PermissionException as e: pass
        except:
            
            traceback.print_exc()
            
            text = 'A serious error occured while trying to start the program. Its traceback will be shown next. It should have also been written to client.log.'
            
            print( text )
            
            wx.CallAfter( wx.MessageBox, text )
            wx.CallAfter( wx.MessageBox, traceback.format_exc() )
            
        finally:
            
            HydrusGlobals.pubsub.pub( 'splash_destroy' )
            
        
    
    def THREADExitEverything( self ):
        
        HydrusGlobals.pubsub.pub( 'splash_set_text', 'exiting gui' )
        
        gui = self.GetGUI()
        
        try: HydrusThreading.CallBlockingToWx( gui.TestAbleToClose )
        except: return
        
        try:
            
            HydrusThreading.CallBlockingToWx( gui.Shutdown )
            
            HydrusGlobals.pubsub.pub( 'splash_set_text', 'exiting db' )
            
            HydrusThreading.CallBlockingToWx( self.MaintainDB )
            
            self.ShutdownDB() # can't run on wx thread because we need event queue free to update splash text
            
        except HydrusExceptions.PermissionException as e: pass
        except:
            
            traceback.print_exc()
            
            text = 'A serious error occured while trying to exit the program. Its traceback will be shown next. It should have also been written to client.log. You may need to quit the program from task manager.'
            
            print( text )
            
            wx.CallAfter( wx.MessageBox, text )
            
        finally:
            
            HydrusGlobals.pubsub.pub( 'splash_destroy' )
            
        
    
    def Write( self, action, *args, **kwargs ):
        
        if action == 'content_updates': self._managers[ 'undo' ].AddCommand( 'content_updates', *args, **kwargs )
        
        return HydrusController.HydrusController.Write( self, action, *args, **kwargs )
        
    