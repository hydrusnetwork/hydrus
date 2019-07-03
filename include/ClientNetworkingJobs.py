import io
from . import ClientConstants as CC
from . import ClientNetworkingContexts
from . import ClientNetworkingDomain
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNetworking
from . import HydrusThreading
from . import HydrusText
import os
import requests
import threading
import traceback
import time
import urllib

def ConvertStatusCodeAndDataIntoExceptionInfo( status_code, data, is_hydrus_service = False ):
    
    ( error_text, encoding ) = HydrusText.NonFailingUnicodeDecode( data, 'utf-8' )
    
    print_long_error_text = True
    
    if status_code == 304:
        
        print_long_error_text = False
        
        eclass = HydrusExceptions.NotModifiedException
        
    elif status_code == 400:
        
        eclass = HydrusExceptions.BadRequestException
        
    elif status_code == 401:
        
        eclass = HydrusExceptions.MissingCredentialsException
        
    elif status_code == 403:
        
        eclass = HydrusExceptions.InsufficientCredentialsException
        
    elif status_code == 404:
        
        print_long_error_text = False
        
        eclass = HydrusExceptions.NotFoundException
        
    elif status_code == 419:
        
        eclass = HydrusExceptions.SessionException
        
    elif status_code == 426:
        
        eclass = HydrusExceptions.NetworkVersionException
        
    elif status_code == 509:
        
        eclass = HydrusExceptions.BandwidthException
        
    elif status_code >= 500:
        
        if is_hydrus_service and status_code == 503:
            
            eclass = HydrusExceptions.ServerBusyException
            
        else:
            
            eclass = HydrusExceptions.ServerException
            
        
    else:
        
        eclass = HydrusExceptions.NetworkException
        
    
    if len( error_text ) > 1024 and print_long_error_text:
        
        large_chunk = error_text[ : 512 * 1024 ]
        
        smaller_chunk = large_chunk[:256]
        
        HydrusData.DebugPrint( large_chunk )
        
        error_text = 'The server\'s error text was too long to display. The first part follows, while a larger chunk has been written to the log.'
        error_text += os.linesep
        error_text += smaller_chunk
        
    
    e = eclass( '{}: {}'.format( status_code, error_text ) )
    
    return ( e, error_text )
    
class NetworkJob( object ):
    
    WILLING_TO_WAIT_ON_INVALID_LOGIN = True
    IS_HYDRUS_SERVICE = False
    
    def __init__( self, method, url, body = None, referral_url = None, temp_path = None ):
        
        if body is not None and isinstance( body, str ):
            
            body = bytes( body, 'utf-8' )
            
        
        self.engine = None
        
        self._lock = threading.Lock()
        
        self._method = method
        self._url = url
        
        self._max_connection_attempts_allowed = 5
        
        self._domain = ClientNetworkingDomain.ConvertURLIntoDomain( self._url )
        self._second_level_domain = ClientNetworkingDomain.ConvertURLIntoSecondLevelDomain( self._url )
        
        self._body = body
        self._referral_url = referral_url
        self._temp_path = temp_path
        
        self._files = None
        self._for_login = False
        
        self._current_connection_attempt_number = 1
        
        self._additional_headers = {}
        
        self._creation_time = HydrusData.GetNow()
        
        self._bandwidth_tracker = HydrusNetworking.BandwidthTracker()
        
        self._wake_time = 0
        
        self._content_type = None
        
        self._encoding = 'utf-8'
        self._encoding_confirmed = False
        
        self._stream_io = io.BytesIO()
        
        self._error_exception = Exception( 'Exception not initialised.' ) # PyLint hint, wew
        self._error_exception = None
        self._error_text = None
        
        self._is_done_event = threading.Event()
        
        self._is_started = False
        self._is_done = False
        self._is_cancelled = False
        
        self._gallery_token_name = None
        self._gallery_token_consumed = False
        self._bandwidth_manual_override = False
        self._bandwidth_manual_override_delayed_timestamp = None
        
        self._last_time_ongoing_bandwidth_failed = 0
        
        self._status_text = 'initialising\u2026'
        self._num_bytes_read = 0
        self._num_bytes_to_read = 1
        
        self._file_import_options = None
        
        self._network_contexts = self._GenerateNetworkContexts()
        
        ( self._session_network_context, self._login_network_context ) = self._GenerateSpecificNetworkContexts()
        
    
    def _CanReattemptConnection( self ):
        
        return self._current_connection_attempt_number <= self._max_connection_attempts_allowed
        
    
    def _CanReattemptRequest( self ):
        
        if self._method == 'GET':
            
            max_attempts_allowed = 5
            
        elif self._method == 'POST':
            
            max_attempts_allowed = 1
            
        
        return self._current_connection_attempt_number <= max_attempts_allowed
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = []
        
        network_contexts.append( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT )
        
        domains = ClientNetworkingDomain.ConvertDomainIntoAllApplicableDomains( self._domain )
        
        network_contexts.extend( ( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain ) for domain in domains ) )
        
        return network_contexts
        
    
    def _GenerateSpecificNetworkContexts( self ):
        
        # we always store cookies in the larger session (even if the cookie itself refers to a subdomain in the session object)
        # but we can login to a specific subdomain
        
        session_network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, self._second_level_domain )
        login_network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, self._domain )
        
        return ( session_network_context, login_network_context )
        
    
    def _SendRequestAndGetResponse( self ):
        
        with self._lock:
            
            ncs = list( self._network_contexts )
            
        
        headers = self.engine.domain_manager.GetHeaders( ncs )
        
        with self._lock:
            
            method = self._method
            url = self._url
            data = self._body
            files = self._files
            
            if self.IS_HYDRUS_SERVICE:
                
                headers[ 'User-Agent' ] = 'hydrus client/' + str( HC.NETWORK_VERSION )
                
            
            if self._referral_url is not None:
                
                headers[ 'referer' ] = urllib.parse.quote( self._referral_url, "!#$%&'()*+,/:;=?@[]~" ) # quick and dirty way to quote this url when it comes here with full unicode chars. not perfect, but does the job
                
            
            for ( key, value ) in list(self._additional_headers.items()):
                
                headers[ key ] = value
                
            
            self._status_text = 'sending request\u2026'
            
            snc = self._session_network_context
            
        
        session = self.engine.session_manager.GetSession( snc )
        
        connect_timeout = HG.client_controller.new_options.GetInteger( 'network_timeout' )
        
        read_timeout = connect_timeout * 6
        
        response = session.request( method, url, data = data, files = files, headers = headers, stream = True, timeout = ( connect_timeout, read_timeout ) )
        
        return response
        
    
    def _IsCancelled( self ):
        
        if self._is_cancelled:
            
            return True
            
        
        if self.engine.controller.ModelIsShutdown():
            
            return True
            
        
        return False
        
    
    def _IsDone( self ):
        
        if self._is_done:
            
            return True
            
        
        if self.engine.controller.ModelIsShutdown() or HydrusThreading.IsThreadShuttingDown():
            
            return True
            
        
        return False
        
    
    def _ObeysBandwidth( self ):
        
        if self._bandwidth_manual_override:
            
            return False
            
        
        if self._bandwidth_manual_override_delayed_timestamp is not None and HydrusData.TimeHasPassed( self._bandwidth_manual_override_delayed_timestamp ):
            
            return False
            
        
        if self._method == 'POST':
            
            return False
            
        
        if self._for_login:
            
            return False
            
        
        return True
        
    
    def _OngoingBandwidthOK( self ):
        
        now = HydrusData.GetNow()
        
        if now == self._last_time_ongoing_bandwidth_failed: # it won't have changed, so no point spending any cpu checking
            
            return False
            
        else:
            
            result = self.engine.bandwidth_manager.CanContinueDownload( self._network_contexts )
            
            if not result:
                
                self._last_time_ongoing_bandwidth_failed = now
                
            
            return result
            
        
    
    def _ReadResponse( self, response, stream_dest, max_allowed = None ):
        
        with self._lock:
            
            if self._content_type is not None and self._content_type in HC.mime_enum_lookup:
                
                mime = HC.mime_enum_lookup[ self._content_type ]
                
            else:
                
                mime = None
                
            
            if 'content-length' in response.headers:
                
                self._num_bytes_to_read = int( response.headers[ 'content-length' ] )
                
                if max_allowed is not None and self._num_bytes_to_read > max_allowed:
                    
                    raise HydrusExceptions.NetworkException( 'The url was apparently ' + HydrusData.ToHumanBytes( self._num_bytes_to_read ) + ' but the max network size for this type of job is ' + HydrusData.ToHumanBytes( max_allowed ) + '!' )
                    
                
                if self._file_import_options is not None:
                    
                    is_complete_file_size = True
                    
                    self._file_import_options.CheckNetworkDownload( mime, self._num_bytes_to_read, is_complete_file_size )
                    
                
            else:
                
                self._num_bytes_to_read = None
                
            
        
        num_bytes_read_is_accurate = True
        
        for chunk in response.iter_content( chunk_size = 65536 ):
            
            if self._IsCancelled():
                
                return
                
            
            stream_dest.write( chunk )
            
            total_bytes_read = response.raw.tell()
            
            if total_bytes_read == 0:
                
                # this seems to occur when the response is chunked transfer encoding (note, no Content-Length)
                # there's no great way to track raw bytes read in this case. the iter_content chunk can be unzipped from that
                # nonetheless, requests does raise ChunkedEncodingError if it stops early, so not a huge deal to miss here, just slightly off bandwidth tracking
                
                num_bytes_read_is_accurate = False
                
                chunk_num_bytes = len( chunk )
                
                self._num_bytes_read += chunk_num_bytes
                
            else:
                
                chunk_num_bytes = total_bytes_read - self._num_bytes_read
                
                self._num_bytes_read = total_bytes_read
                
            
            with self._lock:
                
                if self._num_bytes_to_read is not None and num_bytes_read_is_accurate and self._num_bytes_read > self._num_bytes_to_read:
                    
                    raise HydrusExceptions.NetworkException( 'Too much data: Was expecting {} but server continued responding!'.format( HydrusData.ToHumanBytes( self._num_bytes_to_read ) ) )
                    
                
                if max_allowed is not None and self._num_bytes_read > max_allowed:
                    
                    raise HydrusExceptions.NetworkException( 'The url exceeded the max network size for this type of job, which is ' + HydrusData.ToHumanBytes( max_allowed ) + '!' )
                    
                
                if self._file_import_options is not None:
                    
                    is_complete_file_size = False
                    
                    self._file_import_options.CheckNetworkDownload( mime, self._num_bytes_read, is_complete_file_size )
                    
                
            
            self._ReportDataUsed( chunk_num_bytes )
            self._WaitOnOngoingBandwidth()
            
            if HG.view_shutdown:
                
                raise HydrusExceptions.ShutdownException()
                
            
        
        if self._num_bytes_to_read is not None and num_bytes_read_is_accurate and self._num_bytes_read < self._num_bytes_to_read:
            
            raise HydrusExceptions.ShouldReattemptNetworkException( 'Incomplete response: Was expecting {} but actually got {} !'.format( HydrusData.ToHumanBytes( self._num_bytes_to_read ), HydrusData.ToHumanBytes( self._num_bytes_read ) ) )
            
        
    
    def _ReportDataUsed( self, num_bytes ):
        
        self._bandwidth_tracker.ReportDataUsed( num_bytes )
        
        self.engine.bandwidth_manager.ReportDataUsed( self._network_contexts, num_bytes )
        
    
    def _SetCancelled( self ):
        
        self._is_cancelled = True
        
        self._SetDone()
        
    
    def _SetError( self, e, error ):
        
        self._error_exception = e
        self._error_text = error
        
        if HG.network_report_mode:
            
            HydrusData.ShowText( 'Network error should follow:' )
            HydrusData.ShowException( e )
            HydrusData.ShowText( error )
            
        
        self._SetDone()
        
    
    def _SetDone( self ):
        
        self._is_done = True
        
        self._is_done_event.set()
        
    
    def _Sleep( self, seconds ):
        
        self._wake_time = HydrusData.GetNow() + seconds
        
    
    def _WaitOnConnectionError( self, status_text ):
        
        time_to_try_again = HydrusData.GetNow() + ( ( self._current_connection_attempt_number - 1 ) * 60 )
        
        while not HydrusData.TimeHasPassed( time_to_try_again ) and not self._IsCancelled():
            
            with self._lock:
                
                self._status_text = status_text + ' - retrying in {}'.format( HydrusData.TimestampToPrettyTimeDelta( time_to_try_again ) )
                
            
            time.sleep( 1 )
            
        
    
    def _WaitOnOngoingBandwidth( self ):
        
        while not self._OngoingBandwidthOK() and not self._IsCancelled():
            
            time.sleep( 0.1 )
            
        
    
    def AddAdditionalHeader( self, key, value ):
        
        with self._lock:
            
            self._additional_headers[ key ] = value
            
        
    
    def BandwidthOK( self ):
        
        with self._lock:
            
            if self._ObeysBandwidth():
                
                result = self.engine.bandwidth_manager.TryToStartRequest( self._network_contexts )
                
                if result:
                    
                    self._bandwidth_tracker.ReportRequestUsed()
                    
                else:
                    
                    ( bandwidth_waiting_duration, bandwidth_network_context ) = self.engine.bandwidth_manager.GetWaitingEstimateAndContext( self._network_contexts )
                    
                    will_override = self._bandwidth_manual_override_delayed_timestamp is not None
                    
                    override_coming_first = False
                    
                    if will_override:
                        
                        override_waiting_duration = self._bandwidth_manual_override_delayed_timestamp - HydrusData.GetNow()
                        
                        override_coming_first = override_waiting_duration < bandwidth_waiting_duration
                        
                    
                    just_now_threshold = 2
                    
                    if override_coming_first:
                        
                        waiting_duration = override_waiting_duration
                        
                        waiting_str = 'overriding bandwidth ' + HydrusData.TimestampToPrettyTimeDelta( self._bandwidth_manual_override_delayed_timestamp, just_now_string = 'imminently', just_now_threshold = just_now_threshold )
                        
                    else:
                        
                        waiting_duration = bandwidth_waiting_duration
                        
                        waiting_str = 'bandwidth free ' + HydrusData.TimestampToPrettyTimeDelta( HydrusData.GetNow() + waiting_duration, just_now_string = 'imminently', just_now_threshold = just_now_threshold )
                        
                    
                    waiting_str += '\u2026 (' + bandwidth_network_context.ToHumanString() + ')'
                    
                    self._status_text = waiting_str
                    
                    if waiting_duration > 1200:
                        
                        self._Sleep( 30 )
                        
                    elif waiting_duration > 120:
                        
                        self._Sleep( 10 )
                        
                    elif waiting_duration > 10:
                        
                        self._Sleep( 1 )
                        
                    
                
                return result
                
            else:
                
                self._bandwidth_tracker.ReportRequestUsed()
                
                self.engine.bandwidth_manager.ReportRequestUsed( self._network_contexts )
                
                return True
                
            
        
    
    def Cancel( self, status_text = None ):
        
        with self._lock:
            
            if status_text is None:
                
                status_text = 'cancelled!'
                
            
            self._status_text = status_text
            
            self._SetCancelled()
            
        
    
    def CanValidateInPopup( self ):
        
        with self._lock:
            
            return self.engine.domain_manager.CanValidateInPopup( self._network_contexts )
            
        
    
    def CheckCanLogin( self ):
        
        with self._lock:
            
            if self._for_login:
                
                raise HydrusExceptions.ValidationException( 'Login jobs should not be asked if they can login!' )
                
            else:
                
                return self.engine.login_manager.CheckCanLogin( self._login_network_context )
                
            
        
    
    def GenerateLoginProcess( self ):
        
        with self._lock:
            
            if self._for_login:
                
                raise Exception( 'Login jobs should not be asked to generate login processes!' )
                
            else:
                
                return self.engine.login_manager.GenerateLoginProcess( self._login_network_context )
                
            
        
    
    def GenerateValidationPopupProcess( self ):
        
        with self._lock:
            
            return self.engine.domain_manager.GenerateValidationPopupProcess( self._network_contexts )
            
        
    
    def GetContentBytes( self ):
        
        with self._lock:
            
            self._stream_io.seek( 0 )
            
            return self._stream_io.read()
            
        
    
    def GetContentText( self ):
        
        data = self.GetContentBytes()
        
        ( text, self._encoding ) = HydrusText.NonFailingUnicodeDecode( data, self._encoding )
        
        return text
        
    
    def GetContentType( self ):
        
        with self._lock:
            
            return self._content_type
            
        
    
    def GetCreationTime( self ):
        
        with self._lock:
            
            return self._creation_time
            
        
    
    def GetDomain( self ):
        
        with self._lock:
            
            return self._domain
            
        
    
    def GetErrorException( self ):
        
        with self._lock:
            
            return self._error_exception
            
        
    
    def GetErrorText( self ):
        
        with self._lock:
            
            return self._error_text
            
        
    
    def GetLoginNetworkContext( self ):
        
        with self._lock:
            
            return self._login_network_context
            
        
    
    def GetNetworkContexts( self ):
        
        with self._lock:
            
            return list( self._network_contexts )
            
        
    
    def GetSecondLevelDomain( self ):
        
        with self._lock:
            
            return self._second_level_domain
            
        
    
    def GetSession( self ):
        
        with self._lock:
            
            snc = self._session_network_context
            
        
        session = self.engine.session_manager.GetSession( snc )
        
        return session
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._status_text, self._bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1 ), self._num_bytes_read, self._num_bytes_to_read )
            
        
    
    def GetTotalDataUsed( self ):
        
        with self._lock:
            
            return self._bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, None )
            
        
    
    def GetURL( self ):
        
        with self._lock:
            
            return self._url
            
        
    
    def HasError( self ):
        
        with self._lock:
            
            return self._error_exception is not None
            
        
    
    def IsAsleep( self ):
        
        with self._lock:
            
            return not HydrusData.TimeHasPassed( self._wake_time )
            
        
    
    def IsCancelled( self ):
        
        with self._lock:
            
            return self._IsCancelled()
            
        
    
    def IsDone( self ):
        
        with self._lock:
            
            return self._IsDone()
            
        
    
    def IsHydrusJob( self ):
        
        with self._lock:
            
            return False
            
        
    
    def IsValid( self ):
        
        with self._lock:
            
            return self.engine.domain_manager.IsValid( self._network_contexts )
            
        
    
    def NeedsLogin( self ):
        
        with self._lock:
            
            if self._for_login:
                
                return False
                
            else:
                
                return self.engine.login_manager.NeedsLogin( self._login_network_context )
                
            
        
    
    def NoEngineYet( self ):
        
        return self.engine is None
        
    
    def ObeysBandwidth( self ):
        
        return self._ObeysBandwidth()
        
    
    def OnlyTryConnectionOnce( self ):
        
        self._max_connection_attempts_allowed = 1
        
    
    def OverrideBandwidth( self, delay = None ):
        
        with self._lock:
            
            if delay is None:
                
                self._bandwidth_manual_override = True
                
                self._wake_time = 0
                
            else:
                
                self._bandwidth_manual_override_delayed_timestamp = HydrusData.GetNow() + delay
                
                self._wake_time = min( self._wake_time, self._bandwidth_manual_override_delayed_timestamp + 1 )
                
            
        
    
    def OverrideToken( self ):
        
        with self._lock:
            
            self._gallery_token_consumed = True
            
            self._wake_time = 0
            
        
    
    def SetError( self, e, error ):
        
        with self._lock:
            
            self._SetError( e, error )
            
        
    
    def SetFiles( self, files ):
        
        with self._lock:
            
            self._files = files
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def SetForLogin( self, for_login ):
        
        with self._lock:
            
            self._for_login = for_login
            
        
    
    def SetGalleryToken( self, token_name ):
        
        with self._lock:
            
            self._gallery_token_name = token_name
            
        
    
    def SetStatus( self, text ):
        
        with self._lock:
            
            self._status_text = text
            
        
    
    def Sleep( self, seconds ):
        
        with self._lock:
            
            self._Sleep( seconds )
            
        
    
    def Start( self ):
        
        try:
            
            with self._lock:
                
                self._is_started = True
                self._status_text = 'job started'
                
            
            request_completed = False
            
            while not request_completed:
                
                try:
                    
                    if self._IsCancelled():
                        
                        return
                        
                    
                    response = self._SendRequestAndGetResponse()
                    
                    with self._lock:
                        
                        if self._body is not None:
                            
                            self._ReportDataUsed( len( self._body ) )
                            
                        
                    
                    if 'Content-Type' in response.headers:
                        
                        self._content_type = response.headers[ 'Content-Type' ]
                        
                    
                    if response.ok:
                        
                        with self._lock:
                            
                            self._status_text = 'downloading\u2026'
                            
                        
                        if response.encoding is not None:
                            
                            encoding = response.encoding
                            
                            # we'll default to utf-8 rather than ISO-8859-1
                            we_got_lame_iso_default_from_requests = encoding == 'ISO-8859-1' and ( self._content_type is None or encoding not in self._content_type )
                            
                            if not we_got_lame_iso_default_from_requests:
                                
                                self._encoding = encoding
                                
                            
                        
                        if self._temp_path is None:
                            
                            self._ReadResponse( response, self._stream_io, 104857600 )
                            
                        else:
                            
                            with open( self._temp_path, 'wb' ) as f:
                                
                                self._ReadResponse( response, f )
                                
                            
                        
                        with self._lock:
                            
                            self._status_text = 'done!'
                            
                        
                    else:
                        
                        with self._lock:
                            
                            self._status_text = str( response.status_code ) + ' - ' + str( response.reason )
                            
                        
                        self._ReadResponse( response, self._stream_io, 104857600 )
                        
                        with self._lock:
                            
                            self._stream_io.seek( 0 )
                            
                            data = self._stream_io.read()
                            
                            ( e, error_text ) = ConvertStatusCodeAndDataIntoExceptionInfo( response.status_code, data, self.IS_HYDRUS_SERVICE )
                            
                            self._SetError( e, error_text )
                            
                        
                    
                    request_completed = True
                    
                except HydrusExceptions.ShouldReattemptNetworkException as e:
                    
                    self._current_connection_attempt_number += 1
                    
                    if not self._CanReattemptRequest():
                        
                        raise HydrusExceptions.NetworkException( 'Ran out of reattempts on this error: ' + str( e ) )
                        
                    
                    self._WaitOnConnectionError( 'server suddenly stopped delivering data' )
                    
                except requests.exceptions.ChunkedEncodingError:
                    
                    self._current_connection_attempt_number += 1
                    
                    if not self._CanReattemptRequest():
                        
                        raise HydrusExceptions.ConnectionException( 'Unable to complete request--it broke mid-way!' )
                        
                    
                    self._WaitOnConnectionError( 'connection broke mid-request' )
                    
                except ( requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout ):
                    
                    self._current_connection_attempt_number += 1
                    
                    if not self._CanReattemptConnection():
                        
                        raise HydrusExceptions.ConnectionException( 'Could not connect!' )
                        
                    
                    self._WaitOnConnectionError( 'connection failed' )
                    
                except requests.exceptions.ReadTimeout:
                    
                    self._current_connection_attempt_number += 1
                    
                    if not self._CanReattemptRequest():
                        
                        raise HydrusExceptions.ConnectionException( 'Connection successful, but reading response timed out!' )
                        
                    
                    self._WaitOnConnectionError( 'read timed out' )
                    
                
            
        except Exception as e:
            
            with self._lock:
                
                trace = traceback.format_exc()
                
                if not isinstance( e, ( HydrusExceptions.ConnectionException, HydrusExceptions.SizeException ) ):
                    
                    HydrusData.Print( trace )
                    
                
                self._status_text = 'Error: ' + str( e )
                
                self._SetError( e, trace )
                
            
        finally:
            
            with self._lock:
                
                self._SetDone()
                
            
        
    
    def TokensOK( self ):
        
        with self._lock:
            
            need_token = self._gallery_token_name is not None and not self._gallery_token_consumed
            
            sld = self._second_level_domain
            gtn = self._gallery_token_name
            
        
        if need_token:
            
            ( consumed, next_timestamp ) = self.engine.bandwidth_manager.TryToConsumeAGalleryToken( sld, gtn )
            
            with self._lock:
                
                if consumed:
                    
                    self._status_text = 'slot consumed, starting soon'
                    
                    self._gallery_token_consumed = True
                    
                else:
                    
                    self._status_text = 'waiting for a ' + self._gallery_token_name + ' slot: next ' + HydrusData.TimestampToPrettyTimeDelta( next_timestamp, just_now_threshold = 1 )
                    
                    self._Sleep( 1 )
                    
                    return False
                    
                
            
        
        return True
        
    
    def WaitUntilDone( self ):
        
        while True:
            
            self._is_done_event.wait( 5 )
            
            if self.IsDone():
                
                break
                
            
        
        with self._lock:
            
            if self.engine.controller.ModelIsShutdown() or HydrusThreading.IsThreadShuttingDown():
                
                raise HydrusExceptions.ShutdownException()
                
            elif self._error_exception is not None:
                
                if isinstance( self._error_exception, Exception ):
                    
                    raise self._error_exception
                    
                else:
                    
                    raise Exception( 'Problem in network error handling.' )
                    
                
            elif self._IsCancelled():
                
                if self._method == 'POST':
                    
                    message = 'Upload cancelled: ' + self._status_text
                    
                else:
                    
                    message = 'Download cancelled: ' + self._status_text
                    
                
                raise HydrusExceptions.CancelledException( message )
                
            
        
    
    def WillingToWaitOnInvalidLogin( self ):
        
        return self.WILLING_TO_WAIT_ON_INVALID_LOGIN
        
    
class NetworkJobDownloader( NetworkJob ):
    
    def __init__( self, downloader_page_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._downloader_page_key = downloader_page_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOWNLOADER_PAGE, self._downloader_page_key ) )
        
        return network_contexts
        
    
class NetworkJobSubscription( NetworkJob ):
    
    WILLING_TO_WAIT_ON_INVALID_LOGIN = False
    
    def __init__( self, subscription_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._subscription_key = subscription_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION, self._subscription_key ) )
        
        return network_contexts
        
    
class NetworkJobHydrus( NetworkJob ):
    
    WILLING_TO_WAIT_ON_INVALID_LOGIN = False
    IS_HYDRUS_SERVICE = True
    
    def __init__( self, service_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._service_key = service_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _CheckHydrusVersion( self, service_type, response ):
        
        service_string = HC.service_string_lookup[ service_type ]
        
        headers = response.headers
        
        if 'server' not in headers or service_string not in headers[ 'server' ]:
            
            raise HydrusExceptions.WrongServiceTypeException( 'Target was not a ' + service_string + '!' )
            
        
        server_header = headers[ 'server' ]
        
        ( service_string_gumpf, network_version ) = server_header.split( '/' )
        
        network_version = int( network_version )
        
        if network_version != HC.NETWORK_VERSION:
            
            if network_version > HC.NETWORK_VERSION:
                
                message = 'Your client is out of date; please download the latest release.'
                
            else:
                
                message = 'The server is out of date; please ask its admin to update to the latest release.'
                
            
            raise HydrusExceptions.NetworkVersionException( 'Network version mismatch! The server\'s network version was ' + str( network_version ) + ', whereas your client\'s is ' + str( HC.NETWORK_VERSION ) + '! ' + message )
            
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = []
        
        network_contexts.append( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT )
        network_contexts.append( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, self._service_key ) )
        
        return network_contexts
        
    
    def _GenerateSpecificNetworkContexts( self ):
        
        # we store cookies on and login to the same hydrus-specific context
        
        session_network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, self._service_key )
        login_network_context = session_network_context
        
        return ( session_network_context, login_network_context )
        
    
    def _ReportDataUsed( self, num_bytes ):
        
        service = self.engine.controller.services_manager.GetService( self._service_key )
        
        service_type = service.GetServiceType()
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            account = service.GetAccount()
            
            account.ReportDataUsed( num_bytes )
            
        
        NetworkJob._ReportDataUsed( self, num_bytes )
        
    
    def _SendRequestAndGetResponse( self ):
        
        service = self.engine.controller.services_manager.GetService( self._service_key )
        
        service_type = service.GetServiceType()
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            account = service.GetAccount()
            
            account.ReportRequestUsed()
            
        
        response = NetworkJob._SendRequestAndGetResponse( self )
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            self._CheckHydrusVersion( service_type, response )
            
        
        return response
        
    
    def IsHydrusJob( self ):
        
        with self._lock:
            
            return True
            
        
    
class NetworkJobWatcherPage( NetworkJob ):
    
    def __init__( self, watcher_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._watcher_key = watcher_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_WATCHER_PAGE, self._watcher_key ) )
        
        return network_contexts
        
    
