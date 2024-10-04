import numpy as np

from mfbcontrol import mfb


def test_create_modulation_signal():
    result = mfb.create_modulation_signal(mod_freq=10, mod_amp=0.1,
                                          samp_freq=20, duration=1)
    assert np.allclose(result,
                       0.1 * np.cos(2 * np.pi * 10 * np.linspace(0, 1.0, 20)))
