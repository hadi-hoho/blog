+++
date = '2026-08-27T20:41:44Z'
draft = false
title = 'The World of Software-Defined Radios'
+++

{{< katex >}}

As a telecommunications engineer, I already have a little experience with [software-defined radios](https://en.wikipedia.org/wiki/Software-defined_radio).

The idea of capturing an electromagnetic wave out of thin air and converting it into a digital data stream might seem like magic at first—and it is the closest thing to a Harry Potter movie, if you ask me! Using an SDR to get an idea of what is happening around you is fairly easy, but first-time users can still encounter plenty of hands-on challenges. I want to focus on those challenges and share what I learned from them.

## Step one: an arm and a leg on the table!

When an enthusiastic nerd tries to DIY their way into wireless communications, one of the main concerns is the cost of equipment. The price of SDR devices is no help in this matter.

A large part of the community will recommend a cheap [RTL-SDR](https://www.amazon.com/dp/B0BMKZCKTF) USB stick, which costs around $50 or less. If you are willing to spend more, however, the world of SDR devices is more than happy to take your money!

The main limitations of cheaper SDR sticks, in my experience, are their frequency range—which typically reaches about 1.7 GHz—and their instantaneous bandwidth. These can become bottlenecks for the applications you want to explore.

A 1.7 GHz upper limit does not include the 2.4 GHz or 5.8 GHz ISM bands. These bands are widely used by everyday devices, including Wi-Fi and Bluetooth equipment, as well as many commercial drones. Although inexpensive SDRs are a great place to start, they do not cover many of the applications that interest me.

That brings us to the next option: SDRs based on the [AD9361](https://www.analog.com/en/products/ad9361.html). This transceiver supports sampling rates of up to 61.44 MS/s, which is enough for experimenting with many wireless systems. The ADALM-Pluto and many of MicroPhase's AntSDR devices are good examples of this transceiver family. Lower-cost AD9361-based devices also exist, including the LibreSDR B210 and HamGeek TinyB210.

## Step two: bandwidth matters more than you think

One thing that wasn't immediately obvious to me when I first started working with SDRs was the difference between **frequency range** and **instantaneous bandwidth**.

Being able to tune an SDR to 6 GHz does not mean that you can simultaneously see everything between DC and 6 GHz. The SDR only observes a relatively small portion of the spectrum around its center frequency at any given time.

For example, if an SDR is configured with an instantaneous bandwidth of 20 MHz and tuned to 2.4 GHz, you are essentially looking at a roughly 20 MHz-wide window around that center frequency.

This becomes important very quickly.

A narrow-band signal such as an FM radio station, an amateur radio transmission, or many telemetry links can comfortably fit inside a few hundred kilohertz or a couple of megahertz.

Wi-Fi is a different story.

A single Wi-Fi channel can occupy 20, 40, 80 or even more MHz of spectrum depending on the standard and configuration. Suddenly, the sampling rate and analog bandwidth of your SDR become a very real limitation.

This was one of the first lessons I learned:

> **The maximum frequency tells you where you can look. The instantaneous bandwidth tells you how much you can see at once.**

And that distinction matters a lot more than it initially seems.

---

## Step three: congratulations, now you need antennas

Buying the SDR is unfortunately not the end of the hardware problem.

Now you need an antenna.

And preferably the *right* antenna.

When starting out, it is tempting to connect whatever antenna happens to have the correct SMA connector and expect everything to work. Sometimes it does. Quite often it doesn't.

Antennas are designed for particular frequency ranges, and their performance can change dramatically outside those ranges.

A small antenna designed for 2.4 GHz might perform terribly at 100 MHz, while an antenna intended for VHF may be practically useless at several gigahertz.

This also introduced me to another rabbit hole:

- antenna gain,
- polarization,
- impedance matching,
- radiation patterns,
- cable loss,
- connector loss,
- and eventually things like LNAs, filters, and attenuators.

At some point you realize that the SDR itself is only one part of the receiver.

The entire chain looks more like:

**Antenna → Filter → LNA/Attenuator → SDR RF front-end → ADC → Digital processing**

Every block can affect what you eventually see on your screen.

---

## Step four: more gain does not necessarily mean more signal

This one sounds obvious after you learn it, but it can be surprisingly confusing at first.

When a signal looks weak on the spectrum display, the natural reaction is:

**MORE GAIN!**

Unfortunately, RF systems don't work quite like turning up the volume on your headphones.

Increasing receiver gain amplifies both the desired signal and the noise entering the receiver. Even worse, too much gain can overload the RF front-end or ADC.

Once that happens, strong signals can produce distortion and unwanted products across the spectrum.

You might suddenly see signals that aren't actually there.

This is particularly noticeable when using an SDR near powerful transmitters such as FM broadcast stations, cellular base stations, or other high-power RF sources.

So one of the first practical habits I developed was to stop asking:

> "How high can I set the gain?"

and instead ask:

> "What is the lowest gain that gives me a clean and usable signal?"

Sometimes an external band-pass filter is much more useful than another 20 dB of amplification.

---

## Step five: what exactly is an IQ sample?

This was probably one of the biggest conceptual jumps for me.

When you record audio, you normally get a sequence of real-valued samples representing the waveform amplitude over time.

An SDR usually gives you something slightly different:

**complex IQ samples.**

Each sample consists of two components:

\[
x[n] = I[n] + jQ[n]
\]

where **I** is the in-phase component and **Q** is the quadrature component.

At first this can feel like unnecessary mathematical complexity.

Why not just record the waveform?

The reason is that IQ representation preserves both the **amplitude and phase information** of the received signal while representing the RF spectrum around a chosen center frequency at baseband.

This makes a huge number of digital signal-processing operations possible.

Once you have IQ samples, you can digitally:

- shift frequencies,
- filter channels,
- estimate signal bandwidth,
- calculate power spectral density,
- demodulate signals,
- estimate carrier frequency,
- recover symbol timing,
- inspect constellations,
- and perform many other operations without touching the RF hardware again.

In other words, the SDR converts an RF problem into a signal-processing problem.

And as someone coming from telecommunications engineering, this is where SDRs started becoming particularly interesting to me.

---

## Step six: sampling rate gets expensive very quickly

Let's say you configure your SDR to produce:

**61.44 million complex samples every second.**

That sounds great.

More samples must mean more information, right?

Technically yes.

Your computer, however, may disagree.

Suppose each IQ component is stored using 16 bits.

That means every complex sample takes:

\[
16 + 16 = 32\ \text{bits per complex sample}
\]

or 4 bytes.

At 61.44 MS/s:

\[
61.44 \times 10^6\ \text{samples/s}
\times 4\ \text{bytes/sample}
= 245.76\ \text{MB/s}
\]

which is approximately:

**246 MB/s.**

That is almost **15 GB per minute** of raw IQ data.

Suddenly a one-hour recording does not sound particularly attractive.

This is why concepts such as **decimation, channel filtering, and selective recording** become extremely important.

If the signal you're interested in only occupies 1 MHz, there is usually no reason to continuously store tens of MHz of spectrum.

Capture what you need.

Filter it.

Decimate it.

Then process the much smaller resulting signal.

Your SSD will thank you.

---

## Step seven: finding a signal is easier than understanding it

Opening an SDR application and seeing a waterfall for the first time is extremely satisfying.

Signals are everywhere.

FM broadcast stations are easy to recognize.

You can see cellular signals.

You can see Wi-Fi.

You can see Bluetooth activity.

Depending on your location and antenna, you might find aircraft transmissions, satellites, telemetry systems, remote controls, and dozens of other signals.

But detecting energy on the spectrum is the easy part.

The difficult question is:

**What exactly am I looking at?**

A spectrum analyzer can tell you that something exists around a certain frequency.

Understanding the signal requires considerably more work.

You might need to determine:

- center frequency,
- occupied bandwidth,
- modulation type,
- symbol rate,
- pulse-shaping filter,
- frame structure,
- synchronization sequence,
- channel spacing,
- duplexing method,
- and sometimes whether frequency hopping is involved.

At that point SDR stops being a cool spectrum visualization tool and becomes an actual communications laboratory.

---

## Step eight: the software part of software-defined radio

One might reasonably assume that the word **software** in SDR means the software side will be simple.

It does not.

There are several excellent SDR applications and frameworks:

- GNU Radio
- SDR++
- GQRX
- SDRangel
- MATLAB
- Python with NumPy/SciPy
- SoapySDR
- UHD
- libiio

But different radios use different drivers, APIs, and ecosystems.

One device might use UHD.

Another uses libiio.

Another uses SoapySDR.

Another comes with some mysterious vendor-specific software last updated several years ago.

Then there are USB bandwidth problems, firmware versions, FPGA images, drivers, and operating-system compatibility.

Eventually you will encounter the classic SDR troubleshooting sequence:

1. Is the SDR detected?
2. Is the driver installed?
3. Is the firmware correct?
4. Is the sample rate supported?
5. Is USB fast enough?
6. Why am I dropping samples?
7. Why does this work on Linux but not Windows?
8. Why did it work yesterday?

At which point the electromagnetic wave you originally wanted to investigate has become the least mysterious part of the system.

---

## Step nine: RF has a way of humbling you

One of the things I enjoy about SDR is that it forces several areas of telecommunications to meet in one place.

You cannot completely separate RF engineering from signal processing.

You cannot completely separate signal processing from communication theory.

And you cannot completely separate any of those things from software and computer architecture.

A strange signal on your waterfall could be caused by the transmitter.

Or multipath.

Or interference.

Or your antenna.

Or your amplifier.

Or ADC clipping.

Or IQ imbalance.

Or DC offset.

Or aliasing.

Or your DSP code.

Or simply a loose SMA connector.

Learning to distinguish between those possibilities is probably more valuable than learning how to operate any particular SDR.

---


## So, what can you actually do with one?

This is where SDR becomes fun.

Once you have a reasonably capable transceiver and understand the basic signal chain, an SDR becomes something between a radio, spectrum analyzer, signal generator, and communications laboratory.

You can use it to experiment with things such as:

- FM/AM reception
- ADS-B aircraft reception
- satellite signals
- amateur radio
- digital modulation
- OFDM
- channel estimation
- direction finding
- spectrum monitoring
- custom wireless protocols
- radar experiments
- wireless security research
- synchronization algorithms
- modulation recognition

With a transmitting SDR, you can also build complete experimental communication links entirely in software.

That last part is what fascinates me most.

You can write a few hundred lines of code implementing a transmitter, send the waveform through actual antennas and an actual wireless channel, receive it on another SDR, and compare what happened with everything you learned from communication theory.

The equations suddenly leave the textbook.

They become signals on your screen.
