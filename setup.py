import setuptools

import rpipe

with open('README.md') as f:
      long_description = f.read()

with open('requirements.txt') as f:
      install_requires = map(lambda s: s.strip(), f)

setuptools.setup(
      name='restpipe',
      version=rpipe.__version__,
      description="An SSL-authenticated, durable, bidirectional, RESTful pipe that transports custom events.",
      long_description=long_description,
      classifiers=[],
      keywords='gevent ssl socket rest event',
      author='Dustin Oprea',
      author_email='myselfasunder@gmail.com',
      url='',
      license='GPL 2',
      packages=['rpipe'],
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      package_data={
            'rpipe': ['resources/scripts/*', 
                      'resources/ssl/*',
                      'resources/data/*',
                      'resources/protobuf/*'],
      },
      scripts=[
            'rpipe/resources/scripts/rp_client_set_identity',
            'rpipe/resources/scripts/rp_client_start_gunicorn_dev',
            'rpipe/resources/scripts/rp_client_start_gunicorn_prod',
            'rpipe/resources/scripts/rp_server_set_identity',
            'rpipe/resources/scripts/rp_server_start_gunicorn_dev',
            'rpipe/resources/scripts/rp_server_start_gunicorn_prod',
      ],
)
