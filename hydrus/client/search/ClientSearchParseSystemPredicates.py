import collections.abc
import datetime

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers

from hydrus.client import ClientGlobals as CG
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchPredicate

from hydrus.external import SystemPredicateParser

def convert_timetuple_to_seconds( v ):
    
    ( days, hours, minutes, seconds ) = v
    
    return days * 86400 + hours * 3600 + minutes * 60 + seconds
    

def convert_double_hex_hashlist_and_other_to_double_bytes_and_other( hex_hashlist_and_other ):
    
    try:
        
        bytes_hashlist_1 = tuple( ( bytes.fromhex( hex_hash ) for hex_hash in hex_hashlist_and_other[0] ) )
        bytes_hashlist_2 = tuple( ( bytes.fromhex( hex_hash ) for hex_hash in hex_hashlist_and_other[1] ) )
        
    except HydrusExceptions.DataMissing as e:
        
        raise ValueError( str( e ) )
        
    
    return ( bytes_hashlist_1, bytes_hashlist_2, hex_hashlist_and_other[2] )
    

def convert_hex_hashlist_and_other_to_bytes_and_other( hex_hashlist_and_other ):
    
    try:
        
        bytes_hashlist = tuple( ( bytes.fromhex( hex_hash ) for hex_hash in hex_hashlist_and_other[0] ) )
        
    except HydrusExceptions.DataMissing as e:
        
        raise ValueError( str( e ) )
        
    
    return ( bytes_hashlist, hex_hashlist_and_other[1] )
    

def date_pred_generator( pred_type, o, v ):
    
    #Either a tuple of 4 non-negative integers: (years, months, days, hours) where the latter is < 24 OR
    #a datetime.date object. For the latter, only the YYYY-MM-DD format is accepted.
    
    if isinstance( v, datetime.datetime ):
        
        date_type = 'date'
        v = ( v.year, v.month, v.day, v.hour, v.minute )
        
    else:
        
        date_type = 'delta'
        
        if o == '=':
            
            o = HC.UNICODE_APPROX_EQUAL
            
        
    
    return ClientSearchPredicate.Predicate( pred_type, ( o, date_type, tuple( v ) ) )
    

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
        
        service_key = CG.client_controller.services_manager.GetServiceKeyFromName( HC.REAL_FILE_SERVICES, service_name )
        
    except Exception as e:
        
        raise HydrusExceptions.BadRequestException( 'Could not find the service "{}"!'.format( service_name ) )
        
    
    return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( is_in, status, service_key ) )
    

def num_file_relationships_pred_generator( o, v, u ):
    
    u_dict = {
        'not related/false positive' : HC.DUPLICATE_FALSE_POSITIVE,
        'duplicates' : HC.DUPLICATE_MEMBER,
        'alternates' : HC.DUPLICATE_ALTERNATE,
        'potential duplicates' : HC.DUPLICATE_POTENTIAL
    }
    
    dupe_type = u_dict[ u ]
    
    return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT, ( o, v, dupe_type ) )
    

def rating_service_pred_generator( operator, value_and_service_name ):
    
    try:
        
        ( value, service_name ) = value_and_service_name
        
        service_key = CG.client_controller.services_manager.GetServiceKeyFromName( HC.RATINGS_SERVICES, service_name )
        
        service = CG.client_controller.services_manager.GetService( service_key )
        
    except Exception as e:
        
        raise HydrusExceptions.BadRequestException( 'Could not find the service "{}"!'.format( service_name ) )
        
    
    if service.GetServiceType() == HC.LOCAL_RATING_NUMERICAL and isinstance( value, int ):
        
        value = service.ConvertStarsToRating( value )
        
    elif service.GetServiceType() == HC.LOCAL_RATING_INCDEC:
        
        if value == 'rated':
            
            operator = '>'
            value = 0
            
        elif value == 'not rated':
            
            operator = '='
            value = 0
            
        
    
    predicate_value = ( operator, value, service_key )
    
    return ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, value = predicate_value )
    

def strip_quotes( s: str ) -> str:
    
    if len( s ) > 2:
        
        for c in [ '\'', '"' ]:
            
            if s.startswith( c ) and s.endswith( c ):
                
                return s[1:-1]
                
            
        
    
    return s
    

def url_class_pred_generator( include, url_class_name ):
    
    description = f'has url with class {url_class_name}' if include else f'does not have url with class {url_class_name}'
    
    try:
        
        url_class = CG.client_controller.network_engine.domain_manager.GetURLClassFromName( url_class_name )
        
    except HydrusExceptions.DataMissing as e:
        
        raise ValueError( str( e ) )
        
    
    return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( include, 'url_class', url_class, description ) )
    

def views_or_viewtime_wash_desired_canvas_types( desired_canvas_types ):
    
    if len( desired_canvas_types ) == 0:
        
        from hydrus.client import ClientConstants as CC
        
        silly_lookup = {
            CC.CANVAS_MEDIA_VIEWER : 'media',
            CC.CANVAS_PREVIEW : 'preview',
            CC.CANVAS_CLIENT_API : 'client api'
        }
        
        desired_canvas_types = [ silly_lookup[ canvas_type ] for canvas_type in CG.client_controller.new_options.GetIntegerList( 'file_viewing_stats_interesting_canvas_types' ) ]
        
    
    return tuple( desired_canvas_types )
    

def views_pred_generator( o, v, u ):
    
    ( desired_canvas_types, o ) = o
    
    desired_canvas_types = views_or_viewtime_wash_desired_canvas_types( desired_canvas_types )
    
    return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'views', desired_canvas_types, o, v ) )
    

def viewtime_pred_generator( o, v, u ):
    
    ( desired_canvas_types, o ) = o
    
    desired_canvas_types = views_or_viewtime_wash_desired_canvas_types( desired_canvas_types )
    
    return ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'viewtime', desired_canvas_types, o, convert_timetuple_to_seconds( v ) ) )
    

SystemPredicateParser.InitialiseFiletypes( HC.mime_enum_lookup )
SystemPredicateParser.InitialiseFiletypes( HC.string_enum_lookup )
SystemPredicateParser.InitialiseFiletypes( { 'gif' : [ HC.IMAGE_GIF, HC.ANIMATION_GIF ] } )

pred_generators = {
    SystemPredicateParser.Predicate.EVERYTHING : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING ),
    SystemPredicateParser.Predicate.INBOX : lambda o, v, u: ClientSearchPredicate.SYSTEM_PREDICATE_INBOX.Duplicate(),
    SystemPredicateParser.Predicate.ARCHIVE : lambda o, v, u: ClientSearchPredicate.SYSTEM_PREDICATE_ARCHIVE.Duplicate(),
    SystemPredicateParser.Predicate.BEST_QUALITY_OF_GROUP : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING, True ),
    SystemPredicateParser.Predicate.NOT_BEST_QUALITY_OF_GROUP : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING, False ),
    SystemPredicateParser.Predicate.HAS_AUDIO : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, True ),
    SystemPredicateParser.Predicate.NO_AUDIO : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, False ),
    SystemPredicateParser.Predicate.HAS_TRANSPARENCY : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY, True ),
    SystemPredicateParser.Predicate.NO_TRANSPARENCY : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY, False ),
    SystemPredicateParser.Predicate.HAS_EXIF : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_EXIF, True ),
    SystemPredicateParser.Predicate.NO_EXIF : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_EXIF, False ),
    SystemPredicateParser.Predicate.HAS_HUMAN_READABLE_EMBEDDED_METADATA : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA, True ),
    SystemPredicateParser.Predicate.NO_HUMAN_READABLE_EMBEDDED_METADATA : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA, False ),
    SystemPredicateParser.Predicate.HAS_ICC_PROFILE : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, True ),
    SystemPredicateParser.Predicate.NO_ICC_PROFILE : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, False ),
    SystemPredicateParser.Predicate.HAS_FORCED_FILETYPE : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE, True ),
    SystemPredicateParser.Predicate.NO_FORCED_FILETYPE : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE, False ),
    SystemPredicateParser.Predicate.LIMIT : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LIMIT, v ),
    SystemPredicateParser.Predicate.FILETYPE : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, tuple( v ), inclusive = o == '=' ),
    SystemPredicateParser.Predicate.HAS_DURATION : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 0 ) ),
    SystemPredicateParser.Predicate.NO_DURATION : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 0 ) ),
    SystemPredicateParser.Predicate.HAS_FRAMERATE : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FRAMERATE, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 0 ) ),
    SystemPredicateParser.Predicate.NO_FRAMERATE : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FRAMERATE, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 0 ) ),
    SystemPredicateParser.Predicate.HAS_FRAMES : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_FRAMES, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 0 ) ),
    SystemPredicateParser.Predicate.NO_FRAMES : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_FRAMES, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 0 ) ),
    SystemPredicateParser.Predicate.HAS_WIDTH : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 0 ) ),
    SystemPredicateParser.Predicate.NO_WIDTH : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 0 ) ),
    SystemPredicateParser.Predicate.HAS_HEIGHT : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 0 ) ),
    SystemPredicateParser.Predicate.NO_HEIGHT : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 0 ) ),
    SystemPredicateParser.Predicate.HAS_NOTES : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_NOTES, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 0 ) ),
    SystemPredicateParser.Predicate.NO_NOTES : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_NOTES, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 0 ) ),
    SystemPredicateParser.Predicate.HAS_URLS : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 0 ) ),
    SystemPredicateParser.Predicate.NO_URLS : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 0 ) ),
    SystemPredicateParser.Predicate.HAS_WORDS : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 0 ) ),
    SystemPredicateParser.Predicate.NO_WORDS : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 0 ) ),
    SystemPredicateParser.Predicate.HAS_TAGS : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '*', '>', 0 ) ),
    SystemPredicateParser.Predicate.UNTAGGED : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '*', '=', 0 ) ),
    SystemPredicateParser.Predicate.NUM_OF_TAGS : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '*', o, v ) ),
    SystemPredicateParser.Predicate.NUM_OF_TAGS_WITH_NAMESPACE : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, v ),
    SystemPredicateParser.Predicate.NUM_OF_URLS : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( o, v ) ),
    SystemPredicateParser.Predicate.NUM_OF_WORDS : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( o, v ) ),
    SystemPredicateParser.Predicate.HEIGHT : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( o, v ) ),
    SystemPredicateParser.Predicate.WIDTH : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( o, v ) ),
    SystemPredicateParser.Predicate.FILESIZE : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( o, v, HydrusNumbers.UnitToInt( u ) ) ),
    SystemPredicateParser.Predicate.SIMILAR_TO_FILES : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES, convert_hex_hashlist_and_other_to_bytes_and_other( v ) ),
    SystemPredicateParser.Predicate.SIMILAR_TO_DATA : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA, convert_double_hex_hashlist_and_other_to_double_bytes_and_other( v ) ),
    SystemPredicateParser.Predicate.HASH : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HASH, convert_hex_hashlist_and_other_to_bytes_and_other( v ), inclusive = o == '=' ),
    SystemPredicateParser.Predicate.DURATION : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION, ClientNumberTest.NumberTest.STATICCreateFromCharacters( o, v ) ),
    SystemPredicateParser.Predicate.FRAMERATE : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FRAMERATE, ClientNumberTest.NumberTest.STATICCreateFromCharacters( o, v ) ),
    SystemPredicateParser.Predicate.NUM_OF_FRAMES : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_FRAMES, ClientNumberTest.NumberTest.STATICCreateFromCharacters( o, v ) ),
    SystemPredicateParser.Predicate.NUM_PIXELS : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_PIXELS, ( o, v, HydrusNumbers.PixelsToInt( u ) ) ),
    SystemPredicateParser.Predicate.RATIO : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATIO, ( o, v[0], v[1] ) ),
    SystemPredicateParser.Predicate.RATIO_SPECIAL : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATIO, ( o, v[0], v[1] ) ),
    SystemPredicateParser.Predicate.TAG_AS_NUMBER : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER, ( o[0], o[1], v ) ),
    SystemPredicateParser.Predicate.MEDIA_VIEWS : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'views', ( 'media', ), o, v ) ),
    SystemPredicateParser.Predicate.PREVIEW_VIEWS : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'views', ( 'preview', ), o, v ) ),
    SystemPredicateParser.Predicate.ALL_VIEWS : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'views', ( 'media', 'preview' ), o, v ) ),
    SystemPredicateParser.Predicate.NEW_VIEWS : views_pred_generator,
    SystemPredicateParser.Predicate.MEDIA_VIEWTIME : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'viewtime', ( 'media', ), o, convert_timetuple_to_seconds( v ) ) ),
    SystemPredicateParser.Predicate.PREVIEW_VIEWTIME : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'viewtime', ( 'preview', ), o, convert_timetuple_to_seconds( v ) ) ),
    SystemPredicateParser.Predicate.ALL_VIEWTIME : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'viewtime', ( 'media', 'preview' ), o, convert_timetuple_to_seconds( v ) ) ),
    SystemPredicateParser.Predicate.NEW_VIEWTIME : viewtime_pred_generator,
    SystemPredicateParser.Predicate.URL_REGEX : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( True, 'regex', v, 'has url matching regex {}'.format( v ) ) ),
    SystemPredicateParser.Predicate.NO_URL_REGEX : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( False, 'regex', v, 'does not have url matching regex {}'.format( v ) ) ),
    SystemPredicateParser.Predicate.URL : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( True, 'exact_match', v, 'has url {}'.format( v ) ) ),
    SystemPredicateParser.Predicate.NO_URL : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( False, 'exact_match', v, 'does not have url {}'.format( v ) ) ),
    SystemPredicateParser.Predicate.DOMAIN : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( True, 'domain', v, 'has url with domain {}'.format( v ) ) ),
    SystemPredicateParser.Predicate.NO_DOMAIN : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( False, 'domain', v, 'does not have url with domain {}'.format( v ) ) ),
    SystemPredicateParser.Predicate.URL_CLASS : lambda o, v, u: url_class_pred_generator( True, v ),
    SystemPredicateParser.Predicate.NO_URL_CLASS : lambda o, v, u: url_class_pred_generator( False, v ),
    SystemPredicateParser.Predicate.MOD_DATE : lambda o, v, u: date_pred_generator( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, o, v ),
    SystemPredicateParser.Predicate.ARCHIVED_DATE : lambda o, v, u: date_pred_generator( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME, o, v ),
    SystemPredicateParser.Predicate.LAST_VIEWED_TIME : lambda o, v, u: date_pred_generator( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME, o, v ),
    SystemPredicateParser.Predicate.TIME_IMPORTED : lambda o, v, u: date_pred_generator( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME, o, v ),
    SystemPredicateParser.Predicate.FILE_SERVICE : file_service_pred_generator,
    SystemPredicateParser.Predicate.NUM_FILE_RELS : num_file_relationships_pred_generator,
    SystemPredicateParser.Predicate.NUM_NOTES : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_NOTES, ClientNumberTest.NumberTest.STATICCreateFromCharacters( o, v ) ),
    SystemPredicateParser.Predicate.HAS_NOTE_NAME : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_NOTE_NAME, ( True, strip_quotes( v ) ) ),
    SystemPredicateParser.Predicate.NO_NOTE_NAME : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_NOTE_NAME, ( False, strip_quotes( v ) ) ),
    SystemPredicateParser.Predicate.HAS_RATING : lambda o, v, u: rating_service_pred_generator( '=', ( 'rated', v ) ),
    SystemPredicateParser.Predicate.NO_RATING : lambda o, v, u: rating_service_pred_generator( '=', ( 'not rated', v ) ),
    SystemPredicateParser.Predicate.RATING_SPECIFIC_NUMERICAL : lambda o, v, u: rating_service_pred_generator( o, v ),
    SystemPredicateParser.Predicate.RATING_SPECIFIC_LIKE_DISLIKE : lambda o, v, u: rating_service_pred_generator( '=', v ),
    SystemPredicateParser.Predicate.RATING_SPECIFIC_INCDEC : lambda o, v, u: rating_service_pred_generator( o, v ),
    SystemPredicateParser.Predicate.TAG_ADVANCED_INCLUSIVE : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TAG_ADVANCED, ( o[0], o[1], o[2], v ) ),
    SystemPredicateParser.Predicate.TAG_ADVANCED_EXCLUSIVE : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TAG_ADVANCED, ( o[0], o[1], o[2], v ), inclusive = False ),
    SystemPredicateParser.Predicate.RATING_ADVANCED : lambda o, v, u: ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING_ADVANCED, v ),
}

def ParseSystemPredicateStringsToPredicates( system_predicate_strings: collections.abc.Collection[ str ], discard_failures = False ) -> list[ ClientSearchPredicate.Predicate ]:
    
    system_predicates = []
    
    for s in system_predicate_strings:
        
        try:
            
            ( ext_pred_type, operator, value, unit ) = SystemPredicateParser.parse_system_predicate( s )
            
            if ext_pred_type not in pred_generators:
                
                raise HydrusExceptions.BadRequestException( 'Sorry, do not know how to parse "{}" yet!'.format( s ) )
                
            
            predicate = pred_generators[ ext_pred_type ]( operator, value, unit )
            
            system_predicates.append( predicate )
            
        except ValueError as e:
            
            if discard_failures:
                
                continue
                
            
            raise HydrusExceptions.BadRequestException( 'Could not parse system predicate "{}"!'.format( s ) )
            
        except Exception as e:
            
            if discard_failures:
                
                continue
                
            
            raise HydrusExceptions.BadRequestException( 'Problem when trying to parse this system predicate: "{}"!'.format( s ) )
            
        
    
    return system_predicates
    
