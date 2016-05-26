// Originally to hold a set of polylines for the pencil widget.

(function () {
    // Depends on the CIRCLE widget
    "use strict";

    function ShapeGroup() {
        this.Shapes = [];
        this.Bounds = [0,-1,0,-1];
    };

    ShapeGroup.prototype.GetBounds = function () {
        return this.Bounds;
    }

    // Returns 0 if is does not overlap at all.
    // Returns 1 if part of the section is in the bounds.
    // Returns 2 if all of the section is in the bounds.
    ShapeGroup.prototype.ContainedInBounds = function(bds) {
        if (this.Shapes.length == 0) { return 0;}
        var retVal = this.Shapes[0].ContainedInBounds(bds);
        for (var i = 1; i < this.Shapes.length; ++i) {
            if (retVal == 1) {
                // Both inside and outside. Nothing more to check.
                return retVal;
            }
            var shapeVal = this.Shapes[i].ContainedInBounds(bds);
            if (retVal == 0 && shapeVal != 0) {
                retVal = 1;
            }
            if (retVal == 2 && shapeVal != 2) {
                retVal = 1;
            }
        }
        return retVal;
    }

    ShapeGroup.prototype.PointOnShape = function(pt, dist) {
        for (var i = 0; i < this.Shapes.length; ++i) {
            if (this.Shapes[i].PointOnShape(pt,dist)) {
                return true;
            }
        }
        return false;
    }

    ShapeGroup.prototype.UpdateBuffers = function(view) {
        for (var i = 0; i < this.Shapes.length; ++i) {
            this.Shapes.UpdateBuffers(view);
        }
    }

    // Find a world location of a popup point given a camera.
    ShapeGroup.prototype.FindPopupPoint = function(cam) {
        if (this.Shapes.length == 0) { return; }
        var roll = cam.Roll;
        var s = Math.sin(roll + (Math.PI*0.25));
        var c = Math.cos(roll + (Math.PI*0.25));
        var bestPt = this.Shapes[0].FindPopupPoint(cam);
        var bestProjection = (c*bestPt[0])-(s*bestPt[1]);
        for (var i = 1; i < this.Shapes.length; ++i) {
            var pt = this.Shapes[i].FindPopupPoint(cam);
            var projection = (c*pt[0])-(s*pt[1]);
            if (projection > bestProjection) {
                bestProjection = projection;
                bestPt = pt;
            }
        }
        return bestPt;
    }

    ShapeGroup.prototype.Draw = function(view) {
        for (var i = 0; i < this.Shapes.length; ++i) {
            this.Shapes[i].Draw(view);
        }
    }

    ShapeGroup.prototype.AddShape = function(shape) {
        this.Shapes.push(shape);
    }

    ShapeGroup.prototype.GetNumberOfShapes = function() {
        return this.Shapes.length;
    }

    ShapeGroup.prototype.GetShape = function(index) {
        return this.Shapes[index];
    }

    ShapeGroup.prototype.SetActive = function(flag) {
        for (var i = 0; i < this.Shapes.length; ++i) {
            this.Shapes[i].SetActive(flag);
        }        
    }

    ShapeGroup.prototype.SetLineWidth = function(lineWidth) {
        for (var i = 0; i < this.Shapes.length; ++i) {
            this.Shapes[i].LineWidth = lineWidth;
        }
    }

    // Just returns the first.
    ShapeGroup.prototype.GetLineWidth = function() {
        if (this.Shapes.length != 0) {
            return this.Shapes[0].GetLineWidth();
        }
        return 0;
    }

    ShapeGroup.prototype.SetOutlineColor = function(color) {
        for (var i = 0; i < this.Shapes.length; ++i) {
            this.Shapes[i].OutlineColor = color;
        }
    }

    // Just returns the first.
    ShapeGroup.prototype.GetOutlineColor = function() {
        if (this.Shapes.length != 0) {
            return this.Shapes[0].OutlineColor;
        }
        return [0,0,0];
    }

    ShapeGroup.prototype.SetOrigin = function(origin) {
        for (var i = 0; i < this.Shapes.length; ++i) {
            // Makes a copy of the array.
            this.Shapes[i].SetOrigin(origin);
        }
    }

    // Adds origin to points and sets origin to 0.
    ShapeGroup.prototype.ResetOrigin = function() {
        for (var i = 0; i < this.Shapes.length; ++i) {
            this.Shapes[i].ResetOrigin();
        }
    }
    
    // Just returns the first.
    ShapeGroup.prototype.GetOrigin = function() {
        if (this.Shapes.length != 0) {
            return this.Shapes[0].Origin;
        }
        return [0,0,0];
    }

    ShapeGroup.prototype.UpdateBuffers = function(view) {
        for (var i = 0; i < this.Shapes.length; ++i) {
            this.Shapes[i].UpdateBuffers(view);
        }
    }


    SAM.ShapeGroup = ShapeGroup;
})();

