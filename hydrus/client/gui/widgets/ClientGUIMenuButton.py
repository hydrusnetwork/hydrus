import collections.abc

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusData

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui.widgets import ClientGUICommon

class MenuTemplateItem( object ):
    
    def __init__( self, title: str | collections.abc.Callable[ [], str ], description: str | collections.abc.Callable[ [], str ] ):
        
        self.title = title
        self.description = description
        self._visible_callable = None
        
    
    def GetDescription( self ) -> str:
        
        if isinstance( self.description, str ):
            
            return self.description
            
        else:
            
            return self.description()
            
        
    
    def GetTitle( self ) -> str:
        
        if isinstance( self.title, str ):
            
            return self.title
            
        else:
            
            return self.title()
            
        
    
    def IsVisible( self ):
        
        if self._visible_callable is not None:
            
            try:
                
                return self._visible_callable()
                
            except Exception as e:
                
                HydrusData.ShowText( 'Problem with a menu visible call! Please send the following error to hydev!' )
                HydrusData.ShowException( e, do_wait = False )
                
                return True
                
            
        
        return True
        
    
    def SetVisibleCallable( self, visible_callable: collections.abc.Callable[ [], bool ] ):
        
        self._visible_callable = visible_callable
        
    

class MenuTemplateItemCall( MenuTemplateItem ):
    
    def __init__( self, title: str | collections.abc.Callable[ [], str ], description: str | collections.abc.Callable[ [], str ], call, *args, **kwargs ):
        
        super().__init__( title, description )
        
        self.call = call
        self.args = args
        self.kwargs = kwargs
        
    

class MenuTemplateItemCheck( MenuTemplateItem ):
    
    def __init__( self, title: str | collections.abc.Callable[ [], str ], description: str | collections.abc.Callable[ [], str ], check_manager: ClientGUICommon.CheckboxManager ):
        
        super().__init__( title, description )
        
        self.check_manager = check_manager
        
    

class MenuTemplateItemLabel( MenuTemplateItem ):
    
    pass
    

class MenuTemplateItemSeparator( MenuTemplateItem ):
    
    def __init__( self ):
        
        super().__init__( 'separator', 'separator' )
        
    

class MenuTemplateItemSubmenu( MenuTemplateItem ):
    
    def __init__( self, title: str | collections.abc.Callable[ [], str ], submenu_template_items: list[ MenuTemplateItem ] ):
        
        super().__init__( title, title )
        
        self.submenu_template_items = submenu_template_items
        
    

def PopulateMenuFromTemplateItems( menu: QW.QMenu, menu_template_items: list[ MenuTemplateItem ] ):
    
    for menu_template_item in menu_template_items:
        
        if not menu_template_item.IsVisible():
            
            continue
            
        
        title = menu_template_item.GetTitle()
        description = menu_template_item.GetDescription()
        
        if isinstance( menu_template_item, MenuTemplateItemCall ):
            
            call = menu_template_item.call
            args = menu_template_item.args
            kwargs = menu_template_item.kwargs
            
            ClientGUIMenus.AppendMenuItem( menu, title, description, call, *args, **kwargs )
            
        elif isinstance( menu_template_item, MenuTemplateItemCheck ):
            
            check_manager = menu_template_item.check_manager
            
            current_value = check_manager.GetCurrentValue()
            func = check_manager.Invert
            
            if current_value is not None:
                
                ClientGUIMenus.AppendMenuCheckItem( menu, title, description, current_value, func )
                
            
        elif isinstance( menu_template_item, MenuTemplateItemSeparator ):
            
            ClientGUIMenus.AppendSeparator( menu )
            
        elif isinstance( menu_template_item, MenuTemplateItemLabel ):
            
            ClientGUIMenus.AppendMenuLabel( menu, title, description = description )
            
        elif isinstance( menu_template_item, MenuTemplateItemSubmenu ):
            
            submenu = ClientGUIMenus.GenerateMenu( menu )
            
            PopulateMenuFromTemplateItems( submenu, menu_template_item.submenu_template_items )
            
            ClientGUIMenus.AppendMenu( menu, submenu, title )
            
        else:
            
            continue
            
        
    

class MenuButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, label, menu_template_items: list[ MenuTemplateItem ] ):
        
        super().__init__( parent, label, self.DoMenu )
        
        self._menu_template_items = menu_template_items
        
    
    def DoMenu( self ):
        
        if len( self._menu_template_items ) == 0:
            
            return
            
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        PopulateMenuFromTemplateItems( menu, self._menu_template_items )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def SetMenuItems( self, menu_template_items: list[ MenuTemplateItem ] ):
        
        self._menu_template_items = menu_template_items
        
    

class MenuIconButton( ClientGUICommon.IconButton ):
    
    def __init__( self, parent, bitmap, menu_template_items: list[ MenuTemplateItem ] ):
        
        super().__init__( parent, bitmap, self.DoMenu )
        
        self._menu_template_items = menu_template_items
        
    
    def DoMenu( self ):
        
        if len( self._menu_template_items ) == 0:
            
            return
            
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        PopulateMenuFromTemplateItems( menu, self._menu_template_items )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def SetMenuItems( self, menu_template_items: list[ MenuTemplateItem ] ):
        
        self._menu_template_items = menu_template_items
        
    

class CogIconButton( MenuIconButton ):
    
    def __init__( self, parent, menu_template_items: list[ MenuTemplateItem ] ):
        
        super().__init__( parent, CC.global_icons().cog, menu_template_items )
        
        self.setToolTip( ClientGUIFunctions.WrapToolTip( 'Advanced settings/commands.' ) )
        
    

class MenuChoiceButton( ClientGUICommon.BetterButton ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, choice_tuples ):
        
        self._choice_tuples = list( choice_tuples )
        self._value_index = None if len( self._choice_tuples ) == 0 else 0
        
        self._menu_template_items = self._GenerateMenuTemplateItems()
        
        label = self._GetCurrentDisplayString()
        
        super().__init__( parent, label, self.DoMenu )
        
    
    def _GenerateMenuTemplateItems( self ):
        
        menu_template_items = []
        
        for ( value_index, ( display_string, data ) ) in enumerate( self._choice_tuples ):
            
            check_manager = self._GetCheckManager( value_index )
            
            menu_template_items.append( MenuTemplateItemCheck( display_string, display_string, check_manager ) )
            
        
        return menu_template_items
        
    
    def _GetCheckManager( self, value_index ):
        
        # in a sub-call so lambda works
        
        check_manager = ClientGUICommon.CheckboxManagerCalls( lambda: self._SetValueIndex( value_index ), lambda: self._value_index == value_index )
        
        return check_manager
        
    
    def _GetCurrentDisplayString( self ):
        
        if self._value_index is None:
            
            return ''
            
        
        return self._choice_tuples[ self._value_index ][0]
        
    
    def _SetValueIndex( self, value_index ):
        
        self._value_index = value_index
        
        display_string = self._GetCurrentDisplayString()
        
        self.setText( display_string )
        
        self.valueChanged.emit()
        
        self.setEnabled( self._value_index is not None )
        
    
    def DoMenu( self ):
        
        if len( self._choice_tuples ) == 0:
            
            return
            
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        PopulateMenuFromTemplateItems( menu, self._menu_template_items )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def GetChoiceTuples( self ):
        
        return list( self._choice_tuples )
        
    
    def GetValue( self ):
        
        if self._value_index is None:
            
            return None
            
        
        return self._choice_tuples[ self._value_index ][1]
        
    
    def SetChoiceTuples( self, choice_tuples ):
        
        self._choice_tuples = choice_tuples
        
        self._menu_template_items = self._GenerateMenuTemplateItems()
        
        if len( self._menu_template_items ) == 0:
            
            self._SetValueIndex( None )
            
        else:
            
            self._SetValueIndex( 0 )
            
        
    
    def SetValue( self, data ):
        
        for ( value_index, ( display_string, existing_data ) ) in enumerate( self._choice_tuples ):
            
            if data == existing_data:
                
                self._SetValueIndex( value_index )
                
                return
                
            
        
    
    def wheelEvent( self, event ):
        
        can_do_it = CG.client_controller.new_options.GetBoolean( 'menu_choice_buttons_can_mouse_scroll' )
        
        if can_do_it:
            
            if self._value_index is not None and can_do_it:
                
                if event.angleDelta().y() > 0:
                    
                    index_delta = -1
                    
                else:
                    
                    index_delta = 1
                    
                
                new_value_index = ( self._value_index + index_delta ) % len( self._choice_tuples )
                
                self._SetValueIndex( new_value_index )
                
            
            event.accept()
            
        else:
            
            event.ignore()
            
        
    
