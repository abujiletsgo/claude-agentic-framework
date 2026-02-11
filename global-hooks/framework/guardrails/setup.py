from setuptools import setup, find_packages

setup(
    name="guardrails",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pyyaml>=6.0.0",
        "pydantic>=2.0.0",
    ],
    python_requires=">=3.9",
)
