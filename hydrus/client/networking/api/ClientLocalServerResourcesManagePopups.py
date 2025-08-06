from hydrus.core import HydrusExceptions
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIPopupMessages
from hydrus.client.networking import ClientNetworkingJobs
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.networking.api import ClientLocalServerResources

def JobStatusToDict( job_status: ClientThreading.JobStatus ):
        
        return_dict = {
            'key' : job_status.GetKey().hex(),
            'creation_time' : job_status.GetCreationTime(),
            'status_title' : job_status.GetStatusTitle(),
            'status_text_1' : job_status.GetStatusText( 1 ),
            'status_text_2' : job_status.GetStatusText( 2 ),
            'traceback' : job_status.GetTraceback(),
            'had_error' : job_status.HadError(),
            'is_cancellable' : job_status.IsCancellable(),
            'is_cancelled' : job_status.IsCancelled(),
            'is_done' : job_status.IsDone(),
            'is_pausable' : job_status.IsPausable(),
            'is_paused' : job_status.IsPaused(),
            'nice_string' : job_status.ToString(),
            'popup_gauge_1' : job_status.GetIfHasVariable( 'popup_gauge_1' ),
            'popup_gauge_2' : job_status.GetIfHasVariable( 'popup_gauge_2' ),
            'attached_files_mergable' : job_status.GetIfHasVariable( 'attached_files_mergable' ),
            'api_data' : job_status.GetIfHasVariable( 'api_data' )
        }
        
        files_object = job_status.GetFiles()
        
        if files_object is not None:
            
            ( hashes, label ) = files_object
            
            return_dict[ 'files' ] = {
                'hashes' : [ hash.hex() for hash in hashes ],
                'label': label
            }
            
        
        user_callable = job_status.GetUserCallable()
        
        if user_callable is not None:
            
            return_dict[ 'user_callable_label' ] = user_callable.GetLabel()
            
        
        network_job: ClientNetworkingJobs.NetworkJob = job_status.GetNetworkJob()
        
        if network_job is not None:
            
            ( status_text, current_speed, bytes_read, bytes_to_read ) = network_job.GetStatus()
            
            network_job_dict = {
                'url' : network_job.GetURL(),
                'waiting_on_connection_error' : network_job.CurrentlyWaitingOnConnectionError(),
                'domain_ok' : network_job.DomainOK(),
                'waiting_on_serverside_bandwidth' : network_job.CurrentlyWaitingOnServersideBandwidth(),
                'no_engine_yet' : network_job.NoEngineYet(),
                'has_error' : network_job.HasError(),
                'total_data_used' : network_job.GetTotalDataUsed(),
                'is_done' : network_job.IsDone(),
                'status_text' : status_text,
                'current_speed' : current_speed,
                'bytes_read' : bytes_read,
                'bytes_to_read' : bytes_to_read
            }
            
            return_dict[ 'network_job' ] = network_job_dict
            
        
        return { k: v for k, v in return_dict.items() if v is not None }
        
    

class HydrusResourceClientAPIRestrictedManagePopups( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_MANAGE_POPUPS )
        
    

class HydrusResourceClientAPIRestrictedManagePopupsAddPopup( HydrusResourceClientAPIRestrictedManagePopups ):
    
    def _threadDoPOSTJob(self, request: HydrusServerRequest.HydrusRequest ):
        
        pausable = request.parsed_request_args.GetValue( 'is_pausable', bool, default_value = False )
        cancellable = request.parsed_request_args.GetValue( 'is_cancellable', bool, default_value = False )
        
        job_status = ClientThreading.JobStatus( pausable = pausable, cancellable = cancellable )
        
        if request.parsed_request_args.GetValue( 'attached_files_mergable', bool, default_value = False ):
            
            job_status.SetVariable( 'attached_files_mergable', True )
            
        
        HandlePopupUpdate( job_status, request )
        
        CG.client_controller.pub( 'message', job_status )
        
        body_dict = {
            'job_status': JobStatusToDict( job_status )
        }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

def GetJobStatusFromRequest( request: HydrusServerRequest.HydrusRequest ) -> ClientThreading.JobStatus:
    
    job_status_key = request.parsed_request_args.GetValue( 'job_status_key', bytes )
    
    job_status_queue: ClientGUIPopupMessages.JobStatusPopupQueue = CG.client_controller.job_status_popup_queue
    
    job_status = job_status_queue.GetJobStatus( job_status_key )
    
    if job_status is None:
        
        raise HydrusExceptions.BadRequestException( 'This job key doesn\'t exist!' )
        
    
    return job_status
    

class HydrusResourceClientAPIRestrictedManagePopupsCallUserCallable( HydrusResourceClientAPIRestrictedManagePopups ):
    
    def _threadDoPOSTJob(self, request: HydrusServerRequest.HydrusRequest ):
        
        job_status = GetJobStatusFromRequest( request )
        
        user_callable = job_status.GetUserCallable()
        
        if user_callable is None:
            
            raise HydrusExceptions.BadRequestException('This job doesn\'t have a user callable!')
            
        
        CG.client_controller.CallBlockingToQt( CG.client_controller.gui, user_callable )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManagePopupsCancelPopup( HydrusResourceClientAPIRestrictedManagePopups ):
    
    def _threadDoPOSTJob(self, request: HydrusServerRequest.HydrusRequest ):
        
        job_status = GetJobStatusFromRequest( request )
        
        if job_status.IsCancellable():
            
            job_status.Cancel()
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManagePopupsDismissPopup( HydrusResourceClientAPIRestrictedManagePopups ):
    
    def _threadDoPOSTJob(self, request: HydrusServerRequest.HydrusRequest ):
        
        job_status = GetJobStatusFromRequest( request )
        
        if job_status.IsDone():
            
            job_status.FinishAndDismiss()
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManagePopupsFinishPopup( HydrusResourceClientAPIRestrictedManagePopups ):
    
    def _threadDoPOSTJob(self, request: HydrusServerRequest.HydrusRequest ):
        
        job_status = GetJobStatusFromRequest( request )
        
        job_status.Finish()
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManagePopupsFinishAndDismissPopup( HydrusResourceClientAPIRestrictedManagePopups ):
    
    def _threadDoPOSTJob(self, request: HydrusServerRequest.HydrusRequest ):
        
        job_status = GetJobStatusFromRequest( request )
        
        seconds = request.parsed_request_args.GetValueOrNone( 'seconds', int )
        
        job_status.FinishAndDismiss( seconds )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManagePopupsGetPopups( HydrusResourceClientAPIRestrictedManagePopups ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        job_status_queue: ClientGUIPopupMessages.JobStatusPopupQueue = CG.client_controller.job_status_popup_queue        
        
        only_in_view = request.parsed_request_args.GetValue( 'only_in_view', bool, default_value = False )
        
        job_statuses = job_status_queue.GetJobStatuses( only_in_view )
        
        body_dict = {
            'job_statuses' : [JobStatusToDict( job ) for job in job_statuses]
        }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

def HandlePopupUpdate( job_status: ClientThreading.JobStatus, request: HydrusServerRequest.HydrusRequest ):
    
    def HandleGenericVariable( name: str, type: type ):
        
        if name in request.parsed_request_args:
            
            value = request.parsed_request_args.GetValueOrNone( name, type )
            
            if value is not None:
                
                job_status.SetVariable( name, value )
                
            else:
                
                job_status.DeleteVariable( name )
                
            
        
    
    if 'status_title' in request.parsed_request_args:
        
        status_title = request.parsed_request_args.GetValueOrNone( 'status_title', str )
        
        if status_title is not None:
            
            job_status.SetStatusTitle( status_title )
            
        else:
            
            job_status.DeleteStatusTitle()
            
        
    
    if 'status_text_1' in request.parsed_request_args:
        
        status_text = request.parsed_request_args.GetValueOrNone( 'status_text_1', str )
        
        if status_text is not None:
            
            job_status.SetStatusText( status_text, 1 )
            
        else:
            
            job_status.DeleteStatusText()
            
        
    
    if 'status_text_2' in request.parsed_request_args:
        
        status_text_2 = request.parsed_request_args.GetValueOrNone( 'status_text_2', str )
        
        if status_text_2 is not None:
            
            job_status.SetStatusText( status_text_2, 2 )
            
        else:
            
            job_status.DeleteStatusText( level = 2 )
            
        
    
    HandleGenericVariable( 'api_data', dict )
    
    for name in ['popup_gauge_1', 'popup_gauge_2']:
        
        if name in request.parsed_request_args:
            
            value = request.parsed_request_args.GetValueOrNone( name, list, expected_list_type = int )
            
            if value is not None:
                
                if len(value) != 2:
                    
                    raise HydrusExceptions.BadRequestException( 'The parameter "{}" had an invalid number of items!'.format( name ) )
                    
                
                job_status.SetVariable( name, value )
                
            else:
                
                job_status.DeleteVariable( name )
                
            
        
    
    files_label = request.parsed_request_args.GetValueOrNone( 'files_label', str )
    
    hashes = ClientLocalServerCore.ParseHashes( request, True )
    
    if hashes is not None:
        
        if len(hashes) > 0 and files_label is None:
            
            raise HydrusExceptions.BadRequestException( '"files_label" is required to add files to a popup!' )
            
        
        job_status.SetFiles( hashes, files_label )
        
    

class HydrusResourceClientAPIRestrictedManagePopupsUpdatePopup( HydrusResourceClientAPIRestrictedManagePopups ):
    
    def _threadDoPOSTJob(self, request: HydrusServerRequest.HydrusRequest ):
        
        job_status = GetJobStatusFromRequest( request )
        
        HandlePopupUpdate( job_status, request )
        
        body_dict = {
            'job_status': JobStatusToDict( job_status )
        }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
