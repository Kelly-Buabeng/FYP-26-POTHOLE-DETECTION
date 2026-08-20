from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.dependencies import verify_api_key
from app.schemas.detection import VideoDetectionResponse
from app.services.detection_repo import save_video_detection
from app.services.video_processor import process_video_upload

router = APIRouter()


@router.post(
    "/detect/video",
    response_model=VideoDetectionResponse,
    summary="Run pothole detection on an uploaded video",
    dependencies=[Depends(verify_api_key)],
)
async def detect_video(video: UploadFile = File(..., description="Road video file (MP4/MOV/AVI)")):
    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video.")

    raw = await video.read()
    if len(raw) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Video too large. Max size is 100MB.")

    try:
        frames, gps_coordinates, summary = process_video_upload(raw, video.filename or "upload.mp4")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record_id = await save_video_detection(
        file_name=summary["file_name"],
        duration_ms=summary["duration_ms"],
        fps=summary["fps"],
        total_frames=summary["total_frames"],
        processed_frames=summary["processed_frames"],
        discarded_frames=summary["discarded_frames"],
        gps_coordinates=gps_coordinates,
        pothole_detected=summary["pothole_detected"],
        best_severity=summary["best_severity"],
        best_frame_index=summary["best_frame_index"],
        frames=[frame.model_dump() for frame in frames],
        device_id="manual",
    )

    return VideoDetectionResponse(
        id=record_id,
        file_name=summary["file_name"],
        duration_ms=summary["duration_ms"],
        fps=summary["fps"],
        total_frames=summary["total_frames"],
        processed_frames=summary["processed_frames"],
        discarded_frames=summary["discarded_frames"],
        gps_coordinates=gps_coordinates,
        frames=frames,
        pothole_detected=summary["pothole_detected"],
        best_severity=summary["best_severity"],
        best_frame_index=summary["best_frame_index"],
    )