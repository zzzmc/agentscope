# -*- coding: utf-8 -*-
""" Setup for installation."""
from __future__ import absolute_import, division, print_function

import re

import setuptools

# obtain version from src/agentscope/_version.py
with open("src/agentscope/_version.py", encoding="UTF-8") as f:
    VERSION = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
        f.read(),
        re.MULTILINE,
    ).group(1)

NAME = "agentscope"
URL = "https://github.com/modelscope/agentscope"

# released requires
minimal_requires = [
    "networkx",
    "black",
    "docstring_parser",
    "pydantic",
    "loguru==0.6.0",
    "tiktoken",
    "Pillow",
    "requests",
    "inputimeout",
    "numpy",
    "Flask==3.0.0",
    "Flask-Cors==4.0.0",
    "Flask-SocketIO==5.3.6",
    "flask_sqlalchemy",
    "flake8",
    "psutil",
    "scipy",
    # Leaving openai and dashscope here as default supports
    "openai>=1.3.0",
    "dashscope>=1.19.0",
]

extra_service_requires = [
    "docker",
    "pymongo",
    "pymysql",
    "bs4",
    "beautifulsoup4",
    "feedparser",
    "notebook",
    "nbclient",
    "nbformat",
    "playwright",
    "markdownify",
]

extra_distribute_requires = [
    "grpcio==1.60.0",
    "grpcio-tools==1.60.0",
    "protobuf==4.25.0",
    "expiringdict",
    "cloudpickle",
    "redis",
]

extra_dev_requires = [
    # unit test
    "pytest",
    "pytest-cov",
    "pre-commit",
    # doc
    "sphinx",
    "sphinx-autobuild",
    "sphinx_rtd_theme",
    "myst-parser",
    "sphinxcontrib-mermaid",
    # extra
    "transformers",
]

extra_gradio_requires = [
    "gradio==4.44.1",
    "modelscope_studio==0.0.5",
]

extra_rag_requires = [
    "llama-index==0.10.30",
]

# API requires
extra_gemini_requires = ["google-generativeai>=0.4.0"]
extra_litellm_requires = ["litellm"]
extra_zhipuai_requires = ["zhipuai"]
extra_ollama_requires = ["ollama>=0.1.7"]

# Full requires
extra_full_requires = (
    extra_distribute_requires
    + extra_service_requires
    + extra_dev_requires
    + extra_gradio_requires
    + extra_rag_requires
    + extra_gemini_requires
    + extra_litellm_requires
    + extra_zhipuai_requires
    + extra_ollama_requires
)

# For online workstation
extra_online_requires = extra_full_requires + [
    "oss2",
    "flask_babel",
    "babel==2.15.0",
    "gunicorn",
]

with open("README.md", "r", encoding="UTF-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name=NAME,
    version=VERSION,
    author="SysML team of Alibaba Tongyi Lab ",
    author_email="gaodawei.gdw@alibaba-inc.com",
    description="AgentScope: A Flexible yet Robust Multi-Agent Platform.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=URL,
    download_url=f"{URL}/archive/v{VERSION}.tar.gz",
    keywords=["deep-learning", "multi agents", "agents"],
    package_dir={"": "src"},
    packages=setuptools.find_packages("src"),
    package_data={
        "agentscope.studio": ["static/**/*", "templates/**/*"],
        "agentscope.prompt": ["_prompt_examples.json"],
        "agentscope.service.browser": ["markpage.js"],
    },
    install_requires=minimal_requires,
    extras_require={
        # For specific LLM API
        "ollama": extra_ollama_requires,
        "litellm": extra_litellm_requires,
        "zhipuai": extra_zhipuai_requires,
        "gemini": extra_gemini_requires,
        # For service functions
        "service": extra_service_requires,
        # For distribution mode
        "distribute": extra_distribute_requires,
        # With unit test requires
        "dev": extra_dev_requires,
        # With full requires
        "full": extra_full_requires,
        # With online workstation requires
        "online": extra_online_requires,
    },
    license="Apache License 2.0",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "as_studio=agentscope.studio:as_studio",
            "as_gradio=agentscope.web.gradio.studio:run_app",
            "as_workflow=agentscope.web.workstation.workflow:main",
            "as_server=agentscope.server.launcher:as_server",
        ],
    },
)
