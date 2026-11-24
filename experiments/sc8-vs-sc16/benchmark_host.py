"""Time individual DSP kernels on the local host with synthetic inputs."""

import argparse
import json
import platform
from time import perf_counter

import numpy as np
from scipy import fft, signal

from run_experiments import HERE, SEED, awgn, write_csv


def converter(codes, scale):
    decoded = np.empty(len(codes) // 2, dtype=np.complex64)
    components = decoded.view(np.float32)

    def process():
        np.multiply(codes, scale, out=components, dtype=np.float32)
        return decoded

    np.testing.assert_array_equal(process().view(np.float32), codes.astype(np.float32) * scale)
    return process


def decimator(size, taps):
    factor = 4
    history = 64  # divisible by the decimation factor, and at least len(taps) - 1
    state = np.zeros(size + history, dtype=np.complex64)

    def process(block):
        state[history:] = block
        filtered = signal.upfirdn(taps, state, down=factor)
        state[:history] = state[-history:]
        return filtered[history // factor:(history + size) // factor]

    return process


def sliding_matched_filter(size, template):
    kernel = template.conj()[::-1]
    history = len(kernel) - 1
    work = np.zeros(fft.next_fast_len(size + history), dtype=np.complex64)
    response = fft.fft(kernel, n=len(work), workers=1)

    def process(block):
        work[history:history + size] = block
        spectrum = fft.fft(work, workers=1)
        spectrum *= response
        filtered = fft.ifft(spectrum, overwrite_x=True, workers=1)
        work[:history] = block[-history:]
        return filtered[history:history + size]

    return process


def measure(call, rounds, repeats):
    for _ in range(15):
        call()
    elapsed = []
    for _ in range(rounds):
        start = perf_counter()
        for _ in range(repeats):
            call()
        elapsed.append((perf_counter() - start) / repeats)
    return np.percentile(elapsed, [50, 95])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpu", default=platform.processor(), help="processor model for the run log")
    args = parser.parse_args()
    rng = np.random.default_rng([SEED, 6])
    taps = signal.firwin(63, 0.225).astype(np.float32)
    template = awgn(rng, (256,))
    template /= np.linalg.norm(template)
    rounds, repeats = 25, 100
    rows = []
    for size in (1024, 4096, 16384):
        block = awgn(rng, (size,))
        second = awgn(rng, (size,))
        decimate = decimator(size, taps)
        correlate = sliding_matched_filter(size, template)
        pair = np.concatenate((block, second))
        np.testing.assert_allclose(np.r_[decimate(block), decimate(second)],
                                   signal.lfilter(taps, [1], pair)[::4], atol=2e-6)
        np.testing.assert_allclose(np.r_[correlate(block), correlate(second)],
                                   signal.lfilter(template.conj()[::-1], [1], pair), atol=2e-6)
        sc8 = rng.integers(-128, 128, 2 * size, dtype=np.int8)
        sc16 = rng.integers(-32768, 32768, 2 * size, dtype=np.int16)
        operations = {
            "sc8_to_fc32": converter(sc8, 1 / 128),
            "sc16_to_fc32": converter(sc16, 1 / 32768),
            "complex_fft": lambda: fft.fft(block, workers=1),
            "fir_decimate_4": lambda: decimate(block),
            "sliding_matched_filter_256": lambda: correlate(block),
        }
        for operation, call in operations.items():
            median, p95 = measure(call, rounds, repeats)
            rows.append(dict(operation=operation, complex_block=size, median_us=median * 1e6,
                             p95_round_mean_us=p95 * 1e6, median_equivalent_msps=size / median / 1e6))

    destination = HERE / "results"
    destination.mkdir(exist_ok=True)
    write_csv(destination, "host_benchmark", rows)
    import scipy

    metadata = dict(cpu=args.cpu, platform=platform.platform(), python=platform.python_version(),
                    numpy=np.__version__, scipy=scipy.__version__, rounds=rounds,
                    repeats_per_round=repeats, warmup_calls=15, fft_workers=1)
    (destination / "host_benchmark_info.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
