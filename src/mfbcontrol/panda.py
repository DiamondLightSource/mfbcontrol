import logging
from sys import deactivate_stack_trampoline
import numpy as np

from pathlib import Path
from numpy.typing import ArrayLike

from pandablocks.asyncio import AsyncioClient
from pandablocks.commands import Arm, Get, Put, SetState
from pandablocks.responses import FrameData, ReadyData

DAC_MAX = 2**31 - 1
DAC_MIN = -2**31
EGU_MAX = 10.0


def to_dac_units(val: float) -> float:
    return np.round(val * DAC_MAX / EGU_MAX, 0)


def from_dac_units(val: float) -> float:
    return val * EGU_MAX / DAC_MAX


class MFBPandaManager(object):
    def __init__(self, host: str, client: AsyncioClient = None):
        self.host = host
        self.connected = False
        self.client = client
        self.dac_value = 0
        self.log = logging.getLogger(__name__)
        self.mod_enabled = False

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    async def connect(self):
        if not self.connected:
            self.client = AsyncioClient(self.host)
            await self.client.connect()
            self.connected = True

    async def configure(self, mod_wave: ArrayLike, samp_freq: int):
        await self.set_modulation_wave(mod_wave)
        await self.set_trigger_period(1 / samp_freq)
        await self.load_state(str(Path(__file__).parent / 'panda_mfb.sav'))
        self.mod_enabled = True
        await self.arm_if_needed()
        self.dac_value = await self.get_dac_raw_value()

    def is_modulation_enabled(self):
        return self.mod_enabled

    async def get_dac_raw_value(self):
        return int(await self.client.send(Get('COUNTER1.OUT')))

    async def set_dac_value(self, value):
        cval = int(to_dac_units(value))
        self.dac_value = cval
        await self.client.send(Put('COUNTER1.SET', cval))

    async def adjust_dac(self, diff: float):
        self.dac_value += int(to_dac_units(diff))
        if self.dac_value > DAC_MAX:
            self.dac_value = DAC_MAX
        elif self.dac_value < DAC_MIN:
            self.dac_value = DAC_MIN

        self.log.debug('Setting DAC value to %d', self.dac_value)
        await self.client.send(Put('COUNTER1.SET', self.dac_value))

    async def close(self):
        if self.connected:
            await self.client.close()
            self.connected = False

    async def set_modulation_wave(self, wave: ArrayLike):
        await self.client.send(
            Put('PGEN1.TABLE',
                [str(int(np.round(to_dac_units(i)))) for i in wave]))

    async def set_modulation_enable(self, enable: bool):
        self.mod_enabled = enable
        await self.client.send(
            Put('PGEN1.ENABLE', 'PCAP.ACTIVE' if enable else 'ZERO'))

    async def set_trigger_period(self, period: float):
        await self.client.send(Put('CLOCK1.PERIOD', period))

    async def arm_if_needed(self):
        if (await self.client.send(Get('PCAP.ACTIVE'))) == '0':
            await self.client.send(Arm())

    async def load_state(self, filepath: str):
        with open(filepath, 'r') as f:
            state = f.read().split()

        await self.client.send(SetState(state))

    async def collect_mfb_signals(self, n_samples: int):
        bpm_data = np.zeros((n_samples,))
        mod_data = np.zeros((n_samples,))
        line_number = 0
        async for data in self.client.data():
            if isinstance(data, ReadyData):
                line_number = 0
            elif isinstance(data, FrameData):
                for line in data.data:
                    bpm_data[line_number] = \
                        line[1] + line[2] + line[3] + line[4]
                    mod_data[line_number] = from_dac_units(line[0])
                    line_number += 1
                    if line_number >= n_samples:
                        line_number = 0
                        yield bpm_data, mod_data
