import datetime
import os

import requests
import tempfile
import threading
import traceback
import time
import urllib
import urllib.parse

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusText
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetworking
from hydrus.core.processes import HydrusThreading

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientTime
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingFunctions

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
        
        print_long_error_text = False
        
        eclass = HydrusExceptions.InsufficientCredentialsException
        
    elif status_code == 404:
        
        print_long_error_text = False
        
        eclass = HydrusExceptions.NotFoundException
        
    elif status_code == 406:
        
        eclass = HydrusExceptions.NotAcceptable
        
    elif status_code == 409:
        
        eclass = HydrusExceptions.ConflictException
        
    elif status_code == 416:
        
        eclass = HydrusExceptions.RangeNotSatisfiableException
        
    elif status_code == 419:
        
        eclass = HydrusExceptions.SessionException
        
    elif status_code == 422:
        
        eclass = HydrusExceptions.UnprocessableEntity
        
    elif status_code == 426:
        
        eclass = HydrusExceptions.NetworkVersionException
        
    elif status_code == 429:
        
        eclass = HydrusExceptions.BandwidthException
        
    elif status_code == 451:
        
        eclass = HydrusExceptions.CensorshipException
        
    elif status_code in ( 509, 529 ):
        
        eclass = HydrusExceptions.BandwidthException
        
        print_long_error_text = False
        
    elif status_code in ( 502, 522 ):
        
        eclass = HydrusExceptions.ShouldReattemptNetworkException
        
        print_long_error_text = False
        
    elif status_code == 503:
        
        if is_hydrus_service:
            
            eclass = HydrusExceptions.ServerBusyException
            
        else:
            
            eclass = HydrusExceptions.ShouldReattemptNetworkException
            
        
        print_long_error_text = False
        
    elif status_code >= 500:
        
        eclass = HydrusExceptions.ServerException
        
    else:
        
        eclass = HydrusExceptions.NetworkException
        
    
    if len( error_text ) > 1024 and print_long_error_text:
        
        large_chunk = error_text[ : 512 * 1024 ]
        
        smaller_chunk = large_chunk[:256]
        
        HydrusData.DebugPrint( large_chunk )
        
        error_text = 'The server\'s error text was too long to display. The first part follows, while a larger chunk has been written to the log.'
        error_text += '\n'
        error_text += smaller_chunk
        
    
    e = eclass( '{}: {}'.format( status_code, error_text ) )
    
    return ( e, error_text )
    
class NetworkJob( object ):
    
    WILLING_TO_WAIT_ON_INVALID_LOGIN = True
    IS_HYDRUS_SERVICE = False
    IS_IPFS_SERVICE = False
    
    def __init__( self, method: str, url: str, body = None, referral_url = None, temp_path = None, file_body_path = None ):
        
        if body is not None and isinstance( body, str ):
            
            body = bytes( body, 'utf-8' )
            
        
        self.engine = None
        
        self._lock = threading.Lock()
        
        self._method = method
        self._url = url
        
        self._additional_bandwidth_urls = []
        
        self._current_connection_attempt_number = 1
        self._current_request_attempt_number = 1
        self._this_is_a_one_shot_request = False
        
        self._domain = ClientNetworkingFunctions.ConvertURLIntoDomain( self._url )
        self._second_level_domain = ClientNetworkingFunctions.ConvertURLIntoSecondLevelDomain( self._url )
        
        self._body = body
        self._referral_url = referral_url
        self._actual_fetched_url = self._url
        self._temp_path = temp_path
        self._file_body_path = file_body_path
        
        self._response_server_header = None
        self._response_last_modified = None
        
        self._files = None
        self._for_login = False
        
        self._additional_headers = {}
        
        self._creation_time = HydrusTime.GetNow()
        
        self._bandwidth_tracker = HydrusNetworking.BandwidthTracker()
        
        self._connection_error_wake_time = 0
        self._serverside_bandwidth_wake_time = 0
        
        self._wake_time_float = 0.0
        
        self._content_type = None
        self._response_mime = None
        
        self._encoding = 'utf-8'
        self._the_network_job_gave_an_encoding = False
        
        self._stream_io = tempfile.SpooledTemporaryFile( max_size = 10 * 1048576, mode = 'w+b' )
        
        self._error_exception: Exception | None = None
        self._error_text = None
        
        self._is_done_event = threading.Event()
        
        self._is_started = False
        self._is_done = False
        self._is_cancelled = False
        
        self._gallery_token_name = None
        self._gallery_token_consumed = False
        self._last_gallery_token_estimate = 0
        self._bandwidth_manual_override = False
        self._bandwidth_manual_override_delayed_timestamp = None
        self._last_bandwidth_time_estimate = 0
        
        self._last_time_ongoing_bandwidth_failed = 0
        
        self._status_text = 'initialising' + HC.UNICODE_ELLIPSIS
        self._num_bytes_read = 0
        self._num_bytes_to_read = None
        self._num_bytes_read_is_accurate = True
        self._num_bytes_read_in_this_response = 0
        self._num_bytes_expected_in_this_range_chunk = None
        self._number_of_concurrent_empty_chunks = 0
        
        self._file_import_options = None
        
        self._network_contexts = self._GenerateNetworkContexts()
        
        ( self._session_network_context, self._login_network_context ) = self._GenerateSpecificNetworkContexts()
        
    
    def __del__( self ):
        
        self._stream_io.close()
        
    
    def _CanReattemptConnection( self ):
        
        if self._this_is_a_one_shot_request:
            
            return False
            
        
        max_connection_attempts_allowed = CG.client_controller.new_options.GetInteger( 'max_connection_attempts_allowed' )
        
        return self._current_connection_attempt_number <= max_connection_attempts_allowed
        
    
    def _CanReattemptRequest( self ):
        
        if self._this_is_a_one_shot_request:
            
            return False
            
        
        if self._method == 'GET':
            
            max_attempts_allowed = CG.client_controller.new_options.GetInteger( 'max_request_attempts_allowed_get' )
            
        else:
            
            max_attempts_allowed = 1
            
        
        return self._current_request_attempt_number <= max_attempts_allowed
        
    
    def _GenerateModifiedDate( self, response: requests.Response ):
        
        if 'Last-Modified' in response.headers:
            
            # Thu, 20 May 2010 07:00:23 GMT
            # these are always in GMT
            last_modified_string = response.headers[ 'Last-Modified' ]
            
            we_did_it = False
            
            if ClientTime.DATEPARSER_OK:
                
                try:
                    
                    last_modified_time = int( ClientTime.ParseDate( last_modified_string ) )
                    
                    if ClientTime.TimestampIsSensible( last_modified_time ):
                        
                        self._response_last_modified = last_modified_time
                        
                        we_did_it = True
                        
                    
                except:
                    
                    pass
                    
                
            
            if not we_did_it:
                
                try:
                    
                    if last_modified_string.endswith( ' GMT' ):
                        
                        last_modified_string = last_modified_string[:-4]
                        
                    
                    dt = datetime.datetime.strptime( last_modified_string, '%a, %d %b %Y %H:%M:%S' )
                    
                    last_modified_time = HydrusTime.DateTimeToTimestamp( dt )
                    
                    if ClientTime.TimestampIsSensible( last_modified_time ):
                        
                        self._response_last_modified = last_modified_time
                        
                        we_did_it = True
                        
                    
                except:
                    
                    pass
                    
                
            
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = [ ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ]
        
        domains = ClientNetworkingFunctions.ConvertDomainIntoAllApplicableDomains( self._domain )
        
        network_contexts.extend( ( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain ) for domain in domains ) )
        
        return network_contexts
        
    
    def _GenerateSpecificNetworkContexts( self ):
        
        # we always store cookies in the larger session (even if the cookie itself refers to a subdomain in the session object)
        # but we can login to a specific subdomain
        
        session_network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, self._second_level_domain )
        login_network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, self._domain )
        
        return ( session_network_context, login_network_context )
        
    
    def _GetTimeouts( self ):
        
        connect_timeout = CG.client_controller.new_options.GetInteger( 'network_timeout' )
        
        read_timeout = connect_timeout * 6
        
        return ( connect_timeout, read_timeout )
        
    
    def _IsCancelled( self ):
        
        if self._is_cancelled:
            
            return True
            
        
        if HG.started_shutdown:
            
            return True
            
        
        return False
        
    
    def _IsDone( self ):
        
        if self._is_done:
            
            return True
            
        
        if HG.started_shutdown or HydrusThreading.IsThreadShuttingDown():
            
            return True
            
        
        return False
        
    
    def _ObeysBandwidth( self ):
        
        if self._bandwidth_manual_override:
            
            return False
            
        
        if self._bandwidth_manual_override_delayed_timestamp is not None and HydrusTime.TimeHasPassed( self._bandwidth_manual_override_delayed_timestamp ):
            
            return False
            
        
        if self._method == 'POST':
            
            return False
            
        
        if self._for_login:
            
            return False
            
        
        return True
        
    
    def _OngoingBandwidthOK( self ):
        
        now = HydrusTime.GetNow()
        
        if now == self._last_time_ongoing_bandwidth_failed: # it won't have changed, so no point spending any cpu checking
            
            return False
            
        else:
            
            result = self.engine.bandwidth_manager.CanContinueDownload( self._network_contexts )
            
            if not result:
                
                self._last_time_ongoing_bandwidth_failed = now
                
            
            return result
            
        
    
    def _ParseFirstResponseHeaders( self, response: requests.Response ):
        
        with self._lock:
            
            if 'Content-Type' in response.headers:
                
                self._content_type = response.headers[ 'Content-Type' ]
                
            
            if self._content_type is not None and self._content_type in HC.mime_enum_lookup:
                
                self._response_mime = HC.mime_enum_lookup[ self._content_type ]
                
            else:
                
                self._response_mime = None
                
            
            if 'Content-Length' in response.headers:
                
                self._num_bytes_to_read = int( response.headers[ 'Content-Length' ] )
                
            else:
                
                self._num_bytes_to_read = None
                
            
            if response.encoding is not None:
                
                self._encoding = response.encoding
                
                # response.encoding will default to ISO-8859-1 or windows-1252 I believe, so tread carefully in trusting it!
                explicit_http_header = self._encoding is not None and 'Content-Type' in response.headers and 'charset' in response.headers[ 'Content-Type' ]
                self._the_network_job_gave_an_encoding = explicit_http_header or self._encoding not in HydrusText.DEFAULT_WEB_ENCODINGS
                
            
            if response.ok: # i.e. we got what we expected, not some error
                
                if self._num_bytes_to_read is not None:
                    
                    if self._file_import_options is not None:
                        
                        is_complete_file_size = True
                        
                        self._file_import_options.CheckNetworkDownload( self._response_mime, self._num_bytes_to_read, is_complete_file_size )
                        
                    
                
            
        
    
    def _ReadResponse( self, response: requests.Response, stream_dest ):
        
        self._num_bytes_read_in_this_response = 0
        self._num_bytes_expected_in_this_range_chunk = None
        
        if 'Content-Range' in response.headers:
            
            content_range = response.headers[ 'Content-Range' ]
            
            # Content-Range: <unit> <range-start>-<range-end>/<size>
            # range and size can be *
            if content_range.startswith( 'bytes ' ):
                
                content_range = content_range[6:]
                
                if '/' in content_range:
                    
                    ( byte_range, size ) = content_range.split( '/', 1 )
                    
                    if byte_range != '*' and '-' in byte_range:
                        
                        ( byte_start, byte_end ) = byte_range.split( '-', 1 )
                        
                        try:
                            
                            byte_start = int( byte_start )
                            
                            if byte_start != self._num_bytes_read:
                                
                                # this server be crazy
                                # I guess in some cases we might be able to fast forward a < byte_start, but we don't have that raw byte access tech yet
                                # and if byte_start > num_bytes_read, then lmao
                                raise HydrusExceptions.NetworkException( 'This server delivered an undesired Range response! We asked for Range "{}" and got Content-Range "{}" back!'.format( response.request.headers[ 'range' ], response.headers[ 'Content-Range' ] ) )
                                
                            
                            try:
                                
                                byte_end = int( byte_end )
                                
                                self._num_bytes_expected_in_this_range_chunk = ( byte_end - byte_start ) + 1
                                
                            except:
                                
                                pass
                                
                            
                        except:
                            
                            pass
                            
                        
                    
                    if size != '*':
                        
                        if self._num_bytes_to_read is None:
                            
                            try:
                                
                                num_bytes = int( size )
                                
                                self._num_bytes_to_read = num_bytes
                                
                            except:
                                
                                pass
                                
                            
                        
                    
                
            
        
        num_bytes_read_before_this_response = self._num_bytes_read
        
        for chunk in response.iter_content( chunk_size = 65536 ):
            
            if self._IsCancelled():
                
                raise HydrusExceptions.CancelledException()
                
            
            stream_dest.write( chunk )
            
            # get the raw bytes read, not the length of the chunk, as there may be transfer-encoding (chunked, gzip etc...)
            total_bytes_read_in_this_response = response.raw.tell()
            
            if total_bytes_read_in_this_response == 0:
                
                # this seems to occur when the response is Transfer-Encoding: chunked (note, no Content-Length)
                # there's no great way to track raw bytes read in this case. the iter_content chunk can be unzipped from that
                # nonetheless, requests does raise ChunkedEncodingError if it stops early, so not a huge deal to miss here, just slightly off bandwidth tracking
                
                self._num_bytes_read_is_accurate = False
                
                chunk_num_bytes = len( chunk )
                
            else:
                
                num_bytes_read_at_last_chunk = self._num_bytes_read
                
                if total_bytes_read_in_this_response >= num_bytes_read_at_last_chunk:
                    
                    chunk_num_bytes = total_bytes_read_in_this_response - num_bytes_read_at_last_chunk
                    
                else:
                    
                    self._num_bytes_read_is_accurate = False
                    
                    chunk_num_bytes = 1
                    
                
            
            self._num_bytes_read += chunk_num_bytes
            self._num_bytes_read_in_this_response += chunk_num_bytes
            
            with self._lock:
                
                if self._num_bytes_read_is_accurate:
                    
                    if self._num_bytes_to_read is not None and self._num_bytes_read > self._num_bytes_to_read:
                        
                        raise HydrusExceptions.NetworkException( 'Too much data: Was expecting {}, but the server continued responding!'.format( HydrusData.ToHumanBytes( self._num_bytes_to_read ) ) )
                        
                    
                    if self._num_bytes_expected_in_this_range_chunk is not None:
                        
                        if self._num_bytes_read_in_this_response > self._num_bytes_expected_in_this_range_chunk:
                            
                            raise HydrusExceptions.NetworkException( 'Too much data: Was expecting {} in this range chunk, but the server continued responding!'.format( HydrusData.ToHumanBytes( self._num_bytes_expected_in_this_range_chunk ) ) )
                            
                        
                    
                
                if self._file_import_options is not None:
                    
                    is_complete_file_size = False
                    
                    self._file_import_options.CheckNetworkDownload( self._response_mime, self._num_bytes_read, is_complete_file_size )
                    
                
            
            self._ReportDataUsed( chunk_num_bytes )
            self._WaitOnOngoingBandwidth()
            
            if HG.started_shutdown:
                
                raise HydrusExceptions.ShutdownException()
                
            
        
        with self._lock:
            
            # stick with GET for now. if there is a complex way to range-chunk a POST, we'll deal with it then, but I don't want to spam file uploads to IQDB by accident etc...
            we_know_there_is_more_to_download = self._method == 'GET' and self._num_bytes_to_read is not None and self._num_bytes_read_is_accurate and self._num_bytes_read < self._num_bytes_to_read
            we_read_some_data = self._num_bytes_read > num_bytes_read_before_this_response
            
            if we_know_there_is_more_to_download:
                
                if we_read_some_data:
                    
                    self._number_of_concurrent_empty_chunks = 0
                    
                    # this range chunk is complete, so this should add up correct
                    if self._num_bytes_read_is_accurate:
                        
                        if self._num_bytes_expected_in_this_range_chunk is not None:
                            
                            if self._num_bytes_read_in_this_response < self._num_bytes_expected_in_this_range_chunk:
                                
                                # ok this situation is actually ok(?)
                                # turns out at least one decent server does this regularly, says 'here's 0-22MB' and gives you 128KB instead
                                
                                HydrusData.Print( 'Not enough data for URL {}: Was expecting {} in this range chunk, but the server only delivered {}!'.format( self._url, HydrusData.ToHumanBytes( self._num_bytes_expected_in_this_range_chunk ), HydrusData.ToHumanBytes( self._num_bytes_read_in_this_response ) ) )
                                
                            
                        
                    
                else:
                    
                    self._number_of_concurrent_empty_chunks += 1
                    
                    if self._number_of_concurrent_empty_chunks > 2:
                        
                        raise HydrusExceptions.NetworkException( 'The server appeared to want to send this URL in ranged chunks, but we got several empty chunks in a row!' )
                        
                    
                
            
        
        if not we_know_there_is_more_to_download:
            
            if self._file_import_options is not None:
                
                is_complete_file_size = True
                
                self._file_import_options.CheckNetworkDownload( self._response_mime, self._num_bytes_read, is_complete_file_size )
                
            
        
        return we_know_there_is_more_to_download
        
    
    def _ReportDataUsed( self, num_bytes ):
        
        self._bandwidth_tracker.ReportDataUsed( num_bytes )
        
        self.engine.bandwidth_manager.ReportDataUsed( self._network_contexts, num_bytes )
        
    
    def _ResetForAnotherAttempt( self ):
        
        self._current_request_attempt_number += 1
        
        self._content_type = None
        self._response_mime = None
        
        self._encoding = 'utf-8'
        
        self._stream_io.close()
        self._stream_io = tempfile.SpooledTemporaryFile( max_size = 10 * 1048576, mode = 'w+b' )
        
        self._num_bytes_read = 0
        self._num_bytes_to_read = None
        self._num_bytes_read_in_this_response = 0
        self._num_bytes_expected_in_this_range_chunk = None
        self._num_bytes_read_is_accurate = True
        self._number_of_concurrent_empty_chunks = 0
        
    
    def _ResetForAnotherConnectionAttempt( self ):
        
        self._ResetForAnotherAttempt()
        
        self._current_connection_attempt_number += 1
        self._current_request_attempt_number = 1
        
    
    def _SendRequestAndGetResponse( self ) -> requests.Response:
        
        with self._lock:
            
            ncs = list( self._network_contexts )
            
        
        headers = self.engine.domain_manager.GetHeaders( ncs )
        
        with self._lock:
            
            method = self._method
            url = self._url
            data = self._body
            files = self._files
            
            if self.IS_HYDRUS_SERVICE or self.IS_IPFS_SERVICE:
                
                headers[ 'User-Agent' ] = 'hydrus client/' + str( HC.NETWORK_VERSION )
                
            
            referral_url = self.engine.domain_manager.GetReferralURL( url, self._referral_url )
            
            url_class = self.engine.domain_manager.GetURLClass( url )
            
            if url_class is not None:
                
                headers.update( url_class.GetHeaderOverrides() )
                
            
            if url_class is None or url_class.GetURLType() in ( HC.URL_TYPE_FILE, HC.URL_TYPE_UNKNOWN ):
                
                headers[ 'Range' ] = 'bytes={}-'.format( self._num_bytes_read )
                
            
            ClientNetworkingFunctions.NetworkReportMode( f'Network Jobs Referral URLs for {url}:\nGiven: {self._referral_url}\nUsed: {referral_url}' )
            
            if referral_url is not None:
                
                try:
                    
                    referral_url.encode( 'latin-1' )
                    
                except UnicodeEncodeError:
                    
                    try:
                        
                        # it prob has some weird unicode characters in it, so let's encode
                        referral_url = ClientNetworkingFunctions.EnsureURLIsEncoded( referral_url )
                        
                    except:
                        
                        # ok this situation is crazy, so let's fall back to what I read in StackExchange an eon ago
                        # quick and dirty way to quote this url when it comes here with full unicode chars. not perfect, but does the job
                        referral_url = urllib.parse.quote( referral_url, "!#$%&'()*+,/:;=?@[]~" )
                        
                    
                    ClientNetworkingFunctions.NetworkReportMode( f'Network Jobs Quoted Referral URL for {url}:\n{referral_url}' )
                    
                
                headers[ 'referer' ] = referral_url
                
            
            for ( key, value ) in self._additional_headers.items():
                
                headers[ key ] = value
                
            
            if self._num_bytes_read == 0:
                
                self._status_text = 'sending request' + HC.UNICODE_ELLIPSIS
                
            
            snc = self._session_network_context
            
        
        session = self.engine.session_manager.GetSession( snc )
        
        ( connect_timeout, read_timeout ) = self._GetTimeouts()
        
        if HG.network_report_mode:
            
            if len( headers ) > 0:
                
                message = f'Request Headers set by the network domain manager: ' + ', '.join( sorted( headers.keys() ) )
                
            else:
                
                message = 'No custom headers set by the network domain manager.'
                
            
            ClientNetworkingFunctions.NetworkReportMode( message )
            
        
        # note we do verify=session.verify here since it is an implicit inheritance and can be overwritten by internal requests ENV gubbins unless explicitly stated
        
        if self._file_body_path is not None:
            
            with open( self._file_body_path, 'rb' ) as f:
                
                response = session.request( method, url, data = f, headers = headers, stream = True, timeout = ( connect_timeout, read_timeout ), verify = session.verify )
                
            
        else:
            
            response = session.request( method, url, data = data, files = files, headers = headers, stream = True, timeout = ( connect_timeout, read_timeout ), verify = session.verify )
            
        
        if HG.network_report_mode:
            
            message = 'Request Headers:\n'
            message += '\n'.join( [ f'{key}: {value}' for ( key, value ) in sorted( response.request.headers.items() ) ] )
            message += '\n\n'
            message += 'Response Headers:\n'
            message += '\n'.join( [ f'{key}: {value}' for ( key, value ) in sorted( response.headers.items() ) ] )
            
            ClientNetworkingFunctions.NetworkReportMode( message )
            
        
        with self._lock:
            
            if self._file_body_path is not None:
                
                self._ReportDataUsed( os.path.getsize( self._file_body_path ) )
                
            elif self._body is not None:
                
                self._ReportDataUsed( len( self._body ) )
                
            
        
        return response
        
    
    def _SetCancelled( self ):
        
        self._is_cancelled = True
        
        self._SetDone()
        
    
    def _SetError( self, e, error ):
        
        self._error_exception = e
        self._error_text = error
        
        if HG.network_report_mode:
            
            if HG.network_report_mode_silent:
                
                HydrusData.Print( 'Network error should follow:' )
                HydrusData.PrintException( e )
                HydrusData.Print( error )
                
            else:
                
                HydrusData.ShowText( 'Network error should follow:' )
                HydrusData.ShowException( e )
                HydrusData.ShowText( error )
                
            
        
        self._SetDone()
        
    
    def _SetDone( self ):
        
        self._is_done = True
        
        self._is_done_event.set()
        
    
    def _Sleep( self, seconds_float ):
        
        self._wake_time_float = HydrusTime.GetNowFloat() + seconds_float
        
    
    def _WaitOnConnectionError( self, status_text: str ):
        
        connection_error_wait_time = CG.client_controller.new_options.GetInteger( 'connection_error_wait_time' )
        
        self._connection_error_wake_time = HydrusTime.GetNow() + ( ( self._current_connection_attempt_number - 1 ) * connection_error_wait_time )
        
        while not HydrusTime.TimeHasPassed( self._connection_error_wake_time ) and not self._IsCancelled():
            
            with self._lock:
                
                self._status_text = '{} - retrying {}'.format( status_text, HydrusTime.TimestampToPrettyTimeDelta( self._connection_error_wake_time ) )
                
            
            time.sleep( 1 )
            
        
        self._WaitOnNetworkTrafficPaused( status_text )
        
    
    def _WaitOnNetworkTrafficPaused( self, status_text: str ):
        
        while CG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' ) and not self._IsCancelled():
            
            with self._lock:
                
                self._status_text = '{} - now waiting because all network traffic is paused'.format( status_text )
                
            
            time.sleep( 1 )
            
        
    
    def _WaitOnOngoingBandwidth( self ):
        
        while not self._OngoingBandwidthOK() and not self._IsCancelled():
            
            time.sleep( 0.1 )
            
        
    
    def _WaitOnServersideBandwidth( self, status_text: str, num_seconds_to_wait = None ):
        
        # 429/509/529 response from server. basically means 'I'm under big load mate'
        # a future version of this could def talk to domain manager and add a temp delay so other network jobs can be informed
        
        if num_seconds_to_wait is None:
            
            serverside_bandwidth_wait_time = CG.client_controller.new_options.GetInteger( 'serverside_bandwidth_wait_time' )
            
            backoff_factor = 1.25
            problem_rating = ( self._current_connection_attempt_number + self._current_request_attempt_number ) - 1
            
            problem_coefficient = backoff_factor ** problem_rating
            
            num_seconds_to_wait = problem_coefficient * serverside_bandwidth_wait_time
            
        
        self._serverside_bandwidth_wake_time = HydrusTime.GetNow() + num_seconds_to_wait
        
        while not HydrusTime.TimeHasPassed( self._serverside_bandwidth_wake_time ) and not self._IsCancelled():
            
            with self._lock:
                
                self._status_text = '{} - retrying {}'.format( status_text, HydrusTime.TimestampToPrettyTimeDelta( self._serverside_bandwidth_wake_time ) )
                
            
            time.sleep( 1 )
            
        
        self._WaitOnNetworkTrafficPaused( status_text )
        
    
    def AddAdditionalHeader( self, key, value ):
        
        with self._lock:
            
            self._additional_headers[ key ] = value
            
        
    
    def AddBandwidthURL( self, url: str ):
        
        with self._lock:
            
            domain = ClientNetworkingFunctions.ConvertURLIntoDomain( url )
            
            domains = ClientNetworkingFunctions.ConvertDomainIntoAllApplicableDomains( domain )
            
            for domain in domains:
                
                network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain )
                
                if network_context not in self._network_contexts:
                    
                    self._network_contexts.append( network_context )
                    
                
            
        
    
    def BandwidthOK( self ):
        
        with self._lock:
            
            if self._ObeysBandwidth():
                
                return self.engine.bandwidth_manager.CanDoWork( self._network_contexts )
                
            else:
                
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
                
            
        
    
    def CurrentlyNeedsLogin( self ):
        
        with self._lock:
            
            if self._for_login:
                
                return False
                
            else:
                
                return self.engine.login_manager.CurrentlyNeedsLogin( self._login_network_context )
                
            
        
    
    def CurrentlyWaitingOnConnectionError( self ):
        
        with self._lock:
            
            return not HydrusTime.TimeHasPassed( self._connection_error_wake_time )
            
        
    
    def CurrentlyWaitingOnServersideBandwidth( self ):
        
        with self._lock:
            
            return not HydrusTime.TimeHasPassed( self._serverside_bandwidth_wake_time )
            
        
    
    def DomainOK( self ):
        
        with self._lock:
            
            if self._this_is_a_one_shot_request:
                
                return True
                
            
            domain_ok = self.engine.domain_manager.DomainOK( self._url )
            
            if not domain_ok:
                
                self._status_text = 'This domain has had several serious errors recently. Waiting a bit.'
                
                self._Sleep( 10 )
                
            
            return domain_ok
            
        
    
    def GenerateLoginProcess( self ):
        
        with self._lock:
            
            if self._for_login:
                
                raise Exception( 'Login jobs should not be asked to generate login processes!' )
                
            else:
                
                return self.engine.login_manager.GenerateLoginProcess( self._login_network_context )
                
            
        
    
    def GenerateValidationPopupProcess( self ):
        
        with self._lock:
            
            return self.engine.domain_manager.GenerateValidationPopupProcess( self._network_contexts )
            
        
    
    def GetActualFetchedURL( self ):
        
        with self._lock:
            
            return self._actual_fetched_url
            
        
    
    def GetContentBytes( self ):
        
        with self._lock:
            
            self._stream_io.seek( 0 )
            
            return self._stream_io.read()
            
        
    
    def GetContentText( self ):
        
        data = self.GetContentBytes()
        
        ( text, self._encoding ) = HydrusText.NonFailingUnicodeDecode( data, self._encoding, trust_the_encoding = self._the_network_job_gave_an_encoding )
        
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
            
        
    
    def GetLastModifiedTime( self ) -> int | None:
        
        with self._lock:
            
            return self._response_last_modified
            
        
    
    def GetLoginNetworkContext( self ):
        
        with self._lock:
            
            return self._login_network_context
            
        
    
    def GetNetworkContexts( self ) -> list[ ClientNetworkingContexts.NetworkContext ]:
        
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
            
            return not HydrusTime.TimeHasPassedFloat( self._wake_time_float )
            
        
    
    def IsCancelled( self ):
        
        with self._lock:
            
            return self._IsCancelled()
            
        
    
    def IsCloudFlareCache( self ):
        
        with self._lock:
            
            return self._response_server_header is not None and self._response_server_header == 'cloudflare'
            
        
    
    def IsDone( self ):
        
        with self._lock:
            
            return self._IsDone()
            
        
    
    def IsHydrusJob( self ):
        
        with self._lock:
            
            return False
            
        
    
    def IsValid( self ):
        
        with self._lock:
            
            return self.engine.domain_manager.IsValid( self._network_contexts )
            
        
    
    def NoEngineYet( self ):
        
        return self.engine is None
        
    
    def ObeysBandwidth( self ):
        
        return self._ObeysBandwidth()
        
    
    def OnlyTryConnectionOnce( self ):
        
        self._this_is_a_one_shot_request = True
        
    
    def OverrideBandwidth( self, delay = None ):
        
        with self._lock:
            
            if delay is None:
                
                self._bandwidth_manual_override = True
                
                self._wake_time_float = 0.0
                
            else:
                
                self._bandwidth_manual_override_delayed_timestamp = HydrusTime.GetNow() + delay
                
                self._wake_time_float = min( self._wake_time_float, self._bandwidth_manual_override_delayed_timestamp + 1.0 )
                
            
        
    
    def OverrideConnectionErrorWait( self ):
        
        with self._lock:
            
            self._connection_error_wake_time = 0
            
        
    
    def OverrideServersideBandwidthWait( self ):
        
        with self._lock:
            
            self._serverside_bandwidth_wake_time = 0
            
        
    
    def OverrideToken( self ):
        
        with self._lock:
            
            self._gallery_token_consumed = True
            
            self._wake_time_float = 0.0
            
        
    
    def ScrubDomainErrors( self ):
        
        with self._lock:
            
            self.engine.domain_manager.ScrubDomainErrors( self._url )
            
            self._wake_time_float = 0.0
            
        
    
    def SetError( self, e: Exception, error: str ):
        
        with self._lock:
            
            self._SetError( e, error )
            
        
    
    def SetFiles( self, files ):
        
        with self._lock:
            
            self._files = files
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def SetForLogin( self, for_login: bool ):
        
        with self._lock:
            
            self._for_login = for_login
            
        
    
    def SetGalleryToken( self, token_name: str ):
        
        with self._lock:
            
            self._gallery_token_name = token_name
            
        
    
    def SetStatus( self, text: str ):
        
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
                
                if self._IsCancelled():
                    
                    return
                    
                
                response = None
                
                try:
                    
                    response = self._SendRequestAndGetResponse()
                    
                    # I think tbh I would rather tell requests not to do 3XX, which is possible with allow_redirects = False on request, and then just raise various 3XX exceptions with url info, so I can requeue easier and keep a record
                    # figuring out correct new url seems a laugh, requests has slight helpers, but lots of exceptions
                    # SessionRedirectMixin here https://requests.readthedocs.io/en/latest/_modules/requests/sessions/
                    # but this will do as a patch for now
                    self._actual_fetched_url = response.url
                    
                    if HG.network_report_mode and self._actual_fetched_url != self._url:
                        
                        message = f'Network Jobs Redirect: {self._url} -> {self._actual_fetched_url}'
                        
                        ClientNetworkingFunctions.NetworkReportMode( message )
                        
                    
                    self._ParseFirstResponseHeaders( response )
                    
                    if response.ok:
                        
                        with self._lock:
                            
                            self._status_text = 'downloading' + HC.UNICODE_ELLIPSIS
                            
                        
                        if self._temp_path is None:
                            
                            stream_dest = self._stream_io
                            
                        else:
                            
                            stream_dest = open( self._temp_path, 'wb' )
                            
                        
                        try:
                            
                            more_to_download = True
                            
                            while more_to_download:
                                
                                more_to_download = self._ReadResponse( response, stream_dest )
                                
                                if more_to_download:
                                    
                                    with self._lock:
                                        
                                        self._status_text = 'downloading next part' + HC.UNICODE_ELLIPSIS
                                        
                                    
                                    # this will magically have new Range header
                                    response = self._SendRequestAndGetResponse()
                                    
                                    if not response.ok:
                                        
                                        raise HydrusExceptions.NetworkException( 'Ranged response failed {}'.format( response.status_code ) )
                                        
                                    
                                
                            
                        finally:
                            
                            if self._temp_path is not None:
                                
                                stream_dest.close()
                                
                            
                        
                        with self._lock:
                            
                            # we are complete here and worked ok
                            
                            self._GenerateModifiedDate( response )
                            
                            if 'Server' in response.headers:
                                
                                self._response_server_header = response.headers[ 'Server' ]
                                
                            
                            self._status_text = 'done!'
                            
                        
                    else:
                        
                        with self._lock:
                            
                            self._status_text = str( response.status_code ) + ' - ' + str( response.reason )
                            
                        
                        stream_dest = self._stream_io
                        
                        # don't care about 'more_to_download' here. lmao if some server ever tried to pull it off anyway
                        self._ReadResponse( response, stream_dest )
                        
                        data = self.GetContentBytes()
                        
                        with self._lock:
                            
                            ( e, error_text ) = ConvertStatusCodeAndDataIntoExceptionInfo( response.status_code, data, self.IS_HYDRUS_SERVICE )
                            
                            if isinstance( e, ( HydrusExceptions.BandwidthException, HydrusExceptions.ShouldReattemptNetworkException ) ):
                                
                                raise e
                                
                            
                            self._SetError( e, error_text )
                            
                        
                    
                    request_completed = True
                    
                except HydrusExceptions.CancelledException:
                    
                    with self._lock:
                        
                        self._status_text = 'Cancelled!'
                        
                    
                    return
                    
                except HydrusExceptions.BandwidthException as e:
                    
                    num_seconds_to_wait = None
                    
                    if response is not None:
                        
                        if 'Retry-After' in response.headers:
                            
                            retry_after = response.headers[ 'Retry-After' ]
                            
                            try:
                                
                                num_seconds_to_wait = int( retry_after )
                                
                            except:
                                
                                try:
                                    
                                    timestamp = int( ClientTime.ParseDate( retry_after ) )
                                    
                                    num_seconds_to_wait = min( max( 60, timestamp - HydrusTime.GetNow() ), 86400 )
                                    
                                except:
                                    
                                    HydrusData.Print( f'Was given an unparsable Retry-After of {retry_after}!' )
                                    
                                
                            
                        
                    
                    self._ResetForAnotherAttempt()
                    
                    if self._CanReattemptRequest():
                        
                        self.engine.domain_manager.ReportNetworkInfrastructureError( self._url )
                        
                    else:
                        
                        raise HydrusExceptions.BandwidthException( 'Server reported very limited bandwidth: ' + str( e ) )
                        
                    
                    self._WaitOnServersideBandwidth( 'server reported limited bandwidth', num_seconds_to_wait = num_seconds_to_wait )
                    
                except HydrusExceptions.ShouldReattemptNetworkException as e:
                    
                    self._ResetForAnotherAttempt()
                    
                    if not self._CanReattemptRequest():
                        
                        raise HydrusExceptions.NetworkInfrastructureException( 'Ran out of reattempts on this error: ' + str( e ) )
                        
                    
                    self._WaitOnConnectionError( str( e ) )
                    
                except requests.exceptions.ChunkedEncodingError:
                    
                    self._ResetForAnotherAttempt()
                    
                    if not self._CanReattemptRequest():
                        
                        raise HydrusExceptions.StreamTimeoutException( 'Unable to complete request--it broke mid-way!' )
                        
                    
                    self._WaitOnConnectionError( 'connection broke mid-request' )
                    
                except ( requests.exceptions.SSLError, requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout ) as e:
                    
                    # note a requests SSLError is a ConnectionError, so be careful if you extract this again
                    
                    if isinstance( e, requests.exceptions.SSLError ):
                        
                        if 'SSLCertVerificationError' in str( e ):
                            
                            fail_text = f'Problem with SSL Verification. (This may be due to a bad certificate on the site or hydrus\'s "requests" library not having up to date root certs or SSL, but ISP level content blockers can also cause it.): {e}\n\n'
                            delay_text = 'SSL Cert Verification failed'
                            
                        else:
                            
                            fail_text = 'Problem with SSL: {}'.format( repr( e ) )
                            delay_text = 'SSL connection failed'
                            
                        
                    else:
                        
                        fail_text = 'Could not connect!'
                        delay_text = 'connection failed'
                        
                    
                    self._ResetForAnotherConnectionAttempt()
                    
                    if self._CanReattemptConnection():
                        
                        self.engine.domain_manager.ReportNetworkInfrastructureError( self._url )
                        
                    else:
                        
                        raise HydrusExceptions.ConnectionException( fail_text )
                        
                    
                    self._WaitOnConnectionError( delay_text )
                    
                except requests.exceptions.ReadTimeout:
                    
                    self._ResetForAnotherAttempt()
                    
                    if not self._CanReattemptRequest():
                        
                        raise HydrusExceptions.StreamTimeoutException( 'Connection successful, but reading response timed out!' )
                        
                    
                    self._WaitOnConnectionError( 'read timed out' )
                    
                except Exception as e:
                    
                    if '\'Retry\' has no attribute' in str( e ):
                        
                        # this is that weird requests 2.25.x(?) urllib3 maybe thread safety error
                        # we'll just try and pause a bit I guess!
                        
                        self._ResetForAnotherConnectionAttempt()
                        
                        if self._CanReattemptConnection():
                            
                            self.engine.domain_manager.ReportNetworkInfrastructureError( self._url )
                            
                        else:
                            
                            raise HydrusExceptions.ConnectionException( 'Could not connect!' )
                            
                        
                        self._WaitOnConnectionError( 'connection failed, and could not recover neatly' )
                        
                    else:
                        
                        raise
                        
                    
                finally:
                    
                    with self._lock:
                        
                        snc = self._session_network_context
                        
                    
                    self.engine.session_manager.SetSessionDirty( snc )
                    
                    if response is not None:
                        
                        # if full data was not read, the response will hang around in connection pool longer than we want
                        # so just an explicit close here
                        response.close()
                        
                    
                
            
        except Exception as e:
            
            with self._lock:
                
                trace = traceback.format_exc()
                
                if not isinstance( e, ( HydrusExceptions.NetworkInfrastructureException, HydrusExceptions.StreamTimeoutException, HydrusExceptions.FileImportRulesException ) ):
                    
                    HydrusData.Print( trace )
                    
                
                if isinstance( e, HydrusExceptions.NetworkInfrastructureException ):
                    
                    self.engine.domain_manager.ReportNetworkInfrastructureError( self._url )
                    
                
                self._status_text = 'Error: ' + str( e )
                
                self._SetError( e, trace )
                
            
        finally:
            
            with self._lock:
                
                self._SetDone()
                
            
        
    
    def TokensOK( self ) -> bool:
        
        with self._lock:
            
            need_token = self._gallery_token_name is not None and not self._gallery_token_consumed
            
            sld = self._second_level_domain
            gtn = self._gallery_token_name
            
        
        if need_token:
            
            ( consumed, next_timestamp ) = self.engine.bandwidth_manager.TryToConsumeAGalleryToken( sld, gtn )
            
            with self._lock:
                
                if consumed:
                    
                    self._status_text = 'gallery token ok - starting soon'
                    
                    self._gallery_token_consumed = True
                    
                else:
                    
                    if HydrusTime.TimeHasPassed( self._last_gallery_token_estimate ) and not HydrusTime.TimeHasPassed( self._last_gallery_token_estimate + 3 ):
                        
                        self._status_text = 'a different {} got the chance to work'.format( self._gallery_token_name )
                        
                    else:
                        
                        self._status_text = 'waiting to start: {}'.format( HydrusTime.TimestampToPrettyTimeDelta( next_timestamp, just_now_threshold = 2, just_now_string = 'checking', no_prefix = True ) )
                        
                        self._last_gallery_token_estimate = next_timestamp
                        
                    
                    self._Sleep( 0.8 )
                    
                    return False
                    
                
            
        
        return True
        
    
    def TryToStartBandwidth( self ):
        
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
                        
                        override_waiting_duration = self._bandwidth_manual_override_delayed_timestamp - HydrusTime.GetNow()
                        
                        override_coming_first = override_waiting_duration < bandwidth_waiting_duration
                        
                    
                    just_now_threshold = 2
                    
                    if override_coming_first:
                        
                        waiting_duration = override_waiting_duration
                        
                        waiting_str = 'overriding bandwidth ' + HydrusTime.TimestampToPrettyTimeDelta( self._bandwidth_manual_override_delayed_timestamp, just_now_string = 'imminently', just_now_threshold = just_now_threshold )
                        
                    else:
                        
                        waiting_duration = bandwidth_waiting_duration
                        
                        bandwidth_time_estimate = HydrusTime.GetNow() + waiting_duration
                        
                        if HydrusTime.TimeHasPassed( self._last_bandwidth_time_estimate ) and not HydrusTime.TimeHasPassed( self._last_bandwidth_time_estimate + 3 ):
                            
                            waiting_str = 'a different network job got the bandwidth'
                            
                        else:
                            
                            waiting_str = 'bandwidth free ' + HydrusTime.TimestampToPrettyTimeDelta( bandwidth_time_estimate, just_now_string = 'imminently', just_now_threshold = just_now_threshold )
                            
                            self._last_bandwidth_time_estimate = bandwidth_time_estimate
                            
                        
                    
                    waiting_str += f'{HC.UNICODE_ELLIPSIS} ({bandwidth_network_context.ToHumanString()})'
                    
                    self._status_text = waiting_str
                    
                    if waiting_duration > 1200:
                        
                        self._Sleep( 30 )
                        
                    elif waiting_duration > 120:
                        
                        self._Sleep( 10 )
                        
                    elif waiting_duration > 10:
                        
                        self._Sleep( 0.8 )
                        
                    
                
                return result
                
            else:
                
                self._bandwidth_tracker.ReportRequestUsed()
                
                self.engine.bandwidth_manager.ReportRequestUsed( self._network_contexts )
                
                return True
                
            
        
    
    def WaitUntilDone( self ):
        
        while True:
            
            if self.IsDone():
                
                break
                
            
            self._is_done_event.wait( 5 )
            
        
        with self._lock:
            
            if HG.started_shutdown or HydrusThreading.IsThreadShuttingDown():
                
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
                
            
        
    
    def WillingToWaitOnInvalidLogin( self ) -> bool:
        
        return self.WILLING_TO_WAIT_ON_INVALID_LOGIN
        
    
    def WriteContentBytesToPath( self, dest_path: str ):
        
        with self._lock:
            
            with open( dest_path, 'wb' ) as f_write:
                
                self._stream_io.seek( 0 )
                
                for block in HydrusPaths.ReadFileLikeAsBlocks( self._stream_io ):
                    
                    f_write.write( block )
                    
                
            
        
    
    

class NetworkJobDownloader( NetworkJob ):
    
    def __init__( self, downloader_page_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._downloader_page_key = downloader_page_key
        
        super().__init__( method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOWNLOADER_PAGE, self._downloader_page_key ) )
        
        return network_contexts
        
    
class NetworkJobSubscription( NetworkJob ):
    
    WILLING_TO_WAIT_ON_INVALID_LOGIN = False
    
    def __init__( self, subscription_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._subscription_key = subscription_key
        
        super().__init__( method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION, self._subscription_key ) )
        
        return network_contexts
        
    
def CheckHydrusVersion( service_type, response ):
    
    service_string = HC.service_string_lookup[ service_type ]
    
    headers = response.headers
    
    if 'server' in headers and service_string in headers[ 'server' ]:
        
        server_header = headers[ 'server' ]
        
    elif 'hydrus-server' in headers and service_string in headers[ 'hydrus-server' ]:
        
        server_header = headers[ 'hydrus-server' ]
        
    else:
        
        raise HydrusExceptions.WrongServiceTypeException( 'Target was not a ' + service_string + '!' )
        
    
    # might be "hydrus tag repository/17" or "hydrus tag repository/17 (498)" kind of thing
    
    ( service_string_gumpf, network_version ) = server_header.split( '/', 1 )
    
    if ' ' in network_version:
    
        ( network_version, software_version_gumpf ) = network_version.split( ' ', 1 )
        
    
    network_version = int( network_version )
    
    if network_version != HC.NETWORK_VERSION:
        
        if network_version > HC.NETWORK_VERSION:
            
            message = 'Your client is out of date; please download the latest release.'
            
        else:
            
            message = 'The server is out of date; please ask its admin to update to the latest release.'
            
        
        raise HydrusExceptions.NetworkVersionException( 'Network version mismatch! The server\'s network version was ' + str( network_version ) + ', whereas your client\'s is ' + str( HC.NETWORK_VERSION ) + '! ' + message )
        
    
class NetworkJobHydrus( NetworkJob ):
    
    WILLING_TO_WAIT_ON_INVALID_LOGIN = False
    IS_HYDRUS_SERVICE = True
    
    def __init__( self, service_key, method, url, body = None, referral_url = None, temp_path = None, file_body_path = None ):
        
        self._service_key = service_key
        
        super().__init__( method, url, body = body, referral_url = referral_url, temp_path = temp_path, file_body_path = file_body_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = [
            ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT,
            ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, self._service_key )
        ]
        
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
        
    
    def _SendRequestAndGetResponse( self ) -> requests.Response:
        
        try:
            
            service = self.engine.controller.services_manager.GetService( self._service_key )
            
        except HydrusExceptions.DataMissing:
            
            raise HydrusExceptions.CancelledException( 'Service no longer exists!' )
            
        
        service_type = service.GetServiceType()
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            account = service.GetAccount()
            
            account.ReportRequestUsed()
            
        
        response = NetworkJob._SendRequestAndGetResponse( self )
        
        if response.ok and service_type in HC.RESTRICTED_SERVICES:
            
            CheckHydrusVersion( service_type, response )
            
        
        return response
        
    
    def IsHydrusJob( self ):
        
        with self._lock:
            
            return True
            
        
    

class NetworkJobIPFS( NetworkJob ):
    
    IS_IPFS_SERVICE = True
    
    def __init__( self, url, body = None, referral_url = None, temp_path = None ):
        
        method = 'POST'
        
        super().__init__( method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
        self.OnlyTryConnectionOnce()
        self.OverrideBandwidth()
        
    
    def _GetTimeouts( self ):
        
        ( connect_timeout, read_timeout ) = NetworkJob._GetTimeouts( self )
        
        read_timeout = max( 7200, read_timeout )
        
        return ( connect_timeout, read_timeout )
        
    
class NetworkJobWatcherPage( NetworkJob ):
    
    def __init__( self, watcher_key, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._watcher_key = watcher_key
        
        super().__init__( method, url, body = body, referral_url = referral_url, temp_path = temp_path )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_WATCHER_PAGE, self._watcher_key ) )
        
        return network_contexts
        
    
