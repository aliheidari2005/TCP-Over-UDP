from packet import Packet, SYN, ACK, FIN, FIN_ACK, RST
import threading
import time
import socket as so
import threading
import time
import math

got_fin_from_remote = threading.Event()


class Connection:

    def __init__(self, socket, client_addr, seq, ack):

        # -------
        # در تابع __init__ کلاس Connection
        # ...
        self.persist_timer_on = False
        self.last_probe_time = 0
        # ...

        self.timeout_occurred = False

        # --- پارامترهای اصلی اتصال ---
        self.socket = socket
        host_ip = so.gethostbyname(client_addr[0])
        self.client_addr = (host_ip, client_addr[1])
        self.lock = threading.Lock()
        self.running = True

        # --- متغیرهای مربوط به شماره سریال‌ها ---
        self.send_base = seq
        self.next_seq = seq
        self.expected_seq = ack
        self.recv_ack = ack

        # --- بافرها ---
        self.buffer = {}      # بافر ارسال: بسته‌های ارسال شده که منتظر ACK هستند
        self.recv_buffer = {}  # بافر دریافت: بسته‌های دریافتی خارج از ترتیب

        # --- منطق داینامیک تایم‌اوت (RTT) ---
        self.estimated_rtt = 1.0
        self.dev_rtt = 0.5
        self.timeout = self.estimated_rtt + 4 * self.dev_rtt
        self.alpha = 0.125
        self.beta = 0.25
        self.is_first_rtt_sample = True

        # --- منطق کنترل جریان و ازدحام ---
        self.max_recv_buffer = 20 * 1024  # برای مثال: ۲۰ کیلوبایت
        self.cwnd = 5                     # پنجره ازدحام (Congestion Window)
        # مقدار اولیه پنجره گیرنده (Receive Window)
        self.rwnd = self.max_recv_buffer

        self.persist_timer_on = False
        self.last_probe_time = 0

        # --- متغیرهای دیگر ---
        self.duplicate_ack_count = {}
        self.fin_sent = False
        self.got_ack_for_fin = threading.Event()

        # --- راه‌اندازی Thread ها ---
        self.receiver_thread = threading.Thread(
            target=self._receiver_loop, daemon=True)
        self.sender_thread = threading.Thread(
            target=self._sender_loop, daemon=True)

        self.retransmit_thread = threading.Thread(
            target=self._retransmit_loop, daemon=True)

        self.receiver_thread.start()
        self.sender_thread.start()
        self.retransmit_thread.start()

        # -----
        self.last_activity_time = time.monotonic()
        self.idle_timeout = 30  # ثانیه (می‌تونی به دلخواه کمتر یا بیشتر کنی)
        self.idle_checker_thread = threading.Thread(
            target=self._check_idle_timeout, daemon=True)
        self.idle_checker_thread.start()
        # -----

    def send(self, data: bytes):
        chunks = [data[i:i + Packet.MSS]
                  for i in range(0, len(data), Packet.MSS)]
        for chunk in chunks:
            while True:
                with self.lock:
                    effective_window = min(self.cwnd * Packet.MSS, self.rwnd)

                    print(
                        f"[FLOW_CONTROL] rwnd={self.rwnd}, effective_window={effective_window}")

                    window_limit = self.send_base + effective_window
                    if self.next_seq + len(chunk) <= window_limit:
                        break
                time.sleep(0.01)

            # print(
            #     f"[SEND] Creating packet: seq={self.next_seq}, ack={self.recv_ack}, chunk_len={len(chunk)}")

            with self.lock:

                bytes_in_buffer = sum(len(d)
                                      for d in self.recv_buffer.values())
                available_space = self.max_recv_buffer - bytes_in_buffer

                pkt = Packet(
                    src_port=self.socket.local_address[1],
                    dest_port=self.client_addr[1],
                    seq_num=self.next_seq,
                    ack_num=self.recv_ack,
                    flags=ACK,
                    payload=chunk,
                    # <--- همیشه اندازه پنجره را ارسال کن
                    window_size=max(0, available_space)

                )

                print(
                    f"[SEND] Buffering: seq={self.next_seq}, ack={self.recv_ack}")
                self.buffer[self.next_seq] = {
                    "packet": pkt,
                    "timestamp": 0,           # not yet sent
                    "sent_once": False,        # hasn't been sent yet
                    "retransmitted": False
                }
                self.next_seq += len(chunk)

    def _sender_loop(self):
        while self.running:
            with self.lock:
                for seq, entry in list(self.buffer.items()):
                    if seq < self.send_base:
                        continue  # already acknowledged
                    if not entry["sent_once"]:
                        # for _ in range(2):
                        self.socket.send_packet(entry["packet"])
                        self.last_activity_time = time.monotonic()

                        # time.sleep(2.5)
                        entry["timestamp"] = time.monotonic()
                        entry["sent_once"] = True
                        print(
                            f"[SENDERLOOP:] Sent for first time: seq={seq}")
            time.sleep(0.1)
# چت دو

    # کد های اصلی
    def _retransmit_loop(self):
        while self.running:
            now = time.monotonic()

            items_to_check = []
            with self.lock:
                items_to_check = list(self.buffer.items())

            for seq, entry in items_to_check:
                ts = entry["timestamp"]
                elapsed = now - ts if ts != 0 else 0

                if ts != 0 and elapsed > self.timeout:
                    with self.lock:
                        if seq in self.buffer and seq >= self.send_base:
                            # --- منطق کنترل ازدحام: واکنش به تایم‌اوت ---
                            if not getattr(self, 'timeout_occurred', False):
                                self.cwnd = 1
                                self.timeout_occurred = True
                                print(
                                    f"[CWND] Timeout detected, cwnd reset to {self.cwnd}")
                            # -----------------------------------------

                            print(
                                f"[RETRANSMIT] Resending, {elapsed:.3f} > {self.timeout}: seq {seq}")
                            self.buffer[seq]["timestamp"] = time.monotonic()
                            self.buffer[seq]["retransmitted"] = True
                            self.last_activity_time = time.monotonic()
                            try:
                                self.socket.send_packet(
                                    self.buffer[seq]["packet"])
                            except OSError:
                                pass

            # ... (منطق Zero-Window Probe در اینجا قرار می‌گیرد) ...
            with self.lock:
                if self.persist_timer_on and self.rwnd == 0:
                    if now - self.last_probe_time > self.timeout:
                        print(
                            "[PROBE] Zero window detected. Sending probe packet...")
                        bytes_in_buffer = sum(len(d)
                                              for d in self.recv_buffer.values())
                        available_space = self.max_recv_buffer - bytes_in_buffer
                        probe_pkt = Packet(
                            src_port=self.socket.local_address[1], dest_port=self.client_addr[1],
                            seq_num=self.next_seq, ack_num=self.recv_ack,
                            flags=ACK, window_size=max(0, available_space)
                        )
                        try:
                            self.socket.send_packet(probe_pkt)
                            self.last_activity_time = time.monotonic()
                        except OSError:
                            pass
                        self.last_probe_time = now

            time.sleep(0.1)

    def handle_ack(self, ack_num):
        with self.lock:
            if self.rwnd == 0:
                if not self.persist_timer_on:
                    self.last_probe_time = time.monotonic()
                self.persist_timer_on = True
            else:
                self.persist_timer_on = False

            # --- بخش ۱: مدیریت ACK تکراری یا قدیمی ---
            if ack_num <= self.send_base:
                if ack_num == self.send_base and self.buffer:
                    self.duplicate_ack_count[ack_num] = self.duplicate_ack_count.get(
                        ack_num, 0) + 1
                    print(
                        f"[DUP-ACK] {ack_num} : {self.duplicate_ack_count.get(ack_num, 0)}")

                    if self.duplicate_ack_count.get(ack_num, 0) >= 3:
                        print(f"[FAST RETRANSMIT] Triggered for seq {ack_num}")
                        if ack_num in self.buffer:
                            # --- منطق کنترل ازدحام: Fast Recovery ---
                            self.cwnd = max(1, self.cwnd // 2)
                            print(
                                f"[CWND] Fast Retransmit, cwnd halved to {self.cwnd}")
                            # ------------------------------------

                            entry = self.buffer[ack_num]
                            entry["retransmitted"] = True
                            entry["timestamp"] = time.monotonic()
                            self.socket.send_packet(entry["packet"])
                            self.last_activity_time = time.monotonic()
                            self.duplicate_ack_count[ack_num] = 0
                return

            # --- بخش ۲: مدیریت ACK جدید ---
            else:  # <--- این else بسیار مهم است
                # با رسیدن ACK جدید، یعنی شبکه سالم است
                self.timeout_occurred = False

                # منطق کنترل ازدحام: Congestion Avoidance / Slow Start
                self.cwnd += 1
                print(
                    f"[CWND] New ACK received, cwnd increased to {self.cwnd}")

                # محاسبه RTT
                oldest_acked_seq = self.send_base
                if oldest_acked_seq in self.buffer:
                    entry = self.buffer[oldest_acked_seq]
                    if not entry.get("retransmitted", False):
                        sample_rtt = time.monotonic() - entry["timestamp"]
                        if self.is_first_rtt_sample:
                            self.estimated_rtt = sample_rtt
                            self.dev_rtt = sample_rtt / 2
                            self.is_first_rtt_sample = False
                        else:
                            self.dev_rtt = (
                                1 - self.beta) * self.dev_rtt + self.beta * abs(sample_rtt - self.estimated_rtt)
                            self.estimated_rtt = (
                                1 - self.alpha) * self.estimated_rtt + self.alpha * sample_rtt

                        self.timeout = self.estimated_rtt + 4 * self.dev_rtt
                        if self.timeout < 0.2:
                            self.timeout = 0.2
                        print(
                            f"[RTT] Sample for seq {oldest_acked_seq}={sample_rtt:.3f}, New Timeout={self.timeout:.3f}")

                # جلو بردن پنجره ارسال و پاک‌سازی بافر
                self.send_base = ack_num
                self.duplicate_ack_count.clear()
                keys_to_delete = [
                    seq for seq in self.buffer if seq < self.send_base]
                for seq in keys_to_delete:
                    try:
                        del self.buffer[seq]
                    except KeyError:
                        pass

                print(
                    f"[ACK] Handled new ACK {ack_num}, new send_base={self.send_base}")

    def _receiver_loop(self):
        while self.running:
            try:
                pkt, addr = self.socket.receive_packet()
            except OSError:
                break
            if not pkt or addr != self.client_addr:
                continue

            with self.lock:
                self.rwnd = pkt.window_size
                self.last_activity_time = time.monotonic()

            if len(pkt.payload) > 0:
                with self.lock:
                    seq = pkt.seq_num
                    if seq < self.expected_seq:
                        pass
                    elif seq >= self.expected_seq:
                        if seq not in self.recv_buffer:
                            self.recv_buffer[seq] = pkt.payload
                    while self.expected_seq in self.recv_buffer:
                        data = self.recv_buffer.pop(self.expected_seq)
                        self.expected_seq += len(data)
                        print(
                            f"[DELIVER] Accepting in-order data (len={len(data)})")

                with self.lock:
                    bytes_in_buffer = sum(len(d)
                                          for d in self.recv_buffer.values())
                    available_space = self.max_recv_buffer - bytes_in_buffer
                    ack_pkt = Packet(
                        src_port=self.socket.local_address[1],
                        dest_port=self.client_addr[1],
                        seq_num=self.next_seq,
                        ack_num=self.expected_seq,
                        flags=ACK,
                        window_size=max(0, available_space)
                    )
                    self.socket.send_packet(ack_pkt)
                    print(
                        f"[RECEIVER LOOP] Sent ACK={self.expected_seq} with Window={max(0, available_space)}")

            elif pkt.flags & ACK:
                print(self.fin_sent)
                if self.fin_sent and pkt.ack_num >= self.next_seq:
                    print("[RECEIVER LOOP] Received ACK for our FIN.")
                    self.got_ack_for_fin.set()
                    self.socket.remove_connection(self.client_addr)
                else:
                    self.handle_ack(pkt.ack_num)

            elif pkt.flags & FIN:
                print("[RECEIVER LOOP] FIN received, sending FIN_ACK.")
                with self.lock:
                    self.expected_seq = max(self.expected_seq, pkt.seq_num + 1)
                    bytes_in_buffer = sum(len(d)
                                          for d in self.recv_buffer.values())
                    available_space = self.max_recv_buffer - bytes_in_buffer
                    fin_ack_pkt = Packet(
                        src_port=self.socket.local_address[1],
                        dest_port=self.client_addr[1],
                        seq_num=self.next_seq,
                        ack_num=pkt.seq_num + 1,
                        flags=FIN_ACK,
                        window_size=max(0, available_space)
                    )
                    self.socket.send_packet(fin_ack_pkt)
                    got_fin_from_remote.set()
                    self.fin_sent = True

    def _check_idle_timeout(self):
        while self.running:
            time.sleep(5)
            if self.running and time.monotonic() - self.last_activity_time > self.idle_timeout:
                print(
                    f"[IDLE TIMEOUT] No activity for {self.idle_timeout}s, closing connection.")
                self.close()
                break

    def read(self):
        # --- اصلاح شد: خطای منطقی در pop ---
        with self.lock:
            if self.expected_seq in self.recv_buffer:
                data = self.recv_buffer.pop(self.expected_seq)
                self.expected_seq += len(data)
                return data
            return None

    def close(self):
        if not self.running:
            return
        print("[CLOSE] Attempting to close connection...")
        self.running = False  # 🔴 Tell threads to stop first

        fin_pkt = Packet(
            src_port=self.socket.local_address[1],
            dest_port=self.client_addr[1],
            seq_num=self.next_seq,
            ack_num=self.expected_seq,
            flags=FIN
        )
        self.socket.send_packet(fin_pkt)
        self.fin_sent = True
        self.next_seq += 1  # فقط بعد از ارسال FIN افزایش بده

        # ⏳ منتظر دریافت FIN یا FIN+ACK از طرف مقابل
        fin_or_fin_ack_received = got_fin_from_remote.wait(timeout=5)
        if not fin_or_fin_ack_received:
            print("[CLOSE] Warning: FIN or FIN|ACK from remote not received")
        else:
            print("[CLOSE] FIN or FIN|ACK received from remote")

        # 🎯 اگر دریافت شد، ACK نهایی را بفرست
        final_ack = Packet(
            src_port=self.socket.local_address[1],
            dest_port=self.client_addr[1],
            seq_num=self.next_seq,
            ack_num=self.expected_seq,
            flags=ACK
        )
        self.socket.send_packet(final_ack)
        print("[CLOSE] Sent final ACK")

        # 🛑 پایان کامل
        time.sleep(0.3)

        # Wait for threads
        self.receiver_thread.join(timeout=1)
        self.sender_thread.join(timeout=1)
        self.retransmit_thread.join(timeout=1)

        # Close the underlying socket
        try:
            self.socket.close()
        except OSError:
            pass

        print("[CLOSE] Connection closed gracefully.")
