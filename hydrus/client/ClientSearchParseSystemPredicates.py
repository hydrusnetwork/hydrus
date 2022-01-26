import datetime
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientSearch

from hydrus.external import SystemPredicateParser

def file_service_pred_generator( o, v, u ):
    
    if o.startswith( 'is not' ):
        
        is_in = False
        
    else:
        
        is_in = True
        
    
    o_dict = {
        'currently in' : HC.CONTENT_STATUS_CURRENT,
        'deleted from' : HC.CONTENT_STATUS_DELETED,
        'pending to' : HC.CONTENT_STATUS_PENDING,
        'petitioned from' : HC.CONTENT_STATUS_PETITIONED
    }
    
    status = None
    
    for ( phrase, possible_status ) in o_dict.items():
        
        if phrase in o:
            
            status = possible_status
            
            break
            
        
    
    if status is None:
        
        raise HydrusExceptions.BadRequestException( 'Did not understand the file service status!' )
        
    
    try:
        
        service_name = v
        
        service_key = HG.client_controller.services_manager.GetServiceKeyFromName( HC.FILE_SERVICES, service_name )
        
    except:
        
        raise HydrusExceptions.BadRequestException( 'Could not find the service "{}"!'.format( service_name ) )
        
    
    return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( is_in, status, service_key ) )
    
def filetype_pred_generator( v ):
    
    # v is a list of non-hydrus-standard filetype strings
    
    mimes = ( 1, )
    
    return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, mimes )
    
def date_pred_generator( pred_type, o, v ):
    
    #Either a tuple of 4 non-negative integers: (years, months, days, hours) where the latter is < 24 OR
    #a datetime.date object. For the latter, only the YYYY-MM-DD format is accepted.
    
    date_type = 'delta'
    
    if isinstance( v, datetime.date ):
        
        date_type = 'date'
        v = ( v.year, v.month, v.day )
        
    
    return ClientSearch.Predicate( pred_type, ( o, date_type, tuple( v ) ) )
    
def num_file_relationships_pred_generator( o, v, u ):
    
    u_dict = {
        'not related/false positive' : HC.DUPLICATE_FALSE_POSITIVE,
        'duplicates' : HC.DUPLICATE_MEMBER,
        'alternates' : HC.DUPLICATE_ALTERNATE,
        'potential duplicates' : HC.DUPLICATE_POTENTIAL
    }
    
    dupe_type = u_dict[ u ]
    
    return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT, ( o, v, dupe_type ) )
    
def url_class_pred_generator( include, url_class_name ):
    
    description = ( 'has {} url' if include else 'does not have {} url' ).format( url_class_name )
    
    try:
        
        url_class = HG.client_controller.network_engine.domain_manager.GetURLClassFromName( url_class_name )
        
    except HydrusExceptions.DataMissing as e:
        
        raise ValueError( str( e ) )
        
    
    return ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( include, 'url_class', url_class, description ) )
    
def convert_timetuple_to_seconds( v ):
    
    ( days, hours, minutes, seconds ) = v
    
    return days * 86400 + hours * 3600 + minutes * 60 + seconds
    
def convert_hex_hashlist_and_other_to_bytes_and_other( hex_hashlist_and_other ):
    
    try:
        
        bytes_hashlist = tuple( ( bytes.fromhex( hex_hash ) for hex_hash in hex_hashlist_and_other[0] ) )
        
    except HydrusExceptions.DataMissing as e:
        
        raise ValueError( str( e ) )
        
    
    return ( bytes_hashlist, hex_hashlist_and_other[1] )
    
SystemPredicateParser.InitialiseFiletypes( HC.mime_enum_lookup )

pred_generators = {
    SystemPredicateParser.Predicate.EVERYTHING : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING ),
    SystemPredicateParser.Predicate.INBOX : lambda o, v, u: ClientSearch.SYSTEM_PREDICATE_INBOX.Duplicate(),
    SystemPredicateParser.Predicate.ARCHIVE : lambda o, v, u: ClientSearch.SYSTEM_PREDICATE_ARCHIVE.Duplicate(),
    SystemPredicateParser.Predicate.BEST_QUALITY_OF_GROUP : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING, True ),
    SystemPredicateParser.Predicate.NOT_BEST_QUALITY_OF_GROUP : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING, False ),
    SystemPredicateParser.Predicate.HAS_AUDIO : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, True ),
    SystemPredicateParser.Predicate.NO_AUDIO : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, False ),
    SystemPredicateParser.Predicate.HAS_ICC_PROFILE : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, True ),
    SystemPredicateParser.Predicate.NO_ICC_PROFILE : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, False ),
    SystemPredicateParser.Predicate.LIMIT : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, v ),
    SystemPredicateParser.Predicate.FILETYPE : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, tuple( v ) ),
    SystemPredicateParser.Predicate.HAS_DURATION : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( '>', 0 ) ),
    SystemPredicateParser.Predicate.NO_DURATION : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( '=', 0 ) ),
    SystemPredicateParser.Predicate.HAS_TAGS : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '>', 0 ) ),
    SystemPredicateParser.Predicate.UNTAGGED : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '=', 0 ) ),
    SystemPredicateParser.Predicate.NUM_OF_TAGS : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, o, v ) ),
    SystemPredicateParser.Predicate.NUM_OF_WORDS : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( o, v ) ),
    SystemPredicateParser.Predicate.HEIGHT : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( o, v ) ),
    SystemPredicateParser.Predicate.WIDTH : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( o, v ) ),
    SystemPredicateParser.Predicate.FILESIZE : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( o, v, HydrusData.ConvertUnitToInt( u ) ) ),
    SystemPredicateParser.Predicate.SIMILAR_TO : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, convert_hex_hashlist_and_other_to_bytes_and_other( v ) ),
    SystemPredicateParser.Predicate.HASH : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HASH, convert_hex_hashlist_and_other_to_bytes_and_other( v ) ),
    SystemPredicateParser.Predicate.DURATION : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( o, v[0] * 1000 + v[1] ) ),
    SystemPredicateParser.Predicate.NUM_PIXELS : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_PIXELS, ( o, v, HydrusData.ConvertPixelsToInt( u ) ) ),
    SystemPredicateParser.Predicate.RATIO : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( o, v[0], v[1] ) ),
    SystemPredicateParser.Predicate.TAG_AS_NUMBER : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER, ( o[0], o[1], v ) ),
    SystemPredicateParser.Predicate.MEDIA_VIEWS : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'views', ( 'media', ), o, v ) ),
    SystemPredicateParser.Predicate.PREVIEW_VIEWS : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'views', ( 'preview', ), o, v ) ),
    SystemPredicateParser.Predicate.ALL_VIEWS : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'views', ( 'media', 'preview' ), o, v ) ),
    SystemPredicateParser.Predicate.MEDIA_VIEWTIME : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'viewtime', ( 'media', ), o, convert_timetuple_to_seconds( v ) ) ),
    SystemPredicateParser.Predicate.PREVIEW_VIEWTIME : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'viewtime', ( 'preview', ), o, convert_timetuple_to_seconds( v ) ) ),
    SystemPredicateParser.Predicate.ALL_VIEWTIME : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'viewtime', ( 'media', 'preview' ), o, convert_timetuple_to_seconds( v ) ) ),
    SystemPredicateParser.Predicate.URL_REGEX : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( True, 'regex', v, 'has a url matching regex: {}'.format( v ) ) ),
    SystemPredicateParser.Predicate.NO_URL_REGEX : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( False, 'regex', v, 'does not have a url matching regex: {}'.format( v ) ) ),
    SystemPredicateParser.Predicate.URL : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( True, 'exact_match', v, 'has url: {}'.format( v ) ) ),
    SystemPredicateParser.Predicate.NO_URL : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( False, 'exact_match', v, 'does not have url: {}'.format( v ) ) ),
    SystemPredicateParser.Predicate.DOMAIN : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( True, 'domain', v, 'has a url with domain: {}'.format( v ) ) ),
    SystemPredicateParser.Predicate.NO_DOMAIN : lambda o, v, u: ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( False, 'domain', v, 'does not have a url with domain: {}'.format( v ) ) ),
    SystemPredicateParser.Predicate.URL_CLASS : lambda o, v, u: url_class_pred_generator( True, v ),
    SystemPredicateParser.Predicate.NO_URL_CLASS : lambda o, v, u: url_class_pred_generator( False, v ),
    SystemPredicateParser.Predicate.MOD_DATE : lambda o, v, u: date_pred_generator( ClientSearch.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, o, v ),
    SystemPredicateParser.Predicate.LAST_VIEWED_TIME : lambda o, v, u: date_pred_generator( ClientSearch.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME, o, v ),
    SystemPredicateParser.Predicate.TIME_IMPORTED : lambda o, v, u: date_pred_generator( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, o, v ),
    SystemPredicateParser.Predicate.FILE_SERVICE : file_service_pred_generator,
    SystemPredicateParser.Predicate.NUM_FILE_RELS : num_file_relationships_pred_generator
}

def ParseSystemPredicateStringsToPredicates( system_predicate_strings: typing.Collection[ str ] ) -> typing.List[ ClientSearch.Predicate ]:
    
    system_predicates = []
    
    for s in system_predicate_strings:
        
        try:
            
            ( ext_pred_type, operator, value, unit ) = SystemPredicateParser.parse_system_predicate( s )
            
            if ext_pred_type not in pred_generators:
                
                raise HydrusExceptions.BadRequestException( 'Sorry, do not know how to parse "{}" yet!'.format( s ) )
                
            
            predicate = pred_generators[ ext_pred_type ]( operator, value, unit )
            
            system_predicates.append( predicate )
            
        except ValueError as e:
            
            raise HydrusExceptions.BadRequestException( 'Could not parse system predicate "{}"!'.format( s ) )
            
        except Exception as e:
            
            raise HydrusExceptions.BadRequestException( 'Problem when trying to parse this system predicate: "{}"!'.format( s ) )
            
        
    
    return system_predicates
