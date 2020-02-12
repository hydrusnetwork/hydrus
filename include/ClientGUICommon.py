from . import ClientCaches
from . import ClientData
from . import ClientConstants as CC
from . import ClientGUIFunctions
from . import ClientGUIMenus
from . import ClientGUITopLevelWindows
from . import ClientMedia
from . import ClientPaths
from . import ClientRatings
from . import ClientThreading
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusText
import os
import re
import sys
import threading
import time
import traceback
from . import QtPorting as QP
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
from . import QtPorting as QP

CANVAS_MEDIA_VIEWER = 0
CANVAS_PREVIEW = 1

canvas_str_lookup = {}

canvas_str_lookup[ CANVAS_MEDIA_VIEWER ] = 'media viewer'
canvas_str_lookup[ CANVAS_PREVIEW ] = 'preview'

def WrapInGrid( parent, rows, expand_text = False, add_stretch_at_end = True ):
    
    gridbox = QP.GridLayout( cols = 2 )
    
    if expand_text:
        
        gridbox.setColumnStretch( 0, 1 )
        
        text_flags = CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY # Trying to expand both ways nixes the center. This seems to work right.
        control_flags = CC.FLAGS_VCENTER
        sizer_flags = CC.FLAGS_SIZER_VCENTER
        
    else:
        
        gridbox.setColumnStretch( 1, 1 )
        
        text_flags = CC.FLAGS_VCENTER
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
        
    if add_stretch_at_end: gridbox.setRowStretch( gridbox.rowCount(), 1 )
    
    return gridbox
    
def WrapInText( control, parent, text, colour = None ):
    
    hbox = QP.HBoxLayout()
    
    st = BetterStaticText( parent, text )
    
    if colour is not None:
        
        QP.SetForegroundColour( st, colour )
        
    
    QP.AddToLayout( hbox, st, CC.FLAGS_VCENTER )
    QP.AddToLayout( hbox, control, CC.FLAGS_EXPAND_BOTH_WAYS )
    
    return hbox
    
class ShortcutAwareToolTipMixin( object ):
    
    def __init__( self, tt_callable ):
        
        self._tt_callable = tt_callable
        
        self._tt = ''
        self._simple_shortcut_command = None
        
        HG.client_controller.sub( self, 'NotifyNewShortcuts', 'notify_new_shortcuts_gui' )
        
    
    def _RefreshToolTip( self ):
        
        tt = self._tt
        
        if self._simple_shortcut_command is not None:
            
            tt += os.linesep * 2
            tt += '----------'
            
            names_to_shortcuts = HG.client_controller.shortcuts_manager.GetNamesToShortcuts( self._simple_shortcut_command )
            
            if len( names_to_shortcuts ) > 0:
                
                names = list( names_to_shortcuts.keys() )
                
                names.sort()
                
                for name in names:
                    
                    shortcuts = names_to_shortcuts[ name ]
                    
                    shortcut_strings = [ shortcut.ToString() for shortcut in shortcuts ]
                    
                    shortcut_strings.sort()
                    
                    tt += os.linesep * 2
                    
                    tt += ', '.join( shortcut_strings )
                    tt += os.linesep
                    tt += '({}->{})'.format( name, self._simple_shortcut_command )
                    
                
            else:
                
                tt += os.linesep * 2
                
                tt += 'no shortcuts set'
                tt += os.linesep
                tt += '({})'.format( self._simple_shortcut_command )
                
            
        
        self._tt_callable( tt )
        
    
    def NotifyNewShortcuts( self ):
        
        self._RefreshToolTip()
        
    
    def SetToolTipWithShortcuts( self, tt, simple_shortcut_command ):
        
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
        self.clicked.connect( self.EventButton )
        
    
    def EventButton( self ):
        
        self._func( *self._args,  **self._kwargs )
        
    
    def setText( self, label ):
        
        button_label = QP.EscapeMnemonics( label )
        
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
            
            return QP.GetClientData( self, selection )
            
        elif self.count() > 0:
            
            return QP.GetClientData( self, 0 )
            
        else:
            
            return None
            
        
    
    def SetValue( self, data ):
        
        for i in range( self.count() ):
            
            if data == QP.GetClientData( self, i ):
                
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
        
        HG.client_controller.PopupMenu( self, menu )
        
    
class BetterNotebook( QW.QTabWidget ):
    
    def _ShiftSelection( self, delta ):
        
        existing_selection = self.currentIndex()
        
        if existing_selection != -1:
            
            new_selection = ( existing_selection + delta ) % self.count()
            
            if new_selection != existing_selection:
                
                self.setCurrentIndex( new_selection )
                
            
        
    
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
        
    
class BetterRadioBox( QP.RadioBox ):
    
    def __init__( self, *args, **kwargs ):
        
        self._indices_to_data = { i : data for ( i, ( s, data ) ) in enumerate( kwargs[ 'choices' ] ) }
        
        kwargs[ 'choices' ] = [ s for ( s, data ) in kwargs[ 'choices' ] ]
        
        QP.RadioBox.__init__( self, *args, **kwargs )
        
    
    def GetValue( self ):
        
        index = self.GetCurrentIndex()
        
        return self._indices_to_data[ index ]
        
    
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
            
            ( x, y ) = kwargs[ 'size' ].toTuple()
            
            self.setFixedSize( x, y )
        
    
    def _Draw( self, painter ):
        
        raise NotImplementedError()
        
    
    def paintEvent( self, event ):
        
        painter = QG.QPainter( self )
        
        self._Draw( painter )
        
    
class BufferedWindowIcon( BufferedWindow ):
    
    def __init__( self, parent, bmp ):
        
        BufferedWindow.__init__( self, parent, size = bmp.size() )
        
        self._bmp = bmp
        
    
    def _Draw( self, painter ):
        
        background_colour = QP.GetBackgroundColour( self.parentWidget() )
        
        painter.setBackground( QG.QBrush( background_colour ) )
        
        painter.eraseRect( painter.viewport() )
        
        if isinstance( self._bmp, QG.QImage ):
            
            painter.drawImage( 0, 0, self._bmp )
            
        else:
            
            painter.drawPixmap( 0, 0, self._bmp )
            
        
    
class CheckboxCollect( QW.QWidget ):
    
    def __init__( self, parent, management_controller = None, silent = False ):
        
        QW.QWidget.__init__( self, parent )
        
        # this is trash, rewrite it to deal with the media_collect object, not the management controller
        
        self._management_controller = management_controller
        
        if self._management_controller is not None and self._management_controller.HasVariable( 'media_collect' ):
            
            self._media_collect = self._management_controller.GetVariable( 'media_collect' )
            
        else:
            
            self._media_collect = HG.client_controller.new_options.GetDefaultCollect()
            
        
        self._silent = silent
        
        self._collect_comboctrl = QP.CollectComboCtrl( self, self._media_collect )
        
        self._collect_unmatched = BetterChoice( self )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._collect_unmatched, 19 )
        
        self._collect_unmatched.setMinimumWidth( width )
        
        self._collect_unmatched.addItem( 'collect unmatched', True )
        self._collect_unmatched.addItem( 'leave unmatched', False )
        
        #
        
        self._collect_unmatched.SetValue( self._media_collect.collect_unmatched )
        
        #
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._collect_comboctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._collect_unmatched, CC.FLAGS_VCENTER )
        
        self.setLayout( hbox )
        
        #
        
        self._collect_comboctrl.SetValue( 'no collections' ) # initialising to this because if there are no collections, no broadcast call goes through
        
        self._collect_unmatched.currentIndexChanged.connect( self.CollectValuesChanged )
        self._collect_comboctrl.itemChanged.connect( self.CollectValuesChanged )
        
    
    def GetValue( self ):
        
        return self._media_collect
        
    
    def CollectValuesChanged( self ):
        
        ( namespaces, rating_service_keys, description ) = self._collect_comboctrl.GetValues()
        
        collect_unmatched = self._collect_unmatched.GetValue()
        
        self._media_collect = ClientMedia.MediaCollect( namespaces = namespaces, rating_service_keys = rating_service_keys, collect_unmatched = collect_unmatched )
        
        self._collect_comboctrl.SetValue( description )
        
        if not self._silent and self._management_controller is not None:
            
            self._management_controller.SetVariable( 'media_collect', self._media_collect )
            
            page_key = self._management_controller.GetKey( 'page' )
            
            HG.client_controller.pub( 'collect_media', page_key, self._media_collect )
            
        
    
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
        
        HG.client_controller.pub( 'checkbox_manager_inverted' )
        
    
class ChoiceSort( QW.QWidget ):
    
    sortChanged = QC.Signal( ClientMedia.MediaSort )
    
    def __init__( self, parent, management_controller = None ):
        
        QW.QWidget.__init__( self, parent )
        
        self._management_controller = management_controller
        
        self._sort_type_choice = BetterChoice( self )
        self._sort_asc_choice = BetterChoice( self )
        
        asc_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._sort_asc_choice, 15 )
        
        self._sort_asc_choice.setMinimumWidth( asc_width )
        
        sort_types = ClientData.GetSortTypeChoices()
        
        choice_tuples = []
        
        for sort_type in sort_types:
            
            example_sort = ClientMedia.MediaSort( sort_type, CC.SORT_ASC )
            
            choice_tuples.append( ( example_sort.GetSortTypeString(), sort_type ) )
            
        
        choice_tuples.sort()
        
        for ( display_string, value ) in choice_tuples:
            
            self._sort_type_choice.addItem( display_string, value )
            
        
        type_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._sort_type_choice, 10 )
        
        self._sort_type_choice.setMinimumWidth( type_width )
        
        self._sort_asc_choice.addItem( '', CC.SORT_ASC )
        
        self._UpdateAscLabels()
        
        #
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._sort_type_choice, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._sort_asc_choice, CC.FLAGS_VCENTER )
        
        self.setLayout( hbox )
        
        HG.client_controller.sub( self, 'ACollectHappened', 'collect_media' )
        HG.client_controller.sub( self, 'BroadcastSort', 'do_page_sort' )
        
        if self._management_controller is not None and self._management_controller.HasVariable( 'media_sort' ):
            
            media_sort = self._management_controller.GetVariable( 'media_sort' )
            
            try:
                
                self.SetSort( media_sort )
                
            except:
                
                default_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
                
                self.SetSort( default_sort )
                
            
        
        self._sort_type_choice.currentIndexChanged.connect( self.EventSortTypeChoice )
        self._sort_asc_choice.currentIndexChanged.connect( self.EventSortAscChoice )
        
    
    def _BroadcastSort( self ):
        
        media_sort = self._GetCurrentSort()
        
        self.sortChanged.emit( media_sort )
        
        if self._management_controller is not None:
            
            self._management_controller.SetVariable( 'media_sort', media_sort )
            
            page_key = self._management_controller.GetKey( 'page' )
            
            HG.client_controller.pub( 'sort_media', page_key, media_sort )
            
        
    
    def _GetCurrentSort( self ):
        
        sort_type = self._sort_type_choice.GetValue()
        sort_asc = self._sort_asc_choice.GetValue()
        
        media_sort = ClientMedia.MediaSort( sort_type, sort_asc )
        
        return media_sort
        
    
    def _UpdateAscLabels( self, set_default_asc = False ):
        
        media_sort = self._GetCurrentSort()
        
        self._sort_asc_choice.clear()
        
        if media_sort.CanAsc():
            
            ( asc_str, desc_str, default_asc ) = media_sort.GetSortAscStrings()
            
            self._sort_asc_choice.addItem( asc_str, CC.SORT_ASC )
            self._sort_asc_choice.addItem( desc_str, CC.SORT_DESC )
            
            if set_default_asc:
                
                asc_to_set = default_asc
                
            else:
                
                asc_to_set = media_sort.sort_asc
                
            
            self._sort_asc_choice.SetValue( asc_to_set )
            
            self._sort_asc_choice.setEnabled( True )
            
        else:
            
            self._sort_asc_choice.addItem( '', CC.SORT_ASC )
            self._sort_asc_choice.addItem( '', CC.SORT_DESC )
            
            self._sort_asc_choice.SetValue( CC.SORT_ASC )
            
            self._sort_asc_choice.setEnabled( False )
            
        
    
    def _UserChoseASort( self ):
        
        if HG.client_controller.new_options.GetBoolean( 'save_page_sort_on_change' ):
            
            media_sort = self._GetCurrentSort()
            
            HG.client_controller.new_options.SetDefaultSort( media_sort )
            
        
    
    def ACollectHappened( self, page_key, media_collect ):
        
        if self._management_controller is not None:
            
            my_page_key = self._management_controller.GetKey( 'page' )
            
            if page_key == my_page_key:
                
                self._BroadcastSort()
                
            
        
    
    def BroadcastSort( self, page_key = None ):
        
        if page_key is not None and page_key != self._management_controller.GetKey( 'page' ):
            
            return
            
        
        self._BroadcastSort()
        
    
    def EventSortAscChoice( self, index ):
        
        self._UserChoseASort()
        
        self._BroadcastSort()
        
    
    def EventSortTypeChoice( self, index ):
        
        self._UserChoseASort()
        
        self._UpdateAscLabels( set_default_asc = True )
        
        self._BroadcastSort()
        
    
    def GetSort( self ):
        
        return self._GetCurrentSort()
        
    
    def SetSort( self, media_sort ):
        
        self._sort_type_choice.SetValue( media_sort.sort_type )
        self._sort_asc_choice.SetValue( media_sort.sort_asc )
        
        self._UpdateAscLabels()
        
    
class AlphaColourControl( QW.QWidget ):
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        self._colour_picker = BetterColourControl( self )
        
        self._alpha_selector = QP.MakeQSpinBox( self, min=0, max=255 )
        
        hbox = QP.HBoxLayout( spacing = 5 )
        
        QP.AddToLayout( hbox, self._colour_picker, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, BetterStaticText(self,'alpha:'), CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._alpha_selector, CC.FLAGS_VCENTER )
        
        hbox.addStretch( 1 )
        
        self.setLayout( hbox )
        
    
    def GetValue( self ):
        
        colour = self._colour_picker.GetColour()
        
        ( r, g, b, a ) = colour.toTuple() # no alpha support here, so it'll be 255
        
        a = self._alpha_selector.value()
        
        colour = QG.QColor( r, g, b, a )
        
        return colour
        
    
    def SetValue( self, colour ):
        
        ( r, g, b, a ) = colour.toTuple()
        
        picker_colour = QG.QColor( r, g, b )
        
        self._colour_picker.SetColour( picker_colour )
        
        self._alpha_selector.setValue( a )
        
    
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
        
        HG.client_controller.PopupMenu( self, menu )
        
    
class Gauge( QW.QProgressBar ):
    
    def __init__( self, *args, **kwargs ):
        
        QW.QProgressBar.__init__( self, *args, **kwargs )
        
        self._actual_value = None
        self._actual_range = None
        
        self._is_pulsing = False
        
    
    def GetValueRange( self ):
        
        if self._actual_range is None:
            
            range = self.maximum()
            
        else:
            
            range = self._actual_range
            
        
        return ( self._actual_value, range )
        
    
    def SetRange( self, range ):
        
        if range is None:
            
            self.Pulse()
            
            self._is_pulsing = True
            
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
                
                self._is_pulsing = True
                
            else:
                
                if self._actual_range is not None:
                    
                    value = min( int( 1000 * ( value / self._actual_range ) ), 1000 )
                    
                
                value = min( value, self.maximum() )
                
                if value != self.value():
                    
                    QW.QProgressBar.setValue( self, value )
                    
                
            
        
    
    def StopPulsing( self ):
        
        self._is_pulsing = False
        
        self.SetRange( 1 )
        self.SetValue( 1 )
        self.SetValue( 0 )
        
    
    def Pulse( self ):
        
        self.setMaximum( 0 )
        
        self.setMinimum( 0 )
        
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
            
            i_key = QP.GetClientData( self._list_box, i )
            
            if i_key == key:
                
                return i
                
            
        
        return -1
        
    
    def _Select( self, selection ):
        
        if selection == -1:
            
            self._current_key = None
            
        else:
            
            self._current_key = QP.GetClientData( self._list_box, selection )
            
        
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
                
            
        
    
class MenuBitmapButton( BetterBitmapButton ):
    
    def __init__( self, parent, bitmap, menu_items ):
        
        BetterBitmapButton.__init__( self, parent, bitmap, self.DoMenu )
        
        self._menu_items = menu_items
        
    
    def DoMenu( self ):
        
        menu = QW.QMenu()
        
        for ( item_type, title, description, data ) in self._menu_items:
            
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
                
            
        
        HG.client_controller.PopupMenu( self, menu )
        
    
class MenuButton( BetterButton ):
    
    def __init__( self, parent, label, menu_items ):
        
        BetterButton.__init__( self, parent, label, self.DoMenu )
        
        self._menu_items = menu_items
        
    
    def DoMenu( self ):
        
        menu = QW.QMenu()
        
        for ( item_type, title, description, data ) in self._menu_items:
            
            if item_type == 'normal':
                
                callable = data
                
                ClientGUIMenus.AppendMenuItem( menu, title, description, callable )
                
            elif item_type == 'check':
                
                check_manager = data
                
                initial_value = check_manager.GetInitialValue()
                
                ClientGUIMenus.AppendMenuCheckItem( menu, title, description, initial_value, check_manager.Invert )
                
                
            elif item_type == 'separator':
                
                ClientGUIMenus.AppendSeparator( menu )
                
            elif item_type == 'label':
                
                ClientGUIMenus.AppendMenuLabel( menu, title, description )
                
            
        
        HG.client_controller.PopupMenu( self, menu )
        
    
    def SetMenuItems( self, menu_items ):
        
        self._menu_items = menu_items
        
    
class NetworkContextButton( BetterButton ):
    
    def __init__( self, parent, network_context, limited_types = None, allow_default = True ):
        
        BetterButton.__init__( self, parent, network_context.ToString(), self._Edit )
        
        self._network_context = network_context
        self._limited_types = limited_types
        self._allow_default = allow_default
        
    
    def _Edit( self ):
        
        from . import ClientGUITopLevelWindows
        from . import ClientGUIScrolledPanelsEdit
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit network context' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditNetworkContextPanel( dlg, self._network_context, limited_types = self._limited_types, allow_default = self._allow_default )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._network_context = panel.GetValue()
                
                self._Update()
                
            
        
    
    def _Update( self ):
        
        self.setText( self._network_context.ToString() )
        
    
    def GetValue( self ):
        
        return self._network_context
        
    
    def SetValue( self, network_context ):
        
        self._network_context = network_context
        
        self._Update()
        
    
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
            
            QP.AddToLayout( hbox, BetterStaticText(self,message+': '), CC.FLAGS_VCENTER )
            
        
        QP.AddToLayout( hbox, self._one, CC.FLAGS_VCENTER )
        
        if self._num_dimensions == 2:
            
            QP.AddToLayout( hbox, BetterStaticText(self,'x'), CC.FLAGS_VCENTER )
            QP.AddToLayout( hbox, self._two, CC.FLAGS_VCENTER )
            
        
        if self._unit is not None:
            
            QP.AddToLayout( hbox, BetterStaticText(self,self._unit), CC.FLAGS_VCENTER )
        
        
        QP.AddToLayout( hbox, self._checkbox, CC.FLAGS_VCENTER )
        
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
            
            QP.AddToLayout( hbox, BetterStaticText(self,message+': '), CC.FLAGS_VCENTER )
            
        
        QP.AddToLayout( hbox, self._text, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._checkbox, CC.FLAGS_VCENTER )
        
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
    
    def __init__( self, parent, page_key, topic, on_label, off_label = None, start_on = True ):
        
        if start_on: label = on_label
        else: label = off_label
        
        QW.QPushButton.__init__( self, parent )
        QW.QPushButton.setText( self, label )
        
        self._page_key = page_key
        self._topic = topic
        self._on_label = on_label
        
        if off_label is None: self._off_label = on_label
        else: self._off_label = off_label
        
        self._on = start_on
        
        if self._on: QP.SetForegroundColour( self, (0,128,0) )
        else: QP.SetForegroundColour( self, (128,0,0) )
        
        self.clicked.connect( self.EventButton )
        
        HG.client_controller.sub( self, 'HitButton', 'hit_on_off_button' )
        
    
    def EventButton( self ):
        
        if self._on:
            
            self._on = False
            
            self.setText( self._off_label )
            
            QP.SetForegroundColour( self, (128,0,0) )
            
            HG.client_controller.pub( self._topic, self._page_key, False )
            
        else:
            
            self._on = True
            
            self.setText( self._on_label )
            
            QP.SetForegroundColour( self, (0,128,0) )
            
            HG.client_controller.pub( self._topic, self._page_key, True )
            
        
    
    def IsOn( self ): return self._on
    
class RatingLike( QW.QWidget ):
    
    def __init__( self, parent, service_key ):
        
        QW.QWidget.__init__( self, parent )
        
        self._service_key = service_key
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
        self._widget_event_filter.EVT_LEFT_DOWN( self.EventLeftDown )
        self._widget_event_filter.EVT_LEFT_DCLICK( self.EventLeftDown )
        self._widget_event_filter.EVT_RIGHT_DOWN( self.EventRightDown )
        self._widget_event_filter.EVT_RIGHT_DCLICK( self.EventRightDown )
        
        self.setMinimumSize( QP.TupleToQSize( (16,16) ) )
        
    
    def _Draw( self, painter ):
        
        raise NotImplementedError()
        
    
    def EventLeftDown( self, event ):
        
        raise NotImplementedError()
        
    
    def paintEvent( self, event ):
        
        painter = QG.QPainter( self )
        
        self._Draw( painter )
        
    
    def EventRightDown( self, event ):
        
        raise NotImplementedError()
        
    
    def GetServiceKey( self ):
        
        return self._service_key
        
    
class RatingLikeDialog( RatingLike ):
    
    def __init__( self, parent, service_key ):
        
        RatingLike.__init__( self, parent, service_key )
        
        self._rating_state = ClientRatings.NULL
        
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        ( pen_colour, brush_colour ) = ClientRatings.GetPenAndBrushColours( self._service_key, self._rating_state )
        
        ClientRatings.DrawLike( painter, 0, 0, self._service_key, self._rating_state )
        
        self._dirty = False
        
    
    def EventLeftDown( self, event ):
        
        if self._rating_state == ClientRatings.LIKE: self._rating_state = ClientRatings.NULL
        else: self._rating_state = ClientRatings.LIKE
        
        self._dirty = True
        
        self.update()
        
    
    def EventRightDown( self, event ):
        
        if self._rating_state == ClientRatings.DISLIKE: self._rating_state = ClientRatings.NULL
        else: self._rating_state = ClientRatings.DISLIKE
        
        self._dirty = True
        
        self.update()
        
    
    def GetRatingState( self ):
        
        return self._rating_state
        
    
    def SetRatingState( self, rating_state ):
        
        self._rating_state = rating_state
        
        self._dirty = True
        
        self.update()
        
    
class RatingLikeCanvas( RatingLike ):

    def __init__( self, parent, service_key, canvas_key ):
        
        RatingLike.__init__( self, parent, service_key )
        
        self._canvas_key = canvas_key
        self._current_media = None
        self._rating_state = None
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
        name = service.GetName()
        
        self.setToolTip( name )
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HG.client_controller.sub( self, 'SetDisplayMedia', 'canvas_new_display_media' )
        
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self._current_media is not None:
            
            self._rating_state = ClientRatings.GetLikeStateFromMedia( ( self._current_media, ), self._service_key )
            
            ClientRatings.DrawLike( painter, 0, 0, self._service_key, self._rating_state )
            
        
        self._dirty = False
        
    
    def EventLeftDown( self, event ):
        
        if self._current_media is not None:
            
            if self._rating_state == ClientRatings.LIKE: rating = None
            else: rating = 1
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            HG.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
            
        
    
    def EventRightDown( self, event ):
        
        if self._current_media is not None:
            
            if self._rating_state == ClientRatings.DISLIKE: rating = None
            else: rating = 0
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            HG.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is not None:
            
            for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
                
                for content_update in content_updates:
                    
                    ( data_type, action, row ) = content_update.ToTuple()
                    
                    if data_type == HC.CONTENT_TYPE_RATINGS:
                        
                        hashes = content_update.GetHashes()
                        
                        if len( self._hashes.intersection( hashes ) ) > 0:
                            
                            self._dirty = True
                            
                            self.update()
                            
                            return
                            
                        
                    
                
            
        
    
    def SetDisplayMedia( self, canvas_key, media ):
        
        if canvas_key == self._canvas_key:
            
            self._current_media = media
            
            if self._current_media is None:
                
                self._hashes = set()
                
            else:
                
                self._hashes = self._current_media.GetHashes()
                
            
            self._dirty = True
            
            self.update()
            
        
    
class RatingNumerical( QW.QWidget ):
    
    def __init__( self, parent, service_key ):
        
        QW.QWidget.__init__( self, parent )
        
        self._service_key = service_key
        
        self._service = HG.client_controller.services_manager.GetService( self._service_key )
        
        self._num_stars = self._service.GetNumStars()
        self._allow_zero = self._service.AllowZero()
        
        my_width = ClientRatings.GetNumericalWidth( self._service_key )
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        
        self._widget_event_filter.EVT_LEFT_DOWN( self.EventLeftDown )
        self._widget_event_filter.EVT_LEFT_DCLICK( self.EventLeftDown )
        self._widget_event_filter.EVT_RIGHT_DOWN( self.EventRightDown )
        self._widget_event_filter.EVT_RIGHT_DCLICK( self.EventRightDown )
        
        self.setMinimumSize( QP.TupleToQSize( (my_width,16) ) )
        
    
    def _Draw( self, painter ):
        
        raise NotImplementedError()
        
    
    def _GetRatingFromClickEvent( self, event ):
        
        x = event.pos().x()
        y = event.pos().y()
        
        ( my_width, my_height ) = self.size().toTuple()
        
        # assuming a border of 2 on every side here
        
        my_active_width = my_width - 4
        my_active_height = my_height - 4
        
        x_adjusted = x - 2
        y_adjusted = y - 2
        
        if 0 <= y and y <= my_active_height:
            
            if 0 <= x and x <= my_active_width:
            
                proportion_filled = x_adjusted / my_active_width
                
                if self._allow_zero:
                    
                    rating = round( proportion_filled * self._num_stars ) / self._num_stars
                    
                else:
                    
                    rating = int( proportion_filled * self._num_stars ) / ( self._num_stars - 1 )
                    
                
                return rating
                
            
        
        return None
        
    
    def EventLeftDown( self, event ):
        
        raise NotImplementedError()
        
    
    def paintEvent( self, event ):
        
        painter = QG.QPainter( self )
        
        self._Draw( painter )
        
    
    def EventRightDown( self, event ):
        
        raise NotImplementedError()
        
    
    def GetServiceKey( self ):
        
        return self._service_key
        
    
class RatingNumericalDialog( RatingNumerical ):
    
    def __init__( self, parent, service_key ):
        
        RatingNumerical.__init__( self, parent, service_key )
        
        self._rating_state = ClientRatings.NULL
        self._rating = None
        
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        ClientRatings.DrawNumerical( painter, 0, 0, self._service_key, self._rating_state, self._rating )
        
        self._dirty = False
        
    
    def EventLeftDown( self, event ):
        
        rating = self._GetRatingFromClickEvent( event )
        
        if rating is not None:
            
            self._rating_state = ClientRatings.SET
            
            self._rating = rating
            
            self._dirty = True
            
            self.update()
            
        
    
    def EventRightDown( self, event ):
        
        self._rating_state = ClientRatings.NULL
        
        self._dirty = True
        
        self.update()
        
    
    def GetRating( self ):
        
        return self._rating
        
    
    def GetRatingState( self ):
        
        return self._rating_state
        
    
    def SetRating( self, rating ):
        
        self._rating_state = ClientRatings.SET
        
        self._rating = rating
        
        self._dirty = True
        
        self.update()
        
    
    def SetRatingState( self, rating_state ):
        
        self._rating_state = rating_state
        
        self._dirty = True
        
        self.update()
        
    
class RatingNumericalCanvas( RatingNumerical ):

    def __init__( self, parent, service_key, canvas_key ):
        
        RatingNumerical.__init__( self, parent, service_key )
        
        self._canvas_key = canvas_key
        self._current_media = None
        self._rating_state = None
        self._rating = None
        
        name = self._service.GetName()
        
        self.setToolTip( name )
        
        HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
        HG.client_controller.sub( self, 'SetDisplayMedia', 'canvas_new_display_media' )
        
    
    def _Draw( self, painter ):
        
        painter.setBackground( QG.QBrush( QP.GetBackgroundColour( self.parentWidget() ) ) )
        
        painter.eraseRect( painter.viewport() )
        
        if self._current_media is not None:
            
            ( self._rating_state, self._rating ) = ClientRatings.GetNumericalStateFromMedia( ( self._current_media, ), self._service_key )
            
            ClientRatings.DrawNumerical( painter, 0, 0, self._service_key, self._rating_state, self._rating )
            
        
        self._dirty = False
        
    
    def EventLeftDown( self, event ):
        
        if self._current_media is not None:
            
            rating = self._GetRatingFromClickEvent( event )
            
            if rating is not None:
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
                
                HG.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
                
            
        
    
    def EventRightDown( self, event ):
        
        if self._current_media is not None:
            
            rating = None
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, self._hashes ) )
            
            HG.client_controller.Write( 'content_updates', { self._service_key : ( content_update, ) } )
            
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        if self._current_media is not None:
            
            for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
                
                for content_update in content_updates:
                    
                    ( data_type, action, row ) = content_update.ToTuple()
                    
                    if data_type == HC.CONTENT_TYPE_RATINGS:
                        
                        hashes = content_update.GetHashes()
                        
                        if len( self._hashes.intersection( hashes ) ) > 0:
                            
                            self._dirty = True
                            
                            self.update()
                            
                            return
                            
                        
                    
                
            
        
    
    def SetDisplayMedia( self, canvas_key, media ):
        
        if canvas_key == self._canvas_key:
            
            self._current_media = media
            
            if self._current_media is None:
                
                self._hashes = set()
                
            else:
                
                self._hashes = self._current_media.GetHashes()
                
            
            self._dirty = True
            
            self.update()
            
        
    
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
        
        HG.client_controller.PopupMenu( self, menu )
        
    
    def _ManageFavourites( self ):
        
        regex_favourites = HC.options[ 'regex_favourites' ]
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'manage regex favourites' ) as dlg:
            
            from . import ClientGUIScrolledPanelsEdit
            
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
        
        title_text = QW.QLabel( title, self )
        title_text.setFont( title_font )
        
        QP.AddToLayout( self._sizer, title_text, CC.FLAGS_CENTER )
        
        self.setLayout( self._sizer )
        
        self.layout().addSpacerItem( self._spacer )
        
    
    def Add( self, widget, flags = None ):
        
        self.layout().removeItem( self._spacer )
        
        QP.AddToLayout( self._sizer, widget, flags )

        self.layout().addSpacerItem( self._spacer )
        
    
class StaticBoxSorterForListBoxTags( StaticBox ):
    
    def __init__( self, parent, title ):
        
        StaticBox.__init__( self, parent, title )
        
        self._sorter = BetterChoice( self )
        
        self._sorter.addItem( 'lexicographic (a-z)', CC.SORT_BY_LEXICOGRAPHIC_ASC )
        self._sorter.addItem( 'lexicographic (z-a)', CC.SORT_BY_LEXICOGRAPHIC_DESC )
        self._sorter.addItem( 'lexicographic (a-z) (group unnamespaced)', CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_ASC )
        self._sorter.addItem( 'lexicographic (z-a) (group unnamespaced)', CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC )
        self._sorter.addItem( 'lexicographic (a-z) (ignore namespace)', CC.SORT_BY_LEXICOGRAPHIC_IGNORE_NAMESPACE_ASC )
        self._sorter.addItem( 'lexicographic (z-a) (ignore namespace)', CC.SORT_BY_LEXICOGRAPHIC_IGNORE_NAMESPACE_DESC )
        self._sorter.addItem( 'incidence (desc)', CC.SORT_BY_INCIDENCE_DESC )
        self._sorter.addItem( 'incidence (asc)', CC.SORT_BY_INCIDENCE_ASC )
        self._sorter.addItem( 'incidence (desc) (grouped by namespace)', CC.SORT_BY_INCIDENCE_NAMESPACE_DESC )
        self._sorter.addItem( 'incidence (asc) (grouped by namespace)', CC.SORT_BY_INCIDENCE_NAMESPACE_ASC )
        
        self._sorter.SetValue( HC.options[ 'default_tag_sort' ] )
        
        self._sorter.currentIndexChanged.connect( self.EventSort )
        
        self.Add( self._sorter, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def ChangeTagService( self, service_key ):
        
        self._tags_box.ChangeTagService( service_key )
        
    
    def EventSort( self, index ):
        
        selection = self._sorter.currentIndex()
        
        if selection != -1:
            
            sort = QP.GetClientData( self._sorter, selection )
            
            self._tags_box.SetSort( sort )
            
        
    
    def SetTagsBox( self, tags_box ):
        
        self._tags_box = tags_box
        
        self.Add( self._tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def SetTagsByMedia( self, media, force_reload = False ):
        
        self._tags_box.SetTagsByMedia( media, force_reload = force_reload )
        
    
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
        
    
    def SetValue( self, text, value, range ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        self._st.setText( text )
        
        self._gauge.SetRange( range )
        self._gauge.SetValue( value )
        
    
