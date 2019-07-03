from . import ClientConstants as CC
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNetwork
from . import HydrusNetworking
from . import HydrusPaths
from . import HydrusSerialisable
import itertools
import os
import random
import requests
import urllib3
import threading
import time
import traceback
import urllib.parse
import yaml


JOB_STATUS_AWAITING_VALIDITY = 0
JOB_STATUS_AWAITING_BANDWIDTH = 1
JOB_STATUS_AWAITING_LOGIN = 2
JOB_STATUS_AWAITING_SLOT = 3
JOB_STATUS_RUNNING = 4

job_status_str_lookup = {}

job_status_str_lookup[ JOB_STATUS_AWAITING_VALIDITY ] = 'waiting for validation'
job_status_str_lookup[ JOB_STATUS_AWAITING_BANDWIDTH ] = 'waiting for bandwidth'
job_status_str_lookup[ JOB_STATUS_AWAITING_LOGIN ] = 'waiting for login'
job_status_str_lookup[ JOB_STATUS_AWAITING_SLOT ] = 'waiting for slot'
job_status_str_lookup[ JOB_STATUS_RUNNING ] = 'running'

class NetworkEngine( object ):
    
    def __init__( self, controller, bandwidth_manager, session_manager, domain_manager, login_manager ):
        
        self.controller = controller
        
        self.bandwidth_manager = bandwidth_manager
        self.session_manager = session_manager
        self.domain_manager = domain_manager
        self.login_manager = login_manager
        
        self.bandwidth_manager.engine = self
        self.session_manager.engine = self
        self.domain_manager.engine = self
        self.login_manager.engine = self
        
        self._lock = threading.Lock()
        
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
        
    
    def AddJob( self, job ):
        
        if HG.network_report_mode:
            
            HydrusData.ShowText( 'Network Job Added: ' + job._method + ' ' + job._url )
            
        
        with self._lock:
            
            job.engine = self
            
            self._jobs_awaiting_validity.append( job )
            
        
        self._new_work_to_do.set()
        
    
    def ForceLogins( self, domains_to_login ):
        
        with self._lock:
            
            self._domains_to_login.extend( domains_to_login )
            
            self._domains_to_login = HydrusData.DedupeList( self._domains_to_login )
            
        
    
    def GetJobsSnapshot( self ):
        
        with self._lock:
            
            jobs = []
            
            jobs.extend( ( ( JOB_STATUS_AWAITING_VALIDITY, j ) for j in self._jobs_awaiting_validity ) )
            jobs.extend( ( ( JOB_STATUS_AWAITING_BANDWIDTH, j ) for j in self._jobs_awaiting_bandwidth ) )
            jobs.extend( ( ( JOB_STATUS_AWAITING_LOGIN, j ) for j in self._jobs_awaiting_login ) )
            jobs.extend( ( ( JOB_STATUS_AWAITING_SLOT, j ) for j in self._jobs_awaiting_slot ) )
            jobs.extend( ( ( JOB_STATUS_RUNNING, j ) for j in self._jobs_running ) )
            
            return jobs
            
        
    
    def IsBusy( self ):
        
        with self._lock:
            
            return len( self._jobs_awaiting_validity ) + len( self._jobs_awaiting_bandwidth ) + len( self._jobs_awaiting_login ) + len( self._jobs_awaiting_slot ) + len( self._jobs_running ) > 50
            
        
    
    def IsRunning( self ):
        
        with self._lock:
            
            return self._is_running
            
        
    
    def IsShutdown( self ):
        
        with self._lock:
            
            return self._is_shutdown
            
        
    
    def MainLoop( self ):
        
        def ProcessValidationJob( job ):
            
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
                        
                        job.SetStatus( 'validation presented to user\u2026' )
                        
                    else:
                        
                        job.SetStatus( 'waiting in user validation queue\u2026' )
                        
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
                    
                
            
        
        def ProcessBandwidthJob( job ):
            
            if job.IsDone():
                
                return False
                
            elif job.IsAsleep():
                
                return True
                
            elif not job.BandwidthOK():
                
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
                
                self._current_login_process = login_process
                
            
        
        def ProcessLoginJob( job ):
            
            if job.IsDone():
                
                return False
                
            elif job.IsAsleep():
                
                return True
                
            elif job.NeedsLogin():
                
                try:
                    
                    job.CheckCanLogin()
                    
                except Exception as e:
                    
                    if job.WillingToWaitOnInvalidLogin():
                        
                        job.SetStatus( str( e ) )
                        
                        job.Sleep( 60 )
                        
                        return True
                        
                    else:
                        
                        if job.IsHydrusJob():
                            
                            message = 'This hydrus service (' + job.GetLoginNetworkContext().ToString() + ') could not do work because: {}'.format( str( e ) )
                            
                        else:
                            
                            message = 'This job\'s network context (' + job.GetLoginNetworkContext().ToString() + ') seems to have an invalid login. The error was: {}'.format( str( e ) )
                            
                        
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
                    
                    self._current_login_process = login_process
                    
                    job.SetStatus( 'logging in\u2026' )
                    
                else:
                    
                    job.SetStatus( 'waiting in login queue\u2026' )
                    
                    job.Sleep( 5 )
                    
                
                return True
                
            else:
                
                self._jobs_awaiting_slot.append( job )
                
                return False
                
            
        
        def ProcessCurrentLoginJob():
            
            if self._current_login_process is not None:
                
                if self._current_login_process.IsDone():
                    
                    self._current_login_process = None
                    
                
            
        
        def ProcessReadyJob( job ):
            
            if job.IsDone():
                
                return False
                
            elif job.IsAsleep():
                
                return True
                
            elif len( self._jobs_running ) < self.MAX_JOBS:
                
                if self._pause_all_new_network_traffic:
                    
                    job.SetStatus( 'all new network traffic is paused\u2026' )
                    
                    job.Sleep( 2 )
                    
                    return True
                    
                elif self.controller.JustWokeFromSleep():
                    
                    job.SetStatus( 'looks like computer just woke up, waiting a bit' )
                    
                    job.Sleep( 5 )
                    
                    return True
                    
                elif self._active_domains_counter[ job.GetSecondLevelDomain() ] >= self.MAX_JOBS_PER_DOMAIN:
                    
                    job.SetStatus( 'waiting for a slot on this domain' )
                    
                    job.Sleep( 2 )
                    
                    return True
                    
                elif not job.TokensOK():
                    
                    return True
                    
                else:
                    
                    if HG.network_report_mode:
                        
                        HydrusData.ShowText( 'Network Job Starting: ' + job._method + ' ' + job._url )
                        
                    
                    self._active_domains_counter[ job.GetSecondLevelDomain() ] += 1
                    
                    self.controller.CallToThread( job.Start )
                    
                    self._jobs_running.append( job )
                    
                    return False
                    
                
            else:
                
                job.SetStatus( 'waiting for a slot\u2026' )
                
                return True
                
            
        
        def ProcessRunningJob( job ):
            
            if job.IsDone():
                
                if HG.network_report_mode:
                    
                    HydrusData.ShowText( 'Network Job Done: ' + job._method + ' ' + job._url )
                    
                
                second_level_domain = job.GetSecondLevelDomain()
                
                self._active_domains_counter[ second_level_domain ] -= 1
                
                if self._active_domains_counter[ second_level_domain ] == 0:
                    
                    del self._active_domains_counter[ second_level_domain ]
                    
                
                return False
                
            else:
                
                return True
                
            
        
        self._is_running = True
        
        while not ( self._local_shutdown or self.controller.ModelIsShutdown() ):
            
            with self._lock:
                
                self._jobs_awaiting_validity = list(filter( ProcessValidationJob, self._jobs_awaiting_validity ))
                
                ProcessCurrentValidationJob()
                
                self._jobs_awaiting_bandwidth = list(filter( ProcessBandwidthJob, self._jobs_awaiting_bandwidth ))
                
                ProcessForceLogins()
                
                self._jobs_awaiting_login = list(filter( ProcessLoginJob, self._jobs_awaiting_login ))
                
                ProcessCurrentLoginJob()
                
                self._jobs_awaiting_slot = list(filter( ProcessReadyJob, self._jobs_awaiting_slot ))
                
                self._jobs_running = list(filter( ProcessRunningJob, self._jobs_running ))
                
            
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
        
    
    def RefreshOptions( self ):
        
        with self._lock:
            
            self.MAX_JOBS = self.controller.new_options.GetInteger( 'max_network_jobs' )
            self.MAX_JOBS_PER_DOMAIN = self.controller.new_options.GetInteger( 'max_network_jobs_per_domain' )
            
        
    
    def Shutdown( self ):
        
        self._local_shutdown = True
        
        self._new_work_to_do.set()
        
    
