from random import randrange
import queue
import logging
import time

# from display import Display
from kb_input import KB_Input
from timer import Timer

#References:
#https://github.com/mattmikolay/chip-8/wiki/CHIP%E2%80%908-Technical-Reference
#https://github.com/mattmikolay/chip-8/wiki/CHIP%E2%80%908-Instruction-Set
#https://github.com/Timendus/chip8-test-suite (Tests 4 and 5 helped a lot)

class Core():
    binary_data = None

    #Emulator systems
    display_queue = None
    kb_input = None
    delay_timer = None
    sound_timer = None

    #Settings
    clk_hz = None #Target frequency
    display_hz = None
    epoch_size = None #Number of instructions before the core cares about target frequency and sleeps
    #Quirks (default = CHIP8)
    quirks = {
        'vf_reset': True,
        'memory': True,
        'display_wait': True,
        'clipping': True,
        'shifting': False,
        'jumping': False
    }

    #CHIP8 structures
    display_data = None
    ram = None
    pc = None
    r_i = None
    r_v = None
    stack = None

    def __init__(self, display_queue : queue.Queue, display_hz=60):
        self.display_hz = display_hz
        self.display_queue = display_queue
        self.kb_input = KB_Input()
        self.delay_timer = Timer(self.display_hz)
    
    def setup(self, file_name, quirks:dict, clk_hz=720, epoch_size=10, debug=False):
        self.clk_hz = clk_hz
        self.epoch_size = epoch_size
        #Load program
        with open(file_name, 'rb') as file:
            self.binary_data = file.read()
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        
        self.quirks = quirks
    
    #Initialize 64x32 screen data
    def init_screen(self):
        self.display_data = [[0]*64 for _ in range(32)]
    
    def init_ram(self):
        #4096 bytes of RAM
        self.ram = bytearray(4096)
        font = [
            [0xF0, 0x90, 0x90, 0x90, 0xF0], #0
            [0x20, 0x60, 0x20, 0x20, 0x70], #1
            [0xF0, 0x10, 0xF0, 0x80, 0xF0], #2
            [0xF0, 0x10, 0xF0, 0x10, 0xF0], #3
            [0x90, 0x90, 0xF0, 0x10, 0x10], #4
            [0xF0, 0x80, 0xF0, 0x10, 0xF0], #5
            [0xF0, 0x80, 0xF0, 0x90, 0xF0], #6
            [0xF0, 0x10, 0x20, 0x40, 0x40], #7
            [0xF0, 0x90, 0xF0, 0x90, 0xF0], #8
            [0xF0, 0x90, 0xF0, 0x10, 0xF0], #9
            [0xF0, 0x90, 0xF0, 0x90, 0x90], #A
            [0xE0, 0x90, 0xE0, 0x90, 0xE0], #B
            [0xF0, 0x80, 0x80, 0x80, 0xF0], #C
            [0xE0, 0x90, 0x90, 0x90, 0xE0], #D
            [0xF0, 0x80, 0xF0, 0x80, 0xF0], #E
            [0xF0, 0x80, 0xF0, 0x80, 0x80]  #F
        ]
        i = 0
        for c in font:
            for line in c:
                self.ram[i] = line
                i += 1
    
    def skip_next(self):
        self.pc += 2

    def run(self):
        self.init_screen()
        self.init_ram()
        self.display_queue.put(self.display_data)
        self.display_queue.join()
        #Program Counter
        self.pc = 0x200
        #Address register
        self.r_i = 0x0
        #Data registers
        self.r_v = [0]*16
        #Stack
        self.stack = []

        #Load program into memory
        self.ram[0x200:(0x200+len(self.binary_data))] = self.binary_data

        #Epoch initialization
        epoch_counter = 0
        epoch_start = time.time()
        epoch_display_time = 0
        epoch_input_time = 0
        while True:
            inst = int.from_bytes(self.ram[self.pc:self.pc+2])
            prev_inst = inst
            logging.debug(f" inst={inst:x}, PC={self.pc:x}, I={self.r_i:x}")
            display_updated = False
            jumping = False
            if inst == 0x00E0:
                display_updated = True
                self.init_screen()
                logging.debug(f"00E0 Clear screen")
            elif inst == 0x00EE:
                self.pc = self.stack.pop()
                logging.debug(f"00EE Returned")
            elif inst <= 0x0FFF:
                self.stack.append(self.pc)
                self.pc = inst
                logging.debug(f"{inst:x} Execute Machine Subroutine")
                jumping = True
            elif inst >= 0x1000 and inst <= 0x1FFF:
                self.pc = inst % 0x1000
                logging.debug(f"{inst:x} Jump")
                jumping = True
            elif inst >= 0x2000 and inst <= 0x2FFF:
                self.stack.append(self.pc)
                self.pc = inst % 0x2000
                logging.debug(f"{inst:x} Execute Subroutine")
                jumping = True
            elif inst >= 0x3000 and inst <= 0x3FFF:
                inst %= 0x1000
                x = inst // 0x100 #2nd digit
                n = inst % 0x100 #3rd and 4th digits
                if self.r_v[x] == n:
                    self.skip_next()
                logging.debug(f"Skip if V{x:x} ({self.r_v[x]}) == {n}")
            elif inst >= 0x4000 and inst <= 0x4FFF:
                inst %= 0x1000
                x = inst // 0x100 #2nd digit
                n = inst % 0x100 #3rd and 4th digits
                if self.r_v[x] != n:
                    self.skip_next()
                logging.debug(f"Skip if V{x:x} ({self.r_v[x]}) != {n}")
            elif inst >= 0x5000 and inst <= 0x5FFF:
                inst %= 0x1000
                x = inst // 0x100 #2nd digit
                y = (inst % 0x100) // 0x10 #3rd digit
                if inst % 0x10 != 0:
                    logging.warning(f"Unexpected digit {inst % 0x10:x} at the end of 0x5XY0 op")
                if self.r_v[x] == self.r_v[y]:
                    self.skip_next()
                logging.debug(f"Skip if V{x:x} ({self.r_v[x]}) != V{y:x} ({self.r_v[y]})")
            elif inst >= 0x6000 and inst <= 0x6FFF:
                inst %= 0x1000
                x = inst // 0x100 #2nd digit
                n = inst % 0x100 #3rd and 4th digits
                self.r_v[x] = n
                logging.debug(f"Store {n:x} in V{x:x}")
            elif inst >= 0x7000 and inst <= 0x7FFF:
                inst %= 0x1000
                x = inst // 0x100 #2nd digit
                n = inst % 0x100 #3rd and 4th digits
                self.r_v[x] += n
                self.r_v[x] %= 0b1_0000_0000 #Restrict itself to 8 bits
                logging.debug(f"{inst:x} V{x:x} += {n:x}")
            elif inst >= 0x8000 and inst <= 0x8FFF: #TEST 0x7
                inst %= 0x1000
                x = inst // 0x100 #2nd digit
                inst %= 0x100
                y = inst // 0x10 #3rd digit
                op = inst % 0x10 #4th digit
                match op:
                    case 0x0:
                        self.r_v[x] = self.r_v[y]
                        logging.debug(f"V{x:x} = V{y:x} ({self.r_v[y]})")
                    case 0x1:
                        self.r_v[x] |= self.r_v[y]
                        if self.quirks['vf_reset']:
                            self.r_v[0xF] = 0x0
                        logging.debug(f"V{x:x} ({self.r_v[x]}) |= V{y:x} ({self.r_v[y]})")
                    case 0x2:
                        self.r_v[x] &= self.r_v[y]
                        if self.quirks['vf_reset']:
                            self.r_v[0xF] = 0x0
                        logging.debug(f"V{x:x} ({self.r_v[x]}) &= V{y:x} ({self.r_v[y]})")
                    case 0x3:
                        self.r_v[x] ^= self.r_v[y]
                        if self.quirks['vf_reset']:
                            self.r_v[0xF] = 0x0
                        logging.debug(f"V{x:x} ({self.r_v[x]}) ^= V{y:x} ({self.r_v[y]})")
                    case 0x4:
                        self.r_v[x] += self.r_v[y]
                        logging.debug(f"V{x:x} ({self.r_v[x]}) += V{y:x} ({self.r_v[y]})")
                        self.r_v[0xF] = (
                            0x01 if self.r_v[x] >= 0b1_0000_0000 else
                            0x00
                        )
                        self.r_v[x] %= 0b1_0000_0000 #Restrict itself to 8 bits
                    case 0x5:
                        res = self.r_v[x] - self.r_v[y]
                        logging.debug(f"V{x:x} ({self.r_v[x]}) -= V{y:x} ({self.r_v[y]})")
                        if res < 0:
                            self.r_v[x] = res + 2**8
                            self.r_v[0xF] = 0x00
                        else:
                            self.r_v[x] = res
                            self.r_v[0xF] = 0x01
                        self.r_v[x] %= 0b1_0000_0000 #Restrict itself to 8 bits
                    case 0x6:
                        if self.quirks['shifting']:
                            flag = self.r_v[x] % 0b10
                            self.r_v[x] = self.r_v[x] >> 1
                            self.r_v[0xF] = flag
                            logging.debug(f"V{x:x} = V{x:x} >> 1 ({self.r_v[x]})")
                        else:
                            flag = self.r_v[y] % 0b10
                            self.r_v[x] = self.r_v[y] >> 1
                            self.r_v[0xF] = flag
                            logging.debug(f"V{x:x} = V{y:x} >> 1 ({self.r_v[y]})")
                    case 0x7:
                        res = self.r_v[y] - self.r_v[x]
                        logging.debug(f"V{x:x} = V{y:x} ({self.r_v[y]}) - V{x:x} ({self.r_v[x]})")
                        if res < 0:
                            self.r_v[x] = res + 2**8
                            self.r_v[0xF] = 0x00
                        else:
                            self.r_v[x] = res
                            self.r_v[0xF] = 0x01
                        self.r_v[x] %= 0b1_0000_0000 #Restrict itself to 8 bits
                    case 0xE:
                        if self.quirks['shifting']:
                            flag = self.r_v[x] // 0b1000_0000
                            self.r_v[x] = self.r_v[x] << 1
                            self.r_v[x] %= 0b1_0000_0000 #Restrict itself to 8 bits
                            self.r_v[0xF] = flag
                            logging.debug(f"V{x:x} = V{x:x} << 1 ({self.r_v[x]})")
                        else:
                            flag = self.r_v[y] // 0b1000_0000
                            self.r_v[x] = self.r_v[y] << 1
                            self.r_v[x] %= 0b1_0000_0000 #Restrict itself to 8 bits
                            self.r_v[0xF] = flag
                            logging.debug(f"V{x:x} = V{y:x} << 1 ({self.r_v[y]})")
                    case _:
                        logging.warning(f"Unexpected digit {op:x} at the end of 0x8XY_ op")
            elif inst >= 0x9000 and inst <= 0x9FFF:
                inst %= 0x1000
                x = inst // 0x100 #2nd digit
                y = (inst % 0x100) // 0x10 #3rd digit
                if self.r_v[x] != self.r_v[y]:
                    self.skip_next()
                logging.debug(f"Skip if V{x:x} ({self.r_v[x]}) != V{y:x} ({self.r_v[y]})")
            elif inst >= 0xA000 and inst <= 0xAFFF:
                self.r_i = inst % 0x1000
                logging.debug(f"Set I to {self.r_i:x}")
            elif inst >= 0xB000 and inst <= 0xBFFF: #TEST
                if self.quirks['jumping']:
                    xnn = inst % 0x1000
                    x = xnn // 0x100 #2nd digit
                    self.pc = xnn + self.r_v[x]
                else:
                    self.pc = (inst % 0x1000) + self.r_v[0]
                continue
            elif inst >= 0xC000 and inst <= 0xCFFF:
                inst %= 0x1000
                x = inst // 0x100 #2nd digit
                n = inst % 0x100 #3rd and 4th digits
                self.r_v[x] = randrange(0b1_0000_0000) & n
            elif inst >= 0xD000 and inst <= 0xDFFF:
                display_updated = True
                inst %= 0x1000
                x = self.r_v[inst // 0x100] #2nd digit
                inst %= 0x100 
                y = self.r_v[inst // 0x10] #3rd digit
                n = inst % 0x10 #4th digit
                x %= 64
                y %= 32
                set_to_unset = False
                for j, byte in enumerate(self.ram[self.r_i : self.r_i+n]):
                    res_y = y + j
                    if self.quirks['clipping']:
                        if res_y >= 32:
                            break
                    else:
                        res_y %= 32
                    for i, bit in enumerate(bin(byte).removeprefix('0b').zfill(8)):
                        res_x = x + i
                        if self.quirks['clipping']:
                            if res_x >= 64:
                                break
                        else:
                            res_x %= 64
                        bit = int(bit)
                        prev = self.display_data[res_y][res_x]
                        if prev == 1 and bit == 1:
                            set_to_unset = True
                        self.display_data[res_y][res_x] ^= bit
                self.r_v[0xF] = 0x1 if set_to_unset else 0x0
            elif inst >= 0xE000 and inst <= 0xEFFF: #TEST
                inst %= 0x1000
                x = inst // 0x100 #2nd digit
                op = inst % 0x100 #3rd and 4th digits
                match op:
                    case 0x9E:
                        if self.kb_input.is_pressed(self.r_v[x]):
                            self.skip_next()
                    case 0xA1:
                        if not self.kb_input.is_pressed(self.r_v[x]):
                            self.skip_next()
                    case _:
                        logging.error(f"Unexpected digits {op:x} at the end of 0xEX__ op")
            elif inst >= 0xF000 and inst <= 0xFFFF:
                inst %= 0x1000
                x = inst // 0x100 #2nd digit
                op = inst % 0x100 #3rd and 4th digits
                match op:
                    case 0x07: #TEST
                        self.r_v[x] = self.delay_timer.timer
                    case 0x0A: #TEST
                        input_time = time.time()
                        self.r_v[x] = self.kb_input.last_key.get()
                        input_time = time.time() - input_time
                        epoch_input_time += input_time
                    case 0x15: #TEST
                        self.delay_timer.timer = self.r_v[x]
                    case 0x18: #TEST
                        #TODO: find cross platform way to beep
                        #and also be able to interrupt the beep
                        0 == 0
                    case 0x1E:
                        self.r_i += self.r_v[x]
                        logging.debug(f"I ({self.r_i}) += V{x:x} ({self.r_v[x]})")
                    case 0x29:
                        self.r_i = (self.r_v[x] % 0x10)*5 #Font data has 5 bytes each and starts at 0x000
                    case 0x33:
                        v = self.r_v[x] % 1000
                        self.ram[self.r_i]   = v // 100
                        self.ram[self.r_i+1] = (v % 100) // 10
                        self.ram[self.r_i+2] = v % 10
                    case 0x55:
                        self.ram[self.r_i:self.r_i+x+1] = bytes(self.r_v[0:x+1])
                        logging.debug(f"RAM[{self.r_i}:{self.r_i+x+1}] = V[0:{x+1:x}] ({bytes(self.r_v[0:x+1])})")
                        if self.quirks['memory']:
                            self.r_i += x + 1
                    case 0x65: #TEST
                        self.r_v[0:x+1] = [v % 0b1_0000_0000 for v in self.ram[self.r_i:self.r_i+x+1]]
                        logging.debug(f"V[0:{x+1}] = RAM[{self.r_i}:{self.r_i+x+1}]")
                        if self.quirks['memory']:
                            self.r_i += x + 1
                    case _:
                        logging.error(f"Unexpected digits {op:x} at the end of 0xFX__ op")
            
            if not jumping:
                self.pc += 2

            #Update display if it's a relevant instruction
            if display_updated:
                display_time = time.time()
                self.display_queue.put(self.display_data)
                self.display_queue.join()
                display_time = time.time() - display_time
                epoch_display_time += display_time

            #After {epoch_size} instructions, check how much faster it was executed than
            #the target frequency, and sleep to make up for it
            epoch_counter += 1
            if epoch_counter == self.epoch_size:
                #Disregard time waiting for display to refresh and for user to press a key
                disregarded_time = epoch_display_time + epoch_input_time
                remaining_time = self.epoch_size*1./self.clk_hz - (time.time() - epoch_start - disregarded_time)
                if remaining_time < 0:
                    logging.warning(
                        f"Epoch took {abs(remaining_time)*1000:.2f}ms too long to meet {self.clk_hz}Hz "
                        f"({self.epoch_size*1000/self.clk_hz:.2f}ms to do {self.epoch_size} cycles):\r\n"
                        f"Display: {epoch_display_time*1000:.2f}ms; Input: {epoch_input_time*1000:.2f}ms; "
                        f"Last instruction: {prev_inst:x}"
                    )
                time.sleep(max(remaining_time, 0))
                epoch_counter = 0
                epoch_start = time.time()
                epoch_display_time = 0
                epoch_input_time = 0
