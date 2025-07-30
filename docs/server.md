---
title: Running Your Own Server  
---

# running your own server

!!! note
	**You do not need the server to do anything with hydrus! It is only for advanced users to do very specific jobs!** The server is also hacked-together and quite technical. It requires a fair amount of experience with the client and its concepts, and it does not operate on a timescale that works well on a LAN. Only try running your own server once you have a bit of experience synchronising with something like the PTR and you think, 'Hey, I know exactly what that does, and I would like one!'

	**[Here is a document put together by a user describing whether you want the server.](youDontWantTheServer.md)**

## setting up a server { id="intro" }

I will use two terms, _server_ and _service_, to mean two distinct things:

*   A **server** is an instantiation of the hydrus server executable (e.g. hydrus_server.exe in Windows). It has a complicated and flexible database that can run many different services in parallel.
*   A **service** sits on a port (e.g. 45871) and responds to certain http requests (e.g. `/file` or `/update`) that the hydrus client can plug into. A service might be a repository for a certain kind of data, the administration interface to manage what services run on a server, or anything else.

Setting up a hydrus server is very old-school, much like setting up a Quake server. It is easy compared to, say, Apache. There are no .conf files to mess about with, and everything is controlled through the client. When started from a terminal, the server will boot up and then wait for Ctrl+C. If you start it without a terminal (e.g. double-clicking on the exe), run a new instance from terminal and you should get some options to (s)top or (r)estart the old instance.

The basic process for setting up a server is:

*   Start the server.
*   Set up your client with its address and initialise the admin account
*   Set the server's options and services.
*   Make some accounts for your users.
*   ???
*   Profit

Let's look at these steps in more detail:

## start the server { id="start" }

Since the server and client have so much common code, I package them together. If you have the client, you have the server. If you installed in Windows, you can hit the shortcut in your start menu. Otherwise, go straight to 'hydrus_server' or 'hydrus_server.exe' or 'hydrus_server.py' in your installation directory. It is best to run it from terminal so you can see what it is doing. The program will first try to take port 45870 for its administration interface, so make sure that is free. If the server is running on a different computer to the one your admin client will be running on, open your server machine's firewall for that port as appropriate.

## set up the client { id="setting_up_the_client" }

In the _services->manage services_ dialog, add a new 'hydrus server administration service' and set up the basic options as appropriate. If you are running the server on the same computer as the client, its hostname is 'localhost'.

In order to set up the first admin account and an access key, use 'init' as a registration token. This special registration token will only work to initialise this first super-account.

!!! danger "YOU'LL WANT TO SAVE YOUR ACCESS KEY IN A SAFE PLACE"
    If you lose your admin access key, there is no way to get it back, and if you are not SQLite-proficient, you'll have to restart from the beginning by deleting your server's database files.

If your client can't connect to the server, it is either not running or you have a firewall/port-mapping problem. If you want a quick way to test the server's visibility, just put `https://host:port` into your browser (make sure it is https! http will not work)--if it is working, your browser will probably complain about its self-signed https certificate. Once you add a certificate exception, the server should return some simple html identifying itself.

## set up the server { id="setting_up_the_server" }

You should have a new submenu, 'administrate services', under 'services', in the client gui. This is where you control most server and service-wide stuff.

_admin->your server->manage services_ lets you add, edit, and delete the services your server runs. Every time you add one, you will also be added as that service's first administrator, and the admin menu will gain a new entry for it.

## making accounts { id="making_accounts" }

Go _admin->your service->create new accounts_ to create new registration tokens. Send the registration tokens to the users you want to give these new accounts. A registration token will only work once, so if you want to give several people the same account, they will have to share the access key amongst themselves once one of them has registered the account. (Or you can register the account yourself and send them all the same access key. Do what you like!)

Go _admin->manage account types_ to add, remove, or edit account types. Make sure everyone has at least downloader (get_data) permissions so they can stay synchronised.

You can create as many accounts of whatever kind you like. Depending on your usage scenario, you may want to have all uploaders, one uploader and many downloaders, or just a single administrator. There are many combinations.

If you want your friends to be able to see your server, you will probably need to figure out port forwarding in your router so the internet can talk to your server machine and perhaps a dynamic domain solution like no-ip.org so you can tell your friends a domain rather than your external IP (which may occasionally change). There are other, more advanced VPN/meshnet/proxy solutions to this problem that you may be familiar with. Again, once you have a host:port you know _should_ work, have your friends test `https://host:port` in a browser, and they should get the same welcome page result you do.

## ??? { id="have_fun" }

The most important part is to have fun! There are no losers on the INFORMATION SUPERHIGHWAY.

## profit { id="profit" }

I honestly hope you can get some benefit out of my code, whether just as a backup or as part of a far more complex system. Please mail me your thoughts as I am always keen to make improvements.

## Why can my friend not see what I just uploaded? { id="delays" }

Remember that the repositories do not work like conventional search engines; it takes a short but predictable while for changes to propagate to other users.

The client's searches only ever happen over its local cache of what is on the repository. Any changes you make will be delayed for others until the server's next update occurs. By default, the update period is 100,000 seconds--a little over a day. You will be able to see when the next update it due in `services->review services`. I recommend you upload at least one piece of information fairly soon--in the first update period is great--so other clients can, within a day, be confident they are all syncing properly.

As the admin, you can change the update period under 'administrate services'. Reducing it may be tempting for a server of just a small group of friends, since it means you'll see changes with lower latency, but don't go crazy. I would never dip below 10,000 seconds, and after some weeks the ratio between what is already on the server and what was added in the past day becomes far less important.

## btw, how to backup a repo's db { id="backing_up" }

All of a server's files and options are stored in its accompanying .db file and respective subdirectories, which are created on first startup (just like with the client). To backup or restore, you have two options:

*   Shut down the server, copy the database files and directories, then restart it. This is the only way, currently, to restore a db.
*   In the client, hit admin->your server->make a backup. This will lock the db server-side while it makes a copy of everything server-related to `server_install_dir/db/server_backup`. When the operation is complete, you can ftp/batch-copy/whatever the server\_backup folder wherever you like.

## OMG EVERYTHING WENT WRONG { id="hell" }

If you get to a point where you can no longer boot the repository, try running SQLite Studio and opening server.db. If the issue is simple--like manually changing the port number--you may be in luck. Send me an email if it is tricky.

Remember that everything is breaking all the time. Make regular backups, and you'll minimise your problems.
