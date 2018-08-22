import ClientConstants as CC
import collections
import cPickle
import cStringIO
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusNetwork
import HydrusNetworking
import HydrusPaths
import HydrusSerialisable
import itertools
import os
import random
import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import threading
import time
import traceback
import urllib
import urlparse
import yaml

urllib3.disable_warnings( InsecureRequestWarning )

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
    
    MAX_JOBS_PER_DOMAIN = 3 # also turn this into an option
    MAX_JOBS = 15 # turn this into an option
    
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
        
        self._new_work_to_do = threading.Event()
        
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
        
    
    def AddJob( self, job ):
        
        if HG.network_report_mode:
            
            HydrusData.ShowText( 'Network Job Added: ' + job._method + ' ' + job._url )
            
        
        with self._lock:
            
            job.engine = self
            
            self._jobs_awaiting_validity.append( job )
            
        
        self._new_work_to_do.set()
        
    
    def GetJobsSnapshot( self ):
        
        with self._lock:
            
            jobs = []
            
            jobs.extend( ( ( JOB_STATUS_AWAITING_VALIDITY, j ) for j in self._jobs_awaiting_validity ) )
            jobs.extend( ( ( JOB_STATUS_AWAITING_BANDWIDTH, j ) for j in self._jobs_awaiting_bandwidth ) )
            jobs.extend( ( ( JOB_STATUS_AWAITING_LOGIN, j ) for j in self._jobs_awaiting_login ) )
            jobs.extend( ( ( JOB_STATUS_AWAITING_SLOT, j ) for j in self._jobs_awaiting_slot ) )
            jobs.extend( ( ( JOB_STATUS_RUNNING, j ) for j in self._jobs_running ) )
            
            return jobs
            
        
    
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
                        
                        job.SetStatus( u'validation presented to user\u2026' )
                        
                    else:
                        
                        job.SetStatus( u'waiting in user validation queue\u2026' )
                        
                        job.Sleep( 5 )
                        
                    
                    return True
                    
                else:
                    
                    error_text = u'network context not currently valid!'
                    
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
                
            
        
        def ProcessLoginJob( job ):
            
            if job.IsDone():
                
                return False
                
            elif job.IsAsleep():
                
                return True
                
            elif job.NeedsLogin():
                
                try:
                    
                    job.CheckCanLogin()
                    
                except Exception as e:
                    
                    job.SetError( e, HydrusData.ToUnicode( e ) )
                    
                    return False
                    
                
                if self._current_login_process is None:
                    
                    login_process = job.GenerateLoginProcess()
                    
                    self.controller.CallToThread( login_process.Start )
                    
                    self._current_login_process = login_process
                    
                    job.SetStatus( u'logging in\u2026' )
                    
                else:
                    
                    job.SetStatus( u'waiting in login queue\u2026' )
                    
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
                
            elif len( self._jobs_running ) < self.MAX_JOBS:
                
                if self._pause_all_new_network_traffic:
                    
                    job.SetStatus( u'all new network traffic is paused\u2026' )
                    
                    return True
                    
                elif self.controller.JustWokeFromSleep():
                    
                    job.SetStatus( u'looks like computer just woke up, waiting a bit' )
                    
                    return True
                    
                elif self._active_domains_counter[ job.GetSecondLevelDomain() ] >= self.MAX_JOBS_PER_DOMAIN:
                    
                    job.SetStatus( u'waiting for a slot on this domain' )
                    
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
                
                job.SetStatus( u'waiting for slot\u2026' )
                
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
                
                self._jobs_awaiting_validity = filter( ProcessValidationJob, self._jobs_awaiting_validity )
                
                ProcessCurrentValidationJob()
                
                self._jobs_awaiting_bandwidth = filter( ProcessBandwidthJob, self._jobs_awaiting_bandwidth )
                
                self._jobs_awaiting_login = filter( ProcessLoginJob, self._jobs_awaiting_login )
                
                ProcessCurrentLoginJob()
                
                self._jobs_awaiting_slot = filter( ProcessReadyJob, self._jobs_awaiting_slot )
                
                self._jobs_running = filter( ProcessRunningJob, self._jobs_running )
                
            
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
        
    
    def Shutdown( self ):
        
        self._local_shutdown = True
        
        self._new_work_to_do.set()
        
    
