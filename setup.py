from setuptools import setup, find_packages

setup(
    name="ai_healthcare_project",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "pydantic",
        "python-dotenv",
        "requests",
    ],
)
