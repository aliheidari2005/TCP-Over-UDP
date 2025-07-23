def _retransmit_loop(self):
    while self.running:
        with self.lock:
            for seq, (pkt, ts) in list(self.buffer.items()):
                now = time.monotonic()
                # ✅ Send if never sent (ts == 0) or timeout expired
                if ts == 0 or now - ts > self.timeout + 1:
                    if ts == 0:
                        print(f"[SEND] Sending new seq {seq}")
                    else:
                        print(
                            f"[RETRANSMIT] Resending seq {seq}, {now - ts} > {self.timeout + 1}")

                    self.buffer[seq] = (pkt, now)  # Update timestamp
                    try:
                        if len(pkt.payload) > 0:
                            print(pkt.payload)
                        self.socket.send_packet(pkt)
                    except OSError:
                        pass
        time.sleep(0.1)


# --------------------------------------------------------------------------------------


def send(self, data: bytes):
    chunks = [data[i:i + Packet.MSS] for i in range(0, len(data), Packet.MSS)]
    for chunk in chunks:
        while True:
            with self.lock:
                if self.next_seq < self.send_base + self.window_size:
                    break
            time.sleep(0.01)

        pkt = Packet(
            src_port=self.socket.local_address[1],
            dest_port=self.client_addr[1],
            seq_num=self.next_seq,
            ack_num=self.recv_ack,
            flags=ACK,
            payload=chunk
        )

        with self.lock:
            print(
                f"[SEND] Buffering: seq={self.next_seq}, ack={self.recv_ack}")
            # Timestamp = 0 → not sent yet
            self.buffer[self.next_seq] = (pkt, 0)
            self.next_seq += len(chunk)


def _sender_loop(self):
    while self.running:
        with self.lock:
            for seq, (pkt, ts) in list(self.buffer.items()):
                if seq < self.send_base:
                    continue  # Already ACKed
                if ts == 0:
                    print(f"[SENDER] Sending buffered packet: seq={seq}")
                    self.socket.send_packet(pkt)
                    self.buffer[seq] = (pkt, time.monotonic())
        time.sleep(0.05)


def _retransmit_loop(self):
    while self.running:
        now = time.monotonic()
        with self.lock:
            for seq, (pkt, ts) in list(self.buffer.items()):
                if seq < self.send_base or ts == 0:
                    continue  # Already ACKed or not yet sent
                elapsed = now - ts
                if elapsed > self.timeout:
                    print(f"[RETRANSMIT] Timeout: resending seq={seq}")
                    self.buffer[seq] = (pkt, time.monotonic())
                    try:
                        self.socket.send_packet(pkt)
                    except OSError:
                        pass
        time.sleep(0.1)


# --------------------------------------------------------------------------------------


def send(self, data: bytes):
    chunks = [data[i:i + Packet.MSS] for i in range(0, len(data), Packet.MSS)]
    for chunk in chunks:
        while True:
            with self.lock:
                # ✅ چک کردن فضای کافی در پنجره براساس بایت (نه تعداد پکت)
                window_limit = self.send_base + self.window_size * Packet.MSS
                if self.next_seq + len(chunk) <= window_limit:
                    break
            time.sleep(0.01)

        print(
            f"[SEND] Creating packet: seq={self.next_seq}, ack={self.recv_ack}, chunk_len={len(chunk)}"
        )

        pkt = Packet(
            src_port=self.socket.local_address[1],
            dest_port=self.client_addr[1],
            seq_num=self.next_seq,
            ack_num=self.recv_ack,
            flags=ACK,
            payload=chunk
        )

        with self.lock:
            print(
                f"[SEND] Buffering: seq={self.next_seq}, ack={self.recv_ack}")
            self.buffer[self.next_seq] = (pkt, 0)  # not sent yet
            self.next_seq += len(chunk)


def _sender_loop(self):
    while self.running:
        with self.lock:
            for seq, entry in list(self.buffer.items()):
                if seq < self.send_base:
                    continue  # already ACKed
                if not entry["sent_once"]:
                    print(f"[SENDER] Sending for first time: seq={seq}")
                    self.socket.send_packet(entry["packet"])
                    entry["timestamp"] = time.monotonic()
                    entry["sent_once"] = True
        time.sleep(0.05)


def _retransmit_loop(self):
    while self.running:
        now = time.monotonic()
        with self.lock:
            items = list(self.buffer.items())

        for seq, (pkt, ts) in items:
            with self.lock:
                window_limit = self.send_base + self.window_size * Packet.MSS
                if seq >= window_limit or seq < self.send_base or seq not in self.buffer:
                    continue

                elapsed = now - ts if ts != 0 else float('inf')

                if ts == 0 or elapsed > self.timeout:
                    msg = "Sending new" if ts == 0 else f"Resending, {elapsed:.3f} > {self.timeout}"
                    print(f"[RETRANSMIT] {msg}: seq {seq}")
                    self.buffer[seq] = (pkt, time.monotonic())

            try:
                self.socket.send_packet(pkt)
            except OSError:
                pass

        time.sleep(0.1)
