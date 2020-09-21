from setuptools import find_packages, setup


setup(name='cloud_config_scan',
      version='0.1',
      description='Checkpoint CloudGuard Just In Time Assessment Execution',
      url='',
      author='Idan Perez',
      author_email='',
      packages=find_packages(),
      install_requires=['boto3','requests'],
      include_package_data=True,
      python_requires='>=3.4')