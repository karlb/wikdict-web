from setuptools import setup, find_packages

with open('requirements.txt') as f:
    install_requires = f.read().splitlines()

setup(name='wikdict_web',
      version='1.0',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      setup_requires=['wheel'],
      author='Karl Bartel',
      author_email='karl@karl.berlin',
     )
