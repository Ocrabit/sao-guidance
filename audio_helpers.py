from IPython.display import Audio, HTML
# import pretty_midi  # I think this has some errors on windows
import urllib.request, os
import torch
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import gradio as gr
import torchaudio


LINE_WIDTH = 2

# fix torchaudio load
_TORCHAUDIO_LOAD = torchaudio.load
def _torchload_with_fallback(uri, *args, **kwargs):
    try:
        return _TORCHAUDIO_LOAD(uri, *args, **kwargs)
    except Exception:
        # fallback to soundfile
        import soundfile as sf
        audio, sr = sf.read(uri, always_2d=True)
        audio = torch.tensor(audio.T)  # channels_first
        if kwargs.get("normalize", True):
            audio = audio.float() / 32768.0
        return audio, sr

torchaudio.load = _torchload_with_fallback

# Helpers
def get_default_soundfont():
    """Download FluidR3Mono_GM.sf3 if missing and return its path."""
    path = "soundfonts/FluidR3Mono_GM.sf3"
    url = "https://github.com/musescore/MuseScore/raw/refs/heads/2.1/share/sound/FluidR3Mono_GM.sf3"

    os.makedirs(os.path.dirname(path), exist_ok=True) # Ensure existence
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

# def render_midi(pm_obj: pretty_midi.PrettyMIDI, sample_rate=16000):
#     return Audio(generate_audio_midi(pm_obj, sample_rate), rate=sample_rate)

# def generate_audio_midi(pm_obj: pretty_midi.PrettyMIDI, sample_rate=16000, path_to_soundfont=get_default_soundfont()):
#     return pm_obj.fluidsynth(synthesizer=path_to_soundfont, fs=sample_rate)


def plot_pitch(pitch, sample_rate, hop_length=None):
    if hop_length is None:
        hop_length = int(sample_rate / 200.)

    if torch.is_tensor(pitch):
        pitch = pitch[0].cpu().detach().numpy()

    times = np.arange(len(pitch)) * hop_length / sample_rate

    plt.figure(figsize=(10, 4))
    plt.plot(times, pitch, linewidth=LINE_WIDTH)
    plt.xlabel("Time (s)")
    plt.ylabel("Pitch (Hz)")
    plt.title("Pitch Contour")
    plt.show()


def plot_pitch_comparison(pitch, target_pitch, sample_rate, hop_length=None, overlay=False):
    if hop_length is None:
        hop_length = int(sample_rate / 200.)

    if torch.is_tensor(pitch):
        pitch = pitch[0].cpu().detach().numpy()
    if torch.is_tensor(target_pitch):
        target_pitch = target_pitch[0].cpu().detach().numpy()

    times1 = np.arange(len(pitch)) * hop_length / sample_rate
    times2 = np.arange(len(target_pitch)) * hop_length / sample_rate

    if overlay:
        plt.figure(figsize=(10, 5))
        plt.plot(times1, pitch, color='magenta', label='Pitch', alpha=0.7, linewidth=LINE_WIDTH)
        plt.plot(times2, target_pitch, color='orange', label='Target Pitch', alpha=0.7, linewidth=LINE_WIDTH)
        plt.xlabel("Time (s)")
        plt.ylabel("Pitch (Hz)")
        plt.title("Pitch Comparison")
        plt.legend()
        plt.grid(True, alpha=0.3)
    else:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4), sharey=True)

        ax1.plot(times1, pitch, color='magenta', linewidth=LINE_WIDTH)
        ax1.set_title("Audio 1")
        ax1.set_xlabel("Time (s)")
        ax1.set_ylabel("Pitch (Hz)")

        ax2.plot(times2, target_pitch, color='orange', linewidth=LINE_WIDTH)
        ax2.set_title("Audio 2")
        ax2.set_xlabel("Time (s)")

        plt.tight_layout()

    plt.show()
        
# Curtesy of Claude and I
def animate_pitch_arrays(pitch_array, sample_rate, target_pitch=None, hop_length=None, interval=200):
    assert len({p.shape[-1] for p in pitch_array}) == 1, f"Unequal lengths: {[p.shape[-1] for p in pitch_array]}"

    if hop_length is None:
        hop_length = int(sample_rate / 200.)

    # Convert to numpy if needed
    pitch_array = [p.detach().cpu().numpy() if torch.is_tensor(p) else p for p in pitch_array]

    if target_pitch is not None and torch.is_tensor(target_pitch):
        target_pitch = target_pitch.cpu().detach().numpy()

    # Assume shape is (num_examples, pitch_length)
    n_frames = len(pitch_array)
    pitch_len = pitch_array[0].shape[-1]
    times = np.arange(pitch_len) * hop_length / sample_rate

    fig, ax = plt.subplots(figsize=(10, 5))

    line1, = ax.plot([], [], color='magenta', label='Pitch', linewidth=LINE_WIDTH, alpha=0.7)

    if target_pitch is not None:
        line2, = ax.plot([], [], color='orange', label='Target', linewidth=2, alpha=0.7)
        y_max = (np.nanmax(np.r_[np.asarray(pitch_array).ravel(), np.asarray(target_pitch).ravel()]) if target_pitch is not None else np.nanmax(np.asarray(pitch_array))) * 1.1
    else:
        line2 = None
        y_max = pitch_array.max() * 1.1

    ax.set_xlim(0, times[-1])
    ax.set_ylim(0, y_max)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Pitch (Hz)")
    ax.set_title("Pitch Animation")
    ax.legend()
    ax.grid(True, alpha=0.3)

    def update(frame):
        line1.set_data(times, pitch_array[frame])
        if target_pitch is not None:
            line2.set_data(times, target_pitch)
            ax.set_title(f"Pitch Animation - Frame {frame+1}/{n_frames}")
            return line1, line2
        else:
            ax.set_title(f"Pitch Animation - Frame {frame+1}/{n_frames}")
            return line1,

    ani = animation.FuncAnimation(fig, update, frames=n_frames, interval=interval, blit=True)
    html = ani.to_jshtml()
    plt.close(fig)
    return HTML(html)


# Some gradio demos curtesy of claude, sorry I don't feel like writing pretty code for this, well I wrote the base it used above
def plot_frame(frame_idx, pitch_array, target_pitch, sample_rate, y_limits, audio_array=None, target_audio=None):
    hop_length = int(sample_rate / 200.)

    # Get current frame and ensure it's 1D
    current_pitch = pitch_array[frame_idx]
    if current_pitch.ndim > 1:
        current_pitch = current_pitch.squeeze()

    times = np.arange(len(current_pitch)) * hop_length / sample_rate

    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot current frame pitch
    ax.plot(times, current_pitch, color='magenta', label='Pitch', linewidth=2, alpha=0.7)

    # Plot target if exists
    if target_pitch is not None:
        target_plot = target_pitch.squeeze() if target_pitch.ndim > 1 else target_pitch
        ax.plot(times, target_plot, color='orange', label='Target', linewidth=2, alpha=0.7)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Pitch (Hz)")
    ax.set_title(f"Pitch Analysis - Frame {frame_idx + 1}/{len(pitch_array)}")
    ax.set_ylim(y_limits)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Build outputs based on what's available
    outputs = [fig]

    if audio_array is not None:
        audio_data = audio_array[frame_idx]

        if audio_data.ndim == 2:
            if audio_data.shape[0] == 2:
                audio_data = audio_data.T

        outputs.append((int(sample_rate), audio_data))

    if target_audio is not None:
        target_data = target_audio

        if target_audio.ndim == 2:
            if target_audio.shape[0] == 1:
                target_data = target_audio.T
        # Convert to int16 to avoid warnings
        target_data = (target_data * 32767).astype(np.int16)
        outputs.append((int(sample_rate), target_data))

    return tuple(outputs)


def create_gradio_interface(pitch_array, target_pitch, sample_rate, audio_array=None, target_audio=None):
    assert len({p.shape[-1] for p in pitch_array}) == 1, f"Unequal lengths: {[p.shape[-1] for p in pitch_array]}"
    n_frames = len(pitch_array)

    # Convert tensors to numpy if needed
    if pitch_array is not None and torch.is_tensor(pitch_array[0]):
        pitch_array = [p.detach().cpu().numpy() for p in pitch_array]
    if target_pitch is not None and torch.is_tensor(target_pitch):
        target_pitch = target_pitch.detach().cpu().numpy()
    if audio_array is not None and torch.is_tensor(audio_array[0]):
        audio_array = [a.detach().cpu().numpy() for a in audio_array]
    if target_audio is not None and torch.is_tensor(target_audio):
        target_audio = target_audio.detach().cpu().numpy()

    # Calculate consistent y-limits across all frames
    all_pitches = np.concatenate([p.flatten() for p in pitch_array])
    if target_pitch is not None:
        all_pitches = np.concatenate([all_pitches, target_pitch.flatten()])

    # Filter out zeros/NaNs for better scaling
    valid_pitches = all_pitches[all_pitches > 0]
    if len(valid_pitches) > 0:
        y_min = np.min(valid_pitches) * 0.9  # 10% padding below
        y_max = np.max(valid_pitches) * 1.1  # 10% padding above
    else:
        y_min, y_max = 0, 1000  # Default range

    y_limits = (y_min, y_max)

    # Create array to hold optional items we can unpack later
    present_items = []

    with gr.Blocks() as demo:
        gr.Markdown("# Pitch Analysis Viewer")

        with gr.Row():
            with gr.Column(scale=10):
                frame_slider = gr.Slider(
                    minimum=0,
                    maximum=n_frames - 1,
                    value=0,
                    step=1,
                    label="Frame",
                    info=f"Select frame (0-{n_frames - 1})"
                )
            with gr.Column(scale=1, min_width=50):
                play_btn = gr.Button("▶", variant="primary", scale=1, min_width=50)
                stop_btn = gr.Button("⏸", variant="secondary", scale=1, min_width=50, visible=False)

        with gr.Row():
            plot_output = gr.Plot(label="Pitch Contour")

        if audio_array is not None:
            with gr.Row():
                audio_output = gr.Audio(label="Frame Audio", autoplay=False)
            present_items.append(audio_output)
        else:
            audio_output = None

        if target_audio is not None:
            with gr.Row():
                target_audio_output = gr.Audio(label="Target Audio", autoplay=False)
            present_items.append(target_audio_output)
        else:
            target_audio_output = None

        # Timer for animation
        timer = gr.Timer(0.2, active=False)  # 200ms between frames

        def advance_frame(current_frame):
            next_frame = current_frame + 1
            if next_frame >= n_frames:
                next_frame = 0  # Loop to beginning

            outputs = plot_frame(next_frame, pitch_array, target_pitch, sample_rate, y_limits, audio_array, target_audio)
            return *outputs, next_frame

        # Play button starts timer
        def start_playing():
            return gr.Timer(active=True), gr.Button(visible=False), gr.Button(visible=True)

        # Stop button stops timer
        def stop_playing():
            return gr.Timer(active=False), gr.Button(visible=True), gr.Button(visible=False)

        play_btn.click(
            start_playing,
            outputs=[timer, play_btn, stop_btn]
        )

        stop_btn.click(
            stop_playing,
            outputs=[timer, play_btn, stop_btn]
        )

        # Timer advances frame
        timer.tick(
            advance_frame,
            inputs=frame_slider,
            outputs=[plot_output, *present_items, frame_slider]
        )

        # Manual slider change
        frame_slider.change(
            fn=lambda idx: plot_frame(idx, pitch_array, target_pitch, sample_rate, y_limits, audio_array, target_audio),
            inputs=frame_slider,
            outputs=[plot_output, *present_items]
        )

        # Initial plot
        demo.load(
            fn=lambda: plot_frame(0, pitch_array, target_pitch, sample_rate, y_limits, audio_array, target_audio),
            outputs=[plot_output, *present_items]
        )

    return demo