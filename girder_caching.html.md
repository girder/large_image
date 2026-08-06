# Caching Large Image in Girder

Tile sources are opened: when large image files uploaded or imported; when large image files are viewed; when thumbnails are generated; when an item page with a large image is viewd; and from some API calls.  All of these result in the source being placed in the cache \_except_ import.

Since there are multiple users, the cache size should be large enough that no user has an image that they are actively viewing fall out of cache.

Example of cache use when the `GET` `/item/{id}/tile/zxy/{z}/{x}/{y}?style=<style>&encoding=<encoding>&...` endpoint is called:
