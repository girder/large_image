// Two behaviors: 
// 1: Single click and drag causes a vertex to follow the
// mouse. A new vertex is inserted if the click was on an edge.  If a
// vertex is dropped on top of its neighbor, the are merged.
// 2: WHen the widget is first created or double cliccked, it goes into
// drawing mode.  A vertex follows the cursor with no buttons pressed.
// A single click causes another vertex to be added.  Double click ends the
// draing state.

(function () {
    // Depends on the CIRCLE widget
    "use strict";

    var VERTEX_RADIUS = 8;
    var EDGE_RADIUS = 4;

    // These need to be cleaned up.
    // Drawing started with 0 points or drawing restarted.
    var DRAWING = 0;
    // Drawing mode: Mouse is up and the new point is following the mouse.
    var DRAWING_EDGE = 1;
    // Not active.
    var WAITING = 2;
    // Waiting but receiving events.  The circle handle is active.
    var DRAGGING = 3; // Mouse is down and a vertex is following the mouse.
    var ACTIVE = 5;
    // Dialog is active.
    var PROPERTIES_DIALOG = 6;


    function PolylineWidget (layer, newFlag) {
        if (layer === undefined) {
            return;
        }

        // Circle is to show an active vertex.
        this.Circle = new SAM.Circle();
        this.Polyline = new SAM.Polyline();

        this.InitializeDialog();

        // Get default properties.
        this.LineWidth = 10.0;
        this.Polyline.Closed = false;
        if (localStorage.PolylineWidgetDefaults) {
            var defaults = JSON.parse(localStorage.PolylineWidgetDefaults);
            if (defaults.Color) {
                this.Dialog.ColorInput.val(SAM.ConvertColorToHex(defaults.Color));
            }
            // Remebering closed flag seems arbitrary.  User can complete
            // the loop if they want it closed. Leaving it open allow
            // restart too.
            //if (defaults.ClosedLoop !== undefined) {
            //    this.Polyline.Closed = defaults.ClosedLoop;
            //}
            if (defaults.LineWidth) {
                this.LineWidth = defaults.LineWidth;
                this.Dialog.LineWidthInput.val(this.LineWidth);
            }
        }

        this.Circle.FillColor = [1.0, 1.0, 0.2];
        this.Circle.OutlineColor = [0.0,0.0,0.0];
        this.Circle.FixedSize = false;
        this.Circle.ZOffset = -0.05;

        this.Polyline.OutlineColor = [0.0, 0.0, 0.0];
        this.Polyline.SetOutlineColor(this.Dialog.ColorInput.val());
        this.Polyline.FixedSize = false;

        this.Layer = layer;
        this.Popup = new SAM.WidgetPopup(this);
        var cam = layer.GetCamera();

        this.Layer.AddWidget(this);

        // Set line thickness using layer. (5 pixels).
        // The Line width of the shape switches to 0 (single line)
        // when the actual line with is too thin.
        this.Polyline.LineWidth =this.LineWidth;
        this.Circle.Radius = this.LineWidth;
        this.Circle.UpdateBuffers(this.Layer.AnnotationView);

        // ActiveVertex and Edge are for placing the circle handle.
        this.ActiveVertex = -1;
        this.ActiveEdge = undefined;
        // Which vertec is being dragged.
        this.DrawingVertex = -1;

        if (newFlag) {
            this.State = DRAWING;
            this.SetCursorToDrawing();
            //this.Polyline.Active = true;
            this.Layer.ActivateWidget(this);
        } else {
            this.State = WAITING;
            this.Circle.Visibility = false;
        }

        // Lets save the zoom level (sort of).
        // Load will overwrite this for existing annotations.
        // This will allow us to expand annotations into notes.
        this.CreationCamera = layer.GetCamera().Serialize();

        // Set to be the width of a pixel.
        this.MinLine = 1.0;

        this.Layer.EventuallyDraw(false);
    }


    PolylineWidget.prototype.InitializeDialog = function() {
        var self = this;
        this.Dialog = new SAM.Dialog(function () {self.DialogApplyCallback();});
        // Customize dialog for a lasso.
        this.Dialog.Title.text('Lasso Annotation Editor');
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

        // closed check
        this.Dialog.ClosedDiv =
            $('<div>')
            .appendTo(this.Dialog.Body)
            .css({'display':'table-row'});
        this.Dialog.ClosedLabel =
            $('<div>')
            .appendTo(this.Dialog.ClosedDiv)
            .text("Closed:")
            .css({'display':'table-cell',
                  'text-align': 'left'});
        this.Dialog.ClosedInput =
            $('<input type="checkbox">')
            .appendTo(this.Dialog.ClosedDiv)
            .attr('checked', 'false')
            .css({'display': 'table-cell'});

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

        // Length
        this.Dialog.LengthDiv =
            $('<div>')
            .appendTo(this.Dialog.Body)
            .css({'display':'table-row'});
        this.Dialog.LengthLabel =
            $('<div>')
            .appendTo(this.Dialog.LengthDiv)
            .text("Length:")
            .css({'display':'table-cell',
                  'text-align': 'left'});
        this.Dialog.Length =
            $('<div>')
            .appendTo(this.Dialog.LengthDiv)
            .css({'display':'table-cell'});

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
    }

    PolylineWidget.prototype.Draw = function(view) {
        // When the line is too thin, we can see nothing.
        // Change it to line drawing.
        var cam = this.Layer.GetCamera();
        this.MinLine = cam.GetSpacing();
        if (this.LineWidth < this.MinLine) {
            // Too thin. Use a single line.
            this.Polyline.LineWidth = 0;
        } else {
            this.Polyline.LineWidth = this.LineWidth;
        }

        this.Polyline.Draw(view);
        this.Circle.Draw(view);
    }

    PolylineWidget.prototype.PasteCallback = function(data, mouseWorldPt) {
        this.Load(data);
        // Place the widget over the mouse.
        // This is more difficult than the circle.  Compute the shift.
        var bounds = this.Polyline.GetBounds();
        if ( ! bounds) {
            console.log("Warining: Pasting empty polyline");
            return;
        }
        var xOffset = mouseWorldPt[0] - (bounds[0]+bounds[1])/2;
        var yOffset = mouseWorldPt[1] - (bounds[2]+bounds[3])/2;
        for (var i = 0; i < this.Polyline.GetNumberOfPoints(); ++i) {
            this.Polyline.Points[i][0] += xOffset;
            this.Polyline.Points[i][1] += yOffset;
        }
        this.Polyline.UpdateBuffers(this.Layer.AnnotationView);
        if (SA.notesWidget) {SA.notesWidget.MarkAsModified();} // hack

        this.Layer.EventuallyDraw(true);
    }

    PolylineWidget.prototype.Serialize = function() {
        if(this.Polyline === undefined){ return null; }
        var obj = new Object();
        obj.type = "polyline";
        obj.outlinecolor = this.Polyline.OutlineColor;
        obj.linewidth = this.LineWidth;
        // Copy the points to avoid array reference bug.
        obj.points = [];
        for (var i = 0; i < this.Polyline.GetNumberOfPoints(); ++i) {
            obj.points.push([this.Polyline.Points[i][0], this.Polyline.Points[i][1]]);
        }

        obj.creation_camera = this.CreationCamera;
        obj.closedloop = this.Polyline.Closed;

        return obj;
    }

    // Load a widget from a json object (origin MongoDB).
    // Object already json decoded.
    PolylineWidget.prototype.Load = function(obj) {
        this.Polyline.OutlineColor[0] = parseFloat(obj.outlinecolor[0]);
        this.Polyline.OutlineColor[1] = parseFloat(obj.outlinecolor[1]);
        this.Polyline.OutlineColor[2] = parseFloat(obj.outlinecolor[2]);
        this.LineWidth = parseFloat(obj.linewidth);
        this.Polyline.LineWidth = this.LineWidth;
        this.Polyline.Points = [];
        for(var n=0; n < obj.points.length; n++){
            this.Polyline.Points[n] = [parseFloat(obj.points[n][0]),
                                    parseFloat(obj.points[n][1])];
        }
        this.Polyline.Closed = obj.closedloop;
        this.Polyline.UpdateBuffers(this.Layer.AnnotationView);

        // How zoomed in was the view when the annotation was created.
        if (obj.view_height !== undefined) {
            this.CreationCamera = obj.creation_camera;
        }
    }

    PolylineWidget.prototype.CityBlockDistance = function(p0, p1) {
        return Math.abs(p1[0]-p0[0]) + Math.abs(p1[1]-p0[1]);
    }

    PolylineWidget.prototype.HandleKeyDown = function(event) {
        // Copy
        if (event.keyCode == 67 && event.ctrlKey) {
            // control-c for copy
            // The extra identifier is not needed for widgets, but will be
            // needed if we have some other object on the clipboard.
            var clip = {Type:"PolylineWidget", Data: this.Serialize()};
            localStorage.ClipBoard = JSON.stringify(clip);
            return false;
        }

        // escape key (or space or enter) to turn off drawing
        if (event.keyCode == 27 || event.keyCode == 32 || event.keyCode == 13) {
            // Last resort.  ESC key always deactivates the widget.
            // Deactivate.
            this.Layer.DeactivateWidget(this);
            if (SAM.NotesWidget) {SAM.NotesWidget.MarkAsModified();} // hack
            if (window.SA) {SA.RecordState();}
            return false;
        }

        return true;
    }
    PolylineWidget.prototype.HandleDoubleClick = function(event) {
        if (this.State == DRAWING || this.State == DRAWING_EDGE) {
            this.Polyline.MergePoints(this.Circle.Radius);
            this.Layer.DeactivateWidget(this);
            return false;
        }
        // Handle: Restart drawing mode. Any point on the line can be used.
        if (this.State == ACTIVE) {
            var x = event.offsetX;
            var y = event.offsetY;
            var pt = this.Layer.GetCamera().ConvertPointViewerToWorld(x,y);
            // Active => Double click starts drawing again.
            if (this.ActiveVertex != -1) {
                this.Polyline.Points[this.ActiveVertex] = pt;
                this.DrawingVertex = this.ActiveVertex;
                this.ActiveVertex = -1;
            } else if (this.ActiveEdge) {
                // Insert a new point in the edge.
                // mouse down gets called before this and does this.
                // TODO: Fix it so mouse down/up do not get called on
                // double click.
                this.Polyline.Points.splice(this.ActiveEdge[1],0,pt);
                this.DrawingVertex = this.ActiveEdge[1];
                this.ActiveEdge = undefined;
            } else {
                // Sanity check:
                console.log("No vertex or edge is active.");
                return false;
            }
            this.Polyline.UpdateBuffers(this.Layer.AnnotationView);
            this.SetCursorToDrawing();
            // Transition to drawing edge when we know which way the user
            // is dragging.
            this.State = DRAWING;
            this.Layer.EventuallyDraw(false);
            return false;
        }
    }

    // Because of double click:
    // Mouse should do nothing. Mouse move and mouse up should cause all
    // the changes.
    PolylineWidget.prototype.HandleMouseDown = function(event) {

        // Only chnage handle properties.  Nothing permanent changes with mousedown.
        if (event.which == 1 && this.State == ACTIVE) {
            //User has started dragging a point with the mouse down.
            this.Popup.Hide();
            // Change the circle color to the line color when dragging.
            this.Circle.FillColor = this.Polyline.OutlineColor;
            this.Circle.Active = false;
        }

        return false;
    }

    // Returns false when it is finished doing its work.
    PolylineWidget.prototype.HandleMouseUp = function(event) {

        // Shop dialog with right click.  I could have a menu appear.
        if (event.which == 3) {
            // Right mouse was pressed.
            // Pop up the properties dialog.
            this.State = PROPERTIES_DIALOG;
            this.ShowPropertiesDialog();
            return false;
        }

        if (event.which != 1) {
            return false;
        }

        if (this.State == ACTIVE) {
            // Dragging a vertex just ended.
            // Handle merging points when user drags a vertex onto another.
            this.Polyline.MergePoints(this.Circle.Radius);
            // TODO: Manage modidfied more consistently.
            if (SAM.NotesWidget) {SAM.NotesWidget.MarkAsModified();} // hack
            if (window.SA) {SA.RecordState();}
            return false;
        }

        var x = event.offsetX;
        var y = event.offsetY;
        var pt = this.Layer.GetCamera().ConvertPointViewerToWorld(x,y);

        if (this.State == DRAWING) {
            // handle the case where we restarted drawing and clicked again
            // before moving the mouse. (triple click).  Do nothing.
            if (this.Polyline.GetNumberOfPoints() > 0) {
                return false;
            }
            // First point after creation. We delayed adding the first
            // point so add it now.
            this.Polyline.Points.push(pt);
            // Not really necessary because DRAWING_EDGE case resets it.
            this.DrawingVertex = this.Polyline.GetNumberOfPoints() -1;
            this.State = DRAWING_EDGE;
        }
        if (this.State == DRAWING_EDGE) {
            // Check to see if the loop was closed.
            if (this.Polyline.GetNumberOfPoints() > 2 && this.ActiveVertex == 0) {
                // The user clicked on the first vertex. End the line.
                // Remove the temporary point at end used for drawing.
                this.Polyline.Points.pop();
                this.Polyline.Closed = true;
                this.Layer.DeactivateWidget(this);
                if (window.SA) {SA.RecordState();}
                return false;
            }
            // Insert another point to drag around.
            this.DrawingVertex += 1;
            this.Polyline.Points.splice(this.DrawingVertex,0,pt);
            this.Polyline.UpdateBuffers(this.Layer.AnnotationView);
            this.Layer.EventuallyDraw(true);
            return false;
        }
        return false;
    }


    //  Preconditions: State == ACTIVE, Mouse 1 is down.
    // ActiveVertex != 1 or ActiveEdge == [p0,p1,k]
    PolylineWidget.prototype.HandleDrag = function(pt) {
        if (this.ActiveEdge) {
            // User is dragging an edge point that has not been
            // created yet.
            var pt0 = this.Polyline.Points[this.ActiveEdge[0]];
            var pt1 = this.Polyline.Points[this.ActiveEdge[1]];
            var x = pt0[0] + this.ActiveEdge[2]*(pt1[0]-pt0[0]);
            var y = pt0[1] + this.ActiveEdge[2]*(pt1[1]-pt0[1]);
            this.Polyline.Points.splice(this.ActiveEdge[1],0,[x,y]);
            this.ActiveVertex = this.ActiveEdge[1];
            this.ActiveEdge = undefined;
            this.HighlightVertex(this.ActiveVertex);
            // When dragging, circle is the same color as the line.
            this.Circle.Active = false;
        }
        if ( this.ActiveVertex == -1) {
            // Sanity check.
            return false;
        }
        // If a vertex is dragged onto its neighbor, indicate that
        // the vertexes will be merged. Change the color of the
        // circle to active as an indicator.
        this.Circle.Active = false;
        this.Polyline.Points[this.ActiveVertex] = pt;
        if (this.ActiveVertex > 0 &&
            this.Polyline.GetEdgeLength(this.ActiveVertex-1) < this.Circle.Radius) {
            this.Circle.Active = true;
            // Snap to the neighbor. Deep copy the point
            pt = this.Polyline.Points[this.ActiveVertex-1].slice(0);
        }
        if (this.ActiveVertex < this.Polyline.GetNumberOfPoints()-1 &&
            this.Polyline.GetEdgeLength(this.ActiveVertex) < this.Circle.Radius) {
            this.Circle.Active = true;
            // Snap to the neighbor. Deep copy the point
            pt = this.Polyline.Points[this.ActiveVertex+1].slice(0);
        }
        // Move the vertex with the mouse.
        this.Polyline.Points[this.ActiveVertex] = pt;
        // Move the hightlight circle with the vertex.
        this.Circle.Origin = pt;
        this.Polyline.UpdateBuffers(this.Layer.AnnotationView);

        // TODO: Fix this hack.
        if (SAM.NotesWidget) {SAM.NotesWidget.MarkAsModified();} // hack
        this.Layer.EventuallyDraw(true);
    }


    // precondition : State == DRAWING
    // postcondition: State == DRAWING_EDGE
    // Handle a bunch of cases.  First created, restart at ends or middle.
    PolylineWidget.prototype.StartDrawing = function(pt) {
        // If the widget was just created do nothing.
        if (this.Polyline.GetNumberOfPoints() == 0) {
            return;
        }
        // If we are the begining, Reverse the points.
        if (this.DrawingVertex == 0) {
            this.Polyline.Points.reverse();
            this.DrawingVertex = this.Polyline.GetNumberOfPoints()-1;
        }
        // If we are at the end.  Add a point.
        if (this.DrawingVertex == this.Polyline.GetNumberOfPoints() -1) {
            this.Polyline.Points.push(pt);
            this.DrawingVertex += 1;
            this.State = DRAWING_EDGE;
            return;
        }
        // If we are in the middle. Choose between the two edges.
        var pt0 = this.Polyline.Points[this.DrawingVertex-1];
        var pt1 = this.Polyline.Points[this.DrawingVertex];
        var pt2 = this.Polyline.Points[this.DrawingVertex+1];
        // Movement vector
        var dx = pt[0] - pt1[0];
        var dy = pt[1] - pt1[1];
        // This is sort of a pain. Normalize the edges.
        var e0 = [pt0[0]-pt1[0], pt0[1]-pt1[1]];
        var dist0 = Math.sqrt(e0[0]*e0[0] + e0[1]*e0[1]);
        dist0 = (dx*e0[0]+dy*e0[1]) / dist0;
        var e1 = [pt2[0]-pt1[0], pt2[1]-pt1[1]];
        var dist1 = Math.sqrt(e1[0]*e1[0] + e1[1]*e1[1]);
        dist1= (dx*e1[0]+dy*e1[1]) / dist0;
        // if the user is draggin backward, reverse the points.
        if (dist0 > dist1) {
            this.Polyline.Points.reverse();
            this.DrawingVertex = this.Polyline.GetNumberOfPoints() - this.DrawingVertex - 1;
        }
        // Insert a point to continue drawing.
        this.DrawingVertex += 1;
        this.Polyline.Points.splice(this.DrawingVertex,0,pt);
        this.State = DRAWING_EDGE;
        return false;
    }

    PolylineWidget.prototype.HandleMouseMove = function(event) {
        var x = event.offsetX;
        var y = event.offsetY;
        var pt = this.Layer.GetCamera().ConvertPointViewerToWorld(x,y);

        if (this.State == DRAWING) {
            this.StartDrawing(pt);
            return false;
        }
        if (this.State == DRAWING_EDGE) {
            // Move the active point to follor the cursor.
            this.Polyline.Points[this.DrawingVertex] = pt;
            this.Polyline.UpdateBuffers(this.Layer.AnnotationView);

            // This higlights the first vertex when a loop is possible.
            var idx = this.Polyline.PointOnVertex(pt, this.Circle.Radius);
            if (this.DrawingVertex == this.Polyline.GetNumberOfPoints()-1 && idx == 0) {
                // Highlight first vertex to indicate potential loop closure.
                this.HighlightVertex(0);
            } else {
                this.HighlightVertex(-1);
            }
            return false;
        }

        if (this.State == ACTIVE) {
            if (event.which == 0) {
                // Turn off the active vertex if the mouse moves away.
                if ( ! this.CheckActive(event)) {
                    this.Layer.DeactivateWidget(this);
                } else {
                    this.UpdateActiveCircle();
                }
                return false;
            }
            if (this.State == ACTIVE && event.which == 1) {
                // We are in the middle of dragging a vertex (not in
                // drawing mode). Leave the circle highlighted.
                // Use ActiveVertex instead of DrawingVertex which is used
                // for drawing mode.
                this.HandleDrag(pt);
            }
        }
    }


    // Just returns true and false.  It saves either ActiveVertex or
    // ActiveEdge if true. Otherwise, it has no side effects.
    PolylineWidget.prototype.CheckActive = function(event) {
        var x = event.offsetX;
        var y = event.offsetY;
        var pt = this.Layer.GetCamera().ConvertPointViewerToWorld(x,y);
        var dist;

        this.ActiveEdge = undefined;

        // Check for mouse touching a vertex circle.
        dist = VERTEX_RADIUS / this.Layer.GetPixelsPerUnit();
        dist = Math.max(dist, this.Polyline.GetLineWidth());
        this.ActiveVertex = this.Polyline.PointOnVertex(pt, dist);

        if (this.State == DRAWING_EDGE) { 
            // TODO:  The same logic is in mouse move.  Decide which to remove.
            // Only allow the first vertex to be active (closing the loop).
            if (this.Polyline.GetNumberOfPoints() < 2 ||
                this.ActiveVertex != 0) {
                this.ActiveVertex = -1;
                return false;
            }
            return true;
        }

        if (this.ActiveVertex == -1) {
            // Tolerance: 5 screen pixels.
            dist = EDGE_RADIUS / this.Layer.GetPixelsPerUnit();
            dist = Math.max(dist, this.Polyline.GetLineWidth()/2);
            this.ActiveEdge = this.Polyline.PointOnShape(pt, dist);
            if ( ! this.ActiveEdge) {
                return false;
            }
        }
        return true;
    }

    // This does not handle the case where we want to highlight an edge
    // point that has not been created yet.
    PolylineWidget.prototype.HighlightVertex = function(vertexIdx) {
        if (vertexIdx < 0 || vertexIdx >= this.Polyline.GetNumberOfPoints()) {
            this.Circle.Visibility = false;
        } else {
            this.Circle.Visibility = true;
            this.Circle.Active = true;
            this.Circle.Radius = VERTEX_RADIUS / this.Layer.GetPixelsPerUnit();
            this.CircleRadius = Math.max(this.CircleRadius,
                                         this.Polyline.GetLineWidth() * 1.5);
            this.Circle.UpdateBuffers(this.Layer.AnnotationView);
            this.Circle.Origin = this.Polyline.Points[vertexIdx];
        }
        this.ActiveVertex = vertexIdx;
        this.Layer.EventuallyDraw(true);
    }

    // Use ActiveVertex and ActiveEdge iVars to place and size circle.
    PolylineWidget.prototype.UpdateActiveCircle = function() {
        if (this.ActiveVertex != -1) {
            this.HighlightVertex(this.ActiveVertex);
            return;
        } else if (this.ActiveEdge) {
            this.Circle.Visibility = true;
            this.Circle.Active = true;
            this.Circle.Radius = EDGE_RADIUS / this.Layer.GetPixelsPerUnit();
            this.CircleRadius = Math.max(this.CircleRadius,
                                         this.Polyline.GetLineWidth());
            // Find the exact point on the edge (projection of
            // cursor on the edge).
            var pt0 = this.Polyline.Points[this.ActiveEdge[0]];
            var pt1 = this.Polyline.Points[this.ActiveEdge[1]];
            var x = pt0[0] + this.ActiveEdge[2]*(pt1[0]-pt0[0]);
            var y = pt0[1] + this.ActiveEdge[2]*(pt1[1]-pt0[1]);
            this.Circle.Origin = [x,y,0];
            this.Circle.UpdateBuffers(this.Layer.AnnotationView);
        } else {
            // Not active.
            this.Circle.Visibility = false;
            // We never hightlight the whold polyline now.
            //this.Polyline.Active = false;
        }
        this.Layer.EventuallyDraw(false);
    }

    // Multiple active states. Active state is a bit confusing.
    // Only one state (WAITING) does not receive events from the layer.
    PolylineWidget.prototype.GetActive = function() {
        if (this.State == WAITING) {
            return false;
        }
        return true;
    }

    // Active means that the widget is receiving events.  It is
    // "hot" and waiting to do something.  
    // However, it is not active when in drawing mode.
    // This draws a circle at the active spot.
    // Vertexes are active for click and drag or double click into drawing
    // mode. Edges are active to insert a new vertex and drag or double
    // click to insert a new vertex and go into drawing mode.
    PolylineWidget.prototype.SetActive = function(flag) {
        if (flag == this.GetActive()) {
            // Nothing has changed.  Do nothing.
            return;
        }

        if (flag) {
            this.State = ACTIVE;
            this.UpdateActiveCircle();
            this.PlacePopup();
        } else {
            this.Popup.StartHideTimer();
            this.State = WAITING;
            this.DrawingVertex = -1;
            this.ActiveVertex = -1;
            this.ActiveEdge = undefined;
            this.Circle.Visibility = false;
            if (this.DeactivateCallback) {
                this.DeactivateCallback();
            }
            // Remove invisible lines (with 0 or 1 points).
            if (this.Polyline.GetNumberOfPoints() < 2) {
                if (this.Layer) {
                    this.Layer.RemoveWidget(this);
                }
            }
        }

        this.Layer.EventuallyDraw(false);
    }

    PolylineWidget.prototype.SetCursorToDrawing = function() {
        this.Popup.Hide();
        this.Layer.GetCanvasDiv().css(
            {'cursor':'url('+SAM.ImagePathUrl+'dotCursor8.png) 4 4,crosshair'});
        this.Layer.EventuallyDraw();
    }


    //This also shows the popup if it is not visible already.
    PolylineWidget.prototype.PlacePopup = function () {
        // The popup gets in the way when firt creating the line.
        if (this.State == DRAWING_EDGE ||
            this.State == DRAWING) {
            return;
        }

        var pt = this.Polyline.FindPopupPoint(this.Layer.GetCamera());
        pt = this.Layer.GetCamera().ConvertPointWorldToViewer(pt[0], pt[1]);

        pt[0] += 20;
        pt[1] -= 10;

        this.Popup.Show(pt[0],pt[1]);
    }

    // Can we bind the dialog apply callback to an objects method?
    var DIALOG_SELF;
    PolylineWidget.prototype.ShowPropertiesDialog = function () {
        this.Dialog.ColorInput.val(SAM.ConvertColorToHex(this.Polyline.OutlineColor));
        this.Dialog.ClosedInput.prop('checked', this.Polyline.Closed);
        this.Dialog.LineWidthInput.val((this.Polyline.LineWidth).toFixed(2));

        var length = this.ComputeLength() * 0.25; // microns per pixel.
        var lengthString = "";
        if (this.Polyline.FixedSize) {
            lengthString += length.toFixed(2);
            lengthString += " px";
        } else {
            if (length > 1000) {
                lengthString += (length/1000).toFixed(2) + " mm";
            } else {
                // Latin-1 00B5 is micro sign
                lengthString += length.toFixed(2) + " \xB5m";
            }
        }
        this.Dialog.Length.text(lengthString);

        if (this.Polyline.Closed) {
            this.Dialog.AreaDiv.show();
            var area = this.ComputeArea() * 0.25 * 0.25;
            var areaString = "";
            if (this.Polyline.FixedSize) {
                areaString += area.toFixed(2);
                areaString += " pixels^2";
            } else {
                if (area > 1000000) {
                    areaString += (area/1000000).toFixed(2) + " mm^2";
                } else {
                    // Latin-1 00B5 is micro sign
                    areaString += area.toFixed(2) + " \xB5m^2";
                }
            }
            this.Dialog.Area.text(areaString);
        } else {
            this.Dialog.AreaDiv.hide();
        }
        this.Dialog.Show(true);
    }

    PolylineWidget.prototype.DialogApplyCallback = function() {
        var hexcolor = this.Dialog.ColorInput.val();
        this.Polyline.SetOutlineColor(hexcolor);
        this.Polyline.Closed = this.Dialog.ClosedInput.prop("checked");

        // Cannot use the shap line width because it is set to zero (single pixel)
        // it the dialog value is too thin.
        this.LineWidth = parseFloat(this.Dialog.LineWidthInput.val());
        this.Polyline.UpdateBuffers(this.Layer.AnnotationView);
        this.SetActive(false);
        if (window.SA) {SA.RecordState();}
        this.Layer.EventuallyDraw(false);

        localStorage.PolylineWidgetDefaults = JSON.stringify(
            {Color: hexcolor,
             ClosedLoop: this.Polyline.Closed,
             LineWidth: this.LineWidth});
        if (SAM.NotesWidget) {SAM.NotesWidget.MarkAsModified();} // hack
    }

    // Note, self intersection can cause unexpected areas.
    // i.e looping around a point twice ...
    PolylineWidget.prototype.ComputeArea = function() {
        if (this.Polyline.GetNumberOfPoints() == 0) {
            return 0.0;
        }

        // Compute the center. It should be more numerically stable.
        // I could just choose the first point as the origin.
        var cx = 0;
        var cy = 0;
        for (var j = 0; j < this.Polyline.GetNumberOfPoints(); ++j) {
            cx += this.Polyline.Points[j][0];
            cy += this.Polyline.Points[j][1];
        }
        cx = cx / this.Polyline.GetNumberOfPoints();
        cy = cy / this.Polyline.GetNumberOfPoints();

        var area = 0.0;
        // Iterate over triangles adding the area of each
        var last = this.Polyline.GetNumberOfPoints()-1;
        var vx1 = this.Polyline.Points[last][0] - cx;
        var vy1 = this.Polyline.Points[last][1] - cy;
        // First and last point form another triangle (they are not the same).
        for (var j = 0; j < this.Polyline.GetNumberOfPoints(); ++j) {
            // Area of triangle is 1/2 magnitude of cross product.
            var vx2 = vx1;
            var vy2 = vy1;
            vx1 = this.Polyline.Points[j][0] - cx;
            vy1 = this.Polyline.Points[j][1] - cy;
            area += (vx1*vy2) - (vx2*vy1);
        }

        // Handle both left hand loops and right hand loops.
        if (area < 0) {
            area = -area;
        }
        return area;
    }

    // Note, self intersection can cause unexpected areas.
    // i.e looping around a point twice ...
    PolylineWidget.prototype.ComputeLength = function() {
        if (this.Polyline.GetNumberOfPoints() < 2) {
            return 0.0;
        }

        var length = 0;
        var x0 = this.Polyline.Points[0][0];
        var y0 = this.Polyline.Points[0][1];
        for (var j = 1; j < this.Polyline.GetNumberOfPoints(); ++j) {
            var x1 = this.Polyline.Points[j][0];
            var y1 = this.Polyline.Points[j][1];
            var dx = x1-x0;
            var dy = y1-y0;
            x0 = x1;
            y0 = y1;
            length += Math.sqrt(dx*dx + dy*dy);
        }

        return length;
    }

    // This differentiates the inside of the polygion from the outside.
    // It is used to sample points in a segmented region.
    // Not actively used (more for experimentation for now).
    PolylineWidget.prototype.PointInside = function(ox,oy) {
        if (this.Polyline.Closed == false) {
            return false;
        }
        var x,y;
        var max = this.Polyline.GetNumberOfPoints() - 1;
        var xPos = 0;
        var xNeg = 0;
        //var yCount = 0;
        var pt0 = this.Polyline.Points[max];
        pt0 = [pt0[0]-ox, pt0[1]-oy];
        for (var idx = 0; idx <= max; ++idx) {
            var pt1 = this.Polyline.Points[idx];
            pt1 = [pt1[0]-ox, pt1[1]-oy];
            var k;
            k = (pt1[1] - pt0[1]);
            if ( k != 0 ) {
                k = -pt0[1] / k;
                if ( k > 0 && k <= 1) {
                    // Edge crosses the axis.  Find the intersection.
                    x = pt0[0] + k*(pt1[0]-pt0[0]);
                    if (x > 0) { xPos += 1; }
                    if (x < 0) { xNeg += 1; }
                }
            }
            pt0 = pt1;
        }

        if ((xPos % 2) && (xNeg % 2)) {
            return true
        }
        return false;
    }

    // TODO: This will not work with Layer.  Move this to the viewer or a
    // helper object.
    // Save images with centers inside the polyline.
    PolylineWidget.prototype.Sample = function(dim, spacing, skip, root, count) {
        var bds = this.Polyline.GetBounds();
        var ctx = this.Layer.Context2d;
        for (var y = bds[2]; y < bds[3]; y += skip) {
            for (var x = bds[0]; x < bds[1]; x += skip) {
                if (this.PointInside(x,y)) {
                    ip = this.Layer.GetCamera().ConvertPointWorldToViewer(x,y);
                    ip[0] = Math.round(ip[0] - dim/2);
                    ip[1] = Math.round(ip[1] - dim/2);
                    var data = ctx.getImageData(ip[0],ip[1],dim,dim);
                    DownloadImageData(data, root+"_"+count+".png");
                    ++count;
                }
            }
        }
    }


    // Save images with centers inside the polyline.
    PolylineWidget.prototype.SampleStack = function(dim, spacing, skip, root, count) {
        var cache = LAYERS[0].GetCache();
        var bds = this.Polyline.GetBounds();
        for (var y = bds[2]; y < bds[3]; y += skip) {
            for (var x = bds[0]; x < bds[1]; x += skip) {
                if (this.PointInside(x,y)) {
                    GetCutoutimage(cache, dim, [x,y], spacing, 0, null,
                                   function (data) {
                                       DownloadImageData(data, root+"_"+count+".png");
                                       ++count;
                                   });
                }
            }
        }
    }

    // Save images with centers inside the polyline.
    PolylineWidget.prototype.DownloadStack = function(x, y, dim, spacing, root) {
        var cache = LAYERS[0].GetCache();
        for (var i = 0; i < 3; ++i) {
            levelSpacing = spacing << i;
            GetCutoutImage(cache, dim, [x,y], levelSpacing, 0, root+i+".png", null);
        }
    }

    /*
    // Saves images centered at spots on the edge.
    // Roll is set to put the edge horizontal.
    // Step is in screen pixel units
    PolylineWidget.prototype.SampleEdge = function(dim, step, count, callback) {
    this.Polyline.SampleEdge(this.Layer,dim,step,count,callback);
    }

    function DownloadTheano(widgetIdx, angleIdx) {
    EDGE_ANGLE = 2*Math.PI * angleIdx / 24;
    LAYERS[0].WidgetList[widgetIdx].SampleEdge(
    64,4,EDGE_COUNT,
    function () {
    setTimeout(function(){ DownloadTheano2(widgetIdx, angleIdx); }, 1000);
    });
    }

    function DownloadTheano2(widgetIdx, angleIdx) {
    ++angleIdx;
    if (angleIdx >= 24) {
    angleIdx = 0;
    ++widgetIdx;
    }
    if (widgetIdx < LAYERS[0].WidgetList.length) {
    DownloadTheano(widgetIdx, angleIdx);
    }
    }
    */


    SAM.PolylineWidget = PolylineWidget;

})();
