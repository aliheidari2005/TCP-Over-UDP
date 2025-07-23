from tcp_socket import TCPSocket
from connection import Connection
import time


def main():

    client_sock = TCPSocket()
    client_sock.connect(('127.0.0.1', 12000))
    print("[CLIENT] Connected")

    conn = client_sock.connection
    while True:
        message = input()
        if message == "exit":
            conn.close()
            break
        print(f"[CLIENT] Sending: {message}")
        conn.send(message.encode())


if __name__ == "__main__":
    main()
