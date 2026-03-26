% =========================================================================
%  generate_fec_traffic_data.m   (v2 — Fixed)
%  FEC for 5G URLLC — Real 5G Channel Data Generator
%  Run on MATLAB Online: https://matlab.mathworks.com
% =========================================================================
%  Uses Gilbert-Elliott Markov chain channel model (directly calibrated).
%  No 5G Toolbox required. Produces identical CSV format to v1.
%
%  Generates two channel types:
%    - "random" : near-i.i.d. (GE with very short bursts, avg len ≈ 1.1 pkts)
%    - "burst"  : correlated  (GE with avg burst ≈ 3.3 pkts, matching Python)
%
%  Output CSV files (download from MATLAB Drive after running):
%    loss_vectors.csv        — binary loss mask per FEC block (8 packets each)
%    latency_samples.csv     — per-packet delay in milliseconds
%    channel_summary.csv     — per-trial aggregate statistics
%    validation_plots.png    — QC comparison against Python baseline
%
%  Runtime: ~1-2 minutes on MATLAB Online
% =========================================================================

clear; clc; close all;

fprintf('=================================================================\n');
fprintf(' FEC 5G Traffic Generator v2 — MATLAB Online\n');
fprintf(' Time: %s\n', datestr(now));
fprintf('=================================================================\n\n');

% ── Simulation Parameters ─────────────────────────────────────────────────
N_DATA    = 4;       % FEC data packets per block
N_PARITY  = 4;       % FEC parity packets per block
N_TOTAL   = 8;       % total packets per FEC block
NUM_BLOCKS  = 50;    % FEC blocks per trial
NUM_TRIALS  = 5;     % independent trials per (loss_rate, model)

BASE_DELAY_MS = 2.0; % mean propagation delay (matches Python ChannelModel)
JITTER_STD_MS = 1.0; % delay standard deviation (matches Python)

loss_rates = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50];
N_RATES    = numel(loss_rates);

% Gilbert–Elliott model parameters
%   Random channel: p_bg = 0.99  →  avg burst len ≈ 1/0.99 ≈ 1.01 (near i.i.d.)
%   Burst  channel: p_bg = 0.30  →  avg burst len ≈ 1/0.30 ≈ 3.33  (matches Python GE)
%
%   Steady-state bad-state probability: pi_bad = p_gb / (p_gb + p_bg)
%   Calibration: p_gb = loss_rate * p_bg / (1 - loss_rate)
%   (both states: p_loss_good=0, p_loss_bad=1 for simplicity)

GE_CONFIGS = struct( ...
    'name',    {'random', 'burst'}, ...
    'p_bg',    {0.99,      0.30},  ...
    'label',   {'random',  'burst'} ...
);
N_MODELS = numel(GE_CONFIGS);

fprintf('[CHANNEL MODEL] Gilbert-Elliott Markov Chain\n');
fprintf('  Random channel: p_bg=%.2f  avg_burst=%.2f pkts  (near i.i.d.)\n', ...
        GE_CONFIGS(1).p_bg, 1/GE_CONFIGS(1).p_bg);
fprintf('  Burst  channel: p_bg=%.2f  avg_burst=%.2f pkts  (vehicular fading)\n', ...
        GE_CONFIGS(2).p_bg, 1/GE_CONFIGS(2).p_bg);

fprintf('\n[PARAMETERS]\n');
fprintf('  FEC block      : k=%d data + r=%d parity = %d total\n', N_DATA, N_PARITY, N_TOTAL);
fprintf('  Blocks/trial   : %d  |  Trials/rate: %d\n', NUM_BLOCKS, NUM_TRIALS);
fprintf('  Loss rates     : %s\n', mat2str(loss_rates));
fprintf('  Total blocks   : %d\n\n', N_MODELS * N_RATES * NUM_TRIALS * NUM_BLOCKS);


% =========================================================================
% STEP 1: Calibrate GE parameters for each target loss rate
% =========================================================================
fprintf('[STEP 1] Calibrating GE parameters...\n');

% p_gb_table(m, r) = transition probability GOOD→BAD for model m, loss rate r
p_gb_table = zeros(N_MODELS, N_RATES);

for m = 1:N_MODELS
    p_bg = GE_CONFIGS(m).p_bg;
    fprintf('  %s (p_bg=%.2f):\n', GE_CONFIGS(m).name, p_bg);
    for r = 1:N_RATES
        lr = loss_rates(r);
        if lr == 0
            p_gb_table(m, r) = 0;  % never enter bad state
        else
            % Solve: pi_bad = p_gb / (p_gb + p_bg) = lr
            %        p_gb = lr * p_bg / (1 - lr)
            p_gb = lr * p_bg / (1 - lr);
            p_gb_table(m, r) = p_gb;
        end
        fprintf('    loss=%4.0f%%  p_gb=%.4f  pi_bad_theory=%.3f\n', ...
                lr*100, p_gb_table(m,r), ...
                p_gb_table(m,r)/(p_gb_table(m,r)+GE_CONFIGS(m).p_bg));
    end
end
fprintf('  [OK] Calibration complete.\n\n');


% =========================================================================
% STEP 2: Main Simulation Loop
% =========================================================================
fprintf('[STEP 2] Running simulation...\n\n');

% Pre-allocate
TOTAL_ROWS_LOSS = N_MODELS * N_RATES * NUM_TRIALS * NUM_BLOCKS;
TOTAL_ROWS_LAT  = TOTAL_ROWS_LOSS * N_TOTAL;
TOTAL_ROWS_SUM  = N_MODELS * N_RATES * NUM_TRIALS;

all_loss_rows = zeros(TOTAL_ROWS_LOSS, N_TOTAL + 4);  % +4: model_id,rate,trial,block
all_lat_rows  = zeros(TOTAL_ROWS_LAT,  3);             % pkt_global, block_id, delay_ms
all_sum_rows  = zeros(TOTAL_ROWS_SUM,  8);

loss_ptr = 0;
lat_ptr  = 0;
sum_ptr  = 0;

for m = 1:N_MODELS
    p_bg = GE_CONFIGS(m).p_bg;

    for r = 1:N_RATES
        p_gb   = p_gb_table(m, r);
        lr     = loss_rates(r);

        for t = 1:NUM_TRIALS
            rng(m * 10000 + r * 100 + t);  % reproducible seed

            trial_loss_accum = 0;
            burst_lengths    = [];
            trial_delays     = [];

            ge_state = 1;  % 1=GOOD, 2=BAD — reset per trial

            for blk = 1:NUM_BLOCKS
                loss_mask = zeros(1, N_TOTAL);
                delays    = zeros(1, N_TOTAL);

                for pkt = 1:N_TOTAL
                    % ── GE state transition ──────────────────────────────
                    if ge_state == 1   % GOOD state
                        loss_mask(pkt) = 1;  % received
                        if rand < p_gb
                            ge_state = 2;
                        end
                    else               % BAD state
                        loss_mask(pkt) = 0;  % lost
                        if rand < p_bg
                            ge_state = 1;
                        end
                    end

                    % ── Packet delay ─────────────────────────────────────
                    jitter    = randn * JITTER_STD_MS;
                    delay_ms  = BASE_DELAY_MS + jitter;
                    if m == 2  % burst model: add extra multipath spread
                        delay_ms = delay_ms + abs(randn) * 0.5;
                    end
                    delays(pkt) = max(0, delay_ms);
                end

                % Accumulate trial statistics
                trial_loss_accum = trial_loss_accum + sum(1 - loss_mask);
                trial_delays     = [trial_delays, delays]; %#ok<AGROW>

                % Burst length analysis
                in_burst = false;
                cur_len  = 0;
                for i = 1:N_TOTAL
                    if loss_mask(i) == 0
                        cur_len  = cur_len + 1;
                        in_burst = true;
                    else
                        if in_burst && cur_len > 0
                            burst_lengths(end+1) = cur_len; %#ok<AGROW>
                        end
                        in_burst = false;
                        cur_len  = 0;
                    end
                end
                if in_burst && cur_len > 0
                    burst_lengths(end+1) = cur_len; %#ok<AGROW>
                end

                % Store loss row
                loss_ptr = loss_ptr + 1;
                block_global = (m-1)*N_RATES*NUM_TRIALS*NUM_BLOCKS + ...
                               (r-1)*NUM_TRIALS*NUM_BLOCKS + ...
                               (t-1)*NUM_BLOCKS + blk;
                all_loss_rows(loss_ptr, :) = [m, lr, t, blk, loss_mask];

                % Store latency rows
                for pkt = 1:N_TOTAL
                    lat_ptr = lat_ptr + 1;
                    pkt_global = (loss_ptr - 1) * N_TOTAL + pkt;
                    all_lat_rows(lat_ptr, :) = [pkt_global, block_global, delays(pkt)];
                end
            end  % blk

            % Summary statistics for this trial
            actual_plr = trial_loss_accum / (NUM_BLOCKS * N_TOTAL);
            mean_burst = 0;
            if ~isempty(burst_lengths)
                mean_burst = mean(burst_lengths);
            end

            sum_ptr = sum_ptr + 1;
            all_sum_rows(sum_ptr, :) = [
                lr, t, actual_plr, mean_burst, ...
                mean(trial_delays), std(trial_delays), ...
                m, GE_CONFIGS(m).p_bg
            ];

        end  % trial

        % Print progress for this (model, loss_rate)
        rows_this = (r-1)*NUM_TRIALS + (1:NUM_TRIALS);
        rows_range = (m-1)*N_RATES*NUM_TRIALS + rows_this;
        actual_plrs   = all_sum_rows(rows_range - (m-1)*N_RATES*NUM_TRIALS + (sum_ptr - NUM_TRIALS + 1 - 1), 3);
        mean_bursts_v = all_sum_rows(rows_range - (m-1)*N_RATES*NUM_TRIALS + (sum_ptr - NUM_TRIALS + 1 - 1), 4);

        % simpler: just grab last NUM_TRIALS summary rows
        s_start = sum_ptr - NUM_TRIALS + 1;
        s_end   = sum_ptr;
        actual_plrs_v   = all_sum_rows(s_start:s_end, 3);
        mean_bursts_v   = all_sum_rows(s_start:s_end, 4);

        fprintf('  [%s] loss=%4.0f%%  actual=%5.1f±%.1f%%  burst_len=%.2f  target=%5.1f%%\n', ...
            GE_CONFIGS(m).name, lr*100, ...
            mean(actual_plrs_v)*100, std(actual_plrs_v)*100, ...
            mean(mean_bursts_v), lr*100);

    end  % rate
    fprintf('\n');
end  % model

fprintf('  [OK] Simulation complete. %d blocks generated.\n\n', loss_ptr);


% =========================================================================
% STEP 3: Write CSV Files
% =========================================================================
fprintf('[STEP 3] Writing CSV output files...\n');

% ── loss_vectors.csv ─────────────────────────────────────────────────────
fid = fopen('loss_vectors.csv', 'w');
fprintf(fid, '# FEC Loss Vectors | model=GE | generated by generate_fec_traffic_data.m v2\n');
fprintf(fid, 'model,loss_rate_target,trial,block,D0,D1,D2,D3,P0,P1,P2,P3\n');
model_names = {'random', 'burst'};
for i = 1:loss_ptr
    row   = all_loss_rows(i, :);
    m_id  = row(1);  lr = row(2);  t = row(3);  blk = row(4);
    mask  = row(5:12);
    fprintf(fid, '%s,%.2f,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n', ...
        model_names{m_id}, lr, t, blk, ...
        mask(1),mask(2),mask(3),mask(4),mask(5),mask(6),mask(7),mask(8));
end
fclose(fid);
fprintf('  Written: loss_vectors.csv  (%d data rows)\n', loss_ptr);

% ── latency_samples.csv ──────────────────────────────────────────────────
fid = fopen('latency_samples.csv', 'w');
fprintf(fid, '# FEC Latency Samples | generated by generate_fec_traffic_data.m v2\n');
fprintf(fid, 'packet_global_idx,block_id,delay_ms\n');
for i = 1:lat_ptr
    fprintf(fid, '%d,%d,%.4f\n', all_lat_rows(i,1), all_lat_rows(i,2), all_lat_rows(i,3));
end
fclose(fid);
fprintf('  Written: latency_samples.csv  (%d rows)\n', lat_ptr);

% ── channel_summary.csv ──────────────────────────────────────────────────
fid = fopen('channel_summary.csv', 'w');
fprintf(fid, '# FEC Channel Summary | generated by generate_fec_traffic_data.m v2\n');
fprintf(fid, 'loss_rate_target,trial,actual_loss_rate,burst_mean_length,');
fprintf(fid, 'delay_mean_ms,delay_std_ms,channel_model_id,p_bg\n');
for i = 1:sum_ptr
    r = all_sum_rows(i,:);
    fprintf(fid, '%.2f,%d,%.4f,%.4f,%.4f,%.4f,%d,%.4f\n', ...
        r(1),r(2),r(3),r(4),r(5),r(6),r(7),r(8));
end
fclose(fid);
fprintf('  Written: channel_summary.csv  (%d rows)\n', sum_ptr);

save('fec_traffic_data.mat');
fprintf('  Written: fec_traffic_data.mat\n\n');


% =========================================================================
% STEP 4: Validation Plots
% =========================================================================
fprintf('[STEP 4] Generating validation plots...\n');

% Python baseline from experiment_results.json
py_loss_rates  = [0.00,0.05,0.10,0.15,0.20,0.25,0.30,0.40,0.50];
py_random_plr  = [0.000,0.056,0.112,0.146,0.199,0.233,0.280,0.389,0.497];
py_burst_plr   = [0.000,0.031,0.097,0.140,0.236,0.209,0.316,0.439,0.477];

% Compute MATLAB mean PLR per (model, rate) from summary rows
matlab_plr = zeros(N_MODELS, N_RATES);
for m = 1:N_MODELS
    for r = 1:N_RATES
        idx = all_sum_rows(:,1) == loss_rates(r) & all_sum_rows(:,7) == m;
        matlab_plr(m, r) = mean(all_sum_rows(idx, 3));
    end
end

% Latency data: split by model
random_lat = all_lat_rows(all_lat_rows(:,3) > 0 & ...
    all_lat_rows(:,2) <= N_RATES*NUM_TRIALS*NUM_BLOCKS, 3);
burst_lat  = all_lat_rows(all_lat_rows(:,3) > 0 & ...
    all_lat_rows(:,2) >  N_RATES*NUM_TRIALS*NUM_BLOCKS, 3);
if isempty(random_lat), random_lat = all_lat_rows(all_lat_rows(:,3)>0, 3); end
if isempty(burst_lat),  burst_lat  = random_lat; end

fig = figure('Position', [50, 50, 1100, 800]);

% ── Plot 1: Actual vs Target PLR ─────────────────────────────────────────
subplot(2, 2, 1);
plot(py_loss_rates*100, matlab_plr(1,:)*100, 'b-o', 'LineWidth', 2, ...
     'MarkerFaceColor','b', 'DisplayName', 'MATLAB GE-Random'); hold on;
plot(py_loss_rates*100, matlab_plr(2,:)*100, 'r-s', 'LineWidth', 2, ...
     'MarkerFaceColor','r', 'DisplayName', 'MATLAB GE-Burst');
plot(py_loss_rates*100, py_random_plr*100,   'b--',  'LineWidth', 1.2, ...
     'DisplayName', 'Python Bernoulli');
plot(py_loss_rates*100, py_burst_plr*100,    'r--',  'LineWidth', 1.2, ...
     'DisplayName', 'Python GE-Burst');
plot([0 50],[0 50], 'k:', 'LineWidth', 1, 'DisplayName', 'Ideal (y=x)');
hold off;
xlabel('Target Loss Rate (%)'); ylabel('Actual Measured PLR (%)');
title('PLR Calibration: MATLAB vs Python Baseline');
legend('Location','northwest','FontSize',7);
grid on;

% ── Plot 2: Latency CDF ──────────────────────────────────────────────────
subplot(2, 2, 2);
cdfplot(random_lat); hold on;
cdfplot(burst_lat);
xline(2.0, 'k--', 'Python mean', 'LabelHorizontalAlignment','right', 'FontSize', 8);
xline(4.28, 'g--', 'Python P99', 'LabelHorizontalAlignment','right', 'FontSize', 8);
hold off;
xlabel('Delay (ms)'); ylabel('CDF');
title('Latency CDF: MATLAB GE-Random vs GE-Burst');
legend('GE-Random','GE-Burst','Location','southeast','FontSize',8);
grid on;

% ── Plot 3: PLR Comparison Bar Chart ─────────────────────────────────────
subplot(2, 2, 3);
x = 1:N_RATES;
bar_data = [py_random_plr; matlab_plr(1,:); py_burst_plr; matlab_plr(2,:)]';
bar(x, bar_data*100);
set(gca, 'XTick', x, ...
    'XTickLabel', arrayfun(@(r) sprintf('%.0f%%',r*100), loss_rates, 'UniformOutput', false));
xlabel('Channel Loss Rate'); ylabel('Effective PLR (%)');
title('PLR: Python vs MATLAB (all models)');
legend('Python Bernoulli','MATLAB GE-Random','Python GE-Burst','MATLAB GE-Burst', ...
       'Location','northwest','FontSize',7);
grid on;

% ── Plot 4: Burst Length Distribution (GE-Burst) ─────────────────────────
subplot(2, 2, 4);
% Extract burst lengths from burst model at 30% loss (most interesting)
target_r = 0.30;
m_burst = 2;
burst_mask_rows = all_loss_rows(all_loss_rows(:,7)==m_burst & ...
                                abs(all_loss_rows(:,2)-target_r)<0.001, 5:12);
if isempty(burst_mask_rows)
    % fallback: use any burst model rows
    burst_mask_rows = all_loss_rows(all_loss_rows(:,7)==m_burst, 5:12);
end
bl_all = [];
for i = 1:size(burst_mask_rows, 1)
    row    = burst_mask_rows(i,:);
    c      = 0;
    for j  = 1:numel(row)
        if row(j) == 0
            c = c + 1;
        else
            if c > 0, bl_all(end+1) = c; end %#ok<AGROW>
            c = 0;
        end
    end
    if c > 0, bl_all(end+1) = c; end %#ok<AGROW>
end
if ~isempty(bl_all)
    histogram(bl_all, 'BinEdges', 0.5:1:(max(bl_all)+0.5), 'Normalization','probability');
    xline(mean(bl_all), 'r--', sprintf('mean=%.2f', mean(bl_all)), 'LineWidth', 1.5);
    xline(1/GE_CONFIGS(2).p_bg, 'g--', sprintf('theory=%.2f', 1/GE_CONFIGS(2).p_bg), 'LineWidth', 1.5);
else
    text(0.5, 0.5, 'No bursts detected at this rate', 'Units','normalized','HorizontalAlignment','center');
end
xlabel('Burst Length (packets)'); ylabel('Probability');
title(sprintf('Burst Length Distribution (GE-Burst, loss=%.0f%%)', target_r*100));
legend('Observed','Mean','Theory','Location','northeast','FontSize',8);
grid on;

sgtitle({'MATLAB GE Channel Simulation — Validation', ...
         'vs Python Experiment Baseline (experiment\_results.json)'}, 'FontSize', 11);
saveas(fig, 'validation_plots.png');
fprintf('  Written: validation_plots.png\n\n');


% =========================================================================
% STEP 5: Print Validation Summary
% =========================================================================
fprintf('[STEP 5] Validation summary:\n\n');

fprintf('  %-40s  %10s  %10s\n', 'Check', 'MATLAB', 'Target');
fprintf('  %s\n', repmat('-', 1, 65));

% Check calibration accuracy
total_checks = 0; passed = 0;
for m = 1:N_MODELS
    for r = 2:N_RATES   % skip 0% loss
        err  = abs(matlab_plr(m,r) - loss_rates(r));
        ok   = err < 0.05;
        total_checks = total_checks + 1;
        if ok, passed = passed + 1; end
    end
end
fprintf('  %-40s  %10s  %10s\n', ...
    sprintf('PLR calibration accuracy (±5%%)'), ...
    sprintf('%d/%d PASS', passed, total_checks), ...
    sprintf('%d/%d', total_checks, total_checks));

% Burst length check
if ~isempty(bl_all)
    mean_bl = mean(bl_all);
    bl_ok   = mean_bl >= 2.5 && mean_bl <= 5.0;
    fprintf('  %-40s  %10.2f  %10s\n', ...
        'GE-Burst mean burst len (target 2.5-5)', mean_bl, '2.5-5.0');
end

% Latency check
lat_mean = mean(random_lat);
lat_ok   = lat_mean >= 1.5 && lat_mean <= 3.0;
fprintf('  %-40s  %10.2f  %10s\n', ...
    'GE-Random latency mean ms (target 1.5-3)', lat_mean, '1.5-3.0');

fprintf('\n');
fprintf('=================================================================\n');
fprintf(' DONE. Download these files from MATLAB Drive:\n');
fprintf('   loss_vectors.csv       — %d blocks\n', loss_ptr);
fprintf('   latency_samples.csv    — %d packet rows\n', lat_ptr);
fprintf('   channel_summary.csv    — %d trial rows\n', sum_ptr);
fprintf('   validation_plots.png   — QC charts\n');
fprintf('\n Copy to: fec_project/data/matlab_channel/\n');
fprintf('=================================================================\n');
