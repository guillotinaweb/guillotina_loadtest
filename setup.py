# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup


setup(
    name='glt',
    version='1.0.0',
    description='guillotina load testing library',  # noqa
    long_description=(open('README.rst').read() + '\n' +
                      open('CHANGELOG.rst').read()),
    keywords=['guillotina', 'load', 'test'],
    author='Nathan Van Gheem',
    author_email='vangheem@gmail.com',
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    url='https://github.com/guillotinaweb/guillotina_loadtest',
    license='BSD',
    setup_requires=[
        'pytest-runner',
    ],
    zip_safe=True,
    include_package_data=True,
    packages=find_packages(),
    install_requires=[
        'psutil',
        'guillotina[test]>=1.1.0a7',
        'guillotina_rediscache>=1.0.4',
        'requests==2.16.5'
    ],
    entry_points={
        'console_scripts': [
            'glt = glt.run:run'
        ]
    }
)
