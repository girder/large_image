# Large Image Frame Selector in Jupyter

The large_image library has some convenience features for use in Jupyter Notebooks and Jupyter Lab. The same widgets that can allow compositing frames together in Girder and HistomicsUI can also be used in Jupyter.

## Installation

The large_image library has a variety of tile sources to support a wide range of file formats. The example used in this notebook can just be pip installed. We also install ipyleafleft to allow interactivity with the images.

**Get a Sample File**

Now we get a file to show off some of the capabilities. The sample file is an extract from a much larger file but is sufficient for demonstration purposes.

**Load the file in python**

When we open a file, it just reads the metadata. Actual pixel data is read as needed.

**Show the Image Interactively**

If ipyleafleft is available, you can zoom in on the image. Since this is a multi-frame image (there are 24 image channels), you also get controls to look at different frames.

Try these:

- Switch the Image Control Mode to “Channel Compositing”.
- Switch the Image Control Mode to “Axis” and click “Max Merge”.
- On Channel Compositing, turn off all channels except “Antigen Ki67” and click “Auto Range”
