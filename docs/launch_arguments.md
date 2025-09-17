---
title: Launch Arguments
---

# launch arguments

You can launch the program with several different arguments to alter core behaviour. If you are not familiar with this, you are essentially putting additional text after the launch command that runs the program. You can run this straight from a terminal console (usually good to test with), or you can bundle it into an easy shortcut that you only have to double-click. An example of a launch command with arguments:

```
C:\Hydrus Network\hydrus_client.exe -d="E:\hydrus db" --no_db_temp_files
```

You can also add --help to your program path, like this:

- `hydrus_client.py --help`
- `hydrus_server.exe --help`
- `./hydrus_server --help`

Which gives you a full listing of all below arguments, however this will not work with the built hydrus_client executables, which are bundled as a non-console programs and will not give you text output to any console they are launched from. As hydrus_client.exe is the most commonly run version of the program, here is the list, with some more help about each command:

##**`-d DB_DIR, --db_dir DB_DIR`**

Lets you customise where hydrus should use for its base database directory. This is install_dir/db by default, but many advanced deployments will move this around, as described [here](database_migration.md). When an argument takes a complicated value like a path that could itself include whitespace, you should wrap it in quote marks, like this:

```
-d="E:\my hydrus\hydrus db"
```

##**`--temp_dir TEMP_DIR`**

This tells all aspects of the client, including the SQLite database, to use a different path for temp operations. This would be by default your system temp path, such as:

```
C:\Users\You\AppData\Local\Temp
```

But you can also check it in _help->about_. A handful of database operations (PTR tag processing, vacuums) require a lot of free space, so if your system drive is very full, or you have unusual ramdisk-based temp storage limits, you may want to relocate to another location or drive.

##**`--db_journal_mode {WAL,TRUNCATE,PERSIST,MEMORY}`**

Change the _journal_ mode of the SQLite database. The default is WAL, which works great for almost all SSD drives, but if you have a very old or slow drive, or if you encounter 'disk I/O error' errors on Windows with an NVMe drive, try TRUNCATE. Full docs are [here](https://sqlite.org/pragma.html#pragma_journal_mode).

Briefly:

*   WAL - Clever write flushing that takes advantage of new drive synchronisation tools to maintain integrity and reduce total writes.
*   TRUNCATE - Compatibility mode. Use this if your drive cannot launch WAL.
*   PERSIST - This is newly added to hydrus. The ideal is that if you have a high latency HDD drive and want sync with the PTR, this will work more efficiently than WAL journals, which will be regularly wiped and recreated and be fraggy. Unfortunately, with hydrus's multiple database file system, SQLite ultimately treats this as DELETE, which in our situation is basically the same as TRUNCATE, so does not increase performance. Hopefully this will change in future.
*   MEMORY - Danger mode. Extremely fast, but you had better guarantee a lot of free ram and no unclean exits.

##**`--db_transaction_commit_period DB_TRANSACTION_COMMIT_PERIOD`**

Change the regular duration at which any database changes are committed to disk. By default this is 30 (seconds) for the client and 120 for the server. Minimum value is 10. Typically, if hydrus crashes, it may 'forget' what happened up to this duration on the next boot. Increasing the duration will result in fewer overall 'commit' writes during very heavy work that makes several changes to the same database pages (read up on [WAL](https://sqlite.org/wal.html) mode for more details here), but it will increase commit time and memory/storage needs. Note that changes can only be committed after a job is complete, so if a single job takes longer than this period, changes will not be saved until it is done.

##**`--db_cache_size DB_CACHE_SIZE`**

Change the size of the cache SQLite will use for each db file, in MB. By default this is 256, for 256MB, which for the four main client db files could mean an absolute 1GB peak use if you run a very heavy client and perform a long period of PTR sync. This does not matter so much (nor should it be fully used) if you have a smaller client.

##**`--db_synchronous_override {0,1,2,3}`**

Change the rules governing how SQLite writes committed changes to your disk. The hydrus default is 1 with WAL, 2 otherwise.

A user has written a full guide on this value [here](Understanding_Database_Synchronization.md)! SQLite docs [here](https://sqlite.org/pragma.html#pragma_synchronous).

##**`--no_db_temp_files`**

When SQLite performs very large queries, it may spool temporary table results to disk. These go in your temp directory. If your temp dir is slow but you have a _ton_ of memory, set this to never spool to disk, as [here](https://sqlite.org/pragma.html#pragma_temp_store).

##**`--boot_debug`**

Prints additional debug information to the log during the bootup phase of the application.

##**`--no_user_static_dir`**

Disallows the 'custom assets' override that lets files in `db_dir/static` override what is it `install_dir/static`. Use for quick debugging.

##**`--profile_mode`**

This starts the program with 'Profile Mode' turned on, which captures the performance of boot functions. This is also a way to get Profile Mode on the server, although support there is very limited. Since Profile Mode is now split into different types, note this specifically turns on "db" Profile Mode.

# client-specific arguments

##**`--pause_network_traffic`**

This starts the program with `network->pause->all new network traffic` on. Useful for debugging a downloader in your boot session that is going crazy or stopping a problem subscription from launching.

##**`--win_qt_darkmode_test`**

**Windows only:** This starts the program with Qt's 'darkmode' detection enabled, as [here](https://doc.qt.io/qt-6/qguiapplication.html#platform-specific-arguments), set to 1 mode. It will override any existing qt.conf, so it is only for experimentation. We are going to experiment more with the 2 mode, but that locks the style to `windows`, and can't handle switches between light and dark mode.

# server-specific arguments

The server also takes an optional _positional_ argument of 'start' (start the server, the default), 'stop' (stop any existing server), or 'restart' (do a stop, then a start), which should go before any of the above arguments.
