import os
import re
import subprocess
from datetime import datetime, timedelta


def convert_srt_time_to_seconds(srt_time):
    """Convert SRT time format to seconds."""
    parts = list(map(int, re.split('[:,]', srt_time)))
    return parts[0] * 3600 + parts[1] * 60 + parts[2] + parts[3] / 1000


def convert_seconds_to_timestamp(seconds):
    """Convert seconds to a timestamp."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds % 1) * 1000)
    seconds = int(seconds)
    return f"{int(hours)}-{int(minutes):02}-{seconds:02}-{milliseconds:03}"


def main(video_path):
    # Extract the directory and filename without extension
    video_dir = os.path.dirname(video_path)
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    # Determine the subtitle file path
    subtitle_path = os.path.join(video_dir, f"{video_name}.srt")

    # Determine the output directory
    output_dir = os.path.join(video_dir, video_name)

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Read subtitles
    with open(subtitle_path, 'r', encoding='utf-8') as f:
        subtitles = f.read()

    # Split subtitles into blocks
    blocks = re.split(r'\r?\n\r?\n', subtitles.strip())

    # Process each block
    for block in blocks:
        match = re.match(r'(\d+)\r?\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\r?\n(.+)', block, re.DOTALL)
        if match:
            index, start_time, end_time, text = match.groups()

            start_seconds = convert_srt_time_to_seconds(start_time)
            end_seconds = convert_srt_time_to_seconds(end_time)
            middle_seconds = (start_seconds + end_seconds) / 2
            timestamp = convert_seconds_to_timestamp(middle_seconds)

            output_file = os.path.join(output_dir, f"{video_name}-{timestamp}.png")

            # Escape the subtitle path
            escaped_subtitle_path = subtitle_path.replace('\\', '\\\\').replace(':', '\:').replace('.srt', '.ass')

            # Use ffmpeg to create a screenshot
            ffmpeg_args = [
                'ffmpeg', '-ss', str(middle_seconds), '-copyts', '-i', video_path,
                '-vf', f"subtitles='{escaped_subtitle_path}'",
                '-vframes', '1', '-y', output_file
            ]
            print(f"Running ffmpeg with arguments: {' '.join(ffmpeg_args)}")
            subprocess.run(ffmpeg_args, check=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Extract screenshots from video based on subtitle timings.')
    parser.add_argument('video_path', type=str, help='Path to the video file')

    args = parser.parse_args()
    main(args.video_path)
