from setuptools import setup, find_packages

setup(
    name="zion-agent",
    version="1.0.0",
    description="Zion AI Agent - A local, repo-aware AI coding assistant",
    author="Gowdham",
    packages=find_packages(),
    py_modules=["config"],
    include_package_data=True,
    install_requires=[
        "ollama",
        "pydantic",
        "rich",
        "cerebras_cloud_sdk",
        "questionary",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "zion=zion.cli:main",
        ],
    },
    python_requires=">=3.8",
)
