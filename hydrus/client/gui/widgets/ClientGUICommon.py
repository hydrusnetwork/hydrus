import collections.abc
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusLists

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientPaths
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.networking import ClientNetworkingFunctions

def AddGridboxStretchSpacer( win: QW.QWidget, layout: QW.QGridLayout ):
    
    widget = QW.QWidget( win )
    
    QP.AddToLayout( layout, widget, CC.FLAGS_EXPAND_PERPENDICULAR )
    

def WrapInGrid( parent, rows, expand_text = False, expand_single_widgets = False ):
    
    gridbox = QP.GridLayout( cols = 2 )
    
    if expand_text:
        
        gridbox.setColumnStretch( 0, 1 )
        
        text_flags = CC.FLAGS_EXPAND_BOTH_WAYS
        control_flags = CC.FLAGS_CENTER_PERPENDICULAR
        sizer_flags = CC.FLAGS_CENTER_PERPENDICULAR
        
    else:
        
        gridbox.setColumnStretch( 1, 1 )
        
        text_flags = CC.FLAGS_ON_LEFT
        control_flags = CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH
        sizer_flags = CC.FLAGS_EXPAND_SIZER_PERPENDICULAR
        
    
    for row in rows:
        
        if HydrusLists.IsAListLikeCollection( row ) and len( row ) == 2:
            
            ( text, control ) = row
            
            if isinstance( text, BetterStaticText ):
                
                st = text
                
            else:
                
                st = BetterStaticText( parent, text )
                
            
            if control.objectName() == 'HydrusWarning':
                
                st.setObjectName( 'HydrusWarning' )
                
            
            possible_tooltip_widget = None
            
            if isinstance( control, QW.QLayout ):
                
                cflags = sizer_flags
                
                if control.count() > 0:
                    
                    possible_widget_item = control.itemAt( 0 )
                    
                    if isinstance( possible_widget_item, QW.QWidgetItem ):
                        
                        possible_tooltip_widget = possible_widget_item.widget()
                        
                    
                
            else:
                
                cflags = control_flags
                
                possible_tooltip_widget = control
                
            
            if possible_tooltip_widget is not None and isinstance( possible_tooltip_widget, QW.QWidget ) and possible_tooltip_widget.toolTip() != '':
                
                st.setToolTip( possible_tooltip_widget.toolTip() )
                
            
            QP.AddToLayout( gridbox, st, text_flags )
            QP.AddToLayout( gridbox, control, cflags )
            
        else:
            
            control = row
            
            r = gridbox.next_row
            c = gridbox.next_col
            
            rowSpan = 1
            columnSpan = -1
            
            gridbox.addWidget( control, r, c, rowSpan, columnSpan )
            
            gridbox.next_row += 1
            gridbox.next_col = 0
            
            h_policy = QW.QSizePolicy.Policy.Expanding
            
            if expand_single_widgets:
                
                v_policy = QW.QSizePolicy.Policy.Expanding
                
            else:
                
                v_policy = QW.QSizePolicy.Policy.Fixed
                
            
            control.setSizePolicy( h_policy, v_policy )
            
            if expand_single_widgets:
                
                gridbox.setRowStretch( gridbox.rowCount() - 1, 0 )
                
            
        
    
    return gridbox
    

def WrapInTable( parent, rows, spacing = 2, expand_text = False, expand_single_widgets = False ):
    
    text_flags = CC.FLAGS_EXPAND_BOTH_WAYS if expand_text else CC.FLAGS_ON_LEFT
    control_flags = CC.FLAGS_CENTER_PERPENDICULAR if expand_single_widgets else CC.FLAGS_EXPAND_SIZER_PERPENDICULAR
    columns = 1
    padded_rows = []
    
    for row in rows:
        
        if HydrusLists.IsAListLikeCollection( row ):
            
            columns = max( columns, len( row ) )
            
        else:
            
            columns = max( columns, 1 )
            
        
    gridbox = QP.GridLayout( cols = columns, spacing = spacing )
    
    for row in rows:
        
        if HydrusLists.IsAListLikeCollection( row ):
            
            padded_row = list( row ) + [ '' ] * ( columns - len( row ) )
            
        else:
            
            padded_row = [ row ] + [ '' ] * ( columns - 1 )
            
        padded_rows.append( padded_row )
        
    
    
    for display_row in padded_rows:
        
        for i in range( len( display_row ) ):
            
            item = display_row[ i ]
            
            if isinstance( item, str ):
                
                display_cell = BetterStaticText( parent, item )
                
                QP.AddToLayout( gridbox, display_cell, text_flags )
                
            elif isinstance( item, BetterStaticText ):
                
                QP.AddToLayout( gridbox, item, text_flags )
                
            else:
                
                QP.AddToLayout( gridbox, item, control_flags )
                
            
        
    return gridbox
    

def WrapInText( control, parent, text, object_name = None ):
    
    hbox = QP.HBoxLayout()
    
    st = BetterStaticText( parent, text )
    
    if object_name is not None:
        
        st.setObjectName( object_name )
        
    
    st.setAlignment( QC.Qt.AlignmentFlag.AlignRight | QC.Qt.AlignmentFlag.AlignVCenter )
    
    h_policy = QW.QSizePolicy.Policy.Expanding
    v_policy = QW.QSizePolicy.Policy.Fixed
    
    st.setSizePolicy( h_policy, v_policy )
    
    QP.AddToLayout( hbox, st, CC.FLAGS_NONE )
    QP.AddToLayout( hbox, control, CC.FLAGS_CENTER )
    
    if isinstance( control, QW.QWidget ):
        
        st.setToolTip( control.toolTip() )
        
    
    return hbox
    
class ShortcutAwareToolTipMixin( object ):
    
    def __init__( self, *args, **kwargs ):
        
        self._tt_callable = None
        
        self._tt = ''
        self._simple_shortcut_command = None
        
        super().__init__( *args, **kwargs )
        
        if ClientGUIShortcuts.shortcuts_manager_initialised():
            
            ClientGUIShortcuts.shortcuts_manager().shortcutsChanged.connect( self.RefreshToolTip )
            
        
    
    def _RefreshToolTip( self ):
        
        if self._tt_callable is None or self._simple_shortcut_command is None:
            
            return
            
        
        tt = self._tt
        
        tt += '\n' * 2
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
                    
                
                tt += '\n' * 2
                
                tt += ', '.join( shortcut_strings )
                tt += '\n'
                tt += '({}->{})'.format( pretty_name, CAC.simple_enum_to_str_lookup[ self._simple_shortcut_command ] )
                
            
        else:
            
            tt += '\n' * 2
            
            tt += 'no shortcuts set'
            tt += '\n'
            tt += '({})'.format( CAC.simple_enum_to_str_lookup[ self._simple_shortcut_command ] )
            
        
        self._tt_callable( tt )
        
    
    def RefreshToolTip( self ):
        
        if ClientGUIShortcuts.shortcuts_manager_initialised():
            
            self._RefreshToolTip()
            
        
    
    def SetToolTipCallable( self, c ):
        
        self._tt_callable = c
        
        self._RefreshToolTip()
        
    
    def SetToolTipWithShortcuts( self, tt: str, simple_shortcut_command: int ):
        
        self._tt = tt
        self._simple_shortcut_command = simple_shortcut_command
        
        self._RefreshToolTip()
        
    

class BetterButton( ShortcutAwareToolTipMixin, QW.QPushButton ):
    
    def __init__( self, parent, label, func, *args, **kwargs ):
        
        super().__init__( parent )
        
        self.SetToolTipCallable( self.setToolTip )
        
        self.setText( label )
        
        self._func = func
        self._args = args
        self._kwargs = kwargs
        
        self._yes_no_text = None
        
        self.clicked.connect( self.EventButton )
        
        # default is Minimum horizontal, but Preferred says we can go down to minSizeHint
        # QPushButton minSizeHint is actually the same as sizeHint though, so maybe this does nothing hooray
        self.setSizePolicy( QW.QSizePolicy.Policy.Preferred, QW.QSizePolicy.Policy.Fixed )
        
    
    def EventButton( self ):
        
        if self._yes_no_text is not None:
            
            from hydrus.client.gui import ClientGUIDialogsQuick
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message = self._yes_no_text )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
        
        self._func( *self._args,  **self._kwargs )
        
    
    def SetCall( self, func, *args, **kwargs ):
        
        self._func = func
        self._args = args
        self._kwargs = kwargs
        
    
    def SetYesNoText( self, text: str ):
        
        # this should probably be setyesnotextfactory, but WHATEVER for now
        
        self._yes_no_text = text
        
    
    def setText( self, label ):
        
        button_label = ClientGUIFunctions.EscapeMnemonics( label )
        
        QW.QPushButton.setText( self, button_label )
        
    

class BetterCheckBoxList( QW.QListWidget ):
    
    checkBoxListChanged = QC.Signal()
    rightClicked = QC.Signal()
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent )
        
        self.itemClicked.connect( self._ItemCheckStateChanged )
        
        self.setSelectionMode( QW.QAbstractItemView.SelectionMode.ExtendedSelection )
        
        self.setEditTriggers( QW.QAbstractItemView.EditTrigger.NoEditTriggers )
        
        self.setUniformItemSizes( True )
        
    
    def _ItemCheckStateChanged( self, item ):
        
        self.checkBoxListChanged.emit()
        
    
    def Append( self, text, data, starts_checked = False ):
        
        item = QW.QListWidgetItem()
        
        item.setFlags( item.flags() | QC.Qt.ItemFlag.ItemIsUserCheckable )
        
        qt_state = QC.Qt.CheckState.Checked if starts_checked else QC.Qt.CheckState.Unchecked
        
        item.setCheckState( qt_state )
        
        item.setText( text )
        
        item.setData( QC.Qt.ItemDataRole.UserRole, data )
        
        self.addItem( item )
        
        self._ItemCheckStateChanged( item )
        
    
    def Check( self, index: int, value: bool = True ):
        
        qt_state = QC.Qt.CheckState.Checked if value else QC.Qt.CheckState.Unchecked
        
        item = self.item( index )
        
        item.setCheckState( qt_state )
        
        self._ItemCheckStateChanged( item )
        
    
    def Flip( self, index: int ):
        
        self.Check( index, not self.IsChecked( index ) )
        
    
    def GetData( self, index: int ):
        
        return self.item( index ).data( QC.Qt.ItemDataRole.UserRole )
        
    
    def GetCheckedIndices( self ) -> list[ int ]:
        
        checked_indices = [ i for i in range( self.count() ) if self.IsChecked( i ) ]
        
        return checked_indices
        
    
    def GetSelectedIndices( self ):
        
        selected_indices = [ i for i in range( self.count() ) if self.IsSelected( i ) ]
        
        return selected_indices
        
    
    def GetValue( self ):
        
        result = [ self.GetData( index ) for index in self.GetCheckedIndices() ]
        
        return result
        
    
    def IsChecked( self, index: int ) -> bool:
        
        return self.item( index ).checkState() == QC.Qt.CheckState.Checked
        
    
    def IsSelected( self, index: int ) -> bool:
        
        return self.item( index ).isSelected()
        
    
    def SetHeightBasedOnContents( self ):
        
        num_chars = self.count()
        
        if num_chars > 32:
            
            self.SetHeightNumChars( 32 )
            
        else:
            
            self.SetHeightNumChars( num_chars, clip_virtual_size_too = True )
            
        
    
    def SetHeightNumChars( self, num_chars: int, clip_virtual_size_too = False ):
        
        row_height = self.sizeHintForRow( 0 )
        
        if row_height == -1:
            
            ( width_gumpf, row_height ) = ClientGUIFunctions.ConvertTextToPixels( self, ( 20, 1 ) )
            
        
        # ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self, ( 10, num_chars ) )
        
        height = ( row_height * num_chars ) + ( self.frameWidth() * 2 )
        
        self.setFixedHeight( height )
        
        if clip_virtual_size_too:
            
            # this fixes some weird issue where the vertical scrollbar wants to scroll down to an extra empty row
            self.viewport().setFixedHeight( row_height * num_chars )
            
        
    
    def SetValue( self, datas: collections.abc.Collection ):
        
        for index in range( self.count() ):
            
            data = self.GetData( index )
            
            check_it = data in datas
            
            self.Check( index, check_it )
            
        
    
    def mousePressEvent( self, event ):
        
        if event.button() == QC.Qt.MouseButton.RightButton:
            
            self.rightClicked.emit()
            
        else:
            
            QW.QListWidget.mousePressEvent( self, event )
            
        
    

class BetterChoice( QW.QComboBox ):
    
    def __init__( self, *args, **kwargs ):
        
        super().__init__( *args, **kwargs )
        
        self.setMaxVisibleItems( 32 )
        
    
    def addItem( self, display_string, client_data ):
        
        QW.QComboBox.addItem( self, display_string, client_data )
        
        if self.count() == 1:
            
            self.setCurrentIndex( 0 )
            
        
    
    def GetValue( self ):
        
        selection = self.currentIndex()
        
        if selection != -1:
            
            return self.itemData( selection, QC.Qt.ItemDataRole.UserRole )
            
        elif self.count() > 0:
            
            return self.itemData( 0, QC.Qt.ItemDataRole.UserRole )
            
        else:
            
            return None
            
        
    
    def SetValue( self, data ):
        
        for i in range( self.count() ):
            
            if data == self.itemData( i, QC.Qt.ItemDataRole.UserRole ):
                
                self.setCurrentIndex( i )
                
                return
                
            
        
        if self.count() > 0:
            
            self.setCurrentIndex( 0 )
            
        
    

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
        
    

class BetterSpinBox( QW.QSpinBox ):
    
    def __init__( self, parent: QW.QWidget, initial = None, min = None, max = None, width = None ):
        
        super().__init__( parent )
        
        if min is not None:
            
            self.setMinimum( min )
            
        
        if max is not None:
            
            self.setMaximum( max )
            
        
        if initial is not None:
            
            self.setValue( initial )
            
        
        if width is not None:
            
            self.setMinimumWidth( width )
            
        
    

class BetterDoubleSpinBox( QW.QDoubleSpinBox ):
    
    def __init__( self, parent: QW.QWidget, initial = None, min = None, max = None, width = None ):
        
        super().__init__( parent )
        
        if min is not None:
            
            self.setMinimum( min )
            
        
        if max is not None:
            
            self.setMaximum( max )
            
        
        if initial is not None:
            
            self.setValue( initial )
            
        
        if width is not None:
            
            self.setMinimumWidth( width )
            
        
    

class ButtonWithMenuArrow( QW.QToolButton ):
    
    def __init__( self, parent: QW.QWidget, action: QW.QAction ):
        
        super().__init__( parent )
        
        self.setPopupMode( QW.QToolButton.ToolButtonPopupMode.MenuButtonPopup )
        
        self.setToolButtonStyle( QC.Qt.ToolButtonStyle.ToolButtonTextOnly )
        
        self.setDefaultAction( action )
        
        self._menu = ClientGUIMenus.GenerateMenu( self )
        
        self._menu.installEventFilter( self )
        
        self.setMenu( self._menu )
        
        self._menu.aboutToShow.connect( self._ClearAndPopulateMenu )
        
    
    def _ClearAndPopulateMenu( self ):
        
        self._menu.clear()
        
        self._PopulateMenu( self._menu )
        
    
    def _PopulateMenu( self, menu ):
        
        raise NotImplementedError()
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == QC.QEvent.Type.Show and watched == self._menu:
                
                pos = QG.QCursor.pos()
                
                self._menu.move( pos )
                
                return True
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
class BetterRadioBox( QW.QFrame ):
    
    radioBoxChanged = QC.Signal()
    
    def __init__( self, parent, choice_tuples, vertical = False ):
        
        super().__init__( parent )
        
        self.setFrameStyle( QW.QFrame.Shape.Box | QW.QFrame.Shadow.Raised )
        
        if vertical:
            
            self.setLayout( QP.VBoxLayout() )
            
        else:
            
            self.setLayout( QP.HBoxLayout() )
            
        
        self._radio_buttons = []
        self._buttons_to_data = {}
        
        for tup in choice_tuples:
            
            if len( tup ) == 2:
                
                ( text, data ) = tup
                tooltip = None
                
            else:
                
                ( text, data, tooltip ) = tup
                
            
            radiobutton = QW.QRadioButton( text, self )
            
            if tooltip is not None:
                
                radiobutton.setToolTip( ClientGUIFunctions.WrapToolTip( tooltip ) ) 
                
            
            self._radio_buttons.append( radiobutton )
            
            self._buttons_to_data[ radiobutton ] = data
            
            radiobutton.clicked.connect( self.radioBoxChanged )
            
            self.layout().addWidget( radiobutton )
            
        
        if vertical and len( self._radio_buttons ):
            
            self._radio_buttons[0].setChecked( True )
            
        elif len( self._radio_buttons ) > 0:
            
            self._radio_buttons[-1].setChecked( True )
            
        
    
    def _GetCurrentChoiceWidget( self ):
        
        for choice in self._radio_buttons:
            
            if choice.isChecked():
                
                return choice
                
            
        
        return None
        
    
    def GetValue( self ):
        
        for ( button, data ) in self._buttons_to_data.items():
            
            if button.isChecked():
                
                return data
                
            
        
        raise Exception( 'No button selected!' )
        
    
    def setFocus( self, reason ):
        
        for button in self._radio_buttons:
            
            if button.isChecked():
                
                button.setFocus( reason )
                
                return
                
            
        
        QW.QFrame.setFocus( self, reason )
        
    
    def Select( self, index ):
        
        try:
            
            radio_button = self._radio_buttons[ index ]
            
            data = self._buttons_to_data[ radio_button ]
            
            self.SetValue( data )
            
        except:
            
            pass
            
        
    
    def SetValue( self, select_data ):
        
        for ( button, data ) in self._buttons_to_data.items():
            
            button.setChecked( data == select_data )
            
        
    

class BetterStaticText( QP.EllipsizedLabel ):
    
    def __init__( self, parent, label = None, tooltip_label = False, ellipsize_end = False, ellipsized_ideal_width_chars = 24 ):
        
        super().__init__( parent, ellipsize_end = ellipsize_end )
        
        # otherwise by default html in 'this is a <hr> parsing step' stuff renders fully lmaoooo
        self.setTextFormat( QC.Qt.TextFormat.PlainText )
        
        self._tooltip_label = tooltip_label
        
        if ellipsize_end:
            
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
                
                self.setToolTip( ClientGUIFunctions.WrapToolTip( text ) )
                
            
        
    

class BetterHyperLink( BetterStaticText ):
    
    def __init__( self, parent, label, url ):
        
        self._colours = {
            'link_color' : QG.QColor( 0, 0, 255 )
        }
        
        self._url = url
        
        super().__init__( parent, label )
        
        self.setObjectName( 'HydrusHyperlink' )
        
        self.setToolTip( ClientNetworkingFunctions.ConvertURLToHumanString( self._url ) )
        
        self.setTextFormat( QC.Qt.TextFormat.RichText )
        self.setTextInteractionFlags( QC.Qt.TextInteractionFlag.LinksAccessibleByMouse | QC.Qt.TextInteractionFlag.LinksAccessibleByKeyboard )
        
        # need this polish to load the QSS property and update self._colours
        self.style().polish( self )
        
        self.setText( '<a style="text-decoration:none; color:{};" href="{}">{}</a>'.format( self._colours[ 'link_color' ].name(), url, label ) )
        
        self.linkActivated.connect( self.Activated )
        
    
    def Activated( self ):
        
        ClientPaths.LaunchURLInWebBrowser( self._url )
        
    
    def get_link_color( self ):
        
        return self._colours[ 'link_color' ]
        
    
    def set_link_color( self, colour ):
        
        self._colours[ 'link_color' ] = colour
        
    
    link_color = QC.Property( QG.QColor, get_link_color, set_link_color )
    

class BusyCursor( object ):
    
    def __enter__( self ):
        
        QW.QApplication.setOverrideCursor( QC.Qt.CursorShape.WaitCursor )
        
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        QW.QApplication.restoreOverrideCursor()
        
    
class CheckboxManager( object ):
    
    def __init__( self ):
        
        self._additional_notify_calls = []
        
    
    def GetCurrentValue( self ):
        
        raise NotImplementedError()
        
    
    def AddNotifyCall( self, func ):
        
        self._additional_notify_calls.append( func )
        
    
    def Invert( self ):
        
        for func in self._additional_notify_calls:
            
            func()
            
        
    
class CheckboxManagerBoolean( CheckboxManager ):
    
    def __init__( self, obj, name ):
        
        super().__init__()
        
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
        
        super().Invert()
        
    

class CheckboxManagerCalls( CheckboxManager ):
    
    def __init__( self, invert_call, value_call ):
        
        super().__init__()
        
        self._invert_call = invert_call
        self._value_call = value_call
        
    
    def GetCurrentValue( self ):
        
        return self._value_call()
        
    
    def Invert( self ):
        
        self._invert_call()
        
        super().Invert()
        
    

class CheckboxManagerOptions( CheckboxManager ):
    
    def __init__( self, boolean_name ):
        
        super().__init__()
        
        self._boolean_name = boolean_name
        
    
    def GetCurrentValue( self ):
        
        new_options = CG.client_controller.new_options
        
        return new_options.GetBoolean( self._boolean_name )
        
    
    def Invert( self ):
        
        new_options = CG.client_controller.new_options
        
        new_options.InvertBoolean( self._boolean_name )
        
        if self._boolean_name == 'advanced_mode':
            
            CG.client_controller.pub( 'notify_advanced_mode' )
            
        
        CG.client_controller.pub( 'checkbox_manager_inverted' )
        CG.client_controller.pub( 'notify_new_menu_option' )
        
        super().Invert()
        
    

class ExportPatternButton( BetterButton ):
    
    def __init__( self, parent ):
        
        super().__init__( parent, 'pattern shortcuts', self._Hit )
        
    
    def _Hit( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        ClientGUIMenus.AppendMenuLabel( menu, 'click on a phrase to copy to clipboard', make_it_bold = True )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'unique numerical file id - {file_id}', 'copy "{file_id}" to the clipboard', CG.client_controller.pub, 'clipboard', 'text', '{file_id}' )
        ClientGUIMenus.AppendMenuItem( menu, 'the file\'s hash - {hash}', 'copy "{hash}" to the clipboard', CG.client_controller.pub, 'clipboard', 'text', '{hash}' )
        ClientGUIMenus.AppendMenuItem( menu, 'all the file\'s tags - {tags}', 'copy "{tags}" to the clipboard', CG.client_controller.pub, 'clipboard', 'text', '{tags}' )
        ClientGUIMenus.AppendMenuItem( menu, 'all the file\'s non-namespaced tags - {nn tags}', 'copy "{nn tags}" to the clipboard', CG.client_controller.pub, 'clipboard', 'text', '{nn tags}' )
        ClientGUIMenus.AppendMenuItem( menu, 'file order - {#}', 'copy "{#}" to the clipboard', CG.client_controller.pub, 'clipboard', 'text', '{#}' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, f'all instances of a particular namespace - [{HC.UNICODE_ELLIPSIS}]', f'copy "[{HC.UNICODE_ELLIPSIS}]" to the clipboard', CG.client_controller.pub, 'clipboard', 'text', f'[{HC.UNICODE_ELLIPSIS}]' )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, f'a particular tag, if the file has it - ({HC.UNICODE_ELLIPSIS})', f'copy "({HC.UNICODE_ELLIPSIS})" to the clipboard', CG.client_controller.pub, 'clipboard', 'text', f'({HC.UNICODE_ELLIPSIS})' )
        
        CGC.core().PopupMenu( self, menu )
        
    

class Gauge( QW.QProgressBar ):
    
    def __init__( self, *args, **kwargs ):
        
        super().__init__( *args, **kwargs )
        
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
        
    

class IconButton( ShortcutAwareToolTipMixin, QW.QPushButton ):
    
    def __init__( self, parent, bitmap_or_icon, func, *args, **kwargs ):
        
        super().__init__( parent )
        
        self.SetToolTipCallable( self.setToolTip )
        
        if isinstance( bitmap_or_icon, QG.QPixmap ):
            
            icon = QG.QIcon( bitmap_or_icon )
            icon_size = bitmap_or_icon.size()
            
        else:
            
            icon = bitmap_or_icon
            icon_size = None # QC.QSize( 16, 16 )
            
        
        self.last_icon_set = icon
        
        self.setIcon( icon )
        
        if icon_size is not None:
            
            self.setIconSize( icon_size ) # if and when we move to SVG, maybe we'll do devicePixelRatio stuff here? 16x16 * dpr?
            
        
        #self.setSizePolicy( QW.QSizePolicy.Policy.Maximum, QW.QSizePolicy.Policy.Maximum )
        
        self._func = func
        self._args = args
        self._kwargs = kwargs
        
        self.clicked.connect( self.EventButton )
        
    
    def EventButton( self ):
        
        self._func( *self._args,  **self._kwargs )
        
    
    def SetIconSmart( self, icon: QG.QIcon ):
        
        # this is actually useful as I understand. the jump to C++ copies the icon and Qt doesn't know it is the same guy
        
        if icon is self.last_icon_set:
            
            return
            
        
        self.setIcon( icon )
        
        self.last_icon_set = icon
        
    

class IconButtonMultiClickable( IconButton ):
    
    def __init__( self, parent, icon, func, right_click_func = None, middle_click_func = None ):
        
        super().__init__( parent, icon, func )
        
        self._left_click_func = func
        self._right_click_func = right_click_func
        self._middle_click_func = middle_click_func
        
    
    def mousePressEvent( self, event ):
        
        if event.button() == QC.Qt.MouseButton.RightButton and self._right_click_func is not None:
            
            self._right_click_func()
            
        elif event.button() == QC.Qt.MouseButton.MiddleButton and self._middle_click_func is not None:
            
            self._middle_click_func()
            
        else:
            
            self._left_click_func()
            
        
    

class NamespaceWidget( QW.QWidget ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        # think about updating to this to have ':' for 'namespaced', but either optionall or (ideally) all users of it would need to support that too
        
        choice_tuples = [
            ( 'any namespace', '*' ),
            ( 'unnamespaced', '' ),
            ( 'namespace', 'specific' )
        ]
        
        self._selector = BetterRadioBox( self, choice_tuples, vertical = True )
        
        self._namespace = QW.QLineEdit( self )
        
        self._namespace.setPlaceholderText( 'e.g. character' )
        self._namespace.setToolTip( ClientGUIFunctions.WrapToolTip( 'No trailing colon. Wildcards are ok!' ) )
        
        vbox = QP.VBoxLayout( margin = 0 )
        
        QP.AddToLayout( vbox, self._selector, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._namespace, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        self._selector.radioBoxChanged.connect( self._UpdateControls )
        
        self.SetValue( '*' )
        
    
    def _UpdateControls( self ):
        
        value = self._selector.GetValue()
        
        self._namespace.setEnabled( value == 'specific' )
        
    
    def GetValue( self ):
        
        value = self._selector.GetValue()
        
        if value in ( '', '*' ):
            
            return value
            
        
        return self._namespace.text()
        
    
    def SetValue( self, value ):
        
        if value is None:
            
            value = '*'
            
        
        if value in ( '', '*' ):
            
            self._selector.SetValue( value )
            
        else:
            
            self._selector.SetValue( 'specific' )
            
            self._namespace.setText( value )
            
        
        self._UpdateControls()
        
    

class NoneableSpinCtrl( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, default_int: int, message = '', none_phrase = 'no limit', min = 0, max = 1000000, unit = None, multiplier = 1 ):
        
        super().__init__( parent )
        
        self._unit = unit
        self._multiplier = multiplier
        
        self._checkbox = QW.QCheckBox( self )
        self._checkbox.stateChanged.connect( self.EventCheckBox )
        self._checkbox.setText( none_phrase )
        
        self._number_value = BetterSpinBox( self, min=min, max=max )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._number_value, len( str( max ) ) + 5 )
        
        self._number_value.setMinimumWidth( width )
        
        self.SetValue( default_int )
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        if len( message ) > 0:
            
            QP.AddToLayout( hbox, BetterStaticText(self,message+': '), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        QP.AddToLayout( hbox, self._number_value, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        if self._unit is not None:
            
            QP.AddToLayout( hbox, BetterStaticText(self,self._unit), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        QP.AddToLayout( hbox, self._checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        self._number_value.valueChanged.connect( self._HandleValueChanged )
        self._checkbox.stateChanged.connect( self._HandleValueChanged )
        
        
    def _HandleValueChanged( self, val ):
        
        self.valueChanged.emit()
        
    
    def EventCheckBox( self, state ):
        
        if self._checkbox.isChecked():
            
            self._number_value.setEnabled( False )
            
        else:
            
            self._number_value.setEnabled( True )
            
        
    
    def GetValue( self ):
        
        if self._checkbox.isChecked():
            
            return None
            
        else:
            
            return self._number_value.value() * self._multiplier
            
        
    
    def setToolTip( self, text ):
        
        QW.QWidget.setToolTip( self, text )
        
        for c in self.children():
            
            if isinstance( c, QW.QWidget ):
                
                c.setToolTip( text )
            
        
    
    def SetValue( self, value ):
        
        if value is None:
            
            self._checkbox.setChecked( True )
            
            self._number_value.setEnabled( False )
            
        else:
            
            self._checkbox.setChecked( False )
            
            self._number_value.setEnabled( True )
            
            self._number_value.setValue( value // self._multiplier )
            
        
    

class NoneableDoubleSpinCtrl( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, default_ints, message = '', none_phrase = 'no limit', min = 0, max = 1000000, unit = None, multiplier = 1 ):
        
        super().__init__( parent )
        
        self._unit = unit
        self._multiplier = multiplier
        
        self._checkbox = QW.QCheckBox( self )
        self._checkbox.stateChanged.connect( self.EventCheckBox )
        self._checkbox.setText( none_phrase )
        
        self._one = BetterSpinBox( self, min=min, max=max )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._one, len( str( max ) ) + 5 )
        
        self._one.setMaximumWidth( width )
        
        self._two = BetterSpinBox( self, initial=0, min=min, max=max )
        self._two.valueChanged.connect( self._HandleValueChanged )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._two, len( str( max ) ) + 5 )
        
        self._two.setMinimumWidth( width )
        
        self.SetValue( default_ints )
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        if len( message ) > 0:
            
            QP.AddToLayout( hbox, BetterStaticText(self,message+': '), CC.FLAGS_CENTER_PERPENDICULAR )
            
        
        QP.AddToLayout( hbox, self._one, CC.FLAGS_CENTER_PERPENDICULAR )
        
        QP.AddToLayout( hbox, BetterStaticText(self,'x'), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._two, CC.FLAGS_CENTER_PERPENDICULAR )
        
        if self._unit is not None:
            
            QP.AddToLayout( hbox, BetterStaticText(self,self._unit), CC.FLAGS_CENTER_PERPENDICULAR )
                
        
        QP.AddToLayout( hbox, self._checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox.addStretch( 0 )
        
        self.setLayout( hbox )
        
        self._one.valueChanged.connect( self._HandleValueChanged )
        self._checkbox.stateChanged.connect( self._HandleValueChanged )
        
        
    def _HandleValueChanged( self, val ):
        
        self.valueChanged.emit()
        
    
    def EventCheckBox( self, state ):
        
        if self._checkbox.isChecked():
            
            self._one.setEnabled( False )
            self._two.setEnabled( False )
            
        else:
            
            self._one.setEnabled( True )
            self._two.setEnabled( True )
            
        
    
    def GetValue( self ):
        
        if self._checkbox.isChecked():
            
            return None
            
        else:
            
            return ( self._one.value() * self._multiplier, self._two.value() * self._multiplier )
            
        
    
    def setToolTip( self, text ):
        
        QW.QWidget.setToolTip( self, text )
        
        for c in self.children():
            
            if isinstance( c, QW.QWidget ):
                
                c.setToolTip( text )
                
            
        
    
    def SetValue( self, value ):
        
        if value is None:
            
            self._checkbox.setChecked( True )
            
            self._one.setEnabled( False )
            self._two.setEnabled( False )
            
        else:
            
            self._checkbox.setChecked( False )
            
            ( x, y ) = value
            
            self._one.setValue( x // self._multiplier )
            self._two.setValue( y // self._multiplier )
            
            self._one.setEnabled( True )
            self._two.setEnabled( True )
            
        
    

class NoneableTextCtrl( QW.QWidget ):

    valueChanged = QC.Signal()
    
    def __init__( self, parent, default_text, message = '', placeholder_text = '', none_phrase = 'none', min_chars_width: int | None = None ):
        
        super().__init__( parent )
        
        self._checkbox = QW.QCheckBox( self )
        self._checkbox.stateChanged.connect( self.EventCheckBox )
        self._checkbox.setText( none_phrase )
        
        self._text = QW.QLineEdit( self )
        
        if default_text != '':
            
            self._text.setText( default_text )
            
        
        if placeholder_text != '':
            
            self._text.setPlaceholderText( placeholder_text )
            
        
        if min_chars_width is not None:
            
            self._text.setMinimumWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._text, min_chars_width ) )
            
        
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
            
        
    
    def setPlaceholderText( self, text: str ):
        
        self._text.setPlaceholderText( text )
        
    
    def setReadOnly( self, value: bool ):
        
        self._text.setReadOnly( value )
        self._checkbox.setEnabled( not value )
        
    
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
        
        super().__init__( parent )
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
        
    

class StaticBox( QW.QFrame ):
    
    def __init__( self, parent, title, can_expand = False, start_expanded = True, expanded_size_vertical_policy = QW.QSizePolicy.Policy.Fixed ):
        
        super().__init__( parent )
        
        self.setFrameStyle( QW.QFrame.Shape.Box | QW.QFrame.Shadow.Raised )
        self._spacer = QW.QSpacerItem( 0, 0, QW.QSizePolicy.Policy.Minimum, QW.QSizePolicy.Policy.MinimumExpanding )
        
        normal_font = self.font()
        
        normal_font_size = normal_font.pointSize()
        normal_font_family = normal_font.family()
        
        title_font = QG.QFont( normal_font_family, int( normal_font_size ), QG.QFont.Weight.Bold )
        
        self._title_st = BetterStaticText( self, label = title )
        self._title_st.setFont( title_font )
        
        self._expanded_size_vertical_policy = expanded_size_vertical_policy
        
        self._expand_button = BetterButton( self, label = '\u25B2', func = self.ExpandCollapse )
        self._expand_button.setFixedWidth( ClientGUIFunctions.ConvertTextToPixelWidth( self._expand_button, 4 ) )
        
        self._content_panel = QW.QWidget( self )
        
        if not can_expand:
            
            self._expand_button.hide()
            
        
        button_hbox = QP.HBoxLayout( 0, 0 )
        
        QP.AddToLayout( button_hbox, QW.QWidget( self ), CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( button_hbox, self._expand_button, CC.FLAGS_ON_RIGHT )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, QW.QWidget( self ), CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._title_st, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, button_hbox, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._content_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self._sizer = QP.VBoxLayout()
        
        self._content_panel.setLayout( self._sizer )
        
        self._sizer.addSpacerItem( self._spacer )
        
        self._expanded = True
        
        if not start_expanded:
            
            self.ExpandCollapse()
            
        
    
    def Add( self, widget, flags = None ):
        
        self._sizer.removeItem( self._spacer )
        
        QP.AddToLayout( self._sizer, widget, flags )
        
        self._sizer.addSpacerItem( self._spacer )
        
    
    def ExpandCollapse( self ):
        
        if self._expanded:
            
            new_label = '\u25BC'
            
            size_policy = self.sizePolicy()
            
            size_policy.setVerticalPolicy( QW.QSizePolicy.Policy.Fixed )
            
            self.setSizePolicy( size_policy )
            
        else:
            
            new_label = '\u25B2'
            
            size_policy = self.sizePolicy()
            
            size_policy.setVerticalPolicy( self._expanded_size_vertical_policy )
            
            self.setSizePolicy( size_policy )
            
        
        self._expand_button.setText( new_label )
        
        self._expanded = not self._expanded
        
        self._content_panel.setVisible( self._expanded )
        
        self.window().layout()
        
    
    def IsExpanded( self ):
        
        return self._expanded
        
    
    def SetTitle( self, title ):
        
        self._title_st.setText( title )
        
    

class TextCatchEnterEventFilter( QC.QObject ):
    
    def __init__( self, parent, callable, *args, **kwargs ):
        
        super().__init__( parent )
        
        self._callable = HydrusData.Call( callable, *args, **kwargs )
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == QC.QEvent.Type.KeyPress:
                
                event = typing.cast( QG.QKeyEvent, event )
                
                if event.key() in ( QC.Qt.Key.Key_Enter, QC.Qt.Key.Key_Return ):
                    
                    self._callable()
                    
                    event.accept()
                    
                    return True
                    
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    

class TextAndGauge( QW.QWidget ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._st = BetterStaticText( self, tooltip_label = True )
        self._gauge = Gauge( self )
        
        vbox = QP.VBoxLayout( margin = 0 )
        
        QP.AddToLayout( vbox, self._st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
    
    def SetText( self, text ):
        
        self._st.setText( text )
        
    
    def SetValue( self, text, value, range ):
        
        self._st.setText( text )
        
        self._gauge.SetRange( range )
        self._gauge.SetValue( value )
        
    

class WindowDragButton( IconButton ):
    
    def __init__( self, parent, icon, func, target_window ):
        
        super().__init__( parent, icon, func )
        
        self._target_window = target_window
        
        self._original_icon = icon
        
    
    def mousePressEvent( self, event ):
        
        if event.button() == QC.Qt.MouseButton.LeftButton:
            
            self._startDrag()
            
            self.SetIconSmart( CC.global_icons().move_cursor )
            
        elif event.button() == QC.Qt.MouseButton.RightButton:
            
            self._func()
            
        else:
            
            super().mousePressEvent( event )
            
        
    
    def mouseReleaseEvent(self, event):
        
        if event.button() == QC.Qt.MouseButton.LeftButton:
            
            self.SetIconSmart( self._original_icon )
            
        
        super().mouseReleaseEvent( event )
        
    
    def _startDrag( self ):
        
        if self._target_window is not None:
            
            window_handle = self._target_window.windowHandle()
            
            if window_handle is not None:
                
                window_handle.startSystemMove()
                
            
        
    
