


(function () {
    "use strict";

    var NEW = 0;
    var WAITING = 3; // The normal (resting) state.
    var ACTIVE = 4; // Mouse is over the widget and it is receiving events.
    var PROPERTIES_DIALOG = 5; // Properties dialog is up

    var DRAG = 6;
    var DRAG_LEFT = 7;
    var DRAG_RIGHT = 8;

    // view argument is the main view (needed to get the spacing...)
    // Viewer coordinates.
    // Horizontal or verticle
    function Scale() {
        SAM.Shape.call(this);
        // Dimension of scale element
        this.BinLength = 100.0; // unit length in screen pixels
        this.TickSize = 6; // Screen pixels
        this.NumberOfBins = 1;
        this.Orientation = 0; // 0 or 90
        this.Origin = [10000,10000]; // middle.
        this.OutlineColor = [0,0,0];
        this.PointBuffer = [];
        this.PositionCoordinateSystem = SAM.Shape.VIEWER;
    };

    Scale.prototype = new SAM.Shape();

    Scale.prototype.destructor=function() {
        // Get rid of the buffers?
    };

    Scale.prototype.UpdateBuffers = function(view) {
        // TODO: Having a single poly line for a shape is to simple.
        // Add cell arrays.
        this.PointBuffer = [];

        // Matrix is computed by the draw method in Shape superclass.
        // TODO: Used to detect first initialization.
        // Get this out of this method.
        this.Matrix = mat4.create();
        mat4.identity(this.Matrix);

        // Draw all of the x lines.
        var x = 0;
        var y = this.TickSize;
        this.PointBuffer.push(x);
        this.PointBuffer.push(y);
        this.PointBuffer.push(0.0);
        y = 0;
        this.PointBuffer.push(x);
        this.PointBuffer.push(y);
        this.PointBuffer.push(0.0);

        for (var i = 0; i < this.NumberOfBins; ++i) {
            x += this.BinLength;
            this.PointBuffer.push(x);
            this.PointBuffer.push(y);
            this.PointBuffer.push(0.0);
            y = this.TickSize;
            this.PointBuffer.push(x);
            this.PointBuffer.push(y);
            this.PointBuffer.push(0.0);
            y = 0;
            this.PointBuffer.push(x);
            this.PointBuffer.push(y);
            this.PointBuffer.push(0.0);
        }
    };

    function ScaleWidget (layer) {
        var self = this;

        if (layer === null) {
            return;
        }

        this.Layer = layer;
        this.PixelsPerMeter = 0;
        this.Shape = new Scale();
        this.Shape.OutlineColor = [0.0, 0.0, 0.0];
        this.Shape.Origin = [30,20];
        this.Shape.BinLength = 200;
        this.Shape.FixedSize = true;

        this.Text = new SAM.Text();
        this.Text.PositionCoordinateSystem = SAM.Shape.VIEWER;
        this.Text.Position = [30,5];
        this.Text.String = "";
        this.Text.Color = [0.0, 0.0, 0.0];
        // I want the anchor to be the center of the text.
        // This is a hackl estimate.
        this.Text.Anchor = [20,0];

        this.Update(layer.GetPixelsPerUnit());

        this.State = WAITING;
    }


    // Change the length of the scale based on the camera.
    ScaleWidget.prototype.Update = function() {
        if ( ! this.View) { return;}
        // Compute the number of screen pixels in a meter.
        var scale = Math.round(
            this.View.GetPixelsPerUnit() / this.View.GetMetersPerUnit());
        if (this.PixelsPerMeter == scale) {
            return;
        }
        // Save the scale so we know when to regenerate.
        this.PixelsPerMeter = scale;
        var target = 200; // pixels
        var e = 0;
        // Note: this assumes max bin length is 1 meter.
        var binLengthViewer = this.PixelsPerMeter;
        // keep reducing the length until it is reasonable.
        while (binLengthViewer > target) {
            binLengthViewer = binLengthViewer / 10;
            --e;
        }
        // Now compute the units from e.
        this.Units = "nm";
        var factor = 1e-9;
        if (e >= -6) {
            this.Units = "\xB5m"
            factor = 1e-6;
        }
        if (e >= -3) {
            this.Units = "mm";
            factor = 1e-3;
        }
        if (e >= -2) {
            this.Units = "cm";
            factor = 1e-2;
        }
        if (e >= 0) {
            this.Units = "m";
            factor = 1;
        }
        if (e >= 3) {
            this.Units = "km";
            factor = 1000;
        }
        // Length is set to the viewer pixel length of a tick / unit.
        this.Shape.BinLength = binLengthViewer;
        // Now add bins to get close to the target length.
        this.Shape.NumberOfBins = Math.floor(target / binLengthViewer);
        // compute the length of entire scale bar (units: viewer pixels).
        var scaleLengthViewer = binLengthViewer * this.Shape.NumberOfBins;
        var scaleLengthMeters = scaleLengthViewer / this.PixelsPerMeter;
        // Compute the label.
        // The round should not change the value, only get rid of numerical error.
        var labelNumber = Math.round(scaleLengthMeters / factor);
        this.Label = labelNumber.toString() + this.Units;

        // Save the length of the scale bar in world units.
        // World (highest res image) pixels default to 0.25e-6 meters.
        this.LengthWorld = scaleLengthMeters * 4e6;

        // Update the label text and position
        this.Text.String = this.Label;
        this.Text.UpdateBuffers(this.Layer.AnnotationView);
        this.Text.Position = [this.Shape.Origin[0]+(scaleLengthViewer/2),
                              this.Shape.Origin[1]-15];

        this.Shape.UpdateBuffers(this.Layer.AnnotationView);
    }

    ScaleWidget.prototype.Draw = function(view) {
        // Update the scale if zoom changed.
        this.Update();
        this.Shape.Draw(view);
        this.Text.Draw(view);
    };

    // This needs to be put in the Viewer.
    //ScaleWidget.prototype.RemoveFromViewer = function() {
    //    if (this.Layer) {
    //        this.RemoveWidget(this);
    //    }
    //};

    ScaleWidget.prototype.HandleKeyPress = function(keyCode, shift) {
        return true;
    };

    ScaleWidget.prototype.HandleDoubleClick = function(event) {
        return true;
    };

    ScaleWidget.prototype.HandleMouseDown = function(event) {
        /*
        if (event.which != 1) {
            return true;
        }
        this.DragLast = this.Layer.ConvertPointViewerToWorld(event.offsetX, event.offsetY);
        */
        return false;
    };

    // returns false when it is finished doing its work.
    ScaleWidget.prototype.HandleMouseUp = function(event) {
        /*
        this.SetActive(false);
        if (window.SA) {SA.RecordState();}
        */
        return true;
    };

    // Orientation is a pain,  we need a world to shape transformation.
    ScaleWidget.prototype.HandleMouseMove = function(event) {
        /*
        if (event.which == 1) {
            var world =
                this.Layer.ConvertPointViewerToWorld(event.offsetX, event.offsetY);
            var dx, dy;
            if (this.State == DRAG) {
                dx = world[0] - this.DragLast[0];
                dy = world[1] - this.DragLast[1];
                this.DragLast = world;
                this.Shape.Origin[0] += dx;
                this.Shape.Origin[1] += dy;
            } else {
                // convert mouse from world to Shape coordinate system.
                dx = world[0] - this.Shape.Origin[0];
                dy = world[1] - this.Shape.Origin[1];
                var c = Math.cos(3.14156* this.Shape.Orientation / 180.0);
                var s = Math.sin(3.14156* this.Shape.Orientation / 180.0);
                var x = c*dx - s*dy;
                var y = c*dy + s*dx;
                // convert from shape to integer scale indexes.
                x = (0.5*this.Shape.Dimensions[0]) + (x /
                  this.Shape.Width);
                y = (0.5*this.Shape.Dimensions[1]) + (y /
                  this.Shape.Height);
                var ix = Math.round(x);
                var iy = Math.round(y);
                // Change scale dimemsions
                dx = dy = 0;
                var changed = false;
                if (this.State == DRAG_RIGHT) {
                    dx = ix - this.Shape.Dimensions[0];
                    if (dx) {
                        this.Shape.Dimensions[0] = ix;
                        // Compute the change in the center point origin.
                        dx = 0.5 * dx * this.Shape.Width;
                        changed = true;
                    }
                } else if (this.State == DRAG_LEFT) {
                    if (ix) {
                        this.Shape.Dimensions[0] -= ix;
                        // Compute the change in the center point origin.
                        dx = 0.5 * ix * this.Shape.Width;
                        changed = true;
                    }
                } else if (this.State == DRAG_BOTTOM) {
                    dy = iy - this.Shape.Dimensions[1];
                    if (dy) {
                        this.Shape.Dimensions[1] = iy;
                        // Compute the change in the center point origin.
                        dy = 0.5 * dy * this.Shape.Height;
                        changed = true;
                    }
                } else if (this.State == DRAG_TOP) {
                    if (iy) {
                        this.Shape.Dimensions[1] -= iy;
                        // Compute the change in the center point origin.
                        dy = 0.5 * iy * this.Shape.Height;
                        changed = true;
                    }
                }
                if (changed) {
                    // Rotate the translation and apply to the center.
                    x = c*dx + s*dy;
                    y = c*dy - s*dx;
                    this.Shape.Origin[0] += x;
                    this.Shape.Origin[1] += y;
                    this.Shape.UpdateBuffers(this.Layer.AnnotationView);
                }
            }
            eventuallyRender();
            return
        }

        this.CheckActive(event);
*/
        return true;
    };


    ScaleWidget.prototype.HandleMouseWheel = function(event) {
        /*
        var x = event.offsetX;
        var y = event.offsetY;

        if (this.State == ACTIVE) {
            if(this.NormalizedActiveDistance < 0.5) {
                var ratio = 1.05;
                var direction = 1;
                if(event.wheelDelta < 0) {
                     ratio = 0.95;
                    direction = -1;
                }
                if(event.shiftKey) {
                    this.Shape.BinLength = this.Shape.BinLength * ratio;
                }
                if(event.ctrlKey) {
                    this.Shape.Width = this.Shape.Width * ratio;
                }
                if(!event.shiftKey && !event.ctrlKey) {
                    this.Shape.Orientation = this.Shape.Orientation + 3 * direction;
                 }

                this.Shape.UpdateBuffers(this.Layer.AnnotationView);
                this.PlacePopup();
                eventuallyRender();
            }
        }
        */
    };


    ScaleWidget.prototype.HandleTouchPan = function(event) {
        /*
          w0 = this.Layer.ConvertPointViewerToWorld(EVENT_MANAGER.LastMouseX,
          EVENT_MANAGER.LastMouseY);
          w1 = this.Layer.ConvertPointViewerToWorld(event.offsetX,event.offsetY);

          // This is the translation.
          var dx = w1[0] - w0[0];
          var dy = w1[1] - w0[1];

          this.Shape.Origin[0] += dx;
          this.Shape.Origin[1] += dy;
          eventuallyRender();
        */
        return true;
    };


    ScaleWidget.prototype.HandleTouchPinch = function(event) {
        //this.Shape.UpdateBuffers(this.Layer.AnnotationView);
        //eventuallyRender();
        return true;
    };

    ScaleWidget.prototype.HandleTouchEnd = function(event) {
        this.SetActive(false);
    };


    ScaleWidget.prototype.CheckActive = function(event) {
        /*
        var x,y;
        if (this.Shape.FixedSize) {
            x = event.offsetX;
            y = event.offsetY;
            pixelSize = 1;
        } else {
            x = event.worldX;
            y = event.worldY;
        }
        x = x - this.Shape.Origin[0];
        y = y - this.Shape.Origin[1];
        // Rotate to scale.
        var c = Math.cos(3.14156* this.Shape.Orientation / 180.0);
        var s = Math.sin(3.14156* this.Shape.Orientation / 180.0);
        var rx = c*x - s*y;
        var ry = c*y + s*x;

        // Convert to scale coordinates (0 -> dims)
        x = (0.5*this.Shape.Dimensions[0]) + (rx / this.Shape.Width);
        y = (0.5*this.Shape.Dimensions[1]) + (ry / this.Shape.Height);
        var ix = Math.round(x);
        var iy = Math.round(y);
        if (ix < 0 || ix > this.Shape.Dimensions[0] ||
            iy < 0 || iy > this.Shape.Dimensions[1]) {
            this.SetActive(false);
            return false;
        }

        // x,y get the residual in pixels.
        x = (x - ix) * this.Shape.Width;
        y = (y - iy) * this.Shape.Height;

        // Compute the screen pixel size for tollerance.
        var tolerance = 5.0 / this.Layer.GetPixelsPerUnit();

        if (Math.abs(x) < tolerance || Math.abs(y) < tolerance) {
            this.SetActive(true);
            if (ix == 0) {
                this.State = DRAG_LEFT;
                thisLayer.AnnotationView.CanvasDiv.css({'cursor':'col-resize'});
            } else if (ix == this.Shape.Dimensions[0]) {
                this.State = DRAG_RIGHT;
                this.Layer.AnnotationView.CanvasDiv.css({'cursor':'col-resize'});
            } else if (iy == 0) {
                this.State = DRAG_TOP;
                this.Viewer.AnnotationView.CanvasDiv.css({'cursor':'row-resize'});
            } else if (iy == this.Shape.Dimensions[1]) {
                this.State = DRAG_BOTTOM;
                this.Layer.MainView.CanvasDiv.css({'cursor':'row-resize'});
            } else {
                this.State = DRAG;
                this.Layer.MainView.CanvasDiv.css({'cursor':'move'});
            }
            return true;
        }
        */
        this.SetActive(false);
        return false;
    };

    // Multiple active states. Active state is a bit confusing.
    ScaleWidget.prototype.GetActive = function() {
        if (this.State == WAITING) {
            return false;
        }
        return true;
    };


    ScaleWidget.prototype.Deactivate = function() {
        this.Layer.AnnotationView.CanvasDiv.css({'cursor':'default'});
        this.Popup.StartHideTimer();
        this.State = WAITING;
        this.Shape.Active = false;
        this.Layer.DeactivateWidget(this);
        if (this.DeactivateCallback) {
            this.DeactivateCallback();
        }
        eventuallyRender();
    };

    // Setting to active always puts state into "active".
    // It can move to other states and stay active.
    ScaleWidget.prototype.SetActive = function(flag) {
        if (flag == this.GetActive()) {
            return;
        }

        if (flag) {
            this.State = ACTIVE;
            this.Shape.Active = true;
            this.Layer.ActivateWidget(this);
            eventuallyRender();
            // Compute the location for the pop up and show it.
            this.PlacePopup();
        } else {
            this.Deactivate();
        }
        eventuallyRender();
    };


    SAM.ScaleWidget = ScaleWidget;

})();
