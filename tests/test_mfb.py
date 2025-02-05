from pytest import mark, approx, fixture
import numpy as np

from mfbcontrol import mfb

from pv_data import pv_data_1
from expected_data import calc_pv_data_1

def test_create_modulation_signal():
    result = mfb.create_modulation_signal(mod_freq=10, mod_amp=0.1,
                                          samp_freq=20, duration=1)
    assert np.allclose(result,
                       0.1 * np.cos(2 * np.pi * 10 * np.linspace(0, 1.0, 20)))


@mark.parametrize("value,limit,expected", 
                         [(-0.499, 0.500, -0.499), # Above min
                          (-0.500, 0.500, -0.500), # Equal min
                          (-0.501, 0.500, -0.500), # Below min
                          (0.499, 0.500, 0.499), # Below max
                          (0.500, 0.500, 0.500), # Equal max
                          (0.501, 0.500, 0.500), # Above max
                          ])
def test_max_value(value, limit, expected):
    assert mfb.max_value(value, limit) == approx(expected)

@fixture
def mfbcalculator1():
    return mfb.MfbCalculator(0.5, 10)

@fixture
def data_1():
    return pv_data_1

@fixture
def expected_data_1():
    return calc_pv_data_1

@fixture
def mfbcalculator1_process_data1(mfbcalculator1, data_1) -> mfb.MfbCalculator:
    mfbcalculator1.process_inputs(data_1['bpm_amp'], data_1['mod_amp'])
    return mfbcalculator1

def test_mfbcalculator_process_inputs_mod_amp(mfbcalculator1, data_1, expected_data_1):
    expected = np.array(expected_data_1['mod_fft_amp'])

    mfbcalculator1.process_inputs(data_1['bpm_amp'], data_1['mod_amp'])
    result = np.array(mfbcalculator1.mod_fft_amp)
    
    np.testing.assert_array_almost_equal_nulp(result, expected)


def test_mfbcalculator_process_inputs_bpm_amp(mfbcalculator1, data_1, expected_data_1):
    expected = np.array(expected_data_1['bpm_fft_amp'])

    mfbcalculator1.process_inputs(data_1['bpm_amp'], data_1['mod_amp'])
    result = np.array(mfbcalculator1.bpm_fft_amp)
    
    np.testing.assert_array_almost_equal_nulp(result, expected)


def test_mfbcalculator_get_bpm_amp(mfbcalculator1, data_1, expected_data_1):
    expected = np.array(expected_data_1['bpm_fft_amp'])

    mfbcalculator1.process_inputs(data_1['bpm_amp'], data_1['mod_amp'])
    result = np.array(mfbcalculator1.get_bpm_amp())
    
    np.testing.assert_array_almost_equal_nulp(result, expected)


def test_mfbcalculator_get_mod_amp(mfbcalculator1, data_1, expected_data_1):
    expected = np.array(expected_data_1['mod_fft_amp'])

    mfbcalculator1.process_inputs(data_1['bpm_amp'], data_1['mod_amp'])
    result = np.array(mfbcalculator1.get_mod_amp())

    np.testing.assert_array_almost_equal_nulp(result, expected)


def test_mfbcalculator_calculate_correction_mod_amp(mfbcalculator1_process_data1, expected_data_1):
    P_GAIN = -0.3
    I_GAIN = 0
    expected = np.array(expected_data_1['mod_fft_amp'])

    result = mfbcalculator1_process_data1.calculate_correction(P_GAIN,I_GAIN)

    np.testing.assert_array_almost_equal_nulp(np.array(result.mod_fft_amp), expected)
    

def test_mfbcalculator_calculate_correction_bpm_amp(mfbcalculator1_process_data1, expected_data_1):
    P_GAIN = -0.3
    I_GAIN = 0
    expected = np.array(expected_data_1['bpm_fft_amp'])

    result = mfbcalculator1_process_data1.calculate_correction(P_GAIN,I_GAIN)

    np.testing.assert_array_almost_equal_nulp(np.array(result.bpm_fft_amp), expected)


def test_mfbcalculator_calculate_correction_value(mfbcalculator1_process_data1):
    P_GAIN = -0.3
    I_GAIN = 0
    expected = -0.002399722350920076
    result = mfbcalculator1_process_data1.calculate_correction(P_GAIN,I_GAIN)
    assert result.value == approx(expected)


def test_mfbcalculator_calculate_correction_target_freq_k(mfbcalculator1_process_data1):
    P_GAIN = -0.3
    I_GAIN = 0
    expected = 30
    result = mfbcalculator1_process_data1.calculate_correction(P_GAIN,I_GAIN)
    assert result.target_freq_k == expected
