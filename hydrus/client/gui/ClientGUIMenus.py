import collections.abc
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusProfiling
from hydrus.core import HydrusText

from hydrus.client import ClientGlobals as CG

from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui import ClientGUIFunctions

HG.last_mouse_click_button = QC.Qt.MouseButton.LeftButton

def AddLastClickMemory( gui_item ):
    
    class _ClickMemoryFilter( QC.QObject ):
        
        def eventFilter(self, watched, event):
            
            if event.type() == QC.QEvent.Type.MouseButtonPress:
                
                event = typing.cast( QG.QMouseEvent, event )
                
                HG.last_mouse_click_button = event.button()
                
            
            return False
            
        
    
    filter_obj = _ClickMemoryFilter( gui_item )
    
    gui_item.installEventFilter( filter_obj )
    
    return filter_obj
    

def AppendMenu( menu, submenu, label ):
    
    RemoveFinalSeparator( submenu )
    
    label = SanitiseLabel( label )
    
    submenu.setTitle( label )
    menu_action = menu.addMenu( submenu )
    
    return menu_action
    

def AppendMenuIconItem( menu: QW.QMenu, label: str, description: str, icon: QG.QIcon, callable, *args, **kwargs ):
    
    menu_item = QW.QAction( menu )
    
    SetMenuTexts( menu_item, label, description )
    
    menu_item.setIcon( icon )
    
    menu.addAction( menu_item )
    
    BindMenuItem( menu_item, callable, *args, **kwargs )
    
    return menu_item
    

def AppendMenuCheckItem( menu, label, description, initial_value, callable, *args, **kwargs ):
    
    menu_item = QW.QAction( menu )
    
    SetMenuTexts( menu_item, label, description )
    
    menu_item.setCheckable( True )
    menu_item.setChecked( initial_value )
    
    menu.addAction( menu_item )
    
    BindMenuItem( menu_item, callable, *args, **kwargs )
    
    return menu_item
    

def AppendMenuItem( menu, label, description, callable, *args, role: QW.QAction.MenuRole = None, **kwargs ):
    
    menu_item = QW.QAction( menu )
    
    if HC.PLATFORM_MACOS:
        
        menu_item.setMenuRole( role if role is not None else QW.QAction.MenuRole.NoRole )
        
    
    SetMenuTexts( menu_item, label, description )
    
    menu.addAction( menu_item )
    
    BindMenuItem( menu_item, callable, *args, **kwargs )
    
    return menu_item
    

def AppendMenuLabel( menu, label, description = '', copy_text = '', no_copy = False, make_it_bold = False ):
    
    if no_copy:
        
        description = ''
        
    else:
        
        if description == label:
            
            description = ''
            
        
        if copy_text == '':
            
            copy_text = label
            
        
        if description == '':
            
            description = f'copy "{copy_text}" to clipboard'
            
        
    
    menu_item = QW.QAction( menu )
    
    SetMenuTexts( menu_item, label, description )
    
    if make_it_bold:
        
        font = menu_item.font()
        font.setBold( True )
        menu_item.setFont( font )
        
    
    menu.addAction( menu_item )
    
    if not no_copy:
        
        BindMenuItem( menu_item, CG.client_controller.pub, 'clipboard', 'text', copy_text )
        
    
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
        
        submenu = GenerateMenu( menu )
        
        AppendMenu( menu, submenu, submenu_name )
        
        item_prefix = ''
        
    
    for ( label, description, call ) in menu_tuples:
        
        label = '{}{}'.format( item_prefix, label )
        
        if call is None:
            
            AppendMenuLabel( submenu, label, description )
            
        else:
            
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
        
    


class StatusBarRedirectFilter( QC.QObject ):
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == QC.QEvent.Type.StatusTip:
                
                QW.QApplication.instance().sendEvent( CG.client_controller.gui, event )
                
                return True
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    

def GenerateMenu( parent: QW.QWidget ) -> QW.QMenu:
    
    menu = QW.QMenu( parent )
    
    menu.setToolTipsVisible( True )
    
    menu.installEventFilter( StatusBarRedirectFilter( menu ) )
    
    return menu
    

def GetEventCallable( callable, *args, **kwargs ):
    
    def event_callable( checked_state ):
        
        if HydrusProfiling.IsProfileMode( 'ui' ):
            
            summary = 'Profiling menu: ' + repr( callable )
            
            HydrusProfiling.Profile( summary, HydrusData.Call( callable, *args, **kwargs ), min_duration_ms = HG.menu_profile_min_job_time_ms )
            
        else:
            
            callable( *args, **kwargs )
            
        
    
    return event_callable
    
    
def RemoveFinalSeparator( menu: QW.QMenu ):
    
    num_items = len( menu.actions() )
    
    if num_items > 0:
        
        last_item = menu.actions()[-1]
        
        # got this once, who knows what happened, so we test for QAction now
        # 'PySide2.QtGui.QStandardItem' object has no attribute 'isSeparator'
        if isinstance( last_item, QW.QAction ):
            
            if last_item.isSeparator():
                
                menu.removeAction( last_item )
                
            
        
    
def SanitiseLabel( label: str ) -> str:
    
    if label == '':
        
        label = '-invalid label-'
        
    
    return label.replace( '&', '&&' )
    

def SetMenuItemLabel( menu_item: QW.QAction, label: str ):
    
    label = SanitiseLabel( label )
    
    menu_item.setText( label )
    

def SetMenuTexts( menu_item: QW.QAction, label: str, description: str ):
    
    unsanitized_label = label
    
    label = SanitiseLabel( label )
    
    elided_label = HydrusText.ElideText( label, 128, elide_center = True )
    
    menu_item.setText( elided_label )
    
    menu_item.setStatusTip( description )
    
    if label != elided_label:
        
        menu_item.setToolTip( ClientGUIFunctions.WrapToolTip( unsanitized_label ) + '\n\n' + description )
        
    elif description != label and description != '':
        
        menu_item.setToolTip( ClientGUIFunctions.WrapToolTip( description ) )
        
    
    menu_item.setWhatsThis( description )
    

def SetMenuTitle( menu: QW.QMenu, label: str ):
    
    label = SanitiseLabel( label )
    
    menu.setTitle( label )
    

def SpamItems( menu: QW.QMenu, labels_descriptions_and_calls: collections.abc.Collection[ tuple[ str, str, collections.abc.Callable ] ], max_allowed: int ):
    
    if len( labels_descriptions_and_calls ) > max_allowed:
        
        num_to_show = max_allowed - 1
        
    else:
        
        num_to_show = max_allowed
        
    
    for ( label, description, call ) in list( labels_descriptions_and_calls )[:num_to_show]:
        
        AppendMenuItem( menu, label, description, call )
        
    
    if len( labels_descriptions_and_calls ) > num_to_show:
        
        # maybe one day this becomes a thing that extends the menu to show them all
        
        AppendMenuLabel( menu, '{} more...'.format( len( labels_descriptions_and_calls ) - num_to_show ) )
        
    

def SpamLabels( menu: QW.QMenu, labels_and_copy_texts: collections.abc.Collection[ tuple[ str, str ] ], max_allowed: int ):
    
    if len( labels_and_copy_texts ) > max_allowed:
        
        num_to_show = max_allowed - 1
        
    else:
        
        num_to_show = max_allowed
        
    
    for ( label, copy_text ) in list( labels_and_copy_texts )[:num_to_show]:
        
        AppendMenuLabel( menu, label, copy_text = copy_text )
        
    
    if len( labels_and_copy_texts ) > num_to_show:
        
        # maybe one day this becomes a thing that extends the menu to show them all
        
        AppendMenuLabel( menu, '{} more...'.format( len( labels_and_copy_texts ) - num_to_show ) )
        
    
