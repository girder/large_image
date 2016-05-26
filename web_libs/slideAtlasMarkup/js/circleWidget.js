
(function () {
    "use strict";

    //==============================================================================
    // Mouse down defined the center.
    // Drag defines the radius.


    // The circle has just been created and is following the mouse.
    // I can probably merge this state with drag. (mouse up vs down though)
    var CIRCLE_WIDGET_NEW_HIDDEN = 0;
    var CIRCLE_WIDGET_NEW_DRAGGING = 1;
    var CIRCLE_WIDGET_DRAG = 2; // The whole arrow is being dragged.
    var CIRCLE_WIDGET_DRAG_RADIUS = 3;
    var CIRCLE_WIDGET_WAITING = 4; // The normal (resting) state.
    var CIRCLE_WIDGET_ACTIVE = 5; // Mouse is over the widget and it is receiving events.
    var CIRCLE_WIDGET_PROPERTIES_DIALOG = 6; // Properties dialog is up

    function CircleWidget (layer, newFlag) {
        var self = this;
        this.Dialog = new SAM.Dialog(function () {self.DialogApplyCallback();});
        // Customize dialog for a circle.
        this.Dialog.Title.text('Circle Annotation Editor');
        this.Dialog.Body.css({'margin':'1em 2em'});
        // Color
        this.Dialog.ColorDiv =
            $('<div>')
            .css({'height':'24px'})
            .appendTo(this.Dialog.Body)
            .addClass("sa-view-annotation-modal-div");
        this.Dialog.ColorLabel =
            $('<div>')
            .appendTo(this.Dialog.ColorDiv)
            .text("Color:")
            .addClass("sa-view-annotation-modal-input-label");
        this.Dialog.ColorInput =
            $('<input type="color">')
            .appendTo(this.Dialog.ColorDiv)
            .val('#30ff00')
            .addClass("sa-view-annotation-modal-input");

        // Line Width
        this.Dialog.LineWidthDiv =
            $('<div>')
            .appendTo(this.Dialog.Body)
            .addClass("sa-view-annotation-modal-div");
        this.Dialog.LineWidthLabel =
            $('<div>')
            .appendTo(this.Dialog.LineWidthDiv)
            .text("Line Width:")
            .addClass("sa-view-annotation-modal-input-label");
        this.Dialog.LineWidthInput =
            $('<input type="number">')
            .appendTo(this.Dialog.LineWidthDiv)
            .addClass("sa-view-annotation-modal-input")
            .keypress(function(event) { return event.keyCode != 13; });

        // Area
        this.Dialog.AreaDiv =
            $('<div>')
            .appendTo(this.Dialog.Body)
            .addClass("sa-view-annotation-modal-div");
        this.Dialog.AreaLabel =
            $('<div>')
            .appendTo(this.Dialog.AreaDiv)
            .text("Area:")
            .addClass("sa-view-annotation-modal-input-label");
        this.Dialog.Area =
            $('<div>')
            .appendTo(this.Dialog.AreaDiv)
            .addClass("sa-view-annotation-modal-input");

        // Get default properties.
        if (localStorage.CircleWidgetDefaults) {
            var defaults = JSON.parse(localStorage.CircleWidgetDefaults);
            if (defaults.Color) {
                this.Dialog.ColorInput.val(SAM.ConvertColorToHex(defaults.Color));
            }
            if (defaults.LineWidth) {
                this.Dialog.LineWidthInput.val(defaults.LineWidth);
            }
        }

        this.Tolerance = 0.05;
        if (SAM.MOBILE_DEVICE) {
            this.Tolerance = 0.1;
        }

        if (layer == null) {
            return;
        }

        // Lets save the zoom level (sort of).
        // Load will overwrite this for existing annotations.
        // This will allow us to expand annotations into notes.
        this.CreationCamera = layer.GetCamera().Serialize();

        this.Layer = layer;
        this.Popup = new SAM.WidgetPopup(this);
        var cam = layer.GetCamera();
        var viewport = layer.GetViewport();
        this.Shape = new SAM.Circle();
        this.Shape.Origin = [0,0];
        this.Shape.OutlineColor = [0.0,0.0,0.0];
        this.Shape.SetOutlineColor(this.Dialog.ColorInput.val());
        this.Shape.Radius = 50*cam.Height/viewport[3];
        this.Shape.LineWidth = 5.0*cam.Height/viewport[3];
        this.Shape.FixedSize = false;

        this.Layer.AddWidget(this);

        // Note: If the user clicks before the mouse is in the
        // canvas, this will behave odd.

        if (newFlag) {
            this.State = CIRCLE_WIDGET_NEW_HIDDEN;
            this.Layer.ActivateWidget(this);
            return;
        }

        this.State = CIRCLE_WIDGET_WAITING;
    }

    CircleWidget.prototype.Draw = function(view) {
        if ( this.State != CIRCLE_WIDGET_NEW_HIDDEN) {
            this.Shape.Draw(view);
        }
    }

    // This needs to be put in the Viewer.
    //CircleWidget.prototype.RemoveFromViewer = function() {
    //    if (this.Viewer) {
    //        this.Viewer.RemoveWidget(this);
    //    }
    //}

    //CircleWidget.prototype.PasteCallback = function(data, mouseWorldPt) {
    //    this.Load(data);
    //    // Place the widget over the mouse.
    //    // This would be better as an argument.
    //    this.Shape.Origin = [mouseWorldPt[0], mouseWorldPt[1]];
    //    this.Layer.EventuallyDraw();
    //}

    CircleWidget.prototype.Serialize = function() {
        if(this.Shape === undefined){ return null; }
        var obj = new Object();
        obj.type = "circle";
        obj.origin = this.Shape.Origin;
        obj.outlinecolor = this.Shape.OutlineColor;
        obj.radius = this.Shape.Radius;
        obj.linewidth = this.Shape.LineWidth;
        obj.creation_camera = this.CreationCamera;
        return obj;
    }

    // Load a widget from a json object (origin MongoDB).
    CircleWidget.prototype.Load = function(obj) {
        this.Shape.Origin[0] = parseFloat(obj.origin[0]);
        this.Shape.Origin[1] = parseFloat(obj.origin[1]);
        this.Shape.OutlineColor[0] = parseFloat(obj.outlinecolor[0]);
        this.Shape.OutlineColor[1] = parseFloat(obj.outlinecolor[1]);
        this.Shape.OutlineColor[2] = parseFloat(obj.outlinecolor[2]);
        this.Shape.Radius = parseFloat(obj.radius);
        this.Shape.LineWidth = parseFloat(obj.linewidth);
        this.Shape.FixedSize = false;
        this.Shape.UpdateBuffers(this.Layer.AnnotationView);

        // How zoomed in was the view when the annotation was created.
        if (obj.creation_camera !== undefined) {
            this.CreationCamera = obj.CreationCamera;
        }
    }

    CircleWidget.prototype.HandleMouseWheel = function(event) {
        // TODO: Scale the radius.
        return false;
    }

    CircleWidget.prototype.HandleKeyDown = function(keyCode) {
        // The dialog consumes all key events.
        if (this.State == CIRCLE_WIDGET_PROPERTIES_DIALOG) {
            return false;
        }

        // Copy
        if (event.keyCode == 67 && event.ctrlKey) {
            // control-c for copy
            // The extra identifier is not needed for widgets, but will be
            // needed if we have some other object on the clipboard.
            var clip = {Type:"CircleWidget", Data: this.Serialize()};
            localStorage.ClipBoard = JSON.stringify(clip);
            return false;
        }

        return true;
    }

    CircleWidget.prototype.HandleDoubleClick = function(event) {
        ShowPropertiesDialog();
        return false;
    }

    CircleWidget.prototype.HandleMouseDown = function(event) {
        if (event.which != 1) {
            return false;
        }
        var cam = this.Layer.GetCamera();
        if (this.State == CIRCLE_WIDGET_NEW_DRAGGING) {
            // We need the viewer position of the circle center to drag radius.
            this.OriginViewer =
                cam.ConvertPointWorldToViewer(this.Shape.Origin[0],
                                              this.Shape.Origin[1]);
            this.State = CIRCLE_WIDGET_DRAG_RADIUS;
        }
        if (this.State == CIRCLE_WIDGET_ACTIVE) {
            // Determine behavior from active radius.
            if (this.NormalizedActiveDistance < 0.5) {
                this.State = CIRCLE_WIDGET_DRAG;
            } else {
                this.OriginViewer =
                    cam.ConvertPointWorldToViewer(this.Shape.Origin[0],
                                                  this.Shape.Origin[1]);
                this.State = CIRCLE_WIDGET_DRAG_RADIUS;
            }
        }
        return false;
    }

    // returns false when it is finished doing its work.
    CircleWidget.prototype.HandleMouseUp = function(event) {
        if ( this.State == CIRCLE_WIDGET_DRAG ||
             this.State == CIRCLE_WIDGET_DRAG_RADIUS) {
            this.SetActive(false);
            if (window.SA) {SA.RecordState();}
        }
        return false;
    }

    CircleWidget.prototype.HandleMouseMove = function(event) {
        var x = event.offsetX;
        var y = event.offsetY;

        if (event.which == 0 && this.State == CIRCLE_WIDGET_ACTIVE) {
            this.SetActive(this.CheckActive(event));
            return false;
        }

        var cam = this.Layer.GetCamera();
        if (this.State == CIRCLE_WIDGET_NEW_HIDDEN) {
            this.State = CIRCLE_WIDGET_NEW_DRAGGING;
        }
        if (this.State == CIRCLE_WIDGET_NEW_DRAGGING || this.State == CIRCLE_WIDGET_DRAG) {
            if (SA && SA.notesWidget) {SA.notesWidget.MarkAsModified();} // hack
            this.Shape.Origin = cam.ConvertPointViewerToWorld(x, y);
            this.PlacePopup();
            this.Layer.EventuallyDraw();
        }

        if (this.State == CIRCLE_WIDGET_DRAG_RADIUS) {
            var viewport = this.Layer.GetViewport();
            var cam = this.Layer.GetCamera();
            var dx = x-this.OriginViewer[0];
            var dy = y-this.OriginViewer[1];
            // Change units from pixels to world.
            this.Shape.Radius = Math.sqrt(dx*dx + dy*dy) * cam.Height / viewport[3];
            this.Shape.UpdateBuffers(this.Layer.AnnotationView);
            if (SA && SA.notesWidget) {SA.notesWidget.MarkAsModified();} // hack
            this.PlacePopup();
            this.Layer.EventuallyDraw();
        }

        if (this.State == CIRCLE_WIDGET_WAITING) {
            this.CheckActive(event);
        }
        return false;
    }

    CircleWidget.prototype.HandleTouchPan = function(event) {
        var cam = this.Layer.GetCamera();
        // TODO: Last mouse should net be in layer.
        w0 = cam.ConvertPointViewerToWorld(this.Layer.LastMouseX,
                                           this.Layer.LastMouseY);
        w1 = cam.ConvertPointViewerToWorld(event.offsetX,event.offsetY);

        // This is the translation.
        var dx = w1[0] - w0[0];
        var dy = w1[1] - w0[1];

        this.Shape.Origin[0] += dx;
        this.Shape.Origin[1] += dy;
        this.Layer.EventuallyDraw();
        return false;
    }

    CircleWidget.prototype.HandleTouchPinch = function(event) {
        this.Shape.Radius *= event.PinchScale;
        this.Shape.UpdateBuffers(this.Layer.AnnotationView);
        if (SA && SA.notesWidget) {SA.notesWidget.MarkAsModified();} // hack
        this.Layer.EventuallyDraw();
        return false;
    }

    CircleWidget.prototype.HandleTouchEnd = function(event) {
        this.SetActive(false);
        return false
    }


    CircleWidget.prototype.CheckActive = function(event) {
        if (this.State == CIRCLE_WIDGET_NEW_HIDDEN ||
            this.State == CIRCLE_WIDGET_NEW_DRAGGING) {
            return true;
        }

        var dx = event.offsetX;
        var dy = event.offsetY;

        // change dx and dy to vector from center of circle.
        if (this.FixedSize) {
            dx = event.offsetX - this.Shape.Origin[0];
            dy = event.offsetY - this.Shape.Origin[1];
        } else {
            dx = event.worldX - this.Shape.Origin[0];
            dy = event.worldY - this.Shape.Origin[1];
        }

        var d = Math.sqrt(dx*dx + dy*dy)/this.Shape.Radius;
        var active = false;
        var lineWidth = this.Shape.LineWidth / this.Shape.Radius;
        this.NormalizedActiveDistance = d;

        if (this.Shape.FillColor == undefined) { // Circle
            if ((d < (1.0+ this.Tolerance +lineWidth) && d > (1.0-this.Tolerance)) ||
                d < (this.Tolerance+lineWidth)) {
                active = true;
            }
        } else { // Disk
            if (d < (1.0+this.Tolerance+lineWidth) && d > (this.Tolerance+lineWidth) ||
                d < lineWidth) {
                active = true;
            }
        }

        return active;
    }

    // Multiple active states. Active state is a bit confusing.
    CircleWidget.prototype.GetActive = function() {
        if (this.State == CIRCLE_WIDGET_WAITING) {
            return false;
        }
        return true;
    }

    CircleWidget.prototype.Deactivate = function() {
        // If the circle button is clicked to deactivate the widget before
        // it is placed, I want to delete it. (like cancel). I think this
        // will do the trick.
        if (this.State == CIRCLE_WIDGET_NEW_HIDDEN) {
            this.Layer.RemoveWidget(this);
            return;
        }

        this.Popup.StartHideTimer();
        this.State = CIRCLE_WIDGET_WAITING;
        this.Shape.Active = false;
        this.Layer.DeactivateWidget(this);
        if (this.DeactivateCallback) {
            this.DeactivateCallback();
        }
        this.Layer.EventuallyDraw();
    }

    // Setting to active always puts state into "active".
    // It can move to other states and stay active.
    CircleWidget.prototype.SetActive = function(flag) {
        if (flag == this.GetActive()) {
            return;
        }

        if (flag) {
            this.State = CIRCLE_WIDGET_ACTIVE;
            this.Shape.Active = true;
            this.Layer.ActivateWidget(this);
            this.Layer.EventuallyDraw();
            // Compute the location for the pop up and show it.
            this.PlacePopup();
        } else {
            this.Deactivate();
        }
        this.Layer.EventuallyDraw();
    }


    //This also shows the popup if it is not visible already.
    CircleWidget.prototype.PlacePopup = function () {
        // Compute the location for the pop up and show it.
        var cam = this.Layer.GetCamera();
        var roll = cam.Roll;
        var x = this.Shape.Origin[0] + 0.8 * this.Shape.Radius * (Math.cos(roll) - Math.sin(roll));
        var y = this.Shape.Origin[1] - 0.8 * this.Shape.Radius * (Math.cos(roll) + Math.sin(roll));
        var pt = cam.ConvertPointWorldToViewer(x, y);
        this.Popup.Show(pt[0],pt[1]);
    }

    // Can we bind the dialog apply callback to an objects method?
    var CIRCLE_WIDGET_DIALOG_SELF;
    CircleWidget.prototype.ShowPropertiesDialog = function () {
        this.Dialog.ColorInput.val(SAM.ConvertColorToHex(this.Shape.OutlineColor));

        this.Dialog.LineWidthInput.val((this.Shape.LineWidth).toFixed(2));

        var area = (2.0*Math.PI*this.Shape.Radius*this.Shape.Radius) * 0.25 * 0.25;
        var areaString = "";
        if (this.Shape.FixedSize) {
            areaString += area.toFixed(2);
            areaString += " pixels^2";
        } else {
            if (area > 1000000) {
                areaString += (area/1000000).toFixed(2);
                areaString += " mm^2";
            } else {
                areaString += area.toFixed(2);
                areaString += " um^2";
            }
        }
        this.Dialog.Area.text(areaString);

        this.Dialog.Show(true);
    }

    CircleWidget.prototype.DialogApplyCallback = function() {
        var hexcolor = this.Dialog.ColorInput.val();
        this.Shape.SetOutlineColor(hexcolor);
        this.Shape.LineWidth = parseFloat(this.Dialog.LineWidthInput.val());
        this.Shape.UpdateBuffers(this.Layer.AnnotationView);
        this.SetActive(false);
        if (window.SA) {SA.RecordState();}

        // TODO: See if anything has changed.
        this.Layer.EventuallyDraw();

        localStorage.CircleWidgetDefaults = JSON.stringify({Color: hexcolor, LineWidth: this.Shape.LineWidth});
        if (SA && SA.notesWidget) {SA.notesWidget.MarkAsModified();} // hack
    }


    SAM.CircleWidget = CircleWidget;

})();
