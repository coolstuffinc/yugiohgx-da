import struct
import wave
import io
from pathlib import Path

try:
    from midiutil import MIDIFile
except ImportError:
    MIDIFile = None


# ---------------------------------------------------------------------------
# Layer 1 bytecode parsing
# Based on Ghidra decompilation of FUN_080efa64 (16-voice song engine).
# ---------------------------------------------------------------------------

# Virtual address of the song data pointer table (46 entries × 0x24 bytes)
_SONG_TABLE_VADDR = 0x08191970


def _read_song_table(rom_path):
    """Read the song data table.

    Each entry (0x24 bytes):
      +0x00: u32 pointer to raw bytecode in ROM
      +0x04: 16 × u16 voice base offsets within the bytecode
    Returns list of dicts.
    """
    import struct

    entries = []
    with open(rom_path, "rb") as f:
        f.seek(_SONG_TABLE_VADDR - 0x08000000)
        while True:
            data = f.read(0x24)
            if len(data) < 0x24:
                break
            ptr = struct.unpack_from("<I", data, 0)[0]
            if not (0x08000000 <= ptr <= 0x0A000000):
                break
            offsets = list(struct.unpack_from("<16H", data, 4))
            entries.append({"ptr": ptr, "offsets": offsets})
    return entries


def _get_voice_bytecode(rom_path, song_idx, voice_idx):
    """Get the raw bytecode for a single voice of a song."""
    entries = _read_song_table(rom_path)
    if song_idx >= len(entries):
        return b""
    e = entries[song_idx]
    start = e["offsets"][voice_idx]
    # End is the next voice offset (or next entry's start)
    end = min(
        (o for o in e["offsets"] if o > start),
        default=None,
    )
    if end is None:
        end = start + 0x10000  # generous fallback
    with open(rom_path, "rb") as f:
        f.seek(e["ptr"] - 0x08000000)
        data = f.read(end)
    if start >= len(data):
        return b""
    return data[start:end]


def _read_bytecode(rom_path, song_idx):
    """Read the full bytecode blob for a song."""
    entries = _read_song_table(rom_path)
    e = entries[song_idx]
    # Find the maximum voice offset to know how much to read
    max_off = max(e["offsets"])
    with open(rom_path, "rb") as f:
        f.seek(e["ptr"] - 0x08000000)
        # Read from start to at least max_off + some margin
        data = f.read(max_off + 0x10000)
    return data, e["offsets"]


def _note_from_param(param):
    """Map a tracker parameter byte to a MIDI note number (0-127).

    The GBA sound engine packs note info: top 3 bits = octave, bottom 5 bits = semitone.
    Octave range 0-7 mapped to MIDI octaves 2-9.
    """
    octave = (param >> 5) & 7
    semitone = param & 0x1F
    return octave * 12 + semitone + 12


# Per-voice state for the streaming parser
class _VoiceState:
    __slots__ = (
        "offset",
        "note_pitch",
        "note_start",
        "volume",
        "instrument",
        "active",
        "pitch_bend",
        "pan",
    )

    def __init__(self):
        self.offset = 0
        self.note_pitch = None
        self.note_start = 0
        self.volume = 100
        self.instrument = 0
        self.active = True
        self.pitch_bend = 0
        self.pan = 64


def _parse_voice_events(bytecode):
    """Parse a single voice's bytecode stream into (delay_note) pairs.

    delay_note is a list of (delay_ticks, pitch_or_None, volume, instrument).
    """
    i = 0
    events = []
    tick = 0
    current_vol = 100
    current_instr = 0
    current_pitch = None
    note_on_tick = None

    def _note_off(at_tick):
        nonlocal note_on_tick
        if note_on_tick is not None and current_pitch is not None:
            dur = at_tick - note_on_tick
            if dur > 0:
                events.append(
                    (note_on_tick, current_pitch, current_vol, current_instr, dur)
                )
        note_on_tick = None

    def _note_on(at_tick, pitch):
        nonlocal note_on_tick, current_pitch
        _note_off(at_tick)
        current_pitch = pitch
        note_on_tick = at_tick

    while i < len(bytecode):
        cmd = bytecode[i]
        i += 1

        # --- Termination / loop commands ---
        if cmd == 0xFD:  # stop
            _note_off(tick)
            break
        if cmd == 0xFE:  # end of track
            _note_off(tick)
            break
        if cmd == 0xFF:  # loop / return
            _note_off(tick)
            break

        # --- Special commands 0xF0-0xFC ---
        if cmd >= 0xF0:
            consumed = 1
            if cmd == 0xF0:  # pan
                if i < len(bytecode):
                    i += 1
                    consumed = 2
            elif cmd == 0xF1:  # vibrato
                if i < len(bytecode):
                    i += 1
                    consumed = 2
            elif cmd == 0xF2:  # freq adjust (2 params)
                if i + 1 < len(bytecode):
                    i += 2
                    consumed = 3
            elif cmd == 0xF3:  # pitch slide (2 params)
                if i + 1 < len(bytecode):
                    i += 2
                    consumed = 3
            elif cmd == 0xF4:  # envelope (2 params)
                if i + 1 < len(bytecode):
                    i += 2
                    consumed = 3
            elif cmd == 0xF5:  # noise (1 param)
                if i < len(bytecode):
                    i += 1
                    consumed = 2
            elif cmd == 0xF6:  # instrument select
                if i < len(bytecode):
                    val = bytecode[i]
                    i += 1
                    consumed = 2
                    if val < 100:
                        current_instr = val
            elif cmd == 0xF7:  # channel config (1 param)
                if i < len(bytecode):
                    i += 1
                    consumed = 2
            elif cmd == 0xF8:  # volume set (1 param)
                if i < len(bytecode):
                    current_vol = min(127, bytecode[i] & 0x7F)
                    i += 1
                    consumed = 2
            elif cmd == 0xF9:  # sub-track effect (2 params)
                if i + 1 < len(bytecode):
                    i += 2
                    consumed = 3
            elif cmd == 0xFA:  # conditional (1 param)
                if i < len(bytecode):
                    i += 1
                    consumed = 2
            elif cmd == 0xFB:  # absolute jump (4 bytes)
                if i + 3 < len(bytecode):
                    i += 4
                    consumed = 5
            elif cmd == 0xFC:  # repeat (1 param)
                if i < len(bytecode):
                    i += 1
                    consumed = 2

            # Consumed bytes include the command byte, so we already advanced i.

        # --- Normal commands 0x00-0xEF ---
        elif cmd < 0xF0:
            if cmd >= 0xE0:  # E0-EF: note/freq (param = same as delay byte)
                nibble = cmd & 7
                if cmd & 8:  # extended: next byte is nibble
                    if i < len(bytecode):
                        nibble = bytecode[i]
                        i += 1
                if i < len(bytecode):
                    param = bytecode[i]  # param AND delay
                    i += 1
                    pitch = _note_from_param(param)
                    _note_on(tick, pitch)

            elif cmd >= 0xD0:  # D0-DF: note with param (param = same as delay)
                nibble = cmd & 7
                if cmd & 8:  # extended
                    if i < len(bytecode):
                        nibble = bytecode[i]
                        i += 1
                if i < len(bytecode):
                    param = bytecode[i]
                    i += 1
                    pitch = _note_from_param(param)
                    _note_on(tick, pitch)

            elif cmd >= 0xC0:  # C0-CF: note with param
                nibble = cmd & 7
                if cmd & 8:
                    if i < len(bytecode):
                        nibble = bytecode[i]
                        i += 1
                if i < len(bytecode):
                    param = bytecode[i]
                    i += 1
                    pitch = _note_from_param(param)
                    _note_on(tick, pitch)

            elif cmd >= 0xB0:  # B0-BF: frequency / pitch
                nibble = cmd & 7
                if cmd & 8:
                    if i < len(bytecode):
                        nibble = bytecode[i]
                        i += 1
                if i < len(bytecode):
                    i += 1  # param consumed

            elif cmd >= 0xA0:  # A0-AF: complex note with instrument
                nibble = cmd & 7
                if cmd & 8:  # extended nibble
                    if i < len(bytecode):
                        nibble = bytecode[i]
                        i += 1
                if i < len(bytecode):
                    val = bytecode[i]
                    i += 1
                    # Check for extended value
                    if val > 0xEF and i < len(bytecode):
                        val = ((val & 0xF) << 8) | bytecode[i]
                        i += 1
                    pitch = _note_from_param(val & 0xFF)
                    # Optional extra param for 0xA8-0xAF
                    if cmd >= 0xA8 and i < len(bytecode):
                        i += 1  # extra param (pitch offset)
                    _note_on(tick, pitch)

            elif cmd >= 0x90:  # 90-9F: no-op / rest
                pass

            else:  # 00-8F
                if cmd >= 0x80:  # 80-8F: encoded volume
                    val = (cmd & 0x3F) << 6
                    if val <= 127:
                        current_vol = val
                else:  # 00-7F: volume/pitch offset
                    pass  # relative adjustment, keep vol as-is

        # --- Read delay (1-3 bytes) ---
        if i >= len(bytecode):
            break
        delay_byte = bytecode[i]
        i += 1

        if delay_byte >= 0xE0:
            if delay_byte < 0xF0:  # E0-EF: 2-byte delay
                if i < len(bytecode):
                    delay = ((delay_byte & 0x0F) << 8) | bytecode[i]
                    i += 1
                else:
                    delay = 0
            else:  # F0-FF: 3-byte delay
                if i + 1 < len(bytecode):
                    delay = bytecode[i] | (bytecode[i + 1] << 8)
                    i += 2
                else:
                    delay = 0
        else:  # 00-DF: direct delay
            delay = delay_byte

        tick += delay

        if delay == 0:
            continue  # process next command immediately

    # Close final note
    _note_off(tick)

    return events


_GBA_FRAMES_PER_SECOND = 59.73


def song_to_midi(song_data, ticks_per_quart=480, bpm=120, track_name="Song"):
    """Convert parsed song events to a MIDI file using midiutil.

    NOTE: song_data is the raw bytecode from the MATRIX1 archive.
    For Layer 1 songs, use song_to_midi_layer1() with the real table instead.
    """
    if MIDIFile is None:
        return None
    return None


def parse_song_events(data, max_events=0):
    """Parse a song block's data stream into events.

    Kept for API compat. Returns empty list — use _parse_voice_events
    for the streaming parser, or song_to_midi_layer1 for full songs.
    """
    return []


def song_events_to_text(events, max_cmds=6):
    lines = []
    for idx, (tick, pitch, volume, instrument, duration) in enumerate(events):
        lines.append(
            f"[{idx:4d}] tick={tick:5d}  pitch={pitch:3d}  "
            f"vol={volume:3d}  instr={instrument:3d}  dur={duration:4d}"
        )
    return "\n".join(lines)


def song_to_midi_layer1(rom_path, song_idx, ticks_per_quart=480, bpm=120):
    """Convert a Layer 1 song (from table at 0x08191970) to MIDI.

    Parses all 16 voices and produces a multi-track MIDI file.
    Each active voice gets its own MIDI track.

    Returns raw MIDI bytes, or None if midiutil is not installed or no voices.
    """
    if MIDIFile is None:
        return None

    data, offsets = _read_bytecode(rom_path, song_idx)

    # Parse all active voices (non-zero offset or voice 0)
    parsed = []
    for voice_idx in range(16):
        start = offsets[voice_idx]
        end = min((o for o in offsets if o > start), default=len(data))
        bytecode = data[start:end]
        if not bytecode:
            continue
        events = _parse_voice_events(bytecode)
        if events:
            parsed.append((voice_idx, events))

    if not parsed:
        return None

    # GBA frame → MIDI beat conversion
    # 1 beat = 60/bpm seconds, 1 GBA frame = 1/59.73 seconds
    frame_to_beat = bpm / (60.0 * _GBA_FRAMES_PER_SECOND)

    mf = MIDIFile(len(parsed), ticks_per_quarternote=ticks_per_quart)

    for track_idx, (voice_idx, events) in enumerate(parsed):
        mf.addTrackName(track_idx, 0, f"Voice {voice_idx}")
        mf.addTempo(track_idx, 0, bpm)
        for tick, pitch, vol, instr, dur in events:
            start_beat = tick * frame_to_beat
            dur_beat = dur * frame_to_beat
            mf.addNote(
                track_idx, 0, pitch, start_beat, max(dur_beat, 0.001), min(127, vol)
            )

    out = io.BytesIO()
    mf.writeFile(out)
    return out.getvalue()


_SOUND_ARCHIVE_VADDR = 0x081EE230
_SOUND_ROM_TABLE_VADDR = 0x080F2D50  # 37 entries, table_sel == 0x9

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
            w.writeframes(bytes(samples))
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
            w.writeframes(bytes(samples))
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

    PCM_BLOCK_TYPES = {0x1000, 0x0AA7}

    def _collect_block_samples(self):
        """Collect PCM blocks in MATRIX1 order.

        MATRIX1 entries can point to songs (bytecode) or samples (PCM).
        Non-PCM blocks (songs, sfx sequences) are replaced with a silent
        sample so instrument numbering stays consistent with the game.
        """
        samples = []
        for i in range(self.num_entries):
            hdr = self.entry_header(i)
            tid = hdr["type_id"] if hdr else 0
            if hdr and tid in self.PCM_BLOCK_TYPES:
                data = self.get_entry_data(i)
                pcm = data[12:]
            else:
                pcm = bytes([128, 128])
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

    def _collect_rom_table_samples(self):
        samples = []
        with open(self.rom_path, "rb") as f:
            f.seek(_SOUND_ROM_TABLE_VADDR - 0x08000000)
            ptrs = []
            while True:
                buf = f.read(4)
                if len(buf) < 4:
                    break
                ptr = struct.unpack_from("<I", buf, 0)[0]
                if 0x08000000 <= ptr <= 0x08200000:
                    ptrs.append(ptr)
                else:
                    break
            for i, ptr in enumerate(ptrs):
                f.seek(ptr - 0x08000000)
                hdr = f.read(12)
                if len(hdr) < 12:
                    break
                tid = struct.unpack_from("<I", hdr, 0)[0]
                sz = struct.unpack_from("<I", hdr, 4)[0]
                mk = struct.unpack_from("<I", hdr, 8)[0]
                pcm = f.read(sz)
                samples.append(
                    {
                        "name": f"rom_instr_{i:03d}_t{tid:04x}",
                        "data": pcm,
                        "type_id": tid,
                        "marker": mk,
                        "source": f"rom_table[{i}] type=0x{tid:08X}",
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
        all_samples.extend(self._collect_rom_table_samples())

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
                w.writeframes(bytes(raw8))
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
        all_samples.extend(self._collect_rom_table_samples())

        total = len(all_samples)

        # type_id = 0x1000 is the pitch reference: blocks with this type_id
        # play at the natural sample rate. Other types scale proportionally:
        # effective_rate = sample_rate * type_id / 0x1000.
        PITCH_REFERENCE = 0x1000

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
            # Sample rate already encodes the type_id pitch ratio (Approach A),
            # so root key stays at 60 (C4) for all blocks.
            igen.extend(struct.pack("<HH", 58, 60))  # overridingRootKey
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
            block_sample_rate = (
                int(round(sample_rate * s["type_id"] / PITCH_REFERENCE))
                if s["type_id"] > 0
                else sample_rate
            )
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
                    block_sample_rate,
                    60,
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
