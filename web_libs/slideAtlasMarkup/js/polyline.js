// Polyline. one line witn multiple segments.

(function () {
    "use strict";

    function Polyline() {
        SAM.Shape.call(this);
        this.Origin = [0.0,0.0]; // Center in world coordinates.
        this.Points = [];
        this.Closed = false;
        this.Bounds = [0,-1,0,-1];
    };
    Polyline.prototype = new SAM.Shape;


    //Polyline.prototype.destructor=function() {
        // Get rid of the buffers?
    //}

    Polyline.prototype.SetLineWidth = function(lineWidth) {
        this.LineWidth = lineWidth;
    }

    Polyline.prototype.GetLineWidth = function() {
        return this.LineWidth;
    }

    Polyline.prototype.GetEdgeLength = function(edgeIdx) {
        if (edgeIdx < 0 || edgeIdx > this.Points.length-2) {
            return 0;
        }
        var dx = this.Points[edgeIdx+1][0] - this.Points[edgeIdx][0];
        var dy = this.Points[edgeIdx+1][1] - this.Points[edgeIdx][1];

        return Math.sqrt(dx*dx + dy*dy);
    }

    Polyline.prototype.GetNumberOfPoints = function() {
        return this.Points.length;
    }

    // Internal bounds will ignore origin and orientation.
    Polyline.prototype.GetBounds = function () {
        var bounds = this.Bounds.slice(0);
        bounds[0] += this.Origin[0];
        bounds[1] += this.Origin[0];
        bounds[2] += this.Origin[1];
        bounds[3] += this.Origin[1];
        return bounds;
    }

    // Returns 0 if is does not overlap at all.
    // Returns 1 if part of the section is in the bounds.
    // Returns 2 if all of the section is in the bounds.
    Polyline.prototype.ContainedInBounds = function(bds) {
        // Need to get world bounds.
        var myBds = this.GetBounds();

        // Polyline does not cache bounds, so just look to the points.
        if (bds[1] < myBds[0] || bds[0] > myBds[1] ||
            bds[3] < myBds[2] || bds[2] > myBds[3]) {
            return 0;
        }
        if (bds[1] >= myBds[0] && bds[0] <= myBds[1] &&
            bds[3] >= myBds[2] && bds[2] <= myBds[3]) {
            return 2;
        }
        return 1;
    }

    Polyline.prototype.SetOrigin = function(origin) {
        this.Origin = origin.slice(0);
    }

    // Adds origin to points and sets origin to 0.
    Polyline.prototype.ResetOrigin = function(view) {
        for (var i = 0; i < this.Points.length; ++i) {
            var pt = this.Points[i];
            pt[0] += this.Origin[0];
            pt[1] += this.Origin[1];
        }
        this.Origin[0] = 0;
        this.Origin[1] = 0;
        this.UpdateBuffers(view);
    }


    // Returns -1 if the point is not on a vertex.
    // Returns the index of the vertex is the point is within dist of a the
    // vertex.
    Polyline.prototype.PointOnVertex = function(pt, dist) {
        dist = dist * dist;
        for (var i = 0; i < this.Points.length; ++i) {
            var dx = this.Points[i][0] - pt[0];
            var dy = this.Points[i][1] - pt[1];
            if (dx*dx + dy*dy < dist) {
                return i;
            }
        }
        return -1;
    }

    // Returns undefined if the point is not on the shape.
    // Otherwise returns the indexes of the segment touched [i0, i1, k].
    Polyline.prototype.PointOnShape = function(pt, dist) {
        // Make a copy of the point (array).
        pt = pt.slice(0);
        pt[0] -= this.Origin[0];
        pt[1] -= this.Origin[1];
        // NOTE: bounds already includes lineWidth
        if (pt[0]+dist < this.Bounds[0] || pt[0]-dist > this.Bounds[1] ||
            pt[1]+dist < this.Bounds[2] || pt[1]-dist > this.Bounds[3]) {
            return undefined;
        }
        // Check for mouse touching an edge.
        for (var i = 1; i < this.Points.length; ++i) {
            var k = this.IntersectPointLine(pt, this.Points[i-1],
                                            this.Points[i], dist);
            if (k !== undefined) {
                return [i-1,i, k];
            }
        }
        if (this.Closed) {
            var k = this.IntersectPointLine(pt, this.Points[this.Points.length-1],
                                            this.Points[0], dist);
            if (k !== undefined) {
                return [this.Points.length-1, 0, k];
            }
        }
        return undefined;
    }

    // Find a world location of a popup point given a camera.
    Polyline.prototype.FindPopupPoint = function(cam) {
        if (this.Points.length == 0) { return; }
        var roll = cam.Roll;
        var s = Math.sin(roll + (Math.PI*0.25));
        var c = Math.cos(roll + (Math.PI*0.25));
        var bestPt = this.Points[0];
        var bestProjection = (c*bestPt[0])-(s*bestPt[1]);
        for (var i = 1; i < this.Points.length; ++i) {
            var pt = this.Points[i];
            var projection = (c*pt[0])-(s*pt[1]);
            if (projection > bestProjection) {
                bestProjection = projection;
                bestPt = pt;
            }
        }
        bestPt[0] += this.Origin[0];
        bestPt[1] += this.Origin[1];
        return bestPt;
    }

    Polyline.prototype.MergePoints = function (thresh, view) {
        thresh = thresh * thresh;
        var modified = false;
        for (var i = 1; i < this.Points.length; ++i) {
            var dx = this.Points[i][0] - this.Points[i-1][0];
            var dy = this.Points[i][1] - this.Points[i-1][1];
            if (dx*dx + dy*dy < thresh) {
                // The two points are close. Remove the point.
                this.Points.splice(i,1);
                // Removing elements from the array we are iterating over.
                --i;
                modified = true;
            }
        }
        if (modified) {
            this.UpdateBuffers(view);
        }
    }

    // The real problem is aliasing.  Line is jagged with high frequency sampling artifacts.
    // Pass in the spacing as a hint to get rid of aliasing.
    Polyline.prototype.Decimate = function (spacing, view) {
        // Keep looping over the line removing points until the line does not change.
        var modified = true;
        while (modified) {
            modified = false;
            var newPoints = [];
            newPoints.push(this.Points[0]);
            // Window of four points.
            var i = 3;
            while (i < this.Points.length) {
                var p0 = this.Points[i];
                var p1 = this.Points[i-1];
                var p2 = this.Points[i-2];
                var p3 = this.Points[i-3];
                // Compute the average of the center two.
                var cx = (p1[0] + p2[0]) * 0.5;
                var cy = (p1[1] + p2[1]) * 0.5;
                // Find the perendicular normal.
                var nx = (p0[1] - p3[1]);
                var ny = -(p0[0] - p3[0]);
                var mag = Math.sqrt(nx*nx + ny*ny);
                nx = nx / mag;
                ny = ny / mag;
                mag = Math.abs(nx*(cx-this.Points[i-3][0]) + ny*(cy-this.Points[i-3][1]));
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
                    newPoints.push(this.Points[i-2]);
                    ++i;
                }
            }
            // Copy the remaing point / 2 points
            i = i-2;
            while (i < this.Points.length) {
                newPoints.push(this.Points[i]);
                ++i;
            }
            this.Points = newPoints;
        }
        this.UpdateBuffers(view);
    }

    Polyline.prototype.AddPointToBounds = function(pt, radius) {
        if (pt[0]-radius < this.Bounds[0]) {
            this.Bounds[0] = pt[0]-radius;
        }
        if (pt[0]+radius > this.Bounds[1]) {
            this.Bounds[1] = pt[0]+radius;
        }

        if (pt[1]-radius < this.Bounds[2]) {
            this.Bounds[2] = pt[1]-radius;
        }
        if (pt[1]+radius > this.Bounds[3]) {
            this.Bounds[3] = pt[1]+radius;
        }
    }

    // NOTE: Line thickness is handled by style in canvas.
    // I think the GL version that uses triangles is broken.
    Polyline.prototype.UpdateBuffers = function(view) {
        var points = this.Points.slice(0);
        if (this.Closed && points.length > 2) {
            points.push(points[0]);
        }
        this.PointBuffer = [];
        var cellData = [];
        var lineCellData = [];
        this.Matrix = mat4.create();
        mat4.identity(this.Matrix);

        if (this.Points.length == 0) { return; }
        // xMin,xMax, yMin,yMax
        this.Bounds = [points[0][0],points[0][0],points[0][1],points[0][1]];

        if (this.LineWidth == 0 || !view.gl ) {
            for (var i = 0; i < points.length; ++i) {
                this.PointBuffer.push(points[i][0]);
                this.PointBuffer.push(points[i][1]);
                this.PointBuffer.push(0.0);
                this.AddPointToBounds(points[i], 0);
            }
            // Not used for line width == 0.
            for (var i = 2; i < points.length; ++i) {
                cellData.push(0);
                cellData.push(i-1);
                cellData.push(i);
            }
        } else {
            // Compute a list normals for middle points.
            var edgeNormals = [];
            var mag;
            var x;
            var y;
            var end = points.length-1;
            // Compute the edge normals.
            for (var i = 0; i < end; ++i) {
                x = points[i+1][0] - points[i][0];
                y = points[i+1][1] - points[i][1];
                mag = Math.sqrt(x*x + y*y);
                edgeNormals.push([-y/mag,x/mag]);
            }

            if ( end > 0 ) {
                var half = this.LineWidth / 2.0;
                // 4 corners per point
                var dx = edgeNormals[0][0]*half;
                var dy = edgeNormals[0][1]*half;
                this.PointBuffer.push(points[0][0] - dx);
                this.PointBuffer.push(points[0][1] - dy);
                this.PointBuffer.push(0.0);
                this.PointBuffer.push(points[0][0] + dx);
                this.PointBuffer.push(points[0][1] + dy);
                this.PointBuffer.push(0.0);
                this.AddPointToBounds(points[i], half);
                for (var i = 1; i < end; ++i) {
                    this.PointBuffer.push(points[i][0] - dx);
                    this.PointBuffer.push(points[i][1] - dy);
                    this.PointBuffer.push(0.0);
                    this.PointBuffer.push(points[i][0] + dx);
                    this.PointBuffer.push(points[i][1] + dy);
                    this.PointBuffer.push(0.0);
                    dx = edgeNormals[i][0]*half;
                    dy = edgeNormals[i][1]*half;
                    this.PointBuffer.push(points[i][0] - dx);
                    this.PointBuffer.push(points[i][1] - dy);
                    this.PointBuffer.push(0.0);
                    this.PointBuffer.push(points[i][0] + dx);
                    this.PointBuffer.push(points[i][1] + dy);
                    this.PointBuffer.push(0.0);
                }
                this.PointBuffer.push(points[end][0] - dx);
                this.PointBuffer.push(points[end][1] - dy);
                this.PointBuffer.push(0.0);
                this.PointBuffer.push(points[end][0] + dx);
                this.PointBuffer.push(points[end][1] + dy);
                this.PointBuffer.push(0.0);
            }
            // Generate the triangles for a thick line
            for (var i = 0; i < end; ++i) {
                lineCellData.push(0 + 4*i);
                lineCellData.push(1 + 4*i);
                lineCellData.push(3 + 4*i);
                lineCellData.push(0 + 4*i);
                lineCellData.push(3 + 4*i);
                lineCellData.push(2 + 4*i);
            }

            // Not used.
            for (var i = 2; i < points.length; ++i) {
                cellData.push(0);
                cellData.push((2*i)-1);
                cellData.push(2*i);
            }
        }

        if (view.gl) {
            this.VertexPositionBuffer = view.gl.createBuffer();
            view.gl.bindBuffer(view.gl.ARRAY_BUFFER, this.VertexPositionBuffer);
            view.gl.bufferData(view.gl.ARRAY_BUFFER, new Float32Array(this.PointBuffer), view.gl.STATIC_DRAW);
            this.VertexPositionBuffer.itemSize = 3;
            this.VertexPositionBuffer.numItems = this.PointBuffer.length / 3;

            this.CellBuffer = view.gl.createBuffer();
            view.gl.bindBuffer(view.gl.ELEMENT_ARRAY_BUFFER, this.CellBuffer);
            view.gl.bufferData(view.gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(cellData), view.gl.STATIC_DRAW);
            this.CellBuffer.itemSize = 1;
            this.CellBuffer.numItems = cellData.length;

            if (this.LineWidth != 0) {
                this.LineCellBuffer = view.gl.createBuffer();
                view.gl.bindBuffer(view.gl.ELEMENT_ARRAY_BUFFER, this.LineCellBuffer);
                view.gl.bufferData(view.gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(lineCellData), view.gl.STATIC_DRAW);
                this.LineCellBuffer.itemSize = 1;
                this.LineCellBuffer.numItems = lineCellData.length;
            }
        }
    }


    // GLOBAL To Position the orientatation of the edge.
    var EDGE_COUNT = 0;
    var EDGE_ANGLE = (2*Math.PI) * 0/24;
    var EDGE_OFFSET = 0; // In screen pixels.
    var EDGE_ROOT = "edge";
    var EDGE_DELAY = 200;
    // Saves images centered at spots on the edge.
    // Roll is set to put the edge horizontal.
    // Step is in screen pixel units
    // Count is the starting index for file name generation.
    Polyline.prototype.SampleEdge = function(viewer, dim, step, count, callback) {
        var cam = viewer.GetCamera();
        var scale = cam.GetHeight() / cam.ViewportHeight;
        // Convert the step from screen pixels to world.
        step *= scale;
        var cache = viewer.GetCache();
        var dimensions = [dim,dim];
        // Distance between edge p0 to next sample point.
        var remaining = step/2;
        // Recursive to serialize asynchronous cutouts.
        this.RecursiveSampleEdge(this.Points.length-1,0,remaining,step,count,
                                 cache,dimensions,scale, callback);
    }
    Polyline.prototype.RecursiveSampleEdge = function(i0,i1,remaining,step,count,
                                                      cache,dimensions,scale, callback) {
        var pt0 = this.Points[i0];
        var pt1 = this.Points[i1];
        // Compute the length of the edge.
        var dx = pt1[0]-pt0[0];
        var dy = pt1[1]-pt0[1];
        var length = Math.sqrt(dx*dx +dy*dy);
        // Take steps along the edge (size 'step')
        if (remaining > length) {
            // We passed over this edge. Move to the next edge.
            remaining = remaining - length;
            i0 = i1;
            i1 += 1;
            // Test for terminating condition.
            if (i1 < this.Points.length) {
                this.RecursiveSampleEdge(i0,i1,remaining,step, count,
                                         cache,dimensions,scale, callback);
            } else {
                (callback)();
            }
        } else {
            var self = this;
            // Compute the sample point and tangent on this edge.
            var edgeAngle = -Math.atan2(dy,dx) + EDGE_ANGLE;
            var k = remaining / length;
            var x = pt0[0] + k*(pt1[0]-pt0[0]);
            var y = pt0[1] + k*(pt1[1]-pt0[1]);
            // Normal (should be out if loop is clockwise).
            var nx = -dy;
            var ny = dx;
            var mag = Math.sqrt(nx*nx + ny*ny);
            nx = (nx / mag) * EDGE_OFFSET * scale;
            ny = (ny / mag) * EDGE_OFFSET * scale;

            // Save an image at this sample point.
            GetCutoutImage(cache,dimensions,[x+nx,y+ny],scale,
                           edgeAngle,EDGE_ROOT+count+".png",
                           function() {
                               setTimeout(
                                   function () {
                                       ++count;
                                       EDGE_COUNT = count;
                                       remaining += step;
                                       self.RecursiveSampleEdge(i0,i1,remaining,step,count,
                                                                cache,dimensions,scale,callback);
                                   }, EDGE_DELAY);
                           });
        }
    }


    Polyline.prototype.SetActive = function(flag) {
        this.Active = flag;
    }


    SAM.Polyline = Polyline;

})();
