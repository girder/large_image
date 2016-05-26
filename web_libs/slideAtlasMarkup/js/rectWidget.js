
// Since there is already a rectangle widget (for axis aligned rectangle)
// renaming this as Rect, other possible name is OrientedRectangle

(function () {
    // Depends on the CIRCLE widget
    "use strict";

    var NEW = 0;
    var DRAG = 1; // The whole arrow is being dragged.
    var DRAG_RADIUS = 2;
    var WAITING = 3; // The normal (resting) state.
    var ACTIVE = 4; // Mouse is over the widget and it is receiving events.
    var PROPERTIES_DIALOG = 5; // Properties dialog is up


    function Rect() {
        SAM.Shape.call(this);

        this.Width = 20.0;
        this.Length = 50.0;
        this.Radius = 60;
        this.Orientation = 90; // Angle with respect to x axis ?
        this.Origin = [10000,10000]; // Center in world coordinates.
        this.OutlineColor = [0,0,0];
        this.PointBuffer = [];
    }

    Rect.prototype = new SAM.Shape();

    Rect.prototype.destructor=function() {
        // Get rid of the buffers?
    };

    Rect.prototype.UpdateBuffers = function(view) {
        this.PointBuffer = [];

        this.Matrix = mat4.create();
        mat4.identity(this.Matrix);
        mat4.rotateZ(this.Matrix, this.Orientation / 180.0 * 3.14159);

        this.PointBuffer.push(1 *this.Width / 2.0);
        this.PointBuffer.push(1 *this.Length / 2.0);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(-1 *this.Width / 2.0);
        this.PointBuffer.push(1 *this.Length / 2.0);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(-1 *this.Width / 2.0);
        this.PointBuffer.push(-1 *this.Length / 2.0);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(1 *this.Width / 2.0);
        this.PointBuffer.push(-1 *this.Length / 2.0);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(1 *this.Width / 2.0);
        this.PointBuffer.push(1 *this.Length / 2.0);
        this.PointBuffer.push(0.0);
    };



    function RectWidget (viewer, newFlag) {
      this.Dialog = new SAM.Dialog(this);
      // Customize dialog for a circle.
      this.Dialog.Title.text('Rect Annotation Editor');
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

      // Area
      this.Dialog.AreaDiv =
        $('<div>')
          .appendTo(this.Dialog.Body)
          .css({'display':'table-row'});
      this.Dialog.AreaLabel =
        $('<div>')
          .appendTo(this.Dialog.AreaDiv)
          .text("Area:")
          .css({'display':'table-cell',
                'text-align': 'left'});
      this.Dialog.Area =
        $('<div>')
          .appendTo(this.Dialog.AreaDiv)
          .css({'display':'table-cell'});

      // Get default properties.
      if (localStorage.RectWidgetDefaults) {
        var defaults = JSON.parse(localStorage.RectWidgetDefaults);
        if (defaults.Color) {
          this.Dialog.ColorInput.val(SAM.ConvertColorToHex(defaults.Color));
        }
        if (defaults.LineWidth) {
          this.Dialog.LineWidthInput.val(defaults.LineWidth);
        }
      }

      this.Tolerance = 0.05;
      if (SAM.detectMobile()) {
        this.Tolerance = 0.1;
      }

      if (viewer === null) {
        return;
      }

      // Lets save the zoom level (sort of).
      // Load will overwrite this for existing annotations.
      // This will allow us to expand annotations into notes.
      this.CreationCamera = viewer.GetCamera().Serialize();

      this.Viewer = viewer;
      this.Popup = new SAM.WidgetPopup(this);
      var cam = viewer.MainView.Camera;
      var viewport = viewer.MainView.Viewport;
      this.Shape = new Rect();
      this.Shape.Origin = [0,0];
      this.Shape.OutlineColor = [0.0,0.0,0.0];
      this.Shape.SetOutlineColor(this.Dialog.ColorInput.val());
      this.Shape.Length = 50.0*cam.Height/viewport[3];
      this.Shape.Width = 30*cam.Height/viewport[3];
      this.Shape.Radius = 50*cam.Height/viewport[3];
      this.Shape.LineWidth = 5.0*cam.Height/viewport[3];
      this.Shape.FixedSize = false;

      this.Viewer.AddWidget(this);

      // Note: If the user clicks before the mouse is in the
      // canvas, this will behave odd.

      if (newFlag) {
        this.State = NEW;
        this.Viewer.ActivateWidget(this);
        return;
      }

      this.State = WAITING;

    }

    RectWidget.prototype.Draw = function(view) {
       this.Shape.Draw(view);
    };

    // This needs to be put in the Viewer.
    RectWidget.prototype.RemoveFromViewer = function() {
        if (this.Viewer) {
            this.Viewer.RemoveWidget(this);
        }
    };

    RectWidget.prototype.PasteCallback = function(data, mouseWorldPt) {
      this.Load(data);
      // Place the widget over the mouse.
      // This would be better as an argument.
      this.Shape.Origin = [mouseWorldPt[0], mouseWorldPt[1]];
      eventuallyRender();
    };

    RectWidget.prototype.Serialize = function() {
      if(this.Shape === undefined){ return null; }
      var obj = {};
      obj.type = "rect";
      obj.origin = this.Shape.Origin;
      obj.outlinecolor = this.Shape.OutlineColor;
      obj.radius = this.Shape.Radius;
      obj.length = this.Shape.Length;
      obj.width = this.Shape.Width;
      obj.orientation = this.Shape.Orientation;
      obj.linewidth = this.Shape.LineWidth;
      obj.creation_camera = this.CreationCamera;
      return obj;
    };

    // Load a widget from a json object (origin MongoDB).
    RectWidget.prototype.Load = function(obj) {
        this.Shape.Origin[0] = parseFloat(obj.origin[0]);
        this.Shape.Origin[1] = parseFloat(obj.origin[1]);
        this.Shape.OutlineColor[0] = parseFloat(obj.outlinecolor[0]);
        this.Shape.OutlineColor[1] = parseFloat(obj.outlinecolor[1]);
        this.Shape.OutlineColor[2] = parseFloat(obj.outlinecolor[2]);
        this.Shape.Radius = parseFloat(obj.radius);
        this.Shape.Width = parseFloat(obj.width);
        this.Shape.Length = parseFloat(obj.length);
        this.Shape.Orientation = parseFloat(obj.orientation);
        this.Shape.LineWidth = parseFloat(obj.linewidth);
        this.Shape.FixedSize = false;
        this.Shape.UpdateBuffers(this.Layer.AnnotationView);

        // How zoomed in was the view when the annotation was created.
        if (obj.creation_camera !== undefined) {
            this.CreationCamera = obj.CreationCamera;
        }
    };

    RectWidget.prototype.HandleKeyPress = function(keyCode, shift) {
      // The dialog consumes all key events.
      if (this.State == PROPERTIES_DIALOG) {
          return false;
      }

      // Copy
      if (event.keyCode == 67 && event.ctrlKey) {
        // control-c for copy
        // The extra identifier is not needed for widgets, but will be
        // needed if we have some other object on the clipboard.
        var clip = {Type:"RectWidget", Data: this.Serialize()};
        localStorage.ClipBoard = JSON.stringify(clip);
        return false;
      }

      return true;
    };

    RectWidget.prototype.HandleDoubleClick = function(event) {
        return true;
    };

    RectWidget.prototype.HandleMouseDown = function(event) {
        if (event.which != 1) {
            return false;
        }
        if (this.State == NEW) {
            // We need the viewer position of the circle center to drag radius.
            this.OriginViewer =
                this.Viewer.ConvertPointWorldToViewer(this.Shape.Origin[0],
                                                      this.Shape.Origin[1]);
            this.State = DRAG_RADIUS;
        }
        if (this.State == ACTIVE) {
            // Determine behavior from active radius.
            if (this.NormalizedActiveDistance < 0.5) {
                this.State = DRAG;
            } else {
                this.OriginViewer =
                    this.Viewer.ConvertPointWorldToViewer(this.Shape.Origin[0],
                                                          this.Shape.Origin[1]);
                this.State = DRAG_RADIUS;
            }
        }
        return true;
    };

    // returns false when it is finished doing its work.
    RectWidget.prototype.HandleMouseUp = function(event) {
        if ( this.State == DRAG || this.State == DRAG_RADIUS) {
            this.SetActive(false);
            if (window.SA) {SA.RecordState();}
        }
    };

    RectWidget.prototype.HandleMouseMove = function(event) {
        var x = event.offsetX;
        var y = event.offsetY;

        if (event.which === 0 && this.State == ACTIVE) {
            this.CheckActive(event);
            return;
        }

        if (this.State == NEW || this.State == DRAG) {
            this.Shape.Origin = this.Viewer.ConvertPointViewerToWorld(x, y);
            this.PlacePopup();
            eventuallyRender();
        }

        if (this.State == DRAG_RADIUS) {
            var viewport = this.Viewer.GetViewport();
            var cam = this.Viewer.MainView.Camera;
            var dx = x-this.OriginViewer[0];
            var dy = y-this.OriginViewer[1];
            // Change units from pixels to world.
            this.Shape.Radius = Math.sqrt(dx*dx + dy*dy) * cam.Height / viewport[3];
            this.Shape.UpdateBuffers(this.Layer.AnnotationView);
            this.PlacePopup();
            eventuallyRender();
        }

        if (this.State == WAITING) {
            this.CheckActive(event);
        }
    };



    RectWidget.prototype.HandleMouseWheel = function(event) {
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
                    this.Shape.Length = this.Shape.Length * ratio;
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
    };


    RectWidget.prototype.HandleTouchPan = function(event) {
      w0 = this.Viewer.ConvertPointViewerToWorld(EVENT_MANAGER.LastMouseX,
                                                 EVENT_MANAGER.LastMouseY);
      w1 = this.Viewer.ConvertPointViewerToWorld(event.offsetX,event.offsetY);

      // This is the translation.
      var dx = w1[0] - w0[0];
      var dy = w1[1] - w0[1];

      this.Shape.Origin[0] += dx;
      this.Shape.Origin[1] += dy;
      eventuallyRender();
    };


    RectWidget.prototype.HandleTouchPinch = function(event) {
      this.Shape.Radius *= event.PinchScale;
      this.Shape.UpdateBuffers(this.Layer.AnnotationView);
      eventuallyRender();
    };

    RectWidget.prototype.HandleTouchEnd = function(event) {
      this.SetActive(false);
    };


    RectWidget.prototype.CheckActive = function(event) {
      var x = event.offsetX;
      var y = event.offsetY;
      var dx, dy;
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

      if (this.Shape.FillColor === undefined) { // Circle
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

      this.SetActive(active);
      return active;
    };

    // Multiple active states. Active state is a bit confusing.
    RectWidget.prototype.GetActive = function() {
      if (this.State == WAITING) {
        return false;
      }
      return true;
    };


    RectWidget.prototype.Deactivate = function() {
        this.Popup.StartHideTimer();
        this.State = WAITING;
        this.Shape.Active = false;
        this.Viewer.DeactivateWidget(this);
        if (this.DeactivateCallback) {
            this.DeactivateCallback();
        }
        eventuallyRender();
    };

    // Setting to active always puts state into "active".
    // It can move to other states and stay active.
    RectWidget.prototype.SetActive = function(flag) {
      if (flag == this.GetActive()) {
        return;
      }

      if (flag) {
        this.State = ACTIVE;
        this.Shape.Active = true;
        this.Viewer.ActivateWidget(this);
        eventuallyRender();
        // Compute the location for the pop up and show it.
        this.PlacePopup();
      } else {
        this.Deactivate();
      }
      eventuallyRender();
    };


    //This also shows the popup if it is not visible already.
    RectWidget.prototype.PlacePopup = function () {
      // Compute the location for the pop up and show it.
      var roll = this.Viewer.GetCamera().Roll;
      var x = this.Shape.Origin[0] + 0.8 * this.Shape.Radius * (Math.cos(roll) - Math.sin(roll));
      var y = this.Shape.Origin[1] - 0.8 * this.Shape.Radius * (Math.cos(roll) + Math.sin(roll));
      var pt = this.Viewer.ConvertPointWorldToViewer(x, y);
      this.Popup.Show(pt[0],pt[1]);
    };

    // Can we bind the dialog apply callback to an objects method?
    var DIALOG_SELF;

    RectWidget.prototype.ShowPropertiesDialog = function () {
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
    };


    RectWidget.prototype.DialogApplyCallback = function() {
      var hexcolor = this.Dialog.ColorInput.val();
      this.Shape.SetOutlineColor(hexcolor);
      this.Shape.LineWidth = parseFloat(this.Dialog.LineWidthInput.val());
      this.Shape.UpdateBuffers(this.Layer.AnnotationView);
      this.SetActive(false);
      if (window.SA) {SA.RecordState();}
      eventuallyRender();

      localStorage.RectWidgetDefaults = JSON.stringify({Color: hexcolor, LineWidth: this.Shape.LineWidth});
    };

    SAM.RectWidget = RectWidget;

})();
