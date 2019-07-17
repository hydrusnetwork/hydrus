import collections
import os
import random
import threading
import collections
import shutil
import sys
import tempfile
import time
import traceback
import unittest
import wx
from . import HydrusConstants as HC
from . import ClientConstants as CC
from . import HydrusGlobals as HG
from . import ClientAPI
from . import ClientDefaults
from . import ClientFiles
from . import ClientNetworking
from . import ClientNetworkingBandwidth
from . import ClientNetworkingDomain
from . import ClientNetworkingLogin
from . import ClientNetworkingSessions
from . import ClientServices
from . import ClientThreading
from . import HydrusExceptions
from . import HydrusPubSub
from . import HydrusSessions
from . import HydrusTags
from . import HydrusThreading
from . import TestClientAPI
from . import TestClientConstants
from . import TestClientDaemons
from . import TestClientData
from . import TestClientDB
from . import TestClientDBDuplicates
from . import TestClientImageHandling
from . import TestClientImportOptions
from . import TestClientImportSubscriptions
from . import TestClientListBoxes
from . import TestClientNetworking
from . import TestClientThreading
from . import TestDialogs
from . import TestFunctions
from . import TestHydrusNATPunch
from . import TestHydrusNetworking
from . import TestHydrusSerialisable
from . import TestHydrusServer
from . import TestHydrusSessions
from . import TestHydrusTags
from . import TestServerDB
from twisted.internet import reactor
from . import ClientCaches
from . import ClientData
from . import ClientOptions
from . import HydrusData
from . import HydrusPaths


DB_DIR = None

tiniest_gif = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\xFF\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00\x3B'

LOCAL_RATING_LIKE_SERVICE_KEY = HydrusData.GenerateKey()
LOCAL_RATING_NUMERICAL_SERVICE_KEY = HydrusData.GenerateKey()

def ConvertServiceKeysToContentUpdatesToComparable( service_keys_to_content_updates ):
    
    comparable_dict = {}
    
    for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
        
        comparable_dict[ service_key ] = set( content_updates )
        
    
    return comparable_dict
    
class MockController( object ):
    
    def __init__( self ):
        
        self.model_is_shutdown = False
        
        self.new_options = ClientOptions.ClientOptions()
        
    
    def CallToThread( self, callable, *args, **kwargs ):
        
        return HG.test_controller.CallToThread( callable, *args, **kwargs )
        
    
    def JustWokeFromSleep( self ):
        
        return False
        
    
    def ModelIsShutdown( self ):
        
        return self.model_is_shutdown or HG.test_controller.ModelIsShutdown()
        
    
    def pub( self, *args, **kwargs ):
        
        pass
        
    
    def sub( self, *args, **kwargs ):
        
        pass
        
    
class MockServicesManager( object ):
    
    def __init__( self, services ):
        
        self._service_keys_to_services = { service.GetServiceKey() : service for service in services }
        
    
    def GetName( self, service_key ):
        
        return self._service_keys_to_services[ service_key ].GetName()
        
    
    def GetService( self, service_key ):
        
        return self._service_keys_to_services[ service_key ]
        
    
    def ServiceExists( self, service_key ):
        
        return service_key in self._service_keys_to_services
        
    
class FakeWebSessionManager():
    
    def EnsureLoggedIn( self, name ):
        
        pass
        
    
    def GetCookies( self, *args, **kwargs ):
        
        return { 'session_cookie' : 'blah' }
        
    
class TestFrame( wx.Frame ):
    
    def __init__( self ):
        
        wx.Frame.__init__( self, None )
        
    
    def SetPanel( self, panel ):
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.Fit()
        
        self.Show()
        

only_run = None

class Controller( object ):
    
    def __init__( self, win, only_run ):
        
        self.win = win
        self.only_run = only_run
        
        self.db_dir = tempfile.mkdtemp()
        
        global DB_DIR
        
        DB_DIR = self.db_dir
        
        self._server_files_dir = os.path.join( self.db_dir, 'server_files' )
        self._updates_dir = os.path.join( self.db_dir, 'test_updates' )
        
        client_files_default = os.path.join( self.db_dir, 'client_files' )
        
        HydrusPaths.MakeSureDirectoryExists( self._server_files_dir )
        HydrusPaths.MakeSureDirectoryExists( self._updates_dir )
        HydrusPaths.MakeSureDirectoryExists( client_files_default )
        
        HG.controller = self
        HG.client_controller = self
        HG.server_controller = self
        HG.test_controller = self
        
        self.gui = self
        
        self._call_to_threads = []
        
        self._pubsub = HydrusPubSub.HydrusPubSub( self )
        
        self.new_options = ClientOptions.ClientOptions()
        
        HC.options = ClientDefaults.GetClientDefaultOptions()
        
        self.options = HC.options
        
        def show_text( text ): pass
        
        HydrusData.ShowText = show_text
        
        self._reads = {}
        
        self._reads[ 'local_booru_share_keys' ] = []
        self._reads[ 'messaging_sessions' ] = []
        self._reads[ 'tag_censorship' ] = []
        self._reads[ 'options' ] = ClientDefaults.GetClientDefaultOptions()
        self._reads[ 'file_system_predicates' ] = []
        self._reads[ 'media_results' ] = []
        
        self.example_tag_repo_service_key = HydrusData.GenerateKey()
        
        services = []
        
        services.append( ClientServices.GenerateService( CC.LOCAL_BOORU_SERVICE_KEY, HC.LOCAL_BOORU, 'local booru' ) )
        services.append( ClientServices.GenerateService( CC.CLIENT_API_SERVICE_KEY, HC.CLIENT_API_SERVICE, 'client api' ) )
        services.append( ClientServices.GenerateService( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, HC.COMBINED_LOCAL_FILE, 'all local files' ) )
        services.append( ClientServices.GenerateService( CC.LOCAL_FILE_SERVICE_KEY, HC.LOCAL_FILE_DOMAIN, 'my files' ) )
        services.append( ClientServices.GenerateService( CC.TRASH_SERVICE_KEY, HC.LOCAL_FILE_TRASH_DOMAIN, 'trash' ) )
        services.append( ClientServices.GenerateService( CC.LOCAL_TAG_SERVICE_KEY, HC.LOCAL_TAG, 'local tags' ) )
        services.append( ClientServices.GenerateService( self.example_tag_repo_service_key, HC.TAG_REPOSITORY, 'example tag repo' ) )
        services.append( ClientServices.GenerateService( CC.COMBINED_TAG_SERVICE_KEY, HC.COMBINED_TAG, 'all known tags' ) )
        services.append( ClientServices.GenerateService( LOCAL_RATING_LIKE_SERVICE_KEY, HC.LOCAL_RATING_LIKE, 'example local rating like service' ) )
        services.append( ClientServices.GenerateService( LOCAL_RATING_NUMERICAL_SERVICE_KEY, HC.LOCAL_RATING_NUMERICAL, 'example local rating numerical service' ) )
        
        self._reads[ 'services' ] = services
        
        client_files_locations = {}
        
        for prefix in HydrusData.IterateHexPrefixes():
            
            for c in ( 'f', 't' ):
                
                client_files_locations[ c + prefix ] = client_files_default
                
            
        
        self._reads[ 'client_files_locations' ] = client_files_locations
        
        self._reads[ 'sessions' ] = []
        self._reads[ 'tag_parents' ] = {}
        self._reads[ 'tag_siblings' ] = {}
        self._reads[ 'in_inbox' ] = False
        
        self._writes = collections.defaultdict( list )
        
        self._managers = {}
        
        self.services_manager = ClientCaches.ServicesManager( self )
        self.client_files_manager = ClientFiles.ClientFilesManager( self )
        
        self.parsing_cache = ClientCaches.ParsingCache()
        
        bandwidth_manager = ClientNetworkingBandwidth.NetworkBandwidthManager()
        session_manager = ClientNetworkingSessions.NetworkSessionManager()
        domain_manager = ClientNetworkingDomain.NetworkDomainManager()
        
        ClientDefaults.SetDefaultDomainManagerData( domain_manager )
        
        login_manager = ClientNetworkingLogin.NetworkLoginManager()
        
        self.network_engine = ClientNetworking.NetworkEngine( self, bandwidth_manager, session_manager, domain_manager, login_manager )
        
        self.CallToThreadLongRunning( self.network_engine.MainLoop )
        
        self.tag_censorship_manager = ClientCaches.TagCensorshipManager( self )
        self.tag_siblings_manager = ClientCaches.TagSiblingsManager( self )
        self.tag_parents_manager = ClientCaches.TagParentsManager( self )
        self._managers[ 'undo' ] = ClientCaches.UndoManager( self )
        self.server_session_manager = HydrusSessions.HydrusSessionManagerServer()
        
        self.bitmap_manager = ClientCaches.BitmapManager( self )
        
        self.local_booru_manager = ClientCaches.LocalBooruCache( self )
        self.client_api_manager = ClientAPI.APIManager()
        
        self._cookies = {}
        
        self._job_scheduler = HydrusThreading.JobScheduler( self )
        
        self._job_scheduler.start()
        
    
    def _GetCallToThread( self ):
        
        for call_to_thread in self._call_to_threads:
            
            if not call_to_thread.CurrentlyWorking():
                
                return call_to_thread
                
            
        
        if len( self._call_to_threads ) > 100:
            
            raise Exception( 'Too many call to threads!' )
            
        
        call_to_thread = HydrusThreading.THREADCallToThread( self, 'CallToThread' )
        
        self._call_to_threads.append( call_to_thread )
        
        call_to_thread.start()
        
        return call_to_thread
        
    
    def _SetupWx( self ):
        
        self.locale = wx.Locale( wx.LANGUAGE_DEFAULT ) # Very important to init this here and keep it non garbage collected
        
        CC.GlobalBMPs.STATICInitialise()
        
        self.frame_icon = wx.Icon( os.path.join( HC.STATIC_DIR, 'hydrus_32_non-transparent.png' ), wx.BITMAP_TYPE_PNG )
        
    
    def pub( self, topic, *args, **kwargs ):
        
        pass
        
    
    def pubimmediate( self, topic, *args, **kwargs ):
        
        self._pubsub.pubimmediate( topic, *args, **kwargs )
        
    
    def sub( self, object, method_name, topic ):
        
        self._pubsub.sub( object, method_name, topic )
        
    
    def AcquirePageKey( self ):
        
        return HydrusData.GenerateKey()
        
    
    def CallBlockingToWX( self, win, func, *args, **kwargs ):
        
        def wx_code( win, job_key ):
            
            try:
                
                if win is not None and not win:
                    
                    raise HydrusExceptions.WXDeadWindowException( 'Parent Window was destroyed before wx command was called!' )
                    
                
                result = func( *args, **kwargs )
                
                job_key.SetVariable( 'result', result )
                
            except ( HydrusExceptions.WXDeadWindowException, HydrusExceptions.InsufficientCredentialsException, HydrusExceptions.ShutdownException ) as e:
                
                job_key.SetVariable( 'error', e )
                
            except Exception as e:
                
                job_key.SetVariable( 'error', e )
                
                HydrusData.Print( 'CallBlockingToWX just caught this error:' )
                HydrusData.DebugPrint( traceback.format_exc() )
                
            finally:
                
                job_key.Finish()
                
            
        
        job_key = ClientThreading.JobKey()
        
        job_key.Begin()
        
        wx.CallAfter( wx_code, win, job_key )
        
        while not job_key.IsDone():
            
            if HG.model_shutdown:
                
                raise HydrusExceptions.ShutdownException( 'Application is shutting down!' )
                
            
            time.sleep( 0.05 )
            
        
        if job_key.HasVariable( 'result' ):
            
            # result can be None, for wx_code that has no return variable
            
            result = job_key.GetIfHasVariable( 'result' )
            
            return result
            
        
        error = job_key.GetIfHasVariable( 'error' )
        
        if error is not None:
            
            raise error
            
        
        raise HydrusExceptions.ShutdownException()
        
    
    def CallToThread( self, callable, *args, **kwargs ):
        
        call_to_thread = self._GetCallToThread()
        
        call_to_thread.put( callable, *args, **kwargs )
        
    
    CallToThreadLongRunning = CallToThread
    
    def CallLater( self, initial_delay, func, *args, **kwargs ):
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        job = HydrusThreading.SchedulableJob( self, self._job_scheduler, initial_delay, call )
        
        self._job_scheduler.AddJob( job )
        
        return job
        
    
    def CallLaterWXSafe( self, window, initial_delay, func, *args, **kwargs ):
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        job = ClientThreading.WXAwareJob( self, self._job_scheduler, window, initial_delay, call )
        
        self._job_scheduler.AddJob( job )
        
        return job
        
    
    def CallRepeating( self, initial_delay, period, func, *args, **kwargs ):
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        job = HydrusThreading.RepeatingJob( self, self._job_scheduler, initial_delay, period, call )
        
        self._job_scheduler.AddJob( job )
        
        return job
        
    
    def CallRepeatingWXSafe( self, window, initial_delay, period, func, *args, **kwargs ):
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        job = ClientThreading.WXAwareRepeatingJob( self, self._job_scheduler, window, initial_delay, period, call )
        
        self._job_scheduler.AddJob( job )
        
        return job
        
    
    def ClearWrites( self, name ):
        
        if name in self._writes:
            
            del self._writes[ name ]
            
        
    
    def DBCurrentlyDoingJob( self ):
        
        return False
        
    
    def GetCurrentSessionPageInfoDict( self ):
        
        return {
            "name" : "top pages notebook",
            "page_key" : "3b28d8a59ec61834325eb6275d9df012860a1ecfd9e1246423059bc47fb6d5bd",
            "page_type" : 10,
            "selected" : True,
            "pages" : [
                {
                    "name" : "files",
                    "page_key" : "d436ff5109215199913705eb9a7669d8a6b67c52e41c3b42904db083255ca84d",
                    "page_type" : 6,
                    "selected" : False
                },
                {
                    "name" : "thread watcher",
                    "page_key" : "40887fa327edca01e1d69b533dddba4681b2c43e0b4ebee0576177852e8c32e7",
                    "page_type" : 9,
                    "selected" : False
                },
                {
                    "name" : "pages",
                    "page_key" : "2ee7fa4058e1e23f2bd9e915cdf9347ae90902a8622d6559ba019a83a785c4dc",
                    "page_type" : 10,
                    "selected" : True,
                    "pages" : [
                        {
                            "name" : "urls",
                            "page_key" : "9fe22cb760d9ee6de32575ed9f27b76b4c215179cf843d3f9044efeeca98411f",
                            "page_type" : 7,
                            "selected" : True
                        },
                        {
                            "name" : "files",
                            "page_key" : "2977d57fc9c588be783727bcd54225d577b44e8aa2f91e365a3eb3c3f580dc4e",
                            "page_type" : 6,
                            "selected" : False
                        }
                    ]
                }	
            ]
        }
        
    
    def GetFilesDir( self ):
        
        return self._server_files_dir
        
    
    def GetNewOptions( self ):
        
        return self.new_options
        
    
    def GetManager( self, manager_type ):
        
        return self._managers[ manager_type ]
        
    
    def GetWrite( self, name ):
        
        write = self._writes[ name ]
        
        del self._writes[ name ]
        
        return write
        
    
    def ImportURLFromAPI( self, url, service_keys_to_tags, destination_page_name, destination_page_key, show_destination_page ):
        
        normalised_url = self.network_engine.domain_manager.NormaliseURL( url )
        
        human_result_text = '"{}" URL added successfully.'.format( normalised_url )
        
        self.Write( 'import_url_test', url, service_keys_to_tags, destination_page_name, destination_page_key, show_destination_page )
        
        return ( normalised_url, human_result_text )
        
    
    def IsBooted( self ):
        
        return True
        
    
    def IsCurrentPage( self, page_key ):
        
        return False
        
    
    def IsFirstStart( self ):
        
        return True
        
    
    def IShouldRegularlyUpdate( self, window ):
        
        return True
        
    
    def JustWokeFromSleep( self ):
        
        return False
        
    
    def ModelIsShutdown( self ):
        
        return HG.model_shutdown
        
    
    def PageAlive( self, page_key ):
        
        return False
        
    
    def PageClosedButNotDestroyed( self, page_key ):
        
        return False
        
    
    def Read( self, name, *args, **kwargs ):
        
        return self._reads[ name ]
        
    
    def RegisterUIUpdateWindow( self, window ):
        
        pass
        
    
    def ReleasePageKey( self, page_key ):
        
        pass
        
    
    def ReportDataUsed( self, num_bytes ):
        
        pass
        
    
    def ReportRequestUsed( self ):
        
        pass
        
    
    def ResetIdleTimer( self ): pass
    
    def Run( self, window ):
        
        # we are in wx thread here, we can do this
        self._SetupWx()
        
        suites = []
        
        if self.only_run is None:
            
            run_all = True
            
        else:
            
            run_all = False
            
        
        # the gui stuff runs fine on its own but crashes in the full test if it is not early, wew
        # something to do with the delayed button clicking stuff
        if run_all or self.only_run == 'gui':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestDialogs ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientListBoxes ) )
            
        if run_all or self.only_run == 'client_api':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientAPI ) )
            
        if run_all or self.only_run == 'daemons':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientDaemons ) )
            
        if run_all or self.only_run == 'data':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientConstants ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientData ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientImportOptions ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientThreading ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestFunctions ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusSerialisable ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusSessions ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusTags ) )
            
        if run_all or self.only_run == 'db':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientDB ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestServerDB ) )
            
        if run_all or self.only_run in ( 'db', 'db_duplicates' ):
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientDBDuplicates ) )
            
        if run_all or self.only_run == 'networking':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientNetworking ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusNetworking ) )
            
        if run_all or self.only_run == 'import':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientImportSubscriptions ) )
            
        if run_all or self.only_run == 'image':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientImageHandling ) )
            
        if run_all or self.only_run == 'nat':
            
            pass
            #suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusNATPunch ) )
            
        if run_all or self.only_run == 'server':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusServer ) )
            
        
        suite = unittest.TestSuite( suites )
        
        runner = unittest.TextTestRunner( verbosity = 2 )
        
        def do_it():
            
            try:
                
                runner.run( suite )
                
            finally:
                
                wx.CallAfter( self.win.DestroyLater )
                
            
        
        self.win.Show()
        
        test_thread = threading.Thread( target = do_it )
        
        test_thread.start()
        
    
    def SetRead( self, name, value ):
        
        self._reads[ name ] = value
        
    
    def SetStatusBarDirty( self ):
        
        pass
        
    
    def SetWebCookies( self, name, value ):
        
        self._cookies[ name ] = value
        
    
    def ShouldStopThisWork( self, maintenance_mode, stop_time = None ):
        
        return False
        
    
    def ShowPage( self, page_key ):
        
        self.Write( 'show_page', page_key )
        
    
    def TidyUp( self ):
        
        time.sleep( 2 )
        
        HydrusPaths.DeletePath( self.db_dir )
        
    
    def ViewIsShutdown( self ):
        
        return HG.view_shutdown
        
    
    def WaitUntilModelFree( self ):
        
        return
        
    
    def WaitUntilViewFree( self ):
        
        return
        
    
    def Write( self, name, *args, **kwargs ):
        
        self._writes[ name ].append( ( args, kwargs ) )
        
    
    def WriteSynchronous( self, name, *args, **kwargs ):
        
        self._writes[ name ].append( ( args, kwargs ) )
        
        if name == 'import_file':
            
            ( file_import_job, ) = args
            
            if file_import_job.GetHash().hex() == 'a593942cb7ea9ffcd8ccf2f0fa23c338e23bfecd9a3e508dfc0bcf07501ead08': # 'blarg' in sha256 hex
                
                raise Exception( 'File failed to import for some reason!' )
                
            else:
                
                return ( CC.STATUS_SUCCESSFUL_AND_NEW, 'test note' )
                
            
        
    
