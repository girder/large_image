//==============================================================================
// Temporary drawing with a pencil.  It goes away as soon as the camera changes.
// pencil icon (image as html) follows the cursor.
// Middle mouse button (or properties menu item) drops pencil.
// maybe option in properties menu to save the drawing permanently.

// TODO:
// Break lines when the mouse is repressed.
// Smooth / compress lines. (Mouse pixel jitter)
// Option for the drawing to disappear when the camera changes.
// Serialize and Load methods.
// Undo / Redo.
// Color (property window).


(function () {
    // Depends on the CIRCLE widget
    "use strict";

    var DRAWING = 0;
    // Active means highlighted.
    var ACTIVE = 1;
    var DRAG = 2;
    var WAITING = 3;


    function PencilWidget (layer, newFlag) {
        if (layer == null) {
            return;
        }

        var self = this;
        this.Dialog = new SAM.Dialog(function () {self.DialogApplyCallback();});
        // Customize dialog for a pencil.
        this.Dialog.Title.text('Pencil Annotation Editor');
        this.Dialog.Body.css({'margin':'1em 2em'});
        // Color
        this.Dialog.ColorDiv =
            $('<div>')
            .appendTo(this.Dialog.Body)
            .css({'display':'table-row'});
        this.Dialog.ColorLabel =
            $('<div>')
            .appendTo(this.Dialog.ColorDiv)
            .text("Color:")
            .css({'display':'table-cell',
                  'text-align': 'left'});
        this.Dialog.ColorInput =
            $('<input type="color">')
            .appendTo(this.Dialog.ColorDiv)
            .val('#30ff00')
            .css({'display':'table-cell'});

        // Line Width
        this.Dialog.LineWidthDiv =
            $('<div>')
            .appendTo(this.Dialog.Body)
            .css({'display':'table-row'});
        this.Dialog.LineWidthLabel =
            $('<div>')
            .appendTo(this.Dialog.LineWidthDiv)
            .text("Line Width:")
            .css({'display':'table-cell',
                  'text-align': 'left'});
        this.Dialog.LineWidthInput =
            $('<input type="number">')
            .appendTo(this.Dialog.LineWidthDiv)
            .css({'display':'table-cell'})
            .keypress(function(event) { return event.keyCode != 13; });

        this.LineWidth = 0;
        if (localStorage.PencilWidgetDefaults) {
            var defaults = JSON.parse(localStorage.PencilWidgetDefaults);
            if (defaults.Color) {
                this.Dialog.ColorInput.val(SAM.ConvertColorToHex(defaults.Color));
            }
            if (defaults.LineWidth) {
                this.LineWidth = defaults.LineWidth;
                this.Dialog.LineWidthInput.val(this.LineWidth);
            }
        }

        this.Layer = layer;
        this.Popup = new SAM.WidgetPopup(this);
        this.Layer.AddWidget(this);

        var self = this;
        this.Shapes = new SAM.ShapeGroup();
        this.SetStateToDrawing();

        if ( ! newFlag) {
            this.State = WAITING;
            this.Layer.GetCanvasDiv().css({'cursor':'default'});
        }

        // Lets save the zoom level (sort of).
        // Load will overwrite this for existing annotations.
        // This will allow us to expand annotations into notes.
        this.CreationCamera = layer.GetCamera().Serialize();
    }

    PencilWidget.prototype.SetStateToDrawing = function() {
        this.State = DRAWING;
        // When drawing, the cursor is enough indication.
        // We keep the lines the normal color. Yellow is too hard to see.
        this.Shapes.SetActive(false);
        this.Popup.Hide();
        this.Layer.GetCanvasDiv().css(
            {'cursor':'url('+SAM.ImagePathUrl+'Pencil-icon.png) 0 24,crosshair'});
        this.Layer.EventuallyDraw();
    }

    PencilWidget.prototype.Draw = function(view) {
        this.Shapes.Draw(view);
    }

    PencilWidget.prototype.Serialize = function() {
        var obj = new Object();
        obj.type = "pencil";
        obj.shapes = [];
        for (var i = 0; i < this.Shapes.GetNumberOfShapes(); ++i) {
            // NOTE: Assumes shape is a Polyline.
            var shape = this.Shapes.GetShape(i);
            var points = [];
            for (var j = 0; j < shape.Points.length; ++j) {
                points.push([shape.Points[j][0], shape.Points[j][1]]);
            }
            obj.shapes.push(points);
            obj.outlinecolor = shape.OutlineColor;
            obj.linewidth = shape.LineWidth;
        }
        obj.creation_camera = this.CreationCamera;

        return obj;
    }

    // Load a widget from a json object (origin MongoDB).
    PencilWidget.prototype.Load = function(obj) {
        this.LineWidth = parseFloat(obj.linewidth);
        if (obj.linewidth) {
            this.LineWidth = parseFloat(obj.linewidth);
        }
        var outlineColor = this.Dialog.ColorInput.val();
        if (obj.outlinecolor) {
            outlineColor[0] = parseFloat(obj.outlinecolor[0]);
            outlineColor[1] = parseFloat(obj.outlinecolor[1]);
            outlineColor[2] = parseFloat(obj.outlinecolor[2]);
        }
        for(var n=0; n < obj.shapes.length; n++){
            var points = obj.shapes[n];
            var shape = new SAM.Polyline();
            shape.SetOutlineColor(outlineColor);
            shape.FixedSize = false;
            shape.LineWidth = this.LineWidth;
            this.Shapes.AddShape(shape);
            for (var m = 0; m < points.length; ++m) {
                shape.Points[m] = [points[m][0], points[m][1]];
            }
            shape.UpdateBuffers(this.Layer.AnnotationView);
        }

        // How zoomed in was the view when the annotation was created.
        if (obj.view_height !== undefined) {
            this.CreationCamera = obj.creation_camera;
        }
    }

    PencilWidget.prototype.Deactivate = function() {
        this.Popup.StartHideTimer();
        this.Layer.GetCanvasDiv().css({'cursor':'default'});
        this.Layer.DeactivateWidget(this);
        this.State = WAITING;
        this.Shapes.SetActive(false);
        if (this.DeactivateCallback) {
            this.DeactivateCallback();
        }
        this.Layer.EventuallyDraw();
    }

    PencilWidget.prototype.HandleKeyDown = function(event) {
        if ( this.State == DRAWING) {
            // escape key (or space or enter) to turn off drawing
            if (event.keyCode == 27 || event.keyCode == 32 || event.keyCode == 13) {
                this.Deactivate();
                return false;
            }
        }
    }

    // Change the line width with the wheel.
    PencilWidget.prototype.HandleMouseWheel = function(event) {
        if ( this.State == DRAWING ||
             this.State == ACTIVE) {
            if (this.Shapes.GetNumberOfShapes() < 0) { return; }
            var tmp = 0;

            if (event.deltaY) {
                tmp = event.deltaY;
            } else if (event.wheelDelta) {
                tmp = event.wheelDelta;
            }

            var minWidth = 1.0 / this.Layer.GetPixelsPerUnit();

            // Wheel event seems to be in increments of 3.
            // depreciated mousewheel had increments of 120....
            var lineWidth = this.Shapes.GetLineWidth();
            lineWidth = lineWidth || minWidth;
            if (tmp > 0) {
                lineWidth *= 1.1;
            } else if (tmp < 0) {
                lineWidth /= 1.1;
            }
            if (lineWidth <= minWidth) {
                lineWidth = 0.0;
            }
            this.Dialog.LineWidthInput.val(lineWidth);
            this.Shapes.SetLineWidth(lineWidth);
            this.Shapes.UpdateBuffers(this.Layer.AnnotationView);

            this.Layer.EventuallyDraw();
            return false;
        }
        return true;
    }

    PencilWidget.prototype.HandleMouseDown = function(event) {
        var x = event.offsetX;
        var y = event.offsetY;

        if (event.which == 1) {
            if (this.State == DRAWING) {
                // Start drawing.
                var shape = new SAM.Polyline();
                //shape.OutlineColor = [0.9, 1.0, 0.0];
                shape.OutlineColor = [0.0, 0.0, 0.0];
                shape.SetOutlineColor(this.Dialog.ColorInput.val());
                shape.FixedSize = false;
                shape.LineWidth = 0;
                shape.LineWidth = this.Shapes.GetLineWidth();
                this.Shapes.AddShape(shape);

                var pt = this.Layer.GetCamera().ConvertPointViewerToWorld(x,y);
                shape.Points.push([pt[0], pt[1]]); // avoid same reference.
            }
            if (this.State == ACTIVE) {
                // Anticipate dragging (might be double click)
                var cam = this.Layer.GetCamera();
                this.LastMouse = cam.ConvertPointViewerToWorld(x, y);
            }
        }
    }

    PencilWidget.prototype.HandleMouseUp = function(event) {
        if (event.which == 3) {
            // Right mouse was pressed.
            // Pop up the properties dialog.
            this.ShowPropertiesDialog();
            return false;
        }
        // Middle mouse deactivates the widget.
        if (event.which == 2) {
            // Middle mouse was pressed.
            this.Deactivate();
            return false;
        }

        if (this.State == DRAG) {
            // Set the origin back to zero (put it explicitely in points).
            this.Shapes.ResetOrigin();
            this.State = ACTIVE;
        }

        // A stroke has just been finished.
        var last = this.Shapes.GetNumberOfShapes() - 1;
        if (this.State == DRAWING && 
            event.which == 1 && last >= 0) {
            var spacing = this.Layer.GetCamera().GetSpacing();
            // NOTE: This assume that the shapes are polylines.
            //this.Decimate(this.Shapes.GetShape(last), spacing);
            this.Shapes.GetShape(last).Decimate(spacing);
            if (window.SA) {SA.RecordState();}
        }
        return false;
    }

    PencilWidget.prototype.HandleDoubleClick = function(event) {
        if (this.State == DRAWING) {
            this.Deactivate();
            return false;
        } 
        if (this.State == ACTIVE) {
            this.SetStateToDrawing();
            return false;
        }
        return true;
    }

    PencilWidget.prototype.HandleMouseMove = function(event) {
        var x = event.offsetX;
        var y = event.offsetY;

        if (event.which == 1 && this.State == DRAWING) {
            var last = this.Shapes.GetNumberOfShapes() - 1;
            var shape = this.Shapes.GetShape(last);
            var pt = this.Layer.GetCamera().ConvertPointViewerToWorld(x,y);
            shape.Points.push([pt[0], pt[1]]); // avoid same reference.
            shape.UpdateBuffers(this.Layer.AnnotationView);
            if (SAM.NotesWidget) { SAM.NotesWidget.MarkAsModified(); } // Hack
            this.Layer.EventuallyDraw();
            return false;
        }

        if (this.State == ACTIVE &&
            event.which == 0) {
            // Deactivate
            this.SetActive(this.CheckActive(event));
            return false;
        }

        if (this.State == ACTIVE && event.which == 1) {
            this.State = DRAG;
        }

        if (this.State == DRAG) {
            // Drag
            this.State = DRAG;
            this.Popup.Hide();
            var cam = this.Layer.GetCamera();
            var mouseWorld = cam.ConvertPointViewerToWorld(x, y);
            var origin = this.Shapes.GetOrigin();
            origin[0] += mouseWorld[0] - this.LastMouse[0];
            origin[1] += mouseWorld[1] - this.LastMouse[1];
            this.Shapes.SetOrigin(origin);
            this.LastMouse = mouseWorld;
            this.Layer.EventuallyDraw();
            return false;
        }
    }

    // This also shows the popup if it is not visible already.
    PencilWidget.prototype.PlacePopup = function () {
        var pt = this.Shapes.FindPopupPoint(this.Layer.GetCamera());
        if ( ! pt) { return; }
        pt = this.Layer.GetCamera().ConvertPointWorldToViewer(pt[0], pt[1]);

        pt[0] += 20;
        pt[1] -= 10;

        this.Popup.Show(pt[0],pt[1]);
    }

    PencilWidget.prototype.CheckActive = function(event) {
        if (this.State == DRAWING) { return true; }
        if (this.Shapes.GetNumberOfShapes() == 0) { return false; }

        var x = event.offsetX;
        var y = event.offsetY;
        var pt = this.Layer.GetCamera().ConvertPointViewerToWorld(x,y);

        var width = this.Shapes.GetLineWidth();
        // Tolerance: 5 screen pixels.
        var minWidth = 10.0 / this.Layer.GetPixelsPerUnit();
        if (width < minWidth) { width = minWidth;}

        var flag = this.Shapes.PointOnShape(pt, width);
        if (this.State == ACTIVE && !flag) {
            this.SetActive(flag);
        } else if (this.State == WAITING && flag) {
            this.PlacePopup();
            this.SetActive(flag);
        }
        return flag;
    }

    // Setting to active always puts state into "active".
    // It can move to other states and stay active.
    PencilWidget.prototype.SetActive = function(flag) {
        if (flag == this.GetActive()) { return; }
        if (flag) {
            this.Layer.ActivateWidget(this);
            this.State = ACTIVE;
            this.Shapes.SetActive(true);
            this.PlacePopup();
            this.Layer.EventuallyDraw();
        } else {
            if (this.State != ACTIVE) {
                // Not active.  Do nothing.
                return;
            }
            this.Deactivate();
            this.Layer.DeactivateWidget(this);
        }
    }

    PencilWidget.prototype.GetActive = function() {
        return this.State != WAITING;
    }

    PencilWidget.prototype.RemoveFromLayer = function() {
        if (this.Layer) {
            this.Layer.RemoveWidget(this);
        }
        this.Layer = null;
    }

    // Can we bind the dialog apply callback to an objects method?
    var DIALOG_SELF
    PencilWidget.prototype.ShowPropertiesDialog = function () {
        this.Dialog.ColorInput.val(SAM.ConvertColorToHex(this.Shapes.GetOutlineColor()));
        this.Dialog.LineWidthInput.val((this.Shapes.GetLineWidth()).toFixed(2));

        this.Dialog.Show(true);
    }

    PencilWidget.prototype.DialogApplyCallback = function() {
        var hexcolor = this.Dialog.ColorInput.val();
        this.LineWidth = parseFloat(this.Dialog.LineWidthInput.val());
        this.Shapes.SetOutlineColor(hexcolor);
        this.Shapes.SetLineWidth(parseFloat(this.Dialog.LineWidthInput.val()));
        this.Shapes.UpdateBuffers(this.Layer.AnnotationView);
        this.SetActive(false);
        if (window.SA) {SA.RecordState();}
        this.Layer.EventuallyDraw();

        localStorage.PencilWidgetDefaults = JSON.stringify({Color: hexcolor,
                                                            LineWidth: this.LineWidth});
        if (SAM.NotesWidget) { SAM.NotesWidget.MarkAsModified(); } // Hack
    }

    /*
    // The real problem is aliasing.  Line is jagged with high frequency sampling artifacts.
    // Pass in the spacing as a hint to get rid of aliasing.
    PencilWidget.prototype.Decimate = function(shape, spacing) {
        // Keep looping over the line removing points until the line does not change.
        var modified = true;
        while (modified) {
            modified = false;
            var newPoints = [];
            newPoints.push(shape.Points[0]);
            // Window of four points.
            var i = 3;
            while (i < shape.Points.length) {
                var p0 = shape.Points[i];
                var p1 = shape.Points[i-1];
                var p2 = shape.Points[i-2];
                var p3 = shape.Points[i-3];
                // Compute the average of the center two.
                var cx = (p1[0] + p2[0]) * 0.5;
                var cy = (p1[1] + p2[1]) * 0.5;
                // Find the perendicular normal.
                var nx = (p0[1] - p3[1]);
                var ny = -(p0[0] - p3[0]);
                var mag = Math.sqrt(nx*nx + ny*ny);
                nx = nx / mag;
                ny = ny / mag;
                mag = Math.abs(nx*(cx-shape.Points[i-3][0]) + ny*(cy-shape.Points[i-3][1]));
                // Mag metric does not distinguish between line and a stroke that double backs on itself.
                // Make sure the two point being merged are between the outer points 0 and 3.
                var dir1 = (p0[0]-p1[0])*(p3[0]-p1[0]) + (p0[1]-p1[1])*(p3[1]-p1[1]);
                var dir2 = (p0[0]-p2[0])*(p3[0]-p2[0]) + (p0[1]-p2[1])*(p3[1]-p2[1]);
                if (mag < spacing && dir1 < 0.0 && dir2 < 0.0) {
                    // Replace the two points with their average.
                    newPoints.push([cx, cy]);
                    modified = true;
                    // Skip the next point the window will have one old merged point,
                    // but that is ok because it is just used as reference and not altered.
                    i += 2;
                } else {
                    //  No modification.  Just move the window one.
                    newPoints.push(shape.Points[i-2]);
                    ++i;
                }
            }
            // Copy the remaing point / 2 points
            i = i-2;
            while (i < shape.Points.length) {
                newPoints.push(shape.Points[i]);
                ++i;
            }
            shape.Points = newPoints;
        }

        shape.UpdateBuffers(this.Layer.AnnotationView);
    }
    */

    SAM.PencilWidget = PencilWidget;

})();
