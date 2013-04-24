import httplib
import HydrusConstants as HC
import ClientConstants as CC
import ClientConstantsMessages
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIMessages
import ClientGUIPages
import os
import random
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
import wx

# timers

ID_TIMER_UPDATES = wx.NewId()

# Sizer Flags

FLAGS_NONE = wx.SizerFlags( 0 )

FLAGS_SMALL_INDENT = wx.SizerFlags( 0 ).Border( wx.ALL, 2 )

FLAGS_EXPAND_PERPENDICULAR = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_BOTH_WAYS = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Expand()

FLAGS_EXPAND_SIZER_PERPENDICULAR = wx.SizerFlags( 0 ).Expand()
FLAGS_EXPAND_SIZER_BOTH_WAYS = wx.SizerFlags( 2 ).Expand()

FLAGS_BUTTON_SIZERS = wx.SizerFlags( 0 ).Align( wx.ALIGN_RIGHT )
FLAGS_LONE_BUTTON = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_RIGHT )

FLAGS_MIXED = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

class FrameGUI( ClientGUICommon.Frame ):
    
    def __init__( self ):
        
        ClientGUICommon.Frame.__init__( self, None, title = wx.GetApp().PrepStringForDisplay( 'Hydrus Client' ) )
        
        self.SetDropTarget( ClientGUICommon.FileDropTarget( self.ImportFiles ) )
        
        self._statusbar = self.CreateStatusBar()
        self._statusbar.SetFieldsCount( 4 )
        self._statusbar.SetStatusWidths( [ -1, 400, 200, 200 ] )
        
        self._statusbar_media = ''
        self._statusbar_service = ''
        self._statusbar_inbox = ''
        self._statusbar_downloads = ''
        
        self.SetIcon( wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO ) )
        
        self.SetMinSize( ( 920, 600 ) )
        
        self.Maximize()
        
        self._notebook = wx.Notebook( self )
        self._notebook.Bind( wx.EVT_MIDDLE_DOWN, self.EventNotebookMiddleClick )
        self._notebook.Bind( wx.EVT_RIGHT_DCLICK, self.EventNotebookMiddleClick )
        self._notebook.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventNotebookPageChanged )
        
        wx.GetApp().SetTopWindow( self )
        
        self.RefreshAcceleratorTable()
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        self.Bind( wx.EVT_CLOSE, self.EventExit )
        self.Bind( wx.EVT_SET_FOCUS, self.EventFocus )
        
        HC.pubsub.sub( self, 'NewCompose', 'new_compose_frame' )
        HC.pubsub.sub( self, 'NewPageImportBooru', 'new_page_import_booru' )
        HC.pubsub.sub( self, 'NewPageImportGallery', 'new_page_import_gallery' )
        HC.pubsub.sub( self, 'NewPageImportHDD', 'new_hdd_import' )
        HC.pubsub.sub( self, 'NewPageImportThreadWatcher', 'new_page_import_thread_watcher' )
        HC.pubsub.sub( self, 'NewPageImportURL', 'new_page_import_url' )
        HC.pubsub.sub( self, 'NewPageMessages', 'new_page_messages' )
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
        HC.pubsub.sub( self, 'SetDownloadsStatus', 'downloads_status' )
        HC.pubsub.sub( self, 'SetInboxStatus', 'inbox_status' )
        HC.pubsub.sub( self, 'SetServiceStatus', 'service_status' )
        
        self.RefreshMenuBar()
        
        self._RefreshStatusBar()
        
        self.Show( True )
        
        wx.CallAfter( self._NewPageQuery, HC.LOCAL_FILE_SERVICE_IDENTIFIER )
        
    
    def _THREADUploadPending( self, service_identifier, job_key, cancel_event ):
        
        # old:
        
        #wx.GetApp().Write( 'upload_pending', service_identifier, job_key, cancel_event )
        
        #return
        
        # new
        
        try:
            
            HC.pubsub.pub( 'progress_update', job_key, 0, 4, u'gathering pending and petitioned' )
            
            result = wx.GetApp().Read( 'pending', service_identifier )
            
            service_type = service_identifier.GetType()
            
            service = wx.GetApp().Read( 'service', service_identifier )
            
            if service_type == HC.TAG_REPOSITORY:
                
                ( mappings_object, petitions_object ) = result
                
                if len( mappings_object ) > 0 or len( petitions_object ) > 0:
                    
                    HC.pubsub.pub( 'progress_update', job_key, 1, 4, u'connecting to repository' )
                    
                    connection = service.GetConnection()
                    
                    if len( mappings_object ) > 0:
                        
                        HC.pubsub.pub( 'progress_update', job_key, 2, 4, u'posting new mappings' )
                        
                        try: connection.Post( 'mappings', mappings = mappings_object )
                        except Exception as e: raise Exception( 'Encountered an error while uploading public_mappings:' + os.linesep + unicode( e ) )
                        
                    
                    if len( petitions_object ) > 0:
                        
                        HC.pubsub.pub( 'progress_update', job_key, 3, 4, u'posting new petitions' )
                        
                        try: connection.Post( 'petitions', petitions = petitions_object )
                        except Exception as e: raise Exception( 'Encountered an error while uploading petitions:' + os.linesep + unicode( e ) )
                        
                    
                    num_mappings = sum( [ len( hashes ) for ( tag, hashes ) in mappings_object ] )
                    num_deleted_mappings = sum( [ len( hashes ) for ( reason, tag, hashes ) in petitions_object ] )
                    
                    HC.pubsub.pub( 'log_message', 'upload mappings', 'uploaded ' + HC.ConvertIntToPrettyString( num_mappings ) + ' mappings to and deleted ' + HC.ConvertIntToPrettyString( num_deleted_mappings ) + ' mappings from ' + service_identifier.GetName() )
                    
                    content_updates = []
                    
                    content_updates += [ HC.ContentUpdate( HC.CONTENT_UPDATE_ADD, service_identifier, hashes, info = tag ) for ( tag, hashes ) in mappings_object ]
                    content_updates += [ HC.ContentUpdate( HC.CONTENT_UPDATE_DELETE, service_identifier, hashes, info = tag ) for ( reason, tag, hashes ) in petitions_object ]
                    
                    wx.GetApp().Write( 'content_updates', content_updates )
                    
                
            elif service_type == HC.FILE_REPOSITORY:
                
                ( uploads, petitions_object ) = result
                
                ( num_uploads, num_petitions ) = ( len( uploads ), len( petitions_object ) )
                
                if num_uploads > 0 or num_petitions > 0:
                    
                    HC.pubsub.pub( 'progress_update', job_key, 1, num_uploads + 3, u'connecting to repository' )
                    
                    connection = service.GetConnection()
                    
                    good_hashes = []
                    
                    if num_uploads > 0:
                        
                        error_messages = set()
                        
                        for ( index, hash ) in enumerate( uploads ):
                            
                            HC.pubsub.pub( 'progress_update', job_key, index + 2, num_uploads + 3, u'Uploading file ' + HC.ConvertIntToPrettyString( index + 1 ) + ' of ' + HC.ConvertIntToPrettyString( num_uploads ) )
                            
                            if cancel_event.isSet(): break
                            
                            try:
                                
                                file = wx.GetApp().Read( 'file', hash )
                                
                                connection.Post( 'file', file = file )
                                
                                good_hashes.append( hash )
                                
                            except Exception as e:
                                
                                message = 'Error: ' + unicode( e )
                                
                                HC.pubsub.pub( 'progress_update', job_key, num_uploads + 1, num_uploads + 3, message )
                                
                                print( message )
                                
                                time.sleep( 1 )
                                
                            
                        
                        HC.pubsub.pub( 'progress_update', job_key, num_uploads + 1, num_uploads + 3, u'saving changes to local database' )
                        
                    
                    if num_petitions > 0:
                        
                        try:
                            
                            HC.pubsub.pub( 'progress_update', job_key, num_uploads + 2, num_uploads + 3, u'uploading petitions' )
                            
                            connection.Post( 'petitions', petitions = petitions_object )
                            
                        except Exception as e: raise Exception( 'Encountered an error while trying to uploads petitions to '+ service_name + ':' + os.linesep + unicode( e ) )
                        
                    
                    HC.pubsub.pub( 'log_message', 'upload files', 'uploaded ' + HC.ConvertIntToPrettyString( num_uploads ) + ' files to and deleted ' + HC.ConvertIntToPrettyString( num_petitions ) + ' files from ' + service_identifier.GetName() )
                    
                    content_updates = []
                    
                    content_updates.append( HC.ContentUpdate( HC.CONTENT_UPDATE_ADD, service_identifier, good_hashes ) )
                    content_updates.append( HC.ContentUpdate( HC.CONTENT_UPDATE_DELETE, service_identifier, petitions_object.GetHashes() ) )
                    
                    wx.GetApp().Write( 'content_updates', content_updates )
                    
                
            
        except Exception as e:
            
            print( traceback.format_exc() )
            
            HC.pubsub.pub( 'exception', unicode( e ) )
            
        
        HC.pubsub.pub( 'progress_update', job_key, 4, 4, u'done!' )
        
        HC.pubsub.pub( 'notify_new_pending' )
        
    
    def _AboutWindow( self ):
        
        aboutinfo = wx.AboutDialogInfo()
        
        aboutinfo.SetIcon( wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO ) )
        aboutinfo.SetName( 'hydrus client' )
        aboutinfo.SetVersion( str( HC.SOFTWARE_VERSION ) )
        aboutinfo.SetDescription( CC.CLIENT_DESCRIPTION )
        
        with open( HC.BASE_DIR + os.path.sep + 'license.txt', 'rb' ) as f: license = f.read()
        
        aboutinfo.SetLicense( license )
        
        aboutinfo.SetDevelopers( [ 'Anonymous' ] )
        aboutinfo.SetWebSite( 'http://hydrus.x10.mx/' )
        
        wx.AboutBox( aboutinfo )
        
    
    def _AccountInfo( self, service_identifier ):
        
        with wx.TextEntryDialog( self, 'Access key' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    subject_access_key = dlg.GetValue().decode( 'hex' )
                    
                    service = wx.GetApp().Read( 'service', service_identifier )
                    
                    connection = service.GetConnection()
                    
                    account_info = connection.Get( 'account_info', subject_access_key = subject_access_key.encode( 'hex' ) )
                    
                    wx.MessageBox( str( account_info ) )
                    
                except Exception as e: wx.MessageBox( unicode( e ) )
                
            
        
    
    def _AutoRepoSetup( self ):
        
        message = 'This will attempt to set up your client with my repositories\' credentials, letting you tag on the public tag repository and see some files.'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                try:
                    
                    edit_log = []
                    
                    tag_repo_identifier = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.TAG_REPOSITORY, 'public tag repository' )
                    tag_repo_credentials = CC.Credentials( 'hydrus.no-ip.org', 45871, '4a285629721ca442541ef2c15ea17d1f7f7578b0c3f4f5f2a05f8f0ab297786f'.decode( 'hex' ) )
                    
                    edit_log.append( ( 'add', ( tag_repo_identifier, tag_repo_credentials, None ) ) )
                    
                    file_repo_identifier = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.FILE_REPOSITORY, 'read-only art file repository' )
                    file_repo_credentials = CC.Credentials( 'hydrus.no-ip.org', 45872, '8f8a3685abc19e78a92ba61d84a0482b1cfac176fd853f46d93fe437a95e40a5'.decode( 'hex' ) )
                    
                    edit_log.append( ( 'add', ( file_repo_identifier, file_repo_credentials, None ) ) )
                    
                    wx.GetApp().Write( 'update_services', edit_log )
                    
                    wx.MessageBox( 'Done!' )
                    
                except: wx.MessageBox( traceback.format_exc() )
                
            
        
    
    def _AutoServerSetup( self ):
        
        message = 'This will attempt to start the server in the same install directory as this client, initialise it, and store the resultant admin accounts.'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                try:
                    
                    try:
                        
                        connection = httplib.HTTPConnection( '127.0.0.1', HC.DEFAULT_SERVER_ADMIN_PORT )
                        
                        connection.connect()
                        
                        connection.close()
                        
                        already_running = True
                        
                    except:
                        
                        already_running = False
                        
                    
                    if already_running:
                        
                        message = 'The server appears to be already running. Either that, or something else is using port ' + str( HC.DEFAULT_SERVER_ADMIN_PORT ) + '.' + os.linesep + 'Would you like to try to initialise the server that is already running?'
                        
                        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                            
                            if dlg.ShowModal() == wx.ID_NO: return
                            
                        
                    else:
                        
                        try:
                            
                            my_scriptname = sys.argv[0]
                            
                            if my_scriptname.endswith( 'pyw' ): subprocess.Popen( [ 'pythonw', HC.BASE_DIR + os.path.sep + 'server.pyw' ] )
                            else:
                                
                                # The problem here is that, for mystical reasons, a PyInstaller exe can't launch another using subprocess, so we do it via explorer.
                                
                                subprocess.Popen( [ 'explorer', HC.BASE_DIR + os.path.sep + 'server.exe' ] )
                                
                            
                            time.sleep( 5 ) # give it time to init its db
                            
                        except:
                            
                            wx.MessageBox( 'I tried to start the server, but something failed!' )
                            wx.MessageBox( traceback.format_exc() )
                            return
                            
                        
                    
                    edit_log = []
                    
                    admin_service_identifier = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.SERVER_ADMIN, 'local server admin' )
                    admin_service_credentials = CC.Credentials( '127.0.0.1', HC.DEFAULT_SERVER_ADMIN_PORT, '' )
                    
                    edit_log.append( ( 'add', ( admin_service_identifier, admin_service_credentials, None ) ) )
                    
                    wx.GetApp().Write( 'update_services', edit_log )
                    
                    i = 0
                    
                    while True:
                        
                        time.sleep( i + 1 )
                        
                        try:
                            
                            service = wx.GetApp().Read( 'service', admin_service_identifier )
                            
                            break
                            
                        except: pass
                        
                        i += 1
                        
                        if i > 5:
                            
                            wx.MessageBox( 'For some reason, I could not add the new server to the db! Perhaps it is very busy. Please contact the administrator, or sort it out yourself!' )
                            
                            return
                            
                        
                    
                    connection = service.GetConnection()
                    
                    connection.Get( 'init' )
                    
                    edit_log = []
                    
                    tag_service_identifier = HC.ServerServiceIdentifier( HC.TAG_REPOSITORY, HC.DEFAULT_SERVICE_PORT )
                    file_service_identifier = HC.ServerServiceIdentifier( HC.FILE_REPOSITORY, HC.DEFAULT_SERVICE_PORT + 1 )
                    
                    edit_log.append( ( HC.ADD, tag_service_identifier ) )
                    edit_log.append( ( HC.ADD, file_service_identifier ) )
                    
                    connection.Post( 'services_modification', edit_log = edit_log )
                    
                    wx.GetApp().Write( 'update_server_services', admin_service_identifier, edit_log )
                    
                    wx.MessageBox( 'Done! Check services->review services to see your new server and its services.' )
                    
                except: wx.MessageBox( traceback.format_exc() )
                
            
        
    
    def _BackupService( self, service_identifier ):
        
        message = 'This will tell the service to lock and copy its database files. It will not be able to serve any requests until the operation is complete.'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                service = wx.GetApp().Read( 'service', service_identifier )
                
                connection = service.GetConnection()
                
                with wx.BusyCursor(): connection.Post( 'backup' )
                
                wx.MessageBox( 'Done!' )
                
            
        
    
    def _CloseCurrentPage( self ):
        
        selection = self._notebook.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            page = self._notebook.GetPage( selection )
            
            try: page.TryToClose()
            except: return
            
            self._notebook.DeletePage( selection )
            
        
    
    def _DeletePending( self, service_identifier ):
        
        try:
            
            with ClientGUIDialogs.DialogYesNo( self, 'Are you sure you want to delete the pending data for ' + service_identifier.GetName() + '?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES: wx.GetApp().Write( 'delete_pending', service_identifier )
                
            
        except: wx.MessageBox( traceback.format_exc() )
        
    
    def _News( self, service_identifier ):
        
        try: 
            
            with ClientGUIDialogs.DialogNews( self, service_identifier ) as dlg: dlg.ShowModal()
            
        except: wx.MessageBox( traceback.format_exc() )
        
    
    def _Stats( self, service_identifier ):
        
        try:
            
            service = wx.GetApp().Read( 'service', service_identifier )
            
            connection = service.GetConnection()
            
            stats = connection.Get( 'stats' )
            
            wx.MessageBox( str( stats ) )
            
        except Exception as e: wx.MessageBox( unicode( e ) )
        
    
    def _EditServices( self ):
        
        original_pause_status = self._options[ 'pause_repo_sync' ]
        
        self._options[ 'pause_repo_sync' ] = True
        
        try:
            
            with ClientGUIDialogs.DialogManageServices( self ) as dlg: dlg.ShowModal()
            
        except: wx.MessageBox( traceback.format_exc() )
        
        self._options[ 'pause_repo_sync' ] = original_pause_status
        
    
    def _FetchIP( self, service_identifier ):
        
        with wx.TextEntryDialog( self, 'File Hash' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try:
                    
                    hash = dlg.GetValue().decode( 'hex' )
                    
                    service = wx.GetApp().Read( 'service', service_identifier )
                    
                    connection = service.GetConnection()
                    
                    with wx.BusyCursor(): ( ip, timestamp ) = connection.Get( 'ip', hash = hash.encode( 'hex' ) )
                    
                    message = 'File Hash: ' + hash.encode( 'hex' ) + os.linesep + 'Uploader\'s IP: ' + ip + os.linesep + 'Upload Time (GMT): ' + time.asctime( time.gmtime( int( timestamp ) ) )
                    
                    print( message )
                    
                    wx.MessageBox( message + os.linesep + 'This has been written to the log.' )
                    
                except Exception as e:
                    wx.MessageBox( traceback.format_exc() )
                    wx.MessageBox( unicode( e ) )
                
            
        
    
    def _ImportFiles( self, paths = [] ):
        
        try:
            
            with ClientGUIDialogs.DialogSelectLocalFiles( self, paths ) as dlg: dlg.ShowModal()
            
        except Exception as e:
            
            wx.MessageBox( traceback.format_exc() )
            wx.MessageBox( unicode( e ) )
        
    
    def _Manage4chanPass( self ):
        
        try:
            
            with ClientGUIDialogs.DialogManage4chanPass( self ) as dlg: dlg.ShowModal()
            
        except Exception as e: wx.MessageBox( unicode( e ) )
        
    
    def _ManageAccountTypes( self, service_identifier ):
        
        try:
            
            with ClientGUIDialogs.DialogManageAccountTypes( self, service_identifier ) as dlg: dlg.ShowModal()
            
        except Exception as e: wx.MessageBox( unicode( e ) )
        
    
    def _ManageBoorus( self ):
        
        try:
            
            with ClientGUIDialogs.DialogManageBoorus( self ) as dlg: dlg.ShowModal()
            
        except Exception as e: wx.MessageBox( unicode( e ) + traceback.format_exc() )
        
    
    def _ManageContacts( self ):
        
        try:
            
            with ClientGUIDialogs.DialogManageContacts( self ) as dlg: dlg.ShowModal()
            
        except Exception as e: wx.MessageBox( unicode( e ) + traceback.format_exc() )
        
    
    def _ManageImageboards( self ):
        
        try:
            
            with ClientGUIDialogs.DialogManageImageboards( self ) as dlg: dlg.ShowModal()
            
        except Exception as e: wx.MessageBox( unicode( e ) + traceback.format_exc() )
        
    
    def _ManageOptions( self, service_identifier ):
        
        try:
            
            if service_identifier.GetType() == HC.LOCAL_FILE:
                
                with ClientGUIDialogs.DialogManageOptionsLocal( self ) as dlg: dlg.ShowModal()
                
            else:
                
                if service_identifier.GetType() == HC.FILE_REPOSITORY:
                    
                    with ClientGUIDialogs.DialogManageOptionsFileRepository( self, service_identifier ) as dlg: dlg.ShowModal()
                    
                elif service_identifier.GetType() == HC.TAG_REPOSITORY:
                    
                    with ClientGUIDialogs.DialogManageOptionsTagRepository( self, service_identifier ) as dlg: dlg.ShowModal()
                    
                elif service_identifier.GetType() == HC.MESSAGE_DEPOT:
                    
                    with ClientGUIDialogs.DialogManageOptionsMessageDepot( self, service_identifier ) as dlg: dlg.ShowModal()
                    
                elif service_identifier.GetType() == HC.SERVER_ADMIN:
                    
                    with ClientGUIDialogs.DialogManageOptionsServerAdmin( self, service_identifier ) as dlg: dlg.ShowModal()
                    
                
            
        except Exception as e: wx.MessageBox( unicode( e ) + traceback.format_exc() )
        
    
    def _ManagePixivAccount( self ):
        
        try:
            
            with ClientGUIDialogs.DialogManagePixivAccount( self ) as dlg: dlg.ShowModal()
            
        except Exception as e: wx.MessageBox( unicode( e ) )
        
    
    def _ManageServices( self, service_identifier ):
        
        try:
            
            with ClientGUIDialogs.DialogManageServer( self, service_identifier ) as dlg: dlg.ShowModal()
            
        except Exception as e: wx.MessageBox( unicode( e ) + traceback.format_exc() )
        
    
    def _ManageSubscriptions( self ):
        
        original_pause_status = self._options[ 'pause_subs_sync' ]
        
        self._options[ 'pause_subs_sync' ] = True
        
        try:
            
            with ClientGUIDialogs.DialogManageSubscriptions( self ) as dlg: dlg.ShowModal()
            
        except Exception as e: wx.MessageBox( unicode( e ) + traceback.format_exc() )
        
        self._options[ 'pause_subs_sync' ] = original_pause_status
        
    
    def _ManageTagServicePrecedence( self ):
        
        try:
            
            with ClientGUIDialogs.DialogManageTagServicePrecedence( self ) as dlg: dlg.ShowModal()
            
        except Exception as e: wx.MessageBox( unicode( e ) + traceback.format_exc() )
        
    
    def _ModifyAccount( self, service_identifier ):
        
        service = wx.GetApp().Read( 'service', service_identifier )
        
        with wx.TextEntryDialog( self, 'Enter the access key for the account to be modified' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                try: access_key = dlg.GetValue().decode( 'hex' )
                except:
                    
                    wx.MessageBox( 'Could not parse that access key' )
                    
                    return
                    
                
                subject_identifiers = ( HC.AccountIdentifier( access_key = access_key ), )
                
                try:
                    
                    with ClientGUIDialogs.DialogModifyAccounts( self, service_identifier, subject_identifiers ) as dlg2: dlg2.ShowModal()
                    
                except Exception as e: wx.MessageBox( unicode( e ) )
                
            
        
    
    def _NewAccounts( self, service_identifier ):
        
        try:
            
            with ClientGUIDialogs.DialogInputNewAccounts( self, service_identifier ) as dlg: dlg.ShowModal()
            
        except Exception as e: wx.MessageBox( unicode( e ) )
        
    
    def _NewPageImportBooru( self ):
        
        try:
            
            with ClientGUIDialogs.DialogSelectBooru( self ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    booru = dlg.GetBooru()
                    
                    new_page = ClientGUIPages.PageImportBooru( self._notebook, booru )
                    
                    self._notebook.AddPage( new_page, booru.GetName(), select = True )
                    
                    self._notebook.SetSelection( self._notebook.GetPageCount() - 1 )
                    
                    new_page.SetSearchFocus()
                    
                
            
        except Exception as e:
            wx.MessageBox( traceback.format_exc() )
            wx.MessageBox( unicode( e ) )
        
    
    def _NewPageImportGallery( self, name ):
        
        try:
            
            if name == 'deviant art by artist': new_page = ClientGUIPages.PageImportDeviantArt( self._notebook )
            elif name == 'hentai foundry by artist': new_page = ClientGUIPages.PageImportHentaiFoundryArtist( self._notebook )
            elif name == 'hentai foundry by tags': new_page = ClientGUIPages.PageImportHentaiFoundryTags( self._notebook )
            elif name == 'giphy': new_page = ClientGUIPages.PageImportGiphy( self._notebook )
            elif name == 'pixiv by artist': new_page = ClientGUIPages.PageImportPixivArtist( self._notebook )
            elif name == 'pixiv by tag': new_page = ClientGUIPages.PageImportPixivTag( self._notebook )
            elif name == 'tumblr': new_page = ClientGUIPages.PageImportTumblr( self._notebook )
            
            self._notebook.AddPage( new_page, name, select = True )
            
            self._notebook.SetSelection( self._notebook.GetPageCount() - 1 )
            
            new_page.SetSearchFocus()
            
        except Exception as e:
            wx.MessageBox( traceback.format_exc() )
            wx.MessageBox( unicode( e ) )
        
    
    def _NewPageImportThreadWatcher( self ):
        
        try:
            
            new_page = ClientGUIPages.PageImportThreadWatcher( self._notebook )
            
            self._notebook.AddPage( new_page, 'thread watcher', select = True )
            
            self._notebook.SetSelection( self._notebook.GetPageCount() - 1 )
            
            new_page.SetSearchFocus()
            
        except Exception as e:
            wx.MessageBox( traceback.format_exc() )
            wx.MessageBox( unicode( e ) )
        
    
    def _NewPageImportURL( self ):
        
        new_page = ClientGUIPages.PageImportURL( self._notebook )
        
        self._notebook.AddPage( new_page, 'download', select = True )
        
        self._notebook.SetSelection( self._notebook.GetPageCount() - 1 )
        
        new_page.SetSearchFocus()
        
    
    def _NewPageLog( self ):
        
        new_page = ClientGUIPages.PageLog( self._notebook )
        
        self._notebook.AddPage( new_page, 'log', select = True )
        
        self._notebook.SetSelection( self._notebook.GetPageCount() - 1 )
        
    
    def _NewPageMessages( self, identity ):
        
        new_page = ClientGUIPages.PageMessages( self._notebook, identity )
        
        self._notebook.AddPage( new_page, identity.GetName() + ' messages', select = True )
        
        self._notebook.SetSelection( self._notebook.GetPageCount() - 1 )
        
        new_page.SetSearchFocus()
        
    
    def _NewPagePetitions( self, service_identifier = None ):
        
        if service_identifier is None: service_identifier = ClientGUIDialogs.SelectServiceIdentifier( service_types = HC.REPOSITORIES, permission = HC.RESOLVE_PETITIONS )
        
        if service_identifier is not None:
            
            service = wx.GetApp().Read( 'service', service_identifier )
            
            account = service.GetAccount()
            
            if not account.HasPermission( HC.RESOLVE_PETITIONS ): return
            
            self._notebook.AddPage( ClientGUIPages.PagePetitions( self._notebook, service_identifier ), service_identifier.GetName() + ' petitions', select = True )
            
        
    
    def _NewPageQuery( self, service_identifier, initial_media_results = [], initial_predicates = [] ):
        
        if service_identifier is None: service_identifier = ClientGUIDialogs.SelectServiceIdentifier( service_types = ( HC.FILE_REPOSITORY, ) )
        
        if service_identifier is not None:
            
            new_page = ClientGUIPages.PageQuery( self._notebook, service_identifier, initial_media_results = initial_media_results, initial_predicates = initial_predicates )
            
            self._notebook.AddPage( new_page, 'files', select = True )
            
            wx.CallAfter( new_page.SetSearchFocus )
            
        
    
    def _OpenExportFolder( self ):
        
        export_path = HC.ConvertPortablePathToAbsPath( self._options[ 'export_path' ] )
        
        if export_path is None: wx.MessageBox( 'Export folder is missing or not set.' )
        else:
            
            export_path = os.path.normpath( export_path ) # windows complains about those forward slashes when launching from the command line
            
            if 'Windows' in os.environ.get( 'os' ): subprocess.Popen( [ 'explorer', export_path ] )
            else: subprocess.Popen( [ 'explorer', export_path ] )
            
        
    
    def _PauseSync( self, sync_type ):
        
        if sync_type == 'repo': self._options[ 'pause_repo_sync' ] = not self._options[ 'pause_repo_sync' ]
        elif sync_type == 'subs': self._options[ 'pause_subs_sync' ] = not self._options[ 'pause_subs_sync' ]
        
        try: wx.GetApp().Write( 'save_options' )
        except: wx.MessageBox( traceback.format_exc() )
        
        self.RefreshMenuBar()
        
        HC.pubsub.pub( 'notify_new_subscriptions' ) # this pushes the daemon to restart if sleeping
        
    
    def _PostNews( self, service_identifier ):
        
        with wx.TextEntryDialog( self, 'Enter the news you would like to post.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                news = dlg.GetValue()
                
                try:
                    
                    service = wx.GetApp().Read( 'service', service_identifier )
                    
                    connection = service.GetConnection()
                    
                    with wx.BusyCursor(): connection.Post( 'news', news = news )
                    
                except Exception as e: wx.MessageBox( unicode( e ) )
                
            
        
    
    def _RefreshStatusBar( self ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is None: media_status = ''
        else: media_status = page.GetPrettyStatus()
        
        self._statusbar_media = media_status
        
        self._statusbar.SetStatusText( self._statusbar_media, number = 0 )
        self._statusbar.SetStatusText( self._statusbar_service, number = 1 )
        self._statusbar.SetStatusText( self._statusbar_inbox, number = 2 )
        self._statusbar.SetStatusText( self._statusbar_downloads, number = 3 )
        
    
    def _ReviewServices( self ):
        
        try: FrameReviewServices()
        except: wx.MessageBox( traceback.format_exc() )
        
    
    def _SetPassword( self ):
        
        message = '''You can set a password to be asked for whenever the client starts.

Though not foolproof, it will stop noobs from easily seeing your files if you leave your machine unattended.

Do not ever forget your password! If you do, you'll have to manually insert a yaml-dumped python dictionary into a sqlite database or recompile from source to regain easy access. This is not trivial.

The password is cleartext here but obscured in the entry dialog. Enter a blank password to remove.'''
        
        with wx.TextEntryDialog( self, message, 'Enter new password' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                password = dlg.GetValue()
                
                if password == '': password = None
                
                wx.GetApp().Write( 'set_password', password )
                
            
        
    
    def _SetMediaFocus( self ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None: page.SetMediaFocus()
        
    
    def _SetSearchFocus( self ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None: page.SetSearchFocus()
        
    
    def _SetSynchronisedWait( self ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None: page.SetSynchronisedWait()
        
    
    def _UploadPending( self, service_identifier ):
        
        job_key = os.urandom( 32 )
        
        if service_identifier.GetType() == HC.TAG_REPOSITORY: cancel_event = None
        else: cancel_event = threading.Event()
        
        with ClientGUIDialogs.DialogProgress( self, job_key, cancel_event ) as dlg:
            
            threading.Thread( target = self._THREADUploadPending, args = ( service_identifier, job_key, cancel_event ) ).start()
            
            dlg.ShowModal()
            
        
    
    def _VacuumDatabase( self ):
        
        message = 'This will rebuild the database, rewriting all indices and tables to be contiguous, optimising most operations. If you have a large database, it will take some time.'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES: wx.GetApp().Write( 'vacuum' )
            
        
    
    def DoFirstStart( self ):
        
        with ClientGUIDialogs.DialogFirstStart( self ) as dlg: dlg.ShowModal()
        
    
    def EventExit( self, event ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None and self.IsMaximized():
            
            ( self._options[ 'hpos' ], self._options[ 'vpos' ] ) = page.GetSashPositions()
            
            with wx.BusyCursor(): wx.GetApp().Write( 'save_options' )
            
        
        for page in [ self._notebook.GetPage( i ) for i in range( self._notebook.GetPageCount() ) ]:
            
            try: page.TryToClose()
            except: return
            
        
        self.Hide()
        
        # for some insane reason, the read makes the controller block until the writes are done!??!
            # hence the hide, to make it appear the destroy is actually happening on time
        
        wx.GetApp().MaintainDB()
        
        self.Destroy()
        
    
    def EventFocus( self, event ):
        
        page = self._notebook.GetCurrentPage()
        
        if page is not None: page.SetMediaFocus()
        
    
    def EventMenu( self, event ):
        
        action = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            try:
                
                ( command, data ) = action
                
                if command == 'account_info': self._AccountInfo( data )
                elif command == 'auto_repo_setup': self._AutoRepoSetup()
                elif command == 'auto_server_setup': self._AutoServerSetup()
                elif command == 'backup_service': self._BackupService( data )
                elif command == 'clear_caches': wx.GetApp().ClearCaches()
                elif command == 'close_page': self._CloseCurrentPage()
                elif command == 'debug_options': wx.MessageBox( str( wx.GetApp().Read( 'options' ) ) )
                elif command == 'delete_pending': self._DeletePending( data )
                elif command == 'edit_services': self._EditServices()
                elif command == 'exit': self.EventExit( event )
                elif command == 'fetch_ip': self._FetchIP( data )
                elif command == 'forum': webbrowser.open( 'http://hydrus.x10.mx/forum' )
                elif command == 'help': webbrowser.open( 'file://' + HC.BASE_DIR + '/help/index.html' )
                elif command == 'help_about': self._AboutWindow()
                elif command == 'help_shortcuts': wx.MessageBox( CC.SHORTCUT_HELP )
                elif command == 'import': self._ImportFiles()
                elif command == 'manage_4chan_pass': self._Manage4chanPass()
                elif command == 'manage_account_types': self._ManageAccountTypes( data )
                elif command == 'manage_boorus': self._ManageBoorus()
                elif command == 'manage_contacts': self._ManageContacts()
                elif command == 'manage_imageboards': self._ManageImageboards()
                elif command == 'manage_pixiv_account': self._ManagePixivAccount()
                elif command == 'manage_services': self._ManageServices( data )
                elif command == 'manage_subscriptions': self._ManageSubscriptions()
                elif command == 'manage_tag_service_precedence': self._ManageTagServicePrecedence()
                elif command == 'modify_account': self._ModifyAccount( data )
                elif command == 'new_accounts': self._NewAccounts( data )
                elif command == 'new_import_booru': self._NewPageImportBooru()
                elif command == 'new_import_thread_watcher': self._NewPageImportThreadWatcher()
                elif command == 'new_import_url': self._NewPageImportURL()
                elif command == 'new_log_page': self._NewPageLog()
                elif command == 'new_messages_page': self._NewPageMessages( data )
                elif command == 'new_page': FramePageChooser()
                elif command == 'new_page_query': self._NewPageQuery( data )
                elif command == 'news': self._News( data )
                elif command == 'open_export_folder': self._OpenExportFolder()
                elif command == 'options': self._ManageOptions( data )
                elif command == 'pause_repo_sync': self._PauseSync( 'repo' )
                elif command == 'pause_subs_sync': self._PauseSync( 'subs' )
                elif command == 'petitions': self._NewPagePetitions( data )
                elif command == 'post_news': self._PostNews( data )
                elif command == 'refresh':
                    
                    page = self._notebook.GetCurrentPage()
                    
                    if page is not None: page.RefreshQuery()
                    
                elif command == 'review_services': self._ReviewServices()
                elif command == 'show_hide_splitters':
                    
                    page = self._notebook.GetCurrentPage()
                    
                    if page is not None: page.ShowHideSplit()
                    
                elif command == 'set_password': self._SetPassword()
                elif command == 'set_media_focus': self._SetMediaFocus()
                elif command == 'set_search_focus': self._SetSearchFocus()
                elif command == 'site': webbrowser.open( 'http://hydrus.x10.mx/' )
                elif command == 'stats': self._Stats( data )
                elif command == 'synchronised_wait_switch': self._SetSynchronisedWait()
                elif command == 'tumblr': webbrowser.open( 'http://hydrus.tumblr.com/' )
                elif command == 'twitter': webbrowser.open( 'http://twitter.com/#!/hydrusnetwork' )
                elif command == 'upload_pending': self._UploadPending( data )
                elif command == 'vacuum_db': self._VacuumDatabase()
                else: event.Skip()
                
            except Exception as e:
                
                wx.MessageBox( unicode( e ) )
                wx.MessageBox( traceback.format_exc() )
                
            
        
    
    def EventNotebookMiddleClick( self, event ):
        
        ( tab_index, flags ) = self._notebook.HitTest( ( event.GetX(), event.GetY() ) )
        
        page = self._notebook.GetPage( tab_index )
        
        try: page.TryToClose()
        except: return
        
        self._notebook.DeletePage( tab_index )
        
    
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
        
        try: FrameComposeMessage( empty_draft_message )
        except: wx.MessageBox( traceback.format_exc() )
    
    def NewPageImportBooru( self ): self._NewPageImportBooru()
    
    def NewPageImportGallery( self, name ): self._NewPageImportGallery( name )
    
    def NewPageImportHDD( self, paths, **kwargs ):
        
        new_page = ClientGUIPages.PageImportHDD( self._notebook, paths, **kwargs )
        
        self._notebook.AddPage( new_page, 'import', select = True )
        
        self._notebook.SetSelection( self._notebook.GetPageCount() - 1 )
        
    
    def NewPageImportThreadWatcher( self ): self._NewPageImportThreadWatcher()
    
    def NewPageImportURL( self ): self._NewPageImportURL()
    
    def NewPageMessages( self, identity ): self._NewPageMessages( identity )
    
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
        
        interested_actions = [ 'archive', 'inbox', 'close_page', 'filter', 'ratings_filter', 'manage_ratings', 'manage_tags', 'new_page', 'refresh', 'set_media_focus', 'set_search_focus', 'show_hide_splitters', 'synchronised_wait_switch' ]
        
        entries = []
        
        for ( modifier, key_dict ) in self._options[ 'shortcuts' ].items(): entries.extend( [ ( modifier, key, CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    def RefreshMenuBar( self ):
        
        p = wx.GetApp().PrepStringForDisplay
        
        services = wx.GetApp().Read( 'services' )
        
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
        
        identities = wx.GetApp().Read( 'identities' )
        
        servers_admin = [ service for service in services if service.GetServiceIdentifier().GetType() == HC.SERVER_ADMIN ]
        
        server_admin_identifiers = [ service.GetServiceIdentifier() for service in servers_admin if service.GetAccount().HasPermission( HC.GENERAL_ADMIN ) ]
        
        nums_pending = wx.GetApp().Read( 'nums_pending' )
        
        menu = wx.MenuBar()
        
        file = wx.Menu()
        file.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'import' ), p( '&Import Files' ), p( 'Add new files to the database.' ) )
        file.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'open_export_folder' ), p( 'Open E&xport Folder' ), p( 'Open the export folder so you can easily access files you have exported.' ) )
        file.AppendSeparator()
        file.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'options', HC.LOCAL_FILE_SERVICE_IDENTIFIER ), p( '&Options' ) )
        file.AppendSeparator()
        file.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'exit' ), p( '&Exit' ) )
        
        menu.Append( file, p( '&File' ) )
        
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
        if len( identities ) > 0:
            
            for identity in identities: view.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_messages_page', identity ), p( identity.GetName() + ' Message Page' ), p( 'Open a new tab to review the messages for ' + identity.GetName() ) )
            view.AppendSeparator()
            
        view.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'new_log_page' ), p( '&New Log Page' ), p( 'Open a new tab to show recently logged events.' ) )
        
        menu.Append( view, p( '&View' ) )
        
        database = wx.Menu()
        database.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'set_password' ), p( 'Set a &Password' ), p( 'Set a password for the database so only you can access it.' ) )
        database.AppendSeparator()
        #database.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'reindex_db' ), '&reindex', 'reindex the database.' )
        database.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'vacuum_db' ), p( '&Vacuum' ), p( 'Rebuild the Database.' ) )
        database.AppendSeparator()
        database.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'clear_caches' ), p( '&Clear Caches' ), p( 'Fully clear the fullscreen, preview and thumbnail caches.' ) )
        
        menu.Append( database, p( '&Database' ) )
        
        if len( nums_pending ) > 0:
            
            pending = wx.Menu()
            
            for ( service_identifier, num_pending ) in nums_pending.items():
                
                if num_pending > 0:
                    
                    service_type = service_identifier.GetType()
                    
                    submenu = wx.Menu()
                    
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'upload_pending', service_identifier ), p( '&Upload' ), p( 'Upload ' + service_identifier.GetName() + '\'s Pending and Petitions.' ) )
                    submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'delete_pending', service_identifier ), p( '&Forget' ), p( 'Clear ' + service_identifier.GetName() + '\'s Pending and Petitions.' ) )
                    
                    pending.AppendMenu( CC.ID_NULL, p( service_identifier.GetName() + ' Pending (' + HC.ConvertIntToPrettyString( num_pending ) + ')' ), submenu )
                    
                
            
            num_pending_total = sum( nums_pending.values() )
            
            menu.Append( pending, p( '&Pending (' + HC.ConvertIntToPrettyString( num_pending_total ) + ')' ) )
            
        
        services = wx.Menu()
        
        submenu = wx.Menu()
        
        pause_repo_sync_id = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'pause_repo_sync' )
        pause_subs_sync_id = CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'pause_subs_sync' )
        
        submenu.AppendCheckItem( pause_repo_sync_id, p( '&Repositories Synchronisation' ), p( 'Pause the client\'s synchronisation with hydrus repositories.' ) )
        submenu.AppendCheckItem( pause_subs_sync_id, p( '&Subscriptions Synchronisation' ), p( 'Pause the client\'s synchronisation with website subscriptions.' ) )
        
        submenu.Check( pause_repo_sync_id, self._options[ 'pause_repo_sync' ] )
        submenu.Check( pause_subs_sync_id, self._options[ 'pause_subs_sync' ] )
        
        services.AppendMenu( CC.ID_NULL, p( 'Pause' ), submenu )
        
        services.AppendSeparator()
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'review_services' ), p( '&Review Services' ), p( 'Review your services.' ) )
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'edit_services' ), p( '&Add, Remove or Edit Services' ), p( 'Edit your services.' ) )
        if len( download_tag_service_identifiers ) > 1: services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_tag_service_precedence' ), p( '&Manage Tag Service Precedence' ), p( 'Change the order in which tag repositories\' taxonomies will be added to the database.' ) )
        services.AppendSeparator()
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_boorus' ), p( 'Manage &Boorus' ), p( 'Change the html parsing information for boorus to download from.' ) )
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_imageboards' ), p( 'Manage &Imageboards' ), p( 'Change the html POST form information for imageboards to dump to.' ) )
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_4chan_pass' ), p( 'Manage &4chan Pass' ), p( 'Set up your 4chan pass, so you can dump without having to fill in a captcha.' ) )
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_pixiv_account' ), p( 'Manage &Pixiv Account' ), p( 'Set up your pixiv username and password.' ) )
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_subscriptions' ), p( 'Manage &Subscriptions' ), p( 'Change the queries you want the client to regularly import from.' ) )
        services.AppendSeparator()
        services.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_contacts' ), p( 'Manage &Contacts and Identities' ), p( 'Change the names and addresses of the people you talk to.' ) )
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
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'options', s_i ), p( '&Options' ), p( 'Set the tag repository\'s options.' ) )
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
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'options', s_i ), p( '&Options' ), p( 'Set the file repository\'s options.' ) )
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
                
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'options', s_i ), p( '&Options' ), p( 'Set the server\'s options.' ) )
                submenu.AppendSeparator()
                submenu.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'manage_services', s_i ), p( 'Manage &Services' ), p( 'Add, edit, and delete this server\'s services.' ) )
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
        debug.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'debug_options' ), p( 'Options' ) )
        help.AppendMenu( wx.ID_NONE, p( 'Debug' ), debug )
        help.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'help_shortcuts' ), p( '&Shortcuts' ) )
        help.Append( CC.MENU_EVENT_ID_TO_ACTION_CACHE.GetId( 'help_about' ), p( '&About' ) )
        
        menu.Append( help, p( '&Help' ) )
        
        old_menu = self.GetMenuBar()
        
        self.SetMenuBar( menu )
        
        if old_menu is not None: old_menu.Destroy()
        
    
    def RefreshStatusBar( self ): self._RefreshStatusBar()
    
    def SetDownloadsStatus( self, status ):
        
        if self.IsShown():
            
            self._statusbar_downloads = status
            
            self._RefreshStatusBar()
            
        
    
    def SetInboxStatus( self, status ):
        
        if self.IsShown():
            
            self._statusbar_inbox = status
            
            self._RefreshStatusBar()
            
        
    
    def SetServiceStatus( self, status ):
        
        if self.IsShown():
            
            self._statusbar_service = status
            
            self._RefreshStatusBar()
            
        
    
class FrameComposeMessage( ClientGUICommon.Frame ):
    
    def __init__( self, empty_draft_message ):
        
        ClientGUICommon.Frame.__init__( self, None, title = wx.GetApp().PrepStringForDisplay( 'Compose Message' ) )
        
        self.SetIcon( wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO ) )
        
        self.SetInitialSize( ( 920, 600 ) )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._draft_panel = ClientGUIMessages.DraftPanel( self, empty_draft_message )
        
        vbox.AddF( self._draft_panel, FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.Show( True )
        
        HC.pubsub.sub( self, 'DeleteConversation', 'delete_conversation_gui' )
        HC.pubsub.sub( self, 'DeleteDraft', 'delete_draft_gui' )
        
    
    def DeleteConversation( self, conversation_key ):
        
        if self._draft_panel.GetConversationKey() == conversation_key: self.Destroy()
        
    
    def DeleteDraft( self, draft_key ):
        
        if draft_key == self._draft_panel.GetDraftKey(): self.Destroy()
        
    
class FramePageChooser( ClientGUICommon.Frame ):
    
    def __init__( self ):
        
        def InitialiseControls():
            
            self._button_hidden = wx.Button( self )
            self._button_hidden.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
            self._button_hidden.Hide()
            
            self._button_1 = wx.Button( self, label = '', id = 1 )
            self._button_2 = wx.Button( self, label = '', id = 2 )
            self._button_3 = wx.Button( self, label = '', id = 3 )
            self._button_4 = wx.Button( self, label = '', id = 4 )
            self._button_5 = wx.Button( self, label = '', id = 5 )
            self._button_6 = wx.Button( self, label = '', id = 6 )
            self._button_7 = wx.Button( self, label = '', id = 7 )
            self._button_8 = wx.Button( self, label = '', id = 8 )
            self._button_9 = wx.Button( self, label = '', id = 9 )
            
        
        def InitialisePanel():
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            gridbox = wx.GridSizer( 0, 3 )
            
            gridbox.AddF( self._button_1, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_2, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_3, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_4, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_5, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_6, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_7, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_8, FLAGS_EXPAND_BOTH_WAYS )
            gridbox.AddF( self._button_9, FLAGS_EXPAND_BOTH_WAYS )
            
            self.SetSizer( gridbox )
            
            self.SetInitialSize( ( 420, 210 ) )
            
        
        ClientGUICommon.Frame.__init__( self, None, title = wx.GetApp().PrepStringForDisplay( 'New Page' ) )
        
        self.Center()
        
        self.SetIcon( wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO ) )
        
        self._keycodes_to_ids = {}
        
        self._keycodes_to_ids[ wx.WXK_NUMPAD1 ] = 1
        self._keycodes_to_ids[ wx.WXK_NUMPAD2 ] = 2
        self._keycodes_to_ids[ wx.WXK_NUMPAD3 ] = 3
        self._keycodes_to_ids[ wx.WXK_NUMPAD4 ] = 4
        self._keycodes_to_ids[ wx.WXK_NUMPAD5 ] = 5
        self._keycodes_to_ids[ wx.WXK_NUMPAD6 ] = 6
        self._keycodes_to_ids[ wx.WXK_NUMPAD7 ] = 7
        self._keycodes_to_ids[ wx.WXK_NUMPAD8 ] = 8
        self._keycodes_to_ids[ wx.WXK_NUMPAD9 ] = 9
        
        self._keycodes_to_ids[ wx.WXK_UP ] = 2
        self._keycodes_to_ids[ wx.WXK_DOWN ] = 8
        self._keycodes_to_ids[ wx.WXK_LEFT ] = 4
        self._keycodes_to_ids[ wx.WXK_RIGHT ] = 6
        
        InitialiseControls()
        
        InitialisePanel()
        
        self._services = wx.GetApp().Read( 'services' )
        
        self._petition_service_identifiers = [ service.GetServiceIdentifier() for service in self._services if service.GetServiceIdentifier().GetType() in HC.REPOSITORIES and service.GetAccount().HasPermission( HC.RESOLVE_PETITIONS ) ]
        
        self._identities = wx.GetApp().Read( 'identities' )
        
        self._InitButtons( 'home' )
        
        self.Bind( wx.EVT_BUTTON, self.EventButton )
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._button_hidden.SetFocus()
        
        self.Show( True )
        
    
    def _AddEntry( self, button, entry ):
        
        id = button.GetId()
        
        self._command_dict[ id ] = entry
        
        ( entry_type, obj ) = entry
        
        if entry_type == 'menu': button.SetLabel( obj )
        elif entry_type in ( 'page_query', 'page_petitions' ):
            
            name = obj.GetName()
            
            button.SetLabel( name )
            
        elif entry_type == 'page_import_booru': button.SetLabel( 'booru' )
        elif entry_type == 'page_import_gallery': button.SetLabel( obj )
        elif entry_type == 'page_messages':
            
            name = obj.GetName()
            
            button.SetLabel( name )
            
        elif entry_type == 'page_import_thread_watcher': button.SetLabel( 'thread watcher' )
        elif entry_type == 'page_import_url': button.SetLabel( 'url' )
        
        button.Show()
        
    
    def _InitButtons( self, menu_keyword ):
        
        self._command_dict = {}
        
        if menu_keyword == 'home':
            
            entries = [ ( 'menu', 'files' ), ( 'menu', 'download' ) ]
            
            if len( self._petition_service_identifiers ) > 0: entries.append( ( 'menu', 'petitions' ) )
            
            if len( self._identities ) > 0: entries.append( ( 'menu', 'messages' ) )
            
        elif menu_keyword == 'files':
            
            file_repos = [ ( 'page_query', service_identifier ) for service_identifier in [ service.GetServiceIdentifier() for service in self._services ] if service_identifier.GetType() == HC.FILE_REPOSITORY ]
            
            entries = [ ( 'page_query', HC.LOCAL_FILE_SERVICE_IDENTIFIER ) ] + file_repos
            
        elif menu_keyword == 'download': entries = [ ( 'page_import_url', None ), ( 'page_import_thread_watcher', None ), ( 'menu', 'gallery' ) ]
        elif menu_keyword == 'gallery': entries = [ ( 'page_import_booru', None ), ( 'page_import_gallery', 'giphy' ), ( 'page_import_gallery', 'deviant art by artist' ), ( 'menu', 'hentai foundry' ), ( 'menu', 'pixiv' ), ( 'page_import_gallery', 'tumblr' ) ]
        elif menu_keyword == 'hentai foundry': entries = [ ( 'page_import_gallery', 'hentai foundry by artist' ), ( 'page_import_gallery', 'hentai foundry by tags' ) ]
        elif menu_keyword == 'pixiv': entries = [ ( 'page_import_gallery', 'pixiv by artist' ), ( 'page_import_gallery', 'pixiv by tag' ) ]
        elif menu_keyword == 'messages': entries = [ ( 'page_messages', identity ) for identity in self._identities ]
        elif menu_keyword == 'petitions': entries = [ ( 'page_petitions', service_identifier ) for service_identifier in self._petition_service_identifiers ]
        
        if len( entries ) <= 4:
            
            self._button_1.Hide()
            self._button_3.Hide()
            self._button_5.Hide()
            self._button_7.Hide()
            self._button_9.Hide()
            
            usable_buttons = [ self._button_2, self._button_4, self._button_6, self._button_8 ]
            
        elif len( entries ) <= 9: usable_buttons = [ self._button_1, self._button_2, self._button_3, self._button_4, self._button_5, self._button_6, self._button_7, self._button_8, self._button_9 ]
        else:
            
            pass # sort out a multi-page solution? maybe only if this becomes a big thing; the person can always select from the menus, yeah?
            
            usable_buttons = [ self._button_1, self._button_2, self._button_3, self._button_4, self._button_5, self._button_6, self._button_7, self._button_8, self._button_9 ]
            entries = entries[:9]
            
        
        for entry in entries: self._AddEntry( usable_buttons.pop( 0 ), entry )
        
        for button in usable_buttons: button.Hide()
        
    
    def EventButton( self, event ):
        
        id = event.GetId()
        
        if id in self._command_dict:
            
            ( entry_type, obj ) = self._command_dict[ id ]
            
            if entry_type == 'menu': self._InitButtons( obj )
            else:
                
                if entry_type == 'page_query': HC.pubsub.pub( 'new_page_query', obj )
                elif entry_type == 'page_import_booru': HC.pubsub.pub( 'new_page_import_booru' )
                elif entry_type == 'page_import_gallery': HC.pubsub.pub( 'new_page_import_gallery', obj )
                elif entry_type == 'page_import_thread_watcher': HC.pubsub.pub( 'new_page_import_thread_watcher' )
                elif entry_type == 'page_import_url': HC.pubsub.pub( 'new_page_import_url' )
                elif entry_type == 'page_messages': HC.pubsub.pub( 'new_page_messages', obj )
                elif entry_type == 'page_petitions': HC.pubsub.pub( 'new_page_petitions', obj )
                
                self.Destroy()
                
            
        
        self._button_hidden.SetFocus()
        
    
    def EventKeyDown( self, event ):
        
        if event.KeyCode in self._keycodes_to_ids.keys():
            
            id = self._keycodes_to_ids[ event.KeyCode ]
            
            new_event = wx.CommandEvent( wx.wxEVT_COMMAND_BUTTON_CLICKED, winid = id )
            
            self.ProcessEvent( new_event )
            
        elif event.KeyCode == wx.WXK_ESCAPE: self.Destroy()
        else: event.Skip()
        
    
class FrameReviewServices( ClientGUICommon.Frame ):
    
    def __init__( self ):
        
        def InitialiseControls():
            
            self._listbook = ClientGUICommon.ListBook( self )
            
            self._edit = wx.Button( self, label='add, remove or edit services' )
            self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
            
            self._ok = wx.Button( self, label='ok' )
            self._ok.Bind( wx.EVT_BUTTON, self.EventOk )
            self._ok.SetForegroundColour( ( 0, 128, 0 ) )
            
        
        def InitialisePanel():
            
            self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            vbox.AddF( self._listbook, FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._edit, FLAGS_SMALL_INDENT )
            vbox.AddF( self._ok, FLAGS_BUTTON_SIZERS )
            
            self.SetSizer( vbox )
            
            self.SetInitialSize( ( 880, 620 ) )
            
        
        ( pos_x, pos_y ) = wx.GetApp().GetGUI().GetPositionTuple()
        
        pos = ( pos_x + 25, pos_y + 50 )
        
        ClientGUICommon.Frame.__init__( self, None, title = wx.GetApp().PrepStringForDisplay( 'Review Services' ), pos = pos )
        
        self.SetIcon( wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO ) )
        
        InitialiseControls()
        
        self._InitialiseServices()
        
        InitialisePanel()
        
        self.Show( True )
        
        HC.pubsub.sub( self, 'RefreshServices', 'notify_new_services' )
        
    
    def _InitialiseServices( self ):
        
        self._listbook.DeleteAllPages()
        
        listbook_dict = {}
        
        service_identifiers = wx.GetApp().Read( 'service_identifiers' )
        
        for service_identifier in service_identifiers:
            
            service_type = service_identifier.GetType()
            
            if service_type in ( HC.LOCAL_FILE, HC.LOCAL_TAG ):
                
                page = FrameReviewServicesServicePanel( self._listbook, service_identifier )
                
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
                
                page = ( FrameReviewServicesServicePanel, [ listbook, service_identifier ], {} )
                
                name = service_identifier.GetName()
                
                listbook.AddPage( page, name )
                
            
        
        wx.CallAfter( self._listbook.Layout )
        
    
    def EventEdit( self, event ):
        
        original_pause_status = self._options[ 'pause_repo_sync' ]
        
        self._options[ 'pause_repo_sync' ] = True
        
        try:
            
            with ClientGUIDialogs.DialogManageServices( self ) as dlg: dlg.ShowModal()
            
        except: wx.MessageBox( traceback.format_exc() )
        
        self._options[ 'pause_repo_sync' ] = original_pause_status
        
    
    def EventOk( self, event ): self.Destroy()
    
    def RefreshServices( self ): self._InitialiseServices()
    
class FrameReviewServicesServicePanel( wx.ScrolledWindow ):
    
    def __init__( self, parent, service_identifier ):
        
        wx.ScrolledWindow.__init__( self, parent )
        
        self.SetScrollRate( 0, 20 )
        
        self._service_identifier = service_identifier
        
        self._service = wx.GetApp().Read( 'service', self._service_identifier )
        
        service_type = service_identifier.GetType()
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            account = self._service.GetAccount()
            
            account_type = account.GetAccountType()
            
            expires = account.GetExpires()
            
        
        def InitialiseControls():
            
            if service_type in HC.RESTRICTED_SERVICES:
                
                self._permissions_panel = ClientGUICommon.StaticBox( self, 'service permissions' )
                
                self._account_type = wx.StaticText( self._permissions_panel )
                
                self._age = ClientGUICommon.Gauge( self._permissions_panel )
                
                self._age_text = wx.StaticText( self._permissions_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                
                ( max_num_bytes, max_num_requests ) = account_type.GetMaxMonthlyData()
                
                self._bytes = ClientGUICommon.Gauge( self._permissions_panel )
                
                self._bytes_text = wx.StaticText( self._permissions_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                
                self._requests = ClientGUICommon.Gauge( self._permissions_panel )
                
                self._requests_text = wx.StaticText( self._permissions_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                
                if max_num_bytes is None: self._bytes.Hide()
                if expires is None: self._age.Hide()
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
                    
                
            
            if service_type in HC.RESTRICTED_SERVICES:
                
                if service_type in HC.REPOSITORIES:
                    
                    self._reset = wx.Button( self, label='reset cache' )
                    self._reset.Bind( wx.EVT_BUTTON, self.EventServiceReset )
                    
                
                if service_type == HC.SERVER_ADMIN:
                    
                    self._init = wx.Button( self, label='initialise server' )
                    self._init.Bind( wx.EVT_BUTTON, self.EventServerInitialise )
                    
                
                self._refresh = wx.Button( self, label='refresh account' )
                self._refresh.Bind( wx.EVT_BUTTON, self.EventServiceRefreshAccount )
                
            
        
        def InitialisePanel():
            
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
                
            
            if service_type in HC.RESTRICTED_SERVICES:
                
                repo_buttons_hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                if service_type in HC.REPOSITORIES: repo_buttons_hbox.AddF( self._reset, FLAGS_MIXED )
                
                if service_type == HC.SERVER_ADMIN: repo_buttons_hbox.AddF( self._init, FLAGS_MIXED )
                
                repo_buttons_hbox.AddF( self._refresh, FLAGS_MIXED )
                
                vbox.AddF( repo_buttons_hbox, FLAGS_BUTTON_SIZERS )
                
            
            self.SetSizer( vbox )
            
        
        InitialiseControls()
        
        InitialisePanel()
        
        self._DisplayService()
        
        self._timer_updates = wx.Timer( self, id = ID_TIMER_UPDATES )
        
        if service_type in HC.REPOSITORIES:
            
            self.Bind( wx.EVT_TIMER, self.EventTimerUpdates, id = ID_TIMER_UPDATES )
            
            self._timer_updates.Start( 1000, wx.TIMER_CONTINUOUS )
            
        
        HC.pubsub.sub( self, 'ProcessServiceUpdate', 'service_update_gui' )
        HC.pubsub.sub( self, 'AddThumbnailCount', 'add_thumbnail_count' )
        
    
    def _DisplayAccountInfo( self ):
        
        self._service = wx.GetApp().Read( 'service', self._service_identifier )
        
        service_type = self._service_identifier.GetType()
        
        now = int( time.time() )
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            account = self._service.GetAccount()
            
            account_type = account.GetAccountType()
            
            self._account_type.SetLabel( account_type.ConvertToString() )
            
            if service_type in HC.REPOSITORIES:
                
                if not account.IsBanned():
                    
                    created = account.GetCreated()
                    expires = account.GetExpires()
                    
                    if expires is None: self._age.Hide()
                    else:
                        
                        self._age.Show()
                        
                        self._age.SetRange( expires - created )
                        self._age.SetValue( min( now - created, expires - created ) )
                        
                    
                    self._age_text.SetLabel( account.GetExpiresString() )
                    
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
                    
                
            
        
    
    def _DisplayNumThumbs( self ):
        
        self._thumbnails.SetRange( self._num_thumbs )
        self._thumbnails.SetValue( min( self._num_local_thumbs, self._num_thumbs ) )
        
        self._thumbnails_text.SetLabel( HC.ConvertIntToPrettyString( self._num_local_thumbs ) + '/' + HC.ConvertIntToPrettyString( self._num_thumbs ) + ' thumbnails downloaded' )
        
    
    def _DisplayService( self ):
        
        service_type = self._service_identifier.GetType()
        
        self._DisplayAccountInfo()
        
        if service_type in HC.REPOSITORIES + [ HC.LOCAL_FILE, HC.LOCAL_TAG, HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ]:
            
            service_info = wx.GetApp().Read( 'service_info', self._service_identifier )
            
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
                
                self._ratings_text.SetLabel( str( num_ratings ) + ' files rated' )
                
            
        
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
            
        
    
    def EventServerInitialise( self, event ):
        
        try:
            
            service = wx.GetApp().Read( 'service', self._service_identifier )
            
            connection = service.GetConnection()
            
            connection.Get( 'init' )
            
        except Exception as e: wx.MessageBox( unicode( e ) )
        
    
    def EventServiceRefreshAccount( self, event ):
        
        try:
            
            connection = self._service.GetConnection()
            
            connection.Get( 'account' )
            
        except Exception as e:
            
            wx.MessageBox( unicode( e ) )
            
            print( traceback.format_exc() )
            
        
    
    def EventServiceReset( self, event ):
        
        message = 'This will remove all cached information for ' + self._service_identifier.GetName() + ' from the database. It will take time to resynchronise.'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                with wx.BusyCursor(): wx.GetApp().Write( 'reset_service', self._service_identifier )
                
            
        
    
    def EventTimerUpdates( self, event ):
        
        now = int( time.time() )
        
        first_begin = self._service.GetFirstBegin()
        next_begin = self._service.GetNextBegin()
        
        if first_begin == 0:
            
            num_updates = 0
            num_updates_downloaded = 0
            
        else:
            
            num_updates = ( now - first_begin ) / HC.UPDATE_DURATION
            num_updates_downloaded = ( next_begin - first_begin ) / HC.UPDATE_DURATION
            
        
        self._updates_text.SetLabel( HC.ConvertIntToPrettyString( num_updates_downloaded ) + '/' + HC.ConvertIntToPrettyString( num_updates ) + ' - ' + self._service.GetUpdateStatus() )
        
    
    def ProcessServiceUpdate( self, update ):
        
        service_identifier = update.GetServiceIdentifier()
        
        if service_identifier == self._service_identifier:
            
            action = update.GetAction()
            
            if action == HC.SERVICE_UPDATE_RESET: self._service_identifier = update.GetInfo()
            
            if action in ( HC.SERVICE_UPDATE_ACCOUNT, HC.SERVICE_UPDATE_REQUEST_MADE ): wx.CallLater( 200, self._DisplayAccountInfo )
            else:
                wx.CallLater( 200, self._DisplayService )
                wx.CallLater( 400, self.Layout ) # ugly hack, but it works for now
            
        
    
class FrameSplash( ClientGUICommon.Frame ):
    
    def __init__( self ):
        
        wx.Frame.__init__( self, None, style = wx.FRAME_NO_TASKBAR | wx.FRAME_SHAPED, title = 'hydrus client' )
        
        self.SetIcon( wx.Icon( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', wx.BITMAP_TYPE_ICO ) )
        
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
        
    