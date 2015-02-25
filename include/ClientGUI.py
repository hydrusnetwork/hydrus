import httplib
import HydrusConstants as HC
import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIDialogsManage
import ClientGUIPages
import HydrusDownloading
import HydrusExceptions
import HydrusFileHandling
import HydrusImageHandling
import HydrusNATPunch
import HydrusThreading
import itertools
import os
import random
import sqlite3
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
import wx
import yaml

# timers

ID_TIMER_UPDATES = wx.NewId()

# Sizer Flags

FLAGS_NONE = wx.SizerFlags( 0 )

FLAGS_SMALL_INDENT = wx.SizerFlags( 0 ).Border( wx.ALL, 2 )

FLAGS_EXPAND_PERPENDICULAR = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_BOTH_WAYS = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_DEPTH_ONLY = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_EXPAND_SIZER_PERPENDICULAR = wx.SizerFlags( 0 ).Expand()
FLAGS_EXPAND_SIZER_BOTH_WAYS = wx.SizerFlags( 2 ).Expand()
FLAGS_EXPAND_SIZER_DEPTH_ONLY = wx.SizerFlags( 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_BUTTON_SIZER = wx.SizerFlags( 0 ).Align( wx.ALIGN_RIGHT )
FLAGS_LONE_BUTTON = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_RIGHT )

FLAGS_MIXED = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

#

MENU_ORDER = [ 'file', 'undo', 'view', 'download', 'database', 'pending', 'services', 'admin', 'help' ]

class FrameGUI( ClientGUICommon.FrameThatResizes ):
    
    def __init__( self ):
        
        ClientGUICommon.FrameThatResizes.__init__( self, None, resize_option_prefix = 'gui_', title = HC.app.PrepStringForDisplay( 'Hydrus Client' ) )
        
        self.SetDropTarget( ClientGUICommon.FileDropTarget( self.ImportFiles ) )
        
        self._statusbar = self.CreateStatusBar()
        self._statusbar.SetFieldsCount( 4 )
        self._statusbar.SetStatusWidths( [ -1, 100, 120, 50 ] )
        
        self._statusbar_media = ''
        self._statusbar_inbox = ''
        self._statusbar_downloads = ''
        self._statusbar_db_locked = ''
        
        self._focus_holder = wx.Window( self, size = ( 0, 0 ) )
        
        self._closed_pages = []
        
        self._notebook = wx.Notebook( self )
        self._notebook.Bind( wx.EVT_MIDDLE_DOWN, self.EventNotebookMiddleClick )
        self._notebook.Bind( wx.EVT_RIGHT_DCLICK, self.EventNotebookMiddleClick )
        self._notebook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventNotebookPageChanged )
        
        HC.app.SetTopWindow( self )
        
        self.RefreshAcceleratorTable()
        
        self._message_manager = ClientGUICommon.PopupMessageManager( self )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        self.Bind( wx.EVT_CLOSE, self.EventExit )
        self.Bind( wx.EVT_SET_FOCUS, self.EventFocus )
        
        HC.pubsub.sub( self, 'ClearClosedPages', 'clear_closed_pages' )
        HC.pubsub.sub( self, 'NewCompose', 'new_compose_frame' )
        HC.pubsub.sub( self, 'NewPageImportGallery', 'new_page_import_gallery' )
        HC.pubsub.sub( self, 'NewPageImportHDD', 'new_hdd_import' )
        HC.pubsub.sub( self, 'NewPageImportThreadWatcher', 'new_page_import_thread_watcher' )
        HC.pubsub.sub( self, 'NewPageImportURL', 'new_page_import_url' )
        HC.pubsub.sub( self, 'NewPagePetitions', 'new_page_petitions' )
        HC.pubsub.sub( self, 'NewPageQuery', 'new_page_query' )
        HC.pubsub.sub( self, 'NewPageThreadDumper', 'new_thread_dumper' )
        HC.pubsub.sub( self, 'NewSimilarTo', 'new_similar_to' )
        HC.pubsub.sub( self, 'NotifyNewOptions', 'notify_new_options' )
        HC.pubsub.sub( self, 'NotifyNewPending', 'notify_new_pending' )
        HC.pubsub.sub( self, 'NotifyNewPermissions', 'notify_new_permissions' )
        HC.pubsub.sub( self, 'NotifyNewServices', 'notify_new_services_gui' )
        HC.pubsub.sub( self, 'NotifyNewSessions', 'notify_new_sessions' )
        HC.pubsub.sub( self, 'NotifyNewUndo', 'notify_new_undo' )
        HC.pubsub.sub( self, 'RefreshStatusBar', 'refresh_status' )
        HC.pubsub.sub( self, 'SetDBLockedStatus', 'db_locked_status' )
        HC.pubsub.sub( self, 'SetDownloadsStatus', 'downloads_status' )
        HC.pubsub.sub( self, 'SetInboxStatus', 'inbox_status' )
        HC.pubsub.sub( self, 'SetMediaFocus', 'set_media_focus' )
        
        self._menus = {}
        
        self._InitialiseMenubar()
        
        self._RefreshStatusBar()
        
        vbox = wx.BoxSizer( wx.HORIZONTAL )
        
        vbox.AddF( self._notebook, FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.Show( True )
        
        # as we are in oninit, callafter and calllater( 0 ) are different
        # later waits until the mainloop is running, I think.
        # after seems to execute synchronously
        
        if HC.options[ 'default_gui_session' ] == 'just a blank page':
            
            wx.CallLater( 1, self._NewPageQuery, HC.LOCAL_FILE_SERVICE_KEY )
            
        else:
            
            name = HC.options[ 'default_gui_session' ]
            
            wx.CallLater( 1, self._LoadGUISession, name )
            
        
        wx.CallLater( 5 * 60 * 1000, self.SaveLastSession )
        
    
    def _THREADUploadPending( self, service_key ):
        
        service = HC.app.GetManager( 'services' ).GetService( service_key )
        
        service_name = service.GetName()
        service_type = service.GetServiceType()
        
        try:
            
            prefix = 'uploading pending to ' + service_name + ': '
            
            job_key = HC.JobKey( pausable = True, cancellable = True )
            
            job_key.SetVariable( 'popup_message_text_1', prefix + 'gathering pending content' )
            
            HC.pubsub.pub( 'message', job_key )
            
            result = HC.app.Read( 'pending', service_key )
            
            if service_type == HC.FILE_REPOSITORY:
                
                ( upload_hashes, update ) = result
                
                media_results = HC.app.Read( 'media_results', HC.LOCAL_FILE_SERVICE_KEY, upload_hashes )
                
                job_key.SetVariable( 'popup_message_text_1', prefix + 'connecting to repository' )
                
                good_hashes = []
                
                error_messages = set()
                
                for ( i, media_result ) in enumerate( media_results ):
                    
                    while job_key.IsPaused() or job_key.IsCancelled() or HC.shutdown:
                        
                        time.sleep( 0.1 )
                        
                        if job_key.IsPaused(): job_key.SetVariable( 'popup_message_text_1', prefix + 'paused' )
                        
                        if job_key.IsCancelled():
                            
                            job_key.SetVariable( 'popup_message_text_1', prefix + 'cancelled' )
                            
                            print( HC.ConvertJobKeyToString( job_key ) )
                            
                            return
                            
                        
                        if HC.shutdown: return
                        
                    
                    i += 1
                    
                    hash = media_result.GetHash()
                    mime = media_result.GetMime()
                    
                    job_key.SetVariable( 'popup_message_text_1', prefix + 'uploading file ' + HC.ConvertIntToPrettyString( i + 1 ) + ' of ' + HC.ConvertIntToPrettyString( len( media_results ) ) )
                    job_key.SetVariable( 'popup_message_gauge_1', ( i, len( media_results ) ) )
                    
                    try:
                        
                        path = CC.GetFilePath( hash, mime )
                        
                        with open( path, 'rb' ) as f: file = f.read()
                        
                        service.Request( HC.POST, 'file', { 'file' : file } )
                        
                        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, locations_manager, local_ratings, remote_ratings ) = media_result.ToTuple()
                        
                        timestamp = HC.GetNow()
                        
                        content_update_row = ( hash, size, mime, timestamp, width, height, duration, num_frames, num_words )
                        
                        content_updates = [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_ADD, content_update_row ) ]
                        
                        HC.app.Write( 'content_updates', { service_key : content_updates } )
                        
                    except Exception as e:
                        
                        HC.ShowException( e )
                        
                        time.sleep( 2 )
                        
                    
                    time.sleep( 0.1 )
                    
                    HC.app.WaitUntilGoodTimeToUseGUIThread()
                    
                
                if not update.IsEmpty():
                    
                    job_key.SetVariable( 'popup_message_text_1', prefix + 'uploading petitions' )
                    
                    service.Request( HC.POST, 'update', { 'update' : update } )
                    
                    content_updates = update.GetContentUpdates( for_client = True )
                    
                    HC.app.Write( 'content_updates', { service_key : content_updates } )
                    
                
            elif service_type == HC.TAG_REPOSITORY:
                
                updates = result
                
                job_key.SetVariable( 'popup_message_text_1', prefix + 'connecting to repository' )
                
                for ( i, update ) in enumerate( updates ):
                    
                    while job_key.IsPaused() or job_key.IsCancelled() or HC.shutdown:
                        
                        time.sleep( 0.1 )
                        
                        if job_key.IsPaused(): job_key.SetVariable( 'popup_message_text_1', prefix + 'paused' )
                        
                        if job_key.IsCancelled():
                            
                            job_key.SetVariable( 'popup_message_text_1', prefix + 'cancelled' )
                            
                            print( HC.ConvertJobKeyToString( job_key ) )
                            
                            return
                            
                        
                        if HC.shutdown: return
                        
                    
                    job_key.SetVariable( 'popup_message_text_1', prefix + 'posting update: ' + HC.ConvertIntToPrettyString( i + 1 ) + '/' + HC.ConvertIntToPrettyString( len( updates ) ) )
                    job_key.SetVariable( 'popup_message_gauge_1', ( i, len( updates ) ) )
                    
                    service.Request( HC.POST, 'update', { 'update' : update } )
                    
                    content_updates = update.GetContentUpdates( for_client = True )
                    
                    HC.app.Write( 'content_updates', { service_key : content_updates } )
                    
                    time.sleep( 0.5 )
                    
                    HC.app.WaitUntilGoodTimeToUseGUIThread()
                    
                
                
            
        except Exception as e:
            
            job_key.Cancel()
            
            raise
            
        
        job_key.DeleteVariable( 'popup_message_gauge_1' )
        job_key.SetVariable( 'popup_message_text_1', prefix + 'upload done!' )
        
        print( HC.ConvertJobKeyToString( job_key ) )
        
        job_key.Finish()
        
        wx.CallLater( 1000 * 3600, job_key.Delete )
        
        HC.pubsub.pub( 'notify_new_pending' )
        
    
    def _AboutWindow( self ):
        
        aboutinfo = wx.AboutDialogInfo()
        
        aboutinfo.SetIcon( wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO ) )
        aboutinfo.SetName( 'hydrus client' )
        aboutinfo.SetVersion( HC.u( HC.SOFTWARE_VERSION ) )
        aboutinfo.SetDescription( CC.CLIENT_DESCRIPTION )
        
        with open( HC.BASE_DIR + os.path.sep + 'license.txt', 'rb' ) as f: license = f.read()
        
        aboutinfo.SetLicense( license )
        
        aboutinfo.SetDevelopers( [ 'Anonymous' ] )
        aboutinfo.SetWebSite( 'http://hydrusnetwork.github.io/hydrus/' )
        
        wx.AboutBox( aboutinfo )
        
    
    def _AccountInfo( self, service_key ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the account\'s account key.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                subject_account_key = dlg.GetValue().decode( 'hex' )
                
                service = HC.app.GetManager( 'services' ).GetService( service_key )
                
                response = service.Request( HC.GET, 'account_info', { 'subject_account_key' : subject_account_key.encode( 'hex' ) } )
                
                account_info = response[ 'account_info' ]
                
                wx.MessageBox( HC.u( account_info ) )
                
            
        
    
    def _AutoRepoSetup( self ):
        
        def do_it():
        
            edit_log = []
            
            service_key = os.urandom( 32 )
            service_type = HC.TAG_REPOSITORY
            name = 'public tag repository'
            
            info = {}
            
            info[ 'host' ] = 'hydrus.no-ip.org'
            info[ 'port' ] = 45871
            info[ 'access_key' ] = '4a285629721ca442541ef2c15ea17d1f7f7578b0c3f4f5f2a05f8f0ab297786f'.decode( 'hex' )
            
            edit_log.append( HC.EditLogActionAdd( ( service_key, service_type, name, info ) ) )
            
            service_key = os.urandom( 32 )
            service_type = HC.FILE_REPOSITORY
            name = 'read-only art file repository'
            
            info = {}
            
            info[ 'host' ] = 'hydrus.no-ip.org'
            info[ 'port' ] = 45872
            info[ 'access_key' ] = '8f8a3685abc19e78a92ba61d84a0482b1cfac176fd853f46d93fe437a95e40a5'.decode( 'hex' )
            
            edit_log.append( HC.EditLogActionAdd( ( service_key, service_type, name, info ) ) )
            
            HC.app.WriteSynchronous( 'update_services', edit_log )
            
            HC.ShowText( 'Auto repo setup done! Check services->review services to see your new services.' )
            
        
        text = 'This will attempt to set up your client with my repositories\' credentials, letting you tag on the public tag repository and see some files.'
        
        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES: HydrusThreading.CallToThread( do_it )
            
        
    
    def _AutoServerSetup( self ):
        
        def do_it():
            
            host = '127.0.0.1'
            port = HC.DEFAULT_SERVER_ADMIN_PORT
            
            try:
                
                connection = httplib.HTTPConnection( '127.0.0.1', HC.DEFAULT_SERVER_ADMIN_PORT, timeout = 20 )
                
                connection.connect()
                
                connection.close()
                
                already_running = True
                
            except:
                
                already_running = False
                
            
            if already_running:
                
                HC.ShowText( 'The server appears to be already running. Either that, or something else is using port ' + HC.u( HC.DEFAULT_SERVER_ADMIN_PORT ) + '.' )
                
                return
                
            else:
                
                try:
                    
                    HC.ShowText( u'Starting server\u2026' )
                    
                    my_scriptname = sys.argv[0]
                    
                    if my_scriptname.endswith( 'pyw' ):
                        
                        if HC.PLATFORM_WINDOWS or HC.PLATFORM_OSX: python_bin = 'pythonw'
                        else: python_bin = 'python'
                        
                        subprocess.Popen( python_bin + ' "' + HC.BASE_DIR + os.path.sep + 'server.pyw"', shell = True )
                        
                    else:
                        
                        if HC.PLATFORM_WINDOWS: subprocess.Popen( '"' + HC.BASE_DIR + os.path.sep + 'server.exe"', shell = True )
                        else: subprocess.Popen( '"./' + HC.BASE_DIR + os.path.sep + 'server"', shell = True )
                        
                    
                    time.sleep( 10 ) # give it time to init its db
                    
                except:
                    
                    HC.ShowText( 'I tried to start the server, but something failed!' + os.linesep + traceback.format_exc() )
                    
                    return
                    
                
            
            HC.ShowText( u'Creating admin service\u2026' )
            
            admin_service_key = os.urandom( 32 )
            service_type = HC.SERVER_ADMIN
            name = 'local server admin'
            
            info = {}
            
            info[ 'host' ] = host
            info[ 'port' ] = port
            
            service = CC.Service( admin_service_key, service_type, name, info )
            
            response = service.Request( HC.GET, 'init' )
            
            access_key = response[ 'access_key' ]
            
            #
            
            info[ 'access_key' ] = access_key
            
            edit_log = [ HC.EditLogActionAdd( ( admin_service_key, service_type, name, info ) ) ]
            
            HC.app.WriteSynchronous( 'update_services', edit_log )
            
            time.sleep( 2 )
            
            HC.ShowText( 'Admin service initialised.' )
            
            wx.CallAfter( ClientGUICommon.ShowKeys, 'access', ( access_key, ) )
            
            admin_service = HC.app.GetManager( 'services' ).GetService( admin_service_key )
            
            #
            
            HC.ShowText( u'Creating tag and file services\u2026' )
            
            tag_options = HC.DEFAULT_OPTIONS[ HC.TAG_REPOSITORY ]
            tag_options[ 'port' ] = HC.DEFAULT_SERVICE_PORT
            
            file_options = HC.DEFAULT_OPTIONS[ HC.FILE_REPOSITORY ]
            file_options[ 'port' ] = HC.DEFAULT_SERVICE_PORT + 1
            
            edit_log = []
            
            edit_log.append( ( HC.ADD, ( os.urandom( 32 ), HC.TAG_REPOSITORY, tag_options ) ) )
            edit_log.append( ( HC.ADD, ( os.urandom( 32 ), HC.FILE_REPOSITORY, file_options ) ) )
            
            response = admin_service.Request( HC.POST, 'services', { 'edit_log' : edit_log } )
            
            service_keys_to_access_keys = dict( response[ 'service_keys_to_access_keys' ] )
            
            HC.app.WriteSynchronous( 'update_server_services', admin_service_key, [], edit_log, service_keys_to_access_keys )
            
            HC.ShowText( 'Done! Check services->review services to see your new server and its services.' )
            
        
        text = 'This will attempt to start the server in the same install directory as this client, initialise it, and store the resultant admin accounts in the client.'
        
        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES: HydrusThreading.CallToThread( do_it )
            
        
    
    def _BackupService( self, service_key ):
        
        message = 'This will tell the server to lock and copy its database files. It will probably take a few minutes to complete, during which time it will not be able to serve any requests. The client\'s GUI will lock up as well.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                service = HC.app.GetManager( 'services' ).GetService( service_key )
                
                with wx.BusyCursor(): service.Request( HC.POST, 'backup' )
                
                HC.ShowText( 'Server backup done!' )
                
            
        
    
    def _CheckFileIntegrity( self ):
        
        message = 'This will go through all the files the database thinks it has and check that they actually exist. Any files that are missing will be deleted from the internal record.'
        message += os.linesep * 2
        message += 'You can perform a quick existence check, which will only look to see if a file exists, or a thorough content check, which will also make sure existing files are not corrupt or otherwise incorrect.'
        message += os.linesep * 2
        message += 'The thorough check will have to read all of your files\' content, which can take a long time. You should probably only do it if you suspect hard drive corruption and are now working on a safe drive.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose how thorough your integrity check will be.', yes_label = 'quick', no_label = 'thorough' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_YES: HC.app.Write( 'file_integrity', 'quick' )
            elif result == wx.ID_NO: HC.app.Write( 'file_integrity', 'thorough' )
            
        
    
    def _CloseCurrentPage( self, polite = True ):
        
        selection = self._notebook.GetSelection()
        
        if selection != wx.NOT_FOUND: self._ClosePage( selection, polite = True )
        
    
    def _ClosePage( self, selection, polite = True ):
        
        # issue with having all pages closed
        if HC.PLATFORM_OSX and self._notebook.GetPageCount() == 1: return
        
        page = self._notebook.GetPage( selection )
        
        if polite:
            
            try: page.TestAbleToClose()
            except: return
            
        
        page.Pause()
        
        page.Hide()
        
        name = self._notebook.GetPageText( selection )
        
        self._closed_pages.append( ( HC.GetNow(), selection, name, page ) )
        
        self._notebook.RemovePage( selection )
        
        if self._notebook.GetPageCount() == 0: self._focus_holder.SetFocus()
        
        HC.pubsub.pub( 'notify_new_undo' )
        
    
    def _DeleteAllClosedPages( self ):
        
        for ( time_closed, selection, name, page ) in self._closed_pages: self._DestroyPage( page )
        
        self._closed_pages = []
        
        self._focus_holder.SetFocus()
        
        HC.pubsub.pub( 'notify_new_undo' )
        
    
    def _DeleteOrphans( self ):
        
        text = 'This will iterate through the client\'s file store, deleting anything that is no longer needed. It happens automatically every few days, but you can force it here. If you have a lot of files, it will take a few minutes. A popup message will appear when it is done.'
        
        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES: HC.app.Write( 'delete_orphans' )
            
        
    
    def _DeletePending( self, service_key ):
        
        service = HC.app.GetManager( 'services' ).GetService( service_key )
        
        with ClientGUIDialogs.DialogYesNo( self, 'Are you sure you want to delete the pending data for ' + service.GetName() + '?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES: HC.app.Write( 'delete_pending', service_key )
            
        
    
    def _DeleteServiceInfo( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Are you sure you want to clear the cached service info? Rebuilding it may slow some GUI elements for a little while.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES: HC.app.Write( 'delete_service_info' )
            
        
    
    def _DestroyPage( self, page ):
        
        page.Hide()
        
        page.CleanBeforeDestroy()
        
        wx.CallAfter( page.Destroy )
        
    
    def _FetchIP( self, service_key ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the file\'s hash.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                hash = dlg.GetValue().decode( 'hex' )
                
                service = HC.app.GetManager( 'services' ).GetService( service_key )
                
                with wx.BusyCursor(): response = service.Request( HC.GET, 'ip', { 'hash' : hash.encode( 'hex' ) } )
                
                ip = response[ 'ip' ]
                timestamp = response[ 'timestamp' ]
                
                text = 'File Hash: ' + hash.encode( 'hex' ) + os.linesep + 'Uploader\'s IP: ' + ip + os.linesep + 'Upload Time (GMT): ' + time.asctime( time.gmtime( int( timestamp ) ) )
                
                print( text )
                
                wx.MessageBox( text + os.linesep + 'This has been written to the log.' )
                
            
        
    
    def _GenerateMenuInfo( self, name ):
        
        menu = wx.Menu()
        
        p = HC.app.PrepStringForDisplay
        
        def file():
            
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'import_files' ), p( '&Import Files' ), p( 'Add new files to the database.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'import_metadata' ), p( '&Import Metadata' ), p( 'Add YAML metadata.' ) )
            menu.AppendSeparator()
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_import_folders' ), p( 'Manage Import Folders' ), p( 'Manage folders from which the client can automatically import.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_export_folders' ), p( 'Manage Export Folders' ), p( 'Manage folders to which the client can automatically export.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'open_export_folder' ), p( 'Open Quick E&xport Folder' ), p( 'Open the export folder so you can easily access the files you have exported.' ) )
            menu.AppendSeparator()
            
            gui_sessions = HC.app.Read( 'gui_sessions' )
            
            gui_session_names = gui_sessions.keys()
            
            sessions = wx.Menu()
            
            if len( gui_session_names ) > 0:
                
                load = wx.Menu()
                
                for name in gui_session_names:
                    
                    load.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'load_gui_session', name ), name )
                    
                
                sessions.AppendMenu( CC.ID_NULL, p( 'Load' ), load )
                
            
            sessions.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'save_gui_session' ), p( 'Save Current' ) )
            
            if len( gui_session_names ) > 0:
                
                delete = wx.Menu()
                
                for name in gui_session_names:
                    
                    delete.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'delete_gui_session', name ), name )
                    
                
                sessions.AppendMenu( CC.ID_NULL, p( 'Delete' ), delete )
                
            
            menu.AppendMenu( CC.ID_NULL, p( 'Sessions' ), sessions )
            
            menu.AppendSeparator()
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'options' ), p( '&Options' ) )
            menu.AppendSeparator()
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'exit' ), p( '&Exit' ) )
            
            return ( menu, p( '&File' ), True )
            
        
        def undo():
            
            have_closed_pages = len( self._closed_pages ) > 0
            
            undo_manager = HC.app.GetManager( 'undo' )
            
            ( undo_string, redo_string ) = undo_manager.GetUndoRedoStrings()
            
            have_undo_stuff = undo_string is not None or redo_string is not None
            
            if have_closed_pages or have_undo_stuff:
                
                show = True
                
                did_undo_stuff = False
                
                if undo_string is not None:
                    
                    did_undo_stuff = True
                    
                    menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'undo' ), undo_string )
                    
                
                if redo_string is not None:
                    
                    did_undo_stuff = True
                    
                    menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'redo' ), redo_string )
                    
                
                if have_closed_pages:
                    
                    if did_undo_stuff: menu.AppendSeparator()
                    
                    undo_pages = wx.Menu()
                    
                    undo_pages.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'delete_all_closed_pages' ), 'clear all' )
                    
                    undo_pages.AppendSeparator()
                    
                    args = []
                    
                    for ( i, ( time_closed, index, name, page ) ) in enumerate( self._closed_pages ):
                        
                        args.append( ( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'unclose_page', i ), name + ' - ' + page.GetPrettyStatus() ) )
                        
                    
                    args.reverse() # so that recently closed are at the top
                    
                    for a in args: undo_pages.Append( *a )
                    
                    menu.AppendMenu( CC.ID_NULL, p( 'Closed Pages' ), undo_pages )
                    
                
            else: show = False
            
            return ( menu, p( '&Undo' ), show )
            
        
        def view():
            
            services = HC.app.GetManager( 'services' ).GetServices()
            
            tag_repositories = [ service for service in services if service.GetServiceType() == HC.TAG_REPOSITORY ]
            
            petition_resolve_tag_services = [ repository for repository in tag_repositories if repository.GetInfo( 'account' ).HasPermission( HC.RESOLVE_PETITIONS ) ]
            
            file_repositories = [ service for service in services if service.GetServiceType() == HC.FILE_REPOSITORY ]
            
            petition_resolve_file_services = [ repository for repository in file_repositories if repository.GetInfo( 'account' ).HasPermission( HC.RESOLVE_PETITIONS ) ]
            
            menu = wx.Menu()
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'refresh' ), p( '&Refresh' ), p( 'Refresh the current view.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'show_hide_splitters' ), p( 'Show/Hide Splitters' ), p( 'Show or hide the current page\'s splitters.' ) )
            menu.AppendSeparator()
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_page' ), p( 'Pick a New &Page' ), p( 'Pick a new page.' ) )
            menu.AppendSeparator()
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_page_query', HC.LOCAL_FILE_SERVICE_KEY ), p( '&New Local Search' ), p( 'Open a new search tab for your files' ) )
            for service in file_repositories: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_page_query', service.GetServiceKey() ), p( 'New ' + service.GetName() + ' Search' ), p( 'Open a new search tab for ' + service.GetName() + '.' ) )
            if len( petition_resolve_tag_services ) > 0 or len( petition_resolve_file_services ) > 0:
                
                menu.AppendSeparator()
                for service in petition_resolve_tag_services: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'petitions', service.GetServiceKey() ), p( service.GetName() + ' Petitions' ), p( 'Open a petition tab for ' + service.GetName() ) )
                for service in petition_resolve_file_services: menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'petitions', service.GetServiceKey() ), p( service.GetName() + ' Petitions' ), p( 'Open a petition tab for ' + service.GetName() ) )
                
            menu.AppendSeparator()
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_import_url' ), p( '&New URL Download Page' ), p( 'Open a new tab to download files from galleries or threads.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_import_booru' ), p( '&New Booru Download Page' ), p( 'Open a new tab to download files from a booru.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_import_thread_watcher' ), p( '&New Thread Watcher Page' ), p( 'Open a new tab to watch a thread.' ) )
            
            return ( menu, p( '&View' ), True )
            
        
        def download():
            
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'start_youtube_download' ), p( '&A YouTube Video' ), p( 'Enter a YouTube URL and choose which formats you would like to download' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'start_url_download' ), p( '&A Raw URL' ), p( 'Enter a normal URL and attempt to import whatever is returned' ) )
            
            return ( menu, p( 'Do&wnload' ), True )
            
        
        def database():
            
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'set_password' ), p( 'Set a &Password' ), p( 'Set a password for the database so only you can access it.' ) )
            menu.AppendSeparator()
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'backup_database' ), p( 'Create Database Backup' ), p( 'Back the database up to an external location.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'restore_database' ), p( 'Restore Database Backup' ), p( 'Restore the database from an external location.' ) )
            menu.AppendSeparator()
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'vacuum_db' ), p( '&Vacuum' ), p( 'Rebuild the Database.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'delete_orphans' ), p( '&Delete Orphan Files' ), p( 'Go through the client\'s file store, deleting any files that are no longer needed.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'delete_service_info' ), p( '&Clear Service Info Cache' ), p( 'Delete all cache service info, in case it has become desynchronised.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'regenerate_thumbnails' ), p( '&Regenerate All Thumbnails' ), p( 'Delete all thumbnails and regenerate from original files.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'file_integrity' ), p( '&Check File Integrity' ), p( 'Review and fix all local file records.' ) )
            menu.AppendSeparator()
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'clear_caches' ), p( '&Clear Caches' ), p( 'Fully clear the fullscreen, preview and thumbnail caches.' ) )
            
            return ( menu, p( '&Database' ), True )
            
        
        def pending():
            
            nums_pending = HC.app.Read( 'nums_pending' )
            
            total_num_pending = 0
            
            for ( service_key, info ) in nums_pending.items():
                
                service = HC.app.GetManager( 'services' ).GetService( service_key )
                
                service_type = service.GetServiceType()
                name = service.GetName()
                
                if service_type == HC.TAG_REPOSITORY:
                    
                    num_pending = info[ HC.SERVICE_INFO_NUM_PENDING_MAPPINGS ] + info[ HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS ] + info[ HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS ]
                    num_petitioned = info[ HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS ] + info[ HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS ] + info[ HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS ]
                    
                elif service_type == HC.FILE_REPOSITORY:
                    
                    num_pending = info[ HC.SERVICE_INFO_NUM_PENDING_FILES ]
                    num_petitioned = info[ HC.SERVICE_INFO_NUM_PETITIONED_FILES ]
                    
                
                if num_pending + num_petitioned > 0:
                    
                    submenu = wx.Menu()
                    
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'upload_pending', service_key ), p( '&Upload' ), p( 'Upload ' + name + '\'s Pending and Petitions.' ) )
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'delete_pending', service_key ), p( '&Forget' ), p( 'Clear ' + name + '\'s Pending and Petitions.' ) )
                    
                    menu.AppendMenu( CC.ID_NULL, p( name + ' Pending (' + HC.ConvertIntToPrettyString( num_pending ) + '/' + HC.ConvertIntToPrettyString( num_petitioned ) + ')' ), submenu )
                    
                
                total_num_pending += num_pending + num_petitioned
                
            
            show = total_num_pending > 0
            
            return ( menu, p( '&Pending (' + HC.ConvertIntToPrettyString( total_num_pending ) + ')' ), show )
            
        
        def services():
            
            tag_services = HC.app.GetManager( 'services' ).GetServices( ( HC.TAG_REPOSITORY, ) )
            file_services = HC.app.GetManager( 'services' ).GetServices( ( HC.FILE_REPOSITORY, ) )
            
            submenu = wx.Menu()
            
            pause_export_folders_sync_id = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'pause_export_folders_sync' )
            pause_import_folders_sync_id = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'pause_import_folders_sync' )
            pause_repo_sync_id = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'pause_repo_sync' )
            pause_subs_sync_id = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'pause_subs_sync' )
            
            submenu.AppendCheckItem( pause_export_folders_sync_id, p( '&Export Folders Synchronisation' ), p( 'Pause the client\'s export folders.' ) )
            submenu.AppendCheckItem( pause_import_folders_sync_id, p( '&Import Folders Synchronisation' ), p( 'Pause the client\'s import folders.' ) )
            submenu.AppendCheckItem( pause_repo_sync_id, p( '&Repositories Synchronisation' ), p( 'Pause the client\'s synchronisation with hydrus repositories.' ) )
            submenu.AppendCheckItem( pause_subs_sync_id, p( '&Subscriptions Synchronisation' ), p( 'Pause the client\'s synchronisation with website subscriptions.' ) )
            
            submenu.Check( pause_export_folders_sync_id, HC.options[ 'pause_export_folders_sync' ] )
            submenu.Check( pause_import_folders_sync_id, HC.options[ 'pause_import_folders_sync' ] )
            submenu.Check( pause_repo_sync_id, HC.options[ 'pause_repo_sync' ] )
            submenu.Check( pause_subs_sync_id, HC.options[ 'pause_subs_sync' ] )
            
            menu.AppendMenu( CC.ID_NULL, p( 'Pause' ), submenu )
            
            menu.AppendSeparator()
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'review_services' ), p( '&Review Services' ), p( 'Look at the services your client connects to.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_services' ), p( '&Manage Services' ), p( 'Edit the services your client connects to.' ) )
            menu.AppendSeparator()
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_tag_censorship' ), p( '&Manage Tag Censorship' ), p( 'Set which tags you want to see from which services.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_tag_siblings' ), p( '&Manage Tag Siblings' ), p( 'Set certain tags to be automatically replaced with other tags.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_tag_parents' ), p( '&Manage Tag Parents' ), p( 'Set certain tags to be automatically added with other tags.' ) )
            menu.AppendSeparator()
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_boorus' ), p( 'Manage &Boorus' ), p( 'Change the html parsing information for boorus to download from.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_imageboards' ), p( 'Manage &Imageboards' ), p( 'Change the html POST form information for imageboards to dump to.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_4chan_pass' ), p( 'Manage &4chan Pass' ), p( 'Set up your 4chan pass, so you can dump without having to fill in a captcha.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_pixiv_account' ), p( 'Manage &Pixiv Account' ), p( 'Set up your pixiv username and password.' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_subscriptions' ), p( 'Manage &Subscriptions' ), p( 'Change the queries you want the client to regularly import from.' ) )
            menu.AppendSeparator()
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_upnp', HC.LOCAL_FILE_SERVICE_KEY ), p( 'Manage Local UPnP' ) )
            
            if len( tag_services ) + len( file_services ) > 0:
                
                menu.AppendSeparator()
                submenu = wx.Menu()
                for service in tag_services: submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'news', service.GetServiceKey() ), p( service.GetName() ), p( 'Review ' + service.GetName() + '\'s past news.' ) )
                for service in file_services: submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'news', service.GetServiceKey() ), p( service.GetName() ), p( 'Review ' + service.GetName() + '\'s past news.' ) )
                menu.AppendMenu( CC.ID_NULL, p( 'News' ), submenu )
                
            
            return ( menu, p( '&Services' ), True )
            
        
        def admin():
            
            tag_repositories = HC.app.GetManager( 'services' ).GetServices( ( HC.TAG_REPOSITORY, ) )
            admin_tag_services = [ repository for repository in tag_repositories if repository.GetInfo( 'account' ).HasPermission( HC.GENERAL_ADMIN ) ]
            
            file_repositories = HC.app.GetManager( 'services' ).GetServices( ( HC.FILE_REPOSITORY, ) )
            admin_file_services = [ repository for repository in file_repositories if repository.GetInfo( 'account' ).HasPermission( HC.GENERAL_ADMIN ) ]
            
            servers_admin = HC.app.GetManager( 'services' ).GetServices( ( HC.SERVER_ADMIN, ) )
            server_admins = [ service for service in servers_admin if service.GetInfo( 'account' ).HasPermission( HC.GENERAL_ADMIN ) ]
            
            if len( admin_tag_services ) > 0 or len( admin_file_services ) > 0 or len( server_admins ) > 0:
                
                show = True
                
                for service in admin_tag_services:
                    
                    submenu = wx.Menu()
                    
                    service_key = service.GetServiceKey()
                    
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_accounts', service_key ), p( 'Create New &Accounts' ), p( 'Create new accounts.' ) )
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_account_types', service_key ), p( '&Manage Account Types' ), p( 'Add, edit and delete account types for the tag repository.' ) )
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'modify_account', service_key ), p( '&Modify an Account' ), p( 'Modify a specific account\'s type and expiration.' ) )
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'account_info', service_key ), p( '&Get an Account\'s Info' ), p( 'Fetch information about an account from the tag repository.' ) )
                    submenu.AppendSeparator()
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'stats', service_key ), p( '&Get Stats' ), p( 'Fetch operating statistics from the tag repository.' ) )
                    submenu.AppendSeparator()
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'post_news', service_key ), p( '&Post News' ), p( 'Post a news item to the tag repository.' ) )
                    
                    menu.AppendMenu( CC.ID_NULL, p( service.GetName() ), submenu )
                    
                
                for service in admin_file_services:
                    
                    submenu = wx.Menu()
                    
                    service_key = service.GetServiceKey()
                    
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_accounts', service_key ), p( 'Create New &Accounts' ), p( 'Create new accounts.' ) )
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_account_types', service_key ), p( '&Manage Account Types' ), p( 'Add, edit and delete account types for the file repository.' ) )
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'modify_account', service_key ), p( '&Modify an Account' ), p( 'Modify a specific account\'s type and expiration.' ) )
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'account_info', service_key ), p( '&Get an Account\'s Info' ), p( 'Fetch information about an account from the file repository.' ) )
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'fetch_ip', service_key ), p( '&Get an Uploader\'s IP Address' ), p( 'Fetch an uploader\'s ip address.' ) )
                    submenu.AppendSeparator()
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'stats', service_key ), p( '&Get Stats' ), p( 'Fetch operating statistics from the file repository.' ) )
                    submenu.AppendSeparator()
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'post_news', service_key ), p( '&Post News' ), p( 'Post a news item to the file repository.' ) )
                    
                    menu.AppendMenu( CC.ID_NULL, p( service.GetName() ), submenu )
                    
                
                for service in server_admins:
                    
                    submenu = wx.Menu()
                    
                    service_key = service.GetServiceKey()
                    
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_server_services', service_key ), p( 'Manage &Services' ), p( 'Add, edit, and delete this server\'s services.' ) )
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'backup_service', service_key ), p( 'Make a &Backup' ), p( 'Back up this server\'s database.' ) )
                    
                    menu.AppendMenu( CC.ID_NULL, p( service.GetName() ), submenu )
                    
                
            else: show = False
            
            return( menu, p( '&Admin' ), show )
            
        
        def help():
            
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'help' ), p( '&Help' ) )
            dont_know = wx.Menu()
            dont_know.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'auto_repo_setup' ), p( 'Just set up some repositories for me, please' ) )
            dont_know.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'auto_server_setup' ), p( 'Just set up the server on this computer, please' ) )
            menu.AppendMenu( wx.ID_NONE, p( 'I don\'t know what I am doing' ), dont_know )
            links = wx.Menu()
            site = wx.MenuItem( links, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'site' ), p( 'Site' ) )
            site.SetBitmap( wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'file_repository_small.png' ) )
            board = wx.MenuItem( links, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( '8chan_board' ), p( '8chan Board' ) )
            board.SetBitmap( wx.Bitmap( HC.STATIC_DIR + os.path.sep + '8chan.png' ) )
            twitter = wx.MenuItem( links, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'twitter' ), p( 'Twitter' ) )
            twitter.SetBitmap( wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'twitter.png' ) )
            tumblr = wx.MenuItem( links, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'tumblr' ), p( 'Tumblr' ) )
            tumblr.SetBitmap( wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'tumblr.png' ) )
            links.AppendItem( site )
            links.AppendItem( board )
            links.AppendItem( twitter )
            links.AppendItem( tumblr )
            menu.AppendMenu( wx.ID_NONE, p( 'Links' ), links )
            debug = wx.Menu()
            debug.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'debug_garbage' ), p( 'Garbage' ) )
            menu.AppendMenu( wx.ID_NONE, p( 'Debug' ), debug )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'help_shortcuts' ), p( '&Shortcuts' ) )
            menu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'help_about' ), p( '&About' ) )
            
            return ( menu, p( '&Help' ), True )
            
        
        if name == 'file': return file()
        elif name == 'undo': return undo()
        elif name == 'view': return view()
        elif name == 'download': return download()
        elif name == 'database': return database()
        elif name == 'pending': return pending()
        elif name == 'services': return services()
        elif name == 'admin': return admin()
        elif name == 'help': return help()
        
    
    def _GenerateNewAccounts( self, service_key ):
        
        with ClientGUIDialogs.DialogGenerateNewAccounts( self, service_key ) as dlg: dlg.ShowModal()
        
    
    def _ImportFiles( self, paths = [] ):
        
        with ClientGUIDialogs.DialogInputLocalFiles( self, paths ) as dlg: dlg.ShowModal()
        
    
    def _ImportMetadata( self ):
        
        with wx.FileDialog( self, style = wx.FD_MULTIPLE ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                paths = dlg.GetPaths()
                
                for path in paths:
                    
                    try:
                        
                        with open( path, 'rb' ) as f: o = yaml.safe_load( f )
                        
                        if isinstance( o, HC.ServerToClientUpdate ):
                            
                            # turn this into a thread that'll spam it to a gui-polite gauge
                            
                            update = o
                            
                            service_key = ClientGUIDialogs.SelectServiceKey( service_types = ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ) )
                            
                            if service_key is not None:
                                
                                content_updates = []
                                current_weight = 0
                                
                                for content_update in update.IterateContentUpdates():
                                    
                                    content_updates.append( content_update )
                                    
                                    current_weight += len( content_update.GetHashes() )
                                    
                                    if current_weight > 50:
                                        
                                        HC.app.WriteSynchronous( 'content_updates', { service_key : content_updates } )
                                        
                                        content_updates = []
                                        current_weight = 0
                                        
                                    
                                
                                if len( content_updates ) > 0: HC.app.WriteSynchronous( 'content_updates', { service_key : content_updates } )
                                
                            
                        
                    except Exception as e: HC.ShowException( e )
                    
                
        
    
    def _InitialiseMenubar( self ):
        
        self._menubar = wx.MenuBar()
        
        self.SetMenuBar( self._menubar )
        
        for name in MENU_ORDER:
            
            ( menu, label, show ) = self._GenerateMenuInfo( name )
            
            if show: self._menubar.Append( menu, label )
            
            self._menus[ name ] = ( menu, label, show )
            
        
    
    def _LoadGUISession( self, name ):
        
        names_to_info = HC.app.Read( 'gui_sessions' )
        
        if name not in names_to_info: self._NewPageQuery( HC.LOCAL_FILE_SERVICE_KEY )
        else:
            
            info = names_to_info[ name ]
            
            for page in [ self._notebook.GetPage( i ) for i in range( self._notebook.GetPageCount() ) ]:
                
                try: page.TestAbleToClose()
                except: return
                
            
            while self._notebook.GetPageCount() > 0:
                
                self._CloseCurrentPage( polite = False )
                
            
            for ( page_name, c_text, args, kwargs ) in info:
                
                try:
                    
                    c = ClientGUIPages.text_to_class[ c_text ]
                    
                    kwargs[ 'starting_from_session' ] = True
                    
                    new_page = c( self._notebook, *args, **kwargs )
                    
                    self._notebook.AddPage( new_page, page_name, select = True )
                    
                    self._notebook.SetSelection( self._notebook.GetPageCount() - 1 )
                    
                    new_page.SetSearchFocus()
                    
                except Exception as e: HC.ShowException( e )
                
            
            if HC.PLATFORM_OSX: self._ClosePage( 0 )
            
        
    
    def _Manage4chanPass( self ):
        
        with ClientGUIDialogsManage.DialogManage4chanPass( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageAccountTypes( self, service_key ):
        
        with ClientGUIDialogsManage.DialogManageAccountTypes( self, service_key ) as dlg: dlg.ShowModal()
        
    
    def _ManageBoorus( self ):
        
        with ClientGUIDialogsManage.DialogManageBoorus( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageContacts( self ):
        
        with ClientGUIDialogsManage.DialogManageContacts( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageExportFolders( self ):
        
        with ClientGUIDialogsManage.DialogManageExportFolders( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageImageboards( self ):
        
        with ClientGUIDialogsManage.DialogManageImageboards( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageImportFolders( self ):
        
        with ClientGUIDialogsManage.DialogManageImportFolders( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageOptions( self ):
        
        with ClientGUIDialogsManage.DialogManageOptions( self ) as dlg: dlg.ShowModal()
        
    
    def _ManagePixivAccount( self ):
        
        with ClientGUIDialogsManage.DialogManagePixivAccount( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageServer( self, service_key ):
        
        with ClientGUIDialogsManage.DialogManageServer( self, service_key ) as dlg: dlg.ShowModal()
        
    
    def _ManageServices( self ):
        
        original_pause_status = HC.options[ 'pause_repo_sync' ]
        
        HC.options[ 'pause_repo_sync' ] = True
        
        try:
            
            with ClientGUIDialogsManage.DialogManageServices( self ) as dlg: dlg.ShowModal()
            
        finally: HC.options[ 'pause_repo_sync' ] = original_pause_status
        
    
    def _ManageSubscriptions( self ):
        
        original_pause_status = HC.options[ 'pause_subs_sync' ]
        
        HC.options[ 'pause_subs_sync' ] = True
        
        try:
            
            with ClientGUIDialogsManage.DialogManageSubscriptions( self ) as dlg: dlg.ShowModal()
            
        finally: HC.options[ 'pause_subs_sync' ] = original_pause_status
        
    
    def _ManageTagCensorship( self ):
        
        with ClientGUIDialogsManage.DialogManageTagCensorship( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageTagParents( self ):
        
        with ClientGUIDialogsManage.DialogManageTagParents( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageTagSiblings( self ):
        
        with ClientGUIDialogsManage.DialogManageTagSiblings( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageUPnP( self, service_key ):
        
        with ClientGUIDialogsManage.DialogManageUPnP( self, service_key ) as dlg: dlg.ShowModal()
        
    
    def _ModifyAccount( self, service_key ):
        
        service = HC.app.GetManager( 'services' ).GetService( service_key )
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the account key for the account to be modified.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try: account_key = dlg.GetValue().decode( 'hex' )
                except:
                    
                    wx.MessageBox( 'Could not parse that account key' )
                    
                    return
                    
                
                subject_identifiers = ( HC.AccountIdentifier( account_key = account_key ), )
                
                with ClientGUIDialogs.DialogModifyAccounts( self, service_key, subject_identifiers ) as dlg2: dlg2.ShowModal()
                
            
        
    
    def _NewPageImportBooru( self ):

        with ClientGUIDialogs.DialogSelectBooru( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                booru = dlg.GetBooru()
                
                self._NewPageImportGallery( 'booru', booru )
                
            
        
    
    def _NewPageImportGallery( self, name, import_type ):
        
        new_page = ClientGUIPages.PageImportGallery( self._notebook, name, import_type )
        
        if name == 'booru': page_name = import_type.GetName()
        elif import_type is None: page_name = name
        else: page_name = name + ' by ' + import_type
        
        self._notebook.AddPage( new_page, page_name, select = True )
        
        self._notebook.SetSelection( self._notebook.GetPageCount() - 1 )
        
        new_page.SetSearchFocus()
        
    
    def _NewPageImportThreadWatcher( self ):
        
        new_page = ClientGUIPages.PageImportThreadWatcher( self._notebook )
        
        self._notebook.AddPage( new_page, 'thread watcher', select = True )
        
        self._notebook.SetSelection( self._notebook.GetPageCount() - 1 )
        
        new_page.SetSearchFocus()
        
    
    def _NewPageImportURL( self ):
        
        new_page = ClientGUIPages.PageImportURL( self._notebook )
        
        self._notebook.AddPage( new_page, 'download', select = True )
        
        self._notebook.SetSelection( self._notebook.GetPageCount() - 1 )
        
        new_page.SetSearchFocus()
        
    
    def _NewPagePetitions( self, service_key = None ):
        
        if service_key is None: service_key = ClientGUIDialogs.SelectServiceKey( service_types = HC.REPOSITORIES, permission = HC.RESOLVE_PETITIONS )
        
        if service_key is not None:
            
            service = HC.app.GetManager( 'services' ).GetService( service_key )
            
            account = service.GetInfo( 'account' )
            
            if not account.HasPermission( HC.RESOLVE_PETITIONS ): return
            
            self._notebook.AddPage( ClientGUIPages.PagePetitions( self._notebook, service_key ), service.GetName() + ' petitions', select = True )
            
        
    
    def _NewPageQuery( self, service_key, initial_media_results = [], initial_predicates = [] ):
        
        if service_key is None: service_key = ClientGUIDialogs.SelectServiceKey( service_types = ( HC.FILE_REPOSITORY, ) )
        
        if service_key is not None:
            
            new_page = ClientGUIPages.PageQuery( self._notebook, service_key, initial_media_results = initial_media_results, initial_predicates = initial_predicates )
            
            self._notebook.AddPage( new_page, 'files', select = True )
            
            wx.CallAfter( new_page.SetSearchFocus )
            
        
    
    def _News( self, service_key ):
        
        with ClientGUIDialogs.DialogNews( self, service_key ) as dlg: dlg.ShowModal()
        
    
    def _OpenExportFolder( self ):
        
        export_path = HC.ConvertPortablePathToAbsPath( HC.options[ 'export_path' ] )
        
        if export_path is None: wx.MessageBox( 'Export folder is missing or not set.' )
        else:
            
            export_path = os.path.normpath( export_path ) # windows complains about those forward slashes when launching from the command line
            
            HC.LaunchDirectory( export_path )
            
        
    
    def _PauseSync( self, sync_type ):
        
        if sync_type == 'repo':
            
            HC.options[ 'pause_repo_sync' ] = not HC.options[ 'pause_repo_sync' ]
            
            HC.pubsub.pub( 'notify_restart_repo_sync_daemon' )
            
        elif sync_type == 'subs':
            
            HC.options[ 'pause_subs_sync' ] = not HC.options[ 'pause_subs_sync' ]
            
            HC.pubsub.pub( 'notify_restart_subs_sync_daemon' )
            
        elif sync_type == 'export_folders':
            
            HC.options[ 'pause_export_folders_sync' ] = not HC.options[ 'pause_export_folders_sync' ]
            
            HC.pubsub.pub( 'notify_restart_export_folders_daemon' )
            
        elif sync_type == 'import_folders':
            
            HC.options[ 'pause_import_folders_sync' ] = not HC.options[ 'pause_import_folders_sync' ]
            
            HC.pubsub.pub( 'notify_restart_import_folders_daemon' )
            
        
        try: HC.app.Write( 'save_options' )
        except: wx.MessageBox( traceback.format_exc() )
        
    
    def _PostNews( self, service_key ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the news you would like to post.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                news = dlg.GetValue()
                
                service = HC.app.GetManager( 'services' ).GetService( service_key )
                
                with wx.BusyCursor(): service.Request( HC.POST, 'news', { 'news' : news } )
                
            
        
    
    def _RefreshStatusBar( self ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is None: media_status = ''
        else: media_status = page.GetPrettyStatus()
        
        self._statusbar_media = media_status
        
        self._statusbar.SetStatusText( self._statusbar_media, number = 0 )
        self._statusbar.SetStatusText( self._statusbar_inbox, number = 1 )
        self._statusbar.SetStatusText( self._statusbar_downloads, number = 2 )
        self._statusbar.SetStatusText( self._statusbar_db_locked, number = 3 )
        
    
    def _RegenerateThumbnails( self ):
        
        text = 'This will rebuild all your thumbnails from the original files. You probably only want to do this if you experience thumbnail errors. If you have a lot of files, it will take some time. A popup message will show its progress.'
        
        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                def THREADRegenerateThumbnails():
                    
                    prefix = 'regenerating thumbnails: '
                    
                    job_key = HC.JobKey( pausable = True, cancellable = True )
                    
                    job_key.SetVariable( 'popup_message_text_1', prefix + 'creating directories' )
                    
                    HC.pubsub.pub( 'message', job_key )
                    
                    if not os.path.exists( HC.CLIENT_THUMBNAILS_DIR ): os.mkdir( HC.CLIENT_THUMBNAILS_DIR )
                    
                    hex_chars = '0123456789abcdef'
                    
                    for ( one, two ) in itertools.product( hex_chars, hex_chars ):
                        
                        dir = HC.CLIENT_THUMBNAILS_DIR + os.path.sep + one + two
                        
                        if not os.path.exists( dir ): os.mkdir( dir )
                        
                    
                    num_broken = 0
                    
                    for ( i, path ) in enumerate( CC.IterateAllFilePaths() ):
                        
                        try:
                            
                            while job_key.IsPaused() or job_key.IsCancelled() or HC.shutdown:
                                
                                time.sleep( 0.1 )
                                
                                if job_key.IsPaused(): job_key.SetVariable( 'popup_message_text_1', prefix + 'paused' )
                                
                                if job_key.IsCancelled():
                                    
                                    job_key.SetVariable( 'popup_message_text_1', prefix + 'cancelled' )
                                    
                                    print( HC.ConvertJobKeyToString( job_key ) )
                                    
                                    return
                                    
                                
                                if HC.shutdown: return
                                
                            
                            mime = HydrusFileHandling.GetMime( path )
                            
                            if mime in HC.MIMES_WITH_THUMBNAILS:
                                
                                job_key.SetVariable( 'popup_message_text_1', prefix + HC.ConvertIntToPrettyString( i ) + ' done' )
                                
                                ( base, filename ) = os.path.split( path )
                                
                                ( hash_encoded, ext ) = filename.split( '.', 1 )
                                
                                hash = hash_encoded.decode( 'hex' )
                                
                                thumbnail = HydrusFileHandling.GenerateThumbnail( path )
                                
                                thumbnail_path = CC.GetExpectedThumbnailPath( hash, True )
                                
                                with open( thumbnail_path, 'wb' ) as f: f.write( thumbnail )
                                
                                thumbnail_resized = HydrusFileHandling.GenerateThumbnail( thumbnail_path, HC.options[ 'thumbnail_dimensions' ] )
                                
                                thumbnail_resized_path = CC.GetExpectedThumbnailPath( hash, False )
                                
                                with open( thumbnail_resized_path, 'wb' ) as f: f.write( thumbnail_resized )
                                
                            
                        except:
                            
                            print( path )
                            print( traceback.format_exc() )
                            
                            num_broken += 1
                            
                        
                    
                    if num_broken > 0: job_key.SetVariable( 'popup_message_text_1', prefix + 'done! ' + HC.ConvertIntToPrettyString( num_broken ) + ' files caused errors, which have been written to the log.' )
                    else: job_key.SetVariable( 'popup_message_text_1', prefix + 'done!' )
                    
                    print( HC.ConvertJobKeyToString( job_key ) )
                    
                    job_key.Finish()
                    
                
                HydrusThreading.CallToThread( THREADRegenerateThumbnails )
                
            
        
    
    def _ReviewServices( self ): FrameReviewServices()
    
    def _SaveGUISession( self, name = None ):
        
        if name is None:
            
            while True:
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Enter a name for the new session.' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        name = dlg.GetValue()
                        
                        if name in ( 'just a blank page', 'last session' ):
                            
                            wx.MessageBox( 'Sorry, you cannot have that name! Try another.' )
                            
                        else: break
                        
                    else: return
                    
                
            
        
        info = []
        
        for i in range( self._notebook.GetPageCount() ):
            
            page = self._notebook.GetPage( i )
            
            page_name = self._notebook.GetPageText( i )
            
            c = type( page )
            
            c_text = ClientGUIPages.class_to_text[ c ]
            
            try: ( args, kwargs ) = page.GetSessionArgs()
            except: continue
            
            info.append( ( page_name, c_text, args, kwargs ) )
            
        
        HC.app.Write( 'gui_session', name, info )
        
        HC.pubsub.pub( 'notify_new_sessions' )
        
    
    def _SetPassword( self ):
        
        message = '''You can set a password to be asked for whenever the client starts.

Though not foolproof, it will stop noobs from easily seeing your files if you leave your machine unattended.

Do not ever forget your password! If you do, you'll have to manually insert a yaml-dumped python dictionary into a sqlite database or recompile from source to regain easy access. This is not trivial.

The password is cleartext here but obscured in the entry dialog. Enter a blank password to remove.'''
        
        with ClientGUIDialogs.DialogTextEntry( self, message, allow_blank = True ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                password = dlg.GetValue()
                
                if password == '': password = None
                
                HC.app.Write( 'set_password', password )
                
            
        
    
    def _SetMediaFocus( self ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None: page.SetMediaFocus()
        
    
    def _SetSearchFocus( self ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None: page.SetSearchFocus()
        
    
    def _SetSynchronisedWait( self ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None: page.SetSynchronisedWait()
        
    
    def _StartURLDownload( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter URL.' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_OK:
                
                url = dlg.GetValue()
                
                url_string = url
                
                job_key = HC.JobKey( pausable = True, cancellable = True )
                
                HC.pubsub.pub( 'message', job_key )
                
                HydrusThreading.CallToThread( HydrusDownloading.THREADDownloadURL, job_key, url, url_string )
                
            
        
    
    def _StartYoutubeDownload( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter YouTube URL.' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_OK:
                
                url = dlg.GetValue()
                
                info = HydrusDownloading.GetYoutubeFormats( url )
                
                with ClientGUIDialogs.DialogSelectYoutubeURL( self, info ) as select_dlg: select_dlg.ShowModal()
                
            
        
    
    def _Stats( self, service_key ):
        
        service = HC.app.GetManager( 'services' ).GetService( service_key )
        
        response = service.Request( HC.GET, 'stats' )
        
        stats = response[ 'stats' ]
        
        wx.MessageBox( HC.u( stats ) )
        
    
    def _UnclosePage( self, closed_page_index ):
        
        ( time_closed, index, name, page ) = self._closed_pages.pop( closed_page_index )
        
        page.Resume()
        
        page.Show()
        
        index = min( index, self._notebook.GetPageCount() )
        
        self._notebook.InsertPage( index, page, name, True )
        
        HC.pubsub.pub( 'notify_new_undo' )
        
    
    def _UploadPending( self, service_key ):
        
        HydrusThreading.CallToThread( self._THREADUploadPending, service_key )
        
    
    def _VacuumDatabase( self ):
        
        text = 'This will rebuild the database, rewriting all indices and tables to be contiguous and optimising most operations. It happens automatically every few days, but you can force it here. If you have a large database, it will take a few minutes. A popup message will appear when it is done.'
        
        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES: HC.app.Write( 'vacuum' )
            
        
    
    def ClearClosedPages( self ):
        
        new_closed_pages = []
        
        now = HC.GetNow()
        
        timeout = 60 * 60
        
        for ( time_closed, index, name, page ) in self._closed_pages:
            
            if time_closed + timeout < now: self._DestroyPage( page )
            else: new_closed_pages.append( ( time_closed, index, name, page ) )
            
        
        old_closed_pages = self._closed_pages
        
        self._closed_pages = new_closed_pages
        
        if len( old_closed_pages ) != len( new_closed_pages ): HC.pubsub.pub( 'notify_new_undo' )
        
    
    def DoFirstStart( self ):
        
        with ClientGUIDialogs.DialogFirstStart( self ) as dlg: dlg.ShowModal()
        
    
    def EventExit( self, event ):
        
        if HC.options[ 'confirm_client_exit' ]:
            
            text = 'Are you sure you want to exit the client? (Will auto-yes in 15 seconds)'
            
            with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
                
                call_later = wx.CallLater( 15000, dlg.EndModal, wx.ID_YES )
                
                if dlg.ShowModal() == wx.ID_NO:
                    
                    call_later.Stop()
                    
                    return
                    
                
                call_later.Stop()
                
            
        
        try: splash = FrameSplash( 'exit' )
        except:
            
            print( 'There was an error trying to start the splash screen!' )
            
            print( traceback.format_exc() )
            
            try: wx.CallAfter( splash.Destroy )
            except: pass
            
        
    
    def EventFocus( self, event ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None: page.SetMediaFocus()
        
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'account_info': self._AccountInfo( data )
            elif command == 'auto_repo_setup': self._AutoRepoSetup()
            elif command == 'auto_server_setup': self._AutoServerSetup()
            elif command == 'backup_database': HC.app.BackupDatabase()
            elif command == 'backup_service': self._BackupService( data )
            elif command == 'clear_caches': HC.app.ClearCaches()
            elif command == 'close_page': self._CloseCurrentPage()
            elif command == 'debug_garbage':
                
                import gc
                import collections
                import types
                
                gc.collect()
                
                count = collections.Counter()
                
                class_count = collections.Counter()
                
                for o in gc.get_objects():
                    
                    count[ type( o ) ] += 1
                    
                    if type( o ) == types.InstanceType: class_count[ o.__class__.__name__ ] += 1
                    elif type( o ) == types.BuiltinFunctionType: class_count[ o.__name__ ] += 1
                    elif type( o ) == types.BuiltinMethodType: class_count[ o.__name__ ] += 1
                    
                
                print( 'gc:' )
                
                for ( k, v ) in count.items():
                    
                    if v > 100: print ( k, v )
                    
                
                for ( k, v ) in class_count.items():
                    
                    if v > 100: print ( k, v )
                    
                
                print( 'garbage: ' + HC.u( gc.garbage ) )
                
            elif command == 'delete_all_closed_pages': self._DeleteAllClosedPages()
            elif command == 'delete_gui_session':
                
                HC.app.Write( 'delete_gui_session', data )
                
                HC.pubsub.pub( 'notify_new_sessions' )
                
            elif command == 'delete_orphans': self._DeleteOrphans()
            elif command == 'delete_pending': self._DeletePending( data )
            elif command == 'delete_service_info': self._DeleteServiceInfo()
            elif command == 'exit': self.EventExit( event )
            elif command == 'fetch_ip': self._FetchIP( data )
            elif command == '8chan_board': webbrowser.open( 'http://8ch.net/hydrus/index.html' )
            elif command == 'file_integrity': self._CheckFileIntegrity()
            elif command == 'help': webbrowser.open( 'file://' + HC.BASE_DIR + '/help/index.html' )
            elif command == 'help_about': self._AboutWindow()
            elif command == 'help_shortcuts': wx.MessageBox( CC.SHORTCUT_HELP )
            elif command == 'import_files': self._ImportFiles()
            elif command == 'import_metadata': self._ImportMetadata()
            elif command == 'load_gui_session': self._LoadGUISession( data )
            elif command == 'manage_4chan_pass': self._Manage4chanPass()
            elif command == 'manage_account_types': self._ManageAccountTypes( data )
            elif command == 'manage_boorus': self._ManageBoorus()
            elif command == 'manage_contacts': self._ManageContacts()
            elif command == 'manage_export_folders': self._ManageExportFolders()
            elif command == 'manage_imageboards': self._ManageImageboards()
            elif command == 'manage_import_folders': self._ManageImportFolders()
            elif command == 'manage_pixiv_account': self._ManagePixivAccount()
            elif command == 'manage_server_services': self._ManageServer( data )
            elif command == 'manage_services': self._ManageServices()
            elif command == 'manage_subscriptions': self._ManageSubscriptions()
            elif command == 'manage_tag_censorship': self._ManageTagCensorship()
            elif command == 'manage_tag_parents': self._ManageTagParents()
            elif command == 'manage_tag_siblings': self._ManageTagSiblings()
            elif command == 'manage_upnp': self._ManageUPnP( data )
            elif command == 'modify_account': self._ModifyAccount( data )
            elif command == 'new_accounts': self._GenerateNewAccounts( data )
            elif command == 'new_import_booru': self._NewPageImportBooru()
            elif command == 'new_import_thread_watcher': self._NewPageImportThreadWatcher()
            elif command == 'new_import_url': self._NewPageImportURL()
            elif command == 'new_page':
                
                with ClientGUIDialogs.DialogPageChooser( self ) as dlg: dlg.ShowModal()
                
            elif command == 'new_page_query': self._NewPageQuery( data )
            elif command == 'news': self._News( data )
            elif command == 'open_export_folder': self._OpenExportFolder()
            elif command == 'options': self._ManageOptions()
            elif command == 'pause_export_folders_sync': self._PauseSync( 'export_folders' )
            elif command == 'pause_import_folders_sync': self._PauseSync( 'import_folders' )
            elif command == 'pause_repo_sync': self._PauseSync( 'repo' )
            elif command == 'pause_subs_sync': self._PauseSync( 'subs' )
            elif command == 'petitions': self._NewPagePetitions( data )
            elif command == 'post_news': self._PostNews( data )
            elif command == 'redo': HC.pubsub.pub( 'redo' )
            elif command == 'refresh':
                
                page = self._notebook.GetCurrentPage()
                
                if page is not None: page.RefreshQuery()
                
            elif command == 'regenerate_thumbnails': self._RegenerateThumbnails()
            elif command == 'restore_database': HC.app.RestoreDatabase()
            elif command == 'review_services': self._ReviewServices()
            elif command == 'save_gui_session': self._SaveGUISession()
            elif command == 'set_password': self._SetPassword()
            elif command == 'set_media_focus': self._SetMediaFocus()
            elif command == 'set_search_focus': self._SetSearchFocus()
            elif command == 'show_hide_splitters':
                
                page = self._notebook.GetCurrentPage()
                
                if page is not None: page.ShowHideSplit()
                
            elif command == 'site': webbrowser.open( 'http://hydrusnetwork.github.io/hydrus/' )
            elif command == 'start_url_download': self._StartURLDownload()
            elif command == 'start_youtube_download': self._StartYoutubeDownload()
            elif command == 'stats': self._Stats( data )
            elif command == 'synchronised_wait_switch': self._SetSynchronisedWait()
            elif command == 'tumblr': webbrowser.open( 'http://hydrus.tumblr.com/' )
            elif command == 'twitter': webbrowser.open( 'http://twitter.com/#!/hydrusnetwork' )
            elif command == 'unclose_page': self._UnclosePage( data )
            elif command == 'undo': HC.pubsub.pub( 'undo' )
            elif command == 'upload_pending': self._UploadPending( data )
            elif command == 'vacuum_db': self._VacuumDatabase()
            else: event.Skip()
            
        
    
    def EventNotebookMiddleClick( self, event ):
        
        ( tab_index, flags ) = self._notebook.HitTest( ( event.GetX(), event.GetY() ) )
        
        self._ClosePage( tab_index )
        
    
    def EventNotebookPageChanged( self, event ):
        
        old_selection = event.GetOldSelection()
        selection = event.GetSelection()
        
        if old_selection != -1: self._notebook.GetPage( old_selection ).PageHidden()
        
        if selection != -1: self._notebook.GetPage( selection ).PageShown()
        
        self._RefreshStatusBar()
        
        event.Skip( True )
        
    
    def ImportFiles( self, paths ): self._ImportFiles( paths )
    '''
    def NewCompose( self, identity ):
        
        draft_key = os.urandom( 32 )
        conversation_key = draft_key
        subject = ''
        contact_from = identity
        contacts_to = []
        recipients_visible = False
        body = ''
        attachments = []
        
        empty_draft_message = ClientConstantsMessages.DraftMessage( draft_key, conversation_key, subject, contact_from, contacts_to, recipients_visible, body, attachments, is_new = True )
        
        FrameComposeMessage( empty_draft_message )
        
    '''
    def NewPageImportGallery( self, gallery_name, gallery_type ): self._NewPageImportGallery( gallery_name, gallery_type )
    
    def NewPageImportHDD( self, paths_info, advanced_import_options = {}, paths_to_tags = {}, delete_after_success = False ):
        
        new_page = ClientGUIPages.PageImportHDD( self._notebook, paths_info, advanced_import_options = advanced_import_options, paths_to_tags = paths_to_tags, delete_after_success = delete_after_success )
        
        self._notebook.AddPage( new_page, 'import', select = True )
        
        self._notebook.SetSelection( self._notebook.GetPageCount() - 1 )
        
    
    def NewPageImportThreadWatcher( self ): self._NewPageImportThreadWatcher()
    
    def NewPageImportURL( self ): self._NewPageImportURL()
    
    def NewPagePetitions( self, service_key ): self._NewPagePetitions( service_key )
    
    def NewPageQuery( self, service_key, initial_media_results = [], initial_predicates = [] ): self._NewPageQuery( service_key, initial_media_results = initial_media_results, initial_predicates = initial_predicates )
    
    def NewPageThreadDumper( self, hashes ):
        
        with ClientGUIDialogs.DialogSelectImageboard( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                imageboard = dlg.GetImageboard()
                
                new_page = ClientGUIPages.PageThreadDumper( self._notebook, imageboard, hashes )
                
                self._notebook.AddPage( new_page, 'imageboard dumper', select = True )
                
                new_page.SetSearchFocus()
                
            
        
    
    def NewSimilarTo( self, file_service_key, hash ): self._NewPageQuery( file_service_key, initial_predicates = [ HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO, ( hash, 5 ) ) ) ] )
    
    def NotifyNewOptions( self ):
        
        self.RefreshAcceleratorTable()
        
        self.RefreshMenu( 'services' )
        
    
    def NotifyNewPending( self ): self.RefreshMenu( 'pending' )
    
    def NotifyNewPermissions( self ):
        
        self.RefreshMenu( 'view' )
        self.RefreshMenu( 'admin' )
        
    
    def NotifyNewServices( self ):
        
        self.RefreshMenu( 'view' )
        self.RefreshMenu( 'services' )
        self.RefreshMenu( 'admin' )
        
    
    def NotifyNewSessions( self ): self.RefreshMenu( 'file' )
    
    def NotifyNewUndo( self ): self.RefreshMenu( 'undo' )
    
    def RefreshAcceleratorTable( self ):
        
        interested_actions = [ 'archive', 'inbox', 'close_page', 'filter', 'ratings_filter', 'manage_ratings', 'manage_tags', 'new_page', 'refresh', 'set_media_focus', 'set_search_focus', 'show_hide_splitters', 'synchronised_wait_switch', 'undo', 'redo' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    def RefreshMenu( self, name ):
        
        ( menu, label, show ) = self._GenerateMenuInfo( name )
        
        if HC.PLATFORM_OSX: menu.SetTitle( label ) # causes bugs in os x if this is not here
        
        ( old_menu, old_label, old_show ) = self._menus[ name ]
        
        if old_show:
            
            old_menu_index = self._menubar.FindMenu( old_label )
            
            if show: self._menubar.Replace( old_menu_index, menu, label )
            else: self._menubar.Remove( old_menu_index )
            
        else:
            
            if show:
                
                insert_index = 0
                
                for temp_name in MENU_ORDER:
                    
                    if temp_name == name: break
                    
                    ( temp_menu, temp_label, temp_show ) = self._menus[ temp_name ]
                    
                    if temp_show: insert_index += 1
                    
                
                self._menubar.Insert( insert_index, menu, label )
                
            
        
        self._menus[ name ] = ( menu, label, show )
        
        wx.CallAfter( old_menu.Destroy )
        
    
    def RefreshStatusBar( self ): self._RefreshStatusBar()
    
    def SaveLastSession( self ):
        
        self._SaveGUISession( 'last session' )
        
        wx.CallLater( 5 * 60 * 1000, self.SaveLastSession )
        
    
    def SetDBLockedStatus( self, status ):
        
        if self.IsShown():
            
            self._statusbar_db_locked = status
            
            self._RefreshStatusBar()
            
        
    
    def SetDownloadsStatus( self, status ):
        
        if self.IsShown():
            
            self._statusbar_downloads = status
            
            self._RefreshStatusBar()
            
        
    
    def SetMediaFocus( self ): self._SetMediaFocus()
    
    def SetInboxStatus( self, status ):
        
        if self.IsShown():
            
            self._statusbar_inbox = status
            
            self._RefreshStatusBar()
            
        
    
    def Shutdown( self ):
        
        self._message_manager.Hide()
        
        self.Hide()
        
        try: self._message_manager.CleanBeforeDestroy()
        except: pass
        
        for page in [ self._notebook.GetPage( i ) for i in range( self._notebook.GetPageCount() ) ]: page.CleanBeforeDestroy()
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None:
            
            ( HC.options[ 'hpos' ], HC.options[ 'vpos' ] ) = page.GetSashPositions()
            
        
        HC.app.Write( 'save_options' )
        
        self._SaveGUISession( 'last session' )
        
        wx.CallAfter( self.Destroy )
        
    
    def TestAbleToClose( self ):
        
        for page in [ self._notebook.GetPage( i ) for i in range( self._notebook.GetPageCount() ) ]: page.TestAbleToClose()
        
    '''
class FrameComposeMessage( ClientGUICommon.Frame ):
    
    def __init__( self, empty_draft_message ):
        
        ClientGUICommon.Frame.__init__( self, None, title = HC.app.PrepStringForDisplay( 'Compose Message' ) )
        
        self.SetInitialSize( ( 920, 600 ) )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._draft_panel = ClientGUIMessages.DraftPanel( self, empty_draft_message )
        
        vbox.AddF( self._draft_panel, FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.Show( True )
        
        HC.pubsub.sub( self, 'DeleteConversation', 'delete_conversation_gui' )
        HC.pubsub.sub( self, 'DeleteDraft', 'delete_draft_gui' )
        
    
    def DeleteConversation( self, conversation_key ):
        
        if self._draft_panel.GetConversationKey() == conversation_key: self.Close()
        
    
    def DeleteDraft( self, draft_key ):
        
        if draft_key == self._draft_panel.GetDraftKey(): self.Close()
        
    '''
class FrameReviewServices( ClientGUICommon.Frame ):
    
    def __init__( self ):
        
        def InitialiseControls():
            
            self._notebook = wx.Notebook( self )
            
            self._local_listbook = ClientGUICommon.ListBook( self._notebook )
            self._remote_listbook = ClientGUICommon.ListBook( self._notebook )
            
            self._edit = wx.Button( self, label = 'manage services' )
            self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
            
            self._ok = wx.Button( self, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
        
        def PopulateControls():
            
            self._InitialiseServices()
            
        
        def ArrangeControls():
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            self._notebook.AddPage( self._local_listbook, 'local' )
            self._notebook.AddPage( self._remote_listbook, 'remote' )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._notebook, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._edit, FLAGS_SMALL_INDENT )
            vbox.AddF( self._ok, FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
            self.SetInitialSize( ( 880, 620 ) )
            
        
        ( pos_x, pos_y ) = HC.app.GetGUI().GetPositionTuple()
        
        pos = ( pos_x + 25, pos_y + 50 )
        
        tlp = HC.app.GetTopWindow()
        
        ClientGUICommon.Frame.__init__( self, tlp, title = HC.app.PrepStringForDisplay( 'Review Services' ), pos = pos )
        
        InitialiseControls()
        
        PopulateControls()
        
        ArrangeControls()
        
        self.Show( True )
        
        HC.pubsub.sub( self, 'RefreshServices', 'notify_new_services_gui' )
        
        wx.CallAfter( self.Raise )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _InitialiseServices( self ):
        
        self._local_listbook.DeleteAllPages()
        self._remote_listbook.DeleteAllPages()
        
        listbook_dict = {}
        
        services = HC.app.GetManager( 'services' ).GetServices()
        
        for service in services:
            
            service_type = service.GetServiceType()
            
            if service_type in HC.LOCAL_SERVICES: parent_listbook = self._local_listbook
            else: parent_listbook = self._remote_listbook
            
            if service_type not in listbook_dict:
                
                if service_type == HC.TAG_REPOSITORY: name = 'tag repositories'
                elif service_type == HC.FILE_REPOSITORY: name = 'file repositories'
                elif service_type == HC.MESSAGE_DEPOT: name = 'message depots'
                elif service_type == HC.SERVER_ADMIN: name = 'administrative servers'
                elif service_type == HC.LOCAL_FILE: name = 'files'
                elif service_type == HC.LOCAL_TAG: name = 'tags'
                elif service_type == HC.LOCAL_RATING_LIKE: name = 'like/dislike ratings'
                elif service_type == HC.LOCAL_RATING_NUMERICAL: name = 'numerical ratings'
                elif service_type == HC.LOCAL_BOORU: name = 'booru'
                else: continue
                
                listbook = ClientGUICommon.ListBook( parent_listbook )
                
                listbook_dict[ service_type ] = listbook
                
                parent_listbook.AddPage( listbook, name )
                
            
            listbook = listbook_dict[ service_type ]
            
            page_info = ( self._Panel, [ listbook, service.GetServiceKey() ], {} )
            
            name = service.GetName()
            
            listbook.AddPage( page_info, name )
            
        
        wx.CallAfter( self._local_listbook.Layout )
        wx.CallAfter( self._remote_listbook.Layout )
        
    
    def EventEdit( self, event ):
        
        original_pause_status = HC.options[ 'pause_repo_sync' ]
        
        HC.options[ 'pause_repo_sync' ] = True
        
        try:
            
            with ClientGUIDialogsManage.DialogManageServices( self ) as dlg: dlg.ShowModal()
            
        except: wx.MessageBox( traceback.format_exc() )
        
        HC.options[ 'pause_repo_sync' ] = original_pause_status
        
    
    def EventOk( self, event ): self.Close()
    
    def RefreshServices( self ): self._InitialiseServices()
    
    class _Panel( wx.ScrolledWindow ):
        
        def __init__( self, parent, service_key ):
            
            def InitialiseControls():
                
                if service_type in HC.REPOSITORIES + HC.LOCAL_SERVICES:
                    
                    self._info_panel = ClientGUICommon.StaticBox( self, 'service information' )
                    
                    if service_type in ( HC.LOCAL_FILE, HC.FILE_REPOSITORY ): 
                        
                        self._files_text = wx.StaticText( self._info_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                        
                        self._deleted_files_text = wx.StaticText( self._info_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                        
                        if service_type == HC.FILE_REPOSITORY:
                            
                            self._num_thumbs = 0
                            self._num_local_thumbs = 0
                            
                            self._thumbnails = ClientGUICommon.Gauge( self._info_panel )
                            
                            self._thumbnails_text = wx.StaticText( self._info_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                            
                        
                    elif service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ):
                        
                        self._tags_text = wx.StaticText( self._info_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                        
                        if service_type == HC.TAG_REPOSITORY:
                            
                            self._deleted_tags_text = wx.StaticText( self._info_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                            
                        
                    elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                        
                        self._ratings_text = wx.StaticText( self._info_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                        
                    elif service_type == HC.LOCAL_BOORU:
                        
                        self._num_shares = wx.StaticText( self._info_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                        
                        self._bytes = ClientGUICommon.Gauge( self._info_panel )
                        
                        self._bytes_text = wx.StaticText( self._info_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                        
                    
                
                if service_type in HC.RESTRICTED_SERVICES:
                    
                    self._permissions_panel = ClientGUICommon.StaticBox( self, 'service permissions' )
                    
                    self._account_type = wx.StaticText( self._permissions_panel, style = wx.ALIGN_CENTER )
                    
                    self._age = ClientGUICommon.Gauge( self._permissions_panel )
                    
                    self._age_text = wx.StaticText( self._permissions_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                    
                    self._bytes = ClientGUICommon.Gauge( self._permissions_panel )
                    
                    self._bytes_text = wx.StaticText( self._permissions_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                    
                    self._requests = ClientGUICommon.Gauge( self._permissions_panel )
                    
                    self._requests_text = wx.StaticText( self._permissions_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                    
                
                if service_type in HC.REPOSITORIES:
                    
                    self._synchro_panel = ClientGUICommon.StaticBox( self, 'repository synchronisation' )
                    
                    self._updates = ClientGUICommon.Gauge( self._synchro_panel )
                    
                    self._updates_text = wx.StaticText( self._synchro_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                    
                
                if service_type == HC.LOCAL_BOORU:
                    
                    self._booru_shares_panel = ClientGUICommon.StaticBox( self, 'shares' )
                    
                    self._booru_shares = ClientGUICommon.SaneListCtrl( self._booru_shares_panel, -1, [ ( 'title', 110 ), ( 'text', -1 ), ( 'expires', 170 ), ( 'num files', 70 ) ] )
                    
                    self._booru_open_search = wx.Button( self._booru_shares_panel, label = 'open share in new page' )
                    self._booru_open_search.Bind( wx.EVT_BUTTON, self.EventBooruOpenSearch )
                    
                    self._copy_internal_share_link = wx.Button( self._booru_shares_panel, label = 'copy internal share link' )
                    self._copy_internal_share_link.Bind( wx.EVT_BUTTON, self.EventCopyInternalShareURL )
                    
                    self._copy_external_share_link = wx.Button( self._booru_shares_panel, label = 'copy external share link' )
                    self._copy_external_share_link.Bind( wx.EVT_BUTTON, self.EventCopyExternalShareURL )
                    
                    self._booru_edit = wx.Button( self._booru_shares_panel, label = 'edit' )
                    self._booru_edit.Bind( wx.EVT_BUTTON, self.EventBooruEdit )
                    
                    self._booru_delete = wx.Button( self._booru_shares_panel, label = 'delete' )
                    self._booru_delete.Bind( wx.EVT_BUTTON, self.EventBooruDelete )
                    
                
                if service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ):
                    
                    self._service_wide_update = wx.Button( self, label = 'perform a service-wide operation' )
                    self._service_wide_update.Bind( wx.EVT_BUTTON, self.EventServiceWideUpdate )
                    
                
                if service_type == HC.SERVER_ADMIN:
                    
                    self._init = wx.Button( self, label = 'initialise server' )
                    self._init.Bind( wx.EVT_BUTTON, self.EventServerInitialise )
                    
                
                if service_type in HC.RESTRICTED_SERVICES:
                    
                    self._refresh = wx.Button( self, label = 'refresh account' )
                    self._refresh.Bind( wx.EVT_BUTTON, self.EventServiceRefreshAccount )
                    
                    self._copy_account_key = wx.Button( self, label = 'copy account key' )
                    self._copy_account_key.Bind( wx.EVT_BUTTON, self.EventCopyAccountKey )
                    
                
            
            def PopulateControls():
                
                self._DisplayService()
                
            
            def ArrangeControls():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                if service_type in HC.REPOSITORIES + HC.LOCAL_SERVICES:
                    
                    if service_type in ( HC.LOCAL_FILE, HC.FILE_REPOSITORY ):
                        
                        self._info_panel.AddF( self._files_text, FLAGS_EXPAND_PERPENDICULAR )
                        self._info_panel.AddF( self._deleted_files_text, FLAGS_EXPAND_PERPENDICULAR )
                        
                        if service_type == HC.FILE_REPOSITORY:
                            
                            self._info_panel.AddF( self._thumbnails, FLAGS_EXPAND_PERPENDICULAR )
                            self._info_panel.AddF( self._thumbnails_text, FLAGS_EXPAND_PERPENDICULAR )
                            
                        
                    elif service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ):
                        
                        self._info_panel.AddF( self._tags_text, FLAGS_EXPAND_PERPENDICULAR )
                        
                        if service_type == HC.TAG_REPOSITORY:
                            
                            self._info_panel.AddF( self._deleted_tags_text, FLAGS_EXPAND_PERPENDICULAR )
                            
                        
                    elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                        
                        self._info_panel.AddF( self._ratings_text, FLAGS_EXPAND_PERPENDICULAR )
                        
                    elif service_type == HC.LOCAL_BOORU:
                        
                        self._info_panel.AddF( self._num_shares, FLAGS_EXPAND_PERPENDICULAR )
                        self._info_panel.AddF( self._bytes, FLAGS_EXPAND_PERPENDICULAR )
                        self._info_panel.AddF( self._bytes_text, FLAGS_EXPAND_PERPENDICULAR )
                        
                    
                    vbox.AddF( self._info_panel, FLAGS_EXPAND_PERPENDICULAR )
                    
                
                if service_type in HC.RESTRICTED_SERVICES:
                    
                    self._permissions_panel.AddF( self._account_type, FLAGS_EXPAND_PERPENDICULAR )
                    self._permissions_panel.AddF( self._age, FLAGS_EXPAND_PERPENDICULAR )
                    self._permissions_panel.AddF( self._age_text, FLAGS_EXPAND_PERPENDICULAR )
                    self._permissions_panel.AddF( self._bytes, FLAGS_EXPAND_PERPENDICULAR )
                    self._permissions_panel.AddF( self._bytes_text, FLAGS_EXPAND_PERPENDICULAR )
                    self._permissions_panel.AddF( self._requests, FLAGS_EXPAND_PERPENDICULAR )
                    self._permissions_panel.AddF( self._requests_text, FLAGS_EXPAND_PERPENDICULAR )
                    
                    vbox.AddF( self._permissions_panel, FLAGS_EXPAND_PERPENDICULAR )
                    
                
                if service_type in HC.REPOSITORIES:
                    
                    self._synchro_panel.AddF( self._updates, FLAGS_EXPAND_PERPENDICULAR )
                    self._synchro_panel.AddF( self._updates_text, FLAGS_EXPAND_PERPENDICULAR )
                    
                    vbox.AddF( self._synchro_panel, FLAGS_EXPAND_PERPENDICULAR )
                    
                
                if service_type == HC.LOCAL_BOORU:
                    
                    self._booru_shares_panel.AddF( self._booru_shares, FLAGS_EXPAND_BOTH_WAYS )
                    
                    b_box = wx.BoxSizer( wx.HORIZONTAL )
                    b_box.AddF( self._booru_open_search, FLAGS_MIXED )
                    b_box.AddF( self._copy_internal_share_link, FLAGS_MIXED )
                    b_box.AddF( self._copy_external_share_link, FLAGS_MIXED )
                    b_box.AddF( self._booru_edit, FLAGS_MIXED )
                    b_box.AddF( self._booru_delete, FLAGS_MIXED )
                    
                    self._booru_shares_panel.AddF( b_box, FLAGS_BUTTON_SIZER )
                    
                    vbox.AddF( self._booru_shares_panel, FLAGS_EXPAND_BOTH_WAYS )
                    
                
                if service_type in HC.RESTRICTED_SERVICES + [ HC.LOCAL_TAG ]:
                    
                    repo_buttons_hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                    if service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ):
                        
                        repo_buttons_hbox.AddF( self._service_wide_update, FLAGS_MIXED )
                        
                    
                    if service_type == HC.SERVER_ADMIN:
                        
                        repo_buttons_hbox.AddF( self._init, FLAGS_MIXED )
                        
                    
                    if service_type in HC.RESTRICTED_SERVICES:
                        
                        repo_buttons_hbox.AddF( self._refresh, FLAGS_MIXED )
                        repo_buttons_hbox.AddF( self._copy_account_key, FLAGS_MIXED )
                        
                    
                    vbox.AddF( repo_buttons_hbox, FLAGS_BUTTON_SIZER )
                    
                
                self.SetSizer( vbox )
                
            
            wx.ScrolledWindow.__init__( self, parent )
            
            self.SetScrollRate( 0, 20 )
            
            self._service_key = service_key
            
            self._service = HC.app.GetManager( 'services' ).GetService( service_key )
            
            service_type = self._service.GetServiceType()
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
            
            self._timer_updates = wx.Timer( self, id = ID_TIMER_UPDATES )
            
            if service_type in HC.REPOSITORIES:
                
                self.Bind( wx.EVT_TIMER, self.TIMEREventUpdates, id = ID_TIMER_UPDATES )
                
                self._timer_updates.Start( 1000, wx.TIMER_CONTINUOUS )
                
            
            HC.pubsub.sub( self, 'ProcessServiceUpdates', 'service_updates_gui' )
            HC.pubsub.sub( self, 'AddThumbnailCount', 'add_thumbnail_count' )
            if service_type == HC.LOCAL_BOORU: HC.pubsub.sub( self, 'RefreshLocalBooruShares', 'refresh_local_booru_shares' )
            
        
        def _DisplayAccountInfo( self ):
            
            service_type = self._service.GetServiceType()
            
            now = HC.GetNow()
            
            if service_type == HC.LOCAL_BOORU:
                
                info = self._service.GetInfo()
                
                max_monthly_data = info[ 'max_monthly_data' ]
                used_monthly_data = info[ 'used_monthly_data' ]
                used_monthly_requests = info[ 'used_monthly_requests' ]
                
                if used_monthly_requests == 0: monthly_requests_text = ''
                else: monthly_requests_text = ' in ' + HC.ConvertIntToPrettyString( used_monthly_requests ) + ' requests'
                
                if max_monthly_data is None:
                    
                    self._bytes.Hide()
                    
                    self._bytes_text.SetLabel( 'used ' + HC.ConvertIntToBytes( used_monthly_data ) + monthly_requests_text + ' this month' )
                    
                else:
                    
                    self._bytes.Show()
                    
                    self._bytes.SetRange( max_monthly_data )
                    self._bytes.SetValue( used_monthly_data )
                    
                    self._bytes_text.SetLabel( 'used ' + HC.ConvertIntToBytes( used_monthly_data ) + '/' + HC.ConvertIntToBytes( max_monthly_data ) + monthly_requests_text + ' this month' )
                    
                
            
            if service_type in HC.RESTRICTED_SERVICES:
                
                account = self._service.GetInfo( 'account' )
                
                account_type = account.GetAccountType()
                
                account_type_string = account_type.ConvertToString()
                
                if self._account_type.GetLabel() != account_type_string:
                    
                    self._account_type.SetLabel( account_type_string )
                    
                    self._account_type.Wrap( 400 )
                    
                
                created = account.GetCreated()
                expires = account.GetExpires()
                
                if expires is None: self._age.Hide()
                else:
                    
                    self._age.Show()
                    
                    self._age.SetRange( expires - created )
                    self._age.SetValue( min( now - created, expires - created ) )
                    
                
                self._age_text.SetLabel( account.GetExpiresString() )
                
                max_num_bytes = account_type.GetMaxBytes()
                max_num_requests = account_type.GetMaxRequests()
                
                used_bytes = account.GetUsedBytes()
                used_requests = account.GetUsedRequests()
                
                if max_num_bytes is None: self._bytes.Hide()
                else:
                    
                    self._bytes.Show()
                    
                    self._bytes.SetRange( max_num_bytes )
                    self._bytes.SetValue( used_bytes )
                    
                
                self._bytes_text.SetLabel( account.GetUsedBytesString() )
                
                if max_num_requests is None: self._requests.Hide()
                else:
                    
                    self._requests.Show()
                    
                    self._requests.SetRange( max_num_requests )
                    self._requests.SetValue( min( used_requests, max_num_requests ) )
                    
                
                self._requests_text.SetLabel( account.GetUsedRequestsString() )
                
                if service_type in HC.REPOSITORIES:
                    
                    ( first_timestamp, next_download_timestamp, next_processing_timestamp ) = self._service.GetTimestamps()
                    
                    if first_timestamp is None:
                        
                        num_updates = 0
                        num_updates_downloaded = 0
                        
                        self._updates.SetValue( 0 )
                        
                    else:
                        
                        num_updates = ( now - first_timestamp ) / HC.UPDATE_DURATION
                        num_updates_downloaded = ( next_download_timestamp - first_timestamp ) / HC.UPDATE_DURATION
                        
                        self._updates.SetRange( num_updates )
                        self._updates.SetValue( num_updates_downloaded )
                        
                    
                    self._updates_text.SetLabel( self._service.GetUpdateStatus() )
                    
                
                self._refresh.Enable()
                
                if account.HasAccountKey(): self._copy_account_key.Enable()
                else: self._copy_account_key.Disable()
                
            
        
        def _DisplayNumThumbs( self ):
            
            self._thumbnails.SetRange( self._num_thumbs )
            self._thumbnails.SetValue( min( self._num_local_thumbs, self._num_thumbs ) )
            
            self._thumbnails_text.SetLabel( HC.ConvertIntToPrettyString( self._num_local_thumbs ) + '/' + HC.ConvertIntToPrettyString( self._num_thumbs ) + ' thumbnails downloaded' )
            
        
        def _DisplayService( self ):
            
            service_type = self._service.GetServiceType()
            
            self._DisplayAccountInfo()
            
            if service_type in HC.REPOSITORIES + HC.LOCAL_SERVICES:
                
                service_info = HC.app.Read( 'service_info', self._service_key )
                
                if service_type in ( HC.LOCAL_FILE, HC.FILE_REPOSITORY ): 
                    
                    num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
                    total_size = service_info[ HC.SERVICE_INFO_TOTAL_SIZE ]
                    num_deleted_files = service_info[ HC.SERVICE_INFO_NUM_DELETED_FILES ]
                    
                    self._files_text.SetLabel( HC.ConvertIntToPrettyString( num_files ) + ' files, totalling ' + HC.ConvertIntToBytes( total_size ) )
                    
                    self._deleted_files_text.SetLabel( HC.ConvertIntToPrettyString( num_deleted_files ) + ' deleted files' )
                    
                    if service_type == HC.FILE_REPOSITORY:
                        
                        self._num_thumbs = service_info[ HC.SERVICE_INFO_NUM_THUMBNAILS ]
                        self._num_local_thumbs = service_info[ HC.SERVICE_INFO_NUM_THUMBNAILS_LOCAL ]
                        
                        self._DisplayNumThumbs()
                        
                    
                elif service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ):
                    
                    num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
                    num_namespaces = service_info[ HC.SERVICE_INFO_NUM_NAMESPACES ]
                    num_tags = service_info[ HC.SERVICE_INFO_NUM_TAGS ]
                    num_mappings = service_info[ HC.SERVICE_INFO_NUM_MAPPINGS ]
                    
                    self._tags_text.SetLabel( HC.ConvertIntToPrettyString( num_files ) + ' hashes, ' + HC.ConvertIntToPrettyString( num_namespaces ) + ' namespaces, ' + HC.ConvertIntToPrettyString( num_tags ) + ' tags, totalling ' + HC.ConvertIntToPrettyString( num_mappings ) + ' mappings' )
                    
                    if service_type == HC.TAG_REPOSITORY:
                        
                        num_deleted_mappings = service_info[ HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ]
                        
                        self._deleted_tags_text.SetLabel( HC.ConvertIntToPrettyString( num_deleted_mappings ) + ' deleted mappings' )
                        
                    
                elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                    
                    num_ratings = service_info[ HC.SERVICE_INFO_NUM_FILES ]
                    
                    self._ratings_text.SetLabel( HC.u( num_ratings ) + ' files rated' )
                    
                elif service_type == HC.LOCAL_BOORU:
                    
                    num_shares = service_info[ HC.SERVICE_INFO_NUM_SHARES ]
                    
                    self._num_shares.SetLabel( HC.ConvertIntToPrettyString( num_shares ) + ' shares currently active' )
                    
                
            
            if service_type == HC.LOCAL_BOORU:
                
                booru_shares = HC.app.Read( 'local_booru_shares' )
                
                self._booru_shares.DeleteAllItems()
                
                for ( share_key, info ) in booru_shares.items():
                    
                    name = info[ 'name' ]
                    text = info[ 'text' ]
                    timeout = info[ 'timeout' ]
                    hashes = info[ 'hashes' ]
                    
                    self._booru_shares.Append( ( name, text, HC.ConvertTimestampToPrettyExpires( timeout ), len( hashes ) ), ( name, text, timeout, ( len( hashes ), hashes, share_key ) ) )
                    
                
            
            if service_type == HC.SERVER_ADMIN:
                
                if self._service.IsInitialised():
                    
                    self._init.Hide()
                    self._refresh.Show()
                    
                else:
                    
                    self._init.Show()
                    self._refresh.Hide()
                    
                
            
        
        def AddThumbnailCount( self, service_key, count ):
            
            if service_key == self._service_key:
                
                self._num_local_thumbs += count
                
                self._DisplayNumThumbs()
                
            
        
        def EventBooruDelete( self, event ):
            
            for ( name, text, timeout, ( num_hashes, hashes, share_key ) ) in self._booru_shares.GetSelectedClientData():
                
                HC.app.Write( 'delete_local_booru_share', share_key )
                
            
        
        def EventBooruEdit( self, event ):
            
            writes = []
            
            for ( name, text, timeout, ( num_hashes, hashes, share_key ) ) in self._booru_shares.GetSelectedClientData():
                
                with ClientGUIDialogs.DialogInputLocalBooruShare( self, share_key, name, text, timeout, hashes, new_share = False) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        ( share_key, name, text, timeout, hashes ) = dlg.GetInfo()
                        
                        info = {}
                        
                        info[ 'name' ] = name
                        info[ 'text' ] = text
                        info[ 'timeout' ] = timeout
                        info[ 'hashes' ] = hashes
                        
                        writes.append( ( share_key, info ) )
                        
                    
                
            
            for ( share_key, info ) in writes: HC.app.Write( 'local_booru_share', share_key, info )
            
        
        def EventBooruOpenSearch( self, event ):
            
            for ( name, text, timeout, ( num_hashes, hashes, share_key ) ) in self._booru_shares.GetSelectedClientData():
                
                media_results = HC.app.Read( 'media_results', HC.LOCAL_FILE_SERVICE_KEY, hashes )
                
                HC.pubsub.pub( 'new_page_query', HC.LOCAL_FILE_SERVICE_KEY, initial_media_results = media_results )
                
            
        
        def EventCopyAccountKey( self, event ):
            
            account_key = self._service.GetInfo( 'account' ).GetAccountKey()
            
            account_key_hex = account_key.encode( 'hex' )
            
            HC.pubsub.pub( 'clipboard', 'text', account_key_hex )
            
        
        def EventCopyExternalShareURL( self, event ):
            
            shares = self._booru_shares.GetSelectedClientData()
            
            if len( shares ) > 0:
                
                ( name, text, timeout, ( num_hashes, hashes, share_key ) ) = shares[0]
                
                self._service = HC.app.GetManager( 'services' ).GetService( HC.LOCAL_BOORU_SERVICE_KEY )
                
                info = self._service.GetInfo()
                
                external_ip = HydrusNATPunch.GetExternalIP() # eventually check for optional host replacement here
                
                external_port = info[ 'upnp' ]
                
                if external_port is None: external_port = info[ 'port' ]
                
                url = 'http://' + external_ip + ':' + str( external_port ) + '/gallery?share_key=' + share_key.encode( 'hex' )
                
                HC.pubsub.pub( 'clipboard', 'text', url )
                
            
        
        def EventCopyInternalShareURL( self, event ):
            
            shares = self._booru_shares.GetSelectedClientData()
            
            if len( shares ) > 0:
                
                ( name, text, timeout, ( num_hashes, hashes, share_key ) ) = shares[0]
                
                self._service = HC.app.GetManager( 'services' ).GetService( HC.LOCAL_BOORU_SERVICE_KEY )
                
                info = self._service.GetInfo()
                
                internal_ip = '127.0.0.1'
                
                internal_port = info[ 'port' ]
                
                url = 'http://' + internal_ip + ':' + str( internal_port ) + '/gallery?share_key=' + share_key.encode( 'hex' )
                
                HC.pubsub.pub( 'clipboard', 'text', url )
                
            
        
        def EventServiceWideUpdate( self, event ):
            
            with ClientGUIDialogs.DialogAdvancedContentUpdate( self, self._service_key ) as dlg:
                
                dlg.ShowModal()
                
            
        
        def EventServerInitialise( self, event ):
            
            service_key = self._service.GetServiceKey()
            service_type = self._service.GetServiceType()
            name = self._service.GetName()
            
            response = self._service.Request( HC.GET, 'init' )
            
            access_key = response[ 'access_key' ]
            
            info_update = { 'access_key' : access_key }
            
            edit_log = [ HC.EditLogActionEdit( service_key, ( service_key, service_type, name, info_update ) ) ]
            
            HC.app.Write( 'update_services', edit_log )
            
            ClientGUICommon.ShowKeys( 'access', ( access_key, ) )
            
        
        def EventServiceRefreshAccount( self, event ):
            
            self._refresh.Disable()
            
            response = self._service.Request( HC.GET, 'account' )
            
            account = response[ 'account' ]
            
            account.MakeFresh()
            
            HC.app.Write( 'service_updates', { self._service_key : [ HC.ServiceUpdate( HC.SERVICE_UPDATE_ACCOUNT, account ) ] } )
            
        
        def ProcessServiceUpdates( self, service_keys_to_service_updates ):
            
            for ( service_key, service_updates ) in service_keys_to_service_updates.items():
                
                for service_update in service_updates:
                    
                    if service_key == self._service_key:
                        
                        ( action, row ) = service_update.ToTuple()
                        
                        if action in ( HC.SERVICE_UPDATE_ACCOUNT, HC.SERVICE_UPDATE_REQUEST_MADE ): wx.CallLater( 600, self._DisplayAccountInfo )
                        else:
                            wx.CallLater( 200, self._DisplayService )
                            wx.CallLater( 400, self.Layout ) # ugly hack, but it works for now
                        
                    
                
            
        
        def RefreshLocalBooruShares( self ):
            
            self._DisplayService()
            
        
        def TIMEREventUpdates( self, event ): self._updates_text.SetLabel( self._service.GetUpdateStatus() )
        
    
class FrameSplash( ClientGUICommon.Frame ):
    
    WIDTH = 254
    HEIGHT = 220
    
    def __init__( self, action ):
        
        wx.Frame.__init__( self, None, style = wx.FRAME_NO_TASKBAR, title = 'hydrus client' )
        
        self._bmp = wx.EmptyBitmap( self.WIDTH, self.HEIGHT, 24 )
        
        self.SetSize( ( self.WIDTH, self.HEIGHT ) )
        
        self.Center()
        
        self._last_drag_coordinates = None
        self._total_drag_delta = ( 0, 0 )
        self._initial_position = self.GetPosition()
        
        # this is 124 x 166
        self._hydrus = wx.Image( HC.STATIC_DIR + os.path.sep + 'hydrus_splash.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_MOTION, self.EventDrag )
        self.Bind( wx.EVT_LEFT_DOWN, self.EventDragBegin )
        self.Bind( wx.EVT_LEFT_UP, self.EventDragEnd )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
        if action == 'boot':
            
            self.SetText( 'initialising startup' )
            
            my_thread = threading.Thread( target = self.BootApp, name = 'Application Boot Thread' )
            
        elif action == 'exit':
            
            self.SetText( 'initialising shutdown' )
            
            my_thread = threading.Thread( target = self.ExitApp, name = 'Application Boot Thread' )
            
        
        self.Show( True )
        
        HC.pubsub.sub( self, 'SetText', 'set_splash_text' )
        
        wx.CallAfter( my_thread.start )
        
    
    def BootApp( self ):
        
        try:
            
            wx.CallAfter( self.SetText, 'booting db' )
            
            HC.app.InitDB()
            
            if HC.options[ 'password' ] is not None:
                
                wx.CallAfter( self.SetText, 'waiting for password' )
                
                HC.app.InitCheckPassword()
                
            
            wx.CallAfter( self.SetText, 'booting gui' )
            
            wx.CallAfter( HC.app.InitGUI )
            
        except sqlite3.OperationalError as e:
            
            text = 'Database error!' + os.linesep * 2 + traceback.format_exc()
            
            print( text )
            
            wx.CallAfter( wx.MessageBox, text )
            
        except HydrusExceptions.PermissionException as e: pass
        except:
            
            text = 'Woah, bad error during startup!' + os.linesep * 2 + traceback.format_exc()
            
            print( text )
            
            wx.CallAfter( wx.MessageBox, text )
            
        finally:
            
            try: wx.CallAfter( self.Destroy )
            except: pass
            
        
    
    def EventDrag( self, event ):
        
        if event.Dragging() and self._last_drag_coordinates is not None:
            
            ( old_x, old_y ) = self._last_drag_coordinates
            
            ( x, y ) = event.GetPosition()
            
            ( delta_x, delta_y ) = ( x - old_x, y - old_y )
            
            ( old_delta_x, old_delta_y ) = self._total_drag_delta
            
            self._total_drag_delta = ( old_delta_x + delta_x, old_delta_y + delta_y )
            
            ( init_x, init_y ) = self._initial_position
            
            ( total_delta_x, total_delta_y ) = self._total_drag_delta
            
            self.SetPosition( ( init_x + total_delta_x, init_y + total_delta_y ) )
            
        
    
    def EventDragBegin( self, event ):
        
        self._last_drag_coordinates = event.GetPosition()
        
        event.Skip()
        
    
    def EventDragEnd( self, event ):
        
        self._last_drag_coordinates = None
        
        event.Skip()
        
    
    def EventEraseBackground( self, event ): pass
    
    def EventPaint( self, event ): wx.BufferedPaintDC( self, self._bmp )
    
    def ExitApp( self ):
        
        try:
            
            wx.CallAfter( self.SetText, 'exiting gui' )
            
            gui = HC.app.GetGUI()
            
            try: gui.TestAbleToClose()
            except: return
            
            gui.Shutdown()
            
            wx.CallAfter( self.SetText, 'exiting db' )
            
            db = HC.app.GetDB()
            
            HC.app.MaintainDB()
            
            db.Shutdown()
            
            while not db.LoopIsFinished(): time.sleep( 0.1 )
            
        except sqlite3.OperationalError as e:
            
            text = 'Database error!' + os.linesep * 2 + traceback.format_exc()
            
            print( text )
            
            wx.CallAfter( wx.MessageBox, text )
            
        except HydrusExceptions.PermissionException as e: pass
        except:
            
            text = 'Woah, bad error during shutdown!' + os.linesep * 2 + 'You may need to quit the program from task manager.' + os.linesep * 2 + traceback.format_exc()
            
            print( text )
            
            wx.CallAfter( wx.MessageBox, text )
            
        finally:
            
            try: wx.CallAfter( self.Destroy )
            except: pass
            
        
    
    def SetText( self, text ):
        
        print( text )
        
        dc = wx.BufferedDC( wx.ClientDC( self ), self._bmp )
        
        dc.SetBackground( wx.Brush( wx.WHITE ) )
        
        dc.Clear()
        
        x = ( self.WIDTH - 124 ) / 2
        
        dc.DrawBitmap( self._hydrus, x, 15 )
        
        dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
        
        ( width, height ) = dc.GetTextExtent( text )
        
        x = ( self.WIDTH - width ) / 2
        
        dc.DrawText( text, x, 200 )
        
    