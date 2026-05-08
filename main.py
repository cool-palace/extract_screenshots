import os
import re
import subprocess
import time


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


def get_video_resolution(video_path):
    """Extract video resolution using ffmpeg."""
    ffprobe_cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=width,height', '-of', 'csv=p=0', video_path
    ]
    result = subprocess.run(ffprobe_cmd, capture_output=True, text=True)
    width, height = result.stdout.strip().split(',')
    return int(width), int(height)


def process_folder(input_folder, output_folder=None, quality="original"):
    """Process all videos in a folder, saving results with original folder structure in output directory."""
    # Имя корневой папки (например, "Folder" для пути "C:\Folder")
    root_folder_name = os.path.basename(input_folder.rstrip(os.sep))

    # Устанавливаем базовую выходную директорию:
    # если output_folder не указан, используем input_folder
    if output_folder is None:
        base_output_dir = input_folder
    else:
        base_output_dir = os.path.join(output_folder, root_folder_name)
        os.makedirs(base_output_dir, exist_ok=True)

    # Рекурсивно обходим все файлы и папки
    for root, _, files in os.walk(input_folder):
        for file in files:
            m = re.match(r'\[Beatrice-Raws\] One Piece (\d\d\d) \[DVDRip 768x576 x264 AC3\]\.mkv', str(file))
            if m:
                if int(m[1]) < 40:
                    continue
            # Проверяем, является ли файл видео (можно добавить свои условия)
            if file.endswith(('.mp4', '.mkv', '.avi')):
                video_path = os.path.join(root, file)

                # Путь относительно корневой папки input_folder
                relative_path = os.path.relpath(root, input_folder)

                # Директория для текущего видеофайла
                video_name = os.path.splitext(file)[0]
                output_dir = os.path.join(base_output_dir, relative_path, video_name)
                os.makedirs(output_dir, exist_ok=True)

                print(f"Processing video: {video_path}")
                process_video(video_path, output_dir, quality)


def process_video(video_path, output_dir, quality='original'):
    # Extract the directory and filename without extension
    video_dir = os.path.dirname(video_path)
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    # Extract resolution
    width, height = get_video_resolution(video_path)
    original_size = f"{width}x{height}"

    # Determine the subtitle file path
    subtitle_path = os.path.join(video_dir, f"{video_name}.ass")

    subtitle_path_srt = subtitle_path.replace('.ass', '.srt')

    srt_mode = False     # os.path.exists(subtitle_path_srt)
    if srt_mode:
        subtitle_path = subtitle_path_srt

    # output_dir = os.path.join(f"C:\\Users\\User\\Pictures\\Compressed Pack\\", video_name)

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Read subtitles
    with open(subtitle_path, 'r', encoding='utf-8') as f:
        subtitles = f.read()

    # Split subtitles into lines
    lines = re.split(r'\r?\n\r?\n', subtitles.strip()) if srt_mode else subtitles.strip().split('\n')

    # Regex to match Dialogue lines with timestamps
    dialogue_re = re.compile(r'Dialogue:\s*\d+,\s*(\d+:\d+:\d+\.\d+),\s*(\d+:\d+:\d+\.\d+),(?:[^,]*,){6}(.+)')
    # Regex to match SRT subtitle lines with timestamps
    srt_time_re = re.compile(r'\d+\r?\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\r?\n(.+)', re.DOTALL)

    ignored_tags_re = re.compile(r'^(?:\{\\(?:blur|an5|fade))')

    offset = 0 if srt_mode else 0.4

    # Process each block
    for line in lines:
        match = srt_time_re.match(line) if srt_mode else dialogue_re.match(line)
        if match:
            start_time, end_time, subtitle_text = match.groups()

            if ignored_tags_re.match(subtitle_text):
                continue

            start_seconds = convert_time_to_seconds(start_time)
            end_seconds = convert_time_to_seconds(end_time)
            middle_seconds = (start_seconds + end_seconds) / 2 + offset
            timestamp = convert_seconds_to_timestamp(middle_seconds)

            image_format = 'jpg' if quality == 'compressed' else 'png'
            output_file = os.path.join(output_dir, f"{video_name}-{timestamp}.{image_format}")

            if not os.path.isfile(output_file):
                # Escape the subtitle path
                pre_subtitle_path = subtitle_path.replace('\\', '\\\\').replace(':', '\:')
                escaped_subtitle_path = pre_subtitle_path.replace('.srt', '.ass') if srt_mode else pre_subtitle_path

                # Use ffmpeg to create a screenshot
                if quality == "original":
                    ffmpeg_args = [
                        'ffmpeg', '-ss', str(middle_seconds), '-copyts', '-i', video_path,
                        '-vf', f"subtitles='{subtitle_path}",
                        '-vframes', '1', '-y', output_file
                    ]
                elif quality == "compressed":
                    ffmpeg_args = [
                        'ffmpeg', '-ss', str(middle_seconds), '-copyts', '-i', video_path,
                        '-vf', f"subtitles='{escaped_subtitle_path}:original_size={original_size}',scale=-1:360'",
                        '-vframes', '1', '-q:v', '20', '-y', output_file
                    ]
                else:
                    raise ValueError("Invalid quality parameter. Use 'original' or 'compressed'.")

                print(f"Running ffmpeg with arguments: {' '.join(ffmpeg_args)}")
                subprocess.run(ffmpeg_args, check=True)
            else:
                print(f"{output_file} already exists, skipping to to next one")
    # time.sleep(60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Extract screenshots from video based on subtitle timings.')
    parser.add_argument(
        '-i', '--input', type=str, required=True,
        help='Path to the input video file or directory with videos.'
    )
    parser.add_argument(
        '-o', '--output', type=str, required=False,
        help='Path to the output directory where screenshots will be saved.'
    )
    parser.add_argument(
        '-q', '--quality', choices=['original', 'compressed'], default='compressed',
        help="Specify the output quality: 'original' for PNG (full resolution) or 'compressed' for JPEG (360px height)."
    )

    args = parser.parse_args()

    # Check if input is a file or directory
    if os.path.isfile(args.input):
        # Process a single video file
        process_video(args.input, args.output, args.quality)
    elif os.path.isdir(args.input):
        # Process all videos in a directory
        process_folder(args.input, args.output, args.quality)
    else:
        raise ValueError("The input path must be a valid file or directory.")

