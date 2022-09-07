from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusText

from hydrus.client.gui import QtPorting as QP

def AppendMenu( menu, submenu, label ):
    
    label = SanitiseLabel( label )
    
    submenu.setTitle( label )
    menu_action = menu.addMenu( submenu )
    
    return menu_action
    
def AppendMenuBitmapItem( menu, label, description, bitmap, callable, *args, **kwargs ):
    
    label = SanitiseLabel( label )
    
    menu_item = QW.QAction( menu )
    
    if HC.PLATFORM_MACOS:
        
        menu_item.setMenuRole( QW.QAction.ApplicationSpecificRole )
        
    
    menu_item.setText( HydrusText.ElideText( label, 128, elide_center = True ) )
    
    menu_item.setStatusTip( description )
    menu_item.setToolTip( description )
    menu_item.setWhatsThis( description )
    
    menu_item.setIcon( QG.QIcon( bitmap ) )
    
    menu.addAction(menu_item)
    
    BindMenuItem( menu_item, callable, *args, **kwargs )
    
    return menu_item
    
def AppendMenuCheckItem( menu, label, description, initial_value, callable, *args, **kwargs ):
    
    label = SanitiseLabel( label )
    
    menu_item = QW.QAction( menu )
    
    if HC.PLATFORM_MACOS:
        
        menu_item.setMenuRole( QW.QAction.ApplicationSpecificRole )
        
    
    menu_item.setText( HydrusText.ElideText( label, 128, elide_center = True ) )
    
    menu_item.setStatusTip( description )
    menu_item.setToolTip( description )
    menu_item.setWhatsThis( description )
    
    menu_item.setCheckable( True )
    menu_item.setChecked( initial_value )
    
    menu.addAction( menu_item )
    
    BindMenuItem( menu_item, callable, *args, **kwargs )
    
    return menu_item
    
def AppendMenuItem( menu, label, description, callable, *args, **kwargs ):
    
    label = SanitiseLabel( label )
    
    menu_item = QW.QAction( menu )
    
    if HC.PLATFORM_MACOS:
        
        menu_item.setMenuRole( QW.QAction.ApplicationSpecificRole )
        
    
    elided_label = HydrusText.ElideText( label, 128, elide_center = True )
    
    menu_item.setText( elided_label )
    
    if elided_label != label:
        
        menu_item.setToolTip( label )
        
    else:
        
        menu_item.setToolTip( description )
        
    
    menu_item.setStatusTip( description )
    menu_item.setWhatsThis( description )

    menu.addAction( menu_item )
    
    BindMenuItem( menu_item, callable, *args, **kwargs )
    
    return menu_item
    
def AppendMenuLabel( menu, label, description = '' ):
    
    original_label_text = label
    label = SanitiseLabel( label )
    
    if description is None:
        
        description = ''
        
    
    menu_item = QW.QAction( menu )

    if HC.PLATFORM_MACOS:
        
        menu_item.setMenuRole( QW.QAction.ApplicationSpecificRole )
        
    
    menu_item.setText( HydrusText.ElideText( label, 128, elide_center = True ) )
    
    menu_item.setStatusTip( description )
    menu_item.setToolTip( description )
    menu_item.setWhatsThis( description )

    menu.addAction( menu_item )
    
    BindMenuItem( menu_item, HG.client_controller.pub, 'clipboard', 'text', original_label_text )
    
    return menu_item
    
def AppendMenuOrItem( menu, submenu_name, menu_tuples, sort_tuples = True ):
    
    if sort_tuples:
        
        try:
            
            menu_tuples = sorted( menu_tuples )
            
        except:
            
            pass
            
        
    
    if len( menu_tuples ) == 1:
        
        submenu = menu
        
        item_prefix = '{} '.format( submenu_name )
        
    else:
        
        submenu = QW.QMenu( menu )
        
        AppendMenu( menu, submenu, submenu_name )
        
        item_prefix = ''
        
    
    for ( label, description, call ) in menu_tuples:
        
        label = '{}{}'.format( item_prefix, label )
        
        AppendMenuItem( submenu, label, description, call )
        
    
def AppendSeparator( menu ):
    
    num_items = len( menu.actions() )
    
    if num_items > 0:
        
        last_item = menu.actions()[-1]
        
        # got this once, who knows what happened, so we test for QAction now
        # 'PySide2.QtGui.QStandardItem' object has no attribute 'isSeparator'
        last_item_is_separator = isinstance( last_item, QW.QAction ) and last_item.isSeparator()
        
        if not last_item_is_separator:
            
            menu.addSeparator()
            
        
    
def BindMenuItem( menu_item, callable, *args, **kwargs ):
    
    event_callable = GetEventCallable( callable, *args, **kwargs )
    
    menu_item.triggered.connect( event_callable )
    
def DestroyMenu( menu ):
    
    if menu is None:
        
        return
        
    
    if QP.isValid( menu ):
        
        menu.deleteLater()
        
    
def GetEventCallable( callable, *args, **kwargs ):
    
    def event_callable( checked_state ):
        
        if HG.profile_mode:
            
            summary = 'Profiling menu: ' + repr( callable )
            
            HydrusData.Profile( summary, 'callable( *args, **kwargs )', globals(), locals(), min_duration_ms = HG.menu_profile_min_job_time_ms )
            
        else:
            
            callable( *args, **kwargs )
            
        
    
    return event_callable
    
def SanitiseLabel( label: str ) -> str:
    
    if label == '':
        
        label = '-invalid label-'
        
    
    return label.replace( '&', '&&' )
    
def SetMenuItemLabel( menu_item: QW.QAction, label: str ):
    
    label = SanitiseLabel( label )
    
    menu_item.setText( label )
    
def SetMenuTitle( menu: QW.QMenu, label: str ):
    
    label = SanitiseLabel( label )
    
    menu.setTitle( label )
    
