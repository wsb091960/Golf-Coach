from pathlib import Path
path = Path('app/models.py')
text = path.read_text(encoding='utf-8')

# Add videos relationship to CoachingSession if absent.
needle = '    shots: Mapped[list["Shot"]] = relationship(\n        back_populates="session",\n        cascade="all, delete-orphan",\n    )\n'
addition = needle + '    videos: Mapped[list["SessionVideo"]] = relationship(\n        back_populates="session",\n        cascade="all, delete-orphan",\n    )\n'
if 'videos: Mapped[list["SessionVideo"]]' not in text:
    if needle not in text:
        raise SystemExit('Could not locate CoachingSession.shots relationship')
    text = text.replace(needle, addition, 1)

if 'class SessionVideo(Base):' not in text:
    text += '''\n\nclass SessionVideo(Base):\n    __tablename__ = "session_videos"\n\n    id: Mapped[str] = mapped_column(String(64), primary_key=True)\n    session_id: Mapped[str] = mapped_column(\n        String(64), ForeignKey("sessions.id", ondelete="CASCADE"), index=True\n    )\n    student_id: Mapped[str] = mapped_column(\n        String(64), ForeignKey("students.id", ondelete="CASCADE"), index=True\n    )\n    title: Mapped[str] = mapped_column(String(255), default="Onform Video")\n    camera_view: Mapped[str] = mapped_column(String(50), default="")\n    club: Mapped[str] = mapped_column(String(100), default="")\n    shot_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)\n    notes: Mapped[str] = mapped_column(Text, default="")\n    original_filename: Mapped[str] = mapped_column(String(255), default="")\n    stored_filename: Mapped[str] = mapped_column(String(255), default="")\n    content_type: Mapped[str] = mapped_column(String(100), default="video/mp4")\n    source: Mapped[str] = mapped_column(String(50), default="Onform")\n    onform_url: Mapped[str] = mapped_column(Text, default="")\n    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)\n\n    session: Mapped["CoachingSession"] = relationship(back_populates="videos")\n'''

path.write_text(text, encoding='utf-8')
print('Updated app/models.py for SessionVideo')
