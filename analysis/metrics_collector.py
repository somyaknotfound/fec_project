"""
Metrics Collector
=================
Aggregates and formats experiment results for reporting.
"""


class MetricsCollector:
    """Collects, formats, and summarizes experiment metrics."""

    def __init__(self):
        self.records = []

    def add_result(self, channel_loss, no_fec_plr, fec_plr,
                   recovery_rate, overhead, no_fec_tp, fec_tp):
        """Add one data point (averaged across trials)."""
        self.records.append({
            'channel_loss_pct': round(channel_loss * 100, 1),
            'no_fec_plr_pct': round(no_fec_plr * 100, 2),
            'fec_plr_pct': round(fec_plr * 100, 2),
            'plr_reduction_pct': round((no_fec_plr - fec_plr) * 100, 2),
            'recovery_rate_pct': round(recovery_rate * 100, 2),
            'fec_overhead_pct': round(overhead * 100, 1),
            'no_fec_throughput_pct': round(no_fec_tp * 100, 2),
            'fec_throughput_pct': round(fec_tp * 100, 2),
        })

    def print_summary_table(self):
        """Print a formatted ASCII table of results."""
        header = (
            f"{'Ch.Loss%':>8} | {'No-FEC PLR%':>12} | {'FEC PLR%':>10} | "
            f"{'PLR Saved%':>10} | {'Recovery%':>10} | "
            f"{'No-FEC Tput%':>13} | {'FEC Tput%':>10}"
        )
        sep = "-" * len(header)

        print("\n" + sep)
        print("                  EXPERIMENT RESULTS SUMMARY")
        print(sep)
        print(header)
        print(sep)

        for r in self.records:
            print(
                f"{r['channel_loss_pct']:>8.1f} | "
                f"{r['no_fec_plr_pct']:>12.2f} | "
                f"{r['fec_plr_pct']:>10.2f} | "
                f"{r['plr_reduction_pct']:>10.2f} | "
                f"{r['recovery_rate_pct']:>10.1f} | "
                f"{r['no_fec_throughput_pct']:>13.2f} | "
                f"{r['fec_throughput_pct']:>10.2f}"
            )

        print(sep)

    def get_records(self):
        return self.records
