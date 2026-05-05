import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dsp2.audio_to_midi import (  # noqa: E402,F401
    build_audio_to_midi_graph,
    collect_midi_note_frames,
    export_audio_to_midi,
    main,
)


if __name__ == "__main__":
    main()
