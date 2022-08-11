Girder Annotation Configuration Options
=======================================

General Plugin Settings
-----------------------

There are some general plugin settings that affect large_image annotation as a Girder plugin.  These settings can be accessed by an Admin user through the ``Admin Console`` / ``Plugins`` and selecting the gear icon next to ``Large image annotation``.

Store annotation history
~~~~~~~~~~~~~~~~~~~~~~~~

If ``Record annotation history`` is selected, whenever annotations are saved, previous versions are kept in the database.  This can greatly increase the size of the database.  The old versions of the annotations allow the API to be used to revent to previous versions or to audit changes over time.
