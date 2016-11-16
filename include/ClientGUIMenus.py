import ClientConstants as CC
import collections
import wx

menus_to_submenus = collections.defaultdict( set )
menus_to_menu_item_data = collections.defaultdict( set )

def AppendMenu( menu, submenu, label ):
    
    label.replace( '&', '&&' )
    
    menu.AppendMenu( CC.ID_NULL, label, submenu )
    
    menus_to_submenus[ menu ].add( submenu )
    
def AppendMenuItem( menu, label, description, event_handler, callable, *args, **kwargs ):
    
    label.replace( '&', '&&' )
    
    menu_item = menu.Append( wx.ID_ANY, label, description )
    
    l_callable = GetLambdaCallable( callable, *args, **kwargs )
    
    event_handler.Bind( wx.EVT_MENU, l_callable, source = menu_item )
    
    menus_to_menu_item_data[ menu ].add( ( menu_item, event_handler ) )
    
    return menu_item
    
def GetLambdaCallable( callable, *args, **kwargs ):
    
    l_callable = lambda event: callable( *args, **kwargs )
    
    return l_callable
    
def DestroyMenuItems( menu ):
    
    menu_item_data = menus_to_menu_item_data[ menu ]
    
    del menus_to_menu_item_data[ menu ]
    
    for ( menu_item, event_handler ) in menu_item_data:
        
        event_handler.Unbind( wx.EVT_MENU, source = menu_item )
        
        menu_item.Destroy()
        
    
    submenus = menus_to_submenus[ menu ]
    
    del menus_to_submenus[ menu ]
    
    for submenu in submenus:
        
        DestroyMenuItems( submenu )
        
    
def DestroyMenu( menu ):
    
    DestroyMenuItems( menu )
    
    menu.Destroy()
    