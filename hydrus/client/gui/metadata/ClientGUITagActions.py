import collections
import collections.abc
import threading

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusThreading
from hydrus.core import HydrusText

from hydrus.client import ClientGlobals as CG
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick

AUTO_PETITION_REASON = 'TO BE AUTO-PETITIONED'

class TagPairActionContext( object ):
    
    def __init__( self, service_key: bytes ):
        
        # TODO: Consider how TPS/TSS objects can plug into all of this
        # it may be a fully constructed TPS/TSS cannot provide useful info on loops and such, since it is already collapsed, but it would be nice to share all that tech 
        
        self._service_key = service_key
        
        self._service = CG.client_controller.services_manager.GetService( self._service_key )
        
        self._i_am_local_tag_service = self._service.GetServiceType() == HC.LOCAL_TAG
        
        self._original_statuses_to_pairs = collections.defaultdict( set )
        self._current_statuses_to_pairs = collections.defaultdict( set )
        
        self._pairs_to_reasons = {}
        
        self._tags_being_fetched = set()
        self._tags_done_fetched = set()
        
        self._have_fetched_all = False
        self._have_fetched_pending_and_petitioned = False
        
        self._lock = threading.Lock()
        self._notify_new_tags_info = threading.Event()
        
        self._notify_callables = []
        
    
    def _AddStatusesToPairsToCache( self, statuses_to_pairs ):
        
        for ( status, pairs ) in statuses_to_pairs.items():
            
            for ( a, b ) in pairs:
                
                self._tags_done_fetched.add( a )
                self._tags_done_fetched.add( b )
                
            
            self._original_statuses_to_pairs[ status ].update( pairs )
            self._current_statuses_to_pairs[ status ].update( pairs )
            
        
    
    def _FetchStatusToPairs( self, tags = None, where_chain_includes_pending_or_petitioned = False ):
        
        raise NotImplementedError()
        
    
    def _GetFixedPendSuggestions( self ) -> collections.abc.Collection[ str ]:
        
        raise NotImplementedError()
        
    
    def _GetFixedPetitionSuggestions( self ) -> collections.abc.Collection[ str ]:
        
        raise NotImplementedError()
        
    
    def _GetMyContentType( self ) -> int:
        
        raise NotImplementedError()
        
    
    def _GetTagsToFetch( self, tags: collections.abc.Collection[ str ] ) -> set[ str ]:
        
        if self._have_fetched_all:
            
            return set()
            
        
        return set( tags ).difference( self._tags_done_fetched ).difference( self._tags_being_fetched )
        
    
    def AutoPetitionConflicts( self, widget, pairs ):
        
        raise NotImplementedError()
        
    
    def AutoPetitionLoops( self, widget, pairs ):
        
        with self._lock:
            
            current_pairs = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] ).difference( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ] )
            
        
        as_to_bs = HydrusData.BuildKeyToListDict( current_pairs )
        
        pre_existing_loop_strings = []
        a_to_a_loop_strings = []
        
        # we only want to auto-petition stuff (and give the user dialog warnings) if they are _adding_. if they are removing an existing pair from a loop, great!
        addee_pairs = set( pairs ).difference( current_pairs )
        
        for ( potential_new_a, potential_new_b ) in addee_pairs:
            
            if potential_new_a == potential_new_b:
                
                a_to_a_loop_strings.append( f'{potential_new_a} -> {potential_new_b}' )
                
                continue
                
            
            tags_to_check = [ ( potential_new_b, set(), [] ) ]
            
            while len( tags_to_check ) > 0:
                
                next_tags_to_check = []
                
                for ( tag_we_are_checking, seen_tags, seen_tags_in_order ) in tags_to_check:
                    
                    seen_tags.add( tag_we_are_checking )
                    seen_tags_in_order.append( tag_we_are_checking )
                    
                    if tag_we_are_checking in as_to_bs:
                        
                        next_tags_from_this_tag_we_are_checking = as_to_bs[ tag_we_are_checking ]
                        
                        for next_tag_from_this_tag_we_are_checking in next_tags_from_this_tag_we_are_checking:
                            
                            if next_tag_from_this_tag_we_are_checking in seen_tags:
                                
                                # we have detected a pre-existing loop in the database record! some old borked PTR record etc..
                                # we note it down and will tell the user in a bit. don't want to keep searching this 'branch' obviously, so continue
                                pre_existing_loop_strings.append( '->'.join( seen_tags_in_order ) + '->' + next_tag_from_this_tag_we_are_checking )
                                
                                continue
                                
                            elif next_tag_from_this_tag_we_are_checking == potential_new_a:
                                
                                # adding this pair would create a loop!
                                # so, let's repeal the final link that would cause a loop
                                pairs_to_auto_petition = [ ( tag_we_are_checking, next_tag_from_this_tag_we_are_checking ) ]
                                
                                self.EnterCleanedPairs( widget, pairs_to_auto_petition, only_remove = True, forced_reason = AUTO_PETITION_REASON )
                                
                                with self._lock:
                                    
                                    current_pairs = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] ).difference( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ] )
                                    
                                
                                as_to_bs = HydrusData.BuildKeyToListDict( current_pairs )
                                
                                continue
                                
                            else:
                                
                                # ok no loop so far, so we'll continue to chase it down in the next iteration
                                next_tags_to_check.append( ( next_tag_from_this_tag_we_are_checking, set( seen_tags ), list( seen_tags_in_order ) ) )
                                
                            
                        
                    
                
                tags_to_check = next_tags_to_check
                
            
        
        if len( a_to_a_loop_strings ) > 0:
            
            message = 'The pair(s) you mean to add include some self-referencing loops, i.e. "tag->tag"! I will add what you wanted to, but you almost certainly want to undo this. If you are importing from an external source, is there a misplaced line somewhere? In any case, the loops appear to be (take a screenshot/write this down now!):'
            message += '\n' * 2
            message += '\n'.join( a_to_a_loop_strings )
            
            ClientGUIDialogsMessage.ShowCritical( widget, 'Loop problem!', message )
            
        
        if len( pre_existing_loop_strings ) > 0:
            
            message = 'The pair(s) you mean to add seem to connect to one or more sibling/parent loops that already exist in your database! I will add what you wanted to, but please undo these loops manually. The loops appear to be (take a screenshot/write this down now!):'
            message += '\n' * 2
            message += '\n'.join( pre_existing_loop_strings )
            
            ClientGUIDialogsMessage.ShowCritical( widget, 'Loop problem!', message )
            
        
    
    def EnterCleanedPairs( self, widget: QW.QWidget, pairs, only_add = False, only_remove = False, forced_reason = None ):
        """Can only call this guy when all the respective tags have been loaded and, when allowing adds, all conflicts and loops have been sorted."""
        
        # Note this dude now handles lockgubbins granularly. It used to have an atomic lock wrapped around it, along with other stuff, but the dialogs can cause new Qt events to fire, leading to deadlock hell!
        # it isn't that big a deal since the threads and stuff don't _edit_ content, they pretty much just ever expand it
        
        all_tags = set()
        
        for ( a, b ) in pairs:
            
            all_tags.add( a )
            all_tags.add( b )
            
        
        with self._lock:
            
            problem = not all_tags.issubset( self._tags_done_fetched ) and not self._have_fetched_all
            
            missing_tags = all_tags.difference( self._tags_done_fetched )
            
        
        if problem:
            
            message = 'Hey, somehow the "Enter some Pairs" routine was called before the related underlying pairs\' groups were loaded. This should not happen! Please tell hydev about this.'
            message += '\n'
            message += f'I have queued up the needed fetch. Please write down what you were doing to get into this state and see if trying it again works. The missing tags were: {HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( missing_tags, no_trailing_whitespace = True )}'
            
            ClientGUIDialogsMessage.ShowWarning( widget, message )
            
            CG.client_controller.CallToThread( self.InformTagsInterest, all_tags )
            
            return
            
        
        pairs = list( pairs )
        
        pairs.sort( key = lambda c_p1: HydrusText.HumanTextSortKey( c_p1[1] ) )
        
        pairs_to_pend = []
        pairs_to_petition = []
        pairs_to_petition_rescind = []
        pairs_to_pend_rescind = []
        
        with self._lock:
            
            for pair in pairs:
                
                if pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]:
                    
                    if not only_add:
                        
                        pairs_to_pend_rescind.append( pair )
                        
                    
                elif pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]:
                    
                    if not only_remove:
                        
                        pairs_to_petition_rescind.append( pair )
                        
                    
                elif pair in self._original_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ]:
                    
                    if not only_add:
                        
                        pairs_to_petition.append( pair )
                        
                    
                else:
                    
                    if not only_remove:
                        
                        pairs_to_pend.append( pair )
                        
                    
                
            
        
        content_type = self._GetMyContentType()
        
        if len( pairs_to_pend ) > 0:
            
            do_it = True
            
            if forced_reason is not None:
                
                reason = forced_reason
                
            elif self._i_am_local_tag_service:
                
                reason = 'added by user'
                
            else:
                
                if self._service.HasPermission( content_type, HC.PERMISSION_ACTION_MODERATE ):
                    
                    reason = 'Entered by a janitor.'
                    
                else:
                    
                    if len( pairs_to_pend ) > 10:
                        
                        pair_strings = 'The many pairs you entered.'
                        
                    else:
                        
                        pair_strings = '\n'.join( ( old + '->' + new for ( old, new ) in pairs_to_pend ) )
                        
                    
                    fixed_suggestions = self._GetFixedPendSuggestions()
                    
                    suggestions = CG.client_controller.new_options.GetRecentPetitionReasons( content_type, HC.CONTENT_UPDATE_ADD )
                    
                    suggestions.extend( fixed_suggestions )
                    
                    message = 'Enter a reason for:' + '\n' * 2 + pair_strings + '\n' * 2 + 'To be added. A janitor will review your petition.'
                    
                    with ClientGUIDialogs.DialogTextEntry( widget, message, suggestions = suggestions ) as dlg:
                        
                        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                            
                            reason = dlg.GetValue()
                            
                            if reason not in fixed_suggestions:
                                
                                CG.client_controller.new_options.PushRecentPetitionReason( content_type, HC.CONTENT_UPDATE_ADD, reason )
                                
                            
                        else:
                            
                            do_it = False
                            
                        
                    
                
            
            if do_it:
                
                with self._lock:
                    
                    we_are_autopetitioning_somewhere = AUTO_PETITION_REASON in self._pairs_to_reasons.values()
                    
                    if we_are_autopetitioning_somewhere:
                        
                        if self._i_am_local_tag_service:
                            
                            reason = 'REPLACEMENT: by user'
                            
                        else:
                            
                            reason = 'REPLACEMENT: {}'.format( reason )
                            
                        
                    
                    for pair in pairs_to_pend:
                        
                        self._pairs_to_reasons[ pair ] = reason
                        
                    
                    if we_are_autopetitioning_somewhere:
                        
                        for ( p, r ) in list( self._pairs_to_reasons.items() ):
                            
                            if r == AUTO_PETITION_REASON:
                                
                                self._pairs_to_reasons[ p ] = reason
                                
                            
                        
                    
                    self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ].update( pairs_to_pend )
                    
                
            
        
        if len( pairs_to_petition ) > 0:
            
            do_it = True
            
            if forced_reason is not None:
                
                reason = forced_reason
                
            elif self._i_am_local_tag_service:
                
                reason = 'removed by user'
                
            else:
                
                if self._service.HasPermission( content_type, HC.PERMISSION_ACTION_MODERATE ):
                    
                    reason = 'Entered by a janitor.'
                    
                else:
                    
                    if len( pairs_to_petition ) > 10:
                        
                        pair_strings = 'The many pairs you entered.'
                        
                    else:
                        
                        pair_strings = '\n'.join( ( old + '->' + new for ( old, new ) in pairs_to_petition ) )
                        
                    
                    message = 'Enter a reason for:'
                    message += '\n' * 2
                    message += pair_strings
                    message += '\n' * 2
                    message += 'to be removed. You will see the delete as soon as you upload, but a janitor will review your petition to decide if all users should receive it as well.'
                    
                    fixed_suggestions = self._GetFixedPetitionSuggestions()
                    
                    suggestions = CG.client_controller.new_options.GetRecentPetitionReasons( content_type, HC.CONTENT_UPDATE_DELETE )
                    
                    suggestions.extend( fixed_suggestions )
                    
                    with ClientGUIDialogs.DialogTextEntry( widget, message, suggestions = suggestions ) as dlg:
                        
                        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                            
                            reason = dlg.GetValue()
                            
                            if reason not in fixed_suggestions:
                                
                                CG.client_controller.new_options.PushRecentPetitionReason( content_type, HC.CONTENT_UPDATE_DELETE, reason )
                                
                            
                        else:
                            
                            do_it = False
                            
                        
                    
                
            
            if do_it:
                
                with self._lock:
                    
                    we_are_autopetitioning_somewhere = AUTO_PETITION_REASON in self._pairs_to_reasons.values()
                    
                    if we_are_autopetitioning_somewhere:
                        
                        if self._i_am_local_tag_service:
                            
                            reason = 'REPLACEMENT: by user'
                            
                        else:
                            
                            reason = 'REPLACEMENT: {}'.format( reason )
                            
                        
                    
                    for pair in pairs_to_petition:
                        
                        self._pairs_to_reasons[ pair ] = reason
                        
                    
                    if we_are_autopetitioning_somewhere:
                        
                        for ( p, r ) in list( self._pairs_to_reasons.items() ):
                            
                            if r == AUTO_PETITION_REASON:
                                
                                self._pairs_to_reasons[ p ] = reason
                                
                            
                        
                    
                    self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ].update( pairs_to_petition )
                    
                
            
        
        if len( pairs_to_pend_rescind ) > 0:
            
            if len( pairs_to_pend_rescind ) > 10:
                
                pair_strings = 'The many pairs you entered.'
                
            else:
                
                pair_strings = '\n'.join( ( old + '->' + new for ( old, new ) in pairs_to_pend_rescind ) )
                
            
            if len( pairs_to_pend_rescind ) > 1:
                
                message = 'The pairs:' + '\n' * 2 + pair_strings + '\n' * 2 + 'Are pending.'
                
            else:
                
                message = 'The pair ' + pair_strings + ' is pending.'
                
            
            result = ClientGUIDialogsQuick.GetYesNo( widget, message, title = 'Choose what to do.', yes_label = 'rescind the pend', no_label = 'do nothing' )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                with self._lock:
                    
                    self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ].difference_update( pairs_to_pend_rescind )
                    
                
            
        
        if len( pairs_to_petition_rescind ) > 0:
            
            if len( pairs_to_petition_rescind ) > 10:
                
                pair_strings = 'The many pairs you entered.'
                
            else:
                
                pair_strings = ', '.join( ( old + '->' + new for ( old, new ) in pairs_to_petition_rescind ) )
                
            
            if len( pairs_to_petition_rescind ) > 1:
                
                message = 'The pairs:' + '\n' * 2 + pair_strings + '\n' * 2 + 'Are petitioned.'
                
            else:
                
                message = 'The pair ' + pair_strings + ' is petitioned.'
                
            
            result = ClientGUIDialogsQuick.GetYesNo( widget, message, title = 'Choose what to do.', yes_label = 'rescind the petition', no_label = 'do nothing' )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                with self._lock:
                    
                    self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ].difference_update( pairs_to_petition_rescind )
                    
                
            
        
        with self._lock:
            
            for ( win, c ) in self._notify_callables:
                
                CG.client_controller.CallAfterQtSafe( win, 'showing pair updates', c )
                
            
            self._notify_new_tags_info.set()
            
        
    
    def EnterPairs( self, widget: QW.QWidget, pairs, only_add = False ):
        
        def wait_for_preload():
            
            while not self.IsReady():
                
                if HydrusThreading.IsThreadShuttingDown():
                    
                    return
                    
                
                self._notify_new_tags_info.wait( 0.5 )
                
                self._notify_new_tags_info.clear()
                
            
            CG.client_controller.CallAfterQtSafe( widget, 'add tag pairs (after preload)', do_it_qt )
            
        
        def do_it_qt():
            
            # ok we used to wrap this guy in a big lock to make it atomic
            # HOWEVER since EnterCleanedPairs can spawn a couple dialogs, which would then exit the Qt event loop and start processing other stuff, I'm pretty sure we could get an UI deadlock (e.g. some list row updating), hooray
            # thus we need to promote these guys and do more granular locking and simply trust that the various fetchers and stuff around here aren't making any _edit_ changes to this stuff, only ever _additions_
            # further, it shouldn't be possible to enterpairs twice at once, so the main guy who is editing stuff here doesn't care about atomicity--that _is_ enforced serialised, fingers-crossed
            
            self.AutoPetitionConflicts( widget, pairs )
            
            self.AutoPetitionLoops( widget, pairs )
            
            self.EnterCleanedPairs( widget, pairs, only_add = only_add )
            
        
        all_tags = set()
        
        for ( a, b ) in pairs:
            
            all_tags.add( a )
            all_tags.add( b )
            
        
        with self._lock:
            
            to_fetch = self._GetTagsToFetch( all_tags )
            
        
        if len( to_fetch ) > 0:
            
            self.InformTagsInterest( to_fetch )
            
        
        # don't call the qt directly; we may still need to wait for IsReady on stuff that was already fetching before we were called
        CG.client_controller.CallToThread( wait_for_preload )
        
    
    def GetContentUpdates( self ) -> list[ ClientContentUpdates.ContentUpdate ]:
        
        content_type = self._GetMyContentType()
        
        with self._lock:
            
            content_updates = []
            
            if self._i_am_local_tag_service:
                
                for pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]:
                    
                    content_updates.append( ClientContentUpdates.ContentUpdate( content_type, HC.CONTENT_UPDATE_DELETE, pair ) )
                    
                
                for pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]:
                    
                    content_updates.append( ClientContentUpdates.ContentUpdate( content_type, HC.CONTENT_UPDATE_ADD, pair ) )
                    
                
            else:
                
                current_pending = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]
                original_pending = self._original_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]
                
                current_petitioned = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]
                original_petitioned = self._original_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]
                
                new_pends = current_pending.difference( original_pending )
                rescinded_pends = original_pending.difference( current_pending )
                
                new_petitions = current_petitioned.difference( original_petitioned )
                rescinded_petitions = original_petitioned.difference( current_petitioned )
                
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( content_type, HC.CONTENT_UPDATE_RESCIND_PETITION, pair ) for pair in rescinded_petitions ) )
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( content_type, HC.CONTENT_UPDATE_RESCIND_PEND, pair ) for pair in rescinded_pends ) )
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( content_type, HC.CONTENT_UPDATE_PETITION, pair, reason = self._pairs_to_reasons[ pair ] ) for pair in new_petitions ) )
                content_updates.extend( ( ClientContentUpdates.ContentUpdate( content_type, HC.CONTENT_UPDATE_PEND, pair, reason = self._pairs_to_reasons[ pair ] ) for pair in new_pends ) )
                
            
        
        return content_updates
        
    
    def GetPairListCtrlInfo( self, pair ):
        
        with self._lock:
            
            in_pending = pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]
            in_petitioned = pair in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]
            
            reason = ''
            
            if pair in self._pairs_to_reasons:
                
                reason = self._pairs_to_reasons[ pair ]
                
                if reason is None:
                    
                    reason = 'unknown'
                    
                
                reason = f'Reason: {reason}'
                
            
            return ( in_pending, in_petitioned, reason )
            
        
    
    def GetPertinentPairsForTags( self, tags: collections.abc.Collection[ str ], show_all: bool, show_pending_and_petitioned: bool, pursue_whole_chain: bool ) -> set[ tuple[ str, str ] ]:
        """This guy can take a long time to return, so call it on a thread!"""
        
        if show_all and not self._have_fetched_all:
            
            statuses_to_pairs = self._FetchStatusToPairs()
            
            with self._lock:
                
                self._AddStatusesToPairsToCache( statuses_to_pairs )
                
            
            self._have_fetched_all = True
            self._have_fetched_pending_and_petitioned = True
            
        
        if show_pending_and_petitioned:
            
            if not self._have_fetched_pending_and_petitioned:
                
                # we fetch the whole chains rather than just the pending/petitioned pairs so we have a nice complete chain to add to our cache and know we don't have to ask further about any member of it going forward
                statuses_to_pairs = self._FetchStatusToPairs( where_chain_includes_pending_or_petitioned = True )
                
                with self._lock:
                    
                    self._AddStatusesToPairsToCache( statuses_to_pairs )
                    
                
                self._have_fetched_pending_and_petitioned = True
                
            
            tags = set( tags )
            
            for ( a, b ) in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ]:
                
                tags.add( a )
                tags.add( b )
                
            
            for ( a, b ) in self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ]:
                
                tags.add( a )
                tags.add( b )
                
            
        
        with self._lock:
            
            to_fetch = self._GetTagsToFetch( tags )
            
        
        if len( to_fetch ) > 0:
            
            self.InformTagsInterest( to_fetch )
            
            while not self.IsReady():
                
                if HydrusThreading.IsThreadShuttingDown():
                    
                    return set()
                    
                
                self._notify_new_tags_info.wait( 0.5 )
                
                self._notify_new_tags_info.clear()
                
            
        
        pertinent_pairs = set()
        
        with self._lock:
            
            if show_all:
                
                for ( status, pairs ) in self._current_statuses_to_pairs.items():
                    
                    if status == HC.CONTENT_STATUS_DELETED:
                        
                        continue
                        
                    
                    pertinent_pairs.update( pairs )
                    
                
            elif len( tags ) == 0:
                
                pass
                
            else:
                
                if pursue_whole_chain:
                    
                    next_pertinent_tags = tags
                    
                    seen_pertinent_tags = set()
                    
                    while len( next_pertinent_tags ) > 0:
                        
                        current_pertinent_tags = next_pertinent_tags
                        
                        seen_pertinent_tags.update( current_pertinent_tags )
                        
                        next_pertinent_tags = set()
                        
                        for ( status, pairs ) in self._current_statuses_to_pairs.items():
                            
                            if status == HC.CONTENT_STATUS_DELETED:
                                
                                continue
                                
                            
                            # show all appropriate
                            
                            for pair in pairs:
                                
                                ( a, b ) = pair
                                
                                if a in current_pertinent_tags or b in current_pertinent_tags:
                                    
                                    pertinent_pairs.add( pair )
                                    
                                    if a not in seen_pertinent_tags:
                                        
                                        next_pertinent_tags.add( a )
                                        
                                    
                                    if b not in seen_pertinent_tags:
                                        
                                        next_pertinent_tags.add( b )
                                        
                                    
                                
                            
                        
                    
                else:
                    
                    # at the moment this is only pertinent to parent searching, but we'll try and write it neutral anyway
                    
                    # start off searching in all directions, even if we disallow 'cousins' later
                    next_pertinent_as = set( tags )
                    next_pertinent_bs = set( tags )
                    
                    seen_pertinent_tags = set()
                    
                    while len( next_pertinent_as ) + len( next_pertinent_bs ) > 0:
                        
                        current_pertinent_children = next_pertinent_as
                        current_pertinent_parents = next_pertinent_bs
                        
                        seen_pertinent_tags.update( current_pertinent_children )
                        seen_pertinent_tags.update( current_pertinent_parents )
                        
                        next_pertinent_as = set()
                        next_pertinent_bs = set()
                        
                        for ( status, pairs ) in self._current_statuses_to_pairs.items():
                            
                            if status == HC.CONTENT_STATUS_DELETED:
                                
                                continue
                                
                            
                            # show all appropriate
                            
                            for pair in pairs:
                                
                                ( a, b ) = pair
                                
                                if a in current_pertinent_parents:
                                    
                                    pertinent_pairs.add( pair )
                                    
                                    if b not in seen_pertinent_tags:
                                        
                                        next_pertinent_bs.add( b )
                                        
                                    
                                
                                if b in current_pertinent_children:
                                    
                                    pertinent_pairs.add( pair )
                                    
                                    if a not in seen_pertinent_tags:
                                        
                                        next_pertinent_as.add( a )
                                        
                                    
                                
                            
                        
                    
                
            
        
        return pertinent_pairs
        
    
    def InformTagsInterest( self, tags: collections.abc.Collection[ str ] ):
        
        # ok the user just entered a new tag pair or something. we need to fetch the related pairs from the db so we can do logic
        
        def do_it():
            
            statuses_to_pairs = self._FetchStatusToPairs( tags = unfetched_tags )
            
            with self._lock:
                
                self._tags_being_fetched.difference_update( unfetched_tags )
                self._tags_done_fetched.update( unfetched_tags )
                
                self._AddStatusesToPairsToCache( statuses_to_pairs )
                
            
        
        def do_it_with_notify():
            
            try:
                
                do_it()
                
            finally:
                
                with self._lock:
                    
                    for ( win, c ) in self._notify_callables:
                        
                        CG.client_controller.CallAfterQtSafe( win, 'showing tag pair updates', c )
                        
                    
                    self._notify_new_tags_info.set()
                    
                
            
        
        with self._lock:
            
            if self._have_fetched_all:
                
                self._tags_done_fetched.update( tags )
                
                return
                
            
            unfetched_tags = self._GetTagsToFetch( tags )
            
            if len( unfetched_tags ) == 0:
                
                return
                
            
            self._tags_being_fetched.update( unfetched_tags )
            
        
        CG.client_controller.CallToThread( do_it_with_notify )
        
    
    def IsReady( self ) -> bool:
        
        with self._lock:
            
            return len( self._tags_being_fetched ) == 0
            
        
    
    def RegisterQtUpdateCall( self, widget: QW.QWidget, c: collections.abc.Callable ):
        
        with self._lock:
            
            self._notify_callables.append( ( widget, c ) )
            
        
    

# TODO: ok a future version of ParentActionContext would fetch sibling data so it can join and filter sibling-disparate groups
# probably saving tag->sibling data cache and then doing lookups based on that. OR storing double-pair copies with ideals

class ParentActionContext( TagPairActionContext ):
    
    def _FetchStatusToPairs( self, tags = None, where_chain_includes_pending_or_petitioned = False ):
        
        try:
            
            statuses_to_pairs = CG.client_controller.Read( 'tag_parents', self._service_key, tags = tags, where_chain_includes_pending_or_petitioned = where_chain_includes_pending_or_petitioned )
            
        except HydrusExceptions.ShutdownException:
            
            return {}
            
        
        return statuses_to_pairs
        
    
    def _GetFixedPendSuggestions( self ) -> collections.abc.Collection[ str ]:
        
        return [
            'obvious by definition (a sword is a weapon)',
            'character/series/studio/etc... belonging (character x belongs to series y)'
        ]
        
    
    def _GetFixedPetitionSuggestions( self ) -> collections.abc.Collection[ str ]:
        
        return [
            'obvious typo/mistake'
        ]
        
    
    def _GetMyContentType( self ) -> int:
        
        return HC.CONTENT_TYPE_TAG_PARENTS
        
    
    def AutoPetitionConflicts( self, widget, pairs ):
        
        # no conflicts for parents!
        pass
        
    

class SiblingActionContext( TagPairActionContext ):
    
    def AutoPetitionConflicts( self, widget, pairs ):
        
        with self._lock:
            
            current_pairs = self._current_statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ].union( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] ).difference( self._current_statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ] )
            
        
        current_olds_to_news = dict( current_pairs )
        
        current_olds = { current_old for ( current_old, current_new ) in current_pairs }
        
        pairs_to_auto_petition = set()
        
        for ( old, new ) in pairs:
            
            if old in current_olds:
                
                conflicting_new = current_olds_to_news[ old ]
                
                if conflicting_new != new:
                    
                    conflicting_pair = ( old, conflicting_new )
                    
                    pairs_to_auto_petition.add( conflicting_pair )
                    
                
            
        
        if len( pairs_to_auto_petition ) > 0:
            
            pairs_to_auto_petition = list( pairs_to_auto_petition )
            
            self.EnterCleanedPairs( widget, pairs_to_auto_petition, only_remove = True, forced_reason = AUTO_PETITION_REASON )
            
        
    
    def _FetchStatusToPairs( self, tags = None, where_chain_includes_pending_or_petitioned = False ):
        
        try:
            
            statuses_to_pairs = CG.client_controller.Read( 'tag_siblings', self._service_key, tags = tags, where_chain_includes_pending_or_petitioned = where_chain_includes_pending_or_petitioned )
            
        except HydrusExceptions.ShutdownException:
            
            return {}
            
        
        return statuses_to_pairs
        
    
    def _GetFixedPendSuggestions( self ) -> collections.abc.Collection[ str ]:
        
        return [
            'merging underscores/typos/phrasing/unnamespaced to a single uncontroversial good tag',
            'rewording/namespacing based on preference'
        ]
        
    
    def _GetFixedPetitionSuggestions( self ) -> collections.abc.Collection[ str ]:
        
        return [
            'obvious typo/mistake',
            'disambiguation',
            'correcting to repository standard'
        ]
        
    
    def _GetMyContentType( self ) -> int:
        
        return HC.CONTENT_TYPE_TAG_SIBLINGS
        
    
