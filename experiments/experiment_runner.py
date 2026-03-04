"""
Experiment Runner — FEC vs No-FEC Comparison
=============================================
Runs controlled experiments to measure how FEC improves packet delivery
under varying channel loss conditions.

For each loss rate, we run:
  - Baseline (no FEC):  send N packets, simulate loss, count survivors
  - With FEC:           encode N→(N+K) packets, simulate loss, decode, count recovered

Multiple trials per loss rate for statistical significance.
Results are saved to JSON for later visualization.
"""

import json
import os
import time
import logging

from core.fec_encoder import FECEncoder
from core.fec_decoder import FECDecoder
from network.packet_loss_simulator import RandomLossSimulator, BurstLossSimulator
from network.channel_model import ChannelModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExperimentRunner:
    """Runs FEC performance experiments with baseline comparison."""

    def __init__(self, n_data=4, n_parity=4, num_blocks=50, num_trials=5):
        """
        Parameters
        ----------
        n_data : int
            Number of data packets per FEC block.
        n_parity : int
            Number of parity packets per FEC block.
        num_blocks : int
            Number of FEC blocks per trial (more blocks = more data points).
        num_trials : int
            Number of trials per loss rate (for computing averages).
        """
        self.n_data = n_data
        self.n_parity = n_parity
        self.num_blocks = num_blocks
        self.num_trials = num_trials

    def run_all_experiments(self, loss_rates=None):
        """
        Run experiments across all loss rates for both random and burst loss.

        Returns a dict with all results ready for visualization.
        """
        if loss_rates is None:
            loss_rates = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]

        logger.info("=" * 60)
        logger.info("FEC EXPERIMENT SUITE")
        logger.info(f"Config: ({self.n_data},{self.n_parity}) code, "
                     f"{self.num_blocks} blocks/trial, {self.num_trials} trials/rate")
        logger.info("=" * 60)

        results = {
            'config': {
                'n_data': self.n_data,
                'n_parity': self.n_parity,
                'code_rate': self.n_data / (self.n_data + self.n_parity),
                'num_blocks': self.num_blocks,
                'num_trials': self.num_trials,
            },
            'random_loss': self._run_loss_sweep(loss_rates, loss_type='random'),
            'burst_loss': self._run_loss_sweep(loss_rates, loss_type='burst'),
        }

        # Add latency comparison
        results['latency'] = self._run_latency_experiment()

        return results

    # ------------------------------------------------------------------
    # Core experiment loops
    # ------------------------------------------------------------------

    def _run_loss_sweep(self, loss_rates, loss_type='random'):
        """Sweep across loss rates, comparing FEC vs no-FEC."""
        sweep_results = []

        for rate in loss_rates:
            logger.info(f"\n--- {loss_type.upper()} Loss Rate: {rate*100:.0f}% ---")

            trial_results = []
            for trial in range(self.num_trials):
                seed = trial * 1000 + int(rate * 100)
                result = self._run_single_trial(rate, seed, loss_type)
                trial_results.append(result)

            # Average across trials
            avg = self._average_results(trial_results)
            avg['channel_loss_rate'] = rate
            avg['loss_type'] = loss_type
            sweep_results.append(avg)

            logger.info(f"  No-FEC PLR: {avg['no_fec_plr']*100:.1f}%  |  "
                         f"FEC PLR: {avg['fec_plr']*100:.1f}%  |  "
                         f"Recovery: {avg['recovery_rate']*100:.1f}%")

        return sweep_results

    def _run_single_trial(self, loss_rate, seed, loss_type):
        """Run one trial: generate data, encode, simulate loss, decode."""
        encoder = FECEncoder(self.n_data, self.n_parity)
        decoder = FECDecoder(self.n_data, self.n_parity)
        channel = ChannelModel(base_delay_ms=2.0, jitter_std_ms=1.0, seed=seed)

        # Create loss simulator
        if loss_type == 'random':
            simulator = RandomLossSimulator(loss_rate, seed=seed)
        else:
            # Configure burst loss to achieve approximately the target loss rate
            # Steady-state loss ≈ p_gb / (p_gb + p_bg)
            if loss_rate == 0:
                simulator = RandomLossSimulator(0.0, seed=seed)
            else:
                p_bg = 0.3   # avg burst length ≈ 3.3 packets
                p_gb = (loss_rate * p_bg) / (1.0 - loss_rate) if loss_rate < 1.0 else 0.5
                p_gb = min(p_gb, 0.9)
                simulator = BurstLossSimulator(
                    p_good_to_bad=p_gb, p_bad_to_good=p_bg,
                    seed=seed
                )

        # Generate test data
        all_data_packets = []
        for block_id in range(self.num_blocks):
            block_data = [
                f"B{block_id:04d}_P{i:02d}".encode() + bytes(range(256)) * 4
                for i in range(self.n_data)
            ]
            all_data_packets.append(block_data)

        # === Baseline (No FEC) ===
        no_fec_sent = 0
        no_fec_received = 0
        baseline_sim = RandomLossSimulator(loss_rate, seed=seed) if loss_type == 'random' \
            else BurstLossSimulator(
                p_good_to_bad=simulator.p_gb if hasattr(simulator, 'p_gb') else 0,
                p_bad_to_good=simulator.p_bg if hasattr(simulator, 'p_bg') else 0.3,
                seed=seed
            ) if loss_rate > 0 else RandomLossSimulator(0.0, seed=seed)

        for block_data in all_data_packets:
            received = baseline_sim.apply_loss(block_data)
            no_fec_sent += len(block_data)
            no_fec_received += sum(1 for p in received if p is not None)

        # === With FEC ===
        fec_data_sent = 0
        fec_data_recovered = 0
        fec_total_sent = 0
        blocks_ok = 0
        blocks_fail = 0

        # Reset simulator with same seed for fair comparison
        if loss_type == 'random':
            fec_sim = RandomLossSimulator(loss_rate, seed=seed + 500)
        elif loss_rate > 0:
            fec_sim = BurstLossSimulator(
                p_good_to_bad=simulator.p_gb if hasattr(simulator, 'p_gb') else 0,
                p_bad_to_good=simulator.p_bg if hasattr(simulator, 'p_bg') else 0.3,
                seed=seed + 500
            )
        else:
            fec_sim = RandomLossSimulator(0.0, seed=seed + 500)

        for block_data in all_data_packets:
            # Encode
            encoded = encoder.encode_block(block_data)
            fec_total_sent += len(encoded)
            fec_data_sent += len(block_data)

            # Simulate channel delay for each packet
            for _ in encoded:
                channel.get_delay()

            # Simulate loss
            received = fec_sim.apply_loss(encoded)

            # Decode
            recovered, success = decoder.decode_block(received)

            if success:
                blocks_ok += 1
                fec_data_recovered += self.n_data
            else:
                blocks_fail += 1
                # Count whatever data packets survived directly
                for i in range(self.n_data):
                    if received[i] is not None:
                        fec_data_recovered += 1

        # Compute metrics
        no_fec_plr = 1.0 - (no_fec_received / no_fec_sent) if no_fec_sent > 0 else 0
        fec_plr = 1.0 - (fec_data_recovered / fec_data_sent) if fec_data_sent > 0 else 0
        recovery_rate = blocks_ok / self.num_blocks if self.num_blocks > 0 else 0
        overhead = (fec_total_sent - fec_data_sent) / fec_data_sent if fec_data_sent > 0 else 0

        # Effective throughput (data packets recovered / total packets sent)
        no_fec_throughput = no_fec_received / no_fec_sent if no_fec_sent > 0 else 0
        fec_throughput = fec_data_recovered / fec_total_sent if fec_total_sent > 0 else 0

        return {
            'no_fec_plr': no_fec_plr,
            'fec_plr': fec_plr,
            'recovery_rate': recovery_rate,
            'overhead': overhead,
            'no_fec_throughput': no_fec_throughput,
            'fec_throughput': fec_throughput,
            'latency_stats': channel.get_statistics(),
            'blocks_ok': blocks_ok,
            'blocks_fail': blocks_fail,
        }

    def _run_latency_experiment(self):
        """Compare latency with and without FEC."""
        logger.info("\n--- Latency Experiment ---")

        # Without FEC: just propagation delay
        channel_no_fec = ChannelModel(base_delay_ms=2.0, jitter_std_ms=1.0, seed=42)
        for _ in range(1000):
            channel_no_fec.get_delay()

        # With FEC: propagation delay + encoding overhead (~0.5ms simulated)
        channel_fec = ChannelModel(base_delay_ms=2.5, jitter_std_ms=1.0, seed=42)
        for _ in range(1000):
            channel_fec.get_delay()

        return {
            'no_fec': channel_no_fec.get_statistics(),
            'with_fec': channel_fec.get_statistics(),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _average_results(trial_results):
        """Average numeric fields across multiple trials."""
        keys = ['no_fec_plr', 'fec_plr', 'recovery_rate', 'overhead',
                'no_fec_throughput', 'fec_throughput']
        avg = {}
        for key in keys:
            values = [t[key] for t in trial_results]
            avg[key] = sum(values) / len(values)
            avg[key + '_std'] = (
                sum((v - avg[key]) ** 2 for v in values) / len(values)
            ) ** 0.5
        return avg

    @staticmethod
    def save_results(results, filepath):
        """Save experiment results to JSON."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to: {filepath}")
