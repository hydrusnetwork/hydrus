import collections
import collections.abc
import os
import threading
import tempfile
import time
import typing
import unittest

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusPaths
from hydrus.core import HydrusPubSub
from hydrus.core import HydrusSessions
from hydrus.core import HydrusTemp
from hydrus.core.files import HydrusFilesPhysicalStorage
from hydrus.core.processes import HydrusThreading

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDefaults
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientOptions
from hydrus.client import ClientManagers
from hydrus.client import ClientServices
from hydrus.client import ClientThreading
from hydrus.client.caches import ClientCaches
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.files import ClientFilesManager
from hydrus.client.files import ClientFilesPhysical
from hydrus.client.gui import ClientGUICallAfter
from hydrus.client.gui import ClientGUISplash
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListManager
from hydrus.client.importing import ClientImportFiles
from hydrus.client.metadata import ClientTagsHandling
from hydrus.client.networking import ClientNetworking
from hydrus.client.networking import ClientNetworkingBandwidth
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingLogin
from hydrus.client.networking import ClientNetworkingSessions

from hydrus.server import ServerGlobals as SG

from hydrus.test import TestClientAPI
from hydrus.test import TestClientConstants
from hydrus.test import TestClientDaemons
from hydrus.test import TestClientDB
from hydrus.test import TestClientDBDuplicates
from hydrus.test import TestClientDBDuplicatesAutoResolution
from hydrus.test import TestClientDBTags
from hydrus.test import TestClientDuplicatesAutoResolution
from hydrus.test import TestClientFileStorage
from hydrus.test import TestClientImageHandling
from hydrus.test import TestClientImportObjects
from hydrus.test import TestClientImportOptions
from hydrus.test import TestClientImportSubscriptions
from hydrus.test import TestClientListBoxes
from hydrus.test import TestClientMetadataConditional
from hydrus.test import TestClientMetadataMigration
from hydrus.test import TestClientMigration
from hydrus.test import TestClientNetworking
from hydrus.test import TestClientParsing
from hydrus.test import TestClientSearch
from hydrus.test import TestClientTags
from hydrus.test import TestClientThreading
from hydrus.test import TestDialogs
from hydrus.test import TestGlobals as TG
from hydrus.test import TestHydrusData
from hydrus.test import TestHydrusNATPunch
from hydrus.test import TestHydrusNetworking
from hydrus.test import TestHydrusPaths
from hydrus.test import TestHydrusSerialisable
from hydrus.test import TestHydrusServer
from hydrus.test import TestHydrusSessions
from hydrus.test import TestHydrusTags
from hydrus.test import TestHydrusTime
from hydrus.test import TestServerDB

DB_DIR = None

tiniest_gif = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\xFF\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00\x3B'

LOCAL_RATING_LIKE_SERVICE_KEY = HydrusData.GenerateKey()
LOCAL_RATING_NUMERICAL_SERVICE_KEY = HydrusData.GenerateKey()
LOCAL_RATING_INCDEC_SERVICE_KEY = HydrusData.GenerateKey()

callable_P = typing.ParamSpec( 'callable_P' )
callable_R = typing.TypeVar( 'callable_R' )

class MockController( object ):
    
    def __init__( self ):
        
        self.new_options = ClientOptions.ClientOptions()
        
    
    def CallToThread( self, callable, *args, **kwargs ):
        
        return TG.test_controller.CallToThread( callable, *args, **kwargs )
        
    
    def JustWokeFromSleep( self ):
        
        return False
        
    
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
        
    

class TestFrame( QW.QWidget ):
    
    def __init__( self ):
        
        super().__init__( None )
        
    
    def SetPanel( self, panel ):
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self.show()
        
    

only_run = None

class Controller( object ):
    
    def __init__( self, win, only_run ):
        
        self.app = win
        self.win = win
        self.only_run = only_run
        self.run_finished = False
        self.was_successful = False
        
        self.main_qt_thread = self.app.thread()
        
        self.call_after_catcher = ClientGUICallAfter.CallAfterEventCatcher( QW.QApplication.instance() )
        
        self._test_db = None
        
        self.db_dir = tempfile.mkdtemp()
        
        self._hydrus_temp_dir = HydrusTemp.InitialiseHydrusTempDir()
        
        global DB_DIR
        
        DB_DIR = self.db_dir
        
        self._server_files_dir = os.path.join( self.db_dir, 'server_files' )
        self._updates_dir = os.path.join( self.db_dir, 'test_updates' )
        
        client_files_default = os.path.join( self.db_dir, 'client_files' )
        
        HydrusPaths.MakeSureDirectoryExists( self._server_files_dir )
        HydrusPaths.MakeSureDirectoryExists( self._updates_dir )
        HydrusPaths.MakeSureDirectoryExists( client_files_default )
        
        HG.controller = self
        CG.client_controller = self
        SG.server_controller = self
        TG.test_controller = self
        
        self.db = self
        self.gui = self
        
        self.frame_splash_status = ClientGUISplash.FrameSplashStatus()
        
        self._call_to_threads = []
        
        self._pubsub = HydrusPubSub.HydrusPubSub( lambda o: True )
        
        self.new_options = ClientOptions.ClientOptions()
        
        HC.options = ClientDefaults.GetClientDefaultOptions()
        
        self.options = HC.options
        
        def show_text( text ): pass
        
        HydrusData.ShowText = show_text
        
        self._name_read_responses = {}
        
        self._name_read_responses[ 'messaging_sessions' ] = []
        self._name_read_responses[ 'options' ] = ClientDefaults.GetClientDefaultOptions()
        self._name_read_responses[ 'file_system_predicates' ] = []
        self._name_read_responses[ 'media_results' ] = []
        
        self._param_read_responses = {}
        
        self.example_like_rating_service_key = LOCAL_RATING_LIKE_SERVICE_KEY
        self.example_numerical_rating_service_key = LOCAL_RATING_NUMERICAL_SERVICE_KEY
        self.example_incdec_rating_service_key = LOCAL_RATING_INCDEC_SERVICE_KEY
        
        self.example_file_repo_service_key_1 = HydrusData.GenerateKey()
        self.example_file_repo_service_key_2 = HydrusData.GenerateKey()
        self.example_tag_repo_service_key = HydrusData.GenerateKey()
        self.example_ipfs_service_key = HydrusData.GenerateKey()
        
        services = []
        
        services.append( ClientServices.GenerateService( CC.CLIENT_API_SERVICE_KEY, HC.CLIENT_API_SERVICE, 'client api' ) )
        services.append( ClientServices.GenerateService( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, HC.HYDRUS_LOCAL_FILE_STORAGE, 'hydrus local file storage' ) )
        services.append( ClientServices.GenerateService( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, HC.COMBINED_LOCAL_FILE_DOMAINS, 'combined local file domains' ) )
        services.append( ClientServices.GenerateService( CC.LOCAL_FILE_SERVICE_KEY, HC.LOCAL_FILE_DOMAIN, 'my files' ) )
        services.append( ClientServices.GenerateService( CC.LOCAL_UPDATE_SERVICE_KEY, HC.LOCAL_FILE_UPDATE_DOMAIN, 'repository updates' ) )
        services.append( ClientServices.GenerateService( CC.TRASH_SERVICE_KEY, HC.LOCAL_FILE_TRASH_DOMAIN, 'trash' ) )
        services.append( ClientServices.GenerateService( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, HC.LOCAL_TAG, 'my tags' ) )
        services.append( ClientServices.GenerateService( self.example_file_repo_service_key_1, HC.FILE_REPOSITORY, 'example file repo 1' ) )
        services.append( ClientServices.GenerateService( self.example_file_repo_service_key_2, HC.FILE_REPOSITORY, 'example file repo 2' ) )
        services.append( ClientServices.GenerateService( self.example_tag_repo_service_key, HC.TAG_REPOSITORY, 'example tag repo' ) )
        services.append( ClientServices.GenerateService( CC.COMBINED_TAG_SERVICE_KEY, HC.COMBINED_TAG, 'all known tags' ) )
        services.append( ClientServices.GenerateService( CC.COMBINED_FILE_SERVICE_KEY, HC.COMBINED_FILE, 'all known files' ) )
        
        service = typing.cast( ClientServices.ServiceLocalRatingLike, ClientServices.GenerateService( LOCAL_RATING_LIKE_SERVICE_KEY, HC.LOCAL_RATING_LIKE, 'example local rating like service' ) )
        service._shape = None
        service._rating_svg = 'star'
        services.append( service )
        
        services.append( ClientServices.GenerateService( LOCAL_RATING_NUMERICAL_SERVICE_KEY, HC.LOCAL_RATING_NUMERICAL, 'example local rating numerical service' ) )
        services.append( ClientServices.GenerateService( LOCAL_RATING_INCDEC_SERVICE_KEY, HC.LOCAL_RATING_INCDEC, 'example local rating inc/dec service' ) )
        services.append( ClientServices.GenerateService( self.example_ipfs_service_key, HC.IPFS, 'example ipfs service' ) )
        services.append( ClientServices.GenerateService( CC.COMBINED_DELETED_FILE_SERVICE_KEY, HC.COMBINED_DELETED_FILE, 'deleted from anywhere' ) ),
        
        self._name_read_responses[ 'services' ] = services
        
        client_files_subfolders = []
        
        base_location = ClientFilesPhysical.FilesStorageBaseLocation( client_files_default, 1 )
        
        for prefix in HydrusFilesPhysicalStorage.IteratePrefixes( 'f' ):
            
            client_files_subfolders.append( ClientFilesPhysical.FilesStorageSubfolder( prefix, base_location ) )
            
        
        for prefix in HydrusFilesPhysicalStorage.IteratePrefixes( 't' ):
            
            client_files_subfolders.append( ClientFilesPhysical.FilesStorageSubfolder( prefix, base_location ) )
            
        
        self._name_read_responses[ 'client_files_subfolders' ] = client_files_subfolders
        
        self._name_read_responses[ 'sessions' ] = []
        self._name_read_responses[ 'tag_parents' ] = {}
        self._name_read_responses[ 'tag_siblings_all_ideals' ] = {}
        self._name_read_responses[ 'inbox_hashes' ] = set()
        
        self._read_call_args = collections.defaultdict( list )
        self._write_call_args = collections.defaultdict( list )
        
        self._managers = {}
        
        self.column_list_manager = ClientGUIListManager.ColumnListManager()
        
        self.services_manager = ClientServices.ServicesManager( self )
        self.client_files_manager = ClientFilesManager.ClientFilesManager( self )
        
        self.parsing_cache = ClientCaches.ParsingCache()
        
        bandwidth_manager = ClientNetworkingBandwidth.NetworkBandwidthManager()
        session_manager = ClientNetworkingSessions.NetworkSessionManager()
        domain_manager = ClientNetworkingDomain.NetworkDomainManager()
        
        ClientDefaults.SetDefaultDomainManagerData( domain_manager )
        
        login_manager = ClientNetworkingLogin.NetworkLoginManager()
        
        self.network_engine = ClientNetworking.NetworkEngine( self, bandwidth_manager, session_manager, domain_manager, login_manager )
        
        self.CallToThreadLongRunning( self.network_engine.MainLoop )
        
        self.tag_display_manager = ClientTagsHandling.TagDisplayManager()
        
        self.duplicates_auto_resolution_manager = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionManager( self )
        
        self._managers[ 'undo' ] = ClientManagers.UndoManager( self )
        
        self.images_cache = ClientCaches.ImageRendererCache( self )
        self.image_tiles_cache = ClientCaches.ImageTileCache( self )
        self.thumbnails_cache = ClientCaches.ThumbnailCache( self )
        
        self.server_session_manager = HydrusSessions.HydrusSessionManagerServer()
        
        self.bitmap_manager = ClientManagers.BitmapManager( self )
        
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
        
    
    def _SetupQt( self ):
        
        self.locale = QC.QLocale() # Very important to init this here and keep it non garbage collected
        
        CC.GlobalPixmaps()
        CC.GlobalIcons()
        
    
    def pub( self, topic, *args, **kwargs ):
        
        pass
        
    
    def pubimmediate( self, topic, *args, **kwargs ):
        
        self._pubsub.pubimmediate( topic, *args, **kwargs )
        
    
    def sub( self, object, method_name, topic ):
        
        self._pubsub.sub( object, method_name, topic )
        
    
    def AcquirePageKey( self ):
        
        return HydrusData.GenerateKey()
        
    
    def AmInTheMainQtThread( self ) -> bool:
        
        return QC.QThread.currentThread() == self.main_qt_thread
        
    
    def CallBlockingToQt( self, win, func: typing.Callable[ callable_P, callable_R ], *args: callable_P.args, **kwargs: callable_P.kwargs ) -> callable_R:
        
        def qt_code( win: QW.QWidget, job_status: ClientThreading.JobStatus ):
            
            try:
                
                result = func( *args, **kwargs )
                
                job_status.SetVariable( 'result', result )
                
            except Exception as e:
                
                job_status.SetErrorException( e )
                
            finally:
                
                job_status.Finish()
                
            
        
        if self.AmInTheMainQtThread():
            
            return func( *args, **kwargs )
            
        
        job_status = ClientThreading.JobStatus( cancellable = True, cancel_on_shutdown = False )
        
        self.CallAfterQtSafe( win, qt_code, win, job_status )
        
        done_event = job_status.GetDoneEvent()
        
        while not job_status.IsDone():
            
            if not QP.isValid( win ):
                
                raise HydrusExceptions.QtDeadWindowException( 'Window died before job returned!' )
                
            
            if HG.model_shutdown:
                
                raise HydrusExceptions.ShutdownException( 'Application is shutting down!' )
                
            
            done_event.wait( 1.0 )
            
        
        if job_status.HasVariable( 'result' ):
            
            # result can be None, for qt_code that has no return variable
            
            result = job_status.GetIfHasVariable( 'result' )
            
            return result
            
        
        if job_status.HadError():
            
            e = job_status.GetErrorException()
            
            raise e
            
        
        raise HydrusExceptions.ShutdownException()
        
    
    def CallBlockingToQtFireAndForgetNoResponse( self, win, func, *args, **kwargs ) -> None:
        
        try:
            
            self.CallBlockingToQt( win, func, *args, **kwargs )
            
        except ( HydrusExceptions.QtDeadWindowException, HydrusExceptions.ShutdownException, HydrusExceptions.CancelledException ):
            
            pass
            
        
    
    def CallBlockingToQtTLW( self, func: typing.Callable[ callable_P, callable_R ], *args: callable_P.args, **kwargs: callable_P.kwargs ) -> callable_R:
        
        main_tlw = self.GetMainTLW()
        
        if main_tlw is None:
            
            raise HydrusExceptions.ShutdownException( 'Could not find a TLW! I think the program is shutting down or never booted correct!' )
            
        
        try:
            
            return self.CallBlockingToQt( main_tlw, func, *args, **kwargs )
            
        except ( HydrusExceptions.QtDeadWindowException, HydrusExceptions.ShutdownException ):
            
            raise HydrusExceptions.ShutdownException( 'Program is shutting down!' )
            
        
    
    def CallToThread( self, callable, *args, **kwargs ):
        
        call_to_thread = self._GetCallToThread()
        
        call_to_thread.put( callable, *args, **kwargs )
        
    
    CallToThreadLongRunning = CallToThread
    
    def CallAfterQtSafe( self, qobject: QC.QObject, func, *args, **kwargs ):
        
        ClientGUICallAfter.CallAfter( self.call_after_catcher, qobject, func, *args, **kwargs )
        
    
    def CallLater( self, initial_delay, func, *args, **kwargs ):
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        job = HydrusThreading.SingleJob( self, self._job_scheduler, initial_delay, call )
        
        self._job_scheduler.AddJob( job )
        
        return job
        
    
    def CallLaterQtSafe( self, window, initial_delay, label, func, *args, **kwargs ):
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        call.SetLabel( label )
        
        job = ClientThreading.QtAwareJob( self, self._job_scheduler, window, initial_delay, call )
        
        self._job_scheduler.AddJob( job )
        
        return job
        
    
    def CallRepeating( self, initial_delay, period, label, func, *args, **kwargs ):
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        job = HydrusThreading.RepeatingJob( self, self._job_scheduler, initial_delay, period, call )
        
        self._job_scheduler.AddJob( job )
        
        return job
        
    
    def CallRepeatingQtSafe( self, window, initial_delay, period, label, func, *args, **kwargs ):
        
        call = HydrusData.Call( func, *args, **kwargs )
        
        job = ClientThreading.QtAwareRepeatingJob(self, self._job_scheduler, window, initial_delay, period, call)
        
        self._job_scheduler.AddJob( job )
        
        return job
        
    
    def ClearReads( self, name ):
        
        if name in self._read_call_args:
            
            del self._read_call_args[ name ]
            
        
    
    def ClearTestDB( self ):
        
        self._test_db = None
        
    
    def ClearWrites( self, name ):
        
        if name in self._write_call_args:
            
            del self._write_call_args[ name ]
            
        
    
    def CurrentlyIdle( self ):
        
        return False
        
    
    def DBCurrentlyDoingJob( self ):
        
        return False
        
    
    def DoingFastExit( self ):
        
        return False
        
    
    def GetCurrentSessionPageAPIInfoDict( self ):
        
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
        
    
    def GetMainGUI( self ):
        
        return self.win
        
    
    def GetMainTLW( self ):
        
        return self.win
        
    
    def GetMediaViewersAPIInfo( self ):
        
        raise NotImplementedError()
        
    
    def GetNewOptions( self ):
        
        return self.new_options
        
    
    def GetManager( self, manager_type ):
        
        return self._managers[ manager_type ]
        
    
    def GetPageAPIInfoDict( self, page_key, simple ):
        
        return {}
        
    
    def GetRead( self, name ):
        
        read = self._read_call_args[ name ]
        
        del self._read_call_args[ name ]
        
        return read
        
    
    def GetHydrusTempDir( self ):
        
        return self._hydrus_temp_dir
        
    
    def GetWrite( self, name ):
        
        write = self._write_call_args[ name ]
        
        del self._write_call_args[ name ]
        
        return write
        
    
    def ImportURLFromAPI( self, url, filterable_tags, additional_service_keys_to_tags, destination_page_name, destination_page_key, show_destination_page, destination_location_context ):
        
        from hydrus.client.networking import ClientNetworkingFunctions
        
        ClientNetworkingFunctions.CheckLooksLikeAFullURL( url )
        
        normalised_url = self.network_engine.domain_manager.NormaliseURL( url, for_server = True )
        
        human_result_text = '"{}" URL added successfully.'.format( normalised_url )
        
        self.Write( 'import_url_test', url, filterable_tags, additional_service_keys_to_tags, destination_page_name, destination_page_key, show_destination_page, destination_location_context )
        
        return ( normalised_url, human_result_text )
        
    
    def IsBooted( self ):
        
        return True
        
    
    def IsConnected( self ):
        
        return False
        
    
    def IsCurrentPage( self, page_key ):
        
        return False
        
    
    def IsFirstStart( self ):
        
        return True
        
    
    def isFullScreen( self ):
        
        return True # hackery for another test
        
    
    def IShouldRegularlyUpdate( self, window ):
        
        return True
        
    
    def JustWokeFromSleep( self ):
        
        return False
        
    
    def LastShutdownWasBad( self ):
        
        return False
        
    
    def PageAlive( self, page_key ):
        
        return False
        
    
    def PageClosedButNotDestroyed( self, page_key ):
        
        return False
        
    
    def PauseAndDisconnect( self, pause_and_disconnect ):
        
        pass
        
    
    def Read( self, name, *args, **kwargs ):
        
        self._read_call_args[ name ].append( ( args, kwargs ) )
        
        if self._test_db is not None:
            
            return self._test_db.Read( name, *args, **kwargs )
            
        
        try:
            
            if ( name, args ) in self._param_read_responses:
                
                return self._param_read_responses[ ( name, args ) ]
                
            
        except:
            
            pass
            
        
        result = self._name_read_responses[ name ]
        
        if isinstance( result, Exception ):
            
            raise HydrusExceptions.DBException( result, str( result ), 'test trace' )
            
        
        return result
        
    
    def RegisterUIUpdateWindow( self, window ):
        
        pass
        
    
    def ReleasePageKey( self, page_key ):
        
        pass
        
    
    def ReportDataUsed( self, num_bytes ):
        
        pass
        
    
    def ReportRequestUsed( self ):
        
        pass
        
    
    def ResetIdleTimer( self ):
        
        pass
        
    
    def ResetIdleTimerFromClientAPI( self ):
        
        pass
        
    
    def Run( self, window ):
        
        # we are in Qt thread here, we can do this
        self._SetupQt()
        
        if self.only_run is None:
            
            run_all = True
            
        else:
            
            run_all = False
            
        
        # the gui stuff runs fine on its own but crashes in the full test if it is not early, wew
        # something to do with the delayed button clicking stuff
        
        module_lookup = collections.defaultdict( list )
        
        module_lookup[ 'gui' ] = [
            TestDialogs,
            TestClientListBoxes
        ]
        
        module_lookup[ 'client_api' ] = [
            TestClientAPI
        ]
        
        module_lookup[ 'daemons' ] = [
            TestClientDaemons
        ]
        
        module_lookup[ 'data' ] = [
            TestHydrusPaths,
            TestClientConstants,
            TestClientFileStorage,
            TestClientImportObjects,
            TestClientImportOptions,
            TestClientParsing,
            TestClientSearch,
            TestClientTags,
            TestClientThreading,
            TestHydrusData,
            TestHydrusTags,
            TestHydrusTime,
            TestHydrusSerialisable,
            TestHydrusSessions,
            TestClientMetadataConditional
        ]
        
        module_lookup[ 'metadata_conditional' ] = [
            TestClientMetadataConditional
        ]
        
        module_lookup[ 'search' ] = [
            TestClientSearch,
            TestClientMetadataConditional
        ]
        
        module_lookup[ 'tags_fast' ] = [
            TestClientTags,
            TestHydrusTags
        ]
        
        module_lookup[ 'tags' ] = [
            TestClientTags,
            TestClientDBTags
        ]
        
        module_lookup[ 'client_db' ] = [
            TestClientDB
        ]
        
        module_lookup[ 'server_db' ] = [
            TestServerDB
        ]
        
        module_lookup[ 'db' ] = [
            TestClientDB,
            TestServerDB
        ]
        
        module_lookup[ 'db_duplicates' ] = [
            TestClientDBDuplicates,
            TestClientDBDuplicatesAutoResolution
        ]
        
        module_lookup[ 'db_duplicates_auto_resolution' ] = [
            TestClientDBDuplicatesAutoResolution
        ]
        
        module_lookup[ 'db_tags' ] = [
            TestClientDBTags
        ]
        
        module_lookup[ 'duplicates_auto_resolution' ] = [
            TestClientDuplicatesAutoResolution,
            TestClientDBDuplicatesAutoResolution,
            TestClientMetadataConditional
        ]
        
        module_lookup[ 'duplicates_auto_resolution_objects' ] = [
            TestClientDuplicatesAutoResolution
        ]
        
        module_lookup[ 'nat' ] = [
            TestHydrusNATPunch
        ]
        
        module_lookup[ 'networking' ] = [
            TestClientNetworking,
            TestHydrusNetworking
        ]
        
        module_lookup[ 'import' ] = [
            TestClientImportSubscriptions
        ]
        
        module_lookup[ 'image' ] = [
            TestClientImageHandling
        ]
        
        module_lookup[ 'metadata_migration' ] = [
            TestClientMetadataMigration,
            TestClientMigration
        ]
        
        module_lookup[ 'server' ] = [
            TestHydrusServer
        ]
        
        module_lookup[ 'all' ] = sorted( HydrusLists.MassUnion( module_lookup.values() ), key = lambda d: d.__name__ )
        
        if run_all:
            
            modules = module_lookup[ 'all' ]
            
        else:
            
            modules = module_lookup[ self.only_run ]
            
        
        suites = [ unittest.TestLoader().loadTestsFromModule( module ) for module in modules ]
        
        suite = unittest.TestSuite( suites )
        
        runner = unittest.TextTestRunner( verbosity = 2 )
        
        runner.failfast = True
        
        def do_it():
            
            try:
                
                result = runner.run( suite )
                
                self.run_finished = True
                self.was_successful = result.wasSuccessful()
                
            finally:
                
                self.CallAfterQtSafe( self.win, self.win.deleteLater )
                
            
        
        self.win.show()
        
        test_thread = threading.Thread( target = do_it )
        
        test_thread.start()
        
    
    def SetParamRead( self, name, args, value ):
        
        self._param_read_responses[ ( name, args ) ] = value
        
    
    def SetRead( self, name: str, value ):
        
        self._name_read_responses[ name ] = value
        
    
    def SetStatusBarDirty( self ):
        
        pass
        
    
    def SetTestDB( self, db ):
        
        self._test_db = db
        
    
    def SetWebCookies( self, name, value ):
        
        self._cookies[ name ] = value
        
    
    def ShouldStopThisWork( self, maintenance_mode, stop_time = None ):
        
        return False
        
    
    def RefreshPage( self, page_key ):
        
        self.Write( 'refresh_page', page_key )
        
    
    def ShowPage( self, page_key ):
        
        self.Write( 'show_page', page_key )
        
    
    def TidyUp( self ):
        
        time.sleep( 2 )
        
        HydrusPaths.DeletePath( self.db_dir )
        
    
    def WaitUntilModelFree( self ):
        
        return
        
    
    def WaitUntilViewFree( self ):
        
        return
        
    
    def Write( self, name, *args, **kwargs ):
        
        if self._test_db is not None:
            
            return self._test_db.Write( name, *args, **kwargs )
            
        
        self._write_call_args[ name ].append( ( args, kwargs ) )
        
    
    def WriteSynchronous( self, name, *args, **kwargs ):
        
        self._write_call_args[ name ].append( ( args, kwargs ) )
        
        if name == 'import_file':
            
            ( file_import_job, ) = args
            
            if file_import_job.GetHash().hex() == 'a593942cb7ea9ffcd8ccf2f0fa23c338e23bfecd9a3e508dfc0bcf07501ead08': # 'blarg' in sha256 hex
                
                raise Exception( 'File failed to import for some reason!' )
                
            else:
                
                h = file_import_job.GetHash()
                
                if h is None:
                    
                    h = os.urandom( 32 )
                    
                
                return ClientImportFiles.FileImportStatus( CC.STATUS_SUCCESSFUL_AND_NEW, h, note = 'test note' )
                
            
        
    
