from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.importing import ClientGUIImport
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class DownloadingPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        #
        
        gallery_downloader = ClientGUICommon.StaticBox( self, 'gallery downloader' )
        
        gug_key_and_name = CG.client_controller.network_engine.domain_manager.GetDefaultGUGKeyAndName()
        
        self._default_gug = ClientGUIImport.GUGKeyAndNameSelector( gallery_downloader, gug_key_and_name )
        
        self._override_bandwidth_on_file_urls_from_post_urls = QW.QCheckBox( gallery_downloader )
        tt = 'Sometimes, File URLs have tokens on them that cause them to time out. If this is on, all file urls will override all bandwidth rules within three seconds, ensuring they occur quickly after their spawning Post URL parsed them. I recommend you leave this on, but you can turn it off if you have troubles here.'
        self._override_bandwidth_on_file_urls_from_post_urls.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._gallery_page_wait_period_pages = ClientGUICommon.BetterSpinBox( gallery_downloader, min=1, max=3600 )
        self._gallery_file_limit = ClientGUICommon.NoneableSpinCtrl( gallery_downloader, 2000, none_phrase = 'no limit', min = 1, max = 1000000 )
        
        self._highlight_new_query = QW.QCheckBox( gallery_downloader )
        
        #
        
        subscriptions = ClientGUICommon.StaticBox( self, 'subscriptions' )
        
        self._gallery_page_wait_period_subscriptions = ClientGUICommon.BetterSpinBox( subscriptions, min=1, max=3600 )
        self._max_simultaneous_subscriptions = ClientGUICommon.BetterSpinBox( subscriptions, min=1, max=100 )
        
        self._subscription_file_error_cancel_threshold = ClientGUICommon.NoneableSpinCtrl( subscriptions, 5, min = 1, max = 1000000, unit = 'errors' )
        self._subscription_file_error_cancel_threshold.setToolTip( ClientGUIFunctions.WrapToolTip( 'This is a simple patch and will be replaced with a better "retry network errors later" system at some point, but is useful to increase if you have subs to unreliable websites.' ) )
        
        self._process_subs_in_random_order = QW.QCheckBox( subscriptions )
        self._process_subs_in_random_order.setToolTip( ClientGUIFunctions.WrapToolTip( 'Processing in random order is useful whenever bandwidth is tight, as it stops an \'aardvark\' subscription from always getting first whack at what is available. Otherwise, they will be processed in smart alphabetical order.' ) )
        
        checker_options = self._new_options.GetDefaultSubscriptionCheckerOptions()
        
        self._subscription_checker_options = ClientGUIImport.CheckerOptionsButton( subscriptions, checker_options )
        
        #
        
        watchers = ClientGUICommon.StaticBox( self, 'watchers' )
        
        self._watcher_page_wait_period = ClientGUICommon.BetterSpinBox( watchers, min=1, max=3600 )
        self._highlight_new_watcher = QW.QCheckBox( watchers )
        
        checker_options = self._new_options.GetDefaultWatcherCheckerOptions()
        
        self._watcher_checker_options = ClientGUIImport.CheckerOptionsButton( watchers, checker_options )
        
        #
        
        misc = ClientGUICommon.StaticBox( self, 'misc' )
        
        self._remove_leading_url_double_slashes = QW.QCheckBox( misc )
        tt = 'The client used to remove leading double slashes from an URL path, collapsing something like https://site.com//images/123456 to https://site.com/images/123456. This is not correct, and it no longer does this. If you need it to do this again, to fix some URL CLass, turn this on. I will retire this option eventually, so update your downloader to work in the new system (ideally recognise both formats).'
        self._remove_leading_url_double_slashes.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._replace_percent_twenty_with_space_in_gug_input = QW.QCheckBox( misc )
        tt = 'Checking this will cause any query text input into a downloader like "skirt%20blue_eyes" to be considered as "skirt blue_eyes". This lets you copy/paste an input straight from certain encoded URLs, but it also causes trouble if you need to input %20 raw, so this is no longer the default behaviour. This is a legacy option and I recommend you turn it off if you no longer think you need it.'
        self._replace_percent_twenty_with_space_in_gug_input.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._pause_character = QW.QLineEdit( misc )
        self._stop_character = QW.QLineEdit( misc )
        self._show_new_on_file_seed_short_summary = QW.QCheckBox( misc )
        self._show_deleted_on_file_seed_short_summary = QW.QCheckBox( misc )
        
        if self._new_options.GetBoolean( 'advanced_mode' ):
            
            delay_min = 1
            
        else:
            
            delay_min = 600
            
        
        self._subscription_network_error_delay = ClientGUITime.TimeDeltaButton( misc, min = delay_min, days = True, hours = True, minutes = True, seconds = True )
        self._subscription_other_error_delay = ClientGUITime.TimeDeltaButton( misc, min = delay_min, days = True, hours = True, minutes = True, seconds = True )
        self._downloader_network_error_delay = ClientGUITime.TimeDeltaButton( misc, min = delay_min, days = True, hours = True, minutes = True, seconds = True )
        
        #
        
        gallery_page_tt = 'Gallery page fetches are heavy requests with unusual fetch-time requirements. It is important they not wait too long, but it is also useful to throttle them:'
        gallery_page_tt += '\n' * 2
        gallery_page_tt += '- So they do not compete with file downloads for bandwidth, leading to very unbalanced 20/4400-type queues.'
        gallery_page_tt += '\n'
        gallery_page_tt += '- So you do not get 1000 items in your queue before realising you did not like that tag anyway.'
        gallery_page_tt += '\n'
        gallery_page_tt += '- To give servers a break (some gallery pages can be CPU-expensive to generate).'
        gallery_page_tt += '\n' * 2
        gallery_page_tt += 'These delays/lots are per-domain.'
        gallery_page_tt += '\n' * 2
        gallery_page_tt += 'If you do not understand this stuff, you can just leave it alone.'
        
        self._gallery_page_wait_period_pages.setValue( self._new_options.GetInteger( 'gallery_page_wait_period_pages' ) )
        self._gallery_page_wait_period_pages.setToolTip( ClientGUIFunctions.WrapToolTip( gallery_page_tt ) )
        self._gallery_file_limit.SetValue( HC.options['gallery_file_limit'] )
        
        self._override_bandwidth_on_file_urls_from_post_urls.setChecked( self._new_options.GetBoolean( 'override_bandwidth_on_file_urls_from_post_urls' ) )
        self._highlight_new_query.setChecked( self._new_options.GetBoolean( 'highlight_new_query' ) )
        
        self._gallery_page_wait_period_subscriptions.setValue( self._new_options.GetInteger( 'gallery_page_wait_period_subscriptions' ) )
        self._gallery_page_wait_period_subscriptions.setToolTip( ClientGUIFunctions.WrapToolTip( gallery_page_tt ) )
        self._max_simultaneous_subscriptions.setValue( self._new_options.GetInteger( 'max_simultaneous_subscriptions' ) )
        
        self._subscription_file_error_cancel_threshold.SetValue( self._new_options.GetNoneableInteger( 'subscription_file_error_cancel_threshold' ) )
        
        self._process_subs_in_random_order.setChecked( self._new_options.GetBoolean( 'process_subs_in_random_order' ) )
        
        self._remove_leading_url_double_slashes.setChecked( self._new_options.GetBoolean( 'remove_leading_url_double_slashes' ) )
        self._replace_percent_twenty_with_space_in_gug_input.setChecked( self._new_options.GetBoolean( 'replace_percent_twenty_with_space_in_gug_input' ) )
        self._pause_character.setText( self._new_options.GetString( 'pause_character' ) )
        self._stop_character.setText( self._new_options.GetString( 'stop_character' ) )
        self._show_new_on_file_seed_short_summary.setChecked( self._new_options.GetBoolean( 'show_new_on_file_seed_short_summary' ) )
        self._show_deleted_on_file_seed_short_summary.setChecked( self._new_options.GetBoolean( 'show_deleted_on_file_seed_short_summary' ) )
        
        self._watcher_page_wait_period.setValue( self._new_options.GetInteger( 'watcher_page_wait_period' ) )
        self._watcher_page_wait_period.setToolTip( ClientGUIFunctions.WrapToolTip( gallery_page_tt ) )
        self._highlight_new_watcher.setChecked( self._new_options.GetBoolean( 'highlight_new_watcher' ) )
        
        self._subscription_network_error_delay.SetValue( self._new_options.GetInteger( 'subscription_network_error_delay' ) )
        self._subscription_other_error_delay.SetValue( self._new_options.GetInteger( 'subscription_other_error_delay' ) )
        self._downloader_network_error_delay.SetValue( self._new_options.GetInteger( 'downloader_network_error_delay' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'Default download source:', self._default_gug ) )
        rows.append( ( 'Additional fixed time (in seconds) to wait between gallery page fetches:', self._gallery_page_wait_period_pages ) )
        rows.append( ( 'By default, stop searching once this many files are found:', self._gallery_file_limit ) )
        rows.append( ( 'If new query entered and no current highlight, highlight the new query:', self._highlight_new_query ) )
        rows.append( ( 'Force file downloads to occur quickly after Post URL fetches:', self._override_bandwidth_on_file_urls_from_post_urls ) )
        
        gridbox = ClientGUICommon.WrapInGrid( gallery_downloader, rows )
        
        gallery_downloader.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Additional fixed time (in seconds) to wait between gallery page fetches:', self._gallery_page_wait_period_subscriptions ) )
        rows.append( ( 'Maximum number of subscriptions that can sync simultaneously:', self._max_simultaneous_subscriptions ) )
        rows.append( ( 'If a subscription has this many failed file imports, stop and continue later:', self._subscription_file_error_cancel_threshold ) )
        rows.append( ( 'Sync subscriptions in random order:', self._process_subs_in_random_order ) )
        rows.append( ( 'Default subscription checker options:', self._subscription_checker_options ) )
        
        gridbox = ClientGUICommon.WrapInGrid( subscriptions, rows )
        
        subscriptions.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Additional fixed time (in seconds) to wait between watcher checks:', self._watcher_page_wait_period ) )
        rows.append( ( 'If new watcher entered and no current highlight, highlight the new watcher:', self._highlight_new_watcher ) )
        rows.append( ( 'Default watcher checker options:', self._watcher_checker_options ) )
        
        gridbox = ClientGUICommon.WrapInGrid( watchers, rows )
        
        watchers.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Pause character:', self._pause_character ) )
        rows.append( ( 'Stop character:', self._stop_character ) )
        rows.append( ( 'Show a \'N\' (for \'new\') count on short file import summaries:', self._show_new_on_file_seed_short_summary ) )
        rows.append( ( 'Show a \'D\' (for \'deleted\') count on short file import summaries:', self._show_deleted_on_file_seed_short_summary ) )
        rows.append( ( 'Delay time on a gallery/watcher network error:', self._downloader_network_error_delay ) )
        rows.append( ( 'Delay time on a subscription network error:', self._subscription_network_error_delay ) )
        rows.append( ( 'Delay time on a subscription other error:', self._subscription_other_error_delay ) )
        rows.append( ( 'DEBUG: remove leading double-slashes from URL paths:', self._remove_leading_url_double_slashes ) )
        rows.append( ( 'DEBUG: consider %20 the same as space in downloader query text inputs:', self._replace_percent_twenty_with_space_in_gug_input ) )
        
        gridbox = ClientGUICommon.WrapInGrid( misc, rows )
        
        misc.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gallery_downloader, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, subscriptions, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, watchers, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, misc, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def UpdateOptions( self ):
        
        CG.client_controller.network_engine.domain_manager.SetDefaultGUGKeyAndName( self._default_gug.GetValue() )
        
        self._new_options.SetInteger( 'gallery_page_wait_period_pages', self._gallery_page_wait_period_pages.value() )
        HC.options[ 'gallery_file_limit' ] = self._gallery_file_limit.GetValue()
        self._new_options.SetBoolean( 'highlight_new_query', self._highlight_new_query.isChecked() )
        self._new_options.SetBoolean( 'override_bandwidth_on_file_urls_from_post_urls', self._override_bandwidth_on_file_urls_from_post_urls.isChecked() )
        
        self._new_options.SetInteger( 'gallery_page_wait_period_subscriptions', self._gallery_page_wait_period_subscriptions.value() )
        self._new_options.SetInteger( 'max_simultaneous_subscriptions', self._max_simultaneous_subscriptions.value() )
        self._new_options.SetNoneableInteger( 'subscription_file_error_cancel_threshold', self._subscription_file_error_cancel_threshold.GetValue() )
        self._new_options.SetBoolean( 'process_subs_in_random_order', self._process_subs_in_random_order.isChecked() )
        
        self._new_options.SetInteger( 'watcher_page_wait_period', self._watcher_page_wait_period.value() )
        self._new_options.SetBoolean( 'highlight_new_watcher', self._highlight_new_watcher.isChecked() )
        
        self._new_options.SetDefaultWatcherCheckerOptions( self._watcher_checker_options.GetValue() )
        self._new_options.SetDefaultSubscriptionCheckerOptions( self._subscription_checker_options.GetValue() )
        
        self._new_options.SetBoolean( 'remove_leading_url_double_slashes', self._remove_leading_url_double_slashes.isChecked() )
        self._new_options.SetBoolean( 'replace_percent_twenty_with_space_in_gug_input', self._replace_percent_twenty_with_space_in_gug_input.isChecked() )
        self._new_options.SetString( 'pause_character', self._pause_character.text() )
        self._new_options.SetString( 'stop_character', self._stop_character.text() )
        self._new_options.SetBoolean( 'show_new_on_file_seed_short_summary', self._show_new_on_file_seed_short_summary.isChecked() )
        self._new_options.SetBoolean( 'show_deleted_on_file_seed_short_summary', self._show_deleted_on_file_seed_short_summary.isChecked() )
        
        self._new_options.SetInteger( 'subscription_network_error_delay', self._subscription_network_error_delay.GetValue() )
        self._new_options.SetInteger( 'subscription_other_error_delay', self._subscription_other_error_delay.GetValue() )
        self._new_options.SetInteger( 'downloader_network_error_delay', self._downloader_network_error_delay.GetValue() )
        
    
