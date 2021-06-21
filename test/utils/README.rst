********************************
Large Image Taet Utility Scripts
********************************

This directory consists of files that were useful in testing various aspects of
large_image.  These files are not part of the stable library interface nor part
of the regularly used testing code.  They may not be maintained.

Some utilities:

- compression_test.py - Recompress input files with a wide set of options.
  Compute full statistics on each output file to determine the amount of loss
  introduced with those compression options when appropriate.

- compression_test_summary.py - Collect the results from the compression test
  and output a csv file.
