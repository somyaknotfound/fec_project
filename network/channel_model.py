"""
5G Channel Model — Latency Simulation
======================================
Simulates variable propagation delay typical of 5G URLLC links.

Typical 5G user-plane latency:
  - Best case (URLLC): ~1 ms
  - Typical eMBB:     ~4-10 ms
  - With congestion:  ~10-50 ms

This module adds per-packet delay values drawn from a configurable
distribution.  It does NOT actually sleep — it just annotates packets
with their simulated arrival time so experiments can compute latency
metrics offline.
"""

import random
import math

class ChannelModel:
    """
    Simulates 5G user-plane latency characteristics.

    Latency for each packet =  base_delay + jitter_sample
    where jitter_sample is drawn from a chosen distribution.
    """

    def __init__(self, base_delay_ms=2.0, jitter_std_ms=1.0,
                 distribution='normal', seed=None):
        """
        Parameters
        ----------
        base_delay_ms : float
            Fixed base propagation delay in milliseconds.
        jitter_std_ms : float
            Standard deviation of the jitter component (ms).
        distribution : str
            'normal' or 'uniform'.
        seed : int, optional
            Random seed for reproducibility.
        """
        self.base_delay_ms = base_delay_ms
        self.jitter_std_ms = jitter_std_ms
        self.distribution = distribution
        self.rng = random.Random(seed)
        # Recorded delays
        self.delays = []

    def get_delay(self):
        """
        Sample a single packet delay (in milliseconds).
        Always non-negative.
        """
        if self.distribution == 'normal':
            jitter = self.rng.gauss(0, self.jitter_std_ms)
        else:  # uniform
            jitter = self.rng.uniform(-self.jitter_std_ms, self.jitter_std_ms)

        delay = max(0.0, self.base_delay_ms + jitter)
        self.delays.append(delay)
        return delay

    def get_statistics(self):
        """
        Return latency statistics from all sampled delays.
        """
        if not self.delays:
            return {
                'count': 0, 'mean_ms': 0, 'std_ms': 0,
                'min_ms': 0, 'max_ms': 0,
                'p50_ms': 0, 'p95_ms': 0, 'p99_ms': 0,
            }

        sorted_d = sorted(self.delays)
        n = len(sorted_d)
        mean = sum(sorted_d) / n
        variance = sum((x - mean) ** 2 for x in sorted_d) / n

        def percentile(p):
            idx = int(p / 100.0 * (n - 1))
            return sorted_d[min(idx, n - 1)]

        return {
            'count': n,
            'mean_ms': round(mean, 3),
            'std_ms': round(math.sqrt(variance), 3),
            'min_ms': round(sorted_d[0], 3),
            'max_ms': round(sorted_d[-1], 3),
            'p50_ms': round(percentile(50), 3),
            'p95_ms': round(percentile(95), 3),
            'p99_ms': round(percentile(99), 3),
        }

    def reset(self):
        """Clear recorded delays."""
        self.delays = []
