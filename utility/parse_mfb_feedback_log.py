from argparse import ArgumentParser
from dataclasses import dataclass
from math import isclose
import matplotlib.pyplot as plt
import re
from enum import Enum

@dataclass
class ControlDebugData:
    value: float
    k: int  # was int made float to simplify  
    fb_k: int  # int
    bpm_phase: float
    mod_phase: float
    phase_diff: float
    gain_p: float
    gain_i: float
    bpm_amp: float
    max_bpm_amp: float
    mod_amp: float
    integral: float
    unlimited_integral: float

    def __eq__(self, other):
        return isinstance(self, ControlDebugData) and isinstance(other, ControlDebugData) \
                            and isclose(self.value, other.value) \
                            and isclose(self.k, other.k) \
                            and isclose(self.fb_k, other.fb_k) \
                            and isclose(self.bpm_phase, other.bpm_phase) \
                            and isclose(self.mod_phase, other.mod_phase) \
                            and isclose(self.phase_diff, other.phase_diff) \
                            and isclose(self.gain_p, other.gain_p) \
                            and isclose(self.gain_i, other.gain_i) \
                            and isclose(self.bpm_amp, other.bpm_amp) \
                            and isclose(self.max_bpm_amp, other.max_bpm_amp) \
                            and isclose(self.mod_amp, other.mod_amp) \
                            and isclose(self.integral, other.integral) \
                            and isclose(self.unlimited_integral, other.unlimited_integral) \

@dataclass
class CorrectionDebugData:
    correction: float
    signal: float

    def __eq__(self, other):
        return isinstance(self, CorrectionDebugData) and isinstance(other, CorrectionDebugData) \
                            and isclose(self.correction, other.correction) \
                            and isclose (self.signal, other.signal)

@dataclass
class MfbDebugData:
    control:ControlDebugData
    correction: CorrectionDebugData
    pandaDac: int


class MfbLogProcessor:
    _PATTERN_SUFFIX = r" ?= ?(-?[0-9]+\.?[0-9]+)"
    control_line_fields = ["value", "k", "fb_k", "bpm_phase", "mod_phase", "phase_diff", "gain_p", "gain_i", "bpm_amp", "max_bpm_amp", "mod_amp", "integral", "unlimited_integral"]
    ioc_line_fields = ["Signal","correction"]
    log_entries = []
    _file = None

    def __init__(self):
        pass
    

    def _parse_control_line(self, line) -> ControlDebugData:
        values = ControlDebugData(None, None, None, None, None, None, None, None, None, None, None, None, None)
        for field in self.control_line_fields:
            match = re.search(field + self._PATTERN_SUFFIX, line)
            if match != None:
                setattr(values, str.lower(field) , float(match[1])) # Assumed that fields are lower case

        return values


    def _parse_ioc_line(self, line) -> CorrectionDebugData: 
        values = CorrectionDebugData(None, None)
        for field in self.ioc_line_fields:
            match = re.search(field + self._PATTERN_SUFFIX, line)
            setattr(values, str.lower(field) , float(match[1])) # Assumed that fields are lower case
        return values


    def _parse_panda_line(self, line) -> int:
        match = re.search(r"DAC value to (-?[0-9]\w+)", line)
        return int(match[1])


    def _process_one_loops_logs(self, lines:list[str]) -> MfbDebugData:
        LINES_PER_LOOP = 3
        # one loops output consits of three lines:
        #    - control
        #    - ioc
        #    - panda
        if (len(lines) != LINES_PER_LOOP):
            raise Exception("Incomplete log given to process")

        control_data = self._parse_control_line(lines[0])
        ioc_data = self._parse_ioc_line(lines[1])
        panda_data = self._parse_panda_line(lines[2])

        return MfbDebugData(control_data, ioc_data, panda_data)

    def _create_category_id(self, data:MfbDebugData):
        return "p" + str(data.control.gain_p) + "i" +str(data.control.gain_i)

    def _is_mfb_line(self, line):
        # May not detect missing small parameter names 
        return all(field in line for field in self.control_line_fields)


    def process_log(self, file: str):
        self._file = file
        with  open(file) as log:
            line = log.readline()
            cnt = 1
            while (line != ""):
                if (self._is_mfb_line(line)):
                    # Order is assumed so this could get out of order TODO add defensive handling
                    control_line = line
                    ioc_line = log.readline()
                    cnt += 1
                    panda_line = log.readline()
                    cnt += 1
                    log_entry = self._process_one_loops_logs([control_line, ioc_line, panda_line])
                    self.log_entries.append((self._create_category_id(log_entry), log_entry))
                line = log.readline()
                cnt += 1



    def get_unique_categories(self) -> list[str]:
        categories = [c[0] for c in self.log_entries] #Get all category ids
        
        categories_set = set(categories)

        categories_string = ""
        for c in categories_set:
            categories_string += c + "    "
        print(categories_string)

        return categories_set


    def plot_parameter(self, category:str):
        category_values: list[MfbDebugData] = [value[1] for value in self.log_entries if value[0]==category]

        bpm_amp = [value.control.bpm_amp for value in category_values]
        phase_diff = [value.control.phase_diff for value in category_values]
        uintegral_values = [value.control.unlimited_integral for value in category_values]
        integral_values = [value.control.integral for value in category_values]
        correction = [value.control.value for value in category_values]

        #print(str(correction))
        print(f"Displaying {len(bpm_amp)} data points of {category} from file {self._file}")

        dac = [value.pandaDac for value in category_values]

        plt.figure(self._file)
        plt.subplot(231)
        plt.plot(bpm_amp)
        plt.title('BPM amp')
        plt.draw()

        plt.subplot(232)
        plt.plot(phase_diff)
        plt.title('Phase diff')
        plt.draw()

        plt.subplot(233)
        plt.plot(uintegral_values)
        plt.draw()
        plt.plot(integral_values) # Plot limited and unlimited together for comparison
        plt.title('I')
        plt.draw()

        plt.subplot(235)
        plt.plot(correction)
        plt.title('Correction')
        plt.draw()

        plt.subplot(236)
        plt.plot(dac)
        plt.title('DAC')
        plt.draw()


        plt.suptitle(category)
        plt.show() 



class MfbLogParserAction (Enum):
    PLOT = "plot"
    CATEGORIES = "categories"

def parse_args():
    parser = ArgumentParser(
        prog= "Mfbcontrol Log Processor"
    )

    parser.add_argument('filename', help= "The log file to process.")
    parser.add_argument('action', choices= [MfbLogParserAction.PLOT.value, MfbLogParserAction.CATEGORIES.value], help="The action to perform.")
    parser.add_argument('-c', '--category', help="The category to plot.") 
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    
    FILENAME = args.filename
    ACTION = MfbLogParserAction(args.action)
    CATEGORY = args.category

    lp = MfbLogProcessor()
    lp.process_log(FILENAME)

    if ACTION == MfbLogParserAction.CATEGORIES :
        lp.get_unique_categories()

    elif ACTION == MfbLogParserAction.PLOT:
        lp.plot_parameter(CATEGORY)


if __name__ == "__main__":
    main()