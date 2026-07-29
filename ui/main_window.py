import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QListWidget, QListWidgetItem, QLabel, QPushButton, QLineEdit,
                             QTextEdit, QSpinBox, QComboBox, QCheckBox, QGroupBox, QFormLayout,
                             QScrollArea, QMessageBox, QFileDialog, QProgressDialog, QDialog)
from PyQt6.QtGui import QPixmap, QImage, QIcon, QFont, QColor
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import requests
from io import BytesIO
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from core.recipe_manager import RecipeManager, NutritionAnalyzer, FoodImageAnalyzer
from core.models import session, Recipe, Tag

class ImageDownloader(QThread):
    """图片下载线程"""
    image_downloaded = pyqtSignal(QImage, str)  # (image, url)
    download_failed = pyqtSignal(str)  # (url)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
    
    def run(self):
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            
            image_data = BytesIO(response.content)
            image = QImage()
            image.loadFromData(image_data.getvalue())
            
            self.image_downloaded.emit(image, self.url)
        except Exception as e:
            self.download_failed.emit(self.url)

class NutritionAnalysisThread(QThread):
    """营养分析线程"""
    analysis_progress = pyqtSignal(int, str)  # (progress, message)
    analysis_finished = pyqtSignal(dict)  # (nutrition_data)
    analysis_failed = pyqtSignal(str)  # (error_message)
    
    def __init__(self, recipe_id):
        super().__init__()
        self.recipe_id = recipe_id
    
    def run(self):
        try:
            self.analysis_progress.emit(30, "正在获取食谱信息...")
            nutrition_data = NutritionAnalyzer.analyze_recipe_nutrition(self.recipe_id)
            
            if nutrition_data:
                self.analysis_progress.emit(100, "营养分析完成")
                self.analysis_finished.emit(nutrition_data)
            else:
                self.analysis_failed.emit("无法分析该食谱的营养成分")
        except Exception as e:
            self.analysis_failed.emit(f"分析失败: {str(e)}")

class FoodImageAnalysisThread(QThread):
    """食物图像分析线程"""
    analysis_progress = pyqtSignal(int, str)  # (progress, message)
    analysis_finished = pyqtSignal(list)  # (ingredients_list)
    analysis_failed = pyqtSignal(str)  # (error_message)
    
    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
    
    def run(self):
        try:
            self.analysis_progress.emit(30, "正在分析图像...")
            ingredients = FoodImageAnalyzer.analyze_food_image(self.image_path)
            
            if ingredients:
                self.analysis_progress.emit(100, "图像分析完成")
                self.analysis_finished.emit(ingredients)
            else:
                self.analysis_failed.emit("无法分析该图像中的食材")
        except Exception as e:
            self.analysis_failed.emit(f"分析失败: {str(e)}")

class NutritionChartWidget(QWidget):
    """营养成分图表"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.figure, self.ax = plt.subplots(figsize=(5, 4))
        self.canvas = FigureCanvas(self.figure)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
    
    def update_chart(self, nutrition_data):
        """更新营养成分图表"""
        self.ax.clear()
        
        if not nutrition_data:
            self.canvas.draw()
            return
        
        # 准备数据
        labels = ['蛋白质(g)', '脂肪(g)', '碳水化合物(g)', '纤维(g)', '糖(g)']
        values = [
            nutrition_data.get('protein', 0),
            nutrition_data.get('fat', 0),
            nutrition_data.get('carbohydrates', 0),
            nutrition_data.get('fiber', 0),
            nutrition_data.get('sugar', 0)
        ]
        
        # 设置颜色
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']
        
        # 创建柱状图
        bars = self.ax.bar(labels, values, color=colors)
        
        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            self.ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{height:.1f}', ha='center', va='bottom')
        
        # 设置标题和标签
        self.ax.set_title('营养成分分析', fontsize=14, fontweight='bold')
        self.ax.set_ylabel('克数', fontsize=12)
        
        # 设置网格
        self.ax.yaxis.grid(True, linestyle='--', alpha=0.7)
        
        # 调整布局
        self.figure.tight_layout()
        
        # 更新图表
        self.canvas.draw()

class RecipeDetailWidget(QWidget):
    """食谱详情面板"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.recipe_id = None
        self.image_cache = {}  # 缓存下载的图片
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题
        self.title_label = QLabel()
        self.title_label.setFont(QFont('Arial', 20, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        # 图片
        self.image_label = QLabel()
        self.image_label.setFixedSize(300, 200)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #ddd; border-radius: 5px;")
        layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 基本信息
        info_layout = QHBoxLayout()
        
        # 时间和难度
        time_diff_layout = QVBoxLayout()
        
        self.prep_time_label = QLabel()
        self.cook_time_label = QLabel()
        self.total_time_label = QLabel()
        self.difficulty_label = QLabel()
        
        time_diff_layout.addWidget(self.prep_time_label)
        time_diff_layout.addWidget(self.cook_time_label)
        time_diff_layout.addWidget(self.total_time_label)
        time_diff_layout.addWidget(self.difficulty_label)
        
        # 菜系和标签
        cuisine_tags_layout = QVBoxLayout()
        
        self.cuisine_label = QLabel()
        self.tags_label = QLabel()
        
        cuisine_tags_layout.addWidget(self.cuisine_label)
        cuisine_tags_layout.addWidget(self.tags_label)
        
        info_layout.addLayout(time_diff_layout)
        info_layout.addLayout(cuisine_tags_layout)
        
        layout.addLayout(info_layout)
        
        # 描述
        self.desc_group = QGroupBox("描述")
        self.desc_text = QTextEdit()
        self.desc_text.setReadOnly(True)
        self.desc_text.setStyleSheet("background-color: #f9f9f9;")
        
        desc_layout = QVBoxLayout()
        desc_layout.addWidget(self.desc_text)
        self.desc_group.setLayout(desc_layout)
        layout.addWidget(self.desc_group)
        
        # 食材
        self.ingredients_group = QGroupBox("食材")
        self.ingredients_text = QTextEdit()
        self.ingredients_text.setReadOnly(True)
        self.ingredients_text.setStyleSheet("background-color: #f9f9f9;")
        
        ingredients_layout = QVBoxLayout()
        ingredients_layout.addWidget(self.ingredients_text)
        self.ingredients_group.setLayout(ingredients_layout)
        layout.addWidget(self.ingredients_group)
        
        # 步骤
        self.steps_group = QGroupBox("烹饪步骤")
        self.steps_text = QTextEdit()
        self.steps_text.setReadOnly(True)
        self.steps_text.setStyleSheet("background-color: #f9f9f9;")
        
        steps_layout = QVBoxLayout()
        steps_layout.addWidget(self.steps_text)
        self.steps_group.setLayout(steps_layout)
        layout.addWidget(self.steps_group)
        
        # 营养分析
        self.nutrition_group = QGroupBox("营养分析")
        self.nutrition_chart = NutritionChartWidget()
        
        nutrition_layout = QVBoxLayout()
        nutrition_layout.addWidget(self.nutrition_chart)
        self.nutrition_group.setLayout(nutrition_layout)
        layout.addWidget(self.nutrition_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("分析营养成分")
        self.analyze_btn.clicked.connect(self.on_analyze_clicked)
        button_layout.addWidget(self.analyze_btn)
        
        self.edit_btn = QPushButton("编辑食谱")
        self.edit_btn.clicked.connect(self.on_edit_clicked)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("删除食谱")
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        button_layout.addWidget(self.delete_btn)
        
        layout.addLayout(button_layout)
        
        # 添加拉伸项
        layout.addStretch()
        
        self.setLayout(layout)
    
    def set_recipe(self, recipe):
        """设置显示的食谱"""
        if not recipe:
            self.clear()
            return
        
        self.recipe_id = recipe.id
        
        # 更新标题
        self.title_label.setText(recipe.name)
        
        # 更新图片
        if recipe.image_url:
            self.load_image(recipe.image_url)
        else:
            self.image_label.setText("无图片")
            self.image_label.setPixmap(QPixmap())
        
        # 更新基本信息
        prep_time = recipe.prep_time if recipe.prep_time else 0
        cook_time = recipe.cook_time if recipe.cook_time else 0
        total_time = prep_time + cook_time
        
        self.prep_time_label.setText(f"准备时间: {prep_time} 分钟")
        self.cook_time_label.setText(f"烹饪时间: {cook_time} 分钟")
        self.total_time_label.setText(f"总时间: {total_time} 分钟")
        self.difficulty_label.setText(f"难度: {recipe.difficulty_str}")
        
        self.cuisine_label.setText(f"菜系: {recipe.cuisine if recipe.cuisine else '未知'}")
        
        # 更新标签
        tags = [tag.name for tag in recipe.tags]
        self.tags_label.setText(f"标签: {', '.join(tags) if tags else '无'}")
        
        # 更新描述
        self.desc_text.setText(recipe.description if recipe.description else "无描述")
        
        # 更新食材
        ingredients_text = ""
        for ingredient in recipe.ingredients:
            amount = ingredient.amount if ingredient.amount is not None else ""
            unit = ingredient.unit if ingredient.unit else ""
            ingredients_text += f"- {ingredient.name}: {amount} {unit}\n"
        
        self.ingredients_text.setText(ingredients_text if ingredients_text else "无食材信息")
        
        # 更新步骤
        steps_text = ""
        for step in sorted(recipe.steps, key=lambda x: x.order):
            steps_text += f"{step.order}. {step.description}\n\n"
        
        self.steps_text.setText(steps_text if steps_text else "无步骤信息")
        
        # 更新营养分析
        if recipe.nutrition:
            nutrition_data = {
                'calories': recipe.nutrition.calories,
                'protein': recipe.nutrition.protein,
                'fat': recipe.nutrition.fat,
                'carbohydrates': recipe.nutrition.carbohydrates,
                'fiber': recipe.nutrition.fiber,
                'sugar': recipe.nutrition.sugar,
                'sodium': recipe.nutrition.sodium
            }
            self.nutrition_chart.update_chart(nutrition_data)
        else:
            self.nutrition_chart.update_chart(None)
    
    def clear(self):
        """清空详情面板"""
        self.recipe_id = None
        self.title_label.setText("")
        self.image_label.setText("请选择食谱")
        self.image_label.setPixmap(QPixmap())
        self.prep_time_label.setText("")
        self.cook_time_label.setText("")
        self.total_time_label.setText("")
        self.difficulty_label.setText("")
        self.cuisine_label.setText("")
        self.tags_label.setText("")
        self.desc_text.setText("")
        self.ingredients_text.setText("")
        self.steps_text.setText("")
        self.nutrition_chart.update_chart(None)
    
    def load_image(self, url):
        """加载图片"""
        if url in self.image_cache:
            # 使用缓存的图片
            pixmap = self.image_cache[url]
            self.update_image(pixmap)
            return
        
        # 创建下载线程
        self.downloader = ImageDownloader(url)
        self.downloader.image_downloaded.connect(self.on_image_downloaded)
        self.downloader.download_failed.connect(self.on_image_download_failed)
        self.downloader.start()
        
        # 显示加载中
        self.image_label.setText("加载中...")
    
    def update_image(self, pixmap):
        """更新图片显示"""
        if not pixmap.isNull():
            # 缩放图片以适应标签大小
            scaled_pixmap = pixmap.scaled(self.image_label.size(), 
                                        Qt.AspectRatioMode.KeepAspectRatio, 
                                        Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setText("")
        else:
            self.image_label.setText("无法加载图片")
    
    @pyqtSlot(QImage, str)
    def on_image_downloaded(self, image, url):
        """图片下载完成"""
        pixmap = QPixmap.fromImage(image)
        self.image_cache[url] = pixmap
        self.update_image(pixmap)
    
    @pyqtSlot(str)
    def on_image_download_failed(self, url):
        """图片下载失败"""
        self.image_label.setText("无法加载图片")
    
    def on_analyze_clicked(self):
        """分析营养成分按钮点击事件"""
        if not self.recipe_id:
            QMessageBox.warning(self, "警告", "请先选择一个食谱")
            return
        
        # 创建进度对话框
        progress_dialog = QProgressDialog("正在分析营养成分...", "取消", 0, 100, self)
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)
        
        # 创建分析线程
        self.analysis_thread = NutritionAnalysisThread(self.recipe_id)
        self.analysis_thread.analysis_progress.connect(progress_dialog.setValue)
        self.analysis_thread.analysis_progress.connect(lambda p, m: progress_dialog.setLabelText(m))
        self.analysis_thread.analysis_finished.connect(self.on_analysis_finished)
        self.analysis_thread.analysis_failed.connect(self.on_analysis_failed)
        
        # 连接取消按钮
        progress_dialog.canceled.connect(self.analysis_thread.terminate)
        
        # 启动线程
        self.analysis_thread.start()
        progress_dialog.exec()
    
    @pyqtSlot(dict)
    def on_analysis_finished(self, nutrition_data):
        """营养分析完成"""
        self.nutrition_chart.update_chart(nutrition_data)
        
        # 更新食谱详情
        recipe = RecipeManager.get_recipe_by_id(self.recipe_id)
        if recipe:
            self.set_recipe(recipe)
        
        QMessageBox.information(self, "成功", "营养分析完成")
    
    @pyqtSlot(str)
    def on_analysis_failed(self, error_message):
        """营养分析失败"""
        QMessageBox.warning(self, "失败", error_message)
    
    def on_edit_clicked(self):
        """编辑食谱按钮点击事件"""
        if not self.recipe_id:
            QMessageBox.warning(self, "警告", "请先选择一个食谱")
            return
        
        # 获取当前食谱
        recipe = RecipeManager.get_recipe_by_id(self.recipe_id)
        if not recipe:
            QMessageBox.warning(self, "警告", "食谱不存在")
            return
        
        # 创建编辑对话框
        dialog = RecipeEditDialog(recipe, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 刷新食谱详情
            updated_recipe = RecipeManager.get_recipe_by_id(self.recipe_id)
            self.set_recipe(updated_recipe)
            
            # 发送更新信号
            self.parent().recipe_updated.emit()
    
    def on_delete_clicked(self):
        """删除食谱按钮点击事件"""
        if not self.recipe_id:
            QMessageBox.warning(self, "警告", "请先选择一个食谱")
            return
        
        # 确认删除
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个食谱吗？",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # 删除食谱
            success = RecipeManager.delete_recipe(self.recipe_id)
            if success:
                # 清空详情面板
                self.clear()
                
                # 发送删除信号
                self.parent().recipe_deleted.emit()
                
                QMessageBox.information(self, "成功", "食谱已删除")
            else:
                QMessageBox.warning(self, "失败", "删除食谱失败")

class RecipeEditDialog(QDialog):
    """食谱编辑对话框"""
    def __init__(self, recipe=None, parent=None):
        super().__init__(parent)
        
        self.recipe = recipe
        self.is_new = recipe is None
        
        self.setWindowTitle("添加食谱" if self.is_new else "编辑食谱")
        self.setMinimumSize(600, 500)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 基本信息
        basic_info_group = QGroupBox("基本信息")
        basic_info_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.prep_time_spin = QSpinBox()
        self.prep_time_spin.setRange(0, 1440)
        self.cook_time_spin = QSpinBox()
        self.cook_time_spin.setRange(0, 1440)
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["简单", "中等", "一般", "较难", "困难"])
        self.cuisine_edit = QLineEdit()
        self.image_url_edit = QLineEdit()
        
        basic_info_layout.addRow("名称:", self.name_edit)
        basic_info_layout.addRow("描述:", self.description_edit)
        basic_info_layout.addRow("准备时间(分钟):", self.prep_time_spin)
        basic_info_layout.addRow("烹饪时间(分钟):", self.cook_time_spin)
        basic_info_layout.addRow("难度:", self.difficulty_combo)
        basic_info_layout.addRow("菜系:", self.cuisine_edit)
        basic_info_layout.addRow("图片URL:", self.image_url_edit)
        
        basic_info_group.setLayout(basic_info_layout)
        layout.addWidget(basic_info_group)
        
        # 食材
        ingredients_group = QGroupBox("食材")
        ingredients_layout = QVBoxLayout()
        
        self.ingredients_text = QTextEdit()
        self.ingredients_text.setPlaceholderText("每行输入一种食材，格式：食材名称: 数量 单位\n例如：\n鸡肉: 500 g\n番茄: 2 个")
        
        ingredients_layout.addWidget(self.ingredients_text)
        ingredients_group.setLayout(ingredients_layout)
        layout.addWidget(ingredients_group)
        
        # 步骤
        steps_group = QGroupBox("烹饪步骤")
        steps_layout = QVBoxLayout()
        
        self.steps_text = QTextEdit()
        self.steps_text.setPlaceholderText("每行输入一个步骤，按顺序排列\n例如：\n1. 将鸡肉切成块\n2. 加入调料腌制")
        
        steps_layout.addWidget(self.steps_text)
        steps_group.setLayout(steps_layout)
        layout.addWidget(steps_group)
        
        # 标签
        tags_group = QGroupBox("标签")
        tags_layout = QHBoxLayout()
        
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("用逗号分隔多个标签，例如：早餐,快速,素食")
        
        tags_layout.addWidget(self.tags_edit)
        tags_group.setLayout(tags_layout)
        layout.addWidget(tags_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.on_save_clicked)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 加载食谱数据
        if self.recipe:
            self.load_recipe_data()
    
    def load_recipe_data(self):
        """加载食谱数据到表单"""
        self.name_edit.setText(self.recipe.name)
        self.description_edit.setText(self.recipe.description if self.recipe.description else "")
        self.prep_time_spin.setValue(self.recipe.prep_time if self.recipe.prep_time else 0)
        self.cook_time_spin.setValue(self.recipe.cook_time if self.recipe.cook_time else 0)
        
        # 设置难度
        if self.recipe.difficulty:
            self.difficulty_combo.setCurrentIndex(self.recipe.difficulty - 1)
        
        self.cuisine_edit.setText(self.recipe.cuisine if self.recipe.cuisine else "")
        self.image_url_edit.setText(self.recipe.image_url if self.recipe.image_url else "")
        
        # 设置食材
        ingredients_text = ""
        for ingredient in self.recipe.ingredients:
            amount = ingredient.amount if ingredient.amount is not None else ""
            unit = ingredient.unit if ingredient.unit else ""
            ingredients_text += f"{ingredient.name}: {amount} {unit}\n"
        
        self.ingredients_text.setText(ingredients_text.strip())
        
        # 设置步骤
        steps_text = ""
        for step in sorted(self.recipe.steps, key=lambda x: x.order):
            steps_text += f"{step.order}. {step.description}\n"
        
        self.steps_text.setText(steps_text.strip())
        
        # 设置标签
        tags = [tag.name for tag in self.recipe.tags]
        self.tags_edit.setText(", ".join(tags))
    
    def validate_form(self):
        """验证表单数据"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入食谱名称")
            return False
        
        return True
    
    def parse_ingredients(self):
        """解析食材文本"""
        ingredients = []
        lines = self.ingredients_text.toPlainText().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 解析格式：名称: 数量 单位
            if ':' in line:
                name_part, amount_part = line.split(':', 1)
                name = name_part.strip()
                amount_part = amount_part.strip()
                
                amount = None
                unit = ""
                
                if amount_part:
                    # 尝试解析数量和单位
                    parts = amount_part.split()
                    if parts:
                        try:
                            amount = float(parts[0])
                            if len(parts) > 1:
                                unit = ' '.join(parts[1:])
                        except ValueError:
                            # 如果无法解析数量，将整个部分作为名称的一部分
                            name = f"{name}: {amount_part}"
                
                ingredients.append({
                    'name': name,
                    'amount': amount,
                    'unit': unit
                })
            else:
                # 如果没有冒号，整个行作为食材名称
                ingredients.append({
                    'name': line,
                    'amount': None,
                    'unit': ""
                })
        
        return ingredients
    
    def parse_steps(self):
        """解析步骤文本"""
        steps = []
        lines = self.steps_text.toPlainText().split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 移除可能的数字前缀
            step_text = re.sub(r'^\d+\.\s*', '', line)
            steps.append({
                'order': i + 1,
                'description': step_text
            })
        
        return steps
    
    def parse_tags(self):
        """解析标签文本"""
        tags_text = self.tags_edit.text().strip()
        if not tags_text:
            return []
        
        # 用逗号分隔标签
        tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
        return tags
    
    def on_save_clicked(self):
        """保存按钮点击事件"""
        if not self.validate_form():
            return
        
        # 准备食谱数据
        recipe_data = {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'prep_time': self.prep_time_spin.value(),
            'cook_time': self.cook_time_spin.value(),
            'difficulty': self.difficulty_combo.currentIndex() + 1,
            'cuisine': self.cuisine_edit.text().strip(),
            'image_url': self.image_url_edit.text().strip(),
            'ingredients': self.parse_ingredients(),
            'steps': self.parse_steps(),
            'tags': self.parse_tags()
        }
        
        try:
            if self.is_new:
                # 添加新食谱
                RecipeManager.add_recipe(recipe_data)
                QMessageBox.information(self, "成功", "食谱添加成功")
            else:
                # 更新现有食谱
                RecipeManager.update_recipe(self.recipe.id, recipe_data)
                QMessageBox.information(self, "成功", "食谱更新成功")
            
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "失败", f"保存食谱失败: {str(e)}")

class RecipeFilterWidget(QWidget):
    """食谱筛选面板"""
    filter_changed = pyqtSignal()  # 筛选条件改变信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索食谱名称、食材...")
        self.search_edit.textChanged.connect(self.filter_changed)
        layout.addWidget(self.search_edit)
        
        # 标签筛选
        self.tags_group = QGroupBox("标签")
        self.tags_layout = QVBoxLayout()
        self.tags_group.setLayout(self.tags_layout)
        layout.addWidget(self.tags_group)
        
        # 加载标签
        self.load_tags()
        
        # 时间筛选
        self.time_group = QGroupBox("烹饪时间")
        time_layout = QVBoxLayout()
        
        time_range_layout = QHBoxLayout()
        
        self.min_time_spin = QSpinBox()
        self.min_time_spin.setRange(0, 1440)
        self.min_time_spin.setSuffix(" 分钟")
        self.min_time_spin.valueChanged.connect(self.filter_changed)
        
        self.max_time_spin = QSpinBox()
        self.max_time_spin.setRange(0, 1440)
        self.max_time_spin.setSuffix(" 分钟")
        self.max_time_spin.setValue(1440)
        self.max_time_spin.valueChanged.connect(self.filter_changed)
        
        time_range_layout.addWidget(QLabel("最小:"))
        time_range_layout.addWidget(self.min_time_spin)
        time_range_layout.addSpacing(20)
        time_range_layout.addWidget(QLabel("最大:"))
        time_range_layout.addWidget(self.max_time_spin)
        
        time_layout.addLayout(time_range_layout)
        self.time_group.setLayout(time_layout)
        layout.addWidget(self.time_group)
        
        # 难度筛选
        self.difficulty_group = QGroupBox("难度")
        difficulty_layout = QHBoxLayout()
        
        self.min_difficulty_combo = QComboBox()
        self.min_difficulty_combo.addItems(["不限", "简单", "中等", "一般", "较难", "困难"])
        self.min_difficulty_combo.currentIndexChanged.connect(self.filter_changed)
        
        self.max_difficulty_combo = QComboBox()
        self.max_difficulty_combo.addItems(["不限", "简单", "中等", "一般", "较难", "困难"])
        self.max_difficulty_combo.setCurrentIndex(5)
        self.max_difficulty_combo.currentIndexChanged.connect(self.filter_changed)
        
        difficulty_layout.addWidget(QLabel("从:"))
        difficulty_layout.addWidget(self.min_difficulty_combo)
        difficulty_layout.addSpacing(20)
        difficulty_layout.addWidget(QLabel("到:"))
        difficulty_layout.addWidget(self.max_difficulty_combo)
        
        self.difficulty_group.setLayout(difficulty_layout)
        layout.addWidget(self.difficulty_group)
        
        # 菜系筛选
        self.cuisine_group = QGroupBox("菜系")
        cuisine_layout = QVBoxLayout()
        
        self.cuisine_combo = QComboBox()
        self.cuisine_combo.addItem("不限")
        self.cuisine_combo.currentIndexChanged.connect(self.filter_changed)
        
        cuisine_layout.addWidget(self.cuisine_combo)
        self.cuisine_group.setLayout(cuisine_layout)
        layout.addWidget(self.cuisine_group)
        
        # 加载菜系
        self.load_cuisines()
        
        # 重置按钮
        self.reset_btn = QPushButton("重置筛选")
        self.reset_btn.clicked.connect(self.reset_filter)
        layout.addWidget(self.reset_btn)
        
        # 添加拉伸项
        layout.addStretch()
        
        self.setLayout(layout)
    
    def load_tags(self):
        """加载标签"""
        # 清空现有标签
        for i in reversed(range(self.tags_layout.count())):
            widget = self.tags_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 获取所有标签
        tags = RecipeManager.get_all_tags()
        
        # 创建标签复选框
        self.tag_checkboxes = {}
        for tag in tags:
            checkbox = QCheckBox(tag.name)
            checkbox.stateChanged.connect(self.filter_changed)
            self.tag_checkboxes[tag.name] = checkbox
            self.tags_layout.addWidget(checkbox)
    
    def load_cuisines(self):
        """加载菜系"""
        # 获取所有菜系
        cuisines = RecipeManager.get_cuisines()
        
        # 添加到下拉框
        for cuisine in cuisines:
            self.cuisine_combo.addItem(cuisine)
    
    def reset_filter(self):
        """重置筛选条件"""
        self.search_edit.clear()
        
        # 重置标签
        for checkbox in self.tag_checkboxes.values():
            checkbox.setChecked(False)
        
        # 重置时间
        self.min_time_spin.setValue(0)
        self.max_time_spin.setValue(1440)
        
        # 重置难度
        self.min_difficulty_combo.setCurrentIndex(0)
        self.max_difficulty_combo.setCurrentIndex(5)
        
        # 重置菜系
        self.cuisine_combo.setCurrentIndex(0)
        
        # 发送筛选改变信号
        self.filter_changed.emit()
    
    def get_filter_params(self):
        """获取筛选参数"""
        # 关键词
        keyword = self.search_edit.text().strip() or None
        
        # 标签
        selected_tags = []
        for tag_name, checkbox in self.tag_checkboxes.items():
            if checkbox.isChecked():
                selected_tags.append(tag_name)
        
        tags = selected_tags if selected_tags else None
        
        # 时间
        min_time = self.min_time_spin.value() if self.min_time_spin.value() > 0 else None
        max_time = self.max_time_spin.value() if self.max_time_spin.value() < 1440 else None
        
        # 难度
        min_difficulty = self.min_difficulty_combo.currentIndex() if self.min_difficulty_combo.currentIndex() > 0 else None
        max_difficulty = self.max_difficulty_combo.currentIndex() if self.max_difficulty_combo.currentIndex() < 5 else None
        
        # 菜系
        cuisine = self.cuisine_combo.currentText() if self.cuisine_combo.currentIndex() > 0 else None
        
        return {
            'keyword': keyword,
            'tags': tags,
            'min_time': min_time,
            'max_time': max_time,
            'min_difficulty': min_difficulty,
            'max_difficulty': max_difficulty,
            'cuisine': cuisine
        }

class RecipeListWidget(QWidget):
    """食谱列表面板"""
    recipe_selected = pyqtSignal(int)  # (recipe_id)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 列表控件
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.list_widget)
        
        self.setLayout(layout)
    
    def load_recipes(self, recipes=None):
        """加载食谱列表"""
        # 清空列表
        self.list_widget.clear()
        
        # 如果没有提供食谱列表，则获取所有食谱
        if recipes is None:
            recipes = RecipeManager.get_all_recipes()
        
        # 添加食谱到列表
        for recipe in recipes:
            item = QListWidgetItem()
            
            # 设置食谱名称
            item.setText(recipe.name)
            
            # 设置食谱ID作为数据
            item.setData(Qt.ItemDataRole.UserRole, recipe.id)
            
            # 设置食谱详情作为工具提示
            prep_time = recipe.prep_time if recipe.prep_time else 0
            cook_time = recipe.cook_time if recipe.cook_time else 0
            total_time = prep_time + cook_time
            
            tooltip = f"""
            <b>{recipe.name}</b><br>
            时间: {total_time} 分钟<br>
            难度: {recipe.difficulty_str}<br>
            菜系: {recipe.cuisine if recipe.cuisine else '未知'}
            """
            item.setToolTip(tooltip)
            
            self.list_widget.addItem(item)
    
    def on_item_clicked(self, item):
        """列表项点击事件"""
        recipe_id = item.data(Qt.ItemDataRole.UserRole)
        if recipe_id:
            self.recipe_selected.emit(recipe_id)

class MainWindow(QMainWindow):
    """主窗口"""
    recipe_updated = pyqtSignal()  # 食谱更新信号
    recipe_deleted = pyqtSignal()  # 食谱删除信号
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("智能食谱管理系统")
        self.setMinimumSize(1200, 800)
        
        # 初始化UI
        self.init_ui()
        
        # 连接信号槽
        self.connect_signals()
        
        # 加载数据
        self.load_data()
    
    def init_ui(self):
        """初始化UI"""
        # 中心窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 左侧：筛选面板
        self.filter_widget = RecipeFilterWidget()
        self.filter_widget.setFixedWidth(250)
        main_layout.addWidget(self.filter_widget)
        
        # 中间：食谱列表
        self.recipe_list_widget = RecipeListWidget()
        self.recipe_list_widget.setFixedWidth(300)
        main_layout.addWidget(self.recipe_list_widget)
        
        # 右侧：食谱详情
        self.recipe_detail_widget = RecipeDetailWidget(self)
        main_layout.addWidget(self.recipe_detail_widget)
        
        # 菜单栏
        self.create_menubar()
    
    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        # 添加食谱
        add_recipe_action = file_menu.addAction("添加食谱")
        add_recipe_action.triggered.connect(self.on_add_recipe)
        
        # 从图片分析
        analyze_image_action = file_menu.addAction("从图片分析食材")
        analyze_image_action.triggered.connect(self.on_analyze_image)
        
        # 退出
        exit_action = file_menu.addAction("退出")
        exit_action.triggered.connect(self.close)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        # 关于
        about_action = help_menu.addAction("关于")
        about_action.triggered.connect(self.on_about)
    
    def connect_signals(self):
        """连接信号槽"""
        # 筛选条件改变
        self.filter_widget.filter_changed.connect(self.on_filter_changed)
        
        # 食谱选中
        self.recipe_list_widget.recipe_selected.connect(self.on_recipe_selected)
        
        # 食谱更新和删除
        self.recipe_updated.connect(self.load_data)
        self.recipe_deleted.connect(self.load_data)
    
    def load_data(self):
        """加载数据"""
        # 加载食谱列表
        self.recipe_list_widget.load_recipes()
    
    def on_filter_changed(self):
        """筛选条件改变"""
        # 获取筛选参数
        filter_params = self.filter_widget.get_filter_params()
        
        # 搜索食谱
        recipes = RecipeManager.search_recipes(**filter_params)
        
        # 更新列表
        self.recipe_list_widget.load_recipes(recipes)
    
    def on_recipe_selected(self, recipe_id):
        """食谱选中"""
        # 获取食谱详情
        recipe = RecipeManager.get_recipe_by_id(recipe_id)
        
        # 更新详情面板
        self.recipe_detail_widget.set_recipe(recipe)
    
    def on_add_recipe(self):
        """添加食谱"""
        dialog = RecipeEditDialog(None, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()
    
    def on_analyze_image(self):
        """从图片分析食材"""
        # 打开文件对话框
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        
        if file_dialog.exec() == QDialog.DialogCode.Accepted:
            image_path = file_dialog.selectedFiles()[0]
            
            # 创建进度对话框
            progress_dialog = QProgressDialog("正在分析图像...", "取消", 0, 100, self)
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setValue(0)
            
            # 创建分析线程
            self.image_analysis_thread = FoodImageAnalysisThread(image_path)
            self.image_analysis_thread.analysis_progress.connect(progress_dialog.setValue)
            self.image_analysis_thread.analysis_progress.connect(lambda p, m: progress_dialog.setLabelText(m))
            self.image_analysis_thread.analysis_finished.connect(self.on_image_analysis_finished)
            self.image_analysis_thread.analysis_failed.connect(self.on_image_analysis_failed)
            
            # 连接取消按钮
            progress_dialog.canceled.connect(self.image_analysis_thread.terminate)
            
            # 启动线程
            self.image_analysis_thread.start()
            progress_dialog.exec()
    
    @pyqtSlot(list)
    def on_image_analysis_finished(self, ingredients):
        """图像分析完成"""
        # 创建食材列表文本
        ingredients_text = ""
        for ingredient in ingredients:
            ingredients_text += f"{ingredient['name']}: {ingredient['amount']} {ingredient['unit']} (可信度: {ingredient['confidence']:.2f})\n"
        
        # 显示分析结果
        QMessageBox.information(self, "图像分析结果", f"识别到的食材:\n\n{ingredients_text}")
        
        # 询问是否创建新食谱
        reply = QMessageBox.question(self, "创建食谱", "是否使用这些食材创建新食谱？",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # 创建编辑对话框
            dialog = RecipeEditDialog(None, self)
            
            # 填充食材
            dialog.ingredients_text.setText(ingredients_text)
            
            # 显示对话框
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_data()
    
    @pyqtSlot(str)
    def on_image_analysis_failed(self, error_message):
        """图像分析失败"""
        QMessageBox.warning(self, "失败", error_message)
    
    def on_about(self):
        """关于"""
        about_text = """
        <h2>智能食谱管理系统</h2>
        <p>版本 1.0.0</p>
        <p>一个功能强大的食谱管理软件，支持从网页导入食谱、智能搜索筛选和营养分析。</p>
        <p>使用 Python 和 Qt 开发。</p>
        """
        QMessageBox.about(self, "关于", about_text)

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用图标
    icon_path = os.path.join(os.path.dirname(__file__), '../assets/icons/app_icon.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
