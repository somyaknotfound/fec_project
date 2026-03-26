"""
network/matlab_loss_reader.py
──────────────────────────────────────────────────────────────────────────
Reads MATLAB-generated 5G channel simulation CSV files and replays them
as packet loss vectors inside the Python FEC experiment framework.

Replaces RandomLossSimulator / BurstLossSimulator when channel_source='matlab'.

Usage:
    from network.matlab_loss_reader import MatlabLossReader

    reader = MatlabLossReader('data/matlab_channel/')
    reader.load()

    # Get a loss mask for one FEC block
    loss_mask = reader.get_block(model='random', loss_rate=0.20, trial=1, block=5)
    # Returns: [1, 0, 1, 1, 1, 1, 0, 1]  (1=received, 0=lost)

    # Apply to encoded packets (same API as existing simulators)
    received = reader.apply_loss(encoded_packets, loss_mask)
"""

import csv
import os
import random
from collections import defaultdict


class MatlabLossReader:
    """
    Loads MATLAB-generated loss vectors and replays them block-by-block.
    Provides the same apply_loss() interface as RandomLossSimulator
    so it can be dropped into ExperimentRunner seamlessly.
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.loss_vectors  = defaultdict(list)   # key: (model, loss_rate) → list of [8] masks
        self.latency_data  = []
        self.summary_data  = []

        self._block_cursors = defaultdict(int)   # round-robin pointers
        self._is_loaded = False

    # ── Loading ────────────────────────────────────────────────────────────

    def load(self):
        """Parse all three CSV files from the MATLAB output directory."""
        self._load_loss_vectors()
        self._load_latency_samples()
        self._load_summary()
        self._is_loaded = True

        print(f"[MatlabLossReader] Loaded from '{self.data_dir}'")
        keys = list(self.loss_vectors.keys())
        for key in sorted(keys):
            model, rate = key
            print(f"  {model:12s}  loss={rate:.0%}  →  {len(self.loss_vectors[key]):4d} blocks")

    def _load_loss_vectors(self):
        # Support both singular and plural filenames
        for name in ('loss_vectors.csv', 'loss_vector.csv'):
            path = os.path.join(self.data_dir, name)
            if os.path.exists(path):
                break
        if not os.path.exists(path):
            raise FileNotFoundError(f"loss_vectors.csv not found in {self.data_dir}")

        with open(path, newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                # Skip blank lines, comment lines, and the header row
                if not row:
                    continue
                first = row[0].strip()
                if first.startswith('#') or first == 'model':
                    continue
                # Columns: model, loss_rate_target, trial, block, D0..P3
                model     = first              # 'random' or 'burst'
                loss_rate = float(row[1])
                mask = [int(row[i]) for i in range(4, 12)]  # D0-P3
                key = (model, round(loss_rate, 2))
                self.loss_vectors[key].append(mask)

    def _load_latency_samples(self):
        # Support both singular and plural filenames
        path = None
        for name in ('latency_samples.csv', 'latency_sample.csv'):
            candidate = os.path.join(self.data_dir, name)
            if os.path.exists(candidate):
                path = candidate
                break
        if path is None:
            return  # optional

        with open(path, newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0].startswith('#') or row[0] == 'packet_global_idx':
                    continue
                self.latency_data.append(float(row[2]))  # delay_ms

    def _load_summary(self):
        path = os.path.join(self.data_dir, 'channel_summary.csv')
        if not os.path.exists(path):
            return  # optional

        with open(path, newline='') as f:
            # Skip comment lines so DictReader sees the real header first
            lines = (ln for ln in f if not ln.startswith('#'))
            reader = csv.DictReader(lines)
            for row in reader:
                try:
                    self.summary_data.append({
                        'loss_rate_target': float(row['loss_rate_target']),
                        'trial':            int(row['trial']),
                        'actual_loss_rate': float(row['actual_loss_rate']),
                        'burst_mean_length':float(row['burst_mean_length']),
                        'delay_mean_ms':    float(row['delay_mean_ms']),
                        'delay_std_ms':     float(row['delay_std_ms']),
                        'channel_model_id': int(row['channel_model_id']),
                        'p_bg':             float(row.get('p_bg', row.get('doppler_hz', 0))),
                    })
                except (KeyError, ValueError):
                    continue  # skip any malformed rows

    # ── Block Access ───────────────────────────────────────────────────────

    def get_block(self, model: str, loss_rate: float) -> list:
        """
        Return next loss mask (list of 8 ints: 1=received, 0=lost)
        for the given (model, loss_rate) pair. Cycles round-robin through
        all available blocks.
        """
        assert self._is_loaded, "Call load() first"
        key = (model, round(loss_rate, 2))
        blocks = self.loss_vectors.get(key)
        if not blocks:
            # Graceful fallback: Bernoulli with target rate
            return [1 if random.random() > loss_rate else 0 for _ in range(8)]
        idx = self._block_cursors[key] % len(blocks)
        self._block_cursors[key] += 1
        return blocks[idx]

    def apply_loss(self, encoded_packets: list, loss_rate: float,
                   model: str = 'random') -> list:
        """
        Drop-in replacement for RandomLossSimulator.apply_loss().

        Args:
            encoded_packets: list of 8 bytes objects [D0,D1,D2,D3,P0,P1,P2,P3]
            loss_rate:       target channel loss rate (e.g. 0.20)
            model:           'random' (TDL-A) or 'burst' (TDL-B)

        Returns:
            list of 8 items — original bytes or None (if lost)
        """
        mask = self.get_block(model=model, loss_rate=loss_rate)
        return [pkt if mask[i] == 1 else None
                for i, pkt in enumerate(encoded_packets)]

    # ── Statistics ─────────────────────────────────────────────────────────

    def get_actual_loss_rate(self, model: str, loss_rate: float) -> float:
        """Compute measured PLR from the loaded MATLAB data."""
        key = (model, round(loss_rate, 2))
        blocks = self.loss_vectors.get(key, [])
        if not blocks:
            return loss_rate
        total = sum(len(b) for b in blocks)
        lost  = sum(1 - v for b in blocks for v in b)
        return lost / total if total > 0 else 0.0

    def get_burst_stats(self, model: str, loss_rate: float) -> dict:
        """Returns mean and max burst length from loaded blocks."""
        key = (model, round(loss_rate, 2))
        blocks = self.loss_vectors.get(key, [])
        burst_lengths = []
        for block in blocks:
            cur = 0
            for v in block:
                if v == 0:
                    cur += 1
                else:
                    if cur > 0:
                        burst_lengths.append(cur)
                        cur = 0
            if cur > 0:
                burst_lengths.append(cur)
        if not burst_lengths:
            return {'mean': 0, 'max': 0, 'count': 0}
        return {
            'mean':  sum(burst_lengths) / len(burst_lengths),
            'max':   max(burst_lengths),
            'count': len(burst_lengths),
        }

    def get_latency_stats(self) -> dict:
        """Return latency statistics matching Python ChannelModel.get_statistics()."""
        if not self.latency_data:
            return {}
        d = sorted(self.latency_data)
        n = len(d)
        return {
            'count':    n,
            'mean_ms':  sum(d) / n,
            'std_ms':   (sum((x - sum(d)/n)**2 for x in d) / n) ** 0.5,
            'min_ms':   d[0],
            'max_ms':   d[-1],
            'p50_ms':   d[int(n * 0.50)],
            'p95_ms':   d[int(n * 0.95)],
            'p99_ms':   d[int(n * 0.99)],
        }

    def available_models(self) -> list:
        return list({k[0] for k in self.loss_vectors})

    def available_rates(self, model: str) -> list:
        return sorted([k[1] for k in self.loss_vectors if k[0] == model])
