import ClientConstants as CC
import ClientData
import HydrusConstants as HC
import HydrusGlobals as HG
import HydrusNetworking
import os
import wx

def SetDefaultBandwidthManagerRules( bandwidth_manager ):
    
    import ClientNetworking
    
    KB = 1024
    MB = 1024 ** 2
    GB = 1024 ** 3
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 1, 5 ) # stop accidental spam
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 60, 120 ) # smooth out heavy usage/bugspam. db and gui prob need a break
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 10 * GB ) # check your inbox lad
    
    bandwidth_manager.SetRules( ClientNetworking.GLOBAL_NETWORK_CONTEXT, rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 1, 1 ) # don't ever hammer a domain
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 2 * GB ) # don't go nuts on a site in a single day
    
    bandwidth_manager.SetRules( ClientNetworking.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 64 * MB ) # don't sync a giant db in one day
    
    bandwidth_manager.SetRules( ClientNetworking.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    bandwidth_manager.SetRules( ClientNetworking.NetworkContext( CC.NETWORK_CONTEXT_DOWNLOADER ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    # most gallery downloaders need two rqs per file (page and file), remember
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 300, 200 ) # after that first sample of small files, take it easy
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 300, 128 * MB ) # after that first sample of big files, take it easy
    
    bandwidth_manager.SetRules( ClientNetworking.NetworkContext( CC.NETWORK_CONTEXT_DOWNLOADER_QUERY ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    # most gallery downloaders need two rqs per file (page and file), remember
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 86400, 400 ) # catch up on a big sub in little chunks every day
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 86400, 256 * MB ) # catch up on a big sub in little chunks every day
    
    bandwidth_manager.SetRules( ClientNetworking.NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 300, 100 ) # after that first sample of small files, take it easy
    
    rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 300, 128 * MB ) # after that first sample of big files, take it easy
    
    bandwidth_manager.SetRules( ClientNetworking.NetworkContext( CC.NETWORK_CONTEXT_THREAD_WATCHER_THREAD ), rules )
    
    #
    
    rules = HydrusNetworking.BandwidthRules()
    
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 60 * 7, 80 )
    
    rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 4, 1 )
    
    bandwidth_manager.SetRules( ClientNetworking.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, 'sankakucomplex.com' ), rules )
    
def SetDefaultDomainManagerData( domain_manager ):
    
    network_contexts_to_custom_header_dicts = {}
    
    #
    
    import ClientNetworking
    import ClientNetworkingDomain
    
    custom_header_dict = {}
    
    custom_header_dict[ 'User-Agent' ] = ( 'hydrus client', ClientNetworkingDomain.VALID_APPROVED, 'This is the default User-Agent identifier for the client for all network connections.' )
    
    network_contexts_to_custom_header_dicts[ ClientNetworking.GLOBAL_NETWORK_CONTEXT ] = custom_header_dict
    
    #
    
    custom_header_dict = {}
    
    custom_header_dict[ 'User-Agent' ] = ( 'SCChannelApp/2.0.1 (Android; black)', ClientNetworkingDomain.VALID_UNKNOWN, 'Sankaku seem to currently have a User-Agent whitelist on file requests. Setting this User-Agent allows the sankaku downloader to work.' )
    
    network_context = ClientNetworking.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, 'sankakucomplex.com' )
    
    network_contexts_to_custom_header_dicts[ network_context ] = custom_header_dict
    
    #
    
    domain_manager.SetNetworkContextsToCustomHeaderDicts( network_contexts_to_custom_header_dicts )
    
    #
    
    domain_manager.SetURLMatches( GetDefaultURLMatches() )
    
def GetClientDefaultOptions():
    
    options = {}
    
    options[ 'play_dumper_noises' ] = True
    options[ 'default_collect' ] = None
    options[ 'export_path' ] = None
    options[ 'hpos' ] = 400
    options[ 'vpos' ] = 700
    options[ 'thumbnail_cache_size' ] = 25 * 1048576
    options[ 'preview_cache_size' ] = 15 * 1048576
    options[ 'fullscreen_cache_size' ] = 150 * 1048576
    options[ 'thumbnail_dimensions' ] = [ 150, 125 ]
    options[ 'password' ] = None
    options[ 'num_autocomplete_chars' ] = 2
    options[ 'default_gui_session' ] = 'last session'
    options[ 'fetch_ac_results_automatically' ] = True
    options[ 'ac_timings' ] = ( 3, 500, 250 )
    options[ 'thread_checker_timings' ] = ( 3, 1200 )
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
    options[ 'external_host' ] = None
    options[ 'gallery_file_limit' ] = 200
    options[ 'always_embed_autocompletes' ] = HC.PLATFORM_LINUX or HC.PLATFORM_OSX
    options[ 'confirm_trash' ] = True
    options[ 'confirm_archive' ] = True
    options[ 'delete_to_recycle_bin' ] = True
    options[ 'animation_start_position' ] = 0.0
    options[ 'hide_preview' ] = False
    
    regex_favourites = []
    
    regex_favourites.append( ( r'[1-9]+\d*(?=.{4}$)', u'\u2026' + r'0074.jpg -> 74' ) )
    regex_favourites.append( ( r'[^' + os.path.sep.encode( 'string_escape' ) + r']+(?=\s-)', r'E:\my collection\author name - v4c1p0074.jpg -> author name' ) )
    
    options[ 'regex_favourites' ] = regex_favourites
    
    system_predicates = {}
    
    system_predicates[ 'age' ] = ( '<', 0, 0, 7, 0 )
    system_predicates[ 'duration' ] = ( '>', 0 )
    system_predicates[ 'height' ] = ( '=', 1080 )
    system_predicates[ 'limit' ] = 600
    system_predicates[ 'mime' ] = HC.IMAGES
    system_predicates[ 'num_tags' ] = ( '<', 4 )
    system_predicates[ 'ratio' ] = ( '=', 16, 9 )
    system_predicates[ 'size' ] = ( '<', 200, 1024 )
    system_predicates[ 'width' ] = ( '=', 1920 )
    system_predicates[ 'num_words' ] = ( '<', 30000 )
    system_predicates[ 'num_pixels' ] = ( u'\u2248', 2, 1000000 )
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
    
def GetDefaultNamespacesAndSearchValue( gallery_identifier ):
    
    site_type = gallery_identifier.GetSiteType()
    
    if site_type == HC.SITE_TYPE_DEFAULT:
        
        namespaces = [ 'all namespaces' ]
        
        search_value = ''
        
    elif site_type == HC.SITE_TYPE_BOORU:
        
        name = gallery_identifier.GetAdditionalInfo()
        
        if name is None:
            
            namespaces = [ 'all namespaces' ]
            
        else:
            
            try:
                
                booru = HG.client_controller.Read( 'remote_booru', name )
                
                namespaces = booru.GetNamespaces()
                
            except:
                
                namespaces = []
                
            
        
        search_value = 'search tags'
        
    elif site_type == HC.SITE_TYPE_DEVIANT_ART:
        
        namespaces = [ 'creator', 'title' ]
        search_value = 'artist username'
        
    elif site_type == HC.SITE_TYPE_GIPHY:
        
        namespaces = [ '' ]
        
        search_value = 'search tag'
        
    elif site_type in ( HC.SITE_TYPE_HENTAI_FOUNDRY, HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST, HC.SITE_TYPE_HENTAI_FOUNDRY_TAGS ):
        
        namespaces = [ 'creator', 'title' ]
        
        if site_type == HC.SITE_TYPE_HENTAI_FOUNDRY:
            
            search_value = 'search'
            
        elif site_type == HC.SITE_TYPE_HENTAI_FOUNDRY_ARTIST:
            
            search_value = 'artist username'
            
        elif site_type == HC.SITE_TYPE_HENTAI_FOUNDRY_TAGS:
            
            search_value = 'search tags'
            
        
    elif site_type == HC.SITE_TYPE_NEWGROUNDS:
        
        namespaces = [ 'creator', 'title', '' ]
        search_value = 'artist username'
        
    elif site_type in ( HC.SITE_TYPE_PIXIV, HC.SITE_TYPE_PIXIV_ARTIST_ID, HC.SITE_TYPE_PIXIV_TAG ):
        
        namespaces = [ 'creator', 'title', '' ]
        
        if site_type == HC.SITE_TYPE_PIXIV:
            
            search_value = 'search'
            
        elif site_type == HC.SITE_TYPE_PIXIV_ARTIST_ID:
            
            search_value = 'numerical artist id'
            
        elif site_type == HC.SITE_TYPE_PIXIV_TAG:
            
            search_value = 'search tag'
            
        
    elif site_type == HC.SITE_TYPE_TUMBLR:
        
        namespaces = [ '' ]
        search_value = 'username'
        
    elif site_type == HC.SITE_TYPE_THREAD_WATCHER:
        
        namespaces = [ 'filename' ]
        search_value = 'thread url'
        
    
    return ( namespaces, search_value )
    
def GetDefaultBoorus():
    
    boorus = {}
    
    name = 'gelbooru'
    search_url = 'https://gelbooru.com/index.php?page=post&s=list&tags=%tags%&pid=%index%'
    search_separator = '+'
    advance_by_page_num = False
    thumb_classname = 'thumb'
    image_id = None
    image_data = 'Original image'
    tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }
    
    boorus[ 'gelbooru' ] = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
    
    name = 'safebooru'
    search_url = 'https://safebooru.org/index.php?page=post&s=list&tags=%tags%&pid=%index%'
    search_separator = '+'
    advance_by_page_num = False
    thumb_classname = 'thumb'
    image_id = None
    image_data = 'Original image'
    tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }
    
    boorus[ 'safebooru' ] = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
    
    name = 'e621'
    search_url = 'https://e621.net/post/index/%index%/%tags%'
    search_separator = '%20'
    advance_by_page_num = True
    thumb_classname = 'thumb'
    image_id = None
    image_data = 'Download'
    tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator', 'tag-type-species' : 'species' }
    
    boorus[ 'e621' ] = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
    
    name = 'rule34@paheal'
    search_url = 'https://rule34.paheal.net/post/list/%tags%/%index%'
    search_separator = '%20'
    advance_by_page_num = True
    thumb_classname = 'thumb'
    image_id = 'main_image'
    image_data = None
    tag_classnames_to_namespaces = { 'tag_name' : '' }
    
    boorus[ 'rule34@paheal' ] = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
    
    name = 'danbooru'
    search_url = 'https://danbooru.donmai.us/posts?page=%index%&tags=%tags%'
    search_separator = '%20'
    advance_by_page_num = True
    thumb_classname = 'post-preview'
    image_id = 'image'
    image_data = None
    tag_classnames_to_namespaces = { 'category-0' : '', 'category-4' : 'character', 'category-3' : 'series', 'category-1' : 'creator' }
    
    boorus[ 'danbooru' ] = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
    
    name = 'mishimmie'
    search_url = 'https://shimmie.katawa-shoujo.com/post/list/%tags%/%index%'
    search_separator = '%20'
    advance_by_page_num = True
    thumb_classname = 'thumb'
    image_id = 'main_image'
    image_data = None
    tag_classnames_to_namespaces = { 'tag_name' : '' }
    
    boorus[ 'mishimmie' ] = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
    
    name = 'rule34@booru.org'
    search_url = 'https://rule34.xxx/index.php?page=post&s=list&tags=%tags%&pid=%index%'
    search_separator = '%20'
    advance_by_page_num = False
    thumb_classname = 'thumb'
    image_id = None
    image_data = 'Original image'
    tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }
    
    boorus[ 'rule34@booru.org' ] = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
    
    name = 'furry@booru.org'
    search_url = 'http://furry.booru.org/index.php?page=post&s=list&tags=%tags%&pid=%index%'
    search_separator = '+'
    advance_by_page_num = False
    thumb_classname = 'thumb'
    image_id = None
    image_data = 'Original image'
    tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }
    
    boorus[ 'furry@booru.org' ] = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
    
    name = 'xbooru'
    search_url = 'http://xbooru.com/index.php?page=post&s=list&tags=%tags%&pid=%index%'
    search_separator = '+'
    advance_by_page_num = False
    thumb_classname = 'thumb'
    image_id = None
    image_data = 'Original image'
    tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }
    
    boorus[ 'xbooru' ] = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
    
    name = 'konachan'
    search_url = 'https://konachan.com/post?page=%index%&tags=%tags%'
    search_separator = '+'
    advance_by_page_num = True
    thumb_classname = 'thumb'
    image_id = None
    image_data = 'View larger version'
    tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }
    
    boorus[ 'konachan' ] = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
    
    name = 'yande.re'
    search_url = 'https://yande.re/post?page=%index%&tags=%tags%'
    search_separator = '+'
    advance_by_page_num = True
    thumb_classname = 'thumb'
    image_id = None
    image_data = 'View larger version'
    tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }
    
    boorus[ 'yande.re' ] = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
    
    name = 'tbib'
    search_url = 'https://tbib.org/index.php?page=post&s=list&tags=%tags%&pid=%index%'
    search_separator = '+'
    advance_by_page_num = False
    thumb_classname = 'thumb'
    image_id = None
    image_data = 'Original image'
    tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator' }
    
    boorus[ 'tbib' ] = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
    
    name = 'sankaku chan'
    search_url = 'https://chan.sankakucomplex.com/?tags=%tags%&page=%index%'
    search_separator = '+'
    advance_by_page_num = True
    thumb_classname = 'thumb'
    image_id = 'highres'
    image_data = None
    tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator', 'tag-type-medium' : 'medium', 'tag-type-meta' : 'meta', 'tag-type-studio' : 'studio' }
    
    boorus[ 'sankaku chan' ] = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
    
    name = 'sankaku idol'
    search_url = 'https://idol.sankakucomplex.com/?tags=%tags%&page=%index%'
    search_separator = '+'
    advance_by_page_num = True
    thumb_classname = 'thumb'
    image_id = 'highres'
    image_data = None
    tag_classnames_to_namespaces = { 'tag-type-general' : '', 'tag-type-character' : 'character', 'tag-type-copyright' : 'series', 'tag-type-artist' : 'creator', 'tag-type-medium' : 'medium', 'tag-type-meta' : 'meta', 'tag-type-photo_set' : 'photo set', 'tag-type-idol' : 'person' }
    
    boorus[ 'sankaku idol' ] = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
    
    name = 'rule34hentai'
    search_url = 'https://rule34hentai.net/post/list/%tags%/%index%'
    search_separator = '%20'
    advance_by_page_num = True
    thumb_classname = 'shm-thumb'
    image_id = 'main_image'
    image_data = None
    tag_classnames_to_namespaces = { 'tag_name' : '' }
    
    boorus[ 'rule34hentai' ] = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
    
    return boorus
    
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
    
def GetDefaultScriptRows():
    
    script_info = []
    
    script_info.append( ( 32, 'gelbooru md5', 1, '''["http://gelbooru.com/index.php", 0, 1, 1, "md5", {"s": "list", "page": "post"}, [[30, 1, ["we got sent back to main gallery page -- title test", 8, [27, 1, [[["head", {}, 0], ["title", {}, 0]], null]], [true, true, "Image List"]]], [30, 1, ["", 0, [27, 1, [[["li", {"class": "tag-type-general"}, null], ["a", {}, 1]], null]], ""]], [30, 1, ["", 0, [27, 1, [[["li", {"class": "tag-type-copyright"}, null], ["a", {}, 1]], null]], "series"]], [30, 1, ["", 0, [27, 1, [[["li", {"class": "tag-type-artist"}, null], ["a", {}, 1]], null]], "creator"]], [30, 1, ["", 0, [27, 1, [[["li", {"class": "tag-type-character"}, null], ["a", {}, 1]], null]], "character"]], [30, 1, ["we got sent back to main gallery page -- page links exist", 8, [27, 1, [[["div", {}, null]], "class"]], [true, true, "pagination"]]]]]''' ) )
    script_info.append( ( 32, 'iqdb danbooru', 1, '''["http://danbooru.iqdb.org/", 1, 0, 0, "file", {}, [[29, 1, ["link to danbooru", [27, 1, [[["td", {"class": "image"}, 1], ["a", {}, 0]], "href"]], [[30, 1, ["", 0, [27, 1, [[["section", {"id": "tag-list"}, 0], ["li", {"class": "category-1"}, null], ["a", {"class": "search-tag"}, 0]], null]], "creator"]], [30, 1, ["", 0, [27, 1, [[["section", {"id": "tag-list"}, 0], ["li", {"class": "category-3"}, null], ["a", {"class": "search-tag"}, 0]], null]], "series"]], [30, 1, ["", 0, [27, 1, [[["section", {"id": "tag-list"}, 0], ["li", {"class": "category-4"}, null], ["a", {"class": "search-tag"}, 0]], null]], "character"]], [30, 1, ["", 0, [27, 1, [[["section", {"id": "tag-list"}, 0], ["li", {"class": "category-0"}, null], ["a", {"class": "search-tag"}, 0]], null]], ""]]]]], [30, 1, ["no iqdb match found", 8, [27, 1, [[["th", {}, null]], null]], [false, true, "Best match"]]]]]''' ) )
    
    return script_info
    
def GetDefaultShortcuts():
    
    shortcuts = []
    
    archive_delete_filter = ClientData.Shortcuts( 'archive_delete_filter' )
    
    archive_delete_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_LEFT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_keep' ) )
    archive_delete_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_RIGHT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_delete' ) )
    archive_delete_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_MIDDLE, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_back' ) )
    
    archive_delete_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_SPACE, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_keep' ) )
    archive_delete_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F7, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_keep' ) )
    archive_delete_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_DELETE, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_delete' ) )
    archive_delete_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_DELETE, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_delete' ) )
    archive_delete_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_BACK, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_back' ) )
    archive_delete_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_UP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_skip' ) )
    archive_delete_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_UP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_delete_filter_skip' ) )
    
    shortcuts.append( archive_delete_filter )
    
    duplicate_filter = ClientData.Shortcuts( 'duplicate_filter' )
    
    duplicate_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_LEFT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_this_is_better' ) )
    duplicate_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_RIGHT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_alternates' ) )
    duplicate_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_MIDDLE, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_back' ) )
    
    duplicate_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_SPACE, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_this_is_better' ) )
    duplicate_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_UP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_skip' ) )
    duplicate_filter.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_UP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_filter_skip' ) )
    
    shortcuts.append( duplicate_filter )
    
    media = ClientData.Shortcuts( 'media' )
    
    media.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F4, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'manage_file_ratings' ) )
    media.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F3, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'manage_file_tags' ) )
    
    media.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F7, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'archive_file' ) )
    media.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F7, [ CC.SHORTCUT_MODIFIER_SHIFT ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'inbox_file' ) )
    
    media.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'E' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'open_file_in_external_program' ) )
    
    media.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'R' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'remove_file_from_view' ) )
    
    media.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F12, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'launch_the_archive_delete_filter' ) )
    
    media.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'C' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'copy_file' ) )
    
    shortcuts.append( media )
    
    main_gui = ClientData.Shortcuts( 'main_gui' )
    
    main_gui.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F5, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'refresh' ) )
    main_gui.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F9, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_page' ) )
    
    main_gui.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'I' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'synchronised_wait_switch' ) )
    main_gui.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'M' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'set_media_focus' ) )
    main_gui.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'R' ), [ CC.SHORTCUT_MODIFIER_CTRL, CC.SHORTCUT_MODIFIER_SHIFT ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'show_hide_splitters' ) )
    main_gui.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'S' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'set_search_focus' ) )
    main_gui.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'T' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'new_page' ) )
    main_gui.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'U' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'unclose_page' ) )    
    main_gui.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'W' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'close_page' ) )
    main_gui.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'Y' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'redo' ) )
    main_gui.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'Z' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'undo' ) )
    
    shortcuts.append( main_gui )
    
    media_viewer_browser = ClientData.Shortcuts( 'media_viewer_browser' )
    
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_UP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_previous' ) )
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_LEFT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_previous' ) )
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_UP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_previous' ) )
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_LEFT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_previous' ) )
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_PAGEUP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_previous' ) )
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_PAGEUP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_previous' ) )
    
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_SCROLL_UP, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_previous' ) )
    
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_DOWN, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_next' ) )
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_RIGHT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_next' ) )
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_RIGHT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_next' ) )
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_DOWN, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_next' ) )
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_PAGEDOWN, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_next' ) )
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_PAGEDOWN, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_next' ) )
    
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_SCROLL_DOWN, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_next' ) )
    
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_HOME, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_first' ) )
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_HOME, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_first' ) )
    
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_END, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_last' ) )
    media_viewer_browser.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_END, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'view_last' ) )
    
    shortcuts.append( media_viewer_browser )
    
    media_viewer = ClientData.Shortcuts( 'media_viewer' )
    
    media_viewer.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'B' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'move_animation_to_previous_frame' ) )
    media_viewer.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'N' ), [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'move_animation_to_next_frame' ) )
    
    media_viewer.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'F' ), [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'switch_between_fullscreen_borderless_and_regular_framed_window' ) )
    
    media_viewer.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, ord( 'Z' ), [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'switch_between_100_percent_and_canvas_zoom' ) )
    media_viewer.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_ADD, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'zoom_in' ) )
    media_viewer.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_ADD, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'zoom_in' ) )
    media_viewer.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_SUBTRACT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'zoom_out' ) )
    media_viewer.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_NUMPAD_SUBTRACT, [] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'zoom_out' ) )
    
    media_viewer.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_SCROLL_UP, [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'zoom_in' ) )
    media_viewer.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_SCROLL_DOWN, [ CC.SHORTCUT_MODIFIER_CTRL ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'zoom_out' ) )
    
    media_viewer.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_UP, [ CC.SHORTCUT_MODIFIER_SHIFT ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'pan_up' ) )
    media_viewer.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_DOWN, [ CC.SHORTCUT_MODIFIER_SHIFT ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'pan_down' ) )
    media_viewer.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_LEFT, [ CC.SHORTCUT_MODIFIER_SHIFT ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'pan_left' ) )
    media_viewer.SetCommand( ClientData.Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_RIGHT, [ CC.SHORTCUT_MODIFIER_SHIFT ] ), ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'pan_right' ) )
    
    shortcuts.append( media_viewer )
    
    return shortcuts
    
def GetDefaultURLMatches():
    
    import ClientNetworkingDomain
    import ClientParsing
    
    url_matches = []
    
    #
    
    name = '4chan thread'
    url_type = HC.URL_TYPE_WATCHABLE
    preferred_scheme = 'https'
    netloc = 'boards.4chan.org'
    allow_subdomains = False
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_ANY, example_string = 'm' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'thread', example_string = 'thread' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '16086187' ) )
    
    parameters = {}
    
    example_url = 'https://boards.4chan.org/m/thread/16086187/ssg-super-sentai-general-651'
    
    # convert
    # https://boards.4chan.org/m/thread/16086187/ssg-super-sentai-general-651
    # to
    # https://a.4cdn.org/m/thread/16086187.json
    api_lookup_converter = ClientParsing.StringConverter( transformations = [ ( ClientParsing.STRING_TRANSFORMATION_REGEX_SUB, ( r'.*?([^/]+/thread/\d+).+', r'https://a.4cdn.org/\1.json' ) ) ] )
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, api_lookup_converter = api_lookup_converter, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = '4chan thread json api'
    url_type = HC.URL_TYPE_WATCHABLE
    preferred_scheme = 'https'
    netloc = 'a.4cdn.org'
    allow_subdomains = False
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_ANY, example_string = 'm' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'thread', example_string = 'thread' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_REGEX, match_value = r'\d+\.json', example_string = '16086187.json' ) )
    
    parameters = {}
    
    example_url = 'https://a.4cdn.org/m/thread/16086187.json'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = '4chan file'
    url_type = HC.URL_TYPE_FILE
    preferred_scheme = 'https'
    netloc = 'i.4cdn.org'
    allow_subdomains = False
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_ANY, example_string = 'm' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_REGEX, match_value = r'\d+\..+', example_string = '1512858563140.jpg' ) )
    
    parameters = {}
    
    example_url = 'https://i.4cdn.org/m/1512858563140.jpg'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = '8chan thread'
    url_type = HC.URL_TYPE_WATCHABLE
    preferred_scheme = 'https'
    netloc = '8ch.net'
    allow_subdomains = False
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_ANY, example_string = 'tv' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'res', example_string = 'res' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_REGEX, match_value = r'\d+\.html', example_string = '1002432.html' ) )
    
    parameters = {}
    
    example_url = 'https://8ch.net/tv/res/1002432.html'
    
    # convert
    # https://8ch.net/tv/res/1002432.html
    # to
    # https://8ch.net/tv/res/1002432.json
    api_lookup_converter = ClientParsing.StringConverter( transformations = [ ( ClientParsing.STRING_TRANSFORMATION_REGEX_SUB, ( r'(.+)html', r'\1json' ) ) ] )
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, api_lookup_converter = api_lookup_converter, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = '8chan thread json api'
    url_type = HC.URL_TYPE_WATCHABLE
    preferred_scheme = 'https'
    netloc = '8ch.net'
    allow_subdomains = False
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_ANY, example_string = 'tv' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'res', example_string = 'res' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_REGEX, match_value = r'\d+\.json', example_string = '1002432.json' ) )
    
    parameters = {}
    
    example_url = 'https://8ch.net/tv/res/1002432.json'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = '8chan file'
    url_type = HC.URL_TYPE_FILE
    preferred_scheme = 'https'
    netloc = '8ch.net'
    allow_subdomains = True
    keep_subdomains = True
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'file_store', example_string = 'file_store' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_REGEX, match_value = r'[\dabcdef]+\..+', example_string = '91b6d00f8f274d4505cabe690fbcf0b896a846e35a7faa8d2ddde5214d5bdc71.jpg' ) )
    
    parameters = {}
    example_url = 'https://media.8ch.net/file_store/91b6d00f8f274d4505cabe690fbcf0b896a846e35a7faa8d2ddde5214d5bdc71.jpg'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'hentai foundry artist pictures gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'www.hentai-foundry.com'
    allow_subdomains = False
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'pictures', example_string = 'pictures' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'user', example_string = 'user' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_ANY, example_string = 'daruak' ) )
    
    parameters = {}
    
    example_url = 'https://www.hentai-foundry.com/pictures/user/daruak/page/2'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'hentai foundry artist scraps gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'www.hentai-foundry.com'
    allow_subdomains = False
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'pictures', example_string = 'pictures' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'user', example_string = 'user' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_ANY, example_string = 'Sparrow' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'scraps', example_string = 'scraps' ) )
    
    parameters = {}
    
    example_url = 'https://www.hentai-foundry.com/pictures/user/Sparrow/scraps/page/3'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'hentai foundry tag search gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'www.hentai-foundry.com'
    allow_subdomains = False
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'search', example_string = 'search' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'index', example_string = 'index' ) )
    
    parameters = {}
    
    example_url = 'https://www.hentai-foundry.com/search/index?query=thick_thighs&page=5'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'hentai foundry file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'www.hentai-foundry.com'
    allow_subdomains = False
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'pictures', example_string = 'pictures' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'user', example_string = 'user' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_ANY, example_string = 'LittlePaw' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '554706' ) )
    
    parameters = {}
    
    example_url = 'https://www.hentai-foundry.com/pictures/user/LittlePaw/554706/Serpent-Girl'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'gelbooru gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'gelbooru.com'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'index.php', example_string = 'index.php' ) )
    
    parameters = {}
    
    parameters[ 'page' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' )
    parameters[ 's' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'list', example_string = 'list' )
    
    example_url = 'https://www.gelbooru.com/index.php?page=post&s=list&tags=bar_censor'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'gelbooru file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'gelbooru.com'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'index.php', example_string = 'index.php' ) )
    
    parameters = {}
    
    parameters[ 'page' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' )
    parameters[ 's' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'view', example_string = 'view' )
    parameters[ 'id' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '4009146' )
    
    example_url = 'https://gelbooru.com/index.php?page=post&s=view&id=4009146'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'safebooru gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'safebooru.org'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'index.php', example_string = 'index.php' ) )
    
    parameters = {}
    
    parameters[ 'page' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' )
    parameters[ 's' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'list', example_string = 'list' )
    
    example_url = 'https://safebooru.org/index.php?page=post&s=list&tags=black_footwear'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'safebooru file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'safebooru.org'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'index.php', example_string = 'index.php' ) )
    
    parameters = {}
    
    parameters[ 'page' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' )
    parameters[ 's' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'view', example_string = 'view' )
    parameters[ 'id' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '2406024' )
    
    example_url = 'https://safebooru.org/index.php?page=post&s=view&id=2406024'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'rule34.xxx gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'rule34.xxx'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'index.php', example_string = 'index.php' ) )
    
    parameters = {}
    
    parameters[ 'page' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' )
    parameters[ 's' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'list', example_string = 'list' )
    
    example_url = 'https://rule34.xxx/index.php?page=post&s=list&tags=ahe_gao'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'rule34.xxx file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'rule34.xxx'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'index.php', example_string = 'index.php' ) )
    
    parameters = {}
    
    parameters[ 'page' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' )
    parameters[ 's' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'view', example_string = 'view' )
    parameters[ 'id' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '2592511' )
    
    example_url = 'https://rule34.xxx/index.php?page=post&s=view&id=2592511'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'furry.booru.org gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'http'
    netloc = 'furry.booru.org'
    allow_subdomains = False
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'index.php', example_string = 'index.php' ) )
    
    parameters = {}
    
    parameters[ 'page' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' )
    parameters[ 's' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'list', example_string = 'list' )
    
    example_url = 'http://furry.booru.org/index.php?page=post&s=list&tags=blue_background'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'furry.booru.org file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'http'
    netloc = 'furry.booru.org'
    allow_subdomains = False
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'index.php', example_string = 'index.php' ) )
    
    parameters = {}
    
    parameters[ 'page' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' )
    parameters[ 's' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'view', example_string = 'view' )
    parameters[ 'id' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '1199885' )
    
    example_url = 'http://furry.booru.org/index.php?page=post&s=view&id=1199885'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'xbooru gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'http'
    netloc = 'xbooru.com'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'index.php', example_string = 'index.php' ) )
    
    parameters = {}
    
    parameters[ 'page' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' )
    parameters[ 's' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'list', example_string = 'list' )
    
    example_url = 'http://xbooru.com/index.php?page=post&s=list&tags=dickgirl'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'xbooru file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'http'
    netloc = 'xbooru.com'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'index.php', example_string = 'index.php' ) )
    
    parameters = {}
    
    parameters[ 'page' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' )
    parameters[ 's' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'view', example_string = 'view' )
    parameters[ 'id' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '708517' )
    
    example_url = 'http://xbooru.com/index.php?page=post&s=view&id=708517'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'tbib gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'tbib.org'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'index.php', example_string = 'index.php' ) )
    
    parameters = {}
    
    parameters[ 'page' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' )
    parameters[ 's' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'list', example_string = 'list' )
    
    example_url = 'https://tbib.org/index.php?page=post&s=list&tags=alternate_hairstyle'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'tbib file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'tbib.org'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'index.php', example_string = 'index.php' ) )
    
    parameters = {}
    
    parameters[ 'page' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' )
    parameters[ 's' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'view', example_string = 'view' )
    parameters[ 'id' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '6391256' )
    
    example_url = 'https://tbib.org/index.php?page=post&s=view&id=6391256'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'e621 gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'e621.net'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'index', example_string = 'index' ) )
    
    parameters = {}
    
    example_url = 'https://e621.net/post/index/1/smile'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'e621 file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'e621.net'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'show', example_string = 'show' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '1421754' ) )
    
    parameters = {}
    
    example_url = 'https://e621.net/post/show/1421754/abstract_background-animal_humanoid-blush-brown_ey'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'rule34.paheal gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'rule34.paheal.net'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'list', example_string = 'list' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_ANY, example_string = 'Pyra' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '1' ) )
    
    parameters = {}
    
    example_url = 'http://rule34.paheal.net/post/list/Pyra/1'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'rule34.paheal file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'rule34.paheal.net'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'view', example_string = 'view' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '2442974' ) )
    
    parameters = {}
    
    example_url = 'http://rule34.paheal.net/post/view/2442974'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'rule34hentai gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'rule34hentai.net'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'list', example_string = 'list' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_ANY, example_string = 'Triss_Merigold' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '1' ) )
    
    parameters = {}
    
    example_url = 'https://rule34hentai.net/post/list/Triss_Merigold/1'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'rule34hentai file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'rule34hentai.net'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'view', example_string = 'view' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '289558' ) )
    
    parameters = {}
    
    example_url = 'https://rule34hentai.net/post/view/289558'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'mishimmie gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'shimmie.katawa-shoujo.com'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'list', example_string = 'list' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_ANY, example_string = 'hanako' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '1' ) )
    
    parameters = {}
    
    example_url = 'http://shimmie.katawa-shoujo.com/post/list/hanako/1'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'mishimmie file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'shimmie.katawa-shoujo.com'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'view', example_string = 'view' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '4565' ) )
    
    parameters = {}
    
    example_url = 'http://shimmie.katawa-shoujo.com/post/view/4565'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'danbooru gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'danbooru.donmai.us'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' ) )
    
    parameters = {}
    
    example_url = 'https://danbooru.donmai.us/posts?page=1&tags=mikasa_ackerman'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'danbooru file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'danbooru.donmai.us'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '2982422' ) )
    
    parameters = {}
    
    example_url = 'https://danbooru.donmai.us/posts/2982422'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'konachan gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'konachan.com'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
    
    parameters = {}
    
    example_url = 'https://konachan.com/post?page=1&tags=landscape'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'konachan file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'konachan.com'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'show', example_string = 'show' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '258390' ) )
    
    parameters = {}
    
    example_url = 'https://konachan.com/post/show/258390/black_hair-dress-flowers-landscape-long_hair-neckl'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'yande.re gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'yande.re'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
    
    parameters = {}
    
    parameters[ 'page' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '1' )
    
    example_url = 'https://yande.re/post?page=1&tags=atago_%28azur_lane%29'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'yande.re file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'yande.re'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'show', example_string = 'show' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '428714' ) )
    
    parameters = {}
    
    example_url = 'https://yande.re/post/show/428714'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'sankaku chan gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'chan.sankakucomplex.com'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    parameters = {}
    
    example_url = 'https://chan.sankakucomplex.com/?tags=tomboy&page=1'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'sankaku chan file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'chan.sankakucomplex.com'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'show', example_string = 'show' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '6586014' ) )
    
    parameters = {}
    
    example_url = 'https://chan.sankakucomplex.com/post/show/6586014'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'sankaku idol gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'idol.sankakucomplex.com'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    parameters = {}
    
    example_url = 'https://idol.sankakucomplex.com/?tags=akagi_kuro&page=1'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'sankaku idol file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'idol.sankakucomplex.com'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'show', example_string = 'show' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '695512' ) )
    
    parameters = {}
    
    example_url = 'https://idol.sankakucomplex.com/post/show/695512'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'deviant art artist gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'deviantart.com'
    allow_subdomains = True
    keep_subdomains = True
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'gallery', example_string = 'gallery' ) )
    
    parameters = {}
    
    example_url = 'https://starca.deviantart.com/gallery/?catpath=/&offset=0'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'deviant art file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'deviantart.com'
    allow_subdomains = True
    keep_subdomains = True
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'art', example_string = 'art' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_ANY, example_string = 'Commission-animation-Elsa-and-Anna-541820782' ) )
    
    parameters = {}
    
    example_url = 'https://starca.deviantart.com/art/Commission-animation-Elsa-and-Anna-541820782'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'newgrounds games gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'newgrounds.com'
    allow_subdomains = True
    keep_subdomains = True
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'games', example_string = 'games' ) )
    
    parameters = {}
    
    example_url = 'https://matt-likes-swords.newgrounds.com/games/'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'newgrounds movies gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'newgrounds.com'
    allow_subdomains = True
    keep_subdomains = True
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'movies', example_string = 'movies' ) )
    
    parameters = {}
    
    example_url = 'https://sambakza.newgrounds.com/movies/'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'newgrounds file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'newgrounds.com'
    allow_subdomains = True
    keep_subdomains = True
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'portal', example_string = 'portal' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'view', example_string = 'view' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '161181' ) )
    
    parameters = {}
    
    example_url = 'https://www.newgrounds.com/portal/view/161181'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'pixiv artist gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'pixiv.net'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'member_illust.php', example_string = 'member_illust.php' ) )
    
    parameters = {}
    
    parameters[ 'id' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '115625' )
    
    example_url = 'https://www.pixiv.net/member_illust.php?id=115625&type=illust&p=1'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'pixiv file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'https'
    netloc = 'pixiv.net'
    allow_subdomains = True
    keep_subdomains = False
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'member_illust.php', example_string = 'member_illust.php' ) )
    
    parameters = {}
    
    parameters[ 'illust_id' ] = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '66476204' )
    
    example_url = 'https://www.pixiv.net/member_illust.php?mode=medium&illust_id=66476204'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'tumblr api gallery page'
    url_type = HC.URL_TYPE_GALLERY
    preferred_scheme = 'https'
    netloc = 'tumblr.com'
    allow_subdomains = True
    keep_subdomains = True
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'api', example_string = 'api' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'read', example_string = 'read' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'json', example_string = 'json' ) )
    
    parameters = {}
    
    example_url = 'https://sautte-fashion.tumblr.com/api/read/json?start=0&num=50'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    #
    
    name = 'tumblr file page'
    url_type = HC.URL_TYPE_POST
    preferred_scheme = 'http' # wew
    netloc = 'tumblr.com'
    allow_subdomains = True
    keep_subdomains = True
    
    path_components = []
    
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = 'post', example_string = 'post' ) )
    path_components.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC, example_string = '169381609093' ) )
    
    parameters = {}
    
    example_url = 'http://sautte-fashion.tumblr.com/post/169381609093/favorite-looks-from-alexander-mcqueen-resort-2012'
    
    url_match = ClientNetworkingDomain.URLMatch( name, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, allow_subdomains = allow_subdomains, keep_subdomains = keep_subdomains, path_components = path_components, parameters = parameters, example_url = example_url )
    
    url_matches.append( url_match )
    
    return url_matches
    
