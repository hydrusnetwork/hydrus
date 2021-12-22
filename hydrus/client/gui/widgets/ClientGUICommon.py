import os
import re
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientPaths
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP

CANVAS_MEDIA_VIEWER = 0
CANVAS_PREVIEW = 1

canvas_str_lookup = {}

canvas_str_lookup[ CANVAS_MEDIA_VIEWER ] = 'media viewer'
canvas_str_lookup[ CANVAS_PREVIEW ] = 'preview'

def AddGridboxStretchSpacer( layout: QW.QGridLayout ):
    
    layout.addItem( QW.QSpacerItem( 10, 10, QW.QSizePolicy.Expanding, QW.QSizePolicy.Fixed ) )
    
def WrapInGrid( parent, rows, expand_text = False, add_stretch_at_end = True ):
    
    gridbox = QP.GridLayout( cols = 2 )
    
    if expand_text:
        
        gridbox.setColumnStretch( 0, 1 )
        
        text_flags = CC.FLAGS_EXPAND_BOTH_WAYS
        control_flags = CC.FLAGS_CENTER_PERPENDICULAR
        sizer_flags = CC.FLAGS_CENTER_PERPENDICULAR
        
    else:
        
        gridbox.setColumnStretch( 1, 1 )
        
        text_flags = CC.FLAGS_ON_LEFT
        control_flags = CC.FLAGS_NONE
        sizer_flags = CC.FLAGS_EXPAND_SIZER_BOTH_WAYS
        
    
    for ( text, control ) in rows:
        
        if isinstance( text, BetterStaticText ):
            
            st = text
            
        else:
            
            st = BetterStaticText( parent, text )
            
        
        if isinstance( control, QW.QLayout ):
            
            cflags = sizer_flags
            
        else:
            
            cflags = control_flags
            
            if control.toolTip() != '':
                
                st.setToolTip( control.toolTip() )
                
            
        
        QP.AddToLayout( gridbox, st, text_flags )
        QP.AddToLayout( gridbox, control, cflags )
        
    
    if add_stretch_at_end:
        
        gridbox.setRowStretch( gridbox.rowCount(), 1 )
        
    
    return gridbox
    
def WrapInText( control, parent, text, object_name = None ):
    
    hbox = QP.HBoxLayout()
    
    st = BetterStaticText( parent, text )
    
    if object_name is not None:
        
        st.setObjectName( object_name )
        
    
    QP.AddToLayout( hbox, st, CC.FLAGS_CENTER_PERPENDICULAR )
    QP.AddToLayout( hbox, control, CC.FLAGS_EXPAND_BOTH_WAYS )
    
    return hbox
    
class ShortcutAwareToolTipMixin( object ):
    
    def __init__( self, tt_callable ):
        
        self._tt_callable = tt_callable
        
        self._tt = ''
        self._simple_shortcut_command = None
        
        if ClientGUIShortcuts.shortcuts_manager_initialised():
            
            ClientGUIShortcuts.shortcuts_manager().shortcutsChanged.connect( self.RefreshToolTip )
            
        
    
    def _RefreshToolTip( self ):
        
        tt = self._tt
        
        if self._simple_shortcut_command is not None:
            
            tt += os.linesep * 2
            tt += '----------'
            
            names_to_shortcuts = ClientGUIShortcuts.shortcuts_manager().GetNamesToShortcuts( self._simple_shortcut_command )
            
            if len( names_to_shortcuts ) > 0:
                
                names = sorted( names_to_shortcuts.keys() )
                
                for name in names:
                    
                    shortcuts = names_to_shortcuts[ name ]
                    
                    shortcut_strings = sorted( ( shortcut.ToString() for shortcut in shortcuts ) )
                    
                    if name in ClientGUIShortcuts.shortcut_names_to_pretty_names:
                        
                        pretty_name = ClientGUIShortcuts.shortcut_names_to_pretty_names[ name ]
                        
                    else:
                        
                        pretty_name = name
                        
                    
                    tt += os.linesep * 2
                    
                    tt += ', '.join( shortcut_strings )
                    tt += os.linesep
                    tt += '({}->{})'.format( pretty_name, CAC.simple_enum_to_str_lookup[ self._simple_shortcut_command ] )
                    
                
            else:
                
                tt += os.linesep * 2
                
                tt += 'no shortcuts set'
                tt += os.linesep
                tt += '({})'.format( CAC.simple_enum_to_str_lookup[ self._simple_shortcut_command ] )
                
            
        
        self._tt_callable( tt )
        
    
    def RefreshToolTip( self ):
        
        if ClientGUIShortcuts.shortcuts_manager_initialised():
            
            self._RefreshToolTip()
            
        
    
    def SetToolTipWithShortcuts( self, tt: str, simple_shortcut_command: int ):
        
        self._tt = tt
        self._simple_shortcut_command = simple_shortcut_command
        
        self._RefreshToolTip()
        
    
class BetterBitmapButton( ShortcutAwareToolTipMixin, QW.QPushButton ):
    
    def __init__( self, parent, bitmap, func, *args, **kwargs ):
        
        QW.QPushButton.__init__( self, parent )
        self.setIcon( QG.QIcon( bitmap ) )
        self.setIconSize( bitmap.size() )
        self.setSizePolicy( QW.QSizePolicy.Maximum, QW.QSizePolicy.Maximum )
        ShortcutAwareToolTipMixin.__init__( self, self.setToolTip )
        
        self._func = func
        self._args = args
        self._kwargs = kwargs
        
        self.clicked.connect( self.EventButton )
        
    
    def EventButton( self ):
        
        self._func( *self._args,  **self._kwargs )
        
    
class BetterButton( ShortcutAwareToolTipMixin, QW.QPushButton ):
    
    def __init__( self, parent, label, func, *args, **kwargs ):
        
        QW.QPushButton.__init__( self, parent )
        ShortcutAwareToolTipMixin.__init__( self, self.setToolTip )
        
        self.setText( label )
        
        self._func = func
        self._args = args
        self._kwargs = kwargs
        
        self._yes_no_text = None
        
        self.clicked.connect( self.EventButton )
        
    
    def EventButton( self ):
        
        if self._yes_no_text is not None:
            
            from hydrus.client.gui import ClientGUIDialogsQuick
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message = self._yes_no_text )
            
            if result != QW.QDialog.Accepted:
                
                return
                
            
        
        self._func( *self._args,  **self._kwargs )
        
    
    def SetYesNoText( self, text: str ):
        
        # this should probably be setyesnotextfactory, but WHATEVER for now
        
        self._yes_no_text = text
        
    
    def setText( self, label ):
        
        button_label = ClientGUIFunctions.EscapeMnemonics( label )
        
        QW.QPushButton.setText( self, button_label )
        
    
class BetterChoice( QW.QComboBox ):
    
    def __init__( self, *args, **kwargs ):
        
        QW.QComboBox.__init__( self, *args, **kwargs )
        
        self.setMaxVisibleItems( 32 )
        
    
    def addItem( self, display_string, client_data ):
        
        QW.QComboBox.addItem( self, display_string, client_data )
        
        if self.count() == 1:
            
            self.setCurrentIndex( 0 )
            
        
    
    def GetValue( self ):
        
        selection = self.currentIndex()
        
        if selection != -1:
            
            return self.itemData( selection, QC.Qt.UserRole )
            
        elif self.count() > 0:
            
            return self.itemData( 0, QC.Qt.UserRole )
            
        else:
            
            return None
            
        
    
    def SetValue( self, data ):
        
        for i in range( self.count() ):
            
            if data == self.itemData( i, QC.Qt.UserRole ):
                
                self.setCurrentIndex( i )
                
                return
                
            
        
        if self.count() > 0:
            
            self.setCurrentIndex( 0 )
            
        
    
class BetterColourControl( QP.ColourPickerCtrl ):
    
    def __init__( self, *args, **kwargs ):
        
        QP.ColourPickerCtrl.__init__( self, *args, **kwargs )
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
    
    def _ImportHexFromClipboard( self ):
        
        try:
            
            import_string = HG.client_controller.GetClipboardText()
            
        except Exception as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        if import_string.startswith( '#' ):
            
            import_string = import_string[1:]
            
        
        import_string = '#' + re.sub( '[^0-9a-fA-F]', '', import_string )
        
        if len( import_string ) != 7:
            
            QW.QMessageBox.critical( self, 'Error', 'That did not appear to be a hex string!' )
            
            return
            
        
        try:
            
            colour = QG.QColor( import_string )
            
        except Exception as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            HydrusData.ShowException( e )
            
            return
            
        
        self.SetColour( colour )
        
    
    def contextMenuEvent( self, event ):
        
        if event.reason() == QG.QContextMenuEvent.Keyboard:
            
            self.ShowMenu()
            
        
    
    def mouseReleaseEvent( self, event ):
        
        if event.button() != QC.Qt.RightButton:
            
            QP.ColourPickerCtrl.mouseReleaseEvent( self, event )
            
            return
            
        
        self.ShowMenu()
        
    
    def ShowMenu( self ):
        
        menu = QW.QMenu()
        
        hex_string = self.GetColour().name( QG.QColor.HexRgb )
        
        ClientGUIMenus.AppendMenuItem( menu, 'copy ' + hex_string + ' to the clipboard', 'Copy the current colour to the clipboard.', HG.client_controller.pub, 'clipboard', 'text', hex_string )
        ClientGUIMenus.AppendMenuItem( menu, 'import a hex colour from the clipboard', 'Look at the clipboard for a colour in the format #FF0000, and set the colour.', self._ImportHexFromClipboard )
        
        CGC.core().PopupMenu( self, menu )
        
    
class BetterNotebook( QW.QTabWidget ):
    
    def _ShiftSelection( self, delta ):
        
        existing_selection = self.currentIndex()
        
        if existing_selection != -1:
            
            new_selection = ( existing_selection + delta ) % self.count()
            
            if new_selection != existing_selection:
                
                self.setCurrentIndex( new_selection )
                
            
        
    
    def DeleteAllPages( self ):
        
        while self.count() > 0:
            
            page = self.widget( 0 )
            
            self.removeTab( 0 )
            
            page.deleteLater()
            
        
    
    def GetPages( self ):
        
        return [ self.widget( i ) for i in range( self.count() ) ]
        
    
    def SelectLeft( self ):
        
        self._ShiftSelection( -1 )
        
    
    def SelectPage( self, page ):
        
        for i in range( self.count() ):
            
            if self.widget( i ) == page:
                
                self.setCurrentIndex( i )
                
                return
                
            
        
    
    def SelectRight( self ):
        
        self._ShiftSelection( 1 )
        
    
class ButtonWithMenuArrow( QW.QToolButton ):
    
    def __init__( self, parent: QW.QWidget, action: QW.QAction ):
        
        QW.QToolButton.__init__( self, parent )
        
        self.setPopupMode( QW.QToolButton.MenuButtonPopup )
        
        self.setToolButtonStyle( QC.Qt.ToolButtonTextOnly )
        
        self.setDefaultAction( action )
        
        self._menu = QW.QMenu( self )
        
        self.setMenu( self._menu )
        
        self._menu.aboutToShow.connect( self._ClearAndPopulateMenu )
        
    
    def _ClearAndPopulateMenu( self ):
        
        self._menu.clear()
        
        self._PopulateMenu( self._menu )
        
    
    def _PopulateMenu( self, menu ):
        
        raise NotImplementedError()
        
    
class BetterRadioBox( QP.RadioBox ):
    
    def __init__( self, *args, **kwargs ):
        
        self._indices_to_data = { i : data for ( i, ( s, data ) ) in enumerate( kwargs[ 'choices' ] ) }
        
        kwargs[ 'choices' ] = [ s for ( s, data ) in kwargs[ 'choices' ] ]
        
        QP.RadioBox.__init__( self, *args, **kwargs )
        
    
    def GetValue( self ):
        
        index = self.GetCurrentIndex()
        
        return self._indices_to_data[ index ]
        
    
    def SetValue( self, data ):
        
        for ( i, d ) in self._indices_to_data.items():
            
            if d == data:
                
                self.Select( i )
                
                return
                
            
        
    
class BetterStaticText( QP.EllipsizedLabel ):
    
    def __init__( self, parent, label = None, tooltip_label = False, **kwargs ):
        
        ellipsize_end = 'ellipsize_end' in kwargs and kwargs[ 'ellipsize_end' ]

        QP.EllipsizedLabel.__init__( self, parent, ellipsize_end = ellipsize_end )
        
        # otherwise by default html in 'this is a <hr> parsing step' stuff renders fully lmaoooo
        self.setTextFormat( QC.Qt.PlainText )
        
        self._tooltip_label = tooltip_label
        
        if 'ellipsize_end' in kwargs and kwargs[ 'ellipsize_end' ]:
            
            self._tooltip_label = True
            
        
        self._last_set_text = '' # we want a separate copy since the one we'll send to the st will be wrapped and have additional '\n's
        
        self._wrap_width = None
        
        if label is not None:
            
            self.setText( label )
            
        
    
    def clear( self ):
        
        self._last_set_text = ''
        
        QP.EllipsizedLabel.clear( self )
        
    
    def setText( self, text ):
        
        # this doesn't need mnemonic escape _unless_ a buddy is set, wew lad
        
        if text != self._last_set_text:
            
            self._last_set_text = text
            
            QP.EllipsizedLabel.setText( self, text )
            
            if self._tooltip_label:
                
                self.setToolTip( text )
                
            
        
    
class BetterHyperLink( BetterStaticText ):
    
    def __init__( self, parent, label, url ):
        
        BetterStaticText.__init__( self, parent, label )
        
        self._url = url
        
        self.setToolTip( self._url )

        self.setTextFormat( QC.Qt.RichText )
        self.setTextInteractionFlags( QC.Qt.TextBrowserInteraction )
        
        self.setText( '<a href="{}">{}</a>'.format( url, label ) )
        
        self.linkActivated.connect( self.Activated )
        
    
    def Activated( self ):
        
        ClientPaths.LaunchURLInWebBrowser( self._url )
        

class BufferedWindow( QW.QWidget ):
    
    def __init__( self, *args, **kwargs ):
        
        QW.QWidget.__init__( self, *args )
        
        if 'size' in kwargs:
            
            size = kwargs[ 'size' ]
            
            if isinstance( size, QC.QSize ):
                
                self.setFixedSize( kwargs[ 'size' ] )
                
            
        
    
    def _Draw( self, painter ):
        
        raise NotImplementedError()
        
    
    def paintEvent( self, event ):
        
        painter = QG.QPainter( self )
        
        self._Draw( painter )
        
    
class BufferedWindowIcon( BufferedWindow ):
    
    def __init__( self, parent, bmp, click_callable = None ):
        
        BufferedWindow.__init__( self, parent, size = bmp.size() )
        
        self._bmp = bmp
        self._click_callable = click_callable
        
    
    def _Draw( self, painter ):
        
        background_colour = QP.GetBackgroundColour( self.parentWidget() )
        
        painter.setBackground( QG.QBrush( background_colour ) )
        
        painter.eraseRect( painter.viewport() )
        
        if isinstance( self._bmp, QG.QImage ):
            
            painter.drawImage( 0, 0, self._bmp )
            
        else:
            
            painter.drawPixmap( 0, 0, self._bmp )
            
        
    
    def mousePressEvent( self, event ):
        
        if self._click_callable is None:
            
            return BufferedWindow.mousePressEvent( self, event )
            
        else:
            
            self._click_callable()
            
        
    
class CheckboxManager( object ):
    
    def GetCurrentValue( self ):
        
        raise NotImplementedError()
        
    
    def Invert( self ):
        
        raise NotImplementedError()
        
    
class CheckboxManagerBoolean( CheckboxManager ):
    
    def __init__( self, obj, name ):
        
        CheckboxManager.__init__( self )
        
        self._obj = obj
        self._name = name
        
    
    def GetCurrentValue( self ):
        
        if not self._obj:
            
            return False
            
        
        return getattr( self._obj, self._name )
        
    
    def Invert( self ):
        
        if not self._obj:
            
            return
            
        
        value = getattr( self._obj, self._name )
        
        setattr( self._obj, self._name, not value )
        
    
class CheckboxManagerCalls( CheckboxManager ):
    
    def __init__( self, invert_call, value_call ):
        
        CheckboxManager.__init__( self )
        
        self._invert_call = invert_call
        self._value_call = value_call
        
    
    def GetCurrentValue( self ):
        
        return self._value_call()
        
    
    def Invert( self ):
        
        self._invert_call()
        
    
class CheckboxManagerOptions( CheckboxManager ):
    
    def __init__( self, boolean_name ):
        
        CheckboxManager.__init__( self )
        
        self._boolean_name = boolean_name
        
    
    def GetCurrentValue( self ):
        
        new_options = HG.client_controller.new_options
        
        return new_options.GetBoolean( self._boolean_name )
        
    
    def Invert( self ):
        
        new_options = HG.client_controller.new_options
        
        new_options.InvertBoolean( self._boolean_name )
        
        if self._boolean_name == 'advanced_mode':
            
            HG.client_controller.pub( 'notify_advanced_mode' )
            
        
        HG.client_controller.pub( 'checkbox_manager_inverted' )
        HG.client_controller.pub( 'notify_new_menu_option' )
        
    
class AlphaColourControl( QW.QWidget ):
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        self._colour_picker = BetterColourControl( self )
        
        self._alpha_selector = QP.MakeQSpinBox( self, min=0, max=255 )
        
        hbox = QP.HBoxLayout( spacing = 5 )
        
        QP.AddToLayout( hbox, self._colour_picker, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, BetterStaticText(self,'alpha:'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._alpha_selector, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetValue( self ):
        
        colour = self._colour_picker.GetColour()
        
        a = self._alpha_selector.value()
        
        colour.setAlpha( a )
        
        return colour
        
    
    def SetValue( self, colour: QG.QColor ):
        
        picker_colour = QG.QColor( colour.rgb() )
        
        self._colour_picker.SetColour( picker_colour )
        
        self._alpha_selector.setValue( colour.alpha() )
        
    
class ExportPatternButton( BetterButton ):
    
    def __init__( self, parent ):
        
        BetterButton.__init__( self, parent, 'pattern shortcuts', self._Hit )
        
    
    def _Hit( self ):
        
        menu = QW.QMenu()
        
        ClientGUIMenus.AppendMenuLabel( menu, 'click on a phrase to copy to clipboard' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'unique numerical file id - {file_id}', 'copy "{file_id}" to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '{file_id}' )
        ClientGUIMenus.AppendMenuItem( menu, 'the file\'s hash - {hash}', 'copy "{hash}" to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '{hash}' )
        ClientGUIMenus.AppendMenuItem( menu, 'all the file\'s tags - {tags}', 'copy "{tags}" to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '{tags}' )
        ClientGUIMenus.AppendMenuItem( menu, 'all the file\'s non-namespaced tags - {nn tags}', 'copy "{nn tags}" to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '{nn tags}' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'all instances of a particular namespace - [\u2026]', 'copy "[\u2026]" to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '[\u2026]' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'a particular tag, if the file has it - (\u2026)', 'copy "(\u2026)" to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '(\u2026)' )
        
        CGC.core().PopupMenu( self, menu )
        
    
class Gauge( QW.QProgressBar ):
    
    def __init__( self, *args, **kwargs ):
        
        QW.QProgressBar.__init__( self, *args, **kwargs )
        
        self._actual_value = None
        self._actual_range = None
        
        self._is_pulsing = False
        
        self.SetRange( 1 )
        self.SetValue( 0 )
        
    
    def GetValueRange( self ):
        
        if self._actual_range is None:
            
            range = self.maximum()
            
        else:
            
            range = self._actual_range
            
        
        return ( self._actual_value, range )
        
    
    def SetRange( self, range ):
        
        if range is None or range == 0:
            
            self.Pulse()
            
        else:
            
            if self._is_pulsing:
                
                self.StopPulsing()
                
            
            if range > 1000:
                
                self._actual_range = range
                range = 1000
                
            else:
                
                self._actual_range = None
                
            
            if range != self.maximum():
                
                QW.QProgressBar.setMaximum( self, range )
                
            
        
    
    def SetValue( self, value ):
        
        self._actual_value = value
        
        if not self._is_pulsing:
            
            if value is None:
                
                self.Pulse()
                
            else:
                
                if self._actual_range is not None:
                    
                    value = min( int( 1000 * ( value / self._actual_range ) ), 1000 )
                    
                
                value = min( value, self.maximum() )
                
                if value != self.value():
                    
                    QW.QProgressBar.setValue( self, value )
                    
                
            
        
    
    def StopPulsing( self ):
        
        self._is_pulsing = False
        
        self.SetRange( 1 )
        self.SetValue( 0 )
        
    
    def Pulse( self ):
        
        # pulse looked stupid, was turning on too much, should improve it later
        
        #self.setMaximum( 0 )
        
        #self.setMinimum( 0 )
        
        self.SetRange( 1 )
        self.SetValue( 0 )
        
        self._is_pulsing = True
        
    
class ListBook( QW.QWidget ):
    
    def __init__( self, *args, **kwargs ):
        
        QW.QWidget.__init__( self, *args, **kwargs )
        
        self._keys_to_active_pages = {}
        self._keys_to_proto_pages = {}
        
        self._list_box = QW.QListWidget( self )
        self._list_box.setSelectionMode( QW.QListWidget.SingleSelection )
        
        self._empty_panel = QW.QWidget( self )
        
        self._current_key = None
        
        self._current_panel = self._empty_panel
        
        self._panel_sizer = QP.VBoxLayout()
        
        QP.AddToLayout( self._panel_sizer, self._empty_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._list_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( hbox, self._panel_sizer, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._list_box.itemSelectionChanged.connect( self.EventSelection )
        
        self.setLayout( hbox )
        
    
    def _ActivatePage( self, key ):

        ( classname, args, kwargs ) = self._keys_to_proto_pages[ key ]
        
        page = classname( *args, **kwargs )
        
        page.setVisible( False )
        
        QP.AddToLayout( self._panel_sizer, page, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._keys_to_active_pages[ key ] = page
        
        del self._keys_to_proto_pages[ key ]
        
    
    def _GetIndex( self, key ):
        
        for i in range( self._list_box.count() ):
            
            i_key = self._list_box.item( i ).data( QC.Qt.UserRole )
            
            if i_key == key:
                
                return i
                
            
        
        return -1
        
    
    def _Select( self, selection ):
        
        if selection == -1:
            
            self._current_key = None
            
        else:
            
            self._current_key = self._list_box.item( selection ).data( QC.Qt.UserRole )
            
        
        self._current_panel.setVisible( False )
        
        self._list_box.blockSignals( True )
        
        QP.ListWidgetSetSelection( self._list_box, selection )
        
        self._list_box.blockSignals( False )
        
        if selection == -1:
            
            self._current_panel = self._empty_panel
            
        else:
            
            if self._current_key in self._keys_to_proto_pages:
                
                self._ActivatePage( self._current_key )
                
            
            self._current_panel = self._keys_to_active_pages[ self._current_key ]
            
        
        self._current_panel.show()
        
        self.update()
        
    
    def AddPage( self, display_name, key, page, select = False ):
        
        if self._GetIndex( key ) != -1:
            
            raise HydrusExceptions.NameException( 'That entry already exists!' )
            
        
        if not isinstance( page, tuple ):
            
            page.setVisible( False )
            
            QP.AddToLayout( self._panel_sizer, page, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
        
        # Could call QListWidget.sortItems() here instead of doing it manually
        
        current_display_names = QP.ListWidgetGetStrings( self._list_box )
        
        insertion_index = len( current_display_names )
        
        for ( i, current_display_name ) in enumerate( current_display_names ):
            
            if current_display_name > display_name:
                
                insertion_index = i
                
                break
                
            
        item = QW.QListWidgetItem()
        item.setText( display_name )
        item.setData( QC.Qt.UserRole, key )
        self._list_box.insertItem( insertion_index, item )
        
        self._keys_to_active_pages[ key ] = page
        
        if self._list_box.count() == 1:
            
            self._Select( 0 )
            
        elif select:
            
            index = self._GetIndex( key )
            
            self._Select( index )
            
        
    
    def AddPageArgs( self, display_name, key, classname, args, kwargs ):
        
        if self._GetIndex( key ) != -1:
            
            raise HydrusExceptions.NameException( 'That entry already exists!' )
            
        
        # Could call QListWidget.sortItems() here instead of doing it manually
        
        current_display_names = QP.ListWidgetGetStrings( self._list_box )
        
        insertion_index = len( current_display_names )
        
        for ( i, current_display_name ) in enumerate( current_display_names ):
            
            if current_display_name > display_name:
                
                insertion_index = i
                
                break
                
            
        item = QW.QListWidgetItem()
        item.setText( display_name )
        item.setData( QC.Qt.UserRole, key )
        self._list_box.insertItem( insertion_index, item )
        
        self._keys_to_proto_pages[ key ] = ( classname, args, kwargs )
        
        if self._list_box.count() == 1:
            
            self._Select( 0 )
            
        
    
    def DeleteAllPages( self ):
        
        self._panel_sizer.removeWidget( self._empty_panel )
        
        QP.ClearLayout( self._panel_sizer, delete_widgets=True )
        
        QP.AddToLayout( self._panel_sizer, self._empty_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._current_key = None
        
        self._current_panel = self._empty_panel
        
        self._keys_to_active_pages = {}
        self._keys_to_proto_pages = {}
        
        self._list_box.clear()
        
    
    def DeleteCurrentPage( self ):
        
        selection = QP.ListWidgetGetSelection( self._list_box )
        
        if selection != -1:
            
            key_to_delete = self._current_key
            page_to_delete = self._current_panel
            
            next_selection = selection + 1
            previous_selection = selection - 1
            
            if next_selection < self._list_box.count():
                
                self._Select( next_selection )
                
            elif previous_selection >= 0:
                
                self._Select( previous_selection )
                
            else:
                
                self._Select( -1 )
                
            
            self._panel_sizer.removeWidget( page_to_delete )
            
            page_to_delete.deleteLater()
            
            del self._keys_to_active_pages[ key_to_delete ]
            
            QP.ListWidgetDelete( self._list_box, selection )
            
        
    
    def EventSelection( self ):
        
        selection = QP.ListWidgetGetSelection( self._list_box )
        
        if selection != self._GetIndex( self._current_key ):
            
            self._Select( selection )
                
            
        
    
    def GetCurrentKey( self ):
        
        return self._current_key
        
    
    def GetCurrentPage( self ):
        
        if self._current_panel == self._empty_panel:
            
            return None
            
        else:
            
            return self._current_panel
            
        
    
    def GetActivePages( self ):
        
        return list(self._keys_to_active_pages.values())
        
    
    def GetPage( self, key ):
        
        if key in self._keys_to_proto_pages:
            
            self._ActivatePage( key )
            
        
        if key in self._keys_to_active_pages:
            
            return self._keys_to_active_pages[ key ]
            
        
        raise Exception( 'That page not found!' )
        
    
    def GetPageCount( self ):
        
        return len( self._keys_to_active_pages ) + len( self._keys_to_proto_pages )
        
    
    def KeyExists( self, key ):
        
        return key in self._keys_to_active_pages or key in self._keys_to_proto_pages
        
    
    def Select( self, key ):
        
        index = self._GetIndex( key )
        
        if index != -1 and index != QP.ListWidgetGetSelection( self._list_box ) :
            
            self._Select( index )
            
        
    
    def SelectDown( self ):
        
        current_selection = QP.ListWidgetGetSelection( self._list_box )
        
        if current_selection != -1:
            
            num_entries = self._list_box.count()
            
            if current_selection == num_entries - 1: selection = 0
            else: selection = current_selection + 1
            
            if selection != current_selection:
                
                self._Select( selection )
                
            
        
    
    def SelectPage( self, page_to_select ):
        
        for ( key, page ) in list(self._keys_to_active_pages.items()):
            
            if page == page_to_select:
                
                self._Select( self._GetIndex( key ) )
                
                return
                
            
        
    
    def SelectUp( self ):
        
        current_selection = QP.ListWidgetGetSelection( self._list_box )
        
        if current_selection != -1:
            
            num_entries = self._list_box.count()
            
            if current_selection == 0: selection = num_entries - 1
            else: selection = current_selection - 1
            
            if selection != current_selection:
                
                self._Select( selection )
                
            
        
    
class NoneableSpinCtrl( QW.QWidget ):

    valueChanged = QC.Signal()
    
    def __init__( self, parent, message = '', none_phrase = 'no limit', min = 0, max = 1000000, unit = None, multiplier = 1, num_dimensions = 1 ):
        
        QW.QWidget.__init__( self, parent )
        
        self._unit = unit
        self._multiplier = multiplier
        self._num_dimensions = num_dimensions
        
        self._checkbox = QW.QCheckBox( self )
        self._checkbox.stateChanged.connect( self.EventCheckBox )
        self._checkbox.setText( none_phrase )
        
        self._one = QP.MakeQSpinBox( self, min=min, max=max )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._one, len( str( max ) ) + 5 )
        
        self._one.setMaximumWidth( width )
        
        if num_dimensions == 2:
            
            self._two = QP.MakeQSpinBox( self, initial=0, min=min, max=max )
            self._two.valueChanged.connect( self._HandleValueChanged )
            
            width = ClientGUIFunctions.ConvertTextToPixelWidth( self._two, len( str( max ) ) + 5 )
            
            self._two.setMinimumWidth( width )
            
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        if len( message ) > 0:
            
            QP.AddToLayout( hbox, BetterStaticText(self,message+': '), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        QP.AddToLayout( hbox, self._one, CC.FLAGS_CENTER_PERPENDICULAR )
        
        if self._num_dimensions == 2:
            
            QP.AddToLayout( hbox, BetterStaticText(self,'x'), CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, self._two, CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        if self._unit is not None:
            
            QP.AddToLayout( hbox, BetterStaticText(self,self._unit), CC.FLAGS_CENTER_PERPENDICULAR )
        
        
        QP.AddToLayout( hbox, self._checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
    
        self._one.valueChanged.connect( self._HandleValueChanged )
        self._checkbox.stateChanged.connect( self._HandleValueChanged )
        
        
    def _HandleValueChanged( self, val ):
        
        self.valueChanged.emit()
        
    
    def EventCheckBox( self, state ):
        
        if self._checkbox.isChecked():
    
            self._one.setEnabled( False )
            
            if self._num_dimensions == 2:
                
                self._two.setEnabled( False )
                
            
        else:
            
            self._one.setEnabled( True )
            
            if self._num_dimensions == 2:
                
                self._two.setEnabled( True )
                
            
        
    
    def GetValue( self ):
        
        if self._checkbox.isChecked():
            
            return None
            
        else:
            
            if self._num_dimensions == 2:
                
                return ( self._one.value() * self._multiplier, self._two.value() * self._multiplier )
                
            else:
                
                return self._one.value() * self._multiplier
                
            
        
    
    def setToolTip( self, text ):
        
        QW.QWidget.setToolTip( self, text )
        
        for c in self.children():
            
            if isinstance( c, QW.QWidget ):
                
                c.setToolTip( text )
            
        
    
    def SetValue( self, value ):
        
        if value is None:
            
            self._checkbox.setChecked( True )
            
            self._one.setEnabled( False )
            if self._num_dimensions == 2: self._two.setEnabled( False )
            
        else:
            
            self._checkbox.setChecked( False )
            
            if self._num_dimensions == 2:
                
                self._two.setEnabled( True )
                
                ( value, y ) = value
                
                self._two.setValue( y // self._multiplier )
                
            
            self._one.setEnabled( True )
            
            self._one.setValue( value // self._multiplier )
            
        
    
class NoneableTextCtrl( QW.QWidget ):

    valueChanged = QC.Signal()
    
    def __init__( self, parent, message = '', none_phrase = 'none' ):
        
        QW.QWidget.__init__( self, parent )
        
        self._checkbox = QW.QCheckBox( self )
        self._checkbox.stateChanged.connect( self.EventCheckBox )
        self._checkbox.setText( none_phrase )
        
        self._text = QW.QLineEdit( self )
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        if len( message ) > 0:
            
            QP.AddToLayout( hbox, BetterStaticText(self,message+': '), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        QP.AddToLayout( hbox, self._text, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        self._checkbox.stateChanged.connect( self._HandleValueChanged )
        self._text.textChanged.connect( self._HandleValueChanged )
    
    def _HandleValueChanged( self, val ):
        
        self.valueChanged.emit()
        
        
    def EventCheckBox( self, state ):
    
        if self._checkbox.isChecked():
        
            self._text.setEnabled( False )
            
        else:
            
            self._text.setEnabled( True )
            
        
    
    def GetValue( self ):
        
        if self._checkbox.isChecked():
            
            return None
            
        else:
            
            return self._text.text()
            
        
    
    def setToolTip( self, text ):
        
        QW.QWidget.setToolTip( self, text )
        
        for c in self.children():
            
            if isinstance( c, QW.QWidget ):
                
                c.setToolTip( text )
            
        
    
    def SetValue( self, value ):
        
        if value is None:
            
            self._checkbox.setChecked( True )
            
            self._text.setEnabled( False )
            
        else:
            
            self._checkbox.setChecked( False )
            
            self._text.setEnabled( True )
            
            self._text.setText( value )
            
        
    
class OnOffButton( QW.QPushButton ):
    
    valueChanged = QC.Signal( bool )
    
    def __init__( self, parent, on_label, off_label = None, start_on = True ):
        
        if start_on: label = on_label
        else: label = off_label
        
        QW.QPushButton.__init__( self, parent )
        QW.QPushButton.setText( self, label )
        
        self.setObjectName( 'HydrusOnOffButton' )
        
        self._on_label = on_label
        
        if off_label is None:
            
            self._off_label = on_label
            
        else:
            
            self._off_label = off_label
            
        
        self.setProperty( 'hydrus_on', start_on )
        
        self.clicked.connect( self.Flip )
        
    
    def _SetValue( self, value ):
        
        self.setProperty( 'hydrus_on', value )
        
        if value:
            
            self.setText( self._on_label )
            
        else:
            
            self.setText( self._off_label )
            
        
        self.valueChanged.emit( value )
        
        self.style().polish( self )
        
    
    def Flip( self ):
        
        new_value = not self.property( 'hydrus_on' )
        
        self._SetValue( new_value )
        
    
    def IsOn( self ):
        
        return self.property( 'hydrus_on' )
        
    
    def SetOnOff( self, value ):
        
        self._SetValue( value )
        
    
class RegexButton( BetterButton ):
    
    def __init__( self, parent ):
        
        BetterButton.__init__( self, parent, 'regex shortcuts', self._ShowMenu )
        
    
    def _ShowMenu( self ):
        
        menu = QW.QMenu()
        
        ClientGUIMenus.AppendMenuLabel( menu, 'click on a phrase to copy it to the clipboard' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        submenu = QW.QMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( submenu, r'whitespace character - \s', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'\s' )
        ClientGUIMenus.AppendMenuItem( submenu, r'number character - \d', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'\d' )
        ClientGUIMenus.AppendMenuItem( submenu, r'alphanumeric or backspace character - \w', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'\w' )
        ClientGUIMenus.AppendMenuItem( submenu, r'any character - .', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'.' )
        ClientGUIMenus.AppendMenuItem( submenu, r'backslash character - \\', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'\\' )
        ClientGUIMenus.AppendMenuItem( submenu, r'beginning of line - ^', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'^' )
        ClientGUIMenus.AppendMenuItem( submenu, r'end of line - $', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'$' )
        ClientGUIMenus.AppendMenuItem( submenu, 'any of these - [\u2026]', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '[\u2026]' )
        ClientGUIMenus.AppendMenuItem( submenu, 'anything other than these - [^\u2026]', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '[^\u2026]' )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        ClientGUIMenus.AppendMenuItem( submenu, r'0 or more matches, consuming as many as possible - *', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'*' )
        ClientGUIMenus.AppendMenuItem( submenu, r'1 or more matches, consuming as many as possible - +', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'+' )
        ClientGUIMenus.AppendMenuItem( submenu, r'0 or 1 matches, preferring 1 - ?', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'?' )
        ClientGUIMenus.AppendMenuItem( submenu, r'0 or more matches, consuming as few as possible - *?', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'*?' )
        ClientGUIMenus.AppendMenuItem( submenu, r'1 or more matches, consuming as few as possible - +?', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'+?' )
        ClientGUIMenus.AppendMenuItem( submenu, r'0 or 1 matches, preferring 0 - ??', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'??' )
        ClientGUIMenus.AppendMenuItem( submenu, r'exactly m matches - {m}', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'{m}' )
        ClientGUIMenus.AppendMenuItem( submenu, r'm to n matches, consuming as many as possible - {m,n}', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'{m,n}' )
        ClientGUIMenus.AppendMenuItem( submenu, r'm to n matches, consuming as few as possible - {m,n}?', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'{m,n}?' )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        ClientGUIMenus.AppendMenuItem( submenu, 'the next characters are: (non-consuming) - (?=\u2026)', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '(?=\u2026)' )
        ClientGUIMenus.AppendMenuItem( submenu, 'the next characters are not: (non-consuming) - (?!\u2026)', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '(?!\u2026)' )
        ClientGUIMenus.AppendMenuItem( submenu, 'the previous characters are: (non-consuming) - (?<=\u2026)', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '(?<=\u2026)' )
        ClientGUIMenus.AppendMenuItem( submenu, 'the previous characters are not: (non-consuming) - (?<!\u2026)', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '(?<!\u2026)' )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        ClientGUIMenus.AppendMenuItem( submenu, r'0074 -> 74 - [1-9]+\d*', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', r'[1-9]+\d*' )
        ClientGUIMenus.AppendMenuItem( submenu, r'filename - (?<=' + re.escape( os.path.sep ) + r')[^' + re.escape( os.path.sep ) + r']*?(?=\..*$)', 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', '(?<=' + re.escape( os.path.sep ) + r')[^' + re.escape( os.path.sep ) + r']*?(?=\..*$)' )
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'regex components' )
        
        submenu = QW.QMenu( menu )
        
        ClientGUIMenus.AppendMenuItem( submenu, 'manage favourites', 'manage some custom favourite phrases', self._ManageFavourites )
        
        ClientGUIMenus.AppendSeparator( submenu )
        
        for ( regex_phrase, description ) in HC.options[ 'regex_favourites' ]:
            
            ClientGUIMenus.AppendMenuItem( submenu, description, 'copy this phrase to the clipboard', HG.client_controller.pub, 'clipboard', 'text', regex_phrase )
            
        
        ClientGUIMenus.AppendMenu( menu, submenu, 'favourites' )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _ManageFavourites( self ):
        
        regex_favourites = HC.options[ 'regex_favourites' ]
        
        from hydrus.client.gui import ClientGUITopLevelWindowsPanels
        from hydrus.client.gui import ClientGUIScrolledPanelsEdit
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'manage regex favourites' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditRegexFavourites( dlg, regex_favourites )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                regex_favourites = panel.GetValue()
                
                HC.options[ 'regex_favourites' ] = regex_favourites
                
                HG.client_controller.Write( 'save_options', HC.options )
                
            
        
    
class StaticBox( QW.QFrame ):
    
    def __init__( self, parent, title ):
        
        QW.QFrame.__init__( self, parent )
        
        self.setFrameStyle( QW.QFrame.Box | QW.QFrame.Raised )
        self._spacer = QW.QSpacerItem( 0, 0, QW.QSizePolicy.Minimum, QW.QSizePolicy.MinimumExpanding )
        
        self._sizer = QP.VBoxLayout()
        
        normal_font = QW.QApplication.font()
        
        normal_font_size = normal_font.pointSize()
        normal_font_family = normal_font.family()
        
        title_font = QG.QFont( normal_font_family, int( normal_font_size ), QG.QFont.Bold )
        
        self._title_st = BetterStaticText( self, label = title )
        self._title_st.setFont( title_font )
        
        QP.AddToLayout( self._sizer, self._title_st, CC.FLAGS_CENTER )
        
        self.setLayout( self._sizer )
        
        self.layout().addSpacerItem( self._spacer )
        
    
    def Add( self, widget, flags = None ):
        
        self.layout().removeItem( self._spacer )
        
        QP.AddToLayout( self._sizer, widget, flags )

        self.layout().addSpacerItem( self._spacer )
        
    
    def SetTitle( self, title ):
        
        self._title_st.setText( title )
        
    
class RadioBox( StaticBox ):
    
    def __init__( self, parent, title, choice_pairs, initial_index = None ):
        
        StaticBox.__init__( self, parent, title )
        
        self._indices_to_radio_buttons = {}
        self._radio_buttons_to_data = {}
        
        for ( index, ( text, data ) ) in enumerate( choice_pairs ):
            
            radio_button = QW.QRadioButton( text, self )
            
            self.Add( radio_button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._indices_to_radio_buttons[ index ] = radio_button
            self._radio_buttons_to_data[ radio_button ] = data
            
        
        if initial_index is not None and initial_index in self._indices_to_radio_buttons: self._indices_to_radio_buttons[ initial_index ].setChecked( True )
        
    
    def GetSelectedClientData( self ):
        
        for radio_button in list(self._radio_buttons_to_data.keys()):
            
            if radio_button.isDown(): return self._radio_buttons_to_data[ radio_button]
            
        
    
    def SetSelection( self, index ):
        
        self._indices_to_radio_buttons[ index ].setChecked( True )
        
    
    def SetString( self, index, text ):
        
        self._indices_to_radio_buttons[ index ].setText( text )
        
    
class TextCatchEnterEventFilter( QC.QObject ):
    
    def __init__( self, parent, callable, *args, **kwargs ):
        
        QC.QObject.__init__( self, parent )
        
        self._callable = HydrusData.Call( callable, *args, **kwargs )
        
    
    def eventFilter( self, watched, event ):
        
        if event.type() == QC.QEvent.KeyPress and event.key() in ( QC.Qt.Key_Enter, QC.Qt.Key_Return ):
            
            self._callable()
            
            event.accept()
            
            return True
            
        
        return False
        
    
class TextAndGauge( QW.QWidget ):
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        self._st = BetterStaticText( self )
        self._gauge = Gauge( self )
        
        vbox = QP.VBoxLayout( margin = 0 )
        
        QP.AddToLayout( vbox, self._st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
    
    def SetText( self, text ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        self._st.setText( text )
        
    
    def SetValue( self, text, value, range ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        self._st.setText( text )
        
        self._gauge.SetRange( range )
        self._gauge.SetValue( value )
        
    
