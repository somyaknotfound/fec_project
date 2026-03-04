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

### ⚡ Set Up Kernel-Level Packet Loss (CRITICAL STEP)
```
Step 33 ▸  In Terminal 2, enable 30% kernel-level packet loss:
              sudo tc qdisc add dev lo root netem loss 30%

           This makes the Linux KERNEL drop 30% of loopback packets.
           Wireshark will see the drops because they happen BEFORE capture!

Step 34 ▸  Verify it's active:
              tc qdisc show dev lo
           You should see: "qdisc netem ... loss 30%"
```

> ⚠️ **Why this matters:** Without this step, packet loss is simulated inside the
> receiver app, and Wireshark would show ALL 16 packets arriving. With `tc netem`,
> the kernel itself drops packets, so Wireshark genuinely shows missing packets.

### Wireshark Setup
```
Step 35 ▸  In Wireshark: File → Close (discard previous)
Step 36 ▸  Change the filter bar to:
              udp.port == 5002
Step 37 ▸  Start a NEW capture on "Loopback: lo"
```

### Run the Demo
```
Step 38 ▸  In Terminal 1, run:
              sudo python3 demo/demo3_live_recovery.py

           (Must use sudo so the script can detect netem is active)

Step 39 ▸  Script confirms: "✓ Kernel-level loss active (tc netem)"
Step 40 ▸  Press Enter when prompted
```

### What to Watch
```
Step 41 ▸  TERMINAL: Sender sends ALL 16 packets

              [SENDER]   → Sent      block=0 idx=0 (DATA)
              [SENDER]   → Sent      block=0 idx=1 (DATA)
              ...

Step 42 ▸  TERMINAL: Receiver only gets SOME packets (kernel drops the rest!)

              [RECEIVER] ✓ Received  block=0 idx=0 (DATA)
              [RECEIVER] ✓ Received  block=0 idx=2 (DATA)    ← idx=1 MISSING!
              [RECEIVER] ✓ Received  block=0 idx=3 (DATA)
              ...

           NOTE: There are NO red ✗ lines — dropped packets simply NEVER
           arrive at the receiver. This is REAL network-level loss!

Step 43 ▸  WIRESHARK: Count the packets — you'll see ~11 instead of 16!
              → These are the packets that survived kernel-level drops
              → The missing ones were dropped by tc netem before capture
```

### After Transmission Finishes
```
Step 44 ▸  TERMINAL shows "FEC DECODING PHASE":

              Block 0: received 5/8 (lost 1 data + 2 parity)
                       Missing indices: [1, 5, 7]
                       ✓ DECODED SUCCESSFULLY

              Block 1: received 6/8 (lost 2 data + 0 parity)
                       Missing indices: [0, 3]
                       ✓ DECODED SUCCESSFULLY

Step 45 ▸  FINAL STATISTICS:
              Packets sent:       16
              Packets received:   ~11
              Packets lost:       ~5        ← REAL kernel drops!
              Actual loss rate:   ~31%
              Loss method:        Kernel-level (tc netem)

              Blocks decoded:     2/2
              ★ SUCCESS RATE:     100% ★

           Key line:  "Wireshark shows only ~11 packets!"
```

### Wireshark Verification (THE PROOF)
```
Step 46 ▸  STOP the Wireshark capture (red square)

Step 47 ▸  COUNT the packets in the packet list:
              → You'll see approximately 11 packets, NOT 16
              → The missing 5 were genuinely lost by the kernel!

Step 48 ▸  Statistics → Conversations → UDP tab
              → Shows exact packet count confirming the loss

Step 49 ▸  COMPARE: Demo 2 had 8/8 packets (no loss)
                     Demo 3 has ~11/16 packets (30% kernel loss)
              → Yet the decoder STILL recovered ALL original data!
```

### 🧹 CLEAN UP (Don't Forget!)
```
Step 50 ▸  In Terminal 2, REMOVE the packet loss rule:
              sudo tc qdisc del dev lo root

Step 51 ▸  Verify it's removed:
              tc qdisc show dev lo
           Should show: "qdisc noqueue" or "qdisc fq_codel" (default)
```

> ⚠️ **IMPORTANT:** Always remove the netem rule after the demo!
> Otherwise ALL loopback traffic will have 30% loss — breaking DNS,
> database connections, and other localhost services.

> 💬 **Say:** *"Look at Wireshark — it captured only 11 of 16 packets. The missing 5 were dropped by the Linux kernel's traffic control before they even reached the receiver. This is REAL packet loss, not simulated. Yet the FEC decoder used Gaussian elimination over GF(256) to reconstruct ALL original data from just the surviving packets. No retransmission was needed. This is exactly the property we need for 5G URLLC."*

---

## WRAP-UP (2 min)

```
Step 52 ▸  Close Wireshark
Step 53 ▸  (Optional) Show the experiment graphs:
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
| 3. Recovery ⭐ | `sudo python3 demo/demo3_live_recovery.py` | `udp.port == 5002` | 5002 | ~20s |

### Network Loss Setup (Demo 3 Only)
```
BEFORE Demo 3:   sudo tc qdisc add dev lo root netem loss 30%
AFTER Demo 3:    sudo tc qdisc del dev lo root
```

### Between Each Demo
1. **STOP** the Wireshark capture (red square ⬛)
2. **Close** the capture (File → Close, don't save)
3. **Change** the filter to the next port
4. **Start** a new capture (blue shark fin ▶)
5. **Then** run the next demo script
