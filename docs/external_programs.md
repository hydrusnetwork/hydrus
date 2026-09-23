---
title: External Programs
---

!!! warning "Notice"
    This system is under construction, and this help page is a first draft. At the moment, the exe manager only supports 'send single file' and 'send single URL' jobs, but I expect to extend it to do more soon.

## other programs { id="intro" }

There are times when hydrus wants to communicate with other programs. It might want to say "Open this Ebook" to a specialised document viewer or "Open this URL" to a web browser, or maybe something more sophisticated like "Tell me which tags this image should have".

These program calls are highly user-customisable under `options->external programs`.

## the executable manager

(image tbd of the options page)

There are several "types" of call that hydrus understands:

- "Send single file" sends a file or file identifier and receives no results.
- "Send single URL" sends an URL and receives no results.
- _"Get file tags" sends a file or file identifier and receives a list of tags._
- _"Download URL" sends an URL and a temporary_dir and expects the program to place the result of the URL download in the temporary directory._

Places in the program that fit one of those shapes can consult the appropriate list of executables to provide options on what to do. For instance, the "Open file externally" command expects to send a file (usually a file path) and receive nothing back. The settings under `options->open externally` use the 'send file/URL' executable calls you define under `options->external programs`.

The important part here is that Hydrus doesn't care about how the job is done--all it needs to be told is "if you send (these parameters) at (this program), you get (this stuff back)". It lets us add new features easily.

Let's look at a simple "send single file" example.

## open file externally

Firefox can open all sorts of files. If you have firefox, try opening up a terminal or command-line and type `firefox "%path%"`, where `%path` is either `/path/to/an/image.jpeg` or `C:\path\to\an\image.jpeg`, depending on your system. The command should return instantly, and firefox will appear, showing the image.

You should have a 'firefox (file path)' entry in your defaults. Check it out:

(image tbd of the edit panel)

This command teaches hydrus how to launch `firefox %path%`. Look at the left pane, from top to bottom:

### Job type

The job type is set as 'send single file'. This tells hydrus that this firefox call is something that fits into 'open file externally' jobs.

### External Call

Since we are launching a local process, we are set to 'local process call'.

### Input Parameters

Hydrus can provide multiple ways of referring to the file that is being 'sent'. We want the file path, so we have checked that and we have set that file path to have a token name of `%path%`. You can use any token you like, so if your executable uses percent signs for its own static parameters and putting `%path%` in there would be confusing, feel free to change it to `FILE_PATH` or `||||PATH||||` or whatever works for you.

You can select multiple input parameters, if you need them. If you are building up a database of file information, you might want to track both file hash and id, for instance, and maybe do processing on the actual file path too.

### Command Template

Hit the edit button to see how this works:

(image tbd of command template edit panel)

When the call is made, any parameter that includes our magic `%path%` token will have that token replaced with the actual file path. You can embed the token in a longer string, like `-o{%path%}`, and it all works. If you use just `%path%`, then we might type `firefox "%path%"` in the terminal to ensure that whitespace does not break things, but here it is important to not add those quotes. You only need to use quotes here if it is _inside_ a parameter, let's say for a parameter like `-profile="My Special Profile"`.

If your call includes multiple parameters, you add multiple, like this:

(image tbd of multi-param call)

If you have a complicated executable to call that has dozens of difficult parameters, just roll it into a little .sh or .py script that takes the %path% and invoke that from hydrus instead.

!!! info "PATH"
    If you do not know what the PATH is, ask a chatbot!
    
    Hydrus's PATH is what you launch it with, usually plus its base and bin dir. Maybe a bit more if you use a built release.
    
    If the executable you want to call is not on your PATH, you need to declare the entire executable file path, something like `/home/me/my_project/cool_program` or `C:\stuff\bins\cool_program.exe`. A specific path is obviously less portable than a name, so think about this if you want to share your executable definition.

### Extra Options

For 'open externally', we are not listening for a response, and the media viewer called might stay open for a long time, even longer than hydrus stays alive. We do not want hydrus to set a timeout here.

'hide terminal' and 'output is text' should generally be left on unless you know what you are doing.

### sharing and security

!!! danger "AYY LMAO"
    Do not skip this part!

Like many other user-configurable hydrus systems, these exe definitions are easily shared via JSON or PNG files. This allows cool solutions to spread around.

However, taking an instruction for "run this program on your machine" from another person across the internet is something to be cautious about. You might not notice if he gives you a command that does something neat but then, with some clever quiet trick--let's say the exe offers a "once job complete, call this second thing" parameter--also tries to execute something bad (e.g. steal your passwords and upload them to his server).

THEREFORE, if you import an exe definition from someone else, load up its edit panel and just give it the once over. If it is nice and simple, something like `program -open %path%`, then all is well. If it tucks multiple kilobytes of obfuscated bash scripting into a parameter, delete that call! Do not run a test on it!

Similarly, if the call uses a network operation like `curl` or `wget`--are you sure that is what you wanted?

### Testing

Once you are set up, look at the testing panel on the right. Put in a valid value for each input parameter you have set up, e.g. an actual URL, and then click test, and the job will fire for real. If everything is good, your program should do its thing.

!!! info "Flatpak/Sandboxing"
    If hydrus is aggressively sandboxed/bubblewrapped, it may not see the exe. Similarly, if the _exe_ is sandboxed, it may not see a path that hydrus gives it. Consider this carefully--you might need to, say, install Flatseal and add your hydrus file storage dir to your program's viewable directories.
