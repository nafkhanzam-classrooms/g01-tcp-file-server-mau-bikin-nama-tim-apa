import socket
import threading
import struct
import os

S_IP = "0.0.0.0"
S_PORT = 5000
S_GREEN = "\033[1;32m"
S_RED = "\033[1;31m"
S_CYAN = "\033[1;36m"
S_YELLOW = "\033[1;33m"
S_RESET = "\033[0m"
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
        buf += sock.recv(length - len(buf))
    return buf

def process_command(sock, data, addr, client_name="Anonymous"):
    addr_str = f"{S_CYAN}({client_name}-{addr[0]}:{addr[1]}){S_RESET}"
    
    p_label = f"{S_YELLOW}[PROCESS]{S_RESET}"

    # 1. Handle List
    if data == b"/list":
        print(f"{p_label} {addr_str}: Requested file list.")
        files = os.listdir(SERVER_FILES_DIR)
        res = ", ".join(files) if files else "Directory is empty."
        send_msg(sock, f"[LIST]: {res}")

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
            print(f"{p_label} {addr_str}: {S_RED}Download failed because '{filename}' not found.{S_RESET}")
            send_msg(sock, f"[ERROR]: File '{filename}' not found.")

    # 3. Handle Upload
    elif data.startswith(b"/upload "):
        try:
            content = data[8:]
            header, filedata = content.split(b":", 1)
            filename = header.decode('utf-8')
            
            print(f"{p_label} {addr_str}: Receiving '{filename}'.")
            with open(os.path.join(SERVER_FILES_DIR, filename), "wb") as f:
                f.write(filedata)
            
            send_msg(sock, f"[SUCCESS]: File '{filename}' stored on server.")
            print(f"{p_label} {addr_str}: {S_GREEN}Receiving '{filename}' is complete.{S_RESET}")
        except Exception as e:
            print(f"{p_label} {addr_str}: {S_RED}Receiving error {e}.{S_RESET}")
            send_msg(sock, b"[ERROR]: Receiving failed.")

    # 4. Handle Chat
    else:
        msg = data.decode('utf-8', errors='ignore')
        print(f"{S_BOLD}[CHAT]{S_RESET} {addr_str}: {msg}")
        send_msg(sock, f"[{client_name}]: {msg}")

def client_handler(sock, addr):
    print(f"{S_GREEN}[CONNECTED]{S_RESET}: Connection from {addr[0]}:{addr[1]}.")
    client_name = "Anonymous"
    try:
        while True:
            data = recv_msg(sock)
            if not data: break
            if data.startswith(b"/name "):
                client_name = data[6:].decode('utf-8', errors='ignore')
                print(f"{S_CYAN}[INFO]{S_RESET}: {client_name} has joined from {addr[0]}:{addr[1]}.")
                continue
            process_command(sock, data, addr, client_name)
    finally:
        print(f"{S_RED}[DISCONNECTED]{S_RESET}: Connection closed for {addr[0]}:{addr[1]}")
        sock.close()

def main():
    os.system("clear")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        s.bind((S_IP, S_PORT))
        s.listen(1)
        print(f"{S_BOLD}{S_GREEN}[INFO]: Server Sync is running on port {S_PORT}...{S_RESET}")
    except Exception as e:
        print(f"{S_RED}[ERROR]: Could not start server: {e}{S_RESET}")
        return

    while True:
        c_sock, addr = s.accept()
        threading.Thread(target=client_handler, args=(c_sock, addr), daemon=True).start()

if __name__ == "__main__":
    main()