from sqlalchemy import create_engine, Column, Integer, String, Text, Float, ForeignKey, Table, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 数据库初始化
def get_database_path():
    """获取数据库文件的绝对路径"""
    try:
        # 获取当前文件的绝对路径
        current_dir = os.path.path.dirname.abspath(os.path.dirname(__file__))
        logger.info(f"当前文件目录: {current_dir}")

        # 项目根目录
        project_root = os.path.abdir(current_dir, '..')
        project_root = os.path.abspath(project_root)
        logger.info(f"项目根目录: {project_root}")

        # 数据目录
        data_dir = os.path.join(project_root, 'data')
        logger.info(f"数据目录: {data_dir}")

        # 创建数据目录（如果不存在）
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            logger.info(f"创建数据目录: {data_dir}")

        # 数据库文件路径
        db_path = os.path.join(data_dir, 'recipes.db')
        db_path = os.path.abspath(db_path)
        logger.info(f"数据库文件路径: {db_path}")

        return db_path
    except Exception as e:
        logger.error(f"获取数据库路径失败: {e}")
        # 如果获取失败，使用当前目录下的数据库文件
        fallback_path = os.path.abspath('recipes_fallback.db')
        logger.warning(f"使用 fallback 数据库路径: {fallback_path}")
        return fallback_path


# 获取数据库路径
DB_PATH = get_database_path()

# 创建数据库引擎
try:
    engine = create_engine(f'sqlite:///{DB_PATH}')
    logger.info(f"数据库引擎创建成功: sqlite:///{DB_PATH}")
except Exception as e:
    logger.error(f"数据库引擎创建失败: {e}")
    # 尝试使用内存数据库作为最后的 fallback
    engine = create_engine('sqlite:///:memory:')
    logger.warning("使用内存数据库作为 fallback")

Base = declarative_base()

# 食谱-标签关联表
recipe_tag_association = Table('recipe_tag', Base.metadata,
                               Column('recipe_id', Integer, ForeignKey('recipes.id')),
                               Column('tag_id', Integer, ForeignKey('tags.id'))
                               )


class Recipe(Base):
    """食谱模型"""
    __tablename__ = 'recipes'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    prep_time = Column(Integer)  # 准备时间(分钟)
    cook_time = Column(Integer)  # 烹饪时间(分钟)
    difficulty = Column(Integer)  # 难度(1-5)
    cuisine = Column(String(100))  # 菜系
    image_url = Column(String(500))  # 图片链接
    source_url = Column(String(500))  # 来源链接
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    ingredients = relationship('Ingredient', back_populates='recipe', cascade='all, delete-orphan')
    steps = relationship('Step', back_populates='recipe', cascade='all, delete-orphan')
    nutrition = relationship('Nutrition', back_populates='recipe', uselist=False, cascade='all, delete-orphan')
    tags = relationship('Tag', secondary=recipe_tag_association, back_populates='recipes')

    def __repr__(self):
        return f"<Recipe(name='{self.name}')>"

    @property
    def total_time(self):
        """总烹饪时间"""
        return (self.prep_time or 0) + (self.cook_time or 0)

    @property
    def difficulty_str(self):
        """难度字符串表示"""
        difficulty_map = {1: '简单', 2: '中等', 3: '一般', 4: '较难', 5: '困难'}
        return difficulty_map.get(self.difficulty, '未知')


class Ingredient(Base):
    """食材模型"""
    __tablename__ = 'ingredients'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    amount = Column(Float)
    unit = Column(String(50))
    recipe_id = Column(Integer, ForeignKey('recipes.id'))

    # 关联
    recipe = relationship('Recipe', back_populates='ingredients')

    def __repr__(self):
        return f"<Ingredient(name='{self.name}', amount={self.amount} {self.unit})>"


class Step(Base):
    """步骤模型"""
    __tablename__ = 'steps'

    id = Column(Integer, primary_key=True)
    order = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    recipe_id = Column(Integer, ForeignKey('recipes.id'))

    # 关联
    recipe = relationship('Recipe', back_populates='steps')

    def __repr__(self):
        return f"<Step(order={self.order}, description='{self.description[:20]}...')>"


class Nutrition(Base):
    """营养成分模型"""
    __tablename__ = 'nutrition'

    id = Column(Integer, primary_key=True)
    calories = Column(Float)  # 热量(kcal)
    protein = Column(Float)  # 蛋白质(g)
    fat = Column(Float)  # 脂肪(g)
    carbohydrates = Column(Float)  # 碳水化合物(g)
    fiber = Column(Float)  # 纤维(g)
    sugar = Column(Float)  # 糖(g)
    sodium = Column(Float)  # 钠(mg)
    recipe_id = Column(Integer, ForeignKey('recipes.id'))

    # 关联
    recipe = relationship('Recipe', back_populates='nutrition')

    def __repr__(self):
        return f"<Nutrition(calories={self.calories}, protein={self.protein})>"


class Tag(Base):
    """标签模型"""
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

    # 关联
    recipes = relationship('Recipe', secondary=recipe_tag_association, back_populates='tags')

    def __repr__(self):
        return f"<Tag(name='{self.name}')>"


# 创建数据库表
try:
    Base.metadata.create_all(engine)
    logger.info("数据库表创建成功")
except Exception as e:
    logger.error(f"数据库表创建失败: {e}")

# 创建会话
try:
    Session = sessionmaker(bind=engine)
    session = Session()
    logger.info("数据库会话创建成功")
except Exception as e:
    logger.error(f"数据库会话创建失败: {e}")
    session = None


# 初始化示例数据
def init_sample_data():
    """初始化示例数据"""
    try:
        if session is None:
            logger.error("数据库会话未初始化，无法初始化示例数据")
            return

        if session.query(Recipe).count() == 0:
            logger.info("初始化示例数据...")

            # 创建示例标签 - 修复了语法错误
            tag1 = Tag(name='早餐')
            tag2 = Tag(name='午餐')  # 修复：添加了右括号
            tag3 = Tag(name='晚餐')
            tag4 = Tag(name='素食')
            tag5 = Tag(name='快速')

            session.add_all([tag1, tag2, tag3, tag4, tag5])
            session.commit()

            # 创建示例食谱1
            recipe1 = Recipe(
                name='蔬菜沙拉',
                description='清新爽口的蔬菜沙拉，富含维生素和纤维',
                prep_time=10,
                cook_time=0,
                difficulty=1,
                cuisine='西式',
                image_url='https://p11-doubao-search-sign.byteimg.com/labis/4c979925e0bae738af10a5245cb28072~tplv-be4g95zd3a-image.jpeg?rk3s=542c0f93&x-expires=1777280728&x-signature=PN8i78n9EsqIvC1FnxFn7QGwqsI%3D'
            )

            # 添加食材
            recipe1.ingredients = [
                Ingredient(name='生菜', amount=100, unit='g'),
                Ingredient(name='番茄', amount=1, unit='个'),
                Ingredient(name='黄瓜', amount=1, unit='根'),
                Ingredient(name='橄榄油', amount=10, unit='ml'),
                Ingredient(name='醋', amount=5, unit='ml')
            ]

            # 添加步骤
            recipe1.steps = [
                Step(order=1, description='将生菜洗净撕成小块'),
                Step(order=2, description='番茄和黄瓜切成小块'),
                Step(order=3, description='将所有食材混合，加入橄榄油和醋拌匀')
            ]

            # 添加营养信息
            recipe1.nutrition = Nutrition(
                calories=120,
                protein=3,
                fat=8,
                carbohydrates=10,
                fiber=4,
                sugar=5,
                sodium=60
            )

            # 添加标签
            recipe1.tags = [tag1, tag4, tag5]

            # 创建示例食谱2
            recipe2 = Recipe(
                name='黄焖鸡',
                description='经典中式家常菜，鸡肉鲜嫩，汤汁浓郁',
                prep_time=15,
                cook_time=30,
                difficulty=3,
                cuisine='中式',
                image_url='https://p26-doubao-search-sign.byteimg.com/tos-cn-i-xv4ileqgde/35b7b10f5cd441309afa1c34febf4be4~tplv-be4g95zd3a-image.jpeg?rk3s=542c0f93&x-expires=1777280729&x-signature=HkfK%2BSZzJA0PhK%2Bvp%2BlVExeG4i8%3D'
            )

            # 添加食材
            recipe2.ingredients = [
                Ingredient(name='鸡肉', amount=500, unit='g'),
                Ingredient(name='青椒', amount=1, unit='个'),
                Ingredient(name='红椒', amount=1, unit='个'),
                Ingredient(name='洋葱', amount=1, unit='个'),
                Ingredient(name='姜', amount=3, unit='片'),
                Ingredient(name='蒜', amount=3, unit='瓣'),
                Ingredient(name='生抽', amount=20, unit='ml'),
                Ingredient(name='老抽', amount=5, unit='ml'),
                Ingredient(name='料酒', amount=15, unit='ml'),
                Ingredient(name='糖', amount=5, unit='g'),
                Ingredient(name='盐', amount=3, unit='g')
            ]

            # 添加步骤
            recipe2.steps = [
                Step(order=1, description='鸡肉切成块，用料酒和盐腌制10分钟'),
                Step(order=2, description='青红椒和洋葱切成块，姜蒜切末'),
                Step(order=3, description='锅中放油，爆香姜蒜'),
                Step(order=4, description='加入鸡肉煸炒至表面金黄'),
                Step(order=5, description='加入生抽、老抽、糖调味'),
                Step(order=6, description='加入适量清水，没过鸡肉'),
                Step(order=7, description='大火烧开后转小火焖煮20分钟'),
                Step(order=8, description='加入青红椒和洋葱块，继续煮5分钟'),
                Step(order=9, description='收汁后即可出锅')
            ]

            # 添加营养信息
            recipe2.nutrition = Nutrition(
                calories=350,
                protein=30,
                fat=20,
                carbohydrates=10,
                fiber=2,
                sugar=6,
                sodium=800
            )

            # 添加标签
            recipe2.tags = [tag2, tag3]

            session.add_all([recipe1, recipe2])
            session.commit()
            logger.info("示例数据初始化完成")
        else:
            logger.info("数据库已包含数据，跳过示例数据初始化")
    except Exception as e:
        logger.error(f"初始化示例数据失败: {e}")
        if session:
            session.rollback()


# 初始化示例数据
if session:
    init_sample_data()
else:
    logger.error("无法初始化示例数据，数据库会话未创建")
