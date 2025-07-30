# Copyright (c) gzip
# Licensed under CC BY-NC-SA 4.0 https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en

import math, os, sys, time, argparse
from py65emu.cpu import CPU
from py65emu.mmu import MMU

DEBUG = False

def shift_left(val, count):
  return val << count

def shift_right(val, count):
  return val >> count

def to_16_bit(hi, lo):
  return (hi << 8) + lo

def bytes_to_hex(bytes):
  return ' '.join(list(map(lambda v: f'{v:02X}', bytes)))

def k(val):
  return val * 1024

PRG_SIZE = [k(512), k(256), k(128), k(64), k(32), k(16), k(8), k(2048)]
CHR_SIZE = [k(256), k(128), k(64),  None,  k(32), k(16), k(8), None]

PRG_SIZE_HDR = [0x20, 0x10, 0x08, 0x04, 0x02, 0x01, None, 0x80]
CHR_SIZE_HDR = [0x20, 0x10, 0x08, None, 0x04, 0x02, 0x01, None]

PRG_SIZE_K = ["512k", "256k", "128k", "64k", "32k", "16k", "8k", "2048k"]
CHR_SIZE_K = ["256k", "128k", "64k", "Invalid", "32k", "16k", "8k", "Invalid"]

# look for mapper specific signatures (not guaranteed)
def guess_mapper(data):

  if data.find(b'\x8D\x10\x20') != -1 or \
     data.find(b'\x2C\x10\x20') != -1: # STA $2010 / xor'd
    mapper = 256
  elif data.find(b'\x8D\x01\x80') != -1 or \
       data.find(b'\x8E\x01\x80') != -1:     # STA/STX $8001 $8001
    mapper = 4
  elif data.find(b'\x8D\x00\xE0\x4A') != -1 or \
       data.find(b'\x8D\x00\xC0\x4A') != -1 or \
       data.find(b'\x8D\x00\xA0\x4A') != -1:     # STA $E000/$C000/$A000 LSR
    mapper = 1
  else:
    mapper = 0
  return mapper

def write_header(handle, bank, mapper):

  handle.write(b'NES\x1A')
  handle.write(bank["prgSizeHeader"].to_bytes())
  handle.write(bank["chrSizeHeader"].to_bytes())

  mirror = bank["mirror"] & 1

  if mapper == 256:
    handle.write(mirror.to_bytes())
    handle.write(b"\x0B\x01")
    handle.write(b"\0"*7)
  else:
    if mapper == 4:
      mirror ^= mirror
    handle.write((mapper << 4 | mirror).to_bytes())
    handle.write(b"\0"*9)

def write_rom(file_handle, title, bank, args):

  rom = {}
  file_handle.seek(bank["prgAddr"])
  rom["prg"] = file_handle.read(bank["prgSize"])

  rom["mapper"] = guess_mapper(rom["prg"])

  # adjust values for OneBus
  if (rom["mapper"] == 256):
    bank["chrAddr"] = shift_left(bank["chrAddr"], 1)
    chrSizeIndex = bank["chrSizeIndex"]
    if (chrSizeIndex != 0):
      chrSizeIndex -= 1
      if (CHR_SIZE[chrSizeIndex] == None):
        chrSizeIndex -= 1
    elif bank["mirror"] == 1: # coincidental workaround for broken games in gamer_v
      chrSizeIndex = 2

    bank["chrSize"] = CHR_SIZE[chrSizeIndex]
    bank["chrSizeK"] = CHR_SIZE_K[chrSizeIndex]
    bank["chrSizeHeader"] = CHR_SIZE_HDR[chrSizeIndex]
    bank["chrSizeIndex"] = chrSizeIndex

  file_handle.seek(bank["chrAddr"])
  rom["chr"] = file_handle.read(bank["chrSize"])

  if (args.rom_fn != None):
    args.rom_fn(rom, args)

  file_path = os.path.join(args.outdir, title) + ".nes"
  print ("extracting " + file_path + (" (mapper " + str(rom["mapper"]) + ") from data:" if DEBUG else ""))
  with open(file_path, "wb") as rom_handle:
    write_header (rom_handle, bank, rom["mapper"])
    rom_handle.write(rom["prg"])
    rom_handle.write(rom["chr"])
    rom_handle.close()

  if DEBUG:
    modified_bytes = "oldBytes" in bank.keys()
    bytes = bank["bytes"] if not modified_bytes else bank["oldBytes"]
    print ("    " + bytes + " :: " + str(bank["prgSizeK"]) + " PRG @ " + bank["prgAddrHex"] + " / " + str(bank["chrSizeK"]) + " CHR @ " + bank["chrAddrHex"])
    if modified_bytes:
      print ("    " + bank["bytes"])

def process_titles(file_handle, args):

  separator = args.separator
  end = args.end
  max_titles = args.count

  title_len = 0
  titles = []

  while (title_len < 30):
    title_len = 0
    title = ""
    byte = file_handle.read(1)
    if (int.from_bytes(byte) == end):
      break
    while (int.from_bytes(byte) != separator):
      title += byte.decode('utf-8')
      byte = file_handle.read(1)
      title_len += 1
      if (title_len == 30):
        break
    if (title_len < 30):
      titles.append(title)
      if (len(titles) >= max_titles):
        break

  return titles

def process_banks(file_handle, args):

  data = []

  max = args.count if "data_count" not in args else args.data_count
  while (len(data) < max):
    bytes = file_handle.read(args.size)
    info = args.process_fn(bytes, args)
    if info:
      data.append(info)
    else:
      break
  return data

# indices:
#    outerBank - the value written to $4100
#    prgSize   - the value written to $410B
#    chrBank0  - the value written to $2018
#    chrBank1  - the value written to $201A
#    prgBank0  - the value written to $4107
#    mirror    - the value written to $4106 or $A000
def process_bank(bytes, indices, chr_offset = None):

  data = {}
  data["bytes"] = bytes_to_hex(bytes)

  # PRG info
  data["prgAddr"] = shift_left(to_16_bit(shift_right(bytes[indices["outerBank"]], 4), bytes[indices["prgBank0"]]), 13)
  data["prgAddrHex"] = f'{data["prgAddr"]:07X}'
  prg_size_index = bytes[indices["prgSize"]]
  data["prgSize"] = PRG_SIZE[prg_size_index]
  data["prgSizeK"] = PRG_SIZE_K[prg_size_index]
  data["prgSizeHeader"] = PRG_SIZE_HDR[prg_size_index]

  # chr_offset may vary by device
  if (chr_offset is None):
    chr_offset = (bytes[indices["outerBank"]] & 0b00001111) * 0x200000

  data["chrAddr"] = chr_offset + shift_left(to_16_bit(shift_right(bytes[indices["chrBank0"]], 4), bytes[indices["chrBank1"]] & 0b11111000), 10)
  data["chrAddrHex"] = f'{data["chrAddr"]:07X}'

  chr_size_index = bytes[indices["chrBank1"]] & 0b00000111

  data["chrSizeIndex"] = chr_size_index
  data["chrSize"] = CHR_SIZE[chr_size_index]
  data["chrSizeK"] = CHR_SIZE_K[chr_size_index]
  data["chrSizeHeader"] = CHR_SIZE_HDR[chr_size_index]

  data["mirror"] = bytes[indices["mirror"]] ^ 1
  return data

# this is required to be called first if using process_dynamic_bank
# args:
#    code_addr  - the physical code address in the dump
#    code_len   - the length of the code we're going to execute
#    mem_addr   - the expected memory addr for the code_addr (optional, may affect JMP/JSR etc)
#    start_addr - the memory address we want to start execution at if different than mem_addr
def setup_emu(file_handle, args):

  # grab the chunk of 6502 that we want to execute
  file_handle.seek(args.code_addr)
  asm = file_handle.read(args.code_len)
  #print(bytes_to_hex(asm))
  mem = MMU([
    (0x00, 0xFFFF, False, asm, args.mem_addr), # create the full nes memory space to catch register writes
    # note that we'd have problems if we happened to be executing code at an address that's also a register
  ])
  cpu_addr = args.mem_addr if "start_addr" not in args else args.start_addr
  cpu = CPU(mem, cpu_addr)
  args.cpu = cpu
  args.mem = mem
  return args

# this processes a game's bank data by executing 6502 from the dump.
# it then reads the resulting registers for final processing and extraction
def process_dynamic_bank(bytes, args):

  # make sure we start executing from the beginning each time
  args.cpu.r.pc = args.mem_addr if "start_addr" not in args else args.start_addr

  # set up expected memory values
  for i, byte in enumerate(bytes):
    args.mem.write(args.bank_data_addr + i, byte)

  # execute the code, stopping at the magic number found by debugging,
  # or by printing pc until it breaks (uncomment the print line below)
  # stop_addr must point to an instruction
  while (args.cpu.r.pc != args.stop_addr):
    #print(f'{args.cpu.r.pc:04X}')
    args.cpu.step(args.xor_val)

  indices = {
    "outerBank":0, "chrBank0":1, "chrBank1":2,
    "prgSize":3, "prgBank0":4, "prgBank1":5, "prgBank2":6, "prgBank3":7, "mirror": 8
    #"exGfx1": 9, "mapper": 10, "encryption": 11, "outerBank1":12, "outerBank2":13
  }

  newbytes = bytearray()
  for reg in [0x4100, 0x2018, 0x201A, 0x410B, 0x4107, 0x4108, 0x4109, 0x410A, 0xA000]:
             #0x2010, 0x411D, 0x411E, 0x412C, 0x412E]:
    newbytes.append(args.mem.read(reg))
    #print('{0:04X}: {1:02X}'.format(reg, args.mem.read(reg)), end=", ")

  # set mirror
  if "mirror_byte" in args:
    newbytes[8] = bytes[args.mirror_byte]

  # work around bad data
  if (args.device in ["qss","lets_play"] and newbytes[4] == 0 and newbytes[0] < 4 and newbytes[0] > 1):
    newbytes[4] = newbytes[6] - 0x0E
    newbytes[5] = newbytes[7] - 0x0E

  data = process_bank(newbytes, indices)

  data["oldBytes"] = bytes_to_hex(bytes)

  return data


# this reads the title pointer data and then processes each title.
# it must also save the bank data index so that the proper title is applied to each rom
def process_indexed_titles(file_handle, args):

  titles = []
  pointers = []
  args.indices = []
  p = 0

  file_handle.seek(args.indices_addr)
  ct = args.count
  max = ct if "data_count" not in args else args.data_count
  while (p < max):
    lo = int.from_bytes(file_handle.read(1))
    hi = int.from_bytes(file_handle.read(1))
    i  = int.from_bytes(file_handle.read(1))
    file_handle.read(1) # discard the last byte which is always 0

    if (p < ct):
      val = args.titles_offset + to_16_bit(hi, lo)
      pointers.append(val)

    # this is how the correct title will be applied later
    args.indices.append(i)

    p += 1

  args.count = 1
  for pointer in pointers:
    file_handle.seek(pointer)
    titles.extend(process_titles(file_handle, args))
  args.count = ct

  return titles

# this reads the bank index data
def setup_retrogame(file_handle, args):

  p = 0
  args.indices = []

  file_handle.seek(0x7B800)
  while (p < args.count):
    i  = int.from_bytes(file_handle.read(1))
    file_handle.read(3) # skip next 3 bytes (2 byte address plus 1 byte value)

    # associate the correct title with the corresponding bank data
    args.indices.append(i)
    p += 1

def process_retro_game_box_bank(bytes, args):

  indices = {"outerBank":0, "prgSize":1, "chrBank0":2, "chrBank1":3, "prgBank0":4, "prgBank1":5, "mirror": 6}
  chr_offset = (bytes[indices["outerBank"]] & 0x02) * 0x200000
  data = process_bank(bytes, indices, chr_offset)
  return data

def process_retrogame_bank(bytes, args):

  if bytes[0] == 0xFF:
    return None

  indices = {"outerBank":0, "chrBank0":1, "chrBank1":2, "prgSize":3, "prgBank0":4, "prgBank1":5, "prgBank2":6, "prgBank3":7, "mirror": 8}
  data = process_bank(bytes, indices)
  return data

# check if we should NOP out 3 bytes of JSR $6100
def process_gamer_v_rom(rom, args):

  seq = b"\x20\x00\x61"
  if (seq in rom["prg"]):
    # make mutable before continuing
    rom["prg"] = bytearray(rom["prg"])
    # no guarantee this is accurate
    addr = rom["prg"].find(seq)
    for i in range(3):
      rom["prg"][addr + i] = 0xEA


def set_args(args, defaults):

  keys = vars(args).keys()
  for key in defaults:
    if not key in keys or args.__dict__[key] == None:
      args.__dict__[key] = defaults[key]

def export():

  parser, args = parse_args()

  error = ""

  if args.debug:
    globals()['DEBUG'] = True

  args.process_fn = None
  args.rom_fn = None
  args.titles_fn = process_titles
  args.banks_fn = process_banks

  args.xor_val = None

  if args.device == "retro_game_box":
    set_args(args, {
      "titles": 0x6A1BC,
      "banks": 0x6E000,
      "separator": 255,
      "end": 0,
      "size": 8
    })
    args.process_fn = process_retro_game_box_bank

  elif args.device == "retrogame":
    set_args(args, {
      "titles": 0x7C010,
      "banks": 0x7B000,
      "separator": 0,
      "end": 0,
      "size": 9,
      "count": 128
    })
    args.setup_fn = setup_retrogame
    args.process_fn = process_retrogame_bank

  elif args.device == "hkb_502":
    set_args(args, {
      "titles": 0x7C010,
      "banks": 0x7B000,
      "separator": 0,
      "end": 255,
      "size": 9,
      "count": 268
    })
    args.setup_fn = setup_retrogame
    args.process_fn = process_retrogame_bank

  elif args.device == "jl3000":
    set_args(args, {
      "titles": 0x7BA6A,
      "banks": 0x7A900,
      "separator": 0,
      "end": 255,
      "size": 9
    })
    args.process_fn = process_retrogame_bank

  elif args.device == "mini_arcade":
    set_args(args, {
      "titles": 0x6867E,
      "banks": 0x6C1E0,
      "separator": 255,
      "end": 255,
      "size": 12,
      "count": 240,
      # expected by setup_emu
      "code_addr": 0x7E899,
      "code_len": 200,
      "mem_addr": 0x020D,
      # expected by process_dynamic_bank
      "bank_data_addr": 0x0200,
      "stop_addr": 0x2D5,
      "mirror_byte": 0x0B
    })
    args.setup_fn = setup_emu
    args.process_fn = process_dynamic_bank

  # identical to mini_arcade except for code_addr
  elif args.device == "arcade_zone":
    set_args(args, {
      "titles": 0x6867E,
      "banks": 0x6C1E0,
      "separator": 255,
      "end": 255,
      "size": 12,
      "count": 240,
      # expected by setup_emu
      "code_addr": 0x7E88F,
      "code_len": 200,
      "mem_addr": 0x020D,
      # expected by process_dynamic_bank
      "bank_data_addr": 0x0200,
      "stop_addr": 0x2D5,
      "mirror_byte": 0x0B
    })
    args.setup_fn = setup_emu
    args.process_fn = process_dynamic_bank

  elif args.device == "qss":
    set_args(args, {
      "titles": 0x7C506,
      "banks": 0x7CE62,
      "separator": 255,
      "end": 0,
      "size": 9,
      # expected by setup_emu
      "code_addr": 0x7E46F,
      "code_len": 1500,
      "mem_addr": 0xE46F,
      # expected by process_dynamic_bank
      "bank_data_addr": 0x0600,
      "start_addr": 0xE8AA,
      "stop_addr": 0x232,
      # expected by process_indexed_titles
      "indices_addr": 0x7C13A,
      "titles_offset": 0x70000,
      "count": 240
    })
    args.setup_fn = setup_emu
    args.titles_fn = process_indexed_titles
    args.process_fn = process_dynamic_bank

  elif args.device == "lets_play":
    set_args(args, {
      "titles": 0x7C506,
      "banks": 0x7CE62,
      "separator": 255,
      "end": 0,
      "size": 9,
      # expected by setup_emu
      "code_addr": 0x7E46F,
      "code_len": 1500,
      "mem_addr": 0xE46F,
      # expected by process_dynamic_bank
      "bank_data_addr": 0x0600,
      "start_addr": 0xE8AA,
      "stop_addr": 0x232,
      # expected by process_indexed_titles
      "indices_addr": 0x7C13A,
      "titles_offset": 0x70000,
      "count": 200
    })
    args.setup_fn = setup_emu
    args.titles_fn = process_indexed_titles
    args.process_fn = process_dynamic_bank

  elif args.device == "oplayer":
    set_args(args, {
      "titles": 0x6CB2F,
      "banks": 0x6D2E5,
      "separator": 255,
      "end": 0,
      "size": 0x0C,
      # expected by setup_emu
      "code_addr": 0x7E372,
      "code_len": 0xE5,
      "mem_addr": 0x0410,
      # expected by process_dynamic_bank
      "bank_data_addr": 0x0400,
      "stop_addr": 0x04F4,
      "mirror_byte": 0x0B,
      # expected by process_indexed_titles
      "indices_addr": 0x6C8D5,
      "titles_offset": 0x64000,
      "count": 150
    })
    args.setup_fn = setup_emu
    args.titles_fn = process_indexed_titles
    args.process_fn = process_dynamic_bank

  elif args.device == "gamer_v":
    set_args(args, {
      "titles": 0x70680,
      "banks": 0x71335,
      "separator": 255,
      "end": 0,
      "size": 0x0C,
      # expected by setup_emu
      "code_addr": 0x7E4F2,
      "code_len": 0xF0,
      "mem_addr": 0x0410,
      # expected by process_dynamic_bank
      "bank_data_addr": 0x0400,
      "stop_addr": 0x0500,
      "mirror_byte": 0x0B,
      "xor_val": 0xA1,
      # expected by process_indexed_titles
      "indices_addr": 0x702D8,
      "titles_offset": 0x68000,
      "count": 220,
      "data_count": 248
    })
    args.setup_fn = setup_emu
    args.titles_fn = process_indexed_titles
    args.process_fn = process_dynamic_bank
    args.rom_fn = process_gamer_v_rom

  if args.filename == None:
    error += f'\nError: Filename is required!'
  elif not os.path.isfile(args.filename):
    error += f'\nError: File "{args.filename}" not found!'
    args.filename = ""

  if args.titles == None:
    error += f'\nError: Titles address is required!'

  if args.banks == None:
    error += f'\nError: Banks address is required!'

  if args.size == None:
    error += f'\nError: Entry size is required!'

  if args.separator == None:
    error += f'\nError: Title separator character is required!'

  if args.end == None:
    error += f'\nError: Title end character is required!'

  if args.outdir:
    if not os.path.isdir(args.outdir):
      os.makedirs(args.outdir)
  else:
    error += f'\nError: Outdir is required!'

  if args.count == None:
    args.count = 1000

  if args.outdir and args.filename and args.titles and args.banks and args.size:
    with open(args.filename, "rb") as file_handle:

      if ("setup_fn" in args):
        args.setup_fn(file_handle, args)

      file_handle.seek(args.titles)
      titles = args.titles_fn(file_handle, args)

      args.count = len(titles)
      file_handle.seek(args.banks)
      banks = args.banks_fn(file_handle, args)

      for i in range(min(len(titles), len(banks))):
        bankIndex = i if "indices" not in args else args.indices[i]
        if bankIndex < len(banks):
          print (f'{i+1:03n}. ', end = '')
          write_rom(file_handle, titles[i], banks[bankIndex], args)
        else:
          print (f'{i+1:03n}. Index {i} not found for {titles[i]}')

  else:
    print ('\n')
    parser.print_help()

  if error:
    print (f'{error}\n')

def dec(val):
  return int(val, 16)

def parse_args():

    parser = argparse.ArgumentParser(description="Extracts roms from a multicart dump.", add_help=False, epilog='Pass the required arguments to begin parsing roms.')

    parser.add_argument('--help', action="help")
    parser.add_argument('-f', '--filename', help='Input filename.')
    parser.add_argument('-t', '--titles', help='Address of title information, e.g. 0xA03F.', type=dec)
    parser.add_argument('-b', '--banks', help='Address of bank information, e.g. 0x6A000.', type=dec)
    parser.add_argument('-z', '--size', help='Size of each bank data entry, e.g. 9.', type=int)
    parser.add_argument('-s', '--separator', help='Character used to separate titles, e.g. 255.')
    parser.add_argument('-e', '--end', help='Character used to end titles, e.g. 0.', type=int)
    parser.add_argument('-d', '--device', help='Device name (automatically sets values for the required arguments).', choices=["arcade_zone", "gamer_v", "hkb_502", "jl3000", "mini_arcade", "oplayer", "qss", "retro_game_box", "retrogame","lets_play"])
    parser.add_argument('-c', '--count', help='Max number of roms to parse, e.g. 10.', type=int)
    parser.add_argument('-o', '--outdir', help='Output directory.')
    parser.add_argument('-g', '--debug', help='Enable debug output.', action='store_true')

    args = parser.parse_args()

    return parser, args

if __name__ == "__main__":
    export()
