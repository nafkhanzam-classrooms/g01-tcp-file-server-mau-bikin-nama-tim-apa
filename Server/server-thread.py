import socket
import threading
import struct
import os

S_IP = "0.0.0.0"
S_PORT = 5000
S_GREEN= "\033[1;32m"
S_RED = "\033[1;31m"
S_CYAN = "\033[1;36m"
S_YELLOW = "\033[1;33m"
S_RESET= "\033[0m"
S_BOLD = "\033[1m"

SERVER_FILES_DIR = "server_files"
os.makedirs(SERVER_FILES_DIR, exist_ok=True)

clients_lock = threading.Lock()
clients  = {}

def send_msg(sock, data):
    if isinstance(data, str): data = data.encode()
    header = struct.pack(">I", len(data))
    sock.sendall(header + data)

def recv_msg(sock):
    header = sock.recv(4)
    if not header or len(header) < 4:
        return None
    length = struct.unpack(">I", header)[0]
    buf = b""
    while len(buf) < length:
        chunk = sock.recv(length - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf

def broadcast(snapshot, sender_sock, message):
    dead = []
    for sock in snapshot:
        if sock is not sender_sock:
            try:
                send_msg(sock, message)
            except OSError:
                dead.append(sock)
    return dead

def process_command(sock, data, snapshot):
    addr = snapshot[sock]["addr"]
    name= snapshot[sock]["name"]
    addr_str = f"{S_CYAN}({name}-{addr[0]}:{addr[1]}){S_RESET}"
    p_label = f"{S_YELLOW}[PROCESS]{S_RESET}"

    # 1. Handle List
    if data == b"/list":
        print(f"{p_label} {addr_str}: Requested file list.")
        files = os.listdir(SERVER_FILES_DIR)
        res = ", ".join(files) if files else "Directory is empty."
        send_msg(sock, f"[LIST]: {res}")
        return []

    # 2. Handle Download
    elif data.startswith(b"/download "):
        filename = data[10:].decode('utf-8', errors='ignore')
        filepath = os.path.join(SERVER_FILES_DIR, filename)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            print(f"{p_label} {addr_str}: Sending file: '{filename}'.")
            with open(filepath, "rb") as f:
                filedata = f.read()
            print(f"{p_label} {addr_str}: {S_GREEN}Download '{filename}' is successful.{S_RESET}")
            send_msg(sock, f"[SUCCESS]: Download '{filename}' is finished.")
        else:
            print(f"{p_label} {addr_str}: {S_RED}Download failed, '{filename}' not found.{S_RESET}")
            send_msg(sock, f"[ERROR]: File '{filename}' not found.")
        return []

    # 3. Handle Upload
    elif data.startswith(b"/upload "):
        try:
            content = data[8:]
            file_header, filedata = content.split(b":", 1)
            filename = file_header.decode('utf-8')
            print(f"{p_label} {addr_str}: Receiving '{filename}'.")
            with open(os.path.join(SERVER_FILES_DIR, filename), "wb") as f:
                f.write(filedata)
            send_msg(sock, f"[SUCCESS]: File '{filename}' stored on server.")
            print(f"{p_label} {addr_str}: {S_GREEN}Receiving '{filename}' is complete.{S_RESET}")
        except Exception as e:
            print(f"{p_label} {addr_str}: {S_RED}Receiving error: {e}.{S_RESET}")
            send_msg(sock, "[ERROR]: Upload failed.")
        return []

    # 4. Handle Chat
    else:
        msg = data.decode('utf-8', errors='ignore')
        print(f"{S_BOLD}[CHAT]{S_RESET} {addr_str}: {msg}")
        dead = broadcast(snapshot, sock, f"[{name}]: {msg}")
        return dead


class ClientHandler(threading.Thread):
    def __init__(self, sock, addr):
        super().__init__(daemon=True)
        self.sock = sock
        self.addr = addr

    def run(self):
        print(f"{S_GREEN}[CONNECTED]{S_RESET}: Connection from {self.addr[0]}:{self.addr[1]}.")
        with clients_lock:
            clients[self.sock] = {"addr": self.addr, "name": "Anonymous"}

        try:
            while True:
                data = recv_msg(self.sock)
                if not data:
                    break

                if data.startswith(b"/name "):
                    name = data[6:].decode('utf-8', errors='ignore')
                    with clients_lock:
                        clients[self.sock]["name"] = name
                    print(f"{S_CYAN}[INFO]{S_RESET}: {name} has joined from {self.addr[0]}:{self.addr[1]}.")
                    continue

                with clients_lock:
                    snapshot = dict(clients)

                dead = process_command(self.sock, data, snapshot)

                with clients_lock:
                    for d in dead:
                        clients.pop(d, None)
                for d in dead:
                    try:
                        d.close()
                    except OSError:
                        pass

        finally:
            with clients_lock:
                info = clients.pop(self.sock, {})
            name = info.get("name", "Anonymous")
            print(f"{S_RED}[DISCONNECTED]{S_RESET}: {name} from {self.addr[0]}:{self.addr[1]}.")
            try:
                self.sock.close()
            except OSError:
                pass


class Server:
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        os.system("clear")
        try:
            self.server.bind((S_IP, S_PORT))
            self.server.listen(5)
            print(f"{S_BOLD}{S_GREEN}[INFO]: Server Thread is running on port {S_PORT}...{S_RESET}")
        except Exception as e:
            print(f"{S_RED}[ERROR]: Could not start server: {e}{S_RESET}")
            return

        try:
            while True:
                c_sock, addr = self.server.accept()
                ClientHandler(c_sock, addr).start()
        except KeyboardInterrupt:
            print(f"\n{S_RED}[INFO]: Server shutting down.{S_RESET}")
        finally:
            self.server.close()


if __name__ == "__main__":
    Server().run()
