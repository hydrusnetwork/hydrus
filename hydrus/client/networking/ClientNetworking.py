import collections
import collections.abc
import threading
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists

from hydrus.client import ClientGlobals as CG
from hydrus.client.networking import ClientNetworkingBandwidth
from hydrus.client.networking import ClientNetworkingFunctions
from hydrus.client.networking import ClientNetworkingSessions
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingJobs
from hydrus.client.networking import ClientNetworkingLogin

JOB_STATUS_AWAITING_VALIDITY = 0
JOB_STATUS_AWAITING_BANDWIDTH = 1
JOB_STATUS_AWAITING_LOGIN = 2
JOB_STATUS_AWAITING_SLOT = 3
JOB_STATUS_RUNNING = 4

job_status_str_lookup = {
    JOB_STATUS_AWAITING_VALIDITY : 'waiting for validation',
    JOB_STATUS_AWAITING_BANDWIDTH : 'waiting for bandwidth',
    JOB_STATUS_AWAITING_LOGIN : 'waiting for login',
    JOB_STATUS_AWAITING_SLOT : 'waiting for free work slot',
    JOB_STATUS_RUNNING : 'running'
}

class NetworkEngine( object ):
    
    def __init__(
        self,
        controller: "CG.ClientController.Controller",
        bandwidth_manager: ClientNetworkingBandwidth.NetworkBandwidthManager,
        session_manager: ClientNetworkingSessions.NetworkSessionManager,
        domain_manager: ClientNetworkingDomain.NetworkDomainManager,
        login_manager: ClientNetworkingLogin.NetworkLoginManager
        ):
        
        self.controller = controller
        
        self.bandwidth_manager = bandwidth_manager
        self.session_manager = session_manager
        self.domain_manager = domain_manager
        self.login_manager = login_manager
        
        self.login_manager.engine = self
        
        self._lock = threading.Lock()
        
        self.MAX_JOBS = 1
        self.MAX_JOBS_PER_DOMAIN = 1
        
        self.RefreshOptions()
        
        self._new_work_to_do = threading.Event()
        
        self._domains_to_login = []
        
        self._active_domains_counter = collections.Counter()
        
        self._jobs_awaiting_validity = []
        self._current_validation_process = None
        self._jobs_awaiting_bandwidth = []
        self._jobs_awaiting_login = []
        self._current_login_process = None
        self._jobs_awaiting_slot = []
        self._jobs_running = []
        
        self._pause_all_new_network_traffic = self.controller.new_options.GetBoolean( 'pause_all_new_network_traffic' )
        
        self._is_running = False
        self._is_shutdown = False
        self._local_shutdown = False
        
        self.controller.sub( self, 'RefreshOptions', 'notify_new_options' )
        
    
    def _AssignCurrentLoginProcess( self, login_process: ClientNetworkingLogin.LoginProcess | None ):
        
        self._current_login_process = login_process
        
        self.login_manager.SetCurrentLoginProcess( login_process )
        
    
    def AddJob( self, job: ClientNetworkingJobs.NetworkJob ):
        
        ClientNetworkingFunctions.NetworkReportMode( f'Network Job Added: {job._method}  {job._url}' )
        
        with self._lock:
            
            job.engine = self
            
            self._jobs_awaiting_validity.append( job )
            
        
        self._new_work_to_do.set()
        
    
    def ForceLogins( self, domains_to_login: collections.abc.Collection[ str ] ):
        
        with self._lock:
            
            self._domains_to_login.extend( domains_to_login )
            
            self._domains_to_login = HydrusLists.DedupeList( self._domains_to_login )
            
        
    
    def GetJobsSnapshot( self ):
        
        with self._lock:
            
            jobs = []
            
            jobs.extend( ( ( JOB_STATUS_AWAITING_VALIDITY, j ) for j in self._jobs_awaiting_validity ) )
            jobs.extend( ( ( JOB_STATUS_AWAITING_BANDWIDTH, j ) for j in self._jobs_awaiting_bandwidth ) )
            jobs.extend( ( ( JOB_STATUS_AWAITING_LOGIN, j ) for j in self._jobs_awaiting_login ) )
            jobs.extend( ( ( JOB_STATUS_AWAITING_SLOT, j ) for j in self._jobs_awaiting_slot ) )
            jobs.extend( ( ( JOB_STATUS_RUNNING, j ) for j in self._jobs_running ) )
            
            return jobs
            
        
    
    def IsBusy( self ) -> bool:
        
        with self._lock:
            
            return len( self._jobs_awaiting_validity ) + len( self._jobs_awaiting_bandwidth ) + len( self._jobs_awaiting_login ) + len( self._jobs_awaiting_slot ) + len( self._jobs_running ) > 50
            
        
    
    def IsRunning( self ) -> bool:
        
        with self._lock:
            
            return self._is_running
            
        
    
    def IsShutdown( self ) -> bool:
        
        with self._lock:
            
            return self._is_shutdown
            
        
    
    def MainLoop( self ):
        
        def ProcessValidationJob( job: ClientNetworkingJobs.NetworkJob ):
            
            if job.IsDone():
                
                return False
                
            elif job.IsAsleep():
                
                return True
                
            elif not job.IsValid():
                
                if job.CanValidateInPopup():
                    
                    if self._current_validation_process is None:
                        
                        validation_process = job.GenerateValidationPopupProcess()
                        
                        self.controller.CallToThread( validation_process.Start )
                        
                        self._current_validation_process = validation_process
                        
                        job.SetStatus( 'validation presented to user' + HC.UNICODE_ELLIPSIS )
                        
                    else:
                        
                        job.SetStatus( 'waiting in user validation queue' + HC.UNICODE_ELLIPSIS )
                        
                        job.Sleep( 5 )
                        
                    
                    return True
                    
                else:
                    
                    error_text = 'network context not currently valid!'
                    
                    job.SetError( HydrusExceptions.ValidationException( error_text ), error_text )
                    
                    return False
                    
                
            else:
                
                self._jobs_awaiting_bandwidth.append( job )
                
                return False
                
            
        
        def ProcessCurrentValidationJob():
            
            if self._current_validation_process is not None:
                
                if self._current_validation_process.IsDone():
                    
                    self._current_validation_process = None
                    
                
            
        
        def ProcessBandwidthJob( job: ClientNetworkingJobs.NetworkJob ):
            
            if job.IsDone():
                
                return False
                
            elif job.IsAsleep():
                
                return True
                
            
            elif self._pause_all_new_network_traffic:
                
                job.SetStatus( 'all new network traffic is paused' + HC.UNICODE_ELLIPSIS )
                
                job.Sleep( 2 )
                
                return True
                
            elif not job.TryToStartBandwidth():
                
                return True
                
            else:
                
                self._jobs_awaiting_login.append( job )
                
                return False
                
            
        
        def ProcessForceLogins():
            
            if len( self._domains_to_login ) > 0 and self._current_login_process is None:
                
                try:
                    
                    login_domain = self._domains_to_login.pop( 0 )
                    
                    login_process = self.login_manager.GenerateLoginProcessForDomain( login_domain )
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    return
                    
                
                self.controller.CallToThread( login_process.Start )
                
                self._AssignCurrentLoginProcess( login_process )
                
            
        
        def ProcessLoginJob( job: ClientNetworkingJobs.NetworkJob ):
            
            if job.IsDone():
                
                return False
                
            elif job.IsAsleep():
                
                return True
                
            elif job.CurrentlyNeedsLogin():
                
                try:
                    
                    job.CheckCanLogin()
                    
                except Exception as e:
                    
                    if job.WillingToWaitOnInvalidLogin():
                        
                        job.SetStatus( str( e ) )
                        
                        job.Sleep( 60 )
                        
                        return True
                        
                    else:
                        
                        job_login_network_context = job.GetLoginNetworkContext()
                        
                        if job.IsHydrusJob():
                            
                            message = f'This hydrus service "{job_login_network_context.ToString()}" could not do work because: {e}'
                            
                        else:
                            
                            message = f'This job\'s network context "{job_login_network_context.ToString()}" seems to have an invalid login. The error was: {e}'
                            
                        
                        job.Cancel( message )
                        
                        return False
                        
                    
                
                if self._current_login_process is None:
                    
                    try:
                        
                        login_process = job.GenerateLoginProcess()
                        
                    except Exception as e:
                        
                        HydrusData.ShowException( e )
                        
                        job.SetStatus( str( e ) )
                        
                        job.Sleep( 60 )
                        
                        return True
                        
                    
                    self.controller.CallToThread( login_process.Start )
                    
                    self._AssignCurrentLoginProcess( login_process )
                    
                    job.SetStatus( 'logging in' + HC.UNICODE_ELLIPSIS )
                    
                else:
                    
                    job.SetStatus( 'waiting in login queue' + HC.UNICODE_ELLIPSIS )
                    
                
                return True
                
            else:
                
                self._jobs_awaiting_slot.append( job )
                
                return False
                
            
        
        def ProcessCurrentLoginJob():
            
            if self._current_login_process is not None:
                
                if self._current_login_process.IsDone():
                    
                    self._AssignCurrentLoginProcess( None )
                    
                
            
        
        def ProcessReadyJob( job: ClientNetworkingJobs.NetworkJob ):
            
            if job.IsDone():
                
                return False
                
            elif job.IsAsleep():
                
                return True
                
            elif len( self._jobs_running ) < self.MAX_JOBS:
                
                if self._pause_all_new_network_traffic:
                    
                    job.SetStatus( 'all new network traffic is paused' + HC.UNICODE_ELLIPSIS )
                    
                    job.Sleep( 2 )
                    
                    return True
                    
                elif self.controller.JustWokeFromSleep():
                    
                    job.SetStatus( 'looks like computer just woke up, waiting a bit' )
                    
                    job.Sleep( 5 )
                    
                    return True
                    
                elif self._active_domains_counter[ job.GetSecondLevelDomain() ] >= self.MAX_JOBS_PER_DOMAIN:
                    
                    job.SetStatus( 'waiting for other jobs on this domain to finish' )
                    
                    job.Sleep( 2 )
                    
                    return True
                    
                elif not job.TokensOK():
                    
                    return True
                    
                elif not job.DomainOK():
                    
                    return True
                    
                else:
                    
                    ClientNetworkingFunctions.NetworkReportMode( f'Network Job Starting: {job._method} {job._url}' )
                    
                    self._active_domains_counter[ job.GetSecondLevelDomain() ] += 1
                    
                    self.controller.CallToThread( job.Start )
                    
                    self._jobs_running.append( job )
                    
                    return False
                    
                
            else:
                
                job.SetStatus( 'waiting for other jobs to finish' + HC.UNICODE_ELLIPSIS )
                
                return True
                
            
        
        def ProcessRunningJob( job: ClientNetworkingJobs.NetworkJob ):
            
            if job.IsDone():
                
                ClientNetworkingFunctions.NetworkReportMode( f'Network Job Done: {job._method} {job._url}' )
                
                second_level_domain = job.GetSecondLevelDomain()
                
                self._active_domains_counter[ second_level_domain ] -= 1
                
                if self._active_domains_counter[ second_level_domain ] == 0:
                    
                    del self._active_domains_counter[ second_level_domain ]
                    
                
                return False
                
            else:
                
                return True
                
            
        
        self._is_running = True
        
        while not ( self._local_shutdown or HG.model_shutdown ):
            
            with self._lock:
                
                self._jobs_awaiting_validity = list( filter( ProcessValidationJob, self._jobs_awaiting_validity ) )
                
                ProcessCurrentValidationJob()
                
                self._jobs_awaiting_bandwidth = list( filter( ProcessBandwidthJob, self._jobs_awaiting_bandwidth ) )
                
                ProcessForceLogins()
                
                self._jobs_awaiting_login = list( filter( ProcessLoginJob, self._jobs_awaiting_login ) )
                
                ProcessCurrentLoginJob()
                
                self._jobs_awaiting_slot = list( filter( ProcessReadyJob, self._jobs_awaiting_slot ) )
                
                self._jobs_running = list( filter( ProcessRunningJob, self._jobs_running ) )
                
            
            # we want to catch the rollover of the second for bandwidth jobs
            
            now_with_subsecond = time.time()
            subsecond_part = now_with_subsecond % 1
            
            time_until_next_second = 1.0 - subsecond_part
            
            self._new_work_to_do.wait( time_until_next_second )
            
            self._new_work_to_do.clear()
            
        
        self._is_running = False
        
        self._is_shutdown = True
        
    
    def PausePlayNewJobs( self ):
        
        self._pause_all_new_network_traffic = not self._pause_all_new_network_traffic
        
        self.controller.new_options.SetBoolean( 'pause_all_new_network_traffic', self._pause_all_new_network_traffic )
        
        if not self._pause_all_new_network_traffic:
            
            self.controller.pub( 'notify_network_traffic_unpaused' )
            
        
    
    def RefreshOptions( self ):
        
        with self._lock:
            
            self.MAX_JOBS = self.controller.new_options.GetInteger( 'max_network_jobs' )
            self.MAX_JOBS_PER_DOMAIN = self.controller.new_options.GetInteger( 'max_network_jobs_per_domain' )
            
        
    
    def Shutdown( self ):
        
        self._local_shutdown = True
        
        self._new_work_to_do.set()
        
    
