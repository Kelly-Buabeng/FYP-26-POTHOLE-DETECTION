import csv
import io
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Response

from app.core.dependencies import verify_api_key
from app.schemas.detection import ReportResponse, RegionReport, SeverityBreakdown
from app.services.detection_repo import get_all_detections
from app.services.geo import nearest_region, severity_bucket

router = APIRouter()


@router.get(
    "/report",
    response_model=ReportResponse,
    summary="Detections grouped by severity and region for GHA",
    dependencies=[Depends(verify_api_key)],
)
async def report(
    min_confidence: float = Query(default=0.4, ge=0.0, le=1.0),
    limit: int = Query(default=5000, le=20000),
):
    """
    Aggregates saved detections by nearest Ghana region and confidence-based
    severity band (high >= 0.75, medium >= 0.5, else low), for handoff to
    the Ghana Highway Authority. Region is nearest-centroid, not a precise
    boundary lookup — see app/services/geo.py.
    """
    rows = await get_all_detections(min_confidence=min_confidence, limit=limit)

    confidences_by_region: dict[str, list[float]] = {}
    breakdown_by_region: dict[str, SeverityBreakdown] = {}

    for row in rows:
        region = nearest_region(row["lat"], row["lng"])
        confidences_by_region.setdefault(region, []).append(row["confidence"])
        breakdown = breakdown_by_region.setdefault(region, SeverityBreakdown())
        bucket = severity_bucket(row["confidence"])
        setattr(breakdown, bucket, getattr(breakdown, bucket) + 1)

    regions = [
        RegionReport(
            region=region,
            total=len(confidences),
            avg_confidence=round(sum(confidences) / len(confidences), 4),
            severity_breakdown=breakdown_by_region[region],
        )
        for region, confidences in sorted(
            confidences_by_region.items(), key=lambda kv: -len(kv[1])
        )
    ]

    return ReportResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_detections=len(rows),
        regions=regions,
    )


@router.get(
    "/detections/export",
    summary="Export detections as CSV or GeoJSON for QGIS/ArcGIS",
    dependencies=[Depends(verify_api_key)],
)
async def export_detections(
    format: str = Query(default="csv", pattern="^(csv|geojson)$", description="csv or geojson"),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
    limit: int = Query(default=5000, le=20000),
):
    """
    Downloads saved detections. `geojson` returns a Point FeatureCollection
    ready to drag into QGIS/ArcGIS; `csv` returns one row per detection
    with region/severity columns for spreadsheet or GIS table joins.
    """
    rows = await get_all_detections(min_confidence=min_confidence, limit=limit)

    if format == "geojson":
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row["lng"], row["lat"]]},
                "properties": {
                    "id": row["id"],
                    "device_id": row["device_id"],
                    "confidence": row["confidence"],
                    "severity": severity_bucket(row["confidence"]),
                    "region": nearest_region(row["lat"], row["lng"]),
                    "created_at": row["created_at"],
                    "labels": [d["label"] for d in row.get("detections") or []],
                },
            }
            for row in rows
        ]
        body = json.dumps({"type": "FeatureCollection", "features": features})
        return Response(
            content=body,
            media_type="application/geo+json",
            headers={"Content-Disposition": "attachment; filename=detections.geojson"},
        )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["id", "device_id", "lat", "lng", "confidence", "severity", "region", "num_objects", "created_at"]
    )
    for row in rows:
        writer.writerow([
            row["id"],
            row["device_id"],
            row["lat"],
            row["lng"],
            row["confidence"],
            severity_bucket(row["confidence"]),
            nearest_region(row["lat"], row["lng"]),
            len(row.get("detections") or []),
            row["created_at"],
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=detections.csv"},
    )
