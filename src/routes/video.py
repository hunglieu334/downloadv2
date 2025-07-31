from flask import Blueprint, request, jsonify, current_app
import yt_dlp
import ffmpeg
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
import time

video_bp = Blueprint("video", __name__)

# Global variables for tracking downloads and processing
active_downloads = {}
active_processing = {}
download_executor = ThreadPoolExecutor(max_workers=5)
processing_executor = ThreadPoolExecutor(max_workers=3)

@video_bp.route("/download", methods=["POST"])
def download_video():
    """Download video from URL with multi-threading support"""
    try:
        data = request.get_json()
        url = data.get("url")
        quality = data.get("quality", "best")
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Create download directory
        download_dir = os.path.join(os.path.dirname(__file__), "..", "downloads")
        os.makedirs(download_dir, exist_ok=True)
        
        # Initialize job status
        active_downloads[job_id] = {
            "status": "starting",
            "progress": 0,
            "url": url,
            "quality": quality,
            "files": []
        }
        
        # Submit download task
        future = download_executor.submit(download_task, job_id, url, quality, download_dir)
        
        return jsonify({
            "job_id": job_id,
            "status": "started",
            "message": "Download started successfully"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@video_bp.route("/download-channel", methods=["POST"])
def download_channel():
    """Download all videos from a channel"""
    try:
        data = request.get_json()
        channel_url = data.get("channel_url")
        quality = data.get("quality", "best")
        max_videos = data.get("max_videos", 50)  # Limit for demo
        
        if not channel_url:
            return jsonify({"error": "Channel URL is required"}), 400
        
        job_id = str(uuid.uuid4())
        download_dir = os.path.join(os.path.dirname(__file__), "..", "downloads", job_id)
        os.makedirs(download_dir, exist_ok=True)
        
        active_downloads[job_id] = {
            "status": "starting",
            "progress": 0,
            "channel_url": channel_url,
            "quality": quality,
            "total_videos": 0,
            "downloaded_videos": 0,
            "files": []
        }
        
        future = download_executor.submit(download_channel_task, job_id, channel_url, quality, download_dir, max_videos)
        
        return jsonify({
            "job_id": job_id,
            "status": "started",
            "message": "Channel download started successfully"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@video_bp.route("/process", methods=["POST"])
def process_videos():
    """Process multiple videos with FFmpeg filters"""
    try:
        data = request.get_json()
        video_files = data.get("video_files", [])
        filters = data.get("filters", {})
        
        if not video_files:
            return jsonify({"error": "Video files are required"}), 400
        
        job_id = str(uuid.uuid4())
        output_dir = os.path.join(os.path.dirname(__file__), "..", "processed", job_id)
        os.makedirs(output_dir, exist_ok=True)
        
        active_processing[job_id] = {
            "status": "starting",
            "progress": 0,
            "total_videos": len(video_files),
            "processed_videos": 0,
            "filters": filters,
            "output_files": []
        }
        
        future = processing_executor.submit(process_videos_task, job_id, video_files, filters, output_dir)
        
        return jsonify({
            "job_id": job_id,
            "status": "started",
            "message": "Video processing started successfully"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@video_bp.route("/status/<job_id>", methods=["GET"])
def get_job_status(job_id):
    """Get status of download or processing job"""
    try:
        if job_id in active_downloads:
            return jsonify(active_downloads[job_id])
        elif job_id in active_processing:
            return jsonify(active_processing[job_id])
        else:
            return jsonify({"error": "Job not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@video_bp.route("/filters", methods=["GET"])
def get_available_filters():
    """Get list of available FFmpeg filters"""
    filters = {
        "video": {
            "scale": {"description": "Resize video", "params": ["width", "height"]},
            "crop": {"description": "Crop video", "params": ["width", "height", "x", "y"]},
            "rotate": {"description": "Rotate video", "params": ["angle"]},
            "brightness": {"description": "Adjust brightness", "params": ["value"]},
            "contrast": {"description": "Adjust contrast", "params": ["value"]},
            "saturation": {"description": "Adjust saturation", "params": ["value"]},
            "hue": {"description": "Adjust hue", "params": ["value"]},
            "blur": {"description": "Apply blur effect", "params": ["radius"]},
            "sharpen": {"description": "Sharpen video", "params": ["intensity"]},
            "grayscale": {"description": "Convert to grayscale", "params": []},
            "sepia": {"description": "Apply sepia effect", "params": []},
            "vignette": {"description": "Apply vignette effect", "params": ["intensity"]},
            "fade_in": {"description": "Fade in effect", "params": ["duration"]},
            "fade_out": {"description": "Fade out effect", "params": ["start_time", "duration"]},
            "speed": {"description": "Change playback speed", "params": ["factor"]},
            "reverse": {"description": "Reverse video", "params": []},
            "flip_horizontal": {"description": "Flip horizontally", "params": []},
            "flip_vertical": {"description": "Flip vertically", "params": []},
            "watermark": {"description": "Add watermark", "params": ["image_path", "position"]}
        },
        "audio": {
            "volume": {"description": "Adjust volume", "params": ["factor"]},
            "fade_in_audio": {"description": "Audio fade in", "params": ["duration"]},
            "fade_out_audio": {"description": "Audio fade out", "params": ["start_time", "duration"]},
            "speed_audio": {"description": "Change audio speed", "params": ["factor"]},
            "normalize": {"description": "Normalize audio", "params": []},
            "echo": {"description": "Add echo effect", "params": ["delay", "decay"]},
            "reverb": {"description": "Add reverb effect", "params": ["room_size"]},
            "bass_boost": {"description": "Boost bass frequencies", "params": ["gain"]},
            "treble_boost": {"description": "Boost treble frequencies", "params": ["gain"]}
        }
    }
    
    return jsonify(filters)

def download_task(job_id, url, quality, download_dir):
    """Background task for downloading video"""
    try:
        active_downloads[job_id]["status"] = "downloading"
        
        def progress_hook(d):
            if d["status"] == "downloading":
                if "total_bytes" in d and d["total_bytes"]:
                    progress = (d["downloaded_bytes"] / d["total_bytes"]) * 100
                    active_downloads[job_id]["progress"] = round(progress, 2)
                elif "total_bytes_estimate" in d and d["total_bytes_estimate"]:
                    progress = (d["downloaded_bytes"] / d["total_bytes_estimate"]) * 100
                    active_downloads[job_id]["progress"] = round(progress, 2)
            elif d["status"] == "finished":
                active_downloads[job_id]["files"].append(d["filename"])
        
        ydl_opts = {
            "format": f"{quality}[ext=mp4]/best[ext=mp4]/best",
            "outtmpl": os.path.join(download_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [progress_hook],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        active_downloads[job_id]["status"] = "completed"
        active_downloads[job_id]["progress"] = 100
        
    except Exception as e:
        active_downloads[job_id]["status"] = "error"
        active_downloads[job_id]["error"] = str(e)

def download_channel_task(job_id, channel_url, quality, download_dir, max_videos):
    """Background task for downloading channel videos"""
    try:
        active_downloads[job_id]["status"] = "extracting_info"
        
        def progress_hook(d):
            if d["status"] == "downloading":
                current_video = active_downloads[job_id]["downloaded_videos"]
                total_videos = active_downloads[job_id]["total_videos"]
                
                if "total_bytes" in d and d["total_bytes"]:
                    video_progress = (d["downloaded_bytes"] / d["total_bytes"]) * 100
                else:
                    video_progress = 0  # Initialize if no total bytes
                
                if total_videos > 0:
                    overall_progress = ((current_video + video_progress/100) / total_videos) * 100
                    active_downloads[job_id]["progress"] = round(overall_progress, 2)
                
            elif d["status"] == "finished":
                active_downloads[job_id]["files"].append(d["filename"])
                active_downloads[job_id]["downloaded_videos"] += 1
                # Update overall progress after each video finishes
                current_video = active_downloads[job_id]["downloaded_videos"]
                total_videos = active_downloads[job_id]["total_videos"]
                if total_videos > 0:
                    overall_progress = (current_video / total_videos) * 100
                    active_downloads[job_id]["progress"] = round(overall_progress, 2)
        
        ydl_opts = {
            "format": f"{quality}[ext=mp4]/best[ext=mp4]/best",
            "outtmpl": os.path.join(download_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [progress_hook],
            "playlistend": max_videos,
            "extract_flat": False,
            "noplaylist": False, # Ensure playlist is processed
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First, extract info to get video count
            info = ydl.extract_info(channel_url, download=False)
            if "entries" in info and info["entries"] is not None:
                # Filter out None entries and limit to max_videos
                valid_entries = [entry for entry in info["entries"] if entry is not None]
                total_videos = min(len(valid_entries), max_videos)
                active_downloads[job_id]["total_videos"] = total_videos
                active_downloads[job_id]["status"] = "downloading"
                
                # Download videos one by one to respect max_videos and progress tracking
                for i, entry in enumerate(valid_entries):
                    if i >= max_videos:
                        break
                    video_url = entry.get("url") or entry.get("webpage_url")
                    if video_url:
                        try:
                            ydl.download([video_url])
                        except Exception as video_e:
                            print(f"Error downloading video {video_url}: {video_e}")
                            # Continue to next video even if one fails
            else:
                # Single video or no entries found
                active_downloads[job_id]["total_videos"] = 1
                active_downloads[job_id]["status"] = "downloading"
                ydl.download([channel_url])
        
        active_downloads[job_id]["status"] = "completed"
        active_downloads[job_id]["progress"] = 100
        
    except Exception as e:
        active_downloads[job_id]["status"] = "error"
        active_downloads[job_id]["error"] = str(e)

def process_videos_task(job_id, video_files, filters, output_dir):
    """Background task for processing videos"""
    try:
        active_processing[job_id]["status"] = "processing"
        total_videos = len(video_files)
        
        for i, video_file in enumerate(video_files):
            try:
                # Build FFmpeg filter chain
                input_stream = ffmpeg.input(video_file)
                video_stream = input_stream["v"]
                audio_stream = input_stream["a"]
                
                # Apply video filters
                if "scale" in filters:
                    scale_params = filters["scale"]
                    video_stream = ffmpeg.filter(video_stream, "scale", 
                                                scale_params.get("width", -1), 
                                                scale_params.get("height", -1))
                
                if "brightness" in filters:
                    brightness = filters["brightness"].get("value", 0)
                    video_stream = ffmpeg.filter(video_stream, "eq", brightness=brightness)
                
                if "contrast" in filters:
                    contrast = filters["contrast"].get("value", 1)
                    video_stream = ffmpeg.filter(video_stream, "eq", contrast=contrast)
                
                if "saturation" in filters:
                    saturation = filters["saturation"].get("value", 1)
                    video_stream = ffmpeg.filter(video_stream, "eq", saturation=saturation)
                
                if "grayscale" in filters:
                    video_stream = ffmpeg.filter(video_stream, "format", "gray")
                
                if "blur" in filters:
                    radius = filters["blur"].get("radius", 5)
                    video_stream = ffmpeg.filter(video_stream, "boxblur", radius)
                
                if "speed" in filters:
                    factor = filters["speed"].get("factor", 1.0)
                    video_stream = ffmpeg.filter(video_stream, "setpts", f"PTS/{factor}")
                    audio_stream = ffmpeg.filter(audio_stream, "atempo", factor)
                
                if "flip_horizontal" in filters:
                    video_stream = ffmpeg.filter(video_stream, "hflip")
                
                if "flip_vertical" in filters:
                    video_stream = ffmpeg.filter(video_stream, "vflip")
                
                # Output file
                output_filename = f"processed_{i+1}_{os.path.basename(video_file)}"
                output_path = os.path.join(output_dir, output_filename)
                
                # Create output
                out = ffmpeg.output(video_stream, audio_stream, output_path, 
                                  vcodec="libx264", acodec="aac", preset="fast")
                
                # Run FFmpeg
                ffmpeg.run(out, overwrite_output=True, quiet=True)
                
                active_processing[job_id]["output_files"].append(output_path)
                active_processing[job_id]["processed_videos"] = i + 1
                active_processing[job_id]["progress"] = ((i + 1) / total_videos) * 100
                
            except Exception as e:
                print(f"Error processing video {video_file}: {str(e)}")
                continue
        
        active_processing[job_id]["status"] = "completed"
        active_processing[job_id]["progress"] = 100
        
    except Exception as e:
        active_processing[job_id]["status"] = "error"
        active_processing[job_id]["error"] = str(e)



