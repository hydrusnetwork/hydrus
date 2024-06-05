import os

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTags
from hydrus.core import HydrusTagArchive
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientMigration
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITags
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.search import ClientGUILocation
from hydrus.client.gui.widgets import ClientGUICommon

class MigrateTagsPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    COPY = 0
    DELETE = 1
    DELETE_DELETED = 2
    DELETE_FOR_DELETED_FILES = 3
    
    ALL_MAPPINGS = 0
    SPECIFIC_MAPPINGS = 1
    SPECIFIC_NAMESPACE = 2
    NAMESPACED = 3
    UNNAMESPACED = 4
    
    HTA_SERVICE_KEY = b'hydrus tag archive'
    HTPA_SERVICE_KEY = b'hydrus tag pair archive'
    
    LOCATION_CONTEXT_LOCATION = 0
    HASHES_LOCATION = 1
    
    def __init__( self, parent, service_key, hashes = None ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._service_key = service_key
        self._hashes = hashes
        
        self._source_archive_path = None
        self._source_archive_hash_type = None
        self._dest_archive_path = None
        self._dest_archive_hash_type_override = None
        
        try:
            
            service = CG.client_controller.services_manager.GetService( self._service_key )
            
        except HydrusExceptions.DataMissing:
            
            services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) )
            
            service = next( iter( services ) )
            
            self._service_key = service.GetServiceKey()
            
        
        #
        
        self._migration_panel = ClientGUICommon.StaticBox( self, 'migration' )
        
        self._migration_content_type = ClientGUICommon.BetterChoice( self._migration_panel )
        
        for content_type in ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_TYPE_TAG_SIBLINGS ):
            
            self._migration_content_type.addItem( HC.content_type_string_lookup[ content_type ], content_type )
            
        
        self._migration_content_type.setToolTip( ClientGUIFunctions.WrapToolTip( 'Sets what will be migrated.' ) )
        
        self._migration_source = ClientGUICommon.BetterChoice( self._migration_panel )
        
        location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
        
        self._migration_source_hash_type_st = ClientGUICommon.BetterStaticText( self._migration_panel, 'hash type: unknown' )
        
        self._migration_source_hash_type_st.setToolTip( ClientGUIFunctions.WrapToolTip( 'If this is something other than sha256, this will only work for files the client has ever previously imported.' ) )
        
        self._migration_source_content_status_filter = ClientGUICommon.BetterChoice( self._migration_panel )
        
        self._migration_source_content_status_filter.setToolTip( ClientGUIFunctions.WrapToolTip( 'This filters which status of tags will be migrated.' ) )
        
        self._migration_source_file_filtering_type = ClientGUICommon.BetterChoice( self._migration_panel )
        
        self._migration_source_file_filtering_type.addItem( 'file domain', self.LOCATION_CONTEXT_LOCATION )
        
        if self._hashes is not None:
            
            self._migration_source_file_filtering_type.addItem( '{} files'.format( HydrusData.ToHumanInt( len( self._hashes ) ) ), self.HASHES_LOCATION )
            
            self._migration_source_file_filtering_type.SetValue( self.HASHES_LOCATION )
            
        
        self._migration_source_file_filtering_type.setToolTip( ClientGUIFunctions.WrapToolTip( 'Choose whether to do this operation for the files you launched the dialog on, or a whole file domain.' ) )
        
        self._migration_source_location_context_button = ClientGUILocation.LocationSearchContextButton( self._migration_panel, location_context )
        self._migration_source_location_context_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Set which files should be eligible. This can get as complicated as you like!' ) )
        
        self._migration_source_archive_path_button = ClientGUICommon.BetterButton( self._migration_panel, 'no path set', self._SetSourceArchivePath )
        
        message = 'Tags that pass this filter will be applied to the destination with the chosen action.'
        message += '\n' * 2
        message += 'For instance, if you whitelist the \'series\' namespace, only series: tags from the source will be added to/deleted from the destination.'
        
        tag_filter = HydrusTags.TagFilter()
        
        self._migration_source_tag_filter = ClientGUITags.TagFilterButton( self._migration_panel, message, tag_filter, label_prefix = 'tags taken: ' )
        
        message = 'The left side of a tag sibling/parent pair must pass this filter for the pair to be included in the migration.'
        message += '\n' * 2
        message += 'For instance, if you whitelist the \'character\' namespace, only pairs from the source with character: tags on the left will be added to/deleted from the destination.'
        
        tag_filter = HydrusTags.TagFilter()
        
        self._migration_source_left_tag_pair_filter = ClientGUITags.TagFilterButton( self._migration_panel, message, tag_filter, label_prefix = 'left: ' )
        
        message = 'The right side of a tag sibling/parent pair must pass this filter for the pair to be included in the migration.'
        message += '\n' * 2
        message += 'For instance, if you whitelist the \'series\' namespace, only pairs from the source with series: tags on the right will be added to/deleted from the destination.'
        
        tag_filter = HydrusTags.TagFilter()
        
        self._migration_source_right_tag_pair_filter = ClientGUITags.TagFilterButton( self._migration_panel, message, tag_filter, label_prefix = 'right: ' )
        
        self._migration_destination = ClientGUICommon.BetterChoice( self._migration_panel )
        
        self._migration_destination_archive_path_button = ClientGUICommon.BetterButton( self._migration_panel, 'no path set', self._SetDestinationArchivePath )
        
        self._migration_destination_hash_type_choice_st = ClientGUICommon.BetterStaticText( self._migration_panel, 'hash type: ' )
        
        self._migration_destination_hash_type_choice = ClientGUICommon.BetterChoice( self._migration_panel )
        
        for hash_type in ( 'sha256', 'md5', 'sha1', 'sha512' ):
            
            self._migration_destination_hash_type_choice.addItem( hash_type, hash_type )
            
        
        self._migration_destination_hash_type_choice.setToolTip( ClientGUIFunctions.WrapToolTip( 'If you set something other than sha256, this will only work for files the client has ever previously imported.' ) )
        
        self._migration_action = ClientGUICommon.BetterChoice( self._migration_panel )
        
        self._migration_go = ClientGUICommon.BetterButton( self._migration_panel, 'Go!', self._MigrationGo )
        
        #
        
        file_left_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( file_left_vbox, self._migration_source_file_filtering_type, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( file_left_vbox, self._migration_source_location_context_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( file_left_vbox, self._migration_source_left_tag_pair_filter, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        tag_right_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( tag_right_vbox, self._migration_source_tag_filter, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( tag_right_vbox, self._migration_source_right_tag_pair_filter, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        dest_hash_type_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( dest_hash_type_hbox, self._migration_destination_hash_type_choice_st, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( dest_hash_type_hbox, self._migration_destination_hash_type_choice, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        gridbox = QP.GridLayout( 6 )
        
        gridbox.setColumnStretch( 0, 1 )
        gridbox.setColumnStretch( 1, 1 )
        gridbox.setColumnStretch( 2, 1 )
        gridbox.setColumnStretch( 3, 1 )
        
        QP.AddToLayout( gridbox, ClientGUICommon.BetterStaticText( self._migration_panel, 'content' ), CC.FLAGS_CENTER )
        QP.AddToLayout( gridbox, ClientGUICommon.BetterStaticText( self._migration_panel, 'source' ), CC.FLAGS_CENTER )
        QP.AddToLayout( gridbox, ClientGUICommon.BetterStaticText( self._migration_panel, 'filter' ), CC.FLAGS_CENTER )
        QP.AddToLayout( gridbox, ClientGUICommon.BetterStaticText( self._migration_panel, 'action' ), CC.FLAGS_CENTER )
        QP.AddToLayout( gridbox, ClientGUICommon.BetterStaticText( self._migration_panel, 'destination' ), CC.FLAGS_CENTER )
        ClientGUICommon.AddGridboxStretchSpacer( self._migration_panel, gridbox )
        
        QP.AddToLayout( gridbox, self._migration_content_type, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._migration_source, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._migration_source_content_status_filter, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._migration_action, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._migration_destination, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._migration_go, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        ClientGUICommon.AddGridboxStretchSpacer( self._migration_panel, gridbox )
        QP.AddToLayout( gridbox, self._migration_source_archive_path_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, file_left_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        ClientGUICommon.AddGridboxStretchSpacer( self._migration_panel, gridbox )
        QP.AddToLayout( gridbox, self._migration_destination_archive_path_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        ClientGUICommon.AddGridboxStretchSpacer( self._migration_panel, gridbox )
        
        ClientGUICommon.AddGridboxStretchSpacer( self._migration_panel, gridbox )
        QP.AddToLayout( gridbox, self._migration_source_hash_type_st, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( gridbox, tag_right_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        ClientGUICommon.AddGridboxStretchSpacer( self._migration_panel, gridbox )
        QP.AddToLayout( gridbox, dest_hash_type_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        ClientGUICommon.AddGridboxStretchSpacer( self._migration_panel, gridbox )
        
        self._migration_panel.Add( gridbox )
        
        #
        
        message = 'The content from the SOURCE that the FILTER ALLOWS is applied using the ACTION to the DESTINATION.'
        message += '\n' * 2
        message += 'To delete content en masse from one location, select what you want to delete with the filter and set the source and destination the same.'
        message += '\n' * 2
        message += 'These migrations can be powerful, so be very careful that you understand what you are doing and choose what you want. Large jobs may have a significant initial setup time, during which case the client may hang briefly, but once they start they are pausable or cancellable. If you do want to perform a large action, it is a good idea to back up your database first, just in case you get a result you did not intend.'
        message += '\n' * 2
        message += 'You may need to restart your client to see their effect.' 
        
        st = ClientGUICommon.BetterStaticText( self, message )
        st.setWordWrap( True )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._migration_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #vbox.addStretch( 1 )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._migration_content_type.SetValue( HC.CONTENT_TYPE_MAPPINGS )
        
        self._UpdateMigrationControlsNewType()
        
        self._migration_content_type.activated.connect( self._UpdateMigrationControlsNewType )
        self._migration_source.activated.connect( self._UpdateMigrationControlsNewSource )
        self._migration_destination.activated.connect( self._UpdateMigrationControlsNewDestination )
        self._migration_source_content_status_filter.activated.connect( self._UpdateMigrationControlsActions )
        self._migration_source_file_filtering_type.activated.connect( self._UpdateMigrationControlsFileFilter )
        
    
    def _MigrationGo( self ):
        
        extra_info = ''
        
        source_content_statuses_strings = {
            ( HC.CONTENT_STATUS_CURRENT, ) : 'current',
            ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING ) : 'current and pending',
            ( HC.CONTENT_STATUS_PENDING, ) : 'pending',
            ( HC.CONTENT_STATUS_DELETED, ) : 'deleted'
        }
        
        destination_action_strings = {
            HC.CONTENT_UPDATE_ADD : 'adding them to',
            HC.CONTENT_UPDATE_DELETE : 'deleting them from',
            HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD : 'clearing their deletion record from',
            HC.CONTENT_UPDATE_PEND : 'pending them to',
            HC.CONTENT_UPDATE_PETITION : 'petitioning them for removal from'
        }
        
        content_type = self._migration_content_type.GetValue()
        content_statuses = self._migration_source_content_status_filter.GetValue()
        
        destination_service_key = self._migration_destination.GetValue()
        source_service_key = self._migration_source.GetValue()
        
        if content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            if destination_service_key == self.HTA_SERVICE_KEY:
                
                if self._dest_archive_path is None:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'Please set a path for the destination Hydrus Tag Archive.' )
                    
                    return
                    
                
                content_action = HC.CONTENT_UPDATE_ADD
                
                desired_hash_type = self._migration_destination_hash_type_choice.GetValue()
                
                destination = ClientMigration.MigrationDestinationHTA( CG.client_controller, self._dest_archive_path, desired_hash_type )
                
            else:
                
                content_action = self._migration_action.GetValue()
                
                desired_hash_type = 'sha256'
                
                destination = ClientMigration.MigrationDestinationTagServiceMappings( CG.client_controller, destination_service_key, content_action )
                
            
            file_filtering_type = self._migration_source_file_filtering_type.GetValue()
            
            if file_filtering_type == self.HASHES_LOCATION:
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY )
                hashes = self._hashes
                
                extra_info = ' for {} files'.format( HydrusData.ToHumanInt( len( hashes ) ) )
                
            else:
                
                location_context = self._migration_source_location_context_button.GetValue()
                hashes = None
                
                if location_context.IsAllKnownFiles():
                    
                    extra_info = ' for all known files'
                    
                else:
                    
                    extra_info = ' for files in "{}"'.format( location_context.ToString( CG.client_controller.services_manager.GetName ) )
                    
                
            
            tag_filter = self._migration_source_tag_filter.GetValue()
            
            extra_info += ' and for tags "{}"'.format( HydrusText.ElideText( tag_filter.ToPermittedString(), 96 ) )
            
            if source_service_key == self.HTA_SERVICE_KEY:
                
                if self._source_archive_path is None:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'Please set a path for the source Hydrus Tag Archive.' )
                    
                    return
                    
                
                source = ClientMigration.MigrationSourceHTA( CG.client_controller, self._source_archive_path, location_context, desired_hash_type, hashes, tag_filter )
                
            else:
                
                source = ClientMigration.MigrationSourceTagServiceMappings( CG.client_controller, source_service_key, location_context, desired_hash_type, hashes, tag_filter, content_statuses )
                
            
        else:
            
            if destination_service_key == self.HTPA_SERVICE_KEY:
                
                if self._dest_archive_path is None:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'Please set a path for the destination Hydrus Tag Pair Archive.' )
                    
                    return
                    
                
                content_action = HC.CONTENT_UPDATE_ADD
                
                destination = ClientMigration.MigrationDestinationHTPA( CG.client_controller, self._dest_archive_path, content_type )
                
            else:
                
                content_action = self._migration_action.GetValue()
                
                destination = ClientMigration.MigrationDestinationTagServicePairs( CG.client_controller, destination_service_key, content_action, content_type )
                
            
            left_tag_pair_filter = self._migration_source_left_tag_pair_filter.GetValue()
            right_tag_pair_filter = self._migration_source_right_tag_pair_filter.GetValue()
            
            left_s = left_tag_pair_filter.ToPermittedString()
            right_s = right_tag_pair_filter.ToPermittedString()
            
            if left_s == right_s:
                
                extra_info = ' for "{}" on both sides'.format( left_s )
                
            else:
                
                extra_info = ' for "{}" on the left and "{}" on the right'.format( left_s, right_s )
                
            
            if source_service_key == self.HTPA_SERVICE_KEY:
                
                if self._source_archive_path is None:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'Please set a path for the source Hydrus Tag Archive.' )
                    
                    return
                    
                
                source = ClientMigration.MigrationSourceHTPA( CG.client_controller, self._source_archive_path, left_tag_pair_filter, right_tag_pair_filter )
                
            else:
                
                source = ClientMigration.MigrationSourceTagServicePairs( CG.client_controller, source_service_key, content_type, left_tag_pair_filter, right_tag_pair_filter, content_statuses )
                
            
        
        title = 'taking {} {}{} from "{}" and {} "{}"'.format( source_content_statuses_strings[ content_statuses ], HC.content_type_string_lookup[ content_type ], extra_info, source.GetName(), destination_action_strings[ content_action ], destination.GetName() )
        
        message = 'Migrations can make huge changes. They can be cancelled early, but any work they do cannot always be undone. Please check that this summary looks correct:'
        message += '\n' * 2
        message += title
        message += '\n' * 2
        message += 'If you plan to make a very big change (especially a mass delete), I recommend making a backup of your database before going ahead, just in case something unexpected happens.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'looks good', no_label = 'go back' )
        
        if result == QW.QDialog.Accepted:
            
            if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                
                do_it = True
                
            else:
                
                message = 'Are you absolutely sure you set up the filters and everything how you wanted? Last chance to turn back.'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                do_it = result == QW.QDialog.Accepted
                
            
            if do_it:
                
                migration_job = ClientMigration.MigrationJob( CG.client_controller, title, source, destination )
                
                CG.client_controller.CallToThread( migration_job.Run )
                
            
        
    
    def _SetDestinationArchivePath( self ):
        
        message = 'Select the destination location for the Archive. Existing Archives are also ok, and will be appended to.'
        
        with QP.FileDialog( self, message = message, acceptMode = QW.QFileDialog.AcceptSave, default_filename = 'archive.db', fileMode = QW.QFileDialog.AnyFile ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                if os.path.exists( path ):
                    
                    content_type = self._migration_content_type.GetValue()
                    
                    if content_type == HC.CONTENT_TYPE_MAPPINGS:
                        
                        try:
                            
                            hta = HydrusTagArchive.HydrusTagArchive( path )
                            
                        except Exception as e:
                            
                            ClientGUIDialogsMessage.ShowCritical( self, 'Problem with HTA!', f'Could not load that path as an Archive!\n\n{e}' )
                            
                        
                        try:
                            
                            hash_type = hta.GetHashType()
                            
                            self._dest_archive_hash_type_override = hash_type
                            
                            self._migration_destination_hash_type_choice.SetValue( hash_type )
                            
                            self._migration_destination_hash_type_choice.setEnabled( False )
                            
                        except:
                            
                            pass
                            
                        
                    else:
                        
                        try:
                            
                            hta = HydrusTagArchive.HydrusTagPairArchive( path )
                            
                            pair_type = hta.GetPairType()
                            
                        except Exception as e:
                            
                            ClientGUIDialogsMessage.ShowCritical( self, 'Problem!', f'Could not load that file as a Hydrus Tag Pair Archive! {e}' )
                            
                            return
                            
                        
                        if content_type == HC.CONTENT_TYPE_TAG_PARENTS and pair_type != HydrusTagArchive.TAG_PAIR_TYPE_PARENTS:
                            
                            ClientGUIDialogsMessage.ShowWarning( self, 'This Hydrus Tag Pair Archive is not a tag parents archive!' )
                            
                            return
                            
                        elif content_type == HC.CONTENT_TYPE_TAG_SIBLINGS and pair_type != HydrusTagArchive.TAG_PAIR_TYPE_SIBLINGS:
                            
                            ClientGUIDialogsMessage.ShowWarning( self, 'This Hydrus Tag Pair Archive is not a tag siblings archive!' )
                            
                            return
                            
                        
                        
                    
                else:
                    
                    self._migration_destination_hash_type_choice.setEnabled( True )
                    
                
                self._dest_archive_path = path
                
                filename = os.path.basename( self._dest_archive_path )
                
                self._migration_destination_archive_path_button.setText( filename )
                
                self._migration_destination_archive_path_button.setToolTip( ClientGUIFunctions.WrapToolTip( path ) )
                
            
        
    
    def _SetSourceArchivePath( self ):
        
        message = 'Select the Archive to pull data from.'
        
        with QP.FileDialog( self, message = message, acceptMode = QW.QFileDialog.AcceptOpen ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                content_type = self._migration_content_type.GetValue()
                
                if content_type == HC.CONTENT_TYPE_MAPPINGS:
                    
                    try:
                        
                        hta = HydrusTagArchive.HydrusTagArchive( path )
                        
                        hash_type = hta.GetHashType()
                        
                    except Exception as e:
                        
                        ClientGUIDialogsMessage.ShowCritical( self, 'Problem!', f'Could not load that file as a Hydrus Tag Archive! {e}' )
                        
                        return
                        
                    
                    hash_type_str = HydrusTagArchive.hash_type_to_str_lookup[ hash_type ]
                    
                    self._migration_source_hash_type_st.setText( 'hash type: {}'.format(hash_type_str) )
                    
                else:
                    
                    try:
                        
                        hta = HydrusTagArchive.HydrusTagPairArchive( path )
                        
                        pair_type = hta.GetPairType()
                        
                    except Exception as e:
                        
                        ClientGUIDialogsMessage.ShowCritical( self, 'Problem!', f'Could not load that file as a Hydrus Tag Pair Archive! {e}' )
                        
                        return
                        
                    
                    if pair_type is None:
                        
                        ClientGUIDialogsMessage.ShowWarning( self, 'This Hydrus Tag Pair Archive does not have a pair type set!' )
                        
                        return
                        
                    
                    if content_type == HC.CONTENT_TYPE_TAG_PARENTS and pair_type != HydrusTagArchive.TAG_PAIR_TYPE_PARENTS:
                        
                        ClientGUIDialogsMessage.ShowWarning( self, 'This Hydrus Tag Pair Archive is not a tag parents archive!' )
                        
                        return
                        
                    elif content_type == HC.CONTENT_TYPE_TAG_SIBLINGS and pair_type != HydrusTagArchive.TAG_PAIR_TYPE_SIBLINGS:
                        
                        ClientGUIDialogsMessage.ShowWarning( self, 'This Hydrus Tag Pair Archive is not a tag siblings archive!' )
                        
                        return
                        
                    
                
                self._source_archive_path = path
                
                filename = os.path.basename( self._source_archive_path )
                
                self._migration_source_archive_path_button.setText( filename )
                
                self._migration_source_archive_path_button.setToolTip( ClientGUIFunctions.WrapToolTip( path ) )
                
            
        
    
    def _UpdateMigrationControlsActions( self ):
        
        content_type = self._migration_content_type.GetValue()
        
        self._migration_action.clear()
        
        source = self._migration_source.GetValue()
        destination = self._migration_destination.GetValue()
        
        tag_status = self._migration_source_content_status_filter.GetValue()
        
        source_and_destination_the_same = source == destination
        
        pulling_and_pushing_existing = source_and_destination_the_same and HC.CONTENT_STATUS_CURRENT in tag_status
        pulling_and_pushing_deleted = source_and_destination_the_same and HC.CONTENT_STATUS_DELETED in tag_status
        
        actions = []
        
        if destination in ( self.HTA_SERVICE_KEY, self.HTPA_SERVICE_KEY ):
            
            actions.append( HC.CONTENT_UPDATE_ADD )
            
        else:
            
            destination_service = CG.client_controller.services_manager.GetService( destination )
            
            destination_service_type = destination_service.GetServiceType()
            
            if destination_service_type == HC.LOCAL_TAG:
                
                if not pulling_and_pushing_existing:
                    
                    actions.append( HC.CONTENT_UPDATE_ADD )
                    
                
                if not pulling_and_pushing_deleted:
                    
                    actions.append( HC.CONTENT_UPDATE_DELETE )
                    
                
                if not pulling_and_pushing_existing and content_type == HC.CONTENT_TYPE_MAPPINGS:
                    
                    actions.append( HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD )
                    
                
            elif destination_service_type == HC.TAG_REPOSITORY:
                
                if not pulling_and_pushing_existing:
                    
                    actions.append( HC.CONTENT_UPDATE_PEND )
                    
                
                if not pulling_and_pushing_deleted:
                    
                    actions.append( HC.CONTENT_UPDATE_PETITION )
                    
                
            
        
        for action in actions:
            
            self._migration_action.addItem( HC.content_update_string_lookup[ action ], action )
            
        
        if len( actions ) > 1:
            
            self._migration_action.setEnabled( True )
            
        else:
            
            self._migration_action.setEnabled( False )
            
        
    
    def _UpdateMigrationControlsFileFilter( self ):
        
        self._migration_source_file_filtering_type.setVisible( self._migration_source_file_filtering_type.count() > 1 )
        self._migration_source_location_context_button.setVisible( self._migration_source_file_filtering_type.GetValue() == self.LOCATION_CONTEXT_LOCATION )
        
    
    def _UpdateMigrationControlsNewDestination( self ):
        
        destination = self._migration_destination.GetValue()
        
        if destination in ( self.HTA_SERVICE_KEY, self.HTPA_SERVICE_KEY ):
            
            self._migration_destination_archive_path_button.show()
            
            if destination == self.HTA_SERVICE_KEY:
                
                self._migration_destination_hash_type_choice_st.show()
                self._migration_destination_hash_type_choice.show()
                
            else:
                
                self._migration_destination_hash_type_choice_st.hide()
                self._migration_destination_hash_type_choice.hide()
                
            
        else:
            
            self._migration_destination_archive_path_button.hide()
            self._migration_destination_hash_type_choice_st.hide()
            self._migration_destination_hash_type_choice.hide()
        
        self._UpdateMigrationControlsActions()
        
    
    def _UpdateMigrationControlsNewSource( self ):
        
        source = self._migration_source.GetValue()
        
        self._migration_source_content_status_filter.clear()
        
        if source in ( self.HTA_SERVICE_KEY, self.HTPA_SERVICE_KEY ):
            
            self._migration_source_archive_path_button.show()
            
            if source == self.HTA_SERVICE_KEY:
                
                self._migration_source_hash_type_st.show()
                
            else:
                
                self._migration_source_hash_type_st.hide()
                
            
            self._migration_source_content_status_filter.addItem( 'current', ( HC.CONTENT_STATUS_CURRENT, ) )
            
            self._migration_source_content_status_filter.setEnabled( False )
            
        else:
            
            self._migration_source_archive_path_button.hide()
            self._migration_source_hash_type_st.hide()
            
            source_service = CG.client_controller.services_manager.GetService( source )
            
            source_service_type = source_service.GetServiceType()
            
            self._migration_source_content_status_filter.addItem( 'current', ( HC.CONTENT_STATUS_CURRENT, ) )
            
            if source_service_type == HC.TAG_REPOSITORY:
                
                self._migration_source_content_status_filter.addItem( 'current and pending', ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING ) )
                self._migration_source_content_status_filter.addItem( 'pending', ( HC.CONTENT_STATUS_PENDING, ) )
                
            
            self._migration_source_content_status_filter.addItem( 'deleted', ( HC.CONTENT_STATUS_DELETED, ) )
            
            self._migration_source_content_status_filter.setEnabled( True )
            
        
        self._UpdateMigrationControlsActions()
        
    
    def _UpdateMigrationControlsNewType( self ):
        
        content_type = self._migration_content_type.GetValue()
        
        self._migration_source.clear()
        self._migration_destination.clear()
        
        for service in CG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES ):
            
            self._migration_source.addItem( service.GetName(), service.GetServiceKey() )
            self._migration_destination.addItem( service.GetName(), service.GetServiceKey() )
            
        
        self._source_archive_path = None
        self._source_archive_hash_type = None
        self._dest_archive_path = None
        self._dest_archive_hash_type_override = None
        
        self._migration_source_hash_type_st.setText( 'hash type: unknown' )
        self._migration_destination_hash_type_choice.SetValue( 'sha256' )
        self._migration_destination_hash_type_choice.setEnabled( True )
        
        self._migration_source_archive_path_button.setText( 'no path set' )
        self._migration_source_archive_path_button.setToolTip( ClientGUIFunctions.WrapToolTip( '' ) )
        
        self._migration_destination_archive_path_button.setText( 'no path set' )
        self._migration_destination_archive_path_button.setToolTip( ClientGUIFunctions.WrapToolTip( '' ) )
        
        if content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            self._migration_source.addItem( 'Hydrus Tag Archive', self.HTA_SERVICE_KEY )
            self._migration_destination.addItem( 'Hydrus Tag Archive', self.HTA_SERVICE_KEY )
            self._migration_source_tag_filter.show()
            self._migration_source_left_tag_pair_filter.hide()
            self._migration_source_right_tag_pair_filter.hide()
            
            self._UpdateMigrationControlsFileFilter()
            
        elif content_type in ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ):
            
            self._migration_source.addItem( 'Hydrus Tag Pair Archive', self.HTPA_SERVICE_KEY )
            self._migration_destination.addItem( 'Hydrus Tag Pair Archive', self.HTPA_SERVICE_KEY )
            
            self._migration_source_file_filtering_type.hide()
            self._migration_source_location_context_button.hide()
            self._migration_source_tag_filter.hide()
            self._migration_source_left_tag_pair_filter.show()
            self._migration_source_right_tag_pair_filter.show()
            
        
        self._migration_source.SetValue( self._service_key )
        self._migration_destination.SetValue( self._service_key )
        
        self._UpdateMigrationControlsNewSource()
        self._UpdateMigrationControlsNewDestination()
        
    
