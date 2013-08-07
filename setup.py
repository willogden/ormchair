from distutils.core import setup

setup(
	name='ormchair',
	version='0.3.0',
	description='An ORM for CouchDB with JSON-Schema export support',
	long_description=open('README').read(),
	author='Will Ogden',
	url='https://github.com/willogden/ormchair',
	py_modules=['ormchair'],
	packages=['tests',],
	install_requires=['requests>=1.2.0']
)