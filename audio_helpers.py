from IPython.display import Audio
import pretty_midi
import urllib.request, os


# Helpers
def get_default_soundfont():
    """Download FluidR3Mono_GM.sf3 if missing and return its path."""
    path = "soundfonts/FluidR3Mono_GM.sf3"
    url = "https://github.com/musescore/MuseScore/raw/refs/heads/2.1/share/sound/FluidR3Mono_GM.sf3"

    os.makedirs(path, exist_ok=True) # Ensure existence
    if not os.path.exists(path):
        print("Downloading free SoundFont FluidR3Mono_GM.sf3 for midi interactions...")
        urllib.request.urlretrieve(url, path)
        print(f"Saved to {path}")
    else:
        print(f"Using cached SoundFont: {path}")
    return path
    
def get_github_audio(url, filename=None):
    """Download a GitHub audio file to data/audio/ if missing and return its path."""
    os.makedirs("data/audio", exist_ok=True)
    if not filename:
        filename = os.path.basename(url)
    path = os.path.join("data/audio", filename)

    if not os.path.exists(path):
        print(f"Downloading {filename}...")
        urllib.request.urlretrieve(url, path)
        print(f"Saved to {path}")
    else:
        print(f"Using cached file: {path}")
    return path

def render_midi(pm_obj: pretty_midi.PrettyMIDI, sample_rate=16000):
    return Audio(generate_audio_midi(pm_obj, sample_rate), rate=sample_rate)

def generate_audio_midi(pm_obj: pretty_midi.PrettyMIDI, sample_rate=16000, path_to_soundfont=get_default_soundfont()):
    return pm_obj.fluidsynth(synthesizer=path_to_soundfont, fs=sample_rate)