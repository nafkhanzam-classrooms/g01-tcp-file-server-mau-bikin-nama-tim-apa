import socket
import select
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

def broadcast(clients, sender_sock, message):
    dead = []
    for sock in list(clients):
        if sock is not sender_sock:
            try:
                send_msg(sock, message)
            except OSError:
                dead.append(sock)
    return dead

def process_command(sock, data, clients):
    addr = clients[sock]["addr"]
    name = clients[sock]["name"]
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
        dead = broadcast(clients, sock, f"[{name}]: {msg}")
        return dead

def remove_client(sock, poll_obj, fd_map, clients):
    info = clients.pop(sock, {})
    addr = info.get("addr", ("?", "?"))
    name = info.get("name", "Anonymous")
    print(f"{S_RED}[DISCONNECTED]{S_RESET}: {name} from {addr[0]}:{addr[1]}.")
    fd = sock.fileno()
    try:
        poll_obj.unregister(fd)
    except Exception:
        pass
    fd_map.pop(fd, None)
    try:
        sock.close()
    except OSError:
        pass

def main():
    os.system("clear")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        s.bind((S_IP, S_PORT))
        s.listen(5)
        print(f"{S_BOLD}{S_GREEN}[INFO]: Server Poll is running on port {S_PORT}...{S_RESET}")
    except Exception as e:
        print(f"{S_RED}[ERROR]: Could not start server: {e}{S_RESET}")
        return

    poll_obj = select.poll()
    poll_obj.register(s.fileno(), select.POLLIN)

    fd_map = {s.fileno(): s}
    clients = {}

    while True:
        for fd, event in poll_obj.poll():
            sock = fd_map[fd]

            if event & (select.POLLHUP | select.POLLERR | select.POLLNVAL):
                if sock is not s:
                    remove_client(sock, poll_obj, fd_map, clients)
                continue

            if event & select.POLLIN:
                if sock is s:
                    c_sock, addr = s.accept()
                    c_fd = c_sock.fileno()
                    fd_map[c_fd] = c_sock
                    poll_obj.register(c_fd, select.POLLIN)
                    clients[c_sock] = {"addr": addr, "name": "Anonymous"}
                    print(f"{S_GREEN}[CONNECTED]{S_RESET}: Connection from {addr[0]}:{addr[1]}.")

                else:
                    data = recv_msg(sock)
                    if not data:
                        remove_client(sock, poll_obj, fd_map, clients)
                        continue

                    if data.startswith(b"/name "):
                        name = data[6:].decode('utf-8', errors='ignore')
                        clients[sock]["name"] = name
                        addr = clients[sock]["addr"]
                        print(f"{S_CYAN}[INFO]{S_RESET}: {name} has joined from {addr[0]}:{addr[1]}.")
                        continue

                    dead = process_command(sock, data, clients)
                    for d in dead:
                        remove_client(d, poll_obj, fd_map, clients)

if __name__ == "__main__":
    main()
