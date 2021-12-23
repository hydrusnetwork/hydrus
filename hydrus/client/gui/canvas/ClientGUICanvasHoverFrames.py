import os

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client.gui import ClientGUIDragDrop
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMediaControls
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIMPV
from hydrus.client.gui import ClientGUIRatings
from hydrus.client.gui import ClientGUIScrolledPanelsEdit
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUIShortcutControls
from hydrus.client.gui import ClientGUITopLevelWindows
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientRatings

class RatingLikeCanvas( ClientGUIRatings.RatingLike ):
    
    def __init__( self, parent, service_key, canvas_key ):
        
        ClientGUIRatings.RatingLike.__init__( self, parent, service_key )
        
        self._canvas_key = canvas_key
        self._current_media = None
        self._rating_state = None
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
        name = service.GetName()
        
        self.setToolTip( name )
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HG.client_controller.sub( self, 'SetDisplayMedia', 'canvas_new_display_media' )
        
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self._current_media is not None:
            
            self._rating_state = ClientRatings.GetLikeStateFromMedia( ( self._current_media, ), self._service_key )
            
            ClientGUIRatings.DrawLike( painter, 0, 0, self._service_key, self._rating_state )
            
        
        self._dirty = False
        
    
    def EventLeftDown( self, event ):
        
        if self._current_media is not None:
            
            if self._rating_state == ClientRatings.LIKE: rating = None
            else: rating = 1
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            HG.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
            
        
    
    def EventRightDown( self, event ):
        
        if self._current_media is not None:
            
            if self._rating_state == ClientRatings.DISLIKE: rating = None
            else: rating = 0
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            HG.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is not None:
            
            for ( service_key, content_updates ) in service_keys_to_content_updates.items():
                
                for content_update in content_updates:
                    
                    ( data_type, action, row ) = content_update.ToTuple()
                    
                    if data_type == HC.CONTENT_TYPE_RATINGS:
                        
                        hashes = content_update.GetHashes()
                        
                        if HydrusData.SetsIntersect( self._hashes, hashes ):
                            
                            self._dirty = True
                            
                            self.update()
                            
                            return
                            
                        
                    
                
            
        
    
    def SetDisplayMedia( self, canvas_key, media ):
        
        if canvas_key == self._canvas_key:
            
            self._current_media = media
            
            if self._current_media is None:
                
                self._hashes = set()
                
            else:
                
                self._hashes = self._current_media.GetHashes()
                
            
            self._dirty = True
            
            self.update()
            
        
    
class RatingNumericalCanvas( ClientGUIRatings.RatingNumerical ):

    def __init__( self, parent, service_key, canvas_key ):
        
        ClientGUIRatings.RatingNumerical.__init__( self, parent, service_key )
        
        self._canvas_key = canvas_key
        self._current_media = None
        self._rating_state = None
        self._rating = None
        
        self._hashes = set()
        
        name = self._service.GetName()
        
        self.setToolTip( name )
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HG.client_controller.sub( self, 'SetDisplayMedia', 'canvas_new_display_media' )
        
    
    def _ClearRating( self ):
        
        ClientGUIRatings.RatingNumerical._ClearRating( self )
        
        if self._current_media is not None:
            
            rating = None
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            HG.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
            
        
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self._current_media is not None:
            
            ( self._rating_state, self._rating ) = ClientRatings.GetNumericalStateFromMedia( ( self._current_media, ), self._service_key )
            
            ClientGUIRatings.DrawNumerical( painter, 0, 0, self._service_key, self._rating_state, self._rating )
            
        
        self._dirty = False
        
    
    def _SetRating( self, rating ):
        
        ClientGUIRatings.RatingNumerical._SetRating( self, rating )
        
        if self._current_media is not None and rating is not None:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            HG.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is not None:
            
            for ( service_key, content_updates ) in service_keys_to_content_updates.items():
                
                for content_update in content_updates:
                    
                    ( data_type, action, row ) = content_update.ToTuple()
                    
                    if data_type == HC.CONTENT_TYPE_RATINGS:
                        
                        hashes = content_update.GetHashes()
                        
                        if HydrusData.SetsIntersect( self._hashes, hashes ):
                            
                            self._dirty = True
                            
                            self.update()
                            
                            return
                            
                        
                    
                
            
        
    
    def SetDisplayMedia( self, canvas_key, media ):
        
        if canvas_key == self._canvas_key:
            
            self._current_media = media
            
            if self._current_media is None:
                
                self._hashes = set()
                
            else:
                
                self._hashes = self._current_media.GetHashes()
                
            
            self._dirty = True
            
            self.update()
            
        
    
class CanvasHoverFrame( QW.QFrame ):
    
    def __init__( self, parent, my_canvas, canvas_key ):
        
        QW.QFrame.__init__( self, parent )
        
        self.setWindowFlags( QC.Qt.FramelessWindowHint | QC.Qt.Tool )
        
        self.setAttribute( QC.Qt.WA_ShowWithoutActivating )
        self.setAttribute( QC.Qt.WA_DeleteOnClose )
        
        self.setFrameStyle( QW.QFrame.Panel | QW.QFrame.Raised )
        self.setLineWidth( 2 )
        
        self._my_parent_tlw = parent.window()
        self._my_canvas = my_canvas
        self._canvas_key = canvas_key
        self._current_media = None
        
        self._always_on_top = False
        
        self._last_ideal_position = None
        
        self.setCursor( QG.QCursor( QC.Qt.ArrowCursor ) )
        
        self._hide_until =  None
        
        self._position_initialised = False
        
        self._my_parent_tlw.installEventFilter( self )
        
        HG.client_controller.sub( self, 'SetDisplayMedia', 'canvas_new_display_media' )
        
        HG.client_controller.gui.RegisterUIUpdateWindow( self )
        
    
    def _GetIdealSizeAndPosition( self ):
        
        raise NotImplementedError()
        
    
    def _SizeAndPosition( self, force = False ):
        
        if self.parentWidget().isVisible() or force:
            
            ( should_resize, my_ideal_size, my_ideal_position ) = self._GetIdealSizeAndPosition()
            
            if should_resize:
                
                self.resize( my_ideal_size )
                
            
            if my_ideal_position != self.pos():
                
                self.move( my_ideal_position )
                
            
            self._position_initialised = True
            
        
    
    def eventFilter( self, watched, event ):
        
        if watched == self._my_parent_tlw:
            
            if event.type() in ( QC.QEvent.Move, QC.QEvent.Resize ):
                
                self._position_initialised = False
                
            
        
        return False
        
    
    def SetDisplayMedia( self, canvas_key, media ):
        
        if canvas_key == self._canvas_key:
            
            self._current_media = media
            
        
    
    def TIMERUIUpdate( self ):
        
        if not self._position_initialised:
            
            self._SizeAndPosition()
            
        
        current_focus_tlw = QW.QApplication.activeWindow()
        
        focus_is_on_descendant = ClientGUIFunctions.IsQtAncestor( current_focus_tlw, self._my_canvas.window(), through_tlws = True )
        focus_has_right_window_type = isinstance( current_focus_tlw, ( ClientGUITopLevelWindows.FrameThatResizesWithHovers, CanvasHoverFrame ) )
        
        focus_is_good = focus_is_on_descendant and focus_has_right_window_type
        
        mouse_is_over_self_or_child = False
        
        for tlw in QW.QApplication.topLevelWidgets():
            
            if tlw == self or ClientGUIFunctions.IsQtAncestor( tlw, self, through_tlws = True ):
                
                if ClientGUIFunctions.MouseIsOverWidget( tlw ):
                    
                    mouse_is_over_self_or_child = True
                    
                    break
                    
                
            
        
        if self._always_on_top:
            
            self._SizeAndPosition()
            
            self.show()
            
            return
            
        
        if self._hide_until is not None:
            
            if HydrusData.TimeHasPassed( self._hide_until ):
                
                self._hide_until =  None
                
            else:
                
                return
                
            
        
        if self._current_media is None or not self._my_canvas.isVisible():
            
            if self.isVisible():
                
                if HG.hover_window_report_mode:
                    
                    HydrusData.ShowText( repr( self ) + ' - hiding because nothing to show or parent hidden.' )
                    
                
                self.hide()
                
            
        else:
            
            mouse_pos = QG.QCursor.pos()
            
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
            
            my_ideal_x = my_ideal_pos.x()
            my_ideal_y = my_ideal_pos.y()
            
            if my_ideal_width == -1:
                
                my_ideal_width = max( my_width, 50 )
                
            
            if my_ideal_height == -1:
                
                my_ideal_height = max( my_height, 50 )
                
            
            in_ideal_x = my_ideal_x <= mouse_x <= my_ideal_x + my_ideal_width
            in_ideal_y = my_ideal_y <= mouse_y <= my_ideal_y + my_ideal_height
            
            in_actual_x = my_x <= mouse_x <= my_x + my_width
            in_actual_y = my_y <= mouse_y <= my_y + my_height
            
            # we test both ideal and actual here because setposition is not always honoured by the OS
            # for instance, in some Linux window managers on a fullscreen view, the top taskbar is hidden, but when hover window is shown, it takes focus and causes taskbar to reappear
            # the reappearance shuffles the screen coordinates down a bit so the hover sits +20px y despite wanting to be lined up with the underlying fullscreen viewer
            # wew lad
            
            in_position = ( in_ideal_x or in_actual_x ) and ( in_ideal_y or in_actual_y )
            
            menu_open = CGC.core().MenuIsOpen()
            
            dialog_is_open = ClientGUIFunctions.DialogIsOpen()
            
            mouse_is_near_animation_bar = self._my_canvas.MouseIsNearAnimationBar()
            
            # this used to have the flash media window test to ensure mouse over flash window hid hovers going over it
            mouse_is_over_something_else_important = mouse_is_near_animation_bar
            
            hide_focus_is_good = focus_is_good or current_focus_tlw is None # don't hide if focus is either gone to another problem or temporarily sperging-out due to a click-transition or similar
            
            ready_to_show = in_position and not mouse_is_over_something_else_important and focus_is_good and not dialog_is_open and not menu_open
            ready_to_hide = not menu_open and not mouse_is_over_self_or_child and ( not in_position or dialog_is_open or not hide_focus_is_good )
            
            def get_logic_report_string():
                
                tuples = []
                
                tuples.append( ( 'mouse: ', ( mouse_x, mouse_y ) ) )
                tuples.append( ( 'winpos: ', ( my_x, my_y ) ) )
                tuples.append( ( 'ideal winpos: ', ( my_ideal_x, my_ideal_y ) ) )
                tuples.append( ( 'winsize: ', ( my_width, my_height ) ) )
                tuples.append( ( 'ideal winsize: ', ( my_ideal_width, my_ideal_height ) ) )
                tuples.append( ( 'in position: ', in_position ) )
                tuples.append( ( 'menu open: ', menu_open ) )
                tuples.append( ( 'dialog open: ', dialog_is_open ) )
                tuples.append( ( 'mouse near animation bar: ', mouse_is_near_animation_bar ) )
                tuples.append( ( 'focus is good: ', focus_is_good ) )
                tuples.append( ( 'focus is on descendant: ', focus_is_on_descendant ) )
                tuples.append( ( 'current focus tlw: ', current_focus_tlw ) )
                
                message = os.linesep * 2 + os.linesep.join( ( a + str( b ) for ( a, b ) in tuples ) )
                
                return message
                
            
            if ready_to_show:
                
                self._SizeAndPosition()
                
                if not self.isVisible():
                    
                    if HG.hover_window_report_mode:
                        
                        HydrusData.ShowText( repr( self ) + ' - showing.' + get_logic_report_string() )
                        
                    
                    self.show()
                    
                
            elif ready_to_hide:
                
                if self.isVisible():
                    
                    if HG.hover_window_report_mode:
                        
                        HydrusData.ShowText( repr( self ) + ' - hiding.' + get_logic_report_string() )
                        
                    
                    self.hide()
                    
                
            
        
    
class CanvasHoverFrameRightDuplicates( CanvasHoverFrame ):
    
    def __init__( self, parent, my_canvas, canvas_key ):
        
        CanvasHoverFrame.__init__( self, parent, my_canvas, canvas_key )
        
        self._always_on_top = True
        
        self._current_index_string = ''
        
        self._comparison_media = None
        
        self._trash_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().delete, HG.client_controller.pub, 'canvas_delete', self._canvas_key )
        self._trash_button.setToolTip( 'send to trash' )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'edit duplicate metadata merge options for \'this is better\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_BETTER ) ) )
        menu_items.append( ( 'normal', 'edit duplicate metadata merge options for \'same quality\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_SAME_QUALITY ) ) )
        
        if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            menu_items.append( ( 'normal', 'edit duplicate metadata merge options for \'alternates\' (advanced!)', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_ALTERNATE ) ) )
            
        
        menu_items.append( ( 'separator', None, None, None ) )
        menu_items.append( ( 'normal', 'edit background lighten/darken switch intensity', 'edit how much the background will brighten or darken as you switch between the pair', self._EditBackgroundSwitchIntensity ) )
        
        self._cog_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().cog, menu_items )
        
        close_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().stop, HG.client_controller.pub, 'canvas_close', self._canvas_key )
        close_button.setToolTip( 'close filter' )
        
        self._back_a_pair = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().first, HG.client_controller.pub, 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_BACK ), self._canvas_key )
        self._back_a_pair.SetToolTipWithShortcuts( 'go back a pair', CAC.SIMPLE_DUPLICATE_FILTER_BACK )
        
        self._index_text = ClientGUICommon.BetterStaticText( self, 'index' )
        
        self._next_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().pair, HG.client_controller.pub, 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_NEXT ), self._canvas_key )
        self._next_button.SetToolTipWithShortcuts( 'next', CAC.SIMPLE_VIEW_NEXT )
        
        self._skip_a_pair = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().last, HG.client_controller.pub, 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_SKIP ), self._canvas_key )
        self._skip_a_pair.SetToolTipWithShortcuts( 'show a different pair', CAC.SIMPLE_DUPLICATE_FILTER_SKIP )
        
        command_button_vbox = QP.VBoxLayout()
        
        dupe_boxes = []
        
        dupe_commands = []
        
        dupe_commands.append( ( 'this is better, and delete the other', 'Set that the current file you are looking at is better than the other in the pair, and set the other file to be deleted.', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_AND_DELETE_OTHER ) ) )
        dupe_commands.append( ( 'this is better, but keep both', 'Set that the current file you are looking at is better than the other in the pair, but keep both files.', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_BUT_KEEP_BOTH ) ) )
        dupe_commands.append( ( 'they are the same quality', 'Set that the two files are duplicates of very similar quality.', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_EXACTLY_THE_SAME ) ) )
        
        dupe_boxes.append( ( 'they are duplicates', dupe_commands ) )
        
        dupe_commands = []
        
        dupe_commands.append( ( 'they are related alternates', 'Set that the files are not duplicates, but that one is derived from the other or that they are both descendants of a common ancestor.', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_ALTERNATES ) ) )
        dupe_commands.append( ( 'they are not related', 'Set that the files are not duplicates or otherwise related--that this potential pair is a false positive match.', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_FALSE_POSITIVE ) ) )
        dupe_commands.append( ( 'custom action', 'Choose one of the other actions but customise the merge and delete options for this specific decision.', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_CUSTOM_ACTION ) ) )
        
        dupe_boxes.append( ( 'other', dupe_commands ) )
        
        for ( panel_name, dupe_commands ) in dupe_boxes:
            
            button_panel = ClientGUICommon.StaticBox( self, panel_name )
            
            for ( label, tooltip, command ) in dupe_commands:
                
                command_button = ClientGUICommon.BetterButton( button_panel, label, HG.client_controller.pub, 'canvas_application_command', command, self._canvas_key )
                
                command_button.SetToolTipWithShortcuts( tooltip, command.GetSimpleAction() )
                
                button_panel.Add( command_button, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            QP.AddToLayout( command_button_vbox, button_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self._comparison_statements_vbox = QP.VBoxLayout()
        
        self._comparison_statement_names = [ 'filesize', 'resolution', 'ratio', 'mime', 'num_tags', 'time_imported', 'jpeg_quality', 'pixel_duplicates' ]
        
        self._comparison_statements_sts = {}
        
        for name in self._comparison_statement_names:
            
            panel = QW.QWidget( self )
            
            st = ClientGUICommon.BetterStaticText( panel, 'init' )
            
            self._comparison_statements_sts[ name ] = ( panel, st )
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, st, CC.FLAGS_CENTER )
            
            panel.setLayout( hbox )
            
            panel.setVisible( False )
            
            QP.AddToLayout( self._comparison_statements_vbox, panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        #
        
        top_button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( top_button_hbox, self._next_button, CC.FLAGS_EXPAND_BOTH_WAYS )
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
        
        HG.client_controller.sub( self, 'SetDuplicatePair', 'canvas_new_duplicate_pair' )
        HG.client_controller.sub( self, 'SetIndexString', 'canvas_new_index_string' )
        
    
    def _EditBackgroundSwitchIntensity( self ):
        
        new_options = HG.client_controller.new_options
        
        value = new_options.GetNoneableInteger( 'duplicate_background_switch_intensity' )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit lighten/darken intensity' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditNoneableIntegerPanel( dlg, value, message = 'intensity: ', none_phrase = 'do not change', min = 1, max = 9 )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                new_value = panel.GetValue()
                
                new_options.SetNoneableInteger( 'duplicate_background_switch_intensity', new_value )
                
            
        
    
    def _EditMergeOptions( self, duplicate_type ):
        
        new_options = HG.client_controller.new_options
        
        duplicate_action_options = new_options.GetDuplicateActionOptions( duplicate_type )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit duplicate merge options' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditDuplicateActionOptionsPanel( dlg, duplicate_type, duplicate_action_options )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                duplicate_action_options = panel.GetValue()
                
                new_options.SetDuplicateActionOptions( duplicate_type, duplicate_action_options )
                
            
        
    
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
        ideal_position = ClientGUIFunctions.ClientToScreen( parent_window, QC.QPoint( int( parent_width - my_ideal_width ), int( parent_height * 0.3 ) ) )
        
        return ( should_resize, ideal_size, ideal_position )
        
    
    def _ResetComparisonStatements( self ):
        
        statements_and_scores = ClientMedia.GetDuplicateComparisonStatements( self._current_media, self._comparison_media )
        
        for name in self._comparison_statement_names:
            
            ( panel, st ) = self._comparison_statements_sts[ name ]
            
            got_data = name in statements_and_scores
            
            show_panel = got_data
            
            if panel.isVisible() != show_panel:
                
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
                
            
        
    
    def wheelEvent( self, event ):
        
        QW.QApplication.sendEvent( self.parentWidget(), event )
        
    
    def SetDuplicatePair( self, canvas_key, shown_media, comparison_media ):
        
        if canvas_key == self._canvas_key:
            
            self._current_media = shown_media
            self._comparison_media = comparison_media
            
            self._ResetComparisonStatements()
            
            # minimumsize is not immediately updated without this
            self.layout().activate()
            
            self._SizeAndPosition( force = True )
            
        
    
    def SetIndexString( self, canvas_key, text ):
        
        if canvas_key == self._canvas_key:
            
            self._current_index_string = text
            
            self._index_text.setText( self._current_index_string )
            
        
    
class CanvasHoverFrameTop( CanvasHoverFrame ):
    
    def __init__( self, parent, my_canvas, canvas_key ):
        
        CanvasHoverFrame.__init__( self, parent, my_canvas, canvas_key )
        
        self._current_zoom = 1.0
        self._current_index_string = ''
        
        self._top_hbox = QP.HBoxLayout()
        
        self._title_text = ClientGUICommon.BetterStaticText( self, 'title', ellipsize_end = True )
        self._info_text = ClientGUICommon.BetterStaticText( self, 'info', ellipsize_end = True )
        
        self._title_text.setAlignment( QC.Qt.AlignHCenter | QC.Qt.AlignVCenter )
        self._info_text.setAlignment( QC.Qt.AlignHCenter | QC.Qt.AlignVCenter )
        
        self._PopulateLeftButtons()
        self._top_hbox.addStretch( 1 )
        self._PopulateCenterButtons()
        self._top_hbox.addStretch( 1 )
        self._PopulateRightButtons()
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._top_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._title_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._info_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HG.client_controller.sub( self, 'SetCurrentZoom', 'canvas_new_zoom' )
        HG.client_controller.sub( self, 'SetIndexString', 'canvas_new_index_string' )
        
    
    def _Archive( self ):
        
        if self._current_media.HasInbox():
            
            command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_FILE )
            
        else:
            
            command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_INBOX_FILE )
            
        
        HG.client_controller.pub( 'canvas_application_command', command, self._canvas_key )
        
    
    def _GetIdealSizeAndPosition( self ):
        
        # clip this and friends to availableScreenGeometry for size and position, not rely 100% on parent
        
        parent_window = self.parentWidget().window()
        
        parent_size = parent_window.size()
        
        parent_width = parent_size.width()
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        my_ideal_width = max( int( parent_width * 0.6 ), self.sizeHint().width() )
        
        my_ideal_height = self.sizeHint().height()
        
        should_resize = my_ideal_width != my_width or my_ideal_height != my_height
        
        ideal_size = QC.QSize( my_ideal_width, my_ideal_height )
        ideal_position = ClientGUIFunctions.ClientToScreen( parent_window, QC.QPoint( int( parent_width * 0.2 ), 0 ) )
        
        return ( should_resize, ideal_size, ideal_position )
        
    
    def _PopulateCenterButtons( self ):
        
        self._archive_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().archive, self._Archive )
        
        self._trash_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().delete, HG.client_controller.pub, 'canvas_delete', self._canvas_key )
        self._trash_button.setToolTip( 'send to trash' )
        
        self._delete_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().trash_delete, HG.client_controller.pub, 'canvas_delete', self._canvas_key )
        self._delete_button.setToolTip( 'delete completely' )
        
        self._undelete_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().undelete, HG.client_controller.pub, 'canvas_undelete', self._canvas_key )
        self._undelete_button.setToolTip( 'undelete' )
        
        QP.AddToLayout( self._top_hbox, self._archive_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_hbox, self._trash_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_hbox, self._delete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_hbox, self._undelete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
    def _PopulateLeftButtons( self ):
        
        self._index_text = ClientGUICommon.BetterStaticText( self, 'index' )
        
        QP.AddToLayout( self._top_hbox, self._index_text, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
    def _PopulateRightButtons( self ):
        
        self._zoom_text = ClientGUICommon.BetterStaticText( self, 'zoom' )
        
        zoom_in = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().zoom_in, HG.client_controller.pub, 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ZOOM_IN_VIEWER_CENTER ), self._canvas_key )
        zoom_in.SetToolTipWithShortcuts( 'zoom in', CAC.SIMPLE_ZOOM_IN )
        
        zoom_out = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().zoom_out, HG.client_controller.pub, 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ZOOM_OUT_VIEWER_CENTER ), self._canvas_key )
        zoom_out.SetToolTipWithShortcuts( 'zoom out', CAC.SIMPLE_ZOOM_OUT )
        
        zoom_switch = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().zoom_switch, HG.client_controller.pub, 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM_VIEWER_CENTER ), self._canvas_key )
        zoom_switch.SetToolTipWithShortcuts( 'zoom switch', CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM )
        
        self._volume_control = ClientGUIMediaControls.VolumeControl( self, ClientGUICommon.CANVAS_MEDIA_VIEWER )
        
        if not ClientGUIMPV.MPV_IS_AVAILABLE:
            
            self._volume_control.hide()
            
        
        shortcuts = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().keyboard, self._ShowShortcutMenu )
        shortcuts.setToolTip( 'shortcuts' )
        
        fullscreen_switch = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().fullscreen_switch, HG.client_controller.pub, 'canvas_fullscreen_switch', self._canvas_key )
        fullscreen_switch.setToolTip( 'fullscreen switch' )
        
        if HC.PLATFORM_MACOS:
            
            fullscreen_switch.hide()
            
        
        open_externally = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().open_externally, HG.client_controller.pub, 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM ), self._canvas_key )
        open_externally.SetToolTipWithShortcuts( 'open externally', CAC.SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM )
        
        drag_button = QW.QPushButton( self )
        drag_button.setIcon( QG.QIcon( CC.global_pixmaps().drag ) )
        drag_button.setIconSize( CC.global_pixmaps().drag.size() )
        drag_button.setToolTip( 'drag from here to export file' )
        drag_button.pressed.connect( self.EventDragButton )
        
        close = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().stop, HG.client_controller.pub, 'canvas_close', self._canvas_key )
        close.setToolTip( 'close' )
        
        QP.AddToLayout( self._top_hbox, self._zoom_text, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_hbox, zoom_in, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_hbox, zoom_out, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_hbox, zoom_switch, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_hbox, self._volume_control, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_hbox, shortcuts, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_hbox, fullscreen_switch, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_hbox, open_externally, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_hbox, drag_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_hbox, close, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
    def _ResetArchiveButton( self ):
        
        if self._current_media.HasInbox():
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._archive_button, CC.global_pixmaps().archive )
            self._archive_button.setToolTip( 'archive' )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._archive_button, CC.global_pixmaps().to_inbox )
            
            self._archive_button.setToolTip( 'return to inbox' )
            
        
    
    def _ResetButtons( self ):
        
        if self._current_media is not None:
            
            self._ResetArchiveButton()
            
            locations_manager = self._current_media.GetLocationsManager()
            
            if CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent():
                
                self._trash_button.show()
                self._delete_button.hide()
                self._undelete_button.hide()
                
            elif locations_manager.IsTrashed():
                
                self._trash_button.hide()
                self._delete_button.show()
                self._undelete_button.show()
                
            
        
    
    def _ResetText( self ):
        
        if self._current_media is None:
            
            self._title_text.hide()
            self._info_text.hide()
            
        else:
            
            label = self._current_media.GetTitleString()
            
            if len( label ) > 0:
                
                self._title_text.setText( label )
                
                self._title_text.show()
                
            else: self._title_text.hide()
            
            lines = self._current_media.GetPrettyInfoLines()
            
            label = ' | '.join( lines )
            
            self._info_text.setText( label )
            
            self._info_text.show()
            
        
    
    def _FlipActiveDefaultCustomShortcut( self, name ):
        
        new_options = HG.client_controller.new_options
        
        default_media_viewer_custom_shortcuts = list( new_options.GetStringList( 'default_media_viewer_custom_shortcuts' ) )
        
        if name in default_media_viewer_custom_shortcuts:
            
            default_media_viewer_custom_shortcuts.remove( name )
            
        else:
            
            default_media_viewer_custom_shortcuts.append( name )
            
            default_media_viewer_custom_shortcuts.sort()
            
        
        new_options.SetStringList( 'default_media_viewer_custom_shortcuts', default_media_viewer_custom_shortcuts )
        
    
    def _ShowShortcutMenu( self ):
        
        all_shortcut_names = HG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET )
        
        custom_shortcuts_names = [ name for name in all_shortcut_names if name not in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES ]
        
        menu = QW.QMenu()

        ClientGUIMenus.AppendMenuItem( menu, 'edit shortcuts', 'edit your sets of shortcuts, and change what shortcuts are currently active on this media viewer', ClientGUIShortcutControls.ManageShortcuts, self )
        
        if len( custom_shortcuts_names ) > 0:
            
            my_canvas_active_custom_shortcuts = self._my_canvas.GetActiveCustomShortcutNames()
            default_media_viewer_custom_shortcuts = HG.client_controller.new_options.GetStringList( 'default_media_viewer_custom_shortcuts' )
            
            current_menu = QW.QMenu( menu )
            
            for name in custom_shortcuts_names:
                
                ClientGUIMenus.AppendMenuCheckItem( current_menu, name, 'turn this shortcut set on/off', name in my_canvas_active_custom_shortcuts, self._my_canvas.FlipActiveCustomShortcutName, name )
                
            
            ClientGUIMenus.AppendMenu( menu, current_menu, 'set current shortcuts' )
            
            defaults_menu = QW.QMenu( menu )
            
            for name in custom_shortcuts_names:
                
                ClientGUIMenus.AppendMenuCheckItem( defaults_menu, name, 'turn this shortcut set on/off by default', name in default_media_viewer_custom_shortcuts, self._FlipActiveDefaultCustomShortcut, name )
                
            
            ClientGUIMenus.AppendMenu( menu, defaults_menu, 'set default shortcuts' )
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def EventDragButton( self ):
        
        if self._current_media is None:
            
            return True # was: event.ignore()
            
        
        page_key = None
        
        media = [ self._current_media ]
        
        alt_down = QW.QApplication.keyboardModifiers() & QC.Qt.AltModifier
        
        result = ClientGUIDragDrop.DoFileExportDragDrop( self, page_key, media, alt_down )
        
        if result != QC.Qt.IgnoreAction:
            
            HG.client_controller.pub( 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_PAUSE_MEDIA ), self._canvas_key )
            
        
    
    def resizeEvent( self, event ):
        
        # reset wrap width
        self._ResetText()
        
        event.ignore()
        
    
    def wheelEvent( self, event ):
        
        QW.QApplication.sendEvent( self.parentWidget(), event )
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is not None:
            
            my_hash = self._current_media.GetHash()
            
            do_redraw = False
            
            for ( service_key, content_updates ) in service_keys_to_content_updates.items():
                
                if True in ( my_hash in content_update.GetHashes() for content_update in content_updates ):
                    
                    do_redraw = True
                    
                    break
                    
                
            
            if do_redraw:
                
                self._ResetText()
                self._ResetButtons()
                
            
        
    
    def SetCurrentZoom( self, canvas_key, zoom ):
        
        if canvas_key == self._canvas_key:
            
            self._current_zoom = zoom
            
            label = ClientData.ConvertZoomToPercentage( self._current_zoom )
            
            self._zoom_text.setText( label )
            
        
    
    def SetDisplayMedia( self, canvas_key, media ):
        
        if canvas_key == self._canvas_key:
            
            CanvasHoverFrame.SetDisplayMedia( self, canvas_key, media )
            
            self._ResetText()
            
            self._ResetButtons()
            
            # minimumsize is not immediately updated without this
            self.layout().activate()
            
            self._SizeAndPosition( force = True )
            
        
    
    def SetIndexString( self, canvas_key, text ):
        
        if canvas_key == self._canvas_key:
            
            self._current_index_string = text
            
            self._index_text.setText( self._current_index_string )
            
        
    
class CanvasHoverFrameTopArchiveDeleteFilter( CanvasHoverFrameTop ):
    
    def _Archive( self ):
        
        HG.client_controller.pub( 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_FILE ), self._canvas_key )
        
    
    def _PopulateLeftButtons( self ):
        
        self._back_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().previous, HG.client_controller.pub, 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_BACK ), self._canvas_key )
        self._back_button.SetToolTipWithShortcuts( 'back', CAC.SIMPLE_ARCHIVE_DELETE_FILTER_BACK )
        
        QP.AddToLayout( self._top_hbox, self._back_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        CanvasHoverFrameTop._PopulateLeftButtons( self )
        
        self._skip_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().next_bmp, HG.client_controller.pub, 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_DELETE_FILTER_SKIP ), self._canvas_key )
        self._skip_button.SetToolTipWithShortcuts( 'skip', CAC.SIMPLE_ARCHIVE_DELETE_FILTER_SKIP )
        
        QP.AddToLayout( self._top_hbox, self._skip_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
    def _ResetArchiveButton( self ):
        
        ClientGUIFunctions.SetBitmapButtonBitmap( self._archive_button, CC.global_pixmaps().archive )
        self._archive_button.setToolTip( 'archive' )
        
    
class CanvasHoverFrameTopNavigable( CanvasHoverFrameTop ):
    
    def _PopulateLeftButtons( self ):
        
        self._previous_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().previous, HG.client_controller.pub, 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_PREVIOUS ), self._canvas_key )
        self._previous_button.SetToolTipWithShortcuts( 'previous', CAC.SIMPLE_VIEW_PREVIOUS )
        
        self._index_text = ClientGUICommon.BetterStaticText( self, 'index' )
        
        self._next_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().next_bmp, HG.client_controller.pub, 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_NEXT ), self._canvas_key )
        self._next_button.SetToolTipWithShortcuts( 'next', CAC.SIMPLE_VIEW_NEXT )
        
        QP.AddToLayout( self._top_hbox, self._previous_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_hbox, self._index_text, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._top_hbox, self._next_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
class CanvasHoverFrameTopDuplicatesFilter( CanvasHoverFrameTopNavigable ):
    
    def _PopulateLeftButtons( self ):
        
        self._first_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().first, HG.client_controller.pub, 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_BACK ), self._canvas_key )
        self._first_button.SetToolTipWithShortcuts( 'go back a pair', CAC.SIMPLE_DUPLICATE_FILTER_BACK )
        
        QP.AddToLayout( self._top_hbox, self._first_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        CanvasHoverFrameTopNavigable._PopulateLeftButtons( self )
        
        self._last_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().last, HG.client_controller.pub, 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_DUPLICATE_FILTER_SKIP ), self._canvas_key )
        self._last_button.SetToolTipWithShortcuts( 'show a different pair', CAC.SIMPLE_DUPLICATE_FILTER_SKIP )
        
        QP.AddToLayout( self._top_hbox, self._last_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
class CanvasHoverFrameTopNavigableList( CanvasHoverFrameTopNavigable ):
    
    def _PopulateLeftButtons( self ):
        
        self._first_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().first, HG.client_controller.pub, 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_FIRST ), self._canvas_key )
        self._first_button.SetToolTipWithShortcuts( 'first', CAC.SIMPLE_VIEW_FIRST )
        
        QP.AddToLayout( self._top_hbox, self._first_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        CanvasHoverFrameTopNavigable._PopulateLeftButtons( self )
        
        self._last_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().last, HG.client_controller.pub, 'canvas_application_command', CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_VIEW_LAST ), self._canvas_key )
        self._last_button.SetToolTipWithShortcuts( 'last', CAC.SIMPLE_VIEW_LAST )
        
        QP.AddToLayout( self._top_hbox, self._last_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
class CanvasHoverFrameTopRight( CanvasHoverFrame ):
    
    def __init__( self, parent, my_canvas, top_hover: CanvasHoverFrameTop, canvas_key ):
        
        CanvasHoverFrame.__init__( self, parent, my_canvas, canvas_key )
        
        self._top_hover = top_hover
        
        vbox = QP.VBoxLayout()
        
        self._icon_panel = QW.QWidget( self )
        
        self._trash_icon = ClientGUICommon.BufferedWindowIcon( self._icon_panel, CC.global_pixmaps().trash )
        self._inbox_icon = ClientGUICommon.BufferedWindowIcon( self._icon_panel, CC.global_pixmaps().inbox, click_callable = self._Archive )
        self._notes_icon = ClientGUICommon.BufferedWindowIcon( self._icon_panel, CC.global_pixmaps().notes, click_callable = self._EditNotes )
        
        icon_hbox = QP.HBoxLayout( spacing = 0 )
        
        icon_hbox.addStretch( 1 )
        QP.AddToLayout( icon_hbox, self._inbox_icon, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( icon_hbox, self._trash_icon, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( icon_hbox, self._notes_icon, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._icon_panel.setLayout( icon_hbox )
        
        # repo strings
        
        self._file_repos = QP.MakeQLabelWithAlignment( '', self, QC.Qt.AlignRight | QC.Qt.AlignVCenter )
        
        # urls
        
        self._last_seen_urls = []
        self._urls_vbox = QP.VBoxLayout()
        
        # likes
        
        like_hbox = QP.HBoxLayout( spacing = 0 )
        
        like_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, ) )
        
        if len( like_services ) > 0:
            
            like_hbox.addStretch( 1 )
            
        
        for service in like_services:
            
            service_key = service.GetServiceKey()
            
            control = RatingLikeCanvas( self, service_key, canvas_key )
            
            QP.AddToLayout( like_hbox, control, CC.FLAGS_NONE )
            
        
        # each numerical one in turn
        
        QP.AddToLayout( vbox, like_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        numerical_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_RATING_NUMERICAL, ) )
        
        for service in numerical_services:
            
            service_key = service.GetServiceKey()
            
            control = RatingNumericalCanvas( self, service_key, canvas_key )
            
            QP.AddToLayout( vbox, control, CC.FLAGS_NONE )
            
            vbox.setAlignment( control, QC.Qt.AlignRight )
            
        
        QP.AddToLayout( vbox, self._icon_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._file_repos, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._urls_vbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        self._ResetData()
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        
    
    def _Archive( self ):
        
        if self._current_media.HasInbox():
            
            command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_ARCHIVE_FILE )
            
        else:
            
            command = CAC.ApplicationCommand.STATICCreateSimpleCommand( CAC.SIMPLE_INBOX_FILE )
            
        
        HG.client_controller.pub( 'canvas_application_command', command, self._canvas_key )
        
    
    def _EditNotes( self ):
        
        HG.client_controller.pub( 'canvas_manage_notes', self._canvas_key )
        
    
    def _GetIdealSizeAndPosition( self ):
        
        parent_window = self.parentWidget().window()
        
        parent_size = parent_window.size()
        
        parent_width = parent_size.width()
        
        my_size = self.size()
        
        my_width = my_size.width()
        my_height = my_size.height()
        
        # don't use .rect() here, it (sometimes) isn't updated on a hidden window until next show, I think
        top_hover_bottom_right = QC.QPoint( self._top_hover.x() + self._top_hover.width(), self._top_hover.y() + self._top_hover.height() )
        
        width_beside_top_hover = ClientGUIFunctions.ClientToScreen( parent_window, parent_window.rect().topRight() ).x() - top_hover_bottom_right.x()
        
        my_ideal_width = max( self.sizeHint().width(), width_beside_top_hover )
        
        my_ideal_height = self.sizeHint().height()
        
        should_resize = my_ideal_width != my_width or my_ideal_height != my_height
        
        ideal_size = QC.QSize( my_ideal_width, my_ideal_height )
        
        ideal_position = ClientGUIFunctions.ClientToScreen( parent_window, QC.QPoint( int( parent_width - my_ideal_width ), 0 ) )
        
        if top_hover_bottom_right.x() > ideal_position.x():
            
            ideal_position.setY( top_hover_bottom_right.y() )
            
        
        return ( should_resize, ideal_size, ideal_position )
        
    
    def _ResetData( self ):
        
        if self._current_media is not None:
            
            has_inbox = self._current_media.HasInbox()
            has_trash = self._current_media.GetLocationsManager().IsTrashed()
            has_notes = self._current_media.HasNotes()
            
            if has_inbox or has_trash or has_notes:
                
                self._icon_panel.show()
                
                if has_inbox:
                    
                    self._inbox_icon.show()
                    
                else:
                    
                    self._inbox_icon.hide()
                    
                
                if has_trash:
                    
                    self._trash_icon.show()
                    
                else:
                    
                    self._trash_icon.hide()
                    
                
                if has_notes:
                    
                    self._notes_icon.show()
                    
                else:
                    
                    self._notes_icon.hide()
                    
                
            else:
                
                self._icon_panel.setVisible( False )
                
            
            remote_strings = self._current_media.GetLocationsManager().GetRemoteLocationStrings()
            
            if len( remote_strings ) == 0:
                
                self._file_repos.hide()
                
            else:
                
                remote_string = os.linesep.join( remote_strings )
                
                self._file_repos.setText( remote_string )
                
                self._file_repos.show()
                
            
            # urls
            
            urls = self._current_media.GetLocationsManager().GetURLs()
            
            if urls != self._last_seen_urls:
                
                self._last_seen_urls = list( urls )
                
                QP.ClearLayout( self._urls_vbox, delete_widgets = True )
                
                url_tuples = HG.client_controller.network_engine.domain_manager.ConvertURLsToMediaViewerTuples( urls )
                
                for ( display_string, url ) in url_tuples:
                    
                    link = ClientGUICommon.BetterHyperLink( self, display_string, url )
                    
                    link.setAlignment( QC.Qt.AlignRight )
                    
                    QP.AddToLayout( self._urls_vbox, link, CC.FLAGS_EXPAND_PERPENDICULAR )
                    
                
            
        
        self._SizeAndPosition()
        
    
    def wheelEvent( self, event ):
        
        QW.QApplication.sendEvent( self.parentWidget(), event )
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is not None:
            
            my_hash = self._current_media.GetHash()
            
            do_redraw = False
            
            for ( service_key, content_updates ) in service_keys_to_content_updates.items():
                
                # ratings updates do not change the shape of this hover but file changes of several kinds do
                
                if True in ( my_hash in content_update.GetHashes() for content_update in content_updates if content_update.GetDataType() == HC.CONTENT_TYPE_FILES ):
                    
                    do_redraw = True
                    
                    break
                    
                
            
            if do_redraw:
                
                self._ResetData()
                
            
        
    
    def SetDisplayMedia( self, canvas_key, media ):
        
        if canvas_key == self._canvas_key:
            
            CanvasHoverFrame.SetDisplayMedia( self, canvas_key, media )
            
            self._ResetData()
            
            # size is not immediately updated without this
            self.layout().activate()
            
            self._SizeAndPosition( force = True )
            
        
    
class CanvasHoverFrameTags( CanvasHoverFrame ):
    
    def __init__( self, parent, my_canvas, top_hover: CanvasHoverFrameTop, canvas_key ):
        
        CanvasHoverFrame.__init__( self, parent, my_canvas, canvas_key )
        
        self._top_hover = top_hover
        
        vbox = QP.VBoxLayout()
        
        self._tags = ClientGUIListBoxes.ListBoxTagsMediaHoverFrame( self, self._canvas_key )
        
        QP.AddToLayout( vbox, self._tags, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        
    
    def _GetIdealSizeAndPosition( self ):
        
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
        ideal_position = ClientGUIFunctions.ClientToScreen( parent_window, QC.QPoint( 0, 0 ) )
        
        return ( should_resize, ideal_size, ideal_position )
        
    
    def _ResetTags( self ):
        
        if self._current_media is not None:
            
            self._tags.SetTagsByMedia( [ self._current_media ] )
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is not None:
            
            my_hash = self._current_media.GetHash()
            
            do_redraw = False
            
            for ( service_key, content_updates ) in service_keys_to_content_updates.items():
                
                if True in ( my_hash in content_update.GetHashes() for content_update in content_updates ):
                    
                    do_redraw = True
                    
                    break
                    
                
            
            if do_redraw:
                
                self._ResetTags()
                
            
        
    
    def SetDisplayMedia( self, canvas_key, media ):
        
        if canvas_key == self._canvas_key:
            
            CanvasHoverFrame.SetDisplayMedia( self, canvas_key, media )
            
            self._ResetTags()
            
        
    
