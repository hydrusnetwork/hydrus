import collections
import os
import queue
import threading
import time
import typing

from PIL import ExifTags

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusCompression
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusTagArchive
from hydrus.core import HydrusText
from hydrus.core import HydrusThreading
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusFileHandling

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientFiles
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientMigration
from hydrus.client import ClientParsing
from hydrus.client import ClientFilesPhysical
from hydrus.client import ClientRendering
from hydrus.client import ClientSerialisable
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUICharts
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIDragDrop
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUITags
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.importing import ClientGUIImport
from hydrus.client.gui.importing import ClientGUIImportOptions
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.search import ClientGUILocation
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIControls
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.importing.options import FileImportOptions
from hydrus.client.metadata import ClientTags
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingGUG
from hydrus.client.networking import ClientNetworkingLogin
from hydrus.client.networking import ClientNetworkingURLClass
from hydrus.client.search import ClientSearch

class AboutPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, name, version, description, license_text, developers, site ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        icon_label = ClientGUICommon.BetterStaticText( self )
        icon_label.setPixmap( CG.client_controller.frame_icon_pixmap )
        
        name_label = ClientGUICommon.BetterStaticText( self, name )
        name_label_font = name_label.font()
        name_label_font.setBold( True )
        name_label.setFont( name_label_font )
        
        version_label = ClientGUICommon.BetterStaticText( self, version )
        
        tabwidget = QW.QTabWidget( self )
        
        desc_panel = QW.QWidget( self )
        
        desc_label = ClientGUICommon.BetterStaticText( self, description )
        desc_label.setAlignment( QC.Qt.AlignHCenter | QC.Qt.AlignVCenter )
        
        url_label = ClientGUICommon.BetterHyperLink( self, site, site )
        
        credits = QW.QTextEdit( self )
        credits.setPlainText( 'Created by ' + ', '.join( developers ) )
        credits.setReadOnly( True )
        credits.setAlignment( QC.Qt.AlignHCenter )
        
        license_textedit = QW.QTextEdit( self )
        license_textedit.setPlainText( license_text )
        license_textedit.setReadOnly( True )
        
        tabwidget.addTab( desc_panel, 'Description' )
        tabwidget.addTab( credits, 'Credits' )
        tabwidget.addTab( license_textedit, 'License' )
        tabwidget.setCurrentIndex( 0 )
        
        desc_layout = QP.VBoxLayout()
        
        QP.AddToLayout( desc_layout, desc_label, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( desc_layout, url_label, CC.FLAGS_CENTER_PERPENDICULAR )
        
        desc_panel.setLayout( desc_layout )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, icon_label, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( vbox, name_label, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( vbox, version_label, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( vbox, tabwidget, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    

class MoveMediaFilesPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller ):
        
        self._controller = controller
        
        self._new_options = self._controller.new_options
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._client_files_subfolders = CG.client_controller.Read( 'client_files_subfolders' )
        
        ( self._media_base_locations, self._ideal_thumbnails_base_location_override ) = self._controller.Read( 'ideal_client_files_locations' )
        
        service_info = CG.client_controller.Read( 'service_info', CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
        
        self._all_local_files_total_size = service_info[ HC.SERVICE_INFO_TOTAL_SIZE ]
        self._all_local_files_total_num = service_info[ HC.SERVICE_INFO_NUM_FILES ]
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DATABASE_MIGRATION )
        
        menu_items.append( ( 'normal', 'open the html migration help', 'Open the help page for database migration in your web browser.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuBitmapButton( self, CC.global_pixmaps().help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', object_name = 'HydrusIndeterminate' )
        
        #
        
        info_panel = ClientGUICommon.StaticBox( self, 'database components' )
        
        self._current_install_path_st = ClientGUICommon.BetterStaticText( info_panel )
        self._current_db_path_st = ClientGUICommon.BetterStaticText( info_panel )
        self._current_media_paths_st = ClientGUICommon.BetterStaticText( info_panel )
        
        file_locations_panel = ClientGUICommon.StaticBox( self, 'media file locations' )
        
        current_media_base_locations_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( file_locations_panel )
        
        self._current_media_base_locations_listctrl = ClientGUIListCtrl.BetterListCtrl( current_media_base_locations_listctrl_panel, CGLC.COLUMN_LIST_DB_MIGRATION_LOCATIONS.ID, 8, self._ConvertLocationToListCtrlTuples, activation_callback = self._SetMaxNumBytes )
        self._current_media_base_locations_listctrl.setSelectionMode( QW.QAbstractItemView.SingleSelection )
        
        self._current_media_base_locations_listctrl.Sort()
        
        current_media_base_locations_listctrl_panel.SetListCtrl( self._current_media_base_locations_listctrl )
        
        current_media_base_locations_listctrl_panel.AddButton( 'add new location for files', self._SelectPathToAdd )
        current_media_base_locations_listctrl_panel.AddButton( 'increase location weight', self._IncreaseWeight, enabled_check_func = self._CanIncreaseWeight )
        current_media_base_locations_listctrl_panel.AddButton( 'decrease location weight', self._DecreaseWeight, enabled_check_func = self._CanDecreaseWeight )
        current_media_base_locations_listctrl_panel.AddButton( 'set max size', self._SetMaxNumBytes, enabled_check_func = self._CanSetMaxNumBytes )
        current_media_base_locations_listctrl_panel.AddButton( 'remove location', self._RemoveSelectedBaseLocation, enabled_check_func = self._CanRemoveLocation )
        
        self._thumbnails_location = QW.QLineEdit( file_locations_panel )
        self._thumbnails_location.setEnabled( False )
        
        self._thumbnails_location_set = ClientGUICommon.BetterButton( file_locations_panel, 'set', self._SetThumbnailLocation )
        
        self._thumbnails_location_clear = ClientGUICommon.BetterButton( file_locations_panel, 'clear', self._ClearThumbnailLocation )
        
        self._rebalance_status_st = ClientGUICommon.BetterStaticText( file_locations_panel )
        self._rebalance_status_st.setAlignment( QC.Qt.AlignRight | QC.Qt.AlignVCenter )
        
        self._rebalance_button = ClientGUICommon.BetterButton( file_locations_panel, 'move files now', self._Rebalance )
        
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
        
        file_locations_panel.Add( current_media_base_locations_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        file_locations_panel.Add( t_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        file_locations_panel.Add( rebalance_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        message = 'THIS IS ADVANCED. DO NOT CHANGE ANYTHING HERE UNLESS YOU KNOW WHAT IT DOES!'
        
        warning_st = ClientGUICommon.BetterStaticText( self, label = message )
        
        warning_st.setObjectName( 'HydrusWarning' )
        
        QP.AddToLayout( vbox, warning_st, CC.FLAGS_CENTER )
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, file_locations_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, 100 )
        
        self.setMinimumWidth( min_width )
        
        self._Update()
        
    
    def _AddBaseLocation( self, base_location ):
        
        if base_location in self._media_base_locations:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'You already have that location entered!' )
            
            return
            
        
        if self._ideal_thumbnails_base_location_override is not None and base_location.path == self._ideal_thumbnails_base_location_override.path:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'That path is already used as the special thumbnail location--please choose another.' )
            
            return
            
        
        self._media_base_locations.add( base_location )
        
        self._SaveToDB()
        
    
    def _AdjustWeight( self, amount ):
        
        base_locations = self._current_media_base_locations_listctrl.GetData( only_selected = True )
        
        if len( base_locations ) > 0:
            
            base_location = base_locations[0]
            
            if base_location in self._media_base_locations:
                
                new_amount = base_location.ideal_weight + amount
                
                if new_amount > 0:
                    
                    base_location.ideal_weight = new_amount
                    
                    self._SaveToDB()
                    
                elif new_amount <= 0:
                    
                    self._RemoveBaseLocation( base_location )
                    
                
            else:
                
                if amount > 0:
                    
                    new_base_location = ClientFilesPhysical.FilesStorageBaseLocation( base_location.path, amount )
                    
                    if base_location != self._ideal_thumbnails_base_location_override:
                        
                        self._AddBaseLocation( new_base_location )
                        
                    
                
            
        
    
    def _CanDecreaseWeight( self ):
        
        base_locations = self._current_media_base_locations_listctrl.GetData( only_selected = True )
        
        if len( base_locations ) > 0:
            
            base_location = base_locations[0]
            
            if base_location in self._media_base_locations:
                
                is_big = base_location.ideal_weight > 1
                others_can_take_slack = len( self._media_base_locations ) > 1
                
                if is_big or others_can_take_slack:
                    
                    return True
                    
                
            
        
        return False
        
    
    def _CanIncreaseWeight( self ):
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        base_locations = self._current_media_base_locations_listctrl.GetData( only_selected = True )
        
        if len( base_locations ) > 0:
            
            base_location = base_locations[0]
            
            if base_location in self._media_base_locations:
                
                if len( self._media_base_locations ) > 1:
                    
                    return True
                    
                
            elif base_location in locations_to_file_weights:
                
                return True
                
            
        
        return False
        
    
    def _CanRemoveLocation( self ):
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        base_locations = self._current_media_base_locations_listctrl.GetData( only_selected = True )
        
        if len( base_locations ) > 0:
            
            base_location = base_locations[0]
            
            if base_location in self._media_base_locations:
                
                others_can_take_slack = len( self._media_base_locations ) > 1
                
                if others_can_take_slack:
                    
                    return True
                    
                
            
        
        return False
        
    
    def _CanSetMaxNumBytes( self ):
        
        only_one_location_is_limitless = len( [ 1 for base_location in self._media_base_locations if base_location.max_num_bytes is None ] ) == 1
        
        base_locations = self._current_media_base_locations_listctrl.GetData( only_selected = True )
        
        if len( base_locations ) > 0:
            
            base_location = base_locations[0]
            
            if base_location in self._media_base_locations:
                
                if base_location.max_num_bytes is None and only_one_location_is_limitless:
                    
                    return False
                    
                
                return True
                
            
        
        return False
        
    
    def _ClearThumbnailLocation( self ):
        
        message = 'Clear the custom thumbnail location? This will schedule all the thumbnail files to migrate back into the regular file locations.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.Accepted:
            
            return
            
        
        self._ideal_thumbnails_base_location_override = None
        
        self._SaveToDB()
        
    
    def _ConvertLocationToListCtrlTuples( self, base_location: ClientFilesPhysical.FilesStorageBaseLocation ):
        
        f_space = self._all_local_files_total_size
        ( t_space_min, t_space_max ) = self._GetThumbnailSizeEstimates()
        
        # current
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        #
        
        path = base_location.path
        
        if os.path.exists( path ):
            
            pretty_location = path
            
            try:
                
                free_space = HydrusPaths.GetFreeSpace( path )
                pretty_free_space = HydrusData.ToHumanBytes( free_space )
                
            except Exception as e:
                
                message = 'There was a problem finding the free space for "{path}"! Perhaps this location does not exist?'
                
                HydrusData.Print( message )
                
                HydrusData.PrintException( e )
                
                free_space = 0
                pretty_free_space = 'problem finding free space'
                
            
        else:
            
            pretty_location = 'DOES NOT EXIST: {}'.format( path )
            
            free_space = 0
            pretty_free_space = 'DOES NOT EXIST'
            
        
        portable_location = HydrusPaths.ConvertAbsPathToPortablePath( base_location.path )
        portable = not os.path.isabs( portable_location )
        
        if portable:
            
            pretty_portable = 'yes'
            
        else:
            
            pretty_portable = 'no'
            
        
        fp = locations_to_file_weights[ base_location ]
        tp = locations_to_thumb_weights[ base_location ]
        
        p = HydrusData.ConvertFloatToPercentage
        
        current_bytes = fp * f_space + tp * t_space_max
        
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
        
        if base_location in self._media_base_locations:
            
            ideal_weight = base_location.ideal_weight
            
            pretty_ideal_weight = str( int( ideal_weight ) )
            
        else:
            
            ideal_weight = 0
            
            if base_location in locations_to_file_weights:
                
                pretty_ideal_weight = '0'
                
            else:
                
                pretty_ideal_weight = 'n/a'
                
            
        
        if base_location.max_num_bytes is None:
            
            pretty_max_num_bytes = 'n/a'
            sort_max_num_bytes = -1
            
        else:
            
            pretty_max_num_bytes = HydrusData.ToHumanBytes( base_location.max_num_bytes )
            sort_max_num_bytes = base_location.max_num_bytes
            
        
        ideal_fp = self._media_base_locations_to_ideal_usage.get( base_location, 0.0 )
        
        if self._ideal_thumbnails_base_location_override is None:
            
            ideal_tp = ideal_fp
            
        else:
            
            if base_location == self._ideal_thumbnails_base_location_override:
                
                ideal_tp = 1.0
                
            else:
                
                ideal_tp = 0.0
                
            
        
        ideal_bytes = ideal_fp * f_space + ideal_tp * t_space_max
        
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
            
        
        display_tuple = ( pretty_location, pretty_portable, pretty_free_space, pretty_current_usage, pretty_ideal_weight, pretty_max_num_bytes, pretty_ideal_usage )
        sort_tuple = ( pretty_location, portable, free_space, ideal_weight, ideal_usage, sort_max_num_bytes, current_usage )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DecreaseWeight( self ):
        
        self._AdjustWeight( -1 )
        
    
    def _GetLocationsToCurrentWeights( self ):
        
        locations_to_file_weights = collections.Counter()
        locations_to_thumb_weights = collections.Counter()
        
        for client_files_subfolder in self._client_files_subfolders:
            
            prefix = client_files_subfolder.prefix
            base_location = client_files_subfolder.base_location
            
            subfolder_weight = client_files_subfolder.GetNormalisedWeight()
            
            if prefix.startswith( 'f' ):
                
                locations_to_file_weights[ base_location ] += subfolder_weight
                
            
            if prefix.startswith( 't' ):
                
                locations_to_thumb_weights[ base_location ] += subfolder_weight
                
            
        
        return ( locations_to_file_weights, locations_to_thumb_weights )
        
    
    def _GetListCtrlLocations( self ):
        
        # current
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        #
        
        all_locations = set()
        
        all_locations.update( self._media_base_locations )
        
        if self._ideal_thumbnails_base_location_override is not None:
            
            all_locations.add( self._ideal_thumbnails_base_location_override )
            
        
        all_locations.update( locations_to_file_weights.keys() )
        all_locations.update( locations_to_thumb_weights.keys() )
        
        all_locations = list( all_locations )
        
        return all_locations
        
    
    def _GetThumbnailSizeEstimates( self ):
        
        ( t_width, t_height ) = CG.client_controller.options[ 'thumbnail_dimensions' ]
        
        typical_thumb_num_pixels = 320 * 240
        typical_thumb_size = 36 * 1024
        
        our_thumb_num_pixels = t_width * t_height
        our_thumb_size_estimate = typical_thumb_size * ( our_thumb_num_pixels / typical_thumb_num_pixels )
        
        our_total_thumb_size_estimate = self._all_local_files_total_num * our_thumb_size_estimate
        
        return ( int( our_total_thumb_size_estimate * 0.8 ), int( our_total_thumb_size_estimate * 1.4 ) )
        
    
    def _IncreaseWeight( self ):
        
        self._AdjustWeight( 1 )
        
    
    def _Rebalance( self ):
        
        for base_location in self._GetListCtrlLocations():
            
            if not os.path.exists( base_location.path ):
                
                message = 'The path "{}" does not exist! Please ensure all the locations on this dialog are valid before trying to rebalance your files.'.format( base_location )
                
                ClientGUIDialogsMessage.ShowWarning( self, message )
                
                return
                
            
        
        
        message = 'Moving files can be a slow and slightly laggy process, with the UI intermittently hanging, which sometimes makes manually stopping a large ongoing job difficult. Would you like to set a max runtime on this job?'
        
        yes_tuples = []
        
        yes_tuples.append( ( 'run for 10 minutes', 600 ) )
        yes_tuples.append( ( 'run for 30 minutes', 1800 ) )
        yes_tuples.append( ( 'run for 1 hour', 3600 ) )
        yes_tuples.append( ( 'run indefinitely', None ) )
        
        try:
            
            result = ClientGUIDialogsQuick.GetYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if result is None:
            
            stop_time = None
            
        else:
            
            stop_time = HydrusTime.GetNow() + result
            
        
        job_status = ClientThreading.JobStatus( cancellable = True, stop_time = stop_time )
        
        CG.client_controller.pub( 'do_file_storage_rebalance', job_status )
        
        self._OKParent()
        
    
    def _RemoveBaseLocation( self, base_location ):
        
        ( locations_to_file_weights, locations_to_thumb_weights ) = self._GetLocationsToCurrentWeights()
        
        removees = set()
        
        if base_location not in self._media_base_locations:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Please select a location with weight.' )
            
            return
            
        
        if len( self._media_base_locations ) == 1:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'You cannot empty every single current file location--please add a new place for the files to be moved to and then try again.' )
            
        
        if os.path.exists( base_location.path ):
            
            if base_location in locations_to_file_weights:
                
                message = 'Are you sure you want to remove this location? This will schedule all of the files it is currently responsible for to be moved elsewhere.'
                
            else:
                
                message = 'Are you sure you want to remove this location?'
                
            
        else:
            
            if base_location in locations_to_file_weights:
                
                message = 'This path does not exist, but it seems to have files. This could be a critical error that has occurred while the client is open (maybe a drive unmounting?). I recommend you do not remove it here and instead shut the client down immediately and fix the problem, then restart it, which will run the \'recover missing file locations\' routine if needed.'
                
            else:
                
                message = 'This path does not exist. Just checking, but I recommend you remove it.'
                
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            self._media_base_locations.remove( base_location )
            
            self._SaveToDB()
            
        
    
    def _RemoveSelectedBaseLocation( self ):
        
        locations = self._current_media_base_locations_listctrl.GetData( only_selected = True )
        
        if len( locations ) > 0:
            
            location = locations[0]
            
            self._RemoveBaseLocation( location )
            
        
    
    def _SaveToDB( self ):
        
        self._controller.Write( 'ideal_client_files_locations', self._media_base_locations, self._ideal_thumbnails_base_location_override )
        
        self._controller.client_files_manager.Reinit()
        
        self._Update()
        
    
    def _SelectPathToAdd( self ):
        
        with QP.DirDialog( self, 'Select location' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                base_location = ClientFilesPhysical.FilesStorageBaseLocation( path, 1 )
                
                self._AddBaseLocation( base_location )
                
            
        
    
    def _SetMaxNumBytes( self ):
        
        if not self._CanSetMaxNumBytes():
            
            return
            
        
        base_locations = self._current_media_base_locations_listctrl.GetData( only_selected = True )
        
        if len( base_locations ) > 0:
            
            base_location = base_locations[0]
            
            if base_location in self._media_base_locations:
                
                max_num_bytes = base_location.max_num_bytes
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit max size' ) as dlg:
                    
                    message = 'If a location goes over its set size, it will schedule to migrate some files to other locations. At least one media location must have no limit.'
                    message += '\n' * 2
                    message += 'This is not precise (it works on average size, and thumbnails can add a bit), so give it some padding. Also, in general, remember it is not healthy to fill any hard drive more than 90% full.'
                    message += '\n' * 2
                    message += 'Also, this feature is under active development. The client will go over this limit if your collection grows significantly--the only way things rebalance atm are if you click "move files now"--but in future I will have things automatically migrate in the background to ensure limits are obeyed. This is just for advanced users to play with for now!'
                    
                    panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg, message = message )
                    
                    control = ClientGUIControls.NoneableBytesControl( panel, initial_value = 100 * ( 1024 ** 3 ) )
                    
                    control.SetValue( max_num_bytes )
                    
                    panel.SetControl( control )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        max_num_bytes = control.GetValue()
                        
                        base_location.max_num_bytes = max_num_bytes
                        
                        self._SaveToDB()
                        
                    
                
            
        
    
    def _SetThumbnailLocation( self ):
        
        with QP.DirDialog( self, 'Select thumbnail location' ) as dlg:
            
            if self._ideal_thumbnails_base_location_override is not None:
                
                dlg.setDirectory( self._ideal_thumbnails_base_location_override.path )
                
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                all_paths = { base_location.path for base_location in self._media_base_locations }
                
                if path in all_paths:
                    
                    ClientGUIDialogsMessage.ShowWarning( self, 'That path already exists as a regular file location! Please choose another.' )
                    
                else:
                    
                    self._ideal_thumbnails_base_location_override = ClientFilesPhysical.FilesStorageBaseLocation( path, 1 )
                    
                    self._SaveToDB()
                    
                
            
        
    
    def _Update( self ):
        
        self._client_files_subfolders = CG.client_controller.Read( 'client_files_subfolders' )
        
        ( self._media_base_locations, self._ideal_thumbnails_base_location_override ) = self._controller.Read( 'ideal_client_files_locations' )
        
        self._media_base_locations_to_ideal_usage = ClientFilesPhysical.FilesStorageBaseLocation.STATICGetIdealWeights( self._all_local_files_total_size, self._media_base_locations )
        
        approx_total_db_size = self._controller.db.GetApproxTotalFileSize()
        
        self._current_db_path_st.setText( 'database (about '+HydrusData.ToHumanBytes(approx_total_db_size)+'): '+self._controller.GetDBDir() )
        self._current_install_path_st.setText( 'install: ' + HC.BASE_DIR )
        
        approx_total_client_files = self._all_local_files_total_size
        ( approx_total_thumbnails_min, approx_total_thumbnails_max ) = self._GetThumbnailSizeEstimates()
        
        label = 'media is {}, thumbnails are estimated at {}-{}'.format( HydrusData.ToHumanBytes( approx_total_client_files ), HydrusData.ToHumanBytes( approx_total_thumbnails_min ), HydrusData.ToHumanBytes( approx_total_thumbnails_max ) )
        
        self._current_media_paths_st.setText( label )
        self._current_media_paths_st.setToolTip( 'Precise thumbnail sizes are not tracked, so this is an estimate based on your current thumbnail dimensions.' )
        
        base_locations = self._GetListCtrlLocations()
        
        self._current_media_base_locations_listctrl.SetData( base_locations )
        
        #
        
        if self._ideal_thumbnails_base_location_override is None:
            
            self._thumbnails_location.setText( 'none set' )
            
            self._thumbnails_location_set.setEnabled( True )
            self._thumbnails_location_clear.setEnabled( False )
            
        else:
            
            self._thumbnails_location.setText( self._ideal_thumbnails_base_location_override.path )
            
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
            
        
        self._migration_content_type.setToolTip( 'Sets what will be migrated.' )
        
        self._migration_source = ClientGUICommon.BetterChoice( self._migration_panel )
        
        location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
        
        self._migration_source_hash_type_st = ClientGUICommon.BetterStaticText( self._migration_panel, 'hash type: unknown' )
        
        self._migration_source_hash_type_st.setToolTip( 'If this is something other than sha256, this will only work for files the client has ever previously imported.' )
        
        self._migration_source_content_status_filter = ClientGUICommon.BetterChoice( self._migration_panel )
        
        self._migration_source_content_status_filter.setToolTip( 'This filters which status of tags will be migrated.' )
        
        self._migration_source_file_filtering_type = ClientGUICommon.BetterChoice( self._migration_panel )
        
        self._migration_source_file_filtering_type.addItem( 'file domain', self.LOCATION_CONTEXT_LOCATION )
        
        if self._hashes is not None:
            
            self._migration_source_file_filtering_type.addItem( '{} files'.format( HydrusData.ToHumanInt( len( self._hashes ) ) ), self.HASHES_LOCATION )
            
            self._migration_source_file_filtering_type.SetValue( self.HASHES_LOCATION )
            
        
        self._migration_source_file_filtering_type.setToolTip( 'Choose whether to do this operation for the files you launched the dialog on, or a whole file domain.' )
        
        self._migration_source_location_context_button = ClientGUILocation.LocationSearchContextButton( self._migration_panel, location_context )
        self._migration_source_location_context_button.setToolTip( 'Set which files should be eligible. This can get as complicated as you like!' )
        
        self._migration_source_archive_path_button = ClientGUICommon.BetterButton( self._migration_panel, 'no path set', self._SetSourceArchivePath )
        
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
        message += os.linesep * 2
        message += 'To delete content en masse from one location, select what you want to delete with the filter and set the source and destination the same.'
        message += os.linesep * 2
        message += 'These migrations can be powerful, so be very careful that you understand what you are doing and choose what you want. Large jobs may have a significant initial setup time, during which case the client may hang briefly, but once they start they are pausable or cancellable. If you do want to perform a large action, it is a good idea to back up your database first, just in case you get a result you did not intend.'
        message += os.linesep * 2
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
        message += os.linesep * 2
        message += title
        message += os.linesep * 2
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
        self._migration_source_archive_path_button.setToolTip( '' )
        
        self._migration_destination_archive_path_button.setText( 'no path set' )
        self._migration_destination_archive_path_button.setToolTip( '' )
        
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
        
    
class ReviewDownloaderImport( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, network_engine ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._network_engine = network_engine
        
        vbox = QP.VBoxLayout()
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_ADDING_NEW_DOWNLOADERS )
        
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
        
        if CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
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
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem loading PNG!', str(e) )
                
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
                        
                    
                    ClientGUIDialogsMessage.ShowCritical( self, 'Serialisation Object Load Error!', message )
                    
                    have_shown_load_error = True
                    
                
                continue
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Error', 'I could not understand what was encoded in {}!'.format( payload_description ) )
                
                continue
                
            
            if isinstance( obj_list, ( ClientNetworkingGUG.GalleryURLGenerator, ClientNetworkingGUG.NestedGalleryURLGenerator, ClientNetworkingURLClass.URLClass, ClientParsing.PageParser, ClientNetworkingDomain.DomainMetadataPackage, ClientNetworkingLogin.LoginScriptDomain ) ):
                
                obj_list = HydrusSerialisable.SerialisableList( [ obj_list ] )
                
            
            if not isinstance( obj_list, HydrusSerialisable.SerialisableList ):
                
                ClientGUIDialogsMessage.ShowWarning( self, 'Unfortunately, {} did not look like a package of download data! Instead, it looked like: {}'.format( payload_description, obj_list.SERIALISABLE_NAME ) )
                
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
                
                ClientGUIDialogsMessage.ShowWarning( self, 'I found '+HydrusData.ToHumanInt(num_misc_objects)+' misc objects in that png, but nothing downloader related.' )
                
            
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
            
            ClientGUIDialogsMessage.ShowInformation( self, f'All {HydrusData.ToHumanInt( total_num_dupes )} downloader objects in that package appeared to already be in the client, so nothing need be added.' )
            
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
                
                ClientGUIDialogsMessage.ShowInformation( self, new_dm.GetDetailedSafeSummary() )
                
            
        
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
        domain_manager.AutoAddDomainMetadatas( new_domain_metadatas, approved = ClientNetworkingDomain.VALID_APPROVED )
        login_manager.AutoAddLoginScripts( new_login_scripts )
        
        num_new_gugs = len( new_gugs )
        num_aux = len( new_url_classes ) + len( new_parsers ) + len( new_login_scripts ) + len( new_domain_metadatas )
        
        final_message = 'Successfully added ' + HydrusData.ToHumanInt( num_new_gugs ) + ' new downloaders and ' + HydrusData.ToHumanInt( num_aux ) + ' auxiliary objects.'
        
        if total_num_dupes > 0:
            
            final_message += ' ' + HydrusData.ToHumanInt( total_num_dupes ) + ' duplicate objects were not added (but some additional metadata may have been merged).'
            
        
        ClientGUIDialogsMessage.ShowInformation( self, final_message )
        
    
    def _Paste( self ):
        
        if CG.client_controller.ClipboardHasImage():
            
            try:
                
                qt_image = CG.client_controller.GetClipboardImage()
                
                payload_description = 'clipboard image data'
                payload = ClientSerialisable.LoadFromQtImage( qt_image )
                
            except Exception as e:
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting image!', f'Sorry, seemed to be a problem: {e}' )
                
                return
                
            
        else:
            
            try:
                
                raw_text = CG.client_controller.GetClipboardText()
                
                payload_description = 'clipboard text data'
                payload = HydrusCompression.CompressStringToBytes( raw_text )
                
            except HydrusExceptions.DataMissing as e:
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem pasting text!', f'Sorry, seemed to be a problem: {e}' )
                
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
        
    

class ReviewFileEmbeddedMetadata( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, exif_dict: typing.Optional[ dict ], file_text: typing.Optional[ str ], extra_rows: typing.List[ typing.Tuple[ str, str ] ] ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        #
        
        exif_panel = ClientGUICommon.StaticBox( self, 'EXIF' )
        
        label = 'Double-click a row to copy its value to clipboard.'
        
        st = ClientGUICommon.BetterStaticText( exif_panel, label = label )
        
        st.setWordWrap( True )
        st.setAlignment( QC.Qt.AlignCenter )
        
        self._exif_listctrl = ClientGUIListCtrl.BetterListCtrl( exif_panel, CGLC.COLUMN_LIST_EXIF_DATA.ID, 16, self._ConvertEXIFToListCtrlTuples, activation_callback = self._CopyRow )
        
        exif_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        exif_panel.Add( self._exif_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        text_panel = ClientGUICommon.StaticBox( self, 'embedded text' )
        
        self._text = QW.QPlainTextEdit( text_panel )
        self._text.setReadOnly( True )
        
        text_panel.Add( self._text, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        extra_rows_panel = ClientGUICommon.StaticBox( self, 'extra info' )
        
        rows = [ ( f'{key}: ', ClientGUICommon.BetterStaticText( extra_rows_panel, label = value ) ) for ( key, value ) in extra_rows ]
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        extra_rows_panel.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        if exif_dict is None:
            
            exif_panel.setVisible( False )
            
        else:
            
            datas = []
            
            for ( exif_id, value ) in exif_dict.items():
                
                if isinstance( value, dict ):
                    
                    datas.extend( value.items() )
                    
                else:
                    
                    datas.append( ( exif_id, value ) )
                    
                
            
            self._exif_listctrl.AddDatas( datas )
            
        
        if file_text is None:
            
            text_panel.setVisible( False )
            
        else:
            
            self._text.setPlainText( file_text )
            
        
        if len( extra_rows ) == 0:
            
            extra_rows_panel.setVisible( False )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, exif_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, text_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, extra_rows_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def _ConvertEXIFToListCtrlTuples( self, exif_tuple ):
    
        ( exif_id, raw_value ) = exif_tuple
        
        if exif_id in ExifTags.TAGS:
            
            label = ExifTags.TAGS[ exif_id ]
            pretty_label = label
            
        elif exif_id in ExifTags.GPSTAGS:
            
            label = ExifTags.GPSTAGS[ exif_id ]
            pretty_label = label
            
        else:
            
            label = 'zzz'
            pretty_label = 'Unknown'
            
        
        pretty_id = str( exif_id )
        
        if isinstance( raw_value, bytes ):
            
            value = raw_value.hex()
            pretty_value = '{}: {}'.format( HydrusData.ToHumanBytes( len( raw_value ) ), value )
            
        else:
            
            value = str( raw_value )
            
            if HydrusText.NULL_CHARACTER in value:
                
                value = value.replace( HydrusText.NULL_CHARACTER, '[null]' )
                
            
            pretty_value = value
            
        
        display_tuple = ( pretty_id, pretty_label, pretty_value )
        sort_tuple = ( exif_id, label, value )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopyRow( self ):
        
        selected_exif_tuples = self._exif_listctrl.GetData( only_selected = True )
        
        if len( selected_exif_tuples ) == 0:
            
            return
            
        
        ( first_row_id, first_row_value ) = selected_exif_tuples[0]
        
        if isinstance( first_row_value, bytes ):
            
            copy_text = first_row_value.hex()
            
        else:
            
            copy_text = str( first_row_value )
            
        
        CG.client_controller.pub( 'clipboard', 'text', copy_text )
        
    
class ReviewFileHistory( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._job_status = ClientThreading.JobStatus()
        
        #
        
        self._search_panel = QW.QWidget( self )
        
        # TODO: ok add 'num_steps' as a control, and a date range
        
        panel_vbox = QP.VBoxLayout()
        
        file_search_context = ClientSearch.FileSearchContext(
            location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
        )
        
        page_key = b'mr bones placeholder'
        
        self._tag_autocomplete = ClientGUIACDropdown.AutoCompleteDropdownTagsRead(
            self._search_panel,
            page_key,
            file_search_context,
            allow_all_known_files = False,
            force_system_everything = True,
            fixed_results_list_height = 8
        )
        
        self._loading_text = ClientGUICommon.BetterStaticText( self._search_panel )
        self._loading_text.setAlignment( QC.Qt.AlignVCenter | QC.Qt.AlignRight )
        
        self._cancel_button = ClientGUICommon.BetterBitmapButton( self._search_panel, CC.global_pixmaps().stop, self._CancelCurrentSearch )
        self._refresh_button = ClientGUICommon.BetterBitmapButton( self._search_panel, CC.global_pixmaps().refresh, self._RefreshSearch )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._loading_text, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._cancel_button, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._refresh_button, CC.FLAGS_CENTER )
        
        QP.AddToLayout( panel_vbox, self._tag_autocomplete, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( panel_vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        panel_vbox.addStretch( 1 )
        
        self._search_panel.setLayout( panel_vbox )
        
        #
        
        self._file_history_chart_panel = QW.QWidget( self )
        
        self._file_history_vbox = QP.VBoxLayout()
        
        self._status_st = ClientGUICommon.BetterStaticText( self._file_history_chart_panel, label = f'loading{HC.UNICODE_ELLIPSIS}' )
        
        self._flip_deleted = QW.QCheckBox( 'show deleted', self._file_history_chart_panel )
        
        self._flip_deleted.setChecked( True )
        
        self._file_history_chart = QW.QWidget( self._file_history_chart_panel )
        
        QP.AddToLayout( self._file_history_vbox, self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( self._file_history_vbox, self._flip_deleted, CC.FLAGS_CENTER )
        QP.AddToLayout( self._file_history_vbox, self._file_history_chart, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._file_history_chart_panel.setLayout( self._file_history_vbox )
        
        #
        
        self._hbox = QP.HBoxLayout()
        
        QP.AddToLayout( self._hbox, self._search_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( self._hbox, self._file_history_chart_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( self._hbox )
        
        self._tag_autocomplete.searchChanged.connect( self._RefreshSearch )
        
        self._RefreshSearch()
        
    
    def _CancelCurrentSearch( self ):
        
        self._job_status.Cancel()
        
        self._cancel_button.setEnabled( False )
        
    
    def _RefreshSearch( self ):
        
        def work_callable():
            
            try:
                
                file_history = CG.client_controller.Read( 'file_history', num_steps, file_search_context = file_search_context, job_status = job_status )
                
            except HydrusExceptions.DBException as e:
                
                if isinstance( e.db_e, HydrusExceptions.TooComplicatedM8 ):
                    
                    return -1
                    
                
                raise
                
            
            return file_history
            
        
        def publish_callable( file_history ):
            
            try:
                
                if file_history == -1:
                    
                    self._status_st.setText( 'Sorry, this domain is too complicated to calculate for now, try something simpler!' )
                    
                    return
                    
                elif job_status.IsCancelled():
                    
                    self._status_st.setText( 'Cancelled!' )
                    
                    return
                    
                
                self._file_history_vbox.removeWidget( self._file_history_chart )
                
                show_deleted = self._flip_deleted.isChecked()
                
                # TODO: presumably the thing here is to have SetValue on this widget so we can simply clear/set it rather than the mickey-mouse replace
                self._file_history_chart = ClientGUICharts.FileHistory( self._file_history_chart_panel, file_history, show_deleted )
                
                self._file_history_chart.setMinimumSize( 720, 480 )
                
                self._flip_deleted.clicked.connect( self._file_history_chart.FlipDeletedVisible )
                
                QP.AddToLayout( self._file_history_vbox, self._file_history_chart, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                self._status_st.setVisible( False )
                self._flip_deleted.setVisible( True )
                
            finally:
                
                self._cancel_button.setEnabled( False )
                self._refresh_button.setEnabled( True )
                
            
        
        if not self._tag_autocomplete.IsSynchronised():
            
            self._refresh_button.setEnabled( False )
            
            return
            
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        
        num_steps = 7680
        
        self._cancel_button.setEnabled( True )
        self._refresh_button.setEnabled( False )
        
        self._status_st.setText( 'loading' + HC.UNICODE_ELLIPSIS )
        self._status_st.setVisible( True )
        
        self._flip_deleted.setVisible( False )
        self._file_history_chart.setVisible( False )
        
        self._job_status.Cancel()
        
        job_status = ClientThreading.JobStatus()
        
        self._job_status = job_status
        
        self._update_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        self._update_job.start()
        
    
class ReviewFileMaintenance( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, stats ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._hash_ids = None
        self._job_types_to_due_counts = {}
        self._job_types_to_not_due_counts = {}
        
        self._notebook = ClientGUICommon.BetterNotebook( self )
        
        #
        
        self._current_work_panel = QW.QWidget( self._notebook )
        
        jobs_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._current_work_panel )
        
        self._jobs_listctrl = ClientGUIListCtrl.BetterListCtrl( jobs_listctrl_panel, CGLC.COLUMN_LIST_FILE_MAINTENANCE_JOBS.ID, 8, self._ConvertJobTypeToListCtrlTuples )
        
        jobs_listctrl_panel.SetListCtrl( self._jobs_listctrl )
        
        jobs_listctrl_panel.AddButton( 'clear', self._DeleteWork, enabled_only_on_selection = True )
        jobs_listctrl_panel.AddButton( 'do work', self._DoWork, enabled_check_func = self._WorkToDoOnSelection )
        jobs_listctrl_panel.AddButton( 'do all work', self._DoAllWork, enabled_check_func = self._WorkToDo )
        jobs_listctrl_panel.AddButton( 'refresh', self._RefreshWorkDue )
        
        vbox = QP.VBoxLayout()
        
        text = 'Here is the outstanding file maintenance work. This will be slowly completed in the background, usually a file every few seconds (you can edit this under _options->maintenance and processing_). Although you can rush work if you want to, it is best to generally leave it alone.'
        
        st = ClientGUICommon.BetterStaticText( self._current_work_panel, text )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, jobs_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._current_work_panel.setLayout( vbox )
        
        #
        
        self._new_work_panel = QW.QWidget( self._notebook )
        
        #
        
        self._search_panel = ClientGUICommon.StaticBox( self._new_work_panel, 'select files by search' )
        
        page_key = HydrusData.GenerateKey()
        
        default_location_context = CG.client_controller.new_options.GetDefaultLocalLocationContext()
        
        file_search_context = ClientSearch.FileSearchContext( location_context = default_location_context )
        
        self._tag_autocomplete = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._search_panel, page_key, file_search_context, allow_all_known_files = False, force_system_everything = True )
        
        self._run_search_st = ClientGUICommon.BetterStaticText( self._search_panel, label = 'no results yet' )
        
        self._run_search = ClientGUICommon.BetterButton( self._search_panel, 'run this search', self._RunSearch )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._run_search_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._run_search, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._search_panel.Add( self._tag_autocomplete, CC.FLAGS_EXPAND_BOTH_WAYS )
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
        
        for job_type in ClientFiles.ALL_REGEN_JOBS_IN_HUMAN_ORDER:
            
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
        
        label = 'Here you can queue up new file maintenance work. You determine the files to run a job on by loading a normal file search.'
        label += '\n' * 2
        label += 'Once your search is set, you need to hit \'run this search\' to actually load up the files. Then select the job type to apply and click \'add job\'. Click \'see description\' for more information on the job.'
        label += '\n' * 2
        label += 'Be cautious--do not queue up an integrity scan for all your files on a whim! If you don\'t know what a job does, do not add it!'
        
        st = ClientGUICommon.BetterStaticText( self._new_work_panel, label )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._search_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
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
        
        CG.client_controller.sub( self, '_RefreshWorkDue', 'notify_files_maintenance_done' )
        
    
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
            
            CG.client_controller.files_maintenance_manager.ScheduleJobHashIds( hash_ids, job_type )
            
            return True
            
        
        def publish_callable( result ):
            
            ClientGUIDialogsMessage.ShowInformation( self, 'Jobs added!' )
            
            self._add_new_job.setEnabled( True )
            
            self._RefreshWorkDue()
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _ConvertJobTypeToListCtrlTuples( self, job_type ):
        
        pretty_job_type = ClientFiles.regen_file_enum_to_str_lookup[ job_type ]
        sort_job_type = pretty_job_type
        
        if job_type in self._job_types_to_due_counts:
            
            num_to_do = self._job_types_to_due_counts[ job_type ]
            
        else:
            
            num_to_do = 0
            
        
        pretty_num_to_do = HydrusData.ToHumanInt( num_to_do )
        
        not_due_num_to_do = self._job_types_to_not_due_counts[ job_type ]
        
        if not_due_num_to_do > 0:
            
            pretty_num_to_do = '{} ({} is not yet due)'.format( pretty_num_to_do, HydrusData.ToHumanInt( not_due_num_to_do ) )
            
        
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
                
                CG.client_controller.files_maintenance_manager.CancelJobs( job_type )
                
            
            return True
            
        
        def publish_callable( result ):
            
            self._RefreshWorkDue()
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _DoAllWork( self ):
        
        CG.client_controller.CallToThread( CG.client_controller.files_maintenance_manager.ForceMaintenance )
        
    
    def _DoWork( self ):
        
        job_types = self._jobs_listctrl.GetData( only_selected = True )
        
        if len( job_types ) == 0:
            
            return
            
        
        CG.client_controller.CallToThread( CG.client_controller.files_maintenance_manager.ForceMaintenance, mandated_job_types = job_types )
        
    
    def _RefreshWorkDue( self ):
        
        def work_callable():
            
            job_types_to_counts = CG.client_controller.Read( 'file_maintenance_get_job_counts' )
            
            return job_types_to_counts
            
        
        def publish_callable( job_types_to_counts ):
            
            job_types = set()
            self._job_types_to_due_counts = collections.Counter()
            self._job_types_to_not_due_counts = collections.Counter()
            
            for ( job_type, ( due_count, not_due_count ) ) in job_types_to_counts.items():
                
                job_types.add( job_type )
                self._job_types_to_due_counts[ job_type ] = due_count
                self._job_types_to_not_due_counts[ job_type ] = not_due_count
                
            
            self._jobs_listctrl.SetData( job_types )
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _RunSearch( self ):
        
        self._run_search_st.setText( 'loading' + HC.UNICODE_ELLIPSIS )
        
        self._run_search.setEnabled( False )
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        
        def work_callable():
            
            query_hash_ids = CG.client_controller.Read( 'file_query_ids', file_search_context, apply_implicit_limit = False )
            
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
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def _SelectAllMediaFiles( self ):
        
        self._select_all_media_files.setEnabled( False )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
        
        file_search_context = ClientSearch.FileSearchContext( location_context = location_context )
        
        def work_callable():
            
            query_hash_ids = CG.client_controller.Read( 'file_query_ids', file_search_context, apply_implicit_limit = False )
            
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
            
            query_hash_ids = CG.client_controller.Read( 'file_query_ids', file_search_context, apply_implicit_limit = False )
            
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
        
        return sum( self._job_types_to_due_counts.values() ) > 0
        
    
    def _WorkToDoOnSelection( self ):
        
        job_types = self._jobs_listctrl.GetData( only_selected = True )
        
        for job_type in job_types:
            
            if self._job_types_to_due_counts[ job_type ] > 0:
                
                return True
                
            
        
        return False
        
    

class ReviewHowBonedAmI( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._update_job = None
        self._job_status = ClientThreading.JobStatus()
        
        vbox = QP.VBoxLayout()
        
        self._mr_bones_text = ClientGUICommon.BetterStaticText( self )
        
        boned_path = os.path.join( HC.STATIC_DIR, 'boned.jpg' )
        
        boned_qt_pixmap = ClientRendering.GenerateHydrusBitmap( boned_path, HC.IMAGE_JPEG ).GetQtPixmap()
        
        self._mr_bones_image = ClientGUICommon.BufferedWindowIcon( self, boned_qt_pixmap )
        
        QP.AddToLayout( vbox, self._mr_bones_image, CC.FLAGS_CENTER )
        QP.AddToLayout( vbox, self._mr_bones_text, CC.FLAGS_CENTER )
        
        self._notebook = ClientGUICommon.BetterNotebook( self )
        
        #
        
        self._search_panel = QW.QWidget( self )
        
        self._files_panel = QW.QWidget( self._notebook )
        self._views_panel = QW.QWidget( self._notebook )
        self._duplicates_panel = QW.QWidget( self._notebook )
        
        self._notebook.addTab( self._files_panel, 'files' )
        self._notebook.addTab( self._views_panel, 'views' )
        self._notebook.addTab( self._duplicates_panel, 'duplicates' )
        
        #
        
        self._files_content_panel = QW.QWidget( self._files_panel )
        
        self._files_content_vbox = QP.VBoxLayout( margin = 0, spacing = 0 )
        
        QP.AddToLayout( self._files_content_vbox, self._files_content_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._files_panel.setLayout( self._files_content_vbox )
        
        #
        
        panel_vbox = QP.VBoxLayout()
        
        self._media_views_st = ClientGUICommon.BetterStaticText( self._views_panel )
        
        self._preview_views_st = ClientGUICommon.BetterStaticText( self._views_panel )
        
        QP.AddToLayout( panel_vbox, self._media_views_st, CC.FLAGS_CENTER )
        QP.AddToLayout( panel_vbox, self._preview_views_st, CC.FLAGS_CENTER )
        
        panel_vbox.addStretch( 1 )
        
        self._views_panel.setLayout( panel_vbox )
        
        #
        
        panel_vbox = QP.VBoxLayout()
        
        self._potentials_st = ClientGUICommon.BetterStaticText( self._duplicates_panel )
        self._duplicates_st = ClientGUICommon.BetterStaticText( self._duplicates_panel )
        self._alternates_st = ClientGUICommon.BetterStaticText( self._duplicates_panel )
        
        QP.AddToLayout( panel_vbox, self._potentials_st, CC.FLAGS_CENTER )
        QP.AddToLayout( panel_vbox, self._duplicates_st, CC.FLAGS_CENTER )
        QP.AddToLayout( panel_vbox, self._alternates_st, CC.FLAGS_CENTER )
        
        panel_vbox.addStretch( 1 )
        
        self._duplicates_panel.setLayout( panel_vbox )
        
        #
        
        panel_vbox = QP.VBoxLayout()
        
        file_search_context = ClientSearch.FileSearchContext(
            location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
        )
        
        page_key = b'mr bones placeholder'
        
        self._tag_autocomplete = ClientGUIACDropdown.AutoCompleteDropdownTagsRead(
            self._search_panel,
            page_key,
            file_search_context,
            allow_all_known_files = False,
            force_system_everything = True,
            fixed_results_list_height = 8
        )
        
        self._loading_text = ClientGUICommon.BetterStaticText( self._search_panel )
        self._loading_text.setAlignment( QC.Qt.AlignVCenter | QC.Qt.AlignRight )
        
        self._cancel_button = ClientGUICommon.BetterBitmapButton( self._search_panel, CC.global_pixmaps().stop, self._CancelCurrentSearch )
        self._refresh_button = ClientGUICommon.BetterBitmapButton( self._search_panel, CC.global_pixmaps().refresh, self._RefreshSearch )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._loading_text, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._cancel_button, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._refresh_button, CC.FLAGS_CENTER )
        
        QP.AddToLayout( panel_vbox, self._tag_autocomplete, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( panel_vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        panel_vbox.addStretch( 1 )
        
        self._search_panel.setLayout( panel_vbox )
        
        #
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        big_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( big_hbox, self._search_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( big_hbox, vbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( big_hbox )
        
        self._tag_autocomplete.searchChanged.connect( self._RefreshSearch )
        
        self._RefreshSearch()
        
    
    def _CancelCurrentSearch( self ):
        
        self._job_status.Cancel()
        
        self._cancel_button.setEnabled( False )
        
    
    def _RefreshSearch( self ):
        
        def work_callable():
            
            boned_stats = CG.client_controller.Read( 'boned_stats', file_search_context = file_search_context, job_status = job_status )
            
            return boned_stats
            
        
        def publish_callable( boned_stats ):
            
            if job_status.IsCancelled():
                
                self._SetCancelled()
                
            else:
                
                self._SetBones( boned_stats )
                
                self._loading_text.setText( '' )
                
            
            self._cancel_button.setEnabled( False )
            self._refresh_button.setEnabled( True )
            
        
        if not self._tag_autocomplete.IsSynchronised():
            
            self._refresh_button.setEnabled( False )
            
            return
            
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        
        self._SetToLoading()
        
        self._job_status.Cancel()
        
        job_status = ClientThreading.JobStatus()
        
        self._job_status = job_status
        
        self._update_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        self._update_job.start()
        
    
    def _SetBones( self, boned_stats: dict ):
        
        self._SetTheMasterOfCeremonies( boned_stats )
        self._SetFilesPanel( boned_stats )
        self._SetViewsPanel( boned_stats )
        self._SetDuplicatesPanel( boned_stats )
        
    
    def _SetCancelled( self ):
        
        self._loading_text.setText( 'cancelled!' )
        
    
    def _SetDuplicatesPanel( self, boned_stats: dict ):
        
        total_alternate_files = boned_stats[ 'total_alternate_files' ]
        total_duplicate_files = boned_stats[ 'total_duplicate_files' ]
        #total_potential_pairs = boned_stats[ 'total_potential_pairs' ]
        
        #potentials_label = f'Total duplicate potential pairs: {HydrusData.ToHumanInt( total_potential_pairs )}'
        potentials_label = f'Total duplicate potential pairs: disabled for now'
        duplicates_label = f'Total files set duplicate: {HydrusData.ToHumanInt( total_duplicate_files )}'
        alternates_label = f'Total duplicate file groups set alternate: {HydrusData.ToHumanInt( total_alternate_files )}'
        
        self._potentials_st.setText( potentials_label )
        self._duplicates_st.setText( duplicates_label )
        self._alternates_st.setText( alternates_label )
        
    
    def _SetFilesPanel( self, boned_stats: dict ):
        
        self._files_content_vbox.removeWidget( self._files_content_panel )
        
        self._files_content_panel.deleteLater()
        
        self._files_content_panel = QW.QWidget( self._files_panel )
        
        num_inbox = boned_stats[ 'num_inbox' ]
        num_archive = boned_stats[ 'num_archive' ]
        size_inbox = boned_stats[ 'size_inbox' ]
        size_archive = boned_stats[ 'size_archive' ]
        
        num_total = num_archive + num_inbox
        size_total = size_archive + size_inbox
        
        panel_vbox = QP.VBoxLayout()
        
        if num_total == 0 or size_total == 0:
            
            divide_by_zero_m8 = ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'No files!' )
            
            QP.AddToLayout( panel_vbox, divide_by_zero_m8, CC.FLAGS_CENTER )
            
        else:
            
            current_average_filesize = size_total // num_total
            
            inbox_num_percent = num_inbox / num_total
            inbox_size_percent = size_inbox / size_total
            
            if num_inbox > 0:
                
                inbox_average_filesize = size_inbox // num_inbox
                
            else:
                
                inbox_average_filesize = 0
                
            
            archive_num_percent = num_archive / num_total
            archive_size_percent = size_archive / size_total
            
            if num_archive > 0:
                
                archive_average_filesize = size_archive // num_archive
                
            else:
                
                archive_average_filesize = 0
                
            
            if 'num_deleted' in boned_stats:
                
                num_deleted = boned_stats[ 'num_deleted' ]
                size_deleted = boned_stats[ 'size_deleted' ]
                
                num_supertotal = num_total + num_deleted
                size_supertotal = size_total + size_deleted
                
                supertotal_average_filesize = size_supertotal // num_supertotal
                
                current_num_percent = num_total / num_supertotal
                current_size_percent = size_total / size_supertotal
                
                deleted_num_percent = num_deleted / num_supertotal
                deleted_size_percent = size_deleted / size_supertotal
                
                if num_deleted > 0:
                    
                    deleted_average_filesize = size_deleted // num_deleted
                    
                else:
                    
                    deleted_average_filesize = 0
                    
                
                # spacing=0 to make the weird unicode characters join up neater
                text_table_layout = QP.GridLayout( cols = 6, spacing = 0 )
                
                text_table_layout.setHorizontalSpacing( ClientGUIFunctions.ConvertTextToPixelWidth( self, 2 ) )
                
                text_table_layout.setColumnStretch( 0, 1 )
                
                #
                
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Files' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = '%' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Size' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = '%' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Average' ), CC.FLAGS_CENTER )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Total Ever Imported:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanInt( num_supertotal ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_supertotal ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( supertotal_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = '' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Current:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanInt( num_total ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( current_num_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_total ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( current_size_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( current_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Deleted:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanInt( num_deleted ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( deleted_num_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_deleted ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( deleted_size_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( deleted_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = '' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Inbox:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanInt( num_inbox ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( inbox_num_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_inbox ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( inbox_size_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( inbox_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Archive:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanInt( num_archive ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( archive_num_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_archive ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( archive_size_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( archive_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
            else:
                
                panel_vbox = QP.VBoxLayout()
                
                # spacing=0 to make the weird unicode characters join up neater
                text_table_layout = QP.GridLayout( cols = 6, spacing = 0 )
                
                text_table_layout.setHorizontalSpacing( ClientGUIFunctions.ConvertTextToPixelWidth( self, 2 ) )
                
                text_table_layout.setColumnStretch( 0, 1 )
                
                #
                
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Files' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = '%' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Size' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = '%' ), CC.FLAGS_CENTER )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Average' ), CC.FLAGS_CENTER )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Current:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanInt( num_total ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_total ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( current_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = '' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, QW.QWidget( self._files_content_panel ), CC.FLAGS_ON_LEFT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Inbox:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanInt( num_inbox ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( inbox_num_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_inbox ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( inbox_size_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( inbox_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
                #
                
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = 'Archive:' ), CC.FLAGS_ON_LEFT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanInt( num_archive ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( archive_num_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( size_archive ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = ClientData.ConvertZoomToPercentage( archive_size_percent ) ), CC.FLAGS_ON_RIGHT )
                QP.AddToLayout( text_table_layout, ClientGUICommon.BetterStaticText( self._files_content_panel, label = HydrusData.ToHumanBytes( archive_average_filesize ) ), CC.FLAGS_ON_RIGHT )
                
            
            #
            
            QP.AddToLayout( panel_vbox, text_table_layout, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            if 'earliest_import_time' in boned_stats:
                
                panel_vbox.addSpacing( ClientGUIFunctions.ConvertTextToPixelWidth( self, 2 ) )
                
                eit_timestamp = boned_stats[ 'earliest_import_time' ]
                
                eit_label = 'Earliest file import: {} ({})'.format( HydrusTime.TimestampToPrettyTime( eit_timestamp ), HydrusTime.TimestampToPrettyTimeDelta( eit_timestamp ) )
                
                eit_st = ClientGUICommon.BetterStaticText( self._files_content_panel, label = eit_label )
                
                QP.AddToLayout( panel_vbox, eit_st, CC.FLAGS_CENTER )
                
            
        
        panel_vbox.addStretch( 1 )
        
        self._files_content_panel.setLayout( panel_vbox )
        
        QP.AddToLayout( self._files_content_vbox, self._files_content_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
    
    def _SetTheMasterOfCeremonies( self, boned_stats: dict ):
        
        num_inbox = boned_stats[ 'num_inbox' ]
        num_archive = boned_stats[ 'num_archive' ]
        
        num_total = num_archive + num_inbox
        
        special_message = None
        
        num_deleted = boned_stats.get( 'num_deleted', 0 )
        
        current_fsc = self._tag_autocomplete.GetFileSearchContext()
        
        special_message_is_appropriate = len( current_fsc.GetPredicates() ) == 0 and current_fsc.GetLocationContext() == ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
        
        if special_message_is_appropriate:
            
            if num_total == 0 and num_deleted == 0:
                
                special_message = 'You have yet to board the ride.'
                
            elif num_total + num_deleted < 1000:
                
                special_message = 'I hope you enjoy my software. You might like to check out the downloaders! :^)'
                
            elif num_inbox <= num_archive / 99:
                
                special_message = 'CONGRATULATIONS. YOU APPEAR TO BE UNBONED--BUT REMAIN EVER VIGILANT'
                
            
        
        if special_message is None:
            
            self._mr_bones_text.setVisible( False )
            
            self._mr_bones_image.setVisible( True )
            
        else:
            
            self._mr_bones_image.setVisible( False )
            
            self._mr_bones_text.setVisible( True )
            self._mr_bones_text.setText( special_message )
            
        
    
    def _SetToLoading( self ):
        
        self._loading_text.setText( 'loading' + HC.UNICODE_ELLIPSIS )
        
        self._files_content_vbox.removeWidget( self._files_content_panel )
        
        self._files_content_panel.deleteLater()
        
        self._files_content_panel = QW.QWidget( self._files_panel )
        
        QP.AddToLayout( self._files_content_vbox, self._files_content_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._potentials_st.setText( '' )
        self._duplicates_st.setText( '' )
        self._alternates_st.setText( '' )
        
        self._media_views_st.setText( '' )
        self._preview_views_st.setText( '' )
        
        self._refresh_button.setEnabled( False )
        self._cancel_button.setEnabled( True )
        
    
    def _SetViewsPanel( self, boned_stats: dict ):
        
        total_viewtime = boned_stats[ 'total_viewtime' ]
        
        ( media_views, media_viewtime, preview_views, preview_viewtime ) = total_viewtime
        
        media_label = 'Total media views: ' + HydrusData.ToHumanInt( media_views ) + ', totalling ' + HydrusTime.TimeDeltaToPrettyTimeDelta( media_viewtime )
        
        preview_label = 'Total preview views: ' + HydrusData.ToHumanInt( preview_views ) + ', totalling ' + HydrusTime.TimeDeltaToPrettyTimeDelta( preview_viewtime )
        
        self._media_views_st.setText( media_label )
        self._preview_views_st.setText( preview_label )
        
    

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
        
        file_import_options = FileImportOptions.FileImportOptions()
        file_import_options.SetIsDefault( True )
        
        show_downloader_options = False
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        
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
        
        self._tag_button = ClientGUICommon.BetterButton( self, 'add tags/urls with the import >>', self._AddTags )
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
        
        QP.AddToLayout( import_options_buttons, self._import_options_button, CC.FLAGS_CENTER )
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
        
        self._job_status = ClientThreading.JobStatus()
        
        self._unparsed_paths_queue = queue.Queue()
        self._currently_parsing = threading.Event()
        self._work_to_do = threading.Event()
        self._parsed_path_queue = queue.Queue()
        self._pause_event = threading.Event()
        self._cancel_event = threading.Event()
        
        self._progress_updater = ClientGUIAsync.FastThreadToGUIUpdater( self._progress, self._progress.SetValue )
        
        if len( paths ) > 0:
            
            self._AddPathsToList( paths )
            
        
        CG.client_controller.gui.RegisterUIUpdateWindow( self )
        
        CG.client_controller.CallToThreadLongRunning( self.THREADParseImportablePaths, self._unparsed_paths_queue, self._currently_parsing, self._work_to_do, self._parsed_path_queue, self._progress_updater, self._pause_event, self._cancel_event )
        
    
    def _AddPathsToList( self, paths ):
        
        if self._cancel_event.is_set():
            
            message = 'Please wait for the cancel to clear.'
            
            ClientGUIDialogsMessage.ShowWarning( self, message )
            
            return
            
        
        self._unparsed_paths_queue.put( paths )
        
    
    def _AddTags( self ):
        
        # TODO: convert this class to have a filenametaggingoptions and the structure for 'tags for these files', which is separate
        # then make this button not start the import. just edit the options and routers and return
        # if needed, we convert to paths_to_additional_tags on ultimate ok, or we convert the hdd import to just hold service_keys_to_filenametaggingoptions, like an import folder does
        
        paths = self._paths_list.GetData()
        
        if len( paths ) > 0:
            
            file_import_options = self._import_options_button.GetFileImportOptions()
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'filename tagging', frame_key = 'local_import_filename_tagging' ) as dlg:
                
                panel = ClientGUIImport.EditLocalImportFilenameTaggingPanel( dlg, paths )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    ( metadata_routers, paths_to_additional_service_keys_to_tags ) = panel.GetValue()
                    
                    delete_after_success = self._delete_after_success.isChecked()
                    
                    CG.client_controller.pub( 'new_hdd_import', paths, file_import_options, metadata_routers, paths_to_additional_service_keys_to_tags, delete_after_success )
                    
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
            
            file_import_options = self._import_options_button.GetFileImportOptions()
            
            metadata_routers = []
            paths_to_additional_service_keys_to_tags = collections.defaultdict( ClientTags.ServiceKeysToTags )
            
            delete_after_success = self._delete_after_success.isChecked()
            
            CG.client_controller.pub( 'new_hdd_import', paths, file_import_options, metadata_routers, paths_to_additional_service_keys_to_tags, delete_after_success )
            
        
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
        
        num_sidecars = 0
        
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
                
            
            if num_empty_files + num_missing_files + num_unimportable_mime_files + num_occupied_files + num_sidecars > 0:
                
                if num_good_files == 0:
                    
                    message += ': '
                    
                else:
                    
                    message += ', but '
                    
                
                bad_comments = []
                
                if num_sidecars > 0:
                    
                    bad_comments.append( '{} looked like txt/json/xml sidecars'.format( HydrusData.ToHumanInt( num_sidecars ) ) )
                    
                
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
            
            do_human_sort = CG.client_controller.new_options.GetBoolean( 'do_human_sort_on_hdd_file_import_paths' )
            
            while not unparsed_paths_queue.empty():
                
                try:
                    
                    raw_paths = unparsed_paths_queue.get( block = False )

                    ( paths, num_sidecars_this_loop ) = ClientFiles.GetAllFilePaths( raw_paths, do_human_sort = do_human_sort ) # convert any dirs to subpaths
                    
                    num_sidecars += num_sidecars_this_loop
                    unparsed_paths.extend( paths )
                    
                except queue.Empty:
                    
                    pass
                    
                
            
            # if unparsed_paths still has nothing, we'll nonetheless sleep on new paths
            
            if len( unparsed_paths ) == 0:
                
                try:
                    
                    raw_paths = unparsed_paths_queue.get( timeout = 5 )

                    ( paths, num_sidecars_this_loop ) = ClientFiles.GetAllFilePaths( raw_paths, do_human_sort = do_human_sort ) # convert any dirs to subpaths
                    
                    num_sidecars += num_sidecars_this_loop
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
        
    

class ReviewDeferredDeleteTableData( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._controller = controller
        
        #
        
        info_message = '''When large database objects are no longer needed, they are not deleted immediately, but incrementally shrunk in the background over time. This is the queue of pending deferred delete database tables and approximate sizes.'''
        
        st = ClientGUICommon.BetterStaticText( self, label = info_message )
        
        st.setWordWrap( True )
        
        deferred_delete_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._names_to_num_rows = {}
        
        self._deferred_delete_listctrl = ClientGUIListCtrl.BetterListCtrl( deferred_delete_listctrl_panel, CGLC.COLUMN_LIST_DEFERRED_DELETE_TABLE_DATA.ID, 24, self._ConvertRowToListCtrlTuples )
        
        deferred_delete_listctrl_panel.SetListCtrl( self._deferred_delete_listctrl )
        
        self._refresh_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().refresh, self._RefreshData )
        self._work_hard_button = ClientGUICommon.BetterButton( self,'work hard now', self._FlipWorkingHard )
        
        #
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, deferred_delete_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._refresh_button, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._work_hard_button, CC.FLAGS_CENTER )
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        self._updater = self._InitialiseUpdater()
        
        self._RefreshData()
        self._UpdateButtonLabel()
        
        self._controller.sub( self, 'NotifyRefresh', 'notify_deferred_delete_database_maintenance_work_complete' )
        self._controller.sub( self, 'NotifyStateChange', 'notify_deferred_delete_database_maintenance_state_change' )
        self._controller.sub( self, 'NotifyRefresh', 'notify_deferred_delete_database_maintenance_new_work' )
        
    
    def _ConvertRowToListCtrlTuples( self, name ):
        
        num_rows = self._names_to_num_rows.get( name, None )
        
        sort_name = name
        pretty_name = name
        
        if num_rows is None:
            
            sort_num_rows = -1
            pretty_num_rows = 'unknown'
            
        else:
            
            sort_num_rows = num_rows
            pretty_num_rows = HydrusData.ToHumanInt( sort_num_rows )
            
        
        display_tuple = ( pretty_name, pretty_num_rows )
        sort_tuple = ( sort_name, sort_num_rows )
        
        return ( display_tuple, sort_tuple )
        
    
    def _FlipWorkingHard( self ):
        
        self._controller.database_maintenance_manager.FlipWorkingHard()
        
        self._UpdateButtonLabel()
        
    
    def _InitialiseUpdater( self ) -> ClientGUIAsync.AsyncQtUpdater:
        
        def loading_callable():
            
            self._refresh_button.setEnabled( False )
            
        
        def work_callable( args ):
            
            deferred_delete_data = self._controller.Read( 'deferred_delete_data' )
            
            return deferred_delete_data
            
        
        def publish_callable( deferred_delete_data ):
            
            self._names_to_num_rows = dict( deferred_delete_data )
            
            self._deferred_delete_listctrl.SetData( list( self._names_to_num_rows.keys() ) )
            
            self._deferred_delete_listctrl.Sort()
            
            self._refresh_button.setEnabled( True )
            
            self._UpdateButtonLabel()
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable )
        
    
    def _RefreshData( self ):
        
        self._updater.update()
        
    
    def _UpdateButtonLabel( self ):
        
        if self._controller.database_maintenance_manager.IsWorkingHard():
            
            label = 'slow down'
            enabled = True
            
        else:
            
            work_to_do = len( self._deferred_delete_listctrl.GetData() ) > 0
            
            if work_to_do:
                
                label = 'work hard'
                
            else:
                
                label = 'all work done!'
                
            
            enabled = work_to_do
            
        
        self._work_hard_button.setText( label )
        
        self._work_hard_button.setEnabled( enabled )
        
    
    def NotifyRefresh( self ):
        
        self._RefreshData()
        
    
    def NotifyStateChange( self ):
        
        self._UpdateButtonLabel()
        
    

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
        
        info_message = '''Vacuuming is essentially an aggressive defrag of a database file. The entire database is copied contiguously to a new file, which then has tightly packed pages and no empty 'free' pages.

Because the new database is tightly packed, it will generally be smaller than the original file. This is currently the only way to truncate a hydrus database file.

Vacuuming is an expensive operation. It requires lots of free space on your drive(s) (including a full copy in your temp directory!), hydrus cannot operate while it is going on, and it tends to run quite slow, about 1-40MB/s. The main benefit is in truncating the database files after you delete a lot of data, so I recommend you only do it on files with a lot of free space.'''
        
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
            
        
        sort_last_vacuumed_ms = vacuum_dict[ 'last_vacuumed_ms' ]
        
        if sort_last_vacuumed_ms == 0 or sort_last_vacuumed_ms is None:
            
            sort_last_vacuumed_ms = 0
            pretty_last_vacuumed_ms = 'never done'
            
        else:
            
            pretty_last_vacuumed_ms = HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( sort_last_vacuumed_ms ) )
            
        
        ( result, info ) = self._CanVacuumName( name )
        
        sort_can_vacuum = result
        pretty_can_vacuum = info
        
        ( sort_vacuum_time_estimate, pretty_vacuum_time_estimate ) = self._GetVacuumTimeEstimate( sort_total_size )
        
        display_tuple = ( pretty_name, pretty_total_size, pretty_free_size, pretty_last_vacuumed_ms, pretty_can_vacuum, pretty_vacuum_time_estimate )
        sort_tuple = ( sort_name, sort_total_size, sort_free_size, sort_last_vacuumed_ms, sort_can_vacuum, sort_vacuum_time_estimate )
        
        return ( display_tuple, sort_tuple )
        
    
    def _GetVacuumTimeEstimate( self, db_size ):
        
        from hydrus.core import HydrusDB
        
        vacuum_time_estimate = HydrusDB.GetApproxVacuumDuration( db_size )
        
        pretty_vacuum_time_estimate = '{} to {}'.format( HydrusTime.TimeDeltaToPrettyTimeDelta( vacuum_time_estimate / 40 ), HydrusTime.TimeDeltaToPrettyTimeDelta( vacuum_time_estimate ) )
        
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
                
            
        
    
