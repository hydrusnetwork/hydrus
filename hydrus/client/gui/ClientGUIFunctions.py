import collections

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.client import ClientTags
from hydrus.client.gui import QtPorting as QP

def ApplyContentApplicationCommandToMedia( parent, command, media ):
    
    data = command.GetData()
    
    ( service_key, content_type, action, value ) = data
    
    try:
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
    except HydrusExceptions.DataMissing:
        
        command_processed = False
        
        return command_processed
        
    
    service_type = service.GetServiceType()
    
    hashes = set()
    
    for m in media:
        
        hashes.add( m.GetHash() )
        
    
    if service_type in HC.REAL_TAG_SERVICES:
        
        tag = value
        
        can_add = False
        can_pend = False
        can_delete = False
        can_petition = True
        can_rescind_pend = False
        can_rescind_petition = False
        
        for m in media:
            
            tags_manager = m.GetTagsManager()
            
            current = tags_manager.GetCurrent( service_key, ClientTags.TAG_DISPLAY_STORAGE )
            pending = tags_manager.GetPending( service_key, ClientTags.TAG_DISPLAY_STORAGE )
            petitioned = tags_manager.GetPetitioned( service_key, ClientTags.TAG_DISPLAY_STORAGE )
            
            if tag not in current:
                
                can_add = True
                
            
            if tag not in current and tag not in pending:
                
                can_pend = True
                
            
            if tag in current and action == HC.CONTENT_UPDATE_FLIP:
                
                can_delete = True
                
            
            if tag in current and tag not in petitioned and action == HC.CONTENT_UPDATE_FLIP:
                
                can_petition = True
                
            
            if tag in pending and action == HC.CONTENT_UPDATE_FLIP:
                
                can_rescind_pend = True
                
            
            if tag in petitioned:
                
                can_rescind_petition = True
                
            
        
        reason = None
        
        if service_type == HC.LOCAL_TAG:
            
            tags = [ tag ]
            
            if can_add:
                
                content_update_action = HC.CONTENT_UPDATE_ADD
                
                tag_parents_manager = HG.client_controller.tag_parents_manager
                
                parents = tag_parents_manager.GetParents( service_key, tag )
                
                tags.extend( parents )
                
            elif can_delete:
                
                content_update_action = HC.CONTENT_UPDATE_DELETE
                
            else:
                
                return True
                
            
            rows = [ ( tag, hashes ) for tag in tags ]
            
        else:
            
            if can_rescind_petition:
                
                content_update_action = HC.CONTENT_UPDATE_RESCIND_PETITION
                
                rows = [ ( tag, hashes ) ]
                
            elif can_pend:
                
                tags = [ tag ]
                
                content_update_action = HC.CONTENT_UPDATE_PEND
                
                tag_parents_manager = HG.client_controller.tag_parents_manager
                
                parents = tag_parents_manager.GetParents( service_key, tag )
                
                tags.extend( parents )
                
                rows = [ ( tag, hashes ) for tag in tags ]
                
            elif can_rescind_pend:
                
                content_update_action = HC.CONTENT_UPDATE_RESCIND_PEND
                
                rows = [ ( tag, hashes ) ]
                
            elif can_petition:
                
                message = 'Enter a reason for this tag to be removed. A janitor will review your petition.'
                
                from hydrus.client.gui import ClientGUIDialogs
                
                with ClientGUIDialogs.DialogTextEntry( parent, message ) as dlg:
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        content_update_action = HC.CONTENT_UPDATE_PETITION
                        
                        reason = dlg.GetValue()
                        
                        rows = [ ( tag, hashes ) ]
                        
                    else:
                        
                        return True
                        
                    
                
            else:
                
                return True
                
            
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_update_action, row, reason = reason ) for row in rows ]
        
    elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
        
        if action in ( HC.CONTENT_UPDATE_SET, HC.CONTENT_UPDATE_FLIP ):
            
            rating = value
            
            can_set = False
            can_unset = False
            
            for m in media:
                
                ratings_manager = m.GetRatingsManager()
                
                current_rating = ratings_manager.GetRating( service_key )
                
                if current_rating == rating and action == HC.CONTENT_UPDATE_FLIP:
                    
                    can_unset = True
                    
                else:
                    
                    can_set = True
                    
                
            
            if can_set:
                
                row = ( rating, hashes )
                
            elif can_unset:
                
                row = ( None, hashes )
                
            else:
                
                return True
                
            
            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, row ) ]
            
        elif action in ( HC.CONTENT_UPDATE_INCREMENT, HC.CONTENT_UPDATE_DECREMENT ):
            
            if service_type == HC.LOCAL_RATING_NUMERICAL:
                
                if action == HC.CONTENT_UPDATE_INCREMENT:
                    
                    direction = 1
                    initialisation_rating = 0.0
                    
                elif action == HC.CONTENT_UPDATE_DECREMENT:
                    
                    direction = -1
                    initialisation_rating = 1.0
                    
                
                num_stars = service.GetNumStars()
                
                if service.AllowZero():
                    
                    num_stars += 1
                    
                
                one_star_value = 1.0 / ( num_stars - 1 )
                
                ratings_to_hashes = collections.defaultdict( set )
                
                for m in media:
                    
                    ratings_manager = m.GetRatingsManager()
                    
                    current_rating = ratings_manager.GetRating( service_key )
                    
                    if current_rating is None:
                        
                        new_rating = initialisation_rating
                        
                    else:
                        
                        new_rating = current_rating + ( one_star_value * direction )
                        
                        new_rating = max( min( new_rating, 1.0 ), 0.0 )
                        
                    
                    if current_rating != new_rating:
                        
                        ratings_to_hashes[ new_rating ].add( m.GetHash() )
                        
                    
                
                content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, hashes ) ) for ( rating, hashes ) in ratings_to_hashes.items() ]
                
            else:
                
                return True
                
            
        
    else:
        
        return False
        
    
    if len( content_updates ) > 0:
        
        HG.client_controller.Write( 'content_updates', { service_key : content_updates } )
        
    
    return True
    
def ClientToScreen( win: QW.QWidget, pos: QC.QPoint ) -> QC.QPoint:
    
    tlw = win.window()
    
    if win.isVisible() and tlw.isVisible():
        
        return win.mapToGlobal( pos )
        
    else:
        
        return QC.QPoint( 50, 50 )
        
    

MAGIC_TEXT_PADDING = 1.1

def ColourIsBright( colour: QG.QColor ):
    
    it_is_bright = colour.valueF() > 0.75
    
    return it_is_bright
    
def ColourIsGreyish( colour: QG.QColor ):
    
    it_is_greyish = colour.hsvSaturationF() < 0.12
    
    return it_is_greyish
    
def ConvertTextToPixels( window, char_dimensions ):
    
    ( char_cols, char_rows ) = char_dimensions
    
    return ( int( window.fontMetrics().boundingRect( char_cols * 'x' ).width() * MAGIC_TEXT_PADDING ), int( char_rows * window.fontMetrics().height() * MAGIC_TEXT_PADDING ) )
    
def ConvertTextToPixelWidth( window, char_cols ):
    
    return int( window.fontMetrics().boundingRect( char_cols * 'x' ).width() * MAGIC_TEXT_PADDING )
    
def DialogIsOpen():
    
    tlws = QW.QApplication.topLevelWidgets()
    
    for tlw in tlws:
        
        if isinstance( tlw, QP.Dialog ) and tlw.isModal():
            
            return True
            
        
    
    return False
    
def EscapeMnemonics( s: str ):
    
    return s.replace( "&", "&&" )
    
def GetDifferentLighterDarkerColour( colour, intensity = 3 ):
    
    new_hue = colour.hsvHueF()
    
    if new_hue == -1: # completely achromatic
        
        new_hue = 0.5
        
    else:
        
        new_hue = ( new_hue + 0.33 ) % 1.0
        
    
    new_saturation = colour.hsvSaturationF()
    
    if ColourIsGreyish( colour ):
        
        new_saturation = 0.2
        
    
    new_colour = QG.QColor.fromHsvF( new_hue, new_saturation, colour.valueF(), colour.alphaF() )
    
    return GetLighterDarkerColour( new_colour, intensity )
    
def GetDisplayPosition( window ):
    
    return QW.QApplication.desktop().availableGeometry( window ).topLeft()
    
def GetDisplaySize( window ):
    
    return QW.QApplication.desktop().availableGeometry( window ).size()
    
def GetLighterDarkerColour( colour, intensity = 3 ):
    
    if intensity is None or intensity == 0:
        
        return colour
        
    
    # darker/lighter works by multiplying value, so when it is closer to 0, lmao
    breddy_darg_made = 0.25
    
    if colour.value() < breddy_darg_made:
        
        colour = QG.QColor.fromHslF( colour.hsvHueF(), colour.hsvSaturationF(), breddy_darg_made, colour.alphaF() )
        
    
    qt_intensity = 100 + ( 20 * intensity )
    
    if ColourIsBright( colour ):
        
        return colour.darker( qt_intensity )
        
    else:
        
        return colour.lighter( qt_intensity )
        
    
def GetMouseScreen():
    
    return QW.QApplication.screenAt( QG.QCursor.pos() )
    
def GetTLWParents( widget ):
    
    widget_tlw = widget.window()        
    
    parent_tlws = []
    
    parent = widget_tlw.parentWidget()
    
    while parent is not None:
        
        parent_tlw = parent.window()
        
        parent_tlws.append( parent_tlw )
        
        parent = parent_tlw.parentWidget()
        
    
    return parent_tlws
    
def IsQtAncestor( child, ancestor, through_tlws = False ):
    
    if child == ancestor:
        
        return True
        
    
    parent = child
    
    if through_tlws:
        
        while not parent is None:
            
            if parent == ancestor:
                
                return True
                
            
            parent = parent.parentWidget()
            
        
    else:
        
        # only works within window
        return ancestor.isAncestorOf( child )
        
    
    return False
    
def MouseIsOnMyDisplay( window ):
    
    window_handle = window.window().windowHandle()
    
    if window_handle is None:
        
        return False
        
    
    window_screen = window_handle.screen()
    
    mouse_screen = GetMouseScreen()
    
    return mouse_screen is window_screen
    
def NotebookScreenToHitTest( notebook, screen_position ):
    
    tab_pos = notebook.tabBar().mapFromGlobal( screen_position )    
    
    return notebook.tabBar().tabAt( tab_pos )
    
def SetBitmapButtonBitmap( button, bitmap ):
    
    # old wx stuff, but still basically relevant
    # the button's bitmap, retrieved via GetBitmap, is not the same as the one we gave it!
    # hence testing bitmap vs that won't work to save time on an update loop, so we'll just save it here custom
    # this isn't a big memory deal for our purposes since they are small and mostly if not all from the GlobalPixmaps library so shared anyway
    
    if hasattr( button, 'last_bitmap' ):
        
        if button.last_bitmap == bitmap:
            
            return
            
        
    
    button.setIcon( QG.QIcon( bitmap ) )
    button.setIconSize( bitmap.size() )
    
    button.last_bitmap = bitmap
    
def TLWIsActive( window ):
    
    return window.window() == QW.QApplication.activeWindow()
    
def TLWOrChildIsActive( win ):
    
    current_focus_tlw = QW.QApplication.activeWindow()
    
    if current_focus_tlw is None:
        
        return False
        
    
    if current_focus_tlw == win:
        
        return True
        
    
    if win in GetTLWParents( current_focus_tlw ):
        
        return True
        
    
    return False
    
def WidgetOrAnyTLWChildHasFocus( window ):
    
    active_window = QW.QApplication.activeWindow()
    
    if window == active_window:
        
        return True
        
    
    widget = QW.QApplication.focusWidget()
    
    if widget is None:
        
        # take active window in lieu of focus, if it is unavailable
        widget = active_window
        
    
    while widget is not None:
        
        if widget == window:
            
            return True
            
        
        widget = widget.parentWidget()
        
    
    return False
    
