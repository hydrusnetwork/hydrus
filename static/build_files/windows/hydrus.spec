# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

client_a = Analysis(['hydrus\\hydrus_client.pyw'],
             pathex=['.'],
             binaries=[
               ('hydrus\\static\\build_files\\windows\\sqlite3.dll', '.'),
               ('hydrus\\static\\build_files\\windows\\sqlite3.exe', 'db'),
               ('hydrus\\libmpv-2.dll', '.')
             ],
             datas=[
               ('hydrus\\bin', 'bin'),
               ('hydrus\\help', 'help'),
               ('hydrus\\static', 'static'),
               ('hydrus\\license.txt', '.'),
               ('hydrus\\README.md', '.'),
               ('hydrus\\auto_update_installer.bat', '.'),
               ('hydrus\\help my client will not boot.txt', '.'),
               ('hydrus\\db', 'db')
             ],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

server_a = Analysis(['hydrus\\hydrus_server.py'],
             pathex=['.'],
             binaries=[
               ('hydrus\\static\\build_files\\windows\\sqlite3.dll', '.')
             ],
             datas=[],
             hiddenimports=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

client_pyz = PYZ(client_a.pure, client_a.zipped_data, cipher=block_cipher)
server_pyz = PYZ(server_a.pure, server_a.zipped_data, cipher=block_cipher)

client_exe = EXE(client_pyz,
                 client_a.scripts,
                 [],
                 exclude_binaries=True,
                 name='hydrus_client',
                 contents_directory='lib',
                 debug=False,
                 bootloader_ignore_signals=False,
                 strip=False,
                 upx=True,
                 console=False,
                 version='client_file_version_info.txt',
                 icon='hydrus\\static\\hydrus.ico' )

server_exe = EXE(server_pyz,
                 server_a.scripts,
                 [],
                 exclude_binaries=True,
                 name='hydrus_server',
                 contents_directory='lib',
                 debug=False,
                 bootloader_ignore_signals=False,
                 strip=False,
                 upx=False,
                 console=True,
                 version='server_file_version_info.txt',
                 icon='hydrus\\static\\hydrus.ico' )

coll = COLLECT(server_exe,
               server_a.binaries,
               server_a.zipfiles,
               server_a.datas,
               client_exe,
               client_a.binaries,
               client_a.zipfiles,
               client_a.datas,
               strip=False,
               upx=False,
               upx_exclude=[],
               name='Hydrus Network')
