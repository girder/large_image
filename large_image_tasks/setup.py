from setuptools import setup, find_packages

with open('README.rst', 'r') as fh:
    long_desc = fh.read()

setup(name='large_image_tasks',
      version='0.2.0',
      description='Girder Worker tasks for Large Image.',
      long_description=long_desc,
      author='Kitware Inc',
      author_email='kitware@kitware.com',
      license='Apache Software License 2.0',
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'License :: OSI Approved :: Apache Software License',
          'Topic :: Scientific/Engineering',
          'Intended Audience :: Science/Research',
          'Natural Language :: English',
          'Programming Language :: Python'
      ],
      install_requires=[
          'girder_worker',
          'girder_worker_utils',
          # Packages required by both producer and consumer side installations
          'six>=1.10.0',
      ],
      extras_require={
          'girder': [
              # Dependencies required on the producer (Girder) side.
          ],
          'worker': [
              # Dependencies required on the consumer (Girder Worker) side.
              'pyvips',
          ]
      },
      include_package_data=True,
      entry_points={
          'girder_worker_plugins': [
              'large_image_tasks = large_image_tasks:LargeImageTasks',
          ]
      },
      packages=find_packages(),
      zip_safe=False)
