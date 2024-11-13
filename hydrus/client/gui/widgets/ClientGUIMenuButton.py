from qtpy import QtCore as QC

from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui.widgets import ClientGUICommon

# TODO: if I am feeling clever, I'm pretty sure this guy can inherit from QW.QWidget and do the DoMenu stuff itself, and super() now resolves the diamon inheritance problem
class MenuMixin( object ):
    
    def __init__( self, *args, **kwargs ):
        
        self._menu_items = []
        
        super().__init__( *args, **kwargs )
        
    
    def _PopulateMenu( self, menu, menu_items ):
        
        for ( item_type, title, description, data ) in menu_items:
            
            if item_type == 'normal':
                
                func = data
                
                ClientGUIMenus.AppendMenuItem( menu, title, description, func )
                
            elif item_type == 'check':
                
                check_manager = data
                
                current_value = check_manager.GetCurrentValue()
                func = check_manager.Invert
                
                if current_value is not None:
                    
                    ClientGUIMenus.AppendMenuCheckItem( menu, title, description, current_value, func )
                    
                
            elif item_type == 'separator':
                
                ClientGUIMenus.AppendSeparator( menu )
                
            elif item_type == 'submenu':
                
                submenu = ClientGUIMenus.GenerateMenu( menu )
                
                self._PopulateMenu( submenu, data )
                
                ClientGUIMenus.AppendMenu( menu, submenu, title )
                
            elif item_type == 'label':
                
                ClientGUIMenus.AppendMenuLabel( menu, title, description = description )
                
            
        
    
    def _SetMenuItems( self, menu_items ):
        
        self._menu_items = menu_items
        
    

class MenuBitmapButton( MenuMixin, ClientGUICommon.BetterBitmapButton ):
    
    def __init__( self, parent, bitmap, menu_items ):
        
        super().__init__( parent, bitmap, self.DoMenu )
        
        self._SetMenuItems( menu_items )
        
    
    def DoMenu( self ):
        
        if len( self._menu_items ) == 0:
            
            return
            
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        self._PopulateMenu( menu, self._menu_items )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def SetMenuItems( self, menu_items ):
        
        self._SetMenuItems( menu_items )
        
    

class MenuButton( MenuMixin, ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, label, menu_items ):
        
        super().__init__( parent, label, self.DoMenu )
        
        self._SetMenuItems( menu_items )
        
    
    def DoMenu( self ):
        
        if len( self._menu_items ) == 0:
            
            return
            
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        self._PopulateMenu( menu, self._menu_items )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def SetMenuItems( self, menu_items ):
        
        self._SetMenuItems( menu_items )
        
    

class MenuChoiceButton( MenuMixin, ClientGUICommon.BetterButton ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, choice_tuples ):
        
        self._choice_tuples = list( choice_tuples )
        self._value_index = None if len( self._choice_tuples ) == 0 else 0
        
        label = self._GetCurrentDisplayString()
        
        super().__init__( parent, label, self.DoMenu )
        
        menu_items = self._GenerateMenuItems()
        
        self._SetMenuItems( menu_items )
        
    
    def _GenerateMenuItems( self ):
        
        menu_items = []
        
        for ( value_index, ( display_string, data ) ) in enumerate( self._choice_tuples ):
            
            check_manager = self._GetCheckManager( value_index )
            
            menu_items.append( ( 'check', display_string, display_string, check_manager ) )
            
        
        return menu_items
        
    
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
        
        if len( self._menu_items ) == 0:
            
            return
            
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        self._PopulateMenu( menu, self._menu_items )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def GetChoiceTuples( self ):
        
        return list( self._choice_tuples )
        
    
    def GetValue( self ):
        
        if self._value_index is None:
            
            return None
            
        
        return self._choice_tuples[ self._value_index ][1]
        
    
    def SetChoiceTuples( self, choice_tuples ):
        
        self._choice_tuples = choice_tuples
        
        menu_items = self._GenerateMenuItems()
        
        self._SetMenuItems( menu_items )
        
        if len( menu_items ) == 0:
            
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
            
        
    
