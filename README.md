# Forward Error Correction (FEC) for 5G URLLC Networks

> **B.Tech Data Communications — Semester Research Mini-Project**
>
> Packet-level FEC to improve reliability and reduce retransmissions in 5G Ultra-Reliable Low-Latency Communication (URLLC) scenarios.

---

## 📌 Problem Statement

In 5G networks, retransmission mechanisms (ARQ/HARQ) introduce latency that is unacceptable for URLLC use cases like IoT, industrial automation, and real-time control. This project investigates whether **application-layer Forward Error Correction** can reduce packet loss *without* retransmission, improving both reliability and latency.

## 🎯 Approach

We implement a **packet-level erasure code** using Galois Field GF(256) arithmetic (Cauchy matrix construction). The sender adds redundant parity packets to each block; the receiver uses them to **recover lost packets** without requesting retransmission.

```
┌──────────┐    ┌───────────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐
│  Traffic  │───▶│    FEC    │───▶│ Channel  │───▶│    FEC    │───▶│ Receiver │
│ Generator │    │  Encoder  │    │  (loss)  │    │  Decoder  │    │          │
└──────────┘    └───────────┘    └──────────┘    └───────────┘    └──────────┘
  4 data pkts   4 data + 4 par    some lost       recovers up      original 4
                 = 8 packets      (up to 4)       to 4 losses      data pkts
```

### Key Parameters

| Parameter | Value | Meaning |
|-----------|-------|---------|
| N (data packets) | 4 | Original data packets per block |
| K (parity packets) | 4 | Redundant packets added |
| Code Rate | 0.5 (50%) | Ratio of useful data to total |
| Max Recovery | 4 packets | Can tolerate up to 4 losses per block of 8 |

---

## 📁 Project Structure

```
fec_project/
│
├── config/                          # Configuration
│   ├── __init__.py
│   ├── fec_config.py                # FEC parameters (N=4, K=4)
│   └── network_config.py           # Network settings (IPs, ports)
│
├── core/                            # ★ FEC Algorithm (GF(256) Erasure Coding)
│   ├── __init__.py
│   ├── galois.py                    # GF(256) field arithmetic
│   ├── fec_encoder.py               # Cauchy matrix encoder
│   └── fec_decoder.py               # Gaussian elimination decoder
│
├── network/                         # Network Simulation
│   ├── __init__.py
│   ├── traffic_generator.py         # UDP traffic generation
│   ├── traffic_receiver.py          # UDP traffic reception
│   ├── packet_loss_simulator.py     # Random + burst loss models
│   └── channel_model.py            # 5G latency simulation
│
├── integration/                     # End-to-End UDP Integration
│   ├── __init__.py
│   ├── fec_sender.py                # FEC encode + UDP send
│   └── fec_receiver.py              # UDP receive + FEC decode
│
├── experiments/                     # Experiment Automation
│   ├── __init__.py
│   └── experiment_runner.py         # FEC vs no-FEC comparison engine
│
├── analysis/                        # Results & Visualization
│   ├── __init__.py
│   ├── metrics_collector.py         # Summary table formatting
│   └── visualizer.py               # Academic matplotlib graphs
│
├── data/results/                    # Generated Output
│   ├── experiment_results.json      # Raw experiment data
│   ├── plr_comparison.png           # Graph: Packet Loss Rate
│   ├── recovery_rate.png            # Graph: Block Recovery Rate
│   ├── throughput_comparison.png    # Graph: Throughput Trade-off
│   └── latency_cdf.png             # Graph: Latency Distribution
│
├── test_fec_basic.py                # FEC unit test (8 scenarios)
├── test_fec_integration.py          # End-to-end sender/receiver test
├── test_traffic.py                  # Basic UDP traffic test
├── run_experiments.py               # ★ Main entry point
└── README.md                       # This file
```

---

## 🔧 Module Details

### 1. `core/galois.py` — GF(256) Field Arithmetic

**Purpose:** Provides the mathematical foundation for erasure coding.

All FEC operations happen in GF(2⁸), a finite field with 256 elements where:
- **Addition** = XOR (no carry)
- **Multiplication** uses pre-computed log/exp lookup tables for O(1) speed
- **Every non-zero element has a multiplicative inverse**

| Function | Description |
|----------|-------------|
| `gf_add(a, b)` | Addition in GF(256) = XOR |
| `gf_mul(a, b)` | Multiplication via log/exp tables |
| `gf_div(a, b)` | Division: `a × b⁻¹` |
| `gf_inv(a)` | Multiplicative inverse |
| `gf_matrix_invert(M)` | Gauss-Jordan elimination over GF(256) |

Uses the **irreducible polynomial** `x⁸ + x⁴ + x³ + x² + 1` (0x11D), same as AES.

---

### 2. `core/fec_encoder.py` — Cauchy Matrix Encoder

**Purpose:** Encodes a block of 4 data packets into 8 packets (4 data + 4 parity).

**How it works:**
1. Constructs a **Cauchy encoding matrix** `C[j][i] = 1/(x_j ⊕ y_i)` in GF(256)
2. Each parity packet is a unique linear combination: `parity_j[pos] = Σ C[j][i] × data_i[pos]`
3. The Cauchy construction **guarantees** that any 4×4 sub-matrix is invertible — this is why we can recover from any pattern of up to 4 losses

**Key property:** Unlike simple XOR (where all parity packets are identical), every parity packet here is **different**, enabling multi-packet recovery.

```python
encoder = FECEncoder(n_data_packets=4, n_parity_packets=4)
encoded = encoder.encode_block([pkt0, pkt1, pkt2, pkt3])
# encoded = [pkt0, pkt1, pkt2, pkt3, parity0, parity1, parity2, parity3]
#            ← data (unchanged) →     ← 4 unique parity packets →
```

---

### 3. `core/fec_decoder.py` — Gaussian Elimination Decoder

**Purpose:** Recovers original data packets from any subset of ≥4 received packets.

**How it works:**
1. Identifies which packets were received and which are missing
2. Selects the encoding matrix rows corresponding to received packets → forms sub-matrix `S`
3. **Inverts `S` over GF(256)** using Gauss-Jordan elimination
4. Multiplies the inverse by the received bytes to recover all original data

**Fast path:** If all 4 data packets arrive intact, skips the math entirely.

```python
decoder = FECDecoder(n_data_packets=4, n_parity_packets=4)
received = [None, None, None, None, par0, par1, par2, par3]  # ALL data lost!
recovered, success = decoder.decode_block(received)
# success = True — recovers all 4 data packets from parity alone!
```

---

### 4. `network/packet_loss_simulator.py` — Loss Models

**Purpose:** Simulates realistic packet loss patterns to test FEC under various conditions.

#### RandomLossSimulator (Bernoulli)
Each packet dropped independently with probability `p`. Simple but useful baseline.

#### BurstLossSimulator (Gilbert-Elliott)
Two-state Markov chain modeling real wireless fading:
- **GOOD state** → packets delivered (low loss)
- **BAD state** → packets dropped (high loss, burst errors)
- Transitions: `GOOD→BAD` with probability `p_gb`, `BAD→GOOD` with probability `p_bg`
- Average burst length ≈ `1/p_bg`

```
GOOD ──(p_gb)──▶ BAD
  ▲                │
  └──(p_bg)────────┘
```

---

### 5. `network/channel_model.py` — 5G Latency Simulation

**Purpose:** Models user-plane latency characteristics of 5G links.

Each packet gets a delay = `base_delay + jitter`, where jitter is drawn from a normal or uniform distribution. Computes percentile statistics (P50, P95, P99).

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `base_delay_ms` | 2.0 | Fixed propagation delay |
| `jitter_std_ms` | 1.0 | Jitter standard deviation |

---

### 6. `network/traffic_generator.py` & `traffic_receiver.py` — UDP Traffic

**Purpose:** Generate and receive UDP traffic for testing.

- `TrafficGenerator`: sends numbered packets with configurable size and rate
- `TrafficReceiver`: listens on a UDP socket, counts received packets

---

### 7. `integration/fec_sender.py` — FEC + UDP Sender

**Purpose:** Combines FEC encoding with network transmission.

1. Buffers incoming data packets until a full block (4 packets) is ready
2. Calls the FEC encoder to produce 8 encoded packets
3. Adds a binary header to each: `block_id(4B) | packet_idx(2B) | total(2B)`
4. Sends all 8 packets via UDP

---

### 8. `integration/fec_receiver.py` — FEC + UDP Receiver

**Purpose:** Receives UDP packets and applies FEC decoding.

1. Receives packets and parses the FEC header
2. Groups packets by `block_id` using a dictionary
3. When ≥4 packets from a block arrive, attempts FEC decoding
4. Returns recovered data packets

---

### 9. `experiments/experiment_runner.py` — Experiment Engine

**Purpose:** Automates FEC vs no-FEC comparison experiments.

For each loss rate (0% to 50%), runs multiple trials:

| Scenario | What happens |
|----------|-------------|
| **No FEC** | Send `N` packets through loss simulator → count survivors |
| **With FEC** | Encode `N→N+K`, apply loss, decode → count recovered data |

Collects per-trial metrics:
- Packet Loss Rate (before and after FEC)
- Block recovery success rate
- Effective throughput (accounts for FEC overhead)
- Latency statistics

---

### 10. `analysis/visualizer.py` — Academic Graphs

**Purpose:** Generates 4 publication-ready matplotlib plots.

| Graph | What it shows |
|-------|--------------|
| **PLR Comparison** | Channel loss vs effective PLR for random & burst loss |
| **Recovery Rate** | Block recovery success rate with 5G URLLC/eMBB target lines |
| **Throughput Trade-off** | Effective throughput showing FEC overhead cost vs recovery benefit |
| **Latency CDF** | Cumulative distribution of packet delivery latency |

---

## 🚀 How to Run

### Prerequisites
```bash
pip install matplotlib numpy
```

### Run FEC Unit Test
```bash
py -3.13 test_fec_basic.py
```
Tests 8 loss scenarios (0 to 5 losses). Expected: 7 pass, 1 correctly fails.

### Run Full Experiments
```bash
py -3.13 run_experiments.py
```
Runs 90 experiments (9 loss rates × 2 loss models × 5 trials), prints summary table, generates 4 PNG graphs in `data/results/`.

### Run Integration Test
```bash
py -3.13 test_fec_integration.py
```
Tests end-to-end sender→receiver via UDP on localhost.

---

## 📊 Results Summary

### FEC Unit Test — ALL PASSED ✓

| Scenario | Lost Packets | Result |
|----------|:---:|:---:|
| No loss | 0/8 | ✓ Recovered |
| 1 data packet lost | 1/8 | ✓ Recovered |
| 2 packets lost (data + parity) | 2/8 | ✓ Recovered |
| 3 packets lost | 3/8 | ✓ Recovered |
| 3 data packets lost | 3/8 | ✓ Recovered |
| **ALL 4 data packets lost** | **4/8** | **✓ Recovered** |
| 4 mixed packets lost | 4/8 | ✓ Recovered |
| 5 packets lost (exceeds limit) | 5/8 | ✗ Failed (expected) |

### Experiment Results — Random Loss

| Channel Loss | No-FEC PLR | FEC PLR | Improvement | Recovery Rate |
|:---:|:---:|:---:|:---:|:---:|
| 5% | 5.6% | **0.0%** | 5.6% | 100% |
| 10% | 11.2% | **0.0%** | 11.2% | 100% |
| 15% | 14.6% | **0.0%** | 14.6% | 100% |
| 20% | 19.9% | **0.3%** | 19.6% | 99.6% |
| 25% | 23.3% | **3.0%** | 20.3% | 96.0% |
| 30% | 28.0% | **3.8%** | 24.2% | 93.6% |
| 40% | 38.9% | **12.1%** | 26.8% | 82.0% |
| 50% | 49.7% | **23.4%** | 26.3% | 64.8% |

**Key Takeaway:** FEC **eliminates** packet loss completely up to 15% channel loss, and cuts loss by 50-86% even at higher rates.

---

## ✅ Progress Tracker

### Completed
- [x] FEC encoder with GF(256) Cauchy matrix (multi-packet recovery)
- [x] FEC decoder with Gaussian elimination (recovers up to 4 lost packets)
- [x] GF(256) arithmetic library (pure Python, no dependencies)
- [x] UDP traffic generator and receiver
- [x] FEC sender/receiver integration (FEC + UDP)
- [x] Packet loss simulator (random Bernoulli + burst Gilbert-Elliott)
- [x] 5G channel latency model (base delay + jitter)
- [x] Experiment framework (FEC vs no-FEC baseline comparison)
- [x] Metrics collection and summary tables
- [x] Visualization (4 academic-quality matplotlib graphs)
- [x] Unit tests and integration tests

### Possible Future Work
- [ ] Open5GS integration (route traffic through real 5G core)
- [ ] Compare different FEC codes (LDPC, Raptor, Fountain)
- [ ] Adaptive code rate (adjust parity based on channel quality)
- [ ] Real-time visualization dashboard
- [ ] Burst loss interleaving optimization

---

## 🛠 Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.13 |
| Networking | UDP sockets (`socket` module) |
| FEC Math | Custom GF(256) (pure Python) |
| Concurrency | `threading` for sender/receiver |
| Visualization | `matplotlib`, `numpy` |
| Data Format | JSON for experiment results |

---

## 📚 References

- **Forward Error Correction** — Proactive packet recovery without retransmission
- **Reed-Solomon Codes** — Basis for our GF(256) erasure coding approach
- **Cauchy Matrices** — Every square sub-matrix is invertible over finite fields
- **Gilbert-Elliott Model** — Standard two-state channel model for wireless burst errors
- **5G URLLC** — 3GPP target: 99.999% reliability, <1ms latency
- **ARQ/HARQ** — Retransmission-based reliability (what FEC aims to reduce/replace)
