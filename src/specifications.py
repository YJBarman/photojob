from dataclasses import dataclass
from typing import Optional


@dataclass
class PhotoSpec:
    name: str

    # Exact pixel dimensions
    width_px: Optional[int] = None
    height_px: Optional[int] = None

    # Pixel dimension ranges
    min_width_px: Optional[int] = None
    max_width_px: Optional[int] = None

    min_height_px: Optional[int] = None
    max_height_px: Optional[int] = None

    # File size
    min_kb: Optional[int] = None
    max_kb: Optional[int] = None

    # Physical dimensions
    physical_size_mm: Optional[tuple] = None

    # Background expectation
    background: Optional[str] = None

    # Additional information
    notes: str = ""


SPECS = {

    # ---------------------------------------------------------
    # Banking
    # ---------------------------------------------------------

    "banking": PhotoSpec(
        name="Banking — IBPS / SBI",

        width_px=200,
        height_px=230,

        min_kb=20,
        max_kb=50,

        background="white",

        notes=(
            "Recruitment portal requirements may change."
        )
    ),

    # ---------------------------------------------------------
    # Railways
    # ---------------------------------------------------------

    "railways": PhotoSpec(
        name="Railways — RRB",
        width_px=413,
        height_px=531,
        min_kb=30,
        max_kb=70,
        background="white",
        physical_size_mm=(35, 45),
        notes=(
            "35 × 45 mm at 300 DPI ≈ 413 × 531 px. "
            "If the recruitment portal requires live capture, "
            "that portal process must still be completed separately."
        )
    ),

    # ---------------------------------------------------------
    # UPSC
    # ---------------------------------------------------------

    "upsc": PhotoSpec(
        name="UPSC",

        min_width_px=350,
        max_width_px=1000,

        min_height_px=350,
        max_height_px=1000,

        min_kb=20,
        max_kb=300,

        background="white",

        notes=(
            "Name/date requirements should be checked "
            "against the specific application notification."
        )
    ),

    # ---------------------------------------------------------
    # SSC
    # ---------------------------------------------------------

    "ssc": PhotoSpec(
        name="SSC",

        notes=(
            "No static upload dimensions are configured "
            "for this preset. Use Custom if a specific "
            "photo specification is provided by the application."
        )
    ),

    # ---------------------------------------------------------
    # NTA
    # ---------------------------------------------------------

    "nta": PhotoSpec(
        name="NTA — NEET / JEE / CUET",

        width_px=275,
        height_px=354,

        min_kb=10,
        max_kb=200,

        background="white",

        notes=(
            "Face coverage and application-specific "
            "requirements should be checked against "
            "the current notification."
        )
    ),

    # ---------------------------------------------------------
    # India Post
    # ---------------------------------------------------------

    "india_post": PhotoSpec(
        name="India Post — GDS",

        width_px=200,
        height_px=230,

        max_kb=50,

        background="white"
    ),

    # ---------------------------------------------------------
    # State PSC
    # ---------------------------------------------------------

    "state_psc": PhotoSpec(
        name="State PSC",

        width_px=200,
        height_px=250,

        min_kb=20,
        max_kb=100,

        background="white",

        notes=(
            "Different PSCs may specify different "
            "dimensions."
        )
    )
}