#!/usr/bin/env python
import asyncio
import logging
import numpy as np

from dataclasses import dataclass
from enum import Enum, auto
from numpy.typing import ArrayLike
from typing import Optional
from scipy import fft
from scipy._lib.uarray import set_state

from mfbcontrol.panda import MFBPandaManager

log = logging.getLogger(__name__)


@dataclass
class CorrectionResult:
    value: float
    target_freq_k: int
    bpm_fft_amp: ArrayLike
    mod_fft_amp: ArrayLike


def normalise_phase(phase: float) -> float:
    while phase > np.pi:
        phase -= 2 * np.pi

    while phase < -np.pi:
        phase += 2 * np.pi

    return phase


def calculate_correction(bpm_data: ArrayLike, mod_data: ArrayLike,
                         gain: float) -> CorrectionResult:
    bpm_fft = fft.fft(bpm_data)
    mod_fft = fft.fft(mod_data)
    bpm_fft_amp = np.absolute(bpm_fft) * 2 / len(bpm_data)
    mod_fft_amp = np.absolute(mod_fft) * 2 / len(mod_data)

    # skip DC and beyond Nyquist
    k = np.argmax(mod_fft_amp[1:len(mod_fft_amp) // 2]) + 1
    fb_k = np.argmax(bpm_fft_amp[1:len(bpm_fft_amp) // 2]) + 1
    bpm_amp = bpm_fft_amp[k]
    max_bpm_amp = bpm_fft_amp[fb_k]
    bpm_phase = np.angle(bpm_fft)[k]
    mod_amp = mod_fft_amp[k]
    mod_phase = np.angle(mod_fft)[k]
    phase_diff = normalise_phase(bpm_phase - mod_phase)
    correction = np.sign(phase_diff) * gain * bpm_amp
    log.debug(
        'Calculation: value = %f, k = %d, fb_k = %d, '
        'bpm_phase = %f, mod_phase = %f, phase_diff = %f, '
        'gain = %f, bpm_amp = %f, max_bpm_amp = %f, mod_amp = %f',
        correction, k, fb_k, bpm_phase, mod_phase, phase_diff, gain, bpm_amp,
        max_bpm_amp, mod_amp)
    return CorrectionResult(correction, int(k), bpm_fft_amp, mod_fft_amp)


def create_modulation_signal(mod_freq: int, mod_amp: float, samp_freq: int,
                             duration: float) -> ArrayLike:
    t = np.linspace(0, duration, samp_freq)
    return np.cos(mod_freq * 2 * np.pi * t) * mod_amp
