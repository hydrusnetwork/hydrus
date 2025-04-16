---
title: Introduction  
---

## this help { id="this_help" }

Click the links on the left to go through the getting started guide. Subheadings are on the right. Larger sections are up top. Please at least skim every page in the getting started section, as this will introduce you to the main systems in the client. There is a lot, so you do not have to do it all in one go.

The section on installing, updating, and **backing up** is very important.

This help is available locally in every release. Hit `help->help and getting started guide` in the client, or open `install_dir/help/index.html`.

## on having too many files { id="files" }

I've been on the internet for a <span style="color:red">lo</span><span style="color:green">ng</span> time, and I've always saved cool things I came across. After a while, my collection became too large to manage. I couldn't find anything in the mess, and I just saved new things in there with filenames like 'image1257.jpg'.

There aren't many solutions to this problem, particularly those that will work on the scale of tens or hundreds of thousands of files. I decided to make a solution myself, and here we are.

## the hydrus network { id="hydrus_network" }

So! I'm developing a program that helps people organise their files on their own terms. I want to help you do what you want with your stuff, and that's it. You can anonymously share some tags with other people if you want to, but you don't have to connect to anything if you don't. **The default is complete privacy, no sharing**, and every upload requires a conscious action on your part. I don't plan to ever record metrics on users, nor serve ads, nor charge for my software. The software never phones home.

This does a lot more than a normal image viewer. If you are totally new to the idea of personal media collections and booru-style tagging, I suggest you start slow, walk through the getting started guides, and experiment doing different things. If you aren't sure on what a button does, try clicking it! You'll be importing thousands of files and applying _tens_ of thousands of tags in no time. The best way to learn is just to try things out.

The client is chiefly a file database. It stores your files inside its own folders, managing them faster and more richly than an explorer window or online gallery. Here's a screenshot of one of my test installs with a search showing all files:

[![](images/example_client.png "WELCOME TO INTERNET")](images/example_client.png)

As well as the client, there is also a server that anyone can run to store tags or files for sharing between many users. This is advanced, and almost always confusing to new users, so do not explore this until you know what you are doing. There is, however, a user-run **public tag repository**, with more than a billion tags, that you can access and contribute to if you wish.

I have many ideas on how to improve the software in future. If, after a few months, you find you enjoy it and would like to offer support, I have set up a simple no-reward patreon, which you can read more about [here](support.md).

## license

This is free software. Everything I, hydrus dev, have made is under the very permissive Do What The Fuck You Want To Public License, Version 3:

``` title="license.txt"
--8<-- "license.txt"
```

This is a joke, but it also isn't. If you want to fork my code and change it to do something else, go ahead. In the same way, looking after your client and making backups in case something goes wrong is your responsibility.
