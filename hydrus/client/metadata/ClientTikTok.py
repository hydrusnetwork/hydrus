import re
import urllib.parse

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusTags

_TIKTOK_HANDLE_RE = re.compile( r'/@([^/?#]+)' )
_TIKTOK_HASHTAG_RE = re.compile( r'(?<![A-Za-z0-9_])#([A-Za-z0-9_]+)' )
_TIKTOK_DESCRIPTION_NOTE_NAMES = ( 'description', 'caption', 'title', 'text' )

TIKTOK_URL_TYPES = (
    HC.URL_TYPE_POST,
    HC.URL_TYPE_API,
    HC.URL_TYPE_FILE,
    HC.URL_TYPE_GALLERY,
    HC.URL_TYPE_WATCHABLE,
    HC.URL_TYPE_UNKNOWN,
    HC.URL_TYPE_DESIRED,
    HC.URL_TYPE_SOURCE,
    HC.URL_TYPE_SUB_GALLERY
)


def _LooksLikeTikTokURL( url: str ) -> bool:
    
    if not url:
        
        return False
        
    
    try:
        
        parsed = urllib.parse.urlparse( url )
        
    except Exception:
        
        return False
        
    
    netloc = parsed.netloc.lower()
    
    if not netloc:
        
        return False
        
    
    if ':' in netloc:
        
        netloc = netloc.split( ':', 1 )[0]
        
    
    return netloc.endswith( 'tiktok.com' )


def GetTikTokTagsFromURLs( urls ):
    
    raw_tags = set()
    
    for url in urls:
        
        if not _LooksLikeTikTokURL( url ):
            
            continue
            
        
        raw_tags.add( 'site:tiktok' )
        
        match = _TIKTOK_HANDLE_RE.search( url )
        
        if match is not None:
            
            handle = match.group( 1 )
            
            if handle.startswith( '@' ):
                
                handle = handle[1:]
                
            
            if handle:
                
                raw_tags.add( f'creator:{handle}' )
                
            
        
    
    return HydrusTags.CleanTags( raw_tags )


def GetTikTokDescriptionTextFromNotes( notes_manager ):
    
    return GetTikTokDescriptionTextFromNamesAndNotes( notes_manager.GetNamesToNotes() )


def GetTikTokDescriptionTextFromNamesAndNotes( names_and_notes ):
    
    if isinstance( names_and_notes, dict ):
        
        names_to_notes = dict( names_and_notes )
        
    else:
        
        names_to_notes = { name : note for ( name, note ) in names_and_notes }
        
    
    for ( name, note ) in names_to_notes.items():
        
        if name is None:
            
            continue
            
        
        lowered_name = name.strip().lower()
        
        if lowered_name in _TIKTOK_DESCRIPTION_NOTE_NAMES:
            
            return note
            
        
    
    if len( names_to_notes ) == 1:
        
        return next( iter( names_to_notes.values() ) )
        
    
    return None


def GetTikTokHashtagTagsFromText( text ):
    
    if not text:
        
        return set()
        
    
    raw_tags = set()
    
    for match in _TIKTOK_HASHTAG_RE.finditer( text ):
        
        hashtag = match.group( 1 )
        
        if hashtag:
            
            raw_tags.add( f'tiktok:{hashtag}' )
            
        
    
    return HydrusTags.CleanTags( raw_tags )


def GetTikTokTagsFromParsedMetadata( urls, names_and_notes, existing_tags = None ):
    
    tags = set()
    
    tags.update( GetTikTokTagsFromURLs( urls ) )
    
    looks_like_tiktok = len( tags ) > 0
    
    if existing_tags is not None and 'site:tiktok' in existing_tags:
        
        looks_like_tiktok = True
        
    
    if looks_like_tiktok:
        
        description_text = GetTikTokDescriptionTextFromNamesAndNotes( names_and_notes )
        
        if description_text is not None:
            
            tags.update( GetTikTokHashtagTagsFromText( description_text ) )
            
        
    
    return tags

