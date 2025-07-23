from server_socket import ServerSocket
import time


def main():

    while True:
        server = ServerSocket()
        server.bind(('127.0.0.1', 12000))
        server.listen(backlog=1)

        print("[SERVER] Waiting for client...")
        conn = server.accept()
        print("[SERVER] Client connected.")

        # Communicate
        while True:
            if not server.connectionqueue:
                print("connection end")
                break

            message = input()
            if message == "exit":
                conn.close()
                break
            elif len(message) > 0:
                print(f"[SERVER] Sending: {message}")
                conn.send(message.encode())

        print(
            "enter close for close the server or enter connection for make a new connection")
        message2 = input()
        if message2 == "exit":
            break
        elif message2 == "connection":
            continue

        server.close()

    # response = b"Hello from server"
    # print(f"[CLIENT] Sending: {response}")
    # conn.send(response)

    # time.sleep(5)
    # Graceful connection close

    # # Close listener socket (no new SYNs will be accepted)
    # server.close()


if __name__ == "__main__":
    main()
