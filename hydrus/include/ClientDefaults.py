from . import ClientConstants as CC
from . import ClientData
from . import HydrusConstants as HC
from . import HydrusGlobals as HG
from . import HydrusNetworking
from . import HydrusSerialisable
import re
import os
import wx

def GetClientDefaultOptions():
    
    options = {}
    
    options[ 'play_dumper_noises' ] = True
    options[ 'default_collect' ] = []
    options[ 'export_path' ] = None
    options[ 'hpos' ] = 400
    options[ 'vpos' ] = 700
    options[ 'thumbnail_cache_size' ] = 25 * 1048576
    options[ 'preview_cache_size' ] = 15 * 1048576
    options[ 'fullscreen_cache_size' ] = 150 * 1048576
    options[ 'thumbnail_dimensions' ] = [ 150, 125 ]
    options[ 'password' ] = None
    options[ 'default_gui_session' ] = 'last session'
    options[ 'idle_period' ] = 60 * 30
    options[ 'idle_mouse_period' ] = 60 * 10
    options[ 'idle_cpu_max' ] = 50
    options[ 'idle_normal' ] = True
    options[ 'idle_shutdown' ] = CC.IDLE_ON_SHUTDOWN_ASK_FIRST
    options[ 'idle_shutdown_max_minutes' ] = 5
    options[ 'maintenance_delete_orphans_period' ] = 86400 * 3
    options[ 'trash_max_age' ] = 72
    options[ 'trash_max_size' ] = 2048
    options[ 'remove_trashed_files' ] = False
    options[ 'remove_filtered_files' ] = False
    options[ 'gallery_file_limit' ] = 2000
    options[ 'always_embed_autocompletes' ] = HC.PLATFORM_LINUX or HC.PLATFORM_OSX
    options[ 'confirm_trash' ] = True
    options[ 'confirm_archive' ] = True
    options[ 'delete_to_recycle_bin' ] = True
    options[ 'animation_start_position' ] = 0.0
    options[ 'hide_preview' ] = False
    
    regex_favourites = []
    
    regex_favourites.append( ( r'[1-9]+\d*(?=.{4}$)', '\u2026' + r'0074.jpg -> 74' ) )
    regex_favourites.append( ( r'[^' + re.escape( os.path.sep ) + r']+(?=\s-)', r'E:\my collection\author name - v4c1p0074.jpg -> author name' ) )
    
    options[ 'regex_favourites' ] = regex_favourites
    
    system_predicates = {}
    
    system_predicates[ 'age' ] = ( '<', 'delta', ( 0, 0, 7, 0 ) )
    system_predicates[ 'duration' ] = ( '>', 0 )
    system_predicates[ 'height' ] = ( '=', 1080 )
    system_predicates[ 'limit' ] = 600
    system_predicates[ 'mime' ] = HC.IMAGES
    system_predicates[ 'num_tags' ] = ( '<', 4 )
    system_predicates[ 'ratio' ] = ( '=', 16, 9 )
    system_predicates[ 'size' ] = ( '<', 200, 1024 )
    system_predicates[ 'width' ] = ( '=', 1920 )
    system_predicates[ 'num_words' ] = ( '<', 30000 )
    system_predicates[ 'num_pixels' ] = ( '\u2248', 2, 1000000 )
    system_predicates[ 'hamming_distance' ] = 5
    
    options[ 'file_system_predicates' ] = system_predicates
    
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
    
    default_sort_by_choices = []
    
    default_sort_by_choices.append( ( 'namespaces', [ 'series', 'creator', 'title', 'volume', 'chapter', 'page' ] ) )
    default_sort_by_choices.append( ( 'namespaces', [ 'creator', 'series', 'title', 'volume', 'chapter', 'page' ] ) )
    
    options[ 'sort_by' ] = default_sort_by_choices
    options[ 'show_all_tags_in_autocomplete' ] = True
    
    options[ 'proxy' ] = None
    
    options[ 'confirm_client_exit' ] = False
    
    options[ 'default_tag_repository' ] = CC.LOCAL_TAG_SERVICE_KEY
    options[ 'default_tag_sort' ] = CC.SORT_BY_LEXICOGRAPHIC_ASC
    
    options[ 'pause_export_folders_sync' ] = False
    options[ 'pause_import_folders_sync' ] = False
    options[ 'pause_repo_sync' ] = False
    options[ 'pause_subs_sync' ] = False
    
    options[ 'rating_dialog_position' ] = ( False, None )
    
    return options
    
def GetDefaultCheckerOptions( name ):
    
    from . import ClientImportOptions
    
    if name == 'thread':
        
        return ClientImportOptions.CheckerOptions( intended_files_per_check = 4, never_faster_than = 300, never_slower_than = 86400, death_file_velocity = ( 1, 3 * 86400 ) )
        
    elif name == 'slow thread':
        
        return ClientImportOptions.CheckerOptions( intended_files_per_check = 1, never_faster_than = 4 * 3600, never_slower_than = 7 * 86400, death_file_velocity = ( 1, 30 * 86400 ) )
        
    elif name == 'artist subscription':
        
        return ClientImportOptions.CheckerOptions( intended_files_per_check = 4, never_faster_than = 86400, never_slower_than = 90 * 86400, death_file_velocity = ( 1, 180 * 86400 ) )
        
    elif name == 'fast tag subscription':
        
        return ClientImportOptions.CheckerOptions( intended_files_per_check = 10, never_faster_than = 43200, never_slower_than = 30 * 86400, death_file_velocity = ( 1, 90 * 86400 ) )
        
    elif name == 'slow tag subscription':
        
        return ClientImportOptions.CheckerOptions( intended_files_per_check = 1, never_faster_than = 7 * 86400, never_slower_than = 180 * 86400, death_file_velocity = ( 1, 360 * 86400 ) )
        
    
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
    
    from . import ClientNetworkingDomain
    
    return GetDefaultObjectsFromPNGs( dir_path, ( ClientNetworkingDomain.GalleryURLGenerator, ClientNetworkingDomain.NestedGalleryURLGenerator ) )
    
def GetDefaultNGUGs():
    
    from . import ClientNetworkingDomain
    
    gugs = [ gug for gug in GetDefaultGUGs() if isinstance( gug, ClientNetworkingDomain.NestedGalleryURLGenerator ) ]
    
    return gugs
    
def GetDefaultSingleGUGs():
    
    from . import ClientNetworkingDomain
    
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
    
    from . import ClientNetworkingLogin
    
    return GetDefaultObjectsFromPNGs( dir_path, ( ClientNetworkingLogin.LoginScriptDomain, ) )
    
def GetDefaultParsers():
    
    dir_path = os.path.join( HC.STATIC_DIR, 'default', 'parsers' )
    
    from . import ClientParsing
    
    return GetDefaultObjectsFromPNGs( dir_path, ( ClientParsing.PageParser, ) )
    
def GetDefaultScriptRows():
    
    from . import HydrusData
    
    script_info = []
    
    script_info.append( ( 32, 'gelbooru md5', 1, HydrusData.GetNow(), '''["http://gelbooru.com/index.php", 0, 1, 1, "md5", {"s": "list", "page": "post"}, [[30, 1, ["we got sent back to main gallery page -- title test", 8, [27, 1, [[["head", {}, 0], ["title", {}, 0]], null]], [true, true, "Image List"]]], [30, 1, ["", 0, [27, 1, [[["li", {"class": "tag-type-general"}, null], ["a", {}, 1]], null]], ""]], [30, 1, ["", 0, [27, 1, [[["li", {"class": "tag-type-copyright"}, null], ["a", {}, 1]], null]], "series"]], [30, 1, ["", 0, [27, 1, [[["li", {"class": "tag-type-artist"}, null], ["a", {}, 1]], null]], "creator"]], [30, 1, ["", 0, [27, 1, [[["li", {"class": "tag-type-character"}, null], ["a", {}, 1]], null]], "character"]], [30, 1, ["we got sent back to main gallery page -- page links exist", 8, [27, 1, [[["div", {}, null]], "class"]], [true, true, "pagination"]]]]]''' ) )
    script_info.append( ( 32, 'iqdb danbooru', 1, HydrusData.GetNow(), '''["http://danbooru.iqdb.org/", 1, 0, 0, "file", {}, [[29, 1, ["link to danbooru", [27, 1, [[["td", {"class": "image"}, 1], ["a", {}, 0]], "href"]], [[30, 1, ["", 0, [27, 1, [[["section", {"id": "tag-list"}, 0], ["li", {"class": "category-1"}, null], ["a", {"class": "search-tag"}, 0]], null]], "creator"]], [30, 1, ["", 0, [27, 1, [[["section", {"id": "tag-list"}, 0], ["li", {"class": "category-3"}, null], ["a", {"class": "search-tag"}, 0]], null]], "series"]], [30, 1, ["", 0, [27, 1, [[["section", {"id": "tag-list"}, 0], ["li", {"class": "category-4"}, null], ["a", {"class": "search-tag"}, 0]], null]], "character"]], [30, 1, ["", 0, [27, 1, [[["section", {"id": "tag-list"}, 0], ["li", {"class": "category-0"}, null], ["a", {"class": "search-tag"}, 0]], null]], ""]]]]], [30, 1, ["no iqdb match found", 8, [27, 1, [[["th", {}, null]], null]], [false, true, "Best match"]]]]]''' ) )
    
    return script_info
    
def GetDefaultShortcuts():
    
    from . import ClientGUIShortcuts
    
    shortcuts = []
    
    archive_delete_filter = ClientGUIShortcuts.ShortcutSet( 'archive_delete_filter' )
    
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_LEFT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_keep' ) )
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_RIGHT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_delete' ) )
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_MIDDLE, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_back' ) )
    
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_SPACE, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_keep' ) )
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F7, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_keep' ) )
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_DELETE, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_delete' ) )
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_DELETE, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_delete' ) )
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_BACK, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_back' ) )
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_UP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_skip' ) )
    archive_delete_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_UP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_skip' ) )
    
    shortcuts.append( archive_delete_filter )
    
    duplicate_filter = ClientGUIShortcuts.ShortcutSet( 'duplicate_filter' )
    
    duplicate_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_LEFT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_this_is_better_and_delete_other' ) )
    duplicate_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_RIGHT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_alternates' ) )
    duplicate_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_MIDDLE, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_back' ) )
    
    duplicate_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_SPACE, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_this_is_better_and_delete_other' ) )
    duplicate_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_UP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_skip' ) )
    duplicate_filter.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_UP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_skip' ) )
    
    shortcuts.append( duplicate_filter )
    
    media = ClientGUIShortcuts.ShortcutSet( 'media' )
    
    media.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F4, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'manage_file_ratings' ) )
    media.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F3, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'manage_file_tags' ) )
    
    media.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F7, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_file' ) )
    media.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F7, [ CC.SHORTCUT_MODIFIER_SHIFT ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'inbox_file' ) )
    
    media.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'E' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'open_file_in_external_program' ) )
    
    media.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'R' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'remove_file_from_view' ) )
    
    media.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F12, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'launch_the_archive_delete_filter' ) )
    
    media.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'C' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'copy_file' ) )
    
    shortcuts.append( media )
    
    main_gui = ClientGUIShortcuts.ShortcutSet( 'main_gui' )
    
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F5, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'refresh' ) )
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F9, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_page' ) )
    
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'I' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'synchronised_wait_switch' ) )
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'M' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'set_media_focus' ) )
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'R' ), [ CC.SHORTCUT_MODIFIER_CTRL, CC.SHORTCUT_MODIFIER_SHIFT ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'show_hide_splitters' ) )
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'S' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'set_search_focus' ) )
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'T' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_page' ) )
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'U' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'unclose_page' ) )    
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'W' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'close_page' ) )
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'Y' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'redo' ) )
    main_gui.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'Z' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'undo' ) )
    
    shortcuts.append( main_gui )
    
    media_viewer_browser = ClientGUIShortcuts.ShortcutSet( 'media_viewer_browser' )
    
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_UP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_previous' ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_LEFT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_previous' ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_UP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_previous' ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_LEFT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_previous' ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_PAGEUP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_previous' ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_PAGEUP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_previous' ) )
    
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_SCROLL_UP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_previous' ) )
    
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_DOWN, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_next' ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_RIGHT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_next' ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_RIGHT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_next' ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_DOWN, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_next' ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_PAGEDOWN, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_next' ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_PAGEDOWN, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_next' ) )
    
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_SCROLL_DOWN, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_next' ) )
    
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_HOME, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_first' ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_HOME, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_first' ) )
    
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_END, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_last' ) )
    media_viewer_browser.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_END, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_last' ) )
    
    shortcuts.append( media_viewer_browser )
    
    media_viewer = ClientGUIShortcuts.ShortcutSet( 'media_viewer' )
    
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'B' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'move_animation_to_previous_frame' ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'N' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'move_animation_to_next_frame' ) )
    
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'F' ), [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'switch_between_fullscreen_borderless_and_regular_framed_window' ) )
    
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'Z' ), [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'switch_between_100_percent_and_canvas_zoom' ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_ADD, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'zoom_in' ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_ADD, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'zoom_in' ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_SUBTRACT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'zoom_out' ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_SUBTRACT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'zoom_out' ) )
    
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_SCROLL_UP, [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'zoom_in' ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_SCROLL_DOWN, [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'zoom_out' ) )
    
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_UP, [ CC.SHORTCUT_MODIFIER_SHIFT ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'pan_up' ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_DOWN, [ CC.SHORTCUT_MODIFIER_SHIFT ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'pan_down' ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_LEFT, [ CC.SHORTCUT_MODIFIER_SHIFT ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'pan_left' ) )
    media_viewer.SetCommand( ClientGUIShortcuts.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_RIGHT, [ CC.SHORTCUT_MODIFIER_SHIFT ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'pan_right' ) )
    
    shortcuts.append( media_viewer )
    
    return shortcuts
    
def GetDefaultSimpleDownloaderFormulae():
    
    dir_path = os.path.join( HC.STATIC_DIR, 'default', 'simple_downloader_formulae' )
    
    from . import ClientParsing
    
    return GetDefaultObjectsFromPNGs( dir_path, ( ClientParsing.SimpleDownloaderParsingFormula, ) )
    
def GetDefaultURLClasses():
    
    dir_path = os.path.join( HC.STATIC_DIR, 'default', 'url_classes' )
    
    from . import ClientNetworkingDomain
    
    return GetDefaultObjectsFromPNGs( dir_path, ( ClientNetworkingDomain.URLClass, ) )
    
def GetDefaultObjectsFromPNGs( dir_path, allowed_object_types ):
    
    if not os.path.exists( dir_path ):
        
        return []
        
    
    default_objects = []
    
    from . import ClientSerialisable
    
    for filename in os.listdir( dir_path ):
        
        path = os.path.join( dir_path, filename )
        
        try:
            
            payload = ClientSerialisable.LoadFromPng( path )
            
            obj = HydrusSerialisable.CreateFromNetworkBytes( payload )
            
            if isinstance( obj, HydrusSerialisable.SerialisableList ):
                
                objs = obj
                
            else:
                
                objs = [ obj ]
                
            
            for obj in objs:
                
                if isinstance( obj, allowed_object_types ):
                    
                    default_objects.append( obj )
                    
                
            
        except:
            
            pass
            
        
    
    return default_objects
    
def SetDefaultBandwidthManagerRules( bandwidth_manager ):
    
    from . import ClientNetworkingContexts
    
    KB = 1024
    MB = 1024 ** 2
    GB = 1024 ** 3
    
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
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 64 * MB ) # don't sync a giant db in one day
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    # most gallery downloaders need two rqs per file (page and file), remember
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 300, 200 ) # after that first sample of small files, take it easy
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 300, 128 * MB ) # after that first sample of big files, take it easy
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOWNLOADER_PAGE ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    # most gallery downloaders need two rqs per file (page and file), remember
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 86400, 400 ) # catch up on a big sub in little chunks every day
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 256 * MB ) # catch up on a big sub in little chunks every day
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 300, 100 ) # after that first sample of small files, take it easy
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 300, 128 * MB ) # after that first sample of big files, take it easy
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_WATCHER_PAGE ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 60 * 7, 80 )
    
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 4, 1 )
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 2 * GB ) # keep this in there so subs can know better when to stop running (the files come from a subdomain, which causes a pain for bandwidth calcs)
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 64 * MB ) # added as a compromise to try to reduce hydrus sankaku bandwidth usage until their new API and subscription model comes in
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, 'sankakucomplex.com' ), rules )
    
def SetDefaultDomainManagerData( domain_manager ):
    
    network_contexts_to_custom_header_dicts = {}
    
    #
    
    from . import ClientNetworkingContexts
    from . import ClientNetworkingDomain
    
    custom_header_dict = {}
    
    custom_header_dict[ 'User-Agent' ] = ( 'Mozilla/5.0 (compatible; Hydrus Client)', ClientNetworkingDomain.VALID_APPROVED, 'This is the default User-Agent identifier for the client for all network connections.' )
    
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
    
def SetDefaultLoginManagerScripts( login_manager ):
    
    default_login_scripts = GetDefaultLoginScripts()
    
    login_manager.SetLoginScripts( default_login_scripts )
    
