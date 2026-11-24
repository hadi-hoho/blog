# Reproducing the SC8 and SC16 experiments

These simulations support the Hugo post in [the page bundle](../../content/posts/sc8-vs-sc16-iq-quantization/index.md). The inputs are synthetic complex baseband. The equipment in the article motivates the model and the throughput calculation. The only measured timings are the optional local computer benchmarks below.

## Run the simulations

Use Python 3.11 or a later version supported by the pinned dependencies. From the repository root:

~~~text
python -m venv .venv
~~~

On Windows PowerShell:

~~~powershell
.\.venv\Scripts\python -m pip install -r experiments/sc8-vs-sc16/requirements.txt
.\.venv\Scripts\python experiments/sc8-vs-sc16/run_experiments.py
~~~

On Linux or macOS:

~~~sh
.venv/bin/python -m pip install -r experiments/sc8-vs-sc16/requirements.txt
.venv/bin/python experiments/sc8-vs-sc16/run_experiments.py
~~~

On the Intel Core i7-6500U used for this run, the full simulation took about 5½ minutes. Experiment C did most of the work. It keeps Monte Carlo working sets bounded by processing blocks of 512 trials. The full command writes CSVs and run metadata to <code>results/</code>, the article figures and featured PNG to the page bundle, and supplementary plots to <code>figures/</code> beside this README.

Use <code>--only a b</code> to regenerate selected tables without rendering figures, and <code>--plots-only</code> to render from saved tables. For a scratch run use both <code>--data path/to/results</code> and <code>--figures path/to/bundle/figures</code>. Supplemental figures go beside the results directory.

## Model and methods

Full scale is a nominal I or Q component peak of 1. A complex power of one is the reference for the PSD in dBFS/Hz. Each quantizer uses a signed grid with codes from −2^(B−1) to 2^(B−1)−1, round-to-nearest with ties to even, then componentwise saturation. For the nominal peak of 1, the step is 2^(1−B). The modeled ADC-to-SC16 path shifts a 12-bit signed code left by four and exactly recreates its normalized value on decode. It therefore agrees exactly with the standalone ideal 12-bit quantizer. SC8 requantizes that 12-bit grid. The usual SC8 setting is a peak of 1. A different peak P gives a step of P/128. These are explicit numerical conventions. Actual FPGA rounding, scaling and gain behavior depend on the board and image.

| Experiment | Inputs and outputs |
| --- | --- |
| A · Quantization | Phase-sampled real and complex sinusoids, with 8-, 12- and 16-bit SQNR across a peak-amplitude sweep. Waveforms and an error histogram expose underfill and clipping. |
| B · Spectrum and peak scaling | A tone in circular AWGN at 1.024 MSps, with identical waveforms across formats and two gains. Two-sided Welch estimates use 2,048-point Hann segments, 50% overlap, no detrending and density scaling. The table also compares three SC8 peak settings on the same underfilled 12-bit capture. |
| C · Detection | A fixed BPSK sequence with lengths 64, 256 and 1,024 from the same template. The target has a uniform random common phase in each trial and arrives at a known time. SNR is desired power divided by complex AWGN power per sample before scaling. At each of two gains, compare float, ideal 8-, 12- and 16-bit quantizers, and the two modeled ADC transport paths. |
| D · Blocker | One constant-amplitude tone at +0.375 cycles/sample with uniform random phase, swept from 0 to 70 dB relative to the desired signal. The 512-sample target uses repeated BPSK chips band-limited to ±0.09 cycles/sample with a DFT mask. Its pre-scaling SNR stays at −12 dB per complex sample. A 97-tap, 0.11 cycles/sample Kaiser FIR selects the channel on a periodic block. The code folds filtering into the template, which gives the same dot product as filtering both inputs. |
| E · Demodulation | Unit-average-power QPSK and Gray-coded 16-QAM, one complex sample per symbol at the decision instant, perfect timing, phase and gain. QPSK uses levels ±1/√2 with bit labels 0, 1 per axis. 16-QAM uses [−3, −1, +1, +3]/√10 with labels 00, 01, 11, 10 per axis. Hard slicing uses midpoint boundaries. Noise, transmitted bits and gain are shared across formats. EVM uses RMS error relative to the transmitted symbols after known gain correction. |
| Throughput | Integer-derived bytes per complex sample multiplied by complex sample rate. Rates and storage use decimal MB and GB, for one channel. |

C calibrates each threshold from 200,000 noise-only trials and validates it on 200,000 separate noise-only trials. There are 20,000 signal-present trials per SNR. The test is a strict exceedance, so a tie at the threshold stays a non-detection and can make the achieved false-alarm rate slightly conservative on quantized score grids. The ROC thresholds also come from the calibration set. Wilson intervals are conditional on the selected thresholds. The paired differences use approximate Bonferroni-Wilson bounds on the two discordant proportions. The 90% sensitivity estimates use linear interpolation in dB between adjacent sweep points. Their bounds come from interpolating the pointwise Wilson curves and describe signal-trial uncertainty conditional on the calibrated threshold. They omit calibration uncertainty and interpolation bias. Coherent gain is the phase-aligned mean correlation amplitude divided by the nominal floating-point signal-only value, expressed as 20 log10 of the amplitude ratio.

For C, if the template has unit power per sample and the complex AWGN power after scaling is P, the floating-point noise-only score is exponential with mean NP. The reference threshold is −NP ln(P_FA). Under the target, 2T/(NP) is noncentral chi-square with two degrees of freedom and noncentrality 2N times the linear input SNR. These enable independent checks on the Monte Carlo curves.

D uses 50,000 calibration blocks, 30,000 independent validation blocks and 12,000 target-present blocks for each interference setting. Noise-only here means target absent with the blocker present. One gain stays fixed. The other backs off against the combined blocker peak, target peak and a 4.5σ allowance for the noise. This is a fixed setting per condition, with no AGC dynamics. The ADC overrange fraction counts individual I and Q inputs beyond nominal full scale. The SC8 positive rail count additionally records values that round past code +127. The model isolates digitization and transport. Mixer compression, intermodulation, oscillator phase noise and other analog effects are outside its scope.

E uses 400,000 independent symbols per setting. Analytical BER is calculated by integrating Gaussian noise across all slicer boundaries and weighting symbol transitions by their bit errors. For 16-QAM, intervals use independent axes and keep together the two bits from one axis. Zero observed errors are drawn at a conservative one-sided 95% upper bound for the axis error rate, which also bounds BER.

## Saved data

| Files in <code>results/</code> | Contents |
| --- | --- |
| <code>a_sqnr.csv</code>, <code>a_waveforms.csv</code>, <code>a_error_pdf.csv</code> | SQNR and theory, waveform samples and histogram bins |
| <code>b_psd.csv</code>, <code>b_psd_summary.csv</code>, <code>b_peak_scaling.csv</code> | PSD bins, tone and noise summaries, scale and saturation comparison |
| <code>c_detection.csv</code>, <code>c_false_alarm.csv</code>, <code>c_roc.csv</code> | Detection probabilities and counts, independent threshold checks and ROC data |
| <code>c_required.csv</code>, <code>c_paired.csv</code>, <code>c_reference.npy</code> | 90% SNR crossings, paired SC8 and SC16 contrasts, and the BPSK reference |
| <code>d_blocker.csv</code>, <code>d_reference.csv</code> | Detection, gain, saturation, baseband reference and folded filter template |
| <code>e_demod.csv</code>, <code>e_constellation.csv</code> | BER, EVM, analytical values, confidence bounds and plotted IQ points |
| <code>throughput.csv</code>, <code>run_info.json</code> | Payload and storage calculations, seed, environment and trial counts |

The script asserts signed rails and ties-to-even behavior, checks that all 4,096 ADC codes fit in the modeled SC16 mapping, checks SQNR close to full scale and integrated Welch PSD against time-domain power, and compares the floating-point detector and BER with analytical results. Experiment D checks the blocker frequency and confirms that the folded FIR implementation is equivalent to the explicit correlation.

## Optional local host microbenchmark

With the same Python environment, run <code>python experiments/sc8-vs-sc16/benchmark_host.py --cpu "your processor model"</code>. It writes <code>host_benchmark.csv</code> and <code>host_benchmark_info.json</code> into <code>results/</code>. The checked-in timings are from an Intel Core i7-6500U at 2.50 GHz on Windows, with Python 3.11.9, NumPy 2.4.6 and SciPy 1.17.1.

The test uses 1,024, 4,096 and 16,384 complex samples per block, warms up each operation, and times 25 rounds of 100 calls. It works with synthetic buffers reused across calls. Conversions write a preallocated FC32 buffer. The SciPy FFT and FIR calls allocate output arrays. The decimator uses a 63-tap FIR with persistent history. The sliding matched filter uses a 256-tap template, overlap-save and a precomputed FFT of the kernel. FFTs use one worker. Reported p95 is across round means, so it smooths individual-call spikes.

At 4,096 samples the measured medians were about 8.8 μs for SC8 conversion, 10.3 μs for SC16 conversion, 63 μs for the FFT, 236 μs for FIR decimation and 147 μs for sliding matched filtering. These are warm, local kernel timings. They omit transport, queueing, concurrent processing and Android thermal behavior. For an Android run, measure received sample counts and discontinuities, time conversion and DSP per block, track queue occupancy and thermal state, and repeat with the device warm on both the receive-only and full paths.
