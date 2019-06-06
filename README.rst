==========================
NDEx Signor Content Loader
==========================


.. image:: https://img.shields.io/pypi/v/ndexsignorloader.svg
        :target: https://pypi.python.org/pypi/ndexsignorloader

.. image:: https://img.shields.io/travis/ndexcontent/ndexsignorloader.svg
        :target: https://travis-ci.org/ndexcontent/ndexsignorloader

.. image:: https://coveralls.io/repos/github/ndexcontent/ndexsignorloader/badge.svg?branch=master
        :target: https://coveralls.io/github/ndexcontent/ndexsignorloader?branch=master

.. image:: https://readthedocs.org/projects/ndexsignorloader/badge/?version=latest
        :target: https://ndexsignorloader.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

Python application that loads Signor data into NDEx_

This tool downloads data files from Signor_ and performs the following operations:

**1\)** The text files are loaded into a network using this loadplan_

**2\)** The edge attribute **direct** is set to **True** if value is **'t'** otherwise its set to **False**


**3\)** Using values in the **databasea** and **databaseb** data files, the **represents** field found on each node is prefixed with **uniprot:** if the database value is **UNIPROT** and **signor:** if the database value is **SIGNOR**

**4\)** The **compartment** node attribute is set to **cytoplasm** if its not set

**5\)** The layout of the network is created using the spring layout, but with additional logic that positions nodes in a vertical based on value of the **compartment** node attribute. The ordering is as follows:

* **extracellular** are placed at the top
* **receptor** are below **extracellular**
* **cytoplasm** are placed in the middle
* **factor** are below **cytoplasm**
* **phenotypeList** are placed at the bottom

**1000\)** The following network attributes are set

* **name**
* **author** ADD INFO
* **organism** is set to **Human, 9606, Homo sapiens**
* **prov:wasGeneratedBy** is set to ndexsignorloader <VERSION> (example: ndexsignorloader 1.0.0)
* **prov:wasDerivedFrom** set to URL to download data file
* **version** is set to Abbreviated day-month-year (example: 05-Jun-2019)
* **description** is hardcoded in <ADD FILE>
* **rightsHolder** is set to **Prof. Gianni Cesareni**
* **rights** is set to **Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**
* **reference** is set to ADD INFO
* **labels** is set to ADD INFO
* **type** is set to a list with **pathway** and if known type of pathway
* **__normalizationversion** is pulled from **__normalizationversion** attribute of `style.cx`_

Dependencies
------------

* `ndex2 <https://pypi.org/project/ndex2>`_
* `ndexutil <https://pypi.org/project/ndexutil>`_

Compatibility
-------------

* Python 3.3+

Installation
------------

.. code-block::

   git clone https://github.com/ndexcontent/ndexsignorloader
   cd ndexsignorloader
   make dist
   pip install dist/ndexloadsignor*whl


Run **make** command with no arguments to see other build/deploy options including creation of Docker image 

.. code-block::

   make

Output:

.. code-block::

   clean                remove all build, test, coverage and Python artifacts
   clean-build          remove build artifacts
   clean-pyc            remove Python file artifacts
   clean-test           remove test and coverage artifacts
   lint                 check style with flake8
   test                 run tests quickly with the default Python
   test-all             run tests on every Python version with tox
   coverage             check code coverage quickly with the default Python
   docs                 generate Sphinx HTML documentation, including API docs
   servedocs            compile the docs watching for changes
   testrelease          package and upload a TEST release
   release              package and upload a release
   dist                 builds source and wheel package
   install              install the package to the active Python's site-packages
   dockerbuild          build docker image and store in local repository
   dockerpush           push image to dockerhub


Configuration
-------------

The **ndexloadsignor.py** requires a configuration file in the following format be created.
The default path for this configuration is :code:`~/.ndexutils.conf` but can be overridden with
:code:`--conf` flag.

**Format of configuration file**

.. code-block::

    [<value in --profile (default ndexsignorloader)>]

    user = <NDEx username>
    password = <NDEx password>
    server = <NDEx server(omit http) ie public.ndexbio.org>

**Example configuration file**

.. code-block::

    [ndexsignorloader_dev]

    user = joe123
    password = somepassword123
    server = dev.ndexbio.org


Needed files
------------

**TODO:** Add description of needed files


Usage
-----

For information invoke :code:`ndexloadsignor.py -h`

**Example usage**

**TODO:** Add information about example usage

.. code-block::

   ndexloadsignor.py # TODO Add other needed arguments here


Via Docker
~~~~~~~~~~~~~~~~~~~~~~

**Example usage**

**TODO:** Add information about example usage


.. code-block::

   docker run -v `pwd`:`pwd` -w `pwd` coleslawndex/ndexsignorloader:0.1.0 ndexloadsignor.py --conf conf # TODO Add other needed arguments here


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _NDEx: http://www.ndexbio.org
.. _Signor: https://signor.uniroma2.it/
.. _loadplan: https://github.com/ndexcontent/ndexsignorloader/blob/master/ndexsignorloader/loadplan.json
.. _style.cx: https://github.com/ndexcontent/ndexsignorloader/blob/master/ndexsignorloader/style.cx
