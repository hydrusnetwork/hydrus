import collections
import collections.abc

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags

class IncrementalTaggingPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, medias: list[ ClientMedia.MediaSingleton ] ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        self._medias = medias
        self._namespaces_to_medias_to_namespaced_subtags = collections.defaultdict( dict )
        
        self._service = CG.client_controller.services_manager.GetService( self._service_key )
        
        self._i_am_local_tag_service = self._service.GetServiceType() == HC.LOCAL_TAG
        
        label = 'Here you can add numerical tags incrementally to a selection of files, for instance adding page:1 -> page:20 to twenty files.'
        
        self._top_st = ClientGUICommon.BetterStaticText( self, label = label )
        self._top_st.setWordWrap( True )
        
        self._namespace = QW.QLineEdit( self )
        initial_namespace = CG.client_controller.new_options.GetString( 'last_incremental_tagging_namespace' )
        self._namespace.setText( initial_namespace )
        
        # let's make this dialog a reasonable landscape shape
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._namespace, 64 )
        self._namespace.setFixedWidth( width )
        
        self._prefix = QW.QLineEdit( self )
        initial_prefix = CG.client_controller.new_options.GetString( 'last_incremental_tagging_prefix' )
        self._prefix.setText( initial_prefix )
        
        self._suffix = QW.QLineEdit( self )
        initial_suffix = CG.client_controller.new_options.GetString( 'last_incremental_tagging_suffix' )
        self._suffix.setText( initial_suffix )
        
        self._tag_in_reverse = QW.QCheckBox( self )
        tt = 'Tag the last file first and work backwards, e.g. for start=1, step=1 on five files, set 5, 4, 3, 2, 1.'
        self._tag_in_reverse.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        initial_start = self._GetInitialStart()
        
        self._start = ClientGUICommon.BetterSpinBox( self, initial = initial_start, min = -10000000, max = 10000000 )
        tt = 'If you initialise this dialog and the first file already has that namespace, this widget will start with that version! A little overlap/prep may help here!'
        self._start.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._step = ClientGUICommon.BetterSpinBox( self, initial = 1, min = -10000, max = 10000 )
        tt = 'This sets how much the numerical tag should increment with each iteration. Negative values are fine and will decrement.'
        self._step.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        label = 'initialising\n\ninitialising'
        self._summary_st = ClientGUICommon.BetterStaticText( self, label = label )
        self._summary_st.setWordWrap( True )
        
        #
        
        rows = []
        
        rows.append( ( 'namespace: ', self._namespace ) )
        rows.append( ( 'start: ', self._start ) )
        rows.append( ( 'step: ', self._step ) )
        rows.append( ( 'prefix: ', self._prefix ) )
        rows.append( ( 'suffix: ', self._suffix ) )
        rows.append( ( 'tag in reverse: ', self._tag_in_reverse ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._top_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._summary_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._namespace.textChanged.connect( self._UpdateNamespace )
        self._prefix.textChanged.connect( self._UpdatePrefix )
        self._suffix.textChanged.connect( self._UpdateSuffix )
        self._start.valueChanged.connect( self._UpdateSummary )
        self._step.valueChanged.connect( self._UpdateSummary )
        self._tag_in_reverse.clicked.connect( self._UpdateSummary )
        
        self._UpdateSummary()
        
    
    def _GetInitialStart( self ):
        
        namespace = self._namespace.text()
        
        first_media = self._medias[0]
        
        medias_to_namespaced_subtags = self._GetMediasToNamespacedSubtags( namespace )
        
        namespaced_subtags = HydrusTags.SortNumericTags( medias_to_namespaced_subtags[ first_media ] )
        
        for subtag in namespaced_subtags:
            
            if subtag.isdecimal():
                
                return int( subtag )
                
            
        
        return 1
        
    
    def _GetMediaAndTagPairs( self ) -> list[ tuple[ ClientMedia.MediaSingleton, str ] ]:
        
        tag_template = self._GetTagTemplate()
        start = self._start.value()
        step = self._step.value()
        prefix = self._prefix.text()
        suffix = self._suffix.text()
        
        result = []
        
        medias = list( self._medias )
        
        if self._tag_in_reverse.isChecked():
            
            medias.reverse()
            
        
        for ( i, media ) in enumerate( medias ):
            
            number = start + i * step
            
            subtag = f'{prefix}{number}{suffix}'
            
            tag = tag_template.format( subtag )
            
            result.append( ( media, tag ) )
            
        
        if self._tag_in_reverse.isChecked():
            
            result.reverse()
            
        
        return result
        
    
    def _GetMediasToNamespacedSubtags( self, namespace: str ):
        
        if namespace not in self._namespaces_to_medias_to_namespaced_subtags:
            
            medias_to_namespaced_subtags = dict()
            
            for media in self._medias:
                
                namespaced_subtags = set()
                
                current_and_pending_tags = media.GetTagsManager().GetCurrentAndPending( self._service_key, ClientTags.TAG_DISPLAY_STORAGE )
                
                for tag in current_and_pending_tags:
                    
                    ( n, subtag ) = HydrusTags.SplitTag( tag )
                    
                    if n == namespace:
                        
                        namespaced_subtags.add( subtag )
                        
                    
                
                medias_to_namespaced_subtags[ media ] = namespaced_subtags
                
            
            self._namespaces_to_medias_to_namespaced_subtags[ namespace ] = medias_to_namespaced_subtags
            
        
        return self._namespaces_to_medias_to_namespaced_subtags[ namespace ]
        
    
    def _GetTagTemplate( self ):
        
        namespace = self._namespace.text()
        
        if namespace == '':
            
            return '{}'
            
        else:
            
            return namespace + ':{}'
            
        
    
    def _UpdateNamespace( self ):
        
        namespace = self._namespace.text()
        
        CG.client_controller.new_options.SetString( 'last_incremental_tagging_namespace', namespace )
        
        self._UpdateSummary()
        
    
    def _UpdatePrefix( self ):
        
        prefix = self._prefix.text()
        
        CG.client_controller.new_options.SetString( 'last_incremental_tagging_prefix', prefix )
        
        self._UpdateSummary()
        
    
    def _UpdateSuffix( self ):
        
        suffix = self._suffix.text()
        
        CG.client_controller.new_options.SetString( 'last_incremental_tagging_suffix', suffix )
        
        self._UpdateSummary()
        
    
    def _UpdateSummary( self ):
        
        file_summary = f'{HydrusNumbers.ToHumanInt(len(self._medias))} files'
        
        medias_and_tags = self._GetMediaAndTagPairs()
        
        if len( medias_and_tags ) <= 4:
            
            tag_summary = ', '.join( ( tag for ( media, tag ) in medias_and_tags ) )
            
        else:
            
            if self._tag_in_reverse.isChecked():
                
                tag_summary = medias_and_tags[0][1] + f' {HC.UNICODE_ELLIPSIS} ' + ', '.join( ( tag for ( media, tag ) in medias_and_tags[-3:] ) )
                
            else:
                
                tag_summary = ', '.join( ( tag for ( media, tag ) in medias_and_tags[:3] ) ) + f' {HC.UNICODE_ELLIPSIS} ' + medias_and_tags[-1][1]
                
            
        
        #
        
        namespace = self._namespace.text()
        
        medias_to_namespaced_subtags = self._GetMediasToNamespacedSubtags( namespace )
        
        already_count = 0
        disagree_count = 0
        
        for ( media, tag ) in medias_and_tags:
            
            ( n, subtag ) = HydrusTags.SplitTag( tag )
            
            namespaced_subtags = medias_to_namespaced_subtags[ media ]
            
            if subtag in namespaced_subtags:
                
                already_count += 1
                
            elif len( namespaced_subtags ) > 0:
                
                disagree_count += 1
                
            
        
        if already_count == 0 and disagree_count == 0:
            
            conflict_summary = 'No conflicts, this all looks fresh!'
            
        elif disagree_count == 0:
            
            if already_count == len( self._medias ):
                
                conflict_summary = 'All the files already have these tags. This will make no changes.'
                
            else:
                
                conflict_summary = f'{HydrusNumbers.ToHumanInt( already_count )} files already have these tags.'
                
            
        elif already_count == 0:
            
            conflict_summary = f'{HydrusNumbers.ToHumanInt( disagree_count )} files already have different tags for this namespace. Are you sure you are lined up correct?'
            
        else:
            
            conflict_summary = f'{HydrusNumbers.ToHumanInt( already_count )} files already have these tags, and {HydrusNumbers.ToHumanInt( disagree_count )} files already have different tags for this namespace. Are you sure you are lined up correct?'
            
        
        label = f'For the {file_summary}, you are setting {tag_summary}.'
        label += '\n' * 2
        label += f'{conflict_summary}'
        
        self._summary_st.setText( label )
        
    
    def GetValue( self ) -> ClientContentUpdates.ContentUpdatePackage:
        
        if self._i_am_local_tag_service:
            
            content_action = HC.CONTENT_UPDATE_ADD
            
        else:
            
            content_action = HC.CONTENT_UPDATE_PEND
            
        
        medias_and_tags = self._GetMediaAndTagPairs()
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_action, ( tag, { media.GetHash() } ) ) for ( media, tag ) in medias_and_tags ]
        
        return ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( self._service_key, content_updates )
        
    
