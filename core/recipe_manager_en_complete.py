from sqlalchemy import or_, and_
from sqlalchemy.exc import SQLAlchemyError
from .models_en import session, Recipe, Ingredient, Step, Nutrition, Tag, recipe_tag_association
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecipeManager:
    """Recipe management core class"""
    
    @staticmethod
    def get_all_recipes():
        """Get all recipes"""
        try:
            return session.query(Recipe).all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get recipes: {e}")
            return []
    
    @staticmethod
    def get_recipe_by_id(recipe_id):
        """Get recipe by ID"""
        try:
            return session.query(Recipe).filter_by(id=recipe_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get recipe: {e}")
            return None
    
    @staticmethod
    def search_recipes(keyword=None, tags=None, min_time=None, max_time=None, 
                      min_difficulty=None, max_difficulty=None, cuisine=None):
        """
        Search recipes
        :param keyword: Search keyword
        :param tags: List of tags
        :param min_time: Minimum time
        :param max_time: Maximum time
        :param min_difficulty: Minimum difficulty
        :param max_difficulty: Maximum difficulty
        :param cuisine: Cuisine type
        :return: List of matching recipes
        """
        try:
            query = session.query(Recipe)
            
            # Keyword search
            if keyword:
                keyword = f"%{keyword}%"
                query = query.filter(
                    or_(
                        Recipe.name.ilike(keyword),
                        Recipe.description.ilike(keyword),
                        Recipe.ingredients.any(Ingredient.name.ilike(keyword))
                    )
                )
            
            # Tag filter
            if tags and isinstance(tags, list) and len(tags) > 0:
                query = query.filter(Recipe.tags.any(Tag.name.in_(tags)))
            
            # Time filter
            if min_time is not None:
                query = query.filter(Recipe.total_time >= min_time)
            if max_time is not None:
                query = query.filter(Recipe.total_time <= max_time)
            
            # Difficulty filter
            if min_difficulty is not None:
                query = query.filter(Recipe.difficulty >= min_difficulty)
            if max_difficulty is not None:
                query = query.filter(Recipe.difficulty <= max_difficulty)
            
            # Cuisine filter
            if cuisine:
                query = query.filter(Recipe.cuisine.ilike(f"%{cuisine}%"))
            
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to search recipes: {e}")
            return []
    
    @staticmethod
    def add_recipe(recipe_data):
        """
        Add new recipe
        :param recipe_data: Recipe data dictionary
        :return: Created recipe object or None
        """
        try:
            # Create recipe
            recipe = Recipe(
                name=recipe_data.get('name'),
                description=recipe_data.get('description'),
                prep_time=recipe_data.get('prep_time'),
                cook_time=recipe_data.get('cook_time'),
                difficulty=recipe_data.get('difficulty'),
                cuisine=recipe_data.get('cuisine'),
                image_url=recipe_data.get('image_url'),
                source_url=recipe_data.get('source_url')
            )
            
            # Add ingredients
            ingredients_data = recipe_data.get('ingredients', [])
            for ing_data in ingredients_data:
                ingredient = Ingredient(
                    name=ing_data.get('name'),
                    amount=ing_data.get('amount'),
                    unit=ing_data.get('unit')
                )
                recipe.ingredients.append(ingredient)
            
            # Add steps
            steps_data = recipe_data.get('steps', [])
            for step_data in steps_data:
                step = Step(
                    order=step_data.get('order'),
                    description=step_data.get('description')
                )
                recipe.steps.append(step)
            
            # Add nutrition information
            nutrition_data = recipe_data.get('nutrition')
            if nutrition_data:
                nutrition = Nutrition(
                    calories=nutrition_data.get('calories'),
                    protein=nutrition_data.get('protein'),
                    fat=nutrition_data.get('fat'),
                    carbohydrates=nutrition_data.get('carbohydrates'),
                    fiber=nutrition_data.get('fiber'),
                    sugar=nutrition_data.get('sugar'),
                    sodium=nutrition_data.get('sodium')
                )
                recipe.nutrition = nutrition
            
            # Add tags
            tags_data = recipe_data.get('tags', [])
            for tag_name in tags_data:
                tag = session.query(Tag).filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    session.add(tag)
                recipe.tags.append(tag)
            
            session.add(recipe)
            session.commit()
            logger.info(f"Recipe added successfully: {recipe.name}")
            return recipe
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to add recipe: {e}")
            return None
    
    @staticmethod
    def update_recipe(recipe_id, recipe_data):
        """
        Update recipe
        :param recipe_id: Recipe ID
        :param recipe_data: Updated recipe data
        :return: Updated recipe object or None
        """
        try:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                logger.warning(f"Recipe not found: {recipe_id}")
                return None
            
            # Update basic information
            if 'name' in recipe_data:
                recipe.name = recipe_data['name']
            if 'description' in recipe_data:
                recipe.description = recipe_data['description']
            if 'prep_time' in recipe_data:
                recipe.prep_time = recipe_data['prep_time']
            if 'cook_time' in recipe_data:
                recipe.cook_time = recipe_data['cook_time']
            if 'difficulty' in recipe_data:
                recipe.difficulty = recipe_data['difficulty']
            if 'cuisine' in recipe_data:
                recipe.cuisine = recipe_data['cuisine']
            if 'image_url' in recipe_data:
                recipe.image_url = recipe_data['image_url']
            if 'source_url' in recipe_data:
                recipe.source_url = recipe_data['source_url']
            
            # Update ingredients
            if 'ingredients' in recipe_data:
                # Clear existing ingredients
                recipe.ingredients = []
                for ing_data in recipe_data['ingredients']:
                    ingredient = Ingredient(
                        name=ing_data.get('name'),
                        amount=ing_data.get('amount'),
                        unit=ing_data.get('unit')
                    )
                    recipe.ingredients.append(ingredient)
            
            # Update steps
            if 'steps' in recipe_data:
                # Clear existing steps
                recipe.steps = []
                for step_data in recipe_data['steps']:
                    step = Step(
                        order=step_data.get('order'),
                        description=step_data.get('description')
                    )
                    recipe.steps.append(step)
            
            # Update nutrition information
            if 'nutrition' in recipe_data:
                nutrition_data = recipe_data['nutrition']
                if recipe.nutrition:
                    # Update existing nutrition information
                    if 'calories' in nutrition_data:
                        recipe.nutrition.calories = nutrition_data['calories']
                    if 'protein' in nutrition_data:
                        recipe.nutrition.protein = nutrition_data['protein']
                    if 'fat' in nutrition_data:
                        recipe.nutrition.fat = nutrition_data['fat']
                    if 'carbohydrates' in nutrition_data:
                        recipe.nutrition.carbohydrates = nutrition_data['carbohydrates']
                    if 'fiber' in nutrition_data:
                        recipe.nutrition.fiber = nutrition_data['fiber']
                    if 'sugar' in nutrition_data:
                        recipe.nutrition.sugar = nutrition_data['sugar']
                    if 'sodium' in nutrition_data:
                        recipe.nutrition.sodium = nutrition_data['sodium']
                else:
                    # Create new nutrition information
                    nutrition = Nutrition(
                        calories=nutrition_data.get('calories'),
                        protein=nutrition_data.get('protein'),
                        fat=nutrition_data.get('fat'),
                        carbohydrates=nutrition_data.get('carbohydrates'),
                        fiber=nutrition_data.get('fiber'),
                        sugar=nutrition_data.get('sugar'),
                        sodium=nutrition_data.get('sodium')
                    )
                    recipe.nutrition = nutrition
            
            # Update tags
            if 'tags' in recipe_data:
                # Clear existing tags
                recipe.tags = []
                for tag_name in recipe_data['tags']:
                    tag = session.query(Tag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        session.add(tag)
                    recipe.tags.append(tag)
            
            recipe.updated_at = datetime.now()
            session.commit()
            logger.info(f"Recipe updated successfully: {recipe.name}")
            return recipe
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to update recipe: {e}")
            return None
    
    @staticmethod
    def delete_recipe(recipe_id):
        """
        Delete recipe
        :param recipe_id: Recipe ID
        :return: Whether deletion was successful
        """
        try:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                logger.warning(f"Recipe not found: {recipe_id}")
                return False
            
            session.delete(recipe)
            session.commit()
            logger.info(f"Recipe deleted successfully: {recipe.name}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to delete recipe: {e}")
            return False
    
    @staticmethod
    def get_all_tags():
        """Get all tags"""
        try:
            return session.query(Tag).all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get tags: {e}")
            return []
    
    @staticmethod
    def get_cuisines():
        """Get all cuisines"""
        try:
            cuisines = session.query(Recipe.cuisine).distinct().all()
            return [cuisine[0] for cuisine in cuisines if cuisine[0]]
        except SQLAlchemyError as e:
            logger.error(f"Failed to get cuisines: {e}")
            return []
    
    @staticmethod
    def import_recipe_from_url(url):
        """
        Import recipe from URL
        :param url: Recipe webpage URL
        :return: Imported recipe data or None
        """
        try:
            # Send request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Parse recipe based on different website structures
            # Here are examples for some common recipe websites
            recipe_data = {}
            
            # Parse Meishichina
            if 'meishichina.com' in url:
                recipe_data = RecipeManager._parse_meishichina(soup, url)
            # Parse Xiachufang
            elif 'xiachufang.com' in url:
                recipe_data = RecipeManager._parse_xiachufang(soup, url)
            # Parse Douguo
            elif 'douguo.com' in url:
                recipe_data = RecipeManager._parse_douguo(soup, url)
            # Other websites
            else:
                # Generic parsing method
                recipe_data = RecipeManager._parse_generic(soup, url)
            
            if recipe_data:
                # Add source URL
                recipe_data['source_url'] = url
                return recipe_data
            else:
                logger.warning(f"Could not parse URL: {url}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to request URL: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse recipe: {e}")
            return None
    
    @staticmethod
    def _parse_meishichina(soup, url):
        """Parse recipe from Meishichina website"""
        recipe_data = {}
        
        # Title
        title_tag = soup.find('h1', class_='recipe_De_title')
        if title_tag:
            recipe_data['name'] = title_tag.get_text(strip=True)
        
        # Description
        desc_tag = soup.find('div', class_='recipe_De_desc')
        if desc_tag:
            recipe_data['description'] = desc_tag.get_text(strip=True)
        
        # Time and difficulty
        info_tags = soup.find_all('div', class_='recipe_De_info_item')
        for tag in info_tags:
            label = tag.find('span', class_='recipe_De_info_label')
            if label:
                label_text = label.get_text(strip=True)
                value = tag.find('span', class_='recipe_De_info_con').get_text(strip=True)
                
                if '准备时间' in label_text:  # Chinese for "Preparation Time"
                    # Extract number
                    match = re.search(r'(\d+)', value)
                    if match:
                        recipe_data['prep_time'] = int(match.group(1))
                elif '烹饪时间' in label_text:  # Chinese for "Cooking Time"
                    match = re.search(r'(\d+)', value)
                    if match:
                        recipe_data['cook_time'] = int(match.group(1))
                elif '难度' in label_text:  # Chinese for "Difficulty"
                    if '简单' in value:  # Chinese for "Easy"
                        recipe_data['difficulty'] = 1
                    elif '中等' in value:  # Chinese for "Medium"
                        recipe_data['difficulty'] = 2
                    elif '一般' in value:  # Chinese for "Intermediate"
                        recipe_data['difficulty'] = 3
                    elif '较难' in value:  # Chinese for "Advanced"
                        recipe_data['difficulty'] = 4
                    elif '困难' in value:  # Chinese for "Expert"
                        recipe_data['difficulty'] = 5
        
        # Cuisine
        cuisine_tag = soup.find('a', href=re.compile('/cuisine/'))
        if cuisine_tag:
            recipe_data['cuisine'] = cuisine_tag.get_text(strip=True)
        
        # Image
        image_tag = soup.find('img', class_='recipe_De_img')
        if image_tag and 'src' in image_tag.attrs:
            recipe_data['image_url'] = urljoin(url, image_tag['src'])
        
        # Ingredients
        ingredients = []
        ingredient_tags = soup.find_all('li', class_='recipe_ingredients_item')
        for tag in ingredient_tags:
            name_tag = tag.find('span', class_='recipe_ingredients_name')
            amount_tag = tag.find('span', class_='recipe_ingredients_unit')
            
            if name_tag:
                name = name_tag.get_text(strip=True)
                amount = ''
                unit = ''
                
                if amount_tag:
                    amount_text = amount_tag.get_text(strip=True)
                    # Try to parse amount and unit
                    match = re.search(r'(\d+\.?\d*)\s*([^\d]+)', amount_text)
                    if match:
                        amount = float(match.group(1))
                        unit = match.group(2).strip()
                    else:
                        amount = amount_text
                
                ingredients.append({
                    'name': name,
                    'amount': amount,
                    'unit': unit
                })
        
        if ingredients:
            recipe_data['ingredients'] = ingredients
        
        # Steps
        steps = []
        step_tags = soup.find_all('li', class_='recipe_step_item')
        for i, tag in enumerate(step_tags, 1):
            desc_tag = tag.find('div', class_='recipe_step_txt')
            if desc_tag:
                steps.append({
                    'order': i,
                    'description': desc_tag.get_text(strip=True)
                })
        
        if steps:
            recipe_data['steps'] = steps
        
        return recipe_data
    
    @staticmethod
    def _parse_xiachufang(soup, url):
        """Parse recipe from Xiachufang website"""
        recipe_data = {}
        
        # Title
        title_tag = soup.find('h1', class_='page-title')
        if title_tag:
            recipe_data['name'] = title_tag.get_text(strip=True)
        
        # Description
        desc_tag = soup.find('div', class_='desc mt30')
        if desc_tag:
            recipe_data['description'] = desc_tag.get_text(strip=True)
        
        # Time and difficulty
        info_tags = soup.find_all('div', class_='info-item')
        for tag in info_tags:
            label = tag.find('span', class_='label')
            if label:
                label_text = label.get_text(strip=True)
                value = tag.find('span', class_='value').get_text(strip=True)
                
                if '准备时间' in label_text:  # Chinese for "Preparation Time"
                    match = re.search(r'(\d+)', value)
                    if match:
                        recipe_data['prep_time'] = int(match.group(1))
                elif '烹饪时间' in label_text:  # Chinese for "Cooking Time"
                    match = re.search(r'(\d+)', value)
                    if match:
                        recipe_data['cook_time'] = int(match.group(1))
                elif '难度' in label_text:  # Chinese for "Difficulty"
                    if '简单' in value:  # Chinese for "Easy"
                        recipe_data['difficulty'] = 1
                    elif '中等' in value:  # Chinese for "Medium"
                        recipe_data['difficulty'] = 2
                    elif '一般' in value:  # Chinese for "Intermediate"
                        recipe_data['difficulty'] = 3
                    elif '较难' in value:  # Chinese for "Advanced"
                        recipe_data['difficulty'] = 4
                    elif '困难' in value:  # Chinese for "Expert"
                        recipe_data['difficulty'] = 5
        
        # Cuisine
        cuisine_tag = soup.find('a', href=re.compile('/category/'))
        if cuisine_tag:
            recipe_data['cuisine'] = cuisine_tag.get_text(strip=True)
        
        # Image
        image_tag = soup.find('img', class_='cover-image')
        if image_tag and 'src' in image_tag.attrs:
            recipe_data['image_url'] = urljoin(url, image_tag['src'])
        
        # Ingredients
        ingredients = []
        ingredient_tags = soup.find_all('li', class_='ingredient')
        for tag in ingredient_tags:
            name_tag = tag.find('span', class_='name')
            amount_tag = tag.find('span', class_='amount')
            
            if name_tag:
                name = name_tag.get_text(strip=True)
                amount = amount_tag.get_text(strip=True) if amount_tag else ''
                
                # Try to parse amount and unit
                amount_val = ''
                unit = ''
                if amount:
                    match = re.search(r'(\d+\.?\d*)\s*([^\d]+)', amount)
                    if match:
                        amount_val = float(match.group(1))
                        unit = match.group(2).strip()
                    else:
                        amount_val = amount
                
                ingredients.append({
                    'name': name,
                    'amount': amount_val,
                    'unit': unit
                })
        
        if ingredients:
            recipe_data['ingredients'] = ingredients
        
        # Steps
        steps = []
        step_tags = soup.find_all('li', class_='step')
        for i, tag in enumerate(step_tags, 1):
            desc_tag = tag.find('p', class_='text')
            if desc_tag:
                steps.append({
                    'order': i,
                    'description': desc_tag.get_text(strip=True)
                })
        
        if steps:
            recipe_data['steps'] = steps
        
        return recipe_data
    
    @staticmethod
    def _parse_douguo(soup, url):
        """Parse recipe from Douguo website"""
        recipe_data = {}
        
        # Title
        title_tag = soup.find('h1', class_='recipe-title')
        if title_tag:
            recipe_data['name'] = title_tag.get_text(strip=True)
        
        # Description
        desc_tag = soup.find('div', class_='recipe-description')
        if desc_tag:
            recipe_data['description'] = desc_tag.get_text(strip=True)
        
        # Time and difficulty
        info_tags = soup.find_all('div', class_='recipe-info-item')
        for tag in info_tags:
            label = tag.find('span', class_='recipe-info-label')
            if label:
                label_text = label.get_text(strip=True)
                value = tag.find('span', class_='recipe-info-value').get_text(strip=True)
                
                if '准备时间' in label_text:  # Chinese for "Preparation Time"
                    match = re.search(r'(\d+)', value)
                    if match:
                        recipe_data['prep_time'] = int(match.group(1))
                elif '烹饪时间' in label_text:  # Chinese for "Cooking Time"
                    match = re.search(r'(\d+)', value)
                    if match:
                        recipe_data['cook_time'] = int(match.group(1))
                elif '难度' in label_text:  # Chinese for "Difficulty"
                    if '简单' in value:  # Chinese for "Easy"
                        recipe_data['difficulty'] = 1
                    elif '中等' in value:  # Chinese for "Medium"
                        recipe_data['difficulty'] = 2
                    elif '一般' in value:  # Chinese for "Intermediate"
                        recipe_data['difficulty'] = 3
                    elif '较难' in value:  # Chinese for "Advanced"
                        recipe_data['difficulty'] = 4
                    elif '困难' in value:  # Chinese for "Expert"
                        recipe_data['difficulty'] = 5
        
        # Cuisine
        cuisine_tag = soup.find('a', href=re.compile('/cuisine/'))
        if cuisine_tag:
            recipe_data['cuisine'] = cuisine_tag.get_text(strip=True)
        
        # Image
        image_tag = soup.find('img', class_='recipe-img')
        if image_tag and 'src' in image_tag.attrs:
            recipe_data['image_url'] = urljoin(url, image_tag['src'])
        
        # Ingredients
        ingredients = []
        ingredient_tags = soup.find_all('li', class_='ingredient-item')
        for tag in ingredient_tags:
            name_tag = tag.find('span', class_='ingredient-name')
            amount_tag = tag.find('span', class_='ingredient-amount')
            
            if name_tag:
                name = name_tag.get_text(strip=True)
                amount = amount_tag.get_text(strip=True) if amount_tag else ''
                
                # Try to parse amount and unit
                amount_val = ''
                unit = ''
                if amount:
                    match = re.search(r'(\d+\.?\d*)\s*([^\d]+)', amount)
                    if match:
                        amount_val = float(match.group(1))
                        unit = match.group(2).strip()
                    else:
                        amount_val = amount
                
                ingredients.append({
                    'name': name,
                    'amount': amount_val,
                    'unit': unit
                })
        
        if ingredients:
            recipe_data['ingredients'] = ingredients
        
        # Steps
        steps = []
        step_tags = soup.find_all('li', class_='step-item')
        for i, tag in enumerate(step_tags, 1):
            desc_tag = tag.find('div', class_='step-description')
            if desc_tag:
                steps.append({
                    'order': i,
                    'description': desc_tag.get_text(strip=True)
                })
        
        if steps:
            recipe_data['steps'] = steps
        
        return recipe_data
    
    @staticmethod
    def _parse_generic(soup, url):
        """Generic recipe parsing method"""
        recipe_data = {}
        
        # Title (try common selectors)
        title_tag = soup.find('h1') or soup.find('h2', class_='title') or soup.find('div', class_='recipe-title')
        if title_tag:
            recipe_data['name'] = title_tag.get_text(strip=True)
        
        # Description (try common selectors)
        desc_tag = soup.find('div', class_='description') or soup.find('div', class_='recipe-description')
        if desc_tag:
            recipe_data['description'] = desc_tag.get_text(strip=True)
        
        # Image (try common selectors)
        image_tag = soup.find('img', class_='recipe-image') or soup.find('img', class_='main-image') or soup.find('meta', property='og:image')
        if image_tag:
            if hasattr(image_tag, 'attrs'):
                if 'src' in image_tag.attrs:
                    recipe_data['image_url'] = urljoin(url, image_tag['src'])
                elif 'content' in image_tag.attrs:
                    recipe_data['image_url'] = image_tag['content']
        
        # Ingredients (try common selectors)
        ingredients = []
        ingredient_containers = soup.find_all(['ul', 'div'], class_=re.compile('ingredient|材料|食材', re.IGNORECASE))
        
        for container in ingredient_containers:
            ingredient_tags = container.find_all('li')
            for tag in ingredient_tags:
                text = tag.get_text(strip=True)
                if text and len(text) < 100:  # Filter out too long texts
                    ingredients.append({
                        'name': text,
                        'amount': '',
                        'unit': ''
                    })
        
        if ingredients:
            recipe_data['ingredients'] = ingredients
        
        # Steps (try common selectors)
        steps = []
        step_containers = soup.find_all(['ol', 'ul', 'div'], class_=re.compile('step|步骤', re.IGNORECASE))
        
        for container in step_containers:
            step_tags = container.find_all('li')
            for i, tag in enumerate(step_tags, 1):
                text = tag.get_text(strip=True)
                if text and len(text) < 500:  # Filter out too long texts
                    steps.append({
                        'order': i,
                        'description': text
                    })
        
        if steps:
            recipe_data['steps'] = steps
        
        return recipe_data


class NutritionAnalyzer:
    """Nutrition analysis class"""
    
    @staticmethod
    def analyze_recipe_nutrition(recipe_id):
        """
        Analyze recipe nutrition
        :param recipe_id: Recipe ID
        :return: Nutrition data or None
        """
        try:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                logger.warning(f"Recipe not found: {recipe_id}")
                return None
            
            # If nutrition information already exists, return it directly
            if recipe.nutrition:
                return {
                    'calories': recipe.nutrition.calories,
                    'protein': recipe.nutrition.protein,
                    'fat': recipe.nutrition.fat,
                    'carbohydrates': recipe.nutrition.carbohydrates,
                    'fiber': recipe.nutrition.fiber,
                    'sugar': recipe.nutrition.sugar,
                    'sodium': recipe.nutrition.sodium
                }
            
            # Simplified nutrition calculation logic
            # In a real application, a more complex food nutrition database should be used
            nutrition_data = {
                'calories': 0,
                'protein': 0,
                'fat': 0,
                'carbohydrates': 0,
                'fiber': 0,
                'sugar': 0,
                'sodium': 0
            }
            
            # Simplified food nutrition database
            food_nutrition_db = {
                'Chicken': {'calories': 165, 'protein': 20, 'fat': 7.5, 'carbohydrates': 0, 'fiber': 0, 'sugar': 0, 'sodium': 70},
                'Beef': {'calories': 250, 'protein': 26, 'fat': 17, 'carbohydrates': 0, 'fiber': 0, 'sugar': 0, 'sodium': 60},
                'Pork': {'calories': 200, 'protein': 17, 'fat': 14, 'carbohydrates': 0, 'fiber': 0, 'sugar': 0, 'sodium': 50},
                'Fish': {'calories': 120, 'protein': 20, 'fat': 3, 'carbohydrates': 0, 'fiber': 0, 'sugar': 0, 'sodium': 40},
                'Egg': {'calories': 155, 'protein': 13, 'fat': 11, 'carbohydrates': 1.1, 'fiber': 0, 'sugar': 1.1, 'sodium': 120},
                'Milk': {'calories': 42, 'protein': 3.2, 'fat': 1, 'carbohydrates': 5, 'fiber': 0, 'sugar': 5, 'sodium': 40},
                'Rice': {'calories': 130, 'protein': 2.7, 'fat': 0.3, 'carbohydrates': 28, 'fiber': 0.3, 'sugar': 0.1, 'sodium': 1},
                'Noodles': {'calories': 158, 'protein': 5.5, 'fat': 1.6, 'carbohydrates': 30, 'fiber': 2.5, 'sugar': 0.3, 'sodium': 11},
                'Bread': {'calories': 265, 'protein': 9, 'fat': 3.2, 'carbohydrates': 49, 'fiber': 2.7, 'sugar': 5.5, 'sodium': 601},
                'Potato': {'calories': 77, 'protein': 2, 'fat': 0.1, 'carbohydrates': 17, 'fiber': 2.2, 'sugar': 0.8, 'sodium': 6},
                'Tomato': {'calories': 18, 'protein': 0.9, 'fat': 0.2, 'carbohydrates': 4, 'fiber': 1.5, 'sugar': 2.6, 'sodium': 5},
                'Cucumber': {'calories': 15, 'protein': 0.7, 'fat': 0.1, 'carbohydrates': 3.6, 'fiber': 0.5, 'sugar': 1.8, 'sodium': 2},
                'Lettuce': {'calories': 15, 'protein': 1.4, 'fat': 0.2, 'carbohydrates': 2.9, 'fiber': 1.5, 'sugar': 0.9, 'sodium': 32},
                'Onion': {'calories': 40, 'protein': 1.1, 'fat': 0.1, 'carbohydrates': 9.3, 'fiber': 1.7, 'sugar': 4.7, 'sodium': 4},
                'Carrot': {'calories': 41, 'protein': 0.9, 'fat': 0.2, 'carbohydrates': 9.6, 'fiber': 2.8, 'sugar': 4.7, 'sodium': 42},
                'Green Bell Pepper': {'calories': 20, 'protein': 0.9, 'fat': 0.2, 'carbohydrates': 4.6, 'fiber': 1.8, 'sugar': 2.4, 'sodium': 2},
                'Red Bell Pepper': {'calories': 25, 'protein': 1.5, 'fat': 0.3, 'carbohydrates': 5.5, 'fiber': 1.9, 'sugar': 4.2, 'sodium': 3},
                'Garlic': {'calories': 149, 'protein': 6.4, 'fat': 0.5, 'carbohydrates': 33.1, 'fiber': 2.1, 'sugar': 1.0, 'sodium': 17},
                'Ginger': {'calories': 80, 'protein': 1.8, 'fat': 0.3, 'carbohydrates': 18.6, 'fiber': 2.7, 'sugar': 1.7, 'sodium': 13},
                'Olive Oil': {'calories': 884, 'protein': 0, 'fat': 100, 'carbohydrates': 0, 'fiber': 0, 'sugar': 0, 'sodium': 0},
                'Salt': {'calories': 0, 'protein': 0, 'fat': 0, 'carbohydrates': 0, 'fiber': 0, 'sugar': 0, 'sodium': 39300},
                'Sugar': {'calories': 387, 'protein': 0, 'fat': 0, 'carbohydrates': 100, 'fiber': 0, 'sugar': 100, 'sodium': 1},
                'Soy Sauce': {'calories': 60, 'protein': 8, 'fat': 0, 'carbohydrates': 5, 'fiber': 0, 'sugar': 3, 'sodium': 5700},
                'Vinegar': {'calories': 11, 'protein': 0.1, 'fat': 0, 'carbohydrates': 2.8, 'fiber': 0, 'sugar': 0.4, 'sodium': 15}
            }
            
            # Calculate nutrition
            for ingredient in recipe.ingredients:
                if ingredient.name in food_nutrition_db and ingredient.amount and ingredient.unit:
                    food_data = food_nutrition_db[ingredient.name]
                    
                    # Assume unit is grams
                    if ingredient.unit == 'g':
                        weight = ingredient.amount
                    elif ingredient.unit == 'kg':
                        weight = ingredient.amount * 1000
                    elif ingredient.unit == 'mg':
                        weight = ingredient.amount / 1000
                    else:
                        # Other units, simplified processing
                        weight = ingredient.amount
                    
                    # Calculate nutrition (per 100g)
                    ratio = weight / 100
                    nutrition_data['calories'] += food_data['calories'] * ratio
                    nutrition_data['protein'] += food_data['protein'] * ratio
                    nutrition_data['fat'] += food_data['fat'] * ratio
                    nutrition_data['carbohydrates'] += food_data['carbohydrates'] * ratio
                    nutrition_data['fiber'] += food_data['fiber'] * ratio
                    nutrition_data['sugar'] += food_data['sugar'] * ratio
                    nutrition_data['sodium'] += food_data['sodium'] * ratio
            
            # Save nutrition information to database
            if not recipe.nutrition:
                nutrition = Nutrition(
                    calories=round(nutrition_data['calories'], 1),
                    protein=round(nutrition_data['protein'], 1),
                    fat=round(nutrition_data['fat'], 1),
                    carbohydrates=round(nutrition_data['carbohydrates'], 1),
                    fiber=round(nutrition_data['fiber'], 1),
                    sugar=round(nutrition_data['sugar'], 1),
                    sodium=round(nutrition_data['sodium'], 1)
                )
                recipe.nutrition = nutrition
                session.commit()
            
            return nutrition_data
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to analyze nutrition: {e}")
            return None


class FoodImageAnalyzer:
    """Food image analysis class"""
    
    @staticmethod
    def analyze_food_image(image_path):
        """
        Analyze food image to identify ingredients
        :param image_path: Image path
        :return: List of recognized ingredients or None
        """
        try:
            # Simplified image analysis logic
            # In a real application, OpenCV should be used for image segmentation and ingredient recognition
            # Due to complexity constraints, simulated data is returned here
            
            # Simulated ingredient recognition results
            import random
            common_ingredients = [
                'Chicken', 'Beef', 'Pork', 'Fish', 'Egg', 'Rice', 'Noodles',
                'Potato', 'Tomato', 'Cucumber', 'Lettuce', 'Onion', 'Carrot', 'Green Bell Pepper'
            ]
            
            # Randomly select 3-5 ingredients
            num_ingredients = random.randint(3, 5)
            recognized_ingredients = random.sample(common_ingredients, num_ingredients)
            
            # Generate random weights for each ingredient
            result = []
            for ingredient in recognized_ingredients:
                weight = round(random.uniform(50, 300), 1)
                result.append({
                    'name': ingredient,
                    'amount': weight,
                    'unit': 'g',
                    'confidence': round(random.uniform(0.7, 0.95), 2)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze food image: {e}")
            return None
