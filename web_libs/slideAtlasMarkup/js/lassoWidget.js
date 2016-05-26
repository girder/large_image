//==============================================================================
// Variation of pencil
// Free form loop
// I plan to be abble to add or remove regions from the loop with multiple strokes.
// It will be a state, just like the pencil widget is a state.

(function () {
    // Depends on the CIRCLE widget
    "use strict";

    var DRAWING = 0;
    var ACTIVE = 1;
    var WAITING = 2;

    function LassoWidget (layer, newFlag) {
        if (layer == null) {
            return;
        }

        var self = this;
        this.Dialog = new SAM.Dialog(function () {self.DialogApplyCallback();});
        // Customize dialog for a lasso.
        this.Dialog.Title.text('Lasso Annotation Editor');
        this.Dialog.Body.css({'margin':'1em 2em'});
        // Color
        this.Dialog.ColorDiv =
            $('<div>')
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
        if (localStorage.LassoWidgetDefaults) {
            var defaults = JSON.parse(localStorage.LassoWidgetDefaults);
            if (defaults.Color) {
                this.Dialog.ColorInput.val(SAM.ConvertColorToHex(defaults.Color));
            }
            if (defaults.LineWidth) {
                this.Dialog.LineWidthInput.val(defaults.LineWidth);
            }
        }

        this.Layer = layer;
        this.Popup = new SAM.WidgetPopup(this);
        this.Layer.AddWidget(this);

        var self = this;

        this.Loop = new SAM.Polyline();
        this.Loop.OutlineColor = [0.0, 0.0, 0.0];
        this.Loop.SetOutlineColor(this.Dialog.ColorInput.val());
        this.Loop.FixedSize = false;
        this.Loop.LineWidth = 0;
        this.Loop.Closed = true;
        this.Stroke = false;

        this.ActiveCenter = [0,0];

        if ( newFlag) {
            this.SetStateToDrawing();
        } else {
            this.State = WAITING;
        }
    }

    LassoWidget.prototype.Draw = function(view) {
        this.Loop.Draw(view);
        if (this.Stroke) {
            this.Stroke.Draw(view);
        }
    }

    LassoWidget.prototype.Serialize = function() {
        var obj = new Object();
        obj.type = "lasso";
        obj.outlinecolor = this.Loop.OutlineColor;
        obj.linewidth = this.Loop.GetLineWidth();
        obj.points = [];
        for (var j = 0; j < this.Loop.Points.length; ++j) {
            obj.points.push([this.Loop.Points[j][0], this.Loop.Points[j][1]]);
        }
        obj.closedloop = true;

        return obj;
    }

    // Load a widget from a json object (origin MongoDB).
    LassoWidget.prototype.Load = function(obj) {
        if (obj.outlinecolor != undefined) {
            this.Loop.OutlineColor[0] = parseFloat(obj.outlinecolor[0]);
            this.Loop.OutlineColor[1] = parseFloat(obj.outlinecolor[1]);
            this.Loop.OutlineColor[2] = parseFloat(obj.outlinecolor[2]);
            // will never happen
            //if (this.Stroke) {
            //    this.Stroke.OutlineColor = this.Loop.OutlineColor;
            //}
        }
        if (obj.outlinewidth != undefined) {
            this.Loop.LineWidth = obj.linewidth;
        }
        var points = [];
        if ( obj.points != undefined) {
            points = obj.points;
        }
        if ( obj.shape != undefined) {
            points = obj.shapes[0];
        }

        for(var n=0; n < points.length; n++){
            this.Loop.Points[n] = [parseFloat(points[n][0]),
                                   parseFloat(points[n][1])];
        }
        this.ComputeActiveCenter();
        this.Loop.UpdateBuffers(this.Layer.AnnotationView);
    }

    LassoWidget.prototype.HandleMouseWheel = function(event) {
        if ( this.State == DRAWING ||
             this.State == ACTIVE) {
            if ( ! this.Loop) { return true; }
            var tmp = 0;

            if (event.deltaY) {
                tmp = event.deltaY;
            } else if (event.wheelDelta) {
                tmp = event.wheelDelta;
            }

            var minWidth = 1.0 / this.Layer.GetPixelsPerUnit();

            // Wheel event seems to be in increments of 3.
            // depreciated mousewheel had increments of 120....
            var lineWidth = this.Loop.GetLineWidth();
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
            this.Loop.SetLineWidth(lineWidth);
            this.Loop.UpdateBuffers(this.Layer.AnnotationView);

            this.Layer.EventuallyDraw();
            return false;
        }
        return true;
    }

    LassoWidget.prototype.Deactivate = function() {
        this.Popup.StartHideTimer();
        this.Layer.DeactivateWidget(this);
        this.State = WAITING;
        this.Loop.SetActive(false);
        if (this.Stroke) {
            this.Stroke.SetActive(false);
        }
        if (this.DeactivateCallback) {
            this.DeactivateCallback();
        }
        this.Layer.EventuallyDraw();
    }

    LassoWidget.prototype.HandleKeyDown = function(event) {
        if ( this.State == DRAWING) {
            // escape key (or space or enter) to turn off drawing
            if (event.keyCode == 27 || event.keyCode == 32 || event.keyCode == 13) {
                this.Deactivate();
                return false;
            }
        }
    }

    LassoWidget.prototype.HandleMouseDown = function(event) {
        var x = event.offsetX;
        var y = event.offsetY;

        if (event.which == 1) {
            // Start drawing.
            // Stroke is a temporary line for interaction.
            // When interaction stops, it is converted/merged with loop.
            this.Stroke = new SAM.Polyline();
            this.Stroke.OutlineColor = [0.0, 0.0, 0.0];
            this.Stroke.SetOutlineColor(this.Loop.OutlineColor);
            //this.Stroke.SetOutlineColor(this.Dialog.ColorInput.val());
            this.Stroke.FixedSize = false;
            this.Stroke.LineWidth = 0;

            var pt = this.Layer.GetCamera().ConvertPointViewerToWorld(x,y);
            this.Stroke.Points = [];
            this.Stroke.Points.push([pt[0], pt[1]]); // avoid same reference.
            return false;
        }
        return true;
    }

    LassoWidget.prototype.HandleMouseUp = function(event) {
        // Middle mouse deactivates the widget.
        if (event.which == 2) {
            // Middle mouse was pressed.
            this.Deactivate();
        }

        // A stroke has just been finished.
        if (event.which == 1 && this.State == DRAWING) {
            var spacing = this.Layer.GetCamera().GetSpacing();
            //this.Decimate(this.Stroke, spacing);
            this.Stroke.Decimate(spacing);
            if (this.Loop && this.Loop.Points.length > 0) {
                this.CombineStroke();
            } else {
                this.Stroke.Closed = true;
                this.Stroke.UpdateBuffers(this.Layer.AnnotationView);
                this.Loop = this.Stroke;
                this.Stroke = false;
            }
            this.ComputeActiveCenter();
            this.Layer.EventuallyDraw();

            if (window.SA) {SA.RecordState();}
        }
        return false;
    }

    LassoWidget.prototype.HandleDoubleClick = function(event) {
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

    LassoWidget.prototype.SetStateToDrawing = function() {
        this.State = DRAWING;
        // When drawing, the cursor is enough indication.
        // We keep the lines the normal color. Yellow is too hard to see.
        this.Loop.SetActive(false);
        this.Popup.Hide();
        this.Layer.GetCanvasDiv().css(
            {'cursor':'url('+SAM.ImagePathUrl+'select_lasso.png) 5 30,crosshair'});
        this.Layer.EventuallyDraw();
    }

    LassoWidget.prototype.HandleMouseMove = function(event) {
        var x = event.offsetX;
        var y = event.offsetY;

        if (event.which == 1 && this.State == DRAWING) {
            var shape = this.Stroke;
            var pt = this.Layer.GetCamera().ConvertPointViewerToWorld(x,y);
            shape.Points.push([pt[0], pt[1]]); // avoid same reference.
            shape.UpdateBuffers(this.Layer.AnnotationView);
            if (SA.notesWidget) {SA.notesWidget.MarkAsModified();} // hack
            this.Layer.EventuallyDraw();
            return false;
        }

        if (this.State == ACTIVE &&
            event.which == 0) {
            // Deactivate
            this.SetActive(this.CheckActive(event));
            return false;
        }
        return true;
    }

    LassoWidget.prototype.ComputeActiveCenter = function() {
        var count = 0;
        var sx = 0.0;
        var sy = 0.0;
        var shape = this.Loop;
        var points = [];
        for (var j = 0; j < shape.Points.length; ++j) {
            sx += shape.Points[j][0];
            sy += shape.Points[j][1];
        }

        this.ActiveCenter[0] = sx / shape.Points.length;
        this.ActiveCenter[1] = sy / shape.Points.length;
    }

    // This also shows the popup if it is not visible already.
    LassoWidget.prototype.PlacePopup = function () {
        var pt = this.Loop.FindPopupPoint(this.Layer.GetCamera());
        pt = this.Layer.GetCamera().ConvertPointWorldToViewer(pt[0], pt[1]);

        pt[0] += 20;
        pt[1] -= 10;

        this.Popup.Show(pt[0],pt[1]);
    }

    // Just returns whether the widget thinks it should be active.
    // Layer is responsible for seting it to active.
    LassoWidget.prototype.CheckActive = function(event) {
        if (this.State == DRAWING) { return; }

        var x = event.offsetX;
        var y = event.offsetY;
        var pt = this.Layer.GetCamera().ConvertPointViewerToWorld(x,y);

        var width = this.Loop.GetLineWidth() / 2;
        // Tolerance: 5 screen pixels.
        var minWidth = 10.0 / this.Layer.GetPixelsPerUnit();
        if (width < minWidth) { width = minWidth;}

        if (this.Loop.PointOnShape(pt, width)) {
            return true;
        } else {
            return false;
        }
    }

    LassoWidget.prototype.GetActive = function() {
        return this.State != WAITING;
    }

    // Setting to active always puts state into "active".
    // It can move to other states and stay active.
    LassoWidget.prototype.SetActive = function(flag) {
        if (flag) {
            if (this.State == WAITING ) {
                this.State = ACTIVE;
                this.Loop.SetActive(true);
                this.PlacePopup();
                this.Layer.EventuallyDraw();
            }
        } else {
            if (this.State != WAITING) {
                this.Deactivate();
                this.Layer.DeactivateWidget(this);
            }
        }
        this.Layer.EventuallyDraw();
    }

    // It would be nice to put this as a superclass method, or call the
    // layer.RemoveWidget method instead.
    LassoWidget.prototype.RemoveFromLayer = function() {
        if (this.Layer) {
            this.RemoveWidget(this);
        }
    }

    // Can we bind the dialog apply callback to an objects method?
    LassoWidget.prototype.ShowPropertiesDialog = function () {
        this.Dialog.ColorInput.val(SAM.ConvertColorToHex(this.Loop.OutlineColor));
        this.Dialog.LineWidthInput.val((this.Loop.LineWidth).toFixed(2));

        var area = this.ComputeArea();
        var areaString = "" + area.toFixed(2);
        if (this.Loop.FixedSize) {
            areaString += " pixels^2";
        } else {
            areaString += " units^2";
        }
        this.Dialog.Area.text(areaString);
        this.Dialog.Show(true);
    }

    LassoWidget.prototype.DialogApplyCallback = function() {
        var hexcolor = this.Dialog.ColorInput.val();
        this.Loop.SetOutlineColor(hexcolor);
        this.Loop.LineWidth = parseFloat(this.Dialog.LineWidthInput.val());
        this.Loop.UpdateBuffers(this.Layer.AnnotationView);
        this.SetActive(false);
        if (window.SA) {SA.RecordState();}
        this.Layer.EventuallyDraw();

        localStorage.LassoWidgetDefaults = JSON.stringify({Color: hexcolor, LineWidth: this.Loop.LineWidth});
        if (SAM.NotesWidget) {SAM.NotesWidget.MarkAsModified();} // hack
    }

    /*
    // The real problem is aliasing.  Line is jagged with high frequency sampling artifacts.
    // Pass in the spacing as a hint to get rid of aliasing.
    LassoWidget.prototype.Decimate = function(shape, spacing) {
        // Keep looping over the line removing points until the line does not change.
        var modified = true;
        var sanityCheck = 0;
        while (modified) {
            modified = false;
            var newPoints = [];
            newPoints.push(shape.Points[0]);
            // Window of four points.
            var i = 3;
            while (i < shape.Points.length) {
                // Debugging a hang.  I do not think it occurs in decimate, but it might.
                if (++sanityCheck > 100000) {
                    alert("Decimate is takeing too long.");
                    return;
                }
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
    LassoWidget.prototype.CombineStroke = function() {
        // This algorithm was desinged to have the first point be the same as the last point.
        // To generalize polylineWidgets and lassoWidgets, I changed this and put a closed 
        // flag (which implicitely draws the last segment) in polyline.
        // It is easier to temporarily add the extra point and them remove it, than change the algorithm.
        this.Loop.Points.push(this.Loop.Points[0]);

        // Find the first and last intersection points between stroke and loop.
        var intersection0;
        var intersection1;
        for (var i = 1; i < this.Stroke.Points.length; ++i) {
            var pt0 = this.Stroke.Points[i-1];
            var pt1 = this.Stroke.Points[i];
            var tmp = this.FindIntersection(pt0, pt1);
            if (tmp) {
                // I need to insert the intersection in the stroke so
                // one stroke segment does not intersect loop twice.
                this.Stroke.Points.splice(i,0,tmp.Point);
                if (intersection0 == undefined) {
                    intersection0 = tmp;
                    intersection0.StrokeIndex = i;
                } else {
                    // If a point was added before first intersection,
                    // its index needs to be updated too.
                    if (tmp.LoopIndex < intersection0.LoopIndex) {
                        intersection0.LoopIndex += 1;
                    }
                    intersection1 = tmp;
                    intersection1.StrokeIndex = i;
                }
            }
        }

        var sanityCheck = 0;

        // If we have two intersections, clip the loop with the stroke.
        if (intersection1 != undefined) {
            // We will have two parts.
            // Build both loops keeing track of their lengths.
            // Keep the longer part.
            var points0 = [];
            var len0 = 0.0;
            var points1 = [];
            var len1 = 0.0;
            var i;
            // Add the clipped stroke to both loops.
            for (i = intersection0.StrokeIndex; i < intersection1.StrokeIndex; ++i) {
                points0.push(this.Stroke.Points[i]);
                points1.push(this.Stroke.Points[i]);
            }
            // Now the two new loops take different directions around the original loop.
            // Decreasing
            i = intersection1.LoopIndex;
            while (i != intersection0.LoopIndex) {
                if (++sanityCheck > 1000000) {
                    alert("Combine loop 1 is taking too long.");
                    return;
                }
                points0.push(this.Loop.Points[i]);
                var dx = this.Loop.Points[i][0];
                var dy = this.Loop.Points[i][1];
                // decrement around loop.  First and last loop points are the same.
                if (--i == 0) { i = this.Loop.Points.length - 1;}
                // Integrate distance.
                dx -= this.Loop.Points[i][0];
                dy -= this.Loop.Points[i][1];
                len0 += Math.sqrt(dx*dx + dy*dy);
            }
            // Duplicate the first point in the loop
            points0.push(intersection0.Point);

            // Increasing
            i = intersection1.LoopIndex;
            while (i != intersection0.LoopIndex) {
                if (++sanityCheck > 1000000) {
                    alert("Combine loop 2 is taking too long.");
                    return;
                }
                points1.push(this.Loop.Points[i]);
                var dx = this.Loop.Points[i][0];
                var dy = this.Loop.Points[i][1];
                //increment around loop.  First and last loop points are the same.
                if (++i == this.Loop.Points.length - 1) { i = 0;}
                // Integrate distance.
                dx -= this.Loop.Points[i][0];
                dy -= this.Loop.Points[i][1];
                len1 += Math.sqrt(dx*dx + dy*dy);
            }
            // Duplicate the first point in the loop
            points1.push(intersection0.Point);

            if (len0 > len1) {
                this.Loop.Points = points0;
            } else {
                this.Loop.Points = points1;
            }

            if (window.SA) {SA.RecordState();}
        }

        // Remove the extra point added at the begining of this method.
        this.Loop.Points.pop();
        this.Loop.UpdateBuffers(this.Layer.AnnotationView);
        this.ComputeActiveCenter();

        this.Stroke = false;
        this.Layer.EventuallyDraw();
    }


    // tranform all points so p0 is origin and p1 maps to (1,0)
    // Returns false if no intersection, 
    // If there is an intersection, it adds that point to the loop.
    // It returns {Point: newPt, LoopIndex: i} .
    LassoWidget.prototype.FindIntersection = function(p0, p1) {
        var best = false;
        var p = [(p1[0]-p0[0]), (p1[1]-p0[1])];
        var mag = Math.sqrt(p[0]*p[0] + p[1]*p[1]);
        if (mag < 0.0) { return false;}
        p[0] = p[0] / mag;
        p[1] = p[1] / mag;

        var m0 = this.Loop.Points[0];
        var n0 = [(m0[0]-p0[0])/mag, (m0[1]-p0[1])/mag];
        var k0 = [(n0[0]*p[0]+n0[1]*p[1]), (n0[1]*p[0]-n0[0]*p[1])];

        for (var i = 1; i < this.Loop.Points.length; ++i) {
            var m1 = this.Loop.Points[i];
            // Avoid an infinite loop inserting points.
            if (p0 == m0 || p0 == m1) { continue;}
            var n1 = [(m1[0]-p0[0])/mag, (m1[1]-p0[1])/mag];
            var k1 = [(n1[0]*p[0]+n1[1]*p[1]), (n1[1]*p[0]-n1[0]*p[1])];
            if ((k1[1] >= 0.0 && k0[1] <= 0.0) || (k1[1] <= 0.0 && k0[1] >= 0.0)) {
                var k = k0[1] / (k0[1]-k1[1]);
                var x = k0[0] + k*(k1[0]-k0[0]);
                if (x > 0 && x <=1) {
                    var newPt = [(m0[0]+k*(m1[0]-m0[0])), (m0[1]+k*(m1[1]-m0[1]))];
                    if ( ! best || x < best.k) {
                        best = {Point: newPt, LoopIndex: i, k: x};
                    }
                }
            }
            m0 = m1;
            n0 = n1;
            k0 = k1;
        }
        if (best) {
            this.Loop.Points.splice(best.LoopIndex,0,best.Point);
        }

        return best;
    }

    // This is not actually needed!  So it is not used.
    LassoWidget.prototype.IsPointInsideLoop = function(x, y) {
        // Sum up angles.  Inside poitns will sum to 2pi, outside will sum to 0.
        var angle = 0.0;
        var pt0 = this.Loop.Points[this.Loop.length - 1];
        for ( var i = 0; i < this.Loop.length; ++i)
        {
            var pt1 = this.Loop.Points[i];
            var v0 = [pt0[0]-x, pt0[1]-y];
            var v1 = [pt1[0]-x, pt1[1]-y];
            var mag0 = Math.sqrt(v0[0]*v0[0] + v0[1]*v0[1]);
            var mag1 = Math.sqrt(v1[0]*v1[0] + v1[1]*v1[1]);
            angle += Math.arcsin((v0[0]*v1[1] - v0[1]*v1[0])/(mag0*mag1));
        }

        return (angle > 3.14 || angle < -3.14);
    }
    
    LassoWidget.prototype.ComputeArea = function() {
        var area = 0.0;
        // Use the active center. It should be more numerical stable.
        // Iterate over triangles
        var vx1 = this.Loop.Points[0][0] - this.ActiveCenter[0];
        var vy1 = this.Loop.Points[0][1] - this.ActiveCenter[1];
        for (var j = 1; j < this.Loop.Points.length; ++j) {
            // Area of triangle is 1/2 magnitude of cross product.
            var vx2 = vx1;
            var vy2 = vy1;
            vx1 = this.Loop.Points[j][0] - this.ActiveCenter[0];
            vy1 = this.Loop.Points[j][1] - this.ActiveCenter[1];
            area += (vx1*vy2) - (vx2*vy1);
        }

        if (area < 0) {
            area = -area;
        }
        return area;
    }

    
    SAM.LassoWidget = LassoWidget;

})();
