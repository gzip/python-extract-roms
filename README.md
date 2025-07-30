# ROM Extraction Utility
A command line utility to extract the roms from firmware dumps of various handhelds.

## Supported Devices
The following devices are currently supported:

| Name | Photo | Link |
| --- | --- | --- |
| Arcade Zone | <img src="images/arcade_zone.jpg" alt="Photo of Arcade Zone by Legami Milano" width="200"> | ([on nesdev](https://forums.nesdev.org/viewtopic.php?p=301774#p301774)) |
| My Arcade Gamer V | <img src="images/gamer_v.jpg" alt="Photo of My Arcade Gamer V" width="200"> | ([MAME dgun2573](https://www.google.com/search?q=mame+dgun2573)) |
| Gaminja GC31 / Gameruns Retrogame | <img src="images/gaminja_gc31.jpg" alt="Gaminja GC31 Handheld Console" width="200"> | ([on nesdev](https://forums.nesdev.org/viewtopic.php?p=298744#p298744)) |
| Gaminja GC36 / Gameruns Retro Game Box | <img src="images/gaminja_gc36.jpg" alt="Photo of GC36 Handheld Console" width="200"> | ([on nesdev](https://forums.nesdev.org/viewtopic.php?p=298602#p298602)) |
| HKB-502 | <img src="images/hkb-502.jpg" alt="Photo of HKB-502 Handheld Console" width="200"> | ([on nesdev](https://forums.nesdev.org/viewtopic.php?p=252679#p252679)) |
| Lexibook JL3000 Power Cyber Arcade | <img src="images/lexibook_jl3000.jpg" alt="Photo of Lexibook JL3000 Handheld Console" width="200"> | ([on nesdev](https://forums.nesdev.org/viewtopic.php?p=265765&hilit=dump#p265765)) |
| Oplayer MGS2401A | <img src="images/oplayer.jpg" alt="Photo of Oplayer MGS2401A Handheld Console" width="200"> | ([on nesdev](https://forums.nesdev.org/viewtopic.php?p=257743#p257743)) |
| Thumbs Up Orb Retro Arcade | <img src="images/thumbs_up_orb_mini_arcade.jpg" alt="Photo of Thumbs Up Orb Retro Arcade Handheld Console" width="200"> | ([on nesdev](https://forums.nesdev.org/viewtopic.php?p=284160#p284160)) |
| QSS Retro Arcade | <img src="images/qss_retro_arcade.jpg" alt="Photo of QSS Retro Arcade Handheld Console" width="200"> | ([on nesdev](https://forums.nesdev.org/viewtopic.php?p=300556#p300556)) |
| Lets Play Retro Arcade | <img src="images/letsplay_retro_arcade.jpg" alt="Photo of Lets Play Retro Arcade Handheld Console" width="200"> | ([on nesdev](https://forums.nesdev.org/viewtopic.php?p=303309#p303309)) |

## Running the Script
Examples of typical execution:
```
python extract_roms.py -f "arcade_zone.bin" -d arcade_zone -o dump\arcade_zone -g
python extract_roms.py -f "gamer_v.bin" -d gamer_v -o dump\gamer_v -g
python extract_roms.py -f "hkb-502.bin" -d hkb-502 -o dump\hkb-502 -g
python extract_roms.py -f "jl3000.bin" -d jl3000 -o dump\jl3000 -g
python extract_roms.py -f "mini_arcade.bin" -d mini_arcade -o dump\mini_arcade -g
python extract_roms.py -f "oplayer.bin" -d oplayer -o dump\oplayer -g
python extract_roms.py -f "retro_game_box.bin" -d retro_game_box -o dump\retro_game_box -g
python extract_roms.py -f "retrogame.bin" -d retrogame -o dump\retrogame -g
python extract_roms.py -f "qss.bin" -d qss -o dump\qss -g
python extract_roms.py -f "letsplay_arcade.bin" -d lets_play -o dump\lets_play -g
```

## Replacing ROMs

The -g option outputs additional information that can be used to _manually replace_ one of the existing roms in your dump.

1. Find an existing rom in the output that matches the same PRG and CHR size as the rom you'd like to replace it with.
2. Use a utility like [famiROM](https://gbatemp.net/download/famirom-2019-01-13.37661/download) or [NES Rom Splitter](https://www.romhacking.net/utilities/683/) to split up the new rom into separate chunks of PRG and CHR data.
3. Then use a hex editor like [HxD](https://mh-nexus.de/en/downloads.php?product=HxD20) to paste the respective chunks in the firmware dump at the hex addresses given with the -g option, overwriting the existing data.
4. Locate the title with a text search and replace it with the title of your new rom, making sure not to overflow the provided title space.

```
extracting dump\qss\Vangvard.nes (mapper 4) from data:
    4C 00 F0 12 08 00 D0 02 00 :: 128k PRG @ 0020000 / 128k CHR @ 05A0000
    02 60 81 02 10 11 1E 1F 00
```

## Testing Modifications

The raw dumps require an ines header to be added in order to run in [NintendulatorNRS](https://unlicensed.games/libg/static.php?page=NintendulatorNRS). Here are a few headers that may work with the various dumps.

```
4E 45 53 1A 00 00 00 0B 01 01 07 00 00 0A 00 00 (4MB dump, mapper 256)
4E 45 53 1A 00 00 00 0B 01 02 07 00 00 0A 00 00 (8MB dump, mapper 256)
4E 45 53 1A 00 00 B0 AB 01 04 07 00 01 0A 00 00 (16MB dump, mapper 427)
```

## Dumping and Programming Firmware
The most friendly firmwares are on 8-pin serial flash memory chips, often from Winbond. These are relatively easy to dump using the inexpensive CH341A programmer. You'll also need a test clip to go along with it, or specialty test hooks for SMD components. Larger NAND flash chips are also common but are much more complicated to dump.

| Description | Photo |
| --- | --- |
| CH341A programmer with test clip | <img src="images/CH341A.jpg" alt="Photo of the programmer and test clip" width="200"> |
| Typical flash chip | <img src="images/winbond.jpg" alt="Photo of the flash chip" width="200"> |

## New Devices

Generally, code change is going to be required to support a new device, but if the device happens to use the same data formats as one of the already supported devices, then you can pass that device name and override the data addresses using the various command line options.

```
>python extract_roms.py


usage: extract_roms.py [--help] [-f FILENAME] [-t TITLES] [-b BANKS] [-z SIZE] [-s SEPARATOR] [-e END]
                       [-d {jl3000,mini_arcade,retro_game_box,retrogame,qss}] [-c COUNT] [-o OUTDIR] [-g]

Extracts roms from a multicart dump.

options:
  --help
  -f FILENAME, --filename FILENAME
                        Input filename.
  -t TITLES, --titles TITLES
                        Address of title information, e.g. 0xA03F.
  -b BANKS, --banks BANKS
                        Address of bank information, e.g. 0x6A000.
  -z SIZE, --size SIZE  Size of each bank data entry, e.g. 9.
  -s SEPARATOR, --separator SEPARATOR
                        Character used to separate titles, e.g. 255.
  -e END, --end END     Character used to end titles, e.g. 0.
  -d {jl3000,mini_arcade,retro_game_box,retrogame,qss}, --device {jl3000,mini_arcade,retro_game_box,retrogame,qss}
                        Device name (automatically sets values for the required arguments).
  -c COUNT, --count COUNT
                        Max number of roms to parse, e.g. 10.
  -o OUTDIR, --outdir OUTDIR
                        Output directory.
  -g, --debug           Enable debug output.

Pass the required arguments to begin parsing roms.
```

## License
Licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en).
