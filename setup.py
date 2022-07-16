from setuptools import setup
import codecs
import os

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "py_sec/README.md"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

VERSION = '0.0.1'
DESCRIPTION = 'Retrieves and processes the financial statement excel files'
LONG_DESCRIPTION = 'Retrieves and processes the financial statement excel ' \
                   'files from the SEC Edgar website. '

# Setting up
setup(
    name='py_sec',
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    packages=['py_sec'],
    install_requires=['pandas>=1.4.2', 'requests>=2.28.0', 'datetime>=4.5',
                      'ratelimit>=2.2.1', 'tqdm>=4.64.0', 'user_agent>=0.1.10'],
    keywords=['pandas', 'finance', 'sec', 'edgar', 'investing', 'modeling'],
    url='https://github.com/ChrisTheBoi/pySEC',
    author='_fiz_',
    author_email='fiz.czr@gmail.com',
    license='MIT License',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Office/Business :: Financial',
        'Topic :: Office/Business :: Financial :: Investment',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
