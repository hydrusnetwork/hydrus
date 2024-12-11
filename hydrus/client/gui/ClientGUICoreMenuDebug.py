from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui.panels import ClientGUIScrolledPanels

def ShowMenuDialog( window: QW.QWidget, menu: QW.QMenu ):
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( window, 'macOS debug menu dialog' ) as dlg:
        
        panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
        
        #
        
        # make a treeview control thing from menu
        control = QW.QTreeWidget( panel )
        
        control.setColumnCount( 1 )
        
        control.setHeaderHidden( True )
        
        jobs = [ ( control, menu ) ]
        
        while len( jobs ) > 0:
            
            ( job_parent, job_menu ) = jobs.pop( 0 )
            
            for action in job_menu.actions():
                
                if action.isSeparator():
                    
                    twi = QW.QTreeWidgetItem()
                    
                    twi.setText( 0, '----' )
                    
                elif action.menu() is not None:
                    
                    twi = QW.QTreeWidgetItem()
                    
                    twi.setText( 0, action.text() )
                    
                    jobs.append( ( twi, action.menu() ) )
                    
                else:
                    
                    twi = QW.QTreeWidgetItem()
                    
                    twi.setText( 0, action.text() )
                    
                    twi.setData( 0, QC.Qt.ItemDataRole.UserRole, action )
                    
                
                if isinstance( job_parent, QW.QTreeWidget ):
                    
                    job_parent.addTopLevelItem( twi )
                    
                else:
                    
                    job_parent.addChild( twi )
                    
                
            
        
        control.value = lambda: 1
        
        control.activated.connect( panel.okSignal )
        
        #
        
        panel.SetControl( control )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            selected_items = control.selectedItems()
            
            if len( selected_items ) > 0:
                
                item = selected_items[0]
                
                action = item.data( 0, QC.Qt.ItemDataRole.UserRole )
                
                if action is not None:
                    
                    action.trigger()
                    
                
            
        
    
