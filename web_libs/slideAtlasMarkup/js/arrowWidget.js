//==============================================================================
// This widget will first be setup to define an arrow.
// Layer will forward events to the arrow.
// TODO: I need to indicate that the base of the arrow has different active
// state than the rest.


(function () {
    "use strict";


    // The arrow has just been created and is following the mouse.
    // I have to differentiate from ARROW_WIDGET_DRAG because
    // dragging while just created cannot be relative.  It places the tip on the mouse.
    var ARROW_WIDGET_NEW = 0;
    var ARROW_WIDGET_DRAG = 1; // The whole arrow is being dragged.
    var ARROW_WIDGET_DRAG_TIP = 2;
    var ARROW_WIDGET_DRAG_TAIL = 3;
    var ARROW_WIDGET_WAITING = 4; // The normal (resting) state.
    var ARROW_WIDGET_ACTIVE = 5; // Mouse is over the widget and it is receiving events.
    var ARROW_WIDGET_PROPERTIES_DIALOG = 6; // Properties dialog is up


    // We might get rid of the new flag by passing in a null layer.
    function ArrowWidget (layer, newFlag) {
        if (layer == null) {
            return null;
        }
        this.Layer = layer;

        // Wait to create this until the first move event.
        this.Shape = new Arrow();
        this.Shape.Origin = [0,0];
        this.Shape.SetFillColor([0.0, 0.0, 0.0]);
        this.Shape.OutlineColor = [1.0, 1.0, 1.0];
        this.Shape.Length = 50;
        this.Shape.Width = 8;
        // Note: If the user clicks before the mouse is in the
        // canvas, this will behave odd.
        this.TipPosition = [0,0];
        this.TipOffset = [0,0];

        if (layer) {
            layer.AddWidget(this);
            if (newFlag && layer) {
                this.State = ARROW_WIDGET_NEW;
                this.Layer.ActivateWidget(this);
                return;
            }
        }

        this.State = ARROW_WIDGET_WAITING;
    }

    ArrowWidget.prototype.Draw = function(view) {
        this.Shape.Draw(view);
    }


    ArrowWidget.prototype.RemoveFromLayer = function() {
        if (this.Layer) {
            this.Layer.RemoveWidget(this);
        }
    }

    ArrowWidget.prototype.Serialize = function() {
        if(this.Shape === undefined) {
            return null;
        }

        var obj = new Object();
        obj.type = "arrow";
        obj.origin = this.Shape.Origin
        obj.fillcolor = this.Shape.FillColor;
        obj.outlinecolor = this.Shape.OutlineColor;
        obj.length = this.Shape.Length;
        obj.width = this.Shape.Width;
        obj.orientation = this.Shape.Orientation;
        obj.fixedsize = this.Shape.FixedSize;
        obj.fixedorientation = this.Shape.FixedOrientation;

        return obj;
    }

    // Load a widget from a json object (origin MongoDB).
    ArrowWidget.prototype.Load = function(obj) {
        this.Shape.Origin = [parseFloat(obj.origin[0]), parseFloat(obj.origin[1])];
        this.Shape.FillColor = [parseFloat(obj.fillcolor[0]),parseFloat(obj.fillcolor[1]),parseFloat(obj.fillcolor[2])];
        this.Shape.OutlineColor = [parseFloat(obj.outlinecolor[0]),parseFloat(obj.outlinecolor[1]),parseFloat(obj.outlinecolor[2])];
        this.Shape.Length = parseFloat(obj.length);
        this.Shape.Width = parseFloat(obj.width);
        this.Shape.Orientation = parseFloat(obj.orientation);

        if (obj.fixedsize === undefined) {
            this.Shape.FixedSize = true;
        } else {
            this.Shape.FixedSize = (obj.fixedsize == "true");
        }

        if (obj.fixedorientation === undefined) {
            this.Shape.FixedOrientation = true;
        } else {
            this.Shape.FixedOrientation = (obj.fixedorientation == "true");
        }

        this.Shape.UpdateBuffers(this.Layer.AnnotationView);
    }

    // When we toggle fixed size, we have to convert the length of the arrow
    // between viewer and world.
    ArrowWidget.prototype.SetFixedSize = function(fixedSizeFlag) {
        if (this.Shape.FixedSize == fixedSizeFlag) {
            return;
        }
        var pixelsPerUnit = this.Layer.GetPixelsPerUnit();

        if (fixedSizeFlag) {
            // Convert length from world to viewer.
            this.Shape.Length *= pixelsPerUnit;
            this.Shape.Width *= pixelsPerUnit;
        } else {
            this.Shape.Length /= pixelsPerUnit;
            this.Shape.Width /= pixelsPerUnit;
        }
        this.Shape.FixedSize = fixedSizeFlag;
        this.Shape.UpdateBuffers();
        eventuallyRender();
    }


    ArrowWidget.prototype.HandleKeyPress = function(keyCode, shift) {
    }

    ArrowWidget.prototype.HandleMouseDown = function(event) {
        if (event.which != 1)
        {
            return;
        }
        if (this.State == ARROW_WIDGET_NEW) {
            this.TipPosition = [this.Layer.MouseX, this.Layer.MouseY];
            this.State = ARROW_WIDGET_DRAG_TAIL;
        }
        if (this.State == ARROW_WIDGET_ACTIVE) {
            if (this.ActiveTail) {
                this.TipPosition = this.Layer.ConvertPointWorldToViewer(this.Shape.Origin[0], this.Shape.Origin[1]);
                this.State = ARROW_WIDGET_DRAG_TAIL;
            } else {
                var tipPosition = this.Layer.ConvertPointWorldToViewer(this.Shape.Origin[0], this.Shape.Origin[1]);
                this.TipOffset[0] = tipPosition[0] - this.Layer.MouseX;
                this.TipOffset[1] = tipPosition[1] - this.Layer.MouseY;
                this.State = ARROW_WIDGET_DRAG;
            }
        }
    }

    // returns false when it is finished doing its work.
    ArrowWidget.prototype.HandleMouseUp = function(event) {
        if (this.State == ARROW_WIDGET_ACTIVE && event.which == 3) {
            // Right mouse was pressed.
            // Pop up the properties dialog.
            // Which one should we popup?
            // Add a ShowProperties method to the widget. (With the magic of javascript).
            this.State = ARROW_WIDGET_PROPERTIES_DIALOG;
            this.ShowPropertiesDialog();
        } else if (this.State != ARROW_WIDGET_PROPERTIES_DIALOG) {
            this.SetActive(false);
        }
    }

    ArrowWidget.prototype.HandleMouseMove = function(event) {
        var x = this.Layer.MouseX;
        var y = this.Layer.MouseY;

        if (this.Layer.MouseDown == false && this.State == ARROW_WIDGET_ACTIVE) {
            this.CheckActive(event);
            return;
        }

        if (this.State == ARROW_WIDGET_NEW || this.State == ARROW_WIDGET_DRAG) {
            var viewport = this.Layer.GetViewport();
            this.Shape.Origin = this.Layer.ConvertPointViewerToWorld(x+this.TipOffset[0], y+this.TipOffset[1]);
            eventuallyRender();
        }

        if (this.State == ARROW_WIDGET_DRAG_TAIL) {
            var dx = x-this.TipPosition[0];
            var dy = y-this.TipPosition[1];
            if ( ! this.Shape.FixedSize) {
                var pixelsPerUnit = this.Layer.GetPixelsPerUnit();
                dx /= pixelsPerUnit;
                dy /= pixelsPerUnit;
            }
            this.Shape.Length = Math.sqrt(dx*dx + dy*dy);
            this.Shape.Orientation = Math.atan2(dy, dx) * 180.0 / Math.PI;
            this.Shape.UpdateBuffers();
            eventuallyRender();
        }

        if (this.State == ARROW_WIDGET_WAITING) {
            this.CheckActive(event);
        }
    }

    ArrowWidget.prototype.CheckActive = function(event) {
        var viewport = this.Layer.GetViewport();
        var cam = this.Layer.MainView.Camera;
        var m = cam.Matrix;
        // Compute tip point in screen coordinates.
        var x = this.Shape.Origin[0];
        var y = this.Shape.Origin[1];
        // Convert from world coordinate to view (-1->1);
        var h = (x*m[3] + y*m[7] + m[15]);
        var xNew = (x*m[0] + y*m[4] + m[12]) / h;
        var yNew = (x*m[1] + y*m[5] + m[13]) / h;
        // Convert from view to screen pixel coordinates.
        xNew = (xNew + 1.0)*0.5*viewport[2] + viewport[0];
        yNew = (yNew + 1.0)*0.5*viewport[3] + viewport[1];

        // Use this point as the origin.
        x = this.Layer.MouseX - xNew;
        y = this.Layer.MouseY - yNew;
        // Rotate so arrow lies along the x axis.
        var tmp = this.Shape.Orientation * Math.PI / 180.0;
        var ct = Math.cos(tmp);
        var st = Math.sin(tmp);
        xNew = x*ct + y*st;
        yNew = -x*st + y*ct;

        var length = this.Shape.Length;
        var halfWidth = this.Shape.Width / 2.0;
        if ( ! this.Shape.FixedSize) {
            var pixelsPerUnit = this.Layer.GetPixelsPerUnit();
            length *= pixelsPerUnit;
            halfWidth *= pixelsPerUnit;
        }

        this.ActiveTail = false;
        if (xNew > 0.0 && xNew < length && yNew > -halfWidth && yNew < halfWidth) {
            this.SetActive(true);
            // Save the position along the arrow to decide which drag behavior to use.
            if (xNew > length - halfWidth) {
                this.ActiveTail = true;
            }
            return true;
        } else {
            this.SetActive(false);
            return false;
        }
    }

    // We have three states this widget is active.
    // First created and folloing the mouse (actually two, head or tail following). Color nbot active.
    // Active because mouse is over the arrow.  Color of arrow set to active.
    // Active because the properties dialog is up. (This is how dialog know which widget is being edited).
    ArrowWidget.prototype.GetActive = function() {
        if (this.State == ARROW_WIDGET_WAITING) {
            return false;
        }
        return true;
    }

    ArrowWidget.prototype.SetActive = function(flag) {
        if (flag == this.GetActive()) {
            return;
        }

        if (flag) {
            this.State = ARROW_WIDGET_ACTIVE;
            this.Shape.Active = true;
            this.Layer.ActivateWidget(this);
            eventuallyRender();
        } else {
            this.State = ARROW_WIDGET_WAITING;
            this.Shape.Active = false;
            this.Layer.DeactivateWidget(this);
            eventuallyRender();
        }
    }

    // Can we bind the dialog apply callback to an objects method?
    var ARROW_WIDGET_DIALOG_SELF;
    ArrowWidget.prototype.ShowPropertiesDialog = function () {
        //var fs = document.getElementById("ArrowFixedSize");
        //fs.checked = this.Shape.FixedSize;

        var color = document.getElementById("arrowcolor");
        color.value = SAM.ConvertColorToHex(this.Shape.FillColor);

        var lengthLabel = document.getElementById("ArrowLength");
        //if (fs.checked) {
        //  lengthLabel.innerHTML = "Length: " + (this.Shape.Length).toFixed(2) + " pixels";
        //} else {
        //  lengthLabel.innerHTML = "Length: " + (this.Shape.Length).toFixed(2) + " units";
        //}

        ARROW_WIDGET_DIALOG_SELF = this;
        $("#arrow-properties-dialog").dialog("open");
    }

    // I need this because old schemes cannot use "Load"
    ArrowWidget.prototype.SetColor = function (hexColor) {
        this.Shape.SetFillColor(hexColor);
        eventuallyRender();
    }

    function ArrowPropertyDialogApply() {
        var widget = ARROW_WIDGET_DIALOG_SELF;
        if ( ! widget) {
            return;
        }

        var hexcolor = document.getElementById("arrowcolor").value;
        //var fixedSizeFlag = document.getElementById("ArrowFixedSize").checked;
        widget.Shape.SetFillColor(hexcolor);
        if (widget != null) {
            widget.SetActive(false);
            //widget.SetFixedSize(fixedSizeFlag);
        }
        eventuallyRender();
    }

    function ArrowPropertyDialogCancel() {
        var widget = ARROW_WIDGET_DIALOG_SELF;
        if (widget != null) {
            widget.SetActive(false);
        }
    }

    function ArrowPropertyDialogDelete() {
        var widget = ARROW_WIDGET_DIALOG_SELF;
        if (widget != null) {
            this.Layer.ActiveWidget = null;
            // We need to remove an item from a list.
            // shape list and widget list.
            widget.RemoveFromLayer();
            eventuallyRender();
        }
    }


    SAM.ArrowWidget = ArrowWidget;

})();




