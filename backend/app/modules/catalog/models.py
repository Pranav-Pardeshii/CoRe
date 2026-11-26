from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.infrastructure.database.base import Base


class College(Base):
    """Engineering institution participating in MHT-CET CAP."""

    __tablename__ = "colleges"

    college_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    college_name: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str | None] = mapped_column(String(300), nullable=True)
    division: Mapped[str | None] = mapped_column(String(100), nullable=True)

    branches: Mapped[list["Branch"]] = relationship(back_populates="college")


class Branch(Base):
    """Academic branch offered by a college."""

    __tablename__ = "branches"
    __table_args__ = (Index("ix_branches_college_code", "college_code"),)

    branch_code: Mapped[str] = mapped_column(String(15), primary_key=True)
    branch_name: Mapped[str] = mapped_column(String(300), nullable=False)
    college_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("colleges.college_code"),
        nullable=False,
    )

    college: Mapped["College"] = relationship(back_populates="branches")
    cutoffs: Mapped[list["AdmissionCutoff"]] = relationship(back_populates="branch")


class AdmissionCutoff(Base):
    """CAP round admission cutoff record for a branch and category."""

    __tablename__ = "admission_cutoffs"
    __table_args__ = (
        UniqueConstraint(
            "branch_code",
            "admission_year",
            "cap_round",
            "level",
            "admission_stage",
            "category",
            name="uq_admission_cutoffs_composite",
        ),
        CheckConstraint(
            "percentile >= 0 AND percentile <= 100",
            name="percentile_range",
        ),
        Index(
            "ix_admission_cutoffs_recommender",
            "admission_year",
            "admission_stage",
            "category",
            "branch_code",
        ),
        Index(
            "ix_admission_cutoffs_trends",
            "branch_code",
            "category",
            "admission_stage",
            "admission_year",
            "cap_round",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    branch_code: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("branches.branch_code"),
        nullable=False,
    )
    admission_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    cap_round: Mapped[int] = mapped_column(TINYINT, nullable=False)
    level: Mapped[str] = mapped_column(String(10), nullable=False)
    admission_stage: Mapped[str] = mapped_column(String(5), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    merit_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    percentile: Mapped[float] = mapped_column(Float, nullable=False)

    branch: Mapped["Branch"] = relationship(back_populates="cutoffs")
