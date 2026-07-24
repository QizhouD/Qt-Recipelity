"""SQLAlchemy ORM models — unified, language-agnostic schema.

Display text (difficulty labels, cuisine names) is handled by the frontend i18n layer.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, relationship

from app.db.session import Base

# ── association table ────────────────────────────────────────────────────────

recipe_tag = Table(
    "recipe_tag",
    Base.metadata,
    Column("recipe_id", Integer, ForeignKey("recipes.id", ondelete="CASCADE")),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE")),
)

# ── models ───────────────────────────────────────────────────────────────────


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(200), nullable=False)
    description: Mapped[str | None] = Column(Text)
    prep_time: Mapped[int | None] = Column(Integer)  # minutes
    cook_time: Mapped[int | None] = Column(Integer)  # minutes
    difficulty: Mapped[int | None] = Column(Integer)  # 1-5
    cuisine: Mapped[str | None] = Column(String(100))
    image_url: Mapped[str | None] = Column(String(500))
    source_url: Mapped[str | None] = Column(String(500))
    created_at: Mapped[datetime] = Column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = Column(DateTime, default=func.now(), onupdate=func.now())

    # relationships
    ingredients: Mapped[list[Ingredient]] = relationship(
        "Ingredient", back_populates="recipe", cascade="all, delete-orphan"
    )
    steps: Mapped[list[Step]] = relationship(
        "Step", back_populates="recipe", cascade="all, delete-orphan", order_by="Step.order"
    )
    nutrition: Mapped[Nutrition | None] = relationship(
        "Nutrition", back_populates="recipe", uselist=False, cascade="all, delete-orphan"
    )
    tags: Mapped[list[Tag]] = relationship(
        "Tag", secondary=recipe_tag, back_populates="recipes"
    )

    @hybrid_property
    def total_time(self) -> int:
        """Total time in minutes (prep + cook). Safe for SQL filtering."""
        return (self.prep_time or 0) + (self.cook_time or 0)

    @total_time.expression  # type: ignore[no-redef]  # noqa: N805
    def total_time(cls):
        return func.coalesce(cls.prep_time, 0) + func.coalesce(cls.cook_time, 0)


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(100), nullable=False, index=True)
    amount: Mapped[float | None] = Column(Float)
    unit: Mapped[str | None] = Column(String(50))
    recipe_id: Mapped[int] = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"))

    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="ingredients")


class Step(Base):
    __tablename__ = "steps"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    order: Mapped[int] = Column(Integer, nullable=False)
    description: Mapped[str] = Column(Text, nullable=False)
    recipe_id: Mapped[int] = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"))

    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="steps")


class Nutrition(Base):
    __tablename__ = "nutrition"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    calories: Mapped[float | None] = Column(Float)
    protein: Mapped[float | None] = Column(Float)
    fat: Mapped[float | None] = Column(Float)
    carbohydrates: Mapped[float | None] = Column(Float)
    fiber: Mapped[float | None] = Column(Float)
    sugar: Mapped[float | None] = Column(Float)
    sodium: Mapped[float | None] = Column(Float)
    # audit fields
    source: Mapped[str | None] = Column(String(100), default="manual")
    calculated_at: Mapped[datetime | None] = Column(DateTime)
    recipe_id: Mapped[int] = Column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), unique=True
    )

    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="nutrition")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(50), unique=True, nullable=False, index=True)

    recipes: Mapped[list[Recipe]] = relationship(
        "Recipe", secondary=recipe_tag, back_populates="tags"
    )
