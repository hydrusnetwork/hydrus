import collections
import itertools
import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client import ClientSearch
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.pages import ClientGUIResultsSortCollect
from hydrus.client.gui.widgets import ClientGUICommon

class EditFavouriteSearchPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, existing_folders_to_names, foldername, name, file_search_context, synchronised, media_sort, media_collect ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._existing_folders_to_names = existing_folders_to_names
        self._original_folder_and_name = ( foldername, name )
        
        self._foldername = QW.QLineEdit( self )
        self._name = QW.QLineEdit( self )
        
        self._media_sort = ClientGUIResultsSortCollect.MediaSortControl( self )
        self._media_collect = ClientGUIResultsSortCollect.MediaCollectControl( self, silent = True )
        
        page_key = HydrusData.GenerateKey()
        
        from hydrus.client.gui.search import ClientGUIACDropdown
        
        self._tag_autocomplete = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self, page_key, file_search_context, media_sort_widget = self._media_sort, media_collect_widget = self._media_collect, synchronised = synchronised, hide_favourites_edit_actions = True )
        
        self._include_media_sort = QW.QCheckBox( self )
        self._include_media_collect = QW.QCheckBox( self )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._include_media_collect, 48 )
        
        self._include_media_collect.setMinimumWidth( width )
        
        self._include_media_sort.stateChanged.connect( self._UpdateWidgets )
        self._include_media_collect.stateChanged.connect( self._UpdateWidgets )
        
        #
        
        if foldername is not None:
            
            self._foldername.setText( foldername )
            
        
        self._name.setText( name )
        
        if media_sort is not None:
            
            self._include_media_sort.setChecked( True )
            
            self._media_sort.SetSort( media_sort )
            
        
        if media_collect is not None:
            
            self._include_media_collect.setChecked( True )
            
            self._media_collect.SetCollect( media_collect )
            
        
        #
        
        rows = []
        
        rows.append( ( 'folder (blank for none): ', self._foldername ) )
        rows.append( ( 'name: ', self._name ) )
        
        top_gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        rows = []
        
        rows.append( ( 'save sort: ', self._include_media_sort ) )
        rows.append( ( 'sort: ', self._media_sort ) )
        rows.append( ( 'save collect: ', self._include_media_collect ) )
        rows.append( ( 'collect: ', self._media_collect ) )
        
        bottom_gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, top_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tag_autocomplete, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, bottom_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def _UpdateWidgets( self ):
        
        self._media_sort.setEnabled( self._include_media_sort.isChecked() )
        self._media_collect.setEnabled( self._include_media_collect.isChecked() )
        
    
    def UserIsOKToOK( self ):
        
        ( foldername, name, file_search_context, synchronised, media_sort, media_collect ) = self.GetValue()
        
        if ( foldername, name ) != self._original_folder_and_name:
            
            if foldername in self._existing_folders_to_names and name in self._existing_folders_to_names[ foldername ]:
                
                if foldername is None:
                    
                    folder_str = ''
                    
                else:
                    
                    folder_str = ' under folder "{}"'.format( foldername )
                    
                
                message = 'The search "{}"{} already exists! Do you want to overwrite it?'.format( name, folder_str )
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.Accepted:
                    
                    return False
                    
                
            
        
        return True
        
    
    def GetValue( self ):
        
        foldername = self._foldername.text()
        
        if foldername == '':
            
            foldername = None
            
        
        name = self._name.text()
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        synchronised = self._tag_autocomplete.IsSynchronised()
        
        if self._include_media_sort.isChecked():
            
            media_sort = self._media_sort.GetSort()
            
        else:
            
            media_sort = None
            
        
        if self._include_media_collect.isChecked():
            
            media_collect = self._media_collect.GetValue()
            
        else:
            
            media_collect = None
            
        
        return ( foldername, name, file_search_context, synchronised, media_sort, media_collect )
        
    
class EditFavouriteSearchesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, favourite_searches_rows, initial_search_row_to_edit = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._favourite_searches_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._favourite_searches = ClientGUIListCtrl.BetterListCtrl( self._favourite_searches_panel, CGLC.COLUMN_LIST_FAVOURITE_SEARCHES.ID, 20, self._ConvertRowToListCtrlTuples, use_simple_delete = True, activation_callback = self._EditFavouriteSearch )
        
        self._favourite_searches_panel.SetListCtrl( self._favourite_searches )
        
        self._favourite_searches_panel.AddButton( 'add', self._AddNewFavouriteSearch )
        self._favourite_searches_panel.AddButton( 'edit', self._EditFavouriteSearch, enabled_only_on_selection = True )
        self._favourite_searches_panel.AddDeleteButton()
        
        #
        
        self._favourite_searches.AddDatas( favourite_searches_rows )
        
        self._favourite_searches.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._favourite_searches_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        if initial_search_row_to_edit is not None:
            
            HG.client_controller.CallLaterQtSafe( self, 0.5, 'add new favourite search', self._AddNewFavouriteSearch, initial_search_row_to_edit )
            
        
    
    def _AddNewFavouriteSearch( self, search_row = None ):
        
        existing_folders_to_names = self._GetExistingFoldersToNames()
        
        existing_names = { name for name in itertools.chain.from_iterable( existing_folders_to_names.values() ) }
        
        if search_row is None:
            
            foldername = None
            name = 'new favourite search'
            
            default_location_context = HG.client_controller.services_manager.GetDefaultLocationContext()
            
            file_search_context = ClientSearch.FileSearchContext( location_context = default_location_context )
            
            synchronised = True
            media_sort = None
            media_collect = None
            
        else:
            
            ( foldername, name, file_search_context, synchronised, media_sort, media_collect ) = search_row
            
        
        name = HydrusData.GetNonDupeName( name, existing_names )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit favourite search' ) as dlg:
            
            panel = EditFavouriteSearchPanel( dlg, existing_folders_to_names, foldername, name, file_search_context, synchronised, media_sort, media_collect )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                row = panel.GetValue()
                
                self._DeleteRow( row[0], row[1] )
                
                self._favourite_searches.AddDatas( ( row, ) )
                
                self._favourite_searches.Sort()
                
            
        
    
    def _ConvertRowToListCtrlTuples( self, row ):
        
        ( foldername, name, file_search_context, synchronised, media_sort, media_collect ) = row
        
        if foldername is None:
            
            pretty_foldername = ''
            
        else:
            
            pretty_foldername = foldername
            
        
        pretty_name = name
        pretty_file_search_context = ', '.join( predicate.ToString() for predicate in file_search_context.GetPredicates() )
        
        if media_sort is None:
            
            pretty_media_sort = ''
            
        else:
            
            pretty_media_sort = media_sort.ToString()
            
        
        if media_collect is None:
            
            pretty_media_collect = ''
            
        else:
            
            pretty_media_collect = media_collect.ToString()
            
        
        display_tuple = ( pretty_foldername, pretty_name, pretty_file_search_context, pretty_media_sort, pretty_media_collect )
        sort_tuple = ( pretty_foldername, pretty_name, pretty_file_search_context, pretty_media_sort, pretty_media_collect )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DeleteRow( self, foldername, name ):
        
        for row in self._favourite_searches.GetData():
            
            if foldername == row[0] and name == row[1]:
                
                self._favourite_searches.DeleteDatas( ( row, ) )
                
                return
                
            
        
    
    def _EditFavouriteSearch( self ):
        
        for row in self._favourite_searches.GetData( only_selected = True ):
            
            ( foldername, name, file_search_context, synchronised, media_sort, media_collect ) = row
            
            existing_folders_to_names = self._GetExistingFoldersToNames()
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit favourite search' ) as dlg:
                
                panel = EditFavouriteSearchPanel( dlg, existing_folders_to_names, foldername, name, file_search_context, synchronised, media_sort, media_collect )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    self._DeleteRow( foldername, name )
                    
                    edited_row = panel.GetValue()
                    
                    self._DeleteRow( edited_row[0], edited_row[1] )
                    
                    self._favourite_searches.AddDatas( ( edited_row, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._favourite_searches.Sort()
        
    
    def _GetExistingFoldersToNames( self ):
        
        existing_folders_to_names = collections.defaultdict( list )
        
        for ( foldername, name, file_search_context, synchronised, media_sort, media_collect ) in self._favourite_searches.GetData():
            
            existing_folders_to_names[ foldername ].append( name )
            
        
        return existing_folders_to_names
        
    
    def GetValue( self ):
        
        favourite_searches_rows = self._favourite_searches.GetData()
        
        return favourite_searches_rows
        
    
