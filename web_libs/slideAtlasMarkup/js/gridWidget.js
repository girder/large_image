
(function () {
    "use strict";

    var NEW = 0;
    var WAITING = 3; // The normal (resting) state.
    var ACTIVE = 4; // Mouse is over the widget and it is receiving events.
    var PROPERTIES_DIALOG = 5; // Properties dialog is up

    var DRAG = 6;
    var DRAG_LEFT = 7;
    var DRAG_RIGHT = 8;
    var DRAG_TOP = 9;
    var DRAG_BOTTOM = 10;
    var ROTATE = 11;
    // Worry about corners later.

    function Grid() {
        SAM.Shape.call(this);
        // Dimension of grid bin
        this.BinWidth = 20.0;
        this.BinHeight = 20.0;
        // Number of grid bins in x and y
        this.Dimensions = [10,8];
        this.Orientation = 0; // Angle with respect to x axis ?
        this.Origin = [10000,10000]; // middle.
        this.OutlineColor = [0,0,0];
        this.PointBuffer = [];
        this.ActiveIndex = undefined;
    };

    Grid.prototype = new SAM.Shape();

    Grid.prototype.destructor=function() {
        // Get rid of the buffers?
    };

    Grid.prototype.UpdateBuffers = function(view) {
        // TODO: Having a single poly line for a shape is to simple.
        // Add cell arrays.
        this.PointBuffer = [];

        // Matrix is computed by the draw method in Shape superclass.
        // TODO: Used to detect first initialization.
        // Get this out of this method.
        this.Matrix = mat4.create();
        mat4.identity(this.Matrix);
        //mat4.rotateZ(this.Matrix, this.Orientation / 180.0 * 3.14159);

        if (this.Dimensions[0] < 1 || this.Dimensions[1] < 1 ||
            this.BinWidth <= 0.0 || this.BinHeight <= 0.0) {
            return;
        }

        var totalWidth = this.BinWidth * this.Dimensions[0];
        var totalHeight = this.BinHeight * this.Dimensions[1];
        var halfWidth = totalWidth / 2;
        var halfHeight = totalHeight / 2;

        // Draw all of the x polylines.
        var x = this.Dimensions[1]%2 ? 0 : totalWidth;
        var y = 0;
        this.PointBuffer.push(x-halfWidth);
        this.PointBuffer.push(y-halfHeight);
        this.PointBuffer.push(0.0);

        for (var i = 0; i < this.Dimensions[1]; ++i) {
            //shuttle back and forth.
            x = x ? 0 : totalWidth;
            this.PointBuffer.push(x-halfWidth);
            this.PointBuffer.push(y-halfHeight);
            this.PointBuffer.push(0.0);
            y += this.BinHeight;
            this.PointBuffer.push(x-halfWidth);
            this.PointBuffer.push(y-halfHeight);
            this.PointBuffer.push(0.0);
        }
        //shuttle back and forth.
        x = x ? 0 : totalWidth;
        this.PointBuffer.push(x-halfWidth);
        this.PointBuffer.push(y-halfHeight);
        this.PointBuffer.push(0.0);

        // Draw all of the y lines.
        for (var i = 0; i < this.Dimensions[0]; ++i) {
            //shuttle up and down.
            y = y ? 0 : totalHeight;
            this.PointBuffer.push(x-halfWidth);
            this.PointBuffer.push(y-halfHeight);
            this.PointBuffer.push(0.0);
            x += this.BinWidth;
            this.PointBuffer.push(x-halfWidth);
            this.PointBuffer.push(y-halfHeight);
            this.PointBuffer.push(0.0);
        }
        y = y ? 0 : totalHeight;
        this.PointBuffer.push(x-halfWidth);
        this.PointBuffer.push(y-halfHeight);
        this.PointBuffer.push(0.0);
    };


    function GridWidget (layer, newFlag) {
        var self = this;
        this.Dialog = new SAM.Dialog(function () {self.DialogApplyCallback();});
        // Customize dialog for a circle.
        this.Dialog.Title.text('Grid Annotation Editor');

        // Grid Size
        // X
        this.Dialog.BinWidthDiv =
            $('<div>')
            .appendTo(this.Dialog.Body)
            .css({'display':'table-row'});
        this.Dialog.BinWidthLabel =
            $('<div>')
            .appendTo(this.Dialog.BinWidthDiv)
            .text("Bin Width:")
            .css({'display':'table-cell',
                  'text-align': 'left'});
        this.Dialog.BinWidthInput =
            $('<input>')
            .appendTo(this.Dialog.BinWidthDiv)
            .css({'display':'table-cell'})
            .keypress(function(event) { return event.keyCode != 13; });
        // Y
        this.Dialog.BinHeightDiv =
            $('<div>')
            .appendTo(this.Dialog.Body)
            .css({'display':'table-row'});
        this.Dialog.BinHeightLabel =
            $('<div>')
            .appendTo(this.Dialog.BinHeightDiv)
            .text("Bin Height:")
            .css({'display':'table-cell',
                  'text-align': 'left'});
        this.Dialog.BinHeightInput =
            $('<input>')
            .appendTo(this.Dialog.BinHeightDiv)
            .css({'display':'table-cell'})
            .keypress(function(event) { return event.keyCode != 13; });

        // Orientation
        this.Dialog.RotationDiv =
            $('<div>')
            .appendTo(this.Dialog.Body)
            .css({'display':'table-row'});
        this.Dialog.RotationLabel =
            $('<div>')
            .appendTo(this.Dialog.RotationDiv)
            .text("Rotation:")
            .css({'display':'table-cell',
                  'text-align': 'left'});
        this.Dialog.RotationInput =
            $('<input>')
            .appendTo(this.Dialog.RotationDiv)
            .css({'display':'table-cell'})
            .keypress(function(event) { return event.keyCode != 13; });

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

        this.Tolerance = 0.05;
        if (SAM.MOBILE_DEVICE) {
            this.Tolerance = 0.1;
        }

        if (layer === null) {
            return;
        }

        // Lets save the zoom level (sort of).
        // Load will overwrite this for existing annotations.
        // This will allow us to expand annotations into notes.
        this.CreationCamera = layer.GetCamera().Serialize();

        this.Layer = layer;
        this.Popup = new SAM.WidgetPopup(this);
        var cam = layer.AnnotationView.Camera;
        var viewport = layer.AnnotationView.Viewport;
        this.Grid = new Grid();
        this.Grid.Origin = [0,0];
        this.Grid.OutlineColor = [0.0,0.0,0.0];
        this.Grid.SetOutlineColor('#0A0F7A');
        // Get the default bin size from the layer scale bar.
        if (layer.ScaleWidget) {
            this.Grid.BinWidth = layer.ScaleWidget.LengthWorld;
        } else {
            this.Grid.BinWidth = 30*cam.Height/viewport[3];
        }
        this.Grid.BinHeight = this.Grid.BinWidth;
        this.Grid.LineWidth = 2.0*cam.Height/viewport[3];
        this.Grid.FixedSize = false;

        var width = 0.8 * viewport[2] / layer.GetPixelsPerUnit();
        this.Grid.Dimensions[0] = Math.floor(width / this.Grid.BinWidth);
        var height = 0.8 * viewport[3] / layer.GetPixelsPerUnit();
        this.Grid.Dimensions[1] = Math.floor(height / this.Grid.BinHeight);
        this.Grid.UpdateBuffers(this.Layer.AnnotationView);

        this.Text = new SAM.Text();
        // Shallow copy is dangerous
        this.Text.Position = this.Grid.Origin;
        this.Text.String = SAM.DistanceToString(this.Grid.BinWidth*0.25e-6);
        this.Text.Color = [0.0, 0.0, 0.5];
        this.Text.Anchor = [0,0];
        this.Text.UpdateBuffers(this.Layer.AnnotationView);

        // Get default properties.
        if (localStorage.GridWidgetDefaults) {
            var defaults = JSON.parse(localStorage.GridWidgetDefaults);
            if (defaults.Color) {
                this.Dialog.ColorInput.val(SAM.ConvertColorToHex(defaults.Color));
                this.Grid.SetOutlineColor(this.Dialog.ColorInput.val());
            }
            if (defaults.LineWidth != undefined) {
                this.Dialog.LineWidthInput.val(defaults.LineWidth);
                this.Grid.LineWidth == defaults.LineWidth;
            }
        }

        this.Layer.AddWidget(this);

        this.State = WAITING;

    }


    // sign specifies which corner is origin.
    // gx, gy is the point in grid pixel coordinates offset from the corner.
    GridWidget.prototype.ComputeCorner = function(xSign, ySign, gx, gy) {
        // Pick the upper left most corner to display the grid size text.
        var xRadius = this.Grid.BinWidth * this.Grid.Dimensions[0] / 2;
        var yRadius = this.Grid.BinHeight * this.Grid.Dimensions[1] / 2;
        xRadius += gx;
        yRadius += gy;
        var x = this.Grid.Origin[0];
        var y = this.Grid.Origin[1];
        // Choose the corner from 0 to 90 degrees in the window.
        var roll = (this.Layer.GetCamera().GetRotation()-
                    this.Grid.Orientation) / 90; // range 0-4
        roll = Math.round(roll);
        // Modulo that works with negative numbers;
        roll = ((roll % 4) + 4) % 4;
        var c = Math.cos(3.14156* this.Grid.Orientation / 180.0);
        var s = Math.sin(3.14156* this.Grid.Orientation / 180.0);
        var dx , dy;
        if (roll == 0) {
            dx =  xSign*xRadius;
            dy =  ySign*yRadius;
        } else if (roll == 3) {
            dx =  xSign*xRadius;
            dy = -ySign*yRadius;
        } else if (roll == 2) {
            dx = -xSign*xRadius;
            dy = -ySign*yRadius;
        } else if (roll == 1) {
            dx = -xSign*xRadius;
            dy =  ySign*yRadius;
        }
        x = x + c*dx + s*dy;
        y = y + c*dy - s*dx;

        return [x,y];
    }

    GridWidget.prototype.Draw = function(view) {
        this.Grid.Draw(view);

        // Corner in grid pixel coordinates.
        var x = - (this.Grid.BinWidth * this.Grid.Dimensions[0] / 2);
        var y = - (this.Grid.BinHeight * this.Grid.Dimensions[1] / 2);
        this.Text.Anchor = [0,20];
        this.Text.Orientation = (this.Grid.Orientation -
                                 this.Layer.GetCamera().GetRotation());
        // Modulo that works with negative numbers;
        this.Text.Orientation = ((this.Text.Orientation % 360) + 360) % 360;
        // Do not draw text upside down.
        if (this.Text.Orientation > 90 && this.Text.Orientation < 270) {
            this.Text.Orientation -= 180.0;
            this.Text.Anchor = [this.Text.PixelBounds[1],0];
            //x += this.Text.PixelBounds[1]; // wrong units (want world
            //pixels , this is screen pixels).
        }
        // Convert to world Coordinates.
        var radians = this.Grid.Orientation * Math.PI / 180;
        var c = Math.cos(radians);
        var s = Math.sin(radians);
        var wx = c*x + s*y;
        var wy = c*y - s*x;
        this.Text.Position = [this.Grid.Origin[0]+wx,this.Grid.Origin[1]+wy];

        this.Text.Draw(view);
    };

    // This needs to be put in the layer.
    //GridWidget.prototype.RemoveFromViewer = function() {
    //    if (this.Viewer) {
    //        this.Viewer.RemoveWidget(this);
    //    }
    //};

    GridWidget.prototype.PasteCallback = function(data, mouseWorldPt, camera) {
        this.Load(data);
        // Keep the pasted grid from rotating when the camera changes.
        var dr = this.Layer.GetCamera().GetRotation() -
        camera.GetRotation();
        this.Grid.Orientation += dr;
        // Place the widget over the mouse.
        // This would be better as an argument.
        this.Grid.Origin = [mouseWorldPt[0], mouseWorldPt[1]];
        this.Text.Position = [mouseWorldPt[0], mouseWorldPt[1]];

        this.Layer.EventuallyDraw();
    };

    GridWidget.prototype.Serialize = function() {
        if(this.Grid === undefined){ return null; }
        var obj = {};
        obj.type = "grid";
        obj.origin = this.Grid.Origin;
        obj.outlinecolor = this.Grid.OutlineColor;
        obj.bin_width = this.Grid.BinWidth;
        obj.bin_height = this.Grid.BinHeight;
        obj.dimensions = this.Grid.Dimensions;
        obj.orientation = this.Grid.Orientation;
        obj.linewidth = this.Grid.LineWidth;
        obj.creation_camera = this.CreationCamera;
        return obj;
    };

    // Load a widget from a json object (origin MongoDB).
    GridWidget.prototype.Load = function(obj) {
        this.Grid.Origin[0] = parseFloat(obj.origin[0]);
        this.Grid.Origin[1] = parseFloat(obj.origin[1]);
        this.Grid.OutlineColor[0] = parseFloat(obj.outlinecolor[0]);
        this.Grid.OutlineColor[1] = parseFloat(obj.outlinecolor[1]);
        this.Grid.OutlineColor[2] = parseFloat(obj.outlinecolor[2]);
        if (obj.width)  { this.Grid.BinWidth = parseFloat(obj.width);}
        if (obj.height) {this.Grid.BinHeight = parseFloat(obj.height);}
        if (obj.bin_width)  { this.Grid.BinWidth = parseFloat(obj.bin_width);}
        if (obj.bin_height) {this.Grid.BinHeight = parseFloat(obj.bin_height);}
        this.Grid.Dimensions[0] = parseInt(obj.dimensions[0]);
        this.Grid.Dimensions[1] = parseInt(obj.dimensions[1]);
        this.Grid.Orientation = parseFloat(obj.orientation);
        this.Grid.LineWidth = parseFloat(obj.linewidth);
        this.Grid.FixedSize = false;
        this.Grid.UpdateBuffers(this.Layer.AnnotationView);

        this.Text.String = SAM.DistanceToString(this.Grid.BinWidth*0.25e-6);
        // Shallow copy is dangerous
        this.Text.Position = this.Grid.Origin;
        this.Text.UpdateBuffers(this.Layer.AnnotationView);

        // How zoomed in was the view when the annotation was created.
        if (obj.creation_camera !== undefined) {
            this.CreationCamera = obj.CreationCamera;
        }
    };

    GridWidget.prototype.HandleKeyPress = function(keyCode, shift) {
        // The dialog consumes all key events.
        if (this.State == PROPERTIES_DIALOG) {
            return false;
        }

        // Copy
        if (event.keyCode == 67 && event.ctrlKey) {
            //control-c for copy
            //The extra identifier is not needed for widgets, but will be
            // needed if we have some other object on the clipboard.
            // The camera is needed so grid does not rotate when pasting in
            // another stack section.
            var clip = {Type:"GridWidget", 
                        Data: this.Serialize(), 
                        Camera: this.Layer.GetCamera().Serialize()};
            localStorage.ClipBoard = JSON.stringify(clip);
            return false;
        }

        return true;
    };

    GridWidget.prototype.HandleDoubleClick = function(event) {
        return true;
    };

    GridWidget.prototype.HandleMouseDown = function(event) {
        if (event.which != 1) {
            return true;
        }
        var cam = this.Layer.GetCamera();
        this.DragLast = cam.ConvertPointViewerToWorld(event.offsetX, event.offsetY);
        return false;
    };

    // returns false when it is finished doing its work.
    GridWidget.prototype.HandleMouseUp = function(event) {
        this.SetActive(false);
        if (window.SA) {SA.RecordState();}

        return true;
    };

    // Orientation is a pain,  we need a world to shape transformation.
    GridWidget.prototype.HandleMouseMove = function(event) {
        if (event.which == 1) {
            var cam = this.Layer.GetCamera();
            var world =
                cam.ConvertPointViewerToWorld(event.offsetX, event.offsetY);
            var dx, dy;
            if (this.State == DRAG) {
                dx = world[0] - this.DragLast[0];
                dy = world[1] - this.DragLast[1];
                this.DragLast = world;
                this.Grid.Origin[0] += dx;
                this.Grid.Origin[1] += dy;
            } else {
                // convert mouse from world to Grid coordinate system.
                dx = world[0] - this.Grid.Origin[0];
                dy = world[1] - this.Grid.Origin[1];
                var c = Math.cos(3.14156* this.Grid.Orientation / 180.0);
                var s = Math.sin(3.14156* this.Grid.Orientation / 180.0);
                var x = c*dx - s*dy;
                var y = c*dy + s*dx;
                // convert from shape to integer grid indexes.
                x = (0.5*this.Grid.Dimensions[0]) + (x / this.Grid.BinWidth);
                y = (0.5*this.Grid.Dimensions[1]) + (y / this.Grid.BinHeight);
                var ix = Math.round(x);
                var iy = Math.round(y);
                // Change grid dimemsions
                dx = dy = 0;
                var changed = false;
                if (this.State == DRAG_RIGHT) {
                    dx = ix - this.Grid.Dimensions[0];
                    if (dx) {
                        this.Grid.Dimensions[0] = ix;
                        // Compute the change in the center point origin.
                        dx = 0.5 * dx * this.Grid.BinWidth;
                        changed = true;
                    }
                } else if (this.State == DRAG_LEFT) {
                    if (ix) {
                        this.Grid.Dimensions[0] -= ix;
                        // Compute the change in the center point origin.
                        dx = 0.5 * ix * this.Grid.BinWidth;
                        changed = true;
                    }
                } else if (this.State == DRAG_BOTTOM) {
                    dy = iy - this.Grid.Dimensions[1];
                    if (dy) {
                        this.Grid.Dimensions[1] = iy;
                        // Compute the change in the center point origin.
                        dy = 0.5 * dy * this.Grid.BinHeight;
                        changed = true;
                    }
                } else if (this.State == DRAG_TOP) {
                    if (iy) {
                        this.Grid.Dimensions[1] -= iy;
                        // Compute the change in the center point origin.
                        dy = 0.5 * iy * this.Grid.BinHeight;
                        changed = true;
                    }
                }
                if (changed) {
                    // Rotate the translation and apply to the center.
                    x = c*dx + s*dy;
                    y = c*dy - s*dx;
                    this.Grid.Origin[0] += x;
                    this.Grid.Origin[1] += y;
                    this.Grid.UpdateBuffers(this.Layer.AnnotationView);
                }
            }
            this.Layer.EventuallyDraw();
            return
        }

        if (event.which == 0) {
            // Update the active state if theuser is not interacting.
            this.SetActive(this.CheckActive(event));
        }

        return true;
    };


    GridWidget.prototype.HandleMouseWheel = function(event) {
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
                    this.Grid.Length = this.Grid.Length * ratio;
                }
                if(event.ctrlKey) {
                    this.Grid.BinWidth = this.Grid.BinWidth * ratio;
                }
                if(!event.shiftKey && !event.ctrlKey) {
                    this.Grid.Orientation = this.Grid.Orientation + 3 * direction;
                 }

                this.Grid.UpdateBuffers(this.Layer.AnnotationView);
                this.PlacePopup();
                this.Layer.EventuallyDraw();
            }
        }
        */
    };


    GridWidget.prototype.HandleTouchPan = function(event) {
        /*
          w0 = this.Viewer.ConvertPointViewerToWorld(EVENT_MANAGER.LastMouseX,
          EVENT_MANAGER.LastMouseY);
          w1 = this.Viewer.ConvertPointViewerToWorld(event.offsetX,event.offsetY);

          // This is the translation.
          var dx = w1[0] - w0[0];
          var dy = w1[1] - w0[1];

          this.Grid.Origin[0] += dx;
          this.Grid.Origin[1] += dy;
          this.Layer.EventuallyDraw();
        */
        return true;
    };


    GridWidget.prototype.HandleTouchPinch = function(event) {
        //this.Grid.UpdateBuffers(this.Layer.AnnotationView);
        //this.Layer.EventuallyDraw();
        return true;
    };

    GridWidget.prototype.HandleTouchEnd = function(event) {
        this.SetActive(false);
    };


    GridWidget.prototype.CheckActive = function(event) {
        var x,y;
        if (this.Grid.FixedSize) {
            x = event.offsetX;
            y = event.offsetY;
            pixelSize = 1;
        } else {
            x = event.worldX;
            y = event.worldY;
        }
        x = x - this.Grid.Origin[0];
        y = y - this.Grid.Origin[1];
        // Rotate to grid.
        var c = Math.cos(3.14156* this.Grid.Orientation / 180.0);
        var s = Math.sin(3.14156* this.Grid.Orientation / 180.0);
        var rx = c*x - s*y;
        var ry = c*y + s*x;

        // Convert to grid coordinates (0 -> dims)
        x = (0.5*this.Grid.Dimensions[0]) + (rx / this.Grid.BinWidth);
        y = (0.5*this.Grid.Dimensions[1]) + (ry / this.Grid.BinHeight);
        var ix = Math.round(x);
        var iy = Math.round(y);
        if (ix < 0 || ix > this.Grid.Dimensions[0] ||
            iy < 0 || iy > this.Grid.Dimensions[1]) {
            this.SetActive(false);
            return false;
        }

        // x,y get the residual in pixels.
        x = (x - ix) * this.Grid.BinWidth;
        y = (y - iy) * this.Grid.BinHeight;

        // Compute the screen pixel size for tollerance.
        var tolerance = 5.0 / this.Layer.GetPixelsPerUnit();

        if (Math.abs(x) < tolerance || Math.abs(y) < tolerance) {
            this.ActiveIndex =[ix,iy];
            return true;
        }

        return false;
    };

    // Multiple active states. Active state is a bit confusing.
    GridWidget.prototype.GetActive = function() {
        if (this.State == WAITING) {
            return false;
        }
        return true;
    };


    GridWidget.prototype.Deactivate = function() {
        this.Layer.AnnotationView.CanvasDiv.css({'cursor':'default'});
        this.Popup.StartHideTimer();
        this.State = WAITING;
        this.Grid.Active = false;
        this.Layer.DeactivateWidget(this);
        if (this.DeactivateCallback) {
            this.DeactivateCallback();
        }
        this.Layer.EventuallyDraw();
    };

    // Setting to active always puts state into "active".
    // It can move to other states and stay active.
    GridWidget.prototype.SetActive = function(flag) {

        if (flag) {
            this.State = ACTIVE;
            this.Grid.Active = true;

            if ( ! this.ActiveIndex) {
                console.log("No active index");
                return;
            }
            if (this.ActiveIndex[0] == 0) {
                this.State = DRAG_LEFT;
                this.Layer.AnnotationView.CanvasDiv.css({'cursor':'col-resize'});
            } else if (this.ActiveIndex[0] == this.Grid.Dimensions[0]) {
                this.State = DRAG_RIGHT;
                this.Layer.AnnotationView.CanvasDiv.css({'cursor':'col-resize'});
            } else if (this.ActiveIndex[1] == 0) {
                this.State = DRAG_TOP;
                this.Layer.AnnotationView.CanvasDiv.css({'cursor':'row-resize'});
            } else if (this.ActiveIndex[1] == this.Grid.Dimensions[1]) {
                this.State = DRAG_BOTTOM;
                this.Layer.AnnotationView.CanvasDiv.css({'cursor':'row-resize'});
            } else {
                this.State = DRAG;
                this.Layer.AnnotationView.CanvasDiv.css({'cursor':'move'});
            }

            // Compute the location for the pop up and show it.
            this.PlacePopup();
        } else {
            this.Deactivate();
        }
        this.Layer.EventuallyDraw();
    };


    // This also shows the popup if it is not visible already.
    GridWidget.prototype.PlacePopup = function () {
        // Compute corner has its angle backwards.  I do not see how this works.
        var pt = this.ComputeCorner(1, -1, 0, 0);
        var cam = this.Layer.GetCamera();
        pt = cam.ConvertPointWorldToViewer(pt[0], pt[1]);
        this.Popup.Show(pt[0]+10,pt[1]-30);
    };

    // Can we bind the dialog apply callback to an objects method?
    var DIALOG_SELF;

    GridWidget.prototype.ShowPropertiesDialog = function () {
        this.Dialog.ColorInput.val(SAM.ConvertColorToHex(this.Grid.OutlineColor));
        this.Dialog.LineWidthInput.val((this.Grid.LineWidth).toFixed(2));
        // convert 40x scan pixels into meters
        this.Dialog.BinWidthInput.val(SAM.DistanceToString(this.Grid.BinWidth*0.25e-6));
        this.Dialog.BinHeightInput.val(SAM.DistanceToString(this.Grid.BinHeight*0.25e-6));
        this.Dialog.RotationInput.val(this.Grid.Orientation);

        this.Dialog.Show(true);
    };

    GridWidget.prototype.DialogApplyCallback = function() {
        var hexcolor = this.Dialog.ColorInput.val();
        this.Grid.SetOutlineColor(hexcolor);
        this.Grid.LineWidth = parseFloat(this.Dialog.LineWidthInput.val());
        this.Grid.BinWidth = SAM.StringToDistance(this.Dialog.BinWidthInput.val())*4e6;
        this.Grid.BinHeight = SAM.StringToDistance(this.Dialog.BinHeightInput.val())*4e6;
        this.Grid.Orientation = parseFloat(this.Dialog.RotationInput.val());
        this.Grid.UpdateBuffers(this.Layer.AnnotationView);
        this.SetActive(false);

        this.Text.String = SAM.DistanceToString(this.Grid.BinWidth*0.25e-6);
        this.Text.UpdateBuffers(this.Layer.AnnotationView);

        if (window.SA) {SA.RecordState();}
        this.Layer.EventuallyDraw();

        localStorage.GridWidgetDefaults = JSON.stringify({Color: hexcolor, LineWidth: this.Grid.LineWidth});
    };

    SAM.GridWidget = GridWidget;

})();
