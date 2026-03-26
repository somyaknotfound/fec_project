# FEC Wireshark Demo — Quick Start

**B.Tech Mini-Project — Data Communications & Networks**  
**Students:** Shivam Kumar (241CS255), Somyak Priyadarshi Mohanta (241CS257)  
**Institution:** NITK Surathkal, Department of Computer Science & Engineering  
**Guide:** BR Chandravarkar, NITK Surathkal  
**Course:** CS255 - Data Communications

## Prerequisites
- Python 3.13+
- Wireshark installed (for packet visualization)
- `matplotlib`, `numpy` (already installed from main project)
- `scapy` (optional, for PCAP analysis: `pip install scapy`)

## Three Demos (Run in Order)

### Demo 1: Baseline (No FEC)
```bash
# Shows that packet loss is permanent without FEC
python3 demo1_no_fec.py
```
**Wireshark filter:** `udp.port == 5000`  
**Duration:** ~10 seconds  
**Key point:** Lost packets = permanently lost data

---

### Demo 2: FEC Packet Structure
```bash
# Shows FEC encoding and header format
python3 demo2_with_fec.py
```
**Wireshark filter:** `udp.port == 5001`  
**Duration:** ~8 seconds  
**Key point:** Click any packet → Data section → first 8 bytes = FEC header

---

### Demo 3: Live Recovery (⭐ Main Demo)
```bash
# Live packet loss with 100% recovery
python3 demo3_live_recovery.py
```
**Wireshark filter:** `udp.port == 5002`  
**Duration:** ~20 seconds  
**Key point:** ~30% packets dropped, but ALL data recovered via GF(256) FEC

---

## Optional: Automated Capture
```bash
# Check if tshark is available
python3 capture_helper.py check

# Start capture (requires sudo on Linux)
sudo python3 capture_helper.py start --port 5002 --name demo3
# Run demo in another terminal, then Ctrl+C to stop

# Analyze captured PCAP
python3 analyze_pcap.py ../data/captures/capture_demo3_*.pcap --port 5002
```

## Wireshark Setup (Manual)
1. Open Wireshark → Select **Loopback** (or `lo`) interface
2. Set display filter (e.g., `udp.port == 5002`)
3. Click **Start Capture** (blue shark fin)
4. Run a demo script
5. Watch packets appear in real-time
6. Click **Stop** when demo finishes
7. Click any packet to inspect FEC headers

## Ports Used
| Demo | Port | Purpose |
|------|------|---------|
| Demo 1 | 5000 | Baseline (no FEC) |
| Demo 2 | 5001 | FEC structure |
| Demo 3 | 5002 | Live recovery |
