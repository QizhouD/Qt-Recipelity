from sqlalchemy import or_, and_
from sqlalchemy.exc import SQLAlchemyError
from .models import session, Recipe, Ingredient, Step, Nutrition, Tag, recipe_tag_association
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecipeManager:
    """食谱管理核心类"""
    
    @staticmethod
    def get_all_recipes():
        """获取所有食谱"""
        try:
            return session.query(Recipe).all()
        except SQLAlchemyError as e:
            logger.error(f"获取食谱失败: {e}")
            return []
    
    @staticmethod
    def get_recipe_by_id(recipe_id):
        """根据ID获取食谱"""
        try:
            return session.query(Recipe).filter_by(id=recipe_id).first()
        except SQLAlchemyError as e:
            logger.error(f"获取食谱失败: {e}")
            return None
    
    @staticmethod
    def search_recipes(keyword=None, tags=None, min_time=None, max_time=None, 
                      min_difficulty=None, max_difficulty=None, cuisine=None):
        """
        搜索食谱
        :param keyword: 关键词
        :param tags: 标签列表
        :param min_time: 最小时间
        :param max_time: 最大时间
        :param min_difficulty: 最小难度
        :param max_difficulty: 最大难度
        :param cuisine: 菜系
        :return: 符合条件的食谱列表
        """
        try:
            query = session.query(Recipe)
            
            # 关键词搜索
            if keyword:
                keyword = f"%{keyword}%"
                query = query.filter(
                    or_(
                        Recipe.name.ilike(keyword),
                        Recipe.description.ilike(keyword),
                        Recipe.ingredients.any(Ingredient.name.ilike(keyword))
                    )
                )
            
            # 标签筛选
            if tags and isinstance(tags, list) and len(tags) > 0:
                query = query.filter(Recipe.tags.any(Tag.name.in_(tags)))
            
            # 时间筛选
            if min_time is not None:
                query = query.filter(Recipe.total_time >= min_time)
            if max_time is not None:
                query = query.filter(Recipe.total_time <= max_time)
            
            # 难度筛选
            if min_difficulty is not None:
                query = query.filter(Recipe.difficulty >= min_difficulty)
            if max_difficulty is not None:
                query = query.filter(Recipe.difficulty <= max_difficulty)
            
            # 菜系筛选
            if cuisine:
                query = query.filter(Recipe.cuisine.ilike(f"%{cuisine}%"))
            
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"搜索食谱失败: {e}")
            return []
    
    @staticmethod
    def add_recipe(recipe_data):
        """
        添加新食谱
        :param recipe_data: 食谱数据字典
        :return: 创建的食谱对象或None
        """
        try:
            # 创建食谱
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
            
            # 添加食材
            ingredients_data = recipe_data.get('ingredients', [])
            for ing_data in ingredients_data:
                ingredient = Ingredient(
                    name=ing_data.get('name'),
                    amount=ing_data.get('amount'),
                    unit=ing_data.get('unit')
                )
                recipe.ingredients.append(ingredient)
            
            # 添加步骤
            steps_data = recipe_data.get('steps', [])
            for step_data in steps_data:
                step = Step(
                    order=step_data.get('order'),
                    description=step_data.get('description')
                )
                recipe.steps.append(step)
            
            # 添加营养信息
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
            
            # 添加标签
            tags_data = recipe_data.get('tags', [])
            for tag_name in tags_data:
                tag = session.query(Tag).filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    session.add(tag)
                recipe.tags.append(tag)
            
            session.add(recipe)
            session.commit()
            logger.info(f"添加食谱成功: {recipe.name}")
            return recipe
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"添加食谱失败: {e}")
            return None
    
    @staticmethod
    def update_recipe(recipe_id, recipe_data):
        """
        更新食谱
        :param recipe_id: 食谱ID
        :param recipe_data: 更新的食谱数据
        :return: 更新后的食谱对象或None
        """
        try:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                logger.warning(f"食谱不存在: {recipe_id}")
                return None
            
            # 更新基本信息
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
            
            # 更新食材
            if 'ingredients' in recipe_data:
                # 清空现有食材
                recipe.ingredients = []
                for ing_data in recipe_data['ingredients']:
                    ingredient = Ingredient(
                        name=ing_data.get('name'),
                        amount=ing_data.get('amount'),
                        unit=ing_data.get('unit')
                    )
                    recipe.ingredients.append(ingredient)
            
            # 更新步骤
            if 'steps' in recipe_data:
                # 清空现有步骤
                recipe.steps = []
                for step_data in recipe_data['steps']:
                    step = Step(
                        order=step_data.get('order'),
                        description=step_data.get('description')
                    )
                    recipe.steps.append(step)
            
            # 更新营养信息
            if 'nutrition' in recipe_data:
                nutrition_data = recipe_data['nutrition']
                if recipe.nutrition:
                    # 更新现有营养信息
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
                    # 创建新的营养信息
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
            
            # 更新标签
            if 'tags' in recipe_data:
                # 清空现有标签
                recipe.tags = []
                for tag_name in recipe_data['tags']:
                    tag = session.query(Tag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        session.add(tag)
                    recipe.tags.append(tag)
            
            recipe.updated_at = datetime.now()
            session.commit()
            logger.info(f"更新食谱成功: {recipe.name}")
            return recipe
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"更新食谱失败: {e}")
            return None
    
    @staticmethod
    def delete_recipe(recipe_id):
        """
        删除食谱
        :param recipe_id: 食谱ID
        :return: 是否成功删除
        """
        try:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                logger.warning(f"食谱不存在: {recipe_id}")
                return False
            
            session.delete(recipe)
            session.commit()
            logger.info(f"删除食谱成功: {recipe.name}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"删除食谱失败: {e}")
            return False
    
    @staticmethod
    def get_all_tags():
        """获取所有标签"""
        try:
            return session.query(Tag).all()
        except SQLAlchemyError as e:
            logger.error(f"获取标签失败: {e}")
            return []
    
    @staticmethod
    def get_cuisines():
        """获取所有菜系"""
        try:
            cuisines = session.query(Recipe.cuisine).distinct().all()
            return [cuisine[0] for cuisine in cuisines if cuisine[0]]
        except SQLAlchemyError as e:
            logger.error(f"获取菜系失败: {e}")
            return []
    
    @staticmethod
    def import_recipe_from_url(url):
        """
        从URL导入食谱
        :param url: 食谱网页URL
        :return: 导入的食谱数据或None
        """
        try:
            # 发送请求
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 根据不同网站的结构解析食谱
            # 这里以一些常见的食谱网站为例，实际应用中需要扩展更多网站的解析规则
            recipe_data = {}
            
            # 解析美食天下
            if 'meishichina.com' in url:
                recipe_data = RecipeManager._parse_meishichina(soup, url)
            # 解析下厨房
            elif 'xiachufang.com' in url:
                recipe_data = RecipeManager._parse_xiachufang(soup, url)
            # 解析豆果美食
            elif 'douguo.com' in url:
                recipe_data = RecipeManager._parse_douguo(soup, url)
            # 其他网站
            else:
                # 通用解析方法
                recipe_data = RecipeManager._parse_generic(soup, url)
            
            if recipe_data:
                # 添加来源URL
                recipe_data['source_url'] = url
                return recipe_data
            else:
                logger.warning(f"无法解析URL: {url}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求URL失败: {e}")
            return None
        except Exception as e:
            logger.error(f"解析食谱失败: {e}")
            return None
    
    @staticmethod
    def _parse_meishichina(soup, url):
        """解析美食天下网站的食谱"""
        recipe_data = {}
        
        # 标题
        title_tag = soup.find('h1', class_='recipe_De_title')
        if title_tag:
            recipe_data['name'] = title_tag.get_text(strip=True)
        
        # 描述
        desc_tag = soup.find('div', class_='recipe_De_desc')
        if desc_tag:
            recipe_data['description'] = desc_tag.get_text(strip=True)
        
        # 时间和难度
        info_tags = soup.find_all('div', class_='recipe_De_info_item')
        for tag in info_tags:
            label = tag.find('span', class_='recipe_De_info_label')
            if label:
                label_text = label.get_text(strip=True)
                value = tag.find('span', class_='recipe_De_info_con').get_text(strip=True)
                
                if '准备时间' in label_text:
                    # 提取数字
                    match = re.search(r'(\d+)', value)
                    if match:
                        recipe_data['prep_time'] = int(match.group(1))
                elif '烹饪时间' in label_text:
                    match = re.search(r'(\d+)', value)
                    if match:
                        recipe_data['cook_time'] = int(match.group(1))
                elif '难度' in label_text:
                    if '简单' in value:
                        recipe_data['difficulty'] = 1
                    elif '中等' in value:
                        recipe_data['difficulty'] = 2
                    elif '一般' in value:
                        recipe_data['difficulty'] = 3
                    elif '较难' in value:
                        recipe_data['difficulty'] = 4
                    elif '困难' in value:
                        recipe_data['difficulty'] = 5
        
        # 菜系
        cuisine_tag = soup.find('a', href=re.compile('/cuisine/'))
        if cuisine_tag:
            recipe_data['cuisine'] = cuisine_tag.get_text(strip=True)
        
        # 图片
        image_tag = soup.find('img', class_='recipe_De_img')
        if image_tag and 'src' in image_tag.attrs:
            recipe_data['image_url'] = urljoin(url, image_tag['src'])
        
        # 食材
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
                    # 尝试解析数量和单位
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
        
        # 步骤
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
        """解析下厨房网站的食谱"""
        recipe_data = {}
        
        # 标题
        title_tag = soup.find('h1', class_='page-title')
        if title_tag:
            recipe_data['name'] = title_tag.get_text(strip=True)
        
        # 描述
        desc_tag = soup.find('div', class_='desc mt30')
        if desc_tag:
            recipe_data['description'] = desc_tag.get_text(strip=True)
        
        # 时间和难度
        info_tags = soup.find_all('div', class_='info-item')
        for tag in info_tags:
            label = tag.find('span', class_='label')
            if label:
                label_text = label.get_text(strip=True)
                value = tag.find('span', class_='value').get_text(strip=True)
                
                if '准备时间' in label_text:
                    match = re.search(r'(\d+)', value)
                    if match:
                        recipe_data['prep_time'] = int(match.group(1))
                elif '烹饪时间' in label_text:
                    match = re.search(r'(\d+)', value)
                    if match:
                        recipe_data['cook_time'] = int(match.group(1))
                elif '难度' in label_text:
                    if '简单' in value:
                        recipe_data['difficulty'] = 1
                    elif '中等' in value:
                        recipe_data['difficulty'] = 2
                    elif '一般' in value:
                        recipe_data['difficulty'] = 3
                    elif '较难' in value:
                        recipe_data['difficulty'] = 4
                    elif '困难' in value:
                        recipe_data['difficulty'] = 5
        
        # 菜系
        cuisine_tag = soup.find('a', href=re.compile('/category/'))
        if cuisine_tag:
            recipe_data['cuisine'] = cuisine_tag.get_text(strip=True)
        
        # 图片
        image_tag = soup.find('img', class_='cover image-lazy-loaded')
        if image_tag and 'src' in image_tag.attrs:
            recipe_data['image_url'] = urljoin(url, image_tag['src'])
        
        # 食材
        ingredients = []
        ingredient_tags = soup.find_all('li', class_='ingredient')
        for tag in ingredient_tags:
            name_tag = tag.find('span', class_='name')
            amount_tag = tag.find('span', class_='amount')
            
            if name_tag:
                name = name_tag.get_text(strip=True)
                amount = ''
                unit = ''
                
                if amount_tag:
                    amount_text = amount_tag.get_text(strip=True)
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
        
        # 步骤
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
        """解析豆果美食网站的食谱"""
        recipe_data = {}
        
        # 标题
        title_tag = soup.find('h1', class_='recipe-title')
        if title_tag:
            recipe_data['name'] = title_tag.get_text(strip=True)
        
        # 描述
        desc_tag = soup.find('div', class_='recipe-description')
        if desc_tag:
            recipe_data['description'] = desc_tag.get_text(strip=True)
        
        # 时间和难度
        info_tags = soup.find_all('div', class_='recipe-info-item')
        for tag in info_tags:
            label = tag.find('span', class_='info-label')
            if label:
                label_text = label.get_text(strip=True)
                value = tag.find('span', class_='info-value').get_text(strip=True)
                
                if '准备时间' in label_text:
                    match = re.search(r'(\d+)', value)
                    if match:
                        recipe_data['prep_time'] = int(match.group(1))
                elif '烹饪时间' in label_text:
                    match = re.search(r'(\d+)', value)
                    if match:
                        recipe_data['cook_time'] = int(match.group(1))
                elif '难度' in label_text:
                    if '简单' in value:
                        recipe_data['difficulty'] = 1
                    elif '中等' in value:
                        recipe_data['difficulty'] = 2
                    elif '一般' in value:
                        recipe_data['difficulty'] = 3
                    elif '较难' in value:
                        recipe_data['difficulty'] = 4
                    elif '困难' in value:
                        recipe_data['difficulty'] = 5
        
        # 菜系
        cuisine_tag = soup.find('a', href=re.compile('/cuisine/'))
        if cuisine_tag:
            recipe_data['cuisine'] = cuisine_tag.get_text(strip=True)
        
        # 图片
        image_tag = soup.find('img', class_='recipe-cover')
        if image_tag and 'src' in image_tag.attrs:
            recipe_data['image_url'] = urljoin(url, image_tag['src'])
        
        # 食材
        ingredients = []
        ingredient_tags = soup.find_all('li', class_='ingredient-item')
        for tag in ingredient_tags:
            name_tag = tag.find('span', class_='ingredient-name')
            amount_tag = tag.find('span', class_='ingredient-amount')
            
            if name_tag:
                name = name_tag.get_text(strip=True)
                amount = ''
                unit = ''
                
                if amount_tag:
                    amount_text = amount_tag.get_text(strip=True)
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
        
        # 步骤
        steps = []
        step_tags = soup.find_all('li', class_='cooking-step')
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
        """通用食谱解析方法"""
        recipe_data = {}
        
        # 尝试获取标题
        title_tags = [
            soup.find('h1'),
            soup.find('h2', class_=re.compile('title|recipe')),
            soup.find('div', class_=re.compile('title|recipe'))
        ]
        
        for tag in title_tags:
            if tag and tag.get_text(strip()):
                recipe_data['name'] = tag.get_text(strip())
                break
        
        # 尝试获取描述
        desc_tags = [
            soup.find('meta', property='og:description'),
            soup.find('div', class_=re.compile('description|intro')),
            soup.find('p', class_=re.compile('description|intro'))
        ]
        
        for tag in desc_tags:
            if tag:
                if tag.name == 'meta' and 'content' in tag.attrs:
                    recipe_data['description'] = tag['content'].strip()
                else:
                    recipe_data['description'] = tag.get_text(strip())
                break
        
        # 尝试获取图片
        image_tags = [
            soup.find('meta', property='og:image'),
            soup.find('img', class_=re.compile('main|cover|recipe')),
            soup.find('img', id=re.compile('main|cover|recipe'))
        ]
        
        for tag in image_tags:
            if tag:
                if tag.name == 'meta' and 'content' in tag.attrs:
                    recipe_data['image_url'] = tag['content'].strip()
                elif 'src' in tag.attrs:
                    recipe_data['image_url'] = urljoin(url, tag['src'])
                break
        
        # 尝试获取食材
        ingredients = []
        # 查找包含"食材"、"用料"等关键词的容器
        ingredient_containers = soup.find_all(['div', 'ul', 'ol'], text=re.compile('食材|用料|材料|配料', re.IGNORECASE))
        
        for container in ingredient_containers:
            # 获取容器内的列表项
            list_items = container.find_next(['ul', 'ol']).find_all('li') if container else []
            
            for item in list_items:
                text = item.get_text(strip())
                if text:
                    ingredients.append({
                        'name': text,
                        'amount': '',
                        'unit': ''
                    })
            
            if ingredients:
                break
        
        if ingredients:
            recipe_data['ingredients'] = ingredients
        
        # 尝试获取步骤
        steps = []
        # 查找包含"步骤"、"做法"等关键词的容器
        step_containers = soup.find_all(['div', 'ul', 'ol'], text=re.compile('步骤|做法|烹饪步骤', re.IGNORECASE))
        
        for container in step_containers:
            # 获取容器内的列表项
            list_items = container.find_next(['ul', 'ol']).find_all('li') if container else []
            
            for i, item in enumerate(list_items, 1):
                text = item.get_text(strip())
                if text:
                    steps.append({
                        'order': i,
                        'description': text
                    })
            
            if steps:
                break
        
        if steps:
            recipe_data['steps'] = steps
        
        return recipe_data


class NutritionAnalyzer:
    """营养分析类"""
    
    @staticmethod
    def analyze_recipe_nutrition(recipe_id):
        """
        分析食谱的营养成分
        :param recipe_id: 食谱ID
        :return: 营养成分数据或None
        """
        try:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                logger.warning(f"食谱不存在: {recipe_id}")
                return None
            
            # 如果已经有营养信息，直接返回
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
            
            # 这里是简化的营养计算逻辑
            # 实际应用中应该使用更复杂的食材营养数据库
            nutrition_data = {
                'calories': 0,
                'protein': 0,
                'fat': 0,
                'carbohydrates': 0,
                'fiber': 0,
                'sugar': 0,
                'sodium': 0
            }
            
            # 简化的食材营养数据库
            food_nutrition_db = {
                '鸡肉': {'calories': 165, 'protein': 20, 'fat': 7.5, 'carbohydrates': 0, 'fiber': 0, 'sugar': 0, 'sodium': 70},
                '牛肉': {'calories': 250, 'protein': 26, 'fat': 17, 'carbohydrates': 0, 'fiber': 0, 'sugar': 0, 'sodium': 60},
                '猪肉': {'calories': 200, 'protein': 17, 'fat': 14, 'carbohydrates': 0, 'fiber': 0, 'sugar': 0, 'sodium': 50},
                '鱼': {'calories': 120, 'protein': 20, 'fat': 3, 'carbohydrates': 0, 'fiber': 0, 'sugar': 0, 'sodium': 40},
                '鸡蛋': {'calories': 155, 'protein': 13, 'fat': 11, 'carbohydrates': 1.1, 'fiber': 0, 'sugar': 1.1, 'sodium': 120},
                '牛奶': {'calories': 42, 'protein': 3.2, 'fat': 1, 'carbohydrates': 5, 'fiber': 0, 'sugar': 5, 'sodium': 40},
                '米饭': {'calories': 130, 'protein': 2.7, 'fat': 0.3, 'carbohydrates': 28, 'fiber': 0.3, 'sugar': 0.1, 'sodium': 1},
                '面条': {'calories': 158, 'protein': 5.5, 'fat': 1.6, 'carbohydrates': 30, 'fiber': 2.5, 'sugar': 0.3, 'sodium': 11},
                '面包': {'calories': 265, 'protein': 9, 'fat': 3.2, 'carbohydrates': 49, 'fiber': 2.7, 'sugar': 5.5, 'sodium': 601},
                '土豆': {'calories': 77, 'protein': 2, 'fat': 0.1, 'carbohydrates': 17, 'fiber': 2.2, 'sugar': 0.8, 'sodium': 6},
                '番茄': {'calories': 18, 'protein': 0.9, 'fat': 0.2, 'carbohydrates': 4, 'fiber': 1.5, 'sugar': 2.6, 'sodium': 5},
                '黄瓜': {'calories': 15, 'protein': 0.7, 'fat': 0.1, 'carbohydrates': 3.6, 'fiber': 0.5, 'sugar': 1.8, 'sodium': 2},
                '生菜': {'calories': 15, 'protein': 1.4, 'fat': 0.2, 'carbohydrates': 2.9, 'fiber': 1.5, 'sugar': 0.9, 'sodium': 32},
                '洋葱': {'calories': 40, 'protein': 1.1, 'fat': 0.1, 'carbohydrates': 9.3, 'fiber': 1.7, 'sugar': 4.7, 'sodium': 4},
                '胡萝卜': {'calories': 41, 'protein': 0.9, 'fat': 0.2, 'carbohydrates': 9.6, 'fiber': 2.8, 'sugar': 4.7, 'sodium': 42},
                '青椒': {'calories': 20, 'protein': 0.9, 'fat': 0.2, 'carbohydrates': 4.6, 'fiber': 1.8, 'sugar': 2.4, 'sodium': 2},
                '红椒': {'calories': 25, 'protein': 1.5, 'fat': 0.3, 'carbohydrates': 5.5, 'fiber': 1.9, 'sugar': 4.2, 'sodium': 3},
                '大蒜': {'calories': 149, 'protein': 6.4, 'fat': 0.5, 'carbohydrates': 33.1, 'fiber': 2.1, 'sugar': 1.0, 'sodium': 17},
                '姜': {'calories': 80, 'protein': 1.8, 'fat': 0.3, 'carbohydrates': 18.6, 'fiber': 2.7, 'sugar': 1.7, 'sodium': 13},
                '橄榄油': {'calories': 884, 'protein': 0, 'fat': 100, 'carbohydrates': 0, 'fiber': 0, 'sugar': 0, 'sodium': 0},
                '盐': {'calories': 0, 'protein': 0, 'fat': 0, 'carbohydrates': 0, 'fiber': 0, 'sugar': 0, 'sodium': 39300},
                '糖': {'calories': 387, 'protein': 0, 'fat': 0, 'carbohydrates': 100, 'fiber': 0, 'sugar': 100, 'sodium': 1},
                '酱油': {'calories': 60, 'protein': 8, 'fat': 0, 'carbohydrates': 5, 'fiber': 0, 'sugar': 3, 'sodium': 5700},
                '醋': {'calories': 11, 'protein': 0.1, 'fat': 0, 'carbohydrates': 2.8, 'fiber': 0, 'sugar': 0.4, 'sodium': 15}
            }
            
            # 计算营养成分
            for ingredient in recipe.ingredients:
                if ingredient.name in food_nutrition_db and ingredient.amount and ingredient.unit:
                    food_data = food_nutrition_db[ingredient.name]
                    
                    # 假设单位是克
                    if ingredient.unit == 'g' or ingredient.unit == '克':
                        weight = ingredient.amount
                    elif ingredient.unit == 'kg' or ingredient.unit == '千克':
                        weight = ingredient.amount * 1000
                    elif ingredient.unit == 'mg' or ingredient.unit == '毫克':
                        weight = ingredient.amount / 1000
                    else:
                        # 其他单位，简化处理
                        weight = ingredient.amount
                    
                    # 计算营养成分（每100克）
                    ratio = weight / 100
                    nutrition_data['calories'] += food_data['calories'] * ratio
                    nutrition_data['protein'] += food_data['protein'] * ratio
                    nutrition_data['fat'] += food_data['fat'] * ratio
                    nutrition_data['carbohydrates'] += food_data['carbohydrates'] * ratio
                    nutrition_data['fiber'] += food_data['fiber'] * ratio
                    nutrition_data['sugar'] += food_data['sugar'] * ratio
                    nutrition_data['sodium'] += food_data['sodium'] * ratio
            
            # 保存营养信息到数据库
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
            logger.error(f"分析营养成分失败: {e}")
            return None


class FoodImageAnalyzer:
    """食物图像分析类"""
    
    @staticmethod
    def analyze_food_image(image_path):
        """
        分析食物图像，识别食材
        :param image_path: 图像路径
        :return: 识别的食材列表或None
        """
        try:
            # 这里是简化的图像分析逻辑
            # 实际应用中应该使用OpenCV进行图像分割和食材识别
            # 由于复杂度限制，这里返回模拟数据
            
            # 模拟食材识别结果
            import random
            common_ingredients = [
                '鸡肉', '牛肉', '猪肉', '鱼', '鸡蛋', '米饭', '面条',
                '土豆', '番茄', '黄瓜', '生菜', '洋葱', '胡萝卜', '青椒'
            ]
            
            # 随机选择3-5种食材
            num_ingredients = random.randint(3, 5)
            recognized_ingredients = random.sample(common_ingredients, num_ingredients)
            
            # 为每种食材生成随机重量
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
            logger.error(f"分析食物图像失败: {e}")
            return None
