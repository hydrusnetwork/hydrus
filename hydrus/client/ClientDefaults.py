import re
import os

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusSerialisable
from hydrus.core.networking import HydrusNetworking

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData

def GetClientDefaultOptions():
    
    options = {}
    
    options[ 'play_dumper_noises' ] = True
    options[ 'export_path' ] = None
    options[ 'hpos' ] = 400
    options[ 'vpos' ] = -240
    options[ 'thumbnail_cache_size' ] = 25 * 1048576
    options[ 'fullscreen_cache_size' ] = 150 * 1048576
    options[ 'thumbnail_dimensions' ] = [ 150, 125 ]
    options[ 'password' ] = None
    options[ 'default_gui_session' ] = CC.LAST_SESSION_SESSION_NAME
    options[ 'idle_period' ] = 60 * 30
    options[ 'idle_mouse_period' ] = 60 * 10
    options[ 'idle_normal' ] = True
    options[ 'idle_shutdown' ] = CC.IDLE_ON_SHUTDOWN_ASK_FIRST
    options[ 'idle_shutdown_max_minutes' ] = 5
    options[ 'maintenance_delete_orphans_period' ] = 86400 * 3
    options[ 'trash_max_age' ] = 72
    options[ 'trash_max_size' ] = 2048
    options[ 'remove_trashed_files' ] = False
    options[ 'remove_filtered_files' ] = False
    options[ 'gallery_file_limit' ] = 2000
    options[ 'confirm_trash' ] = True
    options[ 'confirm_archive' ] = True
    options[ 'delete_to_recycle_bin' ] = True
    options[ 'animation_start_position' ] = 0.0
    options[ 'hide_preview' ] = False
    
    regex_favourites = []
    
    regex_favourites.append( ( r'[1-9]+\d*(?=.{4}$)', '\u2026' + r'0074.jpg -> 74' ) )
    regex_favourites.append( ( r'[^' + re.escape( os.path.sep ) + r']+(?=\s-)', r'E:\my collection\author name - v4c1p0074.jpg -> author name' ) )
    
    options[ 'regex_favourites' ] = regex_favourites
    
    default_namespace_colours = {}
    
    default_namespace_colours[ 'system' ] = ( 153, 101, 21 )
    default_namespace_colours[ 'meta' ] = ( 0, 0, 0 )
    default_namespace_colours[ 'creator' ] = ( 170, 0, 0 )
    default_namespace_colours[ 'studio' ] = ( 128, 0, 0 )
    default_namespace_colours[ 'character' ] = ( 0, 170, 0 )
    default_namespace_colours[ 'person' ] = ( 0, 128, 0 )
    default_namespace_colours[ 'series' ] = ( 170, 0, 170 )
    default_namespace_colours[ None ] = ( 114, 160, 193 )
    default_namespace_colours[ '' ] = ( 0, 111, 250 )
    
    options[ 'namespace_colours' ] = default_namespace_colours
    
    options[ 'proxy' ] = None
    
    options[ 'confirm_client_exit' ] = False
    
    options[ 'pause_export_folders_sync' ] = False
    options[ 'pause_import_folders_sync' ] = False
    options[ 'pause_repo_sync' ] = False
    options[ 'pause_subs_sync' ] = False
    
    return options
    
def GetDefaultCheckerOptions( name ):
    
    from hydrus.client.importing.options import ClientImportOptions
    
    if name == 'thread':
        
        return ClientImportOptions.CheckerOptions( intended_files_per_check = 4, never_faster_than = 300, never_slower_than = 86400, death_file_velocity = ( 1, 3 * 86400 ) )
        
    elif name == 'slow thread':
        
        return ClientImportOptions.CheckerOptions( intended_files_per_check = 1, never_faster_than = 4 * 3600, never_slower_than = 7 * 86400, death_file_velocity = ( 1, 30 * 86400 ) )
        
    elif name == 'artist subscription':
        
        return ClientImportOptions.CheckerOptions( intended_files_per_check = 4, never_faster_than = 86400, never_slower_than = 90 * 86400, death_file_velocity = ( 1, 180 * 86400 ) )
        
    elif name == 'fast tag subscription':
        
        return ClientImportOptions.CheckerOptions( intended_files_per_check = 10, never_faster_than = 43200, never_slower_than = 30 * 86400, death_file_velocity = ( 1, 90 * 86400 ) )
        
    elif name == 'slow tag subscription':
        
        return ClientImportOptions.CheckerOptions( intended_files_per_check = 1, never_faster_than = 7 * 86400, never_slower_than = 180 * 86400, death_file_velocity = ( 1, 365 * 86400 ) )
        
    
def GetDefaultHentaiFoundryInfo():

    info = {}
    
    info[ 'rating_nudity' ] = '3'
    info[ 'rating_violence' ] = '3'
    info[ 'rating_profanity' ] = '3'
    info[ 'rating_racism' ] = '3'
    info[ 'rating_sex' ] = '3'
    info[ 'rating_spoilers' ] = '3'
    
    info[ 'rating_yaoi' ] = '1'
    info[ 'rating_yuri' ] = '1'
    info[ 'rating_teen' ] = '1'
    info[ 'rating_guro' ] = '1'
    info[ 'rating_furry' ] = '1'
    info[ 'rating_beast' ] = '1'
    info[ 'rating_male' ] = '1'
    info[ 'rating_female' ] = '1'
    info[ 'rating_futa' ] = '1'
    info[ 'rating_other' ] = '1'
    info[ 'rating_scat' ] = '1'
    info[ 'rating_incest' ] = '1'
    info[ 'rating_rape' ] = '1'
    
    info[ 'filter_media' ] = 'A'
    info[ 'filter_order' ] = 'date_new'
    info[ 'filter_type' ] = '0'
    
    info[ 'yt0' ] = 'Apply' # the submit button wew lad
    
    return info
    
def GetDefaultGUGs():
    
    dir_path = os.path.join( HC.STATIC_DIR, 'default', 'gugs' )
    
    from hydrus.client.networking import ClientNetworkingDomain
    
    return GetDefaultObjectsFromPNGs( dir_path, ( ClientNetworkingDomain.GalleryURLGenerator, ClientNetworkingDomain.NestedGalleryURLGenerator ) )
    
def GetDefaultNGUGs():
    
    from hydrus.client.networking import ClientNetworkingDomain
    
    gugs = [ gug for gug in GetDefaultGUGs() if isinstance( gug, ClientNetworkingDomain.NestedGalleryURLGenerator ) ]
    
    return gugs
    
def GetDefaultSingleGUGs():
    
    from hydrus.client.networking import ClientNetworkingDomain
    
    gugs = [ gug for gug in GetDefaultGUGs() if isinstance( gug, ClientNetworkingDomain.GalleryURLGenerator ) ]
    
    return gugs
    
def GetDefaultImageboards():
    
    imageboards = []
    
    fourchan_common_form_fields = []
    
    fourchan_common_form_fields.append( ( 'resto', CC.FIELD_THREAD_ID, 'thread_id', True ) )
    fourchan_common_form_fields.append( ( 'email', CC.FIELD_TEXT, '', True ) )
    fourchan_common_form_fields.append( ( 'pwd', CC.FIELD_PASSWORD, '', True ) )
    fourchan_common_form_fields.append( ( 'recaptcha_response_field', CC.FIELD_VERIFICATION_RECAPTCHA, '6Ldp2bsSAAAAAAJ5uyx_lx34lJeEpTLVkP5k04qc', True ) )
    fourchan_common_form_fields.append( ( 'com', CC.FIELD_COMMENT, '', True ) )
    fourchan_common_form_fields.append( ( 'upfile', CC.FIELD_FILE, '', True ) )
    fourchan_common_form_fields.append( ( 'mode', CC.FIELD_TEXT, 'regist', False ) )
    
    fourchan_typical_form_fields = list( fourchan_common_form_fields )
    
    fourchan_typical_form_fields.insert( 1, ( 'name', CC.FIELD_TEXT, '', True ) )
    fourchan_typical_form_fields.insert( 3, ( 'sub', CC.FIELD_TEXT, '', True ) )
    
    fourchan_anon_form_fields = list( fourchan_common_form_fields )
    
    fourchan_anon_form_fields.insert( 1, ( 'name', CC.FIELD_TEXT, '', False ) )
    fourchan_anon_form_fields.insert( 3, ( 'sub', CC.FIELD_TEXT, '', False ) )
    
    fourchan_spoiler_form_fields = list( fourchan_typical_form_fields )
    
    fourchan_spoiler_form_fields.append( ( 'spoiler/on', CC.FIELD_CHECKBOX, 'False', True ) )
    
    GJP = [ HC.IMAGE_GIF, HC.IMAGE_PNG, HC.IMAGE_JPEG ]
    
    fourchan_typical_restrictions = { CC.RESTRICTION_MAX_FILE_SIZE : 3145728, CC.RESTRICTION_ALLOWED_MIMES : GJP }
    
    fourchan_imageboards = []
    
    fourchan_imageboards.append( ClientData.Imageboard( '/3/', 'https://sys.4chan.org/3/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/a/', 'https://sys.4chan.org/a/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/adv/', 'https://sys.4chan.org/adv/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/an/', 'https://sys.4chan.org/an/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/asp/', 'https://sys.4chan.org/asp/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/b/', 'https://sys.4chan.org/b/post', 75, fourchan_anon_form_fields, { CC.RESTRICTION_MAX_FILE_SIZE : 2097152, CC.RESTRICTION_ALLOWED_MIMES : GJP } ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/c/', 'https://sys.4chan.org/c/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/cgl/', 'https://sys.4chan.org/cgl/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/ck/', 'https://sys.4chan.org/ck/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/cm/', 'https://sys.4chan.org/cm/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/co/', 'https://sys.4chan.org/co/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/d/', 'https://sys.4chan.org/d/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/diy/', 'https://sys.4chan.org/diy/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/e/', 'https://sys.4chan.org/e/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/fa/', 'https://sys.4chan.org/fa/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/fit/', 'https://sys.4chan.org/fit/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/g/', 'https://sys.4chan.org/g/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/gd/', 'https://sys.4chan.org/gd/post', 75, fourchan_typical_form_fields, { CC.RESTRICTION_MAX_FILE_SIZE : 8388608, CC.RESTRICTION_ALLOWED_MIMES : [ HC.IMAGE_GIF, HC.IMAGE_PNG, HC.IMAGE_JPEG, HC.APPLICATION_PDF ] } ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/gif/', 'https://sys.4chan.org/gif/post', 75, fourchan_typical_form_fields, { CC.RESTRICTION_MAX_FILE_SIZE : 4194304, CC.RESTRICTION_ALLOWED_MIMES : [ HC.IMAGE_GIF ] } ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/h/', 'https://sys.4chan.org/h/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/hc/', 'https://sys.4chan.org/hc/post', 75, fourchan_typical_form_fields, { CC.RESTRICTION_MAX_FILE_SIZE : 8388608, CC.RESTRICTION_ALLOWED_MIMES : GJP } ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/hm/', 'https://sys.4chan.org/hm/post', 75, fourchan_typical_form_fields, { CC.RESTRICTION_MAX_FILE_SIZE : 8388608, CC.RESTRICTION_ALLOWED_MIMES : GJP } ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/hr/', 'https://sys.4chan.org/hr/post', 75, fourchan_typical_form_fields, { CC.RESTRICTION_MAX_FILE_SIZE : 8388608, CC.RESTRICTION_ALLOWED_MIMES : GJP, CC.RESTRICTION_MIN_RESOLUTION : ( 700, 700 ), CC.RESTRICTION_MAX_RESOLUTION : ( 10000, 10000 ) } ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/int/', 'https://sys.4chan.org/int/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/jp/', 'https://sys.4chan.org/jp/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/k/', 'https://sys.4chan.org/k/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/lgbt/', 'https://sys.4chan.org/lgbt/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/lit/', 'https://sys.4chan.org/lit/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/m/', 'https://sys.4chan.org/m/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/mlp/', 'https://sys.4chan.org/mlp/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/mu/', 'https://sys.4chan.org/mu/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/n/', 'https://sys.4chan.org/n/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/o/', 'https://sys.4chan.org/o/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/p/', 'https://sys.4chan.org/p/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/po/', 'https://sys.4chan.org/po/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/pol/', 'https://sys.4chan.org/pol/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/r9k/', 'https://sys.4chan.org/r9k/post', 75, fourchan_spoiler_form_fields, { CC.RESTRICTION_MAX_FILE_SIZE : 2097152, CC.RESTRICTION_ALLOWED_MIMES : GJP } ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/s/', 'https://sys.4chan.org/s/post', 75, fourchan_typical_form_fields, { CC.RESTRICTION_MAX_FILE_SIZE : 8388608, CC.RESTRICTION_ALLOWED_MIMES : GJP } ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/sci/', 'https://sys.4chan.org/sci/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/soc/', 'https://sys.4chan.org/soc/post', 75, fourchan_anon_form_fields, { CC.RESTRICTION_MAX_FILE_SIZE : 2097152, CC.RESTRICTION_ALLOWED_MIMES : GJP } ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/sp/', 'https://sys.4chan.org/sp/post', 75, fourchan_typical_form_fields, { CC.RESTRICTION_MAX_FILE_SIZE : 4194304, CC.RESTRICTION_ALLOWED_MIMES : GJP } ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/tg/', 'https://sys.4chan.org/tg/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/toy/', 'https://sys.4chan.org/toy/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/trv/', 'https://sys.4chan.org/trv/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/tv/', 'https://sys.4chan.org/tv/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/u/', 'https://sys.4chan.org/u/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/v/', 'https://sys.4chan.org/v/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/vg/', 'https://sys.4chan.org/vg/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/vr/', 'https://sys.4chan.org/vr/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/w/', 'https://sys.4chan.org/w/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/wg/', 'https://sys.4chan.org/wg/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/wsg/', 'https://sys.4chan.org/wsg/post', 75, fourchan_typical_form_fields, { CC.RESTRICTION_MAX_FILE_SIZE : 4194304, CC.RESTRICTION_ALLOWED_MIMES : [ HC.IMAGE_GIF ] } ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/x/', 'https://sys.4chan.org/x/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/y/', 'https://sys.4chan.org/y/post', 75, fourchan_typical_form_fields, fourchan_typical_restrictions ) )
    fourchan_imageboards.append( ClientData.Imageboard( '/vp/', 'https://sys.4chan.org/vp/post', 75, fourchan_spoiler_form_fields, fourchan_typical_restrictions ) )
    
    imageboards.append( ( '4chan', fourchan_imageboards ) )
    
    return imageboards
    
def GetDefaultLoginScripts():
    
    dir_path = os.path.join( HC.STATIC_DIR, 'default', 'login_scripts' )
    
    from hydrus.client.networking import ClientNetworkingLogin
    
    return GetDefaultObjectsFromPNGs( dir_path, ( ClientNetworkingLogin.LoginScriptDomain, ) )
    
def GetDefaultParsers():
    
    dir_path = os.path.join( HC.STATIC_DIR, 'default', 'parsers' )
    
    from hydrus.client import ClientParsing
    
    return GetDefaultObjectsFromPNGs( dir_path, ( ClientParsing.PageParser, ) )
    
def GetDefaultScriptRows():
    
    script_info = []
    
    script_info.append( ( 32, 'iqdb danbooru', 2, HydrusData.GetNow(), '''["https://danbooru.iqdb.org/", 1, 0, [55, 1, [[], "some hash bytes"]], "file", {}, [[29, 1, ["link to danbooru", [27, 6, [[26, 1, [[62, 2, [0, "td", {"class": "image"}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 0, "href", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], [[30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "section", {"id": "tag-list"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "li", {"class": "tag-type-1"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {"class": "search-tag"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, "creator"]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "section", {"id": "tag-list"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "li", {"class": "tag-type-3"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {"class": "search-tag"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, "series"]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "section", {"id": "tag-list"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "li", {"class": "tag-type-4"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {"class": "search-tag"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, "character"]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "section", {"id": "tag-list"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "li", {"class": "tag-type-0"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {"class": "search-tag"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, ""]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "section", {"id": "post-information"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "li", {}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [2, "Rating:*", null, null, "Rating: Safe"]], [55, 1, [[[0, 8]], "Rating: Safe"]]]], 0, false, "rating"]], [30, 4, ["", 7, [27, 6, [[26, 1, [[62, 2, [0, "section", {"id": "post-information"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "li", {}, null, null, true, [51, 1, [2, "Source:*", null, null, "Source:"]]]], [62, 2, [0, "a", {}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 0, "href", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, [8, 0]]]]]], [30, 4, ["no iqdb match found", 8, [27, 6, [[26, 1, [[62, 2, [0, "th", {}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, [false, [51, 1, [2, "Best match", null, null, "Best match"]]]]]]]''' ) )
    script_info.append( ( 32, 'danbooru md5', 2, HydrusData.GetNow(), '''["https://danbooru.donmai.us/", 0, 1, [55, 1, [[[4, "hex"]], "some hash bytes"]], "md5", {"page": "post", "s": "list"}, [[30, 4, ["we got sent back to main gallery page -- title test", 8, [27, 6, [[26, 1, [[62, 2, [0, "head", {}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "title", {}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, [true, [51, 1, [2, "Image List", null, null, "Image List"]]]]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-0"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, ""]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-3"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, "series"]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-1"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, "creator"]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-4"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, "character"]], [30, 4, ["we got sent back to main gallery page -- page links exist", 8, [27, 6, [[26, 1, [[62, 2, [0, "div", {}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 0, "class", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, [true, [51, 1, [2, "pagination", null, null, "pagination"]]]]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "section", {"id": "post-information"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "li", {}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "href", [51, 1, [2, "Rating:*", null, null, "Rating: Safe"]], [55, 1, [[[0, 8]], "Rating: Safe"]]]], 0, false, "rating"]]]]''' ) )
    script_info.append( ( 32, 'gelbooru md5', 2, HydrusData.GetNow(), '''["http://gelbooru.com/index.php", 0, 1, [55, 1, [[[4, "hex"]], "some hash bytes"]], "md5", {"s": "list", "page": "post"}, [[30, 6, ["we got sent back to main gallery page -- title test", 8, [27, 7, [[26, 1, [[62, 2, [0, "head", {}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "title", {}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [84, 1, [26, 1, []]]]], [true, [51, 1, [2, "Image List", null, null, "Image List"]]]]], [30, 6, ["", 0, [27, 7, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-general"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [84, 1, [26, 1, []]]]], ""]], [30, 6, ["", 0, [27, 7, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-copyright"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [84, 1, [26, 1, []]]]], "series"]], [30, 6, ["", 0, [27, 7, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-artist"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [84, 1, [26, 1, []]]]], "creator"]], [30, 6, ["", 0, [27, 7, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-character"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [84, 1, [26, 1, []]]]], "character"]], [30, 6, ["we got sent back to main gallery page -- page links exist", 8, [27, 7, [[26, 1, [[62, 2, [0, "div", {"id": "paginator"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 2, "class", [84, 1, [26, 1, []]]]], [true, [51, 1, [3, "", null, null, "pagination"]]]]]]]''' ) )
    
    return script_info
    
def GetDefaultShortcuts():
    
    from hydrus.client.gui import ClientGUIShortcuts
    
    shortcuts = []
    
    global_shortcuts = ClientGUIShortcuts.ShortcutSet( 'global' )
    
    global_shortcuts.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'G' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_GLOBAL_AUDIO_MUTE_FLIP ) )
    
    shortcuts.append( global_shortcuts )
    
    archive_delete_filter = ClientGUIShortcuts.ShortcutSet( 'archive_delete_filter' )
    
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_KEEP ) )
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_DOUBLE_CLICK, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_KEEP ) )
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_DELETE ) )
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_MIDDLE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_BACK ) )
    
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_SPACE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_KEEP ) )
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F7, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_KEEP ) )
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_DELETE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_DELETE ) )
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_BACKSPACE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_BACK ) )
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_SKIP ) )
    
    shortcuts.append( archive_delete_filter )
    
    duplicate_filter = ClientGUIShortcuts.ShortcutSet( 'duplicate_filter' )
    
    duplicate_filter.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_AND_DELETE_OTHER ) )
    duplicate_filter.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_DOUBLE_CLICK, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_AND_DELETE_OTHER ) )
    duplicate_filter.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_ALTERNATES ) )
    duplicate_filter.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_MIDDLE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_BACK ) )
    
    duplicate_filter.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_SPACE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_AND_DELETE_OTHER ) )
    duplicate_filter.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_SKIP ) )
    
    shortcuts.append( duplicate_filter )
    
    media = ClientGUIShortcuts.ShortcutSet( 'media' )
    
    delete_command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DELETE_FILE )
    undelete_command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_UNDELETE_FILE )
    
    for delete_key in ClientGUIShortcuts.DELETE_KEYS_HYDRUS:
        
        shortcut = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, delete_key, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] )
        
        if media.GetCommand( shortcut ) is None:
            
            media.SetCommand( shortcut, delete_command )
            
        
        shortcut = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, delete_key, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] )
        
        if media.GetCommand( shortcut ) is None:
            
            media.SetCommand( shortcut, undelete_command )
            
        
    
    media.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F4, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MANAGE_FILE_RATINGS ) )
    media.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F3, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MANAGE_FILE_TAGS ) )
    
    media.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F7, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_FILE ) )
    media.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F7, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_INBOX_FILE ) )
    
    media.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'E' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM ) )
    
    media.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'R' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_REMOVE_FILE_FROM_VIEW ) )
    
    media.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F12, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_LAUNCH_THE_ARCHIVE_DELETE_FILTER ) )
    
    media.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'C' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILE ) )
    
    shortcuts.append( media )
    
    tags_autocomplete = ClientGUIShortcuts.ShortcutSet( 'tags_autocomplete' )
    
    tags_autocomplete.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_SPACE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_FORCE_FETCH ) )
    tags_autocomplete.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_INSERT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_IME_MODE ) )
    
    tags_autocomplete.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_TAB_LEFT ) )
    tags_autocomplete.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_TAB_RIGHT ) )
    tags_autocomplete.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_PAGE_LEFT ) )
    tags_autocomplete.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_PAGE_RIGHT ) )
    tags_autocomplete.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_PAGE_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_MEDIA_PREVIOUS ) )
    tags_autocomplete.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_PAGE_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_MEDIA_NEXT ) )
    
    tags_autocomplete.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'I' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SYNCHRONISED_WAIT_SWITCH ) )
    
    shortcuts.append( tags_autocomplete )
    
    main_gui = ClientGUIShortcuts.ShortcutSet( 'main_gui' )
    
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F5, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_REFRESH ) )
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F9, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_PAGE ) )
    
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'M' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SET_MEDIA_FOCUS ) )
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'R' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL, ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SHOW_HIDE_SPLITTERS ) )
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'S' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SET_SEARCH_FOCUS ) )
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'T' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_PAGE ) )
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'U' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_UNCLOSE_PAGE ) )    
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'W' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_CLOSE_PAGE ) )
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'Y' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_REDO ) )
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'Z' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_UNDO ) )
    
    shortcuts.append( main_gui )
    
    media_viewer_browser = ClientGUIShortcuts.ShortcutSet( 'media_viewer_browser' )
    
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_PREVIOUS ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_PREVIOUS ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_PAGE_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_PREVIOUS ) )
    
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_RELEASE, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SHOW_MENU ) )
    
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_SCROLL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_PREVIOUS ) )
    
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_NEXT ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_NEXT ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_PAGE_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_NEXT ) )
    
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_SCROLL_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_NEXT ) )
    
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_HOME, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_FIRST ) )
    
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_END, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_LAST ) )
    
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_DOUBLE_CLICK, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_CLOSE_MEDIA_VIEWER ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_MIDDLE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_CLOSE_MEDIA_VIEWER ) )
    
    shortcuts.append( media_viewer_browser )
    
    media_viewer = ClientGUIShortcuts.ShortcutSet( 'media_viewer' )
    
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_SPACE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAUSE_PLAY_MEDIA ) )
    
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MEDIA_SEEK_DELTA, simple_data = ( -1, 2500 ) ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MEDIA_SEEK_DELTA, simple_data = ( 1, 5000 ) ) )
    
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'B' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_ANIMATION_TO_PREVIOUS_FRAME ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'N' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_ANIMATION_TO_NEXT_FRAME ) )
    
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'F' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SWITCH_BETWEEN_FULLSCREEN_BORDERLESS_AND_REGULAR_FRAMED_WINDOW ) )
    
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'Z' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( '+' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ZOOM_IN ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( '-' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ZOOM_OUT ) )
    
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_SCROLL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ZOOM_IN ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_SCROLL_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ZOOM_OUT ) )
    
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAN_UP ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAN_DOWN ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAN_LEFT ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAN_RIGHT ) )
    
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_ENTER, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_CLOSE_MEDIA_VIEWER ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_ENTER, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_KEYPAD ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_CLOSE_MEDIA_VIEWER ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_RETURN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_CLOSE_MEDIA_VIEWER ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_RETURN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_KEYPAD ] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_CLOSE_MEDIA_VIEWER ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_ESCAPE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_CLOSE_MEDIA_VIEWER ) )
    
    shortcuts.append( media_viewer )
    
    media_viewer_video_audio_player = ClientGUIShortcuts.ShortcutSet( 'media_viewer_media_window' )
    
    media_viewer_video_audio_player.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAUSE_PLAY_MEDIA ) )
    
    shortcuts.append( media_viewer_video_audio_player )
    
    preview_video_audio_player = ClientGUIShortcuts.ShortcutSet( 'preview_media_window' )
    
    preview_video_audio_player.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAUSE_PLAY_MEDIA ) )
    preview_video_audio_player.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_DOUBLE_CLICK, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_LAUNCH_MEDIA_VIEWER ) )
    preview_video_audio_player.SetCommand( ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_MIDDLE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ), CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_LAUNCH_MEDIA_VIEWER ) )
    
    shortcuts.append( preview_video_audio_player )
    
    return shortcuts
    
def GetDefaultSimpleDownloaderFormulae():
    
    dir_path = os.path.join( HC.STATIC_DIR, 'default', 'simple_downloader_formulae' )
    
    from hydrus.client import ClientParsing
    
    return GetDefaultObjectsFromPNGs( dir_path, ( ClientParsing.SimpleDownloaderParsingFormula, ) )
    
def GetDefaultURLClasses():
    
    dir_path = os.path.join( HC.STATIC_DIR, 'default', 'url_classes' )
    
    from hydrus.client.networking import ClientNetworkingDomain
    
    return GetDefaultObjectsFromPNGs( dir_path, ( ClientNetworkingDomain.URLClass, ) )
    
def GetDefaultObjectsFromPNGs( dir_path, allowed_object_types ):
    
    if not os.path.exists( dir_path ):
        
        return []
        
    
    default_objects = []
    
    from hydrus.client import ClientSerialisable
    
    for filename in os.listdir( dir_path ):
        
        path = os.path.join( dir_path, filename )
        
        try:
            
            payload = ClientSerialisable.LoadFromPNG( path )
            
            obj = HydrusSerialisable.CreateFromNetworkBytes( payload )
            
            if isinstance( obj, HydrusSerialisable.SerialisableList ):
                
                objs = obj
                
            else:
                
                objs = [ obj ]
                
            
            for obj in objs:
                
                if isinstance( obj, allowed_object_types ):
                    
                    default_objects.append( obj )
                    
                
            
        except Exception as e:
            
            HydrusData.Print( 'Object at location "{}" failed to load: {}'.format( path, e ) )
            
        
    
    return default_objects
    
def SetDefaultBandwidthManagerRules( bandwidth_manager ):
    
    from hydrus.client.networking import ClientNetworkingContexts
    
    KB = 1024
    MB = KB ** 2
    GB = KB ** 3
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 1, 5 ) # stop accidental spam
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 60, 512 * MB ) # smooth out heavy usage. db and gui prob need a break
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 10 * GB ) # check your inbox lad
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT, rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 1, 1 ) # don't ever hammer a domain
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 2 * GB ) # don't go nuts on a site in a single day
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 512 * MB ) # don't sync a giant db in one day
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 300, 512 * MB ) # just a careful stopgap
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOWNLOADER_PAGE ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    # most gallery downloaders need two rqs per file (page and file), remember
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 86400, 800 ) # catch up on a big sub in little chunks every day
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 768 * MB ) # catch up on a big sub in little chunks every day
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_WATCHER_PAGE ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 60 * 7, 80 )
    
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 4, 1 )
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 2 * GB ) # keep this in there so subs can know better when to stop running (the files come from a subdomain, which causes a pain for bandwidth calcs)
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 64 * MB ) # added as a compromise to try to reduce hydrus sankaku bandwidth usage until their new API and subscription model comes in
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, 'sankakucomplex.com' ), rules )
    
DEFAULT_USER_AGENT = 'Mozilla/5.0 (compatible; Hydrus Client)'

def SetDefaultDomainManagerData( domain_manager ):
    
    network_contexts_to_custom_header_dicts = {}
    
    #
    
    from hydrus.client.networking import ClientNetworkingContexts
    from hydrus.client.networking import ClientNetworkingDomain
    
    custom_header_dict = {}
    
    custom_header_dict[ 'User-Agent' ] = ( DEFAULT_USER_AGENT, ClientNetworkingDomain.VALID_APPROVED, 'This is the default User-Agent identifier for the client for all network connections.' )
    
    network_contexts_to_custom_header_dicts[ ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ] = custom_header_dict
    
    #
    
    custom_header_dict = {}
    
    custom_header_dict[ 'User-Agent' ] = ( 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0', ClientNetworkingDomain.VALID_UNKNOWN, 'Sankaku have unusual User-Agent rules on certain requests. Setting this User-Agent allows the sankaku downloader to work.' )
    
    network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, 'sankakucomplex.com' )
    
    network_contexts_to_custom_header_dicts[ network_context ] = custom_header_dict
    
    #
    
    domain_manager.SetNetworkContextsToCustomHeaderDicts( network_contexts_to_custom_header_dicts )
    
    #
    
    gugs = GetDefaultGUGs()
    
    domain_manager.SetGUGs( gugs )
    
    gug_keys_to_display = [ gug.GetGUGKey() for gug in gugs if 'ugoira' not in gug.GetName() ]
    
    domain_manager.SetGUGKeysToDisplay( gug_keys_to_display )
    
    #
    
    domain_manager.SetURLClasses( GetDefaultURLClasses() )
    
    #
    
    domain_manager.SetParsers( GetDefaultParsers() )
    
    #
    
    domain_manager.TryToLinkURLClassesAndParsers()
    
    #
    
    from hydrus.client.importing.options import TagImportOptions
    
    service_tag_import_options = TagImportOptions.ServiceTagImportOptions( get_tags = True )
    
    service_keys_to_service_tag_import_options = { CC.DEFAULT_LOCAL_DOWNLOADER_TAG_SERVICE_KEY : service_tag_import_options }
    
    tag_import_options = TagImportOptions.TagImportOptions( service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
    
    domain_manager.SetDefaultFilePostTagImportOptions( tag_import_options )
    
def SetDefaultFavouriteSearchManagerData( favourite_search_manager ):
    
    from hydrus.client.media import ClientMedia
    from hydrus.client import ClientSearch
    
    rows = []
    
    #
    
    foldername = 'example search'
    name = 'inbox filter'
    
    location_search_context = ClientSearch.LocationSearchContext( current_service_keys = [ CC.LOCAL_FILE_SERVICE_KEY ] )
    
    tag_search_context = ClientSearch.TagSearchContext()
    
    predicates = []
    
    predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_SYSTEM_INBOX ) )
    predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, value = 256 ) )
    
    filetypes = []
    filetypes.extend( HC.general_mimetypes_to_mime_groups[ HC.GENERAL_IMAGE ] )
    filetypes.extend( HC.general_mimetypes_to_mime_groups[ HC.GENERAL_ANIMATION ] )
    filetypes.extend( HC.general_mimetypes_to_mime_groups[ HC.GENERAL_VIDEO ] )
    
    predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, value = filetypes ) )
    
    file_search_context = ClientSearch.FileSearchContext( location_search_context = location_search_context, tag_search_context = tag_search_context, predicates = predicates )
    
    synchronised = True
    media_sort = ClientMedia.MediaSort( sort_type = ( 'system', CC.SORT_FILES_BY_FILESIZE ), sort_order = CC.SORT_DESC )
    media_collect = None
    
    rows.append( ( foldername, name, file_search_context, synchronised, media_sort, media_collect ) )
    
    #
    
    foldername = None
    name = 'empty page'
    
    location_search_context = ClientSearch.LocationSearchContext( current_service_keys = [ CC.LOCAL_FILE_SERVICE_KEY ] )
    
    tag_search_context = ClientSearch.TagSearchContext()
    
    predicates = []
    
    file_search_context = ClientSearch.FileSearchContext( location_search_context = location_search_context, tag_search_context = tag_search_context, predicates = predicates )
    
    synchronised = True
    media_sort = None
    media_collect = None
    
    rows.append( ( foldername, name, file_search_context, synchronised, media_sort, media_collect ) )
    
    #
    
    favourite_search_manager.SetFavouriteSearchRows( rows )

def SetDefaultLoginManagerScripts( login_manager ):
    
    default_login_scripts = GetDefaultLoginScripts()
    
    login_manager.SetLoginScripts( default_login_scripts )
    
