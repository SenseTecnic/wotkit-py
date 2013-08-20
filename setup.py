
from distutils.core import setup

requires = ["requests"]

setup(name = "wotkitpy",
      description = "WoTKit python client using HTTP",
      author = "Mark Duppenthaler",
      author_email = "mduppes@gmail.com",
      url = "http://wotkit.sensetecnic.com/wotkit/",
      version = "1.0.2",
      maintainer = "Sensetecnic Systems",
      maintainer_email = "info@sensetecnic.com",
      license = "MIT",
      py_modules = ["wotkitpy"],
      requires = requires,
      install_requires = requires,
      classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers"
        ]
      )
