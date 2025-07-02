from qtpy import QtWidgets as QW

from hydrus.core import HydrusExceptions

from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUIRegex

class EditRegexFavourites( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, regex_favourites ):
        
        super().__init__( parent )
        
        regex_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_REGEX_FAVOURITES.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._regexes = ClientGUIListCtrl.BetterListCtrlTreeView( regex_listctrl_panel, 8, model, use_simple_delete = True, activation_callback = self._Edit )
        
        regex_listctrl_panel.SetListCtrl( self._regexes )
        
        regex_listctrl_panel.AddButton( 'add', self._Add )
        regex_listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        regex_listctrl_panel.AddDeleteButton()
        
        #
        
        self._regexes.SetData( regex_favourites )
        
        self._regexes.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, regex_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _Add( self ):
        
        current_data = self._regexes.GetData()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'Enter regex' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = ClientGUIRegex.RegexInput( panel, show_manage_favourites_menu = False )
            
            width = ClientGUIFunctions.ConvertTextToPixelWidth( control, 48 )
            
            control.setMinimumWidth( width )
            
            panel.SetControl( control, perpendicular = True )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                regex_phrase = control.GetValue()
                
            else:
                
                return
                
            
        
        try:
            
            description = ClientGUIDialogsQuick.EnterText( self, 'Enter description.' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        row = ( regex_phrase, description )
        
        if row in current_data:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'That regex and description are already in the list!' )
            
            return
            
        
        self._regexes.AddData( row, select_sort_and_scroll = True )
        
    
    def _ConvertDataToDisplayTuple( self, row ):
        
        ( regex_phrase, description ) = row
        
        display_tuple = ( regex_phrase, description )
        
        return display_tuple
        
    
    _ConvertDataToSortTuple = _ConvertDataToDisplayTuple
    
    def _Edit( self ):
        
        data = self._regexes.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        row = data
        
        ( regex_phrase, description ) = row
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit regex' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = ClientGUIRegex.RegexInput( panel, show_manage_favourites_menu = False )
            
            width = ClientGUIFunctions.ConvertTextToPixelWidth( control, 48 )
            
            control.setMinimumWidth( width )
            
            control.SetValue( regex_phrase )
            
            panel.SetControl( control, perpendicular = True )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                regex_phrase = control.GetValue()
                
            else:
                
                return
                
            
        
        try:
            
            description = ClientGUIDialogsQuick.EnterText( self, 'Edit description.', default = description )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        edited_row = ( regex_phrase, description )
        
        self._regexes.ReplaceData( row, edited_row, sort_and_scroll = True )
        
    
    def GetValue( self ):
        
        return self._regexes.GetData()
        
    
