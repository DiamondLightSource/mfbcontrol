#!/usr/bin/env python

import argparse
import asyncio
import logging

from mfbcontrol.mfb import create_modulation_signal, calculate_correction
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
    parser.add_argument('--control-gain', type=float, default=-0.3,
                        help='Gain applied to correction')
    parser.add_argument('--min-sig', type=float, default=0.5,
                        help='Minimum signal level to apply correction')
    parser.add_argument('--log-level',
                        choices=['debug', 'warn', 'info', 'critical'],
                        default='info', help='Logging level')
    return parser.parse_args()


def main():
    args = parse_args()
    # Importing it here to reduce time to showing the version and to avoid
    # INFO message comming from PVXS
    from softioc import softioc, builder, asyncio_dispatcher
    dispatcher = asyncio_dispatcher.AsyncioDispatcher()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()))
    builder.SetDeviceName(args.pv_prefix)
    panda_manager = MFBPandaManager(args.panda_host)
    gain = args.control_gain
    min_sig = args.min_sig
    t_control = 1 / args.control_freq
    n_samples = round(args.samp_freq / args.control_freq)
    gain_pv = builder.aOut('GAIN', initial_value=gain)

    async def mod_enable_pv_update(value):
        await panda_manager.set_modulation_enable(+value)

    builder.boolOut('ENABLE', initial_value=True,
                    on_update=mod_enable_pv_update)

    async def dac_set_pv_update(value):
        await panda_manager.set_dac_value(value)

    builder.aOut('DAC:SET', on_update=dac_set_pv_update)
    bpm_inten_pv = builder.aOut('BPM:INTEN')
    bpm_fft_amp_pv = builder.WaveformIn('FFT:BPM:AMP', length=n_samples)
    mod_fft_amp_pv = builder.WaveformIn('FFT:MOD:AMP', length=n_samples)

    async def control_loop():
        await panda_manager.connect()
        mod_signal = create_modulation_signal(
            args.mod_freq, args.mod_amp, args.samp_freq, t_control)
        await panda_manager.configure(mod_signal, args.samp_freq)
        async for bpm_data, mod_data in \
                panda_manager.collect_mfb_signals(n_samples):
            correction = calculate_correction(bpm_data, mod_data,
                                              gain_pv.get())
            bpm_inten_pv.set(correction.bpm_fft_amp[0])
            bpm_fft_amp_pv.set(correction.bpm_fft_amp)
            mod_fft_amp_pv.set(correction.mod_fft_amp)
            if not panda_manager.is_modulation_enabled():
                log.debug('Control loop is disabled')
                continue

            if correction.bpm_fft_amp[0] < min_sig:
                log.debug('Signal below threshold: %f < %f',
                          correction.bpm_fft_amp[0], min_sig)
            else:
                log.debug('Signal = %f, correction = %f',
                          correction.bpm_fft_amp[0], correction.value)
                await panda_manager.adjust_dac(correction.value)

        await panda_manager.close()

    dispatcher(control_loop)
    builder.LoadDatabase()
    softioc.iocInit(dispatcher)
    softioc.interactive_ioc(globals())


if __name__ == "__main__":
    main()
