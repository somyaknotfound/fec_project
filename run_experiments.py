#!/usr/bin/env python3
"""
Run FEC Experiments — Main Entry Point
=======================================
Runs the full experiment suite comparing FEC vs no-FEC performance,
then generates graphs and a summary table.

Usage:
    python run_experiments.py
"""

import os
import sys
import time

from experiments.experiment_runner import ExperimentRunner
from analysis.metrics_collector import MetricsCollector
from analysis.visualizer import Visualizer


def main():
    print("=" * 60)
    print("  FORWARD ERROR CORRECTION - 5G URLLC EXPERIMENTS")
    print("  Packet-Level FEC Performance Evaluation")
    print("=" * 60)
    print()

    start = time.time()

    # ------------------------------------------------------------------
    # 1. Run experiments
    # ------------------------------------------------------------------
    runner = ExperimentRunner(
        n_data=4,        # 4 data packets per block
        n_parity=4,      # 4 parity packets per block (code rate = 0.5)
        num_blocks=50,   # 50 blocks per trial
        num_trials=5,    # 5 trials per loss rate
    )

    results = runner.run_all_experiments(
        loss_rates=[0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
    )

    # ------------------------------------------------------------------
    # 2. Collect and display metrics
    # ------------------------------------------------------------------
    collector = MetricsCollector()
    for entry in results['random_loss']:
        collector.add_result(
            channel_loss=entry['channel_loss_rate'],
            no_fec_plr=entry['no_fec_plr'],
            fec_plr=entry['fec_plr'],
            recovery_rate=entry['recovery_rate'],
            overhead=entry['overhead'],
            no_fec_tp=entry['no_fec_throughput'],
            fec_tp=entry['fec_throughput'],
        )

    collector.print_summary_table()

    # ------------------------------------------------------------------
    # 3. Generate graphs
    # ------------------------------------------------------------------
    print("\nGenerating academic-quality graphs...")
    viz = Visualizer(output_dir='data/results')
    viz.generate_all(results)

    # ------------------------------------------------------------------
    # 4. Save raw results
    # ------------------------------------------------------------------
    results_path = os.path.join('data', 'results', 'experiment_results.json')
    runner.save_results(results, results_path)

    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"  ALL EXPERIMENTS COMPLETE  ({elapsed:.1f}s)")
    print(f"  Results:  data/results/experiment_results.json")
    print(f"  Graphs:   data/results/*.png")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
