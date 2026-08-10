from setuptools import find_packages, setup

setup(
    name="datadoctor",
    version="0.1.0",
    description="AI-Powered Automated Data Science & Machine Learning Platform",
    packages=find_packages(where="backend"),
    package_dir={"": "backend"},
    python_requires=">=3.10",
)
