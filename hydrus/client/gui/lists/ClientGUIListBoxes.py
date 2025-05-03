import collections
import itertools
import threading
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientSerialisable
from hydrus.client import ClientServices
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITagSorting
from hydrus.client.gui import QtInit
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxesData
from hydrus.client.gui.search import ClientGUISearch
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientTagSorting
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

class BetterQListWidget( QW.QListWidget ):
    
    def __init__( self, parent, delete_callable = None ):
        
        self._delete_callable = delete_callable
        
        super().__init__( parent )
        
    
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
        
    
    def _GetListWidgetItems( self, only_selected = False ) -> typing.Collection[ QW.QListWidgetItem ]:
        
        # not sure if selectedItems is always sorted, so just do it manually
        
        list_widget_items = []
        
        for index in range( self.count() ):
            
            list_widget_item = self.item( index )
            
            if only_selected and not list_widget_item.isSelected():
                
                continue
                
            
            list_widget_items.append( list_widget_item )
            
        
        return list_widget_items
        
    
    def _GetRowData( self, list_widget_item: QW.QListWidgetItem ):
        
        return list_widget_item.data( QC.Qt.ItemDataRole.UserRole )
        
    
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
        
    
    def Append( self, text: str, data: object, select = False ):
        
        item = QW.QListWidgetItem()
        
        item.setText( text )
        item.setData( QC.Qt.ItemDataRole.UserRole, data )
        
        self.addItem( item )
        
        if select:
            
            item.setSelected( True )
            
        
    
    def DeleteData( self, datas: typing.Collection[ object ] ):
        
        indices = self._GetDataIndices( datas )
        
        self._DeleteIndices( indices )
        
    
    def DeleteSelected( self ):
        
        indices = self._GetSelectedIndices()
        
        self._DeleteIndices( indices )
        
    
    def GetData( self, only_selected: bool = False ) -> typing.List[ typing.Any ]:
        
        datas = []
        
        list_widget_items = self._GetListWidgetItems( only_selected = only_selected )
        
        for list_widget_item in list_widget_items:
            
            data = self._GetRowData( list_widget_item )
            
            datas.append( data )
            
        
        return datas
        
    
    def GetNumSelected( self ) -> int:
        
        indices = self._GetSelectedIndices()
        
        return len( indices )
        
    
    def GetSelectedIndices( self ):
        
        return self._GetSelectedIndices()
        
    
    def HasData( self, obj ):
        
        return obj in self.GetData()
        
    
    def keyPressEvent( self, event: QG.QKeyEvent ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key in ClientGUIShortcuts.DELETE_KEYS_QT and self._delete_callable is not None:
            
            event.accept()
            
            self._delete_callable()
            
        elif event.modifiers() & QC.Qt.KeyboardModifier.ControlModifier and event.key() in ( QC.Qt.Key.Key_C, QC.Qt.Key.Key_Insert ):
            
            event.accept()
            
            try:
                
                texts_to_copy = []
                
                for list_widget_item in self.selectedItems():
                    
                    user_role_data = list_widget_item.data( QC.Qt.ItemDataRole.UserRole )
                    
                    if isinstance( user_role_data, str ):
                        
                        text = user_role_data
                        
                    else:
                        
                        text = list_widget_item.text()
                        
                    
                    texts_to_copy.append( text )
                    
                
                if len( texts_to_copy ) == 0:
                    
                    return
                    
                
                copyable_text = '\n'.join( texts_to_copy )
                
                CG.client_controller.pub( 'clipboard', 'text', copyable_text )
                
            except Exception as e:
                
                HydrusData.ShowText( 'Could not copy some text from a list!' )
                
                HydrusData.ShowException( e )
                
            
        else:
            
            QW.QListWidget.keyPressEvent( self, event )
            
        
    
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
        
        datas = set( datas )
        
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
        
        super().__init__( parent )
        
        self._listbox = BetterQListWidget( self )
        self._listbox.setSelectionMode( QW.QAbstractItemView.SelectionMode.ExtendedSelection )
        
        self._add_button = ClientGUICommon.BetterButton( self, 'add', self._Add )
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self._Edit )
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self._Delete )
        
        self._enabled_only_on_selection_buttons = []
        
        self._permitted_object_types = tuple()
        
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
        
    
    def _AddData( self, data, select = False ):
        
        self._SetNonDupeName( data )
        
        pretty_data = self._data_to_pretty_callable( data )
        
        self._listbox.Append( pretty_data, data, select = select )
        
    
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
        
    
    def _CheckImportObjectCustom( self, obj ):
        
        pass
        
    
    def _Delete( self ):
        
        num_selected = self._listbox.GetNumSelected()
        
        if num_selected == 0:
            
            return
            
        
        from hydrus.client.gui import ClientGUIDialogsQuick
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove {} selected?'.format( HydrusNumbers.ToHumanInt( num_selected ) ) )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        self._listbox.DeleteSelected()
        
        self.listBoxChanged.emit()
        
    
    def _Edit( self ):
        
        for list_widget_item in self._listbox.selectedItems():
            
            data = list_widget_item.data( QC.Qt.ItemDataRole.UserRole )
            
            try:
                
                new_data = self._edit_callable( data )
                
            except HydrusExceptions.VetoException:
                
                break
                
            
            self._SetNonDupeName( new_data )
            
            pretty_new_data = self._data_to_pretty_callable( new_data )
            
            list_widget_item.setText( pretty_new_data )
            list_widget_item.setData( QC.Qt.ItemDataRole.UserRole, new_data )
            
        
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
            
            CG.client_controller.pub( 'clipboard', 'text', json )
            
        
    
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
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
            self._ImportObject( obj )
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON-serialised Hydrus Object(s)', e )
            
        
    
    def _ImportFromPNG( self ):
        
        with QP.FileDialog( self, 'select the png or pngs with the encoded data', acceptMode = QW.QFileDialog.AcceptMode.AcceptOpen, fileMode = QW.QFileDialog.FileMode.ExistingFiles, wildcard = 'PNG (*.png)' ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                for path in dlg.GetPaths():
                    
                    try:
                        
                        payload = ClientSerialisable.LoadFromPNG( path )
                        
                    except Exception as e:
                        
                        HydrusData.PrintException( e )
                        
                        ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', str(e) )
                        
                        return
                        
                    
                    try:
                        
                        obj = HydrusSerialisable.CreateFromNetworkBytes( payload )
                        
                        self._ImportObject( obj )
                        
                    except Exception as e:
                        
                        HydrusData.PrintException( e )
                        
                        ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', 'I could not understand what was encoded in the png!' )
                        
                        return
                        
                    
                
            
        
    
    def _ImportObject( self, obj, can_present_messages = True ):
        
        num_added = 0
        bad_object_type_names = set()
        other_bad_errors = set()
        
        if isinstance( obj, HydrusSerialisable.SerialisableList ):
            
            for sub_obj in obj:
                
                ( sub_num_added, sub_bad_object_type_names, sub_other_bad_errors ) = self._ImportObject( sub_obj, can_present_messages = False )
                
                num_added += sub_num_added
                bad_object_type_names.update( sub_bad_object_type_names )
                other_bad_errors.update( sub_other_bad_errors )
                
            
        else:
            
            if isinstance( obj, self._permitted_object_types ):
                
                import_ok = True
                
                try:
                    
                    self._CheckImportObjectCustom( obj )
                    
                except HydrusExceptions.VetoException as e:
                    
                    import_ok = False
                    
                    other_bad_errors.add( str( e ) )
                    
                
                if import_ok:
                    
                    self._AddData( obj, select = True )
                    
                    num_added += 1
                    
                
            else:
                
                bad_object_type_names.add( HydrusData.GetTypeName( type( obj ) ) )
                
            
        
        if can_present_messages:
            
            if len( bad_object_type_names ) > 0:
                
                message = 'The imported objects included these types:'
                message += '\n' * 2
                message += '\n'.join( bad_object_type_names )
                message += '\n' * 2
                message += 'Whereas this control only allows:'
                message += '\n' * 2
                message += '\n'.join( ( HydrusData.GetTypeName( o ) for o in self._permitted_object_types ) )
                
                ClientGUIDialogsMessage.ShowWarning( self, message )
                
            
            if len( other_bad_errors ) > 0:
                
                message = 'The imported objects were wrong for this control:'
                message += '\n' * 2
                message += '\n'.join( other_bad_errors )
                
                ClientGUIDialogsMessage.ShowWarning( self, message )
                
            
            if num_added > 0:
                
                message = '{} objects added!'.format( HydrusNumbers.ToHumanInt( num_added ) )
                
                ClientGUIDialogsMessage.ShowInformation( self, message )
                
            
        
        self.listBoxChanged.emit()
        
        return ( num_added, bad_object_type_names, other_bad_errors )
        
    
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
        
        self._permitted_object_types = tuple( permitted_object_types )
        
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
        
    
    def Clear( self ):
        
        self._listbox.clear()
        
    
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
        
    

# TODO: We must be able to unify this guy with AddEditDeleteListBox mate. This is basically just that guy but with (duplicates allowed?) and different sort
# failing that, we must be able to merge a bunch of this to a base superclass
class QueueListBox( QW.QWidget ):
    
    listBoxContentsChanged = QC.Signal()
    listBoxContentsDeleted = QC.Signal()
    listBoxOrderChanged = QC.Signal()
    listBoxChanged = QC.Signal()
    
    def __init__( self, parent, height_num_chars, data_to_pretty_callable, add_callable = None, edit_callable = None, paste_callable = None ):
        
        self._data_to_pretty_callable = data_to_pretty_callable
        self._add_callable = add_callable
        self._paste_callable = paste_callable
        self._edit_callable = edit_callable
        
        super().__init__( parent )
        
        self._permitted_object_types = tuple()
        
        self._listbox = BetterQListWidget( self, delete_callable = self._Delete )
        self._listbox.setSelectionMode( QW.QAbstractItemView.SelectionMode.ExtendedSelection )
        
        self._up_button = ClientGUICommon.BetterButton( self, '\u2191', self._Up )
        
        self._delete_button = ClientGUICommon.BetterButton( self, 'X', self._Delete )
        
        self._down_button = ClientGUICommon.BetterButton( self, '\u2193', self._Down )
        
        self._add_button = ClientGUICommon.BetterButton( self, 'add', self._Add )
        self._paste_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().paste, self._Paste )
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self._Edit )
        
        self._enabled_only_on_selection_buttons = []
        
        if self._add_callable is None:
            
            self._add_button.hide()
            
        
        if paste_callable is None:
            
            self._paste_button.hide()
            
        
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
        
        self._buttons_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( self._buttons_hbox, self._add_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( self._buttons_hbox, self._paste_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( self._buttons_hbox, self._edit_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._buttons_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
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
        
        self.listBoxContentsChanged.emit()
        self.listBoxChanged.emit()
        
    
    def _AddData( self, data ):
        
        pretty_data = self._data_to_pretty_callable( data )
        
        self._listbox.Append( pretty_data, data )
        
    
    def _CheckImportObjectCustom( self, obj ):
        
        pass
        
    
    def _Delete( self ):
        
        num_selected = self._listbox.GetNumSelected()
        
        if num_selected == 0:
            
            return
            
        
        from hydrus.client.gui import ClientGUIDialogsQuick
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove {} selected?'.format( HydrusNumbers.ToHumanInt( num_selected ) ) )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._listbox.DeleteSelected()
            
            self.listBoxContentsChanged.emit()
            self.listBoxContentsDeleted.emit()
            self.listBoxChanged.emit()
            
        
    
    def _Down( self ):
        
        self._listbox.MoveSelected( 1 )
        
        self.listBoxOrderChanged.emit()
        self.listBoxChanged.emit()
        
    
    def _Duplicate( self ):
        
        dupe_data = self._GetExportObject()
        
        if dupe_data is not None:
            
            dupe_data = dupe_data.Duplicate()
            
            self._ImportObject( dupe_data )
            
        
    
    def _Edit( self ):
        
        items = list( self._listbox.selectedItems() )
        
        if len( items ) == 0:
            
            return
            
        
        top_list_widget_item = items[0]
        
        data = top_list_widget_item.data( QC.Qt.ItemDataRole.UserRole )
        
        try:
            
            new_data = self._edit_callable( data )
            
        except HydrusExceptions.VetoException:
            
            return
            
        
        pretty_new_data = self._data_to_pretty_callable( new_data )
        
        top_list_widget_item.setText( pretty_new_data )
        top_list_widget_item.setData( QC.Qt.ItemDataRole.UserRole, new_data )
        
        self.listBoxContentsChanged.emit()
        self.listBoxChanged.emit()
        
    
    def _ExportToClipboard( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            json = export_object.DumpToString()
            
            CG.client_controller.pub( 'clipboard', 'text', json )
            
        
    
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
            
            raw_text = CG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting!', str(e) )
            
            return
            
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
            self._ImportObject( obj )
            
        except Exception as e:
            
            ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON-serialised Hydrus Object(s)', e )
            
        
    
    def _ImportFromPNG( self ):
        
        with QP.FileDialog( self, 'select the png or pngs with the encoded data', acceptMode = QW.QFileDialog.AcceptMode.AcceptOpen, fileMode = QW.QFileDialog.FileMode.ExistingFiles, wildcard = 'PNG (*.png)' ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                for path in dlg.GetPaths():
                    
                    try:
                        
                        payload = ClientSerialisable.LoadFromPNG( path )
                        
                    except Exception as e:
                        
                        HydrusData.PrintException( e )
                        
                        ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', str(e) )
                        
                        return
                        
                    
                    try:
                        
                        obj = HydrusSerialisable.CreateFromNetworkBytes( payload )
                        
                        self._ImportObject( obj )
                        
                    except Exception as e:
                        
                        HydrusData.PrintException( e )
                        
                        ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', 'I could not understand what was encoded in the png!' )
                        
                        return
                        
                    
                
            
        
    
    def _ImportObject( self, obj, can_present_messages = True ):
        
        num_added = 0
        bad_object_type_names = set()
        other_bad_errors = set()
        
        if isinstance( obj, HydrusSerialisable.SerialisableList ):
            
            for sub_obj in obj:
                
                ( sub_num_added, sub_bad_object_type_names, sub_other_bad_errors ) = self._ImportObject( sub_obj, can_present_messages = False )
                
                num_added += sub_num_added
                bad_object_type_names.update( sub_bad_object_type_names )
                other_bad_errors.update( sub_other_bad_errors )
                
            
        else:
            
            if isinstance( obj, self._permitted_object_types ):
                
                import_ok = True
                
                try:
                    
                    self._CheckImportObjectCustom( obj )
                    
                except HydrusExceptions.VetoException as e:
                    
                    import_ok = False
                    
                    other_bad_errors.add( str( e ) )
                    
                
                if import_ok:
                    
                    self._AddData( obj )
                    
                    num_added += 1
                    
                
            else:
                
                bad_object_type_names.add( HydrusData.GetTypeName( type( obj ) ) )
                
            
        
        if can_present_messages:
            
            if len( bad_object_type_names ) > 0:
                
                message = 'The imported objects included these types:'
                message += '\n' * 2
                message += '\n'.join( bad_object_type_names )
                message += '\n' * 2
                message += 'Whereas this control only allows:'
                message += '\n' * 2
                message += '\n'.join( ( HydrusData.GetTypeName( o ) for o in self._permitted_object_types ) )
                
                ClientGUIDialogsMessage.ShowWarning( self, message )
                
            
            if len( other_bad_errors ) > 0:
                
                message = 'The imported objects were wrong for this control:'
                message += '\n' * 2
                message += '\n'.join( other_bad_errors )
                
                ClientGUIDialogsMessage.ShowWarning( self, message )
                
            
            if num_added > 0:
                
                message = '{} objects added!'.format( HydrusNumbers.ToHumanInt( num_added ) )
                
                ClientGUIDialogsMessage.ShowInformation( self, message )
                
            
        
        self.listBoxContentsChanged.emit()
        self.listBoxChanged.emit()
        
        return ( num_added, bad_object_type_names, other_bad_errors )
        
    
    def _Paste( self ):
        
        try:
            
            datas = self._paste_callable()
            
        except HydrusExceptions.VetoException:
            
            return
            
        
        for data in datas:
            
            self._AddData( data )
            
        
        self.listBoxContentsChanged.emit()
        self.listBoxChanged.emit()
        
    
    def _Up( self ):
        
        self._listbox.MoveSelected( -1 )
        
        self.listBoxOrderChanged.emit()
        self.listBoxChanged.emit()
        
    
    def _UpdateButtons( self ):
        
        we_have_selection = self._listbox.GetNumSelected() > 0
        
        self._up_button.setEnabled( we_have_selection )
        self._delete_button.setEnabled( we_have_selection )
        self._down_button.setEnabled( we_have_selection )
        
        self._edit_button.setEnabled( we_have_selection )
        
        for button in self._enabled_only_on_selection_buttons:
            
            button.setEnabled( we_have_selection )
            
        
    
    def AddDatas( self, datas ):
        
        for data in datas:
            
            self._AddData( data )
            
        
        self.listBoxContentsChanged.emit()
        self.listBoxChanged.emit()
        
    
    def AddImportExportButtons( self, permitted_object_types ):
        
        self._permitted_object_types = tuple( permitted_object_types )
        
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
        QP.AddToLayout( self._buttons_hbox, button, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._enabled_only_on_selection_buttons.append( button )
        
        button = ClientGUIMenuButton.MenuButton( self, 'import', import_menu_items )
        QP.AddToLayout( self._buttons_hbox, button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        button = ClientGUICommon.BetterButton( self, 'duplicate', self._Duplicate )
        QP.AddToLayout( self._buttons_hbox, button, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._enabled_only_on_selection_buttons.append( button )
        
        self._UpdateButtons()
        
    
    def Clear( self ):
        
        self._listbox.clear()
        
    
    def GetCount( self ):
        
        return self._listbox.count()
        
    
    def GetData( self, only_selected = False ):
        
        return self._listbox.GetData( only_selected = only_selected )
        
    
    def Pop( self ):
        
        if self._listbox.count() == 0:
            
            return None
            
        
        return self._listbox.PopData( 0 )
        
    
    def SetData( self, datas ):
        
        selected_datas = self.GetData( only_selected = True )
        
        self._listbox.clear()
        
        for data in datas:
            
            self._AddData( data )
            
        
        self._listbox.SelectData( selected_datas )
        
    

class ListBox( QW.QScrollArea ):
    
    listBoxChanged = QC.Signal()
    mouseActivationOccurred = QC.Signal()
    
    TEXT_X_PADDING = 2
    
    def __init__( self, parent: QW.QWidget, terms_may_have_sibling_or_parent_info: bool, height_num_chars = 10, has_async_text_info = False ):
        
        super().__init__( parent )
        self.setFrameStyle( QW.QFrame.Shape.Panel | QW.QFrame.Shadow.Sunken )
        self.setHorizontalScrollBarPolicy( QC.Qt.ScrollBarPolicy.ScrollBarAlwaysOff )
        self.setVerticalScrollBarPolicy( QC.Qt.ScrollBarPolicy.ScrollBarAsNeeded )
        self.setWidget( ListBox._InnerWidget( self ) )
        self.setWidgetResizable( True )
        
        self._ordered_terms = []
        self._terms_to_logical_indices = {}
        self._terms_to_positional_indices = {}
        self._positional_indices_to_terms = {}
        self._selected_terms = set()
        self._total_positional_rows = 0
        
        self._last_hit_logical_index = None
        self._shift_click_start_logical_index = None
        self._logical_indices_selected_this_shift_click = set()
        self._logical_indices_deselected_this_shift_click = set()
        self._in_drag = False
        self._this_drag_is_a_deselection = False
        
        self._last_view_start = None
        
        self._height_num_chars = height_num_chars
        self._minimum_height_num_chars = 8
        self._max_height_num_chars = None
        
        self._num_rows_per_page = 0
        
        self._draw_background = True
        
        self._show_sibling_decorators = True
        self._show_parent_decorators = True
        self._extra_parent_rows_allowed = True
        
        self._terms_may_have_sibling_or_parent_info = terms_may_have_sibling_or_parent_info
        
        #
        
        self._has_async_text_info = has_async_text_info
        self._terms_to_async_text_info = {}
        self._pending_async_text_info_terms = set()
        self._currently_fetching_async_text_info_terms = set()
        self._async_text_info_lock = threading.Lock()
        self._async_text_info_updater = self._InitialiseAsyncTextInfoUpdater()
        
    
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
                
            
            show_parent_rows = self._show_parent_decorators and self._extra_parent_rows_allowed
            
            self._total_positional_rows += term.GetRowCount( show_parent_rows )
            
        
        if len( previously_selected_terms ) > 0:
            
            self._selected_terms.update( previously_selected_terms )
            
        
    
    def _Clear( self ):
        
        self._ordered_terms = []
        self._selected_terms = set()
        self._terms_to_logical_indices = {}
        self._terms_to_positional_indices = {}
        self._positional_indices_to_terms = {}
        self._total_positional_rows = 0
        
        self._shift_click_start_logical_index = None
        self._logical_indices_selected_this_shift_click = set()
        self._logical_indices_deselected_this_shift_click = set()
        self._in_drag = False
        self._this_drag_is_a_deselection = False
        
        self._last_hit_logical_index = None
        
        self._last_view_start = None
        
    
    def _CopySelectedTexts( self ):
        
        if len( self._selected_terms ) > 1:
            
            # keep order
            terms = [ term for term in self._ordered_terms if term in self._selected_terms ]
            
        else:
            
            # nice and fast
            terms = self._selected_terms
            
        
        texts = HydrusLists.MassExtend( [ term.GetCopyableTexts() for term in terms ] )
        
        if len( texts ) > 0:
            
            text = '\n'.join( texts )
            
            CG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _DataHasChanged( self ):
        
        self._SetVirtualSize()
        
        self.widget().update()
        
        self.listBoxChanged.emit()
        
        self._SelectionChanged()
        
    
    def _Deselect( self, index ):
        
        try:
            
            term = self._GetTermFromLogicalIndex( index )
            
        except HydrusExceptions.DataMissing:
            
            # we've got ghosts, so exorcise them
            self._DeselectAll()
            
            return
            
        
        self._selected_terms.discard( term )
        
        self.widget().update()
        
    
    def _DeselectAll( self ):
        
        self._selected_terms = set()
        
        self.widget().update()
        
    
    def _GetBackgroundColour( self ):
        
        return QG.QColor( 255, 255, 255 )
        
    
    def _GetCopyableTagStrings( self, command, include_parents = False, collapse_ors = False ):
        
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
            
        
        copyable_tag_strings = HydrusLists.MassExtend( [ term.GetCopyableTexts( with_counts = with_counts, include_parents = include_parents, collapse_ors = collapse_ors ) for term in terms ] )
        
        if only_subtags:
            
            copyable_tag_strings = [ HydrusTags.SplitTag( tag_string )[1] for tag_string in copyable_tag_strings ]
            
        
        if '' in copyable_tag_strings:
            
            copyable_tag_strings.remove( '' )
            
        
        if not with_counts:
            
            copyable_tag_strings = HydrusData.DedupeList( copyable_tag_strings )
            
        
        return copyable_tag_strings
        
    
    def _GetLogicalIndexFromTerm( self, term ):
        
        if term in self._terms_to_logical_indices:
            
            return self._terms_to_logical_indices[ term ]
            
        
        raise HydrusExceptions.DataMissing()
        
    
    def _GetLogicalIndexUnderMouse( self, mouse_event ):
        
        positional_index = self._GetPositionalIndexUnderMouse( mouse_event )
        
        if positional_index < 0 or positional_index >= self._total_positional_rows:
            
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
        
    
    def _GetPositionalIndexUnderMouse( self, mouse_event ):
        
        y = mouse_event.position().toPoint().y()
        
        if mouse_event.type() == QC.QEvent.Type.MouseMove:
            
            visible_rect = QP.ScrollAreaVisibleRect( self )
            
            visible_rect_y = visible_rect.y()
            
            y += visible_rect_y
            
        
        text_height = self.fontMetrics().height()
        
        positional_index = y // text_height
        
        return positional_index
        
    
    def _GetPredicatesFromTerms( self, terms: typing.Collection[ ClientGUIListBoxesData.ListBoxItem ] ):
        
        return list( itertools.chain.from_iterable( ( term.GetSearchPredicates() for term in terms ) ) )
        
    
    def _GetRowsOfTextsAndColours( self, term: ClientGUIListBoxesData.ListBoxItem ):
        
        raise NotImplementedError()
        
    
    def _GetSelectedPredicatesAndInverseCopies( self ):
        
        predicates = self._GetPredicatesFromTerms( self._selected_terms )
        inverse_predicates = [ predicate.GetInverseCopy() for predicate in predicates if predicate.IsInvertible() ]
        
        if len( predicates ) > 1 and ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER not in ( p.GetType() for p in predicates ):
            
            or_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, value = list( predicates ) )
            
        else:
            
            or_predicate = None
            
        
        namespace_predicate = None
        inverse_namespace_predicate = None
        
        if False not in [ predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_TAG for predicate in predicates ]:
            
            namespaces = { HydrusTags.SplitTag( predicate.GetValue() )[0] for predicate in predicates }
            
            if len( namespaces ) == 1:
                
                ( namespace, ) = namespaces
                
                namespace_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, value = namespace )
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
        
        shift = event.modifiers() & QC.Qt.KeyboardModifier.ShiftModifier
        ctrl = event.modifiers() & QC.Qt.KeyboardModifier.ControlModifier
        
        self._Hit( shift, ctrl, logical_index )
        

    def _Hit( self, shift, ctrl, hit_logical_index ):
        
        if hit_logical_index is not None and ( hit_logical_index < 0 or hit_logical_index >= len( self._ordered_terms ) ):
            
            hit_logical_index = None
            
        
        to_select = set()
        to_deselect = set()
        
        deselect_all = False
        
        if not shift:
            
            self._shift_click_start_logical_index = hit_logical_index # this can be None
            self._logical_indices_selected_this_shift_click = set()
            self._logical_indices_deselected_this_shift_click = set()
            
        
        if shift:
            
            # if we started a shift click already, then assume the end of the list
            # this lets us shift-click in whitespace and select to the end
            # however don't initialise a shift-click this way
            if hit_logical_index is None and self._shift_click_start_logical_index is not None:
                
                hit_logical_index = len( self ) - 1
                
            
            if hit_logical_index is not None:
                
                if self._shift_click_start_logical_index is None or self._last_hit_logical_index is None:
                    
                    if self._last_hit_logical_index is None:
                        
                        # no obvious start point to initialise from (blind shift-click out of nowhere), so let's start right here with this click
                        self._last_hit_logical_index = hit_logical_index
                        
                    
                    self._shift_click_start_logical_index = self._last_hit_logical_index
                    
                
                if ctrl:
                    
                    if len( self._logical_indices_selected_this_shift_click ) > 0:
                        
                        self._shift_click_start_logical_index = self._last_hit_logical_index
                        self._logical_indices_selected_this_shift_click = set()
                        
                    
                else:
                    
                    if len( self._logical_indices_deselected_this_shift_click ) > 0:
                        
                        self._shift_click_start_logical_index = self._last_hit_logical_index
                        self._logical_indices_deselected_this_shift_click = set()
                        
                    
                
                min_index = min( self._shift_click_start_logical_index, hit_logical_index )
                max_index = max( self._shift_click_start_logical_index, hit_logical_index )
                
                logical_indices_between_start_and_hit = list( range( min_index, max_index + 1 ) )
                
                if ctrl:
                    
                    # deselect mode, either drag or shift-click
                    
                    to_deselect = [ logical_index for logical_index in logical_indices_between_start_and_hit if self._LogicalIndexIsSelected( logical_index ) ]
                    
                    # any that were previously deselected but no longer in our shift range should be re-selected
                    to_select = [ logical_index for logical_index in self._logical_indices_deselected_this_shift_click if logical_index not in logical_indices_between_start_and_hit ]
                    
                    self._logical_indices_deselected_this_shift_click.update( to_deselect )
                    self._logical_indices_deselected_this_shift_click.difference_update( to_select )
                    
                else:
                    
                    to_select = [ logical_index for logical_index in logical_indices_between_start_and_hit if not self._LogicalIndexIsSelected( logical_index ) ]
                    
                    # any that were previously selected but no longer in our shift range should be deselected
                    to_deselect = [ logical_index for logical_index in self._logical_indices_selected_this_shift_click if logical_index not in logical_indices_between_start_and_hit ]
                    
                    self._logical_indices_selected_this_shift_click.update( to_select )
                    self._logical_indices_selected_this_shift_click.difference_update( to_deselect )
                    
                
            
        elif ctrl:
            
            if hit_logical_index is not None:
                
                if self._LogicalIndexIsSelected( hit_logical_index ):
                    
                    to_deselect.add( hit_logical_index )
                    
                else:
                    
                    to_select.add( hit_logical_index )
                    
                
            
        else:
            
            if hit_logical_index is None:
                
                deselect_all = True
                
            else:
                
                if not self._LogicalIndexIsSelected( hit_logical_index ):
                    
                    deselect_all = True
                    to_select.add( hit_logical_index )
                    
                
            
        
        if deselect_all:
            
            self._DeselectAll()
            
        
        for index in to_select:
            
            self._Select( index )
            
        
        for index in to_deselect:
            
            self._Deselect( index )
            
        
        self._last_hit_logical_index = hit_logical_index
        
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
                
            
        
        self._SelectionChanged()
        
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
                
            
        
    
    def _InitialiseAsyncTextInfoUpdaterWorkCallables( self ):
        
        def pre_work_callable():
            
            return ( self._async_text_info_lock, self._currently_fetching_async_text_info_terms, self._pending_async_text_info_terms )
            
        
        def work_callable( args ):
            
            ( async_lock, currently_fetching, pending ) = args
            
            with async_lock:
                
                to_lookup = set( pending )
                
                pending.clear()
                
                currently_fetching.update( to_lookup )
                
            
            terms_to_info = { term : None for term in to_lookup }
            
            return terms_to_info
            
        
        return ( pre_work_callable, work_callable )
        
    
    def _InitialiseAsyncTextInfoUpdater( self ):
        
        def loading_callable():
            
            pass


        ( pre_work_callable, work_callable ) = self._InitialiseAsyncTextInfoUpdaterWorkCallables()
        
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
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
        
    
    def _LogicalIndexIsSelected( self, logical_index ):
        
        try:
            
            term = self._GetTermFromLogicalIndex( logical_index )
            
        except HydrusExceptions.DataMissing:
            
            return False
            
        
        return term in self._selected_terms
        
    
    def _ProcessMenuCopyEvent( self, command, include_parents = False, collapse_ors = False ):
        
        texts = self._GetCopyableTagStrings( command, include_parents = include_parents, collapse_ors = collapse_ors )
        
        if len( texts ) > 0:
            
            text = '\n'.join( texts )
            
            CG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _Redraw( self, painter ):
        
        bg_colour = self._GetBackgroundColour()
        
        if self._draw_background:
            
            painter.setBackground( QG.QBrush( bg_colour ) )
            
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
            
        
        fades_can_ever_happen = QtInit.WE_ARE_QT6 and CG.client_controller.new_options.GetBoolean( 'fade_sibling_connector' )
        
        current_visible_index = first_visible_positional_index
        
        for logical_index in range( first_visible_logical_index, last_visible_logical_index + 1 ):
            
            term = self._GetTermFromLogicalIndex( logical_index )
            
            rows_of_texts_and_colours = self._GetRowsOfTextsAndColours( term )
            
            term_ok_with_fade = term.CanFadeColours()
            
            for texts_and_colours in rows_of_texts_and_colours:
                
                x_start = self.TEXT_X_PADDING
                y_top = current_visible_index * text_height
                
                last_used_namespace_colour = None
                
                for ( text, ( r, g, b ) ) in texts_and_colours:
                    
                    ( this_text_size, text ) = ClientGUIFunctions.GetTextSizeFromPainter( painter, text )
                    
                    this_text_width = this_text_size.width()
                    this_text_height = this_text_size.height()
                    
                    background_block_width = this_text_width + self.TEXT_X_PADDING
                    
                    if x_start == self.TEXT_X_PADDING:
                        
                        background_colour_x = 0
                        
                    else:
                        
                        background_colour_x = x_start
                        
                    
                    namespace_colour = QG.QColor( r, g, b )
                    
                    text_colour = namespace_colour
                    
                    do_a_fade = fades_can_ever_happen and term_ok_with_fade and last_used_namespace_colour is not None and last_used_namespace_colour != namespace_colour
                    
                    if term in self._selected_terms:
                        
                        if do_a_fade:
                            
                            # this seems like a pain to set up, but I guess the correct way to do it is draw one rect in one go, since the lineargradient will draw beyond the fade fine
                            gradient_brush = QG.QLinearGradient( background_colour_x, 0.0, background_colour_x + background_block_width, 0.0 )
                            gradient_brush.setColorAt( 0.0, last_used_namespace_colour )
                            gradient_brush.setColorAt( 1.0, namespace_colour )
                            
                            rect_drawing_fill = gradient_brush
                            
                            rect_width = background_block_width
                            
                        else:
                            
                            rect_drawing_fill = namespace_colour
                            
                            rect_width = visible_rect_width - background_colour_x
                            
                        
                        try:
                            
                            painter.fillRect( background_colour_x, y_top, rect_width, text_height, rect_drawing_fill )
                            
                        except:
                            
                            painter.fillRect( background_colour_x, y_top, rect_width, text_height, namespace_colour )
                            
                        
                        pen_colour = self._GetBackgroundColour()
                        
                        text_pen = QG.QPen( pen_colour )
                        
                    else:
                        
                        if do_a_fade:
                            
                            gradient_brush = QG.QLinearGradient( x_start, 0.0, x_start + this_text_width, 0.0 )
                            gradient_brush.setColorAt( 0.0, last_used_namespace_colour )
                            gradient_brush.setColorAt( 1.0, namespace_colour )
                            
                            text_pen = QG.QPen( gradient_brush, 1 )
                            
                        else:
                            
                            text_pen = QG.QPen( text_colour )
                            
                        
                    
                    painter.setPen( text_pen )
                    
                    painter.drawText( QC.QRectF( x_start, y_top, this_text_width, this_text_height ), text )
                    
                    x_start += background_block_width
                    
                    last_used_namespace_colour = namespace_colour
                    
                
                current_visible_index += 1
                
            
        
    
    def _RegenTermsToIndices( self ):
        
        # TODO: although it is a pain in the neck, it would be best if this just cleared and set a flag for deferred regen
        # we'll have to go through all references to these variables though and ensure it is all wrapped in 'if dirty, regen' stuff
        # it mite b cool to also develop 'swap' tech for sort-swapping stuff, which will not change the total rows or indices outside of the range between the two swappers
        
        self._terms_to_logical_indices = {}
        self._terms_to_positional_indices = {}
        self._positional_indices_to_terms = {}
        self._total_positional_rows = 0
        
        for ( logical_index, term ) in enumerate( self._ordered_terms ):
            
            self._terms_to_logical_indices[ term ] = logical_index
            self._terms_to_positional_indices[ term ] = self._total_positional_rows
            self._positional_indices_to_terms[ self._total_positional_rows ] = term
            
            show_parent_rows = self._show_parent_decorators and self._extra_parent_rows_allowed
            
            self._total_positional_rows += term.GetRowCount( show_parent_rows )
            
        
    
    def _RemoveSelectedTerms( self ):
        
        self._RemoveTerms( list( self._selected_terms ) )
        
    
    def _RemoveTerms( self, terms ):
        
        removable_terms = { term for term in terms if term in self._terms_to_logical_indices }
        
        if len( removable_terms ) == 0:
            
            return
            
        
        if len( removable_terms ) > len( self._ordered_terms ) ** 0.5:
            
            self._ordered_terms = [ term for term in self._ordered_terms if term not in removable_terms ]
            
        else:
            
            for term in removable_terms:
                
                self._ordered_terms.remove( term )
                
            
        
        self._selected_terms.difference_update( removable_terms )
        
        self._RegenTermsToIndices()
        
        self._last_hit_logical_index = None
        self._shift_click_start_logical_index = None
        self._logical_indices_selected_this_shift_click = set()
        self._logical_indices_deselected_this_shift_click = set()
        self._in_drag = False
        self._this_drag_is_a_deselection = False
        
    
    def _Select( self, index ):
        
        try:
            
            term = self._GetTermFromLogicalIndex( index )
            
            self._selected_terms.add( term )
            
        except HydrusExceptions.DataMissing:
            
            pass
            
        
    
    def _SelectAll( self ):
        
        self._selected_terms = set( self._terms_to_logical_indices.keys() )
        
        self.widget().update()
        
    
    def _SelectionChanged( self ):
        
        pass
        
    
    def _SetVirtualSize( self ):
        
        # this triggers an update of the scrollbars, maybe important if this is the first time the thing is shown, let's see if it helps our missing scrollbar issue
        # I think this is needed here for PySide2 and a/c dropdowns, help
        self.setWidgetResizable( True )
        
        my_size = self.widget().size()
        
        text_height = self.fontMetrics().height()
        
        ideal_virtual_size = QC.QSize( my_size.width(), text_height * self._total_positional_rows )
        
        if HG.gui_report_mode:
            
            HydrusData.ShowText( f'Setting a virtual size on {self}. Num terms: {len( self._ordered_terms)}, Text height: {text_height}, Total Positional Rows: {self._total_positional_rows}, My Height: {my_size.height()}, Ideal Height: {ideal_virtual_size.height()}' )
            
        
        if ideal_virtual_size != my_size:
            
            self.widget().setMinimumSize( ideal_virtual_size )
            
            # this triggers an update of the scrollbars, maybe important if this is the first time the thing is shown, let's see if it helps our missing scrollbar issue
            self.setWidgetResizable( True )
            
        
    
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
        
        if not self.isEnabled():
            
            return
            
        
        shift = event.modifiers() & QC.Qt.KeyboardModifier.ShiftModifier
        ctrl = event.modifiers() & QC.Qt.KeyboardModifier.ControlModifier
        
        key_code = event.key()
        
        has_focus = self.hasFocus()
        
        if has_focus and key_code in ClientGUIShortcuts.DELETE_KEYS_QT:
            
            self._DeleteActivate()
            
        elif has_focus and key_code == QC.Qt.Key.Key_Escape:
            
            if len( self._selected_terms ) > 0:
                
                self._DeselectAll()
                
            else:
                
                event.ignore()
                
            
        elif key_code in ( QC.Qt.Key.Key_Enter, QC.Qt.Key.Key_Return ):
            
            self._ActivateFromKeyboard( ctrl, shift )
            
        else:
            
            if ctrl and key_code in ( ord( 'A' ), ord( 'a' ) ):
                
                self._SelectAll()
                
            elif ClientGUIShortcuts.KeyPressEventIsACopy( event ):
                
                if len( self._selected_terms ) > 0:
                    
                    command = COPY_SELECTED_TAGS
                    
                else:
                    
                    command = COPY_ALL_TAGS
                    
                
                include_parents = shift
                
                self._ProcessMenuCopyEvent( command, include_parents = include_parents )
                
            else:
                
                hit_logical_index = None
                
                if len( self._ordered_terms ) > 1:
                    
                    if key_code in ( QC.Qt.Key.Key_Home, ):
                        
                        hit_logical_index = 0
                        
                    elif key_code in ( QC.Qt.Key.Key_End, ):
                        
                        hit_logical_index = len( self._ordered_terms ) - 1
                        
                    elif self._last_hit_logical_index is not None:
                        
                        if ctrl and key_code in ( ord( 'P' ), ord( 'p' ) ):
                            
                            # remove ctrl key to make it act exactly like the up arrow
                            ctrl = False
                            
                            hit_logical_index = ( self._last_hit_logical_index - 1 ) % len( self._ordered_terms )
                            
                        elif ctrl and key_code in ( ord( 'N' ), ord( 'n' ) ):
                            
                            # remove ctrl key to make it act exactly like the down arrow
                            ctrl = False
                            
                            hit_logical_index = ( self._last_hit_logical_index + 1 ) % len( self._ordered_terms )
                            
                        elif key_code in ( QC.Qt.Key.Key_Up, ):
                            
                            hit_logical_index = ( self._last_hit_logical_index - 1 ) % len( self._ordered_terms )
                            
                        elif key_code in ( QC.Qt.Key.Key_Down, ):
                            
                            hit_logical_index = ( self._last_hit_logical_index + 1 ) % len( self._ordered_terms )
                            
                        elif key_code in ( QC.Qt.Key.Key_PageUp, QC.Qt.Key.Key_PageDown ):
                            
                            last_hit_positional_index = self._GetPositionalIndexFromLogicalIndex( self._last_hit_logical_index )
                            
                            if key_code == QC.Qt.Key.Key_PageUp:
                                
                                hit_positional_index = max( 0, last_hit_positional_index - self._num_rows_per_page )
                                
                            else:
                                
                                hit_positional_index = min( self._total_positional_rows - 1, last_hit_positional_index + self._num_rows_per_page )
                                
                            
                            ( hit_logical_index, hit_positional_index ) = self._GetLogicalIndicesFromPositionalIndex( hit_positional_index )
                            
                        
                    
                
                if hit_logical_index is None:
                    
                    event.ignore()
                    
                else:
                    
                    self._Hit( shift, ctrl, hit_logical_index )
                    
                
            
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            # we do the event filter since we need to 'scroll' the click, so we capture the event on the widget, not ourselves
            
            if watched == self.widget() and self.isEnabled():
                
                if event.type() == QC.QEvent.Type.MouseButtonPress:
                    
                    self._HandleClick( event )
                    
                    event.accept()
                    
                    return True
                    
                elif event.type() == QC.QEvent.Type.MouseButtonRelease:
                    
                    self._in_drag = False
                    
                    event.ignore()
                    
                elif event.type() == QC.QEvent.Type.MouseButtonDblClick:
                    
                    if event.button() == QC.Qt.MouseButton.LeftButton:
                        
                        ctrl_down = event.modifiers() & QC.Qt.KeyboardModifier.ControlModifier
                        shift_down = event.modifiers() & QC.Qt.KeyboardModifier.ShiftModifier
                        
                        if ctrl_down:
                            
                            logical_index = self._GetLogicalIndexUnderMouse( event )
                            
                            if not self._LogicalIndexIsSelected( logical_index ):
                                
                                # ok we will assume that the user just deselected with the first ctrl-click, and to fudge the awkward moment, we will sneakily re-select it
                                
                                self._Hit( False, True, logical_index )
                                
                            
                        
                        action_occurred = self._Activate( ctrl_down, shift_down )
                        
                        if action_occurred:
                            
                            self.mouseActivationOccurred.emit()
                            
                        
                    else:
                        
                        QW.QScrollArea.mouseDoubleClickEvent( self, event )
                        
                    
                    event.accept()
                    
                    return True
                    
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
    def mouseMoveEvent( self, event ):
        
        is_dragging = event.buttons() & QC.Qt.MouseButton.LeftButton
        
        if is_dragging:
            
            positional_index = self._GetPositionalIndexUnderMouse( event )
            
            # this causes lelmode as we cycle a 'None' hit position to the end of the list on a drag up
            # therefore, just clip to 0
            if positional_index < 0:
                
                logical_index = 0
                
            else:
                
                logical_index = self._GetLogicalIndexUnderMouse( event )
                
            
            if not self._in_drag:
                
                self._in_drag = True
                
                if self._last_hit_logical_index is None:
                    
                    self._this_drag_is_a_deselection = False
                    
                else:
                    
                    self._this_drag_is_a_deselection = not self._LogicalIndexIsSelected( self._last_hit_logical_index )
                    
                
            
            ctrl = self._this_drag_is_a_deselection
            
            self._Hit( True, ctrl, logical_index )
            
        else:
            
            event.ignore()
            
        
    
    class _InnerWidget( QW.QWidget ):
        
        def __init__( self, parent: "ListBox" ):
            
            super().__init__( parent )
            
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
        
    
    def GetNumTerms( self ):
        
        return len( self._ordered_terms )
        
    
    def HasValues( self ):
        
        return len( self._ordered_terms ) > 0
        
    
    def minimumSizeHint( self ):
        
        size_hint = QW.QScrollArea.minimumSizeHint( self )
        
        text_height = self.fontMetrics().height()
        
        minimum_height = self._minimum_height_num_chars * text_height + ( self.frameWidth() * 2 )
        
        size_hint.setHeight( minimum_height )
        
        return size_hint
        
    
    def MoveSelectionDown( self ):
        
        if not self.isEnabled():
            
            return
            
        
        if len( self._ordered_terms ) > 1 and self._last_hit_logical_index is not None:
            
            logical_index = ( self._last_hit_logical_index + 1 ) % len( self._ordered_terms )
            
            self._Hit( False, False, logical_index )
            
        
    
    def MoveSelectionUp( self ):
        
        if not self.isEnabled():
            
            return
            
        
        if len( self._ordered_terms ) > 1 and self._last_hit_logical_index is not None:
            
            logical_index = ( self._last_hit_logical_index - 1 ) % len( self._ordered_terms )
            
            self._Hit( False, False, logical_index )
            
        
    
    def SelectTopItem( self ):
        
        if not self.isEnabled():
            
            return
            
        
        if len( self._ordered_terms ) > 0:
            
            if len( self._selected_terms ) == 1 and self._LogicalIndexIsSelected( 0 ):
                
                return
                
            
            self._DeselectAll()
            
            self._Hit( False, False, 0 )
            
            self.widget().update()
            
        
    
    def setEnabled( self, value ):
        
        if not value:
            
            self._DeselectAll()
            
        
        super().setEnabled( value )
        
    
    def SetExtraParentRowsAllowed( self, value: bool ):
        
        if self._terms_may_have_sibling_or_parent_info and self._extra_parent_rows_allowed != value:
            
            self._extra_parent_rows_allowed = value
            
            self._RegenTermsToIndices()
            
            self._SetVirtualSize()
            
            self.widget().update()
            
        
    
    def SetMaximumHeightNumChars( self, maximum_height_num_chars ):
        
        self._maximum_height_num_chars = maximum_height_num_chars
        
    
    def SetMinimumHeightNumChars( self, minimum_height_num_chars ):
        
        self._minimum_height_num_chars = minimum_height_num_chars
        
    
    def SetParentDecoratorsAllowed( self, value: bool ):
        
        if self._terms_may_have_sibling_or_parent_info and self._show_parent_decorators != value:
            
            self._show_parent_decorators = value
            
            # i.e. if we just hid/showed parent sub-rows
            if self._extra_parent_rows_allowed:
                
                self._RegenTermsToIndices()
                
                self._SetVirtualSize()
                
            
            self.widget().update()
            
        
    
    def SetSiblingDecoratorsAllowed( self, value: bool ):
        
        if self._terms_may_have_sibling_or_parent_info and self._show_sibling_decorators != value:
            
            self._show_sibling_decorators = value
            
            self.widget().update()
            
        
    
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
    
    tagsSelected = QC.Signal( set )
    can_spawn_new_windows = True
    
    def __init__( self, parent, *args, tag_display_type: int = ClientTags.TAG_DISPLAY_STORAGE, **kwargs ):
        
        self._tag_display_type = tag_display_type
        
        self._qss_colours = {
            CC.COLOUR_TAGS_BOX : QG.QColor( 255, 255, 255 ),
        }
        
        terms_may_have_sibling_or_parent_info = self._tag_display_type == ClientTags.TAG_DISPLAY_STORAGE
        
        super().__init__( parent, terms_may_have_sibling_or_parent_info, *args, **kwargs )
        
        self.setObjectName( 'HydrusTagList' )
        
        if terms_may_have_sibling_or_parent_info:
            
            self._show_parent_decorators = CG.client_controller.new_options.GetBoolean( 'show_parent_decorators_on_storage_taglists' )
            self._show_sibling_decorators = CG.client_controller.new_options.GetBoolean( 'show_sibling_decorators_on_storage_taglists' )
            
            self._extra_parent_rows_allowed = CG.client_controller.new_options.GetBoolean( 'expand_parents_on_storage_taglists' )
            
        
        self._render_for_user = not self._tag_display_type == ClientTags.TAG_DISPLAY_STORAGE
        
        self._page_key = None # placeholder. if a subclass sets this, it changes menu behaviour to allow 'select this tag' menu pubsubs
        
        self._sibling_connector_string = CG.client_controller.new_options.GetString( 'sibling_connector' )
        self._sibling_connector_namespace = None
        
        if not CG.client_controller.new_options.GetBoolean( 'fade_sibling_connector' ):
            
            self._sibling_connector_namespace = CG.client_controller.new_options.GetNoneableString( 'sibling_connector_custom_namespace_colour' )
            
        
        self._UpdateBackgroundColour()
        
        CG.client_controller.sub( self, 'ForceTagRecalc', 'refresh_all_tag_presentation_gui' )
        CG.client_controller.sub( self, '_UpdateBackgroundColour', 'notify_new_colourset' )
        CG.client_controller.sub( self, 'NotifyNewOptions', 'notify_new_options' )
        
    
    def _GetCurrentLocationContext( self ):
        
        return ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
        
    
    def _GetCurrentPagePredicates( self ) -> typing.Set[ ClientSearchPredicate.Predicate ]:
        
        return set()
        
    
    def _GetNamespaceColours( self ):
        
        return HC.options[ 'namespace_colours' ]
        
    
    def _CanProvideCurrentPagePredicates( self ):
        
        return False
        
    
    def _GetBackgroundColour( self ):
        
        new_options = CG.client_controller.new_options
        
        if new_options.GetBoolean( 'override_stylesheet_colours' ):
            
            return new_options.GetColour( CC.COLOUR_TAGS_BOX )
            
        else:
            
            return self._qss_colours.get( CC.COLOUR_TAGS_BOX, QG.QColor( 127, 127, 127 ) )
            
        
    
    def _GetRowsOfTextsAndColours( self, term: ClientGUIListBoxesData.ListBoxItem ):
        
        namespace_colours = self._GetNamespaceColours()
        
        show_parent_rows = self._show_parent_decorators and self._extra_parent_rows_allowed
        
        rows_of_texts_and_namespaces = term.GetRowsOfPresentationTextsWithNamespaces( self._render_for_user, self._show_sibling_decorators, self._sibling_connector_string, self._sibling_connector_namespace, self._show_parent_decorators, show_parent_rows )
        
        rows_of_texts_and_colours = []
        
        for texts_and_namespaces in rows_of_texts_and_namespaces:
            
            texts_and_colours = []
            
            for ( text, colour_type, namespace ) in texts_and_namespaces:
                
                if namespace in namespace_colours:
                    
                    rgb = namespace_colours[ namespace ]
                    
                else:
                    
                    rgb = namespace_colours[ None ]
                    
                
                texts_and_colours.append( ( text, rgb ) )
                
            
            rows_of_texts_and_colours.append( texts_and_colours )
            
        
        return rows_of_texts_and_colours
        
    
    def _HasCounts( self ):
        
        return False
        
    
    def _NewDuplicateFilterPage( self, predicates ):
        
        activate_window = CG.client_controller.new_options.GetBoolean( 'activate_window_on_tag_search_page_activation' )
        
        predicates = ClientGUISearch.FleshOutPredicates( self, predicates )
        
        if len( predicates ) == 0:
            
            return
            
        
        s = sorted( ( predicate.ToString() for predicate in predicates ) )
        
        page_name = 'duplicates: ' + ', '.join( s )
        
        location_context = self._GetCurrentLocationContext()
        
        CG.client_controller.pub( 'new_page_duplicates', location_context, initial_predicates = predicates, page_name = page_name, activate_window = activate_window )
        
    
    def _NewSearchPages( self, pages_of_predicates ):
        
        activate_window = CG.client_controller.new_options.GetBoolean( 'activate_window_on_tag_search_page_activation' )
        
        for predicates in pages_of_predicates:
            
            predicates = ClientGUISearch.FleshOutPredicates( self, predicates )
            
            if len( predicates ) == 0:
                
                break
                
            
            s = sorted( ( predicate.ToString() for predicate in predicates ) )
            
            page_name = ', '.join( s )
            
            location_context = self._GetCurrentLocationContext()
            
            CG.client_controller.pub( 'new_page_query', location_context, initial_predicates = predicates, page_name = page_name, activate_window = activate_window )
            
            activate_window = False
            
        
    
    def _ProcessMenuPredicateEvent( self, command ):
        
        pass
        
    
    def _ProcessMenuTagEvent( self, command ):
        
        tags = self._GetTagsFromTerms( self._selected_terms )
        
        tags = [ tag for tag in tags if tag is not None ]
        
        if command in ( 'hide', 'hide_namespace' ):
            
            if command == 'hide':
                
                message = f'Hide{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( tags )}from here?'
                
                from hydrus.client.gui import ClientGUIDialogsQuick
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return
                    
                
                CG.client_controller.tag_display_manager.HideTags( self._tag_display_type, CC.COMBINED_TAG_SERVICE_KEY, tags )
                
            elif command == 'hide_namespace':
                
                namespaces = { namespace for ( namespace, subtag ) in ( HydrusTags.SplitTag( tag ) for tag in tags ) }
                nice_namespaces = [ ClientTags.RenderNamespaceForUser( namespace ) for namespace in namespaces ]
                
                message = f'Hide{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( nice_namespaces )}tags from here?'
                
                from hydrus.client.gui import ClientGUIDialogsQuick
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return
                    
                
                tag_slices = [ namespace if namespace == '' else namespace + ':' for namespace in namespaces ]
                
                CG.client_controller.tag_display_manager.HideTags( self._tag_display_type, CC.COMBINED_TAG_SERVICE_KEY, tag_slices )
                
            
            CG.client_controller.pub( 'notify_new_tag_display_rules' )
            
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
        
    
    def _SelectionChanged( self ):
        
        tags = set( self._GetTagsFromTerms( self._selected_terms ) )
        
        self.tagsSelected.emit( tags )
        
    
    def _UpdateBackgroundColour( self ):
        
        self.widget().update()
        
    
    def AddAdditionalMenuItems( self, menu: QW.QMenu ):
        
        pass
        
    
    def contextMenuEvent( self, event ):
        
        if event.reason() == QG.QContextMenuEvent.Reason.Keyboard:
            
            self.ShowMenu()
            
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            # we do the event filter since we need to 'scroll' the click, so we capture the event on the widget, not ourselves
            
            if watched == self.widget():
                
                if event.type() == QC.QEvent.Type.MouseButtonPress:
                    
                    if event.button() == QC.Qt.MouseButton.MiddleButton:
                        
                        self._HandleClick( event )
                        
                        if self.can_spawn_new_windows:
                            
                            (predicates, or_predicate, inverse_predicates, namespace_predicate, inverse_namespace_predicate) = self._GetSelectedPredicatesAndInverseCopies()
                            
                            if len( predicates ) > 0:
                                
                                shift_down = event.modifiers() & QC.Qt.KeyboardModifier.ShiftModifier
                                
                                if shift_down and or_predicate is not None:
                                    
                                    predicates = ( or_predicate, )
                                    
                                self._NewSearchPages( [ predicates ] )
                                
                            
                        
                        event.accept()
                        
                        return True
                        
                    
                elif event.type() == QC.QEvent.Type.MouseButtonRelease:
                    
                    if event.button() == QC.Qt.MouseButton.RightButton:
                        
                        self.ShowMenu()
                        
                        event.accept()
                        
                        return True
                        
                    
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return ListBox.eventFilter( self, watched, event )
        
    
    def NotifyNewOptions( self ):
        
        new_sibling_connector_string = CG.client_controller.new_options.GetString( 'sibling_connector' )
        new_sibling_connector_namespace = None
        
        if not CG.client_controller.new_options.GetBoolean( 'fade_sibling_connector' ):
            
            new_sibling_connector_namespace = CG.client_controller.new_options.GetNoneableString( 'sibling_connector_custom_namespace_colour' )
            
        
        if new_sibling_connector_string != self._sibling_connector_string or new_sibling_connector_namespace != self._sibling_connector_namespace:
            
            self._sibling_connector_string = new_sibling_connector_string
            self._sibling_connector_namespace = new_sibling_connector_namespace
            
            self.widget().update()
            
        
    
    def ShowMenu( self ):
        
        if len( self._ordered_terms ) == 0 or not self.isEnabled():
            
            return
            
        
        selected_actual_tags = self._GetTagsFromTerms( self._selected_terms )
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        if self._terms_may_have_sibling_or_parent_info:
            
            if self._show_parent_decorators:
                
                if self._extra_parent_rows_allowed:
                    
                    if len( self._ordered_terms ) != self._total_positional_rows:
                        
                        ClientGUIMenus.AppendMenuItem( menu, 'collapse parent rows', 'Show/hide parents.', self.SetExtraParentRowsAllowed, not self._extra_parent_rows_allowed )
                        
                    
                else:
                    
                    ClientGUIMenus.AppendMenuItem( menu, 'expand parent rows', 'Show/hide parents.', self.SetExtraParentRowsAllowed, not self._extra_parent_rows_allowed )
                    
                
                ClientGUIMenus.AppendMenuItem( menu, 'hide parent decorators', 'Show/hide parent info.', self.SetParentDecoratorsAllowed, not self._show_parent_decorators )
                
            else:
                
                ClientGUIMenus.AppendMenuItem( menu, 'show parent decorators', 'Show/hide parent info.', self.SetParentDecoratorsAllowed, not self._show_parent_decorators )
                
            
            if self._show_sibling_decorators:
                
                ClientGUIMenus.AppendMenuItem( menu, 'hide sibling decorators', 'Show/hide sibling info.', self.SetSiblingDecoratorsAllowed, not self._show_sibling_decorators )
                
            else:
                
                ClientGUIMenus.AppendMenuItem( menu, 'show sibling decorators', 'Show/hide sibling info.', self.SetSiblingDecoratorsAllowed, not self._show_sibling_decorators )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        copy_menu = ClientGUIMenus.GenerateMenu( menu )
        
        selected_copyable_tag_strings = self._GetCopyableTagStrings( COPY_SELECTED_TAGS )
        selected_copyable_subtag_strings = self._GetCopyableTagStrings( COPY_SELECTED_SUBTAGS )
        
        selected_copyable_tag_strings_with_parents = self._GetCopyableTagStrings( COPY_SELECTED_TAGS, include_parents = True )
        selected_copyable_tag_strings_with_collapsed_ors = self._GetCopyableTagStrings( COPY_SELECTED_TAGS, collapse_ors = True )
        
        if len( selected_copyable_tag_strings ) > 0:
            
            if len( selected_copyable_tag_strings ) == 1:
                
                ( selection_string, ) = selected_copyable_tag_strings
                
            else:
                
                selection_string = '{} selected'.format( HydrusNumbers.ToHumanInt( len( selected_copyable_tag_strings ) ) )
                
            
            ClientGUIMenus.AppendMenuItem( copy_menu, selection_string, 'Copy the selected tags to your clipboard.', self._ProcessMenuCopyEvent, COPY_SELECTED_TAGS )
            
            sub_selection_string = None
            
            if len( selected_copyable_subtag_strings ) > 0:
                
                if len( selected_copyable_subtag_strings ) == 1:
                    
                    # this does a quick test for 'are we selecting a namespaced tags' that also allows for having both 'samus aran' and 'character:samus aran'
                    if set( selected_copyable_subtag_strings ) != set( selected_copyable_tag_strings ):
                        
                        ( sub_selection_string, ) = selected_copyable_subtag_strings
                        
                        ClientGUIMenus.AppendMenuItem( copy_menu, sub_selection_string, 'Copy the selected subtag to your clipboard.', self._ProcessMenuCopyEvent, COPY_SELECTED_SUBTAGS )
                        
                    
                else:
                    
                    sub_selection_string = '{} selected subtags'.format( HydrusNumbers.ToHumanInt( len( selected_copyable_subtag_strings ) ) )
                    
                    ClientGUIMenus.AppendMenuItem( copy_menu, sub_selection_string, 'Copy the selected subtags to your clipboard.', self._ProcessMenuCopyEvent, COPY_SELECTED_SUBTAGS )
                    
                
            
            if self._HasCounts():
                
                ClientGUIMenus.AppendSeparator( copy_menu )
                
                ClientGUIMenus.AppendMenuItem( copy_menu, '{} with counts'.format( selection_string ), 'Copy the selected tags, with their counts, to your clipboard.', self._ProcessMenuCopyEvent, COPY_SELECTED_TAGS_WITH_COUNTS )
                
                if sub_selection_string is not None:
                    
                    ClientGUIMenus.AppendMenuItem( copy_menu, '{} with counts'.format( sub_selection_string ), 'Copy the selected subtags, with their counts, to your clipboard.', self._ProcessMenuCopyEvent, COPY_SELECTED_SUBTAGS_WITH_COUNTS )
                    
                
            
            collapsed_ors_occurred = len( selected_copyable_tag_strings_with_collapsed_ors ) < len( selected_copyable_tag_strings )
            
            if collapsed_ors_occurred:
                
                ClientGUIMenus.AppendSeparator( copy_menu )
                
                if len( selected_copyable_tag_strings ) == 1:
                    
                    ( selection_string, ) = selected_copyable_tag_strings_with_collapsed_ors
                    
                else:
                    
                    selection_string = '{} selected, with OR predicates collapsed'.format( HydrusNumbers.ToHumanInt( len( selected_copyable_tag_strings_with_collapsed_ors ) ) )
                    
                
                ClientGUIMenus.AppendMenuItem( copy_menu, selection_string, 'Copy the selected tags to your clipboard, with OR predicates collapsed.', self._ProcessMenuCopyEvent, COPY_SELECTED_TAGS, collapse_ors = True )
                
            
            num_parents = len( selected_copyable_tag_strings_with_parents ) - len( selected_copyable_tag_strings )
            
            if num_parents > 0:
                
                ClientGUIMenus.AppendSeparator( copy_menu )
                
                if len( selected_copyable_tag_strings ) == 1:
                    
                    ( selection_string, ) = selected_copyable_tag_strings
                    
                else:
                    
                    selection_string = '{} selected'.format( HydrusNumbers.ToHumanInt( len( selected_copyable_tag_strings ) ) )
                    
                
                selection_string += f' and {HydrusNumbers.ToHumanInt( num_parents )} parents'
                
                ClientGUIMenus.AppendMenuItem( copy_menu, selection_string, 'Copy the selected tags and their (deduplicated) parents to your clipboard.', self._ProcessMenuCopyEvent, COPY_SELECTED_TAGS, include_parents = True )
                
            
        
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
            
            siblings_menu = ClientGUIMenus.GenerateMenu( menu )
            parents_menu = ClientGUIMenus.GenerateMenu( menu )
            
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
                    
                    selected_tag_to_service_keys_to_siblings_and_parents = CG.client_controller.Read( 'tag_siblings_and_parents_lookup', ClientTags.TAG_DISPLAY_DISPLAY_IDEAL, ( selected_tag, ) )
                    
                    service_keys_to_siblings_and_parents = selected_tag_to_service_keys_to_siblings_and_parents[ selected_tag ]
                    
                    return service_keys_to_siblings_and_parents
                    
                
                def sp_publish_callable( service_keys_to_siblings_and_parents ):
                    
                    service_keys_in_order = CG.client_controller.services_manager.GetServiceKeys( HC.REAL_TAG_SERVICES )
                    
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
                    
                    service_keys_to_service_names = { service_key : CG.client_controller.services_manager.GetName( service_key ) for service_key in service_keys_in_order }
                    
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
                        
                    
                    MAX_ITEMS_HERE = 10
                    
                    if num_siblings == 0:
                        
                        siblings_menu.setTitle( 'no siblings' )
                        
                    else:
                        
                        siblings_menu.setTitle( '{} siblings'.format( HydrusNumbers.ToHumanInt( num_siblings ) ) )
                        
                        #
                        
                        ClientGUIMenus.AppendSeparator( siblings_menu )
                        
                        ideals = sorted( ideals_to_service_keys.keys(), key = HydrusText.HumanTextSortKey )
                        
                        for ideal in ideals:
                            
                            if ideal == selected_tag:
                                
                                continue
                                
                            
                            ideal_label = 'ideal is "{}" on: {}'.format( ideal, convert_service_keys_to_name_string( ideals_to_service_keys[ ideal ] ) )
                            
                            ClientGUIMenus.AppendMenuItem( siblings_menu, ideal_label, ideal_label, CG.client_controller.pub, 'clipboard', 'text', ideal )
                            
                        
                        #
                        
                        for ( s_k_name, tags ) in group_and_sort_siblings_to_service_keys( siblings_to_service_keys ):
                            
                            ClientGUIMenus.AppendSeparator( siblings_menu )
                            
                            if s_k_name != ALL_SERVICES_LABEL:
                                
                                ClientGUIMenus.AppendMenuLabel( siblings_menu, '--{}--'.format( s_k_name ) )
                                
                            
                            ClientGUIMenus.SpamLabels( siblings_menu, [ ( tag, tag ) for tag in tags ], MAX_ITEMS_HERE )
                            
                        
                    
                    #
                    
                    if num_parents + num_children == 0:
                        
                        parents_menu.setTitle( 'no parents' )
                        
                    else:
                        
                        parents_menu.setTitle( '{} parents, {} children'.format( HydrusNumbers.ToHumanInt( num_parents ), HydrusNumbers.ToHumanInt( num_children ) ) )
                        
                        ClientGUIMenus.AppendSeparator( parents_menu )
                        
                        for ( s_k_name, ( parents, children ) ) in group_and_sort_parents_to_service_keys( parents_to_service_keys, children_to_service_keys ):
                            
                            ClientGUIMenus.AppendSeparator( parents_menu )
                            
                            if s_k_name != ALL_SERVICES_LABEL:
                                
                                ClientGUIMenus.AppendMenuLabel( parents_menu, '--{}--'.format( s_k_name ) )
                                
                            
                            ClientGUIMenus.SpamLabels( parents_menu, [ ( f'parent: {parent}', parent ) for parent in parents ], MAX_ITEMS_HERE )
                            
                            ClientGUIMenus.SpamLabels( parents_menu, [ ( f'child: {child}', child ) for child in children ], MAX_ITEMS_HERE )
                            
                        
                    
                
                async_job = ClientGUIAsync.AsyncQtJob( menu, sp_work_callable, sp_publish_callable )
                
                async_job.start()
                
            
        
        if len( self._selected_terms ) > 0:
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ( predicates, or_predicate, inverse_predicates, namespace_predicate, inverse_namespace_predicate ) = self._GetSelectedPredicatesAndInverseCopies()
            
            if len( predicates ) > 0:
                
                if self.can_spawn_new_windows or self._CanProvideCurrentPagePredicates():
                    
                    search_menu = ClientGUIMenus.GenerateMenu( menu )
                    
                    ClientGUIMenus.AppendMenu( menu, search_menu, 'search' )
                    
                    if self.can_spawn_new_windows:
                        
                        ClientGUIMenus.AppendMenuItem( search_menu, 'open a new search page for ' + selection_string, 'Open a new search page starting with the selected predicates.', self._NewSearchPages, [ predicates ] )
                        
                        if or_predicate is not None:
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, 'open a new OR search page for ' + selection_string, 'Open a new search page starting with the selected merged as an OR search predicate.', self._NewSearchPages, [ ( or_predicate, ) ] )
                            
                        
                        if len( predicates ) > 1:
                            
                            for_each_predicates = [ ( predicate, ) for predicate in predicates ]
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, 'open new search pages for each in selection', 'Open one new search page for each selected predicate.', self._NewSearchPages, for_each_predicates )
                            
                        
                        ClientGUIMenus.AppendSeparator( search_menu )
                        
                        ClientGUIMenus.AppendMenuItem( search_menu, f'open a new duplicate filter page for {selection_string}', 'Open a new duplicate filter page starting with the selected predicates.', self._NewDuplicateFilterPage, predicates )
                        
                        ClientGUIMenus.AppendSeparator( search_menu )
                        
                    
                    self._AddEditMenu( search_menu )
                    
                    ClientGUIMenus.AppendSeparator( search_menu )
                    
                    if self._CanProvideCurrentPagePredicates():
                        
                        current_predicates = self._GetCurrentPagePredicates()
                        
                        predicates = set( predicates )
                        inverse_predicates = set( inverse_predicates )
                        
                        if len( predicates ) == 1:
                            
                            ( p, ) = predicates
                            
                            predicates_selection_string = p.ToString( with_count = False )
                            
                        else:
                            
                            predicates_selection_string = 'selected'
                            
                        
                        some_selected_not_in_current = len( predicates.intersection( current_predicates ) ) < len( predicates )
                        
                        if some_selected_not_in_current:
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, 'add {} to current search'.format( predicates_selection_string ), 'Add the selected predicates to the current search.', self._ProcessMenuPredicateEvent, 'add_predicates' )
                            
                        
                        some_selected_in_current = HydrusLists.SetsIntersect( predicates, current_predicates )
                        
                        if some_selected_in_current:
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, 'remove {} from current search'.format( predicates_selection_string ), 'Remove the selected predicates from the current search.', self._ProcessMenuPredicateEvent, 'remove_predicates' )
                            
                        
                        we_can_flip_some_of_selection = len( inverse_predicates ) > 0
                        
                        if we_can_flip_some_of_selection:
                            
                            inclusives = { p.IsInclusive() for p in inverse_predicates }
                            
                            inverse_all_exclusive = True not in inclusives
                            inverse_all_inclusive = False not in inclusives
                            
                            if inverse_all_exclusive:
                                
                                text = 'exclude {} from the current search'.format( predicates_selection_string )
                                desc = 'Disallow the selected predicates for the current search.'
                                
                            elif inverse_all_inclusive and len( inverse_predicates ) == 1:
                                
                                ( p, ) = inverse_predicates
                                
                                inverse_selection_string = p.ToString( with_count = False )
                                
                                text = 'require {} for the current search'.format( inverse_selection_string )
                                desc = 'Stop disallowing the selected predicates from the current search.'
                                
                            else:
                                
                                text = 'invert selection for the current search'
                                desc = 'Flip the inclusive/exclusive nature of the selected predicates from the current search.'
                                
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, text, desc, self._ProcessMenuPredicateEvent, 'add_inverse_predicates' )
                            
                        
                        ClientGUIMenus.AppendSeparator( search_menu )
                        
                        if or_predicate is not None and or_predicate not in predicates:
                            
                            all_selected_in_current = predicates.issubset( current_predicates )
                            
                            if all_selected_in_current:
                                
                                ClientGUIMenus.AppendMenuItem( search_menu, f'replace {predicates_selection_string} with their OR', 'Remove the selected predicates and replace them with an OR predicate that searches for any of them.', self._ProcessMenuPredicateEvent, 'replace_or_predicate')
                                
                            else:
                                
                                ClientGUIMenus.AppendMenuItem( search_menu, 'add an OR of {} to current search'.format( predicates_selection_string ), 'Add the selected predicates as an OR predicate to the current search.', self._ProcessMenuPredicateEvent, 'add_or_predicate' )
                                
                            
                        
                        if True not in ( p.IsORPredicate() for p in predicates ):
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, f'start an OR predicate with {predicates_selection_string}', 'Start up the Edit OR Predicate panel starting with this.', self._ProcessMenuPredicateEvent, 'start_or_predicate' )
                            
                        
                        if False not in ( p.IsORPredicate() for p in predicates ):
                            
                            label = f'dissolve {predicates_selection_string} into single predicates'
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, label, 'Convert OR predicates to their constituent parts.', self._ProcessMenuPredicateEvent, 'dissolve_or_predicate' )
                            
                        
                        ClientGUIMenus.AppendSeparator( search_menu )
                        
                        if namespace_predicate is not None and namespace_predicate not in current_predicates:
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, 'add {} to current search'.format( namespace_predicate.ToString( with_count = False ) ), 'Add the namespace predicate to the current search.', self._ProcessMenuPredicateEvent, 'add_namespace_predicate' )
                            
                        
                        if inverse_namespace_predicate is not None and inverse_namespace_predicate not in current_predicates:
                            
                            ClientGUIMenus.AppendMenuItem( search_menu, 'exclude {} from the current search'.format( namespace_predicate.ToString( with_count = False ) ), 'Disallow the namespace predicate from the current search.', self._ProcessMenuPredicateEvent, 'add_inverse_namespace_predicate' )
                            
                        
                    
                
            
            if len( selected_actual_tags ) > 0 and self._page_key is not None:
                
                select_menu = ClientGUIMenus.GenerateMenu( menu )
                
                tags_sorted_to_show_on_menu = HydrusTags.SortNumericTags( selected_actual_tags )
                
                tags_sorted_to_show_on_menu_string = ', '.join( tags_sorted_to_show_on_menu )
                
                while len( tags_sorted_to_show_on_menu_string ) > 64:
                    
                    if len( tags_sorted_to_show_on_menu ) == 1:
                        
                        tags_sorted_to_show_on_menu_string = '(many/long tags)'
                        
                    else:
                        
                        tags_sorted_to_show_on_menu.pop( -1 )
                        
                        tags_sorted_to_show_on_menu_string = ', '.join( tags_sorted_to_show_on_menu + [ HC.UNICODE_ELLIPSIS ] )
                        
                    
                
                if len( selected_actual_tags ) == 1:
                    
                    label = 'files with "{}"'.format( tags_sorted_to_show_on_menu_string )
                    
                else:
                    
                    label = 'files with all of "{}"'.format( tags_sorted_to_show_on_menu_string )
                    
                
                ClientGUIMenus.AppendMenuItem( select_menu, label, 'Select the files with these tags.', self._SelectFilesWithTags, 'AND' )
                
                if len( selected_actual_tags ) > 1:
                    
                    label = 'files with any of "{}"'.format( tags_sorted_to_show_on_menu_string )
                    
                    ClientGUIMenus.AppendMenuItem( select_menu, label, 'Select the files with any of these tags.', self._SelectFilesWithTags, 'OR' )
                    
                
                ClientGUIMenus.AppendMenu( menu, select_menu, 'select' )
                
            
        
        if len( selected_actual_tags ) > 0:
            
            if self._tag_display_type in ( ClientTags.TAG_DISPLAY_SINGLE_MEDIA, ClientTags.TAG_DISPLAY_SELECTION_LIST ):
                
                ClientGUIMenus.AppendSeparator( menu )
                
                namespaces = set()
                
                for selected_actual_tag in selected_actual_tags:
                    
                    ( namespace, subtag ) = HydrusTags.SplitTag( selected_actual_tag )
                    
                    namespaces.add( namespace )
                    
                
                if len( namespaces ) == 1:
                    
                    namespace = list( namespaces )[0]
                    
                    namespace_label = f'"{ClientTags.RenderNamespaceForUser( namespace )}" tags from here'
                    
                else:
                    
                    namespace_label = f'{HydrusNumbers.ToHumanInt( len( namespaces ) )} selected namespaces from here'
                    
                
                if len( selected_actual_tags ) == 1:
                    
                    actual_tag = list( selected_actual_tags )[0]
                    
                    actual_tag_label = f'"{actual_tag}" from here'
                    
                else:
                    
                    actual_tag_label = f'{HydrusNumbers.ToHumanInt( len( selected_actual_tags ) )} selected tags from here'
                    
                
                hide_menu = ClientGUIMenus.GenerateMenu( menu )
                
                ClientGUIMenus.AppendMenuItem( hide_menu, namespace_label, 'Hide these namespaces from view in future.', self._ProcessMenuTagEvent, 'hide_namespace' )
                ClientGUIMenus.AppendMenuItem( hide_menu, actual_tag_label, 'Hide these tags from view in future.', self._ProcessMenuTagEvent, 'hide' )
                
                ClientGUIMenus.AppendMenu( menu, hide_menu, 'hide' )
                
            
        
        #
        
        def add_favourite_tags( tags ):
            
            if len( tags ) > 5:
                
                message = f'Add{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( tags )}to the favourites list?'
                
                from hydrus.client.gui import ClientGUIDialogsQuick
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.DialogCode.Accepted:
                    
                    return
                    
                
            
            favourite_tags = set( CG.client_controller.new_options.GetStringList( 'favourite_tags' ) )
            
            favourite_tags.update( tags )
            
            CG.client_controller.new_options.SetStringList( 'favourite_tags', list( favourite_tags ) )
            
            CG.client_controller.pub( 'notify_new_favourite_tags' )
            
        
        def remove_favourite_tags( tags ):
            
            message = f'Remove{HydrusText.ConvertManyStringsToNiceInsertableHumanSummary( tags )}from the favourites list?'
            
            from hydrus.client.gui import ClientGUIDialogsQuick
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
            favourite_tags = set( CG.client_controller.new_options.GetStringList( 'favourite_tags' ) )
            
            favourite_tags.difference_update( tags )
            
            CG.client_controller.new_options.SetStringList( 'favourite_tags', list( favourite_tags ) )
            
            CG.client_controller.pub( 'notify_new_favourite_tags' )
            
        
        favourite_tags = list( CG.client_controller.new_options.GetStringList( 'favourite_tags' ) )
        
        to_add = set( selected_actual_tags ).difference( favourite_tags )
        to_remove = set( selected_actual_tags ).intersection( favourite_tags )
        
        if len( to_add ) + len( to_remove ) > 0:
            
            favourites_menu = ClientGUIMenus.GenerateMenu( menu )
            
            if len( to_add ) > 0:
                
                if len( to_add ) == 1:
                    
                    tag = list( to_add )[0]
                    
                    label = f'Add "{tag}" to favourites'
                    
                else:
                    
                    label = f'Add {HydrusNumbers.ToHumanInt( len( to_add ) )} selected tags to favourites'
                    
                
                description = 'Add these tags to the favourites list.'
                
                ClientGUIMenus.AppendMenuItem( favourites_menu, label, description, add_favourite_tags, to_add )
                
            
            if len( to_remove ) > 0:
                
                if len( to_remove ) == 1:
                    
                    tag = list( to_remove )[0]
                    
                    label = f'Remove "{tag}" from favourites'
                    
                else:
                    
                    label = f'Remove {HydrusNumbers.ToHumanInt( len( to_remove ) )} selected tags from favourites'
                    
                
                description = 'Add these tags to the favourites list.'
                
                ClientGUIMenus.AppendMenuItem( favourites_menu, label, description, remove_favourite_tags, to_remove )
                
            
            ClientGUIMenus.AppendMenu( menu, favourites_menu, 'favourites' )
            
        
        #
        
        self.AddAdditionalMenuItems( menu )
        
        if len( selected_actual_tags ) > 0:
            
            def regen_tags():
                
                message = '!!WARNING EXPERIMENTAL!!'
                message += '\n' * 2
                message += 'This will delete and then regenerate all the display calculations for the selected tags and their siblings and parents, with the intention of fixing bad autocomplete counts or sibling/parent presentation. It is functionally similar to the \'tag storage mappings cache\' regeneration job, but just for these tags.'
                message += '\n' * 2
                message += 'It might take a while to run, perhaps many minutes for a heavily-siblinged/-parented/-mapped tag, during which the database will be locked. Doing it on a thousand tags is going to completely gonk you. Also, any sibling or parent rules will be reset, and they will have to be recalculated, which will probably occur in a few seconds in the background after the regeneration job completes.'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Regen tags?', yes_label = 'let\'s go', no_label = 'forget it' )
                
                if result == QW.QDialog.DialogCode.Accepted:
                    
                    CG.client_controller.Write( 'regenerate_tag_mappings_tags', selected_actual_tags )
                    
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            submenu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'regenerate tag display', 'Delete and regenerate the cached mappings for just these tags.', regen_tags )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'maintenance' )
            
            tag_repos: typing.Collection[ ClientServices.ServiceRepository ] = CG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) )
            
            we_are_admin = True in ( tag_repo.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_MODERATE ) for tag_repo in tag_repos )
            
            noun = 'tags'
            
            from hydrus.client.gui.services import ClientGUIModalClientsideServiceActions
            from hydrus.client.gui.services import ClientGUIModalServersideServiceActions
            
            if we_are_admin:
                
                ClientGUIMenus.AppendSeparator( menu )
                
                for tag_repo in tag_repos:
                    
                    if not tag_repo.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_MODERATE ):
                        
                        continue
                        
                    
                    service_key = tag_repo.GetServiceKey()
                    service_submenu = ClientGUIMenus.GenerateMenu( menu )
                    
                    if tag_repo.HasPermission( HC.CONTENT_TYPE_OPTIONS, HC.PERMISSION_ACTION_MODERATE ):
                        
                        try:
                            
                            tag_filter = tag_repo.GetTagFilter()
                            
                            tags_currently_ok = { tag for tag in selected_actual_tags if tag_filter.TagOK( tag ) }
                            tags_currently_not_ok = { tag for tag in selected_actual_tags if tag not in tags_currently_ok }
                            
                            if len( tags_currently_ok ) > 0:
                                
                                label = f'block {HydrusText.ConvertManyStringsToNiceInsertableHumanSummarySingleLine(tags_currently_ok,noun)}{HC.UNICODE_ELLIPSIS}'
                                
                                ClientGUIMenus.AppendMenuItem( service_submenu, label, 'Change the tag filter for this service.', ClientGUIModalServersideServiceActions.ManageServiceOptionsTagFilter, self, service_key, new_tags_to_block = tags_currently_ok )
                                
                            
                            if len( tags_currently_not_ok ) > 0:
                                
                                label = f're-allow {HydrusText.ConvertManyStringsToNiceInsertableHumanSummarySingleLine(tags_currently_not_ok,noun)}{HC.UNICODE_ELLIPSIS}'
                                
                                ClientGUIMenus.AppendMenuItem( service_submenu, label, 'Change the tag filter for this service.', ClientGUIModalServersideServiceActions.ManageServiceOptionsTagFilter, self, service_key, new_tags_to_allow = tags_currently_not_ok )
                                
                            
                        except:
                            
                            ClientGUIMenus.AppendMenuLabel( service_submenu, 'could not fetch service tag filter! maybe your account is unsynced?' )
                            
                        
                    
                    ClientGUIMenus.AppendSeparator( service_submenu )
                    
                    ClientGUIMenus.AppendMenuItem( service_submenu, f'delete all {HydrusText.ConvertManyStringsToNiceInsertableHumanSummarySingleLine(selected_actual_tags,noun)}{HC.UNICODE_ELLIPSIS}', 'Delete every instance of this tag from the repository.', ClientGUIModalClientsideServiceActions.OpenPurgeTagsWindow, self, service_key, selected_actual_tags )
                    
                    ClientGUIMenus.AppendMenu( menu, service_submenu, 'admin: ' + tag_repo.GetName() )
                    
                
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def ForceTagRecalc( self ):
        
        pass
        
    
    def get_htl_background( self ):
        
        return self._qss_colours[ CC.COLOUR_TAGS_BOX ]
        
    
    def set_htl_background( self, colour ):
        
        self._qss_colours[ CC.COLOUR_TAGS_BOX ] = colour
        
    
    htl_background = QC.Property( QG.QColor, get_htl_background, set_htl_background )
    
    def get_draw_background( self ):
        
        return self._draw_background
        
    
    def set_draw_background( self, draw_background ):
        
        self._draw_background = draw_background
        
    
    draw_background = QC.Property( bool, get_draw_background, set_draw_background )
    

class ListBoxTagsPredicates( ListBoxTags ):
    
    def __init__( self, *args, tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, **kwargs ):
        
        super().__init__( *args, tag_display_type = tag_display_type, **kwargs )
        
    
    def _GenerateTermFromPredicate( self, predicate: ClientSearchPredicate.Predicate ) -> ClientGUIListBoxesData.ListBoxItemPredicate:
        
        return ClientGUIListBoxesData.ListBoxItemPredicate( predicate )
        
    
    def _GetMutuallyExclusivePredicates( self, predicate ):
        
        all_predicates = self._GetPredicatesFromTerms( self._ordered_terms )
        
        m_e_predicates = { existing_predicate for existing_predicate in all_predicates if existing_predicate.IsMutuallyExclusive( predicate ) }
        
        return m_e_predicates
        
    
    def _HasCounts( self ):
        
        return True
        
    
    def GetPredicates( self ) -> typing.Set[ ClientSearchPredicate.Predicate ]:
        
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
        
        super().__init__( parent )
        
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
            
            if result == QW.QDialog.DialogCode.Accepted:
                
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
        
    
    def DeleteSelected( self ):
        
        self._DeleteActivate()
        
    
    def GetNamespaceColours( self ):
        
        return self._GetNamespaceColours()
        
    
    def GetSelectedNamespaceColours( self ):
        
        namespace_colours = dict( ( term.GetNamespaceAndColour() for term in self._selected_terms ) )
        
        return namespace_colours
        
    
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
        
    
class ListBoxTagsFilter( ListBoxTags ):
    
    tagsRemoved = QC.Signal( list )
    
    def __init__( self, parent, read_only = False ):
        
        super().__init__( parent )
        
        self._read_only = read_only
        
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        if len( self._selected_terms ) > 0 and not self._read_only:
            
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
    
    tagsChanged = QC.Signal( list )
    
    def __init__( self, parent, service_key = None, tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, **kwargs ):
        
        if service_key is None:
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        self._service_key = service_key
        
        has_async_text_info = tag_display_type == ClientTags.TAG_DISPLAY_STORAGE
        
        super().__init__( parent, has_async_text_info = has_async_text_info, tag_display_type = tag_display_type, **kwargs )
        
        self.listBoxChanged.connect( self._NotifyListBoxChanged )
        
    
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
        
    
    def _InitialiseAsyncTextInfoUpdaterWorkCallables( self ):
        
        if not self._has_async_text_info:
            
            return ListBoxTags._InitialiseAsyncTextInfoUpdaterWorkCallables( self )
            
        
        def pre_work_callable():
            
            return ( self._service_key, self._async_text_info_lock, self._currently_fetching_async_text_info_terms, self._pending_async_text_info_terms )
            
        
        def work_callable( args ):
            
            ( service_key, async_lock, currently_fetching, pending ) = args
            
            with async_lock:
                
                to_lookup = list( pending )
                
                pending.clear()
                
                currently_fetching.update( to_lookup )
                
            
            terms_to_info = { term : None for term in to_lookup }
            
            for batch_to_lookup in HydrusLists.SplitListIntoChunks( to_lookup, 500 ):
                
                tags_to_terms = { term.GetTag() : term for term in batch_to_lookup }
                
                tags_to_lookup = set( tags_to_terms.keys() )
                
                db_tags_to_ideals_and_parents = CG.client_controller.Read( 'tag_display_decorators', service_key, tags_to_lookup )
                
                terms_to_info.update( { tags_to_terms[ tag ] : info for ( tag, info ) in db_tags_to_ideals_and_parents.items() } )
                
            
            return terms_to_info
            
        
        return ( pre_work_callable, work_callable )
        
    
    def _NotifyListBoxChanged( self ):
        
        # we only want the top tags here, not all parents and so on
        tags = [ term.GetTag() for term in self._ordered_terms ]
        
        self.tagsChanged.emit( list( self._GetTagsFromTerms( self._ordered_terms ) ) )
        
    
    def _SelectFilesWithTags( self, and_or_or ):
        
        if self._page_key is not None:
            
            selected_actual_tags = self._GetTagsFromTerms( self._selected_terms )
            
            CG.client_controller.pub( 'select_files_with_tags', self._page_key, self._service_key, and_or_or, set( selected_actual_tags ) )
            
        
    
    def GetSelectedTags( self ):
        
        return set( self._GetTagsFromTerms( self._selected_terms ) )
        
    
    def SetTagServiceKey( self, service_key ):
        
        self._service_key = service_key
        
        with self._async_text_info_lock:
            
            self._pending_async_text_info_terms.clear()
            self._currently_fetching_async_text_info_terms.clear()
            self._terms_to_async_text_info = {}
            
        
    

class ListBoxTagsStrings( ListBoxTagsDisplayCapable ):
    
    tagsChanged = QC.Signal( list )
    
    def __init__( self, parent, service_key = None, sort_tags = True, **kwargs ):
        
        self._sort_tags = sort_tags
        
        super().__init__( parent, service_key = service_key, **kwargs )
        
        self.listBoxChanged.connect( self._NotifyListBoxChanged )
        
    
    def _GenerateTermFromTag( self, tag: str ) -> ClientGUIListBoxesData.ListBoxItemTextTag:
        
        return ClientGUIListBoxesData.ListBoxItemTextTag( tag )
        
    
    def _NotifyListBoxChanged( self ):
        
        self.tagsChanged.emit( list( self.GetTags() ) )
        
    
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
    
    def __init__( self, parent: QW.QWidget, tag_display_type: int, tag_presentation_location: int, service_key = None, include_counts = True ):
        
        if service_key is None:
            
            service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        super().__init__( parent, service_key = service_key, tag_display_type = tag_display_type, height_num_chars = 24 )
        
        self._tag_presentation_location = tag_presentation_location
        
        self._tag_sort = CG.client_controller.new_options.GetDefaultTagSort( self._tag_presentation_location )
        
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
            
            nonzero_tags = set()
            
            if self._show_current: nonzero_tags.update( ( tag for ( tag, count ) in self._current_tags_to_count.items() if count > 0 ) )
            if self._show_deleted: nonzero_tags.update( ( tag for ( tag, count ) in self._deleted_tags_to_count.items() if count > 0 ) )
            if self._show_pending: nonzero_tags.update( ( tag for ( tag, count ) in self._pending_tags_to_count.items() if count > 0 ) )
            if self._show_petitioned: nonzero_tags.update( ( tag for ( tag, count ) in self._petitioned_tags_to_count.items() if count > 0 ) )
            
            zero_tags = { tag for tag in ( term.GetTag() for term in self._ordered_terms ) if tag not in nonzero_tags }
            
        else:
            
            if len( limit_to_these_tags ) == 0:
                
                return
                
            
            if not isinstance( limit_to_these_tags, set ):
                
                limit_to_these_tags = set( limit_to_these_tags )
                
            
            nonzero_tags = set()
            
            if self._show_current: nonzero_tags.update( ( tag for ( tag, count ) in self._current_tags_to_count.items() if count > 0 and tag in limit_to_these_tags ) )
            if self._show_deleted: nonzero_tags.update( ( tag for ( tag, count ) in self._deleted_tags_to_count.items() if count > 0 and tag in limit_to_these_tags ) )
            if self._show_pending: nonzero_tags.update( ( tag for ( tag, count ) in self._pending_tags_to_count.items() if count > 0 and tag in limit_to_these_tags ) )
            if self._show_petitioned: nonzero_tags.update( ( tag for ( tag, count ) in self._petitioned_tags_to_count.items() if count > 0 and tag in limit_to_these_tags ) )
            
            zero_tags = { tag for tag in limit_to_these_tags if tag not in nonzero_tags }
            
        
        if len( zero_tags ) + len( nonzero_tags ) == 0:
            
            return
            
        
        removee_terms = [ self._GenerateTermFromTag( tag ) for tag in zero_tags ]
        
        nonzero_terms = [ self._GenerateTermFromTag( tag ) for tag in nonzero_tags ]
        
        if len( removee_terms ) > len( self._selected_terms ) ** 0.5:
            
            self._Clear()
            
            removee_terms = []
            altered_terms = []
            new_terms = nonzero_terms
            
        else:
            
            if len( removee_terms ) > 0:
                
                self._RemoveTerms( removee_terms )
                
            
            exists_tuple = [ ( term in self._terms_to_logical_indices, term ) for term in nonzero_terms ]
            
            altered_terms = [ term for ( exists, term ) in exists_tuple if exists ]
            
            new_terms = [ term for ( exists, term ) in exists_tuple if not exists ]
            
        
        if len( altered_terms ) > 0:
            
            for term in altered_terms:
                
                actual_term = self._positional_indices_to_terms[ self._terms_to_positional_indices[ term ] ]
                
                actual_term.UpdateFromOtherTerm( term )
                
            
        
        sort_needed = False
        
        if len( new_terms ) > 0:
            
            # TODO: see about doing an _InsertTerms that will do insort, bisect.insort_left kind of thing, assuming I can get better 'key' tech going in tag sort
            
            self._AppendTerms( new_terms )
            
            sort_needed = True
            
        
        if not sort_needed and self._tag_sort.AffectedByCount():
            
            if len( altered_terms ) < len( self._ordered_terms ) / 20:
                
                # TODO: for every term we have altered or added or whatever...
                # calc its new sort count. if the guy above or below have a higher/lower (wrong) count, immediately stop and say sort needed
                # this gets complicated with namespace grouping and stuff, so we need to have a single key/cmp call tbh
                
                sort_needed = True
                
            else:
                
                # just do it, whatever
                sort_needed = True
                
            
        
        for term in previous_selected_terms:
            
            if term in self._terms_to_logical_indices:
                
                self._selected_terms.add( term )
                
            
        
        if sort_needed:
            
            self._Sort()
            
        
    
    def _Sort( self ):
        
        # TODO: hey, rejigger this to cleverly and neatly not need to count tags if the sort doesn't care about counts at all!
        # probably means converting .SortTags later into cleaner subcalls and then calling them directly here or something
        
        # I do this weird terms to count instead of tags to count because of tag vs ideal tag gubbins later on in sort
        
        terms_to_count = collections.Counter()
        
        jobs = [
            ( self._show_current, self._current_tags_to_count ),
            ( self._show_deleted, self._deleted_tags_to_count ),
            ( self._show_pending, self._pending_tags_to_count ),
            ( self._show_petitioned, self._petitioned_tags_to_count )
        ]
        
        counts_to_include = [ c for ( show, c ) in jobs if show and len( c ) > 0 ]
        
        # this is a CPU sensitive area, so let's compress and hardcode the faster branches
        if len( counts_to_include ) == 1:
            
            ( c, ) = counts_to_include
            
            terms_to_count = collections.Counter(
                { term : c[ term.GetTag() ] for term in self._ordered_terms }
            )
            
        elif len( counts_to_include ) == 2:
            
            ( c1, c2 ) = counts_to_include
            
            tt_iter = ( ( term, term.GetTag() ) for term in self._ordered_terms )
            
            terms_to_count = collections.Counter(
                { term : c1[ tag ] + c2[ tag ] for ( term, tag ) in tt_iter }
            )
            
        else:
            
            tt_iter = ( ( term, term.GetTag() ) for term in self._ordered_terms )
            
            terms_to_count = collections.Counter(
                { term : sum( ( c[ tag ] for c in counts_to_include ) ) for ( term, tag ) in tt_iter }
            )
            
        
        item_to_tag_key_wrapper = lambda term: term.GetTag()
        item_to_sibling_key_wrapper = item_to_tag_key_wrapper
        
        if self._show_sibling_decorators:
            
            item_to_sibling_key_wrapper = lambda term: term.GetBestTag()
            
        
        ClientTagSorting.SortTags( self._tag_sort, self._ordered_terms, tag_items_to_count = terms_to_count, item_to_tag_key_wrapper = item_to_tag_key_wrapper, item_to_sibling_key_wrapper = item_to_sibling_key_wrapper )
        
        self._RegenTermsToIndices()
        
    
    def AddAdditionalMenuItems( self, menu: QW.QMenu ):
        
        ListBoxTagsDisplayCapable.AddAdditionalMenuItems( self, menu )
        
        if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            submenu = ClientGUIMenus.GenerateMenu( menu )
            
            for tag_display_type in ( ClientTags.TAG_DISPLAY_SELECTION_LIST, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL, ClientTags.TAG_DISPLAY_STORAGE ):
                
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
        
    
    def SetTagsByMediaFromMediaResultsPanel( self, media, tags_changed ):
        
        flat_media = ClientMedia.FlattenMedia( media )
        
        media_results = [ m.GetMediaResult() for m in flat_media ]
        
        self.SetTagsByMediaResultsFromMediaResultsPanel( media_results, tags_changed )
        
    
    def SetTagsByMediaResultsFromMediaResultsPanel( self, media_results, tags_changed ):
        
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
    
    def __init__( self, parent, title, tag_presentation_location: int, show_siblings_sort = False ):
        
        super().__init__( parent, title )
        
        self._original_title = title
        
        self._tag_presentation_location = tag_presentation_location
        
        self._tags_box = None
        
        # make this its own panel
        self._tag_sort = ClientGUITagSorting.TagSortControl( self, CG.client_controller.new_options.GetDefaultTagSort( self._tag_presentation_location ), show_siblings = show_siblings_sort )
        
        self._tag_sort.valueChanged.connect( self.EventSort )
        
        self.Add( self._tag_sort, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def SetTagContext( self, tag_context: ClientSearchTagContext.TagContext ):
        
        self.SetTagServiceKey( tag_context.service_key )
        
    
    def SetTagServiceKey( self, service_key ):
        
        if self._tags_box is None:
            
            return
            
        
        self._tags_box.SetTagServiceKey( service_key )
        
        title = self._original_title
        
        if service_key != CC.COMBINED_TAG_SERVICE_KEY:
            
            title = '{} for {}'.format( title, CG.client_controller.services_manager.GetName( service_key ) )
            
        
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
    
    def __init__( self, parent, canvas_key, location_context: ClientLocation.LocationContext ):
        
        super().__init__( parent, ClientTags.TAG_DISPLAY_SINGLE_MEDIA, CC.TAG_PRESENTATION_MEDIA_VIEWER, include_counts = False )
        
        self._canvas_key = canvas_key
        self._location_context = location_context
        
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        CG.client_controller.pub( 'canvas_manage_tags', self._canvas_key )
        
        return True
        
    
    def _GetCurrentLocationContext( self ):
        
        return self._location_context
        
    

class ListBoxTagsMediaTagsDialog( ListBoxTagsMedia ):
    
    def __init__( self, parent, tag_presentation_location, enter_func, delete_func ):
        
        super().__init__( parent, ClientTags.TAG_DISPLAY_STORAGE, tag_presentation_location, include_counts = True )
        
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
            
        
    
