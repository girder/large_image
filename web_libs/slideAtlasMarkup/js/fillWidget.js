//==============================================================================
// Segmentation / fill.  But should I change it into a contour at the end?

(function () {
    "use strict";

    var FILL_WIDGET_DRAWING = 0;
    var FILL_WIDGET_ACTIVE = 1;
    var FILL_WIDGET_WAITING = 2;


    function FillWidget (viewer, newFlag) {
        if (viewer == null) {
            return;
        }

        // I am not sure what to do for the fill because
        // I plan to change it to a contour.

        this.Dialog = new SAM.Dialog(this);
        // Customize dialog for a lasso.
        this.Dialog.Title.text('Fill Annotation Editor');
        this.Dialog.Body.css({'margin':'1em 2em'});
        // Color
        this.Dialog.ColorDiv =
            $('<div>')
            .appendTo(this.Dialog.Body)
            .addClass("sa-view-fill-div");
        this.Dialog.ColorLabel =
            $('<div>')
            .appendTo(this.Dialog.ColorDiv)
            .text("Color:")
            .addClass("sa-view-fill-label");
        this.Dialog.ColorInput =
            $('<input type="color">')
            .appendTo(this.Dialog.ColorDiv)
            .val('#30ff00')
            .addClass("sa-view-fill-input");

        // Line Width
        this.Dialog.LineWidthDiv =
            $('<div>')
            .appendTo(this.Dialog.Body)
            .addClass("sa-view-fill-div");
        this.Dialog.LineWidthLabel =
            $('<div>')
            .appendTo(this.Dialog.LineWidthDiv)
            .text("Line Width:")
            .addClass("sa-view-fill-label");
        this.Dialog.LineWidthInput =
            $('<input type="number">')
            .appendTo(this.Dialog.LineWidthDiv)
            .addClass("sa-view-fill-input")
            .keypress(function(event) { return event.keyCode != 13; });

        this.Popup = new SAM.WidgetPopup(this);
        this.Viewer = viewer;
        this.Viewer.AddWidget(this);

        this.Cursor = $('<img>').appendTo('body')
            .addClass("sa-view-fill-cursor")
            .attr('type','image')
            .attr('src',SAM.ImagePathUrl+"brush1.jpg");

        var self = this;
        // I am trying to stop images from getting move events and displaying a circle/slash.
        // This did not work.  preventDefault did not either.
        //this.Cursor.mousedown(function (event) {self.HandleMouseDown(event);})
        //this.Cursor.mousemove(function (event) {self.HandleMouseMove(event);})
        //this.Cursor.mouseup(function (event) {self.HandleMouseUp(event);})
        //.preventDefault();

        this.ActiveCenter = [0,0];

        this.State = FILL_WIDGET_DRAWING;
        if ( ! newFlag) {
            this.State = FILL_WIDGET_WAITING;
        }

        // Lets save the zoom level (sort of).
        // Load will overwrite this for existing annotations.
        // This will allow us to expand annotations into notes.
        this.CreationCamera = viewer.GetCamera().Serialize;
    }

    // This is expensive, so initialize explicitely outside the constructor.
    FillWidget.prototype.Initialize = function(view) {
        // Now for the segmentation initialization.
        this.Segmentation = new Segmentation(this.Viewer);
    }

    FillWidget.prototype.Draw = function(view) {
        this.Segmentation.ImageAnnotation.Draw(view);
    }

    // I do not know what we are saving yet.
    FillWidget.prototype.Serialize = function() {
        /*
          var obj = new Object();
          obj.type = "pencil";
          obj.shapes = [];
          for (var i = 0; i < this.Shapes.length; ++i) {
          var shape = this.Shapes[i];
          var points = [];
          for (var j = 0; j < shape.Points.length; ++j) {
          points.push([shape.Points[j][0], shape.Points[j][1]]);
          }
          obj.shapes.push(points);
          }
          obj.creation_camera = this.CreationCamera;

          return obj;
        */
    }

    // Load a widget from a json object (origin MongoDB).
    FillWidget.prototype.Load = function(obj) {
        /*
          for(var n=0; n < obj.shapes.length; n++){
          var points = obj.shapes[n];
          var shape = new SAM.Polyline();
          shape.OutlineColor = [0.9, 1.0, 0.0];
          shape.FixedSize = false;
          shape.LineWidth = 0;
          this.Shapes.push(shape);
          for (var m = 0; m < points.length; ++m) {
          shape.Points[m] = [points[m][0], points[m][1]];
          }
          shape.UpdateBuffers(this.Viewer.AnnotationView);
          }

          // How zoomed in was the view when the annotation was created.
          if (obj.view_height !== undefined) {
          this.CreationCamera = obj.creation_camera;
          }
        */
    }

    FillWidget.prototype.HandleKeyPress = function(keyCode, shift) {
        return false;
    }

    FillWidget.prototype.Deactivate = function() {
        this.Popup.StartHideTimer();
        this.Viewer.DeactivateWidget(this);
        this.State = FILL_WIDGET_WAITING;
        if (this.DeactivateCallback) {
            this.DeactivateCallback();
        }
        eventuallyRender();
    }

    FillWidget.prototype.HandleMouseDown = function(event) {
        var x = this.Viewer.MouseX;
        var y = this.Viewer.MouseY;

        if (event.which == 1) {
            var ptWorld = this.Viewer.ConvertPointViewerToWorld(x, y);
            this.Cursor.attr('src',SAM.ImagePathUrl+"brush1.jpg");
            this.Cursor.show();
            this.Segmentation.AddPositive(ptWorld);
        }
        if (event.which == 3) {
            var ptWorld = this.Viewer.ConvertPointViewerToWorld(x, y);
            this.Cursor.attr('src',SAM.ImagePathUrl+"eraser1.jpg");
            this.Cursor.show();
            this.Segmentation.AddNegative(ptWorld);
        }
    }

    FillWidget.prototype.HandleMouseUp = function(event) {
        // Middle mouse deactivates the widget.
        if (event.which == 2) {
            // Middle mouse was pressed.
            this.Deactivate();
        }

        // A stroke has just been finished.
        if (event.which == 1 || event.which == 3) {
            this.Cursor.hide();
            this.Segmentation.Update();
            this.Segmentation.Draw();
            eventuallyRender();
        }
    }

    FillWidget.prototype.HandleDoubleClick = function(event) {
    }

    FillWidget.prototype.HandleMouseMove = function(event) {
        var x = this.Viewer.MouseX;
        var y = this.Viewer.MouseY;

        // Move the paint bucket icon to follow the mouse.
        this.Cursor.css({'left': (x+4), 'top': (y-32)});

        if (this.Viewer.MouseDown == true && this.State == FILL_WIDGET_DRAWING) {
            if (event.which == 1 ) {
                var ptWorld = this.Viewer.ConvertPointViewerToWorld(x, y);
                this.Segmentation.AddPositive(ptWorld);
            }
            if (event.which == 3 ) {
                var ptWorld = this.Viewer.ConvertPointViewerToWorld(x, y);
                this.Segmentation.AddNegative(ptWorld);
            }

            return;
        }
    }

    FillWidget.prototype.ComputeActiveCenter = function() {
        /*
          var count = 0;
          var sx = 0.0;
          var sy = 0.0;
          for (var i = 0; i < this.Shapes.length; ++i) {
          var shape = this.Shapes[i];
          var points = [];
          for (var j = 0; j < shape.Points.length; ++j) {
          sx += shape.Points[j][0];
          sy += shape.Points[j][1];
          }
          count += shape.Points.length;
          }

          this.ActiveCenter[0] = sx / count;
          this.ActiveCenter[1] = sy / count;
        */
    }

    //This also shows the popup if it is not visible already.
    FillWidget.prototype.PlacePopup = function () {
        /*
          var pt = this.Viewer.ConvertPointWorldToViewer(this.ActiveCenter[0],
          this.ActiveCenter[1]);
          pt[0] += 40;
          pt[1] -= 40;
          this.Popup.Show(pt[0],pt[1]);
        */
    }

    FillWidget.prototype.CheckActive = function(event) {
        /*
          if (this.State == FILL_WIDGET_DRAWING) { return; }

          var pt = this.Viewer.ConvertPointWorldToViewer(this.ActiveCenter[0],
          this.ActiveCenter[1]);

          var dx = this.Viewer.MouseX - pt[0];
          var dy = this.Viewer.MouseY - pt[1];
          var active = false;

          if (dx*dx + dy*dy < 1600) {
          active = true;
          }
          this.SetActive(active);
          return active;
        */
    }

    FillWidget.prototype.GetActive = function() {
        return false;
    }

    // Setting to active always puts state into "active".
    // It can move to other states and stay active.
    FillWidget.prototype.SetActive = function(flag) {
        if (flag) {
            this.Viewer.ActivateWidget(this);
            this.State = FILL_WIDGET_ACTIVE;
            for (var i = 0; i < this.Shapes.length; ++i) {
                this.Shapes[i].Active = true;
            }
            this.PlacePopup();
            eventuallyRender();
        } else {
            this.Deactivate();
            this.Viewer.DeactivateWidget(this);
        }
    }

    FillWidget.prototype.RemoveFromViewer = function() {
        if (this.Viewer) {
            this.Viewer.RemoveWidget();
        }
    }

    // Can we bind the dialog apply callback to an objects method?
    var FILL_WIDGET_DIALOG_SELF
    FillWidget.prototype.ShowPropertiesDialog = function () {
        this.Dialog.ColorInput.val(SAM.ConvertColorToHex(this.Shapes[0].OutlineColor));
        this.Dialog.LineWidthInput.val((this.Shapes[0].LineWidth).toFixed(2));

        this.Dialog.Show(true);
    }


    FillWidget.prototype.DialogApplyCallback = function() {
        var hexcolor = this.Dialog.ColorInput.val();
        for (var i = 0; i < this.Shapes.length; ++i) {
            this.Shapes[i].SetOutlineColor(hexcolor);
            this.Shapes[i].LineWidth = parseFloat(this.Dialog.LineWidthInput.val());
            this.Shapes[i].UpdateBuffers(this.Viewer.AnnotationView);
        }
        this.SetActive(false);
        if (window.SA) {SA.RecordState();}
        eventuallyRender();
    }

    SAM.FillWidget = FillWidget;

})();



