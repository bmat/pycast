#!/usr/bin/env python

from distutils.core import setup

setup(
    name = "pycat",
    version = "0.0.1",
    author = "BMAT developers",
    description = "A Python interface to Vericast",
    author_email = "vericast-support@bmat.com",
    url = "http://bmat.com/products/vericast/index.php",
    py_modules = ("pycast",),
    license = "gpl")
