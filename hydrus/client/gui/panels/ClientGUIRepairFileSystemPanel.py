import collections.abc
import os

from qtpy import QtWidgets as QW

from hydrus.core import HydrusExceptions

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.files import ClientFilesPhysical
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon

class RepairFileSystemPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, missing_subfolders: collections.abc.Collection[ ClientFilesPhysical.FilesStorageSubfolder ] ):
        
        super().__init__( parent )
        
        # TODO: This needs another pass as we move to multiple locations and other tech
        # if someone has f10 and we are expecting 16 lots of f10x, or vice versa, (e.g. on an out of sync db recovery, not uncommon) we'll need to handle that
        
        self._only_thumbs = True not in ( subfolder.IsForFiles() for subfolder in missing_subfolders )
        
        self._missing_subfolders_to_new_subfolders = {}
        
        text = 'This dialog has launched because some expected file storage directories were not found. This is a serious error. You have two options:'
        text += '\n\n'
        text += '1) If you know what these should be (e.g. you recently remapped their external drive to another location), update the paths here manually. For most users, this will be clicking _add a possibly correct location_ and then select the new folder where the subdirectories all went. You can repeat this if your folders are missing in multiple locations. Check everything reports _ok!_'
        text += '\n\n'
        text += 'Although it is best if you can find everything, you only _have_ to fix the subdirectories starting with \'f\', which store your original files. Those starting \'t\' and \'r\' are for your thumbnails, which can be regenerated with a bit of work.'
        text += '\n\n'
        text += 'Then hit \'apply\', and the client will launch. You should double-check all your locations under \'database->move media files\' immediately.'
        text += '\n\n'
        text += '2) If the locations are not available, or you do not know what they should be, or you wish to fix this outside of the program, hit \'cancel\' to gracefully cancel client boot. Feel free to contact hydrus dev for help. Regardless of the situation, the document at "install_dir/db/help my media files-folders are broke.txt" may be useful background reading.'
        
        if self._only_thumbs:
            
            text += '\n\n'
            text += 'SPECIAL NOTE FOR YOUR SITUATION: The only paths missing are thumbnail paths. If you cannot recover these folders, you can hit apply to create empty paths at the original or corrected locations and then run a maintenance routine to regenerate the thumbnails from their originals.'
            
        
        st = ClientGUICommon.BetterStaticText( self, text )
        st.setWordWrap( True )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_REPAIR_LOCATIONS.ID, self._ConvertPrefixToDisplayTuple, self._ConvertPrefixToSortTuple )
        
        self._locations = ClientGUIListCtrl.BetterListCtrlTreeView( self, 12, model, activation_callback = self._SetLocations )
        
        self._set_button = ClientGUICommon.BetterButton( self, 'set correct location', self._SetLocations )
        self._add_button = ClientGUICommon.BetterButton( self, 'add a possibly correct location (let the client figure out what it contains)', self._AddLocation )
        
        # add a button here for 'try to fill them in for me'. you give it a dir, and it tries to figure out and fill in the prefixes for you
        
        #
        
        self._locations.SetData( missing_subfolders )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._locations, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._set_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._add_button, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
    
    def _AddLocation( self ):
        
        try:
            
            path = ClientGUIDialogsQuick.PickDirectory( self, 'Select the potential correct location.' )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        potential_base_locations = [
            ClientFilesPhysical.FilesStorageBaseLocation( path, 0 ),
            ClientFilesPhysical.FilesStorageBaseLocation( os.path.join( path, 'client_files' ), 0 ),
            ClientFilesPhysical.FilesStorageBaseLocation( os.path.join( path, 'thumbnails' ), 0 )
        ]
        
        for subfolder in self._locations.GetData():
            
            for potential_base_location in potential_base_locations:
                
                new_subfolder = ClientFilesPhysical.FilesStorageSubfolder( subfolder.prefix, potential_base_location )
                
                ok = new_subfolder.PathExists()
                
                if ok:
                    
                    self._missing_subfolders_to_new_subfolders[ subfolder ] = ( new_subfolder, ok )
                    
                    break
                    
                
            
        
        self._locations.UpdateDatas()
        
    
    def _ConvertPrefixToDisplayTuple( self, subfolder ):
        
        prefix = subfolder.prefix
        incorrect_base_location = subfolder.base_location
        
        if subfolder in self._missing_subfolders_to_new_subfolders:
            
            ( new_subfolder, ok ) = self._missing_subfolders_to_new_subfolders[ subfolder ]
            
            correct_base_location = new_subfolder.base_location
            
            if ok:
                
                pretty_ok = 'ok!'
                
            else:
                
                pretty_ok = 'not found'
                
            
            pretty_correct_base_location = correct_base_location.path
            
        else:
            
            pretty_correct_base_location = ''
            pretty_ok = ''
            
        
        pretty_incorrect_base_location = incorrect_base_location.path
        pretty_prefix = prefix
        
        display_tuple = ( pretty_incorrect_base_location, pretty_prefix, pretty_correct_base_location, pretty_ok )
        
        return display_tuple
        
    
    def _ConvertPrefixToSortTuple( self, subfolder ):
        
        prefix = subfolder.prefix
        incorrect_base_location = subfolder.base_location
        
        if subfolder in self._missing_subfolders_to_new_subfolders:
            
            ( new_subfolder, ok ) = self._missing_subfolders_to_new_subfolders[ subfolder ]
            
            correct_base_location = new_subfolder.base_location
            
            pretty_correct_base_location = correct_base_location.path
            
        else:
            
            pretty_correct_base_location = ''
            ok = None
            
        
        pretty_incorrect_base_location = incorrect_base_location.path
        
        sort_tuple = ( pretty_incorrect_base_location, prefix, pretty_correct_base_location, ok )
        
        return sort_tuple
        
    
    def _GetValue( self ):
        
        correct_rows = []
        
        thumb_problems = False
        
        for subfolder in self._locations.GetData():
            
            prefix = subfolder.prefix
            
            if subfolder not in self._missing_subfolders_to_new_subfolders:
                
                if prefix.startswith( 'f' ):
                    
                    raise HydrusExceptions.VetoException( 'You did not correct all the file locations!' )
                    
                else:
                    
                    thumb_problems = True
                    
                    new_subfolder = subfolder
                    
                
            else:
                
                ( new_subfolder, ok ) = self._missing_subfolders_to_new_subfolders[ subfolder ]
                
                if not ok:
                    
                    if prefix.startswith( 'f' ):
                        
                        raise HydrusExceptions.VetoException( 'You did not find all the correct file locations!' )
                        
                    else:
                        
                        thumb_problems = True
                        
                    
                
            
            correct_rows.append( ( subfolder, new_subfolder ) )
            
        
        return ( correct_rows, thumb_problems )
        
    
    def _SetLocations( self ):
        
        subfolders = self._locations.GetData( only_selected = True )
        
        if len( subfolders ) > 0:
            
            try:
                
                path = ClientGUIDialogsQuick.PickDirectory( self, 'Select correct location.' )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            base_location = ClientFilesPhysical.FilesStorageBaseLocation( path, 0 )
            
            for subfolder in subfolders:
                
                new_subfolder = ClientFilesPhysical.FilesStorageSubfolder( subfolder.prefix, base_location )
                
                ok = new_subfolder.PathExists()
                
                self._missing_subfolders_to_new_subfolders[ subfolder ] = ( new_subfolder, ok )
                
            
            self._locations.UpdateDatas()
            
        
    
    def CheckValid( self ):
        
        # raises veto if invalid
        self._GetValue()
        
    
    def CommitChanges( self ):
        
        ( correct_rows, thumb_problems ) = self._GetValue()
        
        try:
            
            CG.client_controller.WriteSynchronous( 'repair_client_files', correct_rows )
            
        except Exception as e:
            
            message = f'Hey, I am sorry, but I could not save your repaired rows. There may be additional problems with your database. Full error:\n\n{e}'
            
            ClientGUIDialogsMessage.ShowCritical( self, 'problem saving good locations back', message )
            
        
    
    def UserIsOKToOK( self ):
        
        ( correct_rows, thumb_problems ) = self._GetValue()
        
        if thumb_problems:
            
            message = 'Some or all of your incorrect paths have not been corrected, but they are all thumbnail paths.'
            message += '\n' * 2
            message += 'Would you like instead to create new empty subdirectories at the previous (or corrected, if you have entered them) locations?'
            message += '\n' * 2
            message += 'You can run database->regenerate->thumbnails to fill them up again.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
