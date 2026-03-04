# 🎯 Step-by-Step Demo Walkthrough

> Print this page. Follow each step in order. Estimated total time: **15 minutes**.

---

## BEFORE YOU BEGIN (2 min)

```
Step 1  ▸  Open TWO terminal windows side by side
Step 2  ▸  In both terminals, navigate to the project:
              cd ~/Desktop/fec_project/
Step 3  ▸  Open Wireshark:
              sudo wireshark
Step 4  ▸  In Wireshark, select the "Loopback: lo" interface
              (DO NOT click Start yet)
```

> ✅ You should now have: **Terminal 1** | **Terminal 2** | **Wireshark** open

---

## DEMO 1 — Baseline Without FEC (3 min)

### Wireshark Setup
```
Step 5  ▸  In Wireshark's filter bar at the top, type:
              udp.port == 5000
Step 6  ▸  Click the blue shark fin button (▶) to START capture
Step 7  ▸  Verify bottom bar says "Capturing from Loopback: lo"
```

### Run the Demo
```
Step 8  ▸  In Terminal 1, run:
              python3 demo/demo1_no_fec.py
Step 9  ▸  When it says "Press Enter to start", press Enter
Step 10 ▸  WATCH: Terminal shows packets being sent (green ✓)
Step 11 ▸  WATCH: Wireshark shows packets appearing in the list
Step 12 ▸  Wait for "DEMO 1 SUMMARY" to appear (~10 sec)
```

### What to Point Out
```
Step 13 ▸  In Wireshark, click on any packet in the list
Step 14 ▸  In the middle pane, expand "Data" under UDP
Step 15 ▸  You'll see "PACKET_00_NO_FEC" in the hex dump
              → This proves the payload is unprotected plain text
Step 16 ▸  Click the red square (⬛) to STOP the capture
```

> 💬 **Say:** *"These 10 packets have zero protection. If any packet is lost during transmission, that data is gone forever — the only option is retransmission, which adds latency."*

---

## DEMO 2 — FEC Packet Structure (3 min)

### Wireshark Setup
```
Step 17 ▸  In Wireshark: File → Close (discard previous capture)
Step 18 ▸  Change the filter bar to:
              udp.port == 5001
Step 19 ▸  Double-click "Loopback: lo" to start a NEW capture
```

### Run the Demo
```
Step 20 ▸  In Terminal 1, run:
              python3 demo/demo2_with_fec.py
Step 21 ▸  Press Enter when prompted
Step 22 ▸  WATCH: Terminal shows 4 DATA (green) + 4 PARITY (blue) packets
Step 23 ▸  WATCH: Wireshark shows 8 packets appearing
Step 24 ▸  Wait for "DEMO 2 SUMMARY" to appear (~8 sec)
```

### What to Point Out
```
Step 25 ▸  In Wireshark, click on packet #4 (index 3, last data packet)
Step 26 ▸  Expand "Data" in the middle pane
Step 27 ▸  SELECT the first 8 bytes in the hex dump (bottom pane)
Step 28 ▸  Read the hex values aloud:

              00 00 00 00   00 03   00 08
              └─Block ID─┘  └Idx─┘  └Total┘
              Block = 0     Idx = 3  Total = 8

Step 29 ▸  Now click packet #5 (index 4, first PARITY packet)
Step 30 ▸  Show that the header changes to:
              00 00 00 00   00 04   00 08
              (same block, index 4 = first parity)
Step 31 ▸  Note: payload is now computed GF(256) bytes (looks random)
Step 32 ▸  STOP the capture
```

> 💬 **Say:** *"Each packet now has an 8-byte FEC header. We sent 4 original data packets plus 4 parity packets computed using Galois Field GF(256) arithmetic. The key property: ANY 4 of these 8 packets can reconstruct all original data."*

---

## DEMO 3 — Live Recovery ⭐ (5 min)

> **This is the main event. Take your time.**

### Wireshark Setup
```
Step 33 ▸  In Wireshark: File → Close (discard previous)
Step 34 ▸  Change the filter bar to:
              udp.port == 5002
Step 35 ▸  Start a NEW capture on "Loopback: lo"
```

### Run the Demo
```
Step 36 ▸  In Terminal 1, run:
              python3 demo/demo3_live_recovery.py
Step 37 ▸  Press Enter when prompted
```

### What to Watch
```
Step 38 ▸  TERMINAL: You'll see interleaved SENDER and RECEIVER lines
              [SENDER]   → Sent      block=0 idx=0 (DATA)
              [RECEIVER] ✓ Received  block=0 idx=0 (DATA)
              [SENDER]   → Sent      block=0 idx=1 (DATA)
              [RECEIVER] ✗ DROPPED   block=0 idx=1 (DATA)  ← SIMULATED LOSS!
              ...

Step 39 ▸  Count the RED ✗ lines — these are dropped packets (~5 out of 16)

Step 40 ▸  WIRESHARK: Notice fewer packets than 16 appearing
              (because dropped packets never reach the receiver)
```

### After Transmission Finishes
```
Step 41 ▸  TERMINAL shows "FEC DECODING PHASE":
              Block 0: received 6/8 (lost 1 data + 1 parity)
                       ✓ DECODED SUCCESSFULLY
              Block 1: received 5/8 (lost 2 data + 1 parity)
                       ✓ DECODED SUCCESSFULLY

Step 42 ▸  TERMINAL shows final statistics:
              Packets dropped:    ~5
              Actual loss rate:   ~31%
              Blocks decoded:     2/2
              ★ SUCCESS RATE:     100% ★

Step 43 ▸  STOP the Wireshark capture
```

### Wireshark Verification
```
Step 44 ▸  In Wireshark menu: Statistics → Conversations → UDP tab
Step 45 ▸  Show the packet count — it will be LESS than 16
              → This proves packets were actually lost on the wire
Step 46 ▸  Close the Statistics window
```

> 💬 **Say:** *"Despite losing about 30% of packets — confirmed by Wireshark — the FEC decoder recovered ALL original data using Gaussian elimination over GF(256). No retransmission was needed. This is exactly the property we want for 5G URLLC: reliable delivery without the latency of retransmissions."*

---

## WRAP-UP (2 min)

```
Step 47 ▸  Close Wireshark
Step 48 ▸  (Optional) Show the experiment graphs:
              Open: data/results/plr_comparison.png
              Open: data/results/recovery_rate.png
```

> 💬 **Say:** *"We also ran 90 automated experiments across loss rates from 0-50%. The results show that FEC completely eliminates packet loss up to 15% channel loss, and reduces it by 50-86% even at higher rates. The graphs show both random and burst loss patterns, with 5G URLLC reliability targets marked for reference."*

---

## QUICK REFERENCE CARD

| Demo | Command | Wireshark Filter | Port | Duration |
|------|---------|-----------------|------|----------|
| 1. Baseline | `python3 demo/demo1_no_fec.py` | `udp.port == 5000` | 5000 | ~10s |
| 2. Structure | `python3 demo/demo2_with_fec.py` | `udp.port == 5001` | 5001 | ~8s |
| 3. Recovery ⭐ | `python3 demo/demo3_live_recovery.py` | `udp.port == 5002` | 5002 | ~20s |

### Between Each Demo
1. **STOP** the Wireshark capture (red square ⬛)
2. **Close** the capture (File → Close, don't save)
3. **Change** the filter to the next port
4. **Start** a new capture (blue shark fin ▶)
5. **Then** run the next demo script
