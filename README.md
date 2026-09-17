# Python Netcat Replacement

A learning project assembled from notes and excerpts supplied while studying the “Replacing Netcat” section of *Black Hat Python*, second edition, by Justin Seitz and Tim Arnold (No Starch Press). This version fixes formatting and extends connection handling; it is not a verbatim listing from the book or a complete replacement for Netcat.

Requires Python 3.9 or later. Uses only the Python standard library.

## How the script fits together

1. **Imports** provide argument parsing, sockets, subprocesses, and threads.
2. **`execute()`** runs a program and captures its output or error.
3. **`NetCat`** owns the connection. `run()` chooses client `send()` or server `listen()`. The server starts `handle()` for each accepted client.
4. **`main()`** defines and validates command-line options, then starts `NetCat`.
5. **`if __name__ == '__main__':`** calls `main()` only when the file is run directly. Keeping this at the bottom means the class is defined before it is used.

Inside the class, methods are indented four spaces; their bodies are indented eight spaces. `self.send()` calls a method; `self.send` alone only refers to it.

## Try it locally

Run these commands from the folder containing `netcat.py`. Use `python3` on systems where that is the Python command, or `py` on Windows if appropriate.

Show all options:

```sh
python netcat.py --help
```

In terminal 1, start an echo listener:

```sh
python netcat.py -l -t 127.0.0.1 -p 5555
```

In terminal 2, send text:

```sh
echo ABC | python netcat.py -t 127.0.0.1 -p 5555
```

Stop the listener with Ctrl+C before trying another mode on the same port.

### Command session

Terminal 1:

```sh
python netcat.py -l -c
```

Terminal 2:

```sh
python netcat.py
```

At `BHP: #> `, enter `hostname`. Enter `exit` or `quit` to disconnect. Commands run on the listener's computer, under its user account. This executes individual programs; shell built-ins such as `cd` and `dir`, pipelines, redirection, and persistent shell state are not supported. Argument splitting follows `shlex` conventions, so Windows paths may need quoting and forward slashes.

### Execute one program

Terminal 1: `python netcat.py -l -e "hostname"`

Terminal 2: `python netcat.py`

The server sends the result and closes that client connection, while continuing to listen for new clients.

### Save an upload

Terminal 1: `python netcat.py -l -u received.txt`

Terminal 2: `echo ABC | python netcat.py`

On Bash or Windows Command Prompt, upload a file using `python netcat.py < source.bin`. PowerShell's text pipeline is suitable for the text example above, but should not be used to transfer arbitrary binary files. Run file redirection from Command Prompt for binary uploads on Windows.

The filename belongs to the listener. Existing destination files are overwritten. The sender signals end of input by closing its sending direction, then waits for the server's confirmation. A failed or interrupted upload can leave a partial file. Interactive terminal EOF is Ctrl+D on Unix or Ctrl+Z followed by Enter on Windows.

## Changes from the supplied excerpts

- Restored indentation, double underscores, and escaped characters.
- Added the missing target option and corrected `-e` and the `send()` call.
- Used `sendall()` and receive-until-disconnect loops. TCP packet sizes do not define message boundaries.
- Forwarded stdin in a background thread so prompts and incoming output appear immediately without waiting for stdin to finish.
- Preserved binary pipe data and streamed uploads to disk instead of buffering an entire file.
- Handled empty commands, failed programs, and client disconnections; kept one client's errors from closing the listener.
- Read commands by line, including multiple commands received together.
- Added a plain echo mode and validation for incompatible options and invalid ports.

## Scope

Use on your own machines or an authorized lab. The default address is localhost. There is no authentication or encryption; command mode grants command execution to connected clients. Keep it on a trusted lab network. This is a small teaching tool: commands have no execution timeout, and the listener does not limit concurrent clients.

## Attribution

Based on the user's study excerpts from *Black Hat Python*, second edition. Original book material remains attributable to its authors and publisher. No blanket license is assigned to the upstream material by this repository.
