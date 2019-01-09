import bs4
from . import ClientNetworkingDomain
from . import ClientNetworkingJobs
from . import ClientParsing
from . import HydrusConstants as HC
from . import HydrusExceptions
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusTags
import json
import os
import re
import requests
import threading
import time
from . import HydrusData
from . import ClientConstants as CC
from . import HydrusGlobals as HG

def ConvertBooruToNewObjects( booru ):
    
    name = booru.GetName()
    
    name = 'zzz - auto-generated from legacy booru system - ' + name
    
    ( search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces ) = booru.GetData()
    
    if advance_by_page_num:
        
        search_url = search_url.replace( '%index%', '1' )
        
    else:
        
        search_url = search_url.replace( '%index%', '0' )
        
    
    gug = ClientNetworkingDomain.GalleryURLGenerator( name + ' search', url_template = search_url, replacement_phrase = '%tags%', search_terms_separator = search_separator, initial_search_text = 'tag search', example_search_text = 'blonde_hair blue_eyes' )
    
    #
    
    tag_rules = []
    
    rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING
    tag_name = None
    tag_attributes = { 'class' : thumb_classname }
    tag_index = None
    
    tag_rules.append( ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index ) )
    
    rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING
    tag_name = 'a'
    tag_attributes = None
    tag_index = None
    
    tag_rules.append( ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index ) )
    
    formula = ClientParsing.ParseFormulaHTML( tag_rules = tag_rules, content_to_fetch = ClientParsing.HTML_CONTENT_ATTRIBUTE, attribute_to_fetch = 'href' )
    
    url_type = HC.URL_TYPE_DESIRED
    priority = 50
    
    additional_info = ( url_type, priority )
    
    thumb_content_parser = ClientParsing.ContentParser( name = 'get post urls (based on old booru thumb search)', content_type = HC.CONTENT_TYPE_URLS, formula = formula, additional_info = additional_info )
    
    gallery_parser = ClientParsing.PageParser( name + ' gallery page parser', content_parsers = [ thumb_content_parser ], example_urls = [ gug.GetExampleURL() ] )
    
    #
    
    content_parsers = []
    
    if image_id is not None:
        
        tag_rules = []
        
        rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING
        tag_name = 'a'
        tag_attributes = { 'id' : image_id }
        tag_index = None
        
        tag_rules.append( ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index ) )
        
        formula = ClientParsing.ParseFormulaHTML( tag_rules = tag_rules, content_to_fetch = ClientParsing.HTML_CONTENT_ATTRIBUTE, attribute_to_fetch = 'href' )
        
        url_type = HC.URL_TYPE_DESIRED
        priority = 75
        
        additional_info = ( url_type, priority )
        
        image_link_content_parser = ClientParsing.ContentParser( name = 'get image file link url (based on old booru parser)', content_type = HC.CONTENT_TYPE_URLS, formula = formula, additional_info = additional_info )
        
        content_parsers.append( image_link_content_parser )
        
        #
        
        tag_rules = []
        
        rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING
        tag_name = 'img'
        tag_attributes = { 'id' : image_id }
        tag_index = None
        
        tag_rules.append( ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index ) )
        
        formula = ClientParsing.ParseFormulaHTML( tag_rules = tag_rules, content_to_fetch = ClientParsing.HTML_CONTENT_ATTRIBUTE, attribute_to_fetch = 'src' )
        
        url_type = HC.URL_TYPE_DESIRED
        priority = 50
        
        additional_info = ( url_type, priority )
        
        image_src_content_parser = ClientParsing.ContentParser( name = 'get image file src url (based on old booru parser)', content_type = HC.CONTENT_TYPE_URLS, formula = formula, additional_info = additional_info )
        
        content_parsers.append( image_src_content_parser )
        
    elif image_data is not None:
        
        tag_rules = []
        
        rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING
        tag_name = 'a'
        tag_attributes = None
        tag_index = None
        
        string_match = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = image_data, example_string = image_data )
        
        tag_rules.append( ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index, should_test_tag_string = True, tag_string_string_match = string_match ) )
        
        formula = ClientParsing.ParseFormulaHTML( tag_rules = tag_rules, content_to_fetch = ClientParsing.HTML_CONTENT_ATTRIBUTE, attribute_to_fetch = 'href' )
        
        url_type = HC.URL_TYPE_DESIRED
        priority = 50
        
        additional_info = ( url_type, priority )
        
        image_link_content_parser = ClientParsing.ContentParser( name = 'get image file url (based on old booru parser)', content_type = HC.CONTENT_TYPE_URLS, formula = formula, additional_info = additional_info )
        
        content_parsers.append( image_link_content_parser )
        
    
    for ( classname, namespace ) in list(tag_classnames_to_namespaces.items()):
        
        tag_rules = []
        
        rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING
        tag_name = None
        tag_attributes = { 'class' : classname }
        tag_index = None
        
        tag_rules.append( ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index ) )
        
        rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING
        tag_name = 'a'
        tag_attributes = None
        tag_index = None
        
        tag_rules.append( ClientParsing.ParseRuleHTML( rule_type = rule_type, tag_name = tag_name, tag_attributes = tag_attributes, tag_index = tag_index ) )
        
        formula = ClientParsing.ParseFormulaHTML( tag_rules = tag_rules, content_to_fetch = ClientParsing.HTML_CONTENT_STRING )
        
        additional_info = namespace
        
        tag_content_parser = ClientParsing.ContentParser( name = 'get "' + namespace + '" tags', content_type = HC.CONTENT_TYPE_MAPPINGS, formula = formula, additional_info = additional_info )
        
        content_parsers.append( tag_content_parser )
        
    
    post_parser = ClientParsing.PageParser( name + ' post page parser', content_parsers = content_parsers, example_urls = [] )
    
    #
    
    return ( gug, gallery_parser, post_parser )
    
def ConvertGalleryIdentifierToGUGKeyAndName( gallery_identifier ):
    
    gug_name = ConvertGalleryIdentifierToGUGName( gallery_identifier )
    
    from . import ClientDefaults
    
    gugs = ClientDefaults.GetDefaultGUGs()
    
    for gug in gugs:
        
        if gug.GetName() == gug_name:
            
            return gug.GetGUGKeyAndName()
            
        
    
    return ( HydrusData.GenerateKey(), gug_name )
    
def ConvertGalleryIdentifierToGUGName( gallery_identifier ):
    
    site_type = gallery_identifier.GetSiteType()
    
    if site_type == HC.SITE_TYPE_DEVIANT_ART:
        
        return 'deviant art artist lookup'
        
    elif site_type == HC.SITE_TYPE_TUMBLR:
        
        return 'tumblr username lookup'
        
    elif site_type == HC.SITE_TYPE_NEWGROUNDS:
        
        return 'newgrounds artist lookup'
        
    elif site_type == HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST:
        
        return 'hentai foundry artist lookup'
        
    elif site_type == HC.SITE_TYPE_HENTAI_FOUNDRY_TAGS:
        
        return 'hentai foundry tag search'
        
    elif site_type == HC.SITE_TYPE_PIXIV_ARTIST_ID:
        
        return 'pixiv artist lookup'
        
    elif site_type == HC.SITE_TYPE_PIXIV_TAG:
        
        return 'pixiv tag search'
        
    elif site_type == HC.SITE_TYPE_BOORU:
        
        booru_name_converter = {}
        
        booru_name_converter[ 'gelbooru' ] = 'gelbooru tag search'
        booru_name_converter[ 'safebooru' ] = 'safebooru tag search'
        booru_name_converter[ 'e621' ] = 'e621 tag search'
        booru_name_converter[ 'rule34@paheal' ] = 'rule34.paheal tag search'
        booru_name_converter[ 'danbooru' ] = 'danbooru tag search'
        booru_name_converter[ 'mishimmie' ] = 'mishimmie tag search'
        booru_name_converter[ 'rule34@booru.org' ] = 'rule34.xxx tag search'
        booru_name_converter[ 'furry@booru.org' ] = 'furry.booru.org tag search'
        booru_name_converter[ 'xbooru' ] = 'xbooru tag search'
        booru_name_converter[ 'konachan' ] = 'konachan tag search'
        booru_name_converter[ 'yande.re' ] = 'yande.re tag search'
        booru_name_converter[ 'tbib' ] = 'tbib tag search'
        booru_name_converter[ 'sankaku chan' ] = 'sankaku channel tag search'
        booru_name_converter[ 'sankaku idol' ] = 'sankaku idol tag search'
        booru_name_converter[ 'rule34hentai' ] = 'rule34hentai tag search'
        
        booru_name = gallery_identifier.GetAdditionalInfo()
        
        if booru_name in booru_name_converter:
            
            return booru_name_converter[ booru_name ]
            
        else:
            
            return booru_name
            
        
    else:
        
        return 'unknown site'
        
    
class GalleryIdentifier( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IDENTIFIER
    SERIALISABLE_NAME = 'Gallery Identifier'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, site_type = None, additional_info = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._site_type = site_type
        self._additional_info = additional_info
        
    
    def __eq__( self, other ):
        
        return self.__hash__() == other.__hash__()
        
    
    def __hash__( self ):
        
        return ( self._site_type, self._additional_info ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def __repr__( self ):
        
        text = 'Gallery Identifier: ' + HC.site_type_string_lookup[ self._site_type ]
        
        if self._site_type == HC.SITE_TYPE_BOORU:
            
            text += ': ' + str( self._additional_info )
            
        
        return text
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._site_type, self._additional_info )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._site_type, self._additional_info ) = serialisable_info
        
    
    def GetAdditionalInfo( self ):
        
        return self._additional_info
        
    
    def GetSiteType( self ):
        
        return self._site_type
        
    
    def ToString( self ):
        
        text = HC.site_type_string_lookup[ self._site_type ]
        
        if self._site_type == HC.SITE_TYPE_BOORU and self._additional_info is not None:
            
            booru_name = self._additional_info
            
            text = booru_name
            
        
        return text
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IDENTIFIER ] = GalleryIdentifier
