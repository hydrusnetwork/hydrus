import collections
import os
import random
import re
import traceback

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusImageHandling
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusText

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIImport
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIScrolledPanelsEdit
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUIStyle
from hydrus.client.gui import ClientGUITags
from hydrus.client.gui import ClientGUITagSorting
from hydrus.client.gui import ClientGUITime
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.pages import ClientGUIResultsSortCollect
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.search import ClientGUISearch
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIControls
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags
from hydrus.client.networking import ClientNetworkingSessions

class ManageOptionsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._new_options = HG.client_controller.new_options
        
        self._listbook = ClientGUICommon.ListBook( self )
        
        self._listbook.AddPage( 'gui', 'gui', self._GUIPanel( self._listbook ) ) # leave this at the top, to make it default page
        self._listbook.AddPage( 'gui pages', 'gui pages', self._GUIPagesPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'connection', 'connection', self._ConnectionPanel( self._listbook ) )
        self._listbook.AddPage( 'external programs', 'external programs', self._ExternalProgramsPanel( self._listbook ) )
        self._listbook.AddPage( 'files and trash', 'files and trash', self._FilesAndTrashPanel( self._listbook ) )
        self._listbook.AddPage( 'file viewing statistics', 'file viewing statistics', self._FileViewingStatisticsPanel( self._listbook ) )
        self._listbook.AddPage( 'speed and memory', 'speed and memory', self._SpeedAndMemoryPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'maintenance and processing', 'maintenance and processing', self._MaintenanceAndProcessingPanel( self._listbook ) )
        self._listbook.AddPage( 'media', 'media', self._MediaPanel( self._listbook ) )
        self._listbook.AddPage( 'audio', 'audio', self._AudioPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'system tray', 'system tray', self._SystemTrayPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'search', 'search', self._SearchPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'colours', 'colours', self._ColoursPanel( self._listbook ) )
        self._listbook.AddPage( 'popups', 'popups', self._PopupPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'regex favourites', 'regex favourites', self._RegexPanel( self._listbook ) )
        self._listbook.AddPage( 'sort/collect', 'sort/collect', self._SortCollectPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'downloading', 'downloading', self._DownloadingPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'duplicates', 'duplicates', self._DuplicatesPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'importing', 'importing', self._ImportingPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'style', 'style', self._StylePanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tag presentation', 'tag presentation', self._TagPresentationPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tag suggestions', 'tag suggestions', self._TagSuggestionsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tags', 'tags', self._TagsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'thumbnails', 'thumbnails', self._ThumbnailsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'system', 'system', self._SystemPanel( self._listbook, self._new_options ) )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._listbook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    class _AudioPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #self._media_viewer_uses_its_own_audio_volume = QW.QCheckBox( self )
            self._preview_uses_its_own_audio_volume = QW.QCheckBox( self )
            
            self._has_audio_label = QW.QLineEdit( self )
            
            #
            
            tt = 'If unchecked, this media canvas will use the \'global\' audio volume slider. If checked, this media canvas will have its own separate one.'
            tt += os.linesep * 2
            tt += 'Keep this on if you would like the preview viewer to be quieter than the main media viewer.'
            
            #self._media_viewer_uses_its_own_audio_volume.setChecked( self._new_options.GetBoolean( 'media_viewer_uses_its_own_audio_volume' ) )
            self._preview_uses_its_own_audio_volume.setChecked( self._new_options.GetBoolean( 'preview_uses_its_own_audio_volume' ) )
            
            #self._media_viewer_uses_its_own_audio_volume.setToolTip( tt )
            self._preview_uses_its_own_audio_volume.setToolTip( tt )
            
            self._has_audio_label.setText( self._new_options.GetString( 'has_audio_label' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'The preview window has its own volume: ', self._preview_uses_its_own_audio_volume ) )
            #rows.append( ( 'The media viewer has its own volume: ', self._media_viewer_uses_its_own_audio_volume ) )
            rows.append( ( 'Label for files with audio: ', self._has_audio_label ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            #self._new_options.SetBoolean( 'media_viewer_uses_its_own_audio_volume', self._media_viewer_uses_its_own_audio_volume.isChecked() )
            self._new_options.SetBoolean( 'preview_uses_its_own_audio_volume', self._preview_uses_its_own_audio_volume.isChecked() )
            
            self._new_options.SetString( 'has_audio_label', self._has_audio_label.text() )
            
        
    
    class _ColoursPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            coloursets_panel = ClientGUICommon.StaticBox( self, 'coloursets' )
            
            self._current_colourset = ClientGUICommon.BetterChoice( coloursets_panel )
            
            self._current_colourset.addItem( 'default', 'default' )
            self._current_colourset.addItem( 'darkmode', 'darkmode' )
            
            self._current_colourset.SetValue( self._new_options.GetString( 'current_colourset' ) )
            
            self._notebook = QW.QTabWidget( coloursets_panel )
            
            self._gui_colours = {}
            
            for colourset in ( 'default', 'darkmode' ):
                
                self._gui_colours[ colourset ] = {}
                
                colour_panel = QW.QWidget( self._notebook )
                
                colour_types = []
                
                colour_types.append( CC.COLOUR_THUMB_BACKGROUND )
                colour_types.append( CC.COLOUR_THUMB_BACKGROUND_SELECTED )
                colour_types.append( CC.COLOUR_THUMB_BACKGROUND_REMOTE )
                colour_types.append( CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED )
                colour_types.append( CC.COLOUR_THUMB_BORDER )
                colour_types.append( CC.COLOUR_THUMB_BORDER_SELECTED )
                colour_types.append( CC.COLOUR_THUMB_BORDER_REMOTE )
                colour_types.append( CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED )
                colour_types.append( CC.COLOUR_THUMBGRID_BACKGROUND )
                colour_types.append( CC.COLOUR_AUTOCOMPLETE_BACKGROUND )
                colour_types.append( CC.COLOUR_MEDIA_BACKGROUND )
                colour_types.append( CC.COLOUR_MEDIA_TEXT )
                colour_types.append( CC.COLOUR_TAGS_BOX )
                
                for colour_type in colour_types:
                    
                    ctrl = ClientGUICommon.BetterColourControl( colour_panel )
                    
                    ctrl.setMaximumWidth( 20 )
                    
                    ctrl.SetColour( self._new_options.GetColour( colour_type, colourset ) )
                    
                    self._gui_colours[ colourset ][ colour_type ] = ctrl
                    
                
                #
                
                rows = []
                
                hbox = QP.HBoxLayout()
                
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND], CC.FLAGS_CENTER_PERPENDICULAR )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND_SELECTED], CC.FLAGS_CENTER_PERPENDICULAR )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND_REMOTE], CC.FLAGS_CENTER_PERPENDICULAR )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED], CC.FLAGS_CENTER_PERPENDICULAR )
                
                rows.append( ( 'thumbnail background (local: normal/selected, remote: normal/selected): ', hbox ) )
                
                hbox = QP.HBoxLayout()
                
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER], CC.FLAGS_CENTER_PERPENDICULAR )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER_SELECTED], CC.FLAGS_CENTER_PERPENDICULAR )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER_REMOTE], CC.FLAGS_CENTER_PERPENDICULAR )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED], CC.FLAGS_CENTER_PERPENDICULAR )
                
                rows.append( ( 'thumbnail border (local: normal/selected, remote: normal/selected): ', hbox ) )
                
                rows.append( ( 'thumbnail grid background: ', self._gui_colours[ colourset ][ CC.COLOUR_THUMBGRID_BACKGROUND ] ) )
                rows.append( ( 'autocomplete background: ', self._gui_colours[ colourset ][ CC.COLOUR_AUTOCOMPLETE_BACKGROUND ] ) )
                rows.append( ( 'media viewer background: ', self._gui_colours[ colourset ][ CC.COLOUR_MEDIA_BACKGROUND ] ) )
                rows.append( ( 'media viewer text: ', self._gui_colours[ colourset ][ CC.COLOUR_MEDIA_TEXT ] ) )
                rows.append( ( 'tags box background: ', self._gui_colours[ colourset ][ CC.COLOUR_TAGS_BOX ] ) )
                
                gridbox = ClientGUICommon.WrapInGrid( colour_panel, rows )
                
                colour_panel.setLayout( gridbox )
                
                select = colourset == 'default'
                
                self._notebook.addTab( colour_panel, colourset )
                if select: self._notebook.setCurrentWidget( colour_panel )
                
            
            #
            
            coloursets_panel.Add( ClientGUICommon.WrapInText( self._current_colourset, coloursets_panel, 'current colourset: ' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            coloursets_panel.Add( self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, coloursets_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            for colourset in self._gui_colours:
                
                for ( colour_type, ctrl ) in list(self._gui_colours[ colourset ].items()):
                    
                    colour = ctrl.GetColour()
                    
                    self._new_options.SetColour( colour_type, colourset, colour )
                    
                
            
            self._new_options.SetString( 'current_colourset', self._current_colourset.GetValue() )
            
        
    
    class _ConnectionPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            general = ClientGUICommon.StaticBox( self, 'general' )
            
            self._verify_regular_https = QW.QCheckBox( general )
            
            if self._new_options.GetBoolean( 'advanced_mode' ):
                
                network_timeout_min = 1
                network_timeout_max = 86400 * 30
                
                error_wait_time_min = 1
                error_wait_time_max = 86400 * 30
                
                max_network_jobs_max = 1000
                
                max_network_jobs_per_domain_max = 100
                
            else:
                
                network_timeout_min = 3
                network_timeout_max = 600
                
                error_wait_time_min = 3
                error_wait_time_max = 1800
                
                max_network_jobs_max = 30
                
                max_network_jobs_per_domain_max = 5
                
            
            self._network_timeout = QP.MakeQSpinBox( general, min = network_timeout_min, max = network_timeout_max )
            self._network_timeout.setToolTip( 'If a network connection cannot be made in this duration or, if once started, it experiences uninterrupted inactivity for six times this duration, it will be abandoned.' )
            
            self._connection_error_wait_time = QP.MakeQSpinBox( general, min = error_wait_time_min, max = error_wait_time_max )
            self._connection_error_wait_time.setToolTip( 'If a network connection times out as above, it will wait increasing multiples of this base time before retrying.' )
            
            self._serverside_bandwidth_wait_time = QP.MakeQSpinBox( general, min = error_wait_time_min, max = error_wait_time_max )
            self._serverside_bandwidth_wait_time.setToolTip( 'If a server returns a failure status code indicating it is short on bandwidth, the network job will wait increasing multiples of this base time before retrying.' )
            
            self._domain_network_infrastructure_error_velocity = ClientGUITime.VelocityCtrl( general, 0, 100, 30, hours = True, minutes = True, seconds = True, per_phrase = 'within', unit = 'errors' )
            
            self._max_network_jobs = QP.MakeQSpinBox( general, min = 1, max = max_network_jobs_max )
            self._max_network_jobs_per_domain = QP.MakeQSpinBox( general, min = 1, max = max_network_jobs_per_domain_max )
            
            #
            
            proxy_panel = ClientGUICommon.StaticBox( self, 'proxy settings' )
            
            self._http_proxy = ClientGUICommon.NoneableTextCtrl( proxy_panel )
            self._https_proxy = ClientGUICommon.NoneableTextCtrl( proxy_panel )
            self._no_proxy = ClientGUICommon.NoneableTextCtrl( proxy_panel )
            
            #
            
            self._verify_regular_https.setChecked( self._new_options.GetBoolean( 'verify_regular_https' ) )
            
            self._http_proxy.SetValue( self._new_options.GetNoneableString( 'http_proxy' ) )
            self._https_proxy.SetValue( self._new_options.GetNoneableString( 'https_proxy' ) )
            self._no_proxy.SetValue( self._new_options.GetNoneableString( 'no_proxy' ) )
            
            self._network_timeout.setValue( self._new_options.GetInteger( 'network_timeout' ) )
            self._connection_error_wait_time.setValue( self._new_options.GetInteger( 'connection_error_wait_time' ) )
            self._serverside_bandwidth_wait_time.setValue( self._new_options.GetInteger( 'serverside_bandwidth_wait_time' ) )
            
            number = self._new_options.GetInteger( 'domain_network_infrastructure_error_number' )
            time_delta = self._new_options.GetInteger( 'domain_network_infrastructure_error_time_delta' )
            
            self._domain_network_infrastructure_error_velocity.SetValue( ( number, time_delta ) )
            
            self._max_network_jobs.setValue( self._new_options.GetInteger( 'max_network_jobs' ) )
            self._max_network_jobs_per_domain.setValue( self._new_options.GetInteger( 'max_network_jobs_per_domain' ) )
            
            #
            
            if self._new_options.GetBoolean( 'advanced_mode' ):
                
                label = 'As you are in advanced mode, these options have very low and high limits. Be very careful about lowering delay time or raising max number of connections too far, as things will break.'
                
                st = ClientGUICommon.BetterStaticText( general, label = label )
                st.setObjectName( 'HydrusWarning' )
                
                st.setWordWrap( True )
                
                general.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            rows = []
            
            rows.append( ( 'network timeout (seconds): ', self._network_timeout ) )
            rows.append( ( 'connection error retry wait (seconds): ', self._connection_error_wait_time ) )
            rows.append( ( 'serverside bandwidth retry wait (seconds): ', self._serverside_bandwidth_wait_time ) )
            rows.append( ( 'Halt new jobs as long as this many network infrastructure errors on their domain (0 for never wait): ', self._domain_network_infrastructure_error_velocity ) )
            rows.append( ( 'max number of simultaneous active network jobs: ', self._max_network_jobs ) )
            rows.append( ( 'max number of simultaneous active network jobs per domain: ', self._max_network_jobs_per_domain ) )
            rows.append( ( 'BUGFIX: verify regular https traffic:', self._verify_regular_https ) )
            
            gridbox = ClientGUICommon.WrapInGrid( general, rows )
            
            general.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            text = 'Enter strings such as "http://ip:port" or "http://user:pass@ip:port" to use for http and https traffic. It should take effect immediately on dialog ok.'
            text += os.linesep * 2
            text += 'NO PROXY DOES NOT WORK UNLESS YOU HAVE A CUSTOM BUILD OF REQUESTS, SORRY! no_proxy takes the form of comma-separated hosts/domains, just as in curl or the NO_PROXY environment variable. When http and/or https proxies are set, they will not be used for these.'
            text += os.linesep * 2
            
            if ClientNetworkingSessions.SOCKS_PROXY_OK:
                
                text += 'It looks like you have socks support! You should also be able to enter (socks4 or) "socks5://ip:port".'
                text += os.linesep
                text += 'Use socks4a or socks5h to force remote DNS resolution, on the proxy server.'
                
            else:
                
                text += 'It does not look like you have socks support! If you want it, try adding "pysocks" (or "requests[socks]")!'
                
            
            st = ClientGUICommon.BetterStaticText( proxy_panel, text )
            
            st.setWordWrap( True )
            
            proxy_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'http: ', self._http_proxy ) )
            rows.append( ( 'https: ', self._https_proxy ) )
            rows.append( ( 'no_proxy: ', self._no_proxy ) )
            
            gridbox = ClientGUICommon.WrapInGrid( proxy_panel, rows )
            
            proxy_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, general, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, proxy_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'verify_regular_https', self._verify_regular_https.isChecked() )
            
            self._new_options.SetNoneableString( 'http_proxy', self._http_proxy.GetValue() )
            self._new_options.SetNoneableString( 'https_proxy', self._https_proxy.GetValue() )
            self._new_options.SetNoneableString( 'no_proxy', self._no_proxy.GetValue() )
            
            self._new_options.SetInteger( 'network_timeout', self._network_timeout.value() )
            self._new_options.SetInteger( 'connection_error_wait_time', self._connection_error_wait_time.value() )
            self._new_options.SetInteger( 'serverside_bandwidth_wait_time', self._serverside_bandwidth_wait_time.value() )
            self._new_options.SetInteger( 'max_network_jobs', self._max_network_jobs.value() )
            self._new_options.SetInteger( 'max_network_jobs_per_domain', self._max_network_jobs_per_domain.value() )
            
            ( number, time_delta ) = self._domain_network_infrastructure_error_velocity.GetValue()
            
            self._new_options.SetInteger( 'domain_network_infrastructure_error_number', number )
            self._new_options.SetInteger( 'domain_network_infrastructure_error_time_delta', time_delta )
            
        
    
    class _DownloadingPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            gallery_downloader = ClientGUICommon.StaticBox( self, 'gallery downloader' )
            
            gug_key_and_name = HG.client_controller.network_engine.domain_manager.GetDefaultGUGKeyAndName()
            
            self._default_gug = ClientGUIImport.GUGKeyAndNameSelector( gallery_downloader, gug_key_and_name )
            
            self._gallery_page_wait_period_pages = QP.MakeQSpinBox( gallery_downloader, min=1, max=120 )
            self._gallery_file_limit = ClientGUICommon.NoneableSpinCtrl( gallery_downloader, none_phrase = 'no limit', min = 1, max = 1000000 )
            
            self._highlight_new_query = QW.QCheckBox( gallery_downloader )
            
            #
            
            subscriptions = ClientGUICommon.StaticBox( self, 'subscriptions' )
            
            self._gallery_page_wait_period_subscriptions = QP.MakeQSpinBox( subscriptions, min=1, max=30 )
            self._max_simultaneous_subscriptions = QP.MakeQSpinBox( subscriptions, min=1, max=100 )
            
            self._subscription_file_error_cancel_threshold = ClientGUICommon.NoneableSpinCtrl( subscriptions, min = 1, max = 1000000, unit = 'errors' )
            self._subscription_file_error_cancel_threshold.setToolTip( 'This is a simple patch and will be replaced with a better "retry network errors later" system at some point, but is useful to increase if you have subs to unreliable websites.' )
            
            self._process_subs_in_random_order = QW.QCheckBox( subscriptions )
            self._process_subs_in_random_order.setToolTip( 'Processing in random order is useful whenever bandwidth is tight, as it stops an \'aardvark\' subscription from always getting first whack at what is available. Otherwise, they will be processed in alphabetical order.' )
            
            checker_options = self._new_options.GetDefaultSubscriptionCheckerOptions()
            
            self._subscription_checker_options = ClientGUIImport.CheckerOptionsButton( subscriptions, checker_options )
            
            #
            
            watchers = ClientGUICommon.StaticBox( self, 'watchers' )
            
            self._watcher_page_wait_period = QP.MakeQSpinBox( watchers, min=1, max=120 )
            self._highlight_new_watcher = QW.QCheckBox( watchers )
            
            checker_options = self._new_options.GetDefaultWatcherCheckerOptions()
            
            self._watcher_checker_options = ClientGUIImport.CheckerOptionsButton( watchers, checker_options )
            
            #
            
            misc = ClientGUICommon.StaticBox( self, 'misc' )
            
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
            gallery_page_tt += os.linesep * 2
            gallery_page_tt += '- So they do not compete with file downloads for bandwidth, leading to very unbalanced 20/4400-type queues.'
            gallery_page_tt += os.linesep
            gallery_page_tt += '- So you do not get 1000 items in your queue before realising you did not like that tag anyway.'
            gallery_page_tt += os.linesep
            gallery_page_tt += '- To give servers a break (some gallery pages can be CPU-expensive to generate).'
            gallery_page_tt += os.linesep * 2
            gallery_page_tt += 'These delays/lots are per-domain.'
            gallery_page_tt += os.linesep * 2
            gallery_page_tt += 'If you do not understand this stuff, you can just leave it alone.'
            
            self._gallery_page_wait_period_pages.setValue( self._new_options.GetInteger( 'gallery_page_wait_period_pages' ) )
            self._gallery_page_wait_period_pages.setToolTip( gallery_page_tt )
            self._gallery_file_limit.SetValue( HC.options['gallery_file_limit'] )
            
            self._highlight_new_query.setChecked( self._new_options.GetBoolean( 'highlight_new_query' ) )
            
            self._gallery_page_wait_period_subscriptions.setValue( self._new_options.GetInteger( 'gallery_page_wait_period_subscriptions' ) )
            self._gallery_page_wait_period_subscriptions.setToolTip( gallery_page_tt )
            self._max_simultaneous_subscriptions.setValue( self._new_options.GetInteger( 'max_simultaneous_subscriptions' ) )
            
            self._subscription_file_error_cancel_threshold.SetValue( self._new_options.GetNoneableInteger( 'subscription_file_error_cancel_threshold' ) )
            
            self._process_subs_in_random_order.setChecked( self._new_options.GetBoolean( 'process_subs_in_random_order' ) )
            
            self._pause_character.setText( self._new_options.GetString( 'pause_character' ) )
            self._stop_character.setText( self._new_options.GetString( 'stop_character' ) )
            self._show_new_on_file_seed_short_summary.setChecked( self._new_options.GetBoolean( 'show_new_on_file_seed_short_summary' ) )
            self._show_deleted_on_file_seed_short_summary.setChecked( self._new_options.GetBoolean( 'show_deleted_on_file_seed_short_summary' ) )
            
            self._watcher_page_wait_period.setValue( self._new_options.GetInteger( 'watcher_page_wait_period' ) )
            self._watcher_page_wait_period.setToolTip( gallery_page_tt )
            self._highlight_new_watcher.setChecked( self._new_options.GetBoolean( 'highlight_new_watcher' ) )
            
            self._subscription_network_error_delay.SetValue( self._new_options.GetInteger( 'subscription_network_error_delay' ) )
            self._subscription_other_error_delay.SetValue( self._new_options.GetInteger( 'subscription_other_error_delay' ) )
            self._downloader_network_error_delay.SetValue( self._new_options.GetInteger( 'downloader_network_error_delay' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Default download source:', self._default_gug ) )
            rows.append( ( 'If new query entered and no current highlight, highlight the new query:', self._highlight_new_query ) )
            rows.append( ( 'Additional fixed time (in seconds) to wait between gallery page fetches:', self._gallery_page_wait_period_pages ) )
            rows.append( ( 'By default, stop searching once this many files are found:', self._gallery_file_limit ) )
            
            gridbox = ClientGUICommon.WrapInGrid( gallery_downloader, rows )
            
            gallery_downloader.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Additional fixed time (in seconds) to wait between gallery page fetches:', self._gallery_page_wait_period_subscriptions ) )
            rows.append( ( 'Maximum number of subscriptions that can sync simultaneously:', self._max_simultaneous_subscriptions ) )
            rows.append( ( 'If a subscription has this many failed file imports, stop and continue later:', self._subscription_file_error_cancel_threshold ) )
            rows.append( ( 'Sync subscriptions in random order:', self._process_subs_in_random_order ) )
            
            gridbox = ClientGUICommon.WrapInGrid( subscriptions, rows )
            
            subscriptions.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            subscriptions.Add( self._subscription_checker_options, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Additional fixed time (in seconds) to wait between watcher checks:', self._watcher_page_wait_period ) )
            rows.append( ( 'If new watcher entered and no current highlight, highlight the new watcher:', self._highlight_new_watcher ) )
            
            gridbox = ClientGUICommon.WrapInGrid( watchers, rows )
            
            watchers.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            watchers.Add( self._watcher_checker_options, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Pause character:', self._pause_character ) )
            rows.append( ( 'Stop character:', self._stop_character ) )
            rows.append( ( 'Show a \'N\' (for \'new\') count on short file import summaries:', self._show_new_on_file_seed_short_summary ) )
            rows.append( ( 'Show a \'D\' (for \'deleted\') count on short file import summaries:', self._show_deleted_on_file_seed_short_summary ) )
            rows.append( ( 'Delay time on a gallery/watcher network error:', self._downloader_network_error_delay ) )
            rows.append( ( 'Delay time on a subscription network error:', self._subscription_network_error_delay ) )
            rows.append( ( 'Delay time on a subscription other error:', self._subscription_other_error_delay ) )
            
            gridbox = ClientGUICommon.WrapInGrid( misc, rows )
            
            misc.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, gallery_downloader, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, subscriptions, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, watchers, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, misc, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            HG.client_controller.network_engine.domain_manager.SetDefaultGUGKeyAndName( self._default_gug.GetValue() )
            
            self._new_options.SetInteger( 'gallery_page_wait_period_pages', self._gallery_page_wait_period_pages.value() )
            HC.options[ 'gallery_file_limit' ] = self._gallery_file_limit.GetValue()
            self._new_options.SetBoolean( 'highlight_new_query', self._highlight_new_query.isChecked() )
            
            self._new_options.SetInteger( 'gallery_page_wait_period_subscriptions', self._gallery_page_wait_period_subscriptions.value() )
            self._new_options.SetInteger( 'max_simultaneous_subscriptions', self._max_simultaneous_subscriptions.value() )
            self._new_options.SetNoneableInteger( 'subscription_file_error_cancel_threshold', self._subscription_file_error_cancel_threshold.GetValue() )
            self._new_options.SetBoolean( 'process_subs_in_random_order', self._process_subs_in_random_order.isChecked() )
            
            self._new_options.SetInteger( 'watcher_page_wait_period', self._watcher_page_wait_period.value() )
            self._new_options.SetBoolean( 'highlight_new_watcher', self._highlight_new_watcher.isChecked() )
            
            self._new_options.SetDefaultWatcherCheckerOptions( self._watcher_checker_options.GetValue() )
            self._new_options.SetDefaultSubscriptionCheckerOptions( self._subscription_checker_options.GetValue() )
            
            self._new_options.SetString( 'pause_character', self._pause_character.text() )
            self._new_options.SetString( 'stop_character', self._stop_character.text() )
            self._new_options.SetBoolean( 'show_new_on_file_seed_short_summary', self._show_new_on_file_seed_short_summary.isChecked() )
            self._new_options.SetBoolean( 'show_deleted_on_file_seed_short_summary', self._show_deleted_on_file_seed_short_summary.isChecked() )
            
            self._new_options.SetInteger( 'subscription_network_error_delay', self._subscription_network_error_delay.GetValue() )
            self._new_options.SetInteger( 'subscription_other_error_delay', self._subscription_other_error_delay.GetValue() )
            self._new_options.SetInteger( 'downloader_network_error_delay', self._downloader_network_error_delay.GetValue() )
            
        
    
    class _DuplicatesPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            weights_panel = ClientGUICommon.StaticBox( self, 'duplicate filter comparison score weights' )
            
            self._duplicate_comparison_score_higher_jpeg_quality = QP.MakeQSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_much_higher_jpeg_quality = QP.MakeQSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_higher_filesize = QP.MakeQSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_much_higher_filesize = QP.MakeQSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_higher_resolution = QP.MakeQSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_much_higher_resolution = QP.MakeQSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_more_tags = QP.MakeQSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_older = QP.MakeQSpinBox( weights_panel, min=-100, max=100 )
            self._duplicate_comparison_score_nicer_ratio = QP.MakeQSpinBox( weights_panel, min=-100, max=100 )
            
            self._duplicate_comparison_score_nicer_ratio.setToolTip( 'For instance, 16:9 vs 640:357.')
            
            self._duplicate_filter_max_batch_size = QP.MakeQSpinBox( self, min = 10, max = 1024 )
            
            #
            
            self._duplicate_comparison_score_higher_jpeg_quality.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_higher_jpeg_quality' ) )
            self._duplicate_comparison_score_much_higher_jpeg_quality.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_much_higher_jpeg_quality' ) )
            self._duplicate_comparison_score_higher_filesize.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_higher_filesize' ) )
            self._duplicate_comparison_score_much_higher_filesize.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_much_higher_filesize' ) )
            self._duplicate_comparison_score_higher_resolution.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_higher_resolution' ) )
            self._duplicate_comparison_score_much_higher_resolution.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_much_higher_resolution' ) )
            self._duplicate_comparison_score_more_tags.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_more_tags' ) )
            self._duplicate_comparison_score_older.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_older' ) )
            self._duplicate_comparison_score_nicer_ratio.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_nicer_ratio' ) )
            
            self._duplicate_filter_max_batch_size.setValue( self._new_options.GetInteger( 'duplicate_filter_max_batch_size' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Score for jpeg with non-trivially higher jpeg quality:', self._duplicate_comparison_score_higher_jpeg_quality ) )
            rows.append( ( 'Score for jpeg with significantly higher jpeg quality:', self._duplicate_comparison_score_much_higher_jpeg_quality ) )
            rows.append( ( 'Score for file with non-trivially higher filesize:', self._duplicate_comparison_score_higher_filesize ) )
            rows.append( ( 'Score for file with significantly higher filesize:', self._duplicate_comparison_score_much_higher_filesize ) )
            rows.append( ( 'Score for file with higher resolution (as num pixels):', self._duplicate_comparison_score_higher_resolution ) )
            rows.append( ( 'Score for file with significantly higher resolution (as num pixels):', self._duplicate_comparison_score_much_higher_resolution ) )
            rows.append( ( 'Score for file with more tags:', self._duplicate_comparison_score_more_tags ) )
            rows.append( ( 'Score for file with non-trivially earlier import time:', self._duplicate_comparison_score_older ) )
            rows.append( ( 'Score for file with \'nicer\' resolution ratio:', self._duplicate_comparison_score_nicer_ratio ) )
            
            gridbox = ClientGUICommon.WrapInGrid( weights_panel, rows )
            
            label = 'When processing potential duplicate pairs in the duplicate filter, the client tries to present the \'best\' file first. It judges the two files on a variety of potential differences, each with a score. The file with the greatest total score is presented first. Here you can tinker with these scores.'
            label += os.linesep * 2
            label += 'I recommend you leave all these as positive numbers, but if you wish, you can set a negative number to reduce the score.'
            
            st = ClientGUICommon.BetterStaticText( weights_panel, label )
            st.setWordWrap( True )
            
            weights_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            weights_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, weights_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Max size of duplicate filter pair batches:', self._duplicate_filter_max_batch_size ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetInteger( 'duplicate_comparison_score_higher_jpeg_quality', self._duplicate_comparison_score_higher_jpeg_quality.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_much_higher_jpeg_quality', self._duplicate_comparison_score_much_higher_jpeg_quality.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_higher_filesize', self._duplicate_comparison_score_higher_filesize.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_much_higher_filesize', self._duplicate_comparison_score_much_higher_filesize.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_higher_resolution', self._duplicate_comparison_score_higher_resolution.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_much_higher_resolution', self._duplicate_comparison_score_much_higher_resolution.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_more_tags', self._duplicate_comparison_score_more_tags.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_older', self._duplicate_comparison_score_older.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_nicer_ratio', self._duplicate_comparison_score_nicer_ratio.value() )
            
            self._new_options.SetInteger( 'duplicate_filter_max_batch_size', self._duplicate_filter_max_batch_size.value() )
            
        
    
    class _ExternalProgramsPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            mime_panel = ClientGUICommon.StaticBox( self, '\'open externally\' launch paths' )
            
            self._web_browser_path = QW.QLineEdit( mime_panel )
            
            self._mime_launch_listctrl = ClientGUIListCtrl.BetterListCtrl( mime_panel, CGLC.COLUMN_LIST_EXTERNAL_PROGRAMS.ID, 15, self._ConvertMimeToListCtrlTuples, activation_callback = self._EditMimeLaunch )
            
            #
            
            web_browser_path = self._new_options.GetNoneableString( 'web_browser_path' )
            
            if web_browser_path is not None:
                
                self._web_browser_path.setText( web_browser_path )
                
            
            for mime in HC.SEARCHABLE_MIMES:
                
                launch_path = self._new_options.GetMimeLaunch( mime )
                
                self._mime_launch_listctrl.AddDatas( [ ( mime, launch_path ) ] )
                
            
            self._mime_launch_listctrl.Sort()
            
            #
            
            vbox = QP.VBoxLayout()
            
            text = 'Setting a specific web browser path here--like \'C:\\program files\\firefox\\firefox.exe "%path%"\'--can help with the \'share->open->in web browser\' command, which is buggy working with OS defaults, particularly on Windows. It also fixes #anchors, which are dropped in some OSes using default means. Use the same %path% format for the \'open externally\' commands below.'
            
            st = ClientGUICommon.BetterStaticText( mime_panel, text )
            st.setWordWrap( True )
            
            mime_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Manual web browser launch path: ', self._web_browser_path ) )
            
            gridbox = ClientGUICommon.WrapInGrid( mime_panel, rows )
            
            mime_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            mime_panel.Add( self._mime_launch_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            QP.AddToLayout( vbox, mime_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def _ConvertMimeToListCtrlTuples( self, data ):
            
            ( mime, launch_path ) = data
            
            pretty_mime = HC.mime_string_lookup[ mime ]
            
            if launch_path is None:
                
                pretty_launch_path = 'default: {}'.format( HydrusPaths.GetDefaultLaunchPath() )
                
            else:
                
                pretty_launch_path = launch_path
                
            
            display_tuple = ( pretty_mime, pretty_launch_path )
            sort_tuple = display_tuple
            
            return ( display_tuple, sort_tuple )
            
        
        def _EditMimeLaunch( self ):
            
            for ( mime, launch_path ) in self._mime_launch_listctrl.GetData( only_selected = True ):
                
                message = 'Enter the new launch path for {}'.format( HC.mime_string_lookup[ mime ] )
                message += os.linesep * 2
                message += 'Hydrus will insert the file\'s full path wherever you put %path%, even multiple times!'
                message += os.linesep * 2
                message += 'Set as blank to reset to default.'
                
                if launch_path is None:
                    
                    default = 'program "%path%"'
                    
                else:
                    
                    default = launch_path
                    
                
                with ClientGUIDialogs.DialogTextEntry( self, message, default = default, allow_blank = True ) as dlg:
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        new_launch_path = dlg.GetValue()
                        
                        if new_launch_path == '':
                            
                            new_launch_path = None
                            
                        
                        if new_launch_path not in ( launch_path, default ):
                            
                            self._mime_launch_listctrl.DeleteDatas( [ ( mime, launch_path ) ] )
                            
                            self._mime_launch_listctrl.AddDatas( [ ( mime, new_launch_path ) ] )
                            
                        
                    else:
                        
                        break
                        
                    
                
            
            self._mime_launch_listctrl.Sort()
            
        
        def UpdateOptions( self ):
            
            web_browser_path = self._web_browser_path.text()
            
            if web_browser_path == '':
                
                web_browser_path = None
                
            
            self._new_options.SetNoneableString( 'web_browser_path', web_browser_path )
            
            for ( mime, launch_path ) in self._mime_launch_listctrl.GetData():
                
                self._new_options.SetMimeLaunch( mime, launch_path )
                
            
        
    
    class _FilesAndTrashPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            self._export_location = QP.DirPickerCtrl( self )
            
            self._prefix_hash_when_copying = QW.QCheckBox( self )
            self._prefix_hash_when_copying.setToolTip( 'If you often paste hashes into boorus, check this to automatically prefix with the type, like "md5:2496dabcbd69e3c56a5d8caabb7acde5".' )
            
            self._delete_to_recycle_bin = QW.QCheckBox( self )
            
            self._confirm_trash = QW.QCheckBox( self )
            self._confirm_archive = QW.QCheckBox( self )
            
            self._remove_filtered_files = QW.QCheckBox( self )
            self._remove_trashed_files = QW.QCheckBox( self )
            
            self._trash_max_age = ClientGUICommon.NoneableSpinCtrl( self, '', none_phrase = 'no age limit', min = 0, max = 8640 )
            self._trash_max_size = ClientGUICommon.NoneableSpinCtrl( self, '', none_phrase = 'no size limit', min = 0, max = 20480 )
            
            delete_lock_panel = ClientGUICommon.StaticBox( self, 'delete lock' )
            
            self._delete_lock_for_archived_files = QW.QCheckBox( delete_lock_panel )
            
            advanced_file_deletion_panel = ClientGUICommon.StaticBox( self, 'advanced file deletion and custom reasons' )
            
            self._use_advanced_file_deletion_dialog = QW.QCheckBox( advanced_file_deletion_panel )
            self._use_advanced_file_deletion_dialog.setToolTip( 'If this is set, the client will present a more complicated file deletion confirmation dialog that will permit you to set your own deletion reason and perform \'clean\' deletes that leave no deletion record (making later re-import easier).' )
            
            self._remember_last_advanced_file_deletion_special_action = QW.QCheckBox( advanced_file_deletion_panel )
            self._remember_last_advanced_file_deletion_special_action.setToolTip( 'This will try to remember and restore the last action you set, whether that was trash, physical delete, or physical delete and clear history.')
            
            self._remember_last_advanced_file_deletion_reason = QW.QCheckBox( advanced_file_deletion_panel )
            self._remember_last_advanced_file_deletion_reason.setToolTip( 'This will remember and restore the last reason you set for a delete.' )
            
            self._advanced_file_deletion_reasons = ClientGUIListBoxes.QueueListBox( advanced_file_deletion_panel, 5, str, add_callable = self._AddAFDR, edit_callable = self._EditAFDR )
            
            #
            
            if HC.options[ 'export_path' ] is not None:
                
                abs_path = HydrusPaths.ConvertPortablePathToAbsPath( HC.options[ 'export_path' ] )
                
                if abs_path is not None:
                    
                    self._export_location.SetPath( abs_path )
                    
                
            
            self._prefix_hash_when_copying.setChecked( self._new_options.GetBoolean( 'prefix_hash_when_copying' ) )
            
            self._delete_to_recycle_bin.setChecked( HC.options[ 'delete_to_recycle_bin' ] )
            
            self._confirm_trash.setChecked( HC.options[ 'confirm_trash' ] )
            
            self._confirm_archive.setChecked( HC.options[ 'confirm_archive' ] )
            
            self._remove_filtered_files.setChecked( HC.options[ 'remove_filtered_files' ] )
            self._remove_trashed_files.setChecked( HC.options[ 'remove_trashed_files' ] )
            self._trash_max_age.SetValue( HC.options[ 'trash_max_age' ] )
            self._trash_max_size.SetValue( HC.options[ 'trash_max_size' ] )
            
            self._delete_lock_for_archived_files.setChecked( self._new_options.GetBoolean( 'delete_lock_for_archived_files' ) )
            
            self._use_advanced_file_deletion_dialog.setChecked( self._new_options.GetBoolean( 'use_advanced_file_deletion_dialog' ) )
            
            self._use_advanced_file_deletion_dialog.clicked.connect( self._UpdateAdvancedControls )
            
            self._remember_last_advanced_file_deletion_special_action.setChecked( HG.client_controller.new_options.GetBoolean( 'remember_last_advanced_file_deletion_special_action' ) )
            self._remember_last_advanced_file_deletion_reason.setChecked( HG.client_controller.new_options.GetBoolean( 'remember_last_advanced_file_deletion_reason' ) )
            
            self._advanced_file_deletion_reasons.AddDatas( self._new_options.GetStringList( 'advanced_file_deletion_reasons' ) )
            
            self._UpdateAdvancedControls()
            
            #
            
            vbox = QP.VBoxLayout()
            
            text = 'If you set the default export directory blank, the client will use \'hydrus_export\' under the current user\'s home directory.'
            
            QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self,text), CC.FLAGS_CENTER )
            
            rows = []
            
            rows.append( ( 'When copying a file hashes, prefix with booru-friendly hash type: ', self._prefix_hash_when_copying ) )
            rows.append( ( 'Confirm sending files to trash: ', self._confirm_trash ) )
            rows.append( ( 'Confirm sending more than one file to archive or inbox: ', self._confirm_archive ) )
            rows.append( ( 'When deleting files or folders, send them to the OS\'s recycle bin: ', self._delete_to_recycle_bin ) )
            rows.append( ( 'Remove files from view when they are filtered: ', self._remove_filtered_files ) )
            rows.append( ( 'Remove files from view when they are sent to the trash: ', self._remove_trashed_files ) )
            rows.append( ( 'Number of hours a file can be in the trash before being deleted: ', self._trash_max_age ) )
            rows.append( ( 'Maximum size of trash (MB): ', self._trash_max_size ) )
            rows.append( ( 'Default export directory: ', self._export_location ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Do not permit archived files to be trashed or deleted: ', self._delete_lock_for_archived_files ) )
            
            gridbox = ClientGUICommon.WrapInGrid( delete_lock_panel, rows )
            
            delete_lock_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, delete_lock_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Use the advanced file deletion dialog: ', self._use_advanced_file_deletion_dialog ) )
            rows.append( ( 'Remember the last action: ', self._remember_last_advanced_file_deletion_special_action ) )
            rows.append( ( 'Remember the last reason: ', self._remember_last_advanced_file_deletion_reason ) )
            
            gridbox = ClientGUICommon.WrapInGrid( advanced_file_deletion_panel, rows )
            
            advanced_file_deletion_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            advanced_file_deletion_panel.Add( self._advanced_file_deletion_reasons, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            QP.AddToLayout( vbox, advanced_file_deletion_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def _AddAFDR( self ):
            
            reason = 'I do not like the file.'
            
            return self._EditAFDR( reason )
            
        
        def _EditAFDR( self, reason ):
            
            with ClientGUIDialogs.DialogTextEntry( self, 'enter the reason', default = reason, allow_blank = False ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    reason = dlg.GetValue()
                    
                    return reason
                    
                else:
                    
                    raise HydrusExceptions.VetoException()
                    
                
            
        
        def _UpdateAdvancedControls( self ):
            
            advanced_enabled = self._use_advanced_file_deletion_dialog.isChecked()
            
            self._remember_last_advanced_file_deletion_special_action.setEnabled( advanced_enabled )
            self._remember_last_advanced_file_deletion_reason.setEnabled( advanced_enabled )
            self._advanced_file_deletion_reasons.setEnabled( advanced_enabled )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'export_path' ] = HydrusPaths.ConvertAbsPathToPortablePath( self._export_location.GetPath() )
            
            self._new_options.SetBoolean( 'prefix_hash_when_copying', self._prefix_hash_when_copying.isChecked() )
            
            HC.options[ 'delete_to_recycle_bin' ] = self._delete_to_recycle_bin.isChecked()
            HC.options[ 'confirm_trash' ] = self._confirm_trash.isChecked()
            HC.options[ 'confirm_archive' ] = self._confirm_archive.isChecked()
            HC.options[ 'remove_filtered_files' ] = self._remove_filtered_files.isChecked()
            HC.options[ 'remove_trashed_files' ] = self._remove_trashed_files.isChecked()
            HC.options[ 'trash_max_age' ] = self._trash_max_age.GetValue()
            HC.options[ 'trash_max_size' ] = self._trash_max_size.GetValue()
            
            self._new_options.SetBoolean( 'delete_lock_for_archived_files', self._delete_lock_for_archived_files.isChecked() )
            
            self._new_options.SetBoolean( 'use_advanced_file_deletion_dialog', self._use_advanced_file_deletion_dialog.isChecked() )
            
            self._new_options.SetStringList( 'advanced_file_deletion_reasons', self._advanced_file_deletion_reasons.GetData() )
            
            HG.client_controller.new_options.SetBoolean( 'remember_last_advanced_file_deletion_special_action', self._remember_last_advanced_file_deletion_special_action.isChecked() )
            HG.client_controller.new_options.SetBoolean( 'remember_last_advanced_file_deletion_reason', self._remember_last_advanced_file_deletion_reason.isChecked() )
            
        
    
    class _FileViewingStatisticsPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            self._file_viewing_statistics_active = QW.QCheckBox( self )
            self._file_viewing_statistics_active_on_dupe_filter = QW.QCheckBox( self )
            self._file_viewing_statistics_media_min_time = ClientGUICommon.NoneableSpinCtrl( self )
            self._file_viewing_statistics_media_max_time = ClientGUICommon.NoneableSpinCtrl( self )
            self._file_viewing_statistics_preview_min_time = ClientGUICommon.NoneableSpinCtrl( self )
            self._file_viewing_statistics_preview_max_time = ClientGUICommon.NoneableSpinCtrl( self )
            
            self._file_viewing_stats_menu_display = ClientGUICommon.BetterChoice( self )
            
            self._file_viewing_stats_menu_display.addItem( 'do not show', CC.FILE_VIEWING_STATS_MENU_DISPLAY_NONE )
            self._file_viewing_stats_menu_display.addItem( 'show media', CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_ONLY )
            self._file_viewing_stats_menu_display.addItem( 'show media, and put preview in a submenu', CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_IN_SUBMENU )
            self._file_viewing_stats_menu_display.addItem( 'show media and preview in two lines', CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_STACKED )
            self._file_viewing_stats_menu_display.addItem( 'show media and preview combined', CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_SUMMED )
            
            #
            
            self._file_viewing_statistics_active.setChecked( self._new_options.GetBoolean( 'file_viewing_statistics_active' ) )
            self._file_viewing_statistics_active_on_dupe_filter.setChecked( self._new_options.GetBoolean( 'file_viewing_statistics_active_on_dupe_filter' ) )
            self._file_viewing_statistics_media_min_time.SetValue( self._new_options.GetNoneableInteger( 'file_viewing_statistics_media_min_time' ) )
            self._file_viewing_statistics_media_max_time.SetValue( self._new_options.GetNoneableInteger( 'file_viewing_statistics_media_max_time' ) )
            self._file_viewing_statistics_preview_min_time.SetValue( self._new_options.GetNoneableInteger( 'file_viewing_statistics_preview_min_time' ) )
            self._file_viewing_statistics_preview_max_time.SetValue( self._new_options.GetNoneableInteger( 'file_viewing_statistics_preview_max_time' ) )
            
            self._file_viewing_stats_menu_display.SetValue( self._new_options.GetInteger( 'file_viewing_stats_menu_display' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Enable file viewing statistics tracking?:', self._file_viewing_statistics_active ) )
            rows.append( ( 'Enable file viewing statistics tracking on the duplicate filter?:', self._file_viewing_statistics_active_on_dupe_filter ) )
            rows.append( ( 'Min time to view on media viewer to count as a view (seconds):', self._file_viewing_statistics_media_min_time ) )
            rows.append( ( 'Cap any view on the media viewer to this maximum time (seconds):', self._file_viewing_statistics_media_max_time ) )
            rows.append( ( 'Min time to view on preview viewer to count as a view (seconds):', self._file_viewing_statistics_preview_min_time ) )
            rows.append( ( 'Cap any view on the preview viewer to this maximum time (seconds):', self._file_viewing_statistics_preview_max_time ) )
            rows.append( ( 'Show media/preview viewing stats on media right-click menus?:', self._file_viewing_stats_menu_display ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'file_viewing_statistics_active', self._file_viewing_statistics_active.isChecked() )
            self._new_options.SetBoolean( 'file_viewing_statistics_active_on_dupe_filter', self._file_viewing_statistics_active_on_dupe_filter.isChecked() )
            self._new_options.SetNoneableInteger( 'file_viewing_statistics_media_min_time', self._file_viewing_statistics_media_min_time.GetValue() )
            self._new_options.SetNoneableInteger( 'file_viewing_statistics_media_max_time', self._file_viewing_statistics_media_max_time.GetValue() )
            self._new_options.SetNoneableInteger( 'file_viewing_statistics_preview_min_time', self._file_viewing_statistics_preview_min_time.GetValue() )
            self._new_options.SetNoneableInteger( 'file_viewing_statistics_preview_max_time', self._file_viewing_statistics_preview_max_time.GetValue() )
            
            self._new_options.SetInteger( 'file_viewing_stats_menu_display', self._file_viewing_stats_menu_display.GetValue() )
            
        
    
    class _GUIPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._main_gui_panel = ClientGUICommon.StaticBox( self, 'main window' )
            
            self._app_display_name = QW.QLineEdit( self._main_gui_panel )
            self._app_display_name.setToolTip( 'This is placed in every window title, with current version name. Rename if you want to personalise or differentiate.' )
            
            self._confirm_client_exit = QW.QCheckBox( self._main_gui_panel )
            
            self._activate_window_on_tag_search_page_activation = QW.QCheckBox( self._main_gui_panel )
            
            tt = 'Middle-clicking one or more tags in a taglist will cause the creation of a new search page for those tags. If you do this from the media viewer or a child manage tags dialog, do you want to switch immediately to the main gui?'
            
            self._activate_window_on_tag_search_page_activation.setToolTip( tt )
            
            #
            
            self._misc_panel = ClientGUICommon.StaticBox( self, 'misc' )
            
            self._always_show_iso_time = QW.QCheckBox( self._misc_panel )
            tt = 'In many places across the program (typically import status lists), the client will state a timestamp as "5 days ago". If you would prefer a standard ISO string, like "2018-03-01 12:40:23", check this.'
            self._always_show_iso_time.setToolTip( tt )
            
            self._human_bytes_sig_figs = QP.MakeQSpinBox( self._misc_panel, min = 1, max = 6 )
            self._human_bytes_sig_figs.setToolTip( 'When the program presents a bytes size above 1KB, like 21.3KB or 4.11GB, how many total digits do we want in the number? 2 or 3 is best.')
            
            self._discord_dnd_fix = QW.QCheckBox( self._misc_panel )
            self._discord_dnd_fix.setToolTip( 'This makes small file drag-and-drops a little laggier in exchange for discord support.' )
            
            self._discord_dnd_filename_pattern = QW.QLineEdit( self._misc_panel )
            self._discord_dnd_filename_pattern.setToolTip( 'When discord DnD is enabled, this will use this export phrase to rename your files. If no filename can be generated, hash will be used instead.' )
            
            self._secret_discord_dnd_fix = QW.QCheckBox( self._misc_panel )
            self._secret_discord_dnd_fix.setToolTip( 'This saves the lag but is potentially dangerous, as it (may) treat the from-db-files-drag as a move rather than a copy and hence only works when the drop destination will not consume the files. It requires an additional secret Alternate key to unlock.' )
            
            self._do_macos_debug_dialog_menus = QW.QCheckBox( self._misc_panel )
            self._do_macos_debug_dialog_menus.setToolTip( 'There is a bug in Big Sur Qt regarding interacting with some menus in dialogs. The menus show but cannot be clicked. This shows the menu items in a debug dialog instead.' )
            
            self._use_qt_file_dialogs = QW.QCheckBox( self._misc_panel )
            self._use_qt_file_dialogs.setToolTip( 'If you get crashes opening file/directory dialogs, try this.' )
            
            #
            
            frame_locations_panel = ClientGUICommon.StaticBox( self, 'frame locations' )
            
            self._frame_locations = ClientGUIListCtrl.BetterListCtrl( frame_locations_panel, CGLC.COLUMN_LIST_FRAME_LOCATIONS.ID, 15, data_to_tuples_func = lambda x: (self._GetPrettyFrameLocationInfo( x ), self._GetPrettyFrameLocationInfo( x )), activation_callback = self.EditFrameLocations )
            
            self._frame_locations_edit_button = QW.QPushButton( 'edit', frame_locations_panel )
            self._frame_locations_edit_button.clicked.connect( self.EditFrameLocations )
            
            #
            
            self._new_options = HG.client_controller.new_options
            
            self._app_display_name.setText( self._new_options.GetString( 'app_display_name' ) )
            
            self._confirm_client_exit.setChecked( HC.options[ 'confirm_client_exit' ] )
            
            self._activate_window_on_tag_search_page_activation.setChecked( self._new_options.GetBoolean( 'activate_window_on_tag_search_page_activation' ) )
            
            self._always_show_iso_time.setChecked( self._new_options.GetBoolean( 'always_show_iso_time' ) )
            
            self._human_bytes_sig_figs.setValue( self._new_options.GetInteger( 'human_bytes_sig_figs' ) )
            
            self._discord_dnd_fix.setChecked( self._new_options.GetBoolean( 'discord_dnd_fix' ) )
            
            self._discord_dnd_filename_pattern.setText( self._new_options.GetString( 'discord_dnd_filename_pattern' ) )
            
            self._secret_discord_dnd_fix.setChecked( self._new_options.GetBoolean( 'secret_discord_dnd_fix' ) )
            
            self._do_macos_debug_dialog_menus.setChecked( self._new_options.GetBoolean( 'do_macos_debug_dialog_menus' ) )
            
            self._use_qt_file_dialogs.setChecked( self._new_options.GetBoolean( 'use_qt_file_dialogs' ) )
            
            for ( name, info ) in self._new_options.GetFrameLocations():
                
                listctrl_list = QP.ListsToTuples( [ name ] + list( info ) )
                
                self._frame_locations.AddDatas( ( listctrl_list, ) )
                
            
            #self._frame_locations.SortListItems( col = 0 )
            
            #
            
            rows = []
            
            rows.append( ( 'Application display name: ', self._app_display_name ) )
            rows.append( ( 'Confirm client exit: ', self._confirm_client_exit ) )
            rows.append( ( 'Switch to main window when opening tag search page from media viewer: ', self._activate_window_on_tag_search_page_activation ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._main_gui_panel, rows )
            
            self._main_gui_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Prefer ISO time ("2018-03-01 12:40:23") to "5 days ago": ', self._always_show_iso_time ) )
            rows.append( ( 'BUGFIX: Discord file drag-and-drop fix (works for <=25, <200MB file DnDs): ', self._discord_dnd_fix ) )
            rows.append( ( 'Discord drag-and-drop filename pattern: ', self._discord_dnd_filename_pattern ) )
            rows.append( ( 'Export pattern shortcuts: ', ClientGUICommon.ExportPatternButton( self ) ) )
            rows.append( ( 'EXPERIMENTAL: Bytes strings >1KB pseudo significant figures: ', self._human_bytes_sig_figs ) )
            rows.append( ( 'EXPERIMENTAL BUGFIX: Secret discord file drag-and-drop fix: ', self._secret_discord_dnd_fix ) )
            rows.append( ( 'BUGFIX: If on macOS, show dialog menus in a debug menu: ', self._do_macos_debug_dialog_menus ) )
            rows.append( ( 'ANTI-CRASH BUGFIX: Use Qt file/directory selection dialogs, rather than OS native: ', self._use_qt_file_dialogs ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            self._misc_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            text = 'Here you can override the current and default values for many frame and dialog sizing and positioning variables.'
            text += os.linesep
            text += 'This is an advanced control. If you aren\'t confident of what you are doing here, come back later!'
            
            frame_locations_panel.Add( QW.QLabel( text, frame_locations_panel ), CC.FLAGS_EXPAND_PERPENDICULAR )
            frame_locations_panel.Add( self._frame_locations, CC.FLAGS_EXPAND_BOTH_WAYS )
            frame_locations_panel.Add( self._frame_locations_edit_button, CC.FLAGS_ON_RIGHT )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._main_gui_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, self._misc_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, frame_locations_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def _GetPrettyFrameLocationInfo( self, listctrl_list ):
            
            pretty_listctrl_list = []
            
            for item in listctrl_list:
                
                pretty_listctrl_list.append( str( item ) )
                
            
            return pretty_listctrl_list
            
        
        def EditFrameLocations( self ):
            
            for listctrl_list in self._frame_locations.GetData( only_selected = True ):
                
                title = 'set frame location information'
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                    
                    panel = ClientGUIScrolledPanelsEdit.EditFrameLocationPanel( dlg, listctrl_list )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        new_listctrl_list = panel.GetValue()
                        
                        self._frame_locations.ReplaceData( listctrl_list, new_listctrl_list )
                        
                    
                
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'confirm_client_exit' ] = self._confirm_client_exit.isChecked()
            
            self._new_options.SetBoolean( 'always_show_iso_time', self._always_show_iso_time.isChecked() )
            
            self._new_options.SetInteger( 'human_bytes_sig_figs', self._human_bytes_sig_figs.value() )
            
            self._new_options.SetBoolean( 'activate_window_on_tag_search_page_activation', self._activate_window_on_tag_search_page_activation.isChecked() )
            
            app_display_name = self._app_display_name.text()
            
            if app_display_name == '':
                
                app_display_name = 'hydrus client'
                
            
            self._new_options.SetString( 'app_display_name', app_display_name )
            
            self._new_options.SetBoolean( 'discord_dnd_fix', self._discord_dnd_fix.isChecked() )
            self._new_options.SetString( 'discord_dnd_filename_pattern', self._discord_dnd_filename_pattern.text() )
            self._new_options.SetBoolean( 'secret_discord_dnd_fix', self._secret_discord_dnd_fix.isChecked() )
            self._new_options.SetBoolean( 'do_macos_debug_dialog_menus', self._do_macos_debug_dialog_menus.isChecked() )
            self._new_options.SetBoolean( 'use_qt_file_dialogs', self._use_qt_file_dialogs.isChecked() )
            
            for listctrl_list in self._frame_locations.GetData():
                
                ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = listctrl_list
                
                self._new_options.SetFrameLocation( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
                
            
        
    
    class _GUIPagesPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            self._sessions_panel = ClientGUICommon.StaticBox( self, 'sessions' )
            
            self._default_gui_session = QW.QComboBox( self._sessions_panel )
            
            self._last_session_save_period_minutes = QP.MakeQSpinBox( self._sessions_panel, min = 1, max = 1440 )
            
            self._only_save_last_session_during_idle = QW.QCheckBox( self._sessions_panel )
            
            self._only_save_last_session_during_idle.setToolTip( 'This is useful if you usually have a very large session (200,000+ files/import items open) and a client that is always on.' )
            
            self._number_of_gui_session_backups = QP.MakeQSpinBox( self._sessions_panel, min = 1, max = 32 )
            
            self._number_of_gui_session_backups.setToolTip( 'The client keeps multiple rolling backups of your gui sessions. If you have very large sessions, you might like to reduce this number.' )
            
            self._show_session_size_warnings = QW.QCheckBox( self._sessions_panel )
            
            self._show_session_size_warnings.setToolTip( 'This will give you a once-per-boot warning popup if your active session contains more than 10M weight.' )
            
            #
            
            self._pages_panel = ClientGUICommon.StaticBox( self, 'pages' )
            
            self._default_new_page_goes = ClientGUICommon.BetterChoice( self._pages_panel )
            
            for value in [ CC.NEW_PAGE_GOES_FAR_LEFT, CC.NEW_PAGE_GOES_LEFT_OF_CURRENT, CC.NEW_PAGE_GOES_RIGHT_OF_CURRENT, CC.NEW_PAGE_GOES_FAR_RIGHT ]:
                
                self._default_new_page_goes.addItem( CC.new_page_goes_string_lookup[ value], value )
                
            
            self._notebook_tab_alignment = ClientGUICommon.BetterChoice( self._pages_panel )
            
            for value in [ CC.DIRECTION_UP, CC.DIRECTION_LEFT, CC.DIRECTION_RIGHT, CC.DIRECTION_DOWN ]:
                
                self._notebook_tab_alignment.addItem( CC.directions_alignment_string_lookup[ value ], value )
                
            
            self._total_pages_warning = QP.MakeQSpinBox( self._pages_panel, min=5, max=65565 )
            
            tt = 'If you have a gigantic session, or you have very page-spammy subscriptions, you can try boosting this, but be warned it may lead to resource limit crashes. The best solution to a large session is to make it smaller!'
            
            self._total_pages_warning.setToolTip( tt )
            
            self._reverse_page_shift_drag_behaviour = QW.QCheckBox( self._pages_panel )
            self._reverse_page_shift_drag_behaviour.setToolTip( 'By default, holding down shift when you drop off a page tab means the client will not \'chase\' the page tab. This makes this behaviour default, with shift-drop meaning to chase.' )
            
            #
            
            self._page_names_panel = ClientGUICommon.StaticBox( self._pages_panel, 'page tab names' )
            
            self._max_page_name_chars = QP.MakeQSpinBox( self._page_names_panel, min=1, max=256 )
            self._elide_page_tab_names = QW.QCheckBox( self._page_names_panel )
            
            self._page_file_count_display = ClientGUICommon.BetterChoice( self._page_names_panel )
            
            for display_type in ( CC.PAGE_FILE_COUNT_DISPLAY_ALL, CC.PAGE_FILE_COUNT_DISPLAY_ONLY_IMPORTERS, CC.PAGE_FILE_COUNT_DISPLAY_NONE ):
                
                self._page_file_count_display.addItem( CC.page_file_count_display_string_lookup[ display_type], display_type )
                
            
            self._import_page_progress_display = QW.QCheckBox( self._page_names_panel )
            
            #
            
            self._controls_panel = ClientGUICommon.StaticBox( self, 'controls' )
            
            self._set_search_focus_on_page_change = QW.QCheckBox( self._controls_panel )
            
            self._hide_preview = QW.QCheckBox( self._controls_panel )
            
            #
            
            gui_session_names = HG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION_CONTAINER )
            
            if CC.LAST_SESSION_SESSION_NAME not in gui_session_names:
                
                gui_session_names.insert( 0, CC.LAST_SESSION_SESSION_NAME )
                
            
            self._default_gui_session.addItem( 'just a blank page', None )
            
            for name in gui_session_names:
                
                self._default_gui_session.addItem( name, name )
                
            
            try:
                
                QP.SetStringSelection( self._default_gui_session, HC.options['default_gui_session'] )
                
            except:
                
                self._default_gui_session.setCurrentIndex( 0 )
                
            
            self._last_session_save_period_minutes.setValue( self._new_options.GetInteger( 'last_session_save_period_minutes' ) )
            
            self._only_save_last_session_during_idle.setChecked( self._new_options.GetBoolean( 'only_save_last_session_during_idle' ) )
            
            self._number_of_gui_session_backups.setValue( self._new_options.GetInteger( 'number_of_gui_session_backups' ) )
            
            self._show_session_size_warnings.setChecked( self._new_options.GetBoolean( 'show_session_size_warnings' ) )
            
            self._default_new_page_goes.SetValue( self._new_options.GetInteger( 'default_new_page_goes' ) )
            
            self._notebook_tab_alignment.SetValue( self._new_options.GetInteger( 'notebook_tab_alignment' ) )
            
            self._max_page_name_chars.setValue( self._new_options.GetInteger( 'max_page_name_chars' ) )
            
            self._elide_page_tab_names.setChecked( self._new_options.GetBoolean( 'elide_page_tab_names' ) )
            
            self._page_file_count_display.SetValue( self._new_options.GetInteger( 'page_file_count_display' ) )
            
            self._import_page_progress_display.setChecked( self._new_options.GetBoolean( 'import_page_progress_display' ) )
            
            self._total_pages_warning.setValue( self._new_options.GetInteger( 'total_pages_warning' ) )
            
            self._reverse_page_shift_drag_behaviour.setChecked( self._new_options.GetBoolean( 'reverse_page_shift_drag_behaviour' ) )
            
            self._set_search_focus_on_page_change.setChecked( self._new_options.GetBoolean( 'set_search_focus_on_page_change' ) )
            
            self._hide_preview.setChecked( HC.options[ 'hide_preview' ] )
            
            #
            
            rows = []
            
            rows.append( ( 'Default session on startup: ', self._default_gui_session ) )
            rows.append( ( 'If \'last session\' above, autosave it how often (minutes)?', self._last_session_save_period_minutes ) )
            rows.append( ( 'If \'last session\' above, only autosave during idle time?', self._only_save_last_session_during_idle ) )
            rows.append( ( 'Number of session backups to keep: ', self._number_of_gui_session_backups ) )
            rows.append( ( 'Show warning popup if session size exceeds 10,000,000: ', self._show_session_size_warnings ) )
            
            sessions_gridbox = ClientGUICommon.WrapInGrid( self._sessions_panel, rows )
            
            self._sessions_panel.Add( sessions_gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            rows = []
            
            rows.append( ( 'By default, put new page tabs on: ', self._default_new_page_goes ) )
            rows.append( ( 'Notebook tab alignment: ', self._notebook_tab_alignment ) )
            rows.append( ( 'Reverse page tab shift-drag behaviour: ', self._reverse_page_shift_drag_behaviour ) )
            rows.append( ( 'Warn at this many total pages: ', self._total_pages_warning ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._pages_panel, rows )
            
            rows = []
            
            rows.append( ( 'Max characters to display in a page name: ', self._max_page_name_chars ) )
            rows.append( ( 'When there are too many tabs to fit, \'...\' elide their names so they fit: ', self._elide_page_tab_names ) )
            rows.append( ( 'Show page file count after its name: ', self._page_file_count_display ) )
            rows.append( ( 'Show import page x/y progress after its name: ', self._import_page_progress_display ) )
            
            page_names_gridbox = ClientGUICommon.WrapInGrid( self._page_names_panel, rows )
            
            label = 'If you have enough pages in a row, left/right arrows will appear to navigate them back and forth.'
            label += os.linesep
            label += 'Due to an unfortunate Qt issue, the tab bar will scroll so the current tab is right-most visible whenever a page is renamed.'
            label += os.linesep
            label += 'Therefore, if you set pages to have current file count or import progress in their name (which will update from time to time), do not put import pages in a long row of tabs, as it will reset scroll position on every progress update.'
            label += os.linesep
            label += 'Just make some nested \'page of pages\' so they are not all in the same row.'
            
            st = ClientGUICommon.BetterStaticText( self._page_names_panel, label )
            
            st.setWordWrap( True )
            
            self._page_names_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._page_names_panel.Add( page_names_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self._pages_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            self._pages_panel.Add( self._page_names_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'When switching to a page, focus its text input field (if any): ', self._set_search_focus_on_page_change ) )
            rows.append( ( 'Hide the bottom-left preview window: ', self._hide_preview ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._controls_panel, rows )
            
            self._controls_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._sessions_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, self._pages_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._controls_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'default_gui_session' ] = self._default_gui_session.currentText()
            
            self._new_options.SetInteger( 'notebook_tab_alignment', self._notebook_tab_alignment.GetValue() )
            
            self._new_options.SetInteger( 'last_session_save_period_minutes', self._last_session_save_period_minutes.value() )
            
            self._new_options.SetInteger( 'number_of_gui_session_backups', self._number_of_gui_session_backups.value() )
            
            self._new_options.SetBoolean( 'show_session_size_warnings', self._show_session_size_warnings.isChecked() )
            
            self._new_options.SetBoolean( 'only_save_last_session_during_idle', self._only_save_last_session_during_idle.isChecked() )
            
            self._new_options.SetInteger( 'default_new_page_goes', self._default_new_page_goes.GetValue() )
            
            self._new_options.SetInteger( 'max_page_name_chars', self._max_page_name_chars.value() )
            
            self._new_options.SetBoolean( 'elide_page_tab_names', self._elide_page_tab_names.isChecked() )
            
            self._new_options.SetInteger( 'page_file_count_display', self._page_file_count_display.GetValue() )
            self._new_options.SetBoolean( 'import_page_progress_display', self._import_page_progress_display.isChecked() )
            
            self._new_options.SetInteger( 'total_pages_warning', self._total_pages_warning.value() )
            
            self._new_options.SetBoolean( 'reverse_page_shift_drag_behaviour', self._reverse_page_shift_drag_behaviour.isChecked() )
            
            self._new_options.SetBoolean( 'set_search_focus_on_page_change', self._set_search_focus_on_page_change.isChecked() )
            
            HC.options[ 'hide_preview' ] = self._hide_preview.isChecked()
            
        
    
    class _ImportingPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            default_fios = ClientGUICommon.StaticBox( self, 'default file import options' )
            
            show_downloader_options = True
            
            quiet_file_import_options = self._new_options.GetDefaultFileImportOptions( 'quiet' )
            
            self._quiet_fios = ClientGUIImport.FileImportOptionsButton( default_fios, quiet_file_import_options, show_downloader_options )
            
            loud_file_import_options = self._new_options.GetDefaultFileImportOptions( 'loud' )
            
            self._loud_fios = ClientGUIImport.FileImportOptionsButton( default_fios, loud_file_import_options, show_downloader_options )
            
            #
            
            rows = []
            
            rows.append( ( 'For \'quiet\' import contexts like import folders and subscriptions:', self._quiet_fios ) )
            rows.append( ( 'For import contexts that work on pages:', self._loud_fios ) )
            
            gridbox = ClientGUICommon.WrapInGrid( default_fios, rows )
            
            default_fios.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, default_fios, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetDefaultFileImportOptions( 'quiet', self._quiet_fios.GetValue() )
            self._new_options.SetDefaultFileImportOptions( 'loud', self._loud_fios.GetValue() )
            
        
    
    class _MaintenanceAndProcessingPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            self._jobs_panel = ClientGUICommon.StaticBox( self, 'when to run high cpu jobs' )
            self._file_maintenance_panel = ClientGUICommon.StaticBox( self, 'file maintenance' )
            
            self._idle_panel = ClientGUICommon.StaticBox( self._jobs_panel, 'idle' )
            self._shutdown_panel = ClientGUICommon.StaticBox( self._jobs_panel, 'shutdown' )
            
            #
            
            self._idle_normal = QW.QCheckBox( self._idle_panel )
            self._idle_normal.clicked.connect( self._EnableDisableIdleNormal )
            
            self._idle_period = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, '', min = 1, max = 1000, multiplier = 60, unit = 'minutes', none_phrase = 'ignore normal browsing' )
            self._idle_mouse_period = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, '', min = 1, max = 1000, multiplier = 60, unit = 'minutes', none_phrase = 'ignore mouse movements' )
            self._idle_mode_client_api_timeout = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, '', min = 1, max = 1000, multiplier = 60, unit = 'minutes', none_phrase = 'ignore client api' )
            self._system_busy_cpu_percent = QP.MakeQSpinBox( self._idle_panel, min = 5, max = 99 )
            self._system_busy_cpu_count = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, min = 1, max = 64, unit = 'cores', none_phrase = 'ignore cpu usage' )
            
            #
            
            self._idle_shutdown = ClientGUICommon.BetterChoice( self._shutdown_panel )
            
            for idle_id in ( CC.IDLE_NOT_ON_SHUTDOWN, CC.IDLE_ON_SHUTDOWN, CC.IDLE_ON_SHUTDOWN_ASK_FIRST ):
                
                self._idle_shutdown.addItem( CC.idle_string_lookup[ idle_id], idle_id )
                
            
            self._idle_shutdown.currentIndexChanged.connect( self._EnableDisableIdleShutdown )
            
            self._idle_shutdown_max_minutes = QP.MakeQSpinBox( self._shutdown_panel, min=1, max=1440 )
            self._shutdown_work_period = ClientGUITime.TimeDeltaButton( self._shutdown_panel, min = 60, days = True, hours = True, minutes = True )
            
            #
            
            min_unit_value = 1
            max_unit_value = 1000
            min_time_delta = 1
            
            self._file_maintenance_during_idle = QW.QCheckBox( self._file_maintenance_panel )
            
            self._file_maintenance_idle_throttle_velocity = ClientGUITime.VelocityCtrl( self._file_maintenance_panel, min_unit_value, max_unit_value, min_time_delta, minutes = True, seconds = True, per_phrase = 'every', unit = 'heavy work units' )
            
            self._file_maintenance_during_active = QW.QCheckBox( self._file_maintenance_panel )
            
            self._file_maintenance_active_throttle_velocity = ClientGUITime.VelocityCtrl( self._file_maintenance_panel, min_unit_value, max_unit_value, min_time_delta, minutes = True, seconds = True, per_phrase = 'every', unit = 'heavy work units' )
            
            tt = 'Different jobs will count for more or less weight. A file metadata reparse will count as one work unit, but quicker jobs like checking for file presence will count as fractions of one and will will work more frequently.'
            tt += os.linesep * 2
            tt += 'Please note that this throttle is not rigorous for long timescales, as file processing history is not currently saved on client exit. If you restart the client, the file manager thinks it has run 0 jobs and will be happy to run until the throttle kicks in again.'
            
            self._file_maintenance_idle_throttle_velocity.setToolTip( tt )
            self._file_maintenance_active_throttle_velocity.setToolTip( tt )
            
            #
            
            self._idle_normal.setChecked( HC.options[ 'idle_normal' ] )
            self._idle_period.SetValue( HC.options['idle_period'] )
            self._idle_mouse_period.SetValue( HC.options['idle_mouse_period'] )
            self._idle_mode_client_api_timeout.SetValue( self._new_options.GetNoneableInteger( 'idle_mode_client_api_timeout' ) )
            self._system_busy_cpu_percent.setValue( self._new_options.GetInteger( 'system_busy_cpu_percent' ) )
            self._system_busy_cpu_count.SetValue( self._new_options.GetNoneableInteger( 'system_busy_cpu_count' ) )
            
            self._idle_shutdown.SetValue( HC.options[ 'idle_shutdown' ] )
            self._idle_shutdown_max_minutes.setValue( HC.options['idle_shutdown_max_minutes'] )
            self._shutdown_work_period.SetValue( self._new_options.GetInteger( 'shutdown_work_period' ) )
            
            self._file_maintenance_during_idle.setChecked( self._new_options.GetBoolean( 'file_maintenance_during_idle' ) )
            
            file_maintenance_idle_throttle_files = self._new_options.GetInteger( 'file_maintenance_idle_throttle_files' )
            file_maintenance_idle_throttle_time_delta = self._new_options.GetInteger( 'file_maintenance_idle_throttle_time_delta' )
            
            file_maintenance_idle_throttle_velocity = ( file_maintenance_idle_throttle_files, file_maintenance_idle_throttle_time_delta )
            
            self._file_maintenance_idle_throttle_velocity.SetValue( file_maintenance_idle_throttle_velocity )
            
            self._file_maintenance_during_active.setChecked( self._new_options.GetBoolean( 'file_maintenance_during_active' ) )
            
            file_maintenance_active_throttle_files = self._new_options.GetInteger( 'file_maintenance_active_throttle_files' )
            file_maintenance_active_throttle_time_delta = self._new_options.GetInteger( 'file_maintenance_active_throttle_time_delta' )
            
            file_maintenance_active_throttle_velocity = ( file_maintenance_active_throttle_files, file_maintenance_active_throttle_time_delta )
            
            self._file_maintenance_active_throttle_velocity.SetValue( file_maintenance_active_throttle_velocity )
            
            #
            
            rows = []
            
            rows.append( ( 'Run maintenance jobs when the client is idle and the system is not otherwise busy: ', self._idle_normal ) )
            rows.append( ( 'Permit idle mode if no general browsing activity has occurred in the past: ', self._idle_period ) )
            rows.append( ( 'Permit idle mode if the mouse has not been moved in the past: ', self._idle_mouse_period ) )
            rows.append( ( 'Permit idle mode if no Client API requests in the past: ', self._idle_mode_client_api_timeout ) )
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._system_busy_cpu_percent, CC.FLAGS_CENTER )
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self._idle_panel, label = '% on ' ), CC.FLAGS_CENTER )
            QP.AddToLayout( hbox, self._system_busy_cpu_count, CC.FLAGS_CENTER )
            
            import psutil
            
            num_cores = psutil.cpu_count()
            
            QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self._idle_panel, label = '(you appear to have {} cores)'.format( num_cores ) ), CC.FLAGS_CENTER )
            
            rows.append( ( 'Consider the system busy if CPU usage is above: ', hbox ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._idle_panel, rows )
            
            self._idle_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Run jobs on shutdown: ', self._idle_shutdown ) )
            rows.append( ( 'Only run shutdown jobs once per: ', self._shutdown_work_period ) )
            rows.append( ( 'Max number of minutes to run shutdown jobs: ', self._idle_shutdown_max_minutes ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._shutdown_panel, rows )
            
            self._shutdown_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            text = '***'
            text += os.linesep
            text +='If you are a new user or do not completely understand these options, please do not touch them! Do not set the client to be idle all the time unless you know what you are doing or are testing something and are prepared for potential problems!'
            text += os.linesep
            text += '***'
            text += os.linesep * 2
            text += 'Sometimes, the client needs to do some heavy maintenance. This could be reformatting the database to keep it running fast or processing a large number of tags from a repository. Typically, these jobs will not allow you to use the gui while they run, and on slower computers--or those with not much memory--they can take a long time to complete.'
            text += os.linesep * 2
            text += 'You can set these jobs to run only when the client is idle, or only during shutdown, or neither, or both. If you leave the client on all the time in the background, focusing on \'idle time\' processing is often ideal. If you have a slow computer, relying on \'shutdown\' processing (which you can manually start when convenient), is often better.'
            text += os.linesep * 2
            text += 'If the client switches from idle to not idle during a job, it will try to abandon it and give you back control. This is not always possible, and even when it is, it will sometimes take several minutes, particularly on slower machines or those on HDDs rather than SSDs.'
            text += os.linesep * 2
            text += 'If the client believes the system is busy, it will generally not start jobs.'
            
            st = ClientGUICommon.BetterStaticText( self._jobs_panel, label = text )
            st.setWordWrap( True )
            
            self._jobs_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._jobs_panel.Add( self._idle_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._jobs_panel.Add( self._shutdown_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            message = 'Scheduled jobs such as reparsing file metadata and regenerating thumbnails are performed in the background.'
            
            self._file_maintenance_panel.Add( ClientGUICommon.BetterStaticText( self._file_maintenance_panel, label = message ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Run file maintenance during idle time: ', self._file_maintenance_during_idle ) )
            rows.append( ( 'Idle throttle: ', self._file_maintenance_idle_throttle_velocity ) )
            rows.append( ( 'Run file maintenance during normal time: ', self._file_maintenance_during_active ) )
            rows.append( ( 'Normal throttle: ', self._file_maintenance_active_throttle_velocity ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._file_maintenance_panel, rows )
            
            self._file_maintenance_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._jobs_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_maintenance_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
            self._EnableDisableIdleNormal()
            self._EnableDisableIdleShutdown()
            
            self._system_busy_cpu_count.valueChanged.connect( self._EnableDisableCPUPercent )
            
        
        def _EnableDisableCPUPercent( self ):
            
            enabled = self._system_busy_cpu_count.isEnabled() and self._system_busy_cpu_count.GetValue() is not None
            
            self._system_busy_cpu_percent.setEnabled( enabled )
            
        
        def _EnableDisableIdleNormal( self ):
            
            enabled = self._idle_normal.isChecked()
            
            self._idle_period.setEnabled( enabled )
            self._idle_mouse_period.setEnabled( enabled )
            self._idle_mode_client_api_timeout.setEnabled( enabled )
            self._system_busy_cpu_count.setEnabled( enabled )
            
            self._EnableDisableCPUPercent()
            
        
        def _EnableDisableIdleShutdown( self ):
            
            enabled = self._idle_shutdown.GetValue() != CC.IDLE_NOT_ON_SHUTDOWN
            
            self._shutdown_work_period.setEnabled( enabled )
            self._idle_shutdown_max_minutes.setEnabled( enabled )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'idle_normal' ] = self._idle_normal.isChecked()
            
            HC.options[ 'idle_period' ] = self._idle_period.GetValue()
            HC.options[ 'idle_mouse_period' ] = self._idle_mouse_period.GetValue()
            self._new_options.SetNoneableInteger( 'idle_mode_client_api_timeout', self._idle_mode_client_api_timeout.GetValue() )
            
            self._new_options.SetInteger( 'system_busy_cpu_percent', self._system_busy_cpu_percent.value() )
            self._new_options.SetNoneableInteger( 'system_busy_cpu_count', self._system_busy_cpu_count.GetValue() )
            
            HC.options[ 'idle_shutdown' ] = self._idle_shutdown.GetValue()
            HC.options[ 'idle_shutdown_max_minutes' ] = self._idle_shutdown_max_minutes.value()
            
            self._new_options.SetInteger( 'shutdown_work_period', self._shutdown_work_period.GetValue() )
            
            self._new_options.SetBoolean( 'file_maintenance_during_idle', self._file_maintenance_during_idle.isChecked() )
            
            file_maintenance_idle_throttle_velocity = self._file_maintenance_idle_throttle_velocity.GetValue()
            
            ( file_maintenance_idle_throttle_files, file_maintenance_idle_throttle_time_delta ) = file_maintenance_idle_throttle_velocity
            
            self._new_options.SetInteger( 'file_maintenance_idle_throttle_files', file_maintenance_idle_throttle_files )
            self._new_options.SetInteger( 'file_maintenance_idle_throttle_time_delta', file_maintenance_idle_throttle_time_delta )
            
            self._new_options.SetBoolean( 'file_maintenance_during_active', self._file_maintenance_during_active.isChecked() )
            
            file_maintenance_active_throttle_velocity = self._file_maintenance_active_throttle_velocity.GetValue()
            
            ( file_maintenance_active_throttle_files, file_maintenance_active_throttle_time_delta ) = file_maintenance_active_throttle_velocity
            
            self._new_options.SetInteger( 'file_maintenance_active_throttle_files', file_maintenance_active_throttle_files )
            self._new_options.SetInteger( 'file_maintenance_active_throttle_time_delta', file_maintenance_active_throttle_time_delta )
            
        
    
    class _MediaPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            self._animation_start_position = QP.MakeQSpinBox( self, min=0, max=100 )
            
            self._disable_cv_for_gifs = QW.QCheckBox( self )
            self._disable_cv_for_gifs.setToolTip( 'OpenCV is good at rendering gifs, but if you have problems with it and your graphics card, check this and the less reliable and slower PIL will be used instead. EDIT: OpenCV is much better these days--this is mostly not needed.' )
            
            self._load_images_with_pil = QW.QCheckBox( self )
            self._load_images_with_pil.setToolTip( 'OpenCV is much faster than PIL, but it is sometimes less reliable. Switch this on if you experience crashes or other unusual problems while importing or viewing certain images. EDIT: OpenCV is much better these days--this is mostly not needed.' )
            
            self._use_system_ffmpeg = QW.QCheckBox( self )
            self._use_system_ffmpeg.setToolTip( 'Check this to always default to the system ffmpeg in your path, rather than using the static ffmpeg in hydrus\'s bin directory. (requires restart)' )
            
            self._always_loop_gifs = QW.QCheckBox( self )
            self._always_loop_gifs.setToolTip( 'Some GIFS have metadata specifying how many times they should be played, usually 1. Uncheck this to obey that number.' )
            
            self._media_viewer_cursor_autohide_time_ms = ClientGUICommon.NoneableSpinCtrl( self, none_phrase = 'do not autohide', min = 100, max = 100000, unit = 'ms' )
            
            self._anchor_and_hide_canvas_drags = QW.QCheckBox( self )
            self._touchscreen_canvas_drags_unanchor = QW.QCheckBox( self )
            
            from hydrus.client.gui.canvas import ClientGUICanvas
            
            self._media_viewer_zoom_center = ClientGUICommon.BetterChoice()
            
            for zoom_centerpoint_type in ClientGUICanvas.ZOOM_CENTERPOINT_TYPES:
                
                self._media_viewer_zoom_center.addItem( ClientGUICanvas.zoom_centerpoints_str_lookup[ zoom_centerpoint_type ], zoom_centerpoint_type )
                
            
            tt = 'When you zoom in or out, there is a centerpoint about which the image zooms. This point \'stays still\' while the image expands or shrinks around it. Different centerpoints give different feels, especially if you drag images around a bit.'
            
            self._media_viewer_zoom_center.setToolTip( tt )
            
            self._media_zooms = QW.QLineEdit( self )
            self._media_zooms.textChanged.connect( self.EventZoomsChanged )
            
            self._mpv_conf_path = QP.FilePickerCtrl( self, starting_directory = os.path.join( HC.STATIC_DIR, 'mpv-conf' ) )
            
            self._animated_scanbar_height = QP.MakeQSpinBox( self, min=1, max=255 )
            self._animated_scanbar_nub_width = QP.MakeQSpinBox( self, min=1, max=63 )
            
            self._media_viewer_panel = ClientGUICommon.StaticBox( self, 'media viewer mime handling' )
            
            media_viewer_list_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._media_viewer_panel )
            
            self._media_viewer_options = ClientGUIListCtrl.BetterListCtrl( media_viewer_list_panel, CGLC.COLUMN_LIST_MEDIA_VIEWER_OPTIONS.ID, 20, data_to_tuples_func = self._GetListCtrlData, activation_callback = self.EditMediaViewerOptions, use_simple_delete = True )
            
            media_viewer_list_panel.SetListCtrl( self._media_viewer_options )
            
            media_viewer_list_panel.AddButton( 'add', self.AddMediaViewerOptions, enabled_check_func = self._CanAddMediaViewOption )
            media_viewer_list_panel.AddButton( 'edit', self.EditMediaViewerOptions, enabled_only_on_selection = True )
            media_viewer_list_panel.AddDeleteButton( enabled_check_func = self._CanDeleteMediaViewOptions )
            
            #
            
            self._animation_start_position.setValue( int( HC.options['animation_start_position'] * 100.0 ) )
            self._disable_cv_for_gifs.setChecked( self._new_options.GetBoolean( 'disable_cv_for_gifs' ) )
            self._load_images_with_pil.setChecked( self._new_options.GetBoolean( 'load_images_with_pil' ) )
            self._use_system_ffmpeg.setChecked( self._new_options.GetBoolean( 'use_system_ffmpeg' ) )
            self._always_loop_gifs.setChecked( self._new_options.GetBoolean( 'always_loop_gifs' ) )
            self._media_viewer_cursor_autohide_time_ms.SetValue( self._new_options.GetNoneableInteger( 'media_viewer_cursor_autohide_time_ms' ) )
            self._anchor_and_hide_canvas_drags.setChecked( self._new_options.GetBoolean( 'anchor_and_hide_canvas_drags' ) )
            self._touchscreen_canvas_drags_unanchor.setChecked( self._new_options.GetBoolean( 'touchscreen_canvas_drags_unanchor' ) )
            self._animated_scanbar_height.setValue( self._new_options.GetInteger( 'animated_scanbar_height' ) )
            self._animated_scanbar_nub_width.setValue( self._new_options.GetInteger( 'animated_scanbar_nub_width' ) )
            
            self._media_viewer_zoom_center.SetValue( self._new_options.GetInteger( 'media_viewer_zoom_center' ) )
            
            media_zooms = self._new_options.GetMediaZooms()
            
            self._media_zooms.setText( ','.join( ( str( media_zoom ) for media_zoom in media_zooms ) ) )
            
            all_media_view_options = self._new_options.GetMediaViewOptions()
            
            for ( mime, view_options ) in all_media_view_options.items():
                
                data = QP.ListsToTuples( [ mime ] + list( view_options ) )
                
                self._media_viewer_options.AddDatas( ( data, ) )
                
            
            self._media_viewer_options.Sort()
            
            #
            
            vbox = QP.VBoxLayout()
            
            text = 'Please be warned that hydrus does not currently zoom in very efficiently at high zooms!'
            text += os.linesep
            text += 'Just be careful at >400%, particularly for already large files--it can lag out and eat a chunk of memory.'
            
            st = ClientGUICommon.BetterStaticText( self, text )
            st.setObjectName( 'HydrusWarning' )
            
            QP.AddToLayout( vbox, st )
            
            rows = []
            
            rows.append( ( 'Start animations this % in:', self._animation_start_position ) )
            rows.append( ( 'Prefer system FFMPEG:', self._use_system_ffmpeg ) )
            rows.append( ( 'Always Loop GIFs:', self._always_loop_gifs ) )
            rows.append( ( 'Centerpoint for media zooming:', self._media_viewer_zoom_center ) )
            rows.append( ( 'Media zooms:', self._media_zooms ) )
            rows.append( ( 'Set a new mpv.conf on dialog ok?:', self._mpv_conf_path ) )
            rows.append( ( 'Animation scanbar height:', self._animated_scanbar_height ) )
            rows.append( ( 'Animation scanbar nub width:', self._animated_scanbar_nub_width ) )
            rows.append( ( 'Time until mouse cursor autohides on media viewer:', self._media_viewer_cursor_autohide_time_ms ) )
            rows.append( ( 'RECOMMEND WINDOWS ONLY: Hide and anchor mouse cursor on media viewer drags:', self._anchor_and_hide_canvas_drags ) )
            rows.append( ( 'RECOMMEND WINDOWS ONLY: If set to hide and anchor, undo on apparent touchscreen drag:', self._touchscreen_canvas_drags_unanchor ) )
            rows.append( ( 'BUGFIX: Load images with PIL (slower):', self._load_images_with_pil ) )
            rows.append( ( 'BUGFIX: Load gifs with PIL instead of OpenCV (slower, bad transparency):', self._disable_cv_for_gifs ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self._media_viewer_panel.Add( media_viewer_list_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            QP.AddToLayout( vbox, self._media_viewer_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def _CanAddMediaViewOption( self ):
            
            return len( self._GetUnsetMediaViewFiletypes() ) > 0
            
        
        def _CanDeleteMediaViewOptions( self ):
            
            deletable_mimes = set( HC.SEARCHABLE_MIMES )
            
            selected_mimes = set()
            
            for ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) in self._media_viewer_options.GetData( only_selected = True ):
                
                selected_mimes.add( mime )
                
            
            if len( selected_mimes ) == 0:
                
                return False
                
            
            all_selected_are_deletable = selected_mimes.issubset( deletable_mimes )
            
            return all_selected_are_deletable
            
        
        def _GetCopyOfGeneralMediaViewOptions( self, desired_mime ):
            
            general_mime_type = HC.mimes_to_general_mimetypes[ desired_mime ]
            
            for ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) in self._media_viewer_options.GetData():
                
                if mime == general_mime_type:
                    
                    view_options = ( desired_mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info )
                    
                    return view_options
                    
                
            
        
        def _GetUnsetMediaViewFiletypes( self ):
            
            editable_mimes = set( HC.SEARCHABLE_MIMES )
            
            set_mimes = set()
            
            for ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) in self._media_viewer_options.GetData():
                
                set_mimes.add( mime )
                
            
            unset_mimes = editable_mimes.difference( set_mimes )
            
            return unset_mimes
            
        
        def _GetListCtrlData( self, data ):
            
            ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) = data
            
            pretty_mime = self._GetPrettyMime( mime )
            
            pretty_media_show_action = CC.media_viewer_action_string_lookup[ media_show_action ]
            
            if media_start_paused:
                
                pretty_media_show_action += ', start paused'
                
            
            if media_start_with_embed:
                
                pretty_media_show_action += ', start with embed button'
                
            
            pretty_preview_show_action = CC.media_viewer_action_string_lookup[ preview_show_action ]
            
            if preview_start_paused:
                
                pretty_preview_show_action += ', start paused'
                
            
            if preview_start_with_embed:
                
                pretty_preview_show_action += ', start with embed button'
                
            
            no_show = { media_show_action, preview_show_action }.isdisjoint( { CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV } )
            
            if no_show:
                
                pretty_zoom_info = ''
                
            else:
                
                pretty_zoom_info = str( zoom_info )
                
            
            display_tuple = ( pretty_mime, pretty_media_show_action, pretty_preview_show_action, pretty_zoom_info )
            sort_tuple = ( pretty_mime, pretty_media_show_action, pretty_preview_show_action, pretty_zoom_info )
            
            return ( display_tuple, sort_tuple )
            
        
        def _GetPrettyMime( self, mime ):
            
            pretty_mime = HC.mime_string_lookup[ mime ]
            
            if mime not in HC.GENERAL_FILETYPES:
                
                pretty_mime = '{}: {}'.format( HC.mime_string_lookup[ HC.mimes_to_general_mimetypes[ mime ] ], pretty_mime )
                
            
            return pretty_mime
            
        
        def AddMediaViewerOptions( self ):
            
            unset_filetypes = self._GetUnsetMediaViewFiletypes()
            
            if len( unset_filetypes ) == 0:
                
                QW.QMessageBox.warning( self, 'Warning', 'You cannot add any more specific filetype options!' )
                
                return
                
            
            choice_tuples = [ ( self._GetPrettyMime( mime ), mime ) for mime in unset_filetypes ]
            
            try:
                
                mime = ClientGUIDialogsQuick.SelectFromList( self, 'select the filetype to add', choice_tuples, sort_tuples = True )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            data = self._GetCopyOfGeneralMediaViewOptions( mime )
            
            title = 'add media view options information'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                
                panel = ClientGUIScrolledPanelsEdit.EditMediaViewOptionsPanel( dlg, data )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    new_data = panel.GetValue()
                    
                    self._media_viewer_options.AddDatas( ( new_data, ) )
                    
                
            
        
        def EditMediaViewerOptions( self ):
            
            for data in self._media_viewer_options.GetData( only_selected = True ):
                
                title = 'edit media view options information'
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                    
                    panel = ClientGUIScrolledPanelsEdit.EditMediaViewOptionsPanel( dlg, data )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        new_data = panel.GetValue()
                        
                        self._media_viewer_options.ReplaceData( data, new_data )
                        
                    
                
            
        
        def EventZoomsChanged( self, text ):
            
            try:
                
                media_zooms = [ float( media_zoom ) for media_zoom in self._media_zooms.text().split( ',' ) ]
                
                self._media_zooms.setObjectName( '' )
                
            except ValueError:
                
                self._media_zooms.setObjectName( 'HydrusInvalid' )
                
            
            self._media_zooms.style().polish( self._media_zooms )
            
            self._media_zooms.update()
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'animation_start_position' ] = self._animation_start_position.value() / 100.0
            
            self._new_options.SetBoolean( 'disable_cv_for_gifs', self._disable_cv_for_gifs.isChecked() )
            self._new_options.SetBoolean( 'load_images_with_pil', self._load_images_with_pil.isChecked() )
            self._new_options.SetBoolean( 'use_system_ffmpeg', self._use_system_ffmpeg.isChecked() )
            self._new_options.SetBoolean( 'always_loop_gifs', self._always_loop_gifs.isChecked() )
            self._new_options.SetBoolean( 'anchor_and_hide_canvas_drags', self._anchor_and_hide_canvas_drags.isChecked() )
            self._new_options.SetBoolean( 'touchscreen_canvas_drags_unanchor', self._touchscreen_canvas_drags_unanchor.isChecked() )
            
            self._new_options.SetNoneableInteger( 'media_viewer_cursor_autohide_time_ms', self._media_viewer_cursor_autohide_time_ms.GetValue() )
            
            mpv_conf_path = self._mpv_conf_path.GetPath()
            
            if mpv_conf_path is not None and mpv_conf_path != '' and os.path.exists( mpv_conf_path ) and os.path.isfile( mpv_conf_path ):
                
                dest_mpv_conf_path = HG.client_controller.GetMPVConfPath()
                
                try:
                    
                    HydrusPaths.MirrorFile( mpv_conf_path, dest_mpv_conf_path )
                    
                except Exception as e:
                    
                    HydrusData.ShowText( 'Could not set the mpv conf path "{}" to "{}"! Error follows!'.format( mpv_conf_path, dest_mpv_conf_path ) )
                    HydrusData.ShowException( e )
                    
                
            
            self._new_options.SetInteger( 'animated_scanbar_height', self._animated_scanbar_height.value() )
            self._new_options.SetInteger( 'animated_scanbar_nub_width', self._animated_scanbar_nub_width.value() )
            
            self._new_options.SetInteger( 'media_viewer_zoom_center', self._media_viewer_zoom_center.GetValue() )
            
            try:
                
                media_zooms = [ float( media_zoom ) for media_zoom in self._media_zooms.text().split( ',' ) ]
                
                media_zooms = [ media_zoom for media_zoom in media_zooms if media_zoom > 0.0 ]
                
                if len( media_zooms ) > 0:
                    
                    self._new_options.SetMediaZooms( media_zooms )
                    
                
            except ValueError:
                
                HydrusData.ShowText( 'Could not parse those zooms, so they were not saved!' )
                
            
            mimes_to_media_view_options = {}
            
            for data in self._media_viewer_options.GetData():
                
                data = list( data )
                
                mime = data[0]
                
                value = data[1:]
                
                mimes_to_media_view_options[ mime ] = value
                
            
            self._new_options.SetMediaViewOptions( mimes_to_media_view_options )
            
        
    
    class _PopupPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            self._popup_panel = ClientGUICommon.StaticBox( self, 'popup window toaster' )
            
            self._popup_message_character_width = QP.MakeQSpinBox( self._popup_panel, min = 16, max = 256 )
            
            self._popup_message_force_min_width = QW.QCheckBox( self._popup_panel )
            
            self._freeze_message_manager_when_mouse_on_other_monitor = QW.QCheckBox( self._popup_panel )
            self._freeze_message_manager_when_mouse_on_other_monitor.setToolTip( 'This is useful if you have a virtual desktop and find the popup manager restores strangely when you hop back to the hydrus display.' )
            
            self._freeze_message_manager_when_main_gui_minimised = QW.QCheckBox( self._popup_panel )
            self._freeze_message_manager_when_main_gui_minimised.setToolTip( 'This is useful if the popup toaster restores strangely after minimised changes.' )
            
            self._hide_message_manager_on_gui_iconise = QW.QCheckBox( self._popup_panel )
            self._hide_message_manager_on_gui_iconise.setToolTip( 'If your message manager does not automatically minimise with your main gui, try this. It can lead to unusual show and positioning behaviour on window managers that do not support it, however.' )
            
            self._hide_message_manager_on_gui_deactive = QW.QCheckBox( self._popup_panel )
            self._hide_message_manager_on_gui_deactive.setToolTip( 'If your message manager stays up after you minimise the program to the system tray using a custom window manager, try this out! It hides the popup messages as soon as the main gui loses focus.' )
            
            self._notify_client_api_cookies = QW.QCheckBox( self._popup_panel )
            self._notify_client_api_cookies.setToolTip( 'This will make a short-lived popup message every time you get new cookie information over the Client API.' )
            
            #
            
            self._popup_message_character_width.setValue( self._new_options.GetInteger( 'popup_message_character_width' ) )
            
            self._popup_message_force_min_width.setChecked( self._new_options.GetBoolean( 'popup_message_force_min_width' ) )
            
            self._freeze_message_manager_when_mouse_on_other_monitor.setChecked( self._new_options.GetBoolean( 'freeze_message_manager_when_mouse_on_other_monitor' ) )
            self._freeze_message_manager_when_main_gui_minimised.setChecked( self._new_options.GetBoolean( 'freeze_message_manager_when_main_gui_minimised' ) )
            
            self._hide_message_manager_on_gui_iconise.setChecked( self._new_options.GetBoolean( 'hide_message_manager_on_gui_iconise' ) )
            self._hide_message_manager_on_gui_deactive.setChecked( self._new_options.GetBoolean( 'hide_message_manager_on_gui_deactive' ) )
            
            self._notify_client_api_cookies.setChecked( self._new_options.GetBoolean( 'notify_client_api_cookies' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Approximate max width of popup messages (in characters): ', self._popup_message_character_width ) )
            rows.append( ( 'BUGFIX: Force this width as the minimum width for all popup messages: ', self._popup_message_force_min_width ) )
            rows.append( ( 'Freeze the popup toaster when mouse is on another display: ', self._freeze_message_manager_when_mouse_on_other_monitor ) )
            rows.append( ( 'Freeze the popup toaster when the main gui is minimised: ', self._freeze_message_manager_when_main_gui_minimised ) )
            rows.append( ( 'BUGFIX: Hide the popup toaster when the main gui is minimised: ', self._hide_message_manager_on_gui_iconise ) )
            rows.append( ( 'BUGFIX: Hide the popup toaster when the main gui loses focus: ', self._hide_message_manager_on_gui_deactive ) )
            rows.append( ( 'Make a short-lived popup on cookie updates through the Client API: ', self._notify_client_api_cookies ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._popup_panel, rows )
            
            self._popup_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._popup_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetInteger( 'popup_message_character_width', self._popup_message_character_width.value() )
            
            self._new_options.SetBoolean( 'popup_message_force_min_width', self._popup_message_force_min_width.isChecked() )
            
            self._new_options.SetBoolean( 'freeze_message_manager_when_mouse_on_other_monitor', self._freeze_message_manager_when_mouse_on_other_monitor.isChecked() )
            self._new_options.SetBoolean( 'freeze_message_manager_when_main_gui_minimised', self._freeze_message_manager_when_main_gui_minimised.isChecked() )
            
            self._new_options.SetBoolean( 'hide_message_manager_on_gui_iconise', self._hide_message_manager_on_gui_iconise.isChecked() )
            self._new_options.SetBoolean( 'hide_message_manager_on_gui_deactive', self._hide_message_manager_on_gui_deactive.isChecked() )
            
            self._new_options.SetBoolean( 'notify_client_api_cookies', self._notify_client_api_cookies.isChecked() )
            
        
    
    class _RegexPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            regex_favourites = HC.options[ 'regex_favourites' ]
            
            self._regex_panel = ClientGUIScrolledPanelsEdit.EditRegexFavourites( self, regex_favourites )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._regex_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            regex_favourites = self._regex_panel.GetValue()
            
            HC.options[ 'regex_favourites' ] = regex_favourites
            
        
    
    class _SearchPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            self._autocomplete_panel = ClientGUICommon.StaticBox( self, 'autocomplete' )
            
            self._default_search_synchronised = QW.QCheckBox( self._autocomplete_panel )
            tt = 'This refers to the button on the autocomplete dropdown that enables new searches to start. If this is on, then new search pages will search as soon as you enter the first search predicate. If off, no search will happen until you switch it back on.'
            self._default_search_synchronised.setToolTip( tt )
            
            self._autocomplete_float_main_gui = QW.QCheckBox( self._autocomplete_panel )
            tt = 'The autocomplete dropdown can either \'float\' on top of the main window, or if that does not work well for you, it can embed into the parent panel.'
            self._autocomplete_float_main_gui.setToolTip( tt )
            
            self._autocomplete_float_frames = QW.QCheckBox( self._autocomplete_panel )
            tt = 'The autocomplete dropdown can either \'float\' on top of dialogs like _manage tags_, or if that does not work well for you (it can sometimes annoyingly overlap the ok/cancel buttons), it can embed into the parent dialog panel.'
            self._autocomplete_float_frames.setToolTip( tt )
            
            self._ac_read_list_height_num_chars = QP.MakeQSpinBox( self._autocomplete_panel, min = 1, max = 128 )
            tt = 'Read autocompletes are those in search pages, where you are looking through existing tags to find your files.'
            self._ac_read_list_height_num_chars.setToolTip( tt )
            
            self._ac_write_list_height_num_chars = QP.MakeQSpinBox( self._autocomplete_panel, min = 1, max = 128 )
            tt = 'Write autocompletes are those in most dialogs, where you are adding new tags to files.'
            self._ac_write_list_height_num_chars.setToolTip( tt )
            
            self._always_show_system_everything = QW.QCheckBox( self._autocomplete_panel )
            tt = 'After users get some experience with the program and a larger collection, they tend to have less use for system:everything.'
            self._always_show_system_everything.setToolTip( tt )
            
            self._filter_inbox_and_archive_predicates = QW.QCheckBox( self._autocomplete_panel )
            tt = 'If everything is current in the inbox (or archive), then there is no use listing it or its opposite--it either does not change the search or it produces nothing. If you find it jarring though, turn it off here!'
            self._filter_inbox_and_archive_predicates.setToolTip( tt )
            
            #
            
            self._default_search_synchronised.setChecked( self._new_options.GetBoolean( 'default_search_synchronised' ) )
            
            self._autocomplete_float_main_gui.setChecked( self._new_options.GetBoolean( 'autocomplete_float_main_gui' ) )
            self._autocomplete_float_frames.setChecked( self._new_options.GetBoolean( 'autocomplete_float_frames' ) )
            
            self._ac_read_list_height_num_chars.setValue( self._new_options.GetInteger( 'ac_read_list_height_num_chars' ) )
            self._ac_write_list_height_num_chars.setValue( self._new_options.GetInteger( 'ac_write_list_height_num_chars' ) )
            
            self._always_show_system_everything.setChecked( self._new_options.GetBoolean( 'always_show_system_everything' ) )
            
            self._filter_inbox_and_archive_predicates.setChecked( self._new_options.GetBoolean( 'filter_inbox_and_archive_predicates' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            message = 'The autocomplete dropdown list is the panel that hangs below the tag input text box on search pages.'
            
            st = ClientGUICommon.BetterStaticText( self._autocomplete_panel, label = message )
            
            self._autocomplete_panel.Add( st, CC.FLAGS_CENTER )
            
            rows = []
            
            #
            
            rows.append( ( 'Start new search pages in \'searching immediately\': ', self._default_search_synchronised ) )
            rows.append( ( 'Autocomplete results float in main gui: ', self._autocomplete_float_main_gui ) )
            rows.append( ( 'Autocomplete results float in other windows: ', self._autocomplete_float_frames ) )
            rows.append( ( '\'Read\' autocomplete list height: ', self._ac_read_list_height_num_chars ) )
            rows.append( ( '\'Write\' autocomplete list height: ', self._ac_write_list_height_num_chars ) )
            rows.append( ( 'show system:everything even if total files is over 10,000: ', self._always_show_system_everything ) )
            rows.append( ( 'hide inbox and archive system predicates if either has no files: ', self._filter_inbox_and_archive_predicates ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._autocomplete_panel, rows )
            
            self._autocomplete_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            QP.AddToLayout( vbox, self._autocomplete_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'default_search_synchronised', self._default_search_synchronised.isChecked() )
            
            self._new_options.SetBoolean( 'autocomplete_float_main_gui', self._autocomplete_float_main_gui.isChecked() )
            self._new_options.SetBoolean( 'autocomplete_float_frames', self._autocomplete_float_frames.isChecked() )
            
            self._new_options.SetInteger( 'ac_read_list_height_num_chars', self._ac_read_list_height_num_chars.value() )
            self._new_options.SetInteger( 'ac_write_list_height_num_chars', self._ac_write_list_height_num_chars.value() )
            
            self._new_options.SetBoolean( 'always_show_system_everything', self._always_show_system_everything.isChecked() )
            self._new_options.SetBoolean( 'filter_inbox_and_archive_predicates', self._filter_inbox_and_archive_predicates.isChecked() )
            
        
    
    class _SortCollectPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            self._tag_sort_panel = ClientGUICommon.StaticBox( self, 'tag sort' )
            
            self._default_tag_sort = ClientGUITagSorting.TagSortControl( self._tag_sort_panel, self._new_options.GetDefaultTagSort(), show_siblings = True )
            
            self._file_sort_panel = ClientGUICommon.StaticBox( self, 'file sort' )
            
            self._default_media_sort = ClientGUIResultsSortCollect.MediaSortControl( self._file_sort_panel )
            
            self._fallback_media_sort = ClientGUIResultsSortCollect.MediaSortControl( self._file_sort_panel )
            
            self._save_page_sort_on_change = QW.QCheckBox( self._file_sort_panel )
            
            self._default_media_collect = ClientGUIResultsSortCollect.MediaCollectControl( self._file_sort_panel, silent = True )
            
            namespace_sorting_box = ClientGUICommon.StaticBox( self._file_sort_panel, 'namespace file sorting' )
            
            self._namespace_sort_by = ClientGUIListBoxes.QueueListBox( namespace_sorting_box, 8, self._ConvertNamespaceTupleToSortString, self._AddNamespaceSort, self._EditNamespaceSort )
            
            #
            
            try:
                
                self._default_media_sort.SetSort( self._new_options.GetDefaultSort() )
                
            except:
                
                media_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
                
                self._default_media_sort.SetSort( media_sort )
                
            
            try:
                
                self._fallback_media_sort.SetSort( self._new_options.GetFallbackSort() )
                
            except:
                
                media_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_IMPORT_TIME ), CC.SORT_ASC )
                
                self._fallback_media_sort.SetSort( media_sort )
                
            
            self._namespace_sort_by.AddDatas( [ media_sort.sort_type[1] for media_sort in HG.client_controller.new_options.GetDefaultNamespaceSorts() ] )
            
            self._save_page_sort_on_change.setChecked( self._new_options.GetBoolean( 'save_page_sort_on_change' ) )
            
            #
            
            sort_by_text = 'You can manage your namespace sorting schemes here.'
            sort_by_text += os.linesep
            sort_by_text += 'The client will sort media by comparing their namespaces, moving from left to right until an inequality is found.'
            sort_by_text += os.linesep
            sort_by_text += 'Any namespaces here will also appear in your collect-by dropdowns.'
            
            namespace_sorting_box.Add( ClientGUICommon.BetterStaticText( namespace_sorting_box, sort_by_text ), CC.FLAGS_EXPAND_PERPENDICULAR )
            namespace_sorting_box.Add( self._namespace_sort_by, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            rows = []
            
            rows.append( ( 'Default tag sort: ', self._default_tag_sort ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._tag_sort_panel, rows )
            
            self._tag_sort_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Default file sort: ', self._default_media_sort ) )
            rows.append( ( 'Secondary file sort (when primary gives two equal values): ', self._fallback_media_sort ) )
            rows.append( ( 'Update default file sort every time a new sort is manually chosen: ', self._save_page_sort_on_change ) )
            rows.append( ( 'Default collect: ', self._default_media_collect ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            self._file_sort_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            self._file_sort_panel.Add( namespace_sorting_box, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._tag_sort_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_sort_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def _AddNamespaceSort( self ):
            
            default = ( ( 'creator', 'series', 'page' ), ClientTags.TAG_DISPLAY_ACTUAL )
            
            return self._EditNamespaceSort( default )
            
        
        def _ConvertNamespaceTupleToSortString( self, sort_data ):
            
            ( namespaces, tag_display_type ) = sort_data
            
            return '-'.join( namespaces )
            
        
        def _EditNamespaceSort( self, sort_data ):
            
            return ClientGUITags.EditNamespaceSort( self, sort_data )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetDefaultTagSort( self._default_tag_sort.GetValue() )
            
            self._new_options.SetDefaultSort( self._default_media_sort.GetSort() )
            self._new_options.SetFallbackSort( self._fallback_media_sort.GetSort() )
            self._new_options.SetBoolean( 'save_page_sort_on_change', self._save_page_sort_on_change.isChecked() )
            self._new_options.SetDefaultCollect( self._default_media_collect.GetValue() )
            
            namespace_sorts = [ ClientMedia.MediaSort( sort_type = ( 'namespaces', sort_data ) ) for sort_data in self._namespace_sort_by.GetData() ]
            
            self._new_options.SetDefaultNamespaceSorts( namespace_sorts )
            
        
    
    class _SpeedAndMemoryPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            thumbnail_cache_panel = ClientGUICommon.StaticBox( self, 'thumbnail cache' )
            
            self._thumbnail_cache_size = QP.MakeQSpinBox( thumbnail_cache_panel, min=5, max=3000 )
            self._thumbnail_cache_size.valueChanged.connect( self.EventThumbnailsUpdate )
            
            self._estimated_number_thumbnails = QW.QLabel( '', thumbnail_cache_panel )
            
            self._thumbnail_cache_timeout = ClientGUITime.TimeDeltaButton( thumbnail_cache_panel, min = 300, days = True, hours = True, minutes = True )
            self._thumbnail_cache_timeout.setToolTip( 'The amount of time after which a thumbnail in the cache will naturally be removed, if it is not shunted out due to a new member exceeding the size limit.' )
            
            image_cache_panel = ClientGUICommon.StaticBox( self, 'image cache' )
            
            self._fullscreen_cache_size = QP.MakeQSpinBox( image_cache_panel, min=25, max=8192 )
            self._fullscreen_cache_size.valueChanged.connect( self.EventImageCacheUpdate )
            
            self._estimated_number_fullscreens = QW.QLabel( '', image_cache_panel )
            
            self._image_cache_timeout = ClientGUITime.TimeDeltaButton( image_cache_panel, min = 300, days = True, hours = True, minutes = True )
            self._image_cache_timeout.setToolTip( 'The amount of time after which a rendered image in the cache will naturally be removed, if it is not shunted out due to a new member exceeding the size limit.' )
            
            self._media_viewer_prefetch_delay_base_ms = QP.MakeQSpinBox( image_cache_panel, min = 0, max = 2000 )
            tt = 'How long to wait, after the current image is rendered, to start rendering neighbours. Does not matter so much any more, but if you have CPU lag, you can try boosting it a bit.'
            self._media_viewer_prefetch_delay_base_ms.setToolTip( tt )
            
            self._media_viewer_prefetch_num_previous = QP.MakeQSpinBox( image_cache_panel, min = 0, max = 5 )
            self._media_viewer_prefetch_num_next = QP.MakeQSpinBox( image_cache_panel, min = 0, max = 5 )
            
            self._image_cache_storage_limit_percentage = QP.MakeQSpinBox( image_cache_panel, min = 20, max = 50 )
            
            self._image_cache_storage_limit_percentage_st = ClientGUICommon.BetterStaticText( image_cache_panel, label = '' )
            
            self._image_cache_prefetch_limit_percentage = QP.MakeQSpinBox( image_cache_panel, min = 5, max = 20 )
            
            self._image_cache_prefetch_limit_percentage_st = ClientGUICommon.BetterStaticText( image_cache_panel, label = '' )
            
            image_tile_cache_panel = ClientGUICommon.StaticBox( self, 'image tile cache' )
            
            self._image_tile_cache_size = ClientGUIControls.BytesControl( image_tile_cache_panel )
            self._image_tile_cache_size.valueChanged.connect( self.EventImageTilesUpdate )
            
            self._estimated_number_image_tiles = QW.QLabel( '', image_tile_cache_panel )
            
            self._image_tile_cache_timeout = ClientGUITime.TimeDeltaButton( image_tile_cache_panel, min = 300, hours = True, minutes = True )
            self._image_tile_cache_timeout.setToolTip( 'The amount of time after which a rendered image tile in the cache will naturally be removed, if it is not shunted out due to a new member exceeding the size limit.' )
            
            self._ideal_tile_dimension = QP.MakeQSpinBox( image_tile_cache_panel, min = 256, max = 4096 )
            self._ideal_tile_dimension.setToolTip( 'This is the square size the system will aim for. Smaller tiles are more memory efficient but prone to warping and other artifacts. Extreme values may waste CPU.' )
            
            #
            
            buffer_panel = ClientGUICommon.StaticBox( self, 'video buffer' )
            
            self._video_buffer_size_mb = QP.MakeQSpinBox( buffer_panel, min=48, max=16*1024 )
            self._video_buffer_size_mb.valueChanged.connect( self.EventVideoBufferUpdate )
            
            self._estimated_number_video_frames = QW.QLabel( '', buffer_panel )
            
            #
            
            misc_panel = ClientGUICommon.StaticBox( self, 'misc' )
            
            self._forced_search_limit = ClientGUICommon.NoneableSpinCtrl( misc_panel, '', min = 1, max = 100000 )
            
            #
            
            self._thumbnail_cache_size.setValue( int( HC.options['thumbnail_cache_size'] // 1048576 ) )
            
            self._fullscreen_cache_size.setValue( int( HC.options['fullscreen_cache_size'] // 1048576 ) )
            
            self._image_tile_cache_size.SetValue( self._new_options.GetInteger( 'image_tile_cache_size' ) )
            
            self._thumbnail_cache_timeout.SetValue( self._new_options.GetInteger( 'thumbnail_cache_timeout' ) )
            self._image_cache_timeout.SetValue( self._new_options.GetInteger( 'image_cache_timeout' ) )
            self._image_tile_cache_timeout.SetValue( self._new_options.GetInteger( 'image_tile_cache_timeout' ) )
            
            self._ideal_tile_dimension.setValue( self._new_options.GetInteger( 'ideal_tile_dimension' ) )
            
            self._video_buffer_size_mb.setValue( self._new_options.GetInteger( 'video_buffer_size_mb' ) )
            
            self._forced_search_limit.SetValue( self._new_options.GetNoneableInteger( 'forced_search_limit' ) )
            
            self._media_viewer_prefetch_delay_base_ms.setValue( self._new_options.GetInteger( 'media_viewer_prefetch_delay_base_ms' ) )
            self._media_viewer_prefetch_num_previous.setValue( self._new_options.GetInteger( 'media_viewer_prefetch_num_previous' ) )
            self._media_viewer_prefetch_num_next.setValue( self._new_options.GetInteger( 'media_viewer_prefetch_num_next' ) )
            
            self._image_cache_storage_limit_percentage.setValue( self._new_options.GetInteger( 'image_cache_storage_limit_percentage' ) )
            self._image_cache_prefetch_limit_percentage.setValue( self._new_options.GetInteger( 'image_cache_prefetch_limit_percentage' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            text = 'These options are advanced! PROTIP: Do not go crazy here.'
            
            st = ClientGUICommon.BetterStaticText( self, text )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_CENTER )
            
            #
            
            thumbnails_sizer = QP.HBoxLayout()
            
            QP.AddToLayout( thumbnails_sizer, self._thumbnail_cache_size, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( thumbnails_sizer, self._estimated_number_thumbnails, CC.FLAGS_CENTER_PERPENDICULAR )
            
            fullscreens_sizer = QP.HBoxLayout()
            
            QP.AddToLayout( fullscreens_sizer, self._fullscreen_cache_size, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( fullscreens_sizer, self._estimated_number_fullscreens, CC.FLAGS_CENTER_PERPENDICULAR )
            
            image_tiles_sizer = QP.HBoxLayout()
            
            QP.AddToLayout( image_tiles_sizer, self._image_tile_cache_size, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( image_tiles_sizer, self._estimated_number_image_tiles, CC.FLAGS_CENTER_PERPENDICULAR )
            
            image_cache_storage_sizer = QP.HBoxLayout()
            
            QP.AddToLayout( image_cache_storage_sizer, self._image_cache_storage_limit_percentage, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( image_cache_storage_sizer, self._image_cache_storage_limit_percentage_st, CC.FLAGS_CENTER_PERPENDICULAR )
            
            image_cache_prefetch_sizer = QP.HBoxLayout()
            
            QP.AddToLayout( image_cache_prefetch_sizer, self._image_cache_prefetch_limit_percentage, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( image_cache_prefetch_sizer, self._image_cache_prefetch_limit_percentage_st, CC.FLAGS_CENTER_PERPENDICULAR )
            
            video_buffer_sizer = QP.HBoxLayout()
            
            QP.AddToLayout( video_buffer_sizer, self._video_buffer_size_mb, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( video_buffer_sizer, self._estimated_number_video_frames, CC.FLAGS_CENTER_PERPENDICULAR )
            
            #
            
            text = 'Does not change much, thumbs are cheap.'
            
            st = ClientGUICommon.BetterStaticText( thumbnail_cache_panel, text )
            
            thumbnail_cache_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'MB memory reserved for thumbnail cache:', thumbnails_sizer ) )
            rows.append( ( 'Thumbnail cache timeout:', self._thumbnail_cache_timeout ) )
            
            gridbox = ClientGUICommon.WrapInGrid( thumbnail_cache_panel, rows )
            
            thumbnail_cache_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, thumbnail_cache_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            text = 'Important if you want smooth navigation between different images in the media viewer. If you deal with huge images, bump up cache size and max size that can be cached or prefetched, but be prepared to pay the memory price.'
            text += os.linesep * 2
            text += 'Allowing more prefetch is great, but it needs CPU.'
            
            st = ClientGUICommon.BetterStaticText( image_cache_panel, text )
            
            st.setWordWrap( True )
            
            image_cache_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'MB memory reserved for image cache:', fullscreens_sizer ) )
            rows.append( ( 'Image cache timeout:', self._image_cache_timeout ) )
            rows.append( ( 'Maximum image size (in % of cache) that can be cached:', image_cache_storage_sizer ) )
            rows.append( ( 'Maximum image size (in % of cache) that will be prefetched:', image_cache_prefetch_sizer ) )
            rows.append( ( 'Base ms delay for media viewer neighbour render prefetch:', self._media_viewer_prefetch_delay_base_ms ) )
            rows.append( ( 'Num previous to prefetch:', self._media_viewer_prefetch_num_previous ) )
            rows.append( ( 'Num next to prefetch:', self._media_viewer_prefetch_num_next ) )
            
            gridbox = ClientGUICommon.WrapInGrid( image_cache_panel, rows )
            
            image_cache_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, image_cache_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            text = 'Important if you do a lot of zooming in and out on the same image or a small number of comparison images.'
            
            st = ClientGUICommon.BetterStaticText( image_tile_cache_panel, text )
            
            image_tile_cache_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'MB memory reserved for image tile cache:', image_tiles_sizer ) )
            rows.append( ( 'Image tile cache timeout:', self._image_tile_cache_timeout ) )
            rows.append( ( 'Ideal tile width/height px:', self._ideal_tile_dimension ) )
            
            gridbox = ClientGUICommon.WrapInGrid( image_tile_cache_panel, rows )
            
            image_tile_cache_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, image_tile_cache_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            text = 'This old option does not apply to mpv! It only applies to the native hydrus animation renderer!'
            text += os.linesep
            text += 'Hydrus video rendering is CPU intensive.'
            text += os.linesep
            text += 'If you have a lot of memory, you can set a generous potential video buffer to compensate.'
            text += os.linesep
            text += 'If the video buffer can hold an entire video, it only needs to be rendered once and will play and loop very smoothly.'
            text += os.linesep
            text += 'PROTIP: Do not go crazy here.'
            
            st = ClientGUICommon.BetterStaticText( buffer_panel, text )
            
            st.setWordWrap( True )
            
            buffer_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'MB memory for video buffer: ', video_buffer_sizer ) )
            
            gridbox = ClientGUICommon.WrapInGrid( buffer_panel, rows )
            
            buffer_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, buffer_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Forced system:limit for all searches: ', self._forced_search_limit ) )
            
            gridbox = ClientGUICommon.WrapInGrid( misc_panel, rows )
            
            misc_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, misc_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
            #
            
            self._image_cache_storage_limit_percentage.valueChanged.connect( self.EventImageCacheUpdate )
            self._image_cache_prefetch_limit_percentage.valueChanged.connect( self.EventImageCacheUpdate )
            
            self.EventImageCacheUpdate()
            self.EventThumbnailsUpdate( self._thumbnail_cache_size.value() )
            self.EventImageTilesUpdate()
            self.EventVideoBufferUpdate( self._video_buffer_size_mb.value() )
            
        
        def EventImageCacheUpdate( self ):
            
            cache_size = self._fullscreen_cache_size.value() * 1048576
            
            display_size = ClientGUIFunctions.GetDisplaySize( self )
            
            estimated_bytes_per_fullscreen = 3 * display_size.width() * display_size.height()
            
            estimate = cache_size // estimated_bytes_per_fullscreen
            
            self._estimated_number_fullscreens.setText( '(about {}-{} images the size of your screen)'.format( HydrusData.ToHumanInt( estimate // 2 ), HydrusData.ToHumanInt( estimate * 2 ) ) )
            
            num_pixels = cache_size * ( self._image_cache_storage_limit_percentage.value() / 100 ) / 3
            
            unit_square = num_pixels / ( 16 * 9 )
            
            unit_length = unit_square ** 0.5
            
            resolution = ( int( 16 * unit_length ), int( 9 * unit_length ) )
            
            self._image_cache_storage_limit_percentage_st.setText( 'about a {} image'.format( HydrusData.ConvertResolutionToPrettyString( resolution ) ) )
            
            num_pixels = cache_size * ( self._image_cache_prefetch_limit_percentage.value() / 100 ) / 3
            
            unit_square = num_pixels / ( 16 * 9 )
            
            unit_length = unit_square ** 0.5
            
            resolution = ( int( 16 * unit_length ), int( 9 * unit_length ) )
            
            self._image_cache_prefetch_limit_percentage_st.setText( 'about a {} image'.format( HydrusData.ConvertResolutionToPrettyString( resolution ) ) )
            
        
        def EventImageTilesUpdate( self ):
            
            value = self._image_tile_cache_size.GetValue()
            
            display_size = ClientGUIFunctions.GetDisplaySize( self )
            
            estimated_bytes_per_fullscreen = 3 * display_size.width() * display_size.height()
            
            estimate = value // estimated_bytes_per_fullscreen
            
            self._estimated_number_image_tiles.setText( '(about {} fullscreens)'.format( HydrusData.ToHumanInt( estimate ) ) )
            
        
        def EventThumbnailsUpdate( self, value ):
            
            ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
            
            res_string = HydrusData.ConvertResolutionToPrettyString( ( thumbnail_width, thumbnail_height ) )
            
            estimated_bytes_per_thumb = 3 * thumbnail_width * thumbnail_height
            
            estimated_thumbs = ( value * 1024 * 1024 ) // estimated_bytes_per_thumb
            
            self._estimated_number_thumbnails.setText( '(at '+res_string+', about '+HydrusData.ToHumanInt(estimated_thumbs)+' thumbnails)' )
            
        
        def EventVideoBufferUpdate( self, value ):
            
            estimated_720p_frames = int( ( value * 1024 * 1024 ) // ( 1280 * 720 * 3 ) )
            
            self._estimated_number_video_frames.setText( '(about '+HydrusData.ToHumanInt(estimated_720p_frames)+' frames of 720p video)' )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'thumbnail_cache_size' ] = self._thumbnail_cache_size.value() * 1048576
            HC.options[ 'fullscreen_cache_size' ] = self._fullscreen_cache_size.value() * 1048576
            
            self._new_options.SetInteger( 'image_tile_cache_size', self._image_tile_cache_size.GetValue() )
            
            self._new_options.SetInteger( 'thumbnail_cache_timeout', self._thumbnail_cache_timeout.GetValue() )
            self._new_options.SetInteger( 'image_cache_timeout', self._image_cache_timeout.GetValue() )
            self._new_options.SetInteger( 'image_tile_cache_timeout', self._image_tile_cache_timeout.GetValue() )
            
            self._new_options.SetInteger( 'ideal_tile_dimension', self._ideal_tile_dimension.value() )
            
            self._new_options.SetInteger( 'media_viewer_prefetch_delay_base_ms', self._media_viewer_prefetch_delay_base_ms.value() )
            self._new_options.SetInteger( 'media_viewer_prefetch_num_previous', self._media_viewer_prefetch_num_previous.value() )
            self._new_options.SetInteger( 'media_viewer_prefetch_num_next', self._media_viewer_prefetch_num_next.value() )
            
            self._new_options.SetInteger( 'image_cache_storage_limit_percentage', self._image_cache_storage_limit_percentage.value() )
            self._new_options.SetInteger( 'image_cache_prefetch_limit_percentage', self._image_cache_prefetch_limit_percentage.value() )
            
            self._new_options.SetInteger( 'video_buffer_size_mb', self._video_buffer_size_mb.value() )
            
            self._new_options.SetNoneableInteger( 'forced_search_limit', self._forced_search_limit.GetValue() )
            
        
    
    class _StylePanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            self._qt_style_name = ClientGUICommon.BetterChoice( self )
            self._qt_stylesheet_name = ClientGUICommon.BetterChoice( self )
            
            self._qt_style_name.addItem( 'use default ("{}")'.format( ClientGUIStyle.ORIGINAL_STYLE_NAME ), None )
            
            try:
                
                for name in ClientGUIStyle.GetAvailableStyles():
                    
                    self._qt_style_name.addItem( name, name )
                    
                
            except HydrusExceptions.DataMissing as e:
                
                HydrusData.ShowException( e )
                
            
            self._qt_stylesheet_name.addItem( 'use default', None )
            
            try:
                
                for name in ClientGUIStyle.GetAvailableStylesheets():
                    
                    self._qt_stylesheet_name.addItem( name, name )
                    
                
            except HydrusExceptions.DataMissing as e:
                
                HydrusData.ShowException( e )
                
            
            #
            
            self._qt_style_name.SetValue( self._new_options.GetNoneableString( 'qt_style_name' ) )
            self._qt_stylesheet_name.SetValue( self._new_options.GetNoneableString( 'qt_stylesheet_name' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            #
            
            text = 'The current styles are what your Qt has available, the stylesheets are what .css and .qss files are currently in install_dir/static/qss.'
            
            st = ClientGUICommon.BetterStaticText( self, label = text )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Qt style:', self._qt_style_name ) )
            rows.append( ( 'Qt stylesheet:', self._qt_stylesheet_name ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.setLayout( vbox )
            
            self._qt_style_name.currentIndexChanged.connect( self.StyleChanged )
            self._qt_stylesheet_name.currentIndexChanged.connect( self.StyleChanged )
            
        
        def StyleChanged( self ):
            
            qt_style_name = self._qt_style_name.GetValue()
            qt_stylesheet_name = self._qt_stylesheet_name.GetValue()
            
            try:
                
                if qt_style_name is None:
                    
                    ClientGUIStyle.SetStyleFromName( ClientGUIStyle.ORIGINAL_STYLE_NAME )
                    
                else:
                    
                    ClientGUIStyle.SetStyleFromName( qt_style_name )
                    
                
            except Exception as e:
                
                QW.QMessageBox.critical( self, 'Critical', 'Could not apply style: {}'.format( str( e ) ) )
                
            
            try:
                
                if qt_stylesheet_name is None:
                    
                    ClientGUIStyle.ClearStylesheet()
                    
                else:
                    
                    ClientGUIStyle.SetStylesheetFromPath( qt_stylesheet_name )
                    
                
            except Exception as e:
                
                QW.QMessageBox.critical( self, 'Critical', 'Could not apply stylesheet: {}'.format( str( e ) ) )
                
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetNoneableString( 'qt_style_name', self._qt_style_name.GetValue() )
            self._new_options.SetNoneableString( 'qt_stylesheet_name', self._qt_stylesheet_name.GetValue() )
            
        
    
    class _SystemPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            sleep_panel = ClientGUICommon.StaticBox( self, 'system sleep' )
            
            self._wake_delay_period = QP.MakeQSpinBox( sleep_panel, min = 0, max = 60 )
            
            tt = 'It sometimes takes a few seconds for your network adapter to reconnect after a wake. This adds a grace period after a detected wake-from-sleep to allow your OS to sort that out before Hydrus starts making requests.'
            
            self._wake_delay_period.setToolTip( tt )
            
            self._file_system_waits_on_wakeup = QW.QCheckBox( sleep_panel )
            self._file_system_waits_on_wakeup.setToolTip( 'This is useful if your hydrus is stored on a NAS that takes a few seconds to get going after your machine resumes from sleep.' )
            
            #
            
            self._wake_delay_period.setValue( self._new_options.GetInteger( 'wake_delay_period' ) )
            
            self._file_system_waits_on_wakeup.setChecked( self._new_options.GetBoolean( 'file_system_waits_on_wakeup' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'After a wake from system sleep, wait this many seconds before allowing new network access:', self._wake_delay_period ) )
            rows.append( ( 'Include the file system in this wait: ', self._file_system_waits_on_wakeup ) )
            
            gridbox = ClientGUICommon.WrapInGrid( sleep_panel, rows )
            
            sleep_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, sleep_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetInteger( 'wake_delay_period', self._wake_delay_period.value() )
            self._new_options.SetBoolean( 'file_system_waits_on_wakeup', self._file_system_waits_on_wakeup.isChecked() )
            
        
    
    class _SystemTrayPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            self._always_show_system_tray_icon = QW.QCheckBox( self )
            self._minimise_client_to_system_tray = QW.QCheckBox( self )
            self._close_client_to_system_tray = QW.QCheckBox( self )
            self._start_client_in_system_tray = QW.QCheckBox( self )
            
            #
            
            self._always_show_system_tray_icon.setChecked( self._new_options.GetBoolean( 'always_show_system_tray_icon' ) )
            self._minimise_client_to_system_tray.setChecked( self._new_options.GetBoolean( 'minimise_client_to_system_tray' ) )
            self._close_client_to_system_tray.setChecked( self._new_options.GetBoolean( 'close_client_to_system_tray' ) )
            self._start_client_in_system_tray.setChecked( self._new_options.GetBoolean( 'start_client_in_system_tray' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Always show the hydrus system tray icon: ', self._always_show_system_tray_icon ) )
            rows.append( ( 'Minimise the main window to system tray: ', self._minimise_client_to_system_tray ) )
            rows.append( ( 'Close the main window to system tray: ', self._close_client_to_system_tray ) )
            rows.append( ( 'Start the client minimised to system tray: ', self._start_client_in_system_tray ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            from hydrus.client.gui import ClientGUISystemTray
            
            if not ClientGUISystemTray.SystemTrayAvailable():
                
                QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText( self, 'Unfortunately, your system does not seem to have a supported system tray.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
                
                self._always_show_system_tray_icon.setEnabled( False )
                self._minimise_client_to_system_tray.setEnabled( False )
                self._close_client_to_system_tray.setEnabled( False )
                self._start_client_in_system_tray.setEnabled( False )
                
            elif not HC.PLATFORM_WINDOWS:
                
                if not HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                    
                    label = 'This is turned off for non-advanced non-Windows users for now.'
                    
                    self._always_show_system_tray_icon.setEnabled( False )
                    self._minimise_client_to_system_tray.setEnabled( False )
                    self._close_client_to_system_tray.setEnabled( False )
                    self._start_client_in_system_tray.setEnabled( False )
                    
                else:
                    
                    label = 'This can be buggy/crashy on non-Windows, hydev will keep working on this.'
                    
                
                QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText( self, label ), CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'always_show_system_tray_icon', self._always_show_system_tray_icon.isChecked() )
            self._new_options.SetBoolean( 'minimise_client_to_system_tray', self._minimise_client_to_system_tray.isChecked() )
            self._new_options.SetBoolean( 'close_client_to_system_tray', self._close_client_to_system_tray.isChecked() )
            self._new_options.SetBoolean( 'start_client_in_system_tray', self._start_client_in_system_tray.isChecked() )
            
        
    
    class _TagsPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            general_panel = ClientGUICommon.StaticBox( self, 'general tag options' )
            
            self._default_tag_service_tab = ClientGUICommon.BetterChoice( general_panel )
            
            self._save_default_tag_service_tab_on_change = QW.QCheckBox( general_panel )
            
            self._default_tag_service_search_page = ClientGUICommon.BetterChoice( general_panel )
            
            self._expand_parents_on_storage_taglists = QW.QCheckBox( general_panel )
            self._expand_parents_on_storage_autocomplete_taglists = QW.QCheckBox( general_panel )
            self._ac_select_first_with_count = QW.QCheckBox( general_panel )
            
            #
            
            favourites_panel = ClientGUICommon.StaticBox( self, 'favourite tags' )
            
            desc = 'These tags will appear in your tag autocomplete results area, under the \'favourites\' tab.'
            
            favourites_st = ClientGUICommon.BetterStaticText( favourites_panel, desc )
            favourites_st.setWordWrap( True )
            
            default_location_context = HG.client_controller.services_manager.GetDefaultLocationContext()
            
            self._favourites = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( favourites_panel, CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE )
            self._favourites_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( favourites_panel, self._favourites.AddTags, default_location_context, CC.COMBINED_TAG_SERVICE_KEY, show_paste_button = True )
            
            #
            
            self._default_tag_service_search_page.addItem( 'all known tags', CC.COMBINED_TAG_SERVICE_KEY )
            
            services = HG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
            
            for service in services:
                
                self._default_tag_service_tab.addItem( service.GetName(), service.GetServiceKey() )
                
                self._default_tag_service_search_page.addItem( service.GetName(), service.GetServiceKey() )
                
            
            self._default_tag_service_tab.SetValue( self._new_options.GetKey( 'default_tag_service_tab' ) )
            
            self._save_default_tag_service_tab_on_change.setChecked( self._new_options.GetBoolean( 'save_default_tag_service_tab_on_change' ) )
            
            self._default_tag_service_search_page.SetValue( self._new_options.GetKey( 'default_tag_service_search_page' ) )
            
            self._expand_parents_on_storage_taglists.setChecked( self._new_options.GetBoolean( 'expand_parents_on_storage_taglists' ) )
            
            self._expand_parents_on_storage_taglists.setToolTip( 'This affects taglists in places like the manage tags dialog, where you edit tags as they actually are, and implied parents hang below tags.' )
            
            self._expand_parents_on_storage_autocomplete_taglists.setChecked( self._new_options.GetBoolean( 'expand_parents_on_storage_autocomplete_taglists' ) )
            
            self._expand_parents_on_storage_autocomplete_taglists.setToolTip( 'This affects the autocomplete results taglist.' )
            
            self._ac_select_first_with_count.setChecked( self._new_options.GetBoolean( 'ac_select_first_with_count' ) )
            
            #
            
            self._favourites.SetTags( self._new_options.GetStringList( 'favourite_tags' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Default tag service in manage tag dialogs: ', self._default_tag_service_tab ) )
            rows.append( ( 'Remember last used default tag service in manage tag dialogs: ', self._save_default_tag_service_tab_on_change ) )
            rows.append( ( 'Default tag service in search pages: ', self._default_tag_service_search_page ) )
            rows.append( ( 'Show parents expanded by default on edit/write taglists: ', self._expand_parents_on_storage_taglists ) )
            rows.append( ( 'Show parents expanded by default on edit/write autocomplete taglists: ', self._expand_parents_on_storage_autocomplete_taglists ) )
            rows.append( ( 'By default, select the first tag result with actual count in write-autocomplete: ', self._ac_select_first_with_count ) )
            
            gridbox = ClientGUICommon.WrapInGrid( general_panel, rows )
            
            general_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, general_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            favourites_panel.Add( favourites_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            favourites_panel.Add( self._favourites, CC.FLAGS_EXPAND_BOTH_WAYS )
            favourites_panel.Add( self._favourites_input )
            
            QP.AddToLayout( vbox, favourites_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            self.setLayout( vbox )
            
            #
            
            self._save_default_tag_service_tab_on_change.clicked.connect( self._UpdateDefaultTagServiceControl )
            
            self._UpdateDefaultTagServiceControl()
            
        
        def _UpdateDefaultTagServiceControl( self ):
            
            enabled = not self._save_default_tag_service_tab_on_change.isChecked()
            
            self._default_tag_service_tab.setEnabled( enabled )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetKey( 'default_tag_service_tab', self._default_tag_service_tab.GetValue() )
            self._new_options.SetBoolean( 'save_default_tag_service_tab_on_change', self._save_default_tag_service_tab_on_change.isChecked() )
            
            self._new_options.SetKey( 'default_tag_service_search_page', self._default_tag_service_search_page.GetValue() )
            
            self._new_options.SetBoolean( 'expand_parents_on_storage_taglists', self._expand_parents_on_storage_taglists.isChecked() )
            self._new_options.SetBoolean( 'expand_parents_on_storage_autocomplete_taglists', self._expand_parents_on_storage_autocomplete_taglists.isChecked() )
            self._new_options.SetBoolean( 'ac_select_first_with_count', self._ac_select_first_with_count.isChecked() )
            
            #
            
            self._new_options.SetStringList( 'favourite_tags', list( self._favourites.GetTags() ) )
            
        
    
    class _TagPresentationPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            tag_summary_generator = self._new_options.GetTagSummaryGenerator( 'thumbnail_top' )
            
            self._thumbnail_top = ClientGUITags.TagSummaryGeneratorButton( self, tag_summary_generator )
            
            tag_summary_generator = self._new_options.GetTagSummaryGenerator( 'thumbnail_bottom_right' )
            
            self._thumbnail_bottom_right = ClientGUITags.TagSummaryGeneratorButton( self, tag_summary_generator )
            
            tag_summary_generator = self._new_options.GetTagSummaryGenerator( 'media_viewer_top' )
            
            self._media_viewer_top = ClientGUITags.TagSummaryGeneratorButton( self, tag_summary_generator )
            
            #
            
            render_panel = ClientGUICommon.StaticBox( self, 'namespace rendering' )
            
            render_st = ClientGUICommon.BetterStaticText( render_panel, label = 'Namespaced tags are stored and directly edited in hydrus as "namespace:subtag", but most presentation windows can display them differently.' )
            
            self._show_namespaces = QW.QCheckBox( render_panel )
            self._namespace_connector = QW.QLineEdit( render_panel )
            
            self._replace_tag_underscores_with_spaces = QW.QCheckBox( render_panel )
            
            #
            
            namespace_colours_panel = ClientGUICommon.StaticBox( self, 'namespace colours' )
            
            self._namespace_colours = ClientGUIListBoxes.ListBoxTagsColourOptions( namespace_colours_panel, HC.options[ 'namespace_colours' ] )
            
            self._edit_namespace_colour = QW.QPushButton( 'edit selected', namespace_colours_panel )
            self._edit_namespace_colour.clicked.connect( self.EventEditNamespaceColour )
            
            self._new_namespace_colour = QW.QLineEdit( namespace_colours_panel )
            self._new_namespace_colour.installEventFilter( ClientGUICommon.TextCatchEnterEventFilter( self._new_namespace_colour, self.AddNamespaceColour ) )
            
            #
            
            self._show_namespaces.setChecked( new_options.GetBoolean( 'show_namespaces' ) )
            self._namespace_connector.setText( new_options.GetString( 'namespace_connector' ) )
            self._replace_tag_underscores_with_spaces.setChecked( new_options.GetBoolean( 'replace_tag_underscores_with_spaces' ) )
            
            #
            
            namespace_colours_panel.Add( self._namespace_colours, CC.FLAGS_EXPAND_BOTH_WAYS )
            namespace_colours_panel.Add( self._new_namespace_colour, CC.FLAGS_EXPAND_PERPENDICULAR )
            namespace_colours_panel.Add( self._edit_namespace_colour, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            #
            
            rows = []
            
            rows.append( ( 'On thumbnail top:', self._thumbnail_top ) )
            rows.append( ( 'On thumbnail bottom-right:', self._thumbnail_bottom_right ) )
            rows.append( ( 'On media viewer top:', self._media_viewer_top ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Show namespaces: ', self._show_namespaces ) )
            rows.append( ( 'If shown, namespace connecting string: ', self._namespace_connector ) )
            rows.append( ( 'EXPERIMENTAL: Replace all underscores with spaces: ', self._replace_tag_underscores_with_spaces ) )
            
            gridbox = ClientGUICommon.WrapInGrid( render_panel, rows )
            
            render_panel.Add( render_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            render_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, render_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            QP.AddToLayout( vbox, namespace_colours_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            self.setLayout( vbox )
            
        
        def EventEditNamespaceColour( self ):
            
            results = self._namespace_colours.GetSelectedNamespaceColours()
            
            for ( namespace, ( r, g, b ) ) in list( results.items() ):
                
                colour = QG.QColor( r, g, b )
                
                colour = QW.QColorDialog.getColor( colour, self, 'Namespace colour', QW.QColorDialog.ShowAlphaChannel )
                
                if colour.isValid():
                
                    self._namespace_colours.SetNamespaceColour( namespace, colour )
                    
                
            
        
        def AddNamespaceColour( self ):
            
            namespace = self._new_namespace_colour.text()
            
            if namespace != '':
                
                self._namespace_colours.SetNamespaceColour( namespace, QG.QColor( random.randint(0,255), random.randint(0,255), random.randint(0,255) ) )
                
                self._new_namespace_colour.clear()
                
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetTagSummaryGenerator( 'thumbnail_top', self._thumbnail_top.GetValue() )
            self._new_options.SetTagSummaryGenerator( 'thumbnail_bottom_right', self._thumbnail_bottom_right.GetValue() )
            self._new_options.SetTagSummaryGenerator( 'media_viewer_top', self._media_viewer_top.GetValue() )
            
            self._new_options.SetBoolean( 'show_namespaces', self._show_namespaces.isChecked() )
            self._new_options.SetString( 'namespace_connector', self._namespace_connector.text() )
            self._new_options.SetBoolean( 'replace_tag_underscores_with_spaces', self._replace_tag_underscores_with_spaces.isChecked() )
            
            HC.options[ 'namespace_colours' ] = self._namespace_colours.GetNamespaceColours()
            
        
    
    class _TagSuggestionsPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            suggested_tags_panel = ClientGUICommon.StaticBox( self, 'suggested tags' )
            
            self._suggested_tags_width = QP.MakeQSpinBox( suggested_tags_panel, min=20, max=65535 )
            
            self._suggested_tags_layout = ClientGUICommon.BetterChoice( suggested_tags_panel )
            
            self._suggested_tags_layout.addItem( 'notebook', 'notebook' )
            self._suggested_tags_layout.addItem( 'side-by-side', 'columns' )
            
            suggest_tags_panel_notebook = QW.QTabWidget( suggested_tags_panel )
            
            #
            
            suggested_tags_favourites_panel = QW.QWidget( suggest_tags_panel_notebook )
            
            suggested_tags_favourites_panel.setMinimumWidth( 400 )
            
            self._suggested_favourites_services = ClientGUICommon.BetterChoice( suggested_tags_favourites_panel )
            
            tag_services = HG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
            
            for tag_service in tag_services:
                
                self._suggested_favourites_services.addItem( tag_service.GetName(), tag_service.GetServiceKey() )
                
            
            self._suggested_favourites = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( suggested_tags_favourites_panel, CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE )
            
            self._current_suggested_favourites_service = None
            
            self._suggested_favourites_dict = {}
            
            default_location_context = HG.client_controller.services_manager.GetDefaultLocationContext()
            
            self._suggested_favourites_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( suggested_tags_favourites_panel, self._suggested_favourites.AddTags, default_location_context, CC.COMBINED_TAG_SERVICE_KEY, show_paste_button = True )
            
            #
            
            suggested_tags_related_panel = QW.QWidget( suggest_tags_panel_notebook )
            
            self._show_related_tags = QW.QCheckBox( suggested_tags_related_panel )
            
            self._related_tags_search_1_duration_ms = QP.MakeQSpinBox( suggested_tags_related_panel, min=50, max=60000 )
            self._related_tags_search_2_duration_ms = QP.MakeQSpinBox( suggested_tags_related_panel, min=50, max=60000 )
            self._related_tags_search_3_duration_ms = QP.MakeQSpinBox( suggested_tags_related_panel, min=50, max=60000 )
            
            #
            
            suggested_tags_file_lookup_script_panel = QW.QWidget( suggest_tags_panel_notebook )
            
            self._show_file_lookup_script_tags = QW.QCheckBox( suggested_tags_file_lookup_script_panel )
            
            self._favourite_file_lookup_script = ClientGUICommon.BetterChoice( suggested_tags_file_lookup_script_panel )
            
            script_names = sorted( HG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP ) )
            
            for name in script_names:
                
                self._favourite_file_lookup_script.addItem( name, name )
                
            
            #
            
            suggested_tags_recent_panel = QW.QWidget( suggest_tags_panel_notebook )
            
            self._num_recent_tags = ClientGUICommon.NoneableSpinCtrl( suggested_tags_recent_panel, 'number of recent tags to show', min = 1, none_phrase = 'do not show' )
            
            #
            
            self._suggested_tags_width.setValue( self._new_options.GetInteger( 'suggested_tags_width' ) )
            
            self._suggested_tags_layout.SetValue( self._new_options.GetNoneableString( 'suggested_tags_layout' ) )
            
            self._show_related_tags.setChecked( self._new_options.GetBoolean( 'show_related_tags' ) )
            
            self._related_tags_search_1_duration_ms.setValue( self._new_options.GetInteger( 'related_tags_search_1_duration_ms' ) )
            self._related_tags_search_2_duration_ms.setValue( self._new_options.GetInteger( 'related_tags_search_2_duration_ms' ) )
            self._related_tags_search_3_duration_ms.setValue( self._new_options.GetInteger( 'related_tags_search_3_duration_ms' ) )
            
            self._show_file_lookup_script_tags.setChecked( self._new_options.GetBoolean( 'show_file_lookup_script_tags' ) )
            
            self._favourite_file_lookup_script.SetValue( self._new_options.GetNoneableString( 'favourite_file_lookup_script' ) )
            
            self._num_recent_tags.SetValue( self._new_options.GetNoneableInteger( 'num_recent_tags' ) )
            
            #
            
            panel_vbox = QP.VBoxLayout()
            
            QP.AddToLayout( panel_vbox, self._suggested_favourites_services, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( panel_vbox, self._suggested_favourites, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( panel_vbox, self._suggested_favourites_input, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            suggested_tags_favourites_panel.setLayout( panel_vbox )
            
            #
            
            panel_vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Show related tags on single-file manage tags windows: ', self._show_related_tags ) )
            rows.append( ( 'Initial search duration (ms): ', self._related_tags_search_1_duration_ms ) )
            rows.append( ( 'Medium search duration (ms): ', self._related_tags_search_2_duration_ms ) )
            rows.append( ( 'Thorough search duration (ms): ', self._related_tags_search_3_duration_ms ) )
            
            gridbox = ClientGUICommon.WrapInGrid( suggested_tags_related_panel, rows )
            
            desc = 'This will search the database for statistically related tags based on what your focused file already has.'
            
            QP.AddToLayout( panel_vbox, ClientGUICommon.BetterStaticText(suggested_tags_related_panel,desc), CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( panel_vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            suggested_tags_related_panel.setLayout( panel_vbox )
            
            #
            
            panel_vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Show file lookup scripts on single-file manage tags windows: ', self._show_file_lookup_script_tags ) )
            rows.append( ( 'Favourite file lookup script: ', self._favourite_file_lookup_script ) )
            
            gridbox = ClientGUICommon.WrapInGrid( suggested_tags_file_lookup_script_panel, rows )
            
            QP.AddToLayout( panel_vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            suggested_tags_file_lookup_script_panel.setLayout( panel_vbox )
            
            #
            
            panel_vbox = QP.VBoxLayout()
            
            QP.AddToLayout( panel_vbox, self._num_recent_tags, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            panel_vbox.addStretch( 1 )
            
            suggested_tags_recent_panel.setLayout( panel_vbox )
            
            #
            
            suggest_tags_panel_notebook.addTab( suggested_tags_favourites_panel, 'favourites' )
            suggest_tags_panel_notebook.addTab( suggested_tags_related_panel, 'related' )
            suggest_tags_panel_notebook.addTab( suggested_tags_file_lookup_script_panel, 'file lookup scripts' )
            suggest_tags_panel_notebook.addTab( suggested_tags_recent_panel, 'recent' )
            
            #
            
            rows = []
            
            rows.append( ( 'Width of suggested tags columns: ', self._suggested_tags_width ) )
            rows.append( ( 'Column layout: ', self._suggested_tags_layout ) )
            
            gridbox = ClientGUICommon.WrapInGrid( suggested_tags_panel, rows )
            
            desc = 'The manage tags dialog can provide several kinds of tag suggestions. For simplicity, most are turned off by default.'
            
            suggested_tags_panel.Add( ClientGUICommon.BetterStaticText( suggested_tags_panel, desc ), CC.FLAGS_EXPAND_PERPENDICULAR )
            suggested_tags_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            suggested_tags_panel.Add( suggest_tags_panel_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, suggested_tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
            #
            
            self._suggested_favourites_services.currentIndexChanged.connect( self.EventSuggestedFavouritesService )
            
            self.EventSuggestedFavouritesService( None )
            
        
        def _SaveCurrentSuggestedFavourites( self ):
            
            if self._current_suggested_favourites_service is not None:
                
                self._suggested_favourites_dict[ self._current_suggested_favourites_service ] = self._suggested_favourites.GetTags()
                
            
        
        def EventSuggestedFavouritesService( self, index ):
            
            self._SaveCurrentSuggestedFavourites()
            
            self._current_suggested_favourites_service = self._suggested_favourites_services.GetValue()
            
            if self._current_suggested_favourites_service in self._suggested_favourites_dict:
                
                favourites = self._suggested_favourites_dict[ self._current_suggested_favourites_service ]
                
            else:
                
                favourites = self._new_options.GetSuggestedTagsFavourites( self._current_suggested_favourites_service )
                
            
            self._suggested_favourites.SetTagServiceKey( self._current_suggested_favourites_service )
            
            self._suggested_favourites.SetTags( favourites )
            
            self._suggested_favourites_input.SetTagServiceKey( self._current_suggested_favourites_service )
            self._suggested_favourites_input.SetDisplayTagServiceKey( self._current_suggested_favourites_service )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetInteger( 'suggested_tags_width', self._suggested_tags_width.value() )
            self._new_options.SetNoneableString( 'suggested_tags_layout', self._suggested_tags_layout.GetValue() )
            
            self._SaveCurrentSuggestedFavourites()
            
            for ( service_key, favourites ) in list(self._suggested_favourites_dict.items()):
                
                self._new_options.SetSuggestedTagsFavourites( service_key, favourites )
                
            
            self._new_options.SetBoolean( 'show_related_tags', self._show_related_tags.isChecked() )
            
            self._new_options.SetInteger( 'related_tags_search_1_duration_ms', self._related_tags_search_1_duration_ms.value() )
            self._new_options.SetInteger( 'related_tags_search_2_duration_ms', self._related_tags_search_2_duration_ms.value() )
            self._new_options.SetInteger( 'related_tags_search_3_duration_ms', self._related_tags_search_3_duration_ms.value() )
            
            self._new_options.SetBoolean( 'show_file_lookup_script_tags', self._show_file_lookup_script_tags.isChecked() )
            self._new_options.SetNoneableString( 'favourite_file_lookup_script', self._favourite_file_lookup_script.GetValue() )
            
            self._new_options.SetNoneableInteger( 'num_recent_tags', self._num_recent_tags.GetValue() )
            
        
    
    class _ThumbnailsPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            self._thumbnail_width = QP.MakeQSpinBox( self, min=20, max=2048 )
            self._thumbnail_height = QP.MakeQSpinBox( self, min=20, max=2048 )
            
            self._thumbnail_border = QP.MakeQSpinBox( self, min=0, max=20 )
            self._thumbnail_margin = QP.MakeQSpinBox( self, min=0, max=20 )
            
            self._thumbnail_scale_type = ClientGUICommon.BetterChoice( self )
            
            self._video_thumbnail_percentage_in = QP.MakeQSpinBox( self, min=0, max=100 )
            
            for t in ( HydrusImageHandling.THUMBNAIL_SCALE_DOWN_ONLY, HydrusImageHandling.THUMBNAIL_SCALE_TO_FIT, HydrusImageHandling.THUMBNAIL_SCALE_TO_FILL ):
                
                self._thumbnail_scale_type.addItem( HydrusImageHandling.thumbnail_scale_str_lookup[ t ], t )
                
            
            self._thumbnail_scroll_rate = QW.QLineEdit( self )
            
            self._thumbnail_visibility_scroll_percent = QP.MakeQSpinBox( self, min=1, max=99 )
            self._thumbnail_visibility_scroll_percent.setToolTip( 'Lower numbers will cause fewer scrolls, higher numbers more.' )
            
            self._media_background_bmp_path = QP.FilePickerCtrl( self )
            
            #
            
            ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
            
            self._thumbnail_width.setValue( thumbnail_width )
            self._thumbnail_height.setValue( thumbnail_height )
            
            self._thumbnail_border.setValue( self._new_options.GetInteger( 'thumbnail_border' ) )
            self._thumbnail_margin.setValue( self._new_options.GetInteger( 'thumbnail_margin' ) )
            
            self._thumbnail_scale_type.SetValue( self._new_options.GetInteger( 'thumbnail_scale_type' ) )
            
            self._video_thumbnail_percentage_in.setValue( self._new_options.GetInteger( 'video_thumbnail_percentage_in' ) )
            
            self._thumbnail_scroll_rate.setText( self._new_options.GetString( 'thumbnail_scroll_rate' ) )
            
            self._thumbnail_visibility_scroll_percent.setValue( self._new_options.GetInteger( 'thumbnail_visibility_scroll_percent' ) )
            
            media_background_bmp_path = self._new_options.GetNoneableString( 'media_background_bmp_path' )
            
            if media_background_bmp_path is not None:
                
                self._media_background_bmp_path.SetPath( media_background_bmp_path )
                
            
            #
            
            rows = []
            
            rows.append( ( 'Thumbnail width: ', self._thumbnail_width ) )
            rows.append( ( 'Thumbnail height: ', self._thumbnail_height ) )
            rows.append( ( 'Thumbnail border: ', self._thumbnail_border ) )
            rows.append( ( 'Thumbnail margin: ', self._thumbnail_margin ) )
            rows.append( ( 'Thumbnail scaling: ', self._thumbnail_scale_type ) )
            rows.append( ( 'Generate video thumbnails this % in: ', self._video_thumbnail_percentage_in ) )
            rows.append( ( 'Do not scroll down on key navigation if thumbnail at least this % visible: ', self._thumbnail_visibility_scroll_percent ) )
            rows.append( ( 'EXPERIMENTAL: Scroll thumbnails at this rate per scroll tick: ', self._thumbnail_scroll_rate ) )
            rows.append( ( 'EXPERIMENTAL: Image path for thumbnail panel background image (set blank to clear): ', self._media_background_bmp_path ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            new_thumbnail_dimensions = [self._thumbnail_width.value(), self._thumbnail_height.value()]
            
            HC.options[ 'thumbnail_dimensions' ] = new_thumbnail_dimensions
            
            self._new_options.SetInteger( 'thumbnail_border', self._thumbnail_border.value() )
            self._new_options.SetInteger( 'thumbnail_margin', self._thumbnail_margin.value() )
            
            self._new_options.SetInteger( 'thumbnail_scale_type', self._thumbnail_scale_type.GetValue() )
            
            self._new_options.SetInteger( 'video_thumbnail_percentage_in', self._video_thumbnail_percentage_in.value() )
            
            try:
                
                thumbnail_scroll_rate = self._thumbnail_scroll_rate.text()
                
                float( thumbnail_scroll_rate )
                
                self._new_options.SetString( 'thumbnail_scroll_rate', thumbnail_scroll_rate )
                
            except:
                
                pass
                
            
            self._new_options.SetInteger( 'thumbnail_visibility_scroll_percent', self._thumbnail_visibility_scroll_percent.value() )
            
            media_background_bmp_path = self._media_background_bmp_path.GetPath()
            
            if media_background_bmp_path == '':
                
                media_background_bmp_path = None
                
            
            self._new_options.SetNoneableString( 'media_background_bmp_path', media_background_bmp_path )
            
        
    
    def CommitChanges( self ):
        
        for page in self._listbook.GetActivePages():
            
            page.UpdateOptions()
            
        
        try:
            
            HG.client_controller.WriteSynchronous( 'save_options', HC.options )
            
            HG.client_controller.WriteSynchronous( 'serialisable', self._new_options )
            
        except:
            
            QW.QMessageBox.critical( self, 'Error', traceback.format_exc() )
            
        
    
class ManageURLsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, media ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        media = ClientMedia.FlattenMedia( media )
        
        self._current_media = [ m.Duplicate() for m in media ]
        
        self._multiple_files_warning = ClientGUICommon.BetterStaticText( self, label = 'Warning: you are editing urls for multiple files!\nBe very careful about adding URLs here, as they will apply to everything.\nAdding the same URL to multiple files is only appropriate for gallery-type URLs!' )
        self._multiple_files_warning.setObjectName( 'HydrusWarning' )
        
        if len( self._current_media ) == 1:
            
            self._multiple_files_warning.hide()
            
        
        self._urls_listbox = QW.QListWidget( self )
        self._urls_listbox.setSortingEnabled( True )
        self._urls_listbox.setSelectionMode( QW.QAbstractItemView.ExtendedSelection )
        self._urls_listbox.itemDoubleClicked.connect( self.EventListDoubleClick )
        self._listbox_event_filter = QP.WidgetEventFilter( self._urls_listbox )
        self._listbox_event_filter.EVT_KEY_DOWN( self.EventListKeyDown )
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._urls_listbox, ( 120, 10 ) )
        
        self._urls_listbox.setMinimumWidth( width )
        self._urls_listbox.setMinimumHeight( height )
        
        self._url_input = QW.QLineEdit( self )
        self._url_input.installEventFilter( ClientGUICommon.TextCatchEnterEventFilter( self._url_input, self.AddURL ) )
        
        self._copy_button = ClientGUICommon.BetterButton( self, 'copy all', self._Copy )
        self._paste_button = ClientGUICommon.BetterButton( self, 'paste', self._Paste )
        
        self._urls_to_add = set()
        self._urls_to_remove = set()
        
        #
        
        self._pending_content_updates = []
        
        self._current_urls_count = collections.Counter()
        
        self._UpdateList()
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._copy_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._multiple_files_warning, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._urls_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'global', 'media', 'main_gui' ] )
        
        ClientGUIFunctions.SetFocusLater( self._url_input )
        
    
    def _Copy( self ):
        
        urls = sorted( self._current_urls_count.keys() )
        
        text = os.linesep.join( urls )
        
        HG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _EnterURL( self, url, only_add = False ):
        
        normalised_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
        
        addee_media = set()
        
        for m in self._current_media:
            
            locations_manager = m.GetLocationsManager()
            
            if normalised_url not in locations_manager.GetURLs():
                
                addee_media.add( m )
                
            
        
        if len( addee_media ) > 0:
            
            addee_hashes = { m.GetHash() for m in addee_media }
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( ( normalised_url, ), addee_hashes ) )
            
            for m in addee_media:
                
                m.GetMediaResult().ProcessContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
                
            
            self._pending_content_updates.append( content_update )
            
        
        #
        
        self._UpdateList()
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.warning( self, 'Warning', str(e) )
            
            return
            
        
        try:
            
            for url in HydrusText.DeserialiseNewlinedTexts( raw_text ):
                
                if url != '':
                    
                    self._EnterURL( url, only_add = True )
                    
                
            
        except Exception as e:
            
            QW.QMessageBox.warning( self, 'Warning', 'I could not understand what was in the clipboard: {}'.format( e ) )
            
        
    
    def _RemoveURL( self, url ):
        
        removee_media = set()
        
        for m in self._current_media:
            
            locations_manager = m.GetLocationsManager()
            
            if url in locations_manager.GetURLs():
                
                removee_media.add( m )
                
            
        
        if len( removee_media ) > 0:
            
            removee_hashes = { m.GetHash() for m in removee_media }
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_DELETE, ( ( url, ), removee_hashes ) )
            
            for m in removee_media:
                
                m.GetMediaResult().ProcessContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
                
            
            self._pending_content_updates.append( content_update )
            
        
        #
        
        self._UpdateList()
        
    
    def _SetSearchFocus( self ):
        
        self._url_input.setFocus( QC.Qt.OtherFocusReason )
        
    
    def _UpdateList( self ):
        
        self._urls_listbox.clear()
        
        self._current_urls_count = collections.Counter()
        
        for m in self._current_media:
            
            locations_manager = m.GetLocationsManager()
            
            for url in locations_manager.GetURLs():
                
                self._current_urls_count[ url ] += 1
                
            
        
        for ( url, count ) in self._current_urls_count.items():
            
            if len( self._current_media ) == 1:
                
                label = url
                
            else:
                
                label = '{} ({})'.format( url, count )
                
            item = QW.QListWidgetItem()
            item.setText( label )
            item.setData( QC.Qt.UserRole, url )
            self._urls_listbox.addItem( item )
            
        
    
    def EventListDoubleClick( self, item ):
    
        urls = [ QP.GetClientData( self._urls_listbox, selection.row() ) for selection in list( self._urls_listbox.selectedIndexes() ) ]
        
        for url in urls:
            
            self._RemoveURL( url )
            
        
        if len( urls ) == 1:
            
            url = urls[0]
            
            self._url_input.setText( url )
            
        
    
    def EventListKeyDown( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key in ClientGUIShortcuts.DELETE_KEYS_QT:
            
            urls = [ QP.GetClientData( self._urls_listbox, selection.row() ) for selection in list( self._urls_listbox.selectedIndexes() ) ]
            
            for url in urls:
                
                self._RemoveURL( url )
                
            
        else:
            
            return True # was: event.ignore()
        
    
    def AddURL( self ):
        
        url = self._url_input.text()
        
        if url == '':
            
            self.parentWidget().DoOK()
            
        else:
            
            try:
                
                self._EnterURL( url )
                
                self._url_input.clear()
                
            except Exception as e:
                
                QW.QMessageBox.warning( self, 'Warning', 'I could not add that URL: {}'.format( e ) )
                
            
        
    
    def CommitChanges( self ):
        
        if len( self._pending_content_updates ) > 0:
            
            service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : self._pending_content_updates }
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_MANAGE_FILE_URLS:
                
                self._OKParent()
                
            elif action == CAC.SIMPLE_SET_SEARCH_FOCUS:
                
                self._SetSearchFocus()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
class RepairFileSystemPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, missing_locations ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._only_thumbs = True
        
        self._incorrect_locations = {}
        self._correct_locations = {}
        
        for ( incorrect_location, prefix ) in missing_locations:
            
            self._incorrect_locations[ prefix ] = incorrect_location
            
            if prefix.startswith( 'f' ):
                
                self._only_thumbs = False
                
            
        
        text = 'This dialog has launched because some expected file storage directories were not found. This is a serious error. You have two options:'
        text += os.linesep * 2
        text += '1) If you know what these should be (e.g. you recently remapped their external drive to another location), update the paths here manually. For most users, this will be clicking _add a possibly correct location_ and then select the new folder where the subdirectories all went. You can repeat this if your folders are missing in multiple locations. Check everything reports _ok!_'
        text += os.linesep * 2
        text += 'Although it is best if you can find everything, you only _have_ to fix the subdirectories starting with \'f\', which store your original files. Those starting \'t\' and \'r\' are for your thumbnails, which can be regenerated with a bit of work.'
        text += os.linesep * 2
        text += 'Then hit \'apply\', and the client will launch. You should double-check all your locations under database->migrate database immediately.'
        text += os.linesep * 2
        text += '2) If the locations are not available, or you do not know what they should be, or you wish to fix this outside of the program, hit \'cancel\' to gracefully cancel client boot. Feel free to contact hydrus dev for help.'
        
        if self._only_thumbs:
            
            text += os.linesep * 2
            text += 'SPECIAL NOTE FOR YOUR SITUATION: The only paths missing are thumbnail paths. If you cannot recover these folders, you can hit apply to create empty paths at the original or corrected locations and then run a maintenance routine to regenerate the thumbnails from their originals.'
            
        
        st = ClientGUICommon.BetterStaticText( self, text )
        st.setWordWrap( True )
        
        self._locations = ClientGUIListCtrl.BetterListCtrl( self, CGLC.COLUMN_LIST_REPAIR_LOCATIONS.ID, 12, self._ConvertPrefixToListCtrlTuples, activation_callback = self._SetLocations )
        
        self._set_button = ClientGUICommon.BetterButton( self, 'set correct location', self._SetLocations )
        self._add_button = ClientGUICommon.BetterButton( self, 'add a possibly correct location (let the client figure out what it contains)', self._AddLocation )
        
        # add a button here for 'try to fill them in for me'. you give it a dir, and it tries to figure out and fill in the prefixes for you
        
        #
        
        self._locations.AddDatas( [ prefix for ( incorrect_location, prefix ) in missing_locations ] )
        
        self._locations.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._locations, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._set_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._add_button, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
    
    def _AddLocation( self ):
        
        with QP.DirDialog( self, 'Select the potential correct location.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                for prefix in self._locations.GetData():
                    
                    ok = os.path.exists( os.path.join( path, prefix ) )
                    
                    if ok:
                        
                        self._correct_locations[ prefix ] = ( path, ok )
                        
                    
                
                self._locations.UpdateDatas()
                
            
        
    
    def _ConvertPrefixToListCtrlTuples( self, prefix ):
        
        incorrect_location = self._incorrect_locations[ prefix ]
        
        if prefix in self._correct_locations:
            
            ( correct_location, ok ) = self._correct_locations[ prefix ]
            
            if ok:
                
                pretty_ok = 'ok!'
                
            else:
                
                pretty_ok = 'not found'
                
            
        else:
            
            correct_location = ''
            ok = None
            pretty_ok = ''
            
        
        pretty_incorrect_location = incorrect_location
        pretty_prefix = prefix
        pretty_correct_location = correct_location
        
        display_tuple = ( pretty_incorrect_location, pretty_prefix, pretty_correct_location, pretty_ok )
        sort_tuple = ( incorrect_location, prefix, correct_location, ok )
        
        return ( display_tuple, sort_tuple )
        
    
    def _GetValue( self ):
        
        correct_rows = []
        
        thumb_problems = False
        
        for prefix in self._locations.GetData():
            
            incorrect_location = self._incorrect_locations[ prefix ]
            
            if prefix not in self._correct_locations:
                
                if prefix.startswith( 'f' ):
                    
                    raise HydrusExceptions.VetoException( 'You did not correct all the file locations!' )
                    
                else:
                    
                    thumb_problems = True
                    
                    correct_location = incorrect_location
                    
                
            else:
                
                ( correct_location, ok ) = self._correct_locations[ prefix ]
                
                if not ok:
                    
                    if prefix.startswith( 'f' ):
                        
                        raise HydrusExceptions.VetoException( 'You did not find all the correct file locations!' )
                        
                    else:
                        
                        thumb_problems = True
                        
                    
                
            
            correct_rows.append( ( prefix, correct_location ) )
            
        
        return ( correct_rows, thumb_problems )
        
    
    def _SetLocations( self ):
        
        prefixes = self._locations.GetData( only_selected = True )
        
        if len( prefixes ) > 0:
            
            with QP.DirDialog( self, 'Select correct location.' ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    path = dlg.GetPath()
                    
                    for prefix in prefixes:
                        
                        ok = os.path.exists( os.path.join( path, prefix ) )
                        
                        self._correct_locations[ prefix ] = ( path, ok )
                        
                    
                    self._locations.UpdateDatas()
                    
                
            
        
    
    def CheckValid( self ):
        
        # raises veto if invalid
        self._GetValue()
        
    
    def CommitChanges( self ):
        
        ( correct_rows, thumb_problems ) = self._GetValue()
        
        HG.client_controller.WriteSynchronous( 'repair_client_files', correct_rows )
        
    
    def UserIsOKToOK( self ):
        
        ( correct_rows, thumb_problems ) = self._GetValue()
        
        if thumb_problems:
            
            message = 'Some or all of your incorrect paths have not been corrected, but they are all thumbnail paths.'
            message += os.linesep * 2
            message += 'Would you like instead to create new empty subdirectories at the previous (or corrected, if you have entered them) locations?'
            message += os.linesep * 2
            message += 'You can run database->regenerate->thumbnails to fill them up again.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.Accepted:
                
                return False
                
            
        
        return True
        
