import httplib
import HydrusConstants as HC
import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIDialogsManage
import ClientGUIPages
import HydrusDownloading
import HydrusFileHandling
import HydrusImageHandling
import itertools
import os
import random
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

FLAGS_BUTTON_SIZERS = wx.SizerFlags( 0 ).Align( wx.ALIGN_RIGHT )
FLAGS_LONE_BUTTON = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_RIGHT )

FLAGS_MIXED = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

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
        HC.pubsub.sub( self, 'RefreshMenuBar', 'refresh_menu_bar' )
        HC.pubsub.sub( self, 'RefreshMenuBar', 'notify_new_pending' )
        HC.pubsub.sub( self, 'RefreshMenuBar', 'notify_new_permissions' )
        HC.pubsub.sub( self, 'RefreshMenuBar', 'notify_new_services' )
        HC.pubsub.sub( self, 'RefreshAcceleratorTable', 'options_updated' )
        HC.pubsub.sub( self, 'RefreshStatusBar', 'refresh_status' )
        HC.pubsub.sub( self, 'SetDBLockedStatus', 'db_locked_status' )
        HC.pubsub.sub( self, 'SetDownloadsStatus', 'downloads_status' )
        HC.pubsub.sub( self, 'SetInboxStatus', 'inbox_status' )
        
        self.RefreshMenuBar()
        
        self._RefreshStatusBar()
        
        vbox = wx.BoxSizer( wx.HORIZONTAL )
        
        vbox.AddF( self._notebook, FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.Show( True )
        
        # as we are in oninit, callafter and calllater( 0 ) are different
        # later waits until the mainloop is running, I think.
        # after seems to execute synchronously
        
        if HC.options[ 'default_gui_session' ] == 'just a blank page':
            
            wx.CallLater( 1, self._NewPageQuery, HC.LOCAL_FILE_SERVICE_IDENTIFIER )
            
        else:
            
            name = HC.options[ 'default_gui_session' ]
            
            wx.CallLater( 1, self._LoadGUISession, name )
            
        
    
    def _THREADUploadPending( self, service_identifier ):
        
        try:
            
            job_key = HC.JobKey()
            
            HC.pubsub.pub( 'message', HC.Message( HC.MESSAGE_TYPE_GAUGE, ( job_key, True ) ) )
            
            HC.pubsub.pub( 'message_gauge_info', job_key, 1, 0, u'gathering pending and petitioned' )
            
            result = HC.app.Read( 'pending', service_identifier )
            
            service_type = service_identifier.GetType()
            
            service = HC.app.Read( 'service', service_identifier )
            
            if service_type == HC.FILE_REPOSITORY:
                
                ( upload_hashes, update ) = result
                
                media_results = HC.app.Read( 'media_results', HC.LOCAL_FILE_SERVICE_IDENTIFIER, upload_hashes )
                
                num_uploads = len( media_results )
                
                num_other_messages = 1
                
                if not update.IsEmpty(): num_other_messages += 1
                
                gauge_range = num_uploads + num_other_messages
                
                i = 1
                
                HC.pubsub.pub( 'message_gauge_info', job_key, gauge_range, i, u'connecting to repository' )
                
                good_hashes = []
                
                error_messages = set()
                
                for media_result in media_results:
                    
                    if job_key.IsCancelled(): return
                    
                    i += 1
                    
                    hash = media_result.GetHash()
                    
                    mime = media_result.GetMime()
                    
                    HC.pubsub.pub( 'message_gauge_info', job_key, gauge_range, i, u'Uploading file ' + HC.ConvertIntToPrettyString( i ) + ' of ' + HC.ConvertIntToPrettyString( num_uploads ) )
                    
                    try:
                        
                        path = CC.GetFilePath( hash, mime )
                        
                        with open( path, 'rb' ) as f: file = f.read()
                        
                        service.Request( HC.POST, 'file', { 'file' : file } )
                        
                        ( hash, inbox, size, mime, timestamp, width, height, duration, num_frames, num_words, tags_manager, file_service_identifiers_cdpp, local_ratings, remote_ratings ) = media_result.ToTuple()
                        
                        timestamp = HC.GetNow()
                        
                        content_update_row = ( hash, size, mime, timestamp, width, height, duration, num_frames, num_words )
                        
                        content_updates = [ HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_ADD, content_update_row ) ]
                        
                        service_identifiers_to_content_updates = { service_identifier : content_updates }
                        
                        HC.app.Write( 'content_updates', service_identifiers_to_content_updates )
                        
                    except Exception as e:
                        
                        HC.ShowException( e )
                        
                        time.sleep( 1 )
                        
                    
                    time.sleep( 0.1 )
                    
                    HC.app.WaitUntilGoodTimeToUseGUIThread()
                    
                
                if not update.IsEmpty():
                    
                    i += 1
                    
                    HC.pubsub.pub( 'message_gauge_info', job_key, gauge_range, i, u'uploading petitions' )
                    
                    service.Request( HC.POST, 'update', { 'update' : update } )
                    
                    content_updates = update.GetContentUpdates( for_client = True )
                    
                    service_identifiers_to_content_updates = { service_identifier : content_updates }
                    
                    HC.app.Write( 'content_updates', service_identifiers_to_content_updates )
                    
                
            elif service_type == HC.TAG_REPOSITORY:
                
                updates = result
                
                num_updates = len( updates )
                
                num_other_messages = 1
                
                gauge_range = num_updates + num_other_messages + 1
                
                i = 1
                
                HC.pubsub.pub( 'message_gauge_info', job_key, gauge_range, i, u'connecting to repository' )
                
                for update in updates:
                    
                    if job_key.IsCancelled(): return
                    
                    i += 1
                    
                    HC.pubsub.pub( 'message_gauge_info', job_key, gauge_range, i, u'posting update' )
                    
                    service.Request( HC.POST, 'update', { 'update' : update } )
                    
                    service_identifiers_to_content_updates = { service_identifier : update.GetContentUpdates( for_client = True ) }
                    
                    HC.app.Write( 'content_updates', service_identifiers_to_content_updates )
                    
                    time.sleep( 0.5 )
                    
                    HC.app.WaitUntilGoodTimeToUseGUIThread()
                    
                
            
        except Exception as e: HC.ShowException( e )
        
        HC.pubsub.pub( 'message_gauge_info', job_key, None, None, u'upload done!' )
        
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
        
    
    def _AccountInfo( self, service_identifier ):
        
        with wx.TextEntryDialog( self, 'Access key' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                subject_access_key = dlg.GetValue().decode( 'hex' )
                
                service = HC.app.Read( 'service', service_identifier )
                
                response = service.Request( HC.GET, 'account_info', { 'subject_access_key' : subject_access_key.encode( 'hex' ) } )
                
                account_info = response[ 'account_info' ]
                
                wx.MessageBox( HC.u( account_info ) )
                
            
        
    
    def _AutoRepoSetup( self ):
        
        message = 'This will attempt to set up your client with my repositories\' credentials, letting you tag on the public tag repository and see some files.'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                edit_log = []
                
                tag_repo_identifier = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.TAG_REPOSITORY, 'public tag repository' )
                
                tag_repo_info = {}
                
                tag_repo_info[ 'host' ] = 'hydrus.no-ip.org'
                tag_repo_info[ 'port' ] = 45871
                tag_repo_info[ 'access_key' ] = '4a285629721ca442541ef2c15ea17d1f7f7578b0c3f4f5f2a05f8f0ab297786f'.decode( 'hex' )
                
                edit_log.append( ( HC.ADD, ( tag_repo_identifier, tag_repo_info ) ) )
                
                file_repo_identifier = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.FILE_REPOSITORY, 'read-only art file repository' )
                
                file_repo_info = {}
                
                file_repo_info[ 'host' ] = 'hydrus.no-ip.org'
                file_repo_info[ 'port' ] = 45872
                file_repo_info[ 'access_key' ] = '8f8a3685abc19e78a92ba61d84a0482b1cfac176fd853f46d93fe437a95e40a5'.decode( 'hex' )
                
                edit_log.append( ( HC.ADD, ( file_repo_identifier, file_repo_info ) ) )
                
                HC.app.Write( 'update_services', edit_log )
                
                HC.ShowText( 'Auto repo setup done!' )
                
            
        
    
    def _AutoServerSetup( self ):
        
        host = '127.0.0.1'
        port = HC.DEFAULT_SERVER_ADMIN_PORT
        
        message = 'This will attempt to start the server in the same install directory as this client, initialise it, and store the resultant admin accounts in the client.'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                try:
                    
                    connection = httplib.HTTPConnection( '127.0.0.1', HC.DEFAULT_SERVER_ADMIN_PORT, timeout = 20 )
                    
                    connection.connect()
                    
                    connection.close()
                    
                    already_running = True
                    
                except:
                    
                    already_running = False
                    
                
                if already_running:
                    
                    message = 'The server appears to be already running. Either that, or something else is using port ' + HC.u( HC.DEFAULT_SERVER_ADMIN_PORT ) + '.' + os.linesep + 'Would you like to try to initialise the server that is already running?'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                        
                        if dlg.ShowModal() != wx.ID_YES: return
                        
                    
                else:
                    
                    try:
                        
                        my_scriptname = sys.argv[0]
                        
                        if my_scriptname.endswith( 'pyw' ): subprocess.Popen( [ 'pythonw', HC.BASE_DIR + os.path.sep + 'server.pyw' ] )
                        else:
                            
                            # The problem here is that, for mystical reasons, a PyInstaller exe can't launch another using subprocess, so we do it via explorer.
                            
                            subprocess.Popen( [ 'explorer', HC.BASE_DIR + os.path.sep + 'server.exe' ] )
                            
                        
                        time.sleep( 10 ) # give it time to init its db
                        
                    except:
                        
                        wx.MessageBox( 'I tried to start the server, but something failed!' )
                        wx.MessageBox( traceback.format_exc() )
                        
                        return
                        
                    
                
                edit_log = []
                
                admin_service_identifier = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.SERVER_ADMIN, 'local server admin' )
                
                admin_service_info = {}
                
                admin_service_info[ 'host' ] = host
                admin_service_info[ 'port' ] = port
                admin_service_info[ 'access_key' ] = ''
                
                edit_log.append( ( HC.ADD, ( admin_service_identifier, admin_service_info ) ) )
                
                HC.app.Write( 'update_services', edit_log )
                
                i = 0
                
                while True:
                    
                    time.sleep( i + 1 )
                    
                    try:
                        
                        service = HC.app.Read( 'service', admin_service_identifier )
                        
                        break
                        
                    except: pass
                    
                    i += 1
                    
                    if i > 5:
                        
                        wx.MessageBox( 'For some reason, I could not add the new server to the db! Perhaps it is very busy. Please contact the administrator, or sort it out yourself!' )
                        
                        return
                        
                    
                
                #
                
                response = service.Request( HC.GET, 'init' )
                
                access_key = response[ 'access_key' ]
                
                update = { 'access_key' : access_key }
                
                edit_log = [ ( HC.EDIT, ( admin_service_identifier, ( admin_service_identifier, update ) ) ) ]
                
                HC.app.Write( 'update_services', edit_log )
                
                ClientGUICommon.ShowKeys( 'access', ( access_key, ) )
                
                #
                
                tag_server_service_identifier = HC.ServerServiceIdentifier( os.urandom( 32 ), HC.TAG_REPOSITORY )
                
                tag_options = HC.DEFAULT_OPTIONS[ HC.TAG_REPOSITORY ]
                tag_options[ 'port' ] = HC.DEFAULT_SERVICE_PORT
                
                file_server_service_identifier = HC.ServerServiceIdentifier( os.urandom( 32 ), HC.FILE_REPOSITORY )
                
                file_options = HC.DEFAULT_OPTIONS[ HC.FILE_REPOSITORY ]
                file_options[ 'port' ] = HC.DEFAULT_SERVICE_PORT + 1
                
                edit_log = []
                
                edit_log.append( ( HC.ADD, ( tag_server_service_identifier, tag_options ) ) )
                edit_log.append( ( HC.ADD, ( file_server_service_identifier, file_options ) ) )
                
                response = service.Request( HC.POST, 'services', { 'edit_log' : edit_log } )
                
                service_identifiers_to_access_keys = dict( response[ 'service_identifiers_to_access_keys' ] )
                
                HC.app.Write( 'update_server_services', admin_service_identifier, edit_log, service_identifiers_to_access_keys )
                
                wx.MessageBox( 'Done! Check services->review services to see your new server and its services.' )
                
            
        
    
    def _BackupService( self, service_identifier ):
        
        message = 'This will tell the service to lock and copy its database files. It will probably take a few minutes to complete, and will not be able to serve any requests during that time. The GUI will lock up as well.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                service = HC.app.Read( 'service', service_identifier )
                
                with wx.BusyCursor(): service.Request( HC.POST, 'backup' )
                
                HC.ShowText( 'Backup done!' )
                
            
        
    
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
        
        self.RefreshMenuBar()
        
    
    def _DeleteAllClosedPages( self ):
        
        for ( time_closed, selection, name, page ) in self._closed_pages: self._DestroyPage( page )
        
        self._closed_pages = []
        
        self._focus_holder.SetFocus()
        
        self.RefreshMenuBar()
        
    
    def _DeletePending( self, service_identifier ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Are you sure you want to delete the pending data for ' + service_identifier.GetName() + '?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES: HC.app.Write( 'delete_pending', service_identifier )
            
        
    
    def _DestroyPage( self, page ):
        
        page.Hide()
        
        page.CleanBeforeDestroy()
        
        page.Destroy()
        
    
    def _FetchIP( self, service_identifier ):
        
        with wx.TextEntryDialog( self, 'File Hash' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                hash = dlg.GetValue().decode( 'hex' )
                
                service = HC.app.Read( 'service', service_identifier )
                
                with wx.BusyCursor(): response = service.Request( HC.GET, 'ip', { 'hash' : hash.encode( 'hex' ) } )
                
                ip = response[ 'ip' ]
                timestamp = response[ 'timestamp' ]
                
                message = 'File Hash: ' + hash.encode( 'hex' ) + os.linesep + 'Uploader\'s IP: ' + ip + os.linesep + 'Upload Time (GMT): ' + time.asctime( time.gmtime( int( timestamp ) ) )
                
                print( message )
                
                wx.MessageBox( message + os.linesep + 'This has been written to the log.' )
                
            
        
    
    def _GenerateNewAccounts( self, service_identifier ):
        
        with ClientGUIDialogs.DialogGenerateNewAccounts( self, service_identifier ) as dlg: dlg.ShowModal()
        
    
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
                            
                            service_identifier = HC.LOCAL_TAG_SERVICE_IDENTIFIER
                            
                            content_updates = []
                            current_weight = 0
                            
                            for content_update in update.IterateContentUpdates():
                                
                                content_updates.append( content_update )
                                
                                current_weight += len( content_update.GetHashes() )
                                
                                if current_weight > 50:
                                    
                                    HC.app.WriteSynchronous( 'content_updates', { service_identifier : content_updates } )
                                    
                                    content_updates = []
                                    current_weight = 0
                                    
                                
                            
                            if len( content_updates ) > 0: HC.app.WriteSynchronous( 'content_updates', { service_identifier : content_updates } )
                            
                        
                    except Exception as e: HC.ShowException( e )
                    
                
        
    
    def _LoadGUISession( self, name ):
        
        names_to_info = HC.app.Read( 'gui_sessions' )
        
        if name not in names_to_info: self._NewPageQuery( HC.LOCAL_FILE_SERVICE_IDENTIFIER )
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
                    
                except: pass
                
            
            if HC.PLATFORM_OSX: self._ClosePage( 0 )
            
        
    
    def _Manage4chanPass( self ):
        
        with ClientGUIDialogsManage.DialogManage4chanPass( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageAccountTypes( self, service_identifier ):
        
        with ClientGUIDialogsManage.DialogManageAccountTypes( self, service_identifier ) as dlg: dlg.ShowModal()
        
    
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
        
    
    def _ManageNamespaceBlacklists( self ):
        
        with ClientGUIDialogsManage.DialogManageNamespaceBlacklists( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageOptions( self ):
        
        with ClientGUIDialogsManage.DialogManageOptions( self ) as dlg: dlg.ShowModal()
        
    
    def _ManagePixivAccount( self ):
        
        with ClientGUIDialogsManage.DialogManagePixivAccount( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageServer( self, service_identifier ):
        
        with ClientGUIDialogsManage.DialogManageServer( self, service_identifier ) as dlg: dlg.ShowModal()
        
    
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
        
    
    def _ManageTagParents( self ):
        
        with ClientGUIDialogsManage.DialogManageTagParents( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageTagServicePrecedence( self ):
        
        with ClientGUIDialogsManage.DialogManageTagServicePrecedence( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageTagSiblings( self ):
        
        with ClientGUIDialogsManage.DialogManageTagSiblings( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageUPnP( self, service_identifier ):
        
        with ClientGUIDialogsManage.DialogManageUPnP( self, service_identifier ) as dlg: dlg.ShowModal()
        
    
    def _ModifyAccount( self, service_identifier ):
        
        service = HC.app.Read( 'service', service_identifier )
        
        with wx.TextEntryDialog( self, 'Enter the access key for the account to be modified' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try: access_key = dlg.GetValue().decode( 'hex' )
                except:
                    
                    wx.MessageBox( 'Could not parse that access key' )
                    
                    return
                    
                
                subject_identifiers = ( HC.AccountIdentifier( access_key = access_key ), )
                
                with ClientGUIDialogs.DialogModifyAccounts( self, service_identifier, subject_identifiers ) as dlg2: dlg2.ShowModal()
                
            
        
    
    def _NewPageImportBooru( self ):

        with ClientGUIDialogs.DialogSelectBooru( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                booru = dlg.GetBooru()
                
                self._NewPageImportGallery( 'booru', booru )
                
            
        
    
    def _NewPageImportGallery( self, name, type ):
        
        new_page = ClientGUIPages.PageImportGallery( self._notebook, name, type )
        
        if name == 'booru': page_name = type.GetName()
        elif type is None: page_name = name
        else: page_name = name + ' by ' + type
        
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
        
    
    def _NewPageLog( self ):
        
        new_page = ClientGUIPages.PageLog( self._notebook )
        
        self._notebook.AddPage( new_page, 'log', select = True )
        
        self._notebook.SetSelection( self._notebook.GetPageCount() - 1 )
        
    
    def _NewPagePetitions( self, service_identifier = None ):
        
        if service_identifier is None: service_identifier = ClientGUIDialogs.SelectServiceIdentifier( service_types = HC.REPOSITORIES, permission = HC.RESOLVE_PETITIONS )
        
        if service_identifier is not None:
            
            service = HC.app.Read( 'service', service_identifier )
            
            account = service.GetAccount()
            
            if not account.HasPermission( HC.RESOLVE_PETITIONS ): return
            
            self._notebook.AddPage( ClientGUIPages.PagePetitions( self._notebook, service_identifier ), service_identifier.GetName() + ' petitions', select = True )
            
        
    
    def _NewPageQuery( self, service_identifier, initial_media_results = [], initial_predicates = [] ):
        
        if service_identifier is None: service_identifier = ClientGUIDialogs.SelectServiceIdentifier( service_types = ( HC.FILE_REPOSITORY, ) )
        
        if service_identifier is not None:
            
            new_page = ClientGUIPages.PageQuery( self._notebook, service_identifier, initial_media_results = initial_media_results, initial_predicates = initial_predicates )
            
            self._notebook.AddPage( new_page, 'files', select = True )
            
            wx.CallAfter( new_page.SetSearchFocus )
            
        
    
    def _News( self, service_identifier ):
        
        with ClientGUIDialogs.DialogNews( self, service_identifier ) as dlg: dlg.ShowModal()
        
    
    def _OpenExportFolder( self ):
        
        export_path = HC.ConvertPortablePathToAbsPath( HC.options[ 'export_path' ] )
        
        if export_path is None: wx.MessageBox( 'Export folder is missing or not set.' )
        else:
            
            export_path = os.path.normpath( export_path ) # windows complains about those forward slashes when launching from the command line
            
            if 'Windows' in os.environ.get( 'os' ): subprocess.Popen( [ 'explorer', export_path ] )
            else: subprocess.Popen( [ 'explorer', export_path ] )
            
        
    
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
        
        self.RefreshMenuBar()
        
    
    def _PostNews( self, service_identifier ):
        
        with wx.TextEntryDialog( self, 'Enter the news you would like to post.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                news = dlg.GetValue()
                
                service = HC.app.Read( 'service', service_identifier )
                
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
        
        message = 'This will rebuild all your thumbnails from the original files. Only do this if you experience thumbnail errors. If you have a large database, it will take some time. A popup message will appear when it is done.'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                def do_it():
                    
                    job_key = HC.JobKey()
                    
                    HC.pubsub.pub( 'message', HC.Message( HC.MESSAGE_TYPE_GAUGE, ( job_key, False ) ) )
                    
                    HC.pubsub.pub( 'message_gauge_info', job_key, None, 0, 'regenerating thumbnails - creating directories' )
                    
                    if not os.path.exists( HC.CLIENT_THUMBNAILS_DIR ): os.mkdir( HC.CLIENT_THUMBNAILS_DIR )
                    
                    hex_chars = '0123456789abcdef'
                    
                    for ( one, two ) in itertools.product( hex_chars, hex_chars ):
                        
                        dir = HC.CLIENT_THUMBNAILS_DIR + os.path.sep + one + two
                        
                        if not os.path.exists( dir ): os.mkdir( dir )
                        
                    
                    i = 0
                    
                    for path in CC.IterateAllFilePaths():
                        
                        try:
                            
                            mime = HydrusFileHandling.GetMime( path )
                            
                            if mime in HC.MIMES_WITH_THUMBNAILS:
                                
                                if i % 100 == 0:
                                    
                                    HC.pubsub.pub( 'message_gauge_info', job_key, None, 0, 'regenerating thumbnails - ' + HC.ConvertIntToPrettyString( i ) + ' done' )
                                    
                                
                                i += 1
                                
                                ( base, filename ) = os.path.split( path )
                                
                                ( hash_encoded, ext ) = filename.split( '.', 1 )
                                
                                hash = hash_encoded.decode( 'hex' )
                                
                                thumbnail = HydrusImageHandling.GenerateThumbnail( path )
                                
                                thumbnail_path = CC.GetExpectedThumbnailPath( hash, True )
                                
                                with open( thumbnail_path, 'wb' ) as f: f.write( thumbnail )
                                
                                thumbnail_resized = HydrusImageHandling.GenerateThumbnail( thumbnail_path, HC.options[ 'thumbnail_dimensions' ] )
                                
                                thumbnail_resized_path = CC.GetExpectedThumbnailPath( hash, False )
                                
                                with open( thumbnail_resized_path, 'wb' ) as f: f.write( thumbnail_resized )
                                
                            
                            if HC.shutdown: return
                            
                        except: continue
                        
                    
                    HC.pubsub.pub( 'message_gauge_info', job_key, None, None, 'regenerating thumbnails - done' )
                    
                
                threading.Thread( target = do_it ).start()
                
            
        
    
    def _ReviewServices( self ):
        
        try: FrameReviewServices()
        except: wx.MessageBox( traceback.format_exc() )
        
    
    def _SaveGUISession( self, name = None ):
        
        if name is None:
            
            while True:
                
                with wx.TextEntryDialog( self, 'enter a name for the new session', 'name session' ) as dlg:
                    
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
        
        HC.pubsub.pub( 'refresh_menu_bar' )
        
    
    def _SetPassword( self ):
        
        message = '''You can set a password to be asked for whenever the client starts.

Though not foolproof, it will stop noobs from easily seeing your files if you leave your machine unattended.

Do not ever forget your password! If you do, you'll have to manually insert a yaml-dumped python dictionary into a sqlite database or recompile from source to regain easy access. This is not trivial.

The password is cleartext here but obscured in the entry dialog. Enter a blank password to remove.'''
        
        with wx.TextEntryDialog( self, message, 'Enter new password' ) as dlg:
            
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
        
        with wx.TextEntryDialog( self, 'Enter URL' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_OK:
                
                url = dlg.GetValue()
                
                job_key = HC.JobKey()
                
                message_string = url
                
                threading.Thread( target = HydrusDownloading.THREADDownloadURL, args = ( job_key, url, message_string ) ).start()
                
                HC.pubsub.pub( 'message', HC.Message( HC.MESSAGE_TYPE_GAUGE, ( job_key, True ) ) )
                
            
        
    
    def _StartYoutubeDownload( self ):
        
        with wx.TextEntryDialog( self, 'Enter YouTube URL' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_OK:
                
                url = dlg.GetValue()
                
                info = HydrusDownloading.GetYoutubeFormats( url )
                
                with ClientGUIDialogs.DialogSelectYoutubeURL( self, info ) as select_dlg: select_dlg.ShowModal()
                
            
        
    
    def _Stats( self, service_identifier ):
        
        service = HC.app.Read( 'service', service_identifier )
        
        response = service.Request( HC.GET, 'stats' )
        
        stats = response[ 'stats' ]
        
        wx.MessageBox( HC.u( stats ) )
        
    
    def _UnclosePage( self, closed_page_index ):
        
        ( time_closed, index, name, page ) = self._closed_pages.pop( closed_page_index )
        
        page.Resume()
        
        page.Show()
        
        index = min( index, self._notebook.GetPageCount() )
        
        self._notebook.InsertPage( index, page, name, True )
        
        self.RefreshMenuBar()
        
    
    def _UploadPending( self, service_identifier ):
        
        threading.Thread( target = self._THREADUploadPending, args = ( service_identifier, ) ).start()
        
    
    def _VacuumDatabase( self ):
        
        message = 'This will rebuild the database, rewriting all indices and tables to be contiguous, optimising most operations. If you have a large database, it will take some time. A popup message will appear when it is done.'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
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
        
        if len( old_closed_pages ) != len( new_closed_pages ): self.RefreshMenuBar()
        
    
    def DoFirstStart( self ):
        
        with ClientGUIDialogs.DialogFirstStart( self ) as dlg: dlg.ShowModal()
        
    
    def EventExit( self, event ):
        
        if HC.options[ 'confirm_client_exit' ]:
            
            message = 'Are you sure you want to exit the client? (Will auto-yes in 15 seconds)'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                call_later = wx.CallLater( 15000, dlg.EndModal, wx.ID_YES )
                
                if dlg.ShowModal() == wx.ID_NO:
                    
                    call_later.Stop()
                    
                    return
                    
                
                call_later.Stop()
                
            
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None:
            
            ( HC.options[ 'hpos' ], HC.options[ 'vpos' ] ) = page.GetSashPositions()
            
        
        HC.app.Write( 'save_options' )
        
        self._SaveGUISession( 'last session' )
        
        for page in [ self._notebook.GetPage( i ) for i in range( self._notebook.GetPageCount() ) ]:
            
            try: page.TestAbleToClose()
            except Exception as e: return
            
        
        for page in [ self._notebook.GetPage( i ) for i in range( self._notebook.GetPageCount() ) ]:
            
            try: page.CleanBeforeDestroy()
            except: return
            
        
        self._message_manager.CleanBeforeDestroy()
        self._message_manager.Hide()
        
        self.Hide()
        
        # for some insane reason, the read makes the controller block until the writes are done!??!
            # hence the hide, to make it appear the destroy is actually happening on time
        
        HC.app.MaintainDB()
        
        self.Destroy()
        
    
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
                
                HC.pubsub.pub( 'refresh_menu_bar' )
                
            elif command == 'delete_pending': self._DeletePending( data )
            elif command == 'exit': self.EventExit( event )
            elif command == 'fetch_ip': self._FetchIP( data )
            elif command == 'forum': webbrowser.open( 'http://hydrus.x10.mx/forum' )
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
            elif command == 'manage_namespace_blacklists': self._ManageNamespaceBlacklists()
            elif command == 'manage_pixiv_account': self._ManagePixivAccount()
            elif command == 'manage_server_services': self._ManageServer( data )
            elif command == 'manage_services': self._ManageServices()
            elif command == 'manage_subscriptions': self._ManageSubscriptions()
            elif command == 'manage_tag_parents': self._ManageTagParents()
            elif command == 'manage_tag_service_precedence': self._ManageTagServicePrecedence()
            elif command == 'manage_tag_siblings': self._ManageTagSiblings()
            elif command == 'manage_upnp': self._ManageUPnP( data )
            elif command == 'modify_account': self._ModifyAccount( data )
            elif command == 'new_accounts': self._GenerateNewAccounts( data )
            elif command == 'new_import_booru': self._NewPageImportBooru()
            elif command == 'new_import_thread_watcher': self._NewPageImportThreadWatcher()
            elif command == 'new_import_url': self._NewPageImportURL()
            elif command == 'new_log_page': self._NewPageLog()
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
        
    
    def NewPageImportGallery( self, gallery_name, gallery_type ): self._NewPageImportGallery( gallery_name, gallery_type )
    
    def NewPageImportHDD( self, paths_info, advanced_import_options = {}, paths_to_tags = {}, delete_after_success = False ):
        
        new_page = ClientGUIPages.PageImportHDD( self._notebook, paths_info, advanced_import_options = advanced_import_options, paths_to_tags = paths_to_tags, delete_after_success = delete_after_success )
        
        self._notebook.AddPage( new_page, 'import', select = True )
        
        self._notebook.SetSelection( self._notebook.GetPageCount() - 1 )
        
    
    def NewPageImportThreadWatcher( self ): self._NewPageImportThreadWatcher()
    
    def NewPageImportURL( self ): self._NewPageImportURL()
    
    def NewPagePetitions( self, service_identifier ): self._NewPagePetitions( service_identifier )
    
    def NewPageQuery( self, service_identifier, initial_media_results = [], initial_predicates = [] ): self._NewPageQuery( service_identifier, initial_media_results = initial_media_results, initial_predicates = initial_predicates )
    
    def NewPageThreadDumper( self, hashes ):
        
        with ClientGUIDialogs.DialogSelectImageboard( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                imageboard = dlg.GetImageboard()
                
                new_page = ClientGUIPages.PageThreadDumper( self._notebook, imageboard, hashes )
                
                self._notebook.AddPage( new_page, 'imageboard dumper', select = True )
                
                new_page.SetSearchFocus()
                
            
        
    
    def NewSimilarTo( self, file_service_identifier, hash ): self._NewPageQuery( file_service_identifier, initial_predicates = [ HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO, ( hash, 5 ) ), None ) ] )
    
    def RefreshAcceleratorTable( self ):
        
        interested_actions = [ 'archive', 'inbox', 'close_page', 'filter', 'ratings_filter', 'manage_ratings', 'manage_tags', 'new_page', 'refresh', 'set_media_focus', 'set_search_focus', 'show_hide_splitters', 'synchronised_wait_switch', 'undo', 'redo' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    def RefreshMenuBar( self ):
        
        p = HC.app.PrepStringForDisplay
        
        services = HC.app.Read( 'services' )
        
        tag_repositories = [ service for service in services if service.GetServiceIdentifier().GetType() == HC.TAG_REPOSITORY ]
        
        tag_service_identifiers = [ repository.GetServiceIdentifier() for repository in tag_repositories ]
        download_tag_service_identifiers = [ repository.GetServiceIdentifier() for repository in tag_repositories if repository.GetAccount().HasPermission( HC.GET_DATA ) ]
        petition_resolve_tag_service_identifiers = [ repository.GetServiceIdentifier() for repository in tag_repositories if repository.GetAccount().HasPermission( HC.RESOLVE_PETITIONS ) ]
        admin_tag_service_identifiers = [ repository.GetServiceIdentifier() for repository in tag_repositories if repository.GetAccount().HasPermission( HC.GENERAL_ADMIN ) ]
        
        file_repositories = [ service for service in services if service.GetServiceIdentifier().GetType() == HC.FILE_REPOSITORY ]
        
        file_service_identifiers = [ repository.GetServiceIdentifier() for repository in file_repositories ]
        download_file_service_identifiers = [ repository.GetServiceIdentifier() for repository in file_repositories if repository.GetAccount().HasPermission( HC.GET_DATA ) ]
        petition_resolve_file_service_identifiers = [ repository.GetServiceIdentifier() for repository in file_repositories if repository.GetAccount().HasPermission( HC.RESOLVE_PETITIONS ) ]
        admin_file_service_identifiers = [ repository.GetServiceIdentifier() for repository in file_repositories if repository.GetAccount().HasPermission( HC.GENERAL_ADMIN ) ]
        
        message_depots = [ service for service in services if service.GetServiceIdentifier().GetType() == HC.MESSAGE_DEPOT ]
        
        admin_message_depots = [ message_depot.GetServiceIdentifier() for message_depot in message_depots if message_depot.GetAccount().HasPermission( HC.GENERAL_ADMIN ) ]
        
        servers_admin = [ service for service in services if service.GetServiceIdentifier().GetType() == HC.SERVER_ADMIN ]
        
        server_admin_identifiers = [ service.GetServiceIdentifier() for service in servers_admin if service.GetAccount().HasPermission( HC.GENERAL_ADMIN ) ]
        
        menu = wx.MenuBar()
        
        file = wx.Menu()
        file.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'import_files' ), p( '&Import Files' ), p( 'Add new files to the database.' ) )
        file.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'import_metadata' ), p( '&Import Metadata' ), p( 'Add YAML metadata.' ) )
        file.AppendSeparator()
        file.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_import_folders' ), p( 'Manage Import Folders' ), p( 'Manage folders from which the client can automatically import.' ) )
        file.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_export_folders' ), p( 'Manage Export Folders' ), p( 'Manage folders to which the client can automatically export.' ) )
        file.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'open_export_folder' ), p( 'Open Quick E&xport Folder' ), p( 'Open the export folder so you can easily access the files you have exported.' ) )
        file.AppendSeparator()
        
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
            
        
        file.AppendMenu( CC.ID_NULL, p( 'Sessions' ), sessions )
        
        file.AppendSeparator()
        file.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'options' ), p( '&Options' ) )
        file.AppendSeparator()
        file.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'exit' ), p( '&Exit' ) )
        
        menu.Append( file, p( '&File' ) )
        
        have_closed_pages = len( self._closed_pages ) > 0
        
        undo_manager = HC.app.GetManager( 'undo' )
        
        ( undo_string, redo_string ) = undo_manager.GetUndoRedoStrings()
        
        have_undo_stuff = undo_string is not None or redo_string is not None
        
        if have_closed_pages or have_undo_stuff:
            
            undo = wx.Menu()
            
            did_undo_stuff = False
            
            if undo_string is not None:
                
                did_undo_stuff = True
                
                undo.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'undo' ), undo_string )
                
            
            if redo_string is not None:
                
                did_undo_stuff = True
                
                undo.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'redo' ), redo_string )
                
            
            if have_closed_pages:
                
                if did_undo_stuff: undo.AppendSeparator()
                
                undo_pages = wx.Menu()
                
                undo_pages.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'delete_all_closed_pages' ), 'clear all' )
                
                undo_pages.AppendSeparator()
                
                args = []
                
                for ( i, ( time_closed, index, name, page ) ) in enumerate( self._closed_pages ):
                    
                    args.append( ( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'unclose_page', i ), name + ' - ' + page.GetPrettyStatus() ) )
                    
                
                args.reverse() # so that recently closed are at the top
                
                for a in args: undo_pages.Append( *a )
                
                undo.AppendMenu( CC.ID_NULL, p( 'Closed Pages' ), undo_pages )
                
            
            menu.Append( undo, p( '&Undo' ) )
            
        
        view = wx.Menu()
        view.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'refresh' ), p( '&Refresh' ), p( 'Refresh the current view.' ) )
        view.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'show_hide_splitters' ), p( 'Show/Hide Splitters' ), p( 'Show or hide the current page\'s splitters.' ) )
        view.AppendSeparator()
        view.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_page' ), p( 'Pick a New &Page' ), p( 'Pick a new page.' ) )
        view.AppendSeparator()
        view.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_page_query', HC.LOCAL_FILE_SERVICE_IDENTIFIER ), p( '&New Local Search' ), p( 'Open a new search tab for your files' ) )
        for s_i in file_service_identifiers: view.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_page_query', s_i ), p( 'New ' + s_i.GetName() + ' Search' ), p( 'Open a new search tab for ' + s_i.GetName() + '.' ) )
        if len( petition_resolve_tag_service_identifiers ) > 0 or len( petition_resolve_file_service_identifiers ) > 0:
            
            view.AppendSeparator()
            for s_i in petition_resolve_tag_service_identifiers: view.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'petitions', s_i ), p( s_i.GetName() + ' Petitions' ), p( 'Open a petition tab for ' + s_i.GetName() ) )
            for s_i in petition_resolve_file_service_identifiers: view.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'petitions', s_i ), p( s_i.GetName() + ' Petitions' ), p( 'Open a petition tab for ' + s_i.GetName() ) )
            
        view.AppendSeparator()
        view.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_import_url' ), p( '&New URL Download Page' ), p( 'Open a new tab to download files from galleries or threads.' ) )
        view.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_import_booru' ), p( '&New Booru Download Page' ), p( 'Open a new tab to download files from a booru.' ) )
        view.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_import_thread_watcher' ), p( '&New Thread Watcher Page' ), p( 'Open a new tab to watch a thread.' ) )
        view.AppendSeparator()
        view.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_log_page' ), p( '&New Log Page' ), p( 'Open a new tab to show recently logged events.' ) )
        
        menu.Append( view, p( '&View' ) )
        
        download = wx.Menu()
        download.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'start_youtube_download' ), p( '&A YouTube Video' ), p( 'Enter a YouTube URL and choose which formats you would like to download' ) )
        download.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'start_url_download' ), p( '&A Raw URL' ), p( 'Enter a normal URL and attempt to import whatever is returned' ) )
        
        menu.Append( download, p( 'Do&wnload' ) )
        
        database = wx.Menu()
        database.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'set_password' ), p( 'Set a &Password' ), p( 'Set a password for the database so only you can access it.' ) )
        database.AppendSeparator()
        database.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'backup_database' ), p( 'Create Database Backup' ), p( 'Back the database up to an external location.' ) )
        database.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'restore_database' ), p( 'Restore Database Backup' ), p( 'Restore the database from an external location.' ) )
        database.AppendSeparator()
        database.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'vacuum_db' ), p( '&Vacuum' ), p( 'Rebuild the Database.' ) )
        database.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'regenerate_thumbnails' ), p( '&Regenerate All Thumbnails' ), p( 'Delete all thumbnails and regenerate from original files.' ) )
        database.AppendSeparator()
        database.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'clear_caches' ), p( '&Clear Caches' ), p( 'Fully clear the fullscreen, preview and thumbnail caches.' ) )
        
        menu.Append( database, p( '&Database' ) )
        
        nums_pending = HC.app.Read( 'nums_pending' )
        
        pending = wx.Menu()
        
        total_num_pending = 0
        
        for ( service_identifier, info ) in nums_pending.items():
            
            service_type = service_identifier.GetType()
            
            if service_type == HC.TAG_REPOSITORY:
                
                num_pending = info[ HC.SERVICE_INFO_NUM_PENDING_MAPPINGS ] + info[ HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS ] + info[ HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS ]
                num_petitioned = info[ HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS ] + info[ HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS ] + info[ HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS ]
                
            elif service_type == HC.FILE_REPOSITORY:
                
                num_pending = info[ HC.SERVICE_INFO_NUM_PENDING_FILES ]
                num_petitioned = info[ HC.SERVICE_INFO_NUM_PETITIONED_FILES ]
                
            
            if num_pending + num_petitioned > 0:
                
                submenu = wx.Menu()
                
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'upload_pending', service_identifier ), p( '&Upload' ), p( 'Upload ' + service_identifier.GetName() + '\'s Pending and Petitions.' ) )
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'delete_pending', service_identifier ), p( '&Forget' ), p( 'Clear ' + service_identifier.GetName() + '\'s Pending and Petitions.' ) )
                
                pending.AppendMenu( CC.ID_NULL, p( service_identifier.GetName() + ' Pending (' + HC.ConvertIntToPrettyString( num_pending ) + '/' + HC.ConvertIntToPrettyString( num_petitioned ) + ')' ), submenu )
                
            
            total_num_pending += num_pending + num_petitioned
            
        
        if total_num_pending > 0: menu.Append( pending, p( '&Pending (' + HC.ConvertIntToPrettyString( total_num_pending ) + ')' ) )
        else: pending.Destroy()
        
        services = wx.Menu()
        
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
        
        services.AppendMenu( CC.ID_NULL, p( 'Pause' ), submenu )
        
        services.AppendSeparator()
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'review_services' ), p( '&Review Services' ), p( 'Review your services.' ) )
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_services' ), p( '&Add, Remove or Edit Services' ), p( 'Edit your services.' ) )
        services.AppendSeparator()
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_tag_siblings' ), p( '&Manage Tag Siblings' ), p( 'Set certain tags to be automatically replaced with other tags.' ) )
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_tag_parents' ), p( '&Manage Tag Parents' ), p( 'Set certain tags to be automatically added with other tags.' ) )
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_namespace_blacklists' ), p( '&Manage Namespace Blacklists' ), p( 'Set which kinds of tags you want to see from which services.' ) )
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_tag_service_precedence' ), p( '&Manage Tag Service Precedence' ), p( 'Change the order in which tag repositories\' taxonomies will be added to the database.' ) )
        services.AppendSeparator()
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_boorus' ), p( 'Manage &Boorus' ), p( 'Change the html parsing information for boorus to download from.' ) )
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_imageboards' ), p( 'Manage &Imageboards' ), p( 'Change the html POST form information for imageboards to dump to.' ) )
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_4chan_pass' ), p( 'Manage &4chan Pass' ), p( 'Set up your 4chan pass, so you can dump without having to fill in a captcha.' ) )
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_pixiv_account' ), p( 'Manage &Pixiv Account' ), p( 'Set up your pixiv username and password.' ) )
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_subscriptions' ), p( 'Manage &Subscriptions' ), p( 'Change the queries you want the client to regularly import from.' ) )
        services.AppendSeparator()
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_upnp', HC.LOCAL_FILE_SERVICE_IDENTIFIER ), p( 'Manage Local UPnP' ) )
        services.AppendSeparator()
        submenu = wx.Menu()
        for s_i in tag_service_identifiers: submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'news', s_i ), p( s_i.GetName() ), p( 'Review ' + s_i.GetName() + '\'s past news.' ) )
        for s_i in file_service_identifiers: submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'news', s_i ), p( s_i.GetName() ), p( 'Review ' + s_i.GetName() + '\'s past news.' ) )
        services.AppendMenu( CC.ID_NULL, p( 'News' ), submenu )
        
        menu.Append( services, p( '&Services' ) )
        
        if len( admin_tag_service_identifiers ) > 0 or len( admin_file_service_identifiers ) > 0 or len( server_admin_identifiers ) > 0:
            
            admin = wx.Menu()
            
            for s_i in admin_tag_service_identifiers:
                
                submenu = wx.Menu()
                
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_accounts', s_i ), p( 'Create New &Accounts' ), p( 'Create new accounts.' ) )
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_account_types', s_i ), p( '&Manage Account Types' ), p( 'Add, edit and delete account types for the tag repository.' ) )
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'modify_account', s_i ), p( '&Modify an Account' ), p( 'Modify a specific account\'s type and expiration.' ) )
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'account_info', s_i ), p( '&Get an Account\'s Info' ), p( 'Fetch information about an account from the tag repository.' ) )
                submenu.AppendSeparator()
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'stats', s_i ), p( '&Get Stats' ), p( 'Fetch operating statistics from the tag repository.' ) )
                submenu.AppendSeparator()
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'post_news', s_i ), p( '&Post News' ), p( 'Post a news item to the tag repository.' ) )
                
                admin.AppendMenu( CC.ID_NULL, p( s_i.GetName() ), submenu )
                
            
            for s_i in admin_file_service_identifiers:
                
                submenu = wx.Menu()
                
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_accounts', s_i ), p( 'Create New &Accounts' ), p( 'Create new accounts.' ) )
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_account_types', s_i ), p( '&Manage Account Types' ), p( 'Add, edit and delete account types for the file repository.' ) )
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'modify_account', s_i ), p( '&Modify an Account' ), p( 'Modify a specific account\'s type and expiration.' ) )
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'account_info', s_i ), p( '&Get an Account\'s Info' ), p( 'Fetch information about an account from the file repository.' ) )
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'fetch_ip', s_i ), p( '&Get an Uploader\'s IP Address' ), p( 'Fetch an uploader\'s ip address.' ) )
                submenu.AppendSeparator()
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'stats', s_i ), p( '&Get Stats' ), p( 'Fetch operating statistics from the file repository.' ) )
                submenu.AppendSeparator()
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'post_news', s_i ), p( '&Post News' ), p( 'Post a news item to the file repository.' ) )
                
                admin.AppendMenu( CC.ID_NULL, p( s_i.GetName() ), submenu )
                
            
            for s_i in admin_message_depots:
                
                submenu = wx.Menu()
                
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_accounts', s_i ), p( 'Create New &Accounts' ), p( 'Create new accounts.' ) )
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_account_types', s_i ), p( '&Manage Account Types' ), p( 'Add, edit and delete account types for the file repository.' ) )
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'modify_account', s_i ), p( '&Modify an Account' ), p( 'Modify a specific account\'s type and expiration.' ) )
                
                admin.AppendMenu( CC.ID_NULL, p( s_i.GetName() ), submenu )
                
            
            for s_i in server_admin_identifiers:
                
                submenu = wx.Menu()
                
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_server_services', s_i ), p( 'Manage &Services' ), p( 'Add, edit, and delete this server\'s services.' ) )
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'backup_service', s_i ), p( 'Make a &Backup' ), p( 'Back up this server\'s database.' ) )
                
                admin.AppendMenu( CC.ID_NULL, p( s_i.GetName() ), submenu )
                
            
            menu.Append( admin, p( '&Admin' ) )
            
        
        help = wx.Menu()
        help.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'help' ), p( '&Help' ) )
        dont_know = wx.Menu()
        dont_know.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'auto_repo_setup' ), p( 'Just set up some repositories for me, please' ) )
        dont_know.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'auto_server_setup' ), p( 'Just set up the server on this computer, please' ) )
        help.AppendMenu( wx.ID_NONE, p( 'I don\'t know what I am doing' ), dont_know )
        links = wx.Menu()
        tumblr = wx.MenuItem( links, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'tumblr' ), p( 'Tumblr' ) )
        tumblr.SetBitmap( wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'tumblr.png' ) )
        twitter = wx.MenuItem( links, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'twitter' ), p( 'Twitter' ) )
        twitter.SetBitmap( wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'twitter.png' ) )
        site = wx.MenuItem( links, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'site' ), p( 'Site' ) )
        site.SetBitmap( wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'file_repository_small.png' ) )
        forum = wx.MenuItem( links, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'forum' ), p( 'Forum' ) )
        forum.SetBitmap( wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'file_repository_small.png' ) )
        links.AppendItem( tumblr )
        links.AppendItem( twitter )
        links.AppendItem( site )
        links.AppendItem( forum )
        help.AppendMenu( wx.ID_NONE, p( 'Links' ), links )
        debug = wx.Menu()
        debug.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'debug_garbage' ), p( 'Garbage' ) )
        help.AppendMenu( wx.ID_NONE, p( 'Debug' ), debug )
        help.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'help_shortcuts' ), p( '&Shortcuts' ) )
        help.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'help_about' ), p( '&About' ) )
        
        menu.Append( help, p( '&Help' ) )
        
        old_menu = self.GetMenuBar()
        
        self.SetMenuBar( menu )
        
        if old_menu is not None: old_menu.Destroy()
        
    
    def RefreshStatusBar( self ): self._RefreshStatusBar()
    
    def SetDBLockedStatus( self, status ):
        
        if self.IsShown():
            
            self._statusbar_db_locked = status
            
            self._RefreshStatusBar()
            
        
    
    def SetDownloadsStatus( self, status ):
        
        if self.IsShown():
            
            self._statusbar_downloads = status
            
            self._RefreshStatusBar()
            
        
    
    def SetInboxStatus( self, status ):
        
        if self.IsShown():
            
            self._statusbar_inbox = status
            
            self._RefreshStatusBar()
            
        
    
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
        
    
class FrameReviewServices( ClientGUICommon.Frame ):
    
    def __init__( self ):
        
        def InitialiseControls():
            
            self._listbook = ClientGUICommon.ListBook( self )
            
            self._edit = wx.Button( self, label = 'add, remove or edit services' )
            self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
            
            self._ok = wx.Button( self, label = 'ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
        
        def PopulateControls():
            
            self._InitialiseServices()
            
        
        def ArrangeControls():
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._listbook, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._edit, FLAGS_SMALL_INDENT )
            vbox.AddF( self._ok, FLAGS_BUTTON_SIZERS )
            
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
        
        HC.pubsub.sub( self, 'RefreshServices', 'notify_new_services' )
        
        wx.CallAfter( self.Raise )
        
        wx.CallAfter( self._ok.SetFocus )
        
    
    def _InitialiseServices( self ):
        
        self._listbook.DeleteAllPages()
        
        listbook_dict = {}
        
        service_identifiers = HC.app.Read( 'service_identifiers' )
        
        for service_identifier in service_identifiers:
            
            service_type = service_identifier.GetType()
            
            if service_type in ( HC.LOCAL_FILE, HC.LOCAL_TAG ):
                
                page = self._Panel( self._listbook, service_identifier )
                
                name = service_identifier.GetName()
                
                self._listbook.AddPage( page, name )
                
            else:
                
                if service_type not in listbook_dict:
                    
                    listbook = ClientGUICommon.ListBook( self._listbook )
                    
                    listbook_dict[ service_type ] = listbook
                    
                    if service_type == HC.TAG_REPOSITORY: name = 'tags'
                    elif service_type == HC.FILE_REPOSITORY: name = 'files'
                    elif service_type == HC.MESSAGE_DEPOT: name = 'message depots'
                    elif service_type == HC.SERVER_ADMIN: name = 'servers admin'
                    elif service_type == HC.LOCAL_RATING_LIKE: name = 'local ratings like'
                    elif service_type == HC.LOCAL_RATING_NUMERICAL: name = 'local ratings numerical'
                    
                    self._listbook.AddPage( listbook, name )
                    
                
                listbook = listbook_dict[ service_type ]
                
                page = ( self._Panel, [ listbook, service_identifier ], {} )
                
                name = service_identifier.GetName()
                
                listbook.AddPage( page, name )
                
            
        
        wx.CallAfter( self._listbook.Layout )
        
    
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
        
        def __init__( self, parent, service_identifier ):
            
            def InitialiseControls():
                
                if service_type in HC.RESTRICTED_SERVICES:
                    
                    self._permissions_panel = ClientGUICommon.StaticBox( self, 'service permissions' )
                    
                    self._account_type = wx.StaticText( self._permissions_panel, style = wx.ALIGN_CENTER )
                    
                    self._age = ClientGUICommon.Gauge( self._permissions_panel )
                    
                    self._age_text = wx.StaticText( self._permissions_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                    
                    ( max_num_bytes, max_num_requests ) = account_type.GetMaxMonthlyData()
                    
                    self._bytes = ClientGUICommon.Gauge( self._permissions_panel )
                    
                    self._bytes_text = wx.StaticText( self._permissions_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                    
                    self._requests = ClientGUICommon.Gauge( self._permissions_panel )
                    
                    self._requests_text = wx.StaticText( self._permissions_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                    
                    if max_num_bytes is None: self._bytes.Hide()
                    if expiry is None: self._age.Hide()
                    if max_num_requests is None: self._requests.Hide()
                    
                
                if service_type in HC.REPOSITORIES:
                    
                    self._synchro_panel = ClientGUICommon.StaticBox( self, 'repository synchronisation' )
                    
                    self._updates = ClientGUICommon.Gauge( self._synchro_panel )
                    
                    self._updates_text = wx.StaticText( self._synchro_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                    
                
                if service_type in HC.REPOSITORIES + [ HC.LOCAL_FILE, HC.LOCAL_TAG, HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ]:
                    
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
                        
                    
                
                if service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ):
                    
                    self._service_wide_update = wx.Button( self, label = 'perform a service-wide update' )
                    self._service_wide_update.Bind( wx.EVT_BUTTON, self.EventServiceWideUpdate )
                    
                
                if service_type in HC.REPOSITORIES:
                    
                    self._reset = wx.Button( self, label = 'reset cache' )
                    self._reset.Bind( wx.EVT_BUTTON, self.EventServiceReset )
                    
                
                if service_type == HC.SERVER_ADMIN:
                    
                    self._init = wx.Button( self, label = 'initialise server' )
                    self._init.Bind( wx.EVT_BUTTON, self.EventServerInitialise )
                    
                
                if service_type in HC.RESTRICTED_SERVICES:
                    
                    self._refresh = wx.Button( self, label = 'refresh account' )
                    self._refresh.Bind( wx.EVT_BUTTON, self.EventServiceRefreshAccount )
                    
                
            
            def PopulateControls():
                
                self._DisplayService()
                
            
            def ArrangeControls():
                
                self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
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
                    
                
                if service_type in HC.REPOSITORIES + [ HC.LOCAL_FILE, HC.LOCAL_TAG, HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ]:
                    
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
                        
                    
                    vbox.AddF( self._info_panel, FLAGS_EXPAND_PERPENDICULAR )
                    
                
                if service_type in HC.RESTRICTED_SERVICES + [ HC.LOCAL_TAG ]:
                    
                    repo_buttons_hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                    if service_type in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ):
                        
                        repo_buttons_hbox.AddF( self._service_wide_update, FLAGS_MIXED )
                        
                    
                    if service_type in HC.REPOSITORIES:
                        
                        repo_buttons_hbox.AddF( self._reset, FLAGS_MIXED )
                        
                    
                    if service_type == HC.SERVER_ADMIN:
                        
                        repo_buttons_hbox.AddF( self._init, FLAGS_MIXED )
                        
                    
                    if service_type in HC.RESTRICTED_SERVICES:
                        
                        repo_buttons_hbox.AddF( self._refresh, FLAGS_MIXED )
                        
                    
                    vbox.AddF( repo_buttons_hbox, FLAGS_BUTTON_SIZERS )
                    
                
                self.SetSizer( vbox )
                
            
            wx.ScrolledWindow.__init__( self, parent )
            
            self.SetScrollRate( 0, 20 )
            
            self._service_identifier = service_identifier
            
            self._service = HC.app.Read( 'service', self._service_identifier )
            
            service_type = service_identifier.GetType()
            
            if service_type in HC.RESTRICTED_SERVICES:
                
                account = self._service.GetAccount()
                
                account_type = account.GetAccountType()
                
                expiry = account.GetExpiry()
                
            
            InitialiseControls()
            
            PopulateControls()
            
            ArrangeControls()
            
            self._timer_updates = wx.Timer( self, id = ID_TIMER_UPDATES )
            
            if service_type in HC.REPOSITORIES:
                
                self.Bind( wx.EVT_TIMER, self.TIMEREventUpdates, id = ID_TIMER_UPDATES )
                
                self._timer_updates.Start( 1000, wx.TIMER_CONTINUOUS )
                
            
            HC.pubsub.sub( self, 'ProcessServiceUpdates', 'service_updates_gui' )
            HC.pubsub.sub( self, 'AddThumbnailCount', 'add_thumbnail_count' )
            
        
        def _DisplayAccountInfo( self ):
            
            self._service = HC.app.Read( 'service', self._service_identifier )
            
            service_type = self._service_identifier.GetType()
            
            now = HC.GetNow()
            
            if service_type in HC.RESTRICTED_SERVICES:
                
                account = self._service.GetAccount()
                
                account_type = account.GetAccountType()
                
                self._account_type.SetLabel( account_type.ConvertToString() )
                self._account_type.Wrap( 400 )
                
                if service_type in HC.REPOSITORIES:
                    
                    if not account.IsBanned():
                        
                        created = account.GetCreated()
                        expiry = account.GetExpiry()
                        
                        if expiry is None: self._age.Hide()
                        else:
                            
                            self._age.Show()
                            
                            self._age.SetRange( expiry - created )
                            self._age.SetValue( min( now - created, expiry - created ) )
                            
                        
                        self._age_text.SetLabel( account.GetExpiryString() )
                        
                        first_begin = self._service.GetFirstBegin()
                        next_begin = self._service.GetNextBegin()
                        
                        if first_begin == 0:
                            
                            num_updates = 0
                            num_updates_downloaded = 0
                            
                            self._updates.SetValue( 0 )
                            
                        else:
                            
                            num_updates = ( now - first_begin ) / HC.UPDATE_DURATION
                            num_updates_downloaded = ( next_begin - first_begin ) / HC.UPDATE_DURATION
                            
                            self._updates.SetRange( num_updates )
                            self._updates.SetValue( num_updates_downloaded )
                            
                        
                        self._updates_text.SetLabel( HC.ConvertIntToPrettyString( num_updates_downloaded ) + '/' + HC.ConvertIntToPrettyString( num_updates ) + ' - ' + self._service.GetUpdateStatus() )
                        
                        ( max_num_bytes, max_num_requests ) = account_type.GetMaxMonthlyData()
                        ( used_bytes, used_requests ) = account.GetUsedData()
                        
                        if max_num_bytes is None: self._bytes.Hide()
                        else:
                            
                            self._bytes.Show()
                            
                            self._bytes.SetRange( max_num_bytes )
                            self._bytes.SetValue( used_bytes )
                            
                        
                        self._bytes_text.SetLabel( account.GetUsedBytesString() )
                        
                        if max_num_requests is None: self._requests.Hide()
                        else:
                            
                            self._requests.Show()
                            
                            self._requests.SetValue( max_num_requests )
                            self._requests.SetValue( min( used_requests, max_num_requests ) )
                            
                        
                        self._requests_text.SetLabel( account.GetUsedRequestsString() )
                        
                    
                
                self._refresh.Enable()
                
            
        
        def _DisplayNumThumbs( self ):
            
            self._thumbnails.SetRange( self._num_thumbs )
            self._thumbnails.SetValue( min( self._num_local_thumbs, self._num_thumbs ) )
            
            self._thumbnails_text.SetLabel( HC.ConvertIntToPrettyString( self._num_local_thumbs ) + '/' + HC.ConvertIntToPrettyString( self._num_thumbs ) + ' thumbnails downloaded' )
            
        
        def _DisplayService( self ):
            
            service_type = self._service_identifier.GetType()
            
            self._DisplayAccountInfo()
            
            if service_type in HC.REPOSITORIES + [ HC.LOCAL_FILE, HC.LOCAL_TAG, HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ]:
                
                service_info = HC.app.Read( 'service_info', self._service_identifier )
                
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
                    
                
            
            if service_type == HC.SERVER_ADMIN:
                
                if self._service.IsInitialised():
                    
                    self._init.Disable()
                    self._refresh.Enable()
                    
                else:
                    
                    self._init.Enable()
                    self._refresh.Disable()
                    
                
            
        
        def AddThumbnailCount( self, service_identifier, count ):
            
            if service_identifier == self._service_identifier:
                
                self._num_local_thumbs += count
                
                self._DisplayNumThumbs()
                
            
        
        def EventServiceWideUpdate( self, event ):
            
            with ClientGUIDialogs.DialogAdvancedContentUpdate( self, self._service_identifier ) as dlg:
                
                dlg.ShowModal()
                
            
        
        def EventServerInitialise( self, event ):
            
            response = self._service.Request( HC.GET, 'init' )
            
            access_key = response[ 'access_key' ]
            
            update = { 'access_key' : access_key }
            
            edit_log = [ ( HC.EDIT, ( self._service_identifier, ( self._service_identifier, update ) ) ) ]
            
            HC.app.Write( 'update_services', edit_log )
            
            ClientGUICommon.ShowKeys( 'access', ( access_key, ) )
            
        
        def EventServiceRefreshAccount( self, event ):
            
            self._refresh.Disable()
            
            response = self._service.Request( HC.GET, 'account' )
            
            account = response[ 'account' ]
            
            account.MakeFresh()
            
            HC.app.Write( 'service_updates', { self._service_identifier : [ HC.ServiceUpdate( HC.SERVICE_UPDATE_ACCOUNT, account ) ] } )
            
        
        def EventServiceReset( self, event ):
            
            message = 'This will remove all cached information for ' + self._service_identifier.GetName() + ' from the database. It will take a minute for the database to finish the operation, during which time the gui may freeze.'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    with wx.BusyCursor(): HC.app.Write( 'reset_service', self._service_identifier )
                    
                
            
        
        def ProcessServiceUpdates( self, service_identifiers_to_service_updates ):
            
            for ( service_identifier, service_updates ) in service_identifiers_to_service_updates.items():
                
                for service_update in service_updates:
                    
                    if service_identifier == self._service_identifier:
                        
                        ( action, row ) = service_update.ToTuple()
                        
                        if action == HC.SERVICE_UPDATE_RESET: self._service_identifier = row
                        
                        if action in ( HC.SERVICE_UPDATE_ACCOUNT, HC.SERVICE_UPDATE_REQUEST_MADE ): wx.CallLater( 600, self._DisplayAccountInfo )
                        else:
                            wx.CallLater( 200, self._DisplayService )
                            wx.CallLater( 400, self.Layout ) # ugly hack, but it works for now
                        
                    
                
            
        
        def TIMEREventUpdates( self, event ):
            
            now = HC.GetNow()
            
            first_begin = self._service.GetFirstBegin()
            next_begin = self._service.GetNextBegin()
            
            if first_begin == 0:
                
                num_updates = 0
                num_updates_downloaded = 0
                
            else:
                
                num_updates = ( now - first_begin ) / HC.UPDATE_DURATION
                num_updates_downloaded = ( next_begin - first_begin ) / HC.UPDATE_DURATION
                
            
            self._updates_text.SetLabel( HC.ConvertIntToPrettyString( num_updates_downloaded ) + '/' + HC.ConvertIntToPrettyString( num_updates ) + ' - ' + self._service.GetUpdateStatus() )
            
        
    
class FrameSplash( ClientGUICommon.Frame ):
    
    def __init__( self ):
        
        wx.Frame.__init__( self, None, style = wx.FRAME_NO_TASKBAR | wx.FRAME_SHAPED, title = 'hydrus client' )
        
        self._bmp = wx.EmptyBitmap( 154, 220, 32 ) # 32 bit for transparency?
        
        self.SetSize( ( 154, 220 ) )
        
        self.Center()
        
        # this is 124 x 166
        self._hydrus = wx.Image( HC.STATIC_DIR + os.path.sep + 'hydrus_splash.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        
        dc = wx.BufferedDC( wx.ClientDC( self ), self._bmp )
        
        dc.SetBackground( wx.Brush( wx.WHITE ) )
        
        dc.Clear()
        
        dc.DrawBitmap( self._hydrus, 15, 15 )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        
        self.Show( True )
        
        self.Bind( wx.EVT_MOUSE_EVENTS, self.OnMouseEvents )
        
    
    def EventPaint( self, event ): wx.BufferedPaintDC( self, self._bmp )
    
    def OnMouseEvents( self, event ): pass
    
    def SetText( self, text ):
        
        dc = wx.BufferedDC( wx.ClientDC( self ), self._bmp )
        
        dc.SetBackground( wx.Brush( wx.WHITE ) )
        
        dc.Clear()
        
        dc.DrawBitmap( self._hydrus, 15, 15 )
        
        dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
        
        ( width, height ) = dc.GetTextExtent( text )
        
        x = ( 154 - width ) / 2
        
        dc.DrawText( text, x, 200 )
        
    
