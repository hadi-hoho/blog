"""Run the IQ quantization experiments and save data and figures."""

import argparse
import csv
import json
import platform
import time
from pathlib import Path

import numpy as np
import scipy
from scipy import optimize, signal, special, stats


HERE = Path(__file__).resolve().parent
SEED = 20261124
PFA = 1e-3
LENGTHS = (64, 256, 1024)
SIGMAS = (0.12, 0.002)
FORMATS = ("float", "ideal8", "ideal12", "ideal16", "sc16", "sc8")
TRANSPORT = ("float", "sc16", "sc8")
BATCH = 512


def db(power_ratio):
    return 10 * np.log10(power_ratio)


def power(samples):
    return np.mean(np.abs(samples) ** 2, dtype=np.float64)


def quantize(samples, bits, peak=1.0):
    """Quantize real values to normalized two's-complement levels, ties to even."""
    codes = 2 ** (bits - 1)
    step = peak / codes
    output = np.multiply(samples, 1 / step)
    np.rint(output, out=output)
    np.clip(output, -codes, codes - 1, out=output)
    output *= step
    return output


def iq_quantize(samples, bits, peak=1.0):
    # Real and imaginary components are independent converter inputs.
    components = np.ascontiguousarray(samples).view(samples.real.dtype)
    return quantize(components, bits, peak).view(samples.dtype)


def receive(samples, formats=FORMATS, peak=1.0):
    adc = None
    for name in formats:
        if name == "float":
            yield name, samples
        elif name.startswith("ideal"):
            yield name, iq_quantize(samples, int(name[5:]))
        else:
            if adc is None:
                adc = iq_quantize(samples, 12)
            # SC16 shifts four bits and decodes to the same normalized ADC grid.
            yield name, adc if name == "sc16" else iq_quantize(adc, 8, peak)


def awgn(rng, shape):
    """Circular noise with unit expected complex power."""
    noise = rng.standard_normal((*shape, 2), dtype=np.float32)
    return noise.view(np.complex64).reshape(shape) * np.float32(1 / np.sqrt(2))


def interval(count, trials, confidence=0.95):
    return stats.binomtest(int(count), trials).proportion_ci(confidence, method="wilson")


def rate_fields(count, trials, prefix):
    ci = interval(count, trials)
    return {
        prefix: count / trials,
        f"{prefix}_count": count,
        f"{prefix}_n": trials,
        f"{prefix}_lo": ci.low,
        f"{prefix}_hi": ci.high,
    }


def threshold(scores, pfa=PFA):
    # Strict exceedance leaves at most floor(pfa * n) calibration false alarms.
    rank = len(scores) - int(np.floor(pfa * len(scores))) - 1
    return np.partition(scores, rank)[rank]


def write_csv(destination, name, rows):
    rows = iter(rows)
    first = next(rows)
    with (destination / f"{name}.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=first.keys())
        writer.writeheader()
        writer.writerow(first)
        writer.writerows(rows)


def validate_quantizer():
    points = np.array([-2, -1, -2.5 / 128, -1.5 / 128, -0.5 / 128, 0,
                       0.5 / 128, 1.5 / 128, 2.5 / 128, 1, 2])
    expected = np.array([-128, -128, -2, -2, 0, 0, 0, 2, 2, 127, 127])
    np.testing.assert_array_equal(128 * quantize(points, 8), expected)
    np.testing.assert_array_equal(
        128 * iq_quantize(points + 1j * points[::-1], 8), expected + 1j * expected[::-1]
    )
    adc_codes = np.arange(-2048, 2048, dtype=np.int16)
    sc16_codes = adc_codes * 16
    np.testing.assert_array_equal(sc16_codes / 32768, adc_codes / 2048)
    np.testing.assert_array_equal(quantize(adc_codes / 2048, 16), adc_codes / 2048)
    np.testing.assert_array_equal(quantize(points * 0.5, 8, 0.5), expected / 256)


def experiment_a(destination):
    phase = 2 * np.pi * (np.arange(2 ** 17) / 2 ** 17 + 0.12345)
    tone = np.exp(1j * phase)
    levels = np.unique(np.r_[np.arange(-65, 3.26, 0.5), -48, -20, -6, -0.1, 0, 1, 2, 3])
    rows = []
    for level in levels:
        samples = 10 ** (level / 20) * tone
        component_overrange = np.mean(np.abs(samples.view(float)) > 1)
        for bits in (8, 12, 16):
            error = iq_quantize(samples, bits) - samples
            sqnr = db(power(samples) / power(error))
            theory = 10 * np.log10(1.5 * 2 ** (2 * bits)) + level
            if level == -0.1:
                assert abs(sqnr - theory) < 0.35
            rows.append(dict(level_dbfs=level, bits=bits, sqnr_db=sqnr,
                             theory_db=theory, overrange=component_overrange))
    write_csv(destination, "a_sqnr", rows)

    phase = np.linspace(0, 1, 150, endpoint=False)
    rows = []
    for level in (-48, -6, 2):
        samples = 10 ** (level / 20) * np.cos(2 * np.pi * phase)
        for bits in (8, 16):
            output = quantize(samples, bits)
            for cycle, x, y in zip(phase, samples, output, strict=True):
                rows.append(dict(level_dbfs=level, bits=bits, cycle=cycle, input=x, output=y))
    write_csv(destination, "a_waveforms", rows)

    rows = []
    bins = np.linspace(-1, 1, 81)
    for level in (-48, -6):
        component = 10 ** (level / 20) * tone.real
        errors = (quantize(component, 8) - component) * 128
        hist, _ = np.histogram(errors, bins=bins, density=True)
        for left, right, density in zip(bins[:-1], bins[1:], hist, strict=True):
            rows.append(dict(level_dbfs=level, left_lsb=left, right_lsb=right, density=density))
    write_csv(destination, "a_error_pdf", rows)


def experiment_b(destination):
    rng = np.random.default_rng([SEED, 2])
    fs = 1_024_000
    size, segment = 2 ** 18, 2048
    tone = 0.18 * np.exp(2j * np.pi * (246 / segment) * np.arange(size))
    samples = tone + awgn(rng, (size,))
    rows, summary = [], []
    for sigma in SIGMAS:
        scaled = samples * (sigma * np.sqrt(2))
        for name, output in receive(scaled, TRANSPORT):
            f, psd = signal.welch(output, fs=fs, window="hann", nperseg=segment,
                                  noverlap=segment // 2, return_onesided=False,
                                  detrend=False, scaling="density")
            integrated = psd.sum() * fs / segment
            assert abs(integrated / power(output) - 1) < 0.01
            for freq, value in zip(np.fft.fftshift(f), np.fft.fftshift(psd), strict=True):
                rows.append(dict(sigma=sigma, format=name, frequency_hz=freq,
                                 psd_dbfs_hz=db(value)))
            gain = np.vdot(tone, output) / np.vdot(tone, scaled)
            mask = abs(f - 123000) > 3000
            summary.append(dict(sigma=sigma, format=name, tone_gain_db=db(abs(gain) ** 2),
                                mean_floor_dbfs_hz=db(np.mean(psd[mask])),
                                integrated_dbfs=db(integrated), mse=power(output - scaled)))
    write_csv(destination, "b_psd", rows)
    write_csv(destination, "b_psd_summary", summary)
    # Try the same underfilled capture with other SC8 full-scale settings.
    adc = iq_quantize(samples * (SIGMAS[-1] * np.sqrt(2)), 12)
    adc_tone = np.vdot(tone, adc)
    peak_rows = []
    for peak in (1.0, 1 / 16, 1 / 256):
        output = iq_quantize(adc, 8, peak)
        codes = np.rint(adc.view(adc.real.dtype) * 128 / peak)
        peak_rows.append(dict(peak=peak, step=peak / 128,
                              component_saturation=np.mean((codes < -128) | (codes > 127)),
                              tone_gain_vs_adc_db=db(abs(np.vdot(tone, output) / adc_tone) ** 2),
                              mse_vs_adc=power(output - adc)))
        if peak == 1 / 16:
            np.testing.assert_array_equal(output, adc)
    write_csv(destination, "b_peak_scaling", peak_rows)


def bpsk_correlations(samples, reference):
    # The lengths use prefixes of one fixed template. Sum disjoint spans first.
    spans = np.add.reduceat(samples * reference, (0, *LENGTHS[:-1]), axis=1)
    return np.cumsum(spans, axis=1)


def detection_scores(rng, reference, trials, snr_db=None):
    scores = np.empty((len(SIGMAS), len(FORMATS), len(LENGTHS), trials), dtype=np.float64)
    coherent = np.zeros(scores.shape[:3], dtype=np.complex128)
    for start in range(0, trials, BATCH):
        stop = min(start + BATCH, trials)
        count = stop - start
        samples = awgn(rng, (count, len(reference)))
        if snr_db is not None:
            phase = np.exp(2j * np.pi * rng.random(count)).astype(np.complex64)
            amplitude = np.float32(10 ** (snr_db / 20))
            samples += amplitude * phase[:, None] * reference
        for i, sigma in enumerate(SIGMAS):
            gain = np.float32(np.sqrt(2) * sigma)
            for j, (_, output) in enumerate(receive(gain * samples)):
                correlation = bpsk_correlations(output, reference)
                scores[i, j, :, start:stop] = (abs(correlation) ** 2).T
                if snr_db is not None:
                    coherent[i, j] += np.sum(correlation * phase.conj()[:, None],
                                              axis=0, dtype=np.complex128) / gain
    return scores, coherent


def theoretical_pd(length, snr_db, pfa=PFA):
    return stats.ncx2.sf(-2 * np.log(pfa), 2, 2 * length * 10 ** (snr_db / 10))


def experiment_c(destination):
    rng = np.random.default_rng([SEED, 3, 0])
    reference = rng.choice(np.array([-1, 1], dtype=np.float32), LENGTHS[-1])
    np.save(destination / "c_reference.npy", reference)
    n0, n1 = 200_000, 20_000
    cal, _ = detection_scores(np.random.default_rng([SEED, 3, 1]), reference, n0)
    val, _ = detection_scores(np.random.default_rng([SEED, 3, 2]), reference, n0)
    configs = [(i, j, k) for i in range(len(SIGMAS)) for j in range(len(FORMATS))
               for k in range(len(LENGTHS))]
    thresholds = {key: threshold(cal[key]) for key in configs}
    roc_pfa = np.unique(np.r_[np.geomspace(1e-4, 1, 65), PFA])
    roc_key = [(i, FORMATS.index(name), LENGTHS.index(256))
               for i in range(len(SIGMAS)) for name in TRANSPORT]
    roc_thresholds = {key: np.array([threshold(cal[key], pfa) for pfa in roc_pfa])
                      for key in roc_key}

    def labels(key):
        i, j, k = key
        return dict(sigma=SIGMAS[i], format=FORMATS[j], length=LENGTHS[k])

    false_alarm = []
    for key, cutoff in thresholds.items():
        i, j, k = key
        expected = -np.log(PFA) * LENGTHS[k] * 2 * SIGMAS[i] ** 2
        if j == 0:
            assert abs(cutoff / expected - 1) < 0.05
        false_alarm.append(dict(**labels(key), threshold=cutoff,
                                float_theoretical_threshold=expected,
                                **rate_fields(np.count_nonzero(val[key] > cutoff), n0, "pfa")))
    write_csv(destination, "c_false_alarm", false_alarm)

    del cal
    snrs = np.r_[-35, -32, -29, np.arange(-27, -4.9, 0.5), -2, 0, 5, 10]
    pd_rows, roc_rows, differences, required = [], [], [], []
    for index, snr in enumerate(snrs):
        test, coherent = detection_scores(np.random.default_rng([SEED, 3, 3, index]),
                                          reference, n1, snr)
        for key, cutoff in thresholds.items():
            _, j, k = key
            detections = test[key] > cutoff
            field = rate_fields(np.count_nonzero(detections), n1, "pd")
            prediction = theoretical_pd(LENGTHS[k], snr)
            if j == 0 and 0.05 < prediction < 0.95:
                assert abs(field["pd"] - prediction) < 0.025
            gain = abs(coherent[key]) / (10 ** (snr / 20) * n1 * LENGTHS[k])
            pd_rows.append(dict(**labels(key), snr_db=snr, **field,
                                coherent_gain_db=db(gain ** 2), float_theoretical_pd=prediction))
            if FORMATS[j] == "sc8":
                wide_key = (key[0], FORMATS.index("sc16"), k)
                wide = test[wide_key] > thresholds[wide_key]
                eight_only = np.count_nonzero(detections & ~wide)
                sixteen_only = np.count_nonzero(wide & ~detections)
                lo8, hi8 = interval(eight_only, n1, 0.975)
                lo16, hi16 = interval(sixteen_only, n1, 0.975)
                differences.append(dict(**labels(key), snr_db=snr, trials=n1, sc8_only=eight_only,
                                        sc16_only=sixteen_only,
                                        pd_difference=(eight_only - sixteen_only) / n1,
                                        pd_difference_lo=lo8 - hi16, pd_difference_hi=hi8 - lo16))
        if snr == -17:
            for key, cutoffs in roc_thresholds.items():
                h0, h1 = np.sort(val[key]), np.sort(test[key])
                for target, cutoff in zip(roc_pfa, cutoffs, strict=True):
                    nfa = n0 - np.searchsorted(h0, cutoff, side="right")
                    nd = n1 - np.searchsorted(h1, cutoff, side="right")
                    roc_rows.append(dict(**labels(key), snr_db=snr, calibration_pfa=target,
                                         **rate_fields(nfa, n0, "pfa"), **rate_fields(nd, n1, "pd")))
        if index % 10 == 0:
            print(f"  C: {snr:g} dB ({index + 1}/{len(snrs)})", flush=True)

    for key in configs:
        this = [row for row in pd_rows if all(row[col] == value for col, value in labels(key).items())]
        target = 0.9

        def crossing(column):
            probs = np.array([row[column] for row in this])
            upper = np.flatnonzero(probs >= target)[0]
            assert upper > 0
            return np.interp(target, probs[upper - 1:upper + 1], snrs[upper - 1:upper + 1])

        required.append(dict(**labels(key), snr_90_db=crossing("pd"),
                             snr_90_lo_db=crossing("pd_hi"), snr_90_hi_db=crossing("pd_lo"),
                             float_theoretical_snr_90_db=optimize.brentq(
                                 lambda snr: theoretical_pd(LENGTHS[key[2]], snr) - target, -40, 10)))
    write_csv(destination, "c_detection", pd_rows)
    write_csv(destination, "c_roc", roc_rows)
    write_csv(destination, "c_paired", differences)
    write_csv(destination, "c_required", required)


def blocker_reference(rng, length):
    chips = np.repeat(rng.choice([-1, 1], length // 8), 8)
    frequency = np.fft.fftfreq(length)
    spectrum = np.fft.fft(chips)
    spectrum[abs(frequency) > 0.09] = 0
    reference = np.fft.ifft(spectrum).real
    reference /= np.sqrt(power(reference))
    taps = signal.firwin(97, 0.11, fs=1, window=("kaiser", 8.6))
    response = np.fft.fft(taps, n=length) * np.exp(2j * np.pi * 48 * frequency)
    filtered = np.fft.ifft(np.fft.fft(reference) * response).real
    folded = np.fft.ifft(np.fft.fft(filtered) * response.conj()).real
    np.testing.assert_allclose(np.fft.fft(reference)[3 * length // 8], 0, atol=1e-10)
    assert abs(response[3 * length // 8]) < 1e-4
    # Filtering the received block and then matching the filtered reference
    # is equivalent to using H*H on the reference under circular convolution.
    sample = awgn(rng, (length,))
    received = np.fft.ifft(np.fft.fft(sample) * response)
    np.testing.assert_allclose(np.vdot(filtered, received), np.vdot(folded, sample), atol=1e-12)
    return reference.astype(np.float32), folded.astype(np.float32)


def blocker_scores(rng, tone, target, template, noise_rms, gains, trials, draw_target):
    scores = np.empty((len(gains), len(TRANSPORT), trials), dtype=np.float64)
    coherent = np.zeros(scores.shape[:2], dtype=np.complex128)
    overrange = np.zeros(len(gains), dtype=np.int64)
    transport_overrange = np.zeros(len(gains), dtype=np.int64)
    peaks = np.zeros(len(gains))
    for start in range(0, trials, BATCH):
        stop = min(start + BATCH, trials)
        count = stop - start
        phase = np.exp(2j * np.pi * rng.random(count)).astype(np.complex64)
        samples = noise_rms * awgn(rng, (count, len(tone))) + phase[:, None] * tone
        if draw_target:
            target_phase = np.exp(2j * np.pi * rng.random(count)).astype(np.complex64)
            samples += target_phase[:, None] * target
        for i, gain in enumerate(gains):
            scaled = np.float32(gain) * samples
            if draw_target:
                values = np.abs(scaled.view(np.float32))
                overrange[i] += np.count_nonzero(values > 1)
                # At peak=1 the embedded 12-bit output cannot exceed the
                # nominal SC8 input range, but its top codes can round to +128.
                adc_components = quantize(scaled.view(np.float32), 12)
                transport_overrange[i] += np.count_nonzero(np.rint(adc_components * 128) > 127)
                peaks[i] = max(peaks[i], np.max(values))
            for j, (_, output) in enumerate(receive(scaled, TRANSPORT)):
                z = np.einsum("ij,j->i", output, template)
                scores[i, j, start:stop] = abs(z) ** 2
                if draw_target:
                    coherent[i, j] += np.sum(z * target_phase.conj(), dtype=np.complex128)
    return scores, coherent, overrange, transport_overrange, peaks


def experiment_d(destination):
    rng = np.random.default_rng([SEED, 4, 0])
    length = 512
    reference, template = blocker_reference(rng, length)
    rms, snr = 0.035, -12
    target = rms * reference
    noise_rms = rms / 10 ** (snr / 20)
    indices = np.arange(length)
    sinusoid = np.exp(2j * np.pi * 0.375 * indices).astype(np.complex64)
    write_csv(destination, "d_reference", (dict(sample=n, reference=reference[n],
                                                 filter_template=template[n]) for n in indices))
    ncal, nval, nsig = 50_000, 30_000, 12_000
    rows = []
    for index, isr in enumerate(range(0, 71, 5)):
        amplitude = rms * 10 ** (isr / 20)
        gains = (1.0, min(1.0, 0.90 / (amplitude + 4.5 * noise_rms / np.sqrt(2)
                                       + max(abs(target)))))
        tones = amplitude * sinusoid
        cal, *_ = blocker_scores(np.random.default_rng([SEED, 4, 1, index]), tones,
                                 target, template, noise_rms, gains, ncal, False)
        val, *_ = blocker_scores(np.random.default_rng([SEED, 4, 2, index]), tones,
                                 target, template, noise_rms, gains, nval, False)
        test, coherent, clipped, packed, peaks = blocker_scores(
            np.random.default_rng([SEED, 4, 3, index]), tones, target, template, noise_rms,
            gains, nsig, True)
        for i, gain in enumerate(gains):
            for j, name in enumerate(TRANSPORT):
                cutoff = threshold(cal[i, j])
                pfa_count = np.count_nonzero(val[i, j] > cutoff)
                pd_count = np.count_nonzero(test[i, j] > cutoff)
                ratio = abs(coherent[i, j]) / (nsig * gain * np.dot(target, template))
                rows.append(dict(isr_db=isr, input_snr_db=snr, format=name,
                                 gain_mode=("fixed", "backoff")[i], gain_db=db(gain ** 2),
                                 desired_rms_dbfs=db((gain * rms) ** 2), threshold=cutoff,
                                 input_adc_overrange=(clipped[i] / (2 * length * nsig)
                                                      if name != "float" else 0),
                                 sc8_positive_rail_saturation=(packed[i] / (2 * length * nsig)
                                                              if name == "sc8" else 0),
                                 input_max_dbfs=db(peaks[i] ** 2), coherent_gain_db=db(ratio ** 2),
                                 **rate_fields(pfa_count, nval, "pfa"),
                                 **rate_fields(pd_count, nsig, "pd")))
        print(f"  D: {isr:g} dB interference-to-signal ratio", flush=True)
    write_csv(destination, "d_blocker", rows)


def constellation(order):
    if order == 4:
        return np.array([-1, 1]) / np.sqrt(2), np.array([[0], [1]])
    return np.array([-3, -1, 1, 3]) / np.sqrt(10), np.array([[0, 0], [0, 1], [1, 1], [1, 0]])


def analytical_ber(levels, labels, noise_sigma):
    boundaries = np.r_[-np.inf, (levels[:-1] + levels[1:]) / 2, np.inf]
    distances = (boundaries[None, :] - levels[:, None]) / noise_sigma
    transitions = np.diff(special.ndtr(distances), axis=1)
    # Use the equivalent survival-function difference in the positive tail.
    pos = distances[:, :-1] > 0
    transitions[pos] = (-np.diff(special.ndtr(-distances), axis=1))[pos]
    bit_errors = np.count_nonzero(labels[:, None] != labels[None, :], axis=-1)
    return np.sum(transitions * bit_errors) / labels.size


def experiment_e(destination):
    rng = np.random.default_rng([SEED, 5])
    rows, points = [], []
    symbols = 400_000
    for order, snrs in ((4, range(-2, 13)), (16, range(-1, 18))):
        levels, labels = constellation(order)
        slicer = (levels[:-1] + levels[1:]) / 2
        sent = rng.integers(0, len(levels), size=(symbols, 2))
        tx = (levels[sent[:, 0]] + 1j * levels[sent[:, 1]]).astype(np.complex64)
        noise = awgn(rng, tx.shape)
        bits_per_symbol = 2 * labels.shape[1]
        sym_gain = 0.28
        for snr in snrs:
            esn0 = bits_per_symbol * 10 ** (snr / 10)
            unscaled = tx + noise / np.sqrt(esn0)
            scaled = unscaled * sym_gain
            theory = analytical_ber(levels, labels, 1 / np.sqrt(2 * esn0))
            if order == 4:
                np.testing.assert_allclose(theory, special.ndtr(-np.sqrt(2 * esn0 / bits_per_symbol)))
            for name, output in receive(scaled, TRANSPORT):
                decoded = output / sym_gain
                hard = np.stack((np.searchsorted(slicer, decoded.real, side="right"),
                                 np.searchsorted(slicer, decoded.imag, side="right")), axis=-1)
                axis_errors = np.count_nonzero(labels[hard] != labels[sent], axis=-1)
                bit_errors = axis_errors.sum()
                total = symbols * bits_per_symbol
                if name == "float" and theory * total > 30:
                    assert abs(bit_errors - theory * total) < 8 * np.sqrt(theory * total)
                ber = rate_fields(bit_errors, total, "ber")
                axes = 2 * symbols
                if order == 16:
                    # Two bits on the same axis can fail together. Bound
                    # BER = (P(at least 1 error) + P(2 errors)) / 2.
                    lo1, hi1 = interval(np.count_nonzero(axis_errors >= 1), axes, 0.975)
                    lo2, hi2 = interval(np.count_nonzero(axis_errors == 2), axes, 0.975)
                    ber["ber_lo"], ber["ber_hi"] = (lo1 + lo2) / 2, (hi1 + hi2) / 2
                # An axis error is at least as likely as a bit error.
                upper_limit = -np.expm1(np.log(0.05) / axes) if bit_errors == 0 else np.nan
                evm = 100 * np.sqrt(power(decoded - tx) / power(tx))
                rows.append(dict(order=order, ebn0_db=snr, format=name, **ber,
                                 zero_error_upper_95=upper_limit, theory_ber=theory, evm_percent=evm,
                                 adc_input_overrange=np.mean(abs(scaled.view(scaled.real.dtype)) > 1)))
                if (order == 4 and snr == 8) or (order == 16 and snr == 14):
                    for value, ideal in zip(decoded[:1800], tx[:1800], strict=True):
                        points.append(dict(order=order, ebn0_db=snr, format=name, i=value.real,
                                           q=value.imag, ideal_i=ideal.real, ideal_q=ideal.imag))
    write_csv(destination, "e_demod", rows)
    write_csv(destination, "e_constellation", points)


def experiment_throughput(destination):
    rows = []
    for msps in (10, 20, 30.72, 40, 61.44):
        for name, bits in (("SC8", 8), ("SC16", 16), ("FC32", 32)):
            payload = msps * 2 * bits / 8
            rows.append(dict(msps=msps, format=name, mb_per_s=payload,
                             gb_per_min=payload * 60 / 1000, gb_per_hour=payload * 3600 / 1000,
                             block_4096_us=4096 / msps))
    assert [row["mb_per_s"] for row in rows[-3:]] == [122.88, 245.76, 491.52]
    write_csv(destination, "throughput", rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+", choices=["a", "b", "c", "d", "e", "throughput"])
    parser.add_argument("--plots-only", action="store_true")
    parser.add_argument("--data", type=Path, default=HERE / "results")
    parser.add_argument("--figures", type=Path, default=HERE.parents[1] / "content" / "posts"
                        / "sc8-vs-sc16-iq-quantization" / "figures")
    args = parser.parse_args()
    args.data.mkdir(parents=True, exist_ok=True)
    validate_quantizer()
    experiments = {"a": experiment_a, "b": experiment_b, "c": experiment_c, "d": experiment_d,
                   "e": experiment_e, "throughput": experiment_throughput}
    if not args.plots_only:
        for name in args.only or experiments:
            start = time.perf_counter()
            print(f"Running {name.upper()}", flush=True)
            experiments[name](args.data)
            print(f"  finished in {time.perf_counter() - start:.1f} s", flush=True)
        if args.only:
            return
        import matplotlib

        metadata = dict(seed=SEED, python=platform.python_version(), numpy=np.__version__,
                        scipy=scipy.__version__, matplotlib=matplotlib.__version__,
                        c_h0_calibration=200_000, c_h0_validation=200_000, c_h1_per_snr=20_000,
                        d_h0_calibration=50_000, d_h0_validation=30_000, d_h1=12_000,
                        e_symbols_per_setting=400_000)
        (args.data / "run_info.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    from plot_experiments import render_all

    render_all(args.data, args.figures)


if __name__ == "__main__":
    main()
