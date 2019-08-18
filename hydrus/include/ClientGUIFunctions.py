from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
import wx

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
        
        hashes.update( m.GetHashes() )
        
    
    if service_type in HC.TAG_SERVICES:
        
        tag = value
        
        can_add = False
        can_pend = False
        can_delete = False
        can_petition = True
        can_rescind_pend = False
        can_rescind_petition = False
        
        for m in media:
            
            tags_manager = m.GetTagsManager()
            
            current = tags_manager.GetCurrent( service_key )
            pending = tags_manager.GetPending( service_key )
            petitioned = tags_manager.GetPetitioned( service_key )
            
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
                
                from . import ClientGUIDialogs
                
                with ClientGUIDialogs.DialogTextEntry( parent, message ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        content_update_action = HC.CONTENT_UPDATE_PETITION
                        
                        reason = dlg.GetValue()
                        
                        rows = [ ( tag, hashes ) ]
                        
                    else:
                        
                        return True
                        
                    
                
            else:
                
                return True
                
            
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_update_action, row, reason = reason ) for row in rows ]
        
    elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
        
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
        
    else:
        
        return False
        
    
    HG.client_controller.Write( 'content_updates', { service_key : content_updates } )
    
    return True
    
def ClientToScreen( win, pos ):
    
    if isinstance( win, wx.TopLevelWindow ):
        
        tlp = win
        
    else:
        
        tlp = win.GetTopLevelParent()
        
    
    if win.IsShown() and tlp.IsShown():
        
        return win.ClientToScreen( pos )
        
    else:
        
        return ( 50, 50 )
        
    

MAGIC_TEXT_PADDING = 1.1

def ConvertTextToPixels( window, char_dimensions ):
    
    ( char_cols, char_rows ) = char_dimensions
    
    dc = wx.ClientDC( window )
    
    dc.SetFont( window.GetFont() )
    
    return ( int( char_cols * dc.GetCharWidth() * MAGIC_TEXT_PADDING ), int( char_rows * dc.GetCharHeight() * MAGIC_TEXT_PADDING ) )
    
def ConvertTextToPixelWidth( window, char_cols ):
    
    dc = wx.ClientDC( window )
    
    dc.SetFont( window.GetFont() )
    
    return int( char_cols * dc.GetCharWidth() * MAGIC_TEXT_PADDING )
    
def GetFocusTLP():
    
    focus = wx.Window.FindFocus()
    
    return GetTLP( focus )
    
def GetTLP( window ):
    
    if window is None:
        
        return None
        
    elif isinstance( window, wx.TopLevelWindow ):
        
        return window
        
    else:
        
        return window.GetTopLevelParent()
        
    
def GetTLPParents( window ):
    
    if not isinstance( window, wx.TopLevelWindow ):
        
        window = GetTLP( window )
        
    
    parents = []
    
    parent = window.GetParent()
    
    while parent is not None:
        
        parents.append( parent )
        
        parent = parent.GetParent()
        
    
    return parents
    
def GetXYTopTLP( screen_position ):
    
    tlps = wx.GetTopLevelWindows()
    
    hittest_tlps = [ tlp for tlp in tlps if tlp.HitTest( tlp.ScreenToClient( screen_position ) ) == wx.HT_WINDOW_INSIDE and tlp.IsShown() ]
    
    if len( hittest_tlps ) == 0:
        
        return None
        
    
    most_childish = hittest_tlps[0]
    
    for tlp in hittest_tlps[1:]:
        
        if most_childish in GetTLPParents( tlp ):
            
            most_childish = tlp
            
        
    
    return most_childish
    
def IsWXAncestor( child, ancestor, through_tlws = False ):
    
    if child == ancestor:
        
        return True
        
    
    parent = child
    
    if through_tlws:
        
        while not parent is None:
            
            if parent == ancestor:
                
                return True
                
            
            parent = parent.GetParent()
            
        
    else:
        
        # get parent first, then test, then loop test. otherwise we exclude ancestor if it is a tlp
        
        while not isinstance( parent, wx.TopLevelWindow ):
            
            parent = parent.GetParent()
            
            if parent == ancestor:
                
                return True
                
            
        
    
    return False
    
def NotebookScreenToHitTest( notebook, screen_position ):
    
    if HC.PLATFORM_OSX:
        
        # OS X has some unusual coordinates for its notebooks
        # the notebook tabs are not considered to be in the client area (they are actually negative on getscreenposition())
        # its hittest works on window coords, not client coords
        # hence to get hittest position, we get our parent's client position and adjust by our given position in that
        
        # this also seems to cause menus popped on notebooks to spawn high and left, wew
        
        ( my_x, my_y ) = notebook.GetPosition()
        
        ( p_x, p_y ) = notebook.GetParent().ScreenToClient( wx.GetMousePosition() )
        
        position = ( p_x - my_x, p_y - my_y )
        
    else:
        
        position = notebook.ScreenToClient( screen_position )
        
    
    return notebook.HitTest( position )
    
def SetBitmapButtonBitmap( button, bitmap ):
    
    # the button's bitmap, retrieved via GetBitmap, is not the same as the one we gave it!
    # hence testing bitmap vs that won't work to save time on an update loop, so we'll just save it here custom
    # this isn't a big memory deal for our purposes since they are small and mostly if not all from the GlobalBMPs library so shared anyway
    
    if hasattr( button, 'last_bitmap' ):
        
        if button.last_bitmap == bitmap:
            
            return
            
        
    
    button.SetBitmap( bitmap )
    
    button.last_bitmap = bitmap
    
def TLPHasFocus( window ):
    
    focus_tlp = GetFocusTLP()
    
    window_tlp = GetTLP( window )
    
    return window_tlp == focus_tlp
    
def WindowHasFocus( window ):
    
    focus = wx.Window.FindFocus()
    
    if focus is None:
        
        return False
        
    
    return window == focus
    
def WindowOrAnyTLPChildHasFocus( window ):
    
    focus = wx.Window.FindFocus()
    
    while focus is not None:
        
        if focus == window:
            
            return True
            
        
        focus = focus.GetParent()
        
    
    return False
    
def WindowOrSameTLPChildHasFocus( window ):
    
    focus = wx.Window.FindFocus()
    
    while focus is not None:
        
        if focus == window:
            
            return True
            
        
        if isinstance( focus, wx.TopLevelWindow ):
            
            return False
            
        
        focus = focus.GetParent()
        
    
    return False
    
