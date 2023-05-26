import os as _os
import io as _io
import sys as _sys
import _thread as _thread
import time as _time
import dotenv as _dotenv
import tempfile as _tempfile
import whisper as _whisper
import subprocess
from pydub import AudioSegment
from pydub.playback import play

from text_to_speech import synthesize_speech

_dotenv.load_dotenv()

OUTPUTS = "outputs/"
SOURCES = "sources/"
AUDIO_SOURCES = SOURCES + "audio/"
OPENAI_API_KEY = _os.environ["OPENAI_API_KEY"]

_os.makedirs(_os.path.dirname(OUTPUTS), exist_ok=True)
_os.makedirs(_os.path.dirname(SOURCES), exist_ok=True)
_os.makedirs(_os.path.dirname(AUDIO_SOURCES), exist_ok=True)


def _convert_mp4_to_mp3(mp4_path, mp3_path):
    # Blocking run.
    subprocess.run(
        ["ffmpeg", "-i", mp4_path, "-vn", "-ab", "64k", "-ar", "16000", "-y", mp3_path]
    )
    # subprocess.run(['ffmpeg', '-i', mp4_path, '-vn', '-ab', '320k', '-ar', '44100', '-y', audio_path])


def convert_mp4_to_mp3(filename):
    mp4_path = SOURCES + filename
    mp3_path = AUDIO_SOURCES + filename.split(".")[0] + ".mp3"

    _convert_mp4_to_mp3(mp4_path, mp3_path)

    return mp3_path


def synthesize_and_play(text):
    audio_content = synthesize_speech(text)

    with _tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
        temp_file.write(audio_content)
        play_audio_file(temp_file.name)


def capture_stdout(output):
    output_text_path = OUTPUTS + "subs-en.txt"
    with open(output_text_path, "w"):
        pass

    while True:
        captured_output = output.getvalue()
        # Clear the output
        output.truncate(0)
        output.seek(0)

        with open(output_text_path, "a") as file:
            plaintext = "".join(
                [line.split("] ", 1)[1] for line in captured_output.splitlines()]
            )
            file.write(plaintext)

        if text := plaintext.strip():
            # Blocking.
            synthesize_and_play(text)

        _time.sleep(2)


def transcribe_local(file_path, model="small"):
    print("\nTranscribing file: " + file_path + "\n")

    output = _io.StringIO()
    original_stdout = _sys.stdout

    # Redirect standard output to the TextIOWrapper object
    _sys.stdout = output

    _thread.start_new_thread(capture_stdout, (output,))

    result = _whisper.load_model(model, download_root="models").transcribe(
        file_path,
        fp16=False,
        verbose=True,
        language="en",
    )

    # Restore the original standard output when done.
    _sys.stdout = original_stdout

    return result["text"]


def play_audio_file(mp3_file):
    audio = AudioSegment.from_file(mp3_file)
    play(audio)


def run_local(filename):
    audio_path = convert_mp4_to_mp3(filename)
    text = transcribe_local(audio_path, model="small")

    output_text_path = OUTPUTS + filename.split(".")[0] + "-en.txt"
    with open(output_text_path, "w") as out:
        out.write(text)
        print(f"Text content written to file {output_text_path}")

    chunk_size = 4000
    audio_content = b""

    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        audio_content += synthesize_speech(chunk)

    output_audio_path = OUTPUTS + filename.split(".")[0] + "-en.mp3"
    with open(output_audio_path, "wb") as out:
        # Write the response to the output file.
        out.write(audio_content)
        print(f"Audio content written to file {output_audio_path}")


if __name__ == "__main__":
    run_local(filename="recording-shorter.mp4")

    print("Done!")

    while True:
        pass
