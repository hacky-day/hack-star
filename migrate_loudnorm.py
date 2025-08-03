#!/usr/bin/env python3
"""
Migration script to apply loudnorm filter to existing audio files.

This script processes all existing .m4a files in the data directory
and applies the 2-pass loudnorm filter for audio normalization.
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DATA_DIR = os.environ.get("HACKSTAR_DATA_DIR", "data")


def apply_loudnorm_filter(input_file, output_file):
    """
    Apply 2-pass loudnorm filter for audio normalization and compression.
    
    Args:
        input_file (str): Path to input audio file
        output_file (str): Path to output audio file
    
    Returns:
        bool: True if processing succeeded, False otherwise
    """
    try:
        logger.info("Starting loudnorm processing for %s", input_file)
        
        # Convert to absolute paths to avoid path issues
        abs_input = os.path.abspath(input_file)
        abs_output = os.path.abspath(output_file)
        
        # First pass: Detect current loudness levels
        ffprobe_command = [
            "ffprobe",
            "-f", "lavfi",
            "-hide_banner",
            "-i", f"amovie={abs_input},loudnorm=print_format=json[out]",
            "-loglevel", "info"
        ]
        
        logger.debug("Running first pass (loudness detection): %s", " ".join(ffprobe_command))
        result = subprocess.run(
            ffprobe_command,
            text=True,
            capture_output=True
        )
        
        if result.returncode != 0:
            logger.error("First pass failed: %s", result.stderr)
            return False
            
        # Extract JSON from stderr output (ffprobe outputs to stderr)
        stderr_lines = result.stderr.split('\n')
        json_start = -1
        json_end = -1
        
        for i, line in enumerate(stderr_lines):
            if line.strip() == '{':
                json_start = i
            elif line.strip() == '}' and json_start != -1:
                json_end = i
                break
        
        if json_start == -1 or json_end == -1:
            logger.error("Could not find JSON output in ffprobe result")
            return False
        
        json_str = '\n'.join(stderr_lines[json_start:json_end + 1])
        
        try:
            loudness_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse loudness JSON: %s", e)
            return False
        
        # Extract measured values
        measured_i = loudness_data.get("input_i", "-16.00")
        measured_tp = loudness_data.get("input_tp", "-1.50")
        measured_lra = loudness_data.get("input_lra", "2.00")
        measured_thresh = loudness_data.get("input_thresh", "-26.00")
        
        logger.info("Measured loudness values - I: %s, TP: %s, LRA: %s, Thresh: %s", 
                   measured_i, measured_tp, measured_lra, measured_thresh)
        
        # Second pass: Apply loudnorm with measured values
        ffmpeg_command = [
            "ffmpeg",
            "-i", abs_input,
            "-filter:a", 
            f"loudnorm=I=-16:LRA=2:tp=-1:measured_i={measured_i}:measured_tp={measured_tp}:measured_lra={measured_lra}:measured_thresh={measured_thresh}:print_format=summary",
            "-c:a", "aac",
            "-movflags", "faststart",
            "-y",  # Overwrite output file
            abs_output
        ]
        
        logger.debug("Running second pass (loudnorm application): %s", " ".join(ffmpeg_command))
        result = subprocess.run(
            ffmpeg_command,
            text=True,
            capture_output=True
        )
        
        if result.returncode != 0:
            logger.error("Second pass failed: %s", result.stderr)
            return False
        
        logger.info("Loudnorm processing completed successfully for %s", output_file)
        return True
        
    except Exception as e:
        logger.error("Error during loudnorm processing: %s", e)
        return False


def migrate_existing_files():
    """
    Migrate all existing .m4a files in the data directory to use loudnorm.
    """
    data_path = Path(DATA_DIR)
    
    if not data_path.exists():
        logger.error("Data directory %s does not exist", DATA_DIR)
        return False
    
    # Find all .m4a files
    audio_files = list(data_path.glob("*.m4a"))
    
    if not audio_files:
        logger.info("No .m4a files found in %s", DATA_DIR)
        return True
    
    logger.info("Found %d audio files to process", len(audio_files))
    
    success_count = 0
    failure_count = 0
    
    for audio_file in audio_files:
        logger.info("Processing file: %s", audio_file.name)
        
        # Create temporary output file
        temp_output = audio_file.with_suffix('.tmp.m4a')
        
        try:
            if apply_loudnorm_filter(str(audio_file), str(temp_output)):
                # Replace original with normalized version
                temp_output.replace(audio_file)
                success_count += 1
                logger.info("Successfully processed %s", audio_file.name)
            else:
                failure_count += 1
                logger.error("Failed to process %s", audio_file.name)
                # Clean up temp file if it exists
                if temp_output.exists():
                    temp_output.unlink()
        except Exception as e:
            failure_count += 1
            logger.error("Exception processing %s: %s", audio_file.name, e)
            # Clean up temp file if it exists
            if temp_output.exists():
                temp_output.unlink()
    
    logger.info("Migration completed. Success: %d, Failures: %d", success_count, failure_count)
    
    return failure_count == 0


def main():
    """Main entry point for the migration script."""
    logger.info("Starting loudnorm migration for existing audio files")
    logger.info("Data directory: %s", DATA_DIR)
    
    # Check if ffmpeg and ffprobe are available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("FFmpeg and/or FFprobe not found. Please install FFmpeg.")
        sys.exit(1)
    
    success = migrate_existing_files()
    
    if success:
        logger.info("Migration completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()