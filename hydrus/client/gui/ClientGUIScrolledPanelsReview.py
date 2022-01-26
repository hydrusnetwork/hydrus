import collections
import os
import queue
import sys
import threading
import time
import traceback

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusCompression
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusFileHandling
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusTagArchive
from hydrus.core import HydrusText
from hydrus.core import HydrusThreading

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientFiles
from hydrus.client import ClientLocation
from hydrus.client import ClientMigration
from hydrus.client import ClientParsing
from hydrus.client import ClientPaths
from hydrus.client import ClientRendering
from hydrus.client import ClientSearch
from hydrus.client import ClientSerialisable
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIDragDrop
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIImport
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIPopupMessages
from hydrus.client.gui import ClientGUITags
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.metadata import ClientTags
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingGUG
from hydrus.client.networking import ClientNetworkingLogin
from hydrus.client.networking import ClientNetworkingURLClass

class MigrateDatabasePanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller ):
        
        self._controller = controller
        
        self._new_options = self._controller.new_options
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._prefixes_to_locations = HG.client_controller.Read( 'client_files_locations' )
        
        ( self._locations_to_ideal_weights, self._ideal_thumbnails_location_override ) = self._controller.Read( 'ideal_client_files_locations' )
        
        service_info = HG.client_controller.Read( 'service_info', CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
        
        self._all_local_files_total_size = service_info[ HC.SERVICE_INFO_TOTAL_SIZE ]
        self._all_local_files_total_num = service_info[ HC.SERVICE_INFO_NUM_FILES ]
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'database_migration.html' ) )
        
        menu_items.append( ( 'normal', 'open the html migration help', 'Open the help page for database migration in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        info_panel = ClientGUICommon.StaticBox( self, 'database components' )
        
        self._current_install_path_st = ClientGUICommon.BetterStaticText( info_panel )
        self._current_db_path_st = ClientGUICommon.BetterStaticText( info_panel )
        self._current_media_paths_st = ClientGUICommon.BetterStaticText( info_panel )
        
        file_locations_panel = ClientGUICommon.StaticBox( self, 'media file locations' )
        
        current_media_locations_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( file_locations_panel )
        
        self._current_media_locations_listctrl = ClientGUIListCtrl.BetterListCtrl( current_media_locations_listctrl_panel, CGLC.COLUMN_LIST_DB_MIGRATION_LOCATIONS.ID, 8, self._ConvertLocationToListCtrlTuples )
        self._current_media_locations_listctrl.setSelectionMode( QW.QAbstractItemView.SingleSelection )
        
        self._current_media_locations_listctrl.Sort()
        
        current_media_locations_listctrl_panel.SetListCtrl( self._current_media_locations_listctrl )
        
        current_media_locations_listctrl_panel.AddButton( 'add new location for files', self._SelectPathToAdd )
        current_media_locations_listctrl_panel.AddButton( 'increase location weight', self._IncreaseWeight, enabled_check_func = self._CanIncreaseWeight )
        current_media_locations_listctrl_panel.AddButton( 'decrease location weight', self._DecreaseWeight, enabled_check_func = self._CanDecreaseWeight )
        current_media_locations_listctrl_panel.AddButton( 'remove location', self._RemoveSelectedPath, enabled_check_func = self._CanRemoveLocation )
        
        self._thumbnails_location = QW.QLineEdit( file_locations_panel )
        self._thumbnails_location.setEnabled( False )
        
        self._thumbnails_location_set = ClientGUICommon.BetterButton( file_locations_panel, 'set', self._SetThumbnailLocation )
        
        self._thumbnails_location_clear = ClientGUICommon.BetterButton( file_locations_panel, 'clear', self._ClearThumbnailLocation )
        
        self._rebalance_status_st = ClientGUICommon.BetterStaticText( file_locations_panel )
        self._rebalance_status_st.setAlignment( QC.Qt.AlignRight | QC.Qt.AlignVCenter )
        
        self._rebalance_button = ClientGUICommon.BetterButton( file_locations_panel, 'move files now', self._Rebalance )
        
        #
        
        migration_panel = ClientGUICommon.StaticBox( self, 'migrate database files (and portable media file locations)' )
        
        self._migrate_db_button = ClientGUICommon.BetterButton( migration_panel, 'move entire database and all portable paths', self._MigrateDatabase )
        
        #
        
        info_panel.Add( self._current_install_path_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.Add( self._current_db_path_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.Add( self._current_media_paths_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        t_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( t_hbox, ClientGUICommon.BetterStaticText( file_locations_panel, 'thumbnail location override' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( t_hbox, self._thumbnails_location, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( t_hbox, self._thumbnails_location_set, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( t_hbox, self._thumbnails_location_clear, CC.FLAGS_CENTER_PERPENDICULAR )
        
        rebalance_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( rebalance_hbox, self._rebalance_status_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( rebalance_hbox, self._rebalance_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        file_locations_panel.Add( current_media_locations_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        file_locations_panel.Add( t_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        file_locations_panel.Add( rebalance_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        migration_panel.Add( self._migrate_db_button, CC.FLAGS_ON_RIGHT )
        
        #
        
        vbox = QP.VBoxLayout()
        
        message = 'THIS IS ADVANCED. DO NOT CHANGE ANYTHING HERE UNLESS YOU KNOW WHAT IT DOES!'
        
        warning_st = ClientGUICommon.BetterStaticText( self, label = message )
        
        warning_st.setObjectName( 'HydrusWarning' )
        
        QP.AddToLayout( vbox, warning_st, CC.FLAGS_CENTER )
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, file_locations_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, migration_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 100 )
        
        self.setMinimumWidth( min_width )
        
        self._Update()
        
    
    def _AddPath( self, path, starting_weight = 1 ):
        
        path = os.path.realpath( path )
        
        if path in self._locations_to_ideal_weights:
            
            QW.QMessageBox.warning( self, 'Warning', 'You already have that location entered!' )
            
            return
            
        
        if path == self._ideal_thumbnails_location_override:
            
            QW.QMessageBox.warning( self, 'Warning', 'That path is already used as the special thumbnail location--please choose another.' )
            
            return
            
        
        self._locations_to_ideal_weights[ path ] = 1
        
        self._controller.Write( 'ideal_client_files_locations', self._locations_to_ideal_weights, self._ideal_thumbnails_location_override )
        
        self._Update()
        
    
    def _AdjustWeight( self, amount ):
        
        adjustees = set()
        
        locations = self._current_media_locations_listctrl.GetData( only_selected = True )
        
        if len( locations ) > 0:
            
            location = locations[0]
            
            if location in self._locations_to_ideal_weights:
                
                current_weight = self._locations_to_ideal_weights[ location ]
                
                new_amount = current_weight + amount
                
                if new_amount > 0:
                    
                    self._locations_to_ideal_weights[ location ] = new_amount
                    
                    self._controller.Write( 'ideal_client_files_locations', self._locations_to_ideal_weights, self._ideal_thumbnails_location_override )
                    
                elif new_amount <= 0:
                    
                    self._RemovePath( location )
                    
                
            else:
                
                if amount > 0:
                    
                    if location != self._ideal_thumbnails_location_override:
                        
                        self._AddPath( location, starting_weight = amount )
                        
                    
                
                
            
            self._Update()
            
        
    
    def _CanDecreaseWeight( self ):
        
        locations = self._current_media_locations_listctrl.GetData( only_selected = True )
        
        if len( locations ) > 0:
            
            location = locations[0]
            
            if location in self._locations_to_ideal_weights:
                
                ideal_weight = self._locations_to_ideal_weights[ location ]
                
                is_big = ideal_weight > 1
                others_can_take_slack = len( self._locations_to_ideal_weights ) > 1
                
                if is_big or others_can_take_slack:
                    
                    return True
                    
                
            
        
        return False
        
    
    def _CanIncreaseWeight( self ):
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        locations = self._current_media_locations_listctrl.GetData( only_selected = True )
        
        if len( locations ) > 0:
            
            location = locations[0]
            
            if location in self._locations_to_ideal_weights:
                
                if len( self._locations_to_ideal_weights ) > 1:
                    
                    return True
                    
                
            elif location in locations_to_file_weights:
                
                return True
                
            
        
        return False
        
    
    def _CanRemoveLocation( self ):
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        locations = self._current_media_locations_listctrl.GetData( only_selected = True )
        
        if len( locations ) > 0:
            
            location = locations[0]
            
            if location in self._locations_to_ideal_weights:
                
                others_can_take_slack = len( self._locations_to_ideal_weights ) > 1
                
                if others_can_take_slack:
                    
                    return True
                    
                
            
        
        return False
        
    
    def _ClearThumbnailLocation( self ):
        
        self._ideal_thumbnails_location_override = None
        
        self._controller.Write( 'ideal_client_files_locations', self._locations_to_ideal_weights, self._ideal_thumbnails_location_override )
        
        self._Update()
        
    
    def _ConvertLocationToListCtrlTuples( self, location ):
        
        f_space = self._all_local_files_total_size
        t_space = self._GetThumbnailSizeEstimate()
        
        # current
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        #
        
        pretty_location = location
        
        if os.path.exists( location ):
            
            pretty_location = location
            
            try:
                
                free_space = HydrusPaths.GetFreeSpace( location )
                pretty_free_space = HydrusData.ToHumanBytes( free_space )
                
            except Exception as e:
                
                message = 'There was a problem finding the free space for "' + location + '"! Perhaps this location does not exist?'
                
                HydrusData.Print( message )
                
                HydrusData.PrintException( e )
                
                free_space = 0
                pretty_free_space = 'problem finding free space'
                
            
        else:
            
            pretty_location = 'DOES NOT EXIST: {}'.format( location )
            
            free_space = 0
            pretty_free_space = 'DOES NOT EXIST'
            
        
        portable_location = HydrusPaths.ConvertAbsPathToPortablePath( location )
        portable = not os.path.isabs( portable_location )
        
        if portable:
            
            pretty_portable = 'yes'
            
        else:
            
            pretty_portable = 'no'
            
        
        fp = locations_to_file_weights[ location ] / 256.0
        tp = locations_to_thumb_weights[ location ] / 256.0
        
        p = HydrusData.ConvertFloatToPercentage
        
        current_bytes = fp * f_space + tp * t_space
        
        current_usage = ( fp, tp )
        
        usages = []
        
        if fp > 0:
            
            usages.append( p( fp ) + ' files' )
            
        
        if tp > 0:
            
            usages.append( p( tp ) + ' thumbnails' )
            
        
        if len( usages ) > 0:
            
            if fp == tp:
                
                usages = [ p( fp ) + ' everything' ]
                
            
            pretty_current_usage = HydrusData.ToHumanBytes( current_bytes ) + ' - ' + ','.join( usages )
            
        else:
            
            pretty_current_usage = 'nothing'
            
        
        #
        
        total_ideal_weight = sum( self._locations_to_ideal_weights.values() )
        
        if location in self._locations_to_ideal_weights:
            
            ideal_weight = self._locations_to_ideal_weights[ location ]
            
            pretty_ideal_weight = str( int( ideal_weight ) )
            
        else:
            
            ideal_weight = 0
            
            if location in locations_to_file_weights:
                
                pretty_ideal_weight = '0'
                
            else:
                
                pretty_ideal_weight = 'n/a'
                
            
        
        if location in self._locations_to_ideal_weights:
            
            ideal_fp = self._locations_to_ideal_weights[ location ] / total_ideal_weight
            
        else:
            
            ideal_fp = 0.0
            
        
        if self._ideal_thumbnails_location_override is None:
            
            ideal_tp = ideal_fp
            
        else:
            
            if location == self._ideal_thumbnails_location_override:
                
                ideal_tp = 1.0
                
            else:
                
                ideal_tp = 0.0
                
            
        
        ideal_bytes = ideal_fp * f_space + ideal_tp * t_space
        
        ideal_usage = ( ideal_fp, ideal_tp )
        
        usages = []
        
        if ideal_fp > 0:
            
            usages.append( p( ideal_fp ) + ' files' )
            
        
        if ideal_tp > 0:
            
            usages.append( p( ideal_tp ) + ' thumbnails' )
            
        
        if len( usages ) > 0:
            
            if ideal_fp == ideal_tp:
                
                usages = [ p( ideal_fp ) + ' everything' ]
                
            
            pretty_ideal_usage = HydrusData.ToHumanBytes( ideal_bytes ) + ' - ' + ','.join( usages )
            
        else:
            
            pretty_ideal_usage = 'nothing'
            
        
        display_tuple = ( pretty_location, pretty_portable, pretty_free_space, pretty_current_usage, pretty_ideal_weight, pretty_ideal_usage )
        sort_tuple = ( location, portable, free_space, ideal_weight, ideal_usage, current_usage )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DecreaseWeight( self ):
        
        self._AdjustWeight( -1 )
        
    
    def _GetLocationsToCurrentWeights( self ):
        
        locations_to_file_weights = collections.Counter()
        locations_to_thumb_weights = collections.Counter()
        
        for ( prefix, location ) in list(self._prefixes_to_locations.items()):
            
            if prefix.startswith( 'f' ):
                
                locations_to_file_weights[ location ] += 1
                
            
            if prefix.startswith( 't' ):
                
                locations_to_thumb_weights[ location ] += 1
                
            
        
        return ( locations_to_file_weights, locations_to_thumb_weights )
        
    
    def _GetListCtrlLocations( self ):
        
        # current
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        #
        
        all_locations = set()
        
        all_locations.update( list(self._locations_to_ideal_weights.keys()) )
        
        if self._ideal_thumbnails_location_override is not None:
            
            all_locations.add( self._ideal_thumbnails_location_override )
            
        
        all_locations.update( list(locations_to_file_weights.keys()) )
        all_locations.update( list(locations_to_thumb_weights.keys()) )
        
        all_locations = list( all_locations )
        
        return all_locations
        
    
    def _GetThumbnailSizeEstimate( self ):
        
        ( t_width, t_height ) = HG.client_controller.options[ 'thumbnail_dimensions' ]
        
        typical_thumb_num_pixels = 320 * 240
        typical_thumb_size = 36 * 1024
        
        our_thumb_num_pixels = t_width * t_height
        our_thumb_size_estimate = typical_thumb_size * ( our_thumb_num_pixels / typical_thumb_num_pixels )
        
        our_total_thumb_size_estimate = self._all_local_files_total_num * our_thumb_size_estimate
        
        return our_total_thumb_size_estimate
        
    
    def _IncreaseWeight( self ):
        
        self._AdjustWeight( 1 )
        
    
    def _MigrateDatabase( self ):
        
        message = 'This operation will move your database files and any \'portable\' paths. It is a big job that will require a client shutdown and need you to create a new shortcut before you can launch it again.'
        message += os.linesep * 2
        message += 'If you have not read the database migration help or otherwise do not know what is going on here, turn back now!'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            source = self._controller.GetDBDir()
            
            with QP.DirDialog( self, message = 'Choose new database location.' ) as dlg:
                
                dlg.setDirectory( source )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    dest = dlg.GetPath()
                    
                    if source == dest:
                        
                        QW.QMessageBox.warning( self, 'Warning', 'That is the same location!' )
                        
                        return
                        
                    
                    if len( os.listdir( dest ) ) > 0:
                        
                        message = '"{}" is not empty! Please select an empty destination--if your situation is more complicated, please do this move manually! Feel free to ask hydrus dev for help.'.format( dest )
                        
                        result = ClientGUIDialogsQuick.GetYesNo( self, message )
                        
                        if result != QW.QDialog.Accepted:
                            
                            return
                            
                        
                    
                    message = 'Here is the client\'s best guess at your new launch command. Make sure it looks correct and copy it to your clipboard. Update your program shortcut when the transfer is complete.'
                    message += os.linesep * 2
                    message += 'Hit ok to close the client and start the transfer, cancel to back out.'
                    
                    me = sys.argv[0]
                    
                    shortcut = '"' + me + '" -d="' + dest + '"'
                    
                    with ClientGUIDialogs.DialogTextEntry( self, message, default = shortcut ) as dlg_3:
                        
                        if dlg_3.exec() == QW.QDialog.Accepted:
                            
                            # The below comment is from before the Qt port and probably obsolote, leaving it for explanation.
                            #
                            # careful with this stuff!
                            # the app's mainloop didn't want to exit for me, for a while, because this dialog didn't have time to exit before the thread's dialog laid a new event loop on top
                            # the confused event loops lead to problems at a C++ level in ShowModal not being able to do the Destroy because parent stuff had already died
                            # this works, so leave it alone if you can
                            
                            QP.CallAfter( self.parentWidget().close )
                            
                            portable_locations = []
                            
                            for location in set( self._prefixes_to_locations.values() ):
                                
                                if not os.path.exists( location ):
                                    
                                    continue
                                    
                                
                                portable_location = HydrusPaths.ConvertAbsPathToPortablePath( location )
                                portable = not os.path.isabs( portable_location )
                                
                                if portable:
                                    
                                    portable_locations.append( portable_location )
                                    
                                
                            
                            HG.client_controller.CallToThreadLongRunning( THREADMigrateDatabase, self._controller, source, portable_locations, dest )
                            
                        
                    
                
            
        
    
    def _Rebalance( self ):
        
        for location in self._GetListCtrlLocations():
            
            if not os.path.exists( location ):
                
                message = 'The path "{}" does not exist! Please ensure all the locations on this dialog are valid before trying to rebalance your files.'.format( location )
                
                QW.QMessageBox.critical( self, 'Error', message )
                
                return
                
            
        
        
        message = 'Moving files can be a slow and slightly laggy process, with the UI intermittently hanging, which sometimes makes manually stopping a large ongoing job difficult. Would you like to set a max runtime on this job?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'run for 10 minutes', 600 ) )
        yes_tuples.append( ( 'run for 30 minutes', 1800 ) )
        yes_tuples.append( ( 'run for 1 hour', 3600 ) )
        yes_tuples.append( ( 'run indefinitely', None ) )
        
        with ClientGUIDialogs.DialogYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                value = dlg.GetValue()
                
                if value is None:
                    
                    stop_time = None
                    
                else:
                    
                    stop_time = HydrusData.GetNow() + value
                    
                
                job_key = ClientThreading.JobKey( cancellable = True, stop_time = stop_time )
                
            else:
                
                return
                
            
        
        HG.client_controller.pub( 'do_file_storage_rebalance', job_key )
        
        self._OKParent()
        
    
    def _RemovePath( self, location ):
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        removees = set()
        
        if location not in self._locations_to_ideal_weights:
            
            QW.QMessageBox.warning( self, 'Warning', 'Please select a location with weight.' )
            
            return
            
        
        if len( self._locations_to_ideal_weights ) == 1:
            
            QW.QMessageBox.warning( self, 'Warning', 'You cannot empty every single current file location--please add a new place for the files to be moved to and then try again.' )
            
        
        if os.path.exists( location ):
            
            if location in locations_to_file_weights:
                
                message = 'Are you sure you want to remove this location? This will schedule all of the files it is currently responsible for to be moved elsewhere.'
                
            else:
                
                message = 'Are you sure you want to remove this location?'
                
            
        else:
            
            if location in locations_to_file_weights:
                
                message = 'This path does not exist, but it seems to have files. This could be a critical error that has occurred while the client is open (maybe a drive unmounting?). I recommend you do not remove it here and instead shut the client down immediately and fix the problem, then restart it, which will run the \'recover missing file locations\' routine if needed.'
                
            else:
                
                message = 'This path does not exist. Just checking, but I recommend you remove it.'
                
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            del self._locations_to_ideal_weights[ location ]
            
            self._controller.Write( 'ideal_client_files_locations', self._locations_to_ideal_weights, self._ideal_thumbnails_location_override )
            
            self._Update()
            
        
    
    def _RemoveSelectedPath( self ):
        
        locations = self._current_media_locations_listctrl.GetData( only_selected = True )
        
        if len( locations ) > 0:
            
            location = locations[0]
            
            self._RemovePath( location )
            
        
    
    def _SelectPathToAdd( self ):
        
        with QP.DirDialog( self, 'Select location' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                self._AddPath( path )
                
            
        
    
    def _SetThumbnailLocation( self ):
        
        with QP.DirDialog( self, 'Select thumbnail location' ) as dlg:
            
            if self._ideal_thumbnails_location_override is not None:
                
                dlg.setDirectory( self._ideal_thumbnails_location_override )
                
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                path = os.path.realpath( path )
                
                if path in self._locations_to_ideal_weights:
                    
                    QW.QMessageBox.warning( self, 'Warning', 'That path already exists as a regular file location! Please choose another.' )
                    
                else:
                    
                    self._ideal_thumbnails_location_override = path
                    
                    self._controller.Write( 'ideal_client_files_locations', self._locations_to_ideal_weights, self._ideal_thumbnails_location_override )
                    
                    self._Update()
                    
                
            
        
    
    def _Update( self ):
        
        self._prefixes_to_locations = HG.client_controller.Read( 'client_files_locations' )
        
        ( self._locations_to_ideal_weights, self._ideal_thumbnails_location_override ) = self._controller.Read( 'ideal_client_files_locations' )
        
        approx_total_db_size = self._controller.db.GetApproxTotalFileSize()
        
        self._current_db_path_st.setText( 'database (about '+HydrusData.ToHumanBytes(approx_total_db_size)+'): '+self._controller.GetDBDir() )
        self._current_install_path_st.setText( 'install: '+HC.BASE_DIR )
        
        approx_total_client_files = self._all_local_files_total_size
        approx_total_thumbnails = self._GetThumbnailSizeEstimate()
        
        label = 'media is ' + HydrusData.ToHumanBytes( approx_total_client_files ) + ', thumbnails are estimated at ' + HydrusData.ToHumanBytes( approx_total_thumbnails ) + ':'
        
        self._current_media_paths_st.setText( label )
        
        locations = self._GetListCtrlLocations()
        
        self._current_media_locations_listctrl.SetData( locations )
        
        #
        
        if self._ideal_thumbnails_location_override is None:
            
            self._thumbnails_location.setText( 'none set' )
            
            self._thumbnails_location_set.setEnabled( True )
            self._thumbnails_location_clear.setEnabled( False )
            
        else:
            
            self._thumbnails_location.setText( self._ideal_thumbnails_location_override )
            
            self._thumbnails_location_set.setEnabled( False )
            self._thumbnails_location_clear.setEnabled( True )
            
        
        #
        
        if self._controller.client_files_manager.RebalanceWorkToDo():
            
            self._rebalance_button.setEnabled( True )
            
            self._rebalance_status_st.setText( 'files need to be moved' )
            self._rebalance_status_st.setObjectName( 'HydrusInvalid' )
            
        else:
            
            self._rebalance_button.setEnabled( False )
            
            self._rebalance_status_st.setText( 'all files are in their ideal locations' )
            self._rebalance_status_st.setObjectName( 'HydrusValid' )
            
        
        self._rebalance_status_st.style().polish( self._rebalance_status_st )
        
    
def THREADMigrateDatabase( controller, source, portable_locations, dest ):
    
    time.sleep( 2 ) # important to have this, so the migrate dialog can close itself and clean its event loop, wew
    
    def qt_code( job_key ):
        
        HG.client_controller.CallLaterQtSafe( controller.gui, 3.0, 'close program', controller.Exit )
        
        # no parent because this has to outlive the gui, obvs
        
        with ClientGUITopLevelWindowsPanels.DialogNullipotent( None, 'migrating files' ) as dlg:
            
            panel = ClientGUIPopupMessages.PopupMessageDialogPanel( dlg, job_key )
            
            dlg.SetPanel( panel )
            
            dlg.exec()
            
        
    
    db = controller.db
    
    job_key = ClientThreading.JobKey( cancel_on_shutdown = False )
    
    job_key.SetStatusTitle( 'migrating database' )
    
    QP.CallAfter( qt_code, job_key )
    
    try:
        
        job_key.SetVariable( 'popup_text_1', 'waiting for db shutdown' )
        
        while not db.LoopIsFinished():
            
            time.sleep( 1 )
            
        
        job_key.SetVariable( 'popup_text_1', 'doing the move' )
        
        def text_update_hook( text ):
            
            job_key.SetVariable( 'popup_text_1', text )
            
        
        for filename in os.listdir( source ):
            
            if filename.startswith( 'client' ) and filename.endswith( '.db' ):
                
                job_key.SetVariable( 'popup_text_1', 'moving ' + filename )
                
                source_path = os.path.join( source, filename )
                dest_path = os.path.join( dest, filename )
                
                HydrusPaths.MergeFile( source_path, dest_path )
                
            
        
        for portable_location in portable_locations:
            
            source_path = os.path.join( source, portable_location )
            dest_path = os.path.join( dest, portable_location )
            
            HydrusPaths.MergeTree( source_path, dest_path, text_update_hook = text_update_hook )
            
        
        job_key.SetVariable( 'popup_text_1', 'done!' )
        
    except:
        
        QP.CallAfter( QW.QMessageBox.critical, None, 'Error', traceback.format_exc() )
        
        job_key.SetVariable( 'popup_text_1', 'error!' )
        
    finally:
        
        time.sleep( 3 )
        
        job_key.Finish()
        
    
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
    HASHES_SERVICE_KEY = b'hashes'
    
    def __init__( self, parent, service_key, hashes = None ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._service_key = service_key
        self._hashes = hashes
        
        self._source_archive_path = None
        self._source_archive_hash_type = None
        self._dest_archive_path = None
        self._dest_archive_hash_type_override = None
        
        try:
            
            service = HG.client_controller.services_manager.GetService( self._service_key )
            
        except HydrusExceptions.DataMissing:
            
            services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) )
            
            service = next( iter( services ) )
            
            self._service_key = service.GetServiceKey()
            
        
        #
        
        self._migration_panel = ClientGUICommon.StaticBox( self, 'migration' )
        
        self._migration_content_type = ClientGUICommon.BetterChoice( self._migration_panel )
        
        for content_type in ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_TYPE_TAG_SIBLINGS ):
            
            self._migration_content_type.addItem( HC.content_type_string_lookup[ content_type ], content_type )
            
        
        self._migration_content_type.setToolTip( 'Sets what will be migrated.' )
        
        self._migration_source = ClientGUICommon.BetterChoice( self._migration_panel )
        
        self._migration_source_archive_path_button = ClientGUICommon.BetterButton( self._migration_panel, 'no path set', self._SetSourceArchivePath )
        
        self._migration_source_hash_type_st = ClientGUICommon.BetterStaticText( self._migration_panel, 'hash type: unknown' )
        
        self._migration_source_hash_type_st.setToolTip( 'If this is something other than sha256, this will only work for files the client has ever previously imported.' )
        
        self._migration_source_content_status_filter = ClientGUICommon.BetterChoice( self._migration_panel )
        
        self._migration_source_content_status_filter.setToolTip( 'This filters which status of tags will be migrated.' )
        
        self._migration_source_file_filter = ClientGUICommon.BetterChoice( self._migration_panel )
        
        for service_key in ( CC.LOCAL_FILE_SERVICE_KEY, CC.COMBINED_FILE_SERVICE_KEY ):
            
            service = HG.client_controller.services_manager.GetService( service_key )
            
            self._migration_source_file_filter.addItem( service.GetName(), service_key )
            
        
        if self._hashes is not None:
            
            self._migration_source_file_filter.addItem( '{} files'.format( HydrusData.ToHumanInt( len( self._hashes ) ) ), self.HASHES_SERVICE_KEY )
            
            self._migration_source_file_filter.SetValue( self.HASHES_SERVICE_KEY )
            
        
        self._migration_source_file_filter.setToolTip( 'Tags that pass this filter will be applied to the destination with the chosen action.' )
        
        message = 'Tags that pass this filter will be applied to the destination with the chosen action.'
        message += os.linesep * 2
        message += 'For instance, if you whitelist the \'series\' namespace, only series: tags from the source will be added to/deleted from the destination.'
        
        tag_filter = HydrusTags.TagFilter()
        
        self._migration_source_tag_filter = ClientGUITags.TagFilterButton( self._migration_panel, message, tag_filter, label_prefix = 'tags taken: ' )
        
        message = 'The left side of a tag sibling/parent pair must pass this filter for the pair to be included in the migration.'
        message += os.linesep * 2
        message += 'For instance, if you whitelist the \'character\' namespace, only pairs from the source with character: tags on the left will be added to/deleted from the destination.'
        
        tag_filter = HydrusTags.TagFilter()
        
        self._migration_source_left_tag_pair_filter = ClientGUITags.TagFilterButton( self._migration_panel, message, tag_filter, label_prefix = 'left: ' )
        
        message = 'The right side of a tag sibling/parent pair must pass this filter for the pair to be included in the migration.'
        message += os.linesep * 2
        message += 'For instance, if you whitelist the \'series\' namespace, only pairs from the source with series: tags on the right will be added to/deleted from the destination.'
        
        tag_filter = HydrusTags.TagFilter()
        
        self._migration_source_right_tag_pair_filter = ClientGUITags.TagFilterButton( self._migration_panel, message, tag_filter, label_prefix = 'right: ' )
        
        self._migration_destination = ClientGUICommon.BetterChoice( self._migration_panel )
        
        self._migration_destination_archive_path_button = ClientGUICommon.BetterButton( self._migration_panel, 'no path set', self._SetDestinationArchivePath )
        
        self._migration_destination_hash_type_choice_st = ClientGUICommon.BetterStaticText( self._migration_panel, 'hash type: ' )
        
        self._migration_destination_hash_type_choice = ClientGUICommon.BetterChoice( self._migration_panel )
        
        for hash_type in ( 'sha256', 'md5', 'sha1', 'sha512' ):
            
            self._migration_destination_hash_type_choice.addItem( hash_type, hash_type )
            
        
        self._migration_destination_hash_type_choice.setToolTip( 'If you set something other than sha256, this will only work for files the client has ever previously imported.' )
        
        self._migration_action = ClientGUICommon.BetterChoice( self._migration_panel )
        
        self._migration_go = ClientGUICommon.BetterButton( self._migration_panel, 'Go!', self._MigrationGo )
        
        #
        
        file_left_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( file_left_vbox, self._migration_source_file_filter, CC.FLAGS_EXPAND_BOTH_WAYS )
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
        ClientGUICommon.AddGridboxStretchSpacer( gridbox )
        
        QP.AddToLayout( gridbox, self._migration_content_type, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._migration_source, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._migration_source_content_status_filter, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._migration_action, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._migration_destination, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._migration_go, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        ClientGUICommon.AddGridboxStretchSpacer( gridbox )
        QP.AddToLayout( gridbox, self._migration_source_archive_path_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, file_left_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        ClientGUICommon.AddGridboxStretchSpacer( gridbox )
        QP.AddToLayout( gridbox, self._migration_destination_archive_path_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        ClientGUICommon.AddGridboxStretchSpacer( gridbox )
        
        ClientGUICommon.AddGridboxStretchSpacer( gridbox )
        QP.AddToLayout( gridbox, self._migration_source_hash_type_st, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( gridbox, tag_right_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        ClientGUICommon.AddGridboxStretchSpacer( gridbox )
        QP.AddToLayout( gridbox, dest_hash_type_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        ClientGUICommon.AddGridboxStretchSpacer( gridbox )
        
        self._migration_panel.Add( gridbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        message = 'Regarding '
        
        if self._hashes is None:
            
            message += 'all'
            
        else:
            
            message += HydrusData.ToHumanInt( len( self._hashes ) )
            
        
        message = 'The content from the SOURCE that the FILTER ALLOWS is applied using the ACTION to the DESTINATION.'
        message += os.linesep * 2
        message += 'To delete content en masse from one location, select what you want to delete with the filter and set the source and destination the same.'
        message += os.linesep * 2
        message += 'These migrations can be powerful, so be very careful that you understand what you are doing and choose what you want. Large jobs may have a significant initial setup time, during which case the client may hang briefly, but once they start they are pausable or cancellable. If you do want to perform a large action, it is a good idea to back up your database first, just in case you get a result you did not intend.'
        message += os.linesep * 2
        message += 'You may need to restart your client to see their effect.' 
        
        st = ClientGUICommon.BetterStaticText( self, message )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._migration_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._migration_content_type.SetValue( HC.CONTENT_TYPE_MAPPINGS )
        
        self._UpdateMigrationControlsNewType()
        
        self._migration_content_type.activated.connect( self._UpdateMigrationControlsNewType )
        self._migration_source.activated.connect( self._UpdateMigrationControlsNewSource )
        self._migration_destination.activated.connect( self._UpdateMigrationControlsNewDestination )
        self._migration_source_content_status_filter.activated.connect( self._UpdateMigrationControlsActions )
        
    
    def _MigrationGo( self ):
        
        extra_info = ''
        
        source_content_statuses_strings = {}
        
        source_content_statuses_strings[ ( HC.CONTENT_STATUS_CURRENT, ) ] = 'current'
        source_content_statuses_strings[ ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING ) ] = 'current and pending'
        source_content_statuses_strings[ ( HC.CONTENT_STATUS_DELETED, ) ] = 'deleted'
        
        destination_action_strings = {}
        
        destination_action_strings[ HC.CONTENT_UPDATE_ADD ] = 'adding them to'
        destination_action_strings[ HC.CONTENT_UPDATE_DELETE ] = 'deleting them from'
        destination_action_strings[ HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD ] = 'clearing their deletion record from'
        destination_action_strings[ HC.CONTENT_UPDATE_PEND ] = 'pending them to'
        destination_action_strings[ HC.CONTENT_UPDATE_PETITION ] = 'petitioning them for removal from'
        
        content_type = self._migration_content_type.GetValue()
        content_statuses = self._migration_source_content_status_filter.GetValue()
        
        destination_service_key = self._migration_destination.GetValue()
        source_service_key = self._migration_source.GetValue()
        
        if content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            if destination_service_key == self.HTA_SERVICE_KEY:
                
                if self._dest_archive_path is None:
                    
                    QW.QMessageBox.warning( self, 'Warning', 'Please set a path for the destination Hydrus Tag Archive.' )
                    
                    return
                    
                
                content_action = HC.CONTENT_UPDATE_ADD
                
                desired_hash_type = self._migration_destination_hash_type_choice.GetValue()
                
                destination = ClientMigration.MigrationDestinationHTA( HG.client_controller, self._dest_archive_path, desired_hash_type )
                
            else:
                
                content_action = self._migration_action.GetValue()
                
                desired_hash_type = 'sha256'
                
                destination = ClientMigration.MigrationDestinationTagServiceMappings( HG.client_controller, destination_service_key, content_action )
                
            
            file_service_key = self._migration_source_file_filter.GetValue()
            
            if file_service_key == self.HASHES_SERVICE_KEY:
                
                file_service_key = CC.COMBINED_FILE_SERVICE_KEY
                hashes = self._hashes
                
                extra_info = ' for {} files'.format( HydrusData.ToHumanInt( len( hashes ) ) )
                
            else:
                
                hashes = None
                
                if file_service_key == CC.COMBINED_FILE_SERVICE_KEY:
                    
                    extra_info = ' for all known files'
                    
                else:
                    
                    file_service_name = HG.client_controller.services_manager.GetName( file_service_key )
                    
                    extra_info = ' for files in "{}"'.format( file_service_name )
                    
                
            
            tag_filter = self._migration_source_tag_filter.GetValue()
            
            extra_info += ' and for tags "{}"'.format( HydrusText.ElideText( tag_filter.ToPermittedString(), 96 ) )
            
            if source_service_key == self.HTA_SERVICE_KEY:
                
                if self._source_archive_path is None:
                    
                    QW.QMessageBox.warning( self, 'Warning', 'Please set a path for the source Hydrus Tag Archive.' )
                    
                    return
                    
                
                source = ClientMigration.MigrationSourceHTA( HG.client_controller, self._source_archive_path, file_service_key, desired_hash_type, hashes, tag_filter )
                
            else:
                
                source = ClientMigration.MigrationSourceTagServiceMappings( HG.client_controller, source_service_key, file_service_key, desired_hash_type, hashes, tag_filter, content_statuses )
                
            
        else:
            
            if destination_service_key == self.HTPA_SERVICE_KEY:
                
                if self._dest_archive_path is None:
                    
                    QW.QMessageBox.warning( self, 'Warning', 'Please set a path for the destination Hydrus Tag Pair Archive.' )
                    
                    return
                    
                
                content_action = HC.CONTENT_UPDATE_ADD
                
                destination = ClientMigration.MigrationDestinationHTPA( HG.client_controller, self._dest_archive_path, content_type )
                
            else:
                
                content_action = self._migration_action.GetValue()
                
                destination = ClientMigration.MigrationDestinationTagServicePairs( HG.client_controller, destination_service_key, content_action, content_type )
                
            
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
                    
                    QW.QMessageBox.warning( self, 'Warning', 'Please set a path for the source Hydrus Tag Archive.' )
                    
                    return
                    
                
                source = ClientMigration.MigrationSourceHTPA( HG.client_controller, self._source_archive_path, left_tag_pair_filter, right_tag_pair_filter )
                
            else:
                
                source = ClientMigration.MigrationSourceTagServicePairs( HG.client_controller, source_service_key, content_type, left_tag_pair_filter, right_tag_pair_filter, content_statuses )
                
            
        
        title = 'taking {} {}{} from "{}" and {} "{}"'.format( source_content_statuses_strings[ content_statuses ], HC.content_type_string_lookup[ content_type ], extra_info, source.GetName(), destination_action_strings[ content_action ], destination.GetName() )
        
        message = 'Migrations can make huge changes. They can be cancelled early, but any work they do cannot always be undone. Please check that this summary looks correct:'
        message += os.linesep * 2
        message += title
        message += os.linesep * 2
        message += 'If you plan to make a very big change (especially a mass delete), I recommend making a backup of your database before going ahead, just in case something unexpected happens.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'looks good', no_label = 'go back' )
        
        if result == QW.QDialog.Accepted:
            
            if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                
                do_it = True
                
            else:
                
                message = 'Are you absolutely sure you set up the filters and everything how you wanted? Last chance to turn back.'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                do_it = result == QW.QDialog.Accepted
                
            
            if do_it:
                
                migration_job = ClientMigration.MigrationJob( HG.client_controller, title, source, destination )
                
                HG.client_controller.CallToThread( migration_job.Run )
                
            
        
    
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
                            
                            QW.QMessageBox.critical( self, 'Error', 'Could not load that path as an Archive! {}'.format(str(e)) )
                            
                        
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
                            
                            QW.QMessageBox.warning( self, 'Warning', 'Could not load that file as a Hydrus Tag Pair Archive! {}'.format(str(e)) )
                            
                            return
                            
                        
                        if content_type == HC.CONTENT_TYPE_TAG_PARENTS and pair_type != HydrusTagArchive.TAG_PAIR_TYPE_PARENTS:
                            
                            QW.QMessageBox.warning( self, 'Warning', 'This Hydrus Tag Pair Archive is not a tag parents archive!' )
                            
                            return
                            
                        elif content_type == HC.CONTENT_TYPE_TAG_SIBLINGS and pair_type != HydrusTagArchive.TAG_PAIR_TYPE_SIBLINGS:
                            
                            QW.QMessageBox.warning( self, 'Warning', 'This Hydrus Tag Pair Archive is not a tag siblings archive!' )
                            
                            return
                            
                        
                        
                    
                else:
                    
                    self._migration_destination_hash_type_choice.setEnabled( True )
                    
                
                self._dest_archive_path = path
                
                filename = os.path.basename( self._dest_archive_path )
                
                self._migration_destination_archive_path_button.setText( filename )
                
                self._migration_destination_archive_path_button.setToolTip( path )
                
            
        
    
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
                        
                        QW.QMessageBox.warning( self, 'Warning', 'Could not load that file as a Hydrus Tag Archive! {}'.format(str(e)) )
                        
                        return
                        
                    
                    hash_type_str = HydrusTagArchive.hash_type_to_str_lookup[ hash_type ]
                    
                    self._migration_source_hash_type_st.setText( 'hash type: {}'.format(hash_type_str) )
                    
                else:
                    
                    try:
                        
                        hta = HydrusTagArchive.HydrusTagPairArchive( path )
                        
                        pair_type = hta.GetPairType()
                        
                    except Exception as e:
                        
                        QW.QMessageBox.warning( self, 'Warning', 'Could not load that file as a Hydrus Tag Pair Archive! {}'.format(str(e)) )
                        
                        return
                        
                    
                    if pair_type is None:
                        
                        QW.QMessageBox.warning( self, 'Warning', 'This Hydrus Tag Pair Archive does not have a pair type set!' )
                        
                        return
                        
                    
                    if content_type == HC.CONTENT_TYPE_TAG_PARENTS and pair_type != HydrusTagArchive.TAG_PAIR_TYPE_PARENTS:
                        
                        QW.QMessageBox.warning( self, 'Warning', 'This Hydrus Tag Pair Archive is not a tag parents archive!' )
                        
                        return
                        
                    elif content_type == HC.CONTENT_TYPE_TAG_SIBLINGS and pair_type != HydrusTagArchive.TAG_PAIR_TYPE_SIBLINGS:
                        
                        QW.QMessageBox.warning( self, 'Warning', 'This Hydrus Tag Pair Archive is not a tag siblings archive!' )
                        
                        return
                        
                    
                
                self._source_archive_path = path
                
                filename = os.path.basename( self._source_archive_path )
                
                self._migration_source_archive_path_button.setText( filename )
                
                self._migration_source_archive_path_button.setToolTip( path )
                
            
        
    
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
            
            destination_service = HG.client_controller.services_manager.GetService( destination )
            
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
            
            source_service = HG.client_controller.services_manager.GetService( source )
            
            source_service_type = source_service.GetServiceType()
            
            self._migration_source_content_status_filter.addItem( 'current', ( HC.CONTENT_STATUS_CURRENT, ) )
            
            if source_service_type == HC.TAG_REPOSITORY:
                
                self._migration_source_content_status_filter.addItem( 'current and pending', ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING ) )
                
            
            self._migration_source_content_status_filter.addItem( 'deleted', ( HC.CONTENT_STATUS_DELETED, ) )
            
            self._migration_source_content_status_filter.setEnabled( True )
            
        
        self._UpdateMigrationControlsActions()
        
    
    def _UpdateMigrationControlsNewType( self ):
        
        content_type = self._migration_content_type.GetValue()
        
        self._migration_source.clear()
        self._migration_destination.clear()
        
        for service in HG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES ):
            
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
        self._migration_source_archive_path_button.setToolTip( '' )
        
        self._migration_destination_archive_path_button.setText( 'no path set' )
        self._migration_destination_archive_path_button.setToolTip( '' )
        
        if content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            self._migration_source.addItem( 'Hydrus Tag Archive', self.HTA_SERVICE_KEY )
            self._migration_destination.addItem( 'Hydrus Tag Archive', self.HTA_SERVICE_KEY )
            
            self._migration_source_file_filter.show()
            self._migration_source_tag_filter.show()
            self._migration_source_left_tag_pair_filter.hide()
            self._migration_source_right_tag_pair_filter.hide()
            
        elif content_type in ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ):
            
            self._migration_source.addItem( 'Hydrus Tag Pair Archive', self.HTPA_SERVICE_KEY )
            self._migration_destination.addItem( 'Hydrus Tag Pair Archive', self.HTPA_SERVICE_KEY )
            
            self._migration_source_file_filter.hide()
            self._migration_source_tag_filter.hide()
            self._migration_source_left_tag_pair_filter.show()
            self._migration_source_right_tag_pair_filter.show()
            
        
        self._migration_source.SetValue( self._service_key )
        self._migration_destination.SetValue( self._service_key )
        
        self._UpdateMigrationControlsNewSource()
        self._UpdateMigrationControlsNewDestination()
        
    
class ReviewDownloaderImport( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, network_engine ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._network_engine = network_engine
        
        vbox = QP.VBoxLayout()
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'adding_new_downloaders.html' ) )
        
        menu_items.append( ( 'normal', 'open the easy downloader import help', 'Open the help page for easily importing downloaders in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help -->', object_name = 'HydrusIndeterminate' )
        
        self._repo_link = ClientGUICommon.BetterHyperLink( self, 'get user-made downloaders here', 'https://github.com/CuddleBear92/Hydrus-Presets-and-Scripts/tree/master/Downloaders' )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().paste, self._Paste )
        self._paste_button.setToolTip( 'Or you can paste bitmaps from clipboard!' )
        
        st = ClientGUICommon.BetterStaticText( self, label = 'Drop downloader-encoded pngs onto Lain to import.' )
        
        lain_path = os.path.join( HC.STATIC_DIR, 'lain.jpg' )
        
        lain_qt_pixmap = ClientRendering.GenerateHydrusBitmap( lain_path, HC.IMAGE_JPEG ).GetQtPixmap()
        
        win = ClientGUICommon.BufferedWindowIcon( self, lain_qt_pixmap )
        
        win.setCursor( QG.QCursor( QC.Qt.PointingHandCursor ) )
        
        self._select_from_list = QW.QCheckBox( self )
        
        if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            self._select_from_list.setChecked( True )
            
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._repo_link, CC.FLAGS_CENTER )
        QP.AddToLayout( vbox, st, CC.FLAGS_CENTER )
        QP.AddToLayout( vbox, self._paste_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, win, CC.FLAGS_CENTER )
        QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._select_from_list, self, 'select objects from list' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        win.installEventFilter( ClientGUIDragDrop.FileDropTarget( win, filenames_callable = self.ImportFromDragDrop ) )
        
        self._lain_event_filter = QP.WidgetEventFilter( win )
        self._lain_event_filter.EVT_LEFT_DOWN( self.EventLainClick )
        
    
    def _ImportPaths( self, paths ):
        
        payloads = []
        
        for path in paths:
            
            try:
                
                payload = ClientSerialisable.LoadFromPNG( path )
                
            except Exception as e:
                
                QW.QMessageBox.critical( self, 'Error', str(e) )
                
                return
                
            
            payloads.append( ( 'file "{}"'.format( path ), payload ) )
            
        
        self._ImportPayloads( payloads )
        
    
    def _ImportPayloads( self, payloads ):
        
        have_shown_load_error = False
        
        gugs = []
        url_classes = []
        parsers = []
        domain_metadatas = []
        login_scripts = []
        
        num_misc_objects = 0
        
        bandwidth_manager = self._network_engine.bandwidth_manager
        domain_manager = self._network_engine.domain_manager
        login_manager = self._network_engine.login_manager
        
        for ( payload_description, payload ) in payloads:
            
            try:
                
                obj_list = HydrusSerialisable.CreateFromNetworkBytes( payload, raise_error_on_future_version = True )
                
            except HydrusExceptions.SerialisationException as e:
                
                if not have_shown_load_error:
                    
                    message = str( e )
                    
                    if len( payloads ) > 1:
                        
                        message += os.linesep * 2
                        message += 'If there are more unloadable objects in this import, they will be skipped silently.'
                        
                    
                    QW.QMessageBox.critical( self, 'Error', message )
                    
                    have_shown_load_error = True
                    
                
                continue
                
            except:
                
                QW.QMessageBox.critical( self, 'Error', 'I could not understand what was encoded in {}!'.format( payload_description ) )
                
                continue
                
            
            if isinstance( obj_list, ( ClientNetworkingGUG.GalleryURLGenerator, ClientNetworkingGUG.NestedGalleryURLGenerator, ClientNetworkingURLClass.URLClass, ClientParsing.PageParser, ClientNetworkingDomain.DomainMetadataPackage, ClientNetworkingLogin.LoginScriptDomain ) ):
                
                obj_list = HydrusSerialisable.SerialisableList( [ obj_list ] )
                
            
            if not isinstance( obj_list, HydrusSerialisable.SerialisableList ):
                
                QW.QMessageBox.warning( self, 'Warning', 'Unfortunately, {} did not look like a package of download data! Instead, it looked like: {}'.format( payload_description, obj_list.SERIALISABLE_NAME ) )
                
                continue
                
            
            for obj in obj_list:
                
                if isinstance( obj, ( ClientNetworkingGUG.GalleryURLGenerator, ClientNetworkingGUG.NestedGalleryURLGenerator ) ):
                    
                    gugs.append( obj )
                    
                elif isinstance( obj, ClientNetworkingURLClass.URLClass ):
                    
                    url_classes.append( obj )
                    
                elif isinstance( obj, ClientParsing.PageParser ):
                    
                    parsers.append( obj )
                    
                elif isinstance( obj, ClientNetworkingDomain.DomainMetadataPackage ):
                    
                    domain_metadatas.append( obj )
                    
                elif isinstance( obj, ClientNetworkingLogin.LoginScriptDomain ):
                    
                    login_scripts.append( obj )
                    
                else:
                    
                    num_misc_objects += 1
                    
                
            
        
        if len( gugs ) + len( url_classes ) + len( parsers ) + len( domain_metadatas ) + len( login_scripts ) == 0:
            
            if num_misc_objects > 0:
                
                QW.QMessageBox.warning( self, 'Warning', 'I found '+HydrusData.ToHumanInt(num_misc_objects)+' misc objects in that png, but nothing downloader related.' )
                
            
            return
            
        
        # url matches first
        
        url_class_names_seen = set()
        
        dupe_url_classes = []
        num_exact_dupe_url_classes = 0
        new_url_classes = []
        
        for url_class in url_classes:
            
            if url_class.GetName() in url_class_names_seen:
                
                continue
                
            
            if domain_manager.AlreadyHaveExactlyThisURLClass( url_class ):
                
                dupe_url_classes.append( url_class )
                num_exact_dupe_url_classes += 1
                
            else:
                
                new_url_classes.append( url_class )
                
                url_class_names_seen.add( url_class.GetName() )
                
            
        
        # now gugs
        
        gug_names_seen = set()
        
        num_exact_dupe_gugs = 0
        new_gugs = []
        
        for gug in gugs:
            
            if gug.GetName() in gug_names_seen:
                
                continue
                
            
            if domain_manager.AlreadyHaveExactlyThisGUG( gug ):
                
                num_exact_dupe_gugs += 1
                
            else:
                
                new_gugs.append( gug )
                
                gug_names_seen.add( gug.GetName() )
                
            
        
        # now parsers
        
        parser_names_seen = set()
        
        num_exact_dupe_parsers = 0
        new_parsers = []
        
        for parser in parsers:
            
            if parser.GetName() in parser_names_seen:
                
                continue
                
            
            if domain_manager.AlreadyHaveExactlyThisParser( parser ):
                
                num_exact_dupe_parsers += 1
                
            else:
                
                new_parsers.append( parser )
                
                parser_names_seen.add( parser.GetName() )
                
            
        
        # now login scripts
        
        login_script_names_seen = set()
        
        num_exact_dupe_login_scripts = 0
        new_login_scripts = []
        
        for login_script in login_scripts:
            
            if login_script.GetName() in login_script_names_seen:
                
                continue
                
            
            if login_manager.AlreadyHaveExactlyThisLoginScript( login_script ):
                
                num_exact_dupe_login_scripts += 1
                
            else:
                
                new_login_scripts.append( login_script )
                
                login_script_names_seen.add( login_script.GetName() )
                
            
        
        # now domain metadata
        
        domains_seen = set()
        
        num_exact_dupe_domain_metadatas = 0
        new_domain_metadatas = []
        
        for domain_metadata in domain_metadatas:
            
            # check if the headers or rules are new, discarding any dupe content
            
            domain = domain_metadata.GetDomain()
            headers_list = None
            bandwidth_rules = None
            
            if domain in domains_seen:
                
                continue
                
            
            nc = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain )
            
            if domain_metadata.HasHeaders():
                
                headers_list = domain_metadata.GetHeaders()
                
                if domain_manager.AlreadyHaveExactlyTheseHeaders( nc, headers_list ):
                    
                    headers_list = None
                    
                
            
            if domain_metadata.HasBandwidthRules():
                
                bandwidth_rules = domain_metadata.GetBandwidthRules()
                
                if bandwidth_manager.AlreadyHaveExactlyTheseBandwidthRules( nc, bandwidth_rules ):
                    
                    bandwidth_rules = None
                    
                
            
            if headers_list is None and bandwidth_rules is None:
                
                num_exact_dupe_domain_metadatas += 1
                
            else:
                
                new_dm = ClientNetworkingDomain.DomainMetadataPackage( domain = domain, headers_list = headers_list, bandwidth_rules = bandwidth_rules )
                
                new_domain_metadatas.append( new_dm )
                
                domains_seen.add( domain )
                
            
        
        #
        
        total_num_dupes = num_exact_dupe_gugs + num_exact_dupe_url_classes + num_exact_dupe_parsers + num_exact_dupe_domain_metadatas + num_exact_dupe_login_scripts
        
        if len( new_gugs ) + len( new_url_classes ) + len( new_parsers ) + len( new_domain_metadatas ) + len( new_login_scripts ) == 0:
            
            QW.QMessageBox.information( self, 'Information', 'All '+HydrusData.ToHumanInt(total_num_dupes)+' downloader objects in that package appeared to already be in the client, so nothing need be added.' )
            
            return
            
        
        # let's start selecting what we want
        
        if self._select_from_list.isChecked():
            
            choice_tuples = []
            choice_tuples.extend( [ ( 'GUG: ' + gug.GetName(), gug, True ) for gug in new_gugs ] )
            choice_tuples.extend( [ ( 'URL Class: ' + url_class.GetName(), url_class, True ) for url_class in new_url_classes ] )
            choice_tuples.extend( [ ( 'Parser: ' + parser.GetName(), parser, True ) for parser in new_parsers ] )
            choice_tuples.extend( [ ( 'Login Script: ' + login_script.GetName(), login_script, True ) for login_script in new_login_scripts ] )
            choice_tuples.extend( [ ( 'Domain Metadata: ' + domain_metadata.GetDomain(), domain_metadata, True ) for domain_metadata in new_domain_metadatas ] )
            
            try:
                
                new_objects = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'select objects to add', choice_tuples )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            new_gugs = [ obj for obj in new_objects if isinstance( obj, ( ClientNetworkingGUG.GalleryURLGenerator, ClientNetworkingGUG.NestedGalleryURLGenerator ) ) ]
            new_url_classes = [ obj for obj in new_objects if isinstance( obj, ClientNetworkingURLClass.URLClass ) ]
            new_parsers = [ obj for obj in new_objects if isinstance( obj, ClientParsing.PageParser ) ]
            new_login_scripts = [ obj for obj in new_objects if isinstance( obj, ClientNetworkingLogin.LoginScriptDomain ) ]
            new_domain_metadatas = [ obj for obj in new_objects if isinstance( obj, ClientNetworkingDomain.DomainMetadataPackage ) ]
            
        
        # final ask
        
        new_gugs.sort( key = lambda o: o.GetName() )
        new_url_classes.sort( key = lambda o: o.GetName() )
        new_parsers.sort( key = lambda o: o.GetName() )
        new_login_scripts.sort( key = lambda o: o.GetName() )
        new_domain_metadatas.sort( key = lambda o: o.GetDomain() )
        
        if len( new_domain_metadatas ) > 0:
            
            message = 'Before the final import confirmation, I will now show the domain metadata in detail. Give it a cursory look just to check it seems good. If not, click no on the final dialog!'
            
            TOO_MANY_DM = 8
            
            if len( new_domain_metadatas ) > TOO_MANY_DM:
                
                message += os.linesep * 2
                message += 'There are more than ' + HydrusData.ToHumanInt( TOO_MANY_DM ) + ' domain metadata objects. So I do not give you dozens of preview windows, I will only show you these first ' + HydrusData.ToHumanInt( TOO_MANY_DM ) + '.'
                
            
            new_domain_metadatas_to_show = new_domain_metadatas[:TOO_MANY_DM]
            
            for new_dm in new_domain_metadatas_to_show:
                
                QW.QMessageBox.information( self, 'Information', new_dm.GetDetailedSafeSummary() )
                
            
        
        all_to_add = list( new_gugs )
        all_to_add.extend( new_url_classes )
        all_to_add.extend( new_parsers )
        all_to_add.extend( new_login_scripts )
        all_to_add.extend( new_domain_metadatas )
        
        message = 'The client is about to add and link these objects:'
        message += os.linesep * 2
        message += os.linesep.join( ( obj.GetSafeSummary() for obj in all_to_add[:20] ) )
        
        if len( all_to_add ) > 20:
            
            message += os.linesep
            message += '(and ' + HydrusData.ToHumanInt( len( all_to_add ) - 20 ) + ' others)'
            
        
        message += os.linesep * 2
        message += 'Does that sound good?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.Accepted:
            
            return
            
        
        # ok, do it
        
        if len( new_gugs ) > 0:
            
            for gug in new_gugs:
                
                gug.RegenerateGUGKey()
                
            
            domain_manager.AddGUGs( new_gugs )
            
        
        domain_manager.AutoAddURLClassesAndParsers( new_url_classes, dupe_url_classes, new_parsers )
        
        bandwidth_manager.AutoAddDomainMetadatas( new_domain_metadatas )
        domain_manager.AutoAddDomainMetadatas( new_domain_metadatas, approved = True )
        login_manager.AutoAddLoginScripts( new_login_scripts )
        
        num_new_gugs = len( new_gugs )
        num_aux = len( new_url_classes ) + len( new_parsers ) + len( new_login_scripts ) + len( new_domain_metadatas )
        
        final_message = 'Successfully added ' + HydrusData.ToHumanInt( num_new_gugs ) + ' new downloaders and ' + HydrusData.ToHumanInt( num_aux ) + ' auxiliary objects.'
        
        if total_num_dupes > 0:
            
            final_message += ' ' + HydrusData.ToHumanInt( total_num_dupes ) + ' duplicate objects were not added (but some additional metadata may have been merged).'
            
        
        QW.QMessageBox.information( self, 'Information', final_message )
        
    
    def _Paste( self ):
        
        if HG.client_controller.ClipboardHasImage():
            
            try:
                
                qt_image = HG.client_controller.GetClipboardImage()
                
                payload_description = 'clipboard image data'
                payload = ClientSerialisable.LoadFromQtImage( qt_image )
                
            except Exception as e:
                
                QW.QMessageBox.critical( self, 'Error', 'Sorry, seemed to be a problem: {}'.format( str( e ) ) )
                
                return
                
            
        else:
            
            try:
                
                raw_text = HG.client_controller.GetClipboardText()
                
                payload_description = 'clipboard text data'
                payload = HydrusCompression.CompressStringToBytes( raw_text )
                
            except HydrusExceptions.DataMissing as e:
                
                QW.QMessageBox.critical( self, 'Error', str(e) )
                
                return
                
            
        
        payloads = [ ( payload_description, payload ) ]
        
        self._ImportPayloads( payloads )
        
    
    def EventLainClick( self, event ):
        
        with QP.FileDialog( self, 'Select the pngs to add.', acceptMode = QW.QFileDialog.AcceptOpen, fileMode = QW.QFileDialog.ExistingFiles ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                paths = dlg.GetPaths()
                
                self._ImportPaths( paths )
                
            
        
    
    def ImportFromDragDrop( self, paths ):
        
        self._ImportPaths( paths )
        
    
class ReviewFileMaintenance( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, stats ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._hash_ids = None
        self._job_types_to_counts = {}
        
        self._notebook = ClientGUICommon.BetterNotebook( self )
        
        #
        
        self._current_work_panel = QW.QWidget( self._notebook )
        
        jobs_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._current_work_panel )
        
        self._jobs_listctrl = ClientGUIListCtrl.BetterListCtrl( jobs_listctrl_panel, CGLC.COLUMN_LIST_FILE_MAINTENANCE_JOBS.ID, 8, self._ConvertJobTypeToListCtrlTuples )
        
        jobs_listctrl_panel.SetListCtrl( self._jobs_listctrl )
        
        jobs_listctrl_panel.AddButton( 'clear', self._DeleteWork, enabled_only_on_selection = True )
        jobs_listctrl_panel.AddButton( 'do work', self._DoWork, enabled_only_on_selection = True )
        jobs_listctrl_panel.AddButton( 'do all work', self._DoAllWork, enabled_check_func = self._WorkToDo )
        jobs_listctrl_panel.AddButton( 'refresh', self._RefreshWorkDue )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, jobs_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._current_work_panel.setLayout( vbox )
        
        #
        
        self._new_work_panel = QW.QWidget( self._notebook )
        
        #
        
        self._search_panel = ClientGUICommon.StaticBox( self._new_work_panel, 'select files by search' )
        
        page_key = HydrusData.GenerateKey()
        
        default_location_context = HG.client_controller.services_manager.GetDefaultLocationContext()
        
        file_search_context = ClientSearch.FileSearchContext( location_context = default_location_context )
        
        self._tag_autocomplete = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._search_panel, page_key, file_search_context, allow_all_known_files = False, force_system_everything = True )
        
        self._run_search_st = ClientGUICommon.BetterStaticText( self._search_panel, label = 'no results yet' )
        
        self._run_search = ClientGUICommon.BetterButton( self._search_panel, 'run this search', self._RunSearch )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._run_search_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._run_search, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._search_panel.Add( self._tag_autocomplete, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._search_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        self._button_panel = ClientGUICommon.StaticBox( self._new_work_panel, 'easy select' )
        
        self._select_all_media_files = ClientGUICommon.BetterButton( self._button_panel, 'all media files', self._SelectAllMediaFiles )
        self._select_repo_files = ClientGUICommon.BetterButton( self._button_panel, 'all repository update files', self._SelectRepoUpdateFiles )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._select_all_media_files, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._select_repo_files, CC.FLAGS_CENTER )
        
        self._button_panel.Add( hbox, CC.FLAGS_ON_RIGHT )
        
        #
        
        self._action_panel = ClientGUICommon.StaticBox( self._new_work_panel, 'add job' )
        
        self._selected_files_st = ClientGUICommon.BetterStaticText( self._action_panel, label = 'no files selected yet' )
        
        self._action_selector = ClientGUICommon.BetterChoice( self._action_panel )
        
        for job_type in ClientFiles.ALL_REGEN_JOBS_IN_PREFERRED_ORDER:
            
            self._action_selector.addItem( ClientFiles.regen_file_enum_to_str_lookup[ job_type ], job_type )
            
        
        self._description_button = ClientGUICommon.BetterButton( self._action_panel, 'see description', self._SeeDescription )
        
        self._add_new_job = ClientGUICommon.BetterButton( self._action_panel, 'add job', self._AddJob )
        
        self._add_new_job.setEnabled( False )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._selected_files_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._action_selector, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._description_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._add_new_job, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._action_panel.Add( hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        label = 'First, select which files you wish to queue up for the job using a normal search. Hit \'run this search\' to select those files.'
        label += os.linesep
        label += 'Then select the job type and click \'add job\'.'
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self._new_work_panel,label=label), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._search_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._button_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._action_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._new_work_panel.setLayout( vbox )
        
        #
        
        self._notebook.addTab( self._current_work_panel, 'scheduled work' )
        self._notebook.addTab( self._new_work_panel, 'add new work' )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._RefreshWorkDue()
        
        HG.client_controller.sub( self, '_RefreshWorkDue', 'notify_files_maintenance_done' )
        
    
    def _AddJob( self ):
        
        hash_ids = self._hash_ids
        job_type = self._action_selector.GetValue()
        
        if len( hash_ids ) > 1000:
            
            message = 'Are you sure you want to schedule "{}" on {} files?'.format( ClientFiles.regen_file_enum_to_str_lookup[ job_type ], HydrusData.ToHumanInt( len( hash_ids ) ) )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
            
            if result != QW.QDialog.Accepted:
                
                return
                
            
        
        self._add_new_job.setEnabled( False )
        
        def work_callable():
            
            HG.client_controller.files_maintenance_manager.ScheduleJobHashIds( hash_ids, job_type )
            
            return True
            
        
        def publish_callable( result ):
            
            QW.QMessageBox.information( self, 'Information', 'Jobs added!' )
            
            self._add_new_job.setEnabled( True )
            
            self._RefreshWorkDue()
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _ConvertJobTypeToListCtrlTuples( self, job_type ):
        
        pretty_job_type = ClientFiles.regen_file_enum_to_str_lookup[ job_type ]
        sort_job_type = pretty_job_type
        
        if job_type in self._job_types_to_counts:
            
            num_to_do = self._job_types_to_counts[ job_type ]
            
        else:
            
            num_to_do = 0
            
        
        pretty_num_to_do = HydrusData.ToHumanInt( num_to_do )
        
        display_tuple = ( pretty_job_type, pretty_num_to_do )
        sort_tuple = ( sort_job_type, num_to_do )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DeleteWork( self ):
        
        message = 'Clear all the selected scheduled work?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.Accepted:
            
            return
            
        
        job_types = self._jobs_listctrl.GetData( only_selected = True )
        
        def work_callable():
            
            for job_type in job_types:
                
                HG.client_controller.files_maintenance_manager.CancelJobs( job_type )
                
            
            return True
            
        
        def publish_callable( result ):
            
            self._RefreshWorkDue()
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _DoAllWork( self ):
        
        HG.client_controller.CallToThread( HG.client_controller.files_maintenance_manager.ForceMaintenance )
        
    
    def _DoWork( self ):
        
        job_types = self._jobs_listctrl.GetData( only_selected = True )
        
        if len( job_types ) == 0:
            
            return
            
        
        HG.client_controller.CallToThread( HG.client_controller.files_maintenance_manager.ForceMaintenance, mandated_job_types = job_types )
        
    
    def _RefreshWorkDue( self ):
        
        def work_callable():
            
            job_types_to_counts = HG.client_controller.Read( 'file_maintenance_get_job_counts' )
            
            return job_types_to_counts
            
        
        def publish_callable( job_types_to_counts ):
            
            self._job_types_to_counts = job_types_to_counts
            
            job_types = list( job_types_to_counts.keys() )
            
            self._jobs_listctrl.SetData( job_types )
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _RunSearch( self ):
        
        self._run_search_st.setText( 'loading\u2026' )
        
        self._run_search.setEnabled( False )
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        
        def work_callable():
            
            query_hash_ids = HG.client_controller.Read( 'file_query_ids', file_search_context )
            
            return query_hash_ids
            
        
        def publish_callable( hash_ids ):
            
            self._run_search_st.setText( '{} files found'.format( HydrusData.ToHumanInt( len( hash_ids ) ) ) )
            
            self._run_search.setEnabled( True )
            
            self._SetHashIds( hash_ids )
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _SeeDescription( self ):
        
        job_type = self._action_selector.GetValue()
        
        message = ClientFiles.regen_file_enum_to_description_lookup[ job_type ]
        message += os.linesep * 2
        message += 'This job has weight {}, where a normalised unit of file work has value {}.'.format( HydrusData.ToHumanInt( ClientFiles.regen_file_enum_to_job_weight_lookup[ job_type ] ), HydrusData.ToHumanInt( ClientFiles.NORMALISED_BIG_JOB_WEIGHT ) )
        
        QW.QMessageBox.information( self, 'Information', message )
        
    
    def _SelectAllMediaFiles( self ):
        
        self._select_all_media_files.setEnabled( False )
        
        location_context = ClientLocation.GetLocationContextForAllLocalMedia()
        
        file_search_context = ClientSearch.FileSearchContext( location_context = location_context )
        
        def work_callable():
            
            query_hash_ids = HG.client_controller.Read( 'file_query_ids', file_search_context )
            
            return query_hash_ids
            
        
        def publish_callable( hash_ids ):
            
            self._select_all_media_files.setEnabled( True )
            
            self._SetHashIds( hash_ids )
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _SelectRepoUpdateFiles( self ):
        
        self._select_repo_files.setEnabled( False )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_UPDATE_SERVICE_KEY )
        
        file_search_context = ClientSearch.FileSearchContext( location_context = location_context )
        
        def work_callable():
            
            query_hash_ids = HG.client_controller.Read( 'file_query_ids', file_search_context )
            
            return query_hash_ids
            
        
        def publish_callable( hash_ids ):
            
            self._select_repo_files.setEnabled( True )
            
            self._SetHashIds( hash_ids )
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _SetHashIds( self, hash_ids ):
        
        if hash_ids is None:
            
            hash_ids = set()
            
        
        self._hash_ids = hash_ids
        
        self._selected_files_st.setText( '{} files selected'.format(HydrusData.ToHumanInt(len(hash_ids))) )
        
        if len( hash_ids ) == 0:
            
            self._add_new_job.setEnabled( False )
            
        else:
            
            self._add_new_job.setEnabled( True )
            
        
    
    def _WorkToDo( self ):
        
        return len( self._job_types_to_counts ) > 0
        
    
class ReviewHowBonedAmI( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, boned_stats ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        num_inbox = boned_stats[ 'num_inbox' ]
        num_archive = boned_stats[ 'num_archive' ]
        num_deleted = boned_stats[ 'num_deleted' ]
        size_inbox = boned_stats[ 'size_inbox' ]
        size_archive = boned_stats[ 'size_archive' ]
        size_deleted = boned_stats[ 'size_deleted' ]
        total_viewtime = boned_stats[ 'total_viewtime' ]
        total_alternate_files = boned_stats[ 'total_alternate_files' ]
        total_duplicate_files = boned_stats[ 'total_duplicate_files' ]
        total_potential_pairs = boned_stats[ 'total_potential_pairs' ]
        
        num_total = num_archive + num_inbox
        size_total = size_archive + size_inbox
        
        num_supertotal = num_total + num_deleted
        size_supertotal = size_total + size_deleted
        
        vbox = QP.VBoxLayout()
        
        if num_supertotal < 1000:
            
            get_more = ClientGUICommon.BetterStaticText( self, label = 'I hope you enjoy my software. You might like to check out the downloaders! :^)' )
            
            QP.AddToLayout( vbox, get_more, CC.FLAGS_CENTER )
            
        elif num_inbox <= num_archive / 100:
            
            hooray = ClientGUICommon.BetterStaticText( self, label = 'CONGRATULATIONS. YOU APPEAR TO BE UNBONED, BUT REMAIN EVER VIGILANT' )
            
            QP.AddToLayout( vbox, hooray, CC.FLAGS_CENTER )
            
        else:
            
            boned_path = os.path.join( HC.STATIC_DIR, 'boned.jpg' )
            
            boned_qt_pixmap = ClientRendering.GenerateHydrusBitmap( boned_path, HC.IMAGE_JPEG ).GetQtPixmap()
            
            win = ClientGUICommon.BufferedWindowIcon( self, boned_qt_pixmap )
            
            QP.AddToLayout( vbox, win, CC.FLAGS_CENTER )
            
        
        if num_supertotal == 0:
            
            nothing_label = 'You have yet to board the ride.'
            
            nothing_st = ClientGUICommon.BetterStaticText( self, label = nothing_label )
            
            QP.AddToLayout( vbox, nothing_st, CC.FLAGS_CENTER )
            
        else:
            
            notebook = ClientGUICommon.BetterNotebook( self )
            
            #
            
            panel = QW.QWidget( notebook )
            
            panel_vbox = QP.VBoxLayout()
            
            average_filesize = size_total // num_total
            
            summary_label = 'Total: {} files, totalling {}, averaging {}'.format( HydrusData.ToHumanInt( num_total ), HydrusData.ToHumanBytes( size_total ), HydrusData.ToHumanBytes( average_filesize ) )
            
            summary_st = ClientGUICommon.BetterStaticText( panel, label = summary_label )
            
            QP.AddToLayout( panel_vbox, summary_st, CC.FLAGS_CENTER )
            
            num_archive_percent = num_archive / num_total
            size_archive_percent = size_archive / size_total
            
            num_inbox_percent = num_inbox / num_total
            size_inbox_percent = size_inbox / size_total
            
            num_deleted_percent = num_deleted / num_supertotal
            size_deleted_percent = size_deleted / size_supertotal
            
            archive_label = 'Archive: {} files ({}), totalling {} ({})'.format( HydrusData.ToHumanInt( num_archive ), ClientData.ConvertZoomToPercentage( num_archive_percent ), HydrusData.ToHumanBytes( size_archive ), ClientData.ConvertZoomToPercentage( size_archive_percent ) )
            
            archive_st = ClientGUICommon.BetterStaticText( panel, label = archive_label )
            
            inbox_label = 'Inbox: {} files ({}), totalling {} ({})'.format( HydrusData.ToHumanInt( num_inbox ), ClientData.ConvertZoomToPercentage( num_inbox_percent ), HydrusData.ToHumanBytes( size_inbox ), ClientData.ConvertZoomToPercentage( size_inbox_percent ) )
            
            inbox_st = ClientGUICommon.BetterStaticText( panel, label = inbox_label )
            
            deleted_label = 'Deleted: {} files ({}), totalling {} ({})'.format( HydrusData.ToHumanInt( num_deleted ), ClientData.ConvertZoomToPercentage( num_deleted_percent ), HydrusData.ToHumanBytes( size_deleted ), ClientData.ConvertZoomToPercentage( size_deleted_percent ) )
            
            deleted_st = ClientGUICommon.BetterStaticText( panel, label = deleted_label )
            
            QP.AddToLayout( panel_vbox, archive_st, CC.FLAGS_CENTER )
            QP.AddToLayout( panel_vbox, inbox_st, CC.FLAGS_CENTER )
            QP.AddToLayout( panel_vbox, deleted_st, CC.FLAGS_CENTER )
            
            if 'earliest_import_time' in boned_stats:
                
                eit = boned_stats[ 'earliest_import_time' ]
                
                eit_label = 'Earliest file import: {} ({})'.format( HydrusData.ConvertTimestampToPrettyTime( eit ), HydrusData.TimestampToPrettyTimeDelta( eit ) )
                
                eit_st = ClientGUICommon.BetterStaticText( panel, label = eit_label )
                
                QP.AddToLayout( panel_vbox, eit_st, CC.FLAGS_CENTER )
                
            
            panel_vbox.addStretch( 1 )
            
            panel.setLayout( panel_vbox )
            
            notebook.addTab( panel, 'files' )
            
            #
            
            panel = QW.QWidget( notebook )
            
            panel_vbox = QP.VBoxLayout()
            
            ( media_views, media_viewtime, preview_views, preview_viewtime ) = total_viewtime
            
            media_label = 'Total media views: ' + HydrusData.ToHumanInt( media_views ) + ', totalling ' + HydrusData.TimeDeltaToPrettyTimeDelta( media_viewtime )
            
            media_st = ClientGUICommon.BetterStaticText( panel, label = media_label )
            
            preview_label = 'Total preview views: ' + HydrusData.ToHumanInt( preview_views ) + ', totalling ' + HydrusData.TimeDeltaToPrettyTimeDelta( preview_viewtime )
            
            preview_st = ClientGUICommon.BetterStaticText( panel, label = preview_label )
            
            QP.AddToLayout( panel_vbox, media_st, CC.FLAGS_CENTER )
            QP.AddToLayout( panel_vbox, preview_st, CC.FLAGS_CENTER )
            
            panel_vbox.addStretch( 1 )
            
            panel.setLayout( panel_vbox )
            
            notebook.addTab( panel, 'views' )
            
            #
            
            panel = QW.QWidget( notebook )
            
            panel_vbox = QP.VBoxLayout()
            
            potentials_label = 'Total duplicate potential pairs: {}'.format( HydrusData.ToHumanInt( total_potential_pairs ) )
            duplicates_label = 'Total files set duplicate: {}'.format( HydrusData.ToHumanInt( total_duplicate_files ) )
            alternates_label = 'Total duplicate file groups set alternate: {}'.format( HydrusData.ToHumanInt( total_alternate_files ) )
            
            potentials_st = ClientGUICommon.BetterStaticText( panel, label = potentials_label )
            duplicates_st = ClientGUICommon.BetterStaticText( panel, label = duplicates_label )
            alternates_st = ClientGUICommon.BetterStaticText( panel, label = alternates_label )
            
            QP.AddToLayout( panel_vbox, potentials_st, CC.FLAGS_CENTER )
            QP.AddToLayout( panel_vbox, duplicates_st, CC.FLAGS_CENTER )
            QP.AddToLayout( panel_vbox, alternates_st, CC.FLAGS_CENTER )
            
            panel_vbox.addStretch( 1 )
            
            panel.setLayout( panel_vbox )
            
            notebook.addTab( panel, 'duplicates' )
            
            #
            
            QP.AddToLayout( vbox, notebook, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        vbox.addStretch( 1 )
        
        self.widget().setLayout( vbox )
        
    
class ReviewLocalFileImports( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, paths = None ):
        
        if paths is None:
            
            paths = []
            
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self.widget().installEventFilter( ClientGUIDragDrop.FileDropTarget( self.widget(), filenames_callable = self._AddPathsToList ) )
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._paths_list = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, CGLC.COLUMN_LIST_INPUT_LOCAL_FILES.ID, 12, self._ConvertListCtrlDataToTuple, delete_key_callback = self.RemovePaths )
        
        listctrl_panel.SetListCtrl( self._paths_list )
        
        listctrl_panel.AddButton( 'add files', self.AddPaths )
        listctrl_panel.AddButton( 'add folder', self.AddFolder )
        listctrl_panel.AddButton( 'remove files', self.RemovePaths, enabled_only_on_selection = True )
        
        self._progress = ClientGUICommon.TextAndGauge( self )
        
        self._progress_pause = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().pause, self.PauseProgress )
        self._progress_pause.setEnabled( False )
        
        self._progress_cancel = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().stop, self.StopProgress )
        self._progress_cancel.setEnabled( False )
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        show_downloader_options = False
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self, file_import_options, show_downloader_options )
        
        menu_items = []
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'do_human_sort_on_hdd_file_import_paths' )
        
        menu_items.append( ( 'check', 'sort paths as they are added', 'If checked, paths will be sorted in a numerically human-friendly (e.g. "page 9.jpg" comes before "page 10.jpg") way.', check_manager ) )
        
        self._cog_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().cog, menu_items )
        
        self._delete_after_success_st = ClientGUICommon.BetterStaticText( self )
        self._delete_after_success_st.setAlignment( QC.Qt.AlignRight | QC.Qt.AlignVCenter )
        self._delete_after_success_st.setObjectName( 'HydrusWarning' )
        
        self._delete_after_success = QW.QCheckBox( 'delete original files after successful import', self )
        self._delete_after_success.clicked.connect( self.EventDeleteAfterSuccessCheck )
        
        self._add_button = ClientGUICommon.BetterButton( self, 'import now', self._DoImport )
        self._add_button.setObjectName( 'HydrusAccept' )
        
        self._tag_button = ClientGUICommon.BetterButton( self, 'add tags before the import >>', self._AddTags )
        self._tag_button.setObjectName( 'HydrusAccept' )
        
        self._tag_button.setToolTip( 'You can add specific tags to these files, import from sidecar files, or generate them based on filename. Don\'t be afraid to experiment!' )
        
        gauge_sizer = QP.HBoxLayout()
        
        QP.AddToLayout( gauge_sizer, self._progress, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( gauge_sizer, self._progress_pause, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( gauge_sizer, self._progress_cancel, CC.FLAGS_CENTER_PERPENDICULAR )
        
        delete_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( delete_hbox, self._delete_after_success_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( delete_hbox, self._delete_after_success, CC.FLAGS_CENTER_PERPENDICULAR )
        
        import_options_buttons = QP.HBoxLayout()
        
        QP.AddToLayout( import_options_buttons, self._file_import_options, CC.FLAGS_CENTER )
        QP.AddToLayout( import_options_buttons, self._cog_button, CC.FLAGS_CENTER )
        
        buttons = QP.HBoxLayout()
        
        QP.AddToLayout( buttons, self._add_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( buttons, self._tag_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, gauge_sizer, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, delete_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, import_options_buttons, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, buttons, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        self._lock = threading.Lock()
        
        self._current_path_data = {}
        
        self._job_key = ClientThreading.JobKey()
        
        self._unparsed_paths_queue = queue.Queue()
        self._currently_parsing = threading.Event()
        self._work_to_do = threading.Event()
        self._parsed_path_queue = queue.Queue()
        self._pause_event = threading.Event()
        self._cancel_event = threading.Event()
        
        self._progress_updater = ClientGUIAsync.FastThreadToGUIUpdater( self._progress, self._progress.SetValue )
        
        if len( paths ) > 0:
            
            self._AddPathsToList( paths )
            
        
        HG.client_controller.gui.RegisterUIUpdateWindow( self )
        
        HG.client_controller.CallToThreadLongRunning( self.THREADParseImportablePaths, self._unparsed_paths_queue, self._currently_parsing, self._work_to_do, self._parsed_path_queue, self._progress_updater, self._pause_event, self._cancel_event )
        
    
    def _AddPathsToList( self, paths ):
        
        if self._cancel_event.is_set():
            
            message = 'Please wait for the cancel to clear.'
            
            QW.QMessageBox.warning( self, 'Warning', message )
            
            return
            
        
        self._unparsed_paths_queue.put( paths )
        
    
    def _AddTags( self ):
        
        paths = self._paths_list.GetData()
        
        if len( paths ) > 0:
            
            file_import_options = self._file_import_options.GetValue()
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'filename tagging', frame_key = 'local_import_filename_tagging' ) as dlg:
                
                panel = ClientGUIImport.EditLocalImportFilenameTaggingPanel( dlg, paths )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    paths_to_additional_service_keys_to_tags = panel.GetValue()
                    
                    delete_after_success = self._delete_after_success.isChecked()
                    
                    HG.client_controller.pub( 'new_hdd_import', paths, file_import_options, paths_to_additional_service_keys_to_tags, delete_after_success )
                    
                    self._OKParent()
                    
                
            
        
    
    def _ConvertListCtrlDataToTuple( self, path ):
        
        ( index, mime, size ) = self._current_path_data[ path ]
        
        pretty_index = HydrusData.ToHumanInt( index )
        pretty_mime = HC.mime_string_lookup[ mime ]
        pretty_size = HydrusData.ToHumanBytes( size )
        
        display_tuple = ( pretty_index, path, pretty_mime, pretty_size )
        sort_tuple = ( index, path, pretty_mime, size )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DoImport( self ):
        
        paths = self._paths_list.GetData()
        
        if len( paths ) > 0:
            
            file_import_options = self._file_import_options.GetValue()
            
            paths_to_additional_service_keys_to_tags = collections.defaultdict( ClientTags.ServiceKeysToTags )
            
            delete_after_success = self._delete_after_success.isChecked()
            
            HG.client_controller.pub( 'new_hdd_import', paths, file_import_options, paths_to_additional_service_keys_to_tags, delete_after_success )
            
        
        self._OKParent()
        
    
    def _TidyUp( self ):
        
        self._pause_event.set()
        
    
    def AddFolder( self ):
        
        with QP.DirDialog( self, 'Select a folder to add.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                self._AddPathsToList( ( path, ) )
                
            
        
    
    def AddPaths( self ):
        
        with QP.FileDialog( self, 'Select the files to add.', fileMode = QW.QFileDialog.ExistingFiles ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                paths = dlg.GetPaths()
                
                self._AddPathsToList( paths )
                
            
        
    
    def CleanBeforeDestroy( self ):
        
        ClientGUIScrolledPanels.ReviewPanel.CleanBeforeDestroy( self )
        
        self._TidyUp()
        
    
    def EventDeleteAfterSuccessCheck( self ):
        
        if self._delete_after_success.isChecked():
            
            self._delete_after_success_st.setText( 'YOUR ORIGINAL FILES WILL BE DELETED' )
            
        else:
            
            self._delete_after_success_st.clear()
            
        
    
    def PauseProgress( self ):
        
        if self._pause_event.is_set():
            
            self._pause_event.clear()
            
        else:
            
            self._pause_event.set()
            
        
    
    def StopProgress( self ):
        
        self._cancel_event.set()
        
    
    def RemovePaths( self ):
        
        text = 'Remove all selected?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.Accepted:
            
            paths_to_delete = self._paths_list.GetData( only_selected = True )
            
            self._paths_list.DeleteSelected()
            
            for path in paths_to_delete:
                
                del self._current_path_data[ path ]
                
            
            flat_path_data = sorted( ( ( index, path, mime, size ) for ( path, ( index, mime, size ) ) in self._current_path_data.items() ) )
            
            new_index = 1
            
            for ( old_index, path, mime, size ) in flat_path_data:
                
                self._current_path_data[ path ] = ( new_index, mime, size )
                
                new_index += 1
                
            
            self._paths_list.UpdateDatas()
            
        
    
    def THREADParseImportablePaths( self, unparsed_paths_queue, currently_parsing, work_to_do, parsed_path_queue, progress_updater, pause_event, cancel_event ):
        
        unparsed_paths = collections.deque()
        
        num_files_done = 0
        num_good_files = 0
        
        num_empty_files = 0
        num_missing_files = 0
        num_unimportable_mime_files = 0
        num_occupied_files = 0
        
        while not HG.started_shutdown:
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            if len( unparsed_paths ) > 0:
                
                work_to_do.set()
                
            else:
                
                work_to_do.clear()
                
            
            currently_parsing.clear()
            
            # ready to start, let's update ui on status
            
            total_paths = num_files_done + len( unparsed_paths )
            
            if num_good_files == 0:
                
                if num_files_done == 0:
                    
                    message = 'waiting for paths to parse'
                    
                else:
                    
                    message = 'none of the ' + HydrusData.ToHumanInt( total_paths ) + ' files parsed successfully'
                    
                
            else:
                
                message = HydrusData.ConvertValueRangeToPrettyString( num_good_files, total_paths ) + ' files parsed successfully'
                
            
            if num_empty_files + num_missing_files + num_unimportable_mime_files + num_occupied_files > 0:
                
                if num_good_files == 0:
                    
                    message += ': '
                    
                else:
                    
                    message += ', but '
                    
                
                bad_comments = []
                
                if num_empty_files > 0:
                    
                    bad_comments.append( HydrusData.ToHumanInt( num_empty_files ) + ' were empty' )
                    
                
                if num_missing_files > 0:
                    
                    bad_comments.append( HydrusData.ToHumanInt( num_missing_files ) + ' were missing' )
                    
                
                if num_unimportable_mime_files > 0:
                    
                    bad_comments.append( HydrusData.ToHumanInt( num_unimportable_mime_files ) + ' had unsupported file types' )
                    
                
                if num_occupied_files > 0:
                    
                    bad_comments.append( HydrusData.ToHumanInt( num_occupied_files ) + ' were inaccessible (maybe in use by another process)' )
                    
                
                message += ' and '.join( bad_comments )
                
            
            message += '.'
            
            progress_updater.Update( message, num_files_done, total_paths )
            
            # status updated, lets see what work there is to do
            
            if cancel_event.is_set():
                
                while not unparsed_paths_queue.empty():
                    
                    try:
                        
                        unparsed_paths_queue.get( block = False )
                        
                    except queue.Empty:
                        
                        pass
                        
                    
                
                unparsed_paths = collections.deque()
                
                cancel_event.clear()
                pause_event.clear()
                
                continue
                
            
            if pause_event.is_set():
                
                time.sleep( 1 )
                
                continue
                
            
            # let's see if there is anything to parse
            
            # first we'll flesh out unparsed_paths with anything new to look at
            
            do_human_sort = HG.client_controller.new_options.GetBoolean( 'do_human_sort_on_hdd_file_import_paths' )
            
            while not unparsed_paths_queue.empty():
                
                try:
                    
                    raw_paths = unparsed_paths_queue.get( block = False )
                    
                    paths = ClientFiles.GetAllFilePaths( raw_paths, do_human_sort = do_human_sort ) # convert any dirs to subpaths
                    
                    unparsed_paths.extend( paths )
                    
                except queue.Empty:
                    
                    pass
                    
                
            
            # if unparsed_paths still has nothing, we'll nonetheless sleep on new paths
            
            if len( unparsed_paths ) == 0:
                
                try:
                    
                    raw_paths = unparsed_paths_queue.get( timeout = 5 )
                    
                    paths = ClientFiles.GetAllFilePaths( raw_paths, do_human_sort = do_human_sort ) # convert any dirs to subpaths
                    
                    unparsed_paths.extend( paths )
                    
                except queue.Empty:
                    
                    pass
                    
                
                continue # either we added some or didn't--in any case, restart the cycle
                
            
            path = unparsed_paths.popleft()
            
            currently_parsing.set()
            
            # we are now dealing with a file. let's clear out quick no-gos
            
            num_files_done += 1
            
            if path.endswith( os.path.sep + 'Thumbs.db' ) or path.endswith( os.path.sep + 'thumbs.db' ):
                
                HydrusData.Print( 'In import parse, skipping thumbs.db: ' + path )
                
                num_unimportable_mime_files += 1
                
                continue
                
            
            if not os.path.exists( path ):
                
                HydrusData.Print( 'Missing file: ' + path )
                
                num_missing_files += 1
                
                continue
                
            
            if not HydrusPaths.PathIsFree( path ):
                
                HydrusData.Print( 'File currently in use: ' + path )
                
                num_occupied_files += 1
                
                continue
                
            
            size = os.path.getsize( path )
            
            if size == 0:
                
                HydrusData.Print( 'Empty file: ' + path )
                
                num_empty_files += 1
                
                continue
                
            
            # looks good, let's burn some CPU
            
            try:
                
                mime = HydrusFileHandling.GetMime( path )
                
            except Exception as e:
                
                HydrusData.Print( 'Problem parsing mime for: ' + path )
                HydrusData.PrintException( e )
                
                mime = HC.APPLICATION_UNKNOWN
                
            
            if mime in HC.ALLOWED_MIMES:
                
                num_good_files += 1
                
                parsed_path_queue.put( ( path, mime, size ) )
                
            else:
                
                HydrusData.Print( 'Unparsable file: ' + path )
                
                num_unimportable_mime_files += 1
                
            
        
    
    def TIMERUIUpdate( self ):
        
        good_paths = list()
        
        while not self._parsed_path_queue.empty():
            
            ( path, mime, size ) = self._parsed_path_queue.get()
            
            if not self._paths_list.HasData( path ):
                
                good_paths.append( path )
                
                index = len( self._current_path_data ) + 1
                
                self._current_path_data[ path ] = ( index, mime, size )
                
            
        
        if len( good_paths ) > 0:
            
            self._paths_list.AddDatas( good_paths )
            
        
        #
        
        files_in_list = len( self._current_path_data ) > 0
        
        paused = self._pause_event.is_set()
        no_work_in_queue = not self._work_to_do.is_set()
        working_on_a_file_now = self._currently_parsing.is_set()
        
        can_import = files_in_list and ( no_work_in_queue or paused ) and not working_on_a_file_now
        
        if no_work_in_queue:
            
            self._progress_pause.setEnabled( False )
            self._progress_cancel.setEnabled( False )
            
        else:
            
            self._progress_pause.setEnabled( True )
            self._progress_cancel.setEnabled( True )
            
        
        if can_import:
            
            self._add_button.setEnabled( True )
            self._tag_button.setEnabled( True )
            
        else:
            
            self._add_button.setEnabled( False )
            self._tag_button.setEnabled( False )
            
        
        if paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._progress_pause, CC.global_pixmaps().play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._progress_pause, CC.global_pixmaps().pause )
            
        
    
class JobSchedulerPanel( QW.QWidget ):
    
    def __init__( self, parent, controller, scheduler_name ):
        
        self._controller = controller
        self._scheduler_name = scheduler_name
        
        QW.QWidget.__init__( self, parent )
        
        self._list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._list_ctrl_panel, CGLC.COLUMN_LIST_JOB_SCHEDULER_REVIEW.ID, 20, self._ConvertDataToListCtrlTuples )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        # maybe some buttons to control behaviour here for debug
        
        self._list_ctrl_panel.AddButton( 'refresh snapshot', self._RefreshSnapshot )
        
        #
        
        self._list_ctrl.Sort()
        
        self._RefreshSnapshot()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _ConvertDataToListCtrlTuples( self, job: HydrusThreading.SchedulableJob ):
        
        job_type = job.PRETTY_CLASS_NAME
        job_call = job.GetPrettyJob()
        due = job.GetNextWorkTime()
        
        pretty_job_type = job_type
        pretty_job_call = job_call
        pretty_due = job.GetDueString()
        
        display_tuple = ( pretty_job_type, pretty_job_call, pretty_due )
        sort_tuple = ( job_type, job_call, due )
        
        return ( display_tuple, sort_tuple )
        
    
    def _RefreshSnapshot( self ):
        
        jobs = self._controller.GetJobSchedulerSnapshot( self._scheduler_name )
        
        self._list_ctrl.SetData( jobs )
        
    
class ThreadsPanel( QW.QWidget ):
    
    def __init__( self, parent, controller ):
        
        self._controller = controller
        
        QW.QWidget.__init__( self, parent )
        
        self._list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._list_ctrl_panel, CGLC.COLUMN_LIST_THREADS_REVIEW.ID, 20, self._ConvertDataToListCtrlTuples )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        # maybe some buttons to control behaviour here for debug
        
        self._list_ctrl_panel.AddButton( 'refresh snapshot', self._RefreshSnapshot )
        
        #
        
        self._list_ctrl.Sort()
        
        self._RefreshSnapshot()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _ConvertDataToListCtrlTuples( self, thread ):
        
        name = thread.GetName()
        thread_type = repr( type( thread ) )
        current_job = repr( thread.GetCurrentJobSummary() )
        
        pretty_name = name
        pretty_thread_type = thread_type
        pretty_current_job = current_job
        
        display_tuple = ( pretty_name, pretty_thread_type, pretty_current_job )
        sort_tuple = ( name, thread_type, current_job )
        
        return ( display_tuple, sort_tuple )
        
    
    def _RefreshSnapshot( self ):
        
        threads = self._controller.GetThreadsSnapshot()
        
        self._list_ctrl.SetData( threads )
        
    
class ReviewThreads( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._notebook = ClientGUICommon.BetterNotebook( self )
        
        self._thread_panel = ThreadsPanel( self._notebook, controller )
        
        self._fast_scheduler_panel = JobSchedulerPanel( self._notebook, controller, 'fast' )
        
        self._slow_scheduler_panel = JobSchedulerPanel( self._notebook, controller, 'slow' )
        
        self._notebook.addTab( self._thread_panel, 'threads' )
        self._notebook.addTab( self._fast_scheduler_panel, 'fast scheduler' )
        self._notebook.addTab( self._slow_scheduler_panel, 'slow scheduler' )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
class ReviewVacuumData( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller, vacuum_data ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._controller = controller
        self._vacuum_data = vacuum_data
        
        self._currently_vacuuming = False
        
        #
        
        info_message = '''Vacuuming is essentially an aggressive defrag of a database file. The content of the database is copied to a new file, which then has tightly packed pages and no empty 'free' pages.

Because the new database is tightly packed, it will generally be smaller than the original file. This is currently the only way to truncate a hydrus database file.

Vacuuming is an expensive operation. It requires lots of free space on your drive(s), hydrus cannot operate while it is going on, and it tends to run quite slow, about 1-40MB/s. The main benefit is in truncating the database files after you delete a lot of data, so I recommend you only do it on files with a lot of free space.'''
        
        st = ClientGUICommon.BetterStaticText( self, label = info_message )
        
        st.setWordWrap( True )
        
        vacuum_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._vacuum_listctrl = ClientGUIListCtrl.BetterListCtrl( vacuum_listctrl_panel, CGLC.COLUMN_LIST_VACUUM_DATA.ID, 6, self._ConvertNameToListCtrlTuples )
        
        vacuum_listctrl_panel.SetListCtrl( self._vacuum_listctrl )
        
        vacuum_listctrl_panel.AddButton( 'vacuum', self._Vacuum, enabled_check_func = self._CanVacuum )
        
        #
        
        self._vacuum_listctrl.SetData( list( self._vacuum_data.keys() ) )
        
        self._vacuum_listctrl.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, vacuum_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _CanVacuumName( self, name ):
        
        from hydrus.core import HydrusDB
        
        try:
            
            vacuum_dict = self._vacuum_data[ name ]
            
            path = vacuum_dict[ 'path' ]
            page_size = vacuum_dict[ 'page_size' ]
            page_count = vacuum_dict[ 'page_count' ]
            freelist_count = vacuum_dict[ 'freelist_count' ]
            
            HydrusDB.CheckCanVacuumData( path, page_size, page_count, freelist_count )
            
        except Exception as e:
            
            return ( False, str( e ) )
            
        
        return ( True, 'yes!' )
        
    
    def _CanVacuum( self ):
        
        names = self._vacuum_listctrl.GetData( only_selected = True )
        
        if len( names ) == 0:
            
            return False
            
        
        for name in names:
            
            ( result, info ) = self._CanVacuumName( name )
            
            if not result:
                
                return False
                
            
        
        return True
        
    
    def _ConvertNameToListCtrlTuples( self, name ):
        
        vacuum_dict = self._vacuum_data[ name ]
        
        page_size = vacuum_dict[ 'page_size' ]
        
        sort_name = name
        pretty_name = name
        
        sort_total_size = page_size * vacuum_dict[ 'page_count' ]
        pretty_total_size = HydrusData.ToHumanBytes( sort_total_size )
        
        sort_free_size = page_size * vacuum_dict[ 'freelist_count' ]
        pretty_free_size = HydrusData.ToHumanBytes( sort_free_size )
        
        if sort_total_size > 0:
            
            pretty_free_size = '{} ({})'.format( pretty_free_size, HydrusData.ConvertFloatToPercentage( sort_free_size / sort_total_size ) )
            
        
        sort_last_vacuumed = vacuum_dict[ 'last_vacuumed' ]
        
        if sort_last_vacuumed == 0 or sort_last_vacuumed is None:
            
            sort_last_vacuumed = 0
            pretty_last_vacuumed = 'never done'
            
        else:
            
            pretty_last_vacuumed = HydrusData.TimestampToPrettyTimeDelta( sort_last_vacuumed )
            
        
        ( result, info ) = self._CanVacuumName( name )
        
        sort_can_vacuum = result
        pretty_can_vacuum = info
        
        ( sort_vacuum_time_estimate, pretty_vacuum_time_estimate ) = self._GetVacuumTimeEstimate( sort_total_size )
        
        display_tuple = ( pretty_name, pretty_total_size, pretty_free_size, pretty_last_vacuumed, pretty_can_vacuum, pretty_vacuum_time_estimate )
        sort_tuple = ( sort_name, sort_total_size, sort_free_size, sort_last_vacuumed, sort_can_vacuum, sort_vacuum_time_estimate )
        
        return ( display_tuple, sort_tuple )
        
    
    def _GetVacuumTimeEstimate( self, db_size ):
        
        from hydrus.core import HydrusDB
        
        vacuum_time_estimate = HydrusDB.GetApproxVacuumDuration( db_size )
        
        pretty_vacuum_time_estimate = '{} to {}'.format( HydrusData.TimeDeltaToPrettyTimeDelta( vacuum_time_estimate / 40 ), HydrusData.TimeDeltaToPrettyTimeDelta( vacuum_time_estimate ) )
        
        return ( vacuum_time_estimate, pretty_vacuum_time_estimate )
        
    
    def _Vacuum( self ):
        
        names = list( self._vacuum_listctrl.GetData( only_selected = True ) )
        
        if len( names ) > 0:
            
            total_size = sum( ( vd[ 'page_size' ] * vd[ 'page_count' ] for vd in ( self._vacuum_data[ name ] for name in names ) ) )
            
            ( sort_time_estimate, pretty_time_estimate ) = self._GetVacuumTimeEstimate( total_size )
            
            message = 'Do vacuum now? Estimated time to vacuum is {}.'.format( pretty_time_estimate )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
            
            if result == QW.QDialog.Accepted:
                
                self._controller.Write( 'vacuum', names )
                
                self._OKParent()
                
            
        
    
