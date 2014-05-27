from setuptools import setup, find_packages

import os

setup(
    name='PhotoSpread',
    version='0.0.1',
    author='Catherine Warren, Linh Tran, Maitri Kashyap',
    author_email='pytest.photo@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    url='http://pypi.python.org/pypi/PhotoSpread/',
    license='Please check readme',
    description='A Django-based project for organizing and sharing photos',
    long_description=open('Photospread/README.md').read(),
    install_requires=[
        "Django == 1.6.2",
        "South==0.8.4"
        "Pillow==2.4.0"
        "argparse==1.2.1",
        "admin-multiupload==0.1"
        "django-registration==1.0"
        "wsgiref==0.1.2",
    ],
)
