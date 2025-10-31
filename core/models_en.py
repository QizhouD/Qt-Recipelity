from sqlalchemy import create_engine, Column, Integer, String, Text, Float, ForeignKey, Table, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

# Database initialization
import os
import sys
from pathlib import Path

# Get project root directory
if getattr(sys, 'frozen', False):
    # Running as bundled executable
    PROJECT_ROOT = Path(sys.executable).parent
else:
    # Running as script
    PROJECT_ROOT = Path(__file__).parent.parent

# Create data directory if it doesn't exist
DATA_DIR = PROJECT_ROOT / 'data'
DATA_DIR.mkdir(exist_ok=True)

# Database path
DB_PATH = DATA_DIR / 'recipes.db'
engine = create_engine(f'sqlite:///{DB_PATH}')
Base = declarative_base()

# Recipe-Tag association table
recipe_tag_association = Table('recipe_tag', Base.metadata,
                               Column('recipe_id', Integer, ForeignKey('recipes.id')),
                               Column('tag_id', Integer, ForeignKey('tags.id'))
                               )


class Recipe(Base):
    """Recipe model"""
    __tablename__ = 'recipes'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    prep_time = Column(Integer)  # Preparation time (minutes)
    cook_time = Column(Integer)  # Cooking time (minutes)
    difficulty = Column(Integer)  # Difficulty (1-5)
    cuisine = Column(String(100))  # Cuisine type
    image_url = Column(String(500))  # Image URL
    source_url = Column(String(500))  # Source URL
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    ingredients = relationship('Ingredient', back_populates='recipe', cascade='all, delete-orphan')
    steps = relationship('Step', back_populates='recipe', cascade='all, delete-orphan')
    nutrition = relationship('Nutrition', back_populates='recipe', uselist=False, cascade='all, delete-orphan')
    tags = relationship('Tag', secondary=recipe_tag_association, back_populates='recipes')

    def __repr__(self):
        return f"<Recipe(name='{self.name}')>"

    @property
    def total_time(self):
        """Total cooking time"""
        return (self.prep_time or 0) + (self.cook_time or 0)

    @property
    def difficulty_str(self):
        """Difficulty level as string"""
        difficulty_map = {1: 'Easy', 2: 'Medium', 3: 'Intermediate', 4: 'Advanced', 5: 'Expert'}
        return difficulty_map.get(self.difficulty, 'Unknown')


class Ingredient(Base):
    """Ingredient model"""
    __tablename__ = 'ingredients'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    amount = Column(Float)
    unit = Column(String(50))
    recipe_id = Column(Integer, ForeignKey('recipes.id'))

    # Relationships
    recipe = relationship('Recipe', back_populates='ingredients')

    def __repr__(self):
        return f"<Ingredient(name='{self.name}', amount={self.amount} {self.unit})>"


class Step(Base):
    """Step model"""
    __tablename__ = 'steps'

    id = Column(Integer, primary_key=True)
    order = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    recipe_id = Column(Integer, ForeignKey('recipes.id'))

    # Relationships
    recipe = relationship('Recipe', back_populates='steps')

    def __repr__(self):
        return f"<Step(order={self.order}, description='{self.description[:20]}...')>"


class Nutrition(Base):
    """Nutrition model"""
    __tablename__ = 'nutrition'

    id = Column(Integer, primary_key=True)
    calories = Column(Float)  # Calories (kcal)
    protein = Column(Float)  # Protein (g)
    fat = Column(Float)  # Fat (g)
    carbohydrates = Column(Float)  # Carbohydrates (g)
    fiber = Column(Float)  # Fiber (g)
    sugar = Column(Float)  # Sugar (g)
    sodium = Column(Float)  # Sodium (mg)
    recipe_id = Column(Integer, ForeignKey('recipes.id'))

    # Relationships
    recipe = relationship('Recipe', back_populates='nutrition')

    def __repr__(self):
        return f"<Nutrition(calories={self.calories}, protein={self.protein})>"


class Tag(Base):
    """Tag model"""
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

    # Relationships
    recipes = relationship('Recipe', secondary=recipe_tag_association, back_populates='tags')

    def __repr__(self):
        return f"<Tag(name='{self.name}')>"


# Create database tables
Base.metadata.create_all(engine)

# Create session
Session = sessionmaker(bind=engine)
session = Session()


# Initialize sample data
def init_sample_data():
    """Initialize sample data"""
    if session.query(Recipe).count() == 0:
        # Create sample tags
        tag1 = Tag(name='Breakfast')
        tag2 = Tag(name='Lunch')
        tag3 = Tag(name='Dinner')
        tag4 = Tag(name='Vegetarian')
        tag5 = Tag(name='Quick')

        session.add_all([tag1, tag2, tag3, tag4, tag5])
        session.commit()

        # Create sample recipe 1
        recipe1 = Recipe(
            name='Vegetable Salad',
            description='Fresh and refreshing vegetable salad, rich in vitamins and fiber',
            prep_time=10,
            cook_time=0,
            difficulty=1,
            cuisine='Western',
            image_url='https://p11-doubao-search-sign.byteimg.com/labis/4c979925e0bae738af10a5245cb28072~tplv-be4g95zd3a-image.jpeg?rk3s=542c0f93&x-expires=1777280728&x-signature=PN8i78n9EsqIvC1FnxFn7QGwqsI%3D'
        )

        # Add ingredients
        recipe1.ingredients = [
            Ingredient(name='Lettuce', amount=100, unit='g'),
            Ingredient(name='Tomato', amount=1, unit='piece'),
            Ingredient(name='Cucumber', amount=1, unit='piece'),
            Ingredient(name='Olive Oil', amount=10, unit='ml'),
            Ingredient(name='Vinegar', amount=5, unit='ml')
        ]

        # Add steps
        recipe1.steps = [
            Step(order=1, description='Wash lettuce and tear into small pieces'),
            Step(order=2, description='Cut tomato and cucumber into small pieces'),
            Step(order=3, description='Mix all ingredients, add olive oil and vinegar, toss well')
        ]

        # Add nutrition information
        recipe1.nutrition = Nutrition(
            calories=120,
            protein=3,
            fat=8,
            carbohydrates=10,
            fiber=4,
            sugar=5,
            sodium=60
        )

        # Add tags
        recipe1.tags = [tag1, tag4, tag5]

        # Create sample recipe 2
        recipe2 = Recipe(
            name='Braised Chicken',
            description='Classic Chinese home-style dish with tender chicken and rich sauce',
            prep_time=15,
            cook_time=30,
            difficulty=3,
            cuisine='Chinese',
            image_url='https://p26-doubao-search-sign.byteimg.com/tos-cn-i-xv4ileqgde/35b7b10f5cd441309afa1c34febf4be4~tplv-be4g95zd3a-image.jpeg?rk3s=542c0f93&x-expires=1777280729&x-signature=HkfK%2BSZzJA0PhK%2Bvp%2BlVExeG4i8%3D'
        )

        # Add ingredients
        recipe2.ingredients = [
            Ingredient(name='Chicken', amount=500, unit='g'),
            Ingredient(name='Green Bell Pepper', amount=1, unit='piece'),
            Ingredient(name='Red Bell Pepper', amount=1, unit='piece'),
            Ingredient(name='Onion', amount=1, unit='piece'),
            Ingredient(name='Ginger', amount=3, unit='slice'),
            Ingredient(name='Garlic', amount=3, unit='clove'),
            Ingredient(name='Light Soy Sauce', amount=20, unit='ml'),
            Ingredient(name='Dark Soy Sauce', amount=5, unit='ml'),
            Ingredient(name='Cooking Wine', amount=15, unit='ml'),
            Ingredient(name='Sugar', amount=5, unit='g'),
            Ingredient(name='Salt', amount=3, unit='g')
        ]

        # Add steps
        recipe2.steps = [
            Step(order=1, description='Cut chicken into pieces, marinate with cooking wine and salt for 10 minutes'),
            Step(order=2, description='Cut bell peppers and onion into pieces, mince ginger and garlic'),
            Step(order=3, description='Heat oil in a pan, sauté ginger and garlic until fragrant'),
            Step(order=4, description='Add chicken and stir-fry until golden on the surface'),
            Step(order=5, description='Add light soy sauce, dark soy sauce, and sugar for seasoning'),
            Step(order=6, description='Add appropriate amount of water to cover the chicken'),
            Step(order=7, description='Bring to a boil, then reduce heat and simmer for 20 minutes'),
            Step(order=8, description='Add bell peppers and onion pieces, continue cooking for 5 minutes'),
            Step(order=9, description='Simmer until sauce thickens, then serve')
        ]

        # Add nutrition information
        recipe2.nutrition = Nutrition(
            calories=350,
            protein=30,
            fat=20,
            carbohydrates=10,
            fiber=2,
            sugar=6,
            sodium=800
        )

        # Add tags
        recipe2.tags = [tag2, tag3]

        session.add_all([recipe1, recipe2])
        session.commit()
        print("Sample data initialization completed")


# Initialize sample data
init_sample_data()
