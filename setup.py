import os
import sys
import sysconfig
from setuptools import setup, Extension, find_packages


extra_compile_args = []
extra_link_args = []
include_dirs = [r"C:\Users\chkbo\AppData\Local\Programs\Python\Python39\include"]
library_dirs = [r"C:\Users\chkbo\AppData\Local\Programs\Python\Python39\libs"]
libraries = ["python39"]

if sys.platform == "win32":
    extra_compile_args = ["/W4"]

    # Build Python library name (e.g., python39.lib)
    py_version = f"python{sys.version_info.major}{sys.version_info.minor}"
    libraries = [py_version]

    # Try multiple locations for Python libs on Windows
    python_lib_dir = None

    # Method 1: Try sysconfig.get_config_var("LIBDIR")
    libdir = sysconfig.get_config_var("LIBDIR")
    if libdir and os.path.isdir(libdir):
        python_lib_dir = libdir

    # Method 2: Try {prefix}/libs
    if not python_lib_dir:
        prefix = sys.prefix
        libs_path = os.path.join(prefix, "libs")
        if os.path.isdir(libs_path):
            python_lib_dir = libs_path

    # Method 3: Try {exec_prefix}/libs
    if not python_lib_dir:
        exec_prefix = sys.exec_prefix
        libs_path = os.path.join(exec_prefix, "libs")
        if os.path.isdir(libs_path):
            python_lib_dir = libs_path

    if python_lib_dir:
        library_dirs = [python_lib_dir]
        print(f"Using Python library directory: {python_lib_dir}")
    else:
        print(
            f"Warning: Could not find Python library directory. Trying default search paths."
        )
        print(f"sys.prefix: {sys.prefix}")
        print(f"sys.exec_prefix: {sys.exec_prefix}")

else:
    extra_compile_args = ["-Wall", "-Wextra", "-O3"]
    libdir = sysconfig.get_config_var("LIBDIR")
    if libdir:
        library_dirs = [libdir]


magidict_ext = Extension(
    "magidict._magidict",
    sources=["magidict/_magidict.c"],
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args,
    language="c",
)


if os.path.exists("README.md"):
    with open("README.md", encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = ""


setup(
    name="magidict",
    version="0.1.4",
    description="A forgiving dictionary with attribute-style access and safe nested access",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Hristo Bonev",
    author_email="chkbonev@gmail.com",
    url="https://github.com/hristokbonev/magidict",
    license="MIT",
    packages=find_packages(),
    ext_modules=[magidict_ext],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: C",
    ],
    python_requires=">=3.8",
    keywords="dictionary dict safe-access attribute-access nested",
    project_urls={
        "Bug Reports": "https://github.com/hristokbonev/magidict/issues",
        "Source": "https://github.com/hristokbonev/magidict",
    },
)
