Girder Annotation Access Control
================================

Annotations have their own access control lists, separate from the item they are attached to.

Girder items do not have access control lists of their own; access to an item is determined by the folder that contains it.  Annotations are different: each annotation stores its own list of users and groups with access, plus its own public flag.  A user's access to an annotation does not automatically match their access to the item's folder.

Required Access
---------------

Site administrators have full access to all annotations.  For other users:

- Listing or reading the annotations on an item requires read access to the item (that is, to its folder) and read access to each annotation.
- Creating an annotation requires write access to the item's folder, or the ``Create annotations`` access flag on that folder.
- Modifying an annotation requires write access to the annotation and either write access to the item or the ``Create annotations`` access flag.
- Viewing or changing the access control list of an annotation requires admin access to the annotation.

Creating Annotations
--------------------

When an annotation is created, the access control list and public flag of the folder containing the item are copied to the annotation.  The user who created the annotation is then given admin access to it.

This is a one-time copy.  As a consequence, users with write or admin access to a folder get write or admin access to every annotation created in that folder, including annotations created by other users.

Copying an annotation to another item (``POST /annotation/{id}/copy``) creates a new annotation. It follows the same rules as creating one: the new annotation gets the access of the destination item's folder, and the user who copied it gets admin access.

Changing Folder Access
----------------------

Changing the access control list or public flag of a folder does not change the access control lists of annotations that already exist on items in that folder, including when the change is applied to subfolders.  For example:

- If a folder is shared with a user after annotations have been created, that user can see the items but not the existing annotations.  Annotations created after the folder was shared will be visible to that user.
- If a user's access to a folder is removed, the existing annotations still list that user.  The user cannot list or read those annotations through the item while they lack read access to it.

Moving Items and Annotations
----------------------------

Moving an item to a different folder does not change the access control lists of its annotations.  Moving an annotation to a different item (``PUT /annotation/{id}`` with an ``itemId``) also leaves its access control list unchanged.  In both cases the annotations keep the access that was copied from their original folder.

Copying Items and Folders
-------------------------

When an item is copied (directly, or as part of copying a folder), its active annotations are copied as well, unless ``copyAnnotations`` is ``false``.  The copied annotations get access as if they had been created in the destination folder: the access control list and public flag of the destination folder replace the original annotation's access control list, and the user who copied the item is given admin access.

The copied annotations keep the original annotation's creator, but that user is not given access to them unless the destination folder's access control list includes them.  The original annotation's creator may not have access to the destination folder.

Changing Annotation Access
--------------------------

The access control list of a single annotation can be edited by a user with admin access to it, either through the API (``PUT /annotation/{id}/access``) or from the annotation's access dialog in the user interface.  This replaces the annotation's access control list and public flag.

Changing Access for All Annotations in a Folder
-----------------------------------------------

If a user has admin access to any annotations on items in a folder or its subfolders, the folder's actions menu includes ``Annotation access control``.  This dialog changes the access of many annotations at once:

- The dialog shows the access control list of a single annotation: the most recently created annotation in the folder or its subfolders to which the user has admin access.
- Saving the dialog replaces the access control list and public flag of every annotation on items in the folder to which the user has admin access.  For site administrators, this is every annotation in the folder.  The lists are replaced, not merged, so any user or group not in the dialog loses access.  Because folder access is copied to new annotations, a user with admin access to a folder usually has admin access to other users' annotations in it, and saving this dialog can remove those users' access to their own annotations.
- Annotations in subfolders are only changed if the option to apply the change to subfolders is checked.  The access control list shown in the dialog may come from a subfolder even when that option is not checked.
- The dialog closes as soon as the request is sent, without waiting for the changes to finish.  If the request fails, no error is shown.

The same operation is available through the API as ``PUT /annotation/folder/{id}/access``.
