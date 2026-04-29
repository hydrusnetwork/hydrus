import http.cookiejar
import requests
import traceback
import typing

import requests.exceptions

# cribbed and hydrus-wangled and -simplified from ideas here https://codeberg.org/mikf/gallery-dl/pulls/28/files

curl_cffi_http_versions_to_str_lookup = {}

CURL_CFFI_OK = True
CURL_CFFI_MODULE_NOT_FOUND = False
CURL_CFFI_IMPORT_ERROR = 'curl_cffi seems fine!'

try:
    
    import curl_cffi.requests
    import curl_cffi.requests.exceptions
    
    try:
        
        curl_cffi_http_versions_to_str_lookup = {
            curl_cffi.CurlHttpVersion.V1_0 : 'http/1',
            curl_cffi.CurlHttpVersion.V1_1 : 'http/1.1',
            curl_cffi.CurlHttpVersion.V2_0 : 'http/2',
            curl_cffi.CurlHttpVersion.V2TLS : 'http/2 for https, http/1.1 for http',
            curl_cffi.CurlHttpVersion.V2_PRIOR_KNOWLEDGE : 'http/2 without http/1.1 upgrade',
            curl_cffi.CurlHttpVersion.V3 : 'http/3',
            curl_cffi.CurlHttpVersion.V3ONLY : 'http/3 with no fallback',
        }
        
    except:
        
        print( 'Could not set up curl_cffi http versions--I guess the enums changed?' )
        
    
    class MyCurlCFFISession( curl_cffi.requests.Session ):
        
        def request( self, *args, **kwargs ):
            
            try:
                
                return super().request( *args, **kwargs )
                
            except Exception as e:
                
                # order matters here; most to least specific!
                for ( curl_cffi_type, requests_type ) in [
                    ( curl_cffi.requests.exceptions.ReadTimeout, requests.exceptions.ReadTimeout ),
                    ( curl_cffi.requests.exceptions.ConnectTimeout, requests.exceptions.ConnectTimeout ),
                    ( curl_cffi.requests.exceptions.SSLError, requests.exceptions.SSLError ),
                    ( curl_cffi.requests.exceptions.ConnectionError, requests.exceptions.ConnectionError ),
                    ( curl_cffi.requests.exceptions.Timeout, requests.exceptions.Timeout ),
                    ( curl_cffi.requests.exceptions.ContentDecodingError, requests.exceptions.ContentDecodingError ),
                    ( curl_cffi.requests.exceptions.ChunkedEncodingError, requests.exceptions.ChunkedEncodingError ),
                    ( curl_cffi.requests.exceptions.RequestException, requests.exceptions.RequestException ),
                ]:
                    
                    if isinstance( e, curl_cffi_type ):
                        
                        raise requests_type( e ) from e
                        
                    
                
                raise
                
            
        
    
except Exception as e:
    
    CURL_CFFI_OK = False
    CURL_CFFI_MODULE_NOT_FOUND = isinstance( e, ModuleNotFoundError )
    CURL_CFFI_IMPORT_ERROR = traceback.format_exc()
    

def CreateCurlCFFISession(
    definition: str,
    http_version: "curl_cffi.CurlHttpVersion"
):
    
    curl_cffi_session = MyCurlCFFISession( impersonate = definition, http_version = http_version )
    
    return curl_cffi_session
    

def ConvertRequestsSessionToCurlCFFISession(
    definition: str,
    http_version: "curl_cffi.CurlHttpVersion",
    requests_session: requests.Session
):
    
    curl_cffi_session = CreateCurlCFFISession( definition, http_version )
    
    # we out here
    proxies = typing.cast( object, requests_session.proxies )
    proxies = typing.cast( curl_cffi.requests.ProxySpec, proxies )
    
    curl_cffi_session.proxies = proxies
    curl_cffi_session.verify = requests_session.verify
    
    SetCURLCFFISessionCookiesWithRequestsCookieJar( curl_cffi_session, requests_session.cookies )
    
    return curl_cffi_session
    

def GetRequestsCookiesFromCurlCFFISession( curl_cffi_session: "curl_cffi.requests.Session" ) -> requests.sessions.RequestsCookieJar:
    
    requests_session = requests.Session()
    
    jar = typing.cast( http.cookiejar.CookieJar, curl_cffi_session.cookies.jar )
    
    for cookie in jar:
        
        requests_session.cookies.set_cookie( cookie )
        
    
    return requests_session.cookies
    

def SetCURLCFFISessionCookiesWithRequestsCookieJar( curl_cffi_session: "curl_cffi.requests.Session", cookies: requests.sessions.RequestsCookieJar ):
    
    curl_cffi_session.cookies.clear()
    
    jar = typing.cast( http.cookiejar.CookieJar, curl_cffi_session.cookies.jar )
    
    for cookie in cookies:
        
        jar.set_cookie( cookie )
        
    

def SessionIsCurlCFFI( ambiguous_session ) -> bool:
    
    if not CURL_CFFI_OK:
        
        return False
        
    
    return isinstance( ambiguous_session, curl_cffi.requests.Session )
    
