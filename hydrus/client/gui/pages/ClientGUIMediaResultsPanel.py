import collections
import collections.abc
import itertools
import time

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetwork

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientPaths
from hydrus.client import ClientServices
from hydrus.client import ClientThreading
from hydrus.client.files import ClientFilesMaintenance
from hydrus.client.gui import ClientGUIDialogsManage
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIExceptionHandling
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvas
from hydrus.client.gui.canvas import ClientGUICanvasFrame
from hydrus.client.gui.duplicates import ClientGUIDuplicateActions
from hydrus.client.gui.duplicates import ClientGUIDuplicatesContentMergeOptions
from hydrus.client.gui.media import ClientGUIMediaSimpleActions
from hydrus.client.gui.media import ClientGUIMediaModalActions
from hydrus.client.gui.metadata import ClientGUIManageTags
from hydrus.client.gui.networking import ClientGUIHydrusNetwork
from hydrus.client.gui.pages import ClientGUIPageManager
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.panels import ClientGUIScrolledPanelsEdit
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaFileFilter
from hydrus.client.media import ClientMediaResultPrettyInfo
from hydrus.client.metadata import ClientContentUpdates

MAC_QUARTZ_OK = True

if HC.PLATFORM_MACOS:
    
    try:
        
        from hydrus.client import ClientMacIntegration
        
    except:
        
        MAC_QUARTZ_OK = False
        
    

class MediaResultsPanel( CAC.ApplicationCommandProcessorMixin, ClientMedia.ListeningMediaList, QW.QScrollArea ):
    
    selectedMediaTagPresentationChanged = QC.Signal( list, bool, bool )
    selectedMediaTagPresentationIncremented = QC.Signal( list )
    statusTextChanged = QC.Signal( str )
    
    focusMediaChanged = QC.Signal( ClientMedia.Media )
    focusMediaCleared = QC.Signal()
    focusMediaPaused = QC.Signal()
    refreshQuery = QC.Signal()
    
    newMediaAdded = QC.Signal()
    
    filesAdded = QC.Signal( list )
    filesRemoved = QC.Signal( list )
    
    def __init__( self, parent, page_key, page_manager: ClientGUIPageManager.PageManager, media_results ):
        
        self._qss_colours = {
            CC.COLOUR_THUMBGRID_BACKGROUND : QG.QColor( 255, 255, 255 ),
            CC.COLOUR_THUMB_BACKGROUND : QG.QColor( 255, 255, 255 ),
            CC.COLOUR_THUMB_BACKGROUND_SELECTED : QG.QColor( 217, 242, 255 ),
            CC.COLOUR_THUMB_BACKGROUND_REMOTE : QG.QColor( 32, 32, 36 ),
            CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED : QG.QColor( 64, 64, 72 ),
            CC.COLOUR_THUMB_BORDER : QG.QColor( 223, 227, 230 ),
            CC.COLOUR_THUMB_BORDER_SELECTED : QG.QColor( 1, 17, 26 ),
            CC.COLOUR_THUMB_BORDER_REMOTE : QG.QColor( 248, 208, 204 ),
            CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED : QG.QColor( 227, 66, 52 )
        }
        
        self._page_key = page_key
        self._page_manager = page_manager
        
        # TODO: Assuming the canvas listeningmedialist refactoring went well, this guy is next
        # take out the class inheritance, instead create a (non-listening) self._media_list, and fix all method calls to self._GetFirst and so on to instead point at that
        # rewrite process(content/service)updates to update the list as needed
        # delete the listeningmedialist class def
        
        # TODO: BRUH REWRITE THIS GARBAGE
        # we don't really want to be messing around with *args, **kwargs in __init__/super() gubbins, and this is highlighted as we move to super() and see this is all a mess!!
        # obviously decouple the list from the panel here so we aren't trying to do everything in one class
        super().__init__( self._page_manager.GetLocationContext(), media_results, parent )
        
        self.setObjectName( 'HydrusMediaList' )
        
        self.setFrameStyle( QW.QFrame.Shape.Panel | QW.QFrame.Shadow.Sunken )
        self.setLineWidth( 2 )
        
        self.resize( QC.QSize( 20, 20 ) )
        self.setWidget( QW.QWidget( self ) )
        self.setWidgetResizable( True )
        
        self._UpdateBackgroundColour()
        
        self._vertical_scrollbar_pos_on_hide = None
        
        self.verticalScrollBar().setSingleStep( 50 )
        
        self._focused_media = None
        self._last_hit_media = None
        self._next_best_media_if_focuses_removed = None
        self._shift_select_started_with_this_media = None
        self._media_added_in_current_shift_select = set()
        
        self._empty_page_status_override = None
        
        CG.client_controller.sub( self, 'AddMediaResults', 'add_media_results' )
        CG.client_controller.sub( self, '_UpdateBackgroundColour', 'notify_new_colourset' )
        CG.client_controller.sub( self, 'SelectByTags', 'select_files_with_tags' )
        
        self._had_changes_to_tag_presentation_while_hidden = False
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, self, [ 'media', 'thumbnails' ] )
        
        self.setWidget( self._InnerWidget( self ) )
        self.setWidgetResizable( True )
        
    
    def __bool__( self ):
        
        return QP.isValid( self )
        
    
    def _Archive( self ):
        
        hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_INBOX )
        
        if len( hashes ) > 0:
            
            if HC.options[ 'confirm_archive' ]:
                
                if len( hashes ) > 1:
                    
                    message = 'Archive ' + HydrusNumbers.ToHumanInt( len( hashes ) ) + ' files?'
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.DialogCode.Accepted:
                        
                        return
                        
                    
                
            
            CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, hashes ) ) )
            
        
    
    def _ArchiveDeleteFilter( self ):
        
        if len( self._selected_media ) == 0:
            
            media_results = self.GetMediaResults( discriminant = CC.DISCRIMINANT_LOCAL_BUT_NOT_IN_TRASH, selected_media = set( self._sorted_media ), for_media_viewer = True )
            
        else:
            
            media_results = self.GetMediaResults( discriminant = CC.DISCRIMINANT_LOCAL_BUT_NOT_IN_TRASH, selected_media = set( self._selected_media ), for_media_viewer = True )
            
        
        if len( media_results ) > 0:
            
            self.SetFocusedMedia( None )
            
            canvas_frame = ClientGUICanvasFrame.CanvasFrame( self.window() )
            
            canvas_window = ClientGUICanvas.CanvasMediaListFilterArchiveDelete( canvas_frame, self._page_key, self._location_context, media_results )
            
            canvas_frame.SetCanvas( canvas_window )
            
            self._ConnectCanvasWindowSignals( canvas_window )
            
        
    
    def _ClearDeleteRecord( self ):
        
        media = self._GetSelectedFlatMedia()
        
        ClientGUIMediaModalActions.ClearDeleteRecord( self, media )
        
    
    def _ConnectCanvasWindowSignals( self, canvas_window: ClientGUICanvas.Canvas ):
        
        if isinstance( canvas_window, ClientGUICanvas.CanvasMediaList ):
            
            canvas_window.exitFocusMedia.connect( self.NotifyFocusedMediaFromCanvasExiting )
            
            canvas_window.exitFocusMediaForced.connect( self.SetFocusedMedia )
            
            canvas_window.userRemovedMedia.connect( self.RemoveMedia )
            
        
        if isinstance( canvas_window, ClientGUICanvas.CanvasWithHovers ):
            
            canvas_window.canvasWithHoversExiting.connect( CG.client_controller.gui.NotifyMediaViewerExiting )
            
        
    
    def _Delete( self, file_service_key = None, only_those_in_file_service_key = None ):
        
        if file_service_key is None:
            
            if len( self._location_context.current_service_keys ) == 1:
                
                ( possible_suggested_file_service_key, ) = self._location_context.current_service_keys
                
                if CG.client_controller.services_manager.GetServiceType( possible_suggested_file_service_key ) in HC.SPECIFIC_LOCAL_FILE_SERVICES + ( HC.FILE_REPOSITORY, ):
                    
                    file_service_key = possible_suggested_file_service_key
                    
                
            
        
        media_to_delete = ClientMedia.FlattenMedia( self._selected_media )
        
        if only_those_in_file_service_key is not None:
            
            media_to_delete = ClientMedia.FlattenMedia( media_to_delete )
            
            media_to_delete = [ m for m in media_to_delete if only_those_in_file_service_key in m.GetLocationsManager().GetCurrent() ]
            
        
        if file_service_key is None or CG.client_controller.services_manager.GetServiceType( file_service_key ) in HC.LOCAL_FILE_SERVICES:
            
            default_reason = 'Deleted from Media Page.'
            
        else:
            
            default_reason = 'admin'
            
        
        try:
            
            ( hashes_physically_deleted, content_update_packages ) = ClientGUIDialogsQuick.GetDeleteFilesJobs( self, media_to_delete, default_reason, suggested_file_service_key = file_service_key )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        def do_it( content_update_packages ):
            
            display_time = HydrusTime.GetNow() + 3
            message_pubbed = False
            
            job_status = ClientThreading.JobStatus() # not cancellable, this stuff isn't a nice mix
            
            job_status.SetStatusTitle( 'deleting files' )
            # no text, the content update packages are not always a nice mix
            
            num_to_do = len( content_update_packages )
            
            for ( i, content_update_package ) in enumerate( content_update_packages ):
                
                job_status.SetGauge( i, num_to_do )
                
                if not message_pubbed and HydrusTime.TimeHasPassed( display_time ):
                    
                    CG.client_controller.pub( 'message', job_status )
                    
                    message_pubbed = True
                    
                
                CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
                
            
            job_status.FinishAndDismiss()
            
        
        CG.client_controller.CallToThread( do_it, content_update_packages )
        
    
    def _DeselectSelect( self, media_to_deselect, media_to_select ):
        
        if len( media_to_deselect ) > 0:
            
            for m in media_to_deselect: m.Deselect()
            
            self._RedrawMedia( media_to_deselect )
            
            self._selected_media.difference_update( media_to_deselect )
            
        
        if len( media_to_select ) > 0:
            
            for m in media_to_select: m.Select()
            
            self._RedrawMedia( media_to_select )
            
            self._selected_media.update( media_to_select )
            
        
        if len( media_to_select ) + len( media_to_deselect ) > 0:
            
            self._PublishSelectionChange()
            
        
    
    def _DownloadSelected( self ):
        
        hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_NOT_LOCAL )
        
        self._DownloadHashes( hashes )
        
    
    def _DownloadHashes( self, hashes ):
        
        CG.client_controller.quick_download_manager.DownloadFiles( hashes )
        
    
    def _EndShiftSelect( self ):
        
        self._shift_select_started_with_this_media = None
        self._media_added_in_current_shift_select = set()
        
    
    def _GetFocusSingleton( self ) -> ClientMedia.MediaSingleton:
        
        if self._focused_media is not None:
            
            media_singleton = self._focused_media.GetDisplayMedia()
            
            if media_singleton is not None:
                
                return media_singleton
                
            
        
        raise HydrusExceptions.DataMissing( 'No media singleton!' )
        
    
    def _GetMediasForFileCommandTarget( self, file_command_target: int ) -> collections.abc.Collection[ ClientMedia.MediaSingleton ]:
        
        if file_command_target == CAC.FILE_COMMAND_TARGET_FOCUSED_FILE:
            
            if self._HasFocusSingleton():
                
                media = self._GetFocusSingleton()
                
                return [ media.GetDisplayMedia() ]
                
            
        elif file_command_target == CAC.FILE_COMMAND_TARGET_SELECTED_FILES:
            
            if len( self._selected_media ) > 0:
                
                medias = self._GetSelectedMediaOrdered()
                
                return ClientMedia.FlattenMedia( medias )
                
            
        
        return []
        
    
    def _GetNumSelected( self ):
        
        return sum( [ media.GetNumFiles() for media in self._selected_media ] )
        
    
    def _GetPrettyStatusForStatusBar( self ) -> str:
        
        num_files = len( self._hashes )
        
        if self._empty_page_status_override is not None:
            
            if num_files == 0:
                
                return self._empty_page_status_override
                
            else:
                
                # user has dragged files onto this page or similar
                
                self._empty_page_status_override = None
                
            
        
        num_selected = self._GetNumSelected()
        
        num_files_string = ClientMedia.GetMediasFiletypeSummaryString( self._sorted_media )
        selected_files_string = ClientMedia.GetMediasFiletypeSummaryString( self._selected_media )
        
        s = num_files_string # 23 files
        
        if num_selected == 0:
            
            if num_files > 0:
                
                pretty_total_size = self._GetPrettyTotalSize()
                
                s += ' - totalling ' + pretty_total_size
                
                pretty_total_duration = self._GetPrettyTotalDuration()
                
                if pretty_total_duration != '':
                    
                    s += ', {}'.format( pretty_total_duration )
                    
                
            
        else:
            
            s += f' - {selected_files_string} selected, '
            
            if len( self._selected_media ) == 1 and len( list(self._selected_media)[0].GetHashes() ) == 1 and CG.client_controller.new_options.GetBoolean( 'show_extended_single_file_info_in_status_bar' ):
                
                # TODO: Were I feeling clever, this guy would also emit a tooltip, which we can calculate here no prob
                
                singleton_media = ClientMedia.FlattenMedia( self._selected_media )[0]
                
                lines = ClientMediaResultPrettyInfo.GetPrettyMediaResultInfoLines( singleton_media.GetMediaResult(), only_interesting_lines = True )
                
                lines = [ line for line in lines if not line.IsSubmenu() ]
                
                texts = [ line.text for line in lines ]
                
                s += ', '.join( texts )
                
            else:
                
                num_inbox = sum( ( media.GetNumInbox() for media in self._selected_media ) )
                
                if num_inbox == num_selected:
                    
                    inbox_phrase = 'all in inbox' if num_inbox > 1 else 'in inbox'
                    
                elif num_inbox == 0:
                    
                    inbox_phrase = 'all archived' if num_selected > 1 else 'archived'
                    
                else:
                    
                    inbox_phrase = '{} in inbox and {} archived'.format( HydrusNumbers.ToHumanInt( num_inbox ), HydrusNumbers.ToHumanInt( num_selected - num_inbox ) )
                    
                
                pretty_total_size = self._GetPrettyTotalSize( only_selected = True )
                
                s += '{}, totalling {}'.format( inbox_phrase, pretty_total_size )
                
                pretty_total_duration = self._GetPrettyTotalDuration( only_selected = True )
                
                if pretty_total_duration != '':
                    
                    s += ', {}'.format( pretty_total_duration )
                    
                
            
        
        return s
        
    
    def _GetPrettyTotalDuration( self, only_selected = False ):
        
        if only_selected:
            
            media_source = self._selected_media
            
        else:
            
            media_source = self._sorted_media
            
        
        if len( media_source ) == 0 or False in ( media.HasDuration() for media in media_source ):
            
            return ''
            
        
        total_duration = sum( ( media.GetDurationMS() for media in media_source ) )
        
        return HydrusTime.MillisecondsDurationToPrettyTime( total_duration )
        
    
    def _GetPrettyTotalSize( self, only_selected = False ):
        
        if only_selected:
            
            media_source = self._selected_media
            
        else:
            
            media_source = self._sorted_media
            
        
        total_size = sum( [ media.GetSize() for media in media_source ] )
        
        unknown_size = False in ( media.IsSizeDefinite() for media in media_source )
        
        if total_size == 0:
            
            if unknown_size:
                
                return 'unknown size'
                
            else:
                
                return HydrusData.ToHumanBytes( 0 )
                
            
        else:
            
            if unknown_size:
                
                return HydrusData.ToHumanBytes( total_size ) + ' + some unknown size'
                
            else:
                
                return HydrusData.ToHumanBytes( total_size )
                
            
        
    
    def _GetSelectedHashes( self, is_in_file_service_key = None, discriminant = None, is_not_in_file_service_key = None, ordered = False ):
        
        if ordered:
            
            result = []
            
            for media in self._GetSelectedMediaOrdered():
                
                result.extend( media.GetHashes( is_in_file_service_key, discriminant, is_not_in_file_service_key, ordered ) )
                
            
        else:
            
            result = set()
            
            for media in self._selected_media:
                
                result.update( media.GetHashes( is_in_file_service_key, discriminant, is_not_in_file_service_key, ordered ) )
                
            
        
        return result
        
    
    def _GetSelectedCollections( self ):
        
        sorted_selected_collections = [ media for media in self._sorted_media if media.IsCollection() and media in self._selected_media ]
        
        return sorted_selected_collections
        

    def _GetSelectedFlatMedia( self, is_in_file_service_key = None, discriminant = None, is_not_in_file_service_key = None ):
        
        # this now always delivers sorted results
        
        sorted_selected_media = [ media for media in self._sorted_media if media in self._selected_media ]
        
        flat_media = ClientMedia.FlattenMedia( sorted_selected_media )
        
        flat_media = [ media for media in flat_media if media.MatchesDiscriminant( is_in_file_service_key = is_in_file_service_key, discriminant = discriminant, is_not_in_file_service_key = is_not_in_file_service_key ) ]
        
        return flat_media
        
    
    def _GetSelectedMediaOrdered( self ):
        
        # note that this is fast because sorted_media is custom
        return sorted( self._selected_media, key = lambda m: self._sorted_media.index( m ) )
        
    
    def _GetSortedSelectedMimeDescriptors( self ):
        
        def GetDescriptor( plural, classes, num_collections ):
            
            suffix = 's' if plural else ''
            
            if len( classes ) == 0:
                
                return 'file' + suffix
                
            
            if len( classes ) == 1:
                
                ( mime, ) = classes
                
                if mime == HC.APPLICATION_HYDRUS_CLIENT_COLLECTION:
                    
                    collections_suffix = 's' if num_collections > 1 else ''
                    
                    return 'file{} in {} collection{}'.format( suffix, HydrusNumbers.ToHumanInt( num_collections ), collections_suffix )
                    
                else:
                    
                    return HC.mime_string_lookup[ mime ] + suffix
                    
                
            
            if len( classes.difference( HC.IMAGES ) ) == 0:
                
                return 'image' + suffix
                
            elif len( classes.difference( HC.ANIMATIONS ) ) == 0:
                
                return 'animation' + suffix
                
            elif len( classes.difference( HC.VIDEO ) ) == 0:
                
                return 'video' + suffix
                
            elif len( classes.difference( HC.AUDIO ) ) == 0:
                
                return 'audio file' + suffix
                
            else:
                
                return 'file' + suffix
                
            
        
        if len( self._sorted_media ) > 1000:
            
            sorted_mime_descriptor = 'files'
            
        else:
            
            sorted_mimes = { media.GetMime() for media in self._sorted_media }
            
            if HC.APPLICATION_HYDRUS_CLIENT_COLLECTION in sorted_mimes:
                
                num_collections = len( [ media for media in self._sorted_media if isinstance( media, ClientMedia.MediaCollection ) ] )
                
            else:
                
                num_collections = 0
                
            
            plural = len( self._sorted_media ) > 1 or sum( ( m.GetNumFiles() for m in self._sorted_media ) ) > 1
            
            sorted_mime_descriptor = GetDescriptor( plural, sorted_mimes, num_collections )
            
        
        if len( self._selected_media ) > 1000:
            
            selected_mime_descriptor = 'files'
            
        else:
            
            selected_mimes = { media.GetMime() for media in self._selected_media }
            
            if HC.APPLICATION_HYDRUS_CLIENT_COLLECTION in selected_mimes:
                
                num_collections = len( [ media for media in self._selected_media if isinstance( media, ClientMedia.MediaCollection ) ] )
                
            else:
                
                num_collections = 0
                
            
            plural = len( self._selected_media ) > 1 or sum( ( m.GetNumFiles() for m in self._selected_media ) ) > 1
            
            selected_mime_descriptor = GetDescriptor( plural, selected_mimes, num_collections )
            
        
        return ( sorted_mime_descriptor, selected_mime_descriptor )
        
    
    def _GetYStart( self ):
        
        visible_rect = QP.ScrollAreaVisibleRect( self )
        
        visible_rect_y = visible_rect.y()
        
        visible_rect_height = visible_rect.height()
        
        my_virtual_size = self.widget().size()
        
        my_virtual_height = my_virtual_size.height()
        
        max_y = my_virtual_height - visible_rect_height
        
        y_start = max( 0, visible_rect_y )
        
        y_start = min( y_start, max_y )
        
        return y_start
        
    
    def _HasFocusSingleton( self ) -> bool:
        
        try:
            
            media = self._GetFocusSingleton()
            
            return True
            
        except HydrusExceptions.DataMissing:
            
            return False
            
        
    
    def _HitMedia( self, media, ctrl, shift ):
        
        if media is None:
            
            if not ctrl and not shift:
                
                self._Select( ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_NONE ) )
                self._SetFocusedMedia( None )
                self._EndShiftSelect()
                
            
        else:
            
            if ctrl and not shift:
                
                if media.IsSelected():
                    
                    self._DeselectSelect( ( media, ), () )
                    
                    if self._focused_media == media:
                        
                        self._SetFocusedMedia( None )
                        
                    
                    self._EndShiftSelect()
                    
                else:
                    
                    self._DeselectSelect( (), ( media, ) )
                    
                    focus_it = False
                    
                    if CG.client_controller.new_options.GetBoolean( 'focus_preview_on_ctrl_click' ):
                        
                        if CG.client_controller.new_options.GetBoolean( 'focus_preview_on_ctrl_click_only_static' ):
                            
                            focus_it = media.GetDurationMS() is None
                            
                        else:
                            
                            focus_it = True
                            
                        
                    
                    if focus_it:
                        
                        self._SetFocusedMedia( media )
                        
                    else:
                        
                        self._last_hit_media = media
                        
                    
                    self._StartShiftSelect( media )
                    
                
            elif shift and self._shift_select_started_with_this_media is not None:
                
                start_index = self._sorted_media.index( self._shift_select_started_with_this_media )
                
                end_index = self._sorted_media.index( media )
                
                if start_index < end_index:
                    
                    media_from_start_of_shift_to_end = set( self._sorted_media[ start_index : end_index + 1 ] )
                    
                else:
                    
                    media_from_start_of_shift_to_end = set( self._sorted_media[ end_index : start_index + 1 ] )
                    
                
                media_to_deselect = [ m for m in self._media_added_in_current_shift_select if m not in media_from_start_of_shift_to_end ]
                media_to_select = [ m for m in media_from_start_of_shift_to_end if not m.IsSelected() ]
                
                self._media_added_in_current_shift_select.difference_update( media_to_deselect )
                self._media_added_in_current_shift_select.update( media_to_select )
                
                self._DeselectSelect( media_to_deselect, media_to_select )
                
                focus_it = False
                
                if CG.client_controller.new_options.GetBoolean( 'focus_preview_on_shift_click' ):
                    
                    if CG.client_controller.new_options.GetBoolean( 'focus_preview_on_shift_click_only_static' ):
                        
                        focus_it = media.GetDurationMS() is None
                        
                    else:
                        
                        focus_it = True
                        
                    
                
                if focus_it:
                    
                    self._SetFocusedMedia( media )
                    
                else:
                    
                    self._last_hit_media = media
                    
                
            else:
                
                if not media.IsSelected():
                    
                    self._DeselectSelect( self._selected_media, ( media, ) )
                    
                else:
                    
                    self._PublishSelectionChange()
                    
                
                self._SetFocusedMedia( media )
                self._StartShiftSelect( media )
                
            
        
    
    def _Inbox( self ):
        
        hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_ARCHIVE, is_in_file_service_key = CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY  )
        
        if len( hashes ) > 0:
            
            if HC.options[ 'confirm_archive' ]:
                
                if len( hashes ) > 1:
                    
                    message = 'Send {} files to inbox?'.format( HydrusNumbers.ToHumanInt( len( hashes ) ) )
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.DialogCode.Accepted:
                        
                        return
                        
                    
                
            
            CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, hashes ) ) )
            
        
    
    def _LaunchMediaViewer( self, first_media = None ):
        
        if self._HasFocusSingleton():
            
            media = self._GetFocusSingleton()
            
            if not media.GetLocationsManager().IsLocal():
                
                return
                
            
            new_options = CG.client_controller.new_options
            
            ( media_show_action, media_start_paused, media_start_with_embed ) = new_options.GetMediaShowAction( media.GetMime() )
            
            if media_show_action == CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY:
                
                hash = media.GetHash()
                mime = media.GetMime()
                
                client_files_manager = CG.client_controller.client_files_manager
                
                path = client_files_manager.GetFilePath( hash, mime )
                
                new_options = CG.client_controller.new_options
                
                launch_path = new_options.GetMimeLaunch( mime )
                
                HydrusPaths.LaunchFile( path, launch_path )
                
                return
                
            elif media_show_action == CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW:
                
                return
                
            
        
        media_results = self.GetMediaResults( discriminant = CC.DISCRIMINANT_LOCAL, for_media_viewer = True )
        
        if len( media_results ) > 0:
            
            if first_media is not None:
                
                first_media = first_media.GetDisplayMedia()
                
                first_media_result = first_media.GetMediaResult()
                
                if first_media_result not in media_results:
                    
                    first_media = None
                    
                
            
            if first_media is None and self._focused_media is not None:
                
                first_media = self._focused_media
                
            
            if first_media is not None:
                
                first_media = first_media.GetDisplayMedia()
                
            
            if first_media is not None and first_media.GetLocationsManager().IsLocal():
                
                first_hash = first_media.GetHash()
                
            else:
                
                first_hash = None
                
            
            self.SetFocusedMedia( None )
            
            #
            
            canvas_frame = ClientGUICanvasFrame.CanvasFrame( self.window() )
            
            canvas_window = ClientGUICanvas.CanvasMediaListBrowser( canvas_frame, self._page_key, self._location_context, media_results, first_hash )
            
            canvas_window.canvasWithHoversExiting.connect( CG.client_controller.gui.NotifyMediaViewerExiting )
            
            canvas_frame.SetCanvas( canvas_window )
            
            self._ConnectCanvasWindowSignals( canvas_window )
            
        
    
    def _ManageNotes( self ):
        
        if self._HasFocusSingleton():
            
            media = self._GetFocusSingleton()
            
            ClientGUIMediaModalActions.EditFileNotes( self, media )
            
            self.setFocus( QC.Qt.FocusReason.OtherFocusReason )
            
        
    
    def _ManageRatings( self ):
        
        flat_media = ClientMedia.FlattenMedia( self._selected_media )
        
        if len( flat_media ) > 0:
            
            if len( CG.client_controller.services_manager.GetServices( HC.RATINGS_SERVICES ) ) > 0:
                
                with ClientGUIDialogsManage.DialogManageRatings( self, flat_media ) as dlg:
                    
                    dlg.exec()
                    
                
                self.setFocus( QC.Qt.FocusReason.OtherFocusReason )
                
            
        
    
    def _ManageTags( self ):
        
        flat_media = ClientMedia.FlattenMedia( self._GetSelectedMediaOrdered() )
        
        if len( flat_media ) > 0:
            
            num_files = self._GetNumSelected()
            
            title = 'manage tags for ' + HydrusNumbers.ToHumanInt( num_files ) + ' files'
            frame_key = 'manage_tags_dialog'
            
            with ClientGUITopLevelWindowsPanels.DialogManage( self, title, frame_key ) as dlg:
                
                panel = ClientGUIManageTags.ManageTagsPanel( dlg, self._location_context, CC.TAG_PRESENTATION_SEARCH_PAGE_MANAGE_TAGS, flat_media )
                
                dlg.SetPanel( panel )
                
                dlg.exec()
                
            
            self.setFocus( QC.Qt.FocusReason.OtherFocusReason )
            
        
    
    def _ManageTimestamps( self ):
        
        ordered_selected_media = self._GetSelectedMediaOrdered()
        
        ordered_selected_flat_media = ClientMedia.FlattenMedia( ordered_selected_media )
        
        if len( ordered_selected_flat_media ) > 0:
            
            ClientGUIMediaModalActions.EditFileTimestamps( self, ordered_selected_flat_media )
            
            self.setFocus( QC.Qt.FocusReason.OtherFocusReason )
            
        
    
    def _ManageURLs( self ):
        
        flat_media = ClientMedia.FlattenMedia( self._selected_media )
        
        if len( flat_media ) > 0:
            
            num_files = self._GetNumSelected()
            
            title = 'manage urls for {} files'.format( num_files )
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, title, frame_key = 'manage_urls_dialog' ) as dlg:
                
                panel = ClientGUIScrolledPanelsEdit.EditURLsPanel( dlg, flat_media )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    pending_content_updates = panel.GetValue()
                    
                    if len( pending_content_updates ) > 0:
                        
                        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, pending_content_updates )
                        
                        CG.client_controller.Write( 'content_updates', content_update_package )
                        
                    
                
            
            self.setFocus( QC.Qt.FocusReason.OtherFocusReason )
            
        
    
    def _MediaIsVisible( self, media ):
        
        return True
        
    
    def _ModifyUploaders( self, file_service_key ):
        
        hashes = self._GetSelectedHashes()
        
        contents = [ HydrusNetwork.Content( HC.CONTENT_TYPE_FILES, ( hash, ) ) for hash in hashes ]
        
        if len( contents ) > 0:
            
            subject_account_identifiers = [ HydrusNetwork.AccountIdentifier( content = content ) for content in contents ]
            
            frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'manage accounts' )
            
            panel = ClientGUIHydrusNetwork.ModifyAccountsPanel( frame, file_service_key, subject_account_identifiers )
            
            frame.SetPanel( panel )
            
        
    
    def _OpenFileInWebBrowser( self ):
        
        if self._HasFocusSingleton():
            
            focused_singleton = self._GetFocusSingleton()
            
            if focused_singleton.GetLocationsManager().IsLocal():
                
                hash = focused_singleton.GetHash()
                mime = focused_singleton.GetMime()
                
                client_files_manager = CG.client_controller.client_files_manager
                
                path = client_files_manager.GetFilePath( hash, mime )
                
                self.focusMediaPaused.emit()
                
                ClientPaths.LaunchPathInWebBrowser( path )
                
            
        
    
    def _MacQuicklook( self ):
        
        if HC.PLATFORM_MACOS and self._HasFocusSingleton():
            
            focused_singleton = self._GetFocusSingleton()
            
            if focused_singleton.GetLocationsManager().IsLocal():
                
                hash = focused_singleton.GetHash()
                mime = focused_singleton.GetMime()
                
                client_files_manager = CG.client_controller.client_files_manager
                
                path = client_files_manager.GetFilePath( hash, mime )
                
                self.focusMediaPaused.emit()
                
                if not MAC_QUARTZ_OK:
                    
                    HydrusData.ShowText( 'Sorry, could not do the Quick Look integration--it looks like your venv does not support it. If you are running from source, try rebuilding it!' )
                    
                
                ClientMacIntegration.show_quicklook_for_path( path )
                
            
        
    
    def _OpenKnownURL( self ):
        
        if self._HasFocusSingleton():
            
            focused_singleton = self._GetFocusSingleton()
            
            ClientGUIMediaModalActions.DoOpenKnownURLFromShortcut( self, focused_singleton )
            
        
    
    def _PetitionFiles( self, remote_service_key ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:
            
            remote_service = CG.client_controller.services_manager.GetService( remote_service_key )
            
            service_type = remote_service.GetServiceType()
            
            if service_type == HC.FILE_REPOSITORY:
                
                if len( hashes ) == 1:
                    
                    message = 'Enter a reason for this file to be removed from {}.'.format( remote_service.GetName() )
                    
                else:
                    
                    message = 'Enter a reason for these {} files to be removed from {}.'.format( HydrusNumbers.ToHumanInt( len( hashes ) ), remote_service.GetName() )
                    
                
                try:
                    
                    reason = ClientGUIDialogsQuick.EnterText( self, message )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
                content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, hashes, reason = reason )
                
                content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( remote_service_key, content_update )
                
                CG.client_controller.Write( 'content_updates', content_update_package )
                
                self.setFocus( QC.Qt.FocusReason.OtherFocusReason )
                
            elif service_type == HC.IPFS:
                
                content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, hashes, reason = 'ipfs' )
                
                content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( remote_service_key, content_update )
                
                CG.client_controller.Write( 'content_updates', content_update_package )
                
            
        
    
    def _PublishSelectionChange( self, tags_changed = False ):
        
        if CG.client_controller.gui.IsCurrentPage( self._page_key ):
            
            capped_due_to_setting = False
            
            if len( self._selected_media ) == 0:
                
                number_of_unselected_medias_to_present_tags_for = CG.client_controller.new_options.GetNoneableInteger( 'number_of_unselected_medias_to_present_tags_for' )
                
                if number_of_unselected_medias_to_present_tags_for is None:
                    
                    tags_media = self._sorted_media
                    
                else:
                    
                    capped_due_to_setting = len( self._sorted_media ) > number_of_unselected_medias_to_present_tags_for
                    
                    tags_media = self._sorted_media[ :number_of_unselected_medias_to_present_tags_for ]
                    
                
            else:
                
                tags_media = self._selected_media
                
            
            tags_media = list( tags_media )
            
            tags_changed = tags_changed or self._had_changes_to_tag_presentation_while_hidden
            
            self.selectedMediaTagPresentationChanged.emit( tags_media, tags_changed, capped_due_to_setting )
            
            self.statusTextChanged.emit( self._GetPrettyStatusForStatusBar() )
            
            if tags_changed:
                
                self._had_changes_to_tag_presentation_while_hidden = False
                
            
        elif tags_changed:
            
            self._had_changes_to_tag_presentation_while_hidden = True
            
        
    
    def _PublishSelectionIncrement( self, medias ):
        
        if CG.client_controller.gui.IsCurrentPage( self._page_key ):
            
            medias = list( medias )
            
            self.selectedMediaTagPresentationIncremented.emit( medias )
            
            self.statusTextChanged.emit( self._GetPrettyStatusForStatusBar() )
            
        else:
            
            self._had_changes_to_tag_presentation_while_hidden = True
            
        
    
    def _RecalculateVirtualSize( self, called_from_resize_event = False ):
        
        pass
        
    
    def _RedrawMedia( self, media ):
        
        pass
        
    
    def _RegenerateFileData( self, job_type ):
        
        flat_media = self._GetSelectedFlatMedia()
        
        num_files = len( flat_media )
        
        if num_files > 0:
            
            if job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FILE_METADATA:
                
                message = 'This will reparse the {} selected files\' metadata.'.format( HydrusNumbers.ToHumanInt( num_files ) )
                message += '\n' * 2
                message += 'If the files were imported before some more recent improvement in the parsing code (such as EXIF rotation or bad video resolution or duration or frame count calculation), this will update them.'
                
            elif job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL:
                
                message = 'This will force-regenerate the {} selected files\' thumbnails.'.format( HydrusNumbers.ToHumanInt( num_files ) )
                
            elif job_type == ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL:
                
                message = 'This will regenerate the {} selected files\' thumbnails, but only if they are the wrong size.'.format( HydrusNumbers.ToHumanInt( num_files ) )
                
            else:
                
                message = ClientFilesMaintenance.regen_file_enum_to_description_lookup[ job_type ]
                
            
            do_it_now = True
            
            if num_files > 50:
                
                message += '\n' * 2
                message += 'You have selected {} files, so this job may take some time. You can run it all now or schedule it to the overall file maintenance queue for later spread-out processing.'.format( HydrusNumbers.ToHumanInt( num_files ) )
                
                yes_tuples = []
                
                yes_tuples.append( ( 'do it now', 'now' ) )
                yes_tuples.append( ( 'do it later', 'later' ) )
                
                try:
                    
                    result = ClientGUIDialogsQuick.GetYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
                do_it_now = result == 'now'
                
            else:
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return
                    
                
            
            if do_it_now:
                
                self._SetFocusedMedia( None )
                
                time.sleep( 0.1 )
                
                media_results = [ m.GetMediaResult() for m in flat_media ]
                
                CG.client_controller.CallToThread( CG.client_controller.files_maintenance_manager.RunJobImmediately, media_results, job_type )
                
            else:
                
                hashes = { media.GetHash() for media in flat_media }
                
                CG.client_controller.CallToThread( CG.client_controller.files_maintenance_manager.ScheduleJob, hashes, job_type )
                
            
        
    
    def _Remove( self, file_filter: ClientMediaFileFilter.FileFilter ):
        
        hashes = file_filter.GetMediaListHashes( self )
        
        if len( hashes ) > 0:
            
            self._RemoveMediaByHashes( hashes )
            
        
    
    def _RemoveMediaByHashes( self, hashes ):
        
        # even though this guy eventually calls _RemoveMediaDirectly and thus filesRemoved, this doesn't happen when a collection removes a file internally
        
        super()._RemoveMediaByHashes( hashes )
        
        self.filesRemoved.emit( list( hashes ) )
        
    
    def _RemoveMediaDirectly( self, singleton_media, collected_media ):
        
        super()._RemoveMediaDirectly( singleton_media, collected_media )
        
        flat_media = list( singleton_media ) + ClientMedia.FlattenMedia( collected_media )
        
        hashes = [ m.GetHash() for m in flat_media ]
        
        self.filesRemoved.emit( hashes )
        
    
    def _RescindDownloadSelected( self ):
        
        hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_NOT_LOCAL )
        
        CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_RESCIND_PEND, hashes ) ) )
        
    
    def _RescindPetitionFiles( self, file_service_key ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:   
            
            CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( file_service_key, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_RESCIND_PETITION, hashes ) ) )
            
        
    
    def _RescindUploadFiles( self, file_service_key ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:   
            
            CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( file_service_key, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_RESCIND_PEND, hashes ) ) )
            
        
    
    def _Select( self, file_filter: ClientMediaFileFilter.FileFilter ):
        
        matching_media = file_filter.GetMediaListMedia( self )
        
        media_to_deselect = self._selected_media.difference( matching_media )
        media_to_select = matching_media.difference( self._selected_media )
        
        move_focus = self._focused_media in media_to_deselect or self._focused_media is None
        
        if move_focus or self._shift_select_started_with_this_media in media_to_deselect:
            
            self._EndShiftSelect()
            
        
        self._DeselectSelect( media_to_deselect, media_to_select )
        
        if move_focus:
            
            if len( self._selected_media ) == 0:
                
                self._SetFocusedMedia( None )
                
            else:
                
                # let's not focus if one of the selectees is already visible
                
                media_visible = True in ( self._MediaIsVisible( media ) for media in self._selected_media )
                
                if not media_visible:
                    
                    for m in self._sorted_media:
                        
                        if m in self._selected_media:
                            
                            ctrl = False
                            shift = False
                            
                            self._HitMedia( m, ctrl, shift )
                            
                            self._ScrollToMedia( m )
                            
                            break
                            
                        
                    
                
            
        
    
    def _SetCollectionsAsAlternate( self ):
        
        collections = self._GetSelectedCollections()
        
        if len( collections ) > 0:
            
            message = 'Are you sure you want to set files in the selected collections as alternates? Each collection will be considered a separate group of alternates.'
            message += '\n' * 2
            message += 'Be careful applying this to large groups--any more than a few dozen files, and the client could hang a long time.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                for collection in collections:
                    
                    media_group = collection.GetFlatMedia()
                    
                    self._SetDuplicates( HC.DUPLICATE_ALTERNATE, media_group = media_group, silent = True )
                    
                
            
        
    
    def _SetDuplicates( self, duplicate_type, media_pairs = None, media_group = None, duplicate_content_merge_options = None, silent = False ):
        
        if duplicate_type == HC.DUPLICATE_POTENTIAL:
            
            yes_no_text = 'queue all possible and valid pair combinations into the duplicate filter'
            
        elif duplicate_content_merge_options is None:
            
            yes_no_text = 'apply "{}"'.format( HC.duplicate_type_string_lookup[ duplicate_type ] )
            
            if duplicate_type in [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ] or ( CG.client_controller.new_options.GetBoolean( 'advanced_mode' ) and duplicate_type == HC.DUPLICATE_ALTERNATE ):
                
                yes_no_text += ' (with default duplicate metadata merge options)'
                
                new_options = CG.client_controller.new_options
                
                duplicate_content_merge_options = new_options.GetDuplicateContentMergeOptions( duplicate_type )
                
            
        else:
            
            yes_no_text = 'apply "{}" (with custom duplicate metadata merge options)'.format( HC.duplicate_type_string_lookup[ duplicate_type ] )
            
        
        file_deletion_reason = 'Deleted from duplicate action on Media Page ({}).'.format( yes_no_text )
        
        if media_pairs is None:
            
            if media_group is None:
                
                flat_media = self._GetSelectedFlatMedia()
                
            else:
                
                flat_media = ClientMedia.FlattenMedia( media_group )
                
            
            num_files_str = HydrusNumbers.ToHumanInt( len( flat_media ) )
            
            if len( flat_media ) < 2:
                
                return False
                
            
            media_results = [ media_singleton.GetMediaResult() for media_singleton in flat_media ]
            
            if duplicate_type in ( HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_POTENTIAL ):
                
                media_result_pairs = list( itertools.combinations( media_results, 2 ) )
                
            else:
                
                media_result_a = media_results[0]
                
                media_result_pairs = [ ( media_result_a, media_result_b ) for media_result_b in media_results if media_result_b != media_result_a ]
                
            
        else:
            
            media_result_pairs = [ ( media_a.GetMediaResult(), media_b.GetMediaResult() ) for ( media_a, media_b ) in media_pairs ]
            
            num_files_str = HydrusNumbers.ToHumanInt( len( self._GetSelectedFlatMedia() ) )
            
        
        if len( media_result_pairs ) == 0:
            
            return False
            
        
        if not silent:
            
            yes_label = 'yes'
            no_label = 'no'
            
            if len( media_result_pairs ) > 1 and duplicate_type in ( HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_ALTERNATE ):
                
                media_result_pairs_str = HydrusNumbers.ToHumanInt( len( media_result_pairs ) )
                
                message = 'Are you sure you want to {} for the {} selected files? The relationship will be applied between every pair combination in the file selection ({} pairs).'.format( yes_no_text, num_files_str, media_result_pairs_str )
                
                if len( media_result_pairs ) > 100:
                    
                    if duplicate_type == HC.DUPLICATE_FALSE_POSITIVE:
                        
                        message = 'False positive records are complicated, and setting that relationship for {} files ({} pairs) at once is likely a mistake.'.format( num_files_str, media_result_pairs_str )
                        message += '\n' * 2
                        message += 'Are you sure all of these files are all potential duplicates and that they are all false positive matches with each other? If not, I recommend you step back for now.'
                        
                        yes_label = 'I know what I am doing'
                        no_label = 'step back for now'
                        
                    elif duplicate_type == HC.DUPLICATE_ALTERNATE:
                        
                        message = 'Are you certain all these {} files are alternates with every other member of the selection, and that none are duplicates?'.format( num_files_str )
                        message += '\n' * 2
                        message += 'If some of them may be duplicates, I recommend you either deselect the possible duplicates and try again, or just leave this group to be processed in the normal duplicate filter.'
                        
                        yes_label = 'they are all alternates'
                        no_label = 'some may be duplicates'
                        
                    
                
            else:
                
                message = 'Are you sure you want to ' + yes_no_text + ' for the {} selected files?'.format( num_files_str )
                
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = yes_label, no_label = no_label )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        pair_info = []
        
        # there's an issue here in that one decision will affect the next. if we say 'copy tags both sides' and say A > B & C, then B's tags, merged with A, should soon merge with C
        # therefore, we need to update the media objects as we go here, which means we need duplicates to force content updates on
        # this is a little hacky, so maybe a big rewrite here would be nice
        
        # There's a second issue, wew, in that in order to propagate C back to B, we need to do the whole thing twice! wow!
        # some service_key_to_content_updates preservation gubbins is needed as a result
        
        hashes_to_duplicated_media_results = {}
        hash_pairs_to_content_update_packages = collections.defaultdict( list )
        
        for is_first_run in ( True, False ):
            
            for ( media_result_a, media_result_b ) in media_result_pairs:
                
                hash_a = media_result_a.GetHash()
                hash_b = media_result_b.GetHash()
                
                if hash_a not in hashes_to_duplicated_media_results:
                    
                    hashes_to_duplicated_media_results[ hash_a ] = media_result_a.Duplicate()
                    
                
                first_duplicated_media_result = hashes_to_duplicated_media_results[ hash_a ]
                
                if hash_b not in hashes_to_duplicated_media_results:
                    
                    hashes_to_duplicated_media_results[ hash_b ] = media_result_b.Duplicate()
                    
                
                second_duplicated_media_result = hashes_to_duplicated_media_results[ hash_b ]
                
                content_update_packages = hash_pairs_to_content_update_packages[ ( hash_a, hash_b ) ]
                
                if duplicate_content_merge_options is not None:
                    
                    do_not_do_deletes = is_first_run
                    
                    # so the important part of this mess is here. we send the duplicated media, which is keeping up with content updates, to the method here
                    # original 'first_media' is not changed, and won't be until the database Write clears and publishes everything
                    content_update_packages.extend( duplicate_content_merge_options.ProcessPairIntoContentUpdatePackages( first_duplicated_media_result, second_duplicated_media_result, file_deletion_reason = file_deletion_reason, do_not_do_deletes = do_not_do_deletes ) )
                    
                
                for content_update_package in content_update_packages:
                    
                    for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
                        
                        for content_update in content_updates:
                            
                            hashes = content_update.GetHashes()
                            
                            if hash_a in hashes:
                                
                                first_duplicated_media_result.ProcessContentUpdate( service_key, content_update )
                                
                            
                            if hash_b in hashes:
                                
                                second_duplicated_media_result.ProcessContentUpdate( service_key, content_update )
                                
                            
                        
                    
                
                if is_first_run:
                    
                    continue
                    
                
                pair_info.append( ( duplicate_type, hash_a, hash_b, content_update_packages ) )
                
            
        
        if len( pair_info ) > 0:
            
            CG.client_controller.WriteSynchronous( 'duplicate_pair_status', pair_info )
            
            return True
            
        
        return False
        
    
    def _SetDuplicatesCustom( self ):
        
        duplicate_types = [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ]
        
        if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            duplicate_types.append( HC.DUPLICATE_ALTERNATE )
            
        
        choice_tuples = [ ( HC.duplicate_type_string_lookup[ duplicate_type ], duplicate_type ) for duplicate_type in duplicate_types ]
        
        try:
            
            duplicate_type = ClientGUIDialogsQuick.SelectFromList( self, 'select duplicate type', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        new_options = CG.client_controller.new_options
        
        duplicate_content_merge_options = new_options.GetDuplicateContentMergeOptions( duplicate_type )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit duplicate merge options' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            ctrl = ClientGUIDuplicatesContentMergeOptions.EditDuplicateContentMergeOptionsWidget( panel, duplicate_type, duplicate_content_merge_options, for_custom_action = True )
            
            panel.SetControl( ctrl )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                duplicate_content_merge_options = ctrl.GetValue()
                
                if duplicate_type == HC.DUPLICATE_BETTER:
                    
                    self._SetDuplicatesFocusedBetter( duplicate_content_merge_options = duplicate_content_merge_options )
                    
                else:
                    
                    self._SetDuplicates( duplicate_type, duplicate_content_merge_options = duplicate_content_merge_options )
                    
                
            
        
    
    def _SetDuplicatesFocusedBetter( self, duplicate_content_merge_options = None ):
        
        if self._HasFocusSingleton():
            
            focused_singleton = self._GetFocusSingleton()
            
            focused_hash = focused_singleton.GetHash()
            
            flat_media = self._GetSelectedFlatMedia()
            
            ( better_media, ) = [ media for media in flat_media if media.GetHash() == focused_hash ]
            
            worse_flat_media = [ media for media in flat_media if media.GetHash() != focused_hash ]
            
            if len( worse_flat_media ) == 0:
                
                message = 'Since you only selected one file, would you rather just set this file as the best file of its group?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result == QW.QDialog.DialogCode.Accepted:
                    
                    self._SetDuplicatesFocusedKing( silent = True )
                    
                
                return
                
            
            media_pairs = [ ( better_media, worse_media ) for worse_media in worse_flat_media ]
            
            message = 'Are you sure you want to set the focused file as better than the {} other files in the selection?'.format( HydrusNumbers.ToHumanInt( len( worse_flat_media ) ) )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._SetDuplicates( HC.DUPLICATE_BETTER, media_pairs = media_pairs, silent = True, duplicate_content_merge_options = duplicate_content_merge_options )
                
            
        else:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'No file is focused, so cannot set the focused file as better!' )
            
            return
            
        
    
    def _SetDuplicatesFocusedKing( self, silent = False ):
        
        if self._HasFocusSingleton():
            
            media = self._GetFocusSingleton()
            
            focused_hash = media.GetHash()
            
            # TODO: when media knows its duplicate gubbins, we can test num dupe files and if it is king already and stuff easier here
            
            do_it = False
            
            if silent:
                
                do_it = True
                
            else:
                
                message = 'Are you sure you want to set the focused file as the best file of its duplicate group?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result == QW.QDialog.DialogCode.Accepted:
                    
                    do_it = True
                    
                
            
            if do_it:
                
                CG.client_controller.WriteSynchronous( 'duplicate_set_king', focused_hash )
                
            
        else:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'No file is focused, so cannot set the focused file as king!' )
            
            return
            
        
    
    def _SetDuplicatesPotential( self ):
        
        media_group = self._GetSelectedFlatMedia()
        
        self._SetDuplicates( HC.DUPLICATE_POTENTIAL, media_group = media_group )
        
    
    def _SetFocusedMedia( self, media, focus_page = False ):
        
        if media == self._focused_media:
            
            return
            
        
        self._next_best_media_if_focuses_removed = None
        
        for m in [ media, self._focused_media ]:
            
            if m is None:
                
                continue
                
            
            if m in self._sorted_media:
                
                next_best_media = m
                
                i = self._sorted_media.index( next_best_media )
                
                while next_best_media in self._selected_media:
                    
                    if i == 0:
                        
                        next_best_media = None
                        
                        break
                        
                    
                    i -= 1
                    
                    next_best_media = self._sorted_media[ i ]
                    
                
                if next_best_media is not None:
                    
                    self._next_best_media_if_focuses_removed = next_best_media
                    
                    break
                    
                
            
        
        publish_media = None
        
        self._focused_media = media
        self._last_hit_media = media
        
        if self._focused_media is not None:
            
            publish_media = self._focused_media.GetDisplayMedia()
            
        
        if publish_media is None:
            
            self.focusMediaCleared.emit()
            
        else:
            
            self.focusMediaChanged.emit( publish_media )
            
        
    
    def _ScrollToMedia( self, media ):
        
        pass
        
    
    def _ShowSelectionInNewPage( self ):
        
        hashes = self._GetSelectedHashes( ordered = True )
        
        if len( hashes ) > 0:
            
            media_sort = self._page_manager.GetVariable( 'media_sort' )
            
            if self._page_manager.HasVariable( 'media_collect' ):
                
                media_collect = self._page_manager.GetVariable( 'media_collect' )
                
            else:
                
                media_collect = ClientMedia.MediaCollect()
                
            
            ClientGUIMediaSimpleActions.ShowFilesInNewPage( hashes, self._location_context, media_sort = media_sort, media_collect = media_collect )
            
        
    
    def _StartShiftSelect( self, media ):
        
        self._shift_select_started_with_this_media = media
        self._media_added_in_current_shift_select = set()
        
    
    def _Undelete( self ):
        
        media = self._GetSelectedFlatMedia()
        
        ClientGUIMediaModalActions.UndeleteMedia( self, media )
        
    
    def _UpdateBackgroundColour( self ):
        
        self.widget().update()
        
    
    def _UploadDirectory( self, file_service_key ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is None or len( hashes ) == 0:
            
            return
            
        
        ipfs_service = CG.client_controller.services_manager.GetService( file_service_key )
        
        try:
            
            message = 'Enter a note to describe this directory.'
            
            note = ClientGUIDialogsQuick.EnterText( self, message )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        CG.client_controller.CallToThread( ipfs_service.PinDirectory, hashes, note )
        
    
    def _UploadFiles( self, file_service_key ):
        
        hashes = self._GetSelectedHashes( is_not_in_file_service_key = file_service_key )
        
        if hashes is not None and len( hashes ) > 0:   
            
            CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( file_service_key, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PEND, hashes ) ) )
            
        
    
    def AddMediaResults( self, page_key, media_results ):
        
        if page_key == self._page_key:
            
            CG.client_controller.pub( 'refresh_page_name', self._page_key )
            
            new_media = ClientMedia.ListeningMediaList.AddMediaResults( self, media_results )
            
            self.newMediaAdded.emit()
            
            hashes = [ m.GetHash() for m in ClientMedia.FlattenMedia( new_media ) ]
            
            self.filesAdded.emit( hashes )
            
            CG.client_controller.pub( 'notify_new_pages_count' )
            
            return new_media
            
        
        return []
        
    
    def CleanBeforeDestroy( self ):
        
        self.Clear()
        
    
    def ClearPageKey( self ):
        
        self._page_key = b'dead media panel page key'
        
    
    def Collect( self, media_collect = None ):
        
        self._Select( ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_NONE ) )
        
        ClientMedia.ListeningMediaList.Collect( self, media_collect = media_collect )
        
        self._RecalculateVirtualSize()
        
        self.Sort()
        
    
    def GetColour( self, colour_type ):
        
        if CG.client_controller.new_options.GetBoolean( 'override_stylesheet_colours' ):
            
            bg_colour = CG.client_controller.new_options.GetColour( colour_type )
            
        else:
            
            bg_colour = self._qss_colours.get( colour_type, QG.QColor( 127, 127, 127 ) )
            
        
        return bg_colour
        
    
    def GetTotalFileSize( self ):
        
        return 0
        
    
    def LaunchMediaViewerOn( self, media ):
        
        self._LaunchMediaViewer( media )
        
    
    def NotifyFocusedMediaFromCanvasExiting( self, media ):
        
        do_activate_window_test = False
        
        if CG.client_controller.new_options.GetBoolean( 'focus_media_tab_on_viewer_close_if_possible' ):
            
            if CG.client_controller.gui.GetPageFromPageKey( self._page_key ) is not None:
                
                CG.client_controller.gui.ShowPage( self._page_key )
                
            
            do_activate_window_test = True
            
        
        if CG.client_controller.new_options.GetBoolean( 'focus_media_thumb_on_viewer_close' ):
            
            self.SetFocusedMedia( media )
            
            do_activate_window_test = True
            
        
        if do_activate_window_test and CG.client_controller.new_options.GetBoolean( 'activate_main_gui_on_focusing_viewer_close' ):
            
            self.activateWindow()
            
        
    
    def PageHidden( self ):
        
        self._vertical_scrollbar_pos_on_hide = self.verticalScrollBar().value()
        
    
    def PageShown( self ):
        
        self._PublishSelectionChange()
        
        if self._vertical_scrollbar_pos_on_hide is not None:
            
            self.verticalScrollBar().setValue( self._vertical_scrollbar_pos_on_hide )
            
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        if command.IsSimpleCommand():
            
            action = command.GetSimpleAction()
            
            if action == CAC.SIMPLE_COPY_FILE_BITMAP:
                
                if not self._HasFocusSingleton():
                    
                    return
                    
                
                focus_singleton = self._GetFocusSingleton()
                
                bitmap_type = command.GetSimpleData()
                
                ClientGUIMediaSimpleActions.CopyMediaBitmap( focus_singleton, bitmap_type )
                
            elif action == CAC.SIMPLE_COPY_FILES:
                
                file_command_target = command.GetSimpleData()
                
                medias = self._GetMediasForFileCommandTarget( file_command_target )
                
                if len( medias ) > 0:
                    
                    ClientGUIMediaSimpleActions.CopyFilesToClipboard( medias )
                    
                
            elif action == CAC.SIMPLE_COPY_FILE_PATHS:
                
                file_command_target = command.GetSimpleData()
                
                medias = self._GetMediasForFileCommandTarget( file_command_target )
                
                if len( medias ) > 0:
                    
                    ClientGUIMediaSimpleActions.CopyFilePathsToClipboard( medias )
                    
                
            elif action == CAC.SIMPLE_COPY_FILE_HASHES:
                
                ( file_command_target, hash_type ) = command.GetSimpleData()
                
                medias = self._GetMediasForFileCommandTarget( file_command_target )
                
                if len( medias ) > 0:
                    
                    ClientGUIMediaModalActions.CopyHashesToClipboard( self, hash_type, medias )
                    
                
            elif action == CAC.SIMPLE_COPY_FILE_SERVICE_FILENAMES:
                
                hacky_ipfs_dict = command.GetSimpleData()
                
                file_command_target = hacky_ipfs_dict[ 'file_command_target' ]
                ipfs_service_key = hacky_ipfs_dict[ 'ipfs_service_key' ]
                
                medias = self._GetMediasForFileCommandTarget( file_command_target )
                
                if len( medias ) > 0:
                    
                    ClientGUIMediaSimpleActions.CopyServiceFilenamesToClipboard( ipfs_service_key, medias )
                    
                
            elif action == CAC.SIMPLE_COPY_FILE_ID:
                
                file_command_target = command.GetSimpleData()
                
                medias = self._GetMediasForFileCommandTarget( file_command_target )
                
                if len( medias ) > 0:
                    
                    ClientGUIMediaSimpleActions.CopyFileIdsToClipboard( medias )
                    
                
            elif action == CAC.SIMPLE_COPY_URLS:
                
                ordered_selected_media = self._GetSelectedMediaOrdered()
                
                if len( ordered_selected_media ) > 0:
                    
                    ClientGUIMediaSimpleActions.CopyMediaURLs( ordered_selected_media )
                    
                
            elif action == CAC.SIMPLE_REARRANGE_THUMBNAILS:
                
                ordered_selected_media = self._GetSelectedMediaOrdered()
                
                ( rearrange_type, rearrange_data ) = command.GetSimpleData()
                
                insertion_index = None
                
                if rearrange_type == CAC.REARRANGE_THUMBNAILS_TYPE_FIXED:
                    
                    insertion_index = rearrange_data
                    
                elif rearrange_type == CAC.REARRANGE_THUMBNAILS_TYPE_COMMAND:
                    
                    rearrange_command = rearrange_data
                    
                    if rearrange_command == CAC.MOVE_HOME:
                        
                        insertion_index = 0
                        
                    elif rearrange_command == CAC.MOVE_END:
                        
                        insertion_index = len( self._sorted_media )
                        
                    else:
                        
                        if len( self._selected_media ) > 0:
                            
                            if rearrange_command in ( CAC.MOVE_LEFT, CAC.MOVE_RIGHT ):
                                
                                ordered_selected_media = self._GetSelectedMediaOrdered()
                                
                                earliest_index = self._sorted_media.index( ordered_selected_media[ 0 ] )
                                
                                if rearrange_command == CAC.MOVE_LEFT:
                                    
                                    if earliest_index > 0:
                                        
                                        insertion_index = earliest_index - 1
                                        
                                    
                                elif rearrange_command == CAC.MOVE_RIGHT:
                                    
                                    insertion_index = earliest_index + 1
                                    
                                
                            elif rearrange_command == CAC.MOVE_TO_FOCUS:
                                
                                if self._focused_media is not None:
                                    
                                    focus_index = self._sorted_media.index( self._focused_media )
                                    
                                    insertion_index = focus_index
                                    
                                
                            
                        
                    
                
                if insertion_index is None:
                    
                    return
                    
                
                self.MoveMedia( ordered_selected_media, insertion_index = insertion_index )
                
            elif action == CAC.SIMPLE_SHOW_DUPLICATES:
                
                if self._HasFocusSingleton():
                    
                    media = self._GetFocusSingleton()
                    
                    hash = media.GetHash()
                    
                    duplicate_type = command.GetSimpleData()
                    
                    ClientGUIMediaSimpleActions.ShowDuplicatesInNewPage( self._location_context, hash, duplicate_type )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_CLEAR_ALL_FOCUSED_FALSE_POSITIVES:
                
                if self._HasFocusSingleton():
                    
                    media = self._GetFocusSingleton()
                    
                    hash = media.GetHash()
                    
                    ClientGUIDuplicateActions.ClearAllFalsePositives( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_CLEAR_ALL_FALSE_POSITIVES:
                
                hashes = self._GetSelectedHashes()
                
                if len( hashes ) > 0:
                    
                    ClientGUIDuplicateActions.ClearAllFalsePositives( self, hashes )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_CLEAR_INTERNAL_FALSE_POSITIVES:
                
                hashes = self._GetSelectedHashes()
                
                if len( hashes ) > 1:
                    
                    ClientGUIDuplicateActions.ClearInternalFalsePositives( self, hashes )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_FOCUSED_ALTERNATE_GROUP:
                
                if self._HasFocusSingleton():
                    
                    media = self._GetFocusSingleton()
                    
                    hash = media.GetHash()
                    
                    ClientGUIDuplicateActions.DissolveAlternateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_ALTERNATE_GROUP:
                
                hashes = self._GetSelectedHashes()
                
                if len( hashes ) > 0:
                    
                    ClientGUIDuplicateActions.DissolveAlternateGroup( self, hashes )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_FOCUSED_DUPLICATE_GROUP:
                
                if self._HasFocusSingleton():
                    
                    media = self._GetFocusSingleton()
                    
                    hash = media.GetHash()
                    
                    ClientGUIDuplicateActions.DissolveDuplicateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_DUPLICATE_GROUP:
                
                hashes = self._GetSelectedHashes()
                
                if len( hashes ) > 0:
                    
                    ClientGUIDuplicateActions.DissolveDuplicateGroup( self, hashes )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_FROM_ALTERNATE_GROUP:
                
                if self._HasFocusSingleton():
                    
                    media = self._GetFocusSingleton()
                    
                    hash = media.GetHash()
                    
                    ClientGUIDuplicateActions.RemoveFromAlternateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_FROM_DUPLICATE_GROUP:
                
                if self._HasFocusSingleton():
                    
                    media = self._GetFocusSingleton()
                    
                    hash = media.GetHash()
                    
                    ClientGUIDuplicateActions.RemoveFromDuplicateGroup( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_RESET_FOCUSED_POTENTIAL_SEARCH:
                
                if self._HasFocusSingleton():
                    
                    media = self._GetFocusSingleton()
                    
                    hash = media.GetHash()
                    
                    ClientGUIDuplicateActions.ResetPotentialSearch( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_RESET_POTENTIAL_SEARCH:
                
                hashes = self._GetSelectedHashes()
                
                if len( hashes ) > 0:
                    
                    ClientGUIDuplicateActions.ResetPotentialSearch( self, hashes )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_POTENTIALS:
                
                if self._HasFocusSingleton():
                    
                    media = self._GetFocusSingleton()
                    
                    hash = media.GetHash()
                    
                    ClientGUIDuplicateActions.RemovePotentials( self, ( hash, ) )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_POTENTIALS:
                
                hashes = self._GetSelectedHashes()
                
                if len( hashes ) > 0:
                    
                    ClientGUIDuplicateActions.RemovePotentials( self, hashes )
                    
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_SET_ALTERNATE:
                
                self._SetDuplicates( HC.DUPLICATE_ALTERNATE )
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_SET_ALTERNATE_COLLECTIONS:
                
                self._SetCollectionsAsAlternate()
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_SET_CUSTOM:
                
                self._SetDuplicatesCustom()
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_SET_FOCUSED_BETTER:
                
                self._SetDuplicatesFocusedBetter()
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_SET_FOCUSED_KING:
                
                self._SetDuplicatesFocusedKing()
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_SET_POTENTIAL:
                
                self._SetDuplicatesPotential()
                
            elif action == CAC.SIMPLE_DUPLICATE_MEDIA_SET_SAME_QUALITY:
                
                self._SetDuplicates( HC.DUPLICATE_SAME_QUALITY )
                
            elif action in ( CAC.SIMPLE_EXPORT_FILES, CAC.SIMPLE_EXPORT_FILES_QUICK_AUTO_EXPORT ):
                
                do_export_and_then_quit = action == CAC.SIMPLE_EXPORT_FILES_QUICK_AUTO_EXPORT
                
                if len( self._selected_media ) > 0:
                    
                    medias = self._GetSelectedMediaOrdered()
                    
                    flat_media = ClientMedia.FlattenMedia( medias )
                    
                    ClientGUIMediaModalActions.ExportFiles( self, flat_media, do_export_and_then_quit = do_export_and_then_quit )
                    
                
            elif action == CAC.SIMPLE_MANAGE_FILE_RATINGS:
                
                self._ManageRatings()
                
            elif action == CAC.SIMPLE_MANAGE_FILE_TAGS:
                
                self._ManageTags()
                
            elif action == CAC.SIMPLE_MANAGE_FILE_URLS:
                
                self._ManageURLs()
                
            elif action == CAC.SIMPLE_MANAGE_FILE_NOTES:
                
                self._ManageNotes()
                
            elif action == CAC.SIMPLE_MANAGE_FILE_TIMESTAMPS:
                
                self._ManageTimestamps()
                
            elif action == CAC.SIMPLE_OPEN_KNOWN_URL:
                
                self._OpenKnownURL()
                
            elif action == CAC.SIMPLE_ARCHIVE_FILE:
                
                self._Archive()
                
            elif action == CAC.SIMPLE_DELETE_FILE:
                
                self._Delete()
                
            elif action == CAC.SIMPLE_UNDELETE_FILE:
                
                self._Undelete()
                
            elif action == CAC.SIMPLE_INBOX_FILE:
                
                self._Inbox()
                
            elif action == CAC.SIMPLE_REMOVE_FILE_FROM_VIEW:
                
                self._Remove( ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_SELECTED ) )
                
            elif action == CAC.SIMPLE_LAUNCH_MEDIA_VIEWER:
                
                self._LaunchMediaViewer()
                
            elif action == CAC.SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM:
                
                if self._HasFocusSingleton():
                    
                    focused_singleton = self._GetFocusSingleton()
                    
                    it_worked = ClientGUIMediaSimpleActions.OpenExternally( focused_singleton )
                    
                    if it_worked:
                        
                        self.focusMediaPaused.emit()
                        
                    
                
            elif action == CAC.SIMPLE_OPEN_FILE_IN_FILE_EXPLORER:
                
                if self._HasFocusSingleton():
                    
                    focused_singleton = self._GetFocusSingleton()
                    
                    it_worked = ClientGUIMediaSimpleActions.OpenFileLocation( focused_singleton )
                    
                    if it_worked:
                        
                        self.focusMediaPaused.emit()
                        
                    
                
            elif action == CAC.SIMPLE_NATIVE_OPEN_FILE_WITH_DIALOG:
                
                if self._HasFocusSingleton():
                    
                    focused_singleton = self._GetFocusSingleton()
                    
                    it_worked = ClientGUIMediaSimpleActions.OpenFileWithDialog( focused_singleton )
                    
                    if it_worked:
                        
                        self.focusMediaPaused.emit()
                        
                    
                
            elif action == CAC.SIMPLE_NATIVE_OPEN_FILE_PROPERTIES:
                
                if self._HasFocusSingleton():
                    
                    focused_singleton = self._GetFocusSingleton()
                    
                    it_worked = ClientGUIMediaSimpleActions.OpenNativeFileProperties( focused_singleton )
                    
                    if it_worked:
                        
                        self.focusMediaPaused.emit()
                        
                    
                
            elif action == CAC.SIMPLE_OPEN_FILE_IN_WEB_BROWSER:
                
                if self._HasFocusSingleton():
                    
                    focused_singleton = self._GetFocusSingleton()
                    
                    it_worked = ClientGUIMediaSimpleActions.OpenInWebBrowser( focused_singleton )
                    
                    if it_worked:
                        
                        self.focusMediaPaused.emit()
                        
                    
                
            elif action == CAC.SIMPLE_OPEN_SELECTION_IN_NEW_PAGE:
                
                self._ShowSelectionInNewPage()
                
            elif action == CAC.SIMPLE_OPEN_SELECTION_IN_NEW_DUPLICATES_FILTER_PAGE:
                
                hashes = self._GetSelectedHashes( ordered = True )
                
                if CG.client_controller.new_options.GetBoolean( 'open_files_to_duplicate_filter_uses_all_my_files' ):
                    
                    location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
                    
                else:
                    
                    location_context = self._location_context
                    
                
                ClientGUIMediaSimpleActions.ShowFilesInNewDuplicatesFilterPage( hashes, location_context )
                
            elif action == CAC.SIMPLE_OPEN_SIMILAR_LOOKING_FILES:
                
                media = self._GetSelectedFlatMedia()
                
                hamming_distance = command.GetSimpleData()
                
                if hamming_distance is None:
                    
                    from hydrus.client.gui.panels import ClientGUIScrolledPanels
                    from hydrus.client.gui.widgets import ClientGUICommon
                    
                    with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'choose distance' ) as dlg:
                        
                        panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
                        
                        #
                        
                        # make a treeview control thing from menu
                        
                        control = ClientGUICommon.BetterSpinBox( panel )
                        
                        control.setSingleStep( 2 )
                        control.setValue( 10 )
                        
                        panel.SetControl( control )
                        
                        dlg.SetPanel( panel )
                        
                        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                            
                            hamming_distance = control.value()
                            
                        else:
                            
                            return
                            
                        
                    
                
                ClientGUIMediaSimpleActions.ShowSimilarFilesInNewPage( media, self._location_context, hamming_distance )
                
            elif action == CAC.SIMPLE_LAUNCH_THE_ARCHIVE_DELETE_FILTER:
                
                self._ArchiveDeleteFilter()
                
            elif action == CAC.SIMPLE_MAC_QUICKLOOK:
                
                self._MacQuicklook()
                
            else:
                
                command_processed = False
                
            
        elif command.IsContentCommand():
            
            command_processed = ClientGUIMediaModalActions.ApplyContentApplicationCommandToMedia( self, command, self._GetSelectedFlatMedia() )
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        ClientMedia.ListeningMediaList.ProcessContentUpdatePackage( self, content_update_package )
        
        we_were_file_or_tag_affected = False
        
        for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
            
            for content_update in content_updates:
                
                hashes = content_update.GetHashes()
                
                if self._HasHashes( hashes ):
                    
                    affected_media = self._GetMedia( hashes )
                    
                    self._RedrawMedia( affected_media )
                    
                    if content_update.GetDataType() in ( HC.CONTENT_TYPE_FILES, HC.CONTENT_TYPE_MAPPINGS ):
                        
                        we_were_file_or_tag_affected = True
                        
                    
                
            
        
        if we_were_file_or_tag_affected:
            
            self._PublishSelectionChange( tags_changed = True )
            
        
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates: dict[ bytes, collections.abc.Collection[ ClientServices.ServiceUpdate ] ] ):
        
        ClientMedia.ListeningMediaList.ProcessServiceUpdates( self, service_keys_to_service_updates )
        
        for ( service_key, service_updates ) in service_keys_to_service_updates.items():
            
            for service_update in service_updates:
                
                ( action, row ) = service_update.ToTuple()
                
                if action in ( HC.SERVICE_UPDATE_DELETE_PENDING, HC.SERVICE_UPDATE_RESET ):
                    
                    self._RecalculateVirtualSize()
                    
                
                self._PublishSelectionChange( tags_changed = True )
                
            
        
    
    def PublishSelectionChange( self ):
        
        self._PublishSelectionChange()
        
    
    def RemoveMedia( self, hashes ):
        
        self._RemoveMediaByHashes( hashes )
        
    
    def SelectByTags( self, page_key, tag_service_key, and_or_or, tags ):
        
        if page_key == self._page_key:
            
            self._Select( ClientMediaFileFilter.FileFilter( ClientMediaFileFilter.FILE_FILTER_TAGS, ( tag_service_key, and_or_or, tags ) ) )
            
            self.setFocus( QC.Qt.FocusReason.OtherFocusReason )
            
        
    
    def SetDuplicateStatusForAll( self, duplicate_type ):
        
        media_group = ClientMedia.FlattenMedia( self._sorted_media )
        
        return self._SetDuplicates( duplicate_type, media_group = media_group )
        
    
    def SetEmptyPageStatusOverride( self, value: str ):
        
        self._empty_page_status_override = value
        
    
    def SetFocusedMedia( self, media ):
        
        pass
        
    
    def get_hmrp_background( self ):
        
        return self._qss_colours[ CC.COLOUR_THUMBGRID_BACKGROUND ]
        
    
    def get_hmrp_thumbnail_local_background_normal( self ):
        
        return self._qss_colours[ CC.COLOUR_THUMB_BACKGROUND ]
        
    
    def get_hmrp_thumbnail_local_background_selected( self ):
        
        return self._qss_colours[ CC.COLOUR_THUMB_BACKGROUND_SELECTED ]
        
    
    def get_hmrp_thumbnail_local_border_normal( self ):
        
        return self._qss_colours[ CC.COLOUR_THUMB_BORDER ]
        
    
    def get_hmrp_thumbnail_local_border_selected( self ):
        
        return self._qss_colours[ CC.COLOUR_THUMB_BORDER_SELECTED ]
        
    
    def get_hmrp_thumbnail_not_local_background_normal( self ):
        
        return self._qss_colours[ CC.COLOUR_THUMB_BACKGROUND_REMOTE ]
        
    
    def get_hmrp_thumbnail_not_local_background_selected( self ):
        
        return self._qss_colours[ CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED ]
        
    
    def get_hmrp_thumbnail_not_local_border_normal( self ):
        
        return self._qss_colours[ CC.COLOUR_THUMB_BORDER_REMOTE ]
        
    
    def get_hmrp_thumbnail_not_local_border_selected( self ):
        
        return self._qss_colours[ CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED ]
        
    
    def set_hmrp_background( self, colour ):
        
        self._qss_colours[ CC.COLOUR_THUMBGRID_BACKGROUND ] = colour
        
    
    def set_hmrp_thumbnail_local_background_normal( self, colour ):
        
        self._qss_colours[ CC.COLOUR_THUMB_BACKGROUND ] = colour
        
    
    def set_hmrp_thumbnail_local_background_selected( self, colour ):
        
        self._qss_colours[ CC.COLOUR_THUMB_BACKGROUND_SELECTED ] = colour
        
    
    def set_hmrp_thumbnail_local_border_normal( self, colour ):
        
        self._qss_colours[ CC.COLOUR_THUMB_BORDER ] = colour
        
    
    def set_hmrp_thumbnail_local_border_selected( self, colour ):
        
        self._qss_colours[ CC.COLOUR_THUMB_BORDER_SELECTED ] = colour
        
    
    def set_hmrp_thumbnail_not_local_background_normal( self, colour ):
        
        self._qss_colours[ CC.COLOUR_THUMB_BACKGROUND_REMOTE ] = colour
        
    
    def set_hmrp_thumbnail_not_local_background_selected( self, colour ):
        
        self._qss_colours[ CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED ] = colour
        
    
    def set_hmrp_thumbnail_not_local_border_normal( self, colour ):
        
        self._qss_colours[ CC.COLOUR_THUMB_BORDER_REMOTE ] = colour
        
    
    def set_hmrp_thumbnail_not_local_border_selected( self, colour ):
        
        self._qss_colours[ CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED ] = colour
        
    
    hmrp_background = QC.Property( QG.QColor, get_hmrp_background, set_hmrp_background )
    hmrp_thumbnail_local_background_normal = QC.Property( QG.QColor, get_hmrp_thumbnail_local_background_normal, set_hmrp_thumbnail_local_background_normal )
    hmrp_thumbnail_local_background_selected = QC.Property( QG.QColor, get_hmrp_thumbnail_local_background_selected, set_hmrp_thumbnail_local_background_selected )
    hmrp_thumbnail_local_border_normal = QC.Property( QG.QColor, get_hmrp_thumbnail_local_border_normal, set_hmrp_thumbnail_local_border_normal )
    hmrp_thumbnail_local_border_selected = QC.Property( QG.QColor, get_hmrp_thumbnail_local_border_selected, set_hmrp_thumbnail_local_border_selected )
    hmrp_thumbnail_not_local_background_normal = QC.Property( QG.QColor, get_hmrp_thumbnail_not_local_background_normal, set_hmrp_thumbnail_not_local_background_normal )
    hmrp_thumbnail_not_local_background_selected = QC.Property( QG.QColor, get_hmrp_thumbnail_not_local_background_selected, set_hmrp_thumbnail_not_local_background_selected )
    hmrp_thumbnail_not_local_border_normal = QC.Property( QG.QColor, get_hmrp_thumbnail_not_local_border_normal, set_hmrp_thumbnail_not_local_border_normal )
    hmrp_thumbnail_not_local_border_selected = QC.Property( QG.QColor, get_hmrp_thumbnail_not_local_border_selected, set_hmrp_thumbnail_not_local_border_selected )
    
    class _InnerWidget( QW.QWidget ):
        
        def __init__( self, parent: "MediaResultsPanel" ):
            
            super().__init__( parent )
            
            self._parent = parent
            
        
        def paintEvent( self, event ):
            
            try:
                
                painter = QG.QPainter( self )
                
                bg_colour = self._parent.GetColour( CC.COLOUR_THUMBGRID_BACKGROUND )
                
                painter.setBackground( QG.QBrush( bg_colour ) )
                
                painter.eraseRect( painter.viewport() )
                
                background_pixmap = CG.client_controller.bitmap_manager.GetMediaBackgroundPixmap()
                
                if background_pixmap is not None:
                    
                    my_size = QP.ScrollAreaVisibleRect( self._parent ).size()
                    
                    pixmap_size = background_pixmap.size()
                    
                    painter.drawPixmap( my_size.width() - pixmap_size.width(), my_size.height() - pixmap_size.height(), background_pixmap )
                    
                
            except Exception as e:
                
                ClientGUIExceptionHandling.HandlePaintEventException( self, e )
                
            
        
    
