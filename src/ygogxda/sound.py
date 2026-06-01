import struct
import wave
import io
import math
from pathlib import Path

try:
    from midiutil import MIDIFile
except ImportError:
    MIDIFile = None

# Estimated parameter counts per command high-nibble for the tracker format.
# Based on Ghidra decompilation of FUN_080ef2fc.
# Key: high nibble of command byte (cmd >> 4), value: (num_params, description)
CMD_PARAMS = {
    0x1: (1, "note-on with pitch"),
    0x2: (1, "set frequency"),
    0x3: (1, "volume fine adjust"),
    0x4: (1, "volume set"),
    0x5: (1, "instrument/param"),
    0x6: (0, "sub-track trigger"),
    0x7: (2, "frequency/bend"),
    0x8: (1, "note param"),
    0x9: (1, "instrument / note param"),
    0xA: (1, "note/pan"),
    0xB: (2, "pitch bend"),
    0xC: (1, "note-on specific"),
    0xD: (1, "note + param"),
    0xE: (1, "extended command"),
}

# Special commands 0xF0-0xFF parameter counts
SPECIAL_CMD_PARAMS = {
    0xF0: (0, "portamento/effect"),
    0xF1: (0, "reserved"),
    0xF2: (2, "effect control (2 params: value, depth)"),
    0xF3: (2, "pitch slide (2 params: semitones, speed)"),
    0xF4: (2, "envelope target (2 params: target, speed)"),
    0xF5: (0, "noise mode"),
    0xF6: (1, "set param"),
    0xF7: (2, "channel config (2 params)"),
    0xF8: (1, "volume/pan set"),
    0xF9: (0, "stop"),
    0xFA: (0, "jump short"),
    0xFB: (4, "jump absolute (4-byte addr)"),
    0xFC: (1, "repeat/conditional"),
    0xFD: (0, "stop track"),
    0xFE: (0, "end of track"),
    0xFF: (0, "loop/return"),
}


def _cmd_param_count(cmd):
    if 0x10 <= cmd <= 0xEF:
        nibble = (cmd >> 4) & 0xF
        return CMD_PARAMS.get(nibble, (0, ""))[0]
    if 0xF0 <= cmd <= 0xFF:
        return SPECIAL_CMD_PARAMS.get(cmd, (0, ""))[0]
    return 0


def _note_from_param(param):
    """Heuristic: map a tracker parameter byte to a MIDI note number (0-127).

    The GBA sound engine packs note info: top 3 bits = octave, bottom 5 bits = semitone.
    Octave range 0-7 mapped to MIDI octaves 2-9.
    """
    octave = (param >> 5) & 7
    semitone = param & 0x1F
    return octave * 12 + semitone + 12  # MIDI note 12 = C0


def song_to_midi(song_data, ticks_per_quart=480, bpm=120, track_name="Song"):
    """Convert parsed song events to a MIDI file using midiutil.

    The low nibble of 0x10-0x1F selects a voice (0-15). Each voice maps
    to a MIDI channel for polyphonic playback.

    Returns raw MIDI bytes, or None if midiutil is not installed.
    """
    if MIDIFile is None:
        return None

    # Skip the 12-byte block header (type_id + size_field + marker)
    song_data = song_data[12:]

    events = parse_song_events(song_data)

    mf = MIDIFile(1, ticks_per_quarternote=ticks_per_quart)
    track = 0
    time = 0
    mf.addTrackName(track, time, track_name)
    mf.addTempo(track, time, bpm)

    # Per-voice state: { voice_num: {pitch, start, vol, chan, bank} }
    voices = {}
    global_vol = 100

    def _close(v, at_time):
        info = voices.pop(v, None)
        if info is None or info["pitch"] is None:
            return
        dur = at_time - info["start"]
        if dur > 0:
            mf.addNote(
                track, info["chan"], info["pitch"], info["start"], dur, info["vol"]
            )

    for delay, cmds in events:
        time += delay
        for cmd, params in cmds:
            if 0x10 <= cmd <= 0x1F and params:
                voice = cmd & 0x0F
                _close(voice, time)
                pitch = _note_from_param(params[0])
                voices[voice] = {
                    "pitch": pitch,
                    "start": time,
                    "vol": global_vol,
                    "chan": voice % 16,
                    "bank": 0,
                }

            elif 0x30 <= cmd <= 0x3F and params:
                global_vol = min(127, max(0, params[0] & 0x7F))

            elif 0x40 <= cmd <= 0x4F and params:
                global_vol = min(127, params[0] & 0x7F)

            elif 0x90 <= cmd <= 0x9F and params:
                instr = (cmd & 0x0F) | ((params[0] & 0x0F) << 4)
                bank = instr // 128
                prog = instr % 128
                for info in voices.values():
                    if bank != info.get("bank", 0):
                        mf.addControllerEvent(track, info["chan"], time, 0, bank)
                        info["bank"] = bank
                    mf.addProgramChange(track, info["chan"], time, prog)

            elif 0xB0 <= cmd <= 0xBF and len(params) >= 2:
                pb = ((params[0] & 0x7F) | ((params[1] & 0x7F) << 7)) - 8192
                for info in voices.values():
                    mf.addPitchWheelEvent(track, info["chan"], time, pb)

            elif cmd == 0xF8 and params:
                global_vol = min(127, params[0] & 0x7F)

            elif cmd in (0xFD, 0xFE, 0xF9, 0xFF):
                for v in list(voices.keys()):
                    _close(v, time)

    # Close any hanging voices
    for v in list(voices.keys()):
        _close(v, time)

    out = io.BytesIO()
    mf.writeFile(out)
    return out.getvalue()


def parse_song_events(data, max_events=0):
    """Parse a song block's data stream into events.

    Each event: (delay, [(cmd, [params...]), ...])
    """
    i = 0
    events = []
    while i < len(data):
        if max_events and len(events) >= max_events:
            break

        # --- read delay ---
        b = data[i]
        i += 1
        if b >= 0xF0:
            if i >= len(data):
                break
            delay = ((b & 0x0F) << 8) | data[i]
            i += 1
        else:
            delay = b

        # --- read commands for this row ---
        cmds = []
        while i < len(data):
            b = data[i]
            if 0x00 <= b <= 0x0F:
                # next event's delay — push back
                break

            cmd = b
            i += 1
            n = _cmd_param_count(cmd)
            raw_params = []
            for _ in range(n):
                if i >= len(data):
                    break
                raw_params.append(data[i])
                i += 1
            cmds.append((cmd, raw_params))

        events.append((delay, cmds))

    return events


def song_events_to_text(events, max_cmds=6):
    lines = []
    for idx, (delay, cmds) in enumerate(events):
        parts = []
        for cmd, params in cmds[:max_cmds]:
            if cmd >= 0xF0:
                label = f"0x{cmd:02X}"
            elif cmd >= 0x80:
                label = f"0x{cmd:02X}"
            else:
                label = f"0x{cmd:02X}"
            if params:
                label += "(" + ",".join(f"0x{p:02X}" for p in params) + ")"
            parts.append(label)
        if len(cmds) > max_cmds:
            parts.append("...")
        lines.append(f"[{idx:3d}] delay={delay:3d}  {' '.join(parts)}")
    return "\n".join(lines)


_SOUND_ARCHIVE_VADDR = 0x081EE230

BLOCK_TYPES = {
    0x1000: ("sample_bank", "PCM sample data bank"),
    0x0C2D: ("song", "Song sequence (tracker format)"),
    0x0B6A: ("sfx", "Sound effect sequence"),
    0x0AA7: ("sfx_instr", "SFX/instrument definition"),
    0x0F38: ("sequence", "Sequence data"),
    0x085F: ("sequence_alt", "Alternate sequence data"),
    0x079C: ("special", "Special sequence"),
    0x09E4: ("small_seq", "Small sequence data"),
}


class SoundArchive:
    """Parser for the sound/music data archive at 0x081EE230."""

    def __init__(self, rom_path):
        self.rom_path = str(rom_path)
        self._load()

    def _load(self):
        reg = __import__("ygogxda.registry", fromlist=["ASSETS"]).ASSETS.get_region(
            "MATRIX1"
        )
        with open(self.rom_path, "rb") as f:
            f.seek(reg.start - 0x08000000)
            self.raw = f.read(reg.size)
        self._parse_ptrs()

    def _parse_ptrs(self):
        self.ptrs = []
        for off in range(0, len(self.raw), 4):
            val = struct.unpack_from("<I", self.raw, off)[0]
            if 0x08000000 <= val <= 0x0A000000:
                self.ptrs.append(val)
            elif len(self.ptrs) > 10:
                break
            else:
                self.ptrs.clear()

    @property
    def num_entries(self):
        return len(self.ptrs)

    def _entry_offset(self, idx):
        return self.ptrs[idx] - _SOUND_ARCHIVE_VADDR

    def _entry_end_offset(self, idx):
        if idx + 1 < len(self.ptrs):
            return self.ptrs[idx + 1] - _SOUND_ARCHIVE_VADDR
        return len(self.raw)

    def get_entry_data(self, idx):
        start = self._entry_offset(idx)
        end = self._entry_end_offset(idx)
        return self.raw[start:end]

    def entry_size(self, idx):
        return self._entry_end_offset(idx) - self._entry_offset(idx)

    def entry_header(self, idx):
        data = self.get_entry_data(idx)
        if len(data) < 12:
            return None
        return {
            "type_id": struct.unpack_from("<I", data, 0)[0],
            "size_field": struct.unpack_from("<I", data, 4)[0],
            "marker": struct.unpack_from("<I", data, 8)[0],
        }

    def entry_type_name(self, idx):
        hdr = self.entry_header(idx)
        if hdr is None:
            return "unknown"
        tinfo = BLOCK_TYPES.get(hdr["type_id"])
        return tinfo[0] if tinfo else "unknown"

    def info(self):
        lines = []
        lines.append(f"Sound archive: {self.num_entries} entries")
        lines.append(
            f"{'Idx':<5} {'Type':<15} {'Size':>8} {'Header':<12} {'VAddr':<12}"
        )
        lines.append("-" * 55)
        for i in range(self.num_entries):
            hdr = self.entry_header(i)
            tid = hdr["type_id"] if hdr else 0
            tname = self.entry_type_name(i)
            size = self.entry_size(i)
            vaddr = self.ptrs[i]
            lines.append(f"{i:<5} {tname:<15} {size:>8}B 0x{tid:08X} 0x{vaddr:08X}")
        lines.append("-" * 55)
        total = sum(self.entry_size(i) for i in range(self.num_entries))
        lines.append(f"{'TOTAL':<5} {'':15} {total:>8}B")
        return "\n".join(lines)

    def extract_blocks(self, output_dir):
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for i in range(self.num_entries):
            data = self.get_entry_data(i)
            tname = self.entry_type_name(i)
            fname = out / f"block_{i:03d}_{tname}.bin"
            fname.write_bytes(data)
        return str(out)

    def export_sample_bank(self, idx, output_path, sample_rate=16000):
        data = self.get_entry_data(idx)
        hdr = self.entry_header(idx)
        if hdr is None or hdr["type_id"] != 0x1000:
            raise ValueError(
                f"Block {idx} is not a sample bank (type=0x{hdr['type_id']:08X})"
            )
        samples = data[12:]
        outpath = Path(output_path)
        with wave.open(str(outpath), "w") as w:
            w.setnchannels(1)
            w.setsampwidth(1)
            w.setframerate(sample_rate)
            unsigned = bytearray((b + 128) & 0xFF for b in samples)
            w.writeframes(bytes(unsigned))
        return str(outpath)

    def export_all_samples(self, output_dir, sample_rate=16000):
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        exported = []
        for i in range(self.num_entries):
            hdr = self.entry_header(i)
            if hdr and hdr["type_id"] == 0x1000:
                wav_path = out / f"sample_bank_{i:03d}.wav"
                self.export_sample_bank(i, str(wav_path), sample_rate)
                exported.append(str(wav_path))
        return exported

    def export_instrument(self, idx, output_path, sample_rate=16000):
        """Export an sfx_instr block as WAV.

        Instrument blocks (type 0x0AA7) store raw 8-bit PCM sample data
        starting at offset 12. The header fields:
          +0x00: pitch_factor (u32, always 0x0AA7)
          +0x04: sample_length (u32, bit31 = extended format)
          +0x08: loop_flag (u32, <0 = no loop)
        """
        data = self.get_entry_data(idx)
        hdr = self.entry_header(idx)
        if hdr is None or hdr["type_id"] != 0x0AA7:
            raise ValueError(
                f"Block {idx} is not an sfx_instr (type=0x{hdr['type_id']:08X})"
            )
        sample_len = hdr["size_field"]
        samples = data[12 : 12 + sample_len]
        outpath = Path(output_path)
        with wave.open(str(outpath), "w") as w:
            w.setnchannels(1)
            w.setsampwidth(1)
            w.setframerate(sample_rate)
            unsigned = bytearray((b + 128) & 0xFF for b in samples)
            w.writeframes(bytes(unsigned))
        return str(outpath)

    def export_all_instruments(self, output_dir, sample_rate=16000):
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        exported = []
        for i in range(self.num_entries):
            hdr = self.entry_header(i)
            if hdr and hdr["type_id"] == 0x0AA7:
                wav_path = out / f"instrument_{i:03d}.wav"
                self.export_instrument(i, str(wav_path), sample_rate)
                exported.append(str(wav_path))
        return exported

    def _collect_block_samples(self):
        """Collect ALL blocks in MATRIX1 order as potential samples.

        The GBA engine treats every block as a playable instrument:
          - data at +0x0C is PCM (8-bit unsigned, skipping 12-byte block header)
          - block type_id is used as pitch_factor by sound_note_init
          - marker field contains loop flags (0xFFFFFFFF = no loop)
        Blocks 0-24 are song data (tracker commands, not PCM), but they may
        still be referenced as instruments — they'll just sound like noise.
        """
        samples = []
        for i in range(self.num_entries):
            hdr = self.entry_header(i)
            data = self.get_entry_data(i)
            pcm = data[12:]
            tid = hdr["type_id"] if hdr else 0
            samples.append(
                {
                    "name": f"block{i:03d}_t{tid:04x}",
                    "data": pcm,
                    "type_id": tid,
                    "marker": hdr["marker"] if hdr else 0,
                    "source": f"block[{i}] type=0x{tid:08X}" if hdr else f"block[{i}]",
                }
            )
        return samples

    def build_sfz(self, output_dir, sample_rate=16000, root_key=60):
        """Export all blocks as WAVs and generate an SFZ instrument map.

        Blocks are indexed in MATRIX1 order matching the game's instrument numbering.
        Block N is available as bank=N/128, program=N%128.
        """
        output_dir = Path(output_dir)
        samples_dir = output_dir / "samples"
        samples_dir.mkdir(parents=True, exist_ok=True)

        all_samples = self._collect_block_samples()
        if not all_samples:
            raise ValueError("No samples found")

        num_samples = len(all_samples)

        wav_names = []
        for s in all_samples:
            wav_name = s["name"] + ".wav"
            wav_path = samples_dir / wav_name
            raw8 = s["data"]
            with wave.open(str(wav_path), "w") as w:
                w.setnchannels(1)
                w.setsampwidth(1)
                w.setframerate(sample_rate)
                unsigned = bytearray((b + 128) & 0xFF for b in raw8)
                w.writeframes(bytes(unsigned))
            wav_names.append(wav_name)

        lines = [
            f"// Yu-Gi-Oh! GX Duel Academy - SoundFont (SFZ)",
            f"// Generated from {self.rom_path}",
            f"// {num_samples} samples, {sample_rate} Hz, root key C4 ({root_key})",
            f"// Block N = bank=N/128, program=N%128",
            "",
            "<global>",
            f"  ampeg_attack=0.002 ampeg_decay=0.01 ampeg_sustain=100 ampeg_release=0.05",
            "",
        ]
        for idx, s in enumerate(all_samples):
            bank = idx // 128
            prog = idx % 128
            marker = s.get("marker", 0xFFFFFFFF)
            lines.append(f"<region>")
            lines.append(f"  bank={bank}")
            lines.append(f"  program={prog}")
            lines.append(f"  pitch_keycenter={root_key}")
            lines.append(f"  sample=samples/{wav_names[idx]}")
            if marker != 0xFFFFFFFF and marker != 0:
                lines.append(f"  loop_mode=loop_continuous")
                lines.append(f"  loop_start={marker}")
            lines.append("")

        sfz_path = output_dir / "ygogxda.sfz"
        sfz_path.write_text("\n".join(lines))

        readme = f"""SFZ SoundFont for Yu-Gi-Oh! GX Duel Academy
========================================
{num_samples} samples at {sample_rate} Hz
Block N = instrument N in the game engine.
In MIDI: bank=N/128, program=N%128.
Requires bank select support in your player.
"""
        readme_path = output_dir / "README.txt"
        readme_path.write_text(readme)

        return str(output_dir)

    def build_sf2(self, output_path, sample_rate=16000):
        """Build a SoundFont (.sf2) file compatible with FluidSynth.

        Blocks are indexed in MATRIX1 order matching the game's instrument numbering.
        Block N is mapped to MIDI bank=N/128, program=N%128.

        The block type_id is used as pitch_factor by the game engine (sound_note_init).
        For SF2, we encode it in the sample name and use a default root_key=60.
        """
        all_samples = self._collect_block_samples()
        if not all_samples:
            raise ValueError("No samples found")

        total = len(all_samples)
        root_key = 60

        # Convert 8-bit unsigned PCM to 16-bit signed
        pcm16 = bytearray()
        sample_starts = []
        for s in all_samples:
            sample_starts.append(len(pcm16) // 2)
            for b in s["data"]:
                pcm16.extend(struct.pack("<h", (b - 128) << 8))
            pcm16.extend(b"\x00" * 92)  # 46 zero guard samples

        def _pad4(data):
            if len(data) % 2:
                data += b"\x00"
            return data

        def _chunk(ckid, data):
            data = _pad4(data)
            return struct.pack("<4sI", ckid, len(data)) + data

        def _list(id_, subchunks):
            body = _pad4(b"".join(subchunks))
            return struct.pack("<4sI", b"LIST", len(body) + 4) + id_ + body

        ver = struct.pack("<HH", 2, 1)
        info = _list(
            b"INFO",
            [
                _chunk(b"ifil", ver),
                _chunk(b"INAM", b"Yu-Gi-Oh! GX Duel Academy SoundFont\x00"),
                _chunk(b"IENG", b"ygogxda\x00"),
                _chunk(b"ISFT", b"ygogxda sound.py\x00"),
            ],
        )

        sdta = _list(b"sdta", [_chunk(b"smpl", bytes(pcm16))])

        # --- phdr: one preset per block, using bank select for blocks >127 ---
        phdr = bytearray()
        for idx in range(total):
            name = f"Block {idx}\x00".encode("ascii")[:20].ljust(20, b"\x00")
            bank = idx // 128
            prog = idx % 128
            phdr.extend(name)
            phdr.extend(struct.pack("<HHHIII", prog, bank, idx, 0, 0, 0))
        phdr.extend(b"\x00" * 20 + struct.pack("<HHHIII", 127, 0, total, 0, 0, 0))

        # --- pbag / pgen: each preset has one zone → one instrument ---
        pbag = bytearray()
        pgen = bytearray()
        gen_idx = 0
        for idx in range(total):
            pbag.extend(struct.pack("<HH", gen_idx, 0))
            pgen.extend(struct.pack("<HH", 41, idx))
            gen_idx += 1
        pbag.extend(struct.pack("<HH", gen_idx, 0))

        # --- inst: instrument headers ---
        inst = bytearray()
        for idx in range(total):
            name = f"Block {idx}\x00".encode("ascii")[:20].ljust(20, b"\x00")
            inst.extend(name)
            inst.extend(struct.pack("<H", idx))
        inst.extend(b"\x00" * 20 + struct.pack("<H", total))

        # --- ibag / igen: each instrument zone → one sample ---
        # Per SF2 spec §8.1.2, SampleID (gen 53) must be the LAST generator in zone.
        ibag = bytearray()
        igen = bytearray()
        gen_idx = 0
        for idx, s in enumerate(all_samples):
            ibag.extend(struct.pack("<HH", gen_idx, 0))
            igen.extend(struct.pack("<HH", 43, 0x7F00))  # key range 0-127
            igen.extend(struct.pack("<HH", 58, root_key))  # overridingRootKey
            marker = s.get("marker", 0xFFFFFFFF)
            sample_modes = 1 if marker != 0xFFFFFFFF and marker != 0 else 0
            igen.extend(struct.pack("<HH", 54, sample_modes))
            igen.extend(struct.pack("<HH", 53, idx))  # sampleID — must be LAST
            gen_idx += 4
        ibag.extend(struct.pack("<HH", gen_idx, 0))

        # --- shdr: sample headers ---
        shdr = bytearray()
        for idx, s in enumerate(all_samples):
            name = s["name"].encode("ascii")[:20].ljust(20, b"\x00")
            shdr.extend(name)
            start = sample_starts[idx]
            sample_len_16bit = len(s["data"])
            end = start + sample_len_16bit
            marker = s.get("marker", 0xFFFFFFFF)
            if marker != 0xFFFFFFFF and marker != 0:
                loop_start = start + marker
                loop_end = end
            else:
                loop_start = end
                loop_end = end
            shdr.extend(
                struct.pack(
                    "<5IBbHH",
                    start,
                    end,
                    loop_start,
                    loop_end,
                    sample_rate,
                    root_key,
                    0,
                    0,
                    1,
                )
            )
        shdr.extend(b"\x00" * 46)

        empty_mod = struct.pack("<HHHHH", 0, 0, 0, 0, 0)

        pdta = _list(
            b"pdta",
            [
                _chunk(b"phdr", bytes(phdr)),
                _chunk(b"pbag", bytes(pbag)),
                _chunk(b"pmod", empty_mod),
                _chunk(b"pgen", bytes(pgen)),
                _chunk(b"inst", bytes(inst)),
                _chunk(b"ibag", bytes(ibag)),
                _chunk(b"imod", empty_mod),
                _chunk(b"igen", bytes(igen)),
                _chunk(b"shdr", bytes(shdr)),
            ],
        )

        sf2 = _chunk(b"RIFF", b"sfbk" + info + sdta + pdta)
        Path(output_path).write_bytes(sf2)
        return str(output_path)
