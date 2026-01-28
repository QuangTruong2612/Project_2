import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

project_name = "Project_2"

list_of_files = [
    ".github/workflows/.gitkeep",
        f"src/{project_name}/__init__.py",
    f"src/{project_name}/components/__init__.py",
    f"src/{project_name}/utils/__init__.py",
    f"src/{project_name}/configs/__init__.py",
    f"src/{project_name}/configs/configurations.py",
    f"src/{project_name}/pipeline/__init__.py",
    f"src/{project_name}/entity/__init__.py",
    f"src/{project_name}/constants/__init__.py",
    "configs/config.yaml",
    "params.yaml",
    "requirements.txt",
    "setup.py",
    "dvc.yaml",
    "research/trials.ipynb",
    "templates/index.html"
]

for filepath in list_of_files:
    filepath = Path(filepath)
    filedir, filename = os.path.split(filepath)

    if filedir != "":
        os.makedirs(filedir, exist_ok=True)
        logging.info(f"Created directory: {filedir}")

    if (not os.path.exists(filepath)) or (os.path.getsize(filepath) == 0):
        with open(filepath, "w") as f:
            pass
        logging.info(f"Created file: {filepath}")
    else:
        logging.info(f"File already exists and is not empty: {filepath}")