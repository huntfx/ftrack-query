import os
from setuptools import setup, find_packages


# Get the README.md text
with open(os.path.join(os.path.dirname(__file__), 'README.md'), 'r') as f:
    readme = f.read()

# Parse ftrack_query/__init__.py for a version
with open(os.path.join(os.path.dirname(__file__), 'ftrack_query', '__init__.py'), 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = eval(line.split('=')[1].strip())
            break
    else:
        raise RuntimeError('no version found')

# Get the pip requirements
with open(os.path.join(os.path.dirname(__file__), 'requirements.txt'), 'r') as f:
    requirements = [line.strip() for line in f]

setup(
    name='ftrack-query',
    packages=find_packages(),
    version=version,
    license='MIT',
    description='Easy query generation for the FTrack API.',
    long_description=readme,
    long_description_content_type='text/markdown',
    author='Peter Hunt',
    author_email='peter@huntfx.uk',
    url='https://github.com/huntfx/ftrack-query',
    download_url='https://github.com/huntfx/ftrack-query/archive/{}.tar.gz'.format(version),
    project_urls={
        'Documentation': 'https://github.com/huntfx/ftrack-query',
        'Source': 'https://github.com/huntfx/ftrack-query',
        'Issues': 'https://github.com/huntfx/ftrack-query/issues',
    },
    keywords=['ftrack', 'api', 'query', 'vfx'],
    install_requires=requirements,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
    python_requires=('>=2.7')
)
