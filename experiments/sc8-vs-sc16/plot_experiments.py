"""Render publication figures from the saved experiment tables."""

import csv
from functools import cache

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import ticker
from matplotlib.patches import FancyBboxPatch


PAPER, INK, MUTED, GRID = "#f6f8fc", "#17243a", "#495c73", "#dbe2eb"
BLUE, ORANGE, TEAL, PURPLE = "#1c6ba5", "#b34716", "#087a73", "#75499c"
STYLES = {
    "float": dict(color=INK, linestyle=":", label="Float"),
    "sc16": dict(color=BLUE, linestyle="-", label="12-bit → SC16"),
    "sc8": dict(color=ORANGE, linestyle="--", label="12-bit → SC8"),
}
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 12,
    "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER,
    "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": GRID,
    "xtick.color": MUTED, "ytick.color": MUTED, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": True, "legend.facecolor": PAPER, "legend.edgecolor": GRID,
    "legend.fontsize": 10, "lines.linewidth": 1.9, "svg.fonttype": "path",
    "svg.hashsalt": "sc8-vs-sc16", "savefig.dpi": 210,
})


@cache
def table(data, name):
    with (data / f"{name}.csv").open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    columns = {}
    for key in rows[0]:
        values = [row[key] for row in rows]
        try:
            columns[key] = np.array(values, dtype=float)
        except ValueError:
            columns[key] = np.array(values)
    return columns


def select(columns, **filters):
    keep = np.full(len(next(iter(columns.values()))), True)
    for name, value in filters.items():
        keep &= columns[name] == value
    return {name: values[keep] for name, values in columns.items()}


def setup(panels, height):
    fig, axes = plt.subplots(panels, 1, figsize=(6.6, height), layout="constrained")
    for ax in np.atleast_1d(axes):
        ax.grid(True)
        ax.set_axisbelow(True)
        ax.tick_params(length=3)
    return fig, axes


def heading(ax, title):
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", pad=9)


def save(fig, directory, name):
    fig.savefig(directory / name, bbox_inches="tight", pad_inches=0.20, metadata={"Date": None})
    plt.close(fig)


def signal_chain(directory):
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.set(xlim=(0, 6), ylim=(0, 4))
    ax.axis("off")
    stages = [
        (3.50, "RF front end", "Gain, noise and interference", TEAL),
        (2.50, "ADC and internal DSP", "AD9361 exports 12-bit I and Q", BLUE),
        (1.50, "FPGA and USB payload", "SC8 or SC16, where supported", ORANGE),
        (0.50, "Host samples and DSP", "For example, FC32 for filtering and detection", PURPLE),
    ]
    for y, title, label, color in stages:
        box = FancyBboxPatch((0.15, y - 0.36), 5.7, 0.72, boxstyle="round,pad=0.035",
                             ec=color, fc="white", lw=1.25)
        ax.add_patch(box)
        ax.text(3, y + 0.10, title, ha="center", va="center", fontsize=15, weight="bold")
        ax.text(3, y - 0.14, label, ha="center", va="center", color=MUTED, fontsize=12)
        if y > 0.5:
            ax.annotate("", (3, y - 0.60), (3, y - 0.40),
                        arrowprops=dict(arrowstyle="->", color=MUTED, lw=1.4))
    fig.subplots_adjust(left=0.012, right=0.988, bottom=0.012, top=0.988)
    save(fig, directory, "signal-chain.svg")


def quantizer_plots(data, directory, extra):
    fig, axes = setup(3, 8.1)
    waves = table(data, "a_waveforms")
    case = select(waves, level_dbfs=-48, bits=8)
    fine = select(waves, level_dbfs=-48, bits=16)
    axes[0].plot(case["cycle"], case["input"] * 1000, color=INK, ls=":", label="Input")
    axes[0].step(fine["cycle"], fine["output"] * 1000, where="mid", color=BLUE, label="Ideal 16-bit")
    axes[0].step(case["cycle"], case["output"] * 1000, where="mid", color=ORANGE, ls="--",
                 label="Ideal 8-bit")
    axes[0].set(xlabel="Time (cycles)", ylabel="Component (mFS)", xlim=(0, 1))
    heading(axes[0], "A sine wave at −48 dBFS")
    axes[0].legend(loc="lower right", ncols=3)

    hist = table(data, "a_error_pdf")
    for level, color, ls in [(-6, TEAL, "-"), (-48, ORANGE, "--")]:
        case = select(hist, level_dbfs=level)
        edges = np.r_[case["left_lsb"], case["right_lsb"][-1]]
        axes[1].stairs(case["density"], edges, color=color, ls=ls, label=f"{level} dBFS".replace("-", "−"))
    axes[1].set(xlabel="8-bit rounding error (LSB)", ylabel="Density (1/LSB)", xlim=(-0.57, 0.57))
    axes[1].legend(loc="upper center", ncols=2)
    heading(axes[1], "The error changes as fewer codes are used")

    sqnr = table(data, "a_sqnr")
    for bits, color in [(8, ORANGE), (12, TEAL), (16, BLUE)]:
        case = select(sqnr, bits=bits)
        axes[2].plot(case["level_dbfs"], case["sqnr_db"], color=color, label=f"Ideal {bits}-bit")
        model = case["level_dbfs"] <= 0
        axes[2].plot(case["level_dbfs"][model], case["theory_db"][model], color=color,
                     ls=(0, (1.5, 2.5)), alpha=0.82, lw=1.5)
    axes[2].axvspan(0, 3, color=ORANGE, alpha=0.08)
    axes[2].set(xlabel="Sine wave peak (dBFS)", ylabel="SQNR (dB)", xlim=(-65, 3), ylim=(-18, 104))
    axes[2].legend(loc="upper left", ncols=3)
    heading(axes[2], "Signal-to-quantization-noise ratio")
    save(fig, directory, "quantization.svg")

    fig, ax = setup(1, 2.8)
    case = select(waves, level_dbfs=2, bits=8)
    ax.plot(case["cycle"], case["input"], color=INK, ls=":", label="Input")
    ax.step(case["cycle"], case["output"], where="mid", color=ORANGE, label="Ideal 8-bit")
    ax.axhline(1, color=MUTED, ls="--", lw=0.8)
    ax.axhline(-1, color=MUTED, ls="--", lw=0.8)
    ax.set(xlabel="Time (cycles)", ylabel="Component (FS)", xlim=(0, 1))
    ax.legend(loc="upper right", ncols=2)
    heading(ax, "Clipping a sine wave at +2 dBFS")
    save(fig, extra, "clipping.svg")


def spectra(data, directory):
    fig, axes = setup(2, 5.35)
    psd = table(data, "b_psd")
    for ax, sigma, title in zip(axes, (0.12, 0.002), ("Well-scaled input", "Underfilled input"), strict=True):
        for name in ("sc16", "float", "sc8"):
            row = select(psd, sigma=sigma, format=name)
            ax.plot(row["frequency_hz"] / 1000, row["psd_dbfs_hz"], **STYLES[name])
        ax.set(xlabel="Baseband frequency (kHz)", ylabel="PSD (dBFS/Hz)", xlim=(-512, 512))
        ax.legend(loc="upper left", ncols=3)
        heading(ax, f"{title} · noise σ = {sigma:g} FS per component")
    save(fig, directory, "psd.svg")


def detection(data, directory):
    fig, axes = setup(2, 5.8)
    rows = table(data, "c_detection")
    for ax, sigma, label in zip(axes, (0.12, 0.002), ("Well-scaled input", "Underfilled input"), strict=True):
        for length, color, marker in [(64, TEAL, "^"), (256, BLUE, "s"), (1024, PURPLE, "o")]:
            for name, ls in [("sc16", "-"), ("sc8", "--")]:
                case = select(rows, sigma=sigma, length=length, format=name)
                ax.plot(case["snr_db"], case["pd"], ls=ls, color=color,
                        marker=marker, markevery=(0, 9), ms=4, mfc=(color if name == "sc16" else PAPER),
                        label=f"{length} samples" if name == "sc16" else None)
        ax.axhline(0.9, lw=1, ls=":", color=MUTED)
        ax.set(xlim=(-26, 0), ylim=(-0.025, 1.035), xlabel="Input SNR (dB per complex sample)",
               ylabel="Detection probability")
        ax.yaxis.set_major_locator(ticker.MultipleLocator(0.25))
        ax.legend(loc="lower right", ncols=3)
        heading(ax, label)
    save(fig, directory, "detection.svg")

    fig, ax = setup(1, 3.55)
    rows = table(data, "c_roc")
    for sigma, color, title in [(0.12, BLUE, "Well-scaled"), (0.002, ORANGE, "Underfilled")]:
        for name, ls, fmt in [("sc16", "-", "SC16"), ("sc8", "--", "SC8")]:
            case = select(rows, sigma=sigma, format=name)
            ax.semilogx(case["pfa"], case["pd"], color=color, ls=ls, label=f"{title} {fmt}")
    ax.axvline(1e-3, color=MUTED, ls=":", lw=1.1)
    ax.set(xlim=(1e-4, 0.7), ylim=(0, 1.01), xlabel="False-alarm probability",
           ylabel="Detection probability")
    ax.legend(loc="lower right", ncols=2)
    heading(ax, "ROC at −17 dB input SNR · 256 samples")
    save(fig, directory, "roc.svg")


def blockers(data, directory):
    fig, axes = setup(3, 7.7)
    rows = table(data, "d_blocker")
    for ax, mode, label in zip(axes[:2], ("fixed", "backoff"),
                               ("Fixed receiver gain", "Gain backed off for the interferer"), strict=True):
        for name in ("float", "sc16", "sc8"):
            case = select(rows, gain_mode=mode, format=name)
            ax.plot(case["isr_db"], case["pd"], **STYLES[name])
        ax.set(xlim=(0, 70), ylim=(-0.035, 1.045), xlabel="Interference-to-signal ratio (dB)",
               ylabel="Detection probability")
        ax.yaxis.set_major_locator(ticker.MultipleLocator(0.25))
        ax.legend(loc="lower left", ncols=3)
        heading(ax, label)
    for mode, color, label in [("fixed", ORANGE, "Fixed gain"), ("backoff", TEAL, "With gain backoff")]:
        case = select(rows, gain_mode=mode, format="sc16")
        axes[2].plot(case["isr_db"], case["input_adc_overrange"], color=color,
                     ls=("-" if mode == "fixed" else "--"), label=label)
    axes[2].set(xlim=(0, 70), xlabel="Interference-to-signal ratio (dB)",
                ylabel="ADC components\noutside full scale", ylim=(-0.035, 1.025))
    axes[2].yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1, decimals=0))
    axes[2].legend(loc="upper left", ncols=2)
    heading(axes[2], "ADC input overrange")
    save(fig, directory, "blocker.svg")


def demodulation(data, directory, extra):
    rows = table(data, "e_demod")
    fig, axes = setup(2, 5.8)
    for ax, order, title in zip(axes, (4, 16), ("QPSK", "16-QAM"), strict=True):
        ref = select(rows, order=order, format="float")
        visible = ref["theory_ber"] >= 2e-8
        ax.semilogy(ref["ebn0_db"][visible], ref["theory_ber"][visible], ls=":", color=INK, label="AWGN theory")
        for name, color, marker in [("float", INK, "x"), ("sc16", BLUE, "o"), ("sc8", ORANGE, "s")]:
            case = select(rows, order=order, format=name)
            observed = case["ber_count"] > 0
            ax.semilogy(case["ebn0_db"][observed], case["ber"][observed], ls="none", color=color,
                        marker=marker, mfc="none", ms={"x": 3.5, "o": 5.5, "s": 7.5}[marker],
                        label=STYLES[name]["label"])
            zero = ~observed
            ax.semilogy(case["ebn0_db"][zero], case["zero_error_upper_95"][zero], ls="none",
                        marker="v", mfc="none", color=color,
                        ms={"float": 4, "sc16": 6, "sc8": 8}[name])
        ax.set(xlabel=r"$E_b/N_0$ (dB)", ylabel="Bit error rate", ylim=(6e-7, 0.45))
        ax.legend(loc="lower left", ncols=2)
        heading(ax, title)
    save(fig, directory, "ber.svg")

    dots = table(data, "e_constellation")
    fig, axes = plt.subplots(2, 2, figsize=(6.6, 6.4), layout="constrained")
    for row, order, title in zip(axes, (4, 16), ("QPSK", "16-QAM"), strict=True):
        for ax, name, color in zip(row, ("sc16", "sc8"), (BLUE, ORANGE), strict=True):
            case = select(dots, order=order, format=name)
            ax.scatter(case["i"], case["q"], s=6, alpha=0.2, color=color, linewidths=0, rasterized=True)
            ideals = np.unique(np.column_stack((case["ideal_i"], case["ideal_q"])), axis=0)
            ax.scatter(*ideals.T, marker="+", s=60, color=INK, linewidths=1.1)
            ax.set(xlim=(-1.25, 1.25), ylim=(-1.25, 1.25), xlabel="I", ylabel="Q", aspect="equal")
            ax.grid(True)
            heading(ax, f"{title} · {name.upper()}")
    save(fig, extra, "constellations.svg")


def throughput(data, directory):
    fig, ax = setup(1, 3.4)
    rows = table(data, "throughput")
    for name, color, marker in [("SC8", ORANGE, "s"), ("SC16", BLUE, "o"), ("FC32", TEAL, "^")]:
        case = select(rows, format=name)
        ax.plot(case["msps"], case["mb_per_s"], color=color, marker=marker, label=name)
    ax.axhline(60, color=MUTED, lw=1.1, ls=":", label="USB 2.0 high-speed signaling")
    ax.set(xlabel="Complex sampling rate (MSps)", ylabel="Single-channel payload (MB/s)",
           xlim=(8, 64), ylim=(0, 515))
    ax.legend(loc="upper left", ncols=2)
    heading(ax, "Raw IQ payload before protocol overhead")
    save(fig, directory, "throughput.svg")


def featured(data, directory):
    rows = table(data, "a_waveforms")
    case = select(rows, level_dbfs=-48, bits=8)
    fine = select(rows, level_dbfs=-48, bits=16)
    fig, ax = plt.subplots(figsize=(8.4, 3.7))
    dark = "#142039"
    fig.patch.set_facecolor(dark)
    ax.set_facecolor(dark)
    ax.grid(color="#30405d", linewidth=0.8)
    ax.plot(fine["cycle"], fine["output"], color="#75d1e6", lw=2.6)
    ax.step(case["cycle"], case["output"], where="mid", color="#efa96f", lw=3.4)
    ax.scatter(case["cycle"][::4], case["output"][::4], color="#efa96f", s=16)
    ax.set(xlim=(0, 0.99), ylim=(-0.0107, 0.0107), xticks=np.arange(0, 1.1, 0.1),
           yticks=np.arange(-4, 5) / 512)
    ax.tick_params(length=0, labelbottom=False, labelleft=False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.subplots_adjust(left=0.035, right=0.965, bottom=0.075, top=0.925)
    fig.savefig(directory / "featured.png", dpi=160, facecolor=dark)
    plt.close(fig)


def render_all(data, directory):
    directory.mkdir(parents=True, exist_ok=True)
    extra = data.parent / "figures"
    extra.mkdir(parents=True, exist_ok=True)
    signal_chain(directory)
    quantizer_plots(data, directory, extra)
    spectra(data, directory)
    detection(data, directory)
    blockers(data, directory)
    demodulation(data, directory, extra)
    throughput(data, directory)
    featured(data, directory.parent)
