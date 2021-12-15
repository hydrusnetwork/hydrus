import collections
import itertools
import os
import threading
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientSearch
from hydrus.client import ClientSerialisable
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITagSorting
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxesData
from hydrus.client.gui.search import ClientGUISearch
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientTagSorting

class BetterQListWidget( QW.QListWidget ):
    
    def _DeleteIndices( self, indices: typing.Iterable[ int ] ):
        
        indices = sorted( indices, reverse = True )
        
        for index in indices:
            
            item = self.takeItem( index )
            
            del item
            
        
    
    def _GetDataIndices( self, datas: typing.Collection[ object ] ) -> typing.List[ int ]:
        
        indices = []
        
        for index in range( self.count() ):
            
            list_widget_item = self.item( index )
            
            data = self._GetRowData( list_widget_item )
            
            if data in datas:
                
                indices.append( index )
                
            
        
        return indices
        
    
    def _GetListWidgetItems( self, only_selected = False ):
        
        # not sure if selectedItems is always sorted, so just do it manually
        
        list_widget_items = []
        
        for index in range( self.count() ):
            
            list_widget_item = self.item( index )
            
            if only_selected and not list_widget_item.isSelected():
                
                continue
                
            
            list_widget_items.append( list_widget_item )
            
        
        return list_widget_items
        
    
    def _GetRowData( self, list_widget_item: QW.QListWidgetItem ):
        
        return list_widget_item.data( QC.Qt.UserRole )
        
    
    def _GetSelectedIndices( self ):
        
        return [ model_index.row() for model_index in self.selectedIndexes() ]
        
    
    def _MoveRow( self, index: int, distance: int ):
        
        new_index = index + distance
        
        new_index = max( 0, new_index )
        new_index = min( new_index, self.count() - 1 )
        
        if index == new_index:
            
            return
            
        
        was_selected = self.item( index ).isSelected()
        
        list_widget_item = self.takeItem( index )
        
        self.insertItem( new_index, list_widget_item )
        
        list_widget_item.setSelected( was_selected )
        
    
    def Append( self, text: str, data: object ):
        
        item = QW.QListWidgetItem()
        
        item.setText( text )
        item.setData( QC.Qt.UserRole, data )
        
        self.addItem( item )
        
    
    def DeleteData( self, datas: typing.Collection[ object ] ):
        
        indices = self._GetDataIndices( datas )
        
        self._DeleteIndices( indices )
        
    
    def DeleteSelected( self ):
        
        indices = self._GetSelectedIndices()
        
        self._DeleteIndices( indices )
        
    
    def GetData( self, only_selected: bool = False ) -> typing.List[ object ]:
        
        datas = []
        
        list_widget_items = self._GetListWidgetItems( only_selected = only_selected )
        
        for list_widget_item in list_widget_items:
            
            data = self._GetRowData( list_widget_item )
            
            datas.append( data )
            
        
        return datas
        
    
    def GetNumSelected( self ) -> int:
        
        indices = self._GetSelectedIndices()
        
        return len( indices )
        
    
    def MoveSelected( self, distance: int ):
        
        if distance == 0:
            
            return
            
        
        # if going up, -1, then do them in ascending order
        # if going down, +1, then do them in descending order
        
        indices = sorted( self._GetSelectedIndices(), reverse = distance > 0 )
        
        for index in indices:
            
            self._MoveRow( index, distance )
            
        
    
    def PopData( self, index: int ):
        
        if index < 0 or index > self.count() - 1:
            
            return None
            
        
        list_widget_item = self.item( index )
        
        data = self._GetRowData( list_widget_item )
        
        self._DeleteIndices( [ index ] )
        
        return data
        
    
    def SelectData( self, datas: typing.Collection[ object ] ):
        
        list_widget_items = self._GetListWidgetItems()
        
        for list_widget_item in list_widget_items:
            
            data = self._GetRowData( list_widget_item )
            
            list_widget_item.setSelected( data in datas )
            
        
    
class AddEditDeleteListBox( QW.QWidget ):
    
    listBoxChanged = QC.Signal()
    
    def __init__( self, parent, height_num_chars, data_to_pretty_callable, add_callable, edit_callable ):
        
        self._data_to_pretty_callable = data_to_pretty_callable
        self._add_callable = add_callable
        self._edit_callable = edit_callable
        
        QW.QWidget.__init__( self, parent )
        
        self._listbox = BetterQListWidget( self )
        self._listbox.setSelectionMode( QW.QListWidget.ExtendedSelection )
        
        self._add_button = ClientGUICommon.BetterButton( self, 'add', self._Add )
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self._Edit )
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self._Delete )
        
        self._enabled_only_on_selection_buttons = []
        
        self._permitted_object_types = []
        
        #
        
        vbox = QP.VBoxLayout()
        
        self._buttons_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( self._buttons_hbox, self._add_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( self._buttons_hbox, self._edit_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( self._buttons_hbox, self._delete_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        QP.AddToLayout( vbox, self._listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._buttons_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        #
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._listbox, ( 20, height_num_chars ) )
        
        self._listbox.setMinimumWidth( width )
        self._listbox.setMinimumHeight( height )
        
        #
        
        self._ShowHideButtons()
        
        self._listbox.itemSelectionChanged.connect( self._ShowHideButtons )
        
        if self._edit_callable is not None:
            
            self._listbox.itemDoubleClicked.connect( self._Edit )
            
        else:
            
            self._listbox.itemDoubleClicked.connect( self._Delete )
            
        
    
    def _Add( self ):
        
        try:
            
            data = self._add_callable()
            
        except HydrusExceptions.VetoException:
            
            return
            
        
        self._AddData( data )
        
        self.listBoxChanged.emit()
        
    
    def _AddAllDefaults( self, defaults_callable ):
        
        defaults = defaults_callable()
        
        for default in defaults:
            
            self._AddData( default )
            
        
        self.listBoxChanged.emit()
        
    
    def _AddData( self, data ):
        
        self._SetNonDupeName( data )
        
        pretty_data = self._data_to_pretty_callable( data )
        
        self._listbox.Append( pretty_data, data )
        
    
    def _AddSomeDefaults( self, defaults_callable ):
        
        defaults = defaults_callable()
        
        selected = False
        
        choice_tuples = [ ( self._data_to_pretty_callable( default ), default, selected ) for default in defaults ]
        
        from hydrus.client.gui import ClientGUIDialogsQuick
        
        try:
            
            defaults_to_add = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'select the defaults to add', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        for default in defaults_to_add:
            
            self._AddData( default )
            
        
        self.listBoxChanged.emit()
        
    
    def _Delete( self ):
        
        num_selected = self._listbox.GetNumSelected()
        
        if num_selected == 0:
            
            return
            
        
        from hydrus.client.gui import ClientGUIDialogsQuick
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove {} selected?'.format( HydrusData.ToHumanInt( num_selected ) ) )
        
        if result != QW.QDialog.Accepted:
            
            return
            
        
        self._listbox.DeleteSelected()
        
        self.listBoxChanged.emit()
        
    
    def _Edit( self ):
        
        for list_widget_item in self._listbox.selectedItems():
            
            data = list_widget_item.data( QC.Qt.UserRole )
            
            try:
                
                new_data = self._edit_callable( data )
                
            except HydrusExceptions.VetoException:
                
                break
                
            
            self._SetNonDupeName( new_data )
            
            pretty_new_data = self._data_to_pretty_callable( new_data )
            
            list_widget_item.setText( pretty_new_data )
            list_widget_item.setData( QC.Qt.UserRole, new_data )
            
        
        self.listBoxChanged.emit()
        
    
    def _Duplicate( self ):
        
        dupe_data = self._GetExportObject()
        
        if dupe_data is not None:
            
            dupe_data = dupe_data.Duplicate()
            
            self._ImportObject( dupe_data )
            
        
    
    def _ExportToClipboard( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            json = export_object.DumpToString()
            
            HG.client_controller.pub( 'clipboard', 'text', json )
            
        
    
    def _ExportToPNG( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            from hydrus.client.gui import ClientGUITopLevelWindowsPanels
            from hydrus.client.gui import ClientGUISerialisable
            
            with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, 'export to png' ) as dlg:
                
                panel = ClientGUISerialisable.PNGExportPanel( dlg, export_object )
                
                dlg.SetPanel( panel )
                
                dlg.exec()
                
            
        
    
    def _ExportToPNGs( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is None:
            
            return
            
        
        if not isinstance( export_object, HydrusSerialisable.SerialisableList ):
            
            self._ExportToPNG()
            
            return
            
        
        from hydrus.client.gui import ClientGUITopLevelWindowsPanels
        from hydrus.client.gui import ClientGUISerialisable
        
        with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, 'export to pngs' ) as dlg:
            
            panel = ClientGUISerialisable.PNGsExportPanel( dlg, export_object )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
        
    
    def _GetExportObject( self ):
        
        to_export = HydrusSerialisable.SerialisableList()
        
        for obj in self.GetData( only_selected = True ):
            
            to_export.append( obj )
            
        
        if len( to_export ) == 0:
            
            return None
            
        elif len( to_export ) == 1:
            
            return to_export[0]
            
        else:
            
            return to_export
            
        
    
    def _ImportFromClipboard( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
            self._ImportObject( obj )
            
        except Exception as e:
            
            QW.QMessageBox.critical( self, 'Error', 'I could not understand what was in the clipboard' )
            
        
    
    def _ImportFromPNG( self ):
        
        with QP.FileDialog( self, 'select the png or pngs with the encoded data', acceptMode = QW.QFileDialog.AcceptOpen, fileMode = QW.QFileDialog.ExistingFiles, wildcard = 'PNG (*.png)|*.png' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                for path in dlg.GetPaths():
                    
                    try:
                        
                        payload = ClientSerialisable.LoadFromPNG( path )
                        
                    except Exception as e:
                        
                        QW.QMessageBox.critical( self, 'Error', str(e) )
                        
                        return
                        
                    
                    try:
                        
                        obj = HydrusSerialisable.CreateFromNetworkBytes( payload )
                        
                        self._ImportObject( obj )
                        
                    except:
                        
                        QW.QMessageBox.critical( self, 'Error', 'I could not understand what was encoded in the png!' )
                        
                        return
                        
                    
                
            
        
    
    def _ImportObject( self, obj ):
        
        bad_object_type_names = set()
        
        if isinstance( obj, HydrusSerialisable.SerialisableList ):
            
            for sub_obj in obj:
                
                self._ImportObject( sub_obj )
                
            
        else:
            
            if isinstance( obj, self._permitted_object_types ):
                
                self._AddData( obj )
                
            else:
                
                bad_object_type_names.add( HydrusData.GetTypeName( type( obj ) ) )
                
            
        
        if len( bad_object_type_names ) > 0:
            
            message = 'The imported objects included these types:'
            message += os.linesep * 2
            message += os.linesep.join( bad_object_type_names )
            message += os.linesep * 2
            message += 'Whereas this control only allows:'
            message += os.linesep * 2
            message += os.linesep.join( ( HydrusData.GetTypeName( o ) for o in self._permitted_object_types ) )
            
            QW.QMessageBox.critical( self, 'Error', message )
            
        
        self.listBoxChanged.emit()
        
    
    def _SetNonDupeName( self, obj ):
        
        pass
        
    
    def _ShowHideButtons( self ):
        
        if self._listbox.GetNumSelected() == 0:
            
            self._edit_button.setEnabled( False )
            self._delete_button.setEnabled( False )
            
            for button in self._enabled_only_on_selection_buttons:
                
                button.setEnabled( False )
                
            
        else:
            
            self._edit_button.setEnabled( True )
            self._delete_button.setEnabled( True )
            
            for button in self._enabled_only_on_selection_buttons:
                
                button.setEnabled( True )
                
            
        
    
    def AddDatas( self, datas ):
        
        for data in datas:
            
            self._AddData( data )
            
        
        self.listBoxChanged.emit()
        
    
    def AddDefaultsButton( self, defaults_callable ):
        
        import_menu_items = []
        
        all_call = HydrusData.Call( self._AddAllDefaults, defaults_callable )
        some_call = HydrusData.Call( self._AddSomeDefaults, defaults_callable )
        
        import_menu_items.append( ( 'normal', 'add them all', 'Load all the defaults.', all_call ) )
        import_menu_items.append( ( 'normal', 'select from a list', 'Load some of the defaults.', some_call ) )
        
        button = ClientGUIMenuButton.MenuButton( self, 'add defaults', import_menu_items )
        
        QP.AddToLayout( self._buttons_hbox, button, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
    def AddImportExportButtons( self, permitted_object_types ):
        
        self._permitted_object_types = permitted_object_types
        
        export_menu_items = []
        
        export_menu_items.append( ( 'normal', 'to clipboard', 'Serialise the selected data and put it on your clipboard.', self._ExportToClipboard ) )
        export_menu_items.append( ( 'normal', 'to png', 'Serialise the selected data and encode it to an image file you can easily share with other hydrus users.', self._ExportToPNG ) )
        
        all_objs_are_named = False not in ( issubclass( o, HydrusSerialisable.SerialisableBaseNamed ) for o in self._permitted_object_types )
        
        if all_objs_are_named:
            
            export_menu_items.append( ( 'normal', 'to pngs', 'Serialise the selected data and encode it to multiple image files you can easily share with other hydrus users.', self._ExportToPNGs ) )
            
        
        import_menu_items = []
        
        import_menu_items.append( ( 'normal', 'from clipboard', 'Load a data from text in your clipboard.', self._ImportFromClipboard ) )
        import_menu_items.append( ( 'normal', 'from pngs', 'Load a data from an encoded png.', self._ImportFromPNG ) )
        
        button = ClientGUIMenuButton.MenuButton( self, 'export', export_menu_items )
        QP.AddToLayout( self._buttons_hbox, button, CC.FLAGS_CENTER_PERPENDICULAR )
        self._enabled_only_on_selection_buttons.append( button )
        
        button = ClientGUIMenuButton.MenuButton( self, 'import', import_menu_items )
        QP.AddToLayout( self._buttons_hbox, button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        button = ClientGUICommon.BetterButton( self, 'duplicate', self._Duplicate )
        QP.AddToLayout( self._buttons_hbox, button, CC.FLAGS_CENTER_PERPENDICULAR )
        self._enabled_only_on_selection_buttons.append( button )
        
        self._ShowHideButtons()
        
    
    def AddSeparator( self ):
        
        QP.AddToLayout( self._buttons_hbox, (20,20), CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def GetCount( self ):
        
        return self._listbox.count()
        
    
    def GetData( self, only_selected = False ):
        
        return self._listbox.GetData( only_selected = only_selected )
        
    
    def GetValue( self ):
        
        return self.GetData()
        
    
class AddEditDeleteListBoxUniqueNamedObjects( AddEditDeleteListBox ):
    
    def _SetNonDupeName( self, obj ):
        
        disallowed_names = { o.GetName() for o in self.GetData() }
        
        HydrusSerialisable.SetNonDupeName( obj, disallowed_names )
        
    
class QueueListBox( QW.QWidget ):
    
    listBoxChanged = QC.Signal()
    
    def __init__( self, parent, height_num_chars, data_to_pretty_callable, add_callable = None, edit_callable = None ):
        
        self._data_to_pretty_callable = data_to_pretty_callable
        self._add_callable = add_callable
        self._edit_callable = edit_callable
        
        QW.QWidget.__init__( self, parent )
        
        self._listbox = BetterQListWidget( self )
        self._listbox.setSelectionMode( QW.QListWidget.ExtendedSelection )
        
        self._up_button = ClientGUICommon.BetterButton( self, '\u2191', self._Up )
        
        self._delete_button = ClientGUICommon.BetterButton( self, 'X', self._Delete )
        
        self._down_button = ClientGUICommon.BetterButton( self, '\u2193', self._Down )
        
        self._add_button = ClientGUICommon.BetterButton( self, 'add', self._Add )
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self._Edit )
        
        if self._add_callable is None:
            
            self._add_button.hide()
            
        
        if self._edit_callable is None:
            
            self._edit_button.hide()
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        buttons_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( buttons_vbox, self._up_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( buttons_vbox, self._delete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( buttons_vbox, self._down_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, buttons_vbox, CC.FLAGS_CENTER_PERPENDICULAR )
        
        buttons_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( buttons_hbox, self._add_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( buttons_hbox, self._edit_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, buttons_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        #
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._listbox, ( 20, height_num_chars ) )
        
        self._listbox.setMinimumWidth( width )
        self._listbox.setMinimumHeight( height )
        
        #
        
        self._listbox.itemSelectionChanged.connect( self._UpdateButtons )
        
        if self._edit_callable is not None:
            
            self._listbox.itemDoubleClicked.connect( self._Edit )
            
        else:
            
            self._listbox.itemDoubleClicked.connect( self._Delete )
            
        
        self._UpdateButtons()
        
    
    def _Add( self ):
        
        try:
            
            data = self._add_callable()
            
        except HydrusExceptions.VetoException:
            
            return
            
        
        self._AddData( data )
        
        self.listBoxChanged.emit()
        
    
    def _AddData( self, data ):
        
        pretty_data = self._data_to_pretty_callable( data )
        
        self._listbox.Append( pretty_data, data )
        
    
    def _Delete( self ):
        
        num_selected = self._listbox.GetNumSelected()
        
        if num_selected == 0:
            
            return
            
        
        from hydrus.client.gui import ClientGUIDialogsQuick
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove {} selected?'.format( HydrusData.ToHumanInt( num_selected ) ) )
        
        if result == QW.QDialog.Accepted:
            
            self._listbox.DeleteSelected()
            
            self.listBoxChanged.emit()
            
        
    
    def _Down( self ):
        
        self._listbox.MoveSelected( 1 )
        
        self.listBoxChanged.emit()
        
    
    def _Edit( self ):
        
        for list_widget_item in self._listbox.selectedItems():
            
            data = list_widget_item.data( QC.Qt.UserRole )
            
            try:
                
                new_data = self._edit_callable( data )
                
            except HydrusExceptions.VetoException:
                
                break
                
            
            pretty_new_data = self._data_to_pretty_callable( new_data )
            
            list_widget_item.setText( pretty_new_data )
            list_widget_item.setData( QC.Qt.UserRole, new_data )
            
        
        self.listBoxChanged.emit()
        
    
    def _Up( self ):
        
        self._listbox.MoveSelected( -1 )
        
        self.listBoxChanged.emit()
        
    
    def _UpdateButtons( self ):
        
        if self._listbox.GetNumSelected() == 0:
            
            self._up_button.setEnabled( False )
            self._delete_button.setEnabled( False )
            self._down_button.setEnabled( False )
            
            self._edit_button.setEnabled( False )
            
        else:
            
            self._up_button.setEnabled( True )
            self._delete_button.setEnabled( True )
            self._down_button.setEnabled( True )
            
            self._edit_button.setEnabled( True )
            
        
    
    def AddDatas( self, datas ):
        
        for data in datas:
            
            self._AddData( data )
            
        
        self.listBoxChanged.emit()
        
    
    def GetCount( self ):
        
        return self._listbox.count()
        
    
    def GetData( self, only_selected = False ):
        
        return self._listbox.GetData( only_selected = only_selected )
        
    
    def Pop( self ):
        
        if self._listbox.count() == 0:
            
            return None
            
        
        return self._listbox.PopData( 0 )
        
    
class ListBox( QW.QScrollArea ):
    
    listBoxChanged = QC.Signal()
    mouseActivationOccurred = QC.Signal()
    
    TEXT_X_PADDING = 3
    
    def __init__( self, parent: QW.QWidget, child_rows_allowed: bool, terms_may_have_child_rows: bool, height_num_chars = 10, has_async_text_info = False ):
        
        QW.QScrollArea.__init__( self, parent )
        self.setFrameStyle( QW.QFrame.Panel | QW.QFrame.Sunken )
        self.setHorizontalScrollBarPolicy( QC.Qt.ScrollBarAlwaysOff )
        self.setVerticalScrollBarPolicy( QC.Qt.ScrollBarAsNeeded )
        self.setWidget( ListBox._InnerWidget( self ) )
        self.setWidgetResizable( True )
        
        self._background_colour = QG.QColor( 255, 255, 255 )
        
        self._ordered_terms = []
        self._terms_to_logical_indices = {}
        self._terms_to_positional_indices = {}
        self._positional_indices_to_terms = {}
        self._selected_terms = set()
        self._total_positional_rows = 0
        
        self._last_hit_logical_index = None
        self._last_drag_start_logical_index = None
        self._drag_started = False
        
        self._last_view_start = None
        
        self._height_num_chars = height_num_chars
        self._minimum_height_num_chars = 8
        
        self._num_rows_per_page = 0
        
        self._child_rows_allowed = child_rows_allowed
        self._terms_may_have_child_rows = terms_may_have_child_rows
        
        #
        
        self._has_async_text_info = has_async_text_info
        self._terms_to_async_text_info = {}
        self._pending_async_text_info_terms = set()
        self._currently_fetching_async_text_info_terms = set()
        self._async_text_info_lock = threading.Lock()
        self._async_text_info_shared_data = dict()
        self._async_text_info_updater = self._InitialiseAsyncTextInfoUpdater()
        
        #
        
        self.setFont( QW.QApplication.font() )
        
        self._widget_event_filter = QP.WidgetEventFilter( self.widget() )
        
        self._widget_event_filter.EVT_LEFT_DOWN( self.EventMouseSelect )
        self._widget_event_filter.EVT_RIGHT_DOWN( self.EventMouseSelect )
        
    
    def __len__( self ):
        
        return len( self._ordered_terms )
        
    
    def __bool__( self ):
        
        return QP.isValid( self )
        
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        return False
        
    
    def _ActivateFromKeyboard( self, ctrl_down, shift_down ):
        
        selected_indices = []
        
        for term in self._selected_terms:
            
            try:
                
                logical_index = self._GetLogicalIndexFromTerm( term )
                
                selected_indices.append( logical_index )
                
            except HydrusExceptions.DataMissing:
                
                pass
                
            
        
        action_occurred = self._Activate( ctrl_down, shift_down )
        
        if action_occurred and len( self._selected_terms ) == 0 and len( selected_indices ) > 0:
            
            ideal_index = min( selected_indices )
            
            ideal_indices = [ ideal_index, ideal_index - 1, 0 ]
            
            for ideal_index in ideal_indices:
                
                if ideal_index <= len( self._ordered_terms ) - 1:
                    
                    self._Hit( False, False, ideal_index )
                    
                    break
                    
                
            
        
        return action_occurred
        
    
    def _AddEditMenu( self, menu: QW.QMenu ):
        
        pass
        
    
    def _ApplyAsyncInfoToTerm( self, term, info ) -> typing.Tuple[ bool, bool ]:
        
        # this guy comes with the lock
        
        return ( False, False )
        
    
    def _DeleteActivate( self ):
        
        pass
        
    
    def _AppendTerms( self, terms ):
        
        previously_selected_terms = { term for term in terms if term in self._selected_terms }
        
        clear_terms = [ term for term in terms if term in self._terms_to_logical_indices ]
        
        if len( clear_terms ) > 0:
            
            self._RemoveTerms( clear_terms )
            
        
        for term in terms:
            
            self._ordered_terms.append( term )
            
            self._terms_to_logical_indices[ term ] = len( self._ordered_terms ) - 1
            self._terms_to_positional_indices[ term ] = self._total_positional_rows
            self._positional_indices_to_terms[ self._total_positional_rows ] = term
            
            if self._has_async_text_info:
                
                # goes before getrowcount so we can populate if needed
                
                self._StartAsyncTextInfoLookup( term )
                
            
            self._total_positional_rows += term.GetRowCount( self._child_rows_allowed )
            
        
        if len( previously_selected_terms ) > 0:
            
            self._selected_terms.update( previously_selected_terms )
            
        
    
    def _Clear( self ):
        
        self._ordered_terms = []
        self._selected_terms = set()
        self._terms_to_logical_indices = {}
        self._terms_to_positional_indices = {}
        self._positional_indices_to_terms = {}
        self._total_positional_rows = 0
        
        self._last_hit_logical_index = None
        
        self._last_view_start = None
        
    
    def _DataHasChanged( self ):
        
        self._SetVirtualSize()
        
        self.widget().update()
        
        self.listBoxChanged.emit()
        
    
    def _Deselect( self, index ):
        
        term = self._GetTermFromLogicalIndex( index )
        
        self._selected_terms.discard( term )
        
    
    def _DeselectAll( self ):
        
        self._selected_terms = set()
        
    
    def _GetLogicalIndexFromTerm( self, term ):
        
        if term in self._terms_to_logical_indices:
            
            return self._terms_to_logical_indices[ term ]
            
        
        raise HydrusExceptions.DataMissing()
        
    
    def _GetLogicalIndexUnderMouse( self, mouse_event ):
        
        y = mouse_event.pos().y()
        
        if mouse_event.type() == QC.QEvent.MouseMove:
            
            visible_rect = QP.ScrollAreaVisibleRect( self )
            
            visible_rect_y = visible_rect.y()
            
            y += visible_rect_y
            
        
        text_height = self.fontMetrics().height()
        
        positional_index = y // text_height
        
        if positional_index >= self._total_positional_rows:
            
            return None
            
        
        ( logical_index, positional_index ) = self._GetLogicalIndicesFromPositionalIndex( positional_index )
        
        return logical_index
        
    
    def _GetLogicalIndicesFromPositionalIndex( self, positional_index: int ):
        
        if positional_index < 0 or positional_index >= self._total_positional_rows:
            
            return ( None, positional_index )
            
        
        while positional_index not in self._positional_indices_to_terms and positional_index >= 0:
            
            positional_index -= 1
            
        
        if positional_index < 0:
            
            return ( None, 0 )
            
        
        return ( self._terms_to_logical_indices[ self._positional_indices_to_terms[ positional_index ] ], positional_index )
        
    
    def _GetPositionalIndexFromLogicalIndex( self, logical_index: int ):
        
        try:
            
            term = self._GetTermFromLogicalIndex( logical_index )
            
        except HydrusExceptions.DataMissing:
            
            return 0
            
        
        return self._terms_to_positional_indices[ term ]
        
    
    def _GetPredicatesFromTerms( self, terms: typing.Collection[ ClientGUIListBoxesData.ListBoxItem ] ):
        
        return list( itertools.chain.from_iterable( ( term.GetSearchPredicates() for term in terms ) ) )
        
    
    def _GetRowsOfTextsAndColours( self, term: ClientGUIListBoxesData.ListBoxItem ):
        
        raise NotImplementedError()
        
    
    def _GetSelectedPredicatesAndInverseCopies( self ):
        
        predicates = self._GetPredicatesFromTerms( self._selected_terms )
        inverse_predicates = [ predicate.GetInverseCopy() for predicate in predicates if predicate.IsInvertible() ]
        
        if len( predicates ) > 1 and ClientSearch.PREDICATE_TYPE_OR_CONTAINER not in ( p.GetType() for p in predicates ):
            
            or_predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, value = list( predicates ) )
            
        else:
            
            or_predicate = None
            
        
        namespace_predicate = None
        inverse_namespace_predicate = None
        
        if False not in [ predicate.GetType() == ClientSearch.PREDICATE_TYPE_TAG for predicate in predicates ]:
            
            namespaces = { HydrusTags.SplitTag( predicate.GetValue() )[0] for predicate in predicates }
            
            if len( namespaces ) == 1:
                
                ( namespace, ) = namespaces
                
                namespace_predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, value = namespace )
                inverse_namespace_predicate = namespace_predicate.GetInverseCopy()
                
            
        
        return ( predicates, or_predicate, inverse_predicates, namespace_predicate, inverse_namespace_predicate )
        
    
    def _GetSafeHitIndex( self, logical_index, direction = None ):
        
        if direction is None:
            
            if logical_index == 0:
                
                direction = 1
                
            else:
                
                direction = -1
                
            
        
        num_terms = len( self._ordered_terms )
        
        if num_terms == 0:
            
            return None
            
        
        original_logical_index = logical_index
        
        if logical_index is not None:
            
            # if click/selection is out of bounds, fix it
            if logical_index == -1 or logical_index > num_terms:
                
                logical_index = num_terms - 1
                
            elif logical_index == num_terms or logical_index < -1:
                
                logical_index = 0
                
            
        
        return logical_index
        
    
    def _GetTagsFromTerms( self, terms: typing.Collection[ ClientGUIListBoxesData.ListBoxItem ] ):
        
        return list( itertools.chain.from_iterable( ( term.GetTags() for term in terms ) ) )
        
    
    def _GetTermFromLogicalIndex( self, logical_index ) -> ClientGUIListBoxesData.ListBoxItem:
        
        if logical_index < 0 or logical_index > len( self._ordered_terms ) - 1:
            
            raise HydrusExceptions.DataMissing( 'No term for index ' + str( logical_index ) )
            
        
        return self._ordered_terms[ logical_index ]
        
    
    def _HandleClick( self, event ):
        
        logical_index = self._GetLogicalIndexUnderMouse( event )
        
        shift = event.modifiers() & QC.Qt.ShiftModifier
        ctrl = event.modifiers() & QC.Qt.ControlModifier
        
        self._Hit( shift, ctrl, logical_index )
        

    def _Hit( self, shift, ctrl, logical_index, only_add = False ):
        
        if logical_index is not None and ( logical_index < 0 or logical_index >= len( self._ordered_terms ) ):
            
            logical_index = None
            
        
        to_select = set()
        to_deselect = set()
        
        deselect_all = False
        
        if shift:
            
            if logical_index is not None:
                
                if ctrl:
                    
                    if self._LogicalIndexIsSelected( logical_index ):
                        
                        if self._last_hit_logical_index is not None:
                            
                            lower = min( logical_index, self._last_hit_logical_index )
                            upper = max( logical_index, self._last_hit_logical_index )
                            
                            to_deselect = list( range( lower, upper + 1 ) )
                            
                        else:
                            
                            to_deselect.add( logical_index )
                            
                        
                    
                else:
                    
                    # we are now saying if you shift-click on something already selected, we'll make no changes, but we'll move focus ghost
                    if not self._LogicalIndexIsSelected( logical_index ):
                        
                        if self._last_hit_logical_index is not None:
                            
                            lower = min( logical_index, self._last_hit_logical_index )
                            upper = max( logical_index, self._last_hit_logical_index )
                            
                            to_select = list( range( lower, upper + 1 ) )
                            
                        else:
                            
                            to_select.add( logical_index )
                            
                        
                    
                
            
        elif ctrl:
            
            if logical_index is not None:
                
                if self._LogicalIndexIsSelected( logical_index ):
                    
                    to_deselect.add( logical_index )
                    
                else:
                    
                    to_select.add( logical_index )
                    
                
            
        else:
            
            if logical_index is None:
                
                deselect_all = True
                
            else:
                
                if not self._LogicalIndexIsSelected( logical_index ):
                    
                    deselect_all = True
                    to_select.add( logical_index )
                    
                
            
        
        if deselect_all:
            
            self._DeselectAll()
            
        
        for index in to_select:
            
            self._Select( index )
            
        
        for index in to_deselect:
            
            self._Deselect( index )
            
        
        self._last_hit_logical_index = logical_index
        
        if self._last_hit_logical_index is not None:
            
            text_height = self.fontMetrics().height()
            
            last_hit_positional_index = self._GetPositionalIndexFromLogicalIndex( self._last_hit_logical_index )
            
            y = text_height * last_hit_positional_index
            
            visible_rect = QP.ScrollAreaVisibleRect( self )
            
            visible_rect_y = visible_rect.y()
            
            visible_rect_height = visible_rect.height()
            
            if y < visible_rect_y:
                
                self.ensureVisible( 0, y, 0, 0 )
                
            elif y > visible_rect_y + visible_rect_height - text_height:
                
                self.ensureVisible( 0, y + text_height , 0, 0 )
                
            
        
        self.widget().update()
        
    
    def _HitFirstSelectedItem( self ):
        
        selected_indices = []
        
        if len( self._selected_terms ) > 0:
            
            for term in self._selected_terms:
                
                try:
                    
                    logical_index = self._GetLogicalIndexFromTerm( term )
                    
                    selected_indices.append( logical_index )
                    
                except HydrusExceptions.DataMissing:
                    
                    pass
                    
                
            
            if len( selected_indices ) > 0:
                
                first_logical_index = min( selected_indices )
                
                self._Hit( False, False, first_logical_index )
                
            
        
    
    def _InitialiseAsyncTextInfoUpdater( self ):
        
        def loading_callable():
            
            pass
            
        
        work_callable = self._InitialiseAsyncTextInfoUpdaterWorkCallable()
        
        def publish_callable( terms_to_info ):
            
            any_sort_info_changed = False
            any_num_rows_changed = False
            
            with self._async_text_info_lock:
                
                self._currently_fetching_async_text_info_terms.difference_update( terms_to_info.keys() )
                
                self._terms_to_async_text_info.update( terms_to_info )
                
                for ( term, info ) in terms_to_info.items():
                    
                    # ok in the time since this happened, we may have actually changed the term object, so let's cycle to the actual object in use atm!
                    if term in self._terms_to_positional_indices:
                        
                        term = self._positional_indices_to_terms[ self._terms_to_positional_indices[ term ] ]
                        
                    
                    ( sort_info_changed, num_rows_changed ) = self._ApplyAsyncInfoToTerm( term, info )
                    
                    if sort_info_changed:
                        
                        any_sort_info_changed = True
                        
                    
                    if num_rows_changed:
                        
                        any_num_rows_changed = True
                        
                    
                
            
            if any_sort_info_changed:
                
                self._Sort()
                # this does regentermstoindices
                
            elif any_num_rows_changed:
                
                self._RegenTermsToIndices()
                
            
            self._DataHasChanged()
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _InitialiseAsyncTextInfoUpdaterWorkCallable( self ):
        
        async_lock = self._async_text_info_lock
        currently_fetching = self._currently_fetching_async_text_info_terms
        pending = self._pending_async_text_info_terms
        
        def work_callable():
            
            with async_lock:
                
                to_lookup = set( pending )
                
                pending.clear()
                
                currently_fetching.update( to_lookup )
                
            
            terms_to_info = { term : None for term in to_lookup }
            
            return terms_to_info
            
        
        return work_callable
        
    
    def _LogicalIndexIsSelected( self, logical_index ):
        
        try:
            
            term = self._GetTermFromLogicalIndex( logical_index )
            
        except HydrusExceptions.DataMissing:
            
            return False
            
        
        return term in self._selected_terms
        
    
    def _Redraw( self, painter ):
        
        painter.setBackground( QG.QBrush( self._background_colour ) )
        
        painter.eraseRect( painter.viewport() )
        
        if len( self._ordered_terms ) == 0:
            
            return
            
        
        #
        
        text_height = self.fontMetrics().height()
        
        visible_rect = QP.ScrollAreaVisibleRect( self )
        
        visible_rect_y = visible_rect.y()
        
        visible_rect_width = visible_rect.width()
        visible_rect_height = visible_rect.height()
        
        first_visible_positional_index = max( 0, visible_rect_y // text_height )
        
        last_visible_positional_index = ( visible_rect_y + visible_rect_height ) // text_height
        
        if ( visible_rect_y + visible_rect_height ) % text_height != 0:
            
            last_visible_positional_index += 1
            
        
        last_visible_positional_index = max( 0, min( last_visible_positional_index, self._total_positional_rows - 1 ) )
        
        #
        
        ( first_visible_logical_index, first_visible_positional_index ) = self._GetLogicalIndicesFromPositionalIndex( first_visible_positional_index )
        ( last_visible_logical_index, last_visible_positional_index ) = self._GetLogicalIndicesFromPositionalIndex( last_visible_positional_index )
        
        # some crazy situation with ultra laggy sessions where we are rendering a zero or negative size list or something
        if first_visible_logical_index is None or last_visible_logical_index is None:
            
            return
            
        
        current_visible_index = first_visible_positional_index
        
        for logical_index in range( first_visible_logical_index, last_visible_logical_index + 1 ):
            
            term = self._GetTermFromLogicalIndex( logical_index )
            
            rows_of_texts_and_colours = self._GetRowsOfTextsAndColours( term )
            
            for texts_and_colours in rows_of_texts_and_colours:
                
                x_start = self.TEXT_X_PADDING
                y_top = current_visible_index * text_height
                
                for ( text, ( r, g, b ) ) in texts_and_colours:
                    
                    text_colour = QG.QColor( r, g, b )
                    
                    if term in self._selected_terms:
                        
                        painter.setBrush( QG.QBrush( text_colour ) )
                        
                        painter.setPen( QC.Qt.NoPen )
                        
                        if x_start == self.TEXT_X_PADDING:
                            
                            background_colour_x = 0
                            
                        else:
                            
                            background_colour_x = x_start
                            
                        
                        painter.drawRect( background_colour_x, y_top, visible_rect_width, text_height )
                        
                        text_colour = self._background_colour
                        
                    
                    painter.setPen( QG.QPen( text_colour ) )
                    
                    ( this_text_size, text ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, text )
                    
                    this_text_width = this_text_size.width()
                    this_text_height = this_text_size.height()
                    
                    painter.drawText( QC.QRectF( x_start, y_top, this_text_width, this_text_height ), text )
                    
                    x_start += this_text_width
                    
                
                current_visible_index += 1
                
            
        
    
    def _RegenTermsToIndices( self ):
        
        self._terms_to_logical_indices = {}
        self._terms_to_positional_indices = {}
        self._positional_indices_to_terms = {}
        self._total_positional_rows = 0
        
        for ( logical_index, term ) in enumerate( self._ordered_terms ):
            
            self._terms_to_logical_indices[ term ] = logical_index
            self._terms_to_positional_indices[ term ] = self._total_positional_rows
            self._positional_indices_to_terms[ self._total_positional_rows ] = term
            
            self._total_positional_rows += term.GetRowCount( self._child_rows_allowed )
            
        
    
    def _RemoveSelectedTerms( self ):
        
        self._RemoveTerms( list( self._selected_terms ) )
        
    
    def _RemoveTerms( self, terms ):
        
        removable_terms = { term for term in terms if term in self._terms_to_logical_indices }
        
        if len( removable_terms ) == 0:
            
            return
            
        
        for term in removable_terms:
            
            self._ordered_terms.remove( term )
            
        
        self._selected_terms.difference_update( removable_terms )
        
        self._RegenTermsToIndices()
        
        self._last_hit_logical_index = None
        
    
    def _Select( self, index ):
        
        try:
            
            term = self._GetTermFromLogicalIndex( index )
            
            self._selected_terms.add( term )
            
        except HydrusExceptions.DataMissing:
            
            pass
            
        
    
    def _SelectAll( self ):
        
        self._selected_terms = set( self._terms_to_logical_indices.keys() )
        
    
    def _SetVirtualSize( self ):
        
        self.setWidgetResizable( True )
        
        my_size = self.widget().size()
        
        text_height = self.fontMetrics().height()
        
        ideal_virtual_size = QC.QSize( my_size.width(), text_height * self._total_positional_rows )
        
        if ideal_virtual_size != my_size:
            
            self.widget().setMinimumSize( ideal_virtual_size )
            
        
    
    def _Sort( self ):
        
        self._ordered_terms.sort()
        
        self._RegenTermsToIndices()
        
    
    def _StartAsyncTextInfoLookup( self, term ):
        
        with self._async_text_info_lock:
            
            if term in self._terms_to_async_text_info:
                
                info = self._terms_to_async_text_info[ term ]
                
                self._ApplyAsyncInfoToTerm( term, info )
                
            elif term not in self._currently_fetching_async_text_info_terms:
                
                self._pending_async_text_info_terms.add( term )
                
                self._async_text_info_updater.update()
                
            
        
    
    def _GetAsyncTextInfoLookupCallable( self ):
        
        return lambda terms: {}
        
    
    def keyPressEvent( self, event ):
        
        shift = event.modifiers() & QC.Qt.ShiftModifier
        ctrl = event.modifiers() & QC.Qt.ControlModifier
        
        key_code = event.key()
        
        if self.hasFocus() and key_code in ClientGUIShortcuts.DELETE_KEYS_QT:
            
            self._DeleteActivate()
            
        elif key_code in ( QC.Qt.Key_Enter, QC.Qt.Key_Return ):
            
            self._ActivateFromKeyboard( ctrl, shift )
            
        else:
            
            if ctrl and key_code in ( ord( 'A' ), ord( 'a' ) ):
                
                self._SelectAll()
                
                self.widget().update()
                
            else:
                
                hit_logical_index = None
                
                if len( self._ordered_terms ) > 1:
                    
                    roll_up = False
                    roll_down = False
                    
                    if key_code in ( QC.Qt.Key_Home, ):
                        
                        hit_logical_index = 0
                        
                    elif key_code in ( QC.Qt.Key_End, ):
                        
                        hit_logical_index = len( self._ordered_terms ) - 1
                        
                        roll_up = True
                        
                    elif self._last_hit_logical_index is not None:
                        
                        if key_code in ( QC.Qt.Key_Up, ):
                            
                            hit_logical_index = ( self._last_hit_logical_index - 1 ) % len( self._ordered_terms )
                            
                        elif key_code in ( QC.Qt.Key_Down, ):
                            
                            hit_logical_index = ( self._last_hit_logical_index + 1 ) % len( self._ordered_terms )
                            
                        elif key_code in ( QC.Qt.Key_PageUp, QC.Qt.Key_PageDown ):
                            
                            last_hit_positional_index = self._GetPositionalIndexFromLogicalIndex( self._last_hit_logical_index )
                            
                            if key_code == QC.Qt.Key_PageUp:
                                
                                hit_positional_index = max( 0, last_hit_positional_index - self._num_rows_per_page )
                                
                            else:
                                
                                hit_positional_index = min( self._total_positional_rows - 1, last_hit_positional_index + self._num_rows_per_page )
                                
                            
                            ( hit_logical_index, hit_positional_index ) = self._GetLogicalIndicesFromPositionalIndex( hit_positional_index )
                            
                        
                    
                
                if hit_logical_index is None:
                    
                    # don't send to parent, which will do silly scroll window business with arrow key presses
                    event.ignore()
                    
                else:
                    
                    self._Hit( shift, ctrl, hit_logical_index )
                    
                
            
        
    
    def mouseDoubleClickEvent( self, event ):
        
        if event.button() == QC.Qt.LeftButton:
            
            ctrl_down = event.modifiers() & QC.Qt.ControlModifier
            shift_down = event.modifiers() & QC.Qt.ShiftModifier
            
            action_occurred = self._Activate( ctrl_down, shift_down )
            
            if action_occurred:
                
                self.mouseActivationOccurred.emit()
                
            
        else:
            
            QW.QScrollArea.mouseDoubleClickEvent( self, event )
            
        
    
    def mouseMoveEvent( self, event ):
        
        is_dragging = event.buttons() & QC.Qt.LeftButton
        
        if is_dragging:
            
            logical_index = self._GetLogicalIndexUnderMouse( event )
            
            if self._last_drag_start_logical_index is None:
                
                self._last_drag_start_logical_index = logical_index
                
            elif logical_index != self._last_drag_start_logical_index:
                
                ctrl = event.modifiers() & QC.Qt.ControlModifier
                
                if not self._drag_started:
                    
                    self._Hit( True, ctrl, self._last_drag_start_logical_index )
                    
                    self._drag_started = True
                    
                
                self._Hit( True, ctrl, logical_index )
                
            
        else:
            
            event.ignore()
            
        
    
    def mouseReleaseEvent( self, event ):
        
        self._last_drag_start_logical_index = None
        self._drag_started = False
        
        event.ignore()
        
    
    def EventMouseSelect( self, event ):
        
        self._HandleClick( event )
        
        return True # was: event.ignore()
        
    
    class _InnerWidget( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._parent = parent
            
        
        def paintEvent( self, event ):
            
            painter = QG.QPainter( self )
            
            self._parent._Redraw( painter )
            
        
    
    def resizeEvent( self, event ):
        
        text_height = self.fontMetrics().height()
        
        visible_rect = QP.ScrollAreaVisibleRect( self )
        
        self.verticalScrollBar().setSingleStep( text_height )
        
        visible_rect_height = visible_rect.height()
        
        self._num_rows_per_page = visible_rect_height // text_height
        
        self._SetVirtualSize()
        
        self.widget().update()
        
    
    def GetIdealHeight( self ):
        
        text_height = self.fontMetrics().height()
        
        return text_height * self._total_positional_rows + 20
        
    
    def HasValues( self ):
        
        return len( self._ordered_terms ) > 0
        
    
    def minimumSizeHint( self ):
        
        size_hint = QW.QScrollArea.minimumSizeHint( self )
        
        text_height = self.fontMetrics().height()
        
        minimum_height = self._minimum_height_num_chars * text_height + ( self.frameWidth() * 2 )
        
        size_hint.setHeight( minimum_height )
        
        return size_hint
        
    
    def MoveSelectionDown( self ):
        
        if len( self._ordered_terms ) > 1 and self._last_hit_logical_index is not None:
            
            logical_index = ( self._last_hit_logical_index + 1 ) % len( self._ordered_terms )
            
            self._Hit( False, False, logical_index )
            
        
    
    def MoveSelectionUp( self ):
        
        if len( self._ordered_terms ) > 1 and self._last_hit_logical_index is not None:
            
            logical_index = ( self._last_hit_logical_index - 1 ) % len( self._ordered_terms )
            
            self._Hit( False, False, logical_index )
            
        
    
    def SelectTopItem( self ):
        
        if len( self._ordered_terms ) > 0:
            
            if len( self._selected_terms ) == 1 and self._LogicalIndexIsSelected( 0 ):
                
                return
                
            
            self._DeselectAll()
            
            self._Hit( False, False, 0 )
            
            self.widget().update()
            
        
    
    def SetChildRowsAllowed( self, value: bool ):
        
        if self._terms_may_have_child_rows and self._child_rows_allowed != value:
            
            self._child_rows_allowed = value
            
            self._RegenTermsToIndices()
            
            self._SetVirtualSize()
            
            self.widget().update()
            
        
    
    def SetMinimumHeightNumChars( self, minimum_height_num_chars ):
        
        self._minimum_height_num_chars = minimum_height_num_chars
        
    
    def sizeHint( self ):
        
        size_hint = QW.QScrollArea.sizeHint( self )
        
        text_height = self.fontMetrics().height()
        
        ideal_height = self._height_num_chars * text_height + ( self.frameWidth() * 2 )
        
        size_hint.setHeight( ideal_height )
        
        return size_hint
        
    
COPY_ALL_TAGS = 0
COPY_ALL_TAGS_WITH_COUNTS = 1
COPY_SELECTED_TAGS = 2
COPY_SELECTED_TAGS_WITH_COUNTS = 3
COPY_SELECTED_SUBTAGS = 4
COPY_SELECTED_SUBTAGS_WITH_COUNTS = 5
COPY_ALL_SUBTAGS = 6
COPY_ALL_SUBTAGS_WITH_COUNTS = 7

class ListBoxTags( ListBox ):
    
    can_spawn_new_windows = True
    
    def __init__( self, parent, *args, tag_display_type: int = ClientTags.TAG_DISPLAY_STORAGE, **kwargs ):
        
        self._tag_display_type = tag_display_type
        
        child_rows_allowed = HG.client_controller.new_options.GetBoolean( 'expand_parents_on_storage_taglists' )
        terms_may_have_child_rows = self._tag_display_type == ClientTags.TAG_DISPLAY_STORAGE
        
        ListBox.__init__( self, parent, child_rows_allowed, terms_may_have_child_rows, *args, **kwargs )
        
        self._render_for_user = not self._tag_display_type == ClientTags.TAG_DISPLAY_STORAGE
        
        self._sibling_decoration_allowed = self._tag_display_type == ClientTags.TAG_DISPLAY_STORAGE
        
        self._page_key = None # placeholder. if a subclass sets this, it changes menu behaviour to allow 'select this tag' menu pubsubs
        
        self._UpdateBackgroundColour()
        
        self._widget_event_filter.EVT_MIDDLE_DOWN( self.EventMouseMiddleClick )
        
        HG.client_controller.sub( self, 'ForceTagRecalc', 'refresh_all_tag_presentation_gui' )
        HG.client_controller.sub( self, '_UpdateBackgroundColour', 'notify_new_colourset' )
        
    
    def _GetCopyableTagStrings( self, command ):
        
        only_selected = command in ( COPY_SELECTED_TAGS, COPY_SELECTED_TAGS_WITH_COUNTS, COPY_SELECTED_SUBTAGS, COPY_SELECTED_SUBTAGS_WITH_COUNTS )
        with_counts = command in ( COPY_ALL_TAGS_WITH_COUNTS, COPY_ALL_SUBTAGS_WITH_COUNTS, COPY_SELECTED_TAGS_WITH_COUNTS, COPY_SELECTED_SUBTAGS_WITH_COUNTS )
        only_subtags = command in ( COPY_ALL_SUBTAGS, COPY_ALL_SUBTAGS_WITH_COUNTS, COPY_SELECTED_SUBTAGS, COPY_SELECTED_SUBTAGS_WITH_COUNTS )
        
        if only_selected:
            
            if len( self._selected_terms ) > 1:
                
                # keep order
                terms = [ term for term in self._ordered_terms if term in self._selected_terms ]
                
            else:
                
                # nice and fast
                terms = self._selected_terms
                
            
        else:
            
            terms = self._ordered_terms
            
        
        copyable_tag_strings = [ term.GetCopyableText( with_counts = with_counts ) for term in terms ]
        
        if only_subtags:
            
            copyable_tag_strings = [ HydrusTags.SplitTag( tag_string )[1] for tag_string in copyable_tag_strings ]
            
            if not with_counts:
                
                copyable_tag_strings = HydrusData.DedupeList( copyable_tag_strings )
                
            
        
        return copyable_tag_strings
        
    
    def _GetCurrentFileServiceKey( self ):
        
        return CC.LOCAL_FILE_SERVICE_KEY
        
    
    def _GetCurrentPagePredicates( self ) -> typing.Set[ ClientSearch.Predicate ]:
        
        return set()
        
    
    def _GetNamespaceColours( self ):
        
        return HC.options[ 'namespace_colours' ]
        
    
    def _CanProvideCurrentPagePredicates( self ):
        
        return False
        
    
    def _GetRowsOfTextsAndColours( self, term: ClientGUIListBoxesData.ListBoxItem ):
        
        namespace_colours = self._GetNamespaceColours()
        
        rows_of_texts_and_namespaces = term.GetRowsOfPresentationTextsWithNamespaces( self._render_for_user, self._sibling_decoration_allowed, self._child_rows_allowed )
        
        rows_of_texts_and_colours = []
        
        for texts_and_namespaces in rows_of_texts_and_namespaces:
            
            texts_and_colours = []
            
            for ( text, namespace ) in texts_and_namespaces:
                
                if namespace in namespace_colours:
                    
                    rgb = namespace_colours[ namespace ]
                    
                else:
                    
                    rgb = namespace_colours[ None ]
                    
                
                texts_and_colours.append( ( text, rgb ) )
                
            
            rows_of_texts_and_colours.append( texts_and_colours )
            
        
        return rows_of_texts_and_colours
        
    
    def _HasCounts( self ):
        
        return False
        
    
    def _NewSearchPages( self, pages_of_predicates ):
        
        activate_window = HG.client_controller.new_options.GetBoolean( 'activate_window_on_tag_search_page_activation' )
        
        for predicates in pages_of_predicates:
            
            predicates = ClientGUISearch.FleshOutPredicates( self, predicates )
            
            if len( predicates ) == 0:
                
                break
                
            
            s = sorted( ( predicate.ToString() for predicate in predicates ) )
            
            page_name = ', '.join( s )
            
            file_service_key = self._GetCurrentFileServiceKey()
            
            HG.client_controller.pub( 'new_page_query', file_service_key, initial_predicates = predicates, page_name = page_name, activate_window = activate_window )
            
            activate_window = False
            
        
    
    def _ProcessMenuCopyEvent( self, command ):
        
        texts = self._GetCopyableTagStrings( command )
        
        if len( texts ) > 0:
            
            text = os.linesep.join( texts )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _ProcessMenuPredicateEvent( self, command ):
        
        pass
        
    
    def _ProcessMenuTagEvent( self, command ):
        
        tags = self._GetTagsFromTerms( self._selected_terms )
        
        tags = [ tag for tag in tags if tag is not None ]
        
        if command in ( 'hide', 'hide_namespace' ):
            
            if len( tags ) == 1:
                
                ( tag, ) = tags
                
                if command == 'hide':
                    
                    message = 'Hide "{}" from here?'.format( tag )
                    
                    from hydrus.client.gui import ClientGUIDialogsQuick
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.Accepted:
                        
                        return
                        
                    
                    HG.client_controller.tag_display_manager.HideTag( self._tag_display_type, CC.COMBINED_TAG_SERVICE_KEY, tag )
                    
                elif command == 'hide_namespace':
                    
                    ( namespace, subtag ) = HydrusTags.SplitTag( tag )
                    
                    if namespace == '':
                        
                        insert = 'unnamespaced'
                        
                    else:
                        
                        insert = '"{}"'.format( namespace )
                        
                    
                    message = 'Hide {} tags from here?'.format( insert )
                    
                    from hydrus.client.gui import ClientGUIDialogsQuick
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.Accepted:
                        
                        return
                        
                    
                    if namespace != '':
                        
                        namespace += ':'
                        
                    
                    HG.client_controller.tag_display_manager.HideTag( self._tag_display_type, CC.COMBINED_TAG_SERVICE_KEY, namespace )
                    
                
                HG.client_controller.pub( 'notify_new_tag_display_rules' )
                
            
        else:
            
            from hydrus.client.gui import ClientGUITags
            
            if command == 'parent':
                
                title = 'manage tag parents'
                
            elif command == 'sibling':
                
                title = 'manage tag siblings'
                
            
            from hydrus.client.gui import ClientGUITopLevelWindowsPanels
            
            with ClientGUITopLevelWindowsPanels.DialogManage( self, title ) as dlg:
                
                if command == 'parent':
                    
                    panel = ClientGUITags.ManageTagParents( dlg, tags )
                    
                elif command == 'sibling':
                    
                    panel = ClientGUITags.ManageTagSiblings( dlg, tags )
                    
                
                dlg.SetPanel( panel )
                
                dlg.exec()
                
            
        
    
    def _SelectFilesWithTags( self, select_type ):
        
        pass
        
    
    def _UpdateBackgroundColour( self ):
        
        new_options = HG.client_controller.new_options
        
        self._background_colour = new_options.GetColour( CC.COLOUR_TAGS_BOX )
        
        self.widget().update()
        
    
    def AddAdditionalMenuItems( self, menu: QW.QMenu ):
        
        pass
        
    
    def EventMouseMiddleClick( self, event ):
        
        self._HandleClick( event )
        
        if self.can_spawn_new_windows:
            
            ( predicates, or_predicate, inverse_predicates, namespace_predicate, inverse_namespace_predicate ) = self._GetSelectedPredicatesAndInverseCopies()
            
            if len( predicates ) > 0:
                
                shift_down = event.modifiers() & QC.Qt.ShiftModifier
                
                if shift_down and or_predicate is not None:
                    
                    predicates = ( or_predicate, )
                    
                
                self._NewSearchPages( [ predicates ] )
                
            
        
    
    def contextMenuEvent( self, event ):
        
        if event.reason() == QG.QContextMenuEvent.Keyboard:
            
            self.ShowMenu()
            
        
    
    def mouseReleaseEvent( self, event ):
        
        if event.button() != QC.Qt.RightButton:
            
            ListBox.mouseReleaseEvent( self, event )
            
            return
            
        
        self.ShowMenu()
        
    
    def ShowMenu( self ):
        
        sub_selection_string = None
        
        if len( self._ordered_terms ) > 0:
            
            selected_actual_tags = self._GetTagsFromTerms( self._selected_terms )
            
            menu = QW.QMenu()
            
            if self._terms_may_have_child_rows:
                
                add_it = True
                
                if self._child_rows_allowed:
                    
                    if len( self._ordered_terms ) == self._total_positional_rows:
                        
                        # no parents to hide!
                        
                        add_it = False
                        
                    
                    message = 'hide parent rows'
                    
                else:
                    
                    message = 'show parent rows'
                    
                
                if add_it:
                    
                    ClientGUIMenus.AppendMenuItem( menu, message, 'Show/hide parents.', self.SetChildRowsAllowed, not self._child_rows_allowed )
                    
                    ClientGUIMenus.AppendSeparator( menu )
                    
                
            
            copy_menu = QW.QMenu( menu )
            
            selected_copyable_tag_strings = self._GetCopyableTagStrings( COPY_SELECTED_TAGS )
            selected_copyable_subtag_strings = self._GetCopyableTagStrings( COPY_SELECTED_SUBTAGS )
            
            if len( selected_copyable_tag_strings ) == 1:
                
                ( selection_string, ) = selected_copyable_tag_strings 
                
            else:
                
                selection_string = '{} selected'.format( HydrusData.ToHumanInt( len( selected_copyable_tag_strings ) ) )
                
            
            if len( selected_copyable_tag_strings ) > 0:
                
                ClientGUIMenus.AppendMenuItem( copy_menu, selection_string, 'Copy the selected tags to your clipboard.', self._ProcessMenuCopyEvent, COPY_SELECTED_TAGS )
                
                if len( selected_copyable_subtag_strings ) == 1:
                    
                    # this does a quick test for 'are we selecting a namespaced tags' that also allows for having both 'samus aran' and 'character:samus aran'
                    if set( selected_copyable_subtag_strings ) != set( selected_copyable_tag_strings ):
                        
                        ( sub_selection_string, ) = selected_copyable_subtag_strings
                        
                        ClientGUIMenus.AppendMenuItem( copy_menu, sub_selection_string, 'Copy the selected subtag to your clipboard.', self._ProcessMenuCopyEvent, COPY_SELECTED_SUBTAGS )
                        
                    
                else:
                    
                    sub_selection_string = '{} selected subtags'.format( HydrusData.ToHumanInt( len( selected_copyable_subtag_strings ) ) )
                    
                    ClientGUIMenus.AppendMenuItem( copy_menu, sub_selection_string, 'Copy the selected subtags to your clipboard.', self._ProcessMenuCopyEvent, COPY_SELECTED_SUBTAGS )
                    
                
                if self._HasCounts():
                    
                    ClientGUIMenus.AppendSeparator( copy_menu )
                    
                    ClientGUIMenus.AppendMenuItem( copy_menu, '{} with counts'.format( selection_string ), 'Copy the selected tags, with their counts, to your clipboard.', self._ProcessMenuCopyEvent, COPY_SELECTED_TAGS_WITH_COUNTS )
                    
                    if sub_selection_string is not None:
                        
                        ClientGUIMenus.AppendMenuItem( copy_menu, '{} with counts'.format( sub_selection_string ), 'Copy the selected subtags, with their counts, to your clipboard.', self._ProcessMenuCopyEvent, COPY_SELECTED_SUBTAGS_WITH_COUNTS )
                        
                    
                
            
            copy_all_is_appropriate = len( self._ordered_terms ) > len( self._selected_terms )
            
            if copy_all_is_appropriate:
                
                ClientGUIMenus.AppendSeparator( copy_menu )
                
                ClientGUIMenus.AppendMenuItem( copy_menu, 'all tags', 'Copy all the tags in this list to your clipboard.', self._ProcessMenuCopyEvent, COPY_ALL_TAGS )
                ClientGUIMenus.AppendMenuItem( copy_menu, 'all subtags', 'Copy all the subtags in this list to your clipboard.', self._ProcessMenuCopyEvent, COPY_ALL_SUBTAGS )
                
                if self._HasCounts():
                    
                    ClientGUIMenus.AppendMenuItem( copy_menu, 'all tags with counts', 'Copy all the tags in this list, with their counts, to your clipboard.', self._ProcessMenuCopyEvent, COPY_ALL_TAGS_WITH_COUNTS )
                    ClientGUIMenus.AppendMenuItem( copy_menu, 'all subtags with counts', 'Copy all the subtags in this list, with their counts, to your clipboard.', self._ProcessMenuCopyEvent, COPY_ALL_SUBTAGS_WITH_COUNTS )
                    
                
            
            ClientGUIMenus.AppendMenu( menu, copy_menu, 'copy' )
            
            #
            
            can_launch_sibling_and_parent_dialogs = len( selected_actual_tags ) > 0 and self.can_spawn_new_windows
            can_show_siblings_and_parents = len( selected_actual_tags ) == 1
            
            if can_show_siblings_and_parents or can_launch_sibling_and_parent_dialogs:
                
                siblings_menu = QW.QMenu( menu )
                parents_menu = QW.QMenu( menu )
                
                ClientGUIMenus.AppendMenu( menu, siblings_menu, 'siblings' )
                ClientGUIMenus.AppendMenu( menu, parents_menu, 'parents' )
                
                if can_launch_sibling_and_parent_dialogs:
                    
                    if len( selected_actual_tags ) == 1:
                        
                        ( tag, ) = selected_actual_tags
                        
                        text = tag
                        
                    else:
                        
                        text = 'selection'
                        
                    
                    ClientGUIMenus.AppendMenuItem( siblings_menu, 'add siblings to ' + text, 'Add a sibling to this tag.', self._ProcessMenuTagEvent, 'sibling' )
                    ClientGUIMenus.AppendMenuItem( parents_menu, 'add parents to ' + text, 'Add a parent to this tag.', self._ProcessMenuTagEvent, 'parent' )
                    
                
                if can_show_siblings_and_parents:
                    
                    ( selected_tag, ) = selected_actual_tags
                    
                    def sp_work_callable():
                        
                        selected_tag_to_service_keys_to_siblings_and_parents = HG.client_controller.Read( 'tag_siblings_and_parents_lookup', ( selected_tag, ) )
                        
                        service_keys_to_siblings_and_parents = selected_tag_to_service_keys_to_siblings_and_parents[ selected_tag ]
                        
                        return service_keys_to_siblings_and_parents
                        
                    
                    def sp_publish_callable( service_keys_to_siblings_and_parents ):
                        
                        service_keys_in_order = HG.client_controller.services_manager.GetServiceKeys( HC.REAL_TAG_SERVICES )
                        
                        all_siblings = set()
                        
                        siblings_to_service_keys = collections.defaultdict( set )
                        parents_to_service_keys = collections.defaultdict( set )
                        children_to_service_keys = collections.defaultdict( set )
                        
                        ideals_to_service_keys = collections.defaultdict( set )
                        
                        for ( service_key, ( sibling_chain_members, ideal_tag, descendants, ancestors ) ) in service_keys_to_siblings_and_parents.items():
                            
                            all_siblings.update( sibling_chain_members )
                            
                            for sibling in sibling_chain_members:
                                
                                if sibling == ideal_tag:
                                    
                                    ideals_to_service_keys[ ideal_tag ].add( service_key )
                                    
                                    continue
                                    
                                
                                if sibling == selected_tag: # don't care about the selected tag unless it is ideal
                                    
                                    continue
                                    
                                
                                siblings_to_service_keys[ sibling ].add( service_key )
                                
                            
                            for ancestor in ancestors:
                                
                                parents_to_service_keys[ ancestor ].add( service_key )
                                
                            
                            for descendant in descendants:
                                
                                children_to_service_keys[ descendant ].add( service_key )
                                
                            
                        
                        all_siblings.discard( selected_tag )
                        
                        num_siblings = len( all_siblings )
                        num_parents = len( parents_to_service_keys )
                        num_children = len( children_to_service_keys )
                        
                        service_keys_to_service_names = { service_key : HG.client_controller.services_manager.GetName( service_key ) for service_key in service_keys_in_order }
                        
                        ALL_SERVICES_LABEL = 'all services'
                        
                        def convert_service_keys_to_name_string( s_ks ):
                            
                            if len( s_ks ) == len( service_keys_in_order ):
                                
                                return ALL_SERVICES_LABEL
                                
                            
                            return ', '.join( ( service_keys_to_service_names[ service_key ] for service_key in service_keys_in_order if service_key in s_ks ) )
                            
                        
                        def group_and_sort_siblings_to_service_keys( t_to_s_ks ):
                            
                            # convert "tag -> everywhere I am" to "sorted groups of locations -> what we have in common, also sorted"
                            
                            service_key_groups_to_tags = collections.defaultdict( list )
                            
                            for ( t, s_ks ) in t_to_s_ks.items():
                                
                                service_key_groups_to_tags[ tuple( s_ks ) ].append( t )
                                
                            
                            tag_sort = ClientTagSorting.TagSort.STATICGetTextASCDefault()
                            
                            for t_list in service_key_groups_to_tags.values():
                                
                                ClientTagSorting.SortTags( tag_sort, t_list )
                                
                            
                            service_key_groups = sorted( service_key_groups_to_tags.keys(), key = lambda s_k_g: ( -len( s_k_g ), convert_service_keys_to_name_string( s_k_g ) ) )
                            
                            service_key_group_names_and_tags = [ ( convert_service_keys_to_name_string( s_k_g ), service_key_groups_to_tags[ s_k_g ] ) for s_k_g in service_key_groups ]
                            
                            return service_key_group_names_and_tags
                            
                        
                        def group_and_sort_parents_to_service_keys( p_to_s_ks, c_to_s_ks ):
                            
                            # convert two lots of "tag -> everywhere I am" to "sorted groups of locations -> what we have in common, also sorted"
                            
                            service_key_groups_to_tags = collections.defaultdict( lambda: ( [], [] ) )
                            
                            for ( p, s_ks ) in p_to_s_ks.items():
                                
                                service_key_groups_to_tags[ tuple( s_ks ) ][0].append( p )
                                
                            
                            for ( c, s_ks ) in c_to_s_ks.items():
                                
                                service_key_groups_to_tags[ tuple( s_ks ) ][1].append( c )
                                
                            
                            tag_sort = ClientTagSorting.TagSort.STATICGetTextASCDefault()
                            
                            for ( t_list_1, t_list_2 ) in service_key_groups_to_tags.values():
                                
                                ClientTagSorting.SortTags( tag_sort, t_list_1 )
                                ClientTagSorting.SortTags( tag_sort, t_list_2 )
                                
                            
                            service_key_groups = sorted( service_key_groups_to_tags.keys(), key = lambda s_k_g: ( -len( s_k_g ), convert_service_keys_to_name_string( s_k_g ) ) )
                            
                            service_key_group_names_and_tags = [ ( convert_service_keys_to_name_string( s_k_g ), service_key_groups_to_tags[ s_k_g ] ) for s_k_g in service_key_groups ]
                            
                            return service_key_group_names_and_tags
                            
                        
                        if num_siblings == 0:
                            
                            siblings_menu.setTitle( 'no siblings' )
                            
                        else:
                            
                            siblings_menu.setTitle( '{} siblings'.format( HydrusData.ToHumanInt( num_siblings ) ) )
                            
                            #
                            
                            ClientGUIMenus.AppendSeparator( siblings_menu )
                            
                            ideals = sorted( ideals_to_service_keys.keys(), key = HydrusTags.ConvertTagToSortable )
                            
                            for ideal in ideals:
                                
                                if ideal == selected_tag:
                                    
                                    continue
                                    
                                
                                ideal_label = 'ideal is "{}" on: {}'.format( ideal, convert_service_keys_to_name_string( ideals_to_service_keys[ ideal ] ) )
                                
                                ClientGUIMenus.AppendMenuItem( siblings_menu, ideal_label, ideal_label, HG.client_controller.pub, 'clipboard', 'text', ideal )
                                
                            
                            #
                            
                            for ( s_k_name, tags ) in group_and_sort_siblings_to_service_keys( siblings_to_service_keys ):
                                
                                ClientGUIMenus.AppendSeparator( siblings_menu )
                                
                                if s_k_name != ALL_SERVICES_LABEL:
                                    
                                    ClientGUIMenus.AppendMenuLabel( siblings_menu, '--{}--'.format( s_k_name ) )
                                    
                                
                                for tag in tags:
                                    
                                    ClientGUIMenus.AppendMenuLabel( siblings_menu, tag )
                                    
                                
                            
                        
                        #
                        
                        if num_parents + num_children == 0:
                            
                            parents_menu.setTitle( 'no parents' )
                            
                        else:
                            
                            parents_menu.setTitle( '{} parents, {} children'.format( HydrusData.ToHumanInt( num_parents ), HydrusData.ToHumanInt( num_children ) ) )
                            
                            ClientGUIMenus.AppendSeparator( parents_menu )
                            
                            for ( s_k_name, ( parents, children ) ) in group_and_sort_parents_to_service_keys( parents_to_service_keys, children_to_service_keys ):
                                
                                ClientGUIMenus.AppendSeparator( parents_menu )
                                
                                if s_k_name != ALL_SERVICES_LABEL:
                                    
                                    ClientGUIMenus.AppendMenuLabel( parents_menu, '--{}--'.format( s_k_name ) )
                                    
                                
                                for parent in parents:
                                    
                                    parent_label = 'parent: {}'.format( parent )
                                    
                                    ClientGUIMenus.AppendMenuItem( parents_menu, parent_label, parent_label, HG.client_controller.pub, 'clipboard', 'text', parent )
                                    
                                
                                for child in children:
                                    
                                    child_label = 'child: {}'.format( child )
                                    
                                    ClientGUIMenus.AppendMenuItem( parents_menu, child_label, child_label, HG.client_controller.pub, 'clipboard', 'text', child )
                                    
                                
                            
                        
                    
                    async_job = ClientGUIAsync.AsyncQtJob( menu, sp_work_callable, sp_publish_callable )
                    
                    async_job.start()
                    
                
            
            if len( self._selected_terms ) > 0:
                
                ClientGUIMenus.AppendSeparator( menu )
                
                ( predicates, or_predicate, inverse_predicates, namespace_predicate, inverse_namespace_predicate ) = self._GetSelectedPredicatesAndInverseCopies()
                
                if len( predicates ) > 0:
                    
                    if self.can_spawn_new_windows or self._CanProvideCurrentPagePredicates():
                        
                        search_menu = QW.QMenu( menu )
                        
                        ClientGUIMenus.AppendMenu( menu, search_menu, 'search' )
                        
                    
                    if self.can_spawn_new_windows:
                        
                        ClientGUIMenus.AppendMenuItem( search_menu, 'open a new search page for ' + selection_string, 'Open a new search page starting with the selected predicates.', self._NewSearchPages, [ predicates ] )
                        
                        if or_predicate is not None:
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, 'open a new OR search page for ' + selection_string, 'Open a new search page starting with the selected merged as an OR search predicate.', self._NewSearchPages, [ ( or_predicate, ) ] )
                            
                        
                        if len( predicates ) > 1:
                            
                            for_each_predicates = [ ( predicate, ) for predicate in predicates ]
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, 'open new search pages for each in selection', 'Open one new search page for each selected predicate.', self._NewSearchPages, for_each_predicates )
                            
                        
                        ClientGUIMenus.AppendSeparator( search_menu )
                        
                    
                    if self._CanProvideCurrentPagePredicates():
                        
                        current_predicates = self._GetCurrentPagePredicates()
                        
                        predicates = set( predicates )
                        inverse_predicates = set( inverse_predicates )
                        
                        if len( predicates ) == 1:
                            
                            ( pred, ) = predicates
                            
                            predicates_selection_string = pred.ToString( with_count = False )
                            
                        else:
                            
                            predicates_selection_string = 'selected'
                            
                        
                        some_selected_in_current = HydrusData.SetsIntersect( predicates, current_predicates )
                        
                        if some_selected_in_current:
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, 'remove {} from current search'.format( predicates_selection_string ), 'Remove the selected predicates from the current search.', self._ProcessMenuPredicateEvent, 'remove_predicates' )
                            
                        
                        some_selected_not_in_current = len( predicates.intersection( current_predicates ) ) < len( predicates )
                        
                        if some_selected_not_in_current:
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, 'add {} to current search'.format( predicates_selection_string ), 'Add the selected predicates to the current search.', self._ProcessMenuPredicateEvent, 'add_predicates' )
                            
                        
                        if or_predicate is not None:
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, 'add an OR of {} to current search'.format( predicates_selection_string ), 'Add the selected predicates as an OR predicate to the current search.', self._ProcessMenuPredicateEvent, 'add_or_predicate' )
                            
                        
                        some_selected_are_excluded_explicitly = HydrusData.SetsIntersect( inverse_predicates, current_predicates )
                        
                        if some_selected_are_excluded_explicitly:
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, 'permit {} for current search'.format( predicates_selection_string ), 'Stop disallowing the selected predicates from the current search.', self._ProcessMenuPredicateEvent, 'remove_inverse_predicates' )
                            
                        
                        some_selected_are_not_excluded_explicitly = len( inverse_predicates.intersection( current_predicates ) ) < len( inverse_predicates )
                        
                        if some_selected_are_not_excluded_explicitly:
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, 'exclude {} from the current search'.format( predicates_selection_string ), 'Disallow the selected predicates for the current search.', self._ProcessMenuPredicateEvent, 'add_inverse_predicates' )
                            
                        
                        if namespace_predicate is not None and namespace_predicate not in current_predicates:
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, 'add {} to current search'.format( namespace_predicate.ToString( with_count = False ) ), 'Add the namespace predicate to the current search.', self._ProcessMenuPredicateEvent, 'add_namespace_predicate' )
                            
                        
                        if inverse_namespace_predicate is not None and inverse_namespace_predicate not in current_predicates:
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, 'exclude {} from the current search'.format( namespace_predicate.ToString( with_count = False ) ), 'Disallow the namespace predicate from the current search.', self._ProcessMenuPredicateEvent, 'add_inverse_namespace_predicate' )
                            
                        
                    
                    self._AddEditMenu( menu )
                    
                
                if len( selected_actual_tags ) > 0 and self._page_key is not None:
                    
                    select_menu = QW.QMenu( menu )
                    
                    tags_sorted_to_show_on_menu = HydrusTags.SortNumericTags( selected_actual_tags )
                    
                    tags_sorted_to_show_on_menu_string = ', '.join( tags_sorted_to_show_on_menu )
                    
                    while len( tags_sorted_to_show_on_menu_string ) > 64:
                        
                        if len( tags_sorted_to_show_on_menu ) == 1:
                            
                            tags_sorted_to_show_on_menu_string = '(many/long tags)'
                            
                        else:
                            
                            tags_sorted_to_show_on_menu.pop( -1 )
                            
                            tags_sorted_to_show_on_menu_string = ', '.join( tags_sorted_to_show_on_menu + [ '\u2026' ] )
                            
                        
                    
                    if len( selected_actual_tags ) == 1:
                        
                        label = 'files with "{}"'.format( tags_sorted_to_show_on_menu_string )
                        
                    else:
                        
                        label = 'files with all of "{}"'.format( tags_sorted_to_show_on_menu_string )
                        
                    
                    ClientGUIMenus.AppendMenuItem( select_menu, label, 'Select the files with these tags.', self._SelectFilesWithTags, 'AND' )
                    
                    if len( selected_actual_tags ) > 1:
                        
                        label = 'files with any of "{}"'.format( tags_sorted_to_show_on_menu_string )
                        
                        ClientGUIMenus.AppendMenuItem( select_menu, label, 'Select the files with any of these tags.', self._SelectFilesWithTags, 'OR' )
                        
                    
                    ClientGUIMenus.AppendMenu( menu, select_menu, 'select' )
                    
                
            
            if len( selected_actual_tags ) == 1:
                
                ( selected_tag, ) = selected_actual_tags
                
                if self._tag_display_type in ( ClientTags.TAG_DISPLAY_SINGLE_MEDIA, ClientTags.TAG_DISPLAY_SELECTION_LIST ):
                    
                    ClientGUIMenus.AppendSeparator( menu )
                    
                    ( namespace, subtag ) = HydrusTags.SplitTag( selected_tag )
                    
                    hide_menu = QW.QMenu( menu )
                    
                    ClientGUIMenus.AppendMenuItem( hide_menu, '"{}" tags from here'.format( ClientTags.RenderNamespaceForUser( namespace ) ), 'Hide this namespace from view in future.', self._ProcessMenuTagEvent, 'hide_namespace' )
                    ClientGUIMenus.AppendMenuItem( hide_menu, '"{}" from here'.format( selected_tag ), 'Hide this tag from view in future.', self._ProcessMenuTagEvent, 'hide' )
                    
                    ClientGUIMenus.AppendMenu( menu, hide_menu, 'hide' )
                    
                
                def set_favourite_tags( tag ):
                    
                    favourite_tags = list( HG.client_controller.new_options.GetStringList( 'favourite_tags' ) )
                    
                    if selected_tag in favourite_tags:
                        
                        favourite_tags.remove( tag )
                        
                    else:
                        
                        favourite_tags.append( tag )
                        
                    
                    HG.client_controller.new_options.SetStringList( 'favourite_tags', favourite_tags )
                    
                    HG.client_controller.pub( 'notify_new_favourite_tags' )
                    
                
                favourite_tags = list( HG.client_controller.new_options.GetStringList( 'favourite_tags' ) )
                
                if selected_tag in favourite_tags:
                    
                    label = 'remove "{}" from favourites'.format( selected_tag )
                    description = 'Remove this tag from your favourites'
                    
                else:
                    
                    label = 'add "{}" to favourites'.format( selected_tag )
                    description = 'Add this tag from your favourites'
                    
                
                favourites_menu = QW.QMenu( menu )
                
                ClientGUIMenus.AppendMenuItem( favourites_menu, label, description, set_favourite_tags, selected_tag )
                
                m = ClientGUIMenus.AppendMenu( menu, favourites_menu, 'favourites' )
                
            
            self.AddAdditionalMenuItems( menu )
            
            CGC.core().PopupMenu( self, menu )
            
        
    
    def ForceTagRecalc( self ):
        
        pass
        
    
class ListBoxTagsPredicates( ListBoxTags ):
    
    def __init__( self, *args, tag_display_type = ClientTags.TAG_DISPLAY_ACTUAL, **kwargs ):
        
        ListBoxTags.__init__( self, *args, tag_display_type = tag_display_type, **kwargs )
        
    
    def _GenerateTermFromPredicate( self, predicate: ClientSearch.Predicate ) -> ClientGUIListBoxesData.ListBoxItemPredicate:
        
        return ClientGUIListBoxesData.ListBoxItemPredicate( predicate )
        
    
    def _GetMutuallyExclusivePredicates( self, predicate ):
        
        all_predicates = self._GetPredicatesFromTerms( self._ordered_terms )
        
        m_e_predicates = { existing_predicate for existing_predicate in all_predicates if existing_predicate.IsMutuallyExclusive( predicate ) }
        
        return m_e_predicates
        
    
    def _HasCounts( self ):
        
        return True
        
    
    def GetPredicates( self ) -> typing.Set[ ClientSearch.Predicate ]:
        
        return set( self._GetPredicatesFromTerms( self._ordered_terms ) )
        
    
    def SetPredicates( self, predicates ):
        
        selected_terms = set( self._selected_terms )
        
        self._Clear()
        
        terms = [ self._GenerateTermFromPredicate( predicate ) for predicate in predicates ]
        
        self._AppendTerms( terms )
        
        for term in selected_terms:
            
            if term in self._terms_to_logical_indices:
                
                self._selected_terms.add( term )
                
            
        
        self._HitFirstSelectedItem()
        
        self._DataHasChanged()
        
    
class ListBoxTagsColourOptions( ListBoxTags ):
    
    PROTECTED_TERMS = ( None, '' )
    can_spawn_new_windows = False
    
    def __init__( self, parent, initial_namespace_colours ):
        
        ListBoxTags.__init__( self, parent )
        
        terms = []
        
        for ( namespace, colour ) in initial_namespace_colours.items():
            
            colour = tuple( colour ) # tuple to convert from list, for oooold users who have list colours
            
            term = self._GenerateTermFromNamespaceAndColour( namespace, colour )
            
            terms.append( term )
            
        
        self._AppendTerms( terms )
        
        self._Sort()
        
        self._DataHasChanged()
        
    
    def _Activate( self, ctrl_down, shift_down ):
        
        deletable_terms = [ term for term in self._selected_terms if term.GetNamespace() not in self.PROTECTED_TERMS ]
        
        if len( deletable_terms ) > 0:
            
            from hydrus.client.gui import ClientGUIDialogsQuick
            
            result = ClientGUIDialogsQuick.GetYesNo( self, 'Delete all selected colours?' )
            
            if result == QW.QDialog.Accepted:
                
                self._RemoveTerms( deletable_terms )
                
                self._DataHasChanged()
                
                return True
                
            
        
        return False
        
    
    def _DeleteActivate( self ):
        
        ctrl_down = False
        shift_down = False
        
        self._Activate( ctrl_down, shift_down )
        
    
    def _GenerateTermFromNamespaceAndColour( self, namespace, colour ) -> ClientGUIListBoxesData.ListBoxItemNamespaceColour:
        
        return ClientGUIListBoxesData.ListBoxItemNamespaceColour( namespace, colour )
        
    
    def _GetNamespaceColours( self ):
        
        return dict( ( term.GetNamespaceAndColour() for term in self._ordered_terms ) )
        
    
    def SetNamespaceColour( self, namespace, colour: QG.QColor ):
        
        colour_tuple = ( colour.red(), colour.green(), colour.blue() )
        
        for term in self._ordered_terms:
            
            if term.GetNamespace() == namespace:
                
                self._RemoveTerms( ( term, ) )
                
                break
                
            
        
        term = self._GenerateTermFromNamespaceAndColour( namespace, colour_tuple )
        
        self._AppendTerms( ( term, ) )
        
        self._Sort()
        
        self._DataHasChanged()
        
    
    def GetNamespaceColours( self ):
        
        return self._GetNamespaceColours()
        
    
    def GetSelectedNamespaceColours( self ):
        
        namespace_colours = dict( ( term.GetNamespaceAndColour() for term in self._selected_terms ) )
        
        return namespace_colours
        
    
class ListBoxTagsFilter( ListBoxTags ):
    
    tagsRemoved = QC.Signal( list )
    
    def __init__( self, parent ):
        
        ListBoxTags.__init__( self, parent )
        
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        if len( self._selected_terms ) > 0:
            
            tag_slices = [ term.GetTagSlice() for term in self._selected_terms ]
            
            self._RemoveSelectedTerms()
            
            self.tagsRemoved.emit( tag_slices )
            
            self._DataHasChanged()
            
            return True
            
        
        return False
        
    
    def _GenerateTermFromTagSlice( self, tag_slice ) -> ClientGUIListBoxesData.ListBoxItemTagSlice:
        
        return ClientGUIListBoxesData.ListBoxItemTagSlice( tag_slice )
        
    
    def AddTagSlices( self, tag_slices ):
        
        terms = [ self._GenerateTermFromTagSlice( tag_slice ) for tag_slice in tag_slices ]
        
        self._AppendTerms( terms )
        
        self._Sort()
        
        self._DataHasChanged()
        
    
    def EnterTagSlices( self, tag_slices ):
        
        for tag_slice in tag_slices:
            
            term = self._GenerateTermFromTagSlice( tag_slice )
            
            if term in self._terms_to_logical_indices:
                
                self._RemoveTerms( ( term, ) )
                
            else:
                
                self._AppendTerms( ( term, ) )
                
            
        
        self._Sort()
        
        self._DataHasChanged()
        
    
    def GetSelectedTagSlices( self ):
        
        return [ term.GetTagSlice() for term in self._selected_terms ]
        
    
    def GetTagSlices( self ):
        
        return [ term.GetTagSlice() for term in self._ordered_terms ]
        
    
    def RemoveTagSlices( self, tag_slices ):
        
        removee_terms = [ self._GenerateTermFromTagSlice( tag_slice ) for tag_slice in tag_slices ]
        
        self._RemoveTerms( removee_terms )
        
        self._Sort()
        
        self._DataHasChanged()
        
    
    def SetTagSlices( self, tag_slices ):
        
        self._Clear()
        
        self.AddTagSlices( tag_slices )
        
    
class ListBoxTagsDisplayCapable( ListBoxTags ):
    
    def __init__( self, parent, service_key = None, tag_display_type = ClientTags.TAG_DISPLAY_ACTUAL, **kwargs ):
        
        if service_key is None:
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        self._service_key = service_key
        
        has_async_text_info = tag_display_type == ClientTags.TAG_DISPLAY_STORAGE
        
        ListBoxTags.__init__( self, parent, has_async_text_info = has_async_text_info, tag_display_type = tag_display_type, **kwargs )
        
    
    def _ApplyAsyncInfoToTerm( self, term, info ) -> typing.Tuple[ bool, bool ]:
        
        # this guy comes with the lock
        
        if info is None:
            
            return ( False, False )
            
        
        sort_info_changed = False
        num_rows_changed = False
        
        ( ideal, parents ) = info
        
        if ideal is not None and ideal != term.GetTag():
            
            term.SetIdealTag( ideal )
            
            sort_info_changed = True
            
        
        if parents is not None:
            
            term.SetParents( parents )
            
            num_rows_changed = True
            
        
        return ( sort_info_changed, num_rows_changed )
        
    
    def _InitialiseAsyncTextInfoUpdaterWorkCallable( self ):
        
        if not self._has_async_text_info:
            
            return ListBoxTags._InitialiseAsyncTextInfoUpdaterWorkCallable( self )
            
        
        self._async_text_info_shared_data[ 'service_key' ] = self._service_key
        
        async_text_info_shared_data = self._async_text_info_shared_data
        async_lock = self._async_text_info_lock
        currently_fetching = self._currently_fetching_async_text_info_terms
        pending = self._pending_async_text_info_terms
        
        def work_callable():
            
            with async_lock:
                
                to_lookup = list( pending )
                
                pending.clear()
                
                currently_fetching.update( to_lookup )
                
                service_key = async_text_info_shared_data[ 'service_key' ]
                
            
            terms_to_info = { term : None for term in to_lookup }
            
            for batch_to_lookup in HydrusData.SplitListIntoChunks( to_lookup, 500 ):
                
                tags_to_terms = { term.GetTag() : term for term in batch_to_lookup }
                
                tags_to_lookup = set( tags_to_terms.keys() )
                
                db_tags_to_ideals_and_parents = HG.client_controller.Read( 'tag_display_decorators', service_key, tags_to_lookup )
                
                terms_to_info.update( { tags_to_terms[ tag ] : info for ( tag, info ) in db_tags_to_ideals_and_parents.items() } )
                
            
            return terms_to_info
            
        
        return work_callable
        
    
    def _SelectFilesWithTags( self, and_or_or ):
        
        if self._page_key is not None:
            
            selected_actual_tags = self._GetTagsFromTerms( self._selected_terms )
            
            HG.client_controller.pub( 'select_files_with_tags', self._page_key, self._service_key, and_or_or, set( selected_actual_tags ) )
            
        
    
    def GetSelectedTags( self ):
        
        return set( self._GetTagsFromTerms( self._selected_terms ) )
        
    
    def SetTagServiceKey( self, service_key ):
        
        self._service_key = service_key
        
        with self._async_text_info_lock:
            
            self._async_text_info_shared_data[ 'service_key' ] = self._service_key
            
            self._pending_async_text_info_terms.clear()
            self._currently_fetching_async_text_info_terms.clear()
            self._terms_to_async_text_info = {}
            
        
    
class ListBoxTagsStrings( ListBoxTagsDisplayCapable ):
    
    def __init__( self, parent, service_key = None, sort_tags = True, **kwargs ):
        
        self._sort_tags = sort_tags
        
        ListBoxTagsDisplayCapable.__init__( self, parent, service_key = service_key, **kwargs )
        
    
    def _GenerateTermFromTag( self, tag: str ) -> ClientGUIListBoxesData.ListBoxItemTextTag:
        
        return ClientGUIListBoxesData.ListBoxItemTextTag( tag )
        
    
    def GetTags( self ):
        
        return set( self._GetTagsFromTerms( self._ordered_terms ) )
        
    
    def SetTags( self, tags ):
        
        previously_selected_terms = set( self._selected_terms )
        
        self._Clear()
        
        terms_to_add = [ self._GenerateTermFromTag( tag ) for tag in tags ]
        
        self._AppendTerms( terms_to_add )
        
        for term in previously_selected_terms:
            
            if term in self._terms_to_logical_indices:
                
                self._selected_terms.add( term )
                
            
        
        self._HitFirstSelectedItem()
        
        if self._sort_tags:
            
            self._Sort()
            
        
        self._DataHasChanged()
        
    
class ListBoxTagsStringsAddRemove( ListBoxTagsStrings ):
    
    tagsAdded = QC.Signal()
    tagsRemoved = QC.Signal()
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        if len( self._selected_terms ) > 0:
            
            tags = self._GetTagsFromTerms( self._selected_terms )
            
            self._RemoveSelectedTerms()
            
            self._DataHasChanged()
            
            self.tagsRemoved.emit()
            
            return True
            
        
        return False
        
    
    def _RemoveTags( self, tags ):
        
        terms = [ self._GenerateTermFromTag( tag ) for tag in tags ]
        
        self._RemoveTerms( terms )
        
        self._DataHasChanged()
        
        self.tagsRemoved.emit()
        
    
    def AddTags( self, tags ):
        
        terms = [ self._GenerateTermFromTag( tag ) for tag in tags ]
        
        self._AppendTerms( terms )
        
        if self._sort_tags:
            
            self._Sort()
            
        
        self._DataHasChanged()
        
        self.tagsAdded.emit()
        
    
    def Clear( self ):
        
        self._Clear()
        
        self._DataHasChanged()
        
        # doesn't do a removed tags call, this is a different lad
        
    
    def EnterTags( self, tags ):
        
        tags_removed = False
        tags_added = False
        
        for tag in tags:
            
            term = self._GenerateTermFromTag( tag )
            
            if term in self._terms_to_logical_indices:
                
                self._RemoveTerms( ( term, ) )
                
                tags_removed = True
                
            else:
                
                self._AppendTerms( ( term, ) )
                
                tags_added = True
                
            
        
        if self._sort_tags:
            
            self._Sort()
            
        
        self._DataHasChanged()
        
        if tags_added:
            
            self.tagsAdded.emit()
            
        
        if tags_removed:
            
            self.tagsRemoved.emit()
            
        
    
    def keyPressEvent( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key in ClientGUIShortcuts.DELETE_KEYS_QT:
            
            ctrl_down = modifier == ClientGUIShortcuts.SHORTCUT_MODIFIER_CTRL
            shift_down = modifier == ClientGUIShortcuts.SHORTCUT_MODIFIER_SHIFT
            
            action_occurred = self._Activate( ctrl_down, shift_down )
            
        else:
            
            ListBoxTagsStrings.keyPressEvent( self, event )
            
        
    
    def RemoveTags( self, tags ):
        
        self._RemoveTags( tags )
        
    
class ListBoxTagsMedia( ListBoxTagsDisplayCapable ):
    
    def __init__( self, parent, tag_display_type, service_key = None, include_counts = True ):
        
        if service_key is None:
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        ListBoxTagsDisplayCapable.__init__( self, parent, service_key = service_key, tag_display_type = tag_display_type, height_num_chars = 24 )
        
        self._tag_sort = HG.client_controller.new_options.GetDefaultTagSort()
        
        self._last_media_results = set()
        
        self._include_counts = include_counts
        
        self._current_tags_to_count = collections.Counter()
        self._deleted_tags_to_count = collections.Counter()
        self._pending_tags_to_count = collections.Counter()
        self._petitioned_tags_to_count = collections.Counter()
        
        self._show_current = True
        self._show_deleted = False
        self._show_pending = True
        self._show_petitioned = True
        
    
    def _GenerateTermFromTag( self, tag: str ) -> ClientGUIListBoxesData.ListBoxItemTextTag:
        
        current_count = self._current_tags_to_count[ tag ] if self._show_current and tag in self._current_tags_to_count else 0
        deleted_count = self._deleted_tags_to_count[ tag ] if self._show_deleted and tag in self._deleted_tags_to_count else 0
        pending_count = self._pending_tags_to_count[ tag ] if self._show_pending and tag in self._pending_tags_to_count else 0
        petitioned_count = self._petitioned_tags_to_count[ tag ] if self._show_petitioned and tag in self._petitioned_tags_to_count else 0
        
        return ClientGUIListBoxesData.ListBoxItemTextTagWithCounts(
            tag,
            current_count,
            deleted_count,
            pending_count,
            petitioned_count,
            self._include_counts
        )
        
    
    def _HasCounts( self ):
        
        return self._include_counts
        
    
    def _UpdateTerms( self, limit_to_these_tags = None ):
        
        previous_selected_terms = set( self._selected_terms )
        
        if limit_to_these_tags is None:
            
            self._Clear()
            
            nonzero_tags = set()
            
            if self._show_current: nonzero_tags.update( ( tag for ( tag, count ) in self._current_tags_to_count.items() if count > 0 ) )
            if self._show_deleted: nonzero_tags.update( ( tag for ( tag, count ) in self._deleted_tags_to_count.items() if count > 0 ) )
            if self._show_pending: nonzero_tags.update( ( tag for ( tag, count ) in self._pending_tags_to_count.items() if count > 0 ) )
            if self._show_petitioned: nonzero_tags.update( ( tag for ( tag, count ) in self._petitioned_tags_to_count.items() if count > 0 ) )
            
        else:
            
            if not isinstance( limit_to_these_tags, set ):
                
                limit_to_these_tags = set( limit_to_these_tags )
                
            
            clear_terms = [ self._GenerateTermFromTag( tag ) for tag in limit_to_these_tags ]
            
            self._RemoveTerms( clear_terms )
            
            nonzero_tags = set()
            
            if self._show_current: nonzero_tags.update( ( tag for ( tag, count ) in self._current_tags_to_count.items() if count > 0 and tag in limit_to_these_tags ) )
            if self._show_deleted: nonzero_tags.update( ( tag for ( tag, count ) in self._deleted_tags_to_count.items() if count > 0 and tag in limit_to_these_tags ) )
            if self._show_pending: nonzero_tags.update( ( tag for ( tag, count ) in self._pending_tags_to_count.items() if count > 0 and tag in limit_to_these_tags ) )
            if self._show_petitioned: nonzero_tags.update( ( tag for ( tag, count ) in self._petitioned_tags_to_count.items() if count > 0 and tag in limit_to_these_tags ) )
            
        
        nonzero_terms = [ self._GenerateTermFromTag( tag ) for tag in nonzero_tags ]
        
        self._AppendTerms( nonzero_terms )
        
        for term in previous_selected_terms:
            
            if term in self._terms_to_logical_indices:
                
                self._selected_terms.add( term )
                
            
        
        self._Sort()
        
    
    def _Sort( self ):
        
        # I do this weird terms to count instead of tags to count because of tag vs ideal tag gubbins later on in sort
        
        terms_to_count = collections.Counter()
        
        jobs = [
            ( self._show_current, self._current_tags_to_count ),
            ( self._show_deleted, self._deleted_tags_to_count ),
            ( self._show_pending, self._pending_tags_to_count ),
            ( self._show_petitioned, self._petitioned_tags_to_count )
        ]
        
        counts_to_include = [ c for ( show, c ) in jobs if show ]
        
        for term in self._ordered_terms:
            
            tag = term.GetTag()
            
            count = sum( ( c[ tag ] for c in counts_to_include if tag in c ) )
            
            terms_to_count[ term ] = count
            
        
        item_to_tag_key_wrapper = lambda term: term.GetTag()
        item_to_sibling_key_wrapper = item_to_tag_key_wrapper
        
        if self._sibling_decoration_allowed:
            
            item_to_sibling_key_wrapper = lambda term: term.GetBestTag()
            
        
        ClientTagSorting.SortTags( self._tag_sort, self._ordered_terms, tag_items_to_count = terms_to_count, item_to_tag_key_wrapper = item_to_tag_key_wrapper, item_to_sibling_key_wrapper = item_to_sibling_key_wrapper )
        
        self._RegenTermsToIndices()
        
    
    def AddAdditionalMenuItems( self, menu: QW.QMenu ):
        
        ListBoxTagsDisplayCapable.AddAdditionalMenuItems( self, menu )
        
        if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            submenu = QW.QMenu( menu )
            
            for tag_display_type in ( ClientTags.TAG_DISPLAY_SELECTION_LIST, ClientTags.TAG_DISPLAY_ACTUAL, ClientTags.TAG_DISPLAY_STORAGE ):
                
                if tag_display_type == self._tag_display_type:
                    
                    checked = True
                    
                    callable = lambda: 1
                    
                else:
                    
                    checked = False
                    
                    callable = HydrusData.Call( self.SetTagDisplayType, tag_display_type )
                    
                
                label = 'switch to "{}" tag display'.format( ClientTags.tag_display_str_lookup[ tag_display_type ] )
                description = 'Switch which tags this list shows, this may not work!'
                
                ClientGUIMenus.AppendMenuCheckItem( submenu, label, description, checked, callable )
                
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'experimental' )
            
        
    
    def IncrementTagsByMedia( self, media ):
        
        flat_media = ClientMedia.FlattenMedia( media )
        
        media_results = [ m.GetMediaResult() for m in flat_media ]
        
        self.IncrementTagsByMediaResults( media_results )
        
    
    def IncrementTagsByMediaResults( self, media_results ):
        
        if not isinstance( media_results, set ):
            
            media_results = set( media_results )
            
        
        media_results = media_results.difference( self._last_media_results )
        
        ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientMedia.GetMediaResultsTagCount( media_results, self._service_key, self._tag_display_type )
        
        tags_changed = set()
        
        if self._show_current: tags_changed.update( current_tags_to_count.keys() )
        if self._show_deleted: tags_changed.update( deleted_tags_to_count.keys() )
        if self._show_pending: tags_changed.update( pending_tags_to_count.keys() )
        if self._show_petitioned: tags_changed.update( petitioned_tags_to_count.keys() )
        
        self._current_tags_to_count.update( current_tags_to_count )
        self._deleted_tags_to_count.update( deleted_tags_to_count )
        self._pending_tags_to_count.update( pending_tags_to_count )
        self._petitioned_tags_to_count.update( petitioned_tags_to_count )
        
        if len( tags_changed ) > 0:
            
            self._UpdateTerms( tags_changed )
            
        
        self._last_media_results.update( media_results )
        
        self._DataHasChanged()
        
    
    def SetTagsByMedia( self, media ):
        
        flat_media = ClientMedia.FlattenMedia( media )
        
        media_results = [ m.GetMediaResult() for m in flat_media ]
        
        self.SetTagsByMediaResults( media_results )
        
    
    def SetTagsByMediaResults( self, media_results ):
        
        if not isinstance( media_results, set ):
            
            media_results = set( media_results )
            
        
        ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientMedia.GetMediaResultsTagCount( media_results, self._service_key, self._tag_display_type )
        
        self._current_tags_to_count = current_tags_to_count
        self._deleted_tags_to_count = deleted_tags_to_count
        self._pending_tags_to_count = pending_tags_to_count
        self._petitioned_tags_to_count = petitioned_tags_to_count
        
        self._UpdateTerms()
        
        self._last_media_results = media_results
        
        self._DataHasChanged()
        
    
    def SetTagsByMediaFromMediaPanel( self, media, tags_changed ):
        
        flat_media = ClientMedia.FlattenMedia( media )
        
        media_results = [ m.GetMediaResult() for m in flat_media ]
        
        self.SetTagsByMediaResultsFromMediaPanel( media_results, tags_changed )
        
    
    def SetTagsByMediaResultsFromMediaPanel( self, media_results, tags_changed ):
        
        if not isinstance( media_results, set ):
            
            media_results = set( media_results )
            
        
        # this uses the last-set media and count cache to generate new numbers and is faster than re-counting from scratch when the tags have not changed
        
        selection_shrank_a_lot = len( media_results ) < len( self._last_media_results ) // 10 # if we are dropping to a much smaller selection (e.g. 5000 -> 1), we should just recalculate from scratch
        
        if tags_changed or selection_shrank_a_lot:
            
            self.SetTagsByMediaResults( media_results )
            
            return
            
        
        removees = self._last_media_results.difference( media_results )
        
        if len( removees ) == 0:
            
            self.IncrementTagsByMediaResults( media_results )
            
            return
            
        
        adds = media_results.difference( self._last_media_results )
        
        ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientMedia.GetMediaResultsTagCount( removees, self._service_key, self._tag_display_type )
        
        self._current_tags_to_count.subtract( current_tags_to_count )
        self._deleted_tags_to_count.subtract( deleted_tags_to_count )
        self._pending_tags_to_count.subtract( pending_tags_to_count )
        self._petitioned_tags_to_count.subtract( petitioned_tags_to_count )
        
        ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientMedia.GetMediaResultsTagCount( adds, self._service_key, self._tag_display_type )
        
        self._current_tags_to_count.update( current_tags_to_count )
        self._deleted_tags_to_count.update( deleted_tags_to_count )
        self._pending_tags_to_count.update( pending_tags_to_count )
        self._petitioned_tags_to_count.update( petitioned_tags_to_count )
        
        for counter in ( self._current_tags_to_count, self._deleted_tags_to_count, self._pending_tags_to_count, self._petitioned_tags_to_count ):
            
            tags = list( counter.keys() )
            
            for tag in tags:
                
                if counter[ tag ] == 0:
                    
                    del counter[ tag ]
                    
                
            
        
        self._UpdateTerms()
        
        self._last_media_results = media_results
        
        self._DataHasChanged()
        
    
    def SetTagDisplayType( self, tag_display_type: int ):
        
        self._tag_display_type = tag_display_type
        
        self.ForceTagRecalc()
        
    
    def SetTagServiceKey( self, service_key ):
        
        ListBoxTagsDisplayCapable.SetTagServiceKey( self, service_key )
        
        self.SetTagsByMediaResults( self._last_media_results )
        
    
    def SetSort( self, tag_sort: ClientTagSorting.TagSort ):
        
        self._tag_sort = tag_sort
        
        self._Sort()
        
        self._DataHasChanged()
        
    
    def SetShow( self, show_type, value ):
        
        if show_type == 'current': self._show_current = value
        elif show_type == 'deleted': self._show_deleted = value
        elif show_type == 'pending': self._show_pending = value
        elif show_type == 'petitioned': self._show_petitioned = value
        
        self._UpdateTerms()
        
    
    def ForceTagRecalc( self ):
        
        self.SetTagsByMediaResults( self._last_media_results )
        
    
class StaticBoxSorterForListBoxTags( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, title, show_siblings_sort = False ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, title )
        
        self._original_title = title
        
        self._tags_box = None
        
        # make this its own panel
        self._tag_sort = ClientGUITagSorting.TagSortControl( self, HG.client_controller.new_options.GetDefaultTagSort(), show_siblings = show_siblings_sort )
        
        self._tag_sort.valueChanged.connect( self.EventSort )
        
        self.Add( self._tag_sort, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def SetTagServiceKey( self, service_key ):
        
        if self._tags_box is None:
            
            return
            
        
        self._tags_box.SetTagServiceKey( service_key )
        
        title = self._original_title
        
        if service_key != CC.COMBINED_TAG_SERVICE_KEY:
            
            title = '{} for {}'.format( title, HG.client_controller.services_manager.GetName( service_key ) )
            
        
        self.SetTitle( title )
        
    
    def EventSort( self ):
        
        if self._tags_box is None:
            
            return
            
        
        sort = self._tag_sort.GetValue()
        
        self._tags_box.SetSort( sort )
        
    
    def SetTagsBox( self, tags_box: ListBoxTagsMedia ):
        
        self._tags_box = tags_box
        
        self.Add( self._tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def SetTagsByMedia( self, media ):
        
        if self._tags_box is None:
            
            return
            
        
        self._tags_box.SetTagsByMedia( media )
        
    
class ListBoxTagsMediaHoverFrame( ListBoxTagsMedia ):
    
    def __init__( self, parent, canvas_key ):
        
        ListBoxTagsMedia.__init__( self, parent, ClientTags.TAG_DISPLAY_SINGLE_MEDIA, include_counts = False )
        
        self._canvas_key = canvas_key
        
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        HG.client_controller.pub( 'canvas_manage_tags', self._canvas_key )
        
        return True
        
    
class ListBoxTagsMediaTagsDialog( ListBoxTagsMedia ):
    
    def __init__( self, parent, enter_func, delete_func ):
        
        ListBoxTagsMedia.__init__( self, parent, ClientTags.TAG_DISPLAY_STORAGE, include_counts = True )
        
        self._enter_func = enter_func
        self._delete_func = delete_func
        
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        if len( self._selected_terms ) > 0:
            
            tags = set( self._GetTagsFromTerms( self._selected_terms ) )
            
            self._enter_func( tags )
            
            return True
            
        
        return False
        
    
    def _DeleteActivate( self ):
        
        if len( self._selected_terms ) > 0:
            
            tags = set( self._GetTagsFromTerms( self._selected_terms ) )
            
            self._delete_func( tags )
            
        
    
