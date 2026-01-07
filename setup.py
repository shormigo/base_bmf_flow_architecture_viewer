"""Setup configuration for BMF Flow Visualizer"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bmf-flow-visualizer",
    version="0.1.0",
    author="BASE Migration Team",
    description="Automatically generate Mermaid diagrams from BMF (Prefect) flow code",
    long_description=long_description,
    long_description_content_type="text/markdown",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "PyYAML>=6.0",
        "pydantic>=2.0",
        "click>=8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "pylint>=2.0",
            "mypy>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "bmf-visualize=main:cli",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
    ],
)
