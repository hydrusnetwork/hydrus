import collections
from . import HydrusData
from . import HydrusGlobals as HG
import os
import wx

menus_to_submenus = collections.defaultdict( set )
menus_to_menu_item_data = collections.defaultdict( set )

def AppendMenu( menu, submenu, label ):
    
    label = SanitiseLabel( label )
    
    menu.AppendSubMenu( submenu, label )
    
    menus_to_submenus[ menu ].add( submenu )
    
def AppendMenuBitmapItem( event_handler, menu, label, description, bitmap, callable, *args, **kwargs ):
    
    label = SanitiseLabel( label )
    
    menu_item = wx.MenuItem( menu, wx.ID_ANY, label )
    
    menu_item.SetHelp( description )
    
    menu_item.SetBitmap( bitmap )
    
    menu.Append( menu_item )
    
    BindMenuItem( event_handler, menu, menu_item, callable, *args, **kwargs )
    
    return menu_item
    
def AppendMenuCheckItem( event_handler, menu, label, description, initial_value, callable, *args, **kwargs ):
    
    label = SanitiseLabel( label )
    
    menu_item = menu.AppendCheckItem( wx.ID_ANY, label, description )
    
    menu_item.Check( initial_value )
    
    BindMenuItem( event_handler, menu, menu_item, callable, *args, **kwargs )
    
    return menu_item
    
def AppendMenuItem( event_handler, menu, label, description, callable, *args, **kwargs ):
    
    label = SanitiseLabel( label )
    
    menu_item = menu.Append( wx.ID_ANY, label, description )
    
    BindMenuItem( event_handler, menu, menu_item, callable, *args, **kwargs )
    
    return menu_item
    
def AppendMenuLabel( menu, label, description = None ):
    
    if description is None:
        
        description = ''
        
    
    menu_item = menu.Append( wx.ID_ANY, label, description )
    
    return menu_item
    
def AppendSeparator( menu ):
    
    num_items = menu.GetMenuItemCount()
    
    if num_items > 0:
        
        last_item = menu.FindItemByPosition( num_items - 1 )
        
        if not last_item.IsSeparator():
            
            menu.AppendSeparator()
            
        
    
def BindMenuItem( event_handler, menu, menu_item, callable, *args, **kwargs ):
    
    event_callable = GetEventCallable( callable, *args, **kwargs )
    
    event_handler.Bind( wx.EVT_MENU, event_callable, source = menu_item )
    
    menus_to_menu_item_data[ menu ].add( ( menu_item, event_handler ) )
    
def CreateMenu():
    
    menu = wx.Menu()
    
    return menu
    
def UnbindMenuItems( menu ):
    
    menu_item_data = menus_to_menu_item_data[ menu ]
    
    del menus_to_menu_item_data[ menu ]
    
    for ( menu_item, event_handler ) in menu_item_data:
        
        if not event_handler: # under some circumstances, this has been deleted before the menu was
            
            continue
            
        
        event_handler.Unbind( wx.EVT_MENU, source = menu_item )
        
    
    if menu in menus_to_submenus:
        
        submenus = menus_to_submenus[ menu ]
        
        for submenu in submenus:
            
            UnbindMenuItems( submenu )
            
            submenu.is_dead = True
            
        
        del menus_to_submenus[ menu ]
        
    
def DestroyMenu( window, menu ):
    
    UnbindMenuItems( menu )
    
    menu.is_dead = True
    
    # if the window we just popupmenu'd on is dead now (i.e. it died while the menu was open), destroying the menu will cause a crash and letting the event continue will cause a crash
    
    if not window:
        
        message = 'A window just died before its menu could be safely destroyed! If an exception were not raised here, the program would crash! If you know you did something tricky, please avoid this in future. If you think you did something normal, please let hydrus dev know.'
        
        raise Exception( message )
        
    
    menu.Destroy()
    
def GetEventCallable( callable, *args, **kwargs ):
    
    def event_callable( event ):
        
        if HG.menu_profile_mode:
            
            summary = 'Profiling menu: ' + repr( callable )
            
            HydrusData.ShowText( summary )
            
            HydrusData.Profile( summary, 'callable( *args, **kwargs )', globals(), locals() )
            
        else:
            
            callable( *args, **kwargs )
            
        
    
    return event_callable
    
def MenuIsDead( menu ):
    
    # doing 'if menu' doesn't work for the deadobject test, wew
    
    return hasattr( menu, 'is_dead' )
    
def SanitiseLabel( label ):
    
    if label == '':
        
        label = '-invalid label-'
        
    
    return label.replace( '&', '&&' )
    
