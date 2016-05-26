//==============================================================================
// Initially a contour found for each section in a stack.
// Each section gets on of these StackSectionWidgets.  I am extending this
// to include multiple contours fo sections that have multiple pieces,
// and internal contours / features.  Internal edges may not be closed
// loops.
// Initialy, these widgets will have no interaction, so they might
// be better as shapes, but we will see.

// Eventually I will put a transformation in here.
// Also, I would like this to have its own instance variable in
// the viewerRecord.


(function () {
    // Depends on the CIRCLE widget
    "use strict";

    function StackSectionWidget (viewer) {
        var self = this;

        this.Thumb = null; // default click. in stack creator.

        // Active is just to turn the section yellow temporarily.
        this.Active = false;
        this.Color = [0,1,0];
        this.Shapes = [];

        this.Bounds = null;
        if (viewer) {
            this.Viewer = viewer;
            this.Viewer.AddWidget(this);
        }
    }

    StackSectionWidget.prototype.IsEmpty = function() {
        return this.Shapes.length == 0;
    }

    // Add all the lines in the in section to this section.
    StackSectionWidget.prototype.Union = function(section) {
        for (var i = 0; i < section.Shapes.length; ++i) {
            this.Shapes.push(section.Shapes[i]);
        }
        this.Bounds = null;
    }

    // Bounds are in slide / world coordinates.
    // Returns 0 if is does not overlap at all.
    // Returns 1 if part of the section is in the bounds.
    // Returns 2 if all of the section is in the bounds.
    StackSectionWidget.prototype.ContainedInBounds = function(bds) {
        var sBds = this.GetBounds();
        if (sBds[0] > bds[0] && sBds[1] < bds[1] &&
            sBds[2] > bds[2] && sBds[3] < bds[3]) {
            // section is fully contained in the bounds.
            return 2;
        }
        if (sBds[1] < bds[0] || sBds[0] > bds[1] ||
            sBds[3] < bds[2] || sBds[2] > bds[3] ) {
            // No overlap of bounds.
            return 0;
        }

        // Bounds partially overlap.  Look closer.
        var pointsIn = false;
        var pointsOut = false;
        for (var i = 0; i < this.Shapes.length; ++i) {
            var contained = this.Shapes[i].ContainedInBounds(bds);
            if (contained == 1) {
                return 1;
            }
            if (contained == 0) {
                pointsOut = true;
            }
            if (contained == 2) {
                pointsIn = true;
            }
            if (pointsIn && pointsOut) {
                return 1;
            }
        }

        if (pointsIn) {
            return 2;
        }
        return 0;
    }

    // Returns the center of the bounds in view coordinates.
    StackSectionWidget.prototype.GetViewCenter = function(view) {
        var bds = this.GetBounds();
        return view.Camera.ConvertPointWorldToViewer((bds[0]+bds[1])*0.5,
                                                     (bds[2]+bds[3])*0.5);
    }

    // We need bounds in view coordiantes for sorting.
    // Do not bother caching the value.
    StackSectionWidget.prototype.GetViewBounds = function (view) {
        if (this.Shapes.length == 0) {
            return [0,0,0,0];
        }
        var c = this.GetViewCenter(view);
        var bds = [c[0],c[0],c[1],c[1]];
        for (var i = 0; i < this.Shapes.length; ++i) {
            var shape = this.Shapes[i];
            for (j = 0; j < shape.Points.length; ++j) {
                var pt = shape.Points[j];
                pt = view.Camera.ConvertPointWorldToViewer(pt[0],pt[1]);
                if (pt[0] < bds[0]) { bds[0] = pt[0]; }
                if (pt[0] > bds[1]) { bds[1] = pt[0]; }
                if (pt[1] < bds[2]) { bds[2] = pt[1]; }
                if (pt[1] > bds[3]) { bds[3] = pt[1]; }
            }
        }
        return bds;
    }


    StackSectionWidget.prototype.ComputeViewUpperRight = function(view) {
        // Compute the upper right corner in view coordinates.
        // This is used by the SectionsWidget holds this section.
        var bds = this.GetBounds();
        var p0 = view.Camera.ConvertPointWorldToViewer(bds[0],bds[2]);
        var p1 = view.Camera.ConvertPointWorldToViewer(bds[0],bds[3]);
        var p2 = view.Camera.ConvertPointWorldToViewer(bds[1],bds[3]);
        var p3 = view.Camera.ConvertPointWorldToViewer(bds[1],bds[2]);
        // Pick the furthest upper right corner.
        this.ViewUpperRight = p0;
        var best = p0[0]-p0[1];
        var tmp = p1[0]-p1[1];
        if (tmp > best) {
            best = tmp;
            this.ViewUpperRight = p1;
        }
        tmp = p2[0]-p2[1];
        if (tmp > best) {
            best = tmp;
            this.ViewUpperRight = p2;
        }
        tmp = p3[0]-p3[1];
        if (tmp > best) {
            best = tmp;
            this.ViewUpperRight = p3;
        }
    }


    StackSectionWidget.prototype.Draw = function(view) {
        this.ComputeViewUpperRight(view);
        for (var i = 0; i < this.Shapes.length; ++i) {
            if (this.Active) {
                this.Shapes[i].OutlineColor = [1,1,0];
            } else {
                this.Shapes[i].OutlineColor = this.Color;
            }
            this.Shapes[i].Draw(view);
        }
    }

    StackSectionWidget.prototype.Serialize = function() {
        // Backing away from 'every section has a contour'.
        if (this.Thumb) { 
            return null;
        }
        var obj = new Object();
        obj.type = "stack_section";
        obj.color = this.Color;
        obj.shapes = [];
        for (var i = 0; i < this.Shapes.length; ++i) {
            var shape = this.Shapes[i];
            // Is is a pain that polyline does not serialize.
            var polyLineObj = {
                closedloop: shape.Closed,
                points: []};
            for (var j = 0; j < shape.Points.length; ++j) {
                polyLineObj.points.push([shape.Points[j][0], shape.Points[j][1]]);
            }
            obj.shapes.push(polyLineObj);
        }
        return obj;
    }


    // Load a widget from a json object (origin MongoDB).
    StackSectionWidget.prototype.Load = function(obj) {
        if (obj.color) {
            this.Color[0] = parseFloat(obj.color[0]);
            this.Color[1] = parseFloat(obj.color[1]);
            this.Color[2] = parseFloat(obj.color[2]);
        }
        if ( ! obj.shapes) {
            return;
        }
        for(var n=0; n < obj.shapes.length; n++){
            var polylineObj = obj.shapes[n];
            if ( polylineObj.points) { 
                var points = polylineObj.points;
                var shape = new SAM.Polyline();
                shape.OutlineColor = this.Color;
                shape.FixedSize = false;
                shape.LineWidth = 0;
                if (polylineObj.closedloop) {
                    shape.Closed = polylineObj.closedloop;
                }
                this.Shapes.push(shape);
                for (var m = 0; m < points.length; ++m) {
                    shape.Points[m] = [points[m][0], points[m][1]];
                }
                shape.UpdateBuffers(this.Layer.AnnotationView);
            }
        }
    }

    // We could recompute the bounds from the
    StackSectionWidget.prototype.GetCenter = function () {
        var bds = this.GetBounds();
        return [(bds[0]+bds[1])*0.5, (bds[2]+bds[3])*0.5];
    }

    // We could recompute the bounds from the
    StackSectionWidget.prototype.GetBounds = function () {
        // Special case for simple thumb selection.
        if (this.Thumb) {
            var rad = this.Thumb.Height * this.Thumb.ScreenPixelSpacing / 4.0;
            var cx = this.ThumbX;
            var cy = this.ThumbY;
            return [cx-rad, cx+rad, cy-rad, cy+rad];
        }

        if (this.Shapes.length == 0) {
            return this.Bounds;
        }
        if ( ! this.Bounds) {
            this.Bounds = this.Shapes[0].GetBounds();
            for (var i = 1; i < this.Shapes.length; ++i) {
                var bds = this.Shapes[i].GetBounds();
                if (bds[0] < this.Bounds[0]) this.Bounds[0] = bds[0];
                if (bds[1] > this.Bounds[1]) this.Bounds[1] = bds[1];
                if (bds[2] < this.Bounds[2]) this.Bounds[2] = bds[2];
                if (bds[3] > this.Bounds[3]) this.Bounds[3] = bds[3];
            }
        }
        return this.Bounds.slice(0);
    }

    StackSectionWidget.prototype.Deactivate = function() {
        this.Viewer.DeactivateWidget(this);
        for (var i = 0; i < this.Shapes.length; ++i) {
            this.Shapes[i].Active = false;
        }
        eventuallyRender();
    }

    StackSectionWidget.prototype.HandleKeyPress = function(keyCode, shift) {
        return true;
    }

    StackSectionWidget.prototype.HandleMouseDown = function(event) {
        return true;
    }

    StackSectionWidget.prototype.HandleMouseUp = function(event) {
        return true;
    }
    
    StackSectionWidget.prototype.HandleDoubleClick = function(event) {
        return true;
    }

    StackSectionWidget.prototype.HandleMouseMove = function(event) {
        return true
    }

    StackSectionWidget.prototype.CheckActive = function(event) {
        return false;
    }

    StackSectionWidget.prototype.GetActive = function() {
        return false;
    }

    // Setting to active always puts state into "active".
    // It can move to other states and stay active.
    StackSectionWidget.prototype.SetActive = function(flag) {
        if (flag) {
            this.Viewer.ActivateWidget(this);
            for (var i = 0; i < this.Shapes.length; ++i) {
                this.Shapes[i].Active = true;
            }

            eventuallyRender();
        } else {
            this.Deactivate();
            this.Viewer.DeactivateWidget(this);
        }
    }

    StackSectionWidget.prototype.RemoveFromViewer = function() {
        if (this.Viewer) {
            this.Viewer.RemoveWidget(this);
        }
    }

    //==============================================================================
    // These features might better belong in a separate object of edges.

    // Modifies this section's points to match argument section
    // Also returns the translation and rotation.
    StackSectionWidget.prototype.RigidAlign = function (section, trans) {
        var center1 = this.GetCenter();
        var center2 = section.GetCenter();
        // Translate so that the centers are the same.
        //this.Translate([(center2[0]-center1[0]),
        //                (center2[1]-center2[1])]);

        // Lets use a transformation instead.  It will be easier for the stack
        // editor.
        trans[0] = (center2[0]-center1[0]);
        trans[1] = (center2[1]-center1[1]);

        if (this.Thumb || section.Thumb) {
            trans[2] = 0;
            return;
        }

        // Get the bounds of both contours.
        var bds1 = this.GetBounds();
        bds1[0] += trans[0];  bds1[1] += trans[0];
        bds1[2] += trans[1];  bds1[3] += trans[1];
        var bds2 = section.GetBounds();

        // Combine them (union).
        bds2[0] = Math.min(bds1[0], bds2[0]);
        bds2[1] = Math.max(bds1[1], bds2[1]);
        bds2[2] = Math.min(bds1[2], bds2[2]);
        bds2[3] = Math.max(bds1[3], bds2[3]);
        // Exapnd the contour by 10%
        var xMid = (bds2[0] + bds2[1])*0.5;
        var yMid = (bds2[2] + bds2[3])*0.5;
        bds2[0] = xMid + 1.1*(bds1[0]-xMid);
        bds2[1] = xMid + 1.1*(bds1[1]-xMid);
        bds2[2] = yMid + 1.1*(bds1[2]-yMid);
        bds2[3] = yMid + 1.1*(bds1[3]-yMid);

        var spacing;
        // choose a spacing.
        // about 160,000 kPixels (400x400);
        spacing = Math.sqrt((bds2[1]-bds2[0])*(bds2[3]-bds2[2])/160000);
        // Note. gradient decent messes up with spacing too small.

        var distMap = new SA.DistanceMap(bds2, spacing);
        for (var i = 0; i < section.Shapes.length; ++i) {
            // ignore origin.
            distMap.AddPolyline(section.Shapes[i]);
        }
        distMap.Update();

        eventuallyRender();
        // Coordinate system has changed.
        this.RigidAlignWithMap(distMap, trans);
    }

    // Perform gradient descent on the transform....
    // Do not apply to the points.
    // trans is the starting position as well as the return value.
    StackSectionWidget.prototype.RigidAlignWithMap = function(distMap, trans) {
        // Compute center of rotation
        var center = this.GetCenter();

        // shiftX, shiftY, roll
        var tmpTrans = [0,0,0];

        // Try several rotations to see which is the best.
        bestTrans = null;
        bestDist = -1;
        for (a = -180; a < 180; a += 30) {
            tmpTrans = [trans[0],trans[1],Math.PI*a/180];
            var dist;
            for (i = 0; i < 5; ++i) {
                dist = this.RigidDecentStep(tmpTrans, center, distMap, 200000);
            }
            // For symetrical cases, give no rotation a slight advantage.
            dist = dist * (1.0 + Math.abs(a/180));
            if (bestDist < 0 || dist < bestDist) {
                bestDist = dist;
                bestTrans = tmpTrans.slice(0);
            }
        }

        // Now the real gradient decent.
        tmpTrans = bestTrans;
        // Slowing discount outliers.
        var aveDist = 200000;
        for (var i = 0; i < 100; ++i) {
            aveDist = this.RigidDecentStep(tmpTrans, center, distMap, aveDist);
        }
        // caller can do this if they want.
        //this.Transform([trans[0],trans[1]], center, trans[2]);
        // Just return the transformation parameters.
        // The center is als part of the transform, but it can be gotten with GetCenter.
        trans[0] = tmpTrans[0];
        trans[1] = tmpTrans[1];
        trans[2] = tmpTrans[2];
    }

    // Returns the average distance as the error.
    // trans is the starting transform (dx,dy, dRoll). This state is modified
    // by this method.
    // Center: center of rotation.
    // distMap is the array of distances.
    // Threshold sets large distances to a constant. It should be reduced to
    // minimize the contribution of outliers. Thresh is in units of map pixels.
    StackSectionWidget.prototype.RigidDecentStep = function (trans, center,
                                                             distMap, thresh) {
        var vx,vy, rx,ry;
        var s = Math.sin(trans[2]);
        var c = Math.cos(trans[2]);
        var sumx = 0, sumy = 0, totalDist = 0;
        var sumr = 0;
        var numContributingPoints = 0;
        for (var j = 0; j < this.Shapes.length; ++j) {
            var shape = this.Shapes[j];
            //var debugScalars = new Array(shape.Points.length);
            //shape.DebugScalars = debugScalars;
            for (var k = 0; k < shape.Points.length; ++k) {
                var pt = shape.Points[k];
                var x = pt[0];
                var y = pt[1];

                // transform the point.
                vx = (x-center[0]);
                vy = (y-center[1]);
                rx =  c*vx + s*vy;
                ry = -s*vx + c*vy;
                x = x + (rx-vx) + trans[0];
                y = y + (ry-vy) + trans[1];

                // Get the distance for this point.
                var dist = distMap.GetDistance(x,y) * distMap.Spacing;
                totalDist += dist;
                // Use threshold to minimize effect of outliers.
                //debugScalars[k] = (thresh)/(thresh + dist);
                //dist = (thresh*dist)/(thresh + dist);

                //debugScalars[k] = (dist < thresh) ? 1:0;
                //if (dist > thresh) {dist = 0;}
                //debugScalars[k] = Math.exp(-0.69*(dist*dist)/(thresh*thresh));
                var gs = 1;
                if (thresh > 0) {gs = Math.exp(-0.69*(dist*dist)/(thresh*thresh));}
                dist = dist * gs;

                // Scale the negative gradient by thresholded distance.
                var grad = distMap.GetGradient(x,y);
                var mag = Math.sqrt(grad[0]*grad[0] + grad[1]*grad[1]);

                if (mag > 0) {
                    ++numContributingPoints;

                    // Keep a total for translation
                    grad[0] = -grad[0] * dist / mag;
                    grad[1] = -grad[1] * dist / mag;
                    sumx += grad[0];
                    sumy += grad[1];

                    // For rotation
                    var cross = ry*grad[0]-rx*grad[1];
                    sumr += cross / (rx*rx + ry*ry);
                } else {
                    var skip = 1;
                }
            }
        }

        var aveDist = totalDist / numContributingPoints;
        // Trying to be intelligent about the step size
        trans[0] += sumx / numContributingPoints;
        trans[1] += sumy / numContributingPoints;
        trans[2] += sumr / numContributingPoints;

        // for debugging (the rest is in shape.js
        //t = {cx: center[0], cy: center[1], 
        //     c: Math.cos(trans[2]), s: Math.sin(trans[2]),
        //     sx: trans[0], sy: trans[1]};
        //for (var i = 0; i < this.Shapes.length; ++i) {
        //    this.Shapes[i].Trans = t;
        //}
        //VIEWER1.Draw();

        return aveDist;
    }
    
    StackSectionWidget.prototype.Transform = function (shift, center, roll) {
        this.Bounds = null;
        for (var i = 0; i < this.Shapes.length; ++i) {
            var shape = this.Shapes[i];
            shape.Trans = null;
            for (var j = 0; j < shape.Points.length; ++j) {
                var pt = shape.Points[j];
                var x = pt[0];
                var y = pt[1];
                var vx = x-center[0];
                var vy = y-center[1];
                var s = Math.sin(roll);
                var c = Math.cos(roll);
                var rx =  c*vx + s*vy;
                var ry = -s*vx + c*vy;
                pt[0] = x + (rx-vx) + shift[0];
                pt[1] = y + (ry-vy) + shift[1];
            }
            shape.UpdateBuffers(this.Layer.AnnotationView);
        }
    }

    // shift is [x,y]
    StackSectionWidget.prototype.Translate = function (shift) {
        this.Bounds = null;
        for (var i = 0; i < this.Shapes.length; ++i) {
            var shape = this.Shapes[i];
            for (var j = 0; j < shape.Points.length; ++j) {
                var pt = shape.Points[j];
                pt[0] += shift[0];
                pt[1] += shift[1];
            }
            shape.UpdateBuffers(this.Layer.AnnotationView);
        }
    }

    // I could also implement a resample to get uniform spacing.
    StackSectionWidget.prototype.RemoveDuplicatePoints = function (epsilon) {
        if ( epsilon == undefined) {
            epsilon = 0;
        }
        for (var i = 0; i < this.Shapes.length; ++i) {
            var shape = this.Shapes[i];
            var p0 = shape.Points[shape.Points.length-1];
            var idx = 0;
            while (idx < shape.Points.length) {
                var p1 = shape.Points[idx];
                var dx = p1[0] - p0[0];
                var dy = p1[1] - p0[1];
                if (Math.sqrt(dx*dx + dy*dy) <= epsilon) {
                    shape.Points.splice(idx,1);
                } else {
                    ++idx;
                    p0 = p1;
                }
            }
            shape.UpdateBuffers(this.Layer.AnnotationView);
        }
    }


    StackSectionWidget.prototype.Decimate = function() {
        var bds = this.GetBounds();
        var spacing = (bds[1]-bds[0] + bds[3]-bds[2]) / 400;
        for (var i = 0; i < this.Shapes.length; ++i) {
            this.Shapes[i].Decimate(spacing);
        }
    }


    SAM.StackSectionWidget = StackSectionWidget;

})();


