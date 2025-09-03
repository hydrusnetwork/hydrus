import collections
import collections.abc
import os
import random
import threading
import time
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTags
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetwork

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientServices
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.networking import ClientGUIHydrusNetwork
from hydrus.client.gui.pages import ClientGUIPageManager
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelThumbnails
from hydrus.client.gui.pages import ClientGUISidebarCore
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags

fake_account_keys = [ HydrusData.GenerateKey() for i in range( 5 ) ]
cached_local_media_results = []
cached_fake_petition_headers_to_petitions = dict()

def GenerateFakeReason() -> str:
    
    return f'Do this NOW!!! {os.urandom( 6 ).hex()}'
    

def GetPetitionActionInfo( petition: HydrusNetwork.Petition ):
    
    add_contents = petition.GetContents( HC.CONTENT_UPDATE_PEND )
    delete_contents = petition.GetContents( HC.CONTENT_UPDATE_PETITION )
    
    have_add = len( add_contents ) > 0
    have_delete = len( delete_contents ) > 0
    
    action_text = 'UNKNOWN'
    hydrus_text = 'default'
    object_name = 'normal'
    
    if have_add or have_delete:
        
        if have_add and have_delete:
            
            action_text = 'REPLACE'
            
        elif have_add:
            
            action_text = 'ADD'
            hydrus_text = 'valid'
            object_name = 'HydrusValid'
            
        else:
            
            action_text = 'DELETE'
            hydrus_text = 'invalid'
            object_name = 'HydrusInvalid'
            
        
    
    return ( action_text, hydrus_text, object_name )
    

def MakeSomeFakePetitions( service_key: bytes ):
    
    for ( content_type, status ) in [ ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION ) ]:
        
        for i in range( 15 ):
            
            petition_header = HydrusNetwork.PetitionHeader( content_type = content_type, status = status, account_key = SelectFakeAccountKey(), reason = GenerateFakeReason() )
            
            HydrusNetwork.PetitionHeader( content_type = content_type, status = status, account_key = SelectFakeAccountKey(), reason = GenerateFakeReason() )
            
            petitioner_account = HydrusNetwork.Account.GenerateUnknownAccount( petition_header.account_key )
            
            if petition_header.content_type == HC.CONTENT_TYPE_MAPPINGS:
                
                if len( cached_local_media_results ) == 0:
                    
                    from hydrus.client import ClientLocation
                    from hydrus.client.search import ClientSearchFileSearchContext
                    from hydrus.client.search import ClientSearchPredicate
                    
                    predicates = [
                        ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '>', 0 ) ),
                        ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LIMIT, 256 ),
                    ]
                    
                    location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
                    
                    search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, predicates = predicates )
                    
                    file_query_ids = CG.client_controller.Read( 'file_query_ids', search_context )
                    
                    media_results = CG.client_controller.Read( 'media_results_from_ids', file_query_ids )
                    
                    cached_local_media_results.extend( media_results )
                    
                
                if len( cached_local_media_results ) == 0:
                    
                    raise NotImplementedError( 'Populating the fake petition media result cached failed mate' )
                    
                
                contents = []
                
                from hydrus.client.media import ClientMediaResult
                
                for i in range( random.randint( 4, 15 ) ):
                    
                    some_media_results = random.sample( cached_local_media_results, 64 )
                    
                    random.shuffle( some_media_results )
                    
                    first_media_result = typing.cast( ClientMediaResult.MediaResult, some_media_results[0] )
                    
                    some_tags = list( first_media_result.GetTagsManager().GetCurrent( service_key = service_key, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE ) )
                    
                    if len( some_tags ) == 0:
                        
                        our_tag = 'weird situation'
                        
                    else:
                        
                        our_tag = random.choice( some_tags )
                        
                    
                    our_hashes = [ media_result.GetHash() for media_result in some_media_results if our_tag in media_result.GetTagsManager().GetCurrent( service_key = service_key, tag_display_type = ClientTags.TAG_DISPLAY_STORAGE ) ]
                    
                    content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( our_tag, our_hashes ) )
                    
                    contents.append( content )
                    
                
                actions_and_contents = [
                    ( HC.CONTENT_UPDATE_PETITION, contents )
                ]
                
            else:
                
                raise NotImplementedError( 'aiiiieeeeeee!' )
                
            
            petition = HydrusNetwork.Petition(
                petitioner_account = petitioner_account,
                petition_header = petition_header,
                actions_and_contents = actions_and_contents
            )
            
            cached_fake_petition_headers_to_petitions[ petition_header ] = petition
            
        
    

def SelectFakeAccountKey() -> bytes:
    
    return random.choice( fake_account_keys )
    

def SelectFakePetition( service_key: bytes, petition_header ) -> HydrusNetwork.Petition:
    
    if petition_header not in cached_fake_petition_headers_to_petitions:
        
        raise HydrusExceptions.NotFoundException()
        
    else:
        
        return cached_fake_petition_headers_to_petitions[ petition_header ]
        
    

class SidebarPetitions( ClientGUISidebarCore.Sidebar ):
    
    TAG_DISPLAY_TYPE = ClientTags.TAG_DISPLAY_STORAGE
    
    def __init__( self, parent, page, page_manager: ClientGUIPageManager.PageManager ):
        
        self._petition_service_key = page_manager.GetVariable( 'petition_service_key' )
        
        super().__init__( parent, page, page_manager )
        
        self._service = CG.client_controller.services_manager.GetService( self._petition_service_key )
        self._can_ban = self._service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_MODERATE )
        
        service_type = self._service.GetServiceType()
        
        self._petition_types_to_count = collections.Counter()
        self._current_petition = None
        
        content_type = page_manager.GetVariable( 'petition_type_content_type' )
        status = page_manager.GetVariable( 'petition_type_status' )
        
        if content_type is None or status is None:
            
            self._last_petition_type_fetched = None
            
        else:
            
            self._last_petition_type_fetched = ( content_type, status )
            
        
        self._last_fetched_subject_account_key = None
        
        self._petition_headers_to_fetched_petitions_cache = {}
        self._petition_headers_we_failed_to_fetch = set()
        self._petition_headers_we_are_fetching = []
        self._outgoing_petition_headers_to_petitions = {}
        self._failed_outgoing_petition_headers_to_petitions = {}
        
        self._petition_fetcher_and_uploader_work_lock = threading.Lock()
        
        #
        
        self._petition_numbers_panel = ClientGUICommon.StaticBox( self, 'counts' )
        
        self._petition_account_key = QW.QLineEdit( self._petition_numbers_panel )
        self._petition_account_key.setPlaceholderText( 'account id filter' )
        
        self._num_petitions_to_fetch = ClientGUICommon.BetterSpinBox( self._petition_numbers_panel, min = 1, max = 10000 )
        
        self._num_petitions_to_fetch.setValue( page_manager.GetVariable( 'num_petitions_to_fetch' ) )
        
        self._refresh_num_petitions_button = ClientGUICommon.BetterButton( self._petition_numbers_panel, 'refresh counts', self._StartFetchNumPetitions )
        
        self._petition_types_to_controls = {}
        
        content_type_hboxes = []
        
        self._my_petition_types = []
        
        if service_type == HC.FILE_REPOSITORY:
            
            self._my_petition_types.append( ( HC.CONTENT_TYPE_FILES, HC.CONTENT_STATUS_PETITIONED ) )
            
        elif service_type == HC.TAG_REPOSITORY:
            
            self._my_petition_types.append( ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_STATUS_PETITIONED ) )
            self._my_petition_types.append( ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PENDING ) )
            self._my_petition_types.append( ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PETITIONED ) )
            self._my_petition_types.append( ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PENDING ) )
            self._my_petition_types.append( ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PETITIONED ) )
            
        
        for petition_type in self._my_petition_types:
            
            ( content_type, status ) = petition_type
            
            func = HydrusData.Call( self._FetchPetitionsSummary, petition_type )
            
            st = ClientGUICommon.BetterStaticText( self._petition_numbers_panel )
            button = ClientGUICommon.BetterButton( self._petition_numbers_panel, 'fetch ' + HC.content_status_string_lookup[ status ] + ' ' + HC.content_type_string_lookup[ content_type ] + ' petitions', func )
            
            button.setEnabled( False )
            
            self._petition_types_to_controls[ ( content_type, status ) ] = ( st, button )
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, st, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
            QP.AddToLayout( hbox, button, CC.FLAGS_CENTER_PERPENDICULAR )
            
            content_type_hboxes.append( hbox )
            
        
        #
        
        self._petitions_panel = ClientGUICommon.StaticBox( self, 'petitions' )
        
        self._petitions_summary_list_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._petitions_panel )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_PETITIONS_SUMMARY.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._petitions_summary_list = ClientGUIListCtrl.BetterListCtrlTreeView( self._petitions_summary_list_panel, 12, model, activation_callback = self._ActivateToHighlightPetition )
        
        self._petitions_summary_list_panel.SetListCtrl( self._petitions_summary_list )
        
        self._petitions_summary_list_panel.AddButton( 'mass-approve', self._ApproveSelected, enabled_check_func = self._OnlySelectingLoadedPetitions, tooltip = 'Approve the selected petitions' )
        self._petitions_summary_list_panel.AddButton( 'mass-deny', self._DenySelected, enabled_check_func = self._OnlySelectingLoadedPetitions, tooltip = 'Deny the selected petitions' )
        
        #
        
        self._petition_panel = ClientGUICommon.StaticBox( self, 'highlighted petition' )
        
        self._num_files_to_show = ClientGUICommon.NoneableSpinCtrl( self._petition_panel, 256, message = 'number of files to show', min = 1 )
        
        self._num_files_to_show.SetValue( page_manager.GetVariable( 'num_files_to_show' ) )
        
        self._action_text = ClientGUICommon.BetterStaticText( self._petition_panel, label = '' )
        
        self._reason_text = QW.QTextEdit( self._petition_panel )
        self._reason_text.setReadOnly( True )
        
        ( min_width, min_height ) = ClientGUIFunctions.ConvertTextToPixels( self._reason_text, ( 16, 6 ) )
        
        self._reason_text.setFixedHeight( min_height )
        
        check_all = ClientGUICommon.BetterButton( self._petition_panel, 'check all', self._CheckAll )
        flip_selected = ClientGUICommon.BetterButton( self._petition_panel, 'flip selected', self._FlipSelected )
        check_none = ClientGUICommon.BetterButton( self._petition_panel, 'check none', self._CheckNone )
        
        self._sort_by_left = ClientGUICommon.BetterButton( self._petition_panel, 'sort by left', self._SortBy, 'left' )
        self._sort_by_right = ClientGUICommon.BetterButton( self._petition_panel, 'sort by right', self._SortBy, 'right' )
        
        self._sort_by_left.setEnabled( False )
        self._sort_by_right.setEnabled( False )
        
        self._contents_add = ClientGUICommon.BetterCheckBoxList( self._petition_panel )
        self._contents_add.itemDoubleClicked.connect( self.ContentsAddDoubleClick )
        self._contents_add.setHorizontalScrollBarPolicy( QC.Qt.ScrollBarPolicy.ScrollBarAlwaysOff )
        
        self._contents_add.SetHeightNumChars( 20 )
        
        self._contents_delete = ClientGUICommon.BetterCheckBoxList( self._petition_panel )
        self._contents_delete.itemDoubleClicked.connect( self.ContentsDeleteDoubleClick )
        self._contents_delete.setHorizontalScrollBarPolicy( QC.Qt.ScrollBarPolicy.ScrollBarAlwaysOff )
        
        self._contents_delete.SetHeightNumChars( 20 )
        
        self._process = QW.QPushButton( 'process', self._petition_panel )
        self._process.clicked.connect( self.ProcessCurrentPetition )
        self._process.setObjectName( 'HydrusAccept' )
        
        self._copy_account_key_button = ClientGUICommon.BetterButton( self._petition_panel, 'copy petitioner account id', self._CopyAccountKey )
        
        self._modify_petitioner = QW.QPushButton( 'modify petitioner', self._petition_panel )
        self._modify_petitioner.clicked.connect( self.EventModifyPetitioner )
        self._modify_petitioner.setEnabled( False )
        if not self._can_ban: self._modify_petitioner.setVisible( False )
        
        #
        
        self._petition_numbers_panel.Add( self._petition_account_key, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_numbers_panel.Add( self._refresh_num_petitions_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_numbers_panel.Add( ClientGUICommon.WrapInText( self._num_petitions_to_fetch, self, 'number of petitions to fetch' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        for hbox in content_type_hboxes:
            
            self._petition_numbers_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        #
        
        self._petitions_panel.Add( self._petitions_summary_list_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        check_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( check_hbox, check_all, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( check_hbox, flip_selected, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( check_hbox, check_none, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        
        sort_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( sort_hbox, self._sort_by_left, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( sort_hbox, self._sort_by_right, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        
        self._petition_panel.Add( ClientGUICommon.BetterStaticText( self._petition_panel, label = 'Double-click a petition row to see its files, if it has them.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._num_files_to_show, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._action_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._reason_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( sort_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._petition_panel.Add( self._contents_add, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._contents_delete, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( check_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._petition_panel.Add( self._process, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._copy_account_key_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._modify_petitioner, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._petition_numbers_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._petitions_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._petition_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        if service_type == HC.TAG_REPOSITORY:
            
            tag_display_type = ClientTags.TAG_DISPLAY_STORAGE
            
        else:
            
            tag_display_type = ClientTags.TAG_DISPLAY_SELECTION_LIST
            
        
        self._MakeCurrentSelectionTagsBox( vbox, tag_display_type = tag_display_type )
        
        self.widget().setLayout( vbox )
        
        self._contents_add.rightClicked.connect( self.EventAddRowRightClick )
        self._contents_delete.rightClicked.connect( self.EventDeleteRowRightClick )
        
        self._petition_account_key.textChanged.connect( self._UpdateAccountKey )
        
        self._num_files_to_show.valueChanged.connect( self._NotifyNumsUpdated )
        self._num_petitions_to_fetch.valueChanged.connect( self._NotifyNumsUpdated )
        
        self._UpdateAccountKey()
        self._DrawCurrentPetition()
        
    
    def _ActivateToHighlightPetition( self ):
        
        for eligible_petition_header in self._petitions_summary_list.GetData( only_selected = True ):
            
            if self._CanHighlight( eligible_petition_header ):
                
                self._HighlightPetition( eligible_petition_header )
                
                break
                
            
        
    
    def _ApproveSelected( self ):
        
        selected_petition_headers = self._petitions_summary_list.GetData( only_selected = True )
        
        viable_petitions = [ self._petition_headers_to_fetched_petitions_cache[ petition_header ] for petition_header in selected_petition_headers if self._CanHighlight( petition_header ) ]
        
        if len( viable_petitions ) > 0:
            
            text = 'Approve all the content in these {} petitions?'.format( HydrusNumbers.ToHumanInt( len( viable_petitions ) ) )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, text )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                for petition in viable_petitions:
                    
                    petition.ApproveAll()
                    
                
                self._StartUploadingCompletedPetitions( viable_petitions )
                
            
        
    
    def _CanHighlight( self, petition_header: HydrusNetwork.PetitionHeader ):
        
        if petition_header in self._outgoing_petition_headers_to_petitions:
            
            return False
            
        
        if petition_header in self._failed_outgoing_petition_headers_to_petitions:
            
            return False
            
        
        return petition_header in self._petition_headers_to_fetched_petitions_cache
        
    
    def _CheckAll( self ):
        
        for i in range( self._contents_add.count() ):
            
            self._contents_add.Check( i, True )
            
        
        for i in range( self._contents_delete.count() ):
            
            self._contents_delete.Check( i, True )
            
        
    
    def _CheckNone( self ):
        
        for i in range( self._contents_add.count() ):
            
            self._contents_add.Check( i, False )
            
        
        for i in range( self._contents_delete.count() ):
            
            self._contents_delete.Check( i, False )
            
        
    
    def _ClearCurrentPetition( self ):
        
        if self._current_petition is not None:
            
            petition_header = self._current_petition.GetPetitionHeader()
            
            self._current_petition = None
            
            if self._petitions_summary_list.HasData( petition_header ):
                
                self._petitions_summary_list.UpdateDatas( ( petition_header, ) )
                
            
            self._DrawCurrentPetition()
            
            self._ShowHashes( [] )
            
        
    
    def _MoveCurrentPetitionOutOfPendingUpload( self ):
        
        # ok so CanHighlight hands the 'out of pending upload' part, so we don't have to get too clever here
        
        if self._current_petition is not None:
            
            current_header = self._current_petition.GetPetitionHeader()
            
            # this is the hacky solution that uses no indices but is KISS
            
            # round 1, after current
            
            seen_current = False
            
            for eligible_petition_header in self._petitions_summary_list.GetData():
                
                if eligible_petition_header == current_header:
                    
                    seen_current = True
                    
                
                if not seen_current:
                    
                    continue
                    
                
                if self._CanHighlight( eligible_petition_header ):
                    
                    self._HighlightPetition( eligible_petition_header )
                    
                    return
                    
                
            
            # round 2, before current
            
            seen_current = False
            
            for eligible_petition_header in self._petitions_summary_list.GetData():
                
                if eligible_petition_header == current_header:
                    
                    seen_current = True
                    
                
                if seen_current:
                    
                    break
                    
                
                if self._CanHighlight( eligible_petition_header ):
                    
                    self._HighlightPetition( eligible_petition_header )
                    
                    return
                    
                
            
        else:
            
            self._ClearCurrentPetition()
            
            self._HighlightAPetitionIfNeeded()
            
        
    
    def _ClearPetitionsSummary( self ):
        
        self._petitions_summary_list.DeleteDatas( self._petitions_summary_list.GetData() )
        
        self._petition_headers_we_are_fetching = []
        self._petition_headers_we_failed_to_fetch = set()
        self._failed_outgoing_petition_headers_to_petitions = {}
        
        self._ClearCurrentPetition()
        
    
    def _ConvertDataToDisplayTuple( self, petition_header: HydrusNetwork.PetitionHeader ):
        
        pretty_action = ''
        pretty_content = 'fetching' + HC.UNICODE_ELLIPSIS
        
        petition = None
        this_is_current_petition = False
        
        if petition_header in self._outgoing_petition_headers_to_petitions:
            
            petition = self._outgoing_petition_headers_to_petitions[ petition_header ]
            
            pretty_content = 'uploading' + HC.UNICODE_ELLIPSIS
            
        elif petition_header in self._failed_outgoing_petition_headers_to_petitions:
            
            petition = self._failed_outgoing_petition_headers_to_petitions[ petition_header ]
            
            pretty_content = 'failed to upload!'
            
        elif petition_header in self._petition_headers_to_fetched_petitions_cache:
            
            petition = self._petition_headers_to_fetched_petitions_cache[ petition_header ]
            
            pretty_content = petition.GetContentSummary()
            
            this_is_current_petition = False
            
            if self._current_petition is not None and petition_header == self._current_petition.GetPetitionHeader():
                
                this_is_current_petition = True
                
            
        elif petition_header in self._petition_headers_we_failed_to_fetch:
            
            pretty_content = 'failed to fetch!'
            
        
        if petition is not None:
            
            pretty_action = GetPetitionActionInfo( petition )[0]
            
        
        if this_is_current_petition:
            
            pretty_action = f'* {pretty_action}'
            
        
        pretty_account_key = petition_header.account_key.hex()
        pretty_reason = petition_header.reason
        
        display_tuple = ( pretty_action, pretty_account_key, pretty_reason, pretty_content )
        
        return display_tuple
        
    
    def _ConvertDataToSortTuple( self, petition_header: HydrusNetwork.PetitionHeader ):
        
        pretty_action = ''
        
        sort_content = 1
        
        petition = None
        this_is_current_petition = False
        
        if petition_header in self._outgoing_petition_headers_to_petitions:
            
            petition = self._outgoing_petition_headers_to_petitions[ petition_header ]
            
        elif petition_header in self._failed_outgoing_petition_headers_to_petitions:
            
            petition = self._failed_outgoing_petition_headers_to_petitions[ petition_header ]
            
        elif petition_header in self._petition_headers_to_fetched_petitions_cache:
            
            petition = self._petition_headers_to_fetched_petitions_cache[ petition_header ]
            
            this_is_current_petition = False
            
            if self._current_petition is not None and petition_header == self._current_petition.GetPetitionHeader():
                
                this_is_current_petition = True
                
            
        
        if petition is not None:
            
            pretty_action = GetPetitionActionInfo( petition )[0]
            
            sort_content = petition.GetActualContentWeight()
            
        
        if this_is_current_petition:
            
            pretty_action = f'* {pretty_action}'
            
        
        pretty_account_key = petition_header.account_key.hex()
        pretty_reason = petition_header.reason
        
        sort_action = pretty_action
        sort_account_key = pretty_account_key
        sort_reason = pretty_reason
        
        sort_tuple = ( sort_action, sort_account_key, sort_reason, sort_content )
        
        return sort_tuple
        
    
    def _CopyAccountKey( self ):
        
        if self._current_petition is None:
            
            return
            
        
        account_key = self._current_petition.GetPetitionerAccount().GetAccountKey()
        
        CG.client_controller.pub( 'clipboard', 'text', account_key.hex() )
        
    
    def _DenySelected( self ):
        
        selected_petition_headers = self._petitions_summary_list.GetData( only_selected = True )
        
        viable_petitions = [ self._petition_headers_to_fetched_petitions_cache[ petition_header ] for petition_header in selected_petition_headers if self._CanHighlight( petition_header ) ]
        
        if len( viable_petitions ) > 0:
            
            text = 'Deny all the content in these {} petitions?'.format( HydrusNumbers.ToHumanInt( len( viable_petitions ) ) )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, text )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                for petition in viable_petitions:
                    
                    petition.DenyAll()
                    
                
                self._StartUploadingCompletedPetitions( viable_petitions )
                
            
        
    
    def _DrawCurrentPetition( self ):
        
        if self._current_petition is None:
            
            self._action_text.clear()
            self._action_text.setProperty( 'hydrus_text', 'default' )
            
            self._reason_text.clear()
            self._reason_text.setProperty( 'hydrus_text', 'default' )
            
            self._contents_add.clear()
            self._contents_delete.clear()
            
            self._contents_add.hide()
            self._contents_delete.hide()
            
            self._process.setEnabled( False )
            self._copy_account_key_button.setEnabled( False )
            
            self._sort_by_left.setEnabled( False )
            self._sort_by_right.setEnabled( False )
            
            if self._can_ban:
                
                self._modify_petitioner.setEnabled( False )
                
            
        else:
            
            add_contents = self._current_petition.GetContents( HC.CONTENT_UPDATE_PEND )
            delete_contents = self._current_petition.GetContents( HC.CONTENT_UPDATE_PETITION )
            
            have_add = len( add_contents ) > 0
            have_delete = len( delete_contents ) > 0
            
            ( action_text, hydrus_text, object_name ) = GetPetitionActionInfo( self._current_petition )
            
            self._action_text.setText( action_text )
            self._action_text.setObjectName( object_name )
            #self._action_text.setProperty( 'hydrus_text', hydrus_text )
            
            reason = self._current_petition.GetReason()
            
            self._reason_text.setPlainText( reason )
            self._reason_text.setObjectName( object_name )
            #self._reason_text.setProperty( 'hydrus_text', hydrus_text )
            
            if self._last_petition_type_fetched[0] in ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ):
                
                self._sort_by_left.setEnabled( True )
                self._sort_by_right.setEnabled( True )
                
            else:
                
                self._sort_by_left.setEnabled( False )
                self._sort_by_right.setEnabled( False )
                
            
            self._contents_add.setVisible( have_add )
            self._contents_delete.setVisible( have_delete )
            
            contents_and_checks = [ ( c, True ) for c in add_contents ]
            
            self._SetContentsAndChecks( HC.CONTENT_UPDATE_PEND, contents_and_checks, 'right' )
            
            contents_and_checks = [ ( c, True ) for c in delete_contents ]
            
            self._SetContentsAndChecks( HC.CONTENT_UPDATE_PETITION, contents_and_checks, 'right' )
            
            self._process.setEnabled( True )
            self._copy_account_key_button.setEnabled( True )
            
            if self._can_ban:
                
                self._modify_petitioner.setEnabled( True )
                
            
        
        self._action_text.style().polish( self._action_text )
        self._reason_text.style().polish( self._reason_text )
        
    
    def _DrawNumPetitions( self ):
        
        for ( petition_type, ( st, button ) ) in self._petition_types_to_controls.items():
            
            count = self._petition_types_to_count[ petition_type ]
            
            ( st, button ) = self._petition_types_to_controls[ petition_type ]
            
            st.setText( '{} petitions'.format( HydrusNumbers.ToHumanInt( count ) ) )
            
            button.setEnabled( count > 0 )
            
        
    
    def _FetchBestPetitionsSummary( self ):
        
        top_petition_type_with_count = None
        
        for petition_type in self._my_petition_types:
            
            count = self._petition_types_to_count[ petition_type ]
            
            if count == 0:
                
                continue
                
            
            if self._last_petition_type_fetched is not None and self._last_petition_type_fetched == petition_type:
                
                self._FetchPetitionsSummary( petition_type )
                
                return
                
            
            if top_petition_type_with_count is None:
                
                top_petition_type_with_count = petition_type
                
            
        
        if top_petition_type_with_count is not None:
            
            self._FetchPetitionsSummary( top_petition_type_with_count )
            
        
    
    def _FetchPetitionsSummary( self, petition_type ):
        
        ( st, button ) = self._petition_types_to_controls[ petition_type ]
        
        ( content_type, status ) = petition_type
        
        num_to_fetch = self._num_petitions_to_fetch.value()
        
        subject_account_key = self._GetSubjectAccountKey()
        
        def qt_set_petitions_summary( petitions_summary: list[ HydrusNetwork.PetitionHeader ] ):
            
            if self._last_petition_type_fetched != petition_type:
                
                last_petition_type = self._last_petition_type_fetched
                
                self._last_petition_type_fetched = petition_type
                
                self._page_manager.SetVariable( 'petition_type_content_type', content_type )
                self._page_manager.SetVariable( 'petition_type_status', status )
                
                self._UpdateFetchButtonText( last_petition_type )
                
            
            self._SetPetitionsSummary( petitions_summary )
            
        
        def qt_done():
            
            button.setEnabled( True )
            
            self._UpdateFetchButtonText( self._last_petition_type_fetched )
            
        
        def do_it( service ):
            
            try:
                
                if HG.fake_petition_mode:
                    
                    if subject_account_key is None:
                        
                        response = {
                            'petitions_summary' : list( cached_fake_petition_headers_to_petitions.keys() )
                        }
                        
                    else:
                        
                        response = {
                            'petitions_summary' : [ petition_header for petition_header in list( cached_fake_petition_headers_to_petitions.keys() ) if petition_header.account_key == subject_account_key ]
                        }
                        
                    
                else:
                    
                    if subject_account_key is None:
                        
                        response = service.Request( HC.GET, 'petitions_summary', { 'content_type' : content_type, 'status' : status, 'num' : num_to_fetch } )
                        
                    else:
                        
                        response = service.Request( HC.GET, 'petitions_summary', { 'content_type' : content_type, 'status' : status, 'num' : num_to_fetch, 'subject_account_key' : subject_account_key } )
                        
                    
                
                CG.client_controller.CallBlockingToQt( self, qt_set_petitions_summary, response[ 'petitions_summary' ] )
                
            except HydrusExceptions.NotFoundException:
                
                job_status = ClientThreading.JobStatus()
                
                job_status.SetStatusText( 'Hey, the server did not have that type of petition after all. Please hit refresh counts.' )
                
                job_status.FinishAndDismiss( 5 )
                
                CG.client_controller.pub( 'message', job_status )
                
            finally:
                
                CG.client_controller.CallBlockingToQt( self, qt_done )
                
            
        
        if petition_type != self._last_petition_type_fetched:
            
            self._ClearPetitionsSummary()
            
        
        button.setEnabled( False )
        button.setText( 'Fetching' + HC.UNICODE_ELLIPSIS )
        
        CG.client_controller.CallToThread( do_it, self._service )
        
    
    def _FlipSelected( self ):
        
        for i in self._contents_add.GetSelectedIndices():
            
            flipped_state = not self._contents_add.IsChecked( i )
            
            self._contents_add.Check( i, flipped_state )
            
        
        for i in self._contents_delete.GetSelectedIndices():
            
            flipped_state = not self._contents_delete.IsChecked( i )
            
            self._contents_delete.Check( i, flipped_state )
            
        
    
    def _GetContentsAndChecks( self, action ):
        
        if action == HC.CONTENT_UPDATE_PEND:
            
            contents = self._contents_add
            
        else:
            
            contents = self._contents_delete
            
        
        contents_and_checks = []
        
        for i in range( contents.count() ):
            
            content = contents.GetData( i )
            check = contents.IsChecked( i )
            
            contents_and_checks.append( ( content, check ) )
            
        
        return contents_and_checks
        
    
    def _GetSubjectAccountKey( self ):
        
        account_key_hex = self._petition_account_key.text()
        
        if len( account_key_hex ) == 0:
            
            return None
            
        else:
            
            try:
                
                account_key_bytes = bytes.fromhex( account_key_hex )
                
                if len( account_key_bytes ) != 32:
                    
                    raise Exception()
                    
                
                return account_key_bytes
                
            except Exception as e:
                
                return None
                
            
        
    
    def _HighlightAPetitionIfNeeded( self ):
        
        if self._current_petition is None:
            
            for eligible_petition_header in self._petitions_summary_list.GetData():
                
                if self._CanHighlight( eligible_petition_header ):
                    
                    self._HighlightPetition( eligible_petition_header )
                    
                    break
                    
                
            
        
    
    def _HighlightPetition( self, petition_header ):
        
        if not self._CanHighlight( petition_header ):
            
            return
            
        
        if self._current_petition is not None and petition_header == self._current_petition.GetPetitionHeader():
            
            self._ClearCurrentPetition()
            
        elif petition_header in self._petition_headers_to_fetched_petitions_cache:
            
            petition = self._petition_headers_to_fetched_petitions_cache[ petition_header ]
            
            self._SetCurrentPetition( petition )
            
        
    
    def _OnlySelectingLoadedPetitions( self ):
        
        petition_headers = self._petitions_summary_list.GetData( only_selected = True )
        
        if len( petition_headers ) == 0:
            
            return False
            
        
        for petition_header in petition_headers:
            
            if petition_header not in self._petition_headers_to_fetched_petitions_cache:
                
                return False
                
            
        
        return True
        
    
    def _NotifyNumsUpdated( self ):
        
        self._page_manager.SetVariable( 'num_petitions_to_fetch', self._num_petitions_to_fetch.value() )
        self._page_manager.SetVariable( 'num_files_to_show', self._num_files_to_show.GetValue() )
        
    
    def _SetContentsAndChecks( self, action, contents_and_checks, sort_type ):
        
        def key( c_and_s ):
            
            ( c, s ) = c_and_s
            
            if c.GetContentType() in ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ):
                
                ( left, right ) = c.GetContentData()
                
                if sort_type == 'left':
                    
                    ( part_one, part_two ) = ( HydrusTags.SplitTag( left ), HydrusTags.SplitTag( right ) )
                    
                elif sort_type == 'right':
                    
                    ( part_one, part_two ) = ( HydrusTags.SplitTag( right ), HydrusTags.SplitTag( left ) )
                    
                
            elif c.GetContentType() == HC.CONTENT_TYPE_MAPPINGS:
                
                ( tag, hashes ) = c.GetContentData()
                
                part_one = HydrusTags.SplitTag( tag )
                part_two = None
                
            else:
                
                part_one = None
                part_two = None
                
            
            return ( -c.GetVirtualWeight(), part_one, part_two )
            
        
        contents_and_checks.sort( key = key )
        
        if action == HC.CONTENT_UPDATE_PEND:
            
            contents = self._contents_add
            
            string_template = 'ADD: {}'
            
        else:
            
            contents = self._contents_delete
            
            string_template = 'DELETE: {}'
            
        
        contents.clear()
        
        for ( i, ( content, check ) ) in enumerate( contents_and_checks ):
            
            content_string = string_template.format( content.ToString() )
            
            contents.Append( content_string, content, starts_checked = check )
            
        
        if contents.count() > 0:
            
            ideal_height_in_rows = max( 1, min( 20, len( contents_and_checks ) ) )
            
            pixels_per_row = contents.sizeHintForRow( 0 )
            
        else:
            
            ideal_height_in_rows = 1
            pixels_per_row = 16
            
        
        ideal_height_in_pixels = ( ideal_height_in_rows * pixels_per_row ) + ( contents.frameWidth() * 2 )
        
        contents.setFixedHeight( ideal_height_in_pixels )
        
    
    def _SetCurrentPetition( self, petition: HydrusNetwork.Petition ):
        
        self._ClearCurrentPetition()
        
        self._current_petition = petition
        
        self._petitions_summary_list.UpdateDatas( ( self._current_petition.GetPetitionHeader(), ) )
        
        self._DrawCurrentPetition()
        
        self._ShowHashes( [] )
        
    
    def _SetPetitionsSummary( self, petitions_summary: list[ HydrusNetwork.PetitionHeader ] ):
        
        # note we can't make this a nice 'append' so easily, since we still need to cull petitions that were processed without us looking
        # we'll keep the current since the user is looking, but otherwise we'll be good for now
        # maybe add a hard refresh button in future? we'll see how common these issues are
        
        if self._current_petition is not None and len( petitions_summary ) > 0:
            
            current_petition_header = self._current_petition.GetPetitionHeader()
            
            if current_petition_header not in petitions_summary:
                
                petitions_summary.append( current_petition_header )
                
            
        
        self._petitions_summary_list.SetData( petitions_summary )
        
        sorted_petition_headers = self._petitions_summary_list.GetData()
        
        self._petition_headers_we_are_fetching = [ petition_header for petition_header in sorted_petition_headers if petition_header not in self._petition_headers_to_fetched_petitions_cache ]
        
        if len( self._petition_headers_we_are_fetching ) > 0:
            
            CG.client_controller.CallToThread( self.THREADPetitionFetcherAndUploader, self._petition_fetcher_and_uploader_work_lock, self._service )
            
        
        self._HighlightAPetitionIfNeeded()
        
    
    def _ShowHashes( self, hashes ):
        
        with ClientGUICommon.BusyCursor():
            
            media_results = CG.client_controller.Read( 'media_results', hashes )
            
        
        panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self._page, self._page_key, self._page_manager, media_results )
        
        panel.Collect( self._media_collect_widget.GetValue() )
        
        panel.Sort( self._media_sort_widget.GetSort() )
        
        self._page.SwapMediaResultsPanel( panel )
        
    
    def _SortBy( self, sort_type ):
        
        for action in [ HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_PETITION ]:
            
            contents_and_checks = self._GetContentsAndChecks( action )
            
            self._SetContentsAndChecks( action, contents_and_checks, sort_type )
            
        
    
    def _StartFetchNumPetitions( self ):
        
        def do_it( service, subject_account_key = None ):
            
            def qt_draw( petition_count_rows ):
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                num_petitions_currently_listed = len( self._petitions_summary_list.GetData() )
                
                old_petition_types_to_count = self._petition_types_to_count
                
                self._petition_types_to_count = collections.Counter()
                
                # we had a whole thing here that did 'if count dropped by more than 1, refresh summary' and 'if we only have 20% left of our desired count, refresh summary'
                # but the count from the server and the count of what we see differs for mappings, where petitions are bunched, and it was just a pain
                # maybe try again later, with better counting tech and more experience of what is actually wanted here
                
                for ( content_type, status, count ) in petition_count_rows:
                    
                    petition_type = ( content_type, status )
                    
                    self._petition_types_to_count[ petition_type ] = count
                    
                
                self._DrawNumPetitions()
                
                if num_petitions_currently_listed == 0:
                    
                    self._FetchBestPetitionsSummary()
                    
                
            
            def qt_reset():
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                self._refresh_num_petitions_button.setText( 'refresh counts' )
                
            
            try:
                
                if HG.fake_petition_mode:
                    
                    if len( cached_fake_petition_headers_to_petitions ) == 0:
                        
                        MakeSomeFakePetitions( service.GetServiceKey() )
                        
                    
                    if subject_account_key is None:
                        
                        petition_count_rows = [
                            ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_STATUS_PETITIONED, len( cached_fake_petition_headers_to_petitions ) ),
                            ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PETITIONED, 0 ),
                            ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PENDING, 0 ),
                            ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PETITIONED, 0 ),
                            ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PENDING, 0 ),
                        ]
                        
                    else:
                        
                        petition_count_rows = [
                            ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_STATUS_PETITIONED, len( [ petition_header for petition_header in cached_fake_petition_headers_to_petitions.keys() if petition_header.account_key == subject_account_key ] ) ),
                            ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PETITIONED, 0 ),
                            ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PENDING, 0 ),
                            ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PETITIONED, 0 ),
                            ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PENDING, 0 ),
                        ]
                        
                    
                    response = { 'num_petitions' : petition_count_rows }
                    
                else:
                    
                    if subject_account_key is None:
                        
                        response = service.Request( HC.GET, 'num_petitions' )
                        
                    else:
                        
                        try:
                            
                            response = service.Request( HC.GET, 'num_petitions', { 'subject_account_key' : subject_account_key } )
                            
                        except HydrusExceptions.NotFoundException:
                            
                            HydrusData.ShowText( 'That account id was not found!' )
                            
                            CG.client_controller.CallAfter( self, qt_draw, [] )
                            
                            return
                            
                        
                    
                
                num_petition_info = response[ 'num_petitions' ]
                
                CG.client_controller.CallAfter( self, qt_draw, num_petition_info )
                
            finally:
                
                CG.client_controller.CallAfter( self, qt_reset )
                
            
        
        self._refresh_num_petitions_button.setText( 'Fetching' + HC.UNICODE_ELLIPSIS )
        
        subject_account_key = self._GetSubjectAccountKey()
        
        self._last_fetched_subject_account_key = subject_account_key
        
        CG.client_controller.CallToThread( do_it, self._service, subject_account_key )
        
    
    def _StartUploadingCompletedPetitions( self, petitions: collections.abc.Collection[ HydrusNetwork.Petition ] ):
        
        for petition in petitions:
            
            self._outgoing_petition_headers_to_petitions[ petition.GetPetitionHeader() ] = petition
            
        
        self._petitions_summary_list.UpdateDatas( [ petition.GetPetitionHeader() for petition in petitions ] )
        
        self._MoveCurrentPetitionOutOfPendingUpload()
        
        CG.client_controller.CallToThread( self.THREADPetitionFetcherAndUploader, self._petition_fetcher_and_uploader_work_lock, self._service )
        
    
    def _UpdateAccountKey( self ):
        
        account_key_hex = self._petition_account_key.text()
        
        if len( account_key_hex ) == 0:
            
            valid = True
            
        else:
            
            try:
                
                account_key_bytes = bytes.fromhex( account_key_hex )
                
                if len( account_key_bytes ) != 32:
                    
                    raise Exception()
                    
                
                valid = True
                
            except Exception as e:
                
                valid = False
                
            
        
        if valid:
            
            self._petition_account_key.setObjectName( 'HydrusValid' )
            
            if self._GetSubjectAccountKey() != self._last_fetched_subject_account_key:
                
                self._StartFetchNumPetitions()
                
            
        else:
            
            self._petition_account_key.setObjectName( 'HydrusInvalid' )
            
        
        self._petition_account_key.style().polish( self._petition_account_key )
        
    
    def _UpdateFetchButtonText( self, petition_type ):
        
        if petition_type is not None:
            
            ( st, button ) = self._petition_types_to_controls[ petition_type ]
            
            ( content_type, status ) = petition_type
            
            label = 'fetch {} {} petitions'.format( HC.content_status_string_lookup[ status ], HC.content_type_string_lookup[ content_type ] )
            
            if petition_type == self._last_petition_type_fetched:
                
                label = f'{label} (*)'
                
            
            button.setText( label )
            
        
    
    def ContentsAddDoubleClick( self, item ):
        
        selected_indices = self._contents_add.GetSelectedIndices()
        
        if len( selected_indices ) > 0:
            
            selection = selected_indices[0]
            
            content = self._contents_add.GetData( selection )
            
            self.EventContentsDoubleClick( content )
            
        
    
    def ContentsDeleteDoubleClick( self, item ):
        
        selected_indices = self._contents_delete.GetSelectedIndices()
        
        if len( selected_indices ) > 0:
            
            selection = selected_indices[0]
            
            content = self._contents_delete.GetData( selection )
            
            self.EventContentsDoubleClick( content )
            
        
    
    def EventContentsDoubleClick( self, content ):
        
        if content.HasHashes():
            
            hashes = content.GetHashes()
            
            num_files_to_show = self._num_files_to_show.GetValue()
            
            if num_files_to_show is not None and len( hashes ) > num_files_to_show:
                
                hashes = random.sample( hashes, num_files_to_show )
                
            
            self._ShowHashes( hashes )
            
        
    
    def EventModifyPetitioner( self ):
        
        subject_account_key = self._current_petition.GetPetitionerAccount().GetAccountKey()
        
        subject_account_identifiers = [ HydrusNetwork.AccountIdentifier( account_key = subject_account_key ) ]
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'manage accounts' )
        
        panel = ClientGUIHydrusNetwork.ModifyAccountsPanel( frame, self._petition_service_key, subject_account_identifiers )
        
        frame.SetPanel( panel )
        
    
    def EventAddRowRightClick( self ):
        
        selected_indices = self._contents_add.GetSelectedIndices()
        
        selected_contents = []
        
        for i in selected_indices:
            
            content = self._contents_add.GetData( i )
            
            selected_contents.append( content )
            
        
        self.EventContentsRightClick( selected_contents )
        
    
    def EventDeleteRowRightClick( self ):
        
        selected_indices = self._contents_delete.GetSelectedIndices()
        
        selected_contents = []
        
        for i in selected_indices:
            
            content = self._contents_delete.GetData( i )
            
            selected_contents.append( content )
            
        
        self.EventContentsRightClick( selected_contents )
        
    
    def EventContentsRightClick( self, contents ):
        
        copyable_items_a = []
        copyable_items_b = []
        
        for content in contents:
            
            content_type = content.GetContentType()
            
            if content_type == HC.CONTENT_TYPE_MAPPINGS:
                
                ( tag, hashes ) = content.GetContentData()
                
                copyable_items_a.append( tag )
                
            elif content_type in ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ):
                
                ( tag_a, tag_b ) = content.GetContentData()
                
                copyable_items_a.append( tag_a )
                copyable_items_b.append( tag_b )
                
            
        
        copyable_items_a = HydrusLists.DedupeList( copyable_items_a )
        copyable_items_b = HydrusLists.DedupeList( copyable_items_b )
        
        if len( copyable_items_a ) + len( copyable_items_b ) > 0:
            
            menu = ClientGUIMenus.GenerateMenu( self )
            
            for copyable_items in [ copyable_items_a, copyable_items_b ]:
                
                if len( copyable_items ) > 0:
                    
                    if len( copyable_items ) == 1:
                        
                        tag = copyable_items[0]
                        
                        ClientGUIMenus.AppendMenuItem( menu, 'copy {}'.format( tag ), 'Copy this tag.', CG.client_controller.pub, 'clipboard', 'text', tag )
                        
                    else:
                        
                        text = '\n'.join( copyable_items )
                        
                        ClientGUIMenus.AppendMenuItem( menu, 'copy {} tags'.format( HydrusNumbers.ToHumanInt( len( copyable_items ) ) ), 'Copy this tag.', CG.client_controller.pub, 'clipboard', 'text', text )
                        
                    
                
            
            CGC.core().PopupMenu( self, menu )
            
        
    
    def PageShown( self ):
        
        super().PageShown()
        
        CG.client_controller.CallToThread( self.THREADPetitionFetcherAndUploader, self._petition_fetcher_and_uploader_work_lock, self._service )
        
    
    def ProcessCurrentPetition( self ):
        
        if self._current_petition is None:
            
            return
            
        
        jobs = [
            ( self._contents_add, HC.CONTENT_UPDATE_PEND ),
            ( self._contents_delete, HC.CONTENT_UPDATE_PETITION )
        ]
        
        for ( contents_list, action ) in jobs:
            
            for index in range( contents_list.count() ):
                
                content = contents_list.GetData( index )
                
                if contents_list.IsChecked( index ):
                    
                    self._current_petition.Approve( action, content )
                    
                else:
                    
                    self._current_petition.Deny( action, content )
                    
                
            
        
        self._StartUploadingCompletedPetitions( ( self._current_petition, ) )
        
    
    def RefreshQuery( self ):
        
        self._DrawCurrentPetition()
        
    
    def Start( self ):
        
        CG.client_controller.CallAfter( self, self._StartFetchNumPetitions )
        
    
    def THREADPetitionFetcherAndUploader( self, work_lock: threading.Lock, service: ClientServices.ServiceRepository ):
        
        def qt_get_work():
            
            fetch_petition_header = None
            outgoing_petition = None
            
            if len( self._petition_headers_we_are_fetching ) > 0:
                
                if CG.client_controller.PageAliveAndNotClosed( self._page_key ):
                    
                    fetch_petition_header = self._petition_headers_we_are_fetching[0]
                    
                elif CG.client_controller.PageDestroyed( self._page_key ):
                    
                    self._petition_headers_we_are_fetching = []
                    
                
            
            if len( self._outgoing_petition_headers_to_petitions ) > 0:
                
                item = list( self._outgoing_petition_headers_to_petitions.keys() )[0]
                
                outgoing_petition = self._outgoing_petition_headers_to_petitions[ item ]
                
            
            return ( fetch_petition_header, outgoing_petition )
            
        
        def qt_petition_cleared( petition: HydrusNetwork.Petition ):
            
            petition_header = petition.GetPetitionHeader()
            
            if petition_header in self._outgoing_petition_headers_to_petitions:
                
                del self._outgoing_petition_headers_to_petitions[ petition_header ]
                
            
            if petition_header in self._failed_outgoing_petition_headers_to_petitions:
                
                del self._failed_outgoing_petition_headers_to_petitions[ petition_header ]
                
            
            if petition_header in self._petition_headers_to_fetched_petitions_cache:
                
                del self._petition_headers_to_fetched_petitions_cache[ petition_header ]
                
            
            if self._petitions_summary_list.HasData( petition_header ):
                
                self._petitions_summary_list.DeleteDatas( ( petition_header, ) )
                
            
            self._StartFetchNumPetitions()
            
        
        def qt_petition_clear_failed( petition: HydrusNetwork.Petition ):
            
            petition_header = petition.GetPetitionHeader()
            
            if petition_header in self._outgoing_petition_headers_to_petitions:
                
                del self._outgoing_petition_headers_to_petitions[ petition_header ]
                
            
            self._failed_outgoing_petition_headers_to_petitions[ petition_header ] = petition
            
            if self._petitions_summary_list.HasData( petition_header ):
                
                self._petitions_summary_list.UpdateDatas( ( petition_header, ) )
                
            
        
        def qt_petition_fetch_404( petition_header: HydrusNetwork.PetitionHeader ):
            
            if petition_header in self._petition_headers_we_are_fetching:
                
                self._petition_headers_we_are_fetching.remove( petition_header )
                
            
            if self._petitions_summary_list.HasData( petition_header ):
                
                self._petitions_summary_list.DeleteDatas( ( petition_header, ) )
                
            
        
        def qt_petition_fetch_failed( petition_header: HydrusNetwork.PetitionHeader ):
            
            if petition_header in self._petition_headers_we_are_fetching:
                
                self._petition_headers_we_are_fetching.remove( petition_header )
                
            
            self._petition_headers_we_failed_to_fetch.add( petition_header )
            
            if self._petitions_summary_list.HasData( petition_header ):
                
                self._petitions_summary_list.UpdateDatas( ( petition_header, ) )
                
            
        
        def qt_petition_fetched( petition: HydrusNetwork.Petition ):
            
            petition_header = petition.GetPetitionHeader()
            
            if petition_header in self._petition_headers_we_are_fetching:
                
                self._petition_headers_we_are_fetching.remove( petition_header )
                
            
            self._petition_headers_we_failed_to_fetch.discard( petition_header )
            
            if self._petitions_summary_list.HasData( petition_header ):
                
                self._petition_headers_to_fetched_petitions_cache[ petition_header ] = petition
                
                self._petitions_summary_list.UpdateDatas( ( petition_header, ) )
                
            
            if self._current_petition is None:
                
                self._HighlightAPetitionIfNeeded()
                
            
        
        with work_lock:
            
            while True:
                
                ( fetch_petition_header, outgoing_petition ) = CG.client_controller.CallBlockingToQt( self, qt_get_work )
                
                if fetch_petition_header is None and outgoing_petition is None:
                    
                    break
                    
                
                if fetch_petition_header is not None:
                    
                    fetch_petition_header = typing.cast( HydrusNetwork.PetitionHeader, fetch_petition_header )
                    
                    try:
                        
                        if HG.fake_petition_mode:
                            
                            response = { 'petition' : SelectFakePetition( service.GetServiceKey(), fetch_petition_header ) }
                            
                        else:
                            
                            request_dict = {
                                'content_type' : fetch_petition_header.content_type,
                                'status' : fetch_petition_header.status,
                                'subject_account_key' : fetch_petition_header.account_key,
                                'reason' : fetch_petition_header.reason
                            }
                            
                            response = service.Request( HC.GET, 'petition', request_dict )
                            
                        
                        petition = response[ 'petition' ]
                        
                        CG.client_controller.CallBlockingToQt( self, qt_petition_fetched, petition )
                        
                    except HydrusExceptions.NotFoundException:
                        
                        CG.client_controller.CallBlockingToQt( self, qt_petition_fetch_404, fetch_petition_header )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'Failed to fetch a petition!' )
                        HydrusData.ShowException( e )
                        
                        CG.client_controller.CallBlockingToQt( self, qt_petition_fetch_failed, fetch_petition_header )
                        
                    
                
                if outgoing_petition is not None:
                    
                    outgoing_petition = typing.cast( HydrusNetwork.Petition, outgoing_petition )
                    
                    try:
                        
                        job_status = ClientThreading.JobStatus( cancellable = True )
                        
                        job_status.SetStatusTitle( 'committing petition' )
                        
                        time_started = HydrusTime.GetNowFloat()
                        
                        try:
                            
                            updates = outgoing_petition.GetCompletedUploadableClientToServerUpdates()
                            
                            num_to_do = len( updates )
                            
                            for ( num_done, update ) in enumerate( updates ):
                                
                                if HydrusTime.TimeHasPassed( time_started + 3 ):
                                    
                                    CG.client_controller.pub( 'message', job_status )
                                    
                                
                                ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                                
                                if should_quit:
                                    
                                    return
                                    
                                
                                if HG.fake_petition_mode:
                                    
                                    time.sleep( 0.1 )
                                    
                                else:
                                    
                                    service.Request( HC.POST, 'update', { 'client_to_server_update' : update } )
                                    
                                    content_updates = ClientContentUpdates.ConvertClientToServerUpdateToContentUpdates( update )
                                    
                                    if len( content_updates ) > 0:
                                        
                                        CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( service.GetServiceKey(), content_updates ) )
                                        
                                    
                                
                                job_status.SetStatusText( HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do ) )
                                job_status.SetGauge( num_done, num_to_do )
                                
                            
                            if outgoing_petition.GetPetitionHeader() in cached_fake_petition_headers_to_petitions:
                                
                                del cached_fake_petition_headers_to_petitions[ outgoing_petition.GetPetitionHeader() ]
                                
                            
                        finally:
                            
                            job_status.FinishAndDismiss()
                            
                        
                        CG.client_controller.CallBlockingToQt( self, qt_petition_cleared, outgoing_petition )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'Failed to upload a petition!' )
                        HydrusData.ShowException( e )
                        
                        CG.client_controller.CallBlockingToQt( self, qt_petition_clear_failed, outgoing_petition )
                        
                    
                
            
        
    
