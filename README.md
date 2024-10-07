[![CI](https://github.com/DiamondLightSource/mfbcontrol/actions/workflows/ci.yml/badge.svg)](https://github.com/DiamondLightSource/mfbcontrol/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/DiamondLightSource/mfbcontrol/branch/main/graph/badge.svg)](https://codecov.io/gh/DiamondLightSource/mfbcontrol)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# mfbcontrol

Python soft IOC to run the Modulation Feedback control loop using a PandABox.

The MFB control loop takes BPM positions as input and drives a piezo motor to
achieve the position of maximum beam intensity.

A PandABox with a FMC ACQ427ELF is dedicated to this purpose, if the target
PandABox is shared, make sure the blocks CLOCK1, PCAP, COUNTER1, PGEN1, CALC1
and FMC\_OUT are not affected and fully owned by this application.

The BPM channels A, B, C and D should be connected to channel 1, 2, 3 and 4 of
the FMC ADC.

The FMC DAC channel 1 should be connected to the target piezo motor amplifier.

Source          | <https://github.com/DiamondLightSource/mfbcontrol>
:---:           | :---:
Releases        | <https://github.com/DiamondLightSource/mfbcontrol/releases>

# Quickstart

The following command starts an IOC in which the initial gain is -0.3, the
threshold of the beam intensity to start controlling is 0.5 and the modulation
signal generated is a cosine wave with frequency 121Hz and amplitude 0.07V.

```
mfbcontrol-ioc PV-PREFIX panda-host --gain -0.3 --min-sig 0.5 --mod-freq 121 --mod-amp 0.07
```

# PVs provided

## `PV-PREFIX:ENABLE`

Enable/disable for the control loop.

## `PV-PREFIX:GAIN`

Gain in the control loop, note that depending on the total latency of the
system, the sign of the gain might need to be changed so that the correction
happens in the right direction.

## `PV-PREFIX:MINSIG`

Minimum BPM intensity signal average level so that the control loop kicks in.

## `PV-PREFIX:BPM:INTEN`

Current BPM intensity signal average level.

## `PV-PREFIX:BPM:FFT:AMP`

Waveform containing the amplitude of the FFT of the BPM intensity.

## `PV-PREFIX:MOD:FFT:AMP`

Waveform containing the amplitude of the FFT of the modulation signal generated.

## `PV-PREFIX:DAC:SET`

Manual control for the DAC output (in V units).

## `PV-PREFIX:DAC:SET_RBV`

Readback PV for the DAC output (in V units).
