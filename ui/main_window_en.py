import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QListWidget, QListWidgetItem, QLabel, QPushButton, QLineEdit,
                             QTextEdit, QSpinBox, QComboBox, QCheckBox, QGroupBox, QFormLayout,
                             QScrollArea, QMessageBox, QFileDialog, QProgressDialog, QDialog,
                             QInputDialog)
from PyQt6.QtGui import QPixmap, QImage, QIcon, QFont, QColor
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import requests
from io import BytesIO
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from core.recipe_manager_en_complete import RecipeManager, NutritionAnalyzer, FoodImageAnalyzer
from core.models_en import session, Recipe, Tag


class ImageDownloader(QThread):
    """Image download thread"""
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


class RecipeImportThread(QThread):
    """Recipe import thread"""
    import_progress = pyqtSignal(int, str)  # (progress, message)
    import_finished = pyqtSignal(dict)  # (recipe_data)
    import_failed = pyqtSignal(str)  # (error_message)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            self.import_progress.emit(20, "Connecting to webpage...")
            recipe_data = RecipeManager.import_recipe_from_url(self.url)

            if recipe_data:
                self.import_progress.emit(80, "Recipe parsing completed")
                self.import_finished.emit(recipe_data)
            else:
                self.import_failed.emit("Could not parse recipe information from this webpage")
        except Exception as e:
            self.import_failed.emit(f"Import failed: {str(e)}")


class NutritionAnalysisThread(QThread):
    """Nutrition analysis thread"""
    analysis_progress = pyqtSignal(int, str)  # (progress, message)
    analysis_finished = pyqtSignal(dict)  # (nutrition_data)
    analysis_failed = pyqtSignal(str)  # (error_message)

    def __init__(self, recipe_id):
        super().__init__()
        self.recipe_id = recipe_id

    def run(self):
        try:
            self.analysis_progress.emit(30, "Retrieving recipe information...")
            nutrition_data = NutritionAnalyzer.analyze_recipe_nutrition(self.recipe_id)

            if nutrition_data:
                self.analysis_progress.emit(100, "Nutrition analysis completed")
                self.analysis_finished.emit(nutrition_data)
            else:
                self.analysis_failed.emit("Could not analyze the nutritional content of this recipe")
        except Exception as e:
            self.analysis_failed.emit(f"Analysis failed: {str(e)}")


class FoodImageAnalysisThread(QThread):
    """Food image analysis thread"""
    analysis_progress = pyqtSignal(int, str)  # (progress, message)
    analysis_finished = pyqtSignal(list)  # (ingredients_list)
    analysis_failed = pyqtSignal(str)  # (error_message)

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path

    def run(self):
        try:
            self.analysis_progress.emit(30, "Analyzing image...")
            ingredients = FoodImageAnalyzer.analyze_food_image(self.image_path)

            if ingredients:
                self.analysis_progress.emit(100, "Image analysis completed")
                self.analysis_finished.emit(ingredients)
            else:
                self.analysis_failed.emit("Could not analyze ingredients in this image")
        except Exception as e:
            self.analysis_failed.emit(f"Analysis failed: {str(e)}")


class NutritionChartWidget(QWidget):
    """Nutrition chart widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(500, 150)  # 固定尺寸
        self.figure, self.ax = plt.subplots(figsize=(8, 2))
        self.canvas = FigureCanvas(self.figure)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def update_chart(self, nutrition_data):
        """Update nutrition chart"""
        self.ax.clear()

        if not nutrition_data:
            self.canvas.draw()
            return

        # Prepare data
        labels = ['Protein(g)', 'Fat(g)', 'Carbohydrates(g)', 'Fiber(g)', 'Sugar(g)']
        values = [
            nutrition_data.get('protein', 0),
            nutrition_data.get('fat', 0),
            nutrition_data.get('carbohydrates', 0),
            nutrition_data.get('fiber', 0),
            nutrition_data.get('sugar', 0)
        ]

        # Set colors
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']

        # Create bar chart
        bars = self.ax.bar(labels, values, color=colors)

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            self.ax.text(bar.get_x() + bar.get_width() / 2., height + 0.1,
                         f'{height:.1f}', ha='center', va='bottom')

        # Set title and labels
        self.ax.set_title('Nutritional Analysis', fontsize=14, fontweight='bold')
        self.ax.set_ylabel('Grams', fontsize=12)

        # Set grid
        self.ax.yaxis.grid(True, linestyle='--', alpha=0.7)

        # Adjust layout
        self.figure.tight_layout()

        # Update chart
        self.canvas.draw()


class RecipeDetailWidget(QWidget):
    """Recipe detail widget"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.recipe_id = None
        self.image_cache = {}  # Cache downloaded images

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        self.title_label = QLabel()
        self.title_label.setFont(QFont('Arial', 20, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # Image
        self.image_label = QLabel()
        self.image_label.setFixedSize(300, 200)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #ddd; border-radius: 5px;")
        layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Basic information
        info_layout = QHBoxLayout()

        # Time and difficulty
        time_diff_layout = QVBoxLayout()

        self.prep_time_label = QLabel()
        self.cook_time_label = QLabel()
        self.total_time_label = QLabel()
        self.difficulty_label = QLabel()

        time_diff_layout.addWidget(self.prep_time_label)
        time_diff_layout.addWidget(self.cook_time_label)
        time_diff_layout.addWidget(self.total_time_label)
        time_diff_layout.addWidget(self.difficulty_label)

        # Cuisine and tags
        cuisine_tags_layout = QVBoxLayout()

        self.cuisine_label = QLabel()
        self.tags_label = QLabel()

        cuisine_tags_layout.addWidget(self.cuisine_label)
        cuisine_tags_layout.addWidget(self.tags_label)

        info_layout.addLayout(time_diff_layout)
        info_layout.addLayout(cuisine_tags_layout)

        layout.addLayout(info_layout)

        # Description
        self.desc_group = QGroupBox("Description")
        self.desc_text = QTextEdit()
        self.desc_text.setReadOnly(True)
        self.desc_text.setStyleSheet("background-color: #f9f9f9;")

        desc_layout = QVBoxLayout()
        desc_layout.addWidget(self.desc_text)
        self.desc_group.setLayout(desc_layout)
        layout.addWidget(self.desc_group)

        # Ingredients
        self.ingredients_group = QGroupBox("Ingredients")
        self.ingredients_text = QTextEdit()
        self.ingredients_text.setReadOnly(True)
        self.ingredients_text.setStyleSheet("background-color: #f9f9f9;")

        ingredients_layout = QVBoxLayout()
        ingredients_layout.addWidget(self.ingredients_text)
        self.ingredients_group.setLayout(ingredients_layout)
        layout.addWidget(self.ingredients_group)

        # Steps
        self.steps_group = QGroupBox("Cooking Steps")
        self.steps_text = QTextEdit()
        self.steps_text.setReadOnly(True)
        self.steps_text.setStyleSheet("background-color: #f9f9f9;")

        steps_layout = QVBoxLayout()
        steps_layout.addWidget(self.steps_text)
        self.steps_group.setLayout(steps_layout)
        layout.addWidget(self.steps_group)

        # Nutrition Analysis
        self.nutrition_group = QGroupBox("Nutrition Analysis")
        self.nutrition_chart = NutritionChartWidget()

        nutrition_layout = QVBoxLayout()
        nutrition_layout.addWidget(self.nutrition_chart)
        self.nutrition_group.setLayout(nutrition_layout)
        layout.addWidget(self.nutrition_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.analyze_btn = QPushButton("Analyze Nutrition")
        self.analyze_btn.clicked.connect(self.on_analyze_clicked)
        button_layout.addWidget(self.analyze_btn)

        self.edit_btn = QPushButton("Edit Recipe")
        self.edit_btn.clicked.connect(self.on_edit_clicked)
        button_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete Recipe")
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        button_layout.addWidget(self.delete_btn)

        layout.addLayout(button_layout)

        # Add stretch
        layout.addStretch()

        self.setLayout(layout)

    def set_recipe(self, recipe):
        """Set the recipe to display"""
        if not recipe:
            self.clear()
            return

        self.recipe_id = recipe.id

        # Update title
        self.title_label.setText(recipe.name)

        # Update image
        if recipe.image_url:
            self.load_image(recipe.image_url)
        else:
            self.image_label.setText("No Image")
            self.image_label.setPixmap(QPixmap())

        # Update basic information
        prep_time = recipe.prep_time if recipe.prep_time else 0
        cook_time = recipe.cook_time if recipe.cook_time else 0
        total_time = prep_time + cook_time

        self.prep_time_label.setText(f"Prep Time: {prep_time} mins")
        self.cook_time_label.setText(f"Cook Time: {cook_time} mins")
        self.total_time_label.setText(f"Total Time: {total_time} mins")
        self.difficulty_label.setText(f"Difficulty: {recipe.difficulty_str}")

        self.cuisine_label.setText(f"Cuisine: {recipe.cuisine if recipe.cuisine else 'Unknown'}")

        # Update tags
        tags = [tag.name for tag in recipe.tags]
        self.tags_label.setText(f"Tags: {', '.join(tags) if tags else 'None'}")

        # Update description
        self.desc_text.setText(recipe.description if recipe.description else "No description available")

        # Update ingredients
        ingredients_text = ""
        for ingredient in recipe.ingredients:
            amount = ingredient.amount if ingredient.amount is not None else ""
            unit = ingredient.unit if ingredient.unit else ""
            ingredients_text += f"- {ingredient.name}: {amount} {unit}\n"

        self.ingredients_text.setText(ingredients_text if ingredients_text else "No ingredients information")

        # Update steps
        steps_text = ""
        for step in sorted(recipe.steps, key=lambda x: x.order):
            steps_text += f"{step.order}. {step.description}\n\n"

        self.steps_text.setText(steps_text if steps_text else "No steps information")

        # Update nutrition analysis
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
        """Clear the detail panel"""
        self.recipe_id = None
        self.title_label.setText("")
        self.image_label.setText("Select a Recipe")
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
        """Load image from URL"""
        if url in self.image_cache:
            # Use cached image
            pixmap = self.image_cache[url]
            self.update_image(pixmap)
            return

        # Create download thread
        self.downloader = ImageDownloader(url)
        self.downloader.image_downloaded.connect(self.on_image_downloaded)
        self.downloader.download_failed.connect(self.on_image_download_failed)
        self.downloader.start()

        # Show loading message
        self.image_label.setText("Loading...")

    def update_image(self, pixmap):
        """Update image display"""
        if not pixmap.isNull():
            # Scale image to fit label size
            scaled_pixmap = pixmap.scaled(self.image_label.size(),
                                          Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setText("")
        else:
            self.image_label.setText("Failed to load image")

    @pyqtSlot(QImage, str)
    def on_image_downloaded(self, image, url):
        """Image download completed"""
        pixmap = QPixmap.fromImage(image)
        self.image_cache[url] = pixmap
        self.update_image(pixmap)

    @pyqtSlot(str)
    def on_image_download_failed(self, url):
        """Image download failed"""
        self.image_label.setText("Failed to load image")

    def on_analyze_clicked(self):
        """Analyze nutrition button clicked"""
        if not self.recipe_id:
            QMessageBox.warning(self, "Warning", "Please select a recipe first")
            return

        # Create progress dialog
        progress_dialog = QProgressDialog("Analyzing nutritional content...", "Cancel", 0, 100, self)
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)

        # Create analysis thread
        self.analysis_thread = NutritionAnalysisThread(self.recipe_id)
        self.analysis_thread.analysis_progress.connect(progress_dialog.setValue)
        self.analysis_thread.analysis_progress.connect(lambda p, m: progress_dialog.setLabelText(m))
        self.analysis_thread.analysis_finished.connect(self.on_analysis_finished)
        self.analysis_thread.analysis_failed.connect(self.on_analysis_failed)

        # Connect cancel button
        progress_dialog.canceled.connect(self.analysis_thread.terminate)

        # Start thread
        self.analysis_thread.start()
        progress_dialog.exec()

    @pyqtSlot(dict)
    def on_analysis_finished(self, nutrition_data):
        """Nutrition analysis completed"""
        self.nutrition_chart.update_chart(nutrition_data)

        # Update recipe details
        recipe = RecipeManager.get_recipe_by_id(self.recipe_id)
        if recipe:
            self.set_recipe(recipe)

        QMessageBox.information(self, "Success", "Nutrition analysis completed")

    @pyqtSlot(str)
    def on_analysis_failed(self, error_message):
        """Nutrition analysis failed"""
        QMessageBox.warning(self, "Failed", error_message)

    def on_edit_clicked(self):
        """Edit recipe button clicked"""
        if not self.recipe_id:
            QMessageBox.warning(self, "Warning", "Please select a recipe first")
            return

        # Get current recipe
        recipe = RecipeManager.get_recipe_by_id(self.recipe_id)
        if not recipe:
            QMessageBox.warning(self, "Warning", "Recipe does not exist")
            return

        # Create edit dialog
        dialog = RecipeEditDialog(recipe, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Refresh recipe details
            updated_recipe = RecipeManager.get_recipe_by_id(self.recipe_id)
            self.set_recipe(updated_recipe)

            # Emit update signal
            self.parent().recipe_updated.emit()

    def on_delete_clicked(self):
        """Delete recipe button clicked"""
        if not self.recipe_id:
            QMessageBox.warning(self, "Warning", "Please select a recipe first")
            return

        # Confirm deletion
        reply = QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to delete this recipe?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            # Delete recipe
            success = RecipeManager.delete_recipe(self.recipe_id)
            if success:
                # Clear detail panel
                self.clear()

                # Emit deletion signal
                self.parent().recipe_deleted.emit()

                QMessageBox.information(self, "Success", "Recipe has been deleted")
            else:
                QMessageBox.warning(self, "Failed", "Failed to delete recipe")


class RecipeEditDialog(QDialog):
    """Recipe edit dialog"""

    def __init__(self, recipe=None, parent=None):
        super().__init__(parent)

        self.recipe = recipe
        self.is_new = recipe is None

        self.setWindowTitle("Add Recipe" if self.is_new else "Edit Recipe")
        self.setMinimumSize(600, 500)

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()

        # Basic information
        basic_info_group = QGroupBox("Basic Information")
        basic_info_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.prep_time_spin = QSpinBox()
        self.prep_time_spin.setRange(0, 1440)
        self.cook_time_spin = QSpinBox()
        self.cook_time_spin.setRange(0, 1440)
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["Easy", "Medium", "Intermediate", "Advanced", "Expert"])
        self.cuisine_edit = QLineEdit()
        self.image_url_edit = QLineEdit()

        basic_info_layout.addRow("Name:", self.name_edit)
        basic_info_layout.addRow("Description:", self.description_edit)
        basic_info_layout.addRow("Prep Time (minutes):", self.prep_time_spin)
        basic_info_layout.addRow("Cook Time (minutes):", self.cook_time_spin)
        basic_info_layout.addRow("Difficulty:", self.difficulty_combo)
        basic_info_layout.addRow("Cuisine:", self.cuisine_edit)
        basic_info_layout.addRow("Image URL:", self.image_url_edit)

        basic_info_group.setLayout(basic_info_layout)
        layout.addWidget(basic_info_group)

        # Ingredients
        ingredients_group = QGroupBox("Ingredients")
        ingredients_layout = QVBoxLayout()

        self.ingredients_text = QTextEdit()
        self.ingredients_text.setPlaceholderText(
            "Enter one ingredient per line in the format: Ingredient Name: Amount Unit\nExample:\nChicken: 500 g\nTomato: 2 pcs")

        ingredients_layout.addWidget(self.ingredients_text)
        ingredients_group.setLayout(ingredients_layout)
        layout.addWidget(ingredients_group)

        # Steps
        steps_group = QGroupBox("Cooking Steps")
        steps_layout = QVBoxLayout()

        self.steps_text = QTextEdit()
        self.steps_text.setPlaceholderText(
            "Enter one step per line, in order\nExample:\n1. Cut the chicken into pieces\n2. Add seasoning and marinate")

        steps_layout.addWidget(self.steps_text)
        steps_group.setLayout(steps_layout)
        layout.addWidget(steps_group)

        # Tags
        tags_group = QGroupBox("Tags")
        tags_layout = QHBoxLayout()

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Separate multiple tags with commas, e.g.: Breakfast,Quick,Vegan")

        tags_layout.addWidget(self.tags_edit)
        tags_group.setLayout(tags_layout)
        layout.addWidget(tags_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.on_save_clicked)
        button_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Load recipe data
        if self.recipe:
            self.load_recipe_data()

    def load_recipe_data(self):
        """Load recipe data into form"""
        self.name_edit.setText(self.recipe.name)
        self.description_edit.setText(self.recipe.description if self.recipe.description else "")
        self.prep_time_spin.setValue(self.recipe.prep_time if self.recipe.prep_time else 0)
        self.cook_time_spin.setValue(self.recipe.cook_time if self.recipe.cook_time else 0)

        # Set difficulty
        if self.recipe.difficulty:
            self.difficulty_combo.setCurrentIndex(self.recipe.difficulty - 1)

        self.cuisine_edit.setText(self.recipe.cuisine if self.recipe.cuisine else "")
        self.image_url_edit.setText(self.recipe.image_url if self.recipe.image_url else "")

        # Set ingredients
        ingredients_text = ""
        for ingredient in self.recipe.ingredients:
            amount = ingredient.amount if ingredient.amount is not None else ""
            unit = ingredient.unit if ingredient.unit else ""
            ingredients_text += f"{ingredient.name}: {amount} {unit}\n"

        self.ingredients_text.setText(ingredients_text.strip())

        # Set steps
        steps_text = ""
        for step in sorted(self.recipe.steps, key=lambda x: x.order):
            steps_text += f"{step.order}. {step.description}\n"

        self.steps_text.setText(steps_text.strip())

        # Set tags
        tags = [tag.name for tag in self.recipe.tags]
        self.tags_edit.setText(", ".join(tags))

    def validate_form(self):
        """Validate form data"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Warning", "Please enter a recipe name")
            return False

        return True

    def parse_ingredients(self):
        """Parse ingredients text"""
        ingredients = []
        lines = self.ingredients_text.toPlainText().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse format: Name: Amount Unit
            if ':' in line:
                name_part, amount_part = line.split(':', 1)
                name = name_part.strip()
                amount_part = amount_part.strip()

                amount = None
                unit = ""

                if amount_part:
                    # Try to parse amount and unit
                    parts = amount_part.split()
                    if parts:
                        try:
                            amount = float(parts[0])
                            if len(parts) > 1:
                                unit = ' '.join(parts[1:])
                        except ValueError:
                            # If cannot parse amount, treat entire part as part of name
                            name = f"{name}: {amount_part}"

                ingredients.append({
                    'name': name,
                    'amount': amount,
                    'unit': unit
                })
            else:
                # If no colon, treat entire line as ingredient name
                ingredients.append({
                    'name': line,
                    'amount': None,
                    'unit': ""
                })

        return ingredients

    def parse_steps(self):
        """Parse steps text"""
        steps = []
        lines = self.steps_text.toPlainText().split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Remove possible number prefix
            step_text = re.sub(r'^\d+\.\s*', '', line)
            steps.append({
                'order': i + 1,
                'description': step_text
            })

        return steps

    def parse_tags(self):
        """Parse tags text"""
        tags_text = self.tags_edit.text().strip()
        if not tags_text:
            return []

        # Split tags by comma
        tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
        return tags

    def on_save_clicked(self):
        """Save button clicked"""
        if not self.validate_form():
            return

        # Prepare recipe data
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
                # Add new recipe
                RecipeManager.add_recipe(recipe_data)
                QMessageBox.information(self, "Success", "Recipe added successfully")
            else:
                # Update existing recipe
                RecipeManager.update_recipe(self.recipe.id, recipe_data)
                QMessageBox.information(self, "Success", "Recipe updated successfully")

            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Failed", f"Failed to save recipe: {str(e)}")


class RecipeFilterWidget(QWidget):
    """Recipe filter widget"""
    filter_changed = pyqtSignal()  # Filter changed signal

    def __init__(self, parent=None):
        super().__init__(parent)

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Search box
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search recipe name, ingredients...")
        self.search_edit.textChanged.connect(self.filter_changed)
        layout.addWidget(self.search_edit)

        # Tag filter
        self.tags_group = QGroupBox("Tags")
        self.tags_layout = QVBoxLayout()
        self.tags_group.setLayout(self.tags_layout)
        layout.addWidget(self.tags_group)

        # Load tags
        self.load_tags()

        # Time filter
        self.time_group = QGroupBox("Cooking Time")
        time_layout = QVBoxLayout()

        time_range_layout = QHBoxLayout()

        self.min_time_spin = QSpinBox()
        self.min_time_spin.setRange(0, 1440)
        self.min_time_spin.setSuffix(" mins")
        self.min_time_spin.valueChanged.connect(self.filter_changed)

        self.max_time_spin = QSpinBox()
        self.max_time_spin.setRange(0, 1440)
        self.max_time_spin.setSuffix(" mins")
        self.max_time_spin.setValue(1440)
        self.max_time_spin.valueChanged.connect(self.filter_changed)

        time_range_layout.addWidget(QLabel("Min:"))
        time_range_layout.addWidget(self.min_time_spin)
        time_range_layout.addSpacing(20)
        time_range_layout.addWidget(QLabel("Max:"))
        time_range_layout.addWidget(self.max_time_spin)

        time_layout.addLayout(time_range_layout)
        self.time_group.setLayout(time_layout)
        layout.addWidget(self.time_group)

        # Difficulty filter
        self.difficulty_group = QGroupBox("Difficulty")
        difficulty_layout = QHBoxLayout()

        self.min_difficulty_combo = QComboBox()
        self.min_difficulty_combo.addItems(["Any", "Easy", "Medium", "Intermediate", "Advanced", "Expert"])
        self.min_difficulty_combo.currentIndexChanged.connect(self.filter_changed)

        self.max_difficulty_combo = QComboBox()
        self.max_difficulty_combo.addItems(["Any", "Easy", "Medium", "Intermediate", "Advanced", "Expert"])
        self.max_difficulty_combo.setCurrentIndex(5)
        self.max_difficulty_combo.currentIndexChanged.connect(self.filter_changed)

        difficulty_layout.addWidget(QLabel("From:"))
        difficulty_layout.addWidget(self.min_difficulty_combo)
        difficulty_layout.addSpacing(20)
        difficulty_layout.addWidget(QLabel("To:"))
        difficulty_layout.addWidget(self.max_difficulty_combo)

        self.difficulty_group.setLayout(difficulty_layout)
        layout.addWidget(self.difficulty_group)

        # Cuisine filter
        self.cuisine_group = QGroupBox("Cuisine")
        cuisine_layout = QVBoxLayout()

        self.cuisine_combo = QComboBox()
        self.cuisine_combo.addItem("Any")
        self.cuisine_combo.currentIndexChanged.connect(self.filter_changed)

        cuisine_layout.addWidget(self.cuisine_combo)
        self.cuisine_group.setLayout(cuisine_layout)
        layout.addWidget(self.cuisine_group)

        # Load cuisines
        self.load_cuisines()

        # Reset button
        self.reset_btn = QPushButton("Reset Filters")
        self.reset_btn.clicked.connect(self.reset_filter)
        layout.addWidget(self.reset_btn)

        # Add stretch
        layout.addStretch()

        self.setLayout(layout)

    def load_tags(self):
        """Load tags"""
        # Clear existing tags
        for i in reversed(range(self.tags_layout.count())):
            widget = self.tags_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Get all tags
        tags = RecipeManager.get_all_tags()

        # Create tag checkboxes
        self.tag_checkboxes = {}
        for tag in tags:
            checkbox = QCheckBox(tag.name)
            checkbox.stateChanged.connect(self.filter_changed)
            self.tag_checkboxes[tag.name] = checkbox
            self.tags_layout.addWidget(checkbox)

    def load_cuisines(self):
        """Load cuisines"""
        # Get all cuisines
        cuisines = RecipeManager.get_cuisines()

        # Add to combo box
        for cuisine in cuisines:
            self.cuisine_combo.addItem(cuisine)

    def reset_filter(self):
        """Reset filter conditions"""
        self.search_edit.clear()

        # Reset tags
        for checkbox in self.tag_checkboxes.values():
            checkbox.setChecked(False)

        # Reset time
        self.min_time_spin.setValue(0)
        self.max_time_spin.setValue(1440)

        # Reset difficulty
        self.min_difficulty_combo.setCurrentIndex(0)
        self.max_difficulty_combo.setCurrentIndex(5)

        # Reset cuisine
        self.cuisine_combo.setCurrentIndex(0)

        # Emit filter changed signal
        self.filter_changed.emit()

    def get_filter_params(self):
        """Get filter parameters"""
        # Keyword
        keyword = self.search_edit.text().strip() or None

        # Tags
        selected_tags = []
        for tag_name, checkbox in self.tag_checkboxes.items():
            if checkbox.isChecked():
                selected_tags.append(tag_name)

        tags = selected_tags if selected_tags else None

        # Time
        min_time = self.min_time_spin.value() if self.min_time_spin.value() > 0 else None
        max_time = self.max_time_spin.value() if self.max_time_spin.value() < 1440 else None

        # Difficulty
        min_difficulty = self.min_difficulty_combo.currentIndex() if self.min_difficulty_combo.currentIndex() > 0 else None
        max_difficulty = self.max_difficulty_combo.currentIndex() if self.max_difficulty_combo.currentIndex() < 5 else None

        # Cuisine
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
    """Recipe list widget"""
    recipe_selected = pyqtSignal(int)  # (recipe_id)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # List widget
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.list_widget)

        self.setLayout(layout)

    def load_recipes(self, recipes=None):
        """Load recipe list"""
        # Clear list
        self.list_widget.clear()

        # If no recipes provided, get all recipes
        if recipes is None:
            recipes = RecipeManager.get_all_recipes()

        # Add recipes to list
        for recipe in recipes:
            item = QListWidgetItem()

            # Set recipe name
            item.setText(recipe.name)

            # Set recipe ID as data
            item.setData(Qt.ItemDataRole.UserRole, recipe.id)

            # Set recipe details as tooltip
            prep_time = recipe.prep_time if recipe.prep_time else 0
            cook_time = recipe.cook_time if recipe.cook_time else 0
            total_time = prep_time + cook_time

            tooltip = f"""
            <b>{recipe.name}</b><br>
            Time: {total_time} mins<br>
            Difficulty: {recipe.difficulty_str}<br>
            Cuisine: {recipe.cuisine if recipe.cuisine else 'Unknown'}
            """
            item.setToolTip(tooltip)

            self.list_widget.addItem(item)

    def on_item_clicked(self, item):
        """List item clicked event"""
        recipe_id = item.data(Qt.ItemDataRole.UserRole)
        if recipe_id:
            self.recipe_selected.emit(recipe_id)


class MainWindow(QMainWindow):
    """Main window"""
    recipe_updated = pyqtSignal()  # Recipe updated signal
    recipe_deleted = pyqtSignal()  # Recipe deleted signal

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Recipelity - Intelligent Recipe Management System")
        self.setMinimumSize(1200, 800)

        # Initialize UI
        self.init_ui()

        # Connect signals and slots
        self.connect_signals()

        # Load data
        self.load_data()

    def init_ui(self):
        """Initialize UI"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Set stylesheet
        self.setStyleSheet("""
            /* Main window styles */
            QMainWindow {
                background-color: #f8f9fa;
            }

            /* Group box styles */
            QGroupBox {
                border: 1px solid #dee2e6;
                border-radius: 5px;
                margin-top: 10px;
                background-color: white;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: #2c3e50;
                font-weight: bold;
            }

            /* Button styles */
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 14px;
            }

            QPushButton:hover {
                background-color: #2980b9;
            }

            QPushButton:pressed {
                background-color: #1f6391;
            }

            /* List widget styles */
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 5px;
                background-color: white;
            }

            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f1f1;
            }

            QListWidget::item:hover {
                background-color: #e3f2fd;
            }

            QListWidget::item:selected {
                background-color: #bbdefb;
                color: #1a237e;
            }

            /* Line edit styles */
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 12px;
                background-color: white;
            }

            QLineEdit:focus {
                border-color: #3498db;
                outline: none;
            }

            /* Text edit styles */
            QTextEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 12px;
                background-color: white;
            }

            QTextEdit:focus {
                border-color: #3498db;
                outline: none;
            }

            /* Combo box styles */
            QComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 12px;
                background-color: white;
            }

            QComboBox:focus {
                border-color: #3498db;
                outline: none;
            }

            /* Spin box styles */
            QSpinBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 12px;
                background-color: white;
            }

            QSpinBox:focus {
                border-color: #3498db;
                outline: none;
            }

            /* Check box styles */
            QCheckBox {
                color: #343a40;
            }

            /* Label styles */
            QLabel {
                color: #343a40;
            }

            /* Filter widget styles */
            RecipeFilterWidget {
                background-color: #f1f8fe;
                border-right: 1px solid #dee2e6;
            }

            /* Recipe list widget styles */
            RecipeListWidget {
                background-color: #f8f9fa;
                border-right: 1px solid #dee2e6;
            }

            /* Recipe detail widget styles */
            RecipeDetailWidget {
                background-color: white;
            }

            /* Nutrition chart widget styles */
            NutritionChartWidget {
                background-color: white;
            }

            /* Recipe edit dialog styles */
            RecipeEditDialog {
                background-color: white;
            }
        """)

        # Main layout
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # Left: Filter panel
        self.filter_widget = RecipeFilterWidget()
        self.filter_widget.setFixedWidth(280)
        main_layout.addWidget(self.filter_widget)

        # Middle: Recipe list
        self.recipe_list_widget = RecipeListWidget()
        self.recipe_list_widget.setFixedWidth(320)
        main_layout.addWidget(self.recipe_list_widget)

        # Right: Recipe detail
        self.recipe_detail_widget = RecipeDetailWidget(self)
        main_layout.addWidget(self.recipe_detail_widget, stretch=1)

        # Menu bar
        self.create_menubar()

    def create_menubar(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        # Add recipe
        add_recipe_action = file_menu.addAction("Add Recipe")
        add_recipe_action.triggered.connect(self.on_add_recipe)

        # Import from URL
        import_url_action = file_menu.addAction("Import Recipe from URL")
        import_url_action.triggered.connect(self.on_import_url)

        # Analyze from image
        analyze_image_action = file_menu.addAction("Analyze Ingredients from Image")
        analyze_image_action.triggered.connect(self.on_analyze_image)

        # Exit
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # Help menu
        help_menu = menubar.addMenu("Help")

        # About
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.on_about)

    def connect_signals(self):
        """Connect signals and slots"""
        # Filter changed
        self.filter_widget.filter_changed.connect(self.on_filter_changed)

        # Recipe selected
        self.recipe_list_widget.recipe_selected.connect(self.on_recipe_selected)

        # Recipe updated and deleted
        self.recipe_updated.connect(self.load_data)
        self.recipe_deleted.connect(self.load_data)

    def load_data(self):
        """Load data"""
        # Load recipe list
        self.recipe_list_widget.load_recipes()

    def on_filter_changed(self):
        """Filter changed"""
        # Get filter parameters
        filter_params = self.filter_widget.get_filter_params()

        # Search recipes
        recipes = RecipeManager.search_recipes(**filter_params)

        # Update list
        self.recipe_list_widget.load_recipes(recipes)

    def on_recipe_selected(self, recipe_id):
        """Recipe selected"""
        # Get recipe details
        recipe = RecipeManager.get_recipe_by_id(recipe_id)

        # Update detail panel
        self.recipe_detail_widget.set_recipe(recipe)

    def on_add_recipe(self):
        """Add recipe"""
        dialog = RecipeEditDialog(None, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def on_import_url(self):
        """Import recipe from URL"""
        # Create URL input dialog
        url, ok = QInputDialog.getText(self, "Import Recipe from URL", "Please enter the recipe webpage URL:")

        if ok and url:
            # Create progress dialog
            progress_dialog = QProgressDialog("Importing recipe...", "Cancel", 0, 100, self)
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setValue(0)

            # Create import thread
            self.import_thread = RecipeImportThread(url)
            self.import_thread.import_progress.connect(progress_dialog.setValue)
            self.import_thread.import_progress.connect(lambda p, m: progress_dialog.setLabelText(m))
            self.import_thread.import_finished.connect(self.on_import_finished)
            self.import_thread.import_failed.connect(self.on_import_failed)

            # Connect cancel button
            progress_dialog.canceled.connect(self.import_thread.terminate)

            # Start thread
            self.import_thread.start()
            progress_dialog.exec()

    @pyqtSlot(dict)
    def on_import_finished(self, recipe_data):
        """Recipe import finished"""
        # Create edit dialog with pre-filled imported data
        dialog = RecipeEditDialog(None, self)

        # Fill data
        dialog.name_edit.setText(recipe_data.get('name', ''))
        dialog.description_edit.setText(recipe_data.get('description', ''))
        dialog.prep_time_spin.setValue(recipe_data.get('prep_time', 0))
        dialog.cook_time_spin.setValue(recipe_data.get('cook_time', 0))

        # Set difficulty
        difficulty = recipe_data.get('difficulty')
        if difficulty and 1 <= difficulty <= 5:
            dialog.difficulty_combo.setCurrentIndex(difficulty - 1)

        dialog.cuisine_edit.setText(recipe_data.get('cuisine', ''))
        dialog.image_url_edit.setText(recipe_data.get('image_url', ''))

        # Set ingredients
        ingredients_text = ""
        for ingredient in recipe_data.get('ingredients', []):
            amount = ingredient.get('amount', '')
            unit = ingredient.get('unit', '')
            ingredients_text += f"{ingredient.get('name', '')}: {amount} {unit}\n"

        dialog.ingredients_text.setText(ingredients_text.strip())

        # Set steps
        steps_text = ""
        for step in recipe_data.get('steps', []):
            steps_text += f"{step.get('order', '')}. {step.get('description', '')}\n"

        dialog.steps_text.setText(steps_text.strip())

        # Set tags
        tags = recipe_data.get('tags', [])
        dialog.tags_edit.setText(", ".join(tags))

        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    @pyqtSlot(str)
    def on_import_failed(self, error_message):
        """Recipe import failed"""
        QMessageBox.warning(self, "Failed", error_message)

    def on_analyze_image(self):
        """Analyze ingredients from image"""
        # Open file dialog
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

        if file_dialog.exec() == QDialog.DialogCode.Accepted:
            image_path = file_dialog.selectedFiles()[0]

            # Create progress dialog
            progress_dialog = QProgressDialog("Analyzing image...", "Cancel", 0, 100, self)
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setValue(0)

            # Create analysis thread
            self.image_analysis_thread = FoodImageAnalysisThread(image_path)
            self.image_analysis_thread.analysis_progress.connect(progress_dialog.setValue)
            self.image_analysis_thread.analysis_progress.connect(lambda p, m: progress_dialog.setLabelText(m))
            self.image_analysis_thread.analysis_finished.connect(self.on_image_analysis_finished)
            self.image_analysis_thread.analysis_failed.connect(self.on_image_analysis_failed)

            # Connect cancel button
            progress_dialog.canceled.connect(self.image_analysis_thread.terminate)

            # Start thread
            self.image_analysis_thread.start()
            progress_dialog.exec()

    @pyqtSlot(list)
    def on_image_analysis_finished(self, ingredients):
        """Image analysis finished"""
        # Create ingredients list text
        ingredients_text = ""
        for ingredient in ingredients:
            ingredients_text += f"{ingredient['name']}: {ingredient['amount']} {ingredient['unit']} (Confidence: {ingredient['confidence']:.2f})\n"

        # Show analysis result
        QMessageBox.information(self, "Image Analysis Result", f"Recognized ingredients:\n\n{ingredients_text}")

        # Ask if create new recipe
        reply = QMessageBox.question(self, "Create Recipe",
                                     "Do you want to create a new recipe using these ingredients?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            # Create edit dialog
            dialog = RecipeEditDialog(None, self)

            # Fill ingredients
            dialog.ingredients_text.setText(ingredients_text)

            # Show dialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_data()

    @pyqtSlot(str)
    def on_image_analysis_failed(self, error_message):
        """Image analysis failed"""
        QMessageBox.warning(self, "Failed", error_message)

    def on_about(self):
        """About"""
        about_text = """
        <h2>Recipelity - Intelligent Recipe Management System</h2>
        <p>Version 1.0.0</p>
        <p>A powerful recipe management software that supports importing recipes from websites, 
        intelligent search and filtering, and nutrition analysis.</p>
        <p>Developed with Python and Qt.</p>
        """
        QMessageBox.about(self, "About", about_text)


def main():
    """Main function"""
    app = QApplication(sys.argv)

    # Set application icon
    icon_path = os.path.join(os.path.dirname(__file__), '../assets/icons/app_icon.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Create main window
    window = MainWindow()
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
