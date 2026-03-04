"""
Visualizer — Academic-Quality Graphs
=====================================
Generates publication-ready matplotlib plots comparing FEC vs no-FEC
performance under various channel conditions.

Produces 4 graphs:
  1. Packet Loss Rate comparison
  2. Block Recovery Success Rate
  3. Effective Throughput comparison
  4. Latency CDF
"""

import os
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend (no GUI needed)
import matplotlib.pyplot as plt
import numpy as np


# Consistent academic styling
COLORS = {
    'no_fec': '#E74C3C',    # red
    'fec': '#2ECC71',       # green
    'burst_no_fec': '#C0392B',
    'burst_fec': '#27AE60',
}
STYLE = {
    'figure.figsize': (10, 6),
    'font.size': 12,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'legend.fontsize': 11,
    'lines.linewidth': 2.5,
    'lines.markersize': 8,
    'grid.alpha': 0.3,
}
plt.rcParams.update(STYLE)


class Visualizer:
    """Generate academic-quality FEC performance graphs."""

    def __init__(self, output_dir='data/results'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_all(self, results):
        """Generate all 4 graphs from experiment results."""
        self.plot_plr_comparison(results)
        self.plot_recovery_rate(results)
        self.plot_throughput_comparison(results)
        self.plot_latency_cdf(results)
        print(f"\n✓ All graphs saved to: {os.path.abspath(self.output_dir)}/")

    # ------------------------------------------------------------------
    # Graph 1: Packet Loss Rate
    # ------------------------------------------------------------------
    def plot_plr_comparison(self, results):
        """Channel Loss Rate vs Effective Packet Loss Rate."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        for ax, key, title in [
            (ax1, 'random_loss', 'Random (Bernoulli) Packet Loss'),
            (ax2, 'burst_loss', 'Burst (Gilbert-Elliott) Packet Loss'),
        ]:
            data = results[key]
            x = [d['channel_loss_rate'] * 100 for d in data]
            y_no_fec = [d['no_fec_plr'] * 100 for d in data]
            y_fec = [d['fec_plr'] * 100 for d in data]

            ax.plot(x, y_no_fec, 'o-', color=COLORS['no_fec'],
                    label='Without FEC', zorder=3)
            ax.plot(x, y_fec, 's-', color=COLORS['fec'],
                    label='With FEC', zorder=3)
            ax.plot(x, x, '--', color='gray', alpha=0.5,
                    label='Theoretical (no recovery)')

            # Shade the improvement region
            ax.fill_between(x, y_no_fec, y_fec,
                           alpha=0.15, color=COLORS['fec'],
                           label='FEC improvement')

            ax.set_xlabel('Channel Packet Loss Rate (%)')
            ax.set_ylabel('Effective Packet Loss Rate (%)')
            ax.set_title(title)
            ax.legend(loc='upper left')
            ax.grid(True, alpha=0.3)
            ax.set_xlim(-1, 52)
            ax.set_ylim(-1, max(max(y_no_fec) + 5, 55))

        fig.suptitle('FEC Reduces Effective Packet Loss Rate in 5G URLLC',
                     fontsize=15, fontweight='bold', y=1.02)
        fig.tight_layout()
        filepath = os.path.join(self.output_dir, 'plr_comparison.png')
        fig.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  ✓ Saved: {filepath}")

    # ------------------------------------------------------------------
    # Graph 2: Recovery Rate
    # ------------------------------------------------------------------
    def plot_recovery_rate(self, results):
        """Channel Loss Rate vs Block Recovery Success Rate."""
        fig, ax = plt.subplots(figsize=(10, 6))

        for key, label, color, marker in [
            ('random_loss', 'Random Loss', COLORS['fec'], 'o'),
            ('burst_loss', 'Burst Loss', COLORS['burst_fec'], 's'),
        ]:
            data = results[key]
            x = [d['channel_loss_rate'] * 100 for d in data]
            y = [d['recovery_rate'] * 100 for d in data]
            ax.plot(x, y, f'{marker}-', color=color, label=label)

        # 5G URLLC target line
        ax.axhline(y=99.999, color='orange', linestyle='--', alpha=0.7,
                   label='5G URLLC Target (99.999%)')
        ax.axhline(y=99.9, color='gold', linestyle=':', alpha=0.7,
                   label='5G eMBB Target (99.9%)')

        ax.set_xlabel('Channel Packet Loss Rate (%)')
        ax.set_ylabel('Block Recovery Success Rate (%)')
        ax.set_title('FEC Block Recovery Success Rate vs Channel Loss',
                     fontweight='bold')
        ax.legend(loc='lower left')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-1, 52)
        ax.set_ylim(-5, 105)

        filepath = os.path.join(self.output_dir, 'recovery_rate.png')
        fig.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  ✓ Saved: {filepath}")

    # ------------------------------------------------------------------
    # Graph 3: Throughput
    # ------------------------------------------------------------------
    def plot_throughput_comparison(self, results):
        """Effective throughput comparison (accounts for FEC overhead)."""
        fig, ax = plt.subplots(figsize=(10, 6))

        data = results['random_loss']
        x = [d['channel_loss_rate'] * 100 for d in data]
        y_no_fec = [d['no_fec_throughput'] * 100 for d in data]
        y_fec = [d['fec_throughput'] * 100 for d in data]

        ax.plot(x, y_no_fec, 'o-', color=COLORS['no_fec'],
                label='Without FEC (raw)')
        ax.plot(x, y_fec, 's-', color=COLORS['fec'],
                label='With FEC (effective)')

        # Code rate line (theoretical max with FEC overhead)
        code_rate = results['config']['code_rate'] * 100
        ax.axhline(y=code_rate, color='blue', linestyle='--', alpha=0.5,
                   label=f'Code Rate Limit ({code_rate:.0f}%)')

        ax.fill_between(x, y_no_fec, y_fec,
                       where=[f > n for f, n in zip(y_fec, y_no_fec)],
                       alpha=0.15, color=COLORS['fec'],
                       label='FEC advantage')
        ax.fill_between(x, y_no_fec, y_fec,
                       where=[f <= n for f, n in zip(y_fec, y_no_fec)],
                       alpha=0.15, color=COLORS['no_fec'],
                       label='FEC overhead cost')

        ax.set_xlabel('Channel Packet Loss Rate (%)')
        ax.set_ylabel('Effective Throughput (%)')
        ax.set_title('Throughput Trade-off: FEC Overhead vs Recovery Gain',
                     fontweight='bold')
        ax.legend(loc='lower left')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-1, 52)
        ax.set_ylim(-5, 105)

        filepath = os.path.join(self.output_dir, 'throughput_comparison.png')
        fig.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  ✓ Saved: {filepath}")

    # ------------------------------------------------------------------
    # Graph 4: Latency CDF
    # ------------------------------------------------------------------
    def plot_latency_cdf(self, results):
        """Latency CDF comparison (with vs without FEC)."""
        fig, ax = plt.subplots(figsize=(10, 6))

        lat_data = results.get('latency', {})

        for key, label, color in [
            ('no_fec', 'Without FEC', COLORS['no_fec']),
            ('with_fec', 'With FEC', COLORS['fec']),
        ]:
            stats = lat_data.get(key, {})
            if not stats or stats.get('count', 0) == 0:
                continue

            # Regenerate sample data from statistics for CDF plot
            mean = stats['mean_ms']
            std = stats['std_ms']
            n = min(stats['count'], 1000)
            np.random.seed(42 if key == 'no_fec' else 43)
            samples = np.random.normal(mean, std, n)
            samples = np.maximum(samples, 0)
            sorted_s = np.sort(samples)
            cdf = np.arange(1, n + 1) / n

            ax.plot(sorted_s, cdf * 100, color=color, label=label)

            # Mark percentiles
            ax.axvline(x=stats['p95_ms'], color=color, linestyle=':',
                       alpha=0.5)
            ax.text(stats['p95_ms'] + 0.1, 50 if key == 'no_fec' else 40,
                    f"P95={stats['p95_ms']:.1f}ms", color=color, fontsize=9)

        # URLLC target
        ax.axvline(x=1.0, color='orange', linestyle='--', alpha=0.7,
                   label='URLLC Target (1ms)')

        ax.set_xlabel('Latency (ms)')
        ax.set_ylabel('CDF (%)')
        ax.set_title('Packet Delivery Latency Distribution',
                     fontweight='bold')
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-0.5, 8)
        ax.set_ylim(-5, 105)

        filepath = os.path.join(self.output_dir, 'latency_cdf.png')
        fig.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  ✓ Saved: {filepath}")
