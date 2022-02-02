#ifndef Version
    #define Version "Null"
#endif

[Icons]
Name: {group}\hydrus client; Filename: {app}\client.exe; WorkingDir: {app}; Tasks: programgroupicons
Name: {group}\hydrus server; Filename: {app}\server.exe; WorkingDir: {app}; Tasks: programgroupicons
;Taking this out to stop anti-virus testbeds pursing it and launching Edge and detecting Edge update calls as suspicious DNS lmao
;Name: {group}\help; Filename: {app}\help\index.html; WorkingDir: {app}; Tasks: programgroupicons
Name: {group}\uninstall hydrus network; Filename: {uninstallexe}; WorkingDir: {app}; Tasks: programgroupicons; IconFilename: {app}\static\cross.ico
Name: {userdesktop}\hydrus client; Filename: {app}\client.exe; WorkingDir: {app}; Tasks: desktopicons
Name: {userdesktop}\hydrus server; Filename: {app}\server.exe; WorkingDir: {app}; Tasks: desktopicons
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
Uninstallable=IsComponentSelected('install')
UninstallDisplayIcon={app}\static\hydrus.ico
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
;Taking this out to stop anti-virus testbeds pursing it and launching Edge and detecting Edge update calls as suspicious DNS lmao
;Filename: {app}\help\index.html; Description: Open help/getting started guide (highly recommended for new users); Flags: postinstall unchecked shellexec
Filename: {app}\client.exe; Description: Open the client; Flags: postinstall nowait unchecked
[Files]
Source: dist\Hydrus Network\*; DestDir: {app}; Flags: ignoreversion recursesubdirs createallsubdirs
[InstallDelete]
Name: {app}\Crypto; Type: filesandordirs; Components: install
Name: {app}\tcl; Type: filesandordirs; Components: install
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
Name: {app}\opencv_ffmpeg344_64.dll; Type: files; Components: install
Name: {app}\opencv_ffmpeg400_64.dll; Type: files; Components: install
Name: {app}\opencv_ffmpeg410_64.dll; Type: files; Components: install
Name: {app}\opencv_videoio_ffmpeg411_64.dll; Type: files; Components: install
Name: {app}\opencv_videoio_ffmpeg412_64.dll; Type: files; Components: install
Name: {app}\opencv_videoio_ffmpeg420_64.dll; Type: files; Components: install
Name: {app}\opencv_videoio_ffmpeg440_64.dll; Type: files; Components: install
Name: {app}\wxmsw30u_core_vc140_x64.dll; Type: files; Components: install
Name: {app}\wxmsw30u_adv_vc140_x64.dll; Type: files; Components: install
Name: {app}\wxbase30u_vc140_x64.dll; Type: files; Components: install
Name: {app}\wxbase30u_net_vc140_x64.dll; Type: files; Components: install
Name: {app}\tk86t.dll; Type: files; Components: install
Name: {app}\tcl86t.dll; Type: files; Components: install
Name: {app}\_tkinter.pyd; Type: files; Components: install
Name: {app}\_yaml.cp36-win_amd64.pyd; Type: files; Components: install
Name: {app}\_yaml.cp37-win_amd64.pyd; Type: files; Components: install
Name: {app}\_cffi_backend.cp36-win_amd64.pyd; Type: files; Components: install
Name: {app}\_distutils_findvs.pyd; Type: files; Components: install
