from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), default="")
    last_name: Mapped[str] = mapped_column(String(100), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    skill_level: Mapped[str] = mapped_column(String(100), default="")
    handedness: Mapped[str] = mapped_column(String(20), default="Unknown")
    handicap_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    primary_goal: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="Active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    sessions: Mapped[list["CoachingSession"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
    )

    @property
    def name(self) -> str:
        return " ".join(
            part
            for part in [self.first_name.strip(), self.last_name.strip()]
            if part
        )


class CoachingSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    student_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True,
    )

    session_date: Mapped[date] = mapped_column(
        Date,
        default=date.today,
        index=True,
    )

    session_type: Mapped[str] = mapped_column(
        String(100),
        default="Coaching Session",
    )

    primary_club: Mapped[str] = mapped_column(String(100), default="")
    name: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    coaching_notes: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    student: Mapped["Student"] = relationship(
        back_populates="sessions",
    )

    shots: Mapped[list["Shot"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )

    videos: Mapped[list["SessionVideo"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )

    swing_analyses: Mapped[list["SwingAnalysis"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )

    @property
    def shot_count(self) -> int:
        return len(self.shots)


class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True,
    )

    student_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True,
    )

    shot_number: Mapped[int] = mapped_column(Integer, default=1)
    club: Mapped[str] = mapped_column(String(100), default="", index=True)
    shot_shape: Mapped[str] = mapped_column(String(50), default="")
    source: Mapped[str] = mapped_column(String(50), default="Garmin R10")
    included: Mapped[bool] = mapped_column(Boolean, default=True)

    ball_speed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    club_speed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    smash_factor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    launch_angle: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    launch_direction: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spin_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spin_axis: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    carry_distance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_distance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    apex_height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attack_angle: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    club_path: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    club_face: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    face_to_path: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    offline_distance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    raw_signature: Mapped[str] = mapped_column(
        String(512),
        default="",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    session: Mapped["CoachingSession"] = relationship(
        back_populates="shots",
    )


class SessionVideo(Base):
    __tablename__ = "session_videos"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True,
    )

    student_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        default="Swing Video",
    )

    # original_swing | onform_analysis | reference
    video_type: Mapped[str] = mapped_column(
        String(50),
        default="original_swing",
        index=True,
    )

    # Golf Coach | Onform | Garmin R10 | Upload
    source: Mapped[str] = mapped_column(
        String(50),
        default="Golf Coach",
    )

    # Onform analysis -> original swing
    parent_video_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("session_videos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    parent_video: Mapped[Optional["SessionVideo"]] = relationship(
        "SessionVideo",
        remote_side="SessionVideo.id",
        foreign_keys=[parent_video_id],
        back_populates="analysis_videos",
    )

    analysis_videos: Mapped[list["SessionVideo"]] = relationship(
        "SessionVideo",
        foreign_keys="SessionVideo.parent_video_id",
        back_populates="parent_video",
    )

    camera_view: Mapped[str] = mapped_column(String(50), default="")
    club: Mapped[str] = mapped_column(String(100), default="")
    shot_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")

    original_filename: Mapped[str] = mapped_column(
        String(255),
        default="",
    )

    stored_filename: Mapped[str] = mapped_column(
        String(255),
        default="",
    )

    content_type: Mapped[str] = mapped_column(
        String(100),
        default="video/mp4",
    )

    onform_url: Mapped[str] = mapped_column(Text, default="")
    onform_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    # not_analyzed | ready | analyzed | reviewed
    analysis_status: Mapped[str] = mapped_column(
        String(50),
        default="not_analyzed",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    session: Mapped["CoachingSession"] = relationship(
        back_populates="videos",
    )

    @property
    def is_original_swing(self) -> bool:
        return self.video_type == "original_swing"

    @property
    def is_onform_analysis(self) -> bool:
        return self.video_type == "onform_analysis"

    @property
    def has_onform_analysis(self) -> bool:
        return any(
            video.video_type == "onform_analysis"
            for video in self.analysis_videos
        )


# ============================================================
# PHASE 5.2.1 — SWING ANALYSIS DATA MODEL
# ============================================================

class SwingAnalysis(Base):
    """
    One coaching-analysis record for one original swing.

    This is the bridge between:
      - original swing video
      - optional Onform analysis video
      - optional Garmin R10 shot
      - P1–P10 checkpoints
      - TGM interpretation
      - TPI body-swing interpretation
      - biomechanics
      - coaching observations and priorities
    """

    __tablename__ = "swing_analyses"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True,
    )

    student_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True,
    )

    original_video_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("session_videos.id", ondelete="CASCADE"),
        index=True,
    )

    onform_analysis_video_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("session_videos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    shot_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("shots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # draft | measured | analyzed | coach_reviewed | complete
    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        index=True,
    )

    # Face On | Down the Line | Other
    camera_view: Mapped[str] = mapped_column(
        String(50),
        default="",
    )

    club: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    # ========================================================
    # SWING PATTERN / TGM
    # ========================================================

    # swinging | hitting | blended | undetermined
    tgm_pattern: Mapped[str] = mapped_column(
        String(50),
        default="undetermined",
    )

    tgm_stationary_head: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tgm_balance: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tgm_rhythm: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tgm_club_path: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tgm_clubface_alignment: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tgm_timing: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tgm_power_accumulator_1: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tgm_power_accumulator_2: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tgm_power_accumulator_3: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tgm_power_accumulator_4: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tgm_plane_notes: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tgm_component_notes: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    # ========================================================
    # TPI BODY-SWING CONNECTION
    # ========================================================

    tpi_swing_characteristics: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tpi_mobility_observations: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tpi_stability_observations: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tpi_balance_observations: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tpi_sequencing_observations: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tpi_physical_screen_recommended: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    tpi_screen_reason: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    # ========================================================
    # BIOMECHANICS — SWING-LEVEL SUMMARY
    # ========================================================

    max_pelvis_rotation: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    max_torso_rotation: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    max_x_factor: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    max_x_factor_stretch: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    address_spine_tilt: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    top_shoulder_tilt: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    top_hip_tilt: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    finish_balance_offset: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    head_c7_stability_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    rhythm_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    sequencing_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    # ========================================================
    # GARMIN / BALL-FLIGHT INTERPRETATION
    # ========================================================

    garmin_summary: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    ball_flight_summary: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    movement_to_impact_summary: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    # ========================================================
    # COACHING OUTPUT
    # ========================================================

    primary_finding: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    secondary_findings: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    likely_compensations: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    primary_priority: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    coaching_observations: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    recommended_drills: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    player_feels: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    coach_notes: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    # Flexible JSON-like text for future metrics without
    # requiring a schema migration for every new measurement.
    extra_metrics_json: Mapped[str] = mapped_column(
        Text,
        default="{}",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    session: Mapped["CoachingSession"] = relationship(
        back_populates="swing_analyses",
    )

    original_video: Mapped["SessionVideo"] = relationship(
        "SessionVideo",
        foreign_keys=[original_video_id],
    )

    onform_analysis_video: Mapped[Optional["SessionVideo"]] = relationship(
        "SessionVideo",
        foreign_keys=[onform_analysis_video_id],
    )

    shot: Mapped[Optional["Shot"]] = relationship(
        "Shot",
        foreign_keys=[shot_id],
    )

    checkpoints: Mapped[list["SwingCheckpoint"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="SwingCheckpoint.position_order",
    )


class SwingCheckpoint(Base):
    """
    P1–P10 checkpoint measurements and observations.

    P positions are analysis/timing anchors, not mandatory
    aesthetic positions.
    """

    __tablename__ = "swing_checkpoints"

    __table_args__ = (
        UniqueConstraint(
            "analysis_id",
            "position",
            name="uq_swing_checkpoint_analysis_position",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    analysis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("swing_analyses.id", ondelete="CASCADE"),
        index=True,
    )

    # P1 ... P10
    position: Mapped[str] = mapped_column(
        String(10),
        index=True,
    )

    # Numeric sort order 1 ... 10
    position_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    # Frame/video location
    frame_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    time_seconds: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    # ========================================================
    # CHECKPOINT BIOMECHANICS
    # ========================================================

    pelvis_rotation: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    torso_rotation: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    x_factor: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    shoulder_tilt: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    hip_tilt: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    spine_tilt: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    shaft_angle: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    lead_arm_angle: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    trail_arm_angle: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    head_x: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    head_y: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    pelvis_x: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    pelvis_y: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    hand_path_x: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    hand_path_y: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    # ========================================================
    # CHECKPOINT INTERPRETATION
    # ========================================================

    tgm_observation: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    tpi_observation: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    biomechanical_observation: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    coaching_observation: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    # Manual | Onform | Auto Vision | Coach
    measurement_source: Mapped[str] = mapped_column(
        String(50),
        default="Manual",
    )

    # 0.0–1.0 when automated measurement is later introduced.
    confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    extra_metrics_json: Mapped[str] = mapped_column(
        Text,
        default="{}",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    analysis: Mapped["SwingAnalysis"] = relationship(
        back_populates="checkpoints",
    )
