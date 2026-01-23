import string
from random import choices, randint

import matplotlib
import numpy as np
import sounddevice as sd
from matplotlib import pyplot as plt
from scipy.io.wavfile import write

matplotlib.use("TkAgg")
from scipy.signal import spectrogram

sr = 44100
tone_dur = 0.2
gap_dur = 0.01

# base_freqs = np.array([60 * (3 / 2) ** i for i in range(8)])
base = 100
base_freqs = [base * (r + 1) for r in range(8)]
# top_freqs = np.array([x + 2000 for x in base_freqs])
print(base_freqs)


def goertzel(frame, sr, freqs):
    n = len(frame)
    result = []
    for f in freqs:
        k = int(0.5 + n * f / sr)
        w = 2 * np.pi * k / n
        coeff = 2 * np.cos(w)

        s_prev = 0
        s_prev2 = 0
        for sample in frame:
            s = sample + coeff * s_prev - s_prev2
            s_prev2 = s_prev
            s_prev = s
        power = s_prev2**2 + s_prev**2 - coeff * s_prev * s_prev2
        result.append(power)
    return np.array(result)


def generate_fade(length_samples):
    fade = np.hanning(length_samples * 2)
    return fade[:length_samples], fade[length_samples:]


def generate_tone(freq, duration=tone_dur):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    signal = np.sin(2 * np.pi * freq * t)
    fade_in, fade_out = generate_fade(int(sr * tone_dur))
    signal[: len(fade_in)] *= fade_in
    signal[-len(fade_out) :] *= fade_out
    return signal / np.max(np.abs(signal)) * 0.5  # normalize max amplitude


def bucket_energy(fft_freqs, magnitudes, target_freq, bandwidth=5):
    mask = np.abs(fft_freqs - target_freq) <= bandwidth
    return np.sum(magnitudes[mask])


def detect_byte(frame, t):
    powers = goertzel(frame, sr, base_freqs)

    # Inline noise floor estimation from midpoints between base freqs
    noise_bins = [
        (base_freqs[i] + base_freqs[i + 1]) / 2 for i in range(len(base_freqs) - 1)
    ]
    noise_floor = np.mean(goertzel(frame, sr, noise_bins))

    adjusted = powers - noise_floor

    threshold = np.max(adjusted) * t  # or set a fixed value if preferred
    bits = (adjusted > threshold).astype(int)
    byte = int("".join(map(str, bits[::-1])), 2)
    return byte


def generate_chord_for_byte(byte):
    tlen = int(sr * tone_dur)
    signal = np.zeros(tlen)
    for i, base_f in enumerate(base_freqs):
        if (byte >> i) & 1:
            signal += generate_tone(base_f)
    max_amp = np.max(np.abs(signal)) + 1e-9
    signal = signal / max_amp * 0.8
    return signal


def encode_waveform(data: bytes):
    if not isinstance(data, bytes):
        raise ValueError
    gap = np.zeros(int(sr * gap_dur))
    out = []
    for i, b in enumerate(data):
        out.append(generate_chord_for_byte(b))
        out.append(gap)
    signal = np.concatenate(out) if out else np.array([])
    return signal


def decode_waveform(wave, t=0.5) -> bytes:
    step = int(sr * (tone_dur + gap_dur))
    tone_len = int(sr * tone_dur)
    decoded = []
    for i in range(0, len(wave) - step + 1, step):
        frame = wave[i : i + tone_len]
        byte = detect_byte(frame, t)
        decoded.append(byte)
    return bytes(decoded)


def plot_maxres_spectrogram(wave, sr):
    nperseg = 16384  # very high frequency resolution (~1.5 Hz at sr=44100)
    noverlap = int(nperseg * 0.75)

    f, t, Sxx = spectrogram(
        wave,
        sr,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        scaling="spectrum",
        mode="magnitude",
    )

    sxxdb = 20 * np.log10(Sxx + 1e-10)

    plt.figure(figsize=(14, 6))
    plt.pcolormesh(t, f, sxxdb, shading="gouraud", cmap="magma")
    plt.ylabel("Frequency [Hz]")
    plt.xlabel("Time [s]")
    plt.colorbar(label="dB")
    plt.ylim(0, 2500)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    msg = ("NULLSIGNAL" * 13).encode()
    print("Encoding message:", msg)
    wave = encode_waveform(msg)
    print("Playing encoded message...")
    sd.play(wave, sr)

    print("Decoding message...")
    decoded = decode_waveform(wave)
    print("Decoded message:", decoded)

    wave = wave / np.max(np.abs(wave))
    write("output.wav", sr, wave.astype(np.float32))
    exit()

    def rand_string():
        return "".join(choices(string.ascii_letters, k=randint(10, 15)))

    sr, crowdnoise = wavfile.read(os.path.expanduser("~/Documents/crowd.wav"))

    def add_noise(signal, noise_level, crowd):
        crowd = crowd[: len(signal)]  # trim to match
        if crowd.ndim > 1:  # stereo → mono
            crowd = crowd.mean(axis=1)
        crowd = crowd.astype(np.float32)
        crowd = crowd / np.max(np.abs(crowd))  # normalize
        return signal + crowd * noise_level

    noisy = []
    res = {}

    m = rand_string()
    wave = encode_waveform(m.encode())
    for noise_level in np.linspace(0, 3, 50):

        noisy = add_noise(wave, noise_level, crowdnoise)
        decoded = decode_waveform(noisy, 0.2).decode(errors="replace")

        print(m, decoded)

        if decoded != m:
            # sd.play(noisy, sr)
            print(f"Failure at noise level: {noise_level}")
            # write("noisy.wav", sr, noisy.astype(np.float32))
            break
    else:
        res[t] = 3
        pass  # sd.play(noisy, sr)
    print(res)
    sd.play(noisy, sr)
    # plot_maxres_spectrogram(wave, sr)
    sd.wait()
