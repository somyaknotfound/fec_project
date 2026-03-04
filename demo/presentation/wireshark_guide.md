# Wireshark Analysis Guide

## Display Filters (Copy-Paste Ready)

### Per-Demo Filters
```
udp.port == 5000        Demo 1: Baseline (no FEC)
udp.port == 5001        Demo 2: FEC structure
udp.port == 5002        Demo 3: Live recovery
```

### All FEC Traffic
```
udp.port == 5000 || udp.port == 5001 || udp.port == 5002
```

### By Packet Size
```
udp.length > 1000       Only large packets (FEC data)
udp.length < 100        Only small packets (control)
```

---

## Reading FEC Headers in Wireshark

1. Click a captured packet
2. In the middle pane, expand **User Datagram Protocol**
3. Click **Data** (or **Payload**)
4. Bottom pane shows hex dump

### Header Byte Map
```
Offset:  00 01 02 03   04 05   06 07   08 09 ...
Content: [Block ID  ]  [Idx ]  [Tot ]  [Payload...]
Type:    uint32 BE     uint16  uint16  raw bytes
```

### Example Readings
```
Hex:     00 00 00 00   00 00   00 08
Decoded: Block=0       Idx=0   Total=8     → First data packet of block 0

Hex:     00 00 00 00   00 03   00 08
Decoded: Block=0       Idx=3   Total=8     → Last data packet of block 0

Hex:     00 00 00 00   00 04   00 08
Decoded: Block=0       Idx=4   Total=8     → First PARITY packet of block 0

Hex:     00 00 00 01   00 02   00 08
Decoded: Block=1       Idx=2   Total=8     → Third data packet of block 1
```

### Data vs Parity
- **Indices 0-3** = Data packets (payload shows readable text like "DATA_PKT_0")
- **Indices 4-7** = Parity packets (payload is computed GF(256) bytes — looks random)

---

## Useful Statistics Views

### Conversations (Most Important)
**Path:** Statistics → Conversations → UDP tab

Shows per-flow packet counts. In Demo 3, compare:
- Sender's count (16 packets) vs what was captured
- Confirms real packet loss occurred

### I/O Graph
**Path:** Statistics → I/O Graphs

Shows packet rate over time. You'll see:
- Regular transmission pattern (one packet per ~400ms)
- Block boundaries visible as slight pauses

### Flow Graph
**Path:** Statistics → Flow Graph → Show: Displayed packets

Visual timeline of packet exchanges between sender and receiver.

---

## What to Point Out to Professor

### In Demo 2 (Structure)
- All 8 packets have **same Block ID** (they're one FEC block)
- Packet Index increments 0→7
- **Click a data packet** (idx 0-3): payload starts with readable "DATA_PKT_X"
- **Click a parity packet** (idx 4-7): payload is computed bytes (looks like noise)
- Both have the **same size** — parity is same length as data

### In Demo 3 (Recovery)
- Not all 16 sent packets appear in capture (some dropped)
- Despite missing packets, terminal shows **100% block recovery**
- Statistics → Conversations confirms the count mismatch
- This proves FEC works at the actual network/packet level
