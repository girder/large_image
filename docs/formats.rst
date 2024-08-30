Image Formats
=============

Preferred Extensions and Mime Types
-----------------------------------

Images can generally be read regardless of their name.  By default, when opening an image with ``large_image.open()``, each tile source reader is tried in turn until one source can open the file.  Each source lists preferred file extensions and mime types with a priority level.  If the file ends with one of these extensions or has one of these mimetypes, the order that the source readers are tried is adjusted based on the specified priority.

The file extensions and mime types that are listed by the core sources that can affect source processing order are listed below.  See ``large_image.listSources()`` for details about priority of the different sources and the ``large_image.constants.SourcePriority`` for the priority meaning.

The following table describes the primary formats supported by ``large-image`` and the acceptable extensions for each format. This table also describes the ``large-image-source-*`` modules that can be used to read each format.

For a full list of all accepted extensions, see :ref:`extensions`.

.. include:: format_table.rst

.. _extensions:

Extensions
~~~~~~~~~~

.. include:: ../build/docs-work/known_extensions.txt
   :literal:

Mime Types
~~~~~~~~~~

.. include:: ../build/docs-work/known_mimetypes.txt
   :literal:
