from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIStyle
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class StylePanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options ):
        
        super().__init__( parent )
        
        self._new_options = new_options
        
        #
        
        help_text = 'Hey, there are several custom widget colours that can be overridden in the "colours" page!'
        
        self._help_label = ClientGUICommon.BetterStaticText( self, label = help_text )
        
        self._help_label.setObjectName( 'HydrusWarning' )
        
        self._help_label.setWordWrap( True )
        
        self._qt_style_name = ClientGUICommon.BetterChoice( self )
        self._qt_stylesheet_name = ClientGUICommon.BetterChoice( self )
        
        self._qt_style_name.addItem( 'use default ("{}")'.format( ClientGUIStyle.ORIGINAL_STYLE_NAME ), None )
        
        try:
            
            for name in ClientGUIStyle.GetAvailableStyles():
                
                self._qt_style_name.addItem( name, name )
                
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.ShowException( e )
            
        
        self._qt_stylesheet_name.addItem( 'use default', None )
        
        try:
            
            for name in ClientGUIStyle.GetAvailableStyleSheets():
                
                self._qt_stylesheet_name.addItem( name, name )
                
            
        except HydrusExceptions.DataMissing as e:
            
            HydrusData.ShowException( e )
            
        
        #
        
        self._qt_style_name.SetValue( self._new_options.GetNoneableString( 'qt_style_name' ) )
        self._qt_stylesheet_name.SetValue( self._new_options.GetNoneableString( 'qt_stylesheet_name' ) )
        
        #
        
        vbox = QP.VBoxLayout()
        
        #
        
        QP.AddToLayout( vbox, self._help_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        text = 'The current styles are what your Qt has available, the stylesheets are what .css and .qss files are currently in install_dir/static/qss or db_dir/static/qss (if you make one).'
        text += '\n' * 2
        text += 'If you run from source and select e621, or Paper_Dark stylesheets, which include external (svg) assets, you must make sure that your CWD is the hydrus install folder when you boot the program. For a custom QSS in your db_dir that uses external assets, you must edit the .QSS so it uses absolute path names.'
        
        st = ClientGUICommon.BetterStaticText( self, label = text )
        
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'Qt style:', self._qt_style_name ) )
        rows.append( ( 'Qt stylesheet:', self._qt_stylesheet_name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._qt_style_name.currentIndexChanged.connect( self.StyleChanged )
        self._qt_stylesheet_name.currentIndexChanged.connect( self.StyleChanged )
        
    
    def StyleChanged( self ):
        
        qt_style_name = self._qt_style_name.GetValue()
        qt_stylesheet_name = self._qt_stylesheet_name.GetValue()
        
        try:
            
            if qt_style_name is None:
                
                ClientGUIStyle.SetStyleFromName( ClientGUIStyle.ORIGINAL_STYLE_NAME )
                
            else:
                
                ClientGUIStyle.SetStyleFromName( qt_style_name )
                
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Critical', f'Could not apply style: {e}' )
            
        
        CG.client_controller.gui._DoMenuBarStyleHack()
        
        try:
            
            if qt_stylesheet_name is None:
                
                ClientGUIStyle.ClearStyleSheet()
                
            else:
                
                ClientGUIStyle.SetStyleSheetFromPath( qt_stylesheet_name )
                
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Critical', f'Could not apply stylesheet: {e}' )
            
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetNoneableString( 'qt_style_name', self._qt_style_name.GetValue() )
        self._new_options.SetNoneableString( 'qt_stylesheet_name', self._qt_stylesheet_name.GetValue() )
        
    
