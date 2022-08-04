Girder Configuration Options
============================

General Plugin Settings
-----------------------

There are some general plugin settings that affect large_image as a Girder plugin.  These settings can be accessed by an Admin user through the ``Admin Console`` / ``Plugins`` and selecting the gear icon next to ``Large image``.

YAML Configuration Files
------------------------

Some settings can be specified per-folder tree using yaml files.  For these settings, if the configuration file exists in the current folder it is used.  If not, the parent folders are checked iteratively up to the parent collection or user.  If no configuration file is found, the ``.config`` folder in the collection or user is checked for the file.  Lastly, the ``Configuration Folder`` specified on the plugin settings paghe is checked for the configuration file.

The configuration files can have different configurations based on the user's access level and group membership.

The yaml file has the following structure:

::

    ---
    # most settings are key-value pairs, where the value could be another
    # directionary with keys and values, lists, or other valid data.
    <key>: <value>
    # The access key is special
    access:
      # logged in users get these settings
      user:
        # If the value is a dictionary and the key matches a key at the base
        # level, then the values are combined.  To completely replace the base
        # value, add the special key "__all__" and set it's value to true.
        <key>: <value>
      # admin users get these settings
      admin:
        <key>: <value>
    # The groups key specifes that specific user groups have distinct settings
    groups:
      <group name>:
        <key>: <value>
        # groups can specify access based on user or admin, too.
        access: ...
    # If __inherit__ is true, then merge this config file with the next config
    # file in the parent folder hierarchy.
    __inherit__: true

.large_image_config.yaml
~~~~~~~~~~~~~~~~~~~~~~~~

This is used to specify how items appear in item lists.  There are two settings, one for folders in the main Girder UI and one for folders in dialogs (such as when browsing in the file dialog).

::

    ---
    # If present, show a table with column headers in item lists
    itemList:
      # show these columns in order from left to right.  Each column has a
      # "type" and "value".  It optionally has a "title" used for the column
      # header, and a "format" used for searching and filtering.
      columns:
        -
          # The "image" type's value is either "thumbnail" or the name of an
          # associated image, such as "macro" or "label".
          type: image
          value: thumbnail
          title: Thumbnail
        -
          type: image
          value: label
          title: Slide Label
        -
          # The "record" type is from the default item record.  The value is
          # one of "name", "size", or "controls".
          type: record
          value: name
        -
          type: record
          value: siz3
        -
          type: record
          value: controls
        -
          # The "metadata" type is taken from the item's "meta" contents.  It
          # can be a nested key by using dots in its name.
          type: metadata
          value: Stain
          # "format" can be "text", "number", "category".  Other values may be
          # specified later.
          format: text
        -
          type: metadata
          # This will get "Label" from the first entry in array "gloms"
          value: gloms.0.Label
          title: First Glom Label
        -
          type: metadata
          # You can use some javascript-like properties, such as .length for
          # the length of arrays.
          value: gloms.length
          title: Number of Gloms