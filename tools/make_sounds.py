"""Renders sounds/*.wav (additive/noise synth + reverb). Needs numpy in a venv.

Usage: python tools/make_sounds.py sounds
"""
import math, os, sys, wave
import numpy as np

SR = 44100
rng = np.random.default_rng(7)


class Mix:
    def __init__(self, seconds):
        self.n = int(SR * seconds)
        self.dry = np.zeros(self.n)
        self.wet = np.zeros(self.n)

    def add(self, sig, start, send):
        i = int(start * SR)
        sig = sig[: max(0, self.n - i)]
        self.dry[i:i + len(sig)] += sig
        self.wet[i:i + len(sig)] += sig * send


def env(n, vol, attack):
    """0.0001 -> vol linear over `attack`, then exponential decay to 0.0001 at the end."""
    a = max(1, int(attack * SR))
    e = np.empty(n)
    e[:a] = np.linspace(0.0001, vol, a)
    m = n - a
    e[a:] = vol * (0.0001 / vol) ** (np.arange(m) / max(1, m))
    return e


def partial(mix, f, start, dur, vol, send=0.3, f_end=None):
    if f > 15000:
        return
    n = int(dur * SR)
    t = np.arange(n) / SR
    if f_end:
        k = 0.6 * dur
        freq = np.where(t < k, f * (f_end / f) ** (t / k), f_end)
        phase = 2 * np.pi * np.cumsum(freq) / SR
    else:
        phase = 2 * np.pi * f * t
    mix.add(np.sin(phase) * env(n, vol, 0.004), start, send)


def noise(mix, start, dur, vol, ftype, f1, f2, q, att, send=0.3):
    n = int(dur * SR)
    x = rng.uniform(-1, 1, n)
    y = np.empty(n)
    x1 = x2 = y1 = y2 = 0.0
    qlin = q if ftype == 'bandpass' else 10 ** (q / 20)  # Web Audio: Q in dB for lp/hp
    for i in range(n):
        if i % 16 == 0:
            f = f1 * (f2 / f1) ** (i / n)
            w0 = 2 * math.pi * min(f, SR * 0.45) / SR
            cw, sw = math.cos(w0), math.sin(w0)
            al = sw / (2 * qlin)
            if ftype == 'bandpass':
                b0, b1, b2 = al, 0.0, -al
            elif ftype == 'lowpass':
                b0, b1, b2 = (1 - cw) / 2, 1 - cw, (1 - cw) / 2
            else:
                b0, b1, b2 = (1 + cw) / 2, -(1 + cw), (1 + cw) / 2
            a0, a1, a2 = 1 + al, -2 * cw, 1 - al
            b0, b1, b2, a1, a2 = b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0
        yi = b0 * x[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, x[i], y1, yi
        y[i] = yi
    mix.add(y * env(n, vol, att), start, send)


BELL = [(0.5, 0.7), (1, 1), (1.183, 0.55), (1.506, 0.45), (2, 0.35), (2.514, 0.25), (2.662, 0.2), (3.011, 0.15), (4.166, 0.08), (5.433, 0.05)]


def bell(mix, f0, start, vol, ln, send):
    for i, (m, a) in enumerate(BELL):
        partial(mix, f0 * m * (1 + (rng.random() - 0.5) * 0.003), start, ln / (1 + i * 0.5), vol * a * 0.3, send)


def clink(mix, f0, start, vol):
    for m, a, d in [(1, 1, 0.5), (2.32, 0.55, 0.32), (4.25, 0.35, 0.2), (6.63, 0.2, 0.12)]:
        partial(mix, f0 * m, start, d, vol * a, 0.25)
    noise(mix, start, 0.025, vol * 0.5, 'highpass', 7000, 7000, 0.7, 0.002, 0.1)


def pluck(mix, f, start, vol):
    partial(mix, f, start, 1.4, vol, 0.5)
    partial(mix, f * 2.01, start, 0.4, vol * 0.2, 0.5)
    partial(mix, f * 4.2, start, 0.08, vol * 0.12, 0.3)


def bounty(m):
    clink(m, 2350, 0, 0.28); clink(m, 2720, 0.12, 0.22); clink(m, 2530, 0.21, 0.14)


def power(m):
    for k, (st, f0) in enumerate([(0, 466), (0.17, 349)]):
        v = 0.85 if k else 1
        noise(m, st, 0.05, 0.35 * v, 'bandpass', 3200, 1800, 1.2, 0.001, 0.15)
        noise(m, st, 0.08, 0.25 * v, 'lowpass', 900, 300, 0.8, 0.002, 0.15)
        for mul, a, d in [(1, 1, 0.9), (2.756, 0.55, 0.5), (5.404, 0.28, 0.28), (8.933, 0.12, 0.14)]:
            partial(m, f0 * mul, st, d, 0.5 * a * v, 0.3)
            partial(m, (f0 + 2.5) * mul, st + 0.003, d * 0.85, 0.22 * a * v, 0.3)


def wisdom(m):
    for f, st in [(784, 0), (988, 0.12), (1175, 0.24), (1568, 0.38)]:
        pluck(m, f, st, 0.28)


def tormentor(m):
    noise(m, 0, 0.08, 0.25, 'lowpass', 900, 300, 0.7, 0.003, 0.3)
    bell(m, 196, 0, 1.3, 3.5, 0.45)


def reverb_ir():
    n = int(SR * 2.2)
    ir = rng.uniform(-1, 1, n) * (1 - np.arange(n) / n) ** 3.2
    return ir / np.sqrt(np.sum(ir ** 2))


def lowpass(x, fc):
    """One-pole-cascade lowpass (2 poles) approximating the 5 kHz damping filter."""
    a = math.exp(-2 * math.pi * fc / SR)
    for _ in range(2):
        y = np.empty_like(x); s = 0.0
        for i in range(len(x)):
            s = (1 - a) * x[i] + a * s
            y[i] = s
        x = y
    return x


def render(name, fn, seconds):
    m = Mix(seconds)
    fn(m)
    ir = reverb_ir()
    size = 1 << (m.n + len(ir)).bit_length()
    wet = np.fft.irfft(np.fft.rfft(m.wet, size) * np.fft.rfft(ir, size), size)[: m.n]
    wet = lowpass(wet, 5000) * 0.5
    print('  wet/dry rms', round(float(np.sqrt(np.mean(wet**2)) / np.sqrt(np.mean(m.dry**2))), 2))
    out = (m.dry + wet) * 0.9
    fade = int(0.25 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    out = np.tanh(out / np.max(np.abs(out)) * 1.4) / np.tanh(1.4) * 0.85  # normalise + gentle soft clip
    pcm = (out * 32767).astype('<i2')
    path = os.path.join(sys.argv[1], name + '.wav')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print(name, round(seconds, 2), 's', os.path.getsize(path) // 1024, 'KB')


os.makedirs(sys.argv[1], exist_ok=True)
render('bounty', bounty, 1.4)
render('power', power, 2.0)
render('wisdom', wisdom, 2.6)
render('tormentor', tormentor, 4.5)
