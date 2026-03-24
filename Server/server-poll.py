import socket, select

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('127.0.0.1', 5000))
server.listen(5)
server.setblocking(False)

poll_obj = select.poll()
poll_obj.register(server.fileno(), select.POLLIN)

fd_map = {server.fileno(): server}
send_buf = {}

while True:
    for fd, event in poll_obj.poll():
        sock = fd_map[fd]

        if sock is server:
            conn, addr = server.accept()
            conn.setblocking(False)
            fd_map[conn.file()] = conn
            poll_obj.register(conn.fileno(), select.POLLIN)
            print('Connected:', addr)

        elif event & select.POLLIN:
            data = sock.recv(4096)
            if not data:
                poll_obj.unregister(fd); del fd_map[fd]; sock.close()
            else:
                send_buf[sock] = data
                poll_obj.modify(fd, select.POLLOUT)

        elif event & select.POLLOUT:
            data = send_buf[sock]
            n = sock.send(data)
            if n < len(data):
                send_buf[sock] = data[n:]
            else:
                poll_obj.modify(fd, select.POLLIN)

        if event & (select.POLLHUP | select.POLLERR | select.POLLNVAL):
            poll_obj.unregister(fd)
            del fd_map[fd]
            sock.close()