from hydrus.core import HydrusSerialisable

from hydrus.client import ClientGlobals as CG
from hydrus.client.gui.lists import ClientGUIListStatus

class ColumnListManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_COLUMN_LIST_MANAGER
    SERIALISABLE_NAME = 'Column List Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._column_list_types_to_statuses = HydrusSerialisable.SerialisableDictionary()
        
        # populate default values, or load them as needed when missing or whatever mate
        
        self._dirty = False
        
    
    def _GetSerialisableInfo( self ):
        
        return self._column_list_types_to_statuses.GetSerialisableTuple()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_column_list_types_to_statuses = serialisable_info
        
        self._column_list_types_to_statuses = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_column_list_types_to_statuses )
        
    
    def IsDirty( self ):
        
        return self._dirty
        
    
    def GetStatus( self, column_list_type: int, ) -> ClientGUIListStatus.ColumnListStatus:
        
        if column_list_type not in self._column_list_types_to_statuses:
            
            self._column_list_types_to_statuses[ column_list_type ] = ClientGUIListStatus.ColumnListStatus.STATICGetDefault( column_list_type )
            
        
        column_list_status = self._column_list_types_to_statuses[ column_list_type ]
        
        column_list_status.FixMissingDefinitions()
        
        return column_list_status
        
    
    def ResetToDefaults( self, column_list_type = None ):
        
        if column_list_type is None:
            
            self._column_list_types_to_statuses = HydrusSerialisable.SerialisableDictionary()
            
            CG.client_controller.pub( 'reset_all_listctrl_status' )
            
        else:
            
            if column_list_type in self._column_list_types_to_statuses:
                
                del self._column_list_types_to_statuses[ column_list_type ]
                
                CG.client_controller.pub( 'reset_listctrl_status', column_list_type )
                
            
        
        self._dirty = True
        
    
    def SaveStatus( self, column_list_status: ClientGUIListStatus.ColumnListStatus ):
        
        self._column_list_types_to_statuses[ column_list_status.GetColumnListType() ] = column_list_status
        
        self._dirty = True
        
    
    def SetClean( self ):
        
        self._dirty = False
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_COLUMN_LIST_MANAGER ] = ColumnListManager
