# Professor Presentation Script

> Step-by-step guide for the live FEC demonstration.  
> **Total time: ~12 minutes** (3 demos + explanations)

---

## Before Starting (2 min setup)

1. Open **two terminal windows** side by side
2. Open **Wireshark** (sudo wireshark on Linux)
3. Navigate to `fec_project/demo/` in one terminal
4. Have this script printed or on a tablet

---

## Demo 1: The Problem (3 min)

### Setup
- Wireshark: Select **Loopback/lo** interface
- Display filter: `udp.port == 5000`
- Click **Start Capture**

### Run
```bash
python3 demo1_no_fec.py
```
Press Enter when prompted.

### What to Say

> "Let me first demonstrate the baseline problem. I'm sending 10 UDP packets over the network with NO protection."

*Point to terminal — packets appearing one by one*

> "Each packet contains sequentially numbered data: PACKET_00, PACKET_01, and so on."

*Point to Wireshark*

> "In Wireshark, you can see the packets arriving. Notice each one is a standard UDP datagram."

> "The key issue: if we were transmitting over a 5G radio channel and any packet was lost due to fading or interference, that data is gone permanently. The only option is to request retransmission — which adds latency."

> "For 5G URLLC applications that require sub-millisecond latency, retransmission is not acceptable. That's the problem we're solving."

**Stop capture.** Clear Wireshark.

---

## Demo 2: FEC Structure (3 min)

### Setup
- Display filter: `udp.port == 5001`
- Start new capture

### Run
```bash
python3 demo2_with_fec.py
```

### What to Say

> "Now I'll show how Forward Error Correction works at the packet level. I'm sending 4 data packets, but my FEC encoder adds 4 parity packets — 8 total."

*Point to terminal — shows DATA and PARITY labels*

> "The parity packets are computed using Galois Field GF(256) arithmetic with a Cauchy matrix construction. Each parity packet is a unique linear combination of the data."

*Point to Wireshark, click on a packet*

> "Let me show you the packet structure. Click on this packet... expand the UDP section... look at the data."

*Select first 8 bytes in hex dump*

> "The first 8 bytes are our custom FEC header:
> - Bytes 0-3: Block ID (which FEC block this belongs to)
> - Bytes 4-5: Packet Index (position within the block, 0-7)
> - Bytes 6-7: Total Packets (always 8 in our configuration)
> 
> After the header, you can see the payload — 'DATA_PKT_0' for data packets,
> or computed GF(256) bytes for parity packets."

> "The critical mathematical property: **any 4 of these 8 packets** are sufficient to recover all 4 original data packets. This is guaranteed by the Cauchy matrix construction."

**Stop capture.** Clear Wireshark.

---

## Demo 3: Live Recovery (4 min) ⭐

### Setup
- Display filter: `udp.port == 5002`
- Start new capture
- **This is the main event — take your time here**

### Run
```bash
python3 demo3_live_recovery.py
```

### What to Say

> "Now for the main demonstration. I'm sending 2 FEC blocks — that's 8 original data packets encoded into 16 transmitted packets. The receiver will randomly drop 30% of incoming packets to simulate channel loss."

*Press Enter. Watch terminal output.*

> "Watch the terminal carefully:
> - Green checkmarks ✓ mean the packet was received
> - Red crosses ✗ mean simulated packet loss
> 
> You can see packets being dropped randomly..."

*Wait for transmission to complete. Point to decoding phase.*

> "Now the decoder kicks in. For each block, it identifies the received packets, selects the corresponding rows from the encoding matrix, and inverts using Gaussian elimination over GF(256)."

*Point to final statistics*

> "Look at the results:
> - We lost approximately 30% of packets — about 5 out of 16
> - But the FEC decoder recovered **100%** of the original data
> - No retransmissions were needed
> 
> This is exactly the result you'd want for 5G URLLC: reliable delivery without the latency penalty of retransmission."

**Stop capture.**

> "In Wireshark, you can go to Statistics → Conversations → UDP tab to verify the packet counts. The sender sent 16 packets, but only about 11 arrived — confirming real packet loss occurred."

---

## Wrap-Up (2 min)

> "To summarize what we've demonstrated:
> 
> 1. **The Problem**: Without FEC, packet loss requires retransmission, adding latency
> 2. **The Solution**: Our GF(256) erasure code adds parity packets that enable recovery
> 3. **The Proof**: Live packet capture confirms the system works at the network level
> 
> Our automated experiments tested this across loss rates from 0-50%, with both random and burst loss patterns. The results show that FEC eliminates packet loss completely up to 15% channel loss, and reduces it by 50-86% at higher rates."

*Show the 4 graphs from data/results/ if time permits*

---

## Likely Professor Questions

**Q: Why not use standard Reed-Solomon libraries?**
> "We implemented from scratch using GF(256) arithmetic to demonstrate the mathematical principles. Our Cauchy matrix construction provides the same erasure correction capability. We chose this approach for educational transparency — every line of the math is visible in our code."

**Q: What's the overhead?**
> "Our (4,4) code has 100% overhead — we send double the packets. The code rate is 0.5. In practice, you'd tune this: a (4,2) code gives 50% overhead but recovers up to 2 losses. There's a direct trade-off between redundancy and recovery capability."

**Q: How does this compare to 5G HARQ?**
> "HARQ is a retransmission mechanism at the MAC layer with ~1ms round-trip. Our FEC works at the application layer and adds zero retransmission latency — recovery is instant at the receiver. In practice, both would work together: FEC reduces the need for HARQ retransmissions."

**Q: Could this work with real 5G traffic?**
> "Yes. Our system works with any UDP traffic. With Open5GS and UERANSIM, we could route through an actual 5G user plane. The FEC sits at the application layer, so it's transparent to the network — it just adds redundancy before transmission."

**Q: Why GF(256) specifically?**
> "GF(256) = GF(2^8). Each element maps to exactly one byte (0-255), which is the natural unit of data. Operations are fast using pre-computed log/exp tables. This is the same field used in AES encryption and QR codes."
