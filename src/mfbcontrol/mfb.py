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


def max_value(value: float, max: float) -> float:
    m = abs(max)
    return limit_value(value, (m*-1), m)

def limit_value(value: float, min: float, max: float) -> float:
    if value > max:
        return max
    elif value < min:
        return min
    else:
        return value


class MfbCalculator(object):
    control_period = None
    max_integral = None
    
    integral = 0
    bpm_fft = None
    mod_fft = None
    bpm_fft_amp = None
    mod_fft_amp = None

    def __init__(self, control_period, max_integral,):
        self.control_period = control_period
        self.max_integral = max_integral

    def process_inputs(self, bpm_data: ArrayLike, mod_data: ArrayLike):
        self.bpm_fft = fft.fft(bpm_data)
        self.mod_fft = fft.fft(mod_data)
        self.bpm_fft_amp = np.absolute(self.bpm_fft) * 2 / len(bpm_data)
        self.mod_fft_amp = np.absolute(self.mod_fft) * 2 / len(mod_data)

    def get_bpm_amp(self):
        return self.bpm_fft_amp
    
    def get_mod_amp(self):
        return self.mod_fft_amp

    def calculate_correction(self, gain_p: int, gain_i: int):
        # skip DC and beyond Nyquist
        k = np.argmax(self.mod_fft_amp[1:len(self.mod_fft_amp) // 2]) + 1
        fb_k = np.argmax(self.bpm_fft_amp[1:len(self.bpm_fft_amp) // 2]) + 1
        bpm_amp = self.bpm_fft_amp[k]
        max_bpm_amp = self.bpm_fft_amp[fb_k]
        bpm_phase = np.angle(self.bpm_fft)[k]
        mod_amp = self.mod_fft_amp[k]
        mod_phase = np.angle(self.mod_fft)[k]
        phase_diff = normalise_phase(bpm_phase - mod_phase)
        error = np.sign(phase_diff) * bpm_amp
        unlimited_integral = self.integral + error * self.control_period
        self.integral = max_value(unlimited_integral, self.max_integral)

        correction = gain_p * error + gain_i * self.integral

        log.debug(
            'Calculation: value = %f, k = %d, fb_k = %d, '
            'bpm_phase = %f, mod_phase = %f, phase_diff = %f, '
            'gain_p = %f, gain_i = %f, bpm_amp = %f, max_bpm_amp = %f,'
            'mod_amp = %f, integral = %f, unlimited_integral=%f',
            correction, k, fb_k, bpm_phase, mod_phase, phase_diff, gain_p, gain_i,
            bpm_amp, max_bpm_amp, mod_amp, self.integral, unlimited_integral)
        
        return CorrectionResult(correction, int(k), self.bpm_fft_amp, self.mod_fft_amp)


def create_modulation_signal(mod_freq: int, mod_amp: float, samp_freq: int,
                             duration: float) -> ArrayLike:
    t = np.linspace(0, duration, samp_freq)
    return np.cos(mod_freq * 2 * np.pi * t) * mod_amp
