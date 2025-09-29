import os
import sys

# Add the project root and application directories to the Python path
sys.path.insert(0, os.path.abspath('../../'))
sys.path.insert(0, os.path.abspath('../../sample'))
sys.path.insert(0, os.path.abspath('../../julee_example'))

project = '...plays with temporal'
copyright = '2025, Chris Gough'
author = 'Chris Gough'
release = '0.1'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinxcontrib.plantuml',
]

templates_path = ['_templates']
exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
    '.venv',
    '**/.venv/**'
]

language = 'en'
html_theme = 'alabaster'
html_static_path = ['_static']
plantuml = 'java -jar /usr/local/bin/plantuml.jar'
plantuml_output_format = 'png'
