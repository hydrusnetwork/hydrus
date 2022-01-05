import http.cookiejar
import re
import unicodedata
import urllib.parse

from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusExceptions

def AddCookieToSession( session, name, value, domain, path, expires, secure = False, rest = None ):
    
    version = 0
    port = None
    port_specified = False
    domain_specified = True
    domain_initial_dot = domain.startswith( '.' )
    path_specified = True
    discard = False
    comment = None
    comment_url = None
    
    if rest is None:
        
        rest = {}
        
    
    cookie = http.cookiejar.Cookie( version, name, value, port, port_specified, domain, domain_specified, domain_initial_dot, path, path_specified, secure, expires, discard, comment, comment_url, rest )
    
    session.cookies.set_cookie( cookie )
    
def ConvertDomainIntoAllApplicableDomains( domain, discard_www = True ):
    
    # is an ip address or localhost, possibly with a port
    if '.' not in domain or re.search( r'^[\d\.:]+$', domain ) is not None:
        
        return [ domain ]
        
    
    domains = []
    
    if discard_www:
        
        domain = RemoveWWWFromDomain( domain )
        
    
    while domain.count( '.' ) > 0:
        
        domains.append( domain )
        
        domain = ConvertDomainIntoNextLevelDomain( domain )
        
    
    return domains
    
def ConvertDomainIntoNextLevelDomain( domain ):
    
    return '.'.join( domain.split( '.' )[1:] ) # i.e. strip off the leftmost subdomain maps.google.com -> google.com
    
def ConvertDomainIntoSecondLevelDomain( domain ):
    
    domains = ConvertDomainIntoAllApplicableDomains( domain )
    
    if len( domains ) == 0:
        
        raise HydrusExceptions.URLClassException( 'That url or domain did not seem to be valid!' )
        
    
    return domains[-1]
    
def ConvertHTTPSToHTTP( url ):
    
    if url.startswith( 'http://' ):
        
        return url
        
    elif url.startswith( 'https://' ):
        
        http_url = 'http://' + url[8:]
        
        return http_url
        
    else:
        
        raise Exception( 'Given a url that did not have a scheme!' )
        
    
def ConvertHTTPToHTTPS( url ):
    
    if url.startswith( 'https://' ):
        
        return url
        
    elif url.startswith( 'http://' ):
        
        https_url = 'https://' + url[7:]
        
        return https_url
        
    else:
        
        raise Exception( 'Given a url that did not have a scheme!' )
        
    
def ConvertQueryDictToText( query_dict, single_value_parameters, param_order = None ):
    
    # we now do everything with requests, which does all the unicode -> %20 business naturally, phew
    # we still want to call str explicitly to coerce integers and so on that'll slip in here and there
    
    if param_order is None:
        
        param_order = sorted( query_dict.keys() )
        
        single_value_parameters = list( single_value_parameters )
        single_value_parameters.sort()
        
        for i in range( len( single_value_parameters ) ):
            
            param_order.append( None )
            
        
    
    params = []
    
    single_value_parameter_index = 0
    
    for key in param_order:
        
        if key is None:
            
            try:
                
                params.append( single_value_parameters[ single_value_parameter_index ] )
                
            except IndexError:
                
                continue
                
            
            single_value_parameter_index += 1
            
        else:
            
            if key in query_dict:
                
                params.append( '{}={}'.format( key, query_dict[ key ] ) )
                
            
        
    
    query_text = '&'.join( params )
    
    return query_text
    
def ConvertQueryTextToDict( query_text ):
    
    # we generally do not want quote characters, %20 stuff, in our urls. we would prefer properly formatted unicode
    
    # so, let's replace all keys and values with unquoted versions
    # -but-
    # we only replace if it is a completely reversable operation!
    # odd situations like '6+girls+skirt', which comes here encoded as '6%2Bgirls+skirt', shouldn't turn into '6+girls+skirt'
    # so if there are a mix of encoded and non-encoded, we won't touch it here m8
    
    # except these chars, which screw with GET arg syntax when unquoted
    bad_chars = [ '&', '=', '/', '?', '#', ';', '+' ]
    
    param_order = []
    
    query_dict = {}
    single_value_parameters = []
    
    pairs = query_text.split( '&' )
    
    for pair in pairs:
        
        result = pair.split( '=', 1 )
        
        # for the moment, ignore tracker bugs and so on that have only key and no value
        
        if len( result ) == 1:
            
            ( value, ) = result
            
            if value == '':
                
                continue
                
            
            try:
                
                unquoted_value = urllib.parse.unquote( value )
                
                if True not in ( bad_char in unquoted_value for bad_char in bad_chars ):
                    
                    requoted_value = urllib.parse.quote( unquoted_value )
                    
                    if requoted_value == value:
                        
                        value = unquoted_value
                        
                    
                
            except:
                
                pass
                
            
            single_value_parameters.append( value )
            param_order.append( None )
            
        elif len( result ) == 2:
            
            ( key, value ) = result
            
            try:
                
                unquoted_key = urllib.parse.unquote( key )
                
                if True not in ( bad_char in unquoted_key for bad_char in bad_chars ):
                    
                    requoted_key = urllib.parse.quote( unquoted_key )
                    
                    if requoted_key == key:
                        
                        key = unquoted_key
                        
                    
                
            except:
                
                pass
                
            
            try:
                
                unquoted_value = urllib.parse.unquote( value )
                
                if True not in ( bad_char in unquoted_value for bad_char in bad_chars ):
                    
                    requoted_value = urllib.parse.quote( unquoted_value )
                    
                    if requoted_value == value:
                        
                        value = unquoted_value
                        
                    
                
            except:
                
                pass
                
            
            param_order.append( key )
            
            query_dict[ key ] = value
            
        
    
    return ( query_dict, single_value_parameters, param_order )
    
def ConvertURLIntoDomain( url ):
    
    parser_result = ParseURL( url )
    
    if parser_result.scheme == '':
        
        raise HydrusExceptions.URLClassException( 'URL "' + url + '" was not recognised--did you forget the http:// or https://?' )
        
    
    if parser_result.netloc == '':
        
        raise HydrusExceptions.URLClassException( 'URL "' + url + '" was not recognised--is it missing a domain?' )
        
    
    domain = parser_result.netloc
    
    return domain
    
def ConvertURLIntoSecondLevelDomain( url ):
    
    domain = ConvertURLIntoDomain( url )
    
    return ConvertDomainIntoSecondLevelDomain( domain )
    
def CookieDomainMatches( cookie, search_domain ):
    
    cookie_domain = cookie.domain
    
    # blah.com is viewable by blah.com
    matches_exactly = cookie_domain == search_domain
    
    # .blah.com is viewable by blah.com
    matches_dot = cookie_domain == '.' + search_domain
    
    # .blah.com applies to subdomain.blah.com, blah.com does not
    valid_subdomain = cookie_domain.startswith( '.' ) and search_domain.endswith( cookie_domain )
    
    return matches_exactly or matches_dot or valid_subdomain
    
def DomainEqualsAnotherForgivingWWW( test_domain, wwwable_domain ):
    
    # domain is either the same or starts with www. or www2. or something
    rule = r'^(www[^\.]*\.)?' + re.escape( wwwable_domain ) + '$'
    
    return re.search( rule, test_domain ) is not None
    
def GetCookie( cookies, search_domain, cookie_name_string_match ):
    
    for cookie in cookies:
        
        if CookieDomainMatches( cookie, search_domain ) and cookie_name_string_match.Matches( cookie.name ):
            
            return cookie
            
        
    
    raise HydrusExceptions.DataMissing( 'Cookie "' + cookie_name_string_match.ToString() + '" not found for domain ' + search_domain + '!' )
    
def GetSearchURLs( url ):
    
    search_urls = set()
    
    search_urls.add( url )
    
    try:
        
        normalised_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
        
        search_urls.add( normalised_url )
        
    except HydrusExceptions.URLClassException:
        
        pass
        
    
    for url in list( search_urls ):
        
        if url.startswith( 'http://' ):
            
            search_urls.add( ConvertHTTPToHTTPS( url ) )
            
        elif url.startswith( 'https://' ):
            
            search_urls.add( ConvertHTTPSToHTTP( url ) )
            
        
    
    for url in list( search_urls ):
        
        p = ParseURL( url )
        
        scheme = p.scheme
        netloc = p.netloc
        path = p.path
        params = ''
        query = p.query
        fragment = p.fragment
        
        if netloc.startswith( 'www' ):
            
            try:
                
                netloc = ConvertDomainIntoSecondLevelDomain( netloc )
                
            except HydrusExceptions.URLClassException:
                
                continue
                
            
        else:
            
            netloc = 'www.' + netloc
            
        
        r = urllib.parse.ParseResult( scheme, netloc, path, params, query, fragment )
        
        search_urls.add( r.geturl() )
        
    
    for url in list( search_urls ):
        
        if url.endswith( '/' ):
            
            search_urls.add( url[:-1] )
            
        else:
            
            search_urls.add( url + '/' )
            
        
    
    return search_urls
    
def NormaliseAndFilterAssociableURLs( urls ):
    
    normalised_urls = set()
    
    for url in urls:
        
        try:
            
            url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
            
        except HydrusExceptions.URLClassException:
            
            continue # not a url--something like "file:///C:/Users/Tall%20Man/Downloads/maxresdefault.jpg" ha ha ha
            
        
        normalised_urls.add( url )
        
    
    associable_urls = { url for url in normalised_urls if HG.client_controller.network_engine.domain_manager.ShouldAssociateURLWithFiles( url ) }
    
    return associable_urls
    
def ParseURL( url: str ) -> urllib.parse.ParseResult:
    
    url = url.strip()
    
    url = UnicodeNormaliseURL( url )
    
    return urllib.parse.urlparse( url )
    
OH_NO_NO_NETLOC_CHARACTERS = '?#'
OH_NO_NO_NETLOC_CHARACTERS_UNICODE_TRANSLATE = { ord( char ) : '_' for char in OH_NO_NO_NETLOC_CHARACTERS }

def RemoveWWWFromDomain( domain ):
    
    if domain.count( '.' ) > 1 and domain.startswith( 'www' ):
        
        domain = ConvertDomainIntoNextLevelDomain( domain )
        
    
    return domain
    
def UnicodeNormaliseURL( url: str ):
    
    if url.startswith( 'file:' ):
        
        return url
        
    
    # the issue is netloc, blah.com, cannot have certain unicode characters that look like others, or double ( e + accent ) characters that can be one accented-e, so we normalise
    # urllib.urlparse throws a valueerror if these are in, so let's switch out
    
    scheme_splitter = '://'
    netloc_splitter = '/'
    
    if scheme_splitter in url:
        
        ( scheme, netloc_and_path_and_rest ) = url.split( scheme_splitter, 1 )
        
        if netloc_splitter in netloc_and_path_and_rest:
            
            ( netloc, path_and_rest ) = netloc_and_path_and_rest.split( netloc_splitter, 1 )
            
        else:
            
            netloc = netloc_and_path_and_rest
            path_and_rest = None
            
        
        netloc = unicodedata.normalize( 'NFKC', netloc )
        
        netloc = netloc.translate( OH_NO_NO_NETLOC_CHARACTERS_UNICODE_TRANSLATE )
        
        scheme_and_netlock = scheme_splitter.join( ( scheme, netloc ) )
        
        if path_and_rest is None:
            
            url = scheme_and_netlock
            
        else:
            
            url = netloc_splitter.join( ( scheme_and_netlock, path_and_rest ) )
            
        
    
    return url
    