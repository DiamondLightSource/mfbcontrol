
import pytest
from parse_mfb_feedback_log import MfbLogProcessor, MfbDebugData, CorrectionDebugData, ControlDebugData


CONTROL_LINE = "DEBUG:mfbcontrol.mfb:Calculation: value = -0.000436, k = 30, fb_k = 60, bpm_phase = -0.563435, mod_phase = 2.809657, phase_diff = 2.910093, gain_p = -0.400000, gain_i = -0.050000, bpm_amp = 0.001128, max_bpm_amp = 0.060679,mod_amp = 0.126429, integral = -0.000295, unlimited_integral=-0.000295 "
IOC_LINE = "DEBUG:mfbcontrol.ioc:Signal = 5.272345, correction = -0.000436 "
PANDA_LINE = "DEBUG:mfbcontrol.panda:Setting DAC value to 1139773225 "
PANDA_CONSOLE_LINE = "[Wed Mar 26 15:26:05 2025]DEBUG:mfbcontrol.panda:Setting DAC value to -2136286568"

MFB_LINE_MISSING_K_FIELD = "DEBUG:mfbcontrol.mfb:Calculation: value = -0.000436, k = 30, X = X, bpm_phase = -0.563435, mod_phase = 2.809657, phase_diff = 2.910093, gain_p = -0.400000, gain_i = -0.050000, bpm_amp = 0.001128, max_bpm_amp = 0.060679,mod_amp = 0.126429, integral = -0.000295, unlimited_integral=-0.000295 "

def test_mfblogprocessor_is_mfb_line_returns_true_all_fields():
    expected = True
    input = CONTROL_LINE
    lp = MfbLogProcessor()
    result = lp._is_mfb_line(input)
    assert result == expected

def test_mfblogprocessor_is_mfb_line_returns_false_missing_field():
    expected = False
    input = MFB_LINE_MISSING_K_FIELD
    lp = MfbLogProcessor()
    result = lp._is_mfb_line(input)
    assert result == expected

def test_mfblogprocessor_parse_panda_line_returns_value():
    expected = 1139773225
    input = PANDA_LINE
    lp = MfbLogProcessor()
    result = lp._parse_panda_line(input)
    assert result == expected

def test_mfblogprocessor_parse_panda_consoleline_returns_value():
    expected = -2136286568
    input = PANDA_CONSOLE_LINE
    lp = MfbLogProcessor()
    result = lp._parse_panda_line(input)
    assert result == expected

def test_mfblogprocessor_parse_ioc_line_returns_value():
    expected = CorrectionDebugData(-0.000436, 5.272345)
    input = IOC_LINE
    lp = MfbLogProcessor()
    result = lp._parse_ioc_line(input)
    assert result == expected

def test_mfblogprocessor_parse_control_line_returns_value():
    expected = ControlDebugData(-0.000436,30,60,-0.563435,2.809657,2.910093,-0.400000,-0.050000,0.001128,0.060679,0.126429,-0.000295,-0.000295)
    input = CONTROL_LINE
    lp = MfbLogProcessor()
    result = lp._parse_control_line(input)
    assert result == expected

# def test_mfblogprocessor_process_log_entries_are_created():
#     expected = 0
#     input = CONTROL_LINE
#     lp = MfbLogProcessor()
#     result = lp._parse_control_line(input)
#     assert result == expected

def test_mfblogprocessor_get_unique_categories():
    expected = set(["p-0.7i-0.04", "p-0.4i-0.05"])
    input = "./test_mfb_debug_log.txt"
    lp = MfbLogProcessor()
    lp.process_log(input)
    result = lp.get_unique_categories()
    assert result == expected


def test_mfblogprocessor_plot_parameter():
    expected = None # Graphical output manual check
    #input = "./test_mfb_debug_log.txt"
    input = "./logs/feb29-last.txt"
    lp = MfbLogProcessor()
    lp.process_log(input)
    lp.get_unique_categories()
    result = lp.plot_parameter("p-0.4i-0.05")