"""Every sound is synthesized at start-up with numpy (no audio files needed)."""
import math
import random

import numpy as np
import pygame

RATE = 44100


def _env(n, attack=0.002, decay=0.05):
    t = np.arange(n) / RATE
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-t / max(decay, 1e-4))


def _to_sound(x, vol=0.6):
    x = np.clip(x / (np.max(np.abs(x)) + 1e-9) * vol, -1, 1)
    st = np.stack([x, x], axis=1)
    return pygame.sndarray.make_sound((st * 32767).astype(np.int16))


def _clack(pitch=1.0):
    n = int(RATE * 0.09)
    t = np.arange(n) / RATE
    x = (np.sin(2 * math.pi * 2650 * pitch * t) * 0.7 + np.sin(2 * math.pi * 4300 * pitch * t) * 0.35
         + np.sin(2 * math.pi * 6900 * pitch * t) * 0.15)
    x = x * _env(n, 0.0005, 0.012) + np.random.randn(n) * _env(n, 0.0002, 0.003) * 0.5
    return x


def _thud():
    n = int(RATE * 0.16)
    t = np.arange(n) / RATE
    x = np.sin(2 * math.pi * 150 * t) * _env(n, 0.002, 0.05) + np.random.randn(n) * _env(n, 0.001, 0.012) * 0.25
    return x


def _pocket():
    n = int(RATE * 0.42)
    t = np.arange(n) / RATE
    x = np.sin(2 * math.pi * 92 * t) * _env(n, 0.003, 0.09) * 0.9
    for k in range(5):        # little rattle as the ball drops
        s = int(RATE * (0.05 + 0.045 * k + random.uniform(0, 0.01)))
        m = int(RATE * 0.03)
        if s + m < n:
            x[s:s + m] += _clack(0.55 + 0.05 * k)[:m] * (0.35 / (k + 1))
    return x


def _strike():
    n = int(RATE * 0.07)
    t = np.arange(n) / RATE
    return np.sin(2 * math.pi * 820 * t) * _env(n, 0.0005, 0.010) + np.random.randn(n) * _env(n, 0.0002, 0.004) * 0.6


def _tone(freqs, dur=0.5, decay=0.25, wave="sine"):
    n = int(RATE * dur)
    t = np.arange(n) / RATE
    x = np.zeros(n)
    for i, f in enumerate(freqs):
        s = int(i * RATE * 0.07)
        tt = t[: n - s]
        w = np.sin(2 * math.pi * f * tt)
        if wave == "square":
            w = np.sign(w) * 0.5
        x[s:] += w * np.exp(-tt / decay) * np.clip(tt / 0.004, 0, 1)
    return x


def _ambient():
    dur = 12.0
    n = int(RATE * dur)
    t = np.arange(n) / RATE
    x = np.zeros(n)
    chord = [55.0, 82.41, 110.0, 164.81]
    for i, f in enumerate(chord):
        lfo = 0.5 + 0.5 * np.sin(2 * math.pi * (0.05 + 0.02 * i) * t + i)
        x += np.sin(2 * math.pi * f * t) * lfo * 0.25
        x += np.sin(2 * math.pi * f * 2.003 * t) * lfo * 0.06
    fade = np.minimum(1, np.minimum(t / 1.5, (dur - t) / 1.5))
    return x * fade


class Sounds:
    def __init__(self):
        self.ok = False
        self.enabled = True
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(RATE, -16, 2, 512)
            pygame.mixer.set_num_channels(24)
            pygame.mixer.set_reserved(1)          # channel 0 is kept for the ambient music
            self.clacks = [_to_sound(_clack(p), 0.9) for p in (0.92, 1.0, 1.08)]
            self.thud = _to_sound(_thud(), 0.7)
            self.pocket = _to_sound(_pocket(), 0.85)
            self.strike = _to_sound(_strike(), 0.8)
            self.click = _to_sound(_tone([1320], 0.08, 0.02), 0.25)
            self.hover = _to_sound(_tone([990], 0.05, 0.015), 0.12)
            self.tick = _to_sound(_tone([1760], 0.05, 0.012), 0.22)
            self.score = _to_sound(_tone([1046.5, 1318.5, 1568.0], 0.6, 0.18), 0.35)
            self.foul = _to_sound(_tone([196, 147], 0.45, 0.2, "square"), 0.3)
            self.win = _to_sound(_tone([523.25, 659.25, 783.99, 1046.5, 1318.5], 1.6, 0.5), 0.45)
            self.ambient = _to_sound(_ambient(), 0.22)
            self.ok = True
        except Exception:
            self.ok = False

    def play(self, name, volume=1.0):
        if not (self.ok and self.enabled):
            return
        s = getattr(self, name, None)
        if s is None:
            return
        if isinstance(s, list):
            s = random.choice(s)
        ch = pygame.mixer.find_channel(True)
        if ch:
            ch.set_volume(max(0.0, min(1.0, volume)))
            ch.play(s)

    def music(self, on=True):
        if not self.ok:
            return
        if on and self.enabled:
            ch = pygame.mixer.Channel(0)
            if not ch.get_busy():
                ch.set_volume(0.5)
                ch.play(self.ambient, loops=-1)
        else:
            pygame.mixer.Channel(0).stop()
