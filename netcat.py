#!/usr/bin/env python3
"""A learning implementation inspired by Black Hat Python, second edition."""

import argparse
import socket
import shlex
import subprocess
import sys
import textwrap
import threading


def execute(cmd):
    """Run one program and return its output, including command errors."""
    cmd = cmd.strip()
    if not cmd:
        return ''
    try:
        output = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        output = exc.output
    except (OSError, ValueError) as exc:
        return f'Command error: {exc}\n'
    return output.decode(errors='replace')


class NetCat:
    def __init__(self, args, buffer=b''):
        self.args = args
        self.buffer = buffer
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.upload_lock = threading.Lock()

    def run(self):
        try:
            if self.args.listen:
                self.listen()
            else:
                self.send()
        finally:
            self.socket.close()

    def send(self):
        self.socket.connect((self.args.target, self.args.port))
        if self.buffer:
            self.socket.sendall(self.buffer)

        def forward_input():
            try:
                # Read terminal input by line, but preserve bytes from pipes/files.
                if sys.stdin.isatty():
                    for line in sys.stdin:
                        self.socket.sendall(line.encode())
                else:
                    while True:
                        chunk = sys.stdin.buffer.read1(65536)
                        if not chunk:
                            break
                        self.socket.sendall(chunk)
                # EOF ends an upload while leaving the reply direction open.
                self.socket.shutdown(socket.SHUT_WR)
            except OSError:
                pass  # The peer may close while terminal input is pending.

        threading.Thread(target=forward_input, daemon=True).start()
        while True:
            data = self.socket.recv(4096)
            if not data:
                break
            # TCP is a byte stream: a short read does not mean a complete reply.
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()

    def listen(self):
        self.socket.bind((self.args.target, self.args.port))
        self.socket.listen(5)
        print(f'Listening on {self.args.target}:{self.args.port}', file=sys.stderr)
        while True:
            client_socket, _ = self.socket.accept()
            threading.Thread(target=self.handle, args=(client_socket,), daemon=True).start()

    def handle(self, client_socket):
        with client_socket:
            try:
                if self.args.execute:
                    client_socket.sendall(execute(self.args.execute).encode())
                elif self.args.upload:
                    # Only one client can write the configured destination at a time.
                    with self.upload_lock:
                        with open(self.args.upload, 'wb') as destination:
                            while True:
                                data = client_socket.recv(65536)
                                if not data:
                                    break
                                destination.write(data)
                    client_socket.sendall(f'Saved file {self.args.upload}\n'.encode())
                elif self.args.command:
                    # readline retains later commands when TCP combines packets.
                    with client_socket.makefile('rb') as commands:
                        while True:
                            client_socket.sendall(b'BHP: #> ')
                            line = commands.readline(65537)
                            if not line:
                                break
                            if len(line) > 65536:
                                client_socket.sendall(b'Command too long.\n')
                                break
                            cmd = line.decode(errors='replace').strip()
                            if cmd.lower() in {'exit', 'quit'}:
                                break
                            client_socket.sendall(execute(cmd).encode())
                else:
                    # A plain listener echoes received bytes for connection tests.
                    while True:
                        data = client_socket.recv(4096)
                        if not data:
                            break
                        client_socket.sendall(data)
            except OSError as exc:
                print(f'Client error: {exc}', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='BHP Net Tool — educational TCP client and server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''\
            Examples (start a listener in another terminal):
              python netcat.py -t 127.0.0.1 -p 5555 -l -c
              python netcat.py -t 127.0.0.1 -p 5555 -l -u received.txt
              python netcat.py -t 127.0.0.1 -p 5555 -l -e "hostname"
              python netcat.py -t 127.0.0.1 -p 5555 -l
              python netcat.py -t 127.0.0.1 -p 5555
              echo ABC | python netcat.py -t 127.0.0.1 -p 5555
            '''),
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('-c', '--command', action='store_true', help='command session (listener only)')
    modes.add_argument('-e', '--execute', help='execute one program (listener only)')
    modes.add_argument('-u', '--upload', help='save incoming bytes to this file (listener only; overwrites)')
    parser.add_argument('-l', '--listen', action='store_true', help='listen for connections')
    parser.add_argument('-t', '--target', default='127.0.0.1', help='destination or local bind address (default: 127.0.0.1)')
    parser.add_argument('-p', '--port', type=int, default=5555, help='TCP port (default: 5555)')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    if not args.listen and any((args.command, args.execute is not None, args.upload is not None)):
        parser.error('--command, --execute, and --upload require --listen')
    if args.execute is not None and not args.execute.strip():
        parser.error('--execute must not be empty')
    if args.upload is not None and not args.upload.strip():
        parser.error('--upload must not be empty')
    try:
        NetCat(args).run()
    except KeyboardInterrupt:
        print('\nUser terminated.', file=sys.stderr)
    except OSError as exc:
        print(f'Network or output error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
