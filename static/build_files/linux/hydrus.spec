# -*- mode: python -*-

block_cipher = None

client_a = Analysis(['hydrus/hydrus_client.py'],
             pathex=['.'],
             binaries=[],
             datas=[
               ('hydrus/bin', 'bin'),
               ('hydrus/help', 'help'),
               ('hydrus/static', 'static'),
               ('hydrus/license.txt', '.'),
               ('hydrus/README.md', '.'),
               ('hydrus/help my client will not boot.txt', '.'),
               ('hydrus/db', 'db')
             ],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

server_a = Analysis(['hydrus/hydrus_server.py'],
             pathex=['.'],
             binaries=[],
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
                 console=False )

server_exe = EXE(server_pyz,
                 server_a.scripts,
                 [],
                 exclude_binaries=True,
                 name='hydrus_server',
                 contents_directory='lib',
                 debug=False,
                 bootloader_ignore_signals=False,
                 strip=False,
                 upx=True,
                 console=True )

coll = COLLECT(client_exe,
               server_exe,
               client_a.binaries,
               client_a.zipfiles,
               client_a.datas,
               server_a.binaries,
               server_a.zipfiles,
               server_a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='Hydrus Network')
