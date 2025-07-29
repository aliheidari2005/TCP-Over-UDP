
# TCP over UDP – Custom Reliable Transport Protocol


## 🧠 Project Overview

This project implements a simplified yet robust version of the **TCP protocol over UDP**, using Python sockets. The goal is to simulate a reliable, congestion-aware, flow-controlled, connection-oriented communication protocol, built entirely from scratch using **only UDP** sockets — without relying on any existing TCP libraries.

The project is structured around clean, modular classes and adheres to real-world TCP concepts like 3-way handshake, sequence numbers, ACKs, sliding window, congestion control, and graceful termination.

---

## ✅ Implemented Features

### 🧱 Core Functionality

- 🔁 **3-Way Handshake** (SYN → SYN-ACK → ACK)
- 📦 **Reliable Data Transfer** (Sequence & ACK numbers)
- 🔃 **Sliding Window Protocol**
- 📉 **Congestion Control:**
  - `cwnd` (congestion window)
  - Slow start
  - Fast retransmit on triple duplicate ACKs
  - Timeout-based window shrink
- 📏 **Flow Control:**
  - `rwnd` (receiver window)
  - Zero-window probing
- 🧮 **RTT Estimation:**
  - Adaptive timeout based on sample RTT, α, β
- 🔐 **Packet-level Encryption (Caesar Cipher)**
  - Simple encryption using byte-wise Caesar shift with key = 10
- 🧵 **Multithreaded Architecture:**
  - Parallel receiver, sender, retransmission, timeout watchdog
- 🔚 **Connection Termination** via FIN and FIN-ACK
- ⏱️ **Idle Timeout Detection** (auto close inactive connections)
- 🔁 **Automatic Retransmissions** on timeout or loss

---

## 🗂 Project Structure

| File | Description |
|------|-------------|
| `packet.py` | Custom TCP-like packet class with header + payload (with Caesar encryption) |
| `tcp_socket.py` | Base socket with connect, send, receive, bind, and low-level packet I/O |
| `connection.py` | Implements reliable transfer: buffers, retransmission, RTT, congestion & flow control |
| `server_socket.py` | Server-side socket with connection queue, accept, and handshake manager |
| `client_test.py` | Client script to test the protocol interactively |
| `server_test.py` | Server script that listens and communicates interactively with clients |

---

## ⚙️ How to Run

### 🖥️ Server
```bash
python server_test.py
```

### 💻 Client
```bash
python client_test.py
```

> Use two separate terminals or machines for testing.

### Commands
- Type any message and press enter to send.
- Type `exit` to close the connection gracefully.

---

## 🧪 Tested Capabilities

- ✔️ Out-of-order packet buffering
- ✔️ Congestion window dynamics (`cwnd` visualization via logs)
- ✔️ Receiver window (`rwnd`) shrinking to 0 then reopening (flow control)
- ✔️ Packet loss simulation (intentional first-drop for test)
- ✔️ Timeout-based retransmission
- ✔️ Fast retransmit on duplicate ACKs
- ✔️ Idle timeout auto-close
- ✔️ Graceful shutdown with FIN/FIN-ACK

---

## 🧩 Advanced Features Implemented (Bonus Criteria)

| Feature | Implemented? | Description |
|--------|---------------|-------------|
| **Detailed Logging** | ✅ | All packet activity, ACKs, congestion control events |
| **RST on invalid packets** | ✅ | Sends RST in response to unknown or invalid connection attempts |
| **Separate Client/Server Program** | ✅ | Included `client_test.py` and `server_test.py` |
| **Encrypted Payload (Wireshark safe)** | ✅ | Caesar cipher with a key — packets are not raw text |
| **Zero Window Probing** | ✅ | Sends probe when receiver is full |
| **Connection Timeout Watchdog** | ✅ | Automatically closes inactive connections |
| **Dynamic Sliding Window = min(cwnd, rwnd)** | ✅ | Controls flow and congestion effectively |
| **RTT-based Timeout Calculation** | ✅ | Uses α = 0.125 and β = 0.25 |
| **Congestion Control (TCP-like)** | ✅ | Slow start, timeout shrink, fast retransmit |

---

## 📚 Learning Outcomes

Through this project, I deepened my understanding of:

- TCP's connection semantics and how they map to low-level socket programming
- Reliable data transfer techniques: sequence numbering, acknowledgment, buffering
- Congestion avoidance strategies and the importance of adaptive control
- Flow control and receiver-side feedback mechanisms
- How complex systems can be implemented with minimal primitives (UDP only)

---

## 📈 Future Work

- 🔄 Implement simultaneous connections using per-client thread pools
- 📁 Add support for file transmission
- 📊 Visualize cwnd/rwnd vs time using Matplotlib
- 🔬 Add selective acknowledgments (SACK)
- 🧪 Integrate full-scale unit and network testing tools

---


## 🏁 Final Notes

This project represents a full-stack approach to protocol design and network programming. It showcases practical knowledge in socket programming, protocol engineering, flow and congestion management, and system reliability.
