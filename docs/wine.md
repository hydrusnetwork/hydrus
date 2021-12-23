---
title: running in wine
---

# running a client or server in wine

Several Linux and macOS users have found success running hydrus with Wine. Here is a post from a Linux dude:

---

Some things I picked up on after extended use:

*   Wine is kinda retarded sometimes, do not try to close the window by pressing the red close button, while in fullscreen.
*   It will just "go through" it, and do whatever to whats behind it.
*   Flash do work, IF you download the internet explorer version, and install it through wine.
*   Hydrus is selfcontained, and portable. That means that one instance of hydrus do not know what another is doing. This is great if you want different installations for different things.
*   Some of the input fields behave a little wonky. Though that may just be standard Hydrus behavior.
*   Mostly everything else works fine. I was able to connect to the test server and view there. Only thing I need to test is the ability to host a server.

Installation process:

1. Get a standard Wine installation.
2. Download the latest hydrus .zip file.
3. Unpack it with your chosen zip file opener, in the chosen folder. Do not need to be in the wine folder.
4. Run it with wine, either though the file manager, or though the terminal.
5. For Flash support install the IE version through wine.

---

If you get the client running in Wine, please let me know how you get on!