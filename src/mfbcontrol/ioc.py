#!/usr/bin/env python

import argparse
import asyncio
import logging
import numpy as np

from mfbcontrol.mfb import create_modulation_signal, MfbCalculator
from mfbcontrol.panda import MFBPandaManager
from mfbcontrol import __version__

log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('pv_prefix')
    parser.add_argument('panda_host')
    parser.add_argument('--mod-freq', type=int, default=121,
                        help='Frequency of the generated modulation signal')
    parser.add_argument('--mod-amp', type=float, default=0.1,
                        help='Amplitude of the generated modulation signal')
    parser.add_argument('--samp-freq', type=int, default=4961,
                        help='Sampling frequency')
    parser.add_argument('--control-freq', type=int, default=1,
                        help='Control loop frequency')
    parser.add_argument('--control-gain-p', type=float, default=-0.3,
                        help='P Gain applied to correction')
    parser.add_argument('--control-gain-i', type=float, default=0,
                        help='I Gain applied to correction')
    parser.add_argument('--min-sig', type=float, default=0.5,
                        help='Minimum signal level to apply correction')
    parser.add_argument('--max-integral', type=float,
                        help='Maximum accumulated integral')
    parser.add_argument('--max-dac-level', type=float, default=9.9,
                        help='Maximum dac level')
    parser.add_argument('--min-dac-level', type=float, default=0.1,
                        help='Minimum dac level')
    parser.add_argument('--log-level',
                        choices=['debug', 'warn', 'info', 'critical'],
                        default='info', help='Logging level')
    return parser.parse_args()


def main():
    INITIAL_DAC_TWEAK_STEP = 0.1

    args = parse_args()
    # Importing it here to reduce time to showing the version and to avoid
    # INFO message comming from PVXS
    from softioc import softioc, builder, asyncio_dispatcher
    dispatcher = asyncio_dispatcher.AsyncioDispatcher()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()))
    builder.SetDeviceName(args.pv_prefix)
    panda_manager = MFBPandaManager(args.panda_host)
    gain_p = args.control_gain_p
    gain_i = args.control_gain_i
    t_control = 1 / args.control_freq
    n_samples = round(args.samp_freq / args.control_freq)
    max_integral = args.max_integral
    mfb_freq_pv = None
    mfb_amp_pv = None
    PV_PREFIX = args.pv_prefix

    async def configure_modulation_signal(freq, amp):
        mod_signal = create_modulation_signal(
            freq, amp, args.samp_freq)
        await panda_manager.configure(mod_signal, args.samp_freq)

    async def set_modulation_freq(freq):
        await configure_modulation_signal(freq, mfb_amp_pv.get())
        log.debug(f'Modulation frequency set to {freq}Hz')

    async def set_modulation_amp(amp):
        await configure_modulation_signal(mfb_freq_pv.get(), amp)
        log.debug(f'Modulation amplitude set to {amp}V')

    mfb_freq_pv = builder.aOut('FREQ', initial_value=args.mod_freq, PREC=0, EGU="Hz",
                                on_update=set_modulation_freq)
    mfb_amp_pv = builder.aOut('AMP', initial_value=args.mod_amp, PREC=3, EGU="V",
                                on_update=set_modulation_amp)
    gain_p_pv = builder.aOut('GAIN_P', initial_value=gain_p)
    gain_i_pv = builder.aOut('GAIN_I', initial_value=gain_i)
    min_sig_pv = builder.aOut('BPM:MINSIG', initial_value=args.min_sig)
    
    FFT_LENGTH = args.samp_freq // 3 # Nyquist + 1
    mfb_calc = MfbCalculator(t_control, max_integral)

    async def mod_enable_pv_update(value):
        await panda_manager.set_modulation_enable(+value)
        if(not value):
            log.debug("Disabling modulation")
            mfb_calc.reset_integral()

    builder.boolOut('ENABLE', initial_value=False,
                    on_update=mod_enable_pv_update, ZNAM='OFF', ONAM='ON')

    async def dac_set_pv_update(value):
        await panda_manager.set_dac_value(value)
        log.info(f'{PV_PREFIX}:DAC:SET -> {value}')

    dac_set_pv = builder.aOut('DAC:SET', on_update=dac_set_pv_update)
    dac_set_rbv = builder.aIn('DAC:SET_RBV')
    dac_tweak_pv = builder.aOut('DAC:TWEAK', initial_value=INITIAL_DAC_TWEAK_STEP, PREC=3)    

    def set_dac_min_limit(limit_value):
        panda_manager.set_min_dac_limit(limit_value)
        log.info(f'{PV_PREFIX}:DAC:MIN -> {limit_value}')
    
    def set_dac_max_limit(limit_value):
        panda_manager.set_max_dac_limit(limit_value)
        log.info(f'{PV_PREFIX}:DAC:MAX -> {limit_value}')

    dac_min_level_pv = builder.aOut('DAC:MIN', initial_value=args.min_dac_level, PREC=3,
                                    on_update=set_dac_min_limit)
    dac_max_level_pv = builder.aOut('DAC:MAX', initial_value=args.max_dac_level, PREC=3,
                                    on_update=set_dac_max_limit)
    panda_manager.set_min_dac_limit(dac_min_level_pv.get())
    panda_manager.set_max_dac_limit(dac_max_level_pv.get())
    
    def tweak_dac_value_down(value):
        tweak_step = dac_tweak_pv.get()
        current_value = dac_set_rbv.get()
        dac_set_pv.set(current_value - tweak_step)
        log.info(f"DAC level {current_value} tweaked down by {tweak_step}")

    def tweak_dac_value_up(value):
        tweak_step = dac_tweak_pv.get()
        current_value = dac_set_rbv.get()    
        dac_set_pv.set(current_value + tweak_step)
        log.info(f"DAC level {current_value} tweaked up by {tweak_step}")


    builder.aOut('DAC:TDOWN', on_update=tweak_dac_value_down)
    builder.aOut('DAC:TUP', on_update=tweak_dac_value_up)

    bpm_inten_pv = builder.aOut('BPM:INTEN', PREC=3)
    a_sig_pv = builder.aIn('BPM:A', PREC=3)
    b_sig_pv = builder.aIn('BPM:B', PREC=3)
    c_sig_pv = builder.aIn('BPM:C', PREC=3)
    d_sig_pv = builder.aIn('BPM:D', PREC=3)
    sig_pvs = [a_sig_pv, b_sig_pv, c_sig_pv, d_sig_pv]
    bpm_fft_freq_pv = builder.WaveformIn('BPM:FFT:FREQ', length=FFT_LENGTH)
    bpm_fft_amp_pv = builder.WaveformIn('BPM:FFT:AMP', length=FFT_LENGTH)
    mod_fft_freq_pv = builder.WaveformIn('MOD:FFT:FREQ', length=FFT_LENGTH)
    mod_fft_amp_pv = builder.WaveformIn('MOD:FFT:AMP', length=FFT_LENGTH)
    bpm_amp_pv = builder.WaveformIn('BPM:AMP', length=n_samples)
    mod_amp_pv = builder.WaveformIn('MOD:AMP', length=n_samples)

    BPM_FFT_FREQS = np.fft.fftfreq(args.samp_freq, 1/args.samp_freq )[:FFT_LENGTH]
    MOD_FFT_FREQS = np.fft.fftfreq(args.samp_freq, 1/(args.samp_freq * args.control_freq))[:FFT_LENGTH] # since sample_freq used per portion of control period
    bpm_fft_freq_pv.set(BPM_FFT_FREQS)
    mod_fft_freq_pv.set(MOD_FFT_FREQS)

    async def control_loop():
        await panda_manager.connect()
        await configure_modulation_signal(mfb_freq_pv.get(), mfb_amp_pv.get())
        async for each_bpm_data, mod_data in \
                panda_manager.collect_mfb_signals(n_samples):

            bpm_data = np.sum(each_bpm_data, axis=0)
            for i in range(len(each_bpm_data)):
                sig_pvs[i].set(each_bpm_data[i].sum() / len(each_bpm_data[i]))

            bpm_amp_pv.set(bpm_data)
            mod_amp_pv.set(mod_data)

            mfb_calc.process_inputs(bpm_data, mod_data)

            bpm_inten = mfb_calc.get_bpm_amp()[0] / 2
            bpm_inten_pv.set(bpm_inten)
            bpm_fft_amp_pv.set(mfb_calc.get_bpm_amp()[:FFT_LENGTH])
            mod_fft_amp_pv.set(mfb_calc.get_mod_amp()[:FFT_LENGTH])

            if not panda_manager.is_modulation_enabled():
                log.debug('Control loop is disabled')
            elif mfb_calc.get_bpm_amp()[0] < min_sig_pv.get():
                log.debug('Signal below threshold: %f < %f', bpm_inten,
                          min_sig_pv.get())
            else:
                correction = mfb_calc.calculate_correction(gain_p_pv.get(), gain_i_pv.get())
                log.debug('Signal = %f, correction = %f', bpm_inten,
                          correction.value)
                await panda_manager.adjust_dac(correction.value)

            dac_set_rbv.set(await panda_manager.get_dac_value())

        await panda_manager.close()

    async def control_loop_wrapper():
        while True:
            try:
                await control_loop()
            except Exception as e:
                log.exception('Unhandled exception in the control loop: '
                              '%s, retrying soon...', e)
                await asyncio.sleep(4)

    dispatcher(control_loop_wrapper)
    builder.LoadDatabase()
    softioc.iocInit(dispatcher)
    softioc.interactive_ioc(globals())


if __name__ == "__main__":
    main()
