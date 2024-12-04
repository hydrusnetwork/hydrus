#ifndef Version
    #define Version "Null"
#endif

[Icons]
Name: {group}\hydrus client; Filename: {app}\hydrus_client.exe; WorkingDir: {app}; Tasks: programgroupicons
Name: {group}\hydrus server; Filename: {app}\hydrus_server.exe; WorkingDir: {app}; Tasks: programgroupicons
;Taking this out to stop anti-virus testbeds pursuing it and launching Edge and detecting Edge update calls as suspicious DNS lmao
;Name: {group}\help; Filename: {app}\help\index.html; WorkingDir: {app}; Tasks: programgroupicons
Name: {group}\uninstall hydrus network; Filename: {uninstallexe}; WorkingDir: {app}; Tasks: programgroupicons; IconFilename: {app}\static\cross.ico
Name: {userdesktop}\hydrus client; Filename: {app}\hydrus_client.exe; WorkingDir: {app}; Tasks: desktopicons
Name: {userdesktop}\hydrus server; Filename: {app}\hydrus_server.exe; WorkingDir: {app}; Tasks: desktopicons
[Setup]
InternalCompressLevel=ultra64
OutputDir=dist
OutputBaseFilename=HydrusInstaller
Compression=lzma/ultra64
AppName=Hydrus Network
AppVerName=Hydrus Network
AppPublisher=Hydrus Network
AppVersion={#Version}
DefaultDirName={sd}\Hydrus Network
DefaultGroupName=Hydrus Network
DisableProgramGroupPage=yes
DisableReadyPage=yes
DisableDirPage=no
ShowLanguageDialog=no
SetupIconFile=hydrus\static\hydrus.ico
Uninstallable=WizardIsComponentSelected('install')
UninstallDisplayIcon={app}\static\hydrus.ico
UsedUserAreasWarning=no
[Tasks]
Name: desktopicons; Description: Create desktop icons; Flags: unchecked; Components: install
Name: programgroupicons; Description: Create program group icons; Components: install
[Messages]
SelectDirBrowseLabel=To continue, click Next. If you would like to select a different folder, click Browse. By default, databases will be created beneath the install dir, so make sure the hard drive has enough spare space for your purposes and your user has permission to write there! If you install to a protected location like 'Program Files', the database will be created in your User Directory.
[Components]
Name: install; Description: Install; Types: install; Flags: fixed
[Types]
Name: install; Description: Install
Name: extract; Description: Extract only
[Run]
;Taking this out to stop anti-virus testbeds pursuing it and launching Edge and detecting Edge update calls as suspicious DNS lmao
;Filename: {app}\help\index.html; Description: Open help/getting started guide (highly recommended for new users); Flags: postinstall unchecked shellexec
Filename: {app}\hydrus_client.exe; Description: Open the client; Flags: postinstall nowait unchecked
[Files]
Source: dist\Hydrus Network\*; DestDir: {app}; Flags: ignoreversion recursesubdirs createallsubdirs
[InstallDelete]
;v571: I made this basically do a clean install every time. There is no nice way to say "delete all folders except db", so might need to add specific versioned foldernames in future!
Name: {app}\Crypto; Type: filesandordirs; Components: install
Name: {app}\cv2; Type: filesandordirs; Components: install
Name: {app}\PySide6; Type: filesandordirs; Components: install
Name: {app}\tcl; Type: filesandordirs; Components: install
Name: {app}\tcl8; Type: filesandordirs; Components: install
Name: {app}\tk; Type: filesandordirs; Components: install
Name: {app}\wx; Type: filesandordirs; Components: install
Name: {app}\lz4-3.0.2-py3.7.egg-info; Type: filesandordirs; Components: install
Name: {app}\lz4-2.1.6-py3.6.egg-info; Type: filesandordirs; Components: install
Name: {app}\cryptography-2.9-py3.7.egg-info; Type: filesandordirs; Components: install
Name: {app}\cryptography-2.4.2-py3.6.egg-info; Type: filesandordirs; Components: install
Name: {app}\lib2to3; Type: filesandordirs; Components: install
Name: {app}\mpl-data; Type: filesandordirs; Components: install
Name: {app}\matplotlib; Type: filesandordirs; Components: install
Name: {app}\cryptography; Type: filesandordirs; Components: install
Name: {app}\*.exe; Type: files; Components: install
Name: {app}\*.pyd; Type: files; Components: install
Name: {app}\*.dll; Type: files; Components: install
