"""
Setup configuration for kg_manager package
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")

setup(
    name="kg-manager",
    version="0.1.0",
    description="幼儿园教案管理系统核心库",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/ywyz/kindergartenManager",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "python-docx>=0.8.11",
        "openai>=1.0.0",
        "chinese-calendar>=0.15.0",
    ],
    extras_require={
        "ui": ["nicegui>=1.0.0"],
        "dev": ["pytest>=7.0.0"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "Topic :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
