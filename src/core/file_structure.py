"""
File structure management for seismic navigation system

This module handles all file path management and directory structure
for the seismic navigation speech interface.
"""

import os
from pathlib import Path


class FileStructure:
    """Centralized file structure configuration"""
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    # __file__ is str path of file_structure.py
    
    # Main directories
    SRC_DIR = BASE_DIR / "src"
    DATA_DIR = BASE_DIR / "data"
    TESTS_DIR = BASE_DIR / "tests"
    EXAMPLES_DIR = BASE_DIR / "examples"
    DOCS_DIR = BASE_DIR / "docs"
    SCRIPTS_DIR = BASE_DIR / "scripts"
    
    # Data subdirectories
    TEMPLATES_DIR = DATA_DIR / "templates"
    SAMPLES_DIR = DATA_DIR / "samples"
    BOOKMARKS_DIR = DATA_DIR / "bookmarks"
    CAPTURES_DIR = DATA_DIR / "captures"
    DEMOS_DIR = BOOKMARKS_DIR / "demos"
    
    # Test subdirectories
    UNIT_TESTS_DIR = TESTS_DIR / "unit"
    INTEGRATION_TESTS_DIR = TESTS_DIR / "integration"
    RESULTS_DIR = TESTS_DIR / "results"
    
    # Template files
    DEFAULT_TEMPLATE = TEMPLATES_DIR / "default_bookmark.html"
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        directories = [
            cls.SRC_DIR, cls.DATA_DIR, cls.TESTS_DIR, cls.EXAMPLES_DIR,
            cls.DOCS_DIR, cls.SCRIPTS_DIR, cls.TEMPLATES_DIR, cls.SAMPLES_DIR,
            cls.BOOKMARKS_DIR, cls.CAPTURES_DIR, cls.DEMOS_DIR, cls.UNIT_TESTS_DIR,
            cls.INTEGRATION_TESTS_DIR, cls.RESULTS_DIR
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_template_path(cls, filename: str) -> Path:
        """Get path for template file"""
        return cls.TEMPLATES_DIR / filename
    
    @classmethod
    def get_demo_path(cls, filename: str) -> Path:
        """Get path for demo file"""
        return cls.DEMOS_DIR / filename
    
    @classmethod
    def get_test_path(cls, filename: str) -> Path:
        """Get path for test file"""
        return cls.UNIT_TESTS_DIR / filename
    
    @classmethod
    def get_example_path(cls, filename: str) -> Path:
        """Get path for example file"""
        return cls.EXAMPLES_DIR / filename
    
    @classmethod
    def get_results_path(cls, filename: str) -> Path:
        """Get path for test results file"""
        return cls.RESULTS_DIR / filename