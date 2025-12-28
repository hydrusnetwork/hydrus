import re
import os

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusStaticDir
from hydrus.core.networking import HydrusNetworking
from hydrus.core import HydrusTime

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation

def GetClientDefaultOptions():
    
    options = {}
    
    options[ 'export_path' ] = None
    options[ 'hpos' ] = 400
    options[ 'vpos' ] = -240
    options[ 'thumbnail_dimensions' ] = [ 150, 125 ]
    options[ 'password' ] = None
    options[ 'default_gui_session' ] = CC.LAST_SESSION_SESSION_NAME
    options[ 'idle_period' ] = 60 * 30
    options[ 'idle_mouse_period' ] = 60 * 10
    options[ 'idle_normal' ] = True
    options[ 'idle_shutdown' ] = CC.IDLE_ON_SHUTDOWN_ASK_FIRST
    options[ 'idle_shutdown_max_minutes' ] = 5
    options[ 'trash_max_age' ] = 72
    options[ 'trash_max_size' ] = 2048
    options[ 'remove_trashed_files' ] = False
    options[ 'remove_filtered_files' ] = False
    options[ 'confirm_trash' ] = True
    options[ 'confirm_archive' ] = True
    options[ 'gallery_file_limit' ] = 2000
    options[ 'delete_to_recycle_bin' ] = True
    options[ 'animation_start_position' ] = 0.0
    options[ 'hide_preview' ] = False
    
    regex_favourites = []
    
    regex_favourites.append( ( r'[1-9]+\d*(?=.{4}$)', HC.UNICODE_ELLIPSIS + r'0074.jpg -> 74' ) )
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
    
    paths = HydrusStaticDir.ListStaticDirFilePaths( os.path.join( 'default', 'gugs' ) )
    
    from hydrus.client.networking import ClientNetworkingGUG
    
    return GetDefaultObjectsFromPNGs( paths, ( ClientNetworkingGUG.GalleryURLGenerator, ClientNetworkingGUG.NestedGalleryURLGenerator ) )
    

def GetDefaultNGUGs():
    
    from hydrus.client.networking import ClientNetworkingGUG
    
    gugs = [ gug for gug in GetDefaultGUGs() if isinstance( gug, ClientNetworkingGUG.NestedGalleryURLGenerator ) ]
    
    return gugs
    

def GetDefaultSingleGUGs():
    
    from hydrus.client.networking import ClientNetworkingGUG
    
    gugs = [ gug for gug in GetDefaultGUGs() if isinstance( gug, ClientNetworkingGUG.GalleryURLGenerator ) ]
    
    return gugs
    

def GetDefaultLoginScripts():
    
    paths = HydrusStaticDir.ListStaticDirFilePaths( os.path.join( 'default', 'login_scripts' ) )
    
    from hydrus.client.networking import ClientNetworkingLogin
    
    return GetDefaultObjectsFromPNGs( paths, ( ClientNetworkingLogin.LoginScriptDomain, ) )
    

def GetDefaultParsers():
    
    paths = HydrusStaticDir.ListStaticDirFilePaths( os.path.join( 'default', 'parsers' ) )
    
    from hydrus.client.parsing import ClientParsing
    
    return GetDefaultObjectsFromPNGs( paths, ( ClientParsing.PageParser, ) )
    

def GetDefaultScriptRows():
    
    script_info = []
    
    script_info.append( ( 32, 'iqdb danbooru', 2, HydrusTime.GetNowMS(), '''["https://danbooru.iqdb.org/", 1, 0, [55, 1, [[], "some hash bytes"]], "file", {}, [[29, 1, ["link to danbooru", [27, 6, [[26, 1, [[62, 2, [0, "td", {"class": "image"}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 0, "href", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], [[30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "section", {"id": "tag-list"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "li", {"class": "tag-type-1"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {"class": "search-tag"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, "creator"]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "section", {"id": "tag-list"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "li", {"class": "tag-type-3"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {"class": "search-tag"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, "series"]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "section", {"id": "tag-list"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "li", {"class": "tag-type-4"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {"class": "search-tag"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, "character"]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "section", {"id": "tag-list"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "li", {"class": "tag-type-0"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {"class": "search-tag"}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, ""]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "section", {"id": "post-information"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "li", {}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [2, "Rating:*", null, null, "Rating: Safe"]], [55, 1, [[[0, 8]], "Rating: Safe"]]]], 0, false, "rating"]], [30, 4, ["", 7, [27, 6, [[26, 1, [[62, 2, [0, "section", {"id": "post-information"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "li", {}, null, null, true, [51, 1, [2, "Source:*", null, null, "Source:"]]]], [62, 2, [0, "a", {}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 0, "href", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, [8, 0]]]]]], [30, 4, ["no iqdb match found", 8, [27, 6, [[26, 1, [[62, 2, [0, "th", {}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, [false, [51, 1, [2, "Best match", null, null, "Best match"]]]]]]]''' ) )
    script_info.append( ( 32, 'danbooru md5', 2, HydrusTime.GetNowMS(), '''["https://danbooru.donmai.us/", 0, 1, [55, 1, [[[4, "hex"]], "some hash bytes"]], "md5", {"page": "post", "s": "list"}, [[30, 4, ["we got sent back to main gallery page -- title test", 8, [27, 6, [[26, 1, [[62, 2, [0, "head", {}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "title", {}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, [true, [51, 1, [2, "Image List", null, null, "Image List"]]]]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-0"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, ""]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-3"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, "series"]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-1"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, "creator"]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-4"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, "character"]], [30, 4, ["we got sent back to main gallery page -- page links exist", 8, [27, 6, [[26, 1, [[62, 2, [0, "div", {}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 0, "class", [51, 1, [3, "", null, null, "example string"]], [55, 1, [[], "parsed information"]]]], 0, false, [true, [51, 1, [2, "pagination", null, null, "pagination"]]]]], [30, 4, ["", 0, [27, 6, [[26, 1, [[62, 2, [0, "section", {"id": "post-information"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "li", {}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "href", [51, 1, [2, "Rating:*", null, null, "Rating: Safe"]], [55, 1, [[[0, 8]], "Rating: Safe"]]]], 0, false, "rating"]]]]''' ) )
    script_info.append( ( 32, 'gelbooru md5', 2, HydrusTime.GetNowMS(), '''["http://gelbooru.com/index.php", 0, 1, [55, 1, [[[4, "hex"]], "some hash bytes"]], "md5", {"s": "list", "page": "post"}, [[30, 6, ["we got sent back to main gallery page -- title test", 8, [27, 7, [[26, 1, [[62, 2, [0, "head", {}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "title", {}, 0, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [84, 1, [26, 1, []]]]], [true, [51, 1, [2, "Image List", null, null, "Image List"]]]]], [30, 6, ["", 0, [27, 7, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-general"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [84, 1, [26, 1, []]]]], ""]], [30, 6, ["", 0, [27, 7, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-copyright"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [84, 1, [26, 1, []]]]], "series"]], [30, 6, ["", 0, [27, 7, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-artist"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [84, 1, [26, 1, []]]]], "creator"]], [30, 6, ["", 0, [27, 7, [[26, 1, [[62, 2, [0, "li", {"class": "tag-type-character"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, 1, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 1, "", [84, 1, [26, 1, []]]]], "character"]], [30, 6, ["we got sent back to main gallery page -- page links exist", 8, [27, 7, [[26, 1, [[62, 2, [0, "div", {"id": "paginator"}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]], [62, 2, [0, "a", {}, null, null, false, [51, 1, [3, "", null, null, "example string"]]]]]], 2, "class", [84, 1, [26, 1, []]]]], [true, [51, 1, [3, "", null, null, "pagination"]]]]]]]''' ) )
    
    return script_info
    

def GetDefaultShortcuts():
    
    from hydrus.client.gui import ClientGUIShortcuts
    
    shortcuts = []
    
    global_shortcuts = ClientGUIShortcuts.ShortcutSet( 'global' )
    
    global_shortcuts.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'G' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_GLOBAL_AUDIO_MUTE_FLIP )
    )
    
    shortcuts.append( global_shortcuts )
    
    archive_delete_filter = ClientGUIShortcuts.ShortcutSet( 'archive_delete_filter' )
    
    archive_delete_filter.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_KEEP )
    )
    archive_delete_filter.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_DOUBLE_CLICK, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_KEEP )
    )
    archive_delete_filter.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_DELETE )
    )
    archive_delete_filter.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_MIDDLE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_BACK )
    )
    
    archive_delete_filter.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F7, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_KEEP )
    )
    archive_delete_filter.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_DELETE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_DELETE )
    )
    archive_delete_filter.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_BACKSPACE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_BACK )
    )
    archive_delete_filter.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_SKIP )
    )
    
    archive_delete_filter.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F12, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_CLOSE_MEDIA_VIEWER )
    )
    
    shortcuts.append( archive_delete_filter )
    
    duplicate_filter = ClientGUIShortcuts.ShortcutSet( 'duplicate_filter' )
    
    duplicate_filter.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_AND_DELETE_OTHER )
    )
    duplicate_filter.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_DOUBLE_CLICK, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_AND_DELETE_OTHER )
    )
    duplicate_filter.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_ALTERNATES )
    )
    duplicate_filter.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_MIDDLE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_BACK )
    )
    
    duplicate_filter.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_SKIP )
    )
    
    shortcuts.append( duplicate_filter )
    
    media = ClientGUIShortcuts.ShortcutSet( 'media' )
    
    delete_command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DELETE_FILE )
    undelete_command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_UNDELETE_FILE )
    
    for delete_key in ClientGUIShortcuts.DELETE_KEYS_HYDRUS:
        
        shortcut =(
            ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, delete_key, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] )
        )
        
        if media.GetCommand( shortcut ) is None:
            
            media.SetCommand( shortcut, delete_command )
            
        
        shortcut =(
            ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, delete_key, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] )
        )
        
        if media.GetCommand( shortcut ) is None:
            
            media.SetCommand( shortcut, undelete_command )
            
        
    
    media.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F4, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MANAGE_FILE_RATINGS )
    )
    media.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F3, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MANAGE_FILE_TAGS )
    )
    
    media.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F7, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_FILE )
    )
    media.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F7, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_INBOX_FILE )
    )
    
    media.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'E' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM )
    )
    
    media.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'R' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_REMOVE_FILE_FROM_VIEW )
    )
    
    media.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'C' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_COPY_FILES, simple_data = CAC.FILE_COMMAND_TARGET_SELECTED_FILES )
    )
    
    shortcuts.append( media )
    
    tags_autocomplete = ClientGUIShortcuts.ShortcutSet( 'tags_autocomplete' )
    
    tags_autocomplete.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_SPACE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_FORCE_FETCH )
    )
    tags_autocomplete.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_INSERT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_IME_MODE )
    )
    
    tags_autocomplete.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_TAB_LEFT )
    )
    tags_autocomplete.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_TAB_RIGHT )
    )
    tags_autocomplete.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_PAGE_LEFT )
    )
    tags_autocomplete.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_PAGE_RIGHT )
    )
    tags_autocomplete.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_PAGE_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_MEDIA_PREVIOUS )
    )
    tags_autocomplete.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_PAGE_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_AUTOCOMPLETE_IF_EMPTY_MEDIA_NEXT )
    )
    
    tags_autocomplete.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'I' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SYNCHRONISED_WAIT_SWITCH )
    )
    
    shortcuts.append( tags_autocomplete )
    
    main_gui = ClientGUIShortcuts.ShortcutSet( 'main_gui' )
    
    main_gui.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F5, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_REFRESH )
    )
    main_gui.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F9, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_PAGE )
    )
    
    main_gui.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'M' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SET_MEDIA_FOCUS )
    )
    main_gui.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'R' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL, ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SHOW_HIDE_SPLITTERS )
    )
    main_gui.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'S' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SET_SEARCH_FOCUS )
    )
    main_gui.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'T' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_NEW_PAGE )
    )
    main_gui.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'U' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_UNCLOSE_PAGE )
    )    
    main_gui.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'W' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_CLOSE_PAGE )
    )
    main_gui.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'Y' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_REDO )
    )
    main_gui.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'Z' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_UNDO )
    )
    main_gui.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'P' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_COMMAND_PALETTE )
    )
    
    main_gui.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'O' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL, ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_OPTIONS )
    )
    
    main_gui.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_PAGE_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_PAGES_SELECTION_LEFT )
    )
    main_gui.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_PAGE_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_PAGES_SELECTION_RIGHT )
    )
    
    shortcuts.append( main_gui )
    
    media_viewer_browser = ClientGUIShortcuts.ShortcutSet( 'media_viewer_browser' )
    
    media_viewer_browser.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_PREVIOUS )
    )
    media_viewer_browser.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_PREVIOUS )
    )
    media_viewer_browser.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_PAGE_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_PREVIOUS )
    )
    
    media_viewer_browser.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_RELEASE, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SHOW_MENU )
    )
    
    media_viewer_browser.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_SCROLL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_PREVIOUS )
    )
    
    media_viewer_browser.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_NEXT )
    )
    media_viewer_browser.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_NEXT )
    )
    media_viewer_browser.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_PAGE_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_NEXT )
    )
    
    media_viewer_browser.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_SCROLL_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_NEXT )
    )
    
    media_viewer_browser.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_HOME, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_FIRST )
    )
    
    media_viewer_browser.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_END, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_LAST )
    )
    
    media_viewer_browser.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_DOUBLE_CLICK, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_CLOSE_MEDIA_VIEWER )
    )
    media_viewer_browser.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_MIDDLE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_CLOSE_MEDIA_VIEWER )
    )
    
    shortcuts.append( media_viewer_browser )
    
    media_viewer = ClientGUIShortcuts.ShortcutSet( 'media_viewer' )
    
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_SPACE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAUSE_PLAY_MEDIA )
    )
    
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MEDIA_SEEK_DELTA, simple_data = ( -1, 2500 ) )
    )
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MEDIA_SEEK_DELTA, simple_data = ( 1, 5000 ) )
    )
    
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'B' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_ANIMATION_TO_PREVIOUS_FRAME )
    )
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'N' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_ANIMATION_TO_NEXT_FRAME )
    )
    
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'F' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SWITCH_BETWEEN_FULLSCREEN_BORDERLESS_AND_REGULAR_FRAMED_WINDOW )
    )
    
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'Z' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM )
    )
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( '+' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ZOOM_IN )
    )
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( '-' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ZOOM_OUT )
    )
    
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_SCROLL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ZOOM_IN )
    )
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_SCROLL_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ZOOM_OUT )
    )
    
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAN_UP )
    )
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAN_DOWN )
    )
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAN_LEFT )
    )
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAN_RIGHT )
    )
    
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_ENTER, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_CLOSE_MEDIA_VIEWER )
    )
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_RETURN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_CLOSE_MEDIA_VIEWER )
    )
    media_viewer.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_ESCAPE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_CLOSE_MEDIA_VIEWER )
    )
    
    shortcuts.append( media_viewer )
    
    media_viewer_video_audio_player = ClientGUIShortcuts.ShortcutSet( 'media_viewer_media_window' )
    
    media_viewer_video_audio_player.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAUSE_PLAY_MEDIA )
    )
    
    shortcuts.append( media_viewer_video_audio_player )
    
    preview_video_audio_player = ClientGUIShortcuts.ShortcutSet( 'preview_media_window' )
    
    preview_video_audio_player.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAUSE_PLAY_MEDIA )
    )
    preview_video_audio_player.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_DOUBLE_CLICK, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_LAUNCH_MEDIA_VIEWER )
    )
    preview_video_audio_player.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_MIDDLE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_LAUNCH_MEDIA_VIEWER )
    )
    
    shortcuts.append( preview_video_audio_player )
    
    thumbnails = ClientGUIShortcuts.ShortcutSet( 'thumbnails' )
    
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_ENTER, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_LAUNCH_MEDIA_VIEWER )
    )
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_RETURN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_LAUNCH_MEDIA_VIEWER )
    )
    
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_F12, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_LAUNCH_THE_ARCHIVE_DELETE_FILTER )
    )
    
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_HOME, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_HOME, CAC.SELECTION_STATUS_NORMAL ) )
    )
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_HOME, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_HOME, CAC.SELECTION_STATUS_SHIFT ) )
    )
    
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_END, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_END, CAC.SELECTION_STATUS_NORMAL ) )
    )
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_END, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_END, CAC.SELECTION_STATUS_SHIFT ) )
    )
    
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_LEFT, CAC.SELECTION_STATUS_NORMAL ) )
    )
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_LEFT, CAC.SELECTION_STATUS_SHIFT ) )
    )
    
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_RIGHT, CAC.SELECTION_STATUS_NORMAL ) )
    )
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_RIGHT, CAC.SELECTION_STATUS_SHIFT ) )
    )
    
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_UP, CAC.SELECTION_STATUS_NORMAL ) )
    )
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_UP, CAC.SELECTION_STATUS_SHIFT ) )
    )
    
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_DOWN, CAC.SELECTION_STATUS_NORMAL ) )
    )
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_DOWN, CAC.SELECTION_STATUS_SHIFT ) )
    )
    
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_PAGE_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_PAGE_UP, CAC.SELECTION_STATUS_NORMAL ) )
    )
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_PAGE_UP, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_PAGE_UP, CAC.SELECTION_STATUS_SHIFT ) )
    )
    
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_PAGE_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_PAGE_DOWN, CAC.SELECTION_STATUS_NORMAL ) )
    )
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_PAGE_DOWN, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS, simple_data = ( CAC.MOVE_PAGE_DOWN, CAC.SELECTION_STATUS_SHIFT ) )
    )
    
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_HOME, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_ALT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_REARRANGE_THUMBNAILS, ( CAC.REARRANGE_THUMBNAILS_TYPE_COMMAND, CAC.MOVE_HOME ) )
    )
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_END, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_ALT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_REARRANGE_THUMBNAILS, ( CAC.REARRANGE_THUMBNAILS_TYPE_COMMAND, CAC.MOVE_END ) )
    )
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_ALT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_REARRANGE_THUMBNAILS, ( CAC.REARRANGE_THUMBNAILS_TYPE_COMMAND, CAC.MOVE_LEFT ) )
    )
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_RIGHT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_ALT ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_REARRANGE_THUMBNAILS, ( CAC.REARRANGE_THUMBNAILS_TYPE_COMMAND, CAC.MOVE_RIGHT ) )
    )
    
    from hydrus.client.media import ClientMediaFileFilter
    
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_CHARACTER, ord( 'A' ), ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [ ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL ] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SELECT_FILES, simple_data = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_ALL ) )
    )
    thumbnails.SetCommand(
        ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_ESCAPE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
        CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SELECT_FILES, simple_data = ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_NONE ) )
    )
    
    if HC.PLATFORM_MACOS:
        
        thumbnails.SetCommand(
            ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_KEYBOARD_SPECIAL, ClientGUIShortcuts.SHORTCUT_KEY_SPECIAL_SPACE, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] ),
            CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_MAC_QUICKLOOK )
        )
        
    
    shortcuts.append( thumbnails )
    
    return shortcuts
    

def GetDefaultSimpleDownloaderFormulae():
    
    paths = HydrusStaticDir.ListStaticDirFilePaths( os.path.join( 'default', 'simple_downloader_formulae' ) )
    
    from hydrus.client.parsing import ClientParsing
    
    return GetDefaultObjectsFromPNGs( paths, ( ClientParsing.SimpleDownloaderParsingFormula, ) )
    

def GetDefaultURLClasses():
    
    paths = HydrusStaticDir.ListStaticDirFilePaths( os.path.join( 'default', 'url_classes' ) )
    
    from hydrus.client.networking import ClientNetworkingURLClass
    
    return GetDefaultObjectsFromPNGs( paths, ( ClientNetworkingURLClass.URLClass, ) )
    

def GetDefaultObjectsFromPNGs( paths: list[ str ], allowed_object_types ):
    
    default_objects = []
    
    from hydrus.client import ClientSerialisable
    
    for path in paths:
        
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
            
            HydrusData.Print( 'Object at location "{}" failed to load: {}'.format( path, repr( e ) ) )
            
        
    
    return default_objects
    

def SetDefaultBandwidthManagerRules( bandwidth_manager ):
    
    from hydrus.client.networking import ClientNetworkingContexts
    
    KB = 1024
    MB = KB ** 2
    GB = KB ** 3
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 1, 5 ) # stop accidental spam
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 16 * GB ) # check your inbox lad
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT, rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 1, 1 ) # don't ever hammer a domain
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 8 * GB ) # don't go nuts on a site in a single day
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 2 * GB ) # don't sync a giant db in one day, but we can push it more
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 300, 1024 * MB ) # just a careful stopgap
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOWNLOADER_PAGE ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    # most gallery downloaders need two rqs per file (page and file), remember
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 86400, 1000 ) # catch up on a swell of many new things in chunks every day
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 1024 * MB ) # catch up on a stonking bump in chunks every day
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    # watchers have time pressure, so no additional rules beyond global and domain limits
    
    bandwidth_manager.SetRules( ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_WATCHER_PAGE ), rules )
    

DEFAULT_USER_AGENT = 'Mozilla/5.0 (compatible; Hydrus Client)'

def SetDefaultDomainManagerData( domain_manager ):
    
    network_contexts_to_custom_header_dicts = {}
    
    #
    
    from hydrus.client.networking import ClientNetworkingContexts
    from hydrus.client.networking import ClientNetworkingDomain
    
    custom_header_dict = {}
    
    custom_header_dict[ 'User-Agent' ] = ( DEFAULT_USER_AGENT, ClientNetworkingDomain.VALID_APPROVED, 'This is the default User-Agent identifier for the client for all network connections.' )
    custom_header_dict[ 'Accept' ] = ( 'image/jpeg,image/png,image/*;q=0.9,*/*;q=0.8', ClientNetworkingDomain.VALID_APPROVED, 'Prefers jpeg/png over webp, but provides graceful fallback.' )
    custom_header_dict[ 'Cache-Control' ] = ( 'no-transform', ClientNetworkingDomain.VALID_APPROVED, 'Tells CDNs not to deliver "optimised" versions of files. May not be honoured.' )
    
    network_contexts_to_custom_header_dicts[ ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ] = custom_header_dict
    
    custom_header_dict = {}
    
    custom_header_dict[ 'Accept-Language' ] = ( 'en-US,en;q=0.5', ClientNetworkingDomain.VALID_APPROVED, 'Tells Pixiv to give English tag translations.' )
    
    network_contexts_to_custom_header_dicts[ ClientNetworkingContexts.NetworkContext.STATICGenerateForDomain( 'pixiv.net' ) ] = custom_header_dict
    
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
    from hydrus.client.search import ClientSearchFileSearchContext
    from hydrus.client.search import ClientSearchPredicate
    from hydrus.client.search import ClientSearchTagContext
    
    rows = []
    
    #
    
    foldername = 'example search'
    name = 'inbox filter'
    
    location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
    
    tag_context = ClientSearchTagContext.TagContext()
    
    predicates = []
    
    predicates.append( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_INBOX ) )
    predicates.append( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LIMIT, value = 256 ) )
    
    filetypes = []
    filetypes.extend( HC.general_mimetypes_to_mime_groups[ HC.GENERAL_IMAGE ] )
    filetypes.extend( HC.general_mimetypes_to_mime_groups[ HC.GENERAL_ANIMATION ] )
    filetypes.extend( HC.general_mimetypes_to_mime_groups[ HC.GENERAL_VIDEO ] )
    
    predicates.append( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = filetypes ) )
    
    file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, tag_context = tag_context, predicates = predicates )
    
    synchronised = True
    media_sort = ClientMedia.MediaSort( sort_type = ( 'system', CC.SORT_FILES_BY_FILESIZE ), sort_order = CC.SORT_DESC )
    media_collect = None
    
    rows.append( ( foldername, name, file_search_context, synchronised, media_sort, media_collect ) )
    
    #
    
    favourite_search_manager.SetFavouriteSearchRows( rows )
    

def SetDefaultLoginManagerScripts( login_manager ):
    
    default_login_scripts = GetDefaultLoginScripts()
    
    login_manager.SetLoginScripts( default_login_scripts, auto_link = True )
    
