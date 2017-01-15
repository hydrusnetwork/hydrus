import httplib
import HydrusConstants as HC
import ClientConstants as CC
import ClientCaches
import ClientFiles
import ClientData
import ClientDragDrop
import ClientExporting
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIDialogsManage
import ClientGUIFrames
import ClientGUIManagement
import ClientGUIMenus
import ClientGUIPages
import ClientGUIParsing
import ClientGUIScrolledPanelsManagement
import ClientGUIScrolledPanelsReview
import ClientGUITopLevelWindows
import ClientDownloading
import ClientMedia
import ClientSearch
import ClientThreading
import collections
import cv2
import gc
import HydrusData
import HydrusExceptions
import HydrusFileHandling
import HydrusPaths
import HydrusGlobals
import HydrusImageHandling
import HydrusNATPunch
import HydrusNetworking
import HydrusSerialisable
import HydrusTagArchive
import HydrusThreading
import HydrusVideoHandling
import itertools
import os
import PIL
import random
import sqlite3
import ssl
import subprocess
import sys
import threading
import time
import traceback
import types
import webbrowser
import wx
import yaml

# Sizer Flags

MENU_ORDER = [ 'file', 'undo', 'pages', 'database', 'pending', 'services', 'help' ]

class FrameGUI( ClientGUITopLevelWindows.FrameThatResizes ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        title = self._controller.GetNewOptions().GetString( 'main_gui_title' )
        
        if title is None or title == '':
            
            title = 'hydrus client'
            
        
        ClientGUITopLevelWindows.FrameThatResizes.__init__( self, None, title, 'main_gui', float_on_parent = False )
        
        self.SetDropTarget( ClientDragDrop.FileDropTarget( self.ImportFiles ) )
        
        self._statusbar = self.CreateStatusBar()
        self._statusbar.SetFieldsCount( 4 )
        self._statusbar.SetStatusWidths( [ -1, 25, 90, 50 ] )
        
        self._focus_holder = wx.Window( self, size = ( 0, 0 ) )
        
        self._loading_session = False
        self._media_status_override = None
        self._closed_pages = []
        self._deleted_page_keys = set()
        self._lock = threading.Lock()
        
        self._notebook = wx.Notebook( self )
        self._notebook.Bind( wx.EVT_LEFT_DCLICK, self.EventNotebookLeftDoubleClick )
        self._notebook.Bind( wx.EVT_MIDDLE_DOWN, self.EventNotebookMiddleClick )
        self._notebook.Bind( wx.EVT_RIGHT_DOWN, self.EventNotebookMenu )
        self.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventNotebookPageChanged )
        
        self._tab_right_click_index = -1
        
        wx.GetApp().SetTopWindow( self )
        
        self.RefreshAcceleratorTable()
        
        self._message_manager = ClientGUICommon.PopupMessageManager( self )
        
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventFrameNewPage )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventFrameNewPage )
        self.Bind( wx.EVT_CLOSE, self.EventClose )
        self.Bind( wx.EVT_MENU, self.EventMenu )
        self.Bind( wx.EVT_SET_FOCUS, self.EventFocus )
        
        self._controller.sub( self, 'ClearClosedPages', 'clear_closed_pages' )
        self._controller.sub( self, 'NewCompose', 'new_compose_frame' )
        self._controller.sub( self, 'NewPageImportBooru', 'new_import_booru' )
        self._controller.sub( self, 'NewPageImportGallery', 'new_import_gallery' )
        self._controller.sub( self, 'NewPageImportHDD', 'new_hdd_import' )
        self._controller.sub( self, 'NewPageImportPageOfImages', 'new_page_import_page_of_images' )
        self._controller.sub( self, 'NewPageImportThreadWatcher', 'new_page_import_thread_watcher' )
        self._controller.sub( self, 'NewPageImportURLs', 'new_page_import_urls' )
        self._controller.sub( self, 'NewPagePetitions', 'new_page_petitions' )
        self._controller.sub( self, 'NewPageQuery', 'new_page_query' )
        self._controller.sub( self, 'NewPageThreadDumper', 'new_thread_dumper' )
        self._controller.sub( self, 'NewSimilarTo', 'new_similar_to' )
        self._controller.sub( self, 'NotifyNewOptions', 'notify_new_options' )
        self._controller.sub( self, 'NotifyNewPending', 'notify_new_pending' )
        self._controller.sub( self, 'NotifyNewPermissions', 'notify_new_permissions' )
        self._controller.sub( self, 'NotifyNewServices', 'notify_new_services_gui' )
        self._controller.sub( self, 'NotifyNewSessions', 'notify_new_sessions' )
        self._controller.sub( self, 'NotifyNewUndo', 'notify_new_undo' )
        self._controller.sub( self, 'RefreshStatusBar', 'refresh_status' )
        self._controller.sub( self, 'SetDBLockedStatus', 'db_locked_status' )
        self._controller.sub( self, 'SetMediaFocus', 'set_media_focus' )
        self._controller.sub( self, 'SetTitle', 'main_gui_title' )
        self._controller.sub( self, 'SyncToTagArchive', 'sync_to_tag_archive' )
        
        self._menus = {}
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        ClientGUITopLevelWindows.SetTLWSizeAndPosition( self, self._frame_key )
        
        self.Show( True )
        
        self._InitialiseMenubar()
        
        self._RefreshStatusBar()
        
        default_gui_session = HC.options[ 'default_gui_session' ]
        
        existing_session_names = self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
        
        cannot_load_from_db = default_gui_session not in existing_session_names
        
        load_a_blank_page = HC.options[ 'default_gui_session' ] == 'just a blank page' or cannot_load_from_db
        
        if not load_a_blank_page:
            
            if self._controller.LastShutdownWasBad():
                
                # this can be upgraded to a nicer checkboxlist dialog to select pages or w/e
                
                message = 'It looks like the last instance of the client did not shut down cleanly.'
                message += os.linesep * 2
                message += 'Would you like to try loading your default session \'' + default_gui_session + '\', or just a blank page?'
                
                with ClientGUIDialogs.DialogYesNo( self, message, title = 'Previous shutdown was bad', yes_label = 'try to load the default session', no_label = 'just load a blank page' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_NO:
                        
                        load_a_blank_page = True
                        
                    
                
            
        
        if load_a_blank_page:
            
            self._NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY )
            
        else:
            
            self._LoadGUISession( default_gui_session )
            
        
        wx.CallLater( 5 * 60 * 1000, self.SaveLastSession )
        
    
    def _AboutWindow( self ):
        
        aboutinfo = wx.AboutDialogInfo()
        
        aboutinfo.SetIcon( wx.Icon( os.path.join( HC.STATIC_DIR, 'hydrus.ico' ), wx.BITMAP_TYPE_ICO ) )
        aboutinfo.SetName( 'hydrus client' )
        aboutinfo.SetVersion( str( HC.SOFTWARE_VERSION ) + ', using network version ' + str( HC.NETWORK_VERSION ) )
        
        library_versions = []
        
        library_versions.append( ( 'FFMPEG', HydrusVideoHandling.GetFFMPEGVersion() ) )
        library_versions.append( ( 'OpenCV', cv2.__version__ ) )
        library_versions.append( ( 'openssl', ssl.OPENSSL_VERSION ) )
        library_versions.append( ( 'PIL', PIL.VERSION ) )
        
        if hasattr( PIL, 'PILLOW_VERSION' ):
            
            library_versions.append( ( 'Pillow', PIL.PILLOW_VERSION ) )
            
        
        # 2.7.12 (v2.7.12:d33e0cf91556, Jun 27 2016, 15:24:40) [MSC v.1500 64 bit (AMD64)]
        v = sys.version
        
        if ' ' in v:
            
            v = v.split( ' ' )[0]
            
        
        library_versions.append( ( 'python', v ) )
        
        library_versions.append( ( 'sqlite', sqlite3.sqlite_version ) )
        library_versions.append( ( 'wx', wx.version() ) )
        
        description = 'This client is the media management application of the hydrus software suite.'
        
        description += os.linesep * 2 + os.linesep.join( ( lib + ': ' + version for ( lib, version ) in library_versions ) )
        
        aboutinfo.SetDescription( description )
        
        with open( os.path.join( HC.LICENSE_DIR, 'license.txt' ), 'rb' ) as f: license = f.read()
        
        aboutinfo.SetLicense( license )
        
        aboutinfo.SetDevelopers( [ 'Anonymous' ] )
        aboutinfo.SetWebSite( 'https://hydrusnetwork.github.io/hydrus/' )
        
        wx.AboutBox( aboutinfo )
        
    
    def _AccountInfo( self, service_key ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the account\'s account key.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                subject_account_key = dlg.GetValue().decode( 'hex' )
                
                service = self._controller.GetServicesManager().GetService( service_key )
                
                response = service.Request( HC.GET, 'account_info', { 'subject_account_key' : subject_account_key.encode( 'hex' ) } )
                
                account_info = response[ 'account_info' ]
                
                wx.MessageBox( HydrusData.ToUnicode( account_info ) )
                
            
        
    
    def _AnalyzeDatabase( self ):
        
        message = 'This will gather statistical information on the database\'s indices, helping the query planner perform efficiently. It typically happens automatically every few days, but you can force it here. If you have a large database, it will take a few minutes, during which your gui may hang. A popup message will show its status.'
        message += os.linesep * 2
        message += 'A \'soft\' analyze will only reanalyze those indices that are due for a check in the normal db maintenance cycle. If nothing is due, it will return immediately.'
        message += os.linesep * 2
        message += 'A \'full\' analyze will force a run over every index in the database. This can take substantially longer. If you do not have a specific reason to select this, it is probably pointless.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose how thorough your analyze will be.', yes_label = 'soft', no_label = 'full' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_YES:
                
                stop_time = HydrusData.GetNow() + 120
                
                self._controller.Write( 'analyze', stop_time = stop_time )
                
            elif result == wx.ID_NO:
                
                self._controller.Write( 'analyze', force_reanalyze = True )
                
            
        
    
    def _AutoRepoSetup( self ):
        
        def do_it():
        
            edit_log = []
            
            service_key = HydrusData.GenerateKey()
            service_type = HC.TAG_REPOSITORY
            name = 'public tag repository'
            
            info = {}
            
            info[ 'host' ] = 'hydrus.no-ip.org'
            info[ 'port' ] = 45871
            info[ 'access_key' ] = '4a285629721ca442541ef2c15ea17d1f7f7578b0c3f4f5f2a05f8f0ab297786f'.decode( 'hex' )
            
            edit_log.append( HydrusData.EditLogActionAdd( ( service_key, service_type, name, info ) ) )
            
            service_key = HydrusData.GenerateKey()
            service_type = HC.FILE_REPOSITORY
            name = 'read-only art file repository'
            
            info = {}
            
            info[ 'host' ] = 'hydrus.no-ip.org'
            info[ 'port' ] = 45872
            info[ 'access_key' ] = '8f8a3685abc19e78a92ba61d84a0482b1cfac176fd853f46d93fe437a95e40a5'.decode( 'hex' )
            
            edit_log.append( HydrusData.EditLogActionAdd( ( service_key, service_type, name, info ) ) )
            
            self._controller.WriteSynchronous( 'update_services', edit_log )
            
            HydrusData.ShowText( 'Auto repo setup done! Check services->review services to see your new services.' )
            
        
        text = 'This will attempt to set up your client with my repositories\' credentials, letting you tag on the public tag repository and see some files.'
        
        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.CallToThread( do_it )
                
            
        
    
    def _AutoServerSetup( self ):
        
        def do_it():
            
            host = '127.0.0.1'
            port = HC.DEFAULT_SERVER_ADMIN_PORT
            
            try:
                
                connection = HydrusNetworking.GetLocalConnection( port )
                connection.close()
                
                already_running = True
                
            except:
                
                already_running = False
                
            
            if already_running:
                
                HydrusData.ShowText( 'The server appears to be already running. Either that, or something else is using port ' + str( HC.DEFAULT_SERVER_ADMIN_PORT ) + '.' )
                
                return
                
            else:
                
                try:
                    
                    HydrusData.ShowText( u'Starting server\u2026' )
                    
                    if HC.PLATFORM_WINDOWS:
                        
                        server_frozen_path = os.path.join( HC.BASE_DIR, 'server.exe' )
                        
                    else:
                        
                        server_frozen_path = os.path.join( HC.BASE_DIR, 'server' )
                        
                    
                    if os.path.exists( server_frozen_path ):
                    
                        if HC.PLATFORM_WINDOWS: subprocess.Popen( [ server_frozen_path ] )
                        else: subprocess.Popen( [ server_frozen_path ] )
                        
                    else:
                        
                        python_executable = sys.executable
                        
                        if python_executable.endswith( 'client.exe' ) or python_executable.endswith( 'client' ):
                            
                            raise Exception( 'Could not automatically set up the server--could not find server executable or python executable.' )
                            
                        
                        if 'pythonw' in python_executable:
                            
                            python_executable = python_executable.replace( 'pythonw', 'python' )
                            
                        
                        subprocess.Popen( [ python_executable, os.path.join( HC.BASE_DIR, 'server.py' ) ] )
                        
                    
                    time_waited = 0
                    
                    while True:
                        
                        time.sleep( 3 )
                        
                        time_waited += 3
                        
                        try:
                            
                            connection = HydrusNetworking.GetLocalConnection( port )
                            
                            connection.close()
                            
                            break
                            
                        except:
                            
                            if time_waited > 30:
                                
                                raise
                                
                            
                        
                    
                except:
                    
                    HydrusData.ShowText( 'I tried to start the server, but something failed!' + os.linesep + traceback.format_exc() )
                    
                    return
                    
                
            
            time.sleep( 5 )
            
            HydrusData.ShowText( u'Creating admin service\u2026' )
            
            admin_service_key = HydrusData.GenerateKey()
            service_type = HC.SERVER_ADMIN
            name = 'local server admin'
            
            info = {}
            
            info[ 'host' ] = host
            info[ 'port' ] = port
            
            service = ClientData.GenerateService( admin_service_key, service_type, name, info )
            
            response = service.Request( HC.GET, 'init' )
            
            access_key = response[ 'access_key' ]
            
            #
            
            info[ 'access_key' ] = access_key
            
            edit_log = [ HydrusData.EditLogActionAdd( ( admin_service_key, service_type, name, info ) ) ]
            
            self._controller.WriteSynchronous( 'update_services', edit_log )
            
            HydrusData.ShowText( 'Admin service initialised.' )
            
            wx.CallAfter( ClientGUIFrames.ShowKeys, 'access', ( access_key, ) )
            
            admin_service = self._controller.GetServicesManager().GetService( admin_service_key )
            
            #
            
            time.sleep( 5 )
            
            HydrusData.ShowText( u'Creating tag and file services\u2026' )
            
            tag_options = HC.DEFAULT_OPTIONS[ HC.TAG_REPOSITORY ]
            tag_options[ 'port' ] = HC.DEFAULT_SERVICE_PORT
            
            file_options = HC.DEFAULT_OPTIONS[ HC.FILE_REPOSITORY ]
            file_options[ 'port' ] = HC.DEFAULT_SERVICE_PORT + 1
            
            edit_log = []
            
            edit_log.append( ( HC.ADD, ( HydrusData.GenerateKey(), HC.TAG_REPOSITORY, tag_options ) ) )
            edit_log.append( ( HC.ADD, ( HydrusData.GenerateKey(), HC.FILE_REPOSITORY, file_options ) ) )
            
            response = admin_service.Request( HC.POST, 'services', { 'edit_log' : edit_log } )
            
            service_keys_to_access_keys = dict( response[ 'service_keys_to_access_keys' ] )
            
            self._controller.WriteSynchronous( 'update_server_services', admin_service_key, [], edit_log, service_keys_to_access_keys )
            
            HydrusData.ShowText( 'Done! Check services->review services to see your new server and its services.' )
            
        
        text = 'This will attempt to start the server in the same install directory as this client, initialise it, and store the resultant admin accounts in the client.'
        
        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.CallToThread( do_it )
                
            
        
    
    def _BackupService( self, service_key ):
        
        def do_it():
            
            started = HydrusData.GetNow()
            
            service = self._controller.GetServicesManager().GetService( service_key )
            
            service.Request( HC.POST, 'backup' )
            
            HydrusData.ShowText( 'Server backup started!' )
            
            time.sleep( 10 )
            
            result = service.Request( HC.GET, 'busy' )
            
            while result == '1':
                
                if self._controller.ViewIsShutdown():
                    
                    return
                    
                
                time.sleep( 10 )
                
                result = service.Request( HC.GET, 'busy' )
                
            
            it_took = HydrusData.GetNow() - started
            
            HydrusData.ShowText( 'Server backup done in ' + HydrusData.ConvertTimeDeltaToPrettyString( it_took ) + '!' )
            
        
        message = 'This will tell the server to lock and copy its database files. It will probably take a few minutes to complete, during which time it will not be able to serve any requests.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.CallToThread( do_it )
                
            
        
    
    def _CheckDBIntegrity( self ):
        
        message = 'This will check the database for missing and invalid entries. It may take several minutes to complete.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, title = 'Run integrity check?', yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.Write( 'db_integrity' )
                
            
        
    
    def _CheckFileIntegrity( self ):
        
        client_files_manager = self._controller.GetClientFilesManager()
        
        message = 'This will go through all the files the database thinks it has and check that they actually exist. Any files that are missing will be deleted from the internal record.'
        message += os.linesep * 2
        message += 'You can perform a quick existence check, which will only look to see if a file exists, or a thorough content check, which will also make sure existing files are not corrupt or otherwise incorrect.'
        message += os.linesep * 2
        message += 'The thorough check will have to read all of your files\' content, which can take a long time. You should probably only do it if you suspect hard drive corruption and are now working on a safe drive.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, title = 'Choose how thorough your integrity check will be.', yes_label = 'quick', no_label = 'thorough' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_YES:
                
                self._controller.CallToThread( client_files_manager.CheckFileIntegrity, 'quick' )
                
            elif result == wx.ID_NO:
                
                text = 'If an existing file is found to be corrupt/incorrect, would you like to move it or delete it?'
                
                with ClientGUIDialogs.DialogYesNo( self, text, title = 'Choose what do to with bad files.', yes_label = 'move', no_label = 'delete' ) as dlg_2:
                    
                    result = dlg_2.ShowModal()
                    
                    if result == wx.ID_YES:
                        
                        with wx.DirDialog( self, 'Select location.' ) as dlg_3:
                            
                            if dlg_3.ShowModal() == wx.ID_OK:
                                
                                path = HydrusData.ToUnicode( dlg_3.GetPath() )
                                
                                self._controller.CallToThread( client_files_manager.CheckFileIntegrity, 'thorough', path )
                                
                            
                        
                    elif result == wx.ID_NO:
                        
                        self._controller.CallToThread( client_files_manager.CheckFileIntegrity, 'thorough' )
                        
                    
                
            
        
    
    def _ChooseNewPage( self ):
        
        with ClientGUIDialogs.DialogPageChooser( self ) as dlg:
            
            dlg.ShowModal()
            
        
    
    def _ClearOrphans( self ):
        
        text = 'This will iterate through every file in your database\'s file storage, removing any it does not expect to be there. It may take some time.'
        text += os.linesep * 2
        text += 'Files and thumbnails will be inaccessible while this occurs, so it is best to leave the client alone until it is done.'
        
        with ClientGUIDialogs.DialogYesNo( self, text, yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                text = 'What would you like to do with the orphaned files? Note that all orphaned thumbnails will be deleted.'
                
                client_files_manager = self._controller.GetClientFilesManager()
                
                with ClientGUIDialogs.DialogYesNo( self, text, title = 'Choose what do to with the orphans.', yes_label = 'move them somewhere', no_label = 'delete them' ) as dlg_2:
                    
                    result = dlg_2.ShowModal()
                    
                    if result == wx.ID_YES:
                        
                        with wx.DirDialog( self, 'Select location.' ) as dlg_3:
                            
                            if dlg_3.ShowModal() == wx.ID_OK:
                                
                                path = HydrusData.ToUnicode( dlg_3.GetPath() )
                                
                                self._controller.CallToThread( client_files_manager.ClearOrphans, path )
                                
                            
                        
                    elif result == wx.ID_NO:
                        
                        self._controller.CallToThread( client_files_manager.ClearOrphans )
                        
                    
                
            
        
    
    def _CloseCurrentPage( self, polite = True ):
        
        selection = self._notebook.GetSelection()
        
        if selection != wx.NOT_FOUND: self._ClosePage( selection, polite = polite )
        
    
    def _ClosePage( self, selection, polite = True ):
        
        self._controller.ResetIdleTimer()
        self._controller.ResetPageChangeTimer()
        
        if selection == -1 or selection > self._notebook.GetPageCount() - 1:
            
            return
            
        
        # issue with having all pages closed
        if HC.PLATFORM_OSX and self._notebook.GetPageCount() == 1:
            
            return
            
        
        page = self._notebook.GetPage( selection )
        
        if polite:
            
            try: page.TestAbleToClose()
            except HydrusExceptions.PermissionException:
                
                return
                
            
        
        page.PrepareToHide()
        
        page.Hide()
        
        name = self._notebook.GetPageText( selection )
        
        with self._lock:
            
            self._closed_pages.append( ( HydrusData.GetNow(), selection, name, page ) )
            
        
        self._notebook.RemovePage( selection )
        
        if self._notebook.GetPageCount() == 0: self._focus_holder.SetFocus()
        
        self._controller.pub( 'notify_new_undo' )
        
    
    def _DebugMakeSomePopups( self ):
        
        for i in range( 1, 7 ):
            
            HydrusData.ShowText( 'This is a test popup message -- ' + str( i ) )
            
        
        #
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetVariable( 'popup_title', u'\u24c9\u24d7\u24d8\u24e2 \u24d8\u24e2 \u24d0 \u24e3\u24d4\u24e2\u24e3 \u24e4\u24dd\u24d8\u24d2\u24de\u24d3\u24d4 \u24dc\u24d4\u24e2\u24e2\u24d0\u24d6\u24d4' )
        
        job_key.SetVariable( 'popup_text_1', u'\u24b2\u24a0\u24b2 \u24a7\u249c\u249f' )
        job_key.SetVariable( 'popup_text_2', u'p\u0250\u05df \u028d\u01dd\u028d' )
        
        self._controller.pub( 'message', job_key )
        
        #
        
        job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
        
        job_key.SetVariable( 'popup_title', 'test job' )
        
        job_key.SetVariable( 'popup_text_1', 'Currently processing test job 5/8' )
        job_key.SetVariable( 'popup_gauge_1', ( 5, 8 ) )
        
        self._controller.pub( 'message', job_key )
        
        wx.CallLater( 2000, job_key.SetVariable, 'popup_text_2', 'Pulsing subjob' )
        wx.CallLater( 2000, job_key.SetVariable, 'popup_gauge_2', ( 0, None ) )
        
        #
        
        e = HydrusExceptions.DataMissing( 'This is a test exception' )
        
        HydrusData.ShowException( e )
        
        #
        
        for i in range( 1, 4 ):
            
            wx.CallLater( 500 * i, HydrusData.ShowText, 'This is a delayed popup message -- ' + str( i ) )
            
        
    
    def _DebugPrintGarbage( self ):
        
        HydrusData.ShowText( 'Printing garbage to log' )
        
        gc.collect()
        
        count = collections.Counter()
        
        class_count = collections.Counter()
        
        for o in gc.get_objects():
            
            count[ type( o ) ] += 1
            
            if isinstance( o, types.InstanceType ): class_count[ o.__class__.__name__ ] += 1
            elif isinstance( o, types.BuiltinFunctionType ): class_count[ o.__name__ ] += 1
            elif isinstance( o, types.BuiltinMethodType ): class_count[ o.__name__ ] += 1
            
        
        HydrusData.Print( 'gc:' )
        
        for ( k, v ) in count.items():
            
            if v > 100: print ( k, v )
            
        
        for ( k, v ) in class_count.items():
            
            if v > 100: print ( k, v )
            
        
        HydrusData.Print( 'uncollectable garbage: ' + HydrusData.ToUnicode( gc.garbage ) )
        
    
    def _DeleteAllClosedPages( self ):
        
        with self._lock:
            
            deletee_pages = [ page for ( time_closed, selection, name, page ) in self._closed_pages ]
            
            self._closed_pages = []
            
        
        self._DestroyPages( deletee_pages )
        
        self._focus_holder.SetFocus()
        
        self._controller.pub( 'notify_new_undo' )
        
    
    def _DeleteGUISession( self, name ):
        
        self._controller.Write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION, name )
        
        self._controller.pub( 'notify_new_sessions' )
        
    
    def _DeletePending( self, service_key ):
        
        service = self._controller.GetServicesManager().GetService( service_key )
        
        with ClientGUIDialogs.DialogYesNo( self, 'Are you sure you want to delete the pending data for ' + service.GetName() + '?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES: self._controller.Write( 'delete_pending', service_key )
            
        
    
    def _DeleteServiceInfo( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Are you sure you want to clear the cached service info? Rebuilding it may slow some GUI elements for a little while.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES: self._controller.Write( 'delete_service_info' )
            
        
    
    def _DestroyPages( self, pages ):
        
        with self._lock:
            
            for page in pages:
                
                self._deleted_page_keys.add( page.GetPageKey() )
                
            
        
        for page in pages:
            
            page.CleanBeforeDestroy()
            
            page.Destroy()
            
        
        gc.collect()
        
    
    def _FetchIP( self, service_key ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the file\'s hash.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                hash = dlg.GetValue().decode( 'hex' )
                
                service = self._controller.GetServicesManager().GetService( service_key )
                
                with wx.BusyCursor(): response = service.Request( HC.GET, 'ip', { 'hash' : hash.encode( 'hex' ) } )
                
                ip = response[ 'ip' ]
                timestamp = response[ 'timestamp' ]
                
                text = 'File Hash: ' + hash.encode( 'hex' ) + os.linesep + 'Uploader\'s IP: ' + ip + os.linesep + 'Upload Time (GMT): ' + time.asctime( time.gmtime( int( timestamp ) ) )
                
                HydrusData.Print( text )
                
                wx.MessageBox( text + os.linesep + 'This has been written to the log.' )
                
            
        
    
    def _GenerateMenuInfo( self, name ):
        
        menu = wx.Menu()
        
        p = self._controller.PrepStringForDisplay
        
        def file():
            
            ClientGUIMenus.AppendMenuItem( menu, 'import files', 'Add new files to the database.', self, self._ImportFiles )
            menu.AppendSeparator()
            ClientGUIMenus.AppendMenuItem( menu, 'manage import folders', 'Manage folders from which the client can automatically import.', self, self._ManageImportFolders )
            ClientGUIMenus.AppendMenuItem( menu, 'manage export folders', 'Manage folders to which the client can automatically export.', self, self._ManageExportFolders )
            
            menu.AppendSeparator()
            
            open = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( open, 'installation directory', 'Open the installation directory for this client.', self, self._OpenInstallFolder )
            ClientGUIMenus.AppendMenuItem( open, 'database directory', 'Open the database directory for this instance of the client.', self, self._OpenDBFolder )
            ClientGUIMenus.AppendMenuItem( open, 'quick export directory', 'Open the export directory so you can easily access the files you have exported.', self, self._OpenExportFolder )
            
            ClientGUIMenus.AppendMenu( menu, open, 'open' )
            
            menu.AppendSeparator()
            
            ClientGUIMenus.AppendMenuItem( menu, 'options', 'Change how the client operates.', self, self._ManageOptions )
            
            menu.AppendSeparator()
            
            we_borked_linux_pyinstaller = HC.PLATFORM_LINUX and not HC.RUNNING_FROM_SOURCE
            
            if not we_borked_linux_pyinstaller:
                
                ClientGUIMenus.AppendMenuItem( menu, 'restart', 'Shut the client down and then start it up again.', self, self.Exit, restart = True )
                
            
            ClientGUIMenus.AppendMenuItem( menu, 'exit', 'Shut the client down.', self, self.Exit )
            
            return ( menu, p( '&File' ), True )
            
        
        def undo():
            
            with self._lock:
                
                have_closed_pages = len( self._closed_pages ) > 0
                
            
            undo_manager = self._controller.GetManager( 'undo' )
            
            ( undo_string, redo_string ) = undo_manager.GetUndoRedoStrings()
            
            have_undo_stuff = undo_string is not None or redo_string is not None
            
            if have_closed_pages or have_undo_stuff:
                
                show = True
                
                did_undo_stuff = False
                
                if undo_string is not None:
                    
                    did_undo_stuff = True
                    
                    ClientGUIMenus.AppendMenuItem( menu, undo_string, 'Undo last operation.', self, self._controller.pub, 'undo' )
                    
                
                if redo_string is not None:
                    
                    did_undo_stuff = True
                    
                    ClientGUIMenus.AppendMenuItem( menu, redo_string, 'Redo last operation.', self, self._controller.pub, 'redo' )
                    
                
                if have_closed_pages:
                    
                    if did_undo_stuff:
                        
                        menu.AppendSeparator()
                        
                    
                    undo_pages = wx.Menu()
                    
                    ClientGUIMenus.AppendMenuItem( undo_pages, 'clear all', 'Remove all closed pages from memory.', self, self._DeleteAllClosedPages )
                    
                    undo_pages.AppendSeparator()
                    
                    args = []
                    
                    with self._lock:
                        
                        for ( i, ( time_closed, index, name, page ) ) in enumerate( self._closed_pages ):
                            
                            args.append( ( i, name + ' - ' + page.GetPrettyStatus() ) )
                            
                        
                    
                    args.reverse() # so that recently closed are at the top
                    
                    for ( index, name ) in args:
                        
                        ClientGUIMenus.AppendMenuItem( undo_pages, name, 'Restore this page.', self, self._UnclosePage, index )
                        
                    
                    ClientGUIMenus.AppendMenu( menu, undo_pages, 'closed pages' )
                    
                
            else:
                
                show = False
                
            
            return ( menu, p( '&Undo' ), show )
            
        
        def pages():
            
            ClientGUIMenus.AppendMenuItem( menu, 'refresh', 'If the current page has a search, refresh it.', self, self._Refresh )
            ClientGUIMenus.AppendMenuItem( menu, 'show/hide management and preview panels', 'Show or hide the panels on the left.', self, self._ShowHideSplitters )
            
            menu.AppendSeparator()
            
            gui_session_names = self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
            
            sessions = wx.Menu()
            
            if len( gui_session_names ) > 0:
                
                load = wx.Menu()
                
                for name in gui_session_names:
                    
                    ClientGUIMenus.AppendMenuItem( load, name, 'Close all other pages and load this session.', self, self._LoadGUISession, name )
                    
                
                ClientGUIMenus.AppendMenu( sessions, load, 'load' )
                
            
            ClientGUIMenus.AppendMenuItem( sessions, 'save current', 'Save the existing open pages as a session.', self, self._SaveGUISession )
            
            if len( gui_session_names ) > 0 and gui_session_names != [ 'last session' ]:
                
                delete = wx.Menu()
                
                for name in gui_session_names:
                    
                    if name != 'last session':
                        
                        ClientGUIMenus.AppendMenuItem( delete, name, 'Delete this session.', self, self._DeleteGUISession, name )
                        
                    
                
                ClientGUIMenus.AppendMenu( sessions, delete, 'delete' )
                
            
            ClientGUIMenus.AppendMenu( menu, sessions, 'sessions' )
            
            menu.AppendSeparator()
            
            ClientGUIMenus.AppendMenuItem( menu, 'pick a new page', 'Choose a new page to open.', self, self._ChooseNewPage )
            
            #
            
            search_menu = wx.Menu()
            
            services = self._controller.GetServicesManager().GetServices()
            
            tag_repositories = [ service for service in services if service.GetServiceType() == HC.TAG_REPOSITORY ]
            
            petition_resolve_tag_services = [ repository for repository in tag_repositories if repository.GetInfo( 'account' ).HasPermission( HC.RESOLVE_PETITIONS ) ]
            
            file_repositories = [ service for service in services if service.GetServiceType() == HC.FILE_REPOSITORY ]
            
            petition_resolve_file_services = [ repository for repository in file_repositories if repository.GetInfo( 'account' ).HasPermission( HC.RESOLVE_PETITIONS ) ]
            
            ClientGUIMenus.AppendMenuItem( search_menu, 'my files', 'Open a new search tab for your files.', self, self._NewPageQuery, CC.LOCAL_FILE_SERVICE_KEY )
            ClientGUIMenus.AppendMenuItem( search_menu, 'trash', 'Open a new search tab for your recently deleted files.', self, self._NewPageQuery, CC.TRASH_SERVICE_KEY )
            
            for service in file_repositories:
                
                ClientGUIMenus.AppendMenuItem( search_menu, service.GetName(), 'Open a new search tab for ' + service.GetName() + '.', self, self._NewPageQuery, service.GetServiceKey() )
                
            
            search_menu.AppendSeparator()
            
            ClientGUIMenus.AppendMenuItem( search_menu, 'duplicates (under construction!)', 'Open a new tab to discover and filter duplicate files.', self, self._NewPageDuplicateFilter )
            
            ClientGUIMenus.AppendMenu( menu, search_menu, 'new search page' )
            
            #
            
            if len( petition_resolve_tag_services ) > 0 or len( petition_resolve_file_services ) > 0:
                
                petition_menu = wx.Menu()
                
                for service in petition_resolve_tag_services:
                    
                    ClientGUIMenus.AppendMenuItem( petition_menu, service.GetName(), 'Open a new tag petition tab for ' + service.GetName() + '.', self, self._NewPagePetitions, service.GetServiceKey() )
                    
                
                for service in petition_resolve_file_services:
                    
                    ClientGUIMenus.AppendMenuItem( petition_menu, service.GetName(), 'Open a new file petition tab for ' + service.GetName() + '.', self, self._NewPagePetitions, service.GetServiceKey() )
                    
                
                ClientGUIMenus.AppendMenu( menu, petition_menu, 'new petition page' )
                
            
            #
            
            download_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( download_menu, 'url download', 'Open a new tab to download some raw urls.', self, self._NewPageImportURLs )
            ClientGUIMenus.AppendMenuItem( download_menu, 'thread watcher', 'Open a new tab to watch a thread.', self, self._NewPageImportThreadWatcher )
            ClientGUIMenus.AppendMenuItem( download_menu, 'webpage of images', 'Open a new tab to download files from generic galleries or threads.', self, self._NewPageImportPageOfImages )
            
            gallery_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( gallery_menu, 'booru', 'Open a new tab to download files from a booru.', self, self._NewPageImportBooru )
            ClientGUIMenus.AppendMenuItem( gallery_menu, 'deviant art', 'Open a new tab to download files from Deviant Art.', self, self._NewPageImportGallery, ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_DEVIANT_ART ) )
            
            hf_submenu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( hf_submenu, 'by artist', 'Open a new tab to download files from Hentai Foundry.', self, self._NewPageImportGallery, ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST ) )
            ClientGUIMenus.AppendMenuItem( hf_submenu, 'by tags', 'Open a new tab to download files from Hentai Foundry.', self, self._NewPageImportGallery, ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_HENTAI_FOUNDRY_TAGS ) )
            
            ClientGUIMenus.AppendMenu( gallery_menu, hf_submenu, 'hentai foundry' )
            
            ClientGUIMenus.AppendMenuItem( gallery_menu, 'newgrounds', 'Open a new tab to download files from Newgrounds.', self, self._NewPageImportGallery, ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_NEWGROUNDS ) )
            
            result = self._controller.Read( 'serialisable_simple', 'pixiv_account' )
            
            if result is not None:
                
                pixiv_submenu = wx.Menu()
                
                ClientGUIMenus.AppendMenuItem( pixiv_submenu, 'by artist id', 'Open a new tab to download files from Pixiv.', self, self._NewPageImportGallery, ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_PIXIV_ARTIST_ID ) )
                ClientGUIMenus.AppendMenuItem( pixiv_submenu, 'by tag', 'Open a new tab to download files from Pixiv.', self, self._NewPageImportGallery, ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_PIXIV_TAG ) )
                
                ClientGUIMenus.AppendMenu( gallery_menu, pixiv_submenu, 'pixiv' )
                
            
            ClientGUIMenus.AppendMenuItem( gallery_menu, 'tumblr', 'Open a new tab to download files from tumblr.', self, self._NewPageImportGallery, ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_TUMBLR ) )
            
            ClientGUIMenus.AppendMenu( download_menu, gallery_menu, 'gallery' )
            ClientGUIMenus.AppendMenu( menu, download_menu, 'new download page' )
            
            download_popup_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( download_popup_menu, 'a youtube video', 'Enter a YouTube URL and choose which formats you would like to download', self, self._StartYoutubeDownload )
            
            has_ipfs = len( [ service for service in services if service.GetServiceType() == HC.IPFS ] )
            
            if has_ipfs:
                
                ClientGUIMenus.AppendMenuItem( download_popup_menu, 'an ipfs multihash', 'Enter an IPFS multihash and attempt to import whatever is returned.', self, self._StartIPFSDownload )
                
            
            ClientGUIMenus.AppendMenu( menu, download_popup_menu, 'new download popup' )
            
            #
            
            return ( menu, p( '&Pages' ), True )
            
        
        def database():
            
            ClientGUIMenus.AppendMenuItem( menu, 'set a password', 'Set a simple password for the database so only you can open it in the client.', self, self._SetPassword )
            
            menu.AppendSeparator()
            
            ClientGUIMenus.AppendMenuItem( menu, 'create a database backup', 'Back the database up to an external location.', self, self._controller.BackupDatabase )
            ClientGUIMenus.AppendMenuItem( menu, 'restore a database backup', 'Restore the database from an external location.', self, self._controller.RestoreDatabase )
            
            menu.AppendSeparator()
            
            submenu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( submenu, 'vacuum', 'Defrag the database by completely rebuilding it.', self, self._VacuumDatabase )
            ClientGUIMenus.AppendMenuItem( submenu, 'analyze', 'Optimise slow queries by running statistical analyses on the database.', self, self._AnalyzeDatabase )
            ClientGUIMenus.AppendMenuItem( submenu, 'similar files search data', 'Rebalance and update the data the database uses to find similar files.', self, self._MaintainSimilarFilesData )
            ClientGUIMenus.AppendMenuItem( submenu, 'rebalance file storage', 'Move your files around your chosen storage directories until they satisfy the weights you have set in the options.', self, self._RebalanceClientFiles )
            ClientGUIMenus.AppendMenuItem( submenu, 'clear orphans', 'Clear out surplus files that have found their way into the file structure.', self, self._ClearOrphans )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'maintain' )
            
            submenu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( submenu, 'database integrity', 'Have the database examine all its records for internal consistency.', self, self._CheckDBIntegrity )
            ClientGUIMenus.AppendMenuItem( submenu, 'file integrity', 'Have the database check if it truly has the files it thinks it does, and remove records when not.', self, self._CheckFileIntegrity )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'check' )
            
            submenu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( submenu, 'autocomplete cache', 'Delete and recreate the tag autocomplete cache, fixing any miscounts.', self, self._RegenerateACCache )
            ClientGUIMenus.AppendMenuItem( submenu, 'similar files search data', 'Delete and recreate the similar files search tree.', self, self._RegenerateSimilarFilesData )
            ClientGUIMenus.AppendMenuItem( submenu, 'all thumbnails', 'Delete all thumbnails and regenerate them from their original files.', self, self._RegenerateThumbnails )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'regenerate' )
            
            return ( menu, p( '&Database' ), True )
            
        
        def pending():
            
            nums_pending = self._controller.Read( 'nums_pending' )
            
            total_num_pending = 0
            
            for ( service_key, info ) in nums_pending.items():
                
                service = self._controller.GetServicesManager().GetService( service_key )
                
                service_type = service.GetServiceType()
                name = service.GetName()
                
                if service_type == HC.TAG_REPOSITORY:
                    
                    pending_phrase = 'mappings to upload'
                    petitioned_phrase = 'mappings to petition'
                    
                elif service_type == HC.FILE_REPOSITORY:
                    
                    pending_phrase = 'files to upload'
                    petitioned_phrase = 'files to petition'
                    
                elif service_type == HC.IPFS:
                    
                    pending_phrase = 'files to pin'
                    petitioned_phrase = 'files to unpin'
                    
                
                if service_type == HC.TAG_REPOSITORY:
                    
                    num_pending = info[ HC.SERVICE_INFO_NUM_PENDING_MAPPINGS ] + info[ HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS ] + info[ HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS ]
                    num_petitioned = info[ HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS ] + info[ HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS ] + info[ HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS ]
                    
                elif service_type in ( HC.FILE_REPOSITORY, HC.IPFS ):
                    
                    num_pending = info[ HC.SERVICE_INFO_NUM_PENDING_FILES ]
                    num_petitioned = info[ HC.SERVICE_INFO_NUM_PETITIONED_FILES ]
                    
                
                if num_pending + num_petitioned > 0:
                    
                    submenu = wx.Menu()
                    
                    ClientGUIMenus.AppendMenuItem( submenu, 'commit', 'Upload ' + name + '\'s pending content.', self, self._UploadPending, service_key )
                    ClientGUIMenus.AppendMenuItem( submenu, 'forget', 'Clear ' + name + '\'s pending content.', self, self._DeletePending, service_key )
                    
                    submessages = []
                    
                    if num_pending > 0:
                        
                        submessages.append( HydrusData.ConvertIntToPrettyString( num_pending ) + ' ' + pending_phrase )
                        
                    
                    if num_petitioned > 0:
                        
                        submessages.append( HydrusData.ConvertIntToPrettyString( num_petitioned ) + ' ' + petitioned_phrase )
                        
                    
                    message = name + ': ' + ', '.join( submessages )
                    
                    ClientGUIMenus.AppendMenu( menu, submenu, message )
                    
                
                total_num_pending += num_pending + num_petitioned
                
            
            show = total_num_pending > 0
            
            return ( menu, p( '&Pending (' + HydrusData.ConvertIntToPrettyString( total_num_pending ) + ')' ), show )
            
        
        def services():
            
            tag_services = self._controller.GetServicesManager().GetServices( ( HC.TAG_REPOSITORY, ) )
            file_services = self._controller.GetServicesManager().GetServices( ( HC.FILE_REPOSITORY, ) )
            
            submenu = wx.Menu()
            
            pause_export_folders_sync_id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'pause_export_folders_sync' )
            pause_import_folders_sync_id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'pause_import_folders_sync' )
            pause_repo_sync_id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'pause_repo_sync' )
            pause_subs_sync_id = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'pause_subs_sync' )
            
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
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'review_services' ), p( '&Review Services' ), p( 'Look at the services your client connects to.' ) )
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'manage_services' ), p( '&Manage Services' ), p( 'Edit the services your client connects to.' ) )
            
            tag_repositories = self._controller.GetServicesManager().GetServices( ( HC.TAG_REPOSITORY, ) )
            admin_tag_services = [ repository for repository in tag_repositories if repository.GetInfo( 'account' ).HasPermission( HC.GENERAL_ADMIN ) ]
            
            file_repositories = self._controller.GetServicesManager().GetServices( ( HC.FILE_REPOSITORY, ) )
            admin_file_services = [ repository for repository in file_repositories if repository.GetInfo( 'account' ).HasPermission( HC.GENERAL_ADMIN ) ]
            
            servers_admin = self._controller.GetServicesManager().GetServices( ( HC.SERVER_ADMIN, ) )
            server_admins = [ service for service in servers_admin if service.GetInfo( 'account' ).HasPermission( HC.GENERAL_ADMIN ) ]
            
            if len( admin_tag_services ) > 0 or len( admin_file_services ) > 0 or len( server_admins ) > 0:
                
                admin_menu = wx.Menu()
                
                for service in admin_tag_services:
                    
                    submenu = wx.Menu()
                    
                    service_key = service.GetServiceKey()
                    
                    submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'new_accounts', service_key ), p( 'Create New &Accounts' ), p( 'Create new accounts.' ) )
                    submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'manage_account_types', service_key ), p( '&Manage Account Types' ), p( 'Add, edit and delete account types for the tag repository.' ) )
                    submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'modify_account', service_key ), p( '&Modify an Account' ), p( 'Modify a specific account\'s type and expiration.' ) )
                    submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'account_info', service_key ), p( '&Get an Account\'s Info' ), p( 'Fetch information about an account from the tag repository.' ) )
                    submenu.AppendSeparator()
                    submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'stats', service_key ), p( '&Get Stats' ), p( 'Fetch operating statistics from the tag repository.' ) )
                    submenu.AppendSeparator()
                    submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'post_news', service_key ), p( '&Post News' ), p( 'Post a news item to the tag repository.' ) )
                    
                    admin_menu.AppendMenu( CC.ID_NULL, p( service.GetName() ), submenu )
                    
                
                for service in admin_file_services:
                    
                    submenu = wx.Menu()
                    
                    service_key = service.GetServiceKey()
                    
                    submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'new_accounts', service_key ), p( 'Create New &Accounts' ), p( 'Create new accounts.' ) )
                    submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'manage_account_types', service_key ), p( '&Manage Account Types' ), p( 'Add, edit and delete account types for the file repository.' ) )
                    submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'modify_account', service_key ), p( '&Modify an Account' ), p( 'Modify a specific account\'s type and expiration.' ) )
                    submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'account_info', service_key ), p( '&Get an Account\'s Info' ), p( 'Fetch information about an account from the file repository.' ) )
                    submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'fetch_ip', service_key ), p( '&Get an Uploader\'s IP Address' ), p( 'Fetch an uploader\'s ip address.' ) )
                    submenu.AppendSeparator()
                    submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'stats', service_key ), p( '&Get Stats' ), p( 'Fetch operating statistics from the file repository.' ) )
                    submenu.AppendSeparator()
                    submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'post_news', service_key ), p( '&Post News' ), p( 'Post a news item to the file repository.' ) )
                    
                    admin_menu.AppendMenu( CC.ID_NULL, p( service.GetName() ), submenu )
                    
                
                for service in server_admins:
                    
                    submenu = wx.Menu()
                    
                    service_key = service.GetServiceKey()
                    
                    submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'manage_server_services', service_key ), p( 'Manage &Services' ), p( 'Add, edit, and delete this server\'s services.' ) )
                    submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'backup_service', service_key ), p( 'Make a &Backup' ), p( 'Back up this server\'s database.' ) )
                    
                    admin_menu.AppendMenu( CC.ID_NULL, p( service.GetName() ), submenu )
                    
                
                menu.AppendMenu( CC.ID_NULL, p( 'Administrate Services' ), admin_menu )
                
            
            menu.AppendSeparator()
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'manage_tag_censorship' ), p( '&Manage Tag Censorship' ), p( 'Set which tags you want to see from which services.' ) )
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'manage_tag_siblings' ), p( '&Manage Tag Siblings' ), p( 'Set certain tags to be automatically replaced with other tags.' ) )
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'manage_tag_parents' ), p( '&Manage Tag Parents' ), p( 'Set certain tags to be automatically added with other tags.' ) )
            menu.AppendSeparator()
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'manage_parsing_scripts' ), p( 'Manage &Parsing Scripts' ), p( 'Manage how the client parses different types of web content.' ) )
            menu.AppendSeparator()
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'manage_boorus' ), p( 'Manage &Boorus' ), p( 'Change the html parsing information for boorus to download from.' ) )
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'manage_pixiv_account' ), p( 'Manage &Pixiv Account' ), p( 'Set up your pixiv username and password.' ) )
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'manage_subscriptions' ), p( 'Manage &Subscriptions' ), p( 'Change the queries you want the client to regularly import from.' ) )
            menu.AppendSeparator()
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'manage_upnp' ), p( 'Manage Local UPnP' ) )
            
            if len( tag_services ) + len( file_services ) > 0:
                
                menu.AppendSeparator()
                submenu = wx.Menu()
                for service in tag_services: submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'news', service.GetServiceKey() ), p( service.GetName() ), p( 'Review ' + service.GetName() + '\'s past news.' ) )
                for service in file_services: submenu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'news', service.GetServiceKey() ), p( service.GetName() ), p( 'Review ' + service.GetName() + '\'s past news.' ) )
                menu.AppendMenu( CC.ID_NULL, p( 'News' ), submenu )
                
            
            return ( menu, p( '&Services' ), True )
            
        
        def help():
            
            ClientGUIMenus.AppendMenuItem( menu, 'help', 'Open hydrus\'s local help in your web browser.', self, webbrowser.open, 'file://' + HC.HELP_DIR + '/index.html' )
            
            dont_know = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( dont_know, 'just set up some repositories for me, please', 'This will add the hydrus dev\'s two repositories to your client.', self, self._AutoRepoSetup )
            
            ClientGUIMenus.AppendMenu( menu, dont_know, 'I don\'t know what I am doing' )
            
            links = wx.Menu()
            
            site = ClientGUIMenus.AppendMenuBitmapItem( links, 'site', 'Open hydrus\'s website, which is mostly a mirror of the local help.', self, CC.GlobalBMPs.file_repository, webbrowser.open, 'https://hydrusnetwork.github.io/hydrus/' )
            site = ClientGUIMenus.AppendMenuBitmapItem( links, '8chan board', 'Open hydrus dev\'s 8chan board, where he makes release posts and other status updates. Much other discussion also occurs.', self, CC.GlobalBMPs.eight_chan, webbrowser.open, 'https://8ch.net/hydrus/index.html' )
            site = ClientGUIMenus.AppendMenuBitmapItem( links, 'twitter', 'Open hydrus dev\'s twitter, where he makes general progress updates and emergency notifications.', self, CC.GlobalBMPs.twitter, webbrowser.open, 'https://twitter.com/hydrusnetwork' )
            site = ClientGUIMenus.AppendMenuBitmapItem( links, 'tumblr', 'Open hydrus dev\'s tumblr, where he makes release posts and other status updates.', self, CC.GlobalBMPs.tumblr, webbrowser.open, 'http://hydrus.tumblr.com/' )
            site = ClientGUIMenus.AppendMenuBitmapItem( links, 'discord', 'Open a discord channel where many hydrus users congregate. Hydrus dev visits regularly.', self, CC.GlobalBMPs.discord, webbrowser.open, 'https://discord.gg/vy8CUB4' )
            site = ClientGUIMenus.AppendMenuBitmapItem( links, 'patreon', 'Open hydrus dev\'s patreon, which lets you support development.', self, CC.GlobalBMPs.patreon, webbrowser.open, 'https://www.patreon.com/hydrus_dev' )
            
            ClientGUIMenus.AppendMenu( menu, links, 'links' )
            
            debug = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( debug, 'make some popups', 'Throw some varied popups at the message manager, just to check it is working.', self, self._DebugMakeSomePopups )
            ClientGUIMenus.AppendMenuItem( debug, 'make a popup in five seconds', 'Throw a delayed popup at the message manager, giving you time to minimise or otherwise alter the client before it arrives.', self, wx.CallLater, 5000, HydrusData.ShowText, 'This is a delayed popup message.' )
            ClientGUIMenus.AppendMenuCheckItem( debug, 'db report mode', 'Have the db report query information, where supported.', self, HydrusGlobals.db_report_mode, self._SwitchBoolean, 'db_report_mode' )
            ClientGUIMenus.AppendMenuCheckItem( debug, 'db profile mode', 'Run detailed \'profiles\' on every database query and dump this information to the log (this is very useful for hydrus dev to have, if something is running slow for you!).', self, HydrusGlobals.db_profile_mode, self._SwitchBoolean, 'db_profile_mode' )
            ClientGUIMenus.AppendMenuCheckItem( debug, 'pubsub profile mode', 'Run detailed \'profiles\' on every internal publisher/subscriber message and dump this information to the log. This can hammer your log with dozens of large dumps every second. Don\'t run it unless you know you need to.', self, HydrusGlobals.pubsub_profile_mode, self._SwitchBoolean, 'pubsub_profile_mode' )
            ClientGUIMenus.AppendMenuCheckItem( debug, 'force idle mode', 'Make the client consider itself idle and fire all maintenance routines right now. This may hang the gui for a while.', self, HydrusGlobals.force_idle_mode, self._SwitchBoolean, 'force_idle_mode' )
            ClientGUIMenus.AppendMenuItem( debug, 'print garbage', 'Print some information about the python garbage to the log.', self, self._DebugPrintGarbage )
            ClientGUIMenus.AppendMenuItem( debug, 'clear image rendering cache', 'Tell the image rendering system to forget all current images. This will often free up a bunch of memory immediately.', self, self._controller.ClearCaches )
            ClientGUIMenus.AppendMenuItem( debug, 'clear db service info cache', 'Delete all cached service info like total number of mappings or files, in case it has become desynchronised. Some parts of the gui may be laggy immediately after this as these numbers are recalculated.', self, self._DeleteServiceInfo )
            ClientGUIMenus.AppendMenuItem( debug, 'load whole db in disk cache', 'Contiguously read as much of the db as will fit into memory. This will massively speed up any subsequent big job.', self, self._controller.CallToThread, self._controller.Read, 'load_into_disk_cache' )
            ClientGUIMenus.AppendMenuItem( debug, 'run and initialise server for testing', 'This will try to boot the server in your install folder and initialise it. This is mostly here for testing purposes.', self, self._AutoServerSetup )
            
            ClientGUIMenus.AppendMenu( menu, debug, 'debug' )
            
            ClientGUIMenus.AppendMenuItem( menu, 'hardcoded shortcuts', 'Review some currently hardcoded shortcuts.', self, wx.MessageBox, CC.SHORTCUT_HELP )
            ClientGUIMenus.AppendMenuItem( menu, 'about', 'See this client\'s version and other information.', self, self._AboutWindow )
            
            return ( menu, p( '&Help' ), True )
            
        
        if name == 'file': return file()
        elif name == 'undo': return undo()
        elif name == 'pages': return pages()
        elif name == 'database': return database()
        elif name == 'pending': return pending()
        elif name == 'services': return services()
        elif name == 'help': return help()
        
    
    def _GenerateNewAccounts( self, service_key ):
        
        with ClientGUIDialogs.DialogGenerateNewAccounts( self, service_key ) as dlg: dlg.ShowModal()
        
    
    def _ImportFiles( self, paths = None ):
        
        if paths is None: paths = []
        
        with ClientGUIDialogs.DialogInputLocalFiles( self, paths ) as dlg:
            
            dlg.ShowModal()
            
        
    
    def _InitialiseMenubar( self ):
        
        self._menubar = wx.MenuBar()
        
        self.SetMenuBar( self._menubar )
        
        for name in MENU_ORDER:
            
            ( menu, label, show ) = self._GenerateMenuInfo( name )
            
            if show:
                
                self._menubar.Append( menu, label )
                
            
            self._menus[ name ] = ( menu, label, show )
            
        
    
    def _LoadGUISession( self, name ):
        
        if self._loading_session:
            
            HydrusData.ShowText( 'Sorry, currently loading a session. Please wait.' )
            
            return
            
        
        self._loading_session = True
        
        try:
            
            session = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION, name )
            
        except Exception as e:
            
            HydrusData.ShowText( 'While trying to load session ' + name + ', this error happened:' )
            HydrusData.ShowException( e )
            
            self._NewPageQuery( CC.LOCAL_FILE_SERVICE_KEY )
            
            return
            
        
        for page in [ self._notebook.GetPage( i ) for i in range( self._notebook.GetPageCount() ) ]:
            
            try: page.TestAbleToClose()
            except HydrusExceptions.PermissionException:
                
                return
                
            
        
        while self._notebook.GetPageCount() > 0:
            
            self._CloseCurrentPage( polite = False )
            
        
        def do_it():
            
            try:
                
                for ( page_name, management_controller, initial_hashes ) in session.IteratePages():
                    
                    try:
                        
                        if len( initial_hashes ) > 0:
                            
                            initial_media_results = []
                            
                            for group_of_inital_hashes in HydrusData.SplitListIntoChunks( initial_hashes, 256 ):
                                
                                more_media_results = self._controller.Read( 'media_results', group_of_inital_hashes )
                                
                                initial_media_results.extend( more_media_results )
                                
                                self._media_status_override = u'Loading session page \'' + page_name + u'\'\u2026 ' + HydrusData.ConvertValueRangeToPrettyString( len( initial_media_results ), len( initial_hashes ) )
                                
                                self._controller.pub( 'refresh_status' )
                                
                            
                        else:
                            
                            initial_media_results = []
                            
                        
                        wx.CallAfter( self._NewPage, page_name, management_controller, initial_media_results = initial_media_results )
                        
                    except Exception as e:
                        
                        HydrusData.ShowException( e )
                        
                    
                
                if HC.PLATFORM_OSX:
                    
                    wx.CallAfter( self._ClosePage, 0 )
                    
                
            finally:
                
                self._loading_session = False
                self._media_status_override = None
                
            
        
        self._controller.CallToThread( do_it )
        
    
    def _MaintainSimilarFilesData( self ):
        
        text = 'This will rebalance the similar files search data, improving search speed.'
        text += os.linesep * 2
        text += 'If there is work to do, it will report its status through a popup message. The gui may hang until it is done.'
        
        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_YES:
                
                stop_time = HydrusData.GetNow() + 60 * 10
                
                self._controller.Write( 'maintain_similar_files_tree', stop_time )
                
            
        
    
    def _ManageAccountTypes( self, service_key ):
        
        with ClientGUIDialogsManage.DialogManageAccountTypes( self, service_key ) as dlg: dlg.ShowModal()
        
    
    def _ManageBoorus( self ):
        
        with ClientGUIDialogsManage.DialogManageBoorus( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageExportFolders( self ):
        
        with ClientGUIDialogsManage.DialogManageExportFolders( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageImportFolders( self ):
        
        with ClientGUIDialogsManage.DialogManageImportFolders( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageOptions( self ):
        
        title = 'manage options'
        frame_key = 'manage_options_dialog'
        
        with ClientGUITopLevelWindows.DialogManage( self, title, frame_key ) as dlg:
            
            panel = ClientGUIScrolledPanelsManagement.ManageOptionsPanel( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
        self._controller.pub( 'wake_daemons' )
        self._controller.pub( 'refresh_status' )
        
    
    def _ManageParsingScripts( self ):
        
        title = 'manage parsing scripts'
        frame_key = 'regular_dialog'
        
        with ClientGUITopLevelWindows.DialogManage( self, title, frame_key ) as dlg:
            
            panel = ClientGUIParsing.ManageParsingScriptsPanel( dlg )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
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
            
            title = 'manage subscriptions'
            frame_key = 'manage_subscriptions_dialog'
            
            with ClientGUITopLevelWindows.DialogManage( self, title, frame_key ) as dlg:
                
                panel = ClientGUIScrolledPanelsManagement.ManageSubscriptionsPanel( dlg )
                
                dlg.SetPanel( panel )
                
                dlg.ShowModal()
                
            
        finally:
            
            HC.options[ 'pause_subs_sync' ] = original_pause_status
            
        
    
    def _ManageTagCensorship( self ):
        
        with ClientGUIDialogsManage.DialogManageTagCensorship( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageTagParents( self ):
        
        with ClientGUIDialogsManage.DialogManageTagParents( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageTagSiblings( self ):
        
        with ClientGUIDialogsManage.DialogManageTagSiblings( self ) as dlg: dlg.ShowModal()
        
    
    def _ManageUPnP( self ):
        
        with ClientGUIDialogsManage.DialogManageUPnP( self ) as dlg: dlg.ShowModal()
        
    
    def _ModifyAccount( self, service_key ):
        
        service = self._controller.GetServicesManager().GetService( service_key )
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the account key for the account to be modified.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try: account_key = dlg.GetValue().decode( 'hex' )
                except:
                    
                    wx.MessageBox( 'Could not parse that account key' )
                    
                    return
                    
                
                subject_identifiers = ( HydrusData.AccountIdentifier( account_key = account_key ), )
                
                with ClientGUIDialogs.DialogModifyAccounts( self, service_key, subject_identifiers ) as dlg2: dlg2.ShowModal()
                
            
        
    
    def _NewPage( self, page_name, management_controller, initial_media_results = None ):
        
        self._controller.ResetIdleTimer()
        self._controller.ResetPageChangeTimer()
        
        if initial_media_results is None:
            
            initial_media_results = []
            
        
        page = ClientGUIPages.Page( self._notebook, self._controller, management_controller, initial_media_results )
        
        self._notebook.AddPage( page, page_name, select = True )
        
        wx.CallAfter( page.SetSearchFocus )
        
    
    def _NewPageDuplicateFilter( self ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerDuplicateFilter()
        
        page_name = 'duplicates'
        
        self._NewPage( page_name, management_controller )
        
    
    def _NewPageImportBooru( self ):

        with ClientGUIDialogs.DialogSelectBooru( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                gallery_identifier = dlg.GetGalleryIdentifier()
                
                self._NewPageImportGallery( gallery_identifier )
                
            
        
    
    def _NewPageImportGallery( self, gallery_identifier ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportGallery( gallery_identifier )
        
        page_name = gallery_identifier.ToString()
        
        self._NewPage( page_name, management_controller )
        
    
    def _NewPageImportPageOfImages( self ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportPageOfImages()
        
        self._NewPage( 'download', management_controller )
        
    
    def _NewPageImportThreadWatcher( self ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportThreadWatcher()
        
        self._NewPage( 'thread watcher', management_controller )
        
    
    def _NewPageImportURLs( self ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportURLs()
        
        self._NewPage( 'url import', management_controller )
        
    
    def _NewPagePetitions( self, service_key = None ):
        
        if service_key is None: service_key = ClientGUIDialogs.SelectServiceKey( service_types = HC.REPOSITORIES, permission = HC.RESOLVE_PETITIONS )
        
        if service_key is not None:
            
            management_controller = ClientGUIManagement.CreateManagementControllerPetitions( service_key )
            
            service = self._controller.GetServicesManager().GetService( service_key )
            
            page_name = service.GetName() + ' petitions'
            
            self._NewPage( page_name, management_controller )
            
        
    
    def _NewPageQuery( self, file_service_key, initial_media_results = None, initial_predicates = None ):
        
        if initial_media_results is None: initial_media_results = []
        if initial_predicates is None: initial_predicates = []
        
        search_enabled = len( initial_media_results ) == 0
        
        new_options = self._controller.GetNewOptions()
        
        tag_service_key = new_options.GetKey( 'default_tag_service_search_page' )
        
        if not self._controller.GetServicesManager().ServiceExists( tag_service_key ):
            
            tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        file_search_context = ClientSearch.FileSearchContext( file_service_key = file_service_key, tag_service_key = tag_service_key, predicates = initial_predicates )
        
        management_controller = ClientGUIManagement.CreateManagementControllerQuery( file_service_key, file_search_context, search_enabled )
        
        self._NewPage( 'files', management_controller, initial_media_results = initial_media_results )
        
    
    def _News( self, service_key ):
        
        with ClientGUIDialogs.DialogNews( self, service_key ) as dlg: dlg.ShowModal()
        
    
    def _OpenDBFolder( self ):
        
        HydrusPaths.LaunchDirectory( self._controller.GetDBDir() )
        
    
    def _OpenExportFolder( self ):
        
        export_path = ClientExporting.GetExportPath()
        
        HydrusPaths.LaunchDirectory( export_path )
        
    
    def _OpenInstallFolder( self ):
        
        HydrusPaths.LaunchDirectory( HC.BASE_DIR )
        
    
    def _PauseSync( self, sync_type ):
        
        if sync_type == 'repo':
            
            HC.options[ 'pause_repo_sync' ] = not HC.options[ 'pause_repo_sync' ]
            
            self._controller.pub( 'notify_restart_repo_sync_daemon' )
            
        elif sync_type == 'subs':
            
            HC.options[ 'pause_subs_sync' ] = not HC.options[ 'pause_subs_sync' ]
            
            self._controller.pub( 'notify_restart_subs_sync_daemon' )
            
        elif sync_type == 'export_folders':
            
            HC.options[ 'pause_export_folders_sync' ] = not HC.options[ 'pause_export_folders_sync' ]
            
            self._controller.pub( 'notify_restart_export_folders_daemon' )
            
        elif sync_type == 'import_folders':
            
            HC.options[ 'pause_import_folders_sync' ] = not HC.options[ 'pause_import_folders_sync' ]
            
            self._controller.pub( 'notify_restart_import_folders_daemon' )
            
        
        self._controller.Write( 'save_options', HC.options )
        
    
    def _PostNews( self, service_key ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the news you would like to post.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                news = dlg.GetValue()
                
                service = self._controller.GetServicesManager().GetService( service_key )
                
                with wx.BusyCursor(): service.Request( HC.POST, 'news', { 'news' : news } )
                
            
        
    
    def _RebalanceClientFiles( self ):
        
        text = 'This will move your files around your storage directories until they satisfy the weights you have set in the options. It will also recover any folders that are in the wrong place. Use this if you have recently changed your file storage locations and want to hurry any transfers you have set up, or if you are recovering a complicated backup.'
        text += os.linesep * 2
        text += 'The operation will lock file access and the database. Popup messages will report its progress.'
        
        with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.CallToThread( self._controller.GetClientFilesManager().Rebalance, partial = False )
                
            
        
    
    def _Refresh( self ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None:
            
            page.RefreshQuery()
            
        
    
    def _RefreshStatusBar( self ):
        
        if self._media_status_override is not None:
            
            media_status = self._media_status_override
            
        else:
            
            page = self._notebook.GetCurrentPage()
            
            if page is None:
                
                media_status = ''
                
            else:
                
                media_status = page.GetPrettyStatus()
                
            
        
        if self._controller.CurrentlyIdle():
            
            idle_status = 'idle'
            
        else:
            
            idle_status = ''
            
        
        if self._controller.SystemBusy():
            
            busy_status = 'system busy'
            
        else:
            
            busy_status = ''
            
        
        if self._controller.DBCurrentlyDoingJob():
            
            db_status = 'db locked'
            
        else:
            
            db_status = ''
            
        
        self._statusbar.SetStatusText( media_status, number = 0 )
        self._statusbar.SetStatusText( idle_status, number = 1 )
        self._statusbar.SetStatusText( busy_status, number = 2 )
        self._statusbar.SetStatusText( db_status, number = 3 )
        
    
    def _RegenerateACCache( self ):
        
        message = 'This will delete and then recreate the entire autocomplete cache. This is useful if miscounting has somehow occured.'
        message += os.linesep * 2
        message += 'If you have a lot of tags and files, it can take a long time, during which the gui may hang.'
        message += os.linesep * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_YES:
                
                self._controller.Write( 'regenerate_ac_cache' )
                
            
        
    
    def _RegenerateSimilarFilesData( self ):
        
        message = 'This will delete and then recreate the similar files search tree. This is useful if it has somehow become unbalanced and similar files searches are running slow.'
        message += os.linesep * 2
        message += 'If you have a lot of files, it can take a little while, during which the gui may hang.'
        message += os.linesep * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_YES:
                
                self._controller.Write( 'regenerate_similar_files' )
                
            
        
    
    def _RegenerateThumbnails( self ):
        
        client_files_manager = self._controller.GetClientFilesManager()
        
        text = 'This will rebuild all your thumbnails from the original files. You probably only want to do this if you experience thumbnail errors. If you have a lot of files, it will take some time. A popup message will show its progress.'
        text += os.linesep * 2
        text += 'You can choose to only regenerate missing thumbnails, which is useful if you are rebuilding a fractured database, or you can force a complete refresh of all thumbnails, which is useful if some have been corrupted by a faulty hard drive.'
        text += os.linesep * 2
        text += 'Files and thumbnails will be inaccessible while this occurs, so it is best to leave the client alone until it is done.'
        
        with ClientGUIDialogs.DialogYesNo( self, text, yes_label = 'only do missing', no_label = 'force all' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_YES:
                
                self._controller.CallToThread( client_files_manager.RegenerateThumbnails, only_do_missing = True )
                
            elif result == wx.ID_NO:
                
                self._controller.CallToThread( client_files_manager.RegenerateThumbnails )
                
            
        
    
    def _RenamePage( self, selection ):
        
        if selection == -1 or selection > self._notebook.GetPageCount() - 1:
            
            return
            
        
        current_name = self._notebook.GetPageText( selection )
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the new name.', default = current_name, allow_blank = False ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                new_name = dlg.GetValue()
                
                self._notebook.SetPageText( selection, new_name )
                
            
        
    
    def _ReviewServices( self ):
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, self._controller.PrepStringForDisplay( 'Review Services' ), 'review_services' )
        
        panel = ClientGUIScrolledPanelsReview.ReviewServicesPanel( frame, self._controller )
        
        frame.SetPanel( panel )
        
    
    def _SaveGUISession( self, name = None ):
        
        if self._loading_session:
            
            HydrusData.ShowText( 'Sorry, currently loading a session. Please wait.' )
            
            return
            
        
        if name is None:
            
            while True:
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Enter a name for the new session.' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        name = dlg.GetValue()
                        
                        if name in ( 'just a blank page', 'last session' ):
                            
                            wx.MessageBox( 'Sorry, you cannot have that name! Try another.' )
                            
                        else:
                            
                            existing_session_names = self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
                            
                            if name in existing_session_names:
                                
                                message = 'Session \'' + name + '\' already exists! Do you want to overwrite it?'
                                
                                with ClientGUIDialogs.DialogYesNo( self , message, title = 'Overwrite existing session?', yes_label = 'yes, overwrite', no_label = 'no, choose another name' ) as yn_dlg:
                                    
                                    if yn_dlg.ShowModal() != wx.ID_YES:
                                        
                                        continue
                                        
                                    
                                
                            
                            break
                            
                        
                    else:
                        
                        return
                        
                    
                
            
        
        session = ClientGUIPages.GUISession( name )
        
        for i in range( self._notebook.GetPageCount() ):
            
            page = self._notebook.GetPage( i )
            
            page_name = self._notebook.GetPageText( i )
            
            management_controller = page.GetManagementController()
            
            # this bit could obviously be 'getmediaresultsobject' or whatever, with sort/collect/selection/view status
            media = page.GetMedia()
            
            hashes = set()
            
            for m in media: hashes.update( m.GetHashes() )
            
            hashes = list( hashes )
            
            session.AddPage( page_name, management_controller, hashes )
            
        
        self._controller.Write( 'serialisable', session )
        
        self._controller.pub( 'notify_new_sessions' )
        
    
    def _SetPassword( self ):
        
        message = '''You can set a password to be asked for whenever the client starts.

Though not foolproof by any means, it will stop noobs from easily seeing your files if you leave your machine unattended.

Do not ever forget your password! If you do, you'll have to manually insert a yaml-dumped python dictionary into a sqlite database or recompile from source to regain easy access. This is not trivial.

The password is cleartext here but obscured in the entry dialog. Enter a blank password to remove.'''
        
        with ClientGUIDialogs.DialogTextEntry( self, message, allow_blank = True ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                password = dlg.GetValue()
                
                if password == '': password = None
                
                self._controller.Write( 'set_password', password )
                
            
        
    
    def _SetMediaFocus( self ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None: page.SetMediaFocus()
        
    
    def _SetSearchFocus( self ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None: page.SetSearchFocus()
        
    
    def _SetSynchronisedWait( self ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None: page.SetSynchronisedWait()
        
    
    def _ShowHideSplitters( self ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None:
            
            page.ShowHideSplit()
            
        
    
    def _StartIPFSDownload( self ):
        
        ipfs_services = self._controller.GetServicesManager().GetServices( ( HC.IPFS, ) )
        
        if len( ipfs_services ) > 0:
            
            if len( ipfs_services ) == 1:
                
                ( service, ) = ipfs_services
                
            else:
                
                names_to_services = { service.GetName() : service for service in ipfs_services }
                
                with ClientGUIDialogs.DialogSelectFromListOfStrings( self, 'Select which IPFS Daemon', names_to_services.keys() ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        name = dlg.GetString()
                        
                        service = names_to_services[ name ]
                        
                    else:
                        
                        return
                        
                    
                
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Enter multihash to download.' ) as dlg:
                
                result = dlg.ShowModal()
                
                if result == wx.ID_OK:
                    
                    multihash = dlg.GetValue()
                    
                    service.ImportFile( multihash )
                    
                
            
        
    
    def _StartYoutubeDownload( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter YouTube URL.' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_OK:
                
                url = dlg.GetValue()
                
                info = ClientDownloading.GetYoutubeFormats( url )
                
                with ClientGUIDialogs.DialogSelectYoutubeURL( self, info ) as select_dlg: select_dlg.ShowModal()
                
            
        
    
    def _Stats( self, service_key ):
        
        service = self._controller.GetServicesManager().GetService( service_key )
        
        response = service.Request( HC.GET, 'stats' )
        
        stats = response[ 'stats' ]
        
        wx.MessageBox( HydrusData.ToUnicode( stats ) )
        
    
    def _SwitchBoolean( self, name ):
        
        if name == 'db_report_mode':
            
            HydrusGlobals.db_report_mode = not HydrusGlobals.db_report_mode
            
        elif name == 'db_profile_mode':
            
            HydrusGlobals.db_profile_mode = not HydrusGlobals.db_profile_mode
            
        elif name == 'pubsub_profile_mode':
            
            HydrusGlobals.pubsub_profile_mode = not HydrusGlobals.pubsub_profile_mode
            
        elif name == 'force_idle_mode':
            
            HydrusGlobals.force_idle_mode = not HydrusGlobals.force_idle_mode
            
        
    
    def _UnclosePage( self, closed_page_index ):
        
        with self._lock:
            
            ( time_closed, index, name, page ) = self._closed_pages.pop( closed_page_index )
            
        
        page.Show()
        
        index = min( index, self._notebook.GetPageCount() )
        
        self._notebook.InsertPage( index, page, name, True )
        
        self._controller.pub( 'notify_new_undo' )
        
    
    def _UploadPending( self, service_key ):
        
        self._controller.CallToThread( self._THREADUploadPending, service_key )
        
    
    def _VacuumDatabase( self ):
        
        text = 'This will rebuild the database, rewriting all indices and tables to be contiguous and optimising most operations. It typically happens automatically every few days, but you can force it here. If you have a large database, it will take a few minutes, during which your gui may hang. A popup message will show its status.'
        text += os.linesep * 2
        text += 'A \'soft\' vacuum will only reanalyze those databases that are due for a check in the normal db maintenance cycle. If nothing is due, it will return immediately.'
        text += os.linesep * 2
        text += 'A \'full\' vacuum will immediately force a vacuum for the entire database. This can take substantially longer.'
        
        with ClientGUIDialogs.DialogYesNo( self, text, title = 'Choose how thorough your vacuum will be.', yes_label = 'soft', no_label = 'full' ) as dlg:
            
            result = dlg.ShowModal()
            
            if result == wx.ID_YES:
                
                self._controller.Write( 'vacuum' )
                
            elif result == wx.ID_NO:
                
                self._controller.Write( 'vacuum', force_vacuum = True )
                
            
        
    
    def _THREADSyncToTagArchive( self, hta_path, tag_service_key, file_service_key, adding, namespaces, hashes = None ):
        
        if hashes is not None:
            
            hashes = set( hashes )
            
        
        job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
        
        try:
            
            hta = HydrusTagArchive.HydrusTagArchive( hta_path )
            
            job_key.SetVariable( 'popup_title', 'syncing to tag archive ' + hta.GetName() )
            job_key.SetVariable( 'popup_text_1', 'preparing' )
            
            self._controller.pub( 'message', job_key )
            
            hydrus_hashes = []
            
            hash_type = hta.GetHashType()
            
            total_num_hta_hashes = 0
            
            for chunk_of_hta_hashes in HydrusData.SplitIteratorIntoChunks( hta.IterateHashes(), 1000 ):
                
                while job_key.IsPaused() or job_key.IsCancelled():
                    
                    time.sleep( 0.1 )
                    
                    if job_key.IsCancelled():
                        
                        job_key.SetVariable( 'popup_text_1', 'cancelled' )
                        
                        HydrusData.Print( job_key.ToString() )
                        
                        return
                        
                    
                
                if hash_type == HydrusTagArchive.HASH_TYPE_SHA256:
                    
                    chunk_of_hydrus_hashes = chunk_of_hta_hashes
                    
                else:
                    
                    if hash_type == HydrusTagArchive.HASH_TYPE_MD5: given_hash_type = 'md5'
                    elif hash_type == HydrusTagArchive.HASH_TYPE_SHA1: given_hash_type = 'sha1'
                    elif hash_type == HydrusTagArchive.HASH_TYPE_SHA512: given_hash_type = 'sha512'
                    
                    chunk_of_hydrus_hashes = self._controller.Read( 'file_hashes', chunk_of_hta_hashes, given_hash_type, 'sha256' )
                    
                
                if file_service_key != CC.COMBINED_FILE_SERVICE_KEY:
                    
                    chunk_of_hydrus_hashes = self._controller.Read( 'filter_hashes', chunk_of_hydrus_hashes, file_service_key )
                    
                
                if hashes is not None:
                    
                    chunk_of_hydrus_hashes = [ hash for hash in chunk_of_hydrus_hashes if hash in hashes ]
                    
                
                hydrus_hashes.extend( chunk_of_hydrus_hashes )
                
                total_num_hta_hashes += len( chunk_of_hta_hashes )
                
                job_key.SetVariable( 'popup_text_1', 'matched ' + HydrusData.ConvertValueRangeToPrettyString( len( hydrus_hashes ), total_num_hta_hashes ) + ' files' )
                
                HydrusGlobals.client_controller.WaitUntilPubSubsEmpty()
                
            
            del hta
            
            total_num_processed = 0
            
            for chunk_of_hydrus_hashes in HydrusData.SplitListIntoChunks( hydrus_hashes, 50 ):
        
                while job_key.IsPaused() or job_key.IsCancelled():
                    
                    time.sleep( 0.1 )
                    
                    if job_key.IsCancelled():
                        
                        job_key.SetVariable( 'popup_text_1', 'cancelled' )
                        
                        HydrusData.Print( job_key.ToString() )
                        
                        return
                        
                    
                
                self._controller.WriteSynchronous( 'sync_hashes_to_tag_archive', chunk_of_hydrus_hashes, hta_path, tag_service_key, adding, namespaces )
                
                total_num_processed += len( chunk_of_hydrus_hashes )
                
                job_key.SetVariable( 'popup_text_1', 'synced ' + HydrusData.ConvertValueRangeToPrettyString( total_num_processed, len( hydrus_hashes ) ) + ' files' )
                job_key.SetVariable( 'popup_gauge_1', ( total_num_processed, len( hydrus_hashes ) ) )
                
                HydrusGlobals.client_controller.WaitUntilPubSubsEmpty()
                
            
            job_key.DeleteVariable( 'popup_gauge_1' )
            job_key.SetVariable( 'popup_text_1', 'done!' )
            
            job_key.Finish()
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            job_key.Cancel()
            
        
    
    def _THREADUploadPending( self, service_key ):
        
        service = self._controller.GetServicesManager().GetService( service_key )
        
        service_name = service.GetName()
        service_type = service.GetServiceType()
        
        nums_pending = self._controller.Read( 'nums_pending' )
        
        info = nums_pending[ service_key ]
        
        initial_num_pending = sum( info.values() )
        
        result = self._controller.Read( 'pending', service_key )
        
        try:
            
            job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
            
            job_key.SetVariable( 'popup_title', 'uploading pending to ' + service_name )
            
            self._controller.pub( 'message', job_key )
            
            while result is not None:
                
                nums_pending = self._controller.Read( 'nums_pending' )
                
                info = nums_pending[ service_key ]
                
                remaining_num_pending = sum( info.values() )
                done_num_pending = initial_num_pending - remaining_num_pending
                
                job_key.SetVariable( 'popup_text_1', 'uploading to ' + service_name + ': ' + HydrusData.ConvertValueRangeToPrettyString( done_num_pending, initial_num_pending ) )
                job_key.SetVariable( 'popup_gauge_1', ( done_num_pending, initial_num_pending ) )
                
                while job_key.IsPaused() or job_key.IsCancelled():
                    
                    time.sleep( 0.1 )
                    
                    if job_key.IsCancelled():
                        
                        job_key.DeleteVariable( 'popup_gauge_1' )
                        job_key.SetVariable( 'popup_text_1', 'cancelled' )
                        
                        HydrusData.Print( job_key.ToString() )
                        
                        job_key.Delete( 5 )
                        
                        return
                        
                    
                
                try:
                    
                    if service_type in HC.REPOSITORIES:
                        
                        if isinstance( result, ClientMedia.MediaResult ):
                            
                            media_result = result
                            
                            client_files_manager = self._controller.GetClientFilesManager()
                            
                            hash = media_result.GetHash()
                            mime = media_result.GetMime()
                            
                            path = client_files_manager.GetFilePath( hash, mime )
                            
                            with open( path, 'rb' ) as f: file = f.read()
                            
                            service.Request( HC.POST, 'file', { 'file' : file } )
                            
                            ( hash, inbox, size, mime, width, height, duration, num_frames, num_words, tags_manager, locations_manager, ratings_manager ) = media_result.ToTuple()
                            
                            timestamp = HydrusData.GetNow()
                            
                            content_update_row = ( hash, size, mime, timestamp, width, height, duration, num_frames, num_words )
                            
                            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, content_update_row ) ]
                            
                        else:
                            
                            content_update_package = result
                            
                            service.Request( HC.POST, 'content_update_package', { 'update' : content_update_package } )
                            
                            content_updates = content_update_package.GetContentUpdates( for_client = True )
                            
                        
                        self._controller.WriteSynchronous( 'content_updates', { service_key : content_updates } )
                        
                    elif service_type == HC.IPFS:
                        
                        if isinstance( result, ClientMedia.MediaResult ):
                            
                            media_result = result
                            
                            hash = media_result.GetHash()
                            mime = media_result.GetMime()
                            
                            service.PinFile( hash, mime )
                            
                        else:
                            
                            ( hash, multihash ) = result
                            
                            service.UnpinFile( hash, multihash )
                            
                        
                    
                except HydrusExceptions.ServerBusyException:
                    
                    job_key.SetVariable( 'popup_text_1', service.GetName() + ' was busy. please try again in a few minutes' )
                    
                    job_key.Cancel()
                    
                    return
                    
                
                self._controller.pub( 'notify_new_pending' )
                
                time.sleep( 0.1 )
                
                self._controller.WaitUntilPubSubsEmpty()
                
                result = self._controller.Read( 'pending', service_key )
                
            
        except Exception as e:
            
            job_key.SetVariable( 'popup_text_1', service.GetName() + ' error' )
            
            job_key.Cancel()
            
            raise
            
        
        job_key.DeleteVariable( 'popup_gauge_1' )
        job_key.SetVariable( 'popup_text_1', u'upload done!' )
        
        HydrusData.Print( job_key.ToString() )
        
        job_key.Finish()
        
        job_key.Delete( 5 )
        
    
    def ClearClosedPages( self ):
        
        new_closed_pages = []
        
        now = HydrusData.GetNow()
        
        timeout = 60 * 60
        
        with self._lock:
            
            deletee_pages = []
            
            old_closed_pages = self._closed_pages
            
            self._closed_pages = []
            
            for ( time_closed, index, name, page ) in old_closed_pages:
                
                if time_closed + timeout < now: deletee_pages.append( page )
                else: self._closed_pages.append( ( time_closed, index, name, page ) )
                
            
            if len( old_closed_pages ) != len( self._closed_pages ): self._controller.pub( 'notify_new_undo' )
            
        
        self._DestroyPages( deletee_pages )
        
    
    def CurrentlyBusy( self ):
        
        return self._loading_session
        
    
    def EventClose( self, event ):
        
        if not event.CanVeto():
            
            HydrusGlobals.emergency_exit = True
            
        
        exit_allowed = self.Exit()
        
        if not exit_allowed:
            
            event.Veto()
            
        
    
    def EventFocus( self, event ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None:
            
            page.SetMediaFocus()
            
        
    
    def EventFrameNewPage( self, event ):
        
        self._ChooseNewPage()
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'account_info': self._AccountInfo( data )
            elif command == 'auto_repo_setup': self._AutoRepoSetup()
            elif command == 'auto_server_setup': self._AutoServerSetup()
            elif command == 'backup_service': self._BackupService( data )
            elif command == 'close_page': self._CloseCurrentPage()
            elif command == 'delete_gui_session':
                
                self._controller.Write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION, data )
                
                self._controller.pub( 'notify_new_sessions' )
                
            elif command == 'fetch_ip': self._FetchIP( data )
            elif command == 'force_idle_mode':
                
                self._controller.ForceIdle()
                
            elif command == 'load_gui_session': self._LoadGUISession( data )
            elif command == 'manage_account_types': self._ManageAccountTypes( data )
            elif command == 'manage_boorus': self._ManageBoorus()
            elif command == 'manage_parsing_scripts': self._ManageParsingScripts()
            elif command == 'manage_pixiv_account': self._ManagePixivAccount()
            elif command == 'manage_server_services': self._ManageServer( data )
            elif command == 'manage_services': self._ManageServices()
            elif command == 'manage_subscriptions': self._ManageSubscriptions()
            elif command == 'manage_tag_censorship': self._ManageTagCensorship()
            elif command == 'manage_tag_parents': self._ManageTagParents()
            elif command == 'manage_tag_siblings': self._ManageTagSiblings()
            elif command == 'manage_upnp': self._ManageUPnP()
            elif command == 'modify_account': self._ModifyAccount( data )
            elif command == 'new_accounts': self._GenerateNewAccounts( data )
            elif command == 'new_import_booru': self._NewPageImportBooru()
            elif command == 'new_import_gallery':
                
                site_type = data
                
                gallery_identifier = ClientDownloading.GalleryIdentifier( site_type )
                
                self._NewPageImportGallery( gallery_identifier )
                
            elif command == 'new_import_page_of_images': self._NewPageImportPageOfImages()
            elif command == 'new_import_thread_watcher': self._NewPageImportThreadWatcher()
            elif command == 'new_import_urls': self._NewPageImportURLs()
            elif command == 'new_page':
                
                self._ChooseNewPage()
                
            elif command == 'new_page_query': self._NewPageQuery( data )
            elif command == 'news': self._News( data )
            elif command == 'pause_export_folders_sync': self._PauseSync( 'export_folders' )
            elif command == 'pause_import_folders_sync': self._PauseSync( 'import_folders' )
            elif command == 'pause_repo_sync': self._PauseSync( 'repo' )
            elif command == 'pause_subs_sync': self._PauseSync( 'subs' )
            elif command == 'petitions': self._NewPagePetitions( data )
            elif command == 'post_news': self._PostNews( data )
            elif command == 'pubsub_profile_mode':
                
                HydrusGlobals.pubsub_profile_mode = not HydrusGlobals.pubsub_profile_mode
                
            elif command == 'redo': self._controller.pub( 'redo' )
            elif command == 'refresh':
                
                self._Refresh()
                
            elif command == 'review_services': self._ReviewServices()
            elif command == 'save_gui_session': self._SaveGUISession()
            elif command == 'set_media_focus': self._SetMediaFocus()
            elif command == 'set_search_focus': self._SetSearchFocus()
            elif command == 'show_hide_splitters':
                
                self._ShowHideSplitters()
                
            elif command == 'start_ipfs_download': self._StartIPFSDownload()
            elif command == 'start_youtube_download': self._StartYoutubeDownload()
            elif command == 'stats': self._Stats( data )
            elif command == 'synchronised_wait_switch': self._SetSynchronisedWait()
            elif command == 'tab_menu_close_page': self._ClosePage( self._tab_right_click_index )
            elif command == 'tab_menu_rename_page': self._RenamePage( self._tab_right_click_index )
            elif command == 'undo': self._controller.pub( 'undo' )
            else: event.Skip()
            
        
    
    def EventNotebookLeftDoubleClick( self, event ):
        
        ( tab_index, flags ) = self._notebook.HitTest( ( event.GetX(), event.GetY() ) )
        
        if tab_index == wx.NOT_FOUND:
            
            self._ChooseNewPage()
            
        
    
    def EventNotebookMenu( self, event ):
        
        ( tab_index, flags ) = self._notebook.HitTest( ( event.GetX(), event.GetY() ) )
        
        if tab_index != -1:
            
            self._tab_right_click_index = tab_index
            
            menu = wx.Menu()
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'tab_menu_close_page' ), 'close page' )
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'tab_menu_rename_page' ), 'rename page' )
            
            self._controller.PopupMenu( self, menu )
            
        
    
    def EventNotebookMiddleClick( self, event ):
        
        ( tab_index, flags ) = self._notebook.HitTest( ( event.GetX(), event.GetY() ) )
        
        if tab_index == wx.NOT_FOUND:
            
            self._ChooseNewPage()
            
        else:
            
            self._ClosePage( tab_index )
            
        
    
    def EventNotebookPageChanged( self, event ):
        
        old_selection = event.GetOldSelection()
        selection = event.GetSelection()
        
        if old_selection != -1: self._notebook.GetPage( old_selection ).PageHidden()
        
        if selection != -1: self._notebook.GetPage( selection ).PageShown()
        
        self._RefreshStatusBar()
        
        event.Skip( True )
        
    
    def Exit( self, restart = False ):
        
        if not HydrusGlobals.emergency_exit:
            
            if HC.options[ 'confirm_client_exit' ]:
                
                if restart:
                    
                    text = 'Are you sure you want to restart the client? (Will auto-yes in 15 seconds)'
                    
                else:
                    
                    text = 'Are you sure you want to exit the client? (Will auto-yes in 15 seconds)'
                    
                
                with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
                    
                    call_later = wx.CallLater( 15000, dlg.EndModal, wx.ID_YES )
                    
                    if dlg.ShowModal() == wx.ID_NO:
                        
                        call_later.Stop()
                        
                        return False
                        
                    
                    call_later.Stop()
                    
                
            
            try:
                
                for page in [ self._notebook.GetPage( i ) for i in range( self._notebook.GetPageCount() ) ]:
                    
                    page.TestAbleToClose()
                    
                
            except HydrusExceptions.PermissionException:
                
                return False
                
            
        
        if restart:
            
            HydrusGlobals.restart = True
            
        
        try:
            
            if not self._loading_session:
                
                self._SaveGUISession( 'last session' )
                
            
            self._message_manager.CleanBeforeDestroy()
            
            self._message_manager.Hide()
            
            for page in [ self._notebook.GetPage( i ) for i in range( self._notebook.GetPageCount() ) ]: page.CleanBeforeDestroy()
            
            page = self._notebook.GetCurrentPage()
            
            if page is not None:
                
                ( HC.options[ 'hpos' ], HC.options[ 'vpos' ] ) = page.GetSashPositions()
                
            
            ClientGUITopLevelWindows.SaveTLWSizeAndPosition( self, self._frame_key )
            
            self._controller.WriteSynchronous( 'save_options', HC.options )
            
            self._controller.WriteSynchronous( 'serialisable', self._new_options )
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
        
        self.Hide()
        
        if HydrusGlobals.emergency_exit:
            
            self._controller.Exit()
            
        else:
            
            wx.CallAfter( self._controller.Exit )
            
        
        self.Destroy()
        
        return True
        
    
    def GetCurrentPage( self ):
        
        return self._notebook.GetCurrentPage()
        
    
    def ImportFiles( self, paths ):
        
        paths = [ HydrusData.ToUnicode( path ) for path in paths ]
        
        self._ImportFiles( paths )
        
    
    def NewPageImportBooru( self ):
        
        self._NewPageImportBooru()
        
    
    def NewPageImportGallery( self, site_type ):
        
        gallery_identifier = ClientDownloading.GalleryIdentifier( site_type )
        
        self._NewPageImportGallery( gallery_identifier )
        
    
    def NewPageImportHDD( self, paths, import_file_options, paths_to_tags, delete_after_success ):
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportHDD( paths, import_file_options, paths_to_tags, delete_after_success )
        
        self._NewPage( 'import', management_controller )
        
    
    def NewPageImportPageOfImages( self ): self._NewPageImportPageOfImages()
    
    def NewPageImportThreadWatcher( self ): self._NewPageImportThreadWatcher()
    
    def NewPageImportURLs( self ): self._NewPageImportURLs()
    
    def NewPagePetitions( self, service_key ): self._NewPagePetitions( service_key )
    
    def NewPageQuery( self, service_key, initial_media_results = None, initial_predicates = None ):
        
        if initial_media_results is None: initial_media_results = []
        if initial_predicates is None: initial_predicates = []
        
        self._NewPageQuery( service_key, initial_media_results = initial_media_results, initial_predicates = initial_predicates )
        
    
    def NewPageThreadDumper( self, hashes ):
        
        with ClientGUIDialogs.DialogSelectImageboard( self ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                imageboard = dlg.GetImageboard()
                
                pass
                
            
        
    
    def NewSimilarTo( self, file_service_key, hash, hamming_distance ):
        
        initial_predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, ( hash, hamming_distance ) ) ]
        
        self._NewPageQuery( file_service_key, initial_predicates = initial_predicates )
        
    
    def NotifyNewOptions( self ):
        
        self.RefreshAcceleratorTable()
        
        self.RefreshMenu( 'services' )
        
    
    def NotifyNewPending( self ): self.RefreshMenu( 'pending' )
    
    def NotifyNewPermissions( self ):
        
        self.RefreshMenu( 'pages' )
        self.RefreshMenu( 'services' )
        
    
    def NotifyNewServices( self ):
        
        self.RefreshMenu( 'pages' )
        self.RefreshMenu( 'services' )
        
    
    def NotifyNewSessions( self ): self.RefreshMenu( 'pages' )
    
    def NotifyNewUndo( self ): self.RefreshMenu( 'undo' )
    
    def PageDeleted( self, page_key ):
        
        with self._lock:
            
            return page_key in self._deleted_page_keys
            
        
    
    def PageHidden( self, page_key ):
        
        with self._lock:
            
            for ( time_closed, index, name, page ) in self._closed_pages:
                
                try:
                    
                    if page.GetPageKey() == page_key:
                        
                        return True
                    
                except wx.PyDeadObjectError:
                    
                    # page is dead, being cleaned up--it probably just called itself during exit, asking if it should be playing video or w/e
                    
                    return True
                    
                
            
        
        return False
        
    
    def RefreshAcceleratorTable( self ):
        
        interested_actions = [ 'archive', 'inbox', 'close_page', 'filter', 'manage_ratings', 'manage_tags', 'new_page', 'refresh', 'set_media_focus', 'set_search_focus', 'show_hide_splitters', 'synchronised_wait_switch', 'undo', 'redo' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    def RefreshMenu( self, name ):
        
        db_going_to_hang_if_we_hit_it = HydrusGlobals.client_controller.DBCurrentlyDoingJob()
        
        if db_going_to_hang_if_we_hit_it:
            
            wx.CallLater( 2500, self.RefreshMenu, name )
            
            return
            
        
        ( menu, label, show ) = self._GenerateMenuInfo( name )
        
        if HC.PLATFORM_OSX:
            
            menu.SetTitle( label ) # causes bugs in os x if this is not here
            
        
        ( old_menu, old_label, old_show ) = self._menus[ name ]
        
        if old_show:
            
            old_menu_index = self._menubar.FindMenu( old_label )
            
            if show:
                
                self._menubar.Replace( old_menu_index, menu, label )
                
            else:
                
                self._menubar.Remove( old_menu_index )
                
            
        else:
            
            if show:
                
                insert_index = 0
                
                for temp_name in MENU_ORDER:
                    
                    if temp_name == name: break
                    
                    ( temp_menu, temp_label, temp_show ) = self._menus[ temp_name ]
                    
                    if temp_show:
                        
                        insert_index += 1
                        
                    
                
                self._menubar.Insert( insert_index, menu, label )
                
            
        
        self._menus[ name ] = ( menu, label, show )
        
        ClientGUIMenus.DestroyMenu( old_menu )
        
    
    def RefreshStatusBar( self ):
        
        self._RefreshStatusBar()
        
    
    def SaveLastSession( self ):
        
        if HC.options[ 'default_gui_session' ] == 'last session':
            
            self._SaveGUISession( 'last session' )
            
        
        wx.CallLater( 5 * 60 * 1000, self.SaveLastSession )
        
    
    def SetMediaFocus( self ): self._SetMediaFocus()
    
    def SyncToTagArchive( self, hta_path, tag_service_key, file_service_key, adding, namespaces, hashes = None ):
        
        self._controller.CallToThread( self._THREADSyncToTagArchive, hta_path, tag_service_key, file_service_key, adding, namespaces, hashes )
        
    
    '''
class FrameComposeMessage( ClientGUITopLevelWindows.Frame ):
    
    def __init__( self, empty_draft_message ):
        
        ClientGUITopLevelWindows.Frame.__init__( self, None, HC.app.PrepStringForDisplay( 'Compose Message' ) )
        
        self.SetInitialSize( ( 920, 600 ) )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._draft_panel = ClientGUIMessages.DraftPanel( self, empty_draft_message )
        
        vbox.AddF( self._draft_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.Show( True )
        
        HC.pubsub.sub( self, 'DeleteConversation', 'delete_conversation_gui' )
        HC.pubsub.sub( self, 'DeleteDraft', 'delete_draft_gui' )
        
    
    def DeleteConversation( self, conversation_key ):
        
        if self._draft_panel.GetConversationKey() == conversation_key: self.Close()
        
    
    def DeleteDraft( self, draft_key ):
        
        if draft_key == self._draft_panel.GetDraftKey(): self.Close()
        
    '''
class FrameSplash( wx.Frame ):
    
    WIDTH = 420
    HEIGHT = 250
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        style = wx.FRAME_NO_TASKBAR
        
        wx.Frame.__init__( self, None, style = style, title = 'hydrus client' )
        
        self._dirty = True
        self._title_text = ''
        self._status_text = ''
        
        self._bmp = wx.EmptyBitmap( self.WIDTH, self.HEIGHT, 24 )
        
        self.SetSize( ( self.WIDTH, self.HEIGHT ) )
        
        self.Center()
        
        self._last_drag_coordinates = None
        self._total_drag_delta = ( 0, 0 )
        self._initial_position = self.GetPosition()
        
        # this is 124 x 166
        self._hydrus = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'hydrus_splash.png' ) )
        
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_MOTION, self.EventDrag )
        self.Bind( wx.EVT_LEFT_DOWN, self.EventDragBegin )
        self.Bind( wx.EVT_LEFT_UP, self.EventDragEnd )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
        self.Show( True )
        
        self._controller.sub( self, 'SetTitleText', 'splash_set_title_text' )
        self._controller.sub( self, 'SetStatusText', 'splash_set_status_text' )
        self._controller.sub( self, 'SetStatusTextNoLog', 'splash_set_status_text_no_log' )
        self._controller.sub( self, 'Destroy', 'splash_destroy' )
        
        self.Raise()
        
    
    def _Redraw( self, dc ):
        
        dc.SetBackground( wx.Brush( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) ) )
        
        dc.Clear()
        
        x = ( self.WIDTH - 124 ) / 2
        y = 15
        
        dc.DrawBitmap( self._hydrus, x, y )
        
        dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
        
        y += 166 + 15
        
        ( width, height ) = dc.GetTextExtent( self._title_text )
        
        text_gap = ( self.HEIGHT - y - height * 2 ) / 3
        
        x = ( self.WIDTH - width ) / 2
        y += text_gap
        
        dc.DrawText( self._title_text, x, y )
        
        y += height + text_gap
        
        ( width, height ) = dc.GetTextExtent( self._status_text )
        
        x = ( self.WIDTH - width ) / 2
        
        dc.DrawText( self._status_text, x, y )
        
        
    
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
    
    def EventPaint( self, event ):
        
        dc = wx.BufferedPaintDC( self, self._bmp )
        
        if self._dirty:
            
            self._Redraw( dc )
            
        
    
    def SetStatusText( self, text, print_to_log = True ):
        
        if print_to_log:
            
            HydrusData.Print( text )
            
        
        self._status_text = text
        
        self._dirty = True
        
        self.Refresh()
        
    
    def SetTitleText( self, text, print_to_log = True ):
        
        if print_to_log:
            
            HydrusData.Print( text )
            
        
        self._title_text = text
        
        self._dirty = True
        
        self.Refresh()
        
    
