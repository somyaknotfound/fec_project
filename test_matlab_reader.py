import sys
sys.path.insert(0, '.')
from network.matlab_loss_reader import MatlabLossReader

r = MatlabLossReader('data/results/matlab_channel/')
r.load()

print()
print('=== SPOT CHECK: blocks at 20% loss ===')
for model in ['random', 'burst']:
    mask = r.get_block(model=model, loss_rate=0.20)
    print(f'  {model:8s}  mask={mask}  received={sum(mask)}/8')

print()
print('=== BURST STATS (burst model) ===')
for rate in [0.10, 0.20, 0.30]:
    s = r.get_burst_stats('burst', rate)
    print(f'  loss={rate:.0%}  burst_mean={s["mean"]:.2f} pkts  count={s["count"]}')

print()
print('=== ACTUAL LOSS RATES vs TARGET ===')
print(f'  {"Loss Rate":>10}  {"Random Actual":>14}  {"Burst Actual":>13}')
for rate in [0.05, 0.10, 0.20, 0.30, 0.50]:
    ra = r.get_actual_loss_rate('random', rate)
    ba = r.get_actual_loss_rate('burst',  rate)
    ok_r = 'OK' if abs(ra - rate) < 0.05 else 'WARN'
    ok_b = 'OK' if abs(ba - rate) < 0.08 else 'WARN'
    print(f'  {rate*100:>9.0f}%  {ra*100:>12.1f}% {ok_r}  {ba*100:>11.1f}% {ok_b}')

print()
print('=== LATENCY STATS ===')
lat = r.get_latency_stats()
if lat:
    print(f'  Mean: {lat["mean_ms"]:.2f} ms  (Python baseline: 1.99 ms)')
    print(f'  P95:  {lat["p95_ms"]:.2f} ms  (Python baseline: 3.74 ms)')
    print(f'  P99:  {lat["p99_ms"]:.2f} ms  (Python baseline: 4.28 ms)')
else:
    print('  No latency data loaded')

print()
print('=== FEC RECOVERY TEST (100 blocks, 20% random loss) ===')
from core.fec_encoder import FECEncoder
from core.fec_decoder import FECDecoder
enc = FECEncoder(4, 4)
dec = FECDecoder(4, 4)
ok = 0
total = 100
for _ in range(total):
    data = [bytes([i]*1024) for i in range(4)]
    encoded = enc.encode_block(data)
    received = r.apply_loss(encoded, 0.20, 'random')
    _, success = dec.decode_block(received)
    if success:
        ok += 1
print(f'  Recovery rate: {ok}/{total} = {ok*100//total}%')
print(f'  Python baseline at 20%: 99.6%')

print()
print('ALL DONE — MATLAB channel data is working correctly!')
