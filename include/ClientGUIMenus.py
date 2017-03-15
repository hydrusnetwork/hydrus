import ClientConstants as CC
import collections
import HydrusGlobals
import wx

menus_to_submenus = collections.defaultdict( set )
menus_to_menu_item_data = collections.defaultdict( set )

def AppendMenu( menu, submenu, label ):
    
    label = SanitiseLabel( label )
    
    menu.AppendMenu( CC.ID_NULL, label, submenu )
    
    menus_to_submenus[ menu ].add( submenu )
    
def AppendMenuBitmapItem( event_handler, menu, label, description, bitmap, callable, *args, **kwargs ):
    
    label = SanitiseLabel( label )
    
    menu_item = wx.MenuItem( menu, wx.ID_ANY, label )
    
    menu_item.SetHelp( description )
    
    menu_item.SetBitmap( bitmap )
    
    menu.AppendItem( menu_item )
    
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
    
def DestroyMenuItems( menu ):
    
    handler = HydrusGlobals.client_controller.GetApp()
    
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
    
def GetEventCallable( callable, *args, **kwargs ):
    
    def event_callable( event ):
        
        callable( *args, **kwargs )
        
    
    return event_callable
    
def SanitiseLabel( label ):
    
    return label.replace( '&', '&&' )
    
