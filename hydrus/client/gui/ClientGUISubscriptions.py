import collections
import collections.abc
import threading
import time
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.importing import ClientGUIFileSeedCache
from hydrus.client.gui.importing import ClientGUIGallerySeedLog
from hydrus.client.gui.importing import ClientGUIImport
from hydrus.client.gui.importing import ClientGUIImportOptions
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.importing import ClientImporting
from hydrus.client.importing import ClientImportSubscriptions
from hydrus.client.importing import ClientImportSubscriptionQuery
from hydrus.client.importing import ClientImportSubscriptionLegacy # keep this here so the serialisable stuff is registered, it has to be imported somewhere

def DoAliveOrDeadCheck( win: QW.QWidget, subscriptions: collections.abc.Collection[ ClientImportSubscriptions.Subscription ], query_headers: collections.abc.Collection[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ] ):
    
    do_paused_subs = True
    
    num_paused_subs = sum( ( 1 for subscription in subscriptions if subscription.IsPaused() ) )
    
    if 0 < num_paused_subs:
        
        message = f'Of the {HydrusNumbers.ToHumanInt(len(subscriptions))} selected subscriptions, {HydrusNumbers.ToHumanInt(num_paused_subs)} are paused. Do you want to unpause these paused subs and check their queries?'
        
        if num_paused_subs == len( subscriptions ):
            
            choice_tuples = [
                ( f'yes, unpause them and check their queries', True, 'Unpause and check what is paused.' ),
                ( f'no, leave them alone', False, 'Exit out of this.' )
            ]
            
        else:
            
            choice_tuples = [
                ( f'yes, check queries within paused subs', True, 'Unpause and check what is paused.' ),
                ( f'no, just check within unpaused subs', False, 'Only check what is currently active.' )
            ]
            
        
        try:
            
            do_paused_subs = ClientGUIDialogsQuick.SelectFromListButtons( win, 'Check which?', choice_tuples, message = message )
            
        except HydrusExceptions.CancelledException:
            
            raise
            
        
    
    if len( subscriptions ) > 0 and len( query_headers ) == 0:
        
        if do_paused_subs:
            
            subs_to_pull_from = subscriptions
            
        else:
            
            subs_to_pull_from = [ subscription for subscription in subscriptions if not subscription.IsPaused() ]
            
        
        query_headers = HydrusLists.MassExtend( ( subscription.GetQueryHeaders() for subscription in subs_to_pull_from ) )
        
    
    do_alive = True
    do_dead = True
    
    num_dead = sum( ( 1 for query_header in query_headers if query_header.IsDead() ) )
    
    if 0 < num_dead:
        
        message = f'Of the {HydrusNumbers.ToHumanInt(len(query_headers))} selected queries, {HydrusNumbers.ToHumanInt(num_dead)} are DEAD. Do you want to check these?'
        
        if num_dead == len( query_headers ):
            
            choice_tuples = [
                ( f'yes, resurrect the DEAD queries', ( False, True ), 'Resuscitate the DEAD queries and check everything.' ),
                ( f'no, leave them DEAD', ( False, False ), 'Exit out of this.' )
            ]
            
        else:
            
            choice_tuples = [
                ( f'yes, check all of them', ( True, True ), 'Resuscitate the DEAD queries and check everything.' ),
                ( f'check the {HydrusNumbers.ToHumanInt(len(query_headers)-num_dead)} ALIVE', ( True, False ), 'Check the ALIVE queries.' ),
                ( f'resurrect and check the {HydrusNumbers.ToHumanInt(num_dead)} DEAD', ( False, True ), 'Resuscitate the DEAD queries and check them.' )
            ]
            
        
        try:
            
            ( do_alive, do_dead ) = ClientGUIDialogsQuick.SelectFromListButtons( win, 'Check which?', choice_tuples, message = message )
            
        except HydrusExceptions.CancelledException:
            
            raise
            
        
    
    if not do_alive:
        
        query_headers = [ query_header for query_header in query_headers if query_header.IsDead() ]
        
    
    if not do_dead:
        
        query_headers = [ query_header for query_header in query_headers if not query_header.IsDead() ]
        
    
    do_paused_queries = True
    
    num_paused_queries = sum( ( 1 for query_header in query_headers if query_header.IsPaused() ) )
    
    if 0 < num_paused_queries:
        
        message = f'Of the {HydrusNumbers.ToHumanInt(len(query_headers))} selected queries, {HydrusNumbers.ToHumanInt(num_paused_queries)} are paused. Do you want to unpause and check them?'
        
        if num_paused_queries == len( query_headers ):
            
            choice_tuples = [
                ( f'yes, check them', True, 'Unpause and check what is paused.' ),
                ( f'no, leave them alone', False, 'Exit out of this.' )
            ]
            
        else:
            
            choice_tuples = [
                ( f'yes check paused queries', True, 'Unpause and check what is paused.' ),
                ( f'no just what is currently unpaused', False, 'Only check what is currently active.' )
            ]
            
        
        try:
            
            do_paused_queries = ClientGUIDialogsQuick.SelectFromListButtons( win, 'Check which?', choice_tuples, message = message )
            
        except HydrusExceptions.CancelledException:
            
            raise
            
        
    
    return ( do_alive, do_dead, do_paused_subs, do_paused_queries )
    

def GetQueryHeadersQualityInfo( query_headers: collections.abc.Iterable[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ] ):
    
    data = []
    
    for query_header in query_headers:
        
        try:
            
            query_log_container = CG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER, query_header.GetQueryLogContainerName() )
            
        except HydrusExceptions.DataMissing:
            
            continue
            
        
        fsc = query_log_container.GetFileSeedCache()
        
        hashes = fsc.GetHashes()
        
        media_results = CG.client_controller.Read( 'media_results', hashes )
        
        num_inbox = 0
        num_archived = 0
        num_deleted = 0
        
        for media_result in media_results:
            
            lm = media_result.GetLocationsManager()
            
            if lm.IsLocal() and not lm.IsTrashed():
                
                if media_result.GetInbox():
                    
                    num_inbox += 1
                    
                else:
                    
                    num_archived += 1
                    
                
            else:
                
                num_deleted += 1
                
            
        
        data.append( ( query_header.GetHumanName(), num_inbox, num_archived, num_deleted ) )
        
    
    return data
    
def GetQueryLogContainers( query_headers: collections.abc.Iterable[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ] ):
    
    query_log_containers = []
    
    for query_header in query_headers:
        
        try:
            
            query_log_container = CG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER, query_header.GetQueryLogContainerName() )
            
        except HydrusExceptions.DBException as e:
            
            if isinstance( e.db_e, HydrusExceptions.DataMissing ):
                
                continue
                
            else:
                
                raise
                
            
        
        query_log_containers.append( query_log_container )
        
    
    return query_log_containers
    

class EditSubscriptionPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, subscription: ClientImportSubscriptions.Subscription, names_to_edited_query_log_containers: typing.Mapping[ str, ClientImportSubscriptionQuery.SubscriptionQueryLogContainer ], original_existing_query_log_container_names: set[ str ] ):
        
        subscription = subscription.Duplicate()
        
        super().__init__( parent )
        
        self._original_subscription = subscription
        self._names_to_edited_query_log_containers = dict( names_to_edited_query_log_containers )
        self._original_existing_query_log_container_names = original_existing_query_log_container_names
        
        #
        
        menu_template_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_GETTING_STARTED_SUBSCRIPTIONS )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the html subscriptions help', 'Open the help page for subscriptions in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        self._name = QW.QLineEdit( self )
        self._delay_st = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        
        self._delay_st.setWordWrap( True )
        
        #
        
        ( name, gug_key_and_name, query_headers, checker_options, initial_file_limit, periodic_file_limit, paused, file_import_options, tag_import_options, self._no_work_until, self._no_work_until_reason ) = subscription.ToTuple()
        this_is_a_random_sample_sub = subscription.ThisIsARandomSampleSubscription()
        
        self._query_panel = ClientGUICommon.StaticBox( self, 'site and queries' )
        
        label = 'You have selected a downloader that appears to download from multiple sites. Subscriptions make careful timing calculations based on file velocity, and multiple sites offering new files at different times will confuse things! Also, errors or certain search 404s that block a sub query will stop work for all sites in the downloader. Unless you are certain this complex downloader sources data from the same unified stream behind the scenes, and this single website simply has a complicated multi-domain setup, I strongly recommend you duplicate this whole subscription in the dialog above and set each duplicate to check each respective site separately. The subs will clear faster, and your check timings and DEAD results will be far more efficient and reliable!'
        
        self._multi_domain_ngug_warning_label = ClientGUICommon.BetterStaticText( self._query_panel, label = label )
        self._multi_domain_ngug_warning_label.setWordWrap( True )
        self._multi_domain_ngug_warning_label.setObjectName( 'HydrusWarning' )
        self._multi_domain_ngug_warning_label.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        self._gug_key_and_name = ClientGUIImport.GUGKeyAndNameSelector( self._query_panel, gug_key_and_name )
        
        queries_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._query_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_SUBSCRIPTION_QUERIES.ID, self._ConvertQueryHeaderToDisplayTuple, self._ConvertQueryHeaderToSortTuple )
        
        self._query_headers = ClientGUIListCtrl.BetterListCtrlTreeView( queries_panel, 10, model, use_simple_delete = True, activation_callback = self._EditQuery )
        
        queries_panel.SetListCtrl( self._query_headers )
        
        queries_panel.AddButton( 'add', self._AddQuery )
        queries_panel.AddButton( 'copy queries', self._CopyQueries, enabled_only_on_selection = True )
        queries_panel.AddButton( 'paste queries', self._PasteQueries )
        queries_panel.AddButton( 'edit', self._EditQuery, enabled_only_on_single_selection = True )
        queries_panel.AddDeleteButton()
        queries_panel.AddSeparator()
        queries_panel.AddButton( 'pause/play', self._PausePlay, enabled_only_on_selection = True )
        
        menu_template_items = []
        
        menu_template_item = ClientGUIMenuButton.MenuTemplateItemCall( 'retry ignored', 'Retry the files that were moved over for one reason or another.', self._STARTRetryIgnored )
        menu_template_item.SetVisibleCallable( self._ListCtrlCanRetryIgnored )
        
        menu_template_items.append( menu_template_item )
        
        menu_template_item = ClientGUIMenuButton.MenuTemplateItemCall( 'retry failed', 'Retry the files that failed.', self._STARTRetryFailed )
        menu_template_item.SetVisibleCallable( self._ListCtrlCanRetryFailed )
        
        menu_template_items.append( menu_template_item )
        
        queries_panel.AddMenuIconButton( CC.global_icons().retry, 'retry commands', menu_template_items, enabled_check_func = self._ListCtrlCanRetryAnything )
        
        queries_panel.AddButton( 'check now', self._CheckNow, enabled_check_func = self._ListCtrlCanCheckNow )
        queries_panel.AddButton( 'reset', self._STARTReset, enabled_check_func = self._ListCtrlCanResetCache )
        
        if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            queries_panel.AddSeparator()
            
            menu_template_items = []
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'show', 'Show quality info.', self._STARTShowQualityInfo ) )
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'copy csv data to clipboard', 'Copy quality info to clipboard.', self._STARTCopyQualityInfo ) )
            
            queries_panel.AddMenuButton( 'quality info', menu_template_items, enabled_check_func = self._ListCtrlHasExistingQueriesSelected )
            
        
        #
        
        self._file_limits_panel = ClientGUICommon.StaticBox( self, 'synchronisation' )
        
        if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            limits_max = 50000
            
        else:
            
            limits_max = 1000
            
        
        self._initial_file_limit = ClientGUICommon.BetterSpinBox( self._file_limits_panel, min=1, max=limits_max )
        self._initial_file_limit.setToolTip( ClientGUIFunctions.WrapToolTip( 'The first sync will add no more than this many URLs.' ) )
        
        self._periodic_file_limit = ClientGUICommon.BetterSpinBox( self._file_limits_panel, min=1, max=limits_max )
        self._periodic_file_limit.setToolTip( ClientGUIFunctions.WrapToolTip( 'Normal syncs will add no more than this many URLs, stopping early if they find several URLs the query has seen before. Note that this generally means top-level posts. If those posts include multiple files, e.g. as on Pixiv, they will still only count for one URL at the stage when this is checked.' ) )
        
        self._this_is_a_random_sample_sub = QW.QCheckBox( self._file_limits_panel )
        self._this_is_a_random_sample_sub.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you check this, you will not get warnings if the normal file limit is hit. Useful if you have a randomly sorted gallery, or you just want a recurring small sample of files.' ) )
        
        self._checker_options = ClientGUIImport.CheckerOptionsButton( self._file_limits_panel, checker_options )
        
        self._file_presentation_panel = ClientGUICommon.StaticBox( self, 'file publication' )
        
        self._show_a_popup_while_working = QW.QCheckBox( self._file_presentation_panel )
        self._show_a_popup_while_working.setToolTip( ClientGUIFunctions.WrapToolTip( 'Careful with this! Leave it on to begin with, just in case it goes wrong!' ) )
        
        self._publish_files_to_popup_button = QW.QCheckBox( self._file_presentation_panel )
        self._publish_files_to_page = QW.QCheckBox( self._file_presentation_panel )
        self._publish_label_override = ClientGUICommon.NoneableTextCtrl( self._file_presentation_panel, '', placeholder_text = 'subscription files', none_phrase = 'no, use subscription name' )
        self._merge_query_publish_events = QW.QCheckBox( self._file_presentation_panel )
        
        tt = 'This is great to merge multiple subs to a combined location!'
        
        self._publish_label_override.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        tt = 'If unchecked, each query will produce its own \'subscription_name: query\' button or page.'
        
        self._merge_query_publish_events.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._control_panel = ClientGUICommon.StaticBox( self, 'control' )
        
        self._paused = QW.QCheckBox( self._control_panel )
        
        #
        
        note_import_options = subscription.GetNoteImportOptions()
        
        show_downloader_options = True
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        self._import_options_button.SetTagImportOptions( tag_import_options )
        self._import_options_button.SetNoteImportOptions( note_import_options )
        
        
        #
        
        self._name.setText( name )
        
        self._query_headers.AddDatas( query_headers )
        
        self._query_headers.Sort()
        
        self._initial_file_limit.setValue( initial_file_limit )
        self._periodic_file_limit.setValue( periodic_file_limit )
        self._this_is_a_random_sample_sub.setChecked( this_is_a_random_sample_sub )
        
        ( show_a_popup_while_working, publish_files_to_popup_button, publish_files_to_page, publish_label_override, merge_query_publish_events ) = subscription.GetPresentationOptions()
        
        self._show_a_popup_while_working.setChecked( show_a_popup_while_working )
        self._publish_files_to_popup_button.setChecked( publish_files_to_popup_button )
        self._publish_files_to_page.setChecked( publish_files_to_page )
        self._publish_label_override.SetValue( publish_label_override )
        self._merge_query_publish_events.setChecked( merge_query_publish_events )
        
        self._paused.setChecked( paused )
        
        #
        
        self._query_panel.Add( self._multi_domain_ngug_warning_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._query_panel.Add( self._gug_key_and_name, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._query_panel.Add( queries_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        rows = []
        
        rows.append( ( 'on first check, get at most this many urls/posts: ', self._initial_file_limit ) )
        rows.append( ( 'on normal checks, get at most this many newer urls/posts: ', self._periodic_file_limit ) )
        rows.append( ( 'do not worry about subscription gaps: ', self._this_is_a_random_sample_sub ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._file_limits_panel, rows )
        
        self._file_limits_panel.Add( ClientGUICommon.BetterStaticText( self._file_limits_panel, label = 'Don\'t change these values unless you know what you are doing!' ), CC.FLAGS_CENTER )
        self._file_limits_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._file_limits_panel.Add( self._checker_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        label = 'If you like, the subscription can send its files to popup buttons or pages directly. The files it sends are shaped by the \'presentation\' options in _file import options_.'
        
        st = ClientGUICommon.BetterStaticText( self._file_presentation_panel, label = label )
        
        st.setWordWrap( True )
        
        self._file_presentation_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'show a popup while working: ', self._show_a_popup_while_working ) )
        rows.append( ( 'publish presented files to a popup button: ', self._publish_files_to_popup_button ) )
        rows.append( ( 'publish presented files to a page: ', self._publish_files_to_page ) )
        rows.append( ( 'publish to a specific label: ', self._publish_label_override ) )
        rows.append( ( 'publish all queries to the same page/popup button: ', self._merge_query_publish_events ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._file_presentation_panel, rows )
        
        self._file_presentation_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'currently paused: ', self._paused ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._control_panel, rows )
        
        self._control_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._control_panel, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._delay_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._query_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._control_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._file_limits_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._file_presentation_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._import_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        self._checker_options.valueChanged.connect( self._CheckerOptionsUpdated )
        
        self._UpdateDelayText()
        
        self._gug_key_and_name.valueChanged.connect( self._UpdateNGUGWidget )
        
        self._UpdateNGUGWidget()
        
    
    def _UpdateNGUGWidget( self ):
        
        gug_key_and_name = self._gug_key_and_name.GetValue()
        
        try:
            
            gug = CG.client_controller.network_engine.domain_manager.GetGUG( gug_key_and_name )
            
            show_warning = gug.IsMultiDomainNGUG()
            
        except Exception as e:
            
            show_warning = False
            
        
        self._multi_domain_ngug_warning_label.setVisible( show_warning )
        
    
    def _AddQuery( self ):
        
        gug_key_and_name = self._gug_key_and_name.GetValue()
        
        initial_search_text = CG.client_controller.network_engine.domain_manager.GetInitialSearchText( gug_key_and_name )
        
        query_header = ClientImportSubscriptionQuery.SubscriptionQueryHeader()
        
        query_header.SetQueryText( initial_search_text )
        
        query_log_container = ClientImportSubscriptionQuery.SubscriptionQueryLogContainer( query_header.GetQueryLogContainerName() )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit subscription query' ) as dlg:
            
            panel = EditSubscriptionQueryPanel( dlg, query_header, query_log_container )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                ( query_header, query_log_container ) = panel.GetValue()
                
                query_text_lower = query_header.GetQueryText().lower()
                
                lower_query_texts_to_human_names = self._GetCurrentLowerQueryTextsToHumanNames()
                
                if query_text_lower in lower_query_texts_to_human_names:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, f'You already have a query for "{lower_query_texts_to_human_names[ query_text_lower ]}", so nothing new has been added.' )
                    
                    return
                    
                
                self._query_headers.AddData( query_header, select_sort_and_scroll = True )
                
                self._names_to_edited_query_log_containers[ query_log_container.GetName() ] = query_log_container
                
            
        
    
    def _CheckerOptionsUpdated( self, checker_options ):
        
        checker_options = self._checker_options.GetValue()
        
        for query_header in self._query_headers.GetData():
            
            query_log_container_name = query_header.GetQueryLogContainerName()
            
            if query_log_container_name in self._names_to_edited_query_log_containers:
                
                query_log_container = self._names_to_edited_query_log_containers[ query_log_container_name ]
                
                query_header.SyncToQueryLogContainer( checker_options, query_log_container )
                
            else:
                
                query_header.SetQueryLogContainerStatus( ClientImportSubscriptionQuery.LOG_CONTAINER_UNSYNCED, pretty_velocity_override = 'will recalculate when next fully loaded' )
                
            
        
        self._query_headers.UpdateDatas()
        
    
    def _CheckNow( self ):
        
        selected_query_headers = self._query_headers.GetData( only_selected = True )
        
        try:
            
            ( do_alive, do_dead, do_paused_subs, do_paused_queries ) = DoAliveOrDeadCheck( self, [], selected_query_headers )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        for query_header in selected_query_headers:
            
            if query_header.IsDead():
                
                if not do_dead:
                    
                    continue
                    
                
            else:
                
                if not do_alive:
                    
                    continue
                    
                
            
            if not do_paused_queries and query_header.IsPaused():
                
                continue
                
            
            query_header.CheckNow()
            
        
        self._query_headers.UpdateDatas( selected_query_headers )
        
        self._query_headers.Sort()
        
        self._no_work_until = 0
        
        self._UpdateDelayText()
        
    
    def _ConvertQueryHeaderToDisplayTuple( self, query_header: ClientImportSubscriptionQuery.SubscriptionQueryHeader ):
        
        last_check_time = query_header.GetLastCheckTime()
        paused = query_header.IsPaused()
        checker_status = query_header.GetCheckerStatus()
        
        name = query_header.GetFullHumanName()
        pretty_name = name
        
        if paused:
            
            pretty_paused = 'yes'
            
        else:
            
            pretty_paused = ''
            
        
        if checker_status == ClientImporting.CHECKER_STATUS_OK:
            
            pretty_status = 'ok'
            
        else:
            
            pretty_status = 'dead'
            
        
        file_seed_cache_status = query_header.GetFileSeedCacheStatus()
        
        latest_new_file_time = file_seed_cache_status.GetLatestAddedTime()
        
        if latest_new_file_time is None or latest_new_file_time == 0:
            
            pretty_latest_new_file_time = 'n/a'
            
        else:
            
            pretty_latest_new_file_time = HydrusTime.TimestampToPrettyTimeDelta( latest_new_file_time )
            
        
        if last_check_time is None or last_check_time == 0:
            
            pretty_last_check_time = '(initial check has not yet occurred)'
            
        else:
            
            pretty_last_check_time = HydrusTime.TimestampToPrettyTimeDelta( last_check_time )
            
        
        pretty_next_check_time = query_header.GetNextCheckStatusString()
        
        ( file_velocity, pretty_file_velocity ) = query_header.GetFileVelocityInfo()
        
        try:
            
            estimate = query_header.GetBandwidthWaitingEstimate( CG.client_controller.network_engine.bandwidth_manager, self._original_subscription.GetName() )
            
            if estimate == 0:
                
                pretty_delay = ''
                
            else:
                
                pretty_delay = 'bandwidth: ' + HydrusTime.TimeDeltaToPrettyTimeDelta( estimate )
                
            
        except Exception as e:
            
            pretty_delay = 'could not determine bandwidth--there may be a problem with some of the urls in this query'
            
        
        pretty_items = file_seed_cache_status.GetStatusText( simple = True )
        
        return ( pretty_name, pretty_paused, pretty_status, pretty_latest_new_file_time, pretty_last_check_time, pretty_next_check_time, pretty_file_velocity, pretty_delay, pretty_items )
        
    
    def _ConvertQueryHeaderToSortTuple( self, query_header: ClientImportSubscriptionQuery.SubscriptionQueryHeader ):
        
        paused = query_header.IsPaused()
        checker_status = query_header.GetCheckerStatus()
        
        name = query_header.GetFullHumanName()
        
        file_seed_cache_status = query_header.GetFileSeedCacheStatus()
        
        ( file_velocity, pretty_file_velocity ) = query_header.GetFileVelocityInfo()
        
        file_velocity = tuple( file_velocity ) # for sorting, list/tuple -> tuple
        
        try:
            
            estimate = query_header.GetBandwidthWaitingEstimate( CG.client_controller.network_engine.bandwidth_manager, self._original_subscription.GetName() )
            
            if estimate == 0:
                
                delay = 0
                
            else:
                
                delay = estimate
                
            
        except Exception as e:
            
            delay = 0
            
        
        ( num_done, num_total ) = file_seed_cache_status.GetValueRange()
        
        items = ( num_total, num_done )
        
        latest_new_file_time = file_seed_cache_status.GetLatestAddedTime()
        
        if latest_new_file_time == 0:
            
            latest_new_file_time = HydrusTime.GetNow()
            
        
        last_check_time = query_header.GetLastCheckTime()
        
        if last_check_time == 0:
            
            last_check_time = HydrusTime.GetNow()
            
        
        next_check_time = query_header.GetNextCheckTime()
        
        if next_check_time == 0:
            
            next_check_time = HydrusTime.GetNow()
            
        
        sort_latest_new_file_time = ClientGUIListCtrl.SafeNoneInt( latest_new_file_time )
        sort_last_check_time = ClientGUIListCtrl.SafeNoneInt( last_check_time )
        sort_next_check_time = ClientGUIListCtrl.SafeNoneInt( next_check_time )
        
        return ( name, paused, checker_status, sort_latest_new_file_time, sort_last_check_time, sort_next_check_time, file_velocity, delay, items )
        
    
    def _CopyQueries( self ):
        
        query_texts = []
        
        for query_header in self._query_headers.GetData( only_selected = True ):
            
            query_texts.append( query_header.GetQueryText() )
            
        
        clipboard_text = '\n'.join( query_texts )
        
        if len( clipboard_text ) > 0:
            
            CG.client_controller.pub( 'clipboard', 'text', clipboard_text )
            
        
    
    def _DoAsyncGetQueryLogContainers( self, query_headers: collections.abc.Collection[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ], call: HydrusData.Call ):
        
        missing_query_headers = [ query_header for query_header in query_headers if query_header.GetQueryLogContainerName() not in self._names_to_edited_query_log_containers ]
        
        if len( missing_query_headers ) > 0:
            
            self.setEnabled( False )
            
            def work_callable():
                
                result = GetQueryLogContainers( missing_query_headers )
                
                return result
                
            
            def publish_callable( result ):
                
                query_log_containers = result
                
                for query_log_container in query_log_containers:
                    
                    self._names_to_edited_query_log_containers[ query_log_container.GetName() ] = query_log_container
                    
                
                self.setEnabled( True )
                
                call()
                
            
            async_call = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
            
            async_call.start()
            
        else:
            
            call()
            
        
    
    def _EditQuery( self ):
        
        data = self._query_headers.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        old_query_header = data
        
        query_log_container_name = old_query_header.GetQueryLogContainerName()
        
        if query_log_container_name not in self._names_to_edited_query_log_containers:
            
            try:
                
                old_query_log_container = CG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER, query_log_container_name )
                
            except HydrusExceptions.DataMissing:
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Important Error!', f'Some data for this query, "{old_query_header.GetQueryText()}" was missing! This should have been dealt with when the dialog launched, so something is very wrong! Please exit the manage subscriptions dialog immediately, pause your subs, and contact hydrus dev!' )
                
                return
                
            
            self._names_to_edited_query_log_containers[ query_log_container_name ] = old_query_log_container
            
        
        old_query_log_container = self._names_to_edited_query_log_containers[ query_log_container_name ]
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit subscription query' ) as dlg:
            
            panel = EditSubscriptionQueryPanel( dlg, old_query_header, old_query_log_container )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                ( edited_query_header, edited_query_log_container ) = panel.GetValue()
                
                edited_query_header.SyncToQueryLogContainer( self._checker_options.GetValue(), edited_query_log_container )
                
                edited_query_text = edited_query_header.GetQueryText()
                
                edited_query_text_lower = edited_query_text.lower()
                
                lower_query_texts_to_human_names = self._GetCurrentLowerQueryTextsToHumanNames()
                
                if edited_query_text != old_query_header.GetQueryText() and edited_query_text_lower in lower_query_texts_to_human_names:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, f'You already have a query for "{lower_query_texts_to_human_names[ edited_query_text_lower ]}"! The edit you just made will not be saved.' )
                    
                    return
                    
                
                self._query_headers.ReplaceData( old_query_header, edited_query_header, sort_and_scroll = True )
                
                self._names_to_edited_query_log_containers[ query_log_container_name ] = edited_query_log_container
                
            
        
        
    
    def _GetCurrentLowerQueryTextsToHumanNames( self ):
        
        # lower, not casefold; let's not get too clever here
        
        lower_query_texts_to_human_names = dict()
        
        for query_header in self._query_headers.GetData():
            
            query_text_lower = query_header.GetQueryText().lower()
            query_human_name = query_header.GetFullHumanName()
            
            if query_text_lower in lower_query_texts_to_human_names:
                
                lower_query_texts_to_human_names[ query_text_lower ] += ', ' + query_human_name
                
            else:
                
                lower_query_texts_to_human_names[ query_text_lower ] = query_human_name
                
            
        
        return lower_query_texts_to_human_names
        
    
    def _GetSelectedExistingQueries( self ):
        
        query_headers = typing.cast( collections.abc.Collection[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ], self._query_headers.GetData( only_selected = True ) )
        
        existing_query_headers = [ query_header for query_header in query_headers if query_header.GetQueryLogContainerName() in self._original_existing_query_log_container_names ]
        
        return existing_query_headers
        
    
    def _STARTCopyQualityInfo( self ):
        
        query_headers = self._GetSelectedExistingQueries()
        
        if len( query_headers ) == 0:
            
            return
            
        
        self.setEnabled( False )
        
        def work_callable():
            
            result = GetQueryHeadersQualityInfo( query_headers )
            
            return result
            
        
        def publish_callable( result ):
            
            self.setEnabled( True )
            
            self._CopyQualityInfo( result )
            
        
        async_call = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_call.start()
        
    
    def _CopyQualityInfo( self, data ):
        
        data_strings = []
        
        for ( name, num_inbox, num_archived, num_deleted ) in data:
            
            if num_archived + num_deleted > 0:
                
                percent = HydrusNumbers.FloatToPercentage( num_archived / ( num_archived + num_deleted ) )
                
            else:
                
                percent = '0.0%'
                
            
            data_string = '{},{},{},{},{}'.format( name, num_inbox, num_archived, num_deleted, percent )
            
            data_strings.append( data_string )
            
        
        text = '\n'.join( data_strings )
        
        CG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _STARTShowQualityInfo( self ):
        
        query_headers = self._GetSelectedExistingQueries()
        
        if len( query_headers ) == 0:
            
            return
            
        
        self.setEnabled( False )
        
        def work_callable():
            
            result = GetQueryHeadersQualityInfo( query_headers )
            
            return result
            
        
        def publish_callable( result ):
            
            self.setEnabled( True )
            
            self._ShowQualityInfo( result )
            
        
        async_call = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_call.start()
        
    
    def _ShowQualityInfo( self, data ):
        
        data_strings = []
        
        for ( name, num_inbox, num_archived, num_deleted ) in data:
            
            data_string = '{}: inbox {} | archive {} | deleted {}'.format( name, HydrusNumbers.ToHumanInt( num_inbox ), HydrusNumbers.ToHumanInt( num_archived ), HydrusNumbers.ToHumanInt( num_deleted ) )
            
            if num_archived + num_deleted > 0:
                
                data_string += ' | good {}'.format( HydrusNumbers.FloatToPercentage( num_archived / ( num_archived + num_deleted ) ) )
                
            
            data_strings.append( data_string )
            
        
        message = '\n'.join( data_strings )
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def _ListCtrlCanCheckNow( self ):
        
        for query_header in self._query_headers.GetData( only_selected = True ):
            
            if query_header.CanCheckNow():
                
                return True
                
            
        
        return False
        
    
    def _ListCtrlCanResetCache( self ):
        
        for query_header in self._query_headers.GetData( only_selected = True ):
            
            if not query_header.IsInitialSync():
                
                return True
                
            
        
        return False
        
    
    def _ListCtrlCanRetryAnything( self ):
        
        return self._ListCtrlCanRetryIgnored() or self._ListCtrlCanRetryFailed()
        
    
    def _ListCtrlCanRetryFailed( self ):
        
        for query_header in self._query_headers.GetData( only_selected = True ):
            
            if query_header.CanRetryFailed():
                
                return True
                
            
        
        return False
        
    
    def _ListCtrlCanRetryIgnored( self ):
        
        for query_header in self._query_headers.GetData( only_selected = True ):
            
            if query_header.CanRetryIgnored():
                
                return True
                
            
        
        return False
        
    
    def _ListCtrlHasExistingQueriesSelected( self ):
        
        query_headers = self._GetSelectedExistingQueries()
        
        return len( query_headers ) > 0
        
    
    def _PasteQueries( self ):
        
        message = 'This will add new queries by pulling them from your clipboard. It assumes they are currently in your clipboard and newline separated. Queries that are already in the subscription (with any combination of upper/lower case) will not be duplicated, but if they are DEAD, they can be revived. Sound good?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        try:
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        try:
            
            pasted_query_texts = HydrusText.DeserialiseNewlinedTexts( raw_text )
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'Lines of Queries', e )
            
            return
            
        
        if len( pasted_query_texts ) == 0:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'The clipboard did not seem to have anything in it!' )
            
            return
            
        
        lower_query_texts_to_human_names = self._GetCurrentLowerQueryTextsToHumanNames()
        
        already_existing_query_header_texts = set()
        already_existing_human_names = set()
        new_query_texts = set()
        
        for query_text in pasted_query_texts:
            
            query_text_lower = query_text.lower()
            
            if query_text_lower in lower_query_texts_to_human_names:
                
                already_existing_query_header_texts.add( query_text_lower )
                already_existing_human_names.add( lower_query_texts_to_human_names[ query_text_lower ] )
                
            else:
                
                new_query_texts.add( query_text )
                
            
        
        revive_dead = True
        
        DEAD_query_headers = { query_header for query_header in self._query_headers.GetData() if query_header.GetQueryText().lower() in already_existing_query_header_texts and query_header.IsDead() }
        
        already_existing_human_names = sorted( already_existing_human_names, key = HydrusText.HumanTextSortKey )
        new_query_texts = sorted( new_query_texts, key = HydrusText.HumanTextSortKey )
        
        #
        
        paste_message_components = []
        
        if len( already_existing_human_names ) > 0:
            
            paste_message_components.append( f'The queries{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary(already_existing_human_names)}were already in the subscription.' )
            
            if len( DEAD_query_headers ) > 0:
                
                DEAD_human_names = sorted( [ query_header.GetFullHumanName() for query_header in DEAD_query_headers ], key = HydrusText.HumanTextSortKey )
                
                DEAD_revive_message = f'Some of the queries you pasted already exist in the subscription but are DEAD. Do you want to revive them? They are:{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary(DEAD_human_names)}'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, DEAD_revive_message )
                
                if result == QW.QDialog.DialogCode.Accepted:
                    
                    revive_dead = True
                    
                    paste_message_components.append( f'The DEAD queries{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary(DEAD_human_names)}were revived.' )
                    
                else:
                    
                    revive_dead = False
                    
                
            
        
        if len( new_query_texts ) > 0:
            
            paste_message_components.append( f'The queries{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary(new_query_texts)}were added.' )
            
        
        if len( paste_message_components ) > 0:
            
            message = '\n\n'.join( paste_message_components )
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            
        
        new_query_headers = []
        
        for query_text in new_query_texts:
            
            query_header = ClientImportSubscriptionQuery.SubscriptionQueryHeader()
            
            query_header.SetQueryText( query_text )
            
            new_query_headers.append( query_header )
            
            query_log_container_name = query_header.GetQueryLogContainerName()
            
            query_log_container = ClientImportSubscriptionQuery.SubscriptionQueryLogContainer( query_log_container_name )
            
            self._names_to_edited_query_log_containers[ query_log_container_name ] = query_log_container
            
        
        if revive_dead:
            
            for query_header in DEAD_query_headers:
                
                query_header.CheckNow()
                
            
        
        self._query_headers.AddDatas( new_query_headers, select_sort_and_scroll = True )
        
        self._query_headers.UpdateDatas( DEAD_query_headers )
        
    
    def _PausePlay( self ):
        
        selected_query_headers = self._query_headers.GetData( only_selected = True )
        
        for query_header in selected_query_headers:
            
            query_header.PausePlay()
            
        
        self._query_headers.UpdateDatas( selected_query_headers )
        
    
    def _STARTReset( self ):
        
        message = 'Resetting these queries will delete all their cached urls, meaning when the subscription next runs, they will have to download all those links over again. This may be expensive in time and data. Only do this if you know what it means. Do you want to do it?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            selected_query_headers = self._query_headers.GetData( only_selected = True )
            
            call = HydrusData.Call( self._Reset, selected_query_headers )
            
            self._DoAsyncGetQueryLogContainers( selected_query_headers, call )
            
        
    
    def _Reset( self, query_headers ):
        
        for query_header in query_headers:
            
            query_log_container_name = query_header.GetQueryLogContainerName()
            
            if query_log_container_name not in self._names_to_edited_query_log_containers:
                
                continue
                
            
            query_log_container = self._names_to_edited_query_log_containers[ query_log_container_name ]
            
            query_header.Reset( query_log_container )
            
        
        self._query_headers.UpdateDatas( query_headers )
        
    
    def _STARTRetryFailed( self ):
        
        selected_query_headers = self._query_headers.GetData( only_selected = True )
        
        query_headers = [ query_header for query_header in selected_query_headers if query_header.CanRetryFailed() ]
        
        call = HydrusData.Call( self._RetryFailed, query_headers )
        
        self._DoAsyncGetQueryLogContainers( query_headers, call )
        
    
    def _RetryFailed( self, query_headers: collections.abc.Collection[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ] ):
        
        for query_header in query_headers:
            
            query_log_container_name = query_header.GetQueryLogContainerName()
            
            if query_log_container_name not in self._names_to_edited_query_log_containers:
                
                continue
                
            
            query_log_container = self._names_to_edited_query_log_containers[ query_log_container_name ]
            
            query_log_container.GetFileSeedCache().RetryFailed()
            
            query_header.UpdateFileStatus( query_log_container )
            
        
        self._query_headers.UpdateDatas( query_headers )
        
        self._no_work_until = 0
        
        self._UpdateDelayText()
        
    
    def _STARTRetryIgnored( self ):
        
        try:
            
            ignored_regex = ClientGUIFileSeedCache.GetRetryIgnoredParam( self )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        selected_query_headers = self._query_headers.GetData( only_selected = True )
        
        query_headers = [ query_header for query_header in selected_query_headers if query_header.CanRetryIgnored() ]
        
        call = HydrusData.Call( self._RetryIgnored, query_headers, ignored_regex )
        
        self._DoAsyncGetQueryLogContainers( query_headers, call )
        
    
    def _RetryIgnored( self, query_headers: collections.abc.Collection[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ], ignored_regex = str | None ):
        
        for query_header in query_headers:
            
            query_log_container_name = query_header.GetQueryLogContainerName()
            
            if query_log_container_name not in self._names_to_edited_query_log_containers:
                
                continue
                
            
            query_log_container = self._names_to_edited_query_log_containers[ query_log_container_name ]
            
            query_log_container.GetFileSeedCache().RetryIgnored( ignored_regex = ignored_regex )
            
            query_header.UpdateFileStatus( query_log_container )
            
        
        self._query_headers.UpdateDatas( query_headers )
        
        self._no_work_until = 0
        
        self._UpdateDelayText()
        
    
    def _UpdateDelayText( self ):
        
        if HydrusTime.TimeHasPassed( self._no_work_until ):
            
            status = 'no recent errors'
            
        else:
            
            status = 'delayed--retrying ' + HydrusTime.TimestampToPrettyTimeDelta( self._no_work_until, just_now_threshold = 0 ) + ' because: ' + self._no_work_until_reason
            
        
        self._delay_st.setText( status )
        
    
    def GetValue( self ) -> tuple[ ClientImportSubscriptions.Subscription, dict[ str, ClientImportSubscriptionQuery.SubscriptionQueryLogContainer ] ]:
        
        if not self.isEnabled():
            
            raise HydrusExceptions.VetoException( 'It looks like a long-running job is still working. Please wait for it to finish before applying this dialog.' )
            
        
        name = self._name.text()
        
        subscription = ClientImportSubscriptions.Subscription( name )
        
        gug_key_and_name = self._gug_key_and_name.GetValue()
        
        initial_file_limit = self._initial_file_limit.value()
        periodic_file_limit = self._periodic_file_limit.value()
        
        paused = self._paused.isChecked()
        
        checker_options = self._checker_options.GetValue()
        
        file_import_options = self._import_options_button.GetFileImportOptions()
        tag_import_options = self._import_options_button.GetTagImportOptions()
        note_import_options = self._import_options_button.GetNoteImportOptions()
        
        subscription.SetTuple( gug_key_and_name, checker_options, initial_file_limit, periodic_file_limit, paused, file_import_options, tag_import_options, self._no_work_until )
        
        subscription.SetNoteImportOptions( note_import_options )
        
        subscription.SetThisIsARandomSampleSubscription( self._this_is_a_random_sample_sub.isChecked() )
        
        subscription.SetQueryHeaders( self._query_headers.GetData() )
        
        show_a_popup_while_working = self._show_a_popup_while_working.isChecked()
        publish_files_to_popup_button = self._publish_files_to_popup_button.isChecked()
        publish_files_to_page = self._publish_files_to_page.isChecked()
        publish_label_override = self._publish_label_override.GetValue()
        merge_query_publish_events = self._merge_query_publish_events.isChecked()
        
        subscription.SetPresentationOptions( show_a_popup_while_working, publish_files_to_popup_button, publish_files_to_page, publish_label_override, merge_query_publish_events )
        
        return ( subscription, self._names_to_edited_query_log_containers )
        
    

class EditSubscriptionQueryPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, query_header: ClientImportSubscriptionQuery.SubscriptionQueryHeader, query_log_container: ClientImportSubscriptionQuery.SubscriptionQueryLogContainer ):
        
        super().__init__( parent )
        
        self._original_query_header = query_header
        self._original_query_log_container = query_log_container
        
        query_header = query_header.Duplicate()
        query_log_container = query_log_container.Duplicate()
        
        name_panel = ClientGUICommon.StaticBox( self, 'query and name' )
        
        self._display_name = ClientGUICommon.NoneableTextCtrl( name_panel, '', placeholder_text = 'query name', none_phrase = 'use query text' )
        self._query_text = QW.QLineEdit( name_panel )
        
        #
        
        status_panel = ClientGUICommon.StaticBox( self, 'status' )
        
        self._status_st = ClientGUICommon.BetterStaticText( status_panel )
        
        st_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._status_st, 50 )
        
        self._status_st.setMinimumWidth( st_width )
        
        self._check_now = QW.QCheckBox( status_panel )
        self._paused = QW.QCheckBox( status_panel )
        
        #
        
        log_panel = ClientGUICommon.StaticBox( self, 'history' )
        
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( log_panel )
        
        self._gallery_seed_log_control = ClientGUIGallerySeedLog.GallerySeedLogStatusControl( log_panel, True, True, 'search' )
        
        #
        
        tags_panel = ClientGUICommon.StaticBox( self, 'tags' )
        
        tag_import_options = query_header.GetTagImportOptions()
        show_downloader_options = False # just for additional tags, no parsing gubbins needed
        allow_default_selection = False
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetTagImportOptions( tag_import_options )
        
        #
        
        compaction_number_panel = ClientGUICommon.StaticBox( self, 'advanced', can_expand = True, start_expanded = False )
        
        file_seed_cache_compaction_number = query_header.GetFileSeedCacheCompactionNumber()
        
        self._file_seed_cache_compaction_number = ClientGUICommon.BetterSpinBox( compaction_number_panel, initial = file_seed_cache_compaction_number, min = 100, max = 65536 )
        tt = 'The file log attached to this query will regularly cull itself to the x most recent URLs. The default is to keep 250, but if the periodic file limit or the visited gallery URLs are larger, this will automatically scale. Outside of debugging, you should have no reason to edit this value.'
        self._file_seed_cache_compaction_number.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        display_name = query_header.GetDisplayName()
        query_text = query_header.GetQueryText()
        check_now = query_header.IsCheckingNow()
        paused = query_header.IsPaused()
        
        self._display_name.SetValue( display_name )
        
        self._query_text.setText( query_text )
        
        self._check_now.setChecked( check_now )
        
        self._paused.setChecked( paused )
        
        self._file_seed_cache = query_log_container.GetFileSeedCache()
        
        self._file_seed_cache_control.SetFileSeedCache( self._file_seed_cache )
        
        self._gallery_seed_log = query_log_container.GetGallerySeedLog()
        
        self._gallery_seed_log_control.SetGallerySeedLog( self._gallery_seed_log )
        
        #
        
        rows = []
        
        rows.append( ( 'query text: ', self._query_text ) )
        rows.append( ( 'optional display name: ', self._display_name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( name_panel, rows )
        
        name_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'check now: ', self._check_now ) )
        rows.append( ( 'paused: ', self._paused ) )
        
        gridbox = ClientGUICommon.WrapInGrid( status_panel, rows )
        
        status_panel.Add( self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        status_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        log_panel.Add( self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        log_panel.Add( self._gallery_seed_log_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        label = 'This is only for setting \'additional tags\' for this single query! If you want to change the parsed tags or do subscription-wide \'additional tags\', jump up a level to the edit subscriptions dialog.'
        
        st = ClientGUICommon.BetterStaticText( self, label = label )
        
        st.setWordWrap( True )
        
        tags_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        tags_panel.Add( self._import_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'DEBUG: file log compaction number: ', self._file_seed_cache_compaction_number ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        label = 'Do not edit this unless you know what you are doing!'
        
        st = ClientGUICommon.BetterStaticText( compaction_number_panel, label )
        
        st.setWordWrap( True )
        
        compaction_number_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        compaction_number_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, name_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, status_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, log_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, tags_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, compaction_number_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._check_now.clicked.connect( self._UpdateStatus )
        self._paused.clicked.connect( self._UpdateStatus )
        
        self._UpdateStatus()
        
        self._query_text.selectAll()
        
        ClientGUIFunctions.SetFocusLater( self._query_text )
        
    
    def _GetValue( self ) -> tuple[ ClientImportSubscriptionQuery.SubscriptionQueryHeader, ClientImportSubscriptionQuery.SubscriptionQueryLogContainer ]:
        
        query_header = self._original_query_header.Duplicate()
        
        query_header.SetQueryText( self._query_text.text() )
        
        query_header.SetPaused( self._paused.isChecked() )
        
        query_header.SetCheckNow( self._check_now.isChecked() )
        
        query_header.SetDisplayName( self._display_name.GetValue() )
        
        query_header.SetTagImportOptions( self._import_options_button.GetTagImportOptions() )
        
        query_header.SetFileSeedCacheCompactionNumber( self._file_seed_cache_compaction_number.value() )
        
        query_log_container = self._original_query_log_container.Duplicate()
        
        query_log_container.SetFileSeedCache( self._file_seed_cache )
        query_log_container.SetGallerySeedLog( self._gallery_seed_log )
        
        return ( query_header, query_log_container )
        
    
    def _UpdateStatus( self ):
        
        ( query_header, query_log_container ) = self._GetValue()
        
        self._status_st.setText( 'next check: {}'.format( query_header.GetNextCheckStatusString() ) )
        
    
    def GetValue( self ) -> tuple[ ClientImportSubscriptionQuery.SubscriptionQueryHeader, ClientImportSubscriptionQuery.SubscriptionQueryLogContainer ]:
        
        return self._GetValue()
        
    
class EditSubscriptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, subscriptions: collections.abc.Collection[ ClientImportSubscriptions.Subscription ] ):
        
        subscriptions = [ subscription.Duplicate() for subscription in subscriptions ]
        
        super().__init__( parent )
        
        self._original_existing_query_log_container_names = set()
        
        for subscription in subscriptions:
            
            self._original_existing_query_log_container_names.update( subscription.GetAllQueryLogContainerNames() )
            
        
        self._names_to_edited_query_log_containers = {}
        
        self._gug_names_to_dupe_cased_query_texts = {}
        self._subscriptions_to_dupe_cased_query_texts = {}
        
        self._gug_names_to_dupe_caseless_query_texts = {}
        self._subscriptions_to_dupe_caseless_query_texts = {}
        
        #
        
        menu_template_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_GETTING_STARTED_SUBSCRIPTIONS )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the html subscriptions help', 'Open the help page for subscriptions in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        self._subscriptions_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_SUBSCRIPTIONS.ID, self._ConvertSubscriptionToDisplayTuple, self._ConvertSubscriptionToSortTuple )
        
        self._subscriptions = ClientGUIListCtrl.BetterListCtrlTreeView( self._subscriptions_panel, 12, model, use_simple_delete = True, activation_callback = self.Edit )
        
        self._subscriptions_panel.SetListCtrl( self._subscriptions )
        
        self._subscriptions_panel.AddButton( 'add', self.Add )
        self._subscriptions_panel.AddButton( 'edit', self.Edit, enabled_only_on_single_selection = True )
        self._subscriptions_panel.AddDeleteButton()
        
        self._subscriptions_panel.AddSeparator()
        
        self._subscriptions_panel.AddImportExportButtons( ( ClientImportSubscriptionLegacy.SubscriptionLegacy, ClientImportSubscriptions.SubscriptionContainer ), self._AddSubscription, custom_get_callable = self._GetSelectedSubsAsExportableContainers )
        
        self._subscriptions_panel.NewButtonRow()
        
        self._subscriptions_panel.AddButton( 'merge', self.Merge, enabled_check_func = self._CanMerge )
        self._subscriptions_panel.AddButton( 'separate', self.Separate, enabled_check_func = self._CanSeparate )
        self._subscriptions_panel.AddButton( 'deduplicate', self.DedupeAll, enabled_check_func = self._CanDedupeAll )
        self._subscriptions_panel.AddButton( 'lowercase', self.LowerCaseQueries, enabled_check_func = self._CanLowerCaseQueries )
        
        self._subscriptions_panel.AddSeparator()
        
        self._subscriptions_panel.AddButton( 'pause/resume', self.PauseResume, enabled_only_on_selection = True )
        
        menu_template_items = []
        
        menu_template_item = ClientGUIMenuButton.MenuTemplateItemCall( 'retry ignored', 'Retry the files that were moved over for one reason or another.', self._STARTRetryIgnored )
        menu_template_item.SetVisibleCallable( self._CanRetryIgnored )
        
        menu_template_items.append( menu_template_item )
        
        menu_template_item = ClientGUIMenuButton.MenuTemplateItemCall( 'retry failed', 'Retry the files that failed.', self._STARTRetryFailed )
        menu_template_item.SetVisibleCallable( self._CanRetryFailed )
        
        menu_template_items.append( menu_template_item )
        
        self._subscriptions_panel.AddMenuIconButton( CC.global_icons().retry, 'retry commands', menu_template_items, enabled_check_func = self._CanRetryAnything )
        
        self._subscriptions_panel.AddButton( 'scrub delays', self.ScrubDelays, enabled_check_func = self._CanScrubDelays )
        self._subscriptions_panel.AddButton( 'check queries now', self.CheckNow, enabled_check_func = self._CanCheckNow )
        
        self._subscriptions_panel.AddButton( 'reset', self._STARTReset, enabled_check_func = self._CanReset )
        
        self._subscriptions_panel.NewButtonRow()
        
        self._subscriptions_panel.AddButton( 'select subscriptions', self.SelectSubscriptions )
        self._subscriptions_panel.AddButton( 'overwrite checker options', self.SetCheckerOptions, enabled_only_on_selection = True )
        self._subscriptions_panel.AddButton( 'overwrite file import options', self.SetFileImportOptions, enabled_only_on_selection = True )
        self._subscriptions_panel.AddButton( 'overwrite tag import options', self.SetTagImportOptions, enabled_only_on_selection = True )
        self._subscriptions_panel.AddButton( 'overwrite note import options', self.SetNoteImportOptions, enabled_only_on_selection = True )
        
        #
        
        self._subscriptions.AddDatas( subscriptions )
        
        self._subscriptions.Sort()
        
        self._RegenDupeData()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        
        if CG.client_controller.new_options.GetBoolean( 'pause_subs_sync' ):
            
            message = 'SUBSCRIPTIONS ARE CURRENTLY GLOBALLY PAUSED! CHECK THE NETWORK MENU TO UNPAUSE THEM.'
            
            st = ClientGUICommon.BetterStaticText( self, message )
            st.setObjectName( 'HydrusWarning' )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        QP.AddToLayout( vbox, self._subscriptions_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _AddSubscription( self, unknown_subscription ):
        
        if isinstance( unknown_subscription, ( ClientImportSubscriptionLegacy.SubscriptionLegacy, ClientImportSubscriptions.SubscriptionContainer ) ):
            
            if isinstance( unknown_subscription, ClientImportSubscriptionLegacy.SubscriptionLegacy ):
                
                ( subscription, query_log_containers ) = ClientImportSubscriptionLegacy.ConvertLegacySubscriptionToNew( unknown_subscription )
                
            elif isinstance( unknown_subscription, ClientImportSubscriptions.SubscriptionContainer ):
                
                subscription = unknown_subscription.subscription
                query_log_containers = unknown_subscription.query_log_containers
                
            
            old_names_to_query_log_containers = { query_log_container.GetName() : query_log_container for query_log_container in query_log_containers }
            
            there_were_missing_query_log_containers = False
            
            for query_header in subscription.GetQueryHeaders():
                
                old_query_log_container_name = query_header.GetQueryLogContainerName()
                
                new_query_log_container_name = ClientImportSubscriptionQuery.GenerateQueryLogContainerName()
                
                query_header.SetQueryLogContainerName( new_query_log_container_name )
                
                if old_query_log_container_name in old_names_to_query_log_containers:
                    
                    old_names_to_query_log_containers[ old_query_log_container_name ].SetName( new_query_log_container_name )
                    
                else:
                    
                    there_were_missing_query_log_containers = True
                    
                
            
            if there_were_missing_query_log_containers:
                
                message = 'When importing this subscription, "{}", there was missing log data! I will still let you add it, but some of its queries are incomplete. If you are ok with this, ok and then immediately re-open the manage subscriptions dialog to reinitialise the missing data back to zero (and clear any orphaned data that came with this). If you are not ok with this, cancel out now or cancel out of the whole manage subs dialog.'.format( subscription.GetName() )
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'missing query log data!', yes_label = 'import it anyway', no_label = 'back out now' )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return
                    
                
            
            new_names_to_query_log_containers = { query_log_container.GetName() : query_log_container for query_log_container in query_log_containers }
            
            self._names_to_edited_query_log_containers.update( new_names_to_query_log_containers )
            
        elif isinstance( unknown_subscription, ClientImportSubscriptions.Subscription ):
            
            subscription = unknown_subscription
            
        
        subscription.SetNonDupeName( self._GetExistingNames(), do_casefold = True )
        
        self._subscriptions.AddData( subscription, select_sort_and_scroll = True )
        
        self._RegenDupeData()
        
    
    def _CanCheckNow( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        return True in ( subscription.CanCheckNow() for subscription in subscriptions )
        
    
    def _CanDedupeAll( self ):
        
        return len( self._subscriptions_to_dupe_cased_query_texts ) > 0 or len( self._subscriptions_to_dupe_caseless_query_texts ) > 0
        
    
    def _CanLowerCaseQueries( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        return True in ( subscription.CanLowerCaseQueries() for subscription in subscriptions )
        
    
    def _CanMerge( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        # only subs with queries can be merged
        
        mergeable_subscriptions = [ subscription for subscription in subscriptions if len( subscription.GetQueryHeaders() ) > 0 ]
        
        unique_gug_names = { subscription.GetGUGKeyAndName()[1] for subscription in mergeable_subscriptions }
        
        # if there are fewer, there must be dupes, so we must be able to merge
        
        return len( unique_gug_names ) < len( subscriptions )
        
    
    def _CanReset( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        return True in ( subscription.CanReset() for subscription in subscriptions )
        
    
    def _CanRetryAnything( self ):
        
        return self._CanRetryIgnored() or self._CanRetryFailed()
        
    
    def _CanRetryFailed( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        return True in ( subscription.CanRetryFailed() for subscription in subscriptions )
        
    
    def _CanRetryIgnored( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        return True in ( subscription.CanRetryIgnored() for subscription in subscriptions )
        
    
    def _CanScrubDelays( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        return True in ( subscription.CanScrubDelay() for subscription in subscriptions )
        
    
    def _CanSeparate( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        if len( subscriptions ) != 1:
            
            return False
            
        
        subscription = subscriptions[0]
        
        if len( subscription.GetQueryHeaders() ) > 1:
            
            return True
            
        
        return False
        
    
    def _ConvertSubscriptionToDisplayTuple( self, subscription ):
        
        ( name, gug_key_and_name, query_headers, checker_options, initial_file_limit, periodic_file_limit, paused, file_import_options, tag_import_options, no_work_until, no_work_until_reason ) = subscription.ToTuple()
        
        pretty_site = gug_key_and_name[1]
        
        if len( query_headers ) > 0:
            
            latest_new_file_time = max( ( query_header.GetLatestAddedTime() for query_header in query_headers ) )
            
            last_checked = max( ( query_header.GetLastCheckTime() for query_header in query_headers ) )
            
        else:
            
            latest_new_file_time = 0
            
            last_checked = 0
            
        
        if latest_new_file_time is None or latest_new_file_time == 0:
            
            pretty_latest_new_file_time = 'n/a'
            
        else:
            
            pretty_latest_new_file_time = HydrusTime.TimestampToPrettyTimeDelta( latest_new_file_time )
            
        
        if last_checked is None or last_checked == 0:
            
            pretty_last_checked = 'n/a'
            
        else:
            
            pretty_last_checked = HydrusTime.TimestampToPrettyTimeDelta( last_checked )
            
        
        #
        
        num_queries = len( query_headers )
        num_dead = 0
        num_paused = 0
        
        for query_header in query_headers:
            
            if query_header.IsDead():
                
                num_dead += 1
                
            elif query_header.IsPaused():
                
                num_paused += 1
                
            
        
        num_ok = num_queries - ( num_dead + num_paused )
        
        if num_queries == 0:
            
            pretty_status = 'no queries'
            
        else:
            
            status_components = [ HydrusNumbers.ToHumanInt( num_ok ) + ' working' ]
            
            if num_paused > 0:
                
                status_components.append( HydrusNumbers.ToHumanInt( num_paused ) + ' paused' )
                
            
            if num_dead > 0:
                
                status_components.append( HydrusNumbers.ToHumanInt( num_dead ) + ' dead' )
                
            
            pretty_status = ', '.join( status_components )
            
        
        #
        
        if HydrusTime.TimeHasPassed( no_work_until ):
            
            try:
                
                ( min_estimate, max_estimate ) = subscription.GetBandwidthWaitingEstimateMinMax( CG.client_controller.network_engine.bandwidth_manager )
                
                if max_estimate == 0: # don't seem to be any delays of any kind
                    
                    pretty_delay = ''
                    
                elif min_estimate == 0: # some are good to go, but there are delays
                    
                    pretty_delay = 'bandwidth: some ok, some up to ' + HydrusTime.TimeDeltaToPrettyTimeDelta( max_estimate )
                    
                else:
                    
                    if min_estimate == max_estimate: # probably just one query, and it is delayed
                        
                        pretty_delay = 'bandwidth: up to ' + HydrusTime.TimeDeltaToPrettyTimeDelta( max_estimate )
                        
                    else:
                        
                        pretty_delay = 'bandwidth: from ' + HydrusTime.TimeDeltaToPrettyTimeDelta( min_estimate ) + ' to ' + HydrusTime.TimeDeltaToPrettyTimeDelta( max_estimate )
                        
                    
                
            except Exception as e:
                
                pretty_delay = 'could not determine bandwidth, there may be an error with the sub or its urls'
                
            
        else:
            
            pretty_delay = 'delayed--retrying ' + HydrusTime.TimestampToPrettyTimeDelta( no_work_until, just_now_threshold = 0 ) + ' - because: ' + no_work_until_reason
            
        
        file_seed_cache_status = ClientImportSubscriptionQuery.GenerateQueryHeadersStatus( query_headers )
        
        pretty_items = file_seed_cache_status.GetStatusText( simple = True )
        
        if paused:
            
            pretty_paused = 'yes'
            
        else:
            
            pretty_paused = ''
            
        
        return ( name, pretty_site, pretty_status, pretty_latest_new_file_time, pretty_last_checked, pretty_delay, pretty_items, pretty_paused )
        
    
    def _ConvertSubscriptionToSortTuple( self, subscription ):
        
        ( name, gug_key_and_name, query_headers, checker_options, initial_file_limit, periodic_file_limit, paused, file_import_options, tag_import_options, no_work_until, no_work_until_reason ) = subscription.ToTuple()
        
        pretty_site = gug_key_and_name[1]
        
        if len( query_headers ) > 0:
            
            latest_new_file_time = max( ( query_header.GetLatestAddedTime() for query_header in query_headers ) )
            
            last_checked = max( ( query_header.GetLastCheckTime() for query_header in query_headers ) )
            
        else:
            
            latest_new_file_time = -1
            
            last_checked = -1
            
        
        if latest_new_file_time == 0:
            
            latest_new_file_time = HydrusTime.GetNow()
            
        
        if last_checked == 0:
            
            last_checked = HydrusTime.GetNow()
            
        
        #
        
        num_queries = len( query_headers )
        num_dead = 0
        num_paused = 0
        
        for query_header in query_headers:
            
            if query_header.IsDead():
                
                num_dead += 1
                
            elif query_header.IsPaused():
                
                num_paused += 1
                
            
        
        status = ( num_queries, num_paused, num_dead )
        
        #
        
        if HydrusTime.TimeHasPassed( no_work_until ):
            
            try:
                
                ( min_estimate, max_estimate ) = subscription.GetBandwidthWaitingEstimateMinMax( CG.client_controller.network_engine.bandwidth_manager )
                
                if max_estimate == 0: # don't seem to be any delays of any kind
                    
                    delay = 0
                    
                elif min_estimate == 0: # some are good to go, but there are delays
                    
                    delay = max_estimate
                    
                else:
                    
                    if min_estimate == max_estimate: # probably just one query, and it is delayed
                        
                        delay = max_estimate
                        
                    else:
                        
                        delay = max_estimate
                        
                    
                
            except Exception as e:
                
                delay = 0
                
            
        else:
            
            delay = HydrusTime.GetTimeDeltaUntilTime( no_work_until )
            
        
        file_seed_cache_status = ClientImportSubscriptionQuery.GenerateQueryHeadersStatus( query_headers )
        
        ( num_done, num_total ) = file_seed_cache_status.GetValueRange()
        
        items = ( num_total, num_done )
        
        sort_latest_new_file_time = ClientGUIListCtrl.SafeNoneInt( latest_new_file_time )
        sort_last_checked = ClientGUIListCtrl.SafeNoneInt( last_checked )
        
        return ( name, pretty_site, status, sort_latest_new_file_time, sort_last_checked, delay, items, paused )
        
    
    def _DoAsyncGetQueryLogContainers( self, query_headers: collections.abc.Collection[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ], call: HydrusData.Call ):
        
        missing_query_headers = [ query_header for query_header in query_headers if query_header.GetQueryLogContainerName() not in self._names_to_edited_query_log_containers ]
        
        if len( missing_query_headers ) > 0:
            
            self.setEnabled( False )
            
            def work_callable():
                
                result = GetQueryLogContainers( missing_query_headers )
                
                return result
                
            
            def publish_callable( result ):
                
                query_log_containers = result
                
                for query_log_container in query_log_containers:
                    
                    self._names_to_edited_query_log_containers[ query_log_container.GetName() ] = query_log_container
                    
                
                self.setEnabled( True )
                
                call()
                
            
            async_call = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
            
            async_call.start()
            
        else:
            
            call()
            
        
    
    def _GetExistingNames( self ):
        
        subscriptions = self._subscriptions.GetData()
        
        names = { subscription.GetName() for subscription in subscriptions }
        
        return names
        
    
    def _GetSelectedSubsAsExportableContainers( self ):
        
        subs_to_export = self._subscriptions.GetData( only_selected = True )
        
        required_query_log_headers = []
        
        for sub in subs_to_export:
            
            required_query_log_headers.extend( sub.GetQueryHeaders() )
            
        
        missing_query_headers = [ query_header for query_header in required_query_log_headers if query_header.GetQueryLogContainerName() not in self._names_to_edited_query_log_containers ]
        
        if len( missing_query_headers ) > 0:
            
            if len( missing_query_headers ) > 25:
                
                message = 'Exporting or duplicating the current selection means reading query data for {} queries from the database. This may take just a couple of seconds, or, for hundreds of thousands of cached URLs, it could be a couple of minutes (and a whack of memory). Do not panic, it will get there in the end. Do you want to do the export?'.format( HydrusNumbers.ToHumanInt( len( missing_query_headers ) ) )
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return None
                    
                
            
            self.setEnabled( False )
            
            done = threading.Event()
            
            done_call = lambda: done.set()
            
            self._DoAsyncGetQueryLogContainers( missing_query_headers, done_call )
            
            while True:
                
                if not QP.isValid( self ):
                    
                    return None
                    
                
                if done.is_set():
                    
                    break
                    
                else:
                    
                    time.sleep( 0.25 )
                    
                
                QW.QApplication.instance().processEvents()
                
            
            self.setEnabled( True )
            
        
        to_export = HydrusSerialisable.SerialisableList()
        
        for sub in subs_to_export:
            
            query_log_container_names = [ query_header.GetQueryLogContainerName() for query_header in sub.GetQueryHeaders() ]
            
            query_log_containers = [ self._names_to_edited_query_log_containers[ query_log_container_name ] for query_log_container_name in query_log_container_names ]
            
            subscription_container = ClientImportSubscriptions.SubscriptionContainer()
            
            subscription_container.subscription = sub
            subscription_container.query_log_containers = HydrusSerialisable.SerialisableList( query_log_containers )
            
            # duplicate important here to make sure we aren't linked with existing objects on a dupe call
            to_export.append( subscription_container.Duplicate() )
            
        
        if len( to_export ) == 0:
            
            return None
            
        elif len( to_export ) == 1:
            
            return to_export[0]
            
        else:
            
            return to_export
            
        
    
    def _RegenDupeData( self ):
        
        self._gug_names_to_dupe_cased_query_texts = collections.defaultdict( set )
        self._subscriptions_to_dupe_cased_query_texts = collections.defaultdict( set )
        
        gug_name_and_cased_query_text_count = collections.Counter()
        gug_name_and_cased_query_text_to_subscriptions = collections.defaultdict( list )
        
        self._gug_names_to_dupe_caseless_query_texts = collections.defaultdict( set )
        self._subscriptions_to_dupe_caseless_query_texts = collections.defaultdict( set )
        
        gug_name_and_caseless_query_text_count = collections.Counter()
        gug_name_and_caseless_query_text_to_subscriptions = collections.defaultdict( list )
        
        for subscription in self._subscriptions.GetData():
            
            gug_name = subscription.GetGUGKeyAndName()[1]
            
            query_headers = subscription.GetQueryHeaders()
            
            for query_header in query_headers:
                
                query_text = query_header.GetQueryText()
                
                gug_name_and_cased_query_text_count[ ( gug_name, query_text ) ] += 1
                gug_name_and_cased_query_text_to_subscriptions[ ( gug_name, query_text ) ].append( subscription )
                
                query_text_lower = query_text.lower()
                
                gug_name_and_caseless_query_text_count[ ( gug_name, query_text_lower ) ] += 1
                gug_name_and_caseless_query_text_to_subscriptions[ ( gug_name, query_text_lower ) ].append( subscription )
                
            
        
        for ( ( gug_name, query_text ), count ) in gug_name_and_cased_query_text_count.items():
            
            if count <= 1:
                
                continue
                
            
            self._gug_names_to_dupe_cased_query_texts[ gug_name ].add( query_text )
            
            for subscription in gug_name_and_cased_query_text_to_subscriptions[ ( gug_name, query_text ) ]:
                
                self._subscriptions_to_dupe_cased_query_texts[ subscription ].add( query_text )
                
            
        
        for ( ( gug_name, query_text_lower ), count ) in gug_name_and_caseless_query_text_count.items():
            
            if count <= 1:
                
                continue
                
            
            self._gug_names_to_dupe_caseless_query_texts[ gug_name ].add( query_text_lower )
            
            for subscription in gug_name_and_caseless_query_text_to_subscriptions[ ( gug_name, query_text_lower ) ]:
                
                self._subscriptions_to_dupe_caseless_query_texts[ subscription ].add( query_text_lower )
                
            
        
        self._subscriptions_panel.UpdateButtons()
        
    
    def _STARTReset( self ):
        
        message = 'Resetting these subscriptions will delete all their remembered urls, meaning when they next run, they will try to download them all over again. This may be expensive in time and data. Only do it if you are willing to wait. Do you want to do it?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            query_headers = []
            
            subscriptions = self._subscriptions.GetData( only_selected = True )
            
            for subscription in subscriptions:
                
                query_headers.extend( subscription.GetQueryHeaders() )
                
            
            call = HydrusData.Call( self._Reset, query_headers )
            
            self._DoAsyncGetQueryLogContainers( query_headers, call )
            
        
    
    def _Reset( self, query_headers: collections.abc.Iterable[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ] ):
        
        for query_header in query_headers:
            
            query_log_container_name = query_header.GetQueryLogContainerName()
            
            if query_log_container_name not in self._names_to_edited_query_log_containers:
                
                continue
                
            
            query_log_container = self._names_to_edited_query_log_containers[ query_log_container_name ]
            
            query_header.Reset( query_log_container )
            
        
        self._subscriptions.UpdateDatas()
        
    
    def _STARTRetryFailed( self ):
        
        query_headers = []
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        for subscription in subscriptions:
            
            query_headers.extend( subscription.GetQueryHeaders() )
            
        
        query_headers = [ query_header for query_header in query_headers if query_header.CanRetryFailed() ]
        
        call = HydrusData.Call( self._RetryFailed, query_headers )
        
        self._DoAsyncGetQueryLogContainers( query_headers, call )
        
    
    def _RetryFailed( self, query_headers: collections.abc.Iterable[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ] ):
        
        for query_header in query_headers:
            
            query_log_container_name = query_header.GetQueryLogContainerName()
            
            if query_log_container_name not in self._names_to_edited_query_log_containers:
                
                continue
                
            
            query_log_container = self._names_to_edited_query_log_containers[ query_log_container_name ]
            
            query_log_container.GetFileSeedCache().RetryFailed()
            
            query_header.UpdateFileStatus( query_log_container )
            
        
        self._subscriptions.UpdateDatas()
        
    
    def _STARTRetryIgnored( self ):
        
        try:
            
            ignored_regex = ClientGUIFileSeedCache.GetRetryIgnoredParam( self )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        query_headers = []
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        for subscription in subscriptions:
            
            query_headers.extend( subscription.GetQueryHeaders() )
            
        
        query_headers = [ query_header for query_header in query_headers if query_header.CanRetryIgnored() ]
        
        call = HydrusData.Call( self._RetryIgnored, query_headers, ignored_regex )
        
        self._DoAsyncGetQueryLogContainers( query_headers, call )
        
    
    def _RetryIgnored( self, query_headers: collections.abc.Iterable[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ], ignored_regex: str | None ):
        
        for query_header in query_headers:
            
            query_log_container_name = query_header.GetQueryLogContainerName()
            
            if query_log_container_name not in self._names_to_edited_query_log_containers:
                
                continue
                
            
            query_log_container = self._names_to_edited_query_log_containers[ query_log_container_name ]
            
            query_log_container.GetFileSeedCache().RetryIgnored( ignored_regex = ignored_regex )
            
            query_header.UpdateFileStatus( query_log_container )
            
        
        self._subscriptions.UpdateDatas()
        
    
    def Add( self ):
        
        gug_key_and_name = CG.client_controller.network_engine.domain_manager.GetDefaultGUGKeyAndName()
        
        empty_subscription = ClientImportSubscriptions.Subscription( 'new subscription', gug_key_and_name = gug_key_and_name )
        
        frame_key = 'edit_subscription_dialog'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit subscription', frame_key ) as dlg_edit:
            
            panel = EditSubscriptionPanel( dlg_edit, empty_subscription, self._names_to_edited_query_log_containers, self._original_existing_query_log_container_names )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.exec() == QW.QDialog.DialogCode.Accepted:
                
                ( new_subscription, self._names_to_edited_query_log_containers ) = panel.GetValue()
                
                self._AddSubscription( new_subscription )
                
            
        
    
    def CheckNow( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        try:
            
            ( do_alive, do_dead, do_paused_subs, do_paused_queries ) = DoAliveOrDeadCheck( self, subscriptions, [] )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        for subscription in subscriptions:
            
            if not do_paused_subs and subscription.IsPaused():
                
                continue
                
            
            we_did_some = False
            
            query_headers = subscription.GetQueryHeaders()
            
            for query_header in query_headers:
                
                if query_header.IsDead():
                    
                    if not do_dead:
                        
                        continue
                        
                    
                else:
                    
                    if not do_alive:
                        
                        continue
                        
                    
                
                if not do_paused_queries and query_header.IsPaused():
                    
                    continue
                    
                
                query_header.CheckNow()
                
                we_did_some = True
                
            
            if we_did_some:
                
                subscription.SetPaused( False )
                
                subscription.ScrubDelay()
                
            
        
        self._subscriptions.UpdateDatas( subscriptions )
        
    
    def DedupeAll( self ):
        
        # first, select if we are cased or caseless
        
        # can't do a nice 'yes, there are definitely more to do caseless here', as you can have aaA dupes that add to number deduped but don't increase the query text count
        # for now, we won't bother to dive deeper into the data here, but it would be nice
        
        num_cased = sum( ( len( query_texts ) for query_texts in self._gug_names_to_dupe_cased_query_texts.items() ) )
        num_caseless = sum( ( len( query_texts ) for query_texts in self._gug_names_to_dupe_caseless_query_texts.items() ) )
        
        can_do_cased = num_cased > 0
        can_do_caseless = num_caseless > 0
        
        if can_do_cased and can_do_caseless:
            
            choice_tuples = [
                ( 'do a normal upper/lower case deduplication', False, 'Dedupe "samus_aran" with "samus_aran" or "Samus_Aran". This is usually the best option to go with--most sites ignore case.' ),
                ( 'only do exact text deduplication', True, 'Dedupe "samus_aran" with "samus_aran", but not "Samus_Aran". Usually not important, but some specific galleries may care about this.' )
            ]
            
            message = 'Which kind of duplication are we going to do?'
            
            try:
                
                enforce_case = ClientGUIDialogsQuick.SelectFromListButtons( self, 'Caseless or cased?', choice_tuples, message = message )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
        elif can_do_caseless:
            
            message = 'There are no exact text duplicates. Only upper/lower case deduplication is available, merging queries like "samus_aran" and "Samus_Aran". Is this ok?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
            enforce_case = False
            
        else:
            
            # this should never happen, and we should not have the situation where only cased can be done. if cased can, caseless can, riiiiiight?
            
            ClientGUIDialogsMessage.ShowWarning( self, 'There are no apparent duplicates, the dupe data will now be recalculated.' )
            
            self._RegenDupeData()
            
            return
            
        
        # then select the downloader to dedupe for
        
        if enforce_case:
            
            gug_names_to_dupe_query_texts = self._gug_names_to_dupe_cased_query_texts
            subscriptions_to_dupe_query_texts = self._subscriptions_to_dupe_cased_query_texts
            
        else:
            
            gug_names_to_dupe_query_texts = self._gug_names_to_dupe_caseless_query_texts
            subscriptions_to_dupe_query_texts = self._subscriptions_to_dupe_caseless_query_texts
            
        
        if len( gug_names_to_dupe_query_texts ) == 0:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'There are no apparent duplicates, the dupe data will now be recalculated.' )
            
            self._RegenDupeData()
            
            return
            
        elif len( gug_names_to_dupe_query_texts ) == 1:
            
            ( gug_name, ) = gug_names_to_dupe_query_texts.keys()
            
        else:
            
            choice_tuples = []
            
            for ( gug_name, query_texts ) in gug_names_to_dupe_query_texts.items():
                
                label = '{} ({} duplicates)'.format( gug_name, HydrusNumbers.ToHumanInt( len( query_texts ) ) )
                
                tooltip = ', '.join( sorted( query_texts ) )
                
                choice_tuples.append( ( label, gug_name, tooltip ) )
                
            
            message = 'Multiple downloaders have duplicate queries. Which would you like to dedupe now?'
            
            try:
                
                gug_name = ClientGUIDialogsQuick.SelectFromListButtons( self, 'Which downloader to work on?', choice_tuples, message = message )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
        
        subscriptions_we_will_be_deduping = [ subscription for subscription in subscriptions_to_dupe_query_texts if subscription.GetGUGKeyAndName()[1] == gug_name ]
        
        # now select which queries to dedupe
        
        potential_dupe_query_texts = gug_names_to_dupe_query_texts[ gug_name ]
        
        if len( potential_dupe_query_texts ) == 0:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Strangely, there are actually no apparent duplicates for this downloader, the dupe data will now be recalculated. Let hydev know about this, please.' )
            
            self._RegenDupeData()
            
            return
            
        elif len( potential_dupe_query_texts ) == 1:
            
            ( query_text, ) = potential_dupe_query_texts
            
            message = 'The downloader "{}" has a single duplicate query "{}". Is this ok to dedupe?'.format( gug_name, query_text )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
            query_texts_we_want_to_dedupe_now = potential_dupe_query_texts
            
        else:
            
            message = 'There are {} duplicate query texts for the downloader "{}". Would you like to dedupe them all, or select which to do?'.format( HydrusNumbers.ToHumanInt( len( potential_dupe_query_texts ) ), gug_name )
            
            yes_tuples = []
            
            yes_tuples.append( ( 'do them all', 'all' ) )
            yes_tuples.append( ( 'select which to do', 'select' ) )
            
            try:
                
                result = ClientGUIDialogsQuick.GetYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            if result == 'all':
                
                query_texts_we_want_to_dedupe_now = potential_dupe_query_texts
                
            else:
                
                selected = True
                
                choice_tuples = [ ( query_text, query_text, selected ) for query_text in potential_dupe_query_texts ]
                
                try:
                    
                    query_texts_we_want_to_dedupe_now = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'Select which query texts to dedupe', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
                if len( query_texts_we_want_to_dedupe_now ) == 0:
                    
                    return
                    
                
            
        
        # we are now set on what we want to dedupe.
        
        keep_going = True
        query_texts_we_want_to_dedupe_now = set( query_texts_we_want_to_dedupe_now )
        
        try:
            
            while keep_going:
                
                if enforce_case:
                    
                    subscriptions_to_dupe_query_texts = self._subscriptions_to_dupe_cased_query_texts
                    
                else:
                    
                    subscriptions_to_dupe_query_texts = self._subscriptions_to_dupe_caseless_query_texts
                    
                
                # now select the master sub that will not dedupe
                
                subscriptions_to_dupe_query_texts_it_can_do = {}
                
                choice_tuples = []
                
                for subscription in subscriptions_we_will_be_deduping:
                    
                    sub_dupe_query_texts = subscriptions_to_dupe_query_texts[ subscription ]
                    
                    dupe_query_texts_it_can_do = set( sub_dupe_query_texts ).intersection( query_texts_we_want_to_dedupe_now )
                    
                    if len( dupe_query_texts_it_can_do ) == 0:
                        
                        continue # this doesn't have the queries we selected previously, or was cleared out in a previous loop
                        
                    
                    subscriptions_to_dupe_query_texts_it_can_do[ subscription ] = dupe_query_texts_it_can_do
                    
                    if len( dupe_query_texts_it_can_do ) == len( query_texts_we_want_to_dedupe_now ):
                        
                        label = '{} (has all duplicate queries)'.format( subscription.GetName() )
                        
                    else:
                        
                        label = '{} (has {} duplicate queries)'.format( subscription.GetName(), HydrusNumbers.ValueRangeToPrettyString( len( dupe_query_texts_it_can_do ), len( query_texts_we_want_to_dedupe_now ) ) )
                        
                    
                    choice_tuples.append( ( label, subscription, ', '.join( sorted( dupe_query_texts_it_can_do ) ) ) )
                    
                
                if len( choice_tuples ) == 0:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'Strangely, there are actually no subscriptions that can do dedupe work for the selected duplicates, the dupe data will now be recalculated. Let hydev know about this, please.' )
                    
                    return
                    
                elif len( choice_tuples ) == 1:
                    
                    master_subscription = choice_tuples[0][1]
                    
                    message = 'Subscription "{}" will now dedupe the queries within itself. Is this ok?'.format( master_subscription.GetName() )
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.DialogCode.Accepted:
                        
                        return
                        
                    
                else:
                    
                    choice_tuples.sort( key = lambda c_t: c_t[1].GetName() )
                    
                    message = 'Which subscription is going to keep the queries? If the subscription cannot dedupe them all, you will be able to select another, to do the rest, in a moment.'
                    
                    try:
                        
                        master_subscription = ClientGUIDialogsQuick.SelectFromListButtons( self, 'Which sub to retain the queries on?', choice_tuples, message = message )
                        
                    except HydrusExceptions.CancelledException:
                        
                        return
                        
                    
                
                # we are now good to go
                
                query_texts_our_master_can_do = subscriptions_to_dupe_query_texts_it_can_do[ master_subscription ]
                
                for subscription in subscriptions_we_will_be_deduping:
                    
                    if subscription == master_subscription:
                        
                        subscription.DedupeQueryTexts( query_texts_our_master_can_do, enforce_case = enforce_case )
                        
                    else:
                        
                        subscription.RemoveQueryTexts( query_texts_our_master_can_do, enforce_case = enforce_case )
                        
                    
                
                # can more work be done? if so, ask user if they want to keep going
                
                query_texts_we_want_to_dedupe_now.difference_update( query_texts_our_master_can_do )
                
                keep_going = False
                
                if len( query_texts_we_want_to_dedupe_now ) > 0:
                    
                    message = 'Dedupe was done. There are still {} queries that can be deduped between other subscriptions. Want to do them now?'.format( HydrusNumbers.ToHumanInt( len( query_texts_we_want_to_dedupe_now ) ) )
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result == QW.QDialog.DialogCode.Accepted:
                        
                        keep_going = True
                        
                        self._RegenDupeData() # not actually needed, but let's work on current data mate
                        
                    
                
            
        finally:
            
            self._subscriptions.UpdateDatas()
            
            self._subscriptions.Sort()
            
            self._RegenDupeData()
            
        
    
    def Edit( self ):
        
        subscription = self._subscriptions.GetTopSelectedData()
        
        if subscription is None:
            
            return
            
        
        frame_key = 'edit_subscription_dialog'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit subscription', frame_key ) as dlg:
            
            panel = EditSubscriptionPanel( dlg, subscription, self._names_to_edited_query_log_containers, self._original_existing_query_log_container_names )
            
            dlg.SetPanel( panel )
            
            result = dlg.exec()
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                ( edited_subscription, self._names_to_edited_query_log_containers ) = panel.GetValue()
                
                if edited_subscription.GetName() != subscription.GetName():
                    
                    edited_subscription.SetNonDupeName( self._GetExistingNames(), do_casefold = True )
                    
                
                self._subscriptions.ReplaceData( subscription, edited_subscription, sort_and_scroll = True )
                
                self._RegenDupeData()
                
            
        
    
    def GetValue( self ):
        
        if not self.isEnabled():
            
            raise HydrusExceptions.VetoException( 'It looks like a long-running job is still working. Please wait for it to finish before applying this dialog.' )
            
        
        subscriptions = self._subscriptions.GetData()
        
        required_query_log_container_names = set()
        
        for subscription in subscriptions:
            
            required_query_log_container_names.update( subscription.GetAllQueryLogContainerNames() )
            
        
        edited_query_log_containers = list( self._names_to_edited_query_log_containers.values() )
        
        edited_query_log_containers = [ query_log_container for query_log_container in edited_query_log_containers if query_log_container.GetName() in required_query_log_container_names ]
        
        deletee_query_log_container_names = self._original_existing_query_log_container_names.difference( required_query_log_container_names )
        
        return ( subscriptions, edited_query_log_containers, deletee_query_log_container_names )
        
    
    def LowerCaseQueries( self ):
        
        message = 'This will convert the selected subscriptions\' queries to lowercase text. "Samus_Aran" will become "samus_aran". Most sites do not care about case, but it can help things stay neat.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            subscriptions = self._subscriptions.GetData( only_selected = True )
            
            for subscription in subscriptions:
                
                subscription.LowerCaseQueries()
                
            
            self._RegenDupeData()
            
        
    
    def Merge( self ):
        
        edited_datas = []
        
        message = 'Are you sure you want to merge the selected subscriptions? This will combine all selected subscriptions that share the same downloader, wrapping all their different queries into one subscription.'
        message += '\n' * 2
        message += 'This is a big operation, so if it does not do what you expect, hit cancel afterwards!'
        message += '\n' * 2
        message += 'Please note that all other subscription settings settings (like paused status and file limits and tag options) will be merged as well, so double-check your merged subs\' settings afterwards.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            original_subs = self._subscriptions.GetData( only_selected = True )
            
            potential_mergees = original_subs
            
            mergeable_groups = []
            
            while len( potential_mergees ) > 0:
                
                potential_primary = potential_mergees.pop()
                
                ( mergeables_with_our_primary, not_mergeable_with_our_primary ) = potential_primary.GetMergeable( potential_mergees )
                
                if len( mergeables_with_our_primary ) > 0:
                    
                    mergeable_group = []
                    
                    mergeable_group.append( potential_primary )
                    mergeable_group.extend( mergeables_with_our_primary )
                    
                    mergeable_groups.append( mergeable_group )
                    
                
                potential_mergees = not_mergeable_with_our_primary
                
            
            if len( mergeable_groups ) == 0:
                
                ClientGUIDialogsMessage.ShowInformation( self, 'Unfortunately, none of those subscriptions appear to be mergeable!' )
                
                return
                
            
            primary_and_merged_replacement_tuples = []
            merged_and_discardable_subs = []
            
            for mergeable_group in mergeable_groups:
                
                mergeable_group.sort( key = lambda sub: sub.GetName() )
                
                choice_tuples = [ ( sub.GetName(), sub ) for sub in mergeable_group ]
                
                try:
                    
                    original_primary_sub = ClientGUIDialogsQuick.SelectFromList( self, 'select the primary subscription--into which to merge the others', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
                merged_sub = original_primary_sub.Duplicate()
                
                primary_sub_name = merged_sub.GetName()
                
                mergeable_group.remove( original_primary_sub )
                
                ( eaten_subs, unmerged ) = merged_sub.Merge( mergeable_group )
                
                if len( eaten_subs ) == 0:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, f'{primary_sub_name} was unable to merge any queries! The sources probably do not quite line up--if you think they should, try re-setting the source on the subs and then close/re-open this dialog.' )
                    
                    continue
                    
                
                merged_and_discardable_subs.extend( eaten_subs )
                
                message = f'{primary_sub_name} was able to merge {HydrusNumbers.ToHumanInt( len( eaten_subs ) )} other subscriptions. If you wish to change its name, do so here.'
                
                name = primary_sub_name
                
                try:
                    
                    name = ClientGUIDialogsQuick.EnterText( self, message, default = name )
                    
                except HydrusExceptions.CancelledException:
                    
                    # don't care about a cancel here--we'll take that as 'I didn't want to change its name', not 'abort'
                    pass
                    
                
                merged_sub.SetName( name )
                
                primary_and_merged_replacement_tuples.append( ( original_primary_sub, merged_sub ) )
                
            
            # we are ready to do it
            
            self._subscriptions.DeleteDatas( merged_and_discardable_subs )
            
            existing_names = set( self._GetExistingNames() )
            
            for ( primary, merged_sub ) in primary_and_merged_replacement_tuples:
                
                if merged_sub.GetName() != primary.GetName():
                    
                    merged_sub.SetNonDupeName( existing_names, do_casefold = True )
                    
                
                existing_names.add( merged_sub.GetName() )
                
            
            self._subscriptions.ReplaceDatas( primary_and_merged_replacement_tuples, sort_and_scroll = True )
            
            self._RegenDupeData()
            
        
    
    def PauseResume( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        for subscription in subscriptions:
            
            subscription.PauseResume()
            
        
        self._subscriptions.UpdateDatas( subscriptions )
        
    
    def ScrubDelays( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        for subscription in subscriptions:
            
            subscription.ScrubDelay()
            
        
        self._subscriptions.UpdateDatas( subscriptions )
        
    
    def SelectSubscriptions( self ):
        
        message = 'This selects subscriptions based on query text. Please enter some search text, and any subscription that has a query that includes that text will be selected.'
        
        try:
            
            search_text = ClientGUIDialogsQuick.EnterText( self, message )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        self._subscriptions.clearSelection()
        
        selectee_subscriptions = []
        
        for subscription in self._subscriptions.GetData():
            
            if subscription.HasQuerySearchTextFragment( search_text ):
                
                selectee_subscriptions.append( subscription )
                
            
        
        self._subscriptions.SelectDatas( selectee_subscriptions )
        
    
    def Separate( self ):
        
        subscription = self._subscriptions.GetTopSelectedData()
        
        if subscription is None:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Separate only works if one subscription is selected!' )
            
            return
            
        
        num_queries = len( subscription.GetQueryHeaders() )
        
        if num_queries <= 1:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Separate only works if the selected subscription has more than one query!' )
            
            return
            
        
        if num_queries > 2:
            
            message = 'Are you sure you want to separate the selected subscriptions? Separating breaks merged subscriptions apart into smaller pieces.'
            yes_tuples = [ ( 'break it in half', 'half' ), ( 'break it all into single-query subscriptions', 'whole' ), ( 'only extract some of the subscription', 'part' ) ]
            
            try:
                
                action = ClientGUIDialogsQuick.GetYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
        else:
            
            action = 'whole'
            
        
        want_post_merge = False
        
        query_headers_to_extract = []
        
        if action == 'part':
            
            query_headers = subscription.GetQueryHeaders()
            
            choice_tuples = [ ( query_header.GetHumanName(), query_header, False ) for query_header in query_headers ]
            
            try:
                
                query_headers_to_extract = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'select the queries to extract', choice_tuples )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            if len( query_headers_to_extract ) == num_queries: # the madman selected them all
                
                action = 'whole'
                
            elif len( query_headers_to_extract ) > 1:
                
                yes_tuples = [ ( 'one new merged subscription', True ), ( 'many subscriptions with only one query', False ) ]
                
                message = 'Do you want the extracted queries to be a new merged subscription, or many subscriptions with only one query?'
                
                try:
                    
                    want_post_merge = ClientGUIDialogsQuick.GetYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            
        
        name = subscription.GetName()
        
        if action != 'half':
            
            if want_post_merge:
                
                message = 'Please enter the name for the new subscription.'
                
            else:
                
                message = 'Please enter the base name for the new subscriptions. They will be named \'[NAME]: query\'.'
                
            
            try:
                
                name = ClientGUIDialogsQuick.EnterText( self, message, default = subscription.GetName() )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
        
        # ok, let's do it
        
        final_subscriptions = []
        
        self._subscriptions.DeleteDatas( ( subscription, ) )
        
        if action == 'whole':
            
            final_subscriptions.extend( subscription.Separate( name ) )
            
        elif action == 'part':
            
            extracted_subscriptions = list( subscription.Separate( name, query_headers_to_extract ) )
            
            if want_post_merge:
                
                # it is ok to do a blind merge here since they all share the same settings and will get a new name
                
                primary_sub = extracted_subscriptions.pop()
                
                ( merged, unmerged ) = primary_sub.Merge( extracted_subscriptions )
                
                final_subscriptions.extend( unmerged )
                
                primary_sub.SetName( name )
                
                final_subscriptions.append( primary_sub )
                
            else:
                
                final_subscriptions.extend( extracted_subscriptions )
                
            
            final_subscriptions.append( subscription )
            
        elif action == 'half':
            
            query_headers = sorted( subscription.GetQueryHeaders(), key = lambda q: HydrusText.HumanTextSortKey( q.GetQueryText() ) )
            
            query_headers_to_extract = query_headers[ : len( query_headers ) // 2 ]
            
            name = subscription.GetName()
            
            extracted_subscriptions = list( subscription.Separate( name, query_headers_to_extract ) )
            
            primary_sub = extracted_subscriptions.pop()
            
            ( merged, unmerged ) = primary_sub.Merge( extracted_subscriptions )
            
            final_subscriptions.extend( unmerged )
            
            primary_sub.SetName( '{} (A)'.format( name ) )
            subscription.SetName( '{} (B)'.format( name ) )
            
            final_subscriptions.append( primary_sub )
            final_subscriptions.append( subscription )
            
        
        existing_names = set( self._GetExistingNames() )
        
        for final_subscription in final_subscriptions:
            
            final_subscription.SetNonDupeName( existing_names, do_casefold = True )
            
            existing_names.add( final_subscription.GetName() )
            
        
        self._subscriptions.AddDatas( final_subscriptions, select_sort_and_scroll = True )
        
        self._RegenDupeData()
        
    
    def SetCheckerOptions( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        if len( subscriptions ) == 0:
            
            return
            
        
        checker_options = subscriptions[0].GetCheckerOptions()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit checker options' ) as dlg:
            
            panel = ClientGUITime.EditCheckerOptions( dlg, checker_options )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                checker_options = panel.GetValue()
                
                for subscription in subscriptions:
                    
                    subscription.SetCheckerOptions( checker_options, names_to_query_log_containers = self._names_to_edited_query_log_containers )
                    
                
                self._subscriptions.UpdateDatas( subscriptions )
                
            
        
    
    def SetFileImportOptions( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        if len( subscriptions ) == 0:
            
            return
            
        
        file_import_options = subscriptions[0].GetFileImportOptions()
        show_downloader_options = True
        allow_default_selection = True
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit file import options' ) as dlg:
            
            panel = ClientGUIImportOptions.EditFileImportOptionsPanel( dlg, file_import_options, show_downloader_options, allow_default_selection )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                file_import_options = panel.GetValue()
                
                for subscription in subscriptions:
                    
                    subscription.SetFileImportOptions( file_import_options )
                    
                
                self._subscriptions.UpdateDatas( subscriptions )
                
            
        
    
    def SetNoteImportOptions( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        if len( subscriptions ) == 0:
            
            return
            
        
        note_import_options = subscriptions[0].GetNoteImportOptions()
        allow_default_selection = True
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit note import options' ) as dlg:
            
            panel = ClientGUIImportOptions.EditNoteImportOptionsPanel( dlg, note_import_options, allow_default_selection )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                note_import_options = panel.GetValue()
                
                for subscription in subscriptions:
                    
                    subscription.SetNoteImportOptions( note_import_options )
                    
                
                self._subscriptions.UpdateDatas( subscriptions )
                
            
        
    
    def SetTagImportOptions( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        if len( subscriptions ) == 0:
            
            return
            
        
        tag_import_options = subscriptions[0].GetTagImportOptions()
        show_downloader_options = True
        allow_default_selection = True
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit tag import options' ) as dlg:
            
            panel = ClientGUIImportOptions.EditTagImportOptionsPanel( dlg, tag_import_options, show_downloader_options, allow_default_selection )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                tag_import_options = panel.GetValue()
                
                for subscription in subscriptions:
                    
                    subscription.SetTagImportOptions( tag_import_options )
                    
                
                self._subscriptions.UpdateDatas( subscriptions )
                
            
        
    
