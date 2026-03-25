import socket
import threading
import struct
import os
import sys

C_GREEN = "\033[1;32m"
C_RED = "\033[1;31m"
C_RESET = "\033[0m"
C_YELLOW= "\033[1;33m"
C_BOLD = "\033[1m"

CLIENT_FILES_DIR = "client_files"
os.makedirs(CLIENT_FILES_DIR, exist_ok=True)

def send_msg(sock, data):
    header = struct.pack(">I", len(data))
    sock.sendall(header + data)

def recv_msg(sock):
    header = sock.recv(4)
    length = struct.unpack(">I", header)[0]
    if not header or len(header) < 4:
        return None
    buf = b""
    while len(buf) < length:
        buf += sock.recv(length - len(buf))
    return buf

def handle_list(sock):
    send_msg(sock, b"/list")

def handle_download(sock, cmd):
    parts = cmd.split()
    if len(parts) == 1:
        print(f"{C_RED}[ERROR]: Please specify a filename. Usage: /download <filename>{C_RESET}")
        return
    if len(parts) > 2:
        print(f"{C_RED}[ERROR]: Too many arguments. Please provide only one filename.{C_RESET}")
        return
    filename = parts[1]
    print(f"{C_YELLOW}[DOWNLOAD]: Starting download for '{filename}'...{C_RESET}")
    send_msg(sock, f"/download {filename}".encode())

def handle_upload(sock, cmd):
    parts = cmd.split()
    if len(parts) == 1:
        print(f"{C_RED}[ERROR]: Please specify a filename. Usage: /upload <filename>{C_RESET}")
        return
    if len(parts) > 2:
        print(f"{C_RED}[ERROR]: Too many arguments. Please upload one file at a time.{C_RESET}")
        return

    filename = parts[1]
    filepath = os.path.join(CLIENT_FILES_DIR, filename)
    
    if os.path.exists(filepath):
        try:
            print(f"{C_YELLOW}[PENDING]: Uploading '{filename}' to server...{C_RESET}")
            with open(filepath, "rb") as f:
                filedata = f.read()
            payload = f"/upload {filename}:".encode() + filedata
            send_msg(sock, payload)
        except Exception as e:
            print(f"{C_RED}[ERROR]: Failed to read file: {e}{C_RESET}")
    else:
        print(f"{C_RED}[ERROR]: File '{filename}' not found in {CLIENT_FILES_DIR}/{C_RESET}")

def print_menu():
    print(f"\n{C_BOLD}{'-'*24} COMMAND LIST {'-'*24}{C_RESET}")
    print("/list\t\t\t: View files available on server")
    print("/upload <filename>\t: Upload a file to server")
    print("/download <filename>\t: Download a file from server")
    print("/exit\t\t\t: Close connection")
    print("<type message>\t\t: Send a text message (Chat)")
    print("-" * 62)

def receive_handler(sock):
    while True:
        data = recv_msg(sock)
        if data is None:
            print(f"\n{C_RED}[INFO]: Disconnected from server.{C_RESET}")
            os._exit(0)

        sys.stdout.write('\r\033[K')
        
        if data.startswith(b"/download "):
            try:
                content = data[10:]
                header, filedata = content.split(b":", 1)
                filename = header.decode('utf-8')
                
                filepath = os.path.join(CLIENT_FILES_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(filedata)
                
                print(f"{C_GREEN}[SUCCESS]: File '{filename}' downloaded to {CLIENT_FILES_DIR}/{C_RESET}")
            except Exception as e:
                print(f"{C_RED}[ERROR]: Failed to save downloaded file: {e}{C_RESET}")
            return
            
        try:
            msg_str = data.decode('utf-8', errors='ignore')
            if any(key in msg_str for key in ["[LIST]", "[INFO]", "[SUCCESS]", "[UPLOAD]", "[DOWNLOAD]"]):
                print(f"{C_GREEN}{msg_str}{C_RESET}")
            elif "[ERROR]" in msg_str:
                print(f"{C_RED}{msg_str}{C_RESET}")
            else:
                print(msg_str)
        except Exception:
            pass

        print("> ", end="")
        sys.stdout.flush()

def main():
    os.system("clear")
    name = input("Enter your username: ").strip() or "Anonymous"

    print(f"\n{C_BOLD}--- Connection Settings ---{C_RESET}")
    target_ip = input("Enter Server IP: ").strip()
    target_port = int(input("Enter Server Port: ").strip())

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print(f"{C_GREEN}[INFO]: Connecting to {target_ip}:{target_port}...{C_RESET}")
        s.connect((target_ip, target_port))
        send_msg(s, f"/name {name}".encode())
        print(f"{C_GREEN}[INFO]: Successfully connected!{C_RESET}")
    except Exception as exception:
        print(f"{C_RED}[ERROR]: Connection failed: {exception}{C_RESET}")
        return

    print_menu()
    
    threading.Thread(target=receive_handler, args=(s,), daemon=True).start()

    while True:
        try:
            cmd = input("> ").strip()
            if not cmd:
                continue
            if cmd == "/exit":
                print(f"{C_RED}[INFO]: Closing connection...{C_RESET}")
                s.close()
                os._exit(0)
            elif cmd == "/list":
                handle_list(s)
            elif cmd.startswith("/download "):
                handle_download(s, cmd)
            elif cmd.startswith("/upload "):
                handle_upload(s, cmd)
            elif cmd.startswith("/"):
                print(f"{C_RED}[ERROR]: Unknown command.{C_RESET}")
            else:
                send_msg(s, cmd.encode())
                
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C_RED}[INFO]: Connection interrupted by user.{C_RESET}")
            break

if __name__ == "__main__":
    main()