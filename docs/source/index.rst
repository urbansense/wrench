.. Wrench documentation master file, created by
   sphinx-quickstart on Thu Feb 27 19:24:43 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Wrench Documentation
===============================

.. image:: _static/logo.png
   :alt: Wrench Logo
   :align: center
   :width: 400

|

Wrench is a modular framework for harvesting, classifying, and cataloging sensor data from various sources.

.. note::
   This documentation is under active development.

Features
--------

* **Harvesting**: Collection of data from sensor networks (currently SensorThings API)
* **Grouping**: Classification of sensor data using taxonomy-enhanced learning (TELEClass)
* **Cataloging**: Registration of data in standardized catalogs (SDDI)

Components
----------

The framework is composed of three main components:

**Harvester**
   Fetches data from different sources. Currently implemented for SensorThings API.

**Grouper**
   Classifies data using AI techniques. Includes the TELEClass system for taxonomy-enhanced classification.

**Cataloger**
   Registers data in catalog systems. Currently supports SDDI catalogs.

Getting Started
--------------

.. toctree::
   :maxdepth: 1
   :caption: Installation & Usage

   getting_started/installation
   getting_started/quickstart
   getting_started/configuration

Architecture
-----------

.. toctree::
   :maxdepth: 1
   :caption: System Architecture

   architecture/overview
   architecture/pipeline
   architecture/extending

Component Documentation
----------------------

.. toctree::
   :maxdepth: 1
   :caption: Core Components

   components/harvester
   components/grouper
   components/cataloger

API Reference
------------

.. toctree::
   :maxdepth: 2
   :caption: API Documentation

   api/harvester
   api/grouper
   api/cataloger

   api/common

Examples and Tutorials
---------------------

.. toctree::
   :maxdepth: 1
   :caption: Examples

   examples/sensorthings
   examples/teleclass
   examples/sddi
   examples/custom_pipeline

Contributing
-----------

.. toctree::
   :maxdepth: 1
   :caption: Development

   contributing/setup
   contributing/guidelines
   contributing/testing

Indices and Tables
=================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
