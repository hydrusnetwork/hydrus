from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusPaths

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIPathWidgets

class ExportingPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._exports_panel = ClientGUICommon.StaticBox( self, 'all exports' )
        
        self._always_apply_ntfs_export_filename_rules = QW.QCheckBox( self._exports_panel )
        tt = 'IF YOU ARE DRAG AND DROPPING CLEVER FILENAMES TO NTFS, TURN THIS ON.\n\nWhen generating an export filename, hydrus will try to determine the filesystem of the destination, and if it is Windows-like (NTFS, exFAT, CIFS, etc..), it will remove colons and such from the filename. If you have a complicated mount setup where hydrus might not recognise this is true (e.g. NTFS behind NFS, or a mountpoint deeper than the base export folder that translates to NTFS), or if you are doing any drag and drops to an NTFS drive (in this case, hydrus first exports to your tempdir before the drag and drop even starts, and Qt & your OS handle the rest), turn this on and it will always make safer filenames.'
        self._always_apply_ntfs_export_filename_rules.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._export_dirname_character_limit = ClientGUICommon.NoneableSpinCtrl( self, 64, none_phrase = 'let hydrus decide', min = 16, max = 8192 )
        tt = 'BEST USED IN CONJUNCTION WITH THE PATH LIMIT FOR WHEN YOU ARE TESTING OUT VERY LONG PATH NAMES. When generating an export filename that includes subdirectory generation, hydrus will clip those subdirs so everything fits reasonable below the system path limit. This value forces the per-dirname to never be longer than this. On Windows, this means characters, on Linux/macOS, it means bytes (when encoding unicode characters). This stuff can get complicated, so be careful changing it too much! Most OS filesystems do not accept a directory name longer than 256 chars/bytes, but you should leave a little padding for surprises, and of course you will want some space for a filename too.'
        self._export_dirname_character_limit.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._export_path_character_limit = ClientGUICommon.NoneableSpinCtrl( self, 250, none_phrase = 'let hydrus decide', min = 96, max = 8192 )
        tt = 'When generating an export filename, hydrus will clip the generated subdirectories and filename so they fit into the system path limit. This value overrides that limit. On Windows, this means characters, on Linux/macOS, it means bytes (when encoding unicode characters). This stuff can get complicated, so be careful changing it too much! Most OS filesystems do not accept a directory name longer than 256 chars/bytes, but you should leave a little padding for surprises. Also, on Windows, the entire path typically also has to be shorter than 256 characters total, so do not go crazy here unless you know what you are doing! (Linux is usually 4096; macOS 1024.)'
        self._export_path_character_limit.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._export_filename_character_limit = ClientGUICommon.BetterSpinBox( self._exports_panel, min = 16, max = 8192 )
        tt = 'When generating an export filename, hydrus will clip the output so it is not longer than this. On Windows, this means characters, on Linux/macOS, it means bytes (when encoding unicode characters). This stuff can get complicated, so be careful changing it too much! Most OS filesystems do not accept a filename longer than 256 chars/bytes, but you should leave a little padding for stuff like sidecar suffixes and other surprises. If you have a Linux folder using eCryptFS, the filename limit is around 140 bytes, which with sophisticated unicode output can be really short. On Windows, the entire path typically also has to be shorter than 256 characters total! (Linux is usually 4096; macOS 1024.)'
        self._export_filename_character_limit.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._dnd_panel = ClientGUICommon.StaticBox( self, 'drag and drop' )
        
        # TODO: Yo, make the 50 files/200MB thresholds options of their own with warnings about lag!
        # ALSO do gubbins where the temp folder stuff is fired if ctrl is held down or something, otherwise no export and hash filenames
        
        self._discord_dnd_fix = QW.QCheckBox( self._dnd_panel )
        self._discord_dnd_fix.setToolTip( ClientGUIFunctions.WrapToolTip( 'This makes small file drag-and-drops a little laggier in exchange for Discord support. It also lets you set custom filenames for drag and drop exports.' ) )
        
        self._discord_dnd_filename_pattern = QW.QLineEdit( self._dnd_panel )
        self._discord_dnd_filename_pattern.setToolTip( ClientGUIFunctions.WrapToolTip( 'When you put your DnD files in your temp folder, we have a chance to rename them. This export phrase will do that. If no filename can be generated, hash will be used instead.' ) )
        
        self._export_pattern_button = ClientGUICommon.ExportPatternButton( self._dnd_panel )
        
        self._secret_discord_dnd_fix = QW.QCheckBox( self._dnd_panel )
        self._secret_discord_dnd_fix.setToolTip( ClientGUIFunctions.WrapToolTip( 'THIS SOMETIMES FIXES DnD FOR WEIRD PROGRAMS, BUT IT ALSO OFTEN BREAKS IT FOR OTHERS.\n\nBecause of weird security/permission issues, a program will sometimes not accept a drag and drop file export from hydrus unless the DnD is set to "move" rather than "copy" (discord has done this for some people). Since we do not want to let you accidentally move your files out of your primary file store, this is only enabled if you are copying the files in question to your temp folder first!' ) )
        
        self._export_folder_panel = ClientGUICommon.StaticBox( self, 'export folder' )
        
        self._export_location = ClientGUIPathWidgets.DirPickerCtrl( self._export_folder_panel )
        
        #
        
        self._new_options = CG.client_controller.new_options
        
        self._discord_dnd_fix.setChecked( self._new_options.GetBoolean( 'discord_dnd_fix' ) )
        
        self._discord_dnd_filename_pattern.setText( self._new_options.GetString( 'discord_dnd_filename_pattern' ) )
        
        self._secret_discord_dnd_fix.setChecked( self._new_options.GetBoolean( 'secret_discord_dnd_fix' ) )
        
        if HC.options[ 'export_path' ] is not None:
            
            abs_path = HydrusPaths.ConvertPortablePathToAbsPath( HC.options[ 'export_path' ] )
            
            if abs_path is not None:
                
                self._export_location.SetPath( abs_path )
                
            
        
        self._always_apply_ntfs_export_filename_rules.setChecked( self._new_options.GetBoolean( 'always_apply_ntfs_export_filename_rules' ) )
        
        self._export_path_character_limit.SetValue( self._new_options.GetNoneableInteger( 'export_path_character_limit' ) )
        self._export_dirname_character_limit.SetValue( self._new_options.GetNoneableInteger( 'export_dirname_character_limit' ) )
        self._export_filename_character_limit.setValue( self._new_options.GetInteger( 'export_filename_character_limit' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'ADVANCED: Always apply NTFS filename rules to export filenames: ', self._always_apply_ntfs_export_filename_rules ) )
        rows.append( ( 'ADVANCED: Export path length limit (characters/bytes): ', self._export_path_character_limit ) )
        rows.append( ( 'ADVANCED: Export dirname length limit (characters/bytes): ', self._export_dirname_character_limit ) )
        rows.append( ( 'ADVANCED: Export filename length limit (characters/bytes): ', self._export_filename_character_limit ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._exports_panel, rows )
        
        self._exports_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Copy files to temp folder for drag-and-drop (works for <=50, <200MB file DnDs--fixes Discord!): ', self._discord_dnd_fix ) )
        rows.append( ( 'BUGFIX: Set drag-and-drops to have a "move" flag: ', self._secret_discord_dnd_fix ) )
        rows.append( ( 'Drag-and-drop export filename pattern: ', self._discord_dnd_filename_pattern ) )
        rows.append( ( '', self._export_pattern_button ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._dnd_panel, rows )
        
        label = 'You can drag-and-drop a selection of files out of the client to quickly copy-export them to a folder or an external program (include web browser upload boxes).'
        
        if HC.PLATFORM_WINDOWS:
            
            label += '\n\nNote, however, that Windows will generally be unhappy about DnDs between two programs where one is in admin mode and the other not. In this case, you will want to export to a neutral folder like your Desktop and then do a second drag from there to your destination program.'
            
        
        st = ClientGUICommon.BetterStaticText( self._dnd_panel, label = label )
        
        st.setWordWrap( True )
        
        self._dnd_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._dnd_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'Default export directory: ', self._export_location ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._export_folder_panel, rows )
        
        self._export_folder_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._exports_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._dnd_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._export_folder_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        self._discord_dnd_fix.clicked.connect( self._UpdateDnDFilenameEnabled )
        
        self._UpdateDnDFilenameEnabled()
        
    
    def _UpdateDnDFilenameEnabled( self ):
        
        enabled = self._discord_dnd_fix.isChecked()
        
        self._discord_dnd_filename_pattern.setEnabled( enabled )
        self._export_pattern_button.setEnabled( enabled )
        self._secret_discord_dnd_fix.setEnabled( enabled )
        
    
    def UpdateOptions( self ):
        
        self._new_options.SetBoolean( 'always_apply_ntfs_export_filename_rules', self._always_apply_ntfs_export_filename_rules.isChecked() )
        self._new_options.SetNoneableInteger( 'export_path_character_limit', self._export_path_character_limit.GetValue() )
        self._new_options.SetNoneableInteger( 'export_dirname_character_limit', self._export_dirname_character_limit.GetValue() )
        self._new_options.SetInteger( 'export_filename_character_limit', self._export_filename_character_limit.value() )
        
        self._new_options.SetBoolean( 'discord_dnd_fix', self._discord_dnd_fix.isChecked() )
        self._new_options.SetString( 'discord_dnd_filename_pattern', self._discord_dnd_filename_pattern.text() )
        self._new_options.SetBoolean( 'secret_discord_dnd_fix', self._secret_discord_dnd_fix.isChecked() )
        
        path = str( self._export_location.GetPath() ).strip()
        
        if path != '':
            
            HC.options[ 'export_path' ] = HydrusPaths.ConvertAbsPathToPortablePath( self._export_location.GetPath() )
            
        else:
            
            HC.options[ 'export_path' ] = None
            
        
    
