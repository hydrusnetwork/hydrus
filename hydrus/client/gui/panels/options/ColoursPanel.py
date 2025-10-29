from qtpy import QtWidgets as QW

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUIColourPicker
from hydrus.client.gui.widgets import ClientGUICommon

class ColoursPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._new_options = CG.client_controller.new_options
        
        help_text = 'Hey, this page is pretty old, and hydev is in the process of transforming it into a different system. Colours are generally managed through QSS stylesheets now, under the "style" page, but you can still override some stuff here if you want.'
        help_text += '\n\n'
        help_text += 'The "darkmode" in hydrus is also very old and only changes these colours; it does not change the stylesheet. Please bear with the awkwardness, this will be cleaned up eventually, thank you!'
        help_text += '\n\n'
        help_text += 'Tag colours are set under "tag presentation".'
        
        self._help_label = ClientGUICommon.BetterStaticText( self, label = help_text )
        
        self._help_label.setObjectName( 'HydrusWarning' )
        
        self._help_label.setWordWrap( True )
        
        self._override_stylesheet_colours = QW.QCheckBox( self )
        
        self._current_colourset = ClientGUICommon.BetterChoice( self )
        
        self._current_colourset.addItem( 'default', 'default' )
        self._current_colourset.addItem( 'darkmode', 'darkmode' )
        
        self._coloursets_panel = ClientGUICommon.StaticBox( self, 'coloursets' )
        
        self._notebook = QW.QTabWidget( self._coloursets_panel )
        
        self._gui_colours = {}
        
        for colourset in ( 'default', 'darkmode' ):
            
            self._gui_colours[ colourset ] = {}
            
            colour_panel = QW.QWidget( self._notebook )
            
            colour_types = []
            
            colour_types.append( CC.COLOUR_THUMB_BACKGROUND )
            colour_types.append( CC.COLOUR_THUMB_BACKGROUND_SELECTED )
            colour_types.append( CC.COLOUR_THUMB_BACKGROUND_REMOTE )
            colour_types.append( CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED )
            colour_types.append( CC.COLOUR_THUMB_BORDER )
            colour_types.append( CC.COLOUR_THUMB_BORDER_SELECTED )
            colour_types.append( CC.COLOUR_THUMB_BORDER_REMOTE )
            colour_types.append( CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED )
            colour_types.append( CC.COLOUR_THUMBGRID_BACKGROUND )
            colour_types.append( CC.COLOUR_AUTOCOMPLETE_BACKGROUND )
            colour_types.append( CC.COLOUR_MEDIA_BACKGROUND )
            colour_types.append( CC.COLOUR_MEDIA_TEXT )
            colour_types.append( CC.COLOUR_TAGS_BOX )
            
            for colour_type in colour_types:
                
                ctrl = ClientGUIColourPicker.ColourPickerButton( colour_panel )
                
                ctrl.setMaximumWidth( 20 )
                
                ctrl.SetColour( self._new_options.GetColour( colour_type, colourset ) )
                
                self._gui_colours[ colourset ][ colour_type ] = ctrl
                
            
            #
            
            rows = []
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND], CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND_SELECTED], CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND_REMOTE], CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED], CC.FLAGS_CENTER_PERPENDICULAR )
            
            rows.append( ( 'thumbnail background (local: normal/selected, not local: normal/selected): ', hbox ) )
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER], CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER_SELECTED], CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER_REMOTE], CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED], CC.FLAGS_CENTER_PERPENDICULAR )
            
            rows.append( ( 'thumbnail border (local: normal/selected, not local: normal/selected): ', hbox ) )
            
            rows.append( ( 'thumbnail grid background: ', self._gui_colours[ colourset ][ CC.COLOUR_THUMBGRID_BACKGROUND ] ) )
            rows.append( ( 'autocomplete background: ', self._gui_colours[ colourset ][ CC.COLOUR_AUTOCOMPLETE_BACKGROUND ] ) )
            rows.append( ( 'media viewer background: ', self._gui_colours[ colourset ][ CC.COLOUR_MEDIA_BACKGROUND ] ) )
            rows.append( ( 'media viewer text: ', self._gui_colours[ colourset ][ CC.COLOUR_MEDIA_TEXT ] ) )
            rows.append( ( 'tags box background: ', self._gui_colours[ colourset ][ CC.COLOUR_TAGS_BOX ] ) )
            
            gridbox = ClientGUICommon.WrapInGrid( colour_panel, rows )
            
            colour_panel.setLayout( gridbox )
            
            select = colourset == 'default'
            
            self._notebook.addTab( colour_panel, colourset )
            if select: self._notebook.setCurrentWidget( colour_panel )
            
        
        #
        
        self._override_stylesheet_colours.setChecked( self._new_options.GetBoolean( 'override_stylesheet_colours' ) )
        self._current_colourset.SetValue( self._new_options.GetString( 'current_colourset' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'override what is set in the stylesheet with the colours on this page: ', self._override_stylesheet_colours ) )
        rows.append( ( 'current colourset: ', self._current_colourset ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self._coloursets_panel.Add( self._notebook, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._help_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._coloursets_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._override_stylesheet_colours.clicked.connect( self._UpdateOverride )
        
        self._UpdateOverride()
        
    
    def _UpdateOverride( self ):
        
        self._coloursets_panel.setEnabled( self._override_stylesheet_colours.isChecked() )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetBoolean( 'override_stylesheet_colours', self._override_stylesheet_colours.isChecked() )
        
        for colourset in self._gui_colours:
            
            for ( colour_type, ctrl ) in list(self._gui_colours[ colourset ].items()):
                
                colour = ctrl.GetColour()
                
                self._new_options.SetColour( colour_type, colourset, colour )
                
            
        
        self._new_options.SetString( 'current_colourset', self._current_colourset.GetValue() )
        
    
