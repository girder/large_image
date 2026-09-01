# large_image_tasks package

## Submodules

## large_image_tasks.tasks module

### *class* large_image_tasks.tasks.JobLogger(level=0, job=None, \*args, \*\*kwargs)

Bases: `Handler`

Initializes the instance - basically setting the formatter to None
and the filter list to empty.

#### emit(record)

Do whatever it takes to actually log the specified logging record.

This version is intended to be implemented by subclasses and so
raises a NotImplementedError.

### large_image_tasks.tasks.cache_histograms_job(job)

### large_image_tasks.tasks.cache_tile_frames_job(job)

### large_image_tasks.tasks.convert_image_job(job)

## Module contents

Top-level package for Large Image Tasks.

### *class* large_image_tasks.LargeImageTasks(app, \*args, \*\*kwargs)

Bases: `GirderWorkerPluginABC`

#### task_imports()

Plugins should override this method if they have tasks.
