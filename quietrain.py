"""Rain bundle -> one quiet PCM rain loop. Every AudioClip points at the same small PCM FSB5; the original (Valve) audio
data is dropped. usage (UnityPy, numpy):
  quietrain.py <Rainscapes bundle> props/rain_quiet.unity3d crucial_surfacerain_light_loop 0.25
The Rainscapes bundle: https://cdn.steamusercontent.com/ugc/2404446659869065433/3DDE001D9060BAF87A50DFFF1EE21D491508A9DE/
TTS can't set an effect's volume, so the gain goes into the audio itself."""
import hashlib, io, struct, sys, wave
import numpy as np, UnityPy
src, dst, name, gain = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
env = UnityPy.load(src)
clip = next(o for o in env.objects if o.type.name == "AudioClip" and o.read().m_Name == name)
wav = wave.open(io.BytesIO(next(iter(clip.read().samples.values()))))
ch, rate, sw = wav.getnchannels(), wav.getframerate(), wav.getsampwidth()
assert sw == 2
pcm = np.frombuffer(wav.readframes(wav.getnframes()), np.int16).astype(np.float32) * gain
pcm = np.clip(pcm, -32768, 32767).astype("<i2").tobytes()
frames = wav.getnframes()
FREQ = {8000: 1, 11000: 2, 11025: 3, 16000: 4, 22050: 5, 24000: 6, 32000: 7, 44100: 8, 48000: 9}
sh = (FREQ[rate] << 1) | ((ch - 1) << 5) | (0 << 6) | (frames << 34)
fsb = b"FSB5" + struct.pack("<IIIIII", 1, 1, 8, 0, len(pcm), 2) + b"\0" * 8 + b"\0" * 16 + b"\0" * 8 + struct.pack("<Q", sh) + pcm
assert len(fsb) == 60 + 8 + len(pcm)
# replace the .resource with just this FSB and point every clip at it
resname = next(k for k in env.file.files if k.endswith(".resource"))
# new internal names: Unity won't load a bundle whose files (CAB-...) or name match one already loaded, and the original
# Rainscapes bundle is loaded too (thunder)
old_cab = resname[:-len(".resource")]
new_cab = "CAB-" + hashlib.md5(b"giants-of-holst quiet rain").hexdigest()
for o in env.objects:
    if o.type.name == "AssetBundle":
        t = o.read_typetree()
        t["m_Name"] = t["m_AssetBundleName"] = "holstquietrain"
        o.save_typetree(t)
    if o.type.name == "AudioClip":
        t = o.read_typetree()
        t["m_Resource"]["m_Source"] = t["m_Resource"]["m_Source"].replace(old_cab, new_cab)
        t["m_Resource"]["m_Offset"], t["m_Resource"]["m_Size"] = 0, len(fsb)
        t["m_CompressionFormat"], t["m_Channels"], t["m_Frequency"], t["m_BitsPerSample"] = 0, ch, rate, 16
        t["m_Length"] = frames / rate
        o.save_typetree(t)
from UnityPy.streams import EndianBinaryReader
old = env.file.files[resname]
new = EndianBinaryReader(fsb)
for k in ("flags", "name"):
    if hasattr(old, k): setattr(new, k, getattr(old, k))
env.file.files[resname] = new
for k in list(env.file.files):   # rename the bundle's files to the new CAB
    f = env.file.files.pop(k)
    k2 = k.replace(old_cab, new_cab)
    if hasattr(f, "name"): f.name = k2
    env.file.files[k2] = f
open(dst, "wb").write(env.file.save())
# check: reload and decode the clip back
e2 = UnityPy.load(dst)
c2 = next(o for o in e2.objects if o.type.name == "AudioClip" and o.read().m_Name == name).read()
w2 = wave.open(io.BytesIO(next(iter(c2.samples.values()))))
a = np.frombuffer(w2.readframes(w2.getnframes()), np.int16).astype(float)
print("ok", list(e2.file.files), w2.getnchannels(), w2.getframerate(), w2.getnframes(), "rms dBFS", round(20 * np.log10(np.sqrt((a ** 2).mean()) / 32768), 1),
      "size", len(open(dst, "rb").read()))
