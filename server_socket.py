from tcp_socket import TCPSocket
from connection import Connection
from packet import Packet, SYN, ACK, FIN
import random
import threading
import queue
import time
import socket as so
import threading
import time


class ServerSocket(TCPSocket):

    def __init__(self):
        super().__init__()
        self.listen_queue = queue.Queue()
        self.backlog = 1
        self.active_connections = {}  # (client_ip, client_port) → Connection
        self.listener_thread = None
        self.running = False
        self.connectionqueue = False

    def listen(self, backlog=1):
        self.backlog = backlog
        self.listen_queue = queue.Queue(maxsize=backlog)
        self.running = True
        print(f"[LISTEN] Listening with backlog size {backlog}")

        self.listener_thread = threading.Thread(
            target=self._listen_for_connections, daemon=True)
        self.listener_thread.start()

    def _listen_for_connections(self):
        while self.running:
            try:
                pkt, addr = self.receive_packet()
            except OSError as e:
                if not self.running:
                    break
                print(f"[RECEIVE PACKET] OSError: {e}")
                break

            if not pkt:
                continue

            conn_key = (addr[0], addr[1])

            if conn_key in self.active_connections:
                print("conn_key in active_connections")
                continue

            if pkt.flags & SYN:
                print(f"[HANDSHAKE] Received SYN from {addr}")

                if self.listen_queue.full():
                    print("[HANDSHAKE] Queue full. Ignoring new SYN.")
                    continue

                server_seq = random.randint(1000, 5000)

                syn_ack = Packet(
                    src_port=pkt.dest_port,
                    dest_port=pkt.src_port,
                    seq_num=server_seq,
                    ack_num=pkt.seq_num + 1,
                    flags=SYN | ACK
                )
                print("[Send] SYN_ACK from [Server] to [Client]:")
                self.remote_address = addr
                self.send_packet(syn_ack)

                old_timeout = self.udp_socket.gettimeout()
                self.udp_socket.settimeout(2.0)

                ack_received = False
                try:
                    for _ in range(5):
                        try:
                            pkt2, addr2 = self.receive_packet()
                        except so.timeout:
                            print("[HANDSHAKE] Timeout waiting for ACK.")
                            continue

                        if not pkt2:
                            continue

                        if pkt2.flags & ACK and pkt2.ack_num == server_seq + 1:
                            self.connectionqueue = True
                            print(
                                f"[HANDSHAKE] Connection established with {addr2},{self.connectionqueue}")
                            conn = Connection(
                                socket=self,
                                client_addr=addr,
                                seq=server_seq + 1,
                                ack=pkt2.seq_num,
                            )
                            self.active_connections[conn_key] = conn
                            self.listen_queue.put(conn)
                            ack_received = True
                            break
                finally:
                    self.udp_socket.settimeout(old_timeout)

                if not ack_received:
                    print("[HANDSHAKE] Failed to complete handshake, sending RST")
                    rst = Packet(
                        src_port=pkt.dest_port,
                        dest_port=pkt.src_port,
                        seq_num=0,
                        ack_num=0,
                        flags=0x08
                    )
                    self.send_packet(rst)

                break

            else:
                # 🔹 Invalid or unknown packet — reply with RST
                print(f"[LISTEN] Unknown packet from {addr}, sending RST")
                rst = Packet(
                    src_port=pkt.dest_port,
                    dest_port=pkt.src_port,
                    seq_num=0,
                    ack_num=0,
                    flags=0x08  # RST flag
                )
                self.send_packet(rst)

    def accept(self):
        print("[ACCEPT] Waiting for complete connections in queue...")
        return self.listen_queue.get()

    def remove_connection(self, client_addr):

        if client_addr in self.active_connections:
            self.connectionqueue = False
            print(
                f"[remove_connection] Removing connection with {client_addr}, {self.connectionqueue}")
            if self.connectionqueue == False:
                print(self.connectionqueue)
            del self.active_connections[client_addr]

    def close(self):
        print("[SERVER SOCKET] Closing listener socket...")

        # Stop listening thread
        self.running = False
        time.sleep(0.3)

        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=1)

        try:
            self.udp_socket.close()
        except Exception as e:
            print(f"[SERVER SOCKET] Warning: error while closing socket: {e}")

        self.is_bound = False
        self.is_connected = False
        print("[SERVER SOCKET] Listener shut down.")
