import http.cookiejar
import re

import unicodedata
import urllib.parse

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientGlobals as CG

percent_encoding_re = re.compile( r'%[0-9A-Fa-f]{2}' )
double_hex_re = re.compile( r'[0-9A-Fa-f]{2}' )
PARAM_EXCEPTION_CHARS = "!$&'()*+,;=@:/?" # https://www.rfc-editor.org/rfc/rfc3986#section-3.4
PATH_EXCEPTION_CHARS = "!$&'()*+,;=@:" # https://www.rfc-editor.org/rfc/rfc3986#section-3.3

def ensure_component_is_encoded( mixed_encoding_string: str, safe_chars: str ) -> str:
    
    # this guy is supposed to be idempotent!
    
    # we do not want to double-encode %40 to %2540
    # we do want to encode a % sign on its own
    # so let's split by % and then join it up again somewhat cleverly
    
    # this function fails when called to examine a query text for "120%120%hello", the hit new anime series, but I think that's it
    
    parts_of_mixed_encoding_string = mixed_encoding_string.split( '%' )
    
    encoded_parts = []
    
    for ( i, part ) in enumerate( parts_of_mixed_encoding_string ):
        
        if i > 0:
            
            encoded_parts.append( '%' ) # we add the % back in
            
            if double_hex_re.match( part ) is None:
                
                # this part does not start with two hex chars, hence the preceding % character was not encoded, so we make the joiner '%25'
                encoded_parts.append( '25' )
                
            
        
        encoded_parts.append( urllib.parse.quote( part, safe = safe_chars ) )
        
    
    encoded_string = ''.join( encoded_parts )
    
    return encoded_string
    

def ensure_param_component_is_encoded( param_component: str ) -> str:
    """
    Either the key or the value. It can include a mix of encoded and non-encoded characters, it will be returned all encoded.
    
    If you have a tag sub-component that needs to encode "=" or "+", like "6+girls", this will not do it!! You need to call ensure_component_is_encoded with no safe_chars!
    """
    
    return ensure_component_is_encoded( param_component, PARAM_EXCEPTION_CHARS )
    

def ensure_path_component_is_encoded( path_component: str ) -> str:
    """
    A single path component, no slashes. It can include a mix of encoded and non-encoded characters, it will be returned all encoded.
    """
    
    return ensure_component_is_encoded( path_component, PATH_EXCEPTION_CHARS )
    

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
    if '.' not in domain or re.search( r'^[\d.:]+$', domain ) is not None:
        
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
    

def ConvertDomainIntoSortable( domain: str ):
    
    second_level_domain = ConvertDomainIntoSecondLevelDomain( domain )
    
    if domain == second_level_domain:
        
        subdomains_in_power_order = tuple()
        
    else:
        
        prefix_component = domain.replace( '.' + second_level_domain, '' )
        
        subdomains_in_power_order = tuple( reversed( prefix_component.split( '.' ) ) )
        
    
    # ( mysite.com, tuple() )
    # ( mysite.com, ( 'artistname', ) )
    return ( second_level_domain, subdomains_in_power_order )
    

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
        
    

def ConvertPathTextToList( path: str ) -> list[ str ]:
    
    # /post/show/1326143/akunim-anthro-armband-armwear-clothed-clothing-fem
    
    # this is a valid URL, with double //
    # https://img2.gelbooru.com//images/80/c8/80c8646b4a49395fb36c805f316c49a9.jpg
    # We have a bunch of legacy URLs where I collapsed starting // down to /. Oh well!
    
    if CG.client_controller.new_options.GetBoolean( 'remove_leading_url_double_slashes' ):
        
        # old legacy way
        while path.startswith( '/' ):
            
            path = path[ 1 : ]
            
        
    else:
        
        # new test that supports urls properly, but may break some url classes but fingers-crossed it isn't a big deal
        if path.startswith( '/' ):
            
            path = path[ 1 : ]
            
        
    
    # post/show/1326143/akunim-anthro-armband-armwear-clothed-clothing-fem
    
    path_components = path.split( '/' )
    
    return path_components
    

def ConvertQueryDictToText( query_dict, single_value_parameters, param_order = None ):
    
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
                
                params.append( f'{key}={query_dict[ key ]}' )
                
            
        
    
    query_text = '&'.join( params )
    
    return query_text
    

def ConvertQueryTextToDict( query_text ):
    
    # in the old version of this func, we played silly games with character encoding. I made the foolish decision to try to handle/save URLs with %20 stuff decoded
    # this lead to complexity with odd situations like '6+girls+skirt', which would come here encoded as '6%2Bgirls+skirt' 
    # I flipped back and forth and tried to preserve the encoding if it did stepped on x or did not change y, what a mess!
    
    # I no longer do this. I will encode if there is no '%' in there already, which catches cases of humans pasting/typing an URL with something human, but only if it is non-destructive
    
    # Update: I still hate this a bit. I should have a parameter that says 'from human=True' and then anything we ingest should go through a normalisation( from_human = True ) wash
    # I don't like the '+' exception we have to do here, and it would be better isolated to just the initian from_human wash rather than basically every time we look at an url for normalisation
    # indeed, instead of having 'from_human' in here, I could have a 'EncodeQueryDict' that does best-attempt smart encoding from_human, once
    # this guy would then just be a glorified dict parser, great
    
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
                
            
            single_value_parameters.append( value )
            param_order.append( None )
            
        elif len( result ) == 2:
            
            ( key, value ) = result
            
            param_order.append( key )
            
            query_dict[ key ] = value
            
        
    
    return ( query_dict, single_value_parameters, param_order )
    

def ConvertURLIntoDomain( url ):
    
    CheckLooksLikeAFullURL( url )
    
    parser_result = ParseURL( url )
    
    domain = parser_result.netloc
    
    return domain
    

def ConvertURLIntoSecondLevelDomain( url ):
    
    domain = ConvertURLIntoDomain( url )
    
    return ConvertDomainIntoSecondLevelDomain( domain )
    

def ConvertURLToHumanString( url: str ) -> str:
    
    # ok so the idea here is that we want to store 'ugly' urls behind the scenes, with quoted %20 gubbins, but any time we present to the user, we want to convert all that to real (URL-invalid) characters 
    # although there are some caveats, we can pretty much just do a dequote on the whole string and it'll be fine most of the time mate
    # if we have a unicode domain, we'll need to figure out 'punycode' decoding, but w/e for now
    
    pretty_url = urllib.parse.unquote( url )
    
    return pretty_url
    

def CookieDomainMatches( cookie, search_domain ):
    
    cookie_domain = cookie.domain
    
    # blah.com is viewable by blah.com
    matches_exactly = cookie_domain == search_domain
    
    # .blah.com is viewable by blah.com
    matches_dot = cookie_domain == '.' + search_domain
    
    # .blah.com applies to subdomain.blah.com, blah.com does not
    valid_subdomain = cookie_domain.startswith( '.' ) and search_domain.endswith( cookie_domain )
    
    return matches_exactly or matches_dot or valid_subdomain
    

def GetCookie( cookies, search_domain, cookie_name_string_match ):
    
    for cookie in cookies:
        
        if CookieDomainMatches( cookie, search_domain ) and cookie_name_string_match.Matches( cookie.name ):
            
            return cookie
            
        
    
    raise HydrusExceptions.DataMissing( 'Cookie "' + cookie_name_string_match.ToString() + '" not found for domain ' + search_domain + '!' )
    

def GetSearchURLs( url ):
    
    search_urls = set()
    
    search_urls.add( url )
    
    try:
        
        ephemeral_normalised_url = CG.client_controller.network_engine.domain_manager.NormaliseURL( url, for_server = True )
        
        search_urls.add( ephemeral_normalised_url )
        
        normalised_url = CG.client_controller.network_engine.domain_manager.NormaliseURL( url )
        
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
        
        # legacy issue, dealing with URLs we previously collapsed this way
        # not amazing, but the idea that two urls that differ this way are _actually_ different rather than a storage/parsing discrepancy is not real
        if path.startswith( '//' ):
            
            collapsed_path = path
            
            while collapsed_path.startswith( '//' ):
                
                collapsed_path = collapsed_path[ 1 : ]
                
            
            collapsed_adjusted_url = urllib.parse.urlunparse( ( scheme, netloc, collapsed_path, params, query, fragment ) )
            
            search_urls.add( collapsed_adjusted_url )
            
        
        alt_netloc = None
        
        if netloc.startswith( 'www' ):
            
            try:
                
                alt_netloc = RemoveWWWFromDomain( netloc )
                
            except HydrusExceptions.URLClassException:
                
                pass
                
            
        else:
            
            alt_netloc = 'www.' + netloc
            
        
        if alt_netloc is not None:
            
            adjusted_url = urllib.parse.urlunparse( ( scheme, alt_netloc, path, params, query, fragment ) )
            
            search_urls.add( adjusted_url )
            
        
    
    for url in list( search_urls ):
        
        if url.endswith( '/' ):
            
            search_urls.add( url[:-1] )
            
        else:
            
            search_urls.add( url + '/' )
            
        
    
    return search_urls
    

def CheckLooksLikeAFullURL( text: str ):
    
    try:
        
        p = ParseURL( text )
        
        if p.scheme == '':
            
            raise HydrusExceptions.URLClassException( 'No scheme--did you forgot http/https?--in "{text}"!' )
            
        
        if p.netloc == '':
            
            raise HydrusExceptions.URLClassException( 'No domain in "{text}"!' )
            
        
    except:
        
        raise HydrusExceptions.URLClassException( f'Could not parse "{text}" at all!' )
        
    

def LooksLikeAFullURL( text: str ) -> bool:
    
    try:
        
        CheckLooksLikeAFullURL( text )
        
        return True
        
    except HydrusExceptions.URLClassException:
        
        return False
        
    

def NetworkReportMode( message: str ):
    
    if HG.network_report_mode:
        
        if HG.network_report_mode_silent:
            
            HydrusData.Print( message )
            
        else:
            
            HydrusData.ShowText( message ) 
            
        
    

def NormaliseAndFilterAssociableURLs( urls ):
    
    normalised_urls = set()
    
    for url in urls:
        
        try:
            
            CheckLooksLikeAFullURL( url )
            
            url = CG.client_controller.network_engine.domain_manager.NormaliseURL( url )
            
        except HydrusExceptions.URLClassException:
            
            continue # not a url--something like "file:///C:/Users/Tall%20Man/Downloads/maxresdefault.jpg" ha ha ha
            
        
        normalised_urls.add( url )
        
    
    associable_urls = { url for url in normalised_urls if CG.client_controller.network_engine.domain_manager.ShouldAssociateURLWithFiles( url ) }
    
    return associable_urls
    

def ParseURL( url: str ) -> urllib.parse.ParseResult:
    
    url = url.strip()
    
    url = UnicodeNormaliseURL( url )
    
    try:
        
        return urllib.parse.urlparse( url )
        
    except Exception as e:
        
        raise HydrusExceptions.URLClassException( f'Problem with URL ({e})! URL text was "{url}"' )
        
    

def EnsureURLIsEncoded( url: str, keep_fragment = True ) -> str:
    
    if not LooksLikeAFullURL( url ):
        
        return url
        
    
    try:
        
        p = ParseURL( url )
        
        scheme = p.scheme
        netloc = p.netloc
        params = p.params # just so you know, this is ancient web semicolon tech, can be ignored
        fragment = p.fragment
        
        path_components = ConvertPathTextToList( p.path )
        ( query_dict, single_value_parameters, param_order ) = ConvertQueryTextToDict( p.query )
        
        param_order = [ ensure_param_component_is_encoded( param ) if param is not None else None for param in param_order ]
        
        path_components = [ ensure_path_component_is_encoded( path_component ) for path_component in path_components ]
        query_dict = { ensure_param_component_is_encoded( name ) : ensure_param_component_is_encoded( value ) for ( name, value ) in query_dict.items() }
        single_value_parameters = [ ensure_param_component_is_encoded( single_value_parameter ) for single_value_parameter in single_value_parameters ]
        
        path = '/' + '/'.join( path_components )
        query = ConvertQueryDictToText( query_dict, single_value_parameters, param_order = param_order )
        
        if not keep_fragment:
            
            fragment = ''
            
        
        clean_url = urllib.parse.urlunparse( ( scheme, netloc, path, params, query, fragment ) )
        
        return clean_url
        
    except:
        
        return url
        
    

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
