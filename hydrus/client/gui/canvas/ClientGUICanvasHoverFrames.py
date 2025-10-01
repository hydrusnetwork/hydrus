import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.duplicates import ClientDuplicatesComparisonStatements
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDragDrop
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIRatings
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvasMedia
from hydrus.client.gui.canvas import ClientGUIMPV
from hydrus.client.gui.duplicates import ClientGUIDuplicatesContentMergeOptions
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.media import ClientGUIMediaModalActions
from hydrus.client.gui.media import ClientGUIMediaControls
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.gui.widgets import ClientGUIPainterShapes
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaResultPrettyInfo
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientRatings

class RatingIncDecCanvas( ClientGUIRatings.RatingIncDec ):

    def __init__( self, parent: "CanvasHoverFrameTopRight", service_key, canvas_key, icon_pad: QC.QSize = None, canvas_type = CC.CANVAS_PREVIEW ):
        
        super().__init__( parent, service_key, canvas_type )
        
        self._canvas_key = canvas_key
        self._canvas_type = canvas_type
        self._current_media = None
        self._panel = parent
        self._rating_state = None
        self._rating = None
        self._iconsize = ClientGUIRatings.GetIconSize( self._canvas_type, HC.LOCAL_RATING_INCDEC )
        self._iconpad = QC.QSize( round( ClientGUIPainterShapes.PAD_PX ), round( ClientGUIPainterShapes.PAD_PX / 2 ) ) if icon_pad is None else icon_pad
        
        self._hashes = set()
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
        CG.client_controller.sub( self, 'NotifyNewOptions', 'notify_new_options' )
        
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self._current_media is not None:
            
            self._iconsize =  ClientGUIRatings.GetIncDecSize( ClientGUIRatings.GetIconSize( self._canvas_type, HC.LOCAL_RATING_INCDEC ).height(), self._rating )
            
            ClientGUIRatings.DrawIncDec( painter, self._iconpad.width(), self._iconpad.height(), self._service_key, self._rating_state, self._rating, self._iconsize )
            
            self.UpdateSize()
            
        
    
    def _SetRating( self, rating ):
        
        super()._SetRating( rating )
        
        if self._current_media is not None and rating is not None:
            
            content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( self._service_key, content_update ) )
            
        
    
    def ClearMedia( self ):
        
        self.SetMedia( None )
        
    
    def NotifyNewOptions( self ):
        
        self._iconsize =  ClientGUIRatings.GetIncDecSize( ClientGUIRatings.GetIconSize( self._canvas_type, HC.LOCAL_RATING_INCDEC ).height(), self._rating )
        
        self._panel.DoRegularHideShow()
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        if self._current_media is not None:
            
            for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
                
                if service_key != self._service_key:
                    
                    continue
                    
                
                for content_update in content_updates:
                    
                    hashes = content_update.GetHashes()
                    
                    if HydrusLists.SetsIntersect( self._hashes, hashes ):
                        
                        ( self._rating_state, self._rating ) = ClientRatings.GetIncDecStateFromMedia( ( self._current_media, ), self._service_key )
                        
                        self.update()
                        
                        self._UpdateTooltip()
                        
                        return
                        
                    
                
            
        
    
    def SetMedia( self, media ):
        
        self._current_media = media
        
        if self._current_media is None:
            
            self._hashes = set()
            
            self._rating_state = None
            self._rating = None
            
        else:
            
            self._hashes = self._current_media.GetHashes()
            
            ( self._rating_state, self._rating ) = ClientRatings.GetIncDecStateFromMedia( ( self._current_media, ), self._service_key )
            
        
        self.update()
        
        self.UpdateSize()
        
        self._UpdateTooltip()    
        
    
    def sizeHint( self ):
        
        pad = ClientGUIPainterShapes.PAD_PX
        
        return QC.QSize( int( self._iconsize.width() + 1 ), int( self._iconsize.height() + pad ) )
        
    

class RatingLikeCanvas( ClientGUIRatings.RatingLike ):
    
    def __init__( self, parent: "CanvasHoverFrameTopRight", service_key, canvas_key, canvas_type ):
        
        super().__init__( parent, service_key, canvas_type )
        
        self._canvas_key = canvas_key
        self._canvas_type = canvas_type
        self._current_media = None
        self._hashes = set()
        self._iconsize = ClientGUIRatings.GetIconSize( self._canvas_type, HC.LOCAL_RATING_LIKE )
        self._panel = parent
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
        
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self._current_media is not None:
            
            icon_size = ClientGUIRatings.GetIconSize( self._canvas_type, HC.LOCAL_RATING_LIKE )
            
            ClientGUIRatings.DrawLike( painter, round( ClientGUIPainterShapes.PAD_PX / 2 ), round( ClientGUIPainterShapes.PAD_PX / 2 ), self._service_key, self._rating_state, icon_size )
            
            if self._iconsize != icon_size:
                
                self._iconsize = icon_size
                self.UpdateSize()
                
                self._panel.hide()
                self._panel.DoRegularHideShow()
                
            
        
    
    def _SetRatingFromCurrentMedia( self ):
        
        if self._current_media is None:
            
            rating_state = ClientRatings.NULL
            
        else:
            
            rating_state = ClientRatings.GetLikeStateFromMedia( ( self._current_media, ), self._service_key )
            
        
        self._SetRating( rating_state )
        
    
    def ClearMedia( self ):
        
        self.SetMedia( None )
        
    
    def EventLeftDown( self, event ):
        
        if self._current_media is not None:
            
            if self._rating_state == ClientRatings.LIKE: rating = None
            else: rating = 1
            
            content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( self._service_key, content_update ) )
            
        
    
    def EventRightDown( self, event ):
        
        if self._current_media is not None:
            
            if self._rating_state == ClientRatings.DISLIKE: rating = None
            else: rating = 0
            
            content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( self._service_key, content_update ) )
            
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        if self._current_media is not None:
            
            for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
                
                if service_key != self._service_key:
                    
                    continue
                    
                
                for content_update in content_updates:
                    
                    hashes = content_update.GetHashes()
                    
                    if HydrusLists.SetsIntersect( self._hashes, hashes ):
                        
                        self._SetRatingFromCurrentMedia()
                        
                        self.update()
                        
                        return
                        
                    
                
            
        
    
    def SetMedia( self, media ):
        
        self._current_media = media
        
        if self._current_media is None:
            
            self._hashes = set()
            
        else:
            
            self._hashes = self._current_media.GetHashes()
            
        
        self._SetRatingFromCurrentMedia()
        
        self.update()
        
    

class RatingNumericalCanvas( ClientGUIRatings.RatingNumericalControl ):

    def __init__( self, parent: "CanvasHoverFrameTopRight", service_key, canvas_key, canvas_type = CC.CANVAS_PREVIEW ):
        
        super().__init__( parent, service_key, canvas_type )
        
        self._canvas_key = canvas_key
        self._canvas_type = canvas_type
        self._current_media = None
        self._panel = parent
        self._rating_state = None
        self._rating = None
        self._iconsize = ClientGUIRatings.GetIconSize( self._canvas_type, HC.LOCAL_RATING_NUMERICAL )
        
        self._hashes = set()
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
        
        self.valueChanged.connect( self.UpdateSize )
        
    
    def _ClearRating( self ):
        
        super()._ClearRating()
        
        if self._current_media is not None:
            
            rating = None
            
            content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( self._service_key, content_update ) )
            
        
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self._current_media is not None:
            
            icon_size = ClientGUIRatings.GetIconSize( self._canvas_type, HC.LOCAL_RATING_NUMERICAL )
            
            ClientGUIRatings.DrawNumerical( painter, round( ClientGUIPainterShapes.PAD_PX / 2 ), round( ClientGUIPainterShapes.PAD_PX / 2 ), self._service_key, self._rating_state, self._rating, size = icon_size )
            
            if self._iconsize != icon_size:
                
                self._iconsize = icon_size
                self.UpdateSize()
                
                self._panel.hide()
                self._panel.DoRegularHideShow()
                
            
        
    
    def _SetRating( self, rating ):
        
        super()._SetRating( rating )
        
        if self._current_media is not None and rating is not None:
            
            content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( self._service_key, content_update ) )
            
        
    
    def ClearMedia( self ):
        
        self.SetMedia( None )
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        if self._current_media is not None:
            
            for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
                
                if service_key != self._service_key:
                    
                    continue
                    
                
                for content_update in content_updates:
                    
                    hashes = content_update.GetHashes()
                    
                    if HydrusLists.SetsIntersect( self._hashes, hashes ):
                        
                        ( self._rating_state, self._rating ) = ClientRatings.GetNumericalStateFromMedia( ( self._current_media, ), self._service_key )
                        
                        self.update()
                        
                        self._UpdateTooltip()
                        
                        return
                        
                    
                
            
        
    
    def SetMedia( self, media ):
        
        self._current_media = media
        
        if self._current_media is None:
            
            self._hashes = set()
            
        else:
            
            self._hashes = self._current_media.GetHashes()
            
            ( self._rating_state, self._rating ) = ClientRatings.GetNumericalStateFromMedia( ( self._current_media, ), self._service_key )
            
        
        self.UpdateSize()
        
        self.update()
        
        self._UpdateTooltip()
        
    

# Note that I go setFocusPolicy( QC.Qt.FocusPolicy.TabFocus ) on all the icon buttons in the hover windows
# this means that a user can click a button and not give it focus, allowing the arrow keys and space to still propagate up to the main canvas

TOP_HOVER_PROPORTION = 0.6
SIDE_HOVER_PROPORTIONS = ( 1 - TOP_HOVER_PROPORTION ) / 2

class CanvasHoverFrame( QW.QFrame ):
    
    hoverResizedOrMoved = QC.Signal()
    
    sendApplicationCommand = QC.Signal( CAC.ApplicationCommand )
    
    mediaCleared = QC.Signal()
    mediaChanged = QC.Signal( ClientMedia.MediaSingleton )
    
    def __init__( self, parent: QW.QWidget, my_canvas, canvas_key ):
        
        # TODO: Clean up old references to window stuff, decide on lower/hide/show/raise options
        # OK, so I converted these from this "self.setWindowFlags( QC.Qt.WindowType.FramelessWindowHint | QC.Qt.Tool )" to normal raise/lower widgets embedded in the canvas
        # this took some hacks, and there is still a bunch of focus and TLW checking code going on here that needs to be cleaned up
        # note I tried to have them just lower rather than hide and it looked really stupid, so that thought is dead for the current moment. atm I just want to do the same thing as before with no graphics errors
        
        super().__init__( parent )
        
        self.setFrameStyle( QW.QFrame.Shape.Panel | QW.QFrame.Shadow.Raised )
        self.setLineWidth( 2 )
        
        # We need this, or else if the QSS does not define a Widget background color (the default), these 'raised' windows are transparent lmao
        self.setAutoFillBackground( True )
        
        self._my_canvas = my_canvas
        self._canvas_key = canvas_key
        self._current_media = None
        
        self._hover_panels_that_can_be_on_top_of_us = []
        
        self._always_on_top = False
        
        self._last_ideal_position = None
        
        self.hide()
        self._is_currently_up = False
        
        self.setCursor( QG.QCursor( QC.Qt.CursorShape.ArrowCursor ) )
        
        self._position_initialised_since_last_media = False
        
        parent.installEventFilter( self )
        
    
    def _GetIdealSizeAndPosition( self ):
        
        raise NotImplementedError()
        
    
    def _LowerHover( self ):
        
        if self._is_currently_up:
            
            if HG.hover_window_report_mode:
                
                HydrusData.ShowText( repr( self ) + ' - lowering' )
                
            
            self.hide()
            
            self._is_currently_up = False
            
            self.parentWidget().setFocus( QC.Qt.FocusReason.OtherFocusReason )
            
        
    
    def _MouseOverImportantDescendant( self ):
        
        return False
        
    
    def _RaiseHover( self ):
        
        if not self._is_currently_up :
            
            if HG.hover_window_report_mode:
                
                HydrusData.ShowText( repr( self ) + ' - raising' )
                
            
            self.show()
            self.raise_()
            
            self._is_currently_up = True
            
        
    
    def _ShouldBeHidden( self ):
        
        return self._current_media is None
        
    
    def _ShouldBeShown( self ):
        
        return self._always_on_top
        
    
    def _SizeAndPosition( self ):
        
        # hey the parentwidget here is the media viewer! or sometimes it is the preview window
        if self.parentWidget().isVisible():
            
            ( should_resize, my_ideal_size, my_ideal_position ) = self._GetIdealSizeAndPosition()
            
            if should_resize:
                
                self.resize( my_ideal_size )
                
            
            should_move = my_ideal_position != self.pos()
            
            if should_move:
                
                self.move( my_ideal_position )
                
            
            self._position_initialised_since_last_media = True
            
            if should_resize or should_move:
                
                self.hoverResizedOrMoved.emit()
                
            
            if self._my_canvas.GetCanvasType() == CC.CANVAS_PREVIEW:
                
                self.adjustSize()
                
            
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type()  in ( QC.QEvent.Type.Resize, QC.QEvent.Type.Move, QC.QEvent.Type.Show, QC.QEvent.Type.Hide ):
                
                self._SizeAndPosition()
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
    def mouseReleaseEvent( self, event ):
        
        # we eat mouse events to stop interfering with archive/delete and duplicate filter on greyspace clicks
        
        event.accept()
        
    
    def mousePressEvent( self, event ):
        
        # we eat mouse events to stop interfering with archive/delete and duplicate filter on greyspace clicks
        
        event.accept()
        
    
    def AddHoverThatCanBeOnTop( self, win: "CanvasHoverFrame" ):
        
        self._hover_panels_that_can_be_on_top_of_us.append( win )
        
    
    def ClearMedia( self ):
        
        self.SetMedia( None )
        
    
    def DoRegularHideShow( self ):
        
        if not self.parentWidget().isVisible():
            
            return
            
        
        if not self._position_initialised_since_last_media:
            
            self._SizeAndPosition()
            
        
        current_focus_tlw = QW.QApplication.activeWindow()
        
        focus_is_good = current_focus_tlw == self.window()
        
        if self._ShouldBeShown():
            
            self._RaiseHover()
            
            return
            
        
        if self._ShouldBeHidden():
            
            self._LowerHover()
            
            return
            
        
        mouse_pos = self.parentWidget().mapFromGlobal( QG.QCursor.pos() )
        
        mouse_x = mouse_pos.x()
        mouse_y = mouse_pos.y()
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        my_pos = self.pos()
        
        my_x = my_pos.x()
        my_y = my_pos.y()
        
        ( should_resize, my_ideal_size, my_ideal_pos ) = self._GetIdealSizeAndPosition()
        
        my_ideal_width = my_ideal_size.width()
        my_ideal_height = my_ideal_size.height()
        #print(f'ideal size: {my_ideal_size}, ideal pos: {my_ideal_pos}')
        my_ideal_x = my_ideal_pos.x()
        my_ideal_y = my_ideal_pos.y()
        
        if my_ideal_width == -1:
            
            my_ideal_width = max( my_width, 50 )
            
        
        if my_ideal_height == -1:
            
            my_ideal_height = max( my_height, 50 )
            
        
        ideal_rect = QC.QRect( my_ideal_x, my_ideal_y, my_ideal_width, my_ideal_height )
        
        # we used to test for 'contains' on both the ideal and actual, to compensate for some Linux window managers that would be upset about a (taskbarless top level) hover window appearing and make the taskbar jitter, altering layout state
        # but we no longer have top level hover windows!! begone!
        in_position = ideal_rect.contains( mouse_pos )
        
        menu_open = CGC.core().MenuIsOpen()
        
        mouse_over_important_descendant = self._MouseOverImportantDescendant()
        
        mouse_is_near_animation_bar = self._my_canvas.MouseIsNearAnimationBar()
        
        mouse_is_over_something_else_important = mouse_is_near_animation_bar
        
        mouse_is_over_a_dominant_hover = False
        
        for win in self._hover_panels_that_can_be_on_top_of_us:
            
            if win.geometry().contains( mouse_pos ):
                
                mouse_is_over_a_dominant_hover = True
                
            
        
        hide_focus_is_good = focus_is_good or current_focus_tlw is None # don't hide if focus is either gone to another problem or temporarily sperging-out due to a click-transition or similar
        
        ready_to_show = not self._is_currently_up and in_position and not mouse_is_over_something_else_important and focus_is_good and not menu_open and not mouse_is_over_a_dominant_hover
        ready_to_hide = self._is_currently_up and not menu_open and not mouse_over_important_descendant and ( not in_position or not hide_focus_is_good or mouse_is_over_a_dominant_hover )
        
        def get_logic_report_string():
            
            tuples = []
            
            tuples.append( ( 'mouse: ', ( mouse_x, mouse_y ) ) )
            tuples.append( ( 'winpos: ', ( my_x, my_y ) ) )
            tuples.append( ( 'ideal winpos: ', ( my_ideal_x, my_ideal_y ) ) )
            tuples.append( ( 'winsize: ', ( my_width, my_height ) ) )
            tuples.append( ( 'ideal winsize: ', ( my_ideal_width, my_ideal_height ) ) )
            tuples.append( ( 'in position: ', in_position ) )
            tuples.append( ( 'menu open: ', menu_open ) )
            tuples.append( ( 'mouse near animation bar: ', mouse_is_near_animation_bar ) )
            tuples.append( ( 'focus is good: ', focus_is_good ) )
            tuples.append( ( 'current focus tlw: ', current_focus_tlw ) )
            
            message = '\n' * 2 + '\n'.join( ( a + str( b ) for ( a, b ) in tuples ) )
            
            return message
            
        
        if ready_to_show:
            
            if HG.hover_window_report_mode:
                
                HydrusData.ShowText( 'showing' )
                
                h1 = get_logic_report_string()
                HydrusData.ShowText( h1 )
                
            
            self._SizeAndPosition()
            
            if HG.hover_window_report_mode:
                
                h2 = get_logic_report_string()
                
                if h1 == h2:
                    
                    HydrusData.ShowText( 'no change' )
                    
                else:
                    
                    HydrusData.ShowText( h2 )
                    
                
            
            self._RaiseHover()
            
        elif ready_to_hide:
            
            if HG.hover_window_report_mode:
                
                HydrusData.ShowText( 'hiding' )
                HydrusData.ShowText( get_logic_report_string() )
                
            
            self._LowerHover()
            
        
    
    def PositionInitialisedSinceLastMedia( self ):
        
        return self._position_initialised_since_last_media
        
    
    def SetMedia( self, media ):
        
        self._current_media = media
        
        self._position_initialised_since_last_media = False
        
        if self._current_media is None:
            
            self.mediaCleared.emit()
            
        elif isinstance( self._current_media, ClientMedia.MediaSingleton ): # just to be safe on the delicate type def requirements here
            
            self.mediaChanged.emit( self._current_media )
            
        
    

class CanvasHoverFrameTop( CanvasHoverFrame ):
    
    def __init__( self, parent, my_canvas, canvas_key ):
        
        super().__init__( parent, my_canvas, canvas_key )
        
        self._current_zoom_type = ClientGUICanvasMedia.MEDIA_VIEWER_ZOOM_TYPE_DEFAULT_FOR_FILETYPE
        self._current_zoom = 1.0
        self._current_index_string = ''
        
        self._top_left_hbox = QP.HBoxLayout()
        self._top_center_hbox = QP.HBoxLayout()
        self._top_right_hbox = QP.HBoxLayout()
        self._top_hbox = QP.HBoxLayout()
        
        self._top_right_hbox.addStretch( 1 )
        
        self._title_text = ClientGUICommon.BetterStaticText( self, 'title', ellipsize_end = True )
        self._info_text = ClientGUICommon.BetterStaticText( self, 'info', ellipsize_end = True )
        
        self._title_text.setAlignment( QC.Qt.AlignmentFlag.AlignHCenter | QC.Qt.AlignmentFlag.AlignVCenter )
        self._info_text.setAlignment( QC.Qt.AlignmentFlag.AlignHCenter | QC.Qt.AlignmentFlag.AlignVCenter )
        
        self._PopulateLeftButtons()
        self._PopulateCenterButtons()
        self._PopulateRightButtons()
        
        self._top_left_hbox.addStretch( 1 )
        
        QP.AddToLayout( self._top_hbox, self._top_left_hbox, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( self._top_hbox, self._top_center_hbox, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_hbox, self._top_right_hbox, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._top_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._title_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._info_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        self._window_always_on_top = False #can set this with a global option if you want

        self._window_show_title_bar = True #should always start on
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
        CG.client_controller.sub( self, 'SetIndexString', 'canvas_new_index_string' )
        
    
    def _Archive( self ):
        
        if self._current_media.HasInbox():
            
            command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_FILE )
            
        else:
            
            command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_INBOX_FILE )
            
        
        self.sendApplicationCommand.emit( command )
        
    
    def _GetIdealSizeAndPosition( self ):
        
        # clip this and friends to availableScreenGeometry for size and position, not rely 100% on parent
        
        parent_window = self.parentWidget().window()
        
        parent_size = parent_window.size()
        
        parent_width = parent_size.width()
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        my_ideal_width = int( parent_width * TOP_HOVER_PROPORTION )
        
        my_ideal_height = self.sizeHint().height()
        
        should_resize = my_ideal_width != my_width or my_ideal_height != my_height
        
        ideal_size = QC.QSize( my_ideal_width, my_ideal_height )
        ideal_position = QC.QPoint( int( parent_width * SIDE_HOVER_PROPORTIONS ), 0 )
        
        return ( should_resize, ideal_size, ideal_position )
        
    
    def _MouseOverImportantDescendant( self ):
        
        if not self._volume_control.isHidden():
            
            return self._volume_control.PopupIsVisible()
            
        
        return False
        
    
    def _PopulateCenterButtons( self ):
        
        self._archive_button = ClientGUICommon.IconButton( self, CC.global_icons().archive, self._Archive )
        self._archive_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        self._trash_button = ClientGUICommon.IconButton( self, CC.global_icons().delete, CG.client_controller.pub, 'canvas_delete', self._canvas_key )
        self._trash_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'send to trash' ) )
        self._trash_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        self._delete_button = ClientGUICommon.IconButton( self, CC.global_icons().trash_delete, CG.client_controller.pub, 'canvas_delete', self._canvas_key )
        self._delete_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'delete completely' ) )
        self._delete_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        self._undelete_button = ClientGUICommon.IconButton( self, CC.global_icons().undelete, CG.client_controller.pub, 'canvas_undelete', self._canvas_key )
        self._undelete_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'undelete' ) )
        self._undelete_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        self._show_embedded_metadata_button = ClientGUICommon.IconButton( self, CC.global_icons().page_with_text, self._ShowFileEmbeddedMetadata )
        self._show_embedded_metadata_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        QP.AddToLayout( self._top_center_hbox, self._archive_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_center_hbox, self._trash_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_center_hbox, self._delete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_center_hbox, self._undelete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_center_hbox, self._show_embedded_metadata_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
    def _PopulateLeftButtons( self ):
        
        self._index_text = ClientGUICommon.BetterStaticText( self, 'index' )
        
        QP.AddToLayout( self._top_left_hbox, self._index_text, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
    def _PopulateRightButtons( self ):
        
        self._zoom_text = ClientGUICommon.BetterStaticText( self, 'zoom' )
        
        zoom_in = ClientGUICommon.IconButton( self, CC.global_icons().zoom_in, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ZOOM_IN_VIEWER_CENTER ) )
        zoom_in.SetToolTipWithShortcuts( 'zoom in', CAC.SIMPLE_ZOOM_IN )
        zoom_in.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        zoom_out = ClientGUICommon.IconButton( self, CC.global_icons().zoom_out, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ZOOM_OUT_VIEWER_CENTER ) )
        zoom_out.SetToolTipWithShortcuts( 'zoom out', CAC.SIMPLE_ZOOM_OUT )
        zoom_out.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        zoom_switch = ClientGUICommon.IconButton( self, CC.global_icons().zoom_switch, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM_VIEWER_CENTER ) )
        zoom_switch.SetToolTipWithShortcuts( 'zoom switch', CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM )
        #zoom_switch = ClientGUICommon.IconButton( self, CC.global_icons().zoom_switch, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_FIT_AND_FILL_ZOOM_VIEWER_CENTER ) )
        #zoom_switch.SetToolTipWithShortcuts( 'zoom switch3', CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_FIT_AND_FILL_ZOOM_VIEWER_CENTER )
        zoom_switch.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        zoom_options = ClientGUICommon.IconButton( self, CC.global_icons().zoom_cog, self._ShowZoomOptionsMenu )
        zoom_options.setToolTip( ClientGUIFunctions.WrapToolTip( 'advanced zoom' ) )
        zoom_options.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        self._volume_control = ClientGUIMediaControls.VolumeControl( self, CC.CANVAS_MEDIA_VIEWER )
        
        if not ClientGUIMPV.MPV_IS_AVAILABLE:
            
            self._volume_control.hide()
            
        
        shortcuts = ClientGUICommon.IconButton( self, CC.global_icons().keyboard, self._ShowShortcutMenu )
        shortcuts.setToolTip( ClientGUIFunctions.WrapToolTip( 'shortcuts' ) )
        shortcuts.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        view_options = ClientGUICommon.IconButton( self, CC.global_icons().eye, self._ShowViewOptionsMenu )
        view_options.setToolTip( ClientGUIFunctions.WrapToolTip( 'view options' ) )
        view_options.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        window_drag_button = ClientGUICommon.WindowDragButton( self, CC.global_icons().move, self._ShowWindowResizeOptionsMenu, self.parentWidget().window() )
        window_drag_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'click and drag from here to move the window' ) )
        window_drag_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        fullscreen_switch = ClientGUICommon.IconButton( self, CC.global_icons().fullscreen_switch, CG.client_controller.pub, 'canvas_fullscreen_switch', self._canvas_key )
        fullscreen_switch.setToolTip( ClientGUIFunctions.WrapToolTip( 'fullscreen switch' ) )
        fullscreen_switch.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        if HC.PLATFORM_MACOS:
            
            fullscreen_switch.hide()
            
        
        open_externally = ClientGUICommon.IconButton( self, CC.global_icons().open_externally, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM ) )
        open_externally.SetToolTipWithShortcuts( 'open externally', CAC.SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM )
        open_externally.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        right_click_call = HydrusData.Call( self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_FOCUS_TAB_AND_MEDIA ) )
        
        drag_button = ClientGUICommon.IconButtonMultiClickable( self, CC.global_icons().drag, self.DragButtonHit, right_click_call )
        drag_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'drag from here to export file' ) )
        drag_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        close = ClientGUICommon.IconButton( self, CC.global_icons().stop, CG.client_controller.pub, 'canvas_close', self._canvas_key )
        close.setToolTip( ClientGUIFunctions.WrapToolTip( 'close' ) )
        close.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        QP.AddToLayout( self._top_right_hbox, self._zoom_text, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_right_hbox, zoom_in, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_right_hbox, zoom_out, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_right_hbox, zoom_switch, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_right_hbox, zoom_options, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_right_hbox, self._volume_control, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_right_hbox, shortcuts, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_right_hbox, view_options, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_right_hbox, window_drag_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_right_hbox, fullscreen_switch, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_right_hbox, open_externally, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_right_hbox, drag_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_right_hbox, close, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
    def _ResetArchiveButton( self ):
        
        if self._current_media.HasInbox():
            
            self._archive_button.SetIconSmart( CC.global_icons().archive )
            self._archive_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'archive' ) )
            
        else:
            
            self._archive_button.SetIconSmart( CC.global_icons().to_inbox )
            
            self._archive_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'return to inbox' ) )
            
        
    
    def _ResetButtons( self ):
        
        if self._current_media is not None:
            
            self._ResetArchiveButton()
            
            locations_manager = self._current_media.GetLocationsManager()
            
            if locations_manager.IsTrashed():
                
                self._trash_button.hide()
                self._delete_button.show()
                
            elif locations_manager.IsLocal():
                
                self._trash_button.show()
                self._delete_button.hide()
                
            
            if set( locations_manager.GetDeleted() ).isdisjoint( CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) ) ):
                
                self._undelete_button.hide()
                
            else:
                
                self._undelete_button.show()
                
            
            has_exif = self._current_media.GetMediaResult().GetFileInfoManager().has_exif
            has_human_readable_embedded_metadata = self._current_media.GetMediaResult().GetFileInfoManager().has_human_readable_embedded_metadata
            has_extra_rows = self._current_media.GetMime() == HC.IMAGE_JPEG
            
            tt = 'show detailed file metadata'
            
            tt_components = []
            
            if has_exif:
                
                tt_components.append( 'exif' )
                
            
            if has_human_readable_embedded_metadata:
                
                tt_components.append( 'non-exif embedded metadata' )
                
            
            if has_extra_rows:
                
                tt_components.append( 'extra info' )
                
            
            if len( tt_components ) > 0:
                
                tt += ', including {}'.format( ' and '.join( tt_components ) )
                
            
            self._show_embedded_metadata_button.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
            
        
    
    def _ResetText( self ):
        
        if self._current_media is None:
            
            self._title_text.hide()
            self._info_text.hide()
            
        else:
            
            label = self._current_media.GetTitleString()
            
            if len( label ) > 0:
                
                self._title_text.setText( label )
                
                self._title_text.show()
                
            else:
                
                self._title_text.hide()
                
            
            lines = ClientMediaResultPrettyInfo.GetPrettyMediaResultInfoLines( self._current_media.GetMediaResult(), only_interesting_lines = True )
            
            lines = [ line for line in lines if not line.IsSubmenu() ]
            
            texts = [ line.text for line in lines ]
            
            info_string = ' | '.join( texts )
            
            self._info_text.setText( info_string )
            
            texts = [ line.tooltip for line in lines ]
            
            info_string = ' | '.join( texts )
            
            self._info_text.setToolTip( info_string )
            
            self._info_text.show()
            
        
    
    def _FlipActiveDefaultCustomShortcut( self, name ):
        
        new_options = CG.client_controller.new_options
        
        default_media_viewer_custom_shortcuts = list( new_options.GetStringList( 'default_media_viewer_custom_shortcuts' ) )
        
        if name in default_media_viewer_custom_shortcuts:
            
            default_media_viewer_custom_shortcuts.remove( name )
            
        else:
            
            default_media_viewer_custom_shortcuts.append( name )
            
            default_media_viewer_custom_shortcuts.sort()
            
        
        new_options.SetStringList( 'default_media_viewer_custom_shortcuts', default_media_viewer_custom_shortcuts )
        
    
    def _ShowFileEmbeddedMetadata( self ):
        
        if self._current_media is None:
            
            return
            
        
        ClientGUIMediaModalActions.ShowFileEmbeddedMetadata( self, self._current_media )
        
    
    def _ShowShortcutMenu( self ):
        
        all_shortcut_names = CG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET )
        
        custom_shortcuts_names = [ name for name in all_shortcut_names if name not in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES ]
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        from hydrus.client.gui.panels import ClientGUIManageOptionsPanel
        
        ClientGUIMenus.AppendMenuItem( menu, 'edit shortcuts', 'edit your sets of shortcuts, and change what shortcuts are currently active on this media viewer', ClientGUIManageOptionsPanel.ManageShortcuts, self )
        
        if len( custom_shortcuts_names ) > 0:
            
            my_canvas_active_custom_shortcuts = self._my_canvas.GetActiveCustomShortcutNames()
            default_media_viewer_custom_shortcuts = CG.client_controller.new_options.GetStringList( 'default_media_viewer_custom_shortcuts' )
            
            current_menu = ClientGUIMenus.GenerateMenu( menu )
            
            for name in custom_shortcuts_names:
                
                ClientGUIMenus.AppendMenuCheckItem( current_menu, name, 'turn this shortcut set on/off', name in my_canvas_active_custom_shortcuts, self._my_canvas.FlipActiveCustomShortcutName, name )
                
            
            ClientGUIMenus.AppendMenu( menu, current_menu, 'set current shortcuts' )
            
            defaults_menu = ClientGUIMenus.GenerateMenu( menu )
            
            for name in custom_shortcuts_names:
                
                ClientGUIMenus.AppendMenuCheckItem( defaults_menu, name, 'turn this shortcut set on/off by default', name in default_media_viewer_custom_shortcuts, self._FlipActiveDefaultCustomShortcut, name )
                
            
            ClientGUIMenus.AppendMenu( menu, defaults_menu, 'set default shortcuts' )
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _ShowViewOptionsMenu( self ):
        
        def flip_background_boolean( name ):
            
            new_options.FlipBoolean( name )
            
            self.update()
            
        
        def flip_show_window_title_bar():
            
            window_real_geom = self.window().geometry()
            
            self._window_show_title_bar = not self._window_show_title_bar
            
            self.window().setWindowFlag( QC.Qt.WindowType.FramelessWindowHint, not self._window_show_title_bar )
            
            self.window().setGeometry( window_real_geom )

            self.window().show()
            self.update()


        def flip_always_on_top():

            self._window_always_on_top = not self._window_always_on_top
            
            self.parentWidget().window().setWindowFlag( QC.Qt.WindowType.WindowStaysOnTopHint, self._window_always_on_top )
            self.window().setWindowFlag( QC.Qt.WindowType.WindowStaysOnTopHint, self._window_always_on_top )

            self.parentWidget().window().show()
            self.window().show()

            self.update()
        
        new_options = CG.client_controller.new_options
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        ClientGUIMenus.AppendMenuCheckItem( menu, 'always on top', 'Toggle whether this window is always on top.', self._window_always_on_top, flip_always_on_top )
        ClientGUIMenus.AppendMenuCheckItem( menu, 'show titlebar', 'Toggle the OS frame of this window.', self._window_show_title_bar, flip_show_window_title_bar )

        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuCheckItem( menu, 'draw tags hover-window text in the background', 'Draw a copy of the respective hover window\'s text in the background of the media viewer canvas.', new_options.GetBoolean( 'draw_tags_hover_in_media_viewer_background' ), flip_background_boolean, 'draw_tags_hover_in_media_viewer_background' )
        ClientGUIMenus.AppendMenuCheckItem( menu, 'draw top hover-window text in the background', 'Draw a copy of the respective hover window\'s text in the background of the media viewer canvas.', new_options.GetBoolean( 'draw_top_hover_in_media_viewer_background' ), flip_background_boolean, 'draw_top_hover_in_media_viewer_background' )
        ClientGUIMenus.AppendMenuCheckItem( menu, 'draw top-right hover-window text in the background', 'Draw a copy of the respective hover window\'s text in the background of the media viewer canvas.', new_options.GetBoolean( 'draw_top_right_hover_in_media_viewer_background' ), flip_background_boolean, 'draw_top_right_hover_in_media_viewer_background' )
        ClientGUIMenus.AppendMenuCheckItem( menu, 'draw notes hover-window text in the background', 'Draw a copy of the respective hover window\'s text in the background of the media viewer canvas.', new_options.GetBoolean( 'draw_notes_hover_in_media_viewer_background' ), flip_background_boolean, 'draw_notes_hover_in_media_viewer_background' )
        ClientGUIMenus.AppendMenuCheckItem( menu, 'draw bottom-right index text in the background', 'Draw a copy of the respective hover window\'s text in the background of the media viewer canvas.', new_options.GetBoolean( 'draw_bottom_right_index_in_media_viewer_background' ), flip_background_boolean, 'draw_bottom_right_index_in_media_viewer_background' )

        ClientGUIMenus.AppendSeparator( menu )

        ClientGUIMenus.AppendMenuCheckItem( menu, 'do not pop-in tags hover-window on mouseover', 'Disable hovering the tags window.', new_options.GetBoolean( 'disable_tags_hover_in_media_viewer' ), flip_background_boolean, 'disable_tags_hover_in_media_viewer' )
        ClientGUIMenus.AppendMenuCheckItem( menu, 'do not pop-in top-right hover-window on mouseover', 'Disable hovering the ratings/notes window.', new_options.GetBoolean( 'disable_top_right_hover_in_media_viewer' ), flip_background_boolean, 'disable_top_right_hover_in_media_viewer' )

        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuCheckItem( menu, 'apply image ICC Profile colour adjustments', 'Set whether images with ICC Profiles should have them applied. This may be useful to flip back and forth if you are in the duplicate filter.', new_options.GetBoolean( 'do_icc_profile_normalisation' ), self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_FLIP_ICC_PROFILE_APPLICATION ) )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _ShowZoomOptionsMenu( self ):
        
        def flip_background_boolean( name ):
            
            new_options.FlipBoolean( name )
            
            mutually_exclusive_guys = ( 'media_viewer_lock_current_zoom', 'media_viewer_lock_current_zoom_type' )
            
            for ( a, b ) in ( mutually_exclusive_guys, mutually_exclusive_guys[::-1] ):
                
                if name == a and new_options.GetBoolean( a ) and new_options.GetBoolean( b ):
                    
                    new_options.SetBoolean( b, False )
                    
                
            
            self.update()
            
        
        new_options = CG.client_controller.new_options
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        ClientGUIMenus.AppendMenuItem( menu, 'recenter media', 'Restore the media position to the center point.', self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_RESET_PAN_TO_CENTER ) )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        for zoom_type in ClientGUICanvasMedia.MEDIA_VIEWER_ZOOM_TYPES:
            
            label = ClientGUICanvasMedia.media_viewer_zoom_type_str_lookup[ zoom_type ]
            description = ClientGUICanvasMedia.media_viewer_zoom_type_description_lookup[ zoom_type ]
            simple_command = ClientGUICanvasMedia.media_viewer_zoom_type_to_cac_simple_commands[ zoom_type ]
            
            ClientGUIMenus.AppendMenuCheckItem( menu, label, description, self._current_zoom_type == zoom_type, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( simple_command ) )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuCheckItem( menu, 'try to lock current size', 'Try to preserve the zoom ratio between visual media. Useful when trying to compare duplicates.', new_options.GetBoolean( 'media_viewer_lock_current_zoom' ), flip_background_boolean, 'media_viewer_lock_current_zoom' )
        ClientGUIMenus.AppendMenuCheckItem( menu, 'lock current zoom type', 'Prevent the zoom level from changing when switching images.', new_options.GetBoolean( 'media_viewer_lock_current_zoom_type' ), flip_background_boolean, 'media_viewer_lock_current_zoom_type' )
        ClientGUIMenus.AppendMenuCheckItem( menu, 'lock current pan', 'Prevent the panning position from changing when switching images. Useful when trying to compare duplicates.', new_options.GetBoolean( 'media_viewer_lock_current_pan' ), flip_background_boolean, 'media_viewer_lock_current_pan' )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _ShowWindowResizeOptionsMenu( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        ClientGUIMenus.AddLastClickMemory( menu )
        
        # TODO: fix this up to have an optional second callable on menu items for right-click
        
        ClientGUIMenus.AppendMenuItem( menu, 'resize to fit', 'Resize the window to fit the media without changing anything else.', lambda: ( self.sendApplicationCommand.emit( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_VIEWER_CENTER ) )
                                                                                                                                if HG.last_mouse_click_button != QC.Qt.MouseButton.RightButton 
                                                                                                                                else self.sendApplicationCommand.emit( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA ) ) ) )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'resize to 50%', 'Zoom the media to 50% and resize the window to fit it.', lambda: ( self.sendApplicationCommand.emit( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED_VIEWER_CENTER, 0.5 ) )
                                                                                                                                if HG.last_mouse_click_button != QC.Qt.MouseButton.RightButton
                                                                                                                                else self.sendApplicationCommand.emit( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED, 0.5 ) ) ) )
        ClientGUIMenus.AppendMenuItem( menu, 'resize to 75%', 'Zoom the media to 75% and resize the window to fit it.', lambda: ( self.sendApplicationCommand.emit( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED_VIEWER_CENTER, 0.75  ) )
                                                                                                                                if HG.last_mouse_click_button != QC.Qt.MouseButton.RightButton
                                                                                                                                else self.sendApplicationCommand.emit( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED, 0.75 ) ) ) )
        ClientGUIMenus.AppendMenuItem( menu, 'resize to 100%', 'Zoom the media to 100% and resize the window to fit it.', lambda: ( self.sendApplicationCommand.emit( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED_VIEWER_CENTER, 1.0  ) )
                                                                                                                                if HG.last_mouse_click_button != QC.Qt.MouseButton.RightButton
                                                                                                                                else self.sendApplicationCommand.emit( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED, 1.0 ) ) ) )
        ClientGUIMenus.AppendMenuItem( menu, 'resize to 150%', 'Zoom the media to 150% and resize the window to fit it.', lambda: ( self.sendApplicationCommand.emit( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED_VIEWER_CENTER, 1.5  ) )
                                                                                                                                if HG.last_mouse_click_button != QC.Qt.MouseButton.RightButton
                                                                                                                                else self.sendApplicationCommand.emit( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED, 1.5 ) ) ) )
        ClientGUIMenus.AppendMenuItem( menu, 'resize to 200%', 'Zoom the media to 200% and resize the window to fit it.', lambda: ( self.sendApplicationCommand.emit( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED_VIEWER_CENTER, 2.0  ) )
                                                                                                                                if HG.last_mouse_click_button != QC.Qt.MouseButton.RightButton
                                                                                                                                else self.sendApplicationCommand.emit( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED, 2.0 ) ) ) )
        
        #append a non clickable note that says you can right click the above options to choose to center the media first or not. so if you left-click it jumps the media back to window center before resizing, if you right click it jumps the window to where the canvas media location is onscreen and resizes there
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuLabel( menu, 'Right click any of the above to skip centering the media in the viewer window before zooming and/or resizing.' )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def DragButtonHit( self ):
        
        if self._current_media is None:
            
            return
            
        
        page_key = None
        
        media = [ self._current_media ]
        
        alt_down = QW.QApplication.keyboardModifiers() & QC.Qt.KeyboardModifier.AltModifier
        
        drag_object = QG.QDrag( self )
        
        result = ClientGUIDragDrop.DoFileExportDragDrop( drag_object, page_key, media, alt_down )
        
        if result != QC.Qt.DropAction.IgnoreAction:
            
            self.sendApplicationCommand.emit( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAUSE_MEDIA ) )
            
        
    
    def resizeEvent( self, event ):
        
        # reset wrap width
        self._ResetText()
        
        event.ignore()
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        if self._current_media is not None:
            
            my_hash = self._current_media.GetHash()
            
            do_redraw = False
            
            for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
                
                if True in ( my_hash in content_update.GetHashes() for content_update in content_updates ):
                    
                    do_redraw = True
                    
                    break
                    
                
            
            if do_redraw:
                
                self._ResetText()
                self._ResetButtons()
                
            
        
    
    def SetCurrentZoom( self, zoom_type: int, zoom: float ):
        
        self._current_zoom_type = zoom_type
        self._current_zoom = zoom
        
        label = ClientData.ConvertZoomToPercentage( self._current_zoom )
        
        self._zoom_text.setText( label )
        
    
    def SetMedia( self, media ):
        
        super().SetMedia( media )
        
        self._ResetText()
        
        self._ResetButtons()
        
        # minimumsize is not immediately updated without this
        self.layout().activate()
        
        self._SizeAndPosition()
        
    
    def SetIndexString( self, canvas_key, text ):
        
        if canvas_key == self._canvas_key:
            
            self._current_index_string = text
            
            self._index_text.setText( self._current_index_string )
            
        
    
class CanvasHoverFrameTopArchiveDeleteFilter( CanvasHoverFrameTop ):
    
    def _Archive( self ):
        
        self.sendApplicationCommand.emit( CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_FILE ) )
        
    
    def _PopulateLeftButtons( self ):
        
        self._back_button = ClientGUICommon.IconButton( self, CC.global_icons().position_previous, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_BACK ) )
        self._back_button.SetToolTipWithShortcuts( 'back', CAC.SIMPLE_ARCHIVE_DELETE_FILTER_BACK )
        self._back_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        QP.AddToLayout( self._top_left_hbox, self._back_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        CanvasHoverFrameTop._PopulateLeftButtons( self )
        
        self._skip_button = ClientGUICommon.IconButton( self, CC.global_icons().position_next, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_SKIP ) )
        self._skip_button.SetToolTipWithShortcuts( 'skip', CAC.SIMPLE_ARCHIVE_DELETE_FILTER_SKIP )
        self._skip_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        QP.AddToLayout( self._top_left_hbox, self._skip_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
    def _ResetArchiveButton( self ):
        
        self._archive_button.SetIconSmart( CC.global_icons().archive )
        self._archive_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'archive' ) )
        
    
class CanvasHoverFrameTopNavigable( CanvasHoverFrameTop ):
    
    def _PopulateLeftButtons( self ):
        
        self._previous_button = ClientGUICommon.IconButton( self, CC.global_icons().position_previous, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_PREVIOUS ) )
        self._previous_button.SetToolTipWithShortcuts( 'previous', CAC.SIMPLE_VIEW_PREVIOUS )
        self._previous_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        self._index_text = ClientGUICommon.BetterStaticText( self, 'index' )
        
        self._next_button = ClientGUICommon.IconButton( self, CC.global_icons().position_next, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_NEXT ) )
        self._next_button.SetToolTipWithShortcuts( 'next', CAC.SIMPLE_VIEW_NEXT )
        self._next_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        QP.AddToLayout( self._top_left_hbox, self._previous_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_left_hbox, self._index_text, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_left_hbox, self._next_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
class CanvasHoverFrameTopDuplicatesFilter( CanvasHoverFrameTopNavigable ):
    
    def _PopulateLeftButtons( self ):
        
        self._first_button = ClientGUICommon.IconButton( self, CC.global_icons().position_first, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_BACK ) )
        self._first_button.SetToolTipWithShortcuts( 'go back a pair', CAC.SIMPLE_DUPLICATE_FILTER_BACK )
        self._first_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        QP.AddToLayout( self._top_left_hbox, self._first_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        CanvasHoverFrameTopNavigable._PopulateLeftButtons( self )
        
        self._last_button = ClientGUICommon.IconButton( self, CC.global_icons().position_last, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_SKIP ) )
        self._last_button.SetToolTipWithShortcuts( 'show a different pair', CAC.SIMPLE_DUPLICATE_FILTER_SKIP )
        self._last_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        QP.AddToLayout( self._top_left_hbox, self._last_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
    def _ShowZoomOptionsMenu( self ):
        
        new_options = CG.client_controller.new_options
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        ClientGUIMenus.AppendMenuItem( menu, 'recenter media', 'Restore the media position to the center point.', self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_RESET_PAN_TO_CENTER ) )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        for zoom_type in ClientGUICanvasMedia.MEDIA_VIEWER_ZOOM_TYPES:
            
            label = ClientGUICanvasMedia.media_viewer_zoom_type_str_lookup[ zoom_type ]
            description = ClientGUICanvasMedia.media_viewer_zoom_type_description_lookup[ zoom_type ]
            simple_command = ClientGUICanvasMedia.media_viewer_zoom_type_to_cac_simple_commands[ zoom_type ]
            
            ClientGUIMenus.AppendMenuCheckItem( menu, label, description, self._current_zoom_type == zoom_type, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( simple_command ) )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuLabel( menu, 'media size and pan are locked' )
        
        CGC.core().PopupMenu( self, menu )
        
    

class CanvasHoverFrameTopNavigableList( CanvasHoverFrameTopNavigable ):
    
    def _PopulateLeftButtons( self ):
        
        self._first_button = ClientGUICommon.IconButton( self, CC.global_icons().position_first, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_FIRST ) )
        self._first_button.SetToolTipWithShortcuts( 'first', CAC.SIMPLE_VIEW_FIRST )
        self._first_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        QP.AddToLayout( self._top_left_hbox, self._first_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        CanvasHoverFrameTopNavigable._PopulateLeftButtons( self )
        
        self._last_button = ClientGUICommon.IconButton( self, CC.global_icons().position_last, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_LAST ) )
        self._last_button.SetToolTipWithShortcuts( 'last', CAC.SIMPLE_VIEW_LAST )
        self._last_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        QP.AddToLayout( self._top_left_hbox, self._last_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        left_click_call = HydrusData.Call( self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_RANDOM ) )
        right_click_call = HydrusData.Call( self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_UNDO_RANDOM ) )
        
        self._random_button = ClientGUICommon.IconButtonMultiClickable( self, CC.global_icons().position_random, left_click_call, right_click_call )
        
        self._random_button.setToolTip( 'random - right-click to undo showing random media' )
        self._random_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        QP.AddToLayout( self._top_left_hbox, self._random_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
    


class InboxIconClickFilter( QC.QObject ):
    
    def __init__( self, parent, click_callable ):
        
        super().__init__( parent )
        
        self._click_callable = click_callable
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == QC.QEvent.Type.MouseButtonPress:
                
                event = typing.cast( QG.QMouseEvent, event )
                
                if event.button() == QC.Qt.MouseButton.LeftButton:
                    
                    self._click_callable()
                    
                    return True
                    
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    


class CanvasHoverFrameTopRight( CanvasHoverFrame ):
    
    def __init__( self, parent, my_canvas, top_hover: CanvasHoverFrameTop, canvas_key ):
        
        super().__init__( parent, my_canvas, canvas_key )
        
        self._top_hover = top_hover
        
        self._spacing = 2
        self._margin = 2
        
        vbox = QP.VBoxLayout( spacing = self._spacing, margin = self._margin )
        self.setSizePolicy( QW.QSizePolicy.Policy.Fixed, QW.QSizePolicy.Policy.Fixed )
        
        self._icon_panel = QW.QWidget( self )
        
        self._trash_icon = QW.QLabel( self._icon_panel, pixmap = CC.global_icons().trash.pixmap( 16, 16 ) )
        self._inbox_icon = QW.QLabel( self._icon_panel, pixmap = CC.global_icons().inbox.pixmap( 16, 16 ) )
        
        self._inbox_icon.installEventFilter( InboxIconClickFilter( self, self._Archive ) )
        
        icon_hbox = QP.HBoxLayout( spacing = 0 )
        
        icon_hbox.addStretch( 0 )
        
        QP.AddToLayout( icon_hbox, self._inbox_icon, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( icon_hbox, self._trash_icon, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._icon_panel.setLayout( icon_hbox )
        
        canvas_type = self._my_canvas.GetCanvasType()
        
        # repo strings
        
        self._location_strings = ClientGUICommon.BetterStaticText( self, '' )
        
        self._location_strings.setAlignment( QC.Qt.AlignmentFlag.AlignRight | QC.Qt.AlignmentFlag.AlignVCenter )
        
        # urls
        
        self._last_seen_urls = []
        self._urls_vbox = QP.VBoxLayout()
        
        # likes
        
        like_hbox = QP.HBoxLayout( spacing = 0 )
        
        like_services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ) )
        
        if len( like_services ) > 0:
            
            like_hbox.addStretch( 0 )
            
        
        for service in like_services:
            
            service_key = service.GetServiceKey()
            
            control = RatingLikeCanvas( self, service_key, canvas_key, canvas_type )
            control.setSizePolicy( QW.QSizePolicy.Policy.Fixed, QW.QSizePolicy.Policy.Fixed )
            
            self.mediaChanged.connect( control.SetMedia )
            self.mediaCleared.connect( control.ClearMedia )
            
            QP.AddToLayout( like_hbox, control, CC.FLAGS_NONE )
            
        
        QP.AddToLayout( vbox, like_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        # each numerical one in turn
        
        numerical_services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        for service in numerical_services:
            
            service_key = service.GetServiceKey()
            
            control = RatingNumericalCanvas( self, service_key, canvas_key, canvas_type )
            control.setSizePolicy( QW.QSizePolicy.Policy.Fixed, QW.QSizePolicy.Policy.Fixed )
            
            self.mediaChanged.connect( control.SetMedia )
            self.mediaCleared.connect( control.ClearMedia )
            
            QP.AddToLayout( vbox, control, CC.FLAGS_NONE )
            
            vbox.setAlignment( control, QC.Qt.AlignmentFlag.AlignRight )
            
        
        # now incdec
        
        incdec_hbox = QP.HBoxLayout( spacing = 0, margin = 0 )
        
        incdec_services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_INCDEC, ) )
        
        if len( incdec_services ) > 0:
            
            incdec_hbox.addStretch( 0 )
            
        
        incdec_pad = QC.QSize( 0, round( ClientGUIPainterShapes.PAD_PX / 2 ) )
        
        for service in incdec_services:
            
            service_key = service.GetServiceKey()
            
            control = RatingIncDecCanvas( self, service_key, canvas_key, incdec_pad, canvas_type )
            control.setSizePolicy( QW.QSizePolicy.Policy.Fixed, QW.QSizePolicy.Policy.Fixed )
            
            self.mediaChanged.connect( control.SetMedia )
            self.mediaCleared.connect( control.ClearMedia )
            
            QP.AddToLayout( incdec_hbox, control, CC.FLAGS_NONE )
            
        
        QP.AddToLayout( vbox, incdec_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        #
        
        QP.AddToLayout( vbox, self._icon_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._location_strings, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._urls_vbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        self._ResetWidgets()
        
        self.layout().activate()
        
        self.adjustSize()
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
        
    
    def _Archive( self ):
        
        if self._current_media.HasInbox():
            
            command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_FILE )
            
        else:
            
            command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_INBOX_FILE )
            
        
        self.sendApplicationCommand.emit( command )
        
    
    def _GetIdealSizeAndPosition( self ):
        
        canvas_type = self._my_canvas.GetCanvasType()
        
        if canvas_type in CC.CANVAS_MEDIA_VIEWER_TYPES:
            
            if CG.client_controller.new_options.GetBoolean( 'disable_top_right_hover_in_media_viewer'):
                
                return ( False, QC.QSize( 0, 0 ), QC.QPoint( 0, 0 ) )
                
            
            parent_window = self.parentWidget().window()
            
            parent_size = parent_window.size()
            
            parent_width = parent_size.width()
            
            my_size = self.size()
            
            my_width = my_size.width()
            my_height = my_size.height()
            
            my_ideal_width = self.sizeHint().width()
            
            if self._top_hover and not self._top_hover.PositionInitialisedSinceLastMedia():
                
                self._top_hover.DoRegularHideShow()
                
            
            top_hover_bottom_right = QC.QPoint( 0, 0 )
            
            if self._top_hover and self._top_hover.PositionInitialisedSinceLastMedia():
                
                # don't use .rect() here, it (sometimes) isn't updated on a hidden window until next show, I think
                top_hover_bottom_right = QC.QPoint( self._top_hover.x() + self._top_hover.width(), self._top_hover.y() + self._top_hover.height() )
                
                width_beside_top_hover = parent_window.rect().topRight().x() - top_hover_bottom_right.x()
                
                my_ideal_width = max( my_ideal_width, width_beside_top_hover )
                
            
            my_ideal_height = self.sizeHint().height()
            
            should_resize = my_ideal_width != my_width or my_ideal_height != my_height
            
            ideal_size = QC.QSize( my_ideal_width, my_ideal_height )
            
            ideal_position = QC.QPoint( int( parent_width - my_ideal_width ), 0 )
            
            if self._top_hover and self._top_hover.PositionInitialisedSinceLastMedia():
                
                if top_hover_bottom_right.x() > ideal_position.x():
                    
                    ideal_position.setY( top_hover_bottom_right.y() )
                    
                
            return ( should_resize, ideal_size, ideal_position )
            
        elif canvas_type == CC.CANVAS_PREVIEW and CG.client_controller.new_options.GetBoolean( 'preview_window_hover_top_right_shows_popup' ):
            
            preview_size = self.parentWidget().size()
            
            #sometimes the entire width of the widget changes, which affects position calculations; so recalculate the frame size first here
            self.adjustSize()
            
            my_size = self.size()
            my_width = my_size.width()
            my_height = my_size.height()
            
            my_ideal_width = min( my_width, preview_size.width() )
            my_ideal_height = min( my_height, preview_size.height() )
            
            should_resize = ( my_ideal_width != my_width or my_ideal_height != my_height )
            
            ideal_size = QC.QSize( my_ideal_width, my_ideal_height )
            
            ideal_position = QC.QPoint( preview_size.width() - my_ideal_width, 0 )
            
            return ( should_resize, ideal_size, ideal_position )
            
        
        return ( False, QC.QSize( 0, 0 ), QC.QPoint( 0, 0 ) )
        
    
    def _ResetWidgets( self ):
        
        if self._current_media is not None:
            
            has_inbox = self._current_media.HasInbox()
            has_trash = self._current_media.GetLocationsManager().IsTrashed()
            
            if has_inbox or has_trash:
                
                self._icon_panel.show()
                
                if has_inbox:
                    
                    self._inbox_icon.show()
                    
                else:
                    
                    self._inbox_icon.hide()
                    
                
                if has_trash:
                    
                    self._trash_icon.show()
                    
                else:
                    
                    self._trash_icon.hide()
                    
                
            else:
                
                self._icon_panel.setVisible( False )
                
            
            location_strings = self._current_media.GetLocationsManager().GetLocationStrings()
            
            if len( location_strings ) == 0:
                
                self._location_strings.hide()
                
            else:
                
                location_string = '\n'.join( location_strings )
                
                self._location_strings.setText( location_string )
                
                self._location_strings.show()
                
            
            # urls
            
            # BE WARY TRAVELLER
            # unusual sizeHint gubbins occurs here if one does not take care
            # ensure you check for flicker when transitioning from a topright media with and without urls
            # and check that it is ok when the mouse is over the hover for the transition vs mouse not over and visiting later
            
            urls = self._current_media.GetLocationsManager().GetURLs()
            
            if urls != self._last_seen_urls:
                
                self._last_seen_urls = list( urls )
                
                QP.ClearLayout( self._urls_vbox, delete_widgets = True )
                
                url_tuples = CG.client_controller.network_engine.domain_manager.ConvertURLsToMediaViewerTuples( urls )
                
                for ( display_string, url ) in url_tuples:
                    
                    link = ClientGUICommon.BetterHyperLink( self, display_string, url )
                    
                    link.setAlignment( QC.Qt.AlignmentFlag.AlignRight )
                    
                    # very important!
                    # needed for magic hover window crazy layout reasons
                    link.setVisible( True )
                    
                    QP.AddToLayout( self._urls_vbox, link, CC.FLAGS_EXPAND_BOTH_WAYS )
                    
                
            
        
        # dare not remove this
        self.layout().activate()
        
        self._SizeAndPosition()
        
    
    def GetVboxSpacingAndMargin( self ):
        
        return ( self._spacing, self._margin )
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        if self._current_media is not None:
            
            my_hash = self._current_media.GetHash()
            
            for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
                
                if True in ( my_hash in content_update.GetHashes() for content_update in content_updates ):
                    
                    self._ResetWidgets()
                    
                    return
                    
                
            
        
    
    def SetMedia( self, media ):
        
        super().SetMedia( media )
        
        self._ResetWidgets()
        
        self._position_initialised_since_last_media = False
        
    

class NotePanel( QW.QWidget ):
    
    editNote = QC.Signal( str )
    devilsBargainManualUpdateGeometry = QC.Signal()
    
    def __init__( self, parent: "CanvasHoverFrameRightNotes", name: str, note: str, note_visible: bool ):
        
        super().__init__( parent )
        
        self._parent = parent
        
        self._name = name
        self._note_visible = note_visible
        
        self._note_name = ClientGUICommon.BetterStaticText( self, label = name )
        
        self._note_name.setAlignment( QC.Qt.AlignmentFlag.AlignHCenter )
        self._note_name.setWordWrap( True )
        
        font = QG.QFont( self._note_name.font() )
        
        font.setBold( True )
        
        self._note_name.setFont( font )
        
        self._note_text = ClientGUICommon.BetterStaticText( self, label = note )
        
        self._note_text.setAlignment( QC.Qt.AlignmentFlag.AlignJustify )
        self._note_text.setWordWrap( True )
        
        vbox = QP.VBoxLayout( margin = 0 )
        
        QP.AddToLayout( vbox, self._note_name, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._note_text, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._note_text.setVisible( note_visible )
        
        self.setLayout( vbox )
        
        self._note_name.installEventFilter( self )
        self._note_text.installEventFilter( self )
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == QC.QEvent.Type.MouseButtonPress:
                
                event = typing.cast( QG.QMouseEvent, event )
                
                if event.button() == QC.Qt.MouseButton.LeftButton:
                    
                    self.editNote.emit( self._name )
                    
                else:
                    
                    self._note_text.setVisible( self._note_text.isHidden() )
                    
                    self._note_visible = not self._note_text.isHidden()
                    
                    # a normal updateGeometry call doesn't seem to do it (and indeed whatever implicit call occurs), I believe because we have the disconnected layout nonsense
                    self.devilsBargainManualUpdateGeometry.emit()
                    
                
                return True
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
    def heightForWidth( self, width: int ):
        
        spacing = self.layout().spacing()
        margin = self.layout().contentsMargins().top()
        
        total_height = 0
        
        expected_widget_height = self._note_name.heightForWidth( width )
        
        if self._note_name.width() >= width and self._note_name.height() > expected_widget_height:
            
            # there's some mysterious padding that I can't explain, probably a layout flag legacy issue, so we override here if the width seems correct
            
            expected_widget_height = self._note_name.height()
            
        
        total_height += expected_widget_height
        
        if not self._note_text.isHidden():
            
            total_height += spacing
            
            expected_widget_height = self._note_text.heightForWidth( width )
            
            if self._note_text.width() >= width and self._note_text.height() > expected_widget_height:
                
                # there's some mysterious padding that I can't explain, probably a layout flag legacy issue, so we override here if the width seems correct
                
                expected_widget_height = self._note_text.height()
                
            
            total_height += expected_widget_height
            
        
        total_height += margin * 2
        
        return total_height
        
    
    def IsNoteTextVisible( self ) -> bool:
        
        # through various testing, this property appears to be sometimes whack. or it may be good now but was once tangled up in a mess of hacks
        # don't really like it, so maybe just do `not self._note_text.isHidden()` live
        return self._note_visible
        
    
    def sizeHint( self ) -> QC.QSize:
        
        width = self._parent.GetNoteWidth()
        height = self.heightForWidth( width )
        
        return QC.QSize( width, height )
        
    
class CanvasHoverFrameRightNotes( CanvasHoverFrame ):
    
    def __init__( self, parent, my_canvas, top_right_hover: CanvasHoverFrameTopRight, canvas_key ):
        
        super().__init__( parent, my_canvas, canvas_key )
        
        self._top_right_hover = top_right_hover
        
        self._margin = 2
        self._spacing = 2
        
        self._vbox = QP.VBoxLayout( spacing = self._spacing, margin = self._margin )
        self._names_to_note_panels = {}
        
        self.setSizePolicy( QW.QSizePolicy.Policy.Fixed, QW.QSizePolicy.Policy.Expanding )
        
        self.setLayout( self._vbox )
        
        self._ResetNotes()
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
        
    
    def _EditNotes( self, name ):
        
        ClientGUIMediaModalActions.EditFileNotes( self, self._current_media, name_to_start_on = name )
        
    
    def _GetIdealSizeAndPosition( self ):
        
        if len( self._names_to_note_panels ) == 0:
            
            return ( True, QC.QSize( 20, 20 ), QC.QPoint( -100, -100 ) )
            
        
        parent_window = self.parentWidget().window()
        
        parent_size = parent_window.size()
        
        parent_width = parent_size.width()
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        my_ideal_width = int( parent_width * SIDE_HOVER_PROPORTIONS )
        
        ideal_position = QC.QPoint( parent_width - my_ideal_width, 0 )
        
        if not self._top_right_hover.PositionInitialisedSinceLastMedia():
            
            self._top_right_hover.DoRegularHideShow()
            
        
        spacing = self.layout().spacing()
        
        if self._top_right_hover.PositionInitialisedSinceLastMedia():
            
            # steer clear of 'top_right.bottomLeft' style gubbins, easy to get tripped up on some weird overspill circumstance
            
            ideal_position.setY( self._top_right_hover.height() + spacing )
            
        
        max_possible_height = parent_size.height() - ideal_position.y()
        
        # now let's go full meme
        # the problem here is that sizeHint produces what width the static text wants based on its own word wrap rules
        # we want to say 'with this fixed width, how tall are we?'
        # VBoxLayout doesn't support heightForWidth, but statictext does, so let's hack it
        # ideal solution here is to write a new layout that delivers heightforwidth, but lmao. maybe Qt6 will do it. EDIT: It didn't really work?
        
        margin = self.layout().contentsMargins().top()
        
        my_axis_frame_width = self.frameWidth() * 2
        my_axis_margin = margin * 2
        
        note_panel_width = my_ideal_width - ( my_axis_frame_width + my_axis_margin )
        
        best_guess_at_height_for_width = sum( ( spacing + ( margin * 2 ) + note_panel.heightForWidth( note_panel_width ) for note_panel in self._names_to_note_panels.values() ) ) - spacing
        
        best_guess_at_height_for_width += self.frameWidth() * 2
        
        #
        
        my_ideal_height = min( best_guess_at_height_for_width, max_possible_height )
        
        should_resize = my_ideal_width != my_width or abs( my_height - my_ideal_height ) > 10
        
        ideal_size = QC.QSize( my_ideal_width, my_ideal_height )
        
        return ( should_resize, ideal_size, ideal_position )
        
    
    def _ResetNotes( self ):
        
        note_panel_names_with_hidden_notes = set()
        
        for ( name, note_panel ) in list( self._names_to_note_panels.items() ):
            
            if not note_panel.IsNoteTextVisible():
                
                note_panel_names_with_hidden_notes.add( name )
                
            
            self._vbox.removeWidget( note_panel )
            
            note_panel.deleteLater()
            
        
        # BE CAREFUL IF YOU EDIT ANY OF THIS
        # this is a house of cards because of the whack disconnected layout situation
        # one minor change and you'll get tumble into flicker hell
        
        self._names_to_note_panels = {}
        
        if self._current_media is not None and self._current_media.HasNotes():
            
            names_to_notes = self._current_media.GetNotesManager().GetNamesToNotes()
            
            for name in sorted( names_to_notes.keys() ):
                
                note = names_to_notes[ name ]
                
                note_visible = name not in note_panel_names_with_hidden_notes
                
                note_panel = NotePanel( self, name, note, note_visible )
                
                # very important
                # magico fix as per the urls in the top-right
                note_panel.setVisible( True )
                
                QP.AddToLayout( self._vbox, note_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                self._names_to_note_panels[ name ] = note_panel
                
                note_panel.editNote.connect( self._EditNotes )
                note_panel.devilsBargainManualUpdateGeometry.connect( self._SizeAndPosition ) # total wewmode to handle note hide/show
                
            
        
        # dare not remove this
        self.layout().activate()
        
        self._SizeAndPosition()
        
    
    def _ShouldBeHidden( self ):
        
        if len( self._names_to_note_panels ) == 0:
            
            return True
            
        
        return CanvasHoverFrame._ShouldBeHidden( self )
        
    
    def GetNoteWidth( self ):
        
        note_panel_width = self.width() - ( self.frameWidth() + self.layout().contentsMargins().left() ) * 2
        
        return note_panel_width
        
    
    def GetNoteSpacingAndMargin( self ):
        
        return ( self._spacing, self._margin )
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        if self._current_media is not None:
            
            my_hash = self._current_media.GetHash()
            
            do_redraw = False
            
            for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
                
                if True in ( my_hash in content_update.GetHashes() for content_update in content_updates if content_update.GetDataType() == HC.CONTENT_TYPE_NOTES ):
                    
                    do_redraw = True
                    
                    break
                    
                
            
            if do_redraw:
                
                self._ResetNotes()
                
            
        
    
    def SetMedia( self, media ):
        
        super().SetMedia( media )
        
        self._ResetNotes()
        
        self._position_initialised_since_last_media = False
        
    
class CanvasHoverFrameRightDuplicates( CanvasHoverFrame ):
    
    showPairInPage = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, my_canvas: QW.QWidget, canvas_key: bytes, show_approve_deny = False ):
        
        super().__init__( parent, my_canvas, canvas_key )
        
        self._always_on_top = True
        
        self._show_approve_deny = show_approve_deny
        
        self._current_index_string = ''
        
        self._comparison_media = None
        
        self._show_in_a_page_button = ClientGUICommon.IconButton( self, CC.global_icons().copy, self.showPairInPage.emit )
        self._show_in_a_page_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'send pair to the duplicates media page, for later processing' ) )
        self._show_in_a_page_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        self._trash_button = ClientGUICommon.IconButton( self, CC.global_icons().delete, CG.client_controller.pub, 'canvas_delete', self._canvas_key )
        self._trash_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'send to trash' ) )
        self._trash_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'edit duplicate metadata merge options for \'this is better\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_BETTER ) ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'edit duplicate metadata merge options for \'same quality\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_SAME_QUALITY ) ) )
        
        if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'edit duplicate metadata merge options for \'alternates\' (advanced!)', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_ALTERNATE ) ) )
            
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'edit background lighten/darken switch intensity', 'edit how much the background will brighten or darken as you switch between the pair', self._EditBackgroundSwitchIntensity ) )
        
        self._cog_button = ClientGUIMenuButton.CogIconButton( self, menu_template_items )
        self._cog_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        close_button = ClientGUICommon.IconButton( self, CC.global_icons().stop, CG.client_controller.pub, 'canvas_close', self._canvas_key )
        close_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'close filter' ) )
        close_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        self._back_a_pair = ClientGUICommon.IconButton( self, CC.global_icons().position_first, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_BACK ) )
        self._back_a_pair.SetToolTipWithShortcuts( 'go back a pair', CAC.SIMPLE_DUPLICATE_FILTER_BACK )
        self._back_a_pair.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        self._index_text = ClientGUICommon.BetterStaticText( self, 'index' )
        
        self._next_button = ClientGUICommon.IconButton( self, CC.global_icons().pair, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_NEXT ) )
        self._next_button.SetToolTipWithShortcuts( 'next', CAC.SIMPLE_VIEW_NEXT )
        self._next_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        self._skip_a_pair = ClientGUICommon.IconButton( self, CC.global_icons().position_last, self.sendApplicationCommand.emit, CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_SKIP ) )
        self._skip_a_pair.SetToolTipWithShortcuts( 'show a different pair', CAC.SIMPLE_DUPLICATE_FILTER_SKIP )
        self._skip_a_pair.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
        
        command_button_vbox = QP.VBoxLayout()
        
        dupe_boxes = []
        
        if self._show_approve_deny:
            
            dupe_commands = []
            
            dupe_commands.append( ( 'approve', 'Approve this pair for the original auto-resolution rule.', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_APPROVE_AUTO_RESOLUTION ) ) )
            dupe_commands.append( ( 'deny', 'Deny this pair for the original auto-resolution rule.', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_DENY_AUTO_RESOLUTION ) ) )
            
            dupe_boxes.append( ( 'auto-resolution', dupe_commands ) )
            
        
        dupe_commands = []
        
        dupe_commands.append( ( 'this is better, and delete the other', 'Set that the current file you are looking at is better than the other in the pair, and set the other file to be deleted.', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_AND_DELETE_OTHER ) ) )
        dupe_commands.append( ( 'this is better, but keep both', 'Set that the current file you are looking at is better than the other in the pair, but keep both files.', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_BUT_KEEP_BOTH ) ) )
        dupe_commands.append( ( 'they are the same quality', 'Set that the two files are duplicates of very similar quality.', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_EXACTLY_THE_SAME ) ) )
        
        dupe_boxes.append( ( 'set as duplicates', dupe_commands ) )
        
        dupe_commands = []
        
        dupe_commands.append( ( 'they are related alternates', 'Set that the files are not duplicates, but that one is derived from the other or that they are both descendants of a common ancestor.', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_ALTERNATES ) ) )
        dupe_commands.append( ( 'they are not related', 'Set that the files are not duplicates or otherwise related--that this potential pair is a false positive match.', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_FALSE_POSITIVE ) ) )
        dupe_commands.append( ( 'custom action', 'Choose one of the other actions but customise the merge and delete options for this specific decision.', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_CUSTOM_ACTION ) ) )
        
        dupe_boxes.append( ( 'other', dupe_commands ) )
        
        self._this_is_better_and_delete_other = None
        
        for ( panel_name, dupe_commands ) in dupe_boxes:
            
            button_panel = ClientGUICommon.StaticBox( self, panel_name )
            
            for ( label, tooltip, command ) in dupe_commands:
                
                command_button = ClientGUICommon.BetterButton( button_panel, label, self.sendApplicationCommand.emit, command )
                command_button.setFocusPolicy( QC.Qt.FocusPolicy.TabFocus )
                
                command_button.SetToolTipWithShortcuts( tooltip, command.GetSimpleAction() )
                
                button_panel.Add( command_button, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                if command == CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_AND_DELETE_OTHER ):
                    
                    self._this_is_better_and_delete_other = command_button
                    
                
            
            QP.AddToLayout( command_button_vbox, button_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self._comparison_statements_vbox = QP.VBoxLayout()
        
        self._comparison_statement_score_summary = ClientGUICommon.BetterStaticText( self )
        self._comparison_statement_score_summary.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
        
        QP.AddToLayout( self._comparison_statements_vbox, self._comparison_statement_score_summary, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._comparison_statement_names_fast = [ 'filesize', 'resolution', 'ratio', 'mime', 'num_tags', 'time_imported', 'pixel_duplicates', 'has_transparency', 'exif_data', 'embedded_metadata', 'icc_profile', 'has_audio', 'duration' ]
        self._comparison_statement_names_slow = ['jpeg_subsampling', 'jpeg_quality', 'a_and_b_are_visual_duplicates' ]
        
        self._total_score_fast = 0
        self._total_score_slow = 0
        self._they_are_pixel_duplicates = False
        
        self._comparison_statements_sts = {}
        
        for name in self._comparison_statement_names_fast + self._comparison_statement_names_slow:
            
            panel = QW.QWidget( self )
            
            # don't set tooltip here, we do it later
            st = ClientGUICommon.BetterStaticText( panel, 'init' )
            
            st.setAlignment( QC.Qt.AlignmentFlag.AlignCenter )
            
            self._comparison_statements_sts[ name ] = ( panel, st )
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            panel.setLayout( hbox )
            
            panel.setVisible( False )
            
            QP.AddToLayout( self._comparison_statements_vbox, panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        self._comparison_statement_updater_fast = self._InitialiseComparisonStatementUpdaterFast()
        self._comparison_statement_updater_slow = self._InitialiseComparisonStatementUpdaterSlow()
        
        #
        
        top_button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( top_button_hbox, self._next_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( top_button_hbox, self._show_in_a_page_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( top_button_hbox, self._trash_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( top_button_hbox, self._cog_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( top_button_hbox, close_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        navigation_button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( navigation_button_hbox, self._back_a_pair, CC.FLAGS_CENTER_PERPENDICULAR )
        navigation_button_hbox.addStretch( 1 )
        QP.AddToLayout( navigation_button_hbox, self._index_text, CC.FLAGS_CENTER_PERPENDICULAR )
        navigation_button_hbox.addStretch( 1 )
        QP.AddToLayout( navigation_button_hbox, self._skip_a_pair, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, navigation_button_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        #QP.AddToLayout( vbox, self._next_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, top_button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, command_button_vbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._comparison_statements_vbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        CG.client_controller.sub( self, 'SetDuplicatePair', 'canvas_new_duplicate_pair' )
        CG.client_controller.sub( self, 'SetIndexString', 'canvas_new_index_string' )
        
    
    def _BlankStatementsBeforePopulation( self, names ):
        
        for name in names:
            
            ( panel, st ) = self._comparison_statements_sts[ name ]
            
            if panel.isVisible():
                
                current_text = st.text()
                
                num_newlines = current_text.count( '\n' )
                
                st.setText( num_newlines * '\n' )
                
            
        
    
    def _EditBackgroundSwitchIntensity( self ):
        
        new_options = CG.client_controller.new_options
        
        for ( message, tooltip, variable_name ) in [
            ( 'intensity for A', 'This changes the background colour when you are looking at A. If you have a pure white/black background, it helps to highlight transparency vs opaque white/black image background.', 'duplicate_background_switch_intensity_a' ),
            ( 'intensity for B', 'This changes the background colour when you are looking at B. Making it different to the A value helps to highlight switches between the two.', 'duplicate_background_switch_intensity_b' )
        ]:
            
            value = new_options.GetNoneableInteger( variable_name )
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit lighten/darken intensity' ) as dlg:
                
                panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
                
                control = ClientGUICommon.NoneableSpinCtrl( panel, 3, message = message, none_phrase = 'do not change', min = 1, max = 9 )
                control.setToolTip( ClientGUIFunctions.WrapToolTip( tooltip ) )
                control.SetValue( value )
                
                panel.SetControl( control, perpendicular = True )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    new_value = control.GetValue()
                    
                    new_options.SetNoneableInteger( variable_name, new_value )
                    
                    self.window().update()
                    
                else:
                    
                    return
                    
                
            
        
    
    def _EditMergeOptions( self, duplicate_type ):
        
        new_options = CG.client_controller.new_options
        
        duplicate_content_merge_options = new_options.GetDuplicateContentMergeOptions( duplicate_type )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit duplicate merge options' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            ctrl = ClientGUIDuplicatesContentMergeOptions.EditDuplicateContentMergeOptionsWidget( panel, duplicate_type, duplicate_content_merge_options )
            
            panel.SetControl( ctrl )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                duplicate_content_merge_options = ctrl.GetValue()
                
                new_options.SetDuplicateContentMergeOptions( duplicate_type, duplicate_content_merge_options )
                
            
        
    
    def _EnableDisableButtons( self ):
        
        # old delete-lock stuff. maybe it'll be useful to bring back one day, w/e
        disabled = False
        
        self._this_is_better_and_delete_other.setEnabled( not disabled )
        
    
    def _GetIdealSizeAndPosition( self ):
        
        parent_window = self.parentWidget().window()
        
        parent_size = parent_window.size()
        
        parent_width = parent_size.width()
        parent_height = parent_size.height()
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        my_ideal_width = max( int( parent_width * 0.2 ), self.sizeHint().width() )
        my_ideal_height = self.sizeHint().height()
        
        should_resize = my_ideal_width != my_width or my_ideal_height != my_height
        
        ideal_size = QC.QSize( my_ideal_width, my_ideal_height )
        ideal_position = QC.QPoint( int( parent_width - my_ideal_width ), int( parent_height * 0.3 ) )
        
        return ( should_resize, ideal_size, ideal_position )
        
    
    def _InitialiseComparisonStatementUpdaterFast( self ):
        
        def loading_callable():
            
            self._comparison_statement_score_summary.setText( '' )
            
            self._BlankStatementsBeforePopulation( self._comparison_statement_names_fast )
            
            # no resize here! we don't want any possible flicker mate
            
        
        def pre_work_callable():
            
            if self._current_media is None or self._comparison_media is None:
                
                raise HydrusExceptions.CancelledException()
                
            
            return ( self._current_media.GetMediaResult(), self._comparison_media.GetMediaResult() )
            
        
        def work_callable( args ):
            
            ( current_media_result, comparison_media_result ) = args
            
            ( statements_and_scores, they_are_pixel_duplicates ) = ClientDuplicatesComparisonStatements.GetDuplicateComparisonStatementsFast( current_media_result, comparison_media_result )
            
            return ( statements_and_scores, they_are_pixel_duplicates )
            
        
        def publish_callable( result ):
            
            ( statements_and_scores, they_are_pixel_duplicates ) = result
            
            self._they_are_pixel_duplicates = they_are_pixel_duplicates
            
            self._total_score_fast = sum( ( score for ( statement, score ) in statements_and_scores.values() ) )
            
            self._UpdateTotalScore( finished = False )
            
            self._PopulateStatements( statements_and_scores, self._comparison_statement_names_fast )
            
            self._comparison_statement_updater_slow.update()
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
        
    
    def _InitialiseComparisonStatementUpdaterSlow( self ):
        
        def loading_callable():
            
            self._BlankStatementsBeforePopulation( self._comparison_statement_names_slow )
            
            # no resize here! we don't want any possible flicker mate
            
        
        def pre_work_callable():
            
            if self._current_media is None or self._comparison_media is None:
                
                raise HydrusExceptions.CancelledException()
                
            
            return ( self._current_media.GetMediaResult(), self._comparison_media.GetMediaResult(), self._they_are_pixel_duplicates )
            
        
        def work_callable( args ):
            
            ( current_media_result, comparison_media_result, they_are_pixel_duplicates ) = args
            
            statements_and_scores = ClientDuplicatesComparisonStatements.GetDuplicateComparisonStatementsSlow( current_media_result, comparison_media_result, they_are_pixel_duplicates )
            
            return statements_and_scores
            
        
        def publish_callable( result ):
            
            statements_and_scores = result
            
            self._total_score_slow = sum( ( score for ( statement, score ) in statements_and_scores.values() ) )
            
            self._UpdateTotalScore( finished = True )
            
            self._PopulateStatements( statements_and_scores, self._comparison_statement_names_slow )
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
        
    
    def _PopulateStatements( self, statements_and_scores, names ):
        
        for name in names:
            
            ( panel, st ) = self._comparison_statements_sts[ name ]
            
            got_data = name in statements_and_scores
            
            show_panel = got_data
            
            panel.setVisible( show_panel )
            
            if got_data:
                
                ( statement, score ) = statements_and_scores[ name ]
                
                st.setText( statement )
                
                if score > 0:
                    
                    object_name = 'HydrusValid'
                    
                elif score < 0:
                    
                    object_name = 'HydrusInvalid'
                    
                else:
                    
                    object_name = 'HydrusIndeterminate'
                    
                
                st.setObjectName( object_name )
                
                st.style().polish( st )
                
                if name == 'a_and_b_are_visual_duplicates':
                    
                    tt = f'{statement}\n\nThis uses a custom visual inspection algorithm to try to differentiate resizes/re-encodes vs recolours/alternates. It is pretty good and you can generally trust it. On edge cases, it intentionally errs on the side of false negative.'
                    st.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
                    
                elif name == 'jpeg_subsampling':
                    
                    tt = f'{statement}\n\nTo save space, jpegs can encode colour data at a lower resolution than light intensity. This is called "subsampling". You do not notice it much, but it does affect image quality, and you generally want to select the higher resolution of subsampling as the "better" of any pair. There are complicated situations where a jpeg can be subsampled and then saved again at a higher quality level (and this is one of the ways you can have a jpeg that is bloated but looks no better), but in general, know that bigger numbers are better:\n\n4:4:4 > 4:2:2 > 4:2:0.\n\nAnything that counts as "unknown" is probably worse. Truly greyscale jpegs (i.e. 8 bits per pixel) have no colour and thus no subsampling.'
                    st.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
                    
                elif name == 'jpeg_quality':
                    
                    tt = f'{statement}\n\nThis is an estimate based on metadata within the jpeg header. It is not perfect, but it is generally reliable. It will be tricked by a low quality file that is re-saved at a higher quality level.'
                    st.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
                    
                else:
                    
                    st.setToolTip( ClientGUIFunctions.WrapToolTip( statement ) )
                    
                
            
            # hackery dackery doo
            st.updateGeometry()
            panel.updateGeometry()
            
        
        # some more hackery dackery doo, along with the updateGeometry forced calls above
        # might be able to remove this if and when the layout chain here is cleaned up all the way to the window()
        self._comparison_statements_vbox.invalidate()
        self._comparison_statements_vbox.activate()
        
        # minimumsize is not immediately updated without this
        self.layout().activate()
        
        self._SizeAndPosition()
        
    
    def _UpdateTotalScore( self, finished = True ):
        
        total_score = self._total_score_fast + self._total_score_slow
        
        if total_score > 0:
            
            text = 'score: +' + HydrusNumbers.ToHumanInt( total_score )
            object_name = 'HydrusValid'
            
        elif total_score < 0:
            
            text = 'score: ' + HydrusNumbers.ToHumanInt( total_score )
            object_name = 'HydrusInvalid'
            
        else:
            
            text = 'no score difference'
            object_name = 'HydrusIndeterminate'
            
        
        if not finished:
            
            text += HC.UNICODE_ELLIPSIS
            
        
        self._comparison_statement_score_summary.setText( text )
        
        self._comparison_statement_score_summary.setObjectName( object_name )
        
        self._comparison_statement_score_summary.style().polish( self._comparison_statement_score_summary )
        
    
    def SetDuplicatePair( self, canvas_key, shown_media, comparison_media ):
        
        if canvas_key == self._canvas_key:
            
            self._current_media = shown_media
            self._comparison_media = comparison_media
            
            self._total_score_fast = 0
            self._total_score_slow = 0
            self._they_are_pixel_duplicates = False
            
            self._EnableDisableButtons()
            
            self._comparison_statement_updater_fast.update()
            
            # minimumsize is not immediately updated without this
            self.layout().activate()
            
            self._SizeAndPosition()
            
        
    
    def SetIndexString( self, canvas_key, text ):
        
        if canvas_key == self._canvas_key:
            
            self._current_index_string = text
            
            self._index_text.setText( self._current_index_string )
            
        
    
class CanvasHoverFrameTags( CanvasHoverFrame ):
    
    def __init__( self, parent, my_canvas, top_hover: CanvasHoverFrameTop, canvas_key, location_context: ClientLocation.LocationContext ):
        
        super().__init__( parent, my_canvas, canvas_key )
        
        self._top_hover = top_hover
        
        vbox = QP.VBoxLayout()
        
        self._tags = ClientGUIListBoxes.ListBoxTagsMediaHoverFrame( self, self._canvas_key, location_context )
        
        QP.AddToLayout( vbox, self._tags, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        CG.client_controller.sub( self, 'ProcessContentUpdatePackage', 'content_updates_gui' )
        
    
    def _GetIdealSizeAndPosition( self ):
        
        if CG.client_controller.new_options.GetBoolean( 'disable_tags_hover_in_media_viewer' ):
            
            return ( False, QC.QSize( 0, 0 ), QC.QPoint( 0, 0 ) )
            
        
        parent_window = self.parentWidget().window()
        
        parent_size = parent_window.size()
        
        parent_width = parent_size.width()
        parent_height = parent_size.height()
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        my_ideal_width = int( parent_width * 0.2 )
        
        my_ideal_height = parent_height
        
        should_resize = my_ideal_width != my_width or my_ideal_height != my_height
        
        ideal_size = QC.QSize( my_ideal_width, my_ideal_height )
        ideal_position = QC.QPoint( 0, 0 )
        
        return ( should_resize, ideal_size, ideal_position )
        
    
    def _ResetTags( self ):
        
        if self._current_media is not None:
            
            self._tags.SetTagsByMedia( [ self._current_media ] )
            
        
    
    def ProcessContentUpdatePackage( self, content_update_package: ClientContentUpdates.ContentUpdatePackage ):
        
        if self._current_media is not None:
            
            my_hash = self._current_media.GetHash()
            
            do_redraw = False
            
            for ( service_key, content_updates ) in content_update_package.IterateContentUpdates():
                
                if True in ( my_hash in content_update.GetHashes() for content_update in content_updates ):
                    
                    do_redraw = True
                    
                    break
                    
                
            
            if do_redraw:
                
                self._ResetTags()
                
            
        
    
    def SetMedia( self, media ):
        
        super().SetMedia( media )
        
        self._ResetTags()
        
    
    def wheelEvent( self, event ):
        
        # need the mouse test here since some weird event passing happens on mouse events on other stuff, I think because this hover is child 0 of the parent, it somehow gets 'focus'
        if self.rect().contains( self.mapFromGlobal( QG.QCursor.pos() ) ):
            
            # we do not want to send taglist wheel events up to the canvas lad
            
            event.accept()
            
            return
            
        
        CanvasHoverFrame.wheelEvent( self, event )
        
    
