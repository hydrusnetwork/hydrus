import typing

from hydrus.core import HydrusSerialisable

from hydrus.client.gui.lists import ClientGUIListConstants as CGLC

class ColumnListStatus( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_COLUMN_LIST_STATUS
    SERIALISABLE_NAME = 'Column List Status'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._column_list_type = 0
        self._columns = []
        self._sort_column_type = 0
        self._sort_asc = True
        
        self._column_types_in_order = []
        self._columns_to_widths = {}
        self._columns_to_shown = {}
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._column_list_type, self._columns, self._sort_column_type, self._sort_asc )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._column_list_type, self._columns, self._sort_column_type, self._sort_asc ) = serialisable_info
        
        self._UpdateColumnCache()
        
    
    def _UpdateColumnCache( self ):
        
        self._column_types_in_order = []
        self._columns_to_widths = {}
        self._columns_to_shown = {}
        
        for ( column_type, width, shown ) in self._columns:
            
            self._column_types_in_order.append( column_type )
            self._columns_to_widths[ column_type ] = width
            self._columns_to_shown[ column_type ] = shown
            
        
    
    def AddRemoveForNewColumns( self ):
        
        default = ColumnListStatus.STATICGetDefault( self._column_list_type )
        
        if set( default.GetColumnTypes() ) != set( self._column_types_in_order ):
            
            default_column_types = default.GetColumnTypes()
            
            my_new_column_types = []
            
            for column_type in self._column_types_in_order:
                
                # column is now obselete
                if column_type not in default_column_types:
                    
                    continue
                    
                
                my_new_column_types.append( column_type )
                
            
            for ( i, column_type ) in enumerate( default_column_types ):
                
                # new column, try to stick it somewhere reasonable
                if column_type not in my_new_column_types:
                    
                    my_new_column_types.insert( i, column_type )
                    
                
            
            self._columns = []
            
            for column_type in my_new_column_types:
                
                if column_type in self._columns_to_widths:
                    
                    width = self._columns_to_widths[ column_type ]
                    shown = self._columns_to_shown[ column_type ]
                    
                    
                else:
                    
                    width = default.GetColumnWidth( column_type )
                    shown = default.IsColumnShown( column_type )
                    
                
                self._columns.append( ( column_type, width, shown ) )
                
            
            if self._sort_column_type not in default_column_types:
                
                ( self._sort_column_type, self._sort_asc ) = default.GetSort()
                
            
            self._UpdateColumnCache()
            
        
    
    def FixMissingDefinitions( self ):
        
        clean_columns = []
        
        for ( column_type, width, shown ) in self._columns:
            
            if column_type not in CGLC.column_list_column_name_lookup[ self._column_list_type ]:
                
                if self._sort_column_type == column_type:
                    
                    ( self._sort_column_type, self._sort_asc ) = CGLC.default_column_list_sort_lookup[ self._column_list_type ]
                    
                
                continue
                
            
            clean_columns.append( ( column_type, width, shown ) )
            
        
        if len( clean_columns ) != len( self._columns ):
            
            self._columns = clean_columns
            
            self._UpdateColumnCache()
            
        
        new_columns_added = False
        
        for ( i, ( column_type, width, shown ) ) in enumerate( CGLC.default_column_list_columns_lookup[ self._column_list_type ] ):
            
            if column_type not in self._column_types_in_order:
                
                self._columns.insert( i, ( column_type, width, shown ) )
                
                new_columns_added = True
                
            
        
        if new_columns_added:
            
            self._UpdateColumnCache()
            
        
    
    def GetColumnCount( self ) -> int:
        
        return len( self._column_types_in_order )
        
    
    def GetColumnIndexFromType( self, column_type: int ):
        
        return self._column_types_in_order.index( column_type )
        
    
    def GetColumnListType( self ) -> int:
        
        return self._column_list_type
        
    
    def GetColumnTypeFromIndex( self, column_index: int ):
        
        return self._column_types_in_order[ column_index ]
        
    
    def GetColumnTypes( self ) -> typing.List[ int ]:
        
        return list( self._column_types_in_order )
        
    
    def GetColumnWidth( self, column_type: int ) -> int:
        
        return self._columns_to_widths[ column_type ]
        
    
    def GetSort( self ) -> typing.Tuple[ int, bool ]:
        
        return ( self._sort_column_type, self._sort_asc )
        
    
    def IsColumnShown( self, column_type: int ) -> bool:
        
        return self._columns_to_shown[ column_type ]
        
    
    def SetColumnListType( self, column_list_type: int ):
        
        self._column_list_type = column_list_type
        
    
    def SetSort( self, sort_column_type: int, sort_asc: bool ):
        
        self._sort_column_type = sort_column_type
        self._sort_asc = sort_asc
        
    
    def SetColumns( self, columns: typing.List[ typing.Tuple[ int, int, bool ] ] ):
        
        self._columns = columns
        
        self._UpdateColumnCache()
        
    
    @staticmethod
    def STATICGetDefault( column_list_type: int ) -> "ColumnListStatus":
        
        columns = CGLC.default_column_list_columns_lookup[ column_list_type ]
        ( sort_column_type, sort_asc ) = CGLC.default_column_list_sort_lookup[ column_list_type ]
        
        status = ColumnListStatus()
        
        status.SetColumnListType( column_list_type )
        status.SetColumns( columns )
        status.SetSort( sort_column_type, sort_asc )
        
        return status
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_COLUMN_LIST_STATUS ] = ColumnListStatus
