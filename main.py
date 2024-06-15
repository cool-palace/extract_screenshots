import os
import re
import subprocess


def convert_srt_time_to_seconds(srt_time):
    """Convert SRT time format to seconds."""
    parts = list(map(int, re.split('[:,]', srt_time)))
    return parts[0] * 3600 + parts[1] * 60 + parts[2] + parts[3] / 1000


def convert_ass_time_to_seconds(ass_time):
    """Convert ASS time format to seconds."""
    hours, minutes, seconds, milliseconds = map(float, re.split('[:.]', ass_time))
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000


def convert_time_to_seconds(time):
    """Convert any time format to seconds."""
    if re.match(r'(\d{2}:\d{2}:\d{2},\d{3})', time):
        return convert_srt_time_to_seconds(time)
    elif re.match(r'(\d+:\d+:\d+\.\d+)', time):
        return convert_ass_time_to_seconds(time)
    else:
        return 1


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
    subtitle_path = os.path.join(video_dir, f"{video_name}.ass")

    subtitle_path_srt = subtitle_path.replace('.ass', '.srt')

    srt_mode = os.path.exists(subtitle_path_srt)
    if srt_mode:
        subtitle_path = subtitle_path_srt

    # Determine the output directory
    output_dir = os.path.join(video_dir, video_name)

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Read subtitles
    with open(subtitle_path, 'r', encoding='utf-8') as f:
        subtitles = f.read()

    # Split subtitles into lines
    lines = re.split(r'\r?\n\r?\n', subtitles.strip()) if srt_mode else subtitles.strip().split('\n')

    # Regex to match Dialogue lines with timestamps
    dialogue_re = re.compile(r'Dialogue:\s*\d+,\s*(\d+:\d+:\d+\.\d+),\s*(\d+:\d+:\d+\.\d+),(.+)')
    # Regex to match SRT subtitle lines with timestamps
    srt_time_re = re.compile(r'\d+\r?\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\r?\n(.+)', re.DOTALL)

    offset = 0 if srt_mode else 0.4

    # Process each block
    for line in lines:
        match = srt_time_re.match(line) if srt_mode else dialogue_re.match(line)
        if match:
            start_time, end_time, _ = match.groups()

            start_seconds = convert_time_to_seconds(start_time)
            end_seconds = convert_time_to_seconds(end_time)
            middle_seconds = (start_seconds + end_seconds) / 2 + offset
            timestamp = convert_seconds_to_timestamp(middle_seconds)

            output_file = os.path.join(output_dir, f"{video_name}-{timestamp}.png")

            # Escape the subtitle path
            pre_subtitle_path = subtitle_path.replace('\\', '\\\\').replace(':', '\:')
            escaped_subtitle_path = pre_subtitle_path.replace('.srt', '.ass') if srt_mode else pre_subtitle_path

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
