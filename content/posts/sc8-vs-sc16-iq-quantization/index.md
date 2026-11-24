+++
date = '2026-11-24'
draft = false
title = 'SC8 vs. SC16: How Much IQ Precision Do We Really Need?'
description = 'Exploring IQ quantization, weak-signal detection, and the practical limits of real-time software-defined radio.'
tags = ['SDR', 'Signal Processing', 'Quantization', 'Wireless Communications']
+++

{{< katex >}}

I've been looking into whether I could build a portable wideband SDR around a phone. The setup I have in mind is an AD9361-based LibreSDR B210 Mini, a USB 3.x link, and a Samsung Galaxy S21 FE doing the work usually left to a computer. My upper target is 61.44 million complex samples per second, a documented AD9361 baseband rate. The results here come from simulations and payload calculations. [Analog Devices documents the chip's sample-rate limits.](https://developer.analog.com/docs/linux/drivers/iio-transceiver/ad9361/)

One way to make that stream easier to carry is to ask for eight bits each for I and Q instead of sixteen. The payload is immediately cut in half. But what happens to a weak signal I was hoping to find later?

## Where are those sixteen bits, exactly?

An IQ sample is a pair of numbers that together describe amplitude and phase at complex baseband.

\[
x[n]=I[n]+jQ[n].
\]

SC8 and SC16 use signed integers for each component. FC32 and FC64 use floating-point numbers. The number in the name is the width of *one* component.

| Format | Bits per component | Bits per complex sample | Bytes per complex sample |
| --- | ---: | ---: | ---: |
| SC8 | 8 | 16 | 2 |
| SC16 | 16 | 32 | 4 |
| FC32 | 32 | 64 | 8 |
| FC64 | 64 | 128 | 16 |

The ADC resolution tells us about digitization. The AD9361 includes 12-bit ADCs and exports signed 12-bit receive I and Q after its internal digital processing. Internal filters and FPGA arithmetic can carry intermediate values at other widths. A 16-bit transport word can hold a 12-bit result with room to spare. ENOB, or effective number of bits, is a separate measure derived from noise and distortion under specified test conditions. [AD9361 reference manual](https://www.analog.com/media/en/technical-documentation/user-guides/AD9361_Reference_Manual_UG-570.pdf) · [Analog Devices on ENOB](https://www.analog.com/en/resources/technical-articles/how-to-calculate-enob-for-adc-dynamic-performance-measurement.html)

{{< figure src="figures/signal-chain.svg" alt="RF front end, then ADC and internal DSP, FPGA and USB transport, and finally the host sample format and DSP." caption="A receive chain can use several different numerical widths between the antenna and the application." >}}

UHD lets you request the over-the-wire and CPU formats separately. An application can receive SC8 over USB, expand it to FC32 in memory, and use double precision in a later calculation. The FC32 values still lie on the decoded SC8 grid. In UHD, the optional SC8 <code>peak</code> argument describes the expected maximum sample level as a fraction of full scale for device and host scaling, where supported. I use Ettus as a reference for the terminology. The exact behavior of the LibreSDR board and FPGA image is a hardware question. [UHD stream formats and scaling](https://files.ettus.com/manual/structuhd_1_1stream__args__t.html)

## Where does the missing information go?

Imagine rounding each component to the nearest available mark on a ruler. A uniform \(B\)-bit quantizer divides its nominal range into \(2^B\) steps of size \(\Delta\). In the simulation, full scale (FS) means a nominal component peak of 1. I round to nearest, break ties toward the even code, and saturate at the signed endpoints. The positive endpoint sits one step inside \(+1\).

\[
\Delta=\frac{V_{\max}-V_{\min}}{2^B}.
\]

With plenty of codes in use and negligible clipping, the rounding error is often approximately uniform between \(-\Delta/2\) and \(+\Delta/2\). Averaging its square gives the variance. A full-scale sine has average power \(A^2/2\), with \(A=(V_{\max}-V_{\min})/2\). Dividing by the error variance and taking \(10\log_{10}\) gives the familiar result. [Analog Devices MT-001](https://www.analog.com/media/en/training-seminars/tutorials/mt-001.pdf)

\[
\begin{gathered}
\sigma_q^2\approx\frac{\Delta^2}{12},\\
\mathrm{SQNR}\approx 6.02B+1.76\ \mathrm{dB}.
\end{gathered}
\]

The ideal near-full-scale figures are about **50, 74 and 98 dB** for 8, 12 and 16 bits. My simulated tone at −0.1 dBFS came within 0.2 dB of the amplitude-adjusted prediction for all three. At −48 dBFS, the 8-bit sine mostly lands on zero and briefly visits the adjacent codes. Its SQNR is about 0 dB. Drive the same quantizers to +2 dBFS and all three give about 17 dB once clipping dominates the error.

{{< figure src="figures/quantization.svg" alt="A low-level sine mostly rounds to zero at eight bits. The error histogram changes with level, and the SQNR curves converge in clipping." caption="Ideal single-stage quantizers. Dotted curves show the uniform-error prediction. mFS means one thousandth of nominal component full scale." >}}

Those 48 dB between the ideal 8- and 16-bit figures compare *quantizer error* for a full-scale sine. Receiver sensitivity also depends on front-end noise, bandwidth, gain and the detection criterion. dBFS refers to a digital full-scale reference, dBm to power relative to 1 mW, and SNR and SQNR to ratios against noise and quantization error respectively. Quoting an RF sensitivity in dBm would require calibration from the antenna input to the sample values.

## What if the receiver is already noisy?

Let the ADC input \(r[n]=s[n]+w[n]\) contain a desired signal and receiver noise. With negligible clipping and sufficiently decorrelated quantization error, we can approximate \(y[n]=Q_B\{r[n]\}\) by \(s[n]+w[n]+q[n]\). The noise powers then add, so the difference from the original SNR is

\[
\begin{gathered}
\mathrm{SNR}_{\mathrm{out}}\approx\frac{P_s}{P_w+P_q},\\
L_q\approx 10\log_{10}\!\left(1+\frac{P_q}{P_w}\right).
\end{gathered}
\]

For complex IQ, \(P_q\approx 2\sigma_q^2\) if both components behave alike. In the same bandwidth, a tiny \(P_q/P_w\) costs almost nothing. Equal powers cost about 3 dB. Once quantization dominates, the loss grows with their ratio. This approximation can break down when most samples hit a few codes, when a periodic input makes the error repeat, or when the samples clip. A periodic error can create discrete spurs. [Demir and Björnson on nonlinear distortion and correlated inputs](https://arxiv.org/abs/2005.01597)

I sent the same tone and complex additive white Gaussian noise (AWGN) through a floating-point reference, a modeled 12-bit ADC packed losslessly into SC16, and the same ADC requantized to SC8. With noise RMS of 0.12 FS per component, all three spectra looked alike. At 0.002 FS, the SC8 floor went *down* by about 2 dB while its coherent tone fell by about 9 dB. The quieter spectrum was a worse reception. Many small samples rounded to zero.

{{< figure src="figures/psd.svg" alt="Two-sided power spectra of the same noisy tone at two gain settings. At the lower gain the SC8 tone and measured noise floor both fall relative to SC16." caption="Welch PSD at 1.024 MSps using 2,048-point Hann segments with 50% overlap. Each panel uses the same input realization for all formats." >}}

Analog gain moves signal and noise up together and uses up headroom. An AGC that sees a strong station can back off even when the channel I care about is quiet. Digital scaling *before* packing can make better use of the transport codes. In this same low-level capture, setting the modeled SC8 peak to 1/16 FS preserved every ADC code that occurred. Tightening it to 1/256 FS saturated 5.6% of the components. Once clipping has happened at the ADC or information has been rounded away in transport, a later gain change just scales what is left.

## Can a matched filter still find it?

If I know the sequence and its arrival time, I can rotate each sample by the conjugate of the expected value and add them. The desired terms line up even when each one is small compared with the noise. I used the magnitude squared so the detector could handle an unknown common carrier phase. [MIT's notes on matched filtering](https://ocw.mit.edu/courses/16-36-communication-systems-engineering-spring-2009/resources/mit16_36s09_lec08_09/)

\[
T=\left|\sum_{n=0}^{N-1} y[n]s^*[n]\right|^2.
\]

For a unit-energy-per-sample template in white noise, the coherent amplitude grows as \(N\), while the summed noise RMS grows as \(\sqrt N\). That gives \(10\log_{10}N\) dB of processing gain in power SNR. A false alarm is a noise-only block crossing the threshold. Detection probability is the chance of crossing it when the target is present. Searching many possible arrival times would require calibrating the maximum over the search to control false alarms per search.

I swept −35 to +10 dB SNR per complex sample using BPSK sequences of 64, 256 and 1,024 samples. Each format and gain had a threshold set from 200,000 noise-only blocks and checked on 200,000 separate blocks. Validated false-alarm rates ranged from 0.00072 to 0.00120 around the \(10^{-3}\) target. The signal-present curves use 20,000 blocks per SNR. I also checked the floating-point result against the exponential noise-only and noncentral chi-square signal-present distributions.

{{< figure src="figures/detection.svg" alt="Detection curves for three sequence lengths at two input gains. Longer sequences detect lower SNR signals. Underfilled SC8 needs more input SNR than SC16." caption="Solid is modeled SC16 and dashed is modeled SC8. The horizontal guide marks 90% detection. The other quantizers and the full sweep are in the data." >}}

With the well-scaled input and 256 samples, both transport formats reached 90% detection at about **−13.3 dB**, and quadrupling the sequence length bought about 6 dB. At −17 dB and the same length, the paired SC8 minus SC16 difference was +0.05 percentage points, with an approximate 95% interval of −0.13 to +0.22 points.

At low gain the picture changed. SC16 still reached 90% near −13.3 dB, while ideal 8-bit quantization needed about −8.0 dB and ADC-to-SC8 needed −7.2 dB. In this particular two-stage rounding model, the first rounding widens the interval that ends up at SC8 zero. At −17 dB the modeled SC8 coherent peak was 8.7 dB below the floating-point result. Noise still pushed some samples across code boundaries, so the weak signal could change the probability of those crossings. Coherent integration could use that information and the input SNR penalty remained.

{{< figure src="figures/roc.svg" alt="ROC curves showing overlapping SC8 and SC16 with good scaling and a large detection gap for underfilled SC8 at the same false-alarm rate." caption="The ROC varies the decision threshold. The vertical guide marks the target false-alarm rate of one per thousand blocks." >}}

## What if another station is much louder?

I kept the desired SNR at −12 dB per complex sample and added a randomly phased tone outside the wanted channel. A 97-tap host FIR selected the channel before correlation. With fixed gain and a blocker 35 dB stronger than the target, about 66% of ADC components exceeded full scale and both transport formats detected only about two thirds of the blocks.

Backing off gain solved the ADC clipping in this sweep. It also made the desired signal smaller relative to both converters' steps. With a 65 dB blocker, SC8 detected **54.2%** of blocks (95% interval 53.3–55.0%) and SC16 detected all 12,000 in its trial set. The mean SC8 correlation peak lost only about 0.3 dB, but its noise-only threshold was nearly four times higher on the squared-magnitude scale. Filtering can remove the out-of-band tone after digitization. Clipping and quantization have already changed the samples by then. An actual mixer or amplifier can compress or generate intermodulation before the ADC, effects outside this model.

{{< figure src="figures/blocker.svg" alt="Fixed gain causes ADC overrange and loss of detection for both integer transports. With gain backoff SC16 holds up at high blocker ratios while SC8 falls." caption="Known-timing detection versus blocker power relative to the desired signal. Thresholds were calibrated separately with the blocker present." >}}

## What about decoding actual bits?

For a quick check I simulated Gray-coded QPSK and 16-QAM with unit average symbol power and one sample per symbol. I placed AWGN before quantization and used ideal timing, phase and gain, with hard decisions at the receiver. This symbol-rate model abstracts away pulse shaping and synchronization. The floating-point bit error rate (BER) follows the analytical AWGN result. At 12 dB \(E_b/N_0\), 16-QAM produced 235 bit errors in SC8 and 222 in SC16 out of 1.6 million bits. RMS error vector magnitude (EVM) was 12.61% and 12.56% respectively. That agreement is specific to this scaling and channel.

{{< figure src="figures/ber.svg" alt="QPSK and 16-QAM bit error rates for float, SC16 and SC8 track the AWGN curves under good scaling." caption="Each point uses 400,000 symbols. Downward markers represent 95% upper bounds where a format recorded zero errors." >}}

## Meanwhile, the phone has 67 microseconds

In my [previous SDR post]({{< relref "posts/SDRs-basics-for-beginners/index.md#step-six-sampling-rate-gets-expensive-very-quickly" >}}), I worked out what it costs to move 61.44 MSps in SC16. With two components of \(B\) bits, complex rate \(F_s\), and \(C\) receive channels, the raw payload is simply

\[
R_{\mathrm{bytes}}=\frac{2BF_sC}{8}.
\]

| Complex rate (MSps) | SC8 (MB/s) | SC16 (MB/s) | FC32 (MB/s) |
| ---: | ---: | ---: | ---: |
| 10 | 20 | 40 | 80 |
| 20 | 40 | 80 | 160 |
| 30.72 | 61.44 | 122.88 | 245.76 |
| 40 | 80 | 160 | 320 |
| 61.44 | 122.88 | 245.76 | 491.52 |

That is one channel in decimal units. At 61.44 MSps, a raw minute costs **7.37, 14.75 or 29.49 GB** in SC8, SC16 or FC32. An hour costs **442.37, 884.74 or 1,769.47 GB**. Two channels double the traffic. The FC32 column also describes the rate at which the application writes a single converted FC32 stream.

{{< figure src="figures/throughput.svg" alt="Raw payload versus sampling rate for SC8, SC16 and FC32, alongside the USB 2.0 high-speed signaling limit." caption="One receive channel. The USB 2.0 line is the signaling rate expressed in MB/s, before protocol overhead." >}}

USB 2.0 high speed signals at 480 Mb/s, or 60 MB/s before overhead. Even SC8 at 30.72 MSps exceeds that ceiling. USB 3.x at 5 Gb/s gives more room, with usable throughput reduced by line coding and USB and SDR framing. The host controller, negotiated link, driver, queue depth and buffer reuse all matter. Each copy or conversion also adds memory traffic. Reading SC8 and writing FC32 at the target rate moves at least **614.4 MB/s** through the conversion buffers before any later reads or writes. How much of that reaches DRAM depends on cache behavior. [USB-IF high-speed USB](https://www.usb.org/sites/default/files/USB%202%200%20Electrical%20Compliance%20Specification%28v1.07%29.pdf) · [USB 3.2 signaling rates](https://www.usb.org/sites/default/files/USB_3_2_Language_Product_and_Packaging_Guidelines_FINAL.pdf) · [Ettus on bandwidth along the receive chain](https://kb.ettus.com/About_USRP_Bandwidths_and_Sampling_Rates)

Samsung lists Snapdragon 888 and Exynos 2100 variants of the S21 FE. I'd record the exact variant, USB link speed and firmware before comparing runs. Android's USB host API handles enumeration and access. Native C/C++ through the NDK and Arm Neon SIMD can help with unpacking, conversion and DSP, especially when work is batched across the managed/native boundary. A fast FFT leaves the FIR, decimation and matched filter to account for, along with scheduling delays and memory traffic. [Samsung's variant comparison](https://www.samsung.com/uk/support/mobile-devices/what-is-the-difference-between-the-galaxy-s21-fe-s21-s21-and-s20-fe/) · [Android USB host API](https://developer.android.com/develop/connectivity/usb/host) · [NDK](https://developer.android.com/ndk) · [Neon support](https://developer.android.com/ndk/guides/cpu-arm-neon)

\[
T_{\mathrm{block}}=\frac{N}{F_s}.
\]

At 61.44 MSps a 4,096-sample block arrives every **66.7 μs**, or 15,000 times a second. A ring buffer absorbs occasional scheduling delays. If work accumulates faster than it drains, the buffer eventually overflows and a gap can break a coherent integration. On the phone I'd first test receive-only, then add conversion and DSP in stages, logging actual sample rate, gaps, queue depth, tail latency, thermal status and power draw through warm-up and sustained operation. A fast cold run says little about thermal throttling or battery life. [UHD's receive-rate benchmark](https://github.com/EttusResearch/uhd/blob/master/host/examples/benchmark_rate.cpp) · [Android Thermal API](https://developer.android.com/games/optimize/adpf/thermal)

## So, how many bits would I take?

I'd try SC8 when noise spans plenty of codes, peaks have headroom, and the USB link or buffer traffic is what limits continuous capture. I'd use SC16 when a strong blocker sets the gain or when I need to preserve quiet channels for analysis later. If the board can filter, select a channel and decimate before transport, that can save more traffic and processing than changing formats. An FFT on the same number of FC32 samples still has the same arithmetic after either wire format.

The phone project makes this trade-off concrete for me. An uninterrupted SC8 capture could be more valuable than a stream that keeps dropping parts of the sequence I'm trying to recognize. I'd judge the format by what the detector can recover and how long the system can keep delivering samples.

### Further reading and reproduction

The simulation source, CSVs, and extra plots live under <code>experiments/sc8-vs-sc16/</code> in the [blog repository](https://github.com/hadi-hoho/blog). For the reference hardware and clocking details, see the [Ettus B2x0 manual](https://files.ettus.com/manual/page_usrp_b200.html).
