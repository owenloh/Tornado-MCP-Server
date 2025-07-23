# Seismic Navigation Speech Interface

A Python-based system for controlling seismic data visualization through voice commands and programmatic interfaces.

## 🎯 Features

The system provides robust features for manipulating seismic data visualizations:

- **Display Adjustments**: Programmatically control gain, change colormaps, and adjust color scales.
- **View Manipulation**: Zoom, pan, and rotate seismic data views.
- **Bookmark Management**: Create, modify, and save seismic visualization bookmarks.

### Key Functions

1.  **`adjust_gain(bookmark_xml, operation, value=None)`**
    -   `operation='increase'`: Increases sensitivity for higher contrast.
    -   `operation='decrease'`: Decreases sensitivity for a wider dynamic range.
    -   `operation='set'`: Sets a specific gain value.
    -   `operation='reset'`: Resets gain to its default value.

2.  **`change_colormap(bookmark_xml, colormap_index)`**
    -   Changes the seismic colormap using an index from 0 to 15.

3.  **`adjust_color_scale(bookmark_xml, times_value)`**
    -   Adjusts the color scale multiplier (e.g., 1x, 2x, 10x) to enhance color contrast.

## 📁 Project Structure

The project follows a clean architecture to ensure scalability and maintainability.

```
📁 seismic-navigation-speech/
├── 📄 README.md                        # This file
├── 📁 src/                             # Source code
│   ├── 📁 core/                       # Core business logic (e.g., bookmark_engine.py)
│   └── 📁 display/                    # Display adjustment modules
├── 📁 data/                           # Data files and templates for bookmarks
│   └── 📁 templates/
├── 📁 bookmarks/                       # Organized bookmark management
│   ├── 📁 demos/                     # Generated demo bookmark files
│   └── 📁 tests/                     # Bookmark-specific tests
├── 📁 demos/                           # Demo scripts to run examples
└── 📁 tests/                           # Main test directory
    ├── 📁 unit/                      # Unit tests
    └── 📁 results/                   # Test output
```

## 🚀 Quick Start

### Basic Usage

Here’s how to get started with the `BookmarkHTMLEngine`:

```python
from src.core.bookmark_engine import BookmarkHTMLEngine

# 1. Initialize the engine
engine = BookmarkHTMLEngine()

# 2. Load a template bookmark
# Ensure the path to the template is correct
template = engine.load_template("data/templates/Example_bookmark.html") 
bookmark_xml = template.to_xml_string()

# 3. Apply adjustments
# Increase the gain
high_gain_xml = engine.adjust_gain(bookmark_xml, 'increase')
# Change to a rainbow colormap
rainbow_xml = engine.change_colormap(high_gain_xml, 7)

# 4. Save the result
# The output path should be managed for organization
output_path = "bookmarks/demos/gain_control/my_high_gain_bookmark.html"
engine.save_bookmark_html(rainbow_xml, output_path)

print(f"Bookmark saved to {output_path}")
```

### Combined Adjustments

You can chain multiple adjustments to create a custom view:

```python
from src.core.bookmark_engine import BookmarkHTMLEngine

engine = BookmarkHTMLEngine()
template = engine.load_template("data/templates/Example_bookmark.html")
modified_xml = template.to_xml_string()

# Apply multiple adjustments
modified_xml = engine.adjust_gain(modified_xml, 'set', 2.5)
modified_xml = engine.change_colormap(modified_xml, 7)  # Rainbow
modified_xml = engine.adjust_color_scale(modified_xml, 2)

# Save the combined result
output_path = "bookmarks/demos/combined/my_custom_view.html"
engine.save_bookmark_html(modified_xml, output_path)
print(f"Custom view bookmark saved to {output_path}")

```

## 🧪 Testing

The project includes a suite of tests to ensure functionality and correctness.

### Run Demo Scripts

To see the display adjustments in action, run the demo script:
```bash
python demos/demo_display_adjustments_clean.py
```
This script generates various demo bookmarks in the `bookmarks/demos/` directory.

### Run Unit Tests

To run the full suite of unit tests:
```bash
python -m pytest tests/unit/
```

To run a specific test file:
```bash
python tests/unit/test_display_adjustments.py
```

## 🏗️ Architecture

The system is designed with enterprise software development practices in mind:

- **Separation of Concerns**: Core logic, display functions, and file management are kept in separate modules.
- **Modular Design**: The modular structure makes the system easy to extend and maintain.
- **Comprehensive Testing**: Unit tests provide high coverage to ensure reliability.
- **Clean Code**: The code is well-documented, readable, and follows best practices.
