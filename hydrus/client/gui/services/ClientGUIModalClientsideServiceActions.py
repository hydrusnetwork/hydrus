import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientMigration
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon

class ReviewPurgeTagsPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, service_key: bytes, tags: typing.Collection[ str ] ):
        
        # update the listboxstrings to have async count fetch, would be nice. could also show (0) count tags from init
        # prob needs a refresh button also to refresh current counts
        
        self._service_key = service_key
        
        super().__init__( parent )
        
        # what about a listboxtags that has an auto-async thing to produce a count suffix, mate? surely this is doable in some way
        self._tags_to_remove = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( self, service_key = service_key )
        
        self._autocomplete = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self._tags_to_remove.EnterTags, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), self._service_key, show_paste_button = True )
        
        # forcing things in case options try to set default
        self._autocomplete.SetLocationContext( ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ) )
        self._autocomplete.SetTagServiceKey( self._service_key )
        
        self._default_petition_reason = 'Tags purged by janitor.'
        
        self._petition_reason = QW.QLineEdit( self )
        self._petition_reason.setPlaceholderText( self._default_petition_reason )
        
        self._go_button = ClientGUICommon.BetterButton( self, 'Go!', self.Go )
        
        #
        
        self._tags_to_remove.SetTags( tags )
        
        label = 'This will petition every instance of the tag from the repository, which, when you commit, will leave a deletion record (so only janitors would be able to re-add those tags for those files). If you have permission, you likely also want to add these tags to the repository\'s tag filter so they cannot be added to any other files in future.'
        label += '\n' * 2
        label += 'If you cannot find a tag in the autocomplete, then it probably only exists as a result of a sibling or parent relationship. These tags cannot be deleted here, since they do not actually exist on the repository as stored mappings--you need to change the underlying siblings/parents and/or delete the source mappings that implicate them.'
        
        st = ClientGUICommon.BetterStaticText( self, label )
        
        st.setWordWrap( True )
        
        rows = []
        
        rows.append( ( 'petition reason (optional): ', self._petition_reason ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tags_to_remove, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._autocomplete, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._go_button, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        self._autocomplete.tagsPasted.connect( self._tags_to_remove.AddTags )
        
    
    def Go( self ):
        
        tags_to_purge = self._tags_to_remove.GetTags()
        
        if len( tags_to_purge ) == 0:
            
            return
            
        
        text = f'Start this purge job on {HydrusNumbers.ToHumanInt( len( tags_to_purge ) )} tags?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        reason = self._petition_reason.text()
        
        if reason == '':
            
            reason = self._default_petition_reason
            
        
        tag_filter = HydrusTags.TagFilter()
        
        # we want the migration to cover the tags we want to delete
        tag_filter.SetRules( ( '', ':' ), HC.FILTER_BLACKLIST )
        tag_filter.SetRules( tags_to_purge, HC.FILTER_WHITELIST )
        
        PurgeTags( self._service_key, tag_filter, reason )
        
        self._tags_to_remove.Clear()
        
    

def PurgeTags(
    service_key: bytes,
    tag_filter: HydrusTags.TagFilter,
    reason: str
):
    
    location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY )
    desired_hash_type = 'sha256'
    hashes = None
    content_statuses = [ HC.CONTENT_STATUS_CURRENT ]
    content_action = HC.CONTENT_UPDATE_PETITION
    
    source = ClientMigration.MigrationSourceTagServiceMappings( CG.client_controller, service_key, location_context, desired_hash_type, hashes, tag_filter, content_statuses )
    
    destination = ClientMigration.MigrationDestinationTagServiceMappings( CG.client_controller, service_key, content_action )
    destination.SetReason( reason )
    
    migration_job = ClientMigration.MigrationJob( CG.client_controller, 'purging tags', source, destination )
    
    CG.client_controller.CallToThread( migration_job.Run )
    

def OpenPurgeTagsWindow(
    win: QW.QWidget,
    service_key: bytes,
    tags: typing.Collection[ str ]
):
    
    frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( win, 'purge tags' )
    
    panel = ReviewPurgeTagsPanel( frame, service_key, tags )
    
    frame.SetPanel( panel )
    

def StartPurgeTagFilter(
    win: QW.QWidget,
    service_key: bytes
):
    
    tag_filter: HydrusTags.TagFilter = CG.client_controller.services_manager.GetService( service_key ).GetTagFilter()
    
    text = f'This will start a purge job based on the rules in the current tag filter, "syncing" the mappings store to the filter by petitioning everything that retroactively violates the rules. The current tag filter for this service is:'
    text += '\n' * 2
    text += tag_filter.ToPermittedString()
    text += '\n' * 2
    text += 'If you do not make any changes to the tag filter, this is idempotent.'
    
    result = ClientGUIDialogsQuick.GetYesNo( win, text )
    
    if result != QW.QDialog.DialogCode.Accepted:
        
        return
        
    
    inverted_tag_filter = tag_filter.GetInvertedFilter() # we actively want to _delete_ what is currently _disallowed_, which means the migration needs to attack the opposite
    
    reason = 'Tag Filter Purge Sync'
    
    PurgeTags( service_key, inverted_tag_filter, reason )
    
