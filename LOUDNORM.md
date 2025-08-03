# Audio Loudnorm Migration

This document describes the loudnorm audio processing implementation and migration tools.

## Overview

The application now applies 2-pass loudnorm filtering for audio normalization and compression using FFmpeg. This ensures consistent audio levels across all tracks in the music quiz game.

## How It Works

### Automatic Processing
For new files (both uploaded and downloaded), loudnorm processing is automatically applied after successful Shazam recognition:

1. **First Pass**: `ffprobe` analyzes the audio to measure current loudness levels
2. **Second Pass**: `ffmpeg` applies loudnorm filter with measured values to normalize audio

Target normalization parameters:
- Integrated loudness (I): -16 LUFS
- Loudness range (LRA): 2 LU  
- True peak (TP): -1 dBFS

### Migration for Existing Files

For existing audio files that were processed before loudnorm was implemented, use the migration script:

```bash
# Run migration for all existing .m4a files in data directory
python3 migrate_loudnorm.py

# Or with custom data directory
HACKSTAR_DATA_DIR=/path/to/data python3 migrate_loudnorm.py
```

The migration script will:
- Process all .m4a files in the data directory
- Apply the same 2-pass loudnorm processing
- Replace original files with normalized versions
- Provide detailed logging of the process

## Testing

Test the loudnorm implementation:

```bash
# Run integration test
python3 test_loudnorm.py
```

This test creates synthetic audio, applies loudnorm processing, and verifies the normalization works correctly.

## Requirements

- FFmpeg with loudnorm filter support (included in recent versions)
- FFprobe (comes with FFmpeg)

## Technical Details

The loudnorm filter uses the ITU-R BS.1770-4 standard for loudness measurement and the EBU R128 recommendation for loudness normalization. This ensures professional-quality audio normalization suitable for broadcast and streaming applications.

The 2-pass approach (instead of a simple single-pass) prevents audio distortion at the beginning of tracks by measuring the entire audio first, then applying normalization based on the global measurements.