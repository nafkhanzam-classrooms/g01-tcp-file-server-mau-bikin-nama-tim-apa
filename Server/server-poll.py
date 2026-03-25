import base64
import os
import select
import socket

HOST = "127.0.0.1"
PORT = 5000
BUFFER_SIZE = 4096
SERVER_FILES_DIR = "./Files/Uploaded"


def send_line(sock, line):
    sock.sendall((line + "\n").encode())


def broadcast(clients, line):
    broken = []
    for client in clients:
        try:
            send_line(client, line)
        except OSError:
            broken.append(client)
    return broken


def close_client(fd, poll_obj, fd_map, clients, recv_buf, client_list):
    if fd in fd_map:
        sock = fd_map[fd]
        addr = clients.get(sock)
        if addr:
            print("Disconnected:", addr)
        poll_obj.unregister(fd)
        del fd_map[fd]
        if sock in clients:
            del clients[sock]
        if sock in recv_buf:
            del recv_buf[sock]
        if sock in client_list:
            client_list.remove(sock)
        try:
            sock.close()
        except OSError:
            pass


os.makedirs(SERVER_FILES_DIR, exist_ok=True)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen(5)
server.setblocking(False)

poll_obj = select.poll()
poll_obj.register(server.fileno(), select.POLLIN)

fd_map = {server.fileno(): server}
clients = {}
recv_buf = {}
client_list = []

print(f"Server listening on {HOST}:{PORT}")

while True:
    for fd, event in poll_obj.poll():
        sock = fd_map[fd]

        if sock is server:
            conn, addr = server.accept()
            conn.setblocking(False)
            fd_map[conn.fileno()] = conn
            poll_obj.register(conn.fileno(), select.POLLIN)
            clients[conn] = addr
            recv_buf[conn] = ""
            client_list.append(conn)
            print('Connected:', addr)
            send_line(conn, "SYSTEM|Connected to server")
            continue

        elif event & select.POLLIN:
            data = sock.recv(BUFFER_SIZE)
            if not data:
                close_client(fd, poll_obj, fd_map, clients, recv_buf, client_list)
            else:
                recv_buf[sock] += data.decode(errors="replace")

                while "\n" in recv_buf[sock]:
                    line, recv_buf[sock] = recv_buf[sock].split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    addr = clients.get(sock, ("unknown", 0))
                    sender = f"{addr[0]}:{addr[1]}"

                    if line == "LIST":
                        files = sorted(
                            name
                            for name in os.listdir(SERVER_FILES_DIR)
                            if os.path.isfile(os.path.join(SERVER_FILES_DIR, name))
                        )
                        send_line(sock, f"LIST|{','.join(files)}")

                    elif line.startswith("DOWNLOAD|"):
                        filename = os.path.basename(line.split("|", 1)[1].strip())
                        if not filename:
                            send_line(sock, "ERROR|Filename is required")
                            continue

                        file_path = os.path.join(SERVER_FILES_DIR, filename)
                        if not os.path.isfile(file_path):
                            send_line(sock, f"ERROR|File not found: {filename}")
                            continue

                        with open(file_path, "rb") as f:
                            content = f.read()

                        encoded = base64.b64encode(content).decode()
                        send_line(sock, f"DOWNLOAD|{filename}|{encoded}")

                    elif line.startswith("UPLOAD|"):
                        parts = line.split("|", 2)
                        if len(parts) != 3:
                            send_line(sock, "ERROR|Invalid upload format")
                            continue

                        filename = os.path.basename(parts[1].strip())
                        content_b64 = parts[2]
                        if not filename:
                            send_line(sock, "ERROR|Filename is required")
                            continue

                        try:
                            content = base64.b64decode(content_b64.encode(), validate=True)
                        except Exception:
                            send_line(sock, "ERROR|Invalid file content")
                            continue

                        file_path = os.path.join(SERVER_FILES_DIR, filename)
                        with open(file_path, "wb") as f:
                            f.write(content)

                        send_line(sock, f"UPLOAD_OK|{filename}|{len(content)}")

                    elif line.startswith("CHAT|"):
                        message = line.split("|", 1)[1].strip()
                        if not message:
                            send_line(sock, "ERROR|Message cannot be empty")
                            continue

                        payload = f"CHAT|{sender}|{message}"
                        dead_clients = broadcast(client_list[:], payload)
                        for dead in dead_clients:
                            dead_fd = dead.fileno()
                            close_client(dead_fd, poll_obj, fd_map, clients, recv_buf, client_list)

                    else:
                        send_line(sock, "ERROR|Unknown command")

        elif event & select.POLLOUT:
            data = recv_buf[sock]
            n = sock.send(data)
            if n < len(data):
                recv_buf[sock] = data[n:]
            else:
                poll_obj.modify(fd, select.POLLIN)

        if event & (select.POLLHUP | select.POLLERR | select.POLLNVAL):
            close_client(fd, poll_obj, fd_map, clients, recv_buf, client_list)