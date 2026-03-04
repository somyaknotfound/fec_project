"""
Packet Loss Simulator
=====================
Simulates different packet loss patterns to test FEC effectiveness.

Two modes:
  1. Random (Bernoulli) loss  — each packet dropped independently with
     probability `loss_rate`.
  2. Burst (Gilbert-Elliott) loss — two-state Markov chain: GOOD state
     (low loss) and BAD state (high loss).  Models real wireless fading.
"""

import random

class RandomLossSimulator:
    """
    Simple independent random loss.
    Each packet is dropped with probability `loss_rate`.
    """

    def __init__(self, loss_rate=0.1, seed=None):
        """
        Parameters
        ----------
        loss_rate : float
            Probability of dropping each packet (0.0 to 1.0).
        seed : int, optional
            Random seed for reproducibility.
        """
        self.loss_rate = loss_rate
        self.rng = random.Random(seed)
        # Statistics
        self.total_packets = 0
        self.dropped_packets = 0

    def apply_loss(self, packets):
        """
        Apply random loss to a list of packets.

        Parameters
        ----------
        packets : list[bytes]
            List of packet data.

        Returns
        -------
        list[bytes | None]
            Same list with dropped packets replaced by None.
        """
        result = []
        for pkt in packets:
            self.total_packets += 1
            if self.rng.random() < self.loss_rate:
                result.append(None)
                self.dropped_packets += 1
            else:
                result.append(pkt)
        return result

    def get_actual_loss_rate(self):
        """Return the measured loss rate so far."""
        if self.total_packets == 0:
            return 0.0
        return self.dropped_packets / self.total_packets

    def reset_stats(self):
        """Reset statistics counters."""
        self.total_packets = 0
        self.dropped_packets = 0


class BurstLossSimulator:
    """
    Gilbert-Elliott burst loss model.

    Two states:
      - GOOD: packets are delivered (loss_prob = p_loss_good, usually ~0)
      - BAD:  packets are dropped  (loss_prob = p_loss_bad,  usually ~1)

    State transitions per packet:
      - GOOD → BAD  with probability p_good_to_bad
      - BAD  → GOOD with probability p_bad_to_good

    The average burst length ≈ 1 / p_bad_to_good.
    The average gap between bursts ≈ 1 / p_good_to_bad.
    """

    GOOD = 0
    BAD = 1

    def __init__(self, p_good_to_bad=0.05, p_bad_to_good=0.3,
                 p_loss_good=0.0, p_loss_bad=1.0, seed=None):
        """
        Parameters
        ----------
        p_good_to_bad : float
            Transition probability from GOOD→BAD state.
        p_bad_to_good : float
            Transition probability from BAD→GOOD state.
        p_loss_good : float
            Loss probability while in GOOD state (usually 0).
        p_loss_bad : float
            Loss probability while in BAD state (usually 1).
        seed : int, optional
            Random seed for reproducibility.
        """
        self.p_gb = p_good_to_bad
        self.p_bg = p_bad_to_good
        self.p_loss_good = p_loss_good
        self.p_loss_bad = p_loss_bad
        self.state = self.GOOD
        self.rng = random.Random(seed)
        # Statistics
        self.total_packets = 0
        self.dropped_packets = 0

    def apply_loss(self, packets):
        """Apply burst loss to a list of packets."""
        result = []
        for pkt in packets:
            self.total_packets += 1

            # Determine if this packet is lost based on current state
            loss_prob = self.p_loss_good if self.state == self.GOOD else self.p_loss_bad
            if self.rng.random() < loss_prob:
                result.append(None)
                self.dropped_packets += 1
            else:
                result.append(pkt)

            # State transition
            if self.state == self.GOOD:
                if self.rng.random() < self.p_gb:
                    self.state = self.BAD
            else:
                if self.rng.random() < self.p_bg:
                    self.state = self.GOOD

        return result

    def get_actual_loss_rate(self):
        if self.total_packets == 0:
            return 0.0
        return self.dropped_packets / self.total_packets

    def reset_stats(self):
        self.total_packets = 0
        self.dropped_packets = 0
        self.state = self.GOOD
