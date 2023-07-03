Girder Configuration Options
============================

General Plugin Settings
-----------------------

There are some general plugin settings that affect large_image as a Girder plugin.  These settings can be accessed by an Admin user through the ``Admin Console`` / ``Plugins`` and selecting the gear icon next to ``Large image``.

YAML Configuration Files
------------------------

Some settings can be specified per-folder tree using yaml files.  For these settings, if the configuration file exists in the current folder it is used.  If not, the parent folders are checked iteratively up to the parent collection or user.  If no configuration file is found, the ``.config`` folder in the collection or user is checked for the file.  Lastly, the ``Configuration Folder`` specified on the plugin settings page is checked for the configuration file.

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
    # The groups key specifies that specific user groups have distinct settings
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

Items Lists
...........

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
          value: size
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
        # You can edit metadata in a item list by adding the edit: true entry
        # and the options from the itemMetadata records that are shown below.
        # In this case, edit to metadata that validate are saved immediately.
        -
          type: metadata
          value: userstain
          title: User Stain
          # description is used as both a tooltip and as placeholder text
          description: Staining method
          # if required is true, the value can't be empty
          required: true
          # If a regex is specified, the value must match
          # regex: '^(Eosin|H&E|Other)$'
          # If an enum is specified, the value is set via a dropdown select box
          enum:
            - Eosin
            - H&E
            - Other
          # If a default is specified, if the value is unset, it will show this
          # value in the control
          default: H&E
      defaultSort:
        # The default lists a sort order for sortable columns.  This must have
        # type, value, and dir for each entry, where dir is either "up" or
        # "down".
        -
          type: metadata
          value: Stain
          dir: up
        -
          type: record
          value: name
          dir: down
    itemListDialog:
      # Show these columns
      columns:
        -
          type: image
          value: thumbnail
          title: Thumbnail
        -
          type: record
          value: name
        -
          type: metadata
          value: Stain
          format: text
        -
          type: record
          value: size

If there are no large images in a folder, none of the image columns will appear.

Item Metadata
.............

By default, item metadata can contain any keys and values.  These can be given better titles and restricted in their data types.

::

    ---
    # If present, offer to add these specific keys and restrict their datatypes
    itemMetadata:
      -
        # value is the key name within the metadata
        value: stain
        # title is the displayed titles
        title: Stain
        # description is used as both a tooltip and as placeholder text
        description: Staining method
        # if required is true, the delete button does not appear
        required: true
        # If a regex is specified, the value must match
        # regex: '^(Eosin|H&E|Other)$'
        # If an enum is specified, the value is set via a dropdown select box
        enum:
          - Eosin
          - H&E
          - Other
        # If a default is specified, when the value is created, it will show
        # this value in the control
        default: H&E
      -
        value: rating
        # type can be "number", "integer", or "text" (default)
        type: number
        # minimum and maximum are inclusive
        minimum: 0
        maximum: 10
        # Exclusive values can be specified instead
        # exclusiveMinimum: 0
        # exclusiveMaximum: 10

Editing Configuration Files
---------------------------

Some file types can be edited on their item page.  This is detected based on the mime type associated with the file: ``application/json`` for json files and ``text/yaml`` or ``text/x-yaml`` for yaml files.  If a user has enough permissions, these can be modified and saved.  Note that this does not alter imported files; rather, on save it will create a new file in the assetstore and use that; this works fine for using the configuration files.

For admins, there is also support for the ``application/x-girder-ini`` mime type for Girder configuration files.   This has a special option to replace the existing Girder configuration and restart the server and should be used with due caution.
