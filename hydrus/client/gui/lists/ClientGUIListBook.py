import collections.abc
import os
import re
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientPaths
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.networking import ClientNetworkingFunctions

class ListBook( QW.QWidget ):
    
    def __init__( self, *args, **kwargs ):
        
        QW.QWidget.__init__( self, *args, **kwargs )
        
        self._keys_to_active_pages = {}
        self._keys_to_proto_pages = {}
        
        self._list_box = ClientGUIListBoxes.BetterQListWidget( self )
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
                
            
        
    
