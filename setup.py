from setuptools import setup, Extension, find_packages
import sys
import platform

extra_compile_args = []
extra_link_args = []

if sys.platform == 'win32':
    extra_compile_args = ['/W4']
else:
    extra_compile_args = ['-Wall', '-Wextra', '-O3']

magidict_ext = Extension(
    'magidict._magidict',
    sources=['magidict/_magidict.c'],
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args,
    language='c',
)

setup(
    name='magidict',
    version='0.1.4',
    description='A forgiving dictionary with attribute-style access and safe nested access',
    long_description=open('README.md', encoding='utf-8').read() if __import__('os').path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    author='Hristo Bonev',
    author_email='chkbonev@gmail.com',
    url='https://github.com/hristokbonev/magidict',
    license='MIT',
    packages=find_packages(),
    ext_modules=[magidict_ext],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: C',
    ],
    python_requires='>=3.8',
    keywords='dictionary dict safe-access attribute-access nested',
    project_urls={
        'Bug Reports': 'https://github.com/hristokbonev/magidict/issues',
        'Source': 'https://github.com/hristokbonev/magidict',
    },
)
