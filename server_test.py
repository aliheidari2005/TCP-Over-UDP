from server_socket import ServerSocket
import time


def main():

    server = ServerSocket()
    server.bind(('127.0.0.1', 12000))
    server.listen(backlog=5)

    print("[SERVER] Waiting for client...")
    conn = server.accept()
    print("[SERVER] Client connected.")

    # Communicate
    while True:
        message = input()
        if message == "exit":
            conn.close()
            break
        print(f"[CLIENT] Sending: {message}")
        conn.send(message.encode())

    # response = b"Hello from server"
    # print(f"[CLIENT] Sending: {response}")
    # conn.send(response)

    while 1:
        {}

    # time.sleep(5)
    # Graceful connection close
    conn.close()

    # # Close listener socket (no new SYNs will be accepted)
    # server.close()


if __name__ == "__main__":
    main()
