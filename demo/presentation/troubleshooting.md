# Troubleshooting Guide

## Common Issues & Fixes

### 1. Wireshark Won't Start
**Symptom:** "You don't have permission to capture on that device"

**Fix (Linux):**
```bash
sudo wireshark
# OR grant capture permissions permanently:
sudo usermod -aG wireshark $USER
# Then logout and login again
```

**Backup Plan:** Skip Wireshark, just run demo scripts and explain from terminal output. Say: *"Due to permissions on this machine, I'll demonstrate using terminal output. The packet-level behavior is the same."*

---

### 2. No Packets Visible in Wireshark
**Check these in order:**
1. ✅ Correct interface selected? (Use **Loopback** or **lo**, NOT eth0/wlan0)
2. ✅ Capture started? (Blue shark fin button, should show "Capturing...")
3. ✅ Correct filter? (`udp.port == 500X` — check the port number)
4. ✅ Demo script running? (Must run AFTER capture starts)

**Quick test:** Remove the filter temporarily to see if ANY packets appear.

---

### 3. Demo Script Crashes
**"ModuleNotFoundError: No module named 'core'"**

Fix: Run from the correct directory:
```bash
cd ~/Desktop/fec_project/
python3 demo/demo1_no_fec.py
# OR
cd ~/Desktop/fec_project/demo/
python3 demo1_no_fec.py
```

**"Address already in use"**

Fix: Another process is using the port. Wait 30 seconds or:
```bash
# Find and kill the process using the port
lsof -i :5002
kill <PID>
```

---

### 4. Port Conflict Between Demos
Each demo uses a different port (5000, 5001, 5002) to avoid conflicts.
If you get "Address already in use", wait 10 seconds between demos.

---

### 5. Demo 3 Shows 0% Recovery
This shouldn't happen with the default settings (30% loss, seed=42). If it does:
- The random seed ensures reproducible results
- Try running again — sometimes OS-level issues can interfere
- As a last resort, lower LOSS_RATE in the script to 0.2

---

### 6. Colors Don't Show in Terminal
Windows CMD doesn't support ANSI colors. Use:
- **Windows Terminal** (recommended)
- **VS Code terminal**
- **Git Bash**
- **WSL** (Windows Subsystem for Linux)

Or ignore — the demos still work, just without color highlighting.

---

## Emergency Backup Plan

If NOTHING works during the presentation:

1. **Show the pre-generated graphs** from `data/results/`:
   - `plr_comparison.png` — FEC vs no-FEC across loss rates
   - `recovery_rate.png` — 100% recovery up to 15% loss
   - `throughput_comparison.png` — overhead trade-off
   - `latency_cdf.png` — latency impact

2. **Show the test output** (screenshot or run):
   ```bash
   python3 test_fec_basic.py
   ```
   This test always works (no networking) and shows all 7 recovery scenarios passing.

3. **Show the experiment results table** from the last run.

4. **Say:** *"Due to a technical issue with the live environment, let me walk through the pre-recorded results. The live demo has been tested successfully on my development machine — here are the results..."*

## Pre-Demo Checklist

Run through this 5 minutes before presenting:

- [ ] Wireshark opens correctly
- [ ] Can capture on Loopback interface
- [ ] Terminal font size is large enough to read from distance
- [ ] Run `python3 demo1_no_fec.py` — completes without error
- [ ] Run `python3 demo3_live_recovery.py` — shows 100% recovery
- [ ] Have backup graphs ready (open in image viewer)
- [ ] This troubleshooting guide is printed or accessible
