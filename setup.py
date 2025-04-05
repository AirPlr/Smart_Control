from setuptools import setup, Extension
from Cython.Build import cythonize
import os

# Lista dei file Python da compilare con Cython
source_files = [
    "app.py"
]

# Estensioni da compilare
extensions = [
    Extension(os.path.splitext(source_file)[0], [source_file])
    for source_file in source_files
]

setup(
    name="ControlloApp",
    ext_modules=cythonize(extensions, compiler_directives={'language_level': "3"}),
    zip_safe=False,
)