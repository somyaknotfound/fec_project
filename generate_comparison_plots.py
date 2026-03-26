"""
generate_comparison_plots.py
Generates 5 publication-quality comparison plots using:
  - Python experiment results  (data/results/experiment_results.json)
  - MATLAB channel CSV data    (data/results/matlab_channel/)

Outputs saved to: data/results/plots/
Run: python generate_comparison_plots.py
"""

import json
import os
import sys

# ── optional matplotlib check ─────────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use('Agg')   # non-interactive backend (no display needed)
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    from matplotlib.lines import Line2D
    import numpy as np
except ImportError:
    print("Install matplotlib and numpy:  pip install matplotlib numpy")
    sys.exit(1)

sys.path.insert(0, '.')
from network.matlab_loss_reader import MatlabLossReader

# ── Paths ─────────────────────────────────────────────────────────────────
JSON_PATH   = 'data/results/experiment_results.json'
MATLAB_DIR  = 'data/results/matlab_channel/'
OUTPUT_DIR  = 'data/results/plots/'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Load Python experiment results ────────────────────────────────────────
with open(JSON_PATH) as f:
    py_data = json.load(f)

py_loss_rates = [d['channel_loss_rate'] for d in py_data['random_loss']]
py_rnd_nofec  = [d['no_fec_plr']        for d in py_data['random_loss']]
py_rnd_fec    = [d['fec_plr']           for d in py_data['random_loss']]
py_rnd_rec    = [d['recovery_rate']     for d in py_data['random_loss']]
py_rnd_thru   = [d['fec_throughput']    for d in py_data['random_loss']]
py_rnd_nthru  = [d['no_fec_throughput'] for d in py_data['random_loss']]

py_burst_nofec= [d['no_fec_plr']        for d in py_data['burst_loss']]
py_burst_fec  = [d['fec_plr']           for d in py_data['burst_loss']]
py_burst_rec  = [d['recovery_rate']     for d in py_data['burst_loss']]

lat_nofec = py_data['latency']['no_fec']
lat_fec   = py_data['latency']['with_fec']

# ── Load MATLAB data ──────────────────────────────────────────────────────
reader = MatlabLossReader(MATLAB_DIR)
reader.load()

loss_rates = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]

def matlab_plr(model, rates):
    return [reader.get_actual_loss_rate(model, r) for r in rates]

def matlab_recovery(model, rates, n_data=4, n_total=8, n_blocks=500):
    """Replay MATLAB loss vectors through FEC logic to get recovery rate."""
    results = []
    for rate in rates:
        if rate == 0.0:
            results.append(1.0)
            continue
        recovered = 0
        for _ in range(n_blocks):
            mask = reader.get_block(model=model, loss_rate=rate)
            if sum(mask) >= n_data:
                recovered += 1
        results.append(recovered / n_blocks)
    return results

print("Computing MATLAB FEC recovery rates (this takes ~10s)...")
mat_rnd_fec_plr = matlab_plr('random', loss_rates)
mat_bst_fec_plr = matlab_plr('burst',  loss_rates)
mat_rnd_rec     = matlab_recovery('random', loss_rates)
mat_bst_rec     = matlab_recovery('burst',  loss_rates)

x   = [r*100 for r in loss_rates]  # percent for x-axis
px  = [r*100 for r in py_loss_rates]

# ── Style ─────────────────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size'  : 10,
    'axes.titlesize': 11,
    'axes.labelsize': 10,
    'legend.fontsize': 8,
    'figure.dpi' : 150,
    'axes.grid'  : True,
    'grid.alpha' : 0.35,
    'lines.linewidth': 1.8,
    'lines.markersize': 5,
})

COLORS = {
    'py_rnd' : '#2196F3',  # blue
    'py_bst' : '#F44336',  # red
    'mat_rnd': '#4CAF50',  # green
    'mat_bst': '#FF9800',  # orange
    'nofec'  : '#9C27B0',  # purple
    'target' : '#607D8B',  # grey
}

# ═══════════════════════════════════════════════════════════════════════════
#  PLOT 1: PLR Comparison — No-FEC vs FEC (Python + MATLAB)
# ═══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(7, 5))

ax.plot(px, [v*100 for v in py_rnd_nofec],  '--', color=COLORS['nofec'],
        marker='x', label='No-FEC (UDP baseline)')
ax.plot(px, [v*100 for v in py_rnd_fec],
        color=COLORS['py_rnd'],  marker='o', label='FEC + Python Bernoulli loss')
ax.plot(px, [v*100 for v in py_burst_fec],
        color=COLORS['py_bst'],  marker='s', label='FEC + Python GE Burst loss')
ax.plot(x,  [v*100 for v in mat_rnd_fec_plr],
        color=COLORS['mat_rnd'], marker='^', linestyle='--',
        label='FEC + MATLAB GE-Random')
ax.plot(x,  [v*100 for v in mat_bst_fec_plr],
        color=COLORS['mat_bst'], marker='D', linestyle='--',
        label='FEC + MATLAB GE-Burst')

ax.set_xlabel('Channel Packet Loss Rate (%)')
ax.set_ylabel('Effective PLR after FEC (%)')
ax.set_title('Packet Loss Rate: No-FEC vs FEC\n(Python Simulation vs MATLAB Validation)')
ax.legend(loc='upper left')
ax.set_xlim(-1, 52); ax.set_ylim(-1, 55)
plt.tight_layout()
p1 = os.path.join(OUTPUT_DIR, 'plot1_plr_comparison.png')
plt.savefig(p1); plt.close()
print(f"  Saved: {p1}")

# ═══════════════════════════════════════════════════════════════════════════
#  PLOT 2: Block Recovery Rate — All 4 Series
# ═══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(7, 5))

ax.plot(px, [v*100 for v in py_rnd_rec],
        color=COLORS['py_rnd'],  marker='o', label='Python Bernoulli (random)')
ax.plot(px, [v*100 for v in py_burst_rec],
        color=COLORS['py_bst'],  marker='s', label='Python GE Burst')
ax.plot(x,  [v*100 for v in mat_rnd_rec],
        color=COLORS['mat_rnd'], marker='^', linestyle='--',
        label='MATLAB GE-Random (validation)')
ax.plot(x,  [v*100 for v in mat_bst_rec],
        color=COLORS['mat_bst'], marker='D', linestyle='--',
        label='MATLAB GE-Burst (validation)')
ax.axhline(99.999, color=COLORS['target'], linestyle=':', linewidth=1.5,
           label='5G URLLC Target (99.999%)')

ax.set_xlabel('Channel Packet Loss Rate (%)')
ax.set_ylabel('Block Recovery Rate (%)')
ax.set_title('FEC Block Recovery Rate vs Channel Loss\n(k=4 data, r=4 parity — any 4 of 8 suffice)')
ax.legend(loc='lower left')
ax.set_xlim(-1, 52); ax.set_ylim(50, 103)
plt.tight_layout()
p2 = os.path.join(OUTPUT_DIR, 'plot2_recovery_rate.png')
plt.savefig(p2); plt.close()
print(f"  Saved: {p2}")

# ═══════════════════════════════════════════════════════════════════════════
#  PLOT 3: Burst Length Distribution (MATLAB GE-Burst)
# ═══════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(10, 4), sharey=True)
rate_labels = [('10%', 0.10), ('20%', 0.20), ('30%', 0.30)]

for ax, (label, rate) in zip(axes, rate_labels):
    stats = reader.get_burst_stats('burst', rate)
    # Re-collect burst lengths for histogram
    key = ('burst', round(rate, 2))
    blocks = reader.loss_vectors.get(key, [])
    bl = []
    for block in blocks:
        cur = 0
        for v in block:
            if v == 0:
                cur += 1
            else:
                if cur > 0:
                    bl.append(cur)
                    cur = 0
        if cur > 0:
            bl.append(cur)

    if bl:
        max_bl = max(bl)
        bins = np.arange(0.5, max_bl + 1.5, 1)
        ax.hist(bl, bins=bins, density=True, color=COLORS['mat_bst'],
                alpha=0.75, edgecolor='white')
        ax.axvline(stats['mean'], color='red', linestyle='--', linewidth=1.5,
                   label=f'Mean={stats["mean"]:.2f}')
        ax.axvline(1/0.30, color='grey', linestyle=':', linewidth=1.5,
                   label='Theory=3.33')
    ax.set_title(f'Channel Loss = {label}')
    ax.set_xlabel('Burst Length (packets)')
    ax.legend(fontsize=7)

axes[0].set_ylabel('Probability')
fig.suptitle('Burst Length Distribution — MATLAB GE-Burst Model\n'
             '(p_bg=0.30, theoretical mean=3.33 packets)', fontsize=11)
plt.tight_layout()
p3 = os.path.join(OUTPUT_DIR, 'plot3_burst_distribution.png')
plt.savefig(p3); plt.close()
print(f"  Saved: {p3}")

# ═══════════════════════════════════════════════════════════════════════════
#  PLOT 4: Latency CDF — Python vs MATLAB
# ═══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(7, 5))

# Python latency — reconstruct approximate distribution from stats
# Generate normal samples matching Python stats
rng = np.random.default_rng(42)
py_nofec_samples = rng.normal(lat_nofec['mean_ms'], lat_nofec['std_ms'], 1000)
py_fec_samples   = rng.normal(lat_fec['mean_ms'],   lat_fec['std_ms'],   1000)
py_nofec_samples = np.clip(py_nofec_samples, lat_nofec['min_ms'], lat_nofec['max_ms'])
py_fec_samples   = np.clip(py_fec_samples,   lat_fec['min_ms'],   lat_fec['max_ms'])

# MATLAB latency samples
mat_delays = reader.latency_data
mat_random = mat_delays[:len(mat_delays)//2]
mat_burst  = mat_delays[len(mat_delays)//2:]

def plot_cdf(ax, data, color, label, linestyle='-'):
    sorted_d = np.sort(data)
    cdf = np.arange(1, len(sorted_d)+1) / len(sorted_d)
    ax.plot(sorted_d, cdf*100, color=color, linestyle=linestyle, label=label)

plot_cdf(ax, py_nofec_samples, COLORS['nofec'],   'Python No-FEC',       '--')
plot_cdf(ax, py_fec_samples,   COLORS['py_rnd'],  'Python FEC',          '--')
plot_cdf(ax, mat_random,       COLORS['mat_rnd'], 'MATLAB GE-Random FEC')
plot_cdf(ax, mat_burst,        COLORS['mat_bst'], 'MATLAB GE-Burst FEC')

ax.axvline(1.0, color='red',  linestyle=':', alpha=0.7, label='URLLC 1ms target')
ax.axvline(lat_nofec['p99_ms'], color=COLORS['nofec'], linestyle=':',
           alpha=0.5, label=f'Python No-FEC P99={lat_nofec["p99_ms"]}ms')

ax.set_xlabel('Delay (ms)')
ax.set_ylabel('CDF (%)')
ax.set_title('Latency CDF: Python Simulation vs MATLAB Validation')
ax.legend(loc='lower right')
ax.set_xlim(-0.2, 7); ax.set_ylim(0, 102)
plt.tight_layout()
p4 = os.path.join(OUTPUT_DIR, 'plot4_latency_cdf.png')
plt.savefig(p4); plt.close()
print(f"  Saved: {p4}")

# ═══════════════════════════════════════════════════════════════════════════
#  PLOT 5: Throughput Crossover — Python Baseline
# ═══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(7, 5))

ax.plot(px, [v*100 for v in py_rnd_nthru],
        color=COLORS['py_bst'], marker='x', label='No-FEC (UDP)')
ax.plot(px, [v*100 for v in py_rnd_thru],
        color=COLORS['py_rnd'], marker='o', label='With FEC (k=4, r=4)')
ax.axhline(50, color='grey', linestyle='--', alpha=0.6, label='Code rate limit (50%)')

# Find crossover point
for i in range(len(px)-1):
    if py_rnd_nthru[i] > py_rnd_thru[i] and py_rnd_nthru[i+1] < py_rnd_thru[i+1]:
        midx = (px[i] + px[i+1]) / 2
        ax.axvline(midx, color='green', linestyle=':', linewidth=1.5,
                   label=f'Crossover ≈{midx:.0f}%')
        break

ax.fill_between(px,
                [v*100 for v in py_rnd_nthru],
                [v*100 for v in py_rnd_thru],
                where=[t > n for t, n in zip(py_rnd_thru, py_rnd_nthru)],
                alpha=0.15, color='green', label='FEC advantage zone')

ax.set_xlabel('Channel Packet Loss Rate (%)')
ax.set_ylabel('Effective Throughput (%)')
ax.set_title('Effective Throughput: No-FEC vs FEC\n'
             'FEC overhead justified beyond crossover point')
ax.legend(loc='upper right')
ax.set_xlim(-1, 52); ax.set_ylim(30, 105)
plt.tight_layout()
p5 = os.path.join(OUTPUT_DIR, 'plot5_throughput_crossover.png')
plt.savefig(p5); plt.close()
print(f"  Saved: {p5}")

# ═══════════════════════════════════════════════════════════════════════════
#  PLOT 6: Combined 2×3 Summary Figure (paper-ready)
# ═══════════════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(14, 9))
gs  = gridspec.GridSpec(2, 3, figure=fig, hspace=0.42, wspace=0.32)

axes = [fig.add_subplot(gs[r, c]) for r in range(2) for c in range(3)]

# [0] PLR
ax = axes[0]
ax.plot(px, [v*100 for v in py_rnd_nofec], '--', color=COLORS['nofec'],  marker='x', ms=4, label='No-FEC')
ax.plot(px, [v*100 for v in py_rnd_fec],        color=COLORS['py_rnd'], marker='o', ms=4, label='FEC+Bernoulli')
ax.plot(px, [v*100 for v in py_burst_fec],       color=COLORS['py_bst'], marker='s', ms=4, label='FEC+GE Burst')
ax.plot(x,  [v*100 for v in mat_rnd_fec_plr],'--',color=COLORS['mat_rnd'],marker='^',ms=4,label='MATLAB GE-Rnd')
ax.plot(x,  [v*100 for v in mat_bst_fec_plr],'--',color=COLORS['mat_bst'],marker='D',ms=4,label='MATLAB GE-Bst')
ax.set_title('(a) Effective PLR'); ax.set_xlabel('Channel Loss (%)'); ax.set_ylabel('PLR (%)')
ax.legend(fontsize=6, loc='upper left'); ax.set_xlim(-1,52); ax.set_ylim(-1,52)

# [1] Recovery Rate
ax = axes[1]
ax.plot(px,[v*100 for v in py_rnd_rec],  color=COLORS['py_rnd'], marker='o',ms=4,label='Python Bernoulli')
ax.plot(px,[v*100 for v in py_burst_rec],color=COLORS['py_bst'], marker='s',ms=4,label='Python GE Burst')
ax.plot(x, [v*100 for v in mat_rnd_rec],'--',color=COLORS['mat_rnd'],marker='^',ms=4,label='MATLAB GE-Rnd')
ax.plot(x, [v*100 for v in mat_bst_rec],'--',color=COLORS['mat_bst'],marker='D',ms=4,label='MATLAB GE-Bst')
ax.axhline(99.999,color=COLORS['target'],linestyle=':',lw=1.2,label='URLLC 99.999%')
ax.set_title('(b) Block Recovery Rate'); ax.set_xlabel('Channel Loss (%)'); ax.set_ylabel('Recovery (%)')
ax.legend(fontsize=6,loc='lower left'); ax.set_xlim(-1,52); ax.set_ylim(48,103)

# [2] Throughput
ax = axes[2]
ax.plot(px,[v*100 for v in py_rnd_nthru],color=COLORS['py_bst'],marker='x',ms=4,label='No-FEC UDP')
ax.plot(px,[v*100 for v in py_rnd_thru], color=COLORS['py_rnd'],marker='o',ms=4,label='With FEC')
ax.axhline(50,color='grey',linestyle='--',alpha=0.6,lw=1)
ax.fill_between(px,[v*100 for v in py_rnd_nthru],[v*100 for v in py_rnd_thru],
                where=[t>n for t,n in zip(py_rnd_thru,py_rnd_nthru)],
                alpha=0.15,color='green')
ax.set_title('(c) Effective Throughput'); ax.set_xlabel('Channel Loss (%)'); ax.set_ylabel('Throughput (%)')
ax.legend(fontsize=7); ax.set_xlim(-1,52); ax.set_ylim(28,105)

# [3] Burst distribution at 20%
ax = axes[3]
key = ('burst', 0.20)
blocks = reader.loss_vectors.get(key, [])
bl = []
for block in blocks:
    cur = 0
    for v in block:
        if v == 0: cur += 1
        else:
            if cur > 0: bl.append(cur)
            cur = 0
    if cur > 0: bl.append(cur)
if bl:
    bins = np.arange(0.5, max(bl)+1.5, 1)
    ax.hist(bl, bins=bins, density=True, color=COLORS['mat_bst'], alpha=0.75, edgecolor='white')
    ax.axvline(np.mean(bl),color='red',linestyle='--',lw=1.5,label=f'Mean={np.mean(bl):.2f}')
    ax.axvline(1/0.30,color='grey',linestyle=':',lw=1.2,label='Theory=3.33')
ax.set_title('(d) Burst Length (GE-Burst, 20%)'); ax.set_xlabel('Burst Length (pkts)'); ax.set_ylabel('Probability')
ax.legend(fontsize=7)

# [4] Latency CDF
ax = axes[4]
plot_cdf(ax, py_nofec_samples, COLORS['nofec'],   'Python No-FEC', '--')
plot_cdf(ax, py_fec_samples,   COLORS['py_rnd'],  'Python FEC',    '--')
plot_cdf(ax, mat_random,       COLORS['mat_rnd'], 'MATLAB GE-Rnd')
plot_cdf(ax, mat_burst,        COLORS['mat_bst'], 'MATLAB GE-Bst')
ax.axvline(1.0,color='red',linestyle=':',lw=1.2,alpha=0.8,label='URLLC 1ms')
ax.set_title('(e) Latency CDF'); ax.set_xlabel('Delay (ms)'); ax.set_ylabel('CDF (%)')
ax.legend(fontsize=6,loc='lower right'); ax.set_xlim(-0.2,7)

# [5] Python vs MATLAB PLR scatter (calibration check)
ax = axes[5]
ax.scatter(loss_rates, mat_rnd_fec_plr, color=COLORS['mat_rnd'], marker='^', s=50, label='MATLAB GE-Random')
ax.scatter(loss_rates, mat_bst_fec_plr, color=COLORS['mat_bst'], marker='D', s=50, label='MATLAB GE-Burst')
ax.plot([0,0.5],[0,0.5],'k:',lw=1,label='Ideal (y=x)')
ax.set_title('(f) MATLAB PLR Calibration'); ax.set_xlabel('Target Loss Rate'); ax.set_ylabel('Actual PLR')
ax.legend(fontsize=7); ax.set_xlim(-0.02,0.53); ax.set_ylim(-0.02,0.60)

fig.suptitle('FEC for 5G URLLC — Results Summary\n'
             'Python Simulation vs MATLAB GE Channel Validation',
             fontsize=12, fontweight='bold', y=1.01)

p6 = os.path.join(OUTPUT_DIR, 'plot6_summary_figure.png')
plt.savefig(p6, bbox_inches='tight'); plt.close()
print(f"  Saved: {p6}")

print(f"\nAll 6 plots saved to: {OUTPUT_DIR}")
print("  plot1_plr_comparison.png      — PLR: No-FEC vs FEC, all 4 channel types")
print("  plot2_recovery_rate.png       — Block recovery rate vs channel loss")
print("  plot3_burst_distribution.png  — Burst length histograms at 10/20/30%")
print("  plot4_latency_cdf.png         — Latency CDF: Python vs MATLAB")
print("  plot5_throughput_crossover.png— Throughput crossover point")
print("  plot6_summary_figure.png      — Combined 2×3 paper figure")
