import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import QtPorting as QP
from hydrus.client.search import ClientSearchPredicate

class OptionsPanel( QW.QWidget ):
    
    def GetValue( self ):
        
        raise NotImplementedError()
        
    
    def SetValue( self, info ):
        
        raise NotImplementedError()
        
    

class OptionsPanelMimesTree( OptionsPanel ):
    
    def __init__( self, parent, selectable_mimes ):
        
        super().__init__( parent )
        
        self._selectable_mimes = set( selectable_mimes )
        
        self._mimes_to_items = {}
        self._general_mime_types_to_items = {}
        
        general_mime_types = []
        
        general_mime_types.append( HC.GENERAL_IMAGE )
        general_mime_types.append( HC.GENERAL_ANIMATION )
        general_mime_types.append( HC.GENERAL_VIDEO )
        general_mime_types.append( HC.GENERAL_AUDIO )
        general_mime_types.append( HC.GENERAL_APPLICATION )
        general_mime_types.append( HC.GENERAL_IMAGE_PROJECT )
        general_mime_types.append( HC.GENERAL_APPLICATION_ARCHIVE )
        
        self._my_tree = QP.TreeWidgetWithInheritedCheckState( self )
        
        self._my_tree.setHeaderHidden( True )
        
        for general_mime_type in general_mime_types:
            
            mimes_in_type = self._GetMimesForGeneralMimeType( general_mime_type )
            
            if len( mimes_in_type ) == 0:
                
                continue
                
            
            general_mime_item = QW.QTreeWidgetItem()
            general_mime_item.setText( 0, HC.mime_string_lookup[ general_mime_type ] )
            general_mime_item.setFlags( general_mime_item.flags() | QC.Qt.ItemFlag.ItemIsUserCheckable )
            general_mime_item.setCheckState( 0, QC.Qt.CheckState.Unchecked )
            general_mime_item.setData( 0, QC.Qt.ItemDataRole.UserRole, general_mime_type )
            self._my_tree.addTopLevelItem( general_mime_item )
            
            self._general_mime_types_to_items[ general_mime_type ] = general_mime_item
            
            for mime in mimes_in_type:
                
                mime_item = QW.QTreeWidgetItem()
                mime_item.setText( 0, HC.mime_string_lookup[ mime ] )
                mime_item.setFlags( mime_item.flags() | QC.Qt.ItemFlag.ItemIsUserCheckable )
                mime_item.setData( 0, QC.Qt.ItemDataRole.UserRole, mime )
                general_mime_item.addChild( mime_item )
                
                self._mimes_to_items[ mime ] = mime_item
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._my_tree, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _GetMimesForGeneralMimeType( self, general_mime_type ):
        
        mimes_in_type = HC.general_mimetypes_to_mime_groups[ general_mime_type ]
        
        mimes_in_type = [ mime for mime in mimes_in_type if mime in self._selectable_mimes ]
        
        return mimes_in_type
        
    
    def GetValue( self ) -> typing.Tuple[ int ]:
        
        mimes = tuple( [ mime for ( mime, item ) in self._mimes_to_items.items() if item.checkState( 0 ) == QC.Qt.CheckState.Checked ] )
        
        return mimes
        
    
    def SetValue( self, checked_mimes: typing.Collection[ int ] ):
        
        checked_mimes = ClientSearchPredicate.ConvertSummaryFiletypesToSpecific( checked_mimes, only_searchable = False )
        
        for ( mime, item ) in self._mimes_to_items.items():
            
            if mime in checked_mimes:
                
                check_state = QC.Qt.CheckState.Checked
                
            else:
                
                check_state = QC.Qt.CheckState.Unchecked
                
            
            item.setCheckState( 0, check_state )
            
        
    
